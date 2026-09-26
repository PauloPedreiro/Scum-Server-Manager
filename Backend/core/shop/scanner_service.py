from core.database.connector import DatabaseConnector
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from utils.logger import StructuredLogger
from utils.scum_db_helper import scum_db_readonly_connection_strict

from core.shop.db import ssm_tx


@dataclass
class ScannerSyncResult:
    chest_id: int
    discovered_setups: int
    created_catalog: int


class ShopScannerService:
    def __init__(
        self,
        ssm_db_path: str,
        scum_db_path: str,
        logger: Optional[StructuredLogger] = None,
    ):
        self.ssm_db_path = ssm_db_path
        self.scum_db_path = scum_db_path
        self.logger = logger or StructuredLogger()

    def set_scanner_chest_id(self, chest_id: int) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            conn.execute(
                "INSERT INTO app_config(key, value, updated_at) VALUES(?, ?, datetime('now')) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
                ("shop.scanner_chest_id", str(int(chest_id))),
            )

    def get_scanner_chest_id(self) -> Optional[int]:
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM app_config WHERE key = ?", ("shop.scanner_chest_id",))
            row = cur.fetchone()
            if not row:
                return None
            try:
                return int(row[0])
            except Exception:
                return None

    def scan_scum_chest_items(self, chest_id: int) -> Tuple[Set[str], Optional[str]]:
        try:
            with scum_db_readonly_connection_strict(self.scum_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                cur.execute("SELECT id FROM entity WHERE id = ?", (int(chest_id),))
                if not cur.fetchone():
                    return set(), "CHEST_NOT_FOUND_SCUMDB"

                cur.execute(
                    """
                    SELECT id FROM entity_component
                    WHERE entity_id = ? AND name = 'Inventory'
                    LIMIT 1
                    """,
                    (int(chest_id),),
                )
                comp = cur.fetchone()
                if not comp:
                    return set(), "CHEST_NO_INVENTORY"
                comp_id = int(comp[0])

                cur.execute(
                    """
                    SELECT e.class
                    FROM entity_inventory_component_entry eice
                    INNER JOIN entity e ON e.id = eice.entity_id
                    WHERE eice.entity_component_id = ?
                    """,
                    (comp_id,),
                )
                setups = {str(r[0]) for r in cur.fetchall() if r and r[0]}
                return setups, None
        except Exception as e:
            return set(), f"SCAN_FAILED:{e}"

    def sync_catalog_from_scanner(self, chest_id: int) -> ScannerSyncResult:
        setups, err = self.scan_scum_chest_items(chest_id)
        if err:
            raise ValueError(err)

        created = 0
        with ssm_tx(self.ssm_db_path) as conn:
            # Load existing setup->code
            cur = conn.execute("SELECT setup, code FROM shop_catalog")
            existing: Dict[str, int] = {row[0]: int(row[1]) for row in cur.fetchall()}

            # Determine next code
            cur2 = conn.execute("SELECT COALESCE(MAX(code), 0) FROM shop_catalog")
            next_code = int(cur2.fetchone()[0] or 0) + 1

            for setup in sorted(setups):
                if setup in existing:
                    continue

                code = next_code
                next_code += 1

                conn.execute(
                    """
                    INSERT INTO shop_catalog(code, setup, enabled)
                    VALUES(?, ?, 1)
                    """,
                    (int(code), setup),
                )
                conn.execute(
                    """
                    INSERT INTO shop_offer(code, qty, price, enabled)
                    VALUES(?, 1, 0, 0)
                    """,
                    (int(code),),
                )
                created += 1

        return ScannerSyncResult(
            chest_id=int(chest_id),
            discovered_setups=len(setups),
            created_catalog=created,
        )

    def scan_scum_chest_items_with_qty(self, chest_id: int) -> Tuple[List[Dict[str, any]], Optional[str]]:
        try:
            with scum_db_readonly_connection_strict(self.scum_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                cur.execute("SELECT id FROM entity WHERE id = ?", (int(chest_id),))
                if not cur.fetchone():
                    return [], "CHEST_NOT_FOUND_SCUMDB"

                cur.execute(
                    """
                    SELECT id FROM entity_component
                    WHERE entity_id = ? AND name = 'Inventory'
                    LIMIT 1
                    """,
                    (int(chest_id),),
                )
                comp = cur.fetchone()
                if not comp:
                    return [], "CHEST_NO_INVENTORY"
                comp_id = int(comp[0])

                cur.execute(
                    """
                    SELECT e.class as setup, COUNT(*) as qty
                    FROM entity_inventory_component_entry eice
                    INNER JOIN entity e ON e.id = eice.entity_id
                    WHERE eice.entity_component_id = ?
                    GROUP BY e.class
                    """,
                    (comp_id,),
                )
                rows = cur.fetchall()
                items = [{"setup": str(r["setup"]), "qty": int(r["qty"])} for r in rows if r and r["setup"]]
                return items, None
        except Exception as e:
            return [], f"SCAN_FAILED:{e}"

