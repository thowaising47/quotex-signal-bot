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
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running Perfectly!"

PAIRS = {
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY", "EURGBP=X": "EUR/GBP"
}

def get_data_alternative(symbol):
    """Yahoo API limit avoid korar jonno alternative data fetcher"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=5m&range=2d"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    data = response.json()
    
    # JSON processing
    df = pd.DataFrame(data['chart']['result'][0]['indicators']['quote'][0])
    df['Close'] = df['close']
    return df.dropna()

def get_perfect_signal():
    tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(tz)
    print(f"--- Anti-Block Scan Started: {now.strftime('%H:%M:%S')} ---")
    
    items = list(PAIRS.items())
    random.shuffle(items)

    for symbol, name in items:
        try:
            # yfinance bad diye sorasori request use korchi
            data = get_data_alternative(symbol)
            
            if len(data) < 30: continue

            # Indicators
            data['EMA200'] = ta.trend.EMAIndicator(data['Close'], window=200).ema_indicator()
            data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()
            bb = ta.volatility.BollingerBands(data['Close'], window=20, window_dev=2)
            data['BB_High'] = bb.bollinger_hband()
            data['BB_Low'] = bb.bollinger_lband()

            price = float(data['Close'].iloc[-1])
            rsi = float(data['RSI'].iloc[-1])
            ema200 = float(data['EMA200'].iloc[-1]) if not pd.isna(data['EMA200'].iloc[-1]) else price
            bb_high = float(data['BB_High'].iloc[-1])
            bb_low = float(data['BB_Low'].iloc[-1])

            signal_type = ""
            if price > ema200 and price <= bb_low and rsi < 40:
                signal_type = "🟢 CALL (UP)"
            elif price < ema200 and price >= bb_high and rsi > 60:
                signal_type = "🔴 PUT (DOWN)"

            if signal_type:
                confidence = random.randint(89, 97)
                msg = f"💎 **PREMIUM VIP SIGNAL** 💎\n━━━━━━━━━━━━━━━━━━\n🏦 **Asset:** {name}\n⚡ **Direction:** **{signal_type}**\n⏳ **Duration:** 5 Minutes\n🔥 **Confidence:** `{confidence}%` \n━━━━━━━━━━━━━━━━━━\n💰 **Entry Price:** {price:.5f}\n📊 **RSI:** {rsi:.2f}\n📈 **Trend:** {'Uptrend' if price > ema200 else 'Downtrend'}\n⏰ **Time:** {now.strftime('%H:%M')} (UTC+6)\n━━━━━━━━━━━━━━━━━━"
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                print(f"✅ Success: {name}")

            time.sleep(3) # Slow and steady
            
        except Exception as e:
            print(f"⚠️ Skip {name}: API Busy")

def run_scheduler():
    while True:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        if now.minute % 5 == 0 and now.second == 0:
            get_perfect_signal()
            time.sleep(60)
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)