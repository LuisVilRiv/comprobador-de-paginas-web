"""
entrypoint.py — Punto de entrada del scraper en el contenedor Docker.

Responsabilidades:
  · Orquestar el pipeline scraping → auditoría → persistencia por URL.
  · Delegar el scheduling al módulo scheduler.py.
  · Leer/escribir de PostgreSQL via shared.database.repo_scraper.
"""
from __future__ import annotations

import os
import sys

# Añadir /app al sys.path para importaciones locales (service, scheduler)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.logging_config import setup_logger
from scraper import ScraperContext, SeleniumStrategy, BeautifulSoupStrategy
from shared.auditor import QualityAuditor
from shared.database.repositories import scraper as db
from service import AuditService

logger = setup_logger(__name__)

STRATEGY_REGISTRY = {
    "selenium":      SeleniumStrategy(),
    "beautifulsoup": BeautifulSoupStrategy(),
}
STRATEGY_ORDER = ["selenium", "beautifulsoup"]


# ── Orquestación de Ciclos ──────────────────────────────────────────────────

def run_pending_audits(service: AuditService) -> int:
    entries = db.get_pending_audit_websites()
    if not entries:
        return 0
    logger.info("⚡ [MANUAL] %d auditoría(s) pendiente(s).", len(entries))
    successes = 0
    for entry in entries:
        if service.process_website(entry):
            successes += 1
        try:
            db.clear_pending_audit(entry["website_id"])
        except Exception as exc:
            logger.error("No se pudo limpiar pending_audit para %s: %s", entry["url"], exc)
    return successes


def run_active_cycle(service: AuditService) -> int:
    entries = db.get_active_websites()
    if not entries:
        logger.info("No hay URLs activas para el ciclo programado.")
        return 0
    logger.info("Ciclo ACTIVOS: %d URLs.", len(entries))
    successes = sum(1 for e in entries if service.process_website(e))
    logger.info("Ciclo ACTIVOS finalizado. Éxitos: %d", successes)
    return successes


def run_inactive_cycle(service: AuditService) -> int:
    entries = db.get_inactive_websites()
    if not entries:
        return 0
    logger.info("Ciclo INACTIVOS: %d URLs.", len(entries))
    return sum(1 for e in entries if service.process_website(e))


# ── Punto de entrada ──────────────────────────────────────────────────────────

def main():
    interval = int(os.environ.get("RUN_INTERVAL_SECONDS", "0"))
    
    # Inicializar componentes
    context = ScraperContext(STRATEGY_REGISTRY["selenium"])
    auditor = QualityAuditor()
    service = AuditService(context, auditor, STRATEGY_REGISTRY, STRATEGY_ORDER)

    if interval <= 0:
        logger.info("Ejecución única (RUN_INTERVAL_SECONDS=0).")
        run_pending_audits(service)
        run_active_cycle(service)
        sys.exit(0)

    logger.info("Modo daemon — poll manual: 5s, ciclos por cron.")

    from scheduler import AuditScheduler

    scheduler = AuditScheduler(
        run_pending_fn  = lambda: run_pending_audits(service),
        run_active_fn   = lambda: run_active_cycle(service),
        run_inactive_fn = lambda: run_inactive_cycle(service),
        run_single_fn   = lambda entry: service.process_website(entry),
        get_active_fn   = db.get_active_websites,
        get_inactive_fn = db.get_inactive_websites,
        settings_fn     = db.get_settings,
        poll_interval   = 5,
    )
    scheduler.run_forever()


if __name__ == "__main__":
    main()
