# AAPL - Technical Trade Note

## 1. Executive Summary
AAPL has shown a strong performance in the backtest period from November 14, 2016, to February 2, 2026. The strategy employed has yielded a final equity of approximately 4.72 times the initial investment, with a compound annual growth rate (CAGR) of 18.41%. The current market regime is bullish, indicating potential for continued upward movement.

## 2. Current Signal Snapshot
- Latest close price: 263.47
- 20-day moving average (MA): 257.27
- 50-day moving average (MA): 268.22
- 200-day moving average (MA): 236.69
- 14-day Relative Strength Index (RSI): 54.45
- MACD: -2.70
- MACD signal: -4.13
- Bullish regime: true

## 3. Backtest Results (with transaction costs)
- Backtest window: November 14, 2016 - February 2, 2026
- Initial equity: 1.0
- Final equity: 4.72
- CAGR: 18.41%
- Sharpe ratio: 1.52
- Maximum drawdown: -10.67%
- Hit rate: 19.34%
- Number of trades: 19
- Approximate number of trades: 112
- Transaction costs: 10 basis points

## 4. Risk & Position Sizing Considerations
- Maximum drawdown of 10.67% indicates a moderate risk level.
- The hit rate of 19.34% suggests that the strategy may require careful position sizing to manage risk effectively.
- Given the bullish regime, a larger position size may be considered, but caution is advised due to the historical drawdown and hit rate.

## 5. Limitations & Next Steps
- The backtest results are based on historical data and may not predict future performance.
- The strategy assumes a long/flat approach with entry/exit signals shifted by one day to avoid look-ahead bias.
- Transaction costs are applied per turnover, which may impact overall profitability.
- Next steps include monitoring the current market conditions and adjusting positions as necessary based on updated signals and performance metrics.

Charts referenced for further analysis:
- Equity Drawdown: outputs/AAPL_equity_drawdown.png
- Golden Cross Trades: outputs/AAPL_golden_cross_trades.png
- Price, MA, MACD (6 months): outputs/AAPL_price_ma_macd_6m.png
- Equity Log Compare: outputs/AAPL_equity_log_compare.png
- Drawdown Compare: outputs/AAPL_drawdown_compare.png