import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to a price DataFrame and return the enriched DataFrame."""
    data = df.copy()

    # Fix multi-index columns if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        print("successfully fixed：two layer -> one layer")

    # SMA
    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['SMA_200'] = data['Close'].rolling(window=200).mean()

    # RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    period = 14
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    data['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    k_fast = 12
    k_slow = 26
    k_signal = 9
    ema_fast = data['Close'].ewm(span=k_fast, adjust=False).mean()
    ema_slow = data['Close'].ewm(span=k_slow, adjust=False).mean()
    data['MACD_Line'] = ema_fast - ema_slow
    data['Signal_Line'] = data['MACD_Line'].ewm(span=k_signal, adjust=False).mean()
    data['MACD_Hist'] = data['MACD_Line'] - data['Signal_Line']

    # Bollinger Bands
    data['BB_Middle'] = data['Close'].rolling(window=20).mean()
    data['BB_Std'] = data['Close'].rolling(window=20).std()
    data['BB_Upper'] = data['BB_Middle'] + (2 * data['BB_Std'])
    data['BB_Lower'] = data['BB_Middle'] - (2 * data['BB_Std'])

    # ATR
    high_low = data['High'] - data['Low']
    high_close = (data['High'] - data['Close'].shift()).abs()
    low_close = (data['Low'] - data['Close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    data['ATR'] = true_range.rolling(window=14).mean()

    # OBV
    data['OBV'] = (np.sign(data['Close'].diff()) * data['Volume']).fillna(0).cumsum()

    data = data.dropna()

    print("indicator calculation completed")
    return data
