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
    return "Psychology-Based Bot is Active!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

def check_final_result(symbol, signal_type, entry_price):
    time.sleep(605) # 10 min + buffer
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=1&apikey={TWELVE_DATA_API_KEY}"
        data = requests.get(url).json()
        exit_price = float(data['values'][0]['close'])
        win = (exit_price > entry_price) if "CALL" in signal_type else (exit_price < entry_price)
        bot.send_message(CHAT_ID, f"📊 **PSYCHOLOGY RESULT: {symbol}**\nResult: {'✅ WIN' if win else '❌ LOSS'}\nEntry: `{entry_price:.5f}` | Exit: `{exit_price:.5f}`")
    except: pass

def get_psychology_signal():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🧠 [PSYCHOLOGY SCAN] {now.strftime('%H:%M:%S')}")
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=50&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url, timeout=10).json()
            if 'values' not in res: continue
            
            df = pd.DataFrame(res['values'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['open'] = pd.to_numeric(df['open'])
            df = df.iloc[::-1].reset_index(drop=True)

            price = df['close'].iloc[-1]
            high = df['high'].iloc[-1]
            low = df['low'].iloc[-1]
            open_p = df['open'].iloc[-1]
            
            # 1. Exhaustion Logic: Porpor 3-4 ta green/red candle
            last_3_candles = df.iloc[-3:]
            is_exhausted_up = all(last_3_candles['close'] > last_3_candles['open'])
            is_exhausted_down = all(last_3_candles['close'] < last_3_candles['open'])

            # 2. Rejection Logic: 40% wick rejection
            upper_wick = (high - max(open_p, price))
            lower_wick = (min(open_p, price) - low)
            body_size = abs(price - open_p) + 0.000001
            
            signal_type = ""
            
            # CALL Strategy: Price rejection at bottom after sellers are exhausted
            if is_exhausted_down and lower_wick > body_size * 1.5:
                signal_type = "🟢 CALL (UP) - Trap Detected"
            
            # PUT Strategy: Price rejection at top after buyers are exhausted
            elif is_exhausted_up and upper_wick > body_size * 1.5:
                signal_type = "🔴 PUT (DOWN) - Trap Detected"

            if signal_type:
                msg = f"""🧠 **PSYCHOLOGY SIGNAL (TRAP)**
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {symbol}
⚡ **Direction:** **{signal_type}**
⏳ **Duration:** 10 Minutes
━━━━━━━━━━━━━━━━━━
📊 **Logic:** Exhaustion & Rejection
⏰ **BD Time:** {now.strftime('%H:%M')}
━━━━━━━━━━━━━━━━━━"""
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                threading.Thread(target=check_final_result, args=(symbol, signal_type, price)).start()
                break
            time.sleep(5)
        except: continue

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        if now.minute % 10 == 0 and now.second == 0:
            get_psychology_signal()
            time.sleep(60)
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))