"""
Módulo de Autenticação do SSM Backend
"""

from .auth_manager import AuthManager
from .user_manager import UserManager
from .password_handler import PasswordHandler
from .jwt_handler import JWTHandler
from .decorators import require_auth, require_admin

__all__ = [
    "AuthManager",
    "UserManager",
    "PasswordHandler",
    "JWTHandler",
    "require_auth",
    "require_admin",
]
