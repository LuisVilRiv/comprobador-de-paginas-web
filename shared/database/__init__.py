"""
Paquete de base de datos compartido.
Importa explícitamente lo necesario; evita reexportar con *.
"""
from .models import Base, get_db

# Namespaces separados para scraper y dashboard
from . import repo_scraper
from . import repo_dashboard

# Alias de compatibilidad hacia atrás: los módulos existentes
# (entrypoint.py, api/main.py) importan desde shared.database.repository
# → redirigimos a los nuevos módulos hasta migrar los imports.
import shared.database.repo_scraper  as _rs
import shared.database.repo_dashboard as _rd

class _CompatRepository:
    """
    Proxy de compatibilidad.
    Eliminar cuando entrypoint.py y api/main.py usen los nuevos imports.
    """
    # Scraper
    get_active_websites       = staticmethod(_rs.get_active_websites)
    get_inactive_websites     = staticmethod(_rs.get_inactive_websites)
    get_pending_audit_websites= staticmethod(_rs.get_pending_audit_websites)
    clear_pending_audit       = staticmethod(_rs.clear_pending_audit)
    get_settings              = staticmethod(_rs.get_settings)
    update_setting            = staticmethod(_rs.update_setting)
    create_run                = staticmethod(_rs.create_run)
    save_audit_run            = staticmethod(_rs.save_audit_run)
    # Dashboard
    list_clients              = staticmethod(_rd.list_clients)
    list_websites             = staticmethod(_rd.list_websites)
    website_status            = staticmethod(_rd.website_status)
    website_runs              = staticmethod(_rd.website_runs)
    run_detail                = staticmethod(_rd.run_detail)
    run_sections              = staticmethod(_rd.run_sections)
    run_issues                = staticmethod(_rd.run_issues)
    global_summary            = staticmethod(_rd.global_summary)
    create_client             = staticmethod(_rd.create_client)
    update_client             = staticmethod(_rd.update_client)
    delete_client             = staticmethod(_rd.delete_client)
    create_website            = staticmethod(_rd.create_website)
    update_website            = staticmethod(_rd.update_website)
    delete_website            = staticmethod(_rd.delete_website)
    trigger_manual_audit      = staticmethod(_rd.trigger_manual_audit)
    update_settings           = staticmethod(_rd.update_settings)

repository = _CompatRepository()

__all__ = ["Base", "get_db", "repo_scraper", "repo_dashboard", "repository"]
