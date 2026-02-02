from __future__ import annotations

import argparse
from pathlib import Path
import datetime as dt
import shutil

import numpy as np
import pandas as pd

from tech_agent.constants import (
    DEFAULT_TICKER,
    DEFAULT_YEARS,
    DEFAULT_INTERVAL,
    DEFAULT_TRAIN_END,
    DEFAULT_VAL_END,
    DEFAULT_TRADING_COST,
    DEFAULT_INITIAL_CAPITAL,
    VOL_WINDOW_FOR_SIGNALS,
    PARAM_GRID_MAIN,
    LABEL_BH,
    LABEL_MAIN,
    MA_FAST,
    MA_SLOW,
)
from tech_agent.data import load_clean_ohlcv
from tech_agent.signals import generate_signals, build_exec_signals_from_multi
from tech_agent.engines import run_engine_light, run_engine_full
from tech_agent.backtest import run_backtest, sharpe_from_bt, performance_summary
from tech_agent.utils import time_split
from tech_agent.visualization import report_block

from tech_agent.fundamental_filter import FundamentalView, load_fundamental_override, max_leverage_cap_from_view
from tech_agent.report_payload import build_report_payload, save_report_payload
from tech_agent.llm_provider import generate_report_markdown
from tech_agent.report_postprocess import ensure_appendices
from tech_agent.html_report import render_html_report, save_html
from tech_agent.fundamental_metrics import fetch_idaliia_yahoo_snapshot
from tech_agent.fundamental_viz import write_fundamental_charts
from tech_agent.idaliia_bridge import run_idaliia_fundamental_memo
from tech_agent.dotenv_loader import load_dotenv_file


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", type=str, default=DEFAULT_TICKER)
    p.add_argument("--years", type=int, default=DEFAULT_YEARS)
    p.add_argument("--interval", type=str, default=DEFAULT_INTERVAL)
    p.add_argument(
        "--as_of",
        type=str,
        default="latest",
        help=(
            "Data end date for reproducibility (YYYY-MM-DD). Use 'latest' for real-time fetch."
        ),
    )
    p.add_argument("--train_end", type=str, default=DEFAULT_TRAIN_END)
    p.add_argument("--val_end", type=str, default=DEFAULT_VAL_END)
    p.add_argument("--trading_cost", type=float, default=DEFAULT_TRADING_COST)
    p.add_argument("--initial_capital", type=float, default=DEFAULT_INITIAL_CAPITAL)
    p.add_argument(
        "--target_vol",
        type=float,
        default=0.20,
        help="Annualised target volatility for risk management (vol targeting). Lower => smoother equity, often higher Sharpe.",
    )

    # Technical extensions
    p.add_argument(
        "--use_patterns",
        action="store_true",
        help="Enable candlestick/pattern factor (experimental). Default is OFF for the main strategy.",
    )
    p.add_argument(
        "--use_patterns_appendix",
        action="store_true",
        help="Enable candlestick/pattern factor for APPENDIX (experimental). Main strategy remains unchanged.",
    )
    p.add_argument(
        "--no_patterns_appendix",
        action="store_true",
        help="Disable candlestick/pattern factor in the APPENDIX (default is enabled).",
    )
    # Backward-compatible alias (kept): explicitly disable patterns
    p.add_argument("--no_patterns", action="store_true", help="Disable candlestick/pattern factor (alias)")

    # Volume confirmation (experimental; entry-only)
    p.add_argument(
        "--use_volume_confirm",
        action="store_true",
        help="Enable relative-volume entry confirmation for the MAIN strategy (experimental). Default is OFF.",
    )
    p.add_argument("--vol_confirm_window", type=int, default=20, help="Window for relative volume (volume/SMA(volume)).")
    p.add_argument("--vol_confirm_min_ratio", type=float, default=1.1, help="Entry requires rel_vol >= this ratio.")
    p.add_argument(
        "--no_volume_appendix",
        action="store_true",
        help="Disable the volume-confirmed strategy variant in the APPENDIX (default is included).",
    )

    # Fundamental overlay (external)
    p.add_argument("--fundamental_mode", type=str, default="filter", choices=["report_only", "filter"])
    p.add_argument("--fundamental_file", type=str, default="inputs/fundamental_override.json")
    p.add_argument("--sell_leverage_mult", type=float, default=0.3, help="Max leverage multiplier when rating=SELL")
    p.add_argument(
        "--fund_asof_default",
        type=str,
        default=None,
        help="If fundamental_file has no as_of, apply from this date (e.g., 2023-01-01).",
    )
    p.add_argument(
        "--fundamental_report_path",
        type=str,
        default="external/external_fundamental_analysis/fundamental_analyst_agent/README.md",
        help=(
            "Path to the external fundamental report/file used for as_of inference. "
            "If fundamental_override.json omits as_of, we infer publication date from this file's mtime."
        ),
    )
    p.add_argument(
        "--fundamental_embed_path",
        type=str,
        default="",
        help=(
            "Optional: path to an external fundamental memo/report (e.g., Idaliia HTML) to embed/link in the report. "
            "Copied into outputs/appendix for reproducibility."
        ),
    )
    p.add_argument(
        "--run_idaliia",
        action="store_true",
        help=(
            "Run the external Idaliia fundamental module to generate a memo and copy it into outputs/appendix. "
            "May require network + ALPHA_VANTAGE_API_KEY."
        ),
    )
    p.add_argument(
        "--fundamental_from_idaliia",
        action="store_true",
        help="Use Idaliia's BUY/HOLD/SELL recommendation as the fundamental overlay rating (risk filter).",
    )

    # LLM + export (OpenAI only in this packaged project)
    p.add_argument("--openai_model", type=str, default="gpt-4o-mini")
    p.add_argument("--no_llm", action="store_true", help="Skip LLM generation")
    p.add_argument(
        "--yes_openai",
        action="store_true",
        help="Confirm using OpenAI API for LLM report generation (may incur cost).",
    )
    p.add_argument("--export_html", action="store_true")
    p.add_argument("--show", action="store_true", help="Show plots (not recommended in headless)")

    p.add_argument("--out_dir", type=str, default="outputs")
    p.add_argument("--template_dir", type=str, default="templates")
    return p.parse_args()


def _validate_llm_output(md: str, payload: dict) -> list[str]:
    issues: list[str] = []
    md_l = md.lower()

    # This project uses a numbered academic structure in the prompt.
    required_any = {
        "1. investment instrument & data": ["1. investment instrument & data"],
        "2. main strategy": ["2. main strategy"],
        "3. risks": ["3. risks & limitations", "3. key risks & model limitations"],
        "4. conclusion": ["4. conclusion"],
        "appendix": ["appendix"],
    }
    for label, alts in required_any.items():
        if not any(a in md_l for a in alts):
            issues.append(f"Missing section keyword: {label}")

    forbidden = ["kdj", "obv", "stochastic", "volume profile", "fibonacci"]
    for term in forbidden:
        if term in md_l:
            issues.append(f"Contains unsupported indicator term: {term}")

    # YTD label sanity check only if annual returns are explicitly referenced.
    run_params = payload.get("run_params", {}) if isinstance(payload, dict) else {}
    as_of = run_params.get("as_of")
    if isinstance(as_of, str) and as_of and as_of.lower() not in ("latest", "none"):
        if ("annual return" in md_l or "annual returns" in md_l) and (not as_of.endswith("-12-31")) and ("ytd" not in md_l):
            issues.append("Annual returns mentioned but as-of is not year-end and no YTD label found.")

    return issues


def run_pipeline(args: argparse.Namespace) -> dict:
    out_dir = Path(args.out_dir)
    out_main = out_dir / "main"
    out_app = out_dir / "appendix"
    out_main.mkdir(parents=True, exist_ok=True)
    out_app.mkdir(parents=True, exist_ok=True)

    # --- External fundamental memo/report (Idaliia) ---
    # Priority:
    #  1) Auto-run Idaliia module (best for reproducibility)
    #  2) User-provided embed path (fallback)
    idaliia_result = None
    fundamental_report_copy_rel = None

    if bool(getattr(args, "run_idaliia", False)):
        # Best-effort: keep the result object even on failure so the report can
        # disclose that the external module failed (and therefore any overlay may not apply).
        idaliia_result = run_idaliia_fundamental_memo(ticker=str(args.ticker), out_dir=out_app)
        if idaliia_result.ok and idaliia_result.memo_copy_rel:
            fundamental_report_copy_rel = str(idaliia_result.memo_copy_rel)

    if fundamental_report_copy_rel is None:
        # Manual embed fallback.
        try:
            rp_raw = str(getattr(args, "fundamental_embed_path", "") or "").strip()
            if rp_raw:
                rp = Path(rp_raw).expanduser()
                if rp.exists() and rp.is_file():
                    suf = (rp.suffix or ".html").lower()
                    dst = out_app / f"FUND_idaliia_report{suf}"
                    shutil.copy2(rp, dst)
                    fundamental_report_copy_rel = str(dst.relative_to(out_dir))
        except Exception:
            fundamental_report_copy_rel = None

    # Load prices
    as_of = None if str(getattr(args, "as_of", "")).lower() in ("", "latest", "none") else str(args.as_of)
    df, meta = load_clean_ohlcv(
        args.ticker,
        years=int(args.years),
        interval=args.interval,
        as_of=as_of,
    )
    df = df.sort_index()

    # Debug: data window check + price multiples (clarify timing)
    close0_df = float(df["close"].iloc[0])
    closeT_df = float(df["close"].iloc[-1])
    close1_df = float(df["close"].iloc[1]) if len(df) > 1 else close0_df

    print("RUN_DEMO df start:", df.index[0], "close:", close0_df)
    print("RUN_DEMO df end  :", df.index[-1], "close:", closeT_df)

    # Buy&Hold price multiple (day0 -> end) on the adjusted close series
    print("RUN_DEMO price multiple (day0->end):", closeT_df / close0_df)

    # If you *skip* the first close-to-close return (i.e., start from the 2nd bar),
    # the price multiple is day1->end. This is NOT our backtest exposure convention;
    # it is printed only to help interpret differences.
    print("RUN_DEMO price multiple (day1->end, skip first return):", closeT_df / close1_df)

    # Note: df['ret'].iloc[0] is 0 by construction (pct_change then fillna(0)).
    # The first tradable close-to-close return is df['ret'].iloc[1].
    if len(df) > 1:
        r1 = float(df["ret"].iloc[1]) if "ret" in df.columns else float(pd.Series(df["close"]).pct_change().iloc[1])
        print("RUN_DEMO first tradable return (bar1 = close1/close0 - 1):", r1)

    # Split
    train, val, test = time_split(df, train_end=args.train_end, val_end=args.val_end)

    # IMPORTANT: ensure the combined windows have a UNIQUE, sorted index.
    # If time_split boundaries overlap (e.g., the cut date appears in two splits),
    # concatenation can introduce duplicated timestamps, which will incorrectly
    # compound returns and inflate equity/metrics.
    df_tv = pd.concat([train, val], axis=0)
    df_all = pd.concat([train, val, test], axis=0)

    dup_tv = int(df_tv.index.duplicated().sum())
    dup_all = int(df_all.index.duplicated().sum())
    if dup_tv or dup_all:
        print(f"RUN_DEMO WARNING: duplicated timestamps after split concat: df_tv={dup_tv}, df_all={dup_all}. Dropping duplicates (keep first).")

    df_tv = df_tv.loc[~df_tv.index.duplicated(keep="first")].sort_index()
    df_all = df_all.loc[~df_all.index.duplicated(keep="first")].sort_index()

    # Freeze price/return frames to avoid accidental in-place mutation by indicators/signals.
    # All backtests (benchmark + strategy) will use these immutable views.
    px_cols = [c for c in ["close", "ret"] if c in df_all.columns]
    px_tv = df_tv[px_cols].copy(deep=True)
    px_all = df_all[px_cols].copy(deep=True)

    # IMPORTANT: Recompute returns from the (possibly adjusted) close series to guarantee consistency.
    # Some upstream steps may accidentally overwrite a 'ret' column; we treat close as the single source of truth.
    if "close" in px_tv.columns:
        px_tv["ret"] = px_tv["close"].astype("float64").pct_change().fillna(0.0).astype("float64")
    if "close" in px_all.columns:
        px_all["ret"] = px_all["close"].astype("float64").pct_change().fillna(0.0).astype("float64")

    # Separate copies for signal generation (safe to add temporary columns)
    df_tv_sig = df_tv.copy(deep=True)
    df_all_sig = df_all.copy(deep=True)

    # Fit median realised volatility on TRAIN only (annualised), computed from close-to-close returns.
    # We compute this from 'close' to avoid relying on a mutable df['ret'] column.
    train_close = pd.to_numeric(train["close"], errors="coerce").astype("float64")
    train_ret = train_close.pct_change().fillna(0.0)
    vol_train = train_ret.rolling(VOL_WINDOW_FOR_SIGNALS, min_periods=VOL_WINDOW_FOR_SIGNALS).std(ddof=0) * np.sqrt(252.0)
    median_vol_fit = float(vol_train.replace(0.0, np.nan).median())
    if (not np.isfinite(median_vol_fit)) or median_vol_fit <= 0:
        median_vol_fit = 0.2

    # MAIN strategy is fixed to NO patterns for this project.
    # Patterns are allowed only as an APPENDIX experiment (default ON; use --no_patterns_appendix to disable).
    use_patterns = False
    if bool(getattr(args, "use_patterns", False)):
        print("RUN_DEMO NOTE: --use_patterns is ignored. Main strategy is fixed to use_patterns=False; use --use_patterns_appendix for appendix experiment.")

    use_patterns_appendix = not bool(getattr(args, "no_patterns_appendix", False))
    if bool(getattr(args, "use_patterns_appendix", False)):
        use_patterns_appendix = True

    # Optional volume confirmation for MAIN (entry-only). Appendix may still show a volume-confirmed variant.
    use_volume_confirm = bool(getattr(args, "use_volume_confirm", False))
    vol_confirm_window = int(getattr(args, "vol_confirm_window", 20))
    vol_confirm_min_ratio = float(getattr(args, "vol_confirm_min_ratio", 1.1))

    # Fundamental overlay
    fundamental_view = None
    max_lev_cap_all: float | pd.Series = 1.0
    overlay_used_in_bt = False

    # --- Fundamental overlay: load external view, and ensure an as_of date for clean reporting ---
    fundamental_asof_source = None
    fundamental_report_mtime_utc = None
    fundamental_report_exists = None
    fundamental_override_generated_rel = None

    # Optionally derive the fundamental rating from Idaliia's generated memo (preferred for reproducibility).
    # This keeps the "external model" explainable and ties it to concrete outputs saved under outputs/appendix.
    fundamental_view = None
    if bool(getattr(args, "fundamental_from_idaliia", False)) and idaliia_result is not None:
        try:
            rec = (idaliia_result.recommendation or "").strip().upper()
            if rec:
                # Map to BUY/HOLD/SELL; treat unknown as HOLD.
                if "BUY" in rec:
                    rating = "BUY"
                elif "SELL" in rec:
                    rating = "SELL"
                else:
                    rating = "HOLD"

                notes = []
                if idaliia_result.target_price is not None:
                    notes.append(f"Idaliia target price: ${idaliia_result.target_price:.2f}")
                if idaliia_result.upside is not None:
                    notes.append(f"Idaliia upside vs current: {idaliia_result.upside*100:+.1f}%")

                fundamental_view = FundamentalView(
                    rating=rating,
                    as_of=None,
                    source="Idaliia fundamental_analyst_agent (auto-generated memo)",
                    notes=notes or None,
                )
                # Persist the derived override for reproducibility.
                import json as _json

                p = out_app / "FUND_idaliia_override.json"
                p.write_text(
                    _json.dumps(
                        {
                            "rating": fundamental_view.rating,
                            "as_of": fundamental_view.as_of,
                            "source": fundamental_view.source,
                            "notes": fundamental_view.notes,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                fundamental_override_generated_rel = str((out_app / "FUND_idaliia_override.json").relative_to(out_dir))
        except Exception:
            fundamental_view = None

    # Fallback: load manual override file.
    if fundamental_view is None:
        try:
            fundamental_view = load_fundamental_override(args.fundamental_file)
        except Exception:
            fundamental_view = None

    try:
        # If we have a view at this point, ensure it has an as_of for clean reporting.
        if fundamental_view is None:
            raise RuntimeError("no fundamental_view")

        # 1) If user provides a default, use it.
        if fundamental_view.as_of is None and args.fund_asof_default:
            fundamental_view = type(fundamental_view)(
                rating=fundamental_view.rating,
                as_of=str(args.fund_asof_default),
                source=fundamental_view.source,
                notes=fundamental_view.notes,
            )
            fundamental_asof_source = "cli:fund_asof_default"

        # 2) Otherwise, infer as_of from the external report file's mtime (publication-date proxy).
        if fundamental_view.as_of is None:
            rp = Path(str(getattr(args, "fundamental_report_path", "") or ""))
            fundamental_report_exists = bool(rp.exists())
            if rp.exists():
                # Use UTC mtime date as a stable, explainable proxy for 'publication date'.
                mtime_ts = float(rp.stat().st_mtime)
                mtime_dt = dt.datetime.fromtimestamp(mtime_ts, tz=dt.timezone.utc)
                fundamental_report_mtime_utc = mtime_dt.isoformat()
                inferred_asof = mtime_dt.date().isoformat()
                fundamental_view = type(fundamental_view)(
                    rating=fundamental_view.rating,
                    as_of=inferred_asof,
                    source=fundamental_view.source,
                    notes=fundamental_view.notes,
                )
                fundamental_asof_source = "inferred_from_report_mtime"

        # 3) Final fallback: if still missing, use the data end date (pinned as_of if provided, else last bar).
        if fundamental_view.as_of is None:
            inferred_asof = (str(as_of) if isinstance(as_of, str) else None) or df.index[-1].date().isoformat()
            fundamental_view = type(fundamental_view)(
                rating=fundamental_view.rating,
                as_of=inferred_asof,
                source=fundamental_view.source,
                notes=fundamental_view.notes,
            )
            fundamental_asof_source = "fallback:data_end_date"

    except Exception:
        pass

    if args.fundamental_mode == "filter" and fundamental_view is not None:
        # Only SELL changes leverage cap; BUY/HOLD -> cap=1.0
        max_lev_cap_all = max_leverage_cap_from_view(
            df_all.index,
            fundamental_view,
            base_max_leverage=1.0,
            sell_leverage_mult=float(args.sell_leverage_mult),
        )
        overlay_used_in_bt = True

    # --- Fundamental snapshot (metrics) + charts (best-effort) ---
    # We use the external Idaliia fundamental module's YahooFinanceClient to fetch a small, reproducible snapshot.
    # These metrics are for contextual display only (not used as an alpha predictor).
    fundamental_snapshot: dict | None = None
    try:
        snap = fetch_idaliia_yahoo_snapshot(args.ticker)
        if snap is not None and isinstance(snap.data, dict) and snap.data:
            fundamental_snapshot = {
                "ok": True,
                "source": snap.source,
                "fetched_at_utc": snap.fetched_at_utc,
                "data": snap.data,
                "error": None,
            }
            # Store charts in appendix output folder so the HTML report can embed them (PDF is via browser print).
            write_fundamental_charts(
                out_dir=out_app,
                ticker=str(args.ticker).upper(),
                snapshot=snap.data,
            )
        else:
            fundamental_snapshot = {
                "ok": False,
                "source": getattr(snap, "source", None),
                "fetched_at_utc": getattr(snap, "fetched_at_utc", None),
                "data": None,
                "error": "No snapshot data returned.",
            }
    except Exception as e:
        fundamental_snapshot = {
            "ok": False,
            "source": "Yahoo Finance snapshot (via Idaliia fundamental module)",
            "fetched_at_utc": None,
            "data": None,
            "error": str(e),
        }

    # ---- Parameter selection on VAL (light engine) ----
    best = None
    for p in PARAM_GRID_MAIN:
        sig_tv = generate_signals(
            df_tv_sig,
            **p,
            median_vol_fit=median_vol_fit,
            use_patterns=use_patterns,
            use_volume_confirm=use_volume_confirm,
            vol_confirm_window=vol_confirm_window,
            vol_confirm_min_ratio=vol_confirm_min_ratio,
        )
        exec_tv = build_exec_signals_from_multi(sig_tv, df_tv.index)

        max_lev_cap_tv = (
            max_lev_cap_all.reindex(df_tv.index) if isinstance(max_lev_cap_all, pd.Series) else max_lev_cap_all
        )

        bt_tv, _ = run_engine_light(
            df=px_tv,
            signals_exec=exec_tv,
            trading_cost=float(args.trading_cost),
            initial_capital=float(args.initial_capital),
            max_leverage=max_lev_cap_tv,
            target_vol=float(args.target_vol),
            vol_window=int(p.get("vol_window", 20)),
        )

        bt_val = bt_tv.loc[val.index] if len(val) else bt_tv.iloc[0:0]
        score = sharpe_from_bt(bt_val, rf_annual=0.0, min_len=60)

        if (best is None) or (score > best["score"]):
            best = {"params": p, "score": float(score)}

    best_params = dict(best["params"]) if best else dict(PARAM_GRID_MAIN[0])

    # ---- Final full run ----
    sig_all = generate_signals(
        df_all_sig,
        **best_params,
        median_vol_fit=median_vol_fit,
        use_patterns=use_patterns,
        use_volume_confirm=use_volume_confirm,
        vol_confirm_window=vol_confirm_window,
        vol_confirm_min_ratio=vol_confirm_min_ratio,
    )
    exec_all = build_exec_signals_from_multi(sig_all, df_all.index)

    res = run_engine_full(
        df=px_all,
        signals_exec=exec_all,
        trading_cost=float(args.trading_cost),
        initial_capital=float(args.initial_capital),
        max_leverage=max_lev_cap_all,
        target_vol=float(args.target_vol),
        vol_window=int(best_params.get("vol_window", 20)) if isinstance(best_params, dict) else 20,
    )

    bt_main = res["backtest"]
    pos_target = res.get("position_decision")  # risk-managed, decision-time target exposure (pre-shift)

    # ---- Fair benchmark (single definition) ----
    # Decision position = 1 every day; execution delay handled ONLY inside run_backtest (shift(1)).

    bm = run_backtest(
        px_all,
        pd.Series(1.0, index=px_all.index, dtype="float64"),
        trading_cost=float(args.trading_cost),
        initial_capital=float(args.initial_capital),
    )

    # Sanity: compounded close-to-close returns on px_all must match price ratio (up to tiny fp error)
    if "close" in px_all.columns and len(px_all) > 1:
        ret_from_close = px_all["close"].astype("float64").pct_change().fillna(0.0)
        implied_eq = float((1.0 + ret_from_close).cumprod().iloc[-1])
        price_ratio = float(px_all["close"].astype("float64").iloc[-1] / px_all["close"].astype("float64").iloc[0])
        print("RUN_DEMO sanity: price_ratio=", price_ratio, "ret_cumprod(from_close)=", implied_eq)

    # Debug: verify the benchmark bt used for reporting
    try:
        print(
            "DEBUG bm:",
            "start=", bm.index[0],
            "end=", bm.index[-1],
            "pos0=", float(bm["position"].iloc[0]) if "position" in bm.columns else None,
            "equity_end=", float(bm["equity"].iloc[-1]) if "equity" in bm.columns else None,
        )
    except Exception as _e:
        print("DEBUG bm print failed:", _e)

    # Main report block
    report_block(
        "FULL",
        {LABEL_BH: bm.copy(), LABEL_MAIN: bt_main.copy()},
        train=train,
        val=val,
        test=test,
        ticker=args.ticker,
        price_df=px_all[["close"]].copy() if "close" in px_all.columns else None,
        ema_fast=int(best_params.get("ema_fast")) if isinstance(best_params, dict) and best_params.get("ema_fast") is not None else None,
        ema_slow=int(best_params.get("ema_slow")) if isinstance(best_params, dict) and best_params.get("ema_slow") is not None else None,
        out_dir=out_main,
        show=bool(args.show),
    )

    # ---- Sensitivity analysis (full sample, main strategy only) ----
    # Concise robustness grid: keep the main EMA/regime grid, and vary vol_window over a small set.
    # This tests the stability of the vol-targeting estimate horizon without exploding the search space.
    VOL_WINDOW_SENS = [10, 40]

    sens_rows = []
    sens_grid = []
    for base in PARAM_GRID_MAIN:
        for vw in VOL_WINDOW_SENS:
            p = dict(base)
            p["vol_window"] = int(vw)
            sens_grid.append(p)

    for p in sens_grid:
        sig_full = generate_signals(
            df_all_sig,
            **p,
            median_vol_fit=median_vol_fit,
            use_patterns=False,
            use_volume_confirm=use_volume_confirm,
            vol_confirm_window=vol_confirm_window,
            vol_confirm_min_ratio=vol_confirm_min_ratio,
        )
        exec_full = build_exec_signals_from_multi(sig_full, df_all.index)
        res_full = run_engine_full(
            df=px_all,
            signals_exec=exec_full,
            trading_cost=float(args.trading_cost),
            initial_capital=float(args.initial_capital),
            max_leverage=max_lev_cap_all,
            target_vol=float(args.target_vol),
            vol_window=int(p.get("vol_window", 20)),
        )
        m = performance_summary(res_full["backtest"])
        sens_rows.append(
            {
                "params": p,
                "Sharpe": m.get("Sharpe"),
                "total_return": m.get("total_return"),
                "max_drawdown": m.get("max_drawdown"),
            }
        )

    sensitivity_full = None
    if sens_rows:
        def _fmt_params(d: dict) -> str:
            return (
                f"ema_fast={d['ema_fast']}, ema_slow={d['ema_slow']}, "
                f"regime_buffer_pct={d['regime_buffer_pct']}, vol_window={d['vol_window']}"
            )

        best_by_sharpe = max(sens_rows, key=lambda x: (x.get("Sharpe") or -1e9))
        sh = [r.get("Sharpe") for r in sens_rows if r.get("Sharpe") is not None]
        tr = [r.get("total_return") for r in sens_rows if r.get("total_return") is not None]
        dd = [r.get("max_drawdown") for r in sens_rows if r.get("max_drawdown") is not None]
        sensitivity_full = {
            "note": "Full-sample sensitivity across PARAM_GRID_MAIN (main strategy, patterns off).",
            "best_by_sharpe": {
                "params": best_by_sharpe["params"],
                "params_str": _fmt_params(best_by_sharpe["params"]),
                "Sharpe": best_by_sharpe.get("Sharpe"),
                "total_return": best_by_sharpe.get("total_return"),
                "max_drawdown": best_by_sharpe.get("max_drawdown"),
            },
            "ranges": {
                "Sharpe_min": min(sh) if sh else None,
                "Sharpe_max": max(sh) if sh else None,
                "total_return_min": min(tr) if tr else None,
                "total_return_max": max(tr) if tr else None,
                "max_drawdown_min": min(dd) if dd else None,
                "max_drawdown_max": max(dd) if dd else None,
            },
            "grid": [
                {
                    "params_str": _fmt_params(r["params"]),
                    "Sharpe": r.get("Sharpe"),
                    "total_return": r.get("total_return"),
                    "max_drawdown": r.get("max_drawdown"),
                }
                for r in sens_rows
            ],
        }
        # Write sensitivity table to appendix outputs for transparency
        try:
            sens_df = pd.DataFrame(sensitivity_full.get("grid", []))
            if not sens_df.empty:
                sens_df.to_csv(out_app / "FULL_sensitivity.csv", index=False)
        except Exception as _e:
            print("RUN_DEMO WARNING: failed to write sensitivity CSV:", _e)

    # ---- Split metrics (reset equity within each split) ----
    def _reset_equity(bt_slice: pd.DataFrame, initial_capital: float) -> pd.DataFrame:
        if len(bt_slice) == 0:
            return bt_slice.copy()
        out = bt_slice.copy()
        r = pd.to_numeric(out["strategy_ret"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
        out["equity"] = float(initial_capital) * (1.0 + r).cumprod()
        out["drawdown"] = out["equity"] / out["equity"].cummax() - 1.0
        return out

    split_rows = []
    for split_name, idx in [("train", train.index), ("val", val.index), ("test", test.index)]:
        if len(idx) == 0:
            continue
        for label, bt_src in [(LABEL_BH, bm), (LABEL_MAIN, bt_main)]:
            bt_slice = bt_src.loc[idx]
            bt_reset = _reset_equity(bt_slice, float(args.initial_capital))
            metrics = performance_summary(bt_reset)
            split_rows.append(
                {
                    "split": split_name,
                    "name": label,
                    "start": str(idx.min().date()),
                    "end": str(idx.max().date()),
                    **metrics,
                }
            )

    if split_rows:
        split_df = pd.DataFrame(split_rows)
        split_df.to_csv(out_main / "FULL_split_metrics.csv", index=False)

    # Appendix: MA baseline
    fast, slow = int(MA_FAST), int(MA_SLOW)
    close = df_all["close"].astype(float)
    ma_fast = close.rolling(fast).mean()
    ma_slow = close.rolling(slow).mean()
    sig_ma = (ma_fast > ma_slow).astype("float64").fillna(0.0)

    bt_ma = run_backtest(
        px_all,
        sig_ma,
        trading_cost=float(args.trading_cost),
        initial_capital=float(args.initial_capital),
    )
    label_ma = f"Baseline: MA({fast}/{slow})"

    appendix_blocks = {LABEL_BH: bm.copy(), LABEL_MAIN: bt_main.copy(), label_ma: bt_ma.copy()}

    # Appendix: volume-confirmed variant (entry-only confirmation; experimental).
    # This does NOT change the main strategy; it is included as an additional comparison for the assignment.
    if not bool(getattr(args, "no_volume_appendix", False)):
        sig_all_vol = generate_signals(
            df_all_sig,
            **best_params,
            median_vol_fit=median_vol_fit,
            use_patterns=False,
            use_volume_confirm=True,
            vol_confirm_window=vol_confirm_window,
            vol_confirm_min_ratio=vol_confirm_min_ratio,
        )
        exec_all_vol = build_exec_signals_from_multi(sig_all_vol, df_all.index)
        res_vol = run_engine_full(
            df=px_all,
            signals_exec=exec_all_vol,
            trading_cost=float(args.trading_cost),
            initial_capital=float(args.initial_capital),
            max_leverage=max_lev_cap_all,
            target_vol=float(args.target_vol),
            vol_window=int(best_params.get("vol_window", 20)) if isinstance(best_params, dict) else 20,
        )
        appendix_blocks["Appendix: Hybrid Main (volume confirm)"] = res_vol["backtest"].copy()

    # Appendix: experimental patterns-enabled strategy (optional)
    if bool(use_patterns_appendix):
        sig_all_pat = generate_signals(df_all_sig, **best_params, median_vol_fit=median_vol_fit, use_patterns=True)
        exec_all_pat = build_exec_signals_from_multi(sig_all_pat, df_all.index)
        res_pat = run_engine_full(
            df=px_all,
            signals_exec=exec_all_pat,
            trading_cost=float(args.trading_cost),
            initial_capital=float(args.initial_capital),
            max_leverage=max_lev_cap_all,
            target_vol=float(args.target_vol),
            vol_window=int(best_params.get("vol_window", 20)) if isinstance(best_params, dict) else 20,
        )
        bt_pat = res_pat["backtest"]
        appendix_blocks["Appendix: Hybrid Main (patterns)"] = bt_pat.copy()

    # Appendix: fundamental filter overlay (optional comparison)
    # Only include if the MAIN run did NOT already apply the filter.
    if (args.fundamental_mode != "filter") and (fundamental_view is not None):
        max_lev_cap_all_filter = max_leverage_cap_from_view(
            df_all.index,
            fundamental_view,
            base_max_leverage=1.0,
            sell_leverage_mult=float(args.sell_leverage_mult),
        )
        # Only include this variant if it actually changes the leverage cap at least once.
        # Otherwise, the curve/metrics are identical to the main strategy and will confuse the report legend.
        has_effect = True
        try:
            if isinstance(max_lev_cap_all_filter, pd.Series):
                has_effect = bool(pd.to_numeric(max_lev_cap_all_filter, errors="coerce").fillna(1.0).min() < 0.999)
            else:
                has_effect = bool(float(max_lev_cap_all_filter) < 0.999)
        except Exception:
            has_effect = True

        if has_effect:
            res_fund = run_engine_full(
                df=px_all,
                signals_exec=exec_all,
                trading_cost=float(args.trading_cost),
                initial_capital=float(args.initial_capital),
                max_leverage=max_lev_cap_all_filter,
                target_vol=float(args.target_vol),
            )
            bt_fund = res_fund["backtest"]
            appendix_blocks["Appendix: Hybrid Main (fundamental filter)"] = bt_fund.copy()

    report_block(
        "APPENDIX",
        appendix_blocks,
        train=train,
        val=val,
        test=test,
        ticker=args.ticker,
        price_df=px_all[["close"]].copy() if "close" in px_all.columns else None,
        ema_fast=int(best_params.get("ema_fast")) if isinstance(best_params, dict) and best_params.get("ema_fast") is not None else None,
        ema_slow=int(best_params.get("ema_slow")) if isinstance(best_params, dict) and best_params.get("ema_slow") is not None else None,
        out_dir=out_app,
        show=bool(args.show),
    )

    # Save report payload JSON
    # --- Signal snapshot (as-of) for report stance/recommendation ---
    signal_snapshot = None
    try:
        if len(df_all.index) >= 2 and pos_target is not None:
            snap_idx = df_all.index
            t0 = snap_idx[-2]
            t1 = snap_idx[-1]

            base_prev = float(exec_all["position_decision"].reindex(snap_idx).iloc[-2])
            base_last = float(exec_all["position_decision"].reindex(snap_idx).iloc[-1])
            tgt_prev = float(pd.to_numeric(pos_target, errors="coerce").reindex(snap_idx).fillna(0.0).iloc[-2])
            tgt_last = float(pd.to_numeric(pos_target, errors="coerce").reindex(snap_idx).fillna(0.0).iloc[-1])

            exec_prev = float(pd.to_numeric(bt_main["position"], errors="coerce").fillna(0.0).iloc[-2]) if "position" in bt_main.columns else 0.0
            exec_last = float(pd.to_numeric(bt_main["position"], errors="coerce").fillna(0.0).iloc[-1]) if "position" in bt_main.columns else 0.0

            sig_last = sig_all.reindex(snap_idx).iloc[-1]
            sig_prev = sig_all.reindex(snap_idx).iloc[-2]

            def _action(prev: float, cur: float) -> str:
                if prev <= 0.0 and cur > 0.0:
                    return "ENTER (Buy)"
                if prev > 0.0 and cur <= 0.0:
                    return "EXIT (Sell/Reduce to 0)"
                if prev > 0.0 and cur > 0.0:
                    return "HOLD (Maintain)"
                return "WATCH (Stay out)"

            signal_snapshot = {
                "decision_date": str(pd.Timestamp(t1).date()),
                "prev_date": str(pd.Timestamp(t0).date()),
                "regime_last": int(sig_last.get("regime", 0)),
                "signal_bin_last": int(sig_last.get("signal_bin", 0)),
                "long_score_last": int(sig_last.get("long_score", 0)),
                "req_k_entry_last": int(sig_last.get("req_k_long_entry", 0)),
                "req_k_hold_last": int(sig_last.get("req_k_long_hold", 0)),
                "position_base_prev": base_prev,
                "position_base_last": base_last,
                "position_target_prev": tgt_prev,
                "position_target_last": tgt_last,
                "position_executed_prev": exec_prev,
                "position_executed_last": exec_last,
                "recommended_action": _action(tgt_prev, tgt_last),
                "timing_note": "Targets are decision-time; execution occurs on the next bar (1-bar delay in backtest).",
            }
    except Exception:
        signal_snapshot = None

    # Fundamental overlay request flag: keep policy visible even if the external module fails.
    try:
        from pathlib import Path as _Path

        fund_file_exists = bool(str(getattr(args, "fundamental_file", "") or "").strip()) and _Path(
            str(getattr(args, "fundamental_file", "")).strip()
        ).exists()
    except Exception:
        fund_file_exists = False

    fundamental_requested = bool(
        (str(getattr(args, "fundamental_mode", "") or "").lower() in ("filter", "report_only"))
        and (
            str(getattr(args, "fundamental_mode", "") or "").lower() == "filter"
            or bool(getattr(args, "run_idaliia", False))
            or bool(getattr(args, "fundamental_from_idaliia", False))
            or bool(str(getattr(args, "fundamental_embed_path", "") or "").strip())
            or fund_file_exists
        )
    )

    run_params = {
        "ticker": args.ticker,
        "years": int(args.years),
        "interval": args.interval,
        "as_of": ("latest" if as_of is None else str(as_of)),
        "train_end": args.train_end,
        "val_end": args.val_end,
        "trading_cost": float(args.trading_cost),
        "initial_capital": float(args.initial_capital),
        "target_vol": float(args.target_vol),
        "use_patterns": bool(use_patterns),
        "use_patterns_appendix": bool(use_patterns_appendix),
        "use_volume_confirm": bool(use_volume_confirm),
        "vol_confirm_window": int(vol_confirm_window),
        "vol_confirm_min_ratio": float(vol_confirm_min_ratio),
        "volume_appendix_enabled": (not bool(getattr(args, "no_volume_appendix", False))),
        # LLM disclosure / reproducibility: record which provider + model were selected.
        "no_llm": bool(args.no_llm),
        "llm_provider": (None if bool(args.no_llm) else "openai"),
        "openai_model": (None if bool(args.no_llm) else str(args.openai_model)),
        "export_html": bool(getattr(args, "export_html", False)),
        "fundamental_mode": args.fundamental_mode,
        "fundamental_file": args.fundamental_file,
        "fundamental_requested": bool(fundamental_requested),
        "fundamental_report_path": str(getattr(args, "fundamental_report_path", "")),
        "fundamental_embed_path": str(getattr(args, "fundamental_embed_path", "")),
        "fundamental_report_copy_rel": fundamental_report_copy_rel,
        "run_idaliia": bool(getattr(args, "run_idaliia", False)),
        "fundamental_from_idaliia": bool(getattr(args, "fundamental_from_idaliia", False)),
        "fundamental_override_generated_rel": fundamental_override_generated_rel,
        "idaliia_result": (
            None
            if idaliia_result is None
            else {
                "ok": bool(getattr(idaliia_result, "ok", False)),
                "memo_copy_rel": getattr(idaliia_result, "memo_copy_rel", None),
                "log_copy_rel": getattr(idaliia_result, "log_copy_rel", None),
                "recommendation": getattr(idaliia_result, "recommendation", None),
                "target_price": getattr(idaliia_result, "target_price", None),
                "upside": getattr(idaliia_result, "upside", None),
                "generated_at_utc": getattr(idaliia_result, "generated_at_utc", None),
                "error": getattr(idaliia_result, "error", None),
            }
        ),
        "fundamental_asof_source": fundamental_asof_source,
        "fundamental_report_exists": fundamental_report_exists,
        "fundamental_report_mtime_utc": fundamental_report_mtime_utc,
        "sell_leverage_mult": float(args.sell_leverage_mult),
        "overlay_used_in_backtest": bool(overlay_used_in_bt),
        "best_params_val": best_params,
        "sensitivity_full": sensitivity_full,
        "signal_snapshot": signal_snapshot,
        "yfinance_meta": meta,
        # Best-effort fundamental snapshot from the external Idaliia module (Yahoo Finance fields).
        # For contextual display only (NOT used as alpha).
        "fundamental_snapshot": fundamental_snapshot,
        "fundamental_view": (
            None
            if fundamental_view is None
            else {
                "rating": fundamental_view.rating_norm,
                "as_of": fundamental_view.as_of,
                "as_of_source": fundamental_asof_source,
                "source": fundamental_view.source,
                "notes": fundamental_view.notes,
            }
        ),
    }

    # Reproducibility: store an explicit "how to rerun" command (no secrets).
    # Keep it stable and course-friendly; omit API keys.
    repro_full = [
        "python",
        "run_demo.py",
        "--ticker",
        str(args.ticker),
        "--years",
        str(int(args.years)),
        "--interval",
        str(args.interval),
        "--as_of",
        ("latest" if as_of is None else str(as_of)),
        "--train_end",
        str(args.train_end),
        "--val_end",
        str(args.val_end),
        "--trading_cost",
        str(float(args.trading_cost)),
        "--initial_capital",
        str(float(args.initial_capital)),
        "--target_vol",
        str(float(args.target_vol)),
        "--fundamental_mode",
        str(args.fundamental_mode),
        "--fundamental_file",
        str(args.fundamental_file),
        "--sell_leverage_mult",
        str(float(args.sell_leverage_mult)),
    ]
    if bool(getattr(args, "use_patterns", False)):
        repro_full.append("--use_patterns")
    if bool(use_patterns_appendix):
        repro_full.append("--use_patterns_appendix")
    if bool(getattr(args, "no_patterns", False)):
        repro_full.append("--no_patterns")
    if bool(getattr(args, "run_idaliia", False)):
        repro_full.append("--run_idaliia")
    if bool(getattr(args, "fundamental_from_idaliia", False)):
        repro_full.append("--fundamental_from_idaliia")
    if str(getattr(args, "fundamental_embed_path", "") or "").strip():
        repro_full.extend(["--fundamental_embed_path", str(args.fundamental_embed_path)])

    if bool(getattr(args, "no_llm", False)):
        repro_full.append("--no_llm")
    else:
        repro_full.append("--yes_openai")
        repro_full.extend(["--openai_model", str(args.openai_model)])

    if bool(getattr(args, "export_html", False)):
        repro_full.append("--export_html")

    repro_full.extend(["--out_dir", str(args.out_dir), "--template_dir", str(args.template_dir)])
    run_params["repro_cmd"] = " ".join(repro_full)

    # Short-form command for reports (key parameters only; keep the appendix clean).
    repro_short = [
        "python",
        "run_demo.py",
        "--ticker",
        str(args.ticker),
        "--years",
        str(int(args.years)),
        "--as_of",
        ("latest" if as_of is None else str(as_of)),
        "--train_end",
        str(args.train_end),
        "--val_end",
        str(args.val_end),
        "--trading_cost",
        str(float(args.trading_cost)),
        "--target_vol",
        str(float(args.target_vol)),
    ]
    # Fundamental overlay flags (if used)
    if str(args.fundamental_mode).lower() != "report_only" or bool(getattr(args, "run_idaliia", False)) or bool(getattr(args, "fundamental_from_idaliia", False)):
        repro_short.extend(["--fundamental_mode", str(args.fundamental_mode)])
        repro_short.extend(["--sell_leverage_mult", str(float(args.sell_leverage_mult))])
    if bool(getattr(args, "run_idaliia", False)):
        repro_short.append("--run_idaliia")
    if bool(getattr(args, "fundamental_from_idaliia", False)):
        repro_short.append("--fundamental_from_idaliia")

    # Export toggles
    if bool(getattr(args, "export_html", False)):
        repro_short.append("--export_html")

    # LLM provider (only if enabled)
    if not bool(getattr(args, "no_llm", False)):
        repro_short.append("--yes_openai")
        repro_short.extend(["--openai_model", str(args.openai_model)])

    run_params["repro_cmd_short"] = " ".join(repro_short)

    payload = build_report_payload(
        ticker=args.ticker,
        outputs_dir=out_dir,
        run_params=run_params,
        fundamental_view=fundamental_view,
    )
    payload_path = save_report_payload(payload, out_dir / "report_inputs.json")

    return {
        "out_dir": str(out_dir),
        "out_main": str(out_main),
        "out_app": str(out_app),
        "payload_path": str(payload_path),
        "payload": payload,
    }


def main() -> None:
    # Load .env (if present) so teachers can run by only editing one file (no shell config needed).
    # This is intentionally a tiny loader (no python-dotenv dependency).
    load_dotenv_file(".env", override=False)

    args = parse_args()
    info = run_pipeline(args)

    out_dir = Path(info["out_dir"])
    payload = info["payload"]

    print(f"DONE. Outputs written to: {out_dir.resolve()}")
    print(f"Report payload: {Path(info['payload_path']).resolve()}")

    md_path = out_dir / f"{args.ticker}_investment_report.md"

    # If LLM is disabled but export_html is set, reuse an existing markdown report.
    # This allows re-rendering HTML without any LLM/API calls (PDF is via browser print).
    if args.no_llm:
        if args.export_html and md_path.exists():
            md_existing = md_path.read_text(encoding="utf-8")
            md_existing = ensure_appendices(md_existing, payload)
            md_path.write_text(md_existing, encoding="utf-8")
            print(f"Reused Markdown report: {md_path.resolve()}")

            if args.export_html:
                main_dir = Path(info["out_main"])
                app_dir = Path(info["out_app"])
                html = render_html_report(
                    template_dir=args.template_dir,
                    template_name="report.html",
                    markdown_report=md_existing,
                    payload=payload,
                    figures_main=sorted(main_dir.glob("*.png")),
                    figures_appendix=sorted(app_dir.glob("*.png")),
                )
                html_path = out_dir / f"{args.ticker}_investment_report.html"
                save_html(html, html_path)
                print(f"Wrote HTML report: {html_path.resolve()}")

        return

    if not bool(getattr(args, "yes_openai", False)):
        raise SystemExit(
            "Refusing to call OpenAI without explicit confirmation. Re-run with: --yes_openai"
        )

    # ---- LLM report ----
    md = generate_report_markdown(
        payload,
        openai_model=args.openai_model,
    )

    # Deterministic post-process: ensure Appendix A-D exists even if the LLM omits them.
    md = ensure_appendices(md, payload)
    md_path.write_text(md, encoding="utf-8")
    print(f"Wrote Markdown report: {md_path.resolve()}")

    issues = _validate_llm_output(md, payload)
    if issues:
        issues_path = out_dir / "llm_validation.txt"
        issues_path.write_text("\n".join(issues), encoding="utf-8")
        print("LLM output validation warnings:")
        for msg in issues:
            print(" -", msg)
        print(f"Saved validation report: {issues_path.resolve()}")

    # ---- HTML export ----
    if args.export_html:
        main_dir = Path(info["out_main"])
        app_dir = Path(info["out_app"])
        html = render_html_report(
            template_dir=args.template_dir,
            template_name="report.html",
            markdown_report=md,
            payload=payload,
            figures_main=sorted(main_dir.glob("*.png")),
            figures_appendix=sorted(app_dir.glob("*.png")),
        )
        html_path = out_dir / f"{args.ticker}_investment_report.html"
        save_html(html, html_path)
        print(f"Wrote HTML report: {html_path.resolve()}")


if __name__ == "__main__":
    main()
