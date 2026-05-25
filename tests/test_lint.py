"""Tests que verifican que el código pasa lint (ruff + eslint)."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_ruff_lint():
    """Todo el código Python debe pasar ruff check sin errores."""
    result = subprocess.run(
        ["ruff", "check", "."],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"ruff check falló:\n{result.stdout}\n{result.stderr}"


def test_eslint():
    """El código JavaScript del dashboard debe pasar eslint sin errores."""
    dashboard = ROOT / "docker" / "dashboard"
    result = subprocess.run(
        ["npx", "eslint", "frontend/", "server.js"],
        cwd=dashboard,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"eslint falló:\n{result.stdout}\n{result.stderr}"
