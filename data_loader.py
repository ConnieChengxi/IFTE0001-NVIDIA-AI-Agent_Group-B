# src/data_loader.py
import yfinance as yf
import pandas as pd

def load_nvda(start="2016-01-01"):
    df = yf.download("NVDA", start=start, progress=False)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    return df
