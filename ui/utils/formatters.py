"""Formatting helpers for financial values."""

from typing import Optional


def fmt_pct(value: Optional[float], decimals: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:+.{decimals}f}%"


def fmt_price(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def fmt_ratio(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def fmt_multiple(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}x"


def fmt_market_cap(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    if value >= 1e12:
        return f"${value / 1e12:,.1f}T"
    if value >= 1e9:
        return f"${value / 1e9:,.1f}B"
    return f"${value / 1e6:,.0f}M"
