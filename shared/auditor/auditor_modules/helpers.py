"""
auditor_modules/helpers.py — Helper methods extracted from QualityAuditor.
"""
import time
from urllib.parse import urlparse

import requests

from config import settings


def is_banned_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = parsed.netloc.lower()
    return any(banned in host for banned in settings.AUDIT_BANNED_HOSTS)


def warm_up_cookies(session: requests.Session, base_url: str) -> None:
    try:
        session.get(base_url, timeout=settings.REQUEST_TIMEOUT, allow_redirects=True)
        time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
    except:
        pass


def close_driver(auditor) -> None:
    if auditor._driver:
        try:
            auditor._driver.quit()
        except:
            pass
        auditor._driver = None


def ensure_non_empty(section: str, issues: list[str]) -> None:
    if not issues:
        issues.append(f"No se detectaron problemas en {section}.")


def collect_metrics(soup, metadata, security_issues, image_issues, link_issues, button_issues, technical_issues, crawl_stats, asset_stats):
    return {
        "total_security_issues": len(security_issues),
        "total_image_issues": len(image_issues),
        "total_link_issues": len(link_issues),
        "total_button_issues": len(button_issues),
        "total_technical_issues": len(technical_issues),
        "crawl_tested": crawl_stats["tested"],
        "crawl_broken": crawl_stats["broken"],
        "assets_checked": asset_stats["checked"],
        "assets_broken": asset_stats["broken"],
    }


def calculate_score(security_issues, seo_issues, content_issues, image_issues, structure_issues, link_issues, button_issues, technical_issues):
    base_score = 100
    penalties = {
        "security": len(security_issues) * 20,
        "seo": len(seo_issues) * 5,
        "content": len(content_issues) * 10,
        "image": len(image_issues) * 3,
        "structure": len(structure_issues) * 5,
        "link": len(link_issues) * 5,
        "button": len(button_issues) * 2,
        "technical": len(technical_issues) * 10,
    }
    total_penalty = sum(penalties.values())
    return max(0, base_score - total_penalty)


def status_from_score(score: int) -> str:
    if score >= 90:
        return "Excelente"
    elif score >= 70:
        return "Bueno"
    elif score >= 50:
        return "Regular"
    else:
        return "Crítico"


def evaluate_release_gate(score, security_issues, content_issues, link_issues, technical_issues, image_issues, button_issues):
    blockers = []
    if score < 50:
        blockers.append("Puntuación baja")
    if security_issues:
        blockers.append("Problemas de seguridad")
    if len(link_issues) > 10:
        blockers.append("Muchos enlaces rotos")
    blocked = len(blockers) > 0
    return blocked, blockers


def build_recommendations(security_issues, seo_issues, content_issues, image_issues, structure_issues, link_issues, button_issues, technical_issues):
    recs = []
    if security_issues:
        recs.append("Implementar cabeceras de seguridad HTTP.")
    if seo_issues:
        recs.append("Optimizar metadatos SEO.")
    if link_issues:
        recs.append("Reparar enlaces rotos.")
    return recs