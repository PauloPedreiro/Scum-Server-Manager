"""
Blueprint: players
"""
from core.database.connector import DatabaseConnector

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac
from functools import wraps
from core.auth.decorators import require_auth, require_admin
from utils.scum_db_helper import scum_db_readonly_connection_strict
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import sqlite3
from .helpers import (
    _get_ssm_database_path,
    _get_scum_database_path,
    _normalize_player_sort_params,
    _get_sorted_player_rows,
    _fetch_vehicle_statistics
)

players_bp = Blueprint('players', __name__)

@players_bp.route("/api/players/online", methods=["GET"])
def get_players_online():
    """Obter jogadores online"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        if not online_monitor:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Monitor de jogadores online não inicializado",
                    }
                ),
                500,
            )

        # Forçar verificação imediata se solicitado
        force_check = request.args.get("force_check", "false").lower() == "true"

        if force_check:
            result = online_monitor.force_check()
        else:
            result = online_monitor.get_online_players()

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"Erro ao obter jogadores online: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route("/api/players/online/list", methods=["GET"])
def get_players_online_list():
    """Obter lista detalhada de jogadores online"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        if not online_monitor:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Monitor de jogadores online não inicializado",
                    }
                ),
                500,
            )

        players_list = online_monitor.get_online_players_list()

        return jsonify(
            {
                "success": True,
                "data": {
                    "players": players_list,
                    "count": len(players_list),
                    "timestamp": datetime.now().isoformat(),
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter lista de jogadores online: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route("/api/players/online/stats", methods=["GET"])
def get_players_online_stats():
    """Obter estatísticas de jogadores online"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        if not log_processor:
            return (
                jsonify(
                    {"success": False, "error": "Processador de logs não inicializado"}
                ),
                500,
            )

        stats = log_processor.db_manager.get_players_online_stats()

        return jsonify({"success": True, "data": stats})

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de jogadores online: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route("/api/players/online/check", methods=["POST"])
def force_check_online_players():
    """Forçar verificação de jogadores online"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        if not online_monitor:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Monitor de jogadores online não inicializado",
                    }
                ),
                500,
            )

        result = online_monitor.force_check()

        return jsonify(
            {
                "success": True,
                "message": "Verificação forçada concluída",
                "data": result,
            }
        )

    except Exception as e:
        logger.error(f"Erro ao forçar verificação de jogadores online: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route("/api/players", methods=["GET"])
def get_all_players():
    """Listar todos os players cadastrados na tabela players"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        # Obter parâmetros de paginação
        limit = request.args.get("limit", default=100, type=int)
        offset = request.args.get("offset", default=0, type=int)

        if limit is None or limit <= 0:
            limit = 100
        elif limit > 1000:
            limit = 1000

        if offset is None or offset < 0:
            offset = 0

        sort_by_param = request.args.get("sort_by")
        sort_order_param = request.args.get("sort_order")
        search_query = request.args.get("q")

        try:
            sort_by, sort_order = _normalize_player_sort_params(
                sort_by_param, sort_order_param
            )
        except ValueError as exc:
            return jsonify({"success": False, "error": str(exc)}), 400

        rows, total_count, _ = _get_sorted_player_rows(
            limit, offset, sort_by, sort_order, search_query
        )

        players: List[Dict[str, Any]] = []
        for row in rows:
            players.append(
                {
                    "steam_id": row["steam_id"],
                    "player_name": row["player_name"],
                    "player_id": row["player_id"],
                    "first_seen": row["first_seen"],
                    "last_seen": row["last_seen"],
                    "total_sessions": row["total_sessions"],
                    "total_playtime": row["total_playtime"],
                    "is_new_player": bool(row["is_new_player"]),
                    "notification_sent": bool(row["notification_sent"]),
                    "permissao": row["permissao"],
                    "created_at": row["created_at"],
                    "balance": int(row["balance"]) if "balance" in row.keys() else 0,
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "players": players,
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "count": len(players),
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao listar players: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route("/api/players/fame", methods=["GET"])
def get_players_fame():
    """Listar todos os jogadores com seus totais de fama"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        # Obter parâmetros de paginação
        limit = request.args.get("limit", default=100, type=int)
        offset = request.args.get("offset", default=0, type=int)
        sort_order = request.args.get("sort_order", default="desc", type=str)

        if limit is None or limit <= 0:
            limit = 100
        elif limit > 1000:
            limit = 1000

        if offset is None or offset < 0:
            offset = 0

        if sort_order not in ["asc", "desc"]:
            sort_order = "desc"

        order_direction = "DESC" if sort_order == "desc" else "ASC"

        with DatabaseConnector.get_connection(db_path, timeout=30.0, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Contar total
            cursor.execute("SELECT COUNT(*) FROM player_fame_totals")
            total_count = cursor.fetchone()[0]

            # Obter jogadores ordenados por fama
            cursor.execute(
                f"""
                SELECT steam_id, player_name, total_fame, last_updated
                FROM player_fame_totals
                ORDER BY total_fame {order_direction}, player_name ASC
                LIMIT ? OFFSET ?
            """,
                (limit, offset),
            )

            rows = cursor.fetchall()

        players_fame = []
        for row in rows:
            players_fame.append(
                {
                    "steam_id": row["steam_id"],
                    "player_name": row["player_name"],
                    "total_fame": row["total_fame"],
                    "last_updated": row["last_updated"],
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "players": players_fame,
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "count": len(players_fame),
                    "sort_order": sort_order,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao listar players com fama: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route("/api/players/<steam_id>/fame", methods=["GET"])
def get_player_fame(steam_id: str):
    """Obter total de fama de um jogador específico"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(db_path, timeout=30.0, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT steam_id, player_name, total_fame, last_updated
                FROM player_fame_totals
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
                        "error": f"Jogador {steam_id} não encontrado na tabela de fama",
                    }
                ),
                404,
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "steam_id": row["steam_id"],
                    "player_name": row["player_name"],
                    "total_fame": row["total_fame"],
                    "last_updated": row["last_updated"],
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter fama do jogador {steam_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route("/api/players/vehicles/summary", methods=["GET"])
def get_players_vehicle_summary():
    """Resumo de veículos por jogador acompanhando a paginação do /api/players"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        if not log_processor:
            return (
                jsonify({"success": False, "error": "LogProcessor não inicializado"}),
                500,
            )

        limit = request.args.get("limit", default=100, type=int)
        offset = request.args.get("offset", default=0, type=int)
        steam_id_filter = request.args.get("steam_id")
        sort_by_param = request.args.get("sort_by")
        sort_order_param = request.args.get("sort_order")

        if limit is None or limit < 1:
            limit = 100
        elif limit > 1000:
            limit = 1000

        if offset is None or offset < 0:
            offset = 0

        try:
            sort_by, sort_order = _normalize_player_sort_params(
                sort_by_param, sort_order_param
            )
        except ValueError as exc:
            return jsonify({"success": False, "error": str(exc)}), 400

        # Quando o frontend solicitar um jogador específico, ignoramos ordenação/paginação
        if steam_id_filter:
            db_path, error = _get_ssm_database_path()
            if error:
                return jsonify({"success": False, "error": error}), 500

            with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT steam_id, player_name, player_id
                    FROM players
                    WHERE LOWER(steam_id) = LOWER(?)
                    LIMIT 1
                    """,
                    (steam_id_filter,),
                )
                row = cursor.fetchone()

            if not row:
                return jsonify(
                    {
                        "success": True,
                        "data": {
                            "limit": limit,
                            "offset": offset,
                            "total": 0,
                            "count": 0,
                            "summaries": [],
                            "sort_by": sort_by,
                            "sort_order": sort_order,
                        },
                    }
                )

            vehicle_stats = _fetch_vehicle_statistics([row["steam_id"]])
            counts = vehicle_stats.get(row["steam_id"], {})
            summaries = [
                {
                    "steam_id": row["steam_id"],
                    "player_id": row["player_id"],
                    "total": counts.get("total", 0),
                    "by_status": counts.get(
                        "by_status", {"0": 0, "1": 0, "2": 0, "3": 0}
                    ),
                    "updated_at": counts.get("updated_at"),
                }
            ]

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "limit": limit,
                        "offset": offset,
                        "total": 1,
                        "count": 1,
                        "summaries": summaries,
                        "sort_by": sort_by,
                        "sort_order": sort_order,
                    },
                }
            )

        player_rows, total_players, precomputed_stats = _get_sorted_player_rows(
            limit, offset, sort_by, sort_order
        )

        if not player_rows:
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "limit": limit,
                        "offset": offset,
                        "total": total_players,
                        "count": 0,
                        "summaries": [],
                        "sort_by": sort_by,
                        "sort_order": sort_order,
                    },
                }
            )

        steam_ids = [row["steam_id"] for row in player_rows if row["steam_id"]]
        vehicle_counts = (
            precomputed_stats
            if precomputed_stats is not None
            else _fetch_vehicle_statistics(steam_ids)
        )

        summaries = []
        for row in player_rows:
            steam_id = row["steam_id"]
            counts = vehicle_counts.get(steam_id, {}) if vehicle_counts else {}
            by_status = counts.get("by_status", {"0": 0, "1": 0, "2": 0, "3": 0})

            summaries.append(
                {
                    "steam_id": steam_id,
                    "player_id": row["player_id"],
                    "total": counts.get("total", 0),
                    "by_status": by_status,
                    "updated_at": counts.get("updated_at"),
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "limit": limit,
                    "offset": offset,
                    "total": total_players,
                    "count": len(summaries),
                    "summaries": summaries,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter resumo de veículos por jogador: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route("/api/players/<steam_id>/permissao", methods=["PUT", "PATCH"])
def update_player_permissao(steam_id: str):
    """Atualizar permissão do comando /tm para um jogador na tabela players"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        # Obter dados do body
        data = request.get_json() or {}
        permissao = data.get("permissao")

        # Validar que permissao foi fornecida e é válida
        if permissao is None:
            return (
                jsonify({"success": False, "error": 'Campo "permissao" é obrigatório'}),
                400,
            )

        # Validar que permissao é 0 ou 1
        if permissao not in [0, 1, "0", "1"]:
            return (
                jsonify(
                    {"success": False, "error": 'Campo "permissao" deve ser 0 ou 1'}
                ),
                400,
            )

        # Converter para inteiro
        permissao = int(permissao)

        # Obter caminho do banco de dados do config
        if not config or not path_helper:
            return (
                jsonify({"success": False, "error": "Configuração não inicializada"}),
                500,
            )

        db_path = path_helper.get_ssm_db_path()

        if not db_path or not os.path.exists(db_path):
            return (
                jsonify({"success": False, "error": "Banco de dados não encontrado"}),
                500,
            )

        # Conectar ao banco de dados e atualizar
        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            cursor = conn.cursor()

            # Verificar se o jogador existe
            cursor.execute(
                "SELECT steam_id, player_name FROM players WHERE steam_id = ?",
                (steam_id,),
            )
            player = cursor.fetchone()

            if not player:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Jogador com steam_id {steam_id} não encontrado",
                        }
                    ),
                    404,
                )

            # Atualizar a coluna permissao
            cursor.execute(
                "UPDATE players SET permissao = ? WHERE steam_id = ?",
                (permissao, steam_id),
            )

            conn.commit()

            # Obter dados atualizados
            cursor.execute(
                """
                SELECT steam_id, player_name, player_id, first_seen, last_seen,
                       total_sessions, total_playtime, is_new_player, 
                       notification_sent, permissao, created_at
                FROM players 
                WHERE steam_id = ?
            """,
                (steam_id,),
            )

            row = cursor.fetchone()

            player_data = {
                "steam_id": row[0],
                "player_name": row[1],
                "player_id": row[2],
                "first_seen": row[3],
                "last_seen": row[4],
                "total_sessions": row[5],
                "total_playtime": row[6],
                "is_new_player": bool(row[7]),
                "notification_sent": bool(row[8]),
                "permissao": row[9],
                "created_at": row[10],
            }

        return jsonify(
            {
                "success": True,
                "message": f'Permissão do comando /tm {"ativada" if permissao == 1 else "desativada"} com sucesso',
                "data": player_data,
            }
        )

    except Exception as e:
        logger.error(f"Erro ao atualizar permissão do jogador: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route(
    "/api/players/<steam_id>/permissions/<permission_type>/activate", methods=["POST"]
)
def activate_permission(steam_id: str, permission_type: str):
    """Ativar permissão para um jogador"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        if not permission_manager:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Sistema de permissões não inicializado",
                    }
                ),
                500,
            )

        try:
            data = request.get_json() or {}
        except BadRequest as e:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "invalid_json",
                        "message": f"JSON inválido: {e}",
                    }
                ),
                400,
            )
        granted_by = data.get("granted_by", "system")
        notes = data.get("notes")

        result = permission_manager.activate_permission(
            steam_id=steam_id,
            permission_type=permission_type,
            granted_by=granted_by,
            notes=notes,
        )

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Erro ao ativar permissão: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route(
    "/api/players/<steam_id>/permissions/<permission_type>/deactivate", methods=["POST"]
)
def deactivate_permission(steam_id: str, permission_type: str):
    """Desativar permissão de um jogador"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        if not permission_manager:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Sistema de permissões não inicializado",
                    }
                ),
                500,
            )

        try:
            data = request.get_json() or {}
        except BadRequest as e:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "invalid_json",
                        "message": f"JSON inválido: {e}",
                    }
                ),
                400,
            )
        revoked_by = data.get("revoked_by", "system")
        notes = data.get("notes")

        result = permission_manager.deactivate_permission(
            steam_id=steam_id,
            permission_type=permission_type,
            revoked_by=revoked_by,
            notes=notes,
        )

        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Erro ao desativar permissão: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route("/api/players/<steam_id>/permissions", methods=["GET"])
def get_player_permissions(steam_id: str):
    """Obter permissões de um jogador"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        if not permission_manager:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Sistema de permissões não inicializado",
                    }
                ),
                500,
            )

        include_inactive = (
            request.args.get("include_inactive", "false").lower() == "true"
        )

        # Obter dados do jogador
        player = permission_manager.get_player_by_steam_id(steam_id)
        if not player:
            return jsonify({"success": False, "error": "Jogador não encontrado"}), 404

        # Obter permissões
        permissions = permission_manager.get_player_permissions(
            steam_id, include_inactive
        )

        # Contar permissões ativas e inativas
        active_count = sum(1 for p in permissions if p.get("is_active", False))
        total_count = len(permissions)

        return jsonify(
            {
                "success": True,
                "data": {
                    "steam_id": steam_id,
                    "player_name": player.get("player_name"),
                    "permissions": permissions,
                    "total_permissions": total_count,
                    "active_permissions": active_count,
                    "inactive_permissions": total_count - active_count,
                },
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter permissões do jogador: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@players_bp.route("/api/players/<steam_id>/elevated-user", methods=["POST"])
def mark_elevated_user(steam_id: str):
    """Marcar/desmarcar elevated user"""
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
    log_processor = getattr(services, 'log_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    try:
        if not elevated_users_manager:
            return (
                jsonify(
                    {"success": False, "error": "ElevatedUsersManager não inicializado"}
                ),
                500,
            )

        data = request.get_json() or {}
        elevated = data.get("elevated_user", 1)  # Padrão: 1 (adicionar)
        reason = data.get("reason")

        # Converter para boolean
        elevated_bool = bool(elevated)

        result = elevated_users_manager.mark_elevated_user(
            steam_id=steam_id, elevated=elevated_bool, reason=reason
        )

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
        logger.error(f"Erro ao marcar elevated user: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


