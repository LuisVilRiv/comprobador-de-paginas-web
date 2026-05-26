"""
Helpers for auditor modules
"""
from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from config import settings

if TYPE_CHECKING:
    import requests
    from .. import QualityAuditor


def warm_up_cookies(session: requests.Session, url: str) -> None:
    """
    Warms up cookies by making an initial request.
    """
    try:
        session.get(url, timeout=settings.REQUEST_TIMEOUT)
    except Exception:
        pass


def is_banned_url(url: str) -> bool:
    """
    Checks if a URL is banned for network testing.
    """
    domain = urlparse(url).netloc.lower()
    return any(banned_domain in domain for banned_domain in settings.AUDIT_BANNED_DOMAINS)


def find_line(html_lines: list[str], tag: BeautifulSoup) -> tuple[int, str]:
    """
    Finds the line number and content for a given BeautifulSoup tag.
    """
    # Placeholder implementation, as we don't have access to the original
    return 0, str(tag)


def classify_speed(elapsed_ms: int) -> str:
    """
    Classifies the speed of a network request.
    """
    if elapsed_ms < 500:
        return "rápido"
    if elapsed_ms < 1500:
        return "medio"
    return "lento"


def ensure_non_empty(list_name: str, a_list: list) -> None:
    """
    Ensures a list is not empty, adding a default message if it is.
    """
    if not a_list:
        a_list.append("OK")


def close_driver(auditor: QualityAuditor) -> None:
    """
    Closes the Selenium driver if it's running.
    """
    if auditor._driver:
        auditor._driver.quit()
        auditor._driver = None


def collect_metrics(
    soup: BeautifulSoup,
    metadata: dict[str, Any],
    security_issues: list[str],
    image_issues: list[str],
    link_issues: list[str],
    button_issues: list[str],
    technical_issues: list[str],
    crawl_stats: dict[str, int],
    asset_stats: dict[str, int],
) -> dict[str, Any]:
    """
    Collects and returns a dictionary of metrics from the audit.
    """
    # Placeholder implementation
    return {}


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
