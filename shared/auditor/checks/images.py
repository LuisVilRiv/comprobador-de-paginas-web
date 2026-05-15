"""
check_images — Imágenes rotas, alt, lazy-loading, dimensiones y formato.
Extraído de QualityAuditor._check_images.
"""
from __future__ import annotations
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def check_images(
    soup: BeautifulSoup,
    base_url: str,
    html_lines: list[str],
    issues: list[str],
    is_banned_fn,
    check_url_fn,
    classify_speed_fn,
    find_line_fn,
) -> None:
    images = soup.find_all("img")
    if not images:
        issues.append("No hay imágenes en la página; comprobar si es lo esperado.")
        return

    for img in images:
        src = (img.get("src") or "").strip()
        alt = (img.get("alt") or "").strip()
        line_no, line = find_line_fn(html_lines, img)
        location = f"línea aproximada {line_no}: {line}"

        if not src:
            issues.append(f"Imagen sin src en {location}")
            continue
        if not alt:
            issues.append(f"Imagen sin alt (src={src}) en {location}")

        absolute_url = urljoin(base_url, src)
        if is_banned_fn(absolute_url):
            issues.append(f"Imagen no verificada por URL prohibida: {absolute_url} ({location})")
            continue
        if src.startswith("data:"):
            continue

        ok, elapsed_ms, status_code, _ = check_url_fn(absolute_url)
        speed = classify_speed_fn(elapsed_ms)
        if not ok:
            issues.append(
                f"Imagen rota src={absolute_url} estado={status_code} "
                f"tiempo={elapsed_ms}ms ({speed}) en {location}"
            )

        if not img.get("loading"):
            issues.append(f"Imagen sin loading=\"lazy\" (src={src[:80]}) en {location}")
        if not img.get("width") or not img.get("height"):
            issues.append(
                f"Imagen sin width/height explícitos (causa layout shift / CLS): "
                f"src={src[:80]} en {location}"
            )
        ext = src.rsplit(".", 1)[-1].lower() if "." in src else ""
        if ext in ("jpg", "jpeg", "png", "gif", "bmp", "tiff"):
            issues.append(
                f"Imagen en formato heredado ({ext}): considerar WebP/AVIF. src={src[:80]}"
            )
