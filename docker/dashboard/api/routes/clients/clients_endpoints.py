from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from shared.database.repositories import dashboard as repo
from shared.database.repositories.dashboard import runs as runs_repo
from shared.database.connection import get_db
from shared.database.models import Client, Website, AuditRun
from shared.utils.pdf_generator import generate_client_report
from schemas.clients import ClientCreate, ClientUpdate

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("")
def list_clients():
    return repo.list_clients()


@router.post("")
def create_client(payload: ClientCreate):
    try:
        return repo.create_client(
            payload.name,
            payload.email,
            payload.phone,
            payload.company,
            payload.notes,
            payload.custom_cron,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=f"Error: {str(exc)}")


@router.put("/{client_id}")
def update_client(client_id: str, payload: ClientUpdate):
    data = {k: v for k, v in payload.dict().items() if k in payload.model_fields_set}
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    row = repo.update_client(client_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return row


@router.delete("/{client_id}")
def delete_client(client_id: str):
    if not repo.delete_client(client_id):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"message": "Cliente eliminado", "client_id": client_id}


@router.get("/{client_id}/export")
def export_client_report(client_id: str):
    """Genera un PDF consolidado por cliente y lo devuelve como descarga."""
    with get_db() as db:
        client = db.get(Client, client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Obtener websites del cliente
        stmt = select(Website).where(Website.client_id == client.id).order_by(Website.url)
        websites = db.execute(stmt).scalars().all()

        websites_data = []
        for w in websites:
            # Última ejecución (si existe)
            last_run = db.execute(
                select(AuditRun).where(AuditRun.website_id == w.id).order_by(AuditRun.started_at.desc()).limit(1)
            ).scalars().first()

            history = []
            if last_run:
                history = runs_repo.runs_history_for_pdf(str(w.id), str(last_run.id))

            websites_data.append({
                "website": w,
                "latest_run": last_run,
                "history": history,
            })

        pdf = generate_client_report(client.name or "Cliente", websites_data)
        filename = f"client_{client_id}_report.pdf"
        return StreamingResponse(pdf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
