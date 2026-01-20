import pandas as pd
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
