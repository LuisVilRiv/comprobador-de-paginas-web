"""
dashboard/websites.py — Gestión de sitios web para el dashboard.
"""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import aliased
from shared.database.models import Client, Website, AuditRun
from shared.database.connection import get_db
from .helpers import row_to_dict
from sqlalchemy import func

def list_websites(client_id: str | None = None) -> list[dict]:
    with get_db() as db:
        # Subconsulta para obtener el ID de la última auditoría por website
        latest_ids = (
            select(
                AuditRun.website_id.label("website_id"),
                func.max(AuditRun.started_at).label("max_started")
            )
            .group_by(AuditRun.website_id)
            .subquery()
        )
        
        # Encontramos el ID real comparando con la fecha máxima (o usando IDs si fueran secuenciales)
        # Para ser 100% robustos en Postgres, podríamos usar DISTINCT ON, pero mantenemos compatibilidad SQL estándar
        latest_run_id_sub = (
            select(AuditRun.id)
            .join(latest_ids, (AuditRun.website_id == latest_ids.c.website_id) & (AuditRun.started_at == latest_ids.c.max_started))
            .subquery()
        )

        stmt = (
            select(
                Website.id.label("website_id"), Website.url, Website.label,
                Website.active, Website.strategy, Website.pending_audit,
                Website.custom_cron.label("website_cron"),
                Client.id.label("client_id"), Client.name.label("client_name"),
                Client.custom_cron.label("client_cron"),
                AuditRun.id.label("last_run_id"), AuditRun.audit_date,
                AuditRun.score, AuditRun.previous_score, AuditRun.audit_status,
                AuditRun.release_blocked, AuditRun.sections_passed,
                AuditRun.sections_total, AuditRun.status.label("run_status"),
                AuditRun.error_message,
            )
            .outerjoin(Client, Website.client_id == Client.id)
            .outerjoin(AuditRun, (AuditRun.website_id == Website.id) & (AuditRun.id.in_(latest_run_id_sub)))
            .order_by(Client.name, Website.url)
        )
        if client_id is not None:
            stmt = stmt.where(Client.id == client_id)
            
        # Obtener configuración global para fallback
        from shared.database.models import GlobalSetting
        settings = {
            row.key: row.value
            for row in db.execute(select(GlobalSetting)).scalars().all()
        }
        global_active = settings.get("cron_active", "0 0 * * 0,3")
        global_inactive = settings.get("cron_inactive", "0 0 1 2,4,6,8,10,12 *")

        res = []
        for r in db.execute(stmt).all():
            row_dict = row_to_dict(r)
            
            # Lógica de precedencia de crons (idéntica a scheduler.py)
            web_cron = row_dict.get("website_cron")
            cli_cron = row_dict.get("client_cron")
            is_active = row_dict.get("active")
            
            if web_cron:
                crons = web_cron
                source = "website"
            elif cli_cron:
                crons = cli_cron
                source = "client"
            else:
                crons = global_active if is_active else global_inactive
                source = "global"
                
            # Calcular siguiente ejecución
            from shared.database.repositories.dashboard.helpers import cron_next_timestamp
            cron_list = [c.strip() for c in (crons or "").split(",") if c.strip()]
            next_ts = None
            if cron_list:
                ts_list = []
                for c in cron_list:
                    ts = cron_next_timestamp(c)
                    if ts is not None:
                        ts_list.append(ts)
                if ts_list:
                    next_ts = min(ts_list)
                    
            row_dict["next_audit"] = next_ts
            row_dict["cron_source"] = source
            row_dict["resolved_cron"] = crons
            res.append(row_dict)
            
        return res

def website_status(website_id: str) -> dict | None:
    # Optimización: buscar solo la web específica en lugar de listar todas
    rows = list_websites() # Por ahora mantenemos compatibilidad con la lógica original
    match = [r for r in rows if str(r.get("website_id")) == str(website_id)]
    return match[0] if match else None

def create_website(client_id, url, label, strategy, active, custom_cron=None) -> dict:
    with get_db() as db:
        website = Website(
            client_id=client_id, url=url, label=label,
            strategy=strategy, active=active,
            custom_cron=custom_cron,
        )
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
            if hasattr(website, k):
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

def trigger_manual_audit(website_id: str) -> dict | None:
    with get_db() as db:
        website = db.get(Website, website_id)
        if not website:
            return None
        website.pending_audit = True
        website.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(website)
        return {
            "url":           website.url,
            "label":         website.label,
            "pending_audit": website.pending_audit,
        }
