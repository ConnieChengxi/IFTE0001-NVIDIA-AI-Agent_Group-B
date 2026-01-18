from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _ensure_outdir(path: str):
    if path:
        os.makedirs(path, exist_ok=True)


def _get_entry_exit_points(df: pd.DataFrame):
    """
    Returns two DataFrames with rows where entry / exit == True
    """
    entries = df[df.get("entry", False)]
    exits = df[df.get("exit", False)]
    return entries, exits


# -----------------------------
# Price + MA + Entry/Exit
# -----------------------------
def plot_price_with_signals(
    df: pd.DataFrame,
    ticker: str,
    outpath: Optional[str] = None,
):
    """
    Price chart with MA20 / MA50 / MA200 and entry/exit markers.
    """
    required = {"Close", "MA20", "MA50", "MA200"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns for plot_price_with_signals: {missing}")

    entries, exits = _get_entry_exit_points(df)

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(df.index, df["Close"], label="Close", linewidth=1.2)
    ax.plot(df.index, df["MA20"], label="MA20", linestyle="--", alpha=0.8)
    ax.plot(df.index, df["MA50"], label="MA50", linestyle="--", alpha=0.8)
    ax.plot(df.index, df["MA200"], label="MA200", linestyle="-", linewidth=1.5)

    ax.scatter(
        entries.index,
        entries["Close"],
        marker="^",
        color="green",
        s=60,
        label="Entry",
        zorder=5,
    )
    ax.scatter(
        exits.index,
        exits["Close"],
        marker="v",
        color="red",
        s=60,
        label="Exit",
        zorder=5,
    )

    ax.set_title(f"{ticker} Price with Trend & Signals")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    if outpath:
        _ensure_outdir(os.path.dirname(outpath))
        plt.savefig(outpath, dpi=150)
    plt.close(fig)


# -----------------------------
# RSI
# -----------------------------
def plot_strategy_rsi(
    df: pd.DataFrame,
    ticker: str,
    outpath: Optional[str] = None,
):
    required = {"RSI_14"}
    if not required.issubset(df.columns):
        raise ValueError("RSI_14 column missing for RSI plot")

    fig, ax = plt.subplots(figsize=(12, 3))

    ax.plot(df.index, df["RSI_14"], label="RSI(14)")
    ax.axhline(70, linestyle="--", alpha=0.6)
    ax.axhline(30, linestyle="--", alpha=0.6)

    ax.set_ylim(0, 100)
    ax.set_title(f"{ticker} RSI(14)")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    if outpath:
        _ensure_outdir(os.path.dirname(outpath))
        plt.savefig(outpath, dpi=150)
    plt.close(fig)


# -----------------------------
# MACD
# -----------------------------
def plot_macd(
    df: pd.DataFrame,
    ticker: str,
    outpath: Optional[str] = None,
):
    required = {"MACD", "MACD_Signal", "MACD_Hist"}
    if not required.issubset(df.columns):
        raise ValueError("MACD columns missing for MACD plot")

    fig, ax = plt.subplots(figsize=(12, 4))

    ax.plot(df.index, df["MACD"], label="MACD", linewidth=1.2)
    ax.plot(df.index, df["MACD_Signal"], label="Signal", linewidth=1.2)

    colors = np.where(df["MACD_Hist"] >= 0, "green", "red")
    ax.bar(df.index, df["MACD_Hist"], color=colors, alpha=0.3, label="Histogram")

    ax.axhline(0, linewidth=1)
    ax.set_title(f"{ticker} MACD")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    if outpath:
        _ensure_outdir(os.path.dirname(outpath))
        plt.savefig(outpath, dpi=150)
    plt.close(fig)


# -----------------------------
# Short-term signal diagnostics
# -----------------------------
def plot_strategy_shortterm(
    df: pd.DataFrame,
    ticker: str,
    outpath: Optional[str] = None,
):
    """
    Diagnostic chart: position_hint vs Close.
    Useful to visually confirm signal timing & regime behaviour.
    """
    if "position_hint" not in df.columns:
        raise ValueError("position_hint column missing for short-term diagnostic plot")

    fig, ax1 = plt.subplots(figsize=(12, 4))

    ax1.plot(df.index, df["Close"], label="Close", alpha=0.7)
    ax1.set_ylabel("Price")

    ax2 = ax1.twinx()
    ax2.fill_between(
        df.index,
        0,
        df["position_hint"],
        color="green",
        alpha=0.2,
        step="post",
        label="Position (1=Long)",
    )
    ax2.set_ylim(0, 1.2)
    ax2.set_ylabel("Position")

    ax1.set_title(f"{ticker} Position Regime (Diagnostic)")
    ax1.grid(alpha=0.3)

    plt.tight_layout()
    if outpath:
        _ensure_outdir(os.path.dirname(outpath))
        plt.savefig(outpath, dpi=150)
    plt.close(fig)
