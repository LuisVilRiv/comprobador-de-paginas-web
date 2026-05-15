from fastapi import APIRouter, HTTPException, Query

from shared.database import repository as repo
from schemas.websites import WebsiteCreate, WebsiteUpdate

router = APIRouter(prefix="/websites", tags=["websites"])


@router.get("")
def list_websites(client_id: str | None = Query(None)):
    return repo.list_websites(client_id=client_id)


@router.get("/{website_id}/status")
def website_status(website_id: str):
    row = repo.website_status(website_id)
    if not row:
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return row


@router.get("/{website_id}/runs")
def website_runs(
    website_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return repo.website_runs(website_id=website_id, limit=limit, offset=offset)


@router.post("")
def create_website(payload: WebsiteCreate):
    try:
        return repo.create_website(
            payload.client_id,
            payload.url,
            payload.label,
            payload.strategy,
            payload.active,
        )
    except Exception as exc:
        message = str(exc)
        if "unique" in message.lower():
            raise HTTPException(status_code=400, detail="La URL ya existe")
        raise HTTPException(status_code=400, detail=f"Error: {message}")


@router.put("/{website_id}")
def update_website(website_id: str, payload: WebsiteUpdate):
    data = {k: v for k, v in payload.dict().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    row = repo.update_website(website_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return row


@router.delete("/{website_id}")
def delete_website(website_id: str):
    if not repo.delete_website(website_id):
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return {"message": "Website eliminado", "website_id": website_id}


@router.post("/{website_id}/audit")
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
