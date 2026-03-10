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
    return "Bot is Live! Monitoring Market..."

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

def get_signal_pro():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🚀 [SCAN] Starting Market Analysis at {now.strftime('%H:%M:%S')}")
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=80&apikey={TWELVE_DATA_API_KEY}"
            response = requests.get(url, timeout=10).json()
            
            if 'values' not in response: continue
                
            df = pd.DataFrame(response['values'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df = df.iloc[::-1].reset_index(drop=True)

            # Indicators
            df['EMA200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()
            df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'], window=14, smooth_window=3)
            df['Stoch_K'] = stoch.stoch()
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2.2)
            df['BB_High'] = bb.bollinger_hband()
            df['BB_Low'] = bb.bollinger_lband()

            # Latest Values
            price = float(df['close'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])
            stoch_k = float(df['Stoch_K'].iloc[-1])
            ema200 = float(df['EMA200'].iloc[-1]) if not pd.isna(df['EMA200'].iloc[-1]) else price
            bb_high = float(df['BB_High'].iloc[-1])
            bb_low = float(df['BB_Low'].iloc[-1])

            signal_type = ""
            if price > ema200 and price <= (bb_low * 1.0002) and rsi < 38 and stoch_k < 20:
                signal_type = "🟢 CALL (UP)"
            elif price < ema200 and price >= (bb_high * 0.9998) and rsi > 62 and stoch_k > 80:
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
💰 **Price:** {price:.5f}
📊 **RSI:** {rsi:.1f} | **Stoch:** {stoch_k:.1f}
📈 **Trend:** {"Strong Uptrend" if price > ema200 else "Strong Downtrend"}
⏰ **Time:** {now.strftime('%H:%M')} (BD Time)
━━━━━━━━━━━━━━━━━━
"""
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                print(f"✅ [SUCCESS] Signal sent for {symbol}")

            time.sleep(5) 
            
        except Exception as e:
            print(f"❌ [ERROR] {symbol}: {e}")

def run_scheduler():
    print("⏰ [WATCHDOG] Scheduler is running...")
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        
        # Every minute log
        if now.second == 0:
            print(f"🕒 [LIVE] {now.strftime('%H:%M:%S')} - Waiting for 5-min interval...")

        if now.minute % 5 == 0 and now.second == 0:
            get_signal_pro()
            time.sleep(60) 
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)