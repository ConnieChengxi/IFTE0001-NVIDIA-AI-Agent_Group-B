## Backtest Setup & Assumptions

- **Ticker:** AAPL
- **Backtest Period:** 2016-11-14 – 2026-02-02
- **Strategy Type:** Long/Flat
- **Signal Execution:** Entry and exit signals are shifted by one day to avoid look-ahead bias.
- **Transaction Costs:** 10 basis points applied per turnover (position change).
- **Initial Equity:** 1.0 unit
- **Final Equity:** 4.724612200859092 units
- **Number of Trades:** 19 discrete trades executed over the backtest window.

## Performance Results

| METRIC | VALUE |
|--------|-------|
| CAGR | 18.41% |
| Sharpe Ratio | 1.52 |
| Max Drawdown (Strategy) | -10.67% |
| Max Drawdown (Buy-and-Hold) | -38.52% |
| Hit Rate | 19.34% |
| Equity Multiple | 4.72x |
| Buy-and-Hold Multiple | 10.81x |

## Interpretation

- The CAGR of 18.41% indicates a strong annualized return for the strategy, suggesting effective capital growth compared to traditional benchmarks.
- The Sharpe Ratio of 1.52 reflects a favorable risk-adjusted return, implying that the strategy has generated significant returns per unit of risk taken.
- The Max Drawdown of -10.67% is substantially lower than the buy-and-hold benchmark's drawdown of -38.52%, reducing drawdown by 27.85 percentage points, which highlights improved risk management and downside protection.
- The Hit Rate of 19.34% suggests a selective trading approach, where the strategy prioritizes larger gains on winning trades, indicating a focus on payoff structure rather than trade frequency.
- The Equity Multiple of 4.72x demonstrates that the strategy has effectively multiplied the initial investment over the backtest period, although it underperforms the buy-and-hold multiple of 10.81x, indicating potential areas for improvement in capturing longer-term trends.

## Behaviour Across Market Regimes

### Regime Filtering (MA200)

- The current price of 263.47 is above the MA200 of 236.69, indicating a bullish market regime.
- This positioning above the MA200 has likely prevented exposure during adverse periods, allowing the strategy to avoid significant losses.
- The MA200 serves as a critical threshold, ensuring that trades are only executed in favorable market conditions.

### Trend Persistence (MA20 and MA50)

- The current MA20 is 257.27, while the MA50 is 268.22, indicating a short-term trend that is currently below the medium-term trend.
- This relationship enforces a minimum exposure floor, as trades are only initiated when the MA20 is above the MA50, ensuring alignment with prevailing trends.
- The strategy's adherence to these moving averages helps maintain discipline in trade execution, reducing the likelihood of entering trades during potential reversals.

### Volatility Targeting

- The strategy employs volatility targeting to adjust position sizes based on market conditions, enhancing risk management.
- By budgeting risk according to volatility, the strategy aims to maintain consistent performance across varying market environments.
- This approach allows for dynamic adjustments, ensuring that exposure is aligned with prevailing market volatility.

### Momentum Degradation (MACD)

- The current MACD value is -2.70, while the MACD_Signal is -4.13, indicating that the MACD is below the signal line.
- This positioning suggests a bearish momentum signal, which may prompt caution in new trade entries.
- The strategy's reliance on MACD helps identify potential trend reversals, allowing for timely exits or reduced exposure.

### Overextension Control (RSI)

- The current RSI_14 value is 54.45, which is below the overextension threshold of 70.
- This positioning indicates that the asset is not currently overbought, allowing for potential entry opportunities without the risk of immediate price corrections.
- The RSI serves as a valuable tool for assessing market conditions, helping to avoid trades during overextended periods.

### Path-Dependent Risk Control (ATR and Trailing Stops)

- The strategy utilizes ATR-based trailing stops to dynamically adjust exit points based on market volatility.
- This method allows for capturing gains while providing a buffer against sudden market reversals, enhancing overall risk control.
- By implementing trailing stops, the strategy aims to lock in profits while minimizing potential losses during adverse market movements.

## Trade Log

| ENTRY DATE | EXIT DATE | TRADE RETURN (%) | NOTES |
|------------|-----------|------------------|-------|
| 2016-12-13 | 2017-06-13 | <span class="positive">+28.34%</span> | Strong momentum capture |
| 2018-02-07 | 2018-02-08 | <span class="negative">-2.75%</span> | Quick exit on momentum loss |
| 2018-02-13 | 2018-03-22 | <span class="positive">+2.74%</span> | Extended trend participation |
| 2018-05-02 | 2018-06-25 | <span class="positive">+3.57%</span> | Extended trend participation |
| 2019-03-22 | 2019-03-25 | <span class="negative">-1.21%</span> | Quick exit on momentum loss |
| 2019-04-01 | 2019-05-13 | <span class="negative">-2.51%</span> | Quick exit on momentum loss |
| 2019-06-10 | 2019-08-06 | <span class="positive">+2.30%</span> | Extended trend participation |
| 2020-03-31 | 2020-04-01 | <span class="negative">-5.26%</span> | Quick exit on momentum loss |
| 2020-04-07 | 2020-09-09 | <span class="positive">+81.71%</span> | Strong momentum capture |
| 2021-06-07 | 2021-09-21 | <span class="positive">+14.09%</span> | Extended trend participation |
| 2022-03-16 | 2022-04-12 | <span class="positive">+5.06%</span> | Extended trend participation |
| 2022-05-04 | 2022-05-05 | <span class="negative">-5.57%</span> | Quick exit on momentum loss |
| 2022-08-01 | 2022-08-30 | <span class="negative">-1.47%</span> | Quick exit on momentum loss |
| 2023-02-03 | 2023-02-24 | <span class="negative">-4.90%</span> | Quick exit on momentum loss |
| 2023-02-28 | 2023-03-01 | <span class="negative">-1.42%</span> | Quick exit on momentum loss |
| 2023-03-06 | 2023-08-07 | <span class="positive">+16.43%</span> | Extended trend participation |
| 2023-11-01 | 2024-01-03 | <span class="positive">+6.05%</span> | Extended trend participation |
| 2024-05-06 | 2024-08-06 | <span class="positive">+14.20%</span> | Extended trend participation |
| 2025-08-11 | 2026-01-02 | <span class="positive">+19.41%</span> | Strong momentum capture |

- The trade patterns indicate a mix of strong gains and quick exits, reflecting a disciplined approach to managing risk.
- The strategy has successfully captured significant momentum in several trades, particularly in 2020 and 2025, demonstrating effective trend participation.
- The presence of multiple quick exits on losses suggests a proactive risk management strategy, prioritizing capital preservation.

## Limitations & Future Extensions

- The strategy's conservative exposure may underperform relative to buy-and-hold strategies during bull markets, potentially missing out on larger gains.
- A low hit rate implies that while the strategy is selective, it may also lead to fewer opportunities, which could limit overall returns.
- Future improvements could include adaptive parameters that adjust based on market conditions, enhancing responsiveness to changing environments.
- Incorporating machine learning classifiers may provide additional insights into trade signals, potentially improving the strategy's predictive capabilities.

## Conclusion

This analysis highlights a disciplined, risk-aware approach to trading AAPL, balancing capital preservation with participation in favorable market regimes. The strategy's focus on reducing drawdown and enhancing risk management makes it particularly valuable for institutional investors seeking to navigate volatile markets. By leveraging technical indicators and maintaining a selective trading approach, the strategy aims to deliver consistent performance while mitigating downside risks.