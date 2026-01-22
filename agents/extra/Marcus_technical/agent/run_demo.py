# run_demo.py
from src.data_loader import load_nvda
from src.indicators import add_ema, add_rsi, add_atr
from src.strategy import generate_signal
from src.backtest import run_backtest
from src.metrics import compute_metrics
from src.llm_report import generate_llm_summary, save_llm_summary


def main():
    df = load_nvda()
    df = add_ema(df)
    df = add_rsi(df)
    df = add_atr(df)
    df = generate_signal(df)
    df = run_backtest(df)

    # ✅ metrics must be created BEFORE using them
    metrics = compute_metrics(df)

    strategy_desc = (
        "Long-only NVDA technical strategy using EMA(20/50) trend signal, "
        "RSI(14) filter (avoid entries when RSI >= 70), ATR(14) volatility-based "
        "position sizing, and transaction costs."
    )

    # ✅ LLM summary AFTER metrics
    try:
        text = generate_llm_summary(metrics, strategy_desc)
        save_llm_summary(text, out_path="outputs/llm_summary.md")
        print("Saved LLM summary to outputs/llm_summary.md")
    except Exception as e:
        print(f"(LLM summary skipped) {e}")

    print("\nNVDA Trend Strategy Performance")
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}")


if __name__ == "__main__":
    main()
