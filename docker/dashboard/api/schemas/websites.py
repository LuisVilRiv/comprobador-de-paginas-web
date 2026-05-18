from pydantic import BaseModel


class WebsiteCreate(BaseModel):
    client_id: str | None = None
    url: str
    label: str | None = None
    strategy: str = "auto"
    active: bool = True
    custom_cron: str | list[str] | None = None


class WebsiteUpdate(BaseModel):
    client_id: str | None = None
    url: str | None = None
    label: str | None = None
    strategy: str | None = None
    active: bool | None = None
    custom_cron: str | list[str] | None = None
