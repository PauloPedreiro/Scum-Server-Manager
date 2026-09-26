"""
Blueprint: reports
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
from core.reports.player_count_calculator import PlayerCountCalculator
from .helpers import _get_ssm_database_path

reports_bp = Blueprint('reports', __name__)

@reports_bp.route("/api/reports/players/hourly-average", methods=["GET"])
def get_players_hourly_average():
    """Obter média de jogadores por hora do dia"""
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
        # Obter parâmetros
        days = request.args.get("days", type=int) or 7
        if days < 1:
            days = 1
        elif days > 365:
            days = 365

        # Calcular período
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Obter caminho do banco
        db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        # Calcular dados
        calculator = PlayerCountCalculator(db_path)
        hourly_data = calculator.get_hourly_average(start_date, end_date)

        # Calcular estatísticas gerais
        if hourly_data and len(hourly_data) > 0:
            # Filtrar apenas horas com dados válidos
            valid_hours = [h for h in hourly_data if h.get("samples", 0) > 0]
            
            if valid_hours:
                overall_average = sum(h["average"] for h in valid_hours) / len(valid_hours)
                
                # Verificar se todas as médias são iguais
                all_same = all(
                    h["average"] == valid_hours[0]["average"] for h in valid_hours
                )
                
                if all_same:
                    # Se todas as médias são iguais, não há pico ou baixa
                    peak_hour_data = None
                    lowest_hour_data = None
                else:
                    peak_hour_data = max(valid_hours, key=lambda x: x["average"])
                    lowest_hour_data = min(valid_hours, key=lambda x: x["average"])
            else:
                overall_average = 0
                peak_hour_data = None
                lowest_hour_data = None
        else:
            overall_average = 0
            peak_hour_data = None
            lowest_hour_data = None

        # Encontrar pico absoluto (dia + hora exatos)
        # Usa interval_minutes=15 que corresponde a 4 snapshots por hora
        absolute_peak = calculator.get_absolute_peak(start_date, end_date, interval_minutes=15)

        return jsonify(
            {
                "success": True,
                "data": {
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                        "days": days,
                    },
                    "by_hour": hourly_data,
                    "overall_average": round(overall_average, 2),
                    "peak_hour": peak_hour_data["hour"] if peak_hour_data else None,
                    "peak_hour_average": (
                        peak_hour_data["average"] if peak_hour_data else 0
                    ),
                    "lowest_hour": lowest_hour_data["hour"] if lowest_hour_data else None,
                    "lowest_hour_average": (
                        lowest_hour_data["average"] if lowest_hour_data else 0
                    ),
                    "absolute_peak": absolute_peak,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter média horária de jogadores: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@reports_bp.route("/api/reports/players/chart-data", methods=["GET"])
def get_players_chart_data():
    """Obter dados formatados para gráfico"""
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
        # Obter parâmetros
        days = request.args.get("days", type=int) or 7
        if days < 1:
            days = 1
        elif days > 365:
            days = 365

        granularity = request.args.get("granularity", "hour")  # 'hour' ou 'day'
        if granularity not in ["hour", "day"]:
            granularity = "hour"

        # Calcular período
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Obter caminho do banco
        db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        # Calcular dados
        calculator = PlayerCountCalculator(db_path)
        chart_data = calculator.get_chart_data(start_date, end_date, granularity)

        return jsonify(
            {
                "success": True,
                "data": {
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                        "days": days,
                    },
                    "granularity": granularity,
                    **chart_data,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter dados de gráfico: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@reports_bp.route("/api/reports/players/daily-average", methods=["GET"])
def get_players_daily_average():
    """Obter média de jogadores por dia"""
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
        # Obter parâmetros
        days = request.args.get("days", type=int) or 7
        if days < 1:
            days = 1
        elif days > 365:
            days = 365

        interval_minutes = request.args.get("interval_minutes", type=int) or 15
        if interval_minutes < 5:
            interval_minutes = 5
        elif interval_minutes > 60:
            interval_minutes = 60

        # Calcular período
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Obter caminho do banco
        db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        # Calcular dados
        calculator = PlayerCountCalculator(db_path)
        daily_data = calculator.get_daily_average(
            start_date, end_date, interval_minutes
        )

        # Calcular estatísticas gerais
        if daily_data:
            overall_average = sum(d["average"] for d in daily_data) / len(daily_data)
            peak_day = max(daily_data, key=lambda x: x["peak"])
            lowest_day = min(daily_data, key=lambda x: x["lowest"])
        else:
            overall_average = 0
            peak_day = None
            lowest_day = None

        # Encontrar pico absoluto (dia + hora exatos)
        absolute_peak = calculator.get_absolute_peak(
            start_date, end_date, interval_minutes
        )

        return jsonify(
            {
                "success": True,
                "data": {
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                        "days": days,
                    },
                    "interval_minutes": interval_minutes,
                    "by_day": daily_data,
                    "overall_average": round(overall_average, 2),
                    "peak_day": peak_day["date"] if peak_day else None,
                    "peak_day_count": peak_day["peak"] if peak_day else 0,
                    "lowest_day": lowest_day["date"] if lowest_day else None,
                    "lowest_day_count": lowest_day["lowest"] if lowest_day else 0,
                    "absolute_peak": absolute_peak,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter média diária de jogadores: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


