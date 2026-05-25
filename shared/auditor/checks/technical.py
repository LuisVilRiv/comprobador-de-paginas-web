"""
check_technical — DOCTYPE, charset, assets, iframes, IDs duplicados, favicon, etc.
Extraído de QualityAuditor._check_technical y _check_assets.
"""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup


def check_technical(
    html: str,
    soup: BeautifulSoup,
    base_url: str,
    html_lines: list[str],
    issues: list[str],
    asset_stats: dict,
    recommendations: list[str],
    is_banned_fn,
    check_url_fn,
    classify_speed_fn,
    find_line_fn,
) -> None:
    html_lower = html.lower()
    if "<!doctype html>" not in html_lower[:300]:
        issues.append("Falta <!DOCTYPE html> al inicio del documento.")

    if not soup.find("meta", attrs={"charset": True}):
        issues.append("Falta <meta charset='utf-8'>.")

    if not soup.find("meta", attrs={"name": "robots"}):
        issues.append("Falta meta robots.")

    for iframe in soup.find_all("iframe"):
        if not (iframe.get("title") or "").strip():
            ln, line = find_line_fn(html_lines, iframe)
            issues.append(f"Iframe sin atributo title en línea {ln}: {line}")

    id_count: dict[str, int] = {}
    for tag in soup.find_all(attrs={"id": True}):
        tid = (tag.get("id") or "").strip()
        if tid:
            id_count[tid] = id_count.get(tid, 0) + 1
    for dup in [tid for tid, count in id_count.items() if count > 1][:20]:
        issues.append(f"ID duplicado detectado: #{dup}.")

    _check_assets(
        soup, base_url, html_lines, issues, asset_stats, is_banned_fn, check_url_fn, classify_speed_fn, find_line_fn
    )
    _check_forms_accessibility(soup, html_lines, issues, find_line_fn)

    if not soup.find("link", rel=lambda r: r and ("icon" in r or "shortcut icon" in r)):
        issues.append('Falta favicon (<link rel="icon">).')

    if not soup.find("link", attrs={"rel": "manifest"}):
        recommendations.append('Falta web manifest (<link rel="manifest">). Necesario para PWA.')

    inline_script_chars = sum(len(s.get_text(strip=True)) for s in soup.find_all("script") if not s.get("src"))
    inline_style_chars = sum(len(s.get_text(strip=True)) for s in soup.find_all("style"))
    if inline_script_chars > 500_000:
        recommendations.append(f"JS en línea muy voluminoso ({inline_script_chars // 1024} KB).")
    if inline_style_chars > 200_000:
        recommendations.append(f"CSS en línea muy voluminoso ({inline_style_chars // 1024} KB).")


def _check_assets(
    soup, base_url, html_lines, issues, asset_stats, is_banned_fn, check_url_fn, classify_speed_fn, find_line_fn
):
    base_is_https = base_url.lower().startswith("https://")

    for link in soup.find_all("link"):
        rel = " ".join(link.get("rel", [])).lower()
        href = (link.get("href") or "").strip()
        if "stylesheet" not in rel:
            continue
        ln, line = find_line_fn(html_lines, link)
        if not href:
            issues.append(f"Hoja de estilos <link> sin href en línea {ln}: {line}")
            continue
        full = urljoin(base_url, href)
        if base_is_https and full.lower().startswith("http://"):
            asset_stats["mixed_content"] += 1
            issues.append(f"Contenido mixto CSS: {full} (línea {ln})")
        ok, elapsed_ms, status_code, _ = check_url_fn(full)
        asset_stats["checked"] += 1
        if not ok:
            asset_stats["broken"] += 1
            issues.append(f"CSS inaccesible {full} estado={status_code}")

    for script in soup.find_all("script"):
        src = (script.get("src") or "").strip()
        if not src:
            continue
        ln, line = find_line_fn(html_lines, script)
        full = urljoin(base_url, src)
        if base_is_https and full.lower().startswith("http://"):
            asset_stats["mixed_content"] += 1
            issues.append(f"Contenido mixto JS: {full} (línea {ln})")
        ok, elapsed_ms, status_code, _ = check_url_fn(full)
        asset_stats["checked"] += 1
        if not ok:
            asset_stats["broken"] += 1
            issues.append(f"JS inaccesible {full} estado={status_code}")
        if soup.head and script in soup.head.contents and not script.get("defer") and not script.get("async"):
            issues.append(f"Script bloqueante en <head> sin defer/async: {full} (línea {ln}: {line[:120]})")


def _check_forms_accessibility(soup, html_lines, issues, find_line_fn):
    for field in soup.find_all(["input", "select", "textarea"]):
        if field.name == "input" and (field.get("type") or "").lower() in {"hidden", "submit", "button"}:
            continue
        has_aria = bool((field.get("aria-label") or "").strip())
        fid = (field.get("id") or "").strip()
        has_label = bool(fid and soup.find("label", attrs={"for": fid}))
        if not has_aria and not has_label:
            ln, line = find_line_fn(html_lines, field)
            issues.append(f"Campo de formulario sin label ni aria-label en línea {ln}: {line}")
