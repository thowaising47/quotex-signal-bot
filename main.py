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
    return "1-Min Sniper (Entry @ 00s) is Active!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "EUR/JPY"]

def check_1min_result(symbol, signal_type, entry_price):
    # Wait for the 1-min candle to close (60s + 5s buffer)
    time.sleep(65)
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=2&apikey={TWELVE_DATA_API_KEY}"
        data = requests.get(url).json()
        exit_price = float(data['values'][0]['close'])
        
        win = (exit_price > entry_price) if "CALL" in signal_type else (exit_price < entry_price)
        result_icon = "💰 WIN" if win else "❌ LOSS"
        
        bot.send_message(CHAT_ID, f"📊 **RESULT: {symbol}**\nResult: **{result_icon}**\nEntry: `{entry_price:.5f}` | Exit: `{exit_price:.5f}`")
    except: pass

def get_fast_signal():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"⚡ [SCAN START] {now.strftime('%H:%M:%S')}")
    
    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=15&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url, timeout=5).json()
            if 'values' not in res: continue
            
            df = pd.DataFrame(res['values'])
            df['close'] = pd.to_numeric(df['close'])
            df = df.iloc[::-1].reset_index(drop=True)

            # Scalping Indicators
            rsi = ta.momentum.RSIIndicator(df['close'], window=7).rsi().iloc[-1]
            price = df['close'].iloc[-1]

            signal_type = ""
            if rsi < 25: signal_type = "🟢 CALL (1-MIN)"
            elif rsi > 75: signal_type = "🔴 PUT (1-MIN)"

            if signal_type:
                msg = f"🚀 **ENTRY READY!**\n━━━━━━━━━━━━━━\n🏦 Asset: {symbol}\n⚡ Direction: **{signal_type}**\n⏳ Trade at: **:00 Seconds**\n⏰ BD Time: {now.strftime('%H:%M:%S')}\n━━━━━━━━━━━━━━"
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                threading.Thread(target=check_1min_result, args=(symbol, signal_type, price)).start()
                break
        except: continue

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        
        # Thik 50th second-e trigger hobe jate 00 second-e entry dewa jay
        # 2 minute por por: jemon 08:28:50, 08:30:50, 08:32:50
        if now.minute % 2 == 0 and now.second == 50:
            get_fast_signal()
            time.sleep(10) # Avoid double trigger
        elif (now.minute + 1) % 2 == 0 and now.second == 50:
            get_fast_signal()
            time.sleep(10)
            
        time.sleep(0.5)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))