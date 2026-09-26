"""
Blueprint: vehicles
"""
from core.database.connector import DatabaseConnector

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac, queue, mimetypes
from uuid import uuid4
from functools import wraps
from core.auth.decorators import require_auth, require_admin
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import sqlite3
from .helpers import _get_ssm_database_path, _get_scum_database_path, _ensure_sqlite_wal
from utils.scum_templates_sync import merge_vehicle_templates_from_scum_db, reset_scum_templates_db
from utils.sqlite_queue import submit_sqlite_write as _submit_sqlite_write
from utils.integration_helpers import (
    is_valid_vehicle_asset_signature as _is_valid_vehicle_asset_signature,
    make_signed_vehicle_asset_url as _make_signed_vehicle_asset_url
)

vehicles_bp = Blueprint('vehicles', __name__)

@vehicles_bp.route("/api/vehicles/catalog", methods=["GET"])
@require_auth
def vehicles_get_catalog():
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    code,
                    setup,
                    display_name,
                    template_vehicle_entity_id,
                    price,
                    image_url
                FROM vehicle_catalog
                WHERE enabled = 1
                ORDER BY code ASC
                """
            )
            rows = cur.fetchall() or []

        items = []
        for row in rows:
            code, setup, display_name, template_vehicle_entity_id, price, image_url = row
            setup_s = "" if setup is None else str(setup)
            display_name_s = "" if display_name is None else str(display_name)
            name_s = display_name_s.strip() or setup_s.strip()
            image_url_s = "" if image_url is None else str(image_url)
            image_url_s = _make_signed_vehicle_asset_url(image_url_s) if image_url_s else ""
            items.append(
                {
                    "code": int(code),
                    "setup": setup_s,
                    "display_name": display_name_s,
                    "name": name_s,
                    "template_vehicle_entity_id": int(template_vehicle_entity_id),
                    "price": int(price or 0),
                    "image_url": image_url_s,
                }
            )

        return jsonify({"success": True, "data": {"items": items, "count": len(items)}})
    except Exception as e:
        if logger:
            logger.error(f"Erro em vehicles_get_catalog: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/admin/catalog", methods=["GET"])
@require_auth
@require_admin
def vehicles_admin_get_catalog():
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    code,
                    setup,
                    display_name,
                    template_vehicle_entity_id,
                    price,
                    enabled,
                    image_url
                FROM vehicle_catalog
                ORDER BY code ASC
                """
            )
            rows = cur.fetchall() or []

        items = []
        for row in rows:
            code, setup, display_name, template_vehicle_entity_id, price, enabled, image_url = row
            setup_s = "" if setup is None else str(setup)
            display_name_s = "" if display_name is None else str(display_name)
            name_s = display_name_s.strip() or setup_s.strip()
            image_url_s = "" if image_url is None else str(image_url)
            image_url_s = _make_signed_vehicle_asset_url(image_url_s) if image_url_s else ""
            items.append(
                {
                    "code": int(code),
                    "setup": setup_s,
                    "display_name": display_name_s,
                    "name": name_s,
                    "template_vehicle_entity_id": int(template_vehicle_entity_id),
                    "price": int(price or 0),
                    "enabled": bool(int(enabled or 0)),
                    "image_url": image_url_s,
                }
            )

        return jsonify({"success": True, "data": {"items": items, "count": len(items)}})
    except Exception as e:
        if logger:
            logger.error(f"Erro em vehicles_admin_get_catalog: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/admin/orders/retry", methods=["POST"])
@require_auth
@require_admin
def vehicles_admin_retry_orders():
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        payload = request.get_json(force=True, silent=True) or {}
        order_id = (payload.get("order_id") or "").strip() or None
        error_code = (payload.get("error_code") or "").strip() or None

        limit_raw = payload.get("limit", 200)
        try:
            limit_i = int(limit_raw)
        except Exception:
            limit_i = 200
        if limit_i < 1:
            limit_i = 1
        if limit_i > 1000:
            limit_i = 1000

        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            if order_id:
                cur = conn.execute(
                    """
                    UPDATE vehicle_order
                    SET status = 'pending',
                        next_attempt_at = NULL,
                        locked_by = NULL,
                        locked_at = NULL,
                        updated_at = datetime('now')
                    WHERE order_id = ?
                      AND status = 'failed'
                    """,
                    (str(order_id),),
                )
                updated = int(cur.rowcount or 0)
                return jsonify({"success": True, "data": {"updated": updated}})

            if error_code:
                cur = conn.execute(
                    """
                    UPDATE vehicle_order
                    SET status = 'pending',
                        next_attempt_at = NULL,
                        locked_by = NULL,
                        locked_at = NULL,
                        updated_at = datetime('now')
                    WHERE order_id IN (
                        SELECT order_id
                        FROM vehicle_order
                        WHERE status = 'failed'
                          AND error_code = ?
                        ORDER BY datetime(updated_at) DESC
                        LIMIT ?
                    )
                    """,
                    (str(error_code), int(limit_i)),
                )
                updated = int(cur.rowcount or 0)
                return jsonify(
                    {
                        "success": True,
                        "data": {"updated": updated, "error_code": str(error_code)},
                    }
                )

            # default: retry any failed
            cur = conn.execute(
                """
                UPDATE vehicle_order
                SET status = 'pending',
                    next_attempt_at = NULL,
                    locked_by = NULL,
                    locked_at = NULL,
                    updated_at = datetime('now')
                WHERE order_id IN (
                    SELECT order_id
                    FROM vehicle_order
                    WHERE status = 'failed'
                    ORDER BY datetime(updated_at) DESC
                    LIMIT ?
                )
                """,
                (int(limit_i),),
            )
            updated = int(cur.rowcount or 0)
            return jsonify({"success": True, "data": {"updated": updated}})

    except Exception as e:
        if logger:
            logger.error(f"Erro em vehicles_admin_retry_orders: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/admin/templates/sync", methods=["POST"])
@require_auth
@require_admin
def vehicles_admin_sync_templates():
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        if not server_manager:
            return (
                jsonify({"success": False, "error": "ServerManager not initialized"}),
                500,
            )

        payload = request.get_json(force=True, silent=True) or {}

        force = payload.get("force", False)
        force_b = False
        try:
            if isinstance(force, bool):
                force_b = bool(force)
            elif isinstance(force, (int, float)):
                force_b = bool(int(force))
            else:
                s = str(force).strip().lower()
                force_b = s in ("1", "true", "yes", "y", "on")
        except Exception:
            force_b = False

        service_running = False
        try:
            service_running = bool(server_manager._is_service_running())
        except Exception:
            service_running = False

        source_scum_db = str(payload.get("source_scum_db") or "").strip()
        if not source_scum_db or source_scum_db.strip().lower() in (
            "@config",
            "config",
            "default",
        ):
            try:
                if path_helper:
                    source_scum_db = str(path_helper.get_scum_db_path() or "").strip()
            except Exception:
                source_scum_db = ""

        ids_raw = payload.get("ids")
        if ids_raw is None:
            ids_raw = payload.get("template_vehicle_entity_ids")

        if not source_scum_db:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "source_scum_db is required (or use '@config' to use paths.scum_server.database)",
                    }
                ),
                400,
            )

        if not os.path.exists(source_scum_db):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "source_scum_db not found",
                        "source_scum_db": source_scum_db,
                    }
                ),
                400,
            )

        if not isinstance(ids_raw, list) or not ids_raw:
            return (
                jsonify({"success": False, "error": "ids (list) is required"}),
                400,
            )

        ids: List[int] = []
        invalid: List[Any] = []
        for v in ids_raw:
            try:
                ids.append(int(v))
            except Exception:
                invalid.append(v)

        if not ids:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No valid ids provided",
                        "invalid": invalid,
                    }
                ),
                400,
            )

        output_path = "data/templates/SCUM_TEMPLATES.db"
        snapshot_path = None
        used_snapshot = False

        try:
            if service_running and not force_b:
                try:
                    import uuid

                    os.makedirs("data/temp", exist_ok=True)
                    snapshot_path = os.path.join(
                        "data/temp",
                        f"SCUM.db.snapshot.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{uuid.uuid4().hex}.db",
                    )

                    # Create consistent snapshot via SQLite Online Backup API.
                    src = sqlite3.connect(source_scum_db, timeout=30.0)
                    try:
                        src.execute("PRAGMA busy_timeout = 30000")
                        dst = sqlite3.connect(snapshot_path, timeout=30.0)
                        try:
                            dst.execute("PRAGMA journal_mode = WAL")
                            src.backup(dst, pages=0, progress=None, sleep=0.05)
                            dst.commit()
                        finally:
                            try:
                                dst.close()
                            except Exception:
                                pass
                    finally:
                        try:
                            src.close()
                        except Exception:
                            pass

                    source_scum_db = snapshot_path
                    used_snapshot = True
                except Exception as snap_e:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Failed to create SCUM.db snapshot while server is running",
                                "code": "SCUMDB_SNAPSHOT_FAILED",
                                "details": str(snap_e),
                            }
                        ),
                        500,
                    )

            report = merge_vehicle_templates_from_scum_db(
                source_scum_db=source_scum_db,
                output_templates_db=output_path,
                template_vehicle_entity_ids=ids,
            )

            name_by_template_id: Dict[int, str] = {}
            try:
                synced_ids_for_name = [int(x) for x in (report.get("synced") or []) if x is not None]
            except Exception:
                synced_ids_for_name = []
            try:
                if synced_ids_for_name and os.path.exists(output_path):
                    with sqlite3.connect(os.path.abspath(output_path), timeout=10.0) as tconn:
                        tconn.execute("PRAGMA busy_timeout = 10000")
                        cols = []
                        try:
                            cols = [str(r[1]) for r in (tconn.execute("PRAGMA table_info('entity')").fetchall() or [])]
                        except Exception:
                            cols = []

                        idx_by_lower = {c.lower(): i for i, c in enumerate(cols)}
                        candidate_cols = [
                            "setup",
                            "display_name",
                            "name",
                            "class",
                            "class_name",
                            "entity_name",
                            "blueprint",
                        ]
                        candidate_idxs = [
                            idx_by_lower[c.lower()]
                            for c in candidate_cols
                            if c.lower() in idx_by_lower
                        ]

                        for tid_i in synced_ids_for_name:
                            try:
                                row = tconn.execute("SELECT * FROM entity WHERE id=?", (int(tid_i),)).fetchone()
                            except Exception:
                                row = None
                            if not row:
                                continue

                            resolved = ""
                            for idx in candidate_idxs:
                                try:
                                    v = row[idx]
                                except Exception:
                                    v = None
                                v_s = "" if v is None else str(v).strip()
                                if v_s:
                                    resolved = v_s
                                    break

                            if not resolved:
                                # Fallback heuristic: SCUM entity.setup is often around index 2
                                try:
                                    v = row[2]
                                except Exception:
                                    v = None
                                resolved = "" if v is None else str(v).strip()

                            if resolved:
                                name_by_template_id[int(tid_i)] = str(resolved)
            except Exception:
                name_by_template_id = {}

            catalog_report = None
            try:
                synced_ids = list(report.get("synced") or [])
                if synced_ids:
                    ssm_db_path, error = _get_ssm_database_path()
                    if error:
                        return jsonify({"success": False, "error": error}), 500

                    _ensure_sqlite_wal(ssm_db_path)

                    with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
                        conn.execute("PRAGMA busy_timeout = 30000")

                        tables = set(
                            [
                                r[0]
                                for r in (
                                    conn.execute(
                                        "SELECT name FROM sqlite_master WHERE type='table'"
                                    ).fetchall()
                                    or []
                                )
                            ]
                        )

                        inserted = 0
                        skipped = 0

                        if "vehicle_catalog" not in tables:
                            skipped = len(synced_ids)
                        else:
                            next_code = 1
                            try:
                                row = conn.execute(
                                    "SELECT COALESCE(MAX(code), 0) + 1 FROM vehicle_catalog"
                                ).fetchone()
                                if row and row[0] is not None:
                                    next_code = int(row[0])
                            except Exception:
                                next_code = 1

                            for tid in synced_ids:
                                try:
                                    tid_i = int(tid)
                                except Exception:
                                    continue

                                resolved_name = str(name_by_template_id.get(int(tid_i), "") or "").strip()
                                default_s = str(tid_i)
                                setup_s = resolved_name or default_s
                                display_s = resolved_name or default_s

                                try:
                                    r = conn.execute(
                                        "SELECT code, setup, display_name FROM vehicle_catalog WHERE template_vehicle_entity_id=? LIMIT 1",
                                        (int(tid_i),),
                                    ).fetchone()
                                    if r:
                                        code_existing = r[0]
                                        setup_existing = "" if r[1] is None else str(r[1]).strip()
                                        display_existing = "" if r[2] is None else str(r[2]).strip()

                                        # Only fill if still defaulted or empty (do not overwrite admin customization)
                                        need_setup = (not setup_existing) or (setup_existing == default_s)
                                        need_display = (not display_existing) or (display_existing == default_s)
                                        if (need_setup or need_display) and resolved_name:
                                            conn.execute(
                                                """
                                                UPDATE vehicle_catalog
                                                SET setup = CASE WHEN ? THEN ? ELSE setup END,
                                                    display_name = CASE WHEN ? THEN ? ELSE display_name END,
                                                    updated_at = datetime('now')
                                                WHERE code = ?
                                                """,
                                                (
                                                    1 if need_setup else 0,
                                                    str(setup_s),
                                                    1 if need_display else 0,
                                                    str(display_s),
                                                    int(code_existing),
                                                ),
                                            )
                                        skipped += 1
                                        continue
                                except Exception:
                                    pass

                                code_i = int(next_code)
                                next_code += 1
                                conn.execute(
                                    """
                                    INSERT INTO vehicle_catalog(
                                        code,
                                        setup,
                                        display_name,
                                        template_vehicle_entity_id,
                                        price,
                                        enabled,
                                        created_at,
                                        updated_at
                                    )
                                    VALUES(?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                                    """,
                                    (
                                        int(code_i),
                                        str(setup_s),
                                        str(display_s),
                                        int(tid_i),
                                        int(0),
                                        int(0),
                                    ),
                                )
                                inserted += 1

                        conn.commit()

                    catalog_report = {
                        "ssm_db_path": ssm_db_path,
                        "inserted": int(inserted),
                        "skipped": int(skipped),
                    }
            except Exception as ce:
                catalog_report = {"error": str(ce)}

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "report": report,
                        "invalid": invalid,
                        "catalog": catalog_report,
                        "diagnostics": {
                            "service_running": bool(service_running),
                            "used_snapshot": bool(used_snapshot),
                        },
                    },
                }
            )
        finally:
            if snapshot_path:
                try:
                    os.remove(snapshot_path)
                except Exception:
                    pass
                try:
                    for suffix in ("-wal", "-shm"):
                        p = f"{snapshot_path}{suffix}"
                        if os.path.exists(p):
                            try:
                                os.remove(p)
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception as e:
        if logger:
            logger.error(f"Erro em vehicles_admin_sync_templates: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/admin/templates/reset", methods=["POST"])
@require_auth
@require_admin
def vehicles_admin_reset_templates_db():
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        if not server_manager:
            return (
                jsonify({"success": False, "error": "ServerManager not initialized"}),
                500,
            )

        payload = request.get_json(force=True, silent=True) or {}
        force = payload.get("force", False)
        force_b = False
        try:
            if isinstance(force, bool):
                force_b = bool(force)
            elif isinstance(force, (int, float)):
                force_b = bool(int(force))
            else:
                s = str(force).strip().lower()
                force_b = s in ("1", "true", "yes", "y", "on")
        except Exception:
            force_b = False

        if server_manager._is_service_running() and not force_b:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "SCUMServer is running. Stop the server before resetting templates DB.",
                        "code": "SERVER_RUNNING",
                        "diagnostics": {
                            "received_payload_keys": sorted(list(payload.keys())),
                            "received_force": payload.get("force", None),
                            "interpreted_force": bool(force_b),
                            "hint": "Send JSON body: {\"force\": true} to bypass this block (endpoint only touches SCUM_TEMPLATES.db / SSM.db).",
                        },
                    }
                ),
                409,
            )

        make_backup = payload.get("make_backup", True)
        make_backup_b = True
        try:
            if isinstance(make_backup, bool):
                make_backup_b = bool(make_backup)
            elif isinstance(make_backup, (int, float)):
                make_backup_b = bool(int(make_backup))
            else:
                s = str(make_backup).strip().lower()
                make_backup_b = s in ("1", "true", "yes", "y", "on")
        except Exception:
            make_backup_b = True

        templates_path = "data/templates/SCUM_TEMPLATES.db"
        report = reset_scum_templates_db(
            templates_db_path=templates_path,
            make_backup=make_backup_b,
        )

        reset_catalog = payload.get("reset_catalog", True)
        reset_orders = payload.get("reset_orders", True)

        def _as_bool(v, default: bool = False) -> bool:
            if v is None:
                return default
            if isinstance(v, bool):
                return bool(v)
            if isinstance(v, (int, float)):
                return bool(int(v))
            s = str(v).strip().lower()
            if s in ("1", "true", "yes", "y", "on"):
                return True
            if s in ("0", "false", "no", "n", "off"):
                return False
            return default

        reset_catalog_b = _as_bool(reset_catalog, default=True)
        reset_orders_b = _as_bool(reset_orders, default=True)

        ssm_report = None
        if reset_catalog_b or reset_orders_b:
            ssm_db_path, error = _get_ssm_database_path()
            if error:
                return jsonify({"success": False, "error": error}), 500

            _ensure_sqlite_wal(ssm_db_path)

            with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
                conn.execute("PRAGMA busy_timeout = 30000")
                tables = set(
                    [
                        r[0]
                        for r in (
                            conn.execute(
                                "SELECT name FROM sqlite_master WHERE type='table'"
                            ).fetchall()
                            or []
                        )
                    ]
                )

                deleted: Dict[str, int] = {}
                if reset_catalog_b and "vehicle_catalog" in tables:
                    cur = conn.execute("DELETE FROM vehicle_catalog")
                    deleted["vehicle_catalog"] = int(cur.rowcount or 0)
                if reset_orders_b and "vehicle_order" in tables:
                    cur = conn.execute("DELETE FROM vehicle_order")
                    deleted["vehicle_order"] = int(cur.rowcount or 0)

                conn.commit()
                ssm_report = {
                    "ssm_db_path": ssm_db_path,
                    "deleted_rows": deleted,
                }

        return jsonify({"success": True, "data": {"report": report, "ssm": ssm_report}})

    except Exception as e:
        if logger:
            logger.error(f"Erro em vehicles_admin_reset_templates_db: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/admin/catalog/<int:code>", methods=["PATCH"])
@require_auth
@require_admin
def vehicles_admin_patch_catalog_item(code: int):
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
    log_processor = getattr(services, 'log_processor', None)
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

        display_name = payload.get("display_name", None)
        price = payload.get("price", None)
        enabled = payload.get("enabled", None)

        if display_name is not None:
            display_name = str(display_name)

        if price is not None:
            price = int(price)
            if price < 0:
                return jsonify({"success": False, "error": "price must be >= 0"}), 400

        if enabled is not None:
            enabled = 1 if _as_bool(enabled) else 0

        if display_name is None and price is None and enabled is None:
            return jsonify({"success": False, "error": "NO_CHANGES"}), 400

        def _write_txn():
            with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
                conn.execute("PRAGMA busy_timeout = 30000")
                cur = conn.execute(
                    "SELECT code FROM vehicle_catalog WHERE code = ?",
                    (int(code),),
                )
                if not cur.fetchone():
                    conn.rollback()
                    return None

                if display_name is not None:
                    conn.execute(
                        "UPDATE vehicle_catalog SET display_name = ?, updated_at = datetime('now') WHERE code = ?",
                        (display_name, int(code)),
                    )
                if price is not None:
                    conn.execute(
                        "UPDATE vehicle_catalog SET price = ?, updated_at = datetime('now') WHERE code = ?",
                        (int(price), int(code)),
                    )
                if enabled is not None:
                    conn.execute(
                        "UPDATE vehicle_catalog SET enabled = ?, updated_at = datetime('now') WHERE code = ?",
                        (int(enabled), int(code)),
                    )

                cur2 = conn.execute(
                    """
                    SELECT
                        code,
                        setup,
                        display_name,
                        template_vehicle_entity_id,
                        price,
                        enabled,
                        image_url
                    FROM vehicle_catalog
                    WHERE code = ?
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

        code_v, setup, display_name, template_vehicle_entity_id, price_v, enabled_v, image_url = row
        setup_s = "" if setup is None else str(setup)
        display_name_s = "" if display_name is None else str(display_name)
        name_s = display_name_s.strip() or setup_s.strip()
        image_url_s = "" if image_url is None else str(image_url)
        image_url_s = _make_signed_vehicle_asset_url(image_url_s) if image_url_s else ""
        item = {
            "code": int(code_v),
            "setup": setup_s,
            "display_name": display_name_s,
            "name": name_s,
            "template_vehicle_entity_id": int(template_vehicle_entity_id),
            "price": int(price_v or 0),
            "enabled": bool(int(enabled_v or 0)),
            "image_url": image_url_s,
        }

        return jsonify({"success": True, "data": {"item": item}})

    except ValueError as e:
        # invalid boolean
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        if logger:
            logger.error(f"Erro em vehicles_admin_patch_catalog_item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/admin/catalog/<int:code>/image", methods=["POST"])
@require_auth
@require_admin
def vehicles_admin_upload_catalog_image(code: int):
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        file = None
        try:
            file = request.files.get("file")
        except Exception:
            file = None
        if not file or not getattr(file, "filename", ""):
            return jsonify({"success": False, "error": "file is required"}), 400

        filename = secure_filename(str(file.filename))
        ext = os.path.splitext(filename)[1].lower().strip()
        if ext not in (".png", ".jpg", ".jpeg", ".webp"):
            return jsonify({"success": False, "error": "INVALID_FILE_TYPE"}), 400

        # limit: 5 MB
        try:
            file.stream.seek(0, os.SEEK_END)
            size = int(file.stream.tell() or 0)
            file.stream.seek(0)
            if size <= 0:
                return jsonify({"success": False, "error": "EMPTY_FILE"}), 400
            if size > 5 * 1024 * 1024:
                return jsonify({"success": False, "error": "FILE_TOO_LARGE"}), 413
        except Exception:
            pass

        out_dir = os.path.join("data", "imagens", "vehicle")
        os.makedirs(out_dir, exist_ok=True)
        out_name = f"vehicle_{int(code)}_{uuid4().hex}{ext}"
        out_path = os.path.join(out_dir, out_name)
        file.save(out_path)

        image_url = f"/api/vehicles/assets/{out_name}"

        _ensure_sqlite_wal(ssm_db_path)

        def _write_txn():
            with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
                conn.execute("PRAGMA busy_timeout = 30000")
                cur = conn.execute(
                    "SELECT code FROM vehicle_catalog WHERE code=?",
                    (int(code),),
                )
                if not cur.fetchone():
                    conn.rollback()
                    return None

                # Ensure image_url column exists (if db was created before migration ran)
                cur2 = conn.execute("PRAGMA table_info('vehicle_catalog')")
                cols = {str(r[1]) for r in (cur2.fetchall() or [])}
                if "image_url" not in cols:
                    try:
                        conn.execute("ALTER TABLE vehicle_catalog ADD COLUMN image_url TEXT")
                    except Exception:
                        pass

                conn.execute(
                    "UPDATE vehicle_catalog SET image_url = ?, updated_at = datetime('now') WHERE code = ?",
                    (str(image_url), int(code)),
                )
                row = conn.execute(
                    "SELECT code, image_url FROM vehicle_catalog WHERE code=?",
                    (int(code),),
                ).fetchone()
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

        image_url_signed = _make_signed_vehicle_asset_url(str(row[1] or ""))

        return jsonify(
            {
                "success": True,
                "data": {
                    "code": int(row[0]),
                    "image_url": image_url_signed,
                },
            }
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro em vehicles_admin_upload_catalog_image: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/assets/<path:filename>", methods=["GET"])
def vehicles_get_asset(filename: str):
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        filename = str(filename or "").strip()
        if not filename or filename != os.path.basename(filename):
            return jsonify({"success": False, "error": "INVALID_FILENAME"}), 400

        # Allow access either via Authorization: Bearer <JWT> OR via signed querystring (?exp=...&sig=...)
        authorized = False
        try:
            auth_header = request.headers.get("Authorization", "")
            token = None
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1].strip()
            if token and auth_manager and hasattr(auth_manager, "validate_token"):
                user = auth_manager.validate_token(token)
                if user:
                    authorized = True
        except Exception:
            authorized = False

        if not authorized:
            exp_raw = request.args.get("exp", "")
            sig = request.args.get("sig", "")
            try:
                exp_i = int(str(exp_raw).strip())
            except Exception:
                exp_i = 0

            now = int(time.time())
            if exp_i and exp_i >= now:
                if _is_valid_vehicle_asset_signature(filename, exp_i, str(sig or "")):
                    authorized = True

        if not authorized:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Authentication required",
                        "code": "AUTH_REQUIRED",
                    }
                ),
                401,
            )

        base_dir = os.path.join("data", "imagens", "vehicle")
        file_path = os.path.join(base_dir, filename)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "NOT_FOUND"}), 404

        mime, _ = mimetypes.guess_type(file_path)
        return send_file(file_path, mimetype=mime or "application/octet-stream")
    except Exception as e:
        if logger:
            logger.error(f"Erro em vehicles_get_asset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/ownership/history", methods=["GET"])
def get_vehicle_ownership_history():
    """Obter histórico de propriedade de veículos com filtros e paginação"""
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        if not log_processor:
            return (
                jsonify({"success": False, "error": "LogProcessor não inicializado"}),
                500,
            )

        # Obter parâmetros de query
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        steam_id = request.args.get("steam_id")
        vehicle_class = request.args.get("vehicle_class")
        ownership_type = request.args.get("ownership_type")

        # Validar limit
        if limit < 1 or limit > 1000:
            limit = 50
        if offset < 0:
            offset = 0

        # Construir query com filtros
        db_path = log_processor.db_manager.db_path
        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            where_conditions = []
            params = []

            if steam_id:
                where_conditions.append("steam_id = ?")
                params.append(steam_id)

            if vehicle_class:
                where_conditions.append("vehicle_class = ?")
                params.append(vehicle_class)

            if ownership_type:
                where_conditions.append("ownership_type = ?")
                params.append(ownership_type)

            where_clause = (
                "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            )

            # Query para contar total
            count_query = f"SELECT COUNT(*) as total FROM vehicle_ownership_history {where_clause}"
            cursor = conn.execute(count_query, params)
            total = cursor.fetchone()["total"]

            # Query para obter dados
            query = f"""
                SELECT * FROM vehicle_ownership_history 
                {where_clause}
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            vehicles = [dict(row) for row in rows]

        return jsonify(
            {
                "success": True,
                "data": {
                    "vehicles": vehicles,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "count": len(vehicles),
                },
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter histórico de veículos: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/ownership/current", methods=["GET"])
def get_vehicle_ownership_current():
    """Obter propriedade atual de veículos"""
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        if not log_processor:
            return (
                jsonify({"success": False, "error": "LogProcessor não inicializado"}),
                500,
            )

        # Obter parâmetros de query (filtros opcionais)
        steam_id = request.args.get("steam_id")
        vehicle_class = request.args.get("vehicle_class")

        # Construir query com filtros
        db_path = log_processor.db_manager.db_path
        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            where_conditions = []
            params = []

            if steam_id:
                where_conditions.append("steam_id = ?")
                params.append(steam_id)

            if vehicle_class:
                where_conditions.append("vehicle_class = ?")
                params.append(vehicle_class)

            where_clause = (
                "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            )

            query = f"""
                SELECT * FROM vehicle_current_ownership 
                {where_clause}
                ORDER BY last_ownership_change DESC
            """
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            vehicles = [dict(row) for row in rows]

        return jsonify(
            {
                "success": True,
                "data": {"vehicles": vehicles, "count": len(vehicles)},
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter propriedade atual de veículos: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/stats", methods=["GET"])
def get_vehicle_stats():
    """Obter estatísticas de veículos"""
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        if not log_processor:
            return (
                jsonify({"success": False, "error": "LogProcessor não inicializado"}),
                500,
            )

        # Usar método do DatabaseManager
        stats = log_processor.db_manager.get_vehicle_stats()

        # Melhorar estatísticas com contagem de veículos funcionais
        db_path = log_processor.db_manager.db_path
        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            # Contar veículos funcionais vs não funcionais
            cursor = conn.execute(
                """
                SELECT 
                    COUNT(CASE WHEN is_vehicle_functional = 1 THEN 1 END) as functional,
                    COUNT(CASE WHEN is_vehicle_functional = 0 THEN 1 END) as non_functional
                FROM vehicle_current_ownership
            """
            )
            result = cursor.fetchone()
            functional_count = result[0] if result else 0
            non_functional_count = result[1] if result else 0

        # Combinar estatísticas
        enhanced_stats = {
            **stats,
            "functional_vehicles": functional_count,
            "non_functional_vehicles": non_functional_count,
        }

        return jsonify(
            {"success": True, "data": enhanced_stats, "timestamp": time.time()}
        )

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de veículos: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/verification/status", methods=["GET"])
def get_vehicle_verification_status():
    """Obter status do serviço de verificação de veículos"""
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        if vehicle_verification_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "VehicleVerificationService não inicializado",
                    }
                ),
                500,
            )

        status = vehicle_verification_service.get_status()

        return jsonify({"success": True, "data": status, "timestamp": time.time()})

    except Exception as e:
        logger.error(f"Erro ao obter status do serviço de verificação: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/verification/start", methods=["POST"])
def start_vehicle_verification():
    """Iniciar serviço de verificação de veículos"""
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        if vehicle_verification_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "VehicleVerificationService não inicializado",
                    }
                ),
                500,
            )

        result = vehicle_verification_service.start()

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Erro ao iniciar serviço de verificação: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/verification/stop", methods=["POST"])
def stop_vehicle_verification():
    """Parar serviço de verificação de veículos"""
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        if vehicle_verification_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "VehicleVerificationService não inicializado",
                    }
                ),
                500,
            )

        result = vehicle_verification_service.stop()

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Erro ao parar serviço de verificação: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/verification/run-now", methods=["POST"])
def run_vehicle_verification_now():
    """Executar verificação de veículos manualmente (fora do agendamento)"""
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        if vehicle_verification_service is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "VehicleVerificationService não inicializado",
                    }
                ),
                500,
            )

        result = vehicle_verification_service.run_verification_now()

        status_code = 200 if result.get("success") else 500

        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Erro ao executar verificação manual: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/player/<steam_id>/by-status", methods=["GET"])
def get_player_vehicles_by_status(steam_id: str):
    """Listar veículos de um player específico agrupados por status ou filtrados"""
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        if not log_processor:
            return (
                jsonify({"success": False, "error": "LogProcessor não inicializado"}),
                500,
            )

        # Obter parâmetros de query
        status_param = request.args.get("status")

        # Processar filtro de status
        status_filter = None
        if status_param:
            try:
                # Suporta múltiplos status separados por vírgula (ex: "0,1")
                status_list = [
                    int(s.strip()) for s in status_param.split(",") if s.strip()
                ]
                if status_list:
                    status_filter = status_list
            except ValueError:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Parâmetro 'status' inválido. Use valores: 0 (Ativo), 1 (Inativo), 2 (Desaparecido), 3 (Destruído) ou múltiplos separados por vírgula",
                        }
                    ),
                    400,
                )

        # Construir query com filtros
        db_path = log_processor.db_manager.db_path
        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            # Buscar informações do player (primeiro veículo para pegar nome)
            cursor = conn.execute(
                """
                SELECT DISTINCT player_name, player_id 
                FROM vehicle_current_ownership 
                WHERE steam_id = ? 
                LIMIT 1
            """,
                (steam_id,),
            )
            player_info = cursor.fetchone()

            if not player_info:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Player com Steam ID {steam_id} não encontrado ou não possui veículos",
                        }
                    ),
                    404,
                )

            # Construir condições WHERE
            where_conditions = ["steam_id = ?"]
            params = [steam_id]

            if status_filter:
                if len(status_filter) == 1:
                    where_conditions.append("status = ?")
                    params.append(status_filter[0])
                else:
                    placeholders = ",".join(["?" for _ in status_filter])
                    where_conditions.append(f"status IN ({placeholders})")
                    params.extend(status_filter)

            where_clause = "WHERE " + " AND ".join(where_conditions)

            # Query para contar total
            count_query = f"SELECT COUNT(*) as total FROM vehicle_current_ownership {where_clause}"
            cursor = conn.execute(count_query, params)
            total = cursor.fetchone()["total"]

            # Query para obter dados
            query = f"""
                SELECT * FROM vehicle_current_ownership 
                {where_clause}
                ORDER BY status ASC, last_ownership_change DESC
            """
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            vehicles = [dict(row) for row in rows]

        # Mapear status para texto legível
        status_map = {0: "Ativo", 1: "Inativo", 2: "Desaparecido", 3: "Destruído"}

        # Função para formatar nome do veículo (remover prefixos)
        def format_vehicle_name(vehicle_class):
            if not vehicle_class:
                return "Desconhecido"
            # Remover prefixos comuns
            name = (
                vehicle_class.replace("BPC_", "").replace("BP_", "").replace("_ES", "")
            )
            return name

        # Processar veículos e adicionar campos formatados
        for vehicle in vehicles:
            vehicle["status_text"] = status_map.get(
                vehicle["status"], f"Desconhecido ({vehicle['status']})"
            )
            vehicle["vehicle_class_display"] = format_vehicle_name(
                vehicle.get("vehicle_class")
            )

        # Se não há filtro de status, agrupar por status
        if not status_filter:
            vehicles_by_status = {"0": [], "1": [], "2": [], "3": []}
            summary_by_status = {"0": 0, "1": 0, "2": 0, "3": 0}

            for vehicle in vehicles:
                status_key = str(vehicle["status"])
                vehicles_by_status[status_key].append(vehicle)
                summary_by_status[status_key] = summary_by_status.get(status_key, 0) + 1

            # Remover status vazios
            vehicles_by_status = {k: v for k, v in vehicles_by_status.items() if v}

            response_data = {
                "steam_id": steam_id,
                "player_name": player_info["player_name"],
                "player_id": player_info["player_id"],
                "summary": {"total_vehicles": total, "by_status": summary_by_status},
                "vehicles_by_status": vehicles_by_status,
            }
        else:
            # Com filtro, retornar lista simples
            response_data = {
                "steam_id": steam_id,
                "player_name": player_info["player_name"],
                "player_id": player_info["player_id"],
                "summary": {
                    "total_vehicles": total,
                    "filtered_status": status_filter,
                    "count": len(vehicles),
                },
                "vehicles": vehicles,
            }

        return jsonify(
            {"success": True, "data": response_data, "timestamp": time.time()}
        )

    except Exception as e:
        logger.error(f"Erro ao obter veículos do player {steam_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@vehicles_bp.route("/api/vehicles/players", methods=["GET"])
def get_all_players_vehicles():
    """Listar todos os players e seus veículos"""
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
    log_processor = getattr(services, 'log_processor', None)
    try:
        if not log_processor:
            return (
                jsonify({"success": False, "error": "LogProcessor não inicializado"}),
                500,
            )

        # Obter parâmetros de query
        status_param = request.args.get("status")
        group_by_status = request.args.get("group_by_status", "false").lower() == "true"
        limit = int(request.args.get("limit", 1000))
        offset = int(request.args.get("offset", 0))

        # Validar limit
        if limit < 1 or limit > 10000:
            limit = 1000
        if offset < 0:
            offset = 0

        # Processar filtro de status
        status_filter = None
        if status_param:
            try:
                status_list = [
                    int(s.strip()) for s in status_param.split(",") if s.strip()
                ]
                if status_list:
                    status_filter = status_list
            except ValueError:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Parâmetro 'status' inválido. Use valores: 0 (Ativo), 1 (Inativo), 2 (Desaparecido), 3 (Destruído) ou múltiplos separados por vírgula",
                        }
                    ),
                    400,
                )

        # Construir query com filtros
        db_path = log_processor.db_manager.db_path
        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row

            # Buscar todos os players únicos com veículos
            where_conditions = []
            params = []

            if status_filter:
                if len(status_filter) == 1:
                    where_conditions.append("status = ?")
                    params.append(status_filter[0])
                else:
                    placeholders = ",".join(["?" for _ in status_filter])
                    where_conditions.append(f"status IN ({placeholders})")
                    params.extend(status_filter)

            where_clause = (
                "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            )

            # Contar total de players
            count_query = f"""
                SELECT COUNT(DISTINCT steam_id) as total 
                FROM vehicle_current_ownership 
                {where_clause}
            """
            cursor = conn.execute(count_query, params)
            total_players = cursor.fetchone()["total"]

            # Contar total de veículos
            vehicles_count_query = f"""
                SELECT COUNT(*) as total 
                FROM vehicle_current_ownership 
                {where_clause}
            """
            cursor = conn.execute(vehicles_count_query, params)
            total_vehicles = cursor.fetchone()["total"]

            # Buscar lista de players únicos
            players_query = f"""
                SELECT DISTINCT 
                    steam_id,
                    player_name,
                    player_id,
                    COUNT(*) as vehicles_count
                FROM vehicle_current_ownership
                {where_clause}
                GROUP BY steam_id, player_name, player_id
                ORDER BY player_name ASC
                LIMIT ? OFFSET ?
            """
            params_with_pagination = params + [limit, offset]
            cursor = conn.execute(players_query, params_with_pagination)
            players_rows = cursor.fetchall()

            # Mapear status para texto legível
            status_map = {0: "Ativo", 1: "Inativo", 2: "Desaparecido", 3: "Destruído"}

            # Função para formatar nome do veículo
            def format_vehicle_name(vehicle_class):
                if not vehicle_class:
                    return "Desconhecido"
                name = (
                    vehicle_class.replace("BPC_", "")
                    .replace("BP_", "")
                    .replace("_ES", "")
                )
                return name

            # Para cada player, buscar seus veículos
            players_data = []
            for player_row in players_rows:
                steam_id_player = player_row["steam_id"]

                # Buscar veículos deste player
                vehicle_where = ["steam_id = ?", "vehicle_entity_id IS NOT NULL"]
                vehicle_params = [steam_id_player]

                if status_filter:
                    if len(status_filter) == 1:
                        vehicle_where.append("status = ?")
                        vehicle_params.append(status_filter[0])
                    else:
                        placeholders = ",".join(["?" for _ in status_filter])
                        vehicle_where.append(f"status IN ({placeholders})")
                        vehicle_params.extend(status_filter)

                vehicle_where_clause = "WHERE " + " AND ".join(vehicle_where)

                # Defensive: deduplicar por vehicle_entity_id (identidade do veículo) caso existam linhas antigas
                # por troca de container (entity_id).
                # Preferir a linha mais recente por vehicle_entity_id.
                vehicles = []
                try:
                    vehicles_query = f"""
                        SELECT * FROM (
                            SELECT
                                vco.*,
                                ROW_NUMBER() OVER (
                                    PARTITION BY vco.vehicle_entity_id
                                    ORDER BY vco.last_ownership_change DESC, vco.updated_at DESC, vco.entity_id DESC
                                ) AS rn
                            FROM vehicle_current_ownership vco
                            {vehicle_where_clause}
                        )
                        WHERE rn = 1
                        ORDER BY status ASC, last_ownership_change DESC
                    """
                    cursor = conn.execute(vehicles_query, vehicle_params)
                    vehicles_rows = cursor.fetchall()
                    vehicles = [dict(row) for row in vehicles_rows]
                    # Remover coluna auxiliar se vier no dict
                    for v in vehicles:
                        v.pop("rn", None)
                except Exception:
                    # Fallback: buscar tudo e deduplicar em Python
                    vehicles_query = f"""
                        SELECT * FROM vehicle_current_ownership
                        {vehicle_where_clause}
                        ORDER BY status ASC, last_ownership_change DESC
                    """
                    cursor = conn.execute(vehicles_query, vehicle_params)
                    vehicles_rows = cursor.fetchall()
                    all_vehicles = [dict(row) for row in vehicles_rows]

                    best_by_vehicle = {}
                    for v in all_vehicles:
                        key = v.get("vehicle_entity_id")
                        if key is None:
                            continue
                        if key not in best_by_vehicle:
                            best_by_vehicle[key] = v
                            continue
                        # manter o mais recente
                        existing = best_by_vehicle[key]
                        if (v.get("last_ownership_change") or "") > (existing.get("last_ownership_change") or ""):
                            best_by_vehicle[key] = v

                    vehicles = list(best_by_vehicle.values())

                # Adicionar campos formatados
                for vehicle in vehicles:
                    vehicle["status_text"] = status_map.get(
                        vehicle["status"], f"Desconhecido ({vehicle['status']})"
                    )
                    vehicle["vehicle_class_display"] = format_vehicle_name(
                        vehicle.get("vehicle_class")
                    )

                # Agrupar por status se solicitado
                if group_by_status:
                    vehicles_by_status = {"0": [], "1": [], "2": [], "3": []}
                    summary_by_status = {"0": 0, "1": 0, "2": 0, "3": 0}

                    for vehicle in vehicles:
                        status_key = str(vehicle["status"])
                        vehicles_by_status[status_key].append(vehicle)
                        summary_by_status[status_key] = (
                            summary_by_status.get(status_key, 0) + 1
                        )

                    # Remover status vazios
                    vehicles_by_status = {
                        k: v for k, v in vehicles_by_status.items() if v
                    }

                    player_data = {
                        "steam_id": steam_id_player,
                        "player_name": player_row["player_name"],
                        "player_id": player_row["player_id"],
                        "vehicles_count": len(vehicles),
                        "summary": {
                            "total": len(vehicles),
                            "by_status": summary_by_status,
                        },
                        "vehicles_by_status": vehicles_by_status,
                    }
                else:
                    player_data = {
                        "steam_id": steam_id_player,
                        "player_name": player_row["player_name"],
                        "player_id": player_row["player_id"],
                        "vehicles_count": len(vehicles),
                        "vehicles": vehicles,
                    }

                players_data.append(player_data)

        response_data = {
            "total_players": total_players,
            "total_vehicles": total_vehicles,
            "count": len(players_data),
            "limit": limit,
            "offset": offset,
        }

        if status_filter:
            response_data["filtered_status"] = status_filter

        response_data["players"] = players_data

        return jsonify(
            {"success": True, "data": response_data, "timestamp": time.time()}
        )

    except Exception as e:
        logger.error(f"Erro ao obter veículos de todos os players: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


