"""
Handler para gerenciamento de senhas usando bcrypt
"""

import bcrypt
from typing import Optional


class PasswordHandler:
    """Classe para hash e verificação de senhas usando bcrypt"""

    def __init__(self, rounds: int = 12):
        """
        Inicializa o handler de senhas

        Args:
            rounds: Número de rounds do bcrypt (padrão: 12)
        """
        self.rounds = rounds

    def hash_password(self, password: str) -> str:
        """
        Gera hash da senha usando bcrypt

        Args:
            password: Senha em texto plano

        Returns:
            Hash da senha em formato string
        """
        if not password:
            raise ValueError("Password cannot be empty")

        # Gera salt e hash
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

        return hashed.decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verifica se a senha corresponde ao hash

        Args:
            password: Senha em texto plano
            password_hash: Hash armazenado

        Returns:
            True se a senha corresponde, False caso contrário
        """
        if not password or not password_hash:
            return False

        try:
            # Verifica se a senha corresponde ao hash
            # Garantir que ambos são bytes
            password_bytes = (
                password.encode("utf-8") if isinstance(password, str) else password
            )
            hash_bytes = (
                password_hash.encode("utf-8")
                if isinstance(password_hash, str)
                else password_hash
            )

            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception as e:
            # Log do erro para debug (se tiver logger disponível)
            import sys

            print(f"Erro ao verificar senha: {e}", file=sys.stderr)
            return False

    def validate_password_strength(
        self, password: str, min_length: int = 8
    ) -> tuple[bool, Optional[str]]:
        """
        Valida força da senha

        Args:
            password: Senha a validar
            min_length: Comprimento mínimo (padrão: 8)

        Returns:
            Tupla (is_valid, error_message)
        """
        if not password:
            return False, "Password cannot be empty"

        if len(password) < min_length:
            return False, f"Password must be at least {min_length} characters"

        return True, None
