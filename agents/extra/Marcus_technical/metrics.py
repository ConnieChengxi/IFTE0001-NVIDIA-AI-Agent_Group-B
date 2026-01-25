# src/metrics.py
import numpy as np

def compute_metrics(df):
    equity = df["equity"].dropna()
    returns = df.loc[equity.index, "strategy_ret_net"]

    # CAGR
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1

    # Volatility & Sharpe
    vol = returns.std() * np.sqrt(252)
    sharpe = cagr / vol if vol != 0 else np.nan

    # Max Drawdown
    drawdown = equity / equity.cummax() - 1
    max_dd = drawdown.min()

    # Identify actual entries/exits from POSITION (not signal)
    pos = df.loc[equity.index, "position"].fillna(0)
    entry_idx = pos[(pos == 1) & (pos.shift(1) == 0)].index
    exit_idx  = pos[(pos == 0) & (pos.shift(1) == 1)].index

    # Align entries with exits (drop unmatched last entry if still open)
    n_trades = min(len(entry_idx), len(exit_idx))
    entry_idx = entry_idx[:n_trades]
    exit_idx = exit_idx[:n_trades]

    # Per-trade return from equity change between entry and exit
    trade_rets = []
    for ent, ex in zip(entry_idx, exit_idx):
        ent_eq = equity.loc[ent]
        ex_eq = equity.loc[ex]
        trade_rets.append(ex_eq / ent_eq - 1)

    trade_rets = np.array(trade_rets, dtype=float)
    hit_rate = float(np.mean(trade_rets > 0)) if len(trade_rets) > 0 else 0.0

    return {
        "CAGR": cagr,
        "Volatility": vol,
        "Sharpe": sharpe,
        "Max Drawdown": max_dd,
        "Number of Trades": int(n_trades),
        "Hit Rate": hit_rate
    }
