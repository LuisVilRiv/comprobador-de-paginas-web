"""
auditor_modules/core.py — Core QualityAuditor class and main methods.
"""

import re
from collections.abc import Callable

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from config import settings
from config.logging_config import setup_logger

from ..checks import (
    check_buttons,
    check_content,
    check_images,
    check_js_console_errors,
    check_links_recursive,
    check_security,
    check_seo,
    check_structure,
    check_technical,
    check_url,
    interact_buttons_selenium,
)
from ..dictionaries import build_audit_dictionaries
from ..models import QualityAuditReport
from ..regex import LEET_TRANSLATION_TABLE, build_audit_regex_set
from ..scoring import build_recommendations, calculate_score, evaluate_release_gate, status_from_score
from .helpers import (
    classify_speed,
    close_driver,
    collect_metrics,
    ensure_non_empty,
    find_line,
    is_banned_url,
    warm_up_cookies,
)

logger = setup_logger(__name__)

EDUCATIONAL_CONTEXT_TERMS = (
    "codigo de estado",
    "código de estado",
    "http status",
    "status code",
    "response status",
    "reason phrase",
    "request method",
    "http semantics",
    "ietf",
    "internet engineering task force",
    "rfc",
    "wikipedia",
    "enciclopedia",
    "documentacion",
    "documentación",
    "documentation",
    "definicion",
    "definición",
    "que es",
    "qué es",
    "ejemplo",
    "especificacion",
    "especificación",
    "normative",
    "informative",
)

# Umbrales: las páginas de error típicas son cortas; un RFC tiene miles de palabras.
MAX_BODY_STRONG_ERROR_WORDS = 900

SPEC_TECHNICAL_CUES = (
    "status code",
    "response status",
    "request method",
    "reason phrase",
    "request-target",
    "http/",
    "http semantics",
)

ERROR_CONTEXT_TERMS = (
    "error",
    "not found",
    "forbidden",
    "service unavailable",
    "internal server",
    "bad gateway",
    "gateway timeout",
    "acceso denegado",
    "pagina no encontrada",
    "página no encontrada",
    "no disponible",
    "fuera de servicio",
    "mantenimiento",
    "temporarily",
    "unavailable",
    "try again later",
    "cloudflare",
    "blocked",
)


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

    def build_report(
        self, html: str, base_url: str, metadata: dict | None = None, on_progress: Callable | None = None
    ) -> QualityAuditReport:
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
            inoperative_hard_signal = False

            title_str = (soup.title.string or "").strip().lower() if soup.title else ""
            h1_text = " ".join([h1.get_text(" ", strip=True).lower() for h1 in soup.find_all("h1")])
            h2_text = " ".join([h2.get_text(" ", strip=True).lower() for h2 in soup.find_all("h2")])
            body_text = soup.get_text(" ", strip=True).lower()
            words = body_text.split()
            word_count = len(words)
            educational_hits = sum(1 for term in EDUCATIONAL_CONTEXT_TERMS if term in body_text)
            heading_count = len(soup.find_all(["h2", "h3"]))
            has_reference_sections = any(
                marker in body_text for marker in ("references", "referencias", "table of contents", "specification")
            )
            spec_cue_hits = sum(1 for c in SPEC_TECHNICAL_CUES if c in body_text)
            looks_like_spec_document = word_count >= 800 and spec_cue_hits >= 2
            url_lower = base_url.lower()
            url_is_educational = any(
                domain in url_lower
                for domain in (
                    "wikipedia.org",
                    "rfc-editor.org",
                    "tools.ietf.org",
                    "developer.mozilla.org",
                    "docs.python.org",
                    "w3.org",
                )
            )
            title_is_educational = any(
                kw in title_str for kw in ("wikipedia", "rfc ", "rfc-", "enciclopedia", "specification")
            )
            looks_educational = (
                (educational_hits >= 2 and word_count >= 180)
                or (word_count >= 300 and (heading_count >= 3 or has_reference_sections))
                or looks_like_spec_document
                or url_is_educational
                or (educational_hits >= 3 and title_is_educational)
            )

            if isinstance(status_code, int) and status_code >= 400:
                is_inoperative = True
                inoperative_hard_signal = True
                inoperative_reason = (
                    f"El código de estado HTTP {status_code} indica un error del servidor o del cliente."
                )
            else:
                # Patrones FUERTES: códigos HTTP y mensajes de error muy específicos.
                # Se comprueban SIEMPRE en título, H1, H2 y cuerpo completo (sin límite de palabras).
                strong_err_patterns = [
                    "404 not found",
                    "404 forbidden",
                    "404 error",
                    "error 404",
                    "page not found",
                    "página no encontrada",
                    "pagina no encontrada",
                    "internal server error",
                    "500 internal",
                    "500 error",
                    "error 500",
                    "http 500",
                    "502 bad gateway",
                    "bad gateway",
                    "502 error",
                    "error 502",
                    "http 502",
                    "503 service",
                    "503 unavailable",
                    "503 error",
                    "service unavailable",
                    "service temporarily unavailable",
                    "temporarily unavailable",
                    "error 503",
                    "http 503",
                    "servicio no disponible",
                    "504 gateway",
                    "gateway timeout",
                    "504 error",
                    "error 504",
                    "http 504",
                    "web server is down",
                    "error establishing a database connection",
                    "error al establecer una conexión con la base de datos",
                    "welcome to nginx",
                    "apache2 ubuntu default page",
                    "apache2 debian default page",
                    "iis windows server",
                    "hosting account suspended",
                    "cuenta suspendida",
                    "plesk default page",
                    "cpanel hosting",
                    "default website page",
                    "cloudflare ray id",
                    "sucuri web site blocker",
                    "blocked by web application firewall",
                    "ddos protection",
                ]
                # Patrones SUAVES: mantenimiento/construcción.
                # Solo se comprueban en páginas con poco texto (< 500 palabras).
                soft_maint_patterns = [
                    "mantenimiento",
                    "maintenance",
                    "en construcción",
                    "en construccion",
                    "under construction",
                    "coming soon",
                    "próximamente",
                    "proximamente",
                    "volveremos pronto",
                    "back soon",
                    "temporarily down",
                    "sitio inactivo",
                    "temporarily down for maintenance",
                    "site under maintenance",
                    "sitio bajo mantenimiento",
                    "error de conexión",
                    "error de conexion",
                    "database connection error",
                    "fallo de conexión",
                    "fallo de conexion",
                    "connection error",
                    "connection timed out",
                    "connection refused",
                    "error de base de datos",
                    "database error",
                    "access denied",
                    "forbidden error",
                ]

                title_raw = soup.title.string if soup.title else title_str

                # --- Comprobación FUERTE (sin límite de palabras) ---
                if any(p in title_str for p in strong_err_patterns):
                    is_inoperative = True
                    inoperative_hard_signal = True
                    inoperative_reason = (
                        f"El título de la página ('{title_raw}') indica un estado de error del servidor."
                    )
                elif any(p in h1_text for p in strong_err_patterns) or any(p in h2_text for p in strong_err_patterns):
                    is_inoperative = True
                    inoperative_hard_signal = True
                    inoperative_reason = "El encabezado principal de la página indica un error del servidor."
                elif (
                    word_count < MAX_BODY_STRONG_ERROR_WORDS
                    and any(p in body_text for p in strong_err_patterns)
                    and not looks_educational
                ):
                    is_inoperative = True
                    inoperative_reason = (
                        "El cuerpo de la página contiene indicadores de error del servidor (503, 502, 404, etc.)."
                    )
                # Detect custom error codes (e.g., a 503 page that returns HTTP 200)
                elif not looks_educational and (
                    self._has_contextual_error_code(title_str)
                    or self._has_contextual_error_code(h1_text)
                    or self._has_contextual_error_code(h2_text)
                    or self._has_contextual_error_code(body_text)
                ):
                    is_inoperative = True
                    inoperative_reason = "Página indica error HTTP código detectado en el contenido."
                # --- Comprobación SUAVE (solo en páginas con poco texto) ---
                elif word_count < 500:
                    if any(p in title_str for p in soft_maint_patterns):
                        is_inoperative = True
                        inoperative_reason = (
                            f"El título de la página ('{title_raw}') indica que el sitio está en mantenimiento."
                        )
                    elif (
                        any(p in h1_text for p in soft_maint_patterns)
                        or any(p in h2_text for p in soft_maint_patterns)
                        or any(p in body_text for p in soft_maint_patterns)
                    ):
                        is_inoperative = True
                        inoperative_reason = (
                            "El contenido de la página indica que el sitio está en mantenimiento o no disponible."
                        )

            # --- Integración con Microservicio de IA para análisis semántico ---
            ai_data = None
            if settings.AI_ANALYZER_ENABLED:
                try:
                    logger.info("🤖 Invocando microservicio de IA local para análisis semántico: %s", base_url)
                    ai_payload = {"html": html, "url": base_url, "status_code": status_code, "metadata": metadata}
                    ai_resp = self._session.post(
                        f"{settings.AI_ANALYZER_URL}/analyze", json=ai_payload, timeout=settings.AI_ANALYZER_TIMEOUT
                    )
                    if ai_resp.status_code == 200:
                        ai_data = ai_resp.json()
                        logger.info("✓ IA análisis completado. Score semántico: %s", ai_data.get("quality_score"))
                    else:
                        logger.warning("⚠️ Microservicio de IA retornó código %s", ai_resp.status_code)
                except Exception as exc:
                    logger.warning(
                        "⚠️ Error al conectar con el microservicio de IA: %s. Continuando con reglas clásicas.", exc
                    )

            if ai_data:
                # 1. Detección de inoperatividad por IA
                if ai_data.get("is_inoperative") and not is_inoperative:
                    is_inoperative = True
                    inoperative_reason = ai_data.get("inoperative_reason") or "Detectado por IA."
                elif not ai_data.get("is_inoperative") and is_inoperative and not inoperative_hard_signal:
                    # Si la regla clásica era heurística (no señal dura) y la IA no confirma,
                    # priorizamos el criterio semántico para evitar falsos positivos.
                    is_inoperative = False
                    inoperative_reason = ""

                # 2. Agregar problemas detectados por la IA a sus respectivas listas
                for issue in ai_data.get("issues", []):
                    # Si es un problema malicioso o no apto, se añade a seguridad y a contenido
                    if any(
                        kw in issue.lower()
                        for kw in [
                            "malicioso",
                            "no apto",
                            "adulto",
                            "pornografía",
                            "violencia",
                            "phishing",
                            "gambling",
                            "malware",
                            "estafa",
                        ]
                    ):
                        if issue not in security_issues:
                            security_issues.append(issue)
                        if issue not in content_issues:
                            content_issues.append(issue)
                    else:
                        if issue not in content_issues:
                            content_issues.append(issue)

                for warning in ai_data.get("warnings", []):
                    if warning not in content_issues:
                        content_issues.append(warning)

            if is_inoperative:
                warning_msg = f"Sitio web no operativo: {inoperative_reason}"
                if warning_msg not in technical_issues:
                    technical_issues.append(warning_msg)
                if warning_msg not in content_issues:
                    content_issues.append(warning_msg)
                recommendations.append(
                    "Asegurar que el servidor web responda correctamente y desactivar el modo mantenimiento para permitir la auditoría."
                )

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
                html=html,
                soup=soup,
                base_url=base_url,
                issues=security_issues,
                session=self._session,
                last_response_headers=self._last_response_headers,
                timeout=self._timeout,
                regex_set=self._regex,
                driver_factory=self._get_driver,
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
                soup=soup,
                issues=content_issues,
                html_lines=html_lines,
                base_url=base_url,
                dicts=self._dicts,
                regex_set=self._regex,
                normalize_fn=self._normalize_for_detection,
                find_line_fn=find_line,
            )
            update_progress()

            # Fase 4: Imagenes
            logger.info("🖼️ [Fase 5/8] Iniciando análisis de Imágenes rotas y etiquetas alt")
            check_images(
                soup=soup,
                base_url=base_url,
                html_lines=html_lines,
                issues=image_issues,
                is_banned_fn=is_banned_url,
                check_url_fn=lambda url, **kwargs: check_url(self._session, url, **kwargs),
                classify_speed_fn=classify_speed,
                find_line_fn=find_line,
            )
            update_progress()

            # Fase 5: Enlaces
            logger.info(
                "🔗 [Fase 6/8] Iniciando rastreo recursivo y comprobación de Enlaces rotos (máx: %d)",
                settings.AUDIT_MAX_RECURSIVE_LINKS,
            )
            check_links_recursive(
                soup=soup,
                base_url=base_url,
                html_lines=html_lines,
                issues=link_issues,
                crawl_stats=crawl_stats,
                is_banned_fn=is_banned_url,
                check_url_fn=lambda url, **kwargs: check_url(self._session, url, **kwargs),
                classify_speed_fn=classify_speed,
                find_line_fn=find_line,
                blocked_admin_segments=settings.AUDIT_ADMIN_PROBE_PATHS,
            )
            update_progress()

            # Fase 6: Botones
            logger.info("🔘 [Fase 7/8] Iniciando análisis de Botones y accesibilidad de formularios")
            check_buttons(
                soup=soup,
                base_url=base_url,
                html_lines=html_lines,
                issues=button_issues,
                is_banned_fn=is_banned_url,
                check_url_fn=lambda url, **kwargs: check_url(self._session, url, **kwargs),
                classify_speed_fn=classify_speed,
                find_line_fn=find_line,
                blocked_admin_segments=settings.AUDIT_ADMIN_PROBE_PATHS,
            )
            update_progress()

            # Fase 7: Tecnico + Browser
            logger.info("⚙️ [Fase 8/8] Iniciando análisis Técnico, recursos CSS/JS y errores de consola")
            check_technical(
                html=html,
                soup=soup,
                base_url=base_url,
                html_lines=html_lines,
                issues=technical_issues,
                asset_stats=asset_stats,
                recommendations=recommendations,
                is_banned_fn=is_banned_url,
                check_url_fn=lambda url, **kwargs: check_url(self._session, url, **kwargs),
                classify_speed_fn=classify_speed,
                find_line_fn=find_line,
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
            security_issues,
            seo_issues,
            content_issues,
            image_issues,
            structure_issues,
            link_issues,
            button_issues,
            technical_issues,
        )
        status = status_from_score(score)

        is_blocked, blockers = evaluate_release_gate(
            score=score,
            security_issues=security_issues,
            content_issues=content_issues,
            link_issues=link_issues,
            technical_issues=technical_issues,
            image_issues=image_issues,
            button_issues=button_issues,
        )

        final_recommendations = build_recommendations(
            security_issues=security_issues,
            seo_issues=seo_issues,
            content_issues=content_issues,
            image_issues=image_issues,
            structure_issues=structure_issues,
            link_issues=link_issues,
            button_issues=button_issues,
            technical_issues=technical_issues,
        )
        final_recommendations.extend(recommendations)

        report_metrics = collect_metrics(
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
        if ai_data:
            report_metrics["ai_quality_score"] = ai_data.get("quality_score")
            report_metrics["ai_detected_language"] = ai_data.get("detected_language")
            report_metrics["ai_confidence"] = ai_data.get("confidence")
            report_metrics["ai_is_inoperative"] = ai_data.get("is_inoperative")
            report_metrics["ai_has_spam"] = ai_data.get("has_spam")
            report_metrics["ai_has_malicious_content"] = ai_data.get("has_malicious_content")
            report_metrics["ai_has_incoherent_content"] = ai_data.get("has_incoherent_content")

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
            metrics=report_metrics,
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
            "Monitorizacion de errores de consola JS y rendimiento (bloqueo de renderizado)",
        ]

        top_improvements = (
            report.recommendations[:5] if report.recommendations else ["Mantener monitorizacion periodica."]
        )

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
            score_checks.append("[x] Existen recursos rotos o errores tecnicos que penalizan la puntuacion.")
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
            "IMAGENES Y RECURSOS:",
            *([f"  - {item}" for item in report.image_issues] or ["  - OK. Recursos optimizados."]),
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
        t = t.translate(
            str.maketrans(
                "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"
                "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"
                "０１２３４５６７８９",
                "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz0123456789",
            )
        )
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

    @staticmethod
    def _has_contextual_error_code(text: str) -> bool:
        """Devuelve True solo si aparece 4xx/5xx con contexto de error real."""
        lowered = (text or "").lower()
        for match in re.finditer(r"\b(4\d{2}|5\d{2})\b", lowered):
            start = max(0, match.start() - 90)
            end = min(len(lowered), match.end() + 90)
            window = lowered[start:end]
            if any(term in window for term in ERROR_CONTEXT_TERMS):
                return True
        return False
