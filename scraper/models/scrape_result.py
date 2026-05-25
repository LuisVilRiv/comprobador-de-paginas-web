from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ScrapeResult:
    """
    Modelo de datos que representa el resultado de un scraping.
    Es la estructura que devuelven todas las estrategias,
    garantizando una salida uniforme independientemente del método usado.
    """

    url: str
    strategy: str
    content: str  # HTML crudo o texto extraído
    status: str = "success"  # "success" | "error"
    error: str | None = None  # Mensaje de error si status == "error"
    metadata: dict = field(default_factory=dict)  # Datos extra opcionales
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serializa el resultado a diccionario (para exportar a JSON/CSV)."""
        return {
            "url": self.url,
            "strategy": self.strategy,
            "status": self.status,
            "scraped_at": self.scraped_at,
            "error": self.error,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_error(cls, url: str, strategy: str, error: str) -> "ScrapeResult":
        """Factory para crear resultados de error de forma concisa."""
        return cls(
            url=url,
            strategy=strategy,
            content="",
            status="error",
            error=error,
        )
