"""
check_network — Funciones de utilidad para realizar peticiones de red.
"""

import time
from typing import Tuple

import requests

from config import settings


def check_url(
    session: requests.Session,
    url: str,
    method: str = "GET",
    allow_redirects: bool = True,
    timeout: int = settings.REQUEST_TIMEOUT,
) -> Tuple[bool, int, int | None, str]:
    """Comprueba si una URL es accesible y devuelve el estado y la latencia."""
    start_time = time.time()
    final_url = url
    try:
        # Usar GET en lugar de HEAD para evitar falsos negativos con servidores
        # que no responden bien a HEAD. El stream=True evita descargar el cuerpo.
        resp = session.request(
            method,
            url,
            timeout=timeout,
            allow_redirects=allow_redirects,
            stream=True,
        )
        final_url = resp.url
        # La propiedad .ok cubre el rango 200-299
        is_ok = resp.ok
        status_code = resp.status_code
        resp.close()  # Es importante cerrar la respuesta para liberar la conexión
    except requests.exceptions.RequestException:
        is_ok = False
        status_code = None
    finally:
        elapsed_ms = int((time.time() - start_time) * 1000)

    return is_ok, elapsed_ms, status_code, final_url
