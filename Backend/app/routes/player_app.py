"""
Blueprint: player_app
"""
from core.database.connector import DatabaseConnector

from flask import Blueprint, jsonify, request, send_file, Response
from core.shop.db import ssm_tx
from app.extensions import get_services
import traceback, os, time, json, hmac
from functools import wraps
from core.auth.decorators import require_auth, require_admin, require_player_auth
from utils.scum_db_helper import scum_db_readonly_connection_strict
from utils.integration_helpers import require_integration_key
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
import sqlite3

from .helpers import (
    _get_ssm_database_path,
    _get_scum_database_path,
    _gestao_get_player_identity,
    _issue_player_jwt,
    _str_to_bool,
    _fetch_chest_rows,
    _serialize_chest_row,
    _safe_float,
    _format_vehicle_class_display
)

player_app_bp = Blueprint('player_app', __name__)

@player_app_bp.route("/api/player/auth/exchange", methods=["POST"])
def player_auth_exchange():
    """Troca token do Gestão por Player JWT do SSM"""
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
        # Token do Gestão
        gestao_token = ""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            gestao_token = auth_header.split(" ", 1)[1].strip()

        body = request.get_json(silent=True) or {}
        if not gestao_token:
            gestao_token = str(body.get("gestao_token") or body.get("gestao_access_token") or "").strip()

        server_hash = str(body.get("server_hash") or request.headers.get("X-Server-Hash") or "").strip()
        if not server_hash:
            return jsonify({"success": False, "error": "SERVER_HASH_REQUIRED"}), 400

        steam_id, err = _gestao_get_player_identity(gestao_token)
        if err or not steam_id:
            return jsonify({"success": False, "error": err or "AUTH_FAILED"}), 401

        token = _issue_player_jwt(steam_id=steam_id, server_hash=server_hash)
        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "player_token": token,
                        "token_type": "Bearer",
                        "steam_id": steam_id,
                        "server_hash": server_hash,
                    },
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/chests", methods=["GET"])
@require_player_auth
def player_get_my_chests():
    """Listar baús vinculados ao jogador autenticado (via chest_snapshot)."""
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", default=0, type=int)
        minimal = _str_to_bool(request.args.get("minimal"))

        if limit is not None:
            if limit < 1:
                limit = 1
            elif limit > 1000:
                limit = 1000
        if offset < 0:
            offset = 0

        rows, total = _fetch_chest_rows(
            filters={"steam_id": steam_id}, limit=limit, offset=offset
        )
        chests = [_serialize_chest_row(row) for row in rows]

        type_counts: Dict[str, int] = {}
        for chest in chests:
            chest_type = chest.get("chest_type") or chest.get("chest_class") or "Desconhecido"
            type_counts[chest_type] = type_counts.get(chest_type, 0) + 1

        player_names = sorted({c["player_name"] for c in chests if c.get("player_name")})
        fake_names = sorted({c["fake_name"] for c in chests if c.get("fake_name")})

        if minimal:
            chests_payload = [
                {
                    "entity_id": chest["entity_id"],
                    "chest_type": chest.get("chest_type"),
                    "custom_name": chest.get("custom_name"),
                    "location": chest.get("location"),
                    "has_vehicle": chest.get("has_vehicle"),
                    "vehicle_owner_mismatch": chest.get("vehicle_owner_mismatch"),
                    "last_seen_at": chest.get("last_seen_at"),
                }
                for chest in chests
            ]
        else:
            chests_payload = chests

        data: Dict[str, Any] = {
            "steam_id": steam_id,
            "count": len(chests),
            "type_counts": type_counts,
            "player_names": player_names,
            "fake_names": fake_names,
            "chests": chests_payload,
        }
        if limit is not None or offset:
            data["limit"] = limit if limit is not None else len(chests)
            data["offset"] = offset
            if total is not None:
                data["total"] = total

        return jsonify({"success": True, "data": data, "timestamp": time.time()}), 200

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter baús do jogador (player-scoped): {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/chests/<int:entity_id>", methods=["GET"])
@require_player_auth
def player_get_my_chest_detail(entity_id: int):
    """Detalhar um baú por entity_id, garantindo que pertence ao jogador autenticado."""
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        rows, _ = _fetch_chest_rows(filters={"steam_id": steam_id})
        row = None
        for r in rows:
            if int(r["entity_id"]) == int(entity_id):
                row = r
                break

        if not row:
            return jsonify({"success": False, "error": "CHEST_NOT_FOUND"}), 404

        return (
            jsonify(
                {"success": True, "data": _serialize_chest_row(row), "timestamp": time.time()}
            ),
            200,
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter detalhe do baú {entity_id} (player-scoped): {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/chests/<int:entity_id>/inventory", methods=["GET"])
@require_player_auth
def player_get_my_chest_inventory(entity_id: int):
    """Obter inventário do baú (lendo SCUM.db) e persistir snapshot no SSM.db."""
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        ssm_db_path, ssm_err = _get_ssm_database_path()
        if ssm_err:
            return jsonify({"success": False, "error": ssm_err}), 500
        scum_db_path, scum_err = _get_scum_database_path()
        if scum_err:
            return jsonify({"success": False, "error": scum_err}), 500

        # Confirmar que o baú pertence ao jogador (SSM snapshot)
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT entity_id, steam_id, player_name FROM chest_snapshot WHERE entity_id = ? LIMIT 1",
                (int(entity_id),),
            )
            chest_row = cur.fetchone()

        if not chest_row:
            return jsonify({"success": False, "error": "CHEST_NOT_FOUND"}), 404
        if str(chest_row["steam_id"] or "").strip() != steam_id:
            return jsonify({"success": False, "error": "CHEST_NOT_FOUND"}), 404

        items, scan_err = _scan_scum_chest_inventory(scum_db_path, int(entity_id))
        if scan_err:
            return jsonify({"success": False, "error": scan_err}), 400
        if items is None:
            return jsonify({"success": False, "error": "CHEST_NOT_FOUND_SCUMDB"}), 404

        scanned_at = datetime.utcnow().isoformat()
        player_name = chest_row["player_name"]

        _ensure_chest_inventory_tables(ssm_db_path)
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()

            # Auto-preencher catálogo de itens conforme forem aparecendo
            try:
                inserted = _autofill_item_catalog(
                    conn,
                    sorted({str(it.get("item_class") or "").strip() for it in items}),
                )
            except Exception:
                inserted = 0

            cur.execute(
                "DELETE FROM chest_inventory_item WHERE chest_entity_id = ?",
                (int(entity_id),),
            )
            cur.executemany(
                """
                INSERT INTO chest_inventory_item(
                    chest_entity_id, item_entity_id, item_class, slot_index, scanned_at, quantity
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        int(entity_id),
                        int(it.get("item_entity_id") or 0),
                        it.get("item_class"),
                        it.get("slot_index"),
                        scanned_at,
                        int(it.get("quantity") or 1),
                    )
                    for it in items
                ],
            )
            cur.execute(
                """
                INSERT INTO chest_inventory_snapshot(chest_entity_id, steam_id, player_name, scanned_at, items_total)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(chest_entity_id) DO UPDATE SET
                    steam_id=excluded.steam_id,
                    player_name=excluded.player_name,
                    scanned_at=excluded.scanned_at,
                    items_total=excluded.items_total
                """,
                (int(entity_id), steam_id, player_name, scanned_at, len(items)),
            )
            conn.commit()

        counts: Dict[str, int] = {}
        quantity_by_class: Dict[str, int] = {}
        for it in items:
            key = str(it.get("item_class") or "Unknown")
            counts[key] = counts.get(key, 0) + 1
            try:
                quantity_by_class[key] = quantity_by_class.get(key, 0) + int(
                    it.get("quantity") or 1
                )
            except Exception:
                quantity_by_class[key] = quantity_by_class.get(key, 0) + 1

        return jsonify(
            {
                "success": True,
                "data": {
                    "chest_entity_id": int(entity_id),
                    "steam_id": steam_id,
                    "player_name": player_name,
                    "scanned_at": scanned_at,
                    "items_total": len(items),
                    "counts": counts,
                    "quantity_by_class": quantity_by_class,
                    "items": items,
                    "catalog_new_items": int(inserted),
                },
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter inventário do baú {entity_id} (player-scoped): {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/chests/history", methods=["GET"])
@require_player_auth
def player_get_my_chest_history():
    """Listar eventos do histórico de baús do jogador autenticado (via chest_history)."""
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        limit = request.args.get("limit", default=50, type=int)
        offset = request.args.get("offset", default=0, type=int)
        event_type = request.args.get("event_type")

        if limit < 1:
            limit = 1
        elif limit > 500:
            limit = 500

        if offset < 0:
            offset = 0

        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        where = ["steam_id = ?"]
        params: List[Any] = [steam_id]
        if event_type:
            where.append("LOWER(event_type) = ?")
            params.append(str(event_type).strip().lower())
        where_clause = "WHERE " + " AND ".join(where)

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                f"SELECT COUNT(*) AS total FROM chest_history {where_clause}",
                params,
            )
            total = cursor.fetchone()["total"]

            cursor.execute(
                f"""
                SELECT
                    id, entity_id, event_type, container_entity_id,
                    owner_profile_id, steam_id, player_name, fake_name, custom_name,
                    chest_class,
                    location_x, location_y, location_z,
                    rotation_x, rotation_y, rotation_z,
                    vehicle_container_class, vehicle_entity_id, vehicle_class,
                    vehicle_owner_steam_id, vehicle_owner_name, vehicle_owner_player_id,
                    vehicle_registered_at, vehicle_owner_mismatch,
                    details_json, event_at
                FROM chest_history
                {where_clause}
                ORDER BY event_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            )
            rows = cursor.fetchall()

        events: List[Dict[str, Any]] = []
        for row in rows:
            details = row["details_json"]
            if isinstance(details, str) and details.strip():
                try:
                    details = json.loads(details)
                except Exception:
                    details = row["details_json"]

            events.append(
                {
                    "id": row["id"],
                    "entity_id": row["entity_id"],
                    "event_type": row["event_type"],
                    "custom_name": row["custom_name"],
                    "chest_class": row["chest_class"],
                    "chest_type": _get_chest_display_name_api(row["chest_class"]),
                    "location": {
                        "x": _safe_float(row["location_x"]),
                        "y": _safe_float(row["location_y"]),
                        "z": _safe_float(row["location_z"]),
                    },
                    "vehicle_owner_mismatch": (
                        bool(row["vehicle_owner_mismatch"])
                        if row["vehicle_owner_mismatch"] is not None
                        else False
                    ),
                    "details": details,
                    "event_at": row["event_at"],
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "steam_id": steam_id,
                    "events": events,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "count": len(events),
                },
                "timestamp": time.time(),
            }
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter histórico de baús (player-scoped): {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/vehicles", methods=["GET"])
@require_player_auth
def player_get_my_vehicles():
    """Listar veículos do jogador autenticado (via vehicle_current_ownership)."""
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        if not log_processor:
            return jsonify({"success": False, "error": "SERVICE_UNAVAILABLE"}), 503

        status_param = request.args.get("status")
        limit = request.args.get("limit", default=200, type=int)
        offset = request.args.get("offset", default=0, type=int)

        if limit < 1:
            limit = 1
        elif limit > 1000:
            limit = 1000
        if offset < 0:
            offset = 0

        status_filter: list = []
        if status_param is not None:
            try:
                status_filter = [int(s.strip()) for s in str(status_param).split(",") if s.strip()]
            except ValueError:
                return jsonify({"success": False, "error": "INVALID_STATUS_PARAM"}), 400

        db_path = log_processor.db_manager.db_path
        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            where = ["steam_id = ?"]
            params: List[Any] = [steam_id]

            if status_filter:
                placeholders = ",".join(["?"] * len(status_filter))
                where.append(f"status IN ({placeholders})")
                params.extend(status_filter)

            where_clause = "WHERE " + " AND ".join(where)

            cursor = conn.execute(
                f"SELECT COUNT(*) AS total FROM vehicle_current_ownership {where_clause}",
                params,
            )
            total = cursor.fetchone()["total"]

            cursor = conn.execute(
                f"""
                SELECT * FROM vehicle_current_ownership
                {where_clause}
                ORDER BY status ASC, last_ownership_change DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            )
            rows = cursor.fetchall()

        status_map = {0: "Ativo", 1: "Inativo", 2: "Desaparecido", 3: "Destruído"}

        vehicles: List[Dict[str, Any]] = []
        summary_by_status: Dict[str, int] = {}
        summary_by_class: Dict[str, int] = {}

        for row in rows:
            v = dict(row)
            v["status_text"] = status_map.get(v.get("status"), "Desconhecido")
            v["vehicle_class_display"] = _format_vehicle_class_display(v.get("vehicle_class"))
            if v.get("location_x") is not None:
                v["location"] = {
                    "x": _safe_float(v.pop("location_x", None)),
                    "y": _safe_float(v.pop("location_y", None)),
                    "z": _safe_float(v.pop("location_z", None)),
                }
            else:
                v.pop("location_x", None)
                v.pop("location_y", None)
                v.pop("location_z", None)
                v["location"] = None
            vehicles.append(v)

            sk = str(v.get("status", 0))
            summary_by_status[sk] = summary_by_status.get(sk, 0) + 1

            ck = v.get("vehicle_class_display") or "Desconhecido"
            summary_by_class[ck] = summary_by_class.get(ck, 0) + 1

        return jsonify(
            {
                "success": True,
                "data": {
                    "steam_id": steam_id,
                    "total": total,
                    "count": len(vehicles),
                    "limit": limit,
                    "offset": offset,
                    "summary": {
                        "by_status": summary_by_status,
                        "by_class": summary_by_class,
                    },
                    "vehicles": vehicles,
                },
                "timestamp": time.time(),
            }
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter veículos do jogador (player-scoped): {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/vehicles/summary", methods=["GET"])
@require_player_auth
def player_get_my_vehicles_summary():
    """Resumo de veículos do jogador autenticado (contagens por status e tipo)."""
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        if not log_processor:
            return jsonify({"success": False, "error": "SERVICE_UNAVAILABLE"}), 503

        db_path = log_processor.db_manager.db_path
        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute(
                "SELECT COUNT(*) AS total FROM vehicle_current_ownership WHERE steam_id = ?",
                (steam_id,),
            )
            total = cursor.fetchone()["total"]

            cursor = conn.execute(
                """
                SELECT status, COUNT(*) AS cnt
                FROM vehicle_current_ownership
                WHERE steam_id = ?
                GROUP BY status
                """,
                (steam_id,),
            )
            by_status_raw = cursor.fetchall()

            cursor = conn.execute(
                """
                SELECT vehicle_class, COUNT(*) AS cnt
                FROM vehicle_current_ownership
                WHERE steam_id = ?
                GROUP BY vehicle_class
                """,
                (steam_id,),
            )
            by_class_raw = cursor.fetchall()

        status_map = {0: "Ativo", 1: "Inativo", 2: "Desaparecido", 3: "Destruído"}
        by_status: Dict[str, Any] = {}
        for row in by_status_raw:
            s = int(row["status"])
            by_status[str(s)] = {"count": row["cnt"], "label": status_map.get(s, "Desconhecido")}

        by_class: Dict[str, int] = {}
        for row in by_class_raw:
            display = _format_vehicle_class_display(row["vehicle_class"])
            by_class[display] = by_class.get(display, 0) + row["cnt"]

        return jsonify(
            {
                "success": True,
                "data": {
                    "steam_id": steam_id,
                    "total": total,
                    "by_status": by_status,
                    "by_class": by_class,
                },
                "timestamp": time.time(),
            }
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter resumo de veículos (player-scoped): {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/vehicles/<int:vehicle_entity_id>", methods=["GET"])
@require_player_auth
def player_get_my_vehicle_detail(vehicle_entity_id: int):
    """Detalhar veículo específico do jogador autenticado, incluindo histórico."""
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        if not log_processor:
            return jsonify({"success": False, "error": "SERVICE_UNAVAILABLE"}), 503

        include_history = _str_to_bool(request.args.get("history"))
        history_limit = request.args.get("history_limit", default=20, type=int)
        if history_limit < 1:
            history_limit = 1
        elif history_limit > 100:
            history_limit = 100

        db_path = log_processor.db_manager.db_path
        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute(
                """
                SELECT * FROM vehicle_current_ownership
                WHERE vehicle_entity_id = ? AND steam_id = ?
                LIMIT 1
                """,
                (vehicle_entity_id, steam_id),
            )
            row = cursor.fetchone()

            if not row:
                return jsonify({"success": False, "error": "VEHICLE_NOT_FOUND"}), 404

            vehicle = dict(row)

            history: List[Dict[str, Any]] = []
            if include_history:
                cursor = conn.execute(
                    """
                    SELECT * FROM vehicle_ownership_history
                    WHERE vehicle_entity_id = ? AND steam_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (vehicle_entity_id, steam_id, history_limit),
                )
                history = [dict(r) for r in cursor.fetchall()]

        status_map = {0: "Ativo", 1: "Inativo", 2: "Desaparecido", 3: "Destruído"}
        vehicle["status_text"] = status_map.get(vehicle.get("status"), "Desconhecido")
        vehicle["vehicle_class_display"] = _format_vehicle_class_display(vehicle.get("vehicle_class"))
        if vehicle.get("location_x") is not None:
            vehicle["location"] = {
                "x": _safe_float(vehicle.pop("location_x", None)),
                "y": _safe_float(vehicle.pop("location_y", None)),
                "z": _safe_float(vehicle.pop("location_z", None)),
            }
        else:
            vehicle.pop("location_x", None)
            vehicle.pop("location_y", None)
            vehicle.pop("location_z", None)
            vehicle["location"] = None

        data: Dict[str, Any] = {"vehicle": vehicle}
        if include_history:
            data["history"] = history
            data["history_count"] = len(history)

        return jsonify(
            {"success": True, "data": data, "timestamp": time.time()}
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter detalhe do veículo {vehicle_entity_id} (player-scoped): {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/me", methods=["GET"])
@require_player_auth
def player_me():
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
        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "steam_id": str(getattr(request, "player_steam_id", "")),
                        "server_hash": str(getattr(request, "player_server_hash", "")),
                    },
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/wallet/balance", methods=["GET"])
@require_player_auth
def player_wallet_balance():
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500


        balance = 0
        with ssm_tx(ssm_db_path) as conn:
            cur = conn.execute(
                "SELECT balance FROM wallet WHERE steam_id = ? LIMIT 1", (steam_id,)
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                try:
                    balance = int(row[0])
                except Exception:
                    balance = 0

        return jsonify({"success": True, "data": {"balance": balance}}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/bank-account/current", methods=["GET"])
@require_player_auth
def player_bank_account_current():
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500


        row = None
        with ssm_tx(ssm_db_path) as conn:
            cur = conn.execute(
                """
                SELECT
                    account_number,
                    money_balance,
                    gold_balance,
                    account_balance,
                    total_balance,
                    last_transaction_ts,
                    source,
                    updated_at
                FROM bank_accounts_current
                WHERE steam_id = ?
                LIMIT 1
                """,
                (steam_id,),
            )
            row = cur.fetchone()

        def _to_float(val):
            try:
                return float(val or 0.0)
            except Exception:
                return 0.0

        if not row:
            data = {
                "account_number": None,
                "balances": {
                    "money_in_hand": 0.0,
                    "money_in_bank": 0.0,
                    "money_total": 0.0,
                    "gold": 0.0,
                },
                "meta": {
                    "has_data": False,
                    "updated_at": None,
                    "source": None,
                    "last_transaction_ts": None,
                },
            }
            return jsonify({"success": True, "data": data, "timestamp": time.time()}), 200

        account_number = row[0]
        money_balance = _to_float(row[1])
        gold_balance = _to_float(row[2])
        account_balance = _to_float(row[3])
        total_balance = _to_float(row[4])
        last_transaction_ts = row[5]
        source = row[6]
        updated_at = row[7]

        money_total = total_balance
        if money_total <= 0.0:
            money_total = money_balance + account_balance

        data = {
            "account_number": account_number,
            "balances": {
                "money_in_hand": money_balance,
                "money_in_bank": account_balance,
                "money_total": money_total,
                "gold": gold_balance,
            },
            "meta": {
                "has_data": True,
                "updated_at": updated_at,
                "source": source,
                "last_transaction_ts": last_transaction_ts,
            },
        }
        return jsonify({"success": True, "data": data, "timestamp": time.time()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/profile", methods=["GET"])
@require_player_auth
def player_profile():
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500


        with ssm_tx(ssm_db_path) as conn:
            cur = conn.execute(
                """
                SELECT
                    steam_id,
                    player_name,
                    player_id,
                    first_seen,
                    last_seen,
                    total_sessions,
                    total_playtime,
                    is_new_player,
                    notification_sent,
                    permissao,
                    created_at,
                    elevated_user
                FROM players
                WHERE steam_id = ?
                LIMIT 1
                """,
                (steam_id,),
            )
            row = cur.fetchone()

        if not row:
            return jsonify({"success": True, "data": None}), 200

        data = {
            "steam_id": str(row[0]),
            "player_name": str(row[1]),
            "player_id": int(row[2]) if row[2] is not None else None,
            "first_seen": row[3],
            "last_seen": row[4],
            "total_sessions": int(row[5]) if row[5] is not None else 0,
            "total_playtime": int(row[6]) if row[6] is not None else 0,
            "is_new_player": bool(row[7]) if row[7] is not None else False,
            "notification_sent": bool(row[8]) if row[8] is not None else False,
            "permissao": int(row[9]) if row[9] is not None else 0,
            "created_at": row[10],
            "elevated_user": int(row[11]) if row[11] is not None else 0,
        }

        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/rankings", methods=["GET"])
@require_player_auth
def player_get_rankings():
    """Rankings (leaderboard) para o Player App. Usa a tabela rankings do SSM.db."""
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
        category = request.args.get("category", "kills")
        limit = request.args.get("limit", type=int) or 20
        offset = request.args.get("offset", type=int) or 0

        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        if offset < 0:
            offset = 0

        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

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

        order_column = category_map.get(str(category or "").strip().lower())
        if not order_column:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "INVALID_CATEGORY",
                        "available_categories": sorted(list(category_map.keys())),
                    }
                ),
                400,
            )

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(f"SELECT COUNT(*) FROM rankings WHERE {order_column} > 0")
            total = cursor.fetchone()[0]

            cursor.execute(
                f"""
                SELECT steam_id, player_name, {order_column} AS value, last_updated
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
                    "value": row["value"],
                    "last_updated": row["last_updated"],
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "category": str(category),
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
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/rankings/me", methods=["GET"])
@require_player_auth
def player_get_my_ranking():
    """Retorna a linha do jogador na tabela rankings e uma posição aproximada por categoria."""
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        category = request.args.get("category", "kills")

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

        order_column = category_map.get(str(category or "").strip().lower())
        if not order_column:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "INVALID_CATEGORY",
                        "available_categories": sorted(list(category_map.keys())),
                    }
                ),
                400,
            )

        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT steam_id, player_name, {order_column} AS value, last_updated
                FROM rankings
                WHERE steam_id = ?
                """,
                (steam_id,),
            )
            row = cursor.fetchone()

            if not row:
                return jsonify({"success": True, "data": None, "timestamp": time.time()}), 200

            value = row["value"]
            cursor.execute(
                f"SELECT COUNT(*) + 1 FROM rankings WHERE {order_column} > ?",
                (value,),
            )
            approx_rank = cursor.fetchone()[0]

        data = {
            "steam_id": row["steam_id"],
            "player_name": row["player_name"],
            "category": str(category),
            "value": value,
            "approx_rank": approx_rank,
            "last_updated": row["last_updated"],
        }

        return jsonify({"success": True, "data": data, "timestamp": time.time()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@player_app_bp.route("/api/player/survival-stats/snapshot", methods=["GET"])
@require_player_auth
def player_survival_stats_snapshot():
    """Retorna o snapshot atual de survival stats do jogador autenticado."""
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
        steam_id = str(getattr(request, "player_steam_id", "") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "INVALID_TOKEN"}), 401

        db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM survival_stats_snapshot WHERE steam_id = ? LIMIT 1",
                (steam_id,),
            )
            row = cursor.fetchone()

        if not row:
            return jsonify({"success": True, "data": None, "timestamp": time.time()}), 200

        row_dict = dict(row)
        meta_keys = {"user_profile_id", "steam_id", "player_name", "snapshot_at"}
        metrics = {k: row_dict.get(k) for k in row_dict.keys() if k not in meta_keys}

        kills = metrics.get("kills") or 0
        deaths = metrics.get("deaths") or 0
        shots_fired = metrics.get("shots_fired") or 0
        shots_hit = metrics.get("shots_hit") or 0

        raw_kdr = float(kills) / deaths if deaths else float(kills)
        kdr = round(raw_kdr, 2) if deaths else raw_kdr
        accuracy = round((shots_hit / shots_fired) * 100, 2) if shots_fired else None

        return jsonify(
            {
                "success": True,
                "data": {
                    "steam_id": row_dict.get("steam_id"),
                    "player_name": row_dict.get("player_name"),
                    "user_profile_id": row_dict.get("user_profile_id"),
                    "snapshot_at": row_dict.get("snapshot_at"),
                    "metrics": metrics,
                    "derived": {"kdr": kdr, "accuracy_percent": accuracy},
                },
                "timestamp": time.time(),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


