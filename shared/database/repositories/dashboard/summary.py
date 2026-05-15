"""
dashboard/summary.py — Resumen global del estado de las auditorías.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import aliased
from shared.database.models import Client, Website, AuditRun, AuditIssue
from shared.database.connection import get_db

def global_summary() -> dict:
    with get_db() as db:
        total_clients   = db.execute(select(func.count(Client.id))).scalar() or 0
        total_websites  = db.execute(select(func.count(Website.id))).scalar() or 0
        active_websites = db.execute(
            select(func.count(Website.id)).where(Website.active == True)
        ).scalar() or 0
        total_runs          = db.execute(select(func.count(AuditRun.id))).scalar() or 0
        pending_audit_count = db.execute(
            select(func.count(Website.id)).where(Website.pending_audit == True)
        ).scalar() or 0

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
                latest_run.website_id,
                latest_run.audit_status,
                latest_run.release_blocked,
                AuditIssue.severity,
            )
            .join(
                latest_run_dates,
                (latest_run_dates.c.website_id == latest_run.website_id) &
                (latest_run_dates.c.last_started_at == latest_run.started_at),
            )
            .outerjoin(AuditIssue, AuditIssue.run_id == latest_run.id)
        )

        excellent_ids: set[str] = set()
        blocked_ids:   set[str] = set()
        critical_ids:  set[str] = set()
        for website_id, audit_status, release_blocked, severity in db.execute(stmt).all():
            wid = str(website_id)
            if audit_status == "excelente":
                excellent_ids.add(wid)
            if release_blocked:
                blocked_ids.add(wid)
            if severity == "critical":
                critical_ids.add(wid)

        return {
            "total_clients":       total_clients,
            "total_websites":      total_websites,
            "active_websites":     active_websites,
            "total_runs":          total_runs,
            "excellent_count":     len(excellent_ids),
            "critical_count":      len(critical_ids),
            "blocked_count":       len(blocked_ids),
            "pending_audit_count": pending_audit_count,
        }
