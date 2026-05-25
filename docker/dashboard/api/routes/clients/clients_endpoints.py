"""
CLIENTS_ENDPOINTS.PY - Endpoints para Gestión de Clientes

DESCRIPCIÓN:
Este módulo define los endpoints de la API REST para operaciones CRUD sobre
la entidad "Cliente". Un cliente representa una entidad (persona, empresa, etc.)
que posee uno o más sitios web que serán auditados por el sistema.

ENDPOINTS:
- GET    /clients          - Listar todos los clientes
- POST   /clients          - Crear un nuevo cliente
- PUT    /clients/{id}     - Actualizar un cliente existente
- DELETE /clients/{id}     - Eliminar un cliente (y sus websites asociados)
- GET    /clients/{id}/export - Generar y descargar reporte PDF del cliente

AUTORIZACIÓN:
- Actualmente no requiere autenticación (se puede añadir con FastAPI security)

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

# Importar esquemas de validación (Pydantic)
from schemas.clients import ClientCreate, ClientUpdate
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# Importar conexión a base de datos
from shared.database.connection import get_db

# Importar modelos ORM
from shared.database.models import AuditRun, Client, Website

# Importar repositorio de base de datos para operaciones CRUD
from shared.database.repositories import dashboard as repo
from shared.database.repositories.dashboard import runs as runs_repo

# Importar generador de reportes PDF
from shared.utils.pdf_generator import generate_client_report

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

# Crear router con prefijo "/clients" y etiqueta "clients" para Swagger
router = APIRouter(prefix="/clients", tags=["clients"])

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("")
def list_clients():
    """
    Lista todos los clientes registrados en el sistema.

    Returns:
        list: Array de objetos Client con sus datos completos.

    Example:
        GET /api/clients
        [
            {
                "id": "uuid",
                "name": "Empresa XYZ",
                "email": "contacto@empresa.com",
                ...
            },
            ...
        ]
    """
    return repo.list_clients()


@router.post("")
def create_client(payload: ClientCreate):
    """
    Crea un nuevo cliente en el sistema.

    Args:
        payload (ClientCreate): Datos del cliente a crear.
            - name (str, required): Nombre del cliente
            - email (str, optional): Email de contacto
            - phone (str, optional): Teléfono de contacto
            - company (str, optional): Nombre de la empresa
            - notes (str, optional): Notas adicionales
            - custom_cron (str, optional): Programación CRON personalizada

    Returns:
        Client: Objeto del cliente creado con su ID generado.

    Raises:
        HTTPException: 400 si hay error de integridad (ej: email duplicado)

    Example:
        POST /api/clients
        {
            "name": "Nuevo Cliente",
            "email": "cliente@email.com"
        }
    """
    try:
        return repo.create_client(
            payload.name,
            payload.email,
            payload.phone,
            payload.company,
            payload.notes,
            payload.custom_cron,
        )
    except IntegrityError as exc:
        # Manejar errores de base de datos (ej: unique constraint violations)
        raise HTTPException(status_code=400, detail=f"Error: {str(exc)}") from exc


@router.put("/{client_id}")
def update_client(client_id: str, payload: ClientUpdate):
    """
    Actualiza los datos de un cliente existente.

    Args:
        client_id (str): ID del cliente a actualizar
        payload (ClientUpdate): Datos a actualizar (todos opcionales)

    Returns:
        Client: Objeto del cliente actualizado.

    Raises:
        HTTPException:
            - 400 si no hay campos para actualizar
            - 404 si el cliente no existe

    Example:
        PUT /api/clients/123
        {
            "name": "Nombre Actualizado"
        }
    """
    # Filtrar solo los campos que fueron explícitamente establecidos
    # Esto permite actualizaciones parciales sin sobrescribir con null
    data = {k: v for k, v in payload.dict().items() if k in payload.model_fields_set}

    if not data:
        # Si no hay campos para actualizar, retornar error
        raise HTTPException(status_code=400, detail="No fields to update")

    # Ejecutar actualización en el repositorio
    row = repo.update_client(client_id, data)

    if not row:
        # Si el cliente no existe, retornar error 404
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    return row


@router.delete("/{client_id}")
def delete_client(client_id: str):
    """
    Elimina un cliente del sistema.

    NOTA: Esta operación también elimina todos los websites asociados al cliente
    y sus respectivos historiales de auditoría (cascade delete).

    Args:
        client_id (str): ID del cliente a eliminar

    Returns:
        dict: Mensaje de confirmación con el ID del cliente eliminado.

    Raises:
        HTTPException: 404 si el cliente no existe

    Example:
        DELETE /api/clients/123
        {
            "message": "Cliente eliminado",
            "client_id": "123"
        }
    """
    if not repo.delete_client(client_id):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"message": "Cliente eliminado", "client_id": client_id}


@router.get("/{client_id}/export")
def export_client_report(client_id: str):
    """
    Genera y descarga un reporte PDF consolidado de un cliente.

    El reporte incluye:
    - Información básica del cliente
    - Lista de todos sus websites
    - Última auditoría de cada website
    - Historial de auditorías (últimas 5 ejecuciones)

    Args:
        client_id (str): ID del cliente para el reporte

    Returns:
        StreamingResponse: Archivo PDF en streaming para descarga.

    Raises:
        HTTPException: 404 si el cliente no existe

    Example:
        GET /api/clients/123/export
        -> Descarga: client_123_report.pdf
    """
    # Genera un PDF consolidado por cliente y lo devuelve como descarga.
    with get_db() as db:
        # Obtener cliente de la base de datos
        client = db.get(Client, client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Obtener todos los websites del cliente, ordenados por URL
        stmt = select(Website).where(Website.client_id == client.id).order_by(Website.url)
        websites = db.execute(stmt).scalars().all()

        websites_data = []
        for w in websites:
            # Obtener la última ejecución (run) de cada website
            last_run = (
                db.execute(
                    select(AuditRun).where(AuditRun.website_id == w.id).order_by(AuditRun.started_at.desc()).limit(1)
                )
                .scalars()
                .first()
            )

            history = []
            if last_run:
                # Obtener historial de auditorías para el PDF
                history = runs_repo.runs_history_for_pdf(str(w.id), str(last_run.id))

            websites_data.append(
                {
                    "website": w,
                    "latest_run": last_run,
                    "history": history,
                }
            )

        # Generar PDF con los datos consolidados
        pdf = generate_client_report(client.name or "Cliente", websites_data)
        filename = f"client_{client_id}_report.pdf"

        # Retornar como streaming response para descarga
        return StreamingResponse(
            pdf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
