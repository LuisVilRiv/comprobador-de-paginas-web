"""
repositories/scraper/ — Fachada de acceso a BD para el proceso scraper.
Delega en módulos especializados por dominio.
"""

from .runs import create_run, save_audit_run, update_run_progress
from .settings import get_settings, update_setting
from .websites import clear_pending_audit, get_active_websites, get_inactive_websites, get_pending_audit_websites

__all__ = [
    "get_active_websites",
    "get_inactive_websites",
    "get_pending_audit_websites",
    "clear_pending_audit",
    "get_settings",
    "update_setting",
    "create_run",
    "save_audit_run",
    "update_run_progress",
]
