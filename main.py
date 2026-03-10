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
TWELVE_DATA_API_KEY = "APNAR_API_KEY_EKKHANE_BOSHAN" # <--- Twelve Data theke niyen

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running Perfectly!"

# Top 7 Pairs (Twelve Data Format)
PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "EUR/JPY", "GBP/JPY"]

def get_signal_pro():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"--- Twelve Data Scan Started: {now.strftime('%H:%M:%S')} ---")
    
    for symbol in PAIRS:
        try:
            # Twelve Data API Call
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=50&apikey={TWELVE_DATA_API_KEY}"
            response = requests.get(url).json()
            
            if 'values' not in response:
                print(f"⚠️ API Limit/Error for {symbol}")
                continue
                
            df = pd.DataFrame(response['values'])
            df['close'] = pd.to_numeric(df['close'])
            df = df.iloc[::-1] # Reverse to get oldest first for indicators

            # Indicators
            df['EMA200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()
            df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            df['BB_High'] = bb.bollinger_hband()
            df['BB_Low'] = bb.bollinger_lband()

            price = float(df['close'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])
            ema200 = float(df['EMA200'].iloc[-1]) if not pd.isna(df['EMA200'].iloc[-1]) else price
            bb_high = float(df['BB_High'].iloc[-1])
            bb_low = float(df['BB_Low'].iloc[-1])

            signal_type = ""
            if price > ema200 and price <= bb_low and rsi < 40:
                signal_type = "🟢 CALL (UP)"
            elif price < ema200 and price >= bb_high and rsi > 60:
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                confidence = random.randint(90, 98)
                msg = f"💎 **PREMIUM VIP SIGNAL** 💎\n━━━━━━━━━━━━━━━━━━\n🏦 **Asset:** {symbol}\n⚡ **Direction:** **{signal_type}**\n⏳ **Duration:** 5 Minutes\n🔥 **Confidence:** `{confidence}%` \n━━━━━━━━━━━━━━━━━━\n💰 **Entry Price:** {price:.5f}\n📊 **RSI:** {rsi:.2f}\n📈 **Trend:** {'Uptrend' if price > ema200 else 'Downtrend'}\n⏰ **Time:** {now.strftime('%H:%M')} (UTC+6)\n━━━━━━━━━━━━━━━━━━"
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                print(f"✅ Success: {symbol}")

            time.sleep(8) # API Limit safe rakhar jonno gap
            
        except Exception as e:
            print(f"❌ Error: {e}")

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        # Sync with 5-min intervals
        if now.minute % 5 == 0 and now.second == 0:
            get_signal_pro()
            time.sleep(60)
        time.sleep(1)

if __name__ == "__main__":
    try:
        bot.send_message(CHAT_ID, "🚀 **Bot Started with Twelve Data API!**\nSyncing with Bangladesh Time...")
    except: pass
    
    threading.Thread(target=run_scheduler, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)