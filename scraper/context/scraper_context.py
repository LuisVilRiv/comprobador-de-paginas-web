from config.logging_config import setup_logger
from scraper.base.scraper_strategy import ScraperStrategy
from scraper.models.scrape_result import ScrapeResult

logger = setup_logger(__name__)


class ScraperContext:
    """
    Contexto del patrón Estrategia.

    Es el único punto desde el que se ejecuta el scraping.
    No conoce los detalles de ninguna estrategia concreta;
    simplemente delega en la que tenga asignada en ese momento.

    Permite cambiar de estrategia en caliente (set_strategy)
    sin modificar el código que llama a execute().

    Uso básico:
        context = ScraperContext(SeleniumStrategy())
        result  = context.execute("https://ejemplo.com")

    Cambio de estrategia en tiempo de ejecución:
        context.set_strategy(BeautifulSoupStrategy())
        result = context.execute("https://otro.com")
    """

    def __init__(self, strategy: ScraperStrategy):
        self._strategy = strategy
        logger.debug("Contexto iniciado con estrategia: %s", strategy)

    # ── API pública ───────────────────────────────────────────────────────────

    def set_strategy(self, strategy: ScraperStrategy) -> None:
        """Sustituye la estrategia activa."""
        logger.debug(
            "Cambiando estrategia: %s → %s",
            self._strategy,
            strategy,
        )
        self._strategy = strategy

    def execute(self, url: str) -> ScrapeResult:
        """Delega el scraping en la estrategia activa."""
        logger.info(
            "Ejecutando [%s] sobre: %s",
            self._strategy.strategy_name,
            url,
        )
        return self._strategy.scrape(url)

    def execute_batch(self, urls: list[str]) -> list[ScrapeResult]:
        """
        Ejecuta el scraping sobre una lista de URLs con la estrategia actual.
        Recoge todos los resultados sin detener el proceso si uno falla.
        """
        results = []
        for url in urls:
            result = self.execute(url)
            results.append(result)
        return results

    # ── Propiedades de inspección ─────────────────────────────────────────────

    @property
    def current_strategy(self) -> str:
        return self._strategy.strategy_name

    def __repr__(self) -> str:
        return f"<ScraperContext strategy={self.current_strategy}>"
