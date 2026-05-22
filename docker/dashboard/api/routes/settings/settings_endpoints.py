"""
================================================================================
SETTINGS_ENDPOINTS.PY - Endpoints para Configuración del Sistema
================================================================================

DESCRIPCIÓN:
Este módulo define los endpoints para gestionar la configuración global del
sistema de auditoría, incluyendo las expresiones CRON que controlan la
frecuencia de auditorías para websites activos e inactivos.

ENDPOINTS:
- GET /settings - Obtener configuración actual del sistema
- PUT /settings - Actualizar configuración (expresiones CRON)

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("")
def get_settings():
    """
    Obtiene la configuración actual del sistema.
    
    Returns:
        dict: Configuración con expresiones CRON para:
            - cron_active: Frecuencia para websites activos
            - cron_inactive: Frecuencia para websites inactivos
    """
    return repo.get_settings()


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