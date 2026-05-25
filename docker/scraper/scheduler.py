import json
import time
from datetime import UTC, datetime, timedelta

from croniter import croniter

from config.logging_config import setup_logger

logger = setup_logger(__name__)

SCHEDULE_STATUS_FILE = "/app/config/schedule_status.json"


class AuditScheduler:
    """
    Gestiona los ciclos de auditoría mediante expresiones cron.
    Soporta configuraciones globales y granulares (por Website/Client).
    """

    def __init__(
        self,
        run_pending_fn,  # callable: () → int
        run_active_fn,  # callable: () → int
        run_inactive_fn,  # callable: () → int
        run_single_fn,  # callable: (entry) → bool
        get_active_fn,  # callable: () → list
        get_inactive_fn,  # callable: () → list
        settings_fn,  # callable: () → dict
        poll_interval: int = 5,
    ):
        self._run_pending = run_pending_fn
        self._run_active = run_active_fn
        self._run_inactive = run_inactive_fn
        self._run_single = run_single_fn
        self._get_active = get_active_fn
        self._get_inactive = get_inactive_fn
        self._settings_fn = settings_fn
        self._poll_interval = poll_interval

        # website_id → { "next_run": datetime, "crons": list }
        self._web_cache: dict[str, dict] = {}

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
            return website_crons, "website"
        if client_crons:
            return client_crons, "client"

        # Fallback to global
        selected = [global_active if is_active else global_inactive]
        return selected, "global"

    def _update_schedule_status_file(self, active_entries, inactive_entries, now):
        """Calcula y guarda el próximo evento para activos e inactivos en un JSON."""
        next_active_run = None
        next_inactive_run = None

        # Próxima ejecución de webs activas
        active_times: list[datetime] = [
            t for e in active_entries
            if (t := self._web_cache.get(e["website_id"], {}).get("next_run")) is not None
        ]
        if active_times:
            next_active_run = min(active_times)

        # Próxima ejecución de webs inactivas
        inactive_times: list[datetime] = [
            t for e in inactive_entries
            if (t := self._web_cache.get(e["website_id"], {}).get("next_run")) is not None
        ]
        if inactive_times:
            next_inactive_run = min(inactive_times)

        status = {
            "next_active_timestamp": next_active_run.timestamp() if next_active_run else None,
            "next_inactive_timestamp": next_inactive_run.timestamp() if next_inactive_run else None,
            "last_updated": now.isoformat(),
        }

        try:
            with open(SCHEDULE_STATUS_FILE, "w") as f:
                json.dump(status, f)
        except OSError as e:
            logger.error("Error al escribir el estado del scheduler en %s: %s", SCHEDULE_STATUS_FILE, e)

    def _tick(self) -> None:
        # 1. Procesar pendientes
        self._run_pending()

        # 2. Obtener configuración y webs
        try:
            settings = self._settings_fn()
            global_active_cron = settings.get("cron_active", "0 0 * * 0,3")
            global_inactive_cron = settings.get("cron_inactive", "0 0 1 2,4,6,8,10,12 *")
            active_list = self._get_active()
            inactive_list = self._get_inactive()
        except Exception as exc:
            logger.error("Error al refrescar datos en scheduler: %s", exc)
            return

        now = datetime.now(UTC)

        # 3. Evaluar cada web y actualizar su próxima ejecución en cache
        all_entries = active_list + inactive_list
        for entry in all_entries:
            web_id = entry["website_id"]
            is_active = entry in active_list

            crons, source = self._select_crons(entry, global_active_cron, global_inactive_cron, is_active)

            # Si la regla o el estado ha cambiado, recalcular
            cache = self._web_cache.get(web_id)
            if not cache or cache.get("crons") != crons:
                next_t = self._calculate_next(crons, now)
                self._web_cache[web_id] = {"next_run": next_t, "crons": crons}
                logger.info("Web %s (%s) programada para: %s", entry.get("url", web_id), source, next_t)

            # Si la hora de ejecución ha pasado, disparar y recalcular
            next_run_time = self._web_cache[web_id].get("next_run")
            if next_run_time and now >= next_run_time:
                logger.info("⏰ [CRON] Ejecutando auditoría programada para: %s", entry.get("url", web_id))
                self._run_single(entry)
                # Recalcular para la siguiente
                next_t = self._calculate_next(crons, datetime.now(UTC))
                self._web_cache[web_id]["next_run"] = next_t
                logger.info("Web %s reprogramada para: %s", entry.get("url", web_id), next_t)

        # 4. Guardar el estado general para la API
        self._update_schedule_status_file(active_list, inactive_list, now)

    def _calculate_next(self, crons: list[str], from_dt: datetime) -> datetime:
        next_times = []
        for c in crons:
            try:
                iter = croniter(c, from_dt)
                next_times.append(iter.get_next(datetime))
            except Exception as e:
                logger.error("Expresión cron inválida '%s': %s", c, e)

        if not next_times:
            logger.warning(
                "No se pudo determinar la próxima ejecución para las reglas: %s. Reintentando en 1 hora.", crons
            )
            return from_dt + timedelta(hours=1)

        return min(next_times)
