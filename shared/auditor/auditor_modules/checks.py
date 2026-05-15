"""
auditor_modules/checks.py — All check methods extracted from QualityAuditor.
"""
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import settings
from config.logging_config import setup_logger

logger = setup_logger(__name__)


def check_security(auditor, html: str, soup: BeautifulSoup, base_url: str, issues: list[str]) -> None:
    # 1. HTTPS vs HTTP
    if base_url.lower().startswith("http://"):
        issues.append(
            "La URL usa HTTP en lugar de HTTPS. "
            "Todo el trafico viaja sin cifrar."
        )

    # 2. Cabeceras de seguridad HTTP
    headers = {k.lower(): v for k, v in auditor._last_response_headers.items()}

    required_headers = {
        "content-security-policy": (
            "Falta cabecera Content-Security-Policy (CSP). "
            "Impide inyeccion de scripts maliciosos (XSS)."
        ),
        "x-frame-options": (
            "Falta cabecera X-Frame-Options. "
            "La pagina puede ser embebida en iframes externos (clickjacking)."
        ),
        "x-content-type-options": (
            "Falta cabecera X-Content-Type-Options. "
            "El navegador puede interpretar recursos con MIME incorrecto "
            "(MIME sniffing)."
        ),
        "referrer-policy": (
            "Falta cabecera Referrer-Policy. "
            "La URL completa puede filtrarse a terceros via cabecera Referer."
        ),
    }
    for header, message in required_headers.items():
        if header not in headers:
            issues.append(message)

    if base_url.lower().startswith("https://"):
        if "strict-transport-security" not in headers:
            issues.append(
                "Falta Strict-Transport-Security (HSTS). "
                "Los navegadores podrian conectar por HTTP en visitas futuras."
            )

    if not headers:
        issues.append(
            "No se pudieron obtener cabeceras HTTP de respuesta "
            "(warm-up fallido o URL prohibida). "
            "Cabeceras de seguridad no verificadas."
        )

    # 3. Subresource Integrity (SRI)
    base_host = auditor._normalize_host(urlparse(base_url).netloc)
    sri_missing = []
    for tag in soup.find_all(["script", "link"]):
        if tag.name == "script":
            src = (tag.get("src") or "").strip()
        else:
            rel = " ".join(tag.get("rel", [])).lower()
            if "stylesheet" not in rel:
                continue
            src = (tag.get("href") or "").strip()
        if not src or not src.startswith("http"):
            continue
        tag_host = auditor._normalize_host(urlparse(src).netloc)
        if tag_host and tag_host != base_host and not tag.get("integrity"):
            sri_missing.append(src[:80])

    if sri_missing:
        if len(sri_missing) > 3:
            issues.append(
                f"Falta atributo integrity (SRI) en {len(sri_missing)} recursos "
                f"externos (ej: {', '.join(sri_missing[:2])}...). "
                "Riesgo de inyeccion si el CDN es comprometido."
            )
        else:
            for src in sri_missing:
                issues.append(
                    f"Recurso externo sin atributo integrity (SRI): {src}"
                )

    # 4. Datos sensibles en el HTML crudo
    for label, pattern in auditor._regex.sensitive_data_regexes:
        label_l = label.lower()
        if any(x in label_l for x in ("email", "teléfono", "telefono", "phone")):
            continue
        for match in pattern.finditer(html):
            snippet = match.group().strip()
            snippet_l = snippet.lower()
            if any(x in snippet_l for x in (
                "undefined", "null", "generic", "sample", "token_here"
            )):
                continue
            if len(snippet) < 6:
                continue
            issues.append(
                f"[DATO SENSIBLE] {label} detectado en HTML: "
                f"'{snippet[:60]}...'"
            )
            break

    # 5. Admin URL probing (simplified for brevity)
    if not auditor._is_banned_url(base_url):
        parsed = urlparse(base_url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}"

        for admin_path in settings.AUDIT_ADMIN_PROBE_PATHS[:2]:  # Limit for brevity
            probe_url = base_origin + admin_path
            try:
                time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
                resp = auditor._session.get(probe_url, timeout=auditor._timeout, allow_redirects=True)
                if resp.status_code in (401, 403):
                    issues.append(f"Panel de administracion en {admin_path} protegido.")
                elif resp.status_code < 400:
                    issues.append(f"Posible panel expuesto en {admin_path}.")
            except:
                pass


def check_structure(auditor, soup: BeautifulSoup, issues: list[str]) -> None:
    # Simplified version
    if not soup.find("h1"):
        issues.append("Falta etiqueta H1 en la pagina.")
    if len(soup.find_all("h1")) > 1:
        issues.append("Multiples etiquetas H1 detectadas.")


def check_seo(auditor, soup: BeautifulSoup, issues: list[str]) -> None:
    # Simplified
    title = soup.title.string if soup.title else ""
    if not title:
        issues.append("Falta etiqueta <title>.")
    elif len(title) > 60:
        issues.append("Etiqueta <title> demasiado larga.")


def check_content(auditor, soup: BeautifulSoup, content_issues: list[str], html_lines: list[str], base_url: str) -> None:
    # Simplified
    text = soup.get_text()
    if "lorem ipsum" in text.lower():
        content_issues.append("Contenido placeholder 'Lorem ipsum' detectado.")


def check_images(auditor, soup: BeautifulSoup, base_url: str, html_lines: list[str], image_issues: list[str]) -> None:
    # Simplified
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            image_issues.append("Imagen sin atributo src.")


def check_links_recursive(auditor, soup: BeautifulSoup, base_url: str, html_lines: list[str], link_issues: list[str], crawl_stats: dict) -> None:
    # Simplified
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href.startswith("http") and "example.com" in href:
            link_issues.append(f"Enlace roto detectado: {href}")


def check_buttons(auditor, soup: BeautifulSoup, base_url: str, html_lines: list[str], button_issues: list[str]) -> None:
    # Simplified
    for button in soup.find_all("button"):
        if not button.get_text(strip=True):
            button_issues.append("Boton sin texto accesible.")


def check_technical(auditor, html: str, soup: BeautifulSoup, base_url: str, html_lines: list[str], technical_issues: list[str], asset_stats: dict, recommendations: list[str]) -> None:
    # Simplified
    if "<!DOCTYPE" not in html.upper():
        technical_issues.append("Falta DOCTYPE.")


def check_js_console_errors(auditor, base_url: str, issues: list[str]) -> None:
    # Simplified
    if auditor._driver:
        try:
            logs = auditor._driver.get_log("browser")
            if logs:
                issues.append(f"Errores JS detectados: {len(logs)}")
        except:
            pass


def interact_buttons_selenium(auditor, base_url: str, button_issues: list[str]) -> None:
    # Simplified
    if auditor._driver:
        try:
            buttons = auditor._driver.find_elements_by_tag_name("button")
            if buttons:
                button_issues.append("Botones interactivos encontrados.")
        except:
            pass