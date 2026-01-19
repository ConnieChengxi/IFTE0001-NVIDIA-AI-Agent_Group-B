import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

from src.signals.signal import build_signals
from src.backtest.backtest import run_backtest
from src.viz.plot_backtest import plot_equity_and_drawdown
from src.viz.visualisation import plot_macd, plot_strategy_rsi, plot_strategy_shortterm
from src.reporting.llm_report import build_evidence_pack, llm_generate_trade_note
from src.viz.equity import plot_equity_log, plot_drawdown_compare

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance sometimes returns MultiIndex columns; flatten to single level."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # In some environments columns can be tuples; flatten defensively
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.columns.name = None
    return df


def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))

    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # Handle edge cases deterministically
    rsi = rsi.where(~(avg_loss == 0), 100)
    rsi = rsi.where(~(avg_gain == 0), 0)
    return rsi


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist


def _infer_equity_column(out: pd.DataFrame) -> str | None:
    """
    Try to infer which column in `out` is the equity curve.
    Works across slightly different backtest output schemas.
    """
    candidates = [
        "equity",
        "Equity",
        "portfolio_value",
        "Portfolio_Value",
        "portfolio",
        "Portfolio",
        "value",
        "Value",
        "PortfolioValue",
    ]
    for c in candidates:
        if c in out.columns:
            return c

    # Fallback: choose a numeric column that looks like a value series
    numeric_cols = [c for c in out.columns if pd.api.types.is_numeric_dtype(out[c])]
    if not numeric_cols:
        return None

    # Heuristic: prefer columns containing 'equity' or 'value'
    preferred = [c for c in numeric_cols if ("equity" in str(c).lower() or "value" in str(c).lower())]
    return preferred[0] if preferred else numeric_cols[0]


@dataclass
class DemoConfig:
    ticker: str = "NVDA"
    period: str = "10y"
    interval: str = "1d"
    auto_adjust: bool = True
    outdir: str = "outputs"
    plot: bool = True
    llm: bool = True
    llm_model: str = "gpt-4.1-mini"


def run_pipeline(cfg: DemoConfig):
    ensure_dir(cfg.outdir)

    # Step 1: Download data
    df = yf.download(
        cfg.ticker,
        period=cfg.period,
        interval=cfg.interval,
        auto_adjust=cfg.auto_adjust,
        progress=True,
    )
    df = flatten_columns(df).sort_index()

    # Step 2: Features
    df["RSI_14"] = compute_rsi(df["Close"], 14)
    df["MA20"] = df["Close"].rolling(20, min_periods=20).mean()
    df["MA50"] = df["Close"].rolling(50, min_periods=50).mean()
    df["MA200"] = df["Close"].rolling(200, min_periods=200).mean()

    macd, macd_signal, macd_hist = compute_macd(df["Close"])
    df["MACD"] = macd
    df["MACD_Signal"] = macd_signal
    df["MACD_Hist"] = macd_hist

    # Step 3: Signals
    df = df.dropna(subset=["MA200", "MACD", "MACD_Signal", "RSI_14"]).copy()
    df = build_signals(df)
    df = flatten_columns(df)

    df["entry"] = df["entry"].fillna(False).astype(bool)
    df["exit"] = df["exit"].fillna(False).astype(bool)

    # Step 4: Backtest
    out, trade, metrics = run_backtest(df)

    # ---- Step 4.1: Add "equity multiple" + Buy&Hold multiple (both start at 1.0) ----
    equity_col = _infer_equity_column(out)
    if equity_col is None:
        print("WARN: Could not infer equity column from backtest output. "
              "Skipping EquityMultiple/BuyHoldMultiple and compare plot.")
    else:
        equity = out[equity_col].astype(float).dropna()
        close = df["Close"].astype(float).reindex(equity.index).dropna()

        if len(equity) >= 2 and float(equity.iloc[0]) != 0.0:
            equity_multiple = float(equity.iloc[-1] / equity.iloc[0])
        else:
            equity_multiple = float("nan")

        if len(close) >= 2 and float(close.iloc[0]) != 0.0:
            bh_multiple = float(close.iloc[-1] / close.iloc[0])
        else:
            bh_multiple = float("nan")

        metrics["EquityColumn"] = equity_col
        metrics["EquityStart"] = float(equity.iloc[0]) if len(equity) else None
        metrics["EquityEnd"] = float(equity.iloc[-1]) if len(equity) else None
        metrics["EquityMultiple"] = equity_multiple
        metrics["BuyHoldMultiple"] = bh_multiple

    # Persist metrics + config for reproducibility
    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    cfg_path = os.path.join(cfg.outdir, f"{cfg.ticker}_run_config_{run_stamp}.json")
    met_path = os.path.join(cfg.outdir, f"{cfg.ticker}_metrics_{run_stamp}.json")

    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, indent=2)

    with open(met_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, default=str)

    # Step 5: Visualisation
    equity_path = os.path.join(cfg.outdir, f"{cfg.ticker}_equity_drawdown.png")
    plot_equity_and_drawdown(out, cfg.ticker, equity_path)

    # ---- Step 5.1: Plot normalized strategy vs Buy&Hold (start = 1.0) ----
    compare_path = os.path.join(cfg.outdir, f"{cfg.ticker}_strategy_vs_bh_norm.png")
    if equity_col is not None and equity_col in out.columns:
        try:
            import matplotlib.pyplot as plt

            equity = out[equity_col].astype(float).dropna()
            close = df["Close"].astype(float).reindex(equity.index).dropna()

            if len(equity) >= 2 and len(close) >= 2:
                equity_norm = equity / float(equity.iloc[0])
                close_norm = close / float(close.iloc[0])

                plt.figure()
                plt.plot(equity_norm.index, equity_norm.values, label="Strategy (start=1.0)")
                plt.plot(close_norm.index, close_norm.values, label=f"{cfg.ticker} Buy&Hold (start=1.0)")
                plt.legend()
                plt.title(f"Normalized Growth: Strategy vs {cfg.ticker} Buy&Hold")
                plt.savefig(compare_path, dpi=200, bbox_inches="tight")
                plt.close()
        except Exception as e:
            print(f"WARN: Failed to create normalized compare plot: {e}")

    if cfg.plot:
        # Keep plots lightweight; avoid generating 5+ charts by default
        plot_macd(out, cfg.ticker)

    # ---- Step 5.2: Log-scale equity + drawdown compare (more "tech") ----
    if equity_col is not None and equity_col in out.columns:
        equity = out[equity_col].astype(float).dropna()
        close = df["Close"].astype(float).reindex(equity.index).dropna()

        if len(equity) >= 2 and len(close) >= 2:
            equity_strat = equity / float(equity.iloc[0])
            equity_bh = close / float(close.iloc[0])

            log_path = os.path.join(cfg.outdir, f"{cfg.ticker}_equity_log_compare.png")
            dd_path  = os.path.join(cfg.outdir, f"{cfg.ticker}_drawdown_compare.png")

            plot_equity_log(
                bh=equity_bh,
                strat=equity_strat,
                title=f"{cfg.ticker}: Buy&Hold vs Strategy (Log Scale)",
                path=log_path,
            )

            plot_drawdown_compare(
                bh=equity_bh,
                strat=equity_strat,
                title=f"{cfg.ticker}: Drawdown Comparison",
                path=dd_path,
            )


    # LLM reporting (optional)
    md_path = os.path.join(cfg.outdir, f"{cfg.ticker}_trade_note_llm.md")
    llm_note = None

    if cfg.llm:
        api_key_present = bool(os.getenv("OPENAI_API_KEY"))
        if not api_key_present:
            print("INFO: OPENAI_API_KEY not set; skipping LLM trade note generation.")
        else:
            chart_paths = {"equity_drawdown": equity_path, "strategy_vs_bh": compare_path}
            evidence = build_evidence_pack(out, trade, metrics, cfg.ticker, chart_paths=chart_paths)
            llm_note = llm_generate_trade_note(evidence, model=cfg.llm_model)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(llm_note)

    artifacts = {
        "equity_drawdown_png": equity_path,
        "strategy_vs_bh_png": compare_path if os.path.exists(compare_path) else None,
        "metrics_json": met_path,
        "run_config_json": cfg_path,
        "llm_trade_note_md": md_path if llm_note else None,
        "equity_log_compare_png": log_path if os.path.exists(log_path) else None,
        "drawdown_compare_png": dd_path if os.path.exists(dd_path) else None,
    }

    return df, out, trade, metrics, artifacts


def main():
    parser = argparse.ArgumentParser(description="Run the Tech Analyst Agent demo pipeline.")
    parser.add_argument("--ticker", type=str, default="NVDA")
    parser.add_argument("--period", type=str, default="10y")
    parser.add_argument("--interval", type=str, default="1d")
    parser.add_argument("--outdir", type=str, default="outputs")
    parser.add_argument("--no-plot", action="store_true", help="Disable visualisations.")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM trade note generation.")
    parser.add_argument("--llm-model", type=str, default="gpt-4.1-mini")

    args = parser.parse_args()
    cfg = DemoConfig(
        ticker=args.ticker,
        period=args.period,
        interval=args.interval,
        outdir=args.outdir,
        plot=not args.no_plot,
        llm=not args.no_llm,
        llm_model=args.llm_model,
    )

    df, out, trade, metrics, artifacts = run_pipeline(cfg)

    # Clean, sell-side style terminal summary
    print("\n=== SUMMARY ===")
    for k in ["CAGR", "Sharpe", "MaxDrawdown", "HitRate", "NumTrades", "EquityMultiple", "BuyHoldMultiple"]:
        if k in metrics:
            print(f"{k}: {metrics[k]}")

    # Small interpretability lines (optional)
    if "EquityMultiple" in metrics and "BuyHoldMultiple" in metrics:
        try:
            em = float(metrics["EquityMultiple"])
            bm = float(metrics["BuyHoldMultiple"])
            if np.isfinite(em) and np.isfinite(bm):
                print(f"\nStrategy vs Buy&Hold (multiple): {em:.2f}x vs {bm:.2f}x")
        except Exception:
            pass

    print("\n=== ARTIFACTS ===")
    for k, v in artifacts.items():
        if v:
            print(f"{k}: {v}")

if __name__ == "__main__":
    main()
