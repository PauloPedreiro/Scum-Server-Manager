"""
Gerenciador simples do ServerSettings.ini
"""

import configparser
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import shutil
from utils.logger import StructuredLogger


class ServerSettingsManager:
    """Gerenciador simples do ServerSettings.ini"""

    def __init__(self, config_directory: str, logger: Optional[StructuredLogger] = None):
        """
        Inicializar gerenciador

        Args:
            config_directory: Diretório onde está o ServerSettings.ini
        """
        self.config_directory = Path(config_directory)
        self.settings_file = self.config_directory / "ServerSettings.ini"
        self.parser = configparser.ConfigParser(strict=False)
        self.parser.optionxform = str  # Preservar case das chaves
        self.logger = logger or StructuredLogger()
        self._schema_version: Optional[int] = None
        self._schema: Optional[Dict[str, Any]] = None

        try:
            if self.settings_file.exists():
                self.parser.read(self.settings_file, encoding="utf-8")
            self._ensure_schema_loaded()
        except Exception as e:
            try:
                self.logger.warn(f"Erro ao inicializar ServerSettingsManager schema: {e}")
            except Exception:
                pass

    def _get_app_data_dir(self) -> Path:
        exe_dir = Path(sys.executable).parent
        exe_data_dir = exe_dir / "data"
        exe_config_json = exe_data_dir / "config.json"
        if exe_config_json.exists():
            return exe_data_dir

        if exe_data_dir.exists():
            return exe_data_dir

        cwd_data_dir = Path.cwd() / "data"
        if cwd_data_dir.exists():
            return cwd_data_dir

        return Path(__file__).resolve().parents[2] / "data"

    def _load_schema_for_version(self, settings_version: Optional[int]) -> Optional[Dict[str, Any]]:
        data_dir = self._get_app_data_dir()
        models_dir = data_dir / "server_settings_models"

        try:
            models_dir.mkdir(parents=True, exist_ok=True)
            try:
                self.logger.info(f"Server settings schema dir: {models_dir}")
            except Exception:
                pass
        except Exception:
            pass

        version_file_to_create: Optional[Path] = None
        if settings_version is not None and settings_version > 0:
            version_file_to_create = (
                models_dir / f"serversettings_schema_v{settings_version}.override.json"
            )

        found_schema: Optional[Dict[str, Any]] = None

        if settings_version is not None:
            for v in range(settings_version, 0, -1):
                candidate = models_dir / f"serversettings_schema_v{v}.override.json"
                if candidate.exists():
                    try:
                        with open(candidate, "r", encoding="utf-8") as f:
                            schema = json.load(f)
                        if isinstance(schema, dict):
                            found_schema = schema
                            break
                    except Exception:
                        found_schema = None
                        break

        if version_file_to_create is not None and not version_file_to_create.exists():
            try:
                with open(version_file_to_create, "w", encoding="utf-8") as f:
                    f.write("{}\n")
                try:
                    self.logger.info(
                        f"Server settings schema file created: {version_file_to_create}"
                    )
                except Exception:
                    pass
            except Exception:
                pass

        if found_schema is not None:
            return found_schema

        generic = models_dir / "serversettings_schema.override.json"
        if generic.exists():
            try:
                with open(generic, "r", encoding="utf-8") as f:
                    schema = json.load(f)
                return schema if isinstance(schema, dict) else None
            except Exception:
                return None

        if version_file_to_create is not None:
            return {}

        return None

    def _ensure_schema_loaded(self):
        settings_version = self._parse_settings_version()
        if settings_version == self._schema_version and self._schema is not None:
            return
        self._schema_version = settings_version
        self._schema = self._load_schema_for_version(settings_version)

    def _schema_declares_bool(self, section: str, key: str) -> bool:
        self._ensure_schema_loaded()
        if not isinstance(self._schema, dict):
            return False

        section_map = self._schema.get(section)
        if not isinstance(section_map, dict):
            return False

        entry = section_map.get(key)
        if isinstance(entry, str):
            return entry.strip().lower() == "bool"
        if isinstance(entry, dict):
            t = entry.get("type")
            if isinstance(t, str) and t.strip().lower() == "bool":
                return True
        return False

    def _parse_settings_version(self) -> Optional[int]:
        try:
            if not self.parser.has_section("General"):
                return None
            raw = self.parser.get("General", "scum.SettingsVersion", fallback=None)
            if raw is None:
                return None
            return int(str(raw).strip())
        except Exception:
            return None

    def _is_true_false_string(self, value: Optional[str]) -> bool:
        if value is None:
            return False
        v = str(value).strip().lower()
        return v in {"true", "false"}

    def _looks_like_boolean_key(self, key: str) -> bool:
        k = (key or "").strip()
        if not k:
            return False
        last = k.split(".")[-1]
        last_l = last.lower()
        if last_l.endswith("enabled"):
            return True
        prefixes = (
            "allow",
            "enable",
            "disable",
            "should",
            "can",
            "has",
            "hide",
            "log",
        )
        return last_l.startswith(prefixes)

    def _coerce_to_true_false(self, value: Any) -> Optional[str]:
        if isinstance(value, bool):
            return "True" if value else "False"
        if isinstance(value, int) and value in (0, 1):
            return "True" if value == 1 else "False"
        if isinstance(value, str):
            v = value.strip().lower()
            if v in {"true", "1", "yes", "on"}:
                return "True"
            if v in {"false", "0", "no", "off"}:
                return "False"
        return None

    def _normalize_value_for_write(self, section: str, key: str, value: Any) -> str:
        existing_value: Optional[str] = None
        try:
            if self.parser.has_section(section):
                existing_value = self.parser.get(section, key, fallback=None)
        except Exception:
            existing_value = None

        if self._schema_declares_bool(section, key):
            coerced = self._coerce_to_true_false(value)
            return coerced if coerced is not None else str(value)

        if self._is_true_false_string(existing_value):
            coerced = self._coerce_to_true_false(value)
            return coerced if coerced is not None else str(value)

        settings_version = self._parse_settings_version()
        if settings_version is not None and settings_version >= 4 and self._looks_like_boolean_key(key):
            coerced = self._coerce_to_true_false(value)
            if coerced is not None:
                return coerced

        return str(value)

    def load_all(self) -> Dict[str, Dict[str, str]]:
        """
        Carregar todas as configurações preservando a ordem original

        Returns:
            Dicionário com todas as seções e seus campos (preservando ordem)
        """
        if not self.settings_file.exists():
            self.logger.warning(
                f"Arquivo ServerSettings.ini não encontrado: {self.settings_file}"
            )
            return {}

        try:
            # Ler arquivo linha por linha para preservar ordem
            result = {}
            current_section = None
            current_section_data = {}

            with open(self.settings_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    # Ignorar linhas vazias e comentários
                    if not line or line.startswith(";") or line.startswith("#"):
                        continue

                    # Verificar se é uma seção [SectionName]
                    if line.startswith("[") and line.endswith("]"):
                        # Salvar seção anterior se existir
                        if current_section is not None:
                            result[current_section] = current_section_data

                        # Nova seção
                        current_section = line[1:-1]  # Remove [ e ]
                        current_section_data = {}
                    elif "=" in line and current_section is not None:
                        # É uma chave=valor
                        key, value = line.split("=", 1)  # Split apenas no primeiro =
                        key = key.strip()
                        value = value.strip()
                        # Preservar ordem usando dict (Python 3.7+ mantém ordem de inserção)
                        current_section_data[key] = value

            # Salvar última seção
            if current_section is not None:
                result[current_section] = current_section_data

            return result
        except Exception as e:
            self.logger.error(f"Erro ao carregar ServerSettings.ini: {e}")
            raise

    def get_section(self, section: str) -> Dict[str, str]:
        """
        Obter seção específica preservando a ordem original

        Args:
            section: Nome da seção (ex: 'General', 'World')

        Returns:
            Dicionário com campos da seção (preservando ordem)
        """
        if not self.settings_file.exists():
            return {}

        try:
            # Ler arquivo linha por linha para preservar ordem
            section_data = {}
            in_target_section = False

            with open(self.settings_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    # Ignorar linhas vazias e comentários
                    if not line or line.startswith(";") or line.startswith("#"):
                        continue

                    # Verificar se é uma seção [SectionName]
                    if line.startswith("[") and line.endswith("]"):
                        current_section = line[1:-1]  # Remove [ e ]
                        in_target_section = current_section == section
                    elif "=" in line and in_target_section:
                        # É uma chave=valor na seção desejada
                        key, value = line.split("=", 1)  # Split apenas no primeiro =
                        key = key.strip()
                        value = value.strip()
                        # Preservar ordem usando dict (Python 3.7+ mantém ordem de inserção)
                        section_data[key] = value

            return section_data
        except Exception as e:
            self.logger.error(f"Erro ao carregar seção {section}: {e}")
            raise

    def get_value(self, section: str, key: str) -> Optional[str]:
        """
        Obter valor específico

        Args:
            section: Nome da seção
            key: Chave da configuração

        Returns:
            Valor da configuração ou None se não existir
        """
        if not self.settings_file.exists():
            return None

        try:
            self.parser.read(self.settings_file, encoding="utf-8")

            if not self.parser.has_section(section):
                return None

            return self.parser.get(section, key, fallback=None)
        except Exception as e:
            self.logger.error(f"Erro ao obter valor {section}.{key}: {e}")
            return None

    def set_value(self, section: str, key: str, value: Any) -> Dict[str, Any]:
        """
        Definir valor de uma configuração (aceita qualquer campo)

        Args:
            section: Nome da seção
            key: Chave da configuração
            value: Valor a definir (será convertido para string)

        Returns:
            Resultado da operação
        """
        # Criar backup antes de modificar
        backup_path = self._create_backup()

        try:
            # Carregar arquivo atual
            if self.settings_file.exists():
                self.parser.read(self.settings_file, encoding="utf-8")

            # Criar seção se não existir
            if not self.parser.has_section(section):
                self.parser.add_section(section)

            # Definir valor (sempre como string)
            normalized_value = self._normalize_value_for_write(section, key, value)
            self.parser.set(section, key, normalized_value)

            # Salvar arquivo
            with open(self.settings_file, "w", encoding="utf-8") as f:
                self.parser.write(f)

            self.logger.info(f"Configuração atualizada: {section}.{key} = {value}")

            return {
                "success": True,
                "message": f"Configuração {key} atualizada",
                "section": section,
                "key": key,
                "value": normalized_value,
                "backup": str(backup_path) if backup_path else None,
            }
        except Exception as e:
            self.logger.error(f"Erro ao salvar configuração {section}.{key}: {e}")
            return {"success": False, "error": f"Erro ao salvar: {str(e)}"}

    def update_section(self, section: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualizar múltiplos campos de uma seção (aceita qualquer campo)

        Args:
            section: Nome da seção
            updates: Dicionário com chaves e valores a atualizar

        Returns:
            Resultado da operação
        """
        # Criar backup antes de modificar
        backup_path = self._create_backup()

        try:
            # Carregar arquivo atual
            if self.settings_file.exists():
                self.parser.read(self.settings_file, encoding="utf-8")

            # Criar seção se não existir
            if not self.parser.has_section(section):
                self.parser.add_section(section)

            # Atualizar todos os campos
            updated = []
            for key, value in updates.items():
                normalized_value = self._normalize_value_for_write(section, key, value)
                self.parser.set(section, key, normalized_value)
                updated.append(key)

            # Salvar arquivo
            with open(self.settings_file, "w", encoding="utf-8") as f:
                self.parser.write(f)

            self.logger.info(f"Seção {section} atualizada: {len(updated)} campo(s)")

            return {
                "success": True,
                "message": f"{len(updated)} campo(s) atualizado(s)",
                "section": section,
                "updated_fields": updated,
                "backup": str(backup_path) if backup_path else None,
            }
        except Exception as e:
            self.logger.error(f"Erro ao atualizar seção {section}: {e}")
            return {"success": False, "error": f"Erro ao salvar: {str(e)}"}

    def _create_backup(self) -> Optional[Path]:
        """
        Criar backup do arquivo antes de modificar

        Returns:
            Caminho do backup criado ou None se arquivo não existe
        """
        if not self.settings_file.exists():
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.config_directory / "backups"
            backup_dir.mkdir(exist_ok=True)

            backup_path = backup_dir / f"ServerSettings.backup.{timestamp}.ini"
            shutil.copy2(self.settings_file, backup_path)

            # Manter apenas últimos 10 backups
            self._cleanup_old_backups(backup_dir)

            self.logger.info(f"Backup criado: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.warning(f"Erro ao criar backup: {e}")
            return None

    def _cleanup_old_backups(self, backup_dir: Path, keep: int = 10):
        """
        Limpar backups antigos, mantendo apenas os últimos N

        Args:
            backup_dir: Diretório de backups
            keep: Número de backups a manter
        """
        try:
            backups = sorted(
                backup_dir.glob("ServerSettings.backup.*.ini"), reverse=True
            )
            for backup in backups[keep:]:
                backup.unlink()
                self.logger.debug(f"Backup antigo removido: {backup}")
        except Exception as e:
            self.logger.warning(f"Erro ao limpar backups antigos: {e}")
