from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    cron_active: str | None = None
    cron_inactive: str | None = None
