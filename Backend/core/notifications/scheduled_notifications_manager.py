import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .scheduled_notifications_store import ScheduledNotificationsStore
from .notifications_compiler import NotificationsCompiler, ReservedWindow


class ScheduledNotificationConflictError(Exception):
    def __init__(self, payload: Dict[str, Any]):
        super().__init__(payload.get("message") or "Scheduled notification conflict")
        self.payload = payload


class ScheduledNotificationsManager:
    def __init__(
        self,
        store: ScheduledNotificationsStore,
        compiler: NotificationsCompiler,
        logger=None,
    ):
        self.store = store
        self.compiler = compiler
        self.logger = logger

    def list(self) -> List[Dict[str, Any]]:
        return self.store.list_items()

    def get(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get_item(item_id)

    def delete(self, item_id: str) -> bool:
        return self.store.delete_item(item_id)

    def _parse_datetime(self, value: str) -> datetime:
        if not isinstance(value, str) or not value:
            raise ValueError("datetime is required")
        return datetime.fromisoformat(value)

    def _parse_hhmm_today(self, hhmm: str, base: datetime) -> datetime:
        h, m = self.compiler._parse_hhmm(hhmm)
        return datetime(base.year, base.month, base.day, h, m)

    def _calc_occurrences_next_24h(
        self, item: Dict[str, Any], now: Optional[datetime] = None
    ) -> List[datetime]:
        now = now or datetime.now()
        schedule = item.get("schedule") or {}
        stype = schedule.get("type")
        occurrences: List[datetime] = []

        if stype == "once":
            dt = self._parse_datetime(schedule.get("datetime"))
            if now <= dt <= now + timedelta(hours=24):
                occurrences.append(dt)
            return occurrences

        if stype == "daily":
            hhmm = schedule.get("time")
            today_dt = self._parse_hhmm_today(hhmm, now)
            tomorrow_dt = self._parse_hhmm_today(hhmm, now + timedelta(days=1))
            for dt in (today_dt, tomorrow_dt):
                if now <= dt <= now + timedelta(hours=24):
                    occurrences.append(dt)
            return occurrences

        if stype == "relative_to_restart":
            offset = schedule.get("offset_minutes")
            try:
                offset = int(offset)
            except Exception:
                raise ValueError("offset_minutes must be an integer")

            for r in self.compiler.get_restart_datetimes_next_24h(now):
                dt = r + timedelta(minutes=offset)
                if now <= dt <= now + timedelta(hours=24):
                    occurrences.append(dt)
            return occurrences

        raise ValueError("schedule.type must be one of: once, daily, relative_to_restart")

    def _validate_reserved_conflicts(
        self, occurrences: List[datetime], now: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        now = now or datetime.now()
        windows = self.compiler.build_reserved_windows(now)
        for dt in occurrences:
            w = self.compiler.is_reserved_time(dt, windows)
            if w:
                return {
                    "error_code": "SCHEDULE_TIME_RESERVED_BY_RESTART",
                    "message": "Esse horario esta reservado para mensagens de restart. Escolha outro horario.",
                    "details": {
                        "requested_time": dt.isoformat(),
                        "conflicting_restart_time": w.restart_time,
                        "reserved_window_start": w.start.isoformat(),
                        "reserved_window_end": w.end.isoformat(),
                        "reserved_before_minutes": self.compiler.reserved_before_minutes,
                        "reserved_after_minutes": self.compiler.reserved_after_minutes,
                    },
                }
        return None

    def validate_item(self, item: Dict[str, Any], now: Optional[datetime] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        now = now or datetime.now()

        if not isinstance(item.get("message"), str) or not item.get("message"):
            raise ValueError("message is required")

        duration = item.get("duration")
        if duration is None:
            duration = 15
        try:
            duration = int(duration)
        except Exception:
            raise ValueError("duration must be an integer")
        if duration <= 0:
            raise ValueError("duration must be > 0")

        color = item.get("color")
        if color is None:
            color = "255-255-255"
        if not isinstance(color, str) or not color:
            raise ValueError("color is required")

        item["duration"] = duration
        item["color"] = color

        occurrences = self._calc_occurrences_next_24h(item, now)
        conflict = self._validate_reserved_conflicts(occurrences, now)
        if conflict:
            return False, conflict

        return True, None

    def create(self, payload: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
        now = now or datetime.now()
        item = {
            "id": payload.get("id") or str(uuid.uuid4()),
            "enabled": bool(payload.get("enabled", True)),
            "title": str(payload.get("title") or "").strip(),
            "message": payload.get("message"),
            "color": payload.get("color", "255-255-255"),
            "duration": payload.get("duration", 15),
            "schedule": payload.get("schedule") or {},
        }

        ok, conflict = self.validate_item(item, now)
        if not ok:
            raise ScheduledNotificationConflictError(conflict)

        return self.store.upsert_item(item)

    def update(self, item_id: str, payload: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
        now = now or datetime.now()
        existing = self.store.get_item(item_id)
        if not existing:
            raise KeyError("not_found")

        merged = dict(existing)
        merged.update(payload or {})
        merged["id"] = item_id

        ok, conflict = self.validate_item(merged, now)
        if not ok:
            raise ScheduledNotificationConflictError(conflict)

        return self.store.upsert_item(merged)

    def build_custom_notifications_next_24h(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        now = now or datetime.now()
        windows = self.compiler.build_reserved_windows(now)
        result: List[Dict[str, Any]] = []

        for item in self.store.list_items():
            if not item.get("enabled", True):
                continue

            try:
                occurrences = self._calc_occurrences_next_24h(item, now)
            except Exception:
                continue

            for dt in occurrences:
                if self.compiler.is_reserved_time(dt, windows):
                    continue
                result.append(
                    {
                        "day": "Everyday",
                        "time": [dt.strftime("%H:%M")],
                        "duration": int(item.get("duration", 15)),
                        "color": item.get("color", "255-255-255"),
                        "message": item.get("message", ""),
                    }
                )

        result.sort(key=lambda n: (n.get("time") or ["99:99"])[0])
        return result
