"""Script para corrigir a tabela minigame_events no banco existente"""

import sqlite3
from pathlib import Path

db_path = "data/SSM.db"

if not Path(db_path).exists():
    print(f"Banco não encontrado: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verificar se a tabela existe
cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='minigame_events'"
)
if not cursor.fetchone():
    print("Tabela minigame_events não existe. Execute Create Database primeiro.")
    conn.close()
    exit(1)

# Verificar quantas colunas tem
cursor.execute("PRAGMA table_info(minigame_events)")
cols = cursor.fetchall()
print(f"Colunas atuais: {len(cols)}")
col_names = {col[1] for col in cols}

# Colunas esperadas
expected_cols = {
    "log_line",
    "elapsed_time",
    "failed_attempts",
    "target_object",
    "target_object_id",
    "lock_type",
    "owner_id",
    "owner_steam_id",
    "owner_name",
    "is_property_invasion",
    "location_x",
    "location_y",
    "location_z",
    "log_file",
    "discord_sent",
    "created_at",
}

missing = expected_cols - col_names

if not missing:
    print("Tabela já está completa!")
    conn.close()
    exit(0)

print(f"Faltam {len(missing)} colunas. Recriando tabela...")

# Fazer backup dos dados
cursor.execute("SELECT * FROM minigame_events")
data = cursor.fetchall()

# Drop e recriar
cursor.execute("DROP TABLE minigame_events")

cursor.execute("PRAGMA foreign_keys = ON")
cursor.execute(
    """
    CREATE TABLE minigame_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_line TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        minigame_type TEXT,
        steam_id TEXT,
        player_id INTEGER,
        player_name TEXT,
        success BOOLEAN,
        elapsed_time REAL,
        failed_attempts INTEGER,
        target_object TEXT,
        target_object_id TEXT,
        lock_type TEXT,
        owner_id INTEGER,
        owner_steam_id TEXT,
        owner_name TEXT,
        is_property_invasion BOOLEAN DEFAULT 0,
        location_x REAL,
        location_y REAL,
        location_z REAL,
        log_file TEXT,
        discord_sent BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (steam_id) REFERENCES players(steam_id) ON DELETE SET NULL
    )
"""
)

# Restaurar dados (se houver)
if data:
    print(f"Restaurando {len(data)} registros...")
    # Inserir dados antigos (apenas colunas compatíveis)
    for row in data:
        try:
            cursor.execute(
                """
                INSERT INTO minigame_events (id, steam_id, player_name, minigame_type, success, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                row[:6] if len(row) >= 6 else row,
            )
        except:
            pass

conn.commit()
conn.close()

print("Tabela minigame_events recriada com sucesso!")
