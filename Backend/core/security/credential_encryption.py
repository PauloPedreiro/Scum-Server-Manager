"""
Sistema de Criptografia de Credenciais
Criptografa credenciais usando chave derivada do hardware
Impede cópia de credenciais entre máquinas
"""

import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    from core.licensing.hardware_fingerprint import HardwareFingerprint

    HARDWARE_FP_AVAILABLE = True
except ImportError:
    HARDWARE_FP_AVAILABLE = False
    HardwareFingerprint = None


class CredentialEncryption:
    """Criptografa e descriptografa credenciais usando chave derivada do hardware"""

    # Prefixo para identificar credenciais criptografadas
    ENCRYPTED_PREFIX = "ENCRYPTED:"

    def __init__(self, logger=None):
        """
        Inicializa o sistema de criptografia

        Args:
            logger: Logger opcional
        """
        self.logger = logger
        self._hardware_key = None
        self._hardware_fingerprint = None

        if HARDWARE_FP_AVAILABLE:
            try:
                self._hardware_fingerprint = HardwareFingerprint(logger=logger)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Erro ao inicializar HardwareFingerprint: {e}")

    def _get_hardware_key(self) -> bytes:
        """
        Gera chave de criptografia baseada no hardware

        Returns:
            Chave Fernet (32 bytes em base64)
        """
        if self._hardware_key:
            return self._hardware_key

        if not self._hardware_fingerprint:
            raise Exception(
                "HardwareFingerprint não disponível - não é possível criptografar credenciais"
            )

        try:
            # Gerar hash do hardware
            hash_value, _ = self._hardware_fingerprint.generate()

            # Usar hash como salt para PBKDF2
            # PBKDF2 é mais seguro que usar hash diretamente
            salt = hashlib.sha256(hash_value.encode()).digest()[
                :16
            ]  # 16 bytes para salt

            # Derivar chave usando PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 32 bytes para Fernet
                salt=salt,
                iterations=100000,  # Alto número de iterações para segurança
            )

            # Usar hash como password para PBKDF2
            password = hash_value.encode()
            key = kdf.derive(password)

            # Converter para formato Fernet (base64)
            self._hardware_key = base64.urlsafe_b64encode(key)

            return self._hardware_key

        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao gerar chave de hardware: {e}")
            raise

    def encrypt(self, value: str) -> str:
        """
        Criptografa credencial usando chave do hardware

        Args:
            value: Valor a ser criptografado (texto plano)

        Returns:
            String criptografada com prefixo "ENCRYPTED:"
        """
        if not value or not value.strip():
            return value

        # Se já está criptografado, retornar como está
        if value.startswith(self.ENCRYPTED_PREFIX):
            return value

        try:
            key = self._get_hardware_key()
            f = Fernet(key)

            # Criptografar
            encrypted = f.encrypt(value.encode("utf-8"))

            # Codificar em base64 e adicionar prefixo
            encrypted_b64 = base64.urlsafe_b64encode(encrypted).decode("utf-8")
            return f"{self.ENCRYPTED_PREFIX}{encrypted_b64}"

        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao criptografar credencial: {e}")
            # Em caso de erro, retornar valor original (não quebrar sistema)
            return value

    def decrypt(self, encrypted_value: str) -> str:
        """
        Descriptografa credencial usando chave do hardware

        Args:
            encrypted_value: Valor criptografado (com ou sem prefixo)

        Returns:
            Valor descriptografado (texto plano)
        """
        if not encrypted_value or not encrypted_value.strip():
            return encrypted_value

        # Se não está criptografado, retornar como está
        if not encrypted_value.startswith(self.ENCRYPTED_PREFIX):
            return encrypted_value

        try:
            key = self._get_hardware_key()
            f = Fernet(key)

            # Remover prefixo
            encrypted_b64 = encrypted_value[len(self.ENCRYPTED_PREFIX) :]

            # Decodificar base64
            encrypted = base64.urlsafe_b64decode(encrypted_b64.encode("utf-8"))

            # Descriptografar
            decrypted = f.decrypt(encrypted)

            return decrypted.decode("utf-8")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao descriptografar credencial: {e}")
            # Em caso de erro, retornar vazio (forçar reconfiguração)
            return ""

    def is_encrypted(self, value: str) -> bool:
        """
        Verifica se um valor está criptografado

        Args:
            value: Valor a verificar

        Returns:
            True se está criptografado
        """
        return value and value.startswith(self.ENCRYPTED_PREFIX)


# Instância global (lazy initialization)
_credential_encryption_instance = None


def get_credential_encryption(logger=None) -> CredentialEncryption:
    """
    Obtém instância global do sistema de criptografia

    Args:
        logger: Logger opcional

    Returns:
        Instância de CredentialEncryption
    """
    global _credential_encryption_instance
    if _credential_encryption_instance is None:
        _credential_encryption_instance = CredentialEncryption(logger=logger)
    return _credential_encryption_instance


def encrypt_credential(value: str, logger=None) -> str:
    """
    Função helper para criptografar credencial

    Args:
        value: Valor a criptografar
        logger: Logger opcional

    Returns:
        Valor criptografado
    """
    enc = get_credential_encryption(logger=logger)
    return enc.encrypt(value)


def decrypt_credential(encrypted_value: str, logger=None) -> str:
    """
    Função helper para descriptografar credencial

    Args:
        encrypted_value: Valor criptografado
        logger: Logger opcional

    Returns:
        Valor descriptografado
    """
    enc = get_credential_encryption(logger=logger)
    return enc.decrypt(encrypted_value)
