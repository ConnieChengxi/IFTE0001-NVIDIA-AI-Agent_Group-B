from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI  # optional
except Exception:  # pragma: no cover
    OpenAI = None


def _load_dotenv_if_present() -> None:
    """
    Minimal .env loader (no external deps). Reads KEY=VALUE lines from .env in cwd.
    Does not overwrite existing environment variables.
    """
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        # Silent fail to avoid breaking report generation if .env is malformed
        return


def _build_prompt(payload: dict[str, Any]) -> str:
    """Academic prompt for a course-grade quant investment report.

    Goals:
      - Objective, restrained, academic tone (no marketing language).
      - Strict MAIN vs APPENDIX separation.
      - Fully grounded in provided payload (no invented metrics or indicators).
    """

    ticker = payload.get("ticker", "")
    run_params = payload.get("run_params", {}) or {}

    # Prefer reproducible date if provided; otherwise label as latest.
    as_of = run_params.get("as_of")
    report_date = as_of if as_of and str(as_of).lower() not in ("latest", "none", "") else "LATEST"

    # Optional metadata (safe defaults)
    analyst = run_params.get("analyst", "Bo Huang")

    def _collect_png_filenames(obj: Any) -> list[str]:
        """Collect .png filenames from a nested JSON-like structure."""
        out: list[str] = []
        if obj is None:
            return out
        if isinstance(obj, str):
            s = obj.strip()
            if s.lower().endswith(".png"):
                out.append(os.path.basename(s))
            return out
        if isinstance(obj, (list, tuple)):
            for x in obj:
                out.extend(_collect_png_filenames(x))
            return out
        if isinstance(obj, dict):
            for v in obj.values():
                out.extend(_collect_png_filenames(v))
            return out
        return out

    # Try to find figure filenames in common payload locations, but fall back to scanning outputs.
    outputs = payload.get("outputs", {}) or {}
    fig_main = []
    fig_app = []

    # Common explicit lists (if present)
    if isinstance(payload.get("figures_main"), (list, tuple)):
        fig_main.extend(_collect_png_filenames(payload.get("figures_main")))
    if isinstance(payload.get("figures_appendix"), (list, tuple)):
        fig_app.extend(_collect_png_filenames(payload.get("figures_appendix")))

    # Scan outputs sections
    if isinstance(outputs, dict):
        fig_main.extend(_collect_png_filenames(outputs.get("main")))
        fig_app.extend(_collect_png_filenames(outputs.get("appendix")))

    # De-duplicate while preserving a stable sort
    fig_main = sorted(set([f for f in fig_main if f]))
    fig_app = sorted(set([f for f in fig_app if f]))

    main_fig_line = ", ".join(fig_main) if fig_main else "Not provided"
    app_fig_line = ", ".join(fig_app) if fig_app else "Not provided"

    # Prompt is split into 3 layers to reduce model drift:
    # (i) SYSTEM: role + hard constraints
    # (ii) REPORT_SPEC: report structure + MAIN/APPENDIX boundary
    # (iii) PAYLOAD_POLICY: only use JSON; missing -> "Not provided in this run."

    system = f"""SYSTEM (Role + hard constraints)
    You are a Senior Investment Strategist writing a deep-dive technical analysis report for high-net-worth individual investors.

    STYLE (Professional yet Accessible):
    - Tone: Authoritative but educational. Explain *why* a signal matters in plain English, avoiding excessive jargon.
    - Perspective: Focus on "So What?". Connect technical signals to clear investment actions (Buy/Hold/Protect).
    - Risk-Centric: Frame returns in terms of "Sleeping well at night" (Drawdown control) vs "Chasing high-risk gains".
    - Clarity: Use active voice. Avoid "AI Fluff".
    - Do NOT claim causality beyond what the backtest supports.

    Context:
    - Instrument: {ticker}
    - Analyst: {analyst}
    - Report date (data as-of): {report_date}

    STRICT RULES (non-negotiable):
    1) Use ONLY the information and numeric values present in the INPUT JSON payload (metrics, annual returns, diagnostics, assumptions). Do NOT invent any performance numbers.
    2) Do NOT invent prices, targets, support/resistance, macro events, earnings figures, or any performance numbers.
    3) Do NOT invent narrative facts (earnings, news, macro drivers, AI chip cycle, analyst ratings) unless the payload explicitly contains such facts.
    4) Do NOT recompute performance from raw prices (no close_end/close_start, no external data). Use provided metrics and annual return tables only.
    5) Maintain metric semantics:
       - equity_end is the final equity value given initial_capital (if initial_capital=1.0, equity_end is the equity multiple).
       - total_return and CAGR are DECIMALS (not percents). If you show %, convert explicitly and show both.
    6) The report must be interpretable, evidence-based, and reproducible.
    7) Add an education-only disclaimer: "for educational purposes only, not investment advice".
    8) If annual returns include a "label" (e.g., "2026 YTD (through YYYY-MM-DD)"), use that label.
    """.strip()

    report_spec = f"""REPORT_SPEC (Structure + scope boundary)
    Write a complete English investment analysis report in Markdown based on the INPUT JSON payload.

    You MUST follow this structure and headings exactly:

    # {ticker} Investment Research Note
    Include one line under the title:
    "Technical strategy backtest and trade note for {ticker}; for educational purposes only, not investment advice."

    ## 0. Investment Summary
    Provide a concise executive summary (bullet points are acceptable). Must include:
    - **Stance** (Bullish / Neutral / Cautious) and **Action** (Buy / Hold / Sell / Watch).
      Use the latest signal snapshot if provided (run_params.signal_snapshot); otherwise state "Not provided in this run."
    - **Key evidence (2–4 points)** grounded in the payload only:
      Examples: current signal state, Sharpe/max drawdown vs benchmark, volatility targeting + leverage cap,
      and whether the fundamental overlay is binding or non-binding in this run.
    - **Risk boundary / invalidation conditions** (1–3 points) stated in terms of your rules:
      e.g., "exit when the hold condition is no longer met", "bear-regime exposure is reduced by policy", "SELL rating caps exposure".
    Do NOT include any equations, formulas, or code in this section.
    Do NOT discuss turnover or trade counts in this section; reserve that for the Backtest section.

    ## 1. Investment Instrument & Data
    Must include (only if present in JSON):
    - Ticker, exchange, currency (if available).
    - Data frequency and sample window (years, as-of).
    - Dataset description: explicitly state “10 years of daily OHLCV (Open/High/Low/Close/Volume)” for the instrument (standard phrasing; do not invent numeric values).
    - Return definition (verbatim, from JSON).
    - Transaction cost assumption.
    - Execution timing (decision-time signal; execution next bar via 1-bar delay in backtest).
    - Do NOT explain train/validation/test methodology here; move all split discussion to the appendix section specified below.

    Formatting rules (apply to headings):
    - Do NOT use empty parentheses “()”.
    - Do NOT use parenthetical qualifiers in headings (avoid “(…)” in titles). Put emphasis/qualification in the first sentence under the heading instead.
    - Avoid code-like “name=value” phrasing; use analyst prose.

    ## 2. Main Strategy
    Start this section with one short bridging sentence that frames this as the **core strategy used for the main recommendation**.
    Do NOT mention experimental variants here (MA-only, patterns, etc.). Those belong in the Appendix.

    ### 2.1 Signal Logic
    Explain both the **logic** (how the signal is built) and the **reason** (why each piece exists), using concrete, non-abstract language.
    Write this as **readable narrative prose** (2–4 short paragraphs). Avoid a “checklist feel”.
    The reader should be able to answer: *when do we enter, when do we hold, when do we exit, and why?*

    Fidelity rule (non‑negotiable):
    - Use ONLY the strategy rules provided in `strategy_spec_main` and the latest snapshot fields in `run_params.signal_snapshot`.
    - Do NOT infer/guess thresholds or formulas. If a detail is missing, say “Not provided in this run.”

    Use this structure (no code blocks):

    Required coverage (in prose; you can use 3–6 short bullets at the end if needed):
    - Define what `signal_bin` represents in plain English (long/flat state; not the final position size).
    - Explain the “four inputs”: Trend + three confirmations (Pullback, RSI, MACD), and how the **score** is formed (trend has weight 2; each confirmation weight 1).
    - Explain hysteresis clearly: why entry is stricter than holding, and what ENTER/HOLD/EXIT mean operationally.
    - Quote the actual entry/hold thresholds if present in JSON; otherwise state they are not provided.

    **Timing Note (must be explicit and consistent with this codebase):**
    - Signals are computed at decision time on each bar (end-of-bar). Execution is modeled as **next-bar execution** via the 1-bar shift inside the backtest (do not claim “next open” unless the payload explicitly uses opens).

    **Current Signal Status (only if present in JSON):**
    - If `run_params.signal_snapshot` exists, state in one tight paragraph:
      Decision date, current long score, whether the strategy is currently in a long state, the recommended action (ENTER/HOLD/EXIT/WATCH), and the decision-time target exposure (if provided).
      If any field is missing, write “Not provided in this run.”

    **Rule Summary (optional; max 5 bullets; no equations):**
    Keep this short and human-readable. Do not paste code-like expressions.

    ### 2.2 Positioning and Risk Management
    Describe the risk engine as a dynamic protection layer.
    Write this as **readable narrative prose** (2–4 short paragraphs) that explains what ultimately determines “how much to invest”.
    Use only `strategy_spec_main` + `run_params` fields; do not invent any risk rules.

    Required coverage:
    - Regime-scaled **base exposure**: explain the bull/neutral/bear mapping at a high level (1.0 / 0.5 / 0.25 / 0.0) and what “bear requires strongest score” means.
    - 3‑state regime definition: explain the EMA_slow buffer band idea in words (no equations).
    - Volatility targeting: explain the intent (risk normalization) and the mechanics (higher vol → smaller position; lower vol → larger position, capped).
    - Fundamental overlay (if configured): explain it as a hard cap; BUY/HOLD often non‑binding, SELL binding.

    **Transaction Cost Reality (must mention)**
    - Explain that the cost model is `trading_cost * turnover` (commission-like). Higher turnover makes performance more cost-sensitive.
    - Connect this back to design intent: the hysteresis buffer and confirmation logic are partly there to reduce unnecessary churn (whipsaws), not to maximize trading frequency.

    **Pipeline recap (one short paragraph)**
    - Summarise the ordering explicitly:
      Write this as normal prose (no arrow symbols). Example style:
      “The strategy first forms a decision-time signal, then maps it to a regime-scaled base exposure, then applies volatility targeting and any leverage caps, and finally executes the resulting target position on the next bar in the backtest.”

    ### 2.3 Fundamental Overlay
    Include this subsection if **either**:
    - the INPUT JSON contains a fundamental view (rating/as-of/source), **or**
    - the run configuration indicates fundamentals were requested (e.g., `run_params.fundamental_mode` in ["filter", "report_only"] or `run_params.fundamental_requested` is true),
    even if the external fundamental module failed in this run.

    Core requirement: explain fundamentals strictly as a **Risk Filter (Hard Constraint)**, not an entry/exit signal. Do not invent any fundamental facts beyond the payload.

    Write this subsection in three parts:

    **(A) What it is (Mechanism)**
    - Explain that the strategy integrates an *external* fundamental rating (Buy/Hold/Sell) to **constrain maximum exposure** via a leverage cap.
    - Use the payload terminology/fields:
      - `sell_leverage_mult` defines how strongly SELL reduces the cap (SELL → cap multiplied by this factor).
      - Fundamentals do not change the technical signal; they only cap the position sizing layer.

    **(B) How it behaves (Scenario logic; must be explicit)**
    - SELL: defensive posture; the cap is binding and limits exposure even if technicals are bullish.
    - BUY/HOLD: typically **dormant / non-binding** (cap not restrictive); sizing is primarily driven by the technical engine and volatility targeting.

    **(C) What happened in this run (Status + transparency)**
    - State whether the overlay was actually applied in the backtest using `run_params.overlay_used_in_backtest` (if present).
    - If the payload shows the external module failed / returned no view (e.g., missing `fundamental_view`/`fundamental_overlay`, or `run_params.idaliia_result.ok` is false, or `run_params.fundamental_snapshot.ok` is false), you MUST:
      1) still describe the policy (A)+(B) as the intended design, and
      2) explicitly disclose that the external data were not available, therefore the cap could not be applied in this run (i.e., the overlay was not active / not binding due to missing inputs).

    **Source + reproducibility**
    - Name the source/analyst/module exactly as given in the payload (e.g., Idaliia fundamental module).
    - If the payload provides saved output paths (memo/log/report copy), direct readers to the appendix artifacts without pasting the full text.

    DEPTH REQUIREMENT:
    - Write 2–4 short paragraphs (not a single paragraph). Keep it readable, but do not make it vague.
    - State clearly that fundamentals are external (not authored/estimated by this technical strategy code).
    - If `run_params.run_idaliia` is true and the payload includes `run_params.idaliia_result.memo_copy_rel`, state that
      the pipeline generated an external Idaliia fundamental memo and saved it at that path for reproducibility (display-only).
    - Explain the integration as a risk overlay, NOT alpha:
      - Entry/exit timing remains technical.
      - Fundamental view only constrains maximum exposure (a leverage/position cap) when rating is SELL.
    - If `run_params.fundamental_mode` is "filter": state that the backtest includes this exposure cap.
    - If `run_params.fundamental_mode` is "report_only": state it is qualitative context only (not included in backtest).
    - If SELL rating is present: describe the policy in plain English (reduce exposure to the capped maximum using sell_leverage_mult) without inventing any new numbers.
    - End the paragraph by directing readers to Appendix C for details.

    ### 2.4 Backtest Performance Analysis
    First sentence must state this section reports full-sample performance (unless the payload indicates otherwise).
    Present the comparison table (Main vs Benchmark) first. Then provide a **critical interpretation** that ties the numbers back to the strategy mechanics.

    **Step 1 — Quantitative table (must include, only if present in JSON):**
    - Main Strategy vs Benchmark (Buy & Hold, fair 1-bar delayed execution)
    - Include at least: equity_end, total_return, CAGR, Sharpe, max drawdown, hit rate, turnover, exposure.
    - Keep semantics: total_return and CAGR are decimals (show % only if you convert explicitly).

    **Step 2 — Critical interpretation (write 3–6 short paragraphs; not bullet-only):**
    Use the following structure and be concrete, not abstract:

    1) **Absolute return vs risk-adjusted return**
       - Compare CAGR (growth) vs Sharpe (risk-adjusted efficiency).
       - Explain the trade-off: a strategy can “give up” some upside if it meaningfully reduces drawdowns/volatility.

    2) **Link drawdown to the mechanism**
       - Explicitly connect the observed drawdown profile to the risk engine in 2.2:
         volatility targeting and leverage caps mechanically reduce exposure during high-stress periods, which should translate into smaller drawdowns (if supported by the numbers).
       - Do not claim this worked “in every crisis” unless the annual-return / drawdown figures in the payload support it.

    3) **Capital preservation vs growth framing (client-readable, but evidence-based)**
       - You may use the “insurance premium” framing **only as an interpretation**:
         if the Benchmark has higher CAGR/total_return but much larger drawdown, explain that the main strategy’s lower CAGR can be viewed as the cost of capital preservation and survivability.
       - Avoid hype; keep it measured and grounded in the reported metrics.

    4) **Cost and turnover reality**
       - Discuss how turnover interacts with the cost model (`trading_cost * turnover`), and why a churn-reduction design (hysteresis) is economically meaningful.
       - Do not invent slippage or commissions beyond what the payload provides.

    **Tone constraints (important):**
    - The benchmark is context; the recommendation is driven by the strategy signal + risk controls.
    - Do NOT use vague narratives like “lack of momentum” unless the payload explicitly supports that claim.
    - Be confident but not promotional: the report should read like professional research, not marketing.

    ### 2.5 Visual Evidence
    First sentence must state this is chart-based evidence and figures are referenced by filename only.
    Use the provided figures as **evidence** to support the claims in 2.1–2.4. Reference figures by filename only (do not embed images, do not invent charts).
    - MAIN figures available: {main_fig_line}

    Provide both:
    1) **Overview (high-level)**: 3–6 sentences describing the overall trajectory of the equity curve and the comparative volatility/drawdown profile visible in the charts.
    2) **Specific feature analysis (evidence-based)**: 2–4 short paragraphs that point to *concrete* chart features and connect them to the strategy mechanism.

    Evidence rules (non-negotiable):
    - Do NOT invent “events” or “market narratives”. If you mention a year (e.g., 2022), it must be supported by the annual returns table in the JSON and/or the figure’s labeling.
    - Use cautious language: “the chart suggests / is consistent with …” rather than claiming certainty about unseen details.
    - Reference filenames in human-readable prose, e.g., “... (see FULL_drawdown.png).” Do not leave bare filenames dangling at the end of a clause.
      Do NOT wrap filenames in inline-code backticks; keep them as plain text so the report reads like analyst prose.
    - Use precise drawdown language: say “drawdown deepens / becomes more negative / peak-to-trough loss is larger”, not “a decline in drawdown”.
    - Do not infer “volatility exposure” from the chart alone; if you discuss volatility, tie it explicitly to the reported `vol`/`exposure` metrics in the payload.

    Required evidence points (if the corresponding figure exists; otherwise say “Not provided”):
    - **Drawdown protection / risk control**: Use `FULL_drawdown.png` to describe whether the main strategy’s drawdown is visibly shallower than Buy & Hold during stress windows, and connect this to the mechanics in 2.2 (regime scaling, volatility targeting, leverage caps).
      - If the annual returns table indicates a notably negative year (commonly 2022), you may reference that year specifically as an example, but only if the payload supports it.
    - **Return consistency**: Use `FULL_annual_return.png` (or `FULL_annual_returns.csv` if referenced in the payload) to identify years where the strategy avoided very large benchmark losses or displayed smoother outcomes, and connect this to the “risk normalization / safety ceiling” idea.
      - If the fundamental overlay is present and **binding** (SELL), you may mention the “safety ceiling” framing; if it is BUY/HOLD (non-binding), say that the ceiling is conceptually present but may not materially change the curve in this run.
    - **Equity path interpretation**: Use `FULL_equity.png` to highlight whether the strategy’s growth is smoother but potentially lower in strong bull runs, consistent with a risk-managed long/flat design.

    If MAIN figures are not provided, state: "Main figures not provided in this run.".

    ## 3. Key Risks & Model Limitations
    Provide a candid assessment of what could go wrong. Do not sugarcoat. Avoid generic boilerplate; tie risks to the actual mechanics described in Sections 2.1–2.3.

    Cover the following (use short subsections or bullets):

    1) **Strategy-specific risks**
       - **Whipsaw risk**: In choppy, sideways markets (no persistent trend), confirmation logic and hysteresis can still fail, leading to small but repeated losses and higher turnover.
       - **Lag risk**: EMA-based trend filters are inherently lagging; the strategy can be late to sharp V-shaped reversals and may miss the earliest phase of a rebound.
       - **Model form risk**: The score/hysteresis thresholds are discrete; the strategy may be sensitive to small changes around the boundary (enter/exit thresholds).

    2) **Structural limitations**
       - **Single-asset dependency**: Results are entirely tied to this ticker’s idiosyncratic path; conclusions may not generalize.
       - **Parameter sensitivity**: Performance may vary if EMA windows, confirmation thresholds, or vol windows change. If sensitivity results exist in the payload, reference Appendix A as evidence; otherwise acknowledge the limitation.

    3) **Operational / data risks**
       - Data vendor reliability (missing bars, corporate actions, adjusted vs unadjusted series) and how this can change measured returns.
       - Execution realism: the backtest uses a simplified next-bar execution model with a commission-like cost (`trading_cost * turnover`) and does not guarantee live-fill prices or slippage behavior.
    
    Note: do not include any LLM/provider disclosure in the main narrative. A short disclosure will be shown in the report sidebar under “Disclaimer”.

    ## 4. Conclusion
    Synthesize the analysis into a clear, actionable directive for a client. The benchmark is context only; the recommendation must be driven by the **current signal state** and **risk controls**.

    Write this section in the following format (keep it crisp, not verbose):

    **Executive Directive**
    - **Action**: **[BUY / HOLD / SELL / WATCH]** based on the latest signal snapshot (do not guess if the snapshot is missing; write “Not provided in this run.”).
    - **Verdict**: One sentence summarising the stance and the dominant constraint (trend vs volatility controls vs fundamental cap). Example style:
      “Maintain defensive long exposure as the primary trend remains intact, while position sizing is throttled by volatility controls.”

    **Position Sizing Guidance**
    - **Target allocation**: Convert the decision-time target exposure (if provided) into a percentage (e.g., 0.60 → ~60% notional allocation). If not provided, state “Not provided in this run.”
    - **Sizing context**: Classify the allocation qualitatively as **Full / Reduced / Minimal** based on the percentage, and give a *causal* explanation grounded in the pipeline:
      - If sizing is reduced, attribute it to the strategy’s risk controls (e.g., regime scaling and volatility targeting), not to the benchmark.
      - If the fundamental filter is **SELL** (binding cap), say it is an additional constraint on top of the technical sizing.
      - If the fundamental filter is **BUY/HOLD** (non-binding), say it does **not** constrain exposure and should **not** be cited as the reason for reduced sizing.

    **Critical Watchlist (Scenario / boundaries)**
    - **Continuation trigger**: State the objective conditions under which the position is maintained (e.g., trend holds and score remains above the hold threshold).
    - **Invalidation trigger (risk-off / stop rule)**: State the objective exit conditions:
      - Exit if the score drops below the hold threshold (trend/confirmation breakdown),
      - OR (if fundamentals are used as a filter) if the fundamental rating downgrades to SELL, which forces risk reduction via the exposure cap.

    Constraints:
    - Do not invent numeric thresholds; if the exact entry/hold thresholds are not present in the payload, refer to them generically (Entry threshold / Hold threshold).
    - Keep it professional and actionable, but not promotional.

    APPENDIX
    First sentence must state: “Supplementary only; not part of the main recommendation.”

    ## Appendix A. Parameter Selection & Robustness
    ### A.1 Dataset Split & Selection Framework
    Explain (in 1–2 short paragraphs) why the dataset is split and how each segment is used in this pipeline:
    - Train: used to fit rolling statistics / calibrations (e.g., volatility baseline), not to “learn” prices.
    - Validation: used for parameter selection (e.g., choose the best setting by validation Sharpe).
    - Test: used as an out-of-sample sanity check to assess robustness.
    Also clarify that the MAIN report performance table is shown on the full sample, but parameters are selected using the validation segment to reduce overfitting.
    Use the split dates from the payload if present; otherwise write “Not provided in this run.”

    ### A.2 Parameter Sensitivity (Main Strategy)
    If sensitivity results are present in the INPUT JSON, present them as a Markdown table.
    Table requirements:
    - One row per run / parameter setting.
    - Columns (use whatever subset exists in JSON, but keep this order):
      parameter, value, Sharpe, max_drawdown, vol, turnover_sum, exposure, equity_end, total_return, CAGR.
    - Keep metric semantics: equity_end/total_return/CAGR are decimals (optionally show percent equivalents in parentheses).
    Then summarise:
    - Best-by-Sharpe setting (if identifiable from the table),
    - The observed stability/instability across the tested range,
    - **Robustness interpretation**: comment briefly on whether the Best-by-Sharpe setting appears to be an outlier (potentially overfit) or part of a stable cluster (more robust),
    - A brief economic/mechanistic justification for why the tested range is reasonable (e.g., EMA windows represent medium/long trend horizons; regime buffer reduces boundary whipsaws; vol window is the risk-estimation horizon).
    If sensitivity results are not present, state: "Sensitivity analysis not provided in this run.".

    ## Appendix B. Strategy Comparison (Discussion)
    Provide a short discussion of the experimental variants and what they imply:
    - B.1 MA-only (crossover) strategy: compare vs benchmark and main; discuss return vs drawdown vs Sharpe. Address explicitly whether the added complexity of confirmations/score/risk controls improves **risk-adjusted** returns, or whether the MA-only rule is sufficient but riskier.
    - B.2 Volume-confirmed entry filter (if present): interpret whether a volume gate reduces marginal trades and improves robustness, or simply reduces participation (lower return) without improving risk-adjusted outcomes.
    - B.3 Pattern-enabled variant (if present): define the pattern features at a high level (no equations) and interpret whether adding candlestick patterns adds signal value or mostly noise/turnover in this run.

    ## Appendix C. Fundamental Filter (Risk Control, not Alpha)
    Write a detailed, academically grounded description (3–6 paragraphs) ONLY using what exists in the INPUT JSON.
    Structure:
    1) Source & Scope:
       - State that the fundamental view is external (module/report) and is referenced by source/notes in the payload.
       - Clarify what the rating represents (Buy/Hold/Sell) only as described in payload; do not speculate.
    2) Integration in this project (risk filter):
       - Explain that fundamentals do NOT generate entry/exit signals.
       - Explain the **Safety Ceiling** mechanism: the fundamental rating constrains maximum exposure via a leverage cap.
         - SELL: the cap becomes binding and forces risk reduction even if technicals are bullish.
         - BUY/HOLD: the cap is typically dormant (non-binding), allowing sizing to be driven by the technical + vol targeting engine.
       - Elaborate on `sell_leverage_mult` as a mechanical cap (use the numeric value only if present in JSON).
       - Explain whether it was applied in backtest (fundamental_mode == filter) or report-only.
    3) Governance / leakage control:
       - Explain point-in-time enforcement: the rating is applied from its `as_of` date forward (or conservatively lagged if the payload indicates), avoiding look-ahead bias.
       - State that this is a policy overlay designed to reduce risk during unfavourable fundamentals.
    4) Interpretation & limitations:
       - Discuss how this overlay affects risk (drawdown/exposure) rather than claiming alpha.
       - List limitations (external dependency, update frequency, non-reproducible without the external report if not packaged).
    Source context:
       - Briefly mention the source of the fundamental view (e.g., Idaliia memo/report/module) as provided in the payload to establish provenance, without adding outside claims.

    Data usage guidance (important):
    - Do **not** paste large tables or “data dumps” in Appendix C.
    - It is acceptable (and encouraged) to cite a few **key** payload fields (e.g., rating, as_of, sell_leverage_mult, whether the overlay was applied, and one or two representative valuation/target figures if present) and then explain what they imply for the risk-cap mechanism.
    Reproducibility addendum (at the end of Appendix C):
    - If `run_params.idaliia_result.log_copy_rel` exists, mention it as the saved Idaliia run log.
    - If `run_params.repro_cmd` exists, include it verbatim as a single inline code block on its own line.
    If the JSON does not include a fundamental view, state: "Not provided in this run.".
    """.strip()

    payload_policy = """PAYLOAD_POLICY (grounding + missing-data behavior)
    - Use ONLY the INPUT JSON payload. Do not rely on any outside knowledge.
    - If a field/metric/table is not present in the JSON, explicitly say: "Not provided in this run."
    - If a field exists but is empty, explicitly say it is empty.
    - Reference figures by filename only (do not embed images in Markdown).
    """.strip()

    input_json = f"""INPUT JSON:
    {json.dumps(payload, indent=2, default=str)}""".strip()

    return "\n\n\n".join([system, report_spec, payload_policy, input_json]).strip()



def generate_report_markdown(
    payload: dict[str, Any],
    *,
    openai_model: str = "gpt-4o-mini",
    timeout_s: int = 600,
    **_: Any,
) -> str:
    """Generate report markdown via OpenAI.

    This packaged project is intentionally **OpenAI-only** (no Ollama support).
    Extra keyword args are ignored via `**_` for compatibility with older callers.
    """
    prompt = _build_prompt(payload)

    if OpenAI is None:
        raise RuntimeError("openai package not installed. pip install openai")
    _load_dotenv_if_present()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY. Set it in .env or terminal: export OPENAI_API_KEY='sk-...'")

    # Note: timeout_s is kept for API compatibility, but the SDK-level timeout is not
    # wired here to keep the dependency surface minimal for course grading.
    _ = timeout_s

    client = OpenAI()
    r = client.responses.create(
        model=openai_model,
        input=[{"role": "user", "content": prompt}],
    )
    return (r.output_text or "").strip()
