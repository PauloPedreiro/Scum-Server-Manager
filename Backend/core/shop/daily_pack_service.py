import json
import os
import sqlite3
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.database.connector import DatabaseConnector
from utils.logger import StructuredLogger
from utils.restart_guard import is_restart_active


DEFAULT_DAILY_PACK_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "kit_code": 1,
    "cooldown_seconds": 86400,
    "bonus_coins": 50,
    "discord_invite_url": "",
    "reminder_enabled": False,
    "reminder_interval_minutes": 30,
    "reminder_chat_color": 6,
    "reminder_message": (
        "Atenção jogadores, seu Presente diário pode estar disponível! "
        "use /daily em seu chat para conferir"
    ),
}

_CONFIG_LOCK = threading.Lock()


def resolve_config_path(config_path: Optional[Union[str, Path]] = None) -> Path:
    """Resolve o caminho do data/config.json tanto em dev quanto em .exe congelado."""
    if config_path is not None and str(config_path).strip():
        return Path(config_path)

    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "data" / "config.json"

    repo_candidate = Path(__file__).resolve().parent.parent.parent / "data" / "config.json"
    if repo_candidate.exists():
        return repo_candidate

    cwd_candidate = Path("data/config.json")
    if cwd_candidate.exists():
        return cwd_candidate

    return repo_candidate


def _to_bool(val: Any, default: bool) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    if isinstance(val, str):
        low = val.strip().lower()
        if low in ("1", "true", "yes", "sim", "on"):
            return True
        if low in ("0", "false", "no", "nao", "não", "off", ""):
            return False
    return bool(val)


def normalize_daily_pack_config(raw: Any) -> Dict[str, Any]:
    """Normaliza e aplica valores padrão ao bloco daily_pack do config.json."""
    src = raw if isinstance(raw, dict) else {}

    raw_kc = src.get("kit_code", DEFAULT_DAILY_PACK_CONFIG["kit_code"])
    if raw_kc is None or str(raw_kc).strip() == "":
        kit_code: Optional[int] = None
    else:
        try:
            kit_code = int(raw_kc)
        except (ValueError, TypeError):
            kit_code = DEFAULT_DAILY_PACK_CONFIG["kit_code"]

    try:
        cooldown_seconds = max(
            60,
            int(src.get("cooldown_seconds", DEFAULT_DAILY_PACK_CONFIG["cooldown_seconds"]) or 86400),
        )
    except (ValueError, TypeError):
        cooldown_seconds = int(DEFAULT_DAILY_PACK_CONFIG["cooldown_seconds"])

    try:
        bonus_coins = max(0, int(src.get("bonus_coins", DEFAULT_DAILY_PACK_CONFIG["bonus_coins"]) or 0))
    except (ValueError, TypeError):
        bonus_coins = int(DEFAULT_DAILY_PACK_CONFIG["bonus_coins"])

    try:
        reminder_interval_minutes = max(
            1,
            int(
                src.get(
                    "reminder_interval_minutes",
                    DEFAULT_DAILY_PACK_CONFIG["reminder_interval_minutes"],
                )
                or 30
            ),
        )
    except (ValueError, TypeError):
        reminder_interval_minutes = int(DEFAULT_DAILY_PACK_CONFIG["reminder_interval_minutes"])

    try:
        reminder_chat_color = min(
            9,
            max(
                0,
                int(
                    src.get(
                        "reminder_chat_color",
                        DEFAULT_DAILY_PACK_CONFIG["reminder_chat_color"],
                    )
                    if src.get("reminder_chat_color") is not None
                    else DEFAULT_DAILY_PACK_CONFIG["reminder_chat_color"]
                ),
            ),
        )
    except (ValueError, TypeError):
        reminder_chat_color = int(DEFAULT_DAILY_PACK_CONFIG["reminder_chat_color"])

    raw_msg = src.get("reminder_message")
    reminder_message = (
        str(raw_msg)
        if raw_msg is not None
        else str(DEFAULT_DAILY_PACK_CONFIG["reminder_message"])
    )

    discord_invite_url = str(src.get("discord_invite_url") or "").strip()

    return {
        "enabled": _to_bool(src.get("enabled"), bool(DEFAULT_DAILY_PACK_CONFIG["enabled"])),
        "kit_code": kit_code,
        "cooldown_seconds": cooldown_seconds,
        "bonus_coins": bonus_coins,
        "discord_invite_url": discord_invite_url,
        "reminder_enabled": _to_bool(
            src.get("reminder_enabled"), bool(DEFAULT_DAILY_PACK_CONFIG["reminder_enabled"])
        ),
        "reminder_interval_minutes": reminder_interval_minutes,
        "reminder_chat_color": reminder_chat_color,
        "reminder_message": reminder_message,
    }


def _read_full_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_daily_pack_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Lê a seção daily_pack normalizada do config.json."""
    path = resolve_config_path(config_path)
    cfg = _read_full_config(path)
    return normalize_daily_pack_config(cfg.get("daily_pack"))


def save_daily_pack_config(
    updates: Dict[str, Any], config_path: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """Atualiza o bloco daily_pack no config.json preservando o restante do arquivo."""
    path = resolve_config_path(config_path)
    with _CONFIG_LOCK:
        cfg = _read_full_config(path)
        current_dp = cfg.get("daily_pack")
        merged = dict(current_dp) if isinstance(current_dp, dict) else {}
        for k, v in (updates or {}).items():
            merged[k] = v

        normalized = normalize_daily_pack_config(merged)
        cfg["daily_pack"] = normalized

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

        return normalized


def is_rcon_enabled(config_path: Optional[Union[str, Path]] = None) -> bool:
    """Verifica se RCON está habilitado no config.json."""
    path = resolve_config_path(config_path)
    cfg = _read_full_config(path)
    rcon = cfg.get("rcon")
    if not isinstance(rcon, dict) or not rcon.get("enabled", False):
        return False
    provider = str(rcon.get("provider", "bsbr_scum")).lower()
    if provider == "bsbr_scum":
        return True
    return bool(rcon.get("password", ""))


def sanitize_chat_lines(message: str) -> List[str]:
    """Sanitiza texto para envio seguro via SendChat RCON, quebrando por linhas."""
    lines: List[str] = []
    for raw_line in str(message or "").split("\n"):
        cleaned = raw_line.replace("\r", "").replace('"', "'")
        cleaned = "".join(ch for ch in cleaned if ord(ch) >= 32).strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def sanitize_inline_text(text: str) -> str:
    """Sanitiza string de linha única para uso seguro dentro de comando RCON entre aspas."""
    cleaned = str(text or "").replace("\r", " ").replace("\n", " ").replace('"', "'")
    return "".join(ch for ch in cleaned if ord(ch) >= 32).strip()


def ensure_daily_pack_tables(conn: sqlite3.Connection) -> None:
    """Garante criação e migração das tabelas daily_pack_claims e daily_pack_claim_history."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_pack_claims (
            steam_id TEXT PRIMARY KEY,
            last_claimed_ts INTEGER NOT NULL,
            last_claimed_at TEXT NOT NULL,
            total_claims INTEGER NOT NULL DEFAULT 1,
            last_command_at TEXT,
            last_kit_code INTEGER,
            last_kit_name TEXT
        )
        """
    )

    cur.execute("PRAGMA table_info('daily_pack_claims')")
    existing_cols = {str(r[1]) for r in (cur.fetchall() or [])}
    migrations = [
        ("last_command_at", "TEXT"),
        ("last_kit_code", "INTEGER"),
        ("last_kit_name", "TEXT"),
    ]
    for col_name, col_type in migrations:
        if col_name not in existing_cols:
            cur.execute(f"ALTER TABLE daily_pack_claims ADD COLUMN {col_name} {col_type}")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_pack_claim_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            steam_id TEXT NOT NULL,
            player_name TEXT,
            kit_code INTEGER,
            kit_name TEXT,
            bonus_coins INTEGER NOT NULL DEFAULT 0,
            command_at TEXT NOT NULL,
            claimed_ts INTEGER NOT NULL,
            order_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_daily_pack_history_claimed_ts ON daily_pack_claim_history(claimed_ts DESC)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_daily_pack_history_steam_id ON daily_pack_claim_history(steam_id)"
    )


def get_online_registration_stats(ssm_db_path: str) -> Dict[str, Any]:
    """Retorna jogadores online no momento e quantos ainda não estão registrados no Discord."""
    online_steam_ids: List[str] = []
    unregistered_steam_ids: List[str] = []
    seen = set()

    if not ssm_db_path or not os.path.exists(ssm_db_path):
        return {
            "online_steam_ids": [],
            "unregistered_steam_ids": [],
            "online_total": 0,
            "online_unregistered": 0,
            "online_registered": 0,
        }

    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=15.0, write_mode=False) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT po.steam_id, p.discord_user_id
                FROM players_online po
                LEFT JOIN players p ON po.steam_id = p.steam_id
                WHERE po.status = 'online'
                """
            )
            for row in cur.fetchall() or []:
                sid = str(row[0] or "").strip()
                if not sid or sid in seen:
                    continue
                seen.add(sid)
                online_steam_ids.append(sid)
                discord_id = str(row[1] or "").strip() if row[1] is not None else ""
                if not discord_id:
                    unregistered_steam_ids.append(sid)
    except Exception:
        return {
            "online_steam_ids": [],
            "unregistered_steam_ids": [],
            "online_total": 0,
            "online_unregistered": 0,
            "online_registered": 0,
        }

    total_online = len(online_steam_ids)
    total_unreg = len(unregistered_steam_ids)
    return {
        "online_steam_ids": online_steam_ids,
        "unregistered_steam_ids": unregistered_steam_ids,
        "online_total": total_online,
        "online_unregistered": total_unreg,
        "online_registered": max(0, total_online - total_unreg),
    }


class DailyPackReminderScheduler(threading.Thread):
    """
    Agendador em segundo plano que envia mensagem configurável via SendChat
    quando há pelo menos 1 jogador online não registrado, respeitando cooldown em minutos.
    """

    def __init__(
        self,
        ssm_db_path: str,
        rcon_queue_manager: Optional[Any] = None,
        logger: Optional[StructuredLogger] = None,
        config_path: Optional[Union[str, Path]] = None,
        check_interval_seconds: float = 30.0,
    ):
        super().__init__(daemon=True, name="DailyPackReminderSchedulerThread")
        self.ssm_db_path = ssm_db_path
        self.rcon_queue_manager = rcon_queue_manager
        self.logger = logger or StructuredLogger()
        self.config_path = config_path
        self.check_interval_seconds = max(5.0, float(check_interval_seconds or 30.0))

        self._running = False
        self._stop_event = threading.Event()
        self._send_lock = threading.Lock()
        self._last_sent_ts: float = 0.0
        self._last_sent_at: Optional[str] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        super().start()
        try:
            self.logger.info("DailyPackReminderScheduler iniciado")
        except Exception:
            pass

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        try:
            self.logger.info("DailyPackReminderScheduler parando...")
        except Exception:
            pass
        if self.is_alive():
            self.join(timeout=5.0)

    def run(self):
        # Aguarda até 30s no startup para não disputar RCON com inicialização crítica
        self._stop_event.wait(min(30.0, self.check_interval_seconds))
        while self._running and not self._stop_event.is_set():
            try:
                self.check_and_send_reminder(force=False)
            except Exception as err:
                try:
                    self.logger.error(f"Erro no loop DailyPackReminderScheduler: {err}")
                except Exception:
                    pass
            self._stop_event.wait(self.check_interval_seconds)

    def _resolve_rcon_queue(self):
        if self.rcon_queue_manager is not None:
            return self.rcon_queue_manager
        if not is_rcon_enabled(self.config_path):
            return None
        try:
            from core.rcon_queue_manager import RconQueueManager

            return RconQueueManager.get_instance()
        except Exception:
            return None

    def check_and_send_reminder(
        self, force: bool = False, overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Avalia regras e envia lembrete do /daily via SendChat se aplicável."""
        with self._send_lock:
            dp_cfg = load_daily_pack_config(self.config_path)
            if isinstance(overrides, dict) and overrides:
                merged = dict(dp_cfg)
                for key in ("reminder_message", "reminder_chat_color", "discord_invite_url"):
                    if key in overrides and overrides[key] is not None:
                        merged[key] = overrides[key]
                dp_cfg = normalize_daily_pack_config(merged)
            now = time.time()

            if not force:
                try:
                    if is_restart_active():
                        return {"sent": False, "reason": "restart_active"}
                except Exception:
                    pass

                if not dp_cfg["enabled"] or not dp_cfg["reminder_enabled"]:
                    return {"sent": False, "reason": "disabled"}

                interval_sec = max(1, int(dp_cfg["reminder_interval_minutes"])) * 60
                if self._last_sent_ts > 0 and (now - self._last_sent_ts) < interval_sec:
                    return {
                        "sent": False,
                        "reason": "cooldown",
                        "remaining_seconds": int(interval_sec - (now - self._last_sent_ts)),
                    }

            raw_msg = str(dp_cfg.get("reminder_message") or "")
            rendered_msg = raw_msg.replace("{discord}", str(dp_cfg.get("discord_invite_url") or ""))
            lines = sanitize_chat_lines(rendered_msg)
            if not lines:
                return {"sent": False, "reason": "empty_message"}

            stats = get_online_registration_stats(self.ssm_db_path)
            if stats["online_total"] == 0:
                return {"sent": False, "reason": "no_players_online", **stats}

            if not force and stats["online_unregistered"] == 0:
                return {"sent": False, "reason": "no_unregistered_online", **stats}

            rcon_q = self._resolve_rcon_queue()
            if rcon_q is None:
                return {"sent": False, "reason": "rcon_disabled", **stats}

            chat_color = int(dp_cfg.get("reminder_chat_color", 6))
            for steam_id in stats["online_steam_ids"]:
                for line in lines:
                    rcon_q.enqueue_command(
                        command=f'SendChat {chat_color} "{line}" {steam_id}',
                        delay_after=0.05,
                        priority=15,
                        origin="DAILY_PACK_REMINDER",
                    )

            self._last_sent_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            if not force:
                self._last_sent_ts = now

            try:
                self.logger.info(
                    f"Lembrete DailyPack (/daily) enviado para {stats['online_total']} jogador(es) online "
                    f"({stats['online_unregistered']} não registrado(s))."
                )
            except Exception:
                pass

            return {
                "sent": True,
                "lines_sent": len(lines),
                "players_notified": len(stats["online_steam_ids"]),
                "online_unregistered": stats["online_unregistered"],
                "sent_at": self._last_sent_at,
            }

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": bool(self._running and self.is_alive()),
            "last_sent_ts": self._last_sent_ts or None,
            "last_sent_at": self._last_sent_at,
        }
