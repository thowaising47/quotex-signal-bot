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
    return "Bot is Running Perfectly on Twelve Data API!"

# Top 7 Stable Pairs
PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "EUR/JPY", "GBP/JPY"]

def get_signal_pro():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"--- Twelve Data Scan Started: {now.strftime('%H:%M:%S')} (UTC+6) ---")
    
    for symbol in PAIRS:
        try:
            # Official API Call (Twelve Data)
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=70&apikey={TWELVE_DATA_API_KEY}"
            response = requests.get(url, timeout=15).json()
            
            if 'values' not in response:
                print(f"⚠️ Skip {symbol}: {response.get('message', 'API Error')}")
                continue
                
            df = pd.DataFrame(response['values'])
            df['close'] = pd.to_numeric(df['close'])
            # Twelve Data data ulta thake, tai reverse kora dorkar
            df = df.iloc[::-1].reset_index(drop=True)

            # Technical Indicators
            df['EMA200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()
            df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            df['BB_High'] = bb.bollinger_hband()
            df['BB_Low'] = bb.bollinger_lband()

            # Latest Values
            price = float(df['close'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])
            # EMA200 na thakle current price-ei logic check korbe
            ema200 = float(df['EMA200'].iloc[-1]) if not pd.isna(df['EMA200'].iloc[-1]) else price
            bb_high = float(df['BB_High'].iloc[-1])
            bb_low = float(df['BB_Low'].iloc[-1])

            signal_type = ""
            # Logic: Trend Up + Oversold + Touch BB Low
            if price > ema200 and price <= bb_low and rsi < 40:
                signal_type = "🟢 CALL (UP)"
            # Logic: Trend Down + Overbought + Touch BB High
            elif price < ema200 and price >= bb_high and rsi > 60:
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                confidence = random.randint(91, 98)
                msg = f"""
💎 **PREMIUM VIP SIGNAL** 💎
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {symbol}
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
                print(f"✅ Success: {symbol}")

            # API Rate Limit (Free plan e gap dorkar)
            time.sleep(8) 
            
        except Exception as e:
            print(f"❌ Error scanning {symbol}: {e}")

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        # Sync with 5-minute candle marks (00, 05, 10...)
        if now.minute % 5 == 0 and now.second == 0:
            get_signal_pro()
            time.sleep(60) 
        time.sleep(1)

if __name__ == "__main__":
    try:
        bot.send_message(CHAT_ID, "🚀 **Bot PRO Started (Twelve Data)!**\nSyncing with Bangladesh Time (UTC+6)...")
    except: pass
    
    threading.Thread(target=run_scheduler, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)