import argparse
import os
import sqlite3
from typing import Iterable, List, Optional, Tuple


DEFAULT_TEMPLATE_IDS = [
    380005,
    380006,
    380009,
    380014,
    380017,
    380020,
    380023,
    380026,
    380029,
    380032,
    380035,
    380038,
    380043,
    380046,
    380049,
    380052,
    380055,

    # Armored/civil variants (templates extracted from SCUM.db)
    511466,  # Rager armor light
    510857,  # Rager armor heavy
    511586,  # Laika armor light
    511596,  # Laika armor heavy
    511632,  # WolfsWagen armor light
    511620,  # WolfsWagen armor heavy
    511663,  # RIS civil
    511656,  # RIS heavy/military
]


def _read_create_sql(src: sqlite3.Connection, table: str) -> str:
    cur = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    row = cur.fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Table not found in source db: {table}")
    return str(row[0])


def _copy_table_schema(src: sqlite3.Connection, dst: sqlite3.Connection, table: str) -> None:
    create_sql = _read_create_sql(src, table)
    dst.execute(create_sql)


def _fetchone(conn: sqlite3.Connection, sql: str, params: Tuple = ()) -> Optional[tuple]:
    cur = conn.execute(sql, params)
    return cur.fetchone()


def _fetchall(conn: sqlite3.Connection, sql: str, params: Tuple = ()) -> List[tuple]:
    cur = conn.execute(sql, params)
    return cur.fetchall() or []


def _table_cols(conn: sqlite3.Connection, table: str) -> List[str]:
    rows = _fetchall(conn, f"PRAGMA table_info('{table}')")
    return [str(r[1]) for r in rows]


def _insert_row(dst: sqlite3.Connection, table: str, cols: List[str], row: tuple) -> None:
    placeholders = ",".join(["?"] * len(cols))
    cols_sql = ",".join(cols)
    dst.execute(f"INSERT OR IGNORE INTO {table} ({cols_sql}) VALUES ({placeholders})", row)


def build_templates_db(source_db: str, output_db: str, template_ids: Iterable[int]) -> None:
    if not os.path.exists(source_db):
        raise RuntimeError(f"Source db not found: {source_db}")

    out_dir = os.path.dirname(output_db)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    if os.path.exists(output_db):
        os.remove(output_db)

    src = sqlite3.connect(source_db, timeout=30.0)
    dst = sqlite3.connect(output_db, timeout=30.0)

    try:
        src.row_factory = None
        dst.row_factory = None

        # Minimal set of tables used by the cloner
        tables = ["entity", "vehicle_entity", "vehicle_spawner", "entity_component"]
        for t in tables:
            _copy_table_schema(src, dst, t)

        entity_cols = _table_cols(src, "entity")
        ve_cols = _table_cols(src, "vehicle_entity")
        vs_cols = _table_cols(src, "vehicle_spawner")
        ec_cols = _table_cols(src, "entity_component")

        dst.execute("BEGIN")

        for template_vehicle_entity_id in template_ids:
            te = _fetchone(src, "SELECT * FROM entity WHERE id=?", (int(template_vehicle_entity_id),))
            if not te:
                raise RuntimeError(f"Template entity not found in source: {template_vehicle_entity_id}")

            ve = _fetchone(
                src,
                "SELECT * FROM vehicle_entity WHERE entity_id=?",
                (int(template_vehicle_entity_id),),
            )
            if not ve:
                raise RuntimeError(
                    f"Template vehicle_entity not found in source: {template_vehicle_entity_id}"
                )

            try:
                idx_container = ve_cols.index("item_container_entity_id")
            except ValueError:
                raise RuntimeError("vehicle_entity.item_container_entity_id column not found")

            container_entity_id = ve[idx_container]
            tc = _fetchone(src, "SELECT * FROM entity WHERE id=?", (int(container_entity_id),))
            if not tc:
                raise RuntimeError(
                    f"Template container entity not found in source: {container_entity_id}"
                )

            vs = _fetchone(
                src,
                "SELECT * FROM vehicle_spawner WHERE vehicle_entity_id=?",
                (int(template_vehicle_entity_id),),
            )
            if not vs:
                raise RuntimeError(
                    f"Template vehicle_spawner not found in source: {template_vehicle_entity_id}"
                )

            tec = _fetchone(
                src,
                "SELECT * FROM entity_component WHERE entity_id=? ORDER BY id LIMIT 1",
                (int(container_entity_id),),
            )
            if not tec:
                raise RuntimeError(
                    f"Template container component not found in source: {container_entity_id}"
                )

            _insert_row(dst, "entity", entity_cols, te)
            _insert_row(dst, "entity", entity_cols, tc)
            _insert_row(dst, "vehicle_entity", ve_cols, ve)
            _insert_row(dst, "vehicle_spawner", vs_cols, vs)
            _insert_row(dst, "entity_component", ec_cols, tec)

        dst.commit()

    except Exception:
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
            dst.close()
        except Exception:
            pass


def merge_templates_db(source_db: str, output_db: str, template_ids: Iterable[int]) -> None:
    if not os.path.exists(source_db):
        raise RuntimeError(f"Source db not found: {source_db}")

    out_dir = os.path.dirname(output_db)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    src = sqlite3.connect(source_db, timeout=30.0)
    dst = sqlite3.connect(output_db, timeout=30.0)

    try:
        src.row_factory = None
        dst.row_factory = None

        tables = ["entity", "vehicle_entity", "vehicle_spawner", "entity_component"]

        # Ensure schema exists in destination
        existing = set(
            [r[0] for r in _fetchall(dst, "SELECT name FROM sqlite_master WHERE type='table'")]
        )
        for t in tables:
            if t not in existing:
                _copy_table_schema(src, dst, t)

        entity_cols = _table_cols(src, "entity")
        ve_cols = _table_cols(src, "vehicle_entity")
        vs_cols = _table_cols(src, "vehicle_spawner")
        ec_cols = _table_cols(src, "entity_component")

        dst.execute("BEGIN")

        for template_vehicle_entity_id in template_ids:
            te = _fetchone(
                src, "SELECT * FROM entity WHERE id=?", (int(template_vehicle_entity_id),)
            )
            if not te:
                raise RuntimeError(
                    f"Template entity not found in source: {template_vehicle_entity_id}"
                )

            ve = _fetchone(
                src,
                "SELECT * FROM vehicle_entity WHERE entity_id=?",
                (int(template_vehicle_entity_id),),
            )
            if not ve:
                raise RuntimeError(
                    f"Template vehicle_entity not found in source: {template_vehicle_entity_id}"
                )

            try:
                idx_container = ve_cols.index("item_container_entity_id")
            except ValueError:
                raise RuntimeError("vehicle_entity.item_container_entity_id column not found")

            container_entity_id = ve[idx_container]
            tc = _fetchone(src, "SELECT * FROM entity WHERE id=?", (int(container_entity_id),))
            if not tc:
                raise RuntimeError(
                    f"Template container entity not found in source: {container_entity_id}"
                )

            vs = _fetchone(
                src,
                "SELECT * FROM vehicle_spawner WHERE vehicle_entity_id=?",
                (int(template_vehicle_entity_id),),
            )
            if not vs:
                raise RuntimeError(
                    f"Template vehicle_spawner not found in source: {template_vehicle_entity_id}"
                )

            tec = _fetchone(
                src,
                "SELECT * FROM entity_component WHERE entity_id=? ORDER BY id LIMIT 1",
                (int(container_entity_id),),
            )
            if not tec:
                raise RuntimeError(
                    f"Template container component not found in source: {container_entity_id}"
                )

            _insert_row(dst, "entity", entity_cols, te)
            _insert_row(dst, "entity", entity_cols, tc)
            _insert_row(dst, "vehicle_entity", ve_cols, ve)
            _insert_row(dst, "vehicle_spawner", vs_cols, vs)
            _insert_row(dst, "entity_component", ec_cols, tec)

        dst.commit()

    except Exception:
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
            dst.close()
        except Exception:
            pass


def _parse_ids(ids_raw: str) -> List[int]:
    parts = [p.strip() for p in str(ids_raw or "").replace(";", ",").split(",") if p.strip()]
    out: List[int] = []
    for p in parts:
        if not p:
            continue
        out.append(int(p))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SCUM_TEMPLATES.db from a source SCUM.db")
    parser.add_argument("--source", required=True, help="Path to source SCUM.db (with prepared templates)")
    parser.add_argument(
        "--mode",
        default="rebuild",
        choices=["rebuild", "merge"],
        help="rebuild = recreate templates db from scratch; merge = append templates into existing db (default: rebuild)",
    )
    parser.add_argument(
        "--output",
        default="data/templates/SCUM_TEMPLATES.db",
        help="Output path for templates db (default: data/templates/SCUM_TEMPLATES.db)",
    )
    parser.add_argument(
        "--ids",
        default=",".join([str(i) for i in DEFAULT_TEMPLATE_IDS]),
        help="Comma-separated list of template vehicle entity IDs",
    )

    args = parser.parse_args()
    ids = _parse_ids(args.ids)
    if not ids:
        raise RuntimeError("No template IDs provided")

    if str(args.mode or "").strip().lower() == "merge":
        merge_templates_db(args.source, args.output, ids)
        print(f"OK: merged {len(ids)} templates into db at {args.output}")
    else:
        build_templates_db(args.source, args.output, ids)
        print(f"OK: created templates db at {args.output} with {len(ids)} templates")


if __name__ == "__main__":
    main()
