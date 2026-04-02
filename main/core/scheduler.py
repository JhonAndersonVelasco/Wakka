"""
Wakka — Update Scheduler
Periodic update checks using APScheduler with Qt signal integration.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

try:
    from apscheduler.schedulers.qt import QtScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

log = logging.getLogger(__name__)

FREQ_MAP = {
    "hourly": {"hour": "*"},
    "daily":  {"hour": 10, "minute": 0},
    "weekly": {"day_of_week": "sat", "hour": 10, "minute": 0},
    "monthly": {"day": 1, "hour": 10, "minute": 0},
}


class UpdateScheduler(QObject):
    """
    Wraps APScheduler (QtScheduler) to trigger update checks and notify.
    Falls back to QTimer if APScheduler is not installed.
    """

    check_requested = pyqtSignal()  # Emitted when it's time to check for updates

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._scheduler = None
        self._fallback_timer: Optional[QTimer] = None
        self._job_id = "wakka_update_check"

        if HAS_APSCHEDULER:
            try:
                self._scheduler = QtScheduler()
                self._scheduler.start()
            except Exception as e:
                log.warning(f"APScheduler init failed: {e}")
                self._scheduler = None

    def apply_schedule(self, enabled: bool, config: dict):
        """
        config keys: frequency, day, hour, minute
        frequency: "daily" | "weekly" | "monthly"
        """
        self._clear()

        if not enabled:
            return

        frequency = config.get("frequency", "weekly")
        hour = config.get("hour", 10)
        minute = config.get("minute", 0)
        day = config.get("day", "saturday")[:3].lower()  # "sat"
        interval_hours = config.get("interval_hours", 1)

        if self._scheduler:
            try:
                if frequency == "hourly":
                    trigger = IntervalTrigger(hours=interval_hours)
                else:
                    kwargs = {"hour": hour, "minute": minute}
                    if frequency == "weekly":
                        kwargs["day_of_week"] = day
                    elif frequency == "monthly":
                        kwargs["day"] = 1
                    trigger = CronTrigger(**kwargs)

                self._scheduler.add_job(
                    self._on_trigger,
                    trigger=trigger,
                    id=self._job_id,
                    replace_existing=True,
                    misfire_grace_time=3600,
                )
                log.info(f"Update schedule set: {frequency}")
                return
            except Exception as e:
                log.warning(f"APScheduler schedule failed: {e}")

        # Fallback: QTimer with interval
        self._fallback_timer = QTimer(self)
        interval_ms = self._freq_to_ms(frequency, interval_hours)
        self._fallback_timer.setInterval(interval_ms)
        self._fallback_timer.timeout.connect(self._on_trigger)
        self._fallback_timer.start()

    def trigger_now(self):
        """Manually trigger an update check immediately."""
        self._on_trigger()

    def _on_trigger(self):
        self.check_requested.emit()

    def _clear(self):
        if self._scheduler:
            try:
                self._scheduler.remove_job(self._job_id)
            except Exception:
                pass
        if self._fallback_timer:
            self._fallback_timer.stop()
            self._fallback_timer.deleteLater()
            self._fallback_timer = None

    @staticmethod
    def _freq_to_ms(frequency: str, interval_hours: int = 1) -> int:
        hours = {"hourly": interval_hours, "daily": 24, "weekly": 168, "monthly": 720}
        val = hours.get(frequency, 168) * 3_600_000
        # QTimer accepts max signed 32-bit int (~24.8 days)
        return min(val, 2147483647)

    def shutdown(self):
        self._clear()
        if self._scheduler and self._scheduler.running:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
