"""
Sistema de Recuperação de Senha
Gerencia tokens de reset de senha e validações
"""

import threading
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from utils.logger import StructuredLogger


class PasswordResetManager:
    """Gerencia tokens de recuperação de senha"""

    _initialized_schema = False
    _schema_lock = threading.Lock()

    def __init__(self, db_path: str, logger: Optional[StructuredLogger] = None):
        """
        Inicializa o gerenciador de reset de senha

        Args:
            db_path: Caminho do banco SSM.db
            logger: Logger para logs
        """
        self.db_path = db_path
        self.logger = logger or StructuredLogger()
        self.token_expiration_minutes = 15  # Tokens expiram em 15 minutos

        # Rate limiting: armazenar tentativas em memória
        # Formato: {ip: [(timestamp, username), ...]}
        self.rate_limit_requests = {}

        # Garantir que a tabela existe
        self.ensure_table()

    def ensure_table(self):
        """Garante que a tabela password_reset_tokens existe"""
        if PasswordResetManager._initialized_schema:
            return

        with PasswordResetManager._schema_lock:
            if PasswordResetManager._initialized_schema:
                return

            try:
                from core.database.connector import DatabaseConnector
                with DatabaseConnector.get_connection(self.db_path, timeout=30.0, write_mode=True) as conn:
                    cursor = conn.cursor()

                    # Criar tabela se não existir
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS password_reset_tokens (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username VARCHAR(50) NOT NULL,
                            token VARCHAR(64) UNIQUE NOT NULL,
                            expires_at DATETIME NOT NULL,
                            used INTEGER DEFAULT 0,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            ip_address TEXT,
                            FOREIGN KEY (username) REFERENCES frontend_users(username) ON DELETE CASCADE
                        )
                    """
                    )

                    # Criar índices
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token 
                        ON password_reset_tokens(token)
                    """
                    )

                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_username 
                        ON password_reset_tokens(username)
                    """
                    )

                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at 
                        ON password_reset_tokens(expires_at)
                    """
                    )

                    conn.commit()
                    PasswordResetManager._initialized_schema = True
                    self.logger.info("Tabela password_reset_tokens verificada/criada")

            except Exception as e:
                self.logger.error(f"Erro ao criar tabela password_reset_tokens: {e}")
                raise

    def generate_token(self) -> str:
        """
        Gera token único de 64 caracteres hexadecimais

        Returns:
            Token único
        """
        return secrets.token_hex(32)  # 32 bytes = 64 caracteres hex

    def check_rate_limit(self, ip_address: str, username: str) -> Tuple[bool, str]:
        """
        Verifica rate limiting para solicitações de reset

        Args:
            ip_address: IP de origem
            username: Username solicitado

        Returns:
            (is_allowed, error_message)
        """
        now = datetime.now()

        # Limpar entradas antigas (> 15 minutos)
        cutoff_time = now - timedelta(minutes=15)
        if ip_address in self.rate_limit_requests:
            self.rate_limit_requests[ip_address] = [
                (ts, un)
                for ts, un in self.rate_limit_requests[ip_address]
                if ts > cutoff_time
            ]

        # Verificar limite por IP (3 tentativas a cada 15 minutos)
        if ip_address in self.rate_limit_requests:
            recent_requests = len(self.rate_limit_requests[ip_address])
            if recent_requests >= 3:
                return (
                    False,
                    "Muitas tentativas. Aguarde 15 minutos antes de tentar novamente.",
                )

        # Verificar limite por username (1 tentativa a cada 5 minutos)
        cutoff_time_username = now - timedelta(minutes=5)
        for ip, requests in self.rate_limit_requests.items():
            for ts, un in requests:
                if un == username and ts > cutoff_time_username:
                    return (
                        False,
                        "Uma solicitação já foi enviada para este usuário. Aguarde 5 minutos.",
                    )

        return True, ""

    def record_request(self, ip_address: str, username: str):
        """Registra uma solicitação de reset para rate limiting"""
        now = datetime.now()
        if ip_address not in self.rate_limit_requests:
            self.rate_limit_requests[ip_address] = []
        self.rate_limit_requests[ip_address].append((now, username))

    def create_reset_token(
        self, username: str, ip_address: Optional[str] = None
    ) -> Optional[str]:
        """
        Cria um novo token de reset de senha

        Args:
            username: Username do usuário
            ip_address: IP de origem (opcional)

        Returns:
            Token gerado ou None se erro
        """
        try:
            # Gerar token único
            token = self.generate_token()

            # Calcular expiração
            expires_at = datetime.now() + timedelta(
                minutes=self.token_expiration_minutes
            )

            from core.database.connector import DatabaseConnector
            with DatabaseConnector.get_connection(self.db_path, write_mode=True) as conn:
                cursor = conn.cursor()

                # Inserir token
                cursor.execute(
                    """
                    INSERT INTO password_reset_tokens 
                    (username, token, expires_at, ip_address)
                    VALUES (?, ?, ?, ?)
                """,
                    (username, token, expires_at.isoformat(), ip_address),
                )

                conn.commit()

            self.logger.info(f"Token de reset criado para usuário: {username}")
            return token

        except sqlite3.IntegrityError:
            # Token duplicado (muito raro, mas possível)
            self.logger.error("Token duplicado gerado, tentando novamente...")
            return self.create_reset_token(username, ip_address)
        except Exception as e:
            self.logger.error(f"Erro ao criar token de reset: {e}")
            return None

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Valida um token de reset

        Args:
            token: Token a validar

        Returns:
            Dados do token (username, etc.) ou None se inválido
        """
        try:
            from core.database.connector import DatabaseConnector
            with DatabaseConnector.get_connection(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Buscar token
                cursor.execute(
                    """
                    SELECT * FROM password_reset_tokens 
                    WHERE token = ?
                """,
                    (token,),
                )

                row = cursor.fetchone()

                if not row:
                    return None

                token_data = dict(row)

                # Verificar se já foi usado
                if token_data["used"] == 1:
                    self.logger.warn(
                        f"Tentativa de usar token já utilizado: {token[:16]}..."
                    )
                    return None

                # Verificar expiração
                expires_at = datetime.fromisoformat(token_data["expires_at"])
                if datetime.now() > expires_at:
                    self.logger.warn(f"Tentativa de usar token expirado: {token[:16]}...")
                    return None

                return token_data

        except Exception as e:
            self.logger.error(f"Erro ao validar token: {e}")
            return None

    def mark_token_as_used(self, token: str) -> bool:
        """
        Marca um token como usado

        Args:
            token: Token a marcar

        Returns:
            True se sucesso, False caso contrário
        """
        try:
            from core.database.connector import DatabaseConnector
            with DatabaseConnector.get_connection(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    UPDATE password_reset_tokens 
                    SET used = 1 
                    WHERE token = ?
                """,
                    (token,),
                )

                conn.commit()

            self.logger.info(f"Token marcado como usado: {token[:16]}...")
            return True

        except Exception as e:
            self.logger.error(f"Erro ao marcar token como usado: {e}")
            return False

    def cleanup_expired_tokens(self):
        """Remove tokens expirados do banco (opcional, pode ser chamado periodicamente)"""
        try:
            from core.database.connector import DatabaseConnector
            with DatabaseConnector.get_connection(self.db_path) as conn:
                cursor = conn.cursor()

                # Remover tokens expirados há mais de 24 horas
                cutoff_time = datetime.now() - timedelta(hours=24)
                cursor.execute(
                    """
                    DELETE FROM password_reset_tokens 
                    WHERE expires_at < ? OR (used = 1 AND created_at < ?)
                """,
                    (cutoff_time.isoformat(), cutoff_time.isoformat()),
                )

                deleted = cursor.rowcount
                conn.commit()

            if deleted > 0:
                self.logger.info(f"Removidos {deleted} tokens expirados/antigos")

        except Exception as e:
            self.logger.error(f"Erro ao limpar tokens expirados: {e}")
