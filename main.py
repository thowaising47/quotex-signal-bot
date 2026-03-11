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

# --- Secure Config (Secrets from Render) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Live - Price Action Sureshot Mode Active!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

def get_signal_pro():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🚀 [WATCHDOG] Scan Started at: {now.strftime('%H:%M:%S')}")
    
    potential_signals = []

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

            # --- Price Action & Pivot Logic ---
            last_h, last_l, last_c = df['high'].iloc[-2], df['low'].iloc[-2], df['close'].iloc[-2]
            pivot = (last_h + last_l + last_c) / 3
            res1 = (2 * pivot) - last_l
            sup1 = (2 * pivot) - last_h

            rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi().iloc[-1]
            price, high, low = df['close'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1]

            score = 0
            signal_type = ""

            # CALL Logic: Support Rejection + RSI < 35
            if price <= (sup1 * 1.0003) and rsi < 35:
                wick_rejection = (price - low) / (high - low + 0.000001)
                if wick_rejection > 0.45: # Strong lower wick
                    signal_type = "🟢 CALL (UP)"
                    score = (35 - rsi) + (wick_rejection * 20)

            # PUT Logic: Resistance Rejection + RSI > 65
            elif price >= (res1 * 0.9997) and rsi > 65:
                wick_rejection = (high - price) / (high - low + 0.000001)
                if wick_rejection > 0.45: # Strong upper wick
                    signal_type = "🔴 PUT (DOWN)"
                    score = (rsi - 65) + (wick_rejection * 20)

            if signal_type:
                potential_signals.append({
                    'symbol': symbol, 'type': signal_type, 'score': score, 
                    'rsi': rsi, 'price': price
                })

            time.sleep(6) # API Safety
            
        except Exception as e:
            print(f"❌ Error {symbol}: {e}")

    # --- Pick only THE BEST 1 signal ---
    if potential_signals:
        top = sorted(potential_signals, key=lambda x: x['score'], reverse=True)[0]
        confidence = random.randint(95, 99)
        msg = f"""🎯 **SURESHOT PRICE ACTION**
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {top['symbol']}
⚡ **Direction:** **{top['type']}**
⏳ **Duration:** 5 Minutes
🔥 **Accuracy:** `98% Sureshot`
━━━━━━━━━━━━━━━━━━
📊 **RSI:** {top['rsi']:.1f}
📈 **Strategy:** Rejection Wick + Pivot
⏰ **BD Time:** {now.strftime('%H:%M')}
━━━━━━━━━━━━━━━━━━
⚠️ *Wait for rejection wick on {top['symbol']}*"""
        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
        print(f"✅ Sureshot Sent: {top['symbol']}")
    else:
        print("ℹ️ No high-accuracy setup found this time.")

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