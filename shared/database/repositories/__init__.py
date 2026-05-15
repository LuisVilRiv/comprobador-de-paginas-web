"""
repositories — Módulos de acceso a datos separados por dominio.

Uso:
    from shared.database.repositories import dashboard, scraper

    clients  = dashboard.list_clients()
    websites = scraper.get_active_websites()
"""
from . import dashboard, scraper

__all__ = ["dashboard", "scraper"]