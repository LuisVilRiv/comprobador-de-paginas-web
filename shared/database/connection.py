"""
connection.py — Configuración de conexión a base de datos.
Centraliza la configuración del engine SQLAlchemy y sesiones.
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# ── Configuración de conexión ──────────────────────────────────────────────
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 5432))
DB_NAME = os.environ.get("DB_NAME", "web_auditor")
DB_USER = os.environ.get("DB_USER", "auditor")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "auditor_secret")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Engine y sesión globales
engine: Engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)


@contextmanager
def get_db():
    """Context manager para sesiones de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()