"""
entrypoint.py — Punto de entrada del scraper en el contenedor Docker.

Diferencias respecto al main.py original:
  · Lee las URLs desde PostgreSQL (tabla websites) en lugar de urls.json.
  · Persiste los resultados en PostgreSQL (tabla audit_runs + audit_issues).
  · Soporta modo daemon con RUN_INTERVAL_SECONDS > 0.
  · Mantiene el mismo pipeline interno (ScraperContext, QualityAuditor…).
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
    "selenium":       SeleniumStrategy(),
    "beautifulsoup":  BeautifulSoupStrategy(),
}
STRATEGY_ORDER = ["selenium", "beautifulsoup"]


def run_once() -> int:
    """Ejecuta un ciclo completo de scraping sobre todas las URLs activas."""

    # 1. Cargar URLs desde PostgreSQL
    try:
        entries = database.get_active_websites()
    except Exception as exc:
        logger.error("No se pudo conectar a la base de datos: %s", exc)
        return 1

    if not entries:
        logger.warning("No hay URLs activas en la base de datos. Saliendo.")
        return 0

    logger.info("Iniciando análisis de %d URL(s).", len(entries))

    context = ScraperContext(STRATEGY_REGISTRY["selenium"])
    auditor = QualityAuditor()
    successes = 0
    errors = 0

    for entry in entries:
        url         = entry["url"]
        website_id  = entry["website_id"]
        strategy_key = entry.get("strategy", "auto")

        # Determinar orden de estrategias
        if strategy_key != "auto" and strategy_key in STRATEGY_REGISTRY:
            order = [strategy_key] + [s for s in STRATEGY_ORDER if s != strategy_key]
        else:
            order = list(STRATEGY_ORDER)

        # 2. Crear registro de ejecución en BD (estado 'running')
        run_id = database.create_run(website_id, strategy_key)

        # 3. Intentar scraping con fallback
        result      = None
        used_strat  = None
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
                run_id=run_id,
                website_id=website_id,
                status="error",
                strategy_used=strategy_key,
                report=None,
                report_text="",
                error_message=err_msg,
                scrape_metadata={},
            )
            errors += 1
            continue

        # 4. Auditar
        try:
            report_obj = auditor.build_report(
                html=result.content,
                base_url=url,
                metadata=result.metadata,
            )
            report_dict = report_obj.to_dict()
            report_text = auditor.report_to_text(report_obj)
        except Exception as exc:
            logger.error("Error en auditoría de %s: %s", url, exc)
            report_dict = None
            report_text = f"Error durante auditoría: {exc}"

        # 5. Persistir en PostgreSQL
        database.save_audit_run(
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
        successes += 1

    logger.info("Ciclo finalizado. Exitosos: %d | Errores: %d", successes, errors)
    return 0 if errors == 0 else 1


def main():
    interval = int(os.environ.get("RUN_INTERVAL_SECONDS", "0"))

    if interval <= 0:
        # Modo single-shot
        sys.exit(run_once())
    else:
        # Modo daemon: repetir cada N segundos
        logger.info("Modo daemon activado. Intervalo: %d segundos.", interval)
        while True:
            run_once()
            logger.info("Próxima ejecución en %d segundos…", interval)
            time.sleep(interval)


if __name__ == "__main__":
    main()
