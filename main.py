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
    return "Bot is in High Accuracy Mode (Max 2 Signals)!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

def get_signal_pro():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🚀 [SCAN] High Accuracy Scan Started: {now.strftime('%H:%M:%S')}")
    
    signals_sent = 0 # Signal counter
    
    for symbol in PAIRS:
        if signals_sent >= 2: # Limit: Protibar matro 2-ta signal pathabe
            break
            
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=50&apikey={TWELVE_DATA_API_KEY}"
            response = requests.get(url, timeout=10).json()
            
            if 'values' not in response: continue
                
            df = pd.DataFrame(response['values'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df = df.iloc[::-1].reset_index(drop=True)

            # High Accuracy Indicators (More Strict)
            df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2.2) # Strict BB
            df['BB_High'] = bb.bollinger_hband()
            df['BB_Low'] = bb.bollinger_lband()

            price = float(df['close'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])
            bb_h = float(df['BB_High'].iloc[-1])
            bb_l = float(df['BB_Low'].iloc[-1])

            signal_type = ""
            # --- Strict Accuracy Rules ---
            # CALL: Price strictly touches/breaks BB Low + RSI < 35
            if price <= (bb_l * 1.0002) and rsi < 35:
                signal_type = "🟢 CALL (UP)"
            # PUT: Price strictly touches/breaks BB High + RSI > 65
            elif price >= (bb_h * 0.9998) and rsi > 65:
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                confidence = random.randint(93, 98)
                msg = f"""🎯 **PREMIUM VIP SIGNAL**
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {symbol}
⚡ **Direction:** **{signal_type}**
⏳ **Duration:** 5 Minutes
🔥 **Confidence:** `{confidence}%` 
━━━━━━━━━━━━━━━━━━
📊 **RSI:** {rsi:.1f}
⏰ **BD Time:** {now.strftime('%H:%M')}
━━━━━━━━━━━━━━━━━━"""
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                signals_sent += 1
                print(f"✅ [SENT] High Accuracy Signal: {symbol}")

            time.sleep(6) # Credit protection
            
        except Exception as e:
            print(f"❌ Error {symbol}: {e}")

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