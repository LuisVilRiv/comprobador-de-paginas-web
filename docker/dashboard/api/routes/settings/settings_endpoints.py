"""
================================================================================
SETTINGS_ENDPOINTS.PY - Endpoints para Configuración del Sistema
================================================================================

DESCRIPCIÓN:
Este módulo define los endpoints para gestionar la configuración global del
sistema de auditoría, incluyendo las expresiones CRON que controlan la
frecuencia de auditorías para websites activos e inactivos.

ENDPOINTS:
- GET /settings - Obtener configuración actual y estado del scheduler
- PUT /settings - Actualizar configuración (expresiones CRON)

@version 1.1.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
from fastapi import APIRouter, HTTPException

# Importar repositorio de base de datos
from shared.database.repositories import dashboard as repo

# Importar esquema de validación
from schemas.settings import SettingsUpdate

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

# Crear router con prefijo "/settings" y etiqueta "settings" para Swagger
router = APIRouter(prefix="/settings", tags=["settings"])

# Ruta al archivo de estado del scheduler (creado por el scraper)
SCHEDULE_STATUS_FILE = "/app/config/schedule_status.json"

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("")
def get_settings():
    """
    Obtiene la configuración actual del sistema y el estado del scheduler.
    
    Combina la configuración CRON de la base de datos con la información
    de próxima ejecución del archivo de estado del scheduler.

    Returns:
        dict: Configuración que incluye:
            - cron_active: Frecuencia para websites activos
            - cron_inactive: Frecuencia para websites inactivos
            - next_active_timestamp: Timestamp de la próxima ejecución activa
            - next_inactive_timestamp: Timestamp de la próxima ejecución inactiva
    """
    db_settings = repo.get_settings()
    schedule_status = {}

    if os.path.exists(SCHEDULE_STATUS_FILE):
        try:
            with open(SCHEDULE_STATUS_FILE, 'r') as f:
                schedule_status = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            # Si hay un error, el scheduler aún no ha escrito o el archivo es inválido
            # Se devolverá un objeto vacío para el estado, no es un error fatal.
            pass # Loggear esto podría ser útil en producción
    
    # Fusionar ambos diccionarios
    # Los valores de db_settings son la base
    # Los de schedule_status complementan/sobreescriben si existen
    combined_settings = {
        **db_settings,
        "next_active_timestamp": schedule_status.get("next_active_timestamp"),
        "next_inactive_timestamp": schedule_status.get("next_inactive_timestamp"),
    }
    
    return combined_settings


@router.put("")
def update_settings(payload: SettingsUpdate):
    """
    Actualiza la configuración del sistema.
    
    Args:
        payload (SettingsUpdate): Nueva configuración con expresiones CRON.
    
    Returns:
        dict: Mensaje de confirmación.
    
    Raises:
        HTTPException: 500 si hay un error al actualizar la configuración.
    """
    try:
        repo.update_settings(
            cron_active=payload.cron_active,
            cron_inactive=payload.cron_inactive
        )
        return {"message": "Configuración actualizada correctamente"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
