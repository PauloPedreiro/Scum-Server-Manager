"""
Blueprint: notifications
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
import sqlite3
from .helpers import _get_ssm_database_path, _get_scum_database_path

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route("/api/notifications/status", methods=["GET"])
def get_notifications_status():
    """Obter status do sistema de notificações"""
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
        logger.info("Requisição de status das notificações")

        if not notification_manager:
            return (
                jsonify(
                    {"success": False, "error": "NotificationManager não inicializado"}
                ),
                500,
            )

        status = notification_manager.get_status()

        response = {"success": True, "data": status, "timestamp": time.time()}

        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro ao obter status das notificações: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/send", methods=["POST"])
def send_custom_notification():
    """Enviar notificação personalizada"""
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

        message = data.get("message", "")
        duration = data.get("duration", 15)
        color = data.get("color", "255-255-255")

        if not message:
            return jsonify({"success": False, "error": "Mensagem é obrigatória"}), 400

        logger.info(f"Enviando notificação personalizada: {message}")

        if not notification_manager:
            return (
                jsonify(
                    {"success": False, "error": "NotificationManager não inicializado"}
                ),
                500,
            )

        # Usar o método que replica exatamente o comportamento do projeto original
        logger.info(
            f"Chamando send_custom_notification com: message={message[:50]}, duration={duration}, color={color}"
        )
        result = notification_manager.send_custom_notification(
            message=message, duration=duration, color=color
        )

        logger.info(f"Resultado completo: {result}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao enviar notificação personalizada: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/clear", methods=["POST"])
def clear_notifications():
    """Limpar todas as notificações"""
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
        logger.info("Limpando notificações")

        if not notification_manager:
            return (
                jsonify(
                    {"success": False, "error": "NotificationManager não inicializado"}
                ),
                500,
            )

        result = notification_manager.clear_restart_notifications()

        logger.info(f"Resultado da limpeza: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao limpar notificações: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/cooldowns/reset", methods=["POST"])
def reset_cooldowns():
    """Resetar cooldowns de notificações"""
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
        logger.info("Resetando cooldowns de notificações")

        if not notification_manager:
            return (
                jsonify(
                    {"success": False, "error": "NotificationManager não inicializado"}
                ),
                500,
            )

        # Resetar cooldowns
        notification_manager.cooldowns["last_sent"] = {
            "restart": None,
            "custom": None,
            "events": None,
        }
        notification_manager._save_cooldowns(notification_manager.cooldowns)

        logger.info("Cooldowns resetados com sucesso")
        return jsonify(
            {
                "success": True,
                "message": "Cooldowns resetados com sucesso",
                "cooldowns": notification_manager.cooldowns,
            }
        )

    except Exception as e:
        logger.error(f"Erro ao resetar cooldowns: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/restart/create", methods=["POST"])
def create_restart_notifications():
    """Criar notificações de restart"""
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

        restart_time = data.get("restart_time", "")
        restart_date = data.get("restart_date", "")

        if not restart_time:
            return (
                jsonify(
                    {"success": False, "error": "Horário de restart é obrigatório"}
                ),
                400,
            )

        logger.info(f"Criando notificações de restart para {restart_time}")

        if not notification_manager:
            return (
                jsonify(
                    {"success": False, "error": "NotificationManager não inicializado"}
                ),
                500,
            )

        # Criar datetime do restart
        try:

            if restart_date:
                restart_datetime = datetime.strptime(
                    f"{restart_date} {restart_time}", "%Y-%m-%d %H:%M"
                )
            else:
                # Usar data de hoje
                today = datetime.now().strftime("%Y-%m-%d")
                restart_datetime = datetime.strptime(
                    f"{today} {restart_time}", "%Y-%m-%d %H:%M"
                )
        except ValueError as e:
            return (
                jsonify(
                    {"success": False, "error": f"Formato de data/hora inválido: {e}"}
                ),
                400,
            )

        result = notification_manager.create_restart_notifications(
            restart_time, restart_datetime
        )

        logger.info(f"Resultado da criação: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao criar notificações de restart: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/restart/create-next", methods=["POST"])
def create_next_restart_notifications():
    """Criar notificações de restart apenas para o próximo horário"""
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
        logger.info("Criando notificações de restart para o próximo horário")

        if not notification_manager:
            return (
                jsonify(
                    {"success": False, "error": "NotificationManager não inicializado"}
                ),
                500,
            )

        # Usar o novo método que cria apenas notificações de restart
        result = notification_manager.create_correct_notifications()

        logger.info(f"Resultado da criação: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao criar notificações de restart: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/verify", methods=["POST"])
def verify_notifications():
    """Forçar verificação manual do sistema de notificações"""
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
        logger.info("Executando verificação manual do sistema de notificações")

        if not notification_manager:
            return (
                jsonify(
                    {"success": False, "error": "NotificationManager não inicializado"}
                ),
                500,
            )

        # Executar verificação periódica
        notification_manager.periodic_verification()

        return jsonify(
            {
                "success": True,
                "message": "Verificação executada com sucesso",
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.error(f"Erro na verificação manual: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/restart/create-all", methods=["POST"])
def create_all_restart_notifications():
    """Criar notificações de restart para todos os horários do scheduler"""
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
        logger.info(
            "Criando notificações de restart para todos os horários do scheduler"
        )

        if not notification_manager or not restart_scheduler:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "NotificationManager ou RestartScheduler não inicializados",
                    }
                ),
                500,
            )

        # Obter horários do scheduler
        restart_times = restart_scheduler.restart_times
        notification_minutes = restart_scheduler.notification_minutes

        logger.info(f"Horários configurados: {restart_times}")
        logger.info(f"Minutos de notificação: {notification_minutes}")

        results = []
        total_notifications = 0

        # Criar todas as notificações de uma vez para todos os horários
        try:
            import json

            # Carregar template de restart
            template_path = "data/notifications/templates/restart.json"
            with open(template_path, "r", encoding="utf-8") as f:
                template = json.load(f)

            all_notifications = []

            # Para cada horário do scheduler
            for restart_time_str in restart_times:
                # Usar data de hoje para o horário
                today = datetime.now().strftime("%Y-%m-%d")
                restart_datetime = datetime.strptime(
                    f"{today} {restart_time_str}", "%Y-%m-%d %H:%M"
                )

                # Para cada notificação do template
                for notification_template in template.get("notifications", []):
                    # Calcular horário da notificação
                    minutes_before = int(notification_template["time"].split("_")[0])
                    notification_time = restart_datetime - timedelta(
                        minutes=minutes_before
                    )

                    # Criar notificação
                    notification = {
                        "day": "Everyday",
                        "time": [notification_time.strftime("%H:%M")],
                        "duration": notification_template["duration"],
                        "color": notification_template["color"],
                        "message": notification_template["message"],
                    }
                    all_notifications.append(notification)

                    results.append(
                        {
                            "restart_time": restart_time_str,
                            "notification_time": notification_time.strftime("%H:%M"),
                            "minutes_before": minutes_before,
                            "success": True,
                        }
                    )

            # Salvar todas as notificações no arquivo SCUM
            scum_notifications = {"Notifications": all_notifications}

            # Salvar no arquivo Notifications.json do SCUM
            scum_path = "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\Notifications.json"
            with open(scum_path, "w", encoding="utf-8") as f:
                json.dump(scum_notifications, f, indent=2, ensure_ascii=False)

            total_notifications = len(all_notifications)
            successful_results = [r for r in results if r.get("success")]

            logger.info(
                f"Todas as notificações criadas: {total_notifications} notificações para {len(restart_times)} horários"
            )

        except Exception as e:
            logger.error(f"Erro ao criar todas as notificações: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

        # Verificar se pelo menos uma notificação foi criada
        successful_results = [r for r in results if r.get("success")]

        response = {
            "success": len(successful_results) > 0,
            "total_restart_times": len(restart_times),
            "successful_restart_times": len(successful_results),
            "total_notifications_created": total_notifications,
            "notification_minutes": notification_minutes,
            "results": results,
            "path": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\Notifications.json",
        }

        logger.info(
            f"Resumo: {len(successful_results)}/{len(restart_times)} horários processados com sucesso, {total_notifications} notificações criadas"
        )
        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro ao criar notificações para todos os horários: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/admin/send", methods=["POST"])
def send_admin_notification():
    """Enviar notificação administrativa usando templates"""
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

        message_type = data.get("type", "admin_announcement")
        custom_message = data.get("message", "")

        if not custom_message:
            return jsonify({"success": False, "error": "Mensagem é obrigatória"}), 400

        logger.info(
            f"Enviando notificação administrativa do tipo {message_type}: {custom_message}"
        )

        if not notification_manager:
            return (
                jsonify(
                    {"success": False, "error": "NotificationManager não inicializado"}
                ),
                500,
            )

        # Carregar template de mensagens administrativas
        template_path = "data/notifications/templates/custom_messages.json"
        try:
            import json

            with open(template_path, "r", encoding="utf-8") as f:
                template = json.load(f)

            # Buscar configurações do tipo de mensagem
            message_config = None
            for msg_type in template.get("admin_message_types", []):
                if msg_type["type"] == message_type:
                    message_config = msg_type
                    break

            if not message_config:
                # Usar configurações padrão se tipo não encontrado
                message_config = {"color": "255-255-100", "duration": 20}

            # Usar o novo método que cria notificações corretas
            result = notification_manager.create_correct_notifications(
                custom_message=custom_message,
                custom_duration=message_config.get("duration", 20),
                custom_color=message_config.get("color", "255-255-100"),
            )

            if result["success"]:
                logger.info(
                    f"Notificação administrativa enviada",
                    {
                        "type": message_type,
                        "message": custom_message,
                        "color": message_config.get("color"),
                        "duration": message_config.get("duration"),
                    },
                )

            return jsonify(result)

        except FileNotFoundError:
            # Fallback para configurações padrão se template não existir
            result = notification_manager.create_correct_notifications(
                custom_message=custom_message,
                custom_duration=20,
                custom_color="255-255-100",
            )

            # Recriar notificações de restart após mensagem administrativa (fallback)
            if result.get("success") and restart_scheduler:
                try:
                    logger.info(
                        "Recriando notificações de restart após mensagem administrativa (fallback)"
                    )

                    # Obter próximo restart agendado
                    next_restart = restart_scheduler.get_next_restart()
                    if next_restart:
                        # Recriar notificações de restart in-game
                        restart_scheduler._create_restart_notifications(
                            next_restart.strftime("%H:%M"), next_restart
                        )
                        logger.info(
                            f"Notificações de restart recriadas para {next_restart.strftime('%H:%M')}"
                        )
                    else:
                        logger.warn(
                            "Nenhum restart agendado encontrado para recriar notificações"
                        )

                except Exception as e:
                    logger.error(f"Erro ao recriar notificações de restart: {e}")

            return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao enviar notificação administrativa: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/admin/templates", methods=["GET"])
def get_admin_templates():
    """Obter templates de mensagens administrativas"""
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
        logger.info("Requisição de templates administrativos")

        template_path = "data/notifications/templates/custom_messages.json"
        try:
            import json

            with open(template_path, "r", encoding="utf-8") as f:
                template = json.load(f)

            response = {"success": True, "data": template, "timestamp": time.time()}

            return jsonify(response)

        except FileNotFoundError:
            return (
                jsonify(
                    {"success": False, "error": "Arquivo de templates não encontrado"}
                ),
                404,
            )

    except Exception as e:
        logger.error(f"Erro ao obter templates administrativos: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/scheduled", methods=["GET"])
def list_scheduled_notifications():
    """Listar notificações customizadas programadas"""
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
        if not notification_manager:
            return (
                jsonify({"success": False, "error": "NotificationManager não inicializado"}),
                500,
            )

        items = notification_manager.scheduled_manager.list()
        return jsonify({"success": True, "items": items, "timestamp": time.time()})
    except Exception as e:
        logger.error(f"Erro ao listar notificações programadas: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/scheduled/<item_id>", methods=["GET"])
def get_scheduled_notification(item_id: str):
    """Obter uma notificação programada"""
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
        if not notification_manager:
            return (
                jsonify({"success": False, "error": "NotificationManager não inicializado"}),
                500,
            )

        item = notification_manager.scheduled_manager.get(item_id)
        if not item:
            return jsonify({"success": False, "error": "Not found"}), 404
        return jsonify({"success": True, "item": item, "timestamp": time.time()})
    except Exception as e:
        logger.error(f"Erro ao obter notificação programada: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/scheduled/validate", methods=["POST"])
def validate_scheduled_notification():
    """Validar payload de notificação programada sem salvar"""
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
        if not notification_manager:
            return (
                jsonify({"success": False, "error": "NotificationManager não inicializado"}),
                500,
            )

        from core.notifications.scheduled_notifications_manager import (
            ScheduledNotificationConflictError,
        )

        payload = request.get_json() or {}
        ok, conflict = notification_manager.scheduled_manager.validate_item(payload)
        if not ok:
            return jsonify({"success": False, **(conflict or {})}), 409

        return jsonify({"success": True, "timestamp": time.time()})

    except ScheduledNotificationConflictError as e:
        return jsonify({"success": False, **(e.payload or {})}), 409
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao validar notificação programada: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/scheduled", methods=["POST"])
def create_scheduled_notification():
    """Criar notificação programada (persistente)"""
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
        if not notification_manager:
            return (
                jsonify({"success": False, "error": "NotificationManager não inicializado"}),
                500,
            )

        from core.notifications.scheduled_notifications_manager import (
            ScheduledNotificationConflictError,
        )

        payload = request.get_json() or {}
        item = notification_manager.scheduled_manager.create(payload)

        compile_result = notification_manager.compile_notifications()
        return jsonify(
            {
                "success": True,
                "item": item,
                "compile": compile_result,
                "timestamp": time.time(),
            }
        )
    except ScheduledNotificationConflictError as e:
        return jsonify({"success": False, **(e.payload or {})}), 409
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao criar notificação programada: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/scheduled/<item_id>", methods=["PUT"])
def update_scheduled_notification(item_id: str):
    """Atualizar notificação programada"""
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
        if not notification_manager:
            return (
                jsonify({"success": False, "error": "NotificationManager não inicializado"}),
                500,
            )

        from core.notifications.scheduled_notifications_manager import (
            ScheduledNotificationConflictError,
        )

        payload = request.get_json() or {}
        item = notification_manager.scheduled_manager.update(item_id, payload)

        compile_result = notification_manager.compile_notifications()
        return jsonify(
            {
                "success": True,
                "item": item,
                "compile": compile_result,
                "timestamp": time.time(),
            }
        )
    except ScheduledNotificationConflictError as e:
        return jsonify({"success": False, **(e.payload or {})}), 409
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except KeyError:
        return jsonify({"success": False, "error": "Not found"}), 404
    except Exception as e:
        logger.error(f"Erro ao atualizar notificação programada: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/scheduled/<item_id>", methods=["DELETE"])
def delete_scheduled_notification(item_id: str):
    """Remover notificação programada"""
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
        if not notification_manager:
            return (
                jsonify({"success": False, "error": "NotificationManager não inicializado"}),
                500,
            )

        deleted = notification_manager.scheduled_manager.delete(item_id)
        if not deleted:
            return jsonify({"success": False, "error": "Not found"}), 404

        compile_result = notification_manager.compile_notifications()
        return jsonify(
            {
                "success": True,
                "deleted": True,
                "compile": compile_result,
                "timestamp": time.time(),
            }
        )
    except Exception as e:
        logger.error(f"Erro ao remover notificação programada: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/compile", methods=["POST"])
def compile_notifications_now():
    """Forçar compilação do Notifications.json (restart do dia + customs válidas)"""
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
        if not notification_manager:
            return (
                jsonify({"success": False, "error": "NotificationManager não inicializado"}),
                500,
            )

        result = notification_manager.compile_notifications()
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Erro ao compilar notificações: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/time/send", methods=["POST"])
def send_time_notification():
    """Enviar notificação com horário do servidor"""
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
            import sqlite3
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

                # Converter time_of_day para formato legível CORRETAMENTE
                time_of_day = weather_data[0]
                hours = int(time_of_day)
                minutes = int((time_of_day - hours) * 60)
                server_time = f"{hours:02d}:{minutes:02d}"

                # Conversão de time_of_day para formato de hora

        except Exception as e:
            logger.error(f"Erro ao acessar banco SCUM: {e}")
            return (
                jsonify(
                    {"success": False, "error": f"Erro ao acessar banco SCUM: {e}"}
                ),
                500,
            )

        # Configurações da notificação
        message_template = data.get(
            "message_template", "🕐 Horário do servidor: {server_time}"
        )
        duration = data.get("duration", 15)
        color = data.get("color", "255-255-255")

        # Substituir placeholder pelo horário real
        message = message_template.replace("{server_time}", server_time)

        logger.info(f"Enviando notificação de horário: {message}")

        if not notification_manager:
            return (
                jsonify(
                    {"success": False, "error": "NotificationManager não inicializado"}
                ),
                500,
            )

        # Enviar notificação
        result = notification_manager.send_custom_notification(
            message=message, duration=duration, color=color
        )

        if result["success"]:
            logger.info(f"Notificação de horário enviada: {server_time}")

            # Enviar para Discord também
            try:
                if discord_webhook:
                    discord_webhook.send_webhook(
                        webhook_name="timer",
                        title="🕐 Notificação de Horário Enviada",
                        description=f"**Horário do servidor:** {server_time}",
                        color=0x00FF00,  # Verde
                        fields=[
                            {
                                "name": "Mensagem no jogo",
                                "value": message,
                                "inline": False,
                            },
                            {
                                "name": "Duração",
                                "value": f"{duration} segundos",
                                "inline": True,
                            },
                            {"name": "Cor", "value": color, "inline": True},
                        ],
                    )
            except Exception as e:
                logger.error(f"Erro ao enviar para Discord: {e}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao enviar notificação de horário: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/api/notifications/time/template", methods=["GET"])
def get_time_notification_template():
    """Obter template de notificação de horário"""
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
        logger.info("Requisição de template de notificação de horário")

        template_path = "data/notifications/templates/time_notification.json"
        try:
            import json

            with open(template_path, "r", encoding="utf-8") as f:
                template = json.load(f)

            response = {"success": True, "data": template, "timestamp": time.time()}

            return jsonify(response)

        except FileNotFoundError:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Template de notificação de horário não encontrado",
                    }
                ),
                404,
            )

    except Exception as e:
        logger.error(f"Erro ao obter template de notificação de horário: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


