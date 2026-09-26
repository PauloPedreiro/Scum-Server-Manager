import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


def _short_name(asset_path: str) -> str:
    last = asset_path.split("/")[-1]
    if "." in last:
        parts = last.split(".")
        if len(parts) >= 2:
            return parts[-2]
    return last


@dataclass(frozen=True)
class CaptureLevelAsset:
    capture_level: int
    template_level: int
    asset: str


def _compute_level_mapping(levels: Iterable[int]) -> Dict[int, int]:
    lvls = sorted(set(int(x) for x in levels))
    if not lvls:
        return {}

    # Capture JSON may store levels as:
    # - 1..5 (already template levels)
    # - 0..4 (0-based capture; template expects 1..5)
    # Some families may be partially captured (e.g. only 0..3). If we see a 0 and
    # no explicit 5, we treat it as 0-based and shift by +1.
    has_0 = 0 in lvls
    has_5 = 5 in lvls
    all_in_0_4 = all(l in {0, 1, 2, 3, 4} for l in lvls)
    all_in_1_5 = all(1 <= l <= 5 for l in lvls)

    if has_0 and not has_5 and all_in_0_4:
        return {l: l + 1 for l in lvls}

    if all_in_1_5:
        return {l: l for l in lvls}

    # Mixed/unknown: keep only valid template levels.
    return {l: l for l in lvls if 1 <= l <= 5}


def _ensure_template_schema(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS level_map (
            level INTEGER PRIMARY KEY,
            material TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS asset_whitelist (
            asset TEXT PRIMARY KEY,
            short_name TEXT NOT NULL,
            family_key TEXT NOT NULL,
            material TEXT,
            level INTEGER,
            FOREIGN KEY(level) REFERENCES level_map(level)
        );

        CREATE INDEX IF NOT EXISTS idx_asset_whitelist_family_key ON asset_whitelist(family_key);
        CREATE INDEX IF NOT EXISTS idx_asset_whitelist_level ON asset_whitelist(level);

        CREATE TABLE IF NOT EXISTS family_level_asset (
            family_key TEXT NOT NULL,
            level INTEGER NOT NULL,
            asset TEXT NOT NULL,
            PRIMARY KEY (family_key, level)
        );

        CREATE INDEX IF NOT EXISTS idx_family_level_asset_level ON family_level_asset(level);
        """
    )

    existing = {
        r[0]
        for r in cur.execute("SELECT level FROM level_map").fetchall()
        if r and r[0] is not None
    }
    needed = {
        1: "Twig",
        2: "Wood",
        3: "Metal",
        4: "Brick",
        5: "Cement",
    }
    for lvl, mat in needed.items():
        if lvl not in existing:
            cur.execute("INSERT OR IGNORE INTO level_map(level, material) VALUES(?, ?)", (int(lvl), str(mat)))

    con.commit()


def _resolve_base_id_from_flag(scum_con: sqlite3.Connection, flag_id: int) -> int:
    cur = scum_con.cursor()
    cur.execute(
        "SELECT base_id FROM base_element WHERE element_id = ? LIMIT 1",
        (int(flag_id),),
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        raise SystemExit(f"Flag element_id not found in SCUM.db base_element: {flag_id}")
    return int(row[0])


def _list_missing_whitelist_assets(
    *,
    scum_db: Path,
    template_db: Path,
    flag_id: Optional[int],
    base_id: Optional[int],
) -> List[str]:
    if not scum_db.exists():
        raise SystemExit(f"SCUM.db not found: {scum_db}")
    if not template_db.exists():
        raise SystemExit(f"Template DB not found: {template_db}")

    scum_con = sqlite3.connect(f"file:{scum_db.as_posix()}?mode=ro", uri=True)
    tpl_con = sqlite3.connect(str(template_db))
    try:
        scum_con.row_factory = sqlite3.Row
        tpl_con.row_factory = sqlite3.Row

        resolved_base_id = int(base_id) if base_id is not None else _resolve_base_id_from_flag(scum_con, int(flag_id))

        sc_assets = {
            str(r[0]).strip()
            for r in scum_con.execute(
                "SELECT DISTINCT asset FROM base_element WHERE base_id = ? AND asset IS NOT NULL",
                (resolved_base_id,),
            ).fetchall()
            if r and r[0] is not None and str(r[0]).strip()
        }
        wl_assets = {
            str(r[0]).strip()
            for r in tpl_con.execute("SELECT asset FROM asset_whitelist").fetchall()
            if r and r[0] is not None and str(r[0]).strip()
        }

        missing = sorted(sc_assets - wl_assets)
        print("missing_whitelist:", len(missing))
        print("missing_whitelist_base_id:", resolved_base_id)
        for a in missing:
            print(a)
        return missing
    finally:
        try:
            scum_con.close()
        except Exception:
            pass
        try:
            tpl_con.close()
        except Exception:
            pass


def import_capture(*, capture_json: Path, template_db: Path, dry_run: bool) -> None:
    payload = json.loads(capture_json.read_text(encoding="utf-8"))
    families = payload.get("families") or {}

    con = sqlite3.connect(str(template_db), timeout=30.0)
    try:
        _ensure_template_schema(con)
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        inserted_whitelist = 0
        upserted_mapping = 0
        skipped_assets = 0

        cur.execute("BEGIN")

        for family_key, fam in families.items():
            levels_obj = (fam or {}).get("levels") or {}

            level_ints: List[int] = []
            for k in list(levels_obj.keys()):
                try:
                    level_ints.append(int(k))
                except Exception:
                    continue

            level_map = _compute_level_mapping(level_ints)
            if not level_map:
                continue

            rows: List[CaptureLevelAsset] = []
            for capture_level, template_level in level_map.items():
                entry = levels_obj.get(str(capture_level)) or {}
                asset = str(entry.get("asset") or "").strip()
                if not asset:
                    continue
                rows.append(
                    CaptureLevelAsset(
                        capture_level=int(capture_level),
                        template_level=int(template_level),
                        asset=asset,
                    )
                )

            for r in rows:
                short = _short_name(r.asset)
                if not dry_run:
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO asset_whitelist(asset, short_name, family_key, material, level)
                        VALUES (?, ?, ?, NULL, NULL)
                        """,
                        (r.asset, short, str(family_key)),
                    )
                    if cur.rowcount and cur.rowcount > 0:
                        inserted_whitelist += 1

                    cur.execute(
                        """
                        INSERT OR REPLACE INTO family_level_asset(family_key, level, asset)
                        VALUES (?, ?, ?)
                        """,
                        (str(family_key), int(r.template_level), r.asset),
                    )
                    if cur.rowcount and cur.rowcount > 0:
                        upserted_mapping += 1
                else:
                    exists = cur.execute(
                        "SELECT 1 FROM asset_whitelist WHERE asset=? LIMIT 1",
                        (r.asset,),
                    ).fetchone()
                    if not exists:
                        inserted_whitelist += 1

                    existing_map = cur.execute(
                        "SELECT asset FROM family_level_asset WHERE family_key=? AND level=? LIMIT 1",
                        (str(family_key), int(r.template_level)),
                    ).fetchone()
                    if not existing_map or str(existing_map[0]) != r.asset:
                        upserted_mapping += 1

            # Ensure the baseline (capture level 0) asset is whitelisted even if we did not map it
            # into family_level_asset (e.g. when capture levels are 1..5 only).
            baseline = levels_obj.get("0") or {}
            baseline_asset = str(baseline.get("asset") or "").strip()
            if baseline_asset:
                baseline_short = _short_name(baseline_asset)
                if not dry_run:
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO asset_whitelist(asset, short_name, family_key, material, level)
                        VALUES (?, ?, ?, NULL, NULL)
                        """,
                        (baseline_asset, baseline_short, str(family_key)),
                    )
                    if cur.rowcount and cur.rowcount > 0:
                        inserted_whitelist += 1
                else:
                    exists = cur.execute(
                        "SELECT 1 FROM asset_whitelist WHERE asset=? LIMIT 1",
                        (baseline_asset,),
                    ).fetchone()
                    if not exists:
                        inserted_whitelist += 1

        if not dry_run:
            cur.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES(?, datetime('now'))",
                ("last_import_capture_localtime",),
            )
            cur.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)" ,
                ("last_import_capture_file", str(capture_json)),
            )

            con.commit()
        else:
            con.rollback()

        print("capture_json:", capture_json)
        print("template_db:", template_db)
        print("dry_run:", bool(dry_run))
        print("inserted_whitelist:", int(inserted_whitelist))
        print("upserted_family_level_mapping:", int(upserted_mapping))
        print("skipped_assets:", int(skipped_assets))

    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import captured base material level mappings JSON into scum_base_template.db"
    )
    parser.add_argument(
        "--capture-json",
        default=str(Path(__file__).with_name("base_material_level_capture_flag_5.json")),
        help="Path to capture json file",
    )
    parser.add_argument(
        "--template-db",
        default="data/templates/scum_base_template.db",
        help="Path to scum_base_template.db to update",
    )
    parser.add_argument(
        "--scum-db",
        default=r"C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db",
        help="Path to SCUM.db (used only for --show-missing-whitelist)",
    )
    parser.add_argument("--flag-id", type=int, default=None, help="Flag element_id (used only for --show-missing-whitelist)")
    parser.add_argument("--base-id", type=int, default=None, help="Base id (used only for --show-missing-whitelist)")
    parser.add_argument(
        "--show-missing-whitelist",
        action="store_true",
        help="Print assets present in SCUM.db base but missing from template asset_whitelist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report counts; do not modify template_db",
    )

    args = parser.parse_args()

    capture_json = Path(args.capture_json)
    template_db = Path(args.template_db)

    import_capture(
        capture_json=capture_json,
        template_db=template_db,
        dry_run=bool(args.dry_run),
    )

    if bool(args.show_missing_whitelist):
        if args.flag_id is None and args.base_id is None:
            raise SystemExit("Provide --flag-id or --base-id when using --show-missing-whitelist")
        _list_missing_whitelist_assets(
            scum_db=Path(args.scum_db),
            template_db=template_db,
            flag_id=args.flag_id,
            base_id=args.base_id,
        )


if __name__ == "__main__":
    main()
