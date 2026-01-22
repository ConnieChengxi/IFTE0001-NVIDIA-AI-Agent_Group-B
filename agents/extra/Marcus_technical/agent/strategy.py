# src/strategy.py
def generate_signal(df):
    trend = df["EMA_20"] > df["EMA_50"]
    rsi_filter = df["RSI_14"] < 70
    df["signal"] = (trend & rsi_filter).astype(int)
    return df
