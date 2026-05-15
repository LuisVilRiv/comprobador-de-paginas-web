"""
repositories/scraper/ — Fachada de acceso a BD para el proceso scraper.
Delega en módulos especializados por dominio.
"""
from .websites import (
    get_active_websites, get_inactive_websites,
    get_pending_audit_websites, clear_pending_audit
)
from .settings import get_settings, update_setting
from .runs import create_run, save_audit_run, update_run_progress

__all__ = [
    "get_active_websites", "get_inactive_websites",
    "get_pending_audit_websites", "clear_pending_audit",
    "get_settings", "update_setting",
    "create_run", "save_audit_run", "update_run_progress",
]
