"""
Módulo centralizado para inicialização do banco de dados SSM.db
"""
from core.database.connector import DatabaseConnector

import sqlite3
import os
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
from utils.logger import StructuredLogger
from utils.config_path_helper import ConfigPathHelper


# Lista completa de tabelas obrigatórias que devem existir
EXPECTED_TABLES = [
    # Autenticação e Usuários
    "frontend_users",
    "password_reset_tokens",
    # Jogadores e Rankings
    "rankings",
    "fishing_rankings",
    "players",
    "players_online",
    "player_fame_totals",
    "player_permissions",
    "player_webhooks",
    # Squads
    "squad_snapshot",
    "squad_member_snapshot",
    # Estatísticas de Sobrevivência
    "survival_stats_snapshot",
    "player_skills",
    # Sistema Bancário
    "bank_accounts_snapshot",
    "bank_transactions",
    "transaction_types",
    "locations",
    "items",
    # Baús (Chests)
    "chest_snapshot",
    "chest_history",
    "chest_inventory_snapshot",
    "chest_inventory_item",
    "item_catalog",
    # GPS e Localização
    "player_gps_snapshot",
    # Elevated Users
    "elevated_user",
    # Eventos
    "kill_events",
    "minigame_events",
    "minigame_event_deliveries",
    "vehicle_destruction_events",
    "admin_commands_processed",
    # Veículos
    "vehicle_current_ownership",
    "vehicle_ownership_history",
    "vehicle_order",
    "vehicle_catalog",
    "base_material_job",
    "base_material_flag_policy",
    # Sistema de Logs
    "log_files_processed",
    "log_cursors",
    "player_logins",
    # Licenciamento
    "hardware_fingerprints",
    # Clima
    "weather_parameters",
    # Bunkers
    "bunker_status",
    # Preços de atributos
    "attribute_upgrade_prices",
    # Cache de atributos do jogador
    "player_attributes_cache",
    # Upgrades temporários de atributos
    "player_attribute_upgrades",
    # Shop + Mailbox + Economy
    "app_config",
    "player_mailbox",
    "shop_catalog",
    "shop_offer",
    "shop_order",
    "shop_order_item",
    "shop_delivery_item",
    "shop_kit",
    "shop_kit_item",
    "wallet",
    "wallet_tx",
    "admin_credit",
    "integration_keys",
    "integration_requests",
    "time_reward_state",
    "playtime_reward_rules",
    "playtime_reward_state",
    "playtime_reward_targets",
]

# Tabelas opcionais (não contam para verificação de inicialização completa)
OPTIONAL_TABLES = [
    "frontend_user_permissions",
    "frontend_user_groups",
    "frontend_user_group_members",
    "license_validations",
    "custom_zone_region",
    "abandoned_bunker",
    "abandoned_bunker_mesh_instance_bound_to_activation",
]


def get_existing_tables(ssm_db_path: str) -> List[str]:
    """
    Obtém lista de todas as tabelas existentes no banco.

    Args:
        ssm_db_path: Caminho para o banco SSM.db

    Returns:
        Lista de nomes de tabelas (sem tabelas do sistema)
    """
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()

            # Consultar sqlite_master para obter apenas tabelas
            cursor.execute(
                """
                SELECT name 
                FROM sqlite_master 
                WHERE type='table' 
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """
            )

            # sqlite_% são tabelas do sistema (sqlite_sequence, etc.)
            # Não queremos incluí-las na contagem

            tables = [row[0] for row in cursor.fetchall()]
            return tables

    except sqlite3.Error as e:
        return []
    except Exception:
        return []


def get_columns_per_table(ssm_db_path: str, tables: List[str]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            for table in tables:
                try:
                    cursor.execute(f"PRAGMA table_info('{table}')")
                    cols = cursor.fetchall()
                    result[table] = len(cols)
                except Exception:
                    result[table] = 0
        return result
    except Exception:
        return {t: 0 for t in tables}


def check_database_status(ssm_db_path: str) -> Dict:
    """
    Verifica o status completo do banco de dados.

    Args:
        ssm_db_path: Caminho para o banco SSM.db

    Returns:
        {
            'exists': bool,
            'initialized': bool,
            'table_count': int,
            'expected_tables': int,
            'tables': List[str],
            'missing_tables': List[str],
            'optional_tables': List[str],
            'size_bytes': int,
            'size_mb': float,
            'last_modified': Optional[str],
            'status_message': str,
            'path': str
        }
    """
    result = {
        "exists": False,
        "initialized": False,
        "table_count": 0,
        "required_table_count": 0,
        "expected_tables": len(EXPECTED_TABLES),
        "tables": [],
        "missing_tables": [],
        "optional_tables": [],
        "size_bytes": 0,
        "size_mb": 0.0,
        "last_modified": None,
        "status_message": "",
        "path": ssm_db_path,
    }

    # Verificar se arquivo existe
    if not os.path.exists(ssm_db_path):
        result["status_message"] = "❌ Banco não encontrado"
        return result

    result["exists"] = True

    # Obter informações do arquivo
    try:
        stat = os.stat(ssm_db_path)
        result["size_bytes"] = stat.st_size
        result["size_mb"] = round(stat.st_size / (1024 * 1024), 2)
        result["last_modified"] = datetime.fromtimestamp(stat.st_mtime).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    except Exception:
        pass

    # Obter tabelas existentes
    existing_tables = get_existing_tables(ssm_db_path)
    result["tables"] = existing_tables
    result["table_count"] = len(existing_tables)
    result["columns_per_table"] = get_columns_per_table(ssm_db_path, existing_tables)

    # Separar tabelas esperadas, opcionais e faltantes
    existing_set = set(existing_tables)
    expected_set = set(EXPECTED_TABLES)
    optional_set = set(OPTIONAL_TABLES)

    # Quantas tabelas obrigatórias existem (não conta tabelas opcionais/extras)
    result["required_table_count"] = len(expected_set & existing_set)

    # Tabelas faltantes (esperadas mas não existentes)
    result["missing_tables"] = sorted(list(expected_set - existing_set))

    # Tabelas opcionais encontradas
    result["optional_tables"] = sorted(list(optional_set & existing_set))

    # Verificar se está inicializado
    # Considera inicializado se todas as tabelas esperadas existem
    result["initialized"] = len(result["missing_tables"]) == 0

    # Gerar mensagem de status
    if not result["exists"]:
        result["status_message"] = "❌ Banco não encontrado"
    elif result["table_count"] == 0:
        result["status_message"] = "⚠️ Banco existe mas está vazio"
    elif result["initialized"]:
        result["status_message"] = (
            f'✅ Banco inicializado ({result["table_count"]} tabelas)'
        )
    else:
        missing_count = len(result["missing_tables"])
        result["status_message"] = (
            f'⚠️ Banco parcialmente inicializado ({result["required_table_count"]}/{result["expected_tables"]} tabelas, faltam {missing_count})'
        )

    return result


def initialize_all_tables(
    ssm_db_path: str,
    config: Optional[Dict] = None,
    path_helper: Optional[ConfigPathHelper] = None,
    logger: Optional[StructuredLogger] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict:
    """
    Inicializa todas as tabelas do banco de dados.

    Args:
        ssm_db_path: Caminho para o banco
        config: Configuração do sistema (opcional)
        path_helper: Helper de caminhos (opcional)
        logger: Logger opcional
        progress_callback: Função callback(current, total, table_name)

    Returns:
        {
            'success': bool,
            'tables_created': int,
            'tables_total': int,
            'errors': List[Dict],
            'duration_seconds': float
        }
    """
    start_time = time.time()
    errors = []
    tables_created = 0
    total_tables = len(EXPECTED_TABLES)

    if logger:
        logger.info("Iniciando inicialização de todas as tabelas do banco de dados")

    # Ordem de criação (respeitando dependências)
    initialization_steps = [
        # Fase 1: Tabelas base (sem dependências)
        ("hardware_fingerprints", _init_hardware_fingerprints),
        ("transaction_types", _init_bank_transaction_tables),
        ("locations", _init_bank_transaction_tables),
        ("items", _init_bank_transaction_tables),
        ("bank_transactions", _init_bank_transaction_tables),
        ("bunker_status", _init_bunker_status),
        ("attribute_upgrade_prices", _init_attribute_upgrade_prices),
        ("player_attributes_cache", _init_player_attributes_cache),
        ("player_attribute_upgrades", _init_player_attribute_upgrades),
        ("admin_commands_processed", _init_admin_commands_processed),
        ("app_config", _init_app_config),
        ("wallet", _init_wallet),
        ("wallet_tx", _init_wallet_tx),
        ("admin_credit", _init_admin_credit),
        ("integration_keys", _init_integration_keys),
        ("integration_requests", _init_integration_requests),
        ("time_reward_state", _init_time_reward_state),
        ("playtime_reward_rules", _init_playtime_reward_rules),
        ("playtime_reward_state", _init_playtime_reward_state),
        ("playtime_reward_targets", _init_playtime_reward_targets),
        # Fase 2: Tabelas de usuários e players (base para outras tabelas)
        ("frontend_users", _init_frontend_users),
        ("password_reset_tokens", _init_password_reset_tokens),
        ("players", _init_players),
        ("players_online", _init_players_online),
        # Fase 3: Tabelas de dados (podem depender de players)
        ("rankings", _init_rankings),
        ("fishing_rankings", _init_fishing_rankings),
        ("player_fame_totals", _init_player_fame_totals),
        ("player_permissions", _init_player_permissions),
        ("player_webhooks", _init_player_webhooks),
        ("squad_snapshot", _init_squad_tables),
        ("squad_member_snapshot", _init_squad_tables),
        ("survival_stats_snapshot", _init_survival_stats),
        ("player_skills", _init_player_skills),
        ("bank_accounts_snapshot", _init_bank_accounts),
        ("chest_snapshot", _init_chest_tables),
        ("chest_history", _init_chest_tables),
        ("chest_inventory_snapshot", _init_chest_tables),
        ("chest_inventory_item", _init_chest_tables),
        ("item_catalog", _init_chest_tables),
        ("player_mailbox", _init_player_mailbox),
        ("shop_catalog", _init_shop_catalog),
        ("shop_offer", _init_shop_offer),
        ("shop_order", _init_shop_order),
        ("shop_order_item", _init_shop_order_item),
        ("shop_delivery_item", _init_shop_delivery_item),
        ("shop_kit", _init_shop_kit),
        ("shop_kit_item", _init_shop_kit),
        ("player_gps_snapshot", _init_player_gps),
        ("elevated_user", _init_elevated_users),
        ("kill_events", _init_kill_events),
        ("minigame_events", _init_minigame_events),
        ("minigame_event_deliveries", _init_minigame_event_deliveries),
        ("vehicle_destruction_events", _init_vehicle_events),
        ("vehicle_current_ownership", _init_vehicle_events),
        ("vehicle_ownership_history", _init_vehicle_events),
        ("vehicle_order", _init_vehicle_order),
        ("vehicle_catalog", _init_vehicle_catalog),
        ("base_material_job", _init_base_material_tables),
        ("base_material_flag_policy", _init_base_material_tables),
        ("log_files_processed", _init_log_tables),
        ("log_cursors", _init_log_tables),
        ("player_logins", _init_log_tables),
        ("server_time_state", _init_server_time_state),
        ("weather_parameters", _init_weather_parameters),
    ]

    # Verificar quais tabelas já existem
    existing_tables = set(get_existing_tables(ssm_db_path))

    # Tabelas que precisam executar init mesmo quando já existem (migrações/ALTER TABLE/Sincronização)
    migrate_always_tables = {
        "vehicle_order",
        "vehicle_catalog",
        "shop_kit",
        "attribute_upgrade_prices",
    }

    for table_name, init_func in initialization_steps:
        # Pular se tabela já existe
        if table_name in existing_tables:
            if table_name in migrate_always_tables:
                try:
                    init_func(ssm_db_path, config, path_helper, logger)
                except Exception as e:
                    error_msg = str(e)
                    errors.append({"table": table_name, "error": error_msg})
                    if logger:
                        logger.error(
                            f"Erro ao migrar tabela existente {table_name}: {error_msg}"
                        )

            if progress_callback:
                progress_callback(tables_created, total_tables, table_name)
            tables_created += 1
            continue

        try:
            # Chamar função de inicialização
            init_func(ssm_db_path, config, path_helper, logger)

            # Verificar se tabela foi criada
            if table_name in get_existing_tables(ssm_db_path):
                tables_created += 1
                if logger:
                    logger.debug(f"Tabela {table_name} criada com sucesso")
            else:
                errors.append(
                    {
                        "table": table_name,
                        "error": "Tabela não foi criada após chamada de inicialização",
                    }
                )
                if logger:
                    logger.warn(f"Tabela {table_name} não foi criada")

            # Chamar callback de progresso
            if progress_callback:
                progress_callback(tables_created, total_tables, table_name)

        except Exception as e:
            error_msg = str(e)
            errors.append({"table": table_name, "error": error_msg})
            if logger:
                logger.error(f"Erro ao criar tabela {table_name}: {error_msg}")

    duration = time.time() - start_time

    result = {
        "success": len(errors) == 0,
        "tables_created": tables_created,
        "tables_total": total_tables,
        "errors": errors,
        "duration_seconds": round(duration, 2),
    }

    if logger:
        if result["success"]:
            logger.info(
                f"Inicialização concluída: {tables_created}/{total_tables} tabelas criadas em {duration:.2f}s"
            )
        else:
            logger.warn(
                f"Inicialização parcial: {tables_created}/{total_tables} tabelas criadas, {len(errors)} erros"
            )

    return result


# Funções auxiliares de inicialização por módulo


def _init_hardware_fingerprints(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela hardware_fingerprints"""
    from core.licensing.license_cache import LicenseCache

    cache = LicenseCache(
        data_dir=os.path.dirname(ssm_db_path), db_path=ssm_db_path, logger=logger
    )
    cache._ensure_table()


def _init_bank_transaction_tables(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabelas de transações bancárias"""
    from core.banking.bank_transaction_tables import ensure_bank_transaction_tables

    ensure_bank_transaction_tables(ssm_db_path, logger)


def _init_frontend_users(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela frontend_users"""
    from core.auth.user_manager import UserManager

    user_manager = UserManager(ssm_db_path, logger)
    user_manager.ensure_table()


def _init_password_reset_tokens(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela password_reset_tokens"""
    from core.auth.password_reset import PasswordResetManager

    reset_manager = PasswordResetManager(ssm_db_path, logger)
    reset_manager.ensure_table()


def _init_rankings(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela rankings com schema completo"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    
                    -- kill_events
                    kills INTEGER DEFAULT 0,
                    deaths INTEGER DEFAULT 0,
                    kdr REAL DEFAULT 0,
                    longest_shot_distance REAL DEFAULT 0,
                    longest_shot_weapon TEXT,
                    longest_shot_timestamp DATETIME,
                    suicides INTEGER DEFAULT 0,
                    
                    -- minigame_events por tipo de fechadura
                    lockpick_basic_success INTEGER DEFAULT 0,
                    lockpick_basic_fails INTEGER DEFAULT 0,
                    lockpick_basic_total INTEGER DEFAULT 0,
                    lockpick_basic_rate REAL DEFAULT 0,
                    
                    lockpick_medium_success INTEGER DEFAULT 0,
                    lockpick_medium_fails INTEGER DEFAULT 0,
                    lockpick_medium_total INTEGER DEFAULT 0,
                    lockpick_medium_rate REAL DEFAULT 0,
                    
                    lockpick_advanced_success INTEGER DEFAULT 0,
                    lockpick_advanced_fails INTEGER DEFAULT 0,
                    lockpick_advanced_total INTEGER DEFAULT 0,
                    lockpick_advanced_rate REAL DEFAULT 0,
                    
                    lockpick_veryeasy_success INTEGER DEFAULT 0,
                    lockpick_veryeasy_fails INTEGER DEFAULT 0,
                    lockpick_veryeasy_total INTEGER DEFAULT 0,
                    lockpick_veryeasy_rate REAL DEFAULT 0,
                    
                    lockpick_diallock_success INTEGER DEFAULT 0,
                    lockpick_diallock_fails INTEGER DEFAULT 0,
                    lockpick_diallock_total INTEGER DEFAULT 0,
                    lockpick_diallock_rate REAL DEFAULT 0,
                    
                    lockpick_other_success INTEGER DEFAULT 0,
                    lockpick_other_fails INTEGER DEFAULT 0,
                    lockpick_other_total INTEGER DEFAULT 0,
                    lockpick_other_rate REAL DEFAULT 0,
                    
                    -- vehicle_destruction_events
                    vehicles_destroyed INTEGER DEFAULT 0,
                    
                    -- survival_stats_snapshot
                    highest_defecation INTEGER DEFAULT 0,
                    animals_killed INTEGER DEFAULT 0,
                    players_knocked_out INTEGER DEFAULT 0,
                    headshots INTEGER DEFAULT 0,
                    minutes_survived REAL DEFAULT 0,
                    overdoses INTEGER DEFAULT 0,
                    highest_weight_carried REAL DEFAULT 0,
                    
                    -- METADATA
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_fame REAL DEFAULT 0.0,
                    
                    UNIQUE(steam_id)
                )
            """
            )
            conn.commit()
            if logger:
                logger.debug("Tabela rankings verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela rankings: {e}")
        raise


def _init_server_time_state(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS server_time_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    baseline_time_of_day REAL,
                    baseline_real_ts_utc TEXT,
                    time_scale REAL,
                    last_verified_ts_utc TEXT,
                    last_real_time_of_day REAL,
                    last_drift_seconds REAL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO server_time_state (id, time_scale)
                VALUES (1, 1.0)
            """
            )
            conn.commit()
            if logger:
                logger.debug("Tabela server_time_state verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela server_time_state: {e}")
        raise


def _init_app_config(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela app_config: {e}")
        raise


def _init_wallet(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS wallet (
                    steam_id TEXT PRIMARY KEY,
                    balance INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela wallet: {e}")
        raise


def _init_wallet_tx(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS wallet_tx (
                    tx_id TEXT PRIMARY KEY,
                    steam_id TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    ref_type TEXT,
                    ref_id TEXT,
                    meta_json TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_wallet_tx_ref
                ON wallet_tx(steam_id, reason, ref_type, ref_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_wallet_tx_steam_id
                ON wallet_tx(steam_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_wallet_tx_ref
                ON wallet_tx(ref_type, ref_id)
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela wallet_tx: {e}")
        raise


def _init_admin_credit(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_credit (
                    credit_id TEXT PRIMARY KEY,
                    external_id TEXT NOT NULL,
                    steam_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'applied',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_admin_credit_external
                ON admin_credit(external_id)
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela admin_credit: {e}")
        raise


def _init_integration_keys(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS integration_keys (
                    key_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    last_used_at TEXT
                )
            """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_integration_keys_hash
                ON integration_keys(key_hash)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_integration_keys_enabled
                ON integration_keys(enabled)
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela integration_keys: {e}")
        raise


def _init_integration_requests(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS integration_requests (
                    req_id TEXT PRIMARY KEY,
                    key_id TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    steam_id TEXT,
                    request_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (key_id) REFERENCES integration_keys(key_id) ON DELETE CASCADE
                )
            """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_integration_requests_idempotency
                ON integration_requests(key_id, endpoint, external_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_integration_requests_created
                ON integration_requests(created_at)
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela integration_requests: {e}")
        raise


def _init_time_reward_state(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS time_reward_state (
                    steam_id TEXT PRIMARY KEY,
                    last_awarded_epoch INTEGER,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela time_reward_state: {e}")
        raise


def _init_playtime_reward_rules(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS playtime_reward_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    exclusive INTEGER NOT NULL DEFAULT 0,
                    points_per_hour INTEGER NOT NULL DEFAULT 0,
                    max_hours_per_run INTEGER NOT NULL DEFAULT 0,
                    audience_type TEXT NOT NULL DEFAULT 'all',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_playtime_reward_rules_enabled
                ON playtime_reward_rules(enabled)
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela playtime_reward_rules: {e}")
        raise


def _init_playtime_reward_state(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS playtime_reward_state (
                    rule_id TEXT NOT NULL,
                    steam_id TEXT NOT NULL,
                    last_paid_playtime_hours INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    PRIMARY KEY(rule_id, steam_id),
                    FOREIGN KEY (rule_id) REFERENCES playtime_reward_rules(rule_id) ON DELETE CASCADE,
                    FOREIGN KEY (steam_id) REFERENCES players(steam_id) ON DELETE CASCADE
                )
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_playtime_reward_state_steam
                ON playtime_reward_state(steam_id)
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela playtime_reward_state: {e}")
        raise


def _init_playtime_reward_targets(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS playtime_reward_targets (
                    rule_id TEXT NOT NULL,
                    steam_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    PRIMARY KEY(rule_id, steam_id),
                    FOREIGN KEY (rule_id) REFERENCES playtime_reward_rules(rule_id) ON DELETE CASCADE,
                    FOREIGN KEY (steam_id) REFERENCES players(steam_id) ON DELETE CASCADE
                )
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_playtime_reward_targets_rule
                ON playtime_reward_targets(rule_id)
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela playtime_reward_targets: {e}")
        raise


def _init_base_material_tables(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        from core.base_material.base_material_job_service import BaseMaterialJobService

        scum_db_path = None
        try:
            if path_helper:
                scum_db_path = path_helper.get_scum_db_path()
        except Exception:
            scum_db_path = None

        BaseMaterialJobService(
            ssm_db_path=ssm_db_path,
            scum_db_path=str(scum_db_path or ""),
            template_db_path="data/templates/scum_base_template.db",
            logger=logger,
        )
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabelas base_material: {e}")
        raise


def _init_player_mailbox(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS player_mailbox (
                    steam_id TEXT PRIMARY KEY,
                    chest_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela player_mailbox: {e}")
        raise


def _init_shop_catalog(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_catalog (
                    code INTEGER PRIMARY KEY,
                    setup TEXT NOT NULL UNIQUE,
                    display_name TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela shop_catalog: {e}")
        raise


def _init_shop_offer(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_offer (
                    code INTEGER PRIMARY KEY,
                    qty INTEGER NOT NULL DEFAULT 1,
                    price INTEGER NOT NULL DEFAULT 0,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    max_per_order INTEGER,
                    max_per_day INTEGER,
                    FOREIGN KEY (code) REFERENCES shop_catalog(code)
                )
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela shop_offer: {e}")
        raise


def _init_shop_order(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_order (
                    order_id TEXT PRIMARY KEY,
                    steam_id TEXT NOT NULL,
                    chest_id INTEGER,
                    total_price INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    last_attempt_at TEXT,
                    retry_requested INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    delivered_at TEXT,
                    error TEXT
                )
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_shop_order_status_created
                ON shop_order(status, created_at)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_shop_order_steam_id_created
                ON shop_order(steam_id, created_at)
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela shop_order: {e}")
        raise


def _init_shop_order_item(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_order_item (
                    order_id TEXT NOT NULL,
                    code INTEGER NOT NULL,
                    setup TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    PRIMARY KEY (order_id, code),
                    FOREIGN KEY (order_id) REFERENCES shop_order(order_id)
                )
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela shop_order_item: {e}")
        raise


def _init_shop_delivery_item(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_delivery_item (
                    order_id TEXT NOT NULL,
                    code INTEGER NOT NULL,
                    qty_delivered INTEGER NOT NULL DEFAULT 0,
                    last_delivered_at TEXT,
                    PRIMARY KEY (order_id, code),
                    FOREIGN KEY (order_id) REFERENCES shop_order(order_id)
                )
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela shop_delivery_item: {e}")
        raise


def _init_shop_kit(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            # Desativar foreign keys temporariamente para evitar cascade delete durante a migração
            cursor.execute("PRAGMA foreign_keys = OFF")

            # Verificar se precisa migrar (se colunas price/enabled estão ausentes ou se tem FK para shop_catalog)
            cursor.execute("PRAGMA table_info('shop_kit')")
            existing_cols = {str(r[1]) for r in (cursor.fetchall() or [])}
            
            has_fk_to_catalog = False
            if existing_cols:
                cursor.execute("PRAGMA foreign_key_list('shop_kit')")
                fk_list = cursor.fetchall()
                has_fk_to_catalog = any(str(fk[2]).lower() == "shop_catalog" for fk in fk_list)

            if not existing_cols:
                # Criar tabela do zero
                cursor.execute(
                    """
                    CREATE TABLE shop_kit (
                        kit_id TEXT PRIMARY KEY,
                        code INTEGER NOT NULL UNIQUE,
                        name TEXT NOT NULL,
                        price INTEGER NOT NULL DEFAULT 0,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        only_once INTEGER NOT NULL DEFAULT 0,
                        auto_deliver_on_register INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                    )
                    """
                )
            elif "price" not in existing_cols or "enabled" not in existing_cols or has_fk_to_catalog:
                # Executar migração
                if logger:
                    logger.info("Migrando tabela shop_kit para remover chave estrangeira e adicionar colunas de preco/status...")
                
                cursor.execute("DROP TABLE IF EXISTS _shop_kit_old")
                cursor.execute("ALTER TABLE shop_kit RENAME TO _shop_kit_old")
                
                cursor.execute(
                    """
                    CREATE TABLE shop_kit (
                        kit_id TEXT PRIMARY KEY,
                        code INTEGER NOT NULL UNIQUE,
                        name TEXT NOT NULL,
                        price INTEGER NOT NULL DEFAULT 0,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        only_once INTEGER NOT NULL DEFAULT 0,
                        auto_deliver_on_register INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                    )
                    """
                )
                
                cursor.execute("PRAGMA table_info('_shop_kit_old')")
                old_cols = {str(r[1]) for r in (cursor.fetchall() or [])}
                
                src_cols = ["kit_id", "code", "name"]
                dest_cols = ["kit_id", "code", "name"]
                
                if "only_once" in old_cols:
                    src_cols.append("only_once")
                    dest_cols.append("only_once")
                if "auto_deliver_on_register" in old_cols:
                    src_cols.append("auto_deliver_on_register")
                    dest_cols.append("auto_deliver_on_register")
                if "created_at" in old_cols:
                    src_cols.append("created_at")
                    dest_cols.append("created_at")
                if "updated_at" in old_cols:
                    src_cols.append("updated_at")
                    dest_cols.append("updated_at")
                
                # Copiar dados recuperando preços e status das ofertas/catálogo anteriores se existirem
                cursor.execute(
                    f"""
                    INSERT INTO shop_kit (
                        {', '.join(dest_cols)}, price, enabled
                    )
                    SELECT 
                        {', '.join(['o.' + c for c in src_cols])},
                        COALESCE((SELECT price FROM shop_offer WHERE code = o.code), 0) as price,
                        COALESCE((SELECT enabled FROM shop_catalog WHERE code = o.code), 1) as enabled
                    FROM _shop_kit_old o
                    """
                )
                cursor.execute("DROP TABLE _shop_kit_old")

            # Ativar foreign keys novamente
            cursor.execute("PRAGMA foreign_keys = ON")

            # Criar tabela de itens do kit
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_kit_item (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kit_id TEXT NOT NULL,
                    setup TEXT NOT NULL,
                    qty INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (kit_id) REFERENCES shop_kit(kit_id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_shop_kit_item_kit_id ON shop_kit_item(kit_id)"
            )

            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabelas de kits da loja: {e}")
        raise



def _init_fishing_rankings(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela fishing_rankings com schema completo"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fishing_rankings (
                    steam_id TEXT PRIMARY KEY,
                    player_name TEXT NOT NULL,
                    
                    -- Estatísticas gerais
                    fish_caught INTEGER DEFAULT 0,
                    fish_kept INTEGER DEFAULT 0,
                    fish_released INTEGER DEFAULT 0,
                    lines_broken INTEGER DEFAULT 0,
                    
                    -- Recordes
                    heaviest_fish_caught REAL DEFAULT 0,
                    longest_fish_caught REAL DEFAULT 0,
                    
                    -- Por espécie (todos os campos da fishing_stats)
                    bass_caught INTEGER DEFAULT 0,
                    catfish_caught INTEGER DEFAULT 0,
                    pike_caught INTEGER DEFAULT 0,
                    carp_caught INTEGER DEFAULT 0,
                    amur_caught INTEGER DEFAULT 0,
                    bleak_caught INTEGER DEFAULT 0,
                    chub_caught INTEGER DEFAULT 0,
                    ruffe_caught INTEGER DEFAULT 0,
                    prussian_carp_caught INTEGER DEFAULT 0,
                    crucian_carp_caught INTEGER DEFAULT 0,
                    sardine_caught INTEGER DEFAULT 0,
                    dentex_caught INTEGER DEFAULT 0,
                    orata_caught INTEGER DEFAULT 0,
                    tuna_caught INTEGER DEFAULT 0,
                    
                    -- Metadata
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Criar índices
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_fishing_rankings_steam_id ON fishing_rankings(steam_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_fishing_rankings_fish_caught ON fishing_rankings(fish_caught DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_fishing_rankings_last_updated ON fishing_rankings(last_updated DESC)"
            )

            conn.commit()
            if logger:
                logger.debug("Tabela fishing_rankings verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela fishing_rankings: {e}")
        raise


def _init_squad_tables(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabelas de squads"""
    if not config:
        config = {}
    from core.squads.squad_sync_service import SquadSyncService

    squad_service = SquadSyncService(config, path_helper, logger)
    squad_service.ensure_tables()


def _init_survival_stats(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela survival_stats_snapshot"""
    if not config:
        config = {}
    from core.survival.survival_stats_sync_service import SurvivalStatsSyncService

    try:
        survival_service = SurvivalStatsSyncService(config, path_helper, logger)
        survival_service.ensure_table()
        return
    except Exception as e:
        # Fallback: em instalações novas, o SCUM.db pode não existir ainda.
        # Para permitir "Create / Repair Database" completar 35/35, criamos uma
        # tabela mínima. Quando o SCUM.db estiver disponível, o serviço de sync
        # poderá complementar o schema via ALTER TABLE.
        if logger:
            logger.warn(
                f"Falha ao garantir schema dinamico de survival_stats_snapshot ({e}); criando tabela minima"
            )
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS survival_stats_snapshot (
                    steam_id TEXT,
                    player_name TEXT,
                    snapshot_at TEXT NOT NULL
                )
            """
            )
            conn.commit()


def _init_player_skills(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela player_skills"""
    if not config:
        config = {}
    from core.survival.player_skills_sync_service import PlayerSkillsSyncService

    skills_service = PlayerSkillsSyncService(config, path_helper, logger)
    skills_service.ensure_table()


def _init_bank_accounts(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela bank_accounts_snapshot"""
    if not config:
        config = {}
    from core.banking.bank_account_sync_service import BankAccountSyncService

    bank_service = BankAccountSyncService(config, path_helper, logger)
    bank_service.ensure_table()


def _init_chest_tables(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabelas de baús"""
    if not config:
        config = {}
    from core.chests.chest_sync_service import ChestSyncService

    chest_service = ChestSyncService(config, path_helper, logger)
    chest_service.ensure_tables()

    # Tabelas do inventário do baú (Player App)
    with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chest_inventory_snapshot (
                chest_entity_id INTEGER PRIMARY KEY,
                steam_id TEXT,
                player_name TEXT,
                scanned_at TEXT NOT NULL,
                items_total INTEGER DEFAULT 0
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chest_inventory_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chest_entity_id INTEGER NOT NULL,
                item_entity_id INTEGER NOT NULL,
                item_class TEXT,
                slot_index INTEGER,
                scanned_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_chest_inventory_item_chest ON chest_inventory_item (chest_entity_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_chest_inventory_item_class ON chest_inventory_item (item_class)"
        )

        # Catálogo/normalização de itens (por classe)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS item_catalog (
                item_class TEXT PRIMARY KEY,
                display_name TEXT,
                category TEXT,
                icon TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()


def _init_player_gps(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela player_gps_snapshot"""
    if not config:
        config = {}
    from core.gps.player_gps_sync_service import PlayerGpsSyncService

    gps_service = PlayerGpsSyncService(config, path_helper, logger)
    gps_service.ensure_table()


def _init_elevated_users(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela elevated_user"""
    if not config:
        config = {}
    from core.elevated_users.elevated_users_manager import ElevatedUsersManager

    # ElevatedUsersManager precisa de server_manager, mas podemos criar apenas a tabela
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS elevated_user (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id TEXT NOT NULL,
                    synced INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    synced_at DATETIME,
                    UNIQUE(steam_id)
                )
            """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela elevated_user: {e}")
        raise


def _init_kill_events(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela kill_events com schema completo"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS kill_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    game_time TEXT,
                    -- Vítima
                    victim_steam_id TEXT,
                    victim_player_id INTEGER,
                    victim_name TEXT NOT NULL,
                    victim_location_x REAL,
                    victim_location_y REAL,
                    victim_location_z REAL,
                    -- Killer (pode ser NPC ou jogador)
                    killer_steam_id TEXT,
                    killer_user_id TEXT,
                    killer_profile_name TEXT,
                    killer_is_npc BOOLEAN DEFAULT 0,
                    killer_location_x REAL,
                    killer_location_y REAL,
                    killer_location_z REAL,
                    killer_has_immortality BOOLEAN DEFAULT 0,
                    -- Arma e combate
                    weapon TEXT,
                    weapon_type TEXT,
                    distance REAL,
                    -- Contexto
                    is_in_game_event BOOLEAN DEFAULT 0,
                    log_file TEXT,
                    raw_json TEXT,
                    discord_sent BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()
            if logger:
                logger.debug("Tabela kill_events verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela kill_events: {e}")
        raise


def _init_minigame_events(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela minigame_events com schema completo"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS minigame_events (
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
            conn.commit()
            if logger:
                logger.debug("Tabela minigame_events verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela minigame_events: {e}")
        raise


def _init_vehicle_events(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabelas de veículos com schemas completos"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()

            # vehicle_destruction_events
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vehicle_destruction_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL,
                    vehicle_name TEXT NOT NULL,
                    owner_steam_id TEXT,
                    owner_id INTEGER,
                    owner_name TEXT,
                    event_type TEXT NOT NULL,
                    location_x REAL,
                    location_y REAL,
                    location_z REAL,
                    timestamp DATETIME NOT NULL,
                    discord_sent BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # vehicle_current_ownership
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vehicle_current_ownership (
                    entity_id INTEGER PRIMARY KEY,
                    vehicle_entity_id INTEGER,
                    steam_id TEXT NOT NULL,
                    player_id INTEGER,
                    player_name TEXT NOT NULL,
                    location_x REAL,
                    location_y REAL,
                    location_z REAL,
                    last_ownership_change DATETIME NOT NULL,
                    container_class TEXT,
                    vehicle_class TEXT,
                    vehicle_asset_id TEXT,
                    is_vehicle_functional INTEGER,
                    status INTEGER DEFAULT 0,
                    notification_sent BOOLEAN DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # vehicle_ownership_history
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vehicle_ownership_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER NOT NULL,
                    vehicle_entity_id INTEGER,
                    steam_id TEXT NOT NULL,
                    player_id INTEGER,
                    player_name TEXT NOT NULL,
                    ownership_type TEXT NOT NULL,
                    previous_owner_steam_id TEXT,
                    previous_owner_name TEXT,
                    location_x REAL,
                    location_y REAL,
                    location_z REAL,
                    timestamp DATETIME NOT NULL,
                    log_file TEXT,
                    container_class TEXT,
                    vehicle_class TEXT,
                    vehicle_asset_id TEXT,
                    is_vehicle_functional INTEGER,
                    notification_sent BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()
            if logger:
                logger.debug("Tabelas de veículos verificadas/criadas com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabelas de veículos: {e}")
        raise


def _init_vehicle_order(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            conn.execute("PRAGMA busy_timeout = 30000")
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vehicle_order (
                    order_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,

                    template_vehicle_entity_id INTEGER NOT NULL,
                    new_x REAL NOT NULL,
                    new_y REAL NOT NULL,
                    new_z REAL NOT NULL,
                    keep_template_rotation INTEGER NOT NULL DEFAULT 1,
                    new_rot_x REAL,
                    new_rot_y REAL,
                    new_rot_z REAL,

                    status TEXT NOT NULL DEFAULT 'pending',
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at TEXT,
                    locked_by TEXT,
                    locked_at TEXT,

                    restart_cycle_id TEXT,

                    spawned_vehicle_entity_id INTEGER,
                    spawned_container_entity_id INTEGER,
                    spawned_container_component_id INTEGER,

                    error_code TEXT,
                    error_message TEXT,

                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )

            try:
                cursor.execute("PRAGMA table_info('vehicle_order')")
                existing_cols = {str(r[1]) for r in (cursor.fetchall() or [])}

                def _safe_add(col: str, ddl: str) -> None:
                    if col in existing_cols:
                        return
                    try:
                        cursor.execute(ddl)
                    except sqlite3.OperationalError as oe:
                        msg = str(oe or "")
                        # Se duas instâncias tentarem migrar ao mesmo tempo, pode ocorrer duplicate column
                        if "duplicate column name" in msg.lower():
                            return
                        raise

                _safe_add(
                    "requested_steam_id",
                    "ALTER TABLE vehicle_order ADD COLUMN requested_steam_id TEXT",
                )
                _safe_add(
                    "requested_player_name",
                    "ALTER TABLE vehicle_order ADD COLUMN requested_player_name TEXT",
                )
                _safe_add(
                    "requested_vehicle_code",
                    "ALTER TABLE vehicle_order ADD COLUMN requested_vehicle_code INTEGER",
                )
                _safe_add(
                    "requested_vehicle_name",
                    "ALTER TABLE vehicle_order ADD COLUMN requested_vehicle_name TEXT",
                )
            except Exception as e:
                if logger:
                    logger.warn(
                        f"Migração de colunas do vehicle_order falhou (requested_*). Erro: {e}"
                    )
                raise
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_vehicle_order_status_next_attempt
                ON vehicle_order(status, next_attempt_at)
                """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela vehicle_order: {e}")
        raise


def _init_vehicle_catalog(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vehicle_catalog (
                    code INTEGER PRIMARY KEY,
                    setup TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    template_vehicle_entity_id INTEGER NOT NULL,
                    price INTEGER NOT NULL DEFAULT 0,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )

            # Migração: adicionar coluna setup se banco antigo não tiver
            try:
                cursor.execute("PRAGMA table_info('vehicle_catalog')")
                existing_cols = {str(r[1]) for r in (cursor.fetchall() or [])}

                if "setup" not in existing_cols:
                    try:
                        cursor.execute(
                            "ALTER TABLE vehicle_catalog ADD COLUMN setup TEXT NOT NULL DEFAULT ''"
                        )
                    except sqlite3.OperationalError as oe:
                        msg = str(oe or "")
                        if "duplicate column name" not in msg.lower():
                            raise

                # Migration: optional image url (thumbnail) for frontend.
                if "image_url" not in existing_cols:
                    try:
                        cursor.execute(
                            "ALTER TABLE vehicle_catalog ADD COLUMN image_url TEXT"
                        )
                    except sqlite3.OperationalError as oe:
                        msg = str(oe or "")
                        if "duplicate column name" not in msg.lower():
                            raise

                # Backfill: se setup estiver vazio, copiar display_name
                cursor.execute(
                    "UPDATE vehicle_catalog SET setup = display_name WHERE (setup IS NULL OR TRIM(setup) = '')"
                )
            except Exception as e:
                if logger:
                    logger.warn(f"Migração de colunas do vehicle_catalog falhou (setup). Erro: {e}")
                raise

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_vehicle_catalog_enabled
                ON vehicle_catalog(enabled, code)
                """
            )
            conn.commit()
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela vehicle_catalog: {e}")
        raise


def _init_log_tables(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabelas de logs com schemas completos"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()

            # log_files_processed
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS log_files_processed (
                    file_name TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    last_position INTEGER DEFAULT 0,
                    last_modified DATETIME,
                    lines_processed INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # player_logins
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS player_logins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    player_id INTEGER NOT NULL,
                    ip_address TEXT,
                    action TEXT NOT NULL,
                    coordinates_x REAL,
                    coordinates_y REAL,
                    coordinates_z REAL,
                    timestamp DATETIME NOT NULL,
                    server_date DATE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # log_cursors
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS log_cursors (
                    log_file TEXT PRIMARY KEY,
                    cursor_position INTEGER NOT NULL DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()
            if logger:
                logger.debug("Tabelas de logs verificadas/criadas com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabelas de logs: {e}")
        raise


def _init_weather_parameters(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela weather_parameters"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS weather_parameters (
                    map_id INTEGER,
                    user_profile_id INTEGER,
                    time_of_day REAL,
                    moon_rotation REAL,
                    base_air_temperature REAL,
                    water_temperature REAL,
                    should_cumulonimbus_cause_fog INTEGER,
                    fog_density REAL,
                    data BLOB,
                    sync_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()
            if logger:
                logger.debug("Tabela weather_parameters verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela weather_parameters: {e}")
        raise


def _init_players(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela players"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS players (
                    steam_id TEXT PRIMARY KEY,
                    player_name TEXT NOT NULL,
                    player_id INTEGER NOT NULL,
                    first_seen DATETIME NOT NULL,
                    last_seen DATETIME NOT NULL,
                    total_sessions INTEGER DEFAULT 0,
                    total_playtime INTEGER DEFAULT 0,
                    is_new_player BOOLEAN DEFAULT 1,
                    notification_sent BOOLEAN DEFAULT 0,
                    permissao INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    elevated_user INTEGER DEFAULT 0
                )
            """
            )
            conn.commit()
            if logger:
                logger.debug("Tabela players verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela players: {e}")
        raise


def _init_players_online(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela players_online"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS players_online (
                    steam_id TEXT PRIMARY KEY,
                    player_name TEXT NOT NULL,
                    player_id INTEGER NOT NULL,
                    last_activity DATETIME NOT NULL,
                    coordinates_x REAL NOT NULL,
                    coordinates_y REAL NOT NULL,
                    coordinates_z REAL NOT NULL,
                    activity_types TEXT,
                    total_activities INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'online',
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (steam_id) REFERENCES players (steam_id)
                )
            """
            )
            conn.commit()
            if logger:
                logger.debug("Tabela players_online verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela players_online: {e}")
        raise


def _init_player_fame_totals(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela player_fame_totals"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS player_fame_totals (
                    steam_id TEXT PRIMARY KEY,
                    player_name TEXT NOT NULL,
                    total_fame REAL NOT NULL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (steam_id) REFERENCES players (steam_id) ON DELETE CASCADE
                )
            """
            )
            conn.commit()
            if logger:
                logger.debug("Tabela player_fame_totals verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela player_fame_totals: {e}")
        raise


def _init_player_permissions(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela player_permissions"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS player_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id TEXT NOT NULL,
                    permission_type TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    granted_by TEXT,
                    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    revoked_by TEXT,
                    revoked_at DATETIME,
                    notes TEXT,
                    FOREIGN KEY (steam_id) REFERENCES players (steam_id)
                )
            """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_player_permissions_steam_id ON player_permissions(steam_id)"
            )
            conn.commit()
            if logger:
                logger.debug("Tabela player_permissions verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela player_permissions: {e}")
        raise


def _init_player_webhooks(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela player_webhooks"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS player_webhooks (
                    steam_id TEXT PRIMARY KEY,
                    webhook_url TEXT NOT NULL,
                    expires_at DATETIME,
                    warned_3d INTEGER DEFAULT 0,
                    warned_1d INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (steam_id) REFERENCES players (steam_id)
                )
            """
            )

            # Migração: adicionar colunas se não existirem
            try:
                cursor.execute("PRAGMA table_info('player_webhooks')")
                existing_cols = {str(r[1]) for r in (cursor.fetchall() or [])}
                if "expires_at" not in existing_cols:
                    cursor.execute("ALTER TABLE player_webhooks ADD COLUMN expires_at DATETIME")
                if "warned_3d" not in existing_cols:
                    cursor.execute("ALTER TABLE player_webhooks ADD COLUMN warned_3d INTEGER DEFAULT 0")
                if "warned_1d" not in existing_cols:
                    cursor.execute("ALTER TABLE player_webhooks ADD COLUMN warned_1d INTEGER DEFAULT 0")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao adicionar colunas de migracao a player_webhooks: {e}")

            conn.commit()
            if logger:
                logger.debug("Tabela player_webhooks verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela player_webhooks: {e}")
        raise


def _init_minigame_event_deliveries(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela minigame_event_deliveries"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS minigame_event_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_key TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_steam_id TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    last_attempt_at DATETIME,
                    sent_at DATETIME,
                    last_error TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(event_key, target_type, target_steam_id)
                )
            """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_minigame_deliveries_event_key ON minigame_event_deliveries(event_key)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_minigame_deliveries_target ON minigame_event_deliveries(target_type, target_steam_id)"
            )
            conn.commit()
            if logger:
                logger.debug(
                    "Tabela minigame_event_deliveries verificada/criada com sucesso"
                )
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela minigame_event_deliveries: {e}")
        raise


def _init_admin_commands_processed(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela admin_commands_processed"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_commands_processed (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_id TEXT UNIQUE NOT NULL,
                    steam_id TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    discord_sent INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()
            if logger:
                logger.debug(
                    "Tabela admin_commands_processed verificada/criada com sucesso"
                )
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela admin_commands_processed: {e}")
        raise


def _init_bunker_status(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela bunker_status"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bunker_status (
                    bunker_id TEXT PRIMARY KEY,
                    bunker_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    coordinates_x REAL,
                    coordinates_y REAL,
                    coordinates_z REAL,
                    last_activity DATETIME,
                    next_activation DATETIME,
                    duration_minutes INTEGER,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()
            if logger:
                logger.debug("Tabela bunker_status verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela bunker_status: {e}")
        raise


def _init_attribute_upgrade_prices(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela de preços de upgrades de atributos"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS attribute_upgrade_prices (
                    attribute_name TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    PRIMARY KEY (attribute_name, level)
                )
                """
            )
            
            # 1. Verificar se a tabela já possui dados cadastrados no banco SSM.db
            cursor.execute("SELECT COUNT(*) FROM attribute_upgrade_prices")
            existing_count = cursor.fetchone()[0]

            if existing_count > 0:
                if logger:
                    logger.debug(f"[Startup Sync] Tabela attribute_upgrade_prices já possui {existing_count} registros. Preservando valores customizados.")
                return

            # 2. Se a tabela estiver vazia (count == 0), tentar popular a partir de config.json se disponível
            config_prices = None
            if config and isinstance(config, dict):
                config_prices = config.get("attribute_upgrade_prices")

            if config_prices and isinstance(config_prices, dict):
                # Ler preços do config.json e popular a tabela vazia
                attr_mapping = {
                    "strength": "strength", "forca": "strength", "força": "strength", "force": "strength",
                    "constitution": "constitution", "constituiçao": "constitution", "constituição": "constitution",
                    "dexterity": "dexterity", "destreza": "dexterity",
                    "intelligence": "intelligence", "inteligencia": "intelligence", "inteligência": "intelligence"
                }

                insert_rows = []
                for attr, lvls in config_prices.items():
                    if not isinstance(attr, str):
                        continue
                    normalized_attr = attr_mapping.get(attr.lower().strip())
                    if not normalized_attr:
                        continue
                    if not isinstance(lvls, dict):
                        continue
                    for lvl_str, pr_val in lvls.items():
                        try:
                            lvl = int(lvl_str)
                            pr = int(pr_val)
                        except (ValueError, TypeError):
                            continue
                        
                        max_level = 8 if normalized_attr == "strength" else 5
                        if lvl < 1 or lvl > max_level:
                            continue
                        if pr < 0:
                            continue
                        insert_rows.append((normalized_attr, lvl, pr))

                if insert_rows:
                    cursor.executemany(
                        "INSERT INTO attribute_upgrade_prices (attribute_name, level, price) VALUES (?, ?, ?)",
                        insert_rows
                    )
                    conn.commit()
                    if logger:
                        logger.info(f"[Startup Sync] Inicializados {len(insert_rows)} preços de atributos a partir do config.json no SSM.db")
                    return

            # 3. Fallback/Seed com zeros se a tabela estiver vazia e não houver dados no config.json
            defaults = [
                # Strength
                ("strength", 1, 0), ("strength", 2, 0), ("strength", 3, 0), ("strength", 4, 0),
                ("strength", 5, 0), ("strength", 6, 0), ("strength", 7, 0), ("strength", 8, 0),
                # Constitution
                ("constitution", 1, 0), ("constitution", 2, 0), ("constitution", 3, 0),
                ("constitution", 4, 0), ("constitution", 5, 0),
                # Dexterity
                ("dexterity", 1, 0), ("dexterity", 2, 0), ("dexterity", 3, 0),
                ("dexterity", 4, 0), ("dexterity", 5, 0),
                # Intelligence
                ("intelligence", 1, 0), ("intelligence", 2, 0), ("intelligence", 3, 0),
                ("intelligence", 4, 0), ("intelligence", 5, 0)
            ]
            cursor.executemany(
                "INSERT INTO attribute_upgrade_prices (attribute_name, level, price) VALUES (?, ?, ?)",
                defaults
            )
            conn.commit()
            if logger:
                logger.debug("Tabela attribute_upgrade_prices inicializada com preços padrão (0)")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar/sincronizar tabela attribute_upgrade_prices: {e}")
        raise


def _init_player_attributes_cache(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela player_attributes_cache"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS player_attributes_cache (
                    steam_id TEXT PRIMARY KEY,
                    strength REAL,
                    constitution REAL,
                    dexterity REAL,
                    intelligence REAL,
                    prisoner_id INTEGER,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Migração: adicionar coluna prisoner_id se não existir no banco existente
            try:
                cursor.execute("PRAGMA table_info('player_attributes_cache')")
                existing_cols = {str(r[1]) for r in (cursor.fetchall() or [])}
                if "prisoner_id" not in existing_cols:
                    cursor.execute("ALTER TABLE player_attributes_cache ADD COLUMN prisoner_id INTEGER")
            except Exception as e:
                if logger:
                    logger.warn(f"Erro ao adicionar coluna prisoner_id a player_attributes_cache: {e}")

            conn.commit()
            if logger:
                logger.debug("Tabela player_attributes_cache verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela player_attributes_cache: {e}")
        raise


def _init_player_attribute_upgrades(
    ssm_db_path: str,
    config: Optional[Dict],
    path_helper: Optional[ConfigPathHelper],
    logger: Optional[StructuredLogger],
):
    """Inicializar tabela player_attribute_upgrades"""
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS player_attribute_upgrades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id TEXT NOT NULL,
                    attribute_name TEXT NOT NULL,
                    original_value REAL NOT NULL,
                    target_value REAL NOT NULL,
                    expires_at DATETIME NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Índices de performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_player_attribute_upgrades_expires ON player_attribute_upgrades(expires_at, status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_player_attribute_upgrades_steam ON player_attribute_upgrades(steam_id, attribute_name, status)"
            )
            
            conn.commit()
            if logger:
                logger.debug("Tabela player_attribute_upgrades verificada/criada com sucesso")
    except Exception as e:
        if logger:
            logger.error(f"Erro ao criar tabela player_attribute_upgrades: {e}")
        raise


def verify_database_integrity(ssm_db_path: str) -> Dict:
    """
    Verifica a integridade do banco de dados.

    Args:
        ssm_db_path: Caminho para o banco SSM.db

    Returns:
        {
            'valid': bool,
            'issues': List[str],
            'table_status': Dict[str, bool]
        }
    """
    issues = []
    table_status = {}

    # Verificar se banco existe
    if not os.path.exists(ssm_db_path):
        return {
            "valid": False,
            "issues": ["Banco de dados não encontrado"],
            "table_status": {},
        }

    # Obter status do banco
    status = check_database_status(ssm_db_path)

    # Verificar tabelas faltantes
    if status["missing_tables"]:
        issues.append(f"Tabelas faltantes: {', '.join(status['missing_tables'])}")
        for table in status["missing_tables"]:
            table_status[table] = False

    # Verificar tabelas existentes
    for table in status["tables"]:
        if table in EXPECTED_TABLES:
            # Verificar estrutura básica
            try:
                with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    cursor.fetchone()
                    table_status[table] = True
            except Exception as e:
                issues.append(f"Tabela {table} tem problemas: {str(e)}")
                table_status[table] = False

    return {"valid": len(issues) == 0, "issues": issues, "table_status": table_status}
