from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import markdown2
import re
from jinja2 import Environment, FileSystemLoader, select_autoescape


def _img_to_data_uri(path: Path) -> str:
    b = path.read_bytes()
    encoded = base64.b64encode(b).decode("ascii")
    # assume png
    return f"data:image/png;base64,{encoded}"


def render_html_report(
    *,
    template_dir: str | Path,
    template_name: str,
    markdown_report: str,
    payload: dict[str, Any],
    figures_main: list[Path],
    figures_appendix: list[Path],
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template(template_name)

    md_html = markdown2.markdown(markdown_report, extras=["tables", "fenced-code-blocks"])

    # LLMs sometimes emit repeated horizontal rules as separators (e.g., many lines of '---').
    # Collapse runs of <hr> to a single rule, and remove any rule immediately before the Appendix page break.
    md_html = re.sub(r"(?:\s*<hr\s*/?>\s*){2,}", r"\n<hr />\n", md_html, flags=re.I)
    md_html = re.sub(r"\s*<hr\s*/?>\s*(<div class=\"page-break\"></div>)", r"\n\\1", md_html, flags=re.I)

    # Insert a page break before APPENDIX for print/PDF layouts (and to help splitting MAIN/APPENDIX for UI tabs).
    # LLM or post-processing may render APPENDIX as h1/h2/h3; support all common variants.
    md_html = re.sub(
        r"<h1>\s*APPENDIX\s*</h1>",
        r'<div class="page-break"></div><h1>APPENDIX</h1>',
        md_html,
        flags=re.I,
    )
    md_html = re.sub(
        r"<h3>\s*APPENDIX[^<]*</h3>",
        r'<div class="page-break"></div>\g<0>',
        md_html,
        flags=re.I,
    )
    # If the report has no explicit APPENDIX heading, the first appendix section often starts at "Appendix A".
    # Only insert a page break in that case; otherwise we risk isolating the APPENDIX heading on its own page.
    if not re.search(r"<h[1-3]>\s*APPENDIX[^<]*</h[1-3]>", md_html, flags=re.I):
        md_html = re.sub(
            r"<h2>\s*Appendix\s+A\.[^<]*</h2>",
            r'<div class="page-break"></div>\g<0>',
            md_html,
            flags=re.I,
        )

    def _split_main_appendix(html: str) -> tuple[str, str]:
        """Split rendered HTML into main and appendix blocks using the APPENDIX h1 marker."""
        # Split at the first appendix marker (APPENDIX heading or Appendix A heading).
        m = re.search(
            r'(<div class="page-break"></div>\s*)?<h[1-3]>\s*APPENDIX[^<]*</h[1-3]>',
            html,
            flags=re.I,
        )
        if not m:
            m = re.search(
                r'(<div class="page-break"></div>\s*)?<h2>\s*Appendix\s+A\.[^<]*</h2>',
                html,
                flags=re.I,
            )
        if not m:
            return html, ""
        main_html = html[: m.start()].strip()
        appendix_html = html[m.end() :].strip()
        return main_html, appendix_html

    def _tag_tables(html: str) -> str:
        """
        Add stable CSS classes to specific appendix tables so the template can attach interactions.
        Regex-based (no extra deps).
        """
        html = re.sub(
            r"(<h2>\s*Appendix B:\s*Appendix Strategy Comparison\s*</h2>\s*)(<table)",
            r"\1<table class=\"strategy-compare\"",
            html,
            flags=re.I,
        )
        html = re.sub(
            r"(<h2>\s*Appendix A:\s*Sensitivity Analysis.*?</h2>\s*)(<table)",
            r"\1<table class=\"sensitivity-table\"",
            html,
            flags=re.I | re.S,
        )
        return html

    md_html = _tag_tables(md_html)
    main_report_html, appendix_report_html = _split_main_appendix(md_html)

    def _extract_stance(md_text: str) -> str | None:
        for line in md_text.splitlines():
            m = re.search(r"-\s*\*\*Stance\*\*:\s*(.+)", line, flags=re.I)
            if m:
                return m.group(1).strip()
        return None

    def _derive_stance_from_snapshot(p: dict[str, Any]) -> str | None:
        """
        Derive a short "Stance" label (Bullish/Neutral/Cautious) from deterministic run metadata
        when the Markdown doesn't explicitly provide one.
        """
        rp = p.get("run_params", {}) if isinstance(p, dict) else {}
        if not isinstance(rp, dict):
            return None
        snap = rp.get("signal_snapshot")
        if not isinstance(snap, dict):
            return None

        # Long/flat only: treat any positive base position as "long".
        try:
            base_last = float(snap.get("position_base_last", 0.0) or 0.0)
        except Exception:
            base_last = 0.0

        fund = p.get("fundamental_overlay", {}) if isinstance(p, dict) else {}
        rating = None
        if isinstance(fund, dict):
            rating = str(fund.get("rating") or "").strip().upper() or None

        # If fundamentals are SELL and the overlay is enabled, we call this "Cautious".
        if rating == "SELL":
            return "Cautious (Fundamental SELL cap)"

        if base_last > 0.0:
            return "Bullish (Long)"
        return "Neutral (Flat)"

    def _pick_metrics(rows: list[dict[str, Any]] | None, kind: str) -> dict[str, Any] | None:
        if not rows:
            return None
        for row in rows:
            name = str(row.get("name", "")).lower()
            if kind == "benchmark" and ("buy & hold" in name or "benchmark" in name):
                return row
            if kind == "main" and ("strategy" in name and "appendix" not in name):
                return row
        return rows[0] if rows else None

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

    def _fmt_money(x: Any) -> str:
        try:
            return f"{float(x):.2f}"
        except Exception:
            return "—"

    def _fmt_int(x: Any) -> str:
        try:
            return f"{int(float(x))}"
        except Exception:
            return "—"

    def _fmt_turnover(x: Any) -> str:
        try:
            v = float(x)
            return f"{v:.2f}"
        except Exception:
            return "—"

    def _infer_exchange_currency(ticker: str | None) -> tuple[str | None, str | None, bool]:
        """
        Best-effort inference for display only. Used when upstream metadata is missing
        (e.g., cached runs or Yahoo rate limiting). Returns (exchange, currency, inferred_flag).
        """
        if not ticker:
            return None, None, False
        t = str(ticker).strip().upper()
        # Demo-focused: NVDA is NASDAQ / USD.
        if t == "NVDA":
            return "NASDAQ", "USD", True
        # Suffix heuristics (limited but safe).
        if t.endswith(".L"):
            return "LSE", "GBP", True
        if t.endswith(".NS"):
            return "NSE", "INR", True
        if t.endswith(".HK"):
            return "HKEX", "HKD", True
        # Generic fallback for US tickers without suffix.
        if t.isalpha() and len(t) <= 6:
            return "US", "USD", True
        return None, None, False

    main_metrics = payload.get("outputs", {}).get("main", {}).get("metrics")
    bench_row = _pick_metrics(main_metrics, "benchmark")
    main_row = _pick_metrics(main_metrics, "main")

    run_params = payload.get("run_params", {}) if isinstance(payload, dict) else {}
    ymeta = run_params.get("yfinance_meta", {}) if isinstance(run_params, dict) else {}
    data_source_used = None
    return_definition = None
    yfinance_error = None
    yahoo_chart_error = None
    cache_hit = False
    ex = None
    cc = None
    if isinstance(ymeta, dict):
        ex = ymeta.get("exchange")
        cc = ymeta.get("currency")
        data_source_used = ymeta.get("source")
        return_definition = ymeta.get("return_definition")
        yfinance_error = ymeta.get("yfinance_error")
        yahoo_chart_error = ymeta.get("yahoo_chart_error")
        cache_hit = bool(ymeta.get("cache_hit"))
    if isinstance(run_params, dict):
        ex = ex or run_params.get("exchange")
        cc = cc or run_params.get("currency")
    inferred_ex, inferred_cc, inferred = _infer_exchange_currency(payload.get("ticker")) if (not ex or not cc) else (None, None, False)
    ex = ex or inferred_ex
    cc = cc or inferred_cc

    # Fundamental overlay (external) for sidebar display (NOT alpha; risk filter only).
    fund = payload.get("fundamental_overlay", None) if isinstance(payload, dict) else None
    fund_rating = None
    fund_asof = None
    fund_source = None
    fund_notes = None
    if isinstance(fund, dict):
        fund_rating = fund.get("rating")
        fund_asof = fund.get("as_of")
        fund_source = fund.get("source")
        fund_notes = fund.get("notes")

    fund_mode = run_params.get("fundamental_mode") if isinstance(run_params, dict) else None
    overlay_used = bool(run_params.get("overlay_used_in_backtest")) if isinstance(run_params, dict) else False
    sell_mult = run_params.get("sell_leverage_mult") if isinstance(run_params, dict) else None
    fund_report_copy_rel = run_params.get("fundamental_report_copy_rel") if isinstance(run_params, dict) else None
    fund_report_exists = run_params.get("fundamental_report_exists") if isinstance(run_params, dict) else None
    fund_report_mtime_utc = run_params.get("fundamental_report_mtime_utc") if isinstance(run_params, dict) else None
    # "Binding" means the cap actually reduces leverage (SELL). For BUY/HOLD it is typically non-binding.
    fund_binding = bool(overlay_used and str(fund_mode).lower() == "filter" and str(fund_rating).upper() == "SELL")

    idr = run_params.get("idaliia_result") if isinstance(run_params, dict) else None
    idaliia_summary = None
    if isinstance(idr, dict) and idr:
        idaliia_summary = {
            "ok": bool(idr.get("ok")),
            "recommendation": idr.get("recommendation"),
            "target_price": idr.get("target_price"),
            "upside": idr.get("upside"),
            "memo_copy_rel": idr.get("memo_copy_rel"),
            "log_copy_rel": idr.get("log_copy_rel"),
            "generated_at_utc": idr.get("generated_at_utc"),
            "error": idr.get("error"),
        }

    # Fundamental snapshot (best-effort) for sidebar display: valuation + analyst targets.
    fsnap = run_params.get("fundamental_snapshot") if isinstance(run_params, dict) else None
    fsnap_ok = fsnap.get("ok") if isinstance(fsnap, dict) else None
    fsnap_err = fsnap.get("error") if isinstance(fsnap, dict) else None
    fsnap_data = fsnap.get("data") if isinstance(fsnap, dict) else None
    fs = None
    if isinstance(fsnap_data, dict) and fsnap_data:
        fs = {
            "source": fsnap.get("source"),
            "fetched_at_utc": fsnap.get("fetched_at_utc"),
            "current_price": _fmt_money(fsnap_data.get("current_price")),
            "target_price_low": _fmt_money(fsnap_data.get("target_price_low")),
            "target_price_mean": _fmt_money(fsnap_data.get("target_price_mean")),
            "target_price_high": _fmt_money(fsnap_data.get("target_price_high")),
            "trailing_pe": _fmt_num(fsnap_data.get("trailing_pe")),
            "forward_pe": _fmt_num(fsnap_data.get("forward_pe")),
            "price_to_sales": _fmt_num(fsnap_data.get("price_to_sales")),
            "price_to_book": _fmt_num(fsnap_data.get("price_to_book")),
            "enterprise_to_ebitda": _fmt_num(fsnap_data.get("enterprise_to_ebitda")),
            "analyst_count": _fmt_int(fsnap_data.get("analyst_count")),
            "recommendation": (str(fsnap_data.get("recommendation") or "").strip() or "—"),
            "recommendation_score": _fmt_num(fsnap_data.get("recommendation_score")),
        }

    # For display: always show a concrete date (never "latest"), preferring the actual last bar date.
    # This keeps the report gradeable/reproducible even when the run uses as_of="latest".
    as_of_raw = run_params.get("as_of") if isinstance(run_params, dict) else None
    as_of_display = None
    if isinstance(ymeta, dict) and ymeta.get("end_date"):
        as_of_display = str(ymeta.get("end_date")).split(" ")[0]
    if not as_of_display:
        snap = run_params.get("signal_snapshot") if isinstance(run_params, dict) else None
        if isinstance(snap, dict) and snap.get("decision_date"):
            as_of_display = str(snap.get("decision_date")).split(" ")[0]
    if not as_of_display:
        cache_meta = ymeta.get("cache_meta") if isinstance(ymeta, dict) else None
        if isinstance(cache_meta, dict) and cache_meta.get("end_date"):
            # end_date is a reproducibility pin; df end is typically the last trading day <= end_date
            as_of_display = str(cache_meta.get("end_date")).split(" ")[0]
    if not as_of_display:
        as_of_display = as_of_raw

    summary = {
        "ticker": payload.get("ticker"),
        "exchange": ex,
        "currency": cc,
        "exchange_currency_inferred": bool(inferred),
        "as_of": as_of_raw,
        "as_of_display": as_of_display,
        "data_source_used": (f"{data_source_used} (cached)" if cache_hit and data_source_used else data_source_used),
        "return_definition": return_definition,
        "yfinance_error": yfinance_error,
        "yahoo_chart_error": yahoo_chart_error,
        "stance": (_extract_stance(markdown_report) or _derive_stance_from_snapshot(payload) or "—"),
        "fundamental": {
            "mode": fund_mode,
            "rating": fund_rating,
            "as_of": fund_asof,
            "source": fund_source,
            "notes": fund_notes,
            "overlay_used_in_backtest": overlay_used,
            "sell_leverage_mult": sell_mult,
            "binding": fund_binding,
            "report_copy_rel": fund_report_copy_rel,
            "report_exists": fund_report_exists,
            "report_mtime_utc": fund_report_mtime_utc,
        },
        "idaliia": idaliia_summary,
        "fundamental_snapshot": fs,
        "fundamental_snapshot_status": {
            "ok": (bool(fsnap_ok) if fsnap_ok is not None else None),
            "error": (str(fsnap_err) if fsnap_err else None),
            "source": (fsnap.get("source") if isinstance(fsnap, dict) else None),
            "fetched_at_utc": (fsnap.get("fetched_at_utc") if isinstance(fsnap, dict) else None),
        },
        "benchmark": {
            "equity_end": _fmt_num(bench_row.get("equity_end")) if bench_row else "—",
            "total_return": _fmt_pct(bench_row.get("total_return")) if bench_row else "—",
            "cagr": _fmt_pct(bench_row.get("CAGR")) if bench_row else "—",
            "sharpe": _fmt_num(bench_row.get("Sharpe")) if bench_row else "—",
            "max_drawdown": _fmt_pct(bench_row.get("max_drawdown")) if bench_row else "—",
            "hit_rate": _fmt_pct(bench_row.get("hit_rate")) if bench_row else "—",
            "turnover_sum": _fmt_turnover(bench_row.get("turnover_sum")) if bench_row else "—",
            "exposure": _fmt_pct(bench_row.get("exposure")) if bench_row else "—",
        },
        "main": {
            "equity_end": _fmt_num(main_row.get("equity_end")) if main_row else "—",
            "total_return": _fmt_pct(main_row.get("total_return")) if main_row else "—",
            "cagr": _fmt_pct(main_row.get("CAGR")) if main_row else "—",
            "sharpe": _fmt_num(main_row.get("Sharpe")) if main_row else "—",
            "max_drawdown": _fmt_pct(main_row.get("max_drawdown")) if main_row else "—",
            "hit_rate": _fmt_pct(main_row.get("hit_rate")) if main_row else "—",
            "turnover_sum": _fmt_turnover(main_row.get("turnover_sum")) if main_row else "—",
            "exposure": _fmt_pct(main_row.get("exposure")) if main_row else "—",
        },
        "disclaimer": {
            "education_only": True,
            "llm_provider": (run_params.get("llm_provider") if isinstance(run_params, dict) else None),
            # Packaged project is OpenAI-only; keep this robust to older payloads.
            "llm_model": (run_params.get("openai_model") if isinstance(run_params, dict) else None),
            "llm_commercial": bool(isinstance(run_params, dict) and str(run_params.get("llm_provider") or "").lower() == "openai"),
            "deterministic_metrics": True,
            "past_performance_note": True,
        },
    }

    main_imgs = [{"name": p.name, "data_uri": _img_to_data_uri(p)} for p in figures_main if p.exists()]
    app_imgs = [{"name": p.name, "data_uri": _img_to_data_uri(p)} for p in figures_appendix if p.exists()]

    def _select_figs(imgs: list[dict[str, str]], names: list[str]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        by_name = {i["name"]: i for i in imgs}
        picked = [by_name[n] for n in names if n in by_name]
        picked_set = {p["name"] for p in picked}
        rest = [i for i in imgs if i["name"] not in picked_set]
        return picked, rest

    key_main_names = ["FULL_price.png", "FULL_equity.png", "FULL_drawdown.png", "FULL_annual_return.png"]
    key_main, main_rest = _select_figs(main_imgs, key_main_names)

    # Fundamental charts should live in the right sidebar (not duplicated in the supplementary gallery).
    key_fund_names = ["FUND_targets.png", "FUND_multiples.png"]
    key_fund, app_rest = _select_figs(app_imgs, key_fund_names)

    return tpl.render(
        report_html=md_html,
        main_report_html=main_report_html,
        appendix_report_html=appendix_report_html,
        payload=payload,
        summary=summary,
        key_main_figures=key_main,
        key_fund_figures=key_fund,
        main_figures=main_rest,
        appendix_figures=app_rest,
    )


def save_html(html: str, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return p
