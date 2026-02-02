from __future__ import annotations

import argparse
from pathlib import Path

import streamlit as st

import run_demo  # uses run_pipeline
from tech_agent.llm_provider import generate_report_markdown
from tech_agent.html_report import render_html_report, save_html


def _ns(**kwargs) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def main():
    st.set_page_config(page_title="NVDA Technical Agent", layout="wide")
    st.title("Technical Analyst Agent (NVDA) — Web Demo (OpenAI → HTML)")

    with st.sidebar:
        st.header("Run settings")

        ticker = st.text_input("Ticker", value="NVDA")
        years = st.number_input("Years", min_value=1, max_value=30, value=10)
        interval = st.text_input("Interval", value="1d")

        train_end = st.text_input("Train end (YYYY-MM-DD)", value="2019-12-31")
        val_end = st.text_input("Val end (YYYY-MM-DD)", value="2022-12-31")

        trading_cost = st.number_input("Trading cost (per turnover)", value=0.0005, format="%.6f")
        initial_capital = st.number_input("Initial capital", value=1.0, format="%.2f")

        st.divider()
        st.subheader("Technical extensions")
        use_patterns = st.checkbox("Enable candlestick/pattern factor", value=False)
        use_patterns_appendix = st.checkbox("Enable patterns in APPENDIX (experimental)", value=False)

        st.divider()
        st.subheader("Fundamental overlay (external)")
        fundamental_mode = st.selectbox("Fundamental mode", ["report_only", "filter"], index=1)
        fundamental_file = st.text_input("Override JSON", value="inputs/fundamental_override.json")
        sell_leverage_mult = st.slider("SELL leverage multiplier", min_value=0.0, max_value=1.0, value=0.3, step=0.05)
        fund_asof_default = st.text_input("Default as_of (optional)", value="")

        st.divider()
        st.subheader("LLM")
        openai_model = st.text_input("OpenAI model", value="gpt-4o-mini")

        st.divider()
        out_dir = st.text_input("Output folder", value="outputs")
        template_dir = st.text_input("Template folder", value="templates")
        show = st.checkbox("Show plots (usually off)", value=False)

        run_bt = st.button("1) Run backtest + generate outputs")
        gen_report = st.button("2) Generate LLM report (Markdown)")
        export_html = st.button("3) Export HTML")

    out_dir_p = Path(out_dir)
    out_main = out_dir_p / "main"
    out_app = out_dir_p / "appendix"
    out_main.mkdir(parents=True, exist_ok=True)
    out_app.mkdir(parents=True, exist_ok=True)

    # persistent state
    if "payload" not in st.session_state:
        st.session_state["payload"] = None
    if "md" not in st.session_state:
        st.session_state["md"] = None

    if run_bt:
        args = _ns(
            ticker=ticker,
            years=int(years),
            interval=interval,
            train_end=train_end,
            val_end=val_end,
            trading_cost=float(trading_cost),
            initial_capital=float(initial_capital),
            no_patterns=not bool(use_patterns),
            use_patterns_appendix=bool(use_patterns_appendix),
            fundamental_mode=fundamental_mode,
            fundamental_file=fundamental_file,
            sell_leverage_mult=float(sell_leverage_mult),
            fund_asof_default=(fund_asof_default.strip() or None),
            openai_model=openai_model,
            no_llm=True,
            export_html=False,
            show=bool(show),
            out_dir=out_dir,
            template_dir=template_dir,
        )
        with st.spinner("Running pipeline..."):
            info = run_demo.run_pipeline(args)
        st.session_state["payload"] = info["payload"]
        st.success(f"Done. Outputs written to {Path(info['out_dir']).resolve()}")

    # display figures
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Main Figures")
        for p in sorted(out_main.glob("*.png")):
            st.image(str(p), caption=p.name, use_container_width=True)
    with col2:
        st.subheader("Appendix Figures")
        for p in sorted(out_app.glob("*.png")):
            st.image(str(p), caption=p.name, use_container_width=True)

    if gen_report:
        if st.session_state["payload"] is None:
            st.error("Run backtest first.")
        else:
            st.warning("LLM generation may incur API costs. Confirm before proceeding.")
            confirm_llm = st.checkbox("I understand and want to generate the LLM report now.")
            if confirm_llm:
                with st.spinner("Generating report via LLM..."):
                    md = generate_report_markdown(
                        st.session_state["payload"],
                        openai_model=openai_model,
                    )
                st.session_state["md"] = md
                md_path = out_dir_p / f"{ticker}_investment_report.md"
                md_path.write_text(md, encoding="utf-8")
                st.success(f"Markdown saved: {md_path}")
                st.text_area("Report (Markdown)", md, height=400)

    if export_html:
        if st.session_state["md"] is None or st.session_state["payload"] is None:
            st.error("Generate the LLM report first.")
        else:
            html = render_html_report(
                template_dir=template_dir,
                template_name="report.html",
                markdown_report=st.session_state["md"],
                payload=st.session_state["payload"],
                figures_main=sorted(out_main.glob("*.png")),
                figures_appendix=sorted(out_app.glob("*.png")),
            )
            html_path = out_dir_p / f"{ticker}_investment_report.html"
            save_html(html, html_path)
            st.success(f"HTML saved: {html_path}")
            st.download_button("Download HTML", data=html.encode("utf-8"), file_name=html_path.name)

if __name__ == "__main__":
    main()
