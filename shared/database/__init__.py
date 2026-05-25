"""
shared/database/__init__.py

Re-exporta los símbolos públicos del paquete.
NO contiene lógica: cada responsabilidad vive en su propio módulo.

    connection.py   → engine, get_db
    models.py       → modelos ORM
    repositories/   → lógica de acceso a datos
"""

from shared.database import repositories
from shared.database.connection import get_db
from shared.database.models import (
    AuditIssue,
    AuditRun,
    AuditRunSection,
    Base,
    Client,
    GlobalSetting,
    Website,
)

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
]
