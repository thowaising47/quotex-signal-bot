import telebot
import time
import pandas as pd
import ta
import threading
import os
import requests
from datetime import datetime
import pytz
from flask import Flask

# --- Secure Config ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Strategic 10-Min Bot is Active!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

def check_final_result(symbol, signal_type, entry_price):
    time.sleep(605) # 10 min + buffer
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=1&apikey={TWELVE_DATA_API_KEY}"
        data = requests.get(url).json()
        exit_price = float(data['values'][0]['close'])
        win = (exit_price > entry_price) if "CALL" in signal_type else (exit_price < entry_price)
        result_icon = "✅ WIN" if win else "❌ LOSS"
        bot.send_message(CHAT_ID, f"📊 **10-MIN RESULT: {symbol}**\nResult: **{result_icon}**\nEntry: `{entry_price:.5f}` | Exit: `{exit_price:.5f}`")
    except: pass

def get_strategic_signal():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🔭 [STRATEGIC SCAN] {now.strftime('%H:%M:%S')}")
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=50&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url, timeout=10).json()
            if 'values' not in res: continue
            
            df = pd.DataFrame(res['values'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df = df.iloc[::-1].reset_index(drop=True)

            # --- High Accuracy Indicators ---
            rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi().iloc[-1]
            stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'], window=14, smooth_window=3)
            stoch_k = stoch.stoch().iloc[-1]
            
            price = df['close'].iloc[-1]
            ema200 = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator().iloc[-1]

            signal_type = ""
            # 🟢 CALL: Trend UP + RSI < 30 + Stoch < 20
            if price > ema200 and rsi < 32 and stoch_k < 20:
                signal_type = "🟢 CALL (UP) - Sureshot"
            # 🔴 PUT: Trend DOWN + RSI > 70 + Stoch > 80
            elif price < ema200 and rsi > 68 and stoch_k > 80:
                signal_type = "🔴 PUT (DOWN) - Sureshot"

            if signal_type:
                msg = f"""🎯 **STRATEGIC 10-MIN SIGNAL**
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {symbol}
⚡ **Direction:** **{signal_type}**
⏳ **Duration:** 10 Minutes
🔥 **Confidence:** `Premium`
━━━━━━━━━━━━━━━━━━
📊 **RSI:** {rsi:.1f} | **Stoch:** {stoch_k:.1f}
⏰ **BD Time:** {now.strftime('%H:%M')}
━━━━━━━━━━━━━━━━━━"""
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                threading.Thread(target=check_final_result, args=(symbol, signal_type, price)).start()
                break 
            time.sleep(5)
        except: continue

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        # Thik 10 minute por por scan hobe (05:20, 05:30...)
        if now.minute % 10 == 0 and now.second == 0:
            get_strategic_signal()
            time.sleep(60)
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))