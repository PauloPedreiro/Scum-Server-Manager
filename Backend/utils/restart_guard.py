import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional


_STATE_LOCK = threading.Lock()
_RESTART_ACTIVE: bool = False
_RESTART_CYCLE_ID: Optional[str] = None
_ALLOW_SCUM_DB_ACCESS: bool = False

_LAST_RETENTION_DATE: Optional[str] = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_log_retention(logs_dir: str, date_str: str) -> None:
    global _LAST_RETENTION_DATE
    if _LAST_RETENTION_DATE == date_str:
        return
    _LAST_RETENTION_DATE = date_str

    keep_days = 14
    max_files = 30

    prefix = "restart_guard_"
    suffix = ".log"

    try:
        names = os.listdir(logs_dir)
    except Exception:
        return

    paths = []
    for name in names:
        if not (name.startswith(prefix) and name.endswith(suffix)):
            continue
        paths.append(os.path.join(logs_dir, name))

    by_date = []
    for p in paths:
        try:
            base = os.path.basename(p)
            raw = base[len(prefix) : -len(suffix)]
            dt = datetime.strptime(raw, "%Y-%m-%d")
            by_date.append((dt.date(), p))
        except Exception:
            continue

    by_date.sort(key=lambda t: t[0], reverse=True)

    cutoff = datetime.now(timezone.utc).date().toordinal() - keep_days
    kept = []
    for d, p in by_date:
        try:
            if d.toordinal() < cutoff:
                try:
                    os.remove(p)
                except Exception:
                    pass
                continue
            kept.append(p)
        except Exception:
            continue

    if len(kept) > max_files:
        for p in kept[max_files:]:
            try:
                os.remove(p)
            except Exception:
                pass


def _guard_log(event: str, payload: Dict[str, Any]) -> None:
    try:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        logs_dir = os.path.join("data", "logs")
        os.makedirs(logs_dir, exist_ok=True)

        try:
            _ensure_log_retention(logs_dir, date_str)
        except Exception:
            pass

        log_path = os.path.join(logs_dir, f"restart_guard_{date_str}.log")

        with _STATE_LOCK:
            restart_cycle_id = _RESTART_CYCLE_ID
            restart_active = _RESTART_ACTIVE
            allow_scum_db_access = _ALLOW_SCUM_DB_ACCESS

        base: Dict[str, Any] = {
            "ts_utc": _utc_now_iso(),
            "event": str(event),
            "restart_active": bool(restart_active),
            "allow_scum_db_access": bool(allow_scum_db_access),
            "restart_cycle_id": restart_cycle_id,
        }
        base.update(payload or {})

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(base, ensure_ascii=False) + "\n")
    except Exception:
        pass


def set_restart_active(active: bool, restart_cycle_id: Optional[str] = None) -> None:
    with _STATE_LOCK:
        global _RESTART_ACTIVE, _RESTART_CYCLE_ID
        _RESTART_ACTIVE = bool(active)
        _RESTART_CYCLE_ID = restart_cycle_id if active else None


def is_restart_active() -> bool:
    with _STATE_LOCK:
        return bool(_RESTART_ACTIVE)


def is_scum_db_access_allowed() -> bool:
    with _STATE_LOCK:
        return bool(_ALLOW_SCUM_DB_ACCESS)


@contextmanager
def allow_scum_db_access(reason: str) -> Iterator[None]:
    with _STATE_LOCK:
        global _ALLOW_SCUM_DB_ACCESS
        prev = _ALLOW_SCUM_DB_ACCESS
        _ALLOW_SCUM_DB_ACCESS = True

    try:
        _guard_log("allow_scum_db_access_enter", {"reason": reason})
        yield
    finally:
        with _STATE_LOCK:
            _ALLOW_SCUM_DB_ACCESS = prev
        _guard_log("allow_scum_db_access_exit", {"reason": reason})


def should_block_scum_db_access(component: str, operation: str, scum_db_path: Optional[str] = None) -> bool:
    with _STATE_LOCK:
        active = bool(_RESTART_ACTIVE)
        allowed = bool(_ALLOW_SCUM_DB_ACCESS)
        restart_cycle_id = _RESTART_CYCLE_ID

    if not active:
        return False
    if allowed:
        return False

    _guard_log(
        "blocked_scum_db_access",
        {
            "component": component,
            "operation": operation,
            "scum_db_path": scum_db_path,
            "restart_cycle_id": restart_cycle_id,
        },
    )
    return True
