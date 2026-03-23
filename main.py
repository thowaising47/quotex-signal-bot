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
    return "Momentum 1-Min Sniper is Online!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "EUR/JPY"]

def get_recovery_signal():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🚀 [SCAN] Recovery Mode: {now.strftime('%H:%M:%S')}")
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=20&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url, timeout=7).json()
            if 'values' not in res: continue
            
            df = pd.DataFrame(res['values'])
            df['close'] = pd.to_numeric(df['close'])
            df['open'] = pd.to_numeric(df['open'])
            df = df.iloc[::-1].reset_index(drop=True)

            # --- Pro Indicators ---
            ema20 = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator().iloc[-1]
            rsi = ta.momentum.RSIIndicator(df['close'], window=7).rsi().iloc[-1]
            
            # Momentum: Last 2 candles direction
            c1_green = df['close'].iloc[-1] > df['open'].iloc[-1]
            c2_green = df['close'].iloc[-2] > df['open'].iloc[-2]
            
            price = df['close'].iloc[-1]
            signal_type = ""

            # 🟢 CALL: Price > EMA20 (Uptrend) + RSI < 35 + 2 Red Candles (Pullback)
            if price > ema20 and rsi < 35 and not c1_green and not c2_green:
                signal_type = "🟢 CALL (1-MIN)"
            
            # 🔴 PUT: Price < EMA20 (Downtrend) + RSI > 65 + 2 Green Candles (Pullback)
            elif price < ema20 and rsi > 65 and c1_green and c2_green:
                signal_type = "🔴 PUT (1-MIN)"

            if signal_type:
                msg = f"🔥 **RECOVERY SIGNAL**\n━━━━━━━━━━━━━━\n🏦 Asset: {symbol}\n⚡ Direction: **{signal_type}**\n⏳ Trade at: **:00 Seconds**\n⏰ BD Time: {now.strftime('%H:%M:%S')}\n━━━━━━━━━━━━━━"
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                break 
            time.sleep(1)
        except: continue

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        # Thik 50th second-e trigger (08:38:50, 08:40:50...)
        if now.second == 50:
            get_recovery_signal()
            time.sleep(10)
        time.sleep(0.5)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))