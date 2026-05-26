"""
check_buttons — Botones sin texto, formularios con action inválido.
Extraído de QualityAuditor._check_buttons.
"""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from shared.auditor.auditor_modules.helpers import attr_to_str


def check_buttons(
    soup: BeautifulSoup,
    base_url: str,
    html_lines: list[str],
    issues: list[str],
    is_banned_fn,
    check_url_fn,
    classify_speed_fn,
    find_line_fn,
    blocked_admin_segments: tuple,
) -> None:
    buttons = soup.find_all(["button", "input"])
    forms = soup.find_all("form")

    if not buttons:
        issues.append("No hay botones detectables en el HTML estático.")

    for btn in buttons:
        if btn.name == "input" and attr_to_str(btn.get("type")).lower() not in {"submit", "button"}:
            continue
        ln, line = find_line_fn(html_lines, btn)
        text = btn.get_text(" ", strip=True) if isinstance(btn, Tag) else ""
        if not text:
            text = attr_to_str(btn.get("value")) or "(sin texto)"
        if not text or text == "(sin texto)":
            issues.append(f"Botón sin texto visible en línea aproximada {ln}: {line}")

    for form in forms:
        action = attr_to_str(form.get("action")).strip()
        method = attr_to_str(form.get("method")) or "get"
        method = method.lower()
        ln, line = find_line_fn(html_lines, form)
        if not action:
            issues.append(f"Formulario sin action en línea aproximada {ln}: {line}")
            continue

        target = urljoin(base_url, action)
        if is_banned_fn(target):
            issues.append(f"Formulario no probado por URL prohibida: {target}")
            continue
        if any(seg in target.lower() for seg in blocked_admin_segments):
            issues.append(f"Formulario apunta a una ruta prohibida ({target}) en línea {ln}: {line}")
            continue

        ok, elapsed_ms, status_code, _ = check_url_fn(target, method=method)
        speed = classify_speed_fn(elapsed_ms)
        if not ok:
            issues.append(
                f"Fallo al probar el action del formulario {target} "
                f"método={method.upper()} estado={status_code} tiempo={elapsed_ms}ms ({speed})"
            )
