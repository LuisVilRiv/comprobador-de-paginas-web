"""
repositories/dashboard/ — Fachada de acceso a BD para la API del dashboard.
Delega en módulos especializados por dominio.
"""

from .clients import create_client, delete_client, list_clients, update_client
from .runs import run_detail, run_issues, run_sections, runs_history_for_pdf, website_runs
from .settings import get_settings, update_settings
from .summary import global_summary
from .websites import (
    create_website,
    delete_website,
    list_websites,
    trigger_manual_audit,
    update_website,
    website_status,
)

__all__ = [
    "list_clients",
    "create_client",
    "update_client",
    "delete_client",
    "list_websites",
    "website_status",
    "create_website",
    "update_website",
    "delete_website",
    "trigger_manual_audit",
    "website_runs",
    "run_detail",
    "run_sections",
    "run_issues",
    "runs_history_for_pdf",
    "global_summary",
    "get_settings",
    "update_settings",
]
