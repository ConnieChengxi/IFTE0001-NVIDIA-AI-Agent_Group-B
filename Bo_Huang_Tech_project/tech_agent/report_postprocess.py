from __future__ import annotations

import re
from typing import Any


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    h = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join("| " + " | ".join(str(x) for x in r) + " |" for r in rows)
    return "\n".join([h, sep, body])


def _fmt_num(x: Any) -> str:
    try:
        return f"{float(x):.4f}"
    except Exception:
        return "—"


def _fmt_pct_from_decimal(x: Any) -> str:
    try:
        v = float(x)
        return f"{v:.4f} ({v*100:.2f}%)"
    except Exception:
        return "—"


def _find_metric(rows: list[dict[str, Any]] | None, contains: str) -> dict[str, Any] | None:
    if not rows:
        return None
    c = contains.lower()
    for r in rows:
        name = str(r.get("name", "")).lower()
        if c in name:
            return r
    return None


def _appendix_a(payload: dict[str, Any]) -> str:
    run = payload.get("run_params", {}) if isinstance(payload, dict) else {}
    sens = run.get("sensitivity_full") if isinstance(run, dict) else None
    if not isinstance(sens, dict):
        return "### A.2 Parameter Sensitivity (Main Strategy)\n\nNot available for this run.\n"

    best = sens.get("best_by_sharpe", {}) if isinstance(sens.get("best_by_sharpe"), dict) else {}
    ranges = sens.get("ranges", {}) if isinstance(sens.get("ranges"), dict) else {}
    grid = sens.get("grid", []) if isinstance(sens.get("grid"), list) else []

    lines = [
        "### A.2 Parameter Sensitivity",
        "",
        "This robustness check varies the main-strategy parameter grid on the **full sample** and reports how performance changes.",
        "",
        f"- Best-by-Sharpe: {best.get('params_str','—')} "
        f"(Sharpe {_fmt_num(best.get('Sharpe'))}, total return {_fmt_num(best.get('total_return'))}, max drawdown {_fmt_num(best.get('max_drawdown'))}).",
        f"- Ranges across grid: Sharpe {_fmt_num(ranges.get('Sharpe_min'))} to {_fmt_num(ranges.get('Sharpe_max'))}; "
        f"total return {_fmt_num(ranges.get('total_return_min'))} to {_fmt_num(ranges.get('total_return_max'))}; "
        f"max drawdown {_fmt_num(ranges.get('max_drawdown_min'))} to {_fmt_num(ranges.get('max_drawdown_max'))}.",
        "",
        "**Parameter range rationale.** "
        "Economic and mechanistic interpretation: the grid varies a small set of interpretable parameters with clear financial meaning. "
        "The fast/slow EMA windows correspond to medium-to-long trend horizons (avoiding short-term noise fitting). "
        "The regime buffer defines a narrow band around the slow EMA for bull/neutral/bear classification, reducing boundary whipsaws. "
        "The volatility window sets the time scale for realized-volatility estimation used in volatility targeting. "
        "Overall, the grid is intentionally compact: it explores plausible time horizons and risk-estimation windows rather than optimizing over highly flexible, hard-to-explain knobs.",
        "",
    ]

    if grid:
        headers = ["Params", "Sharpe", "Total Return", "Max Drawdown"]
        rows = []
        for r in grid:
            if not isinstance(r, dict):
                continue
            rows.append(
                [
                    r.get("params_str", "—"),
                    _fmt_num(r.get("Sharpe")),
                    _fmt_num(r.get("total_return")),
                    _fmt_num(r.get("max_drawdown")),
                ]
            )
        lines.append(_md_table(headers, rows))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _appendix_split_rationale(payload: dict[str, Any]) -> str:
    """Explain the Train/Validation/Test split deterministically (appendix placement).

    The user wants split rationale in the appendix (not the main report), and we want this to be
    reproducible even if an LLM omits the explanation.
    """
    run = payload.get("run_params", {}) if isinstance(payload, dict) else {}
    train_end = run.get("train_end") if isinstance(run, dict) else None
    val_end = run.get("val_end") if isinstance(run, dict) else None
    meta = run.get("yfinance_meta", {}) if isinstance(run, dict) else {}
    start = meta.get("start_date") if isinstance(meta, dict) else None
    end = meta.get("end_date") if isinstance(meta, dict) else None

    def _d(x: Any) -> str:
        try:
            return str(x).split(" ")[0]
        except Exception:
            return "—"

    lines = [
        "## Appendix A. Parameter Selection and Robustness",
        "",
        "### A.1 Dataset Split & Selection Framework",
        "",
        "We use a simple time-based split to reduce overfitting risk and to keep the parameter-selection process auditable.",
        "",
        f"- **Sample window (data)**: {_d(start)} to {_d(end)}.",
        f"- **Split dates**: Train end = {_d(train_end)}; Validation end = {_d(val_end)}; Test = remaining tail period.",
        "",
        "Segment roles:",
        "- **Train**: estimate rolling statistics/calibrations (e.g., volatility baseline) without peeking into later periods.",
        "- **Validation**: select parameters (e.g., choose the best setting by validation Sharpe within a small grid).",
        "- **Test**: out-of-sample sanity check to confirm the chosen configuration is not purely an in-sample artifact.",
        "",
        "Motivation:",
        "- **Anti-leakage**: prevents look-ahead bias in calibration and selection.",
        "- **Traceability**: links the chosen parameters to an explicit validation criterion.",
        "- **Falsifiability**: provides an out-of-sample checkpoint before drawing conclusions.",
        "",
        "Note: the MAIN report still presents full-sample performance for transparency, but parameter choice is driven by the validation segment to reduce selection bias.",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _appendix_b_cd(payload: dict[str, Any]) -> str:
    """
    Appendix B/C/D need both quantitative comparison and the user's requested critical-thinking narrative.
    We render a compact comparison table from appendix metrics (if present).
    """
    outs = payload.get("outputs", {}) if isinstance(payload, dict) else {}
    app = outs.get("appendix", {}) if isinstance(outs, dict) else {}
    rows = app.get("metrics") if isinstance(app, dict) else None

    # Names are produced by run_demo (Benchmark / Strategy / MA / optional patterns / optional fundamental filter variant)
    bench = _find_metric(rows, "buy & hold") or _find_metric(rows, "benchmark")
    main = _find_metric(rows, "strategy") or _find_metric(rows, "hybrid main")
    ma = _find_metric(rows, "baseline") or _find_metric(rows, "ma(") or _find_metric(rows, "ma")
    volc = _find_metric(rows, "volume confirm")
    pat = _find_metric(rows, "patterns")
    fund = _find_metric(rows, "fundamental filter")

    def pick(r: dict[str, Any] | None, k: str) -> Any:
        return None if not r else r.get(k)

    # If the overlay is enabled but non-binding (e.g., HOLD/BUY), the "fundamental filter" curve is
    # identical to Main and may be intentionally omitted from appendix metrics to avoid misleading legends.
    run = payload.get("run_params", {}) if isinstance(payload, dict) else {}
    fund_overlay = payload.get("fundamental_overlay", None)
    overlay_used = bool(run.get("overlay_used_in_backtest")) if isinstance(run, dict) else False
    fund_mode = (run.get("fundamental_mode") if isinstance(run, dict) else None) or "—"
    sell_mult = run.get("sell_leverage_mult") if isinstance(run, dict) else None
    rating = None
    if isinstance(fund_overlay, dict):
        rating = str(fund_overlay.get("rating") or "").strip().upper() or None

    fund_non_binding = bool(overlay_used and fund_mode == "filter" and rating in ("BUY", "HOLD") and fund is None)
    pat_requested = bool(run.get("use_patterns_appendix") or run.get("use_patterns")) if isinstance(run, dict) else False

    # Build a compact comparison table across strategies if we have at least benchmark+main.
    table_md = ""
    if bench and main:
        headers = ["Metric", "Benchmark", "Main", "MA-only", "Volume confirm", "Patterns", "Fund filter"]
        keys = [
            ("CAGR", "CAGR", _fmt_pct_from_decimal),
            ("Sharpe", "Sharpe", _fmt_num),
            ("Max Drawdown", "max_drawdown", _fmt_pct_from_decimal),
            ("Hit Rate", "hit_rate", _fmt_pct_from_decimal),
            ("Turnover", "turnover_sum", _fmt_num),
            ("Exposure", "exposure", _fmt_pct_from_decimal),
            ("Total Return", "total_return", _fmt_pct_from_decimal),
        ]
        tr = []
        for label, key, fmt in keys:
            # Fund filter column: if it is non-binding, show explicitly that it's the same as Main.
            fund_cell = "—"
            if fund_non_binding:
                fund_cell = "Same as Main (non-binding)"
            elif fund:
                fund_cell = fmt(pick(fund, key))

            tr.append(
                [
                    label,
                    fmt(pick(bench, key)),
                    fmt(pick(main, key)),
                    fmt(pick(ma, key)) if ma else "—",
                    fmt(pick(volc, key)) if volc else "—",
                    fmt(pick(pat, key)) if pat else "—",
                    fund_cell,
                ]
            )
        table_md = _md_table(headers, tr)

    # --- Appendix B: Discussion split into MA-only and Pattern-enabled variants ---
    b_lines: list[str] = [
        "## Appendix B. Strategy Comparison",
        "This section provides a qualitative discussion of experimental variants relative to the main strategy.",
        "",
    ]

    # Summary bullets across experiments (high-level, non-promotional).
    try:
        def _delta(a: Any, b: Any) -> str:
            try:
                return f"{(float(a) - float(b)):+.4f}"
            except Exception:
                return "—"

        def _delta_pct(a: Any, b: Any) -> str:
            try:
                return f"{(float(a) - float(b)) * 100:+.2f}%"
            except Exception:
                return "—"

        if main and (ma or volc or pat):
            b_lines += [
                "### B.0 Summary of experimental variants",
                "Compared with the main strategy, the appendix variants illustrate the empirical trade-off between simplicity, confirmation filters, and added feature complexity:",
                "",
            ]

            if ma:
                b_lines += [
                    f"- **MA-only crossover**: higher exposure and higher headline return, but materially larger drawdown (drawdown increases by {_delta_pct(pick(ma,'max_drawdown'), pick(main,'max_drawdown'))} versus Main).",
                ]
            if volc:
                b_lines += [
                    f"- **Volume-confirmed entry**: slightly lower exposure with similar turnover; risk-adjusted performance changes modestly (Sharpe differs by {_delta(pick(volc,'Sharpe'), pick(main,'Sharpe'))} versus Main).",
                ]
            if pat:
                b_lines += [
                    f"- **Pattern-enabled**: turnover is materially higher (increase of {_delta(pick(pat,'turnover_sum'), pick(main,'turnover_sum'))} versus Main), with a weaker risk-adjusted profile in this run.",
                ]
            b_lines += ["", "These comparisons are descriptive (full-sample backtests) and are included for robustness/interpretability rather than as primary recommendations.", ""]
    except Exception:
        # Keep appendix generation robust; omit summary if anything goes wrong.
        pass

    # B.1 MA-only
    b_lines += [
        "### B.1 MA-only crossover strategy",
        "We compare a simple moving-average crossover rule against the benchmark and the main strategy to illustrate how reducing model complexity can change the risk profile.",
        "",
    ]
    if bench and main and ma:
        headers = ["Metric", "Benchmark", "Main", "MA-only crossover"]
        keys = [
            ("CAGR", "CAGR", _fmt_pct_from_decimal),
            ("Sharpe", "Sharpe", _fmt_num),
            ("Max Drawdown", "max_drawdown", _fmt_pct_from_decimal),
            ("Hit Rate", "hit_rate", _fmt_pct_from_decimal),
            ("Turnover", "turnover_sum", _fmt_num),
            ("Exposure", "exposure", _fmt_pct_from_decimal),
            ("Total Return", "total_return", _fmt_pct_from_decimal),
        ]
        rows_ma = [[label, fmt(pick(bench, k)), fmt(pick(main, k)), fmt(pick(ma, k))] for label, k, fmt in keys]
        b_lines += [_md_table(headers, rows_ma), ""]
    else:
        b_lines += ["Not provided in this run.", ""]

    b_lines += [
        "**Discussion.** A simple MA-only baseline can capture strong trends with high exposure, but it may also exhibit materially larger drawdowns and a weaker risk-adjusted profile depending on the path of returns.",
        "",
    ]

    # B.2 Volume confirmation (entry-only)
    b_lines += [
        "### B.2 Volume-confirmed entry filter",
        "This experiment adds a simple volume-based confirmation to the main strategy: entries are only allowed when **relative volume** is above a threshold, as a proxy for stronger market participation.",
        "",
    ]
    if bench and main and volc:
        headers = ["Metric", "Benchmark", "Main", "Volume confirm"]
        keys = [
            ("CAGR", "CAGR", _fmt_pct_from_decimal),
            ("Sharpe", "Sharpe", _fmt_num),
            ("Max Drawdown", "max_drawdown", _fmt_pct_from_decimal),
            ("Hit Rate", "hit_rate", _fmt_pct_from_decimal),
            ("Turnover", "turnover_sum", _fmt_num),
            ("Exposure", "exposure", _fmt_pct_from_decimal),
            ("Total Return", "total_return", _fmt_pct_from_decimal),
        ]
        rows_vol = [[label, fmt(pick(bench, k)), fmt(pick(main, k)), fmt(pick(volc, k))] for label, k, fmt in keys]
        b_lines += [_md_table(headers, rows_vol), ""]
    else:
        b_lines += ["Not provided in this run.", ""]

    b_lines += [
        "**Discussion.** Volume confirmation can reduce marginal trades and lower exposure, which may improve robustness in sideways regimes, but it can also miss early trend participation; the net effect must be evaluated empirically (as in the table above).",
        "",
    ]

    # B.3 Patterns
    b_lines += [
        "### B.3 Pattern-enabled variant",
        "This experiment augments the technical decision rule with lightweight, interpretable price-action features computed from OHLCV bars.",
        "",
        "Pattern features (as implemented):",
        "- **Bullish/Bearish engulfing**: two-candle body engulfing heuristic.",
        "- **Hammer / Shooting star**: wick-to-body ratio heuristic (reversal-like candles).",
        "- **Donchian breakout**: close breaking above/below a lagged rolling channel (trend continuation / breakdown).",
        "",
        "Integration policy (signal layer): bullish patterns can contribute to the long-score when enabled; bearish patterns act as an explicit risk-off exit trigger (close position).",
        "",
    ]
    if bench and main and pat:
        headers = ["Metric", "Benchmark", "Main", "Patterns"]
        keys = [
            ("CAGR", "CAGR", _fmt_pct_from_decimal),
            ("Sharpe", "Sharpe", _fmt_num),
            ("Max Drawdown", "max_drawdown", _fmt_pct_from_decimal),
            ("Hit Rate", "hit_rate", _fmt_pct_from_decimal),
            ("Turnover", "turnover_sum", _fmt_num),
            ("Exposure", "exposure", _fmt_pct_from_decimal),
            ("Total Return", "total_return", _fmt_pct_from_decimal),
        ]
        rows_pat = [[label, fmt(pick(bench, k)), fmt(pick(main, k)), fmt(pick(pat, k))] for label, k, fmt in keys]
        b_lines += [_md_table(headers, rows_pat), ""]
    else:
        if pat_requested:
            b_lines += [
                "Requested but not present in this run's metrics table (the experiment may not have been executed or its outputs were not saved).",
                "",
            ]
        else:
            b_lines += ["Not enabled in this run.", ""]

    b_lines += [
        "**Discussion.** Pattern features increase model complexity and can raise instability/overfitting risk. If the pattern-enabled variant does not improve the risk-adjusted profile (e.g., Sharpe and drawdown) relative to the main strategy, it is best treated as an appendix experiment rather than as the primary recommendation.",
        "",
    ]

    # --- Appendix C: Fundamental filter (moved from D -> C) ---
    rating = None
    as_of = None
    source = None
    notes = None
    if isinstance(fund_overlay, dict):
        rating = str(fund_overlay.get("rating") or "").strip().upper() or None
        as_of = fund_overlay.get("as_of")
        source = fund_overlay.get("source")
        notes = fund_overlay.get("notes")

    applied = bool(overlay_used and fund_mode == "filter")

    c_lines = [
        "## Appendix C. Fundamental Overlay",
        "In this project, the main strategy includes a fundamental overlay as part of the **risk-management layer**. "
        "Alongside the technical rules, we incorporate a third-party fundamental assessment (Buy/Hold/Sell) as a **risk-control overlay**. "
        "It is treated as external context that constrains sizing, not as an alpha signal that generates trades. In other words, the chart-based rules still decide when the strategy is long or flat; fundamentals only influence how much exposure we are willing to carry.",
        "",
        "In practical terms, the external view is grounded in standard market-facing fundamentals: valuation multiples (e.g., forward/trailing P/E, P/S, P/B, EV/EBITDA) and sell-side expectations (e.g., consensus recommendation and analyst target-price range). "
        "These inputs do not enter the strategy as a return predictor; they provide an interpretable check on whether the market is pricing the stock at historically rich levels and whether analyst expectations are broadly supportive. "
        "Within this project, that context is deliberately translated into a sizing constraint rather than an entry/exit signal.",
        "",
        "The overlay is implemented as a **hard exposure ceiling**. If the external rating is **SELL**, the strategy reduces the maximum allowable leverage by a fixed multiplier "
        f"(a SELL ceiling multiplier of {sell_mult}). If the rating is **BUY/HOLD**, the ceiling is typically non-binding, so the realised return path can be identical to the pure technical strategy.",
        "",
        "To preserve point-in-time integrity (no look-ahead bias), the rating is applied from its stated **as-of** date forward. The backtest does not assume that future rating changes were known in advance.",
        "",
        f"In this run, the overlay was {'applied in the backtest as a sizing cap' if applied else 'configured as context only and not applied to sizing'}.",
        "Latest available view in the payload: "
        f"Rating: {rating or 'Not provided'}; As-of date: {as_of or 'Not provided'}; Source: {source or 'Not provided'}."
        + (f" Notes: {notes}." if notes else " Notes: not provided."),
        "",
        "Practical note: when the rating is BUY/HOLD, the cap may not bind; in that case, the \"Tech+Fund\" variant can be indistinguishable from the main strategy and a separate curve may be omitted to avoid a misleading comparison.",
        "",
    ]

    # Reproducibility: keep the exact command out of the MAIN narrative to avoid clutter,
    # but include it in Appendix D where methodology details live.
    repro_cmd = None
    try:
        rp = payload.get("run_params", {}) if isinstance(payload, dict) else {}
        if isinstance(rp, dict):
            repro_cmd = rp.get("repro_cmd_short") or rp.get("repro_cmd")
    except Exception:
        repro_cmd = None
    # Intentionally do not print rerun commands into the report body.
    # The exact command remains available in outputs/report_inputs.json (run_params.repro_cmd/repro_cmd_short)
    # for reproducibility without cluttering the PDF/HTML layout.

    return "\n".join(b_lines + c_lines).rstrip() + "\n"


def ensure_appendices(markdown_report: str, payload: dict[str, Any]) -> str:
    """
    Ensure the report includes Appendix A-D sections, even if the LLM omits them.
    Also keeps appendices in sync with the latest deterministic payload by replacing any existing
    Appendix A-D block.

    This is deterministic and does not require any additional LLM calls.
    """
    md = (markdown_report or "").strip()

    # ---- Normalize Section 1 (Investment Instrument & Data) to avoid repetitive bullets ----
    # The report should keep data description compact and analyst-friendly: fold frequency/window/return-definition
    # into a single dataset description bullet and remove redundant standalone bullets.
    def _normalize_section1(md_text: str) -> str:
        if not isinstance(payload, dict):
            return md_text

        ticker = str(payload.get("ticker") or "").strip() or "the instrument"
        run = payload.get("run_params", {}) if isinstance(payload.get("run_params", {}), dict) else {}
        years = run.get("years")
        years_s = str(int(years)) if isinstance(years, (int, float)) else "10"
        trading_cost = run.get("trading_cost")

        # Compact, analyst wording: Yahoo Finance adjusted close is used for return computation.
        ds_line = (
            f"- **Dataset Description:** {years_s} years of daily OHLCV (Open/High/Low/Close/Volume) for {ticker}, "
            "sourced from Yahoo Finance (yfinance). Returns are measured close-to-close using the **adjusted close** "
            "price series, which accounts for splits and dividends."
        )

        # Isolate section 1 and rewrite within it. Accept either "## 1. ..." or "## 1 ..."
        m = re.search(r"(?ms)^##\s*1\.?\s*Investment Instrument & Data\s*\n(.*?)(?=^##\s*2\.)", md_text)
        if not m:
            return md_text

        # Deterministic canonical Section 1 block (avoid drift / duplication from LLM output).
        tc_line = f"- **Transaction Cost Assumption**: {trading_cost} per trade." if trading_cost is not None else "- **Transaction Cost Assumption**: Not provided in this run."
        new_block = "\n".join(
            [
                f"- **Ticker**: {ticker}",
                ds_line,
                tc_line,
                "- **Execution Timing**: Decision-time signal computed at bar close; execution occurs on the next bar via a 1-bar delay in backtest.",
                "",
            ]
        )
        return md_text[: m.start(1)] + new_block + md_text[m.end(1):]

    md = _normalize_section1(md)

    # ---- Fix common LLM drift in Section 0 (Investment Summary) ----
    def _fix_summary_fundamental_binding(md_text: str) -> str:
        """Correct misleading summary phrasing about fundamental caps when rating is BUY/HOLD."""
        if not isinstance(payload, dict):
            return md_text
        run = payload.get("run_params", {}) if isinstance(payload.get("run_params", {}), dict) else {}
        rating = None
        fund = payload.get("fundamental_view") or payload.get("fundamental_overlay") or run.get("fundamental_view") or None
        if isinstance(fund, dict):
            rating = str(fund.get("rating") or "").strip().upper() or None

        # Only rewrite if the report claims the cap is binding under BUY/HOLD.
        if rating in ("BUY", "HOLD"):
            sec = re.search(r"(?ms)^##\s*0\.\s*Investment Summary\s*\n(.*?)(?=^##\s*1\.)", md_text)
            if not sec:
                return md_text
            block = sec.group(1)
            if re.search(r"(?i)\bbinding\b.*\bcap\b|\bbinding\b.*\bleverage\b", block):
                clean = re.sub(
                    r"(?im)^\s*[-*]\s+.*binding.*$",
                    "- The fundamental overlay is currently **non-binding** under a BUY/HOLD view; it becomes binding only under a SELL rating (which mechanically caps maximum exposure).",
                    block,
                )
                return md_text[: sec.start(1)] + clean + md_text[sec.end(1):]
        return md_text

    md = _fix_summary_fundamental_binding(md)

    def _inject_main_discussion(md_text: str) -> str:
        """
        Insert a brief, professional discussion note in the MAIN report.
        Keep it short (2-4 sentences) and avoid detailed appendix strategy comparisons here.
        """
        # Avoid double-inserting if the report already contains our marker.
        if "Discussion (brief)" in md_text:
            return md_text

        # Build a short, non-hype discussion grounded in available metrics.
        try:
            outs = payload.get("outputs", {}) if isinstance(payload, dict) else {}
            rows = outs.get("main", {}).get("metrics", []) if isinstance(outs, dict) else []
        except Exception:
            rows = []

        def _pick(rows_: list[dict[str, Any]] | None, kind: str) -> dict[str, Any] | None:
            if not rows_:
                return None
            for r in rows_:
                name = str(r.get("name", "")).lower()
                if kind == "benchmark" and ("buy & hold" in name or "benchmark" in name):
                    return r
                if kind == "main" and ("strategy" in name and "appendix" not in name):
                    return r
            return rows_[0] if rows_ else None

        bench = _pick(rows, "benchmark")
        main = _pick(rows, "main")

        def _fmt_pct(x: Any) -> str:
            try:
                return f"{float(x) * 100:.2f}%"
            except Exception:
                return "—"

        def _fmt_num(x: Any) -> str:
            try:
                return f"{float(x):.2f}"
            except Exception:
                return "—"

        sharpe_main = _fmt_num(main.get("Sharpe")) if isinstance(main, dict) else "—"
        dd_main = _fmt_pct(main.get("max_drawdown")) if isinstance(main, dict) else "—"
        sharpe_bm = _fmt_num(bench.get("Sharpe")) if isinstance(bench, dict) else "—"
        dd_bm = _fmt_pct(bench.get("max_drawdown")) if isinstance(bench, dict) else "—"

        note = (
            "**Discussion (brief).** This strategy is intentionally designed to be explainable and risk-managed "
            "(score + hysteresis + volatility targeting), which typically trades some raw upside for a smoother return path. "
            f"In this run, the risk-adjusted profile is summarized by Sharpe={sharpe_main} and max drawdown={dd_main} "
            f"(vs benchmark Sharpe={sharpe_bm}, max drawdown={dd_bm}). "
            "Supplementary robustness checks and alternative signal variants are reported in the Appendix."
        )

        # Insert the note right before the Risks section if present; otherwise append to the end of main.
        m_risks = re.search(r"(?mi)^\s*##\s*3\.\s*risks\s*&\s*limitations\s*$", md_text)
        if m_risks:
            insert_at = m_risks.start()
            return (md_text[:insert_at].rstrip() + "\n\n" + note + "\n\n" + md_text[insert_at:].lstrip()).strip()

        return (md_text.rstrip() + "\n\n" + note + "\n").strip()

    md = _inject_main_discussion(md)

    def _strip_turnover_from_summary(md_text: str) -> str:
        """
        Remove turnover/trade-count commentary from the Investment Summary section (Section 0).
        The summary should focus on stance/action/evidence/risk boundaries; microstructure stats belong later.
        """
        m0 = re.search(r"(?mis)^\s*##\s*0\.\s*Investment Summary\b.*?(?=^\s*##\s*1\.)", md_text)
        if not m0:
            return md_text
        sec = m0.group(0)
        # Drop bullet lines that mention turnover or "lower turnover"/"high turnover".
        sec = re.sub(r"(?mi)^\s*[-*]\s+.*turnover.*$\n?", "", sec)
        # Also drop bullets that justify trade count as a turnover proxy.
        sec = re.sub(r"(?mi)^\s*[-*]\s+.*\btrade[s]?\b.*turnover.*$\n?", "", sec)
        # If turnover is embedded in a longer bullet, remove the sentence fragment.
        sec = re.sub(r"(?i)\b[^.]*turnover[^.]*\.\s*", "", sec)
        sec = re.sub(r"\n{3,}", "\n\n", sec).strip() + "\n\n"
        return md_text[: m0.start()] + sec + md_text[m0.end() :]

    def _strip_main_repro_block(md_text: str) -> str:
        """
        Remove any "Reproducibility" section that an LLM might place in the MAIN report.
        We keep reproducibility details in Appendix D instead (deterministic, from payload.run_params.repro_cmd).
        """
        m_app = re.search(r"(?mi)^\s*###\s*appendix\b.*$", md_text) or re.search(r"(?mi)^\s*##\s*appendix\b.*$", md_text)
        main_part = md_text if not m_app else md_text[: m_app.start()]
        tail = "" if not m_app else md_text[m_app.start():]

        # Remove a headed reproducibility block (common variants).
        main_part = re.sub(
            r"(?mis)^\s*#{2,4}\s*reproducibility\b.*?(?=^\s*#{2,4}\s+|\Z)",
            "",
            main_part,
        ).strip()

        # Remove any standalone code fence in MAIN that contains the run_demo command.
        main_part = re.sub(
            r"(?mis)```(?:bash)?\s*\n\s*python\s+run_demo\.py[^\n]*\n```",
            "",
            main_part,
        ).strip()

        return (main_part + "\n\n" + tail).strip() if tail else main_part

    md = _strip_main_repro_block(md)
    md = _strip_turnover_from_summary(md)

    def _fix_return_definition_line(md_text: str) -> str:
        """
        Make the return-definition line deterministic and consistent with the actual data metadata.
        LLMs sometimes copy stale wording (e.g., 'stooq fallback') across runs.
        """
        if not isinstance(payload, dict):
            return md_text
        run = payload.get("run_params", {}) if isinstance(payload.get("run_params", {}), dict) else {}
        meta = run.get("yfinance_meta", {}) if isinstance(run.get("yfinance_meta", {}), dict) else {}
        rd = meta.get("return_definition")
        if not isinstance(rd, str) or not rd.strip():
            return md_text
        rd = rd.strip()

        # Replace the first occurrence in the Scope/Data bullet list.
        return re.sub(
            r"(?m)^\s*[-*]\s*\*\*Return definition\*\*:?.*$",
            f"- **Return definition**: {rd}",
            md_text,
            count=1,
        )

    md = _fix_return_definition_line(md)

    def _fix_sample_window_line(md_text: str) -> str:
        """
        Keep the sample window line consistent with metadata (important when we use cached data).
        """
        if not isinstance(payload, dict):
            return md_text
        run = payload.get("run_params", {}) if isinstance(payload.get("run_params", {}), dict) else {}
        meta = run.get("yfinance_meta", {}) if isinstance(run.get("yfinance_meta", {}), dict) else {}
        s = meta.get("start_date")
        e = meta.get("end_date")
        years = run.get("years")
        as_of = run.get("as_of")
        try:
            s = str(s).split(" ")[0]
            e = str(e).split(" ")[0]
        except Exception:
            return md_text
        if not (s and e):
            return md_text
        ao = str(as_of) if as_of is not None else "latest"
        # Avoid repeating "10 years" when we also provide a dataset description bullet.
        # Keep this line focused on concrete dates for reproducibility.
        repl = f"- **Sample window**: {s} to {e} (as of {ao})."
        return re.sub(
            r"(?m)^\s*[-*]\s*\*\*Sample window\*\*:.*$",
            repl,
            md_text,
            count=1,
        )

    md = _fix_sample_window_line(md)

    def _ensure_ohlcv_bullet(md_text: str) -> str:
        """
        Ensure the report explicitly states the dataset is 10 years of daily OHLCV.
        This is a course requirement and should not depend on LLM phrasing.
        """
        low = md_text.lower()
        if "ohlcv" in low and "10 years" in low:
            return md_text

        # Prefer inserting right after the Sample window bullet in Section 1.
        bullet = "- **Dataset**: 10 years of daily OHLCV (Open/High/Low/Close/Volume)."
        if re.search(r"(?m)^\s*-\s*\*\*Dataset\*\*:", md_text):
            # If a dataset bullet exists but doesn't mention OHLCV, replace it.
            return re.sub(
                r"(?m)^\s*-\s*\*\*Dataset\*\*:.*$",
                bullet,
                md_text,
                count=1,
            )

        m_sw = re.search(r"(?m)^\s*-\s*\*\*Sample window\*\*:.*$", md_text)
        if m_sw:
            insert_at = m_sw.end()
            return (md_text[:insert_at] + "\n" + bullet + md_text[insert_at:]).strip()

        # Some LLM outputs combine frequency + window into a single bullet.
        m_fw = re.search(r"(?m)^\s*-\s*\*\*Data frequency and sample window\*\*:.*$", md_text, flags=re.I)
        if m_fw:
            insert_at = m_fw.end()
            return (md_text[:insert_at] + "\n" + bullet + md_text[insert_at:]).strip()

        # Fallback: insert near the top of Section 1 before Section 2 starts.
        m1 = re.search(r"(?mi)^\s*##\s*1\.\s.*$", md_text)
        m2 = re.search(r"(?mi)^\s*##\s*2\.\s.*$", md_text)
        if m1 and m2:
            head = md_text[: m2.start()].rstrip()
            tail = md_text[m2.start():].lstrip()
            # Insert after the first non-empty line in Section 1.
            parts = head.splitlines()
            out: list[str] = []
            inserted = False
            for line in parts:
                out.append(line)
                if (not inserted) and line.strip() and (not line.strip().startswith("##")):
                    out.append("")
                    out.append(bullet)
                    inserted = True
            if not inserted:
                out.append("")
                out.append(bullet)
            return ("\n".join(out).rstrip() + "\n\n" + tail).strip()

        return md_text

    md = _ensure_ohlcv_bullet(md)

    def _dedupe_data_frequency_line(md_text: str) -> str:
        """
        Avoid repeating the "10 years" phrase in multiple bullets in Section 1.
        We keep the sample-window + OHLCV dataset bullets as the place where horizon is stated,
        and keep the frequency bullet strictly about frequency (e.g., Daily (1d)).
        """
        if not isinstance(payload, dict):
            return md_text
        run = payload.get("run_params", {}) if isinstance(payload.get("run_params", {}), dict) else {}
        interval = str(run.get("interval") or "").strip()
        if interval:
            repl = f"- **Data frequency**: Daily ({interval})."
        else:
            repl = "- **Data frequency**: Daily."

        # Replace the first frequency bullet line in Section 1.
        md_text = re.sub(
            r"(?m)^\s*-\s*\*\*Data frequency\*\*:.*$",
            repl,
            md_text,
            count=1,
        )
        # Some LLM outputs merge both into one line: "Data Frequency: ...; Sample Window: ..."
        md_text = re.sub(
            r"(?m)^\s*-\s*\*\*Data Frequency\*\*:.*$",
            repl,
            md_text,
            count=1,
        )
        return md_text

    md = _dedupe_data_frequency_line(md)

    def _strip_governance_disclosure_from_body(md_text: str) -> str:
        """
        The disclosure belongs in the HTML sidebar (Disclaimer), not in the main narrative.
        Strip common "Governance disclosure" blocks that an LLM may include in the Risks section.
        """
        # Remove the numbered subsection heading and any following bullets until the next numbered item or section header.
        md_text = re.sub(
            r"(?mis)^\s*4\)\s*\*\*Governance disclosure.*?\n(?=^\s*\d+\)\s*\*\*|^\s*##\s+|\Z)",
            "",
            md_text,
        ).strip()
        # Remove any standalone disclosure bullets.
        md_text = re.sub(
            r"(?mi)^\s*-\s*This report narrative was drafted using.*$\n?",
            "",
            md_text,
        )
        md_text = re.sub(
            r"(?mi)^\s*This report was drafted using OpenAI[^\n]*\n?",
            "",
            md_text,
        )
        md_text = re.sub(
            r"(?mi)^\s*-\s*Disclosure:\s*OpenAI is used via a commercial/premium API\.\s*$\n?",
            "",
            md_text,
        )
        return md_text.strip()

    md = _strip_governance_disclosure_from_body(md)

    def _rewrite_arrow_pipelines(md_text: str) -> str:
        """
        Replace arrow-chains (→) with human prose. These chains tend to read like code, not an analyst report.
        We only rewrite lines that look like ordering/pipeline statements.
        """
        lines = md_text.splitlines()
        out: list[str] = []
        for line in lines:
            if "→" not in line:
                out.append(line)
                continue

            # Only rewrite likely pipeline/order descriptions; otherwise just replace the arrow.
            low = line.lower()
            if ("pipeline" in low or "order" in low) and ("decision" in low or "regime" in low or "volatility" in low):
                parts = [p.strip(" .;") for p in line.split("→") if p.strip()]
                if len(parts) >= 3:
                    first = parts[0]
                    mids = parts[1:-1]
                    last = parts[-1]
                    # Build a clean sentence.
                    sent = (
                        "The process runs in stages. It starts with "
                        + first.rstrip(".")
                        + ", then "
                        + ", then ".join(mids)
                        + ", and finally "
                        + last
                        + "."
                    )
                    out.append(sent)
                    continue

            out.append(line.replace("→", "then"))

        return "\n".join(out)

    md = _rewrite_arrow_pipelines(md)

    def _ensure_main_strategy_clarity(md_text: str) -> str:
        """
        Keep Sections 2.1/2.2 readable *and* faithful to code.
        We do not overwrite LLM prose, but we patch common omissions/drift with short,
        plain-English clarification paragraphs sourced from the payload.
        """
        if not isinstance(payload, dict):
            return md_text

        # Normalize legacy phrasing from prior postprocess versions.
        md_text = md_text.replace("Implementation clarifications (to avoid ambiguity):", "Clarifying note:")
        md_text = md_text.replace("Implementation clarifications (sizing pipeline):", "Clarifying note:")

        run = payload.get("run_params", {}) if isinstance(payload.get("run_params", {}), dict) else {}
        spec = payload.get("strategy_spec_main", {}) if isinstance(payload.get("strategy_spec_main", {}), dict) else {}
        snap = run.get("signal_snapshot") if isinstance(run.get("signal_snapshot", {}), dict) else {}

        entry_thr = (spec.get("hysteresis_state_machine", {}) or {}).get("entry_threshold")
        hold_thr = (spec.get("hysteresis_state_machine", {}) or {}).get("hold_threshold")
        ema_fast = (spec.get("trend_filter", {}) or {}).get("ema_fast")
        ema_slow = (spec.get("trend_filter", {}) or {}).get("ema_slow")
        buf = (spec.get("regime", {}) or {}).get("buffer_pct")
        target_vol = ((spec.get("risk_management", {}) or {}).get("vol_targeting", {}) or {}).get("target_vol")
        vol_window = ((spec.get("risk_management", {}) or {}).get("vol_targeting", {}) or {}).get("vol_window")

        def _fmt(x: Any) -> str:
            return "—" if x is None else str(x)

        # Patch: 2.1 should define signal_bin + timing + snapshot. Add a short paragraph if missing.
        m21 = re.search(r"(?mis)^\s*###\s*2\.1\b.*?(?=^\s*###\s*2\.2\b|\Z)", md_text)
        if m21:
            sec = m21.group(0)
            low = sec.lower()
            needs_signal_bin = "signal_bin" not in low
            needs_timing = ("next-bar" not in low) and ("1-bar" not in low) and ("execution" not in low)
            needs_snapshot = ("decision date" not in low) and ("recommended action" not in low) and ("signal snapshot" not in low)
            if needs_signal_bin or needs_timing or needs_snapshot:
                parts: list[str] = []
                if needs_signal_bin:
                    parts.append(
                        "In this implementation, the technical layer first produces a binary long/flat state called signal_bin. "
                        "A value of 1 means the strategy is permitted to hold a long position; a value of 0 means the strategy stays flat. "
                        "Position sizing is handled separately in Section 2.2."
                    )
                if needs_timing:
                    parts.append(
                        "Signals and target positions are computed at decision-time on each bar; execution is modeled as **next-bar execution** "
                        "via the single 1-bar shift inside the backtest."
                    )
                if needs_snapshot and snap:
                    parts.append(
                        f"Latest snapshot (decision date {snap.get('decision_date','—')}): "
                        f"long score {snap.get('long_score_last','—')} (entry threshold {snap.get('req_k_entry_last','—')}, hold threshold {snap.get('req_k_hold_last','—')}), "
                        f"recommended action {snap.get('recommended_action','—')}, "
                        f"decision-time target exposure {snap.get('position_target_last','—')}."
                    )
                clar_para = "Clarifying note: " + " ".join(parts)
                sec2 = sec.rstrip() + "\n\n" + clar_para.strip() + "\n\n"
                md_text = md_text[: m21.start()] + sec2 + md_text[m21.end():]

        # Patch: 2.2 common drift — bull exposure is NOT conditioned on "high score" beyond the state machine.
        m22 = re.search(r"(?mis)^\s*###\s*2\.2\b.*?(?=^\s*###\s*2\.3\b|\Z)", md_text)
        if m22:
            sec = m22.group(0)
            # Replace a common hallucinated sentence shape if present.
            sec = re.sub(
                r"(?mi)^.*bull.*demand.*score.*full exposure.*$",
                "Base exposure is determined by the long/flat state (signal_bin) and the 3-state regime (bull/neutral/bear), not by discretionary \"stronger\" scoring beyond the state-machine thresholds.",
                sec,
            )
            low = sec.lower()
            needs_mapping = ("bull" not in low) or ("neutral" not in low) or ("bear" not in low) or ("0.25" not in low)
            if needs_mapping:
                clar = (
                    "\n\n"
                    "Clarifying note: base exposure is mapped mechanically from the long/flat state and the 3-state regime — "
                    "bull → 1.0, neutral → 0.5, and bear → 0.25 **only** for the strongest signals (long_score=5); otherwise the strategy stays flat. "
                    f"Volatility targeting then scales this base exposure toward a target risk level (target volatility {_fmt(target_vol)} and a volatility estimation window of {_fmt(vol_window)} trading days), "
                    "with leverage caps (including the fundamental overlay when enabled) applied before execution.\n\n"
                )
                sec = sec.rstrip() + clar
            md_text = md_text[: m22.start()] + sec + md_text[m22.end():]

        return md_text

    md = _ensure_main_strategy_clarity(md)

    def _fix_visual_evidence_filename_placement(md_text: str) -> str:
        """
        Fix awkward phrasing where figure filenames are dropped as dangling tokens at sentence ends
        (e.g., "... market corrections. FULL_equity.png"). Rewrite to: "In FULL_equity.png, ...".
        """
        m25 = re.search(r"(?mis)^\s*###\s*2\.5\b.*?(?=^\s*##\s*3\b|\Z)", md_text)
        if not m25:
            return md_text

        sec = m25.group(0)
        lines = sec.splitlines()
        out_lines: list[str] = []

        fig_end_re = re.compile(
            r"^(?P<pre>\s*(?:\d+\.\s+|-+\s+)?(?:\*\*[^*]+\*\*:\s*)?)(?P<body>.*?)(?:\s+`?(?P<fig>FULL_[A-Za-z0-9_.-]+\.png)`?)\s*$"
        )

        for line in lines:
            m = fig_end_re.match(line)
            if not m:
                out_lines.append(line)
                continue

            pre = m.group("pre") or ""
            body = (m.group("body") or "").strip()
            fig = (m.group("fig") or "").strip()

            if not fig or not body:
                out_lines.append(line)
                continue

            # If already starts with an "In FULL_..." reference, keep it.
            if re.match(r"(?i)^in\s+`?FULL_[A-Za-z0-9_.-]+\.png`?,", body):
                out_lines.append(pre + body)
                continue

            out_lines.append(pre + f"In {fig}, " + body)

        sec2 = "\n".join(out_lines)

        # Fix a rare artifact where a bad backreference (\1) ended up in the report.
        # Replace by expected figure names based on the enumerated list item.
        fixed_lines: list[str] = []
        for ln in sec2.splitlines():
            if "\\1" not in ln:
                fixed_lines.append(ln)
                continue
            if re.match(r"^\s*1\.", ln):
                fixed_lines.append(ln.replace("\\1", "FULL_equity.png"))
            elif re.match(r"^\s*2\.", ln):
                fixed_lines.append(ln.replace("\\1", "FULL_drawdown.png"))
            elif re.match(r"^\s*3\.", ln):
                fixed_lines.append(ln.replace("\\1", "FULL_annual_return.png"))
            else:
                fixed_lines.append(ln.replace("\\1", "FULL_equity.png"))
        sec2 = "\n".join(fixed_lines)

        # Render filenames as plain text (not inline-code pills) for readability.
        sec2 = re.sub(r"`(FULL_[A-Za-z0-9_.-]+\.png)`", lambda m: m.group(1), sec2)
        return md_text[: m25.start()] + sec2 + md_text[m25.end() :]

    md = _fix_visual_evidence_filename_placement(md)

    # Do NOT overwrite the narrative of Sections 2.1/2.2 here.
    # Those sections are LLM-written; we keep deterministic enforcement limited to facts/labels elsewhere
    # to avoid producing a hard-to-read "code listing" in the main report.

    def _inject_data_source_note(md_text: str) -> str:
        """
        If the data layer fell back from Yahoo(yfinance) to Stooq, disclose it explicitly in the Scope & Data section.
        This is a common point of confusion for readers and should be deterministic (not LLM-dependent).
        """
        if not isinstance(payload, dict):
            return md_text
        run = payload.get("run_params", {}) if isinstance(payload.get("run_params", {}), dict) else {}
        meta = run.get("yfinance_meta", {}) if isinstance(run.get("yfinance_meta", {}), dict) else {}
        src = str(meta.get("source") or "").strip().lower()
        if not src:
            return md_text

        # Only inject a note if we used a fallback or if Yahoo failed but we still produced results.
        yerr = str(meta.get("yfinance_error") or "").strip()
        ychart_err = str(meta.get("yahoo_chart_error") or "").strip()
        warn_unadj = bool(meta.get("warning_unadjusted_fallback"))
        cache_hit = bool(meta.get("cache_hit"))
        cache_meta = meta.get("cache_meta") if isinstance(meta.get("cache_meta"), dict) else None

        if src == "stooq" or warn_unadj:
            note = "Yahoo Finance (yfinance) failed in this run, so the pipeline fell back to Stooq. "
            if yerr:
                note += f"Reason: {yerr}. "
            note += "Stooq provides **unadjusted** daily OHLCV; therefore returns are computed on unadjusted close for this run."
        elif src in ("yfinance", "yahoo_chart", "yahoo_patch"):
            # Yahoo is the data source; do not clutter the report body with an extra bullet.
            # If a prior run injected a note, remove it.
            return re.sub(
                r"(?m)^\s*[-*]\s*\*\*Data source note:\*\*.*$\n?",
                "",
                md_text,
            ).strip()
        else:
            return md_text

        # If a note already exists (from a prior run), replace it to match the *current* payload.
        if "**Data source note:**" in md_text:
            return re.sub(
                r"(?m)^\s*[-*]\s*\*\*Data source note:\*\*.*$",
                "- **Data source note:** " + note,
                md_text,
                count=1,
            )

        # Insert after the "Dataset Description" bullet if present; otherwise after the first bullet list in section 1.
        m_ds = re.search(r"(?mi)^(?:\s*[-*]\s*\*\*Dataset Description:?\\*\\*.*)$", md_text)
        if m_ds:
            insert_at = m_ds.end()
            return (md_text[:insert_at] + "\n- **Data source note:** " + note + md_text[insert_at:]).strip()

        # Fallback: insert near the top of Scope/Data section (before section 2 starts).
        m_scope = re.search(r"(?mi)^\s*##\s*1\.[^\n]*data[^\n]*$", md_text)
        if not m_scope:
            return md_text
        m_next = re.search(r"(?mi)^\s*##\s*2\.", md_text)
        cut = m_next.start() if m_next else len(md_text)
        head = md_text[:cut].rstrip()
        tail = md_text[cut:].lstrip()
        return (head + "\n\n- **Data source note:** " + note + "\n\n" + tail).strip()

    md = _inject_data_source_note(md)

    def _strip_split_from_main(md_text: str) -> str:
        # Remove the Train/Validation/Test split block from the main Scope & Data bullet list.
        # Typical formatting:
        # - **Train/Validation/Test split**: ...
        #   - Training end: ...
        #   - Validation end: ...
        #   - ...
        lines = md_text.splitlines()
        out: list[str] = []
        skip = False
        for i, line in enumerate(lines):
            if re.match(r"^\s*[-*]\s*\*\*Train/Validation/Test split\*\*:", line):
                skip = True
                continue
            if skip:
                # Continue skipping indented bullet lines until we hit the next top-level bullet or a section header.
                if re.match(r"^\s*[-*]\s*\*\*[A-Za-z].*\*\*:", line) or re.match(r"^\s*##\s+", line):
                    skip = False
                    out.append(line)
                else:
                    # swallow
                    continue
            else:
                out.append(line)
        return "\n".join(out)

    md = _strip_split_from_main(md)

    # NOTE: We do NOT inject appendix content directly into the LLM markdown here,
    # because we deterministically rebuild the appendix block later (and strip any
    # existing appendix content). Split rationale is inserted as part of that
    # deterministic appendix block to guarantee placement above Appendix A.

    def _fix_main_fundamental_overlay(md_text: str) -> str:
        """
        Keep the MAIN "Fundamental Overlay" section stable and correct.

        We always want the *policy* to be described deterministically when the overlay is requested,
        and we also want the *run status* to be explicit (e.g., external module failed -> overlay not applied).
        This avoids the LLM inventing or omitting critical integration details.
        """
        if not isinstance(payload, dict):
            return md_text

        run = payload.get("run_params", {}) if isinstance(payload.get("run_params", {}), dict) else {}
        fund_mode = str(run.get("fundamental_mode") or "").lower() or None
        sell_mult = run.get("sell_leverage_mult")
        overlay_used = bool(run.get("overlay_used_in_backtest"))

        requested = bool(
            run.get("fundamental_requested")
            or run.get("run_idaliia")
            or run.get("fundamental_from_idaliia")
            or (fund_mode in ("filter", "report_only"))
        )
        if not requested:
            return md_text

        # Support both keys (backward compatible).
        fund = payload.get("fundamental_view") or payload.get("fundamental_overlay")
        rating = str((fund or {}).get("rating") or "—").strip().upper()
        as_of = (fund or {}).get("as_of") or "—"
        source = (fund or {}).get("source") or "external fundamental module"

        idr = run.get("idaliia_result") if isinstance(run, dict) else None
        idaliia_requested = bool(run.get("run_idaliia") or run.get("fundamental_from_idaliia"))
        idaliia_ok = bool(idr.get("ok")) if isinstance(idr, dict) else None
        idaliia_err = (idr.get("error") if isinstance(idr, dict) else None) or None
        idaliia_log = (idr.get("log_copy_rel") if isinstance(idr, dict) else None) or None

        # Policy (deterministic): explain the mechanism regardless of run success.
        policy = (
            "Design: an external fundamental view (Buy/Hold/Sell) is integrated strictly as a risk filter applied to position sizing. "
            "It does not alter the technical entry/exit logic; it only constrains maximum exposure when the external rating is SELL, "
            f"by applying a fixed SELL exposure ceiling multiplier of {sell_mult}."
        )

        # Run status: be explicit about whether it actually applied.
        if overlay_used and fund_mode == "filter":
            status = "Run status: the exposure cap is enabled and included in the backtest."
        elif fund_mode == "report_only":
            status = "Run status: configured as context only and not applied in the backtest."
        else:
            # Most common failure case: external module did not produce a usable view, so overlay is inactive.
            if idaliia_requested and (idaliia_ok is False):
                tail = f" (log: `{idaliia_log}`)" if idaliia_log else ""
                err = f" Error: {idaliia_err}." if idaliia_err else ""
                status = (
                    "Run status: external fundamental module failed in this run, so the overlay could not be applied; "
                    f"the effective behavior is identical to the technical strategy without the fundamental cap.{err}{tail}"
                )
            elif rating in ("—", ""):
                status = "Run status: no external fundamental view was available in this run, so the overlay could not be applied."
            else:
                # Have a view but not applied (e.g., mode mismatch).
                status = "Run status: an external view is present, but the overlay is not applied in the backtest under the current configuration."

        view_line = f"External view (if available): Rating: {rating}; As-of date: {as_of}; Source: {source}."
        replacement = (policy + " " + status + " " + view_line + " See Appendix C for details.").strip()

        # Replace existing 2.3 block (if present), otherwise insert it before 2.4.
        # Match and replace the whole 2.3 block regardless of how the LLM formatted the heading line.
        sec_pat = r"(?mis)^\s*###\s*2\.3\s*Fundamental Overlay\b.*?(?=^\s*###\s*2\.4\b|\Z)"
        new_block = "### 2.3 Fundamental Overlay\n" + replacement + "\n\n"
        if re.search(sec_pat, md_text):
            md_text = re.sub(sec_pat, new_block, md_text)
            return md_text

        # Insert before 2.4 if we can locate it; else append to end of main.
        m24 = re.search(r"(?mi)^\\s*###\\s*2\\.4\\b.*$", md_text)
        if m24:
            return (md_text[: m24.start()].rstrip() + "\n\n" + new_block + md_text[m24.start():].lstrip()).strip()

        return (md_text.rstrip() + "\n\n" + new_block).strip()

    md = _fix_main_fundamental_overlay(md)

    # Strip any existing appendix block so the deterministic appendices always match the latest run payload.
    # Cut any pre-existing appendix blocks. LLMs sometimes include Appendix headings directly
    # (e.g., "## Appendix A...") without an explicit "### APPENDIX" marker.
    m = re.search(r"(?mi)^\s*###\s*appendix\b.*$", md)
    m2 = re.search(r"(?mi)^\s*##\s*appendix\b.*$", md)
    cut = None
    if m and m2:
        cut = min(m.start(), m2.start())
    elif m:
        cut = m.start()
    elif m2:
        cut = m2.start()

    main_md = md[:cut].rstrip() if cut is not None else md

    appendix_block = (
        "---\n\n"
        "### APPENDIX\n\n"
        "Supplementary only; not part of the main recommendation.\n"
        "For fair comparison, all appendix strategies use the same close-to-close returns based on the adjusted close price series and the same 1-bar execution-delay convention.\n\n"
        + _appendix_split_rationale(payload)
        + "\n"
        + _appendix_a(payload)
        + "\n"
        + _appendix_b_cd(payload)
    ).strip()

    out = (main_md + "\n\n" + appendix_block + "\n").strip() + "\n"
    out = re.sub(r"\n{4,}", "\n\n\n", out)
    # Remove a distracting main-section disclaimer about excluded variants.
    # The main report should focus on what is used, while variants live in the appendix.
    out = re.sub(
        r"(?m)^\s*Main strategy only\s*\(no MA-only variant,\s*no candlestick patterns\)\.\s*$\n?",
        "",
        out,
    )
    # Add a short, reader-friendly bridge sentence under "Main Strategy" if the LLM omitted one.
    out = re.sub(
        r"(?m)^## 2\. Main Strategy\s*\n\n(?=## 2\.1\b)",
        "## 2. Main Strategy\n\nThis section describes the core technical strategy used to derive the stance and position guidance in this report.\n\n",
        out,
    )
    # Remove stray markdown heading markers that sometimes appear as standalone '#'.
    # Some models emit non-breaking spaces around the marker, so match those too.
    out = re.sub(r"(?m)^[\s\u00A0]*#[\s\u00A0]*$\n?", "", out)

    # Fix a common causal error: attributing "Reduced" sizing to a non-binding fundamental cap.
    # If the overlay is non-binding, reduced allocation is driven by regime scaling / vol targeting, not by fundamentals.
    out = re.sub(
        r"(?m)^- \*\*Sizing context\*\*: .*fundamental overlay is not in effect\.\s*$",
        "- **Sizing context**: Classified as a Reduced allocation based on the target exposure. This reduction primarily reflects the strategy’s risk controls (regime scaling and volatility targeting); the fundamental overlay is non-binding here and therefore does not drive sizing.",
        out,
    )

    # Clean up common chart-language issues in Section 2.5 (Visual Evidence):
    # - Avoid the incorrect phrase "decline in drawdown"
    # - Avoid implying "volatility exposure" purely from the chart
    # - Reference figure filenames in a readable parenthetical style
    def _fix_visual_evidence(md: str) -> str:
        m = re.search(r"(?ms)^##\s*2\.5\s+Visual Evidence\b.*?(?=^##\s*3\.)", md)
        if not m:
            return md

        block = md[m.start() : m.end()]

        # Replace problematic phrases.
        block = re.sub(r"\bdecline in drawdown\b", "deeper drawdown", block, flags=re.I)
        block = re.sub(r",\s*indicating higher volatility exposure\.", ".", block, flags=re.I)
        block = re.sub(r"\bsharp deeper drawdown\b", "much deeper drawdown", block, flags=re.I)
        # Avoid name-dropping years unless the LLM explicitly ties them to provided tables/labels.
        block = re.sub(r",\s*especially evident in years like\s+\d{4}\b", "", block, flags=re.I)

        # Make figure references read naturally (avoid bare filenames in mid-sentence).
        block = re.sub(
            r"\bThe equity curve depicted in\s+FULL_equity\.png\b",
            "The equity curve (see FULL_equity.png)",
            block,
        )
        block = re.sub(
            r"\bThe equity curve shown in\s+FULL_equity\.png\b",
            "The equity curve (see FULL_equity.png)",
            block,
        )
        block = re.sub(
            r"\bThe equity curve shown in the equity curve\s*\(see `?FULL_equity\.png`?\)\b",
            "The equity curve (see FULL_equity.png)",
            block,
        )
        block = re.sub(
            r"\bThe equity curve shown in the equity curve\s*\(see `?FULL_equity\.png`?\)\s+shows\b",
            "The equity curve (see FULL_equity.png) shows",
            block,
        )
        block = re.sub(
            r"\bvisible in\s+FULL_drawdown\.png\b",
            "as shown in the drawdown chart (see FULL_drawdown.png)",
            block,
        )
        block = re.sub(
            r"\bshown in the drawdown chart\s*\(see `?FULL_drawdown\.png`?\)\b",
            "as shown in the drawdown chart (see FULL_drawdown.png)",
            block,
        )
        block = re.sub(
            r"\bThe\s+FULL_drawdown\.png\b",
            "The drawdown chart (see FULL_drawdown.png)",
            block,
        )
        block = re.sub(
            r"\bthe\s+FULL_annual_return\.png\b",
            "the annual return chart (see FULL_annual_return.png)",
            block,
            flags=re.I,
        )
        block = re.sub(
            r"\bFULL_annual_return\.png\b",
            "FULL_annual_return.png",
            block,
        )
        # Remove any inline-code backticks around figure filenames in this section
        # so the prose reads less like a templated string.
        block = re.sub(r"`(FULL_[A-Za-z0-9_.-]+\.png)`", r"\1", block)
        block = re.sub(r"`{2,}(FULL_[A-Za-z0-9_.-]+\.png)`{2,}", r"\1", block)
        block = re.sub(
            r"\bLastly,\s*FULL_equity\.png\b",
            "Lastly, the equity curve (see FULL_equity.png)",
            block,
        )

        # Prevent Markdown from interpreting underscores in filenames (e.g., FULL_equity.png)
        # as emphasis delimiters, which can italicize large spans of text.
        block = re.sub(r"(?<!\\)_", r"\\_", block)

        return md[: m.start()] + block + md[m.end() :]

    out = _fix_visual_evidence(out)

    # Remove meaningless empty parentheses left by imperfect template/LLM phrasing.
    out = re.sub(r"\(\s*\)", "", out)
    # De-codeify headings: remove parenthetical qualifiers from common section titles.
    out = re.sub(r"(?m)^##\s*2\.\s*Main Strategy\s*\([^)]*\)\s*$", "## 2. Main Strategy", out)
    out = re.sub(r"(?m)^###\s*2\.1\s*Signal Logic[^\n]*$", "### 2.1 Signal Logic", out)
    out = re.sub(r"(?m)^###\s*2\.2\s*Positioning\s*&\s*Risk Management[^\n]*$", "### 2.2 Positioning and Risk Management", out)
    out = re.sub(r"(?m)^###\s*2\.3\s*Fundamental Overlay[^\n]*$", "### 2.3 Fundamental Overlay", out)
    out = re.sub(r"\(must be explicit\)", "", out, flags=re.I)
    # Normalize other common heading variants that sometimes reappear from LLM outputs.
    out = re.sub(r"(?m)^#\s*(.*Investment Research Note)\s*\([^)]*\)\s*$", r"# \1", out)
    out = re.sub(r"(?m)^###\s*2\.4\s*Backtest Performance Analysis[^\n]*$", "### 2.4 Backtest Performance Analysis", out)
    out = re.sub(r"(?m)^###\s*2\.5\s*Visual Evidence[^\n]*$", "### 2.5 Visual Evidence", out)
    # Replace common code-like "name=value" fragments with prose for readability.
    out = re.sub(r"(?i)\brating\s*=\s*", "Rating: ", out)
    out = re.sub(r"(?i)\bas[-_ ]of\s*=\s*", "As-of date: ", out)
    out = re.sub(r"(?i)\bsource\s*=\s*", "Source: ", out)
    out = re.sub(r"(?i)\blong_score\s*=\s*", "long score ", out)
    out = re.sub(r"(?i)\bscore\s*=\s*", "Score ", out)
    out = re.sub(r"(?i)\bsignal_bin\s*=\s*", "signal_bin ", out)
    # Reduce inline code styling for simple state variables in explanatory text.
    out = out.replace("`signal_bin`", "signal_bin").replace("`1`", "1").replace("`0`", "0")
    out = re.sub(r"(?i)\bentry\s*=\s*", "entry threshold ", out)
    out = re.sub(r"(?i)\bhold\s*=\s*", "hold threshold ", out)
    out = re.sub(r"(?i)\(\s*signal_bin\s*\)\s*:\s*", "called signal_bin. ", out)

    # Headings must start on their own line. Occasionally an LLM will accidentally concatenate
    # a heading marker to the end of the prior sentence (e.g., "... approach.## 3. Key Risks ...").
    # This breaks HTML rendering and makes it look like the risks section is part of 2.5.
    out = re.sub(r"(?m)(\S)\s*(##\s*\d+\.)", r"\1\n\n\2", out)

    # Replace code-like parameter names / formulas with analyst prose (keep meaning).
    out = out.replace("`sell_leverage_mult`", "the SELL exposure ceiling multiplier")
    out = re.sub(r"\bsell_leverage_mult\b", "the SELL exposure ceiling multiplier", out)
    out = out.replace("`trading_cost * turnover`", "a commission-like cost proportional to turnover")
    out = re.sub(r"\btrading_cost\s*\*\s*turnover\b", "a commission-like cost proportional to turnover", out)

    # Clarify scoring scale in analyst prose (avoid overly blunt "max of 5" without intuition).
    # We keep it factual: trend contributes two points; each confirmation contributes one.
    out = re.sub(
        r"(?i)The overall score for a long position is calculated with a maximum of 5,\s*combining the trend and confirmed states\.",
        "We summarize signal strength using a five-point scoring scale. The trend component carries two points (as the primary gate for participating in an uptrend), while each of the three confirmations contributes one point; the score therefore ranges from 0 to 5.",
        out,
    )
    out = out.replace("`trading_cost`", "the per-trade cost rate")
    out = re.sub(r"\btrading_cost\b", "the per-trade cost rate", out)

    # If the report mentions annual returns, ensure it also uses the YTD label if the payload provides it.
    try:
        ann = (
            payload.get("outputs", {})
            .get("main", {})
            .get("annual_returns", [])
        )
        if isinstance(ann, list) and ann:
            last = ann[-1]
            label = str(last.get("label") or "")
            if "ytd" in label.lower():
                low = out.lower()
                if ("annual returns" in low or "annual return" in low) and ("ytd" not in low):
                    out += (
                        "\n\n"
                        f"Note: the latest year is reported as **{label}** (not a full calendar-year return).\n"
                    )
    except Exception:
        pass

    return out
