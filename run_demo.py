# run_demo.py

from src.data_loader import load_nvda
from src.indicators import add_ema, add_rsi, add_atr
from src.strategy import generate_signal
from src.backtest import run_backtest
from src.metrics import compute_metrics
from src.llm_report import generate_trade_note, save_trade_note


def main():
    # Load and prepare data
    df = load_nvda()
    df = add_ema(df)
    df = add_rsi(df)
    df = add_atr(df)
    df = generate_signal(df)
    df = run_backtest(df)

    # Compute performance metrics
    metrics = compute_metrics(df)

    # Strategy description (plain English)
    strategy_desc = (
        "Long-only NVDA technical strategy using EMA(20/50) trend alignment, "
        "RSI(14) as a momentum filter to avoid overbought entries, ATR(14) for "
        "volatility awareness and risk management, and proportional transaction costs."
    )

    # Indicator settings passed to the LLM
    indicator_settings = {
        "EMA_fast": 20,
        "EMA_slow": 50,
        "RSI": 14,
        "ATR": 14,
    }

    # Generate LLM trade note
    try:
        trade_note = generate_trade_note(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            latest_date=str(df.index[-1].date()),
            latest_close=float(df["Close"].iloc[-1]),
            indicators=indicator_settings,
            metrics=metrics,
            strategy_desc=strategy_desc,
            assumptions={
                "transaction_costs": "Proportional cost applied on position changes",
                "slippage": "Not explicitly modelled",
                "data_source": "Yahoo Finance via yfinance",
            },
        )

        save_trade_note(trade_note, out_path="outputs/trade_note.md")
        print("Saved trade note to outputs/trade_note.md")

    except Exception as e:
        print(f"(LLM trade note skipped) {e}")

    # Print performance summary to terminal
    print("\nNVDA Trend Strategy Performance")
    for k, v in metrics.items():
        try:
            print(f"{k}: {v:.4f}")
        except Exception:
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()

