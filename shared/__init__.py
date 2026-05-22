"""
================================================================================
SHARED/__INIT__.PY - Paquete de Módulos Compartidos
================================================================================

DESCRIPCIÓN:
Este paquete contiene módulos y utilidades compartidas que son utilizadas
por múltiples componentes del sistema de auditoría web.

SUBPAQUETES:
- auditor: Módulos de auditoría y verificación de calidad web
- database: Conexión a base de datos, modelos ORM y repositorios
- utils: Utilidades generales (generación de PDFs, etc.)

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

__all__ = ["auditor", "database", "utils"]