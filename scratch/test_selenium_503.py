import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
from scraper.strategies.selenium_strategy import SeleniumStrategy
from shared.auditor.auditor_modules.core import QualityAuditor

async def main():
    url = "https://httpstat.us/503"  # returns 503 with simple HTML
    # Use SeleniumStrategy to fetch page
    strategy = SeleniumStrategy()
    html, meta = strategy.fetch(url)
    metadata = {"status_code": meta.get("status_code", 200)}
    auditor = QualityAuditor()
    report = auditor.build_report(html=html, base_url=url, metadata=metadata)
    print("Score:", report.score)
    print("Status:", report.status)
    print("Release blocked:", report.release_blocked)
    print("Technical issues:", report.technical_issues)
    print("Content issues:", report.content_issues)
    print("Release blockers:", report.release_blockers)

if __name__ == "__main__":
    asyncio.run(main())
