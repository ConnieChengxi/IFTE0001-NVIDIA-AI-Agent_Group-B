"""
Demo script for Zehui Fundamental Agent
Run from repo root or this directory:
    python agents/extra/Zehui_fundamental/run_demo.py
"""

from agents.extra.Zehui_fundamental.agent.agent import run


def main():
    symbol = "NVDA"   # 你也可以之后改成参数
    out = run(symbol)

    print(f"\n=== Fundamental Analysis Demo for {symbol} ===\n")

    print("Income Statement (bn):")
    print(out["is_view"], "\n")

    print("Balance Sheet (bn):")
    print(out["bs_view"], "\n")

    print("Cash Flow (bn):")
    print(out["cf_view"], "\n")


if __name__ == "__main__":
    main()
