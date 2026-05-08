"""
Punto de entrada del proyecto web_scraper_project.

Flujo:
  1. Carga las URLs activas desde data/urls.json.
  2. Agrupa las URLs por estrategia.
  3. Ejecuta cada grupo con su estrategia correspondiente.
  4. Exporta todos los resultados a disco (JSON por defecto).
"""
import sys
from config.logging_config import setup_logger
from scraper import ScraperContext, SeleniumStrategy, BeautifulSoupStrategy
from utils.url_loader import UrlLoader
from utils.file_exporter import FileExporter
from utils.quality_auditor import QualityAuditor

logger = setup_logger(__name__)

# ── Registro de estrategias disponibles ──────────────────────────────────────
STRATEGY_REGISTRY = {
    "selenium":       SeleniumStrategy(),
    "beautifulsoup":  BeautifulSoupStrategy(),
}


def run() -> int:
    """
    Ejecuta el pipeline completo de scraping.

    Returns:
        Código de salida: 0 éxito, 1 si hubo errores.
    """
    # 1. Cargar URLs
    try:
        entries = UrlLoader().load(only_active=True)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("No se pudo cargar urls.json: %s", exc)
        return 1

    if not entries:
        logger.warning("No hay URLs activas en urls.json. Saliendo.")
        return 0

    logger.info("Iniciando scraping de %d URL(s).", len(entries))

    # 2. Ejecutar cada URL con su estrategia
    context  = ScraperContext(STRATEGY_REGISTRY["selenium"])
    auditor  = QualityAuditor()
    results  = []

    for entry in entries:
        strategy_key = entry["strategy"]
        if strategy_key not in STRATEGY_REGISTRY:
            logger.warning("Estrategia '%s' no registrada. Omitiendo.", strategy_key)
            continue

        context.set_strategy(STRATEGY_REGISTRY[strategy_key])
        result = context.execute(entry["url"])

        if result.status == "success":
            report = auditor.build_report(
                html=result.content,
                base_url=entry["url"],
                metadata=result.metadata,
            )
            result.metadata["quality_report"] = report.to_dict()
            result.content = auditor.report_to_text(report)

        results.append(result)

        if result.status == "error":
            logger.error("Error en %s: %s", entry["url"], result.error)

    # 3. Exportar resultados
    exporter  = FileExporter()
    output    = exporter.export(results)
    successes = sum(1 for r in results if r.status == "success")
    errors    = len(results) - successes

    logger.info(
        "Scraping finalizado. Exitosos: %d | Errores: %d | Fichero: %s",
        successes, errors, output,
    )

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
