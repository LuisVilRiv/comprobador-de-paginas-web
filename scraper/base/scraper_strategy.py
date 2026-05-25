"""
SCRAPER_STRATEGY.PY - Interfaz Abstracta del Patrón Strategy

DESCRIPCIÓN:
Este módulo define la interfaz abstracta para todas las estrategias de scraping.
Implementa el patrón Strategy para permitir el intercambio dinámico de métodos
de extracción web (Selenium vs BeautifulSoup).

CLASES:
- ScraperStrategy: Clase base abstracta que define el contrato para estrategias.

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

from abc import ABC, abstractmethod

from scraper.models.scrape_result import ScrapeResult

# ═══════════════════════════════════════════════════════════════════════════════
# CLASES
# ═══════════════════════════════════════════════════════════════════════════════


class ScraperStrategy(ABC):
    """
    Interfaz abstracta del patrón Strategy para scraping web.

    Todas las estrategias de scraping deben heredar de esta clase
    e implementar el método `scrape`. Esto garantiza que el contexto
    (ScraperContext) pueda intercambiarlas sin conocer su implementación.

    Contrato:
      - Recibe una URL como string.
      - Siempre devuelve un ScrapeResult (nunca lanza excepciones al exterior;
        los errores se encapsulan dentro del ScrapeResult).

    Example:
        >>> class MyStrategy(ScraperStrategy):
        ...     def scrape(self, url: str) -> ScrapeResult:
        ...         # Implementación personalizada
        ...         pass
    """

    @abstractmethod
    def scrape(self, url: str) -> ScrapeResult:
        """
        Ejecuta el scraping sobre la URL indicada.

        Args:
            url (str): Dirección web a scrapear.

        Returns:
            ScrapeResult: Objeto con el contenido extraído o información del error.
        """
        ...

    @property
    def strategy_name(self) -> str:
        """
        Nombre identificador de la estrategia.

        Returns:
            str: Nombre de la clase (ej: "SeleniumStrategy").
        """
        return self.__class__.__name__

    def __repr__(self) -> str:
        """Representación string de la estrategia."""
        return f"<{self.strategy_name}>"
