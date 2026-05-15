"""Router package for dashboard API."""

from .clients import router as clients_router
from .health import router as health_router
from .settings import router as settings_router
from .summary import router as summary_router
from .websites import router as websites_router

__all__ = [
    "clients_router",
    "health_router",
    "settings_router",
    "summary_router",
    "websites_router",
]
