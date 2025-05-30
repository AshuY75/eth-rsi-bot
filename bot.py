print("🔍 Script started")
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
import schedule
import time
from datetime import datetime

# Initialize exchange (Binance)
exchange = ccxt.binance()

# Function to fetch and prepare 15m data
def fetch_data():
    bars = exchange.fetch_ohlcv('ETH/USDT', timeframe='15m', limit=100)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
    df['red_candle'] = df['close'] < df['open']
    return df

# Trading logic
def check_signals():
    df = fetch_data()
    last = df.iloc[-1]
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking signals...")
    print(f"Close: {last['close']:.2f}, RSI: {last['rsi']:.2f}, Red Candle: {last['red_candle']}")

    if last['rsi'] <= 30:
        print("🟢 BUY SIGNAL - RSI is below 30")

    elif last['rsi'] >= 70:
        print("🔴 SELL SIGNAL - RSI is above 70")

    if last['red_candle']:
        print("⚠️ CLOSE POSITION - Red candle formed")

# Schedule to run every 15 minutes
schedule.every(1).minutes.do(check_signals)

print("✅ ETH RSI Bot is running...")

while True:
    schedule.run_pending()
    time.sleep(1)
