import time
from urllib.parse import urlparse

from config import settings
from config.logging_config import setup_logger
from scraper.base.scraper_strategy import ScraperStrategy
from scraper.models.scrape_result import ScrapeResult

logger = setup_logger(__name__)


class BaseScraper(ScraperStrategy):
    """
    Capa intermedia con lógica reutilizable por todas las estrategias:
      - Reintentos automáticos con backoff lineal.
      - Validación de URL antes de ejecutar.
      - Logging uniforme de inicio, éxito y error.

    Las estrategias concretas (Selenium, BS4) heredan de esta clase
    e implementan `_do_scrape`, no `scrape` directamente.
    """

    def __init__(
        self,
        max_retries: int = settings.MAX_RETRIES,
        retry_delay: float = settings.RETRY_DELAY,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    # ── Punto de entrada público ──────────────────────────────────────────────

    def scrape(self, url: str) -> ScrapeResult:
        """Orquesta validación + reintentos + logging."""
        if not self._is_valid_url(url):
            logger.warning("URL inválida: %s", url)
            return ScrapeResult.from_error(url, self.strategy_name, "URL inválida")
        if self._is_banned_url(url):
            logger.warning("URL bloqueada por política estricta: %s", url)
            return ScrapeResult.from_error(url, self.strategy_name, "URL bloqueada por política")

        logger.info("[%s] Iniciando scraping → %s", self.strategy_name, url)

        for attempt in range(1, self.max_retries + 1):
            try:
                result = self._do_scrape(url)
                logger.info(
                    "[%s] Éxito en intento %d/%d → %s",
                    self.strategy_name,
                    attempt,
                    self.max_retries,
                    url,
                )
                return result
            except Exception as exc:
                logger.warning(
                    "[%s] Intento %d/%d fallido para %s: %s",
                    self.strategy_name,
                    attempt,
                    self.max_retries,
                    url,
                    exc,
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)  # backoff lineal

        error_msg = f"Fallaron los {self.max_retries} intentos"
        logger.error("[%s] %s → %s", self.strategy_name, error_msg, url)
        return ScrapeResult.from_error(url, self.strategy_name, error_msg)

    # ── Método a implementar por las subclases ────────────────────────────────

    def _do_scrape(self, url: str) -> ScrapeResult:
        """
        Lógica específica de cada estrategia.
        Puede lanzar excepciones; BaseScraper las captura en `scrape`.
        """
        raise NotImplementedError

    # ── Utilidades privadas ───────────────────────────────────────────────────

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        return isinstance(url, str) and url.startswith(("http://", "https://"))

    @staticmethod
    def _is_banned_url(url: str) -> bool:
        host = BaseScraper._normalize_host(urlparse(url).netloc)
        banned = {BaseScraper._normalize_host(h) for h in settings.AUDIT_BANNED_HOSTS}
        return host in banned

    @staticmethod
    def _normalize_host(host: str) -> str:
        host = host.lower().strip()
        return host[4:] if host.startswith("www.") else host
