"""
Blueprint: auth
"""

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac
from functools import wraps
from core.auth.decorators import require_auth, require_admin

from datetime import datetime, timedelta, timezone

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/api/auth/debug", methods=["GET"])
def debug_auth():
    """Endpoint de debug para verificar status do auth_manager e usuários"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not auth_manager:
            return (
                jsonify(
                    {"success": False, "error": "AuthManager não está inicializado"}
                ),
                500,
            )

        # Verificar se usuário admin existe
        admin_exists = auth_manager.user_manager.user_exists("admin")
        admin_user = None
        if admin_exists:
            admin_user = auth_manager.user_manager.get_user_by_username("admin")
            # Não retornar o hash da senha por segurança, mas mostrar se existe
            if admin_user:
                has_hash = bool(admin_user.get("password_hash"))
                admin_user = {
                    k: v for k, v in admin_user.items() if k != "password_hash"
                }
                admin_user["has_password_hash"] = has_hash

        # Tentar recriar usuário admin se não existir
        if not admin_exists:
            try:
                auth_manager.ensure_default_admin()
                admin_exists = auth_manager.user_manager.user_exists("admin")
                if admin_exists:
                    admin_user = auth_manager.user_manager.get_user_by_username("admin")
                    if admin_user:
                        has_hash = bool(admin_user.get("password_hash"))
                        admin_user = {
                            k: v for k, v in admin_user.items() if k != "password_hash"
                        }
                        admin_user["has_password_hash"] = has_hash
            except Exception as e:
                logger.error(f"Erro ao tentar criar usuário admin: {e}")

        return (
            jsonify(
                {
                    "success": True,
                    "auth_manager_initialized": True,
                    "admin_exists": admin_exists,
                    "admin_user": admin_user,
                    "default_username": auth_manager.default_username,
                    "default_password_length": (
                        len(auth_manager.default_password)
                        if auth_manager.default_password
                        else 0
                    ),
                    "has_password_handler": auth_manager.password_handler is not None,
                    "has_jwt_handler": auth_manager.jwt_handler is not None,
                    "note": "Se password_changed=1, a senha padrão não funciona mais. Use recuperação de senha ou endpoint de reset.",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Erro no debug de auth: {e}")
        import traceback

        return (
            jsonify(
                {"success": False, "error": str(e), "traceback": traceback.format_exc()}
            ),
            500,
        )


@auth_bp.route("/api/auth/reset-admin-password", methods=["POST"])
def reset_admin_password():
    """
    Endpoint de emergência para resetar senha do admin
    ATENÇÃO: Use apenas se tiver certeza de que precisa resetar a senha
    """
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not auth_manager:
            return (
                jsonify(
                    {"success": False, "error": "AuthManager não está inicializado"}
                ),
                500,
            )

        remote_addr = (request.remote_addr or "").strip()
        is_local = remote_addr in {"127.0.0.1", "::1"}
        allow_remote = (os.environ.get("SSM_ALLOW_REMOTE_ADMIN_PASSWORD_RESET", "") or "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        reset_secret = (os.environ.get("SSM_ADMIN_RESET_SECRET", "") or "").strip()
        provided_secret = (
            (request.headers.get("X-SSM-Admin-Reset-Secret", "") or "").strip()
        )

        if not is_local:
            if not allow_remote:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Endpoint disponível apenas localmente",
                            "code": "LOCAL_ONLY",
                        }
                    ),
                    403,
                )
            if not reset_secret or not provided_secret or not hmac.compare_digest(reset_secret, provided_secret):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Unauthorized",
                            "code": "UNAUTHORIZED",
                        }
                    ),
                    401,
                )

        data = request.get_json() or {}
        new_password = data.get("new_password", "").strip()
        confirm = data.get("confirm", False)

        # Requer confirmação explícita
        if not confirm:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Confirmação necessária. Envie 'confirm': true no body",
                    }
                ),
                400,
            )

        if not new_password:
            return jsonify({"success": False, "error": "Nova senha é obrigatória"}), 400

        # Validar força da senha
        is_valid, error_msg = auth_manager.password_handler.validate_password_strength(
            new_password, min_length=8
        )
        if not is_valid:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": error_msg
                        or "Senha não atende aos requisitos (mínimo 8 caracteres)",
                    }
                ),
                400,
            )

        # Buscar usuário admin
        admin_user = auth_manager.user_manager.get_user_by_username("admin")
        if not admin_user:
            return (
                jsonify({"success": False, "error": "Usuário admin não encontrado"}),
                404,
            )

        # Gerar novo hash
        new_password_hash = auth_manager.password_handler.hash_password(new_password)

        # Atualizar senha

        now = datetime.now(timezone.utc).isoformat()

        updated_user = auth_manager.user_manager.update_user(
            admin_user["id"],
            password_hash=new_password_hash,
            password_changed=1,
            last_password_change=now,
        )

        if not updated_user:
            return jsonify({"success": False, "error": "Falha ao atualizar senha"}), 500

        logger.warn(f"Senha do admin foi resetada via endpoint de emergência")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Senha do admin resetada com sucesso. Use a nova senha para fazer login.",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Erro ao resetar senha do admin: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """Login do usuário"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not auth_manager:
            logger.error("AuthManager não está inicializado")
            return (
                jsonify(
                    {"success": False, "error": "Authentication system not available"}
                ),
                500,
            )

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request body required"}), 400

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return (
                jsonify({"success": False, "error": "Username and password required"}),
                400,
            )

        # Log de debug (sem mostrar senha completa)
        logger.debug(f"Tentativa de login para usuário: {username}")

        success, result, error = auth_manager.login(username, password)

        if not success:
            # Log de erro para debug
            logger.warn(f"Login falhou para usuário '{username}': {error}")
            return (
                jsonify({"success": False, "error": error or "Invalid credentials"}),
                401,
            )
        return jsonify({"success": True, "data": result}), 200

    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()
        logger.error(f"Erro no login: {e}")
        logger.error(f"Traceback completo: {error_traceback}")
        # Em produção, não expor traceback completo, apenas em debug
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Internal server error",
                    "message": str(e),  # Mostrar mensagem de erro para debug
                }
            ),
            500,
        )


@auth_bp.route("/api/auth/change-password", methods=["POST"])
def change_password():
    """Mudar senha do usuário"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not auth_manager:
            return (
                jsonify(
                    {"success": False, "error": "Authentication system not available"}
                ),
                500,
            )

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request body required"}), 400

        # Pode ter username (primeiro login) ou token (mudança normal)
        username = data.get("username")
        current_password = data.get("current_password")
        new_password = data.get("new_password")
        user_id = None

        # Tentar obter user_id do token se disponível
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user = auth_manager.validate_token(token)
            if user:
                user_id = user["id"]

        if not current_password or not new_password:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Current password and new password required",
                    }
                ),
                400,
            )

        success, result, error = auth_manager.change_password(
            username=username,
            current_password=current_password,
            new_password=new_password,
            user_id=user_id,
        )

        if not success:
            return (
                jsonify(
                    {"success": False, "error": error or "Failed to change password"}
                ),
                400,
            )

        return jsonify({"success": True, "data": result}), 200

    except Exception as e:
        logger.error(f"Erro ao mudar senha: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


def _ensure_discord_admin_link_table(ssm_db_path: str) -> None:
    import sqlite3
    from core.database.connector import DatabaseConnector
    try:
        if not ssm_db_path:
            return
        with DatabaseConnector.get_connection(ssm_db_path, write_mode=True) as conn:
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS discord_admin_link_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username VARCHAR(50) NOT NULL,
                    code VARCHAR(32) UNIQUE NOT NULL,
                    expires_at DATETIME NOT NULL,
                    consumed_at DATETIME,
                    consumed_by_discord_user_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES frontend_users(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_discord_admin_link_codes_code
                ON discord_admin_link_codes(code)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_discord_admin_link_codes_user
                ON discord_admin_link_codes(user_id, consumed_at, expires_at)
                """
            )
            conn.commit()
    except Exception:
        return


def _create_discord_admin_link_code(user: dict, *, ttl_minutes: int = 10) -> str | None:
    import sqlite3
    import secrets
    from core.database.connector import DatabaseConnector
    try:
        if not user:
            return None
        services = get_services()
        ssm_db_path = services.get_ssm_db_path_for_auth()
        _ensure_discord_admin_link_table(ssm_db_path)
        code = f"SSM-LINK-{secrets.token_hex(3).upper()}"
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=int(ttl_minutes))
        with DatabaseConnector.get_connection(ssm_db_path, write_mode=True) as conn:
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute(
                """
                UPDATE discord_admin_link_codes
                SET consumed_at = ?
                WHERE user_id = ?
                  AND consumed_at IS NULL
                  AND expires_at > ?
                """,
                (now.isoformat(), int(user["id"]), now.isoformat()),
            )
            conn.execute(
                """
                INSERT INTO discord_admin_link_codes
                    (user_id, username, code, expires_at, consumed_at, consumed_by_discord_user_id)
                VALUES
                    (?, ?, ?, ?, NULL, NULL)
                """,
                (int(user["id"]), str(user.get("username") or ""), code, expires_at.isoformat()),
            )
            conn.commit()
        return code
    except sqlite3.IntegrityError:
        return _create_discord_admin_link_code(user, ttl_minutes=ttl_minutes)
    except Exception:
        return None


@auth_bp.route("/api/auth/discord-link-code", methods=["POST"])
@require_auth
def generate_discord_link_code():
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not auth_manager:
            return (
                jsonify({"success": False, "error": "Authentication system not available"}),
                500,
            )
        user = request.current_user
        discord_user_id = str((user or {}).get("discord_user_id") or "").strip()
        role = str((user or {}).get("role") or "admin")
        must_link_discord = bool(role == "admin_pending" or (role == "admin" and not discord_user_id))
        if not must_link_discord:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Discord link not required",
                        "code": "DISCORD_LINK_NOT_REQUIRED",
                    }
                ),
                400,
            )

        code = _create_discord_admin_link_code(user, ttl_minutes=10)
        if not code:
            return jsonify({"success": False, "error": "Internal server error"}), 500

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "code": code,
                        "expires_in_minutes": 10,
                        "command": f"!link {code}",
                    },
                }
            ),
            200,
        )
    except Exception as e:
        try:
            import traceback

            logger.error(f"Erro ao gerar código de vinculação Discord: {e}")
            logger.error(traceback.format_exc())
        except Exception:
            pass
        return jsonify({"success": False, "error": "Internal server error"}), 500


@auth_bp.route("/api/auth/me", methods=["GET"])
@require_auth
def get_current_user():
    """Obter dados do usuário atual"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        user = request.current_user

        discord_user_id = (user.get("discord_user_id") or "").strip()
        role = user.get("role", "admin")
        must_link_discord = bool(role == "admin_pending" or (role == "admin" and not discord_user_id))

        # Formatar resposta
        response_data = {
            "id": user["id"],
            "username": user["username"],
            "role": role,
            "password_changed": bool(user.get("password_changed", 0)),
            "discord_user_id": discord_user_id or None,
            "must_link_discord": must_link_discord,
            "steam_id": user.get("steam_id"),
            "player_name": user.get("player_name"),
            "player_id": user.get("player_id"),
            "last_login": user.get("last_login"),
        }

        return jsonify({"success": True, "data": response_data}), 200

    except Exception as e:
        logger.error(f"Erro ao obter usuário atual: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@auth_bp.route("/api/auth/logout", methods=["POST"])
@require_auth
def logout():
    """Logout do usuário (apenas validação do token)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        # Com JWT, logout é apenas do lado do cliente (remover token)
        # Aqui apenas validamos que o token é válido
        return jsonify({"success": True, "message": "Logged out successfully"}), 200

    except Exception as e:
        logger.error(f"Erro no logout: {e}")


@auth_bp.route("/api/auth/request-password-reset", methods=["POST"])
def request_password_reset():
    """Solicitar reset de senha - gera token e envia via Discord"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not password_reset_manager or not auth_manager:
            # Resposta genérica para não revelar se o sistema está disponível
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Se o usuário existir, um token de recuperação foi enviado via Discord",
                    }
                ),
                200,
            )

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "error": "Request body required"}), 400

        username = data.get("username")
        if not username:
            return jsonify({"success": False, "error": "Username required"}), 400

        # Obter IP de origem
        ip_address = request.remote_addr or request.environ.get(
            "HTTP_X_FORWARDED_FOR", "Unknown"
        )

        # Verificar rate limiting
        is_allowed, error_msg = password_reset_manager.check_rate_limit(
            ip_address, username
        )
        if not is_allowed:
            # Resposta genérica mesmo para rate limit
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Se o usuário existir, um token de recuperação foi enviado via Discord",
                    }
                ),
                200,
            )

        # Verificar se usuário existe e está ativo
        user = auth_manager.user_manager.get_user_by_username(username)
        if not user or not user.get("is_active", 1):
            # Resposta genérica - não revelar se usuário existe
            password_reset_manager.record_request(ip_address, username)
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Se o usuário existir, um token de recuperação foi enviado via Discord",
                    }
                ),
                200,
            )

        # Criar token de reset
        token = password_reset_manager.create_reset_token(username, ip_address)
        if not token:
            try:
                logger.error(
                    "Falha ao gerar token de reset de senha (create_reset_token retornou None)",
                    {"username": username, "ip": ip_address},
                )
            except Exception:
                pass
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Se o usuário existir, um token de recuperação foi enviado via Discord",
                    }
                ),
                200,
            )

        # Registrar solicitação para rate limiting
        password_reset_manager.record_request(ip_address, username)

        discord_uid = (user.get("discord_user_id") or "").strip()
        if discord_uid and discord_bot_service is not None:
            try:
                msg = (
                    "Password recovery token generated.\n\n"
                    f"Token: {token}\n"
                    "Expires in 15 minutes.\n\n"
                    "If you did not request this, ignore this message."
                )
                discord_bot_service.send_dm(int(discord_uid), msg)
            except Exception as e:
                try:
                    logger.error(f"Erro ao enviar DM de reset via bot: {e}")
                except Exception:
                    pass
        else:
            try:
                logger.warn(
                    "Solicitacao de reset sem discord_user_id vinculado ou bot indisponivel",
                    {"username": username, "ip": ip_address},
                )
            except Exception:
                pass

        # Resposta genérica
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Se o usuário existir, um token de recuperação foi enviado via Discord",
                }
            ),
            200,
        )

    except Exception as e:
        try:
            import traceback

            logger.error(f"Erro ao solicitar reset de senha: {e}")
            logger.error(traceback.format_exc())
        except Exception:
            pass
        return jsonify({"success": False, "error": "Internal server error"}), 500


@auth_bp.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    """Resetar senha usando token de recuperação"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not password_reset_manager or not auth_manager:
            return (
                jsonify(
                    {"success": False, "error": "Password reset system not available"}
                ),
                500,
            )

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "error": "Request body required"}), 400

        token = data.get("token")
        new_password = data.get("new_password")

        if not token or not new_password:
            return (
                jsonify({"success": False, "error": "Token and new password required"}),
                400,
            )

        # Validar token
        token_data = password_reset_manager.validate_token(token)
        if not token_data:
            # Enviar notificação de tentativa inválida
            try:
                ip_address = request.remote_addr or request.environ.get(
                    "HTTP_X_FORWARDED_FOR", "Unknown"
                )
                if discord_webhook:
                    discord_webhook.send_webhook(
                        webhook_name="log-ssm",
                        title="⚠️ Tentativa de Reset com Token Inválido",
                        description="Alguém tentou usar um token de recuperação inválido ou expirado.",
                        color=0xFF0000,  # Vermelho (error)
                        fields=[
                            {
                                "name": "🔑 Token",
                                "value": f"`{token[:16]}...` (inválido/expirado)",
                                "inline": False,
                            },
                            {"name": "🌐 IP", "value": ip_address, "inline": True},
                        ],
                    )
            except Exception as e:
                logger.error(f"Erro ao enviar notificação Discord: {e}")

            return (
                jsonify({"success": False, "error": "Token inválido ou expirado"}),
                400,
            )

        username = token_data["username"]

        # Validar força da senha
        from core.auth.password_handler import PasswordHandler

        password_handler = PasswordHandler()
        is_valid, error_msg = password_handler.validate_password_strength(
            new_password, min_length=8
        )
        if not is_valid:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": error_msg or "Password does not meet requirements",
                    }
                ),
                400,
            )

        # Buscar usuário
        user = auth_manager.user_manager.get_user_by_username(username)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        # Hash da nova senha
        new_password_hash = password_handler.hash_password(new_password)

        # Atualizar senha

        updated_user = auth_manager.user_manager.update_user(
            user["id"],
            password_hash=new_password_hash,
            password_changed=1,
            last_password_change=datetime.now(timezone.utc).isoformat(),
        )

        if not updated_user:
            return (
                jsonify({"success": False, "error": "Failed to update password"}),
                500,
            )

        # Marcar token como usado
        password_reset_manager.mark_token_as_used(token)
        # Enviar notificação de sucesso
        try:
            now = datetime.now()
            date_str = now.strftime("%d/%m/%Y às %H:%M:%S")

            if discord_webhook:
                discord_webhook.send_webhook(
                    webhook_name="log-ssm",
                    title="✅ Password Reset Successfully",
                    description="The admin user password has been changed through the recovery system.",
                    color=0x00FF00,  # Verde (success)
                    fields=[
                        {"name": "👤 User", "value": username, "inline": True},
                        {"name": "⏰ Date/Time", "value": date_str, "inline": True},
                    ],
                )

            logger.info(f"Senha resetada com sucesso para usuário: {username}")
        except Exception as e:
            logger.error(f"Erro ao enviar notificação Discord: {e}")
            # Não falhar a requisição se Discord falhar

        return jsonify({"success": True, "message": "Senha alterada com sucesso"}), 200

    except Exception as e:
        try:
            import traceback

            logger.error(f"Erro ao resetar senha: {e}")
            logger.error(traceback.format_exc())
        except Exception:
            pass
        return jsonify({"success": False, "error": "Internal server error"}), 500


@auth_bp.route("/api/auth/users", methods=["POST"])
@require_auth
@require_admin
def create_user():
    """Criar novo usuário (admin apenas)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not auth_manager:
            return (
                jsonify(
                    {"success": False, "error": "Authentication system not available"}
                ),
                500,
            )

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request body required"}), 400

        username = data.get("username")
        password = data.get("password")
        role = data.get("role", "moderator")
        steam_id = data.get("steam_id")

        if not username or not password:
            return (
                jsonify({"success": False, "error": "Username and password required"}),
                400,
            )

        # Validar senha
        is_valid, error_msg = auth_manager.password_handler.validate_password_strength(
            password
        )
        if not is_valid:
            return (
                jsonify({"success": False, "error": error_msg or "Invalid password"}),
                400,
            )

        # Criar hash da senha
        password_hash = auth_manager.password_handler.hash_password(password)

        role = str(role or "moderator").strip() or "moderator"
        if role == "admin":
            role = "admin_pending"

        # Criar usuário
        user = auth_manager.user_manager.create_user(
            username=username, password_hash=password_hash, role=role, steam_id=steam_id
        )

        if not user:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Username already exists or invalid steam_id",
                    }
                ),
                400,
            )

        # Formatar resposta
        response_data = {
            "id": user["id"],
            "username": user["username"],
            "role": user.get("role", "moderator"),
            "is_active": bool(user.get("is_active", 1)),
            "password_changed": bool(user.get("password_changed", 0)),
            "steam_id": user.get("steam_id"),
            "player_name": user.get("player_name"),
            "created_at": user.get("created_at"),
            "message": "User created. Password must be changed on first login.",
        }

        return jsonify({"success": True, "data": response_data}), 201

    except Exception as e:
        logger.error(f"Erro ao criar usuário: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@auth_bp.route("/api/auth/users", methods=["GET"])
@require_auth
@require_admin
def list_users():
    """Listar todos os usuários (admin apenas)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not auth_manager:
            return (
                jsonify(
                    {"success": False, "error": "Authentication system not available"}
                ),
                500,
            )

        users = auth_manager.user_manager.list_users()

        # Formatar resposta
        users_data = []
        for user in users:
            users_data.append(
                {
                    "id": user["id"],
                    "username": user["username"],
                    "role": user.get("role", "admin"),
                    "is_active": bool(user.get("is_active", 1)),
                    "password_changed": bool(user.get("password_changed", 0)),
                    "steam_id": user.get("steam_id"),
                    "player_name": user.get("player_name"),
                    "player_id": user.get("player_id"),
                    "last_login": user.get("last_login"),
                    "created_at": user.get("created_at"),
                }
            )

        return (
            jsonify(
                {
                    "success": True,
                    "data": {"users": users_data, "total": len(users_data)},
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@auth_bp.route("/api/auth/users/<int:user_id>", methods=["PUT"])
@require_auth
@require_admin
def update_user(user_id):
    """Atualizar usuário (admin apenas)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not auth_manager:
            return (
                jsonify(
                    {"success": False, "error": "Authentication system not available"}
                ),
                500,
            )

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request body required"}), 400

        # Verificar se usuário existe
        user = auth_manager.user_manager.get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        # Preparar atualizações
        updates = {}
        if "is_active" in data:
            updates["is_active"] = 1 if data["is_active"] else 0
        if "role" in data:
            updates["role"] = data["role"]
        if "steam_id" in data:
            updates["steam_id"] = data["steam_id"] if data["steam_id"] else None

        if not updates:
            return (
                jsonify({"success": False, "error": "No valid fields to update"}),
                400,
            )

        # Atualizar usuário
        updated_user = auth_manager.user_manager.update_user(user_id, **updates)

        if not updated_user:
            return jsonify({"success": False, "error": "Failed to update user"}), 500

        # Formatar resposta
        response_data = {
            "id": updated_user["id"],
            "username": updated_user["username"],
            "role": updated_user.get("role", "admin"),
            "is_active": bool(updated_user.get("is_active", 1)),
            "steam_id": updated_user.get("steam_id"),
            "updated_at": updated_user.get("updated_at"),
        }

        return jsonify({"success": True, "data": response_data}), 200

    except Exception as e:
        logger.error(f"Erro ao atualizar usuário: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@auth_bp.route("/api/auth/users/<int:user_id>", methods=["DELETE"])
@require_auth
@require_admin
def delete_user(user_id):
    """Deletar usuário (admin apenas)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not auth_manager:
            return (
                jsonify(
                    {"success": False, "error": "Authentication system not available"}
                ),
                500,
            )

        logger.info(f"Tentando deletar usuário ID: {user_id}")

        # Verificar se usuário existe
        user = auth_manager.user_manager.get_user_by_id(user_id)
        logger.info(f"Resultado da busca do usuário ID {user_id}: {user is not None}")

        if not user:
            logger.warn(f"Usuário ID {user_id} não encontrado")
            return jsonify({"success": False, "error": "User not found"}), 404

        logger.info(
            f"Usuário encontrado: {user.get('username')}, role: {user.get('role')}"
        )

        # Não permitir deletar admin
        if user.get("role") == "admin":
            logger.warn(f"Tentativa de deletar usuário admin ID {user_id}")
            return jsonify({"success": False, "error": "Cannot delete admin user"}), 400

        # Deletar usuário
        success = auth_manager.user_manager.delete_user(user_id)
        logger.info(f"Resultado da deleção do usuário ID {user_id}: {success}")

        if not success:
            return jsonify({"success": False, "error": "Failed to delete user"}), 500

        return jsonify({"success": True, "message": "User deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Erro ao deletar usuário: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@auth_bp.route("/api/auth/users/search-players", methods=["GET"])
@require_auth
@require_admin
def search_players():
    """Buscar players para vincular a moderadores (admin apenas)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    try:
        if not auth_manager:
            return (
                jsonify(
                    {"success": False, "error": "Authentication system not available"}
                ),
                500,
            )

        query = request.args.get("q", "")
        limit = request.args.get("limit", type=int) or 20

        if not query:
            return (
                jsonify({"success": False, "error": "Query parameter 'q' required"}),
                400,
            )

        players = auth_manager.user_manager.search_players(query, limit)

        return (
            jsonify(
                {"success": True, "data": {"players": players, "total": len(players)}}
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Erro ao buscar players: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


