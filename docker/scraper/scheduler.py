"""
scheduler.py — Lógica de scheduling del daemon del scraper.
Extraído de entrypoint.py para separar la orquestación del cron
de la lógica de ejecución de auditorías individuales.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime

from croniter import croniter

logger = logging.getLogger(__name__)


class AuditScheduler:
    """
    Gestiona los ciclos de auditoría mediante expresiones cron.
    Separa el scheduling de la lógica de ejecución de auditorías.
    """

    def __init__(
        self,
        run_pending_fn,      # callable: () → int (nº éxitos)
        run_active_fn,       # callable: () → int
        run_inactive_fn,     # callable: () → int
        settings_fn,         # callable: () → dict con cron_active, cron_inactive
        poll_interval: int = 5,
    ):
        self._run_pending  = run_pending_fn
        self._run_active   = run_active_fn
        self._run_inactive = run_inactive_fn
        self._settings_fn  = settings_fn
        self._poll_interval = poll_interval

        self._last_cron_active   = None
        self._last_cron_inactive = None
        self._next_active        = None
        self._next_inactive      = None

    # ── API pública ───────────────────────────────────────────────────────────

    def run_forever(self) -> None:
        """Bucle principal del daemon. Bloquea hasta KeyboardInterrupt."""
        logger.info("Scheduler iniciado (poll cada %ds).", self._poll_interval)
        while True:
            try:
                self._tick()
            except Exception as exc:
                logger.error("Error inesperado en el scheduler: %s", exc)
            time.sleep(self._poll_interval)

    def next_run_times(self) -> dict[str, datetime | None]:
        """Devuelve los próximos timestamps de ejecución (para la API /settings)."""
        return {"next_active": self._next_active, "next_inactive": self._next_inactive}

    # ── Lógica interna ────────────────────────────────────────────────────────

    def _tick(self) -> None:
        # 1. Siempre procesar pendientes
        self._run_pending()

        # 2. Leer configuración (puede cambiar en caliente)
        try:
            settings = self._settings_fn()
            cron_active   = settings.get("cron_active",   "0 0 * * 0,3")
            cron_inactive = settings.get("cron_inactive", "0 0 1 2,4,6,8,10,12 *")
        except Exception as exc:
            logger.error("Error al leer settings de cron: %s", exc)
            return

        now_dt = datetime.now()

        # Recalcular next_active si el cron cambió
        if cron_active != self._last_cron_active:
            self._next_active      = croniter(cron_active, now_dt).get_next(datetime)
            self._last_cron_active = cron_active
            logger.info("Nuevo cron ACTIVOS: %s → próxima: %s", cron_active, self._next_active)

        # Recalcular next_inactive si el cron cambió
        if cron_inactive != self._last_cron_inactive:
            self._next_inactive      = croniter(cron_inactive, now_dt).get_next(datetime)
            self._last_cron_inactive = cron_inactive
            logger.info("Nuevo cron INACTIVOS: %s → próxima: %s", cron_inactive, self._next_inactive)

        # 3. Ejecutar ciclo de activos si toca
        if self._next_active and now_dt >= self._next_active:
            logger.info("⏰ [CRON] Ciclo ACTIVOS (%s)", cron_active)
            self._run_active()
            self._next_active = croniter(cron_active, now_dt).get_next(datetime)

        # 4. Ejecutar ciclo de inactivos si toca
        if self._next_inactive and now_dt >= self._next_inactive:
            logger.info("⏰ [CRON] Ciclo INACTIVOS (%s)", cron_inactive)
            self._run_inactive()
            self._next_inactive = croniter(cron_inactive, now_dt).get_next(datetime)
