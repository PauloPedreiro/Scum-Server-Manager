"""
Blueprint: shop
"""
from typing import Dict, Any, List, Optional, Tuple
from core.database.connector import DatabaseConnector

from flask import Blueprint, jsonify, request, send_file, Response
from core.shop.db import ssm_tx
from app.extensions import get_services
import traceback, os, time, json, hmac, queue
from functools import wraps
from core.auth.decorators import require_auth, require_admin
from utils.integration_helpers import (
    require_integration_key,
    ensure_integration_tables as _ensure_integration_tables,
    integration_key_hash as _integration_key_hash,
)
from utils.scum_db_helper import scum_db_readonly_connection_strict
from core.shop.shop_service import ShopService, OrderCreateItem
from core.shop.delivery_service import ShopDeliveryService
from .helpers import _get_ssm_database_path, _ensure_sqlite_wal, _get_scum_database_path
from core.shop.wallet_service import WalletService
from core.shop.rewards_service import RewardsService
from core.shop.scanner_service import ShopScannerService
from utils.sqlite_queue import submit_sqlite_write as _submit_sqlite_write
import sqlite3
from uuid import uuid4

shop_bp = Blueprint('shop', __name__)

@shop_bp.route("/api/shop/wallet/balance", methods=["GET"])
@require_auth
def shop_wallet_get_balance():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        current_user = getattr(request, "current_user", {}) or {}
        current_steam_id = (current_user.get("steam_id") or "").strip()

        requested_steam_id = (request.args.get("steam_id") or "").strip()
        steam_id = requested_steam_id or current_steam_id
        if not steam_id:
            return (
                jsonify({"success": False, "error": "steam_id is required"}),
                400,
            )

        # Non-admin can only query own balance
        is_admin = str(current_user.get("role") or "").lower() == "admin"
        if requested_steam_id and not is_admin and requested_steam_id != current_steam_id:
            return jsonify({"success": False, "error": "FORBIDDEN"}), 403

        wallet = WalletService(ssm_db_path, logger=logger)
        balance = wallet.get_balance(steam_id)

        return jsonify({"success": True, "data": {"steam_id": steam_id, "balance": int(balance)}})
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_wallet_get_balance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/wallet/transactions", methods=["GET"])
@require_auth
def shop_wallet_get_transactions():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        current_user = getattr(request, "current_user", {}) or {}
        steam_id = (current_user.get("steam_id") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "steam_id is required"}), 400

        limit_raw = request.args.get("limit", 50)
        try:
            limit_i = int(limit_raw)
        except Exception:
            limit_i = 50
        if limit_i < 1:
            limit_i = 1
        if limit_i > 200:
            limit_i = 200

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT tx_id, delta, reason, ref_type, ref_id, meta_json, created_at
                FROM wallet_tx
                WHERE steam_id = ?
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (steam_id, int(limit_i)),
            )
            rows = cur.fetchall() or []

        items = []
        for row in rows:
            tx_id, delta, reason, ref_type, ref_id, meta_json, created_at = row
            try:
                meta = json.loads(meta_json) if meta_json else {}
            except Exception:
                meta = {}
            items.append(
                {
                    "tx_id": str(tx_id),
                    "delta": int(delta or 0),
                    "reason": str(reason or ""),
                    "ref_type": str(ref_type) if ref_type is not None else None,
                    "ref_id": str(ref_id) if ref_id is not None else None,
                    "meta": meta,
                    "created_at": str(created_at or ""),
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {"steam_id": steam_id, "items": items, "count": len(items)},
            }
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_wallet_get_transactions: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/wallet/transactions", methods=["GET"])
@require_auth
@require_admin
def shop_admin_wallet_get_transactions():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        steam_id = (request.args.get("steam_id") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "steam_id is required"}), 400

        limit_raw = request.args.get("limit", 100)
        try:
            limit_i = int(limit_raw)
        except Exception:
            limit_i = 100
        if limit_i < 1:
            limit_i = 1
        if limit_i > 500:
            limit_i = 500

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT tx_id, delta, reason, ref_type, ref_id, meta_json, created_at
                FROM wallet_tx
                WHERE steam_id = ?
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (steam_id, int(limit_i)),
            )
            rows = cur.fetchall() or []

        items = []
        for row in rows:
            tx_id, delta, reason, ref_type, ref_id, meta_json, created_at = row
            try:
                meta = json.loads(meta_json) if meta_json else {}
            except Exception:
                meta = {}
            items.append(
                {
                    "tx_id": str(tx_id),
                    "delta": int(delta or 0),
                    "reason": str(reason or ""),
                    "ref_type": str(ref_type) if ref_type is not None else None,
                    "ref_id": str(ref_id) if ref_id is not None else None,
                    "meta": meta,
                    "created_at": str(created_at or ""),
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {"steam_id": steam_id, "items": items, "count": len(items)},
            }
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_wallet_get_transactions: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/wallet/adjust", methods=["POST"])
@require_auth
@require_admin
def shop_admin_wallet_adjust():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        external_id = (payload.get("external_id") or "").strip()
        steam_id = (payload.get("steam_id") or "").strip()
        delta = payload.get("delta")
        reason = (payload.get("reason") or "admin_adjust").strip() or "admin_adjust"
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}

        if not external_id or not steam_id or delta is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "external_id, steam_id and delta are required",
                    }
                ),
                400,
            )

        try:
            delta_i = int(delta)
        except Exception:
            return jsonify({"success": False, "error": "delta must be integer"}), 400
        if delta_i == 0:
            return jsonify({"success": False, "error": "delta must be != 0"}), 400

        wallet = WalletService(ssm_db_path, logger=logger)
        apply_res = wallet.apply_delta(
            steam_id=steam_id,
            delta=int(delta_i),
            reason=str(reason),
            ref_type="admin_adjust",
            ref_id=external_id,
            meta=meta,
            allow_negative=False,
        )

        return jsonify(
            {
                "success": True,
                "already_applied": bool(apply_res.already_applied),
                "steam_id": steam_id,
                "delta": int(delta_i),
                "balance": int(apply_res.balance),
            }
        )
    except ValueError as e:
        if str(e) == "INSUFFICIENT_FUNDS":
            return jsonify({"success": False, "error": "INSUFFICIENT_FUNDS"}), 409
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_wallet_adjust: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/credit", methods=["POST"])
@require_auth
@require_admin
def shop_admin_credit():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        external_id = (payload.get("external_id") or "").strip()
        steam_id = (payload.get("steam_id") or "").strip()
        amount = payload.get("amount")
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}

        if not external_id or not steam_id or amount is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "external_id, steam_id and amount are required",
                    }
                ),
                400,
            )

        try:
            amount_i = int(amount)
        except Exception:
            return jsonify({"success": False, "error": "amount must be integer"}), 400
        if amount_i <= 0:
            return jsonify({"success": False, "error": "amount must be > 0"}), 400

        wallet = WalletService(ssm_db_path, logger=logger)

        import sqlite3
        from uuid import uuid4


        already_applied = False
        with ssm_tx(ssm_db_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO admin_credit(credit_id, external_id, steam_id, amount, status)
                    VALUES(?, ?, ?, ?, 'applied')
                    """,
                    (str(uuid4()), external_id, steam_id, int(amount_i)),
                )
            except sqlite3.IntegrityError:
                already_applied = True

        apply_res = wallet.apply_delta(
            steam_id=steam_id,
            delta=int(amount_i),
            reason="admin_grant",
            ref_type="admin_credit",
            ref_id=external_id,
            meta=meta,
            allow_negative=False,
        )

        return jsonify(
            {
                "success": True,
                "already_applied": bool(apply_res.already_applied or already_applied),
                "steam_id": steam_id,
                "amount": int(amount_i),
                "balance": int(apply_res.balance),
            }
        )

    except ValueError as e:
        if str(e) == "INSUFFICIENT_FUNDS":
            return jsonify({"success": False, "error": "INSUFFICIENT_FUNDS"}), 409
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_credit: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/integrations/keys", methods=["GET"])
@require_auth
@require_admin
def shop_admin_list_integration_keys():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            _ensure_integration_tables(conn)
            cur = conn.execute(
                """
                SELECT key_id, name, enabled, created_at, last_used_at
                FROM integration_keys
                ORDER BY datetime(created_at) DESC
                """
            )
            rows = cur.fetchall() or []

        items = []
        for r in rows:
            items.append(
                {
                    "key_id": str(r["key_id"]),
                    "name": str(r["name"]),
                    "enabled": int(r["enabled"]),
                    "created_at": str(r["created_at"] or ""),
                    "last_used_at": str(r["last_used_at"] or "") if r["last_used_at"] else None,
                }
            )

        return jsonify({"success": True, "data": {"items": items, "count": len(items)}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/integrations/keys", methods=["POST"])
@require_auth
@require_admin
def shop_admin_create_integration_key():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        name = str((payload.get("name") or "discord-bot")).strip() or "discord-bot"
        key_plain = str((payload.get("key") or "")).strip()
        if len(key_plain) < 32:
            return jsonify({"success": False, "error": "key must be at least 32 characters"}), 400

        key_hash = _integration_key_hash(key_plain)
        new_key_id = str(uuid4())


        with ssm_tx(ssm_db_path) as conn:
            _ensure_integration_tables(conn)
            conn.execute("UPDATE integration_keys SET enabled = 0")
            try:
                conn.execute(
                    """
                    INSERT INTO integration_keys(key_id, name, key_hash, enabled)
                    VALUES(?, ?, ?, 1)
                    """,
                    (str(new_key_id), str(name), str(key_hash)),
                )
            except sqlite3.IntegrityError:
                return jsonify({"success": False, "error": "KEY_ALREADY_EXISTS"}), 409

        return jsonify({"success": True, "data": {"key_id": new_key_id, "name": name, "enabled": 1}}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/integrations/keys/<key_id>", methods=["PATCH"])
@require_auth
@require_admin
def shop_admin_patch_integration_key(key_id: str):
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        if "enabled" not in payload:
            return jsonify({"success": False, "error": "enabled is required"}), 400
        try:
            enabled = int(payload.get("enabled"))
        except Exception:
            return jsonify({"success": False, "error": "enabled must be integer"}), 400
        if enabled not in (0, 1):
            return jsonify({"success": False, "error": "enabled must be 0 or 1"}), 400


        with ssm_tx(ssm_db_path) as conn:
            _ensure_integration_tables(conn)
            cur = conn.execute(
                "SELECT 1 FROM integration_keys WHERE key_id = ? LIMIT 1",
                (str(key_id),),
            )
            if not cur.fetchone():
                return jsonify({"success": False, "error": "KEY_NOT_FOUND"}), 404

            if enabled == 1:
                conn.execute("UPDATE integration_keys SET enabled = 0")
            conn.execute(
                "UPDATE integration_keys SET enabled = ? WHERE key_id = ?",
                (int(enabled), str(key_id)),
            )

        return jsonify({"success": True, "data": {"key_id": str(key_id), "enabled": int(enabled)}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/rewards/playtime-config", methods=["GET"])
@require_auth
@require_admin
def shop_admin_get_playtime_rewards_config():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        defaults = {
            "economy.playtime_reward.enabled": "0",
            "economy.playtime_reward.points_per_hour": "0",
            "economy.playtime_reward.max_hours_per_run": "0",
        }

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT key, value FROM app_config WHERE key IN (?, ?, ?)",
                (
                    "economy.playtime_reward.enabled",
                    "economy.playtime_reward.points_per_hour",
                    "economy.playtime_reward.max_hours_per_run",
                ),
            )
            rows = cur.fetchall()

        cfg: Dict[str, str] = dict(defaults)
        for k, v in rows:
            cfg[str(k)] = str(v)

        def _to_int(s: str, default: int) -> int:
            try:
                return int(str(s).strip())
            except Exception:
                return int(default)

        data = {
            "enabled": 1 if _to_int(cfg["economy.playtime_reward.enabled"], 0) == 1 else 0,
            "points_per_hour": _to_int(cfg["economy.playtime_reward.points_per_hour"], 0),
            "max_hours_per_run": _to_int(cfg["economy.playtime_reward.max_hours_per_run"], 0),
            "interval_minutes": 30,
            "baseline_mode": "lazy",
        }

        return jsonify({"success": True, "data": data})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/rewards/playtime-rules", methods=["GET"])
@require_auth
@require_admin
def shop_admin_list_playtime_reward_rules():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        enabled_only = 1 if (request.args.get("enabled_only") in ("1", "true", "True")) else 0
        rewards = RewardsService(ssm_db_path, logger=logger)
        rules = rewards.list_playtime_rules(enabled_only=bool(enabled_only))
        items = [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "enabled": int(r.enabled),
                "exclusive": int(r.exclusive),
                "points_per_hour": int(r.points_per_hour),
                "max_hours_per_run": int(r.max_hours_per_run),
                "audience_type": r.audience_type,
            }
            for r in rules
        ]
        return jsonify({"success": True, "data": {"items": items, "count": len(items)}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/rewards/playtime-rules", methods=["POST"])
@require_auth
@require_admin
def shop_admin_create_playtime_reward_rule():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"success": False, "error": "name is required"}), 400

        try:
            enabled = int(payload.get("enabled", 0))
            exclusive = int(payload.get("exclusive", 0))
            points_per_hour = int(payload.get("points_per_hour", 0))
            max_hours_per_run = int(payload.get("max_hours_per_run", 0))
        except Exception:
            return jsonify({"success": False, "error": "enabled/points_per_hour/max_hours_per_run must be integers"}), 400

        audience_type = str(payload.get("audience_type", "all")).strip() or "all"
        if audience_type not in ("all", "list"):
            return jsonify({"success": False, "error": "audience_type must be 'all' or 'list'"}), 400
        if enabled not in (0, 1) or exclusive not in (0, 1) or points_per_hour < 0 or max_hours_per_run < 0:
            return jsonify({"success": False, "error": "invalid values"}), 400

        from uuid import uuid4

        rule_id = str(uuid4())
        rewards = RewardsService(ssm_db_path, logger=logger)
        rewards.upsert_playtime_rule(
            rule_id=rule_id,
            name=name,
            enabled=enabled,
            exclusive=exclusive,
            points_per_hour=points_per_hour,
            max_hours_per_run=max_hours_per_run,
            audience_type=audience_type,
        )
        return jsonify({"success": True, "data": {"rule_id": rule_id}}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/rewards/playtime-rules/<rule_id>", methods=["PATCH"])
@require_auth
@require_admin
def shop_admin_patch_playtime_reward_rule(rule_id: str):
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        rewards = RewardsService(ssm_db_path, logger=logger)

        # Carregar regra atual
        existing = next((r for r in rewards.list_playtime_rules(enabled_only=False) if r.rule_id == str(rule_id)), None)
        if not existing:
            return jsonify({"success": False, "error": "RULE_NOT_FOUND"}), 404

        name = (payload.get("name") if "name" in payload else existing.name) or ""
        name = str(name).strip()
        if not name:
            return jsonify({"success": False, "error": "name cannot be empty"}), 400

        try:
            enabled = int(payload.get("enabled", existing.enabled))
            exclusive = int(payload.get("exclusive", existing.exclusive))
            points_per_hour = int(payload.get("points_per_hour", existing.points_per_hour))
            max_hours_per_run = int(payload.get("max_hours_per_run", existing.max_hours_per_run))
        except Exception:
            return jsonify({"success": False, "error": "enabled/points_per_hour/max_hours_per_run must be integers"}), 400

        audience_type = str(payload.get("audience_type", existing.audience_type)).strip() or "all"
        if audience_type not in ("all", "list"):
            return jsonify({"success": False, "error": "audience_type must be 'all' or 'list'"}), 400
        if enabled not in (0, 1) or exclusive not in (0, 1) or points_per_hour < 0 or max_hours_per_run < 0:
            return jsonify({"success": False, "error": "invalid values"}), 400

        rewards.upsert_playtime_rule(
            rule_id=str(rule_id),
            name=name,
            enabled=int(enabled),
            exclusive=int(exclusive),
            points_per_hour=int(points_per_hour),
            max_hours_per_run=int(max_hours_per_run),
            audience_type=audience_type,
        )

        return jsonify({"success": True, "data": {"rule_id": str(rule_id)}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/rewards/playtime-rules/<rule_id>", methods=["DELETE"])
@require_auth
@require_admin
def shop_admin_delete_playtime_reward_rule(rule_id: str):
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        rewards = RewardsService(ssm_db_path, logger=logger)
        rewards.delete_playtime_rule(str(rule_id))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/rewards/playtime-rules/<rule_id>/targets", methods=["GET"])
@require_auth
@require_admin
def shop_admin_list_playtime_reward_rule_targets(rule_id: str):
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        rewards = RewardsService(ssm_db_path, logger=logger)
        targets = rewards.list_playtime_rule_targets(str(rule_id))
        return jsonify({"success": True, "data": {"rule_id": str(rule_id), "items": targets, "count": len(targets)}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/rewards/playtime-rules/<rule_id>/targets", methods=["POST"])
@require_auth
@require_admin
def shop_admin_add_playtime_reward_rule_target(rule_id: str):
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        steam_id = (payload.get("steam_id") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "steam_id is required"}), 400

        rewards = RewardsService(ssm_db_path, logger=logger)

        # Regra de negócio:
        # - Ao promover para VIP, remover do Padrão se estiver lá (não-bloqueante)

        with ssm_tx(ssm_db_path) as conn:
            rewards._ensure_playtime_rules_schema(conn)
            cur = conn.execute(
                "SELECT name FROM playtime_reward_rules WHERE rule_id = ? LIMIT 1",
                (str(rule_id),),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"success": False, "error": "RULE_NOT_FOUND"}), 404
            rule_name = str(row[0])

            pcur = conn.execute(
                "SELECT 1 FROM players WHERE steam_id = ? LIMIT 1",
                (str(steam_id),),
            )
            if not pcur.fetchone():
                return jsonify({"success": False, "error": "PLAYER_NOT_FOUND"}), 400

            try:
                rewards.add_playtime_rule_target_conn(str(rule_id), str(steam_id), conn)
            except sqlite3.IntegrityError as ie:
                return jsonify({"success": False, "error": str(ie)}), 400

            # Se promovendo para VIP, remover do Padrão (não-bloqueante)
            if rule_name == "VIP":
                try:
                    default_rule_id = rewards.get_playtime_rule_id_by_name("Padrão", conn=conn)
                    if default_rule_id:
                        rewards.remove_playtime_rule_target_conn(str(default_rule_id), str(steam_id), conn)
                except Exception:
                    pass

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/rewards/playtime-rules/<rule_id>/targets/<steam_id>", methods=["DELETE"])
@require_auth
@require_admin
def shop_admin_remove_playtime_reward_rule_target(rule_id: str, steam_id: str):
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        rewards = RewardsService(ssm_db_path, logger=logger)
        rewards.remove_playtime_rule_target(str(rule_id), str(steam_id))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/rewards/playtime-config", methods=["PATCH"])
@require_auth
@require_admin
def shop_admin_patch_playtime_rewards_config():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}

        allowed_keys = {
            "enabled": "economy.playtime_reward.enabled",
            "points_per_hour": "economy.playtime_reward.points_per_hour",
            "max_hours_per_run": "economy.playtime_reward.max_hours_per_run",
        }

        updates: Dict[str, str] = {}
        for api_key, cfg_key in allowed_keys.items():
            if api_key not in payload:
                continue
            val = payload.get(api_key)
            try:
                val_i = int(val)
            except Exception:
                return (
                    jsonify({"success": False, "error": f"{api_key} must be an integer"}),
                    400,
                )

            if api_key == "enabled" and val_i not in (0, 1):
                return jsonify({"success": False, "error": "enabled must be 0 or 1"}), 400
            if api_key in ("points_per_hour", "max_hours_per_run") and val_i < 0:
                return (
                    jsonify({"success": False, "error": f"{api_key} must be >= 0"}),
                    400,
                )

            updates[str(cfg_key)] = str(int(val_i))

        if not updates:
            return jsonify({"success": False, "error": "No valid fields to update"}), 400

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            cur = conn.cursor()
            for k, v in updates.items():
                cur.execute(
                    """
                    INSERT INTO app_config(key, value, updated_at)
                    VALUES(?, ?, datetime('now'))
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = datetime('now')
                    """,
                    (str(k), str(v)),
                )
            conn.commit()

        return shop_admin_get_playtime_rewards_config()

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/scanner-chest", methods=["POST"])
@require_auth
@require_admin
def shop_admin_set_scanner_chest():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        chest_id = payload.get("chest_id")
        if chest_id is None:
            return jsonify({"success": False, "error": "chest_id is required"}), 400
        try:
            chest_id_i = int(chest_id)
        except Exception:
            return jsonify({"success": False, "error": "chest_id must be integer"}), 400

        scum_db_path, scum_error = _get_scum_database_path()
        if scum_error:
            return jsonify({"success": False, "error": scum_error}), 500

        scanner = ShopScannerService(ssm_db_path, scum_db_path, logger=logger)
        scanner.set_scanner_chest_id(chest_id_i)
        return jsonify({"success": True, "chest_id": chest_id_i})
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_set_scanner_chest: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/scanner/sync", methods=["POST"])
@require_auth
@require_admin
def shop_admin_scanner_sync():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        scum_db_path, scum_error = _get_scum_database_path()
        if scum_error:
            return jsonify({"success": False, "error": scum_error}), 500

        scanner = ShopScannerService(ssm_db_path, scum_db_path, logger=logger)
        chest_id = scanner.get_scanner_chest_id()
        if chest_id is None:
            return jsonify({"success": False, "error": "SCANNER_CHEST_NOT_CONFIGURED"}), 400

        res = scanner.sync_catalog_from_scanner(chest_id)
        return jsonify(
            {
                "success": True,
                "data": {
                    "chest_id": res.chest_id,
                    "discovered_setups": res.discovered_setups,
                    "created_catalog": res.created_catalog,
                },
            }
        )
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_scanner_sync: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/mailbox", methods=["POST"])
@require_auth
def shop_set_mailbox():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        scum_db_path, scum_error = _get_scum_database_path()
        if scum_error:
            return jsonify({"success": False, "error": scum_error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        steam_id = (
            payload.get("steam_id")
            or getattr(request, "current_user", {}).get("steam_id")
            or ""
        ).strip()
        chest_id = payload.get("chest_id")

        if not steam_id or chest_id is None:
            return jsonify({"success": False, "error": "steam_id and chest_id are required"}), 400
        try:
            chest_id_i = int(chest_id)
        except Exception:
            return jsonify({"success": False, "error": "chest_id must be integer"}), 400

        with scum_db_readonly_connection_strict(scum_db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM entity WHERE id = ?", (int(chest_id_i),))
            if not cur.fetchone():
                return jsonify({"success": False, "error": "CHEST_NOT_FOUND_SCUMDB"}), 404
            cur.execute(
                """
                SELECT 1 FROM entity_component
                WHERE entity_id = ? AND name = 'Inventory'
                LIMIT 1
                """,
                (int(chest_id_i),),
            )
            if not cur.fetchone():
                return jsonify({"success": False, "error": "CHEST_NO_INVENTORY"}), 409

        shop = ShopService(ssm_db_path, logger=logger)
        shop.upsert_mailbox(steam_id, chest_id_i)
        return jsonify(
            {
                "success": True,
                "message": "Mailbox atualizado. Entregas so aparecem apos restart.",
                "data": {"steam_id": steam_id, "chest_id": int(chest_id_i)},
            }
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_set_mailbox: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/mailbox", methods=["GET"])
@require_auth
def shop_list_mailboxes():
    """DEPRECATED: Mailbox feature disabled. Use /api/shop/admin/registered-players instead."""
    return jsonify({"success": False, "error": "MAILBOX_FEATURE_DISABLED"}), 410


@shop_bp.route("/api/shop/admin/registered-players", methods=["GET"])
@require_auth
@require_admin
def shop_list_registered_players():
    """Lista jogadores registrados (discord vinculado) para gestão de recompensas e VIP."""
    services = get_services()
    logger = getattr(services, 'logger', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        def _to_int(val, default: int) -> int:
            try:
                return int(val)
            except Exception:
                return int(default)

        limit = _to_int(request.args.get("limit", 100), 100)
        offset = _to_int(request.args.get("offset", 0), 0)
        search_query = request.args.get("q")
        if limit <= 0:
            limit = 100
        if limit > 1000:
            limit = 1000
        if offset < 0:
            offset = 0

        sort_by = request.args.get("sort_by", "discord_linked_at")
        sort_order = request.args.get("sort_order", "desc")
        if sort_by not in {"player_name", "steam_id", "discord_linked_at", "balance"}:
            sort_by = "discord_linked_at"
        if sort_order not in {"asc", "desc"}:
            sort_order = "desc"

        sort_col_map = {
            "player_name": "COALESCE(p.player_name, '') COLLATE NOCASE",
            "steam_id": "p.steam_id",
            "discord_linked_at": "p.discord_linked_at",
            "balance": "COALESCE(w.balance, 0)",
        }
        order_col = sort_col_map.get(sort_by, "p.discord_linked_at")

        where_clause = "WHERE p.discord_user_id IS NOT NULL"
        params = []
        if search_query:
            where_clause += " AND (p.player_name LIKE ? OR p.steam_id LIKE ?)"
            params = [f"%{search_query}%", f"%{search_query}%"]

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute(
                f"SELECT COUNT(*) AS total FROM players p {where_clause}",
                params
            )
            total = int(cur.fetchone()[0] or 0)

            cur.execute(
                f"""
                SELECT p.steam_id, p.player_name, p.discord_user_id,
                       p.discord_linked_at, p.created_at, COALESCE(w.balance, 0) AS balance
                FROM players p
                LEFT JOIN wallet w ON p.steam_id = w.steam_id
                {where_clause}
                ORDER BY {order_col} {sort_order.upper()}, p.steam_id ASC
                LIMIT ? OFFSET ?
                """,
                params + [int(limit), int(offset)],
            )
            rows = cur.fetchall()

        items = []
        for r in rows:
            items.append(
                {
                    "steam_id": str(r["steam_id"]),
                    "player_name": (str(r["player_name"]) if r["player_name"] is not None else None),
                    "discord_user_id": str(r["discord_user_id"]) if r["discord_user_id"] else None,
                    "discord_linked_at": str(r["discord_linked_at"]) if r["discord_linked_at"] else None,
                    "created_at": str(r["created_at"]) if r["created_at"] else None,
                    "balance": int(r["balance"]) if "balance" in r.keys() else 0,
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "items": items,
                    "total": int(total),
                    "count": len(items),
                    "limit": int(limit),
                    "offset": int(offset),
                },
            }
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_list_registered_players: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/orders", methods=["POST"])
@require_auth
def shop_create_order():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        steam_id = (
            payload.get("steam_id")
            or getattr(request, "current_user", {}).get("steam_id")
            or ""
        ).strip()
        items_raw = payload.get("items")

        # Verificar se o jogador está preso
        try:
            if getattr(services, 'squad_tk_jail_service', None) and services.squad_tk_jail_service.is_player_jailed(steam_id):
                return jsonify({"success": False, "error": "PLAYER_JAILED"}), 403
        except Exception as jail_check_err:
            if logger:
                logger.error(f"Erro ao verificar se jogador está preso no shop_create_order: {jail_check_err}")
        if not steam_id:
            return jsonify({"success": False, "error": "steam_id is required"}), 400
        if not isinstance(items_raw, list):
            return jsonify({"success": False, "error": "items must be a list"}), 400

        items: List[OrderCreateItem] = []
        for it in items_raw:
            if not isinstance(it, dict):
                continue
            if "code" not in it or "qty" not in it:
                continue
            items.append(OrderCreateItem(code=int(it["code"]), qty=int(it["qty"])))

        shop = ShopService(ssm_db_path, logger=logger)
        res = shop.create_order(steam_id, items)
        return jsonify(
            {
                "success": True,
                "data": {
                    "order_id": res.order_id,
                    "total_price": res.total_price,
                    "balance": res.balance,
                },
            }
        )
    except ValueError as e:
        code = str(e)
        if code == "INSUFFICIENT_FUNDS":
            return jsonify({"success": False, "error": "INSUFFICIENT_FUNDS"}), 409
        return jsonify({"success": False, "error": code}), 400
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_create_order: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/catalog", methods=["GET"])
@require_auth
def shop_get_catalog():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            cur = conn.cursor()
            # Buscar itens de catálogo normais (filtrando kits legados caso existam no catálogo)
            cur.execute(
                """
                SELECT
                    c.code,
                    c.setup,
                    COALESCE(NULLIF(TRIM(c.display_name), ''), c.setup) AS name,
                    o.price,
                    o.qty,
                    o.max_per_order,
                    o.max_per_day
                FROM shop_catalog c
                INNER JOIN shop_offer o ON o.code = c.code
                WHERE c.enabled = 1 AND o.enabled = 1 AND c.setup NOT LIKE 'KIT:%'
                ORDER BY c.code ASC
                """
            )
            rows = cur.fetchall() or []

            # Buscar kits ativos
            cur.execute(
                """
                SELECT
                    code,
                    kit_id,
                    name,
                    price
                FROM shop_kit
                WHERE enabled = 1
                ORDER BY code ASC
                """
            )
            kit_rows = cur.fetchall() or []

        items = []
        for row in rows:
            code, setup, name, price, qty, max_per_order, max_per_day = row
            items.append(
                {
                    "code": int(code),
                    "setup": str(setup),
                    "name": str(name),
                    "price": int(price or 0),
                    "qty": int(qty or 0),
                    "max_per_order": int(max_per_order) if max_per_order is not None else None,
                    "max_per_day": int(max_per_day) if max_per_day is not None else None,
                }
            )

        for row in kit_rows:
            code, kit_id, name, price = row
            items.append(
                {
                    "code": int(code),
                    "setup": f"KIT:{kit_id}",
                    "name": str(name),
                    "price": int(price or 0),
                    "qty": 1,
                    "max_per_order": 1,
                    "max_per_day": None,
                }
            )

        # Ordenar itens pelo código
        items.sort(key=lambda x: x["code"])

        return jsonify({"success": True, "data": {"items": items, "count": len(items)}})
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_get_catalog: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/catalog", methods=["GET"])
@require_auth
@require_admin
def shop_admin_get_catalog():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    c.code,
                    c.setup,
                    COALESCE(NULLIF(TRIM(c.display_name), ''), c.setup) AS name,
                    c.enabled AS catalog_enabled,
                    o.enabled AS offer_enabled,
                    o.price,
                    o.qty,
                    o.max_per_order,
                    o.max_per_day
                FROM shop_catalog c
                LEFT JOIN shop_offer o ON o.code = c.code
                WHERE c.setup NOT LIKE 'KIT:%'
                ORDER BY c.code ASC
                """
            )
            rows = cur.fetchall() or []

        items = []
        for row in rows:
            (
                code,
                setup,
                name,
                catalog_enabled,
                offer_enabled,
                price,
                qty,
                max_per_order,
                max_per_day,
            ) = row
            items.append(
                {
                    "code": int(code),
                    "setup": str(setup),
                    "name": str(name),
                    "catalog_enabled": bool(int(catalog_enabled or 0)),
                    "offer_enabled": bool(int(offer_enabled or 0)),
                    "price": int(price or 0),
                    "qty": int(qty or 0),
                    "max_per_order": int(max_per_order) if max_per_order is not None else None,
                    "max_per_day": int(max_per_day) if max_per_day is not None else None,
                }
            )

        return jsonify({"success": True, "data": {"items": items, "count": len(items)}})
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_get_catalog: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/bank-account/current", methods=["GET"])
@require_auth
@require_admin
def shop_admin_bank_account_current():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        steam_id = (request.args.get("steam_id") or "").strip()
        if not steam_id:
            return jsonify({"success": False, "error": "steam_id is required"}), 400

        row = None
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
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
                "steam_id": steam_id,
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
            "steam_id": steam_id,
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
        if logger:
            logger.error(f"Erro em shop_admin_bank_account_current: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/bank-accounts/current", methods=["GET"])
@require_auth
@require_admin
def shop_admin_bank_accounts_current_list():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        def _get_int_arg(name: str, default: int) -> int:
            raw = request.args.get(name)
            if raw is None:
                return default
            try:
                return int(raw)
            except Exception:
                return default

        limit = _get_int_arg("limit", 50)
        offset = _get_int_arg("offset", 0)
        if limit <= 0:
            limit = 50
        if limit > 200:
            limit = 200
        if offset < 0:
            offset = 0

        q = (request.args.get("q") or "").strip()
        where = []
        params = []

        if q:
            q_like = f"%{q}%"
            q_prefix = f"{q}%"
            where.append("(steam_id LIKE ? OR player_name LIKE ?)")
            params.extend([q_prefix, q_like])

        where_clause = f"WHERE {' AND '.join(where)}" if where else ""

        money_total_expr = "(CASE WHEN COALESCE(total_balance, 0) > 0 THEN COALESCE(total_balance, 0) ELSE COALESCE(money_balance, 0) + COALESCE(account_balance, 0) END)"

        rows = []
        total = 0
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            cur = conn.cursor()
            count_row = cur.execute(
                f"SELECT COUNT(*) FROM bank_accounts_current {where_clause}",
                tuple(params),
            ).fetchone()
            total = int((count_row[0] if count_row else 0) or 0)

            query = f"""
                SELECT
                    steam_id,
                    player_name,
                    account_number,
                    money_balance,
                    account_balance,
                    total_balance,
                    gold_balance,
                    last_transaction_ts,
                    source,
                    updated_at
                FROM bank_accounts_current
                {where_clause}
                ORDER BY {money_total_expr} DESC, COALESCE(gold_balance, 0) DESC, updated_at DESC, steam_id ASC
                LIMIT ? OFFSET ?
            """
            rows = cur.execute(query, tuple(params + [limit, offset])).fetchall() or []

        def _to_float(val):
            try:
                return float(val or 0.0)
            except Exception:
                return 0.0

        items = []
        for row in rows:
            (
                steam_id,
                player_name,
                account_number,
                money_balance,
                account_balance,
                total_balance,
                gold_balance,
                last_transaction_ts,
                source,
                updated_at,
            ) = row

            money_balance_f = _to_float(money_balance)
            account_balance_f = _to_float(account_balance)
            total_balance_f = _to_float(total_balance)
            gold_balance_f = _to_float(gold_balance)

            money_total = total_balance_f
            if money_total <= 0.0:
                money_total = money_balance_f + account_balance_f

            items.append(
                {
                    "steam_id": str(steam_id or ""),
                    "player_name": "" if player_name is None else str(player_name),
                    "account_number": None if account_number is None else str(account_number),
                    "balances": {
                        "money_in_hand": money_balance_f,
                        "money_in_bank": account_balance_f,
                        "money_total": money_total,
                        "gold": gold_balance_f,
                    },
                    "meta": {
                        "updated_at": updated_at,
                        "source": source,
                        "last_transaction_ts": last_transaction_ts,
                    },
                }
            )

        data = {
            "items": items,
            "count": len(items),
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(items)) < total,
        }
        if q:
            data["q"] = q

        return jsonify({"success": True, "data": data, "timestamp": time.time()}), 200
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_bank_accounts_current_list: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/catalog/<int:code>", methods=["PATCH"])
@require_auth
@require_admin
def shop_admin_patch_catalog_item(code: int):
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        _ensure_sqlite_wal(ssm_db_path)

        payload = request.get_json(force=True, silent=True) or {}

        def _as_bool(v):
            if v is None:
                return None
            if isinstance(v, bool):
                return bool(v)
            if isinstance(v, (int, float)):
                return bool(int(v))
            s = str(v).strip().lower()
            if s in ("1", "true", "yes", "y", "on"):
                return True
            if s in ("0", "false", "no", "n", "off"):
                return False
            raise ValueError("invalid boolean")

        def _as_int_or_none(v):
            if v is None:
                return None
            if isinstance(v, str) and not v.strip():
                return None
            return int(v)

        display_name = payload.get("display_name", None)
        catalog_enabled = payload.get("catalog_enabled", None)
        offer_enabled = payload.get("offer_enabled", None)
        price = payload.get("price", None)
        qty = payload.get("qty", None)
        max_per_order = payload.get("max_per_order", None)
        max_per_day = payload.get("max_per_day", None)

        if catalog_enabled is not None:
            catalog_enabled = 1 if _as_bool(catalog_enabled) else 0
        if offer_enabled is not None:
            offer_enabled = 1 if _as_bool(offer_enabled) else 0
        if price is not None:
            price = int(price)
            if price < 0:
                return jsonify({"success": False, "error": "price must be >= 0"}), 400
        if qty is not None:
            qty = int(qty)
            if qty < 0:
                return jsonify({"success": False, "error": "qty must be >= 0"}), 400
        if max_per_order is not None:
            max_per_order = _as_int_or_none(max_per_order)
            if max_per_order is not None and max_per_order < 0:
                return jsonify({"success": False, "error": "max_per_order must be >= 0 or null"}), 400
        if max_per_day is not None:
            max_per_day = _as_int_or_none(max_per_day)
            if max_per_day is not None and max_per_day < 0:
                return jsonify({"success": False, "error": "max_per_day must be >= 0 or null"}), 400

        if display_name is not None:
            display_name = str(display_name)

        def _write_txn():
            with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA busy_timeout = 30000")
                cur = conn.execute(
                    "SELECT code FROM shop_catalog WHERE code = ?",
                    (int(code),),
                )
                if not cur.fetchone():
                    conn.rollback()
                    return None

                if display_name is not None:
                    conn.execute(
                        "UPDATE shop_catalog SET display_name = ? WHERE code = ?",
                        (display_name, int(code)),
                    )
                if catalog_enabled is not None:
                    conn.execute(
                        "UPDATE shop_catalog SET enabled = ? WHERE code = ?",
                        (int(catalog_enabled), int(code)),
                    )

                if (
                    offer_enabled is not None
                    or price is not None
                    or qty is not None
                    or max_per_order is not None
                    or max_per_day is not None
                ):
                    conn.execute(
                        "INSERT OR IGNORE INTO shop_offer(code, qty, price, enabled) VALUES(?, 1, 0, 0)",
                        (int(code),),
                    )

                if offer_enabled is not None:
                    conn.execute(
                        "UPDATE shop_offer SET enabled = ? WHERE code = ?",
                        (int(offer_enabled), int(code)),
                    )
                if price is not None:
                    conn.execute(
                        "UPDATE shop_offer SET price = ? WHERE code = ?",
                        (int(price), int(code)),
                    )
                if qty is not None:
                    conn.execute(
                        "UPDATE shop_offer SET qty = ? WHERE code = ?",
                        (int(qty), int(code)),
                    )
                if max_per_order is not None:
                    conn.execute(
                        "UPDATE shop_offer SET max_per_order = ? WHERE code = ?",
                        (max_per_order, int(code)),
                    )
                if max_per_day is not None:
                    conn.execute(
                        "UPDATE shop_offer SET max_per_day = ? WHERE code = ?",
                        (max_per_day, int(code)),
                    )

                cur2 = conn.execute(
                    """
                    SELECT
                        c.code,
                        c.setup,
                        c.display_name,
                        c.enabled,
                        o.enabled,
                        o.price,
                        o.qty,
                        o.max_per_order,
                        o.max_per_day
                    FROM shop_catalog c
                    LEFT JOIN shop_offer o ON o.code = c.code
                    WHERE c.code = ?
                    """,
                    (int(code),),
                )
                row = cur2.fetchone()
                conn.commit()
                return row

        try:
            row = _submit_sqlite_write(_write_txn, timeout_seconds=20.0)
        except queue.Empty:
            return jsonify({"success": False, "error": "DATABASE_BUSY"}), 503
        except sqlite3.OperationalError as oe:
            msg = str(oe or "").lower()
            if "database is locked" in msg or "database locked" in msg:
                return jsonify({"success": False, "error": "DATABASE_BUSY"}), 503
            raise

        if not row:
            return jsonify({"success": False, "error": "CATALOG_ITEM_NOT_FOUND"}), 404

        (
            code_v,
            setup,
            name,
            catalog_enabled_v,
            offer_enabled_v,
            price_v,
            qty_v,
            max_per_order_v,
            max_per_day_v,
        ) = row

        item = {
            "code": int(code_v),
            "setup": str(setup),
            "name": str(name),
            "catalog_enabled": bool(int(catalog_enabled_v or 0)),
            "offer_enabled": bool(int(offer_enabled_v or 0)),
            "price": int(price_v or 0),
            "qty": int(qty_v or 0),
            "max_per_order": int(max_per_order_v) if max_per_order_v is not None else None,
            "max_per_day": int(max_per_day_v) if max_per_day_v is not None else None,
        }

        return jsonify({"success": True, "data": {"item": item}})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/catalog/import", methods=["POST"])
@require_auth
@require_admin
def shop_admin_import_catalog():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True)
        if payload is None:
            return jsonify({"success": False, "error": "INVALID_JSON"}), 400

        schema = payload.get("schema")
        if str(schema or "") != "shop_catalog_snapshot_v1":
            return jsonify({"success": False, "error": "INVALID_SCHEMA"}), 400

        items = payload.get("items")
        if not isinstance(items, list):
            return jsonify({"success": False, "error": "INVALID_ITEMS"}), 400

        mode = str(payload.get("mode") or request.args.get("mode") or "merge").strip().lower()
        if mode in ("", "merge"):
            mode = "merge"
        if mode != "merge":
            return jsonify({"success": False, "error": "UNSUPPORTED_MODE"}), 400

        dry_run_raw = payload.get("dry_run", None)
        if dry_run_raw is None:
            dry_run_raw = request.args.get("dry_run", None)
        dry_run = False
        if dry_run_raw is not None:
            if isinstance(dry_run_raw, bool):
                dry_run = bool(dry_run_raw)
            else:
                s = str(dry_run_raw).strip().lower()
                dry_run = s in ("1", "true", "yes", "y", "on")

        errors = []

        def _err(code_v, reason, field=None):
            e = {"code": int(code_v) if code_v is not None else None, "reason": str(reason)}
            if field is not None:
                e["field"] = str(field)
            errors.append(e)

        normalized = []
        seen_codes = set()
        seen_setups = set()

        for idx, it in enumerate(items):
            if not isinstance(it, dict):
                _err(None, "INVALID_ITEM", field=f"items[{idx}]")
                continue

            code_v = it.get("code", None)
            try:
                code_i = int(code_v)
            except Exception:
                _err(code_v, "INVALID_CODE")
                continue
            if code_i <= 0:
                _err(code_i, "INVALID_CODE")
                continue
            if code_i in seen_codes:
                _err(code_i, "DUPLICATE_CODE")
                continue
            seen_codes.add(code_i)

            setup = it.get("setup", None)
            setup_s = str(setup or "").strip()
            if not setup_s:
                _err(code_i, "INVALID_SETUP")
                continue
            if setup_s in seen_setups:
                _err(code_i, "DUPLICATE_SETUP")
                continue
            seen_setups.add(setup_s)

            display_name = it.get("display_name", None)
            display_name_s = "" if display_name is None else str(display_name)

            cat_enabled = it.get("catalog_enabled", None)
            if not isinstance(cat_enabled, bool):
                _err(code_i, "INVALID_CATALOG_ENABLED", field="catalog_enabled")
                continue

            offer_enabled = it.get("offer_enabled", None)
            if not isinstance(offer_enabled, bool):
                _err(code_i, "INVALID_OFFER_ENABLED", field="offer_enabled")
                continue

            price = it.get("price", None)
            try:
                price_i = int(price)
            except Exception:
                _err(code_i, "INVALID_PRICE", field="price")
                continue
            if price_i < 0:
                _err(code_i, "INVALID_PRICE", field="price")
                continue

            qty = it.get("qty", None)
            try:
                qty_i = int(qty)
            except Exception:
                _err(code_i, "INVALID_QTY", field="qty")
                continue
            if qty_i < 1:
                _err(code_i, "INVALID_QTY", field="qty")
                continue

            mpo = it.get("max_per_order", None)
            if mpo is not None:
                try:
                    mpo = int(mpo)
                except Exception:
                    _err(code_i, "INVALID_MAX_PER_ORDER", field="max_per_order")
                    continue
                if mpo < 0:
                    _err(code_i, "INVALID_MAX_PER_ORDER", field="max_per_order")
                    continue

            mpd = it.get("max_per_day", None)
            if mpd is not None:
                try:
                    mpd = int(mpd)
                except Exception:
                    _err(code_i, "INVALID_MAX_PER_DAY", field="max_per_day")
                    continue
                if mpd < 0:
                    _err(code_i, "INVALID_MAX_PER_DAY", field="max_per_day")
                    continue

            normalized.append(
                {
                    "code": int(code_i),
                    "setup": setup_s,
                    "display_name": display_name_s,
                    "catalog_enabled": bool(cat_enabled),
                    "offer_enabled": bool(offer_enabled),
                    "price": int(price_i),
                    "qty": int(qty_i),
                    "max_per_order": mpo,
                    "max_per_day": mpd,
                }
            )

        if errors:
            return jsonify({"success": False, "error": "VALIDATION_FAILED", "data": {"errors": errors}}), 400

        created = 0
        updated = 0

        # All-or-nothing: validate against DB first and either apply in a single transaction or dry-run.
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn_ro:
            conn_ro.execute("PRAGMA foreign_keys = ON")
            # Load existing codes -> setup
            existing = {}
            for code_i, setup_s in conn_ro.execute("SELECT code, setup FROM shop_catalog"):
                existing[int(code_i)] = str(setup_s)

            # Load existing setups -> code
            setup_to_code = {}
            for code_i, setup_s in conn_ro.execute("SELECT code, setup FROM shop_catalog"):
                setup_to_code[str(setup_s)] = int(code_i)

        for it in normalized:
            code_i = int(it["code"])
            setup_s = str(it["setup"])

            if code_i in existing:
                # For safety: do not allow changing setup for an existing code.
                if str(existing.get(code_i)) != setup_s:
                    _err(code_i, "SETUP_MISMATCH")
                    continue
                updated += 1
            else:
                other_code = setup_to_code.get(setup_s)
                if other_code is not None and int(other_code) != code_i:
                    _err(code_i, "SETUP_ALREADY_USED")
                    continue
                created += 1

        if errors:
            return jsonify({"success": False, "error": "CONFLICT", "data": {"created": created, "updated": updated, "ignored": 0, "errors": errors}}), 409

        if dry_run:
            return jsonify({"success": True, "data": {"created": created, "updated": updated, "ignored": 0, "errors": []}})


        with ssm_tx(ssm_db_path) as conn:
            for it in normalized:
                code_i = int(it["code"])
                setup_s = str(it["setup"])
                display_name_s = str(it["display_name"])
                catalog_enabled_i = 1 if bool(it["catalog_enabled"]) else 0
                offer_enabled_i = 1 if bool(it["offer_enabled"]) else 0
                price_i = int(it["price"])
                qty_i = int(it["qty"])
                mpo = it["max_per_order"]
                mpd = it["max_per_day"]

                conn.execute(
                    """
                    INSERT INTO shop_catalog(code, setup, display_name, enabled, created_at, updated_at)
                    VALUES(?, ?, ?, ?, datetime('now'), datetime('now'))
                    ON CONFLICT(code) DO UPDATE SET
                        display_name=excluded.display_name,
                        enabled=excluded.enabled,
                        updated_at=datetime('now')
                    """,
                    (int(code_i), setup_s, display_name_s, int(catalog_enabled_i)),
                )

                conn.execute(
                    """
                    INSERT INTO shop_offer(code, qty, price, enabled, max_per_order, max_per_day)
                    VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET
                        qty=excluded.qty,
                        price=excluded.price,
                        enabled=excluded.enabled,
                        max_per_order=excluded.max_per_order,
                        max_per_day=excluded.max_per_day
                    """,
                    (
                        int(code_i),
                        int(qty_i),
                        int(price_i),
                        int(offer_enabled_i),
                        mpo,
                        mpd,
                    ),
                )

        return jsonify({"success": True, "data": {"created": created, "updated": updated, "ignored": 0, "errors": []}})

    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_import_catalog: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/catalog/clear", methods=["POST"])
@require_auth
@require_admin
def shop_admin_clear_catalog():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        confirm = str(payload.get("confirm", "")).strip()
        if confirm != "DELETE_ALL_CATALOG":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "CONFIRMATION_REQUIRED",
                        "message": "To clear catalog, send {confirm: 'DELETE_ALL_CATALOG'}.",
                    }
                ),
                400,
            )

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            offer_before = int(
                (conn.execute("SELECT COUNT(1) FROM shop_offer").fetchone() or [0])[0]
            )
            catalog_before = int(
                (conn.execute("SELECT COUNT(1) FROM shop_catalog").fetchone() or [0])[0]
            )

            conn.execute("DELETE FROM shop_offer")
            conn.execute("DELETE FROM shop_catalog")

        return jsonify(
            {
                "success": True,
                "data": {
                    "deleted": {
                        "shop_offer": offer_before,
                        "shop_catalog": catalog_before,
                    }
                },
            }
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_clear_catalog: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/orders/<order_id>/retry", methods=["POST"])
@require_auth
@require_admin
def shop_retry_order(order_id: str):
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        shop = ShopService(ssm_db_path, logger=logger)
        changed = shop.request_retry(order_id)
        return jsonify(
            {"success": True, "retry_requested": bool(changed), "order_id": order_id}
        )
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_retry_order: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/delivery/run", methods=["POST"])
@require_auth
@require_admin
def shop_delivery_run():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        scum_db_path, scum_error = _get_scum_database_path()
        if scum_error:
            return jsonify({"success": False, "error": scum_error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        limit = payload.get("limit", 50)
        try:
            limit_i = int(limit)
        except Exception:
            limit_i = 50
        if limit_i < 1:
            limit_i = 1
        if limit_i > 500:
            limit_i = 500

        svc = ShopDeliveryService(ssm_db_path, scum_db_path, logger=logger)
        res = svc.run_once(limit=limit_i)
        return jsonify(
            {
                "success": True,
                "data": {
                    "processed_orders": res.processed_orders,
                    "delivered_orders": res.delivered_orders,
                    "failed_orders": res.failed_orders,
                },
            }
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_delivery_run: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/rewards/time-tick", methods=["POST"])
@require_auth
def shop_time_reward_tick():
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
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        steam_id = (
            payload.get("steam_id")
            or getattr(request, "current_user", {}).get("steam_id")
            or ""
        ).strip()
        if not steam_id:
            return jsonify({"success": False, "error": "steam_id is required"}), 400

        rewards = RewardsService(ssm_db_path, logger=logger)
        res = rewards.tick_time_reward(steam_id)
        return jsonify(
            {
                "success": True,
                "data": {
                    "applied": bool(res.applied),
                    "balance": int(res.balance),
                    "ref_id": res.ref_id,
                },
            }
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_time_reward_tick: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/catalog", methods=["POST"])
@require_auth
@require_admin
def shop_admin_create_catalog_item():
    services = get_services()
    logger = getattr(services, 'logger', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        
        setup = (payload.get("setup") or "").strip()
        if not setup:
            return jsonify({"success": False, "error": "Missing required field: setup"}), 400

        display_name = (payload.get("display_name") or "").strip() or setup
        
        try:
            price = int(payload.get("price", 0))
            if price < 0:
                return jsonify({"success": False, "error": "Price must be a non-negative integer"}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid price value"}), 400

        enabled_val = payload.get("enabled", True)
        enabled_i = 1 if (enabled_val in (True, 1, "1", "true", "True")) else 0

        qty_val = payload.get("qty", 1)
        try:
            qty_i = int(qty_val)
            if qty_i < 1:
                qty_i = 1
        except (ValueError, TypeError):
            qty_i = 1

        code = payload.get("code")
        
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            # Check if setup already exists in shop_catalog
            cur = conn.cursor()
            cur.execute("SELECT code FROM shop_catalog WHERE setup = ?", (setup,))
            if cur.fetchone():
                raise ValueError(f"Item/Vehicle with setup '{setup}' already exists in catalog")

            # Calculate next code if not provided
            if code is None:
                cur.execute("SELECT MAX(code) FROM shop_catalog")
                max_cat = cur.fetchone()[0] or 0

                cur.execute("SELECT MAX(code) FROM shop_offer")
                max_off = cur.fetchone()[0] or 0

                code_i = max(max_cat, max_off, 0) + 1
            else:
                try:
                    code_i = int(code)
                except (ValueError, TypeError):
                    raise ValueError("Invalid code value")

                # Check if code already exists in catalog
                cur.execute("SELECT 1 FROM shop_catalog WHERE code = ? LIMIT 1", (code_i,))
                if cur.fetchone():
                    raise ValueError(f"Catalog code {code_i} already exists")

            # Insert into shop_catalog
            conn.execute(
                """
                INSERT INTO shop_catalog (code, setup, display_name, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                (code_i, setup, display_name, enabled_i)
            )

            # Insert into shop_offer
            conn.execute(
                """
                INSERT INTO shop_offer (code, qty, price, enabled, max_per_order, max_per_day)
                VALUES (?, ?, ?, ?, NULL, NULL)
                """,
                (code_i, qty_i, price, enabled_i)
            )
            # commit() automático pelo DatabaseConnector ao sair do with sem erro

        return jsonify({
            "success": True,
            "data": {
                "code": code_i,
                "setup": setup,
                "display_name": display_name,
                "price": price,
                "qty": qty_i,
                "enabled": bool(enabled_i)
            }
        }), 201

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_create_catalog_item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/catalog/<int:code>", methods=["PUT", "PATCH"])
@require_auth
@require_admin
def shop_admin_update_catalog_item(code):
    services = get_services()
    logger = getattr(services, 'logger', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        
        setup = payload.get("setup")
        if setup is not None:
            setup = setup.strip()
        display_name = payload.get("display_name")
        if display_name is not None:
            display_name = display_name.strip()
            
        price = payload.get("price")
        qty = payload.get("qty")
        enabled_val = payload.get("enabled")

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()
            # Verificar se o item existe
            cur.execute("SELECT 1 FROM shop_catalog WHERE code = ? LIMIT 1", (code,))
            if not cur.fetchone():
                return jsonify({"success": False, "error": f"Item/Vehicle with code {code} not found in catalog"}), 404

            # Atualizar shop_catalog
            updates_catalog = []
            params_catalog = []
            if setup is not None:
                updates_catalog.append("setup = ?")
                params_catalog.append(setup)
            if display_name is not None:
                updates_catalog.append("display_name = ?")
                params_catalog.append(display_name)
            if enabled_val is not None:
                enabled_i = 1 if (enabled_val in (True, 1, "1", "true", "True")) else 0
                updates_catalog.append("enabled = ?")
                params_catalog.append(enabled_i)
            
            if updates_catalog:
                updates_catalog.append("updated_at = datetime('now')")
                sql_cat = f"UPDATE shop_catalog SET {', '.join(updates_catalog)} WHERE code = ?"
                params_catalog.append(code)
                conn.execute(sql_cat, tuple(params_catalog))

            # Atualizar shop_offer
            updates_offer = []
            params_offer = []
            if price is not None:
                try:
                    price_i = int(price)
                    if price_i < 0:
                        return jsonify({"success": False, "error": "Price must be a non-negative integer"}), 400
                except (ValueError, TypeError):
                    return jsonify({"success": False, "error": "Invalid price value"}), 400
                updates_offer.append("price = ?")
                params_offer.append(price_i)
            if qty is not None:
                try:
                    qty_i = int(qty)
                    if qty_i < 1:
                        qty_i = 1
                except (ValueError, TypeError):
                    qty_i = 1
                updates_offer.append("qty = ?")
                params_offer.append(qty_i)
            if enabled_val is not None:
                enabled_i = 1 if (enabled_val in (True, 1, "1", "true", "True")) else 0
                updates_offer.append("enabled = ?")
                params_offer.append(enabled_i)

            if updates_offer:
                sql_off = f"UPDATE shop_offer SET {', '.join(updates_offer)} WHERE code = ?"
                params_offer.append(code)
                conn.execute(sql_off, tuple(params_offer))

            # Buscar dados atualizados para retornar
            cur.execute(
                """
                SELECT c.setup, c.display_name, o.price, o.qty, c.enabled
                FROM shop_catalog c
                JOIN shop_offer o ON c.code = o.code
                WHERE c.code = ?
                """,
                (code,)
            )
            row = cur.fetchone()

        if row:
            return jsonify({
                "success": True,
                "data": {
                    "code": code,
                    "setup": row[0],
                    "display_name": row[1],
                    "price": row[2],
                    "qty": row[3],
                    "enabled": bool(row[4])
                }
            }), 200
        else:
            return jsonify({"success": False, "error": "Failed to retrieve updated catalog item"}), 500

    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_update_catalog_item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/catalog/<int:code>", methods=["DELETE"])
@require_auth
@require_admin
def shop_admin_delete_catalog_item(code):
    services = get_services()
    logger = getattr(services, 'logger', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()
            # Verificar se o item existe
            cur.execute("SELECT 1 FROM shop_catalog WHERE code = ? LIMIT 1", (code,))
            if not cur.fetchone():
                return jsonify({"success": False, "error": f"Item/Vehicle with code {code} not found in catalog"}), 404

            # Deletar do catálogo e da oferta
            conn.execute("DELETE FROM shop_catalog WHERE code = ?", (code,))
            conn.execute("DELETE FROM shop_offer WHERE code = ?", (code,))

        return jsonify({"success": True, "message": f"Item/Vehicle with code {code} successfully deleted from catalog"}), 200

    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_delete_catalog_item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/kits", methods=["GET"])
@require_auth
@require_admin
def shop_admin_list_kits():
    services = get_services()
    logger = getattr(services, 'logger', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        import sqlite3
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 
                    kit_id, code, name, price, enabled, only_once, auto_deliver_on_register, created_at, updated_at
                FROM shop_kit
                ORDER BY name ASC
                """
            )
            kits = [dict(r) for r in cur.fetchall()]

            for kit in kits:
                cur.execute(
                    "SELECT setup, qty FROM shop_kit_item WHERE kit_id = ? ORDER BY id ASC",
                    (kit["kit_id"],)
                )
                kit["items"] = [dict(r) for r in cur.fetchall()]

        return jsonify({"success": True, "data": kits}), 200

    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_list_kits: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/kits", methods=["POST"])
@require_auth
@require_admin
def shop_admin_save_kit():
    services = get_services()
    logger = getattr(services, 'logger', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        kit_id = (payload.get("kit_id") or "").strip()
        code = payload.get("code")
        name = (payload.get("name") or "").strip()
        items = payload.get("items") or []
        only_once_val = payload.get("only_once", 0)
        price_val = payload.get("price", 0)
        enabled_val = payload.get("enabled", True)
        auto_deliver_val = payload.get("auto_deliver_on_register", 0)

        if not kit_id:
            return jsonify({"success": False, "error": "Missing required field: kit_id"}), 400
        if code is None:
            return jsonify({"success": False, "error": "Missing required field: code"}), 400
        if not name:
            return jsonify({"success": False, "error": "Missing required field: name"}), 400
        if not isinstance(items, list):
            return jsonify({"success": False, "error": "items must be a list"}), 400

        try:
            code_i = int(code)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "code must be an integer"}), 400

        try:
            price_i = int(price_val)
            if price_i < 0:
                return jsonify({"success": False, "error": "price must be a non-negative integer"}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "price must be an integer"}), 400

        enabled_i = 1 if (enabled_val in (True, 1, "1", "true", "True")) else 0
        auto_deliver_i = 1 if (auto_deliver_val in (True, 1, "1", "true", "True")) else 0
        only_once_i = 1 if (only_once_val in (True, 1, "1", "true", "True") or auto_deliver_i == 1) else 0

        for it in items:
            if not isinstance(it, dict) or "setup" not in it or "qty" not in it:
                return jsonify({"success": False, "error": "Each item must have 'setup' and 'qty'"}), 400
            try:
                qty_i = int(it["qty"])
                if qty_i < 1:
                    return jsonify({"success": False, "error": "Item qty must be at least 1"}), 400
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Item qty must be an integer"}), 400

        import sqlite3
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()

            # Se for kit de entrega automática no registro, desativar outros kits
            if auto_deliver_i == 1:
                conn.execute(
                    "UPDATE shop_kit SET auto_deliver_on_register = 0 WHERE kit_id != ?",
                    (kit_id,)
                )

            # Insert/replace kit
            conn.execute(
                """
                INSERT OR REPLACE INTO shop_kit (kit_id, code, name, price, enabled, only_once, auto_deliver_on_register, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (kit_id, code_i, name, price_i, enabled_i, only_once_i, auto_deliver_i)
            )

            conn.execute("DELETE FROM shop_kit_item WHERE kit_id = ?", (kit_id,))

            for it in items:
                conn.execute(
                    """
                    INSERT INTO shop_kit_item (kit_id, setup, qty)
                    VALUES (?, ?, ?)
                    """,
                    (kit_id, str(it["setup"]).strip(), int(it["qty"]))
                )

        return jsonify({"success": True, "message": f"Kit '{name}' saved successfully."}), 200

    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_save_kit: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/kits/<kit_id>", methods=["GET"])
@require_auth
@require_admin
def shop_admin_get_kit(kit_id):
    services = get_services()
    logger = getattr(services, 'logger', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        import sqlite3
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 
                    kit_id, code, name, price, enabled, only_once, auto_deliver_on_register, created_at, updated_at
                FROM shop_kit
                WHERE kit_id = ?
                """,
                (kit_id,)
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"success": False, "error": f"Kit with ID '{kit_id}' not found"}), 404

            kit = dict(row)
            cur.execute(
                "SELECT setup, qty FROM shop_kit_item WHERE kit_id = ? ORDER BY id ASC",
                (kit_id,)
            )
            kit["items"] = [dict(r) for r in cur.fetchall()]

        return jsonify({"success": True, "data": kit}), 200

    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_get_kit: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/kits/<kit_id>", methods=["DELETE"])
@require_auth
@require_admin
def shop_admin_delete_kit(kit_id):
    services = get_services()
    logger = getattr(services, 'logger', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()
            cur.execute("SELECT code FROM shop_kit WHERE kit_id = ?", (kit_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"success": False, "error": f"Kit with ID '{kit_id}' not found"}), 404
            code = row[0]

            conn.execute("DELETE FROM shop_kit WHERE kit_id = ?", (kit_id,))
            conn.execute("DELETE FROM shop_kit_item WHERE kit_id = ?", (kit_id,))

        return jsonify({"success": True, "message": f"Kit '{kit_id}' successfully deleted"}), 200

    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_delete_kit: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/api/shop/admin/kits/scan", methods=["POST"])
@require_auth
@require_admin
def shop_admin_scan_and_create_kit():
    services = get_services()
    logger = getattr(services, 'logger', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        scum_db_path, scum_error = _get_scum_database_path()
        if scum_error:
            return jsonify({"success": False, "error": scum_error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        chest_id = payload.get("chest_id")
        kit_id = (payload.get("kit_id") or "").strip()
        name = (payload.get("name") or "").strip()
        price_val = payload.get("price", 0)
        enabled_val = payload.get("enabled", True)
        only_once_val = payload.get("only_once", 0)
        code = payload.get("code")
        auto_deliver_val = payload.get("auto_deliver_on_register", 0)

        if chest_id is None:
            return jsonify({"success": False, "error": "Missing required field: chest_id"}), 400
        if not kit_id:
            return jsonify({"success": False, "error": "Missing required field: kit_id"}), 400
        if not name:
            return jsonify({"success": False, "error": "Missing required field: name"}), 400

        try:
            chest_id_i = int(chest_id)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "chest_id must be an integer"}), 400

        try:
            price_i = int(price_val)
            if price_i < 0:
                return jsonify({"success": False, "error": "price must be a non-negative integer"}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "price must be an integer"}), 400

        enabled_i = 1 if (enabled_val in (True, 1, "1", "true", "True")) else 0
        auto_deliver_i = 1 if (auto_deliver_val in (True, 1, "1", "true", "True")) else 0
        only_once_i = 1 if (only_once_val in (True, 1, "1", "true", "True") or auto_deliver_i == 1) else 0

        # Scan the chest items with quantity
        from core.shop.scanner_service import ShopScannerService
        scanner = ShopScannerService(ssm_db_path, scum_db_path, logger=logger)
        items, scan_err = scanner.scan_scum_chest_items_with_qty(chest_id_i)
        if scan_err:
            return jsonify({"success": False, "error": scan_err}), 400
        if not items:
            return jsonify({"success": False, "error": "The scanned chest is empty"}), 400

        import sqlite3
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()

            # Define kit code
            if code is None:
                cur.execute("SELECT MAX(code) FROM shop_kit")
                max_kit = cur.fetchone()[0] or 0
                code_i = max_kit + 1
            else:
                try:
                    code_i = int(code)
                except (ValueError, TypeError):
                    return jsonify({"success": False, "error": "code must be an integer"}), 400

            # Se for kit de entrega automática no registro, desativar outros kits
            if auto_deliver_i == 1:
                conn.execute(
                    "UPDATE shop_kit SET auto_deliver_on_register = 0 WHERE kit_id != ?",
                    (kit_id,)
                )

            # Insert/replace kit
            conn.execute(
                """
                INSERT OR REPLACE INTO shop_kit (kit_id, code, name, price, enabled, only_once, auto_deliver_on_register, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (kit_id, code_i, name, price_i, enabled_i, only_once_i, auto_deliver_i)
            )

            # Clean old items
            conn.execute("DELETE FROM shop_kit_item WHERE kit_id = ?", (kit_id,))

            # Insert new items scanned
            for it in items:
                conn.execute(
                    """
                    INSERT INTO shop_kit_item (kit_id, setup, qty)
                    VALUES (?, ?, ?)
                    """,
                    (kit_id, str(it["setup"]).strip(), int(it["qty"]))
                )

        return jsonify({
            "success": True,
            "message": f"Kit '{name}' scanned from chest {chest_id_i} and created successfully.",
            "data": {
                "kit_id": kit_id,
                "code": code_i,
                "name": name,
                "price": price_i,
                "enabled": bool(enabled_i),
                "only_once": bool(only_once_i),
                "auto_deliver_on_register": bool(auto_deliver_i),
                "items": items
            }
        }), 201

    except Exception as e:
        if logger:
            logger.error(f"Erro em shop_admin_scan_and_create_kit: {e}")
        return jsonify({"success": False, "error": str(e)}), 500






