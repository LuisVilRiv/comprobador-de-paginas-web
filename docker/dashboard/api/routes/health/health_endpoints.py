"""
================================================================================
HEALTH_ENDPOINTS.PY - Endpoint de Verificación de Salud del Sistema
================================================================================

DESCRIPCIÓN:
Este módulo define un endpoint simple para verificar que la API está en
funcionamiento correcto. Es útil para monitoreo, balanceadores de carga
y sistemas de orquestación como Kubernetes o Docker Swarm.

ENDPOINTS:
- GET /health - Verifica que la API esté operativa

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

# Crear router con etiqueta "health" para Swagger
router = APIRouter(tags=["health"])

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/health")
def health():
    """
    Verifica que la API esté operativa.
    
    Returns:
        dict: Estado de salud con {"status": "ok"} si todo funciona correctamente.
    
    Note:
        Este endpoint es útil para:
        - Monitoreo de disponibilidad
        - Verificación de readiness/liveness en Kubernetes
        - Health checks en balanceadores de carga
    """
    return {"status": "ok"}