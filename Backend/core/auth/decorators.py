"""
Decorators para proteção de rotas
"""

from functools import wraps
from flask import request, jsonify
from typing import Callable, Any
import sys

# Cache do módulo main para evitar múltiplas importações
_main_module_cache = None


def _get_main_module():
    """Obter o módulo main de forma segura"""
    global _main_module_cache

    # Se já temos cache e ele tem auth_manager, usar cache
    if _main_module_cache is not None:
        if hasattr(_main_module_cache, "get_auth_manager") or hasattr(
            _main_module_cache, "auth_manager"
        ):
            return _main_module_cache

    # Tentar importar main diretamente primeiro (mais confiável)
    try:
        import main

        if hasattr(main, "get_auth_manager") or hasattr(main, "auth_manager"):
            _main_module_cache = main
            return _main_module_cache
    except ImportError:
        pass

    # Tentar obter via __main__ (quando executado como script)
    if "__main__" in sys.modules:
        potential_main = sys.modules["__main__"]
        # Verificar se é realmente o main.py (tem get_auth_manager ou auth_manager)
        if hasattr(potential_main, "get_auth_manager") or hasattr(
            potential_main, "auth_manager"
        ):
            _main_module_cache = potential_main
            return _main_module_cache

    # Tentar buscar em todos os módulos carregados
    for module_name, module in sys.modules.items():
        if module_name == "main" or (
            hasattr(module, "__file__")
            and module.__file__
            and "main.py" in module.__file__
        ):
            if hasattr(module, "get_auth_manager") or hasattr(module, "auth_manager"):
                _main_module_cache = module
                return _main_module_cache

    # Se ainda não encontrou, retornar None
    return None


def require_auth(f: Callable) -> Callable:
    """
    Decorator que requer autenticação JWT

    Adiciona ao request:
    - request.current_user_id
    - request.current_username
    - request.current_role
    - request.current_user (dados completos)
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Usar o novo ServiceRegistry para obter o auth_manager
        auth_manager = None
        try:
            from app.extensions import get_services
            services = get_services()
            auth_manager = services.auth_manager
        except ImportError:
            # Fallback para o modo legado se o app factory ainda não estiver pronto
            pass

        if not auth_manager:
            import logging
            logger = logging.getLogger("scum_backend")
            logger.error("AuthManager não encontrado no ServiceRegistry")
            return (
                jsonify(
                    {"success": False, "error": "Authentication system not initialized"}
                ),
                500,
            )

        # Obter token do header
        token = None
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Authentication required",
                        "code": "AUTH_REQUIRED",
                    }
                ),
                401,
            )

        # Validar token
        try:
            user = auth_manager.validate_token(token)

            if not user:
                # Log para debug
                import logging

                logger = logging.getLogger("scum_backend")
                logger.warn(f"Token inválido ou expirado: {token[:50]}...")

                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid or expired token",
                            "code": "INVALID_TOKEN",
                        }
                    ),
                    401,
                )
        except Exception as e:
            import logging

            logger = logging.getLogger("scum_backend")
            logger.error(f"Erro ao validar token: {e}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Token validation error",
                        "code": "TOKEN_ERROR",
                    }
                ),
                401,
            )

        # Adicionar dados do usuário ao request
        request.current_user_id = user["id"]
        request.current_username = user["username"]
        request.current_role = user.get("role", "admin")
        request.current_user = user

        return f(*args, **kwargs)

    return decorated_function


def require_admin(f: Callable) -> Callable:
    """
    Decorator que requer role de admin

    Deve ser usado após @require_auth
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se @require_auth foi aplicado
        if not hasattr(request, "current_role"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Authentication required",
                        "code": "AUTH_REQUIRED",
                    }
                ),
                401,
            )

        current_role = str(getattr(request, "current_role", "") or "")
        current_user = getattr(request, "current_user", None) or {}
        discord_user_id = str((current_user or {}).get("discord_user_id") or "").strip()

        if current_role == "admin_pending" or (current_role == "admin" and not discord_user_id):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Discord link required",
                        "code": "DISCORD_LINK_REQUIRED",
                    }
                ),
                403,
            )

        # Verificar se é admin
        if current_role != "admin":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Admin access required",
                        "code": "ADMIN_REQUIRED",
                    }
                ),
                403,
            )

        return f(*args, **kwargs)

    return decorated_function

def require_player_auth(f: Callable) -> Callable:
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.extensions import get_services
        import jwt
        from flask import request, jsonify
        
        services = get_services()
        config = services.config
        
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return jsonify({"success": False, "error": "AUTH_REQUIRED"}), 401
            
        auth_cfg = (config or {}).get("auth", {}) if isinstance(config, dict) else {}
        secret = str(auth_cfg.get("jwt_secret") or "").strip()
        if secret.startswith("ENCRYPTED:"):
            try:
                from core.security.credential_encryption import decrypt_credential
                secret = decrypt_credential(secret, logger=None)
            except Exception:
                secret = ""
        if not secret:
            secret = "ssm-backend-secret-key-change-in-production"
            
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"require": ["exp", "iat"], "verify_aud": False},
            )
            if not isinstance(payload, dict):
                raise ValueError("Invalid payload")
            if str(payload.get("aud") or "") != "player":
                raise ValueError("Invalid aud")
            if not str(payload.get("sub") or "").strip():
                raise ValueError("No sub")
            if not str(payload.get("server_hash") or "").strip():
                raise ValueError("No server hash")
        except Exception:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        expected_server_hash = str(payload.get("server_hash") or "").strip()
        provided_server_hash = str(request.headers.get("X-Server-Hash") or "").strip()
        if not provided_server_hash:
            return jsonify({"success": False, "error": "SERVER_HASH_REQUIRED"}), 400
        if expected_server_hash and provided_server_hash != expected_server_hash:
            return jsonify({"success": False, "error": "SERVER_HASH_MISMATCH"}), 403

        request.player_steam_id = str(payload.get("sub"))
        request.player_server_hash = expected_server_hash
        request.player_server_hash_provided = provided_server_hash
        return f(*args, **kwargs)

    return decorated_function
