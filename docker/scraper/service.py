"""
service.py — Lógica de negocio del scraper.
Orquesta el flujo de ejecución de una auditoría individual.
"""
import logging
from scraper import ScraperContext
from shared.auditor import QualityAuditor
from shared.database.repositories import scraper as db

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self, context: ScraperContext, auditor: QualityAuditor, strategy_registry: dict, strategy_order: list):
        self.context = context
        self.auditor = auditor
        self.strategy_registry = strategy_registry
        self.strategy_order = strategy_order

    def process_website(self, entry: dict) -> bool:
        """Ejecuta el pipeline completo para un sitio web."""
        url          = entry["url"]
        website_id   = entry["website_id"]
        strategy_key = entry.get("strategy", "auto")

        # Determinar orden de estrategias
        order = (
            [strategy_key] + [s for s in self.strategy_order if s != strategy_key]
            if strategy_key != "auto" and strategy_key in self.strategy_registry
            else list(self.strategy_order)
        )

        run_id = db.create_run(website_id, strategy_key)
        result, used_strat = None, None

        # Intentar con las estrategias disponibles
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
            db.save_audit_run(run_id=run_id, website_id=website_id, status="error",
                              strategy_used=strategy_key, report=None, report_text="",
                              error_message=err_msg, scrape_metadata={})
            return False

        # Ejecutar auditoría sobre el HTML obtenido
        try:
            def on_progress(p, t):
                print(f"AuditService: Updating progress {p}/{t} for run {run_id}")
                db.update_run_progress(run_id, p, t)

            report_obj  = self.auditor.build_report(
                html=result.content, base_url=url, metadata=result.metadata,
                on_progress=on_progress
            )
            report_dict = report_obj.to_dict()
            report_text = self.auditor.report_to_text(report_obj)
        except Exception as exc:
            logger.error("Error en auditoría de %s: %s", url, exc)
            report_dict = None
            report_text = f"Error durante auditoría: {exc}"

        # Persistir resultados finales
        db.save_audit_run(run_id=run_id, website_id=website_id, status="success",
                          strategy_used=used_strat or strategy_key,
                          report=report_dict, report_text=report_text,
                          error_message=None, scrape_metadata=result.metadata)
        
        logger.info("✓ %s → score=%s estado=%s", url,
                    (report_dict or {}).get("score", "N/A"),
                    (report_dict or {}).get("status", "N/A"))
        return True
