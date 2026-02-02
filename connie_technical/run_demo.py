import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

# Load .env from Hybrid root (parent directory) or local
PROJECT_ROOT = Path(__file__).parent
HYBRID_ROOT = PROJECT_ROOT.parent

if (HYBRID_ROOT / ".env").exists():
    load_dotenv(HYBRID_ROOT / ".env")
else:
    load_dotenv(PROJECT_ROOT / ".env")

from src.signals.signal import build_signals
from src.backtest.backtest import run_backtest
from src.reporting.llm_report import (
    build_evidence_pack,
    llm_generate_trade_note,
    llm_generate_full_report,
)
from src.reporting.pdf_report import generate_pdf_report
from src.viz.equity import plot_combined_equity_drawdown, plot_equity_log, plot_drawdown_compare
from src.viz.trade_timeline import plot_golden_cross_with_trades
from src.viz.price_ma_macd import plot_price_ma_macd



# Fallback company names for common tickers
COMPANY_NAMES = {
    "NVDA": "NVIDIA Corporation",
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "GOOG": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "META": "Meta Platforms Inc.",
    "TSLA": "Tesla Inc.",
    "AMD": "Advanced Micro Devices Inc.",
    "INTC": "Intel Corporation",
}


def get_company_name(ticker: str) -> str:
    """Get company name from yfinance, with fallback to predefined mapping."""
    try:
        info = yf.Ticker(ticker).info
        name = info.get("longName") or info.get("shortName")
        if name:
            return name
    except (KeyError, AttributeError, ConnectionError, TimeoutError):
        # API errors or network issues - fall back to mapping
        pass
    return COMPANY_NAMES.get(ticker.upper(), ticker)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_json(obj, path: str) -> None:
    """Safe JSON writer for evidence/config/metrics (no dependency on llm_report.py helpers)."""
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)


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
    ticker: str  # Required, no default
    period: str = "10y"
    interval: str = "1d"
    auto_adjust: bool = True
    outdir: str = "outputs"
    plot: bool = True
    llm: bool = True
    llm_model: str = "gpt-4o-mini"


def run_pipeline(cfg: DemoConfig):
    """Execute the full technical analysis pipeline."""
    ensure_dir(cfg.outdir)

    # Get company name for report title
    company_name = get_company_name(cfg.ticker)
    print(f"Company: {company_name} ({cfg.ticker})")

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

    # Backtest
    out, trade, metrics = run_backtest(df)

    # Add equity multiple and buy-and-hold multiple
    equity_col = _infer_equity_column(out)
    if equity_col is None:
        print(
            "WARN: Could not infer equity column from backtest output. "
            "Skipping EquityMultiple/BuyHoldMultiple and compare plot."
        )
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
        metrics["EquityEnd"] = round(float(equity.iloc[-1]), 2) if len(equity) else None
        metrics["EquityMultiple"] = equity_multiple
        metrics["BuyHoldMultiple"] = bh_multiple

        # Buy-and-hold max drawdown for comparison
        if len(close) >= 2:
            close_norm = close / float(close.iloc[0])
            bh_peak = close_norm.cummax()
            bh_drawdown = (close_norm / bh_peak) - 1.0
            metrics["BuyHoldMaxDrawdown"] = round(float(bh_drawdown.min()) * 100, 2)

    # Persist metrics + config for reproducibility
    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    cfg_path = os.path.join(cfg.outdir, f"{cfg.ticker}_run_config_{run_stamp}.json")
    met_path = os.path.join(cfg.outdir, f"{cfg.ticker}_metrics_{run_stamp}.json")

    save_json(asdict(cfg), cfg_path)
    save_json(metrics, met_path)

    # Step 5: Visualisation - Combined equity & drawdown comparison (strategy vs buy-and-hold)
    equity_path = os.path.join(cfg.outdir, f"{cfg.ticker}_equity_drawdown.png")
    equity_log_path = os.path.join(cfg.outdir, f"{cfg.ticker}_equity_log_compare.png")
    drawdown_compare_path = os.path.join(cfg.outdir, f"{cfg.ticker}_drawdown_compare.png")

    if equity_col is not None and equity_col in out.columns:
        try:
            equity = out[equity_col].astype(float).dropna()
            close = df["Close"].astype(float).reindex(equity.index).dropna()

            if len(equity) >= 2 and len(close) >= 2:
                equity_strat = equity / float(equity.iloc[0])
                equity_bh = close / float(close.iloc[0])
                # Combined chart
                plot_combined_equity_drawdown(equity_bh, equity_strat, cfg.ticker, equity_path)
                # Separate equity log chart for hybrid report
                plot_equity_log(equity_bh, equity_strat, f"{cfg.ticker} Buy&Hold vs Strategy (Log Scale)", equity_log_path)
                # Separate drawdown comparison chart for hybrid report
                plot_drawdown_compare(equity_bh, equity_strat, f"{cfg.ticker} Drawdown Comparison", drawdown_compare_path)
        except Exception as e:
            print(f"WARN: Failed to create equity/drawdown plots: {e}")
            equity_log_path = None
            drawdown_compare_path = None

    # Golden Cross + Trade timeline
    gc_path = os.path.join(cfg.outdir, f"{cfg.ticker}_golden_cross_trades.png")
    try:
        plot_golden_cross_with_trades(df=df, ticker=cfg.ticker, path=gc_path)
    except Exception as e:
        print(f"WARN: Failed to create golden cross + trades plot: {e}")
        gc_path = None

    # Price + MAs + MACD (6 months)
    price_macd_6m_path = os.path.join(cfg.outdir, f"{cfg.ticker}_price_ma_macd_6m.png")
    try:
        df_6m = df.copy().sort_index()
        end = df_6m.index.max()
        start = end - pd.Timedelta(days=182)
        df_6m = df_6m.loc[(df_6m.index >= start) & (df_6m.index <= end)]

        plot_price_ma_macd(
            df=df_6m,
            ticker=cfg.ticker,
            path=price_macd_6m_path,
            ma_cols=("MA20", "MA50", "MA200"),
        )
    except Exception as e:
        print(f"WARN: Failed to create 6M price+MA+MACD plot: {e}")
        price_macd_6m_path = None

    # Evidence pack
    md_path = os.path.join(cfg.outdir, f"{cfg.ticker}_trade_note_llm.md")
    final_md_path = os.path.join(cfg.outdir, f"{cfg.ticker}_final_report_llm.md")
    evi_path = os.path.join(cfg.outdir, f"{cfg.ticker}_evidence.json")

    llm_note = None
    final_report = None
    evidence = None
    pdf_path = None

    # Build chart paths dict
    chart_paths = {}
    if equity_path and os.path.exists(equity_path):
        chart_paths["equity_drawdown"] = equity_path
    if gc_path and os.path.exists(gc_path):
        chart_paths["golden_cross_trades"] = gc_path
    if price_macd_6m_path and os.path.exists(price_macd_6m_path):
        chart_paths["price_ma_macd_6m"] = price_macd_6m_path
    # Separate charts for hybrid report
    if equity_log_path and os.path.exists(equity_log_path):
        chart_paths["equity_log_compare"] = equity_log_path
    if drawdown_compare_path and os.path.exists(drawdown_compare_path):
        chart_paths["drawdown_compare"] = drawdown_compare_path

    # Always build and save evidence pack (for hybrid integration)
    evidence = build_evidence_pack(
        out=out,
        trades=trade,
        metrics=metrics,
        ticker=cfg.ticker,
        chart_paths=chart_paths,
    )

    # Add latest state from df for hybrid analysis
    if len(df) > 0:
        latest = df.iloc[-1]
        evidence["latest_state"] = {
            "date": str(latest.name),
            "close": float(latest.get("Close", 0)),
            "ma20": float(latest.get("MA20", 0)) if "MA20" in df.columns else None,
            "ma50": float(latest.get("MA50", 0)) if "MA50" in df.columns else None,
            "ma200": float(latest.get("MA200", 0)) if "MA200" in df.columns else None,
            "rsi_14": float(latest.get("RSI_14", 50)) if "RSI_14" in df.columns else None,
            "macd": float(latest.get("MACD", 0)) if "MACD" in df.columns else None,
            "macd_signal": float(latest.get("MACD_Signal", 0)) if "MACD_Signal" in df.columns else None,
            "regime_bullish": bool(latest.get("Close", 0) > latest.get("MA200", 0)) if "MA200" in df.columns else None,
        }

    # Save evidence pack
    try:
        save_json(evidence, evi_path)
        print(f"Evidence pack saved: {evi_path}")
    except Exception as e:
        print(f"WARN: Failed to save evidence pack: {e}")
        evi_path = None

    # LLM reporting
    if cfg.llm:
        api_key_present = bool(os.getenv("OPENAI_API_KEY"))
        if not api_key_present:
            print("INFO: OPENAI_API_KEY not set; skipping LLM report generation.")
        else:
            # Short trade note
            llm_note = llm_generate_trade_note(evidence, model=cfg.llm_model)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(llm_note)

            # Final report (longer)
            final_report = llm_generate_full_report(evidence, model=cfg.llm_model)
            with open(final_md_path, "w", encoding="utf-8") as f:
                f.write(final_report)

            # Generate PDF report
            pdf_path = os.path.join(cfg.outdir, f"{cfg.ticker}_final_report.pdf")
            try:
                # Prepare metrics for PDF header
                pdf_metrics = {
                    'CAGR': metrics.get('CAGR', 0),
                    'Sharpe': metrics.get('Sharpe', 0),
                    'MaxDrawdown': metrics.get('MaxDrawdown', 0),
                    'equity_multiple': metrics.get('EquityMultiple', 0),
                    'NumTrades': metrics.get('NumTrades', 'N/A'),
                    'HitRate': metrics.get('HitRate', 0),
                }
                report_date = datetime.now().strftime("%B %d, %Y")

                generate_pdf_report(
                    markdown_content=final_report,
                    output_path=pdf_path,
                    ticker=cfg.ticker,
                    company_name=company_name,
                    metrics=pdf_metrics,
                    report_date=report_date,
                    chart_paths=chart_paths,
                    image_base_path=cfg.outdir,
                )
                print(f"PDF report generated: {pdf_path}")
            except ImportError as e:
                print(f"INFO: PDF generation skipped (install weasyprint): {e}")
                pdf_path = None
            except Exception as e:
                print(f"WARN: PDF generation failed: {e}")
                pdf_path = None

    artifacts = {
        "equity_drawdown_png": equity_path if (equity_path and os.path.exists(equity_path)) else None,
        "equity_log_compare_png": equity_log_path if (equity_log_path and os.path.exists(equity_log_path)) else None,
        "drawdown_compare_png": drawdown_compare_path if (drawdown_compare_path and os.path.exists(drawdown_compare_path)) else None,
        "golden_cross_trades_png": gc_path if (gc_path and os.path.exists(gc_path)) else None,
        "price_ma_macd_6m_png": price_macd_6m_path if (price_macd_6m_path and os.path.exists(price_macd_6m_path)) else None,
        "metrics_json": met_path,
        "run_config_json": cfg_path,
        "evidence_json": evi_path if (evi_path and os.path.exists(evi_path)) else None,
        "llm_trade_note_md": md_path if llm_note else None,
        "llm_final_report_md": final_md_path if final_report else None,
        "llm_final_report_pdf": pdf_path if (pdf_path and os.path.exists(pdf_path)) else None,
    }

    return df, out, trade, metrics, artifacts


def main():
    parser = argparse.ArgumentParser(description="Run the Tech Analyst Agent demo pipeline.")
    parser.add_argument("ticker", type=str, help="Stock ticker symbol (e.g., NVDA, AAPL, MSFT)")
    parser.add_argument("--period", type=str, default="10y")
    parser.add_argument("--interval", type=str, default="1d")
    parser.add_argument("--outdir", type=str, default="outputs")
    parser.add_argument("--no-plot", action="store_true", help="Disable visualisations.")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM report generation.")
    parser.add_argument("--llm-model", type=str, default="gpt-4o-mini")

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
        except (ValueError, TypeError):
            # Non-numeric values - skip comparison
            pass

    print("\n=== ARTIFACTS ===")
    for k, v in artifacts.items():
        if v:
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
