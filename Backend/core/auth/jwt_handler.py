"""
Handler para gerenciamento de JWT tokens
"""

import jwt
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class JWTHandler:
    """Classe para geração e validação de JWT tokens"""

    def __init__(self, secret_key: str, expiration_hours: int = 24):
        """
        Inicializa o handler de JWT

        Args:
            secret_key: Chave secreta para assinar tokens
            expiration_hours: Horas até expiração (padrão: 24)
        """
        secret_clean = str(secret_key or "").strip()
        if not secret_clean:
            secret_clean = "ssm-backend-secret-key-change-in-production"
        self.secret_key = secret_clean
        self.expiration_hours = expiration_hours
        self.algorithm = "HS256"

    def generate_token(
        self, user_id: int, username: str, role: str, password_changed: bool
    ) -> str:
        """
        Gera token JWT para o usuário

        Args:
            user_id: ID do usuário
            username: Nome de usuário
            role: Role do usuário (admin, moderator, etc.)
            password_changed: Se a senha foi alterada

        Returns:
            Token JWT como string
        """
        # Calcula expiração
        exp = datetime.utcnow() + timedelta(hours=self.expiration_hours)

        # Payload do token
        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "password_changed": password_changed,
            "exp": exp,
            "iat": datetime.utcnow(),
        }

        # Gera token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return token

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decodifica e valida token JWT

        Args:
            token: Token JWT

        Returns:
            Payload do token se válido, None caso contrário
        """
        if not token:
            return None

        try:
            # Decodifica e valida token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None

    def get_expiration_seconds(self) -> int:
        """
        Retorna tempo de expiração em segundos

        Returns:
            Segundos até expiração
        """
        return self.expiration_hours * 3600
