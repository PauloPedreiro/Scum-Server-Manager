"""
Gerenciador de arquivos .ini do servidor SCUM
Responsável por ler e escrever nos arquivos de configuração do servidor
"""

from pathlib import Path
from datetime import datetime
from typing import List, Set, Optional

from utils.logger import StructuredLogger

from .permission_types import (
    PERMISSION_FILE_MAPPING,
    FILE_FORMATS,
    format_steam_id_for_file,
    validate_steam_id,
)


class IniManager:
    """Gerenciador de arquivos .ini do servidor SCUM"""

    def __init__(self, config_directory: str):
        """
        Inicializar gerenciador de arquivos .ini

        Args:
            config_directory: Diretório onde estão os arquivos .ini
        """
        self.config_directory = Path(config_directory)
        self.logger = StructuredLogger()

        # Garantir que o diretório existe
        if not self.config_directory.exists():
            self.logger.warning(
                f"Diretório de configuração não existe: {config_directory}",
                {"directory": str(config_directory)},
            )
            self.config_directory.mkdir(parents=True, exist_ok=True)

    def get_ini_file_path(self, permission_type: str) -> Path:
        """
        Obter caminho completo do arquivo .ini

        Args:
            permission_type: Tipo de permissão

        Returns:
            Caminho completo do arquivo .ini
        """
        file_name = PERMISSION_FILE_MAPPING.get(permission_type)
        if not file_name:
            raise ValueError(f"Tipo de permissão inválido: {permission_type}")

        return self.config_directory / file_name

    def read_ini_file(self, file_path: Path) -> Set[str]:
        """
        Ler arquivo .ini e retornar conjunto de Steam IDs

        Args:
            file_path: Caminho do arquivo .ini

        Returns:
            Conjunto de Steam IDs encontrados no arquivo
        """
        steam_ids = set()

        if not file_path.exists():
            return steam_ids

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # Extrair Steam ID (remover sufixos como [setgodmode])
                    steam_id = line.split("[")[0].strip()
                    if validate_steam_id(steam_id):
                        steam_ids.add(steam_id)

        except Exception as e:
            self.logger.error(
                f"Erro ao ler arquivo .ini: {e}",
                {"file_path": str(file_path), "error": str(e)},
            )

        return steam_ids

    def add_to_ini(self, permission_type: str, steam_id: str) -> bool:
        """
        Adicionar Steam ID ao arquivo .ini

        Args:
            permission_type: Tipo de permissão
            steam_id: Steam ID do jogador

        Returns:
            True se sucesso, False caso contrário
        """
        if not validate_steam_id(steam_id):
            self.logger.warning(
                f"Steam ID inválido: {steam_id}", {"steam_id": steam_id}
            )
            return False

        file_path = self.get_ini_file_path(permission_type)
        steam_id_formatted = format_steam_id_for_file(steam_id, permission_type)

        try:
            # Verificar se Steam ID já existe no arquivo (usando read_ini_file para extrair IDs)
            existing_steam_ids = self.read_ini_file(file_path)
            if steam_id in existing_steam_ids:
                self.logger.debug(
                    f"Steam ID já existe no arquivo: {steam_id_formatted}",
                    {"file_path": str(file_path), "steam_id": steam_id},
                )
                return True

            # Ler linhas existentes (preservar comentários e formatação)
            existing_lines = []
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_lines = f.readlines()

            # Adicionar nova linha no final (remover última quebra de linha se necessário)
            if existing_lines and not existing_lines[-1].endswith("\n"):
                existing_lines[-1] = existing_lines[-1].rstrip() + "\n"

            existing_lines.append(steam_id_formatted + "\n")

            # Escrever arquivo
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(existing_lines)

            self.logger.info(
                f"Steam ID adicionado ao arquivo .ini: {steam_id_formatted}",
                {
                    "file_path": str(file_path),
                    "steam_id": steam_id,
                    "permission_type": permission_type,
                },
            )

            return True

        except Exception as e:
            self.logger.error(
                f"Erro ao adicionar Steam ID ao arquivo .ini: {e}",
                {
                    "file_path": str(file_path),
                    "steam_id": steam_id,
                    "permission_type": permission_type,
                    "error": str(e),
                },
            )
            return False

    def remove_from_ini(self, permission_type: str, steam_id: str) -> bool:
        """
        Remover Steam ID do arquivo .ini

        Args:
            permission_type: Tipo de permissão
            steam_id: Steam ID do jogador

        Returns:
            True se sucesso, False caso contrário
        """
        if not validate_steam_id(steam_id):
            self.logger.warning(
                f"Steam ID inválido: {steam_id}", {"steam_id": steam_id}
            )
            return False

        file_path = self.get_ini_file_path(permission_type)
        steam_id_formatted = format_steam_id_for_file(steam_id, permission_type)

        if not file_path.exists():
            self.logger.debug(
                f"Arquivo não existe: {file_path}", {"file_path": str(file_path)}
            )
            return True

        try:
            # Ler linhas existentes
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Filtrar linha a remover (verificar tanto o formato completo quanto apenas o Steam ID)
            original_count = len(lines)
            lines = [
                line
                for line in lines
                if line.strip() != steam_id_formatted
                and line.strip().split("[")[0].strip() != steam_id
            ]

            # Se não houve mudança, Steam ID não estava no arquivo
            if len(lines) == original_count:
                self.logger.debug(
                    f"Steam ID não encontrado no arquivo: {steam_id_formatted}",
                    {"file_path": str(file_path), "steam_id": steam_id},
                )
                return True

            # Escrever arquivo
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            self.logger.info(
                f"Steam ID removido do arquivo .ini: {steam_id_formatted}",
                {
                    "file_path": str(file_path),
                    "steam_id": steam_id,
                    "permission_type": permission_type,
                },
            )

            return True

        except Exception as e:
            self.logger.error(
                f"Erro ao remover Steam ID do arquivo .ini: {e}",
                {
                    "file_path": str(file_path),
                    "steam_id": steam_id,
                    "permission_type": permission_type,
                    "error": str(e),
                },
            )
            return False

    def sync_ini_file(self, permission_type: str, steam_ids: List[str]) -> dict:
        """
        Sincronizar arquivo .ini com lista de Steam IDs

        Args:
            permission_type: Tipo de permissão
            steam_ids: Lista de Steam IDs que devem estar no arquivo

        Returns:
            Dicionário com estatísticas da sincronização
        """
        file_path = self.get_ini_file_path(permission_type)
        steam_ids_set = set(steam_ids)

        # Ler Steam IDs atuais no arquivo
        current_steam_ids = self.read_ini_file(file_path)

        # Calcular diferenças
        to_add = steam_ids_set - current_steam_ids
        to_remove = current_steam_ids - steam_ids_set

        stats = {
            "permission_type": permission_type,
            "file_path": str(file_path),
            "expected_count": len(steam_ids_set),
            "current_count": len(current_steam_ids),
            "added": 0,
            "removed": 0,
            "errors": [],
        }

        # Adicionar faltantes
        for steam_id in to_add:
            if self.add_to_ini(permission_type, steam_id):
                stats["added"] += 1
            else:
                stats["errors"].append(f"Erro ao adicionar {steam_id}")

        # Remover extras
        for steam_id in to_remove:
            if self.remove_from_ini(permission_type, steam_id):
                stats["removed"] += 1
            else:
                stats["errors"].append(f"Erro ao remover {steam_id}")

        return stats

    def sync_all_ini_files(self, permissions_data: dict) -> dict:
        """
        Sincronizar todos os arquivos .ini com dados do banco

        Args:
            permissions_data: Dicionário com permissões por tipo
                Exemplo: {
                    'admin': ['76561198040636105', ...],
                    'banned': [...],
                    ...
                }

        Returns:
            Dicionário com estatísticas de sincronização
        """
        results = {
            "sync_at": datetime.now().isoformat(),
            "files_synced": 0,
            "total_added": 0,
            "total_removed": 0,
            "errors": [],
            "file_stats": [],
        }

        for permission_type, steam_ids in permissions_data.items():
            if permission_type not in PERMISSION_FILE_MAPPING:
                continue
            try:
                stats = self.sync_ini_file(permission_type, steam_ids)
                results["file_stats"].append(stats)
                results["files_synced"] += 1
                results["total_added"] += stats["added"]
                results["total_removed"] += stats["removed"]
                results["errors"].extend(stats["errors"])
            except Exception as e:
                error_msg = f"Erro ao sincronizar {permission_type}: {e}"
                results["errors"].append(error_msg)
                self.logger.error(
                    error_msg, {"permission_type": permission_type, "error": str(e)}
                )

        return results
