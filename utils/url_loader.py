import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from config import settings
from config.logging_config import setup_logger

logger = setup_logger(__name__)

# Estrategias válidas conocidas por el sistema
VALID_STRATEGIES = {"selenium", "beautifulsoup"}


class UrlLoader:
    """
    Responsable de leer, validar y exponer las URLs del fichero JSON.

    El fichero debe tener esta estructura mínima:
        {
          "urls": [
            { "url": "https://...", "strategy": "selenium", "active": true },
            ...
          ]
        }

    Campos obligatorios por entrada: `url`.
    Campos opcionales:               `strategy` (default "auto"), `active` (default True), `id`, `description`.

    Si strategy es "auto" o no se especifica, el sistema elige automaticamente
    la mejor estrategia y hace fallback a la otra si falla.
    """

    def __init__(self, path: Path | str = settings.URLS_JSON_PATH):
        self.path = Path(path)

    # ── API pública ───────────────────────────────────────────────────────────

    def load(self, only_active: bool = True) -> list[dict[str, Any]]:
        """
        Carga las entradas del JSON.

        Args:
            only_active: Si True (por defecto), filtra entradas con active=False.

        Returns:
            Lista de dicts validados y listos para usar.

        Raises:
            FileNotFoundError: Si el fichero no existe.
            ValueError:        Si el JSON tiene formato incorrecto.
        """
        raw = self._read_file()
        entries = self._parse(raw)
        validated = [e for e in map(self._validate_entry, entries) if e]

        if only_active:
            validated = [e for e in validated if e.get("active", True)]

        logger.info(
            "URL loader: %d entradas cargadas desde %s",
            len(validated), self.path,
        )
        return validated

    def load_by_strategy(self, strategy: str) -> list[dict[str, Any]]:
        """Devuelve solo las entradas que usan la estrategia indicada."""
        return [e for e in self.load() if e["strategy"] == strategy]

    # ── Métodos privados ──────────────────────────────────────────────────────

    def _read_file(self) -> dict:
        if not self.path.exists():
            raise FileNotFoundError(f"No se encontró el fichero de URLs: {self.path}")
        with open(self.path, encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON inválido en {self.path}: {exc}") from exc

    @staticmethod
    def _parse(raw: dict) -> list[dict]:
        if "urls" not in raw or not isinstance(raw["urls"], list):
            raise ValueError("El JSON debe tener una clave 'urls' con una lista.")
        return raw["urls"]

    @staticmethod
    def _validate_entry(entry: dict) -> dict | None:
        """Valida una entrada individual. Devuelve None si es inválida."""
        if not isinstance(entry.get("url"), str) or not entry["url"].startswith("http"):
            logger.warning("Entrada ignorada (URL inválida): %s", entry)
            return None
        host = UrlLoader._normalize_host(urlparse(entry["url"]).netloc)
        banned_hosts = {UrlLoader._normalize_host(h) for h in settings.AUDIT_BANNED_HOSTS}
        if host in banned_hosts:
            logger.warning("Entrada ignorada (host prohibido '%s'): %s", host, entry)
            return None
        strategy = entry.get("strategy", "auto")
        if strategy not in VALID_STRATEGIES and strategy != "auto":
            logger.warning(
                "Estrategia '%s' desconocida, usando auto: %s",
                strategy, entry,
            )
            entry["strategy"] = "auto"
        else:
            entry["strategy"] = strategy
        entry.setdefault("active", True)
        return entry

    @staticmethod
    def _normalize_host(host: str) -> str:
        host = host.lower().strip()
        return host[4:] if host.startswith("www.") else host
