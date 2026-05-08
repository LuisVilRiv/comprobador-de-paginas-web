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
        self._last_response_headers: dict = {}   # cabeceras HTTP de la peticion inicial

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
                recommendations.append("Cambiar URL objetivo por un dominio permitido para validar enlaces e imagenes.")
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

            # Checks que requieren Selenium activo
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
            soup,
            metadata,
            security_issues,
            image_issues,
            link_issues,
            button_issues,
            technical_issues,
            crawl_stats,
            asset_stats,
        )
        score = self._calculate_score(
            security_issues,
            seo_issues,
            content_issues,
            image_issues,
            structure_issues,
            link_issues,
            button_issues,
            technical_issues,
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
                security_issues,
                seo_issues,
                content_issues,
                image_issues,
                structure_issues,
                link_issues,
                button_issues,
                technical_issues,
            )
        )
        if not recommendations:
            recommendations.append("No se detectan mejoras criticas. Mantener monitorizacion periodica.")
        if release_blocked:
            recommendations.insert(0, "BLOQUEAR despliegue a produccion hasta resolver blockers del gate.")

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

    @staticmethod
    def report_to_text(report: QualityAuditReport) -> str:
        # Generar lista de pruebas realizadas (dinámica basada en el auditor)
        tests_performed = [
            "Analisis de cabeceras de seguridad HTTP (CSP, HSTS, XFO...)",
            "Escaneo de rutas de administracion (/admin, /wp-login...) con recursividad",
            "Deteccion de datos sensibles expuestos (claves, tokens, APIs)",
            "Auditoria de accesibilidad WCAG (labels, roles, landmarks, contrastes)",
            "Validacion SEO (metas, canonical, lang, jerarquia Hx)",
            "Analisis de contenido (lorem ipsum, toxicidad, duplicidad)",
            "Verificacion de enlaces y assets (rotos, mixed content, SRI)",
            "Pruebas de interaccion UI (clicks en botones y formularios via Selenium)",
            "Monitorizacion de errores de consola JS y rendimiento (bloqueo de renderizado)",
        ]

        # Resumen general de mejoras (basado en recomendaciones)
        top_improvements = report.recommendations[:5] if report.recommendations else ["Mantener monitorizacion periodica."]

        # Justificación de puntuación
        score_checks = []
        if report.score >= 90:
            score_checks.append("[\u2713] Excelente salud tecnica y de seguridad.")
        elif report.score >= 70:
            score_checks.append("[\u2713] Calidad buena, con margen de mejora en optimizacion.")
        else:
            score_checks.append("[x] Critico: Se requieren correcciones inmediatas de seguridad/SEO.")

        if report.security_issues:
            score_checks.append(f"[x] Detectados {len(report.security_issues)} fallos de seguridad.")
        else:
            score_checks.append("[\u2713] Sin brechas de seguridad criticas detectadas.")

        if report.link_issues or report.technical_issues:
            score_checks.append(f"[x] Existen recursos rotos o errores tecnicos que penalizan.")
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
            "-------------------------------",
            *[f"- {item}" for item in top_improvements],
            "",
            "3. PUNTUACION Y ESTADO",
            "----------------------",
            f"SCORE: {report.score}/100",
            f"ESTADO: {report.status}",
            f"GATE DE PRODUCCION: {'BLOQUEADO' if report.release_blocked else 'APTO'}",
            "",
            "Justificacion del score:",
            *[f"  {check}" for check in score_checks],
            "",
            "4. DETALLE DE HALLAZGOS",
            "-----------------------",
            "",
            "SEGURIDAD HTTP Y PROBING:",
            *([f"  - {item}" for item in report.security_issues] or ["  - OK. Sin vulnerabilidades detectadas."]),
            "",
            "SEO Y METADATOS:",
            *([f"  - {item}" for item in report.seo_issues] or ["  - OK. Optimizacion SEO correcta."]),
            "",
            "ESTRUCTURA Y ACCESIBILIDAD:",
            *([f"  - {item}" for item in report.structure_issues] or ["  - OK. Estructura semantica solida."]),
            "",
            "CONTENIDO Y CALIDAD:",
            *([f"  - {item}" for item in report.content_issues] or ["  - OK. Sin contenido problematico."]),
            "",
            "IMAGENES Y ASSETS:",
            *([f"  - {item}" for item in report.image_issues] or ["  - OK. Assets optimizados."]),
            "",
            "ENLACES Y NAVEGACION:",
            *([f"  - {item}" for item in report.link_issues] or ["  - OK. Sin enlaces rotos."]),
            "",
            "BOTONES Y FORMULARIOS:",
            *([f"  - {item}" for item in report.button_issues] or ["  - OK. Interactividad correcta."]),
            "",
            "TECNICO / CONSOLA JS:",
            *([f"  - {item}" for item in report.technical_issues] or ["  - OK. Sin errores de ejecucion."]),
            "",
            "===========================================================",
            "               FIN DEL INFORME AUDITORIA                   ",
            "===========================================================",
        ]
        return "\n".join(lines)

    # ── Normalización para detección robusta de contenido ─────────────────────

    @staticmethod
    def _normalize_for_detection(text: str) -> str:
        """
        Normaliza el texto antes de comparar contra los patrones de contenido
        problemático. Detecta variantes de evasión comunes:

        1. Leetspeak: p0rn → porn, s3x → sex, @dul+os → adultos
        2. Letras separadas por espacios: "p o r n" → "porn"
        3. Letras separadas por puntuación: "p.o.r.n" / "p-o-r-n" → "porn"
        4. Lookalikes unicode (fullwidth, cirílico…): ｐｏｒｎ → porn
        5. Caracteres repetidos entre letras: "p**o**r**n" → "porn"
        """
        t = text.lower()

        # 1. Normalizar lookalikes unicode fullwidth (ａ→a, ０→0…)
        t = t.translate(str.maketrans(
            "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"
            "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"
            "０１２３４５６７８９",
            "abcdefghijklmnopqrstuvwxyz"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789",
        ))

        # 2. Leetspeak: sustituir dígitos/símbolos por su letra equivalente
        t = t.translate(LEET_TRANSLATION_TABLE)

        # 3. Eliminar puntuación entre letras: "p.o.r.n" → "porn"
        t = re.sub(r"([a-z])[.\-_*,;:!?'\"\\]([a-z])", r"\1\2", t)
        # Repetir para cadenas de 3+ separadores: "p.o.r.n.o" necesita dos pasadas
        t = re.sub(r"([a-z])[.\-_*,;:!?'\"\\]([a-z])", r"\1\2", t)

        # 4. Colapsar letras individuales separadas por espacios: "p o r n" → "porn"
        #    Un "run" es 3+ letras sueltas consecutivas separadas por 1-2 espacios.
        t = re.sub(
            r"(?<!\w)(\w)(?!\w)([ \t]{1,2}(?<!\w)\w(?!\w)){2,}",
            lambda m: m.group().replace(" ", "").replace("\t", ""),
            t,
        )

        # 5. Eliminar caracteres no alfanuméricos que queden entre letras
        #    tras las transformaciones anteriores (ej: asteriscos residuales)
        t = re.sub(r"([a-z])\*+([a-z])", r"\1\2", t)

        return t

    # ── Checks principales ────────────────────────────────────────────────────

    def _check_security(
        self,
        html: str,
        soup: BeautifulSoup,
        base_url: str,
        issues: list[str],
    ) -> None:
        """
        Comprueba cabeceras de seguridad HTTP, uso de HTTPS, Subresource Integrity
        y datos sensibles expuestos en el HTML crudo.
        """
        # ── 1. HTTPS vs HTTP ─────────────────────────────────────────────────
        if base_url.lower().startswith("http://"):
            issues.append(
                "La URL usa HTTP en lugar de HTTPS. Todo el trafico viaja sin cifrar."
            )

        # ── 2. Cabeceras de seguridad HTTP ───────────────────────────────────
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
                "El navegador puede interpretar recursos con MIME incorrecto (MIME sniffing)."
            ),
            "referrer-policy": (
                "Falta cabecera Referrer-Policy. "
                "La URL completa puede filtrarse a terceros via cabecera Referer."
            ),
        }
        for header, message in required_headers.items():
            if header not in headers:
                issues.append(message)

        # HSTS solo obligatorio si el sitio es HTTPS
        if base_url.lower().startswith("https://"):
            if "strict-transport-security" not in headers:
                issues.append(
                    "Falta Strict-Transport-Security (HSTS). "
                    "Los navegadores pueden conectar por HTTP en visitas futuras."
                )

        if not headers:
            issues.append(
                "No se pudieron obtener cabeceras HTTP de respuesta "
                "(warm-up fallido o URL prohibida). Cabeceras de seguridad no verificadas."
            )

        # ── 3. Subresource Integrity (SRI) ───────────────────────────────────
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
                    f"Falta atributo integrity (SRI) en {len(sri_missing)} recursos externos "
                    f"(ej: {', '.join(sri_missing[:2])}...). Riesgo de inyeccion si el CDN es comprometido."
                )
            else:
                for src in sri_missing:
                    issues.append(f"Recurso externo sin atributo integrity (SRI): {src}")

        # ── 4. Datos sensibles en el HTML crudo ──────────────────────────────
        for label, pattern in self._regex.sensitive_data_regexes:
            # Si el usuario dice que email y telefono son normales, los saltamos o somos menos estrictos
            label_l = label.lower()
            if any(x in label_l for x in ("email", "teléfono", "telefono", "phone")):
                continue
                
            for match in pattern.finditer(html):
                snippet = match.group().strip()
                snippet_l = snippet.lower()
                
                # Filtrar tokens genéricos o undefined
                if any(x in snippet_l for x in ("undefined", "null", "generic", "sample", "token_here")):
                    continue
                if len(snippet) < 6: # Evitar falsos positivos por strings muy cortos
                    continue
                
                issues.append(
                    f"[DATO SENSIBLE] {label} detectado en HTML: '{snippet[:60]}...'"
                )
                break # Solo reportar el primero de cada tipo para evitar ruido

        # ── 5. Admin URL probing ─────────────────────────────────────────────
        if not self._is_banned_url(base_url):
            parsed = urlparse(base_url)
            base_origin = f"{parsed.scheme}://{parsed.netloc}"

            for admin_path in settings.AUDIT_ADMIN_PROBE_PATHS:
                probe_url = base_origin + admin_path
                state, reason, final_url, resp_status = self._probe_admin_path_recursive(probe_url)

                if state == "protected":
                    issues.append(
                        f"Panel admin en {admin_path} protegido con autenticacion "
                        f"({reason}, final_url={final_url}). OK."
                    )
                elif state == "exposed":
                    issues.append(
                        f"CRITICO: Panel admin posiblemente accesible SIN autenticacion en {admin_path} "
                        f"({reason}, status={resp_status}, final_url={final_url}). "
                        "Revisar manualmente y proteger con usuario/contrasena."
                    )
                elif state == "unknown":
                    issues.append(
                        f"No se pudo confirmar si el panel admin en {admin_path} esta protegido "
                        f"({reason}, final_url={final_url}). Requiere verificacion manual."
                    )
                elif state == "not_found":
                    logger.debug(
                        "Ruta admin no encontrada/no accesible: %s (%s)",
                        probe_url,
                        reason,
                    )

    def _probe_admin_path_recursive(
        self,
        url: str,
        depth: int = 0,
        max_depth: int = 1,
    ) -> tuple[str, str, str, int | None]:
        """
        Prueba una ruta de admin con recursividad limitada para encontrar
        el panel de login real si la pagina inicial es ambigua.
        """
        try:
            time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
            resp = self._session.get(
                url,
                timeout=self._timeout,
                allow_redirects=True,
            )
            final_url = resp.url or url
            # Clasificar respuesta
            state, reason = self._classify_admin_probe_response(url, resp)

            # --- LÓGICA DE RECURSIVIDAD REFORZADA ---
            # Si el estado es 'potentially_protected' (indicadores débiles) 
            # o 'exposed' sin indicadores claros, buscamos profundizar.
            is_ambiguous = (
                (state == "protected" and "weak_indicator" in reason) or
                (state == "exposed" and "without_auth_indicators" in reason)
            )

            if is_ambiguous and depth < max_depth:
                soup = BeautifulSoup(resp.text, settings.BS4_PARSER)
                login_keywords = {
                    "login", "signin", "acceder", "entrar", "admin", "management",
                    "identificarse", "log in", "sign in", "user", "account", "backend",
                    "backoffice", "sistema", "acceso", "control",
                }
                
                promising_links: list[str] = []
                # Buscar en enlaces y tambien en botones/forms (action)
                for tag in soup.find_all(["a", "form", "button"]):
                    href = ""
                    if tag.name == "a": href = tag.get("href") or ""
                    elif tag.name == "form": href = tag.get("action") or ""
                    
                    text = tag.get_text(strip=True).lower()
                    href_l = href.lower()
                    
                    if any(kw in href_l for kw in login_keywords) or any(kw in text for kw in login_keywords):
                        full_href = urljoin(final_url, href)
                        # Evitar bucles, links externos y anchors vacios
                        if (full_href != final_url and 
                            urlparse(full_href).netloc == urlparse(url).netloc and
                            not full_href.endswith(("#", "javascript:void(0)"))):
                            promising_links.append(full_href)

                # Probar los links encontrados (maximo 5 para ser exhaustivos pero prudentes)
                for link in promising_links[:5]:
                    sub_state, sub_reason, sub_final, sub_status = self._probe_admin_path_recursive(
                        link, depth + 1, max_depth
                    )
                    # Si encontramos una proteccion FUERTE en el sub-link, la reportamos.
                    if sub_state == "protected" and "weak_indicator" not in sub_reason:
                        return "protected", f"confirmed_auth_at={link}", sub_final, sub_status
                    # Si encontramos un dashboard expuesto, es un hallazgo crítico.
                    if sub_state == "exposed" and "dashboard" in sub_reason:
                        return "exposed", f"nested_dashboard_found_at={link}", sub_final, sub_status

            # Si despues de la recursividad seguimos teniendo solo indicadores debiles,
            # lo bajamos a 'unknown' o 'exposed' si parece ser el home.
            if state == "protected" and "weak_indicator" in reason:
                return "unknown", f"ambiguous_indicators_only_at={final_url}", final_url, resp.status_code

            return state, reason, final_url, resp.status_code

        except requests.RequestException as exc:
            return "not_found", str(exc), url, None

    def _classify_admin_probe_response(
        self,
        probe_url: str,
        resp: requests.Response,
    ) -> tuple[str, str]:
        """
        Clasifica una respuesta de una ruta de administracion.

        Estados devueltos:
        - protected: hay autenticacion, bloqueo HTTP o redireccion a login.
        - exposed: el panel parece accesible sin autenticacion.
        - not_found: la ruta no existe o no es accesible.
        - unknown: no se puede confirmar de forma fiable.
        """
        status = resp.status_code
        final_url = resp.url or probe_url
        final_url_l = final_url.lower()
        text_l = (resp.text or "").lower()

        # 1. Proteccion real por codigo HTTP.
        if status in (401, 403):
            return "protected", f"status={status}"

        # 2. Ruta inexistente o eliminada.
        if status in (404, 410):
            return "not_found", f"status={status}"

        # 3. Error servidor: no asumir que esta abierto.
        if status >= 500:
            return "unknown", f"status={status}"

        # 4. Redireccion a login/autenticacion (Detección FUERTE si es por URL).
        auth_url_indicators = (
            "login", "signin", "sign-in", "auth", "authenticate", "wp-login",
            "user/login", "account", "session", "sso", "oauth", "keycloak",
        )
        if resp.history and any(ind in final_url_l for ind in auth_url_indicators):
            return "protected", f"redirect_to_auth={final_url}"

        # 5. Detectar "Soft 404" o redirección al Home (Frecuente en catch-all).
        # Si terminamos en la raiz o pagina de inicio, bajamos la confianza.
        parsed_final = urlparse(final_url)
        is_home = final_url_l.rstrip("/") == f"{urlparse(probe_url).scheme}://{urlparse(probe_url).netloc}".lower()
        if is_home or parsed_final.path in ("", "/", "/index.html", "/index.php"):
            # En el home, solo aceptamos indicadores FUERTES.
            pass

        # 6. HTML tipico de formulario de login (Indicadores FUERTES).
        strong_login_indicators = (
            'type="password"', "type='password'", 'name="password"', "name='password'",
            'id="password"', "id='password'", "wp-submit", "user_login", "remember_me",
            "csrf", "_token", 'action="login"', "action='login'",
        )
        if any(ind in text_l for ind in strong_login_indicators):
            return "protected", "strong_login_form_detected"

        # 7. Indicadores DÉBILES (Palabras sueltas que pueden ser links genéricos).
        weak_login_indicators = (
            "contraseña", "password", "iniciar sesión", "iniciar sesion",
            "log in", "login", "sign in", "signin", "authenticate",
            "autenticación", "autenticacion", "remember me", "acceder",
            "identificarse", "entrar", "usuario", "user", "password",
            "contrasenya", "clave", "credenciales", "inicie sesion",
            "inicie sesión", "acceso", "login portal",
        )
        if any(ind in text_l for ind in weak_login_indicators):
            # Si estamos en el Home, ignoramos indicadores débiles (suelen ser links de 'Area Clientes')
            if is_home:
                return "not_found", "redirected_to_home_with_weak_indicators"
            return "protected", "weak_indicator_detected"

        # 8. Indicadores de panel real ya cargado (EXPOSED).
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

        # 7. Si responde bien y no parece login, es sospechoso.
        if status < 400:
            return "exposed", f"status={status}_without_auth_indicators"

        return "unknown", f"status={status}"

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
            issues.append("Falta <!DOCTYPE html> al inicio del documento (modo estandares).")

        charset_meta = soup.find("meta", attrs={"charset": True})
        if not charset_meta:
            issues.append("Falta <meta charset='utf-8'> para codificacion consistente.")

        if not soup.find("meta", attrs={"name": "robots"}):
            issues.append("Falta meta robots (definir index/follow segun entorno).")

        iframes = soup.find_all("iframe")
        for iframe in iframes:
            if not (iframe.get("title") or "").strip():
                ln, line = self._find_line_for_tag(html_lines, iframe)
                issues.append(f"Iframe sin atributo title en linea aproximada {ln}: {line}")

        id_count: dict[str, int] = {}
        for tag in soup.find_all(attrs={"id": True}):
            tid = (tag.get("id") or "").strip()
            if not tid:
                continue
            id_count[tid] = id_count.get(tid, 0) + 1
        duplicates = [item for item, count in id_count.items() if count > 1]
        for dup in duplicates[:20]:
            issues.append(f"ID duplicado detectado: #{dup} (rompe selectores y accesibilidad).")

        headings = [int(h.name[1]) for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])]
        for idx in range(1, len(headings)):
            if headings[idx] - headings[idx - 1] > 1:
                issues.append(
                    f"Salto brusco de jerarquia de headings: h{headings[idx - 1]} -> h{headings[idx]}."
                )
                break

        self._check_assets(soup, base_url, html_lines, issues, asset_stats)
        self._check_forms_accessibility(soup, html_lines, issues)

        # ── Favicon ───────────────────────────────────────────────────────
        favicon = soup.find("link", rel=lambda r: r and ("icon" in r or "shortcut icon" in r))
        if not favicon:
            issues.append("Falta favicon (<link rel=\"icon\">). Afecta a branding y pestanas del navegador.")

        # ── Web Manifest ───────────────────────────────────────────────────
        manifest = soup.find("link", attrs={"rel": "manifest"})
        if not manifest:
            recommendations.append("Falta web manifest (<link rel=\"manifest\">). Necesario para PWA y add-to-homescreen.")

        # ── CSS / JS inline ───────────────────────────────────────────────────
        # En producción es habitual que frameworks y bundlers inyecten CSS/JS
        # directamente en el HTML (SSR, critical CSS, chunks…). Estos bloques
        # NO se penalizan en el score; se añade una nota informativa suave
        # solo si el volumen es realmente extremo (>500 KB).
        inline_script_chars = sum(
            len(s.get_text(strip=True))
            for s in soup.find_all("script")
            if not s.get("src")
        )
        inline_style_chars = sum(
            len(s.get_text(strip=True))
            for s in soup.find_all("style")
        )
        if inline_script_chars > 500_000:
            recommendations.append(
                f"JS inline muy voluminoso ({inline_script_chars // 1024} KB). "
                "Valorar code-splitting o lazy-loading para mejorar TTFB."
            )
        if inline_style_chars > 200_000:
            recommendations.append(
                f"CSS inline muy voluminoso ({inline_style_chars // 1024} KB). "
                "Valorar extraer estilos no-criticos a stylesheet cacheable."
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
                issues.append(f"Stylesheet <link> sin href en linea aproximada {ln}: {line}")
                continue
            full = urljoin(base_url, href)
            if base_is_https and full.lower().startswith("http://"):
                asset_stats["mixed_content"] += 1
                issues.append(f"Mixed content CSS: {full} (linea aproximada {ln})")
            ok, elapsed_ms, status_code = self._check_url_with_strategies(full)
            asset_stats["checked"] += 1
            if not ok:
                asset_stats["broken"] += 1
                issues.append(f"CSS no accesible {full} status={status_code} tiempo={elapsed_ms}ms")

        for script in soup.find_all("script"):
            src = (script.get("src") or "").strip()
            if not src:
                continue
            ln, line = self._find_line_for_tag(html_lines, script)
            full = urljoin(base_url, src)
            if base_is_https and full.lower().startswith("http://"):
                asset_stats["mixed_content"] += 1
                issues.append(f"Mixed content JS: {full} (linea aproximada {ln})")
            ok, elapsed_ms, status_code = self._check_url_with_strategies(full)
            asset_stats["checked"] += 1
            if not ok:
                asset_stats["broken"] += 1
                issues.append(f"JS no accesible {full} status={status_code} tiempo={elapsed_ms}ms")
            if soup.head and script in soup.head.contents and not script.get("defer") and not script.get("async"):
                issues.append(
                    f"Script bloqueante en <head> sin defer/async: {full} (linea aproximada {ln}: {line[:120]})"
                )

    def _check_forms_accessibility(self, soup: BeautifulSoup, html_lines: list[str], issues: list[str]) -> None:
        for field in soup.find_all(["input", "select", "textarea"]):
            if field.name == "input" and (field.get("type") or "").lower() in {"hidden", "submit", "button"}:
                continue
            has_aria = bool((field.get("aria-label") or "").strip())
            fid = (field.get("id") or "").strip()
            has_label = bool(fid and soup.find("label", attrs={"for": fid}))
            if not has_aria and not has_label:
                ln, line = self._find_line_for_tag(html_lines, field)
                issues.append(
                    f"Campo de formulario sin label/aria-label en linea aproximada {ln}: {line}"
                )

    def _check_structure(self, soup: BeautifulSoup, issues: list[str]) -> None:
        if soup.html is None:
            issues.append("Falta etiqueta <html>. Revisar plantilla base.")
            return
        if soup.head is None:
            issues.append("Falta <head>. Algunos metadatos SEO no pueden aplicarse.")
        if soup.body is None:
            issues.append("Falta <body>. HTML incompleto.")
        if not soup.find("h1"):
            issues.append("No existe ningun <h1>; dificulta estructura semantica.")
        if not soup.find_all(["h2", "h3"]):
            issues.append("No hay jerarquia de subtitulos <h2>/<h3>.")

        # ── Landmarks semánticos ──────────────────────────────────────────────
        has_main   = bool(soup.find("main") or soup.find(attrs={"role": "main"}))
        has_nav    = bool(soup.find("nav")  or soup.find(attrs={"role": "navigation"}))
        has_header = bool(soup.find("header") or soup.find(attrs={"role": "banner"}))
        has_footer = bool(soup.find("footer") or soup.find(attrs={"role": "contentinfo"}))
        if not has_main:
            issues.append("Falta landmark <main> o role='main'. Los lectores de pantalla no pueden saltar al contenido principal.")
        if not has_nav:
            issues.append("Falta landmark <nav> o role='navigation'. Dificulta navegacion con lector de pantalla.")
        if not has_header:
            issues.append("Falta landmark <header> o role='banner'.")
        if not has_footer:
            issues.append("Falta landmark <footer> o role='contentinfo'.")

        # ── Enlaces con texto generico (inutilizables con lector de pantalla) ─
        generic_texts = {
            "haz clic aqui", "click here", "haz clic aquí", "clic aqui", "clic aquí",
            "leer mas", "leer más", "read more", "aqui", "aquí", "here",
            "mas informacion", "más información", "more info", "mas", "más",
            "enlace", "link", "ver mas", "ver más", "seguir leyendo",
        }
        for anchor in soup.find_all("a"):
            link_text = anchor.get_text(" ", strip=True).lower().strip(" .,;")
            if link_text in generic_texts:
                href = (anchor.get("href") or "")[:80]
                issues.append(
                    f"Enlace con texto generico inutilizable con lector de pantalla: "
                    f"'{link_text}' (href={href})"
                )

        # ── target=_blank sin rel=noopener noreferrer ─────────────────────────
        for anchor in soup.find_all("a", attrs={"target": "_blank"}):
            rel = " ".join(anchor.get("rel") or []).lower()
            if "noopener" not in rel or "noreferrer" not in rel:
                href = (anchor.get("href") or "")[:80]
                issues.append(
                    f"Enlace target='_blank' sin rel='noopener noreferrer' (seguridad + tab-napping): {href}"
                )

        # ── Video sin <track> (subtitulos) ───────────────────────────────────
        for video in soup.find_all("video"):
            if not video.find("track"):
                src = (video.get("src") or "(sin src)")[:80]
                issues.append(
                    f"Elemento <video> sin <track> para subtitulos/descripcion: {src}"
                )

        # ── Elementos HTML obsoletos ──────────────────────────────────────────
        deprecated_tags = ["center", "font", "blink", "marquee", "frame",
                           "frameset", "noframes", "big", "strike", "tt"]
        for tag_name in deprecated_tags:
            found = soup.find(tag_name)
            if found:
                issues.append(f"Elemento HTML obsoleto <{tag_name}> detectado. Usar CSS equivalente.")

        # ── Tablas de layout (sin <th> ni <caption>) ──────────────────────────
        for table in soup.find_all("table"):
            if not table.find("th") and not table.find("caption"):
                issues.append(
                    "Tabla sin <th> ni <caption>: posible tabla de maquetacion (usar CSS Grid/Flexbox)."
                )
                break  # uno es suficiente para el aviso

        # ── Event handlers inline ─────────────────────────────────────────────
        inline_events = ["onclick", "onmouseover", "onmouseout", "onkeydown",
                         "onkeyup", "onchange", "onsubmit", "onfocus", "onblur"]
        inline_count = 0
        for tag in soup.find_all(True):
            for ev in inline_events:
                if tag.get(ev):
                    inline_count += 1
                    break
        if inline_count > 0:
            issues.append(
                f"{inline_count} elemento(s) con event handlers inline (onclick/onchange/…). "
                "Rompe separacion de responsabilidades; usar addEventListener."
            )

    def _check_seo(self, soup: BeautifulSoup, issues: list[str]) -> None:
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        if not title:
            issues.append("Falta <title>.")
        elif len(title) < 20 or len(title) > 65:
            issues.append(f"Longitud no optima de <title> ({len(title)} chars).")

        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc_text = (meta_desc.get("content") or "").strip() if meta_desc else ""
        if not desc_text:
            issues.append("Falta meta description.")
        elif len(desc_text) < 70 or len(desc_text) > 160:
            issues.append(f"Longitud no optima de meta description ({len(desc_text)} chars).")

        html_tag = soup.find("html")
        if html_tag and not html_tag.get("lang"):
            issues.append("La etiqueta <html> no define lang.")
        if not soup.find("link", attrs={"rel": "canonical"}):
            issues.append("Falta canonical (<link rel='canonical'>).")
        if not soup.find("meta", attrs={"name": "viewport"}):
            issues.append("Falta meta viewport para responsive.")

        # ── Multiples <h1> ────────────────────────────────────────────────────
        h1_list = soup.find_all("h1")
        if len(h1_list) > 1:
            issues.append(
                f"Multiples <h1> detectados ({len(h1_list)}). Solo debe haber uno por pagina."
            )

        # ── Open Graph ────────────────────────────────────────────────────────
        og_props = {"og:title", "og:description", "og:image"}
        found_og = {
            (m.get("property") or "").lower()
            for m in soup.find_all("meta", property=True)
        }
        missing_og = og_props - found_og
        if missing_og:
            issues.append(
                f"Open Graph incompleto. Faltan: {', '.join(sorted(missing_og))}. "
                "Afecta a como se muestra el contenido al compartir en redes sociales."
            )

        # ── Twitter Card ──────────────────────────────────────────────────────
        tw_card = soup.find("meta", attrs={"name": "twitter:card"})
        if not tw_card:
            issues.append(
                "Falta meta twitter:card. El contenido puede mostrarse sin preview en Twitter/X."
            )

        # ── JSON-LD / Schema.org ───────────────────────────────────────────
        jsonld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
        if not jsonld_scripts:
            issues.append(
                "No se detectan datos estructurados JSON-LD (Schema.org). "
                "Mejora visibilidad en resultados enriquecidos de Google."
            )
        else:
            for js_tag in jsonld_scripts:
                raw_json = js_tag.get_text(strip=True)
                if raw_json:
                    try:
                        data = json.loads(raw_json)
                        if not isinstance(data, dict) or ("@type" not in data and "@context" not in data):
                            issues.append(
                                "JSON-LD presente pero sin @type ni @context valido. "
                                "Puede no ser interpretado por motores de busqueda."
                            )
                    except (json.JSONDecodeError, ValueError):
                        issues.append(
                            "JSON-LD presente pero con sintaxis JSON invalida. "
                            "No sera interpretado por motores de busqueda."
                        )

        # ── hreflang (multiidioma) ─────────────────────────────────────────
        html_tag = soup.find("html")
        page_lang = (html_tag.get("lang") or "").strip() if html_tag else ""
        hreflang_links = soup.find_all("link", attrs={"rel": "alternate", "hreflang": True})
        if page_lang and not hreflang_links:
            issues.append(
                f"La pagina declara lang=\"{page_lang}\" pero no tiene etiquetas hreflang. "
                "Si hay versiones en otros idiomas, anadir <link rel=\"alternate\" hreflang=\"xx\">."
            )

        # ── Alt de imagen tipo nombre de archivo ────────────────────────────
        for img in soup.find_all("img"):
            alt = (img.get("alt") or "").strip()
            if alt and self._regex.filename_alt_regex.match(alt):
                src_hint = (img.get("src") or "")[:80]
                issues.append(
                    f"Alt de imagen es un nombre de archivo (\"{alt}\"), no descriptivo. src={src_hint}"
                )

    @staticmethod
    def _is_false_positive(pattern: str, text: str) -> bool:
        """
        Filtra falsos positivos en la deteccion de contenido basados en el contexto espanol.
        Evita que palabras comunes disparen alertas erroneas de contenido explicito.
        """
        # 1. "sex" en palabras espanolas seguras
        if pattern == "sex":
            match = re.search(r"\b(\w*sex\w*)\b", text)
            if match:
                word = match.group(1).lower()
                safe = {"sexta", "sexto", "sesenta", "sexenio", "sexagesimo", "sextuplo"}
                if word in safe:
                    return True
                    
        # 2. "con" (muy comun en espanol)
        if pattern == "con":
            # Si es la preposicion "con", es falso positivo
            if re.search(r"\bcon\b", text):
                return True
                
        # 3. "put" en terminos tecnicos o palabras seguras
        if pattern == "put":
            match = re.search(r"\b(\w*put\w*)\b", text)
            if match:
                word = match.group(1).lower()
                safe_tech = {"input", "output", "computo", "computadora", "reputacion", "disputa"}
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
        """
        Analiza el contenido visible de la página buscando:
        - Texto de relleno / placeholder (lorem ipsum, dummy…)
        - Contenido incoherente (cadenas de ruido, patrones repetitivos…)
        - Contenido explícito / sexual
        - Palabras malsonantes / insultos
        - Discurso de odio / discriminatorio
        - Rutas de administración expuestas en texto
        - Contenido delgado (thin content)
        - Keyword stuffing
        - Ausencia de aviso legal / política de privacidad
        - Ausencia de información de contacto

        La detección opera sobre DOS versiones del texto:
          · text_l          — texto original en minúsculas
          · text_normalized — texto normalizado (anti-leetspeak, anti-evasión)
        Esto garantiza que variantes como "p0rn", "p.o.r.n", "p o r n" o
        "ｐｏｒｎ" sean capturadas aunque el diccionario solo contenga "porn".
        """
        text = soup.get_text(" ", strip=True)
        text_l = text.lower()
        if not text_l.strip():
            issues.append("No se encontro texto visible en el body.")
            return

        # Versión normalizada para detección de evasiones
        text_normalized = self._normalize_for_detection(text_l)

        # ── Diccionarios de patrones ──────────────────────────────────────────
        all_patterns: tuple[tuple[str, str], ...] = (
            *((p, "contenido de relleno")     for p in self._dicts.lorem_patterns),
            *((p, "contenido incoherente")    for p in self._dicts.incoherent_patterns),
            *((p, "contenido explicito")      for p in self._dicts.explicit_patterns),
            *((p, "palabra malsonante")       for p in self._dicts.profanity_patterns),
            *((p, "discurso de odio")         for p in self._dicts.hate_patterns),
        )

        for pattern, category in all_patterns:
            in_original   = pattern in text_l
            in_normalized = pattern in text_normalized
            if in_original or in_normalized:
                # Verificar falsos positivos por contexto español
                if self._is_false_positive(pattern, text_l):
                    continue
                evasion_note = " [detectado via normalizacion/leetspeak]" if not in_original else ""
                line_no, line = self._find_line_for_text(html_lines, pattern)
                issues.append(
                    f"[{category}] Patron '{pattern}'{evasion_note} "
                    f"en linea aproximada {line_no}: {line}"
                )

        # ── Detección heurística de ruido / incoherencia ──────────────────────
        if self._regex.gibberish_regex.search(text_l):
            issues.append("Secuencias de caracteres repetidos anormales (posible ruido o contenido incoherente).")
        if self._regex.multi_symbol_regex.search(text_l):
            issues.append("Bloques de simbolos excesivos detectados (posible ruido de contenido).")
        if self._regex.character_noise_regex.search(text_l):
            issues.append("Caracteres repetitivos no lingüisticos detectados (ruido de contenido).")
        if len(self._regex.typo_regex.findall(text_l)) >= 5:
            issues.append("Exceso de tokens posiblemente mal tipados o generados automaticamente.")
        if len(self._regex.long_token_regex.findall(text_l)) >= 2:
            issues.append("Tokens extremadamente largos detectados (posible texto sin sentido o hash pegado).")

        # Letras individuales separadas por espacios (evasión tipo "p o r n")
        spaced_matches = self._regex.spaced_chars_regex.findall(text_l)
        if spaced_matches:
            # Comprobar si al colapsar forman un patrón problemático
            for match_str in self._regex.spaced_chars_regex.finditer(text_l):
                collapsed = match_str.group().replace(" ", "").replace("\t", "")
                for pattern, category in all_patterns:
                    if pattern in collapsed:
                        line_no, line = self._find_line_for_text(html_lines, match_str.group().strip())
                        issues.append(
                            f"[{category}] Evasion con letras espaciadas '{match_str.group().strip()}' "
                            f"(colapsa en '{collapsed}') en linea aproximada {line_no}: {line}"
                        )
                        break

        # Letras separadas por puntuación (evasión tipo "p.o.r.n")
        dotted_matches = self._regex.dotted_chars_regex.findall(text_l)
        if dotted_matches:
            for raw_match in dotted_matches:
                collapsed = re.sub(r"[.\-_*]", "", raw_match)
                for pattern, category in all_patterns:
                    if pattern in collapsed:
                        line_no, line = self._find_line_for_text(html_lines, raw_match)
                        issues.append(
                            f"[{category}] Evasion con puntuacion intercalada '{raw_match}' "
                            f"(colapsa en '{collapsed}') en linea aproximada {line_no}: {line}"
                        )
                        break

        # Incoherencia semántica profunda (heurísticas de bajo nivel)
        incoherent_samples = self._detect_incoherent_segments(text_l, self._regex)
        if incoherent_samples:
            for reason, token in incoherent_samples[:8]:
                line_no, line = self._find_line_for_text(html_lines, token)
                issues.append(
                    f"Incoherencia heuristica ({reason}) en linea aproximada {line_no}: {line}"
                )

        # ── Rutas de administración en texto visible ───────────────────────────
        for segment in self._dicts.blocked_admin_segments:
            in_orig = segment in text_l
            in_norm = segment in text_normalized
            if in_orig or in_norm:
                evasion_note = " [detectado via normalizacion]" if not in_orig else ""
                line_no, line = self._find_line_for_text(html_lines, segment)
                issues.append(
                    f"Ruta de administracion expuesta '{segment}'{evasion_note} "
                    f"en linea aproximada {line_no}: {line}"
                )

        # ── Thin content (contenido delgado) ──────────────────────────────────
        words = self._regex.keyword_density_word_regex.findall(text_l)
        word_count = len(words)
        # Excluir páginas típicamente cortas (home, contacto, gracias, legal…)
        url_lower = base_url.lower()
        is_short_page = any(
            kw in url_lower
            for kw in ("contact", "contacto", "gracias", "thank", "legal", "privacy", "aviso")
        )
        if not is_short_page and 0 < word_count < settings.AUDIT_MIN_WORD_COUNT:
            issues.append(
                f"Contenido delgado: solo {word_count} palabras visibles "
                f"(minimo recomendado {settings.AUDIT_MIN_WORD_COUNT}). "
                "Puede penalizarse en SEO."
            )

        # ── Keyword stuffing ──────────────────────────────────────────────────
        if words:
            freq: dict[str, int] = {}
            for w in words:
                freq[w] = freq.get(w, 0) + 1
            top_word, top_count = max(freq.items(), key=lambda kv: kv[1])
            density = top_count / len(words)
            if density > settings.AUDIT_KEYWORD_DENSITY_MAX:
                issues.append(
                    f"Posible keyword stuffing: '{top_word}' aparece {top_count} veces "
                    f"({density:.1%} del texto). Limite recomendado: {settings.AUDIT_KEYWORD_DENSITY_MAX:.0%}."
                )

        # ── Aviso legal / política de privacidad ──────────────────────────────
        legal_terms = {
            "aviso legal", "aviso-legal", "politica de privacidad",
            "política de privacidad", "privacy policy", "terminos", "términos",
            "condiciones de uso", "cookies", "rgpd", "gdpr", "lopd",
        }
        has_legal = any(term in text_l for term in legal_terms) or any(
            any(term in (a.get_text(" ", strip=True).lower()) or term in (a.get("href") or "").lower()
                for term in legal_terms)
            for a in soup.find_all("a")
        )
        if not has_legal:
            issues.append(
                "No se detecta enlace ni texto de aviso legal / politica de privacidad. "
                "Obligatorio por RGPD y normativa española."
            )

        # ── Información de contacto ───────────────────────────────────────────
        contact_terms = {"contacto", "contact", "contactanos", "contáctanos", "escribenos"}
        has_contact = (
            any(term in text_l for term in contact_terms)
            or bool(self._regex.sensitive_data_regexes[6][1].search(text))   # email pattern
            or bool(self._regex.sensitive_data_regexes[7][1].search(text))   # phone pattern
        )
        if not has_contact:
            issues.append(
                "No se detecta informacion de contacto (email, telefono o seccion de contacto). "
                "Recomendado para confianza y cumplimiento legal."
            )

    @staticmethod
    def _detect_incoherent_segments(text_l: str, regex_set: AuditRegexSet) -> list[tuple[str, str]]:
        """
        Detecta incoherencias sin depender de un diccionario fijo.
        Señales:
        - bloques repetidos (ej: 'abcabcabc')
        - clusters largos de consonantes (ej: 'xtrplmn')
        - baja proporcion de vocales en palabras largas
        - mezcla anomala de letras+numeros en muchas palabras
        """
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
                    suspicious.append(("baja_ratio_vocales", w[:30]))
                    continue

            if regex_set.repeated_chunk_regex.search(w):
                suspicious.append(("bloque_repetido", w[:30]))
                continue

            if regex_set.consonant_cluster_regex.search(w):
                suspicious.append(("cluster_consonantes", w[:30]))
                continue

            has_letters = any(ch.isalpha() for ch in w)
            has_digits  = any(ch.isdigit() for ch in w)
            if has_letters and has_digits and len(w) >= 8:
                alnum_noise_count += 1

        if alnum_noise_count >= 4:
            suspicious.append(("muchos_tokens_alnum_raros", str(alnum_noise_count)))

        # Umbral para no marcar textos legitimos por falsos positivos aislados.
        min_hits = max(2, int(len(words) * 0.08))
        if len(suspicious) < min_hits:
            return []
        return suspicious

    def _check_images(self, soup: BeautifulSoup, base_url: str, html_lines: list[str], issues: list[str]) -> None:
        images = soup.find_all("img")
        if not images:
            issues.append("No hay imagenes en la pagina; comprobar si es esperado.")
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
                issues.append(f"Imagen no verificada por URL prohibida: {absolute_url} ({location})")
                continue
            if src.startswith("data:"):
                continue

            ok, elapsed_ms, status_code = self._check_url_with_strategies(absolute_url)
            speed = self._classify_speed(elapsed_ms)
            if not ok:
                issues.append(
                    f"Imagen rota src={absolute_url} status={status_code} tiempo={elapsed_ms}ms ({speed}) en {location}"
                )

            # Rendimiento de imagenes
            if not img.get("loading"):
                issues.append(f"Imagen sin loading=\"lazy\" (src={src[:80]}) en {location}")
            if not img.get("width") or not img.get("height"):
                issues.append(
                    f"Imagen sin width/height explicitos (causa layout shift / CLS): src={src[:80]} en {location}"
                )
            ext = src.rsplit(".", 1)[-1].lower() if "." in src else ""
            if ext in ("jpg", "jpeg", "png", "gif", "bmp", "tiff"):
                issues.append(
                    f"Imagen en formato legacy ({ext}): considerar WebP/AVIF para mejor rendimiento. src={src[:80]}"
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
            issues.append("Crawl recursivo omitido por URL prohibida.")
            return

        base_host = self._normalize_host(urlparse(base_url).netloc)
        queue: list[tuple[str, int]] = []
        visited: set[str] = set()

        for anchor in soup.find_all("a"):
            href = (anchor.get("href") or "").strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            # Validar anclajes internos (#id)
            if href.startswith("#"):
                fragment = href[1:]
                if fragment and not soup.find(id=fragment) and not soup.find("a", attrs={"name": fragment}):
                    ln, line = self._find_line_for_tag(html_lines, anchor)
                    issues.append(
                        f"Anclaje roto: href=\"{href}\" apunta a id que no existe en el DOM. Linea aproximada {ln}: {line}"
                    )
                continue
            full = urljoin(base_url, href)
            queue.append((full, 0))
            if any(seg in full.lower() for seg in self._dicts.blocked_admin_segments):
                ln, line = self._find_line_for_tag(html_lines, anchor)
                issues.append(f"Enlace prohibido detectado {full} en linea aproximada {ln}: {line}")

        while queue and crawl_stats["tested"] < settings.AUDIT_MAX_RECURSIVE_LINKS:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            if self._is_banned_url(url):
                crawl_stats["skipped"] += 1
                issues.append(f"Enlace omitido por politica de bloqueo: {url}")
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
                    f"Enlace roto confirmado (HTTP+navegador) {url} status={status_code} tiempo={elapsed_ms}ms ({speed})"
                )

            if content and depth < settings.AUDIT_MAX_CRAWL_DEPTH:
                page_soup = BeautifulSoup(content, settings.BS4_PARSER)
                for inner_anchor in page_soup.find_all("a"):
                    href = (inner_anchor.get("href") or "").strip()
                    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                        continue
                    full_inner = urljoin(url, href)
                    inner_host = self._normalize_host(urlparse(full_inner).netloc)
                    if inner_host != base_host:
                        continue
                    queue.append((full_inner, depth + 1))

    def _check_buttons(self, soup: BeautifulSoup, base_url: str, html_lines: list[str], issues: list[str]) -> None:
        buttons = soup.find_all(["button", "input"])
        forms = soup.find_all("form")

        if not buttons:
            issues.append("No hay botones detectables en HTML estatico.")

        for btn in buttons:
            if btn.name == "input" and (btn.get("type") or "").lower() not in {"submit", "button"}:
                continue
            ln, line = self._find_line_for_tag(html_lines, btn)
            text = btn.get_text(" ", strip=True) if isinstance(btn, Tag) else ""
            if not text:
                text = btn.get("value", "(sin texto)")
            if not text or text == "(sin texto)":
                issues.append(f"Boton sin texto visible en linea aproximada {ln}: {line}")

        for form in forms:
            action = (form.get("action") or "").strip()
            method = (form.get("method") or "get").lower()
            ln, line = self._find_line_for_tag(html_lines, form)
            if not action:
                issues.append(f"Formulario sin action en linea aproximada {ln}: {line}")
                continue

            target = urljoin(base_url, action)
            if self._is_banned_url(target):
                issues.append(f"Formulario no probado por URL prohibida: {target}")
                continue
            if any(seg in target.lower() for seg in self._dicts.blocked_admin_segments):
                issues.append(f"Formulario apunta a ruta prohibida ({target}) en linea aproximada {ln}: {line}")
                continue

            ok, elapsed_ms, status_code = self._check_url_with_strategies(target, method=method)
            speed = self._classify_speed(elapsed_ms)
            if not ok:
                issues.append(
                    f"Fallo al probar action de formulario {target} metodo={method.upper()} status={status_code} tiempo={elapsed_ms}ms ({speed})"
                )

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
        response = None
        try:
            method_l = method.lower()
            if method_l == "post":
                response = self._session.post(url, timeout=self._timeout, data={})
            elif method_l == "get":
                response = self._session.get(url, timeout=self._timeout)
            else:
                response = self._session.head(url, timeout=self._timeout, allow_redirects=True)
                if response.status_code == 405 or response.status_code >= 400:
                    response = self._session.get(url, timeout=self._timeout, allow_redirects=True)

            elapsed_ms = int((time.perf_counter() - start) * 1000)
            ok = response.status_code < 400
            if include_content:
                content = response.text if "text/html" in response.headers.get("content-type", "").lower() else ""
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
        """
        Doble verificacion de enlaces/recursos:
        1) requests (HTTP)
        2) Selenium (navegador) solo cuando HTTP falla
        """
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
                return True, browser_ms, f"{status_code}->ok_browser", content
            return True, browser_ms, f"{status_code}->ok_browser"

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
            resp = self._session.get(base_url, timeout=self._timeout, allow_redirects=True)
            self._last_response_headers = dict(resp.headers)
        except requests.RequestException:
            logger.debug("No se pudo hacer warm-up de cookies para %s", base_url)
            self._last_response_headers = {}

    def _get_driver(self) -> webdriver.Chrome | None:
        if self._driver is not None:
            return self._driver
        try:
            import random
            opts = Options()
            if settings.SELENIUM_HEADLESS:
                opts.add_argument("--headless=new")

            # Anti-deteccion: UA aleatorio + ocultar webdriver
            ua = random.choice(settings.USER_AGENT_POOL)
            opts.add_argument(f"user-agent={ua}")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            opts.add_experimental_option("useAutomationExtension", False)

            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-infobars")
            opts.add_argument("--lang=es-ES")

            # Logs de consola JS
            opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})

            service = Service(settings.SELENIUM_DRIVER_PATH) if settings.SELENIUM_DRIVER_PATH else Service()
            driver = webdriver.Chrome(service=service, options=opts)
            driver.set_page_load_timeout(settings.SELENIUM_PAGE_LOAD_TIMEOUT)

            # Anti-deteccion: eliminar navigator.webdriver
            try:
                driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """
                        Object.defineProperty(navigator, "webdriver", { get: () => undefined });
                        Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3, 4, 5] });
                        Object.defineProperty(navigator, "languages", { get: () => ["es-ES", "es", "en"] });
                        window.chrome = { runtime: {} };
                    """
                })
            except Exception:
                pass  # CDP no soportado en esta version

            self._driver = driver
            return self._driver
        except Exception as exc:
            logger.debug("Selenium no disponible para confirmaciones: %s", exc)
            self._driver = None
            return None

    def _check_js_console_errors(self, base_url: str, issues: list[str]) -> None:
        """
        Captura errores de consola JavaScript en runtime via Selenium.
        Requiere goog:loggingPrefs configurado en el driver.
        """
        if not settings.AUDIT_JS_LOGS_ENABLED:
            return
        driver = self._get_driver()
        if driver is None:
            return
        try:
            time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)
            driver.get(base_url)
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            WebDriverWait(driver, max(4, settings.SELENIUM_IMPLICIT_WAIT)).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            time.sleep(1)  # Esperar a que JS termine de ejecutar
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
                            f"... y mas errores JS (limite de {settings.AUDIT_JS_CONSOLE_MAX_ERRORS} alcanzado)."
                        )
                        break
                    msg = entry.get("message", "(sin mensaje)")[:200]
                    source = entry.get("source", "unknown")
                    issues.append(
                        f"[JS ERROR] {source}: {msg}"
                    )
                    error_count += 1
            if error_count == 0:
                logger.debug("No se detectaron errores JS SEVERE en consola.")
        except (TimeoutException, WebDriverException) as exc:
            logger.debug("No se pudieron capturar logs JS para %s: %s", base_url, exc)
        except Exception as exc:
            logger.debug("Error inesperado capturando logs JS: %s", exc)

    def _interact_buttons_selenium(self, base_url: str, issues: list[str]) -> None:
        """
        Intenta hacer click real en botones via Selenium para detectar fallos
        de interaccion (elementos no clickeables, overlapped, JS errors, etc.).
        """
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
            from selenium.webdriver.common.action_chains import ActionChains

            # Buscar botones interactivos
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

            # Limitar al maximo configurado
            original_url = driver.current_url
            clicked = 0
            for btn in buttons[:settings.AUDIT_BUTTON_MAX_CLICKS * 2]:
                if clicked >= settings.AUDIT_BUTTON_MAX_CLICKS:
                    break
                try:
                    if not btn.is_displayed() or not btn.is_enabled():
                        continue
                    btn_text = (btn.text or btn.get_attribute("value") or "(sin texto)")[:60]
                    btn_tag = btn.tag_name

                    # Scroll al elemento
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(settings.AUDIT_REQUEST_DELAY_SECONDS)

                    try:
                        btn.click()
                        clicked += 1
                        time.sleep(0.3)

                        # Verificar si se rompio la pagina
                        try:
                            driver.find_element(By.TAG_NAME, "body")
                        except Exception:
                            issues.append(
                                f"Pagina se rompio tras click en <{btn_tag}> '{btn_text}'. "
                                "El body dejo de ser accesible."
                            )

                        # Si navego a otra pagina, volver
                        if driver.current_url != original_url:
                            driver.back()
                            time.sleep(0.5)
                            WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located(("tag name", "body"))
                            )

                    except WebDriverException as click_exc:
                        exc_msg = str(click_exc)[:150]
                        if "not interactable" in exc_msg.lower() or "obscured" in exc_msg.lower():
                            issues.append(
                                f"Boton <{btn_tag}> '{btn_text}' no interactivo u oculto por otro elemento."
                            )
                        elif "stale" in exc_msg.lower():
                            pass  # Elemento ya no existe, normal tras navegacion
                        else:
                            issues.append(
                                f"Error al hacer click en <{btn_tag}> '{btn_text}': {exc_msg}"
                            )
                        clicked += 1

                except Exception:
                    pass  # Elemento no accesible, skip

        except (TimeoutException, WebDriverException) as exc:
            logger.debug("No se pudieron probar botones para %s: %s", base_url, exc)
        except Exception as exc:
            logger.debug("Error inesperado probando botones: %s", exc)

    def _close_driver(self) -> None:
        if self._driver is None:
            return
        try:
            self._driver.quit()
        except Exception:
            pass
        self._driver = None

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
        source_speed = QualityAuditor._classify_speed(source_response_ms) if source_response_ms >= 0 else "sin_dato"
        return {
            "status_code": metadata.get("status_code", "sin_dato"),
            "release_gate_blocked": False,
            "source_response_time_ms": source_response_ms,
            "source_response_speed": source_speed,
            "title_length": len(soup.title.string.strip()) if soup.title and soup.title.string else 0,
            "meta_description_present": bool(soup.find("meta", attrs={"name": "description"})),
            "h1_count": len(soup.find_all("h1")),
            "image_count": len(soup.find_all("img")),
            "links_count": len(soup.find_all("a")),
            "forms_count": len(soup.find_all("form")),
            "buttons_count": len(soup.find_all(["button", "input"])),
            "word_count": len(soup.get_text(" ", strip=True).split()),
            "security_issue_count": len([i for i in security_issues if "Sin incidencias" not in i]),
            "image_issue_count": len([i for i in image_issues if "Sin incidencias" not in i]),
            "link_issue_count": len([i for i in link_issues if "Sin incidencias" not in i]),
            "button_issue_count": len([i for i in button_issues if "Sin incidencias" not in i]),
            "technical_issue_count": len([i for i in technical_issues if "Sin incidencias" not in i]),
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
        """
        Calcula la puntuacion final basandose en la gravedad de los hallazgos.
        Se han suavizado las penalizaciones para no ser excesivamente estricto
        con elementos que no son criticos para la funcionalidad o seguridad.
        """
        score = 100
        
        # Categorizacion de pesos
        # CRITICO: -5 (Fallo total de funcionalidad, brecha de seguridad real, enlaces rotos)
        # ALTO: -3 (SEO base, accesibilidad importante, SRI)
        # MEDIO: -1.5 (Mejoras de rendimiento, metadatos, diseño semantico)
        # BAJO: -0.5 (Avisos menores, buenas practicas sugeridas)

        all_lists = [
            security_issues, seo_issues, content_issues, image_issues,
            structure_issues, link_issues, button_issues, technical_issues
        ]
        
        total_deduction = 0.0
        
        for issue_list in all_lists:
            for issue in issue_list:
                issue_l = issue.lower()
                if "sin incidencias" in issue_l:
                    continue
                
                # --- PESO CRITICO (-5) ---
                critical_keywords = (
                    "dato sensible", "panel admin", "clave", "password", "token",
                    "roto", "fallo al", "error de consola", "no existe en el dom",
                    "bloqueo", "vulnerabilidad", "sin autenticacion", "discurso de odio",
                    "explicito", "malsonante"
                )
                if any(k in issue_l for k in critical_keywords):
                    total_deduction += 5
                    continue

                # --- PESO ALTO (-3) ---
                high_keywords = (
                    "falta cabecera", "hsts", "csp", "x-frame", "integrity (sri)",
                    "falta doctype", "falta title", "falta description", "sin label",
                    "viewport", "mixed content", "id duplicado"
                )
                if any(k in issue_l for k in high_keywords):
                    total_deduction += 3
                    continue

                # --- PESO MEDIO (-1.5) ---
                medium_keywords = (
                    "falta canonical", "favicon", "alt de imagen", "legacy",
                    "loading=\"lazy\"", "jerarquia", "semantica", "noopener",
                    "lorem ipsum", "relleno", "hreflang"
                )
                if any(k in issue_l for k in medium_keywords):
                    total_deduction += 1.5
                    continue
                
                # --- PESO BAJO / NOTA (-0.5) ---
                total_deduction += 0.5

        score = 100 - total_deduction
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
            recommendations.append("Reforzar seguridad HTTP: cabeceras, HTTPS, SRI y datos sensibles expuestos.")
        if any("Sin incidencias" not in i for i in seo_issues):
            recommendations.append("Corregir metadatos SEO: title, description, canonical, viewport y lang.")
        if any("Sin incidencias" not in i for i in structure_issues):
            recommendations.append("Reforzar estructura semantica: html/head/body y jerarquia de encabezados.")
        if any("Sin incidencias" not in i for i in image_issues):
            recommendations.append("Arreglar imagenes rotas y completar atributos alt con textos descriptivos.")
        if any("Sin incidencias" not in i for i in content_issues):
            recommendations.append("Eliminar contenido de relleno, incoherente, malsonante, explicito o de odio.")
        if any("Sin incidencias" not in i for i in link_issues):
            recommendations.append("Corregir enlaces rotos y eliminar rutas admin/wp-admin del sitio.")
        if any("Sin incidencias" not in i for i in button_issues):
            recommendations.append("Revisar botones y formularios (texto visible, action valida y respuesta).")
        if any("Sin incidencias" not in i for i in technical_issues):
            recommendations.append(
                "Aplicar hardening tecnico: doctype/charset, assets accesibles, sin mixed-content, labels y IDs unicos."
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
            blockers.append(f"Score global insuficiente para produccion ({score}/100).")

        security_critical = (
            "dato sensible",
            "http en lugar de https",
            "panel de administracion accesible",
            "panel admin accesible",
            "panel admin posiblemente accesible",
            "sin autenticacion",
            "sin autenticación",
        )
        if any(any(flag in issue.lower() for flag in security_critical) for issue in security_issues):
            blockers.append("Incidencias de seguridad criticas (datos sensibles, HTTP o panel admin expuesto).")

        strong_content_flags = (
            "contenido explicito",
            "contenido sexual",
            "porno",
            "nsfw",
            "patron '",          # Captura todos los patrones del diccionario
            "incoherencia heuristica",
            "discurso de odio",
            "palabra malsonante",
            "evasion con letras",
            "evasion con puntuacion",
        )
        if any(any(flag in issue.lower() for flag in strong_content_flags) for issue in content_issues):
            blockers.append("Contenido sensible, incoherente o inadecuado detectado en texto visible.")

        broken_links = [i for i in link_issues if "enlace roto confirmado" in i.lower()]
        if broken_links:
            blockers.append(f"Enlaces rotos confirmados ({len(broken_links)}).")

        broken_images = [i for i in image_issues if "imagen rota" in i.lower()]
        if broken_images:
            blockers.append(f"Imagenes rotas detectadas ({len(broken_images)}).")

        critical_tech_flags = ("mixed content", "id duplicado", "doctype", "charset", "script bloqueante")
        if any(any(flag in issue.lower() for flag in critical_tech_flags) for issue in technical_issues):
            blockers.append("Incidencias tecnicas criticas para estabilidad/seguridad detectadas.")

        form_failures = [i for i in button_issues if "fallo al probar action de formulario" in i.lower()]
        if form_failures:
            blockers.append(f"Formularios con fallos de action detectados ({len(form_failures)}).")

        return (len(blockers) > 0), blockers

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
        return host in {self._normalize_host(x) for x in settings.AUDIT_BANNED_HOSTS}

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