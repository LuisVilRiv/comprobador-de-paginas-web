import json
import logging
import time
from datetime import datetime

from croniter import croniter
from config.logging_config import setup_logger

logger = setup_logger(__name__)



class AuditScheduler:
    """
    Gestiona los ciclos de auditoría mediante expresiones cron.
    Soporta configuraciones globales y granulares (por Website/Client).
    """

    def __init__(
        self,
        run_pending_fn,      # callable: () → int
        run_active_fn,       # callable: () → int
        run_inactive_fn,     # callable: () → int
        run_single_fn,       # NEW callable: (entry) → bool
        get_active_fn,       # NEW callable: () → list
        get_inactive_fn,     # NEW callable: () → list
        settings_fn,         # callable: () → dict
        poll_interval: int = 5,
    ):
        self._run_pending  = run_pending_fn
        self._run_active   = run_active_fn
        self._run_inactive = run_inactive_fn
        self._run_single   = run_single_fn
        self._get_active   = get_active_fn
        self._get_inactive = get_inactive_fn
        self._settings_fn  = settings_fn
        self._poll_interval = poll_interval

        # website_id -> { "next_run": datetime, "crons": list, "active": bool }
        self._web_cache = {}
        
        self._next_active        = None
        self._next_inactive      = None
        self._last_global_active = None
        self._last_global_inactive = None

    def run_forever(self) -> None:
        logger.info("Scheduler iniciado (soporte para cron granular activo).")
        while True:
            try:
                self._tick()
            except Exception as exc:
                logger.exception("Error inesperado en el scheduler: %s", exc)
            time.sleep(self._poll_interval)

    def _normalize_crons(self, raw_crons):
        if raw_crons is None:
            return []
        if isinstance(raw_crons, str):
            return [c.strip() for c in raw_crons.split(",") if c.strip()]
        if isinstance(raw_crons, list):
            return [str(c).strip() for c in raw_crons if str(c).strip()]
        return []

    def _select_crons(self, entry, global_active, global_inactive, is_active):
        website_crons = self._normalize_crons(entry.get("website_cron"))
        client_crons = self._normalize_crons(entry.get("client_cron"))

        if website_crons:
            source = "website"
            selected = website_crons
        elif client_crons:
            source = "client"
            selected = client_crons
        else:
            source = "global"
            selected = [global_active if is_active else global_inactive]

        if not selected:
            # Si no quedan crons válidos, volver a global también como reserva.
            source = "global"
            selected = [global_active if is_active else global_inactive]

        return selected, source

    def _tick(self) -> None:
        # 1. Siempre procesar pendientes (prioridad máxima)
        self._run_pending()

        # 2. Obtener configuración y webs
        try:
            settings = self._settings_fn()
            global_active   = settings.get("cron_active",   "0 0 * * 0,3")
            global_inactive = settings.get("cron_inactive", "0 0 1 2,4,6,8,10,12 *")
            
            active_list   = self._get_active()
            inactive_list = self._get_inactive()
        except Exception as exc:
            logger.error("Error al refrescar datos en scheduler: %s", exc)
            return

        now = datetime.now()

        # 3. Evaluar cada web
        for entry in active_list + inactive_list:
            web_id = entry["website_id"]
            is_active = (entry in active_list)
            
            crons, source = self._select_crons(entry, global_active, global_inactive, is_active)
            cache = self._web_cache.get(web_id)
            if not cache or cache["crons"] != crons:
                next_t = self._calculate_next(crons, now)
                self._web_cache[web_id] = {"next_run": next_t, "crons": crons}
                logger.info("Web %s (%s) programada para: %s", entry["url"], source, next_t)
            
            if now >= self._web_cache[web_id]["next_run"]:
                logger.info("⏰ [CRON] Ejecutando auditoría programada: %s", entry["url"])
                self._run_single(entry)
                self._web_cache[web_id]["next_run"] = self._calculate_next(crons, now)

    def _calculate_next(self, crons: list[str], from_dt: datetime) -> datetime:
        next_times = []
        for c in crons:
            try:
                next_times.append(croniter(c, from_dt).get_next(datetime))
            except Exception as e:
                logger.error("Expresión cron inválida '%s': %s", c, e)
        
        if not next_times:
            # Fallback a 1 hora si falla todo
            return croniter("0 * * * *", from_dt).get_next(datetime)
        return min(next_times)
