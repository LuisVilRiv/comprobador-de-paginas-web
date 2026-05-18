"""
repositories/dashboard/ — Fachada de acceso a BD para la API del dashboard.
Delega en módulos especializados por dominio.
"""
from .clients import (
    list_clients, create_client, update_client, delete_client
)
from .websites import (
    list_websites, website_status, create_website, update_website,
    delete_website, trigger_manual_audit
)
from .runs import (
    website_runs, run_detail, run_sections, run_issues, runs_history_for_pdf
)
from .summary import global_summary
from .settings import get_settings, update_settings

__all__ = [
    "list_clients", "create_client", "update_client", "delete_client",
    "list_websites", "website_status", "create_website", "update_website",
    "delete_website", "trigger_manual_audit",
    "website_runs", "run_detail", "run_sections", "run_issues", "runs_history_for_pdf",
    "global_summary",
    "get_settings", "update_settings",
]
