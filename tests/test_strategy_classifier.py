import pytest
from unittest.mock import MagicMock
from docker.scraper.service import AuditService
from scraper.models.scrape_result import ScrapeResult


class MockStrategy:
    def __init__(self, status="success", content="", metadata=None):
        self.status = status
        self.content = content
        self.metadata = metadata or {}

    def scrape(self, url):
        return ScrapeResult(
            url=url,
            status=self.status,
            content=self.content,
            strategy="BeautifulSoupStrategy",
            metadata=self.metadata,
            error=None if self.status == "success" else "Error scraping"
        )


@pytest.fixture
def base_context():
    return MagicMock()


@pytest.fixture
def base_auditor():
    return MagicMock()


def test_classify_classic_ssr(base_context, base_auditor):
    # Heurística: Mucho texto, sin contenedores SPA vacíos, sin bundles JS pesados
    html = """
    <html>
        <body>
            <header><h1>Mi Blog de Recetas</h1></header>
            <main>
                <article>
                    <h2>Receta de Tarta de Manzana</h2>
                    <p>La tarta de manzana es una tarta de fruta elaborada con una masa recubierta de manzana.</p>
                    <p>Para hacerla necesitas manzanas, harina, mantequilla, azúcar y huevos.</p>
                    <p>Mezcla todos los ingredientes secos, añade la mantequilla y amasa hasta tener una masa homogénea.</p>
                </article>
            </main>
        </body>
    </html>
    """
    bs_mock = MockStrategy(content=html)
    strategy_registry = {
        "beautifulsoup": bs_mock,
        "selenium": MagicMock()
    }
    service = AuditService(base_context, base_auditor, strategy_registry, ["beautifulsoup", "selenium"])
    
    res, recommended = service.classify_and_scrape("https://recetas.com")
    assert recommended == "beautifulsoup"
    assert res is not None
    assert "Receta de Tarta de Manzana" in res.content


def test_classify_empty_spa_root(base_context, base_auditor):
    # Heurística: Contenedor SPA típico con poco o ningún texto (SPA pura)
    html = """
    <html>
        <body>
            <div id="root">
                <!-- React mounts here -->
            </div>
            <script src="/static/js/main.chunk.js"></script>
        </body>
    </html>
    """
    bs_mock = MockStrategy(content=html)
    strategy_registry = {
        "beautifulsoup": bs_mock,
        "selenium": MagicMock()
    }
    service = AuditService(base_context, base_auditor, strategy_registry, ["beautifulsoup", "selenium"])
    
    res, recommended = service.classify_and_scrape("https://spa-react.com")
    assert recommended == "selenium"
    assert res is None  # Debe requerir scrapeo con Selenium, por ende no devuelve el pre-fetch de BS


def test_classify_thin_content_heavy_js(base_context, base_auditor):
    # Heurística: Menos de 80 palabras y más de 5000 chars de scripts
    script_content = "console.log('js pesado');" * 300  # > 7000 chars
    html = f"""
    <html>
        <body>
            <p>Página de carga rápida</p>
            <script>{script_content}</script>
        </body>
    </html>
    """
    bs_mock = MockStrategy(content=html)
    strategy_registry = {
        "beautifulsoup": bs_mock,
        "selenium": MagicMock()
    }
    service = AuditService(base_context, base_auditor, strategy_registry, ["beautifulsoup", "selenium"])
    
    res, recommended = service.classify_and_scrape("https://heavy-js.com")
    assert recommended == "selenium"
    assert res is None


def test_classify_react_bundle_js(base_context, base_auditor):
    # Heurística: Poco texto (<150 palabras) y script de bundle React
    html = """
    <html>
        <body>
            <h1>Cargando aplicación web...</h1>
            <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
        </body>
    </html>
    """
    bs_mock = MockStrategy(content=html)
    strategy_registry = {
        "beautifulsoup": bs_mock,
        "selenium": MagicMock()
    }
    service = AuditService(base_context, base_auditor, strategy_registry, ["beautifulsoup", "selenium"])
    
    res, recommended = service.classify_and_scrape("https://react-app.com")
    assert recommended == "selenium"
    assert res is None


def test_classify_vue_bundle_js(base_context, base_auditor):
    # Heurística: Poco texto y script de bundle Vue
    html = """
    <html>
        <body>
            <h1>Cargando aplicación Vue...</h1>
            <script src="/js/chunk-vendors.vue.js"></script>
        </body>
    </html>
    """
    bs_mock = MockStrategy(content=html)
    strategy_registry = {
        "beautifulsoup": bs_mock,
        "selenium": MagicMock()
    }
    service = AuditService(base_context, base_auditor, strategy_registry, ["beautifulsoup", "selenium"])
    
    res, recommended = service.classify_and_scrape("https://vue-app.com")
    assert recommended == "selenium"
    assert res is None


def test_classify_angular_bundle_js(base_context, base_auditor):
    # Heurística: Poco texto y script de bundle Angular
    html = """
    <html>
        <body>
            <app-root></app-root>
            <script src="/runtime-es2015.js"></script>
            <script src="/main-es2015.js"></script>
        </body>
    </html>
    """
    bs_mock = MockStrategy(content=html)
    strategy_registry = {
        "beautifulsoup": bs_mock,
        "selenium": MagicMock()
    }
    service = AuditService(base_context, base_auditor, strategy_registry, ["beautifulsoup", "selenium"])
    
    res, recommended = service.classify_and_scrape("https://angular-app.com")
    assert recommended == "selenium"
    assert res is None


def test_classify_fallback_if_selenium_missing(base_context, base_auditor):
    # Heurística: Debería clasificarse como Selenium pero Selenium no está registrado
    html = """
    <html>
        <body>
            <div id="app"></div>
            <script src="/static/react-bundle.js"></script>
        </body>
    </html>
    """
    bs_mock = MockStrategy(content=html)
    # Registry no posee selenium
    strategy_registry = {
        "beautifulsoup": bs_mock
    }
    service = AuditService(base_context, base_auditor, strategy_registry, ["beautifulsoup"])
    
    res, recommended = service.classify_and_scrape("https://no-selenium.com")
    assert recommended == "beautifulsoup"  # Hace fallback a BeautifulSoup
    assert res is not None  # Retorna el pre-fetched result de BS4
    assert "<div id=\"app\"></div>" in res.content


def test_classify_failsafe_empty_body(base_context, base_auditor):
    # Heurística: Cuerpo completamente vacío, pre-fetch da error
    bs_mock = MockStrategy(status="error")
    strategy_registry = {
        "beautifulsoup": bs_mock,
        "selenium": MagicMock()
    }
    service = AuditService(base_context, base_auditor, strategy_registry, ["beautifulsoup", "selenium"])
    
    res, recommended = service.classify_and_scrape("https://error-site.com")
    assert recommended == "selenium"
    assert res is None
