"""
service.py — Lógica de negocio del scraper.
Orquesta el flujo de ejecución de una auditoría individual.
"""

from __future__ import annotations

from config.logging_config import setup_logger
from scraper import ScraperContext
from scraper.models.scrape_result import ScrapeResult
from shared.auditor import QualityAuditor
from shared.database.repositories import scraper as db

logger = setup_logger(__name__)


class AuditService:
    def __init__(self, context: ScraperContext, auditor: QualityAuditor, strategy_registry: dict, strategy_order: list):
        self.context = context
        self.auditor = auditor
        self.strategy_registry = strategy_registry
        self.strategy_order = strategy_order
        self._last_bs_prefetch = None

    def classify_and_scrape(self, url: str) -> tuple[ScrapeResult | None, str]:
        """
        Determina de forma inteligente la mejor estrategia (BeautifulSoup o Selenium)
        para una URL realizando un pre-fetch rápido mediante HTTP requests.
        Devuelve el ScrapeResult obtenido y la estrategia recomendada/usada.
        """
        from bs4 import BeautifulSoup

        logger.info("🔍 [AUTO] Analizando sitio web para determinar mejor estrategia: %s", url)

        # 1. Intentar pre-fetch rápido con BeautifulSoup
        bs_strategy = self.strategy_registry.get("beautifulsoup")
        if not bs_strategy:
            return None, "beautifulsoup"

        try:
            bs_result = bs_strategy.scrape(url)
            self._last_bs_prefetch = bs_result
        except Exception as e:
            logger.warning("Pre-fetch rápido falló para %s: %s", url, e)
            bs_result = None
            self._last_bs_prefetch = None

        if not bs_result or bs_result.status != "success":
            logger.info("⚠️ Pre-fetch de BeautifulSoup falló. Se sugerirá Selenium.")
            return None, "selenium"

        # 2. Analizar el HTML pre-fetcheado para determinar si es un SPA (Single Page Application)
        html_content = bs_result.content
        soup = BeautifulSoup(html_content, "html.parser")

        # Criterios de SPA / Dynamic Site:
        # A. Cuerpos vacíos o casi vacíos con nodos root típicos de frameworks SPA
        spa_nodos = ["root", "app", "app-root", "__next", "nuxt-app", "svelte-app"]
        is_spa_root_empty = False
        for nodo_id in spa_nodos:
            el = soup.find(id=nodo_id) or soup.find(nodo_id)
            if el:
                text_len = len(el.get_text().strip())
                if text_len < 100:
                    logger.info(
                        "🎯 Detectado contenedor SPA '%s' con poco contenido (%d chars).",
                        el.name or el.get("id"),
                        text_len,
                    )
                    is_spa_root_empty = True
                    break

        # B. Ratio de contenido de texto vs código HTML extremadamente bajo
        text_content = soup.get_text().strip()
        words = text_content.split()
        word_count = len(words)

        scripts = soup.find_all("script")
        script_char_count = sum(len(s.string or "") for s in scripts)

        is_thin_content_heavy_js = False
        if word_count < 80 and script_char_count > 5000:
            logger.info(
                "🎯 Detectado contenido muy ligero (%d palabras) con JS pesado (%d chars).",
                word_count,
                script_char_count,
            )
            is_thin_content_heavy_js = True

        # C. Detección de bundles específicos en scripts
        has_spa_js_bundles = False
        script_srcs = [s.get("src", "").lower() for s in scripts if s.get("src")]
        spa_keywords = ["react", "vue", "angular", "webpack", "chunk-vendors", "main-es2015", "svelte"]
        for src in script_srcs:
            if any(kw in src for kw in spa_keywords):
                if word_count < 150:
                    logger.info("🎯 Detectado bundle JS de framework SPA: %s", src)
                    has_spa_js_bundles = True
                    break

        # 3. Clasificación Final
        if is_spa_root_empty or is_thin_content_heavy_js or has_spa_js_bundles:
            logger.info("🖥️ [AUTO-CLASI] Sitio clasificado como DINÁMICO (Requiere Selenium) → %s", url)

            # Verificar si Selenium está disponible en este entorno
            selenium_strategy = self.strategy_registry.get("selenium")
            if selenium_strategy:
                return None, "selenium"
            else:
                logger.warning("⚠️ Selenium no está registrado en el entorno. Usando BeautifulSoup como fallback.")
                return bs_result, "beautifulsoup"
        else:
            logger.info("📄 [AUTO-CLASI] Sitio clasificado como ESTÁTICO/SSR (BeautifulSoup es ideal) → %s", url)
            return bs_result, "beautifulsoup"

    def process_website(self, entry: dict) -> bool:
        """Ejecuta el pipeline completo para un sitio web."""
        url = entry["url"]
        website_id = entry["website_id"]
        strategy_key = entry.get("strategy", "auto")

        run_id = db.create_run(website_id, strategy_key)
        result, used_strat = None, None

        if strategy_key == "auto":
            self._last_bs_prefetch = None
            # Usar clasificación inteligente y pre-fetch
            result, used_strat = self.classify_and_scrape(url)
            if result and result.status == "success":
                logger.info("🚀 [AUTO] Usando resultado pre-fetcheado de BeautifulSoup para ahorrar recursos.")
            else:
                logger.info("🚀 [AUTO] Ejecutando estrategia recomendada: %s", used_strat)
                order = [used_strat] + [s for s in self.strategy_order if s != used_strat]
                for strat_name in order:
                    if strat_name not in self.strategy_registry:
                        continue
                    self.context.set_strategy(self.strategy_registry[strat_name])
                    result = self.context.execute(url)
                    if result.status == "success":
                        used_strat = strat_name
                        break
                    logger.warning("Estrategia %s falló para %s", strat_name, url)

                # Failsafe absoluto si todas las ejecuciones principales fallaron
                if (
                    (result is None or result.status != "success")
                    and self._last_bs_prefetch
                    and self._last_bs_prefetch.status == "success"
                ):
                    logger.info(
                        "🚀 [FAILSAFE] Selenium o ejecución principal falló. Recuperando pre-fetch exitoso de BeautifulSoup."
                    )
                    result = self._last_bs_prefetch
                    used_strat = "beautifulsoup"
        else:
            # Determinar orden explícito de estrategias solicitado
            order = (
                [strategy_key] + [s for s in self.strategy_order if s != strategy_key]
                if strategy_key in self.strategy_registry
                else list(self.strategy_order)
            )
            for strat_name in order:
                if strat_name not in self.strategy_registry:
                    continue
                self.context.set_strategy(self.strategy_registry[strat_name])
                result = self.context.execute(url)
                if result.status == "success":
                    used_strat = strat_name
                    break
                logger.warning("Estrategia %s falló para %s", strat_name, url)

        # Manejo de error en el scraping
        if result is None or result.status != "success":
            err_msg = result.error if result else "Sin resultado"
            logger.error("Error en %s: %s", url, err_msg)
            db.save_audit_run(
                run_id=run_id,
                website_id=website_id,
                status="error",
                strategy_used=strategy_key,
                report=None,
                report_text="",
                error_message=err_msg,
                scrape_metadata={},
            )
            return False

        # Ejecutar auditoría sobre el HTML obtenido
        try:

            def on_progress(p, t):
                print(f"AuditService: Updating progress {p}/{t} for run {run_id}")
                db.update_run_progress(run_id, p, t)

            report_obj = self.auditor.build_report(
                html=result.content, base_url=url, metadata=result.metadata, on_progress=on_progress
            )
            report_dict = report_obj.to_dict()
            report_text = self.auditor.report_to_text(report_obj)
        except Exception as exc:
            logger.error("Error en auditoría de %s: %s", url, exc)
            report_dict = None
            report_text = f"Error durante auditoría: {exc}"

        # Persistir resultados finales
        db.save_audit_run(
            run_id=run_id,
            website_id=website_id,
            status="success",
            strategy_used=used_strat or strategy_key,
            report=report_dict,
            report_text=report_text,
            error_message=None,
            scrape_metadata=result.metadata,
        )

        logger.info(
            "✓ %s → score=%s estado=%s",
            url,
            (report_dict or {}).get("score", "N/A"),
            (report_dict or {}).get("status", "N/A"),
        )
        return True
