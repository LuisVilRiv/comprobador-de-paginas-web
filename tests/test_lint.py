"""Tests que verifican que el código pasa lint (ruff + eslint)."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

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


def _find_npx() -> str | None:
    """Find the npx executable, handling Windows where it may be npx.cmd."""
    npx = shutil.which("npx")
    if npx:
        return npx
    if sys.platform == "win32":
        return shutil.which("npx.cmd")
    return None


def test_eslint():
    """El código JavaScript del dashboard debe pasar eslint sin errores."""
    npx = _find_npx()
    if npx is None:
        pytest.skip("npx not found in PATH")
    dashboard = ROOT / "docker" / "dashboard"
    result = subprocess.run(
        [npx, "eslint", "frontend/", "server.js"],
        cwd=dashboard,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"eslint falló:\n{result.stdout}\n{result.stderr}"
