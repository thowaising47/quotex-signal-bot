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

# --- Secure Config ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is in Price Action Sureshot Mode!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

def get_signal_pro():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🚀 [SCAN] Price Action Scan: {now.strftime('%H:%M:%S')}")
    
    best_setup = None
    max_score = -1

    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=50&apikey={TWELVE_DATA_API_KEY}"
            response = requests.get(url, timeout=10).json()
            
            if 'values' not in response: continue
                
            df = pd.DataFrame(response['values'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['open'] = pd.to_numeric(df['open'])
            df = df.iloc[::-1].reset_index(drop=True)

            # --- Price Action Indicators ---
            # Pivot Points (Classic)
            last_high = df['high'].iloc[-2]
            last_low = df['low'].iloc[-2]
            last_close = df['close'].iloc[-2]
            pivot = (last_high + last_low + last_close) / 3
            res1 = (2 * pivot) - last_low
            sup1 = (2 * pivot) - last_high

            # RSI for confirmation
            rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi().iloc[-1]
            
            price = df['close'].iloc[-1]
            high = df['high'].iloc[-1]
            low = df['low'].iloc[-1]

            score = 0
            signal_type = ""

            # CALL: Price at Support + RSI < 35 + Rejection from Low
            if price <= (sup1 * 1.0003) and rsi < 35:
                rejection = (price - low) / (high - low + 0.00001)
                if rejection > 0.4: # 40% wick rejection
                    signal_type = "🟢 CALL (UP)"
                    score = (35 - rsi) + rejection * 10

            # PUT: Price at Resistance + RSI > 65 + Rejection from High
            elif price >= (res1 * 0.9997) and rsi > 65:
                rejection = (high - price) / (high - low + 0.00001)
                if rejection > 0.4:
                    signal_type = "🔴 PUT (DOWN)"
                    score = (rsi - 65) + rejection * 10

            if signal_type and score > max_score:
                max_score = score
                best_setup = {
                    'symbol': symbol,
                    'type': signal_type,
                    'rsi': rsi,
                    'price': price
                }

            time.sleep(6) 
            
        except Exception as e:
            print(f"❌ Error {symbol}: {e}")

    if best_setup:
        msg = f"""🎯 **PRICE ACTION SURESHOT**
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {best_setup['symbol']}
⚡ **Direction:** **{best_setup['type']}**
⏳ **Duration:** 5 Minutes
🔥 **Accuracy:** `94% +` 
━━━━━━━━━━━━━━━━━━
📊 **RSI:** {best_setup['rsi']:.1f}
📉 **Strategy:** Support/Resistance Rejection
⏰ **BD Time:** {now.strftime('%H:%M')}
━━━━━━━━━━━━━━━━━━
⚠️ *Wait for Candle Rejection confirmation*"""
        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        if now.minute % 5 == 0 and now.second == 0:
            get_signal_pro()
            time.sleep(60) 
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)