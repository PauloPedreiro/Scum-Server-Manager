"""Gerenciador de Elevated Users - Sincroniza elevated_users entre SSM.db e SCUM.db"""
from core.database.connector import DatabaseConnector

import os
import sqlite3
import shutil
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from utils.logger import StructuredLogger


class ElevatedUsersManager:
    """Gerencia elevated users com sincronização automática quando servidor para"""

    def __init__(
        self,
        config: Dict[str, Any],
        server_manager,
        path_helper=None,
        discord_webhook=None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        self.server_manager = server_manager
        self.path_helper = path_helper
        self.discord_webhook = discord_webhook

        # Caminhos dos bancos
        default_scum_db = (
            path_helper.get_scum_db_path()
            if path_helper
            else "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
        )
        default_ssm_db = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"

        self.scum_db_path = default_scum_db
        self.ssm_db_path = default_ssm_db

        # Flag de sincronização em andamento
        self._sync_in_progress = False
        self._last_sync_timestamp = None

        # Inicializar tabelas
        self.ensure_tables()

        self.logger.info(
            "ElevatedUsersManager inicializado",
            {"scum_db_path": self.scum_db_path, "ssm_db_path": self.ssm_db_path},
        )

        # Iniciar thread de verificação periódica (diária)
        self._stop_event = threading.Event()
        self._periodic_thread = threading.Thread(
            target=self._run_periodic_check,
            name="ElevatedUsersPeriodicSyncThread",
            daemon=True
        )
        self._periodic_thread.start()

    def stop(self):
        """Parar thread de verificação periódica"""
        self._stop_event.set()
        if hasattr(self, "_periodic_thread") and self._periodic_thread.is_alive():
            self._periodic_thread.join(timeout=2.0)
        self.logger.info("Thread de verificação periódica de elevated users parada")

    _initialized_schema = False
    _schema_lock = threading.Lock()

    def ensure_tables(self):
        """Garantir que as tabelas necessárias existam"""
        if ElevatedUsersManager._initialized_schema:
            return

        with ElevatedUsersManager._schema_lock:
            if ElevatedUsersManager._initialized_schema:
                return

            try:
                with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                    cursor = conn.cursor()

                    # Verificar se coluna elevated_user existe na tabela players
                    cursor.execute("PRAGMA table_info(players)")
                    columns = [col[1] for col in cursor.fetchall()]

                    if "elevated_user" not in columns:
                        cursor.execute(
                            "ALTER TABLE players ADD COLUMN elevated_user INTEGER DEFAULT 0"
                        )
                        self.logger.info("Coluna elevated_user adicionada à tabela players")

                    # Criar tabela elevated_user
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS elevated_user (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            steam_id TEXT NOT NULL,
                            synced INTEGER DEFAULT 0,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            synced_at DATETIME,
                            UNIQUE(steam_id)
                        )
                    """
                    )

                    # Criar índices
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_elevated_user_steam_id 
                        ON elevated_user(steam_id)
                    """
                    )
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_elevated_user_synced 
                        ON elevated_user(synced)
                    """
                    )

                    conn.commit()
                    ElevatedUsersManager._initialized_schema = True
                    self.logger.info(
                        "Tabelas elevated_user verificadas/criadas com sucesso"
                    )

            except Exception as e:
                self.logger.error(f"Erro ao criar tabelas: {e}")

    def _upsert_app_config(self, key: str, value: str) -> None:
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO app_config(key, value, updated_at)
                    VALUES(?, ?, datetime('now'))
                    ON CONFLICT(key) DO UPDATE SET
                      value = excluded.value,
                      updated_at = excluded.updated_at
                    """,
                    (key, value),
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Erro ao salvar app_config {key}: {e}")

    def _get_app_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM app_config WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row[0] if row else default
        except Exception as e:
            self.logger.error(f"Erro ao ler app_config {key}: {e}")
            return default

    def check_and_schedule_sync(self) -> bool:
        """
        Compara as permissões de admin no SSM.db (tabela players, elevated_user = 1)
        com os registros na tabela elevated_users do SCUM.db.
        Se houver divergências, agenda a sincronização para o próximo restart (define a flag no app_config).
        Retorna True se houver divergências.
        """
        try:
            # 1. Obter admins ativos no SSM.db
            approved_ssm = set()
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT steam_id FROM players WHERE elevated_user = 1")
                approved_ssm = {str(row[0]) for row in cursor.fetchall() if row[0]}

            # 2. Obter admins atuais no SCUM.db (usando read-only)
            current_scum = set()
            if os.path.exists(self.scum_db_path):
                try:
                    scum_uri = f"file:{self.scum_db_path}?mode=ro"
                    conn_scum = sqlite3.connect(scum_uri, uri=True, timeout=10.0)
                    cursor_scum = conn_scum.cursor()
                    cursor_scum.execute("SELECT user_id FROM elevated_users")
                    current_scum = {str(row[0]) for row in cursor_scum.fetchall() if row[0]}
                    conn_scum.close()
                except Exception as e:
                    self.logger.error(f"Erro ao consultar elevated_users no SCUM.db: {e}")
                    return False
            else:
                self.logger.warn(f"SCUM.db não encontrado no caminho: {self.scum_db_path}")
                return False

            # 3. Comparar as listas
            to_add = approved_ssm - current_scum
            to_remove = current_scum - approved_ssm

            has_divergence = len(to_add) > 0 or len(to_remove) > 0

            # 4. Agendar se houver divergência
            if has_divergence:
                self.logger.info(
                    f"Divergência detectada nas permissões de admin! Agendando sincronização para o próximo restart. "
                    f"Adicionar: {len(to_add)}, Remover: {len(to_remove)}"
                )
                self._upsert_app_config("sync_elevated_users_pending", "1")
            else:
                self.logger.info("Verificação diária: permissões de admin estão 100% sincronizadas.")
                self._upsert_app_config("sync_elevated_users_pending", "0")

            return has_divergence

        except Exception as e:
            self.logger.error(f"Erro ao verificar consistência de elevated users: {e}")
            return False

    def _run_periodic_check(self):
        """Thread periódica diária para verificar consistência"""
        self.logger.info("Iniciando thread de verificação periódica de elevated users...")
        # Aguardar 5 segundos após inicialização para dar tempo de inicializar o sistema completamente
        if self._stop_event.wait(5.0):
            return

        while not self._stop_event.is_set():
            try:
                self.check_and_schedule_sync()
            except Exception as e:
                self.logger.error(f"Erro na execução da verificação diária: {e}")

            # Dormir por 24 horas (86400s), checando stop_event a cada 60s
            for _ in range(1440):
                if self._stop_event.wait(60.0):
                    break

    def _ensure_server_stopped(self) -> Tuple[bool, str]:
        """Verificar se o servidor está parado"""
        if not self.server_manager:
            return False, "ServerManager não disponível"

        if self.server_manager._is_service_running():
            return False, "Servidor deve estar parado para modificar elevated_users"

        return True, ""

    def _wait_for_db_unlock(self, max_retries: int = 5, delay: float = 1.0) -> bool:
        """Aguardar banco ficar desbloqueado"""
        try:
            from utils.restart_guard import should_block_scum_db_access

            if should_block_scum_db_access(
                component="ElevatedUsersManager",
                operation="wait_for_db_unlock",
                scum_db_path=self.scum_db_path,
            ):
                return False
        except Exception:
            pass

        for i in range(max_retries):
            try:
                conn = sqlite3.connect(self.scum_db_path, timeout=1)
                conn.close()
                return True
            except sqlite3.OperationalError:
                if i < max_retries - 1:
                    time.sleep(delay)
        return False

    def _release_db_lock(self):
        """Liberar banco SCUM.db após escritas - garante que servidor possa acessar"""
        try:
            try:
                from utils.restart_guard import should_block_scum_db_access

                if should_block_scum_db_access(
                    component="ElevatedUsersManager",
                    operation="release_db_lock",
                    scum_db_path=self.scum_db_path,
                ):
                    return
            except Exception:
                pass

            # Conectar e fazer limpeza final
            conn = sqlite3.connect(self.scum_db_path, timeout=5.0)
            try:
                cursor = conn.cursor()

                # Garantir que não há transações pendentes desta conexão.
                # A limpeza de WAL/SHM e alterações de journal_mode devem ser centralizadas
                # no ServerManager durante o ciclo de restart para evitar disputas de lock.
                try:
                    conn.commit()
                except Exception:
                    pass

                try:
                    conn.close()
                except Exception:
                    pass

                time.sleep(0.5)

                self.logger.info("Banco SCUM.db liberado com sucesso")

            except Exception as e:
                self.logger.error(f"Erro ao liberar banco: {e}")
                if conn:
                    conn.close()
        except Exception as e:
            self.logger.error(f"Erro ao conectar para liberar banco: {e}")

    def _backup_scum_db(self) -> Optional[str]:
        """Criar backup do SCUM.db antes de modificar"""
        try:
            if not os.path.exists(self.scum_db_path):
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.scum_db_path}.backup.{timestamp}"

            shutil.copy2(self.scum_db_path, backup_path)
            self.logger.info(f"Backup do SCUM.db criado: {backup_path}")

            return backup_path
        except Exception as e:
            self.logger.error(f"Erro ao criar backup do SCUM.db: {e}")
            return None

    def _validate_steam_id(self, steam_id: str) -> Tuple[bool, str]:
        """Validar Steam ID (formato e existência na tabela players)"""
        # Validar formato
        if not steam_id or not steam_id.isdigit() or len(steam_id) != 17:
            return False, "Steam ID inválido (deve ter 17 dígitos)"

        # Verificar se existe na tabela players
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT steam_id FROM players WHERE steam_id = ?", (steam_id,)
                )
                if not cursor.fetchone():
                    return False, "Steam ID não encontrado na tabela players"
        except Exception as e:
            return False, f"Erro ao validar Steam ID: {e}"

        return True, ""

    def mark_elevated_user(
        self, steam_id: str, elevated: bool, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Marcar/desmarcar elevated user na tabela players e elevated_user"""
        # Validar Steam ID
        is_valid, error_msg = self._validate_steam_id(steam_id)
        if not is_valid:
            return {"success": False, "error": error_msg}

        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
                cursor = conn.cursor()

                # Obter nome do jogador
                cursor.execute(
                    "SELECT player_name FROM players WHERE steam_id = ?", (steam_id,)
                )
                row = cursor.fetchone()
                player_name = row[0] if row else steam_id

                # 1. Atualizar flag na tabela players
                cursor.execute(
                    "UPDATE players SET elevated_user = ? WHERE steam_id = ?",
                    (1 if elevated else 0, steam_id),
                )

                server_running = (
                    self.server_manager._is_service_running()
                    if self.server_manager
                    else False
                )

                if elevated:
                    # 2. Criar/verificar registro na tabela elevated_user
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO elevated_user (steam_id, synced)
                        VALUES (?, 0)
                    """,
                        (steam_id,),
                    )

                    # Verificar status atual no SCUM.db para saber se já está sincronizado
                    already_in_scum = False
                    if os.path.exists(self.scum_db_path):
                        try:
                            scum_uri = f"file:{self.scum_db_path}?mode=ro"
                            scum_conn = sqlite3.connect(scum_uri, uri=True, timeout=5.0)
                            scum_cursor = scum_conn.cursor()
                            scum_cursor.execute("SELECT 1 FROM elevated_users WHERE user_id = ?", (steam_id,))
                            already_in_scum = scum_cursor.fetchone() is not None
                            scum_conn.close()
                        except Exception:
                            pass

                    if already_in_scum:
                        # Atualizar no SSM.db como sincronizado
                        cursor.execute(
                            "UPDATE elevated_user SET synced = 1, synced_at = CURRENT_TIMESTAMP WHERE steam_id = ?",
                            (steam_id,),
                        )
                        conn.commit()
                        return {
                            "success": True,
                            "message": "Já está sincronizado no SCUM.db",
                            "action": "no_change",
                            "player_name": player_name,
                        }

                    conn.commit()

                    # Agenda para o restart
                    self._upsert_app_config("sync_elevated_users_pending", "1")

                    # Se servidor está parado, sincronizar imediatamente
                    if not server_running:
                        sync_result = self.sync_pending_changes(force=True)
                        if sync_result.get("success"):
                            return {
                                "success": True,
                                "message": "Elevated user sincronizado imediatamente",
                                "action": "synced",
                                "player_name": player_name,
                            }

                    # Servidor rodando, apenas agendado
                    self._send_discord_notification(
                        "scheduled",
                        {
                            "steam_id": steam_id,
                            "player_name": player_name,
                            "reason": reason,
                        },
                    )

                    return {
                        "success": True,
                        "message": "Marcado como elevated user (agendado para o próximo restart)",
                        "action": "scheduled",
                        "player_name": player_name,
                    }
                else:
                    # 3. Se desmarcou, verificar se precisa remover
                    already_in_scum = False
                    if os.path.exists(self.scum_db_path):
                        try:
                            scum_uri = f"file:{self.scum_db_path}?mode=ro"
                            scum_conn = sqlite3.connect(scum_uri, uri=True, timeout=5.0)
                            scum_cursor = scum_conn.cursor()
                            scum_cursor.execute("SELECT 1 FROM elevated_users WHERE user_id = ?", (steam_id,))
                            already_in_scum = scum_cursor.fetchone() is not None
                            scum_conn.close()
                        except Exception:
                            pass

                    if not already_in_scum:
                        # Não está no SCUM.db, apenas garante remoção local
                        cursor.execute(
                            "DELETE FROM elevated_user WHERE steam_id = ?", (steam_id,)
                        )
                        conn.commit()
                        return {
                            "success": True,
                            "message": "Removido (já não estava no SCUM.db)",
                            "action": "removed",
                            "player_name": player_name,
                        }

                    # Está no SCUM.db, precisa remover
                    conn.commit()

                    # Agenda para o restart
                    self._upsert_app_config("sync_elevated_users_pending", "1")

                    if not server_running:
                        sync_result = self.sync_pending_changes(force=True)
                        if sync_result.get("success"):
                            return {
                                "success": True,
                                "message": "Elevated user removido imediatamente",
                                "action": "removed",
                                "player_name": player_name,
                            }

                    self._send_discord_notification(
                        "scheduled",
                        {
                            "steam_id": steam_id,
                            "player_name": player_name,
                            "action": "removal",
                            "reason": reason,
                        },
                    )

                    return {
                        "success": True,
                        "message": "Marcado para remoção (aguardando próximo restart)",
                        "action": "marked_for_removal",
                        "player_name": player_name,
                    }

        except Exception as e:
            self.logger.error(f"Erro ao marcar elevated user: {e}")
            return {"success": False, "error": str(e)}

    def get_pending_changes(self) -> Dict[str, List[Dict[str, Any]]]:
        """Detectar mudanças pendentes comparando o estado do SSM.db com o SCUM.db diretamente"""
        try:
            # 1. Obter aprovados do SSM.db
            approved_ssm = {}
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT steam_id, player_name, created_at FROM players WHERE elevated_user = 1"
                )
                for row in cursor.fetchall():
                    if row[0]:
                        steam_id = str(row[0])
                        player_name = str(row[1]) if row[1] else steam_id
                        created_at = str(row[2]) if row[2] else datetime.now().isoformat()
                        approved_ssm[steam_id] = {
                            "steam_id": steam_id,
                            "player_name": player_name,
                            "created_at": created_at
                        }

            # 2. Obter atuais do SCUM.db (usando read-only para segurança)
            current_scum = set()
            if os.path.exists(self.scum_db_path):
                try:
                    scum_uri = f"file:{self.scum_db_path}?mode=ro"
                    conn_scum = sqlite3.connect(scum_uri, uri=True, timeout=10.0)
                    cursor_scum = conn_scum.cursor()
                    cursor_scum.execute("SELECT user_id FROM elevated_users")
                    current_scum = {str(r[0]) for r in cursor_scum.fetchall() if r[0]}
                    conn_scum.close()
                except Exception as e:
                    self.logger.error(f"Erro ao ler SCUM.db em get_pending_changes: {e}")
            else:
                self.logger.warn(f"SCUM.db não encontrado: {self.scum_db_path}")

            # 3. Comparar
            to_add_ids = set(approved_ssm.keys()) - current_scum
            to_remove_ids = current_scum - set(approved_ssm.keys())

            to_add = [approved_ssm[sid] for sid in to_add_ids]

            to_remove = []
            if to_remove_ids:
                with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
                    cursor = conn.cursor()
                    for sid in to_remove_ids:
                        cursor.execute("SELECT player_name FROM players WHERE steam_id = ?", (sid,))
                        row = cursor.fetchone()
                        player_name = str(row[0]) if row and row[0] else sid
                        to_remove.append({
                            "steam_id": sid,
                            "player_name": player_name,
                            "synced_at": datetime.now().isoformat()
                        })

            return {"to_add": to_add, "to_remove": to_remove}

        except Exception as e:
            self.logger.error(f"Erro ao detectar mudanças pendentes: {e}")
            return {"to_add": [], "to_remove": []}

    def sync_pending_changes(self, force: bool = False) -> Dict[str, Any]:
        """Sincronizar mudanças pendentes entre SSM.db e SCUM.db"""
        if self._sync_in_progress:
            return {"success": False, "error": "Sincronização já em andamento"}

        # Verificar se existe flag de pendência
        pending_flag = self._get_app_config("sync_elevated_users_pending", "0")
        if pending_flag != "1" and not force:
            # Em vez de ignorar sumariamente, fazemos uma verificação em tempo real super rápida
            # para garantir que não há divergências órfãs que passaram despercebidas pela thread.
            pending = self.get_pending_changes()
            if not pending["to_add"] and not pending["to_remove"]:
                self.logger.info("Sincronização de elevated users ignorada: nenhuma mudança pendente (verificação em tempo real).")
                return {
                    "success": True,
                    "message": "Nenhuma mudança pendente (verificação em tempo real limpa)",
                    "changes_count": 0,
                }
            else:
                self.logger.info("Divergência de elevated users detectada em tempo real! Forçando sincronização...")

        self._sync_in_progress = True
        start_t = time.time()
        pending_add = 0
        pending_remove = 0
        changes_count = 0
        errors_count = 0

        try:
            # Verificar se servidor está parado
            server_stopped, error_msg = self._ensure_server_stopped()
            if not server_stopped:
                return {"success": False, "error": error_msg}

            try:
                from utils.restart_guard import should_block_scum_db_access

                if should_block_scum_db_access(
                    component="ElevatedUsersManager",
                    operation="sync_pending_changes",
                    scum_db_path=self.scum_db_path,
                ):
                    return {"success": False, "error": "SCUM_DB_BLOCKED_RESTART_GUARD"}
            except Exception:
                pass

            # Aguardar banco desbloquear
            if not self._wait_for_db_unlock():
                return {"success": False, "error": "Banco SCUM.db ainda está bloqueado"}

            pending = self.get_pending_changes()
            pending_add = len(pending.get("to_add") or [])
            pending_remove = len(pending.get("to_remove") or [])
            try:
                self.logger.info(
                    "[ELEVATED_USERS] Iniciando sync_pending_changes",
                    {"to_add": pending_add, "to_remove": pending_remove},
                )
            except Exception:
                pass

            if not pending["to_add"] and not pending["to_remove"]:
                # Limpar flag de pendência se não há nada a fazer
                self._upsert_app_config("sync_elevated_users_pending", "0")
                return {
                    "success": True,
                    "message": "Nenhuma mudança pendente",
                    "changes_count": 0,
                }

            backup_path = self._backup_scum_db()

            results = {
                "added": [],
                "removed": [],
                "errors": [],
                "backup_path": backup_path,
            }

            # 1. Adicionar novos admins ao SCUM.db
            for item in pending["to_add"]:
                steam_id = item["steam_id"]
                player_name = item.get("player_name", steam_id)
                try:
                    with DatabaseConnector.get_connection(self.scum_db_path, timeout=30.0) as scum_conn:
                        scum_cursor = scum_conn.cursor()
                        scum_cursor.execute(
                            "INSERT OR IGNORE INTO elevated_users (user_id) VALUES (?)",
                            (steam_id,),
                        )
                        scum_conn.commit()

                    with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as ssm_conn:
                        ssm_cursor = ssm_conn.cursor()
                        ssm_cursor.execute(
                            """
                            INSERT INTO elevated_user (steam_id, synced, synced_at)
                            VALUES (?, 1, CURRENT_TIMESTAMP)
                            ON CONFLICT(steam_id) DO UPDATE SET
                              synced = 1,
                              synced_at = CURRENT_TIMESTAMP
                            """,
                            (steam_id,),
                        )
                        ssm_conn.commit()

                    results["added"].append(
                        {"steam_id": steam_id, "player_name": player_name}
                    )

                    self.logger.info(
                        f"Elevated user adicionado: {player_name} ({steam_id})"
                    )

                except Exception as e:
                    error_msg = f"Erro ao adicionar {steam_id}: {e}"
                    results["errors"].append(error_msg)
                    self.logger.error(error_msg)

            # 2. Remover admins revogados do SCUM.db
            for item in pending["to_remove"]:
                steam_id = item["steam_id"]
                player_name = item.get("player_name", steam_id)

                try:
                    with DatabaseConnector.get_connection(self.scum_db_path, timeout=30.0) as scum_conn:
                        scum_cursor = scum_conn.cursor()
                        scum_cursor.execute(
                            "DELETE FROM elevated_users WHERE user_id = ?", (steam_id,)
                        )
                        scum_conn.commit()

                    with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as ssm_conn:
                        ssm_cursor = ssm_conn.cursor()
                        ssm_cursor.execute(
                            "DELETE FROM elevated_user WHERE steam_id = ?", (steam_id,)
                        )
                        ssm_conn.commit()

                    results["removed"].append(
                        {"steam_id": steam_id, "player_name": player_name}
                    )

                    self.logger.info(
                        f"Elevated user removido: {player_name} ({steam_id})"
                    )

                except Exception as e:
                    error_msg = f"Erro ao remover {steam_id}: {e}"
                    results["errors"].append(error_msg)
                    self.logger.error(error_msg)

            # Resetar a flag de pendência após conclusão com sucesso
            self._upsert_app_config("sync_elevated_users_pending", "0")

            final_check = self.get_pending_changes()
            if final_check["to_add"] or final_check["to_remove"]:
                results["errors"].append("Sincronização incompleta detectada")

            changes_count = len(results["added"]) + len(results["removed"])
            errors_count = len(results["errors"])

            self._last_sync_timestamp = datetime.now()

            if results["added"] or results["removed"]:
                self._send_discord_notification("sync", results)

            return {
                "success": len(results["errors"]) == 0,
                "changes_count": changes_count,
                "results": results,
            }

        except Exception as e:
            self.logger.error(f"Erro ao sincronizar mudanças pendentes: {e}")
            return {"success": False, "error": str(e)}
        finally:
            self._release_db_lock()
            self._sync_in_progress = False

            elapsed = time.time() - start_t
            try:
                self.logger.info(
                    "[ELEVATED_USERS] Finalizando sync_pending_changes",
                    {
                        "elapsed_s": round(float(elapsed), 3),
                        "to_add": int(pending_add),
                        "to_remove": int(pending_remove),
                        "changes_count": int(changes_count),
                        "errors_count": int(errors_count),
                    },
                )
            except Exception:
                pass

    def list_elevated_users(self) -> List[Dict[str, Any]]:
        """Listar todos os elevated users com informações"""
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT 
                        eu.steam_id,
                        COALESCE(p.player_name, eu.steam_id) AS player_name,
                        eu.synced,
                        eu.created_at,
                        eu.synced_at
                    FROM elevated_user eu
                    LEFT JOIN players p ON eu.steam_id = p.steam_id
                    ORDER BY eu.created_at DESC
                """
                )

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            self.logger.error(f"Erro ao listar elevated users: {e}")
            return []

    def get_status(self) -> Dict[str, Any]:
        """Obter status do sistema"""
        server_running = (
            self.server_manager._is_service_running() if self.server_manager else False
        )
        pending = self.get_pending_changes()

        return {
            "server_status": "running" if server_running else "stopped",
            "can_modify": not server_running,
            "total_elevated_users": len(self.list_elevated_users()),
            "pending_add": len(pending["to_add"]),
            "pending_remove": len(pending["to_remove"]),
            "scum_db_path": self.scum_db_path,
            "scum_db_exists": os.path.exists(self.scum_db_path),
            "last_sync": (
                self._last_sync_timestamp.isoformat()
                if self._last_sync_timestamp
                else None
            ),
        }

    def _send_discord_notification(self, notification_type: str, data: Dict[str, Any]):
        """Enviar notificação para Discord"""
        if not self.discord_webhook:
            return

        try:
            webhook_url = self.config.get("webhooks", {}).get("log-ssm")
            if not webhook_url:
                return

            now = datetime.now()
            date_str = now.strftime("%d/%m/%Y às %H:%M:%S")

            if notification_type == "scheduled":
                # Notificação de agendamento
                player_name = data.get("player_name", "N/A")
                steam_id = data.get("steam_id", "N/A")

                description = f"{player_name} ({steam_id})\nWaiting for server to stop."

                embed = {
                    "title": "⏳ Elevated User Scheduled",
                    "description": description,
                    "color": 16776960,  # Amarelo
                    "footer": {"text": "Sistema SSM - Elevated Users"},
                }

            elif notification_type == "sync":
                # Notificação de sincronização
                if len(data.get("added", [])) > 1 or len(data.get("removed", [])) > 1:
                    # Múltiplas sincronizações
                    total = len(data.get("added", [])) + len(data.get("removed", []))
                    added_count = len(data.get("added", []))
                    removed_count = len(data.get("removed", []))

                    players_list = []
                    for item in data.get("added", []):
                        players_list.append(
                            f"• {item.get('player_name', item.get('steam_id'))} - Adicionado"
                        )
                    for item in data.get("removed", []):
                        players_list.append(
                            f"• {item.get('player_name', item.get('steam_id'))} - Removido"
                        )

                    embed = {
                        "title": "✅ Sincronização em Lote Concluída",
                        "description": "Todas as mudanças pendentes foram sincronizadas com sucesso.",
                        "color": 65280,  # Verde
                        "fields": [
                            {
                                "name": "📊 Total de Operações",
                                "value": f"{total} operações",
                                "inline": True,
                            },
                            {
                                "name": "➕ Adicionados",
                                "value": f"{added_count} jogadores",
                                "inline": True,
                            },
                            {
                                "name": "➖ Removidos",
                                "value": f"{removed_count} jogador{'es' if removed_count != 1 else ''}",
                                "inline": True,
                            },
                            {
                                "name": "👥 Jogadores",
                                "value": "\n".join(
                                    players_list[:10]
                                ),  # Limitar a 10 para não exceder limite do Discord
                                "inline": False,
                            },
                        ],
                        "footer": {"text": "Sistema SSM - Elevated Users"},
                    }
                else:
                    # Sincronização única
                    # Pegar dados do primeiro item adicionado ou removido
                    player_info = None
                    action = "unknown"

                    if data.get("added") and len(data["added"]) > 0:
                        player_info = data["added"][0]
                        action = "added"
                    elif data.get("removed") and len(data["removed"]) > 0:
                        player_info = data["removed"][0]
                        action = "removed"

                    if player_info:
                        steam_id = player_info.get("steam_id", "N/A")
                        player_name = player_info.get("player_name")

                        # Se player_name não estiver disponível ou for inválido, buscar da tabela players
                        if (
                            not player_name
                            or player_name == "N/A"
                            or not str(player_name).strip()
                        ):
                            if steam_id and steam_id != "N/A":
                                try:
                                    with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            "SELECT player_name FROM players WHERE steam_id = ?",
                                            (steam_id,),
                                        )
                                        row = cursor.fetchone()
                                        if row and row[0] and str(row[0]).strip():
                                            player_name = str(row[0]).strip()
                                        else:
                                            player_name = steam_id
                                except Exception as e:
                                    self.logger.warning(
                                        f"Erro ao buscar player_name para notificação: {e}"
                                    )
                                    player_name = steam_id
                            else:
                                player_name = steam_id
                        else:
                            player_name = steam_id
                    else:
                        steam_id = "N/A"
                        player_name = "N/A"

                    # Construir descrição com todas as informações
                    description_lines = [f"{player_name} ({steam_id})", date_str]

                    # Adicionar backup se disponível (oculto com spoiler)
                    if data.get("backup_path"):
                        backup_name = os.path.basename(data["backup_path"])
                        description_lines.append(f"||💾 {backup_name}||")

                    description = "\n".join(description_lines)

                    # Definir título e cor baseado na ação
                    if action == "added":
                        title = "✅ Elevated User Added"
                        color = 65280  # Verde
                    else:
                        title = "❌ Elevated User Removed"
                        color = 15158332  # Vermelho

                    embed = {
                        "title": title,
                        "description": description,
                        "color": color,
                        "footer": {"text": "Sistema SSM - Elevated Users"},
                    }

            else:
                return

            payload = {"embeds": [embed]}
            self.discord_webhook._send_webhook(webhook_url, payload)

        except Exception as e:
            self.logger.error(f"Erro ao enviar notificação Discord: {e}")
