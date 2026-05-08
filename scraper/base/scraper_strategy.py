from abc import ABC, abstractmethod
from scraper.models.scrape_result import ScrapeResult


class ScraperStrategy(ABC):
    """
    Interfaz abstracta del patrón Estrategia.

    Todas las estrategias de scraping deben heredar de esta clase
    e implementar el método `scrape`. Esto garantiza que el contexto
    (ScraperContext) pueda intercambiarlas sin conocer su implementación.

    Contrato:
      - Recibe una URL como string.
      - Siempre devuelve un ScrapeResult (nunca lanza excepciones al exterior;
        los errores se encapsulan dentro del ScrapeResult).
    """

    @abstractmethod
    def scrape(self, url: str) -> ScrapeResult:
        """
        Ejecuta el scraping sobre la URL indicada.

        Args:
            url: Dirección web a scrapear.

        Returns:
            ScrapeResult con el contenido extraído o información del error.
        """
        ...

    @property
    def strategy_name(self) -> str:
        """Nombre identificador de la estrategia (usa el nombre de la clase)."""
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"<{self.strategy_name}>"
