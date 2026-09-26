"""
Gerenciador de usuários do frontend - CRUD no banco SSM.db
"""

import sqlite3
import os
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from utils.logger import StructuredLogger
from core.database.connector import DatabaseConnector

class UserManager:
    """Gerencia usuários do frontend no banco SSM.db"""

    def __init__(self, db_path: str, logger: Optional[StructuredLogger] = None):
        """
        Inicializa o gerenciador de usuários

        Args:
            db_path: Caminho do banco SSM.db
            logger: Logger para logs
        """
        self.db_path = db_path
        self.logger = logger or StructuredLogger()

        # Garantir que a tabela existe
        self.ensure_table()


    _initialized_schema = False
    _schema_lock = threading.Lock()

    def ensure_table(self):
        """Garante que a tabela frontend_users existe"""
        if UserManager._initialized_schema:
            return

        with UserManager._schema_lock:
            if UserManager._initialized_schema:
                return

            try:
                with DatabaseConnector.get_connection(self.db_path, timeout=30.0, write_mode=True) as conn:
                    cursor = conn.cursor()

                    # Criar tabela se não existir
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS frontend_users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username VARCHAR(50) UNIQUE NOT NULL,
                            password_hash VARCHAR(255) NOT NULL,
                            password_changed INTEGER DEFAULT 0,
                            is_active INTEGER DEFAULT 1,
                            role VARCHAR(20) DEFAULT 'admin',
                            discord_user_id TEXT,
                            steam_id TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            last_login DATETIME,
                            last_password_change DATETIME,
                            FOREIGN KEY (steam_id) REFERENCES players(steam_id) ON DELETE SET NULL
                        )
                    """
                    )

                    try:
                        cursor.execute("PRAGMA table_info('frontend_users')")
                        cols = {str(r[1]).lower() for r in (cursor.fetchall() or [])}
                        if "discord_user_id" not in cols:
                            cursor.execute("ALTER TABLE frontend_users ADD COLUMN discord_user_id TEXT")
                    except Exception:
                        pass

                    # Criar índices
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_frontend_users_username 
                        ON frontend_users(username)
                    """
                    )

                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_frontend_users_role 
                        ON frontend_users(role)
                    """
                    )

                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_frontend_users_steam_id 
                        ON frontend_users(steam_id)
                    """
                    )

                    conn.commit()
                    UserManager._initialized_schema = True
                    self.logger.info("Tabela frontend_users verificada/criada")

            except Exception as e:
                self.logger.error(f"Erro ao criar tabela frontend_users: {e}")
                raise

    def create_user(
        self,
        username: str,
        password_hash: str,
        role: str = "admin",
        steam_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Cria um novo usuário

        Args:
            username: Nome de usuário
            password_hash: Hash da senha
            role: Role do usuário (admin, moderator, etc.)
            steam_id: Steam ID opcional para vincular a players

        Returns:
            Dados do usuário criado ou None se erro
        """
        try:
            from core.database.connector import DatabaseConnector
            with DatabaseConnector.get_connection(self.db_path, write_mode=True) as conn:
                cursor = conn.cursor()

                # Verificar se username já existe
                cursor.execute(
                    "SELECT id FROM frontend_users WHERE username = ?", (username,)
                )
                if cursor.fetchone():
                    return None

                # Verificar steam_id se fornecido
                if steam_id:
                    cursor.execute(
                        "SELECT steam_id FROM players WHERE steam_id = ?", (steam_id,)
                    )
                    if not cursor.fetchone():
                        return None  # steam_id não existe na tabela players

                # Inserir usuário
                now = datetime.utcnow().isoformat()
                cursor.execute(
                    """
                    INSERT INTO frontend_users 
                    (username, password_hash, role, steam_id, created_at, updated_at, password_changed)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                    (username, password_hash, role, steam_id, now, now),
                )

                user_id = cursor.lastrowid
                conn.commit()

            # Retornar dados do usuário criado
            return self.get_user_by_id(user_id)

        except sqlite3.IntegrityError as e:
            self.logger.error(f"Erro de integridade ao criar usuário: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao criar usuário: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Busca usuário por username

        Args:
            username: Nome de usuário

        Returns:
            Dados do usuário ou None
        """
        try:
            from core.database.connector import DatabaseConnector
            with DatabaseConnector.get_connection(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Busca simples (sem JOIN)
                cursor.execute(
                    """
                    SELECT * FROM frontend_users WHERE username = ?
                """,
                    (username,),
                )

                row = cursor.fetchone()

                if row:
                    user_dict = dict(row)

                    # Se tiver steam_id, buscar dados do player
                    if user_dict.get("steam_id"):
                        try:
                            cursor.execute(
                                """
                                SELECT player_name FROM players WHERE steam_id = ?
                            """,
                                (user_dict["steam_id"],),
                            )
                            player_row = cursor.fetchone()
                            if player_row:
                                user_dict["player_name"] = player_row["player_name"]
                                user_dict["player_id"] = user_dict[
                                    "steam_id"
                                ]  # Usar steam_id como player_id
                            else:
                                user_dict["player_name"] = None
                                user_dict["player_id"] = None
                        except Exception as player_error:
                            # Se a tabela players não existir ou houver erro, apenas não adicionar dados do player
                            self.logger.warn(
                                f"Erro ao buscar dados do player para steam_id {user_dict['steam_id']}: {player_error}"
                            )
                            user_dict["player_name"] = None
                            user_dict["player_id"] = None
                    else:
                        user_dict["player_name"] = None
                        user_dict["player_id"] = None

                    return user_dict

            return None

        except Exception as e:
            import traceback

            error_traceback = traceback.format_exc()
            if self.logger:
                self.logger.error(f"Erro ao buscar usuário por username: {e}")
                self.logger.error(f"Traceback: {error_traceback}")
            else:
                print(f"Erro ao buscar usuário por username: {e}")
                print(f"Traceback: {error_traceback}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca usuário por ID

        Args:
            user_id: ID do usuário

        Returns:
            Dados do usuário ou None
        """
        try:
            from core.database.connector import DatabaseConnector
            with DatabaseConnector.get_connection(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Busca simples primeiro (sem JOIN)
                cursor.execute(
                    """
                    SELECT * FROM frontend_users WHERE id = ?
                """,
                    (user_id,),
                )

                row = cursor.fetchone()

                if row:
                    user_dict = dict(row)

                    # Se tiver steam_id, buscar dados do player
                    if user_dict.get("steam_id"):
                        try:
                            cursor.execute(
                                """
                                SELECT player_name FROM players WHERE steam_id = ?
                            """,
                                (user_dict["steam_id"],),
                            )
                            player_row = cursor.fetchone()
                            if player_row:
                                user_dict["player_name"] = player_row["player_name"]
                                user_dict["player_id"] = user_dict[
                                    "steam_id"
                                ]  # Usar steam_id como player_id
                            else:
                                user_dict["player_name"] = None
                                user_dict["player_id"] = None
                        except Exception as player_error:
                            # Se a tabela players não existir ou houver erro, apenas não adicionar dados do player
                            self.logger.warn(
                                f"Erro ao buscar dados do player para steam_id {user_dict['steam_id']}: {player_error}"
                            )
                            user_dict["player_name"] = None
                            user_dict["player_id"] = None
                    else:
                        user_dict["player_name"] = None
                        user_dict["player_id"] = None

                    return user_dict

            return None

        except Exception as e:
            self.logger.error(f"Erro ao buscar usuário por ID: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def update_user(self, user_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Atualiza dados do usuário de forma segura através da fila de escrita serializada.
        Args:
            user_id: ID do usuário
            **kwargs: Campos para atualizar (password_hash, is_active, role, steam_id, etc.)
        Returns:
            Dados atualizados do usuário ou None
        """
        try:
            import time
            from core.database.connector import DatabaseConnector
            from utils.sqlite_queue import submit_sqlite_write
            # Campos permitidos
            allowed_fields = [
                "password_hash",
                "is_active",
                "role",
                "steam_id",
                "discord_user_id",
                "password_changed",
                "last_login",
                "last_password_change",
            ]
            updates = []
            values = []
            for key, value in kwargs.items():
                if key in allowed_fields:
                    updates.append(f"{key} = ?")
                    values.append(value)
            if not updates:
                return None
            # Adicionar updated_at
            updates.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(user_id)
            query = f"""
                UPDATE frontend_users 
                SET {', '.join(updates)}
                WHERE id = ?
            """
            # Definimos a transação de escrita interna
            def db_write_op():
                start_conn = time.perf_counter()
                with DatabaseConnector.get_connection(self.db_path, write_mode=True) as conn:
                    conn_time = time.perf_counter() - start_conn
                    self.logger.info(f"[UserManager.update_user] Conexão de escrita obtida em {conn_time:.4f}s")
                    
                    cursor = conn.cursor()
                    start_exec = time.perf_counter()
                    cursor.execute(query, values)
                    exec_time = time.perf_counter() - start_exec
                    
                    start_commit = time.perf_counter()
                    conn.commit()
                    commit_time = time.perf_counter() - start_commit
                    
                    self.logger.info(
                        f"[UserManager.update_user] Query executada em {exec_time:.4f}s, commit concluído em {commit_time:.4f}s"
                    )
                return True
            # Submete a operação de escrita para execução serializada na fila do SQLite
            start_queue = time.perf_counter()
            submit_sqlite_write(db_write_op, timeout_seconds=30.0)
            queue_time = time.perf_counter() - start_queue
            self.logger.info(f"[UserManager.update_user] Operação de escrita concluída via fila em {queue_time:.4f}s")
            # Busca e retorna os dados atualizados (Operação de leitura segura fora da fila de escrita)
            return self.get_user_by_id(user_id)
        except Exception as e:
            self.logger.error(f"Erro ao atualizar usuário no banco de dados: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def delete_user(self, user_id: int) -> bool:
        """
        Deleta usuário (ou desativa se for admin)

        Args:
            user_id: ID do usuário

        Returns:
            True se deletado, False caso contrário
        """
        try:
            # Verificar se é admin
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            if user["role"] == "admin":
                # Não permite deletar admin, apenas desativar
                return False

            from core.database.connector import DatabaseConnector
            with DatabaseConnector.get_connection(self.db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM frontend_users WHERE id = ?", (user_id,))
                conn.commit()

            return True

        except Exception as e:
            self.logger.error(f"Erro ao deletar usuário: {e}")
            return False

    def list_users(self) -> List[Dict[str, Any]]:
        """
        Lista todos os usuários

        Returns:
            Lista de usuários
        """
        try:
            import os
            if not os.path.exists(self.db_path):
                self.logger.error(f"Banco de dados não encontrado: {self.db_path}")
                return []

            with DatabaseConnector.get_connection(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Primeiro, buscar apenas frontend_users (sem JOIN)
                cursor.execute(
                    """
                    SELECT * FROM frontend_users
                    ORDER BY created_at DESC
                """
                )

                rows = cursor.fetchall()

                if not rows:
                    self.logger.warn("Nenhum usuário encontrado na tabela frontend_users")
                    return []

                users = []
                for row in rows:
                    user_dict = dict(row)

                    # Se tiver steam_id, buscar dados do player separadamente
                    if user_dict.get("steam_id"):
                        try:
                            cursor.execute(
                                """
                                SELECT player_name FROM players WHERE steam_id = ?
                            """,
                                (user_dict["steam_id"],),
                            )
                            player_row = cursor.fetchone()
                            if player_row:
                                user_dict["player_name"] = player_row["player_name"]
                                user_dict["player_id"] = user_dict[
                                    "steam_id"
                                ]  # Usar steam_id como player_id
                            else:
                                user_dict["player_name"] = None
                                user_dict["player_id"] = None
                        except Exception as player_error:
                            # Se a tabela players não existir ou houver erro, apenas não adicionar dados do player
                            self.logger.warn(
                                f"Erro ao buscar dados do player para steam_id {user_dict['steam_id']}: {player_error}"
                            )
                            user_dict["player_name"] = None
                            user_dict["player_id"] = None
                    else:
                        user_dict["player_name"] = None
                        user_dict["player_id"] = None

                    users.append(user_dict)

            self.logger.info(f"Listados {len(users)} usuários do banco")
            return users

        except Exception as e:
            self.logger.error(f"Erro ao listar usuários: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def user_exists(self, username: str) -> bool:
        """
        Verifica se usuário existe

        Args:
            username: Nome de usuário

        Returns:
            True se existe, False caso contrário
        """
        return self.get_user_by_username(username) is not None

    def search_players(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Busca players para vincular a moderadores

        Args:
            query: Termo de busca (nome ou steam_id)
            limit: Limite de resultados

        Returns:
            Lista de players encontrados
        """
        try:
            from core.database.connector import DatabaseConnector
            with DatabaseConnector.get_connection(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                search_term = f"%{query}%"
                cursor.execute(
                    """
                    SELECT steam_id, player_name
                    FROM players
                    WHERE player_name LIKE ? OR steam_id LIKE ?
                    ORDER BY player_name
                    LIMIT ?
                """,
                    (search_term, search_term, limit),
                )

                rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Erro ao buscar players: {e}")
            return []
