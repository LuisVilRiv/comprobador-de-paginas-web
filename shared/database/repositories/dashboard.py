"""
repo_dashboard.py — Acceso a BD exclusivo de la API del dashboard.
Funciones: listados, resúmenes, CRUD y auditoría bajo demanda.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from croniter import croniter
from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from .models import AuditIssue, AuditRun, AuditRunSection, Client, GlobalSetting, Website
from ..connection import get_db
from .repo_scraper import update_setting


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    return dict(row._mapping) if hasattr(row, "_mapping") else {}


def _cron_next_timestamp(cron_expr: str | None) -> int | None:
    if not cron_expr:
        return None
    try:
        return int(croniter(cron_expr, datetime.now(timezone.utc)).get_next(datetime).timestamp())
    except Exception:
        return None


# ── Lectura / listados ────────────────────────────────────────────────────────

def list_clients() -> list[dict]:
    with get_db() as db:
        stmt = (
            select(Client.id, Client.name, Client.email, Client.company, Client.notes, Client.created_at,
                   func.count(Website.id).label("website_count"),
                   func.count(Website.id).filter(Website.active == True).label("active_website_count"))
            .outerjoin(Website, Website.client_id == Client.id)
            .group_by(Client.id).order_by(Client.name)
        )
        return [_row_to_dict(r) for r in db.execute(stmt).all()]


def list_websites(client_id: str | None = None) -> list[dict]:
    with get_db() as db:
        latest_run_dates = (
            select(AuditRun.website_id.label("website_id"),
                   func.max(AuditRun.started_at).label("last_started_at"))
            .group_by(AuditRun.website_id).subquery()
        )
        latest_run = aliased(AuditRun)
        stmt = (
            select(Website.id.label("website_id"), Website.url, Website.label, Website.active,
                   Website.strategy, Website.pending_audit,
                   Client.id.label("client_id"), Client.name.label("client_name"),
                   latest_run.id.label("last_run_id"), latest_run.audit_date, latest_run.score,
                   latest_run.previous_score, latest_run.audit_status, latest_run.release_blocked,
                   latest_run.sections_passed, latest_run.sections_total,
                   latest_run.status.label("run_status"), latest_run.error_message)
            .join(Client, Website.client_id == Client.id)
            .outerjoin(latest_run_dates, latest_run_dates.c.website_id == Website.id)
            .outerjoin(latest_run,
                       (latest_run.website_id == Website.id) &
                       (latest_run.started_at == latest_run_dates.c.last_started_at))
            .order_by(Client.name, Website.url)
        )
        if client_id is not None:
            stmt = stmt.where(Client.id == client_id)
        return [_row_to_dict(r) for r in db.execute(stmt).all()]


def website_status(website_id: str) -> dict | None:
    rows = list_websites()
    match = [r for r in rows if str(r.get("website_id")) == str(website_id)]
    return match[0] if match else None


def website_runs(website_id: str, limit: int, offset: int) -> dict:
    with get_db() as db:
        stmt = (
            select(AuditRun.id, AuditRun.started_at, AuditRun.finished_at, AuditRun.status,
                   AuditRun.strategy_used, AuditRun.audit_date, AuditRun.score,
                   AuditRun.previous_score, AuditRun.audit_status, AuditRun.release_blocked,
                   AuditRun.sections_passed, AuditRun.sections_total, AuditRun.error_message)
            .where(AuditRun.website_id == website_id)
            .order_by(AuditRun.started_at.desc()).limit(limit).offset(offset)
        )
        count_stmt = select(func.count(AuditRun.id)).where(AuditRun.website_id == website_id)
        return {"runs": [_row_to_dict(r) for r in db.execute(stmt).all()],
                "total": db.execute(count_stmt).scalar() or 0}


def run_detail(run_id: str) -> dict | None:
    with get_db() as db:
        run = db.get(AuditRun, run_id)
        if not run:
            return None
        return {"id": str(run.id), "website_id": str(run.website_id),
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "status": run.status, "strategy_used": run.strategy_used,
                "score": run.score, "report_json": run.report_json or {},
                "report_text": run.report_text}


def run_sections(run_id: str) -> list[dict]:
    with get_db() as db:
        stmt = select(AuditRunSection).where(AuditRunSection.run_id == run_id).order_by(AuditRunSection.section_label)
        return [{"id": str(s.id), "section_key": s.section_key, "section_label": s.section_label,
                 "passed": s.passed, "status": s.status, "issue_count": s.issue_count,
                 "check_description": s.check_description, "result_description": s.result_description,
                 "details": s.details_json or {}}
                for s in db.execute(stmt).scalars().all()]


def run_issues(run_id: str, category: str | None = None, severity: str | None = None) -> list[dict]:
    with get_db() as db:
        stmt = select(AuditIssue).where(AuditIssue.run_id == run_id)
        if category: stmt = stmt.where(AuditIssue.category == category)
        if severity:  stmt = stmt.where(AuditIssue.severity == severity)
        stmt = stmt.order_by(AuditIssue.category, AuditIssue.severity)
        return [{"id": str(i.id), "category": i.category, "severity": i.severity,
                 "message": i.message, "line_no": i.line_no, "line_hint": i.line_hint}
                for i in db.execute(stmt).scalars().all()]


def global_summary() -> dict:
    with get_db() as db:
        total_clients = db.execute(select(func.count(Client.id))).scalar() or 0
        total_websites = db.execute(select(func.count(Website.id))).scalar() or 0
        active_websites = db.execute(select(func.count(Website.id)).where(Website.active == True)).scalar() or 0
        total_runs = db.execute(select(func.count(AuditRun.id))).scalar() or 0
        pending_audit_count = db.execute(select(func.count(Website.id)).where(Website.pending_audit == True)).scalar() or 0

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
            select(latest_run.website_id, latest_run.audit_status, latest_run.release_blocked, AuditIssue.severity)
            .join(
                latest_run_dates,
                (latest_run_dates.c.website_id == latest_run.website_id) &
                (latest_run_dates.c.last_started_at == latest_run.started_at),
            )
            .outerjoin(AuditIssue, AuditIssue.run_id == latest_run.id)
        )

        excellent_ids: set[str] = set()
        blocked_ids: set[str] = set()
        critical_ids: set[str] = set()
        for website_id, audit_status, release_blocked, severity in db.execute(stmt).all():
            if audit_status == "excelente":
                excellent_ids.add(str(website_id))
            if release_blocked:
                blocked_ids.add(str(website_id))
            if severity == "critical":
                critical_ids.add(str(website_id))

        return {
            "total_clients":      total_clients,
            "total_websites":     total_websites,
            "active_websites":    active_websites,
            "total_runs":         total_runs,
            "excellent_count":    len(excellent_ids),
            "critical_count":     len(critical_ids),
            "blocked_count":      len(blocked_ids),
            "pending_audit_count": pending_audit_count,
        }


def get_settings() -> dict[str, Any]:
    with get_db() as db:
        settings = {row.key: row.value for row in db.execute(select(GlobalSetting)).scalars().all()}

    settings["next_active"] = _cron_next_timestamp(settings.get("cron_active"))
    settings["next_inactive"] = _cron_next_timestamp(settings.get("cron_inactive"))
    return settings


# ── CRUD ─────────────────────────────────────────────────────────────────────

def create_client(name, email, phone, company, notes) -> dict:
    with get_db() as db:
        client = Client(name=name, email=email, phone=phone, company=company, notes=notes)
        db.add(client); db.commit(); db.refresh(client)
        return {"id": str(client.id), "name": client.name}


def update_client(client_id: str, data: dict) -> dict | None:
    with get_db() as db:
        client = db.get(Client, client_id)
        if not client: return None
        for k, v in data.items(): setattr(client, k, v)
        db.commit(); db.refresh(client)
        return {"id": str(client.id), "name": client.name}


def delete_client(client_id: str) -> bool:
    with get_db() as db:
        client = db.get(Client, client_id)
        if not client: return False
        db.delete(client); db.commit(); return True


def create_website(client_id, url, label, strategy, active) -> dict:
    with get_db() as db:
        website = Website(client_id=client_id, url=url, label=label, strategy=strategy, active=active)
        db.add(website); db.commit(); db.refresh(website)
        return {"id": str(website.id), "url": website.url}


def update_website(website_id: str, data: dict) -> dict | None:
    with get_db() as db:
        website = db.get(Website, website_id)
        if not website: return None
        for k, v in data.items(): setattr(website, k, v)
        db.commit(); db.refresh(website)
        return {"id": str(website.id), "url": website.url}


def delete_website(website_id: str) -> bool:
    with get_db() as db:
        website = db.get(Website, website_id)
        if not website: return False
        db.delete(website); db.commit(); return True


def trigger_manual_audit(website_id: str) -> dict | None:
    with get_db() as db:
        website = db.get(Website, website_id)
        if not website: return None
        website.pending_audit = True
        website.updated_at = datetime.now(timezone.utc)
        db.commit(); db.refresh(website)
        return {"url": website.url, "label": website.label, "pending_audit": website.pending_audit}


def update_settings(cron_active: str | None = None, cron_inactive: str | None = None) -> None:
    if cron_active:   update_setting("cron_active",   cron_active)
    if cron_inactive: update_setting("cron_inactive", cron_inactive)
