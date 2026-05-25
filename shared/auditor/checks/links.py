"""
check_links_recursive — Rastreo de enlaces rotos con profundidad configurable.
Extraído de QualityAuditor._check_links_recursive.
"""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import shared.auditor.auditor_modules.helpers as helpers
from config import settings


def check_links_recursive(
    soup: BeautifulSoup,
    base_url: str,
    html_lines: list[str],
    issues: list[str],
    crawl_stats: dict,
    is_banned_fn,
    check_url_fn,
    classify_speed_fn,
    find_line_fn,
    blocked_admin_segments: tuple,
) -> None:
    if is_banned_fn(base_url):
        issues.append("Rastreo recursivo omitido por URL prohibida.")
        return

    base_host = urlparse(base_url).netloc.lower().lstrip("www.")
    queue: list[tuple[str, int]] = []
    seen: set[str] = {base_url}  # Evitar volver a rastrear la URL base

    for anchor in soup.find_all("a"):
        href = helpers.attr_to_str(anchor.get("href")).strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        if href.startswith("#"):
            fragment = href[1:]
            if fragment and not soup.find(id=fragment) and not soup.find("a", attrs={"name": fragment}):
                ln, line = find_line_fn(html_lines, anchor)
                issues.append(f'Ancla rota: href="{href}" apunta a un id que no existe. Línea {ln}: {line}')
            continue
        full = urljoin(base_url, href)
        if full not in seen:
            seen.add(full)
            queue.append((full, 0))
        if any(seg in full.lower() for seg in blocked_admin_segments):
            ln, line = find_line_fn(html_lines, anchor)
            issues.append(f"Enlace prohibido detectado {full} en línea {ln}: {line}")

    # Límite absoluto de iteraciones del bucle para prevenir ciclos infinitos
    max_loop_iterations = settings.AUDIT_MAX_RECURSIVE_LINKS * 3
    iterations = 0

    while queue and crawl_stats["tested"] < settings.AUDIT_MAX_RECURSIVE_LINKS and iterations < max_loop_iterations:
        iterations += 1
        url, depth = queue.pop(0)

        if is_banned_fn(url):
            crawl_stats["skipped"] += 1
            issues.append(f"Enlace omitido por política de bloqueo: {url}")
            continue

        result = check_url_fn(url, include_content=(depth < settings.AUDIT_MAX_CRAWL_DEPTH))
        ok, elapsed_ms, status_code = result[0], result[1], result[2]
        content = result[3] if len(result) > 3 else ""
        crawl_stats["tested"] += 1
        speed = classify_speed_fn(elapsed_ms)

        if not ok:
            crawl_stats["broken"] += 1
            issues.append(f"Enlace roto confirmado {url} estado={status_code} tiempo={elapsed_ms}ms ({speed})")

        if content and depth < settings.AUDIT_MAX_CRAWL_DEPTH:
            page_soup = BeautifulSoup(content, settings.BS4_PARSER)
            for inner_anchor in page_soup.find_all("a"):
                href = helpers.attr_to_str(inner_anchor.get("href")).strip()
                if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                    continue
                full_inner = urljoin(url, href)
                if full_inner in seen:
                    continue
                inner_host = urlparse(full_inner).netloc.lower().lstrip("www.")
                if inner_host != base_host:
                    continue
                seen.add(full_inner)
                queue.append((full_inner, depth + 1))
