"""
scraper/settings.py — Gestión de configuración global para el scraper.
"""
from typing import Any
from sqlalchemy import select
from shared.database.models import GlobalSetting
from shared.database.connection import get_db

def get_settings() -> dict[str, Any]:
    with get_db() as db:
        return {row.key: row.value for row in db.execute(select(GlobalSetting)).scalars().all()}

def update_setting(key: str, value: Any) -> None:
    with get_db() as db:
        setting = db.get(GlobalSetting, key)
        if setting is None:
            setting = GlobalSetting(key=key, value=value)
        else:
            setting.value = value
        db.add(setting)
        db.commit()
