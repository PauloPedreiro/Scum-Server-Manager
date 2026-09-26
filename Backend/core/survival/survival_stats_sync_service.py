"""Serviço de sincronização da tabela survival_stats para o SSM.db"""
from core.database.connector import DatabaseConnector

import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import schedule

from utils.logger import StructuredLogger


class SurvivalStatsSyncService:
    """Sincroniza survival_stats do SCUM para o SSM.db"""

    def __init__(
        self,
        config: Dict[str, Any],
        path_helper=None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        self.sync_config = self.config.get("survival_sync", {})

        self.enabled = self.sync_config.get("enabled", True)
        self.auto_start = self.sync_config.get("auto_start", True)
        self.sync_interval_minutes = self.sync_config.get("sync_interval_minutes", 30)

        default_scum_db = (
            path_helper.get_scum_db_path()
            if path_helper
            else "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
        )
        default_ssm_db = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"

        self.scum_db_path = self.sync_config.get("scum_db_path") or default_scum_db
        self.ssm_db_path = self.sync_config.get("ssm_db_path") or default_ssm_db

        self.scheduler = schedule.Scheduler()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False

        self.last_sync_info: Dict[str, Any] = {
            "timestamp": None,
            "status": "never_run",
            "details": {},
        }

        self.logger.info(
            "SurvivalStatsSyncService inicializado",
            {
                "enabled": self.enabled,
                "auto_start": self.auto_start,
                "sync_interval_minutes": self.sync_interval_minutes,
                "scum_db_path": self.scum_db_path,
                "ssm_db_path": self.ssm_db_path,
            },
        )

        self._cached_columns: Optional[List[Dict[str, Any]]] = None

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def _get_scum_columns(self) -> List[Dict[str, Any]]:
        if self._cached_columns is not None:
            return self._cached_columns

        from utils.scum_db_helper import scum_db_readonly_connection

        with scum_db_readonly_connection(self.scum_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(survival_stats)")
            columns = cursor.fetchall()

        if not columns:
            raise RuntimeError("Tabela survival_stats não encontrada no SCUM.db")

        self._cached_columns = [dict(row) for row in columns]
        return self._cached_columns

    _initialized_schema = False
    _schema_lock = threading.Lock()

    def ensure_table(self):
        """Garantir que a tabela survival_stats_snapshot exista com as colunas atualizadas"""
        if SurvivalStatsSyncService._initialized_schema:
            return

        with SurvivalStatsSyncService._schema_lock:
            if SurvivalStatsSyncService._initialized_schema:
                return

            max_retries = 3
            timeout = 30.0
            scum_columns = self._get_scum_columns()

            for attempt in range(max_retries):
                try:
                    with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                        cursor = conn.cursor()

                        cursor.execute("PRAGMA table_info(survival_stats_snapshot)")
                        existing_columns = cursor.fetchall()

                        if not existing_columns:
                            column_defs = []
                            for col in scum_columns:
                                col_type = col.get("type") or "TEXT"
                                column_def = f"{col['name']} {col_type}"
                                if col.get("pk") == 1:
                                    column_def += " PRIMARY KEY"
                                column_defs.append(column_def.strip())

                            column_defs.append("steam_id TEXT")
                            column_defs.append("player_name TEXT")
                            column_defs.append("snapshot_at TEXT NOT NULL")

                            create_sql = f"CREATE TABLE IF NOT EXISTS survival_stats_snapshot ({', '.join(column_defs)})"
                            cursor.execute(create_sql)
                            conn.commit()
                        else:
                            existing_names = {row[1] for row in existing_columns}

                            for col in scum_columns:
                                if col["name"] not in existing_names:
                                    col_type = col.get("type") or "TEXT"
                                    cursor.execute(
                                        f"ALTER TABLE survival_stats_snapshot ADD COLUMN {col['name']} {col_type}"
                                    )

                            for extra_col, col_type in (
                                ("steam_id", "TEXT"),
                                ("player_name", "TEXT"),
                                ("snapshot_at", "TEXT"),
                            ):
                                if extra_col not in existing_names:
                                    cursor.execute(
                                        f"ALTER TABLE survival_stats_snapshot ADD COLUMN {extra_col} {col_type}"
                                    )

                            conn.commit()
                        
                        SurvivalStatsSyncService._initialized_schema = True
                        return

                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        delay = 2.0 * (2**attempt)
                        self.logger.warn(
                            f"Banco bloqueado ao garantir tabela survival_stats_snapshot, tentando novamente em {delay:.1f}s"
                        )
                        time.sleep(delay)
                        continue
                    raise
                except Exception as exc:
                    self.logger.error(
                        "Erro ao garantir tabela survival_stats_snapshot",
                        {"error": str(exc), "attempt": attempt + 1},
                    )
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2.0 * (2**attempt))

    # ------------------------------------------------------------------
    # Lógica de agendamento
    # ------------------------------------------------------------------

    def start(self) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "success": False,
                "message": "Sincronização de survival stats desabilitada",
                "status": "disabled",
            }

        if self.is_running:
            return {
                "success": False,
                "message": "Sincronização de survival stats já em execução",
                "status": "already_running",
            }

        try:
            self.ensure_table()
            self.logger.info("Executando sincronização inicial de survival stats")
            self.sync_once()

            self.scheduler.clear()
            self.scheduler.every(self.sync_interval_minutes).minutes.do(self.sync_once)

            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self.scheduler_thread.start()
            self.is_running = True

            self.logger.info(
                "SurvivalStatsSyncService iniciado",
                {"sync_interval_minutes": self.sync_interval_minutes},
            )

            return {
                "success": True,
                "message": "Sincronização de survival stats iniciada",
                "status": "started",
                "sync_interval_minutes": self.sync_interval_minutes,
            }

        except Exception as exc:
            self.logger.error(
                "Erro ao iniciar SurvivalStatsSyncService", {"error": str(exc)}
            )
            return {
                "success": False,
                "message": f"Erro ao iniciar sincronização: {exc}",
                "status": "error",
            }

    def stop(self) -> Dict[str, Any]:
        if not self.is_running:
            return {
                "success": False,
                "message": "Sincronização não está em execução",
                "status": "not_running",
            }

        self.stop_event.set()
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        self.scheduler.clear()
        self.is_running = False

        return {
            "success": True,
            "message": "Sincronização de survival stats parada",
            "status": "stopped",
        }

    def _scheduler_loop(self):
        while not self.stop_event.is_set():
            try:
                self.scheduler.run_pending()
                time.sleep(1)
            except Exception as exc:
                self.logger.error(
                    "Erro no loop de agendamento de survival stats", {"error": str(exc)}
                )
                time.sleep(5)

    # ------------------------------------------------------------------
    # Sincronização principal
    # ------------------------------------------------------------------

    def sync_once(self) -> Dict[str, Any]:
        start_time = time.monotonic()

        if not os.path.exists(self.scum_db_path):
            message = "SCUM.db não encontrado"
            self.logger.error(message, {"path": self.scum_db_path})
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": message},
            }
            return {"success": False, "error": message}

        try:
            self.ensure_table()

            scum_columns = self._get_scum_columns()
            scum_column_names = [col["name"] for col in scum_columns]
            snapshot_columns = scum_column_names + [
                "steam_id",
                "player_name",
                "snapshot_at",
            ]

            from utils.scum_db_helper import scum_db_readonly_connection

            with scum_db_readonly_connection(self.scum_db_path) as scum_conn:
                scum_conn.row_factory = sqlite3.Row
                scum_cursor = scum_conn.cursor()
                scum_cursor.execute(
                    """
                    SELECT ss.*, up.user_id AS steam_id,
                           COALESCE(up.fake_name, up.name, up.user_id) AS player_name
                    FROM survival_stats ss
                    LEFT JOIN user_profile up ON up.id = ss.user_profile_id
                    """
                )
                rows = scum_cursor.fetchall()

            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("DELETE FROM survival_stats_snapshot")

                placeholders = ",".join("?" for _ in snapshot_columns)
                insert_sql = (
                    f"INSERT OR REPLACE INTO survival_stats_snapshot "
                    f"({', '.join(snapshot_columns)}) VALUES ({placeholders})"
                )

                snapshot_at = datetime.utcnow().isoformat()
                inserted = 0

                for row in rows:
                    row_dict = dict(row)
                    steam_id = row_dict.get("steam_id")
                    player_name = row_dict.get("player_name")

                    values = [row_dict.get(col) for col in scum_column_names]
                    values.append(steam_id)
                    values.append(player_name)
                    values.append(snapshot_at)

                    cursor.execute(insert_sql, values)
                    inserted += 1

                conn.commit()

            elapsed = time.monotonic() - start_time

            result = {
                "success": True,
                "rows_processed": inserted,
                "snapshot_at": snapshot_at,
                "elapsed_seconds": round(elapsed, 3),
            }

            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success",
                "details": result,
            }

            self.logger.info("Sincronização de survival stats concluída", result)
            return result

        except Exception as exc:
            self.logger.error(
                "Erro durante sincronização de survival stats", {"error": str(exc)}
            )
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": str(exc)},
            }
            return {"success": False, "error": str(exc)}

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "is_running": self.is_running,
            "sync_interval_minutes": self.sync_interval_minutes,
            "last_sync": self.last_sync_info,
        }
