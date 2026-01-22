# src/indicators.py
import pandas as pd

def add_ema(df, short=20, long=50):
    df["EMA_20"] = df["Close"].ewm(span=short, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=long, adjust=False).mean()
    return df

def add_rsi(df, window=14):
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(window).mean() / loss.rolling(window).mean()
    df["RSI_14"] = 100 - (100 / (1 + rs))
    return df

def add_atr(df, window=14):
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs()
    ], axis=1).max(axis=1)

    df["ATR_14"] = tr.rolling(window).mean()
    return df
