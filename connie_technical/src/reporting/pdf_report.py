"""
Professional PDF/HTML Report Generator for Technical Analysis Reports.

Converts Markdown reports to styled HTML/PDF, inserting charts
in appropriate sections while preserving the original MD structure.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Dict, Any, Optional
import markdown
import re


def _get_css_styles() -> str:
    """Return professional CSS styles matching institutional investment memo design."""
    return """
@page {
    margin: 2cm 2.5cm;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #1f2937;
    margin: 0 auto;
    max-width: 800px;
    padding: 0 20px;
    text-align: justify;
}

h1 {
    font-size: 20pt;
    font-weight: 700;
    color: #111827;
    margin-bottom: 5px;
    border-bottom: 3px solid #2563eb;
    padding-bottom: 10px;
    text-align: left;
}

h2 {
    font-size: 14pt;
    font-weight: 700;
    color: #1e40af;
    border-bottom: 2px solid #93c5fd;
    padding-bottom: 5px;
    margin-top: 30px;
    margin-bottom: 15px;
}

h3 {
    font-size: 11pt;
    font-weight: 600;
    color: #374151;
    margin: 20px 0 10px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

p {
    margin: 8px 0;
    text-align: justify;
    line-height: 1.6;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9pt;
}

th {
    background: #f3f4f6;
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
    color: #374151;
    border-bottom: 2px solid #d1d5db;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

td {
    padding: 6px 10px;
    border-bottom: 1px solid #e5e7eb;
}

ul {
    margin: 8px 0;
    padding-left: 25px;
}

li {
    margin: 4px 0;
    text-align: justify;
}

.positive { color: #059669; }
.negative { color: #dc2626; }

/* Report Header */
.report-header {
    margin-bottom: 20px;
}

.report-header h1 {
    margin-bottom: 10px;
}

.report-meta {
    font-size: 10pt;
    color: #4b5563;
    margin-bottom: 5px;
}

.report-meta .date,
.report-meta .analyst {
    margin-right: 30px;
}

.report-meta .date::before {
    content: "Date: ";
    font-weight: 600;
}

.report-meta .analyst::before {
    content: "Analyst: ";
    font-weight: 600;
}

/* Charts */
.chart-container {
    margin: 15px 0;
    text-align: center;
}

.chart-container img {
    max-width: 100%;
    height: auto;
}

/* Keep chart section (header + chart) together */
.chart-section {
    page-break-inside: avoid;
    break-inside: avoid;
}

.chart-caption {
    font-size: 9pt;
    color: #6b7280;
    margin-top: 8px;
    font-style: italic;
}

/* Horizontal rules */
hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 20px 0;
}

/* Disclaimer */
.disclaimer {
    margin-top: 30px;
    padding: 12px;
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    font-size: 8pt;
    color: #6b7280;
    text-align: justify;
}

@media print {
    body {
        margin: 0;
        padding: 15px;
        font-size: 9pt;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }

    table {
        width: 100% !important;
        border-collapse: collapse !important;
    }

    th {
        background-color: #f3f4f6 !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }

    tr {
        page-break-inside: avoid;
    }

    /* Keep headers with following content */
    h2 {
        page-break-after: avoid;
        break-after: avoid;
    }

    h3 {
        page-break-after: avoid;
        break-after: avoid;
    }

    /* Chart containers - keep together but allow page to break before if needed */
    .chart-container {
        page-break-inside: avoid;
        break-inside: avoid;
    }

    /* If there's a section with header + chart, keep them together */
    h2 + .chart-container,
    h2 + p + .chart-container {
        page-break-before: auto;
    }

    .no-print {
        display: none !important;
    }
}
"""


def _embed_image_as_base64(image_path: Path) -> str:
    """Convert image file to base64 data URI."""
    if not image_path.exists():
        return ""

    suffix = image_path.suffix.lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
    }
    mime_type = mime_types.get(suffix, 'image/png')

    with open(image_path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')

    return f"data:{mime_type};base64,{data}"


def _make_chart_html(image_path: Path, caption: str) -> str:
    """Create HTML for a single chart."""
    if not image_path.exists():
        return ""

    data_uri = _embed_image_as_base64(image_path)
    return f'''
<div class="chart-container">
    <img src="{data_uri}" alt="{caption}">
    <div class="chart-caption">{caption}</div>
</div>
'''


def _insert_charts_into_markdown(
    markdown_content: str,
    chart_paths: Dict[str, str],
    base_path: Path,
) -> str:
    """
    Insert charts into appropriate sections of the markdown.
    Charts are placed after relevant sections.
    """
    if not chart_paths:
        return markdown_content

    # Remove old chart references
    markdown_content = re.sub(
        r'\(Refer to attached files:[\s\S]*?\)',
        '',
        markdown_content
    )
    markdown_content = re.sub(
        r'## Charts & Visuals[\s\S]*$',
        '',
        markdown_content
    )

    # Define where to insert each chart
    # Format: (section_pattern, chart_keys, captions, descriptions)
    # Only 3 charts as per technical agent spec:
    # 1. Trade Entry & Exit (golden_cross_trades) - MA200 regime gate
    # 2. Equity + Drawdown comparison (equity_drawdown) - performance comparison
    # 3. Price + MA + MACD 6m (price_ma_macd_6m) - short-horizon diagnostic

    chart_insertions = [
        # After Backtest Setup - show Trade Entry & Exit FIRST (explains HOW strategy works)
        (r'(## Backtest Setup.*?)(\n## |\n---|\Z)',
         ['golden_cross_trades'],
         ['Trade Entry & Exit Points'],
         ['''The figure shows the MA200-based regime gate over the full sample period. The blue line represents daily closing price, the orange line shows MA50, and the green line shows MA200 which defines the regime boundary. Golden Cross (blue triangles) and Death Cross (orange triangles) mark regime transitions. Green dots indicate trade entries, red crosses indicate exits. The sparse distribution of trades demonstrates that MA200 is used as a low-frequency structural filter, not a short-term timing signal.''']),

        # After Performance Results - show equity + drawdown comparison
        (r'(## Performance.*?)(\n## |\n---|\Z)',
         ['equity_drawdown'],
         ['Strategy vs Buy-and-Hold Comparison'],
         ['''The upper panel shows log-scaled equity curves normalised to a common starting value. The buy-and-hold trajectory reflects full market exposure, while the strategy curve reflects conditional exposure governed by the regime gate. Flatter segments correspond to periods when the regime gate is closed and capital is preserved. The lower panel reports drawdown profiles - the strategy exhibits materially shallower drawdowns, indicating improved downside control.''']),
    ]

    # Charts that go to Appendix - only 6-month MACD
    appendix_charts = [
        ('price_ma_macd_6m', 'Price with Moving Averages & MACD (6 Months)',
         '''This short-horizon diagnostic view shows recent price dynamics using candlestick charts, moving averages, and MACD. The upper panel displays price action with MA20 (blue), MA50 (orange), and MA200 (green). The lower panel shows MACD line, signal line, and histogram for momentum analysis. A six-month horizon is selected to preserve visual interpretability.'''),
    ]

    for pattern, chart_keys, captions, descriptions in chart_insertions:
        match = re.search(pattern, markdown_content, re.DOTALL | re.IGNORECASE)
        if match:
            section_content = match.group(1)
            next_section = match.group(2)

            charts_html = ""
            for chart_key, caption, description in zip(chart_keys, captions, descriptions):
                path_str = chart_paths.get(chart_key)
                if path_str:
                    img_path = Path(path_str)
                    if not img_path.is_absolute():
                        img_path = base_path / path_str
                    if not img_path.exists():
                        img_path = base_path / img_path.name

                    if img_path.exists():
                        charts_html += f"\n\n### {caption}\n\n"
                        charts_html += f"![{caption}]({img_path})\n\n"
                        charts_html += f"{description}\n"

            if charts_html:
                new_content = section_content + charts_html + next_section
                markdown_content = markdown_content[:match.start()] + new_content + markdown_content[match.end():]

    # Add Appendix with supplementary charts
    appendix_images = []
    for chart_key, caption, description in appendix_charts:
        path_str = chart_paths.get(chart_key)
        if path_str:
            img_path = Path(path_str)
            if not img_path.is_absolute():
                img_path = base_path / path_str
            if not img_path.exists():
                img_path = base_path / img_path.name
            if img_path.exists():
                appendix_images.append((caption, img_path, description))

    if appendix_images:
        # Use HTML directly to keep header and chart together
        markdown_content += "\n\n---\n\n<div class='chart-section'>\n\n## Strategy Charts\n\n"
        for caption, img_path, description in appendix_images:
            markdown_content += f"![{caption}]({img_path})\n\n"
            markdown_content += f"*{caption}*\n\n"
            markdown_content += f"{description}\n"
        markdown_content += "\n</div>\n"

    # Add Appendix: Strategy Parameters
    markdown_content += """

---

## Appendix: Strategy Parameters

Technical strategy rules and risk management parameters.

| PARAMETER | VALUE | PURPOSE |
|-----------|-------|---------|
| Strategy Type | Long/Flat | No short positions |
| Regime Filter | Close > MA200 | Bull market identification |
| Entry Condition | Regime gate opens | Enter when Close > MA200 |
| Exit Condition | Regime break or stop hit | Close < MA200 or trailing stop |
| Trend Floor | 60% when MA20 > MA50 | Minimum exposure in strong trend |
| Weak Trend Scale | 85% | Reduced weight when MA20 <= MA50 |
| Vol Target | 35% annual | Position sizing based on volatility |
| MACD De-risk | 75% scale | Reduce when MACD < Signal line |
| RSI De-risk (>80) | 90% scale | Reduce on mild overextension |
| RSI De-risk (>90) | 75% scale | Reduce on severe overextension |
| Fixed Stop Loss | 12% | Maximum loss per trade |
| ATR Trailing Stop | 3.5x ATR(14) | Dynamic stop to lock gains |
| Transaction Costs | 10 bps | Cost per position change |
| Signal Shift | +1 day | Avoid look-ahead bias |

"""

    return markdown_content


def _convert_md_images_to_embedded(html_content: str, base_path: Path) -> str:
    """Convert image references in HTML to embedded base64."""

    def replace_img_tag(match):
        full_tag = match.group(0)

        # Extract src and alt from the tag (order-independent)
        src_match = re.search(r'src="([^"]*)"', full_tag)
        alt_match = re.search(r'alt="([^"]*)"', full_tag)

        src = src_match.group(1) if src_match else ""
        alt = alt_match.group(1) if alt_match else ""

        if not src:
            return full_tag

        # Try to find the image
        img_path = Path(src)
        if not img_path.is_absolute():
            img_path = base_path / src
        if not img_path.exists():
            img_path = base_path / img_path.name

        if img_path.exists():
            data_uri = _embed_image_as_base64(img_path)
            return f'''<div class="chart-container">
    <img src="{data_uri}" alt="{alt}">
    <div class="chart-caption">{alt}</div>
</div>'''

        return full_tag

    # Match any <img> tag (regardless of attribute order)
    html_content = re.sub(
        r'<img[^>]+/?>',
        replace_img_tag,
        html_content
    )

    # Remove wrapping <p> tags around chart containers
    html_content = re.sub(
        r'<p>\s*(<div class="chart-container">)',
        r'\1',
        html_content
    )
    html_content = re.sub(
        r'(</div>)\s*</p>',
        r'\1',
        html_content
    )

    return html_content


def _build_html_report(
    markdown_content: str,
    ticker: str,
    company_name: Optional[str] = None,
    report_date: Optional[str] = None,
    chart_paths: Optional[Dict[str, str]] = None,
    base_path: Optional[Path] = None,
    show_print_instructions: bool = True,
) -> str:
    """Build HTML document from Markdown, preserving structure and inserting charts."""

    base_path = base_path or Path('.')

    # Insert charts into markdown at appropriate places
    if chart_paths:
        markdown_content = _insert_charts_into_markdown(
            markdown_content, chart_paths, base_path
        )

    # Convert Markdown to HTML
    md = markdown.Markdown(extensions=['tables', 'fenced_code'])
    html_body = md.convert(markdown_content.strip())

    # Embed images as base64
    html_body = _convert_md_images_to_embedded(html_body, base_path)

    date_str = report_date or ""

    # Print instructions
    print_instr = ""
    if show_print_instructions:
        print_instr = """
        <div class="print-instructions no-print">
            <strong>Save as PDF:</strong> Press <code>Cmd+P</code> (Mac) or <code>Ctrl+P</code> (Windows)
            → Select "Save as PDF" → Save
        </div>
        """

    # Remove the original H1 from markdown (we'll add our own header)
    html_body = re.sub(r'<h1>[^<]*</h1>', '', html_body, count=1)

    # Use company name if provided, otherwise use ticker
    display_name = company_name if company_name else ticker

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Technical Analysis Report: {display_name}</title>
    <style>
{_get_css_styles()}
    </style>
</head>
<body>
    {print_instr}

    <div class="report-header">
        <h1>Technical Analysis Report: {display_name} ({ticker})</h1>
        <div class="report-meta">
            <span class="date">{date_str}</span>
            <span class="analyst">Connie Chengxi</span>
        </div>
    </div>

    <div class="content">
        {html_body}
    </div>

    <div class="disclaimer">
        <strong>Disclaimer:</strong> This report was generated by an AI-powered technical analysis agent for educational purposes.
        All analysis is based on historical price data and should not be considered as financial advice.
        Past performance does not guarantee future results. Please conduct your own due diligence and consult
        with a qualified financial advisor before making investment decisions.
    </div>
</body>
</html>
"""
    return html


def generate_html_report(
    markdown_content: str,
    output_path: str | Path,
    ticker: str = "TICKER",
    company_name: Optional[str] = None,
    report_date: Optional[str] = None,
    chart_paths: Optional[Dict[str, str]] = None,
    metrics: Optional[Dict[str, Any]] = None,  # Ignored, kept for compatibility
) -> Path:
    """Generate HTML report from Markdown with embedded charts."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html_content = _build_html_report(
        markdown_content=markdown_content,
        ticker=ticker,
        company_name=company_name,
        report_date=report_date,
        chart_paths=chart_paths,
        base_path=output_path.parent,
        show_print_instructions=False,
    )

    output_path.write_text(html_content, encoding='utf-8')
    return output_path


def _generate_pdf_with_playwright(html_path: Path, pdf_path: Path) -> bool:
    """Generate PDF using playwright. Returns True if successful."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{html_path.absolute()}")
            page.pdf(
                path=str(pdf_path),
                format="A4",
                margin={"top": "2cm", "bottom": "2cm", "left": "2.5cm", "right": "2.5cm"},
                print_background=True,
            )
            browser.close()
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"Playwright PDF generation failed: {e}")
        return False


def _generate_pdf_with_weasyprint(html_content: str, pdf_path: Path, base_path: Path) -> bool:
    """Generate PDF using weasyprint. Returns True if successful."""
    try:
        from weasyprint import HTML
        html_doc = HTML(string=html_content, base_url=str(base_path))
        html_doc.write_pdf(pdf_path)
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"WeasyPrint PDF generation failed: {e}")
        return False


def generate_pdf_report(
    markdown_content: str,
    output_path: str | Path,
    ticker: str = "TICKER",
    company_name: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None,  # Ignored, kept for compatibility
    report_date: Optional[str] = None,
    chart_paths: Optional[Dict[str, str]] = None,
    image_base_path: Optional[str | Path] = None,
    embed_images: bool = True,
) -> Path:
    """
    Generate PDF report with HTML always saved as well.

    Tries PDF generation in order:
    1. Playwright (easiest cross-platform installation)
    2. WeasyPrint (if system dependencies installed)
    3. Falls back to HTML only with instructions
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base_path = Path(image_base_path) if image_base_path else output_path.parent

    html_content = _build_html_report(
        markdown_content=markdown_content,
        ticker=ticker,
        company_name=company_name,
        report_date=report_date,
        chart_paths=chart_paths,
        base_path=base_path,
        show_print_instructions=False,
    )

    # Always save HTML
    html_path = output_path.with_suffix('.html')
    html_path.write_text(html_content, encoding='utf-8')
    print(f"HTML report saved: {html_path}")

    # Try PDF generation
    pdf_path = output_path.with_suffix('.pdf')

    # 1. Try playwright first (easiest to install cross-platform)
    if _generate_pdf_with_playwright(html_path, pdf_path):
        print(f"PDF report saved: {pdf_path}")
        return pdf_path

    # 2. Try weasyprint
    if _generate_pdf_with_weasyprint(html_content, pdf_path, base_path):
        print(f"PDF report saved: {pdf_path}")
        return pdf_path

    # 3. Fallback - HTML only
    print(f"\nTo generate PDF, install playwright:")
    print(f"  pip install playwright")
    print(f"  playwright install chromium")
    print(f"\nOr open HTML in browser → Cmd+P → Save as PDF\n")

    return html_path