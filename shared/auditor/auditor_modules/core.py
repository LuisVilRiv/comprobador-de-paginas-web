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
from .checks import (
    check_security, check_structure, check_seo, check_content, check_images,
    check_links_recursive, check_buttons, check_technical, check_js_console_errors,
    interact_buttons_selenium
)
from .helpers import (
    is_banned_url, warm_up_cookies, close_driver, ensure_non_empty,
    collect_metrics, calculate_score, status_from_score, evaluate_release_gate,
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
            if is_banned_url(base_url):
                warning = f"URL prohibida para pruebas de red por politica: {base_url}"
                link_issues.append(warning)
                recommendations.append(
                    "Cambiar URL objetivo por un dominio permitido para validar "
                    "enlaces e imagenes."
                )
            else:
                warm_up_cookies(self._session, base_url)

            check_security(self, html, soup, base_url, security_issues)
            check_structure(self, soup, structure_issues)
            check_seo(self, soup, seo_issues)
            check_content(self, soup, content_issues, html_lines, base_url)
            check_images(self, soup, base_url, html_lines, image_issues)
            check_links_recursive(self, soup, base_url, html_lines, link_issues, crawl_stats)
            check_buttons(self, soup, base_url, html_lines, button_issues)
            check_technical(self, html, soup, base_url, html_lines, technical_issues, asset_stats, recommendations)

            if not is_banned_url(base_url):
                check_js_console_errors(self, base_url, technical_issues)
                interact_buttons_selenium(self, base_url, button_issues)
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

        metrics = collect_metrics(
            soup, metadata, security_issues, image_issues, link_issues,
            button_issues, technical_issues, crawl_stats, asset_stats,
        )
        score = calculate_score(
            security_issues, seo_issues, content_issues, image_issues,
            structure_issues, link_issues, button_issues, technical_issues,
        )
        status = status_from_score(score)
        release_blocked, release_blockers = evaluate_release_gate(
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
            build_recommendations(
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