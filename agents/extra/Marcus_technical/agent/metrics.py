# src/metrics.py
import numpy as np

def compute_metrics(df):
    equity = df["equity"].dropna()
    returns = df.loc[equity.index, "strategy_ret_net"]

    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
    vol = returns.std() * np.sqrt(252)
    sharpe = cagr / vol

    drawdown = equity / equity.cummax() - 1
    max_dd = drawdown.min()

    trades = ((df["signal"] == 1) & (df["signal"].shift(1) == 0)).sum()

    return {
        "CAGR": cagr,
        "Volatility": vol,
        "Sharpe": sharpe,
        "Max Drawdown": max_dd,
        "Number of Trades": trades
    }
