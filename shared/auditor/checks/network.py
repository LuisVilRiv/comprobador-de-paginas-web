"""
check_network — Funciones de utilidad para realizar peticiones de red.
"""

from __future__ import annotations

import time

import requests

from config import settings


def check_url(
    session: requests.Session,
    url: str,
    method: str = "GET",
    allow_redirects: bool = True,
    timeout: int = settings.REQUEST_TIMEOUT,
    include_content: bool = False,
) -> tuple[bool, int, int | None, str]:
    """Comprueba si una URL es accesible y devuelve el estado y la latencia."""
    start_time = time.time()
    content = ""
    try:
        resp = session.request(
            method,
            url,
            timeout=timeout,
            allow_redirects=allow_redirects,
            stream=not include_content,
        )
        is_ok = resp.ok
        status_code = resp.status_code
        if include_content:
            content = resp.text
        resp.close()
    except requests.exceptions.RequestException:
        is_ok = False
        status_code = None
    finally:
        elapsed_ms = int((time.time() - start_time) * 1000)

    return is_ok, elapsed_ms, status_code, content
