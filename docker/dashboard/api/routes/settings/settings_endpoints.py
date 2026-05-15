from fastapi import APIRouter, HTTPException

from shared.database import repository as repo
from schemas.settings import SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings():
    return repo.get_settings()


@router.put("")
def update_settings(payload: SettingsUpdate):
    try:
        repo.update_settings(cron_active=payload.cron_active, cron_inactive=payload.cron_inactive)
        return {"message": "Configuración actualizada correctamente"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
