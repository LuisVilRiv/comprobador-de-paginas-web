"""
Paquete database — ORM SQLAlchemy centralizado.

Estructura clara:
├── connection.py      # Configuración de conexión y engine SQLAlchemy
├── models.py          # Definición de modelos y relaciones
├── repositories/      # Lógica de acceso separada por dominio
│   ├── dashboard.py   # Operaciones del dashboard API
│   └── scraper.py     # Operaciones del proceso scraper
└── __init__.py        # Este archivo - exporta lo esencial

Uso recomendado:
    # Para modelos y conexión
    from shared.database import get_db, Client, Website, AuditRun

    # Para operaciones específicas
    from shared.database.repositories import dashboard, scraper

Compatibilidad backward:
    # Los imports antiguos siguen funcionando
    from shared.database import repository  # Proxy de compatibilidad
"""
# ── Exportaciones principales ───────────────────────────────────────────────
from .connection import get_db
from .models import (
    AuditIssue,
    AuditRun,
    AuditRunSection,
    Base,
    Client,
    GlobalSetting,
    Website,
)

# ── Namespaces de repositorios ──────────────────────────────────────────────
from . import repositories

# ── Compatibilidad backward ─────────────────────────────────────────────────
# Los módulos existentes importan desde shared.database.repository
# Mantenemos compatibilidad hasta migrar todos los imports
import shared.database.repositories.scraper as _rs
import shared.database.repositories.dashboard as _rd

class _CompatRepository:
    """Proxy de compatibilidad. Eliminar cuando se migren todos los imports."""
    # Scraper operations
    get_active_websites = staticmethod(_rs.get_active_websites)
    get_inactive_websites = staticmethod(_rs.get_inactive_websites)
    get_pending_audit_websites = staticmethod(_rs.get_pending_audit_websites)
    clear_pending_audit = staticmethod(_rs.clear_pending_audit)
    get_settings = staticmethod(_rs.get_settings)
    update_setting = staticmethod(_rs.update_setting)
    create_run = staticmethod(_rs.create_run)
    save_audit_run = staticmethod(_rs.save_audit_run)

    # Dashboard operations
    list_clients = staticmethod(_rd.list_clients)
    list_websites = staticmethod(_rd.list_websites)
    website_status = staticmethod(_rd.website_status)
    website_runs = staticmethod(_rd.website_runs)
    run_detail = staticmethod(_rd.run_detail)
    run_sections = staticmethod(_rd.run_sections)
    run_issues = staticmethod(_rd.run_issues)
    global_summary = staticmethod(_rd.global_summary)
    create_client = staticmethod(_rd.create_client)
    update_client = staticmethod(_rd.update_client)
    delete_client = staticmethod(_rd.delete_client)
    create_website = staticmethod(_rd.create_website)
    update_website = staticmethod(_rd.update_website)
    delete_website = staticmethod(_rd.delete_website)
    trigger_manual_audit = staticmethod(_rd.trigger_manual_audit)
    update_settings = staticmethod(_rd.update_settings)

repository = _CompatRepository()

__all__ = [
    "get_db",
    "Base",
    "Client",
    "Website",
    "AuditRun",
    "AuditRunSection",
    "AuditIssue",
    "GlobalSetting",
    "repositories",
    "repository",  # Para compatibilidad
]

__all__ = ["Base", "get_db", "repo_scraper", "repo_dashboard", "repository"]
