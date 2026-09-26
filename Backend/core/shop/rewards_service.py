from core.database.connector import DatabaseConnector
import sqlite3
import time
import os
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, List, Optional

from utils.logger import StructuredLogger

from core.shop.db import ssm_tx
from core.shop.wallet_service import WalletService
from core.webhooks.discord_webhook import DiscordWebhook


@dataclass
class TimeRewardResult:
    applied: bool
    balance: int
    ref_id: str


@dataclass
class PlaytimeRewardTickStats:
    processed_players: int
    initialized_baseline: int
    awarded_players: int
    total_points_awarded: int
    errors: int


@dataclass
class PlaytimeRule:
    rule_id: str
    name: str
    enabled: int
    exclusive: int
    points_per_hour: int
    max_hours_per_run: int
    audience_type: str


class RewardsService:
    def __init__(self, ssm_db_path: str, logger: Optional[StructuredLogger] = None):
        self.ssm_db_path = ssm_db_path
        self.logger = logger or StructuredLogger()
        self.config = self._load_config()
        self.discord_webhook = DiscordWebhook(self.config, logger=self.logger)

    def _load_config(self) -> dict:
        config_file = "data/config.json"
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception as e:
                try:
                    self.logger.error(f"Erro ao carregar config em RewardsService: {e}")
                except Exception:
                    pass

        # Carregar configuração de webhooks (v1/v2 com migração automática)
        try:
            webhooks_file = "data/webhooks.json"
            if isinstance(config, dict):
                paths = config.get("paths", {})
                if isinstance(paths, dict):
                    app_paths = paths.get("application", {})
                    if isinstance(app_paths, dict) and "webhooks_file" in app_paths:
                        webhooks_file = app_paths["webhooks_file"]

            from core.webhooks.manager import WebhooksManager
            hooks_manager = WebhooksManager(webhooks_file)
            config["webhooks"] = hooks_manager.load()
        except Exception as e:
            try:
                self.logger.error(f"Erro ao carregar webhooks.json em RewardsService: {e}")
            except Exception:
                pass

        return config

    def _get_player_registration(self, steam_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
        """Retorna o discord_user_id se o jogador for registrado (vinculado), senao None"""
        try:
            if conn is not None:
                cur = conn.execute("SELECT discord_user_id FROM players WHERE steam_id = ?", (steam_id,))
                row = cur.fetchone()
                return str(row[0]).strip() if row and row[0] else None
            else:
                with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as db_conn:
                    cur = db_conn.execute("SELECT discord_user_id FROM players WHERE steam_id = ?", (steam_id,))
                    row = cur.fetchone()
                    return str(row[0]).strip() if row and row[0] else None
        except Exception as e:
            try:
                self.logger.error(f"Erro ao buscar registro do jogador {steam_id}: {e}")
            except Exception:
                pass
            return None

    def _get_grace_period_seconds(self) -> int:
        try:
            pt_rewards = self.config.get("playtime_rewards")
            if isinstance(pt_rewards, dict):
                return int(pt_rewards.get("grace_period_minutes", 5)) * 60
        except Exception as e:
            try:
                self.logger.error(f"Erro ao ler grace_period_minutes do config.json: {e}")
            except Exception:
                pass
        return 300  # Default: 5 minutos

    def _get_config_int(self, key: str, default: int) -> int:
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM app_config WHERE key = ?", (key,))
            row = cur.fetchone()
            if not row:
                return int(default)
            try:
                return int(str(row[0]).strip())
            except Exception:
                return int(default)

    def _ensure_time_reward_state_playtime_schema(self, conn: sqlite3.Connection) -> None:
        cur = conn.execute("PRAGMA table_info(time_reward_state)")
        cols = {str(r[1]) for r in cur.fetchall()}
        if "last_paid_playtime_hours" not in cols:
            conn.execute(
                "ALTER TABLE time_reward_state ADD COLUMN last_paid_playtime_hours INTEGER NOT NULL DEFAULT 0"
            )

    def _ensure_playtime_rules_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS playtime_reward_rules (
                rule_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 0,
                exclusive INTEGER NOT NULL DEFAULT 0,
                points_per_hour INTEGER NOT NULL DEFAULT 0,
                max_hours_per_run INTEGER NOT NULL DEFAULT 0,
                audience_type TEXT NOT NULL DEFAULT 'all',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        cur = conn.execute("PRAGMA table_info(playtime_reward_rules)")
        cols = {str(r[1]) for r in cur.fetchall()}
        if "exclusive" not in cols:
            conn.execute(
                "ALTER TABLE playtime_reward_rules ADD COLUMN exclusive INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_playtime_reward_rules_enabled
            ON playtime_reward_rules(enabled)
            """
        )
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS playtime_reward_state (
                rule_id TEXT NOT NULL,
                steam_id TEXT NOT NULL,
                last_paid_playtime_hours INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY(rule_id, steam_id),
                FOREIGN KEY (rule_id) REFERENCES playtime_reward_rules(rule_id) ON DELETE CASCADE,
                FOREIGN KEY (steam_id) REFERENCES players(steam_id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_playtime_reward_state_steam
            ON playtime_reward_state(steam_id)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS playtime_reward_targets (
                rule_id TEXT NOT NULL,
                steam_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY(rule_id, steam_id),
                FOREIGN KEY (rule_id) REFERENCES playtime_reward_rules(rule_id) ON DELETE CASCADE,
                FOREIGN KEY (steam_id) REFERENCES players(steam_id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_playtime_reward_targets_rule
            ON playtime_reward_targets(rule_id)
            """
        )

    def list_playtime_rules(self, enabled_only: bool = False) -> List[PlaytimeRule]:
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            self._ensure_playtime_rules_schema(conn)
            if enabled_only:
                cur = conn.execute(
                    """
                    SELECT rule_id, name, enabled, exclusive, points_per_hour, max_hours_per_run, audience_type
                    FROM playtime_reward_rules
                    WHERE enabled = 1
                    ORDER BY name ASC
                    """
                )
            else:
                cur = conn.execute(
                    """
                    SELECT rule_id, name, enabled, exclusive, points_per_hour, max_hours_per_run, audience_type
                    FROM playtime_reward_rules
                    ORDER BY name ASC
                    """
                )
            rows = cur.fetchall()

        return [
            PlaytimeRule(
                rule_id=str(r["rule_id"]),
                name=str(r["name"]),
                enabled=int(r["enabled"]),
                exclusive=int(r["exclusive"]),
                points_per_hour=int(r["points_per_hour"]),
                max_hours_per_run=int(r["max_hours_per_run"]),
                audience_type=str(r["audience_type"]),
            )
            for r in rows
        ]

    def upsert_playtime_rule(
        self,
        rule_id: str,
        name: str,
        enabled: int,
        exclusive: int,
        points_per_hour: int,
        max_hours_per_run: int,
        audience_type: str,
    ) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            self._ensure_playtime_rules_schema(conn)
            conn.execute(
                """
                INSERT INTO playtime_reward_rules(rule_id, name, enabled, exclusive, points_per_hour, max_hours_per_run, audience_type)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(rule_id) DO UPDATE SET
                    name = excluded.name,
                    enabled = excluded.enabled,
                    exclusive = excluded.exclusive,
                    points_per_hour = excluded.points_per_hour,
                    max_hours_per_run = excluded.max_hours_per_run,
                    audience_type = excluded.audience_type,
                    updated_at = datetime('now')
                """,
                (
                    str(rule_id),
                    str(name),
                    int(enabled),
                    int(exclusive),
                    int(points_per_hour),
                    int(max_hours_per_run),
                    str(audience_type),
                ),
            )

    def delete_playtime_rule(self, rule_id: str) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            self._ensure_playtime_rules_schema(conn)
            conn.execute("DELETE FROM playtime_reward_rules WHERE rule_id = ?", (str(rule_id),))

    def list_playtime_rule_targets(self, rule_id: str) -> List[str]:
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
            self._ensure_playtime_rules_schema(conn)
            cur = conn.execute(
                """
                SELECT steam_id
                FROM playtime_reward_targets
                WHERE rule_id = ?
                ORDER BY steam_id ASC
                """,
                (str(rule_id),),
            )
            rows = cur.fetchall()
        return [str(r[0]) for r in rows]

    def get_playtime_rule_id_by_name(
        self,
        name: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[str]:
        if conn is not None:
            self._ensure_playtime_rules_schema(conn)
            cur = conn.execute(
                "SELECT rule_id FROM playtime_reward_rules WHERE name = ? LIMIT 1",
                (str(name),),
            )
            row = cur.fetchone()
            return str(row[0]) if row else None

        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as ro_conn:
            self._ensure_playtime_rules_schema(ro_conn)
            cur = ro_conn.execute(
                "SELECT rule_id FROM playtime_reward_rules WHERE name = ? LIMIT 1",
                (str(name),),
            )
            row = cur.fetchone()
            return str(row[0]) if row else None

    def has_playtime_rule_target(
        self,
        rule_id: str,
        steam_id: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> bool:
        if conn is not None:
            self._ensure_playtime_rules_schema(conn)
            cur = conn.execute(
                "SELECT 1 FROM playtime_reward_targets WHERE rule_id = ? AND steam_id = ? LIMIT 1",
                (str(rule_id), str(steam_id)),
            )
            return cur.fetchone() is not None

        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as ro_conn:
            self._ensure_playtime_rules_schema(ro_conn)
            cur = ro_conn.execute(
                "SELECT 1 FROM playtime_reward_targets WHERE rule_id = ? AND steam_id = ? LIMIT 1",
                (str(rule_id), str(steam_id)),
            )
            return cur.fetchone() is not None

    def add_playtime_rule_target_conn(self, rule_id: str, steam_id: str, conn: sqlite3.Connection) -> None:
        self._ensure_playtime_rules_schema(conn)
        conn.execute(
            """
            INSERT INTO playtime_reward_targets(rule_id, steam_id)
            VALUES(?, ?)
            ON CONFLICT(rule_id, steam_id) DO UPDATE SET
                updated_at = datetime('now')
            """,
            (str(rule_id), str(steam_id)),
        )

    def remove_playtime_rule_target_conn(self, rule_id: str, steam_id: str, conn: sqlite3.Connection) -> None:
        self._ensure_playtime_rules_schema(conn)
        conn.execute(
            "DELETE FROM playtime_reward_targets WHERE rule_id = ? AND steam_id = ?",
            (str(rule_id), str(steam_id)),
        )

    def add_playtime_rule_target(self, rule_id: str, steam_id: str) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            self.add_playtime_rule_target_conn(str(rule_id), str(steam_id), conn)

    def remove_playtime_rule_target(self, rule_id: str, steam_id: str) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            self.remove_playtime_rule_target_conn(str(rule_id), str(steam_id), conn)

    def tick_time_reward(self, steam_id: str) -> TimeRewardResult:
        enabled = self._get_config_int("economy.time_reward.enabled", 0)
        if int(enabled) != 1:
            return TimeRewardResult(applied=False, balance=WalletService(self.ssm_db_path).get_balance(steam_id), ref_id="disabled")

        amount = self._get_config_int("economy.time_reward.amount", 0)
        period_seconds = self._get_config_int("economy.time_reward.period_seconds", 3600)
        if period_seconds <= 0:
            period_seconds = 3600

        now_epoch = int(time.time())
        period_index = now_epoch // int(period_seconds)
        ref_id = f"time:{int(period_seconds)}:{int(period_index)}"

        wallet = WalletService(self.ssm_db_path, logger=self.logger)
        res = wallet.apply_delta(
            steam_id=steam_id,
            delta=int(amount),
            reason="time_reward",
            ref_type="time_tick",
            ref_id=ref_id,
            meta={"period_seconds": int(period_seconds), "period_index": int(period_index)},
            allow_negative=False,
        )
        return TimeRewardResult(applied=not res.already_applied, balance=int(res.balance), ref_id=ref_id)

    def _load_sessions(self) -> dict:
        import os
        import json
        db_dir = os.path.dirname(self.ssm_db_path) or "data"
        file_path = os.path.join(db_dir, "playtime_sessions.json")
        if not os.path.exists(file_path):
            return {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            try:
                self.logger.error(f"Erro ao carregar {file_path}: {e}")
            except Exception:
                pass
            return {}

    def _save_sessions(self, sessions: dict) -> None:
        import os
        import json
        db_dir = os.path.dirname(self.ssm_db_path) or "data"
        file_path = os.path.join(db_dir, "playtime_sessions.json")
        try:
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(sessions, f, indent=4)
        except Exception as e:
            try:
                self.logger.error(f"Erro ao salvar {file_path}: {e}")
            except Exception:
                pass

    def _parse_iso_datetime(self, dt_str: str) -> float:
        from datetime import datetime, timezone
        dt_str = dt_str.replace(' ', 'T')
        if not ('+' in dt_str or '-' in dt_str[-6:] or dt_str.endswith('Z')):
            dt_str += '+00:00'
        try:
            return datetime.fromisoformat(dt_str).timestamp()
        except Exception:
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                try:
                    dt = datetime.strptime(dt_str.split('+')[0], fmt)
                    dt = dt.replace(tzinfo=timezone.utc)
                    return dt.timestamp()
                except ValueError:
                    pass
            raise ValueError(f"Formato de data invalido: {dt_str}")

    def tick_playtime_reward_all_players(self) -> PlaytimeRewardTickStats:
        enabled = self._get_config_int("economy.playtime_reward.enabled", 0)
        if int(enabled) != 1:
            return PlaytimeRewardTickStats(
                processed_players=0,
                initialized_baseline=0,
                awarded_players=0,
                total_points_awarded=0,
                errors=0,
            )

        points_per_hour = self._get_config_int("economy.playtime_reward.points_per_hour", 0)
        max_hours_per_run = self._get_config_int("economy.playtime_reward.max_hours_per_run", 0)

        processed_players = 0
        initialized_baseline = 0
        awarded_players = 0
        total_points_awarded = 0
        errors = 0

        wallet = WalletService(self.ssm_db_path, logger=self.logger)
        sessions = self._load_sessions()
        current_time = time.time()
        grace_period_seconds = self._get_grace_period_seconds()

        online_players_map = {}
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
            cur = conn.execute("SELECT steam_id, last_activity, player_name FROM players_online WHERE status = 'online'")
            for r in cur.fetchall():
                online_players_map[str(r[0])] = {
                    "last_activity": str(r[1]),
                    "player_name": str(r[2] or "Unknown")
                }

        with ssm_tx(self.ssm_db_path) as conn:
            # 1. Processar quem está online
            for steam_id, online_data in online_players_map.items():
                try:
                    discord_user_id = self._get_player_registration(steam_id, conn)
                    if not discord_user_id:
                        # Ignorar jogador não registrado
                        continue

                    processed_players += 1
                    last_activity_str = online_data["last_activity"]
                    player_name = online_data["player_name"]
                    db_last_activity = self._parse_iso_datetime(last_activity_str)

                    # Se não tinha sessão anterior, iniciar nova sessão
                    if steam_id not in sessions:
                        sessions[steam_id] = {
                            "session_start": db_last_activity,
                            "last_paid": db_last_activity,
                            "rule_id": "global",
                            "player_name": player_name
                        }
                        initialized_baseline += 1
                        # Notificar Login
                        try:
                            cur_b = conn.execute("SELECT balance FROM wallet WHERE steam_id = ?", (steam_id,))
                            row_b = cur_b.fetchone()
                            balance = int(row_b[0]) if row_b else 0
                            msg = f"Player `{player_name}` (SteamID: `{steam_id}` | Discord: <@{discord_user_id}>) logged in. Balance: `{balance} points.`"
                            self.discord_webhook.send_text_webhook("playtime_rewards", msg)
                        except Exception as ex:
                            self.logger.error(f"Erro ao enviar webhook de login para {steam_id}: {ex}")
                        continue

                    # Se já tinha sessão, atualizar nome se necessário
                    sessions[steam_id]["player_name"] = player_name

                    # Tratar reconexão dentro do grace period (se estava marcado como offline)
                    if "offline_since" in sessions[steam_id]:
                        offline_since = sessions[steam_id].pop("offline_since")
                        offline_duration = current_time - offline_since
                        # Ajustar last_paid e session_start somando a duração em que ficou offline (congelando o tempo)
                        sessions[steam_id]["last_paid"] = sessions[steam_id].get("last_paid", db_last_activity) + offline_duration
                        if "session_start" in sessions[steam_id]:
                            sessions[steam_id]["session_start"] += offline_duration
                        
                        # Notificar Retorno
                        try:
                            cur_b = conn.execute("SELECT balance FROM wallet WHERE steam_id = ?", (steam_id,))
                            row_b = cur_b.fetchone()
                            balance = int(row_b[0]) if row_b else 0
                            msg = f"Player `{player_name}` (SteamID: `{steam_id}` | Discord: <@{discord_user_id}>) returned (Session resumed). Balance: `{balance} points.`"
                            self.discord_webhook.send_text_webhook("playtime_rewards", msg)
                        except Exception as ex:
                            self.logger.error(f"Erro ao enviar webhook de retorno para {steam_id}: {ex}")

                    last_paid = sessions[steam_id].get("last_paid", db_last_activity)
                    elapsed = current_time - last_paid
                    hours_to_pay = int(elapsed // 3600)

                    if hours_to_pay <= 0:
                        continue

                    if max_hours_per_run > 0:
                        hours_to_pay = min(hours_to_pay, max_hours_per_run)

                    if points_per_hour <= 0:
                        sessions[steam_id]["last_paid"] = last_paid + hours_to_pay * 3600
                        continue

                    delta = hours_to_pay * points_per_hour
                    ref_id = f"global:hours:{int(last_paid + hours_to_pay * 3600)}"

                    wallet_res = wallet.apply_delta(
                        steam_id=steam_id,
                        delta=delta,
                        reason="playtime_reward",
                        ref_type="playtime",
                        ref_id=ref_id,
                        meta={
                            "points_per_hour": points_per_hour,
                            "hours_to_pay": hours_to_pay,
                            "last_paid_timestamp": last_paid,
                        },
                        allow_negative=False,
                        conn=conn,
                    )

                    sessions[steam_id]["last_paid"] = last_paid + hours_to_pay * 3600
                    awarded_players += 1
                    total_points_awarded += delta

                    # Notificar Ganho de Recompensa
                    try:
                        new_balance = wallet_res.balance
                        msg = f"Player `{player_name}` (SteamID: `{steam_id}` | Discord: <@{discord_user_id}>) completed {hours_to_pay} hour(s) online and earned +{delta} points `(Rule: Global).` New balance: `{new_balance} points.`"
                        self.discord_webhook.send_text_webhook("playtime_rewards", msg)
                    except Exception as ex:
                        self.logger.error(f"Erro ao enviar webhook de recompensa para {steam_id}: {ex}")

                except Exception as e:
                    errors += 1
                    try:
                        self.logger.error(f"Erro em tick_playtime_reward_all_players para steam_id={steam_id}: {e}")
                    except Exception:
                        pass

            # 2. Processar quem ficou offline
            for sid in list(sessions.keys()):
                if sid not in online_players_map:
                    try:
                        player_name = sessions[sid].get("player_name", "Unknown")
                        discord_user_id = self._get_player_registration(sid, conn)
                        if not discord_user_id:
                            # Se por acaso perdeu registro, remove a sessão silenciosamente
                            sessions.pop(sid, None)
                            continue

                        # Se ainda não marcamos offline_since, é a primeira verificação em que ele está offline
                        if "offline_since" not in sessions[sid]:
                            sessions[sid]["offline_since"] = current_time
                            
                            # Calcular tempo online acumulado até agora e tempo restante na sessão
                            session_start = sessions[sid].get("session_start", current_time)
                            last_paid = sessions[sid].get("last_paid", current_time)
                            
                            total_session_duration = int(current_time - session_start)
                            sh = total_session_duration // 3600
                            sm = (total_session_duration % 3600) // 60
                            duration_str = f"{sh}h {sm}m" if sh > 0 else f"{sm}m"
                            
                            accumulated = int((current_time - last_paid) // 60)
                            
                            # Notificar Logout Temporário (Início da tolerância)
                            try:
                                grace_period_minutes = int(grace_period_seconds // 60)
                                msg = f"Player `{player_name}` (SteamID: `{sid}` | Discord: <@{discord_user_id}>) disconnected. Online time in session: `{duration_str}`. `{grace_period_minutes}min` grace period started (Progress of `{accumulated}m` temporarily frozen)."
                                self.discord_webhook.send_text_webhook("playtime_rewards", msg)
                            except Exception as ex:
                                self.logger.error(f"Erro ao enviar webhook de deslog temporário para {sid}: {ex}")
                        else:
                            # Se já estava marcado offline, ver se expirou a tolerância
                            offline_duration = current_time - sessions[sid]["offline_since"]
                            if offline_duration > grace_period_seconds:
                                # Expirou a tolerância! Deslog permanente
                                session_start = sessions[sid].get("session_start", current_time)
                                last_paid = sessions[sid].get("last_paid", current_time)
                                
                                # Calcular até o momento em que deslogou (offline_since)
                                total_session_duration = int(sessions[sid]["offline_since"] - session_start)
                                sh = total_session_duration // 3600
                                sm = (total_session_duration % 3600) // 60
                                duration_str = f"{sh}h {sm}m" if sh > 0 else f"{sm}m"
                                
                                accumulated = int((sessions[sid]["offline_since"] - last_paid) // 60)
                                
                                # Notificar Logout Permanente
                                try:
                                    msg = f"Player `{player_name}` (SteamID: `{sid}` | Discord: <@{discord_user_id}>) logged out permanently (grace period exceeded). Session terminated (Progress of `{accumulated}m` discarded)."
                                    self.discord_webhook.send_text_webhook("playtime_rewards", msg)
                                except Exception as ex:
                                    self.logger.error(f"Erro ao enviar webhook de deslog permanente para {sid}: {ex}")
                                
                                sessions.pop(sid, None)
                    except Exception as e:
                        try:
                            self.logger.error(f"Erro ao processar logout para steam_id={sid}: {e}")
                        except Exception:
                            pass

        self._save_sessions(sessions)

        return PlaytimeRewardTickStats(
            processed_players=processed_players,
            initialized_baseline=initialized_baseline,
            awarded_players=awarded_players,
            total_points_awarded=total_points_awarded,
            errors=errors,
        )

    def tick_playtime_reward_multi_rules(self) -> PlaytimeRewardTickStats:
        processed_players = 0
        initialized_baseline = 0
        awarded_players = 0
        total_points_awarded = 0
        errors = 0

        wallet = WalletService(self.ssm_db_path, logger=self.logger)

        rule_rows = []
        with ssm_tx(self.ssm_db_path) as conn:
            self._ensure_playtime_rules_schema(conn)
            rules_cur = conn.execute(
                """
                SELECT rule_id, name, enabled, exclusive, points_per_hour, max_hours_per_run, audience_type
                FROM playtime_reward_rules
                WHERE enabled = 1
                ORDER BY name ASC
                """
            )
            rule_rows = rules_cur.fetchall()

        if not rule_rows:
            return self.tick_playtime_reward_all_players()

        online_players_map = {}
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
            cur = conn.execute("SELECT steam_id, last_activity, player_name FROM players_online WHERE status = 'online'")
            for r in cur.fetchall():
                online_players_map[str(r[0])] = {
                    "last_activity": str(r[1]),
                    "player_name": str(r[2] or "Unknown")
                }

        sessions = self._load_sessions()
        current_time = time.time()
        grace_period_seconds = self._get_grace_period_seconds()

        with ssm_tx(self.ssm_db_path) as conn:
            exclusive_players = set()
            for rr in rule_rows:
                try:
                    rule_id = str(rr[0])
                    is_exclusive = 1 if int(rr[3] or 0) == 1 else 0
                    if is_exclusive != 1:
                        continue

                    audience_type = str(rr[6] or "all")
                    if audience_type == "all":
                        exclusive_players |= set(online_players_map.keys())
                    elif audience_type == "list":
                        tcur = conn.execute(
                            "SELECT steam_id FROM playtime_reward_targets WHERE rule_id = ?",
                            (rule_id,),
                        )
                        exclusive_players |= {str(r[0]) for r in tcur.fetchall() if str(r[0]) in online_players_map}
                except Exception as e:
                    try:
                        self.logger.error(f"Erro ao processar exclusividade de regra {rule_id}: {e}")
                    except Exception:
                        pass

            for rr in rule_rows:
                try:
                    rule_id = str(rr[0])
                    rule_name = str(rr[1])
                    is_exclusive = 1 if int(rr[3] or 0) == 1 else 0
                    audience_type = str(rr[6] or "all")
                    points_per_hour = int(rr[4] or 0)
                    max_hours_per_run = int(rr[5] or 0)

                    eligible = None
                    if audience_type == "list":
                        tcur = conn.execute(
                            "SELECT steam_id FROM playtime_reward_targets WHERE rule_id = ?",
                            (rule_id,),
                        )
                        eligible = {str(r[0]) for r in tcur.fetchall()}

                    for steam_id, online_data in online_players_map.items():
                        if eligible is not None and steam_id not in eligible:
                            continue
                        if is_exclusive != 1 and steam_id in exclusive_players:
                            continue

                        discord_user_id = self._get_player_registration(steam_id, conn)
                        if not discord_user_id:
                            continue

                        processed_players += 1
                        try:
                            last_activity_str = online_data["last_activity"]
                            player_name = online_data["player_name"]
                            db_last_activity = self._parse_iso_datetime(last_activity_str)

                            if steam_id not in sessions:
                                sessions[steam_id] = {
                                    "session_start": db_last_activity,
                                    "last_paid": db_last_activity,
                                    "rule_id": rule_id,
                                    "player_name": player_name
                                }
                                initialized_baseline += 1
                                # Notificar Login
                                try:
                                    cur_b = conn.execute("SELECT balance FROM wallet WHERE steam_id = ?", (steam_id,))
                                    row_b = cur_b.fetchone()
                                    balance = int(row_b[0]) if row_b else 0
                                    msg = f"Player `{player_name}` (SteamID: `{steam_id}` | Discord: <@{discord_user_id}>) logged in. Balance: `{balance} points.`"
                                    self.discord_webhook.send_text_webhook("playtime_rewards", msg)
                                except Exception as ex:
                                    self.logger.error(f"Erro ao enviar webhook de login para {steam_id}: {ex}")
                                continue

                            sessions[steam_id]["player_name"] = player_name
                            if sessions[steam_id].get("rule_id") != rule_id:
                                sessions[steam_id]["rule_id"] = rule_id

                            # Tratar reconexão dentro do grace period
                            if "offline_since" in sessions[steam_id]:
                                offline_since = sessions[steam_id].pop("offline_since")
                                offline_duration = current_time - offline_since
                                sessions[steam_id]["last_paid"] = sessions[steam_id].get("last_paid", db_last_activity) + offline_duration
                                if "session_start" in sessions[steam_id]:
                                    sessions[steam_id]["session_start"] += offline_duration
                                
                                # Notificar Retorno
                                try:
                                    cur_b = conn.execute("SELECT balance FROM wallet WHERE steam_id = ?", (steam_id,))
                                    row_b = cur_b.fetchone()
                                    balance = int(row_b[0]) if row_b else 0
                                    msg = f"Player `{player_name}` (SteamID: `{steam_id}` | Discord: <@{discord_user_id}>) returned (Session resumed). Balance: `{balance} points.`"
                                    self.discord_webhook.send_text_webhook("playtime_rewards", msg)
                                except Exception as ex:
                                    self.logger.error(f"Erro ao enviar webhook de retorno para {steam_id}: {ex}")

                            last_paid = sessions[steam_id].get("last_paid", db_last_activity)
                            elapsed = current_time - last_paid
                            hours_to_pay = int(elapsed // 3600)

                            if hours_to_pay <= 0:
                                continue

                            if max_hours_per_run > 0:
                                hours_to_pay = min(hours_to_pay, max_hours_per_run)

                            if points_per_hour <= 0:
                                sessions[steam_id]["last_paid"] = last_paid + hours_to_pay * 3600
                                continue

                            delta = hours_to_pay * points_per_hour
                            ref_id = f"{rule_id}:hours:{int(last_paid + hours_to_pay * 3600)}"

                            wallet_res = wallet.apply_delta(
                                steam_id=steam_id,
                                delta=delta,
                                reason="playtime_reward",
                                ref_type="playtime_rule",
                                ref_id=ref_id,
                                meta={
                                    "rule_id": rule_id,
                                    "points_per_hour": points_per_hour,
                                    "hours_to_pay": hours_to_pay,
                                    "last_paid_timestamp": last_paid,
                                },
                                allow_negative=False,
                                conn=conn,
                            )

                            sessions[steam_id]["last_paid"] = last_paid + hours_to_pay * 3600
                            awarded_players += 1
                            total_points_awarded += delta

                            # Notificar Ganho de Recompensa
                            try:
                                new_balance = wallet_res.balance
                                msg = f"Player `{player_name}` (SteamID: `{steam_id}` | Discord: <@{discord_user_id}>) completed {hours_to_pay} hour(s) online and earned +{delta} points `(Rule: {rule_name}).` New balance: `{new_balance} points.`"
                                self.discord_webhook.send_text_webhook("playtime_rewards", msg)
                            except Exception as ex:
                                self.logger.error(f"Erro ao enviar webhook de recompensa para {steam_id}: {ex}")

                        except Exception as e:
                            errors += 1
                            try:
                                self.logger.error(f"Erro em tick_playtime_reward_multi_rules para rule_id={rule_id} steam_id={steam_id}: {e}")
                            except Exception:
                                pass

                except Exception as e:
                    errors += 1
                    try:
                        self.logger.error(f"Erro processando regra {rr[0]}: {e}")
                    except Exception:
                        pass

            # 2. Processar quem ficou offline
            for sid in list(sessions.keys()):
                if sid not in online_players_map:
                    try:
                        player_name = sessions[sid].get("player_name", "Unknown")
                        discord_user_id = self._get_player_registration(sid, conn)
                        if not discord_user_id:
                            sessions.pop(sid, None)
                            continue

                        if "offline_since" not in sessions[sid]:
                            sessions[sid]["offline_since"] = current_time
                            
                            session_start = sessions[sid].get("session_start", current_time)
                            last_paid = sessions[sid].get("last_paid", current_time)
                            
                            total_session_duration = int(current_time - session_start)
                            sh = total_session_duration // 3600
                            sm = (total_session_duration % 3600) // 60
                            duration_str = f"{sh}h {sm}m" if sh > 0 else f"{sm}m"
                            
                            accumulated = int((current_time - last_paid) // 60)
                            
                            try:
                                grace_period_minutes = int(grace_period_seconds // 60)
                                msg = f"Player `{player_name}` (SteamID: `{sid}` | Discord: <@{discord_user_id}>) disconnected. Online time in session: `{duration_str}`. `{grace_period_minutes}min` grace period started (Progress of `{accumulated}m` temporarily frozen)."
                                self.discord_webhook.send_text_webhook("playtime_rewards", msg)
                            except Exception as ex:
                                self.logger.error(f"Erro ao enviar webhook de deslog temporário para {sid}: {ex}")
                        else:
                            offline_duration = current_time - sessions[sid]["offline_since"]
                            if offline_duration > grace_period_seconds:
                                session_start = sessions[sid].get("session_start", current_time)
                                last_paid = sessions[sid].get("last_paid", current_time)
                                
                                total_session_duration = int(sessions[sid]["offline_since"] - session_start)
                                sh = total_session_duration // 3600
                                sm = (total_session_duration % 3600) // 60
                                duration_str = f"{sh}h {sm}m" if sh > 0 else f"{sm}m"
                                
                                accumulated = int((sessions[sid]["offline_since"] - last_paid) // 60)
                                
                                try:
                                    msg = f"Player `{player_name}` (SteamID: `{sid}` | Discord: <@{discord_user_id}>) logged out permanently (grace period exceeded). Session terminated (Progress of `{accumulated}m` discarded)."
                                    self.discord_webhook.send_text_webhook("playtime_rewards", msg)
                                except Exception as ex:
                                    self.logger.error(f"Erro ao enviar webhook de deslog permanente para {sid}: {ex}")
                                
                                sessions.pop(sid, None)
                    except Exception as e:
                        try:
                            self.logger.error(f"Erro ao processar logout para steam_id={sid}: {e}")
                        except Exception:
                            pass

        self._save_sessions(sessions)

        return PlaytimeRewardTickStats(
            processed_players=processed_players,
            initialized_baseline=initialized_baseline,
            awarded_players=awarded_players,
            total_points_awarded=total_points_awarded,
            errors=errors,
        )
