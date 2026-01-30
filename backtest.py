# src/backtest.py
def run_backtest(df, cost=0.001):
    df["ret"] = df["Close"].pct_change()
    df["position"] = df["signal"].shift(1).fillna(0)

    df["strategy_ret"] = df["position"] * df["ret"]
    df["trade"] = df["position"].diff().abs().fillna(0)

    df["strategy_ret_net"] = df["strategy_ret"] - cost * df["trade"]
    df["equity"] = (1 + df["strategy_ret_net"]).cumprod()

    return df
