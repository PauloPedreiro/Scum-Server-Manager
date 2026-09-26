"""
Blueprint: elevated_users
"""
from typing import Dict, Any, List, Optional, Tuple

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac
from functools import wraps
from core.auth.decorators import require_auth, require_admin, require_player_auth
from utils.scum_db_helper import scum_db_readonly_connection_strict
from utils.integration_helpers import require_integration_key
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone

elevated_users_bp = Blueprint('elevated_users', __name__)

@elevated_users_bp.route("/api/elevated-users/status", methods=["GET"])
def get_elevated_users_status():
    """Obter status do sistema de elevated users"""
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
    try:
        if not elevated_users_manager:
            return (
                jsonify(
                    {"success": False, "error": "ElevatedUsersManager não inicializado"}
                ),
                500,
            )

        status = elevated_users_manager.get_status()
        return jsonify(
            {"success": True, "data": status, "timestamp": datetime.now().isoformat()}
        )
    except Exception as e:
        logger.error(f"Erro ao obter status de elevated users: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@elevated_users_bp.route("/api/elevated-users/list", methods=["GET"])
def list_elevated_users():
    """Listar todos os elevated users"""
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
    try:
        if not elevated_users_manager:
            return (
                jsonify(
                    {"success": False, "error": "ElevatedUsersManager não inicializado"}
                ),
                500,
            )

        elevated_users = elevated_users_manager.list_elevated_users()
        return jsonify(
            {
                "success": True,
                "data": {
                    "elevated_users": elevated_users,
                    "total": len(elevated_users),
                },
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Erro ao listar elevated users: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@elevated_users_bp.route("/api/elevated-users/sync", methods=["POST"])
def sync_elevated_users():
    """Forçar sincronização de elevated users"""
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
    try:
        if not elevated_users_manager:
            return (
                jsonify(
                    {"success": False, "error": "ElevatedUsersManager não inicializado"}
                ),
                500,
            )

        result = elevated_users_manager.sync_pending_changes(force=True)

        if result.get("success"):
            return jsonify(
                {
                    "success": True,
                    "data": result,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result.get("error", "Erro desconhecido"),
                    }
                ),
                400,
            )

    except Exception as e:
        logger.error(f"Erro ao sincronizar elevated users: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


