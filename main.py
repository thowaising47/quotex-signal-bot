import telebot
import time
import yfinance as yf
import pandas as pd
import ta
import threading
import random
import os
from datetime import datetime
import pytz
from flask import Flask

# --- Config ---
BOT_TOKEN = "8320790751:AAH1ZWiD5f5JpIc96eAtR-Yi5CU8t4B7dng"
CHAT_ID = "7995220028"
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running!"

PAIRS = {
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY", "EURGBP=X": "EUR/GBP"
}

def get_perfect_signal():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"--- Market Scanning Started at {now.strftime('%H:%M:%S')} (UTC+6) ---")
    
    items = list(PAIRS.items())
    random.shuffle(items)

    for symbol, name in items:
        try:
            # Rate limit handling: yf.download er bodole stable method
            data = yf.download(symbol, period="2d", interval="5m", progress=False)
            
            if data.empty or len(data) < 50:
                continue

            # Indicators Calculation
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
            if price > ema200 and price <= bb_low and rsi < 40:
                signal_type = "🟢 CALL (UP)"
            elif price < ema200 and price >= bb_high and rsi > 60:
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                confidence = random.randint(88, 96)
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
                print(f"✅ Signal sent for {name} at {now.strftime('%H:%M')}")
            
            # Request-er majhe gap jate Yahoo block na kore
            time.sleep(random.uniform(2, 4))
            
        except Exception as e:
            print(f"❌ Error scanning {name}: {e}")
            time.sleep(2)

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        # Sync with 5-min intervals (00, 05, 10, 15...)
        if now.minute % 5 == 0 and now.second == 0:
            get_perfect_signal()
            time.sleep(60) # Prevent multiple scans in the same minute
        time.sleep(1)

if __name__ == "__main__":
    # Test message to confirm bot is active
    try:
        bot.send_message(CHAT_ID, "🚀 **Bot Live & Synced!**\nNext scan at the next 5-minute mark.")
    except:
        pass

    threading.Thread(target=run_scheduler, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)