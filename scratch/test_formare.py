import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import warnings
warnings.filterwarnings("ignore")

from shared.auditor.auditor_modules.core import QualityAuditor

url = "https://www.formaredigitalaanfp.ro/"

print(f"Fetching {url} ...")
try:
    resp = requests.get(url, timeout=20, verify=False, headers={"User-Agent": "Mozilla/5.0"})
    html = resp.text
    status_code = resp.status_code
except Exception as e:
    html = ""
    status_code = 0
    print(f"Error al conectar: {e}")

print(f"HTTP status code real: {status_code}")
print(f"HTML snippet (primeros 500 chars): {html[:500]!r}")
print()

metadata = {"status_code": status_code}
auditor = QualityAuditor()
report = auditor.build_report(html=html, base_url=url, metadata=metadata)

print(f"Score:           {report.score}")
print(f"Status:          {report.status}")
print(f"Release blocked: {report.release_blocked}")
print(f"Technical issues:")
for i in report.technical_issues:
    print(f"  - {i}")
print(f"Release blockers:")
for i in report.release_blockers:
    print(f"  - {i}")
