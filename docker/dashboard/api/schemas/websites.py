from pydantic import BaseModel


class WebsiteCreate(BaseModel):
    client_id: str
    url: str
    label: str | None = None
    strategy: str = "auto"
    active: bool = True


class WebsiteUpdate(BaseModel):
    url: str | None = None
    label: str | None = None
    strategy: str | None = None
    active: bool | None = None
