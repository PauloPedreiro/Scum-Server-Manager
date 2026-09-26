"""
Gerenciador principal de autenticação
"""

from typing import Optional, Dict, Any, Tuple
from .user_manager import UserManager
from .password_handler import PasswordHandler
from .jwt_handler import JWTHandler
from utils.logger import StructuredLogger
from datetime import datetime, timedelta, timezone


class AuthManager:
    """Gerenciador principal de autenticação"""

    def __init__(
        self,
        db_path: str,
        jwt_secret: str,
        jwt_expiration_hours: int = 24,
        default_username: str = "admin",
        default_password: str = "12345678910",
        logger: Optional[StructuredLogger] = None,
    ):
        """
        Inicializa o gerenciador de autenticação

        Args:
            db_path: Caminho do banco SSM.db
            jwt_secret: Chave secreta para JWT
            jwt_expiration_hours: Horas até expiração do token
            default_username: Username padrão do admin
            default_password: Senha padrão do admin
            logger: Logger para logs
        """
        self.logger = logger or StructuredLogger()
        self.db_path = db_path
        self.default_username = default_username
        self.default_password = default_password

        # Inicializar componentes
        jwt_secret_clean = str(jwt_secret or "").strip()
        if not jwt_secret_clean:
            jwt_secret_clean = "ssm-backend-secret-key-change-in-production"

        self.user_manager = UserManager(db_path, logger)
        self.password_handler = PasswordHandler()
        self.jwt_handler = JWTHandler(jwt_secret_clean, jwt_expiration_hours)

        # Criar usuário admin padrão se não existir
        self.ensure_default_admin()

    def ensure_default_admin(self):
        """Garante que o usuário admin padrão existe e com a senha padrão correta se ainda não alterada"""
        try:
            # Verificar se usuário existe
            if not self.user_manager.user_exists(self.default_username):
                # Criar hash da senha padrão
                password_hash = self.password_handler.hash_password(
                    self.default_password
                )

                # Criar usuário admin
                user = self.user_manager.create_user(
                    username=self.default_username,
                    password_hash=password_hash,
                    role="admin_pending",
                )

                if user:
                    self.logger.info(
                        f"Usuário admin padrão criado: {self.default_username}"
                    )
                else:
                    self.logger.error("Erro ao criar usuário admin padrão")
            else:
                # Se o usuário já existe mas ainda não trocou a senha padrão (password_changed == 0)
                user = self.user_manager.get_user_by_username(self.default_username)
                if user and not bool(user.get("password_changed", 0)):
                    stored_hash = user.get("password_hash")
                    if not self.password_handler.verify_password(self.default_password, stored_hash):
                        new_hash = self.password_handler.hash_password(self.default_password)
                        self.user_manager.update_user(user["id"], password_hash=new_hash)
                        self.logger.info(
                            f"Senha padrão do usuário {self.default_username} sincronizada automaticamente com config.json"
                        )

        except Exception as e:
            self.logger.error(f"Erro ao garantir usuário admin padrão: {e}")


    def login(
        self, username: str, password: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Realiza login do usuário

        Args:
            username: Nome de usuário
            password: Senha

        Returns:
            Tupla (success, data, error_message)
            - success: True se login bem-sucedido
            - data: Dados do usuário ou flag must_change_password
            - error_message: Mensagem de erro se falhou
        """
        try:
            # Buscar usuário
            user = self.user_manager.get_user_by_username(username)

            if not user:
                self.logger.warn(f"Usuário não encontrado: {username}")
                return False, None, "Invalid credentials"

            # Verificar se está ativo
            is_active = user.get("is_active", 1)
            if not is_active:
                self.logger.warn(f"Usuário inativo: {username}")
                return False, None, "User is inactive"

            # Verificar senha
            password_hash = user.get("password_hash")
            if not password_hash:
                self.logger.error(f"Usuário sem hash de senha: {username}")
                return False, None, "Invalid credentials"

            password_valid = self.password_handler.verify_password(
                password, password_hash
            )

            if not password_valid:
                self.logger.warn(f"Senha inválida para usuário: {username}")
                return False, None, "Invalid credentials"

            # Verificar se precisa mudar senha
            password_changed = bool(user.get("password_changed", 0))

            if not password_changed:
                # Primeiro login - forçar mudança de senha
                return (
                    True,
                    {
                        "must_change_password": True,
                        "message": "Please change your password",
                    },
                    None,
                )

            # Login normal - atualizar last_login
            self.user_manager.update_user(
                user["id"], last_login=user.get("last_login") or None
            )

            # Gerar token
            token = self.jwt_handler.generate_token(
                user_id=user["id"],
                username=user["username"],
                role=user.get("role", "admin"),
                password_changed=True,
            )

            discord_user_id = str(user.get("discord_user_id") or "").strip()
            role = user.get("role", "admin")
            must_link_discord = bool(role == "admin_pending" or (role == "admin" and not discord_user_id))

            # Atualizar last_login

            self.user_manager.update_user(
                user["id"], last_login=datetime.utcnow().isoformat()
            )

            return (
                True,
                {
                    "token": token,
                    "username": user["username"],
                    "role": role,
                    "must_link_discord": must_link_discord,
                    "expires_in": self.jwt_handler.get_expiration_seconds(),
                },
                None,
            )

        except Exception as e:
            import traceback

            error_traceback = traceback.format_exc()
            self.logger.error(f"Erro no login: {e}")
            self.logger.error(f"Traceback completo: {error_traceback}")
            return False, None, f"Internal server error: {str(e)}"

    def change_password(
        self,
        username: Optional[str],
        current_password: str,
        new_password: str,
        user_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Muda a senha do usuário

        Args:
            username: Nome de usuário (para primeiro login)
            current_password: Senha atual
            new_password: Nova senha
            user_id: ID do usuário (se já autenticado)

        Returns:
            Tupla (success, data, error_message)
        """
        try:
            # Buscar usuário
            if user_id:
                user = self.user_manager.get_user_by_id(user_id)
            elif username:
                user = self.user_manager.get_user_by_username(username)
            else:
                return False, None, "Username or user_id required"

            if not user:
                return False, None, "User not found"

            # Verificar senha atual
            password_hash = user.get("password_hash")
            if not password_hash:
                return False, None, "User has no password hash"

            password_valid = self.password_handler.verify_password(
                current_password, password_hash
            )

            if not password_valid:
                return False, None, "Current password is incorrect"

            # Validar nova senha
            is_valid, error_msg = self.password_handler.validate_password_strength(
                new_password
            )
            if not is_valid:
                return False, None, error_msg or "Invalid password"

            # Gerar novo hash
            new_password_hash = self.password_handler.hash_password(new_password)

            # Atualizar senha

            now = datetime.utcnow().isoformat()

            updated_user = self.user_manager.update_user(
                user["id"],
                password_hash=new_password_hash,
                password_changed=1,
                last_password_change=now,
            )

            if updated_user:
                try:
                    role = str(updated_user.get("role") or "").strip() or "admin"
                    discord_user_id = str(updated_user.get("discord_user_id") or "").strip()
                    if role == "admin" and not discord_user_id:
                        updated_user = self.user_manager.update_user(
                            user["id"], role="admin_pending"
                        )
                except Exception:
                    pass

            if not updated_user:
                return False, None, "Failed to update password"

            # Gerar novo token
            token = self.jwt_handler.generate_token(
                user_id=updated_user["id"],
                username=updated_user["username"],
                role=updated_user.get("role", "admin"),
                password_changed=True,
            )

            discord_user_id = str(updated_user.get("discord_user_id") or "").strip()
            role = updated_user.get("role", "admin")
            must_link_discord = bool(role == "admin_pending" or (role == "admin" and not discord_user_id))

            return (
                True,
                {
                    "token": token,
                    "message": "Password changed successfully",
                    "password_changed": True,
                    "role": role,
                    "must_link_discord": must_link_discord,
                    "expires_in": self.jwt_handler.get_expiration_seconds(),
                },
                None,
            )

        except Exception as e:
            self.logger.error(f"Erro ao mudar senha: {e}")
            return False, None, "Internal server error"

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Valida token JWT e retorna dados do usuário

        Args:
            token: Token JWT

        Returns:
            Dados do usuário ou None se inválido
        """
        try:
            payload = self.jwt_handler.decode_token(token)

            if not payload:
                return None

            # Buscar usuário atualizado
            user = self.user_manager.get_user_by_id(payload.get("user_id"))

            if not user:
                return None

            # Verificar se está ativo
            if not user.get("is_active", 1):
                return None

            # Verificar se senha foi alterada (não permitir tokens antigos)
            password_changed = bool(user.get("password_changed", 0))
            if not password_changed:
                return None
            return user

        except Exception as e:
            self.logger.error(f"Erro ao validar token: {e}")
            return None
