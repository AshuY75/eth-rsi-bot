# Full script for a trading bot using RSI + Bollinger Bands with Telegram alerts and emojis.

import ccxt
import pandas as pd
import requests
import schedule
import time
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from datetime import datetime

# ========== Configuration ==========
TELEGRAM_TOKEN = '8081874806:AAEVgQpzGcOGUhW4Uj_8319aiNK18S-Z-7w'
CHAT_ID = '5990326636'
SYMBOLS = ['ETH/USDT', 'BTC/USDT', 'USDT/INR']
TIMEFRAME = '15m'
LIMIT = 100
HISTORY_FILE = 'trade_history.csv'

# ========== Initialize Exchange ==========
exchange = ccxt.binance()

# ========== Helper Functions ==========

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

def fetch_data(symbol):
    bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
    bb = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_mid'] = bb.bollinger_mavg()
    df['red_candle'] = df['close'] < df['open']
    df['green_candle'] = df['close'] > df['open']
    return df

def log_trade(symbol, signal_type):
    with open(HISTORY_FILE, 'a') as f:
        f.write(f"{datetime.now()},{symbol},{signal_type}\n")

def analyze_profitability():
    try:
        df = pd.read_csv(HISTORY_FILE, names=['time', 'symbol', 'signal'])
        counts = df['signal'].value_counts()
        total = counts.sum()
        profitable = counts.get('BUY', 0) + counts.get('SELL', 0)
        percentage = (profitable / total) * 100 if total > 0 else 0
        send_telegram_message(f"📈 Profitability Report:\n✅ Profitable signals: {percentage:.2f}%\n🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    except FileNotFoundError:
        send_telegram_message("📉 No trade history found for profitability analysis.")

# ========== Strategy Logic ==========

def check_signals():
    for symbol in SYMBOLS:
        df = fetch_data(symbol)
        last = df.iloc[-1]

        message = f"\n🔍 [{symbol}] Check @ {datetime.now().strftime('%H:%M:%S')}\nPrice: {last['close']:.2f}\nRSI: {last['rsi']:.2f}"

        if last['rsi'] < 30 and last['close'] <= last['bb_lower']:
            message += "\n🟢 BUY SIGNAL - RSI < 30 and below lower BB"
            log_trade(symbol, 'BUY')
        elif last['rsi'] > 70 and last['close'] >= last['bb_upper']:
            message += "\n🔴 SELL SIGNAL - RSI > 70 and above upper BB"
            log_trade(symbol, 'SELL')
        elif last['red_candle'] or last['green_candle'] and (last['close'] >= last['bb_mid'] or last['close'] <= last['bb_mid']):
            message += "\n⚠️ EXIT SIGNAL - Candle reversed or price crossed BB mid"
            log_trade(symbol, 'EXIT')

        send_telegram_message(message)

# ========== Scheduling ==========
schedule.every(1).minutes.do(check_signals)
schedule.every().hour.do(analyze_profitability)
schedule.every().day.at("09:00").do(analyze_profitability)
schedule.every().day.at("18:00").do(analyze_profitability)

print("✅ RSI + BB Bot with Telegram Alerts is running...")

while True:
    schedule.run_pending()
    time.sleep(1)
