"""
dashboard/runs.py — Detalle de ejecuciones (runs), secciones e incidencias.
"""
from sqlalchemy import func, select
from shared.database.models import AuditRun, AuditRunSection, AuditIssue
from shared.database.connection import get_db
from .helpers import row_to_dict

def website_runs(website_id: str, limit: int, offset: int) -> dict:
    with get_db() as db:
        stmt = (
            select(
                AuditRun.id, AuditRun.started_at, AuditRun.finished_at, AuditRun.status,
                AuditRun.strategy_used, AuditRun.audit_date, AuditRun.score,
                AuditRun.previous_score, AuditRun.audit_status, AuditRun.release_blocked,
                AuditRun.sections_passed, AuditRun.sections_total, AuditRun.error_message,
            )
            .where(AuditRun.website_id == website_id)
            .order_by(AuditRun.started_at.desc())
            .limit(limit).offset(offset)
        )
        count_stmt = select(func.count(AuditRun.id)).where(AuditRun.website_id == website_id)
        return {
            "runs":  [row_to_dict(r) for r in db.execute(stmt).all()],
            "total": db.execute(count_stmt).scalar() or 0,
        }

def run_detail(run_id: str) -> dict | None:
    with get_db() as db:
        run = db.get(AuditRun, run_id)
        if not run:
            return None
        return {
            "id":          str(run.id),
            "website_id":  str(run.website_id),
            "started_at":  run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "status":        run.status,
            "strategy_used": run.strategy_used,
            "score":         run.score,
            "report_json":   run.report_json or {},
            "report_text":   run.report_text,
        }

def run_sections(run_id: str) -> list[dict]:
    with get_db() as db:
        stmt = (
            select(AuditRunSection)
            .where(AuditRunSection.run_id == run_id)
            .order_by(AuditRunSection.section_label)
        )
        return [
            {
                "id":                 str(s.id),
                "section_key":        s.section_key,
                "section_label":      s.section_label,
                "passed":             s.passed,
                "status":             s.status,
                "issue_count":        s.issue_count,
                "check_description":  s.check_description,
                "result_description": s.result_description,
                "details":            s.details_json or {},
            }
            for s in db.execute(stmt).scalars().all()
        ]

def run_issues(run_id: str, category: str | None = None, severity: str | None = None) -> list[dict]:
    with get_db() as db:
        stmt = select(AuditIssue).where(AuditIssue.run_id == run_id)
        if category:
            stmt = stmt.where(AuditIssue.category == category)
        if severity:
            stmt = stmt.where(AuditIssue.severity == severity)
        stmt = stmt.order_by(AuditIssue.category, AuditIssue.severity)
        return [
            {
                "id":        str(i.id),
                "category":  i.category,
                "severity":  i.severity,
                "message":   i.message,
                "line_no":   i.line_no,
                "line_hint": i.line_hint,
            }
            for i in db.execute(stmt).scalars().all()
        ]

def runs_history_for_pdf(website_id: str, exclude_run_id: str, limit: int = 4) -> list[dict]:
    """Devuelve los últimos `limit` runs del website (excluyendo el actual),
    con el issue_count desglosado por section_key. Usado para la gráfica del PDF."""
    with get_db() as db:
        stmt = (
            select(AuditRun)
            .where(
                AuditRun.website_id == website_id,
                AuditRun.id != exclude_run_id,
                AuditRun.status == "success",
            )
            .order_by(AuditRun.started_at.desc())
            .limit(limit)
        )
        runs = db.execute(stmt).scalars().all()

        result = []
        for r in reversed(runs):  # orden cronológico
            sections_stmt = (
                select(AuditRunSection.section_key, AuditRunSection.section_label, AuditRunSection.issue_count)
                .where(AuditRunSection.run_id == r.id)
            )
            sections = {
                row.section_key: {
                    "label": row.section_label or row.section_key,
                    "issue_count": row.issue_count or 0,
                }
                for row in db.execute(sections_stmt).all()
            }
            result.append({
                "run_id":     str(r.id),
                "date":       r.audit_date.isoformat() if r.audit_date else str(r.started_at.date()),
                "sections":   sections,
            })
        return result

