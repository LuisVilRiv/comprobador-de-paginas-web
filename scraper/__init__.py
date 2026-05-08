"""
Paquete principal del scraper.
Expone las clases de uso más frecuente para imports cómodos.
"""
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