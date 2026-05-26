import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper.strategies.selenium_strategy import SeleniumStrategy
from shared.auditor.auditor_modules.core import QualityAuditor

# Settings modules that need to be patched
_SETTINGS_PATCHES = [
    "shared.auditor.auditor_modules.core.settings",
    "shared.auditor.checks.security.settings",
    "shared.auditor.checks.links.settings",
    "shared.auditor.checks.content.settings",
    "shared.auditor.checks.browser.settings",
    "shared.auditor.checks.network.settings",
    "shared.auditor.auditor_modules.helpers.settings",
    "shared.auditor.scoring.settings",
]


def _configure_mock_settings(mock_s):
    """Configure all mock settings needed for a mocked auditor."""
    mock_s.AI_ANALYZER_ENABLED = False
    mock_s.AI_ANALYZER_URL = "http://localhost:8080"
    mock_s.AI_ANALYZER_TIMEOUT = 10
    mock_s.BS4_PARSER = "html.parser"
    mock_s.AUDIT_MAX_BROWSER_CONFIRMS = 3
    mock_s.AUDIT_MAX_RECURSIVE_LINKS = 5
    mock_s.AUDIT_MAX_CRAWL_DEPTH = 2
    mock_s.REQUEST_TIMEOUT = 10
    mock_s.DEFAULT_HEADERS = {}
    mock_s.AUDIT_MIN_WORD_COUNT = 50
    mock_s.AUDIT_KEYWORD_DENSITY_MAX = 0.35
    mock_s.AUDIT_JS_CONSOLE_MAX_ERRORS = 3
    mock_s.AUDIT_BUTTON_INTERACTION_ENABLED = False
    mock_s.AUDIT_BUTTON_MAX_CLICKS = 2
    mock_s.AUDIT_BANNED_HOSTS = []
    mock_s.AUDIT_BANNED_DOMAINS = []
    mock_s.SELENIUM_IMPLICIT_WAIT = 10
    mock_s.AUDIT_ADMIN_PATHS = ["/admin", "/wp-admin", "/wp-login.php"]
    mock_s.AUDIT_MAX_ADMIN_REDIRECTS = 3
    mock_s.USER_AGENT_POOL = ["Mozilla/5.0"]
    mock_s.AUDIT_SCORE_EXCELLENT_THRESHOLD = 90
    mock_s.AUDIT_SCORE_GOOD_THRESHOLD = 70
    mock_s.AUDIT_RELEASE_GATE_MIN_SCORE = 60
    mock_s.MAX_RETRIES = 3
    mock_s.RETRY_DELAY = 1
    mock_s.SELENIUM_DRIVER_PATH = ""
    mock_s.SELENIUM_HEADLESS = True
    mock_s.SELENIUM_PAGE_LOAD_TIMEOUT = 30
    mock_s.AUDIT_ADMIN_PROBE_PATHS = ["/admin", "/wp-admin"]
    mock_s.AUDIT_REQUEST_DELAY_SECONDS = 0


def _make_mock_session():
    """Create a mock session that returns 404 for admin paths and 200 for everything else."""
    mock_session = MagicMock()

    def _mock_request(url, **kwargs):
        resp = MagicMock()
        if any(admin_path in url for admin_path in ("/admin", "/wp-admin", "/wp-login")):
            resp.status_code = 404
            resp.text = "<html><body>Not Found</body></html>"
            resp.headers = {}
            resp.url = url
        else:
            resp.status_code = 200
            resp.text = "<html><body>OK</body></html>"
            resp.headers = {"Content-Type": "text/html"}
            resp.url = url
        return resp

    mock_session.get.side_effect = lambda url, **kwargs: _mock_request(url, **kwargs)
    mock_session.head.side_effect = lambda url, **kwargs: _mock_request(url, **kwargs)
    mock_session.request.side_effect = lambda method, url, **kwargs: _mock_request(url, **kwargs)
    mock_session.post.return_value = MagicMock(status_code=200, json=lambda: {})
    return mock_session


@pytest.fixture(autouse=True)
def _patch_all_settings():
    """Auto-use fixture that patches all settings modules for every test."""
    patches = [patch(p) for p in _SETTINGS_PATCHES]
    mocks = [p.start() for p in patches]
    for m in mocks:
        _configure_mock_settings(m)
    yield
    for p in patches:
        p.stop()


def test_selenium_fallback_503_detection():
    """Ensure SeleniumStrategy fallback via HEAD detects 503 error pages.
    Uses mocked HTTP response instead of calling a real external service.
    """
    url = "https://example.com/error-503"

    # Mock SeleniumStrategy.scrape to return a 503 result without real network calls
    mock_result = MagicMock()
    mock_result.content = """
    <html>
        <head><title>503 Service Unavailable</title></head>
        <body>
            <h1>503 Service Temporarily Unavailable</h1>
            <p>The server is temporarily unable to service your request due to maintenance downtime.</p>
        </body>
    </html>
    """
    mock_result.metadata = {"status_code": 503, "js_rendered": False}
    mock_result.status = "success"
    mock_result.strategy = "BeautifulSoupStrategy"

    with patch.object(SeleniumStrategy, "scrape", return_value=mock_result):
        strategy = SeleniumStrategy()
        result = strategy.scrape(url)

    html = result.content
    metadata = result.metadata

    # metadata should contain the status_code from fallback
    assert metadata.get("status_code") == 503

    auditor = QualityAuditor()
    auditor._session = _make_mock_session()
    auditor._driver = None

    report = auditor.build_report(html=html, base_url=url, metadata=metadata)

    # The report must flag the site as inoperative (critical score 5)
    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    # Verify that an appropriate technical issue is present
    assert any("Sitio web no operativo" in issue for issue in report.technical_issues)
