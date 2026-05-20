"""
auditor_modules/core.py — Core QualityAuditor class and main methods.
"""
import json
import re
import time
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
from ..dictionaries import build_audit_dictionaries
from ..models import QualityAuditReport
from ..regex import AuditRegexSet, LEET_TRANSLATION_TABLE, build_audit_regex_set
from ..checks import (
    check_security, check_structure, check_seo, check_content, check_images,
    check_links_recursive, check_buttons, check_technical, check_js_console_errors,
    interact_buttons_selenium
)
from .helpers import (
    is_banned_url, warm_up_cookies, close_driver, ensure_non_empty,
    collect_metrics, check_url, classify_speed, find_line
)
from ..scoring import (
    calculate_score, status_from_score, evaluate_release_gate,
    build_recommendations
)

logger = setup_logger(__name__)


class QualityAuditor:
    def __init__(self, timeout: int = settings.REQUEST_TIMEOUT):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(settings.DEFAULT_HEADERS)
        self._dicts = build_audit_dictionaries()
        self._regex = build_audit_regex_set()
        self._driver: webdriver.Chrome | None = None
        self._browser_confirms = 0
        self._max_browser_confirms = settings.AUDIT_MAX_BROWSER_CONFIRMS
        self._last_response_headers: dict = {}

    def build_report(self, html: str, base_url: str, metadata: dict | None = None, on_progress: callable = None) -> QualityAuditReport:
        metadata = metadata or {}
        self._browser_confirms = 0
        self._last_response_headers = {}
        
        total_steps = 8
        current_step = 0

        def update_progress():
            nonlocal current_step
            current_step += 1
            if on_progress:
                on_progress(current_step, total_steps)

        # 1. Notificar inicio inmediato (0/8)
        if on_progress:
            on_progress(0, total_steps)

        # Inicialización de recolectores
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
        crawl_stats = {"tested": 0, "broken": 0, "skipped": 0}

        try:
            # Parseo inicial
            html_lines = html.splitlines()
            soup = BeautifulSoup(html, settings.BS4_PARSER)

            # Comprobar si la página no está operativa (mantenimiento, error HTTP o plantilla por defecto)
            status_code = metadata.get("status_code", 200)
            is_inoperative = False
            inoperative_reason = ""

            title_str = (soup.title.string or "").strip().lower() if soup.title else ""
            h1_text = " ".join([h1.get_text(" ", strip=True).lower() for h1 in soup.find_all("h1")])
            h2_text = " ".join([h2.get_text(" ", strip=True).lower() for h2 in soup.find_all("h2")])
            body_text = soup.get_text(" ", strip=True).lower()
            words = body_text.split()
            word_count = len(words)

            if isinstance(status_code, int) and status_code >= 400:
                is_inoperative = True
                inoperative_reason = f"El código de estado HTTP {status_code} indica un error del servidor o del cliente."
            else:
                err_patterns = [
                    "404 not found", "page not found", "página no encontrada", "pagina no encontrada",
                    "internal server error", "500 error", "502 bad gateway", "503 service unavailable",
                    "error de conexión", "error de conexion", "database error", "fallo de conexión",
                    "connection error", "access denied", "forbidden", "no autorizado"
                ]
                maint_patterns = [
                    "mantenimiento", "maintenance", "en construcción", "en construccion",
                    "under construction", "coming soon", "próximamente", "proximamente",
                    "volveremos pronto", "back soon", "temporarily down", "sitio inactivo"
                ]
                parking_patterns = [
                    "welcome to nginx", "apache2 ubuntu default page", "apache2 debian default page",
                    "iis windows server", "hosting account suspended", "cuenta suspendida",
                    "plesk default page", "cpanel hosting", "default website page"
                ]

                if any(p in title_str for p in err_patterns):
                    is_inoperative = True
                    inoperative_reason = f"El título de la página ('{soup.title.string}') indica un estado de error."
                elif any(p in title_str for p in maint_patterns):
                    is_inoperative = True
                    inoperative_reason = f"El título de la página ('{soup.title.string}') indica que el sitio está en mantenimiento."
                elif any(p in title_str for p in parking_patterns):
                    is_inoperative = True
                    inoperative_reason = f"El título de la página ('{soup.title.string}') corresponde a una plantilla de servidor por defecto."
                elif word_count < 250:
                    if any(p in h1_text for p in err_patterns) or any(p in h2_text for p in err_patterns):
                        is_inoperative = True
                        inoperative_reason = "El encabezado principal indica un error del sistema en una página con poco contenido."
                    elif any(p in h1_text for p in maint_patterns) or any(p in h2_text for p in maint_patterns):
                        is_inoperative = True
                        inoperative_reason = "El encabezado principal indica que el sitio está en mantenimiento."
                    elif any(p in h1_text for p in parking_patterns) or any(p in h2_text for p in parking_patterns):
                        is_inoperative = True
                        inoperative_reason = "El encabezado corresponde a una plantilla de servidor o hosting por defecto."

            if is_inoperative:
                warning_msg = f"Sitio web no operativo: {inoperative_reason}"
                technical_issues.append(warning_msg)
                content_issues.append(warning_msg)
                recommendations.append("Asegurar que el servidor web responda correctamente y desactivar el modo mantenimiento para permitir la auditoría.")

            if is_banned_url(base_url):
                warning = f"URL prohibida para pruebas de red por politica: {base_url}"
                link_issues.append(warning)
                recommendations.append("Cambiar URL objetivo por un dominio permitido.")
            else:
                logger.info("🍪 Realizando cookie warm-up para %s", base_url)
                warm_up_cookies(self._session, base_url)

            # Fase 1: Seguridad
            logger.info("🛡️ [Fase 1/8] Iniciando análisis de Seguridad para %s", base_url)
            check_security(
                html=html, soup=soup, base_url=base_url, issues=security_issues,
                session=self._session, last_response_headers=self._last_response_headers,
                timeout=self._timeout, regex_set=self._regex, driver_factory=self._get_driver
            )
            update_progress()

            # Fase 2: Estructura y SEO
            logger.info("📐 [Fase 2/8] Iniciando análisis de Estructura de encabezados")
            check_structure(soup=soup, issues=structure_issues)
            update_progress()
            
            logger.info("🔍 [Fase 3/8] Iniciando análisis de SEO y meta-etiquetas")
            check_seo(soup=soup, issues=seo_issues, regex_set=self._regex)
            update_progress()

            # Fase 3: Contenido
            logger.info("📝 [Fase 4/8] Iniciando análisis de Contenido y legibilidad")
            check_content(
                soup=soup, issues=content_issues, html_lines=html_lines, base_url=base_url,
                dicts=self._dicts, regex_set=self._regex, 
                normalize_fn=self._normalize_for_detection, find_line_fn=find_line
            )
            update_progress()

            # Fase 4: Imagenes
            logger.info("🖼️ [Fase 5/8] Iniciando análisis de Imágenes rotas y etiquetas alt")
            check_images(
                soup=soup, base_url=base_url, html_lines=html_lines, issues=image_issues,
                is_banned_fn=is_banned_url, check_url_fn=lambda url, **kwargs: check_url(self._session, url, **kwargs),
                classify_speed_fn=classify_speed, find_line_fn=find_line
            )
            update_progress()

            # Fase 5: Enlaces
            logger.info("🔗 [Fase 6/8] Iniciando rastreo recursivo y comprobación de Enlaces rotos (máx: %d)", settings.AUDIT_MAX_RECURSIVE_LINKS)
            check_links_recursive(
                soup=soup, base_url=base_url, html_lines=html_lines, issues=link_issues,
                crawl_stats=crawl_stats, is_banned_fn=is_banned_url,
                check_url_fn=lambda url, **kwargs: check_url(self._session, url, **kwargs),
                classify_speed_fn=classify_speed, find_line_fn=find_line,
                blocked_admin_segments=settings.AUDIT_ADMIN_PROBE_PATHS
            )
            update_progress()

            # Fase 6: Botones
            logger.info("🔘 [Fase 7/8] Iniciando análisis de Botones y accesibilidad de formularios")
            check_buttons(
                soup=soup, base_url=base_url, html_lines=html_lines, issues=button_issues,
                is_banned_fn=is_banned_url, check_url_fn=lambda url, **kwargs: check_url(self._session, url, **kwargs),
                classify_speed_fn=classify_speed, find_line_fn=find_line,
                blocked_admin_segments=settings.AUDIT_ADMIN_PROBE_PATHS
            )
            update_progress()

            # Fase 7: Tecnico + Browser
            logger.info("⚙️ [Fase 8/8] Iniciando análisis Técnico, recursos CSS/JS y errores de consola")
            check_technical(
                html=html, soup=soup, base_url=base_url, html_lines=html_lines,
                issues=technical_issues, asset_stats=asset_stats, recommendations=recommendations,
                is_banned_fn=is_banned_url, check_url_fn=lambda url, **kwargs: check_url(self._session, url, **kwargs),
                classify_speed_fn=classify_speed, find_line_fn=find_line
            )
            if not is_banned_url(base_url):
                logger.info("🌐 Iniciando driver de Selenium para interactividad en navegador y logs de consola")
                driver = self._get_driver()
                check_js_console_errors(driver, base_url, technical_issues)
                interact_buttons_selenium(driver, base_url, button_issues, self)
            update_progress()

        finally:
            close_driver(self)

        ensure_non_empty("security_issues", security_issues)
        ensure_non_empty("seo_issues", seo_issues)
        ensure_non_empty("content_issues", content_issues)
        ensure_non_empty("image_issues", image_issues)
        ensure_non_empty("structure_issues", structure_issues)
        ensure_non_empty("link_issues", link_issues)
        ensure_non_empty("button_issues", button_issues)
        ensure_non_empty("technical_issues", technical_issues)

        # Calcular score y estado final
        score = calculate_score(
            security_issues, seo_issues, content_issues, image_issues,
            structure_issues, link_issues, button_issues, technical_issues
        )
        status = status_from_score(score)
        
        is_blocked, blockers = evaluate_release_gate(
            score=score,
            security_issues=security_issues,
            content_issues=content_issues,
            link_issues=link_issues,
            technical_issues=technical_issues,
            image_issues=image_issues,
            button_issues=button_issues
        )

        final_recommendations = build_recommendations(
            security_issues=security_issues, 
            seo_issues=seo_issues, 
            content_issues=content_issues, 
            image_issues=image_issues, 
            structure_issues=structure_issues, 
            link_issues=link_issues, 
            button_issues=button_issues, 
            technical_issues=technical_issues
        )
        final_recommendations.extend(recommendations)

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
            release_blocked=is_blocked,
            release_blockers=blockers,
            recommendations=list(set(final_recommendations)),
            metrics=collect_metrics(
                soup, metadata, security_issues, image_issues, 
                link_issues, button_issues, technical_issues,
                crawl_stats, asset_stats
            )
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
    # SELENIUM HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _get_driver(self):
        if self._driver:
            return self._driver
        
        options = Options()
        if settings.SELENIUM_HEADLESS:
            options.add_argument("--headless=new")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f"user-agent={settings.USER_AGENT_POOL[0]}")
        options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
        
        try:
            self._driver = webdriver.Chrome(options=options)
            self._driver.set_page_load_timeout(settings.SELENIUM_PAGE_LOAD_TIMEOUT)
            self._driver.implicitly_wait(settings.SELENIUM_IMPLICIT_WAIT)
            return self._driver
        except Exception as e:
            logger.error("No se pudo iniciar el driver de Selenium: %s", e)
            return None

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