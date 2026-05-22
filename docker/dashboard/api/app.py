"""
APP.PY - Punto de Entrada Principal de la API FastAPI

DESCRIPCIÓN:
Este archivo es el entrypoint principal de la API REST del dashboard de auditoría
web. Configura la aplicación FastAPI, el middleware CORS, y registra todos los
routers de los diferentes módulos (clientes, websites, auditorías, etc.).

ARQUITECTURA:
- Framework: FastAPI (Python moderno, asíncrono, alto rendimiento)
- Patrón: Modular con routers separados por entidad
- CORS: Habilitado para permitir peticiones desde el frontend React
- Documentación: Swagger UI automático en /docs

MÓDULOS RELACIONADOS:
- routes/clients: Gestión de clientes (CRUD)
- routes/websites: Gestión de sitios web (CRUD + auditorías)
- routes/runs: Historial y detalles de auditorías
- routes/summary: Métricas y resumen del dashboard
- routes/settings: Configuración del scheduler
- routes/health: Health check del servicio
- shared/: Módulos compartidos (base de datos, estrategias de scraping, etc.)

CONFIGURACIÓN:
- Título: "Web Auditor Dashboard API"
- Versión: 1.0.0
- Documentación: Disponible en /docs (Swagger UI)
- CORS: Permitir todos los orígenes (para desarrollo)

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE RUTAS Y PATHS
# ═══════════════════════════════════════════════════════════════════════════════

# Asegurar que el directorio raíz del proyecto (que contiene `shared/`) esté en
# sys.path para que las importaciones de módulos compartidos funcionen correctamente.
# Esto es necesario porque la aplicación se ejecuta desde un contenedor Docker.

import sys
from pathlib import Path

# Obtener la ruta absoluta de este archivo
root = Path(__file__).resolve()

# Recorrer hasta 8 niveles hacia arriba buscando el directorio `shared/`
# Esto permite una estructura flexible de directorios
for _ in range(8):
    root = root.parent
    if (root / "shared").is_dir():
        # Añadir el directorio raíz al inicio de sys.path
        sys.path.insert(0, str(root))
        break

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES DE DEPENDENCIAS
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importar routers de cada módulo
# Cada router maneja un conjunto de endpoints relacionados
from routes import (
    clients_router,      # Endpoints para gestión de clientes
    health_router,       # Endpoint para health check
    runs_router,         # Endpoints para historial de auditorías
    settings_router,     # Endpoints para configuración del scheduler
    summary_router,      # Endpoints para resumen de métricas
    websites_router,     # Endpoints para gestión de websites
)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LA APLICACIÓN FASTAPI
# ═══════════════════════════════════════════════════════════════════════════════

# Crear instancia principal de FastAPI
app = FastAPI(
    title="Web Auditor Dashboard API",  # Título mostrado en Swagger UI
    version="1.0.0",                    # Versión de la API
    docs_url="/docs",                   # URL para documentación Swagger
)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE MIDDLEWARE CORS
# ═══════════════════════════════════════════════════════════════════════════════

# Configurar middleware CORS (Cross-Origin Resource Sharing)
# Esto permite que el frontend React (en diferente origen/puerto) pueda hacer
# peticiones a esta API sin problemas de seguridad del navegador.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                 # Permitir peticiones from any origin
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Métodos HTTP permitidos
    allow_headers=["*"],                 # Permitir todos los headers
)

# NOTA: En producción, `allow_origins` debería ser una lista específica de orígenes
# permitidos (ej: ["http://localhost:3000", "https://midominio.com"])

# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRO DE ROUTERS
# ═══════════════════════════════════════════════════════════════════════════════

# Registrar todos los routers en la aplicación principal
# Cada router añade sus endpoints específicos a la API

app.include_router(health_router)       # /health - Health check
app.include_router(clients_router)      # /api/clients - Gestión de clientes
app.include_router(websites_router)     # /api/websites - Gestión de websites
app.include_router(summary_router)      # /api/summary - Métricas del dashboard
app.include_router(runs_router)         # /api/runs - Historial de auditorías
app.include_router(settings_router)     # /api/settings - Configuración del scheduler

# ═══════════════════════════════════════════════════════════════════════════════
# PUNTOS DE ENTRADA (ENTRYPOINTS)
# ═══════════════════════════════════════════════════════════════════════════════

# Esta aplicación se ejecuta típicamente con Uvicorn:
# $ uvicorn app:app --host 0.0.0.0 --port 8000 --reload
#
# Para producción, se recomienda usar Gunicorn con workers Uvicorn:
# $ gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker
