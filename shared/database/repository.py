"""
repository.py — STUB DE COMPATIBILIDAD.
Los imports del código antiguo (shared.database.repository) siguen
funcionando. Migrar gradualmente a repositories.scraper y repositories.dashboard.
"""
from .repositories.scraper import (
    get_active_websites, get_inactive_websites, get_pending_audit_websites,
    clear_pending_audit, create_run, save_audit_run, get_settings, update_setting,
)
from .repositories.dashboard import (
    list_clients, list_websites, website_status, website_runs,
    run_detail, run_sections, run_issues, global_summary,
    create_client, update_client, delete_client,
    create_website, update_website, delete_website,
    trigger_manual_audit, update_settings,
)

__all__ = [
    "get_active_websites", "get_inactive_websites", "get_pending_audit_websites",
    "clear_pending_audit", "create_run", "save_audit_run",
    "list_clients", "list_websites", "website_status", "website_runs",
    "run_detail", "run_sections", "run_issues", "global_summary",
    "create_client", "update_client", "delete_client",
    "create_website", "update_website", "delete_website",
    "trigger_manual_audit", "update_settings", "get_settings", "update_setting",
]
