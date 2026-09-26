import argparse
import sqlite3
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a wide (pivot) view to scum_base_template.db")
    parser.add_argument(
        "--template-db",
        default=str(Path(__file__).with_name("scum_base_template.db")),
        help="Path to scum_base_template.db",
    )
    parser.add_argument(
        "--material",
        action="store_true",
        help="Also include level->material columns (material_1..material_5) via level_map",
    )
    parser.add_argument(
        "--normalize-prefixes",
        action="store_true",
        help=(
            "Create an additional VIEW family_level_wide_norm that normalizes family_key by stripping "
            "leading BP_/BPC_ so Twig (BP_) can be merged with Wood..Cement (BPC_) in one row."
        ),
    )
    parser.add_argument(
        "--materialize",
        action="store_true",
        help=(
            "Create physical tables family_level_wide_table and/or family_level_wide_norm_table (instead of only views). "
            "Tables are (re)built from the corresponding views."
        ),
    )

    args = parser.parse_args()
    db = Path(args.template_db)
    if not db.exists():
        raise FileNotFoundError(f"Template db not found: {db}")

    con = sqlite3.connect(str(db))
    cur = con.cursor()

    cur.execute("DROP VIEW IF EXISTS family_level_wide")
    cur.execute("DROP VIEW IF EXISTS family_level_wide_norm")

    if args.material:
        cur.execute(
            """
            CREATE VIEW family_level_wide AS
            SELECT
              fla.family_key AS family_key,
              MAX(CASE WHEN fla.level = 1 THEN fla.asset END) AS level_1,
              MAX(CASE WHEN fla.level = 2 THEN fla.asset END) AS level_2,
              MAX(CASE WHEN fla.level = 3 THEN fla.asset END) AS level_3,
              MAX(CASE WHEN fla.level = 4 THEN fla.asset END) AS level_4,
              MAX(CASE WHEN fla.level = 5 THEN fla.asset END) AS level_5,
              MAX(CASE WHEN lm.level = 1 THEN lm.material END) AS material_1,
              MAX(CASE WHEN lm.level = 2 THEN lm.material END) AS material_2,
              MAX(CASE WHEN lm.level = 3 THEN lm.material END) AS material_3,
              MAX(CASE WHEN lm.level = 4 THEN lm.material END) AS material_4,
              MAX(CASE WHEN lm.level = 5 THEN lm.material END) AS material_5
            FROM family_level_asset fla
            LEFT JOIN level_map lm ON lm.level = fla.level
            GROUP BY fla.family_key
            """
        )
    else:
        cur.execute(
            """
            CREATE VIEW family_level_wide AS
            SELECT
              family_key,
              MAX(CASE WHEN level = 1 THEN asset END) AS level_1,
              MAX(CASE WHEN level = 2 THEN asset END) AS level_2,
              MAX(CASE WHEN level = 3 THEN asset END) AS level_3,
              MAX(CASE WHEN level = 4 THEN asset END) AS level_4,
              MAX(CASE WHEN level = 5 THEN asset END) AS level_5
            FROM family_level_asset
            GROUP BY family_key
            """
        )

    if args.normalize_prefixes:
        if args.material:
            cur.execute(
                """
                CREATE VIEW family_level_wide_norm AS
                WITH norm AS (
                    SELECT
                        CASE
                            WHEN family_key GLOB 'BPC_*' THEN SUBSTR(family_key, 5)
                            WHEN family_key GLOB 'BP_*' THEN SUBSTR(family_key, 4)
                            ELSE family_key
                        END AS family_key_norm,
                        level,
                        asset
                    FROM family_level_asset
                )
                SELECT
                    n.family_key_norm AS family_key,
                    MAX(CASE WHEN n.level = 1 THEN n.asset END) AS level_1,
                    MAX(CASE WHEN n.level = 2 THEN n.asset END) AS level_2,
                    MAX(CASE WHEN n.level = 3 THEN n.asset END) AS level_3,
                    MAX(CASE WHEN n.level = 4 THEN n.asset END) AS level_4,
                    MAX(CASE WHEN n.level = 5 THEN n.asset END) AS level_5,
                    MAX(CASE WHEN lm.level = 1 THEN lm.material END) AS material_1,
                    MAX(CASE WHEN lm.level = 2 THEN lm.material END) AS material_2,
                    MAX(CASE WHEN lm.level = 3 THEN lm.material END) AS material_3,
                    MAX(CASE WHEN lm.level = 4 THEN lm.material END) AS material_4,
                    MAX(CASE WHEN lm.level = 5 THEN lm.material END) AS material_5
                FROM norm n
                LEFT JOIN level_map lm ON lm.level = n.level
                GROUP BY n.family_key_norm
                """
            )
        else:
            cur.execute(
                """
                CREATE VIEW family_level_wide_norm AS
                WITH norm AS (
                    SELECT
                        CASE
                            WHEN family_key GLOB 'BPC_*' THEN SUBSTR(family_key, 5)
                            WHEN family_key GLOB 'BP_*' THEN SUBSTR(family_key, 4)
                            ELSE family_key
                        END AS family_key_norm,
                        level,
                        asset
                    FROM family_level_asset
                )
                SELECT
                    family_key_norm AS family_key,
                    MAX(CASE WHEN level = 1 THEN asset END) AS level_1,
                    MAX(CASE WHEN level = 2 THEN asset END) AS level_2,
                    MAX(CASE WHEN level = 3 THEN asset END) AS level_3,
                    MAX(CASE WHEN level = 4 THEN asset END) AS level_4,
                    MAX(CASE WHEN level = 5 THEN asset END) AS level_5
                FROM norm
                GROUP BY family_key_norm
                """
            )

    if args.materialize:
        cur.execute("DROP TABLE IF EXISTS family_level_wide_table")
        cur.execute("DROP TABLE IF EXISTS family_level_wide_norm_table")

        if args.material:
            cur.execute(
                """
                CREATE TABLE family_level_wide_table (
                    family_key TEXT PRIMARY KEY,
                    level_1 TEXT,
                    level_2 TEXT,
                    level_3 TEXT,
                    level_4 TEXT,
                    level_5 TEXT,
                    material_1 TEXT,
                    material_2 TEXT,
                    material_3 TEXT,
                    material_4 TEXT,
                    material_5 TEXT
                )
                """
            )
            cur.execute(
                """
                INSERT INTO family_level_wide_table(
                    family_key, level_1, level_2, level_3, level_4, level_5,
                    material_1, material_2, material_3, material_4, material_5
                )
                SELECT
                    family_key, level_1, level_2, level_3, level_4, level_5,
                    material_1, material_2, material_3, material_4, material_5
                FROM family_level_wide
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE family_level_wide_table (
                    family_key TEXT PRIMARY KEY,
                    level_1 TEXT,
                    level_2 TEXT,
                    level_3 TEXT,
                    level_4 TEXT,
                    level_5 TEXT
                )
                """
            )
            cur.execute(
                """
                INSERT INTO family_level_wide_table(family_key, level_1, level_2, level_3, level_4, level_5)
                SELECT family_key, level_1, level_2, level_3, level_4, level_5
                FROM family_level_wide
                """
            )

        if args.normalize_prefixes:
            if args.material:
                cur.execute(
                    """
                    CREATE TABLE family_level_wide_norm_table (
                        family_key TEXT PRIMARY KEY,
                        level_1 TEXT,
                        level_2 TEXT,
                        level_3 TEXT,
                        level_4 TEXT,
                        level_5 TEXT,
                        material_1 TEXT,
                        material_2 TEXT,
                        material_3 TEXT,
                        material_4 TEXT,
                        material_5 TEXT
                    )
                    """
                )
                cur.execute(
                    """
                    INSERT INTO family_level_wide_norm_table(
                        family_key, level_1, level_2, level_3, level_4, level_5,
                        material_1, material_2, material_3, material_4, material_5
                    )
                    SELECT
                        family_key, level_1, level_2, level_3, level_4, level_5,
                        material_1, material_2, material_3, material_4, material_5
                    FROM family_level_wide_norm
                    """
                )
            else:
                cur.execute(
                    """
                    CREATE TABLE family_level_wide_norm_table (
                        family_key TEXT PRIMARY KEY,
                        level_1 TEXT,
                        level_2 TEXT,
                        level_3 TEXT,
                        level_4 TEXT,
                        level_5 TEXT
                    )
                    """
                )
                cur.execute(
                    """
                    INSERT INTO family_level_wide_norm_table(family_key, level_1, level_2, level_3, level_4, level_5)
                    SELECT family_key, level_1, level_2, level_3, level_4, level_5
                    FROM family_level_wide_norm
                    """
                )

    con.commit()

    rows = cur.execute("SELECT COUNT(*) FROM family_level_wide").fetchone()
    count = int(rows[0]) if rows else 0

    norm_count = 0
    if args.normalize_prefixes:
        norm_rows = cur.execute("SELECT COUNT(*) FROM family_level_wide_norm").fetchone()
        norm_count = int(norm_rows[0]) if norm_rows else 0

    wide_table_count = 0
    wide_norm_table_count = 0
    if args.materialize:
        wide_table_row = cur.execute("SELECT COUNT(*) FROM family_level_wide_table").fetchone()
        wide_table_count = int(wide_table_row[0]) if wide_table_row else 0
        if args.normalize_prefixes:
            wide_norm_table_row = cur.execute("SELECT COUNT(*) FROM family_level_wide_norm_table").fetchone()
            wide_norm_table_count = int(wide_norm_table_row[0]) if wide_norm_table_row else 0
    con.close()

    print("Created VIEW family_level_wide")
    print("Rows:", count)

    if args.normalize_prefixes:
        print("Created VIEW family_level_wide_norm")
        print("Rows:", norm_count)

    if args.materialize:
        print("Created TABLE family_level_wide_table")
        print("Rows:", wide_table_count)
        if args.normalize_prefixes:
            print("Created TABLE family_level_wide_norm_table")
            print("Rows:", wide_norm_table_count)


if __name__ == "__main__":
    main()
