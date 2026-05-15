from fastapi import APIRouter

from shared.database import repository as repo

router = APIRouter(tags=["summary"])


@router.get("/summary")
def global_summary():
    return repo.global_summary()
