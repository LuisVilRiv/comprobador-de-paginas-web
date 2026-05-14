"""
api/main.py — API REST del dashboard de auditoría web.

Endpoints GET (Lectura):
  GET  /clients                      → lista de clientes
  GET  /websites?client_id=          → páginas web (filtro opcional por cliente)
  GET  /websites/{website_id}/status → estado actual + score anterior
  GET  /websites/{website_id}/runs   → historial de análisis
  GET  /runs/{run_id}                → detalle completo de un análisis
  GET  /runs/{run_id}/sections       → resultado por sección (10 checks)
  GET  /runs/{run_id}/issues         → incidencias de un análisis
  GET  /summary                      → resumen global para el dashboard

Endpoints CRUD (Escritura):
  POST   /clients                    → crear nuevo cliente
  PUT    /clients/{client_id}        → actualizar datos de cliente
  DELETE /clients/{client_id}        → eliminar cliente
  POST   /websites                   → crear nueva URL/website
  PUT    /websites/{website_id}      → actualizar URL (incluyendo active/inactive)
  DELETE /websites/{website_id}      → eliminar URL

Auditoría bajo demanda:
  POST   /websites/{website_id}/audit → marcar para auditoría inmediata
                                        (el scraper la procesará en cuanto arranque)
"""

import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from shared.database import repository as repo

app = FastAPI(
    title="Web Auditor Dashboard API",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ── Modelos Pydantic ──────────────────────────────────────────────────────────
class ClientCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    notes: str | None = None


class WebsiteCreate(BaseModel):
    client_id: str
    url: str
    label: str | None = None
    strategy: str = "auto"
    active: bool = True


class WebsiteUpdate(BaseModel):
    url: str | None = None
    label: str | None = None
    strategy: str | None = None
    active: bool | None = None


class SettingsUpdate(BaseModel):
    cron_active: str | None = None
    cron_inactive: str | None = None


# ── Endpoints de lectura ──────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/clients")
def list_clients():
    return repo.list_clients()


@app.get("/websites")
def list_websites(client_id: str | None = Query(None)):
    return repo.list_websites(client_id=client_id)


@app.get("/websites/{website_id}/status")
def website_status(website_id: str):
    row = repo.website_status(website_id)
    if not row:
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return row


@app.get("/websites/{website_id}/runs")
def website_runs(
    website_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return repo.website_runs(website_id=website_id, limit=limit, offset=offset)


@app.get("/runs/{run_id}")
def run_detail(run_id: str):
    row = repo.run_detail(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    return row


@app.get("/runs/{run_id}/sections")
def run_sections(run_id: str):
    return repo.run_sections(run_id)


@app.get("/runs/{run_id}/issues")
def run_issues(
    run_id: str,
    category: str | None = Query(None),
    severity: str | None = Query(None),
):
    return repo.run_issues(run_id=run_id, category=category, severity=severity)


@app.get("/summary")
def global_summary():
    return repo.global_summary()


@app.get("/settings")
def get_settings():
    return repo.get_settings()


@app.put("/settings")
def update_settings(payload: SettingsUpdate):
    try:
        repo.update_settings(cron_active=payload.cron_active, cron_inactive=payload.cron_inactive)
        return {"message": "Configuración actualizada correctamente"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/websites/{website_id}/audit")
def trigger_manual_audit(website_id: str):
    result = repo.trigger_manual_audit(website_id)
    if not result:
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return {
        "message": "Auditoría solicitada. Se ejecutará de manera inmediata.",
        "website_id": website_id,
        "url": result["url"],
        "label": result.get("label"),
        "pending_audit": result["pending_audit"],
    }


# ════════════════════════════════════════════════════════════════════════════
#  CRUD — CLIENTES
# ═════════════════════════───────────────────────────────────────────────────

@app.post("/clients")
def create_client(payload: ClientCreate):
    try:
        return repo.create_client(
            payload.name,
            payload.email,
            payload.phone,
            payload.company,
            payload.notes,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=f"Error: {str(exc)}")


@app.put("/clients/{client_id}")
def update_client(client_id: str, payload: ClientUpdate):
    data = {k: v for k, v in payload.dict().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    row = repo.update_client(client_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return row


@app.delete("/clients/{client_id}")
def delete_client(client_id: str):
    if not repo.delete_client(client_id):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"message": "Cliente eliminado", "client_id": client_id}


# ════════════════════════════════════════════════════════════════════════════
#  CRUD — WEBSITES
# ═════════════════════════───────────────────────────────────────────────────

@app.post("/websites")
def create_website(payload: WebsiteCreate):
    try:
        return repo.create_website(
            payload.client_id,
            payload.url,
            payload.label,
            payload.strategy,
            payload.active,
        )
    except IntegrityError as exc:
        message = str(exc)
        if "unique" in message.lower():
            raise HTTPException(status_code=400, detail="La URL ya existe")
        raise HTTPException(status_code=400, detail=f"Error: {message}")


@app.put("/websites/{website_id}")
def update_website(website_id: str, payload: WebsiteUpdate):
    data = {k: v for k, v in payload.dict().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    row = repo.update_website(website_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return row


@app.delete("/websites/{website_id}")
def delete_website(website_id: str):
    if not repo.delete_website(website_id):
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return {"message": "Website eliminado", "website_id": website_id}
