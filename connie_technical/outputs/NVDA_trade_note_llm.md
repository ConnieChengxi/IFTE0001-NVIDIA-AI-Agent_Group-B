# NVDA - Technical Trade Note

## 1. Executive Summary
NVIDIA (NVDA) has demonstrated a strong performance in the backtest period from November 14, 2016, to February 2, 2026. The strategy employed has yielded a final equity of approximately 7.36 times the initial investment, with a compound annual growth rate (CAGR) of 24.27%. The current market regime is bullish, supported by a positive MACD and an RSI indicating strength.

## 2. Current Signal Snapshot
- Latest close price: 189.02
- 20-day moving average: 186.73
- 50-day moving average: 183.97
- 200-day moving average: 168.13
- 14-day RSI: 55.55
- MACD: 1.48
- MACD signal: 0.93
- Current regime: Bullish

## 3. Backtest Results (with transaction costs)
- Backtest window: November 14, 2016 - February 2, 2026
- Initial equity: 1.0
- Final equity: 7.36
- CAGR: 24.27%
- Sharpe ratio: 1.43
- Maximum drawdown: -14.39%
- Hit rate: 17.27%
- Number of trades: 13
- Approximate number of trades: 228
- Transaction costs: 10 bps

## 4. Risk & Position Sizing Considerations
- Maximum drawdown of the strategy is -14.39%, which is significantly lower than the buy-and-hold maximum drawdown of -66.34%.
- The hit rate of 17.27% indicates that the majority of trades are not profitable, which necessitates careful position sizing to manage risk effectively.

## 5. Limitations & Next Steps
- The backtest results are based on historical data and may not predict future performance.
- The number of trades (13) is relatively low, which may limit the robustness of the strategy.
- Future analysis should consider additional market conditions and potential changes in volatility.
- Next steps include monitoring the current market conditions and adjusting the strategy as necessary based on ongoing performance and market developments. 

Charts referenced for further analysis:
- Equity drawdown: outputs/NVDA_equity_drawdown.png
- Golden cross trades: outputs/NVDA_golden_cross_trades.png
- Price, MA, and MACD over 6 months: outputs/NVDA_price_ma_macd_6m.png
- Equity log comparison: outputs/NVDA_equity_log_compare.png
- Drawdown comparison: outputs/NVDA_drawdown_compare.png