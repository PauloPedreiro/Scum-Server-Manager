"""
Blueprint: admin
"""
from core.database.connector import DatabaseConnector

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac
from functools import wraps
from core.auth.decorators import require_auth, require_admin, require_player_auth
from utils.scum_db_helper import scum_db_readonly_connection_strict
from utils.integration_helpers import require_integration_key
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import sqlite3

from .helpers import (
    _get_ssm_database_path,
    _get_scum_database_path,
    _is_player_online,
    _server_must_be_offline_for_scum_db_write
)
from utils.scum_attributes_editor import (
    fetch_prisoners as scum_fetch_prisoners,
    resolve_prisoner_identifier as scum_resolve_prisoner_identifier,
    get_prisoner_attributes as scum_get_prisoner_attributes,
    update_prisoner_attributes as scum_update_prisoner_attributes,
    create_scum_db_backup
)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/api/identity", methods=["GET"])
def get_backend_identity():
    """Obter identidade do backend"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        if not backend_identity:
            return (
                jsonify(
                    {"success": False, "error": "BackendIdentity não inicializado"}
                ),
                500,
            )

        return jsonify(
            {
                "success": True,
                "data": backend_identity.get_identity(),
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter identidade: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/remote/command", methods=["POST"])
def handle_remote_command():
    """Processar comando remoto do frontend central"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        data = request.get_json() or {}

        if not remote_command_handler:
            return (
                jsonify(
                    {"success": False, "error": "RemoteCommandHandler não inicializado"}
                ),
                500,
            )

        result = remote_command_handler.handle_command(data)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao processar comando remoto: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/health/detailed", methods=["GET"])
def get_detailed_health():
    """Health check detalhado para monitoramento central"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        health_data = {
            "backend_id": (
                backend_identity.get_backend_id() if backend_identity else None
            ),
            "owner_id": backend_identity.get_owner_id() if backend_identity else None,
            "status": "healthy",
            "timestamp": time.time(),
            "components": {
                "server_manager": server_manager is not None,
                "restart_scheduler": restart_scheduler is not None,
                "notification_manager": notification_manager is not None,
                "discord_webhook": discord_webhook is not None,
                "backend_identity": backend_identity is not None,
                "heartbeat_manager": heartbeat_manager is not None,
                "remote_command_handler": remote_command_handler is not None,
                "license_validator": license_validator is not None,
            },
            "server_status": server_manager.get_status() if server_manager else {},
            "heartbeat_status": (
                heartbeat_manager.get_heartbeat_status() if heartbeat_manager else {}
            ),
            "license_status": (
                license_validator.get_license_status() if license_validator else {}
            ),
        }

        return jsonify(health_data)

    except Exception as e:
        logger.error(f"Erro no health check detalhado: {e}")
        return (
            jsonify({"status": "unhealthy", "error": str(e), "timestamp": time.time()}),
            500,
        )


@admin_bp.route("/api/owner/info", methods=["GET"])
def get_owner_info():
    """Obter informações do proprietário"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        if not owner_manager:
            return (
                jsonify({"success": False, "error": "OwnerManager não inicializado"}),
                500,
            )

        return jsonify(
            {
                "success": True,
                "data": owner_manager.get_owner_info(),
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter informações do proprietário: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/owner/info", methods=["POST"])
def update_owner_info():
    """Atualizar informações do proprietário"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        data = request.get_json() or {}

        if not owner_manager:
            return (
                jsonify({"success": False, "error": "OwnerManager não inicializado"}),
                500,
            )

        owner_name = data.get("owner_name")
        email = data.get("email")
        region = data.get("region", "america_south")

        if not owner_name:
            return (
                jsonify(
                    {"success": False, "error": "Nome do proprietário é obrigatório"}
                ),
                400,
            )

        # Gerar owner_id se não existir
        owner_id = data.get("owner_id")
        if not owner_id:
            import uuid

            owner_id = f"OWNER-{str(uuid.uuid4()).replace('-', '').upper()[:12]}"

        owner_manager.set_owner_info(owner_id, owner_name, email, region)

        # Atualizar backend_identity se disponível
        if backend_identity:
            backend_identity.set_owner_id(owner_id)
            backend_identity.set_region(region)

        return jsonify(
            {
                "success": True,
                "message": "Informações do proprietário atualizadas",
                "data": {
                    "owner_id": owner_id,
                    "owner_name": owner_name,
                    "region": region,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao atualizar informações do proprietário: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/attributes/prisoners", methods=["GET"])
@require_auth
def list_scum_prisoners():
    """Listar prisioneiros (SCUM.db) para selecao no frontend."""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        scum_db_path, error = _get_scum_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        limit = request.args.get("limit", default=200, type=int)
        offset = request.args.get("offset", default=0, type=int)
        q = (request.args.get("query") or "").strip().lower()

        if limit is None or limit < 1:
            limit = 200
        elif limit > 2000:
            limit = 2000

        if offset is None or offset < 0:
            offset = 0

        with scum_db_readonly_connection_strict(scum_db_path) as conn:
            cur = conn.cursor()
            prisoners = scum_fetch_prisoners(cur)

        if q:
            prisoners = [
                p
                for p in prisoners
                if q in str(p.get("prisoner_id", "")).lower()
                or q in str(p.get("steam_id") or "").lower()
                or q in str(p.get("name") or "").lower()
            ]

        total = len(prisoners)
        page = prisoners[offset : offset + limit]

        return jsonify(
            {
                "success": True,
                "data": {
                    "prisoners": page,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "count": len(page),
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao listar prisioneiros no SCUM.db: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/attributes/prices", methods=["GET"])
@require_auth
def get_attribute_upgrade_prices():
    """Obter preços de upgrades de atributos cadastrados no banco SSM.db"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        # Inicializar com valores de fallback zerados (inativo por padrão) para caso o banco esteja vazio
        prices = {
            "strength": {
                "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0
            },
            "constitution": {
                "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
            },
            "dexterity": {
                "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
            },
            "intelligence": {
                "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
            }
        }

        expiration_enabled = 0
        expiration_duration_days = 30

        with DatabaseConnector.get_connection(ssm_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT attribute_name, level, price 
                FROM attribute_upgrade_prices
                """
            )
            for attr, lvl, pr in cursor.fetchall():
                if attr in prices:
                    prices[attr][str(lvl)] = int(pr)

            # Buscar configurações globais de expiração de atributos
            cursor.execute(
                "SELECT key, value FROM app_config WHERE key IN (?, ?)",
                ("attributes.expiration.enabled", "attributes.expiration.duration_days")
            )
            for key, val in cursor.fetchall():
                if key == "attributes.expiration.enabled":
                    expiration_enabled = int(val) if str(val).isdigit() else 0
                elif key == "attributes.expiration.duration_days":
                    expiration_duration_days = int(val) if str(val).isdigit() else 30

        return jsonify({
            "success": True,
            "data": {
                "prices": prices,
                "expiration_enabled": expiration_enabled,
                "expiration_duration_days": expiration_duration_days
            }
        })
    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter preços de atributos do banco: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/attributes/prices", methods=["PUT"])
@require_auth
@require_admin
def update_attribute_upgrade_prices():
    """Atualizar preços de upgrades de atributos no banco SSM.db. Requer admin."""
    services = get_services()
    logger = getattr(services, 'logger', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json() or {}
        prices = payload.get("prices")
        
        # Retrocompatibilidade: se "prices" não estiver no payload e as outras chaves de expiração
        # também não, significa que o payload inteiro é o dicionário de preços.
        if prices is None:
            if "expiration_enabled" not in payload and "expiration_duration_days" not in payload:
                prices = payload
            else:
                prices = {}

        if not isinstance(prices, dict):
            return jsonify({"success": False, "error": "Payload inválido. Esperado um objeto."}), 400

        allowed_attrs = {"strength", "constitution", "dexterity", "intelligence"}
        
        # Mapeamento robusto para normalizar os nomes dos atributos
        attr_mapping = {
            "strength": "strength",
            "forca": "strength",
            "força": "strength",
            "force": "strength",
            
            "constitution": "constitution",
            "constituiçao": "constitution",
            "constituição": "constitution",
            
            "dexterity": "dexterity",
            "destreza": "dexterity",
            
            "intelligence": "intelligence",
            "inteligencia": "intelligence",
            "inteligência": "intelligence"
        }
        
        # Validar estrutura recebida de preços
        insert_rows = []
        for attr, lvls in prices.items():
            if not isinstance(attr, str):
                continue
            normalized_attr = attr_mapping.get(attr.lower().strip())
            if not normalized_attr:
                if logger:
                    logger.warning(f"[API Prices] Atributo enviado desconhecido ignorado: {attr}")
                continue
            if not isinstance(lvls, dict):
                return jsonify({"success": False, "error": f"Formato inválido para o atributo '{attr}'. Deve ser um dicionário de nível: preço."}), 400
            for lvl_str, pr_val in lvls.items():
                try:
                    lvl = int(lvl_str)
                    pr = int(pr_val)
                except (ValueError, TypeError):
                    return jsonify({"success": False, "error": f"Nível ou preço inválido para '{attr}': {lvl_str}={pr_val}"}), 400
                
                # Regras de limite de níveis usando o atributo normalizado
                max_level = 8 if normalized_attr == "strength" else 5
                if lvl < 1 or lvl > max_level:
                    return jsonify({"success": False, "error": f"Nível {lvl} inválido para '{attr}'. Limite para força é 1-8, outros 1-5."}), 400
                if pr < 0:
                    return jsonify({"success": False, "error": f"Preço não pode ser negativo para '{attr}' nível {lvl}."}), 400
                
                insert_rows.append((normalized_attr, lvl, pr))

        # Validar e coletar alterações de expiração
        expiration_updates = []
        if "expiration_enabled" in payload:
            val = "1" if payload["expiration_enabled"] in (1, True, "1") else "0"
            expiration_updates.append(("attributes.expiration.enabled", val))
            
        if "expiration_duration_days" in payload:
            try:
                days = int(payload["expiration_duration_days"])
                if days < 1:
                    return jsonify({"success": False, "error": "A duração de expiração deve ser de pelo menos 1 dia."}), 400
                expiration_updates.append(("attributes.expiration.duration_days", str(days)))
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "A duração de expiração deve ser um número inteiro válido."}), 400

        # Persistir no banco de dados com transação única
        with DatabaseConnector.get_connection(ssm_db_path, write_mode=True) as conn:
            cursor = conn.cursor()
            
            # Se enviou preços no payload, atualizar tabela de preços
            if prices:
                cursor.execute("DELETE FROM attribute_upgrade_prices")
                if insert_rows:
                    cursor.executemany(
                        """
                        INSERT INTO attribute_upgrade_prices (attribute_name, level, price)
                        VALUES (?, ?, ?)
                        """,
                        insert_rows
                    )

            # Atualizar configs de expiração
            if expiration_updates:
                cursor.executemany(
                    """
                    INSERT INTO app_config (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    expiration_updates
                )
            conn.commit()

            if logger:
                logger.info(
                    f"[API Prices] Preços/Expiracão atualizados com sucesso. "
                    f"Preços salvos: {len(insert_rows)}, Expiracão atualizada: {len(expiration_updates)}"
                )

        return jsonify({
            "success": True,
            "message": "Configurações de upgrades de atributos salvas com sucesso no banco de dados."
        })
    except Exception as e:
        if logger:
            logger.error(f"Erro ao salvar configurações de atributos no banco: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/attributes/player/<identifier>", methods=["GET"])
@require_auth
def get_scum_player_attributes(identifier: str):
    """Obter atributos (STR/CON/DEX/INT) de um player do SCUM.db por steam_id ou prisoner_id."""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        scum_db_path, error = _get_scum_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with scum_db_readonly_connection_strict(scum_db_path) as conn:
            cur = conn.cursor()
            resolved = scum_resolve_prisoner_identifier(cur, identifier)
            if not resolved:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Jogador '{identifier}' não encontrado no SCUM.db",
                        }
                    ),
                    404,
                )

            attrs = scum_get_prisoner_attributes(cur, int(resolved["prisoner_id"]))
            if attrs is None:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Não foi possível ler atributos do prisioneiro {resolved['prisoner_id']}",
                        }
                    ),
                    500,
                )

        return jsonify(
            {
                "success": True,
                "data": {
                    "player": resolved,
                    "attributes": attrs,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter atributos do player '{identifier}': {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/attributes/player/<identifier>", methods=["PATCH"])
@require_auth
@require_admin
def patch_scum_player_attributes(identifier: str):
    """Atualizar atributos (STR/CON/DEX/INT) de um player no SCUM.db. Requer admin."""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        scum_db_path, error = _get_scum_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        # Resolver player antes das travas (precisamos do steam_id para checar online)
        with scum_db_readonly_connection_strict(scum_db_path) as conn_ro:
            cur_ro = conn_ro.cursor()
            resolved = scum_resolve_prisoner_identifier(cur_ro, identifier)
            if not resolved:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Jogador '{identifier}' não encontrado no SCUM.db",
                        }
                    ),
                    404,
                )

        payload = request.get_json() or {}
        attrs_payload = (
            payload.get("attributes")
            if isinstance(payload.get("attributes"), dict)
            else payload
        )

        allowed_keys = {"strength", "constitution", "dexterity", "intelligence"}
        incoming: Dict[str, Any] = {
            k: v for k, v in (attrs_payload or {}).items() if k in allowed_keys
        }

        if not incoming:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Nenhum atributo enviado. Envie strength/constitution/dexterity/intelligence.",
                    }
                ),
                400,
            )

        def _coerce_float(val: Any) -> Optional[float]:
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                try:
                    return float(val.replace(",", "."))
                except Exception:
                    return None
            return None

        ranges = {
            "strength": (1.0, 8.0),
            "constitution": (1.0, 5.0),
            "dexterity": (1.0, 5.0),
            "intelligence": (1.0, 5.0),
        }

        new_values: Dict[str, float] = {}
        for k, v in incoming.items():
            fv = _coerce_float(v)
            if fv is None:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Valor inválido para '{k}'. Envie número.",
                        }
                    ),
                    400,
                )
            min_v, max_v = ranges[k]
            if not (min_v <= fv <= max_v):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"'{k}' deve estar entre {min_v} e {max_v}",
                        }
                    ),
                    400,
                )
            new_values[k] = float(fv)

        # RCON approach (como agora usamos apenas RCON, o jogador precisa estar online)
        from utils.rcon_client import get_rcon_client_from_config
        from utils.scum_attributes_editor import apply_attribute_and_skills_via_rcon

        rcon_client = get_rcon_client_from_config()
        if not rcon_client:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "O RCON está desativado nas configurações do servidor. O jogador precisa estar online e o RCON habilitado.",
                    }
                ),
                400,
            )

        # Obter atributos atuais para mesclar (SCUM.db + SSM.db cache)
        with scum_db_readonly_connection_strict(scum_db_path) as conn_ro:
            cur_ro = conn_ro.cursor()
            current_attrs = scum_get_prisoner_attributes(cur_ro, int(resolved["prisoner_id"]))
            if current_attrs is None:
                current_attrs = {"strength": 3.0, "constitution": 3.0, "dexterity": 3.0, "intelligence": 3.0}

        ssm_db_path, ssm_error = _get_ssm_database_path()
        if not ssm_error:
            cached_attrs = {}
            try:
                with DatabaseConnector.get_connection(ssm_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT strength, constitution, dexterity, intelligence 
                        FROM player_attributes_cache 
                        WHERE steam_id = ?
                        """,
                        (resolved.get("steam_id"),)
                    )
                    row = cursor.fetchone()
                    if row:
                        cached_attrs = {
                            "strength": float(row[0]) if row[0] is not None else 0.0,
                            "constitution": float(row[1]) if row[1] is not None else 0.0,
                            "dexterity": float(row[2]) if row[2] is not None else 0.0,
                            "intelligence": float(row[3]) if row[3] is not None else 0.0,
                        }
            except Exception as e:
                logger.error(f"Erro ao ler cache de atributos no admin PATCH: {e}")

            for attr in ["strength", "constitution", "dexterity", "intelligence"]:
                db_val = current_attrs.get(attr, 3.0)
                cache_val = cached_attrs.get(attr, 0.0)
                current_attrs[attr] = max(db_val, cache_val)

        try:
            with rcon_client as rcon:
                changes = []
                for attr_name, val in new_values.items():
                    old_val = current_attrs.get(attr_name, 3.0)
                    if abs(old_val - val) > 0.01:
                        ok, msg = apply_attribute_and_skills_via_rcon(
                            rcon,
                            resolved.get("steam_id"),
                            attr_name,
                            val,
                            current_attrs
                        )
                        if not ok:
                            return jsonify({"success": False, "error": msg}), 400
                        changes.append(f"{attr_name}: {old_val:.2f} -> {val:.2f}")
                        current_attrs[attr_name] = val

                        # Atualizar cache no SSM.db (inclui prisoner_id para validação de personagem)
                        try:
                            with DatabaseConnector.get_connection(ssm_db_path, write_mode=True) as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    """
                                    INSERT INTO player_attributes_cache (steam_id, strength, constitution, dexterity, intelligence, prisoner_id, updated_at)
                                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                                    ON CONFLICT(steam_id) DO UPDATE SET
                                        strength = excluded.strength,
                                        constitution = excluded.constitution,
                                        dexterity = excluded.dexterity,
                                        intelligence = excluded.intelligence,
                                        prisoner_id = excluded.prisoner_id,
                                        updated_at = CURRENT_TIMESTAMP
                                    """,
                                    (
                                        resolved.get("steam_id"),
                                        current_attrs.get("strength"),
                                        current_attrs.get("constitution"),
                                        current_attrs.get("dexterity"),
                                        current_attrs.get("intelligence"),
                                        resolved.get("prisoner_id")
                                    )
                                )
                                conn.commit()
                        except Exception as e:
                            logger.error(f"Erro ao atualizar cache no admin PATCH success: {e}")

                if not changes:
                    return jsonify(
                        {
                            "success": True,
                            "message": "Nenhuma alteração aplicada (valores já estavam iguais).",
                            "data": {
                                "player": resolved,
                                "attributes": current_attrs,
                                "backup_path": None,
                                "changes": [],
                            },
                        }
                    )

                after = current_attrs
                backup_path = None
                logs = changes
        except Exception as e:
            logger.error(f"Erro ao aplicar atributos via RCON: {e}")
            return jsonify({"success": False, "error": f"Erro RCON: {str(e)}"}), 500

        try:
            logger.info(
                "Atributos atualizados no SCUM.db",
                {
                    "actor": getattr(request, "current_username", None),
                    "identifier": identifier,
                    "prisoner_id": resolved.get("prisoner_id") if resolved else None,
                },
            )
        except Exception:
            pass

        try:
            if discord_webhook:
                actor = getattr(request, "current_username", None)
                actor_role = getattr(request, "current_role", None)

                player_name = resolved.get("name") if isinstance(resolved, dict) else None
                steam_id = resolved.get("steam_id") if isinstance(resolved, dict) else None
                prisoner_id = resolved.get("prisoner_id") if isinstance(resolved, dict) else None

                changes_text = "\n".join(logs[:20]) if logs else "(no changes)"
                fields = [
                    {
                        "name": "Actor",
                        "value": f"{actor} ({actor_role})" if actor_role else f"{actor}",
                        "inline": True,
                    },
                    {
                        "name": "Player",
                        "value": f"{player_name} | steam_id={steam_id} | prisoner_id={prisoner_id}",
                        "inline": False,
                    },
                    {
                        "name": "Changes",
                        "value": changes_text[:1000],
                        "inline": False,
                    },
                    {
                        "name": "Backup",
                        "value": str(backup_path),
                        "inline": False,
                    },
                ]

                discord_webhook.send_webhook(
                    webhook_name="log-ssm",
                    title="[ATTRIBUTES] Player attributes updated",
                    description="SCUM.db attributes were updated via API.",
                    color=0xFFAA00,
                    fields=fields,
                )
        except Exception:
            pass

        return jsonify(
            {
                "success": True,
                "message": "Atributos atualizados com sucesso",
                "data": {
                    "player": resolved,
                    "before": before,
                    "after": after,
                    "changes": logs,
                    "backup_path": backup_path,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao atualizar atributos do player '{identifier}': {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/flags", methods=["GET"])
def get_all_flags():
    """Listar todas as bandeiras do mapa com localizações e owners"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        if not squad_sync_service:
            return (
                jsonify(
                    {"success": False, "error": "SquadSyncService não inicializado"}
                ),
                500,
            )

        result = squad_sync_service.get_all_flags_with_locations()

        if not result.get("success"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result.get("error", "Erro desconhecido"),
                    }
                ),
                500,
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "flags": result.get("flags", []),
                    "total": result.get("total", 0),
                    "with_owner": result.get("with_owner", 0),
                    "no_owner": result.get("no_owner", 0),
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao listar bandeiras: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/flags/owners", methods=["GET"])
@require_auth
@require_admin
def admin_list_flags_owners():
    """Listar bandeiras (flag_id) com owner formatado para facilitar seleção no frontend."""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        if not squad_sync_service:
            return (
                jsonify({"success": False, "error": "SquadSyncService não inicializado"}),
                500,
            )

        only_with_owner_raw = str(request.args.get("only_with_owner", "true") or "true").strip().lower()
        only_with_owner = only_with_owner_raw not in {"0", "false", "no", "off"}

        q = str(request.args.get("q", "") or "").strip().lower()

        try:
            page = int(request.args.get("page", 1))
        except Exception:
            page = 1
        try:
            page_size = int(request.args.get("page_size", 50))
        except Exception:
            page_size = 50

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 1
        if page_size > 500:
            page_size = 500

        result = squad_sync_service.get_all_flags_with_locations()
        if not result.get("success"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result.get("error", "Erro desconhecido"),
                    }
                ),
                500,
            )

        flags = result.get("flags", []) or []

        def _format_owner(owner_name: str | None, owner_steam_id: str | None) -> str:
            name = str(owner_name or "").strip()
            steam = str(owner_steam_id or "").strip()
            if name and steam:
                return f"{name} ({steam})"
            if name:
                return name
            return "no owner"

        simplified = []
        for f in flags:
            flag_id = f.get("element_id")
            owner_name = f.get("owner_name")
            owner_steam_id = f.get("owner_steam_id")
            owner = _format_owner(owner_name, owner_steam_id)

            if only_with_owner and owner == "no owner":
                continue

            if q:
                hay = " ".join(
                    [
                        str(flag_id or ""),
                        str(owner_name or ""),
                        str(owner_steam_id or ""),
                        str(owner),
                    ]
                ).lower()
                if q not in hay:
                    continue

            simplified.append(
                {
                    "flag_id": flag_id,
                    "owner": owner,
                    "owner_name": owner_name,
                    "owner_steam_id": owner_steam_id,
                }
            )

        simplified.sort(key=lambda x: (str(x.get("owner") or ""), int(x.get("flag_id") or 0)))

        total = len(simplified)
        start = (page - 1) * page_size
        end = start + page_size
        items = simplified[start:end]

        return jsonify(
            {
                "success": True,
                "data": {
                    "flags": items,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao listar owners das bandeiras: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/base-material/dry-run", methods=["POST"])
@require_auth
@require_admin
def admin_base_material_dry_run():
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        data = request.get_json(force=True, silent=True) or {}
        flag_id = data.get("flag_id")
        level = data.get("target_level")
        fallback_lowest = data.get("fallback_lowest", True)
        auto_enrich_whitelist = data.get("auto_enrich_whitelist", True)

        try:
            flag_id = int(flag_id)
        except Exception:
            return (
                jsonify({"success": False, "error": "flag_id inválido", "code": "INVALID_FLAG_ID"}),
                400,
            )

        try:
            level = int(level)
        except Exception:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "target_level inválido",
                        "code": "INVALID_TARGET_LEVEL",
                    }
                ),
                400,
            )

        if level < 1 or level > 5:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "target_level deve ser entre 1 e 5",
                        "code": "TARGET_LEVEL_INVALID_RANGE",
                        "details": {"min": 1, "max": 5, "target_level": level},
                    }
                ),
                400,
            )

        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        scum_db_path, error = _get_scum_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        from core.base_material.base_material_job_service import BaseMaterialJobService
        from utils.logger import StructuredLogger

        # Criar logger separado para upgrade de base para facilitar auditoria
        logging_config = {}
        if hasattr(services, 'config') and isinstance(services.config, dict):
            logging_config = services.config.get("logging", {})

        base_material_logger = StructuredLogger(
            config=logging_config,
            name="base_material_upgrade",
            filename="base_material_upgrade.log"
        )

        svc = BaseMaterialJobService(
            ssm_db_path=ssm_db_path,
            scum_db_path=scum_db_path,
            template_db_path="data/templates/scum_base_template.db",
            logger=base_material_logger,
        )

        try:
            res = svc.dry_run(
                flag_id=flag_id,
                target_level=level,
                fallback_lowest=bool(fallback_lowest),
                auto_enrich_whitelist=bool(auto_enrich_whitelist),
            )
        except RuntimeError as e:
            code = str(e)
            if code == "FLAG_NOT_FOUND":
                return jsonify({"success": False, "error": "Flag não encontrada", "code": code}), 404
            if code in {"TARGET_LEVEL_FORBIDDEN"}:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Nível alvo não permitido para esta base",
                            "code": code,
                        }
                    ),
                    400,
                )
            if code in {"SCUM_DB_NOT_FOUND", "TEMPLATE_DB_NOT_FOUND"}:
                return jsonify({"success": False, "error": code, "code": code}), 500
            return jsonify({"success": False, "error": code, "code": "ERROR"}), 500

        return jsonify(
            {
                "success": True,
                "data": {
                    "flag_id": res.flag_id,
                    "internal_base_id": res.internal_base_id,
                    "target_level": res.target_level,
                    "stats": res.stats,
                    "changes_sample": res.changes_sample,
                    "changes_sample_truncated": len(res.changes_sample) >= 200,
                    "debug": getattr(res, "debug", None),
                },
            }
        )
    except Exception as e:
        logger.error(f"Erro no dry-run base-material: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/base-material/schedule", methods=["POST"])
@require_auth
@require_admin
def admin_base_material_schedule():
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        data = request.get_json(force=True, silent=True) or {}
        flag_id = data.get("flag_id")
        level = data.get("target_level")
        fallback_lowest = data.get("fallback_lowest", True)
        run_now_if_offline = bool(data.get("run_now_if_offline", True))

        try:
            flag_id = int(flag_id)
        except Exception:
            return (
                jsonify({"success": False, "error": "flag_id inválido", "code": "INVALID_FLAG_ID"}),
                400,
            )

        try:
            level = int(level)
        except Exception:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "target_level inválido",
                        "code": "INVALID_TARGET_LEVEL",
                    }
                ),
                400,
            )

        if level < 1 or level > 5:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "target_level deve ser entre 1 e 5",
                        "code": "TARGET_LEVEL_INVALID_RANGE",
                        "details": {"min": 1, "max": 5, "target_level": level},
                    }
                ),
                400,
            )

        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        scum_db_path, error = _get_scum_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        from core.base_material.base_material_job_service import BaseMaterialJobService
        from utils.logger import StructuredLogger

        # Criar logger separado para upgrade de base para facilitar auditoria
        logging_config = {}
        if hasattr(services, 'config') and isinstance(services.config, dict):
            logging_config = services.config.get("logging", {})

        base_material_logger = StructuredLogger(
            config=logging_config,
            name="base_material_upgrade",
            filename="base_material_upgrade.log"
        )

        svc = BaseMaterialJobService(
            ssm_db_path=ssm_db_path,
            scum_db_path=scum_db_path,
            template_db_path="data/templates/scum_base_template.db",
            logger=base_material_logger,
        )

        ok, job_or_code, deduplicated = svc.enqueue_dedup(
            flag_id=flag_id, target_level=level, fallback_lowest=bool(fallback_lowest)
        )
        if not ok:
            if job_or_code == "TARGET_LEVEL_FORBIDDEN":
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Nível alvo não permitido para esta base",
                            "code": job_or_code,
                        }
                    ),
                    400,
                )
            return jsonify({"success": False, "error": job_or_code, "code": job_or_code}), 400

        job_id = str(job_or_code)

        executed_now = False
        run_result = None

        if run_now_if_offline:
            offline_ok, offline_msg = _server_must_be_offline_for_scum_db_write()
            if offline_ok:
                try:
                    cycle_id = (
                        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                        + "_manual_"
                        + str(os.getpid())
                    )
                    run_once_res = svc.run_once(restart_cycle_id=cycle_id, limit=10)
                    executed_now = True
                    run_result = {
                        "claimed": run_once_res.claimed,
                        "updated": run_once_res.updated,
                        "no_changes": run_once_res.no_changes,
                        "failed": run_once_res.failed,
                        "job_ids": run_once_res.job_ids,
                    }
                except Exception as e:
                    executed_now = True
                    run_result = {"error": str(e), "code": "RUN_ONCE_FAILED"}

        # Logar no webhook shop-log: job agendado (não dispara restart automaticamente)
        try:
            if discord_webhook:
                fields = [
                    {"name": "JobId", "value": str(job_id), "inline": False},
                    {"name": "FlagId", "value": str(flag_id), "inline": True},
                    {"name": "TargetLevel", "value": str(level), "inline": True},
                    {"name": "FallbackLowest", "value": str(bool(fallback_lowest)), "inline": True},
                    {"name": "ExecutedNow", "value": str(bool(executed_now)), "inline": True},
                ]

                # Se não executou agora, reforçar que ficará pendente até o próximo restart automático
                desc = "Job scheduled. It will run on the next automatic restart (offline window)."
                if executed_now:
                    desc = "Job scheduled and executed now (server offline)."

                discord_webhook.send_webhook(
                    webhook_name="shop-log",
                    title="📌 Base Material Upgrade Scheduled",
                    description=desc,
                    color=0x0099FF,
                    fields=fields,
                )
        except Exception as e:
            logger.warn(f"Falha ao enviar webhook shop-log (base-material schedule): {e}")

        return jsonify(
            {
                "success": True,
                "data": {
                    "job_id": job_id,
                    "scheduled": True,
                    "deduplicated": bool(deduplicated),
                    "executed_now": executed_now,
                    "run_result": run_result,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao agendar base-material: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/base-material/jobs", methods=["GET"])
@require_auth
@require_admin
def admin_base_material_list_jobs():
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        status = str(request.args.get("status", "") or "").strip().lower()
        limit = request.args.get("limit", default=50, type=int)
        offset = request.args.get("offset", default=0, type=int)

        if limit is None or limit < 1:
            limit = 50
        if limit > 200:
            limit = 200
        if offset is None or offset < 0:
            offset = 0

        where = ""
        params: list[Any] = []
        if status:
            where = "WHERE LOWER(status) = ?"
            params.append(status)

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute(
                f"SELECT COUNT(*) as c FROM base_material_job {where}",
                tuple(params),
            )
            total = int((cur.fetchone() or {}).get("c") or 0)

            cur.execute(
                f"""
                SELECT job_id, flag_id, target_level, fallback_lowest, status,
                       attempt_count, next_attempt_at, locked_by, locked_at,
                       error_code, error_message, created_at, updated_at
                FROM base_material_job
                {where}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                tuple(params + [int(limit), int(offset)]),
            )
            rows = cur.fetchall() or []

        jobs = []
        for r in rows:
            jobs.append(
                {
                    "job_id": r["job_id"],
                    "flag_id": r["flag_id"],
                    "target_level": r["target_level"],
                    "fallback_lowest": bool(int(r["fallback_lowest"] or 0)),
                    "status": r["status"],
                    "attempt_count": r["attempt_count"],
                    "next_attempt_at": r["next_attempt_at"],
                    "locked_by": r["locked_by"],
                    "locked_at": r["locked_at"],
                    "error_code": r["error_code"],
                    "error_message": r["error_message"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "jobs": jobs,
                    "total": total,
                    "limit": int(limit),
                    "offset": int(offset),
                },
            }
        )
    except Exception as e:
        logger.error(f"Erro ao listar jobs base-material: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/base-material/jobs/<job_id>", methods=["GET"])
@require_auth
@require_admin
def admin_base_material_get_job(job_id: str):
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    heartbeat_manager = getattr(services, 'heartbeat_manager', None)
    owner_manager = getattr(services, 'owner_manager', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        job_id = str(job_id or "").strip()
        if not job_id:
            return (
                jsonify({"success": False, "error": "job_id inválido", "code": "INVALID_JOB_ID"}),
                400,
            )

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM base_material_job
                WHERE job_id = ?
                LIMIT 1
                """,
                (job_id,),
            )
            row = cur.fetchone()

        if not row:
            return (
                jsonify({"success": False, "error": "job not found", "code": "JOB_NOT_FOUND"}),
                404,
            )

        payload = {
            "job_id": row["job_id"],
            "flag_id": row["flag_id"],
            "target_level": row["target_level"],
            "fallback_lowest": bool(int(row["fallback_lowest"] or 0)),
            "status": row["status"],
            "attempt_count": row["attempt_count"],
            "next_attempt_at": row["next_attempt_at"],
            "locked_by": row["locked_by"],
            "locked_at": row["locked_at"],
            "error_code": row["error_code"],
            "error_message": row["error_message"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

        result_json = row["result_json"]
        if result_json:
            try:
                payload["result"] = json.loads(result_json)
            except Exception:
                payload["result"] = result_json
        else:
            payload["result"] = None

        return jsonify({"success": True, "data": payload})
    except Exception as e:
        logger.error(f"Erro ao obter job base-material: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


