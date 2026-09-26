import json
import os
import sqlite3
import sys
from typing import List


def _get_scum_db_path() -> str:
    try:
        from utils.config_path_helper import ConfigPathHelper

        with open(os.path.join("data", "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return ConfigPathHelper(cfg).get_scum_db_path()
    except Exception:
        return "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"


def _print_table_info(cur: sqlite3.Cursor, table: str) -> None:
    print("\n===", table, "===")
    try:
        cur.execute(f"PRAGMA table_info('{table}')")
        for row in cur.fetchall():
            print(" ", row)
    except Exception as exc:
        print("ERR:", exc)


def main(argv: List[str]) -> int:
    chest_id = int(argv[1]) if len(argv) > 1 else 780962
    db = _get_scum_db_path()
    print("SCUM_DB:", db)
    if not os.path.exists(db):
        print("DB not found")
        return 2

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Find ammunition-related tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    ammo_tables = sorted([t for t in tables if "ammo" in t.lower() or "ammun" in t.lower()])
    print("\n=== Ammunition-related tables (name contains ammo/ammun) ===")
    for t in ammo_tables[:200]:
        print(" -", t)

    ammo_data_tables = sorted([t for t in tables if "ammunition_data" in t.lower()])
    print("\n=== Tables containing 'ammunition_data' ===")
    if not ammo_data_tables:
        print("(none)")
    for t in ammo_data_tables[:200]:
        print(" -", t)

    for t in [
        "entity",
        "entity_component",
        "entity_inventory_component_entry",
        "stackable_component_entry",
        "weapon_item_entity_loaded_ammo_data",
        "weapon_item_entity_internal_magazine_ammo_data",
        "weapon_attachment_magazine_item_entity_ammo_data",
    ]:
        _print_table_info(cur, t)

    # Print table info for first few ammo/ammun tables
    for t in ammo_tables[:15]:
        _print_table_info(cur, t)

    for t in ammo_data_tables[:30]:
        _print_table_info(cur, t)

    print("\n=== Sample items in chest", chest_id, "===")
    cur.execute(
        """
        SELECT id FROM entity_component
        WHERE entity_id = ? AND name = 'Inventory'
        LIMIT 1
        """,
        (chest_id,),
    )
    row = cur.fetchone()
    if not row:
        print("No Inventory component for chest")
        return 0
    inv_comp_id = int(row[0])

    cur.execute(
        """
        SELECT eice.entity_id AS item_entity_id,
               eice.data AS slot_index,
               e.class AS item_class
        FROM entity_inventory_component_entry eice
        JOIN entity e ON e.id = eice.entity_id
        WHERE eice.entity_component_id = ?
        LIMIT 20
        """,
        (inv_comp_id,),
    )
    items = cur.fetchall()
    for it in items:
        print(it)

    if not items:
        print("No items")
        return 0

    sample_item_id = int(items[0][0])
    print("\n=== Inspect components for item", sample_item_id, "===")
    cur.execute(
        "SELECT id,name FROM entity_component WHERE entity_id = ? ORDER BY name",
        (sample_item_id,),
    )
    comps = cur.fetchall()
    for c in comps:
        print(c)

    print("\n=== Try stackable_component_entry for item", sample_item_id, "===")
    cur.execute(
        """
        SELECT sce.*
        FROM entity_component ec
        JOIN stackable_component_entry sce ON sce.entity_component_id = ec.id
        WHERE ec.entity_id = ?
        """,
        (sample_item_id,),
    )
    for r in cur.fetchall()[:10]:
        print(r)

    print("\n=== Try ammo tables for item", sample_item_id, "===")
    for ammo_table in [
        "weapon_item_entity_loaded_ammo_data",
        "weapon_item_entity_internal_magazine_ammo_data",
        "weapon_attachment_magazine_item_entity_ammo_data",
    ]:
        try:
            if ammo_table == "weapon_attachment_magazine_item_entity_ammo_data":
                cur.execute(
                    f"SELECT * FROM {ammo_table} WHERE weapon_attachment_magazine_item_entity_id = ? LIMIT 10",
                    (sample_item_id,),
                )
            else:
                cur.execute(
                    f"SELECT * FROM {ammo_table} WHERE weapon_item_entity_id = ? LIMIT 10",
                    (sample_item_id,),
                )
            rows = cur.fetchall()
            if rows:
                print(ammo_table, "rows:")
                for r in rows:
                    print(" ", r)
        except Exception as exc:
            print(ammo_table, "ERR", exc)

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
