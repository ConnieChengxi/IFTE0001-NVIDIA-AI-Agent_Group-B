"""
Common utility functions for financial data processing.
"""

from typing import Any, Dict, List, Optional


def to_float(value: Any) -> Optional[float]:
    """Safely convert value to float."""
    if value is None or value == 'None':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_divide(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Safely divide two numbers, returning None if division is not possible."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def get_latest(data_list: List[Dict], field: str, convert: bool = False) -> Optional[Any]:
    """
    Get the most recent value for a field from a list of financial records.

    Args:
        data_list: List of financial records (most recent first)
        field: Field name to extract
        convert: If True, convert value to float
    """
    if not data_list:
        return None
    value = data_list[0].get(field)
    return to_float(value) if convert else value


def get_historical(data_list: List[Dict], field: str, years: int = 5) -> List[float]:
    """Get historical values for a field from a list of financial records."""
    values = []
    for i in range(min(years, len(data_list))):
        value = to_float(data_list[i].get(field))
        if value is not None:
            values.append(value)
    return values