"""
Blueprint: chests
"""
from typing import Dict, Any, List, Optional, Tuple

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac
from functools import wraps
from core.auth.decorators import require_auth, require_admin
from .helpers import _fetch_chest_rows, _serialize_chest_row, _build_chest_player_summary, _str_to_bool


chests_bp = Blueprint('chests', __name__)

@chests_bp.route("/api/chests/player/<steam_id>", methods=["GET"])
def get_player_chests(steam_id: str):
    """Listar baús vinculados a um jogador (por Steam ID)."""
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
        steam_id = steam_id.strip()
        rows, _ = _fetch_chest_rows(filters={"steam_id": steam_id})
        chests = [_serialize_chest_row(row) for row in rows]

        type_counts: Dict[str, int] = {}
        for chest in chests:
            chest_type = (
                chest.get("chest_type") or chest.get("chest_class") or "Desconhecido"
            )
            type_counts[chest_type] = type_counts.get(chest_type, 0) + 1

        player_names = sorted(
            {c["player_name"] for c in chests if c.get("player_name")}
        )
        fake_names = sorted({c["fake_name"] for c in chests if c.get("fake_name")})

        response = {
            "steam_id": steam_id,
            "count": len(chests),
            "type_counts": type_counts,
            "player_names": player_names,
            "fake_names": fake_names,
            "chests": chests,
        }

        return jsonify(
            {
                "success": True,
                "data": response,
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter baús do jogador {steam_id}: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@chests_bp.route("/api/chests/inventory/sync/status", methods=["GET"])
@require_auth
@require_admin
def get_chest_inventory_sync_status():
    """Obter status do serviço de sincronização do inventário de baús."""
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
        if chest_inventory_sync_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "ChestInventorySyncService não inicializado",
                    }
                ),
                500,
            )

        status = chest_inventory_sync_service.get_status()
        return jsonify({"success": True, "data": status, "timestamp": time.time()})

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter status do sync de inventário de baús: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@chests_bp.route("/api/chests/inventory/sync/run-now", methods=["POST"])
@require_auth
@require_admin
def run_chest_inventory_sync_now():
    """Executar sincronização do inventário de baús imediatamente (manual)."""
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
        if chest_inventory_sync_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "ChestInventorySyncService não inicializado",
                    }
                ),
                500,
            )

        result = chest_inventory_sync_service.sync_once()
        status_code = 200 if result.get("success") else 400
        return jsonify({"success": True, "data": result, "timestamp": time.time()}), status_code

    except Exception as e:
        if logger:
            logger.error(f"Erro ao executar sync de inventário de baús: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@chests_bp.route("/api/chests", methods=["GET"])
def get_chests():
    """Listar baús do servidor com suporte a filtros básicos."""
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
        steam_id_filter = request.args.get("steam_id")
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", default=0, type=int)
        minimal = _str_to_bool(request.args.get("minimal"))
        include_summary = not _str_to_bool(request.args.get("disable_summary"))

        if limit is not None:
            if limit < 1:
                limit = 1
            elif limit > 1000:
                limit = 1000
        if offset < 0:
            offset = 0

        filters = {}
        if steam_id_filter:
            filters["steam_id"] = steam_id_filter.strip()

        rows, total = _fetch_chest_rows(
            filters=filters or None, limit=limit, offset=offset
        )
        chests = [_serialize_chest_row(row) for row in rows]

        if minimal:
            chests_payload = [
                {
                    "entity_id": chest["entity_id"],
                    "steam_id": chest["steam_id"],
                    "player_name": chest.get("player_name"),
                    "fake_name": chest.get("fake_name"),
                    "chest_type": chest.get("chest_type"),
                    "location": chest.get("location"),
                    "last_seen_at": chest.get("last_seen_at"),
                }
                for chest in chests
            ]
        else:
            chests_payload = chests

        data: Dict[str, Any] = {
            "count": len(chests),
            "chests": chests_payload,
        }

        if include_summary:
            data["players"] = _build_chest_player_summary(chests)

        if limit is not None or offset:
            data["limit"] = limit if limit is not None else len(chests)
            data["offset"] = offset
            if total is not None:
                data["total"] = total

        return jsonify(
            {
                "success": True,
                "data": data,
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao listar baús: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


