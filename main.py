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
    return "Bot is in Trend-Follower Mode!"

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]

def get_signal_pro():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"🚀 [SCAN] Trend Scan: {now.strftime('%H:%M:%S')}")
    
    signals = []

    for symbol in PAIRS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=30&apikey={TWELVE_DATA_API_KEY}"
            response = requests.get(url, timeout=10).json()
            
            if 'values' not in response: continue
                
            df = pd.DataFrame(response['values'])
            df['close'] = pd.to_numeric(df['close'])
            df['open'] = pd.to_numeric(df['open'])
            df = df.iloc[::-1].reset_index(drop=True)

            # EMA for Trend direction
            df['EMA_Fast'] = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
            df['EMA_Slow'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()

            price = float(df['close'].iloc[-1])
            open_p = float(df['open'].iloc[-1])
            ema_f = float(df['EMA_Fast'].iloc[-1])
            ema_s = float(df['EMA_Slow'].iloc[-1])

            signal_type = ""
            # CALL: Trend is UP (EMA Fast > Slow) + Candle is Green
            if ema_f > ema_s and price > open_p:
                signal_type = "🟢 CALL (UP)"
            # PUT: Trend is DOWN (EMA Fast < Slow) + Candle is Red
            elif ema_f < ema_s and price < open_p:
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                signals.append({'symbol': symbol, 'type': signal_type, 'price': price})
            
            time.sleep(5) 
        except Exception as e:
            print(f"❌ Error {symbol}: {e}")

    # Top 1 Signal with logic
    if signals:
        top = signals[0] 
        msg = f"""🎯 **SURESHOT TREND SIGNAL**
━━━━━━━━━━━━━━━━━━
🏦 **Asset:** {top['symbol']}
⚡ **Direction:** **{top['type']}**
⏳ **Duration:** 5 Minutes
━━━━━━━━━━━━━━━━━━
📈 **Strategy:** EMA Cross + Momentum
⏰ **BD Time:** {now.strftime('%H:%M')}
━━━━━━━━━━━━━━━━━━
⚠️ *Follow the current candle trend!*"""
        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
        print(f"✅ Signal Sent: {top['symbol']}")

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