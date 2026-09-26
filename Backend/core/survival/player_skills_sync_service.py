"""Serviço de sincronização da tabela prisoner_skill para o SSM.db"""
from core.database.connector import DatabaseConnector

import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import schedule

from utils.logger import StructuredLogger


class PlayerSkillsSyncService:
    """Sincroniza prisoner_skill do SCUM para o SSM.db"""

    # Mapeamento de skills para grupos (FOR, CON, DES, INT)
    SKILL_GROUPS = {
        "FOR": [
            "BoxingSkill",  # Briga
            "MeleeWeaponsSkill",  # Armas brancas
            "ArcherySkill",  # Arquearia
            "RiflesSkill",  # Fuzis
            "HandgunSkill",  # Pistola
        ],
        "INT": [
            "AwarenessSkill",  # Percepção
            "CamouflageSkill",  # Camuflagem
            "CookingSkill",  # Culinária
            "MedicalSkill",  # Medicina
            "SnipingSkill",  # Tiro de precisão
            "SurvivalSkill",  # Sobrevivência
            "EngineeringSkill",  # Engenharia
            "FarmingSkill",  # Agricultura
        ],
        "CON": ["RunningSkill", "EnduranceSkill"],  # Corrida  # Resiliência
        "DES": [
            "ThieverySkill",  # Roubo
            "DemolitionSkill",  # Demolição
            "StealthSkill",  # Furtividade
            "DrivingSkill",  # Condução
            "MotorcycleSkill",  # Motociclismo
            "AviationSkill",  # Avião
        ],
    }

    def __init__(
        self,
        config: Dict[str, Any],
        path_helper=None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        self.sync_config = self.config.get("player_skills_sync", {})

        self.enabled = self.sync_config.get("enabled", True)
        self.auto_start = self.sync_config.get("auto_start", True)
        self.sync_interval_hours = self.sync_config.get("sync_interval_hours", 24)

        default_scum_db = (
            path_helper.get_scum_db_path()
            if path_helper
            else "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
        )
        default_ssm_db = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"

        self.scum_db_path = self.sync_config.get("scum_db_path") or default_scum_db
        self.ssm_db_path = self.sync_config.get("ssm_db_path") or default_ssm_db

        self.scheduler = schedule.Scheduler()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False

        self.last_sync_info: Dict[str, Any] = {
            "timestamp": None,
            "status": "never_run",
            "details": {},
        }

        self.logger.info(
            "PlayerSkillsSyncService inicializado",
            {
                "enabled": self.enabled,
                "auto_start": self.auto_start,
                "sync_interval_hours": self.sync_interval_hours,
                "scum_db_path": self.scum_db_path,
                "ssm_db_path": self.ssm_db_path,
            },
        )

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def get_skill_group(self, skill_name: str) -> Optional[str]:
        """Determina o grupo de uma skill. Retorna None se não mapeada."""
        for group, skills in self.SKILL_GROUPS.items():
            if skill_name in skills:
                return group
        return None

    def calculate_max_level_and_boost(
        self, skill_group: Optional[str], level: int
    ) -> tuple:
        """
        Calcula max_level e is_temporary_boost baseado no grupo e nível

        Args:
            skill_group: 'FOR', 'CON', 'DES', 'INT', ou None (skill não mapeada)
            level: Nível atual da skill

        Returns:
            (max_level, is_temporary_boost)
        """
        if skill_group == "FOR":
            # FOR pode ser 8 permanentemente
            return (8, False)

        elif skill_group == "INT":
            # INT pode ser 8 temporariamente
            if level > 5:
                return (8, True)  # Boost temporário
            else:
                return (5, False)

        elif skill_group in ("CON", "DES"):
            # CON e DES sempre máximo 5
            return (5, False)

        else:  # skill_group é None (skill não mapeada)
            # Para skills não mapeadas, usar 5 como padrão
            return (5, False)

    _initialized_schema = False
    _schema_lock = threading.Lock()

    def ensure_table(self):
        """Garantir que a tabela player_skills exista com as colunas corretas"""
        if PlayerSkillsSyncService._initialized_schema:
            return

        with PlayerSkillsSyncService._schema_lock:
            if PlayerSkillsSyncService._initialized_schema:
                return

            max_retries = 3
            timeout = 30.0

            for attempt in range(max_retries):
                try:
                    with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                        cursor = conn.cursor()

                        # Criar tabela se não existir
                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS player_skills (
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
                            )
                        """
                        )

                        # Criar índices
                        cursor.execute(
                            """
                            CREATE INDEX IF NOT EXISTS idx_player_skills_steam_id 
                            ON player_skills(steam_id)
                        """
                        )
                        cursor.execute(
                            """
                            CREATE INDEX IF NOT EXISTS idx_player_skills_group 
                            ON player_skills(skill_group)
                        """
                        )
                        cursor.execute(
                            """
                            CREATE INDEX IF NOT EXISTS idx_player_skills_name 
                            ON player_skills(skill_name)
                        """
                        )

                        # Verificar se há colunas faltando e adicionar se necessário
                        cursor.execute("PRAGMA table_info(player_skills)")
                        existing_columns = {row[1] for row in cursor.fetchall()}

                        # Adicionar colunas que podem estar faltando (migração futura)
                        columns_to_add = {
                            "skill_group": "TEXT",
                            "max_level": "INTEGER DEFAULT 5",
                            "is_temporary_boost": "BOOLEAN DEFAULT 0",
                        }

                        for col_name, col_def in columns_to_add.items():
                            if col_name not in existing_columns:
                                try:
                                    cursor.execute(
                                        f"ALTER TABLE player_skills ADD COLUMN {col_name} {col_def}"
                                    )
                                except sqlite3.OperationalError:
                                    # Coluna pode já existir, ignorar erro
                                    pass

                        conn.commit()
                        PlayerSkillsSyncService._initialized_schema = True
                        return

                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        delay = 2.0 * (2**attempt)
                        self.logger.warn(
                            f"Banco bloqueado ao garantir tabela player_skills, tentando novamente em {delay:.1f}s"
                        )
                        time.sleep(delay)
                        continue
                    raise
                except Exception as exc:
                    self.logger.error(f"Erro ao garantir tabela player_skills: {exc}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2.0 * (2**attempt))

    # ------------------------------------------------------------------
    # Lógica de agendamento
    # ------------------------------------------------------------------

    def start(self) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "success": False,
                "message": "Sincronização de player skills desabilitada",
                "status": "disabled",
            }

        if self.is_running:
            return {
                "success": False,
                "message": "Sincronização de player skills já em execução",
                "status": "already_running",
            }

        try:
            self.ensure_table()
            self.logger.info("Executando sincronização inicial de player skills")
            self.sync_once()

            self.scheduler.clear()
            self.scheduler.every(self.sync_interval_hours).hours.do(self.sync_once)

            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self.scheduler_thread.start()
            self.is_running = True

            self.logger.info(
                "PlayerSkillsSyncService iniciado",
                {"sync_interval_hours": self.sync_interval_hours},
            )

            return {
                "success": True,
                "message": "Sincronização de player skills iniciada",
                "status": "started",
                "sync_interval_hours": self.sync_interval_hours,
            }

        except Exception as exc:
            self.logger.error(
                "Erro ao iniciar PlayerSkillsSyncService", {"error": str(exc)}
            )
            return {
                "success": False,
                "message": f"Erro ao iniciar sincronização: {exc}",
                "status": "error",
            }

    def stop(self) -> Dict[str, Any]:
        if not self.is_running:
            return {
                "success": False,
                "message": "Sincronização não está em execução",
                "status": "not_running",
            }

        self.stop_event.set()
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        self.scheduler.clear()
        self.is_running = False

        return {
            "success": True,
            "message": "Sincronização de player skills parada",
            "status": "stopped",
        }

    def _scheduler_loop(self):
        while not self.stop_event.is_set():
            try:
                self.scheduler.run_pending()
                time.sleep(1)
            except Exception as exc:
                self.logger.error(
                    "Erro no loop de agendamento de player skills", {"error": str(exc)}
                )
                time.sleep(5)

    # ------------------------------------------------------------------
    # Sincronização principal
    # ------------------------------------------------------------------

    def sync_once(self) -> Dict[str, Any]:
        start_time = time.monotonic()

        if not os.path.exists(self.scum_db_path):
            message = "SCUM.db não encontrado"
            self.logger.error(message, {"path": self.scum_db_path})
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": message},
            }
            return {"success": False, "error": message}

        try:
            self.ensure_table()

            # Buscar dados do SCUM.db com JOIN para obter steam_id e player_name
            from utils.scum_db_helper import scum_db_readonly_connection

            with scum_db_readonly_connection(self.scum_db_path) as scum_conn:
                scum_conn.row_factory = sqlite3.Row
                scum_cursor = scum_conn.cursor()
                scum_cursor.execute(
                    """
                    SELECT 
                        ps.prisoner_id,
                        ps.name AS skill_name,
                        ps.level,
                        ps.experience,
                        ps.xml,
                        u.id AS steam_id,
                        COALESCE(up.fake_name, up.name, up.user_id) AS player_name
                    FROM prisoner_skill ps
                    LEFT JOIN user_profile up ON ps.prisoner_id = up.prisoner_id
                    LEFT JOIN user u ON up.user_id = u.id
                    WHERE u.id IS NOT NULL
                    """
                )
                rows = scum_cursor.fetchall()

            # Inserir/atualizar no SSM.db
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cursor = conn.cursor()

                inserted = 0
                updated = 0
                last_updated = datetime.utcnow().isoformat()

                for row in rows:
                    row_dict = dict(row)
                    steam_id = row_dict.get("steam_id")
                    skill_name = row_dict.get("skill_name")

                    if not steam_id or not skill_name:
                        continue

                    # Calcular skill_group e metadados
                    skill_group = self.get_skill_group(skill_name)
                    max_level, is_temporary_boost = self.calculate_max_level_and_boost(
                        skill_group, row_dict.get("level", 0)
                    )

                    # Verificar se já existe
                    cursor.execute(
                        "SELECT id FROM player_skills WHERE steam_id = ? AND skill_name = ?",
                        (steam_id, skill_name),
                    )
                    exists = cursor.fetchone()

                    if exists:
                        # UPDATE
                        cursor.execute(
                            """
                            UPDATE player_skills 
                            SET prisoner_id = ?,
                                player_name = ?,
                                level = ?,
                                experience = ?,
                                xml = ?,
                                skill_group = ?,
                                max_level = ?,
                                is_temporary_boost = ?,
                                last_updated = ?
                            WHERE steam_id = ? AND skill_name = ?
                        """,
                            (
                                row_dict.get("prisoner_id"),
                                row_dict.get("player_name"),
                                row_dict.get("level"),
                                row_dict.get("experience"),
                                row_dict.get("xml"),
                                skill_group,
                                max_level,
                                1 if is_temporary_boost else 0,
                                last_updated,
                                steam_id,
                                skill_name,
                            ),
                        )
                        updated += 1
                    else:
                        # INSERT
                        cursor.execute(
                            """
                            INSERT INTO player_skills (
                                steam_id, player_name, prisoner_id,
                                skill_name, level, experience, xml,
                                skill_group, max_level, is_temporary_boost,
                                last_updated
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                steam_id,
                                row_dict.get("player_name"),
                                row_dict.get("prisoner_id"),
                                skill_name,
                                row_dict.get("level"),
                                row_dict.get("experience"),
                                row_dict.get("xml"),
                                skill_group,
                                max_level,
                                1 if is_temporary_boost else 0,
                                last_updated,
                            ),
                        )
                        inserted += 1

                conn.commit()

            elapsed = time.monotonic() - start_time

            result = {
                "success": True,
                "rows_inserted": inserted,
                "rows_updated": updated,
                "rows_processed": inserted + updated,
                "last_updated": last_updated,
                "elapsed_seconds": round(elapsed, 3),
            }

            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success",
                "details": result,
            }

            self.logger.info("Sincronização de player skills concluída", result)
            return result

        except Exception as exc:
            self.logger.error(
                "Erro durante sincronização de player skills", {"error": str(exc)}
            )
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": str(exc)},
            }
            return {"success": False, "error": str(exc)}

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "is_running": self.is_running,
            "sync_interval_hours": self.sync_interval_hours,
            "last_sync": self.last_sync_info,
        }
