"""
Gerenciador de Banco de Dados para Logs do SCUM
Cria e gerencia tabelas SQLite para armazenamento de dados de login
"""

import sqlite3
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import contextlib

class DatabaseManager:
    def __init__(
        self,
        db_path: str = "data/SSM.db",
        timeout: float = 30.0,
        busy_timeout_ms: int = 30000,
        enable_wal: bool = True,
        max_retries: int = 3,
    ):
        self.db_path = db_path
        self.timeout = timeout
        self.busy_timeout_ms = busy_timeout_ms
        self.enable_wal = enable_wal
        self.max_retries = max_retries
        self.init_database()

    @contextlib.contextmanager
    def _connect(self, write_mode: bool = True) -> sqlite3.Connection:
        """Abrir conexão SQLite via DatabaseConnector central."""
        from core.database.connector import DatabaseConnector
        with DatabaseConnector.get_connection(self.db_path, timeout=self.timeout, write_mode=write_mode) as conn:
            # Pragmas adicionais específicos do database_manager se necessário
            try:
                conn.execute("PRAGMA foreign_keys = ON")
            except Exception:
                pass
            yield conn

    def _sleep_backoff(self, attempt: int) -> None:
        # 0->0.2s, 1->0.4s, 2->0.8s ...
        time.sleep(0.2 * (2**attempt))
    
    def init_database(self):
        """Inicializar banco de dados e criar tabelas"""
        try:
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with self._connect() as conn:
                # Tabela principal de logins
                conn.execute('''
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
                ''')
                
                # Tabela de controle de arquivos processados
                conn.execute('''
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
                ''')
                
                # Tabela de jogadores (controle de players)
                conn.execute('''
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
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Migração leve: adicionar colunas novas em players (registro Discord)
                try:
                    cursor = conn.execute("PRAGMA table_info(players)")
                    players_cols = {row[1] for row in cursor.fetchall()}
                    if "discord_user_id" not in players_cols:
                        conn.execute("ALTER TABLE players ADD COLUMN discord_user_id TEXT")
                    if "discord_linked_at" not in players_cols:
                        conn.execute("ALTER TABLE players ADD COLUMN discord_linked_at DATETIME")
                except Exception:
                    pass

                # Tabela de tokens temporários para vincular DiscordID <-> SteamID
                conn.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS discord_link_tokens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code TEXT NOT NULL UNIQUE,
                        discord_user_id TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        expires_at DATETIME NOT NULL,
                        consumed_at DATETIME,
                        consumed_by_steam_id TEXT
                    )
                    '''
                )
                
                # Tabela com total de fama consolidadas por jogador
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS player_fame_totals (
                        steam_id TEXT PRIMARY KEY,
                        player_name TEXT NOT NULL,
                        total_fame REAL NOT NULL,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (steam_id) REFERENCES players (steam_id) ON DELETE CASCADE
                    )
                ''')
                
                # Tabela de jogadores online (status em tempo real)
                conn.execute('''
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
                ''')
                
                # Tabela para histórico de propriedade de veículos
                conn.execute('''
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
                        log_line TEXT,
                        container_class TEXT,
                        vehicle_class TEXT,
                        vehicle_asset_id TEXT,
                        is_vehicle_functional INTEGER,
                        notification_sent BOOLEAN DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Migração leve: garantir que vehicle_ownership_history tem a coluna log_line
                try:
                    cursor = conn.execute("PRAGMA table_info(vehicle_ownership_history)")
                    cols = {row[1] for row in cursor.fetchall()}
                    if "log_line" not in cols:
                        conn.execute("ALTER TABLE vehicle_ownership_history ADD COLUMN log_line TEXT")
                except Exception:
                    pass
                
                # Tabela para propriedade atual de veículos
                conn.execute('''
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
                ''')

                # Tabela para deduplicação robusta de notificações Discord de veículos
                # Usa event_key único (hash da linha original do log) para idempotência.
                conn.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS vehicle_notification_events (
                        event_key TEXT PRIMARY KEY,
                        entity_id INTEGER,
                        ownership_type TEXT,
                        event_timestamp DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    '''
                )

                # Migração leve: garantir 1 linha por veículo (vehicle_entity_id) quando disponível.
                # Cenário: um veículo pode trocar de container (entity_id), mas vehicle_entity_id é estável.
                try:
                    # Remover duplicados existentes antes de criar índice único.
                    # Mantém a linha mais recente por vehicle_entity_id.
                    conn.execute(
                        '''
                        DELETE FROM vehicle_current_ownership
                        WHERE vehicle_entity_id IS NOT NULL
                          AND rowid NOT IN (
                            SELECT rowid FROM (
                              SELECT rowid,
                                     ROW_NUMBER() OVER (
                                       PARTITION BY vehicle_entity_id
                                       ORDER BY last_ownership_change DESC, updated_at DESC, rowid DESC
                                     ) AS rn
                              FROM vehicle_current_ownership
                              WHERE vehicle_entity_id IS NOT NULL
                            )
                            WHERE rn = 1
                          )
                        '''
                    )
                except Exception:
                    # Se window functions não estiverem disponíveis, não interromper a inicialização.
                    pass

                try:
                    conn.execute(
                        '''
                        DELETE FROM vehicle_current_ownership
                        WHERE vehicle_entity_id IS NOT NULL
                          AND rowid NOT IN (
                            SELECT MAX(rowid)
                            FROM vehicle_current_ownership
                            WHERE vehicle_entity_id IS NOT NULL
                            GROUP BY vehicle_entity_id
                          )
                        '''
                    )
                except Exception:
                    pass

                try:
                    # Índice único parcial: permite múltiplos NULLs e garante unicidade para veículos reais.
                    conn.execute(
                        '''
                        CREATE UNIQUE INDEX IF NOT EXISTS ux_vehicle_current_ownership_vehicle_entity_id
                        ON vehicle_current_ownership(vehicle_entity_id)
                        WHERE vehicle_entity_id IS NOT NULL
                        '''
                    )
                except Exception:
                    pass

                try:
                    conn.execute(
                        '''
                        CREATE UNIQUE INDEX IF NOT EXISTS ux_vehicle_current_ownership_vehicle_entity_id_full
                        ON vehicle_current_ownership(vehicle_entity_id)
                        '''
                    )
                except Exception:
                    pass

                # Tabela para status dos bunkers
                conn.execute('''
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
                ''')
                
                # Tabela para eventos de destruição de veículos
                conn.execute('''
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
                ''')
                
                # Tabela para parâmetros climáticos
                conn.execute('''
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
                ''')
                
                # Tabela para rankings de pescadores (uma linha por jogador)
                # Estrutura idêntica à tabela fishing_stats do SCUM.db
                conn.execute('''
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
                ''')
                
                # Migrar tabela fishing_rankings se necessário (remover ranking_data e adicionar colunas novas)
                self._migrate_fishing_rankings_table(conn)
                
                # Tabela para permissões de jogadores
                conn.execute('''
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
                ''')
                
                # Tabela para eventos de kill/morte
                conn.execute('''
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
                ''')
                
                # Tabela para minigame_events
                conn.execute('''
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
                ''')
                
                # Tabela para rastrear minas e armadilhas
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS deployed_mines (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        steam_id TEXT NOT NULL,
                        player_name TEXT,
                        trap_name TEXT,
                        location_x REAL NOT NULL,
                        location_y REAL NOT NULL,
                        location_z REAL NOT NULL,
                        is_illegal BOOLEAN DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'active', -- 'active', 'detonated', 'expired'
                        teleport_executed BOOLEAN DEFAULT 0,
                        fine_executed BOOLEAN DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabela para rankings agregados
                conn.execute('''
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
                        
                        UNIQUE(steam_id)
                    )
                ''')
                
                # Verificar e adicionar coluna permissão se não existir (para bancos existentes)
                self._add_permission_column_if_needed(conn)
                
                # Adicionar colunas de lockpick por tipo se não existirem (para bancos existentes)
                self._add_lockpick_type_columns_if_needed(conn)
                
                # Criar índices para performance
                self._create_indexes(conn)
                
                conn.commit()
                print("OK: Banco de dados inicializado")
                
        except Exception as e:
            print(f"ERRO: Erro ao inicializar banco de dados: {e}")
            raise
    
    def register_vehicle_notification_event(
        self,
        event_key: str,
        entity_id: Optional[int] = None,
        ownership_type: Optional[str] = None,
        event_timestamp: Optional[datetime] = None,
    ) -> bool:
        """Registrar evento de notificação de veículo de forma idempotente.

        Retorna True se o evento é novo (logo, pode enviar para Discord). Retorna False se já existia.
        """
        for attempt in range(self.max_retries):
            try:
                with self._connect() as conn:
                    cur = conn.execute(
                        '''
                        INSERT OR IGNORE INTO vehicle_notification_events
                            (event_key, entity_id, ownership_type, event_timestamp)
                        VALUES (?, ?, ?, ?)
                        ''',
                        (
                            str(event_key),
                            int(entity_id) if entity_id is not None else None,
                            str(ownership_type) if ownership_type is not None else None,
                            event_timestamp.isoformat() if isinstance(event_timestamp, datetime) else None,
                        ),
                    )
                    conn.commit()
                    return bool(getattr(cur, "rowcount", 0) == 1)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                print(f"ERRO Erro ao registrar evento de notificação de veículo: {e}")
                return False
            except Exception as e:
                print(f"ERRO Erro ao registrar evento de notificação de veículo: {e}")
                return False
    
    def _add_permission_column_if_needed(self, conn):
        """Adicionar coluna permissão se não existir (para bancos existentes)"""
        try:
            # Verificar se a coluna permissão já existe
            cursor = conn.execute("PRAGMA table_info(players)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'permissao' not in columns:
                # Adicionar coluna permissão com valor padrão 0
                conn.execute('ALTER TABLE players ADD COLUMN permissao INTEGER DEFAULT 0')
                print("OK: Coluna permissão adicionada à tabela players")
        except Exception as e:
            print(f"AVISO: Erro ao verificar/adicionar coluna permissão: {e}")
    
    def _add_lockpick_type_columns_if_needed(self, conn):
        """Adicionar colunas de lockpick por tipo se não existirem (para bancos existentes)"""
        try:
            # Verificar quais colunas já existem na tabela rankings
            cursor = conn.execute("PRAGMA table_info(rankings)")
            existing_columns = {column[1] for column in cursor.fetchall()}
            
            # Tipos de fechadura a adicionar
            lock_types = ['basic', 'medium', 'advanced', 'veryeasy', 'diallock', 'other']
            
            for lock_type in lock_types:
                columns_to_add = [
                    f'lockpick_{lock_type}_success',
                    f'lockpick_{lock_type}_fails',
                    f'lockpick_{lock_type}_total',
                    f'lockpick_{lock_type}_rate'
                ]
                
                for col_name in columns_to_add:
                    if col_name not in existing_columns:
                        if col_name.endswith('_rate'):
                            # Taxa é REAL
                            conn.execute(f'ALTER TABLE rankings ADD COLUMN {col_name} REAL DEFAULT 0')
                        else:
                            # Success, fails e total são INTEGER
                            conn.execute(f'ALTER TABLE rankings ADD COLUMN {col_name} INTEGER DEFAULT 0')
                        print(f"OK: Coluna {col_name} adicionada à tabela rankings")
                        
        except Exception as e:
            print(f"AVISO: Erro ao verificar/adicionar colunas de lockpick por tipo: {e}")
    
    def _migrate_fishing_rankings_table(self, conn):
        """Migrar tabela fishing_rankings para nova estrutura (uma linha por jogador)"""
        try:
            # Verificar se a tabela existe
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fishing_rankings'")
            if not cursor.fetchone():
                # Tabela não existe, será criada pelo CREATE TABLE acima
                return
            
            # Verificar colunas existentes
            cursor.execute("PRAGMA table_info(fishing_rankings)")
            existing_columns = {column[1]: column for column in cursor.fetchall()}
            
            # Verificar se já está na nova estrutura (tem steam_id como PRIMARY KEY)
            has_steam_id = 'steam_id' in existing_columns
            if has_steam_id:
                # Verificar se é PRIMARY KEY consultando sqlite_master
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='fishing_rankings'")
                table_sql = cursor.fetchone()
                if table_sql and table_sql[0]:
                    sql_text = table_sql[0].upper()
                    # Verificar se steam_id é PRIMARY KEY
                    has_new_structure = 'STEAM_ID' in sql_text and 'PRIMARY KEY' in sql_text
                    # Verificar se steam_id vem antes de PRIMARY KEY (indicando que é a chave primária)
                    if has_new_structure:
                        pk_pos = sql_text.find('PRIMARY KEY')
                        steam_id_pos = sql_text.find('STEAM_ID')
                        has_new_structure = steam_id_pos < pk_pos or 'STEAM_ID TEXT PRIMARY KEY' in sql_text
                else:
                    has_new_structure = False
            else:
                has_new_structure = False
            
            if has_new_structure:
                # Já está na nova estrutura, apenas adicionar colunas faltantes se necessário
                # Todos os campos da tabela fishing_stats do SCUM.db
                required_columns = {
                    'steam_id': 'TEXT PRIMARY KEY',
                    'player_name': 'TEXT NOT NULL',
                    'fish_caught': 'INTEGER DEFAULT 0',
                    'fish_kept': 'INTEGER DEFAULT 0',
                    'fish_released': 'INTEGER DEFAULT 0',
                    'lines_broken': 'INTEGER DEFAULT 0',
                    'heaviest_fish_caught': 'REAL DEFAULT 0',
                    'longest_fish_caught': 'REAL DEFAULT 0',
                    'bass_caught': 'INTEGER DEFAULT 0',
                    'catfish_caught': 'INTEGER DEFAULT 0',
                    'pike_caught': 'INTEGER DEFAULT 0',
                    'carp_caught': 'INTEGER DEFAULT 0',
                    'amur_caught': 'INTEGER DEFAULT 0',
                    'bleak_caught': 'INTEGER DEFAULT 0',
                    'chub_caught': 'INTEGER DEFAULT 0',
                    'ruffe_caught': 'INTEGER DEFAULT 0',
                    'prussian_carp_caught': 'INTEGER DEFAULT 0',
                    'crucian_carp_caught': 'INTEGER DEFAULT 0',
                    'sardine_caught': 'INTEGER DEFAULT 0',
                    'dentex_caught': 'INTEGER DEFAULT 0',
                    'orata_caught': 'INTEGER DEFAULT 0',
                    'tuna_caught': 'INTEGER DEFAULT 0',
                    'last_updated': 'DATETIME DEFAULT CURRENT_TIMESTAMP'
                }
                
                for col_name, col_def in required_columns.items():
                    if col_name not in existing_columns and col_name != 'steam_id':  # steam_id já existe
                        # Converter definição para ALTER TABLE
                        alter_def = col_def.replace('PRIMARY KEY', '').replace('NOT NULL', '').strip()
                        if 'DEFAULT' in col_def:
                            default_part = col_def[col_def.find('DEFAULT'):]
                            alter_def = alter_def.replace(default_part, '').strip() + ' ' + default_part
                        
                        try:
                            conn.execute(f'ALTER TABLE fishing_rankings ADD COLUMN {col_name} {alter_def}')
                            print(f"OK: Coluna {col_name} adicionada à tabela fishing_rankings")
                        except sqlite3.OperationalError as e:
                            print(f"AVISO: Erro ao adicionar coluna {col_name}: {e}")
            else:
                # Estrutura antiga (snapshot diário), precisa recriar completamente
                print("OK: Migrando tabela fishing_rankings para nova estrutura (uma linha por jogador)...")
                
                # Criar nova tabela com estrutura correta (todos os campos da fishing_stats)
                conn.execute('''
                    CREATE TABLE fishing_rankings_new (
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
                ''')
                
                # Não copiar dados da estrutura antiga (snapshot) para a nova (por jogador)
                # Os dados serão populados na próxima execução do ranking
                print("OK: Nova estrutura criada. Dados serão populados na próxima execução do ranking.")
                
                # Dropar tabela antiga
                conn.execute('DROP TABLE fishing_rankings')
                
                # Renomear tabela nova
                conn.execute('ALTER TABLE fishing_rankings_new RENAME TO fishing_rankings')
                
                print("OK: Tabela fishing_rankings migrada com sucesso")
                        
        except Exception as e:
            print(f"AVISO: Erro ao migrar tabela fishing_rankings: {e}")
    
    def _create_indexes(self, conn):
        """Criar índices para otimizar consultas"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_steam_id ON player_logins(steam_id)",
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON player_logins(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_action ON player_logins(action)",
            "CREATE INDEX IF NOT EXISTS idx_server_date ON player_logins(server_date)",
            "CREATE INDEX IF NOT EXISTS idx_player_name ON player_logins(player_name)",
            "CREATE INDEX IF NOT EXISTS idx_players_steam_id ON players(steam_id)",
            "CREATE INDEX IF NOT EXISTS idx_players_last_seen ON players(last_seen)",
            "CREATE INDEX IF NOT EXISTS idx_players_is_new ON players(is_new_player)",
            # Índices para tabelas de veículos
            "CREATE INDEX IF NOT EXISTS idx_vehicle_ownership_entity_id ON vehicle_ownership_history(entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_vehicle_ownership_vehicle_entity_id ON vehicle_ownership_history(vehicle_entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_vehicle_ownership_steam_id ON vehicle_ownership_history(steam_id)",
            "CREATE INDEX IF NOT EXISTS idx_vehicle_ownership_timestamp ON vehicle_ownership_history(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_vehicle_ownership_type ON vehicle_ownership_history(ownership_type)",
            "CREATE INDEX IF NOT EXISTS idx_vehicle_current_steam_id ON vehicle_current_ownership(steam_id)",
            "CREATE INDEX IF NOT EXISTS idx_vehicle_current_vehicle_entity_id ON vehicle_current_ownership(vehicle_entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_vehicle_current_vehicle_class ON vehicle_current_ownership(vehicle_class)",
            "CREATE INDEX IF NOT EXISTS idx_vehicle_current_status ON vehicle_current_ownership(status)",
            # Índices para bunkers
            "CREATE INDEX IF NOT EXISTS idx_bunker_status ON bunker_status(bunker_id)",
            "CREATE INDEX IF NOT EXISTS idx_bunker_status_status ON bunker_status(status)",
            "CREATE INDEX IF NOT EXISTS idx_bunker_last_activity ON bunker_status(last_activity)",
            # Índices para eventos de destruição de veículos
            "CREATE INDEX IF NOT EXISTS idx_vehicle_destruction_vehicle_id ON vehicle_destruction_events(vehicle_id)",
            "CREATE INDEX IF NOT EXISTS idx_vehicle_destruction_event_type ON vehicle_destruction_events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_vehicle_destruction_timestamp ON vehicle_destruction_events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_vehicle_destruction_owner_steam_id ON vehicle_destruction_events(owner_steam_id)",
            # Índices para parâmetros climáticos
            "CREATE INDEX IF NOT EXISTS idx_weather_parameters_map_id ON weather_parameters(map_id)",
            "CREATE INDEX IF NOT EXISTS idx_weather_parameters_sync_timestamp ON weather_parameters(sync_timestamp)",
            # Índices para rankings de pescadores
            "CREATE INDEX IF NOT EXISTS idx_fishing_rankings_steam_id ON fishing_rankings(steam_id)",
            "CREATE INDEX IF NOT EXISTS idx_fishing_rankings_fish_caught ON fishing_rankings(fish_caught DESC)",
            "CREATE INDEX IF NOT EXISTS idx_fishing_rankings_last_updated ON fishing_rankings(last_updated DESC)",
            # Índices para permissões de jogadores
            "CREATE INDEX IF NOT EXISTS idx_player_permissions_steam_id ON player_permissions(steam_id)",
            "CREATE INDEX IF NOT EXISTS idx_player_permissions_type ON player_permissions(permission_type)",
            "CREATE INDEX IF NOT EXISTS idx_player_permissions_active ON player_permissions(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_player_permissions_granted_at ON player_permissions(granted_at)",
            # Índices para eventos de kill
            "CREATE INDEX IF NOT EXISTS idx_kill_events_timestamp ON kill_events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_kill_events_event_type ON kill_events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_kill_events_victim_steam_id ON kill_events(victim_steam_id)",
            "CREATE INDEX IF NOT EXISTS idx_kill_events_victim_name ON kill_events(victim_name)",
            "CREATE INDEX IF NOT EXISTS idx_kill_events_killer_steam_id ON kill_events(killer_steam_id)",
            "CREATE INDEX IF NOT EXISTS idx_kill_events_killer_is_npc ON kill_events(killer_is_npc)",
            "CREATE INDEX IF NOT EXISTS idx_kill_events_weapon ON kill_events(weapon)",
            "CREATE INDEX IF NOT EXISTS idx_kill_events_weapon_type ON kill_events(weapon_type)",
            # Índices para eventos de minigame
            "CREATE INDEX IF NOT EXISTS idx_minigame_timestamp ON minigame_events(timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_minigame_steam_id ON minigame_events(steam_id) WHERE steam_id IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_minigame_type ON minigame_events(minigame_type) WHERE minigame_type IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_minigame_log_file ON minigame_events(log_file)",
            # Índices para rankings
            "CREATE INDEX IF NOT EXISTS idx_rankings_steam_id ON rankings(steam_id)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_kills ON rankings(kills DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_deaths ON rankings(deaths DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_kdr ON rankings(kdr DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_longest_shot ON rankings(longest_shot_distance DESC)",
            # Índices para lockpick por tipo
            "CREATE INDEX IF NOT EXISTS idx_rankings_lockpick_basic_rate ON rankings(lockpick_basic_rate DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_lockpick_medium_rate ON rankings(lockpick_medium_rate DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_lockpick_advanced_rate ON rankings(lockpick_advanced_rate DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_lockpick_veryeasy_rate ON rankings(lockpick_veryeasy_rate DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_lockpick_diallock_rate ON rankings(lockpick_diallock_rate DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_suicides ON rankings(suicides DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_highest_defecation ON rankings(highest_defecation DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_vehicles_destroyed ON rankings(vehicles_destroyed DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_animals_killed ON rankings(animals_killed DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_players_knocked_out ON rankings(players_knocked_out DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_headshots ON rankings(headshots DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_minutes_survived ON rankings(minutes_survived DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_overdoses ON rankings(overdoses DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_highest_weight ON rankings(highest_weight_carried DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rankings_last_updated ON rankings(last_updated DESC)"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except Exception as e:
                print(f"AVISO: Erro ao criar índice: {e}")
    
    def insert_login_session(self, session_data: Dict[str, Any]) -> bool:
        """Inserir sessão de login/logout no banco"""
        try:
            with self._connect() as conn:
                conn.execute('''
                    INSERT INTO player_logins 
                    (steam_id, player_name, player_id, ip_address, action, 
                     coordinates_x, coordinates_y, coordinates_z, timestamp, server_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_data['steam_id'],
                    session_data['player_name'],
                    session_data['player_id'],
                    session_data.get('ip_address'),
                    session_data['action'],
                    session_data.get('coordinates_x'),
                    session_data.get('coordinates_y'),
                    session_data.get('coordinates_z'),
                    session_data['timestamp'],
                    session_data['timestamp'].date() if isinstance(session_data['timestamp'], datetime) else session_data['timestamp']
                ))
                conn.commit()
                return True
                
        except Exception as e:
            print(f"ERRO: Erro ao inserir sessão: {e}")
            return False
    
    def insert_batch_sessions(self, sessions_data: List[Dict[str, Any]]) -> int:
        """Inserir múltiplas sessões em lote para performance"""
        if not sessions_data:
            return 0
            
        inserted_count = 0
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                for session_data in sessions_data:
                    try:
                        cursor.execute('''
                            INSERT INTO player_logins 
                            (steam_id, player_name, player_id, ip_address, action, 
                             coordinates_x, coordinates_y, coordinates_z, timestamp, server_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            session_data['steam_id'],
                            session_data['player_name'],
                            session_data['player_id'],
                            session_data.get('ip_address'),
                            session_data['action'],
                            session_data.get('coordinates_x'),
                            session_data.get('coordinates_y'),
                            session_data.get('coordinates_z'),
                            session_data['timestamp'],
                            session_data['timestamp'].date() if isinstance(session_data['timestamp'], datetime) else session_data['timestamp']
                        ))
                        inserted_count += 1
                    except sqlite3.IntegrityError as e:
                        # Duplicado ou constraint violation - ignorar silenciosamente
                        print(f"AVISO Sessão duplicada ou constraint violation: {session_data.get('steam_id')} - {session_data.get('action')} - {e}")
                        continue
                    except Exception as e:
                        print(f"ERRO Erro ao inserir sessão individual: {e}")
                        print(f"   Dados: steam_id={session_data.get('steam_id')}, action={session_data.get('action')}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                conn.commit()
                # DEBUG removido para reduzir verbosidade do console
                # if inserted_count > 0:
                #     print(f"DEBUG: {inserted_count} de {len(sessions_data)} sessões inseridas com sucesso")
                return inserted_count
                
        except Exception as e:
            print(f"ERRO Erro ao inserir sessões em lote: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def get_file_processing_status(self, file_name: str) -> Optional[Dict[str, Any]]:
        """Obter status de processamento de arquivo"""
        for attempt in range(self.max_retries):
            try:
                with self._connect(write_mode=False) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT file_name, file_path, last_position, last_modified, 
                               lines_processed, status, created_at, updated_at
                        FROM log_files_processed 
                        WHERE file_name = ?
                    ''', (file_name,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'file_name': row[0],
                            'file_path': row[1],
                            'last_position': row[2],
                            'last_modified': row[3],
                            'lines_processed': row[4],
                            'status': row[5],
                            'created_at': row[6],
                            'updated_at': row[7]
                        }
                    return None
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                print(f"ERRO Erro ao obter status do arquivo: {e}")
                return None
            except Exception as e:
                print(f"ERRO Erro ao obter status do arquivo: {e}")
                return None
    
    def update_file_processing_status(self, file_name: str, file_path: str, 
                                    last_position: int, lines_processed: int, 
                                    status: str = 'active') -> bool:
        """Atualizar status de processamento de arquivo"""
        for attempt in range(self.max_retries):
            try:
                with self._connect() as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO log_files_processed 
                        (file_name, file_path, last_position, last_modified, 
                         lines_processed, status, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        file_name, file_path, last_position, 
                        datetime.now().isoformat(), lines_processed, status,
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                    return True
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                print(f"ERRO Erro ao atualizar status do arquivo: {e}")
                return False
            except Exception as e:
                print(f"ERRO Erro ao atualizar status do arquivo: {e}")
                return False
    
    def get_recent_logins(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obter logins recentes para verificação"""
        try:
            with self._connect(write_mode=False) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT steam_id, player_name, player_id, ip_address, action,
                           coordinates_x, coordinates_y, coordinates_z, timestamp, server_date
                    FROM player_logins 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"ERRO Erro ao obter logins recentes: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do banco de dados"""
        try:
            with self._connect(write_mode=False) as conn:
                cursor = conn.cursor()
                
                # Total de registros
                cursor.execute("SELECT COUNT(*) FROM player_logins")
                total_logins = cursor.fetchone()[0]
                
                # Logins por ação
                cursor.execute("SELECT action, COUNT(*) FROM player_logins GROUP BY action")
                logins_by_action = dict(cursor.fetchall())
                
                # Arquivos processados
                cursor.execute("SELECT COUNT(*) FROM log_files_processed")
                files_processed = cursor.fetchone()[0]
                
                # Último login
                cursor.execute("SELECT MAX(timestamp) FROM player_logins")
                last_login = cursor.fetchone()[0]
                
                return {
                    'total_logins': total_logins,
                    'logins_by_action': logins_by_action,
                    'files_processed': files_processed,
                    'last_login': last_login,
                    'database_path': self.db_path
                }
                
        except Exception as e:
            print(f"ERRO Erro ao obter estatísticas: {e}")
            return {}
    
    def get_player_by_steam_id(self, steam_id: str) -> Optional[Dict[str, Any]]:
        """Obter jogador por Steam ID"""
        try:
            with self._connect(write_mode=False) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT steam_id, player_name, player_id, first_seen, last_seen,
                           total_sessions, total_playtime, is_new_player, notification_sent, created_at
                    FROM players 
                    WHERE steam_id = ?
                ''', (steam_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            print(f"ERRO Erro ao obter jogador: {e}")
            return None
    
    def upsert_player_fame_total(self, steam_id: str, player_name: str, total_fame: float) -> bool:
        """
        Atualizar total de fama de um jogador.
        Somente insere/atualiza se o jogador existir na tabela players.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                # Garantir que o jogador existe antes de atualizar o total de fama
                cursor.execute('SELECT 1 FROM players WHERE steam_id = ?', (steam_id,))
                if not cursor.fetchone():
                    return False
                
                cursor.execute('''
                    INSERT INTO player_fame_totals (steam_id, player_name, total_fame, last_updated)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(steam_id) DO UPDATE SET
                        player_name = excluded.player_name,
                        total_fame = excluded.total_fame,
                        last_updated = CURRENT_TIMESTAMP
                ''', (steam_id, player_name, total_fame))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"ERRO Erro ao atualizar total de fama: {e}")
            return False
    
    def create_new_player(self, steam_id: str, player_name: str, player_id: int, timestamp: datetime) -> bool:
        """Criar novo jogador"""
        try:
            with self._connect() as conn:
                conn.execute('''
                    INSERT INTO players 
                    (steam_id, player_name, player_id, first_seen, last_seen, 
                     total_sessions, total_playtime, is_new_player, permissao)
                    VALUES (?, ?, ?, ?, ?, 1, 0, 1, 0)
                ''', (steam_id, player_name, player_id, timestamp, timestamp))
                conn.commit()
                return True
                
        except Exception as e:
            print(f"ERRO Erro ao criar novo jogador: {e}")
            return False
    
    def update_player_activity(self, steam_id: str, player_name: str, player_id: int, 
                              timestamp: datetime, session_duration: int = 0) -> bool:
        """Atualizar atividade do jogador"""
        try:
            with self._connect() as conn:
                # Verificar se nome mudou
                existing = self.get_player_by_steam_id(steam_id)
                name_changed = existing and existing['player_name'] != player_name
                
                if name_changed:
                    print(f"MUDANCA Nome mudou: {existing['player_name']} → {player_name}")
                
                # Atualizar jogador
                conn.execute('''
                    UPDATE players 
                    SET player_name = ?, player_id = ?, last_seen = ?,
                        total_sessions = total_sessions + 1,
                        total_playtime = total_playtime + ?,
                        is_new_player = 0
                    WHERE steam_id = ?
                ''', (player_name, player_id, timestamp, session_duration, steam_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"ERRO Erro ao atualizar jogador: {e}")
            return False
    
    def get_players_stats(self) -> Dict[str, Any]:
        """Obter estatísticas dos jogadores"""
        try:
            with self._connect(write_mode=False) as conn:
                cursor = conn.cursor()
                
                # Total de jogadores
                cursor.execute("SELECT COUNT(*) FROM players")
                total_players = cursor.fetchone()[0]
                
                # Novos jogadores
                cursor.execute("SELECT COUNT(*) FROM players WHERE is_new_player = 1")
                new_players = cursor.fetchone()[0]
                
                # Jogadores ativos (últimos 7 dias)
                cursor.execute('''
                    SELECT COUNT(*) FROM players 
                    WHERE last_seen > datetime('now', '-7 days')
                ''')
                active_players = cursor.fetchone()[0]
                
                # Top jogadores por tempo de jogo
                cursor.execute('''
                    SELECT player_name, total_playtime, total_sessions 
                    FROM players 
                    ORDER BY total_playtime DESC 
                    LIMIT 10
                ''')
                top_players = cursor.fetchall()
                
                return {
                    'total_players': total_players,
                    'new_players': new_players,
                    'active_players': active_players,
                    'top_players': [
                        {
                            'player_name': row[0],
                            'total_playtime': row[1],
                            'total_sessions': row[2]
                        }
                        for row in top_players
                    ]
                }
                
        except Exception as e:
            print(f"ERRO Erro ao obter estatísticas dos jogadores: {e}")
            return {}
    
    def mark_notification_sent(self, steam_id: str) -> bool:
        """Marcar notificação como enviada para um jogador"""
        try:
            with self._connect() as conn:
                conn.execute('''
                    UPDATE players 
                    SET notification_sent = 1 
                    WHERE steam_id = ?
                ''', (steam_id,))
                conn.commit()
                return True
                
        except Exception as e:
            print(f"ERRO: Erro ao marcar notificação como enviada: {e}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Limpar dados antigos (opcional)"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                # Contar registros que serão removidos
                cursor.execute('''
                    SELECT COUNT(*) FROM player_logins 
                    WHERE server_date < date('now', '-{} days')
                '''.format(days_to_keep))
                
                count_to_delete = cursor.fetchone()[0]
                
                # Remover registros antigos
                cursor.execute('''
                    DELETE FROM player_logins 
                    WHERE server_date < date('now', '-{} days')
                '''.format(days_to_keep))
                
                conn.commit()
                return count_to_delete
                
        except Exception as e:
            print(f"ERRO Erro ao limpar dados antigos: {e}")
            return 0
    
    def update_online_players(self, online_players: Dict[str, Dict[str, Any]]) -> int:
        """Atualizar status de jogadores online"""
        for attempt in range(self.max_retries):
            try:
                with self._connect() as conn:
                    conn.row_factory = sqlite3.Row
                    
                    updated_count = 0
                    for steam_id, player_data in online_players.items():
                        try:
                            last_activity_iso = player_data['last_activity'].isoformat()

                            conn.execute('''
                                INSERT INTO players
                                (steam_id, player_name, player_id, first_seen, last_seen,
                                 total_sessions, total_playtime, is_new_player, notification_sent, permissao)
                                VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 0)
                                ON CONFLICT(steam_id) DO UPDATE SET
                                    player_name = excluded.player_name,
                                    player_id = excluded.player_id,
                                    last_seen = excluded.last_seen
                            ''', (
                                steam_id,
                                player_data['player_name'],
                                player_data['player_id'],
                                last_activity_iso,
                                last_activity_iso,
                            ))

                            # Converter activity_types para string JSON
                            activity_types_json = json.dumps(player_data.get('activity_types', []))
                            
                            conn.execute('''
                                INSERT INTO players_online 
                                (steam_id, player_name, player_id, last_activity, 
                                 coordinates_x, coordinates_y, coordinates_z, 
                                 activity_types, total_activities, status, last_updated)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'online', CURRENT_TIMESTAMP)
                                ON CONFLICT(steam_id) DO UPDATE SET
                                    player_name = excluded.player_name,
                                    player_id = excluded.player_id,
                                    last_activity = excluded.last_activity,
                                    coordinates_x = excluded.coordinates_x,
                                    coordinates_y = excluded.coordinates_y,
                                    coordinates_z = excluded.coordinates_z,
                                    activity_types = excluded.activity_types,
                                    total_activities = excluded.total_activities,
                                    status = 'online',
                                    last_updated = CURRENT_TIMESTAMP
                            ''', (
                                steam_id,
                                player_data['player_name'],
                                player_data['player_id'],
                                last_activity_iso,
                                player_data['last_coordinates']['x'],
                                player_data['last_coordinates']['y'],
                                player_data['last_coordinates']['z'],
                                activity_types_json,
                                player_data['total_activities']
                            ))
                            updated_count += 1
                        except Exception as e:
                            print(f"ERRO ao atualizar jogador online {steam_id}: {e}")
                    
                    conn.commit()
                    return updated_count
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                # manter mensagem original para aparecer igual no log
                raise
    
    def mark_players_offline(self, offline_steam_ids: List[str]) -> int:
        """Marcar jogadores como offline"""
        if not offline_steam_ids:
            return 0
        for attempt in range(self.max_retries):
            try:
                with self._connect() as conn:
                    conn.row_factory = sqlite3.Row
                    
                    placeholders = ','.join('?' * len(offline_steam_ids))
                    cursor = conn.execute(
                        f'UPDATE players_online SET status = ?, last_updated = CURRENT_TIMESTAMP WHERE steam_id IN ({placeholders})',
                        ['offline'] + offline_steam_ids
                    )
                    
                    conn.commit()
                    return cursor.rowcount
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                raise

    def mark_all_offline_except(self, active_steam_ids: List[str]) -> int:
        """Marcar como offline todos os jogadores no banco que não estão na lista de ativos"""
        if not active_steam_ids:
            return self.reset_all_players_online()
        for attempt in range(self.max_retries):
            try:
                with self._connect() as conn:
                    placeholders = ','.join('?' * len(active_steam_ids))
                    cursor = conn.execute(
                        f"UPDATE players_online SET status = 'offline', last_updated = CURRENT_TIMESTAMP WHERE status = 'online' AND steam_id NOT IN ({placeholders})",
                        active_steam_ids
                    )
                    conn.commit()
                    return cursor.rowcount
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                raise

    def reset_all_players_online(self) -> int:
        """Marcar TODOS os jogadores como offline (reset pós novo login_*.log)."""
        for attempt in range(self.max_retries):
            try:
                with self._connect() as conn:
                    cursor = conn.execute(
                        "UPDATE players_online SET status = 'offline', last_updated = CURRENT_TIMESTAMP WHERE status = 'online'"
                    )
                    conn.commit()
                    return cursor.rowcount
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                raise
    
    def get_online_players_from_db(self) -> List[Dict[str, Any]]:
        """Obter jogadores online do banco de dados"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute('''
                SELECT po.*, p.first_seen, p.last_seen, p.total_sessions, p.total_playtime
                FROM players_online po
                LEFT JOIN players p ON po.steam_id = p.steam_id
                WHERE po.status = 'online'
                ORDER BY po.last_activity DESC
            ''')
            
            players = []
            for row in cursor.fetchall():
                player_data = dict(row)
                # Converter activity_types de JSON
                try:
                    player_data['activity_types'] = json.loads(player_data.get('activity_types', '[]'))
                except:
                    player_data['activity_types'] = []
                players.append(player_data)
            
            return players
    
    # ============================================================================
    # MÉTODOS PARA VEÍCULOS
    # ============================================================================
    
    def insert_vehicle_ownership(self, vehicle_data: Dict[str, Any]) -> bool:
        """Inserir dados de propriedade de veículo no banco"""
        vehicle_entity_id = vehicle_data.get('vehicle_entity_id')
        if not vehicle_entity_id:
            print(
                f"AVISO: Ignorando veículo sem vehicle_entity_id (entity_id={vehicle_data.get('entity_id')})"
            )
            return False

        for attempt in range(self.max_retries):
            try:
                with self._connect() as conn:
                    # Inserir no histórico
                    conn.execute('''
                        INSERT INTO vehicle_ownership_history 
                        (entity_id, steam_id, player_id, player_name, ownership_type,
                         previous_owner_steam_id, previous_owner_name, location_x, location_y, location_z,
                         timestamp, log_file, log_line, container_class, vehicle_class, vehicle_asset_id, is_vehicle_functional)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        vehicle_data['entity_id'],
                        vehicle_data['steam_id'],
                        vehicle_data.get('player_id'),
                        vehicle_data['player_name'],
                        vehicle_data['ownership_type'],
                        vehicle_data.get('previous_owner_steam_id'),
                        vehicle_data.get('previous_owner_name'),
                        vehicle_data.get('location_x'),
                        vehicle_data.get('location_y'),
                        vehicle_data.get('location_z'),
                        vehicle_data['timestamp'],
                        vehicle_data.get('source_file'),
                        vehicle_data.get('log_line'),
                        vehicle_data.get('container_class'),
                        vehicle_data.get('vehicle_class'),
                        vehicle_data.get('vehicle_asset_id'),
                        vehicle_data.get('is_vehicle_functional')
                    ))

                    # Atualizar propriedade atual por vehicle_entity_id (identidade estável do veículo)
                    conn.execute(
                        '''
                        INSERT INTO vehicle_current_ownership
                        (entity_id, vehicle_entity_id, steam_id, player_id, player_name, location_x, location_y, location_z,
                         last_ownership_change, container_class, vehicle_class, vehicle_asset_id, is_vehicle_functional)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(vehicle_entity_id) DO UPDATE SET
                            entity_id = excluded.entity_id,
                            steam_id = excluded.steam_id,
                            player_id = excluded.player_id,
                            player_name = excluded.player_name,
                            location_x = excluded.location_x,
                            location_y = excluded.location_y,
                            location_z = excluded.location_z,
                            last_ownership_change = excluded.last_ownership_change,
                            container_class = excluded.container_class,
                            vehicle_class = excluded.vehicle_class,
                            vehicle_asset_id = excluded.vehicle_asset_id,
                            is_vehicle_functional = excluded.is_vehicle_functional,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE vehicle_current_ownership.last_ownership_change IS NULL
                           OR excluded.last_ownership_change >= vehicle_current_ownership.last_ownership_change
                        ''',
                        (
                            vehicle_data['entity_id'],
                            vehicle_entity_id,
                            vehicle_data['steam_id'],
                            vehicle_data.get('player_id'),
                            vehicle_data['player_name'],
                            vehicle_data.get('location_x'),
                            vehicle_data.get('location_y'),
                            vehicle_data.get('location_z'),
                            vehicle_data['timestamp'],
                            vehicle_data.get('container_class'),
                            vehicle_data.get('vehicle_class'),
                            vehicle_data.get('vehicle_asset_id'),
                            vehicle_data.get('is_vehicle_functional'),
                        ),
                    )

                    conn.commit()
                    return True
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                print(f"ERRO: Erro ao inserir dados de veículo: {e}")
                return False
            except Exception as e:
                print(f"ERRO: Erro ao inserir dados de veículo: {e}")
                return False
    
    def insert_batch_vehicle_ownership(self, vehicles_data: List[Dict[str, Any]]) -> int:
        """Inserir múltiplos dados de propriedade de veículos"""
        success_count = 0
        
        for attempt in range(self.max_retries):
            try:
                with self._connect() as conn:
                    for vehicle_data in vehicles_data:
                        try:
                            vehicle_entity_id = vehicle_data.get('vehicle_entity_id')
                            ownership_type = vehicle_data.get('ownership_type', 'claimed')
                            entity_id = vehicle_data['entity_id']

                            # vehicle_entity_id é obrigatório para veículo. Sem isso, não existe identidade estável.
                            if not vehicle_entity_id:
                                print(
                                    f"AVISO: Ignorando registro de veículo sem vehicle_entity_id (entity_id={entity_id}, owner={vehicle_data.get('player_name')})"
                                )
                                continue
                            
                            # Log específico para transferências
                            is_transfer = ownership_type == 'changed'
                            if is_transfer:
                                previous_owner = vehicle_data.get('previous_owner_name', 'Unknown')
                                new_owner = vehicle_data.get('player_name', 'Unknown')
                                print(f"TRANSFERÊNCIA Detectada: Entity ID {entity_id}, Vehicle ID {vehicle_entity_id}")
                                print(f"   De: {previous_owner} ({vehicle_data.get('previous_owner_steam_id', 'N/A')})")
                                print(f"   Para: {new_owner} ({vehicle_data.get('steam_id', 'N/A')})")
                            
                            # Verificar se já existe registro duplicado (timestamp + steam_id + log_line completa)
                            # Usar hash MD5 da linha completa para verificação mais precisa
                            timestamp_str = vehicle_data['timestamp'].isoformat() if isinstance(vehicle_data['timestamp'], datetime) else vehicle_data['timestamp']
                            steam_id = vehicle_data.get('steam_id')
                            log_line = vehicle_data.get('log_line', '')

                            # Verificar duplicata usando timestamp, steam_id e log_line completa
                            # (fallback para bancos antigos sem a coluna log_line)
                            try:
                                cursor = conn.execute('''
                                    SELECT COUNT(*) FROM vehicle_ownership_history 
                                    WHERE timestamp = ? AND steam_id = ? AND log_line = ?
                                ''', (
                                    timestamp_str,
                                    steam_id,
                                    log_line
                                ))
                            except sqlite3.OperationalError as e:
                                if "no such column" in str(e).lower() and "log_line" in str(e).lower():
                                    cursor = conn.execute('''
                                        SELECT COUNT(*) FROM vehicle_ownership_history 
                                        WHERE timestamp = ? AND steam_id = ? AND vehicle_entity_id = ? AND ownership_type = ?
                                    ''', (
                                        timestamp_str,
                                        steam_id,
                                        vehicle_entity_id,
                                        ownership_type,
                                    ))
                                else:
                                    raise
                            
                            if cursor.fetchone()[0] > 0:
                                if is_transfer:
                                    print(f"AVISO: Transferência duplicada ignorada - Vehicle ID: {vehicle_entity_id}, Timestamp: {vehicle_data['timestamp']}")
                                else:
                                    print(f"AVISO: Registro duplicado ignorado no histórico - Entity ID: {entity_id}, Timestamp: {vehicle_data['timestamp']}, Type: {ownership_type}")
                                continue
                            
                            # Verificar proprietário anterior em vehicle_current_ownership para transferências
                            previous_owner_in_db = None
                            if is_transfer and vehicle_entity_id:
                                cursor = conn.execute('''
                                    SELECT steam_id, player_name FROM vehicle_current_ownership 
                                    WHERE vehicle_entity_id = ?
                                ''', (vehicle_entity_id,))
                                
                                row = cursor.fetchone()
                                if row:
                                    previous_owner_in_db = {'steam_id': row[0], 'player_name': row[1]}
                                    if previous_owner_in_db['steam_id'] != vehicle_data.get('previous_owner_steam_id'):
                                        print(f"AVISO: Proprietário anterior no DB ({previous_owner_in_db['player_name']}) difere do log ({previous_owner})")
                            
                            # Inserir no histórico (sempre, se não for duplicado)
                            conn.execute('''
                                INSERT INTO vehicle_ownership_history 
                                (entity_id, vehicle_entity_id, steam_id, player_id, player_name, ownership_type,
                                 previous_owner_steam_id, previous_owner_name, location_x, location_y, location_z,
                                 timestamp, log_file, log_line, container_class, vehicle_class, vehicle_asset_id, is_vehicle_functional)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                entity_id,
                                vehicle_entity_id,
                                vehicle_data['steam_id'],
                                vehicle_data.get('player_id'),
                                vehicle_data['player_name'],
                                ownership_type,
                                vehicle_data.get('previous_owner_steam_id'),
                                vehicle_data.get('previous_owner_name'),
                                vehicle_data.get('location_x'),
                                vehicle_data.get('location_y'),
                                vehicle_data.get('location_z'),
                                vehicle_data['timestamp'],
                                vehicle_data.get('source_file'),
                                vehicle_data.get('log_line'),
                                vehicle_data.get('container_class'),
                                vehicle_data.get('vehicle_class'),
                                vehicle_data.get('vehicle_asset_id'),
                                vehicle_data.get('is_vehicle_functional')
                            ))
                            
                            # Atualizar propriedade atual
                            # Importante: vehicle_entity_id é a identidade estável do veículo.
                            # entity_id (container) pode mudar, então não pode ser a chave lógica para deduplicação.
                            # Fazemos UPSERT por vehicle_entity_id quando disponível.
                            conn.execute(
                                '''
                                INSERT INTO vehicle_current_ownership
                                (entity_id, vehicle_entity_id, steam_id, player_id, player_name, location_x, location_y, location_z,
                                 last_ownership_change, container_class, vehicle_class, vehicle_asset_id, is_vehicle_functional)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(vehicle_entity_id) DO UPDATE SET
                                    entity_id = excluded.entity_id,
                                    steam_id = excluded.steam_id,
                                    player_id = excluded.player_id,
                                    player_name = excluded.player_name,
                                    location_x = excluded.location_x,
                                    location_y = excluded.location_y,
                                    location_z = excluded.location_z,
                                    last_ownership_change = excluded.last_ownership_change,
                                    container_class = excluded.container_class,
                                    vehicle_class = excluded.vehicle_class,
                                    vehicle_asset_id = excluded.vehicle_asset_id,
                                    is_vehicle_functional = excluded.is_vehicle_functional,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE vehicle_current_ownership.last_ownership_change IS NULL
                                   OR excluded.last_ownership_change >= vehicle_current_ownership.last_ownership_change
                                ''',
                                (
                                    entity_id,
                                    vehicle_entity_id,
                                    vehicle_data['steam_id'],
                                    vehicle_data.get('player_id'),
                                    vehicle_data['player_name'],
                                    vehicle_data.get('location_x'),
                                    vehicle_data.get('location_y'),
                                    vehicle_data.get('location_z'),
                                    vehicle_data['timestamp'],
                                    vehicle_data.get('container_class'),
                                    vehicle_data.get('vehicle_class'),
                                    vehicle_data.get('vehicle_asset_id'),
                                    vehicle_data.get('is_vehicle_functional'),
                                ),
                            )
                            
                            success_count += 1
                        except Exception as e:
                            print(f"ERRO: Erro ao inserir veículo individual: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                
                return success_count
            
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                print(f"ERRO: Erro ao inserir batch de veículos: {e}")
                import traceback
                traceback.print_exc()
                return success_count
            except Exception as e:
                print(f"ERRO: Erro ao inserir batch de veículos: {e}")
                import traceback
                traceback.print_exc()
                return success_count
        
        return success_count
    
    def get_vehicle_ownership_history(self, entity_id: int = None, steam_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Obter histórico de propriedade de veículos"""
        try:
            with self._connect(write_mode=False) as conn:
                conn.row_factory = sqlite3.Row
                
                where_conditions = []
                params = []
                
                if entity_id:
                    where_conditions.append("entity_id = ?")
                    params.append(entity_id)
                
                if steam_id:
                    where_conditions.append("steam_id = ?")
                    params.append(steam_id)
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                params.append(limit)
                
                query = f'''
                    SELECT * FROM vehicle_ownership_history 
                    {where_clause}
                    ORDER BY timestamp DESC 
                    LIMIT ?
                '''
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"ERRO: Erro ao obter histórico de veículos: {e}")
            return []
    
    def get_current_vehicle_ownership(self, entity_id: int = None, steam_id: str = None) -> List[Dict[str, Any]]:
        """Obter propriedade atual de veículos"""
        try:
            with self._connect(write_mode=False) as conn:
                conn.row_factory = sqlite3.Row
                
                where_conditions = []
                params = []
                
                if entity_id:
                    where_conditions.append("entity_id = ?")
                    params.append(entity_id)
                
                if steam_id:
                    where_conditions.append("steam_id = ?")
                    params.append(steam_id)
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                query = f'''
                    SELECT * FROM vehicle_current_ownership 
                    {where_clause}
                    ORDER BY last_ownership_change DESC
                '''
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"ERRO: Erro ao obter propriedade atual de veículos: {e}")
            return []
    
    def insert_kill_event(self, kill_data: Dict[str, Any]) -> bool:
        """Inserir evento de kill/morte no banco"""
        try:
            with self._connect() as conn:
                conn.execute('''
                    INSERT INTO kill_events (
                        event_type, timestamp, game_time,
                        victim_steam_id, victim_player_id, victim_name,
                        victim_location_x, victim_location_y, victim_location_z,
                        killer_steam_id, killer_user_id, killer_profile_name,
                        killer_is_npc, killer_location_x, killer_location_y, killer_location_z,
                        killer_has_immortality, weapon, weapon_type, distance,
                        is_in_game_event, log_file, raw_json, discord_sent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    kill_data.get('event_type', 'kill'),
                    kill_data.get('timestamp'),
                    kill_data.get('game_time'),
                    kill_data.get('victim_steam_id'),
                    kill_data.get('victim_player_id'),
                    kill_data.get('victim_name'),
                    kill_data.get('victim_location_x'),
                    kill_data.get('victim_location_y'),
                    kill_data.get('victim_location_z'),
                    kill_data.get('killer_steam_id'),
                    kill_data.get('killer_user_id'),
                    kill_data.get('killer_profile_name'),
                    kill_data.get('killer_is_npc', False),
                    kill_data.get('killer_location_x'),
                    kill_data.get('killer_location_y'),
                    kill_data.get('killer_location_z'),
                    kill_data.get('killer_has_immortality', False),
                    kill_data.get('weapon'),
                    kill_data.get('weapon_type'),
                    kill_data.get('distance'),
                    kill_data.get('is_in_game_event', False),
                    kill_data.get('log_file'),
                    kill_data.get('raw_json'),
                    kill_data.get('discord_sent', False)
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"ERRO: Erro ao inserir evento de kill: {e}")
            return False
    
    def insert_minigame_event(self, event_data: Dict[str, Any]) -> bool:
        """Inserir evento de minigame no banco"""
        try:
            with self._connect() as conn:
                conn.execute('''
                    INSERT INTO minigame_events (
                        log_line, timestamp, minigame_type,
                        steam_id, player_id, player_name,
                        success, elapsed_time, failed_attempts,
                        target_object, target_object_id, lock_type,
                        owner_id, owner_steam_id, owner_name, is_property_invasion,
                        location_x, location_y, location_z,
                        log_file, discord_sent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_data['log_line'],
                    event_data['timestamp'].isoformat() if isinstance(event_data['timestamp'], datetime) else event_data['timestamp'],
                    event_data.get('minigame_type'),
                    event_data.get('steam_id'),
                    event_data.get('player_id'),
                    event_data.get('player_name'),
                    event_data.get('success'),
                    event_data.get('elapsed_time'),
                    event_data.get('failed_attempts'),
                    event_data.get('target_object'),
                    event_data.get('target_object_id'),
                    event_data.get('lock_type'),
                    event_data.get('owner_id'),
                    event_data.get('owner_steam_id'),
                    event_data.get('owner_name'),
                    event_data.get('is_property_invasion', False),
                    event_data.get('location_x'),
                    event_data.get('location_y'),
                    event_data.get('location_z'),
                    event_data.get('log_file'),
                    event_data.get('discord_sent', False)
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"ERRO: Erro ao inserir evento de minigame: {e}")
            return False
    
    def insert_batch_minigame_events(self, events: List[Dict[str, Any]]) -> int:
        """Inserir múltiplos eventos de minigame"""
        success_count = 0
        
        for attempt in range(self.max_retries):
            try:
                with self._connect() as conn:
                    # Desabilitar foreign keys temporariamente para evitar falhas se steam_id não existir em players
                    conn.execute("PRAGMA foreign_keys = OFF")
                    
                    error_count = 0
                    for event_data in events:
                        try:
                            # Verificar se já existe (timestamp + steam_id + log_line completa)
                            timestamp_str = event_data['timestamp'].isoformat() if isinstance(event_data['timestamp'], datetime) else event_data['timestamp']
                            steam_id = event_data.get('steam_id')
                            log_line = event_data.get('log_line', '')
                            
                            cursor = conn.execute('''
                                SELECT COUNT(*) FROM minigame_events 
                                WHERE timestamp = ? AND steam_id = ? AND log_line = ?
                            ''', (timestamp_str, steam_id, log_line))
                            
                            if cursor.fetchone()[0] > 0:
                                continue  # Já existe, pular
                            
                            conn.execute('''
                                INSERT INTO minigame_events (
                                    log_line, timestamp, minigame_type,
                                    steam_id, player_id, player_name,
                                    success, elapsed_time, failed_attempts,
                                    target_object, target_object_id, lock_type,
                                    owner_id, owner_steam_id, owner_name, is_property_invasion,
                                    location_x, location_y, location_z,
                                    log_file, discord_sent
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                log_line,
                                timestamp_str,
                                event_data.get('minigame_type'),
                                event_data.get('steam_id'),
                                event_data.get('player_id'),
                                event_data.get('player_name'),
                                event_data.get('success'),
                                event_data.get('elapsed_time'),
                                event_data.get('failed_attempts'),
                                event_data.get('target_object'),
                                event_data.get('target_object_id'),
                                event_data.get('lock_type'),
                                event_data.get('owner_id'),
                                event_data.get('owner_steam_id'),
                                event_data.get('owner_name'),
                                event_data.get('is_property_invasion', False),
                                event_data.get('location_x'),
                                event_data.get('location_y'),
                                event_data.get('location_z'),
                                event_data.get('log_file'),
                                event_data.get('discord_sent', False)
                            ))
                            
                            success_count += 1
                            
                        except sqlite3.IntegrityError:
                            error_count += 1
                            continue
                        except Exception as e:
                            error_count += 1
                            print(f"ERRO ao inserir evento de minigame individual: {e}")
                            continue
                    
                    # Reabilitar foreign keys e commitar
                    conn.execute("PRAGMA foreign_keys = ON")
                    conn.commit()
                    
                    if error_count > 0:
                        print(f"AVISO: {error_count} eventos falharam ao inserir (de {len(events)} total)")
                    
                    return success_count
            
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                print(f"ERRO: Erro ao inserir eventos de minigame em lote: {e}")
                return success_count
            except Exception as e:
                print(f"ERRO: Erro crítico ao inserir eventos de minigame em lote: {e}")
                return success_count
        
        return success_count
    
    def mark_minigame_event_sent(self, event_id: int) -> bool:
        """Marcar evento de minigame como enviado para Discord"""
        try:
            with self._connect() as conn:
                conn.execute('''
                    UPDATE minigame_events 
                    SET discord_sent = 1 
                    WHERE id = ?
                ''', (event_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"ERRO: Erro ao marcar evento de minigame como enviado: {e}")
            return False
    
    def get_unsent_minigame_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obter eventos de minigame não enviados para Discord"""
        try:
            with self._connect(write_mode=False) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM minigame_events
                    WHERE discord_sent = 0
                      AND minigame_type = 'LockpickingMinigame_C'
                    ORDER BY timestamp ASC
                    LIMIT ?
                ''', (limit,))
                
                events = []
                for row in cursor.fetchall():
                    event_dict = dict(row)
                    # Converter timestamp se for string
                    if isinstance(event_dict.get('timestamp'), str):
                        try:
                            event_dict['timestamp'] = datetime.fromisoformat(event_dict['timestamp'].replace('Z', '+00:00'))
                        except:
                            pass
                    events.append(event_dict)
                
                return events
        except Exception as e:
            print(f"ERRO: Erro ao obter eventos não enviados: {e}")
            return []
    
    def insert_batch_kill_events(self, kill_events: List[Dict[str, Any]]) -> int:
        """Inserir múltiplos eventos de kill"""
        success_count = 0
        
        try:
            with self._connect() as conn:
                for kill_data in kill_events:
                    try:
                        # Verificar se já existe
                        # Para suicídio: timestamp + victim_steam_id + event_type
                        # Para kill: timestamp + victim_steam_id + killer_profile_name
                        event_type = kill_data.get('event_type', 'kill')
                        if event_type == 'suicide':
                            cursor = conn.execute('''
                                SELECT COUNT(*) FROM kill_events 
                                WHERE timestamp = ? AND victim_steam_id = ? AND event_type = 'suicide'
                            ''', (
                                kill_data.get('timestamp'),
                                kill_data.get('victim_steam_id')
                            ))
                        else:
                            cursor = conn.execute('''
                                SELECT COUNT(*) FROM kill_events 
                                WHERE timestamp = ? AND victim_steam_id = ? AND killer_profile_name = ?
                            ''', (
                                kill_data.get('timestamp'),
                                kill_data.get('victim_steam_id'),
                                kill_data.get('killer_profile_name')
                            ))
                        
                        if cursor.fetchone()[0] > 0:
                            continue  # Já existe, pular
                        
                        conn.execute('''
                            INSERT INTO kill_events (
                                event_type, timestamp, game_time,
                                victim_steam_id, victim_player_id, victim_name,
                                victim_location_x, victim_location_y, victim_location_z,
                                killer_steam_id, killer_user_id, killer_profile_name,
                                killer_is_npc, killer_location_x, killer_location_y, killer_location_z,
                                killer_has_immortality, weapon, weapon_type, distance,
                                is_in_game_event, log_file, raw_json, discord_sent
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            kill_data.get('event_type', 'kill'),
                            kill_data.get('timestamp'),
                            kill_data.get('game_time'),
                            kill_data.get('victim_steam_id'),
                            kill_data.get('victim_player_id'),
                            kill_data.get('victim_name'),
                            kill_data.get('victim_location_x'),
                            kill_data.get('victim_location_y'),
                            kill_data.get('victim_location_z'),
                            kill_data.get('killer_steam_id'),
                            kill_data.get('killer_user_id'),
                            kill_data.get('killer_profile_name'),
                            kill_data.get('killer_is_npc', False),
                            kill_data.get('killer_location_x'),
                            kill_data.get('killer_location_y'),
                            kill_data.get('killer_location_z'),
                            kill_data.get('killer_has_immortality', False),
                            kill_data.get('weapon'),
                            kill_data.get('weapon_type'),
                            kill_data.get('distance'),
                            kill_data.get('is_in_game_event', False),
                            kill_data.get('log_file'),
                            kill_data.get('raw_json'),
                            kill_data.get('discord_sent', False)
                        ))
                        
                        success_count += 1
                        
                    except Exception as e:
                        print(f"ERRO: Erro ao inserir kill event individual: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            print(f"ERRO: Erro ao inserir batch de kill events: {e}")
        
        return success_count
    
    def get_kill_events(self, victim_steam_id: str = None, killer_steam_id: str = None, 
                       event_type: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Obter eventos de kill"""
        try:
            with self._connect(write_mode=False) as conn:
                conn.row_factory = sqlite3.Row
                
                where_conditions = []
                params = []
                
                if victim_steam_id:
                    where_conditions.append("victim_steam_id = ?")
                    params.append(victim_steam_id)
                
                if killer_steam_id:
                    where_conditions.append("killer_steam_id = ?")
                    params.append(killer_steam_id)
                
                if event_type:
                    where_conditions.append("event_type = ?")
                    params.append(event_type)
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                params.append(limit)
                
                query = f'''
                    SELECT * FROM kill_events 
                    {where_clause}
                    ORDER BY timestamp DESC 
                    LIMIT ?
                '''
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"ERRO: Erro ao obter eventos de kill: {e}")
            return []
    
    def get_all_vehicle_entity_ids(self) -> List[int]:
        """
        Obter todos os vehicle_entity_id da tabela vehicle_current_ownership
        
        Returns:
            Lista de vehicle_entity_id (inteiros)
        """
        try:
            with self._connect(write_mode=False) as conn:
                cursor = conn.execute('''
                    SELECT DISTINCT vehicle_entity_id 
                    FROM vehicle_current_ownership 
                    WHERE vehicle_entity_id IS NOT NULL
                ''')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"ERRO: Erro ao obter vehicle_entity_ids: {e}")
            return []
    
    def update_vehicles_status_batch(self, vehicle_status_map: Dict[int, int]) -> int:
        """
        Atualizar status de múltiplos veículos em lote
        
        Args:
            vehicle_status_map: Dicionário mapeando vehicle_entity_id -> novo status
            
        Returns:
            Número de veículos atualizados
        """
        if not vehicle_status_map:
            return 0
        
        try:
            with self._connect() as conn:
                updated_count = 0
                
                # Atualizar cada veículo
                for vehicle_entity_id, new_status in vehicle_status_map.items():
                    cursor = conn.execute('''
                        UPDATE vehicle_current_ownership 
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE vehicle_entity_id = ?
                    ''', (new_status, vehicle_entity_id))
                    
                    updated_count += cursor.rowcount
                
                conn.commit()
                return updated_count
                
        except Exception as e:
            print(f"ERRO: Erro ao atualizar status de veículos em lote: {e}")
            return 0
    
    def mark_vehicle_notification_sent(self, entity_id: int, ownership_type: str = None):
        """Marcar notificação como enviada para um veículo"""
        for attempt in range(self.max_retries):
            try:
                with self._connect() as conn:
                    if ownership_type:
                        conn.execute('''
                            UPDATE vehicle_ownership_history 
                            SET notification_sent = 1 
                            WHERE entity_id = ? AND ownership_type = ?
                        ''', (entity_id, ownership_type))
                    else:
                        conn.execute('''
                            UPDATE vehicle_current_ownership 
                            SET notification_sent = 1 
                            WHERE entity_id = ?
                        ''', (entity_id,))
                    
                    conn.commit()
                    return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                print(f"ERRO: Erro ao marcar notificação de veículo: {e}")
                return
            except Exception as e:
                print(f"ERRO: Erro ao marcar notificação de veículo: {e}")
                return
    
    def get_vehicle_stats(self) -> Dict[str, Any]:
        """Obter estatísticas de veículos"""
        try:
            with self._connect(write_mode=False) as conn:
                # Total de veículos únicos
                cursor = conn.execute("SELECT COUNT(DISTINCT entity_id) FROM vehicle_current_ownership")
                total_vehicles = cursor.fetchone()[0]
                
                # Total de eventos de ownership
                cursor = conn.execute("SELECT COUNT(*) FROM vehicle_ownership_history")
                total_events = cursor.fetchone()[0]
                
                # Veículos por tipo
                cursor = conn.execute('''
                    SELECT vehicle_class, COUNT(*) as count 
                    FROM vehicle_current_ownership 
                    WHERE vehicle_class IS NOT NULL 
                    GROUP BY vehicle_class 
                    ORDER BY count DESC
                ''')
                vehicles_by_type = dict(cursor.fetchall())
                
                # Eventos por tipo
                cursor = conn.execute('''
                    SELECT ownership_type, COUNT(*) as count 
                    FROM vehicle_ownership_history 
                    GROUP BY ownership_type
                ''')
                events_by_type = dict(cursor.fetchall())
                
                return {
                    'total_vehicles': total_vehicles,
                    'total_events': total_events,
                    'vehicles_by_type': vehicles_by_type,
                    'events_by_type': events_by_type
                }
                
        except Exception as e:
            print(f"ERRO: Erro ao obter estatísticas de veículos: {e}")
            return {}
    
    def get_players_online_stats(self) -> Dict[str, Any]:
        """Obter estatísticas de jogadores online"""
        try:
            with self._connect(write_mode=False) as conn:
                conn.row_factory = sqlite3.Row
                
                # Contar jogadores online
                cursor = conn.execute('SELECT COUNT(*) as count FROM players_online WHERE status = ?', ['online'])
                online_count = cursor.fetchone()['count']
                
                # Contar jogadores offline
                cursor = conn.execute('SELECT COUNT(*) as count FROM players_online WHERE status = ?', ['offline'])
                offline_count = cursor.fetchone()['count']
                
                # Última atualização
                cursor = conn.execute('SELECT MAX(last_updated) as last_update FROM players_online')
                last_update = cursor.fetchone()['last_update']
                
                return {
                    'online_count': online_count,
                    'offline_count': offline_count,
                    'total_tracked': online_count + offline_count,
                    'last_update': last_update
                }
        except Exception as e:
            print(f"ERRO: Erro ao obter estatísticas de jogadores online: {e}")
            return {'online_count': 0, 'offline_count': 0, 'total_tracked': 0, 'last_update': None}
    
    # ============================================================================
    # MÉTODOS PARA BUNKERS
    # ============================================================================
    
    def update_bunker_status(self, bunker_data: Dict[str, Any]) -> bool:
        """Atualizar status de um bunker"""
        try:
            with self._connect() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO bunker_status 
                    (bunker_id, bunker_name, status, coordinates_x, coordinates_y, coordinates_z,
                     last_activity, next_activation, duration_minutes, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    bunker_data['bunker_id'],
                    bunker_data['bunker_name'],
                    bunker_data['status'],
                    bunker_data.get('coordinates_x'),
                    bunker_data.get('coordinates_y'),
                    bunker_data.get('coordinates_z'),
                    bunker_data.get('last_activity'),
                    bunker_data.get('next_activation'),
                    bunker_data.get('duration_minutes')
                ))
                conn.commit()
                return True
                
        except Exception as e:
            print(f"ERRO: Erro ao atualizar status do bunker: {e}")
            return False
    
    def get_bunker_status(self, bunker_id: str = None) -> List[Dict[str, Any]]:
        """Obter status dos bunkers"""
        try:
            with self._connect(write_mode=False) as conn:
                conn.row_factory = sqlite3.Row
                
                if bunker_id:
                    cursor = conn.execute('''
                        SELECT * FROM bunker_status WHERE bunker_id = ?
                    ''', (bunker_id,))
                else:
                    cursor = conn.execute('''
                        SELECT * FROM bunker_status ORDER BY bunker_id
                    ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"ERRO: Erro ao obter status dos bunkers: {e}")
            return []
    
    def get_bunker_stats(self) -> Dict[str, Any]:
        """Obter estatísticas de bunkers"""
        try:
            with self._connect(write_mode=False) as conn:
                cursor = conn.cursor()
                
                # Total de bunkers
                cursor.execute("SELECT COUNT(*) FROM bunker_status")
                total_bunkers = cursor.fetchone()[0]
                
                # Bunkers ativos
                cursor.execute("SELECT COUNT(*) FROM bunker_status WHERE status = 'active'")
                active_bunkers = cursor.fetchone()[0]
                
                # Bunkers bloqueados
                cursor.execute("SELECT COUNT(*) FROM bunker_status WHERE status = 'locked'")
                locked_bunkers = cursor.fetchone()[0]
                
                # Status por bunker
                cursor.execute('''
                    SELECT bunker_id, bunker_name, status, last_activity, next_activation
                    FROM bunker_status 
                    ORDER BY bunker_id
                ''')
                bunker_details = cursor.fetchall()
                
                return {
                    'total_bunkers': total_bunkers,
                    'active_bunkers': active_bunkers,
                    'locked_bunkers': locked_bunkers,
                    'bunker_details': [
                        {
                            'bunker_id': row[0],
                            'bunker_name': row[1],
                            'status': row[2],
                            'last_activity': row[3],
                            'next_activation': row[4]
                        }
                        for row in bunker_details
                    ]
                }
                
        except Exception as e:
            print(f"ERRO: Erro ao obter estatísticas dos bunkers: {e}")
            return {}

    def execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """Executar query SQL personalizada e retornar resultados"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            print(f"ERRO ao executar query: {e}")
            return []

    def insert_deployed_mine(self, mine_data: Dict[str, Any]) -> bool:
        """Inserir uma mina implantada no banco"""
        try:
            with self._connect() as conn:
                conn.execute('''
                    INSERT INTO deployed_mines (
                        steam_id, player_name, trap_name,
                        location_x, location_y, location_z,
                        is_illegal, status, teleport_executed, fine_executed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    mine_data.get('steam_id'),
                    mine_data.get('player_name'),
                    mine_data.get('trap_name'),
                    mine_data.get('location_x'),
                    mine_data.get('location_y'),
                    mine_data.get('location_z'),
                    mine_data.get('is_illegal', False),
                    mine_data.get('status', 'active'),
                    mine_data.get('teleport_executed', False),
                    mine_data.get('fine_executed', False)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"ERRO: Erro ao inserir mina implantada: {e}")
            return False

    def get_active_illegal_mines_by_player(self, steam_id: str) -> List[Dict[str, Any]]:
        """Buscar minas ilegais ativas de um jogador que ainda nao tiveram teleport executado"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, steam_id, player_name, trap_name, location_x, location_y, location_z, is_illegal, status, teleport_executed, created_at
                    FROM deployed_mines
                    WHERE steam_id = ? AND is_illegal = 1 AND status = 'active' AND teleport_executed = 0
                    ORDER BY id ASC
                ''', (steam_id,))
                rows = cursor.fetchall()
                return [
                    {
                        'id': row[0],
                        'steam_id': row[1],
                        'player_name': row[2],
                        'trap_name': row[3],
                        'location_x': row[4],
                        'location_y': row[5],
                        'location_z': row[6],
                        'is_illegal': bool(row[7]),
                        'status': row[8],
                        'teleport_executed': bool(row[9]),
                        'created_at': row[10]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"ERRO: Erro ao obter minas ativas do jogador: {e}")
            return []

    def mark_mine_teleported(self, mine_id: int) -> bool:
        """Marcar mina/trap como tendo o teleporte executado"""
        try:
            with self._connect() as conn:
                conn.execute('''
                    UPDATE deployed_mines
                    SET teleport_executed = 1
                    WHERE id = ?
                ''', (mine_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"ERRO: Erro ao marcar mina como teleportada: {e}")
            return False

    def mark_mine_fined(self, mine_id: int) -> bool:
        """Marcar mina/trap como tendo a multa executada"""
        try:
            with self._connect() as conn:
                conn.execute('''
                    UPDATE deployed_mines
                    SET fine_executed = 1
                    WHERE id = ?
                ''', (mine_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"ERRO: Erro ao marcar mina como multada: {e}")
            return False

    def mark_mine_detonated_by_coords(self, x: float, y: float, tolerance: float = 5.0) -> Optional[str]:
        """Marcar mina ativa próxima à coordenada como detonada e retornar o steam_id do dono"""
        try:
            with self._connect() as conn:
                # Encontrar a mina ativa mais próxima
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, steam_id, location_x, location_y
                    FROM deployed_mines
                    WHERE status = 'active'
                ''')
                rows = cursor.fetchall()
                best_mine = None
                min_dist = tolerance
                for row in rows:
                    mine_id, steam_id, mx, my = row
                    dist = ((mx - x) ** 2 + (my - y) ** 2) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        best_mine = (mine_id, steam_id)
                
                if best_mine:
                    mine_id, steam_id = best_mine
                    conn.execute('''
                        UPDATE deployed_mines
                        SET status = 'detonated'
                        WHERE id = ?
                    ''', (mine_id,))
                    conn.commit()
                    return steam_id
                return None
        except Exception as e:
            print(f"ERRO: Erro ao marcar mina como detonada: {e}")
            return None