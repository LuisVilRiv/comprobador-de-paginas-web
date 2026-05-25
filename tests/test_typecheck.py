"""Test que verifica que el código pasa typecheck (mypy)."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MYPY_DIRS = [
    "config/",
    "shared/",
    "scraper/",
    "docker/dashboard/api/",
    "docker/scraper/",
]


def test_mypy_typecheck():
    """Los módulos principales deben pasar mypy sin errores."""
    result = subprocess.run(
        ["mypy", *MYPY_DIRS],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"mypy falló:\n{result.stdout}\n{result.stderr}"
