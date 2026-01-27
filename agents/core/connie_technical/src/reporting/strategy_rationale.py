# src/reporting/strategy_rationale.py

def get_strategy_rationale() -> str:
    """
    Fixed Strategy Rationale written by the author.
    This section must be included verbatim in the final report.
    Mathematical expressions are intentionally excluded and
    documented separately in the LaTeX report.
    """
    return """
## Strategy Design Philosophy (Buy-Side Perspective)

### 1. Evolution of the Strategy: From Mechanical Signal to Risk-Aware Allocation

The strategy did not originate as a multi-indicator system.
It initially relied on a single mechanical rule—the Golden Cross (MA50 > MA200)—to identify long-term trend transitions.
While intuitive, this approach proved too discrete and brittle for a large-cap technology stock characterised by volatility clustering and momentum persistence.

In practice, a pure Golden Cross framework suffers from late entries after substantial price appreciation, frequent whipsaws during high-volatility consolidation phases, and an inability to distinguish between structural trend deterioration and temporary market noise.

This motivated a shift away from binary entry/exit logic toward a continuous, risk-aware exposure framework.
Indicators are therefore selected not to vote on market direction, but to dynamically shape risk and exposure across regimes.

This evolution reflects a buy-side mindset: the objective is not to predict returns, but to allocate risk efficiently.

---

### 2. Indicator Selection Philosophy: One Role, One Indicator

Each indicator in the Technical AI Agent is assigned a single, non-overlapping role.
Indicators are not used redundantly, nor are they asked to perform beyond their statistical strengths.

#### MA200 – Structural Regime Filter (Market Participation)

The 200-day moving average is used as a structural regime filter rather than a timing signal.
When price is below the long-term trend, capital is withheld regardless of shorter-term momentum signals.
This design prioritises capital preservation and limits exposure to prolonged adverse regimes.

#### MA20 and MA50 – Trend Persistence and Exposure Floor

Shorter-term moving averages are used to assess trend persistence once a favourable regime is established.
Rather than triggering frequent trades, they enforce a minimum level of exposure during confirmed uptrends.
This mitigates systematic under-investment during strong momentum phases.

#### Volatility Targeting – Risk Budget Allocation

Volatility targeting determines how much risk to take, not whether to take risk.
Exposure is scaled to maintain a stable risk profile over time, preventing excessive leverage during volatility spikes while allowing higher exposure when conditions are stable.

#### MACD – Momentum Degradation Filter

MACD is used to detect momentum deterioration rather than to trigger discrete trades.
When momentum weakens, exposure is reduced proportionally rather than exited entirely.
This preserves optionality and reduces turnover during temporary trend pauses.

#### RSI – Overextension Control

RSI is applied asymmetrically as a risk control mechanism.
It is never used to increase exposure and only acts to scale down positions during overextended conditions.
This reflects crowding and mean-reversion risk, particularly relevant for large-cap technology equities.

#### ATR and Trailing Stops – Path-Dependent Risk Control

Volatility-based trailing stops are employed to control drawdowns during nonlinear price reversals.
By adapting to prevailing volatility, exits remain responsive across changing market environments without relying on static thresholds.

---

### 3. Indicator Interaction: A Hierarchical Risk Stack

Indicators are not combined democratically.
Instead, the strategy enforces a strict hierarchy:

- Regime filters determine whether capital is deployed.
- Trend persistence defines baseline commitment.
- Volatility targeting allocates the core risk budget.
- Momentum and overextension filters fine-tune exposure.
- Trailing stops control tail risk and exit timing.

This hierarchy avoids signal conflict and mirrors discretionary buy-side portfolio construction, where risk considerations dominate directional conviction.

---

### 4. Why This Is a Technical AI Agent

The agent does not forecast returns or price levels.
Instead, it adapts behaviour across regimes through structured state transitions embedded in a deterministic decision pipeline.

Exposure is continuous rather than binary, indicators modulate risk rather than trigger trades, and regime awareness dominates execution logic.
In this sense, the agent reflects an interpretable, rule-based form of artificial intelligence aligned with institutional investment processes.
"""
