"""
dashboard/clients.py — Gestión de clientes para el dashboard.
"""

from sqlalchemy import func, select

from shared.database.connection import get_db
from shared.database.models import Client, Website

from .helpers import row_to_dict


def list_clients() -> list[dict]:
    with get_db() as db:
        stmt = (
            select(
                Client.id,
                Client.name,
                Client.email,
                Client.phone,
                Client.company,
                Client.notes,
                Client.custom_cron,
                Client.created_at,
                func.count(Website.id).label("website_count"),
                func.count(Website.id).filter(Website.active == True).label("active_website_count"),
            )
            .outerjoin(Website, Website.client_id == Client.id)
            .group_by(Client.id)
            .order_by(Client.name)
        )
        return [row_to_dict(r) for r in db.execute(stmt).all()]


def create_client(name, email, phone, company, notes, custom_cron=None) -> dict:
    with get_db() as db:
        client = Client(name=name, email=email, phone=phone, company=company, notes=notes, custom_cron=custom_cron)
        db.add(client)
        db.commit()
        db.refresh(client)
        return {"id": str(client.id), "name": client.name}


def update_client(client_id: str, data: dict) -> dict | None:
    with get_db() as db:
        client = db.get(Client, client_id)
        if not client:
            return None
        for k, v in data.items():
            if hasattr(client, k):
                setattr(client, k, v)
        db.commit()
        db.refresh(client)
        return {"id": str(client.id), "name": client.name}


def delete_client(client_id: str) -> bool:
    with get_db() as db:
        client = db.get(Client, client_id)
        if not client:
            return False
        db.delete(client)
        db.commit()
        return True
