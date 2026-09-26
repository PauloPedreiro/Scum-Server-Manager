"""
Blueprint: squads
"""
from typing import Dict, Any, List, Optional, Tuple
from core.database.connector import DatabaseConnector

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac
from functools import wraps
from core.auth.decorators import require_auth, require_admin
import sqlite3
from .helpers import _get_ssm_database_path, _fetch_functional_vehicle_counts_by_steam_id


squads_bp = Blueprint('squads', __name__)

@squads_bp.route("/api/squads", methods=["GET"])
def get_all_squads():
    """Listar todos os squads disponíveis"""
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

        with DatabaseConnector.get_connection(db_path, timeout=30.0, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, squad_id, name, message, information, emblem, score, member_limit,
                       member_count, flag_count, flag_ids, last_member_login_time, last_member_logout_time,
                       rank_position, snapshot_at
                FROM squad_snapshot
                ORDER BY COALESCE(rank_position, 999999), score DESC, squad_id ASC
                """
            )
            rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT sm.squad_id AS squad_id,
                       COUNT(v.entity_id) AS total
                FROM (
                    SELECT DISTINCT squad_id, player_steam_id
                    FROM squad_member_snapshot
                    WHERE player_steam_id IS NOT NULL
                      AND player_steam_id != ''
                ) AS sm
                JOIN vehicle_current_ownership v
                  ON v.steam_id = sm.player_steam_id
                WHERE v.is_vehicle_functional = 1
                  AND v.status = 0
                GROUP BY sm.squad_id
                """
            )
            vehicle_totals_by_squad = {
                r["squad_id"]: (r["total"] or 0) for r in cursor.fetchall()
            }

        squads = []
        for row in rows:
            squad_id = row["squad_id"]
            squads.append(
                {
                    "snapshot_id": row["id"],
                    "squad_id": squad_id,
                    "name": row["name"],
                    "message": row["message"],
                    "information": row["information"],
                    "emblem": row["emblem"],
                    "score": row["score"],
                    "member_limit": row["member_limit"],
                    "member_count": row["member_count"],
                    "flag_count": row["flag_count"],
                    "flag_ids": row["flag_ids"],  # IDs das flags separados por vírgula
                    "last_member_login_time": row["last_member_login_time"],
                    "last_member_logout_time": row["last_member_logout_time"],
                    "rank_position": row["rank_position"],
                    "snapshot_at": row["snapshot_at"],
                    "squad_total_vehicles": vehicle_totals_by_squad.get(squad_id, 0),
                }
            )

        return jsonify(
            {"success": True, "data": {"squads": squads, "total": len(squads)}}
        )

    except Exception as e:
        logger.error(f"Erro ao listar squads: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@squads_bp.route("/api/squads/ranking", methods=["GET"])
def get_squad_ranking():
    """Listar squads com ranking de pontuação"""
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

        limit = request.args.get("limit", default=50, type=int)
        offset = request.args.get("offset", default=0, type=int)
        min_score = request.args.get("min_score", type=float)
        name_filter = request.args.get("name", type=str)

        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            filters = []
            params: List[Any] = []

            if min_score is not None:
                filters.append("score >= ?")
                params.append(min_score)

            if name_filter:
                filters.append("LOWER(name) LIKE ?")
                params.append(f"%{name_filter.lower()}%")

            where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

            cursor.execute(
                f"SELECT COUNT(*) AS total FROM squad_snapshot {where_clause}", params
            )
            total = cursor.fetchone()["total"]

            query = (
                "SELECT id, squad_id, name, message, information, emblem, score, member_limit, "
                "member_count, flag_count, flag_ids, last_member_login_time, last_member_logout_time, rank_position, snapshot_at "
                f"FROM squad_snapshot {where_clause} "
                "ORDER BY COALESCE(rank_position, 999999), score DESC, squad_id ASC"
            )

            query_params = list(params)
            if limit is not None and limit > 0:
                query += " LIMIT ? OFFSET ?"
                query_params.extend([limit, max(offset, 0)])
            elif offset > 0:
                query += " LIMIT -1 OFFSET ?"
                query_params.append(offset)

            cursor.execute(query, query_params)
            rows = cursor.fetchall()

            squads = []
            for row in rows:
                squads.append(
                    {
                        "snapshot_id": row["id"],
                        "squad_id": row["squad_id"],
                        "name": row["name"],
                        "message": row["message"],
                        "information": row["information"],
                        "emblem": row["emblem"],
                        "score": row["score"],
                        "member_limit": row["member_limit"],
                        "member_count": row["member_count"],
                        "flag_count": row["flag_count"],
                        "flag_ids": row["flag_ids"],  # IDs das flags separados por vírgula
                        "last_member_login_time": row["last_member_login_time"],
                        "last_member_logout_time": row["last_member_logout_time"],
                        "rank_position": row["rank_position"],
                        "snapshot_at": row["snapshot_at"],
                    }
                )

        return jsonify(
            {
                "success": True,
                "data": {
                    "squads": squads,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "count": len(squads),
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao listar ranking de squads: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@squads_bp.route("/api/squads/<int:squad_id>", methods=["GET"])
def get_squad_detail(squad_id: int):
    """Obter detalhes de um squad com seus membros"""
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

        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, squad_id, name, message, information, emblem, score, member_limit,
                       member_count, flag_count, flag_ids, last_member_login_time, last_member_logout_time,
                       rank_position, snapshot_at
                FROM squad_snapshot
                WHERE squad_id = ?
                ORDER BY snapshot_at DESC
                LIMIT 1
                """,
                (squad_id,),
            )

            squad_row = cursor.fetchone()
            if not squad_row:
                return (
                    jsonify(
                        {"success": False, "error": f"Squad {squad_id} não encontrado"}
                    ),
                    404,
                )

            cursor.execute(
                """
                SELECT id, member_id, user_profile_id, player_steam_id, player_name, rank, fame_points,
                       last_login_time, last_logout_time, play_time
                FROM squad_member_snapshot
                WHERE squad_id = ?
                ORDER BY rank ASC, player_name COLLATE NOCASE ASC
                """,
                (squad_id,),
            )

            member_rows = cursor.fetchall()

        members = []
        for row in member_rows:
            members.append(
                {
                    "snapshot_member_id": row["id"],
                    "squad_member_id": row["member_id"],
                    "user_profile_id": row["user_profile_id"],
                    "steam_id": row["player_steam_id"],
                    "name": row["player_name"],
                    "rank": row["rank"],
                    "fame_points": row["fame_points"],
                    "last_login_time": row["last_login_time"],
                    "last_logout_time": row["last_logout_time"],
                    "play_time": row["play_time"],
                }
            )

        squad_data = {
            "snapshot_id": squad_row["id"],
            "squad_id": squad_row["squad_id"],
            "name": squad_row["name"],
            "message": squad_row["message"],
            "information": squad_row["information"],
            "emblem": squad_row["emblem"],
            "score": squad_row["score"],
            "member_limit": squad_row["member_limit"],
            "member_count": squad_row["member_count"],
            "flag_count": squad_row["flag_count"],
            "flag_ids": squad_row["flag_ids"],  # IDs das flags separados por vírgula
            "last_member_login_time": squad_row["last_member_login_time"],
            "last_member_logout_time": squad_row["last_member_logout_time"],
            "rank_position": squad_row["rank_position"],
            "snapshot_at": squad_row["snapshot_at"],
            "members": members,
        }

        return jsonify({"success": True, "data": squad_data})

    except Exception as e:
        logger.error(f"Erro ao detalhar squad {squad_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@squads_bp.route("/api/squads/<int:squad_id>/members", methods=["GET"])
def get_squad_members(squad_id: int):
    """Listar membros de um squad com paginação"""
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

        limit = request.args.get("limit", default=50, type=int)
        offset = request.args.get("offset", default=0, type=int)

        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name FROM squad_snapshot WHERE squad_id = ? LIMIT 1",
                (squad_id,),
            )
            squad_row = cursor.fetchone()
            if not squad_row:
                return (
                    jsonify(
                        {"success": False, "error": f"Squad {squad_id} não encontrado"}
                    ),
                    404,
                )

            cursor.execute(
                "SELECT COUNT(*) AS total FROM squad_member_snapshot WHERE squad_id = ?",
                (squad_id,),
            )
            total = cursor.fetchone()["total"]

            query = (
                "SELECT id, member_id, user_profile_id, player_steam_id, player_name, rank, fame_points, "
                "last_login_time, last_logout_time, play_time "
                "FROM squad_member_snapshot "
                "WHERE squad_id = ? "
                "ORDER BY rank ASC, player_name COLLATE NOCASE ASC "
                "LIMIT ? OFFSET ?"
            )

            cursor.execute(query, (squad_id, max(limit or 0, 0), max(offset, 0)))
            rows = cursor.fetchall()

            cursor.execute(
                "SELECT DISTINCT player_steam_id FROM squad_member_snapshot WHERE squad_id = ?",
                (squad_id,),
            )
            all_member_steam_ids = [
                r["player_steam_id"] for r in cursor.fetchall() if r["player_steam_id"]
            ]

        members = []
        page_steam_ids = [row["player_steam_id"] for row in rows if row["player_steam_id"]]
        vehicle_counts_page = _fetch_functional_vehicle_counts_by_steam_id(
            db_path, page_steam_ids
        )
        vehicle_counts_all = _fetch_functional_vehicle_counts_by_steam_id(
            db_path, all_member_steam_ids
        )
        squad_total_vehicles = sum(vehicle_counts_all.values())
        for row in rows:
            steam_id = row["player_steam_id"]
            members.append(
                {
                    "snapshot_member_id": row["id"],
                    "squad_member_id": row["member_id"],
                    "user_profile_id": row["user_profile_id"],
                    "steam_id": steam_id,
                    "name": row["player_name"],
                    "rank": row["rank"],
                    "fame_points": row["fame_points"],
                    "last_login_time": row["last_login_time"],
                    "last_logout_time": row["last_logout_time"],
                    "play_time": row["play_time"],
                    "vehicle_count": vehicle_counts_page.get(steam_id, 0),
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "squad_id": squad_id,
                    "squad_name": squad_row["name"],
                    "members": members,
                    "squad_total_vehicles": squad_total_vehicles,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "count": len(members),
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao listar membros do squad {squad_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@squads_bp.route("/api/squads/sync/status", methods=["GET"])
def get_squad_sync_status():
    """Obter status do serviço de sincronização de squads"""
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
        if not squad_sync_service:
            return (
                jsonify(
                    {"success": False, "error": "SquadSyncService não inicializado"}
                ),
                500,
            )

        status = squad_sync_service.get_status()

        return jsonify({"success": True, "data": status, "timestamp": time.time()})

    except Exception as e:
        logger.error(f"Erro ao obter status do serviço de squads: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@squads_bp.route("/api/squads/sync/start", methods=["POST"])
def start_squad_sync():
    """Iniciar serviço de sincronização de squads"""
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
        if not squad_sync_service:
            return (
                jsonify(
                    {"success": False, "error": "SquadSyncService não inicializado"}
                ),
                500,
            )

        result = squad_sync_service.start()

        return jsonify({"success": True, "data": result, "timestamp": time.time()})

    except Exception as e:
        logger.error(f"Erro ao iniciar serviço de squads: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@squads_bp.route("/api/squads/sync/stop", methods=["POST"])
def stop_squad_sync():
    """Parar serviço de sincronização de squads"""
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
        if not squad_sync_service:
            return (
                jsonify(
                    {"success": False, "error": "SquadSyncService não inicializado"}
                ),
                500,
            )

        result = squad_sync_service.stop()

        return jsonify({"success": True, "data": result, "timestamp": time.time()})

    except Exception as e:
        logger.error(f"Erro ao parar serviço de squads: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@squads_bp.route("/api/squads/sync/run-now", methods=["POST"])
def run_squad_sync_now():
    """Executar sincronização de squads manualmente"""
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
        if not squad_sync_service:
            return (
                jsonify(
                    {"success": False, "error": "SquadSyncService não inicializado"}
                ),
                500,
            )

        result = squad_sync_service.sync_once()

        return jsonify({"success": True, "data": result, "timestamp": time.time()})

    except Exception as e:
        logger.error(f"Erro ao executar sincronização de squads: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


