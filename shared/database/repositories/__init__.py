"""
repositories — Módulos de acceso a datos separados por dominio.

Uso:
    from shared.database.repositories import dashboard, scraper

    # Operaciones del dashboard
    clients = dashboard.list_clients()

    # Operaciones del scraper
    websites = scraper.get_active_websites()
"""
from . import dashboard, scraper

__all__ = ["dashboard", "scraper"]
    "update_setting",
    "get_setting",
]