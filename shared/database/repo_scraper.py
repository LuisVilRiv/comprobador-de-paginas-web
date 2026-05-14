"""
repo_scraper.py — Acceso a BD exclusivo del proceso scraper.
Funciones: lectura de URLs, creación de runs, persistencia de resultados.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, update

from .models import AuditIssue, AuditRun, AuditRunSection, Client, GlobalSetting, Website, get_db


# ── Lectura de websites ───────────────────────────────────────────────────────

def get_active_websites() -> list[dict[str, Any]]:
    with get_db() as db:
        stmt = (
            select(Website.id, Website.url, Website.label, Website.strategy, Client.name.label("client_name"))
            .join(Client, Website.client_id == Client.id)
            .where(Website.active == True, Website.pending_audit == False)
            .order_by(Client.name, Website.url)
        )
        return [{"website_id": str(r.id), "url": r.url, "label": r.label,
                 "strategy": r.strategy, "client_name": r.client_name}
                for r in db.execute(stmt).all()]


def get_inactive_websites() -> list[dict[str, Any]]:
    with get_db() as db:
        stmt = (
            select(Website.id, Website.url, Website.label, Website.strategy, Client.name.label("client_name"))
            .join(Client, Website.client_id == Client.id)
            .where(Website.active == False, Website.pending_audit == False)
            .order_by(Client.name, Website.url)
        )
        return [{"website_id": str(r.id), "url": r.url, "label": r.label,
                 "strategy": r.strategy, "client_name": r.client_name}
                for r in db.execute(stmt).all()]


def get_pending_audit_websites() -> list[dict[str, Any]]:
    with get_db() as db:
        stmt = (
            select(Website.id, Website.url, Website.label, Website.strategy, Client.name.label("client_name"))
            .join(Client, Website.client_id == Client.id)
            .where(Website.pending_audit == True)
            .order_by(Website.updated_at)
        )
        return [{"website_id": str(r.id), "url": r.url, "label": r.label,
                 "strategy": r.strategy, "client_name": r.client_name}
                for r in db.execute(stmt).all()]


def clear_pending_audit(website_id: str) -> None:
    with get_db() as db:
        db.execute(
            update(Website)
            .where(Website.id == website_id)
            .values(pending_audit=False, updated_at=datetime.now(timezone.utc))
        )
        db.commit()


def get_settings() -> dict[str, Any]:
    with get_db() as db:
        return {row.key: row.value for row in db.execute(select(GlobalSetting)).scalars().all()}


def update_setting(key: str, value: Any) -> None:
    with get_db() as db:
        setting = db.get(GlobalSetting, key)
        if setting is None:
            setting = GlobalSetting(key=key, value=value)
        else:
            setting.value = value
        db.add(setting)
        db.commit()


# ── Persistencia de resultados ────────────────────────────────────────────────

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
        db.add(run); db.commit(); db.refresh(run)
        return str(run.id)


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
        sections = _build_audit_sections(report, scrape_metadata)
        run.finished_at       = datetime.now(timezone.utc)
        run.status            = status
        run.strategy_used     = strategy_used
        run.error_message     = error_message
        run.score             = (report or {}).get("score")
        run.audit_status      = (report or {}).get("status")
        run.release_blocked   = (report or {}).get("release_blocked", False)
        run.response_time_ms  = _safe_int(scrape_metadata.get("response_time_ms"))
        run.status_code       = _safe_int(scrape_metadata.get("status_code"))
        run.word_count        = metrics.get("word_count")
        run.h1_count          = metrics.get("h1_count")
        run.image_count       = metrics.get("image_count")
        run.links_count       = metrics.get("links_count")
        run.forms_count       = metrics.get("forms_count")
        run.security_issue_count  = metrics.get("security_issue_count", 0)
        run.seo_issue_count       = len((report or {}).get("seo_issues", []))
        run.content_issue_count   = metrics.get("content_issue_count", 0)
        run.image_issue_count     = metrics.get("image_issue_count", 0)
        run.structure_issue_count = len((report or {}).get("structure_issues", []))
        run.link_issue_count      = metrics.get("link_issue_count", 0)
        run.button_issue_count    = metrics.get("button_issue_count", 0)
        run.technical_issue_count = metrics.get("technical_issue_count", 0)
        run.sections_passed  = sum(1 for s in sections if not s["details_json"].get("is_blocked", False))
        run.sections_total   = len(sections)
        run.report_json      = report
        run.report_text      = report_text
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
                    db.add(AuditIssue(run_id=run.id, category=category,
                                      severity=_classify_severity(msg), message=msg))

        for section in sections:
            db.add(AuditRunSection(run_id=run.id, **section))
        db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_int(value: Any) -> int | None:
    try: return int(value)
    except (TypeError, ValueError): return None


def _classify_severity(message: str) -> str:
    m = message.lower()
    if any(k in m for k in ("critico", "dato sensible", "panel admin", "sin autenticacion", "enlace roto", "imagen rota")):
        return "critical"
    if any(k in m for k in ("falta cabecera", "hsts", "csp", "mixed content", "id duplicado")):
        return "high"
    if any(k in m for k in ("falta canonical", "favicon", "open graph", "lorem ipsum")):
        return "medium"
    if "sin incidencias" in m or m.startswith("ok"):
        return "ok"
    return "low"


def _build_audit_sections(report: dict | None, scrape_metadata: dict) -> list[dict[str, Any]]:
    if not report:
        return [{"section_key": "audit_execution", "section_label": "Ejecución de auditoría",
                 "passed": False, "status": "failed", "issue_count": 1,
                 "check_description": "Validar que la auditoría se ejecute correctamente.",
                 "result_description": "La auditoría no generó informe utilizable.",
                 "details_json": {"status_code": scrape_metadata.get("status_code")}}]

    section_specs = [
        ("security",  "Seguridad",   "security_issues",  "Revisar HTTPS, cabeceras y exposición sensible."),
        ("seo",       "SEO",         "seo_issues",        "Comprobar metadatos SEO y semántica."),
        ("content",   "Contenido",   "content_issues",    "Detectar contenido tóxico o de baja calidad."),
        ("images",    "Imágenes",    "image_issues",      "Comprobar imágenes etiquetadas y optimizadas."),
        ("structure", "Estructura",  "structure_issues",  "Verificar semántica y estructura HTML."),
        ("links",     "Links",       "link_issues",       "Revisar enlaces rotos y redirecciones."),
        ("buttons",   "Botones",     "button_issues",     "Analizar accesibilidad interactiva."),
        ("technical", "Técnico",     "technical_issues",  "Comprobar errores técnicos y de runtime."),
    ]
    sections = []
    for key, label, issue_key, description in section_specs:
        issues = (report or {}).get(issue_key, [])
        passed = len(issues) == 0
        sections.append({
            "section_key": key, "section_label": label, "passed": passed,
            "status": "ok" if passed else "failed", "issue_count": len(issues),
            "check_description": description,
            "result_description": ("No se detectan problemas." if passed
                                   else f"Se han encontrado {len(issues)} incidencias."),
            "details_json": {"issues": issues},
        })
    sections.insert(0, {
        "section_key": "audit_execution", "section_label": "Ejecución de auditoría",
        "passed": True, "status": "passed", "issue_count": 0,
        "check_description": "Validar que la auditoría se ejecutó correctamente.",
        "result_description": "Ejecución correcta.",
        "details_json": {"status_code": scrape_metadata.get("status_code")},
    })
    return sections
