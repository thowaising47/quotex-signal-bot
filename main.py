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
    return "10-Min Fast Signal Bot is Active!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

# --- Instant Result Check (After 10 Mins) ---
def check_final_result(symbol, signal_type, entry_price):
    # 10 minute duration + 5 second buffer for API sync
    time.sleep(605) 
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=1&apikey={TWELVE_DATA_API_KEY}"
        data = requests.get(url).json()
        exit_price = float(data['values'][0]['close'])
        
        win = (exit_price > entry_price) if "CALL" in signal_type else (exit_price < entry_price)
        result_icon = "✅ WIN" if win else "❌ LOSS"
        
        final_text = f"📊 **RESULT: {symbol}**\n━━━━━━━━━━━━━━\nTrade Type: 10 MIN\nEntry: `{entry_price:.5f}`\nExit: `{exit_price:.5f}`\nResult: **{result_icon}**\n━━━━━━━━━━━━━━"
        bot.send_message(CHAT_ID, final_text)
    except Exception as e:
        print(f"Result Error: {e}")

def get_signal_fast():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🚀 [SCANNING] Fast 10-Min Mode: {now.strftime('%H:%M:%S')}")
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=30&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url, timeout=10).json()
            if 'values' not in res: continue
            
            df = pd.DataFrame(res['values'])
            df['close'] = pd.to_numeric(df['close'])
            df = df.iloc[::-1].reset_index(drop=True)

            # Strategy: Balanced RSI (40/60) for faster signals
            rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi().iloc[-1]
            price = df['close'].iloc[-1]

            signal_type = ""
            # Relaxed Rules for more frequency
            if rsi < 40: 
                signal_type = "🟢 CALL (UP)"
            elif rsi > 60: 
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                msg = f"""🎯 **10-MIN FAST SIGNAL**
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {symbol}
⚡ **Direction:** **{signal_type}**
⏳ **Duration:** 10 Minutes
📊 **RSI:** {rsi:.1f}
⏰ **BD Time:** {now.strftime('%H:%M')}
━━━━━━━━━━━━━━━━━━"""
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                # Start result thread immediately
                threading.Thread(target=check_final_result, args=(symbol, signal_type, price)).start()
                break # Send one high-quality signal per scan
            time.sleep(5)
        except: continue

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        # 10 minute interval scan
        if now.minute % 10 == 0 and now.second == 0:
            get_signal_fast()
            time.sleep(60)
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))