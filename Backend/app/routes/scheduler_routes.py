"""
Blueprint: scheduler
"""
from core.database.connector import DatabaseConnector

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac, copy
from functools import wraps
from core.auth.decorators import require_auth, require_admin, require_player_auth
from utils.scum_db_helper import scum_db_readonly_connection_strict
from utils.integration_helpers import require_integration_key
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone

scheduler_bp = Blueprint('scheduler', __name__)

@scheduler_bp.route("/api/scheduler/test-alert", methods=["POST"])
def test_scheduler_alert():
    """Test sending restart alert to Discord"""
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
        if not restart_scheduler:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "RestartScheduler não inicializado",
                    }
                ),
                500,
            )

        data = request.get_json(silent=True) or {}
        alert_type = data.get("alert_type", "failure")

        result = restart_scheduler.test_restart_alert(alert_type=alert_type)

        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Erro ao testar alerta do scheduler: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/status", methods=["GET"])
def get_scheduler_status():
    """Obter status do agendador"""
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
        logger.info("Requisição de status do agendador")

        if not restart_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "RestartScheduler não inicializado"}
                ),
                500,
            )

        status = restart_scheduler.get_status()

        response = {
            "success": True,
            "data": status.get("data", {}),
            "timestamp": time.time(),
        }

        logger.info(
            f"Status do agendador retornado: {status.get('data', {}).get('is_running', False)}"
        )
        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro ao obter status do agendador: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/start", methods=["POST"])
def start_scheduler():
    """Iniciar agendador"""
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
        logger.info("Iniciando agendador")

        if not restart_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "RestartScheduler não inicializado"}
                ),
                500,
            )

        result = restart_scheduler.start()

        logger.info(f"Resultado do início do agendador: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao iniciar agendador: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/stop", methods=["POST"])
def stop_scheduler():
    """Parar agendador"""
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
        logger.info("Parando agendador")

        if not restart_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "RestartScheduler não inicializado"}
                ),
                500,
            )

        result = restart_scheduler.stop()

        logger.info(f"Resultado da parada do agendador: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao parar agendador: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/restart", methods=["POST"])
def restart_scheduler_endpoint():
    """Reiniciar agendador"""
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
        logger.info("Reiniciando agendador")

        if not restart_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "RestartScheduler não inicializado"}
                ),
                500,
            )

        result = restart_scheduler.restart()

        logger.info(f"Resultado do reinício do agendador: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao reiniciar agendador: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/logs", methods=["GET"])
def get_scheduler_logs():
    """Obter logs do agendador"""
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
        # Obter parâmetros da query
        limit = int(request.args.get("limit", 50))

        logger.info(f"Requisição de logs do agendador (limit: {limit})")

        if not restart_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "RestartScheduler não inicializado"}
                ),
                500,
            )

        logs = restart_scheduler.get_logs(limit)

        response = {
            "success": True,
            "data": logs.get("data", {}),
            "timestamp": time.time(),
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro ao obter logs do agendador: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/config", methods=["GET"])
def get_scheduler_config():
    """Obter configuração do agendador"""
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
        logger.info("Requisição de configuração do agendador")

        if not restart_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "RestartScheduler não inicializado"}
                ),
                500,
            )

        scheduler_config = config.get("scheduler", {})

        response = {"success": True, "data": scheduler_config, "timestamp": time.time()}

        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro ao obter configuração do agendador: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/config", methods=["POST"])
def update_scheduler_config():
    """Atualizar configuração do agendador"""
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
        # Obter dados do body
        data = request.get_json() or {}

        logger.info(f"Atualizando configuração do agendador: {data}")

        if not restart_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "RestartScheduler não inicializado"}
                ),
                500,
            )

        # Validar dados
        if "restart_times" in data:
            restart_times = data["restart_times"]
            if not isinstance(restart_times, list):
                return (
                    jsonify(
                        {"success": False, "error": "restart_times deve ser uma lista"}
                    ),
                    400,
                )

            # Validar formato dos horários
            for time_str in restart_times:
                try:
                    hour, minute = map(int, time_str.split(":"))
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError()
                except ValueError:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": f"Formato de horário inválido: {time_str}. Use HH:MM",
                            }
                        ),
                        400,
                    )

        # Atualizar configuração
        result = restart_scheduler.update_config(data)

        # Atualizar arquivo de configuração
        if result.get("success"):
            config["scheduler"].update(data)
            try:
                config_to_save = copy.deepcopy(config)
                config_to_save.pop("webhooks", None)
                server_cfg = config_to_save.get("server")
                if isinstance(server_cfg, dict):
                    server_cfg.pop("webhooks", None)
                fishing_cfg = config_to_save.get("fishing_ranking")
                if isinstance(fishing_cfg, dict):
                    fishing_cfg.pop("scum_db_path", None)
                    fishing_cfg.pop("webhook_url", None)
                with open("data/config.json", "w", encoding="utf-8") as f:
                    json.dump(config_to_save, f, indent=2, ensure_ascii=False)
                logger.info("Arquivo de configuração atualizado")
            except Exception as e:
                logger.error(f"Erro ao salvar configuração: {e}")

        logger.info(f"Resultado da atualização: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao atualizar configuração do agendador: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/force-restart", methods=["POST"])
def force_restart_now():
    """Forçar reinicialização imediatamente"""
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
        logger.info("Reinicialização forçada solicitada")

        if not restart_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "RestartScheduler não inicializado"}
                ),
                500,
            )

        result = restart_scheduler.force_restart_now()

        logger.info(f"Resultado da reinicialização forçada: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro na reinicialização forçada: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/weather/status", methods=["GET"])
def get_weather_scheduler_status():
    """Obter status do agendador climático"""
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
        logger.info("Requisição de status do agendador climático")

        if not weather_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "WeatherScheduler não inicializado"}
                ),
                500,
            )

        status = weather_scheduler.get_status()

        response = {
            "success": True,
            "data": status.get("data", {}),
            "timestamp": time.time(),
        }

        logger.info(
            f"Status do agendador climático retornado: {status.get('data', {}).get('is_running', False)}"
        )
        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro ao obter status do agendador climático: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/weather/start", methods=["POST"])
def start_weather_scheduler():
    """Iniciar agendador climático"""
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
        logger.info("Iniciando agendador climático")

        if not weather_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "WeatherScheduler não inicializado"}
                ),
                500,
            )

        result = weather_scheduler.start()

        logger.info(f"Resultado do início do agendador climático: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao iniciar agendador climático: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/weather/stop", methods=["POST"])
def stop_weather_scheduler():
    """Parar agendador climático"""
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
        logger.info("Parando agendador climático")

        if not weather_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "WeatherScheduler não inicializado"}
                ),
                500,
            )

        result = weather_scheduler.stop()

        logger.info(f"Resultado da parada do agendador climático: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao parar agendador climático: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/weather/sync", methods=["POST"])
def force_weather_sync():
    """Forçar sincronização climática imediata"""
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
        logger.info("Sincronização climática forçada solicitada")

        if not weather_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "WeatherScheduler não inicializado"}
                ),
                500,
            )

        result = weather_scheduler.force_sync_now()

        logger.info(f"Resultado da sincronização forçada: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro na sincronização forçada: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/weather/logs", methods=["GET"])
def get_weather_scheduler_logs():
    """Obter logs do agendador climático"""
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
        # Obter parâmetros da query
        limit = int(request.args.get("limit", 50))

        logger.info(f"Requisição de logs do agendador climático (limit: {limit})")

        if not weather_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "WeatherScheduler não inicializado"}
                ),
                500,
            )

        logs = weather_scheduler.get_logs(limit)

        response = {
            "success": True,
            "data": logs.get("data", {}),
            "timestamp": time.time(),
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro ao obter logs do agendador climático: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/weather/time", methods=["GET"])
def get_server_time():
    """Obter hora atual do servidor SCUM e dados climáticos completos"""
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
        logger.info("Requisição de dados climáticos completos")

        if not weather_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "WeatherScheduler não inicializado"}
                ),
                500,
            )

        # Obter dados climáticos do SSM.db (onde estão os dados sincronizados completos)
        ssm_db_path = path_helper.get_ssm_db_path()

        if not os.path.exists(ssm_db_path):
            return (
                jsonify({"success": False, "error": "Banco SSM.db não encontrado"}),
                404,
            )

        try:
            import sqlite3

            with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cursor = conn.cursor()

                # Buscar todos os dados climáticos da tabela weather_parameters
                cursor.execute(
                    """
                    SELECT map_id, user_profile_id, time_of_day, moon_rotation, 
                           base_air_temperature, water_temperature, 
                           should_cumulonimbus_cause_fog, fog_density, sync_timestamp
                    FROM weather_parameters
                    ORDER BY sync_timestamp DESC
                    LIMIT 1
                """
                )

                weather_data = cursor.fetchone()

                if not weather_data:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Nenhum dado climático encontrado",
                            }
                        ),
                        404,
                    )

                # Extrair dados
                map_id = weather_data[0]
                user_profile_id = weather_data[1]
                time_of_day = weather_data[2]
                moon_rotation = weather_data[3]
                base_air_temp = weather_data[4]
                water_temp = weather_data[5]
                cumulonimbus_fog = weather_data[6]
                fog_density = weather_data[7]
                sync_timestamp = weather_data[8]

                # Converter time_of_day para formato legível
                hours = int(time_of_day)
                minutes = int((time_of_day - hours) * 60)
                server_time = f"{hours:02d}:{minutes:02d}"

                # Calcular próxima sincronização
                sync_interval = weather_scheduler.sync_interval_minutes
                next_sync = datetime.now() + timedelta(minutes=sync_interval)

                # Montar resposta completa
                response = {
                    "success": True,
                    "data": {
                        "server_time": server_time,
                        "time_of_day": time_of_day,
                        "air_temperature": round(base_air_temp, 1),
                        "water_temperature": round(water_temp, 1),
                        "moon_rotation": round(moon_rotation, 2),
                        "fog_density": fog_density,
                        "cumulonimbus_causes_fog": bool(cumulonimbus_fog),
                        "map_id": map_id,
                        "user_profile_id": user_profile_id if user_profile_id else None,
                        "last_sync": sync_timestamp,
                        "next_sync": next_sync.strftime("%Y-%m-%d %H:%M:%S"),
                        "sync_interval_minutes": sync_interval,
                        "is_running": weather_scheduler.is_running,
                    },
                    "timestamp": time.time(),
                }

                logger.info(
                    f"Dados climáticos retornados - Hora: {server_time}, Temp: {base_air_temp:.1f}°C"
                )
                return jsonify(response)

        except Exception as e:
            logger.error(f"Erro ao acessar banco SSM.db: {e}")
            return (
                jsonify(
                    {"success": False, "error": f"Erro ao acessar banco SSM.db: {e}"}
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Erro ao obter dados climáticos: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/time-precision/config", methods=["GET"])
def get_time_precision_config():
    """Obter configuração de precisão de horário"""
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
        logger.info("Requisição de configuração de precisão de horário")

        # Carregar configuração do config.json
        config_path = "data/config.json"
        if not os.path.exists(config_path):
            return (
                jsonify(
                    {"success": False, "error": "Arquivo config.json não encontrado"}
                ),
                404,
            )

        import json

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        time_precision = config.get("time_precision", {})

        response = {
            "success": True,
            "data": {
                "enabled": time_precision.get("enabled", False),
                "offset_minutes": time_precision.get("offset_minutes", 0),
                "description": time_precision.get(
                    "description", "Configuração de precisão de horário"
                ),
            },
            "timestamp": time.time(),
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro ao obter configuração de precisão: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/time-precision/test", methods=["POST"])
def test_time_precision():
    """Testar precisão de horário com offset configurado"""
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
        logger.info("Teste de precisão de horário")

        # Obter horário atual do servidor
        if not weather_scheduler:
            return (
                jsonify(
                    {"success": False, "error": "WeatherScheduler não inicializado"}
                ),
                500,
            )

        # Buscar horário do servidor no banco SCUM
        scum_db_path = "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"

        if not os.path.exists(scum_db_path):
            return (
                jsonify({"success": False, "error": "Banco SCUM.db não encontrado"}),
                404,
            )

        try:
            from utils.scum_db_helper import scum_db_readonly_connection

            with scum_db_readonly_connection(scum_db_path) as conn:
                cursor = conn.cursor()

                # Buscar dados da tabela weather_parameters
                cursor.execute(
                    """
                    SELECT time_of_day
                    FROM weather_parameters
                    ORDER BY map_id DESC
                    LIMIT 1
                """
                )

                weather_data = cursor.fetchone()

                if not weather_data:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Nenhum dado climático encontrado",
                            }
                        ),
                        404,
                    )

                # Converter time_of_day para formato legível
                time_of_day = weather_data[0]
                hours = int(time_of_day)
                minutes = int((time_of_day - hours) * 60)
                base_time = f"{hours:02d}:{minutes:02d}"

        except Exception as e:
            logger.error(f"Erro ao acessar banco SCUM: {e}")
            return (
                jsonify(
                    {"success": False, "error": f"Erro ao acessar banco SCUM: {e}"}
                ),
                500,
            )

        # Carregar configuração de precisão
        config_path = "data/config.json"
        import json

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        time_precision = config.get("time_precision", {})
        offset_minutes = time_precision.get("offset_minutes", 0)
        enabled = time_precision.get("enabled", False)

        # Aplicar offset se habilitado
        adjusted_time = base_time
        if enabled and offset_minutes > 0:

            time_parts = base_time.split(":")
            hours = int(time_parts[0])
            minutes = int(time_parts[1])

            base_datetime = datetime.now().replace(
                hour=hours, minute=minutes, second=0, microsecond=0
            )
            adjusted_datetime = base_datetime + timedelta(minutes=offset_minutes)
            adjusted_time = (
                f"{adjusted_datetime.hour:02d}:{adjusted_datetime.minute:02d}"
            )

        response = {
            "success": True,
            "data": {
                "base_time": base_time,
                "adjusted_time": adjusted_time,
                "offset_minutes": offset_minutes,
                "enabled": enabled,
                "time_of_day": time_of_day,
                "difference_minutes": offset_minutes if enabled else 0,
            },
            "timestamp": time.time(),
        }

        logger.info(
            f"Teste de precisão: {base_time} -> {adjusted_time} (offset: {offset_minutes}min)"
        )
        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro ao testar precisão de horário: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# ENDPOINTS DO AGENDADOR DE CONFIGURAÇÃO (Hot-Swap ServerSettings.ini)
# ============================================================================

@scheduler_bp.route("/api/scheduler/settings/config", methods=["GET"])
@require_auth
@require_admin
def get_settings_scheduler_config():
    """Obter status/configuração global do agendador de configurações"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    scheduler = getattr(services, 'settings_routine_scheduler', None)
    
    if not scheduler:
        return jsonify({"success": False, "error": "Agendador de configurações não inicializado"}), 500

    try:
        return jsonify({
            "success": True,
            "enabled": scheduler.is_enabled(),
            "active_routine_id": scheduler.active_routine_id,
            "timestamp": time.time()
        })
    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter configuração do agendador de configurações: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/settings/config", methods=["POST"])
@require_auth
@require_admin
def update_settings_scheduler_config():
    """Habilitar ou desabilitar o agendador de configurações globalmente"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    scheduler = getattr(services, 'settings_routine_scheduler', None)

    if not scheduler:
        return jsonify({"success": False, "error": "Agendador de configurações não inicializado"}), 500

    try:
        data = request.get_json() or {}
        enabled = data.get("enabled")
        
        if enabled is None:
            return jsonify({"success": False, "error": "O campo 'enabled' é obrigatório"}), 400

        scheduler.set_enabled(bool(enabled))
        return jsonify({
            "success": True,
            "enabled": scheduler.is_enabled(),
            "active_routine_id": scheduler.active_routine_id
        })
    except Exception as e:
        if logger:
            logger.error(f"Erro ao atualizar configuração do agendador de configurações: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/settings/presets", methods=["GET"])
@require_auth
@require_admin
def get_settings_presets():
    """Obter lista de presets (.ini) cadastrados"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    scheduler = getattr(services, 'settings_routine_scheduler', None)

    if not scheduler:
        return jsonify({"success": False, "error": "Agendador de configurações não inicializado"}), 500

    try:
        presets = scheduler.get_presets()
        return jsonify({
            "success": True,
            "presets": presets
        })
    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter presets: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/settings/presets/upload", methods=["POST"])
@require_auth
@require_admin
def upload_settings_preset():
    """Fazer upload de um arquivo de configuração (.ini)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    scheduler = getattr(services, 'settings_routine_scheduler', None)

    if not scheduler:
        return jsonify({"success": False, "error": "Agendador de configurações não inicializado"}), 500

    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "Nenhum arquivo enviado"}), 400

        uploaded_file = request.files["file"]
        filename = secure_filename(uploaded_file.filename or "preset.ini")
        
        if not filename.lower().endswith(".ini"):
            return jsonify({"success": False, "error": "O arquivo deve ter extensão .ini"}), 400

        # Nome opcional enviado via form data para renomear
        custom_name = request.form.get("name")
        if custom_name:
            custom_name = custom_name.strip()
            if not custom_name.lower().endswith(".ini"):
                custom_name += ".ini"
            filename = secure_filename(custom_name)

        # Ler conteúdo e salvar via scheduler
        file_content = uploaded_file.read()
        if not file_content:
            return jsonify({"success": False, "error": "O arquivo enviado está vazio"}), 400

        result = scheduler.upload_preset(file_content, filename)
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        if logger:
            logger.error(f"Erro ao enviar preset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/settings/presets/<name>", methods=["DELETE"])
@require_auth
@require_admin
def delete_settings_preset(name):
    """Excluir um preset de configuração específico"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    scheduler = getattr(services, 'settings_routine_scheduler', None)

    if not scheduler:
        return jsonify({"success": False, "error": "Agendador de configurações não inicializado"}), 500

    try:
        # Verificar se alguma rotina está usando este preset antes de permitir exclusão
        routines = scheduler.load_routines()
        for r in routines:
            if r.get("preset_file") == name:
                return jsonify({
                    "success": False, 
                    "error": f"Este preset não pode ser excluído pois está em uso pela rotina '{r.get('name')}'"
                }), 400

        result = scheduler.delete_preset(name)
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        if logger:
            logger.error(f"Erro ao excluir preset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/settings/presets/clone-current", methods=["POST"])
@require_auth
@require_admin
def clone_current_settings():
    """Clonar o ServerSettings.ini atual do SCUM como um novo preset"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    scheduler = getattr(services, 'settings_routine_scheduler', None)

    if not scheduler:
        return jsonify({"success": False, "error": "Agendador de configurações não inicializado"}), 500

    try:
        data = request.get_json() or {}
        name = data.get("name")
        if not name:
            return jsonify({"success": False, "error": "O nome do preset é obrigatório"}), 400

        result = scheduler.clone_current_as_preset(name)
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        if logger:
            logger.error(f"Erro ao clonar ServerSettings.ini atual: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/settings/routines", methods=["GET"])
@require_auth
@require_admin
def get_settings_routines():
    """Listar todas as rotinas agendadas"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    scheduler = getattr(services, 'settings_routine_scheduler', None)

    if not scheduler:
        return jsonify({"success": False, "error": "Agendador de configurações não inicializado"}), 500

    try:
        routines = scheduler.load_routines()
        return jsonify({
            "success": True,
            "routines": routines
        })
    except Exception as e:
        if logger:
            logger.error(f"Erro ao carregar rotinas de configuração: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/settings/routines", methods=["POST"])
@require_auth
@require_admin
def update_settings_routines():
    """Salvar, atualizar ou substituir rotinas agendadas"""
    import uuid
    services = get_services()
    logger = getattr(services, 'logger', None)
    scheduler = getattr(services, 'settings_routine_scheduler', None)

    if not scheduler:
        return jsonify({"success": False, "error": "Agendador de configurações não inicializado"}), 500

    try:
        data = request.get_json() or {}
        
        # Caso 1: Substituição da lista inteira
        if "routines" in data:
            new_routines = data["routines"]
            if not isinstance(new_routines, list):
                return jsonify({"success": False, "error": "O campo 'routines' deve ser uma lista"}), 400
                
            # Validar e processar cada rotina
            processed_routines = []
            for r in new_routines:
                if not isinstance(r, dict):
                    continue
                
                # Garantir ID
                r_id = r.get("id") or str(uuid.uuid4())
                name = r.get("name", "").strip() or "Nova Rotina"
                enabled = bool(r.get("enabled", True))
                
                # Validar dias da semana
                days = r.get("days_of_week", [])
                if not isinstance(days, list) or not all(isinstance(d, int) and 0 <= d <= 6 for d in days):
                    return jsonify({"success": False, "error": f"Lista de dias da semana inválida na rotina: {name}"}), 400
                
                # Validar horários
                start_time = r.get("start_time", "")
                end_time = r.get("end_time", "")
                try:
                    for t_str in (start_time, end_time):
                        hour, minute = map(int, t_str.split(":"))
                        if not (0 <= hour <= 23 and 0 <= minute <= 59):
                            raise ValueError()
                except (ValueError, AttributeError):
                    return jsonify({"success": False, "error": f"Formato de horário inválido (use HH:MM) na rotina: {name}"}), 400
                
                # Validar preset_file
                preset_file = r.get("preset_file", "")
                if not preset_file:
                    return jsonify({"success": False, "error": f"preset_file é obrigatório na rotina: {name}"}), 400
                
                processed_routines.append({
                    "id": r_id,
                    "name": name,
                    "enabled": enabled,
                    "days_of_week": days,
                    "start_time": start_time,
                    "end_time": end_time,
                    "preset_file": preset_file
                })
            
            scheduler.save_routines(processed_routines)
            scheduler.reconcile() # Forçar verificação após salvar
            return jsonify({"success": True, "routines": processed_routines})

        # Caso 2: Adição/Edição de uma única rotina
        else:
            name = data.get("name", "").strip() or "Nova Rotina"
            enabled = bool(data.get("enabled", True))
            
            days = data.get("days_of_week", [])
            if not isinstance(days, list) or not all(isinstance(d, int) and 0 <= d <= 6 for d in days):
                return jsonify({"success": False, "error": "Lista de dias da semana inválida"}), 400
            
            start_time = data.get("start_time", "")
            end_time = data.get("end_time", "")
            try:
                for t_str in (start_time, end_time):
                    hour, minute = map(int, t_str.split(":"))
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError()
            except (ValueError, AttributeError):
                return jsonify({"success": False, "error": "Formato de horário inválido. Use HH:MM"}), 400
            
            preset_file = data.get("preset_file", "")
            if not preset_file:
                return jsonify({"success": False, "error": "preset_file é obrigatório"}), 400

            routines = scheduler.load_routines()
            routine_id = data.get("id")
            
            if routine_id:
                # Editar existente
                found = False
                for r in routines:
                    if r["id"] == routine_id:
                        r.update({
                            "name": name,
                            "enabled": enabled,
                            "days_of_week": days,
                            "start_time": start_time,
                            "end_time": end_time,
                            "preset_file": preset_file
                        })
                        found = True
                        break
                if not found:
                    return jsonify({"success": False, "error": "Rotina não encontrada para edição"}), 404
            else:
                # Criar nova
                routine_id = str(uuid.uuid4())
                routines.append({
                    "id": routine_id,
                    "name": name,
                    "enabled": enabled,
                    "days_of_week": days,
                    "start_time": start_time,
                    "end_time": end_time,
                    "preset_file": preset_file
                })
            
            scheduler.save_routines(routines)
            scheduler.reconcile() # Forçar verificação após salvar
            return jsonify({"success": True, "routines": routines})

    except Exception as e:
        if logger:
            logger.error(f"Erro ao salvar rotina de configuração: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/settings/routines/<routine_id>", methods=["DELETE"])
@require_auth
@require_admin
def delete_settings_routine(routine_id):
    """Excluir uma rotina agendada específica"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    scheduler = getattr(services, 'settings_routine_scheduler', None)

    if not scheduler:
        return jsonify({"success": False, "error": "Agendador de configurações não inicializado"}), 500

    try:
        routines = scheduler.load_routines()
        initial_count = len(routines)
        routines = [r for r in routines if r["id"] != routine_id]
        
        if len(routines) == initial_count:
            return jsonify({"success": False, "error": "Rotina não encontrada"}), 404
            
        scheduler.save_routines(routines)
        scheduler.reconcile() # Reconciliar imediatamente
        
        return jsonify({
            "success": True,
            "routines": routines
        })
    except Exception as e:
        if logger:
            logger.error(f"Erro ao excluir rotina: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route("/api/scheduler/settings/routines/save", methods=["POST"])
@require_auth
@require_admin
def save_settings_routine_unified():
    """
    Endpoint unificado: cria ou edita uma rotina enviando dados + arquivo .ini
    em uma única requisição multipart/form-data.
    
    Campos do formulário (form fields):
      - id           (opcional): Se presente, edita a rotina existente. Se ausente, cria nova.
      - name         (obrigatório): Nome do evento/rotina (usado também como nome do preset).
      - enabled      (opcional): "true" ou "false". Default: "true".
      - days_of_week (obrigatório): Lista de inteiros em JSON. Ex: "[1,4]"
      - start_time   (obrigatório): Horário inicial no formato HH:MM.
      - end_time     (obrigatório): Horário final no formato HH:MM.
    
    Campos de arquivo:
      - file         (obrigatório na criação, opcional na edição): Arquivo .ini do preset.
    """
    import uuid
    services = get_services()
    logger = getattr(services, 'logger', None)
    scheduler = getattr(services, 'settings_routine_scheduler', None)

    if not scheduler:
        return jsonify({"success": False, "error": "Agendador de configurações não inicializado"}), 500

    try:
        # --- Ler dados do formulário ---
        routine_id = request.form.get("id", "").strip() or None
        name = request.form.get("name", "").strip()
        enabled_str = request.form.get("enabled", "true").strip().lower()
        days_str = request.form.get("days_of_week", "[]").strip()
        start_time = request.form.get("start_time", "").strip()
        end_time = request.form.get("end_time", "").strip()

        # --- Validações ---
        if not name:
            return jsonify({"success": False, "error": "O nome da rotina/evento é obrigatório"}), 400

        enabled = enabled_str in ("true", "1", "yes")

        # Validar dias da semana (vem como JSON string)
        try:
            days = json.loads(days_str)
            if not isinstance(days, list) or not all(isinstance(d, int) and 0 <= d <= 6 for d in days):
                raise ValueError()
        except (json.JSONDecodeError, ValueError):
            return jsonify({"success": False, "error": "Lista de dias da semana inválida. Envie como JSON, ex: [0,1,4]"}), 400

        if not days:
            return jsonify({"success": False, "error": "Selecione pelo menos um dia da semana"}), 400

        # Validar horários
        try:
            for t_str in (start_time, end_time):
                hour, minute = map(int, t_str.split(":"))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError()
        except (ValueError, AttributeError):
            return jsonify({"success": False, "error": "Formato de horário inválido. Use HH:MM"}), 400

        # --- Gerar nome do arquivo preset a partir do nome do evento ---
        # Sanitizar: remover caracteres inválidos, substituir espaços por underscore
        safe_name = name.replace(" ", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in (".", "-", "_"))
        if not safe_name:
            return jsonify({"success": False, "error": "Nome do evento resultou em nome de arquivo inválido"}), 400
        preset_filename = f"{safe_name}.ini"

        # --- Processar arquivo .ini ---
        uploaded_file = request.files.get("file")

        if routine_id:
            # EDIÇÃO: arquivo é opcional (pode querer só mudar horário/dias)
            if uploaded_file and uploaded_file.filename:
                file_content = uploaded_file.read()
                if not file_content:
                    return jsonify({"success": False, "error": "O arquivo enviado está vazio"}), 400
                
                result = scheduler.upload_preset(file_content, preset_filename)
                if not result.get("success"):
                    return jsonify(result), 400
                # Atualizar preset_filename com o nome sanitizado retornado
                preset_filename = result.get("name", preset_filename)
            else:
                # Manter o preset existente da rotina ou usar o nome gerado
                routines = scheduler.load_routines()
                existing = next((r for r in routines if r["id"] == routine_id), None)
                if existing:
                    # Se o nome do evento mudou, renomear o preset antigo
                    old_preset = existing.get("preset_file", "")
                    if old_preset and old_preset != preset_filename and old_preset != "default.ini":
                        old_path = scheduler.presets_dir / old_preset
                        new_path = scheduler.presets_dir / preset_filename
                        if old_path.exists() and not new_path.exists():
                            try:
                                old_path.rename(new_path)
                                if logger:
                                    logger.info(f"Preset renomeado: {old_preset} -> {preset_filename}")
                            except Exception as e:
                                if logger:
                                    logger.warning(f"Não foi possível renomear preset: {e}")
                                preset_filename = old_preset  # Manter o nome antigo
                        elif new_path.exists():
                            pass  # Já existe com o novo nome, OK
                        else:
                            preset_filename = old_preset  # Manter se não encontrou
                    elif old_preset:
                        preset_filename = old_preset
        else:
            # CRIAÇÃO: arquivo é obrigatório
            if not uploaded_file or not uploaded_file.filename:
                return jsonify({"success": False, "error": "O arquivo .ini é obrigatório na criação de uma nova rotina"}), 400

            file_content = uploaded_file.read()
            if not file_content:
                return jsonify({"success": False, "error": "O arquivo enviado está vazio"}), 400

            result = scheduler.upload_preset(file_content, preset_filename)
            if not result.get("success"):
                return jsonify(result), 400
            preset_filename = result.get("name", preset_filename)

        # --- Salvar rotina ---
        routines = scheduler.load_routines()

        if routine_id:
            # Editar existente
            found = False
            for r in routines:
                if r["id"] == routine_id:
                    r.update({
                        "name": name,
                        "enabled": enabled,
                        "days_of_week": days,
                        "start_time": start_time,
                        "end_time": end_time,
                        "preset_file": preset_filename
                    })
                    found = True
                    break
            if not found:
                return jsonify({"success": False, "error": "Rotina não encontrada para edição"}), 404
        else:
            # Criar nova
            routine_id = str(uuid.uuid4())
            routines.append({
                "id": routine_id,
                "name": name,
                "enabled": enabled,
                "days_of_week": days,
                "start_time": start_time,
                "end_time": end_time,
                "preset_file": preset_filename
            })

        scheduler.save_routines(routines)
        scheduler.reconcile()

        return jsonify({"success": True, "routines": routines})

    except Exception as e:
        if logger:
            logger.error(f"Erro ao salvar rotina unificada: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
