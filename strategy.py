import pandas as pd
import numpy as np
import config
from auth import get_fyers_instance
import datetime
import time

def get_historical_data(fyers, symbol, resolution, range_from, range_to):
    """
    Fetches historical data from Fyers.
    """
    data = {
        "symbol": symbol,
        "resolution": resolution,
        "date_format": "1",
        "range_from": range_from,
        "range_to": range_to,
        "cont_flag": "1"
    }
    response = fyers.history(data=data)
    if response and response.get('s') == 'ok':
        df = pd.DataFrame(response.get('candles'), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        # Fyers returns timestamp in UTC, convert to IST if needed, but for EMAs it doesn't matter much as long as it's consistent
        return df
    else:
        print(f"Error fetching historical data: {response}")
        return None

def calculate_ema(df, period):
    return df['close'].ewm(span=period, adjust=False).mean()

def check_crossover(df):
    """
    Checks for EMA crossover.
    Returns: 'BULLISH' for 9 EMA crossing above 21 EMA
             'BEARISH' for 9 EMA crossing below 21 EMA
             None otherwise
    """
    if len(df) < 2:
        return None
    
    ema_fast = calculate_ema(df, config.EMA_FAST)
    ema_slow = calculate_ema(df, config.EMA_SLOW)
    
    prev_fast = ema_fast.iloc[-2]
    prev_slow = ema_slow.iloc[-2]
    curr_fast = ema_fast.iloc[-1]
    curr_slow = ema_slow.iloc[-1]
    
    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return 'BULLISH'
    elif prev_fast >= prev_slow and curr_fast < curr_slow:
        return 'BEARISH'
    
    return None

def get_current_signal(fyers, symbol):
    """
    Fetches recent data and checks for a signal.
    """
    now = datetime.datetime.now()
    range_to = now.strftime('%Y-%m-%d')
    range_from = (now - datetime.timedelta(days=5)).strftime('%Y-%m-%d')
    
    df = get_historical_data(fyers, symbol, config.TIME_FRAME, range_from, range_to)
    if df is not None:
        return check_crossover(df)
    return None

def add_mmr_indicators(df):
    """
    Calculates EMA, VWAP, ATR and PrevClose for MMR strategy.
    """
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()

    tp = (df["high"] + df["low"] + df["close"]) / 3
    df['date'] = df['timestamp'].dt.date
    df["CumVol"] = df.groupby('date')["volume"].cumsum()
    df["CumTPVol"] = (tp * df["volume"]).groupby(df['date']).cumsum()
    df["VWAP"] = df["CumTPVol"] / df["CumVol"]

    tr = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs()
        )
    )
    df["ATR"] = tr.rolling(14).mean()

    daily_close = df.groupby('date')["close"].last()
    prev_day_close = daily_close.shift(1)
    df["PrevClose"] = df['date'].map(prev_day_close)

    return df

def get_mmr_signal(stock_df, index_df):
    """
    Checks for MMR signal for a stock given index data.
    """
    if stock_df is None or index_df is None or len(stock_df) < 2 or len(index_df) < 2:
        return None

    # Get the latest completed candle for both
    # Assuming they are aligned by timestamp
    stock_row = stock_df.iloc[-1]

    # Match index row by timestamp
    try:
        index_row = index_df[index_df['timestamp'] == stock_row['timestamp']].iloc[0]
    except (IndexError, KeyError):
        return None

    index_long = index_row["EMA20"] > index_row["EMA50"]
    index_short = index_row["EMA20"] < index_row["EMA50"]

    close = stock_row["close"]
    high = stock_row["high"]
    low = stock_row["low"]
    open_ = stock_row["open"]
    atr = stock_row["ATR"]
    prev_close = stock_row["PrevClose"]

    if pd.isna(atr) or pd.isna(prev_close):
        return None

    gap = abs((open_ - prev_close) / prev_close * 100)
    expansion = (high - low) >= config.MMR_ATR_TRIGGER_MULT * atr

    if not (gap >= config.MMR_GAP_PCT or expansion):
        return None

    # Entry Logic
    if index_long and close > stock_row["VWAP"] and stock_row["EMA20"] > stock_row["EMA50"]:
        return 'BUY'
    elif index_short and close < stock_row["VWAP"] and stock_row["EMA20"] < stock_row["EMA50"]:
        return 'SELL'

    return None
