"""
SCRAPER/__INIT__.PY - Paquete Principal del Scraper

DESCRIPCIÓN:
Este paquete contiene el sistema de scraping web del auditor. Implementa un
patrón Strategy para permitir diferentes métodos de extracción (Selenium para
páginas dinámicas, BeautifulSoup para páginas estáticas).

COMPONENTES PRINCIPALES:
- ScraperContext: Contexto que gestiona la ejecución del scraping
- SeleniumStrategy: Estrategia para páginas con JavaScript dinámico
- BeautifulSoupStrategy: Estrategia para páginas HTML estáticas
- ScrapeResult: Modelo de resultado de scraping

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

from scraper.context.scraper_context import ScraperContext
from scraper.strategies.selenium_strategy import SeleniumStrategy
from scraper.strategies.beautifulsoup_strategy import BeautifulSoupStrategy
from scraper.models.scrape_result import ScrapeResult

__all__ = [
    "ScraperContext",
    "SeleniumStrategy",
    "BeautifulSoupStrategy",
    "ScrapeResult",
]
