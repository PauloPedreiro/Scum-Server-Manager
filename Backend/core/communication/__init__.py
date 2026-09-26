"""
Módulo de Comunicação para Escalabilidade
Gerencia comunicação com frontend central e comandos remotos
"""

from .heartbeat_manager import HeartbeatManager
from .remote_commands import RemoteCommandHandler
from .license_validator import LicenseValidator
from .gestao_messages_service import GestaoMessagesService

__all__ = [
    "HeartbeatManager",
    "RemoteCommandHandler",
    "LicenseValidator",
    "GestaoMessagesService",
]
