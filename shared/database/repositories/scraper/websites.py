"""
scraper/websites.py — Consulta de sitios web para el proceso de auditoría.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update

from shared.database.connection import get_db
from shared.database.models import Client, Website


def get_active_websites() -> list[dict[str, Any]]:
    with get_db() as db:
        stmt = (
            select(
                Website.id,
                Website.url,
                Website.label,
                Website.strategy,
                Website.custom_cron.label("website_cron"),
                Client.name.label("client_name"),
                Client.custom_cron.label("client_cron"),
            )
            .outerjoin(Client, Website.client_id == Client.id)
            .where(Website.active == True, Website.pending_audit == False)
            .order_by(Client.name, Website.url)
        )
        return [
            {
                "website_id": str(r.id),
                "url": r.url,
                "label": r.label,
                "strategy": r.strategy,
                "client_name": r.client_name,
                "website_cron": r.website_cron,
                "client_cron": r.client_cron,
            }
            for r in db.execute(stmt).all()
        ]


def get_inactive_websites() -> list[dict[str, Any]]:
    with get_db() as db:
        stmt = (
            select(
                Website.id,
                Website.url,
                Website.label,
                Website.strategy,
                Website.custom_cron.label("website_cron"),
                Client.name.label("client_name"),
                Client.custom_cron.label("client_cron"),
            )
            .outerjoin(Client, Website.client_id == Client.id)
            .where(Website.active == False, Website.pending_audit == False)
            .order_by(Client.name, Website.url)
        )
        return [
            {
                "website_id": str(r.id),
                "url": r.url,
                "label": r.label,
                "strategy": r.strategy,
                "client_name": r.client_name,
                "website_cron": r.website_cron,
                "client_cron": r.client_cron,
            }
            for r in db.execute(stmt).all()
        ]


def get_pending_audit_websites() -> list[dict[str, Any]]:
    with get_db() as db:
        stmt = (
            select(Website.id, Website.url, Website.label, Website.strategy, Client.name.label("client_name"))
            .outerjoin(Client, Website.client_id == Client.id)
            .where(Website.pending_audit == True)
            .order_by(Website.updated_at)
        )
        return [
            {
                "website_id": str(r.id),
                "url": r.url,
                "label": r.label,
                "strategy": r.strategy,
                "client_name": r.client_name,
            }
            for r in db.execute(stmt).all()
        ]


def clear_pending_audit(website_id: str) -> None:
    with get_db() as db:
        db.execute(
            update(Website).where(Website.id == website_id).values(pending_audit=False, updated_at=datetime.now(UTC))
        )
        db.commit()
