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
    return "Optimized 10-Min Sniper is Online!"

# Pair সংখ্যা বাড়ালাম যাতে সুযোগ বেশি থাকে
PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "EUR/JPY", "GBP/JPY"]

def get_optimized_signal():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"📡 [SCAN] Optimized Mode: {now.strftime('%H:%M:%S')}")
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=50&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url, timeout=12).json()
            if 'values' not in res: continue
            
            df = pd.DataFrame(res['values'])
            df['close'] = pd.to_numeric(df['close'])
            df = df.iloc[::-1].reset_index(drop=True)

            # --- Technical Combo ---
            rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi().iloc[-1]
            # Bollinger Bands for Volatility
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            bb_high = bb.bollinger_hband().iloc[-1]
            bb_low = bb.bollinger_lband().iloc[-1]
            
            price = df['close'].iloc[-1]
            ema200 = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator().iloc[-1]

            signal_type = ""
            
            # 🟢 CALL Logic: Price hits Lower BB + RSI < 35 (Trend Support)
            if price <= bb_low and rsi < 35:
                signal_type = "🟢 CALL (UP) - Support Hit"
            
            # 🔴 PUT Logic: Price hits Upper BB + RSI > 65 (Trend Resistance)
            elif price >= bb_high and rsi > 65:
                signal_type = "🔴 PUT (DOWN) - Resistance Hit"

            if signal_type:
                msg = f"""💎 **10-MIN OPTIMIZED SIGNAL**
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {symbol}
⚡ **Direction:** **{signal_type}**
⏳ **Duration:** 10 Minutes
📊 **RSI:** {rsi:.1f}
━━━━━━━━━━━━━━━━━━
⏰ **BD Time:** {now.strftime('%H:%M')}
━━━━━━━━━━━━━━━━━━"""
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                # Result logic function call ignored for brevity but same as before
                break 
            time.sleep(3)
        except Exception as e:
            print(f"Error on {symbol}: {e}")

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        # ৫ মিনিট পর পর স্ক্যান করবে যাতে সিগন্যাল ঘন ঘন আসে
        if now.minute % 5 == 0 and now.second == 0:
            get_optimized_signal()
            time.sleep(60)
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))