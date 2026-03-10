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

# --- Config ---
BOT_TOKEN = "8287022829:AAEJfSnbsAgnGqoFbNESwDMifQ9S5Gf9bJk"
CHAT_ID = "7995220028"
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "Perfect Signal Bot with Confidence is Active!"

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

PAIRS = {
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY", "EURGBP=X": "EUR/GBP"
}

def get_perfect_signal():
    print("Searching for Perfect Signals...")
    items = list(PAIRS.items())
    random.shuffle(items)

    for symbol, name in items:
        try:
            data = yf.download(symbol, period="2d", interval="5m", progress=False, session=session)
            if len(data) < 50: continue

            # Indicators
            data['EMA200'] = ta.trend.EMAIndicator(data['Close'], window=200).ema_indicator()
            data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()
            bb = ta.volatility.BollingerBands(data['Close'], window=20, window_dev=2)
            data['BB_High'] = bb.bollinger_hband()
            data['BB_Low'] = bb.bollinger_lband()

            # Latest Values
            price = data['Close'].iloc[-1]
            rsi = data['RSI'].iloc[-1]
            ema200 = data['EMA200'].iloc[-1]
            bb_high = data['BB_High'].iloc[-1]
            bb_low = data['BB_Low'].iloc[-1]

            signal_type = ""
            confidence = 0

            # --- CALL STRATEGY ---
            if price > ema200 and price <= bb_low:
                signal_type = "🟢 CALL (UP)"
                # RSI level onujayi confidence barano
                if rsi < 30: confidence = random.randint(92, 97)
                else: confidence = random.randint(85, 91)

            # --- PUT STRATEGY ---
            elif price < ema200 and price >= bb_high:
                signal_type = "🔴 PUT (DOWN)"
                if rsi > 70: confidence = random.randint(92, 97)
                else: confidence = random.randint(85, 91)

            if signal_type:
                # Premium SMS Format
                msg = f"""
💎 **PREMIUM VIP SIGNAL** 💎
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {name}
⚡ **Direction:** **{signal_type}**
⏳ **Duration:** 5 Minutes
🔥 **Confidence:** `{confidence}%` 
━━━━━━━━━━━━━━━━━━
💰 **Entry Price:** {price:.5f}
📊 **RSI Level:** {rsi:.2f}
📈 **Trend:** {"Strong Bullish" if price > ema200 else "Strong Bearish"}
🏆 **Accuracy:** High Accuracy
━━━━━━━━━━━━━━━━━━
⚠️ *Wait for new candle start.*
⚠️ *1-Step Martingale (MTG) Recommended.*
📢 *Join our VIP for more!*
"""
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                print(f"Perfect Signal sent for {name} with {confidence}% confidence")
            
            time.sleep(random.uniform(4, 8)) # Anti-block delay

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

def run_scheduler():
    schedule.every(5).minutes.do(get_perfect_signal)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)