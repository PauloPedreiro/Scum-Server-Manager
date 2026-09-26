from __future__ import annotations
from core.database.connector import DatabaseConnector

import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import schedule

from utils.logger import StructuredLogger


class ChestInventorySyncService:
    def __init__(
        self,
        config: Dict[str, Any],
        path_helper=None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        self.path_helper = path_helper

        cfg = self.config.get("chest_inventory_sync", {}) if isinstance(self.config, dict) else {}

        self.enabled = bool(cfg.get("enabled", False))
        self.auto_start = bool(cfg.get("auto_start", False))
        self.run_on_startup = bool(cfg.get("run_on_startup", True))
        self.sync_interval_minutes = int(cfg.get("sync_interval_minutes", 30) or 30)
        self.batch_size = int(cfg.get("batch_size", 25) or 25)
        self.ttl_minutes = int(cfg.get("ttl_minutes", 120) or 120)

        default_scum_db = (
            path_helper.get_scum_db_path()
            if path_helper
            else "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
        )
        default_ssm_db = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"

        self.scum_db_path = cfg.get("scum_db_path") or default_scum_db
        self.ssm_db_path = cfg.get("ssm_db_path") or default_ssm_db

        self.scheduler = schedule.Scheduler()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False

        self.last_sync_info: Dict[str, Any] = {
            "timestamp": None,
            "status": "never_run",
            "details": {},
        }

    _initialized_schema = False
    _schema_lock = threading.Lock()

    def ensure_tables(self) -> None:
        if ChestInventorySyncService._initialized_schema:
            return

        with ChestInventorySyncService._schema_lock:
            if ChestInventorySyncService._initialized_schema:
                return

            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chest_inventory_snapshot (
                        chest_entity_id INTEGER PRIMARY KEY,
                        steam_id TEXT,
                        player_name TEXT,
                        scanned_at TEXT NOT NULL,
                        items_total INTEGER DEFAULT 0
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chest_inventory_item (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chest_entity_id INTEGER NOT NULL,
                        item_entity_id INTEGER NOT NULL,
                        item_class TEXT,
                        slot_index INTEGER,
                        scanned_at TEXT NOT NULL
                    )
                    """
                )
                # Migração leve: adicionar coluna quantity se banco já existia
                try:
                    cur.execute("PRAGMA table_info('chest_inventory_item')")
                    cols = {row[1] for row in cur.fetchall()}
                    if "quantity" not in cols:
                        cur.execute(
                            "ALTER TABLE chest_inventory_item ADD COLUMN quantity INTEGER DEFAULT 1"
                        )
                except Exception:
                    pass
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chest_inventory_item_chest ON chest_inventory_item (chest_entity_id)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chest_inventory_item_class ON chest_inventory_item (item_class)"
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS item_catalog (
                        item_class TEXT PRIMARY KEY,
                        display_name TEXT,
                        category TEXT,
                        icon TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                    )
                    """
                )
                conn.commit()
                ChestInventorySyncService._initialized_schema = True

    def start(self) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "success": False,
                "message": "Sincronização de inventário de baús desabilitada",
                "status": "disabled",
            }

        if self.is_running:
            return {
                "success": False,
                "message": "Sincronização de inventário de baús já em execução",
                "status": "already_running",
            }

        try:
            self.ensure_tables()

            self.scheduler.clear()
            self.scheduler.every(self.sync_interval_minutes).minutes.do(self.sync_once)

            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self.scheduler_thread.start()
            self.is_running = True

            # Rodar 1a sincronização logo após iniciar (sem esperar o intervalo),
            # para preencher inventário no startup.
            if self.run_on_startup:
                def _run_startup_sync():
                    try:
                        # Pequeno delay para permitir que ChestSyncService popule chest_snapshot
                        time.sleep(20)
                        self.sync_once()
                    except Exception as exc:
                        self.logger.error(
                            "Erro ao executar sync inicial do inventário de baús",
                            {"error": str(exc)},
                        )

                threading.Thread(target=_run_startup_sync, daemon=True).start()

            return {
                "success": True,
                "message": "Sincronização de inventário de baús iniciada",
                "status": "started",
                "sync_interval_minutes": self.sync_interval_minutes,
            }
        except Exception as exc:
            self.logger.error(
                "Erro ao iniciar ChestInventorySyncService", {"error": str(exc)}
            )
            return {
                "success": False,
                "message": f"Erro ao iniciar sincronização: {exc}",
                "status": "error",
            }

    def stop(self) -> Dict[str, Any]:
        if not self.is_running:
            return {
                "success": False,
                "message": "Sincronização não está em execução",
                "status": "not_running",
            }

        self.stop_event.set()
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        self.scheduler.clear()
        self.is_running = False

        return {
            "success": True,
            "message": "Sincronização de inventário de baús parada",
            "status": "stopped",
        }

    def _scheduler_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.scheduler.run_pending()
                time.sleep(1)
            except Exception as exc:
                self.logger.error(
                    "Erro no loop de agendamento do inventário de baús",
                    {"error": str(exc)},
                )
                time.sleep(5)

    def _scan_scum_chest_inventory(
        self, conn: sqlite3.Connection, chest_entity_id: int
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        cur = conn.cursor()
        cur.execute("SELECT id FROM entity WHERE id = ?", (int(chest_entity_id),))
        if not cur.fetchone():
            return None, "CHEST_NOT_FOUND_SCUMDB"

        cur.execute(
            """
            SELECT id FROM entity_component
            WHERE entity_id = ? AND name = 'Inventory'
            LIMIT 1
            """,
            (int(chest_entity_id),),
        )
        comp = cur.fetchone()
        if not comp:
            return [], None
        comp_id = int(comp[0])

        cur.execute(
            """
            SELECT eice.entity_id AS item_entity_id,
                   eice.data AS slot_index,
                   e.class AS item_class
            FROM entity_inventory_component_entry eice
            INNER JOIN entity e ON e.id = eice.entity_id
            WHERE eice.entity_component_id = ?
            ORDER BY COALESCE(eice.data, 999999), eice.entity_id ASC
            """,
            (comp_id,),
        )
        rows = cur.fetchall()
        items: List[Dict[str, Any]] = []
        item_ids = [int(r[0]) for r in rows]

        stack_qty: Dict[int, int] = {}
        ammo_qty: Dict[int, int] = {}

        if item_ids:
            try:
                placeholders = ",".join(["?"] * len(item_ids))
                cur.execute(
                    f"""
                    SELECT ec.entity_id AS item_entity_id, sce.quantity AS quantity
                    FROM entity_component ec
                    INNER JOIN stackable_component_entry sce
                      ON sce.entity_component_id = ec.id
                    WHERE ec.entity_id IN ({placeholders})
                    """,
                    item_ids,
                )
                for rr in cur.fetchall():
                    try:
                        stack_qty[int(rr[0])] = int(rr[1]) if rr[1] is not None else 1
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                placeholders = ",".join(["?"] * len(item_ids))
                cur.execute(
                    f"""
                    SELECT weapon_item_entity_id, COUNT(1)
                    FROM weapon_item_entity_loaded_ammo_data
                    WHERE weapon_item_entity_id IN ({placeholders})
                    GROUP BY weapon_item_entity_id
                    """,
                    item_ids,
                )
                for rr in cur.fetchall():
                    ammo_qty[int(rr[0])] = ammo_qty.get(int(rr[0]), 0) + int(rr[1] or 0)
            except Exception:
                pass

            try:
                placeholders = ",".join(["?"] * len(item_ids))
                cur.execute(
                    f"""
                    SELECT weapon_item_entity_id, COUNT(1)
                    FROM weapon_item_entity_internal_magazine_ammo_data
                    WHERE weapon_item_entity_id IN ({placeholders})
                    GROUP BY weapon_item_entity_id
                    """,
                    item_ids,
                )
                for rr in cur.fetchall():
                    ammo_qty[int(rr[0])] = ammo_qty.get(int(rr[0]), 0) + int(rr[1] or 0)
            except Exception:
                pass

            try:
                placeholders = ",".join(["?"] * len(item_ids))
                cur.execute(
                    f"""
                    SELECT weapon_attachment_magazine_item_entity_id, COUNT(1)
                    FROM weapon_attachment_magazine_item_entity_ammo_data
                    WHERE weapon_attachment_magazine_item_entity_id IN ({placeholders})
                    GROUP BY weapon_attachment_magazine_item_entity_id
                    """,
                    item_ids,
                )
                for rr in cur.fetchall():
                    ammo_qty[int(rr[0])] = ammo_qty.get(int(rr[0]), 0) + int(rr[1] or 0)
            except Exception:
                pass

        for r in rows:
            item_id = int(r[0])
            qty = 1
            if item_id in stack_qty:
                qty = max(1, int(stack_qty[item_id] or 1))
            elif item_id in ammo_qty and int(ammo_qty[item_id] or 0) > 0:
                qty = int(ammo_qty[item_id] or 0)

            items.append(
                {
                    "item_entity_id": item_id,
                    "slot_index": r[1],
                    "item_class": r[2],
                    "quantity": qty,
                }
            )
        return items, None

    def _autofill_item_catalog(self, conn: sqlite3.Connection, item_classes: List[str]) -> int:
        classes = [str(c).strip() for c in (item_classes or []) if str(c).strip()]
        if not classes:
            return 0

        cur = conn.cursor()
        placeholders = ",".join(["?"] * len(classes))
        cur.execute(
            f"SELECT item_class FROM item_catalog WHERE item_class IN ({placeholders})",
            classes,
        )
        existing = {row[0] for row in cur.fetchall()}
        new_classes = [c for c in classes if c not in existing]
        if not new_classes:
            return 0

        cur.executemany(
            "INSERT OR IGNORE INTO item_catalog(item_class, updated_at) VALUES(?, datetime('now'))",
            [(c,) for c in new_classes],
        )
        return len(new_classes)

    def _select_chests_to_scan(self) -> List[Dict[str, Any]]:
        ttl_cutoff = None
        try:
            ttl_seconds = max(1, int(self.ttl_minutes) * 60)
            ttl_cutoff = datetime.utcfromtimestamp(time.time() - ttl_seconds).isoformat()
        except Exception:
            ttl_cutoff = None

        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if ttl_cutoff:
                cur.execute(
                    """
                    SELECT cs.entity_id, cs.steam_id, cs.player_name
                    FROM chest_snapshot cs
                    LEFT JOIN chest_inventory_snapshot cis
                      ON cis.chest_entity_id = cs.entity_id
                    WHERE cs.steam_id IS NOT NULL
                      AND cs.steam_id != ''
                      AND (cis.scanned_at IS NULL OR cis.scanned_at < ?)
                    ORDER BY COALESCE(cis.scanned_at, '1970-01-01T00:00:00') ASC
                    LIMIT ?
                    """,
                    (ttl_cutoff, int(self.batch_size)),
                )
            else:
                cur.execute(
                    """
                    SELECT cs.entity_id, cs.steam_id, cs.player_name
                    FROM chest_snapshot cs
                    WHERE cs.steam_id IS NOT NULL
                      AND cs.steam_id != ''
                    ORDER BY cs.last_seen_at DESC
                    LIMIT ?
                    """,
                    (int(self.batch_size),),
                )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def sync_once(self) -> Dict[str, Any]:
        start_time = time.monotonic()

        if not self.enabled:
            return {"success": False, "error": "disabled"}

        try:
            self.ensure_tables()
            chests = self._select_chests_to_scan()

            from utils.scum_db_helper import scum_db_readonly_connection

            scanned = 0
            updated_items = 0
            catalog_inserted = 0
            errors: List[Dict[str, Any]] = []

            if not chests:
                elapsed = time.monotonic() - start_time
                result = {
                    "success": True,
                    "scanned": 0,
                    "items": 0,
                    "catalog_new": 0,
                    "errors": [],
                    "elapsed_seconds": round(elapsed, 3),
                }
                self.last_sync_info = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "success",
                    "details": result,
                }
                return result

            with scum_db_readonly_connection(self.scum_db_path) as scum_conn:
                scum_conn.row_factory = sqlite3.Row

                with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as ssm_conn:
                    ssm_cur = ssm_conn.cursor()

                    for chest in chests:
                        chest_id = int(chest.get("entity_id") or 0)
                        if chest_id <= 0:
                            continue

                        items, err = self._scan_scum_chest_inventory(scum_conn, chest_id)
                        if err:
                            errors.append({"entity_id": chest_id, "error": err})
                            continue
                        if items is None:
                            errors.append({"entity_id": chest_id, "error": "CHEST_NOT_FOUND_SCUMDB"})
                            continue

                        scanned_at = datetime.utcnow().isoformat()

                        try:
                            classes = sorted({str(it.get("item_class") or "").strip() for it in items if str(it.get("item_class") or "").strip()})
                            catalog_inserted += self._autofill_item_catalog(ssm_conn, classes)
                        except Exception:
                            pass

                        ssm_cur.execute(
                            "DELETE FROM chest_inventory_item WHERE chest_entity_id = ?",
                            (chest_id,),
                        )
                        if items:
                            ssm_cur.executemany(
                                """
                                INSERT INTO chest_inventory_item(
                                    chest_entity_id, item_entity_id, item_class, slot_index, scanned_at, quantity
                                ) VALUES(?, ?, ?, ?, ?, ?)
                                """,
                                [
                                    (
                                        chest_id,
                                        int(it.get("item_entity_id") or 0),
                                        it.get("item_class"),
                                        it.get("slot_index"),
                                        scanned_at,
                                        int(it.get("quantity") or 1),
                                    )
                                    for it in items
                                ],
                            )

                        ssm_cur.execute(
                            """
                            INSERT INTO chest_inventory_snapshot(chest_entity_id, steam_id, player_name, scanned_at, items_total)
                            VALUES(?, ?, ?, ?, ?)
                            ON CONFLICT(chest_entity_id) DO UPDATE SET
                                steam_id=excluded.steam_id,
                                player_name=excluded.player_name,
                                scanned_at=excluded.scanned_at,
                                items_total=excluded.items_total
                            """,
                            (
                                chest_id,
                                str(chest.get("steam_id") or "").strip(),
                                chest.get("player_name"),
                                scanned_at,
                                len(items),
                            ),
                        )

                        scanned += 1
                        updated_items += len(items)

                    ssm_conn.commit()

            elapsed = time.monotonic() - start_time
            result = {
                "success": True,
                "scanned": scanned,
                "items": updated_items,
                "catalog_new": catalog_inserted,
                "errors": errors,
                "elapsed_seconds": round(elapsed, 3),
                "batch_size": int(self.batch_size),
                "ttl_minutes": int(self.ttl_minutes),
            }

            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success",
                "details": result,
            }

            return result

        except Exception as exc:
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": str(exc)},
            }
            return {"success": False, "error": str(exc)}

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "auto_start": self.auto_start,
            "is_running": self.is_running,
            "sync_interval_minutes": self.sync_interval_minutes,
            "batch_size": self.batch_size,
            "ttl_minutes": self.ttl_minutes,
            "last_sync": self.last_sync_info,
        }
