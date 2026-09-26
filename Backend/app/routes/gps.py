"""
Blueprint: gps
"""
from typing import Dict, Any, List, Optional, Tuple
from core.database.connector import DatabaseConnector

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac
from functools import wraps
from core.auth.decorators import require_auth, require_admin
from datetime import datetime, timedelta, timezone
import sqlite3
from .helpers import _get_ssm_database_path


gps_bp = Blueprint('gps', __name__)

@gps_bp.route("/api/gps/sync/status", methods=["GET"])
def get_gps_sync_status():
    """Obter status do serviço de sincronização de GPS"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    shop_delivery_service = getattr(services, 'shop_delivery_service', None)
    rewards_service = getattr(services, 'rewards_service', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
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
    try:
        if player_gps_sync_service is None:
            return (
                jsonify(
                    {"success": False, "error": "PlayerGpsSyncService não inicializado"}
                ),
                500,
            )

        status = player_gps_sync_service.get_status()

        return jsonify({"success": True, "data": status, "timestamp": time.time()})

    except Exception as e:
        logger.error(f"Erro ao obter status do serviço de GPS: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@gps_bp.route("/api/gps/sync/start", methods=["POST"])
def start_gps_sync():
    """Iniciar serviço de sincronização de GPS"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    shop_delivery_service = getattr(services, 'shop_delivery_service', None)
    rewards_service = getattr(services, 'rewards_service', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
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
    try:
        if player_gps_sync_service is None:
            return (
                jsonify(
                    {"success": False, "error": "PlayerGpsSyncService não inicializado"}
                ),
                500,
            )

        result = player_gps_sync_service.start()

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Erro ao iniciar serviço de GPS: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@gps_bp.route("/api/gps/sync/stop", methods=["POST"])
def stop_gps_sync():
    """Parar serviço de sincronização de GPS"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    shop_delivery_service = getattr(services, 'shop_delivery_service', None)
    rewards_service = getattr(services, 'rewards_service', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
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
    try:
        if player_gps_sync_service is None:
            return (
                jsonify(
                    {"success": False, "error": "PlayerGpsSyncService não inicializado"}
                ),
                500,
            )

        result = player_gps_sync_service.stop()

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Erro ao parar serviço de GPS: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@gps_bp.route("/api/gps/sync/run-now", methods=["POST"])
def run_gps_sync_now():
    """Executar sincronização de GPS imediatamente"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    shop_delivery_service = getattr(services, 'shop_delivery_service', None)
    rewards_service = getattr(services, 'rewards_service', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
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
    try:
        if player_gps_sync_service is None:
            return (
                jsonify(
                    {"success": False, "error": "PlayerGpsSyncService não inicializado"}
                ),
                500,
            )

        result = player_gps_sync_service.sync_once()

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Erro ao executar sincronização de GPS: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@gps_bp.route("/api/gps/online", methods=["GET"])
def get_online_players_gps():
    """Obter dados de GPS apenas dos jogadores online"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    shop_delivery_service = getattr(services, 'shop_delivery_service', None)
    rewards_service = getattr(services, 'rewards_service', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
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
    try:
        db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(db_path, timeout=30.0, write_mode=False) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Buscar GPS apenas de jogadores online
            cursor.execute(
                """
                SELECT 
                    gps.*,
                    po.player_name as online_player_name,
                    po.last_activity,
                    po.coordinates_x as ssm_coord_x,
                    po.coordinates_y as ssm_coord_y,
                    po.coordinates_z as ssm_coord_z
                FROM player_gps_snapshot gps
                INNER JOIN players_online po ON gps.steam_id = po.steam_id
                WHERE po.status = 'online'
                ORDER BY po.last_activity DESC
            """
            )

            rows = cursor.fetchall()

            # Agrupar por steam_id
            players_gps = {}
            for row in rows:
                steam_id = row["steam_id"]
                if steam_id not in players_gps:
                    players_gps[steam_id] = {
                        "steam_id": steam_id,
                        "player_name": row["online_player_name"] or row["player_name"],
                        "last_activity": row["last_activity"],
                        "ssm_coordinates": {
                            "x": row["ssm_coord_x"],
                            "y": row["ssm_coord_y"],
                            "z": row["ssm_coord_z"],
                        },
                        "gps_data": {"spawns": []},
                    }

                # Adicionar spawn
                spawn = {
                    "type": row["type"],
                    "type_label": (
                        "Spawn Padrão" if row["type"] == 0 else "Spawn em Abrigo"
                    ),
                    "location": {
                        "x": row["location_x"],
                        "y": row["location_y"],
                        "z": row["location_z"],
                    },
                    "rotation": {
                        "pitch": row["rotation_pitch"],
                        "yaw": row["rotation_yaw"],
                        "roll": row["rotation_roll"],
                    },
                    "movement": {
                        "velocity": {
                            "x": row["velocity_x"],
                            "y": row["velocity_y"],
                            "z": row["velocity_z"],
                        }
                    },
                    "shelter_id": row["shelter_id"],
                    "map_id": row["map_id"],
                    "last_updated": row["last_updated"],

                    # Compatibilidade retroativa e plana com o frontend
                    "prisoner_id": row["prisoner_id"],
                    "location_x": row["location_x"],
                    "location_y": row["location_y"],
                    "location_z": row["location_z"],
                    "rotation_yaw": row["rotation_yaw"],
                    "velocity_x": row["velocity_x"],
                    "velocity_y": row["velocity_y"],
                    "velocity_z": row["velocity_z"],
                    "updated_at": row["last_updated"],
                }

                # Calcular velocidade total
                vx = row["velocity_x"] or 0
                vy = row["velocity_y"] or 0
                vz = row["velocity_z"] or 0
                speed = (vx**2 + vy**2 + vz**2) ** 0.5
                spawn["movement"]["speed"] = round(speed, 2)
                spawn["movement"]["is_moving"] = speed > 0.1

                players_gps[steam_id]["gps_data"]["spawns"].append(spawn)

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "count": len(players_gps),
                        "players": list(players_gps.values()),
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            )

    except Exception as e:
        logger.error(f"Erro ao obter GPS dos jogadores online: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


