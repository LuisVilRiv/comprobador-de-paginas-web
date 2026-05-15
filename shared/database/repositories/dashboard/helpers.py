"""
dashboard/helpers.py — Utilidades internas del repositorio dashboard.
"""
from datetime import datetime, timezone
from croniter import croniter

def row_to_dict(row) -> dict:
    """Convierte una fila de SQLAlchemy (Row o RowMapping) a un diccionario."""
    return dict(row._mapping) if hasattr(row, "_mapping") else {}

def cron_next_timestamp(cron_expr: str | None) -> int | None:
    """Calcula el próximo timestamp UTC para una expresión cron."""
    if not cron_expr:
        return None
    try:
        return int(croniter(cron_expr, datetime.now(timezone.utc)).get_next(datetime).timestamp())
    except Exception:
        return None
