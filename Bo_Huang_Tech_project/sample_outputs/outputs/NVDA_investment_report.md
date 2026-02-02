# NVDA Investment Research Note
Technical strategy backtest and trade note for NVDA; for educational purposes only, not investment advice.

## 0. Investment Summary
- **Stance**: Cautious / **Action**: Hold
- **Key evidence**:
  - Current signal state shows a long position maintained with a long score of 4, above the required hold threshold of 2.
  - The strategy exhibits a Sharpe ratio of 1.579 and a maximum drawdown of 16.55%, indicating a favorable risk-adjusted return compared to the benchmark.
  - Volatility control mechanisms are operational, with exposure reduced due to risk normalization under current conditions.
- The fundamental overlay is currently **non-binding** under a BUY/HOLD view; it becomes binding only under a SELL rating (which mechanically caps maximum exposure).
- **Risk boundary / invalidation conditions**:
  - Exit if the score drops below 2, indicating a trend/confirmation breakdown.
  - Exit if the fundamental rating downgrades to SELL, which would cap the maximum exposure.

## 1. Investment Instrument & Data
- **Ticker**: NVDA
- **Dataset Description:** 10 years of daily OHLCV (Open/High/Low/Close/Volume) for NVDA, sourced from Yahoo Finance (yfinance). Returns are measured close-to-close using the **adjusted close** price series, which accounts for splits and dividends.
- **Transaction Cost Assumption**: 0.0005 per trade.
- **Execution Timing**: Decision-time signal computed at bar close; execution occurs on the next bar via a 1-bar delay in backtest.

## 2. Main Strategy
The following strategy is the core methodology driving the current recommendation.

## 2.1 Signal Logic
The strategy employs a combination of trend-following and confirmation indicators to determine the optimal entry, holding, and exit points.

- The signal_bin indicates if the strategy is in a long position (1) or flat (0). In this case, we are currently in a long position. 
- The signal’s strength relies on four inputs: 
  - A trend filter using an EMA crossover (weight of 2) that indicates a potential uptrend when the fast EMA (30) is above the slow EMA (150).
  - Three confirmations: a pullback condition (if the close is below the Bollinger Band's midline), an RSI above 45 for strength, and a MACD histogram greater than zero, each contributing a weight of 1.
- Hysteresis is used to distinguish entries from hold conditions. To enter, a score of 4 or higher is needed, while a minimum score of 2 allows the strategy to remain in a long position. Operationally, this design minimizes whipsaws by providing stricter entry criteria.
- Currently, with a long score of 4, the strategy continues to hold, as it exceeds the specified hold threshold.

**Current Signal Status**:
The latest decision was made on 2026-01-30, with a long score of 4, indicating that the strategy is in a long state, recommending to HOLD, with a target exposure of approximately 79.58%.

### Rule Summary
- Trend is up if the fast EMA is above the slow EMA.
- Enter long if conditions exceed an entry score of 4.
- Maintain position as long as the score remains above a hold threshold of 2.

Clarifying note: Signals and target positions are computed at decision-time on each bar; execution is modeled as **next-bar execution** via the single 1-bar shift inside the backtest. Latest snapshot (decision date 2026-01-30): long score 4 (entry threshold 4, hold threshold 2), recommended action HOLD (Maintain), decision-time target exposure 0.7958582689556221.

## 2.2 Positioning and Risk Management
The strategy applies a dynamic risk management framework to adjust exposure based on market conditions and volatility.

- **Base exposure**:
  - The mapping is based on the regime: 1.0 in a bull market (signal bin = 1 and regime = 1), 0.5 in neutral (signal bin = 1 and regime = 0), and 0.25 in bear conditions (only if score is 5 and regime = -1).
- The regime is determined using an EMA buffer where different market scenarios (bull, neutral, bear) dictate the level of allowed exposure.
- The strategy also targets a volatility level of 20%. If the realized volatility is higher, positions are scaled down to control risk, while lower volatility allows for increased exposure, capped by the defined leverage.
- The fundamental overlay acts as a filter; with a current BUY rating, it is non-binding, allowing technical indicators to drive size decisions primarily.

**Transaction Cost Reality**:
As the cost model is based on a commission-like cost proportional to turnover, higher turnover can significantly impact net performance. The design aims to limit unnecessary churn through confirmation logic.

**Pipeline recap**:
The strategy first computes a decision-time signal, then maps that to regime-scaled base exposure, applies volatility targeting, and finally executes the resulting target position on the next bar in the backtest.

## 2.3 Fundamental Overlay
Design: an external fundamental view (Buy/Hold/Sell) is integrated strictly as a risk filter applied to position sizing. It does not alter the technical entry/exit logic; it only constrains maximum exposure when the external rating is SELL, by applying a fixed SELL exposure ceiling multiplier of 0.3. Run status: the exposure cap is enabled and included in the backtest. External view (if available): Rating: BUY; As-of date: 2026-01-31; Source: Idaliia fundamental_analyst_agent (auto-generated memo). See Appendix C for details.

## 2.4 Backtest Performance Analysis
This section reports full-sample performance against a Buy & Hold benchmark to evaluate the strategy.

**Comparison Table**: 
| Metric                                       | Strategy: Hybrid Main | Benchmark: Buy & Hold          |
|----------------------------------------------|-----------------------|--------------------------------|
| Equity End                                   | 24.55                 | 267.29                         |
| Total Return                                 | 23.55                 | 266.29                         |
| CAGR                                         | 0.377                 | 0.749                          |
| Sharpe                                       | 1.579                 | 1.373                          |
| Max Drawdown                                 | -16.55%               | -66.34%                        |
| Hit Rate                                     | 42.86%                | 100%                           |
| Turnover                                     | 55.47                 | 1.00                           |

**Critical interpretation**:
1. **Absolute return vs risk-adjusted return**: The strategy’s CAGR of 37.7% is notably lower than the benchmark’s 74.9%. However, the Sharpe ratio of 1.579 indicates it achieves better risk-adjusted returns despite lower absolute returns. This suggests a more stable capital preservation mechanism.
  
2. **Link drawdown to the mechanism**: The maximum drawdown of -16.55% is significantly less than the benchmark’s -66.34%, corroborated by the strategy's volatility targeting and regime scaling, which thoughtfully reduced exposure during volatile periods.

3. **Capital preservation vs growth framing**: The strategy’s design prioritizes drawdown protection, which comes at the expense of potential upside. The lower CAGR can be viewed as the cost of ensuring capital preservation, particularly through volatile market conditions. 

4. **Cost and turnover reality**: The designed churn reduction mitigates costs, reflecting that lower turnover is generally more cost-effective. Given the high turnover of 55.47 for the strategy, trading costs pose a relevant risk, particularly in volatile markets.

## 2.5 Visual Evidence
This section uses chart-based evidence, referencing figures as necessary.

1. **Overview**: The equity curve (see FULL\_equity.png) shows a gradual ascent during the early years, with noticeable drawdowns corresponding to market stress periods, shown in the drawdown chart (see FULL\_drawdown.png). The benchmark demonstrates a much deeper drawdown.

2. **Specific feature analysis**: The drawdown chart (see FULL\_drawdown.png) suggests that the main strategy's drawdown is visibly shallower compared to the benchmark during stressed market conditions, underpinning the effectiveness of the risk controls described. Furthermore, the annual return chart (see FULL\_annual\_return.png) outlines that years with smoother returns for the strategy avoided extreme benchmark losses, corroborating the narrative of the strategy's design focusing on a smoother growth trajectory. Lastly, the equity curve (see FULL\_equity.png) illustrates that while the growth trajectory of the strategy is less steep in bullish years, it emphasizes risk-managed performance more effectively.

## 3. Key Risks & Model Limitations
A few intrinsic risks and limitations arise from the operational mechanics of the strategy:

1. **Strategy-specific risks**:
   - **Whipsaw risk**: In sideways or choppy markets, the confirmation logic may fail, leading to repeated small losses.
   - **Lag risk**: As a score-based strategy, signals can react with delay during sharp market reversals, causing the main strategy to lag the market and miss early upturn entries.
   - **Model form risk**: The thresholds for entry and exit are discrete, rendering the strategy sensitive to slight market movements around these thresholds.

2. **Structural limitations**:
   - **Single-asset dependency**: The findings are limited to NVDA's idiosyncratic market dynamics and cannot be generalized.
   - **Parameter sensitivity**: Changes in parameters may affect performance; more details can be found in Appendix A.

3. **Operational / data risks**:
   - Reliability of data vendor inputs may pose risks due to missing bars or historical adjustments that could skew results.
   - Execution realism: The next-bar execution model may not reflect precise live market fill conditions.

## 4. Conclusion
**Executive Directive**
- **Action**: Hold based on the latest signal snapshot.
- **Verdict**: Maintain long exposure as technical indicators remain favorable, with synchronization within risk management controls.

**Position Sizing Guidance**
- **Target allocation**: Approximately 79.59% of capital allocation is currently targeted. 
- **Sizing context**: Classified as a Reduced allocation based on the target exposure. This reduction primarily reflects the strategy’s risk controls (regime scaling and volatility targeting); the fundamental overlay is non-binding here and therefore does not drive sizing.
**Critical Watchlist (Scenario / boundaries)**
- **Continuation trigger**: Hold as long as the trend remains intact and the score maintains above the hold threshold of 2.
- **Invalidation trigger (risk-off / stop rule)**: Exit if the score falls below 2 or if the fundamental rating downgrades to SELL, necessitating exposure reduction.

---

---

---

---

---

---

---

---

---

---

---

---

---

### APPENDIX

Supplementary only; not part of the main recommendation.
For fair comparison, all appendix strategies use the same close-to-close returns based on the adjusted close price series and the same 1-bar execution-delay convention.

## Appendix A. Parameter Selection and Robustness

### A.1 Dataset Split & Selection Framework

We use a simple time-based split to reduce overfitting risk and to keep the parameter-selection process auditable.

- **Sample window (data)**: 2016-02-01 to 2026-01-30.
- **Split dates**: Train end = 2019-12-31; Validation end = 2022-12-31; Test = remaining tail period.

Segment roles:
- **Train**: estimate rolling statistics/calibrations (e.g., volatility baseline) without peeking into later periods.
- **Validation**: select parameters (e.g., choose the best setting by validation Sharpe within a small grid).
- **Test**: out-of-sample sanity check to confirm the chosen configuration is not purely an in-sample artifact.

Motivation:
- **Anti-leakage**: prevents look-ahead bias in calibration and selection.
- **Traceability**: links the chosen parameters to an explicit validation criterion.
- **Falsifiability**: provides an out-of-sample checkpoint before drawing conclusions.

Note: the MAIN report still presents full-sample performance for transparency, but parameter choice is driven by the validation segment to reduce selection bias.

### A.2 Parameter Sensitivity

This robustness check varies the main-strategy parameter grid on the **full sample** and reports how performance changes.

- Best-by-Sharpe: ema_fast=30, ema_slow=150, regime_buffer_pct=0.01, vol_window=40 (Sharpe 1.5412, total return 18.9850, max drawdown -0.1884).
- Ranges across grid: Sharpe 1.3494 to 1.5412; total return 13.6935 to 23.8787; max drawdown -0.2463 to -0.1750.

**Parameter range rationale.** Economic and mechanistic interpretation: the grid varies a small set of interpretable parameters with clear financial meaning. The fast/slow EMA windows correspond to medium-to-long trend horizons (avoiding short-term noise fitting). The regime buffer defines a narrow band around the slow EMA for bull/neutral/bear classification, reducing boundary whipsaws. The volatility window sets the time scale for realized-volatility estimation used in volatility targeting. Overall, the grid is intentionally compact: it explores plausible time horizons and risk-estimation windows rather than optimizing over highly flexible, hard-to-explain knobs.

| Params | Sharpe | Total Return | Max Drawdown |
| --- | --- | --- | --- |
| ema_fast=20, ema_slow=100, regime_buffer_pct=0.01, vol_window=10 | 1.3494 | 16.4311 | -0.2443 |
| ema_fast=20, ema_slow=100, regime_buffer_pct=0.01, vol_window=40 | 1.4055 | 13.6935 | -0.1884 |
| ema_fast=20, ema_slow=100, regime_buffer_pct=0.02, vol_window=10 | 1.3529 | 16.3780 | -0.2463 |
| ema_fast=20, ema_slow=100, regime_buffer_pct=0.02, vol_window=40 | 1.4138 | 13.7448 | -0.1750 |
| ema_fast=30, ema_slow=150, regime_buffer_pct=0.01, vol_window=10 | 1.4982 | 23.8787 | -0.1777 |
| ema_fast=30, ema_slow=150, regime_buffer_pct=0.01, vol_window=40 | 1.5412 | 18.9850 | -0.1884 |
| ema_fast=50, ema_slow=200, regime_buffer_pct=0.01, vol_window=10 | 1.4305 | 20.2876 | -0.2062 |
| ema_fast=50, ema_slow=200, regime_buffer_pct=0.01, vol_window=40 | 1.4588 | 16.0390 | -0.1809 |

## Appendix B. Strategy Comparison
This section provides a qualitative discussion of experimental variants relative to the main strategy.

### B.0 Summary of experimental variants
Compared with the main strategy, the appendix variants illustrate the empirical trade-off between simplicity, confirmation filters, and added feature complexity:

- **MA-only crossover**: higher exposure and higher headline return, but materially larger drawdown (drawdown increases by -21.00% versus Main).
- **Volume-confirmed entry**: slightly lower exposure with similar turnover; risk-adjusted performance changes modestly (Sharpe differs by -0.0302 versus Main).
- **Pattern-enabled**: turnover is materially higher (increase of +116.0987 versus Main), with a weaker risk-adjusted profile in this run.

These comparisons are descriptive (full-sample backtests) and are included for robustness/interpretability rather than as primary recommendations.

### B.1 MA-only crossover strategy
We compare a simple moving-average crossover rule against the benchmark and the main strategy to illustrate how reducing model complexity can change the risk profile.

| Metric | Benchmark | Main | MA-only crossover |
| --- | --- | --- | --- |
| CAGR | 0.7490 (74.90%) | 0.3774 (37.74%) | 0.5599 (55.99%) |
| Sharpe | 1.3731 | 1.5793 | 1.2852 |
| Max Drawdown | -0.6634 (-66.34%) | -0.1655 (-16.55%) | -0.3755 (-37.55%) |
| Hit Rate | 1.0000 (100.00%) | 0.4286 (42.86%) | 1.0000 (100.00%) |
| Turnover | 1.0000 | 55.4721 | 7.0000 |
| Exposure | 0.9996 (99.96%) | 0.7812 (78.12%) | 0.7407 (74.07%) |
| Total Return | 266.2863 (26628.63%) | 23.5464 (2354.64%) | 84.1390 (8413.90%) |

**Discussion.** A simple MA-only baseline can capture strong trends with high exposure, but it may also exhibit materially larger drawdowns and a weaker risk-adjusted profile depending on the path of returns.

### B.2 Volume-confirmed entry filter
This experiment adds a simple volume-based confirmation to the main strategy: entries are only allowed when **relative volume** is above a threshold, as a proxy for stronger market participation.

| Metric | Benchmark | Main | Volume confirm |
| --- | --- | --- | --- |
| CAGR | 0.7490 (74.90%) | 0.3774 (37.74%) | 0.3664 (36.64%) |
| Sharpe | 1.3731 | 1.5793 | 1.5492 |
| Max Drawdown | -0.6634 (-66.34%) | -0.1655 (-16.55%) | -0.1813 (-18.13%) |
| Hit Rate | 1.0000 (100.00%) | 0.4286 (42.86%) | 0.4286 (42.86%) |
| Turnover | 1.0000 | 55.4721 | 55.2015 |
| Exposure | 0.9996 (99.96%) | 0.7812 (78.12%) | 0.7661 (76.61%) |
| Total Return | 266.2863 (26628.63%) | 23.5464 (2354.64%) | 21.6626 (2166.26%) |

**Discussion.** Volume confirmation can reduce marginal trades and lower exposure, which may improve robustness in sideways regimes, but it can also miss early trend participation; the net effect must be evaluated empirically (as in the table above).

### B.3 Pattern-enabled variant
This experiment augments the technical decision rule with lightweight, interpretable price-action features computed from OHLCV bars.

Pattern features (as implemented):
- **Bullish/Bearish engulfing**: two-candle body engulfing heuristic.
- **Hammer / Shooting star**: wick-to-body ratio heuristic (reversal-like candles).
- **Donchian breakout**: close breaking above/below a lagged rolling channel (trend continuation / breakdown).

Integration policy (signal layer): bullish patterns can contribute to the long-score when enabled; bearish patterns act as an explicit risk-off exit trigger (close position).

| Metric | Benchmark | Main | Patterns |
| --- | --- | --- | --- |
| CAGR | 0.7490 (74.90%) | 0.3774 (37.74%) | 0.2382 (23.82%) |
| Sharpe | 1.3731 | 1.5793 | 1.2722 |
| Max Drawdown | -0.6634 (-66.34%) | -0.1655 (-16.55%) | -0.2375 (-23.75%) |
| Hit Rate | 1.0000 (100.00%) | 0.4286 (42.86%) | 0.5484 (54.84%) |
| Turnover | 1.0000 | 55.4721 | 171.5708 |
| Exposure | 0.9996 (99.96%) | 0.7812 (78.12%) | 0.5223 (52.23%) |
| Total Return | 266.2863 (26628.63%) | 23.5464 (2354.64%) | 7.4636 (746.36%) |

**Discussion.** Pattern features increase model complexity and can raise instability/overfitting risk. If the pattern-enabled variant does not improve the risk-adjusted profile (e.g., Sharpe and drawdown) relative to the main strategy, it is best treated as an appendix experiment rather than as the primary recommendation.

## Appendix C. Fundamental Overlay
In this project, the main strategy includes a fundamental overlay as part of the **risk-management layer**. Alongside the technical rules, we incorporate a third-party fundamental assessment (Buy/Hold/Sell) as a **risk-control overlay**. It is treated as external context that constrains sizing, not as an alpha signal that generates trades. In other words, the chart-based rules still decide when the strategy is long or flat; fundamentals only influence how much exposure we are willing to carry.

In practical terms, the external view is grounded in standard market-facing fundamentals: valuation multiples (e.g., forward/trailing P/E, P/S, P/B, EV/EBITDA) and sell-side expectations (e.g., consensus recommendation and analyst target-price range). These inputs do not enter the strategy as a return predictor; they provide an interpretable check on whether the market is pricing the stock at historically rich levels and whether analyst expectations are broadly supportive. Within this project, that context is deliberately translated into a sizing constraint rather than an entry/exit signal.

The overlay is implemented as a **hard exposure ceiling**. If the external rating is **SELL**, the strategy reduces the maximum allowable leverage by a fixed multiplier (a SELL ceiling multiplier of 0.3). If the rating is **BUY/HOLD**, the ceiling is typically non-binding, so the realised return path can be identical to the pure technical strategy.

To preserve point-in-time integrity (no look-ahead bias), the rating is applied from its stated **as-of** date forward. The backtest does not assume that future rating changes were known in advance.

In this run, the overlay was applied in the backtest as a sizing cap.
Latest available view in the payload: Rating: BUY; As-of date: 2026-01-31; Source: Idaliia fundamental_analyst_agent (auto-generated memo). Notes: not provided.

Practical note: when the rating is BUY/HOLD, the cap may not bind; in that case, the "Tech+Fund" variant can be indistinguishable from the main strategy and a separate curve may be omitted to avoid a misleading comparison.
