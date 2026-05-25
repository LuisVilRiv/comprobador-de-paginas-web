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


def test_eslint():
    """El código JavaScript del dashboard debe pasar eslint sin errores."""
    # En Windows npx se distribuye como npx.cmd; usar shutil.which para resolverlo
    npx_cmd = shutil.which("npx") or shutil.which("npx.cmd")
    if npx_cmd is None:
        pytest.skip("npx no está instalado o no está en PATH")

    dashboard = ROOT / "docker" / "dashboard"
    if not (dashboard / "node_modules").exists():
        pytest.skip("node_modules no instalados en docker/dashboard (ejecutar npm install)")

    # En Windows es necesario shell=True para ejecutar archivos .cmd
    use_shell = sys.platform == "win32"
    result = subprocess.run(
        [npx_cmd, "eslint", "frontend/", "server.js"],
        cwd=dashboard,
        capture_output=True,
        text=True,
        shell=use_shell,
    )
    assert result.returncode == 0, f"eslint falló:\n{result.stdout}\n{result.stderr}"
