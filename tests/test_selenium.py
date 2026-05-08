import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from scraper.strategies.selenium_strategy import SeleniumStrategy
from scraper.models.scrape_result import ScrapeResult


@pytest.fixture
def strategy() -> SeleniumStrategy:
    return SeleniumStrategy()


def _mock_driver(page_source: str = "<html><body>JS Content</body></html>",
                 title: str = "Página de prueba",
                 current_url: str = "https://ejemplo.com") -> MagicMock:
    """Crea un mock de webdriver.Chrome."""
    driver = MagicMock()
    type(driver).page_source  = PropertyMock(return_value=page_source)
    type(driver).title        = PropertyMock(return_value=title)
    type(driver).current_url  = PropertyMock(return_value=current_url)
    return driver


class TestSeleniumScrape:
    def test_scrape_exitoso(self, strategy):
        mock_driver = _mock_driver()
        with patch.object(strategy, "_create_driver", return_value=mock_driver):
            with patch("scraper.strategies.selenium_strategy.WebDriverWait"):
                result = strategy.scrape("https://ejemplo.com")

        assert isinstance(result, ScrapeResult)
        assert result.status == "success"
        assert result.strategy == "SeleniumStrategy"
        assert "JS Content" in result.content
        mock_driver.quit.assert_called_once()

    def test_metadata_correcta(self, strategy):
        mock_driver = _mock_driver()
        with patch.object(strategy, "_create_driver", return_value=mock_driver):
            with patch("scraper.strategies.selenium_strategy.WebDriverWait"):
                result = strategy.scrape("https://ejemplo.com")

        assert result.metadata["js_rendered"] is True
        assert result.metadata["page_title"] == "Página de prueba"
        assert result.metadata["final_url"] == "https://ejemplo.com"

    def test_url_invalida_devuelve_error(self, strategy):
        result = strategy.scrape("no-es-una-url")
        assert result.status == "error"

    def test_driver_se_cierra_siempre(self, strategy):
        """Garantiza que driver.quit() se llama en cada intento aunque falle."""
        mock_driver = _mock_driver()
        mock_driver.get.side_effect = Exception("Error inesperado")
        with patch.object(strategy, "_create_driver", return_value=mock_driver):
            strategy.scrape("https://ejemplo.com")

        # quit() debe llamarse una vez por cada reintento (no solo una vez en total)
        assert mock_driver.quit.call_count == strategy.max_retries

    def test_fallo_total_devuelve_error_tras_reintentos(self, strategy):
        from selenium.common.exceptions import WebDriverException
        mock_driver = _mock_driver()
        mock_driver.get.side_effect = WebDriverException("fallo")
        with patch.object(strategy, "_create_driver", return_value=mock_driver):
            result = strategy.scrape("https://ejemplo.com")

        assert result.status == "error"
        assert mock_driver.quit.call_count == strategy.max_retries