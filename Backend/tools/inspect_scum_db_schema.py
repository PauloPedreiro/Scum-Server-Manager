import json
import os
import re
import sqlite3
import sys


def _get_scum_db_path_from_config() -> str:
    try:
        from utils.config_path_helper import ConfigPathHelper

        with open(os.path.join("data", "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        ph = ConfigPathHelper(cfg)
        return ph.get_scum_db_path()
    except Exception as exc:
        print(f"WARN: failed to resolve SCUM DB path from config.json: {exc}")
        return ""


def main() -> int:
    scum_db_path = _get_scum_db_path_from_config() or os.environ.get("SCUM_DB_PATH")
    if not scum_db_path:
        scum_db_path = "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
    if not scum_db_path:
        print("ERROR: SCUM DB path not found. Set SCUM_DB_PATH or configure in data/config.json")
        return 2

    if not os.path.exists(scum_db_path):
        print(f"ERROR: SCUM DB not found: {scum_db_path}")
        return 2

    print("SCUM_DB:", scum_db_path)

    kw = re.compile(r"(ammo|stack|quant|count|amount|durab|uses|charges|bullets|rounds)", re.I)

    conn = sqlite3.connect(scum_db_path)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]

    cand_tables = sorted([t for t in tables if kw.search(t)])
    print("\nCandidate tables by name:", len(cand_tables))
    for t in cand_tables[:200]:
        print(" -", t)

    print("\nTables with matching columns:")
    hits = []
    for t in tables:
        try:
            cur.execute(f"PRAGMA table_info('{t}')")
            cols = [c[1] for c in cur.fetchall()]
            match = [c for c in cols if kw.search(c)]
            if match:
                hits.append((t, match))
        except Exception:
            pass

    hits.sort(key=lambda x: (-len(x[1]), x[0]))
    print("Total:", len(hits))
    for t, match in hits[:250]:
        print(t, match)

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
