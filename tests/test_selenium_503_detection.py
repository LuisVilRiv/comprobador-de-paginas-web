import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scraper.strategies.selenium_strategy import SeleniumStrategy
from shared.auditor.auditor_modules.core import QualityAuditor
import pytest
@pytest.mark.slow
def test_selenium_fallback_503_detection():
    """Ensure SeleniumStrategy fallback via HEAD detects 503 error pages.
    Uses httpstat.us which returns a 503 status code with a simple error page.
    """
    url = "https://httpstat.us/503"
    strategy = SeleniumStrategy()
    result = strategy.scrape(url)
    html = result.content
    metadata = result.metadata
    # metadata should contain the real status_code from fallback
    assert metadata.get("status_code") == 503
    auditor = QualityAuditor()
    report = auditor.build_report(html=html, base_url=url, metadata=metadata)
    # The report must flag the site as inoperative (critical score 5)
    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    # Verify that an appropriate technical issue is present
    assert any("Sitio web no operativo" in issue for issue in report.technical_issues)
