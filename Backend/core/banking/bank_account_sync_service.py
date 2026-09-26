"""Serviço de sincronização de saldos bancários do SCUM.db para o SSM.db"""

import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional

import schedule

from utils.logger import StructuredLogger
from core.database.connector import DatabaseConnector


class BankAccountSyncService:
    """Sincroniza saldos bancários do SCUM.db para o SSM.db"""

    def __init__(
        self,
        config: Dict[str, Any],
        path_helper=None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        self.sync_config = self.config.get("bank_account_sync", {})

        self.enabled = self.sync_config.get("enabled", True)
        self.auto_start = self.sync_config.get("auto_start", True)
        self.sync_interval_hours = self.sync_config.get("sync_interval_hours", 4)
        self.reconcile_enabled = self.sync_config.get("reconcile_enabled", True)
        self.reconcile_interval_minutes = int(
            self.sync_config.get("reconcile_interval_minutes", 10) or 10
        )

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
            "BankAccountSyncService inicializado",
            {
                "enabled": self.enabled,
                "auto_start": self.auto_start,
                "sync_interval_hours": self.sync_interval_hours,
                "reconcile_enabled": self.reconcile_enabled,
                "reconcile_interval_minutes": self.reconcile_interval_minutes,
                "scum_db_path": self.scum_db_path,
                "ssm_db_path": self.ssm_db_path,
            },
        )

        # Garantir que a tabela existe
        self.ensure_table()

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    _initialized_schema = False
    _schema_lock = threading.Lock()

    def ensure_table(self):
        """Garantir que as tabelas bank_accounts_snapshot e bank_accounts_current existem"""
        # Se já foi inicializado nesta execução, pular para reduzir carga no banco
        if BankAccountSyncService._initialized_schema:
            return

        with BankAccountSyncService._schema_lock:
            # Check-double-lock
            if BankAccountSyncService._initialized_schema:
                return

            max_retries = 3
            timeout = 30.0

            for attempt in range(max_retries):
                try:
                    with DatabaseConnector.get_connection(self.ssm_db_path, timeout=timeout, write_mode=True) as conn:
                        cursor = conn.cursor()

                        # Criar tabela se não existir
                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS bank_accounts_snapshot (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                
                                -- Identificação do jogador
                                steam_id TEXT NOT NULL,
                                player_name TEXT,
                                
                                -- Dados da conta bancária
                                account_number TEXT,
                                money_balance REAL DEFAULT 0,
                                gold_balance REAL DEFAULT 0,
                                total_balance REAL DEFAULT 0,
                                
                                -- Metadados
                                snapshot_at TEXT NOT NULL,
                                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                
                                -- Relacionamento com tabela players
                                FOREIGN KEY (steam_id) REFERENCES players(steam_id),
                                
                                -- Índices para performance
                                UNIQUE(steam_id, snapshot_at)
                            )
                        """
                        )

                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS bank_accounts_current (
                                steam_id TEXT PRIMARY KEY,

                                player_name TEXT,
                                account_number TEXT,

                                pocket_money_balance REAL DEFAULT 0,
                                money_balance REAL DEFAULT 0,
                                gold_balance REAL DEFAULT 0,
                                account_balance REAL DEFAULT 0,
                                total_balance REAL DEFAULT 0,

                                last_transaction_ts TEXT,
                                source TEXT,
                                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

                                FOREIGN KEY (steam_id) REFERENCES players(steam_id)
                            )
                        """
                        )

                        # Migração leve: adicionar colunas novas sem quebrar bancos existentes
                        cursor.execute("PRAGMA table_info(bank_accounts_current)")
                        current_cols = {row[1] for row in cursor.fetchall()}
                        if "pocket_money_balance" not in current_cols:
                            cursor.execute(
                                "ALTER TABLE bank_accounts_current ADD COLUMN pocket_money_balance REAL DEFAULT 0"
                            )

                        # Criar índices se não existirem
                        cursor.execute(
                            """
                            CREATE INDEX IF NOT EXISTS idx_bank_accounts_steam_id 
                            ON bank_accounts_snapshot(steam_id)
                        """
                        )

                        cursor.execute(
                            """
                            CREATE INDEX IF NOT EXISTS idx_bank_accounts_snapshot_at 
                            ON bank_accounts_snapshot(snapshot_at)
                        """
                        )

                        cursor.execute(
                            """
                            CREATE INDEX IF NOT EXISTS idx_bank_accounts_total_balance 
                            ON bank_accounts_snapshot(total_balance DESC)
                        """
                        )

                        cursor.execute(
                            """
                            CREATE INDEX IF NOT EXISTS idx_bank_accounts_current_total_balance
                            ON bank_accounts_current(total_balance DESC)
                        """
                        )

                        cursor.execute(
                            """
                            CREATE INDEX IF NOT EXISTS idx_bank_accounts_current_updated_at
                            ON bank_accounts_current(updated_at DESC)
                        """
                        )

                        conn.commit()
                        BankAccountSyncService._initialized_schema = True
                        return  # Sucesso - sair do loop de retry

                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        delay = 2.0 * (2**attempt)  # Backoff exponencial: 2s, 4s, 8s
                        self.logger.warn(
                            f"Banco bloqueado ao garantir tabela bank_accounts_snapshot, tentando novamente em {delay:.1f}s (tentativa {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    raise
                except Exception as exc:
                    self.logger.error(
                        "Erro ao garantir tabela bank_accounts_snapshot",
                        {"error": str(exc), "attempt": attempt + 1},
                    )
                    if attempt == max_retries - 1:
                        raise
                    delay = 2.0 * (2**attempt)
                    time.sleep(delay)

    # ------------------------------------------------------------------
    # Lógica de agendamento
    # ------------------------------------------------------------------

    def start(self) -> Dict[str, Any]:
        """Iniciar sincronização periódica"""
        if not self.enabled:
            return {
                "success": False,
                "message": "Sincronização de saldos bancários desabilitada",
                "status": "disabled",
            }

        if self.is_running:
            return {
                "success": False,
                "message": "Sincronização de saldos bancários já em execução",
                "status": "already_running",
            }

        try:
            self.ensure_table()
            self.logger.info("Executando sincronização inicial de saldos bancários")
            self.sync_once()

            self.scheduler.clear()
            self.scheduler.every(self.sync_interval_hours).hours.do(self.sync_once)

            if self.reconcile_enabled and self.reconcile_interval_minutes > 0:
                self.scheduler.every(self.reconcile_interval_minutes).minutes.do(
                    self.reconcile_current
                )

            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self.scheduler_thread.start()
            self.is_running = True

            self.logger.info(
                "BankAccountSyncService iniciado",
                {
                    "sync_interval_hours": self.sync_interval_hours,
                    "reconcile_enabled": self.reconcile_enabled,
                    "reconcile_interval_minutes": self.reconcile_interval_minutes,
                },
            )

            return {
                "success": True,
                "message": "Sincronização de saldos bancários iniciada",
                "status": "started",
                "sync_interval_hours": self.sync_interval_hours,
                "reconcile_enabled": self.reconcile_enabled,
                "reconcile_interval_minutes": self.reconcile_interval_minutes,
            }

        except Exception as exc:
            self.logger.error(
                "Erro ao iniciar BankAccountSyncService", {"error": str(exc)}
            )
            return {
                "success": False,
                "message": f"Erro ao iniciar sincronização: {exc}",
                "status": "error",
            }

    def stop(self) -> Dict[str, Any]:
        """Parar sincronização"""
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
            "message": "Sincronização de saldos bancários parada",
            "status": "stopped",
        }

    def _scheduler_loop(self):
        """Loop do scheduler em thread separada"""
        while not self.stop_event.is_set():
            try:
                self.scheduler.run_pending()
                time.sleep(1)
            except Exception as exc:
                self.logger.error(
                    "Erro no loop de agendamento de saldos bancários",
                    {"error": str(exc)},
                )
                time.sleep(5)

    # ------------------------------------------------------------------
    # Sincronização principal
    # ------------------------------------------------------------------

    def sync_once(self) -> Dict[str, Any]:
        """Executar uma sincronização"""
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

            # 1. Primeiro, obter lista de steam_ids da tabela players do SSM.db
            valid_steam_ids = set()
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as ssm_conn:
                ssm_cursor = ssm_conn.cursor()
                ssm_cursor.execute("SELECT steam_id FROM players")
                valid_steam_ids = {row[0] for row in ssm_cursor.fetchall()}

            if not valid_steam_ids:
                self.logger.warning(
                    "Nenhum jogador encontrado na tabela players do SSM.db"
                )
                result = {
                    "success": True,
                    "rows_processed": 0,
                    "total_players": 0,
                    "snapshot_at": datetime.utcnow().isoformat(),
                    "elapsed_seconds": round(time.monotonic() - start_time, 3),
                    "message": "Nenhum jogador na tabela players para sincronizar",
                }
                self.last_sync_info = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "success",
                    "details": result,
                }
                return result

            # 2. Query no SCUM.db baseada no projeto antigo, filtrada por steam_ids válidos
            from utils.scum_db_helper import scum_db_readonly_connection

            with scum_db_readonly_connection(self.scum_db_path) as scum_conn:
                scum_conn.row_factory = sqlite3.Row
                scum_cursor = scum_conn.cursor()

                # Criar placeholders para a lista de steam_ids
                placeholders = ",".join("?" * len(valid_steam_ids))

                query = f"""
                    SELECT DISTINCT
                        up.user_id as steam_id,
                        up.name as player_name,
                        up.money_balance as pocket_money_balance,
                        bar.bank_account_number,
                        barc.currency_type,
                        barc.account_balance
                    FROM user_profile up
                    INNER JOIN bank_account_registry bar ON up.id = bar.account_owner_user_profile_id
                    INNER JOIN bank_account_registry_currencies barc ON bar.id = barc.bank_account_id
                    WHERE barc.account_balance > 0
                      AND up.user_id IN ({placeholders})
                    ORDER BY up.name, barc.currency_type
                """

                scum_cursor.execute(query, list(valid_steam_ids))
                rows = scum_cursor.fetchall()

            # Processar e agrupar dados por jogador
            players_data = {}

            for row in rows:
                steam_id = row["steam_id"]
                player_name = row["player_name"]
                pocket_money_balance = float(row["pocket_money_balance"] or 0.0)
                account_number = row["bank_account_number"]
                currency_type = row["currency_type"]
                account_balance = float(row["account_balance"])

                # Inicializar jogador se não existir
                if steam_id not in players_data:
                    players_data[steam_id] = {
                        "steam_id": steam_id,
                        "player_name": player_name,
                        "account_number": account_number,
                        "pocket_money_balance": pocket_money_balance,
                        "money_balance": 0.0,
                        "gold_balance": 0.0,
                        "account_balance": 0.0,
                        "total_balance": 0.0,
                    }

                # Atualizar money em mãos (vem do user_profile, não de currency_type)
                players_data[steam_id]["pocket_money_balance"] = pocket_money_balance
                players_data[steam_id]["money_balance"] = pocket_money_balance

                # Adicionar saldo por tipo de moeda
                if currency_type == 1:  # Money
                    players_data[steam_id]["account_balance"] = account_balance
                elif currency_type == 2:  # Gold
                    players_data[steam_id]["gold_balance"] = account_balance

                # Atualizar total
                players_data[steam_id]["total_balance"] = (
                    players_data[steam_id]["money_balance"]
                    + players_data[steam_id]["account_balance"]
                )

            # Inserir snapshots no SSM.db
            snapshot_at = datetime.utcnow().isoformat()
            inserted = 0

            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cursor = conn.cursor()

                insert_sql = """
                    INSERT OR IGNORE INTO bank_accounts_snapshot 
                        (steam_id, player_name, account_number, money_balance, gold_balance, total_balance, snapshot_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """

                upsert_current_sql = """
                    INSERT INTO bank_accounts_current (
                        steam_id, player_name, account_number,
                        pocket_money_balance, money_balance, gold_balance, account_balance, total_balance,
                        last_transaction_ts, source, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(steam_id) DO UPDATE SET
                        player_name = excluded.player_name,
                        account_number = excluded.account_number,
                        pocket_money_balance = CASE
                            WHEN excluded.pocket_money_balance > 0
                                 AND (bank_accounts_current.money_balance IS NULL OR bank_accounts_current.money_balance = 0)
                            THEN excluded.pocket_money_balance
                            ELSE COALESCE(bank_accounts_current.pocket_money_balance, 0)
                        END,
                        money_balance = CASE
                            WHEN excluded.money_balance > 0
                                 AND (bank_accounts_current.money_balance IS NULL OR bank_accounts_current.money_balance = 0)
                            THEN excluded.money_balance
                            ELSE COALESCE(bank_accounts_current.money_balance, 0)
                        END,
                        gold_balance = excluded.gold_balance,
                        account_balance = excluded.account_balance,
                        total_balance = (
                            CASE
                                WHEN excluded.money_balance > 0
                                     AND (bank_accounts_current.money_balance IS NULL OR bank_accounts_current.money_balance = 0)
                                THEN excluded.money_balance
                                ELSE COALESCE(bank_accounts_current.money_balance, 0)
                            END
                        ) + excluded.account_balance,
                        last_transaction_ts = bank_accounts_current.last_transaction_ts,
                        source = excluded.source,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE bank_accounts_current.last_transaction_ts IS NULL
                       OR excluded.last_transaction_ts IS NULL
                       OR excluded.last_transaction_ts >= bank_accounts_current.last_transaction_ts
                """

                for player_data in players_data.values():
                    cursor.execute(
                        insert_sql,
                        (
                            player_data["steam_id"],
                            player_data["player_name"],
                            player_data["account_number"],
                            player_data["money_balance"],
                            player_data["gold_balance"],
                            player_data["total_balance"],
                            snapshot_at,
                        ),
                    )

                    cursor.execute(
                        upsert_current_sql,
                        (
                            player_data["steam_id"],
                            player_data["player_name"],
                            player_data["account_number"],
                            player_data["pocket_money_balance"],
                            player_data["money_balance"],
                            player_data["gold_balance"],
                            player_data["account_balance"],
                            player_data["total_balance"],
                            None,
                            "scum_db_snapshot",
                        ),
                    )
                    inserted += 1

                conn.commit()

            elapsed = time.monotonic() - start_time

            result = {
                "success": True,
                "rows_processed": inserted,
                "total_players": len(players_data),
                "snapshot_at": snapshot_at,
                "elapsed_seconds": round(elapsed, 3),
            }

            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success",
                "details": result,
            }

            self.logger.info(
                "Sincronização de saldos bancários concluída",
                {
                    **result,
                    "valid_players_count": len(valid_steam_ids),
                    "players_with_accounts": len(players_data),
                },
            )
            return result

        except Exception as exc:
            self.logger.error(
                "Erro durante sincronização de saldos bancários", {"error": str(exc)}
            )
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": str(exc)},
            }
            return {"success": False, "error": str(exc)}

    def reconcile_current(self) -> Dict[str, Any]:
        """Atualizar bank_accounts_current a partir do SCUM.db (cópia compartilhada)."""
        start_time = time.monotonic()

        if not os.path.exists(self.scum_db_path):
            message = "SCUM.db não encontrado"
            self.logger.error(message, {"path": self.scum_db_path})
            return {"success": False, "error": message}

        try:
            self.ensure_table()

            valid_steam_ids = set()
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as ssm_conn:
                ssm_cursor = ssm_conn.cursor()
                ssm_cursor.execute("SELECT steam_id FROM players")
                valid_steam_ids = {row[0] for row in ssm_cursor.fetchall()}

            if not valid_steam_ids:
                return {
                    "success": True,
                    "rows_processed": 0,
                    "total_players": 0,
                    "elapsed_seconds": round(time.monotonic() - start_time, 3),
                    "message": "Nenhum jogador na tabela players para reconciliar",
                }

            from utils.scum_db_helper import scum_db_readonly_connection

            with scum_db_readonly_connection(self.scum_db_path) as scum_conn:
                scum_conn.row_factory = sqlite3.Row
                scum_cursor = scum_conn.cursor()

                placeholders = ",".join("?" * len(valid_steam_ids))
                query = f"""
                    SELECT DISTINCT
                        up.user_id as steam_id,
                        up.name as player_name,
                        up.money_balance as pocket_money_balance,
                        bar.bank_account_number,
                        barc.currency_type,
                        barc.account_balance
                    FROM user_profile up
                    INNER JOIN bank_account_registry bar ON up.id = bar.account_owner_user_profile_id
                    INNER JOIN bank_account_registry_currencies barc ON bar.id = barc.bank_account_id
                    WHERE up.user_id IN ({placeholders})
                    ORDER BY up.name, barc.currency_type
                """

                scum_cursor.execute(query, list(valid_steam_ids))
                rows = scum_cursor.fetchall()

            players_data: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                steam_id = row["steam_id"]
                player_name = row["player_name"]
                pocket_money_balance = float(row["pocket_money_balance"] or 0.0)
                account_number = row["bank_account_number"]
                currency_type = row["currency_type"]
                account_balance = float(row["account_balance"])

                if steam_id not in players_data:
                    players_data[steam_id] = {
                        "steam_id": steam_id,
                        "player_name": player_name,
                        "account_number": account_number,
                        "pocket_money_balance": pocket_money_balance,
                        "money_balance": 0.0,
                        "gold_balance": 0.0,
                        "account_balance": 0.0,
                        "total_balance": 0.0,
                    }

                # Money em mãos (vem do user_profile)
                players_data[steam_id]["pocket_money_balance"] = pocket_money_balance
                players_data[steam_id]["money_balance"] = pocket_money_balance

                if currency_type == 1:
                    players_data[steam_id]["account_balance"] = account_balance
                elif currency_type == 2:
                    players_data[steam_id]["gold_balance"] = account_balance

                players_data[steam_id]["total_balance"] = (
                    players_data[steam_id]["money_balance"]
                    + players_data[steam_id]["account_balance"]
                )

            reconcile_at = datetime.utcnow().isoformat()
            updated = 0

            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cursor = conn.cursor()

                upsert_current_sql = """
                    INSERT INTO bank_accounts_current (
                        steam_id, player_name, account_number,
                        pocket_money_balance, money_balance, gold_balance, account_balance, total_balance,
                        last_transaction_ts, source, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(steam_id) DO UPDATE SET
                        player_name = excluded.player_name,
                        account_number = excluded.account_number,
                        pocket_money_balance = CASE
                            WHEN excluded.pocket_money_balance > 0
                                 AND (bank_accounts_current.money_balance IS NULL OR bank_accounts_current.money_balance = 0)
                            THEN excluded.pocket_money_balance
                            ELSE COALESCE(bank_accounts_current.pocket_money_balance, 0)
                        END,
                        money_balance = CASE
                            WHEN excluded.money_balance > 0
                                 AND (bank_accounts_current.money_balance IS NULL OR bank_accounts_current.money_balance = 0)
                            THEN excluded.money_balance
                            ELSE COALESCE(bank_accounts_current.money_balance, 0)
                        END,
                        gold_balance = excluded.gold_balance,
                        account_balance = excluded.account_balance,
                        total_balance = (
                            CASE
                                WHEN excluded.money_balance > 0
                                     AND (bank_accounts_current.money_balance IS NULL OR bank_accounts_current.money_balance = 0)
                                THEN excluded.money_balance
                                ELSE COALESCE(bank_accounts_current.money_balance, 0)
                            END
                        ) + excluded.account_balance,
                        last_transaction_ts = bank_accounts_current.last_transaction_ts,
                        source = excluded.source,
                        updated_at = CURRENT_TIMESTAMP
                """

                for player_data in players_data.values():
                    cursor.execute(
                        upsert_current_sql,
                        (
                            player_data["steam_id"],
                            player_data["player_name"],
                            player_data["account_number"],
                            player_data["pocket_money_balance"],
                            player_data["money_balance"],
                            player_data["gold_balance"],
                            player_data["account_balance"],
                            player_data["total_balance"],
                            None,
                            "scum_db_reconcile",
                        ),
                    )
                    updated += 1

                conn.commit()

            return {
                "success": True,
                "rows_processed": updated,
                "total_players": len(players_data),
                "reconcile_at": reconcile_at,
                "elapsed_seconds": round(time.monotonic() - start_time, 3),
            }

        except Exception as exc:
            self.logger.error(
                "Erro durante reconcile de saldos bancários", {"error": str(exc)}
            )
            return {"success": False, "error": str(exc)}

    def get_status(self) -> Dict[str, Any]:
        """Obter status do serviço"""
        return {
            "enabled": self.enabled,
            "is_running": self.is_running,
            "sync_interval_hours": self.sync_interval_hours,
            "last_sync": self.last_sync_info,
        }
