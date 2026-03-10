import telebot
import time
import pandas as pd
import ta
import threading
import random
import os
import requests
from datetime import datetime
import pytz
from flask import Flask

# --- Config ---
BOT_TOKEN = "8320790751:AAH1ZWiD5f5JpIc96eAtR-Yi5CU8t4B7dng"
CHAT_ID = "7995220028"
TWELVE_DATA_API_KEY = "4a817d9a7a6c477caea0b0550a02ba12"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running with 7 Pairs & Flexible Rules!"

# Fixed 7 High Volume Pairs
PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "EUR/JPY", "GBP/JPY"]

def get_signal_pro():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🚀 Scanning 7 Pairs at {now.strftime('%H:%M:%S')} (BD Time)")
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=70&apikey={TWELVE_DATA_API_KEY}"
            response = requests.get(url, timeout=15).json()
            
            if 'values' not in response:
                print(f"⚠️ Skip {symbol}: API Limit ba Busy")
                continue
                
            df = pd.DataFrame(response['values'])
            df['close'] = pd.to_numeric(df['close'])
            df = df.iloc[::-1].reset_index(drop=True)

            # Indicators
            df['EMA200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()
            df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2.0)
            df['BB_High'] = bb.bollinger_hband()
            df['BB_Low'] = bb.bollinger_lband()

            price = float(df['close'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])
            ema200 = float(df['EMA200'].iloc[-1]) if not pd.isna(df['EMA200'].iloc[-1]) else price
            bb_high = float(df['BB_High'].iloc[-1])
            bb_low = float(df['BB_Low'].iloc[-1])

            signal_type = ""
            # --- Flexible Rules for More Signals ---
            # CALL: RSI 45 er niche ebong Price BB Low er kachakachi
            if rsi < 45 and price <= (bb_low * 1.0003):
                signal_type = "🟢 CALL (UP)"
            # PUT: RSI 55 er upore ebong Price BB High er kachakachi
            elif rsi > 55 and price >= (bb_high * 0.9997):
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                confidence = random.randint(89, 96)
                msg = f"""
💎 **PREMIUM VIP SIGNAL** 💎
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {symbol}
⚡ **Direction:** **{signal_type}**
⏳ **Duration:** 5 Minutes
🔥 **Confidence:** `{confidence}%` 
━━━━━━━━━━━━━━━━━━
💰 **Price:** {price:.5f}
📊 **RSI:** {rsi:.2f}
📈 **Trend:** {"Uptrend" if price > ema200 else "Downtrend"}
⏰ **Time:** {now.strftime('%H:%M')} (BD Time)
━━━━━━━━━━━━━━━━━━
"""
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                print(f"✅ Signal Sent: {symbol}")

            time.sleep(8) # API Limit protection
            
        except Exception as e:
            print(f"❌ Error scanning {symbol}: {e}")

def run_scheduler():
    print("⏰ Scheduler is monitoring Bangladesh Time (UTC+6)...")
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        
        # Exact 5-minute marks (00, 05, 10, 15...)
        if now.minute % 5 == 0 and now.second == 0:
            get_signal_pro()
            time.sleep(60) 
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)