"""
dashboard/helpers.py — Utilidades internas del repositorio dashboard.
"""
from datetime import datetime, timezone
from croniter import croniter

def row_to_dict(row) -> dict:
    """Convierte una fila de SQLAlchemy (Row o RowMapping) a un diccionario."""
    return dict(row._mapping) if hasattr(row, "_mapping") else {}

def cron_next_timestamp(cron_expr: str | None) -> int | None:
    """Calcula el próximo timestamp para una expresión cron en UTC."""
    if not cron_expr:
        return None
    try:
        now = datetime.now(timezone.utc)
        return int(croniter(cron_expr, now).get_next(datetime).timestamp())
    except Exception:
        return None
