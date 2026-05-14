"""
Módulos de comprobación individuales del auditor de calidad.
Cada módulo expone una función check_*(soup, ..., issues) que añade
incidencias a la lista `issues` recibida como parámetro.
"""
from .security  import check_security
from .seo       import check_seo
from .content   import check_content
from .images    import check_images
from .structure import check_structure
from .links     import check_links_recursive
from .buttons   import check_buttons
from .technical import check_technical

__all__ = [
    "check_security",
    "check_seo",
    "check_content",
    "check_images",
    "check_structure",
    "check_links_recursive",
    "check_buttons",
    "check_technical",
]
