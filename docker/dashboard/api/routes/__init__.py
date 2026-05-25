"""
ROUTES/__INIT__.PY - Paquete de Routers de la API

DESCRIPCIÓN:
Este paquete centraliza y exporta todos los routers de la API REST.
Cada submódulo contiene los endpoints relacionados con una entidad específica
(clientes, websites, auditorías, etc.).

ESTRUCTURA:
- clients: Gestión de clientes (CRUD + exportación PDF)
- health: Health check del servicio
- runs: Historial y detalles de auditorías
- settings: Configuración del scheduler de auditorías
- summary: Métricas y resumen del dashboard
- websites: Gestión de sitios web (CRUD + auditorías)

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# Importar y exportar todos los routers
# Cada router se importa desde su submódulo correspondiente
from .clients import router as clients_router  # /api/clients
from .health import router as health_router  # /health
from .runs import router as runs_router  # /api/runs
from .settings import router as settings_router  # /api/settings
from .summary import router as summary_router  # /api/summary
from .websites import router as websites_router  # /api/websites

# Lista de routers disponibles para importación
__all__ = [
    "clients_router",
    "health_router",
    "runs_router",
    "settings_router",
    "summary_router",
    "websites_router",
]
