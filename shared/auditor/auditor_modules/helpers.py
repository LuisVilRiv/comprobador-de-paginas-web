"""
helpers.py — Utilidades internas del auditor de calidad.
"""

import time
from urllib.parse import urlparse

import requests

from config import settings
from config.logging_config import setup_logger

logger = setup_logger(__name__)


def is_banned_url(url: str) -> bool:
    """Verifica si la URL está en la lista de hosts prohibidos (APDI, etc)."""
    if not url:
        return True
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().split(":")[0]  # Quitar puerto si existe

        banned_targets = [h.lower().strip() for h in settings.AUDIT_BANNED_HOSTS]

        for banned in banned_targets:
            # Coincidencia exacta o el host termina en el dominio prohibido (subdominios)
            if host == banned or host.endswith("." + banned):
                return True
            # Si el banned es una IP, coincidencia exacta
            if banned.replace(".", "").isdigit() and host == banned:
                return True

        return False
    except Exception:
        return True


def warm_up_cookies(session: requests.Session, url: str):
    """Realiza una petición HEAD para obtener cookies iniciales y validar acceso."""
    try:
        session.head(url, timeout=settings.REQUEST_TIMEOUT, allow_redirects=True)
    except Exception:
        pass


def close_driver(auditor):
    """Cierra el driver de Selenium si está abierto."""
    if hasattr(auditor, "_driver") and auditor._driver:
        try:
            auditor._driver.quit()
        except Exception:
            pass
        auditor._driver = None


def ensure_non_empty(category: str, issues: list[str]):
    """Asegura que la lista de incidencias no esté vacía."""
    if not issues:
        issues.append("Sin incidencias detectadas en esta categoría.")


def check_url(session, url, timeout=settings.REQUEST_TIMEOUT, include_content=False, method="GET"):
    """Verifica si una URL es accesible y mide el tiempo de respuesta."""
    if is_banned_url(url):
        logger.info("   ↳ [OMITIDO] %s (Bloqueado por política)", url)
        return False, 0, 403, ""  # Prohibido por politica
    try:
        logger.info("   ↳ [HTTP %s] Comprobando: %s", method.upper(), url)
        start = time.perf_counter()
        resp = session.request(method.upper(), url, timeout=timeout, allow_redirects=True)
        elapsed = int((time.perf_counter() - start) * 1000)
        content = resp.text if include_content else ""
        logger.info("     ↳ [RESPUESTA] Estado: %s | Tiempo: %d ms", resp.status_code, elapsed)
        return resp.ok, elapsed, resp.status_code, content
    except Exception as e:
        logger.warning("     ↳ [FALLO DE CONEXIÓN] %s: %s", url, e)
        return False, 0, None, ""


def classify_speed(ms: int) -> str:
    """Clasifica la velocidad de respuesta en ms."""
    if ms < 300:
        return "excelente"
    if ms < 800:
        return "buena"
    if ms < 1500:
        return "mejorable"
    return "lenta"


def find_line(lines: list[str], soup_tag) -> tuple[int, str]:
    """Busca la línea original de un tag de BeautifulSoup en el HTML crudo."""
    try:
        tag_str = str(soup_tag)[:100]
        for i, line in enumerate(lines, 1):
            if tag_str in line:
                return i, line.strip()
    except Exception:
        pass
    return 0, "No encontrada"


def normalize_text(text: str) -> str:
    """Normaliza texto eliminando caracteres especiales y convirtiendo a minúsculas."""
    if not text:
        return ""
    import re

    text = text.lower()
    text = re.sub(r"[^a-z0-9áéíóúñ\s]", "", text)
    return text


def collect_metrics(soup, metadata, security, images, links, buttons, technical, crawl_stats, asset_stats):
    """Compila métricas de la auditoría."""
    return {
        "word_count": len(soup.get_text().split()),
        "links_found": len(soup.find_all("a")),
        "images_found": len(soup.find_all("img")),
        "security_issues_count": len([i for i in security if "Sin incidencias" not in i]),
        "broken_links_count": crawl_stats.get("broken", 0),
        "broken_images_count": asset_stats.get("broken", 0),
        "js_errors_count": len([i for i in technical if "Error de consola JS" in i]),
        **metadata,
    }
