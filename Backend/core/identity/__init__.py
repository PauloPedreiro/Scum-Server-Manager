"""
Módulo de Identidade para Escalabilidade
Gerencia identificação única do backend e proprietário
"""

from .backend_id import BackendIdentity
from .owner_manager import OwnerManager

__all__ = ["BackendIdentity", "OwnerManager"]
