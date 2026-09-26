"""
Gerenciador de config.json
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import shutil
from utils.logger import StructuredLogger


class ConfigManager:
    """Gerenciador de config.json com backup automático"""

    def __init__(self, config_path: str):
        """
        Inicializar gerenciador

        Args:
            config_path: Caminho completo para o config.json
        """
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        self.logger = StructuredLogger()
        self.max_backups = 10

    def load(self) -> Dict[str, Any]:
        """
        Carregar configuração completa

        Returns:
            Dicionário com toda a configuração
        """
        if not self.config_path.exists():
            self.logger.warning(
                f"Arquivo config.json não encontrado: {self.config_path}"
            )
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # Garantir chaves padrão para squad_tk_jail
            if "squad_tk_jail" not in config:
                config["squad_tk_jail"] = {
                    "enabled": False,
                    "jail_coordinates": "-271417.281 314246.875 84056.023",
                    "jail_radius_meters": 20.0,
                    "jail_duration_minutes": 30,
                    "warning_color": "2",
                    "use_colors": True,
                    "announcement_message": "{killer} matou o companheiro de squad {victim} e foi enviado para a prisão por {minutes} minutos!",
                    "escape_message": "{player}, você tentou escapar! Retornando para a cela.",
                    "release_message": "{player} cumpriu sua pena e foi libertado!"
                }
                try:
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                except Exception as save_err:
                    self.logger.warning(f"Erro ao gravar squad_tk_jail padrão no config.json: {save_err}")

            return config
        except Exception as e:
            self.logger.error(f"Erro ao carregar config.json: {e}")
            raise

    def get_section(self, section: str) -> Optional[Dict[str, Any]]:
        """
        Obter uma seção específica (suporta caminhos aninhados com ponto)

        Args:
            section: Nome da seção (ex: "api" ou "paths.scum_server")

        Returns:
            Dicionário com a seção ou None se não existir
        """
        config = self.load()

        # Suportar caminhos aninhados (ex: "paths.scum_server")
        if "." in section:
            parts = section.split(".")
            current = config
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current if isinstance(current, dict) else None

        return config.get(section)

    def get_sections(self, include_nested: bool = True) -> List[str]:
        """
        Listar todas as seções disponíveis (inclui subseções aninhadas)

        Args:
            include_nested: Se True, inclui subseções como "paths.scum_server"

        Returns:
            Lista com nomes das seções
        """
        config = self.load()
        sections = list(config.keys())

        if include_nested:
            # Adicionar subseções de objetos aninhados
            for key, value in config.items():
                if isinstance(value, dict):
                    for subkey in value.keys():
                        sections.append(f"{key}.{subkey}")

        return sections

    def update_section(
        self, section: str, updates: Dict[str, Any], create_backup: bool = True
    ) -> bool:
        """
        Atualizar uma seção específica (suporta caminhos aninhados com ponto)

        Args:
            section: Nome da seção (ex: "api" ou "paths.scum_server")
            updates: Dicionário com campos a atualizar
            create_backup: Se deve criar backup antes de atualizar

        Returns:
            True se atualizado com sucesso
        """
        try:
            # Carregar configuração atual
            config = self.load()

            # Criar backup se solicitado
            if create_backup:
                self._create_backup()

            # Suportar caminhos aninhados (ex: "paths.scum_server")
            if "." in section:
                parts = section.split(".")
                # Navegar até a seção aninhada
                current = config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                # Criar seção final se não existir
                final_key = parts[-1]
                if final_key not in current:
                    current[final_key] = {}

                # Mesclar atualizações
                self._deep_update(current[final_key], updates)
            else:
                # Seção de primeiro nível
                if section not in config:
                    config[section] = {}

                # Mesclar atualizações (suporta objetos aninhados)
                self._deep_update(config[section], updates)

            # Salvar
            self._save(config)

            self.logger.info(f"Seção '{section}' atualizada com sucesso")
            return True

        except Exception as e:
            self.logger.error(f"Erro ao atualizar seção '{section}': {e}")
            raise

    def update_sections(
        self, sections: Dict[str, Dict[str, Any]], create_backup: bool = True
    ) -> List[str]:
        """
        Atualizar múltiplas seções

        Args:
            sections: Dicionário com seções a atualizar {section_name: {fields}}
            create_backup: Se deve criar backup antes de atualizar

        Returns:
            Lista com nomes das seções atualizadas
        """
        try:
            # Carregar configuração atual
            config = self.load()

            # Criar backup se solicitado
            if create_backup:
                self._create_backup()

            updated_sections = []

            # Atualizar cada seção
            for section, updates in sections.items():
                if section not in config:
                    config[section] = {}

                self._deep_update(config[section], updates)
                updated_sections.append(section)

            # Salvar
            self._save(config)

            self.logger.info(f"Seções atualizadas: {', '.join(updated_sections)}")
            return updated_sections

        except Exception as e:
            self.logger.error(f"Erro ao atualizar seções: {e}")
            raise

    def replace_all(
        self, new_config: Dict[str, Any], create_backup: bool = True
    ) -> bool:
        """
        Substituir configuração completa

        Args:
            new_config: Nova configuração completa
            create_backup: Se deve criar backup antes de substituir

        Returns:
            True se substituído com sucesso
        """
        try:
            # Criar backup se solicitado
            if create_backup:
                self._create_backup()

            # Salvar nova configuração
            self._save(new_config)

            self.logger.info("Configuração completa substituída com sucesso")
            return True

        except Exception as e:
            self.logger.error(f"Erro ao substituir configuração: {e}")
            raise

    def _deep_update(self, base: Dict[str, Any], updates: Dict[str, Any]) -> None:
        """
        Atualizar dicionário recursivamente (deep merge)

        Args:
            base: Dicionário base
            updates: Dicionário com atualizações
        """
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                # Se ambos são dicionários, fazer merge recursivo
                self._deep_update(base[key], value)
            else:
                # Caso contrário, substituir
                base[key] = value

    def _encrypt_sensitive_fields(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Criptografa campos sensíveis automaticamente antes de salvar

        Args:
            config: Dicionário com configuração

        Returns:
            Configuração com campos sensíveis criptografados
        """
        try:
            from core.security.credential_encryption import (
                encrypt_credential,
                get_credential_encryption,
            )

            # Criar cópia para não modificar o original
            encrypted_config = json.loads(json.dumps(config))

            # Lista de campos sensíveis que devem ser criptografados
            # Formato: (caminho_seção, campo)
            # Nota: steam.api_key removido - não é mais usado (usamos Steam Community XML API pública)
            sensitive_fields = [
                ("licensing", "gestao_api_key"),
                ("licensing", "api_key"),
                ("auth", "jwt_secret"),
            ]

            # Criptografar campos sensíveis
            for section, field in sensitive_fields:
                if section in encrypted_config and field in encrypted_config[section]:
                    value = encrypted_config[section][field]
                    # Só criptografar se não estiver já criptografado e não for vazio
                    if (
                        value
                        and isinstance(value, str)
                        and not value.startswith("ENCRYPTED:")
                    ):
                        try:
                            encrypted = encrypt_credential(value, logger=self.logger)
                            encrypted_config[section][field] = encrypted
                            self.logger.debug(
                                f"Campo sensível '{section}.{field}' criptografado automaticamente"
                            )
                        except Exception as e:
                            # Se falhar, manter valor original (não quebrar sistema)
                            self.logger.warning(
                                f"Erro ao criptografar '{section}.{field}': {e}"
                            )

            return encrypted_config

        except ImportError:
            # Se módulo de criptografia não estiver disponível, retornar original
            self.logger.warning(
                "Módulo de criptografia não disponível - campos sensíveis não serão criptografados"
            )
            return config
        except Exception as e:
            # Em caso de erro, retornar original (não quebrar sistema)
            self.logger.warning(f"Erro ao criptografar campos sensíveis: {e}")
            return config

    def _save(self, config: Dict[str, Any]) -> None:
        """
        Salvar configuração no arquivo

        Args:
            config: Dicionário com configuração
        """
        # Criptografar campos sensíveis automaticamente
        config = self._encrypt_sensitive_fields(config)

        # Garantir que o diretório existe
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Salvar com formatação
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _create_backup(self) -> str:
        """
        Criar backup do config.json

        Returns:
            Caminho do arquivo de backup criado
        """
        if not self.config_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"config.backup.{timestamp}.json"
        backup_path = self.config_dir / backup_filename

        try:
            shutil.copy2(self.config_path, backup_path)
            self.logger.info(f"Backup criado: {backup_filename}")

            # Limpar backups antigos
            self._cleanup_old_backups()

            return str(backup_path)

        except Exception as e:
            self.logger.error(f"Erro ao criar backup: {e}")
            raise

    def _cleanup_old_backups(self) -> None:
        """Limpar backups antigos, mantendo apenas os últimos N"""
        try:
            # Listar todos os backups
            backups = sorted(
                self.config_dir.glob("config.backup.*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            # Remover backups excedentes
            if len(backups) > self.max_backups:
                for backup in backups[self.max_backups :]:
                    backup.unlink()
                    self.logger.debug(f"Backup antigo removido: {backup.name}")

        except Exception as e:
            self.logger.warning(f"Erro ao limpar backups antigos: {e}")

    def list_backups(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Listar backups disponíveis

        Args:
            limit: Número máximo de backups a retornar

        Returns:
            Lista de dicionários com informações dos backups
        """
        backups = []

        try:
            backup_files = sorted(
                self.config_dir.glob("config.backup.*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:limit]

            for backup_file in backup_files:
                stat = backup_file.stat()
                backups.append(
                    {
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "size": stat.st_size,
                    }
                )

        except Exception as e:
            self.logger.error(f"Erro ao listar backups: {e}")

        return backups

    def restore_backup(self, backup_filename: str, create_backup: bool = True) -> bool:
        """
        Restaurar configuração de um backup

        Args:
            backup_filename: Nome do arquivo de backup (ex: "config.backup.20251202_153045.json")
            create_backup: Se deve criar backup da configuração atual antes de restaurar

        Returns:
            True se restaurado com sucesso
        """
        backup_path = self.config_dir / backup_filename

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup não encontrado: {backup_filename}")

        try:
            # Criar backup da configuração atual se solicitado
            if create_backup and self.config_path.exists():
                self._create_backup()

            # Restaurar backup
            shutil.copy2(backup_path, self.config_path)

            self.logger.info(f"Configuração restaurada do backup: {backup_filename}")
            return True

        except Exception as e:
            self.logger.error(f"Erro ao restaurar backup: {e}")
            raise
