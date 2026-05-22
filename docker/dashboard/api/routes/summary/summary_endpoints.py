"""
SUMMARY_ENDPOINTS.PY - Endpoints para Resumen de Métricas del Dashboard

DESCRIPCIÓN:
Este módulo define los endpoints para obtener métricas agregadas del sistema,
que se muestran en el dashboard principal para dar una visión general del
estado de las auditorías.

ENDPOINTS:
- GET /summary - Métricas globales (webs activas, puntuaciones excelentes, próximos ciclos)

@version 1.1.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
from fastapi import APIRouter

# Importar repositorio de base de datos
from shared.database.repositories import dashboard as repo

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

# Crear router con etiqueta "summary" para Swagger
router = APIRouter(tags=["summary"])

# Ruta al archivo de estado del scheduler (creado por el scraper)
SCHEDULE_STATUS_FILE = "/app/config/schedule_status.json"

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
    summary_data = repo.global_summary()
    schedule_status = {}

    if os.path.exists(SCHEDULE_STATUS_FILE):
        try:
            with open(SCHEDULE_STATUS_FILE, 'r') as f:
                schedule_status = json.load(f)
        except (IOError, json.JSONDecodeError):
            # Si hay un error, el scheduler aún no ha escrito o el archivo es inválido.
            # No es un error fatal, se devolverá un objeto vacío para el estado.
            pass
    
    # Fusionar los datos del repositorio con el estado del scheduler
    combined_data = {
        **summary_data,
        "next_active": schedule_status.get("next_active_timestamp"),
        "next_inactive": schedule_status.get("next_inactive_timestamp"),
    }
    
    return combined_data
