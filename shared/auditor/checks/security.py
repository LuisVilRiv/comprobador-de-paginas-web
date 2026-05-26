"""
check_security — Cabeceras HTTP, HTTPS, SRI y sondeo de rutas de administración.
Extraído de QualityAuditor._check_security y métodos auxiliares de admin probing.
"""

from __future__ import annotations

import socket
import ssl
import time
from datetime import UTC, datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import settings
from shared.auditor.auditor_modules.helpers import attr_to_str

# ── Constantes de clasificación ──────────────────────────────────────────────

_CPANEL_DEEP_PATHS = (
    "/frontend/paper_lantern/index.html",
    "/frontend/jupiter/index.html",
)

_FIREWALL_TITLE_PATTERNS = (
    "just a moment",
    "attention required",
    "bitninja",
    "imunify360",
    "checking your browser",
    "please wait",
    "ddos protection",
)

_FIREWALL_SCRIPT_PATTERNS = (
    "__cf_chl",
    "challenge-platform",
    "turnstile",
    "bitninja.io/challenge",
    "imunify360.com/challenge",
    "captcha",
)

_REQUIRED_HEADERS = {
    "content-security-policy": (
        "Falta cabecera Content-Security-Policy (CSP). Impide inyección de scripts maliciosos (XSS)."
    ),
    "x-frame-options": (
        "Falta cabecera X-Frame-Options. La página puede ser embebida en iframes externos (clickjacking)."
    ),
    "x-content-type-options": (
        "Falta cabecera X-Content-Type-Options. El navegador puede interpretar recursos con MIME incorrecto."
    ),
    "referrer-policy": (
        "Falta cabecera Referrer-Policy. La URL completa puede filtrarse a terceros via cabecera Referer."
    ),
}


# ── Helpers internos ─────────────────────────────────────────────────────────


def _verify_tls(url: str, issues: list[str], timeout: int = 5) -> None:
    """Verifica la validez y expiración del certificado SSL/TLS del sitio web."""
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        return

    hostname = parsed.hostname
    if not hostname:
        return

    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                if cert and "notAfter" in cert:
                    not_after_str = str(cert["notAfter"])
                    try:
                        # Formato: 'May 18 07:19:26 2026 GMT'
                        expire_date = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
                        days_left = (expire_date - datetime.now(UTC)).days

                        if days_left < 0:
                            issues.append(
                                f"El certificado SSL/TLS para {hostname} ha EXPIRADO "
                                f"el {expire_date.strftime('%d/%m/%Y')}."
                            )
                        elif days_left <= 14:
                            issues.append(
                                f"ADVERTENCIA: El certificado SSL/TLS para {hostname} expirará pronto, "
                                f"en {days_left} días ({expire_date.strftime('%d/%m/%Y')})."
                            )
                    except Exception:
                        pass
    except ssl.SSLCertVerificationError as exc:
        issues.append(
            f"Error de verificación SSL/TLS en {hostname}: El certificado no es de confianza "
            f"o no coincide con el nombre de host (Detalle: {exc.reason})."
        )
    except ssl.SSLError as exc:
        issues.append(f"Error de protocolo SSL/TLS al conectar a {hostname}: {str(exc)}.")
    except TimeoutError:
        issues.append(f"Tiempo de espera agotado al verificar el certificado SSL/TLS en {hostname}.")
    except Exception as exc:
        issues.append(f"No se pudo establecer una conexión SSL/TLS segura con {hostname} (Error: {str(exc)}).")


def _normalize_host(host: str) -> str:
    host = host.lower().strip()
    return host[4:] if host.startswith("www.") else host


def _is_banned_url(url: str) -> bool:
    host = _normalize_host(urlparse(url).netloc)
    return host in {_normalize_host(h) for h in settings.AUDIT_BANNED_HOSTS}


def _html_has_firewall_challenge(html_text: str, title: str) -> bool:
    title_l = title.lower()
    html_l = html_text.lower()
    admin_indicators = (
        "cpanel",
        "login",
        "admin",
        "dashboard",
        "backoffice",
        "phpmyadmin",
        "administrator",
        "backend",
        "manage",
        "sesión",
        "sesion",
        "autenticacion",
        "usuario",
        "password",
        "contraseña",
        "acceder",
        "identificarse",
        "wp-login",
    )
    if any(kw in title_l for kw in ("admin", "cpanel", "login", "sesion", "dashboard")):
        return False
    if sum(1 for kw in admin_indicators if kw in html_l) >= 2:
        return False
    return any(p in title_l for p in _FIREWALL_TITLE_PATTERNS) or any(p in html_l for p in _FIREWALL_SCRIPT_PATTERNS)


def _html_has_cpanel_login_signature(html_text: str) -> bool:
    html_l = html_text.lower()
    has_form = "login_form" in html_l
    has_user = 'id="user"' in html_l or 'name="user"' in html_l
    has_pass = 'id="pass"' in html_l or 'name="pass"' in html_l
    has_keywords = "cpanel" in html_l and ("login" in html_l or "sesion" in html_l)
    return (has_form and (has_user or has_pass)) or has_keywords


def _html_has_cpanel_dashboard(html_text: str) -> bool:
    return "#lnkheaderhome" in html_text.lower() or "lnkheaderhome" in html_text.lower()


# ── Función pública ───────────────────────────────────────────────────────────


def check_security(
    html: str,
    soup: BeautifulSoup,
    base_url: str,
    issues: list[str],
    session: requests.Session,
    last_response_headers: dict,
    timeout: int,
    regex_set,
    driver_factory,  # callable() → webdriver | None
) -> None:
    """Ejecuta todas las comprobaciones de seguridad y añade hallazgos a `issues`."""

    if base_url.lower().startswith("http://"):
        issues.append("La URL usa HTTP en lugar de HTTPS. Todo el tráfico viaja sin cifrar.")
    else:
        # Verificación exhaustiva de SSL/TLS
        _verify_tls(base_url, issues, timeout=timeout)

    headers = {k.lower(): v for k, v in last_response_headers.items()}
    for header, message in _REQUIRED_HEADERS.items():
        if header not in headers:
            issues.append(message)

    if base_url.lower().startswith("https://") and "strict-transport-security" not in headers:
        issues.append(
            "Falta Strict-Transport-Security (HSTS). Los navegadores podrían conectar por HTTP en visitas futuras."
        )

    if not headers:
        issues.append(
            "No se pudieron obtener cabeceras HTTP de respuesta "
            "(warm-up fallido o URL prohibida). "
            "Cabeceras de seguridad no verificadas."
        )

    # SRI — Subresource Integrity
    base_host = _normalize_host(urlparse(base_url).netloc)
    sri_missing = []
    for tag in soup.find_all(["script", "link"]):
        if tag.name == "script":
            src = attr_to_str(tag.get("src")).strip()
        else:
            rel = " ".join(attr_to_str(tag.get("rel")).split()).lower()
            if "stylesheet" not in rel:
                continue
            src = attr_to_str(tag.get("href")).strip()
        if not src or not src.startswith("http"):
            continue
        tag_host = _normalize_host(urlparse(src).netloc)
        if tag_host and tag_host != base_host and not tag.get("integrity"):
            sri_missing.append(src[:80])

    if sri_missing:
        if len(sri_missing) > 3:
            issues.append(
                f"Falta atributo integrity (SRI) en {len(sri_missing)} recursos "
                f"externos (ej: {', '.join(sri_missing[:2])}...). "
                "Riesgo de inyección si el CDN es comprometido."
            )
        else:
            for src in sri_missing:
                issues.append(f"Recurso externo sin atributo integrity (SRI): {src}")

    # Datos sensibles
    for label, pattern in regex_set.sensitive_data_regexes:
        label_l = label.lower()
        if any(x in label_l for x in ("email", "teléfono", "telefono", "phone")):
            continue
        for match in pattern.finditer(html):
            snippet = match.group().strip()
            if any(x in snippet.lower() for x in ("undefined", "null", "generic", "sample", "token_here")):
                continue
            if len(snippet) < 6:
                continue
            issues.append(f"[DATO SENSIBLE] {label} detectado en HTML: '{snippet[:60]}...'")
            break

    # Admin probing
    if not _is_banned_url(base_url):
        parsed = urlparse(base_url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        for admin_path in settings.AUDIT_ADMIN_PROBE_PATHS:
            probe_url = base_origin + admin_path
            state, reason, final_url, resp_status = _probe_admin_path(probe_url, session, timeout, driver_factory)
            if state == "protected":
                issues.append(
                    f"Panel de administración en {admin_path} protegido con "
                    f"autenticación ({reason}, url_final={final_url}). OK."
                )
            elif state == "firewall_block":
                issues.append(f"Ruta {admin_path} bloqueada por firewall/WAF ({reason}, url_final={final_url}).")
            elif state == "exposed":
                issues.append(
                    f"CRÍTICO: Panel de administración posiblemente accesible "
                    f"SIN autenticación en {admin_path} "
                    f"({reason}, estado={resp_status}, url_final={final_url}). "
                    "Revisar manualmente y proteger con usuario y contraseña."
                )
            elif state == "unknown":
                issues.append(
                    f"No se pudo confirmar si el panel en {admin_path} está protegido "
                    f"({reason}, url_final={final_url}). Requiere verificación manual."
                )


# ── Admin probing (movido desde QualityAuditor) ───────────────────────────────


def _probe_admin_path(
    url: str,
    session: requests.Session,
    timeout: int,
    driver_factory,
    depth: int = 0,
    max_depth: int = 1,
) -> tuple[str, str, str, int | None]:
    parsed = urlparse(url)
    base_origin = f"{parsed.scheme}://{parsed.netloc}"
    path_l = parsed.path.lower()

    if path_l in ("/cpanel", "/cpanel/"):
        return _probe_cpanel(base_origin, session, timeout, driver_factory)

    try:
        time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        final_url = resp.url or url
        html_text = resp.text or ""
        soup_tmp = BeautifulSoup(html_text, settings.BS4_PARSER)
        title = soup_tmp.title.string.strip() if soup_tmp.title and soup_tmp.title.string else ""

        if resp.status_code in (404, 410):
            return "not_found", f"status={resp.status_code}", final_url, resp.status_code

        if _html_has_firewall_challenge(html_text, title):
            return "firewall_block", f"waf_challenge title='{title[:60]}'", final_url, resp.status_code

        state, reason = _classify_admin_response(url, resp)
        if state == "unknown" or (state == "protected" and "weak" in reason):
            b_state, b_reason, b_final, b_status = _probe_with_browser(url, driver_factory)
            if b_state != "unknown":
                return b_state, b_reason, b_final, b_status

        if state == "protected" and "weak_indicator" in reason:
            return "unknown", f"indicadores_ambiguos_en={final_url}", final_url, resp.status_code

        return state, reason, final_url, resp.status_code

    except requests.RequestException as exc:
        return "not_found", str(exc), url, None


def _probe_cpanel(
    base_origin: str,
    session: requests.Session,
    timeout: int,
    driver_factory,
) -> tuple[str, str, str, int | None]:
    try:
        time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
        resp = session.get(base_origin + "/cpanel", timeout=timeout, allow_redirects=True)
        final_url = resp.url or base_origin + "/cpanel"
        html_text = resp.text or ""
        soup_cp = BeautifulSoup(html_text, settings.BS4_PARSER)
        title = soup_cp.title.string.strip() if soup_cp.title and soup_cp.title.string else ""
        state, reason, f_url, status = _classify_cpanel_response(
            resp, html_text, title, final_url, base_origin, session
        )
        if state != "unknown":
            return state, reason, f_url, status
    except requests.RequestException:
        pass

    for deep_path in _CPANEL_DEEP_PATHS:
        try:
            time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
            resp = session.get(base_origin + deep_path, timeout=timeout, allow_redirects=True)
            final_url = resp.url or base_origin + deep_path
            html_text = resp.text or ""
            soup_cp = BeautifulSoup(html_text, settings.BS4_PARSER)
            title = soup_cp.title.string.strip() if soup_cp.title and soup_cp.title.string else ""
            state, reason, f_url, status = _classify_cpanel_response(
                resp, html_text, title, final_url, base_origin, session
            )
            if state != "unknown":
                return state, reason, f_url, status
        except requests.RequestException:
            continue

    port_host = base_origin.replace("https://", "").replace("http://", "").split("/")[0]

    # Pre-comprobación de socket súper rápida para evitar que Selenium se cuelgue 30s si el puerto está cerrado/bloqueado
    port_open = False
    try:
        with socket.create_connection((port_host, 2083), timeout=1.8):
            port_open = True
    except Exception:
        pass

    if not port_open:
        return "not_found", "cpanel_port_2083_closed_or_filtered", f"https://{port_host}:2083/", None

    return _probe_with_browser(f"https://{port_host}:2083/", driver_factory)


def _classify_cpanel_response(
    resp, html_text: str, title: str, final_url: str, base_origin: str, session
) -> tuple[str, str, str, int | None]:
    status_code = resp.status_code if resp else 0
    if _html_has_firewall_challenge(html_text, title):
        return "firewall_block", f"waf_challenge title='{title[:60]}'", final_url, status_code
    if _html_has_cpanel_dashboard(html_text):
        return "exposed", "cpanel_dashboard_loaded_without_auth", final_url, status_code
    redirected_to_login = "/login" in final_url.lower()
    has_cpsession = any(
        "cpsession" in c.name.lower()
        for c in session.cookies
        if c.domain and urlparse(base_origin).netloc.endswith(c.domain.lstrip("."))
    )
    if redirected_to_login or has_cpsession or _html_has_cpanel_login_signature(html_text):
        return "protected", f"cpanel_auth_confirmed (redir={redirected_to_login})", final_url, status_code
    if status_code in (401, 403):
        return "protected", f"status={status_code}", final_url, status_code
    return "unknown", "inconclusive", final_url, status_code


def _classify_admin_response(probe_url: str, resp) -> tuple[str, str]:
    status = resp.status_code
    final_url = resp.url or probe_url
    final_url_l = final_url.lower()
    text_l = (resp.text or "").lower()

    if status in (401, 403):
        return "protected", f"status={status}"
    if status in (404, 410):
        return "not_found", f"status={status}"
    if status >= 500:
        return "unknown", f"status={status}"

    auth_url_indicators = (
        "login",
        "signin",
        "sign-in",
        "auth",
        "authenticate",
        "wp-login",
        "user/login",
        "account",
        "session",
        "sso",
        "oauth",
    )
    if resp.history and any(ind in final_url_l for ind in auth_url_indicators):
        return "protected", f"redirect_to_auth={final_url}"

    strong_login_indicators = (
        'type="password"',
        'name="password"',
        'id="password"',
        "wp-submit",
        "user_login",
        "csrf",
        "_token",
        "login_form",
    )
    if any(ind in text_l for ind in strong_login_indicators):
        return "protected", "strong_login_form_detected"

    weak_login_indicators = (
        "contraseña",
        "password",
        "iniciar sesión",
        "log in",
        "login",
        "autenticación",
        "acceder",
        "identificarse",
        "usuario",
        "cpanel",
    )
    is_home = final_url_l.rstrip("/") == f"{urlparse(probe_url).scheme}://{urlparse(probe_url).netloc}".lower()
    if any(ind in text_l for ind in weak_login_indicators):
        if is_home:
            return "not_found", "redirected_to_home_with_weak_indicators"
        return "protected", "weak_indicator_detected"

    dashboard_indicators = (
        "dashboard",
        "panel de administración",
        "logout",
        "cerrar sesión",
        "plugins",
        "phpmyadmin",
    )
    if status < 400 and any(ind in text_l for ind in dashboard_indicators):
        return "exposed", "dashboard_indicators_detected"

    if status < 400:
        return "exposed", f"status={status}_without_auth_indicators"

    return "unknown", f"status={status}"


def _probe_with_browser(url: str, driver_factory) -> tuple[str, str, str, int | None]:
    driver = driver_factory()
    if not driver:
        return "unknown", "selenium_not_available", url, None

    orig_timeout = settings.SELENIUM_PAGE_LOAD_TIMEOUT
    try:
        # Timeout ultra-rápido de 5 segundos para sondeos del navegador
        try:
            driver.set_page_load_timeout(5)
        except Exception:
            pass

        time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
        driver.get(url)
        time.sleep(1)
        final_url = driver.current_url
        html_text = driver.page_source or ""
        title = driver.title or ""

        if "cpanel" in url.lower() or ":208" in url:

            class _FakeSession:
                cookies: list = []

            state, reason, f_url, status = _classify_cpanel_response(
                None, html_text, title, final_url, url, _FakeSession()
            )
            return state, f"browser_{reason}", f_url, status

        class MockResponse:
            def __init__(self, text, url):
                self.text = text
                self.url = url
                self.status_code = 200
                self.history = []

        state, reason = _classify_admin_response(url, MockResponse(html_text, final_url))
        return state, f"browser_{reason}", final_url, 200
    except Exception as exc:
        return "unknown", f"browser_error={str(exc)[:50]}", url, None
    finally:
        # Restaurar el timeout original del pool de Selenium
        try:
            driver.set_page_load_timeout(orig_timeout)
        except Exception:
            pass
