"""
dashboard/settings.py — Configuración global y del scheduler para el dashboard.
"""
from typing import Any
from sqlalchemy import select
from shared.database.models import GlobalSetting
from shared.database.connection import get_db
from shared.database.repositories.scraper import update_setting
from .helpers import cron_next_timestamp

def get_settings() -> dict[str, Any]:
    with get_db() as db:
        settings = {
            row.key: row.value
            for row in db.execute(select(GlobalSetting)).scalars().all()
        }
    settings["next_active"]   = cron_next_timestamp(settings.get("cron_active"))
    settings["next_inactive"] = cron_next_timestamp(settings.get("cron_inactive"))
    return settings

def update_settings(cron_active: str | None = None, cron_inactive: str | None = None) -> None:
    if cron_active:
        update_setting("cron_active",   cron_active)
    if cron_inactive:
        update_setting("cron_inactive", cron_inactive)
