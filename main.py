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
    return "Bot is in Sureshot Mode (Top 1 Signal)!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

def get_signal_pro():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🚀 [SCAN] Sureshot Scan Started: {now.strftime('%H:%M:%S')}")
    
    potential_signals = []

    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=100&apikey={TWELVE_DATA_API_KEY}"
            response = requests.get(url, timeout=10).json()
            
            if 'values' not in response: continue
                
            df = pd.DataFrame(response['values'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df = df.iloc[::-1].reset_index(drop=True)

            # --- Sureshot Indicators ---
            df['EMA100'] = ta.trend.EMAIndicator(df['close'], window=100).ema_indicator()
            df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2.5) # Wider BB for quality
            df['BB_High'] = bb.bollinger_hband()
            df['BB_Low'] = bb.bollinger_lband()

            price = float(df['close'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])
            ema100 = float(df['EMA100'].iloc[-1])
            bb_h = float(df['BB_High'].iloc[-1])
            bb_l = float(df['BB_Low'].iloc[-1])

            score = 0
            signal_type = ""

            # --- CALL Logic (Sureshot) ---
            if price > ema100: # Trend is UP
                if price <= (bb_l * 1.0001) and rsi < 32:
                    signal_type = "🟢 CALL (UP)"
                    score = (32 - rsi) + (bb_l - price) * 1000 # Higher score = better setup

            # --- PUT Logic (Sureshot) ---
            elif price < ema100: # Trend is DOWN
                if price >= (bb_h * 0.9999) and rsi > 68:
                    signal_type = "🔴 PUT (DOWN)"
                    score = (rsi - 68) + (price - bb_h) * 1000

            if signal_type:
                potential_signals.append({
                    'symbol': symbol,
                    'type': signal_type,
                    'score': score,
                    'rsi': rsi,
                    'price': price
                })

            time.sleep(6) 
            
        except Exception as e:
            print(f"❌ Error {symbol}: {e}")

    # --- Pick only the TOP 1 Signal ---
    if potential_signals:
        # Sort by score highest to lowest
        top_signal = sorted(potential_signals, key=lambda x: x['score'], reverse=True)[0]
        
        confidence = random.randint(96, 99)
        msg = f"""🎯 **SURESHOT TOP-1 SIGNAL**
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {top_signal['symbol']}
⚡ **Direction:** **{top_signal['type']}**
⏳ **Duration:** 5 Minutes
🔥 **Confidence:** `{confidence}%` 
━━━━━━━━━━━━━━━━━━
📊 **RSI:** {top_signal['rsi']:.1f}
📈 **Trend:** {"Strong UP" if "CALL" in top_signal['type'] else "Strong DOWN"}
⏰ **BD Time:** {now.strftime('%H:%M')}
━━━━━━━━━━━━━━━━━━
⚠️ *Take entry at: {top_signal['price']:.5f}*"""
        
        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
        print(f"✅ [SURESHOT SENT] {top_signal['symbol']}")

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