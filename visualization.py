from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd


def plot_metric_ax(ax, x, y, title: str, yfmt: str | None = None):
    ax.plot(x, y, marker="o")
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.grid(True, alpha=0.3)
    if yfmt == "pct":
        ax.set_ylabel("Ratio")
    else:
        ax.set_ylabel("Value")


def plot_ratios_trends(ratios_df: pd.DataFrame, out_dir: Path) -> None:
    years = ratios_df["fiscal_year"]
    metrics = [
        ("gross_margin", "Gross Margin", "pct"),
        ("operating_margin", "Operating Margin", "pct"),
        ("net_margin", "Net Margin", "pct"),
        ("roa", "ROA", "pct"),
        ("roe", "ROE", "pct"),
    ]
    for col, title, fmt in metrics:
        if col not in ratios_df.columns:
            continue
        fig, ax = plt.subplots(figsize=(7, 4))
        plot_metric_ax(ax, years, ratios_df[col], title, fmt)
        fig.tight_layout()
        fig.savefig(out_dir / f"ratio_{col}.png", dpi=200)
        plt.close(fig)


def plot_multiples_charts(multiples_df: pd.DataFrame, out_dir: Path) -> None:
    # bar charts for EV/EBITDA and EV/Sales, scatter EV/EBITDA vs EV/Sales
    df = multiples_df.copy()

    for col in ["EV/EBITDA", "EV/Sales", "P/E"]:
        if col not in df.columns:
            continue
        fig, ax = plt.subplots(figsize=(7, 4))
        df[col].plot(kind="bar", ax=ax)
        ax.set_title(col)
        ax.set_xlabel("")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / f"multiples_{col.replace('/','_')}.png", dpi=200)
        plt.close(fig)

    if "EV/EBITDA" in df.columns and "EV/Sales" in df.columns:
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(df["EV/EBITDA"], df["EV/Sales"])
        for idx, row in df.iterrows():
            ax.annotate(idx, (row["EV/EBITDA"], row["EV/Sales"]))
        ax.set_title("EV/EBITDA vs EV/Sales")
        ax.set_xlabel("EV/EBITDA")
        ax.set_ylabel("EV/Sales")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "multiples_scatter.png", dpi=200)
        plt.close(fig)
