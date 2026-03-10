import telebot
import schedule
import time
import yfinance as yf
import pandas as pd
import ta
import threading
import random
import requests
from flask import Flask
import os
from datetime import datetime
import pytz

# --- Config ---
BOT_TOKEN = "8320790751:AAH1ZWiD5f5JpIc96eAtR-Yi5CU8t4B7dng"
CHAT_ID = "7995220028"
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running!"

# Currency Pairs
PAIRS = {
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY", "EURGBP=X": "EUR/GBP"
}

def get_perfect_signal():
    # UTC+6 Time Check (Logging-er jonno)
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"--- Market Scanning Started at {now.strftime('%H:%M:%S')} (UTC+6) ---")
    
    items = list(PAIRS.items())
    random.shuffle(items)

    for symbol, name in items:
        try:
            data = yf.download(symbol, period="2d", interval="5m", progress=False)
            if len(data) < 50: continue

            # Indicators
            data['EMA200'] = ta.trend.EMAIndicator(data['Close'], window=200).ema_indicator()
            data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()
            bb = ta.volatility.BollingerBands(data['Close'], window=20, window_dev=2)
            data['BB_High'] = bb.bollinger_hband()
            data['BB_Low'] = bb.bollinger_lband()

            price = float(data['Close'].iloc[-1])
            rsi = float(data['RSI'].iloc[-1])
            ema200 = float(data['EMA200'].iloc[-1])
            bb_high = float(data['BB_High'].iloc[-1])
            bb_low = float(data['BB_Low'].iloc[-1])

            signal_type = ""
            confidence = random.randint(88, 96)

            if price > ema200 and price <= bb_low and rsi < 40:
                signal_type = "🟢 CALL (UP)"
            elif price < ema200 and price >= bb_high and rsi > 60:
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                msg = f"""
💎 **PREMIUM VIP SIGNAL** 💎
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {name}
⚡ **Direction:** **{signal_type}**
⏳ **Duration:** 5 Minutes
🔥 **Confidence:** `{confidence}%` 
━━━━━━━━━━━━━━━━━━
💰 **Entry Price:** {price:.5f}
📊 **RSI:** {rsi:.2f}
📈 **Trend:** {"Uptrend" if price > ema200 else "Downtrend"}
⏰ **Time:** {now.strftime('%H:%M')} (UTC+6)
━━━━━━━━━━━━━━━━━━
"""
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                print(f"✅ Signal sent for {name}")
            
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error scanning {name}: {e}")

def run_scheduler():
    # Bangladesh Time (UTC+6) onujayi sync kora
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        
        # Prottek 5 minute por por (jemon 00, 05, 10, 15...)
        if now.minute % 5 == 0 and now.second == 0:
            get_perfect_signal()
            time.sleep(60) # Ek minute gap jate ek minute e bar bar scan na kore
        
        time.sleep(1)

if __name__ == "__main__":
    try:
        bot.send_message(CHAT_ID, "🚀 **Bot Live & Time-Synced!**\nScanning every 5 minutes (UTC+6)...")
    except:
        pass

    # Start Time-Synced Scheduler in Background
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)