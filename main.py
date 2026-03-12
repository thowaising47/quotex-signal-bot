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
    return "1-Minute Scalper Bot is Active!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

# --- 1-Minute Result Check ---
def check_result_1min(symbol, signal_type, entry_price):
    time.sleep(65) # 1 minute + 5 sec safety buffer
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=1&apikey={TWELVE_DATA_API_KEY}"
        data = requests.get(url).json()
        exit_price = float(data['values'][0]['close'])
        
        if "CALL" in signal_type:
            win = exit_price > entry_price
        else:
            win = exit_price < entry_price
            
        result_icon = "✅ WIN" if win else "❌ LOSS"
        final_text = f"📊 **1-MIN RESULT: {symbol}**\nEntry: `{entry_price:.5f}`\nExit: `{exit_price:.5f}`\nResult: **{result_icon}**"
        bot.send_message(CHAT_ID, final_text)
    except:
        pass

def get_signal_1min():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"⚡ [1-MIN SCAN] {now.strftime('%H:%M:%S')}")
    
    signals = []
    for symbol in PAIRS:
        try:
            # 1-minute interval request
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=30&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url, timeout=7).json()
            if 'values' not in res: continue
                
            df = pd.DataFrame(res['values'])
            df['close'] = pd.to_numeric(df['close'])
            df = df.iloc[::-1].reset_index(drop=True)

            # Fast Indicators for 1-min
            rsi = ta.momentum.RSIIndicator(df['close'], window=7).rsi().iloc[-1]
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2.0)
            bb_h, bb_l = bb.bollinger_hband().iloc[-1], bb.bollinger_lband().iloc[-1]
            price = df['close'].iloc[-1]

            signal_type = ""
            # Scalping Rules: RSI < 20 or > 80
            if price <= bb_l and rsi < 20:
                signal_type = "🟢 CALL (UP)"
            elif price >= bb_h and rsi > 80:
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                signals.append({'symbol': symbol, 'type': signal_type, 'price': price, 'rsi': rsi})
            time.sleep(2) # Faster scanning for 1-min
        except: continue

    if signals:
        top = signals[0]
        msg = f"⚡ **1-MIN SCALPER**\n━━━━━━━━━━━━━━\n🏦 Asset: {top['symbol']}\n⚡ Direction: **{top['type']}**\n⏳ Time: 1 MINUTE\n📊 RSI: {top['rsi']:.1f}\n⏰ BD Time: {now.strftime('%H:%M')}\n━━━━━━━━━━━━━━"
        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
        threading.Thread(target=check_result_1min, args=(top['symbol'], top['type'], top['price'])).start()

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        # 1-minute trading-e prottek minute-e scan hobe
        if now.second == 0:
            get_signal_1min()
            time.sleep(50) 
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))