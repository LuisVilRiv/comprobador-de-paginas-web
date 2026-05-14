"""
entrypoint.py — Punto de entrada del scraper en el contenedor Docker.

Diferencias respecto al main.py original:
  · Lee las URLs desde PostgreSQL (tabla websites) en lugar de urls.json.
  · Procesa PRIMERO los websites con pending_audit=TRUE (solicitudes manuales
    del dashboard), luego continúa con el ciclo normal de activos.
  · Persiste los resultados en PostgreSQL.
  · Soporta modo daemon con RUN_INTERVAL_SECONDS > 0.
"""
import os
import sys
import time

from config.logging_config import setup_logger
from scraper import ScraperContext, SeleniumStrategy, BeautifulSoupStrategy
from utils.quality_auditor import QualityAuditor
import db as database

logger = setup_logger(__name__)

STRATEGY_REGISTRY = {
    "selenium":      SeleniumStrategy(),
    "beautifulsoup": BeautifulSoupStrategy(),
}
STRATEGY_ORDER = ["selenium", "beautifulsoup"]


def _audit_entry(entry: dict, context: ScraperContext, auditor: QualityAuditor) -> bool:
    """
    Ejecuta el pipeline completo (scraping + auditoría + persistencia) para
    una entrada. Devuelve True si tuvo éxito, False si hubo error.
    """
    url          = entry["url"]
    website_id   = entry["website_id"]
    strategy_key = entry.get("strategy", "auto")

    # Determinar orden de estrategias
    if strategy_key != "auto" and strategy_key in STRATEGY_REGISTRY:
        order = [strategy_key] + [s for s in STRATEGY_ORDER if s != strategy_key]
    else:
        order = list(STRATEGY_ORDER)

    # Crear registro de ejecución en BD
    run_id = database.create_run(website_id, strategy_key)

    # Scraping con fallback entre estrategias
    result     = None
    used_strat = None
    for strat_name in order:
        if strat_name not in STRATEGY_REGISTRY:
            continue
        context.set_strategy(STRATEGY_REGISTRY[strat_name])
        result = context.execute(url)
        if result.status == "success":
            used_strat = strat_name
            break
        logger.warning("Estrategia %s falló para %s, probando siguiente…", strat_name, url)

    if result is None or result.status != "success":
        err_msg = result.error if result else "Sin resultado"
        logger.error("Error en %s: %s", url, err_msg)
        database.save_audit_run(
            run_id=run_id, website_id=website_id, status="error",
            strategy_used=strategy_key, report=None, report_text="",
            error_message=err_msg, scrape_metadata={},
        )
        return False

    # Auditoría de calidad
    try:
        report_obj  = auditor.build_report(html=result.content, base_url=url, metadata=result.metadata)
        report_dict = report_obj.to_dict()
        report_text = auditor.report_to_text(report_obj)
    except Exception as exc:
        logger.error("Error en auditoría de %s: %s", url, exc)
        report_dict = None
        report_text = f"Error durante auditoría: {exc}"

    # Persistir en PostgreSQL
    database.save_audit_run(
        run_id=run_id, website_id=website_id, status="success",
        strategy_used=used_strat or strategy_key,
        report=report_dict, report_text=report_text,
        error_message=None, scrape_metadata=result.metadata,
    )
    logger.info(
        "✓ %s → score=%s estado=%s",
        url,
        (report_dict or {}).get("score", "N/A"),
        (report_dict or {}).get("status", "N/A"),
    )
    return True


def run_pending_audits(context: ScraperContext, auditor: QualityAuditor) -> int:
    """Procesa solo las auditorías marcadas manualmente."""
    try:
        pending_entries = database.get_pending_audit_websites()
    except Exception as exc:
        logger.error("Error al leer pendientes: %s", exc)
        return 0

    if not pending_entries:
        return 0

    logger.info("⚡ [MANUAL] Procesando %d auditoría(s) inmediata(s).", len(pending_entries))
    successes = 0
    for entry in pending_entries:
        ok = _audit_entry(entry, context, auditor)
        if ok: successes += 1
        # Limpiar el flag siempre
        try:
            database.clear_pending_audit(entry["website_id"])
        except Exception as exc:
            logger.error("No se pudo limpiar pending_audit para %s: %s", entry["url"], exc)
    
    return successes


def run_scheduled_cycle(context: ScraperContext, auditor: QualityAuditor) -> int:
    """Ejecuta el ciclo normal sobre todas las URLs activas."""
    try:
        active_entries = database.get_active_websites()
    except Exception as exc:
        logger.error("Error al leer activas: %s", exc)
        return 0

    if not active_entries:
        logger.info("No hay URLs activas para el ciclo programado.")
        return 0

    logger.info("Iniciando ciclo programado de %d URL(s).", len(active_entries))
    successes = 0
    for entry in active_entries:
        ok = _audit_entry(entry, context, auditor)
        if ok: successes += 1
    
    logger.info("Ciclo programado finalizado. Exitosos: %d", successes)
    return successes


def main():
    interval = int(os.environ.get("RUN_INTERVAL_SECONDS", "0"))
    context  = ScraperContext(STRATEGY_REGISTRY["selenium"])
    auditor  = QualityAuditor()

    # Si interval es 0, ejecutamos una vez TODO y salimos (comportamiento original run_once)
    if interval <= 0:
        logger.info("Ejecución única (RUN_INTERVAL_SECONDS=0)")
        run_pending_audits(context, auditor)
        run_scheduled_cycle(context, auditor)
        sys.exit(0)

    logger.info("Modo daemon activado. Ciclo programado: %d seg | Poll manual: 5 seg.", interval)
    
    last_scheduled_run = 0
    while True:
        # 1. Siempre procesar pendientes (cada iteración del bucle, que duerme 5s)
        run_pending_audits(context, auditor)

        # 2. Procesar ciclo completo si toca
        now = time.time()
        if now - last_scheduled_run >= interval:
            run_scheduled_cycle(context, auditor)
            last_scheduled_run = now

        time.sleep(5)


if __name__ == "__main__":
    main()