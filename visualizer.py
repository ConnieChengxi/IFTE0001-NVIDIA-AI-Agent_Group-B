import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
from config import SYMBOL, PROCESSED_DATA_DIR, PLOTS_DIR

class Visualizer:
    def __init__(self):
        # Professional aesthetics
        sns.set_theme(style="whitegrid", palette="muted")
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['axes.titleweight'] = 'bold'
        
    def plot_financial_ratios(self, ratios_csv):
        if not os.path.exists(ratios_csv): return
        df = pd.read_csv(ratios_csv)
        df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'])
        df = df.sort_values('fiscalDateEnding')

        # 1. Profitability Trends (Dual Axis)
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(df['fiscalDateEnding'], df['Gross Margin'], marker='o', label='Gross Margin', linewidth=2, color='#2ecc71')
        ax1.plot(df['fiscalDateEnding'], df['Operating Margin'], marker='s', label='Operating Margin', linewidth=2, color='#3498db')
        ax1.plot(df['fiscalDateEnding'], df['Net Margin'], marker='^', label='Net Margin', linewidth=2, color='#e74c3c')
        ax1.set_title(f"{SYMBOL} Profitability Margins (%)")
        ax1.set_ylabel("Margin Ratio")
        ax1.legend(loc='lower left')
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, "profitability_trends.png"), dpi=300)
        plt.close()

        # 2. Return Ratios (Modern look)
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=df, x='fiscalDateEnding', y='ROE', marker='o', label='ROE', color='#9b59b6', linewidth=2.5)
        sns.lineplot(data=df, x='fiscalDateEnding', y='ROA', marker='s', label='ROA', color='#f1c40f', linewidth=2.5)
        plt.title(f"{SYMBOL} Capital Efficiency (ROE vs ROA)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, "return_ratios.png"), dpi=300)
        plt.close()

    def plot_valuation_analysis(self, valuation_json):
        if not os.path.exists(valuation_json): return
        with open(valuation_json, 'r') as f:
            data = json.load(f)

        # 1. Market Multiples (Enhanced Horizontal Bar)
        multiples_data = data.get("Multiples", {})
        if multiples_data:
            tickers_dict = multiples_data.get("Tickers", {})
            if tickers_dict:
                peers = list(tickers_dict.keys())
                pe_values = [tickers_dict[p].get("PE", 0) for p in peers]
                
                plt.figure(figsize=(8, 5))
                colors = ['#1a1a1a' if p == SYMBOL else '#bdc3c7' for p in peers]
                sns.barplot(x=pe_values, y=peers, hue=peers, palette=colors, legend=False)
                plt.title("Valuation Context: P/E Multiple Comparison")
                plt.xlabel("Price-to-Earnings Ratio")
                plt.tight_layout()
                plt.savefig(os.path.join(PLOTS_DIR, "peer_comparison_pe.png"), dpi=300)
                plt.close()

        # 2. DCF Sensitivity Heatmap (Polished)
        dcf = data.get("DCF", {})
        sensitivity = dcf.get("Sensitivity Analysis", {})
        if sensitivity:
            growth_rates = list(sensitivity.keys())
            discount_rates = list(sensitivity[growth_rates[0]].keys())
            matrix_data = [[sensitivity[g][d] for d in discount_rates] for g in growth_rates]
            heatmap_df = pd.DataFrame(matrix_data, index=growth_rates, columns=discount_rates)
            
            plt.figure(figsize=(10, 7))
            sns.heatmap(heatmap_df, annot=True, fmt=".2f", cmap="YlGnBu", cbar_kws={'label': 'Intrinsic Price ($)'}, linewidths=.5)
            plt.title(f"{SYMBOL} DCF Sensitivity Matrix")
            plt.xlabel("Discount Rate")
            plt.ylabel("Growth Rate")
            plt.tight_layout()
            plt.savefig(os.path.join(PLOTS_DIR, "dcf_sensitivity_heatmap.png"), dpi=300)
            plt.close()

    def run_all(self):
        print("Generating visualizations...")
        self.plot_financial_ratios(os.path.join(PROCESSED_DATA_DIR, f"{SYMBOL}_ratios_annual.csv"))
        self.plot_valuation_analysis(os.path.join(PROCESSED_DATA_DIR, f"{SYMBOL}_valuation.json"))
        print(f"Plots saved to {PLOTS_DIR}")

if __name__ == "__main__":
    v = Visualizer()
    v.run_all()
