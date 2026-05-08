from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException

from scraper.base.base_scraper import BaseScraper
from scraper.models.scrape_result import ScrapeResult
from config import settings
from config.logging_config import setup_logger

logger = setup_logger(__name__)


class SeleniumStrategy(BaseScraper):
    """
    Estrategia 1 — Selenium (ChromeDriver).

    Indicada para páginas que requieren JavaScript para renderizar
    su contenido: SPAs, lazy-loading, paginación dinámica, etc.

    El driver se crea y destruye en cada llamada a `_do_scrape`
    para evitar estados colgados entre peticiones.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._chrome_options = self._build_options()

    # ── Implementación del contrato BaseScraper ───────────────────────────────

    def _do_scrape(self, url: str) -> ScrapeResult:
        driver = self._create_driver()
        try:
            start = time.perf_counter()
            driver.get(url)
            WebDriverWait(driver, settings.SELENIUM_IMPLICIT_WAIT).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            elapsed_ms  = int((time.perf_counter() - start) * 1000)
            raw_html    = driver.page_source
            page_title  = driver.title
            current_url = driver.current_url
        except TimeoutException as exc:
            raise RuntimeError(f"Timeout esperando body en {url}") from exc
        except WebDriverException as exc:
            raise RuntimeError(f"WebDriverException: {exc}") from exc
        finally:
            driver.quit()

        # Parsear con BS4 para obtener HTML indentado y legible
        soup = BeautifulSoup(raw_html, settings.BS4_PARSER)

        return ScrapeResult(
            url=url,
            strategy=self.strategy_name,
            content=soup.prettify(),
            metadata={
                "page_title":  page_title,
                "final_url":   current_url,
                "js_rendered": True,
                "response_time_ms": elapsed_ms,
            },
        )

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _create_driver(self) -> webdriver.Chrome:
        service = (
            Service(settings.SELENIUM_DRIVER_PATH)
            if settings.SELENIUM_DRIVER_PATH
            else Service()
        )
        driver = webdriver.Chrome(service=service, options=self._chrome_options)
        driver.set_page_load_timeout(settings.SELENIUM_PAGE_LOAD_TIMEOUT)
        return driver

    @staticmethod
    def _build_options() -> Options:
        opts = Options()
        if settings.SELENIUM_HEADLESS:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(f"user-agent={settings.DEFAULT_HEADERS['User-Agent']}")
        opts.add_experimental_option("excludeSwitches", ["enable-logging"])
        return opts