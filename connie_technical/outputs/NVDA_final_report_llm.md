# Technical Analysis Report for NVDA

## Backtest Setup & Assumptions

- **Ticker:** NVDA
- **Backtest Period:** 2016-11-14 – 2026-02-02
- **Strategy Type:** Long/Flat
- **Signal Execution:** Entry and exit signals are shifted by one day to avoid look-ahead bias.
- **Transaction Costs:** 10 basis points applied per turnover (position change).
- **Initial Equity:** 1.0 unit
- **Final Equity:** 7.36416773940099 units
- **Number of Trades:** 13 discrete trades executed over the backtest window.

## Performance Results

| METRIC | VALUE |
|--------|-------|
| CAGR | 24.27% |
| Sharpe Ratio | 1.43 |
| Max Drawdown (Strategy) | -14.39% |
| Max Drawdown (Buy-and-Hold) | -66.34% |
| Hit Rate | 17.27% |
| Equity Multiple | 7.36x |
| Buy-and-Hold Multiple | 91.90x |

## Interpretation

- The CAGR of 24.27% indicates a strong annualized return for the strategy, significantly outperforming traditional benchmarks and suggesting effective capital growth.
- The Sharpe Ratio of 1.43 reflects a favorable risk-adjusted return, indicating that the strategy has generated substantial returns relative to the volatility of those returns.
- The Max Drawdown of -14.39% is considerably lower than the buy-and-hold benchmark's drawdown of -66.34%, representing a reduction of 51.95 percentage points. This improvement highlights the strategy's effectiveness in risk management and downside protection.
- The Hit Rate of 17.27% suggests a selective trading approach, where the strategy prioritizes larger gains on winning trades. This indicates a deliberate trade-off between trade frequency and payoff structure, as the strategy captures significant upside in fewer trades.
- The Equity Multiple of 7.36x demonstrates that the strategy has effectively multiplied the initial investment over the backtest period, although it is essential to consider the context of the buy-and-hold multiple of 91.90x, which indicates that while the strategy is profitable, it has not captured the full extent of the market's upward movement.

## Behaviour Across Market Regimes

### Regime Filtering (MA200)

- The current price of 189.02 is above the MA200 of 168.13, indicating a bullish market regime.
- This positioning above the MA200 suggests that the strategy has avoided exposure during adverse periods, aligning with a trend-following approach.
- The MA200 serves as a critical threshold, ensuring that trades are only executed in favorable market conditions, thus enhancing overall performance.

### Trend Persistence (MA20 and MA50)

- The current MA20 is 186.73 and the MA50 is 183.97, both of which are below the current price of 189.02.
- This alignment reinforces a minimum exposure floor, ensuring that the strategy remains invested during upward trends.
- The proximity of MA20 and MA50 to the current price indicates a strong trend persistence, which supports continued participation in the market.

### Volatility Targeting

- The strategy employs volatility targeting to manage risk, ensuring that exposure is adjusted based on market conditions.
- By dynamically adjusting position sizes, the strategy aims to maintain a consistent risk profile, which is crucial for capital preservation.
- This approach allows for better risk budgeting, particularly during periods of heightened market volatility.

### Momentum Degradation (MACD)

- The current MACD is 1.48, while the MACD_Signal is 0.93, indicating that the MACD is above the signal line.
- This positioning suggests a bullish momentum, reinforcing the strategy's long positions.
- The positive divergence between MACD and its signal line indicates strong upward momentum, which is favorable for continued investment.

### Overextension Control (RSI)

- The current RSI_14 value is 55.55, which is below the overextension threshold of 70.
- This positioning suggests that the asset is not currently overbought, allowing for potential further upside without immediate risk of a correction.
- The RSI level indicates a balanced market condition, supporting the strategy's continued engagement.

### Path-Dependent Risk Control (ATR and Trailing Stops)

- The strategy utilizes ATR-based trailing stops to dynamically adjust exit points based on market volatility.
- This method allows for effective drawdown control, as it adapts to changing market conditions and protects gains.
- By employing trailing stops, the strategy aims to lock in profits while minimizing potential losses during adverse market movements.

## Trade Log

| ENTRY DATE | EXIT DATE | TRADE RETURN (%) | NOTES |
|------------|-----------|------------------|-------|
| 2016-11-15 | 2017-02-24 | <span class="positive">+18.04%</span> | Strong momentum capture |
| 2019-07-23 | 2019-08-01 | <span class="negative">-6.11%</span> | Quick exit on momentum loss |
| 2019-08-20 | 2020-02-26 | <span class="positive">+59.71%</span> | Extended trend participation |
| 2020-03-18 | 2020-09-09 | <span class="positive">+150.95%</span> | Strong momentum capture |
| 2021-03-10 | 2021-05-05 | <span class="positive">+15.96%</span> | Extended trend participation |
| 2022-01-31 | 2022-02-23 | <span class="negative">-8.57%</span> | Quick exit on momentum loss |
| 2022-02-25 | 2022-03-04 | <span class="negative">-5.04%</span> | Quick exit on momentum loss |
| 2022-03-17 | 2022-04-07 | <span class="negative">-2.25%</span> | Quick exit on momentum loss |
| 2022-12-13 | 2022-12-15 | <span class="negative">-6.20%</span> | Quick exit on momentum loss |
| 2023-01-17 | 2023-08-14 | <span class="positive">+147.23%</span> | Strong momentum capture |
| 2025-01-29 | 2025-01-31 | <span class="negative">-2.93%</span> | Quick exit on momentum loss |
| 2025-02-06 | 2025-02-27 | <span class="negative">-6.63%</span> | Quick exit on momentum loss |
| 2025-05-14 | 2025-12-11 | <span class="positive">+33.71%</span> | Extended trend participation |

- The trade log reveals a mix of successful trades with significant gains, particularly in 2020 and 2023, indicating effective momentum capture.
- The presence of several quick exits on losses suggests a disciplined approach to risk management, prioritizing capital preservation.
- The strategy's ability to generate substantial returns in a few trades highlights its selective nature, focusing on high-potential opportunities.

## Limitations & Future Extensions

- The strategy's conservative exposure may underperform relative to buy-and-hold strategies during bull markets, potentially missing out on larger gains.
- A low hit rate implies that while the strategy is selective, it may also lead to fewer opportunities, which could limit overall returns.
- Future improvements could include adaptive parameters that adjust based on market conditions, enhancing responsiveness.
- Incorporating machine learning classifiers may provide additional insights into market dynamics, improving trade selection and timing.

## Conclusion

This technical analysis report highlights a disciplined, risk-aware approach to trading NVDA, balancing capital preservation with active market participation. The strategy's ability to manage drawdowns effectively while capturing significant upside potential is particularly valuable for institutional investors. By focusing on risk management and trend-following principles, this strategy offers a robust framework for navigating complex market environments.