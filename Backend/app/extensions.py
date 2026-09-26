"""
Service Registry / Extensions - Registro central de serviços do SSM Backend.

Este módulo atua como o "container de dependências" da aplicação.
Todos os serviços e managers são registrados aqui durante init_components()
e ficam acessíveis para qualquer Blueprint via get_services().

Isto substitui as variáveis globais que estavam no main.py.
"""

import threading
from typing import Any, Optional


class ServiceRegistry:
    """
    Registro central de todos os serviços e managers do SSM Backend.
    Substitui as ~30 variáveis globais que estavam no main.py.

    Uso nos Blueprints:
        from app.extensions import get_services
        services = get_services()
        result = services.server_manager.is_running()
    """

    def __init__(self):
        # Config e infraestrutura
        self.config: dict = {}
        self.path_helper = None
        self.logger = None
        self.rcon_queue_manager = None

        # Servidor
        self.server_manager = None
        self.restart_scheduler = None
        self.weather_scheduler = None
        self.settings_routine_scheduler = None
        self.rcon_routine_manager = None
        self.rcon_routine_scheduler = None
        self.event_manager = None

        # Discord
        self.discord_webhook = None
        self.discord_bot_service = None

        # Notificações
        self.notification_manager = None

        # Escalabilidade e Identidade
        self.backend_identity = None
        self.owner_manager = None
        self.heartbeat_manager = None
        self.remote_command_handler = None
        self.license_validator = None

        # Processamento de Logs
        self.log_processor = None
        self.online_monitor = None
        self.chat_processor = None
        self.bunker_processor = None
        self.chat_command_monitor = None
        self.fishing_ranking_manager = None

        # Sincronização
        self.squad_sync_service = None
        self.survival_stats_sync_service = None
        self.chest_sync_service = None
        self.chest_inventory_sync_service = None
        self.vehicle_verification_service = None
        self.player_gps_sync_service = None
        self.player_skills_sync_service = None
        self.bank_account_sync_service = None
        self.elevated_users_manager = None
        self.gestao_sync_service = None
        self.scum_logs_cleanup_service = None

        # Rankings
        self.rankings_update_service = None
        self.lockpicking_ranking_service = None
        self.kills_ranking_service = None
        self.snipers_ranking_service = None
        self.bounty_service = None

        # Autenticação
        self.auth_manager = None
        self.password_reset_manager = None

        # Permissões
        self.permission_manager = None
        self.ini_manager = None

    def get_ssm_db_path(self) -> Optional[str]:
        """Obter caminho do banco SSM.db de forma segura."""
        try:
            if self.path_helper and hasattr(self.path_helper, "get_ssm_db_path"):
                return str(self.path_helper.get_ssm_db_path())
        except Exception:
            pass
        return "data/SSM.db"

    def get_scum_db_path(self) -> Optional[str]:
        """Obter caminho do banco SCUM.db de forma segura."""
        try:
            if self.path_helper and hasattr(self.path_helper, "get_scum_db_path"):
                return str(self.path_helper.get_scum_db_path())
        except Exception:
            pass
        return None

    def get_ssm_db_path_for_auth(self) -> str:
        """Obter caminho do banco SSM.db para autenticação."""
        try:
            if self.auth_manager is not None and getattr(self.auth_manager, "db_path", None):
                return str(getattr(self.auth_manager, "db_path"))
        except Exception:
            pass
        return self.get_ssm_db_path() or "data/SSM.db"


# ============================================================================
# SINGLETON
# ============================================================================

_services: Optional[ServiceRegistry] = None
_services_lock = threading.Lock()


def get_services() -> ServiceRegistry:
    """
    Obter o registro de serviços global.
    Inicializa lazy se necessário.
    """
    global _services
    if _services is None:
        with _services_lock:
            if _services is None:
                _services = ServiceRegistry()
    return _services


def init_services() -> ServiceRegistry:
    """
    Inicializar (ou reinicializar) o registro de serviços.
    Chamado pelo App Factory durante a criação do app.
    """
    global _services
    with _services_lock:
        _services = ServiceRegistry()
    return _services
