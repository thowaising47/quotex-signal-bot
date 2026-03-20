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
    return "10-Min High Frequency Bot is Online!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "EUR/JPY", "GBP/JPY"]

def get_signal_now():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"📡 [SCAN] 10-Min Scan Started: {now.strftime('%H:%M:%S')}")
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=50&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url, timeout=12).json()
            if 'values' not in res: continue
            
            df = pd.DataFrame(res['values'])
            df['close'] = pd.to_numeric(df['close'])
            df = df.iloc[::-1].reset_index(drop=True)

            # --- Faster Indicators for More Signals ---
            rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi().iloc[-1]
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=1.9)
            bb_h, bb_l = bb.bollinger_hband().iloc[-1], bb.bollinger_lband().iloc[-1]
            price = df['close'].iloc[-1]

            signal_type = ""
            # Relaxed Logic: Only RSI + BB (No heavy EMA filter)
            if price <= bb_l and rsi < 40:
                signal_type = "🟢 CALL (UP)"
            elif price >= bb_h and rsi > 60:
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                msg = f"🎯 **10-MIN SIGNAL**\n━━━━━━━━━━━━━━\n🏦 Asset: {symbol}\n⚡ Direction: **{signal_type}**\n📊 RSI: {rsi:.1f}\n⏰ BD Time: {now.strftime('%H:%M')}\n━━━━━━━━━━━━━━"
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                # One signal per scan cycle
                break 
            time.sleep(2)
        except: continue

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        # EXACT 10 MINUTE SCAN (05:40, 05:50, 06:00...)
        if now.minute % 10 == 0 and now.second == 0:
            get_signal_now()
            time.sleep(60)
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))