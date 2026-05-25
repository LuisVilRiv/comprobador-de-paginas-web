"""
CONNECTION.PY - Configuración de Conexión a Base de Datos

DESCRIPCIÓN:
Este módulo centraliza la configuración de conexión a la base de datos PostgreSQL.
Proporciona el engine de SQLAlchemy y un context manager para gestión segura de
sesiones.

CONFIGURACIÓN:
Las credenciales de base de datos se obtienen de variables de entorno:
- DB_HOST: Servidor de base de datos (default: localhost)
- DB_PORT: Puerto de conexión (default: 5432)
- DB_NAME: Nombre de la base de datos (default: web_auditor)
- DB_USER: Usuario de base de datos (default: auditor)
- DB_PASSWORD: Contraseña de base de datos (default: auditor_secret)

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE CONEXIÓN
# ═══════════════════════════════════════════════════════════════════════════════

# Host de la base de datos
DB_HOST = os.environ.get("DB_HOST", "localhost")

# Puerto de conexión PostgreSQL
DB_PORT = int(os.environ.get("DB_PORT", 5432))

# Nombre de la base de datos
DB_NAME = os.environ.get("DB_NAME", "web_auditor")

# Usuario de base de datos
DB_USER = os.environ.get("DB_USER", "auditor")

# Contraseña de base de datos
DB_PASSWORD = os.environ.get("DB_PASSWORD", "auditor_secret")

# URL de conexión completa para SQLAlchemy
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE Y SESIÓN
# ═══════════════════════════════════════════════════════════════════════════════

# Engine de SQLAlchemy (pool de conexiones)
engine: Engine = create_engine(DATABASE_URL, future=True)

# Factory de sesiones
SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES
# ═══════════════════════════════════════════════════════════════════════════════


@contextmanager
def get_db():
    """
    Context manager para gestión segura de sesiones de base de datos.

    Yields:
        Session: Sesión de SQLAlchemy para operaciones CRUD.

    Example:
        >>> with get_db() as db:
        ...     users = db.query(User).all()

    Note:
        - La sesión se cierra automáticamente al salir del contexto
        - Garantiza que los recursos se liberen incluso en caso de excepción
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
