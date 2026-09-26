"""
Gerenciador de permissões de jogadores
Gerencia permissões no banco de dados e sincronização com arquivos .ini
"""
from core.database.connector import DatabaseConnector

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from utils.logger import StructuredLogger

from .ini_manager import IniManager
from .permission_types import (
    PERMISSION_TYPES,
    PERMISSION_FILE_MAPPING,
    validate_permission_type,
    validate_steam_id,
)


class PermissionManager:
    """Gerenciador de permissões de jogadores"""

    def __init__(self, db_path: str, ini_manager: IniManager):
        """
        Inicializar gerenciador de permissões

        Args:
            db_path: Caminho do banco de dados
            ini_manager: Instância do IniManager
        """
        self.db_path = db_path
        self.ini_manager = ini_manager
        self.logger = StructuredLogger()

    def get_player_by_steam_id(self, steam_id: str) -> Optional[Dict[str, Any]]:
        """
        Obter jogador por Steam ID

        Args:
            steam_id: Steam ID do jogador

        Returns:
            Dicionário com dados do jogador ou None se não encontrado
        """
        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=30.0, write_mode=True) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT steam_id, player_name, player_id, first_seen, last_seen,
                           total_sessions, total_playtime, is_new_player, 
                           notification_sent, permissao, created_at
                    FROM players 
                    WHERE steam_id = ?
                """,
                    (steam_id,),
                )

                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None

        except Exception as e:
            self.logger.error(
                f"Erro ao obter jogador: {e}", {"steam_id": steam_id, "error": str(e)}
            )
            return None

    def get_player_permissions(
        self, steam_id: str, include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Obter permissões de um jogador (toggle - apenas registros únicos)

        Args:
            steam_id: Steam ID do jogador
            include_inactive: Incluir permissões inativas

        Returns:
            Lista de permissões do jogador
        """
        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=30.0, write_mode=True) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = """
                    SELECT id, steam_id, permission_type, is_active, 
                           granted_by, granted_at, revoked_by, revoked_at, notes
                    FROM player_permissions 
                    WHERE steam_id = ?
                """

                if not include_inactive:
                    query += " AND is_active = 1"

                query += " ORDER BY permission_type"

                cursor.execute(query, (steam_id,))
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(
                f"Erro ao obter permissões do jogador: {e}",
                {"steam_id": steam_id, "error": str(e)},
            )
            return []

    def get_active_permissions_by_type(self, permission_type: str) -> List[str]:
        """
        Obter lista de Steam IDs com permissão específica ativa

        Args:
            permission_type: Tipo de permissão

        Returns:
            Lista de Steam IDs
        """
        if not validate_permission_type(permission_type):
            self.logger.warning(
                f"Tipo de permissão inválido: {permission_type}",
                {"permission_type": permission_type},
            )
            return []

        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT steam_id 
                    FROM player_permissions 
                    WHERE permission_type = ? AND is_active = 1
                """,
                    (permission_type,),
                )

                return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            self.logger.error(
                f"Erro ao obter permissões por tipo: {e}",
                {"permission_type": permission_type, "error": str(e)},
            )
            return []

    def get_all_active_permissions(self) -> Dict[str, List[str]]:
        """
        Obter todas as permissões ativas organizadas por tipo

        Returns:
            Dicionário com permissões por tipo
        """
        permissions_data = {}

        for permission_type in PERMISSION_TYPES:
            permissions_data[permission_type] = self.get_active_permissions_by_type(
                permission_type
            )

        return permissions_data

    def activate_permission(
        self,
        steam_id: str,
        permission_type: str,
        granted_by: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ativar permissão para um jogador (toggle - cria ou ativa existente)

        Args:
            steam_id: Steam ID do jogador
            permission_type: Tipo de permissão
            granted_by: Usuário que concedeu a permissão
            notes: Observações opcionais

        Returns:
            Dicionário com resultado da operação
        """
        # Validar Steam ID
        if not validate_steam_id(steam_id):
            return {
                "success": False,
                "message": f"Steam ID inválido: {steam_id}",
                "error": "invalid_steam_id",
            }

        # Validar tipo de permissão
        if not validate_permission_type(permission_type):
            return {
                "success": False,
                "message": f"Tipo de permissão inválido: {permission_type}",
                "error": "invalid_permission_type",
            }

        # Verificar se jogador existe
        player = self.get_player_by_steam_id(steam_id)
        if not player:
            return {
                "success": False,
                "message": f"Jogador não encontrado: {steam_id}",
                "error": "player_not_found",
            }

        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()

                # Verificar se já existe um registro para este steam_id + permission_type
                cursor.execute(
                    """
                    SELECT id, is_active FROM player_permissions 
                    WHERE steam_id = ? AND permission_type = ?
                """,
                    (steam_id, permission_type),
                )

                existing = cursor.fetchone()

                if existing:
                    permission_id, is_active = existing

                    if is_active:
                        ini_file_path = None
                        if PERMISSION_FILE_MAPPING.get(permission_type):
                            ini_file_path = str(
                                self.ini_manager.get_ini_file_path(permission_type)
                            )

                        return {
                            "success": True,
                            "message": f"Permissão {permission_type} já está ativa para este jogador",
                            "data": {
                                "permission_id": permission_id,
                                "steam_id": steam_id,
                                "player_name": player.get("player_name"),
                                "permission_type": permission_type,
                                "is_active": True,
                                "granted_by": None,
                                "granted_at": None,
                                "notes": None,
                                "ini_file_updated": None,
                                "ini_file_path": ini_file_path,
                            },
                        }
                    else:
                        # Ativar permissão existente (toggle)
                        cursor.execute(
                            """
                            UPDATE player_permissions 
                            SET is_active = 1, granted_by = ?, granted_at = CURRENT_TIMESTAMP, 
                                revoked_by = NULL, revoked_at = NULL, notes = ?
                            WHERE id = ?
                        """,
                            (granted_by, notes, permission_id),
                        )

                        action = "reativada"
                else:
                    # Criar nova permissão
                    cursor.execute(
                        """
                        INSERT INTO player_permissions 
                        (steam_id, permission_type, is_active, granted_by, notes, granted_at)
                        VALUES (?, ?, 1, ?, ?, CURRENT_TIMESTAMP)
                    """,
                        (steam_id, permission_type, granted_by, notes),
                    )

                    permission_id = cursor.lastrowid
                    action = "ativada"

                conn.commit()

                ini_success = True
                ini_file_path = None
                if PERMISSION_FILE_MAPPING.get(permission_type):
                    # Adicionar no arquivo .ini (somente para permissões mapeadas)
                    ini_success = self.ini_manager.add_to_ini(permission_type, steam_id)
                    ini_file_path = str(self.ini_manager.get_ini_file_path(permission_type))

                    if not ini_success:
                        self.logger.warning(
                            f"Permissão {action} no banco mas erro ao atualizar .ini: {steam_id}",
                            {"steam_id": steam_id, "permission_type": permission_type},
                        )

                self.logger.info(
                    f"Permissão {action}: {permission_type} para {steam_id}",
                    {
                        "steam_id": steam_id,
                        "permission_type": permission_type,
                        "granted_by": granted_by,
                        "ini_updated": ini_success,
                        "action": action,
                    },
                )

                return {
                    "success": True,
                    "message": f"Permissão {permission_type} {action} com sucesso",
                    "data": {
                        "permission_id": permission_id,
                        "steam_id": steam_id,
                        "player_name": player.get("player_name"),
                        "permission_type": permission_type,
                        "is_active": True,
                        "granted_by": granted_by,
                        "granted_at": datetime.now().isoformat(),
                        "notes": notes,
                        "ini_file_updated": ini_success if PERMISSION_FILE_MAPPING.get(permission_type) else None,
                        "ini_file_path": ini_file_path,
                    },
                }

        except sqlite3.IntegrityError as e:
            self.logger.error(
                f"Erro de integridade ao ativar permissão: {e}",
                {
                    "steam_id": steam_id,
                    "permission_type": permission_type,
                    "error": str(e),
                },
            )
            return {
                "success": False,
                "message": f"Erro ao ativar permissão: {e}",
                "error": "database_error",
            }

        except Exception as e:
            self.logger.error(
                f"Erro ao ativar permissão: {e}",
                {
                    "steam_id": steam_id,
                    "permission_type": permission_type,
                    "error": str(e),
                },
            )
            return {
                "success": False,
                "message": f"Erro ao ativar permissão: {e}",
                "error": "unknown_error",
            }

    def deactivate_permission(
        self,
        steam_id: str,
        permission_type: str,
        revoked_by: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Desativar permissão de um jogador (toggle - desativa existente)

        Args:
            steam_id: Steam ID do jogador
            permission_type: Tipo de permissão
            revoked_by: Usuário que revogou a permissão
            notes: Observações opcionais

        Returns:
            Dicionário com resultado da operação
        """
        # Validar Steam ID
        if not validate_steam_id(steam_id):
            return {
                "success": False,
                "message": f"Steam ID inválido: {steam_id}",
                "error": "invalid_steam_id",
            }

        # Validar tipo de permissão
        if not validate_permission_type(permission_type):
            return {
                "success": False,
                "message": f"Tipo de permissão inválido: {permission_type}",
                "error": "invalid_permission_type",
            }

        # Verificar se jogador existe
        player = self.get_player_by_steam_id(steam_id)
        if not player:
            return {
                "success": False,
                "message": f"Jogador não encontrado: {steam_id}",
                "error": "player_not_found",
            }

        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()

                # Verificar se permissão existe e está ativa
                cursor.execute(
                    """
                    SELECT id, is_active FROM player_permissions 
                    WHERE steam_id = ? AND permission_type = ?
                """,
                    (steam_id, permission_type),
                )

                existing = cursor.fetchone()

                if not existing:
                    return {
                        "success": False,
                        "message": f"Permissão {permission_type} não existe para este jogador",
                        "error": "permission_not_found",
                    }

                permission_id, is_active = existing

                if not is_active:
                    ini_file_path = None
                    if PERMISSION_FILE_MAPPING.get(permission_type):
                        ini_file_path = str(
                            self.ini_manager.get_ini_file_path(permission_type)
                        )

                    return {
                        "success": True,
                        "message": f"Permissão {permission_type} já está inativa para este jogador",
                        "data": {
                            "permission_id": permission_id,
                            "steam_id": steam_id,
                            "player_name": player.get("player_name"),
                            "permission_type": permission_type,
                            "is_active": False,
                            "revoked_by": None,
                            "revoked_at": None,
                            "notes": None,
                            "ini_file_updated": None,
                            "ini_file_path": ini_file_path,
                        },
                    }

                # Desativar permissão (toggle)
                cursor.execute(
                    """
                    UPDATE player_permissions 
                    SET is_active = 0, revoked_by = ?, revoked_at = CURRENT_TIMESTAMP, notes = ?
                    WHERE id = ?
                """,
                    (revoked_by, notes, permission_id),
                )

                conn.commit()

                ini_success = True
                ini_file_path = None
                if PERMISSION_FILE_MAPPING.get(permission_type):
                    # Remover do arquivo .ini (somente para permissões mapeadas)
                    ini_success = self.ini_manager.remove_from_ini(
                        permission_type, steam_id
                    )
                    ini_file_path = str(self.ini_manager.get_ini_file_path(permission_type))

                if not ini_success:
                    self.logger.warning(
                        f"Permissão desativada no banco mas erro ao atualizar .ini: {steam_id}",
                        {"steam_id": steam_id, "permission_type": permission_type},
                    )

                self.logger.info(
                    f"Permissão desativada: {permission_type} para {steam_id}",
                    {
                        "steam_id": steam_id,
                        "permission_type": permission_type,
                        "revoked_by": revoked_by,
                        "ini_updated": ini_success,
                    },
                )

                return {
                    "success": True,
                    "message": f"Permissão {permission_type} desativada com sucesso",
                    "data": {
                        "permission_id": permission_id,
                        "steam_id": steam_id,
                        "player_name": player.get("player_name"),
                        "permission_type": permission_type,
                        "is_active": False,
                        "revoked_by": revoked_by,
                        "revoked_at": datetime.now().isoformat(),
                        "notes": notes,
                        "ini_file_updated": ini_success if PERMISSION_FILE_MAPPING.get(permission_type) else None,
                        "ini_file_path": ini_file_path,
                    },
                }

        except Exception as e:
            self.logger.error(
                f"Erro ao desativar permissão: {e}",
                {
                    "steam_id": steam_id,
                    "permission_type": permission_type,
                    "error": str(e),
                },
            )
            return {
                "success": False,
                "message": f"Erro ao desativar permissão: {e}",
                "error": "unknown_error",
            }

    def sync_all_ini_files(self) -> Dict[str, Any]:
        """
        Sincronizar todos os arquivos .ini com o banco de dados

        Returns:
            Dicionário com estatísticas de sincronização
        """
        try:
            # Obter todas as permissões ativas
            permissions_data = self.get_all_active_permissions()

            # Sincronizar arquivos
            sync_results = self.ini_manager.sync_all_ini_files(permissions_data)

            self.logger.info("Sincronização de arquivos .ini concluída", sync_results)

            return {
                "success": True,
                "message": "Arquivos .ini sincronizados com sucesso",
                "data": sync_results,
            }

        except Exception as e:
            self.logger.error(
                f"Erro ao sincronizar arquivos .ini: {e}", {"error": str(e)}
            )
            return {
                "success": False,
                "message": f"Erro ao sincronizar arquivos .ini: {e}",
                "error": "sync_error",
            }

    def get_permission_stats(self) -> Dict[str, Any]:
        """
        Obter estatísticas de permissões (toggle - registros únicos)

        Returns:
            Dicionário com estatísticas
        """
        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()

                # Total de permissões ativas por tipo
                cursor.execute(
                    """
                    SELECT permission_type, COUNT(*) as count
                    FROM player_permissions
                    WHERE is_active = 1
                    GROUP BY permission_type
                """
                )

                active_by_type = {row[0]: row[1] for row in cursor.fetchall()}

                # Total de permissões inativas por tipo
                cursor.execute(
                    """
                    SELECT permission_type, COUNT(*) as count
                    FROM player_permissions
                    WHERE is_active = 0
                    GROUP BY permission_type
                """
                )

                inactive_by_type = {row[0]: row[1] for row in cursor.fetchall()}

                # Total geral
                cursor.execute(
                    "SELECT COUNT(*) FROM player_permissions WHERE is_active = 1"
                )
                total_active = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM player_permissions WHERE is_active = 0"
                )
                total_inactive = cursor.fetchone()[0]

                # Total de registros únicos (steam_id + permission_type)
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT steam_id || '|' || permission_type) 
                    FROM player_permissions
                """
                )
                total_unique_permissions = cursor.fetchone()[0]

                return {
                    "total_permissions": total_unique_permissions,
                    "active_permissions": total_active,
                    "inactive_permissions": total_inactive,
                    "permissions_by_type": active_by_type,
                    "permissions_by_status": {
                        "active": total_active,
                        "inactive": total_inactive,
                    },
                    "recent_activity": {
                        "last_24h": 0,  # Pode ser implementado se necessário
                        "last_7d": 0,
                        "last_30d": 0,
                    },
                }

        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas: {e}", {"error": str(e)})
            return {
                "total_permissions": 0,
                "active_permissions": 0,
                "inactive_permissions": 0,
                "permissions_by_type": {},
                "permissions_by_status": {"active": 0, "inactive": 0},
                "recent_activity": {"last_24h": 0, "last_7d": 0, "last_30d": 0},
            }
