"""
Módulos de comprobación individuales del auditor de calidad.
Cada módulo expone una función check_*(soup, ..., issues) que añade
incidencias a la lista `issues` recibida como parámetro.
"""

from .browser import check_js_console_errors, interact_buttons_selenium
from .buttons import check_buttons
from .content import check_content
from .images import check_images
from .links import check_links_recursive
from .security import check_security
from .seo import check_seo
from .structure import check_structure
from .technical import check_technical

__all__ = [
    "check_js_console_errors",
    "check_security",
    "check_seo",
    "check_content",
    "check_images",
    "check_structure",
    "check_links_recursive",
    "check_buttons",
    "check_technical",
    "interact_buttons_selenium",
]
