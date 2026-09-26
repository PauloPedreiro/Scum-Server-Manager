import sqlite3
from pathlib import Path


def main() -> None:
    db_path = Path("data/templates/scum_base_template.db")
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    con = sqlite3.connect(str(db_path))
    try:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        tables = [r["name"] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()]
        print(f"db: {db_path}")
        print(f"tables ({len(tables)}): {tables}")

        def count_rows(table: str) -> int:
            return int(cur.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()[0])

        if "asset_whitelist" in tables:
            print("asset_whitelist rows:", count_rows("asset_whitelist"))
        else:
            print("asset_whitelist: MISSING")

        if "family_level_asset" in tables:
            print("family_level_asset rows:", count_rows("family_level_asset"))
            print(
                "family_level_asset distinct families:",
                int(cur.execute("SELECT COUNT(DISTINCT family_key) FROM family_level_asset").fetchone()[0]),
            )
            print(
                "family_level_asset by level:",
                [tuple(r) for r in cur.execute(
                    "SELECT level, COUNT(*) FROM family_level_asset GROUP BY level ORDER BY level"
                ).fetchall()],
            )

            # Coverage: families that have (or don't have) level 5
            fam_total = int(cur.execute("SELECT COUNT(DISTINCT family_key) FROM family_level_asset").fetchone()[0])
            fam_with_5 = int(
                cur.execute(
                    "SELECT COUNT(DISTINCT family_key) FROM family_level_asset WHERE level = 5"
                ).fetchone()[0]
            )
            print("families with level 5:", fam_with_5, "/", fam_total)

            # Show some families missing level 5 (sample)
            missing_5 = [
                r[0]
                for r in cur.execute(
                    """
                    SELECT DISTINCT f.family_key
                    FROM family_level_asset f
                    WHERE f.family_key NOT IN (
                        SELECT family_key FROM family_level_asset WHERE level = 5
                    )
                    ORDER BY f.family_key
                    LIMIT 30
                    """
                ).fetchall()
            ]
            print("sample families missing level 5 (up to 30):", missing_5)
        else:
            print("family_level_asset: MISSING")

    finally:
        con.close()


if __name__ == "__main__":
    main()
