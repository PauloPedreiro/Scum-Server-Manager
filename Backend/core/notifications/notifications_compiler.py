import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ReservedWindow:
    restart_time: str
    start: datetime
    end: datetime


class NotificationsCompiler:
    def __init__(
        self,
        logger,
        scum_notifications_path: Path,
        scheduler_times: List[str],
        templates_path: Path,
        reserved_before_minutes: int = 15,
        reserved_after_minutes: int = 5,
    ):
        self.logger = logger
        self.scum_notifications_path = scum_notifications_path
        self.scheduler_times = list(scheduler_times or [])
        self.templates_path = templates_path
        self.reserved_before_minutes = reserved_before_minutes
        self.reserved_after_minutes = reserved_after_minutes

    def _load_restart_template(self) -> Dict[str, Any]:
        template_path = self.templates_path / "restart.json"
        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _parse_hhmm(self, hhmm: str) -> Tuple[int, int]:
        parts = (hhmm or "").split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid HH:MM: {hhmm}")
        return int(parts[0]), int(parts[1])

    def get_restart_datetimes_next_24h(self, now: Optional[datetime] = None) -> List[datetime]:
        now = now or datetime.now()
        times = self.scheduler_times
        if not times:
            return []

        result: List[datetime] = []
        today = now.date()
        for t in times:
            h, m = self._parse_hhmm(t)
            dt = datetime(now.year, now.month, now.day, h, m)
            if dt >= now - timedelta(minutes=1):
                result.append(dt)

        tomorrow = now + timedelta(days=1)
        for t in times:
            h, m = self._parse_hhmm(t)
            dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, h, m)
            if dt <= now + timedelta(hours=24):
                result.append(dt)

        result = sorted({dt for dt in result})
        return result

    def get_restart_datetimes_for_date(self, day: datetime) -> List[datetime]:
        times = self.scheduler_times
        if not times:
            return []
        result: List[datetime] = []
        for t in times:
            h, m = self._parse_hhmm(t)
            result.append(datetime(day.year, day.month, day.day, h, m))
        return sorted(result)

    def build_reserved_windows(self, now: Optional[datetime] = None) -> List[ReservedWindow]:
        now = now or datetime.now()
        restarts = self.get_restart_datetimes_next_24h(now)
        windows: List[ReservedWindow] = []
        for r in restarts:
            windows.append(
                ReservedWindow(
                    restart_time=r.strftime("%H:%M"),
                    start=r - timedelta(minutes=self.reserved_before_minutes),
                    end=r + timedelta(minutes=self.reserved_after_minutes),
                )
            )
        return windows

    def is_reserved_time(self, when: datetime, windows: List[ReservedWindow]) -> Optional[ReservedWindow]:
        for w in windows:
            if w.start <= when <= w.end:
                return w
        return None

    def build_restart_notifications(self, restart_dt: datetime) -> List[Dict[str, Any]]:
        template = self._load_restart_template()
        notifications: List[Dict[str, Any]] = []
        for notification_config in template.get("notifications", []):
            time_type = notification_config.get("time")
            duration = int(notification_config.get("duration", 10))
            color = notification_config.get("color", "255-180-50")
            message = notification_config.get("message", "")

            minutes_before = None
            if isinstance(time_type, str) and time_type.endswith("_min_before"):
                try:
                    minutes_before = int(time_type.split("_")[0])
                except Exception:
                    minutes_before = None

            if minutes_before is None:
                continue

            notification_time = restart_dt - timedelta(minutes=minutes_before)
            notifications.append(
                {
                    "day": "Everyday",
                    "time": [notification_time.strftime("%H:%M")],
                    "duration": duration,
                    "color": color,
                    "message": message,
                }
            )
        return notifications

    def write_notifications_atomic(self, notifications: List[Dict[str, Any]]):
        self.scum_notifications_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = str(self.scum_notifications_path) + ".tmp"
        payload = {"Notifications": notifications}

        # 1) Escrever arquivo temporario (pode falhar em Windows por lock/permissao)
        last_error: Optional[Exception] = None
        for attempt in range(5):
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                last_error = None
                break
            except OSError as e:
                last_error = e
                winerror = getattr(e, "winerror", None)
                errno = getattr(e, "errno", None)
                # 5=Access denied, 32=File in use, 13=Permission denied
                if winerror not in (5, 32) and errno != 13:
                    break
                time.sleep(0.15 * (2**attempt))

        if last_error is not None:
            try:
                self.logger.warn(
                    "Falha ao escrever Notifications.json.tmp (arquivo bloqueado/permissao)",
                    {"tmp_path": str(tmp_path), "error": str(last_error)},
                )
            except Exception:
                pass
            return

        # 2) Tentar replace atomico com retry
        last_error = None
        for attempt in range(5):
            try:
                os.replace(tmp_path, self.scum_notifications_path)
                return
            except OSError as e:
                last_error = e
                winerror = getattr(e, "winerror", None)
                errno = getattr(e, "errno", None)
                if winerror not in (5, 32) and errno != 13:
                    break
                time.sleep(0.15 * (2**attempt))

        # 3) Fallback: escrita direta no destino (tambem pode falhar)
        direct_error: Optional[Exception] = None
        for attempt in range(5):
            try:
                with open(self.scum_notifications_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
                if last_error:
                    try:
                        self.logger.warn(
                            "Notifications.json estava bloqueado; aplicado fallback de escrita direta",
                            {
                                "path": str(self.scum_notifications_path),
                                "error": str(last_error),
                            },
                        )
                    except Exception:
                        pass
                return
            except OSError as e:
                direct_error = e
                winerror = getattr(e, "winerror", None)
                errno = getattr(e, "errno", None)
                if winerror not in (5, 32) and errno != 13:
                    break
                time.sleep(0.15 * (2**attempt))
        try:
            self.logger.warn(
                "Falha ao escrever Notifications.json (arquivo bloqueado/permissao)",
                {
                    "path": str(self.scum_notifications_path),
                    "error": str(direct_error or last_error or "unknown"),
                },
            )
        except Exception:
            pass
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return

    def load_current_notifications(self) -> List[Dict[str, Any]]:
        if not self.scum_notifications_path.exists():
            return []
        try:
            with open(self.scum_notifications_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("Notifications"), list):
                return list(data.get("Notifications", []))
            return []
        except Exception:
            return []

    def build_expected_restart_schedule_for_today(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        now = now or datetime.now()
        notifications: List[Dict[str, Any]] = []
        for r in self.get_restart_datetimes_for_date(now):
            notifications.extend(self.build_restart_notifications(r))
        notifications.sort(key=lambda n: (n.get("time") or ["99:99"])[0])
        return notifications

    def validate_restart_presence(self, current: List[Dict[str, Any]], expected: List[Dict[str, Any]]) -> bool:
        current_times = set()
        for n in current:
            t = (n.get("time") or [None])[0]
            msg = n.get("message", "")
            if t and isinstance(t, str) and "RESTART" in str(msg).upper():
                current_times.add(t)

        expected_times = set()
        for n in expected:
            t = (n.get("time") or [None])[0]
            msg = n.get("message", "")
            if t and isinstance(t, str) and "RESTART" in str(msg).upper():
                expected_times.add(t)

        if not expected_times:
            return True

        missing = expected_times - current_times
        return len(missing) == 0
