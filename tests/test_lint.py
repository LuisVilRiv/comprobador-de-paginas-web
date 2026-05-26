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


def _find_npx() -> str | None:
    """Find npx executable, checking common Node.js install paths on Windows."""
    import os
    import shutil

    npx = shutil.which("npx")
    if npx:
        return npx
    # On Windows, Node.js may be installed but not in the current process PATH
    if os.name == "nt":
        program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        candidate = os.path.join(program_files, "nodejs", "npx.cmd")
        if os.path.isfile(candidate):
            return candidate
    return None


def test_eslint():
    """El código JavaScript del dashboard debe pasar eslint sin errores."""
    import pytest

    npx = _find_npx()
    if not npx:
        pytest.skip("npx no encontrado en PATH; ESLint no disponible")
    dashboard = ROOT / "docker" / "dashboard"
    result = subprocess.run(
        [npx, "eslint", "frontend/", "server.js"],
        cwd=dashboard,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"eslint falló:\n{result.stdout}\n{result.stderr}"
