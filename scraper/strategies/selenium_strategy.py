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

            # Obtener status code real de los performance logs
            status_code = 200  # Default si la pagina cargo
            try:
                perf_logs = driver.execute_cdp_cmd("Network.getResponseBody", {})
            except Exception:
                pass
            try:
                for entry in driver.get_log("performance"):
                    import json as _json
                    msg = _json.loads(entry["message"])["message"]
                    if msg.get("method") == "Network.responseReceived":
                        resp_url = msg["params"]["response"]["url"]
                        if resp_url.rstrip("/") == url.rstrip("/"):
                            status_code = msg["params"]["response"]["status"]
                            break
            except Exception:
                pass  # Performance logs no disponibles, usar 200
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
                "status_code":  status_code,
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

        # Anti-deteccion: eliminar flag navigator.webdriver
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, "webdriver", { get: () => undefined });
                Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, "languages", { get: () => ["es-ES", "es", "en"] });
                window.chrome = { runtime: {} };
            """
        })

        return driver

    @staticmethod
    def _build_options() -> Options:
        import random
        opts = Options()
        if settings.SELENIUM_HEADLESS:
            opts.add_argument("--headless=new")

        # Anti-deteccion: User-Agent aleatorio
        ua = random.choice(settings.USER_AGENT_POOL)
        opts.add_argument(f"user-agent={ua}")

        # Anti-deteccion: Ocultar que es webdriver
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        opts.add_experimental_option("useAutomationExtension", False)

        # Fingerprint de navegador real
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-infobars")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-popup-blocking")
        opts.add_argument("--lang=es-ES")
        opts.add_argument("--accept-lang=es-ES,es;q=0.9,en;q=0.8")

        # Logging para captura de errores JS y performance (status codes)
        opts.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})

        return opts