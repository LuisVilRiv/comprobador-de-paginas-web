"""
db.py — Capa de acceso a PostgreSQL para el scraper.

Funciones principales:
  · get_connection()               → devuelve una conexión psycopg2
  · get_active_websites()          → lista de páginas activas desde la BD
  · get_pending_audit_websites()   → páginas marcadas para auditoría manual
  · clear_pending_audit(website_id)→ resetea el flag pending_audit tras procesar
  · save_audit_run()               → persiste el resultado completo de un análisis
"""
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST", "localhost"),
    "port":     int(os.environ.get("DB_PORT", 5432)),
    "dbname":   os.environ.get("DB_NAME", "web_auditor"),
    "user":     os.environ.get("DB_USER", "auditor"),
    "password": os.environ.get("DB_PASSWORD", "auditor_secret"),
}


@contextmanager
def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Lectura ───────────────────────────────────────────────────────────────────

def get_active_websites() -> list[dict[str, Any]]:
    """
    Devuelve la lista de websites activos.
    Excluye los que ya tienen pending_audit=TRUE (se procesan aparte con prioridad).
    """
    sql = """
        SELECT w.id AS website_id, w.url, w.label, w.strategy, c.name AS client_name
        FROM   websites w
        JOIN   clients  c ON c.id = w.client_id
        WHERE  w.active = TRUE
          AND  w.pending_audit = FALSE
        ORDER  BY c.name, w.url
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]


def get_pending_audit_websites() -> list[dict[str, Any]]:
    """
    Devuelve los websites marcados para auditoría manual (pending_audit=TRUE).
    Se incluyen tanto activos como inactivos — el operador los marcó explícitamente.
    Ordena por updated_at ASC para respetar el orden de solicitud (FIFO).
    """
    sql = """
        SELECT w.id AS website_id, w.url, w.label, w.strategy, c.name AS client_name
        FROM   websites w
        JOIN   clients  c ON c.id = w.client_id
        WHERE  w.pending_audit = TRUE
        ORDER  BY w.updated_at ASC
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]


def clear_pending_audit(website_id: str) -> None:
    """Resetea el flag pending_audit a FALSE una vez procesado el website."""
    sql = """
        UPDATE websites
        SET pending_audit = FALSE,
            updated_at    = %s
        WHERE id = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (datetime.now(timezone.utc), website_id))


# ── Escritura ─────────────────────────────────────────────────────────────────

def create_run(website_id: str, strategy_used: str) -> str:
    """
    Crea un registro de ejecución en estado 'running' y devuelve su UUID.
    """
    sql = """
        INSERT INTO audit_runs (
            website_id, strategy_used, status, started_at, audit_date, previous_score
        )
        VALUES (
            %s, %s, 'running', %s, CURRENT_DATE,
            (
                SELECT score FROM audit_runs
                WHERE website_id = %s AND status = 'success'
                ORDER BY started_at DESC LIMIT 1
            )
        )
        RETURNING id
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (website_id, strategy_used, datetime.now(timezone.utc), website_id))
            return str(cur.fetchone()[0])


def save_audit_run(
    run_id: str,
    website_id: str,
    status: str,
    strategy_used: str,
    report: dict | None,
    report_text: str,
    error_message: str | None,
    scrape_metadata: dict,
) -> None:
    """
    Actualiza el registro de ejecución con los resultados completos.
    También inserta todas las incidencias individuales en audit_issues.
    """
    metrics = (report or {}).get("metrics", {})
    sections = _build_audit_sections(report, scrape_metadata)
    sections_passed = sum(1 for s in sections if not s["details_json"].get("is_blocked", False))

    update_sql = """
        UPDATE audit_runs SET
            finished_at             = %s,
            status                  = %s,
            strategy_used           = %s,
            error_message           = %s,
            score                   = %s,
            audit_status            = %s,
            release_blocked         = %s,
            response_time_ms        = %s,
            status_code             = %s,
            word_count              = %s,
            h1_count                = %s,
            image_count             = %s,
            links_count             = %s,
            forms_count             = %s,
            security_issue_count    = %s,
            seo_issue_count         = %s,
            content_issue_count     = %s,
            image_issue_count       = %s,
            structure_issue_count   = %s,
            link_issue_count        = %s,
            button_issue_count      = %s,
            technical_issue_count   = %s,
            sections_passed         = %s,
            sections_total          = %s,
            report_json             = %s,
            report_text             = %s
        WHERE id = %s
    """

    sc = _safe_int(scrape_metadata.get("status_code"))
    rt = _safe_int(scrape_metadata.get("response_time_ms"))

    params = (
        datetime.now(timezone.utc),
        status,
        strategy_used,
        error_message,
        (report or {}).get("score"),
        (report or {}).get("status"),
        (report or {}).get("release_blocked", False),
        rt, sc,
        metrics.get("word_count"),
        metrics.get("h1_count"),
        metrics.get("image_count"),
        metrics.get("links_count"),
        metrics.get("forms_count"),
        metrics.get("security_issue_count", 0),
        len((report or {}).get("seo_issues", [])),
        metrics.get("content_issue_count", 0),
        metrics.get("image_issue_count", 0),
        len((report or {}).get("structure_issues", [])),
        metrics.get("link_issue_count", 0),
        metrics.get("button_issue_count", 0),
        metrics.get("technical_issue_count", 0),
        sections_passed,
        len(sections),
        json.dumps(report, ensure_ascii=False) if report else None,
        report_text,
        run_id,
    )

    issue_categories = {
        "security":  (report or {}).get("security_issues", []),
        "seo":       (report or {}).get("seo_issues", []),
        "content":   (report or {}).get("content_issues", []),
        "images":    (report or {}).get("image_issues", []),
        "structure": (report or {}).get("structure_issues", []),
        "links":     (report or {}).get("link_issues", []),
        "buttons":   (report or {}).get("button_issues", []),
        "technical": (report or {}).get("technical_issues", []),
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(update_sql, params)

            # Si el rowcount es 0, significa que el registro en audit_runs fue eliminado
            # (ej. borrado en cascada si el usuario eliminó la URL o el Cliente en el dashboard
            # mientras el scraper estaba analizando la página). Salimos para evitar errores de Foreign Key.
            if cur.rowcount == 0:
                return

            if report:
                issues_rows = []
                for category, issues_list in issue_categories.items():
                    for msg in issues_list:
                        severity = _classify_severity(msg)
                        issues_rows.append((run_id, category, severity, msg))

                if issues_rows:
                    psycopg2.extras.execute_values(
                        cur,
                        "INSERT INTO audit_issues (run_id, category, severity, message) VALUES %s",
                        issues_rows,
                    )

            if sections:
                section_rows = [
                    (
                        run_id,
                        s["section_key"], s["section_label"], s["passed"],
                        s["status"], s["issue_count"],
                        s["check_description"], s["result_description"],
                        json.dumps(s["details_json"], ensure_ascii=False),
                    )
                    for s in sections
                ]
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO audit_run_sections (
                        run_id, section_key, section_label, passed, status,
                        issue_count, check_description, result_description, details_json
                    ) VALUES %s
                    ON CONFLICT (run_id, section_key) DO UPDATE SET
                        section_label      = EXCLUDED.section_label,
                        passed             = EXCLUDED.passed,
                        status             = EXCLUDED.status,
                        issue_count        = EXCLUDED.issue_count,
                        check_description  = EXCLUDED.check_description,
                        result_description = EXCLUDED.result_description,
                        details_json       = EXCLUDED.details_json
                    """,
                    section_rows,
                )


# ── Helpers privados ──────────────────────────────────────────────────────────

def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _classify_severity(message: str) -> str:
    m = message.lower()
    if any(k in m for k in ("critico", "crítico", "dato sensible", "panel admin",
                              "sin autenticacion", "enlace roto confirmado", "imagen rota")):
        return "critical"
    if any(k in m for k in ("falta cabecera", "hsts", "csp", "mixed content",
                              "id duplicado", "falta doctype", "sin label")):
        return "high"
    if any(k in m for k in ("falta canonical", "favicon", "open graph", "lorem ipsum",
                              "legacy", "jerarquia")):
        return "medium"
    if "sin incidencias" in m or m.startswith("ok"):
        return "ok"
    return "low"


def _build_audit_sections(report: dict | None, scrape_metadata: dict) -> list[dict[str, Any]]:
    if not report:
        return [{
            "section_key": "audit_execution",
            "section_label": "Ejecucion de auditoria",
            "passed": False,
            "status": "failed",
            "issue_count": 1,
            "check_description": "Validar que la auditoria se ejecute y finalice correctamente.",
            "result_description": "La auditoria no genero informe utilizable.",
            "details_json": {"status_code": scrape_metadata.get("status_code")},
        }]

    section_specs = [
        ("security", "Seguridad", "security_issues", "Revisar HTTPS, cabeceras de seguridad y exposicion sensible."),
        ("seo", "SEO", "seo_issues", "Comprobar metadatos SEO, semantica y trazas para buscadores."),
        ("content", "Contenido", "content_issues", "Detectar contenido toxico, incoherente o de baja calidad."),
        ("images", "Imagenes", "image_issues", "Validar imagenes, atributos alt y optimizacion de recursos."),
        ("structure", "Estructura", "structure_issues", "Inspeccionar landmarks, jerarquia y accesibilidad estructural."),
        ("links", "Enlaces", "link_issues", "Verificar enlaces rotos, anclas y rutas no permitidas."),
        ("buttons", "Botones", "button_issues", "Probar interacciones de botones y formularios."),
        ("technical", "Tecnico", "technical_issues", "Comprobar consistencia tecnica y errores de runtime."),
        ("performance", "Rendimiento", None, "Medir tiempo de respuesta y eficiencia general de carga."),
        ("release_gate", "Gate de release", None, "Determinar si el sitio queda apto para despliegue."),
    ]

    sections: list[dict[str, Any]] = []
    metrics = report.get("metrics", {})
    response_time = _safe_int(scrape_metadata.get("response_time_ms"))
    release_blocked = bool(report.get("release_blocked", False))

    for section_key, label, report_key, check_description in section_specs:
        if section_key == "performance":
            issue_count = 1 if (response_time is not None and response_time > 1200) else 0
            passed = issue_count == 0
            status = "ok" if passed else "warning"
            result_description = (
                f"Tiempo de respuesta dentro de umbral ({response_time} ms)." if passed and response_time is not None
                else "Rendimiento degradado: el tiempo de respuesta supera 1200 ms."
            ) if response_time is not None else "Sin dato de tiempo de respuesta en esta ejecucion."
            details_json = {"response_time_ms": response_time}
        elif section_key == "release_gate":
            issue_count = len(report.get("release_blockers", []))
            passed = not release_blocked
            status = "ok" if passed else "failed"
            result_description = (
                "Gate superado: la web esta apta para release."
                if passed else "Gate bloqueado: hay blockers que impiden el despliegue."
            )
            details_json = {"release_blockers": report.get("release_blockers", [])}
        else:
            section_issues = report.get(report_key, [])
            issue_count = len([i for i in section_issues if "sin incidencias" not in i.lower()])
            
            # Detectar si esta sección está bloqueada
            is_section_blocked = any(kw in " ".join(section_issues).lower() for kw in ["bloqueada", "firewall", "403", "forbidden"])
            
            passed = not is_section_blocked
            status = "failed" if is_section_blocked else ("ok" if issue_count == 0 else "warning")
            result_description = (
                "Comprobacion correcta sin incidencias."
                if issue_count == 0 and not is_section_blocked else (
                    f"BLOQUEADO: La prueba fue impedida por la web o firewall." if is_section_blocked
                    else f"Se detectaron {issue_count} incidencia(s) en esta seccion."
                )
            )
            details_json = {
                "sample_issues": section_issues[:3],
                "metric_issue_count": metrics.get(f"{section_key.rstrip('s')}_issue_count"),
                "is_blocked": is_section_blocked
            }

        sections.append({
            "section_key": section_key,
            "section_label": label,
            "passed": passed,
            "status": status,
            "issue_count": issue_count,
            "check_description": check_description,
            "result_description": result_description,
            "details_json": details_json,
        })

    return sections