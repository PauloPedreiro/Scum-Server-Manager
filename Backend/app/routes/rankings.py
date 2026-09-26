"""
Blueprint: rankings
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
from .helpers import _get_ssm_database_path, _get_scum_database_path


rankings_bp = Blueprint('rankings', __name__)

@rankings_bp.route("/api/rankings", methods=["GET"])
def get_rankings():
    """Obter rankings por categoria"""
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
        category = request.args.get("category", "kills")
        limit = request.args.get("limit", type=int) or 20
        offset = request.args.get("offset", type=int) or 0

        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        if offset < 0:
            offset = 0

        db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        # Mapeamento de categorias para colunas
        category_map = {
            "kills": "kills",
            "deaths": "deaths",
            "kdr": "kdr",
            "longest_shot": "longest_shot_distance",
            "lockpick_basic_rate": "lockpick_basic_rate",
            "lockpick_medium_rate": "lockpick_medium_rate",
            "lockpick_advanced_rate": "lockpick_advanced_rate",
            "lockpick_veryeasy_rate": "lockpick_veryeasy_rate",
            "lockpick_diallock_rate": "lockpick_diallock_rate",
            "suicides": "suicides",
            "defecation": "highest_defecation",
            "vehicles": "vehicles_destroyed",
            "hunting": "animals_killed",
            "melee": "players_knocked_out",
            "headshots": "headshots",
            "survival_time": "minutes_survived",
            "overdoses": "overdoses",
            "weight": "highest_weight_carried",
            "fame": "total_fame",
        }

        order_column = category_map.get(category)
        if not order_column:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Categoria inválida. Categorias disponíveis: {", ".join(category_map.keys())}',
                    }
                ),
                400,
            )

        with DatabaseConnector.get_connection(db_path, timeout=30.0, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Contar total
            cursor.execute(f"SELECT COUNT(*) FROM rankings WHERE {order_column} > 0")
            total = cursor.fetchone()[0]

            # Obter rankings ordenados
            cursor.execute(
                f"""
                SELECT steam_id, player_name,
                       kills, deaths, kdr,
                       longest_shot_distance, longest_shot_weapon, longest_shot_timestamp,
                       suicides,
                       lockpick_basic_success, lockpick_basic_fails, lockpick_basic_total, lockpick_basic_rate,
                       lockpick_medium_success, lockpick_medium_fails, lockpick_medium_total, lockpick_medium_rate,
                       lockpick_advanced_success, lockpick_advanced_fails, lockpick_advanced_total, lockpick_advanced_rate,
                       lockpick_veryeasy_success, lockpick_veryeasy_fails, lockpick_veryeasy_total, lockpick_veryeasy_rate,
                       lockpick_diallock_success, lockpick_diallock_fails, lockpick_diallock_total, lockpick_diallock_rate,
                       lockpick_other_success, lockpick_other_fails, lockpick_other_total, lockpick_other_rate,
                       vehicles_destroyed,
                       highest_defecation, animals_killed, players_knocked_out,
                       headshots, minutes_survived, overdoses, highest_weight_carried,
                       total_fame,
                       last_updated
                FROM rankings
                WHERE {order_column} > 0
                ORDER BY {order_column} DESC, steam_id ASC
                LIMIT ? OFFSET ?
            """,
                (limit, offset),
            )

            rows = cursor.fetchall()

        rankings = []
        for idx, row in enumerate(rows, start=offset + 1):
            rankings.append(
                {
                    "rank": idx,
                    "steam_id": row["steam_id"],
                    "player_name": row["player_name"],
                    "value": row[order_column],
                    "kills": row["kills"],
                    "deaths": row["deaths"],
                    "kdr": row["kdr"],
                    "longest_shot_distance": row["longest_shot_distance"],
                    "longest_shot_weapon": row["longest_shot_weapon"],
                    "suicides": row["suicides"],
                    "lockpick_by_type": {
                        "basic": {
                            "success": row["lockpick_basic_success"],
                            "fails": row["lockpick_basic_fails"],
                            "total": row["lockpick_basic_total"],
                            "rate": row["lockpick_basic_rate"],
                        },
                        "medium": {
                            "success": row["lockpick_medium_success"],
                            "fails": row["lockpick_medium_fails"],
                            "total": row["lockpick_medium_total"],
                            "rate": row["lockpick_medium_rate"],
                        },
                        "advanced": {
                            "success": row["lockpick_advanced_success"],
                            "fails": row["lockpick_advanced_fails"],
                            "total": row["lockpick_advanced_total"],
                            "rate": row["lockpick_advanced_rate"],
                        },
                        "veryeasy": {
                            "success": row["lockpick_veryeasy_success"],
                            "fails": row["lockpick_veryeasy_fails"],
                            "total": row["lockpick_veryeasy_total"],
                            "rate": row["lockpick_veryeasy_rate"],
                        },
                        "diallock": {
                            "success": row["lockpick_diallock_success"],
                            "fails": row["lockpick_diallock_fails"],
                            "total": row["lockpick_diallock_total"],
                            "rate": row["lockpick_diallock_rate"],
                        },
                        "other": {
                            "success": row["lockpick_other_success"],
                            "fails": row["lockpick_other_fails"],
                            "total": row["lockpick_other_total"],
                            "rate": row["lockpick_other_rate"],
                        },
                    },
                    "vehicles_destroyed": row["vehicles_destroyed"],
                    "highest_defecation": row["highest_defecation"],
                    "animals_killed": row["animals_killed"],
                    "players_knocked_out": row["players_knocked_out"],
                    "headshots": row["headshots"],
                    "minutes_survived": row["minutes_survived"],
                    "overdoses": row["overdoses"],
                    "highest_weight_carried": row["highest_weight_carried"],
                    "total_fame": (
                        row["total_fame"] if row["total_fame"] is not None else 0.0
                    ),
                    "last_updated": row["last_updated"],
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "category": category,
                    "order_column": order_column,
                    "rankings": rankings,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter rankings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@rankings_bp.route("/api/rankings/player/<steam_id>", methods=["GET"])
def get_player_ranking(steam_id: str):
    """Obter ranking completo de um jogador específico"""
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
                SELECT steam_id, player_name,
                       kills, deaths, kdr,
                       longest_shot_distance, longest_shot_weapon, longest_shot_timestamp,
                       suicides,
                       lockpick_basic_success, lockpick_basic_fails, lockpick_basic_total, lockpick_basic_rate,
                       lockpick_medium_success, lockpick_medium_fails, lockpick_medium_total, lockpick_medium_rate,
                       lockpick_advanced_success, lockpick_advanced_fails, lockpick_advanced_total, lockpick_advanced_rate,
                       lockpick_veryeasy_success, lockpick_veryeasy_fails, lockpick_veryeasy_total, lockpick_veryeasy_rate,
                       lockpick_diallock_success, lockpick_diallock_fails, lockpick_diallock_total, lockpick_diallock_rate,
                       lockpick_other_success, lockpick_other_fails, lockpick_other_total, lockpick_other_rate,
                       vehicles_destroyed,
                       highest_defecation, animals_killed, players_knocked_out,
                       headshots, minutes_survived, overdoses, highest_weight_carried,
                       total_fame,
                       last_updated
                FROM rankings
                WHERE steam_id = ?
            """,
                (steam_id,),
            )

            row = cursor.fetchone()

        if not row:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Jogador {steam_id} não encontrado nos rankings",
                    }
                ),
                404,
            )

        ranking_data = {
            "steam_id": row["steam_id"],
            "player_name": row["player_name"],
            "kills": row["kills"],
            "deaths": row["deaths"],
            "kdr": row["kdr"],
            "longest_shot_distance": row["longest_shot_distance"],
            "longest_shot_weapon": row["longest_shot_weapon"],
            "longest_shot_timestamp": row["longest_shot_timestamp"],
            "suicides": row["suicides"],
            "lockpick_by_type": {
                "basic": {
                    "success": row["lockpick_basic_success"],
                    "fails": row["lockpick_basic_fails"],
                    "total": row["lockpick_basic_total"],
                    "rate": row["lockpick_basic_rate"],
                },
                "medium": {
                    "success": row["lockpick_medium_success"],
                    "fails": row["lockpick_medium_fails"],
                    "total": row["lockpick_medium_total"],
                    "rate": row["lockpick_medium_rate"],
                },
                "advanced": {
                    "success": row["lockpick_advanced_success"],
                    "fails": row["lockpick_advanced_fails"],
                    "total": row["lockpick_advanced_total"],
                    "rate": row["lockpick_advanced_rate"],
                },
                "veryeasy": {
                    "success": row["lockpick_veryeasy_success"],
                    "fails": row["lockpick_veryeasy_fails"],
                    "total": row["lockpick_veryeasy_total"],
                    "rate": row["lockpick_veryeasy_rate"],
                },
                "diallock": {
                    "success": row["lockpick_diallock_success"],
                    "fails": row["lockpick_diallock_fails"],
                    "total": row["lockpick_diallock_total"],
                    "rate": row["lockpick_diallock_rate"],
                },
                "other": {
                    "success": row["lockpick_other_success"],
                    "fails": row["lockpick_other_fails"],
                    "total": row["lockpick_other_total"],
                    "rate": row["lockpick_other_rate"],
                },
            },
            "vehicles_destroyed": row["vehicles_destroyed"],
            "highest_defecation": row["highest_defecation"],
            "animals_killed": row["animals_killed"],
            "players_knocked_out": row["players_knocked_out"],
            "headshots": row["headshots"],
            "minutes_survived": row["minutes_survived"],
            "overdoses": row["overdoses"],
            "highest_weight_carried": row["highest_weight_carried"],
            "total_fame": row["total_fame"] if row["total_fame"] is not None else 0.0,
            "last_updated": row["last_updated"],
        }

        return jsonify(
            {"success": True, "data": ranking_data, "timestamp": time.time()}
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter ranking do jogador: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@rankings_bp.route("/api/rankings/list", methods=["GET"])
def get_rankings_list():
    """Listar todos os jogadores com rankings completos (para tabela de rankings)"""
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
        # Obter parâmetros
        limit = request.args.get("limit", default=50, type=int)
        offset = request.args.get("offset", default=0, type=int)
        sort_by = request.args.get("sort_by", default="kills", type=str)
        sort_order = request.args.get("sort_order", default="desc", type=str)
        search = request.args.get("search", default="", type=str).strip()

        # Validar limit
        if limit is None or limit <= 0:
            limit = 50
        elif limit > 200:
            limit = 200

        # Validar offset
        if offset is None or offset < 0:
            offset = 0

        # Validar sort_order
        if sort_order not in ["asc", "desc"]:
            sort_order = "desc"

        # Mapeamento de campos ordenáveis
        sort_column_map = {
            "kills": "kills",
            "deaths": "deaths",
            "kdr": "kdr",
            "longest_shot": "longest_shot_distance",
            "longest_shot_distance": "longest_shot_distance",
            "suicides": "suicides",
            "lockpick_basic_rate": "lockpick_basic_rate",
            "lockpick_medium_rate": "lockpick_medium_rate",
            "lockpick_advanced_rate": "lockpick_advanced_rate",
            "lockpick_veryeasy_rate": "lockpick_veryeasy_rate",
            "lockpick_diallock_rate": "lockpick_diallock_rate",
            "vehicles_destroyed": "vehicles_destroyed",
            "highest_defecation": "highest_defecation",
            "defecation": "highest_defecation",
            "animals_killed": "animals_killed",
            "hunting": "animals_killed",
            "players_knocked_out": "players_knocked_out",
            "melee": "players_knocked_out",
            "headshots": "headshots",
            "minutes_survived": "minutes_survived",
            "survival_time": "minutes_survived",
            "overdoses": "overdoses",
            "highest_weight_carried": "highest_weight_carried",
            "weight": "highest_weight_carried",
            "total_fame": "total_fame",
            "fame": "total_fame",
            "player_name": "player_name",
            "last_updated": "last_updated",
        }

        # Validar sort_by
        order_column = sort_column_map.get(sort_by.lower())
        if not order_column:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Campo de ordenação inválido: {sort_by}. Campos disponíveis: {", ".join(sort_column_map.keys())}',
                    }
                ),
                400,
            )

        order_direction = "DESC" if sort_order == "desc" else "ASC"

        db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Construir query base
            base_query = """
                SELECT steam_id, player_name,
                       kills, deaths, kdr,
                       longest_shot_distance, longest_shot_weapon, longest_shot_timestamp,
                       suicides,
                       lockpick_basic_success, lockpick_basic_fails, lockpick_basic_total, lockpick_basic_rate,
                       lockpick_medium_success, lockpick_medium_fails, lockpick_medium_total, lockpick_medium_rate,
                       lockpick_advanced_success, lockpick_advanced_fails, lockpick_advanced_total, lockpick_advanced_rate,
                       lockpick_veryeasy_success, lockpick_veryeasy_fails, lockpick_veryeasy_total, lockpick_veryeasy_rate,
                       lockpick_diallock_success, lockpick_diallock_fails, lockpick_diallock_total, lockpick_diallock_rate,
                       lockpick_other_success, lockpick_other_fails, lockpick_other_total, lockpick_other_rate,
                       vehicles_destroyed,
                       highest_defecation, animals_killed, players_knocked_out,
                       headshots, minutes_survived, overdoses, highest_weight_carried,
                       total_fame,
                       last_updated
                FROM rankings
            """

            # Adicionar filtro de busca se fornecido
            where_clause = ""
            params = []

            if search:
                where_clause = "WHERE player_name LIKE ?"
                params.append(f"%{search}%")

            # Contar total
            count_query = f"SELECT COUNT(*) FROM rankings {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # Query de seleção com ordenação
            # Para player_name, usar COLLATE NOCASE para ordenação case-insensitive
            if order_column == "player_name":
                order_by = f"ORDER BY player_name COLLATE NOCASE {order_direction}, steam_id ASC"
            else:
                order_by = f"ORDER BY {order_column} {order_direction}, steam_id ASC"

            query = f"{base_query} {where_clause} {order_by} LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

        # Montar resposta
        players = []
        for idx, row in enumerate(rows, start=offset + 1):
            players.append(
                {
                    "rank": idx,
                    "steam_id": row["steam_id"],
                    "player_name": row["player_name"],
                    # Combat Stats
                    "kills": row["kills"],
                    "deaths": row["deaths"],
                    "kdr": row["kdr"],
                    "longest_shot": {
                        "distance": row["longest_shot_distance"] or 0.0,
                        "weapon": row["longest_shot_weapon"],
                        "timestamp": row["longest_shot_timestamp"],
                    },
                    "suicides": row["suicides"],
                    "headshots": row["headshots"],
                    # Lockpicking Stats
                    "lockpicking": {
                        "basic": {
                            "success": row["lockpick_basic_success"],
                            "fails": row["lockpick_basic_fails"],
                            "total": row["lockpick_basic_total"],
                            "rate": row["lockpick_basic_rate"],
                        },
                        "medium": {
                            "success": row["lockpick_medium_success"],
                            "fails": row["lockpick_medium_fails"],
                            "total": row["lockpick_medium_total"],
                            "rate": row["lockpick_medium_rate"],
                        },
                        "advanced": {
                            "success": row["lockpick_advanced_success"],
                            "fails": row["lockpick_advanced_fails"],
                            "total": row["lockpick_advanced_total"],
                            "rate": row["lockpick_advanced_rate"],
                        },
                        "veryeasy": {
                            "success": row["lockpick_veryeasy_success"],
                            "fails": row["lockpick_veryeasy_fails"],
                            "total": row["lockpick_veryeasy_total"],
                            "rate": row["lockpick_veryeasy_rate"],
                        },
                        "diallock": {
                            "success": row["lockpick_diallock_success"],
                            "fails": row["lockpick_diallock_fails"],
                            "total": row["lockpick_diallock_total"],
                            "rate": row["lockpick_diallock_rate"],
                        },
                        "other": {
                            "success": row["lockpick_other_success"],
                            "fails": row["lockpick_other_fails"],
                            "total": row["lockpick_other_total"],
                            "rate": row["lockpick_other_rate"],
                        },
                    },
                    # Survival Stats
                    "vehicles_destroyed": row["vehicles_destroyed"],
                    "highest_defecation": row["highest_defecation"],
                    "animals_killed": row["animals_killed"],
                    "players_knocked_out": row["players_knocked_out"],
                    "minutes_survived": row["minutes_survived"],
                    "overdoses": row["overdoses"],
                    "highest_weight_carried": row["highest_weight_carried"],
                    "total_fame": (
                        row["total_fame"] if row["total_fame"] is not None else 0.0
                    ),
                    # Metadata
                    "last_updated": row["last_updated"],
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "players": players,
                    "pagination": {
                        "total": total,
                        "limit": limit,
                        "offset": offset,
                        "count": len(players),
                        "has_more": offset + len(players) < total,
                    },
                    "sorting": {
                        "sort_by": sort_by,
                        "sort_order": sort_order,
                        "order_column": order_column,
                    },
                    "search": search if search else None,
                },
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao listar rankings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@rankings_bp.route("/api/rankings/update", methods=["POST"])
def update_rankings():
    """Atualizar rankings manualmente"""
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
        if rankings_update_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "RankingsUpdateService não inicializado",
                    }
                ),
                500,
            )

        result = rankings_update_service.update_once()

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except Exception as e:
        if logger:
            logger.error(f"Erro ao atualizar rankings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@rankings_bp.route("/api/rankings/status", methods=["GET"])
def get_rankings_status():
    """Obter status do serviço de atualização de rankings"""
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
        if rankings_update_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "RankingsUpdateService não inicializado",
                    }
                ),
                500,
            )

        status = rankings_update_service.get_status()

        return jsonify({"success": True, "data": status, "timestamp": time.time()})

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter status dos rankings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@rankings_bp.route("/api/rankings/lockpicking/send", methods=["POST"])
def send_lockpicking_rankings():
    """Enviar rankings de lockpicking para Discord manualmente"""
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
        if lockpicking_ranking_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "LockpickingRankingService não inicializado",
                    }
                ),
                500,
            )

        result = lockpicking_ranking_service.send_rankings()

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except Exception as e:
        if logger:
            logger.error(f"Erro ao enviar rankings de lockpicking: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@rankings_bp.route("/api/rankings/lockpicking/status", methods=["GET"])
def get_lockpicking_rankings_status():
    """Obter status do serviço de rankings de lockpicking"""
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
        if lockpicking_ranking_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "LockpickingRankingService não inicializado",
                    }
                ),
                500,
            )

        status = lockpicking_ranking_service.get_status()

        return jsonify({"success": True, "data": status, "timestamp": time.time()})

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter status dos rankings de lockpicking: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@rankings_bp.route("/api/rankings/kills/send", methods=["POST"])
def send_kills_rankings():
    """Enviar rankings de kills para Discord manualmente"""
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
        if kills_ranking_service is None:
            return (
                jsonify(
                    {"success": False, "error": "KillsRankingService não inicializado"}
                ),
                500,
            )

        result = kills_ranking_service.send_rankings()

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except Exception as e:
        if logger:
            logger.error(f"Erro ao enviar rankings de kills: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@rankings_bp.route("/api/rankings/kills/status", methods=["GET"])
def get_kills_rankings_status():
    """Obter status do serviço de rankings de kills"""
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
        if kills_ranking_service is None:
            return (
                jsonify(
                    {"success": False, "error": "KillsRankingService não inicializado"}
                ),
                500,
            )

        status = kills_ranking_service.get_status()

        return jsonify({"success": True, "data": status, "timestamp": time.time()})

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter status dos rankings de kills: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@rankings_bp.route("/api/rankings/snipers/send", methods=["POST"])
def send_snipers_rankings():
    """Enviar ranking de snipers para Discord manualmente"""
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
        target_service = snipers_ranking_service or kills_ranking_service
        if target_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Serviço de rankings de combate não inicializado",
                    }
                ),
                500,
            )

        result = target_service.send_rankings()

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except Exception as e:
        if logger:
            logger.error(f"Erro ao enviar ranking de snipers: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@rankings_bp.route("/api/rankings/snipers/status", methods=["GET"])
def get_snipers_rankings_status():
    """Obter status do serviço de ranking de snipers"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    try:
        target_service = snipers_ranking_service or kills_ranking_service
        if target_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Serviço de rankings de combate não inicializado",
                    }
                ),
                500,
            )

        status = target_service.get_status()

        return jsonify({"success": True, "data": status, "timestamp": time.time()})

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter status do ranking de snipers: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


