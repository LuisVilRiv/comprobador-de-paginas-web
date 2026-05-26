"""
checks/__init__.py - Punto de entrada para el paquete de módulos de auditoría.
"""

# Importar funciones clave para que estén disponibles en el nivel superior del paquete.

from .browser import check_js_console_errors, interact_buttons_selenium
from .buttons import check_buttons
from .content import check_content
from .images import check_images
from .links import check_links_recursive
from .network import check_url
from .security import check_security
from .seo import check_seo
from .structure import check_structure
from .technical import check_technical

__all__ = [
    "check_js_console_errors",
    "interact_buttons_selenium",
    "check_buttons",
    "check_content",
    "check_images",
    "check_links_recursive",
    "check_url",
    "check_security",
    "check_seo",
    "check_structure",
    "check_technical",
]
