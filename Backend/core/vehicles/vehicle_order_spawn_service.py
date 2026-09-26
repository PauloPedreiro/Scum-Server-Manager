from core.database.connector import DatabaseConnector
import os
import json
import mimetypes
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from core.shop.db import ssm_tx
from utils.logger import StructuredLogger
from utils.scum_attributes_editor import create_scum_db_backup


@dataclass
class VehicleOrderSpawnRunResult:
    claimed: int
    spawned: int
    failed: int
    order_ids: List[str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clone_vehicle_template(
    templates_db_path: str,
    scum_db_path: str,
    template_vehicle_entity_id: int,
    new_x: float,
    new_y: float,
    new_z: float,
    *,
    keep_template_rotation: bool = True,
    new_rot: Optional[Tuple[float, float, float]] = None,
) -> Dict[str, Any]:
    src_uri = f"file:{templates_db_path}?mode=ro&immutable=1"
    src = sqlite3.connect(src_uri, uri=True, timeout=10.0)
    dst: Optional[sqlite3.Connection] = None
    dst_cur: Optional[sqlite3.Cursor] = None
    src_cur = src.cursor()

    def one_src(sql: str, params: Tuple[Any, ...] = ()):
        src_cur.execute(sql, params)
        return src_cur.fetchone()

    def all_src(sql: str, params: Tuple[Any, ...] = ()):
        src_cur.execute(sql, params)
        return src_cur.fetchall()

    tx_started = False
    try:
        try:
            from utils.restart_guard import should_block_scum_db_access

            if should_block_scum_db_access(
                component="VehicleOrderSpawnService",
                operation="clone_vehicle_template",
                scum_db_path=scum_db_path,
            ):
                raise RuntimeError("SCUM_DB_BLOCKED_RESTART_GUARD")
        except RuntimeError:
            raise
        except Exception:
            pass

        # Colunas devem ser compatíveis entre templates DB e DB destino.
        # Importante: validar tudo NO templates DB antes de abrir transação no SCUM.db,
        # para evitar lock desnecessário quando o SCUM_TEMPLATES.db estiver incompleto.
        entity_cols = [r[1] for r in all_src("PRAGMA table_info('entity')")]
        ve_cols = [r[1] for r in all_src("PRAGMA table_info('vehicle_entity')")]
        vs_cols = [r[1] for r in all_src("PRAGMA table_info('vehicle_spawner')")]
        ec_cols = [r[1] for r in all_src("PRAGMA table_info('entity_component')")]

        te = one_src("SELECT * FROM entity WHERE id=?", (int(template_vehicle_entity_id),))
        if not te:
            raise RuntimeError(
                f"Template entity not found in templates DB: {template_vehicle_entity_id}"
            )

        ve = one_src(
            "SELECT * FROM vehicle_entity WHERE entity_id=?",
            (int(template_vehicle_entity_id),),
        )
        if not ve:
            raise RuntimeError(
                f"Template vehicle_entity not found in templates DB: {template_vehicle_entity_id}"
            )

        template_container_id = ve[ve_cols.index("item_container_entity_id")]
        tc = one_src("SELECT * FROM entity WHERE id=?", (int(template_container_id),))
        if not tc:
            raise RuntimeError(
                f"Template container entity not found in templates DB: {template_container_id}"
            )

        vs = one_src(
            "SELECT * FROM vehicle_spawner WHERE vehicle_entity_id=?",
            (int(template_vehicle_entity_id),),
        )
        if not vs:
            raise RuntimeError(
                f"Template vehicle_spawner not found in templates DB: {template_vehicle_entity_id}"
            )

        tec = one_src(
            "SELECT * FROM entity_component WHERE entity_id=? ORDER BY id LIMIT 1",
            (int(template_container_id),),
        )
        if not tec:
            raise RuntimeError(
                f"Template container component not found in templates DB: {template_container_id}"
            )

        dst = sqlite3.connect(scum_db_path, timeout=30.0)
        dst_cur = dst.cursor()

        def one_dst(sql: str, params: Tuple[Any, ...] = ()):
            assert dst_cur is not None
            dst_cur.execute(sql, params)
            return dst_cur.fetchone()

        def all_dst(sql: str, params: Tuple[Any, ...] = ()):
            assert dst_cur is not None
            dst_cur.execute(sql, params)
            return dst_cur.fetchall()

        # lock de escrita no banco alvo (db offline, mas garante atomicidade)
        dst.execute("BEGIN IMMEDIATE")
        tx_started = True

        max_entity_id = one_dst("SELECT MAX(id) FROM entity")[0] or 0
        new_vehicle_id = int(max_entity_id) + 1
        new_container_id = int(max_entity_id) + 2

        max_comp_id = one_dst("SELECT MAX(id) FROM entity_component")[0] or 0
        new_comp_id = int(max_comp_id) + 1

        new_te = list(te)
        new_te[entity_cols.index("id")] = new_vehicle_id
        new_te[entity_cols.index("location_x")] = float(new_x)
        new_te[entity_cols.index("location_y")] = float(new_y)
        new_te[entity_cols.index("location_z")] = float(new_z)

        if not keep_template_rotation:
            if not new_rot:
                raise RuntimeError("new_rot required when keep_template_rotation=False")
            rx, ry, rz = new_rot
            new_te[entity_cols.index("rotation_x")] = float(rx)
            new_te[entity_cols.index("rotation_y")] = float(ry)
            new_te[entity_cols.index("rotation_z")] = float(rz)

        new_tc = list(tc)
        new_tc[entity_cols.index("id")] = new_container_id

        assert dst_cur is not None
        dst_cur.execute(
            f"INSERT INTO entity ({','.join(entity_cols)}) VALUES ({','.join(['?']*len(entity_cols))})",
            new_te,
        )
        dst_cur.execute(
            f"INSERT INTO entity ({','.join(entity_cols)}) VALUES ({','.join(['?']*len(entity_cols))})",
            new_tc,
        )

        new_ve = list(ve)
        new_ve[ve_cols.index("entity_id")] = new_vehicle_id
        new_ve[ve_cols.index("item_container_entity_id")] = new_container_id
        dst_cur.execute(
            f"INSERT INTO vehicle_entity ({','.join(ve_cols)}) VALUES ({','.join(['?']*len(ve_cols))})",
            new_ve,
        )

        new_vs = list(vs)
        new_vs[vs_cols.index("vehicle_entity_id")] = new_vehicle_id
        if "vehicle_last_access_time" in vs_cols:
            new_vs[vs_cols.index("vehicle_last_access_time")] = int(time.time())
        dst_cur.execute(
            f"INSERT INTO vehicle_spawner ({','.join(vs_cols)}) VALUES ({','.join(['?']*len(vs_cols))})",
            new_vs,
        )

        new_ec = list(tec)
        new_ec[ec_cols.index("id")] = new_comp_id
        new_ec[ec_cols.index("entity_id")] = new_container_id
        dst_cur.execute(
            f"INSERT INTO entity_component ({','.join(ec_cols)}) VALUES ({','.join(['?']*len(ec_cols))})",
            new_ec,
        )

        assert dst is not None
        dst.commit()

        v = one_dst(
            "SELECT id, class, location_x, location_y, location_z, rotation_x, rotation_y, rotation_z FROM entity WHERE id=?",
            (int(new_vehicle_id),),
        )

        return {
            "new_vehicle_entity_id": new_vehicle_id,
            "new_container_entity_id": new_container_id,
            "new_container_component_id": new_comp_id,
            "entity_row": v,
            "vehicle_asset_id": new_vs[vs_cols.index("vehicle_asset_id")]
            if "vehicle_asset_id" in vs_cols
            else None,
        }
    except Exception:
        if tx_started and dst is not None:
            try:
                dst.rollback()
            except Exception:
                pass
        raise
    finally:
        try:
            src.close()
        except Exception:
            pass
        try:
            if dst is not None:
                dst.close()
        except Exception:
            pass


class VehicleOrderSpawnService:
    def __init__(
        self,
        ssm_db_path: str,
        scum_db_path: str,
        templates_db_path: str = "data/templates/SCUM_TEMPLATES.db",
        logger=None,
    ):
        self.ssm_db_path = ssm_db_path
        self.scum_db_path = scum_db_path
        self.templates_db_path = templates_db_path
        self.logger = logger or StructuredLogger()

        self._shop_log_webhook = self._load_shop_log_webhook()
        self._vehicle_images_path = "data/imagens/vehicle"
        self._vehicle_image_mapping_path = os.path.join(
            self._vehicle_images_path, "mapping.json"
        )
        self._vehicle_image_mapping = self._load_vehicle_image_mapping()

    def _load_shop_log_webhook(self) -> str:
        try:
            webhooks_path = "data/webhooks.json"
            if not os.path.exists(webhooks_path):
                return ""
            with open(webhooks_path, "r", encoding="utf-8") as f:
                webhooks = json.load(f)
            return str((webhooks or {}).get("shop-log") or "").strip()
        except Exception:
            return ""

    def _load_vehicle_image_mapping(self) -> Dict[str, str]:
        try:
            if not os.path.exists(self._vehicle_image_mapping_path):
                return {}
            with open(self._vehicle_image_mapping_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {str(k).strip().lower(): str(v).strip() for k, v in data.items()}
            return {}
        except Exception:
            return {}

    def _resolve_vehicle_thumbnail_path_from_catalog(self, *, vehicle_code: int) -> Optional[str]:
        try:
            code_i = int(vehicle_code)
        except Exception:
            return None

        try:
            if not self.ssm_db_path or not os.path.exists(self.ssm_db_path):
                return None
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cur = conn.execute(
                    "SELECT image_url FROM vehicle_catalog WHERE code = ?",
                    (int(code_i),),
                )
                row = cur.fetchone()
            if not row:
                return None

            image_url = str(row[0] or "").strip()
            if not image_url:
                return None

            # image_url example:
            # /api/vehicles/assets/<filename>?exp=...&sig=...
            path_only = image_url.split("?", 1)[0]
            filename = path_only.rsplit("/", 1)[-1].strip()
            if not filename:
                return None
            if filename != os.path.basename(filename):
                return None

            local_path = os.path.join(self._vehicle_images_path, filename)
            return local_path if os.path.exists(local_path) else None
        except Exception:
            return None

    def _resolve_vehicle_thumbnail_path(
        self, *, vehicle_name: str, vehicle_code: Optional[int]
    ) -> Optional[str]:
        try:
            if vehicle_code is not None:
                from_catalog = self._resolve_vehicle_thumbnail_path_from_catalog(
                    vehicle_code=int(vehicle_code)
                )
                if from_catalog:
                    return from_catalog

            return None
        except Exception:
            return None

    def _send_shop_log_embed(self, *, embed: Dict[str, Any], thumbnail_path: Optional[str]) -> None:
        try:
            if not self._shop_log_webhook:
                return

            payload = {"embeds": [embed]}

            if thumbnail_path and os.path.exists(thumbnail_path):
                filename = os.path.basename(thumbnail_path)
                mime_type = (
                    mimetypes.guess_type(filename)[0] or "application/octet-stream"
                )
                embed.setdefault("thumbnail", {"url": f"attachment://{filename}"})
                with open(thumbnail_path, "rb") as f:
                    files = {"file": (filename, f, mime_type)}
                    requests.post(
                        self._shop_log_webhook,
                        data={"payload_json": json.dumps(payload)},
                        files=files,
                        timeout=10,
                    )
                return

            requests.post(self._shop_log_webhook, json=payload, timeout=10)
        except Exception:
            return

    def _notify_spawned(self, *, order: Dict[str, Any], order_id: str, res: Dict[str, Any]) -> None:
        try:
            requested_player = str(order.get("requested_player_name") or "").strip()
            requested_steam_id = str(order.get("requested_steam_id") or "").strip()
            vehicle_name = str(
                order.get("requested_vehicle_name")
                or order.get("vehicle_name")
                or ""
            ).strip()

            try:
                vehicle_code = int(
                    order.get("requested_vehicle_code")
                    or order.get("vehicle_code")
                )
            except Exception:
                vehicle_code = None

            try:
                x = float(order.get("new_x") or 0.0)
                y = float(order.get("new_y") or 0.0)
                z = float(order.get("new_z") or 0.0)
            except Exception:
                x, y, z = 0.0, 0.0, 0.0

            spawned_vehicle_id = int(res.get("new_vehicle_entity_id") or 0)
            spawned_container_id = int(res.get("new_container_entity_id") or 0)

            thumb = self._resolve_vehicle_thumbnail_path(
                vehicle_name=vehicle_name, vehicle_code=vehicle_code
            )

            player_text = requested_player or "-"
            vehicle_text = (
                f"{vehicle_code} {vehicle_name}".strip()
                if vehicle_code is not None
                else (vehicle_name or "-")
            )
            teleport_text = "```text\n" + f"#Teleport {x:.4f} {y:.4f} {z:.3f}" + "\n```"

            embed = {
                "title": "Veículo entregue",
                "color": 0xFF6B35,
                "fields": [
                    {"name": "\u200b", "value": player_text, "inline": True},
                    {"name": "\u200b", "value": vehicle_text, "inline": True},
                    {"name": "Location", "value": teleport_text, "inline": False},
                ],
                "footer": {
                    "text": (
                        f"Order: {order_id} • Container ID: {spawned_container_id} • "
                        f"Vehicle ID: {spawned_vehicle_id} • Steam ID: {requested_steam_id or '-'}"
                    )
                },
            }

            self._send_shop_log_embed(embed=embed, thumbnail_path=thumb)
        except Exception:
            return

    def _notify_template_missing(
        self,
        *,
        order: Dict[str, Any],
        order_id: str,
        template_id: int,
        error_message: str,
    ) -> None:
        try:
            requested_player = str(order.get("requested_player_name") or "").strip()
            requested_steam_id = str(order.get("requested_steam_id") or "").strip()
            vehicle_name = str(order.get("vehicle_name") or "").strip()
            vehicle_code = str(order.get("vehicle_code") or "").strip()

            try:
                x = float(order.get("new_x") or 0.0)
                y = float(order.get("new_y") or 0.0)
                z = float(order.get("new_z") or 0.0)
            except Exception:
                x, y, z = 0.0, 0.0, 0.0

            keep_rot = bool(int(order.get("keep_template_rotation") or 1))
            if keep_rot:
                rot_str = "(template)"
            else:
                rx = float(order.get("new_rot_x") or 0.0)
                ry = float(order.get("new_rot_y") or 0.0)
                rz = float(order.get("new_rot_z") or 0.0)
                rot_str = f"P={rx} Y={ry} R={rz}"

            vbuy_preview = f"/vbuy {vehicle_code or '?'} {{X={x} Y={y} Z={z}|{rot_str}}}"

            thumb = self._resolve_vehicle_thumbnail_path(
                vehicle_name=vehicle_name, vehicle_code=vehicle_code
            )

            embed = {
                "title": "Veículo indisponível (template não encontrado)",
                "color": 15158332,
                "fields": [
                    {
                        "name": "Jogador",
                        "value": requested_player or "-",
                        "inline": True,
                    },
                    {
                        "name": "Veículo",
                        "value": vehicle_name or "-",
                        "inline": True,
                    },
                    {
                        "name": "Código",
                        "value": vehicle_code or "-",
                        "inline": True,
                    },
                    {
                        "name": "Template ID",
                        "value": str(int(template_id)),
                        "inline": True,
                    },
                    {
                        "name": "Comando",
                        "value": f"`{vbuy_preview}`",
                        "inline": False,
                    },
                    {
                        "name": "Motivo",
                        "value": str(error_message or "").strip()[:900] or "-",
                        "inline": False,
                    },
                ],
                "footer": {
                    "text": f"Order: {order_id} • Steam ID: {requested_steam_id or '-'}"
                },
            }

            self._send_shop_log_embed(embed=embed, thumbnail_path=thumb)
        except Exception:
            return

    def _is_template_missing_error(self, exc: Exception) -> bool:
        msg = str(exc or "")
        if "templates db" in msg.lower() and "not found" in msg.lower():
            return True
        if msg.startswith("Template ") and "not found" in msg.lower():
            return True
        return False

    def _claim_pending(self, restart_cycle_id: str, limit: int) -> List[Dict[str, Any]]:
        now_iso = _utc_now_iso()
        claimed: List[Dict[str, Any]] = []
        with ssm_tx(self.ssm_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM vehicle_order
                WHERE status = 'pending'
                  AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (now_iso, int(limit)),
            )
            rows = cur.fetchall() or []
            for row in rows:
                order_id = str(row["order_id"])
                cur.execute(
                    """
                    UPDATE vehicle_order
                    SET status = 'processing',
                        attempt_count = attempt_count + 1,
                        locked_by = ?,
                        locked_at = ?,
                        restart_cycle_id = ?,
                        updated_at = datetime('now')
                    WHERE order_id = ?
                      AND status = 'pending'
                    """,
                    (restart_cycle_id, now_iso, restart_cycle_id, order_id),
                )
                if cur.rowcount:
                    claimed.append(dict(row))
        return claimed

    def _mark_spawned(self, order_id: str, restart_cycle_id: str, res: Dict[str, Any]) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE vehicle_order
                SET status = 'spawned',
                    spawned_vehicle_entity_id = ?,
                    spawned_container_entity_id = ?,
                    spawned_container_component_id = ?,
                    error_code = NULL,
                    error_message = NULL,
                    locked_by = NULL,
                    locked_at = NULL,
                    restart_cycle_id = ?,
                    updated_at = datetime('now')
                WHERE order_id = ?
                """,
                (
                    int(res["new_vehicle_entity_id"]),
                    int(res["new_container_entity_id"]),
                    int(res["new_container_component_id"]),
                    restart_cycle_id,
                    str(order_id),
                ),
            )

    def _mark_failed(self, order_id: str, restart_cycle_id: str, error_code: str, error_message: str) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE vehicle_order
                SET status = 'failed',
                    error_code = ?,
                    error_message = ?,
                    locked_by = NULL,
                    locked_at = NULL,
                    restart_cycle_id = ?,
                    updated_at = datetime('now')
                WHERE order_id = ?
                """,
                (str(error_code), str(error_message)[:2000], restart_cycle_id, str(order_id)),
            )

    def _upsert_app_config(self, key: str, value: str) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO app_config(key, value, updated_at)
                VALUES(?, ?, datetime('now'))
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')
                """,
                (str(key), str(value)),
            )

    def run_once(self, restart_cycle_id: str, limit: int = 50) -> VehicleOrderSpawnRunResult:
        worker_id = restart_cycle_id

        if not os.path.exists(self.scum_db_path):
            self.logger.warn(f"[VEHICLE_ORDER] SCUM.db not found: {self.scum_db_path}")
            return VehicleOrderSpawnRunResult(claimed=0, spawned=0, failed=0, order_ids=[])

        if not os.path.exists(self.templates_db_path):
            self.logger.error(
                f"[VEHICLE_ORDER] Templates DB not found: {self.templates_db_path}. Orders will not be spawned."
            )

        self._upsert_app_config("vehicle_order.last_restart_cycle_id", restart_cycle_id)
        self._upsert_app_config("vehicle_order.last_run_started_at", _utc_now_iso())

        claimed = self._claim_pending(worker_id, int(limit))
        if not claimed:
            self._upsert_app_config("vehicle_order.last_run_finished_at", _utc_now_iso())
            return VehicleOrderSpawnRunResult(claimed=0, spawned=0, failed=0, order_ids=[])

        if not os.path.exists(self.templates_db_path):
            failed = 0
            order_ids: List[str] = []
            for order in claimed:
                order_id = str(order.get("order_id"))
                order_ids.append(order_id)
                failed += 1
                self._mark_failed(
                    order_id,
                    restart_cycle_id,
                    "TEMPLATES_DB_MISSING",
                    f"Templates DB missing: {self.templates_db_path}",
                )

            self._upsert_app_config("vehicle_order.last_run_finished_at", _utc_now_iso())
            return VehicleOrderSpawnRunResult(
                claimed=len(claimed),
                spawned=0,
                failed=failed,
                order_ids=order_ids,
            )

        spawned = 0
        failed = 0
        order_ids: List[str] = []

        backup_path = None
        try:
            backup_path = create_scum_db_backup(self.scum_db_path)
            if backup_path:
                self.logger.info(f"[VEHICLE_ORDER] SCUM.db backup created: {backup_path}")
        except Exception as e:
            self.logger.warn(f"[VEHICLE_ORDER] Failed to create SCUM.db backup: {e}")

        for order in claimed:
            order_id = str(order.get("order_id"))
            order_ids.append(order_id)

            try:
                template_id = int(order["template_vehicle_entity_id"])
                new_x = float(order["new_x"])
                new_y = float(order["new_y"])
                new_z = float(order["new_z"])

                keep_rot = bool(int(order.get("keep_template_rotation") or 1))
                new_rot: Optional[Tuple[float, float, float]] = None
                if not keep_rot:
                    new_rot = (
                        float(order.get("new_rot_x") or 0.0),
                        float(order.get("new_rot_y") or 0.0),
                        float(order.get("new_rot_z") or 0.0),
                    )

                res = clone_vehicle_template(
                    templates_db_path=self.templates_db_path,
                    scum_db_path=self.scum_db_path,
                    template_vehicle_entity_id=template_id,
                    new_x=new_x,
                    new_y=new_y,
                    new_z=new_z,
                    keep_template_rotation=keep_rot,
                    new_rot=new_rot,
                )
                self._mark_spawned(order_id, restart_cycle_id, res)
                self._notify_spawned(order=order, order_id=order_id, res=res)
                spawned += 1

                self.logger.info(
                    f"[VEHICLE_ORDER] Spawned order_id={order_id} new_vehicle_entity_id={res.get('new_vehicle_entity_id')}"
                )

            except Exception as e:
                failed += 1
                if self._is_template_missing_error(e):
                    self._mark_failed(order_id, restart_cycle_id, "TEMPLATE_MISSING", str(e))
                    try:
                        template_id = int(order.get("template_vehicle_entity_id") or 0)
                    except Exception:
                        template_id = 0
                    self._notify_template_missing(
                        order=order,
                        order_id=order_id,
                        template_id=template_id,
                        error_message=str(e),
                    )
                    self.logger.warn(
                        f"[VEHICLE_ORDER] Template missing order_id={order_id} template_id={template_id}: {e}"
                    )
                else:
                    self._mark_failed(order_id, restart_cycle_id, "SPAWN_FAILED", str(e))
                    self.logger.error(f"[VEHICLE_ORDER] Failed order_id={order_id}: {e}")

        self._upsert_app_config("vehicle_order.last_run_finished_at", _utc_now_iso())

        return VehicleOrderSpawnRunResult(
            claimed=len(claimed),
            spawned=spawned,
            failed=failed,
            order_ids=order_ids,
        )
