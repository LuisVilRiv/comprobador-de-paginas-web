from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError

from shared.database.repositories import dashboard as repo
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
    data = {k: v for k, v in payload.dict().items() if v is not None}
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
