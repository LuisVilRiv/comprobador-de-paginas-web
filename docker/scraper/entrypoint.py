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
from datetime import datetime
from croniter import croniter

from config.logging_config import setup_logger
from scraper import ScraperContext, SeleniumStrategy, BeautifulSoupStrategy
from shared.auditor import QualityAuditor
from shared.database import repository as db_repo

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
    run_id = db_repo.create_run(website_id, strategy_key)

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
        db_repo.save_audit_run(
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
    db_repo.save_audit_run(
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
        pending_entries = db_repo.get_pending_audit_websites()
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
            db_repo.clear_pending_audit(entry["website_id"])
        except Exception as exc:
            logger.error("No se pudo limpiar pending_audit para %s: %s", entry["url"], exc)
    
    return successes


def run_scheduled_cycle(context: ScraperContext, auditor: QualityAuditor) -> int:
    """Ejecuta el ciclo normal sobre todas las URLs activas."""
    try:
        active_entries = db_repo.get_active_websites()
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
    
    # Próximas ejecuciones calculadas
    next_runs = {"active": None, "inactive": None}

    while True:
        # 1. Siempre procesar pendientes (cada 5 seg)
        run_pending_audits(context, auditor)

        # 2. Leer configuración de crons desde la BD
        try:
            settings = db_repo.get_settings()
            cron_active = settings.get("cron_active", "0 0 * * 0,3")
            cron_inactive = settings.get("cron_inactive", "0 0 1 2,4,6,8,10,12 *")
            
            # Detectar si el cron ha cambiado para recalcular next_runs inmediatamente
            if "last_cron_active" not in locals() or last_cron_active != cron_active:
                next_runs["active"] = croniter(cron_active, datetime.now()).get_next(datetime)
                last_cron_active = cron_active
                logger.info("🆕 Nuevo horario para ACTIVOS detectado: %s. Próxima: %s", cron_active, next_runs["active"])

            if "last_cron_inactive" not in locals() or last_cron_inactive != cron_inactive:
                next_runs["inactive"] = croniter(cron_inactive, datetime.now()).get_next(datetime)
                last_cron_inactive = cron_inactive
                logger.info("🆕 Nuevo horario para INACTIVOS detectado: %s. Próxima: %s", cron_inactive, next_runs["inactive"])

        except Exception as exc:
            logger.error("Error al leer settings: %s", exc)
            cron_active = "0 0 * * 0,3"
            cron_inactive = "0 0 1 2,4,6,8,10,12 *"

        now_dt = datetime.now()

        # 3. Evaluar si toca ejecutar ciclo de ACTIVOS
        try:
            if next_runs["active"] is None:
                next_runs["active"] = croniter(cron_active, now_dt).get_next(datetime)
            
            if now_dt >= next_runs["active"]:
                logger.info("⏰ [CRON] Iniciando ciclo programado de ACTIVOS (%s)", cron_active)
                run_scheduled_cycle(context, auditor)
                next_runs["active"] = croniter(cron_active, now_dt).get_next(datetime)
        except Exception as exc:
            logger.error("Error en scheduler de activos: %s", exc)

        # 4. Evaluar si toca ejecutar ciclo de INACTIVOS
        try:
            if next_runs["inactive"] is None:
                next_runs["inactive"] = croniter(cron_inactive, now_dt).get_next(datetime)

            if now_dt >= next_runs["inactive"]:
                logger.info("⏰ [CRON] Iniciando ciclo programado de INACTIVOS (%s)", cron_inactive)
                inactive_entries = db_repo.get_inactive_websites()
                if inactive_entries:
                    logger.info("Procesando %d URLs inactivas.", len(inactive_entries))
                    for entry in inactive_entries:
                        _audit_entry(entry, context, auditor)
                next_runs["inactive"] = croniter(cron_inactive, now_dt).get_next(datetime)
        except Exception as exc:
            logger.error("Error en scheduler de inactivos: %s", exc)

        time.sleep(5)



if __name__ == "__main__":
    main()