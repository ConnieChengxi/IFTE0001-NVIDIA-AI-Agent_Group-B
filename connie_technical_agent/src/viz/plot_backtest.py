# plot_backtest.py
import os
import matplotlib.pyplot as plt
import pandas as pd

def plot_equity_and_drawdown(df: pd.DataFrame, ticker: str, outpath: str):
    outdir = os.path.dirname(outpath)
    if outdir:
        os.makedirs(outdir, exist_ok=True)

    equity = df["equity"]
    peak = equity.cummax()
    drawdown = equity / peak - 1.0

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

    ax1.plot(df.index, equity, label="Equity")
    ax1.set_title(f"{ticker} Backtest Equity")
    ax1.legend()

    ax2.plot(df.index, drawdown, label="Drawdown")
    ax2.axhline(y=0)
    ax2.legend()

    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close(fig)
