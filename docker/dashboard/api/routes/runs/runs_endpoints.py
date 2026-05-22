"""
RUNS_ENDPOINTS.PY - Endpoints para Gestión de Ejecuciones de Auditorías

DESCRIPCIÓN:
Este módulo define los endpoints de la API REST para consultar detalles de
ejecuciones de auditoría (runs). Cada run representa una auditoría completada
o en progreso para un website específico.

ENDPOINTS:
- GET /runs/{run_id}           - Detalle completo de un run
- GET /runs/{run_id}/sections  - Secciones del informe (SEO, seguridad, etc.)
- GET /runs/{run_id}/issues    - Incidencias (filtrables por categoría y severidad)
- GET /runs/{run_id}/export    - Generar y descargar informe PDF

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

# Importar repositorio de base de datos
from shared.database.repositories import dashboard as repo

# Importar conexión a base de datos
from shared.database.connection import get_db

# Importar modelos ORM
from shared.database.models import AuditRun, Website

# Importar generador de reportes PDF
from shared.utils.pdf_generator import generate_audit_pdf

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

# Crear router con prefijo "/runs" y etiqueta "runs" para Swagger
router = APIRouter(prefix="/runs", tags=["runs"])

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{run_id}")
def get_run_detail(run_id: str):
    """
    Devuelve el detalle completo de un run de auditoría.
    
    Args:
        run_id (str): ID de la ejecución de auditoría.
    
    Returns:
        dict: Detalle completo del run con métricas, estado y timestamps.
    
    Raises:
        HTTPException: 404 si el run no existe.
    """
    result = repo.run_detail(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run no encontrado")
    return result


@router.get("/{run_id}/sections")
def get_run_sections(run_id: str):
    """
    Devuelve las secciones del informe de un run (SEO, seguridad, etc.).
    
    Args:
        run_id (str): ID de la ejecución de auditoría.
    
    Returns:
        list: Array de secciones con su estado individual (passed/failed/blocked).
    """
    return repo.run_sections(run_id)


@router.get("/{run_id}/issues")
def get_run_issues(
    run_id: str,
    category: str | None = Query(None, description="Filtrar por categoría (security, seo, content, images, structure, links, buttons, technical)"),
    severity: str | None = Query(None, description="Filtrar por severidad (critical, high, medium, low, ok)"),
):
    """
    Devuelve las incidencias detectadas en un run.
    
    Args:
        run_id (str): ID de la ejecución de auditoría.
        category (str, optional): Filtrar por categoría específica.
        severity (str, optional): Filtrar por nivel de severidad.
    
    Returns:
        list: Array de incidencias con detalles, severidad y sugerencias de solución.
    """
    return repo.run_issues(run_id, category=category, severity=severity)


@router.get("/{run_id}/export")
def export_run_pdf(run_id: str):
    """
    Genera y descarga el informe de auditoría en formato PDF.
    
    Args:
        run_id (str): ID de la ejecución de auditoría.
    
    Returns:
        StreamingResponse: Archivo PDF en streaming para descarga.
    
    Raises:
        HTTPException: 404 si el run no existe.
    """
    with get_db() as db:
        run = db.get(AuditRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run no encontrado")

        website = db.get(Website, run.website_id)

    # Historial de las últimas 4 auditorías previas con datos por sección
    history = repo.runs_history_for_pdf(
        website_id=str(run.website_id),
        exclude_run_id=run_id,
        limit=4,
    )

    with get_db() as db:
        run = db.get(AuditRun, run_id)   # re-fetch dentro del contexto para el PDF
        pdf_buffer = generate_audit_pdf(run, website, history=history)

    filename = f"auditoria_{run.started_at.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
