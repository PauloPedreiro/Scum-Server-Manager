import argparse
import re
import sqlite3
from dataclasses import dataclass
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
        raise ValueError("Either --base-id or --flag-element-id must be provided")

    cur.execute(
        "SELECT base_id FROM base_element WHERE element_id = ? LIMIT 1", (flag_element_id,)
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Flag element_id not found in base_element: {flag_element_id}")
    return int(row[0])


def _init_template_db(db_path: Path) -> sqlite3.Connection:
    if db_path.exists():
        db_path.unlink()

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    cur.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;

        CREATE TABLE meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE level_map (
            level INTEGER PRIMARY KEY,
            material TEXT NOT NULL UNIQUE
        );

        CREATE TABLE asset_whitelist (
            asset TEXT PRIMARY KEY,
            short_name TEXT NOT NULL,
            family_key TEXT NOT NULL,
            material TEXT,
            level INTEGER,
            FOREIGN KEY(level) REFERENCES level_map(level)
        );

        CREATE INDEX idx_asset_whitelist_family_key ON asset_whitelist(family_key);
        CREATE INDEX idx_asset_whitelist_level ON asset_whitelist(level);

        CREATE TABLE family_level_asset (
            family_key TEXT NOT NULL,
            level INTEGER NOT NULL,
            asset TEXT NOT NULL,
            PRIMARY KEY (family_key, level),
            FOREIGN KEY(level) REFERENCES level_map(level),
            FOREIGN KEY(asset) REFERENCES asset_whitelist(asset)
        );

        CREATE INDEX idx_family_level_asset_level ON family_level_asset(level);
        """
    )

    cur.executemany(
        "INSERT INTO level_map(level, material) VALUES (?, ?)",
        [(lvl, mat) for mat, lvl in _LEVELS.items()],
    )

    con.commit()
    return con


def build_template(scum_db: Path, out_db: Path, flag_element_id: int | None, base_id: int | None) -> None:
    scum_con = sqlite3.connect(f"file:{scum_db.as_posix()}?mode=ro", uri=True)
    scum_cur = scum_con.cursor()

    resolved_base_id = _resolve_base_id(scum_cur, flag_element_id, base_id)

    scum_cur.execute(
        "SELECT DISTINCT asset FROM base_element WHERE base_id = ? AND asset IS NOT NULL",
        (resolved_base_id,),
    )
    assets = sorted(r[0] for r in scum_cur.fetchall() if r and r[0])

    tpl_con = _init_template_db(out_db)
    tpl_cur = tpl_con.cursor()

    tpl_cur.executemany(
        "INSERT INTO meta(key, value) VALUES (?, ?)",
        [
            ("source_scum_db", str(scum_db)),
            ("source_base_id", str(resolved_base_id)),
            ("source_flag_element_id", str(flag_element_id) if flag_element_id is not None else ""),
        ],
    )

    parsed = [_parse_asset(a) for a in assets]

    tpl_cur.executemany(
        """
        INSERT INTO asset_whitelist(asset, short_name, family_key, material, level)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (p.asset, p.short_name, p.family_key, p.material, p.level)
            for p in parsed
        ],
    )

    # Build family->level->asset mapping when a level is detectable
    fam_level_rows = []
    for p in parsed:
        if p.level is None:
            continue
        fam_level_rows.append((p.family_key, p.level, p.asset))

    tpl_cur.executemany(
        """
        INSERT OR REPLACE INTO family_level_asset(family_key, level, asset)
        VALUES (?, ?, ?)
        """,
        fam_level_rows,
    )

    tpl_con.commit()
    tpl_con.close()
    scum_con.close()

    print("Wrote:", out_db)
    print("Whitelisted assets:", len(assets))
    print("Families with level mapping:", len({r[0] for r in fam_level_rows}))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build scum_base_template.db whitelist/crosswalk from a SCUM.db base area"
    )
    parser.add_argument(
        "--scum-db",
        default=r"C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db",
        help="Path to SCUM.db",
    )
    parser.add_argument(
        "--out-db",
        default=str(Path(__file__).with_name("scum_base_template.db")),
        help="Output template db path",
    )
    parser.add_argument("--flag-element-id", type=int, default=343)
    parser.add_argument("--base-id", type=int, default=None)

    args = parser.parse_args()

    build_template(
        scum_db=Path(args.scum_db),
        out_db=Path(args.out_db),
        flag_element_id=args.flag_element_id,
        base_id=args.base_id,
    )


if __name__ == "__main__":
    main()
