import numpy as np
import pandas as pd

from config import Config
from src.data_fetcher import av_get


def _to_float(x):
    try:
        return float(x)
    except Exception:
        return np.nan


def build_peer_multiples(cfg: Config, asof: pd.Timestamp) -> pd.DataFrame:
    """
    Peer multiples using Alpha Vantage OVERVIEW + statement fields where available.
    Outputs P/E, EV/EBITDA, EV/Sales.
    """
    rows = []
    for t in cfg.peers:
        ov = av_get("OVERVIEW", t, cache_dir=cfg.cache_dir)

        mcap = _to_float(ov.get("MarketCapitalization")) / 1e9
        pe = _to_float(ov.get("PERatio"))

        # Some tickers provide these in OVERVIEW; otherwise NaN
        ebitda = _to_float(ov.get("EBITDA")) / 1e9
        rev = _to_float(ov.get("RevenueTTM")) / 1e9

        cash = _to_float(ov.get("CashAndCashEquivalents")) / 1e9
        debt = _to_float(ov.get("TotalDebt")) / 1e9

        ev = np.nan
        if np.isfinite(mcap) and (np.isfinite(debt) or np.isfinite(cash)):
            ev = mcap + (debt if np.isfinite(debt) else 0.0) - (cash if np.isfinite(cash) else 0.0)

        ev_ebitda = ev / ebitda if (np.isfinite(ev) and np.isfinite(ebitda) and ebitda != 0) else np.nan
        ev_sales = ev / rev if (np.isfinite(ev) and np.isfinite(rev) and rev != 0) else np.nan

        rows.append({
            "Ticker": t,
            "MarketCap (USD bn)": mcap,
            "EV (USD bn)": ev,
            "P/E": pe,
            "EV/EBITDA": ev_ebitda,
            "EV/Sales": ev_sales,
        })

    df = pd.DataFrame(rows).set_index("Ticker")

    # Optional: add benchmark rows like your notebook
    # (keep as manual constants if you used those averages)
    df.loc["Semiconductor Avg"] = [np.nan, np.nan, 37.29, 42.70, 15.70]
    df.loc["S&P 500 Avg"] = [np.nan, np.nan, 27.66, 23.95, 3.97]

    return df

