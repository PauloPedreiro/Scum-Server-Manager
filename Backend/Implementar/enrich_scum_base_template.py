import argparse
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


_LEVELS = {
    "Twig": 1,
    "Wood": 2,
    "Metal": 3,
    "Brick": 4,
    "Cement": 5,
}

_MATERIAL_RE = re.compile(r"_(Twig|Wood|Metal|Brick|Cement)$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedAsset:
    asset: str
    short_name: str
    family_key: str
    material: str | None
    level: int | None


def _short_name(asset_path: str) -> str:
    last = asset_path.split("/")[-1]
    if "." in last:
        parts = last.split(".")
        if len(parts) >= 2:
            return parts[-2]
    return last


def _parse_asset(asset_path: str) -> ParsedAsset:
    short = _short_name(asset_path)

    material = None
    level = None
    family_key = short

    m = _MATERIAL_RE.search(short)
    if m:
        material = m.group(1)
        material_norm = material[:1].upper() + material[1:].lower()
        level = _LEVELS.get(material_norm)
        family_key = short[: m.start()]

    return ParsedAsset(
        asset=asset_path,
        short_name=short,
        family_key=family_key,
        material=material,
        level=level,
    )


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


def _open_scum(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _open_template(template_db: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(template_db))
    con.row_factory = sqlite3.Row
    return con


def _ensure_schema(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='asset_whitelist'"
    )
    if not cur.fetchone():
        raise ValueError(
            "Template DB schema not found (missing asset_whitelist). "
            "Create it first using build_scum_base_template.py"
        )


def enrich_template(
    scum_db: Path,
    template_db: Path,
    flag_id: int | None,
    base_id: int | None,
) -> None:
    scum_con = _open_scum(scum_db)
    tpl_con = _open_template(template_db)
    _ensure_schema(tpl_con)

    sc_cur = scum_con.cursor()
    tp_cur = tpl_con.cursor()

    resolved_base_id = _resolve_base_id(sc_cur, flag_id, base_id)

    sc_cur.execute(
        "SELECT DISTINCT asset FROM base_element WHERE base_id = ? AND asset IS NOT NULL",
        (resolved_base_id,),
    )
    assets = []
    for r in sc_cur.fetchall():
        if not r:
            continue
        a = r[0]
        if a is None:
            continue
        a = str(a).strip()
        if not a:
            continue
        assets.append(a)

    parsed = [_parse_asset(a) for a in assets]

    inserted_whitelist = 0
    inserted_mapping = 0

    tp_cur.execute("BEGIN")

    for p in parsed:
        tp_cur.execute(
            """
            INSERT OR IGNORE INTO asset_whitelist(asset, short_name, family_key, material, level)
            VALUES (?, ?, ?, ?, ?)
            """,
            (p.asset, p.short_name, p.family_key, p.material, p.level),
        )
        if tp_cur.rowcount and tp_cur.rowcount > 0:
            inserted_whitelist += 1

        if p.level is None:
            continue

        tp_cur.execute(
            """
            INSERT OR REPLACE INTO family_level_asset(family_key, level, asset)
            VALUES (?, ?, ?)
            """,
            (p.family_key, p.level, p.asset),
        )
        if tp_cur.rowcount and tp_cur.rowcount > 0:
            inserted_mapping += 1

    tp_cur.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        (
            "last_enrich_utc",
            datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        ),
    )
    tp_cur.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("last_enrich_source_flag_id", str(flag_id) if flag_id is not None else ""),
    )
    tp_cur.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("last_enrich_source_base_id", str(resolved_base_id)),
    )

    tpl_con.commit()

    tpl_con.close()
    scum_con.close()

    print("Template:", template_db)
    print("Source base_id:", resolved_base_id)
    print("Assets scanned:", len(assets))
    print("Inserted into whitelist:", inserted_whitelist)
    print("Upserted family-level mappings:", inserted_mapping)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Enrich scum_base_template.db from a SCUM.db base area (flag/base). "
            "Does not delete existing template data."
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

    parser.add_argument("--flag-id", type=int, default=None, help="Flag element_id")
    parser.add_argument("--base-id", type=int, default=None, help="Base id")

    args = parser.parse_args()

    enrich_template(
        scum_db=Path(args.scum_db),
        template_db=Path(args.template_db),
        flag_id=args.flag_id,
        base_id=args.base_id,
    )


if __name__ == "__main__":
    main()
