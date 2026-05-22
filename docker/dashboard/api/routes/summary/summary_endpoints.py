"""
SUMMARY_ENDPOINTS.PY - Endpoints para Resumen de Métricas del Dashboard

DESCRIPCIÓN:
Este módulo define los endpoints para obtener métricas agregadas del sistema,
que se muestran en el dashboard principal para dar una visión general del
estado de las auditorías.

ENDPOINTS:
- GET /summary - Métricas globales (webs activas, puntuaciones excelentes, próximos ciclos)

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter

# Importar repositorio de base de datos
from shared.database.repositories import dashboard as repo

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

# Crear router con etiqueta "summary" para Swagger
router = APIRouter(tags=["summary"])

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/summary")
def global_summary():
    """
    Obtiene el resumen de métricas globales del sistema.
    
    Returns:
        dict: Métricas agregadas incluyendo:
            - active_websites: Total de websites activos
            - excellent_count: Websites con puntuación excelente (>= 90)
            - next_active: Timestamp del próximo ciclo para websites activos
            - next_inactive: Timestamp del próximo ciclo para websites inactivos
    """
    return repo.global_summary()
