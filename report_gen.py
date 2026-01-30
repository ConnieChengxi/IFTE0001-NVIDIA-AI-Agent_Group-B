import os
import json
import pandas as pd
import re
from fpdf import FPDF
from datetime import datetime
from openai import OpenAI
from config import SYMBOL, PROCESSED_DATA_DIR, PLOTS_DIR, OPENAI_API_KEY, PEERS

class PDF(FPDF):
    def header(self):
        if self.page_no() == 1: return
        self.set_fill_color(41, 128, 185) 
        self.rect(0, 0, 210, 20, 'F')
        self.set_y(5)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, f'EQUITY RESEARCH: {SYMBOL} | AI-DRIVEN ANALYSIS', 0, 0, 'L')
        self.set_font('Arial', 'I', 8)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, f'Report Date: {datetime.now().strftime("%Y-%m-%d")}', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(160, 160, 160)
        self.cell(0, 10, f'Confidential Financial Analysis | Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        # Check if we need a new page (if less than 60mm left)
        if self.get_y() > 220:
            self.add_page()
        else:
            self.ln(5)
            
        self.set_font('Arial', 'B', 13)
        self.set_fill_color(44, 62, 80)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, f'  {title}', 0, 1, 'L', fill=True)
        self.ln(3)

    def sub_title(self, title):
        if self.get_y() > 250:
            self.add_page()
        self.set_font('Arial', 'B', 11)
        self.set_text_color(41, 128, 185)
        self.cell(0, 8, title, 0, 1, 'L')
        self.ln(1)

    def sanitize_text(self, text):
        """Replace unicode characters that cause issues with default PDF fonts."""
        replacements = {
            '\u2013': '-', # em dash
            '\u2014': '-', # en dash
            '\u2018': "'", # left single quote
            '\u2019': "'", # right single quote
            '\u201c': '"', # left double quote
            '\u201d': '"', # right double quote
            '\u2022': '*', # bullet point
            '\u2026': '...', # ellipsis
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        # Fallback: remove any other non-latin1 characters
        return text.encode('latin-1', 'replace').decode('latin-1')

    def create_cover_page(self, symbol):
        self.add_page()
        self.set_fill_color(41, 128, 185)
        self.rect(0, 0, 210, 297, 'F')
        self.set_y(100)
        self.set_font('Arial', 'B', 36)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, "EQUITY RESEARCH REPORT", 0, 1, 'C')
        self.set_font('Arial', 'B', 72)
        self.cell(0, 40, symbol, 0, 1, 'C')
        self.set_y(180)
        self.set_font('Arial', '', 16)
        self.cell(0, 10, "Institutional Grade Financial Analysis", 0, 1, 'C')
        self.cell(0, 10, "& Strategic AI Synthesis", 0, 1, 'C')
        self.set_y(240)
        self.set_font('Arial', 'I', 12)
        self.cell(0, 10, f"Generated on {datetime.now().strftime('%B %d, %Y')}", 0, 1, 'C')
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, "STRICTLY CONFIDENTIAL", 0, 1, 'C')
        # Ensure next page has header
        self.add_page() 

class ReportGenerator:
    def __init__(self):
        self.symbol = SYMBOL
        self.ratios_path = os.path.join(PROCESSED_DATA_DIR, f'{SYMBOL}_ratios_annual.csv')
        self.valuation_path = os.path.join(PROCESSED_DATA_DIR, f'{SYMBOL}_valuation.json')
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.pdf_path = os.path.join(PROCESSED_DATA_DIR, f'{SYMBOL}_Investment_Report_{self.timestamp}.pdf')
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    def _load_data(self):
        ratios = pd.read_csv(self.ratios_path) if os.path.exists(self.ratios_path) else None
        valuation = None
        if os.path.exists(self.valuation_path):
            with open(self.valuation_path, 'r') as f:
                valuation = json.load(f)
        return ratios, valuation

    def _get_llm_content(self, prompt):
        if not self.client:
            print("No OpenAI client available, skipping LLM.")
            return "Analysis based on quantitative models."
        try:
            print(f"Requesting JSON content from GPT-4o for {SYMBOL}...")
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Senior Equity Research Director. Provide a Rigorous, Professional Analysis. "
                                                 "Return your response ONLY as a JSON object with keys: 'section1', 'section2', 'section3', 'section4', 'section5'. "
                                                 "Each section should be multiple paragraphs of deep insight (around 300 words)."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=2500,
                temperature=0.7,
                timeout=90
            )
            content = response.choices[0].message.content
            print("JSON content received from LLM.")
            return content
        except Exception as e:
            print(f"LLM Synthesis Error: {e}")
            return json.dumps({"section1": f"Analysis summary: Numerical growth remains strong. [Error: {e}]"})

    def _create_styled_table(self, pdf, header, data, col_widths, align='C'):
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(44, 62, 80)
        pdf.set_text_color(255, 255, 255)
        for i, h in enumerate(header):
            pdf.cell(col_widths[i], 10, h, 1, 0, 'C', fill=True)
        pdf.ln()
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(0, 0, 0)
        fill = False
        for row in data:
            pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
            for i, item in enumerate(row):
                pdf.cell(col_widths[i], 8, str(item), 1, 0, align, fill=True)
            pdf.ln()
            fill = not fill
        pdf.ln(5)

    def _get_section(self, text, header_num, next_header=None):
        try:
            data = json.loads(text)
            key = f"section{header_num}"
            if key in data:
                return data[key].strip()
        except:
            pass

        # Fallback to old regex if JSON fails
        pattern = rf"(?:^|\n)(?:[#*\s]*)?{header_num}\.\s*.*?(?:\n|$)"
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        
        if len(parts) > 1:
            content = parts[1]
            if next_header:
                next_pattern = rf"(?:^|\n)(?:[#*\s]*)?{next_header}\.\s*.*?(?:\n|$)"
                content = re.split(next_pattern, content, flags=re.IGNORECASE)[0]
            
            # Clean up formatting artifacts
            return content.replace("**", "").replace("###", "").replace("##", "").strip()
            
        print(f"Warning: Section {header_num} missing.")
        return "Refer to quantitative data tables."

    def generate_pdf(self, llm_content, ratios_df, val_data):
        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.create_cover_page(self.symbol)
        
        # Mapping our internal headers to LLM response headers
        # Use full names or just numbers depending on LLM output
        sections = [
            ('1. EXECUTIVE SUMMARY & THESIS', 1, 2),
            ('2. FINANCIAL PERFORMANCE ANALYSIS', 2, 3),
            ('3. STRATEGIC VALUATION ANALYSIS', 3, 4),
            ('4. COMPETITIVE LANDSCAPE & RISKS', 4, 5),
            ('5. INVESTMENT CONCLUSION', 5, None)
        ]

        for title, curr, next_h in sections:
            pdf.chapter_title(title)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', '', 10)
            
            text = self._get_section(llm_content, curr, next_h)
            sanitized_text = pdf.sanitize_text(text)
            
            # If the parser failed to find specific sections, use the whole text for section 1 
            # and generic reminders for others, or just print what we have.
            pdf.multi_cell(0, 6, sanitized_text)
            pdf.ln(5)
            
            if curr == 1:
                wv = val_data.get('WeightedValuation', {})
                self._create_styled_table(pdf, ['Metric', 'Value'], [
                    ['Market Price', f"${val_data['CurrentMarketPrice']:.2f}"],
                    ['Instrinsic Value', f"${wv['IntrinsicValue']:.2f}"],
                    ['Upside/Downside', f"{wv['Upside']:.1%}"],
                    ['Recommendation', str(wv['Recommendation']).upper()]
                ], [70, 70])
            elif curr == 2:
                latest = ratios_df.iloc[0]
                self._create_styled_table(pdf, ['Metric', 'Current', 'Previous'], [
                    ['Gross Margin', f"{latest['Gross Margin']:.1%}", f"{ratios_df.iloc[1]['Gross Margin']:.1%}"],
                    ['Net Margin', f"{latest['Net Margin']:.1%}", f"{ratios_df.iloc[1]['Net Margin']:.1%}"],
                    ['ROE', f"{latest['ROE']:.1%}", f"{ratios_df.iloc[1]['ROE']:.1%}"],
                    ['Current Ratio', f"{latest.get('Current Ratio', 0):.2f}", f"{ratios_df.iloc[1].get('Current Ratio', 0):.2f}"]
                ], [60, 40, 40])
                
                # Side-by-side Images
                p1, p2 = [os.path.join(PLOTS_DIR, x) for x in ['profitability_trends.png', 'return_ratios.png']]
                curr_y = pdf.get_y()
                # Check for space (image height approx 60mm)
                if curr_y > 220:
                    pdf.add_page()
                    curr_y = pdf.get_y()
                
                if os.path.exists(p1): pdf.image(p1, x=10, y=curr_y, w=90)
                if os.path.exists(p2): pdf.image(p2, x=110, y=curr_y, w=90)
                pdf.set_y(curr_y + 70) # Offset for next section
                
            elif curr == 3:
                # 1. Weighted Valuation Summary Table (New)
                wv = val_data.get('WeightedValuation', {})
                weights = wv.get('Weights', {})
                
                pdf.sub_title("Integrated Valuation Model Breakdown (Weighted Average)")
                valuation_rows = [
                    ['Model Type', 'Calculated Intrinsic Value', 'Weight (%)', 'Contribution'],
                    ['Discounted Cash Flow (DCF)', f"${val_data['DCF']['Intrinsic Price']:.2f}", f"{weights.get('DCF', 0):.0%}", f"${val_data['DCF']['Intrinsic Price'] * weights.get('DCF', 0):.2f}"],
                    ['Dividend Discount (DDM)', f"${val_data['DDM']['Intrinsic Price']:.2f}", f"{weights.get('DDM', 0):.0%}", f"${val_data['DDM']['Intrinsic Price'] * weights.get('DDM', 0):.2f}"],
                    ['Market Multiples', f"${val_data['Multiples']['Implied_Price']:.2f}", f"{weights.get('Multiples', 0):.0%}", f"${val_data['Multiples']['Implied_Price'] * weights.get('Multiples', 0):.2f}"],
                    ['TOTAL WEIGHTED VALUE', f"${wv['IntrinsicValue']:.2f}", '100%', f"${wv['IntrinsicValue']:.2f}"]
                ]
                self._create_styled_table(pdf, valuation_rows[0], valuation_rows[1:], [55, 45, 20, 30])
                
                # Weight Rationales
                pdf.set_font('Arial', 'I', 8)
                pdf.set_text_color(100, 100, 100)
                pdf.multi_cell(0, 4, "Weighting Rationale: "
                               "DCF (40%) reflects long-term cash flow potential; "
                               "Market Multiples (60%) capture sector-leading premiums and peer benchmarks; "
                               "DDM (0%) excluded due to NVDA's growth-focused reinvestment and negligible dividend yield.")
                pdf.ln(4)
                pdf.set_text_color(0, 0, 0)

                # 2. Peer Comparison Table
                tickers = val_data['Multiples']['Tickers']
                rows = [[t, f"${d['MarketCap']/1e9:.1f}B", f"{d['PE']:.1f}x", f"{d['ROE']:.1%}"] for t, d in tickers.items()]
                pdf.sub_title("Peer Relative Valuation Metrics")
                self._create_styled_table(pdf, ['Ticker', 'Mkt Cap', 'P/E TTM', 'ROE'], rows, [40, 40, 30, 30])
                
                # 3. DCF Model Metrics Table
                dcf_data = val_data.get('DCF', {})
                assumptions = dcf_data.get('Assumptions', {})
                pdf.sub_title("Discounted Cash Flow (DCF) Model Parameters")
                dcf_rows = [
                    ['WACC (Discount Rate)', f"{assumptions.get('Derived Discount Rate', 0):.2%}"],
                    ['Terminal Growth Rate', f"{assumptions.get('Terminal Growth (AV GDP)', 0):.2%}"],
                    ['Projected FCF Growth', f"{assumptions.get('Projected Business Growth', 0):.1%}"],
                    ['DCF Implied Share Price', f"${dcf_data.get('Intrinsic Price', 0):.2f}"]
                ]
                self._create_styled_table(pdf, ['Parameter', 'Assumption / Result'], dcf_rows, [70, 70])

                # Side-by-side Images
                p3, p4 = [os.path.join(PLOTS_DIR, x) for x in ['peer_comparison_pe.png', 'dcf_sensitivity_heatmap.png']]
                curr_y = pdf.get_y()
                if curr_y > 190: # Adjusted for more tables
                    pdf.add_page()
                    curr_y = pdf.get_y()
                    
                if os.path.exists(p3): pdf.image(p3, x=10, y=curr_y, w=90)
                if os.path.exists(p4): pdf.image(p4, x=110, y=curr_y, w=90)
                pdf.set_y(curr_y + 70)

        pdf.output(self.pdf_path)
        print(f"Professional multi-page report saved: {self.pdf_path}")
        return self.pdf_path

    def generate_memo(self):
        print("Loading data for memo...")
        ratios_df, valuation = self._load_data()
        if ratios_df is None or valuation is None: return "Missing Data"
        wv = valuation.get('WeightedValuation', {})
        prompt = (f"Analyze {SYMBOL} (NVDA). Market Price: ${valuation.get('CurrentMarketPrice')}, Target Price: ${wv.get('IntrinsicValue')}. "
                  f"Benchmarked vs peers: {PEERS}. Financial stats from latest filing: {ratios_df.iloc[0].to_dict()}. "
                  "Provide a deep, rigorous institutional analysis across 5 sections.")
        print("Synthesizing comprehensive analysis...")
        content = self._get_llm_content(prompt)
        print("Finalizing PDF layout...")
        return self.generate_pdf(content, ratios_df, valuation)

if __name__ == "__main__":
    ReportGenerator().generate_memo()
