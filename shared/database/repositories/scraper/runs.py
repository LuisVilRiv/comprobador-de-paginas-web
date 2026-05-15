"""
scraper/runs.py — Persistencia de resultados de auditoría y creación de runs.
"""
from datetime import date, datetime, timezone
from shared.database.models import AuditIssue, AuditRun, AuditRunSection
from shared.database.connection import get_db
from sqlalchemy import select, delete
from .mappers import build_audit_sections, classify_severity, safe_int

def create_run(website_id: str, strategy_used: str) -> str:
    with get_db() as db:
        previous_score = db.execute(
            select(AuditRun.score)
            .where(AuditRun.website_id == website_id, AuditRun.status == "success")
            .order_by(AuditRun.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        run = AuditRun(
            website_id=website_id, strategy_used=strategy_used, status="running",
            started_at=datetime.now(timezone.utc), audit_date=date.today(),
            previous_score=previous_score,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return str(run.id)

def update_run_progress(run_id: str, passed: int, total: int) -> None:
    try:
        with get_db() as db:
            run = db.get(AuditRun, run_id)
            if run:
                run.sections_passed = passed
                run.sections_total = total
                db.commit()
                print(f"DEBUG: Run {run_id} updated to {passed}/{total}")
            else:
                print(f"DEBUG: Run {run_id} not found for progress update")
    except Exception as e:
        print(f"ERROR updating progress for run {run_id}: {e}")

def save_audit_run(
    run_id: str, website_id: str, status: str, strategy_used: str,
    report: dict | None, report_text: str, error_message: str | None,
    scrape_metadata: dict,
) -> None:
    with get_db() as db:
        run = db.get(AuditRun, run_id)
        if run is None:
            return
        metrics  = (report or {}).get("metrics", {})
        sections = build_audit_sections(report, scrape_metadata)
        run.finished_at           = datetime.now(timezone.utc)
        run.status                = status
        run.strategy_used         = strategy_used
        run.error_message         = error_message
        run.score                 = (report or {}).get("score")
        run.audit_status          = (report or {}).get("status")
        run.release_blocked       = (report or {}).get("release_blocked", False)
        run.response_time_ms      = safe_int(scrape_metadata.get("response_time_ms"))
        run.status_code           = safe_int(scrape_metadata.get("status_code"))
        run.word_count            = metrics.get("word_count")
        run.h1_count              = metrics.get("h1_count")
        run.image_count           = metrics.get("image_count")
        run.links_count           = metrics.get("links_count")
        run.forms_count           = metrics.get("forms_count")
        run.security_issue_count  = metrics.get("security_issue_count", 0)
        run.seo_issue_count       = len((report or {}).get("seo_issues", []))
        run.content_issue_count   = metrics.get("content_issue_count", 0)
        run.image_issue_count     = metrics.get("image_issue_count", 0)
        run.structure_issue_count = len((report or {}).get("structure_issues", []))
        run.link_issue_count      = metrics.get("link_issue_count", 0)
        run.button_issue_count    = metrics.get("button_issue_count", 0)
        run.technical_issue_count = metrics.get("technical_issue_count", 0)
        run.sections_passed       = sum(1 for s in sections if s["status"] == "ok")
        run.sections_total        = len(sections)
        run.report_json           = report
        run.report_text           = report_text
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
                    db.add(AuditIssue(
                        run_id=run.id,
                        category=category,
                        severity=classify_severity(msg),
                        message=msg,
                    ))

        for section in sections:
            db.add(AuditRunSection(run_id=run.id, **section))
        
        db.commit()

        # ── Política de Retención (Top 5) ──
        try:
            cleanup_old_runs(db, website_id)
            db.commit()
        except Exception as exc:
            db.rollback()
            # No bloqueamos el resultado principal si falla el cleanup
            print(f"Error en cleanup de auditorías antiguas: {exc}")

def cleanup_old_runs(db_session, website_id: str, keep: int = 5):
    """Mantiene solo los últimos N runs para una URL."""
    runs_to_delete = db_session.execute(
        select(AuditRun.id)
        .where(AuditRun.website_id == website_id)
        .order_by(AuditRun.started_at.desc())
        .offset(keep)
    ).scalars().all()
    
    if runs_to_delete:
        db_session.execute(delete(AuditRun).where(AuditRun.id.in_(runs_to_delete)))
