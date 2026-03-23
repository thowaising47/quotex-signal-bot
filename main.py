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
    return "Pro Sniper 1-Min is Online!"

# পেয়ার সংখ্যা বাড়ালাম যাতে সিগন্যাল মিস না হয়
PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "EUR/JPY", "GBP/JPY", "EUR/GBP"]

def get_pro_signal():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🚀 [SCANNING] {now.strftime('%H:%M:%S')}")
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=30&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url, timeout=5).json()
            if 'values' not in res: continue
            
            df = pd.DataFrame(res['values'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df = df.iloc[::-1].reset_index(drop=True)

            # --- Pro Logic ---
            rsi = ta.momentum.RSIIndicator(df['close'], window=7).rsi().iloc[-1]
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            bb_h, bb_l = bb.bollinger_hband().iloc[-1], bb.bollinger_lband().iloc[-1]
            
            price = df['close'].iloc[-1]
            signal_type = ""

            # 🟢 CALL: Price hit Lower BB + RSI < 30
            if price <= bb_l and rsi < 32:
                signal_type = "🟢 CALL (UP)"
            # 🔴 PUT: Price hit Upper BB + RSI > 70
            elif price >= bb_h and rsi > 68:
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                msg = f"💎 **PRO SNIPER SIGNAL**\n━━━━━━━━━━━━━━\n🏦 Asset: {symbol}\n⚡ Direction: **{signal_type}**\n⏳ Entry: **:00 Seconds**\n⏰ BD Time: {now.strftime('%H:%M:%S')}\n━━━━━━━━━━━━━━"
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                break # ১টা ভালো সিগন্যাল পাওয়ামাত্র স্ক্যান থামাবে
            time.sleep(0.5)
        except: continue

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        
        # আপনার চাওয়া অনুযায়ী ঠিক ৫০ সেকেন্ডে স্ক্যান (যাতে ০০ তে এন্ট্রি নিতে পারেন)
        # ২ মিনিট পর পর: ৬:১৪:৫০, ৬:১৬:৫০, ৬:১৮:৫০...
        if now.minute % 2 == 0 and now.second == 50:
            get_pro_signal()
            time.sleep(10) # ডাবল ট্রিগার বন্ধ করতে
        time.sleep(0.5)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))