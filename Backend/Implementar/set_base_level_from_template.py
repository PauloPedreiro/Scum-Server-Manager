import argparse
import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
import io
from pathlib import Path


@dataclass(frozen=True)
class Change:
    element_id: int
    old_asset: str
    new_asset: str
    family_key: str


def _resolve_base_id(cur: sqlite3.Cursor, flag_element_id: int | None, base_id: int | None) -> int:
    if base_id is not None:
        return base_id
    if flag_element_id is None:
        raise ValueError("Either --base-id or --flag-id must be provided")

    cur.execute(
        "SELECT base_id FROM base_element WHERE element_id = ? LIMIT 1", (flag_element_id,)
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Flag element_id not found in base_element: {flag_element_id}")
    return int(row[0])


def _backup_db(db_path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{db_path.name}.bak_set_level_{ts}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def _open_template(template_db: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(template_db))
    con.row_factory = sqlite3.Row
    return con


def _open_scum(db_path: Path, read_only: bool) -> sqlite3.Connection:
    if read_only:
        # On Windows, SQLite URI paths must be absolute and use file:///C:/... form.
        # Using file:C:/... may resolve unexpectedly and point to a different DB.
        uri = f"{db_path.resolve().as_uri()}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
    else:
        con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def _compute_changes(
    scum_con: sqlite3.Connection,
    tpl_con: sqlite3.Connection,
    base_id: int,
    target_level: int,
    exclude_element_ids: set[int] | None = None,
    fallback_lowest: bool = False,
) -> tuple[list[Change], dict[str, int]]:
    sc = scum_con.cursor()
    tp = tpl_con.cursor()

    sc.execute(
        """
        SELECT be.element_id, be.asset
        FROM base_element be
        WHERE be.base_id = ? AND be.asset IS NOT NULL
        """,
        (base_id,),
    )

    changes: list[Change] = []
    stats: dict[str, int] = {
        "total": 0,
        "not_whitelisted": 0,
        "no_family": 0,
        "no_mapping": 0,
        "fallback_lowest_used": 0,
        "already_target": 0,
        "to_change": 0,
    }

    debug: dict[str, list[str]] = {
        "not_whitelisted_assets": [],
        "no_mapping_family_keys": [],
    }

    debug_cases: dict[str, list[dict]] = {
        "fallback_lowest_samples": [],
        "already_target_samples": [],
    }

    exclude = exclude_element_ids or set()

    for row in sc.fetchall():
        stats["total"] += 1
        element_id = int(row["element_id"])
        if element_id in exclude:
            continue

        asset_raw = row["asset"]
        asset = str(asset_raw).strip() if asset_raw is not None else None
        if not asset:
            continue

        tp.execute(
            "SELECT family_key FROM asset_whitelist WHERE asset = ? LIMIT 1",
            (asset,),
        )
        r_whitelist = tp.fetchone()
        if not r_whitelist:
            stats["not_whitelisted"] += 1
            if len(debug["not_whitelisted_assets"]) < 25:
                debug["not_whitelisted_assets"].append(str(asset))
            continue

        family_key = str(r_whitelist["family_key"]) if "family_key" in r_whitelist.keys() else str(r_whitelist[0])
        if not family_key:
            stats["no_family"] += 1
            continue

        def _alt_family_keys(fk: str) -> list[str]:
            fk = str(fk)
            if fk.startswith("BP_"):
                return ["BPC_" + fk[3:]]
            if fk.startswith("BPC_"):
                return ["BP_" + fk[4:]]
            return []

        tp.execute(
            "SELECT asset FROM family_level_asset WHERE family_key = ? AND level = ? LIMIT 1",
            (family_key, target_level),
        )
        r = tp.fetchone()
        resolved_family_key = family_key
        if not r:
            for fk2 in _alt_family_keys(family_key):
                tp.execute(
                    "SELECT asset FROM family_level_asset WHERE family_key = ? AND level = ? LIMIT 1",
                    (fk2, target_level),
                )
                r = tp.fetchone()
                if r:
                    resolved_family_key = fk2
                    break

        if not r:
            if fallback_lowest:
                tp.execute(
                    """SELECT level, asset FROM family_level_asset WHERE family_key = ? ORDER BY level ASC LIMIT 1""",
                    (resolved_family_key,),
                )
                r = tp.fetchone()
                if not r:
                    for fk2 in _alt_family_keys(resolved_family_key):
                        tp.execute(
                            """SELECT level, asset FROM family_level_asset WHERE family_key = ? ORDER BY level ASC LIMIT 1""",
                            (fk2,),
                        )
                        r = tp.fetchone()
                        if r:
                            resolved_family_key = fk2
                            break
                if r:
                    stats["fallback_lowest_used"] += 1
                    if len(debug_cases["fallback_lowest_samples"]) < 50:
                        debug_cases["fallback_lowest_samples"].append(
                            {
                                "family_key": resolved_family_key,
                                "current_asset": asset,
                                "chosen_level": int(r["level"]) if "level" in r.keys() else int(r[0]),
                                "chosen_asset": str(r["asset"]) if "asset" in r.keys() else str(r[1]),
                            }
                        )
                else:
                    stats["no_mapping"] += 1
                    if len(debug["no_mapping_family_keys"]) < 25:
                        debug["no_mapping_family_keys"].append(resolved_family_key)
                    continue
            else:
                stats["no_mapping"] += 1
                if len(debug["no_mapping_family_keys"]) < 25:
                    debug["no_mapping_family_keys"].append(resolved_family_key)
                continue

        if "asset" in r.keys():
            new_asset = str(r["asset"])
        else:
            new_asset = str(r[0])
        if new_asset == asset:
            stats["already_target"] += 1
            if len(debug_cases["already_target_samples"]) < 50:
                debug_cases["already_target_samples"].append(
                    {
                        "family_key": family_key,
                        "current_asset": asset,
                        "resolved_asset": new_asset,
                        "note": "current_asset_equals_resolved_asset",
                    }
                )
            continue

        changes.append(
            Change(
                element_id=element_id,
                old_asset=str(asset),
                new_asset=new_asset,
                family_key=family_key,
            )
        )

    stats["to_change"] = len(changes)
    # Attach debug samples into stats so caller can print them in dry-run mode.
    stats["_debug_not_whitelisted_assets"] = list(dict.fromkeys(debug["not_whitelisted_assets"]))
    stats["_debug_no_mapping_family_keys"] = list(dict.fromkeys(debug["no_mapping_family_keys"]))
    stats["_debug_fallback_lowest_samples"] = debug_cases["fallback_lowest_samples"]
    stats["_debug_already_target_samples"] = debug_cases["already_target_samples"]
    return changes, stats


def apply_changes(scum_db: Path, changes: list[Change]) -> int:
    con = _open_scum(scum_db, read_only=False)
    cur = con.cursor()

    cur.execute("BEGIN")
    cur.executemany(
        "UPDATE base_element SET asset = ? WHERE element_id = ?",
        [(c.new_asset, c.element_id) for c in changes],
    )
    updated = cur.rowcount if cur.rowcount is not None else 0
    con.commit()
    con.close()
    return updated


def _write_report(report_path: Path, report_text: str, payload: dict) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.suffix.lower() == ".json":
        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        report_path.write_text(report_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Set base construction level (1..5) for all elements under a flag/base, "
            "using scum_base_template.db as a strict whitelist/crosswalk."
        )
    )

    parser.add_argument(
        "--scum-db",
        default=r"C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db",
        help="Path to SCUM.db",
    )
    parser.add_argument(
        "--template-db",
        default=str(Path(__file__).with_name("scum_base_template.db")),
        help="Path to scum_base_template.db",
    )

    parser.add_argument("--flag-id", type=int, default=None, help="Flag element_id (e.g. 343)")
    parser.add_argument("--base-id", type=int, default=None, help="Base id (optional)")

    parser.add_argument(
        "--level",
        type=int,
        required=True,
        help="Target level: 1=Twig, 2=Wood, 3=Metal, 4=Brick, 5=Cement",
    )

    parser.add_argument(
        "--fallback-lowest",
        action="store_true",
        help=(
            "If a family has no mapping for the requested level, fall back to the lowest available level "
            "for that family in the template (safe; no string guessing)."
        ),
    )

    parser.add_argument("--dry-run", action="store_true", help="Only report changes")
    parser.add_argument("--apply", action="store_true", help="Apply changes (requires backup)")
    parser.add_argument(
        "--report-file",
        default=None,
        help="Optional path to write a full report (useful when console output is truncated)",
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        help="Backup directory. Default: alongside SCUM.db",
    )

    args = parser.parse_args()

    if args.level < 1 or args.level > 5:
        raise ValueError("--level must be between 1 and 5")

    scum_db = Path(args.scum_db)
    template_db = Path(args.template_db)

    if not scum_db.exists():
        raise FileNotFoundError(f"SCUM.db not found: {scum_db}")
    if not template_db.exists():
        raise FileNotFoundError(f"Template db not found: {template_db}")

    if args.apply and args.dry_run:
        raise ValueError("Use either --apply or --dry-run (or none for implicit dry-run)")

    is_dry_run = True
    if args.apply:
        is_dry_run = False

    tpl_con = _open_template(template_db)
    scum_con = _open_scum(scum_db, read_only=True)
    base_id = _resolve_base_id(scum_con.cursor(), args.flag_id, args.base_id)

    exclude_ids: set[int] = set()
    if args.flag_id is not None:
        exclude_ids.add(int(args.flag_id))

    changes, stats = _compute_changes(
        scum_con=scum_con,
        tpl_con=tpl_con,
        base_id=base_id,
        target_level=args.level,
        exclude_element_ids=exclude_ids,
        fallback_lowest=bool(args.fallback_lowest),
    )

    scum_con.close()
    tpl_con.close()

    report_buf = io.StringIO()

    def _p(*a: object) -> None:
        print(*a)
        print(*a, file=report_buf)

    _p("Base:", base_id)
    _p("Target level:", args.level)
    for k in [
        "total",
        "not_whitelisted",
        "no_family",
        "no_mapping",
        "fallback_lowest_used",
        "already_target",
        "to_change",
    ]:
        _p(f"{k}: {stats.get(k, 0)}")

    if is_dry_run:
        _p("Mode: DRY-RUN")
        if stats.get("not_whitelisted", 0) > 0:
            assets = stats.get("_debug_not_whitelisted_assets", [])
            if assets:
                _p("\nSample not_whitelisted assets (up to 25):")
                for a in assets:
                    _p(a)
        if stats.get("no_mapping", 0) > 0:
            fams = stats.get("_debug_no_mapping_family_keys", [])
            if fams:
                _p("\nSample no_mapping family_keys (up to 25):")
                for fk in fams:
                    _p(fk)
        for c in changes[:50]:
            _p(f"{c.element_id}: {c.old_asset} -> {c.new_asset}")
        if len(changes) > 50:
            _p(f"... ({len(changes) - 50} more)")

        report_payload = {
            "base_id": base_id,
            "target_level": args.level,
            "mode": "DRY-RUN",
            "stats": {k: stats.get(k, 0) for k in [
                "total",
                "not_whitelisted",
                "no_family",
                "no_mapping",
                "fallback_lowest_used",
                "already_target",
                "to_change",
            ]},
            "debug_samples": {
                "not_whitelisted_assets": stats.get("_debug_not_whitelisted_assets", []),
                "no_mapping_family_keys": stats.get("_debug_no_mapping_family_keys", []),
                "fallback_lowest_samples": stats.get("_debug_fallback_lowest_samples", []),
                "already_target_samples": stats.get("_debug_already_target_samples", []),
            },
            "changes_sample": [
                {
                    "element_id": c.element_id,
                    "family_key": c.family_key,
                    "old_asset": c.old_asset,
                    "new_asset": c.new_asset,
                }
                for c in changes[:200]
            ],
            "changes_sample_truncated": len(changes) > 200,
        }

        if args.report_file:
            report_path = Path(args.report_file)
            _write_report(report_path, report_buf.getvalue(), report_payload)
            print("Report written:", report_path)
        return

    if not changes:
        print("Mode: APPLY")
        print("No changes to apply (already at target level for all mappable elements).")

        if args.report_file:
            report_payload = {
                "base_id": base_id,
                "target_level": args.level,
                "mode": "APPLY",
                "result": "no_changes",
                "stats": {k: stats.get(k, 0) for k in [
                    "total",
                    "not_whitelisted",
                    "no_family",
                    "no_mapping",
                    "fallback_lowest_used",
                    "already_target",
                    "to_change",
                ]},
                "debug_samples": {
                    "not_whitelisted_assets": stats.get("_debug_not_whitelisted_assets", []),
                    "no_mapping_family_keys": stats.get("_debug_no_mapping_family_keys", []),
                    "fallback_lowest_samples": stats.get("_debug_fallback_lowest_samples", []),
                    "already_target_samples": stats.get("_debug_already_target_samples", []),
                },
                "changes_sample": [],
            }
            report_path = Path(args.report_file)
            _write_report(report_path, report_buf.getvalue(), report_payload)
            print("Report written:", report_path)
        return

    backup_dir = (
        Path(args.backup_dir) if args.backup_dir else scum_db.parent
    )
    backup_path = _backup_db(scum_db, backup_dir)
    print("Backup:", backup_path)

    updated = apply_changes(scum_db, changes)
    print("Updated rows:", updated)

    if args.report_file:
        report_payload = {
            "base_id": base_id,
            "target_level": args.level,
            "mode": "APPLY",
            "result": "updated",
            "backup_path": str(backup_path),
            "updated_rows": int(updated),
            "stats": {k: stats.get(k, 0) for k in [
                "total",
                "not_whitelisted",
                "no_family",
                "no_mapping",
                "fallback_lowest_used",
                "already_target",
                "to_change",
            ]},
            "debug_samples": {
                "not_whitelisted_assets": stats.get("_debug_not_whitelisted_assets", []),
                "no_mapping_family_keys": stats.get("_debug_no_mapping_family_keys", []),
                "fallback_lowest_samples": stats.get("_debug_fallback_lowest_samples", []),
                "already_target_samples": stats.get("_debug_already_target_samples", []),
            },
            "changes_sample": [
                {
                    "element_id": c.element_id,
                    "family_key": c.family_key,
                    "old_asset": c.old_asset,
                    "new_asset": c.new_asset,
                }
                for c in changes[:200]
            ],
            "changes_sample_truncated": len(changes) > 200,
        }
        report_path = Path(args.report_file)
        _write_report(report_path, report_buf.getvalue(), report_payload)
        print("Report written:", report_path)


if __name__ == "__main__":
    main()
