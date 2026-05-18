"""
runs_endpoints.py — Endpoints de detalle de auditorías (runs).

Rutas expuestas:
    GET /runs/{run_id}           → Detalle completo de un run
    GET /runs/{run_id}/sections  → Secciones del informe
    GET /runs/{run_id}/issues    → Incidencias (filtrables por categoría y severidad)
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from shared.database.repositories import dashboard as repo
from shared.database.connection import get_db
from shared.database.models import AuditRun, Website
from shared.utils.pdf_generator import generate_audit_pdf

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}")
def get_run_detail(run_id: str):
    """Devuelve el detalle completo de un run de auditoría."""
    result = repo.run_detail(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run no encontrado")
    return result


@router.get("/{run_id}/sections")
def get_run_sections(run_id: str):
    """Devuelve las secciones del informe de un run (SEO, seguridad, etc.)."""
    return repo.run_sections(run_id)


@router.get("/{run_id}/issues")
def get_run_issues(
    run_id: str,
    category: str | None = Query(None, description="Filtrar por categoría (security, seo, content, images, structure, links, buttons, technical)"),
    severity: str | None = Query(None, description="Filtrar por severidad (critical, high, medium, low, ok)"),
):
    """
    Devuelve las incidencias detectadas en un run.
    Opcionalmente filtrables por categoría y/o severidad.
    """
    return repo.run_issues(run_id, category=category, severity=severity)


@router.get("/{run_id}/export")
def export_run_pdf(run_id: str):
    """Genera y descarga el informe de auditoría en formato PDF."""
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
