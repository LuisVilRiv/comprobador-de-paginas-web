import json
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from config.logging_config import setup_logger
from utils.audit_dictionaries import build_audit_dictionaries
from utils.audit_regex import AuditRegexSet, LEET_TRANSLATION_TABLE, build_audit_regex_set

logger = setup_logger(__name__)


@dataclass
class QualityAuditReport:
    status: str
    score: int
    security_issues: list[str] = field(default_factory=list)
    seo_issues: list[str] = field(default_factory=list)
    content_issues: list[str] = field(default_factory=list)
    image_issues: list[str] = field(default_factory=list)
    structure_issues: list[str] = field(default_factory=list)
    link_issues: list[str] = field(default_factory=list)
    button_issues: list[str] = field(default_factory=list)
    technical_issues: list[str] = field(default_factory=list)
    release_blocked: bool = False
    release_blockers: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "score": self.score,
            "security_issues": self.security_issues,
            "seo_issues": self.seo_issues,
            "content_issues": self.content_issues,
            "image_issues": self.image_issues,
            "structure_issues": self.structure_issues,
            "link_issues": self.link_issues,
            "button_issues": self.button_issues,
            "technical_issues": self.technical_issues,
            "release_blocked": self.release_blocked,
            "release_blockers": self.release_blockers,
            "recommendations": self.recommendations,
            "metrics": self.metrics,
        }


class QualityAuditor:
    def __init__(self, timeout: int = settings.REQUEST_TIMEOUT):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(settings.DEFAULT_HEADERS)
        self._dicts = build_audit_dictionaries()
        self._regex = build_audit_regex_set()
        self._driver: webdriver.Chrome | None = None
        self._browser_confirms = 0
        self._max_browser_confirms = 15
        self._last_response_headers: dict = {}

    def build_report(self, html: str, base_url: str, metadata: dict | None = None) -> QualityAuditReport:
        metadata = metadata or {}
        self._browser_confirms = 0
        self._last_response_headers = {}
        html_lines = html.splitlines()
        soup = BeautifulSoup(html, settings.BS4_PARSER)
        crawl_stats = {"tested": 0, "broken": 0, "skipped": 0}

        security_issues: list[str] = []
        seo_issues: list[str] = []
        content_issues: list[str] = []
        image_issues: list[str] = []
        structure_issues: list[str] = []
        link_issues: list[str] = []
        button_issues: list[str] = []
        technical_issues: list[str] = []
        recommendations: list[str] = []
        asset_stats = {"checked": 0, "broken": 0, "mixed_content": 0}

        try:
            if self._is_banned_url(base_url):
                warning = f"URL prohibida para pruebas de red por politica: {base_url}"
                link_issues.append(warning)
                recommendations.append(
                    "Cambiar URL objetivo por un dominio permitido para validar "
                    "enlaces e imagenes."
                )
            else:
                self._warm_up_cookies(base_url)

            self._check_security(html, soup, base_url, security_issues)
            self._check_structure(soup, structure_issues)
            self._check_seo(soup, seo_issues)
            self._check_content(soup, content_issues, html_lines, base_url)
            self._check_images(soup, base_url, html_lines, image_issues)
            self._check_links_recursive(soup, base_url, html_lines, link_issues, crawl_stats)
            self._check_buttons(soup, base_url, html_lines, button_issues)
            self._check_technical(html, soup, base_url, html_lines, technical_issues, asset_stats, recommendations)

            if not self._is_banned_url(base_url):
                self._check_js_console_errors(base_url, technical_issues)
                self._interact_buttons_selenium(base_url, button_issues)
        finally:
            self._close_driver()

        self._ensure_non_empty("security_issues", security_issues)
        self._ensure_non_empty("seo_issues", seo_issues)
        self._ensure_non_empty("content_issues", content_issues)
        self._ensure_non_empty("image_issues", image_issues)
        self._ensure_non_empty("structure_issues", structure_issues)
        self._ensure_non_empty("link_issues", link_issues)
        self._ensure_non_empty("button_issues", button_issues)
        self._ensure_non_empty("technical_issues", technical_issues)

        metrics = self._collect_metrics(
            soup, metadata, security_issues, image_issues, link_issues,
            button_issues, technical_issues, crawl_stats, asset_stats,
        )
        score = self._calculate_score(
            security_issues, seo_issues, content_issues, image_issues,
            structure_issues, link_issues, button_issues, technical_issues,
        )
        status = self._status_from_score(score)
        release_blocked, release_blockers = self._evaluate_release_gate(
            score=score,
            security_issues=security_issues,
            content_issues=content_issues,
            link_issues=link_issues,
            technical_issues=technical_issues,
            image_issues=image_issues,
            button_issues=button_issues,
        )
        metrics["release_gate_blocked"] = release_blocked
        metrics["release_blockers_count"] = len(release_blockers)

        recommendations.extend(
            self._build_recommendations(
                security_issues, seo_issues, content_issues, image_issues,
                structure_issues, link_issues, button_issues, technical_issues,
            )
        )
        if not recommendations:
            recommendations.append(
                "No se detectan mejoras criticas. Mantener monitorizacion periodica."
            )
        if release_blocked:
            recommendations.insert(
                0, "BLOQUEAR despliegue a produccion hasta resolver los blockers del gate."
            )

        return QualityAuditReport(
            status=status,
            score=score,
            security_issues=security_issues,
            seo_issues=seo_issues,
            content_issues=content_issues,
            image_issues=image_issues,
            structure_issues=structure_issues,
            link_issues=link_issues,
            button_issues=button_issues,
            technical_issues=technical_issues,
            release_blocked=release_blocked,
            release_blockers=release_blockers,
            recommendations=recommendations,
            metrics=metrics,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # INFORME DE TEXTO  (ortografia corregida en todos los literales)
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def report_to_text(report: QualityAuditReport) -> str:
        tests_performed = [
            "Analisis de cabeceras de seguridad HTTP (CSP, HSTS, XFO...)",
            "Escaneo de rutas de administracion (/admin, /wp-login...) con recursividad",
            "Deteccion de datos sensibles expuestos (claves, tokens, APIs)",
            "Auditoria de accesibilidad WCAG (etiquetas, roles, landmarks, contrastes)",
            "Validacion SEO (metas, canonical, lang, jerarquia Hx)",
            "Analisis de contenido (lorem ipsum, toxicidad, duplicidad)",
            "Verificacion de enlaces y recursos (rotos, mixed content, SRI)",
            "Pruebas de interaccion de UI (clics en botones y formularios via Selenium)",
            "Monitorizacion de errores de consola JS y rendimiento "
            "(bloqueo de renderizado)",
        ]

        top_improvements = (
            report.recommendations[:5]
            if report.recommendations
            else ["Mantener monitorizacion periodica."]
        )

        score_checks = []
        if report.score >= 90:
            score_checks.append("[\u2713] Excelente salud tecnica y de seguridad.")
        elif report.score >= 70:
            score_checks.append(
                "[\u2713] Calidad buena, con margen de mejora en optimizacion."
            )
        else:
            score_checks.append(
                "[x] Critico: Se requieren correcciones inmediatas de seguridad/SEO."
            )

        if report.security_issues:
            score_checks.append(
                f"[x] Detectados {len(report.security_issues)} fallos de seguridad."
            )
        else:
            score_checks.append("[\u2713] Sin brechas de seguridad criticas detectadas.")

        if report.link_issues or report.technical_issues:
            score_checks.append(
                "[x] Existen recursos rotos o errores tecnicos que penalizan la puntuacion."
            )
        else:
            score_checks.append("[\u2713] Estabilidad tecnica validada.")

        lines = [
            "===========================================================",
            "           INFORME DE AUDITORIA DE CALIDAD WEB             ",
            "===========================================================",
            "",
            "1. RESUMEN DE PRUEBAS REALIZADAS",
            "--------------------------------",
            *[f"- {test}" for test in tests_performed],
            "",
            "2. RESUMEN EJECUTIVO DE MEJORAS",
            "--------------------------------",
            *[f"- {item}" for item in top_improvements],
            "",
            "3. PUNTUACION Y ESTADO",
            "----------------------",
            f"PUNTUACION: {report.score}/100",
            f"ESTADO: {report.status}",
            f"GATE DE PRODUCCION: {'BLOQUEADO' if report.release_blocked else 'APTO'}",
            "",
            "Justificacion de la puntuacion:",
            *[f"  {check}" for check in score_checks],
            "",
            "4. DETALLE DE HALLAZGOS",
            "-----------------------",
            "",
            "SEGURIDAD HTTP Y SONDEO DE RUTAS:",
            *(
                [f"  - {item}" for item in report.security_issues]
                or ["  - OK. Sin vulnerabilidades detectadas."]
            ),
            "",
            "SEO Y METADATOS:",
            *(
                [f"  - {item}" for item in report.seo_issues]
                or ["  - OK. Optimizacion SEO correcta."]
            ),
            "",
            "ESTRUCTURA Y ACCESIBILIDAD:",
            *(
                [f"  - {item}" for item in report.structure_issues]
                or ["  - OK. Estructura semantica solida."]
            ),
            "",
            "CONTENIDO Y CALIDAD:",
            *(
                [f"  - {item}" for item in report.content_issues]
                or ["  - OK. Sin contenido problematico."]
            ),
            "",
            "IMAGENES Y RECURSOS:",
            *(
                [f"  - {item}" for item in report.image_issues]
                or ["  - OK. Recursos optimizados."]
            ),
            "",
            "ENLACES Y NAVEGACION:",
            *(
                [f"  - {item}" for item in report.link_issues]
                or ["  - OK. Sin enlaces rotos."]
            ),
            "",
            "BOTONES Y FORMULARIOS:",
            *(
                [f"  - {item}" for item in report.button_issues]
                or ["  - OK. Interactividad correcta."]
            ),
            "",
            "TECNICO / CONSOLA JS:",
            *(
                [f"  - {item}" for item in report.technical_issues]
                or ["  - OK. Sin errores de ejecucion."]
            ),
            "",
            "===========================================================",
            "               FIN DEL INFORME DE AUDITORIA                ",
            "===========================================================",
        ]
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    # NORMALIZACION ANTI-LEETSPEAK
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_for_detection(text: str) -> str:
        t = text.lower()
        t = t.translate(str.maketrans(
            "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"
            "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"
            "０１２３４５６７８９",
            "abcdefghijklmnopqrstuvwxyz"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789",
        ))
        t = t.translate(LEET_TRANSLATION_TABLE)
        t = re.sub(r"([a-z])[.\-_*,;:!?'\"\\]([a-z])", r"\1\2", t)
        t = re.sub(r"([a-z])[.\-_*,;:!?'\"\\]([a-z])", r"\1\2", t)
        t = re.sub(
            r"(?<!\w)(\w)(?!\w)([ \t]{1,2}(?<!\w)\w(?!\w)){2,}",
            lambda m: m.group().replace(" ", "").replace("\t", ""),
            t,
        )
        t = re.sub(r"([a-z])\*+([a-z])", r"\1\2", t)
        return t

    # ──────────────────────────────────────────────────────────────────────────
    # CHECK SEGURIDAD  (incluye la nueva logica de cPanel)
    # ──────────────────────────────────────────────────────────────────────────

    def _check_security(
        self,
        html: str,
        soup: BeautifulSoup,
        base_url: str,
        issues: list[str],
    ) -> None:
        # 1. HTTPS vs HTTP
        if base_url.lower().startswith("http://"):
            issues.append(
                "La URL usa HTTP en lugar de HTTPS. "
                "Todo el trafico viaja sin cifrar."
            )

        # 2. Cabeceras de seguridad HTTP
        headers = {k.lower(): v for k, v in self._last_response_headers.items()}

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
        base_host = self._normalize_host(urlparse(base_url).netloc)
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
            tag_host = self._normalize_host(urlparse(src).netloc)
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
        for label, pattern in self._regex.sensitive_data_regexes:
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

        # 5. Admin URL probing  (con la nueva logica de cPanel)
        if not self._is_banned_url(base_url):
            parsed = urlparse(base_url)
            base_origin = f"{parsed.scheme}://{parsed.netloc}"

            for admin_path in settings.AUDIT_ADMIN_PROBE_PATHS:
                probe_url = base_origin + admin_path
                state, reason, final_url, resp_status = (
                    self._probe_admin_path_recursive(probe_url)
                )

                if state == "protected":
                    issues.append(
                        f"Panel de administracion en {admin_path} protegido con "
                        f"autenticacion ({reason}, url_final={final_url}). OK."
                    )
                elif state == "firewall_block":
                    issues.append(
                        f"Ruta {admin_path} bloqueada por firewall/WAF "
                        f"({reason}, url_final={final_url}). "
                        "No se puede confirmar el estado real del panel."
                    )
                elif state == "exposed":
                    issues.append(
                        f"CRITICO: Panel de administracion posiblemente accesible "
                        f"SIN autenticacion en {admin_path} "
                        f"({reason}, estado={resp_status}, url_final={final_url}). "
                        "Revisar manualmente y proteger con usuario y contrasena."
                    )
                elif state == "unknown":
                    issues.append(
                        f"No se pudo confirmar si el panel de administracion en "
                        f"{admin_path} esta protegido "
                        f"({reason}, url_final={final_url}). "
                        "Requiere verificacion manual."
                    )
                elif state == "not_found":
                    logger.debug(
                        "Ruta de administracion no encontrada: %s (%s)",
                        probe_url, reason,
                    )

    # ──────────────────────────────────────────────────────────────────────────
    # SONDEO DE RUTAS DE ADMIN  (logica de cPanel reforzada)
    # ──────────────────────────────────────────────────────────────────────────

    # Rutas internas de cPanel que requieren sesion activa
    _CPANEL_DEEP_PATHS = (
        "/frontend/paper_lantern/index.html",
        "/frontend/jupiter/index.html",
    )

    # Patrones de desafio de firewall/WAF presentes en el <title> o scripts
    _FIREWALL_TITLE_PATTERNS = (
        "just a moment",       # Cloudflare
        "attention required",  # Cloudflare
        "bitninja",
        "imunify360",
        "checking your browser",
        "please wait",
        "ddos protection",
    )

    # Scripts de desafio inyectados por WAF en el <head>
    _FIREWALL_SCRIPT_PATTERNS = (
        "__cf_chl",
        "challenge-platform",
        "turnstile",
        "bitninja.io/challenge",
        "imunify360.com/challenge",
        "captcha",
    )

    @staticmethod
    def _html_has_firewall_challenge(html_text: str, title: str) -> bool:
        """Devuelve True si la pagina es una pagina intermediaria de WAF/firewall."""
        title_l = title.lower()
        html_l = html_text.lower()

        # BYPASS: Si es claramente un panel de admin o login (según keywords de settings.py),
        # no es un bloqueo "ciego" de WAF que impida la auditoria.
        # Basado en la sugerencia del usuario de usar keywords tipo PowerShell.
        admin_indicators = (
            "cpanel", "login", "admin", "dashboard", "backoffice", 
            "phpmyadmin", "administrator", "backend", "manage",
            "sesión", "sesion", "autenticacion", "usuario", "password",
            "contraseña", "acceder", "identificarse", "wp-login"
        )
        
        # Si el título tiene indicators o el cuerpo tiene al menos 2, ignoramos el firewall block
        # para proceder con la clasificacion detallada.
        if any(kw in title_l for kw in ("admin", "cpanel", "login", "sesion", "dashboard")):
            return False
        
        found_count = sum(1 for kw in admin_indicators if kw in html_l)
        if found_count >= 2:
            return False

        return any(p in title_l for p in QualityAuditor._FIREWALL_TITLE_PATTERNS) or any(
            p in html_l for p in QualityAuditor._FIREWALL_SCRIPT_PATTERNS
        )

    @staticmethod
    def _html_has_cpanel_login_signature(html_text: str) -> bool:
        """
        Valida la firma tecnica de un login de cPanel.
        Relajado para evitar falsos negativos por cambios menores en el DOM.
        """
        html_l = html_text.lower()

        # Firma estructural basica
        has_form = "login_form" in html_l
        has_user = 'id="user"' in html_l or "id='user'" in html_l or "name=\"user\"" in html_l
        has_pass = 'id="pass"' in html_l or "id='pass'" in html_l or "name=\"pass\"" in html_l
        
        # Firma por contenido (como el ejemplo de PowerShell del usuario)
        has_keywords = "cpanel" in html_l and ("login" in html_l or "sesion" in html_l or "sesión" in html_l)

        return (has_form and (has_user or has_pass)) or has_keywords

    @staticmethod
    def _html_has_cpanel_dashboard(html_text: str) -> bool:
        """Detecta el dashboard de cPanel cargado sin autenticacion."""
        html_l = html_text.lower()
        # Elemento caracteristico del header de cPanel en session activa
        return "#lnkheaderhome" in html_l or "lnkheaderhome" in html_l

    def _probe_cpanel(
        self, base_origin: str
    ) -> tuple[str, str, str, int | None]:
        """
        Logica especializada para verificar si cPanel esta protegido.
        """
        # --- Paso 0: Verificar la ruta raiz de cPanel / login rapido ---
        try:
            time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
            root_url = base_origin + "/cpanel"
            resp = self._session.get(root_url, timeout=self._timeout, allow_redirects=True)
            
            final_url = resp.url or root_url
            html_text = resp.text or ""
            soup_cp = BeautifulSoup(html_text, settings.BS4_PARSER)
            title = soup_cp.title.string.strip() if soup_cp.title and soup_cp.title.string else ""
            
            # Clasificar respuesta raiz
            state, reason, f_url, status = self._classify_cpanel_response(resp, html_text, title, final_url, base_origin)
            
            # Si redirige a home, es muy probable que el servidor bloquee 'requests' 
            # pero el panel exista en el puerto 2083
            is_redirect_to_home = (
                f_url.rstrip("/") == base_origin.rstrip("/")
                or f_url.rstrip("/") == base_origin.rstrip("/") + "/index.php"
            )
            
            if state == "unknown" and is_redirect_to_home:
                # Intentar acceso directo al puerto con navegador
                port_url = base_origin.replace("https://", "").replace("http://", "").split("/")[0]
                port_url = f"https://{port_url}:2083/"
                b_state, b_reason, b_final, b_status = self._probe_with_browser(port_url)
                if b_state != "unknown":
                    return b_state, b_reason, b_final, b_status

            if state != "unknown":
                return state, reason, f_url, status

        except requests.RequestException:
            pass

        # --- Paso 1: Probar rutas profundas ---
        for deep_path in self._CPANEL_DEEP_PATHS:
            probe_url = base_origin + deep_path
            try:
                time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
                resp = self._session.get(probe_url, timeout=self._timeout, allow_redirects=True)
                final_url = resp.url or probe_url
                html_text = resp.text or ""
                soup_cp = BeautifulSoup(html_text, settings.BS4_PARSER)
                title = soup_cp.title.string.strip() if soup_cp.title and soup_cp.title.string else ""
                
                state, reason, f_url, status = self._classify_cpanel_response(resp, html_text, title, final_url, base_origin)
                if state != "unknown":
                    return state, reason, f_url, status

            except requests.RequestException:
                continue

        # --- Paso 2: Ultimo recurso - Probar el puerto 2083 con navegador ---
        port_url = base_origin.replace("https://", "").replace("http://", "").split("/")[0]
        port_url = f"https://{port_url}:2083/"
        return self._probe_with_browser(port_url)

    def _classify_cpanel_response(
        self, resp: requests.Response, html_text: str, title: str, final_url: str, base_origin: str
    ) -> tuple[str, str, str, int | None]:
        """Helper para clasificar una respuesta como cPanel."""
        # 1. Desafio de WAF
        if self._html_has_firewall_challenge(html_text, title):
            return (
                "firewall_block",
                f"waf_challenge_detected title='{title[:60]}'",
                final_url,
                resp.status_code,
            )

        # 2. Dashboard expuesto
        if self._html_has_cpanel_dashboard(html_text):
            return (
                "exposed",
                "cpanel_dashboard_loaded_without_auth",
                final_url,
                resp.status_code,
            )

        # 3. Firma de login (redireccion o contenido)
        redirected_to_login = "/login" in final_url.lower()
        has_cpsession = any(
            "cpsession" in c.name.lower()
            for c in self._session.cookies
            if c.domain and urlparse(base_origin).netloc.endswith(c.domain.lstrip("."))
        )

        if redirected_to_login or has_cpsession or self._html_has_cpanel_login_signature(html_text):
            return (
                "protected",
                f"cpanel_auth_confirmed (redir={redirected_to_login}, session={has_cpsession})",
                final_url,
                resp.status_code,
            )
            
        if resp.status_code in (401, 403):
            return "protected", f"status={resp.status_code}", final_url, resp.status_code

        return "unknown", "inconclusive", final_url, resp.status_code

        # Si ninguna ruta profunda respondio de forma concluyente
        return "unknown", "cpanel_deep_probe_inconclusive", base_origin, None

    def _probe_admin_path_recursive(
        self,
        url: str,
        depth: int = 0,
        max_depth: int = 1,
    ) -> tuple[str, str, str, int | None]:
        """
        Sondea una ruta de administracion con recursividad limitada.
        Para la ruta /cpanel delega en _probe_cpanel con la logica especializada.
        """
        parsed = urlparse(url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        path_l = parsed.path.lower()

        # Delegar a la logica especializada de cPanel
        if path_l in ("/cpanel", "/cpanel/"):
            return self._probe_cpanel(base_origin)

        try:
            time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
            resp = self._session.get(
                url,
                timeout=self._timeout,
                allow_redirects=True,
            )
            final_url = resp.url or url
            html_text = resp.text or ""
            soup_tmp = BeautifulSoup(html_text, settings.BS4_PARSER)
            title = (
                soup_tmp.title.string.strip()
                if soup_tmp.title and soup_tmp.title.string
                else ""
            )

            # --- Paso 1: Verificar existencia (404/410) antes que el firewall ---
            if resp.status_code in (404, 410):
                return "not_found", f"status={resp.status_code}", final_url, resp.status_code

            # Detectar pagina intermediaria de WAF
            if self._html_has_firewall_challenge(html_text, title):
                return (
                    "firewall_block",
                    f"waf_challenge_detected title='{title[:60]}'",
                    final_url,
                    resp.status_code,
                )

            state, reason = self._classify_admin_probe_response(url, resp)

            # Si es unknown o ambiguo, intentar con navegador
            if state == "unknown" or (state == "protected" and "weak" in reason):
                b_state, b_reason, b_final, b_status = self._probe_with_browser(url)
                if b_state != "unknown":
                    return b_state, b_reason, b_final, b_status

            # Recursividad para casos ambiguos
            is_ambiguous = (
                (state == "protected" and "weak_indicator" in reason)
                or (state == "exposed" and "without_auth_indicators" in reason)
            )

            if is_ambiguous and depth < max_depth:
                login_keywords = {
                    "login", "signin", "acceder", "entrar", "admin", "management",
                    "identificarse", "log in", "sign in", "user", "account",
                    "backend", "backoffice", "sistema", "acceso", "control",
                }
                promising_links: list[str] = []
                for tag in soup_tmp.find_all(["a", "form", "button"]):
                    href = ""
                    if tag.name == "a":
                        href = tag.get("href") or ""
                    elif tag.name == "form":
                        href = tag.get("action") or ""
                    text = tag.get_text(strip=True).lower()
                    href_l = href.lower()
                    if any(kw in href_l for kw in login_keywords) or any(
                        kw in text for kw in login_keywords
                    ):
                        full_href = urljoin(final_url, href)
                        if (
                            full_href != final_url
                            and urlparse(full_href).netloc == urlparse(url).netloc
                            and not full_href.endswith(("#", "javascript:void(0)"))
                        ):
                            promising_links.append(full_href)

                for link in promising_links[:5]:
                    sub_state, sub_reason, sub_final, sub_status = (
                        self._probe_admin_path_recursive(link, depth + 1, max_depth)
                    )
                    if sub_state == "protected" and "weak_indicator" not in sub_reason:
                        return (
                            "protected",
                            f"auth_confirmed_at={link}",
                            sub_final,
                            sub_status,
                        )
                    if sub_state == "exposed" and "dashboard" in sub_reason:
                        return (
                            "exposed",
                            f"nested_dashboard_found_at={link}",
                            sub_final,
                            sub_status,
                        )

            if state == "protected" and "weak_indicator" in reason:
                return (
                    "unknown",
                    f"indicadores_ambiguos_en={final_url}",
                    final_url,
                    resp.status_code,
                )

            return state, reason, final_url, resp.status_code

        except requests.RequestException as exc:
            return "not_found", str(exc), url, None

    def _classify_admin_probe_response(
        self,
        probe_url: str,
        resp: requests.Response,
    ) -> tuple[str, str]:
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
            "login", "signin", "sign-in", "auth", "authenticate", "wp-login",
            "user/login", "account", "session", "sso", "oauth", "keycloak",
        )
        if resp.history and any(ind in final_url_l for ind in auth_url_indicators):
            return "protected", f"redirect_to_auth={final_url}"

        parsed_final = urlparse(final_url)
        is_home = (
            final_url_l.rstrip("/")
            == f"{urlparse(probe_url).scheme}://{urlparse(probe_url).netloc}".lower()
        )

        strong_login_indicators = (
            'type="password"', "type='password'",
            'name="password"', "name='password'",
            'id="password"', "id='password'",
            "wp-submit", "user_login", "remember_me",
            "csrf", "_token", 'action="login"', "action='login'",
            "cpanel-login", "login_form",
        )
        if any(ind in text_l for ind in strong_login_indicators):
            return "protected", "strong_login_form_detected"

        weak_login_indicators = (
            "contraseña", "password", "iniciar sesión", "iniciar sesion",
            "log in", "login", "sign in", "signin", "authenticate",
            "autenticación", "autenticacion", "remember me", "acceder",
            "identificarse", "entrar", "usuario", "user",
            "contrasenya", "clave", "credenciales", "inicie sesion",
            "inicie sesión", "acceso", "login portal", "cpanel",
        )
        if any(ind in text_l for ind in weak_login_indicators):
            if is_home:
                return "not_found", "redirected_to_home_with_weak_indicators"
            return "protected", "weak_indicator_detected"

        dashboard_indicators = (
            "dashboard",
            "panel de administración",
            "panel de administracion",
            "admin dashboard",
            "logout",
            "cerrar sesión",
            "cerrar sesion",
            "usuarios",
            "ajustes",
            "settings",
            "plugins",
            "posts",
            "pages",
            "phpmyadmin",
            "database server",
        )
        if status < 400 and any(ind in text_l for ind in dashboard_indicators):
            return "exposed", "dashboard_indicators_detected"

        if status < 400:
            return "exposed", f"status={status}_without_auth_indicators"

        return "unknown", f"status={status}"

    def _probe_with_browser(self, url: str) -> tuple[str, str, str, int | None]:
        """
        Sondea una URL usando Selenium para bypass de anti-bots y clasificacion visual.
        """
        driver = self._get_driver()
        if not driver:
            return "unknown", "selenium_not_available", url, None
        
        try:
            time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
            driver.get(url)
            # Esperar un poco por los retos JS
            time.sleep(2)
            
            final_url = driver.current_url
            html_text = driver.page_source or ""
            title = driver.title or ""
            
            # Reutilizar clasificadores
            if "cpanel" in url.lower() or ":208" in url:
                state, reason, f_url, status = self._classify_cpanel_response(
                    None, html_text, title, final_url, url
                )
                return state, f"browser_{reason}", f_url, status
            
            # Para otros panels, creamos un objeto 'Response' simulado para _classify_admin_probe_response
            class MockResponse:
                def __init__(self, text, url):
                    self.text = text
                    self.url = url
                    self.status_code = 200
                    self.history = []
            
            state, reason = self._classify_admin_probe_response(url, MockResponse(html_text, final_url))
            return state, f"browser_{reason}", final_url, 200

        except Exception as exc:
            return "unknown", f"browser_error={str(exc)[:50]}", url, None

    # ──────────────────────────────────────────────────────────────────────────
    # RESTO DE CHECKS  (sin cambios funcionales, solo ortografia en literales)
    # ──────────────────────────────────────────────────────────────────────────

    def _check_technical(
        self,
        html: str,
        soup: BeautifulSoup,
        base_url: str,
        html_lines: list[str],
        issues: list[str],
        asset_stats: dict,
        recommendations: list[str],
    ) -> None:
        html_lower = html.lower()
        if "<!doctype html>" not in html_lower[:300]:
            issues.append(
                "Falta <!DOCTYPE html> al inicio del documento (modo estandares)."
            )

        charset_meta = soup.find("meta", attrs={"charset": True})
        if not charset_meta:
            issues.append(
                "Falta <meta charset='utf-8'> para una codificacion consistente."
            )

        if not soup.find("meta", attrs={"name": "robots"}):
            issues.append(
                "Falta meta robots (definir index/follow segun el entorno)."
            )

        iframes = soup.find_all("iframe")
        for iframe in iframes:
            if not (iframe.get("title") or "").strip():
                ln, line = self._find_line_for_tag(html_lines, iframe)
                issues.append(
                    f"Iframe sin atributo title en linea aproximada {ln}: {line}"
                )

        id_count: dict[str, int] = {}
        for tag in soup.find_all(attrs={"id": True}):
            tid = (tag.get("id") or "").strip()
            if not tid:
                continue
            id_count[tid] = id_count.get(tid, 0) + 1
        duplicates = [item for item, count in id_count.items() if count > 1]
        for dup in duplicates[:20]:
            issues.append(
                f"ID duplicado detectado: #{dup} "
                "(rompe selectores y accesibilidad)."
            )

        headings = [
            int(h.name[1])
            for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        ]
        for idx in range(1, len(headings)):
            if headings[idx] - headings[idx - 1] > 1:
                issues.append(
                    f"Salto brusco en la jerarquia de encabezados: "
                    f"h{headings[idx - 1]} -> h{headings[idx]}."
                )
                break

        self._check_assets(soup, base_url, html_lines, issues, asset_stats)
        self._check_forms_accessibility(soup, html_lines, issues)

        favicon = soup.find(
            "link", rel=lambda r: r and ("icon" in r or "shortcut icon" in r)
        )
        if not favicon:
            issues.append(
                "Falta favicon (<link rel=\"icon\">). "
                "Afecta al branding y a las pestanas del navegador."
            )

        manifest = soup.find("link", attrs={"rel": "manifest"})
        if not manifest:
            recommendations.append(
                "Falta web manifest (<link rel=\"manifest\">). "
                "Necesario para PWA y la funcion 'agregar a pantalla de inicio'."
            )

        inline_script_chars = sum(
            len(s.get_text(strip=True))
            for s in soup.find_all("script")
            if not s.get("src")
        )
        inline_style_chars = sum(
            len(s.get_text(strip=True)) for s in soup.find_all("style")
        )
        if inline_script_chars > 500_000:
            recommendations.append(
                f"JS en linea muy voluminoso ({inline_script_chars // 1024} KB). "
                "Valorar code-splitting o lazy-loading para mejorar el TTFB."
            )
        if inline_style_chars > 200_000:
            recommendations.append(
                f"CSS en linea muy voluminoso ({inline_style_chars // 1024} KB). "
                "Valorar extraer estilos no criticos a una hoja de estilos cacheable."
            )

    def _check_assets(
        self,
        soup: BeautifulSoup,
        base_url: str,
        html_lines: list[str],
        issues: list[str],
        asset_stats: dict,
    ) -> None:
        base_is_https = base_url.lower().startswith("https://")

        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel", [])).lower()
            href = (link.get("href") or "").strip()
            if "stylesheet" not in rel:
                continue
            ln, line = self._find_line_for_tag(html_lines, link)
            if not href:
                issues.append(
                    f"Hoja de estilos <link> sin href en linea aproximada {ln}: {line}"
                )
                continue
            full = urljoin(base_url, href)
            if base_is_https and full.lower().startswith("http://"):
                asset_stats["mixed_content"] += 1
                issues.append(f"Contenido mixto (mixed content) CSS: {full} (linea aproximada {ln})")
            ok, elapsed_ms, status_code = self._check_url_with_strategies(full)
            asset_stats["checked"] += 1
            if not ok:
                asset_stats["broken"] += 1
                issues.append(
                    f"CSS inaccesible {full} estado={status_code} tiempo={elapsed_ms}ms"
                )

        for script in soup.find_all("script"):
            src = (script.get("src") or "").strip()
            if not src:
                continue
            ln, line = self._find_line_for_tag(html_lines, script)
            full = urljoin(base_url, src)
            if base_is_https and full.lower().startswith("http://"):
                asset_stats["mixed_content"] += 1
                issues.append(
                    f"Contenido mixto (mixed content) JS: {full} "
                    f"(linea aproximada {ln})"
                )
            ok, elapsed_ms, status_code = self._check_url_with_strategies(full)
            asset_stats["checked"] += 1
            if not ok:
                asset_stats["broken"] += 1
                issues.append(
                    f"JS inaccesible {full} estado={status_code} tiempo={elapsed_ms}ms"
                )
            if (
                soup.head
                and script in soup.head.contents
                and not script.get("defer")
                and not script.get("async")
            ):
                issues.append(
                    f"Script bloqueante en <head> sin defer/async: {full} "
                    f"(linea aproximada {ln}: {line[:120]})"
                )

    def _check_forms_accessibility(
        self, soup: BeautifulSoup, html_lines: list[str], issues: list[str]
    ) -> None:
        for field in soup.find_all(["input", "select", "textarea"]):
            if field.name == "input" and (field.get("type") or "").lower() in {
                "hidden", "submit", "button"
            }:
                continue
            has_aria = bool((field.get("aria-label") or "").strip())
            fid = (field.get("id") or "").strip()
            has_label = bool(fid and soup.find("label", attrs={"for": fid}))
            if not has_aria and not has_label:
                ln, line = self._find_line_for_tag(html_lines, field)
                issues.append(
                    f"Campo de formulario sin label ni aria-label en "
                    f"linea aproximada {ln}: {line}"
                )

    def _check_structure(self, soup: BeautifulSoup, issues: list[str]) -> None:
        if soup.html is None:
            issues.append("Falta la etiqueta <html>. Revisar la plantilla base.")
            return
        if soup.head is None:
            issues.append(
                "Falta <head>. Algunos metadatos SEO no pueden aplicarse."
            )
        if soup.body is None:
            issues.append("Falta <body>. El HTML esta incompleto.")
        if not soup.find("h1"):
            issues.append(
                "No existe ningun <h1>; dificulta la estructura semantica."
            )
        if not soup.find_all(["h2", "h3"]):
            issues.append("No hay jerarquia de subtitulos <h2>/<h3>.")

        has_main = bool(soup.find("main") or soup.find(attrs={"role": "main"}))
        has_nav = bool(soup.find("nav") or soup.find(attrs={"role": "navigation"}))
        has_header = bool(
            soup.find("header") or soup.find(attrs={"role": "banner"})
        )
        has_footer = bool(
            soup.find("footer") or soup.find(attrs={"role": "contentinfo"})
        )
        if not has_main:
            issues.append(
                "Falta el landmark <main> o role='main'. "
                "Los lectores de pantalla no pueden saltar al contenido principal."
            )
        if not has_nav:
            issues.append(
                "Falta el landmark <nav> o role='navigation'. "
                "Dificulta la navegacion con lector de pantalla."
            )
        if not has_header:
            issues.append("Falta el landmark <header> o role='banner'.")
        if not has_footer:
            issues.append("Falta el landmark <footer> o role='contentinfo'.")

        generic_texts = {
            "haz clic aqui", "click here", "haz clic aquí", "clic aqui",
            "clic aquí", "leer mas", "leer más", "read more", "aqui", "aquí",
            "here", "mas informacion", "más información", "more info", "mas",
            "más", "enlace", "link", "ver mas", "ver más", "seguir leyendo",
        }
        for anchor in soup.find_all("a"):
            link_text = anchor.get_text(" ", strip=True).lower().strip(" .,;")
            if link_text in generic_texts:
                href = (anchor.get("href") or "")[:80]
                issues.append(
                    f"Enlace con texto generico inutilizable con lector de pantalla: "
                    f"'{link_text}' (href={href})"
                )

        for anchor in soup.find_all("a", attrs={"target": "_blank"}):
            rel = " ".join(anchor.get("rel") or []).lower()
            if "noopener" not in rel or "noreferrer" not in rel:
                href = (anchor.get("href") or "")[:80]
                issues.append(
                    f"Enlace target='_blank' sin rel='noopener noreferrer' "
                    f"(seguridad + tab-napping): {href}"
                )

        for video in soup.find_all("video"):
            if not video.find("track"):
                src = (video.get("src") or "(sin src)")[:80]
                issues.append(
                    f"Elemento <video> sin <track> para subtitulos o descripcion: {src}"
                )

        deprecated_tags = [
            "center", "font", "blink", "marquee", "frame",
            "frameset", "noframes", "big", "strike", "tt",
        ]
        for tag_name in deprecated_tags:
            found = soup.find(tag_name)
            if found:
                issues.append(
                    f"Elemento HTML obsoleto <{tag_name}> detectado. "
                    "Usar el equivalente en CSS."
                )

        for table in soup.find_all("table"):
            if not table.find("th") and not table.find("caption"):
                issues.append(
                    "Tabla sin <th> ni <caption>: posible tabla de maquetacion "
                    "(usar CSS Grid/Flexbox)."
                )
                break

        inline_events = [
            "onclick", "onmouseover", "onmouseout", "onkeydown",
            "onkeyup", "onchange", "onsubmit", "onfocus", "onblur",
        ]
        inline_count = 0
        for tag in soup.find_all(True):
            for ev in inline_events:
                if tag.get(ev):
                    inline_count += 1
                    break
        if inline_count > 0:
            issues.append(
                f"{inline_count} elemento(s) con manejadores de eventos en linea "
                "(onclick/onchange/...). "
                "Rompe la separacion de responsabilidades; usar addEventListener."
            )

    def _check_seo(self, soup: BeautifulSoup, issues: list[str]) -> None:
        title = (
            soup.title.string.strip()
            if soup.title and soup.title.string
            else ""
        )
        if not title:
            issues.append("Falta <title>.")
        elif len(title) < 20 or len(title) > 65:
            issues.append(
                f"Longitud no optima de <title> ({len(title)} caracteres)."
            )

        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc_text = (
            (meta_desc.get("content") or "").strip() if meta_desc else ""
        )
        if not desc_text:
            issues.append("Falta meta description.")
        elif len(desc_text) < 70 or len(desc_text) > 160:
            issues.append(
                f"Longitud no optima de meta description ({len(desc_text)} caracteres)."
            )

        html_tag = soup.find("html")
        if html_tag and not html_tag.get("lang"):
            issues.append("La etiqueta <html> no define el atributo lang.")
        if not soup.find("link", attrs={"rel": "canonical"}):
            issues.append("Falta canonical (<link rel='canonical'>).")
        if not soup.find("meta", attrs={"name": "viewport"}):
            issues.append("Falta meta viewport para diseno responsivo.")

        h1_list = soup.find_all("h1")
        if len(h1_list) > 1:
            issues.append(
                f"Multiples <h1> detectados ({len(h1_list)}). "
                "Solo debe haber uno por pagina."
            )

        og_props = {"og:title", "og:description", "og:image"}
        found_og = {
            (m.get("property") or "").lower()
            for m in soup.find_all("meta", property=True)
        }
        missing_og = og_props - found_og
        if missing_og:
            issues.append(
                f"Open Graph incompleto. Faltan: {', '.join(sorted(missing_og))}. "
                "Afecta a como se muestra el contenido al compartirlo en redes sociales."
            )

        tw_card = soup.find("meta", attrs={"name": "twitter:card"})
        if not tw_card:
            issues.append(
                "Falta meta twitter:card. "
                "El contenido puede mostrarse sin vista previa en Twitter/X."
            )

        jsonld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
        if not jsonld_scripts:
            issues.append(
                "No se detectan datos estructurados JSON-LD (Schema.org). "
                "Mejora la visibilidad en resultados enriquecidos de Google."
            )
        else:
            for js_tag in jsonld_scripts:
                raw_json = js_tag.get_text(strip=True)
                if raw_json:
                    try:
                        data = json.loads(raw_json)
                        if not isinstance(data, dict) or (
                            "@type" not in data and "@context" not in data
                        ):
                            issues.append(
                                "JSON-LD presente pero sin @type ni @context validos. "
                                "Puede no ser interpretado por motores de busqueda."
                            )
                    except (json.JSONDecodeError, ValueError):
                        issues.append(
                            "JSON-LD presente pero con sintaxis JSON invalida. "
                            "No sera interpretado por motores de busqueda."
                        )

        html_tag = soup.find("html")
        page_lang = (html_tag.get("lang") or "").strip() if html_tag else ""
        hreflang_links = soup.find_all(
            "link", attrs={"rel": "alternate", "hreflang": True}
        )
        if page_lang and not hreflang_links:
            issues.append(
                f"La pagina declara lang=\"{page_lang}\" pero no tiene etiquetas "
                "hreflang. Si existen versiones en otros idiomas, anadir "
                "<link rel=\"alternate\" hreflang=\"xx\">."
            )

        for img in soup.find_all("img"):
            alt = (img.get("alt") or "").strip()
            if alt and self._regex.filename_alt_regex.match(alt):
                src_hint = (img.get("src") or "")[:80]
                issues.append(
                    f"El alt de una imagen es un nombre de archivo (\"{alt}\"), "
                    f"no descriptivo. src={src_hint}"
                )

    @staticmethod
    def _is_false_positive(pattern: str, text: str) -> bool:
        if pattern == "sex":
            match = re.search(r"\b(\w*sex\w*)\b", text)
            if match:
                word = match.group(1).lower()
                safe = {
                    "sexta", "sexto", "sesenta", "sexenio",
                    "sexagesimo", "sextuplo",
                }
                if word in safe:
                    return True
        if pattern == "con":
            if re.search(r"\bcon\b", text):
                return True
        if pattern == "put":
            match = re.search(r"\b(\w*put\w*)\b", text)
            if match:
                word = match.group(1).lower()
                safe_tech = {
                    "input", "output", "computo", "computadora",
                    "reputacion", "disputa",
                }
                if word in safe_tech:
                    return True
        return False

    def _check_content(
        self,
        soup: BeautifulSoup,
        issues: list[str],
        html_lines: list[str],
        base_url: str = "",
    ) -> None:
        text = soup.get_text(" ", strip=True)
        text_l = text.lower()
        if not text_l.strip():
            issues.append("No se encontro texto visible en el body.")
            return

        text_normalized = self._normalize_for_detection(text_l)

        all_patterns: tuple[tuple[str, str], ...] = (
            *((p, "contenido de relleno") for p in self._dicts.lorem_patterns),
            *((p, "contenido incoherente") for p in self._dicts.incoherent_patterns),
            *((p, "contenido explicito") for p in self._dicts.explicit_patterns),
            *((p, "palabra malsonante") for p in self._dicts.profanity_patterns),
            *((p, "discurso de odio") for p in self._dicts.hate_patterns),
        )

        for pattern, category in all_patterns:
            in_original = pattern in text_l
            in_normalized = pattern in text_normalized
            if in_original or in_normalized:
                if self._is_false_positive(pattern, text_l):
                    continue
                evasion_note = (
                    " [detectado via normalizacion/leetspeak]"
                    if not in_original
                    else ""
                )
                line_no, line = self._find_line_for_text(html_lines, pattern)
                issues.append(
                    f"[{category}] Patron '{pattern}'{evasion_note} "
                    f"en linea aproximada {line_no}: {line}"
                )

        if self._regex.gibberish_regex.search(text_l):
            issues.append(
                "Secuencias de caracteres repetidos anormales detectadas "
                "(posible ruido o contenido incoherente)."
            )
        if self._regex.multi_symbol_regex.search(text_l):
            issues.append(
                "Bloques de simbolos excesivos detectados "
                "(posible ruido de contenido)."
            )
        if self._regex.character_noise_regex.search(text_l):
            issues.append(
                "Caracteres repetitivos no linguisticos detectados "
                "(ruido de contenido)."
            )
        if len(self._regex.typo_regex.findall(text_l)) >= 5:
            issues.append(
                "Exceso de tokens posiblemente mal escritos o generados "
                "automaticamente."
            )
        if len(self._regex.long_token_regex.findall(text_l)) >= 2:
            issues.append(
                "Tokens extremadamente largos detectados "
                "(posible texto sin sentido o hash pegado)."
            )

        for match_str in self._regex.spaced_chars_regex.finditer(text_l):
            collapsed = match_str.group().replace(" ", "").replace("\t", "")
            for pattern, category in all_patterns:
                if pattern in collapsed:
                    line_no, line = self._find_line_for_text(
                        html_lines, match_str.group().strip()
                    )
                    issues.append(
                        f"[{category}] Evasion con letras espaciadas "
                        f"'{match_str.group().strip()}' "
                        f"(colapsa en '{collapsed}') "
                        f"en linea aproximada {line_no}: {line}"
                    )
                    break

        dotted_matches = self._regex.dotted_chars_regex.findall(text_l)
        if dotted_matches:
            for raw_match in dotted_matches:
                collapsed = re.sub(r"[.\-_*]", "", raw_match)
                for pattern, category in all_patterns:
                    if pattern in collapsed:
                        line_no, line = self._find_line_for_text(
                            html_lines, raw_match
                        )
                        issues.append(
                            f"[{category}] Evasion con puntuacion intercalada "
                            f"'{raw_match}' (colapsa en '{collapsed}') "
                            f"en linea aproximada {line_no}: {line}"
                        )
                        break

        incoherent_samples = self._detect_incoherent_segments(text_l, self._regex)
        if incoherent_samples:
            for reason, token in incoherent_samples[:8]:
                line_no, line = self._find_line_for_text(html_lines, token)
                issues.append(
                    f"Incoherencia heuristica ({reason}) en linea aproximada "
                    f"{line_no}: {line}"
                )

        for segment in self._dicts.blocked_admin_segments:
            in_orig = segment in text_l
            in_norm = segment in text_normalized
            if in_orig or in_norm:
                evasion_note = (
                    " [detectado via normalizacion]" if not in_orig else ""
                )
                line_no, line = self._find_line_for_text(html_lines, segment)
                issues.append(
                    f"Ruta de administracion expuesta en texto visible "
                    f"'{segment}'{evasion_note} en linea aproximada {line_no}: {line}"
                )

        words = self._regex.keyword_density_word_regex.findall(text_l)
        word_count = len(words)
        url_lower = base_url.lower()
        is_short_page = any(
            kw in url_lower
            for kw in (
                "contact", "contacto", "gracias", "thank", "legal",
                "privacy", "aviso",
            )
        )
        if not is_short_page and 0 < word_count < settings.AUDIT_MIN_WORD_COUNT:
            issues.append(
                f"Contenido delgado (thin content): solo {word_count} palabras "
                f"visibles (minimo recomendado {settings.AUDIT_MIN_WORD_COUNT}). "
                "Puede penalizarse en SEO."
            )

        if words:
            freq: dict[str, int] = {}
            for w in words:
                freq[w] = freq.get(w, 0) + 1
            top_word, top_count = max(freq.items(), key=lambda kv: kv[1])
            density = top_count / len(words)
            if density > settings.AUDIT_KEYWORD_DENSITY_MAX:
                issues.append(
                    f"Posible keyword stuffing: '{top_word}' aparece {top_count} veces "
                    f"({density:.1%} del texto). "
                    f"Limite recomendado: {settings.AUDIT_KEYWORD_DENSITY_MAX:.0%}."
                )

        legal_terms = {
            "aviso legal", "aviso-legal", "politica de privacidad",
            "política de privacidad", "privacy policy", "terminos", "términos",
            "condiciones de uso", "cookies", "rgpd", "gdpr", "lopd",
        }
        has_legal = any(term in text_l for term in legal_terms) or any(
            any(
                term in (a.get_text(" ", strip=True).lower())
                or term in (a.get("href") or "").lower()
                for term in legal_terms
            )
            for a in soup.find_all("a")
        )
        if not has_legal:
            issues.append(
                "No se detecta enlace ni texto de aviso legal ni de politica de "
                "privacidad. Obligatorio por el RGPD y la normativa espanola."
            )

        contact_terms = {
            "contacto", "contact", "contactanos", "contáctanos", "escribenos",
        }
        has_contact = (
            any(term in text_l for term in contact_terms)
            or bool(self._regex.sensitive_data_regexes[6][1].search(text))
            or bool(self._regex.sensitive_data_regexes[7][1].search(text))
        )
        if not has_contact:
            issues.append(
                "No se detecta informacion de contacto (email, telefono o seccion "
                "de contacto). Recomendado para generar confianza y cumplir la "
                "normativa legal."
            )

    @staticmethod
    def _detect_incoherent_segments(
        text_l: str, regex_set: AuditRegexSet
    ) -> list[tuple[str, str]]:
        words = regex_set.word_regex.findall(text_l)
        if not words:
            return []

        suspicious: list[tuple[str, str]] = []
        alnum_noise_count = 0

        for w in words:
            if len(w) >= 7:
                vowel_count = sum(1 for c in w if c in "aeiouáéíóúü")
                vowel_ratio = vowel_count / max(1, len(w))
                if vowel_ratio < 0.22:
                    suspicious.append(("baja_proporcion_vocales", w[:30]))
                    continue

            if regex_set.repeated_chunk_regex.search(w):
                suspicious.append(("bloque_repetido", w[:30]))
                continue

            if regex_set.consonant_cluster_regex.search(w):
                suspicious.append(("grupo_consonantico", w[:30]))
                continue

            has_letters = any(ch.isalpha() for ch in w)
            has_digits = any(ch.isdigit() for ch in w)
            if has_letters and has_digits and len(w) >= 8:
                alnum_noise_count += 1

        if alnum_noise_count >= 4:
            suspicious.append(("muchos_tokens_alfanumericos_raros", str(alnum_noise_count)))

        min_hits = max(2, int(len(words) * 0.08))
        if len(suspicious) < min_hits:
            return []
        return suspicious

    def _check_images(
        self,
        soup: BeautifulSoup,
        base_url: str,
        html_lines: list[str],
        issues: list[str],
    ) -> None:
        images = soup.find_all("img")
        if not images:
            issues.append(
                "No hay imagenes en la pagina; comprobar si es lo esperado."
            )
            return

        for img in images:
            src = (img.get("src") or "").strip()
            alt = (img.get("alt") or "").strip()
            line_no, line = self._find_line_for_tag(html_lines, img)
            location = f"linea aproximada {line_no}: {line}"

            if not src:
                issues.append(f"Imagen sin src en {location}")
                continue
            if not alt:
                issues.append(f"Imagen sin alt (src={src}) en {location}")

            absolute_url = urljoin(base_url, src)
            if self._is_banned_url(absolute_url):
                issues.append(
                    f"Imagen no verificada por URL prohibida: "
                    f"{absolute_url} ({location})"
                )
                continue
            if src.startswith("data:"):
                continue

            ok, elapsed_ms, status_code = self._check_url_with_strategies(absolute_url)
            speed = self._classify_speed(elapsed_ms)
            if not ok:
                issues.append(
                    f"Imagen rota src={absolute_url} estado={status_code} "
                    f"tiempo={elapsed_ms}ms ({speed}) en {location}"
                )

            if not img.get("loading"):
                issues.append(
                    f"Imagen sin loading=\"lazy\" (src={src[:80]}) en {location}"
                )
            if not img.get("width") or not img.get("height"):
                issues.append(
                    f"Imagen sin width/height explicitos (causa layout shift / CLS): "
                    f"src={src[:80]} en {location}"
                )
            ext = src.rsplit(".", 1)[-1].lower() if "." in src else ""
            if ext in ("jpg", "jpeg", "png", "gif", "bmp", "tiff"):
                issues.append(
                    f"Imagen en formato heredado ({ext}): considerar WebP/AVIF para "
                    f"mejor rendimiento. src={src[:80]}"
                )

    def _check_links_recursive(
        self,
        soup: BeautifulSoup,
        base_url: str,
        html_lines: list[str],
        issues: list[str],
        crawl_stats: dict,
    ) -> None:
        if self._is_banned_url(base_url):
            issues.append("Rastreo recursivo omitido por URL prohibida.")
            return

        base_host = self._normalize_host(urlparse(base_url).netloc)
        queue: list[tuple[str, int]] = []
        visited: set[str] = set()

        for anchor in soup.find_all("a"):
            href = (anchor.get("href") or "").strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            if href.startswith("#"):
                fragment = href[1:]
                if fragment and not soup.find(id=fragment) and not soup.find(
                    "a", attrs={"name": fragment}
                ):
                    ln, line = self._find_line_for_tag(html_lines, anchor)
                    issues.append(
                        f"Ancla rota: href=\"{href}\" apunta a un id que no existe "
                        f"en el DOM. Linea aproximada {ln}: {line}"
                    )
                continue
            full = urljoin(base_url, href)
            queue.append((full, 0))
            if any(seg in full.lower() for seg in self._dicts.blocked_admin_segments):
                ln, line = self._find_line_for_tag(html_lines, anchor)
                issues.append(
                    f"Enlace prohibido detectado {full} en linea aproximada {ln}: {line}"
                )

        while queue and crawl_stats["tested"] < settings.AUDIT_MAX_RECURSIVE_LINKS:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            if self._is_banned_url(url):
                crawl_stats["skipped"] += 1
                issues.append(
                    f"Enlace omitido por politica de bloqueo: {url}"
                )
                continue

            ok, elapsed_ms, status_code, content = self._check_url_with_strategies(
                url,
                include_content=(depth < settings.AUDIT_MAX_CRAWL_DEPTH),
            )
            crawl_stats["tested"] += 1
            speed = self._classify_speed(elapsed_ms)
            if not ok:
                crawl_stats["broken"] += 1
                issues.append(
                    f"Enlace roto confirmado (HTTP+navegador) {url} "
                    f"estado={status_code} tiempo={elapsed_ms}ms ({speed})"
                )

            if content and depth < settings.AUDIT_MAX_CRAWL_DEPTH:
                page_soup = BeautifulSoup(content, settings.BS4_PARSER)
                for inner_anchor in page_soup.find_all("a"):
                    href = (inner_anchor.get("href") or "").strip()
                    if not href or href.startswith(
                        ("#", "mailto:", "tel:", "javascript:")
                    ):
                        continue
                    full_inner = urljoin(url, href)
                    inner_host = self._normalize_host(urlparse(full_inner).netloc)
                    if inner_host != base_host:
                        continue
                    queue.append((full_inner, depth + 1))

    def _check_buttons(
        self,
        soup: BeautifulSoup,
        base_url: str,
        html_lines: list[str],
        issues: list[str],
    ) -> None:
        buttons = soup.find_all(["button", "input"])
        forms = soup.find_all("form")

        if not buttons:
            issues.append(
                "No hay botones detectables en el HTML estatico."
            )

        for btn in buttons:
            if btn.name == "input" and (btn.get("type") or "").lower() not in {
                "submit", "button"
            }:
                continue
            ln, line = self._find_line_for_tag(html_lines, btn)
            text = (
                btn.get_text(" ", strip=True) if isinstance(btn, Tag) else ""
            )
            if not text:
                text = btn.get("value", "(sin texto)")
            if not text or text == "(sin texto)":
                issues.append(
                    f"Boton sin texto visible en linea aproximada {ln}: {line}"
                )

        for form in forms:
            action = (form.get("action") or "").strip()
            method = (form.get("method") or "get").lower()
            ln, line = self._find_line_for_tag(html_lines, form)
            if not action:
                issues.append(
                    f"Formulario sin action en linea aproximada {ln}: {line}"
                )
                continue

            target = urljoin(base_url, action)
            if self._is_banned_url(target):
                issues.append(
                    f"Formulario no probado por URL prohibida: {target}"
                )
                continue
            if any(
                seg in target.lower() for seg in self._dicts.blocked_admin_segments
            ):
                issues.append(
                    f"Formulario apunta a una ruta prohibida ({target}) "
                    f"en linea aproximada {ln}: {line}"
                )
                continue

            ok, elapsed_ms, status_code = self._check_url_with_strategies(
                target, method=method
            )
            speed = self._classify_speed(elapsed_ms)
            if not ok:
                issues.append(
                    f"Fallo al probar el action del formulario {target} "
                    f"metodo={method.upper()} estado={status_code} "
                    f"tiempo={elapsed_ms}ms ({speed})"
                )

    # ──────────────────────────────────────────────────────────────────────────
    # VERIFICACION DE URLs
    # ──────────────────────────────────────────────────────────────────────────

    def _check_url(
        self,
        url: str,
        method: str = "head",
        include_content: bool = False,
    ) -> tuple:
        if self._is_banned_url(url):
            return (False, 0, "blocked", "") if include_content else (False, 0, "blocked")
        time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)

        start = time.perf_counter()
        try:
            method_l = method.lower()
            if method_l == "post":
                response = self._session.post(url, timeout=self._timeout, data={})
            elif method_l == "get":
                response = self._session.get(url, timeout=self._timeout)
            else:
                response = self._session.head(
                    url, timeout=self._timeout, allow_redirects=True
                )
                if response.status_code == 405 or response.status_code >= 400:
                    response = self._session.get(url, timeout=self._timeout, allow_redirects=True)

            elapsed_ms = int((time.perf_counter() - start) * 1000)
            ok = response.status_code < 400
            if include_content:
                content = (
                    response.text
                    if "text/html"
                    in response.headers.get("content-type", "").lower()
                    else ""
                )
                return ok, elapsed_ms, response.status_code, content
            return ok, elapsed_ms, response.status_code
        except requests.RequestException:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            if include_content:
                return False, elapsed_ms, "request_exception", ""
            return False, elapsed_ms, "request_exception"

    def _check_url_with_strategies(
        self,
        url: str,
        method: str = "head",
        include_content: bool = False,
    ) -> tuple:
        primary = self._check_url(url, method=method, include_content=include_content)
        if include_content:
            ok, elapsed_ms, status_code, content = primary
        else:
            ok, elapsed_ms, status_code = primary
            content = ""

        if ok:
            return primary

        browser_ok, browser_ms = self._check_url_browser(url)
        if browser_ok:
            if include_content:
                return True, browser_ms, f"{status_code}->ok_navegador", content
            return True, browser_ms, f"{status_code}->ok_navegador"

        if include_content:
            return False, elapsed_ms, status_code, content
        return False, elapsed_ms, status_code

    def _check_url_browser(self, url: str) -> tuple[bool, int]:
        if self._is_banned_url(url):
            return False, 0
        if self._browser_confirms >= self._max_browser_confirms:
            return False, 0

        driver = self._get_driver()
        if driver is None:
            return False, 0

        start = time.perf_counter()
        try:
            self._browser_confirms += 1
            driver.get(url)
            WebDriverWait(driver, max(4, settings.SELENIUM_IMPLICIT_WAIT)).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return True, elapsed_ms
        except (TimeoutException, WebDriverException):
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return False, elapsed_ms

    def _warm_up_cookies(self, base_url: str) -> None:
        try:
            resp = self._session.get(
                base_url, timeout=self._timeout, allow_redirects=True
            )
            self._last_response_headers = dict(resp.headers)
        except requests.RequestException:
            logger.debug(
                "No se pudo hacer warm-up de cookies para %s", base_url
            )
            self._last_response_headers = {}

    def _get_driver(self) -> webdriver.Chrome | None:
        if self._driver is not None:
            return self._driver
        try:
            import random
            opts = Options()
            if settings.SELENIUM_HEADLESS:
                opts.add_argument("--headless=new")
            ua = random.choice(settings.USER_AGENT_POOL)
            opts.add_argument(f"user-agent={ua}")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option(
                "excludeSwitches", ["enable-automation", "enable-logging"]
            )
            opts.add_experimental_option("useAutomationExtension", False)
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-infobars")
            opts.add_argument("--lang=es-ES")
            opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})

            service = (
                Service(settings.SELENIUM_DRIVER_PATH)
                if settings.SELENIUM_DRIVER_PATH
                else Service()
            )
            driver = webdriver.Chrome(service=service, options=opts)
            driver.set_page_load_timeout(settings.SELENIUM_PAGE_LOAD_TIMEOUT)
            try:
                driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {
                        "source": """
                            Object.defineProperty(navigator, "webdriver",
                                { get: () => undefined });
                            Object.defineProperty(navigator, "plugins",
                                { get: () => [1, 2, 3, 4, 5] });
                            Object.defineProperty(navigator, "languages",
                                { get: () => ["es-ES", "es", "en"] });
                            window.chrome = { runtime: {} };
                        """
                    },
                )
            except Exception:
                pass

            self._driver = driver
            return self._driver
        except Exception as exc:
            logger.debug(
                "Selenium no disponible para confirmaciones: %s", exc
            )
            self._driver = None
            return None

    def _check_js_console_errors(self, base_url: str, issues: list[str]) -> None:
        if not settings.AUDIT_JS_LOGS_ENABLED:
            return
        driver = self._get_driver()
        if driver is None:
            return
        try:
            time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
            driver.get(base_url)
            WebDriverWait(driver, max(4, settings.SELENIUM_IMPLICIT_WAIT)).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            time.sleep(1)
            try:
                logs = driver.get_log("browser")
            except Exception:
                logs = []
            error_count = 0
            for entry in logs:
                level = entry.get("level", "").upper()
                if level == "SEVERE":
                    if error_count >= settings.AUDIT_JS_CONSOLE_MAX_ERRORS:
                        issues.append(
                            f"... y mas errores JS "
                            f"(limite de {settings.AUDIT_JS_CONSOLE_MAX_ERRORS} alcanzado)."
                        )
                        break
                    msg = entry.get("message", "(sin mensaje)")[:200]
                    source = entry.get("source", "desconocido")
                    issues.append(f"[ERROR JS] {source}: {msg}")
                    error_count += 1
            if error_count == 0:
                logger.debug(
                    "No se detectaron errores JS SEVERE en consola."
                )
        except (TimeoutException, WebDriverException) as exc:
            logger.debug(
                "No se pudieron capturar logs JS para %s: %s", base_url, exc
            )
        except Exception as exc:
            logger.debug(
                "Error inesperado capturando logs JS: %s", exc
            )

    def _interact_buttons_selenium(self, base_url: str, issues: list[str]) -> None:
        if not settings.AUDIT_BUTTON_INTERACTION_ENABLED:
            return
        driver = self._get_driver()
        if driver is None:
            return
        try:
            time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
            driver.get(base_url)
            WebDriverWait(driver, max(4, settings.SELENIUM_IMPLICIT_WAIT)).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            time.sleep(0.5)

            from selenium.webdriver.common.by import By

            selectors = [
                "button",
                "input[type='submit']",
                "input[type='button']",
                "a[role='button']",
                "[role='button']",
            ]
            buttons = []
            for sel in selectors:
                try:
                    buttons.extend(driver.find_elements(By.CSS_SELECTOR, sel))
                except Exception:
                    pass

            original_url = driver.current_url
            clicked = 0
            for btn in buttons[: settings.AUDIT_BUTTON_MAX_CLICKS * 2]:
                if clicked >= settings.AUDIT_BUTTON_MAX_CLICKS:
                    break
                try:
                    if not btn.is_displayed() or not btn.is_enabled():
                        continue
                    btn_text = (
                        btn.text or btn.get_attribute("value") or "(sin texto)"
                    )[:60]
                    btn_tag = btn.tag_name

                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", btn
                    )
                    time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)

                    try:
                        btn.click()
                        clicked += 1
                        time.sleep(0.3)
                        try:
                            driver.find_element(By.TAG_NAME, "body")
                        except Exception:
                            issues.append(
                                f"La pagina se rompio tras el clic en "
                                f"<{btn_tag}> '{btn_text}'. "
                                "El body dejo de ser accesible."
                            )
                        if driver.current_url != original_url:
                            driver.back()
                            time.sleep(0.5)
                            WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located(
                                    ("tag name", "body")
                                )
                            )
                    except WebDriverException as click_exc:
                        exc_msg = str(click_exc)[:150]
                        if (
                            "not interactable" in exc_msg.lower()
                            or "obscured" in exc_msg.lower()
                        ):
                            issues.append(
                                f"Boton <{btn_tag}> '{btn_text}' no interactivo "
                                "u oculto por otro elemento."
                            )
                        elif "stale" in exc_msg.lower():
                            pass
                        else:
                            issues.append(
                                f"Error al hacer clic en <{btn_tag}> "
                                f"'{btn_text}': {exc_msg}"
                            )
                        clicked += 1
                except Exception:
                    pass
        except (TimeoutException, WebDriverException) as exc:
            logger.debug(
                "No se pudieron probar botones para %s: %s", base_url, exc
            )
        except Exception as exc:
            logger.debug(
                "Error inesperado probando botones: %s", exc
            )

    def _close_driver(self) -> None:
        if self._driver is None:
            return
        try:
            self._driver.quit()
        except Exception:
            pass
        self._driver = None

    # ──────────────────────────────────────────────────────────────────────────
    # METRICAS Y PUNTUACION
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _collect_metrics(
        soup: BeautifulSoup,
        metadata: dict,
        security_issues: list[str],
        image_issues: list[str],
        link_issues: list[str],
        button_issues: list[str],
        technical_issues: list[str],
        crawl_stats: dict,
        asset_stats: dict,
    ) -> dict:
        source_response_ms = metadata.get("response_time_ms", -1)
        source_speed = (
            QualityAuditor._classify_speed(source_response_ms)
            if source_response_ms >= 0
            else "sin_dato"
        )
        return {
            "status_code": metadata.get("status_code", "sin_dato"),
            "release_gate_blocked": False,
            "source_response_time_ms": source_response_ms,
            "source_response_speed": source_speed,
            "title_length": (
                len(soup.title.string.strip())
                if soup.title and soup.title.string
                else 0
            ),
            "meta_description_present": bool(
                soup.find("meta", attrs={"name": "description"})
            ),
            "h1_count": len(soup.find_all("h1")),
            "image_count": len(soup.find_all("img")),
            "links_count": len(soup.find_all("a")),
            "forms_count": len(soup.find_all("form")),
            "buttons_count": len(soup.find_all(["button", "input"])),
            "word_count": len(soup.get_text(" ", strip=True).split()),
            "security_issue_count": len(
                [i for i in security_issues if "Sin incidencias" not in i]
            ),
            "image_issue_count": len(
                [i for i in image_issues if "Sin incidencias" not in i]
            ),
            "link_issue_count": len(
                [i for i in link_issues if "Sin incidencias" not in i]
            ),
            "button_issue_count": len(
                [i for i in button_issues if "Sin incidencias" not in i]
            ),
            "technical_issue_count": len(
                [i for i in technical_issues if "Sin incidencias" not in i]
            ),
            "recursive_links_tested": crawl_stats["tested"],
            "recursive_links_broken": crawl_stats["broken"],
            "recursive_links_skipped": crawl_stats["skipped"],
            "assets_checked": asset_stats["checked"],
            "assets_broken": asset_stats["broken"],
            "assets_mixed_content": asset_stats["mixed_content"],
        }

    @staticmethod
    def _calculate_score(
        security_issues: list[str],
        seo_issues: list[str],
        content_issues: list[str],
        image_issues: list[str],
        structure_issues: list[str],
        link_issues: list[str],
        button_issues: list[str],
        technical_issues: list[str],
    ) -> int:
        score = 100.0
        
        # Categorias con sus topes de deduccion maxima para evitar el 0/100 facil
        categories = {
            "security": (security_issues, 30.0),
            "seo": (seo_issues, 20.0),
            "content": (content_issues, 20.0),
            "images": (image_issues, 15.0),
            "structure": (structure_issues, 15.0),
            "links": (link_issues, 20.0),
            "buttons": (button_issues, 15.0),
            "technical": (technical_issues, 20.0),
        }

        total_deduction = 0.0

        for cat_name, (issue_list, cat_limit) in categories.items():
            cat_deduction = 0.0
            type_counts: dict[str, int] = {}

            for issue in issue_list:
                issue_l = issue.lower()
                if "sin incidencias" in issue_l:
                    continue

                # Identificar "tipo" de error para aplicar deduccion decreciente
                # Simplificado: usamos los keywords para identificar el tipo
                issue_type = "generic"
                
                critical_keywords = (
                    "dato sensible", "panel admin", "clave", "password", "token",
                    "roto", "fallo al", "error de consola", "no existe en el dom",
                    "bloqueo", "vulnerabilidad", "sin autenticacion",
                    "discurso de odio", "explicito", "malsonante",
                    "firewall_block",
                )
                high_keywords = (
                    "falta cabecera", "hsts", "csp", "x-frame", "integrity (sri)",
                    "falta doctype", "falta title", "falta description",
                    "sin label", "viewport", "mixed content", "id duplicado",
                    "contenido mixto",
                )
                medium_keywords = (
                    "falta canonical", "favicon", "alt de imagen", "heredado",
                    "loading=\"lazy\"", "jerarquia", "semantica", "noopener",
                    "lorem ipsum", "relleno", "hreflang",
                )

                base_weight = 0.1
                for k in critical_keywords:
                    if k in issue_l:
                        base_weight = 3.0
                        issue_type = k
                        break
                if issue_type == "generic":
                    for k in high_keywords:
                        if k in issue_l:
                            base_weight = 1.5
                            issue_type = k
                            break
                if issue_type == "generic":
                    for k in medium_keywords:
                        if k in issue_l:
                            base_weight = 0.5
                            issue_type = k
                            break

                # Aplicar deduccion decreciente: 
                # 100% las primeras 3 veces, 50% las siguientes 5, 10% el resto
                count = type_counts.get(issue_type, 0)
                if count < 3:
                    multiplier = 1.0
                elif count < 8:
                    multiplier = 0.5
                else:
                    multiplier = 0.1
                
                cat_deduction += base_weight * multiplier
                type_counts[issue_type] = count + 1

            # Aplicar limite de la categoria
            total_deduction += min(cat_deduction, cat_limit)

        score = 100.0 - total_deduction
        return max(0, min(100, int(score)))

    @staticmethod
    def _status_from_score(score: int) -> str:
        if score >= 85:
            return "excelente"
        if score >= 70:
            return "bueno"
        if score >= 50:
            return "mejorable"
        return "critico"

    @staticmethod
    def _build_recommendations(
        security_issues: list[str],
        seo_issues: list[str],
        content_issues: list[str],
        image_issues: list[str],
        structure_issues: list[str],
        link_issues: list[str],
        button_issues: list[str],
        technical_issues: list[str],
    ) -> list[str]:
        recommendations: list[str] = []
        if any("Sin incidencias" not in i for i in security_issues):
            recommendations.append(
                "Reforzar la seguridad HTTP: cabeceras, HTTPS, SRI y datos "
                "sensibles expuestos."
            )
        if any("Sin incidencias" not in i for i in seo_issues):
            recommendations.append(
                "Corregir metadatos SEO: title, description, canonical, "
                "viewport y lang."
            )
        if any("Sin incidencias" not in i for i in structure_issues):
            recommendations.append(
                "Reforzar la estructura semantica: html/head/body y jerarquia "
                "de encabezados."
            )
        if any("Sin incidencias" not in i for i in image_issues):
            recommendations.append(
                "Arreglar las imagenes rotas y completar los atributos alt "
                "con textos descriptivos."
            )
        if any("Sin incidencias" not in i for i in content_issues):
            recommendations.append(
                "Eliminar contenido de relleno, incoherente, malsonante, "
                "explicito o de odio."
            )
        if any("Sin incidencias" not in i for i in link_issues):
            recommendations.append(
                "Corregir los enlaces rotos y eliminar rutas admin/wp-admin del sitio."
            )
        if any("Sin incidencias" not in i for i in button_issues):
            recommendations.append(
                "Revisar botones y formularios "
                "(texto visible, action valida y respuesta correcta)."
            )
        if any("Sin incidencias" not in i for i in technical_issues):
            recommendations.append(
                "Aplicar hardening tecnico: doctype/charset, recursos accesibles, "
                "sin mixed content, labels e IDs unicos."
            )
        return recommendations

    @staticmethod
    def _evaluate_release_gate(
        score: int,
        security_issues: list[str],
        content_issues: list[str],
        link_issues: list[str],
        technical_issues: list[str],
        image_issues: list[str],
        button_issues: list[str],
    ) -> tuple[bool, list[str]]:
        blockers: list[str] = []

        if score < 70:
            blockers.append(
                f"Puntuacion global insuficiente para produccion ({score}/100)."
            )

        security_critical = (
            "dato sensible",
            "http en lugar de https",
            "panel de administracion accesible",
            "panel admin accesible",
            "panel admin posiblemente accesible",
            "sin autenticacion",
            "sin autenticación",
        )
        if any(
            any(flag in issue.lower() for flag in security_critical)
            for issue in security_issues
        ):
            blockers.append(
                "Incidencias de seguridad criticas (datos sensibles, HTTP o panel "
                "de administracion expuesto)."
            )

        strong_content_flags = (
            "contenido explicito",
            "contenido sexual",
            "porno",
            "nsfw",
            "patron '",
            "incoherencia heuristica",
            "discurso de odio",
            "palabra malsonante",
            "evasion con letras",
            "evasion con puntuacion",
        )
        if any(
            any(flag in issue.lower() for flag in strong_content_flags)
            for issue in content_issues
        ):
            blockers.append(
                "Contenido sensible, incoherente o inadecuado detectado en el "
                "texto visible."
            )

        broken_links = [
            i for i in link_issues if "enlace roto confirmado" in i.lower()
        ]
        if broken_links:
            blockers.append(
                f"Enlaces rotos confirmados ({len(broken_links)})."
            )

        broken_images = [
            i for i in image_issues if "imagen rota" in i.lower()
        ]
        if broken_images:
            blockers.append(
                f"Imagenes rotas detectadas ({len(broken_images)})."
            )

        critical_tech_flags = (
            "mixed content", "contenido mixto", "id duplicado",
            "doctype", "charset", "script bloqueante",
        )
        if any(
            any(flag in issue.lower() for flag in critical_tech_flags)
            for issue in technical_issues
        ):
            blockers.append(
                "Incidencias tecnicas criticas para la estabilidad o seguridad "
                "detectadas."
            )

        form_failures = [
            i for i in button_issues
            if "fallo al probar el action del formulario" in i.lower()
        ]
        if form_failures:
            blockers.append(
                f"Formularios con fallos en el action detectados ({len(form_failures)})."
            )

        return (len(blockers) > 0), blockers

    # ──────────────────────────────────────────────────────────────────────────
    # UTILIDADES ESTATICAS
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _classify_speed(response_time_ms: int) -> str:
        if response_time_ms < 0:
            return "sin_dato"
        if response_time_ms < 400:
            return "rapido"
        if response_time_ms < 1200:
            return "medio"
        return "lento"

    @staticmethod
    def _normalize_host(host: str) -> str:
        host = host.lower().strip()
        return host[4:] if host.startswith("www.") else host

    def _is_banned_url(self, url: str) -> bool:
        host = self._normalize_host(urlparse(url).netloc)
        return host in {
            self._normalize_host(x) for x in settings.AUDIT_BANNED_HOSTS
        }

    @staticmethod
    def _find_line_for_tag(html_lines: list[str], tag: Tag) -> tuple[int, str]:
        text = str(tag).strip().split("\n")[0][:300]
        return QualityAuditor._find_line_for_text(html_lines, text)

    @staticmethod
    def _find_line_for_text(html_lines: list[str], text: str) -> tuple[int, str]:
        token = text.strip().lower()
        if not token:
            return -1, "(linea no localizada)"
        token = token[:120]
        for idx, line in enumerate(html_lines, start=1):
            if token in line.lower():
                return idx, line.strip()[:350]
        return -1, f"(linea no localizada para '{token}')"

    @staticmethod
    def _ensure_non_empty(section_name: str, issues: list[str]) -> None:
        if not issues:
            issues.append(f"Sin incidencias detectadas en {section_name}.")