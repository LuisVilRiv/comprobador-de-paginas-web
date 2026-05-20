import requests
import time
from bs4 import BeautifulSoup
from requests.exceptions import RequestException, Timeout, ConnectionError

from scraper.base.base_scraper import BaseScraper
from scraper.models.scrape_result import ScrapeResult
from config import settings
from config.logging_config import setup_logger

logger = setup_logger(__name__)


class BeautifulSoupStrategy(BaseScraper):
    """
    Estrategia 2 — requests + BeautifulSoup.

    Indicada para páginas HTML estáticas o con contenido ya presente
    en la respuesta HTTP (sin necesidad de ejecutar JavaScript).
    Es más rápida y ligera que Selenium.

    La sesión de requests se reutiliza entre llamadas para aprovechar
    el pool de conexiones HTTP.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session = self._build_session()

    # ── Implementación del contrato BaseScraper ───────────────────────────────

    def _do_scrape(self, url: str) -> ScrapeResult:
        try:
            start = time.perf_counter()
            response = self._session.get(url, timeout=settings.REQUEST_TIMEOUT)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            if response.status_code >= 400:
                logger.warning("Respuesta HTTP con código de error %d para %s", response.status_code, url)
        except Timeout as exc:
            raise RuntimeError(f"Timeout al conectar con {url}") from exc
        except ConnectionError as exc:
            raise RuntimeError(f"Error de conexión con {url}") from exc
        except RequestException as exc:
            raise RuntimeError(f"Error HTTP o de red al conectar con {url}: {exc}") from exc

        soup = BeautifulSoup(
            response.content,
            settings.BS4_PARSER,
            from_encoding=settings.BS4_ENCODING,
        )

        return ScrapeResult(
            url=url,
            strategy=self.strategy_name,
            content=soup.prettify(),
            metadata={
                "page_title":   soup.title.string if soup.title else None,
                "status_code":  response.status_code,
                "content_type": response.headers.get("Content-Type", ""),
                "js_rendered":  False,
                "response_time_ms": elapsed_ms,
            },
        )

    # ── Helpers privados ──────────────────────────────────────────────────────

    @staticmethod
    def _build_session() -> requests.Session:
        import random
        session = requests.Session()
        headers = dict(settings.DEFAULT_HEADERS)
        # Anti-deteccion: User-Agent aleatorio por sesion
        headers["User-Agent"] = random.choice(settings.USER_AGENT_POOL)
        session.headers.update(headers)
        return session

    def close(self) -> None:
        """Cierra la sesión HTTP. Llamar al finalizar si se usa como contexto."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()