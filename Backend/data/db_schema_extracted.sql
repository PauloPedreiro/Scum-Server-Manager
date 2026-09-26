-- Schema completo extraído do SSM.db

-- Table: admin_commands_processed
CREATE TABLE admin_commands_processed (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_id TEXT UNIQUE NOT NULL,
                    steam_id TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    discord_sent INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

-- Table: bank_accounts_snapshot
CREATE TABLE bank_accounts_snapshot (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            
                            -- Identificação do jogador
                            steam_id TEXT NOT NULL,
                            player_name TEXT,
                            
                            -- Dados da conta bancária
                            account_number TEXT,
                            money_balance REAL DEFAULT 0,
                            gold_balance REAL DEFAULT 0,
                            total_balance REAL DEFAULT 0,
                            
                            -- Metadados
                            snapshot_at TEXT NOT NULL,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            
                            -- Relacionamento com tabela players
                            FOREIGN KEY (steam_id) REFERENCES players(steam_id),
                            
                            -- Índices para performance
                            UNIQUE(steam_id, snapshot_at)
                        );

-- Table: bank_transactions
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
                    );

-- Table: bunker_status
CREATE TABLE bunker_status (
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
                    );

-- Table: chest_history
CREATE TABLE chest_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        entity_id INTEGER,
                        event_type TEXT NOT NULL,
                        container_entity_id INTEGER,
                        owner_profile_id INTEGER,
                        steam_id TEXT,
                        player_name TEXT,
                        fake_name TEXT,
                        custom_name TEXT,
                        chest_class TEXT,
                        location_x REAL,
                        location_y REAL,
                        location_z REAL,
                        rotation_x REAL,
                        rotation_y REAL,
                        rotation_z REAL,
                        vehicle_container_class TEXT,
                        vehicle_entity_id INTEGER,
                        vehicle_class TEXT,
                        vehicle_owner_steam_id TEXT,
                        vehicle_owner_name TEXT,
                        vehicle_owner_player_id INTEGER,
                        vehicle_registered_at TEXT,
                        vehicle_owner_mismatch INTEGER DEFAULT 0,
                        details_json TEXT,
                        event_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    , discord_sent INTEGER DEFAULT 0);

-- Table: chest_snapshot
CREATE TABLE chest_snapshot (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        entity_id INTEGER NOT NULL UNIQUE,
                        container_entity_id INTEGER,
                        chest_class TEXT,
                        owner_profile_id INTEGER,
                        steam_id TEXT,
                        player_name TEXT,
                        fake_name TEXT,
                        custom_name TEXT,
                        location_x REAL,
                        location_y REAL,
                        location_z REAL,
                        rotation_x REAL,
                        rotation_y REAL,
                        rotation_z REAL,
                        vehicle_container_class TEXT,
                        vehicle_entity_id INTEGER,
                        vehicle_class TEXT,
                        vehicle_owner_steam_id TEXT,
                        vehicle_owner_name TEXT,
                        vehicle_owner_player_id INTEGER,
                        vehicle_registered_at TEXT,
                        vehicle_owner_mismatch INTEGER DEFAULT 0,
                        last_seen_at TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

-- Table: elevated_user
CREATE TABLE elevated_user (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        steam_id TEXT NOT NULL,
                        synced INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        synced_at DATETIME,
                        FOREIGN KEY (steam_id) REFERENCES players (steam_id),
                        UNIQUE(steam_id)
                    );

-- Table: fishing_rankings
CREATE TABLE fishing_rankings (
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
                    );

-- Table: frontend_users
CREATE TABLE frontend_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    password_changed INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    role VARCHAR(20) DEFAULT 'admin',
                    steam_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME,
                    last_password_change DATETIME,
                    FOREIGN KEY (steam_id) REFERENCES players(steam_id) ON DELETE SET NULL
                );

-- Table: hardware_fingerprints
CREATE TABLE hardware_fingerprints (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fingerprint_hash TEXT UNIQUE NOT NULL,
                        components_json TEXT NOT NULL,
                        first_detected DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_verified DATETIME DEFAULT CURRENT_TIMESTAMP,
                        verification_count INTEGER DEFAULT 0,
                        is_valid BOOLEAN DEFAULT 1,
                        server_registered_at DATETIME,
                        notes TEXT
                    );

-- Table: items
CREATE TABLE items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    base_name TEXT,
                    category TEXT,
                    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

-- Table: kill_events
CREATE TABLE kill_events (
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
                    );

-- Table: locations
CREATE TABLE locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quadrant TEXT NOT NULL,
                    location_type TEXT NOT NULL,
                    full_name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    transaction_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

-- Table: log_files_processed
CREATE TABLE log_files_processed (
                        file_name TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        last_position INTEGER DEFAULT 0,
                        last_modified DATETIME,
                        lines_processed INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'active',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );

-- Table: minigame_events
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
                    );

-- Table: password_reset_tokens
CREATE TABLE password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) NOT NULL,
                    token VARCHAR(64) UNIQUE NOT NULL,
                    expires_at DATETIME NOT NULL,
                    used INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    FOREIGN KEY (username) REFERENCES frontend_users(username) ON DELETE CASCADE
                );

-- Table: player_fame_totals
CREATE TABLE player_fame_totals (
                        steam_id TEXT PRIMARY KEY,
                        player_name TEXT NOT NULL,
                        total_fame REAL NOT NULL,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (steam_id) REFERENCES players (steam_id) ON DELETE CASCADE
                    );

-- Table: player_gps_snapshot
CREATE TABLE player_gps_snapshot (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            prisoner_id INTEGER,
                            map_id INTEGER,
                            type INTEGER,
                            shelter_id INTEGER,
                            location_x REAL,
                            location_y REAL,
                            location_z REAL,
                            rotation_pitch REAL,
                            rotation_yaw REAL,
                            rotation_roll REAL,
                            velocity_x REAL,
                            velocity_y REAL,
                            velocity_z REAL,
                            steam_id TEXT NOT NULL,
                            player_name TEXT,
                            fake_name TEXT,
                            snapshot_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(steam_id, type),
                            FOREIGN KEY (steam_id) REFERENCES players_online(steam_id)
                        );

-- Table: player_logins
CREATE TABLE player_logins (
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
                    );

-- Table: player_permissions
CREATE TABLE player_permissions (
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
                    );

-- Table: player_skills
CREATE TABLE player_skills (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            
                            -- Identificação do jogador
                            steam_id TEXT NOT NULL,
                            player_name TEXT,
                            prisoner_id INTEGER,
                            
                            -- Dados da skill (originais do SCUM.db)
                            skill_name TEXT NOT NULL,
                            level INTEGER NOT NULL,
                            experience REAL NOT NULL,
                            xml TEXT,
                            
                            -- Metadados adicionais
                            skill_group TEXT,  -- 'FOR', 'CON', 'DES', 'INT', ou NULL
                            max_level INTEGER DEFAULT 5,
                            is_temporary_boost BOOLEAN DEFAULT 0,
                            
                            -- Metadados de sincronização
                            last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            
                            -- Constraints
                            UNIQUE(steam_id, skill_name),
                            FOREIGN KEY (steam_id) REFERENCES players(steam_id)
                        );

-- Table: players
CREATE TABLE players (
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
                    , elevated_user INTEGER DEFAULT 0);

-- Table: players_online
CREATE TABLE players_online (
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
                    );

-- Table: rankings
CREATE TABLE rankings (
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
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP, total_fame REAL DEFAULT 0.0,
                        
                        UNIQUE(steam_id)
                    );

-- Table: sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- Table: squad_member_snapshot
CREATE TABLE squad_member_snapshot (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            squad_snapshot_id INTEGER NOT NULL,
                            squad_id INTEGER NOT NULL,
                            member_id INTEGER NOT NULL,
                            user_profile_id INTEGER,
                            player_steam_id TEXT,
                            player_name TEXT,
                            rank INTEGER,
                            fame_points REAL,
                            last_login_time TEXT,
                            last_logout_time TEXT,
                            play_time INTEGER,
                            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (squad_snapshot_id) REFERENCES squad_snapshot(id) ON DELETE CASCADE
                        );

-- Table: squad_snapshot
CREATE TABLE squad_snapshot (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            squad_id INTEGER NOT NULL,
                            name TEXT,
                            message TEXT,
                            information TEXT,
                            emblem TEXT,
                            score REAL,
                            member_limit INTEGER,
                            member_count INTEGER,
                            flag_count INTEGER DEFAULT 0,
                            last_member_login_time TEXT,
                            last_member_logout_time TEXT,
                            rank_position INTEGER,
                            snapshot_at TEXT NOT NULL
                        );

-- Table: survival_stats_snapshot
CREATE TABLE survival_stats_snapshot (user_profile_id INTEGER PRIMARY KEY, highest_positive_fame_points REAL, doors_claimed INTEGER, animals_killed INTEGER, minutes_survived REAL, kills INTEGER, deaths INTEGER, locks_picked INTEGER, puppets_killed INTEGER, guns_crafted INTEGER, bullets_crafted INTEGER, arrows_crafted INTEGER, clothing_crafted INTEGER, longest_kill_distance REAL, melee_kills INTEGER, archery_kills INTEGER, players_knocked_out INTEGER, total_defecations INTEGER, total_urinations INTEGER, lights_fired INTEGER, containers_looted INTEGER, items_put_into_containers INTEGER, deaths_by_prisoners INTEGER, animals_skinned INTEGER, food_eaten REAL, distance_travelled_by_foot REAL, wounds_patched INTEGER, items_picked_up INTEGER, liquid_drank REAL, teeth_lost INTEGER, total_calories_intake INTEGER, shots_fired INTEGER, shots_hit INTEGER, headshots INTEGER, melee_weapon_swings INTEGER, melee_weapon_hits INTEGER, melee_weapons_crafted INTEGER, drone_kills INTEGER, sentry_kills INTEGER, prisoner_kills INTEGER, puppets_knocked_out INTEGER, diarrheas INTEGER, vomits INTEGER, distance_travelled_in_vehicle REAL, mushrooms_eaten INTEGER, highest_muscle_mass REAL, highest_fat REAL, heart_attacks INTEGER, overdose INTEGER, starvation INTEGER, highest_damage_taken REAL, highest_weight_carried REAL, lowest_negative_fame_points REAL, distance_travelled_swimming REAL, crows_killed INTEGER, seagulls_killed INTEGER, horses_killed INTEGER, boars_killed INTEGER, bears_killed INTEGER, goats_killed INTEGER, deers_killed INTEGER, chickens_killed INTEGER, rabbits_killed INTEGER, donkeys_killed INTEGER, times_mauled_by_bear INTEGER, longest_animal_kill_distance REAL, alcohol_drank INTEGER, foliage_cut INTEGER, distance_travel_by_boat REAL, distance_sailed REAL, times_caught_by_shark INTEGER, times_escaped_shark_bite INTEGER, wolves_killed INTEGER, last_fame_point_award_consecutive_days INTEGER, firearm_kills INTEGER, bare_handed_kills INTEGER, steam_id TEXT, player_name TEXT, snapshot_at TEXT NOT NULL);

-- Table: transaction_types
CREATE TABLE transaction_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT,
                    description TEXT,
                    is_income BOOLEAN,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

-- Table: vehicle_current_ownership
CREATE TABLE vehicle_current_ownership (
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
                    );

-- Table: vehicle_destruction_events
CREATE TABLE vehicle_destruction_events (
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
                    );

-- Table: vehicle_ownership_history
CREATE TABLE vehicle_ownership_history (
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
                    );

-- Table: weather_parameters
CREATE TABLE weather_parameters (
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
                    );

