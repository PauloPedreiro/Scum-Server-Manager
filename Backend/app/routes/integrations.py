"""
Blueprint: integrations
"""
from typing import Dict, Any, List, Optional, Tuple

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac
from core.shop.db import ssm_tx
from functools import wraps
from core.auth.decorators import require_auth, require_admin, require_player_auth
from utils.scum_db_helper import scum_db_readonly_connection_strict
from utils.integration_helpers import require_integration_key
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
import sqlite3
from .helpers import _get_ssm_database_path, _get_scum_database_path

integrations_bp = Blueprint('integrations', __name__)

@integrations_bp.route("/api/integrations/wallet/credit", methods=["POST"])
@require_integration_key
def integration_wallet_credit():
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
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        external_id = str((payload.get("external_id") or "")).strip()
        steam_id = str((payload.get("steam_id") or "")).strip()
        amount = payload.get("amount")
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}

        if not external_id or not steam_id or amount is None:
            return jsonify({"success": False, "error": "external_id, steam_id and amount are required"}), 400
        try:
            amount_i = int(amount)
        except Exception:
            return jsonify({"success": False, "error": "amount must be integer"}), 400
        if amount_i <= 0:
            return jsonify({"success": False, "error": "amount must be > 0"}), 400

        endpoint = "/api/integrations/wallet/credit"
        key_id = getattr(request, "integration_key_id", "")


        with ssm_tx(ssm_db_path) as conn:
            _ensure_integration_tables(conn)
            existing = _integration_find_idempotent(
                conn,
                key_id=str(key_id),
                endpoint=endpoint,
                external_id=str(external_id),
            )
            if existing is not None:
                payload_out, status_code = existing
                return jsonify(payload_out), int(status_code)

            pcur = conn.execute(
                "SELECT 1 FROM players WHERE steam_id = ? LIMIT 1",
                (str(steam_id),),
            )
            if not pcur.fetchone():
                resp = {"success": False, "error": "PLAYER_NOT_FOUND"}
                try:
                    _integration_log_request(
                        conn,
                        key_id=str(key_id),
                        endpoint=endpoint,
                        external_id=str(external_id),
                        steam_id=str(steam_id),
                        request_payload=payload,
                        response_payload=resp,
                        status_code=400,
                    )
                except sqlite3.IntegrityError:
                    pass
                return jsonify(resp), 400

            wallet = WalletService(ssm_db_path, logger=logger)
            apply_res = wallet.apply_delta(
                steam_id=str(steam_id),
                delta=int(amount_i),
                reason="integration_credit",
                ref_type="integration_credit",
                ref_id=str(external_id),
                meta=meta,
                allow_negative=False,
                conn=conn,
            )

            resp = {
                "success": True,
                "already_applied": bool(apply_res.already_applied),
                "steam_id": str(steam_id),
                "amount": int(amount_i),
                "balance": int(apply_res.balance),
            }
            try:
                _integration_log_request(
                    conn,
                    key_id=str(key_id),
                    endpoint=endpoint,
                    external_id=str(external_id),
                    steam_id=str(steam_id),
                    request_payload=payload,
                    response_payload=resp,
                    status_code=200,
                )
            except sqlite3.IntegrityError:
                existing = _integration_find_idempotent(
                    conn,
                    key_id=str(key_id),
                    endpoint=endpoint,
                    external_id=str(external_id),
                )
                if existing is not None:
                    payload_out, status_code = existing
                    return jsonify(payload_out), int(status_code)

        return jsonify(resp)
    except ValueError as e:
        if str(e) == "INSUFFICIENT_FUNDS":
            return jsonify({"success": False, "error": "INSUFFICIENT_FUNDS"}), 409
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@integrations_bp.route("/api/integrations/wallet/debit", methods=["POST"])
@require_integration_key
def integration_wallet_debit():
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
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        external_id = str((payload.get("external_id") or "")).strip()
        steam_id = str((payload.get("steam_id") or "")).strip()
        amount = payload.get("amount")
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}

        if not external_id or not steam_id or amount is None:
            return jsonify({"success": False, "error": "external_id, steam_id and amount are required"}), 400
        try:
            amount_i = int(amount)
        except Exception:
            return jsonify({"success": False, "error": "amount must be integer"}), 400
        if amount_i <= 0:
            return jsonify({"success": False, "error": "amount must be > 0"}), 400

        endpoint = "/api/integrations/wallet/debit"
        key_id = getattr(request, "integration_key_id", "")


        with ssm_tx(ssm_db_path) as conn:
            _ensure_integration_tables(conn)
            existing = _integration_find_idempotent(
                conn,
                key_id=str(key_id),
                endpoint=endpoint,
                external_id=str(external_id),
            )
            if existing is not None:
                payload_out, status_code = existing
                return jsonify(payload_out), int(status_code)

            pcur = conn.execute(
                "SELECT 1 FROM players WHERE steam_id = ? LIMIT 1",
                (str(steam_id),),
            )
            if not pcur.fetchone():
                resp = {"success": False, "error": "PLAYER_NOT_FOUND"}
                try:
                    _integration_log_request(
                        conn,
                        key_id=str(key_id),
                        endpoint=endpoint,
                        external_id=str(external_id),
                        steam_id=str(steam_id),
                        request_payload=payload,
                        response_payload=resp,
                        status_code=400,
                    )
                except sqlite3.IntegrityError:
                    pass
                return jsonify(resp), 400

            wallet = WalletService(ssm_db_path, logger=logger)
            apply_res = wallet.apply_delta(
                steam_id=str(steam_id),
                delta=int(-abs(int(amount_i))),
                reason="integration_debit",
                ref_type="integration_debit",
                ref_id=str(external_id),
                meta=meta,
                allow_negative=False,
                conn=conn,
            )

            resp = {
                "success": True,
                "already_applied": bool(apply_res.already_applied),
                "steam_id": str(steam_id),
                "amount": int(amount_i),
                "balance": int(apply_res.balance),
            }
            try:
                _integration_log_request(
                    conn,
                    key_id=str(key_id),
                    endpoint=endpoint,
                    external_id=str(external_id),
                    steam_id=str(steam_id),
                    request_payload=payload,
                    response_payload=resp,
                    status_code=200,
                )
            except sqlite3.IntegrityError:
                existing = _integration_find_idempotent(
                    conn,
                    key_id=str(key_id),
                    endpoint=endpoint,
                    external_id=str(external_id),
                )
                if existing is not None:
                    payload_out, status_code = existing
                    return jsonify(payload_out), int(status_code)

        return jsonify(resp)
    except ValueError as e:
        if str(e) == "INSUFFICIENT_FUNDS":
            return jsonify({"success": False, "error": "INSUFFICIENT_FUNDS"}), 409
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@integrations_bp.route("/api/integrations/wallet/balance", methods=["POST"])
@require_integration_key
def integration_wallet_balance():
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
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        external_id = str((payload.get("external_id") or "")).strip()
        steam_id = str((payload.get("steam_id") or "")).strip()
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        if not external_id or not steam_id:
            return jsonify({"success": False, "error": "external_id and steam_id are required"}), 400

        endpoint = "/api/integrations/wallet/balance"
        key_id = getattr(request, "integration_key_id", "")


        with ssm_tx(ssm_db_path) as conn:
            _ensure_integration_tables(conn)
            existing = _integration_find_idempotent(
                conn,
                key_id=str(key_id),
                endpoint=endpoint,
                external_id=str(external_id),
            )
            if existing is not None:
                payload_out, status_code = existing
                return jsonify(payload_out), int(status_code)

            pcur = conn.execute(
                "SELECT player_name FROM players WHERE steam_id = ? LIMIT 1",
                (str(steam_id),),
            )
            prow = pcur.fetchone()
            if not prow:
                resp = {"success": False, "error": "PLAYER_NOT_FOUND"}
                try:
                    _integration_log_request(
                        conn,
                        key_id=str(key_id),
                        endpoint=endpoint,
                        external_id=str(external_id),
                        steam_id=str(steam_id),
                        request_payload=payload,
                        response_payload=resp,
                        status_code=400,
                    )
                except sqlite3.IntegrityError:
                    pass
                return jsonify(resp), 400

            player_name = (str(prow[0]) if prow[0] is not None else None)

            # 10-minute rate limit per (key_id, endpoint, steam_id)
            cur_rl = conn.execute(
                """
                SELECT created_at
                FROM integration_requests
                WHERE key_id = ?
                  AND endpoint = ?
                  AND steam_id = ?
                  AND status_code = 200
                  AND datetime(created_at) >= datetime('now', '-10 minutes')
                ORDER BY datetime(created_at) DESC
                LIMIT 1
                """,
                (str(key_id), str(endpoint), str(steam_id)),
            )
            if cur_rl.fetchone():
                resp = {
                    "success": False,
                    "error": "RATE_LIMITED",
                    "retry_after_seconds": 600,
                }
                try:
                    _integration_log_request(
                        conn,
                        key_id=str(key_id),
                        endpoint=endpoint,
                        external_id=str(external_id),
                        steam_id=str(steam_id),
                        request_payload=payload,
                        response_payload=resp,
                        status_code=429,
                    )
                except sqlite3.IntegrityError:
                    pass
                return jsonify(resp), 429

            row = conn.execute(
                "SELECT balance FROM wallet WHERE steam_id = ? LIMIT 1",
                (str(steam_id),),
            ).fetchone()
            balance_i = int(row[0]) if row and row[0] is not None else 0

            resp = {
                "success": True,
                "steam_id": str(steam_id),
                "player_name": player_name,
                "balance": int(balance_i),
                "meta": meta,
            }
            try:
                _integration_log_request(
                    conn,
                    key_id=str(key_id),
                    endpoint=endpoint,
                    external_id=str(external_id),
                    steam_id=str(steam_id),
                    request_payload=payload,
                    response_payload=resp,
                    status_code=200,
                )
            except sqlite3.IntegrityError:
                existing = _integration_find_idempotent(
                    conn,
                    key_id=str(key_id),
                    endpoint=endpoint,
                    external_id=str(external_id),
                )
                if existing is not None:
                    payload_out, status_code = existing
                    return jsonify(payload_out), int(status_code)

        return jsonify(resp)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@integrations_bp.route("/api/integrations/vip/activate", methods=["POST"])
@require_integration_key
def integration_vip_activate():
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
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        external_id = str((payload.get("external_id") or "")).strip()
        steam_id = str((payload.get("steam_id") or "")).strip()
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        if not external_id or not steam_id:
            return jsonify({"success": False, "error": "external_id and steam_id are required"}), 400

        endpoint = "/api/integrations/vip/activate"
        key_id = getattr(request, "integration_key_id", "")


        with ssm_tx(ssm_db_path) as conn:
            _ensure_integration_tables(conn)
            existing = _integration_find_idempotent(
                conn,
                key_id=str(key_id),
                endpoint=endpoint,
                external_id=str(external_id),
            )
            if existing is not None:
                payload_out, status_code = existing
                return jsonify(payload_out), int(status_code)

            pcur = conn.execute(
                "SELECT 1 FROM players WHERE steam_id = ? LIMIT 1",
                (str(steam_id),),
            )
            if not pcur.fetchone():
                resp = {"success": False, "error": "PLAYER_NOT_FOUND"}
                try:
                    _integration_log_request(
                        conn,
                        key_id=str(key_id),
                        endpoint=endpoint,
                        external_id=str(external_id),
                        steam_id=str(steam_id),
                        request_payload=payload,
                        response_payload=resp,
                        status_code=400,
                    )
                except sqlite3.IntegrityError:
                    pass
                return jsonify(resp), 400

            rewards = RewardsService(ssm_db_path, logger=logger)
            rewards._ensure_playtime_rules_schema(conn)
            vip_id = rewards.get_playtime_rule_id_by_name("VIP", conn=conn)
            default_id = rewards.get_playtime_rule_id_by_name("Padrão", conn=conn)
            if not vip_id:
                resp = {"success": False, "error": "VIP_RULE_NOT_FOUND"}
                try:
                    _integration_log_request(
                        conn,
                        key_id=str(key_id),
                        endpoint=endpoint,
                        external_id=str(external_id),
                        steam_id=str(steam_id),
                        request_payload=payload,
                        response_payload=resp,
                        status_code=400,
                    )
                except sqlite3.IntegrityError:
                    pass
                return jsonify(resp), 400
            if not default_id:
                resp = {"success": False, "error": "DEFAULT_RULE_NOT_FOUND"}
                try:
                    _integration_log_request(
                        conn,
                        key_id=str(key_id),
                        endpoint=endpoint,
                        external_id=str(external_id),
                        steam_id=str(steam_id),
                        request_payload=payload,
                        response_payload=resp,
                        status_code=400,
                    )
                except sqlite3.IntegrityError:
                    pass
                return jsonify(resp), 400

            rewards.add_playtime_rule_target_conn(str(vip_id), str(steam_id), conn)
            # Remover do Padrão se estiver lá (não-bloqueante)
            if default_id:
                try:
                    rewards.remove_playtime_rule_target_conn(str(default_id), str(steam_id), conn)
                except Exception:
                    pass

            resp = {
                "success": True,
                "already_applied": False,
                "steam_id": str(steam_id),
                "vip": 1,
                "meta": meta,
            }
            try:
                _integration_log_request(
                    conn,
                    key_id=str(key_id),
                    endpoint=endpoint,
                    external_id=str(external_id),
                    steam_id=str(steam_id),
                    request_payload=payload,
                    response_payload=resp,
                    status_code=200,
                )
            except sqlite3.IntegrityError:
                existing = _integration_find_idempotent(
                    conn,
                    key_id=str(key_id),
                    endpoint=endpoint,
                    external_id=str(external_id),
                )
                if existing is not None:
                    payload_out, status_code = existing
                    return jsonify(payload_out), int(status_code)

        return jsonify(resp)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@integrations_bp.route("/api/integrations/vip/deactivate", methods=["POST"])
@require_integration_key
def integration_vip_deactivate():
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
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        external_id = str((payload.get("external_id") or "")).strip()
        steam_id = str((payload.get("steam_id") or "")).strip()
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        if not external_id or not steam_id:
            return jsonify({"success": False, "error": "external_id and steam_id are required"}), 400

        endpoint = "/api/integrations/vip/deactivate"
        key_id = getattr(request, "integration_key_id", "")


        with ssm_tx(ssm_db_path) as conn:
            _ensure_integration_tables(conn)
            existing = _integration_find_idempotent(
                conn,
                key_id=str(key_id),
                endpoint=endpoint,
                external_id=str(external_id),
            )
            if existing is not None:
                payload_out, status_code = existing
                return jsonify(payload_out), int(status_code)

            pcur = conn.execute(
                "SELECT 1 FROM players WHERE steam_id = ? LIMIT 1",
                (str(steam_id),),
            )
            if not pcur.fetchone():
                resp = {"success": False, "error": "PLAYER_NOT_FOUND"}
                try:
                    _integration_log_request(
                        conn,
                        key_id=str(key_id),
                        endpoint=endpoint,
                        external_id=str(external_id),
                        steam_id=str(steam_id),
                        request_payload=payload,
                        response_payload=resp,
                        status_code=400,
                    )
                except sqlite3.IntegrityError:
                    pass
                return jsonify(resp), 400

            rewards = RewardsService(ssm_db_path, logger=logger)
            rewards._ensure_playtime_rules_schema(conn)
            vip_id = rewards.get_playtime_rule_id_by_name("VIP", conn=conn)
            default_id = rewards.get_playtime_rule_id_by_name("Padrão", conn=conn)
            if not vip_id:
                resp = {"success": False, "error": "VIP_RULE_NOT_FOUND"}
                try:
                    _integration_log_request(
                        conn,
                        key_id=str(key_id),
                        endpoint=endpoint,
                        external_id=str(external_id),
                        steam_id=str(steam_id),
                        request_payload=payload,
                        response_payload=resp,
                        status_code=400,
                    )
                except sqlite3.IntegrityError:
                    pass
                return jsonify(resp), 400
            if not default_id:
                resp = {"success": False, "error": "DEFAULT_RULE_NOT_FOUND"}
                try:
                    _integration_log_request(
                        conn,
                        key_id=str(key_id),
                        endpoint=endpoint,
                        external_id=str(external_id),
                        steam_id=str(steam_id),
                        request_payload=payload,
                        response_payload=resp,
                        status_code=400,
                    )
                except sqlite3.IntegrityError:
                    pass
                return jsonify(resp), 400

            rewards.remove_playtime_rule_target_conn(str(vip_id), str(steam_id), conn)
            rewards.add_playtime_rule_target_conn(str(default_id), str(steam_id), conn)

            resp = {
                "success": True,
                "already_applied": False,
                "steam_id": str(steam_id),
                "vip": 0,
                "meta": meta,
            }
            try:
                _integration_log_request(
                    conn,
                    key_id=str(key_id),
                    endpoint=endpoint,
                    external_id=str(external_id),
                    steam_id=str(steam_id),
                    request_payload=payload,
                    response_payload=resp,
                    status_code=200,
                )
            except sqlite3.IntegrityError:
                existing = _integration_find_idempotent(
                    conn,
                    key_id=str(key_id),
                    endpoint=endpoint,
                    external_id=str(external_id),
                )
                if existing is not None:
                    payload_out, status_code = existing
                    return jsonify(payload_out), int(status_code)

        return jsonify(resp)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


