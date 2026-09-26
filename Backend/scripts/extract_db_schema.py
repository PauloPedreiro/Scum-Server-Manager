"""Script para extrair schema completo do banco SSM.db"""

import sqlite3
import json
from pathlib import Path


def extract_schema(db_path: str):
    """Extrair schema completo do banco"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Obter todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    schema = {}

    for (table_name,) in tables:
        # Obter CREATE TABLE statement
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        )
        create_sql = cursor.fetchone()

        if create_sql and create_sql[0]:
            schema[table_name] = create_sql[0]

            # Obter informações das colunas
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            schema[f"{table_name}_columns"] = columns

            # Obter índices
            cursor.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name=?",
                (table_name,),
            )
            indexes = cursor.fetchall()
            if indexes:
                schema[f"{table_name}_indexes"] = [idx[1] for idx in indexes if idx[1]]

    conn.close()

    # Salvar em arquivo
    output_file = Path("data/db_schema_extracted.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    # Também salvar em formato SQL
    output_sql = Path("data/db_schema_extracted.sql")
    with open(output_sql, "w", encoding="utf-8") as f:
        f.write("-- Schema completo extraído do SSM.db\n\n")
        for table_name in sorted(schema.keys()):
            if not table_name.endswith("_columns") and not table_name.endswith(
                "_indexes"
            ):
                f.write(f"-- Table: {table_name}\n")
                f.write(f"{schema[table_name]};\n\n")

    print(f"Schema extraído para {output_file} e {output_sql}")
    print(
        f"Total de tabelas: {len([k for k in schema.keys() if not k.endswith('_columns') and not k.endswith('_indexes')])}"
    )

    return schema


if __name__ == "__main__":
    db_path = "data/SSM.db"
    if Path(db_path).exists():
        extract_schema(db_path)
    else:
        print(f"Banco não encontrado: {db_path}")
