#!/usr/bin/env python3
"""
SCUM Backend - Ponto de entrada principal
"""

import sys
import os

# Auto-delegação para .venv se executado diretamente via python global
if not getattr(sys, "frozen", False) and sys.prefix == sys.base_prefix:
    _venv_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")
    if os.path.exists(_venv_py) and os.path.abspath(sys.executable).lower() != os.path.abspath(_venv_py).lower():
        import subprocess
        _res = subprocess.run([_venv_py, os.path.abspath(__file__)] + sys.argv[1:])
        sys.exit(_res.returncode)

# Compatibilidade com Python 3.13+ onde audioop foi removido da stdlib
if "audioop" not in sys.modules:
    try:
        import audioop  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        import types
        _audioop = types.ModuleType("audioop")
        _audioop.error = Exception
        sys.modules["audioop"] = _audioop

import json
import time
import sqlite3
from core.database.connector import DatabaseConnector
import re
import hashlib
import hmac
import secrets
import threading
import queue
import urllib.request
import urllib.error
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from flask import (  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
    Flask,
    request,
    jsonify,
    Response,
    send_file,
)  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
from flask_cors import CORS  # pyright: ignore[reportMissingModuleSource]
from werkzeug.exceptions import BadRequest  # pyright: ignore[reportMissingImports]
from werkzeug.utils import secure_filename  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
import mimetypes
import copy
import jwt  # pyright: ignore[reportMissingImports, reportMissingModuleSource]


# ============================================================================
# IMPORTS DOS MÓDULOS EXTRAÍDOS (Refatoração Modular)
# ============================================================================
# SQLite Write Queue e WAL - extraídos para utils/sqlite_queue.py
from utils.sqlite_queue import (
    ensure_sqlite_wal as _ensure_sqlite_wal,
    submit_sqlite_write as _submit_sqlite_write,
    SQLiteWriteQueue as _SQLiteWriteQueue,
)

from utils.app_data_dir import get_runtime_data_dir, migrate_legacy_data_dir

# Detectar se está rodando como executável
if getattr(sys, "frozen", False):
    # Rodando como executável (PyInstaller)
    ROOT_DIR = Path(sys._MEIPASS)  # Diretório temporário do PyInstaller
    EXE_DIR = Path(sys.executable).parent  # Diretório onde o .exe está
    IS_EXE = True
else:
    # Rodando como script Python
    ROOT_DIR = Path(__file__).parent
    EXE_DIR = ROOT_DIR
    IS_EXE = False

DATA_DIR = get_runtime_data_dir(is_exe=IS_EXE, exe_dir=EXE_DIR, project_root=ROOT_DIR)
if IS_EXE:
    migrate_legacy_data_dir(EXE_DIR / "data", DATA_DIR)

# Adicionar diretório raiz ao path
sys.path.insert(0, str(ROOT_DIR))

# ============================================================================
# CONFIGURAÇÃO DE SERVIDORES DE LICENCIAMENTO
# ============================================================================
# IMPORTANTE: URLs agora são definidas em core/config/server_urls.py
# Importar do módulo centralizado:
from core.config.server_urls import LICENSE_SERVER_URL, GESTAO_SERVER_URL

# ============================================================================

from core.server_control.server_manager import ServerManager
from core.server_settings.manager import ServerSettingsManager
from core.config.config_manager import ConfigManager
from core.webhooks.manager import WebhooksManager
from core.scheduler.restart_scheduler import RestartScheduler
from core.scheduler.weather_scheduler import WeatherScheduler
from core.scheduler.rcon_routine_manager import RconRoutineManager
from core.scheduler.rcon_routine_scheduler import RconRoutineScheduler
from core.scheduler.attribute_expiration_scheduler import AttributeExpirationScheduler
from core.scheduler.personal_webhook_scheduler import PersonalWebhookScheduler
from core.scheduler.settings_routine_scheduler import SettingsRoutineScheduler

from core.webhooks.discord_webhook import DiscordWebhook
from core.notifications.notification_manager import NotificationManager
from core.logs.scum_logs_cleanup_service import ScumLogsCleanupService
from core.communication.gestao_messages_service import GestaoMessagesService
from core.identity.backend_id import BackendIdentity
from core.identity.owner_manager import OwnerManager
from core.communication.heartbeat_manager import HeartbeatManager
from core.communication.remote_commands import RemoteCommandHandler

# SEGURANÇA: Import crítico - se falhar, aplicação não pode iniciar
try:
    from core.communication.license_validator import (
        LicenseValidator,
        VALIDATION_INTERVAL_SECONDS,
    )

    LICENSE_VALIDATOR_AVAILABLE = True

    # SEGURANÇA: Verificar integridade do módulo (proteção contra modificação/extração)
    try:
        from core.communication.license_validator_integrity import (
            verify_module_integrity,
            verify_module_not_extracted,
        )

        # Verificar integridade
        integrity_ok, integrity_msg = verify_module_integrity()
        if not integrity_ok:
            print(
                "ERRO CRÍTICO DE SEGURANÇA: Integridade do license_validator comprometida!"
            )
            print(f"Detalhes: {integrity_msg}")
            sys.exit(1)

        # Verificar se não foi extraído
        extraction_ok, extraction_msg = verify_module_not_extracted()
        if not extraction_ok:
            print(
                "ERRO CRÍTICO DE SEGURANÇA: Módulo license_validator foi extraído do executável!"
            )
            print(f"Detalhes: {extraction_msg}")
            sys.exit(1)

    except ImportError:
        # SEGURANÇA: BLOQUEAR se módulo de integridade não existir
        # O módulo de integridade é obrigatório para prevenir modificações no código de validação
        print(
            "ERRO CRÍTICO DE SEGURANÇA: Módulo license_validator_integrity não encontrado!"
        )
        print("A aplicação não pode iniciar sem verificação de integridade.")
        print(
            "O módulo de integridade é obrigatório para proteger o sistema de licenciamento."
        )
        sys.exit(1)

except ImportError as e:
    LICENSE_VALIDATOR_AVAILABLE = False
    print("ERRO CRÍTICO: Módulo license_validator.py não encontrado!")
    print("A aplicação não pode iniciar sem o sistema de validação de licença.")
    print(f"Erro: {e}")
    sys.exit(1)
from core.communication.gestao_sync_service import GestaoSyncService
from core.licensing.hardware_fingerprint import HardwareFingerprint
from core.auth.decorators import require_auth, require_admin
from core.logs.log_processor import LogProcessor
from core.logs.online_monitor import OnlinePlayersMonitor
from core.logs.chat_processor import ChatProcessor
from core.reports.player_count_calculator import PlayerCountCalculator
from utils.scum_templates_sync import merge_vehicle_templates_from_scum_db, reset_scum_templates_db


# Integration helpers - extraídos para utils/integration_helpers.py
from utils.integration_helpers import (
    ensure_integration_tables as _ensure_integration_tables,
    integration_key_hash as _integration_key_hash,
    _integration_rate_limit_ok,
    integration_find_idempotent as _integration_find_idempotent,
    integration_log_request as _integration_log_request,
    sign_vehicle_asset as _sign_vehicle_asset,
    is_valid_vehicle_asset_signature as _is_valid_vehicle_asset_signature,
    make_signed_vehicle_asset_url as _make_signed_vehicle_asset_url,
)


def require_integration_key(f):
    """Wrapper retrocompatível - delega para utils.integration_helpers."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            key_plain = (request.headers.get("X-Integration-Key") or "").strip()
            if not key_plain:
                return jsonify({"success": False, "error": "INTEGRATION_KEY_REQUIRED"}), 401

            ssm_db_path, error = _get_ssm_database_path()
            if error:
                return jsonify({"success": False, "error": error}), 500

            key_hash = _integration_key_hash(key_plain)

            from core.shop.db import ssm_tx

            with ssm_tx(ssm_db_path) as conn:
                _ensure_integration_tables(conn)
                cur = conn.execute(
                    """
                    SELECT key_id
                    FROM integration_keys
                    WHERE enabled = 1 AND key_hash = ?
                    LIMIT 1
                    """,
                    (str(key_hash),),
                )
                row = cur.fetchone()
                if not row:
                    return jsonify({"success": False, "error": "INTEGRATION_KEY_INVALID"}), 401

                key_id = str(row[0])
                if not _integration_rate_limit_ok(key_id):
                    return jsonify({"success": False, "error": "RATE_LIMIT"}), 429

                conn.execute(
                    "UPDATE integration_keys SET last_used_at = datetime('now') WHERE key_id = ?",
                    (str(key_id),),
                )

            request.integration_key_id = key_id
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return decorated_function


# from core.logs.bunker_processor import BunkerProcessor  # DESATIVADO temporariamente
from core.logs.chat_command_monitor import ChatCommandMonitor
from core.shop.shop_buy_job_worker import ShopBuyJobWorker
from core.logs.fishing_ranking_manager import FishingRankingManager
from core.permissions.permission_manager import PermissionManager
from core.permissions.ini_manager import IniManager
from core.squads.squad_sync_service import SquadSyncService
from core.survival.survival_stats_sync_service import SurvivalStatsSyncService
from core.survival.player_skills_sync_service import PlayerSkillsSyncService
from core.survival.rankings_update_service import RankingsUpdateService
from core.survival.lockpicking_ranking_service import LockpickingRankingService
from core.survival.kills_ranking_service import KillsRankingService
from core.survival.snipers_ranking_service import SnipersRankingService
from core.chests.chest_sync_service import ChestSyncService
from core.chests.chest_inventory_sync_service import ChestInventorySyncService
from core.vehicles.vehicle_verification_service import VehicleVerificationService
from core.gps.player_gps_sync_service import PlayerGpsSyncService
from core.banking.bank_account_sync_service import BankAccountSyncService
from core.elevated_users.elevated_users_manager import ElevatedUsersManager
from utils.logger import StructuredLogger
from utils.config_path_helper import load_config_with_paths
from utils.scum_db_helper import scum_db_readonly_connection_strict
from utils.scum_attributes_editor import (
    fetch_prisoners as scum_fetch_prisoners,
    resolve_prisoner_identifier as scum_resolve_prisoner_identifier,
    get_prisoner_attributes as scum_get_prisoner_attributes,
    update_prisoner_attributes as scum_update_prisoner_attributes,
    create_scum_db_backup,
)
from typing import Dict, Any, List, Set, Optional, Tuple
import threading
import queue
import re
from version import VERSION

from core.shop.wallet_service import WalletService
from core.shop.scanner_service import ShopScannerService
from core.shop.shop_service import ShopService, OrderCreateItem
from core.shop.delivery_service import ShopDeliveryService
from core.shop.rewards_service import RewardsService


# Sanitize helpers - extraídos para utils/sanitize.py
from utils.sanitize import sanitize_log_message, sanitize_log_data


# ============================================================================
# CRIAÇÃO DO APP FLASK (App Factory)
# ============================================================================
# Criar aplicação Flask via App Factory
# Isto registra automaticamente os Blueprints migrados e o middleware
from app import create_app as _create_app
app = _create_app()

# Variáveis globais
server_manager = None
restart_scheduler = None
weather_scheduler = None
discord_webhook = None
discord_bot_service = None
notification_manager = None
logger = None
config = None
path_helper = None
rcon_routine_manager = None
rcon_routine_scheduler = None
attribute_expiration_scheduler = None
personal_webhook_scheduler = None
settings_routine_scheduler = None

# 🆕 Variáveis de escalabilidade
backend_identity = None
owner_manager = None
heartbeat_manager = None
remote_command_handler = None
license_validator = None

# Sistema de logs
log_processor = None
online_monitor = None
chat_processor = None
bunker_processor = None  # DESATIVADO temporariamente
chat_command_monitor = None
fishing_ranking_manager = None
_fishing_scheduler_stop_event = None
vehicle_verification_service = None
rcon_queue_manager = None
event_manager = None
shop_buy_job_worker = None
shop_delivery_worker = None
player_gps_sync_service = None
player_skills_sync_service = None
bank_account_sync_service = None
elevated_users_manager = None
chest_inventory_sync_service = None

# Serviços de sincronização
squad_sync_service = None
squad_tk_jail_service = None
survival_stats_sync_service = None
chest_sync_service = None
scum_logs_cleanup_service = None

# Serviços de ranking
rankings_update_service = None
lockpicking_ranking_service = None
kills_ranking_service = None
snipers_ranking_service = None

# Sistema de permissões
permission_manager = None
ini_manager = None

# Sistema de autenticação
auth_manager = None
password_reset_manager = None

# Licenciamento (variável de hash de validação)
_validation_hash = None


def get_auth_manager():
    """Função helper para obter auth_manager de forma segura"""
    global auth_manager
    return auth_manager


# Exportar função para uso em decorators
# Isso permite que decorators acessem auth_manager mesmo quando importados antes da inicialização
__all__ = ["get_auth_manager", "auth_manager"]


# Vehicle asset signing - funções já importadas de utils.integration_helpers
# _sign_vehicle_asset, _is_valid_vehicle_asset_signature, _make_signed_vehicle_asset_url
# são aliases retrocompatíveis importados no bloco de integração acima

# Serviço de sincronização com Gestão
gestao_sync_service = None
gestao_messages_service = None

_SURVIVAL_EXCLUDED_METRICS = {"user_profile_id"}


def ensure_default_config_sections(config_path: str, config: Dict[str, Any]) -> bool:
    """
    Garantir que seções padrão existam no config.json
    Adiciona apenas seções que não existem, sem modificar configurações existentes

    Args:
        config_path: Caminho completo para o config.json
        config: Dicionário com a configuração atual

    Returns:
        True se alguma seção foi adicionada, False caso contrário
    """
    try:
        config_modified = False

        # Seção vehicle_registration
        if "vehicle_registration" not in config:
            config["vehicle_registration"] = {
                "show_location": True,
                "description": "Controla se a localização é exibida no embed do Discord para registro de veículos. true = mostra localização, false = oculta (dados continuam sendo salvos no banco normalmente)",
            }
            config_modified = True

        # Seção public
        public_cfg = config.get("public")
        if not isinstance(public_cfg, dict):
            config["public"] = {}
            public_cfg = config.get("public")
            config_modified = True

        if isinstance(public_cfg, dict):
            if "backend_base_url_enabled" not in public_cfg:
                public_cfg["backend_base_url_enabled"] = False
                config_modified = True
            if "backend_base_url" not in public_cfg:
                public_cfg["backend_base_url"] = ""
                config_modified = True
            if "gestao_player_me_path" not in public_cfg:
                public_cfg["gestao_player_me_path"] = "/api/v1/player/me"
                config_modified = True
            if "player_jwt_expiration_hours" not in public_cfg:
                public_cfg["player_jwt_expiration_hours"] = 24
                config_modified = True

        # Seção chest_inventory_sync
        if "chest_inventory_sync" not in config:
            config["chest_inventory_sync"] = {
                "enabled": True,
                "auto_start": True,
                "run_on_startup": True,
                "sync_interval_minutes": 30,
                "batch_size": 25,
                "ttl_minutes": 120,
            }
            config_modified = True

        # Seção bank_account_sync: garantir chaves de reconcile (sem sobrescrever)
        bank_cfg = config.get("bank_account_sync")
        if not isinstance(bank_cfg, dict):
            config["bank_account_sync"] = {}
            bank_cfg = config.get("bank_account_sync")
            config_modified = True

        if isinstance(bank_cfg, dict):
            if "reconcile_enabled" not in bank_cfg:
                bank_cfg["reconcile_enabled"] = True
                config_modified = True
            if "reconcile_interval_minutes" not in bank_cfg:
                bank_cfg["reconcile_interval_minutes"] = 10
                config_modified = True

        # Seção discord_bot: configuracoes opcionais do bot para provisionar canais/webhooks
        discord_bot_cfg = config.get("discord_bot")
        if not isinstance(discord_bot_cfg, dict):
            config["discord_bot"] = {}
            discord_bot_cfg = config.get("discord_bot")
            config_modified = True

        if isinstance(discord_bot_cfg, dict):
            if "bot_token" not in discord_bot_cfg:
                discord_bot_cfg["bot_token"] = ""
                config_modified = True
            if "guild_id" not in discord_bot_cfg:
                discord_bot_cfg["guild_id"] = ""
                config_modified = True
            if "default_category_name" not in discord_bot_cfg:
                discord_bot_cfg["default_category_name"] = "SSM"
                config_modified = True
            if "include_disabled_events" not in discord_bot_cfg:
                discord_bot_cfg["include_disabled_events"] = True
                config_modified = True
            if "validate_existing_urls" not in discord_bot_cfg:
                discord_bot_cfg["validate_existing_urls"] = True
                config_modified = True
            if "repair_invalid_urls" not in discord_bot_cfg:
                discord_bot_cfg["repair_invalid_urls"] = True
                config_modified = True

        # Seção shop_notifications
        shop_notif_cfg = config.get("shop_notifications")
        if not isinstance(shop_notif_cfg, dict):
            config["shop_notifications"] = {}
            shop_notif_cfg = config.get("shop_notifications")
            config_modified = True

        if isinstance(shop_notif_cfg, dict):
            if "welcome_kit_delivered" not in shop_notif_cfg:
                shop_notif_cfg["welcome_kit_delivered"] = "Your kit has been successfully delivered!"
                config_modified = True
            if "items_delivered" not in shop_notif_cfg:
                shop_notif_cfg["items_delivered"] = "Seus itens foram entregues com sucesso!"
                config_modified = True
            if "insufficient_funds" not in shop_notif_cfg:
                shop_notif_cfg["insufficient_funds"] = "Saldo insuficiente! Seu saldo atual: R$ {balance}"
                config_modified = True

        # Seção economy
        if "economy" not in config:
            config["economy"] = {
                "initial_balance": 0
            }
            config_modified = True

        # Seção personal_webhooks
        pw_cfg = config.get("personal_webhooks")
        if not isinstance(pw_cfg, dict):
            config["personal_webhooks"] = {
                "enabled": True,
                "price_points": 500,
                "duration_days": 30,
                "messages": {
                    "system_disabled": "[SSM] O sistema de webhook pessoal de raid esta desativado neste servidor.",
                    "usage_help": "[SSM] Uso correto: /rd <url> ou /rd off. Para ver detalhes digite: /rd info",
                    "no_permission": "[SSM] Voce nao tem permissao para gerenciar webhook pessoal.",
                    "insufficient_funds": "[SSM] Saldo insuficiente. Para cadastrar o webhook sao necessarios {price} pontos. Seu saldo: {balance}.",
                    "disabled_success": "[SSM] Webhook desativado. Sua assinatura continua valida ate {expires_at}.",
                    "disabled_success_lifetime": "[SSM] Webhook pessoal desativado com sucesso.",
                    "registered_success": "[SSM] Webhook cadastrado por {days} dias! Validade: {expires_at}. Descontado {price} pontos.",
                    "registered_success_lifetime": "[SSM] Webhook pessoal cadastrado com sucesso (Plano Vitalicio)!",
                    "updated_success": "[SSM] Webhook atualizado com sucesso! Validade: {expires_at}.",
                    "updated_success_lifetime": "[SSM] Webhook pessoal atualizado com sucesso!",
                    "renewed_success": "[SSM] Assinatura estendida por mais {days} dias! Nova validade: {expires_at}. Descontado {price} pontos.",
                    "status_info": "[SSM] Webhook: {url} | Validade da assinatura: {expires_at} {remaining}.",
                    "status_expired": "[SSM] Webhook: {url} | Assinatura EXPIRADA em: {expires_at}.",
                    "status_no_subscription": "[SSM] Voce nao possui uma assinatura de webhook pessoal ativa.",
                    "invalid_webhook": "[SSM] URL de webhook invalida. Use uma URL do Discord valida.",
                    "database_error": "[SSM] Erro interno ao salvar as configuracoes do webhook.",
                    "auto_renew_success": "🔄 [SSM] Sua assinatura do webhook de raid foi renovada automaticamente por mais {days} dias! Validade: {expires_at}. Descontado {price} pontos.",
                    "auto_renew_failed": "⚠️ [SSM] Sua assinatura do webhook de raid expirou e nao pôde ser renovada automaticamente por falta de saldo (Preço: {price} pontos | Seu saldo: {balance}). Adicione pontos para reativar.",
                    "expiry_warning_3_days": "📅 [SSM] Lembrete: Sua assinatura do webhook de raid expira em 3 dias ({expires_at}). Caso tenha saldo suficiente, ela será renovada automaticamente.",
                    "expiry_warning_1_day": "🚨 [SSM] Atenção: Sua assinatura do webhook de raid expira amanhã ({expires_at}). Verifique se possui saldo suficiente para a renovação automática."
                }
            }
            config_modified = True
        else:
            if "messages" not in pw_cfg or not isinstance(pw_cfg["messages"], dict):
                pw_cfg["messages"] = {}
                config_modified = True
            
            msgs = pw_cfg["messages"]
            new_msgs = {
                "system_disabled": "[SSM] O sistema de webhook pessoal de raid esta desativado neste servidor.",
                "usage_help": "[SSM] Uso correto: /rd <url> ou /rd off. Para ver detalhes digite: /rd info",
                "no_permission": "[SSM] Voce nao tem permissao para gerenciar webhook pessoal.",
                "insufficient_funds": "[SSM] Saldo insuficiente. Para cadastrar o webhook sao necessarios {price} pontos. Seu saldo: {balance}.",
                "disabled_success": "[SSM] Webhook desativado. Sua assinatura continua valida ate {expires_at}.",
                "disabled_success_lifetime": "[SSM] Webhook pessoal desativado com sucesso.",
                "registered_success": "[SSM] Webhook cadastrado por {days} dias! Validade: {expires_at}. Descontado {price} pontos.",
                "registered_success_lifetime": "[SSM] Webhook pessoal cadastrado com sucesso (Plano Vitalicio)!",
                "updated_success": "[SSM] Webhook atualizado com sucesso! Validade: {expires_at}.",
                "updated_success_lifetime": "[SSM] Webhook pessoal atualizado com sucesso!",
                "renewed_success": "[SSM] Assinatura estendida por mais {days} dias! Nova validade: {expires_at}. Descontado {price} pontos.",
                "status_info": "[SSM] Webhook: {url} | Validade da assinatura: {expires_at} {remaining}.",
                "status_expired": "[SSM] Webhook: {url} | Assinatura EXPIRADA em: {expires_at}.",
                "status_no_subscription": "[SSM] Voce nao possui uma assinatura de webhook pessoal ativa.",
                "invalid_webhook": "[SSM] URL de webhook invalida. Use uma URL do Discord valida.",
                "database_error": "[SSM] Erro interno ao salvar as configuracoes do webhook.",
                "auto_renew_success": "🔄 [SSM] Sua assinatura do webhook de raid foi renovada automaticamente por mais {days} dias! Validade: {expires_at}. Descontado {price} pontos.",
                "auto_renew_failed": "⚠️ [SSM] Sua assinatura do webhook de raid expirou e nao pôde ser renovada automaticamente por falta de saldo (Preço: {price} pontos | Seu saldo: {balance}). Adicione pontos para reativar.",
                "expiry_warning_3_days": "📅 [SSM] Lembrete: Sua assinatura do webhook de raid expira em 3 dias ({expires_at}). Caso tenha saldo suficiente, ela será renovada automaticamente.",
                "expiry_warning_1_day": "🚨 [SSM] Atenção: Sua assinatura do webhook de raid expira amanhã ({expires_at}). Verifique se possui saldo suficiente para a renovação automática."
            }
            for k, v in new_msgs.items():
                if k not in msgs:
                    msgs[k] = v
                    config_modified = True

        # Se alguma seção foi adicionada, salvar o config
        if config_modified:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print("OK Seções padrão adicionadas ao config.json")

        return config_modified

    except Exception as e:
        print(f"AVISO Erro ao garantir seções padrão no config.json: {e}")
        return False


def load_config():
    """Carregar configuração"""
    global config, path_helper
    try:
        # Quando executável, usar diretório do .exe para dados
        if IS_EXE:
            config_path = DATA_DIR / "config.json"
        else:
            config_path = ROOT_DIR / "data" / "config.json"

        config, path_helper = load_config_with_paths(str(config_path))

        try:
            resolved_scum_db = (
                path_helper.get_scum_db_path() if path_helper is not None else None
            )
            resolved_ssm_db = (
                path_helper.get_ssm_db_path() if path_helper is not None else None
            )
            (logger.info("Config carregado", {"config_path": str(config_path), "scum_db": resolved_scum_db, "ssm_db": resolved_ssm_db}) if logger else print(f"Config carregado: {config_path} | scum_db={resolved_scum_db} | ssm_db={resolved_ssm_db}"))
        except Exception:
            pass

        # Garantir que seções padrão existam (sem modificar configurações existentes)
        if ensure_default_config_sections(str(config_path), config):
            # Recarregar config caso tenha sido modificado
            config, path_helper = load_config_with_paths(str(config_path))

        # Carregar configuração de webhooks (v1/v2 com migração automática)
        webhooks_path = path_helper.get_application_path(
            "webhooks_file", "data/webhooks.json"
        )

        try:
            from core.webhooks.manager import WebhooksManager

            hooks_manager = WebhooksManager(webhooks_path)
            config["webhooks"] = hooks_manager.load()
        except Exception as e:
            (
                logger.warn(f"Erro ao carregar webhooks.json via WebhooksManager: {e}")
                if logger
                else print(f"Erro ao carregar webhooks.json via WebhooksManager: {e}")
            )
            config["webhooks"] = {}

        # Sanitizar campos legados/deduplicados
        server_cfg = config.get("server")
        if isinstance(server_cfg, dict):
            server_cfg.pop("webhooks", None)

        fishing_cfg = config.get("fishing_ranking")
        if isinstance(fishing_cfg, dict):
            fishing_cfg.pop("scum_db_path", None)
            fishing_cfg.pop("webhook_url", None)

        return config
    except Exception as e:
        (
            logger.error(f"Erro ao carregar configuração: {e}")
            if "logger" in globals()
            else print(f"Erro ao carregar configuração: {e}")
        )
        sys.exit(1)


def init_components(allow_gui_call=False):
    """Inicializar componentes

    Args:
        allow_gui_call: Se True, permite ser chamado do GUI (para integração em thread)
    """
    # SEGURANÇA: Verificar se está sendo chamado durante validação do Panel SSM
    # Se sim, não inicializar componentes (validação deve ser isolada)
    # MAS: Se allow_gui_call=True, permite chamada do GUI para iniciar backend em thread
    if not allow_gui_call:
        import traceback

        stack = traceback.extract_stack()
        # Verificar se alguma função do gui está na stack
        for frame in stack:
            if (
                "gui" in str(frame.filename).lower()
                or "main_window" in str(frame.filename).lower()
            ):
                # Está sendo chamado do Panel SSM durante validação - não inicializar
                raise RuntimeError(
                    "init_components() não pode ser chamado durante validação do Panel SSM. Use apenas os módulos de licenciamento diretamente."
                )

    global server_manager, restart_scheduler, weather_scheduler, discord_webhook, discord_bot_service, notification_manager, logger, config
    global rcon_routine_manager, rcon_routine_scheduler, attribute_expiration_scheduler, personal_webhook_scheduler, settings_routine_scheduler
    global backend_identity, owner_manager, heartbeat_manager, remote_command_handler, license_validator

    global log_processor, online_monitor, chat_processor, bunker_processor, chat_command_monitor, fishing_ranking_manager
    global rcon_queue_manager, event_manager
    global permission_manager, ini_manager
    global squad_sync_service, squad_tk_jail_service, survival_stats_sync_service, chest_sync_service, vehicle_verification_service
    global player_gps_sync_service, player_skills_sync_service, bank_account_sync_service, elevated_users_manager
    global rankings_update_service, lockpicking_ranking_service, kills_ranking_service, snipers_ranking_service
    global auth_manager, password_reset_manager, gestao_sync_service, gestao_messages_service
    global chest_inventory_sync_service
    global scum_logs_cleanup_service
    global shop_buy_job_worker, shop_delivery_worker, _fishing_scheduler_stop_event

    # Carregar configuração
    config = load_config()

    # Inicializar logger
    logger = StructuredLogger(config.get("logging", {}))
    logger.info("SCUM Backend iniciado")

    # Inicializar logger dedicado para Discord e Eventos
    discord_logger = StructuredLogger(
        config=config.get("logging", {}),
        name="discord_events",
        filename="discord_events.log"
    )
    discord_logger.info("Logger de eventos do Discord inicializado")

    try:
        config_dir = None
        if path_helper:
            config_dir = path_helper.get_scum_server_path("config_directory")
        ServerSettingsManager(config_dir or str(EXE_DIR), logger=logger)
    except Exception as e:
        logger.warn(f"Erro ao inicializar ServerSettingsManager: {e}")

    # MELHORIA: Limpar journal órfão do SSM.db antes de iniciar serviços
    # Isso evita bloqueios causados por transações não finalizadas de execuções anteriores
    try:
        from utils.ssm_db_helper import cleanup_ssm_db_journal

        ssm_db_path = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"
        if cleanup_ssm_db_journal(ssm_db_path, logger):
            logger.debug("Verificação de journal do SSM.db concluída")
    except Exception as e:
        logger.warn(
            f"Erro ao verificar journal do SSM.db: {e} - continuando normalmente"
        )

    # Garantir schema do SSM.db (criar tabelas faltantes automaticamente)
    try:
        from utils.database_initializer import initialize_all_tables

        ssm_db_path = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"
        init_result = initialize_all_tables(ssm_db_path, config=config, path_helper=path_helper, logger=logger)
        if not init_result.get("success", False):
            logger.warn(
                f"Inicializacao do SSM.db incompleta: {init_result.get('tables_created')}/{init_result.get('tables_total')} tabelas - {len(init_result.get('errors', []))} erro(s)"
            )
        else:
            logger.info(
                f"SSM.db verificado/inicializado: {init_result.get('tables_created')}/{init_result.get('tables_total')} tabelas"
            )
    except Exception as e:
        logger.warn(f"Erro ao inicializar tabelas do SSM.db: {e} - continuando normalmente")

    # Inicializar ScumDbSharedCopyManager (deve ser antes dos serviços que o usam)
    try:
        from utils.scum_db_shared_copy import get_shared_copy_manager

        scum_db_path = path_helper.get_scum_db_path() if path_helper else None
        shared_copy_manager = get_shared_copy_manager()
        shared_copy_manager.configure(config, scum_db_path=scum_db_path)
        logger.debug("ScumDbSharedCopyManager inicializado")
    except Exception as e:
        logger.warn(
            f"Erro ao inicializar ScumDbSharedCopyManager: {e} - usando conexões diretas"
        )

    # Inicializar ServerManager (usando ConfigPathHelper para eliminar redundância)
    server_manager = ServerManager(config.get("server", {}), path_helper)
    logger.debug("ServerManager inicializado")

    # Inicializar NotificationManager
    scum_config_path = path_helper.get_scum_server_path("config_directory")
    scheduler_times = config.get("scheduler", {}).get("restart_times", [])
    notification_manager = NotificationManager(
        config.get("notifications", {}),
        logger,
        scum_config_path,
        scheduler_times=scheduler_times,
    )
    logger.debug("NotificationManager inicializado")

    # Garantir imediatamente o Notifications.json correto (restart do dia + customs válidas)
    try:
        compile_result = notification_manager.compile_notifications()
        if not compile_result.get("success"):
            logger.warn(
                "Falha ao compilar notificações no startup",
                {"error": compile_result.get("error")},
            )
    except Exception as e:
        logger.warn(f"Erro ao compilar notificações no startup: {e}")

    # Inicializar GestaoMessagesService para consultar mensagens agendadas
    gestao_messages_service = GestaoMessagesService(config, logger)
    logger.debug("GestaoMessagesService inicializado")

    # Inicializar DiscordWebhook (precisa estar antes do RestartScheduler)
    discord_webhook = DiscordWebhook(config, logger)
    logger.debug("DiscordWebhook inicializado")

    # Inicializar ScumLogsCleanupService (limpeza periódica de logs do SCUM)
    try:
        scum_logs_cleanup_service = ScumLogsCleanupService(config, path_helper, logger=logger)
        if scum_logs_cleanup_service.enabled and scum_logs_cleanup_service.auto_start:
            scum_logs_cleanup_service.start()
        logger.debug("ScumLogsCleanupService inicializado")
    except Exception as e:
        scum_logs_cleanup_service = None
        logger.warn(f"ScumLogsCleanupService não disponível: {e}")

    # Inicializar RconLogger e executar auto-limpeza de logs antigos da RCON
    try:
        from utils.rcon_logger import RconLogger
        rcon_logger_inst = RconLogger.get_instance(config=config)
        if rcon_logger_inst.auto_cleanup:
            deleted_f, freed_b = rcon_logger_inst.cleanup_old_logs()
            if deleted_f > 0:
                logger.info(f"Limpeza de logs da RCON: {deleted_f} arquivos removidos ({freed_b / 1024:.1f} KB liberados)")
    except Exception as e:
        logger.warn(f"Erro ao inicializar RconLogger ou limpar logs antigos: {e}")


    # Inicializar RestartScheduler com NotificationManager, GestaoMessagesService e DiscordWebhook
    restart_scheduler = RestartScheduler(
        config,
        server_manager,
        notification_manager,
        logger,
        gestao_messages_service=gestao_messages_service,
        discord_webhook=discord_webhook,
    )
    logger.debug("RestartScheduler inicializado")

    # Adicionar elevated_users_manager ao restart_scheduler (será definido depois da inicialização)
    # Isso será feito após a inicialização do ElevatedUsersManager

    # Inicializar WeatherScheduler
    scum_db_path = path_helper.get_scum_db_path()
    ssm_db_path = path_helper.get_ssm_db_path()
    weather_scheduler = WeatherScheduler(config, logger, scum_db_path, ssm_db_path)
    logger.debug("WeatherScheduler inicializado")

    # Inicializar SettingsRoutineScheduler
    try:
        settings_routine_scheduler = SettingsRoutineScheduler(config, path_helper, logger)
        settings_routine_scheduler.start()
        logger.info("SettingsRoutineScheduler inicializado e iniciado")
    except Exception as e:
        settings_routine_scheduler = None
        logger.error(f"Erro ao inicializar SettingsRoutineScheduler: {e}")


    # Inicializar SquadSyncService
    squad_sync_service = SquadSyncService(config, path_helper, logger)
    logger.debug("SquadSyncService inicializado")

    # Inicializar SquadTKJailService
    try:
        from core.squads.squad_tk_punish_service import SquadTKJailService
        squad_tk_jail_service = SquadTKJailService(config, path_helper, logger)
        squad_tk_jail_service.start()
        logger.info("SquadTKJailService inicializado e iniciado")
    except Exception as e:
        squad_tk_jail_service = None
        logger.error(f"Erro ao inicializar SquadTKJailService: {e}")

    # Inicializar SurvivalStatsSyncService
    survival_stats_sync_service = SurvivalStatsSyncService(config, path_helper, logger)
    logger.debug("SurvivalStatsSyncService inicializado")

    # Inicializar PlayerSkillsSyncService
    player_skills_sync_service = PlayerSkillsSyncService(config, path_helper, logger)
    logger.debug("PlayerSkillsSyncService inicializado")

    # Inicializar BankAccountSyncService
    bank_account_sync_service = BankAccountSyncService(config, path_helper, logger)
    logger.debug("BankAccountSyncService inicializado")

    # Garantir que as tabelas de transações bancárias existam
    try:
        from core.banking.bank_transaction_tables import ensure_bank_transaction_tables

        ssm_db_path = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"
        ensure_bank_transaction_tables(ssm_db_path, logger)
        logger.info("Tabelas de transações bancárias verificadas/criadas")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas de transações bancárias: {e}")

    # Inicializar RankingsUpdateService
    rankings_update_service = RankingsUpdateService(config, path_helper, logger)
    logger.debug("RankingsUpdateService inicializado")

    # Inicializar LockpickingRankingService
    try:
        lockpicking_config = config.get("lockpicking_ranking", {})
        if lockpicking_config.get("enabled", True):
            ssm_db_path = path_helper.get_ssm_db_path()
            webhooks_dict = config.get("webhooks", {})
            webhook_url = webhooks_dict.get("top10_lockpicking") or webhooks_dict.get("top20_lockpicking", "")
            webhooks_path = path_helper.get_application_path("webhooks_file", "data/webhooks.json")
            if not webhook_url:
                logger.debug("Webhook 'top10_lockpicking' não encontrado em webhooks.json")

            min_attempts = lockpicking_config.get("min_attempts", 10)
            top_n = lockpicking_config.get("top_n", 10)
            schedule_time = lockpicking_config.get("schedule_time", "00:00")
            interval_minutes = lockpicking_config.get("interval_minutes", 15)
            send_on_startup = lockpicking_config.get("send_on_startup", True)

            lockpicking_ranking_service = LockpickingRankingService(
                ssm_db_path=ssm_db_path,
                webhook_url=webhook_url,
                webhooks_path=str(webhooks_path),
                logger=logger,
                min_attempts=min_attempts,
                top_n=top_n,
                schedule_time=schedule_time,
                interval_minutes=interval_minutes,
            )
            logger.debug("LockpickingRankingService inicializado")

            lockpicking_start_result = lockpicking_ranking_service.start()
            if lockpicking_start_result.get("success"):
                logger.debug(
                    f"LockpickingRankingService iniciado automaticamente (agendado para {schedule_time})"
                )
                if send_on_startup:
                    logger.info(
                        "Envio de rankings de lockpicking agendado para após servidor iniciar"
                    )
            else:
                logger.debug(
                    f"Falha ao iniciar LockpickingRankingService: {lockpicking_start_result.get('message')}"
                )
        else:
            logger.info("LockpickingRankingService desabilitado no config.json")
            lockpicking_ranking_service = None
    except Exception as e:
        logger.error(f"Erro ao inicializar LockpickingRankingService: {e}")
        lockpicking_ranking_service = None
        logger.debug("LockpickingRankingService não disponível")

    # Inicializar KillsRankingService (Live Top 10 Combat Dashboard: Kills, Snipers, Shame)
    try:
        kills_config = config.get("kills_ranking", {})
        if kills_config.get("enabled", True):
            ssm_db_path = path_helper.get_ssm_db_path()
            webhooks_map = config.get("webhooks", {})
            webhook_url = webhooks_map.get("top10_kills") or webhooks_map.get("top20_kills") or ""
            if not webhook_url:
                logger.debug("Webhook 'top10_kills' não encontrado em webhooks.json")

            top_n = kills_config.get("top_n", 10)
            schedule_time = kills_config.get("schedule_time", "00:00")
            interval_minutes = kills_config.get("interval_minutes", 15)
            send_on_startup = kills_config.get("send_on_startup", True)
            webhooks_path = (
                path_helper.get_application_path("webhooks_file", "data/webhooks.json")
                if path_helper
                else "data/webhooks.json"
            )

            kills_ranking_service = KillsRankingService(
                ssm_db_path=ssm_db_path,
                webhook_url=webhook_url,
                webhooks_path=webhooks_path,
                logger=logger,
                top_n=top_n,
                schedule_time=schedule_time,
                interval_minutes=interval_minutes,
            )
            logger.debug("KillsRankingService inicializado")

            kills_start_result = kills_ranking_service.start()
            if kills_start_result.get("success"):
                logger.debug(
                    f"KillsRankingService iniciado automaticamente (agendado a cada {interval_minutes}m e diariamente às {schedule_time})"
                )
                if send_on_startup:
                    logger.info(
                        "Envio de rankings de combate agendado para após servidor iniciar"
                    )
            else:
                logger.debug(
                    f"Falha ao iniciar KillsRankingService: {kills_start_result.get('message')}"
                )
        else:
            logger.info("KillsRankingService desabilitado no config.json")
            kills_ranking_service = None
    except Exception as e:
        logger.error(f"Erro ao inicializar KillsRankingService: {e}")
        kills_ranking_service = None
        logger.debug("KillsRankingService não disponível")

    # SnipersRankingService descontinuado (integrado diretamente no KillsRankingService)
    snipers_ranking_service = None

    # Inicializar BountyService
    try:
        from core.survival.bounty_service import BountyService
        ssm_db_path = path_helper.get_ssm_db_path()
        bounty_service = BountyService(
            ssm_db_path=ssm_db_path,
            config=config,
            config_path=path_helper.get_config_path() if hasattr(path_helper, "get_config_path") else "data/config.json"
        )
        logger.debug("BountyService inicializado")
    except Exception as e:
        logger.error(f"Erro ao inicializar BountyService: {e}")
        bounty_service = None

    # Inicializar ChestSyncService
    chest_sync_service = ChestSyncService(config, path_helper, logger)
    logger.debug("ChestSyncService inicializado")

    # Inicializar ChestInventorySyncService (inventário de baús)
    try:
        chest_inventory_sync_service = ChestInventorySyncService(config, path_helper, logger)
        logger.debug("ChestInventorySyncService inicializado")
    except Exception as e:
        chest_inventory_sync_service = None
        logger.warn(f"ChestInventorySyncService não disponível: {e}")

    # DiscordWebhook já foi inicializado anteriormente (antes do RestartScheduler)
    # Não recriar aqui para evitar duplicação

    # Disponibilizar webhook para o serviço de baús
    try:
        chest_sync_service.set_discord_webhook(discord_webhook)
    except Exception as exc:
        logger.warn(
            f"Não foi possível associar DiscordWebhook ao ChestSyncService: {exc}"
        )

    # Configurar callbacks do agendador para webhooks
    def scheduler_notification_callback(message: str, data: Dict[str, Any] = None):
        """Callback para notificações do agendador - Atualiza Live Dashboard dinamicamente e registra logs em log-ssm"""
        try:
            # Determinar tipo de evento baseado nos dados ou mensagem
            if data and data.get("notification_type") == "discord_warning":
                # Notificações de aviso de restart (10, 5, 4, 3, 2, 1 min)
                # Opção 3: Atualizar dinamicamente o Live Dashboard Embed sem poluir o canal com cards soltos
                try:
                    if weather_scheduler and hasattr(weather_scheduler, "trigger_immediate_refresh"):
                        weather_scheduler.trigger_immediate_refresh()
                except Exception:
                    pass
                return

            elif "⚠️" in message and (
                "reinicialização" in message.lower() or "restart" in message.lower()
            ):
                event = "restart_warning"  # Fallback para mensagens antigas
            elif "reinicialização agendada" in message.lower():
                event = "restart_scheduled"
            elif "reinicialização iniciada" in message.lower():
                event = "restart_started"
            elif "reinicialização concluída" in message.lower():
                event = "restart_completed"
            elif "falha na reinicialização" in message.lower():
                event = "restart_failed"
            else:
                event = "restart_scheduled"  # Default

            title_map = {
                "restart_warning": "⏳ Restart Warning",
                "restart_scheduled": "📅 Restart Scheduled",
                "restart_started": "🟡 Restart Started",
                "restart_completed": "🟢 Restart Completed",
                "restart_failed": "🔴 Restart Failed",
            }

            color_map = {
                "restart_warning": 0xFFAA00,
                "restart_scheduled": 0x0099FF,
                "restart_started": 0xFFAA00,
                "restart_completed": 0x00FF00,
                "restart_failed": 0xFF0000,
            }

            title = title_map.get(event, f"[SCHEDULER] {event}")
            color = color_map.get(event, 0x0099FF)

            description = (message or "").strip()
            if not description and isinstance(data, dict):
                data_msg = data.get("message")
                if isinstance(data_msg, str):
                    description = data_msg.strip()

            # Disparar atualização imediata do Live Dashboard
            try:
                if weather_scheduler and hasattr(weather_scheduler, "trigger_immediate_refresh"):
                    weather_scheduler.trigger_immediate_refresh()
            except Exception:
                pass

            # Roteamento dos eventos operacionais para o log-ssm (mantendo o canal serverstatus 100% limpo para o Live Embed)
            discord_webhook.send_webhook(
                webhook_name="log-ssm",
                title=title,
                description=description,
                color=color,
                fields=[],
            )
        except Exception as e:
            logger.error(f"Erro no callback de notificação do agendador: {e}")

    # Registrar callback no agendador
    restart_scheduler.add_notification_callback(scheduler_notification_callback)

    # Configurar callbacks do NotificationManager para webhooks
    def notification_callback(event: str, data: Dict[str, Any] = None):
        """Callback para notificações do NotificationManager"""
        try:
            # Enviar notificação para Discord baseada no evento
            # REMOVIDO: restart_notifications_created para evitar duplicação
            # (as notificações Discord são enviadas pelo RestartScheduler)
            if event == "restart_notifications_cleared":
                discord_webhook.send_scheduler_notification(
                    "restart_completed", data or {}
                )
            elif event == "custom_notification_sent":
                discord_webhook.send_webhook(
                    webhook_name="log-ssm",
                    title="💬 Custom Notification Sent",
                    description=data.get("message", ""),
                    color=0x0099FF,  # Azul
                    fields=[],
                )
        except Exception as e:
            logger.error(f"Erro no callback de notificação do NotificationManager: {e}")

    # Registrar callback no NotificationManager
    notification_manager.add_notification_callback(notification_callback)

    # Iniciar agendador se configurado
    scheduler_config = config.get("scheduler", {})
    if scheduler_config.get("enabled", True) and scheduler_config.get(
        "auto_start", True
    ):
        start_result = restart_scheduler.start()
        if start_result.get("success"):
            logger.debug("Agendador iniciado automaticamente")
        else:
            logger.warn(
                f"Falha ao iniciar agendador automaticamente: {start_result.get('message')}"
            )

    # Iniciar agendador climático se configurado
    weather_scheduler_config = config.get("weather_scheduler", {})
    if weather_scheduler_config.get("enabled", True) and weather_scheduler_config.get(
        "auto_start", True
    ):
        weather_start_result = weather_scheduler.start()
        if weather_start_result.get("success"):
            logger.debug("Agendador climático iniciado automaticamente")
        else:
            logger.warn(
                f"Falha ao iniciar agendador climático automaticamente: {weather_start_result.get('message')}"
            )

    # NÃO iniciar serviços de sincronização aqui - serão agendados para depois do servidor Flask iniciar
    # Isso evita travar a inicialização do backend fazendo todas as sincronizações antes de iniciar
    logger.debug(
        "Serviços de sincronização prontos (serão iniciados após servidor Flask iniciar)"
    )

    # 🆕 INICIALIZAR SISTEMAS DE ESCALABILIDADE

    try:
        # Inicializar BackendIdentity
        backend_identity = BackendIdentity()
        backend_id = backend_identity.get_backend_id()
        masked_id = (
            f"{backend_id[:8]}****{backend_id[-4:]}" if len(backend_id) > 12 else "****"
        )
        logger.info(f"Backend ID: {masked_id}")

        # Inicializar OwnerManager
        owner_manager = OwnerManager()
        logger.debug("OwnerManager inicializado")

        # Inicializar HeartbeatManager
        heartbeat_manager = HeartbeatManager(config, logger, backend_identity)
        heartbeat_manager.start_heartbeat()
        logger.debug("Sistema de heartbeat inicializado")

        # Inicializar RemoteCommandHandler
        remote_command_handler = RemoteCommandHandler(
            logger=logger,
            notification_manager=notification_manager,
            server_manager=server_manager,
            scheduler=restart_scheduler,
        )
        logger.debug("RemoteCommandHandler inicializado")

        # Inicializar LicenseValidator
        # SEGURANÇA: Verificar se módulo está disponível
        if not LICENSE_VALIDATOR_AVAILABLE:
            logger.critical(
                "ERRO CRÍTICO: LicenseValidator não disponível - aplicação não pode continuar"
            )
            raise RuntimeError(
                "LicenseValidator é obrigatório para segurança da aplicação"
            )

        license_validator = LicenseValidator(
            config, logger, backend_identity, path_helper
        )
        logger.debug("LicenseValidator inicializado")

        # Função auxiliar para processar resposta do servidor de licenciamento
        def process_license_response(
            response: Dict[str, Any],
        ) -> Tuple[bool, Optional[str], Optional[str]]:
            """
            Processar resposta do servidor de licenciamento
            Retorna: (is_valid: bool, message: str, reason: Optional[str])

            SEGURANÇA: Distingue entre erros de rede (permitem grace period)
            e licença inválida (bloqueiam imediatamente)
            """
            # Verificar resposta (MESMA LÓGICA DA GUI)
            status_code = response.get("status_code", 200)
            has_error = response.get("error") is not None
            success = response.get("success")
            error_type = response.get(
                "error_type"
            )  # Tipo de erro (Timeout, ConnectionError, etc)

            # PRIORIDADE 1: status_code = 0 = erro de conexão/rede
            # Este é um erro de rede (timeout, connection error, etc)
            # Diferente de licença inválida - pode permitir grace period se cache válido
            if status_code == 0:
                error_msg = response.get(
                    "error", "Erro de conexão com servidor de licenciamento"
                )
                logger.warn(
                    f"Erro de rede detectado na validação: {error_msg} (tipo: {error_type})"
                )
                # Retornar network_error para permitir tratamento diferenciado (grace period)
                return False, error_msg, "network_error"

            # PRIORIDADE 2: success = False = erro (pode ser rede ou servidor)
            # Se não tem status_code ou status_code não é 0, tratar como erro de servidor
            if success is False:
                error_msg = response.get("error", "Erro na validação")
                logger.warn(
                    f"Erro na resposta do servidor (success=False): {error_msg}"
                )
                # Se status_code existe e não é 0, não é erro de rede
                if status_code and status_code != 0:
                    return False, error_msg, "server_error"
                else:
                    return False, error_msg, "network_error"

            # PRIORIDADE 3: campo 'error' presente = erro
            # Verificar se é erro de rede (status_code = 0) ou erro de servidor
            if has_error:
                error_msg = response.get("error", "Erro na validação")
                logger.warn(f"Campo 'error' presente na resposta: {error_msg}")
                if status_code == 0:
                    return False, error_msg, "network_error"
                else:
                    return False, error_msg, "server_error"

            # PRIORIDADE 4: status_code != 200 = erro de servidor (não rede)
            if status_code != 200:
                error_msg = (
                    f"Resposta inesperada do servidor (status_code={status_code})"
                )
                logger.warn(f"Status code inválido: {status_code}")
                # Status code diferente de 200 mas existe = erro de servidor (não rede)
                return False, error_msg, "server_error"

            # PRIORIDADE 5: Verificar campo 'valid'
            is_valid = response.get("valid")
            if is_valid is None:
                error_msg = "Resposta do servidor não contém campo 'valid'"
                logger.warn(
                    f"Resposta inválida: campo 'valid' ausente. Resposta completa: {response}"
                )
                return False, error_msg, "server_error"

            # PRIORIDADE 6: Verificar se licença é válida
            if is_valid is True:
                return True, "Equipamento liberado", None
            else:
                # Licença inválida - SEMPRE bloquear (não é erro de rede)
                reason = response.get("reason", "unknown")
                message = response.get("message", "Licença inválida")
                logger.error(f"Licença inválida - Reason: {reason}, Message: {message}")
                # Retornar reason específica para permitir tratamento diferenciado
                return False, message, reason

        # Função para enviar notificação de validação para Discord
        def send_license_validation_notification(
            validation_type: str,  # "initial" ou "periodic"
            is_valid: bool,
            message: str = None,
            reason: str = None,
        ):
            """Enviar notificação de validação de licença para Discord (desativada no Open Source)"""
            return True

        _validation_hash = None

        # Função para validar licença (MESMO PROCESSO QUE GUI)
        # Usada tanto para validação inicial quanto periódica
        def validate_license_simple(validation_type: str = "initial"):
            """
            Validar licença usando o mesmo processo que a GUI usa
            Retorna: (is_valid: bool, message: str, reason: Optional[str])

            Args:
                validation_type: "initial" ou "periodic" - usado apenas para logs
            """
            return True, "Licença liberada (Open Source / Standalone)", None

        # VALIDAÇÃO INICIAL - Ao iniciar o backend
        # SEGURANÇA: URL é hardcoded para https://scumsm.com
        licensing_config = config.get("licensing", {})
        # Segurança: validação inicial sempre habilitada (ignorar config)
        server_url = LICENSE_SERVER_URL
        logger.debug(f"Validando licença inicial com servidor: {server_url}")

        is_valid, message, reason = validate_license_simple(validation_type="initial")

        if not is_valid:
            logger.critical(f"Validação inicial falhou: {message}")
            if reason:
                logger.critical(f"Motivo: {reason}")

            # Enviar notificação de falha para Discord
            send_license_validation_notification(
                validation_type="initial",
                is_valid=False,
                message=message,
                reason=reason,
            )

            logger.critical("Encerrando SSM Backend...")
            time.sleep(2)
            os._exit(1)
        else:
            logger.info(f"Validação inicial concluída com sucesso: {message}")

            # Enviar notificação de sucesso para Discord
            send_license_validation_notification(
                validation_type="initial", is_valid=True, message=message
            )

        # VALIDAÇÃO PERIÓDICA - A cada 4 horas (14400 segundos)
        # Constante importada de license_validator.py (única fonte da verdade)
        # Este valor é hardcoded para prevenir manipulação via config.json

        def periodic_license_check():
            """Thread que valida licença periodicamente com retry inteligente"""
            import time  # Fix for NameError (free variable)

            # Formatar intervalo para exibição (horas ou minutos)
            if VALIDATION_INTERVAL_SECONDS >= 3600:
                interval_str = f"{VALIDATION_INTERVAL_SECONDS // 3600} horas"
            else:
                interval_str = f"{VALIDATION_INTERVAL_SECONDS // 60} minutos"
            logger.info(
                f"Thread de validação periódica iniciada - próxima validação em {interval_str}"
            )

            consecutive_failures = 0  # Contador de falhas consecutivas
            max_consecutive_failures = 3  # Máximo de falhas antes de bloquear

            while True:
                try:
                    # MELHORIA: Retry inteligente - intervalos menores após falhas
                    if consecutive_failures == 0:
                        # Primeira tentativa ou após sucesso: aguardar 4 horas
                        wait_seconds = VALIDATION_INTERVAL_SECONDS
                        if wait_seconds >= 3600:
                            wait_str = f"{wait_seconds // 3600} horas"
                        else:
                            wait_str = f"{wait_seconds // 60} minutos"
                    elif consecutive_failures == 1:
                        # Primeira falha: tentar novamente em 15 minutos
                        wait_seconds = 900  # 15 minutos
                        wait_str = "15 minutos"
                    elif consecutive_failures == 2:
                        # Segunda falha: tentar novamente em 30 minutos
                        wait_seconds = 1800  # 30 minutos
                        wait_str = "30 minutos"
                    else:
                        # Terceira falha: tentar novamente em 1 hora
                        wait_seconds = 3600  # 1 hora
                        wait_str = "1 hora"

                    logger.info(
                        f"Aguardando {wait_str} para próxima validação... (falhas consecutivas: {consecutive_failures}/{max_consecutive_failures})"
                    )
                    time.sleep(wait_seconds)

                    # Executar validação usando O MESMO PROCESSO da validação inicial
                    logger.info("Executando validação periódica de licença...")

                    # Usar a mesma função da validação inicial
                    is_valid, message, reason = validate_license_simple(
                        validation_type="periodic"
                    )

                    if not is_valid:
                        consecutive_failures += 1
                        logger.warn(
                            f"Validação periódica falhou (falhas consecutivas: {consecutive_failures}/{max_consecutive_failures})"
                        )

                        # SEGURANÇA: Distinguir entre erro de rede e licença inválida
                        # Grace period APENAS para erros de rede (se cache válido)
                        if reason == "network_error":
                            # Erro de rede: verificar se cache ainda válido para grace period
                            try:
                                from core.licensing.license_cache import LicenseCache
                                from utils.config_path_helper import ConfigPathHelper

                                # Inicializar cache
                                path_helper = ConfigPathHelper(config)
                                db_path = path_helper.get_ssm_db_path()
                                license_cache = LicenseCache(
                                    data_dir=str(DATA_DIR) if IS_EXE else "data",
                                    db_path=db_path,
                                    logger=logger,
                                )

                                # Verificar se cache ainda válido (< 4 horas)
                                cache_ttl = 14400  # 4 horas
                                if license_cache.is_validation_cached(cache_ttl):
                                    logger.warn(
                                        f"Erro de rede, mas cache ainda válido. "
                                        f"Permitindo continuar operação. Nova tentativa em {wait_str}."
                                    )
                                    logger.warn(f"Detalhes do erro: {message}")
                                    # Resetar contador de falhas (cache válido = não é falha real)
                                    consecutive_failures = 0
                                    continue
                                else:
                                    # Cache expirado + erro de rede = não pode continuar
                                    logger.error(
                                        f"Erro de rede E cache expirado. "
                                        f"Não é possível continuar sem validação válida."
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Erro ao verificar cache para grace period: {e}"
                                )
                                # Em caso de erro, continuar contagem de falhas

                        # Verificar se excedeu máximo de falhas consecutivas
                        if consecutive_failures >= max_consecutive_failures:
                            # Múltiplas falhas consecutivas: bloquear
                            logger.critical(
                                f"Validação periódica falhou {consecutive_failures} vezes consecutivas. "
                                f"Bloqueando backend."
                            )
                            if reason:
                                logger.critical(f"Motivo: {reason}")
                            if message:
                                logger.critical(f"Mensagem: {message}")

                            # Enviar notificação de falha para Discord
                            send_license_validation_notification(
                                validation_type="periodic",
                                is_valid=False,
                                message=message or "Licença inválida",
                                reason=reason or "unknown",
                            )

                            logger.critical("Encerrando SSM Backend...")

                            # Parar schedulers
                            if restart_scheduler:
                                try:
                                    restart_scheduler.stop()
                                    logger.info("Restart scheduler parado")
                                except Exception as e:
                                    logger.error(
                                        f"Erro ao parar restart scheduler: {e}"
                                    )

                            if weather_scheduler:
                                try:
                                    weather_scheduler.stop()
                                    logger.info("Weather scheduler parado")
                                except Exception as e:
                                    logger.error(
                                        f"Erro ao parar weather scheduler: {e}"
                                    )

                            time.sleep(2)
                            os._exit(1)
                        else:
                            # Ainda há tentativas: continuar loop com intervalo menor
                            logger.warn(
                                f"Falha {consecutive_failures}/{max_consecutive_failures}. Tentando novamente em {wait_str}."
                            )
                            continue
                    else:
                        # Sucesso: resetar contador de falhas
                        if consecutive_failures > 0:
                            logger.info(
                                f"Validação periódica bem-sucedida após {consecutive_failures} falha(s). Contador resetado."
                            )
                        consecutive_failures = 0
                        logger.info("Validação periódica concluída com sucesso")

                        # Enviar notificação de sucesso para Discord
                        send_license_validation_notification(
                            validation_type="periodic",
                            is_valid=True,
                            message=message
                            or "Validação periódica realizada com sucesso",
                        )

                except Exception as e:
                    logger.error(f"Erro na validação periódica: {e}")
                    logger.critical(
                        "Encerrando SSM Backend devido a erro na validação..."
                    )
                    time.sleep(2)
                    os._exit(1)

        # SEGURANÇA: Sempre iniciar thread de validação periódica se server_url estiver configurado (ignorar enabled)
        if server_url and server_url.strip():
            import threading

            validation_thread = threading.Thread(
                target=periodic_license_check,
                daemon=True,
                name="LicenseValidationThread",
            )
            validation_thread.start()
            # Formatar intervalo para exibição (horas ou minutos)
            if VALIDATION_INTERVAL_SECONDS >= 3600:
                interval_display = f"{VALIDATION_INTERVAL_SECONDS // 3600} horas"
            else:
                interval_display = f"{VALIDATION_INTERVAL_SECONDS // 60} minutos"
            logger.info(
                f"Validação periódica de licença iniciada (verificação a cada {interval_display} usando o mesmo processo da validação inicial)"
            )
            logger.info(
                f"Thread de validação: {validation_thread.name} (ativa: {validation_thread.is_alive()})"
            )
        else:
            logger.warn("Validação periódica não iniciada - server_url não configurado")

        logger.debug("Sistema de escalabilidade inicializado com sucesso")

    except Exception as e:
        logger.error(f"Erro ao inicializar sistema de escalabilidade: {e}")
        logger.warn(
            "Sistema de escalabilidade não disponível - funcionando em modo individual"
        )

    # Inicializar sistema de processamento de logs
    # SEGURANÇA: Verificar se validação de licença foi concluída antes de inicializar componentes
    if not license_validator:
        logger.critical(
            "ERRO CRÍTICO: LicenseValidator não inicializado - componentes não podem ser inicializados"
        )
        raise RuntimeError("LicenseValidator é obrigatório para segurança da aplicação")

    # Verificar se licenciamento está habilitado e válido
    if license_validator.licensing_enabled and not license_validator.is_valid:
        logger.critical(
            "ERRO CRÍTICO: Tentativa de inicializar componentes sem validação de licença válida"
        )
        raise RuntimeError(
            "Componentes não podem ser inicializados sem validação de licença válida"
        )

    try:
        logger.debug("Inicializando sistema de processamento de logs...")
        logs_directory = path_helper.get_scum_logs_directory()
        ssm_db_path = path_helper.get_ssm_db_path()
        log_processor = LogProcessor(
            log_directory=logs_directory,
            db_path=ssm_db_path,
            discord_webhook=discord_webhook,
            discord_bot_service=discord_bot_service,
            logger=logger,
        )

        # Iniciar processamento em thread separada para não bloquear o Flask
        def start_log_processing():
            try:
                log_processor.start_processing(real_time=True)
            except Exception as e:
                logger.error(f"Erro no processamento de logs: {e}")
                import traceback

                traceback_str = traceback.format_exc()
                logger.error(f"Traceback completo: {traceback_str}")
                error_str = str(e).lower()
                if "main thread" in error_str or "main loop" in error_str:
                    logger.warn(
                        "Erro de threading detectado - pode indicar problema de inicialização, mas não afeta validação de licença"
                    )

        # Garantir que threading está disponível
        import threading as threading_module

        log_thread = threading_module.Thread(target=start_log_processing, daemon=True)
        log_thread.start()

        logger.debug("Sistema de processamento de logs iniciado em thread separada")

        # Inicializar monitor de jogadores online
        logger.debug("Inicializando monitor de jogadores online...")
        gameplay_logs_path = path_helper.get_scum_logs_directory()
        online_monitor = OnlinePlayersMonitor(
            log_processor.db_manager, gameplay_logs_path=gameplay_logs_path
        )
        online_monitor.start_monitoring()
        logger.debug("Monitor de jogadores online iniciado")

        # Inicializar sistema de monitoramento de chat
        logger.debug("Inicializando sistema de monitoramento de chat...")
        chat_config = config.get("chat_monitoring", {})
        if chat_config.get("enabled", True):
            webhook_config = config.get("webhooks", {})
            chat_processor = ChatProcessor(webhook_config, logger, chat_config=chat_config)

        # Inicializar processador de bunkers
        try:
            bunker_processor = getattr(log_processor, "bunker_processor", None)
            if bunker_processor:
                logger.info("Processador de bunkers inicializado")
            else:
                logger.warn("Processador de bunkers não disponível no LogProcessor")
        except Exception as e:
            bunker_processor = None
            logger.warn(f"Processador de bunkers não disponível: {e}")

        # Inicializar monitor de comandos de chat
        logger.debug("Inicializando monitor de comandos de chat...")
        scum_db_path = path_helper.get_scum_db_path()
        ssm_db_path = path_helper.get_ssm_db_path()
        chat_command_monitor = ChatCommandMonitor(
            logger,
            scum_db_path,
            discord_bot_service=discord_bot_service,
            ssm_db_path=ssm_db_path,
        )
        chat_command_monitor.start_monitoring()
        logger.debug("Monitor de comandos de chat iniciado")

        # Inicializar RconQueueManager
        logger.debug("Inicializando RconQueueManager...")
        from core.rcon_queue_manager import RconQueueManager
        rcon_queue_manager = RconQueueManager.get_instance(logger=logger)
        rcon_queue_manager.start()
        logger.debug("RconQueueManager iniciado com sucesso")

        # Inicializar RconRoutineManager e Scheduler
        logger.debug("Inicializando RconRoutineManager...")
        rcon_routines_path = path_helper.get_application_path("rcon_routines", "data/rcon_routines.json")
        rcon_routine_manager = RconRoutineManager(str(rcon_routines_path), logger=logger)
        
        logger.debug("Inicializando RconRoutineScheduler...")
        rcon_routine_scheduler = RconRoutineScheduler(rcon_routine_manager, rcon_queue_manager, logger=logger, db_manager=log_processor.db_manager)
        rcon_routine_scheduler.start()
        logger.debug("RconRoutineScheduler iniciado com sucesso")

        logger.debug("Inicializando AttributeExpirationScheduler...")
        attribute_expiration_scheduler = AttributeExpirationScheduler(ssm_db_path, scum_db_path, logger=logger)
        attribute_expiration_scheduler.start()
        logger.debug("AttributeExpirationScheduler iniciado com sucesso")

        logger.debug("Inicializando PersonalWebhookScheduler...")
        personal_webhook_scheduler = PersonalWebhookScheduler(ssm_db_path, logger=logger)
        personal_webhook_scheduler.start()
        logger.debug("PersonalWebhookScheduler iniciado com sucesso")

        # Inicializar EventManager
        logger.debug("Inicializando EventManager...")
        from core.events.event_manager import EventManager
        event_manager = EventManager.get_instance(ssm_db_path=ssm_db_path, logger=discord_logger)
        event_manager.start()
        logger.debug("EventManager iniciado com sucesso")

        # Inicializar worker de jobs de compra (/buy)
        logger.debug("Inicializando worker de jobs de compra (/buy)...")
        shop_buy_job_worker = ShopBuyJobWorker(ssm_db_path, logger=logger)
        shop_buy_job_worker.start()
        logger.debug("Worker de jobs de compra iniciado")

        # Inicializar worker de entregas de shop (RCON/tempo real)
        logger.debug("Inicializando worker de entregas de shop...")
        from core.shop.delivery_service import ShopDeliveryWorker
        shop_delivery_worker = ShopDeliveryWorker(
            ssm_db_path=ssm_db_path,
            scum_db_path=scum_db_path,
            logger=logger,
            poll_interval_seconds=10.0
        )
        shop_delivery_worker.start()
        logger.debug("Worker de entregas de shop iniciado")


        # Inicializar sistema de ranking de pescadores
        logger.debug("Inicializando sistema de ranking de pescadores...")
        fishing_config = config.get("fishing_ranking", {})
        if fishing_config.get("enabled", False):
            try:
                # Usar helper para obter caminho do SCUM.db
                fishing_config["scum_db_path"] = path_helper.get_scum_db_path()

                # Combinar configuração com webhook
                try:
                    webhooks_path = path_helper.get_application_path(
                        "webhooks_file", "data/webhooks.json"
                    )
                    try:
                        from core.webhooks.manager import WebhooksManager

                        fishing_hooks_manager = WebhooksManager(webhooks_path)
                        fishing_hooks = fishing_hooks_manager.load()
                        fishing_config["webhook_url"] = (
                            fishing_hooks.get("fishing_ranking", "")
                            if isinstance(fishing_hooks, dict)
                            else ""
                        )
                    except Exception:
                        webhooks_config = json.load(open(webhooks_path))
                        fishing_config["webhook_url"] = webhooks_config.get(
                            "fishing_ranking", ""
                        )
                except Exception as e:
                    logger.error(f"Erro ao carregar webhooks: {e}")
                    fishing_config["webhook_url"] = ""
                fishing_ranking_manager = FishingRankingManager(
                    fishing_config, path_helper
                )
                logger.info("FishingRankingManager criado com sucesso")

                # Armazenar referência local para usar no closure
                manager_ref = fishing_ranking_manager

                # Iniciar scheduler do fishing ranking em thread separada
                def start_fishing_scheduler():
                    try:
                        logger.info("Thread do scheduler de fishing ranking iniciada")
                        import schedule  # pyright: ignore[reportMissingImports]
                        import traceback

                        logger.info("Biblioteca schedule importada com sucesso")

                        # Criar instância própria do scheduler (como outros schedulers fazem)
                        fishing_scheduler = schedule.Scheduler()
                        logger.info("Instância do scheduler criada")

                        # Usar referência capturada do closure
                        manager = manager_ref

                        if manager is None:
                            logger.error(
                                "ERRO CRÍTICO: fishing_ranking_manager não está disponível na thread!"
                            )
                            return

                        logger.info(
                            f"FishingRankingManager verificado na thread: {type(manager).__name__}"
                        )

                        # Executar ranking ao iniciar se configurado
                        run_on_startup = fishing_config.get("run_on_startup", False)
                        logger.info(f"Configuração run_on_startup: {run_on_startup}")

                        if run_on_startup:
                            logger.info(
                                "Executando ranking de pescadores ao iniciar..."
                            )
                            try:
                                manager.generate_daily_ranking()
                                logger.info(
                                    "Ranking de pescadores executado com sucesso ao iniciar"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Erro ao executar ranking ao iniciar: {e}"
                                )
                                logger.error(f"Traceback: {traceback.format_exc()}")

                        # Agendar execução periódica e diária
                        interval_minutes = max(1, int(fishing_config.get("interval_minutes", 15)))
                        schedule_time = fishing_config.get("schedule_time", "10:00")
                        logger.info(f"Agendando fishing ranking a cada {interval_minutes}m e diariamente às {schedule_time}")

                        # Criar função wrapper para garantir que manager está disponível
                        def execute_ranking():
                            try:
                                # Usar referência do closure externo
                                current_manager = manager_ref
                                if current_manager:
                                    logger.info("Sincronizando fishing ranking agendado...")
                                    current_manager.generate_daily_ranking()
                                else:
                                    logger.error(
                                        "ERRO: manager não disponível na execução agendada"
                                    )
                            except Exception as e:
                                logger.error(f"Erro ao sincronizar ranking agendado: {e}")
                                import traceback

                                logger.error(f"Traceback: {traceback.format_exc()}")

                        fishing_scheduler.every(interval_minutes).minutes.do(
                            execute_ranking
                        )
                        fishing_scheduler.every().day.at(schedule_time).do(
                            execute_ranking
                        )

                        logger.info(
                            f"Scheduler de fishing ranking agendado a cada {interval_minutes}m e às {schedule_time}"
                        )


                        # Verificar jobs agendados imediatamente
                        try:
                            jobs = fishing_scheduler.jobs
                            logger.info(f"Jobs agendados no scheduler: {len(jobs)}")
                            for job in jobs:
                                logger.info(
                                    f"  - Job: {job.job_func.__name__ if hasattr(job.job_func, '__name__') else 'anonymous'}, Próxima execução: {job.next_run}"
                                )
                        except Exception as e:
                            logger.warn(f"Erro ao verificar jobs: {e}")

                        logger.info("Iniciando loop do scheduler...")

                        # Loop do scheduler
                        iteration = 0
                        last_log_time = time.time()
                        logger.info(
                            "Loop do scheduler de fishing ranking iniciado - verificando a cada minuto"
                        )
                        logger.info("Primeira iteração do loop iniciando agora...")

                        global _fishing_scheduler_stop_event
                        _fishing_scheduler_stop_event = threading.Event()

                        while not _fishing_scheduler_stop_event.is_set():
                            try:
                                iteration += 1
                                current_time = time.time()

                                # Log na primeira iteração
                                if iteration == 1:
                                    logger.info(
                                        "Primeira iteração do loop executada com sucesso"
                                    )

                                # Log a cada 5 minutos para confirmar que está rodando
                                if current_time - last_log_time >= 300:  # 5 minutos
                                    logger.info(
                                        f"Scheduler de fishing ranking rodando (iteração {iteration}, há {iteration} minutos)"
                                    )
                                    last_log_time = current_time

                                    # Verificar jobs novamente
                                    try:
                                        if hasattr(schedule, "get_jobs"):
                                            jobs = schedule.get_jobs()
                                            logger.info(f"Jobs agendados: {len(jobs)}")
                                            for job in jobs:
                                                logger.info(
                                                    f"  - Próxima execução: {job.next_run}"
                                                )
                                    except:
                                        pass

                                # Executar jobs pendentes usando a instância do scheduler
                                fishing_scheduler.run_pending()

                                # Log detalhado a cada 10 iterações
                                if iteration % 10 == 0:
                                    try:
                                        jobs = fishing_scheduler.jobs
                                        logger.info(
                                            f"Verificação {iteration}: {len(jobs)} job(s) agendado(s)"
                                        )
                                        for job in jobs:
                                            logger.info(
                                                f"  - Próxima execução: {job.next_run}"
                                            )
                                    except:
                                        pass

                                # Log a cada minuto nas primeiras 5 iterações
                                if iteration <= 5:
                                    logger.info(
                                        f"Loop executado (iteração {iteration}) - próximo check em 60s"
                                    )

                                # Sleep responsivo de 60 segundos com suporte a interrupção rápida
                                _fishing_scheduler_stop_event.wait(60)

                            except KeyboardInterrupt:
                                logger.info("Scheduler de fishing ranking interrompido")
                                break
                            except Exception as e:
                                logger.error(
                                    f"Erro no loop do scheduler (iteração {iteration}): {e}"
                                )
                                logger.error(f"Traceback: {traceback.format_exc()}")
                                _fishing_scheduler_stop_event.wait(60)  # Continuar mesmo com erro

                    except ImportError as e:
                        logger.error(f"Erro ao importar schedule: {e}")
                        import traceback

                        logger.error(f"Traceback: {traceback.format_exc()}")
                    except Exception as e:
                        logger.error(f"Erro no scheduler de fishing ranking: {e}")
                        import traceback

                        logger.error(f"Traceback: {traceback.format_exc()}")

                fishing_thread = threading.Thread(
                    target=start_fishing_scheduler,
                    daemon=True,
                    name="FishingRankingScheduler",
                )
                fishing_thread.start()

                # Verificar se a thread foi iniciada
                time.sleep(0.5)  # Dar tempo para thread iniciar
                if fishing_thread.is_alive():
                    logger.info(
                        f"Sistema de ranking de pescadores inicializado - Thread ativa: {fishing_thread.is_alive()}, Nome: {fishing_thread.name}"
                    )
                else:
                    logger.error(
                        "ERRO: Thread do scheduler de fishing ranking não está ativa!"
                    )
                    logger.error("Isso pode indicar que a thread falhou ao iniciar")
            except Exception as e:
                logger.error(
                    f"Erro ao inicializar sistema de ranking de pescadores: {e}"
                )
        else:
            logger.info("Sistema de ranking de pescadores desabilitado")

        if chat_config.get("enabled", True):
            logger.debug("Sistema de monitoramento de chat iniciado")
        else:
            logger.info("Sistema de monitoramento de chat desabilitado")

        # Inicializar serviço de verificação de veículos (DEPOIS do log_processor)
        try:
            vehicle_verification_config = config.get("vehicle_verification", {})
            if log_processor and log_processor.vehicle_processor:
                vehicle_verification_service = VehicleVerificationService(
                    log_processor=log_processor,
                    enabled=vehicle_verification_config.get("enabled", True),
                    verification_interval_hours=vehicle_verification_config.get(
                        "verification_interval_hours", 24
                    ),
                    logger=logger,
                )
                logger.debug("VehicleVerificationService inicializado")

                # Iniciar serviço se configurado
                if (
                    vehicle_verification_service.enabled
                    and vehicle_verification_config.get("auto_start", True)
                ):
                    verification_start_result = vehicle_verification_service.start()
                    if verification_start_result.get("success"):
                        logger.debug(
                            "Serviço de verificação de veículos iniciado automaticamente"
                        )
                    else:
                        logger.warn(
                            f"Falha ao iniciar serviço de verificação de veículos automaticamente: {verification_start_result.get('message')}"
                        )
            else:
                logger.warn(
                    "VehicleVerificationService não inicializado - LogProcessor ou VehicleProcessor não disponível"
                )
                vehicle_verification_service = None
        except Exception as e:
            logger.error(f"Erro ao inicializar VehicleVerificationService: {e}")
            vehicle_verification_service = None

        # Inicializar serviço de sincronização de GPS
        try:
            gps_config = config.get("player_gps_sync", {})
            if gps_config.get("enabled", True):
                player_gps_sync_service = PlayerGpsSyncService(
                    config=config, path_helper=path_helper, logger=logger
                )
                logger.debug("PlayerGpsSyncService inicializado")

                # NÃO iniciar serviço aqui - será agendado em schedule_initial_syncs() para evitar conflitos de banco
                # O serviço será iniciado sequencialmente junto com os outros serviços
            else:
                logger.info("Sistema de sincronização de GPS desabilitado")
                player_gps_sync_service = None
        except Exception as e:
            logger.error(f"Erro ao inicializar PlayerGpsSyncService: {e}")
            player_gps_sync_service = None

        # Inicializar ElevatedUsersManager
        try:
            elevated_users_manager = ElevatedUsersManager(
                config=config,
                server_manager=server_manager,
                path_helper=path_helper,
                discord_webhook=discord_webhook,
                logger=logger,
            )
            logger.debug("ElevatedUsersManager inicializado")

            # Adicionar referência ao restart_scheduler para sincronização automática
            if restart_scheduler:
                restart_scheduler.elevated_users_manager = elevated_users_manager
                logger.info("ElevatedUsersManager vinculado ao RestartScheduler")
        except Exception as e:
            logger.error(f"Erro ao inicializar ElevatedUsersManager: {e}")
            elevated_users_manager = None

    except Exception as e:
        logger.error(f"Erro ao inicializar sistema de logs: {e}")
        import traceback

        logger.error(f"Traceback completo do erro: {traceback.format_exc()}")
        logger.warn("Sistema de logs não disponível")
        log_processor = None
        online_monitor = None
        chat_processor = None
        vehicle_verification_service = None
        player_gps_sync_service = None
        elevated_users_manager = None

    # Inicializar sistema de permissões
    try:
        logger.debug("Inicializando sistema de permissões...")
        config_directory = path_helper.get_scum_server_path(
            "config_directory", "C:\\Servers\\scum\\SCUM\\Saved\\Config\\WindowsServer"
        )
        ssm_db_path = path_helper.get_ssm_db_path()

        # Inicializar IniManager
        ini_manager = IniManager(config_directory)
        logger.debug(f"IniManager inicializado - Diretório: {config_directory}")

        # Inicializar PermissionManager
        permission_manager = PermissionManager(ssm_db_path, ini_manager)
        logger.debug("PermissionManager inicializado")

        # Sincronizar permissões do banco com arquivos INI na inicialização
        try:
            logger.info("Sincronizando permissões do banco com arquivos INI...")
            sync_result = permission_manager.sync_all_ini_files()
            if sync_result.get("success"):
                logger.info(
                    "Sincronização de permissões concluída",
                    {
                        "files_synced": sync_result.get("data", {}).get(
                            "files_synced", 0
                        ),
                        "total_added": sync_result.get("data", {}).get(
                            "total_added", 0
                        ),
                        "total_removed": sync_result.get("data", {}).get(
                            "total_removed", 0
                        ),
                    },
                )
            else:
                logger.warn(
                    f"Sincronização de permissões falhou: {sync_result.get('message', 'Erro desconhecido')}"
                )
        except Exception as sync_error:
            logger.warn(
                f"Erro ao sincronizar permissões na inicialização: {sync_error}"
            )

        logger.debug("Sistema de permissões inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar sistema de permissões: {e}")
        logger.warn("Sistema de permissões não disponível")

    # Inicializar AuthManager
    try:
        auth_config = config.get("auth", {})
        if auth_config.get("enabled", True):
            db_path = path_helper.get_ssm_db_path()
            jwt_secret = auth_config.get("jwt_secret")
            if isinstance(jwt_secret, str) and jwt_secret.startswith("ENCRYPTED:"):
                try:
                    from core.security.credential_encryption import decrypt_credential
                    jwt_secret = decrypt_credential(jwt_secret, logger=logger)
                except Exception:
                    jwt_secret = ""

            if not jwt_secret or not str(jwt_secret).strip():
                jwt_secret = "ssm-backend-secret-key-change-in-production"

            jwt_expiration_hours = auth_config.get("jwt_expiration_hours", 24)
            default_username = auth_config.get("default_username", "admin")
            default_password = auth_config.get("default_password", "12345678910")

            from core.auth.auth_manager import AuthManager

            auth_manager = AuthManager(
                db_path=db_path,
                jwt_secret=jwt_secret,
                jwt_expiration_hours=jwt_expiration_hours,
                default_username=default_username,
                default_password=default_password,
                logger=logger,
            )
            logger.debug("AuthManager inicializado com sucesso")

            # Inicializar PasswordResetManager
            try:
                from core.auth.password_reset import PasswordResetManager

                password_reset_manager = PasswordResetManager(
                    db_path=db_path, logger=logger
                )
                logger.debug("PasswordResetManager inicializado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao inicializar PasswordResetManager: {e}")
                password_reset_manager = None
        else:
            auth_manager = None
            password_reset_manager = None
            logger.info("AuthManager desabilitado no config.json")
    except Exception as e:
        logger.error(f"Erro ao inicializar AuthManager: {e}")
        logger.warn("AuthManager não disponível")
        auth_manager = None
        password_reset_manager = None

    # Inicializar GestaoSyncService (Desabilitado - Gestão não é mais utilizada)
    gestao_sync_service = None

    # Inicializar DiscordBotService (Gateway / bot online)
    try:
        from core.discord_bot_service import DiscordBotService

        ssm_db_path_local = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"
        discord_bot_service = DiscordBotService(
            config=config,
            ssm_db_path=ssm_db_path_local,
            logger=discord_logger,
            webhooks_path=(str(path_helper.get_application_path("webhooks", "data/webhooks.json")) if path_helper else "data/webhooks.json"),
            auth_manager=auth_manager,
        )

        bot_start = discord_bot_service.start()
        if not bot_start.get("success"):
            logger.warn(f"DiscordBotService não iniciado: {bot_start.get('message')}")
        else:
            logger.info("DiscordBotService iniciado")

            # Injetar bot service nos monitores já criados (ordem de init pode criar monitor antes do bot)
            try:
                if chat_command_monitor and getattr(chat_command_monitor, "discord_bot_service", None) is None:
                    chat_command_monitor.discord_bot_service = discord_bot_service
            except Exception:
                pass
            try:
                if (
                    log_processor
                    and getattr(log_processor, "chat_command_monitor", None)
                    and getattr(log_processor.chat_command_monitor, "discord_bot_service", None)
                    is None
                ):
                    log_processor.chat_command_monitor.discord_bot_service = discord_bot_service
            except Exception:
                pass
    except Exception as e:
        discord_bot_service = None
        try:
            logger.warn(f"DiscordBotService não disponível: {e}")
        except Exception:
            pass

    logger.info("Todos os componentes inicializados com sucesso")

    # ============================================================================
    # POPULAR SERVICE REGISTRY (Bridge para Blueprints)
    # ============================================================================
    # Popula o ServiceRegistry com todos os serviços inicializados.
    # Blueprints acessam estes serviços via get_services() em vez de variáveis globais.
    try:
        from app.extensions import get_services
        svc = get_services()

        # Config e infraestrutura
        svc.config = config
        svc.path_helper = path_helper
        svc.logger = logger
        svc.rcon_queue_manager = rcon_queue_manager
        svc.event_manager = event_manager

        # Servidor
        svc.server_manager = server_manager
        svc.restart_scheduler = restart_scheduler
        svc.weather_scheduler = weather_scheduler
        svc.rcon_routine_manager = rcon_routine_manager
        svc.rcon_routine_scheduler = rcon_routine_scheduler
        svc.attribute_expiration_scheduler = attribute_expiration_scheduler
        svc.settings_routine_scheduler = settings_routine_scheduler


        # Discord
        svc.discord_webhook = discord_webhook
        svc.discord_bot_service = discord_bot_service

        # Notificações
        svc.notification_manager = notification_manager

        # Escalabilidade e Identidade
        svc.backend_identity = backend_identity
        svc.owner_manager = owner_manager
        svc.heartbeat_manager = heartbeat_manager
        svc.remote_command_handler = remote_command_handler
        svc.license_validator = license_validator

        # Processamento de Logs
        svc.log_processor = log_processor
        svc.online_monitor = online_monitor
        svc.chat_processor = chat_processor
        svc.bunker_processor = bunker_processor
        svc.chat_command_monitor = chat_command_monitor
        svc.fishing_ranking_manager = fishing_ranking_manager
        svc.shop_buy_job_worker = shop_buy_job_worker
        svc.shop_delivery_worker = shop_delivery_worker

        # Sincronização
        svc.squad_sync_service = squad_sync_service
        svc.squad_tk_jail_service = squad_tk_jail_service
        svc.survival_stats_sync_service = survival_stats_sync_service
        svc.chest_sync_service = chest_sync_service
        svc.chest_inventory_sync_service = chest_inventory_sync_service
        svc.vehicle_verification_service = vehicle_verification_service
        svc.player_gps_sync_service = player_gps_sync_service
        svc.player_skills_sync_service = player_skills_sync_service
        svc.bank_account_sync_service = bank_account_sync_service
        svc.elevated_users_manager = elevated_users_manager
        svc.gestao_sync_service = gestao_sync_service
        svc.scum_logs_cleanup_service = scum_logs_cleanup_service

        # Rankings
        svc.rankings_update_service = rankings_update_service
        svc.lockpicking_ranking_service = lockpicking_ranking_service
        svc.kills_ranking_service = kills_ranking_service
        svc.snipers_ranking_service = snipers_ranking_service
        svc.bounty_service = bounty_service

        # Autenticação
        svc.auth_manager = auth_manager
        svc.password_reset_manager = password_reset_manager

        # Permissões
        svc.permission_manager = permission_manager
        svc.ini_manager = ini_manager

        logger.debug("ServiceRegistry populado com sucesso (Blueprints habilitados)")
    except Exception as e:
        logger.warn(f"Erro ao popular ServiceRegistry: {e} - Blueprints podem não funcionar corretamente")


def cleanup_components():
    """
    Parar todos os componentes e threads de background graciosamente.
    Deve ser chamado antes de parar o servidor Flask ou ao fechar a aplicação.
    Funciona tanto no ambiente de desenvolvimento (.py) quanto empacotado (.exe).
    """
    global log_processor, online_monitor, restart_scheduler, weather_scheduler, rcon_routine_scheduler, attribute_expiration_scheduler
    global personal_webhook_scheduler, settings_routine_scheduler
    global squad_sync_service, squad_tk_jail_service, survival_stats_sync_service, chest_sync_service
    global player_gps_sync_service, player_skills_sync_service, bank_account_sync_service
    global rankings_update_service, lockpicking_ranking_service, kills_ranking_service, snipers_ranking_service, vehicle_verification_service
    global notification_manager, gestao_messages_service
    global chest_inventory_sync_service
    global discord_bot_service, discord_webhook
    global scum_logs_cleanup_service
    global rcon_queue_manager, event_manager
    global elevated_users_manager, heartbeat_manager
    global chat_processor, bunker_processor, chat_command_monitor
    global shop_buy_job_worker, shop_delivery_worker, _fishing_scheduler_stop_event, fishing_ranking_manager
    global permission_manager, ini_manager, auth_manager, password_reset_manager, server_manager

    if logger:
        logger.info("Parando todos os componentes de background...")

    try:
        # 1. Parar workers de Shop (RCON / compras) PRIMEIRO para cessar chamadas de socket
        if shop_delivery_worker:
            try:
                shop_delivery_worker.stop()
                if logger:
                    logger.info("ShopDeliveryWorker parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar ShopDeliveryWorker: {e}")
            shop_delivery_worker = None

        if shop_buy_job_worker:
            try:
                shop_buy_job_worker.stop()
                if logger:
                    logger.info("ShopBuyJobWorker parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar ShopBuyJobWorker: {e}")
            shop_buy_job_worker = None

        # 2. Parar EventManager e RconQueueManager
        if event_manager:
            try:
                event_manager.stop()
                if logger:
                    logger.info("EventManager parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar EventManager: {e}")
            event_manager = None

        if rcon_queue_manager:
            try:
                rcon_queue_manager.stop()
                if logger:
                    logger.info("RconQueueManager parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar RconQueueManager: {e}")
            rcon_queue_manager = None

        # 3. Parar monitores de chat e comandos
        if chat_command_monitor:
            try:
                chat_command_monitor.stop_monitoring()
                if logger:
                    logger.info("ChatCommandMonitor parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar ChatCommandMonitor: {e}")
            chat_command_monitor = None

        if bunker_processor and hasattr(bunker_processor, "stop_status_updater"):
            try:
                bunker_processor.stop_status_updater()
                if logger:
                    logger.info("BunkerProcessor parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar BunkerProcessor: {e}")
            bunker_processor = None

        # 4. Parar NotificationManager (tem thread periódica)
        if notification_manager:
            try:
                notification_manager.stop()
                if logger:
                    logger.info("NotificationManager parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar NotificationManager: {e}")
            notification_manager = None

        # 5. Parar processamento de logs (FileMonitor + log processor)
        if log_processor:
            try:
                log_processor.running = False
                if hasattr(log_processor, "stop_event"):
                    log_processor.stop_event.set()
                
                log_processor.stop_processing(timeout=3.0)
                
                if hasattr(log_processor, "bank_transaction_processor") and log_processor.bank_transaction_processor:
                    if hasattr(log_processor.bank_transaction_processor, "set_running"):
                        log_processor.bank_transaction_processor.set_running(False)
                
                if logger:
                    logger.info("LogProcessor parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar LogProcessor: {e}")
            log_processor = None

        # 6. Parar monitor de jogadores online
        if online_monitor:
            try:
                online_monitor.stop_monitoring()
                if logger:
                    logger.info("OnlinePlayersMonitor parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar OnlinePlayersMonitor: {e}")
            online_monitor = None

        # 7. Parar schedulers
        if restart_scheduler:
            try:
                restart_scheduler.stop()
                if logger:
                    logger.info("RestartScheduler parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar RestartScheduler: {e}")
            restart_scheduler = None

        if weather_scheduler:
            try:
                weather_scheduler.stop()
                if logger:
                    logger.info("WeatherScheduler parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar WeatherScheduler: {e}")
            weather_scheduler = None

        if rcon_routine_scheduler:
            try:
                rcon_routine_scheduler.stop()
                if logger:
                    logger.info("RconRoutineScheduler parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar RconRoutineScheduler: {e}")
            rcon_routine_scheduler = None

        if settings_routine_scheduler:
            try:
                settings_routine_scheduler.stop()
                if logger:
                    logger.info("SettingsRoutineScheduler parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar SettingsRoutineScheduler: {e}")
            settings_routine_scheduler = None

        if attribute_expiration_scheduler:
            try:
                attribute_expiration_scheduler.stop()
                if logger:
                    logger.info("AttributeExpirationScheduler parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar AttributeExpirationScheduler: {e}")
            attribute_expiration_scheduler = None

        if personal_webhook_scheduler:
            try:
                personal_webhook_scheduler.stop()
                if logger:
                    logger.info("PersonalWebhookScheduler parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar PersonalWebhookScheduler: {e}")
            personal_webhook_scheduler = None

        if scum_logs_cleanup_service:
            try:
                scum_logs_cleanup_service.stop()
                if logger:
                    logger.info("ScumLogsCleanupService parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar ScumLogsCleanupService: {e}")
            scum_logs_cleanup_service = None

        # 8. Sinalizar parada do scheduler de pesca
        if _fishing_scheduler_stop_event:
            try:
                _fishing_scheduler_stop_event.set()
                if logger:
                    logger.info("FishingRankingScheduler sinalizado para parar")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao sinalizar parada de FishingRankingScheduler: {e}")

        # 9. Parar HeartbeatManager
        if heartbeat_manager and hasattr(heartbeat_manager, "stop_heartbeat"):
            try:
                heartbeat_manager.stop_heartbeat()
                if logger:
                    logger.info("HeartbeatManager parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar HeartbeatManager: {e}")
            heartbeat_manager = None

        # 10. Parar DiscordBotService (Gateway)
        if discord_bot_service:
            try:
                discord_bot_service.stop()
                if logger:
                    logger.info("DiscordBotService parado")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao parar DiscordBotService: {e}")
            discord_bot_service = None

        # 11. Parar serviços de sincronização e rankings em paralelo
        services_to_stop = [
            (squad_sync_service, "SquadSyncService"),
            (squad_tk_jail_service, "SquadTKJailService"),
            (survival_stats_sync_service, "SurvivalStatsSyncService"),
            (chest_sync_service, "ChestSyncService"),
            (chest_inventory_sync_service, "ChestInventorySyncService"),
            (player_gps_sync_service, "PlayerGpsSyncService"),
            (player_skills_sync_service, "PlayerSkillsSyncService"),
            (bank_account_sync_service, "BankAccountSyncService"),
            (rankings_update_service, "RankingsUpdateService"),
            (lockpicking_ranking_service, "LockpickingRankingService"),
            (kills_ranking_service, "KillsRankingService"),
            (snipers_ranking_service, "SnipersRankingService"),
            (vehicle_verification_service, "VehicleVerificationService"),
            (elevated_users_manager, "ElevatedUsersManager"),
        ]

        import threading

        stop_threads = []
        for service, name in services_to_stop:
            if service and hasattr(service, "stop"):

                def stop_service(s, n):
                    try:
                        s.stop()
                        if logger:
                            logger.info(f"{n} parado")
                    except Exception as e:
                        if logger:
                            logger.warn(f"Erro ao parar {n}: {e}")

                thread = threading.Thread(
                    target=stop_service, args=(service, name), daemon=True
                )
                thread.start()
                stop_threads.append((thread, name))

        still_running = []
        for thread, name in stop_threads:
            thread.join(timeout=1.5)
            if thread.is_alive():
                still_running.append(name)

        if still_running and logger:
            logger.warn(
                "Alguns serviços ainda estão parando após timeout:",
                {"services": still_running},
            )

        # 12. Limpar referências do ServiceRegistry para isolamento completo
        try:
            from app.extensions import get_services
            svc = get_services()
            for attr in list(vars(svc).keys()):
                if not attr.startswith("__"):
                    setattr(svc, attr, None)
            if logger:
                logger.debug("ServiceRegistry limpo com sucesso")
        except Exception as e:
            if logger:
                logger.warn(f"Erro ao limpar ServiceRegistry: {e}")

        # 13. Resetar referências globais
        squad_sync_service = None
        squad_tk_jail_service = None
        survival_stats_sync_service = None
        chest_sync_service = None
        chest_inventory_sync_service = None
        player_gps_sync_service = None
        player_skills_sync_service = None
        bank_account_sync_service = None
        rankings_update_service = None
        lockpicking_ranking_service = None
        kills_ranking_service = None
        snipers_ranking_service = None
        vehicle_verification_service = None
        elevated_users_manager = None
        chat_processor = None
        fishing_ranking_manager = None
        discord_webhook = None

        if logger:
            logger.info("Todos os componentes de background foram parados com sucesso")

    except Exception as e:
        if logger:
            logger.error(f"Erro geral ao parar componentes: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")


def schedule_initial_syncs():
    """
    Agenda todas as sincronizações iniciais para serem executadas em threads
    após o servidor Flask iniciar, evitando travar a inicialização
    """
    import threading

    def run_initial_syncs():
        """Executar sincronizações iniciais em background"""
        # Aguardar 3 segundos para garantir que o servidor Flask iniciou completamente
        time.sleep(3)

        logger.info("Iniciando serviços de sincronização em background...")

        ssm_db_path_local = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"

        playtime_rewards_config = config.get("playtime_rewards", {})
        playtime_rewards_enabled = playtime_rewards_config.get("enabled", True)
        playtime_rewards_interval_seconds = int(
            playtime_rewards_config.get("interval_seconds", 30 * 60)
        )
        playtime_rewards_startup_delay_seconds = int(
            playtime_rewards_config.get("startup_delay_seconds", 30)
        )
        playtime_rewards_wait_for_rankings = bool(
            playtime_rewards_config.get("wait_for_rankings_initial_update", True)
        )
        playtime_rewards_started = False

        def _start_playtime_rewards_thread(ssm_db_path_arg: str) -> None:
            try:
                logger.info("Thread do scheduler de playtime rewards iniciada")
                if playtime_rewards_startup_delay_seconds > 0:
                    time.sleep(int(playtime_rewards_startup_delay_seconds))

                while True:
                    try:
                        rewards = RewardsService(ssm_db_path_arg, logger=logger)
                        stats = rewards.tick_playtime_reward_multi_rules()
                        if (
                            int(stats.processed_players) > 0
                            or int(stats.initialized_baseline) > 0
                            or int(stats.awarded_players) > 0
                            or int(stats.errors) > 0
                        ):
                            logger.info(
                                "Playtime reward tick (multi-rules)",
                                {
                                    "processed": int(stats.processed_players),
                                    "baseline": int(stats.initialized_baseline),
                                    "awarded": int(stats.awarded_players),
                                    "total_points": int(stats.total_points_awarded),
                                    "errors": int(stats.errors),
                                },
                            )
                    except Exception as e:
                        logger.error(f"Erro no scheduler de playtime rewards: {e}")

                    time.sleep(int(playtime_rewards_interval_seconds))
            except Exception as e:
                logger.error(f"Erro fatal na thread do scheduler de playtime rewards: {e}")

        # Iniciar a thread de playtime rewards imediatamente se não precisar aguardar rankings
        if (
            playtime_rewards_enabled
            and (not playtime_rewards_wait_for_rankings)
            and (not playtime_rewards_started)
        ):
            playtime_rewards_thread = threading.Thread(
                target=_start_playtime_rewards_thread,
                args=(str(ssm_db_path_local),),
                daemon=True,
                name="PlaytimeRewardsThread",
            )
            playtime_rewards_thread.start()
            playtime_rewards_started = True
            logger.info(
                "Scheduler de playtime rewards iniciado antecipadamente",
                {
                    "thread": playtime_rewards_thread.name,
                    "interval_seconds": int(playtime_rewards_interval_seconds),
                    "startup_delay_seconds": int(playtime_rewards_startup_delay_seconds),
                },
            )

        # MELHORIA: Lista de serviços para iniciar com delay entre cada um
        # Isso evita conflitos de "database is locked" na inicialização
        services_to_start = [
            (squad_sync_service, "squads", "squad_sync"),
            (survival_stats_sync_service, "survival stats", "survival_stats_sync"),
            (rankings_update_service, "rankings", "rankings_update"),
            (player_skills_sync_service, "player skills", "player_skills_sync"),
            (bank_account_sync_service, "saldos bancários", "bank_account_sync"),
            (chest_sync_service, "baús", "chest_sync"),
            (chest_inventory_sync_service, "inventário de baús", "chest_inventory_sync"),
            (player_gps_sync_service, "GPS", "player_gps_sync"),
            (scum_logs_cleanup_service, "limpeza de logs (SCUM)", "scum_logs_cleanup"),
        ]

        # Iniciar serviços de sincronização com delay entre cada um
        try:
            for i, (service, service_name, config_key) in enumerate(services_to_start):
                if service and service.enabled:
                    service_config = config.get(config_key, {})
                    if service_config.get("auto_start", True):
                        try:
                            start_result = service.start()
                            if start_result.get("success"):
                                logger.info(f"Sincronização de {service_name} iniciada")
                            else:
                                logger.warn(
                                    f"Falha ao iniciar sincronização de {service_name}: {start_result.get('message')}"
                                )
                        except Exception as e:
                            logger.error(
                                f"Erro ao iniciar sincronização de {service_name}: {e}"
                            )

                if (
                    not playtime_rewards_started
                    and playtime_rewards_enabled
                    and playtime_rewards_wait_for_rankings
                    and config_key == "rankings_update"
                ):
                    playtime_rewards_thread = threading.Thread(
                        target=_start_playtime_rewards_thread,
                        args=(str(ssm_db_path_local),),
                        daemon=True,
                        name="PlaytimeRewardsThread",
                    )
                    playtime_rewards_thread.start()
                    playtime_rewards_started = True
                    logger.info(
                        "Scheduler de playtime rewards liberado após atualização inicial de rankings",
                        {
                            "thread": playtime_rewards_thread.name,
                            "interval_seconds": int(playtime_rewards_interval_seconds),
                            "startup_delay_seconds": int(playtime_rewards_startup_delay_seconds),
                        },
                    )

                # Delay de 3 segundos entre cada serviço para evitar conflitos de banco de dados
                # Isso permite que cada serviço complete ensure_table() antes do próximo iniciar
                if i < len(services_to_start) - 1:
                    time.sleep(3)



            # GestaoSyncService (Desabilitado)

            # Enviar rankings iniciais se configurado (lockpicking, kills, snipers)
            try:
                lockpicking_config = config.get("lockpicking_ranking", {})
                if lockpicking_config.get("enabled", True) and lockpicking_config.get(
                    "send_on_startup", True
                ):
                    if lockpicking_ranking_service:

                        def send_lockpicking():
                            try:
                                logger.info("Enviando rankings de lockpicking...")
                                send_result = (
                                    lockpicking_ranking_service.send_rankings()
                                )
                                if send_result.get("success"):
                                    if send_result.get("skipped"):
                                        logger.debug(
                                            "Envio de rankings de lockpicking ignorado (webhook não configurado)"
                                        )
                                    else:
                                        logger.info(
                                            f"Rankings de lockpicking sincronizados com sucesso: {send_result.get('message')}"
                                        )
                                else:
                                    logger.warn(
                                        f"Falha ao enviar rankings: {send_result.get('message')}"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Erro ao enviar rankings de lockpicking: {e}"
                                )

                        threading.Thread(target=send_lockpicking, daemon=True).start()

                kills_config = config.get("kills_ranking", {})
                if kills_config.get("enabled", True) and kills_config.get(
                    "send_on_startup", True
                ):
                    if kills_ranking_service:

                        def send_kills():
                            try:
                                logger.info("Sincronizando rankings de combate...")
                                send_result = kills_ranking_service.send_rankings()
                                if send_result.get("success"):
                                    if send_result.get("skipped"):
                                        logger.debug(
                                            "Envio de rankings de combate ignorado (dados inalterados ou webhook não configurado)"
                                        )
                                    else:
                                        logger.info(
                                            "Rankings de combate sincronizados com sucesso no Discord"
                                        )
                                else:
                                    logger.warn(
                                        f"Falha ao sincronizar rankings de combate: {send_result.get('message')}"
                                    )
                            except Exception as e:
                                logger.error(f"Erro ao sincronizar rankings de combate: {e}")

                        threading.Thread(target=send_kills, daemon=True).start()
            except Exception as e:
                logger.error(f"Erro ao agendar envio de rankings iniciais: {e}")

            logger.debug(
                "Todos os serviços de sincronização foram iniciados em background"
            )
        except Exception as e:
            logger.error(f"Erro ao iniciar serviços de sincronização: {e}")

    # Executar em thread separada
    sync_thread = threading.Thread(target=run_initial_syncs, daemon=True)
    sync_thread.start()


# ============================================================================
# API ENDPOINTS
# ============================================================================


# ROTAS MIGRADAS PARA auth_bp


# ROTAS MIGRADAS PARA auth_bp


# ============================================================================
# ROTAS MIGRADAS PARA BLUEPRINTS
# ============================================================================
# Os seguintes endpoints foram migrados para módulos independentes:
#
# Middleware (app/middleware.py):
#   - @app.errorhandler(BadRequest)  → handle_bad_request
#   - @app.before_request            → check_license_before_request
#
# Blueprint system_bp (app/routes/system.py):
#   - GET  /api/health                           → health_check
#   - GET  /api/licensing/hardware-fingerprint    → get_hardware_fingerprint
#   - GET  /api/discord/webhooks/test             → discord_webhooks_test_list
#   - POST /api/discord/webhooks/test/<event_key> → discord_webhooks_test_send
#
# Estes endpoints agora são registrados automaticamente via App Factory
# em app/__init__.py → create_app()
# ============================================================================

# ============================================================================
# ENDPOINTS DE AUTENTICAÇÃO
# ============================================================================


def _decrypt_if_needed(value: str) -> str:
    try:
        if not value:
            return ""
        if not str(value).startswith("ENCRYPTED:"):
            return str(value)
        from core.security.credential_encryption import decrypt_credential

        return str(decrypt_credential(str(value), logger=logger))
    except Exception:
        return str(value or "")


def _get_player_jwt_secret() -> str:
    auth_cfg = (config or {}).get("auth", {}) if isinstance(config, dict) else {}
    raw = str(auth_cfg.get("jwt_secret") or "").strip()
    if not raw:
        return "ssm-player-secret-change-in-production"
    return _decrypt_if_needed(raw)


def _get_player_jwt_expiration_hours() -> int:
    public_cfg = (config or {}).get("public", {}) if isinstance(config, dict) else {}
    try:
        v = int(public_cfg.get("player_jwt_expiration_hours", 24))
        return v if v > 0 else 24
    except Exception:
        return 24


def _get_gestao_player_me_path() -> str:
    public_cfg = (config or {}).get("public", {}) if isinstance(config, dict) else {}
    path = str(public_cfg.get("gestao_player_me_path") or "").strip() or "/api/v1/player/me"
    if not path.startswith("/"):
        path = "/" + path
    return path


def _issue_player_jwt(steam_id: str, server_hash: str) -> str:
    exp = datetime.utcnow() + timedelta(hours=_get_player_jwt_expiration_hours())
    payload = {
        "sub": str(steam_id),
        "aud": "player",
        "server_hash": str(server_hash),
        "iat": datetime.utcnow(),
        "exp": exp,
    }
    return jwt.encode(payload, _get_player_jwt_secret(), algorithm="HS256")


def _decode_player_jwt(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            _get_player_jwt_secret(),
            algorithms=["HS256"],
            options={"require": ["exp", "iat"], "verify_aud": False},
        )
        if not isinstance(payload, dict):
            return None
        if str(payload.get("aud") or "") != "player":
            return None
        if not str(payload.get("sub") or "").strip():
            return None
        if not str(payload.get("server_hash") or "").strip():
            return None
        return payload
    except Exception:
        return None


def require_player_auth(f):
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return jsonify({"success": False, "error": "AUTH_REQUIRED"}), 401

        payload = _decode_player_jwt(token)
        if not payload:
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


def _gestao_get_player_identity(gestao_access_token: str) -> Tuple[Optional[str], Optional[str]]:
    """Retorna (steam_id, error_code)"""
    token = str(gestao_access_token or "").strip()
    if not token:
        return None, "GESTAO_TOKEN_REQUIRED"

    base = str(GESTAO_SERVER_URL or "").rstrip("/")
    url = f"{base}{_get_gestao_player_me_path()}"

    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace") if raw else "{}"
            data = json.loads(text) if text else {}
            # aceitar formatos: {steam_id: "..."} ou {success:true,data:{steam_id:"..."}}
            if isinstance(data, dict) and "steam_id" in data:
                steam_id = str(data.get("steam_id") or "").strip()
            else:
                inner = (data or {}).get("data") if isinstance(data, dict) else None
                steam_id = str((inner or {}).get("steam_id") or "").strip() if isinstance(inner, dict) else ""
            if not steam_id:
                return None, "STEAM_ID_NOT_FOUND"
            return steam_id, None
    except urllib.error.HTTPError as he:
        status = getattr(he, "code", None)
        if status in (401, 403):
            return None, "GESTAO_TOKEN_INVALID"
        return None, "GESTAO_HTTP_ERROR"
    except Exception:
        return None, "GESTAO_UNREACHABLE"


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA player_app_bp


def _ensure_chest_inventory_tables(ssm_db_path: str) -> None:
    with DatabaseConnector.get_connection(ssm_db_path, write_mode=True) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chest_inventory_snapshot (
                chest_entity_id INTEGER PRIMARY KEY,
                steam_id TEXT,
                player_name TEXT,
                scanned_at TEXT NOT NULL,
                items_total INTEGER DEFAULT 0
            )
            """
        )
        # Migração leve: adicionar coluna quantity se banco já existia
        try:
            cur.execute("PRAGMA table_info('chest_inventory_item')")
            cols = {row[1] for row in cur.fetchall()}
            if "quantity" not in cols:
                cur.execute(
                    "ALTER TABLE chest_inventory_item ADD COLUMN quantity INTEGER DEFAULT 1"
                )
        except Exception:
            pass
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chest_inventory_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chest_entity_id INTEGER NOT NULL,
                item_entity_id INTEGER NOT NULL,
                item_class TEXT,
                slot_index INTEGER,
                scanned_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_chest_inventory_item_chest ON chest_inventory_item (chest_entity_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_chest_inventory_item_class ON chest_inventory_item (item_class)"
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS item_catalog (
                item_class TEXT PRIMARY KEY,
                display_name TEXT,
                category TEXT,
                icon TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()


def _autofill_item_catalog(conn: sqlite3.Connection, item_classes: List[str]) -> int:
    """Inserir item_class novos no item_catalog (sem sobrescrever display_name etc.)."""
    classes = [str(c).strip() for c in (item_classes or []) if str(c).strip()]
    if not classes:
        return 0

    cur = conn.cursor()

    placeholders = ",".join(["?"] * len(classes))
    cur.execute(
        f"SELECT item_class FROM item_catalog WHERE item_class IN ({placeholders})",
        classes,
    )
    existing = {row[0] for row in cur.fetchall()}

    new_classes = [c for c in classes if c not in existing]
    if not new_classes:
        return 0

    cur.executemany(
        "INSERT OR IGNORE INTO item_catalog(item_class, updated_at) VALUES(?, datetime('now'))",
        [(c,) for c in new_classes],
    )
    return len(new_classes)


def _scan_scum_chest_inventory(scum_db_path: str, chest_entity_id: int):
    """Ler inventário do baú no SCUM.db (via shared copy) usando Inventory component."""
    from utils.scum_db_helper import scum_db_readonly_connection

    with scum_db_readonly_connection(scum_db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id FROM entity WHERE id = ?", (int(chest_entity_id),))
        if not cur.fetchone():
            return None, "CHEST_NOT_FOUND_SCUMDB"

        cur.execute(
            """
            SELECT id FROM entity_component
            WHERE entity_id = ? AND name = 'Inventory'
            LIMIT 1
            """,
            (int(chest_entity_id),),
        )
        comp = cur.fetchone()
        if not comp:
            return [], None
        comp_id = int(comp[0])

        cur.execute(
            """
            SELECT eice.entity_id AS item_entity_id,
                   eice.data AS slot_index,
                   e.class AS item_class
            FROM entity_inventory_component_entry eice
            INNER JOIN entity e ON e.id = eice.entity_id
            WHERE eice.entity_component_id = ?
            ORDER BY COALESCE(eice.data, 999999), eice.entity_id ASC
            """,
            (comp_id,),
        )
        rows = cur.fetchall()
        items = []
        item_ids = [int(r["item_entity_id"]) for r in rows]

        stack_qty: Dict[int, int] = {}
        ammo_qty: Dict[int, int] = {}

        if item_ids:
            # Stackable quantities
            try:
                placeholders = ",".join(["?"] * len(item_ids))
                cur.execute(
                    f"""
                    SELECT ec.entity_id AS item_entity_id, sce.quantity AS quantity
                    FROM entity_component ec
                    INNER JOIN stackable_component_entry sce
                      ON sce.entity_component_id = ec.id
                    WHERE ec.entity_id IN ({placeholders})
                    """,
                    item_ids,
                )
                for rr in cur.fetchall():
                    try:
                        stack_qty[int(rr[0])] = int(rr[1]) if rr[1] is not None else 1
                    except Exception:
                        pass
            except Exception:
                pass

            # Ammo quantities (count rows per weapon/magazine entity)
            try:
                placeholders = ",".join(["?"] * len(item_ids))
                cur.execute(
                    f"""
                    SELECT weapon_item_entity_id, COUNT(1)
                    FROM weapon_item_entity_loaded_ammo_data
                    WHERE weapon_item_entity_id IN ({placeholders})
                    GROUP BY weapon_item_entity_id
                    """,
                    item_ids,
                )
                for rr in cur.fetchall():
                    ammo_qty[int(rr[0])] = ammo_qty.get(int(rr[0]), 0) + int(rr[1] or 0)
            except Exception:
                pass

            try:
                placeholders = ",".join(["?"] * len(item_ids))
                cur.execute(
                    f"""
                    SELECT weapon_item_entity_id, COUNT(1)
                    FROM weapon_item_entity_internal_magazine_ammo_data
                    WHERE weapon_item_entity_id IN ({placeholders})
                    GROUP BY weapon_item_entity_id
                    """,
                    item_ids,
                )
                for rr in cur.fetchall():
                    ammo_qty[int(rr[0])] = ammo_qty.get(int(rr[0]), 0) + int(rr[1] or 0)
            except Exception:
                pass

            try:
                placeholders = ",".join(["?"] * len(item_ids))
                cur.execute(
                    f"""
                    SELECT weapon_attachment_magazine_item_entity_id, COUNT(1)
                    FROM weapon_attachment_magazine_item_entity_ammo_data
                    WHERE weapon_attachment_magazine_item_entity_id IN ({placeholders})
                    GROUP BY weapon_attachment_magazine_item_entity_id
                    """,
                    item_ids,
                )
                for rr in cur.fetchall():
                    ammo_qty[int(rr[0])] = ammo_qty.get(int(rr[0]), 0) + int(rr[1] or 0)
            except Exception:
                pass

        for r in rows:
            item_id = int(r["item_entity_id"])
            qty = 1
            if item_id in stack_qty:
                qty = max(1, int(stack_qty[item_id] or 1))
            elif item_id in ammo_qty and int(ammo_qty[item_id] or 0) > 0:
                qty = int(ammo_qty[item_id] or 0)

            items.append(
                {
                    "item_entity_id": item_id,
                    "item_class": r["item_class"],
                    "slot_index": r["slot_index"],
                    "quantity": qty,
                }
            )
        return items, None


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA player_app_bp


# ---------------------------------------------------------------------------
# Player App – Veículos do Jogador (player-scoped)
# ---------------------------------------------------------------------------

def _format_vehicle_class_display(vehicle_class: str) -> str:
    """Formatar nome amigável do veículo removendo prefixos/sufixos."""
    if not vehicle_class:
        return "Desconhecido"
    return vehicle_class.replace("BPC_", "").replace("BP_", "").replace("_ES", "").replace("_C", "").replace("_", " ").strip()


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA auth_bp


# ROTAS MIGRADAS PARA auth_bp


# ROTAS MIGRADAS PARA auth_bp


# ROTAS MIGRADAS PARA auth_bp


# ROTAS MIGRADAS PARA auth_bp


# ==========================================================================
# ENDPOINTS DO PLAYER APP (PLAYER-SCOPED)
# ==========================================================================


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA player_app_bp


# ROTAS MIGRADAS PARA auth_bp


# ROTAS MIGRADAS PARA auth_bp


# ROTAS MIGRADAS PARA auth_bp


# ROTAS MIGRADAS PARA auth_bp


# ROTAS MIGRADAS PARA auth_bp


# ROTAS MIGRADAS PARA auth_bp


# ROTAS MIGRADAS PARA auth_bp


# ============================================================================
# ENDPOINTS DO SHOP + ECONOMY
# ============================================================================


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA integrations_bp


# ROTAS MIGRADAS PARA integrations_bp


# ROTAS MIGRADAS PARA integrations_bp


# ROTAS MIGRADAS PARA integrations_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp

# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ROTAS MIGRADAS PARA shop_bp


# ============================================================================
# ENDPOINTS DO SERVIDOR
# ============================================================================


# ROTAS MIGRADAS PARA server_bp


# ROTAS MIGRADAS PARA server_bp


# ROTAS MIGRADAS PARA server_bp


# ROTAS MIGRADAS PARA server_bp


# ============================================================================
# ENDPOINTS DE SERVER SETTINGS (ServerSettings.ini)
# ============================================================================


# ROTAS MIGRADAS PARA server_bp


# ROTAS MIGRADAS PARA server_bp


# ROTAS MIGRADAS PARA server_bp


# ============================================================================
# ENDPOINTS DE CONFIGURAÇÃO (config.json)
# ============================================================================


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ============================================================================
# Endpoints de Webhooks (webhooks.json)
# ============================================================================


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA config_bp


# ROTAS MIGRADAS PARA server_bp


# ROTAS MIGRADAS PARA server_bp


# ============================================================================
# ENDPOINTS DO AGENDADOR
# ============================================================================


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA server_bp


# ============================================================================
# ENDPOINTS DO AGENDADOR CLIMÁTICO
# ============================================================================


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ============================================================================
# ENDPOINTS DE NOTIFICAÇÕES
# ============================================================================


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ============================================================================
# ENDPOINTS DE ESCALABILIDADE
# ============================================================================


# ROTAS MIGRADAS PARA admin_bp


@app.route("/api/licensing/hardware-fingerprint", methods=["GET"])
def get_hardware_fingerprint():
    """Obter hardware fingerprint atual (para cadastro inicial)"""
    try:
        # Importar módulos de licenciamento
        try:
            from core.licensing.hardware_fingerprint import (
                HardwareFingerprint,
                WMI_AVAILABLE,
            )
            from core.licensing.license_cache import LicenseCache
        except ImportError as e:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Módulos de licenciamento não disponíveis: {e}",
                    }
                ),
                500,
            )

        # Inicializar HardwareFingerprint
        fingerprint = HardwareFingerprint(logger=logger)

        # SEMPRE gerar hash na hora (não usar armazenado)
        hash_value, components = fingerprint.generate()

        # SEGURANÇA: Hash não é mais armazenado (nem arquivo, nem banco)
        # Hash sempre gerado em memória quando necessário
        # stored_hash removido - não há mais hash armazenado

        # Verificar se componentes críticos foram coletados
        has_critical = (
            bool(components.get("windows_guid"))
            or bool(components.get("cpu_id"))
            or len(components.get("network_macs", [])) > 0
            or len(components.get("disk_serials", [])) > 0
        )

        warning_message = None
        if not has_critical or (
            len(components.get("network_macs", [])) == 0
            and not components.get("cpu_id")
            and len(components.get("disk_serials", [])) == 0
        ):
            warning_message = "ATENÇÃO: Poucos componentes coletados. Instale 'wmi' e 'pywin32': pip install wmi pywin32"

        return jsonify(
            {
                "success": True,
                "data": {
                    "hardware_fingerprint": hash_value,
                    "components": {
                        "network_macs": components.get("network_macs", []),
                        "cpu": {
                            "id": components.get("cpu_id"),
                            "name": components.get("cpu_name"),
                            "cores": components.get("cpu_cores"),
                        },
                        "disks": {
                            "serials": components.get("disk_serials", []),
                            "detailed": components.get("disks_detailed", []),
                        },
                        "motherboard": {
                            "serial": components.get("motherboard_serial"),
                            "name": components.get("motherboard_name"),
                        },
                        "bios_serial": components.get("bios_serial"),
                        "windows_guid": components.get("windows_guid"),
                        "ram": {
                            "serials": components.get("ram_serials", []),
                            "detailed": components.get("ram_detailed", []),
                        },
                        "gpu": {
                            "name": components.get("gpu_name"),
                            "serial": components.get("gpu_serial"),
                        },
                    },
                    # SEGURANÇA: Hash não é mais armazenado (nem arquivo, nem banco)
                    # "stored_hash" removido por segurança
                    "is_new": True,  # Sempre novo (gerado em memória)
                    "matches_stored": None,  # Não há hash armazenado para comparar
                    "generated_at": datetime.now().isoformat(),
                    "wmi_available": WMI_AVAILABLE,
                    "wmi_initialized": (
                        fingerprint.wmi_available
                        if hasattr(fingerprint, "wmi_available")
                        else False
                    ),
                    "wmi_connection": (
                        fingerprint.wmi_conn is not None
                        if hasattr(fingerprint, "wmi_conn")
                        else False
                    ),
                },
                "message": "Use este hardware_fingerprint para cadastro no servidor de licenciamento",
                "warning": warning_message,
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter hardware fingerprint: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ROTAS MIGRADAS PARA admin_bp


# ROTAS MIGRADAS PARA admin_bp


# ROTAS MIGRADAS PARA admin_bp


# ROTAS MIGRADAS PARA admin_bp


# ============================================================================
# ENDPOINTS DO SISTEMA DE LOGS
# ============================================================================


# ROTAS MIGRADAS PARA logs_bp


# ROTAS MIGRADAS PARA logs_bp


# ROTAS MIGRADAS PARA logs_bp


# ROTAS MIGRADAS PARA logs_bp


# ============================================================================
# ENDPOINTS DO SISTEMA DE DEDUPLICAÇÃO
# ============================================================================


# ROTAS MIGRADAS PARA logs_bp


# ROTAS MIGRADAS PARA logs_bp


# ROTAS MIGRADAS PARA logs_bp


# ============================================================================
# ENDPOINTS DE ADMIN LOGS
# ============================================================================


# ROTAS MIGRADAS PARA logs_bp


# ROTAS MIGRADAS PARA logs_bp


# ROTAS MIGRADAS PARA logs_bp


# ROTAS MIGRADAS PARA logs_bp


# ROTAS MIGRADAS PARA logs_bp


# ============================================================================
# ENDPOINTS DE KILL LOGS
# ============================================================================


# ROTAS MIGRADAS PARA logs_bp


# ROTAS MIGRADAS PARA logs_bp


# ROTAS MIGRADAS PARA logs_bp


# ============================================================================
# ENDPOINTS DE JOGADORES ONLINE
# ============================================================================


# ROTAS MIGRADAS PARA players_bp


# ROTAS MIGRADAS PARA players_bp


# ROTAS MIGRADAS PARA players_bp


# ROTAS MIGRADAS PARA players_bp


# ============================================================================
# ENDPOINTS DE RELATÓRIOS DE JOGADORES
# ============================================================================


# ROTAS MIGRADAS PARA reports_bp


# ROTAS MIGRADAS PARA reports_bp


# ROTAS MIGRADAS PARA reports_bp


# ============================================================================
# ENDPOINTS DE JOGADORES (TABELA PLAYERS)
# ============================================================================

PLAYER_DEFAULT_SORT_FIELD = "last_seen"
PLAYER_DEFAULT_SORT_ORDER = "desc"
PLAYER_SORT_COLUMN_MAP: Dict[str, str] = {
    "player_name": "COALESCE(player_name, '') COLLATE NOCASE",
    "last_seen": "last_seen",
    "first_seen": "first_seen",
    "total_playtime": "COALESCE(total_playtime, 0)",
    "total_sessions": "COALESCE(total_sessions, 0)",
    "created_at": "created_at",
}
PLAYER_SORTABLE_FIELDS: Set[str] = set(PLAYER_SORT_COLUMN_MAP.keys()).union(
    {"vehicles_total"}
)


def _normalize_player_sort_params(
    sort_by: Optional[str], sort_order: Optional[str]
) -> Tuple[str, str]:
    normalized_sort_by = (sort_by or PLAYER_DEFAULT_SORT_FIELD).lower()
    if normalized_sort_by not in PLAYER_SORTABLE_FIELDS:
        raise ValueError(f"Campo de ordenação '{normalized_sort_by}' não é suportado")

    normalized_sort_order = (sort_order or PLAYER_DEFAULT_SORT_ORDER).lower()
    if normalized_sort_order not in {"asc", "desc"}:
        raise ValueError("Parâmetro 'sort_order' deve ser 'asc' ou 'desc'")

    return normalized_sort_by, normalized_sort_order


def _fetch_vehicle_statistics(
    steam_ids: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    if not log_processor:
        return {}

    ids = [sid for sid in (steam_ids or []) if sid]
    vehicle_db_path = log_processor.db_manager.db_path

    query = """
        SELECT steam_id,
               COUNT(*) AS total,
               SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) AS status_0,
               SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS status_1,
               SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) AS status_2,
               SUM(CASE WHEN status = 3 THEN 1 ELSE 0 END) AS status_3,
               MAX(last_ownership_change) AS updated_at
        FROM vehicle_current_ownership
    """

    params: List[Any] = []
    if ids:
        placeholders = ",".join("?" for _ in ids)
        query += f" WHERE steam_id IN ({placeholders})"
        params.extend(ids)

    query += " GROUP BY steam_id"

    try:
        with DatabaseConnector.get_connection(vehicle_db_path, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(query, params).fetchall()
    except Exception as exc:
        logger.warn(f"Não foi possível obter estatísticas de veículos: {exc}")
        return {}

    stats: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        stats[row["steam_id"]] = {
            "total": row["total"] or 0,
            "by_status": {
                "0": row["status_0"] or 0,
                "1": row["status_1"] or 0,
                "2": row["status_2"] or 0,
                "3": row["status_3"] or 0,
            },
            "updated_at": row["updated_at"],
        }

    return stats


def _fetch_functional_vehicle_counts_by_steam_id(
    db_path: str,
    steam_ids: List[str],
) -> Dict[str, int]:
    ids = [sid for sid in (steam_ids or []) if sid]
    if not ids:
        return {}

    counts: Dict[str, int] = {}
    chunk_size = 900

    try:
        with DatabaseConnector.get_connection(db_path, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            for i in range(0, len(ids), chunk_size):
                chunk = ids[i : i + chunk_size]
                placeholders = ",".join("?" for _ in chunk)
                query = f"""
                    SELECT steam_id, COUNT(*) AS total
                    FROM vehicle_current_ownership
                    WHERE is_vehicle_functional = 1
                      AND status = 0
                      AND steam_id IN ({placeholders})
                    GROUP BY steam_id
                """
                rows = cursor.execute(query, chunk).fetchall()
                for row in rows:
                    counts[row["steam_id"]] = (row["total"] or 0)

    except Exception as exc:
        logger.warn(f"Não foi possível obter contagem de veículos funcionais: {exc}")
        return {}

    return counts


def _get_sorted_player_rows(
    limit: int, offset: int, sort_by: str, sort_order: str
) -> Tuple[List[sqlite3.Row], int, Optional[Dict[str, Dict[str, Any]]]]:
    db_path, error = _get_ssm_database_path()
    if error:
        raise RuntimeError(error)

    with DatabaseConnector.get_connection(db_path, write_mode=True) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM players")
        total_count = cursor.fetchone()["total"]

        base_query = (
            "SELECT steam_id, player_name, player_id, first_seen, last_seen, "
            "       total_sessions, total_playtime, is_new_player, "
            "       notification_sent, permissao, created_at "
            "FROM players"
        )

        if sort_by == "vehicles_total":
            if not log_processor:
                raise RuntimeError("LogProcessor não inicializado")

            rows = cursor.execute(base_query).fetchall()
            vehicle_stats = _fetch_vehicle_statistics()

            def sort_key(row: sqlite3.Row):
                vehicles_total = vehicle_stats.get(row["steam_id"], {}).get("total", 0)
                name = (row["player_name"] or "").lower()
                return (vehicles_total, name, row["steam_id"])

            reverse = sort_order == "desc"
            sorted_rows = sorted(rows, key=sort_key, reverse=reverse)
            page_rows = sorted_rows[offset : offset + limit]
            return page_rows, total_count, vehicle_stats

        order_column = PLAYER_SORT_COLUMN_MAP[sort_by]
        order_direction = "DESC" if sort_order == "desc" else "ASC"

        query = (
            base_query + f" ORDER BY {order_column} {order_direction}, steam_id ASC "
            "LIMIT ? OFFSET ?"
        )

        rows = cursor.execute(query, (limit, offset)).fetchall()
        return rows, total_count, None


# ROTAS MIGRADAS PARA players_bp


# ROTAS MIGRADAS PARA players_bp


# ROTAS MIGRADAS PARA players_bp


# ROTAS MIGRADAS PARA players_bp


# ROTAS MIGRADAS PARA players_bp


# ============================================================================
# ENDPOINTS DE SQUADS (SNAPSHOT SSM)
# ============================================================================


def _get_ssm_database_path():
    if not config or not path_helper:
        return None, "Configuração não inicializada"

    db_path = path_helper.get_ssm_db_path()
    if not db_path or not os.path.exists(db_path):
        return None, "Banco SSM.db não encontrado"

    return db_path, None


def _get_scum_database_path():
    if not config or not path_helper:
        return None, "Configuração não inicializada"

    db_path = path_helper.get_scum_db_path()
    if not db_path or not os.path.exists(db_path):
        return None, "Banco SCUM.db não encontrado"

    return db_path, None


def _server_must_be_offline_for_scum_db_write():
    """Retorna (ok, error_message)."""
    try:
        if server_manager:
            status = server_manager.get_status()
            if status and status.get("is_running"):
                return (
                    False,
                    "Servidor SCUM precisa estar parado para alterar atributos (evitar corrupção do SCUM.db)",
                )
        return True, None
    except Exception as e:
        return False, f"Falha ao verificar status do servidor: {e}"


def _is_player_online(steam_id: Optional[str]) -> Tuple[Optional[bool], Optional[str]]:
    """Retorna (is_online, error_message). is_online pode ser None se não for possível verificar."""
    if not steam_id:
        return None, "SteamID não disponível para verificar status online"

    try:
        db_path, error = _get_ssm_database_path()
        if error:
            return None, error

        with DatabaseConnector.get_connection(db_path, write_mode=True) as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT 1 FROM players_online WHERE steam_id = ? AND status = 'online' LIMIT 1",
                    (steam_id,),
                )
                row = cur.fetchone()
                return (row is not None), None
            except sqlite3.OperationalError as e:
                # Tabela pode não existir em bancos antigos
                if "no such table" in str(e).lower():
                    return None, "Tabela players_online não existe no SSM.db"
                raise
    except Exception as e:
        return None, f"Falha ao verificar players_online: {e}"


# ============================================================================
# ENDPOINTS - ATRIBUTOS (SCUM.db)
# ============================================================================


# ROTAS MIGRADAS PARA admin_bp


# ROTAS MIGRADAS PARA admin_bp


# ROTAS MIGRADAS PARA admin_bp


def _get_survival_numeric_columns(db_path: str) -> Set[str]:
    """Obter colunas numéricas disponíveis na tabela survival_stats_snapshot"""
    if not db_path or not os.path.exists(db_path):
        return set()

    try:
        with DatabaseConnector.get_connection(db_path, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(survival_stats_snapshot)")
            columns = cursor.fetchall()
    except Exception:
        return set()

    if not columns:
        return set()

    numeric_prefixes = ("INT", "REAL", "NUMERIC", "FLOAT", "DOUBLE", "DECIMAL")
    numeric_columns = {
        row["name"]
        for row in columns
        if (row["type"] or "").upper().startswith(numeric_prefixes)
    }

    return numeric_columns.difference(_SURVIVAL_EXCLUDED_METRICS)


# ROTAS MIGRADAS PARA squads_bp


# ROTAS MIGRADAS PARA squads_bp


# ROTAS MIGRADAS PARA squads_bp


# ROTAS MIGRADAS PARA squads_bp


# ROTAS MIGRADAS PARA squads_bp


# ROTAS MIGRADAS PARA squads_bp


# ROTAS MIGRADAS PARA squads_bp


# ROTAS MIGRADAS PARA squads_bp


# ROTAS MIGRADAS PARA survival_bp


# ROTAS MIGRADAS PARA survival_bp


# ROTAS MIGRADAS PARA survival_bp


# ROTAS MIGRADAS PARA survival_bp


# ROTAS MIGRADAS PARA admin_bp


# ROTAS MIGRADAS PARA admin_bp


# ROTAS MIGRADAS PARA admin_bp


# ROTAS MIGRADAS PARA admin_bp


# ROTAS MIGRADAS PARA admin_bp


# ROTAS MIGRADAS PARA admin_bp


# ============================================================================
# ENDPOINTS DE SURVIVAL STATS
# ============================================================================


# ROTAS MIGRADAS PARA survival_bp


# ROTAS MIGRADAS PARA survival_bp


# ============================================================================
# ENDPOINTS DO SISTEMA DE CHAT
# ============================================================================


# ROTAS MIGRADAS PARA chat_bp


# ROTAS MIGRADAS PARA chat_bp


# ROTAS MIGRADAS PARA chat_bp


# ROTAS MIGRADAS PARA chat_bp


# ROTAS MIGRADAS PARA chat_bp


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================


def main():
    """Função principal"""
    # sys já está importado no topo do arquivo
    import argparse
    import traceback

    # SEGURANÇA: Verificar se está sendo chamado durante validação do Panel SSM
    # Se sim, não inicializar backend (validação deve ser isolada)
    stack = traceback.extract_stack()
    for frame in stack:
        frame_file = str(frame.filename).lower()
        if (
            "gui" in frame_file
            or "main_window" in frame_file
            or ("validate" in frame_file.lower() and "gui" in frame_file)
        ):
            # Está sendo chamado do Panel SSM durante validação - não inicializar backend
            print(
                "ERRO CRÍTICO: main() não pode ser chamado durante validação do Panel SSM."
            )
            print(
                "A validação deve usar apenas os módulos de licenciamento diretamente."
            )
            print(f"Chamado de: {frame_file}")
            sys.exit(1)

    # SEGURANÇA: Verificar se já existe instância rodando
    from utils.single_instance import ensure_single_instance

    def _run_scum_server_installer(base_dir: str, installer_state_dir: str = "") -> int:
        import json
        import os
        import subprocess
        import sys
        import time
        import urllib.request
        import zipfile
        from collections import deque
        from pathlib import Path

        if installer_state_dir:
            state_dir = Path(installer_state_dir)
        else:
            program_data = os.environ.get("PROGRAMDATA") or "C:\\ProgramData"
            state_dir = Path(program_data) / "SSM" / "installer"

        logs_dir = state_dir / "logs"
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        log_path = logs_dir / "scum_installer.log"
        status_path = state_dir / "scum_installer_status.json"

        def write_status(state: str, message: str, progress: int = 0):
            payload = {
                "state": state,
                "message": message,
                "progress": progress,
                "updated_at": int(time.time()),
            }
            try:
                with open(status_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        def log_line(text: str):
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{ts}] {text}"
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass
            try:
                print(line)
            except Exception:
                pass

        try:
            base = Path(base_dir)
            steamcmd_dir = base / "steamcmd"
            scum_install_dir = base / "scum"
            steamcmd_exe = steamcmd_dir / "steamcmd.exe"
            steamcmd_zip_url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
            steamcmd_zip_path = steamcmd_dir / "steamcmd.zip"

            write_status("running", "Preparing folders", 5)
            log_line("[1/4] Preparing folders...")
            steamcmd_dir.mkdir(parents=True, exist_ok=True)
            scum_install_dir.mkdir(parents=True, exist_ok=True)

            if not steamcmd_exe.exists():
                write_status("running", "Downloading SteamCMD", 15)
                log_line("[2/4] Downloading SteamCMD...")
                try:
                    if steamcmd_zip_path.exists():
                        steamcmd_zip_path.unlink()
                except Exception:
                    pass

                urllib.request.urlretrieve(steamcmd_zip_url, str(steamcmd_zip_path))

                write_status("running", "Extracting SteamCMD", 25)
                log_line("Extracting SteamCMD...")
                with zipfile.ZipFile(str(steamcmd_zip_path), "r") as z:
                    z.extractall(str(steamcmd_dir))

            if not steamcmd_exe.exists():
                msg = f"SteamCMD not found after extraction: {steamcmd_exe}"
                write_status("error", msg, 0)
                log_line(f"ERROR: {msg}")
                return 1

            write_status("running", "Initializing SteamCMD", 35)
            log_line("[3/4] Initializing SteamCMD...")
            def _run_steamcmd_stream(
                args_list,
                timeout_seconds: int,
                heartbeat_message: str = "",
                heartbeat_progress_range: tuple = None,
            ) -> tuple:
                """Run steamcmd and stream output to log in real time. Returns (returncode, last_output)."""
                last_lines = deque(maxlen=200)
                start = time.time()
                last_activity = time.time()
                last_heartbeat = 0.0
                last_heartbeat_log = 0.0
                heartbeat_progress = None
                if heartbeat_progress_range and len(heartbeat_progress_range) == 2:
                    heartbeat_progress = heartbeat_progress_range[0]

                p = subprocess.Popen(
                    [str(steamcmd_exe)] + args_list,
                    cwd=str(steamcmd_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=False,
                    bufsize=0,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ),
                )

                try:
                    assert p.stdout is not None
                    q: "queue.Queue[bytes | None]" = queue.Queue()

                    def _reader():
                        try:
                            while True:
                                data = p.stdout.read(1024)
                                if not data:
                                    break
                                q.put(data)
                        except Exception:
                            pass
                        finally:
                            try:
                                q.put(None)
                            except Exception:
                                pass

                    reader_t = threading.Thread(target=_reader, daemon=True)
                    reader_t.start()

                    buffer = ""
                    saw_eof = False
                    while True:
                        if timeout_seconds and (time.time() - start) > timeout_seconds:
                            try:
                                p.kill()
                            except Exception:
                                pass
                            break

                        # Heartbeat: se ficar muito tempo sem output, atualizar status com progresso estimado
                        now = time.time()
                        if (
                            heartbeat_progress is not None
                            and heartbeat_message
                            and (now - last_activity) > 8
                            and (now - last_heartbeat) > 8
                        ):
                            last_heartbeat = now
                            try:
                                lo, hi = heartbeat_progress_range
                                # sobe devagar e para antes do final da faixa
                                heartbeat_progress = min(int(heartbeat_progress + 1), int(hi))
                                write_status("running", heartbeat_message, int(heartbeat_progress))
                            except Exception:
                                pass

                            # Também escrever no log/console para evitar sensação de travamento no CLI
                            if (now - last_heartbeat_log) > 15:
                                last_heartbeat_log = now
                                try:
                                    log_line(
                                        f"{heartbeat_message}... ({int(heartbeat_progress)}%)"
                                    )
                                except Exception:
                                    pass

                        try:
                            item = q.get(timeout=0.1)
                        except queue.Empty:
                            if p.poll() is not None and saw_eof:
                                break
                            continue

                        if item is None:
                            saw_eof = True
                            if p.poll() is not None:
                                break
                            continue

                        try:
                            text = item.decode("utf-8", errors="replace")
                        except Exception:
                            text = str(item)

                        buffer += text

                        # SteamCMD usa muito '\r' para progressos (sem '\n')
                        while True:
                            idx_r = buffer.find("\r")
                            idx_n = buffer.find("\n")
                            if idx_r == -1 and idx_n == -1:
                                break

                            if idx_r != -1 and idx_n != -1:
                                idx = min(idx_r, idx_n)
                            elif idx_r != -1:
                                idx = idx_r
                            elif idx_n != -1:
                                idx = idx_n

                            line = buffer[:idx].strip()
                            buffer = buffer[idx + 1 :]
                            if line:
                                last_lines.append(line)
                                log_line(line)
                                last_activity = time.time()

                    try:
                        reader_t.join(timeout=1)
                    except Exception:
                        pass

                    try:
                        p.wait(timeout=5)
                    except Exception:
                        pass
                finally:
                    try:
                        if p.stdout:
                            p.stdout.close()
                    except Exception:
                        pass

                return int(p.returncode or 0), "\n".join(list(last_lines))

            # SteamCMD frequentemente se auto-atualiza na primeira execução e pode retornar código != 0.
            # Para ficar robusto, tentamos algumas vezes antes de falhar.
            init_ok = False
            last_init_output = ""
            for attempt in range(1, 4):
                try:
                    log_line(f"SteamCMD init attempt {attempt}/3...")
                    rc, combined = _run_steamcmd_stream(
                        ["+quit"],
                        timeout_seconds=600,
                        heartbeat_message="Initializing SteamCMD",
                        heartbeat_progress_range=(35, 54),
                    )
                    combined = (combined or "").strip()
                    last_init_output = combined

                    if rc == 0:
                        init_ok = True
                        break

                    # Heurística: se o SteamCMD está aplicando update, normalmente ele finaliza e relança.
                    # Damos um tempo e tentamos de novo.
                    lowered = combined.lower()
                    if (
                        "update complete" in lowered
                        or "atualiza" in lowered
                        or "applying update" in lowered
                        or "downloading update" in lowered
                        or "checking for available update" in lowered
                    ):
                        time.sleep(8)
                        continue

                    # Caso genérico: aguardar pouco e tentar novamente
                    time.sleep(5)
                except subprocess.TimeoutExpired:
                    last_init_output = "SteamCMD init timeout"
                    log_line("SteamCMD init timeout, retrying...")
                    time.sleep(5)

            if not init_ok:
                msg = last_init_output or "SteamCMD init failed"
                write_status("error", msg, 0)
                log_line(f"ERROR: SteamCMD init failed after retries: {msg}")
                return 1

            write_status("running", "Installing/Updating SCUM Server", 55)
            log_line("[4/4] Installing/Updating SCUM Server...")

            install_ok = False
            last_install_output = ""
            for attempt in range(1, 4):
                log_line(f"SCUM install attempt {attempt}/3...")
                rc, combined = _run_steamcmd_stream(
                    [
                        "+force_install_dir",
                        str(scum_install_dir),
                        "+login",
                        "anonymous",
                        "+app_update",
                        "3792580",
                        "+quit",
                    ],
                    timeout_seconds=3600,
                    heartbeat_message="Installing/Updating SCUM Server",
                    heartbeat_progress_range=(55, 84),
                )

                combined = (combined or "").strip()
                last_install_output = combined

                if rc == 0:
                    install_ok = True
                    break

                lowered = combined.lower()
                if "missing configuration" in lowered:
                    # SteamCMD às vezes falha com isso logo após update/primeiro login.
                    # Tentar re-inicializar e repetir.
                    log_line("SteamCMD reported 'Missing configuration' - reinitializing and retrying...")
                    try:
                        _run_steamcmd_stream(
                            ["+quit"],
                            timeout_seconds=600,
                            heartbeat_message="Initializing SteamCMD",
                            heartbeat_progress_range=(35, 54),
                        )
                    except Exception:
                        pass
                    time.sleep(10)
                    continue

                # Falha genérica: aguardar e tentar novamente
                time.sleep(8)

            if not install_ok:
                msg = last_install_output or "SteamCMD app_update failed"
                write_status("error", msg, 0)
                log_line(f"ERROR: SCUM install/update failed after retries: {msg}")
                return 1

            # Preparar estrutura de pastas esperada pelo backend (o SCUM.db só é criado após o servidor rodar).
            try:
                (scum_install_dir / "SCUM" / "Saved" / "SaveFiles").mkdir(
                    parents=True, exist_ok=True
                )
                (scum_install_dir / "SCUM" / "Saved" / "SaveFiles" / "Logs").mkdir(
                    parents=True, exist_ok=True
                )
                (scum_install_dir / "SCUM" / "Saved" / "Config" / "WindowsServer").mkdir(
                    parents=True, exist_ok=True
                )
            except Exception:
                pass

            write_status("running", "Updating configuration", 85)
            log_line("Updating config.json paths...")

            if getattr(sys, "frozen", False):
                app_dir = Path(sys.executable).parent
            else:
                app_dir = Path(__file__).resolve().parent

            data_dir = DATA_DIR if getattr(sys, "frozen", False) else (app_dir / "data")
            config_path = data_dir / "config.json"
            if not config_path.exists():
                msg = f"config.json not found: {config_path}"
                write_status("error", msg, 0)
                log_line(f"ERROR: {msg}")
                return 1

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f) or {}

            config.setdefault("server", {})
            config["server"]["steamcmd_path"] = str(steamcmd_dir)

            config.setdefault("paths", {})
            config["paths"].setdefault("scum_server", {})
            scum_paths = config["paths"]["scum_server"]
            scum_paths["root_directory"] = str(scum_install_dir)
            scum_paths["binaries_directory"] = str(scum_install_dir / "SCUM" / "Binaries" / "Win64")
            scum_paths["logs_directory"] = str(scum_install_dir / "SCUM" / "Saved" / "SaveFiles" / "Logs")
            scum_paths["config_directory"] = str(scum_install_dir / "SCUM" / "Saved" / "Config" / "WindowsServer")
            scum_paths["database"] = str(scum_install_dir / "SCUM" / "Saved" / "SaveFiles" / "SCUM.db")
            scum_paths["savefiles_directory"] = str(scum_install_dir / "SCUM" / "Saved" / "SaveFiles")

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            write_status("success", "SCUM Server installed/updated successfully", 100)
            log_line("SUCCESS: Installation completed.")
            return 0
        except Exception as e:
            write_status("error", str(e), 0)
            try:
                log_line(f"ERROR: {e}")
            except Exception:
                pass
            return 1

    parser = argparse.ArgumentParser(description="SSM Backend")
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="Executar em modo GUI (desktop)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--install-scum-server",
        action="store_true",
        help="Instalar/atualizar SCUM Server (SteamCMD) e sair",
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default="C:\\Servers",
        help="Diretorio base para instalar (cria steamcmd/ e scum/ dentro)",
    )
    parser.add_argument(
        "--installer-state-dir",
        type=str,
        default="",
        help="Diretorio para estado/logs do instalador (default: ProgramData\\SSM\\installer)",
    )
    args = parser.parse_args()

    if args.install_scum_server:
        from installer.scum_server_installer import run_scum_server_installer

        exit_code = run_scum_server_installer(args.base_dir, args.installer_state_dir)
        sys.exit(exit_code)

    # Se modo GUI, usar gui_runner (já tem verificação de single instance)
    if args.gui and not args.desktop:
        try:
            print("[WARN] '--gui' is deprecated. Use '--desktop' instead.")
        except Exception:
            pass
    if args.desktop or args.gui:
        try:
            from gui.gui_runner import run_gui_mode

            run_gui_mode()
            return
        except ImportError as e:
            print(f"Erro ao importar GUI: {e}")
            print("Instale customtkinter: pip install customtkinter pyperclip")
            sys.exit(1)

    # Modo normal (apenas API) - verificar single instance
    instance_lock = ensure_single_instance("ssm_backend_api")
    if instance_lock is None:
        # Já existe outra instância - sair
        sys.exit(0)

    # Modo normal (apenas API)
    try:
        # Inicializar componentes
        init_components()

        # Obter configurações da API
        api_config = config.get("api", {})
        host = api_config.get("host", "127.0.0.1")
        port = api_config.get("port", 3000)
        debug = api_config.get("debug", False)

        logger.info(f"Servidor API iniciando na porta {port}")

        # Agendar sincronizações iniciais para depois do servidor iniciar
        schedule_initial_syncs()

        # Desabilitar logs do Flask para não expor URLs e IPs
        import logging

        # sys já está importado no topo do arquivo
        from io import StringIO

        # Silenciar werkzeug completamente
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)
        log.disabled = True

        # Silenciar mensagens de inicialização do Flask
        # Capturar stdout temporariamente durante app.run() para filtrar mensagens de debug
        class FlaskOutputFilter:
            def __init__(self, original_stream):
                self.original_stream = original_stream
                self.filtered_patterns = [
                    "* Serving Flask app",
                    "* Debug mode:",
                    "WARNING: This is a development server",
                    "Consider using",
                ]

            def write(self, text):
                # Filtrar mensagens específicas do Flask
                if any(pattern in text for pattern in self.filtered_patterns):
                    return  # Não escrever essas mensagens
                self.original_stream.write(text)

            def flush(self):
                self.original_stream.flush()

            def __getattr__(self, name):
                return getattr(self.original_stream, name)

        # Redirecionar stdout temporariamente para filtrar mensagens do Flask
        original_stdout = sys.stdout
        sys.stdout = FlaskOutputFilter(original_stdout)

        try:
            # Iniciar servidor Flask
            app.run(
                host=host,
                port=port,
                debug=debug,
                threaded=True,
                use_reloader=False,  # Desabilitar reloader para evitar logs extras
            )
        finally:
            # Restaurar stdout original
            sys.stdout = original_stdout

    except KeyboardInterrupt:
        if logger:
            logger.info("SCUM Backend encerrado pelo usuário")
        else:
            print("SCUM Backend encerrado pelo usuário")
    except Exception as e:
        if logger:
            logger.error(f"Erro fatal: {e}")
        else:
            print(f"Erro fatal: {e}")
            import traceback

            traceback.print_exc()
        sys.exit(1)
    finally:
        # Liberar lock ao sair
        if "instance_lock" in locals() and instance_lock:
            instance_lock.release()


# ROTAS MIGRADAS PARA chat_bp


# ============================================================================
# API ENDPOINTS - PERMISSÕES
# ============================================================================


# ROTAS MIGRADAS PARA players_bp


# ROTAS MIGRADAS PARA players_bp


# ROTAS MIGRADAS PARA players_bp


# ROTAS MIGRADAS PARA permissions_bp


# ROTAS MIGRADAS PARA permissions_bp


# ROTAS MIGRADAS PARA permissions_bp


# ROTAS MIGRADAS PARA permissions_bp


# ROTAS MIGRADAS PARA chat_bp


# ROTAS MIGRADAS PARA chat_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA notifications_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ROTAS MIGRADAS PARA scheduler_bp


# ============================================================================
# FUNÇÕES E ENDPOINTS DO SISTEMA DE BAÚS
# ============================================================================

_CHEST_CLASS_DISPLAY: Dict[str, str] = {
    "Improvised_Metal_Chest_ES": "Metal",
    "ImprovisedMetalChest": "Metal",
    "Improved_Wooden_Chest_ES": "Wooden",
    "ImprovedWoodenChest": "Wooden",
    "Improvised_Wooden_Chest_ES": "Wooden",
    "ImprovisedWoodenChest": "Wooden",
    "MedicalLocker_C": "Medical Locker",
    "ImprovisedWardrobe_C": "Wardrobe",
    "StorageShelf_C": "Storage Shelf",
    "WoodenWeaponRack_C": "Weapon Rack",
}


def _get_chest_display_name_api(chest_class: Optional[str]) -> str:
    """Retornar nome amigável para o tipo de baú."""
    if not chest_class:
        return "Desconhecido"

    if chest_class in _CHEST_CLASS_DISPLAY:
        return _CHEST_CLASS_DISPLAY[chest_class]

    lowered = chest_class.lower()
    if "wood" in lowered:
        return "Wooden"
    if "metal" in lowered:
        return "Metal"
    if "steel" in lowered:
        return "Steel"

    return chest_class


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fetch_chest_rows(
    filters: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> Tuple[List[sqlite3.Row], Optional[int]]:
    """Consultar registros da tabela chest_snapshot com filtros opcionais."""
    if not path_helper:
        raise RuntimeError("Configuração não carregada - path_helper indisponível.")

    db_path = path_helper.get_ssm_db_path()
    with DatabaseConnector.get_connection(db_path, write_mode=False) as conn:
        conn.row_factory = sqlite3.Row

        filters = filters or {}
        where_clauses: List[str] = []
        params: List[Any] = []

        steam_id_filter = filters.get("steam_id")
        if steam_id_filter is not None:
            where_clauses.append("steam_id = ?")
            params.append(steam_id_filter)

        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        base_query = f"""
            SELECT
                entity_id,
                container_entity_id,
                chest_class,
                owner_profile_id,
                steam_id,
                player_name,
                fake_name,
                custom_name,
                location_x,
                location_y,
                location_z,
                rotation_x,
                rotation_y,
                rotation_z,
                vehicle_container_class,
                vehicle_entity_id,
                vehicle_class,
                vehicle_owner_name,
                vehicle_owner_steam_id,
                vehicle_owner_player_id,
                vehicle_registered_at,
                vehicle_owner_mismatch,
                last_seen_at,
                created_at
            FROM chest_snapshot
            {where_clause}
            ORDER BY last_seen_at DESC
        """

        query_params = list(params)
        if limit is not None:
            base_query += " LIMIT ?"
            query_params.append(limit)
            if offset:
                base_query += " OFFSET ?"
                query_params.append(offset)
        elif offset:
            base_query += " LIMIT -1 OFFSET ?"
            query_params.append(offset)

        try:
            cursor = conn.execute(base_query, query_params)
            rows = cursor.fetchall()

            total = None
            if limit is not None or offset:
                count_query = f"SELECT COUNT(*) AS total FROM chest_snapshot {where_clause}"
                count_cursor = conn.execute(count_query, params)
                total_row = count_cursor.fetchone()
                total = total_row["total"] if total_row else 0

            return rows, total
        except Exception as e:
            raise e


def _serialize_chest_row(row: sqlite3.Row) -> Dict[str, Any]:
    """Transformar linha do banco em estrutura pronta para API."""
    vehicle_info = None
    if (
        row["vehicle_entity_id"]
        or row["vehicle_class"]
        or row["vehicle_container_class"]
    ):
        vehicle_info = {
            "entity_id": row["vehicle_entity_id"],
            "class": row["vehicle_class"],
            "container_class": row["vehicle_container_class"],
            "owner_name": row["vehicle_owner_name"],
            "owner_steam_id": row["vehicle_owner_steam_id"],
            "owner_player_id": row["vehicle_owner_player_id"],
            "registered_at": row["vehicle_registered_at"],
        }

    return {
        "entity_id": row["entity_id"],
        "container_entity_id": row["container_entity_id"],
        "owner_profile_id": row["owner_profile_id"],
        "steam_id": row["steam_id"],
        "player_name": row["player_name"],
        "fake_name": row["fake_name"],
        "custom_name": row["custom_name"],
        "chest_class": row["chest_class"],
        "chest_type": _get_chest_display_name_api(row["chest_class"]),
        "location": {
            "x": _safe_float(row["location_x"]),
            "y": _safe_float(row["location_y"]),
            "z": _safe_float(row["location_z"]),
        },
        "rotation": {
            "x": _safe_float(row["rotation_x"]),
            "y": _safe_float(row["rotation_y"]),
            "z": _safe_float(row["rotation_z"]),
        },
        "vehicle_owner_mismatch": (
            bool(row["vehicle_owner_mismatch"])
            if row["vehicle_owner_mismatch"] is not None
            else False
        ),
        "vehicle": vehicle_info,
        "last_seen_at": row["last_seen_at"],
        "created_at": row["created_at"],
        "has_vehicle": vehicle_info is not None,
    }


def _build_chest_player_summary(chests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Gerar resumo por jogador para facilitar filtros."""
    summary: Dict[str, Dict[str, Any]] = {}
    for chest in chests:
        key = chest.get("steam_id") or "__UNKNOWN__"
        entry = summary.setdefault(
            key,
            {
                "steam_id": None if key == "__UNKNOWN__" else key,
                "count": 0,
                "player_name": chest.get("player_name"),
                "fake_name": chest.get("fake_name"),
            },
        )
        entry["count"] += 1
        if not entry.get("player_name") and chest.get("player_name"):
            entry["player_name"] = chest["player_name"]
        if not entry.get("fake_name") and chest.get("fake_name"):
            entry["fake_name"] = chest["fake_name"]
    return sorted(summary.values(), key=lambda item: item["count"], reverse=True)


def _str_to_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


# ROTAS MIGRADAS PARA chests_bp


# ROTAS MIGRADAS PARA chests_bp


# ROTAS MIGRADAS PARA chests_bp


# ROTAS MIGRADAS PARA chests_bp


# ============================================================================
# ENDPOINTS DO SISTEMA DE VEÍCULOS
# ============================================================================


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ============================================================================
# ENDPOINTS DO SISTEMA DE GPS
# ============================================================================


# ROTAS MIGRADAS PARA gps_bp


# ROTAS MIGRADAS PARA gps_bp


# ROTAS MIGRADAS PARA gps_bp


# ROTAS MIGRADAS PARA gps_bp


# ROTAS MIGRADAS PARA gps_bp


# ============================================================================
# ENDPOINTS DE ELEVATED USERS
# ============================================================================


# ROTAS MIGRADAS PARA elevated_users_bp


# ROTAS MIGRADAS PARA elevated_users_bp


# ROTAS MIGRADAS PARA players_bp


# ROTAS MIGRADAS PARA elevated_users_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ROTAS MIGRADAS PARA vehicles_bp


# ============================================================================
# ENDPOINTS DO SISTEMA DE RANKINGS
# ============================================================================


# ROTAS MIGRADAS PARA rankings_bp


# ROTAS MIGRADAS PARA rankings_bp


# ROTAS MIGRADAS PARA rankings_bp


# ROTAS MIGRADAS PARA rankings_bp


# ROTAS MIGRADAS PARA rankings_bp


# ROTAS MIGRADAS PARA rankings_bp


# ROTAS MIGRADAS PARA rankings_bp


# ROTAS MIGRADAS PARA rankings_bp


# ROTAS MIGRADAS PARA rankings_bp


# ROTAS MIGRADAS PARA rankings_bp


# ROTAS MIGRADAS PARA rankings_bp


if __name__ == "__main__":
    main()
