"""
repository.py — Funciones de acceso a base de datos (DAO layer).
"""
import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import case, func, select, update
from sqlalchemy.orm import aliased

from .models import (
    AuditIssue,
    AuditRun,
    AuditRunSection,
    Client,
    GlobalSetting,
    Website,
    get_db,
)


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER — Funciones de db.py (lectura de URLs, persistencia de resultados)
# ══════════════════════════════════════════════════════════════════════════════

def get_active_websites() -> list[dict[str, Any]]:
    """Obtiene websites activos sin auditoría pendiente."""
    with get_db() as db:
        stmt = (
            select(Website.id, Website.url, Website.label, Website.strategy, Client.name.label("client_name"))
            .join(Client, Website.client_id == Client.id)
            .where(Website.active == True, Website.pending_audit == False)
            .order_by(Client.name, Website.url)
        )
        return [
            {
                "website_id": str(row.id),
                "url": row.url,
                "label": row.label,
                "strategy": row.strategy,
                "client_name": row.client_name,
            }
            for row in db.execute(stmt).all()
        ]


def get_pending_audit_websites() -> list[dict[str, Any]]:
    """Obtiene websites marcados para auditoría inmediata."""
    with get_db() as db:
        stmt = (
            select(Website.id, Website.url, Website.label, Website.strategy, Client.name.label("client_name"))
            .join(Client, Website.client_id == Client.id)
            .where(Website.pending_audit == True)
            .order_by(Website.updated_at)
        )
        return [
            {
                "website_id": str(row.id),
                "url": row.url,
                "label": row.label,
                "strategy": row.strategy,
                "client_name": row.client_name,
            }
            for row in db.execute(stmt).all()
        ]


def get_inactive_websites() -> list[dict[str, Any]]:
    """Obtiene websites inactivos."""
    with get_db() as db:
        stmt = (
            select(Website.id, Website.url, Website.label, Website.strategy, Client.name.label("client_name"))
            .join(Client, Website.client_id == Client.id)
            .where(Website.active == False, Website.pending_audit == False)
            .order_by(Client.name, Website.url)
        )
        return [
            {
                "website_id": str(row.id),
                "url": row.url,
                "label": row.label,
                "strategy": row.strategy,
                "client_name": row.client_name,
            }
            for row in db.execute(stmt).all()
        ]


def clear_pending_audit(website_id: str) -> None:
    """Marca un website como ya procesado (pending_audit=False)."""
    with get_db() as db:
        stmt = (
            update(Website)
            .where(Website.id == website_id)
            .values(pending_audit=False, updated_at=datetime.now(timezone.utc))
        )
        db.execute(stmt)
        db.commit()


def get_settings() -> dict[str, Any]:
    """Obtiene configuración global."""
    with get_db() as db:
        stmt = select(GlobalSetting)
        return {row.key: row.value for row in db.execute(stmt).scalars().all()}


def update_setting(key: str, value: Any) -> None:
    """Actualiza una setting global."""
    with get_db() as db:
        setting = db.get(GlobalSetting, key)
        if setting is None:
            setting = GlobalSetting(key=key, value=value)
        else:
            setting.value = value
        db.add(setting)
        db.commit()


def create_run(website_id: str, strategy_used: str) -> str:
    """Crea un nuevo registro de auditoría. Devuelve el run_id."""
    with get_db() as db:
        previous_score = db.execute(
            select(AuditRun.score)
            .where(AuditRun.website_id == website_id, AuditRun.status == "success")
            .order_by(AuditRun.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        run = AuditRun(
            website_id=website_id,
            strategy_used=strategy_used,
            status="running",
            started_at=datetime.now(timezone.utc),
            audit_date=date.today(),
            previous_score=previous_score,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return str(run.id)


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
    """Persiste el resultado de una auditoría en BD."""
    with get_db() as db:
        run = db.get(AuditRun, run_id)
        if run is None:
            return

        metrics = (report or {}).get("metrics", {})
        sections = _build_audit_sections(report, scrape_metadata)
        sections_passed = sum(1 for s in sections if not s["details_json"].get("is_blocked", False))

        run.finished_at = datetime.now(timezone.utc)
        run.status = status
        run.strategy_used = strategy_used
        run.error_message = error_message
        run.score = (report or {}).get("score")
        run.audit_status = (report or {}).get("status")
        run.release_blocked = (report or {}).get("release_blocked", False)
        run.response_time_ms = _safe_int(scrape_metadata.get("response_time_ms"))
        run.status_code = _safe_int(scrape_metadata.get("status_code"))
        run.word_count = metrics.get("word_count")
        run.h1_count = metrics.get("h1_count")
        run.image_count = metrics.get("image_count")
        run.links_count = metrics.get("links_count")
        run.forms_count = metrics.get("forms_count")
        run.security_issue_count = metrics.get("security_issue_count", 0)
        run.seo_issue_count = len((report or {}).get("seo_issues", []))
        run.content_issue_count = metrics.get("content_issue_count", 0)
        run.image_issue_count = metrics.get("image_issue_count", 0)
        run.structure_issue_count = len((report or {}).get("structure_issues", []))
        run.link_issue_count = metrics.get("link_issue_count", 0)
        run.button_issue_count = metrics.get("button_issue_count", 0)
        run.technical_issue_count = metrics.get("technical_issue_count", 0)
        run.sections_passed = sections_passed
        run.sections_total = len(sections)
        run.report_json = report
        run.report_text = report_text

        db.add(run)

        if report:
            for category, issues_list in {
                "security":  (report or {}).get("security_issues", []),
                "seo":       (report or {}).get("seo_issues", []),
                "content":   (report or {}).get("content_issues", []),
                "images":    (report or {}).get("image_issues", []),
                "structure": (report or {}).get("structure_issues", []),
                "links":     (report or {}).get("link_issues", []),
                "buttons":   (report or {}).get("button_issues", []),
                "technical": (report or {}).get("technical_issues", []),
            }.items():
                for msg in issues_list:
                    issue = AuditIssue(
                        run_id=run.id,
                        category=category,
                        severity=_classify_severity(msg),
                        message=msg,
                    )
                    db.add(issue)

        for section in sections:
            db.add(AuditRunSection(
                run_id=run.id,
                section_key=section["section_key"],
                section_label=section["section_label"],
                passed=section["passed"],
                status=section["status"],
                issue_count=section["issue_count"],
                check_description=section["check_description"],
                result_description=section["result_description"],
                details_json=section["details_json"],
            ))

        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD API — Funciones de acceso (lectura para dashboard)
# ══════════════════════════════════════════════════════════════════════════════

def _row_to_dict(row) -> dict:
    """Convierte una fila de SQLAlchemy a dict."""
    return dict(row._mapping) if hasattr(row, "_mapping") else {}


def list_clients() -> list[dict]:
    """Lista clientes con estadísticas de websites."""
    with get_db() as db:
        stmt = (
            select(
                Client.id,
                Client.name,
                Client.email,
                Client.company,
                Client.notes,
                Client.created_at,
                func.count(Website.id).label("website_count"),
                func.count(Website.id).filter(Website.active == True).label("active_website_count"),
            )
            .outerjoin(Website, Website.client_id == Client.id)
            .group_by(Client.id)
            .order_by(Client.name)
        )
        return [_row_to_dict(row) for row in db.execute(stmt).all()]


def list_websites(client_id: str | None = None) -> list[dict]:
    """Lista websites con últimos resultados de auditoría."""
    with get_db() as db:
        latest_run_dates = (
            select(
                AuditRun.website_id.label("website_id"),
                func.max(AuditRun.started_at).label("last_started_at"),
            )
            .group_by(AuditRun.website_id)
            .subquery()
        )

        latest_run = aliased(AuditRun)
        stmt = (
            select(
                Website.id.label("website_id"),
                Website.url,
                Website.label,
                Website.active,
                Website.strategy,
                Website.pending_audit,
                Client.id.label("client_id"),
                Client.name.label("client_name"),
                Client.company.label("client_company"),
                latest_run.id.label("last_run_id"),
                latest_run.started_at.label("last_run_at"),
                latest_run.audit_date,
                latest_run.score,
                latest_run.previous_score,
                latest_run.audit_status,
                latest_run.release_blocked,
                latest_run.sections_passed,
                latest_run.sections_total,
                latest_run.response_time_ms,
                latest_run.status_code,
                latest_run.security_issue_count,
                latest_run.seo_issue_count,
                latest_run.content_issue_count,
                latest_run.image_issue_count,
                latest_run.structure_issue_count,
                latest_run.link_issue_count,
                latest_run.button_issue_count,
                latest_run.technical_issue_count,
                latest_run.status.label("run_status"),
                latest_run.error_message,
            )
            .join(Client, Website.client_id == Client.id)
            .outerjoin(latest_run_dates, latest_run_dates.c.website_id == Website.id)
            .outerjoin(
                latest_run,
                (latest_run.website_id == Website.id)
                & (latest_run.started_at == latest_run_dates.c.last_started_at),
            )
            .order_by(Client.name, Website.url)
        )

        if client_id is not None:
            stmt = stmt.where(Client.id == client_id)

        return [_row_to_dict(row) for row in db.execute(stmt).all()]


def website_status(website_id: str) -> dict | None:
    """Obtiene el estado actual de un website."""
    with get_db() as db:
        latest_run_dates = (
            select(
                AuditRun.website_id.label("website_id"),
                func.max(AuditRun.started_at).label("last_started_at"),
            )
            .group_by(AuditRun.website_id)
            .subquery()
        )
        latest_run = aliased(AuditRun)
        stmt = (
            select(
                Website.id.label("website_id"),
                Website.url,
                Website.label,
                Website.active,
                Website.strategy,
                Website.pending_audit,
                Client.id.label("client_id"),
                Client.name.label("client_name"),
                Client.company.label("client_company"),
                latest_run.id.label("last_run_id"),
                latest_run.started_at.label("last_run_at"),
                latest_run.audit_date,
                latest_run.score,
                latest_run.previous_score,
                latest_run.audit_status,
                latest_run.release_blocked,
                latest_run.sections_passed,
                latest_run.sections_total,
                latest_run.response_time_ms,
                latest_run.status_code,
                latest_run.security_issue_count,
                latest_run.seo_issue_count,
                latest_run.content_issue_count,
                latest_run.image_issue_count,
                latest_run.structure_issue_count,
                latest_run.link_issue_count,
                latest_run.button_issue_count,
                latest_run.technical_issue_count,
                latest_run.status.label("run_status"),
                latest_run.error_message,
            )
            .join(Client, Website.client_id == Client.id)
            .outerjoin(latest_run_dates, latest_run_dates.c.website_id == Website.id)
            .outerjoin(
                latest_run,
                (latest_run.website_id == Website.id)
                & (latest_run.started_at == latest_run_dates.c.last_started_at),
            )
            .where(Website.id == website_id)
        )
        row = db.execute(stmt).one_or_none()
        return _row_to_dict(row) if row else None


def website_runs(website_id: str, limit: int, offset: int) -> dict:
    """Obtiene historial de auditorías de un website."""
    with get_db() as db:
        stmt = (
            select(
                AuditRun.id,
                AuditRun.started_at,
                AuditRun.finished_at,
                AuditRun.status,
                AuditRun.strategy_used,
                AuditRun.audit_date,
                AuditRun.score,
                AuditRun.previous_score,
                AuditRun.audit_status,
                AuditRun.release_blocked,
                AuditRun.sections_passed,
                AuditRun.sections_total,
                AuditRun.response_time_ms,
                AuditRun.status_code,
                AuditRun.word_count,
                AuditRun.security_issue_count,
                AuditRun.seo_issue_count,
                AuditRun.content_issue_count,
                AuditRun.image_issue_count,
                AuditRun.structure_issue_count,
                AuditRun.link_issue_count,
                AuditRun.button_issue_count,
                AuditRun.technical_issue_count,
                AuditRun.error_message,
            )
            .where(AuditRun.website_id == website_id)
            .order_by(AuditRun.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        count_stmt = select(func.count(AuditRun.id)).where(AuditRun.website_id == website_id)
        rows = [_row_to_dict(row) for row in db.execute(stmt).all()]
        total = db.execute(count_stmt).scalar() or 0
        return {"runs": rows, "total": total}


def run_detail(run_id: str) -> dict | None:
    """Obtiene detalles de una auditoría."""
    with get_db() as db:
        run = db.get(AuditRun, run_id)
        if not run:
            return None
        return {
            "id": str(run.id),
            "website_id": str(run.website_id),
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "status": run.status,
            "strategy_used": run.strategy_used,
            "score": run.score,
            "report_json": run.report_json or {},
            "report_text": run.report_text,
        }


def run_sections(run_id: str) -> list[dict]:
    """Obtiene secciones de una auditoría."""
    with get_db() as db:
        stmt = select(AuditRunSection).where(AuditRunSection.run_id == run_id).order_by(AuditRunSection.section_label)
        return [
            {
                "id": str(s.id),
                "section_key": s.section_key,
                "section_label": s.section_label,
                "passed": s.passed,
                "status": s.status,
                "issue_count": s.issue_count,
                "check_description": s.check_description,
                "result_description": s.result_description,
                "details": s.details_json or {},
            }
            for s in db.execute(stmt).scalars().all()
        ]


def run_issues(run_id: str, category: str | None = None, severity: str | None = None) -> list[dict]:
    """Obtiene incidencias de una auditoría."""
    with get_db() as db:
        stmt = select(AuditIssue).where(AuditIssue.run_id == run_id)
        if category:
            stmt = stmt.where(AuditIssue.category == category)
        if severity:
            stmt = stmt.where(AuditIssue.severity == severity)
        stmt = stmt.order_by(AuditIssue.category, AuditIssue.severity)
        return [
            {
                "id": str(issue.id),
                "category": issue.category,
                "severity": issue.severity,
                "message": issue.message,
                "line_no": issue.line_no,
                "line_hint": issue.line_hint,
            }
            for issue in db.execute(stmt).scalars().all()
        ]


def global_summary() -> dict:
    """Resumen global para el dashboard."""
    with get_db() as db:
        total_clients = db.execute(select(func.count(Client.id))).scalar() or 0
        total_websites = db.execute(select(func.count(Website.id))).scalar() or 0
        active_websites = db.execute(select(func.count(Website.id)).where(Website.active == True)).scalar() or 0
        total_runs = db.execute(select(func.count(AuditRun.id))).scalar() or 0
        
        return {
            "total_clients": total_clients,
            "total_websites": total_websites,
            "active_websites": active_websites,
            "total_runs": total_runs,
        }


def update_settings(cron_active: str | None = None, cron_inactive: str | None = None) -> None:
    """Actualiza la configuración de ciclos de auditoría."""
    if cron_active:
        update_setting("cron_active", cron_active)
    if cron_inactive:
        update_setting("cron_inactive", cron_inactive)


def trigger_manual_audit(website_id: str) -> dict | None:
    """Marca un website para auditoría manual inmediata."""
    with get_db() as db:
        website = db.get(Website, website_id)
        if not website:
            return None
        website.pending_audit = True
        website.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(website)
        return {
            "url": website.url,
            "label": website.label,
            "pending_audit": website.pending_audit,
        }


def create_client(name: str, email: str | None, phone: str | None, company: str | None, notes: str | None) -> dict:
    with get_db() as db:
        client = Client(name=name, email=email, phone=phone, company=company, notes=notes)
        db.add(client)
        db.commit()
        db.refresh(client)
        return {"id": str(client.id), "name": client.name}


def update_client(client_id: str, data: dict) -> dict | None:
    with get_db() as db:
        client = db.get(Client, client_id)
        if not client:
            return None
        for k, v in data.items():
            setattr(client, k, v)
        db.commit()
        db.refresh(client)
        return {"id": str(client.id), "name": client.name}


def delete_client(client_id: str) -> bool:
    with get_db() as db:
        client = db.get(Client, client_id)
        if not client:
            return False
        db.delete(client)
        db.commit()
        return True


def create_website(client_id: str, url: str, label: str | None, strategy: str, active: bool) -> dict:
    with get_db() as db:
        website = Website(client_id=client_id, url=url, label=label, strategy=strategy, active=active)
        db.add(website)
        db.commit()
        db.refresh(website)
        return {"id": str(website.id), "url": website.url}


def update_website(website_id: str, data: dict) -> dict | None:
    with get_db() as db:
        website = db.get(Website, website_id)
        if not website:
            return None
        for k, v in data.items():
            setattr(website, k, v)
        db.commit()
        db.refresh(website)
        return {"id": str(website.id), "url": website.url}


def delete_website(website_id: str) -> bool:
    with get_db() as db:
        website = db.get(Website, website_id)
        if not website:
            return False
        db.delete(website)
        db.commit()
        return True


# ══════════════════════════════════════════════════════════════════════════════
# Helpers privados
# ══════════════════════════════════════════════════════════════════════════════

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
        ("images", "Imágenes", "image_issues", "Comprobar que las imágenes están bien etiquetadas y optimizadas."),
        ("structure", "Estructura", "structure_issues", "Verificar semántica, encabezados y estructura HTML."),
        ("links", "Links", "link_issues", "Revisar enlaces rotos, redirecciones y atributos nofollow."),
        ("buttons", "Botones", "button_issues", "Analizar accesibilidad y consistencia interactiva."),
        ("technical", "Técnico", "technical_issues", "Comprobar consistencia tecnica y errores de runtime."),
    ]

    sections = []
    for key, label, issue_key, description in section_specs:
        issues = (report or {}).get(issue_key, [])
        passed = len(issues) == 0
        sections.append({
            "section_key": key,
            "section_label": label,
            "passed": passed,
            "status": "ok" if passed else "failed",
            "issue_count": len(issues),
            "check_description": description,
            "result_description": (
                "No se detectan problemas en esta seccion." if passed
                else f"Se han encontrado {len(issues)} incidencias."
            ),
            "details_json": {
                "issues": issues,
                "summary": f"{len(issues)} incidencia(s) detectada(s).",
            },
        })

    sections.insert(0, {
        "section_key": "audit_execution",
        "section_label": "Ejecucion de auditoria",
        "passed": True,
        "status": "passed",
        "issue_count": 0,
        "check_description": "Validar que la auditoria se ejecutó y finalizó correctamente.",
        "result_description": "Ejecucion correcta.",
        "details_json": {"status_code": scrape_metadata.get("status_code")},
    })

    return sections
