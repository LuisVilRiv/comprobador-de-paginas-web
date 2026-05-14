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

from config.logging_config import setup_logger
from scraper import ScraperContext, SeleniumStrategy, BeautifulSoupStrategy
from shared.auditor import QualityAuditor
from shared.database import repo_scraper as db

logger = setup_logger(__name__)

STRATEGY_REGISTRY = {
    "selenium":      SeleniumStrategy(),
    "beautifulsoup": BeautifulSoupStrategy(),
}
STRATEGY_ORDER = ["selenium", "beautifulsoup"]


# ── Pipeline de ejecución por URL ─────────────────────────────────────────────

def _audit_entry(entry: dict, context: ScraperContext, auditor: QualityAuditor) -> bool:
    url          = entry["url"]
    website_id   = entry["website_id"]
    strategy_key = entry.get("strategy", "auto")

    order = (
        [strategy_key] + [s for s in STRATEGY_ORDER if s != strategy_key]
        if strategy_key != "auto" and strategy_key in STRATEGY_REGISTRY
        else list(STRATEGY_ORDER)
    )

    run_id = db.create_run(website_id, strategy_key)
    result, used_strat = None, None

    for strat_name in order:
        if strat_name not in STRATEGY_REGISTRY:
            continue
        context.set_strategy(STRATEGY_REGISTRY[strat_name])
        result = context.execute(url)
        if result.status == "success":
            used_strat = strat_name
            break
        logger.warning("Estrategia %s falló para %s", strat_name, url)

    if result is None or result.status != "success":
        err_msg = result.error if result else "Sin resultado"
        logger.error("Error en %s: %s", url, err_msg)
        db.save_audit_run(run_id=run_id, website_id=website_id, status="error",
                          strategy_used=strategy_key, report=None, report_text="",
                          error_message=err_msg, scrape_metadata={})
        return False

    try:
        report_obj  = auditor.build_report(html=result.content, base_url=url, metadata=result.metadata)
        report_dict = report_obj.to_dict()
        report_text = auditor.report_to_text(report_obj)
    except Exception as exc:
        logger.error("Error en auditoría de %s: %s", url, exc)
        report_dict = None
        report_text = f"Error durante auditoría: {exc}"

    db.save_audit_run(run_id=run_id, website_id=website_id, status="success",
                      strategy_used=used_strat or strategy_key,
                      report=report_dict, report_text=report_text,
                      error_message=None, scrape_metadata=result.metadata)
    logger.info("✓ %s → score=%s estado=%s", url,
                (report_dict or {}).get("score", "N/A"),
                (report_dict or {}).get("status", "N/A"))
    return True


# ── Funciones de ciclo ────────────────────────────────────────────────────────

def _make_context_and_auditor():
    return ScraperContext(STRATEGY_REGISTRY["selenium"]), QualityAuditor()


def run_pending_audits(context, auditor) -> int:
    entries = db.get_pending_audit_websites()
    if not entries:
        return 0
    logger.info("⚡ [MANUAL] %d auditoría(s) pendiente(s).", len(entries))
    successes = 0
    for entry in entries:
        if _audit_entry(entry, context, auditor):
            successes += 1
        try:
            db.clear_pending_audit(entry["website_id"])
        except Exception as exc:
            logger.error("No se pudo limpiar pending_audit para %s: %s", entry["url"], exc)
    return successes


def run_active_cycle(context, auditor) -> int:
    entries = db.get_active_websites()
    if not entries:
        logger.info("No hay URLs activas para el ciclo programado.")
        return 0
    logger.info("Ciclo ACTIVOS: %d URLs.", len(entries))
    successes = sum(1 for e in entries if _audit_entry(e, context, auditor))
    logger.info("Ciclo ACTIVOS finalizado. Éxitos: %d", successes)
    return successes


def run_inactive_cycle(context, auditor) -> int:
    entries = db.get_inactive_websites()
    if not entries:
        return 0
    logger.info("Ciclo INACTIVOS: %d URLs.", len(entries))
    return sum(1 for e in entries if _audit_entry(e, context, auditor))


# ── Punto de entrada ──────────────────────────────────────────────────────────

def main():
    interval = int(os.environ.get("RUN_INTERVAL_SECONDS", "0"))
    context, auditor = _make_context_and_auditor()

    if interval <= 0:
        logger.info("Ejecución única (RUN_INTERVAL_SECONDS=0).")
        run_pending_audits(context, auditor)
        run_active_cycle(context, auditor)
        sys.exit(0)

    logger.info("Modo daemon — poll manual: 5s, ciclos por cron.")

    from scheduler import AuditScheduler

    scheduler = AuditScheduler(
        run_pending_fn  = lambda: run_pending_audits(context, auditor),
        run_active_fn   = lambda: run_active_cycle(context, auditor),
        run_inactive_fn = lambda: run_inactive_cycle(context, auditor),
        settings_fn     = db.get_settings,
        poll_interval   = 5,
    )
    scheduler.run_forever()


if __name__ == "__main__":
    main()
