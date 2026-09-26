"""
Módulo para criação e gerenciamento das tabelas de transações bancárias
"""
from core.database.connector import DatabaseConnector

import sqlite3
from typing import Optional
from utils.logger import StructuredLogger


def ensure_bank_transaction_tables(
    ssm_db_path: str, logger: Optional[StructuredLogger] = None
):
    """
    Garantir que todas as tabelas de transações bancárias existam e estejam atualizadas.

    Args:
        ssm_db_path: Caminho para o banco SSM.db
        logger: Logger opcional para registrar operações
    """
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()

            # Habilitar foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")

            # 1. Criar tabela transaction_types
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transaction_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT,
                    description TEXT,
                    is_income BOOLEAN,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Migração: adicionar coluna category se não existir
            cursor.execute("PRAGMA table_info(transaction_types)")
            columns = [col[1] for col in cursor.fetchall()]
            if "category" not in columns:
                cursor.execute("ALTER TABLE transaction_types ADD COLUMN category TEXT")
                if logger:
                    logger.info(
                        "Coluna 'category' adicionada à tabela transaction_types"
                    )

            # Criar índices para transaction_types
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_transaction_types_name 
                ON transaction_types(name)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_transaction_types_category 
                ON transaction_types(category)
            """
            )

            # Inserir tipos de transação iniciais (se não existirem)
            initial_types = [
                ("trade_sale", "trade", "Venda de item para trader", True),
                ("trade_purchase", "trade", "Compra de item de trader", False),
                ("bank_deposit", "bank", "Depósito bancário", False),
                ("bank_withdrawal", "bank", "Saque bancário", True),
                (
                    "currency_conversion",
                    "currency",
                    "Conversão de moeda (credits → gold)",
                    False,
                ),
                ("service_repair", "service", "Serviço de reparo de veículo", False),
                (
                    "service_modification",
                    "service",
                    "Serviço de modificação de veículo",
                    False,
                ),
            ]

            for name, category, description, is_income in initial_types:
                # Verificar se já existe
                cursor.execute(
                    "SELECT id FROM transaction_types WHERE name = ?", (name,)
                )
                if not cursor.fetchone():
                    # Inserir apenas se não existir
                    cursor.execute(
                        """
                        INSERT INTO transaction_types (name, category, description, is_income)
                        VALUES (?, ?, ?, ?)
                    """,
                        (name, category, description, is_income),
                    )

            # 2. Criar tabela locations
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quadrant TEXT NOT NULL,
                    location_type TEXT NOT NULL,
                    full_name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    transaction_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Criar índices para locations
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_locations_quadrant 
                ON locations(quadrant)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_locations_type 
                ON locations(location_type)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_locations_full_name 
                ON locations(full_name)
            """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_locations_quadrant_type 
                ON locations(quadrant, location_type)
            """
            )

            # 3. Criar tabela items
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    base_name TEXT,
                    category TEXT,
                    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Migração: adicionar colunas base_name e category se não existirem
            cursor.execute("PRAGMA table_info(items)")
            columns = [col[1] for col in cursor.fetchall()]
            if "base_name" not in columns:
                cursor.execute("ALTER TABLE items ADD COLUMN base_name TEXT")
                if logger:
                    logger.info("Coluna 'base_name' adicionada à tabela items")
            if "category" not in columns:
                cursor.execute("ALTER TABLE items ADD COLUMN category TEXT")
                if logger:
                    logger.info("Coluna 'category' adicionada à tabela items")

            # Criar índices para items
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_items_name 
                ON items(name)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_items_category 
                ON items(category)
            """
            )

            # 4. Criar tabela bank_transactions (com migração se necessário)
            # Verificar se tabela existe e se tem foreign keys
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='bank_transactions'
            """
            )
            table_exists = cursor.fetchone() is not None

            if table_exists:
                # Verificar se tem foreign keys (SQLite não suporta verificar diretamente)
                # Vamos recriar a tabela se necessário para garantir foreign keys
                cursor.execute("PRAGMA table_info(bank_transactions)")
                columns = [col[1] for col in cursor.fetchall()]

                # Se a tabela existe mas não tem todas as colunas necessárias, recriar
                required_columns = [
                    "steam_id",
                    "transaction_type_id",
                    "location_id",
                    "item_id",
                    "transaction_value",
                    "timestamp",
                ]
                if all(col in columns for col in required_columns):
                    # Tabela existe e tem colunas necessárias, verificar se precisa recriar para foreign keys
                    # Como SQLite não permite adicionar foreign keys depois, vamos verificar se precisa recriar
                    # Por enquanto, vamos apenas garantir que a estrutura está correta
                    pass
                else:
                    # Recriar tabela se faltar colunas
                    if logger:
                        logger.warn(
                            "Recriando tabela bank_transactions para adicionar colunas faltantes"
                        )
                    cursor.execute("DROP TABLE IF EXISTS bank_transactions")
                    table_exists = False

            if not table_exists:
                # Criar tabela com foreign keys
                cursor.execute(
                    """
                    CREATE TABLE bank_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        
                        -- Relacionamentos
                        steam_id TEXT NOT NULL,
                        transaction_type_id INTEGER NOT NULL,
                        location_id INTEGER,
                        item_id INTEGER,
                        item_quantity INTEGER DEFAULT 1,
                        
                        -- Valores monetários
                        transaction_value REAL NOT NULL,
                        currency_type TEXT DEFAULT 'money',
                        value_base REAL,
                        value_contained_items REAL DEFAULT 0,
                        
                        -- Saldos ANTES da transação
                        balance_before_money REAL DEFAULT 0,
                        balance_before_gold REAL DEFAULT 0,
                        balance_before_account REAL DEFAULT 0,
                        
                        -- Saldos DEPOIS da transação
                        balance_after_money REAL DEFAULT 0,
                        balance_after_gold REAL DEFAULT 0,
                        balance_after_account REAL DEFAULT 0,
                        
                        -- Informações adicionais (para transações de Trade)
                        trader_funds_before INTEGER,
                        trader_funds_after INTEGER,
                        store_quantity_before INTEGER,
                        store_quantity_after INTEGER,
                        players_online INTEGER,
                        
                        -- Metadados
                        timestamp TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        
                        -- Foreign Keys
                        FOREIGN KEY (steam_id) REFERENCES players(steam_id) ON DELETE CASCADE,
                        FOREIGN KEY (transaction_type_id) REFERENCES transaction_types(id) ON DELETE RESTRICT,
                        FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL,
                        FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
                    )
                """
                )
                if logger:
                    logger.info("Tabela bank_transactions criada com foreign keys")

            # Criar índices para bank_transactions
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_bank_transactions_steam_timestamp 
                ON bank_transactions(steam_id, timestamp DESC)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_bank_transactions_location 
                ON bank_transactions(location_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_bank_transactions_type 
                ON bank_transactions(transaction_type_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_bank_transactions_item 
                ON bank_transactions(item_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_bank_transactions_timestamp 
                ON bank_transactions(timestamp DESC)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_bank_transactions_steam_id 
                ON bank_transactions(steam_id)
            """
            )

            # Migração: adicionar coluna discord_sent se não existir
            cursor.execute("PRAGMA table_info(bank_transactions)")
            columns = [col[1] for col in cursor.fetchall()]
            if "discord_sent" not in columns:
                cursor.execute(
                    "ALTER TABLE bank_transactions ADD COLUMN discord_sent INTEGER DEFAULT 0"
                )
                if logger:
                    logger.info(
                        "Coluna 'discord_sent' adicionada à tabela bank_transactions"
                    )
                
                # Criar índice para consultas rápidas
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_bank_transactions_discord_sent 
                    ON bank_transactions(discord_sent, timestamp DESC)
                """
                )
                if logger:
                    logger.info(
                        "Índice 'idx_bank_transactions_discord_sent' criado"
                    )

            # Migração: colunas de robustez para envio Discord (retry controlado)
            cursor.execute("PRAGMA table_info(bank_transactions)")
            columns = [col[1] for col in cursor.fetchall()]
            if "discord_attempts" not in columns:
                cursor.execute(
                    "ALTER TABLE bank_transactions ADD COLUMN discord_attempts INTEGER DEFAULT 0"
                )
                if logger:
                    logger.info(
                        "Coluna 'discord_attempts' adicionada à tabela bank_transactions"
                    )
            if "discord_last_attempt_at" not in columns:
                cursor.execute(
                    "ALTER TABLE bank_transactions ADD COLUMN discord_last_attempt_at TEXT"
                )
                if logger:
                    logger.info(
                        "Coluna 'discord_last_attempt_at' adicionada à tabela bank_transactions"
                    )
            if "discord_last_error" not in columns:
                cursor.execute(
                    "ALTER TABLE bank_transactions ADD COLUMN discord_last_error TEXT"
                )
                if logger:
                    logger.info(
                        "Coluna 'discord_last_error' adicionada à tabela bank_transactions"
                    )

            # Migração: hash idempotente para evitar duplicação ao reprocessar logs
            cursor.execute("PRAGMA table_info(bank_transactions)")
            columns = [col[1] for col in cursor.fetchall()]
            if "transaction_hash" not in columns:
                cursor.execute(
                    "ALTER TABLE bank_transactions ADD COLUMN transaction_hash TEXT"
                )
                if logger:
                    logger.info(
                        "Coluna 'transaction_hash' adicionada à tabela bank_transactions"
                    )

            # Índice UNIQUE parcial (não quebra registros legados com NULL)
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_transactions_transaction_hash
                ON bank_transactions(transaction_hash)
                WHERE transaction_hash IS NOT NULL
            """
            )

            # Tabela de cursores de leitura dos logs (para não reler tudo ao iniciar)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS log_cursors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    last_line INTEGER NOT NULL DEFAULT 0,
                    last_size INTEGER NOT NULL DEFAULT 0,
                    last_mtime REAL NOT NULL DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_log_cursors_updated
                ON log_cursors(updated_at DESC)
            """
            )

            conn.commit()

            if logger:
                logger.info(
                    "Tabelas de transações bancárias verificadas/criadas com sucesso"
                )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabelas de transações bancárias: {e}")
        raise


def get_or_create_location(
    conn: sqlite3.Connection,
    quadrant: str,
    location_type: str,
    logger: Optional[StructuredLogger] = None,
) -> int:
    """
    Obter ou criar um local e retornar seu ID.

    Args:
        conn: Conexão com o banco
        quadrant: Quadrante (ex: B_4)
        location_type: Tipo de local (ex: Armory)
        logger: Logger opcional

    Returns:
        ID do local
    """
    cursor = conn.cursor()
    full_name = f"{quadrant}_{location_type}"

    # Tentar obter ID existente
    cursor.execute("SELECT id FROM locations WHERE full_name = ?", (full_name,))
    result = cursor.fetchone()

    if result:
        location_id = result[0]
        # Atualizar last_seen e transaction_count
        cursor.execute(
            """
            UPDATE locations 
            SET last_seen = CURRENT_TIMESTAMP, 
                transaction_count = transaction_count + 1
            WHERE id = ?
        """,
            (location_id,),
        )
        return location_id

    # Criar novo local
    cursor.execute(
        """
        INSERT INTO locations (quadrant, location_type, full_name, description, first_seen, last_seen, transaction_count)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
    """,
        (
            quadrant,
            location_type,
            full_name,
            f"{location_type} no quadrante {quadrant}",
        ),
    )

    location_id = cursor.lastrowid
    conn.commit()

    if logger:
        logger.debug(f"Novo local criado: {full_name} (ID: {location_id})")

    return location_id


def get_or_create_item(
    conn: sqlite3.Connection, item_name: str, logger: Optional[StructuredLogger] = None
) -> int:
    """
    Obter ou criar um item e retornar seu ID.

    Args:
        conn: Conexão com o banco
        item_name: Nome base do item (já limpo, sem health/quantidade)
        logger: Logger opcional

    Returns:
        ID do item
    """
    cursor = conn.cursor()

    # Tentar obter ID existente
    cursor.execute("SELECT id FROM items WHERE name = ?", (item_name,))
    result = cursor.fetchone()

    if result:
        item_id = result[0]
        # Atualizar last_seen e usage_count
        cursor.execute(
            """
            UPDATE items 
            SET last_seen = CURRENT_TIMESTAMP, 
                usage_count = usage_count + 1
            WHERE id = ?
        """,
            (item_id,),
        )
        return item_id

    # Criar novo item
    cursor.execute(
        """
        INSERT INTO items (name, base_name, first_seen, last_seen, usage_count)
        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
    """,
        (item_name, item_name),
    )

    item_id = cursor.lastrowid
    conn.commit()

    if logger:
        logger.debug(f"Novo item criado: {item_name} (ID: {item_id})")

    return item_id


def get_transaction_type_id(conn: sqlite3.Connection, type_name: str) -> Optional[int]:
    """
    Obter ID de um tipo de transação.

    Args:
        conn: Conexão com o banco
        type_name: Nome do tipo (ex: 'trade_sale')

    Returns:
        ID do tipo ou None se não encontrado
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM transaction_types WHERE name = ?", (type_name,))
    result = cursor.fetchone()
    return result[0] if result else None
