"""
Blueprint: logs
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

logs_bp = Blueprint('logs', __name__)

@logs_bp.route("/api/logs/players", methods=["GET"])
def get_players_summary():
    """Obter resumo dos jogadores"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                503,
            )

        summary = log_processor.get_players_summary()
        return jsonify({"success": True, "data": summary})

    except Exception as e:
        logger.error(f"Erro ao obter resumo dos jogadores: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/logs/players/active", methods=["GET"])
def get_active_sessions():
    """Obter sessões ativas"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                503,
            )

        sessions = log_processor.get_active_sessions()
        return jsonify({"success": True, "data": sessions})

    except Exception as e:
        logger.error(f"Erro ao obter sessões ativas: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/logs/stats", methods=["GET"])
def get_logs_stats():
    """Obter estatísticas do sistema de logs"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                503,
            )

        # Estatísticas de processamento
        processing_stats = log_processor.get_processing_stats()

        # Estatísticas de arquivos processados
        files_stats = log_processor.get_processed_files_stats()

        # Estatísticas do banco de dados
        db_stats = log_processor.db_manager.get_database_stats()

        # Estatísticas dos jogadores
        players_stats = log_processor.db_manager.get_players_stats()

        return jsonify(
            {
                "success": True,
                "data": {
                    "processing": processing_stats,
                    "files": files_stats,
                    "database": db_stats,
                    "players": players_stats,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/logs/cleanup", methods=["POST"])
def cleanup_inactive_sessions():
    """Limpar sessões inativas"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                503,
            )

        # Obter timeout dos parâmetros (padrão: 24 horas)
        timeout_hours = request.json.get("timeout_hours", 24) if request.json else 24

        cleaned_count = log_processor.cleanup_inactive_sessions(timeout_hours)

        return jsonify(
            {
                "success": True,
                "data": {
                    "cleaned_sessions": cleaned_count,
                    "timeout_hours": timeout_hours,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao limpar sessões inativas: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/deduplication/status", methods=["GET"])
def get_deduplication_status():
    """Obter status do sistema de deduplicação"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                503,
            )

        # Obter informações de deduplicação
        processed_files_count = len(log_processor.processed_files)
        processing_locks_count = len(log_processor.processing_locks)

        # Status dos processadores
        processors_status = {
            "admin_logs": {
                "deduplication_enabled": log_processor.admin_log_processor is not None,
                "files_processed": 0,  # Seria necessário rastrear individualmente
                "last_processed": None,
            },
            "vehicle_destruction": {
                "deduplication_enabled": log_processor.vehicle_destruction_processor
                is not None,
                "files_processed": 0,
                "last_processed": None,
            },
            "chat": {
                "deduplication_enabled": log_processor.chat_processor is not None,
                "files_processed": 0,
                "last_processed": None,
            },
            "bunkers": {
                "deduplication_enabled": bunker_processor is not None,
                "files_processed": 0,
                "last_processed": None,
            },
            "chest_ownership": {
                "deduplication_enabled": log_processor.vehicle_processor is not None,
                "files_processed": 0,
                "last_processed": None,
            },
        }

        # Contar arquivos processados por tipo (aproximado)
        for file_path in log_processor.processed_files:
            filename = os.path.basename(file_path)
            if filename.startswith("admin_"):
                processors_status["admin_logs"]["files_processed"] += 1
            elif filename.startswith("vehicle_destruction_"):
                processors_status["vehicle_destruction"]["files_processed"] += 1
            elif filename.startswith("chat_"):
                processors_status["chat"]["files_processed"] += 1
            elif filename.startswith("gameplay_"):
                processors_status["bunkers"]["files_processed"] += 1
            elif filename.startswith("chest_ownership_"):
                processors_status["chest_ownership"]["files_processed"] += 1

        return jsonify(
            {
                "success": True,
                "data": {
                    "deduplication_active": True,
                    "processed_files_count": processed_files_count,
                    "processing_locks_count": processing_locks_count,
                    "last_cleanup": None,  # Não rastreado atualmente
                    "processors_status": processors_status,
                },
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter status de deduplicação: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/deduplication/clear-cache", methods=["POST"])
def clear_deduplication_cache():
    """Limpar cache de deduplicação"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                503,
            )

        # Contar antes de limpar
        processed_files_cleared = len(log_processor.processed_files)
        processing_locks_cleared = len(log_processor.processing_locks)

        # Limpar cache
        log_processor.processed_files.clear()
        log_processor.processing_locks.clear()

        logger.info(
            f"Cache de deduplicação limpo: {processed_files_cleared} arquivos processados, {processing_locks_cleared} locks"
        )

        return jsonify(
            {
                "success": True,
                "message": "Cache de deduplicação limpo com sucesso",
                "data": {
                    "processed_files_cleared": processed_files_cleared,
                    "processing_locks_cleared": processing_locks_cleared,
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao limpar cache de deduplicação: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/deduplication/force-reprocess", methods=["POST"])
def force_reprocess_file():
    """Forçar reprocessamento de um arquivo específico"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                503,
            )

        data = request.json or {}
        file_path = data.get("file_path")

        if not file_path:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Parâmetros inválidos",
                        "details": "file_path é obrigatório",
                    }
                ),
                400,
            )

        # Verificar se o arquivo existe
        if not os.path.exists(file_path):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Arquivo não encontrado",
                        "details": f"Arquivo {file_path} não existe",
                    }
                ),
                404,
            )

        # Remover do cache de processados
        removed_from_processed = file_path in log_processor.processed_files
        if removed_from_processed:
            log_processor.processed_files.discard(file_path)

        # Remover do lock também
        log_processor.processing_locks.discard(file_path)

        logger.info("Arquivo marcado para reprocessamento")

        return jsonify(
            {
                "success": True,
                "message": "Arquivo marcado para reprocessamento",
                "data": {
                    "file_path": file_path,
                    "removed_from_processed": removed_from_processed,
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao forçar reprocessamento: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "details": "Falha ao acessar sistema de deduplicação",
                }
            ),
            500,
        )


@logs_bp.route("/api/admin-logs/status", methods=["GET"])
def get_admin_logs_status():
    """Obter status do sistema de admin logs"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                500,
            )

        admin_log_processor = log_processor.admin_log_processor

        if not admin_log_processor:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Sistema de admin logs não inicializado",
                    }
                ),
                500,
            )

        # Verificar webhook
        webhook_url = admin_log_processor._get_admin_webhook_url()
        webhook_configured = webhook_url is not None

        # Obter último comando processado
        last_command = admin_log_processor._get_last_processed_command()

        # Obter estatísticas básicas
        stats = admin_log_processor.get_processing_stats()

        # Contar comandos por categoria
        try:
            import sqlite3

            conn = sqlite3.connect("data/SSM.db")
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT category, COUNT(*) 
                FROM admin_commands_processed 
                GROUP BY category
            """
            )
            categories_data = cursor.fetchall()

            commands_by_category = {cat: count for cat, count in categories_data}

            # Admin mais ativo
            cursor.execute(
                """
                SELECT steam_id, player_name, COUNT(*) as count
                FROM admin_commands_processed
                GROUP BY steam_id, player_name
                ORDER BY count DESC
                LIMIT 1
            """
            )
            top_admin = cursor.fetchone()
            most_active_admin = None
            if top_admin:
                most_active_admin = f"{top_admin[1]} ({top_admin[0]})"

            # Última atividade
            cursor.execute(
                """
                SELECT timestamp 
                FROM admin_commands_processed 
                ORDER BY created_at DESC 
                LIMIT 1
            """
            )
            last_activity_row = cursor.fetchone()
            last_activity = last_activity_row[0] if last_activity_row else None

            conn.close()
        except Exception as e:
            logger.error(f"Erro ao consultar banco de admin logs: {e}")
            commands_by_category = {}
            most_active_admin = None
            last_activity = None

        return jsonify(
            {
                "success": True,
                "data": {
                    "admin_log_processor": True,
                    "webhook_configured": webhook_configured,
                    "last_processed_command": last_command,
                    "total_commands_processed": stats.get("total_commands", 0),
                    "commands_by_category": commands_by_category,
                    "most_active_admin": most_active_admin,
                    "last_activity": last_activity,
                },
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter status de admin logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/admin-logs/stats", methods=["GET"])
def get_admin_logs_stats():
    """Obter estatísticas detalhadas dos admin logs"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                500,
            )

        admin_log_processor = log_processor.admin_log_processor

        if not admin_log_processor:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Sistema de admin logs não inicializado",
                    }
                ),
                500,
            )

        try:
            import sqlite3

            conn = sqlite3.connect("data/SSM.db")
            cursor = conn.cursor()

            # Total de comandos
            cursor.execute("SELECT COUNT(*) FROM admin_commands_processed")
            total_commands = cursor.fetchone()[0]

            # Comandos hoje
            today = datetime.now().date().isoformat()
            cursor.execute(
                """
                SELECT COUNT(*) FROM admin_commands_processed 
                WHERE DATE(created_at) = ?
            """,
                (today,),
            )
            commands_today = cursor.fetchone()[0]

            # Comandos esta semana
            week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
            cursor.execute(
                """
                SELECT COUNT(*) FROM admin_commands_processed 
                WHERE DATE(created_at) >= ?
            """,
                (week_ago,),
            )
            commands_this_week = cursor.fetchone()[0]

            # Comandos este mês
            month_ago = (datetime.now() - timedelta(days=30)).date().isoformat()
            cursor.execute(
                """
                SELECT COUNT(*) FROM admin_commands_processed 
                WHERE DATE(created_at) >= ?
            """,
                (month_ago,),
            )
            commands_this_month = cursor.fetchone()[0]

            # Estatísticas por categoria
            try:
                cursor.execute(
                    """
                    SELECT COALESCE(category_key, category) as category_key, COUNT(*) as count
                    FROM admin_commands_processed
                    GROUP BY COALESCE(category_key, category)
                """
                )
            except Exception:
                cursor.execute(
                    """
                    SELECT category as category_key, COUNT(*) as count
                    FROM admin_commands_processed
                    GROUP BY category
                """
                )

            categories_data = cursor.fetchall()

            categories = {}
            for cat_key, count in categories_data:
                percentage = (count / total_commands * 100) if total_commands > 0 else 0
                cat_info = admin_log_processor._get_category_config(cat_key)

                categories[cat_info.get("category", cat_key)] = {
                    "count": count,
                    "percentage": round(percentage, 1),
                    "emoji": cat_info.get("emoji", "📋"),
                    "color": f"#{hex(cat_info.get('color', 0x2ecc71))[2:]}",
                    "name": cat_info.get("name", "Other"),
                }

            # Top admins
            cursor.execute(
                """
                SELECT steam_id, player_name, COUNT(*) as count
                FROM admin_commands_processed
                GROUP BY steam_id, player_name
                ORDER BY count DESC
                LIMIT 10
            """
            )
            top_admins_data = cursor.fetchall()

            top_admins = []
            for steam_id, player_name, count in top_admins_data:
                percentage = (count / total_commands * 100) if total_commands > 0 else 0
                top_admins.append(
                    {
                        "steam_id": steam_id,
                        "name": player_name,
                        "commands_count": count,
                        "percentage": round(percentage, 1),
                    }
                )

            conn.close()

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "total_commands": total_commands,
                        "commands_today": commands_today,
                        "commands_this_week": commands_this_week,
                        "commands_this_month": commands_this_month,
                        "categories": categories,
                        "top_admins": top_admins,
                    },
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de admin logs: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de admin logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/admin-logs/recent", methods=["GET"])
def get_admin_logs_recent():
    """Obter últimos comandos admin processados"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                500,
            )

        admin_log_processor = log_processor.admin_log_processor

        if not admin_log_processor:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Sistema de admin logs não inicializado",
                    }
                ),
                500,
            )

        # Obter limite (padrão: 10)
        limit_raw = request.args.get("limit", "10")
        try:
            limit = int(limit_raw)
        except Exception:
            return jsonify({"success": False, "error": "Parâmetro 'limit' inválido"}), 400

        if limit < 1:
            limit = 1
        if limit > 200:
            limit = 200

        include_total = str(request.args.get("include_total", "false")).strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
            "on",
        )

        category_filters = request.args.getlist("category")
        steam_id_filter = request.args.get("steam_id")
        player_name_filter = request.args.get("player_name")
        q_filter = request.args.get("q")

        try:
            import sqlite3

            conn = sqlite3.connect("data/SSM.db")
            cursor = conn.cursor()

            where_clauses = []
            params = []

            if category_filters:
                normalized = [c.strip().lower() for c in category_filters if (c or "").strip()]
                if normalized:
                    category_aliases = {
                        "teleport": ["teleport"],
                        "spawn": ["spawn", "spawn item", "spawn_item", "spawnitem"],
                        "godmode": ["godmode", "god mode", "god_mode"],
                        "info": ["info", "player info", "player_info"],
                        "punishments": [
                            "punishments",
                            "server punishments",
                            "server_punishments",
                            "punishment",
                            "punishments",
                        ],
                        "other": ["other"],
                    }

                    expanded = []
                    seen = set()
                    for key in normalized:
                        values = category_aliases.get(key, [key])
                        for v in values:
                            vv = (v or "").strip().lower()
                            if vv and vv not in seen:
                                seen.add(vv)
                                expanded.append(vv)

                    placeholders = ",".join(["?"] * len(expanded))
                    where_clauses.append(
                        f"LOWER(COALESCE(category_key, category)) IN ({placeholders})"
                    )
                    params.extend(expanded)

            if steam_id_filter:
                where_clauses.append("steam_id = ?")
                params.append(steam_id_filter)

            if player_name_filter:
                where_clauses.append("LOWER(player_name) LIKE ?")
                params.append(f"%{player_name_filter.strip().lower()}%")

            if q_filter:
                where_clauses.append("LOWER(action) LIKE ?")
                params.append(f"%{q_filter.strip().lower()}%")

            where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            # Obter últimos comandos (compatível com schemas antigos)
            try:
                cursor.execute(
                    f"""
                    SELECT command_id, timestamp, steam_id, player_name, action,
                           COALESCE(category_key, category) as category_key,
                           category_name,
                           event_type
                    FROM admin_commands_processed
                    {where_sql}
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (*params, limit),
                )
            except Exception:
                cursor.execute(
                    f"""
                    SELECT command_id, timestamp, steam_id, player_name, action,
                           category as category_key,
                           NULL as category_name,
                           NULL as event_type
                    FROM admin_commands_processed
                    {where_sql}
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (*params, limit),
                )

            commands_data = cursor.fetchall()

            total = None
            if include_total:
                cursor.execute(
                    f"SELECT COUNT(*) FROM admin_commands_processed{where_sql}",
                    params,
                )
                total = cursor.fetchone()[0]

            conn.close()

            # Formatar comandos
            commands = []
            for (
                cmd_id,
                ts,
                steam_id,
                player_name,
                action,
                category_key,
                category_name,
                event_type,
            ) in commands_data:
                cat_info = admin_log_processor._get_category_config(category_key)
                if category_name:
                    cat_info = {
                        **cat_info,
                        "name": category_name,
                    }

                commands.append(
                    {
                        "command_id": cmd_id,
                        "timestamp": ts,
                        "steam_id": steam_id,
                        "player_name": player_name,
                        "action": action,
                        "event_type": event_type,
                        "category": {
                            "key": cat_info.get("category", "other"),
                            "name": cat_info.get("name", "Other"),
                            "emoji": cat_info.get("emoji", "📋"),
                            "color": f"#{hex(cat_info.get('color', 0x2ecc71))[2:]}",
                        },
                    }
                )

            return jsonify(
                {
                    "success": True,
                    "data": {"commands": commands, "total": total, "limit": limit},
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            logger.error(f"Erro ao obter comandos recentes: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    except Exception as e:
        logger.error(f"Erro ao obter comandos recentes: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/admin-logs/processing-status", methods=["GET"])
def get_admin_logs_processing_status():
    """Obter status do processamento de admin logs"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                500,
            )

        admin_log_processor = log_processor.admin_log_processor

        if not admin_log_processor:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Sistema de admin logs não inicializado",
                    }
                ),
                500,
            )

        # Verificar webhook
        webhook_url = admin_log_processor._get_admin_webhook_url()

        # Obter último comando processado
        last_command = admin_log_processor._get_last_processed_command()

        # Verificar arquivo mais recente
        logs_directory = path_helper.get_scum_logs_directory()
        latest_file = admin_log_processor._find_latest_admin_log(logs_directory)

        return jsonify(
            {
                "success": True,
                "data": {
                    "admin_log_processor_active": True,
                    "webhook_configured": webhook_url is not None,
                    "last_processed_command": last_command,
                    "latest_log_file": (
                        os.path.basename(latest_file) if latest_file else None
                    ),
                    "logs_directory": logs_directory,
                },
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter status de processamento: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/admin-logs/files-status", methods=["GET"])
def get_admin_logs_files_status():
    """Obter status dos arquivos de admin logs"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                500,
            )

        admin_log_processor = log_processor.admin_log_processor

        if not admin_log_processor:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Sistema de admin logs não inicializado",
                    }
                ),
                500,
            )

        logs_directory = path_helper.get_scum_logs_directory()

        try:
            import sqlite3

            # Listar arquivos admin
            admin_files = []
            if os.path.exists(logs_directory):
                for filename in os.listdir(logs_directory):
                    if filename.startswith("admin_") and filename.endswith(".log"):
                        file_path = os.path.join(logs_directory, filename)
                        file_size = os.path.getsize(file_path)
                        mtime = os.path.getmtime(file_path)
                        modified_time = datetime.fromtimestamp(mtime).isoformat()

                        # Verificar se foi processado
                        try:
                            conn = sqlite3.connect("data/SSM.db")
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                SELECT COUNT(*) FROM log_files_processed 
                                WHERE filename = ?
                            """,
                                (filename,),
                            )
                            is_processed = cursor.fetchone()[0] > 0
                            conn.close()
                        except:
                            is_processed = False

                        admin_files.append(
                            {
                                "filename": filename,
                                "size_bytes": file_size,
                                "size_mb": round(file_size / (1024 * 1024), 2),
                                "modified_time": modified_time,
                                "processed": is_processed,
                            }
                        )

            # Ordenar por data de modificação (mais recente primeiro)
            admin_files.sort(key=lambda x: x["modified_time"], reverse=True)

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "logs_directory": logs_directory,
                        "total_files": len(admin_files),
                        "files": admin_files[:20],  # Limitar a 20 arquivos
                        "latest_file": (
                            admin_files[0]["filename"] if admin_files else None
                        ),
                    },
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            logger.error(f"Erro ao obter status de arquivos: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    except Exception as e:
        logger.error(f"Erro ao obter status de arquivos: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/kill-logs/recent", methods=["GET"])
def get_kill_logs_recent():
    """Obter eventos de kill recentes"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                500,
            )

        db_manager = log_processor.db_manager

        # Obter parâmetros
        limit = int(request.args.get("limit", 50))
        event_type = request.args.get("event_type")
        victim_steam_id = request.args.get("victim_steam_id")
        killer_steam_id = request.args.get("killer_steam_id")

        # Buscar eventos
        events = db_manager.get_kill_events(
            victim_steam_id=victim_steam_id,
            killer_steam_id=killer_steam_id,
            event_type=event_type,
            limit=limit,
        )

        # Contar total
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            where_conditions = []
            params = []

            if event_type:
                where_conditions.append("event_type = ?")
                params.append(event_type)
            if victim_steam_id:
                where_conditions.append("victim_steam_id = ?")
                params.append(victim_steam_id)
            if killer_steam_id:
                where_conditions.append("killer_steam_id = ?")
                params.append(killer_steam_id)

            where_clause = (
                "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            )

            cursor.execute(f"SELECT COUNT(*) FROM kill_events {where_clause}", params)
            total = cursor.fetchone()[0]
            conn.close()
        except Exception as e:
            logger.error(f"Erro ao contar eventos: {e}")
            total = len(events)

        # Formatar eventos com estrutura aninhada
        formatted_events = []
        for event in events:
            formatted_event = {
                "id": event.get("id"),
                "event_type": event.get("event_type", "kill"),
                "timestamp": event.get("timestamp"),
                "game_time": event.get("game_time"),
                "victim": {
                    "steam_id": event.get("victim_steam_id"),
                    "player_id": event.get("victim_player_id"),
                    "name": event.get("victim_name"),
                    "location": {
                        "x": event.get("victim_location_x"),
                        "y": event.get("victim_location_y"),
                        "z": event.get("victim_location_z"),
                    },
                },
                "killer": None,
                "weapon": None,
                "distance": event.get("distance"),
                "is_in_game_event": bool(event.get("is_in_game_event", False)),
                "discord_sent": bool(event.get("discord_sent", False)),
                "created_at": event.get("created_at"),
            }

            # Adicionar killer se existir
            if event.get("killer_profile_name"):
                formatted_event["killer"] = {
                    "steam_id": event.get("killer_steam_id"),
                    "user_id": event.get("killer_user_id"),
                    "profile_name": event.get("killer_profile_name"),
                    "is_npc": bool(event.get("killer_is_npc", False)),
                    "location": {
                        "x": event.get("killer_location_x"),
                        "y": event.get("killer_location_y"),
                        "z": event.get("killer_location_z"),
                    },
                    "has_immortality": bool(event.get("killer_has_immortality", False)),
                }

            # Adicionar weapon se existir
            if event.get("weapon"):
                formatted_event["weapon"] = {
                    "name": event.get("weapon"),
                    "type": event.get("weapon_type"),
                }

            formatted_events.append(formatted_event)

        return jsonify(
            {
                "success": True,
                "data": {
                    "events": formatted_events,
                    "total": total,
                    "count": len(formatted_events),
                    "limit": limit,
                },
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter eventos de kill recentes: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/kill-logs/stats", methods=["GET"])
def get_kill_logs_stats():
    """Obter estatísticas de kill logs"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                500,
            )

        db_manager = log_processor.db_manager

        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Total de eventos
            cursor.execute("SELECT COUNT(*) FROM kill_events")
            total_events = cursor.fetchone()[0]

            # Eventos hoje
            cursor.execute(
                """
                SELECT COUNT(*) FROM kill_events 
                WHERE date(timestamp) = date('now')
            """
            )
            events_today = cursor.fetchone()[0]

            # Eventos esta semana
            cursor.execute(
                """
                SELECT COUNT(*) FROM kill_events 
                WHERE timestamp >= datetime('now', '-7 days')
            """
            )
            events_this_week = cursor.fetchone()[0]

            # Eventos este mês
            cursor.execute(
                """
                SELECT COUNT(*) FROM kill_events 
                WHERE timestamp >= datetime('now', '-30 days')
            """
            )
            events_this_month = cursor.fetchone()[0]

            # Por tipo de evento
            cursor.execute(
                """
                SELECT event_type, COUNT(*) as count 
                FROM kill_events 
                GROUP BY event_type
            """
            )
            by_event_type = {}
            total_for_percentage = total_events if total_events > 0 else 1
            for row in cursor.fetchall():
                event_type = row["event_type"]
                count = row["count"]
                by_event_type[event_type] = {
                    "count": count,
                    "percentage": round((count / total_for_percentage) * 100, 1),
                }

            # Por tipo de killer (NPC vs Player)
            cursor.execute(
                """
                SELECT 
                    CASE WHEN killer_is_npc = 1 THEN 'npc' ELSE 'player' END as killer_type,
                    COUNT(*) as count
                FROM kill_events 
                WHERE event_type = 'kill'
                GROUP BY killer_type
            """
            )
            by_killer_type = {}
            total_kills = by_event_type.get("kill", {}).get("count", 0)
            total_kills_for_percentage = total_kills if total_kills > 0 else 1
            for row in cursor.fetchall():
                killer_type = row["killer_type"]
                count = row["count"]
                by_killer_type[killer_type] = {
                    "count": count,
                    "percentage": round((count / total_kills_for_percentage) * 100, 1),
                }

            # Top armas
            cursor.execute(
                """
                SELECT weapon, COUNT(*) as count 
                FROM kill_events 
                WHERE weapon IS NOT NULL AND event_type = 'kill'
                GROUP BY weapon 
                ORDER BY count DESC 
                LIMIT 10
            """
            )
            top_weapons = []
            for row in cursor.fetchall():
                count = row["count"]
                top_weapons.append(
                    {
                        "weapon": row["weapon"],
                        "count": count,
                        "percentage": (
                            round((count / total_kills_for_percentage) * 100, 1)
                            if total_kills_for_percentage > 0
                            else 0
                        ),
                    }
                )

            # Top vítimas
            cursor.execute(
                """
                SELECT victim_steam_id, victim_name, COUNT(*) as deaths
                FROM kill_events 
                WHERE victim_steam_id IS NOT NULL
                GROUP BY victim_steam_id, victim_name
                ORDER BY deaths DESC 
                LIMIT 10
            """
            )
            top_victims = []
            for row in cursor.fetchall():
                deaths = row["deaths"]
                top_victims.append(
                    {
                        "steam_id": row["victim_steam_id"],
                        "name": row["victim_name"],
                        "deaths": deaths,
                        "percentage": (
                            round((deaths / total_for_percentage) * 100, 1)
                            if total_for_percentage > 0
                            else 0
                        ),
                    }
                )

            # Top killers (apenas jogadores, não NPCs)
            cursor.execute(
                """
                SELECT killer_steam_id, killer_profile_name, COUNT(*) as kills
                FROM kill_events 
                WHERE killer_steam_id IS NOT NULL 
                    AND killer_is_npc = 0 
                    AND event_type = 'kill'
                GROUP BY killer_steam_id, killer_profile_name
                ORDER BY kills DESC 
                LIMIT 10
            """
            )
            top_killers = []
            for row in cursor.fetchall():
                kills = row["kills"]
                top_killers.append(
                    {
                        "steam_id": row["killer_steam_id"],
                        "name": row["killer_profile_name"],
                        "kills": kills,
                        "percentage": (
                            round((kills / total_kills_for_percentage) * 100, 1)
                            if total_kills_for_percentage > 0
                            else 0
                        ),
                    }
                )

            # Distância média
            cursor.execute(
                """
                SELECT AVG(distance) as avg_distance 
                FROM kill_events 
                WHERE distance IS NOT NULL AND event_type = 'kill'
            """
            )
            avg_distance_row = cursor.fetchone()
            average_distance = (
                round(avg_distance_row["avg_distance"], 2)
                if avg_distance_row["avg_distance"]
                else 0
            )

            # Notificações Discord enviadas
            cursor.execute("SELECT COUNT(*) FROM kill_events WHERE discord_sent = 1")
            discord_notifications_sent = cursor.fetchone()[0]

            conn.close()

            stats = {
                "total_events": total_events,
                "events_today": events_today,
                "events_this_week": events_this_week,
                "events_this_month": events_this_month,
                "by_event_type": by_event_type,
                "by_killer_type": by_killer_type,
                "top_weapons": top_weapons,
                "top_victims": top_victims,
                "top_killers": top_killers,
                "average_distance": average_distance,
                "discord_notifications_sent": discord_notifications_sent,
            }

            return jsonify({"success": True, "data": stats, "timestamp": time.time()})

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de kill logs: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de kill logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@logs_bp.route("/api/kill-logs/events", methods=["GET"])
def get_kill_logs_events():
    """Obter eventos de kill com filtros e paginação"""
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
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Sistema de logs não inicializado"}
                ),
                500,
            )

        db_manager = log_processor.db_manager

        # Obter parâmetros
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        event_type = request.args.get("event_type")
        victim_steam_id = request.args.get("victim_steam_id")
        killer_steam_id = request.args.get("killer_steam_id")
        killer_is_npc = request.args.get("killer_is_npc")
        weapon = request.args.get("weapon")
        weapon_type = request.args.get("weapon_type")
        from_date = request.args.get("from_date")
        to_date = request.args.get("to_date")

        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Construir query com filtros
            where_conditions = []
            params = []

            if event_type:
                where_conditions.append("event_type = ?")
                params.append(event_type)

            if victim_steam_id:
                where_conditions.append("victim_steam_id = ?")
                params.append(victim_steam_id)

            if killer_steam_id:
                where_conditions.append("killer_steam_id = ?")
                params.append(killer_steam_id)

            if killer_is_npc is not None:
                killer_is_npc_bool = killer_is_npc.lower() == "true"
                where_conditions.append("killer_is_npc = ?")
                params.append(1 if killer_is_npc_bool else 0)

            if weapon:
                where_conditions.append("weapon = ?")
                params.append(weapon)

            if weapon_type:
                where_conditions.append("weapon_type = ?")
                params.append(weapon_type)

            if from_date:
                where_conditions.append("timestamp >= ?")
                params.append(from_date)

            if to_date:
                where_conditions.append("timestamp <= ?")
                params.append(to_date)

            where_clause = (
                "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            )

            # Contar total
            cursor.execute(f"SELECT COUNT(*) FROM kill_events {where_clause}", params)
            total = cursor.fetchone()[0]

            # Buscar eventos com paginação
            query = f"""
                SELECT * FROM kill_events 
                {where_clause}
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            cursor.execute(query, params)

            events = []
            for row in cursor.fetchall():
                event = dict(row)
                # Converter booleanos
                event["killer_is_npc"] = bool(event.get("killer_is_npc", 0))
                event["killer_has_immortality"] = bool(
                    event.get("killer_has_immortality", 0)
                )
                event["is_in_game_event"] = bool(event.get("is_in_game_event", 0))
                event["discord_sent"] = bool(event.get("discord_sent", 0))
                events.append(event)

            conn.close()

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "events": events,
                        "total": total,
                        "count": len(events),
                        "limit": limit,
                        "offset": offset,
                    },
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            logger.error(f"Erro ao consultar eventos de kill: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    except Exception as e:
        logger.error(f"Erro ao obter eventos de kill: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


