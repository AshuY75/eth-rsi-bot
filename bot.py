print("🔍 Script started")
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import schedule
import time
from datetime import datetime
import requests
import json
import os

# Telegram config
TELEGRAM_TOKEN = "8081874806:AAEVgQpzGcOGUhW4Uj_8319aiNK18S-Z-7w"
CHAT_ID = "5990326636"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send message: {e}")

# Initialize exchange (Bybit)
exchange = ccxt.bybit({
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

# Symbols
symbols = ['ETH/USDT', 'BTC/USDT']

# Initialize trade log
trade_log = {symbol: [] for symbol in symbols}

# File for persistent log
TRADE_LOG_FILE = 'trade_log.json'

def save_trade_log():
    with open(TRADE_LOG_FILE, 'w') as f:
        json.dump(trade_log, f, default=str)

def load_trade_log():
    if os.path.exists(TRADE_LOG_FILE):
        with open(TRADE_LOG_FILE, 'r') as f:
            raw = json.load(f)
            for symbol in raw:
                trade_log[symbol] = [(datetime.fromisoformat(t[0]), t[1]) for t in raw[symbol]]

load_trade_log()

def fetch_data(symbol):
    bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
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

def analyze_and_alert(symbol):
    df = fetch_data(symbol)
    last = df.iloc[-1]

    msg_prefix = f"[{symbol}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    if last['rsi'] < 30 and last['close'] < last['bb_lower']:
        msg = msg_prefix + "🟢 Buy Signal: RSI < 30 and price below lower BB"
        send_telegram(msg)
        trade_log[symbol].append((datetime.now(), 'buy'))
        save_trade_log()

    elif last['rsi'] > 70 and last['close'] > last['bb_upper']:
        msg = msg_prefix + "🔴 Sell Signal: RSI > 70 and price above upper BB"
        send_telegram(msg)
        trade_log[symbol].append((datetime.now(), 'sell'))
        save_trade_log()

    # Exit logic
    if trade_log[symbol]:
        last_trade_type = trade_log[symbol][-1][1]
        if ((last_trade_type == 'buy' and last['red_candle']) or
            (last_trade_type == 'sell' and last['green_candle']) or
            (last['close'] > last['bb_mid'] if last_trade_type == 'buy' else last['close'] < last['bb_mid'])):
            msg = msg_prefix + "⚠️ Exit Signal: Opposite candle or mid BB cross"
            send_telegram(msg)
            trade_log[symbol].append((datetime.now(), 'exit'))
            save_trade_log()

def report_profitability():
    now = datetime.now()
    msg = f"📈 Daily Profitability Report ({now.strftime('%Y-%m-%d %H:%M')})\n"
    for symbol in symbols:
        signals = trade_log[symbol]
        buys = [t for t in signals if t[1] == 'buy']
        sells = [t for t in signals if t[1] == 'sell']
        exits = [t for t in signals if t[1] == 'exit']
        total = len(signals)
        profit_pct = (len(exits) / total * 100) if total else 0
        msg += f"{symbol}: {profit_pct:.2f}% profitable exits out of {total} trades.\n"
    send_telegram(msg)

# Verify symbols
markets = exchange.load_markets()
for symbol in symbols:
    status = "✅ Supported" if symbol in markets else "❌ Not Supported"
    print(f"{symbol} {status}")

# Schedule alerts
for symbol in symbols:
    schedule.every(30).seconds.do(analyze_and_alert, symbol=symbol)

schedule.every().day.at("09:00").do(report_profitability)
schedule.every().day.at("18:00").do(report_profitability)
schedule.every().hour.at(":00").do(report_profitability)

print("✅ RSI + BB Bot (Bybit) with Telegram Alerts is running...")
while True:
    schedule.run_pending()
    time.sleep(1)
