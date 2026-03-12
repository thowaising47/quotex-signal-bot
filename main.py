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
    return "10-Min Trade with 1-Min Update Bot is Active!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

# --- Result Tracking System ---
def process_result(symbol, signal_type, entry_price):
    # 1. Early Update after 1 Minute
    time.sleep(60) 
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=1&apikey={TWELVE_DATA_API_KEY}"
        data = requests.get(url).json()
        current_price = float(data['values'][0]['close'])
        
        status = "✅ IN PROFIT" if (("CALL" in signal_type and current_price > entry_price) or ("PUT" in signal_type and current_price < entry_price)) else "❌ IN LOSS"
        
        bot.send_message(CHAT_ID, f"⏱ **1-MIN UPDATE: {symbol}**\nStatus: **{status}**\nCurrent Price: `{current_price:.5f}`")
    except: pass

    # 2. Final Result after 10 Minutes (Total)
    time.sleep(540) # Remaining 9 minutes
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=1&apikey={TWELVE_DATA_API_KEY}"
        data = requests.get(url).json()
        final_price = float(data['values'][0]['close'])
        
        win = (final_price > entry_price) if "CALL" in signal_type else (final_price < entry_price)
        result_icon = "✅ FINAL WIN" if win else "❌ FINAL LOSS"
        
        bot.send_message(CHAT_ID, f"📊 **FINAL RESULT: {symbol}**\nResult: **{result_icon}**\nEntry: `{entry_price:.5f}`\nExit: `{final_price:.5f}`")
    except: pass

def get_signal_10min():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=40&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url, timeout=10).json()
            if 'values' not in res: continue
            
            df = pd.DataFrame(res['values'])
            df['close'] = pd.to_numeric(df['close'])
            df = df.iloc[::-1].reset_index(drop=True)

            # Strategy: EMA 20 + RSI (Balanced for 10-min)
            ema20 = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator().iloc[-1]
            rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi().iloc[-1]
            price = df['close'].iloc[-1]

            signal_type = ""
            if price > ema20 and rsi < 38: signal_type = "🟢 CALL (UP)"
            elif price < ema20 and rsi > 62: signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                msg = f"🎯 **10-MIN VIP SIGNAL**\n🏦 Asset: {symbol}\n⚡ Direction: **{signal_type}**\n⏳ Duration: 10 Min\n⏰ BD Time: {now.strftime('%H:%M')}"
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                threading.Thread(target=process_result, args=(symbol, signal_type, price)).start()
                break 
            time.sleep(5)
        except: continue

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        if now.minute % 10 == 0 and now.second == 0:
            get_signal_10min()
            time.sleep(60)
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))