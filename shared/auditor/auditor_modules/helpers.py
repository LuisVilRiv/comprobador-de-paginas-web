"""Helpers for auditor modules"""
from __future__ import annotations

def attr_to_str(value: str | list[str] | None) -> str:
    """
    Safely converts an attribute value to a string.
    BeautifulSoup attributes can be str, list[str], or None.
    """
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(value)
    return value
