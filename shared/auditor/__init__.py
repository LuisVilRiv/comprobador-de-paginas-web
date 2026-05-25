"""
Paquete auditor.
Exporta QualityAuditor como punto de entrada principal.
Los submódulos de checks, modelos y scoring son internos.
"""

from .auditor_modules import QualityAuditor
from .models import QualityAuditReport

__all__ = ["QualityAuditor", "QualityAuditReport"]
