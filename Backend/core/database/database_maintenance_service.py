"""
Serviço de Manutenção, Limpeza e Compactação do Banco de Dados SSM.db.
Gerencia expiração de históricos antigos, deduplicação de eventos repetitivos
e execução de VACUUM para recuperação de espaço em disco.
"""

import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import schedule

from core.database.connector import DatabaseConnector
from utils.logger import StructuredLogger


class DatabaseMaintenanceService:
    def __init__(
        self,
        config: Dict[str, Any],
        path_helper=None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        self.maint_config = self.config.get("database_maintenance", {})

        self.enabled = bool(self.maint_config.get("enabled", True))
        self.auto_start = bool(self.maint_config.get("auto_start", True))
        self.retention_days = int(self.maint_config.get("retention_days", 30) or 30)
        self.schedule_time = str(self.maint_config.get("schedule_time", "04:00") or "04:00")
        self.auto_vacuum = bool(self.maint_config.get("auto_vacuum", True))

        if path_helper:
            self.db_path = path_helper.get_ssm_db_path()
        else:
            self.db_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "SSM.db")
            )

        self.scheduler = schedule.Scheduler()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False

        self.last_run_info: Dict[str, Any] = {
            "timestamp": None,
            "status": "never_run",
            "bytes_before": 0,
            "bytes_after": 0,
            "bytes_freed": 0,
            "deleted_rows": {},
            "duration_seconds": 0.0,
            "error": None,
        }

        self.logger.info(
            "DatabaseMaintenanceService inicializado",
            {
                "enabled": self.enabled,
                "db_path": self.db_path,
                "retention_days": self.retention_days,
                "schedule_time": self.schedule_time,
                "auto_vacuum": self.auto_vacuum,
            },
        )

    def get_database_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas atuais de tamanho e contagem de registros do banco."""
        try:
            if not os.path.exists(self.db_path):
                return {"exists": False, "size_bytes": 0, "size_mb": 0.0}

            size_bytes = os.path.getsize(self.db_path)
            size_mb = round(size_bytes / (1024 * 1024), 2)

            counts = {}
            with DatabaseConnector.get_connection(self.db_path, timeout=15.0, write_mode=False) as conn:
                cursor = conn.cursor()
                tables = [
                    "vehicle_ownership_history",
                    "vehicle_current_ownership",
                    "bank_accounts_snapshot",
                    "bank_accounts_current",
                    "bank_transactions",
                    "player_logins",
                    "minigame_events",
                    "chest_inventory_item",
                ]
                for tbl in tables:
                    try:
                        cursor.execute(f"SELECT count(*) FROM {tbl}")
                        counts[tbl] = cursor.fetchone()[0]
                    except Exception:
                        counts[tbl] = 0

            return {
                "exists": True,
                "size_bytes": size_bytes,
                "size_mb": size_mb,
                "counts": counts,
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas do banco: {e}")
            return {"exists": False, "error": str(e)}

    def run_maintenance(
        self,
        retention_days: Optional[int] = None,
        run_vacuum: Optional[bool] = None,
        deduplicate_history: bool = True,
    ) -> Dict[str, Any]:
        """
        Executa a limpeza de dados antigos, deduplicação e compactação (VACUUM).
        Thread-safe: adquire DatabaseConnector._write_lock para exclusividade.
        """
        days = retention_days if retention_days is not None else self.retention_days
        do_vacuum = run_vacuum if run_vacuum is not None else self.auto_vacuum

        start_time = time.monotonic()
        bytes_before = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        cutoff_dt = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff_dt.isoformat()
        cutoff_std = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")
        cutoff_scum = cutoff_dt.strftime("%Y.%m.%d-%H.%M.%S")

        self.logger.info(
            f"Iniciando manutenção do banco de dados (retenção: {days} dias, cutoff: {cutoff_std})..."
        )

        deleted_counts = {}

        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=60.0, write_mode=True) as conn:
                cursor = conn.cursor()

                # 1. Purge & Deduplicate: vehicle_ownership_history
                try:
                    cursor.execute(
                        "SELECT count(*) FROM vehicle_ownership_history WHERE timestamp < ? OR (timestamp IS NULL AND created_at < ?)",
                        (cutoff_std, cutoff_std),
                    )
                    v_old_count = cursor.fetchone()[0]

                    cursor.execute(
                        "DELETE FROM vehicle_ownership_history WHERE timestamp < ? OR (timestamp IS NULL AND created_at < ?)",
                        (cutoff_std, cutoff_std),
                    )
                    deleted_counts["vehicle_ownership_history_expired"] = v_old_count

                    # Deduplicar registros redundantes restantes mantendo MIN(id) por (veículo, dono, tipo)
                    if deduplicate_history:
                        cursor.execute("""
                            DELETE FROM vehicle_ownership_history
                            WHERE id NOT IN (
                                SELECT MIN(id)
                                FROM vehicle_ownership_history
                                GROUP BY vehicle_entity_id, steam_id, ownership_type
                            )
                        """)
                        deleted_counts["vehicle_ownership_history_dedup"] = cursor.rowcount
                except Exception as e:
                    self.logger.warn(f"Aviso ao limpar vehicle_ownership_history: {e}")
                    deleted_counts["vehicle_ownership_history_error"] = str(e)

                # 2. Purge & Deduplicate: bank_accounts_snapshot
                try:
                    # Manter sempre pelo menos o último snapshot de cada jogador (MAX(id))
                    cursor.execute("""
                        DELETE FROM bank_accounts_snapshot
                        WHERE (snapshot_at < ? OR (snapshot_at IS NULL AND created_at < ?))
                          AND id NOT IN (
                              SELECT MAX(id) FROM bank_accounts_snapshot GROUP BY steam_id
                          )
                    """, (cutoff_iso, cutoff_std))
                    deleted_counts["bank_accounts_snapshot_expired"] = cursor.rowcount

                    # Deduplicar snapshots redundantes de saldos inalterados
                    if deduplicate_history:
                        cursor.execute("""
                            DELETE FROM bank_accounts_snapshot
                            WHERE id NOT IN (
                                SELECT MIN(id)
                                FROM bank_accounts_snapshot
                                GROUP BY steam_id, total_balance, gold_balance
                            )
                            AND id NOT IN (
                                SELECT MAX(id)
                                FROM bank_accounts_snapshot
                                GROUP BY steam_id
                            )
                        """)
                        deleted_counts["bank_accounts_snapshot_dedup"] = cursor.rowcount
                except Exception as e:
                    self.logger.warn(f"Aviso ao limpar bank_accounts_snapshot: {e}")
                    deleted_counts["bank_accounts_snapshot_error"] = str(e)

                # 3. Purge: bank_transactions
                try:
                    cursor.execute(
                        "DELETE FROM bank_transactions WHERE timestamp < ? OR (timestamp IS NULL AND created_at < ?)",
                        (cutoff_scum, cutoff_std),
                    )
                    deleted_counts["bank_transactions"] = cursor.rowcount
                except Exception as e:
                    self.logger.warn(f"Aviso ao limpar bank_transactions: {e}")
                    deleted_counts["bank_transactions_error"] = str(e)

                # 4. Purge: player_logins
                try:
                    cursor.execute(
                        "DELETE FROM player_logins WHERE timestamp < ? OR (timestamp IS NULL AND created_at < ?)",
                        (cutoff_std, cutoff_std),
                    )
                    deleted_counts["player_logins"] = cursor.rowcount
                except Exception as e:
                    self.logger.warn(f"Aviso ao limpar player_logins: {e}")
                    deleted_counts["player_logins_error"] = str(e)

                # 5. Purge: minigame_events
                try:
                    cursor.execute(
                        "DELETE FROM minigame_events WHERE timestamp < ? OR (timestamp IS NULL AND created_at < ?)",
                        (cutoff_std, cutoff_std),
                    )
                    deleted_counts["minigame_events"] = cursor.rowcount
                except Exception as e:
                    self.logger.warn(f"Aviso ao limpar minigame_events: {e}")
                    deleted_counts["minigame_events_error"] = str(e)

                # 6. Clean orphans: chest_inventory_item & chest_history
                try:
                    cursor.execute("""
                        DELETE FROM chest_inventory_item
                        WHERE chest_entity_id NOT IN (
                            SELECT entity_id FROM chest_snapshot
                        )
                    """)
                    deleted_counts["chest_inventory_item_orphans"] = cursor.rowcount
                except Exception as e:
                    deleted_counts["chest_inventory_item_error"] = str(e)

                try:
                    cursor.execute(
                        "DELETE FROM chest_history WHERE event_at < ?",
                        (cutoff_std,),
                    )
                    deleted_counts["chest_history"] = cursor.rowcount
                except Exception:
                    pass

                # 7. Clean old deduplication events: vehicle_notification_events
                try:
                    cursor.execute(
                        "DELETE FROM vehicle_notification_events WHERE created_at < ?",
                        (cutoff_std,),
                    )
                    deleted_counts["vehicle_notification_events"] = cursor.rowcount
                except Exception:
                    pass

                conn.commit()

            # 8. VACUUM & Truncate WAL para recuperação de espaço físico em disco
            if do_vacuum:
                self.logger.info("Executando VACUUM e compactação física do arquivo SSM.db...")
                with DatabaseConnector._write_lock:
                    v_conn = sqlite3.connect(self.db_path, timeout=120.0)
                    v_conn.isolation_level = None
                    try:
                        v_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    except Exception:
                        pass
                    try:
                        v_conn.execute("REINDEX")
                    except Exception:
                        pass
                    v_conn.execute("VACUUM")
                    try:
                        v_conn.execute("PRAGMA optimize")
                    except Exception:
                        pass
                    v_conn.close()

            bytes_after = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            bytes_freed = max(0, bytes_before - bytes_after)
            duration = round(time.monotonic() - start_time, 2)

            total_rows_deleted = sum(
                v for k, v in deleted_counts.items() if isinstance(v, int)
            )

            result = {
                "success": True,
                "bytes_before": bytes_before,
                "bytes_after": bytes_after,
                "bytes_freed": bytes_freed,
                "bytes_freed_mb": round(bytes_freed / (1024 * 1024), 2),
                "deleted_counts": deleted_counts,
                "total_rows_deleted": total_rows_deleted,
                "duration_seconds": duration,
                "vacuum_executed": do_vacuum,
            }

            self.last_run_info = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "bytes_before": bytes_before,
                "bytes_after": bytes_after,
                "bytes_freed": bytes_freed,
                "deleted_rows": deleted_counts,
                "duration_seconds": duration,
                "error": None,
            }

            self.logger.info(
                f"Manutenção do banco concluída em {duration}s: {total_rows_deleted} registros removidos. "
                f"Espaço recuperado: {result['bytes_freed_mb']} MB (Tamanho atual: {round(bytes_after / (1024 * 1024), 2)} MB)",
                result,
            )
            return result

        except Exception as e:
            duration = round(time.monotonic() - start_time, 2)
            self.logger.error(f"Erro durante a manutenção do banco: {e}")
            self.last_run_info = {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "bytes_before": bytes_before,
                "bytes_after": bytes_before,
                "bytes_freed": 0,
                "deleted_rows": deleted_counts,
                "duration_seconds": duration,
                "error": str(e),
            }
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": duration,
                "deleted_counts": deleted_counts,
            }

    def _scheduler_loop(self):
        """Loop de execução do agendador em thread separada"""
        self.logger.info(
            f"Scheduler de manutenção do banco iniciado (horário: {self.schedule_time})"
        )
        self.is_running = True

        while not self.stop_event.is_set():
            try:
                self.scheduler.run_pending()
            except Exception as e:
                self.logger.error(f"Erro no loop do agendador de manutenção: {e}")
            
            # Aguardar com stop_event para encerramento instantâneo
            if self.stop_event.wait(30):
                break

        self.is_running = False
        self.logger.info("Scheduler de manutenção do banco encerrado")

    def start(self) -> Dict[str, Any]:
        """Inicia o serviço e seu agendamento"""
        if not self.enabled:
            return {"status": "disabled", "message": "DatabaseMaintenanceService está desativado"}

        if self.is_running:
            return {"status": "already_running", "message": "DatabaseMaintenanceService já está em execução"}

        self.stop_event.clear()
        self.scheduler.clear()

        # Agendar execução diária no horário configurado
        self.scheduler.every().day.at(self.schedule_time).do(self.run_maintenance)

        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="DatabaseMaintenanceScheduler",
        )
        self.scheduler_thread.start()

        return {"status": "started", "message": f"Agendado diariamente às {self.schedule_time}"}

    def stop(self) -> Dict[str, Any]:
        """Para o serviço"""
        if not self.is_running:
            return {"status": "not_running", "message": "DatabaseMaintenanceService não está em execução"}

        self.stop_event.set()
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        self.is_running = False
        return {"status": "stopped", "message": "DatabaseMaintenanceService parado"}

    def update_config(self, new_config: Dict[str, Any]):
        """Atualiza configurações e reagenda se necessário"""
        self.maint_config.update(new_config)
        self.enabled = bool(self.maint_config.get("enabled", self.enabled))
        self.retention_days = int(self.maint_config.get("retention_days", self.retention_days) or 30)
        old_time = self.schedule_time
        self.schedule_time = str(self.maint_config.get("schedule_time", self.schedule_time) or "04:00")
        self.auto_vacuum = bool(self.maint_config.get("auto_vacuum", self.auto_vacuum))

        if self.is_running and old_time != self.schedule_time:
            self.stop()
            if self.enabled:
                self.start()
