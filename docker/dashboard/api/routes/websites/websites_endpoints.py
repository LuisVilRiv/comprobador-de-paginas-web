"""
WEBSITES_ENDPOINTS.PY - Endpoints para Gestión de Sitios Web

DESCRIPCIÓN:
Este módulo define los endpoints de la API REST para operaciones CRUD sobre
la entidad "Website". Un website representa una URL específica que será
auditada periódicamente por el sistema.

ENDPOINTS:
- GET    /websites              - Listar todos los websites (opcionalmente por cliente)
- GET    /websites/{id}/status  - Obtener estado actual de un website
- GET    /websites/{id}/runs    - Obtener historial de auditorías de un website
- POST   /websites              - Crear un nuevo website
- PUT    /websites/{id}         - Actualizar un website existente
- DELETE /websites/{id}         - Eliminar un website
- POST   /websites/{id}/audit   - Iniciar auditoría manual inmediata

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException, Query

# Importar esquemas de validación (Pydantic)
from schemas.websites import WebsiteCreate, WebsiteUpdate

# Importar repositorio de base de datos para operaciones CRUD
from shared.database.repositories import dashboard as repo

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

# Crear router con prefijo "/websites" y etiqueta "websites" para Swagger
router = APIRouter(prefix="/websites", tags=["websites"])

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("")
def list_websites(client_id: str | None = Query(None)):
    """
    Lista todos los websites, opcionalmente filtrados por cliente.

    Args:
        client_id (str, optional): ID del cliente para filtrar. Si es None, devuelve todos.

    Returns:
        list: Array de objetos Website con sus datos completos.

    Example:
        GET /api/websites - Todos los websites
        GET /api/websites?client_id=123 - Websites del cliente 123
    """
    return repo.list_websites(client_id=client_id)


@router.get("/{website_id}/status")
def website_status(website_id: str):
    """
    Obtiene el estado actual de un website específico.

    Args:
        website_id (str): ID del website.

    Returns:
        dict: Estado actual del website (activo/inactivo, última auditoría, etc.)

    Raises:
        HTTPException: 404 si el website no existe.
    """
    row = repo.website_status(website_id)
    if not row:
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return row


@router.get("/{website_id}/runs")
def website_runs(
    website_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Obtiene el historial de auditorías de un website con paginación.

    Args:
        website_id (str): ID del website.
        limit (int, optional): Número máximo de resultados (1-100). Default: 20.
        offset (int, optional): Número de resultados a saltar. Default: 0.

    Returns:
        list: Array de objetos AuditRun (ejecuciones de auditoría).
    """
    return repo.website_runs(website_id=website_id, limit=limit, offset=offset)


@router.post("")
def create_website(payload: WebsiteCreate):
    """
    Crea un nuevo website para auditoría.

    Args:
        payload (WebsiteCreate): Datos del website a crear.
            - client_id (str, optional): ID del cliente propietario
            - url (str, required): URL completa del website
            - label (str, optional): Alias/etiqueta para identificar el website
            - strategy (str, required): Estrategia de scraping ("auto", "selenium", "bs4")
            - active (bool, required): Si está activo para auditorías automáticas
            - custom_cron (str, optional): Programación CRON personalizada

    Returns:
        Website: Objeto del website creado con su ID generado.

    Raises:
        HTTPException: 400 si la URL ya existe o hay error en los datos.
    """
    try:
        return repo.create_website(
            payload.client_id,
            payload.url,
            payload.label,
            payload.strategy,
            payload.active,
            payload.custom_cron,
        )
    except Exception as exc:
        message = str(exc)
        # Manejar error de URL duplicada (unique constraint)
        if "unique" in message.lower():
            raise HTTPException(status_code=400, detail="La URL ya existe") from exc
        raise HTTPException(status_code=400, detail=f"Error: {message}") from exc


@router.put("/{website_id}")
def update_website(website_id: str, payload: WebsiteUpdate):
    """
    Actualiza los datos de un website existente.

    Args:
        website_id (str): ID del website a actualizar.
        payload (WebsiteUpdate): Datos a actualizar (todos opcionales).

    Returns:
        Website: Objeto del website actualizado.

    Raises:
        HTTPException:
            - 400 si no hay campos para actualizar
            - 404 si el website no existe

    Note:
        Usa model_fields_set para distinguir entre "no enviado" y "enviado como null",
        permitiendo actualizaciones parciales sin sobrescribir con null valores existentes.
    """
    # Incluimos solo los campos que el cliente envió explícitamente.
    # Usamos model_fields_set para distinguir "no enviado" de "enviado como null"
    # (e.g. client_id=null es válido para desasociar un cliente).
    data = {k: v for k, v in payload.dict().items() if k in payload.model_fields_set}
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    row = repo.update_website(website_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return row


@router.delete("/{website_id}")
def delete_website(website_id: str):
    """
    Elimina un website del sistema de auditoría.

    Args:
        website_id (str): ID del website a eliminar.

    Returns:
        dict: Mensaje de confirmación con el ID del website eliminado.

    Raises:
        HTTPException: 404 si el website no existe.
    """
    if not repo.delete_website(website_id):
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return {"message": "Website eliminado", "website_id": website_id}


@router.post("/{website_id}/audit")
def trigger_manual_audit(website_id: str):
    """
    Inicia una auditoría manual e inmediata para un website específico.

    Args:
        website_id (str): ID del website a auditar.

    Returns:
        dict: Mensaje de confirmación con información del website.

    Raises:
        HTTPException: 404 si el website no existe.
    """
    result = repo.trigger_manual_audit(website_id)
    if not result:
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return {
        "message": "Auditoría solicitada. Se ejecutará de manera inmediata.",
        "website_id": website_id,
        "url": result["url"],
        "label": result.get("label"),
        "pending_audit": result["pending_audit"],
    }
