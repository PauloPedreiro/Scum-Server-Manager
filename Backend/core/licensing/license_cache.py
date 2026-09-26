"""
Cache Local de Validação de Licença
Armazena hash de hardware e resultados de validação localmente
"""
from core.database.connector import DatabaseConnector

import json
import os
import sqlite3
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class LicenseCache:
    """Gerencia cache local de hardware fingerprint e validações"""

    def __init__(
        self, data_dir: str = "data", db_path: Optional[str] = None, logger=None
    ):
        """
        Inicializa o cache de licença

        Args:
            data_dir: Diretório de dados
            db_path: Caminho do banco de dados (opcional)
            logger: Logger opcional
        """
        self.data_dir = Path(data_dir)
        self.logger = logger
        # ❌ REMOVIDO: fingerprint_file (não salvar hash por segurança)
        self.license_file = self.data_dir / "license.json"

        # Caminho do banco
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = str(self.data_dir / "SSM.db")

        # Garantir que diretório existe
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Inicializar tabela no banco
        self._ensure_table()

    def _ensure_table(self):
        """Garante que a tabela hardware_fingerprints existe"""
        try:
            with DatabaseConnector.get_connection(self.db_path, timeout=30.0, write_mode=True) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS hardware_fingerprints (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fingerprint_hash TEXT UNIQUE NOT NULL,
                        components_json TEXT NOT NULL,
                        first_detected DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_verified DATETIME DEFAULT CURRENT_TIMESTAMP,
                        verification_count INTEGER DEFAULT 0,
                        is_valid BOOLEAN DEFAULT 1,
                        server_registered_at DATETIME,
                        notes TEXT
                    )
                """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_fingerprint_hash 
                    ON hardware_fingerprints(fingerprint_hash)
                """
                )

                conn.commit()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao criar tabela hardware_fingerprints: {e}")

    def save_fingerprint(
        self, fingerprint_hash: str, components: Dict[str, Any]
    ) -> bool:
        """
        DEPRECATED: Não salva hash em lugar nenhum por segurança

        Motivo: Arquivo JSON e banco podem ser copiados entre máquinas.
        Auditoria é feita no servidor (que recebe hash a cada validação).

        Args:
            fingerprint_hash: Hash do hardware (não usado)
            components: Componentes coletados (não usado)

        Returns:
            True (apenas para compatibilidade)
        """
        # SEGURANÇA: Não salvar hash em lugar nenhum (nem arquivo, nem banco)
        # Hash sempre gerado em memória quando necessário
        # Auditoria é feita no servidor que recebe hash a cada validação
        if self.logger:
            self.logger.debug(
                "save_fingerprint() chamado mas hash não será armazenado por segurança"
            )
        return True

    # ❌ REMOVIDO: load_fingerprint() e get_stored_hash()
    # Hash não é mais armazenado (nem arquivo, nem banco)
    # Hash sempre gerado em memória quando necessário

    def save_license_info(self, license_data: Dict[str, Any]) -> bool:
        """
        Salva informações da licença

        Args:
            license_data: Dados da licença

        Returns:
            True se salvo com sucesso
        """
        try:
            # Carregar dados existentes
            existing_data = self.load_license_info() or {}

            # Atualizar com novos dados
            existing_data.update(license_data)
            existing_data["updated_at"] = datetime.now().isoformat()

            with open(self.license_file, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao salvar informações da licença: {e}")
            return False

    def load_license_info(self) -> Optional[Dict[str, Any]]:
        """
        Carrega informações da licença

        Returns:
            Dicionário com dados da licença ou None
        """
        try:
            if not self.license_file.exists():
                return None

            with open(self.license_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return data

        except Exception as e:
            if self.logger:
                self.logger.warning(f"Erro ao carregar informações da licença: {e}")
            return None

    def save_validation_result(self, validation_data: Dict[str, Any]) -> bool:
        """
        Salva resultado de validação

        Args:
            validation_data: Dados da validação

        Returns:
            True se salvo com sucesso
        """
        try:
            license_info = self.load_license_info() or {}

            license_info["last_validation"] = {
                "timestamp": datetime.now().isoformat(),
                "valid": validation_data.get("valid", False),
                "expires_at": validation_data.get("expires_at"),
                "next_check_at": validation_data.get("next_check_at"),
                "server_response": validation_data,
            }

            return self.save_license_info(license_info)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao salvar resultado de validação: {e}")
            return False

    def is_validation_cached(self, max_age_seconds: int = 14400) -> bool:
        """
        Verifica se há validação em cache válida

        Args:
            max_age_seconds: Idade máxima do cache em segundos (padrão: 4h)

        Returns:
            True se cache válido
        """
        license_info = self.load_license_info()
        if not license_info:
            return False

        last_validation = license_info.get("last_validation")
        if not last_validation:
            return False

        if not last_validation.get("valid", False):
            return False

        # Verificar idade do cache
        try:
            timestamp_str = last_validation.get("timestamp")
            if not timestamp_str:
                return False

            timestamp = datetime.fromisoformat(timestamp_str)
            age_seconds = (datetime.now() - timestamp).total_seconds()

            return age_seconds < max_age_seconds

        except Exception:
            return False

    def clear_cache(self):
        """Limpa cache de validação"""
        try:
            if self.license_file.exists():
                self.license_file.unlink()
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Erro ao limpar cache: {e}")
