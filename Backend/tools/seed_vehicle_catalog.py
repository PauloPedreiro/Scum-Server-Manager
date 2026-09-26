import argparse
import json
import os
import sqlite3
from core.database.connector import DatabaseConnector
from typing import List, Tuple


DEFAULT_PRICE = 10000

# code, setup, display_name, template_vehicle_entity_id
DEFAULT_ITEMS: List[Tuple[int, str, str, int]] = [
    (1, "Rager", "Rager", 380026),
    (18, "Rager_ArmorLight", "Rager (Blindagem Basica)", 511466),
    (19, "Rager_ArmorHeavy", "Rager (Blindagem Pesada)", 510857),
    (2, "RIS", "RIS", 380032),
    (24, "RIS_Civil", "RIS (Civil)", 511663),
    (25, "RIS_ArmorHeavy", "RIS (Blindagem Pesada)", 511656),
    (3, "WolfsWagen", "WolfsWagen", 380005),
    (22, "WolfsWagen_ArmorLight", "WolfsWagen (Blindagem Basica)", 511632),
    (23, "WolfsWagen_ArmorHeavy", "WolfsWagen (Blindagem Pesada)", 511620),
    (4, "Laika", "Laika", 380006),
    (20, "Laika_ArmorLight", "Laika (Blindagem Basica)", 511586),
    (21, "Laika_ArmorHeavy", "Laika (Blindagem Pesada)", 511596),
    (5, "Barba", "Barba", 380009),
    (6, "Dirtbike", "Dirtbike", 380014),
    (7, "CityBike", "CityBike", 380017),
    (8, "MountainBike", "MountainBike", 380020),
    (9, "Kinglet_Duster", "Kinglet_Duster", 380023),
    (10, "Cruiser", "Cruiser", 380029),
    (11, "BigRaft", "BigRaft", 380035),
    (12, "Tractor", "Tractor", 380038),
    (13, "Kinglet_Mariner", "Kinglet_Mariner", 380043),
    (14, "SidecarBike", "SidecarBike", 380046),
    (15, "Dinghy", "Dinghy", 380049),
    (16, "WheelBarrow_Improvised", "WheelBarrow_Improvised", 380052),
    (17, "WheelBarrow_Metal", "WheelBarrow_Metal", 380055),
]


def _resolve_ssm_db_path(config_path: str) -> str:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        p = (
            cfg.get("paths", {})
            .get("application", {})
            .get("database", "data/SSM.db")
        )
        return str(p)
    return "data/SSM.db"


def _ensure_vehicle_catalog(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicle_catalog (
            code INTEGER PRIMARY KEY,
            setup TEXT NOT NULL,
            display_name TEXT NOT NULL,
            template_vehicle_entity_id INTEGER NOT NULL,
            price INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    # Migração: adicionar coluna setup se banco antigo não tiver
    cur = conn.execute("PRAGMA table_info('vehicle_catalog')")
    cols = {str(r[1]) for r in (cur.fetchall() or [])}
    if "setup" not in cols:
        try:
            conn.execute("ALTER TABLE vehicle_catalog ADD COLUMN setup TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError as oe:
            msg = str(oe or "")
            if "duplicate column name" not in msg.lower():
                raise

    # Backfill: se setup estiver vazio, copiar display_name
    conn.execute(
        "UPDATE vehicle_catalog SET setup = display_name WHERE (setup IS NULL OR TRIM(setup) = '')"
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_vehicle_catalog_enabled
        ON vehicle_catalog(enabled, code)
        """
    )


def seed_vehicle_catalog(ssm_db_path: str, price: int, enabled: int) -> int:
    if not os.path.exists(ssm_db_path):
        raise RuntimeError(f"SSM.db not found: {ssm_db_path}")

    with DatabaseConnector.get_connection(ssm_db_path, write_mode=True) as conn:
        conn.execute("BEGIN")
        _ensure_vehicle_catalog(conn)
        updated = 0
        for code, setup, display_name, template_id in DEFAULT_ITEMS:
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
                ON CONFLICT(code) DO UPDATE SET
                    setup=excluded.setup,
                    display_name=excluded.display_name,
                    template_vehicle_entity_id=excluded.template_vehicle_entity_id,
                    price=excluded.price,
                    enabled=excluded.enabled,
                    updated_at=datetime('now')
                """,
                (
                    int(code),
                    str(setup),
                    str(display_name),
                    int(template_id),
                    int(price),
                    int(enabled),
                ),
            )
            updated += 1
        conn.commit()
        return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed vehicle_catalog in SSM.db")
    parser.add_argument(
        "--config",
        default="data/config.json",
        help="Path to config.json (default: data/config.json)",
    )
    parser.add_argument(
        "--ssm-db",
        default="",
        help="Override SSM.db path (otherwise resolved from config)",
    )
    parser.add_argument(
        "--price",
        type=int,
        default=DEFAULT_PRICE,
        help=f"Default price for all vehicles (default: {DEFAULT_PRICE})",
    )
    parser.add_argument(
        "--enabled",
        type=int,
        default=1,
        help="Set enabled=1 or 0 for all items (default: 1)",
    )

    args = parser.parse_args()
    ssm_db_path = args.ssm_db.strip() or _resolve_ssm_db_path(args.config)
    n = seed_vehicle_catalog(ssm_db_path=ssm_db_path, price=int(args.price), enabled=int(args.enabled))
    print(f"OK: vehicle_catalog seeded/updated ({n} items) in {ssm_db_path}")


if __name__ == "__main__":
    main()
