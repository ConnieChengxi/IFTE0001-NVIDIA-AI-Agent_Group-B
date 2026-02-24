"""Report download buttons component."""

import streamlit as st

from utils.paths import OUTPUT_DIR


def render_downloads(ticker: str):
    """Render PDF/HTML download buttons for all generated reports."""
    st.markdown(
        '<div class="section-header">Download Reports</div>',
        unsafe_allow_html=True,
    )

    report_files = {
        "Hybrid Investment Memo": (
            OUTPUT_DIR / f"{ticker}_investment_memo.pdf",
            OUTPUT_DIR / f"{ticker}_investment_memo.html",
        ),
        "Fundamental Analysis": (
            OUTPUT_DIR / f"{ticker}_fundamental_analysis.pdf",
            OUTPUT_DIR / f"{ticker}_fundamental_analysis.html",
        ),
        "Technical Analysis": (
            OUTPUT_DIR / f"{ticker}_technical_analysis.pdf",
            OUTPUT_DIR / f"{ticker}_technical_analysis.html",
        ),
    }

    cols = st.columns(3)
    for col, (label, (pdf_path, html_path)) in zip(cols, report_files.items()):
        with col:
            if pdf_path.exists():
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label=f"{label} (PDF)",
                        data=f.read(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        use_container_width=True,
                    )
            elif html_path.exists():
                with open(html_path, "rb") as f:
                    st.download_button(
                        label=f"{label} (HTML)",
                        data=f.read(),
                        file_name=html_path.name,
                        mime="text/html",
                        use_container_width=True,
                    )
            else:
                st.button(
                    f"{label} (N/A)",
                    disabled=True,
                    use_container_width=True,
                )
