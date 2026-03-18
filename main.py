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
    return "Strict 10-Min Sniper is Online!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "EUR/JPY", "GBP/JPY"]

def get_strict_signal():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"📡 [SCAN] Strict 10-Min Mode: {now.strftime('%H:%M:%S')}")
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=50&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url, timeout=12).json()
            if 'values' not in res: continue
            
            df = pd.DataFrame(res['values'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['open'] = pd.to_numeric(df['open'])
            df = df.iloc[::-1].reset_index(drop=True)

            # --- Technicals ---
            ema200 = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator().iloc[-1]
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            bb_high, bb_low = bb.bollinger_hband().iloc[-1], bb.bollinger_lband().iloc[-1]
            
            price, high, low, open_p = df['close'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1], df['open'].iloc[-1]
            
            # Candle Rejection (Pin Bar Logic)
            upper_wick = high - max(open_p, price)
            lower_wick = min(open_p, price) - low
            body = abs(price - open_p) + 0.000001

            signal_type = ""
            # 🟢 CALL: Price below BB Low + Strong Lower Rejection + Trend is UP (Price > EMA200)
            if price <= bb_low and lower_wick > body * 1.2 and price > ema200:
                signal_type = "🟢 CALL (UP) - Rejection"
            
            # 🔴 PUT: Price above BB High + Strong Upper Rejection + Trend is DOWN (Price < EMA200)
            elif price >= bb_high and upper_wick > body * 1.2 and price < ema200:
                signal_type = "🔴 PUT (DOWN) - Rejection"

            if signal_type:
                msg = f"💎 **10-MIN SNIPER SIGNAL**\n━━━━━━━━━━━━━━\n🏦 Asset: {symbol}\n⚡ Direction: **{signal_type}**\n⏳ Time: 10 MIN\n⏰ BD Time: {now.strftime('%H:%M')}\n━━━━━━━━━━━━━━"
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                break 
            time.sleep(3)
        except: continue

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        # THIK 10 MINUTE POR POR SCAN (12:20, 12:30...)
        if now.minute % 10 == 0 and now.second == 0:
            get_strict_signal()
            time.sleep(60)
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))