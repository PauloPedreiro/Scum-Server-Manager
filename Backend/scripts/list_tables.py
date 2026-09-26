"""Script para listar todas as tabelas do banco SSM.db"""

import sqlite3
from pathlib import Path

db_path = "data/SSM.db"

if Path(db_path).exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Obter todas as tabelas (excluindo tabelas do sistema SQLite)
    cursor.execute(
        """
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%' 
        ORDER BY name
    """
    )

    tables = [row[0] for row in cursor.fetchall()]

    print(f"Total tables: {len(tables)}\n")
    for i, table in enumerate(tables, 1):
        print(f"{i:2d}. {table}")

    conn.close()
else:
    print(f"Database not found: {db_path}")
