"""
api/main.py — API REST del dashboard de auditoría web.

Endpoints GET (Lectura):
  GET  /clients                      → lista de clientes
  GET  /websites?client_id=          → páginas web (filtro opcional por cliente)
  GET  /websites/{website_id}/status → estado actual + score anterior
  GET  /websites/{website_id}/runs   → historial de análisis
  GET  /runs/{run_id}                → detalle completo de un análisis
  GET  /runs/{run_id}/sections       → resultado por sección (10 checks)
  GET  /runs/{run_id}/issues         → incidencias de un análisis
  GET  /summary                      → resumen global para el dashboard

Endpoints CRUD (Escritura):
  POST   /clients                    → crear nuevo cliente
  PUT    /clients/{client_id}        → actualizar datos de cliente
  DELETE /clients/{client_id}        → eliminar cliente
  POST   /websites                   → crear nueva URL/website
  PUT    /websites/{website_id}      → actualizar URL (incluyendo active/inactive)
  DELETE /websites/{website_id}      → eliminar URL

Frecuencia de Scraping:
  - URLs ACTIVAS (active=true):   2 veces a la semana
  - URLs INACTIVAS (active=false): 1 vez cada 2 meses
"""
import os
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Web Auditor Dashboard API",
    version="1.0.0",
    docs_url="/docs",
)

# CORS (frontend servido por Node, también útil para dev local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ── Conexión a PostgreSQL ─────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.environ.get("DB_HOST", "localhost"),
    "port":     int(os.environ.get("DB_PORT", 5432)),
    "dbname":   os.environ.get("DB_NAME", "web_auditor"),
    "user":     os.environ.get("DB_USER", "auditor"),
    "password": os.environ.get("DB_PASSWORD", "auditor_secret"),
}


@contextmanager
def get_db():
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def q(conn, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Ejecuta una query y devuelve lista de dicts."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def q_one(conn, sql: str, params: tuple = ()) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


# ── Modelos Pydantic para CRUD ─────────────────────────────────────────────────
class ClientCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    notes: str | None = None


class WebsiteCreate(BaseModel):
    client_id: str  # UUID como string
    url: str
    label: str | None = None
    strategy: str = "auto"  # 'auto', 'selenium', 'beautifulsoup'
    active: bool = True


class WebsiteUpdate(BaseModel):
    url: str | None = None
    label: str | None = None
    strategy: str | None = None
    active: bool | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/clients")
def list_clients():
    """Lista todos los clientes con el número de páginas web asociadas."""
    sql = """
        SELECT  c.id, c.name, c.email, c.company, c.notes, c.created_at,
                COUNT(w.id)                             AS website_count,
                COUNT(w.id) FILTER (WHERE w.active)     AS active_website_count
        FROM    clients c
        LEFT JOIN websites w ON w.client_id = c.id
        GROUP BY c.id
        ORDER BY c.name
    """
    with get_db() as conn:
        return q(conn, sql)


@app.get("/websites")
def list_websites(client_id: str | None = Query(None)):
    """
    Lista páginas web con su estado actual.
    Filtro opcional por cliente.
    """
    sql = """
        SELECT
            w.id                    AS website_id,
            w.url,
            w.label,
            w.active,
            w.strategy,
            c.id                    AS client_id,
            c.name                  AS client_name,
            c.company               AS client_company,
            r.id                    AS last_run_id,
            r.started_at            AS last_run_at,
            r.audit_date,
            r.score,
            r.previous_score,
            r.audit_status,
            r.release_blocked,
            r.sections_passed,
            r.sections_total,
            r.response_time_ms,
            r.status_code,
            r.security_issue_count,
            r.seo_issue_count,
            r.content_issue_count,
            r.image_issue_count,
            r.structure_issue_count,
            r.link_issue_count,
            r.button_issue_count,
            r.technical_issue_count,
            r.status                AS run_status,
            r.error_message
        FROM websites w
        JOIN clients c ON c.id = w.client_id
        LEFT JOIN LATERAL (
            SELECT *
            FROM audit_runs
            WHERE website_id = w.id
            ORDER BY started_at DESC
            LIMIT 1
        ) r ON TRUE
        WHERE (%s::uuid IS NULL OR c.id = %s::uuid)
        ORDER BY c.name, w.url
    """
    with get_db() as conn:
        return q(conn, sql, (client_id, client_id))


@app.get("/websites/{website_id}/status")
def website_status(website_id: str):
    """Estado actual de una página web (último análisis)."""
    sql = """
        SELECT
            w.id                    AS website_id,
            w.url,
            w.label,
            w.active,
            w.strategy,
            c.id                    AS client_id,
            c.name                  AS client_name,
            c.company               AS client_company,
            r.id                    AS last_run_id,
            r.started_at            AS last_run_at,
            r.audit_date,
            r.score,
            r.previous_score,
            r.audit_status,
            r.release_blocked,
            r.sections_passed,
            r.sections_total,
            r.response_time_ms,
            r.status_code,
            r.security_issue_count,
            r.seo_issue_count,
            r.content_issue_count,
            r.image_issue_count,
            r.structure_issue_count,
            r.link_issue_count,
            r.button_issue_count,
            r.technical_issue_count,
            r.status                AS run_status,
            r.error_message
        FROM websites w
        JOIN clients c ON c.id = w.client_id
        LEFT JOIN LATERAL (
            SELECT *
            FROM audit_runs
            WHERE website_id = w.id
            ORDER BY started_at DESC
            LIMIT 1
        ) r ON TRUE
        WHERE w.id = %s::uuid
    """
    with get_db() as conn:
        row = q_one(conn, sql, (website_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Website no encontrado")
    return row


@app.get("/websites/{website_id}/runs")
def website_runs(
    website_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Historial de análisis de una página web, paginado."""
    sql = """
        SELECT  id, started_at, finished_at, status, strategy_used,
                audit_date, score, previous_score, audit_status, release_blocked,
                sections_passed, sections_total,
                response_time_ms, status_code, word_count,
                security_issue_count, seo_issue_count, content_issue_count,
                image_issue_count, structure_issue_count, link_issue_count,
                button_issue_count, technical_issue_count,
                error_message
        FROM    audit_runs
        WHERE   website_id = %s
        ORDER   BY started_at DESC
        LIMIT   %s OFFSET %s
    """
    count_sql = "SELECT COUNT(*) AS total FROM audit_runs WHERE website_id = %s"
    with get_db() as conn:
        rows = q(conn, sql, (website_id, limit, offset))
        total = q_one(conn, count_sql, (website_id,))["total"]
    return {"total": total, "limit": limit, "offset": offset, "runs": rows}


@app.get("/runs/{run_id}")
def run_detail(run_id: str):
    """Detalle completo de un análisis (incluye el JSON del informe)."""
    sql = """
        SELECT  r.*, w.url, w.label,
                c.name AS client_name, c.company AS client_company
        FROM    audit_runs r
        JOIN    websites w ON w.id = r.website_id
        JOIN    clients  c ON c.id = w.client_id
        WHERE   r.id = %s
    """
    with get_db() as conn:
        row = q_one(conn, sql, (run_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    return row


@app.get("/runs/{run_id}/sections")
def run_sections(run_id: str):
    """Detalle por secciones de la auditoría para una ejecución."""
    sql = """
        SELECT
            section_key,
            section_label,
            passed,
            status,
            issue_count,
            check_description,
            result_description,
            details_json
        FROM audit_run_sections
        WHERE run_id = %s
        ORDER BY section_key
    """
    with get_db() as conn:
        rows = q(conn, sql, (run_id,))
    return rows


@app.get("/runs/{run_id}/issues")
def run_issues(
    run_id: str,
    category: str | None = Query(None),
    severity: str | None = Query(None),
):
    """
    Incidencias de un análisis.
    Filtros opcionales: category (security|seo|…), severity (critical|high|…).
    """
    sql = """
        SELECT id, category, severity, message, line_no, line_hint
        FROM   audit_issues
        WHERE  run_id = %s
          AND  (%s::text IS NULL OR category = %s)
          AND  (%s::text IS NULL OR severity = %s)
        ORDER  BY
            CASE severity
                WHEN 'critical' THEN 1
                WHEN 'high'     THEN 2
                WHEN 'medium'   THEN 3
                WHEN 'low'      THEN 4
                ELSE 5
            END,
            category
    """
    with get_db() as conn:
        return q(conn, sql, (run_id, category, category, severity, severity))


@app.get("/summary")
def global_summary():
    """Resumen global para las tarjetas del dashboard principal."""
    sql = """
        SELECT
            COUNT(DISTINCT c.id)                                        AS total_clients,
            COUNT(DISTINCT w.id)                                        AS total_websites,
            COUNT(DISTINCT w.id) FILTER (WHERE w.active)                AS active_websites,
            COUNT(r.id) FILTER (WHERE r.audit_status = 'excelente')     AS excellent_count,
            COUNT(r.id) FILTER (WHERE r.audit_status = 'bueno')         AS good_count,
            COUNT(r.id) FILTER (WHERE r.audit_status = 'mejorable')     AS fair_count,
            COUNT(r.id) FILTER (WHERE r.audit_status = 'critico')       AS critical_count,
            COUNT(r.id) FILTER (WHERE r.release_blocked = TRUE)         AS blocked_count,
            ROUND(AVG(r.score))                                         AS avg_score
        FROM    clients c
        LEFT JOIN websites w ON w.client_id = c.id
        LEFT JOIN LATERAL (
            SELECT * FROM audit_runs
            WHERE website_id = w.id AND status = 'success'
            ORDER BY started_at DESC LIMIT 1
        ) r ON TRUE
    """
    with get_db() as conn:
        return q_one(conn, sql) or {}


# ════════════════════════════════════════════════════════════════════════════
#  CRUD ENDPOINTS — GESTIÓN DE CLIENTES
# ════════════════════════════════════════════════════════════════════════════

@app.post("/clients")
def create_client(payload: ClientCreate):
    """Crear un nuevo cliente."""
    sql = """
        INSERT INTO clients (name, email, phone, company, notes)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, name, email, phone, company, notes, created_at, updated_at
    """
    with get_db() as conn:
        try:
            row = q_one(conn, sql, (
                payload.name,
                payload.email,
                payload.phone,
                payload.company,
                payload.notes,
            ))
            conn.commit()
            return row
        except psycopg2.IntegrityError as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


@app.put("/clients/{client_id}")
def update_client(client_id: str, payload: ClientUpdate):
    """Actualizar datos de un cliente."""
    # Construir SET dinámicamente según los campos enviados
    updates = []
    params = []
    
    if payload.name is not None:
        updates.append("name = %s")
        params.append(payload.name)
    if payload.email is not None:
        updates.append("email = %s")
        params.append(payload.email)
    if payload.phone is not None:
        updates.append("phone = %s")
        params.append(payload.phone)
    if payload.company is not None:
        updates.append("company = %s")
        params.append(payload.company)
    if payload.notes is not None:
        updates.append("notes = %s")
        params.append(payload.notes)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = now()")
    params.append(client_id)
    
    sql = f"""
        UPDATE clients
        SET {', '.join(updates)}
        WHERE id = %s::uuid
        RETURNING id, name, email, phone, company, notes, created_at, updated_at
    """
    with get_db() as conn:
        try:
            row = q_one(conn, sql, tuple(params))
            conn.commit()
            if not row:
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            return row
        except psycopg2.IntegrityError as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


@app.delete("/clients/{client_id}")
def delete_client(client_id: str):
    """Eliminar un cliente (y sus websites asociadas)."""
    sql = "DELETE FROM clients WHERE id = %s::uuid RETURNING id"
    with get_db() as conn:
        try:
            row = q_one(conn, sql, (client_id,))
            conn.commit()
            if not row:
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            return {"message": "Cliente eliminado", "client_id": client_id}
        except psycopg2.IntegrityError as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


# ════════════════════════════════════════════════════════════════════════════
#  CRUD ENDPOINTS — GESTIÓN DE WEBSITES
# ════════════════════════════════════════════════════════════════════════════

@app.post("/websites")
def create_website(payload: WebsiteCreate):
    """Crear una nueva página web / URL a monitorizar."""
    sql = """
        INSERT INTO websites (client_id, url, label, strategy, active)
        VALUES (%s::uuid, %s, %s, %s, %s)
        RETURNING 
            id AS website_id, 
            client_id, 
            url, 
            label, 
            strategy, 
            active, 
            created_at, 
            updated_at
    """
    with get_db() as conn:
        try:
            row = q_one(conn, sql, (
                payload.client_id,
                payload.url,
                payload.label,
                payload.strategy,
                payload.active,
            ))
            conn.commit()
            if not row:
                raise HTTPException(status_code=400, detail="Error creando website")
            return row
        except psycopg2.IntegrityError as e:
            conn.rollback()
            if "unique" in str(e).lower():
                raise HTTPException(status_code=400, detail="La URL ya existe")
            raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


@app.put("/websites/{website_id}")
def update_website(website_id: str, payload: WebsiteUpdate):
    """Actualizar una página web (URL, etiqueta, estrategia, estado active/inactive)."""
    updates = []
    params = []
    
    if payload.url is not None:
        updates.append("url = %s")
        params.append(payload.url)
    if payload.label is not None:
        updates.append("label = %s")
        params.append(payload.label)
    if payload.strategy is not None:
        updates.append("strategy = %s")
        params.append(payload.strategy)
    if payload.active is not None:
        updates.append("active = %s")
        params.append(payload.active)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = now()")
    params.append(website_id)
    
    sql = f"""
        UPDATE websites
        SET {', '.join(updates)}
        WHERE id = %s::uuid
        RETURNING 
            id AS website_id, 
            client_id, 
            url, 
            label, 
            strategy, 
            active, 
            created_at, 
            updated_at
    """
    with get_db() as conn:
        try:
            row = q_one(conn, sql, tuple(params))
            conn.commit()
            if not row:
                raise HTTPException(status_code=404, detail="Website no encontrado")
            return row
        except psycopg2.IntegrityError as e:
            conn.rollback()
            if "unique" in str(e).lower():
                raise HTTPException(status_code=400, detail="La URL ya existe")
            raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


@app.delete("/websites/{website_id}")
def delete_website(website_id: str):
    """Eliminar una página web (y su historial de análisis asociado)."""
    sql = "DELETE FROM websites WHERE id = %s::uuid RETURNING id"
    with get_db() as conn:
        try:
            row = q_one(conn, sql, (website_id,))
            conn.commit()
            if not row:
                raise HTTPException(status_code=404, detail="Website no encontrado")
            return {"message": "Website eliminado", "website_id": website_id}
        except psycopg2.IntegrityError as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
