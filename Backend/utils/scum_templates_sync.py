from core.database.connector import DatabaseConnector
import os
import sqlite3
import shutil
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class TemplateSyncIssue:
    template_vehicle_entity_id: int
    reason: str


def reset_scum_templates_db(*, templates_db_path: str, make_backup: bool = True) -> Dict[str, Any]:
    backup_path = None
    if os.path.exists(templates_db_path) and make_backup:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{templates_db_path}.{ts}.bak"
        shutil.copy2(templates_db_path, backup_path)

    if not os.path.exists(templates_db_path):
        return {
            "existed": False,
            "cleared": False,
            "backup_path": backup_path,
            "message": "Templates DB did not exist. Nothing to clear.",
        }

    with DatabaseConnector.get_connection(templates_db_path, timeout=30.0, write_mode=True) as conn:
        existing = set(
            [
                r[0]
                for r in (conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() or [])
            ]
        )

        tables = ["entity", "vehicle_entity", "vehicle_spawner", "entity_component"]
        cleared_counts: Dict[str, int] = {}

        # O DatabaseConnector já inicia uma transação IMMEDIATE se write_mode=True,
        # mas aqui o código original usava BEGIN manual. Vamos remover o BEGIN manual
        # para evitar conflitos, ou usar o conn diretamente.
        for t in tables:
            if t not in existing:
                cleared_counts[t] = 0
                continue
            cur = conn.execute(f"DELETE FROM {t}")
            cleared_counts[t] = int(cur.rowcount or 0)
        
        return {
            "existed": True,
            "cleared": True,
            "backup_path": backup_path,
            "deleted_rows": cleared_counts,
            "message": "Templates DB cleared.",
        }


def _fetchone(conn: sqlite3.Connection, sql: str, params: Tuple[Any, ...] = ()) -> Optional[tuple]:
    cur = conn.execute(sql, params)
    return cur.fetchone()


def _fetchall(conn: sqlite3.Connection, sql: str, params: Tuple[Any, ...] = ()) -> List[tuple]:
    cur = conn.execute(sql, params)
    return cur.fetchall() or []


def _read_create_sql(src: sqlite3.Connection, table: str) -> str:
    row = _fetchone(
        src, "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    if not row or not row[0]:
        raise RuntimeError(f"Table not found in source db: {table}")
    return str(row[0])


def _ensure_schema(src: sqlite3.Connection, dst: sqlite3.Connection, tables: List[str]) -> None:
    existing = set([r[0] for r in _fetchall(dst, "SELECT name FROM sqlite_master WHERE type='table'")])
    for t in tables:
        if t not in existing:
            dst.execute(_read_create_sql(src, t))


def _table_cols(conn: sqlite3.Connection, table: str) -> List[str]:
    rows = _fetchall(conn, f"PRAGMA table_info('{table}')")
    return [str(r[1]) for r in rows]


def _insert_row(dst: sqlite3.Connection, table: str, cols: List[str], row: tuple) -> None:
    placeholders = ",".join(["?"] * len(cols))
    cols_sql = ",".join(cols)
    dst.execute(
        f"INSERT OR REPLACE INTO {table} ({cols_sql}) VALUES ({placeholders})", row
    )


def merge_vehicle_templates_from_scum_db(
    *,
    source_scum_db: str,
    output_templates_db: str,
    template_vehicle_entity_ids: Iterable[int],
) -> Dict[str, Any]:
    ids = list(template_vehicle_entity_ids)
    if not os.path.exists(source_scum_db):
        raise RuntimeError(f"Source SCUM.db not found: {source_scum_db}")

    out_dir = os.path.dirname(output_templates_db)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with DatabaseConnector.get_connection(source_scum_db, timeout=30.0, write_mode=False) as src:
        with DatabaseConnector.get_connection(output_templates_db, timeout=30.0, write_mode=True) as dst:
            tables = ["entity", "vehicle_entity", "vehicle_spawner", "entity_component"]

            synced_ids: List[int] = []
            missing: List[TemplateSyncIssue] = []

            src.row_factory = None
            dst.row_factory = None

            _ensure_schema(src, dst, tables)

            entity_cols = _table_cols(src, "entity")
            ve_cols = _table_cols(src, "vehicle_entity")
            vs_cols = _table_cols(src, "vehicle_spawner")
            ec_cols = _table_cols(src, "entity_component")

            for raw_id in ids:
                try:
                    template_id = int(raw_id)
                except Exception:
                    continue

                te = _fetchone(src, "SELECT * FROM entity WHERE id=?", (template_id,))
                if not te:
                    missing.append(
                        TemplateSyncIssue(template_vehicle_entity_id=template_id, reason="entity missing")
                    )
                    continue

                ve = _fetchone(
                    src, "SELECT * FROM vehicle_entity WHERE entity_id=?", (template_id,)
                )
                if not ve:
                    missing.append(
                        TemplateSyncIssue(
                            template_vehicle_entity_id=template_id,
                            reason="vehicle_entity missing",
                        )
                    )
                    continue

                try:
                    idx_container = ve_cols.index("item_container_entity_id")
                except ValueError:
                    missing.append(
                        TemplateSyncIssue(
                            template_vehicle_entity_id=template_id,
                            reason="vehicle_entity.item_container_entity_id column missing",
                        )
                    )
                    continue

                container_entity_id = ve[idx_container]
                tc = _fetchone(src, "SELECT * FROM entity WHERE id=?", (int(container_entity_id),))
                if not tc:
                    missing.append(
                        TemplateSyncIssue(
                            template_vehicle_entity_id=template_id,
                            reason=f"container entity missing: {container_entity_id}",
                        )
                    )
                    continue

                vs = _fetchone(
                    src,
                    "SELECT * FROM vehicle_spawner WHERE vehicle_entity_id=?",
                    (template_id,),
                )
                if not vs:
                    missing.append(
                        TemplateSyncIssue(
                            template_vehicle_entity_id=template_id,
                            reason="vehicle_spawner missing",
                        )
                    )
                    continue

                tec = _fetchone(
                    src,
                    "SELECT * FROM entity_component WHERE entity_id=? ORDER BY id LIMIT 1",
                    (int(container_entity_id),),
                )
                if not tec:
                    missing.append(
                        TemplateSyncIssue(
                            template_vehicle_entity_id=template_id,
                            reason=f"entity_component missing for container: {container_entity_id}",
                        )
                    )
                    continue

                _insert_row(dst, "entity", entity_cols, te)
                _insert_row(dst, "entity", entity_cols, tc)
                _insert_row(dst, "vehicle_entity", ve_cols, ve)
                _insert_row(dst, "vehicle_spawner", vs_cols, vs)
                _insert_row(dst, "entity_component", ec_cols, tec)

                synced_ids.append(template_id)

            return {
                "synced": sorted(list(set(synced_ids))),
                "missing": [
                    {
                        "template_vehicle_entity_id": int(i.template_vehicle_entity_id),
                        "reason": str(i.reason),
                    }
                    for i in missing
                ],
                "counts": {
                    "requested": len(ids),
                    "synced": len(list(set(synced_ids))),
                    "missing": len(missing),
                },
                "output": output_templates_db,
            }
