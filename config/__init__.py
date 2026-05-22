"""
__init__.py para el paquete de configuración.

Este fichero, aunque mayormente vacío, es crucial para que Python reconozca
el directorio 'config' como un paquete, permitiendo importaciones como:

  from config.settings import DB_HOST

También es un buen lugar para inicializaciones a nivel de paquete, si fueran
necesarias en el futuro.

Nota sobre imports:
  - Evitar imports directos que carguen módulos pesados al inicio.
  - Usar __all__ para definir la API pública del paquete si se desea.
"""

# __all__ = ["settings", "logging_config"]

# Para facilitar el acceso, se puede hacer un "lifting" de las variables
# o funciones más comunes de los submódulos.

from .settings import get_secret, get_db_url, AppStage
from .logging_config import setup_logger
