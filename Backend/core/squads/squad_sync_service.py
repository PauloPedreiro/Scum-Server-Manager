"""Serviço de sincronização de squads do SCUM para o SSM"""
from core.database.connector import DatabaseConnector

import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import schedule

from utils.logger import StructuredLogger


class SquadSyncService:
    """Sincroniza squads do SCUM.db para tabelas snapshot no SSM.db"""

    def __init__(
        self,
        config: Dict[str, Any],
        path_helper=None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        self.squad_config = self.config.get("squad_sync", {})

        self.enabled = self.squad_config.get("enabled", True)
        self.auto_start = self.squad_config.get("auto_start", True)
        self.sync_interval_minutes = self.squad_config.get("sync_interval_minutes", 30)

        default_scum_db = (
            path_helper.get_scum_db_path()
            if path_helper
            else "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
        )
        default_ssm_db = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"

        self.scum_db_path = self.squad_config.get("scum_db_path") or default_scum_db
        self.ssm_db_path = self.squad_config.get("ssm_db_path") or default_ssm_db

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
            "SquadSyncService inicializado",
            {
                "enabled": self.enabled,
                "auto_start": self.auto_start,
                "sync_interval_minutes": self.sync_interval_minutes,
                "scum_db_path": self.scum_db_path,
                "ssm_db_path": self.ssm_db_path,
            },
        )

    _initialized_schema = False
    _schema_lock = threading.Lock()

    def ensure_tables(self):
        """Garantir que as tabelas snapshot existam"""
        if SquadSyncService._initialized_schema:
            return

        with SquadSyncService._schema_lock:
            if SquadSyncService._initialized_schema:
                return

            max_retries = 3
            timeout = 30.0

            for attempt in range(max_retries):
                try:
                    with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                        cursor = conn.cursor()

                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS squad_snapshot (
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
                            )
                            """
                        )

                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS squad_member_snapshot (
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
                            )
                            """
                        )

                        # Garantir colunas em cenários de upgrade
                        cursor.execute("PRAGMA table_info(squad_snapshot)")
                        squad_columns = {row[1] for row in cursor.fetchall()}
                        if "flag_count" not in squad_columns:
                            cursor.execute(
                                "ALTER TABLE squad_snapshot ADD COLUMN flag_count INTEGER DEFAULT 0"
                            )
                        if "flag_ids" not in squad_columns:
                            cursor.execute(
                                "ALTER TABLE squad_snapshot ADD COLUMN flag_ids TEXT"
                            )

                        cursor.execute("PRAGMA table_info(squad_member_snapshot)")
                        member_columns = {row[1] for row in cursor.fetchall()}
                        if "player_steam_id" not in member_columns:
                            cursor.execute(
                                "ALTER TABLE squad_member_snapshot ADD COLUMN player_steam_id TEXT"
                            )

                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_squad_snapshot_squad_id ON squad_snapshot(squad_id)"
                        )
                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_squad_snapshot_rank ON squad_snapshot(rank_position)"
                        )
                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_squad_member_snapshot_squad_id ON squad_member_snapshot(squad_id)"
                        )

                        conn.commit()
                        SquadSyncService._initialized_schema = True
                        return

                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        delay = 2.0 * (2**attempt)
                        self.logger.warn(
                            f"Banco bloqueado ao garantir tabelas de squads, tentando novamente em {delay:.1f}s"
                        )
                        time.sleep(delay)
                        continue
                    raise
                except Exception as exc:
                    self.logger.error(f"Erro ao garantir tabelas de squads: {exc}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2.0 * (2**attempt))

    def start(self) -> Dict[str, Any]:
        """Iniciar sincronização periódica"""
        if not self.enabled:
            return {
                "success": False,
                "message": "Sincronização de squads desabilitada",
                "status": "disabled",
            }

        if self.is_running:
            return {
                "success": False,
                "message": "Sincronização de squads já em execução",
                "status": "already_running",
            }

        try:
            self.ensure_tables()

            # Primeira sincronização imediata
            self.logger.info("Executando sincronização inicial de squads")
            self.sync_once()

            # Agendar próximas execuções
            self.scheduler.clear()
            self.scheduler.every(self.sync_interval_minutes).minutes.do(self.sync_once)

            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self.scheduler_thread.start()
            self.is_running = True

            self.logger.info(
                "SquadSyncService iniciado",
                {"sync_interval_minutes": self.sync_interval_minutes},
            )

            return {
                "success": True,
                "message": "Sincronização de squads iniciada",
                "status": "started",
                "sync_interval_minutes": self.sync_interval_minutes,
            }

        except Exception as exc:
            self.logger.error("Erro ao iniciar SquadSyncService", {"error": str(exc)})
            return {
                "success": False,
                "message": f"Erro ao iniciar sincronização: {exc}",
                "status": "error",
            }

    def stop(self) -> Dict[str, Any]:
        """Parar sincronização periódica"""
        if not self.is_running:
            return {
                "success": False,
                "message": "Sincronização de squads não está em execução",
                "status": "not_running",
            }

        self.stop_event.set()
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        self.scheduler.clear()
        self.is_running = False

        return {
            "success": True,
            "message": "Sincronização de squads parada",
            "status": "stopped",
        }

    def _scheduler_loop(self):
        """Loop do agendador"""
        while not self.stop_event.is_set():
            try:
                self.scheduler.run_pending()
                time.sleep(1)
            except Exception as exc:
                self.logger.error(
                    "Erro no loop de agendamento de squads", {"error": str(exc)}
                )
                time.sleep(5)

    def sync_once(self) -> Dict[str, Any]:
        """Executar sincronização completa uma vez"""
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
            self.ensure_tables()

            squads, members, flag_counts, flag_ids = self._fetch_scum_data()
            result = self._persist_snapshot(squads, members, flag_counts, flag_ids)

            elapsed = time.monotonic() - start_time
            result["elapsed_seconds"] = round(elapsed, 3)

            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success" if result.get("success") else "warning",
                "details": result,
            }

            status = "sucesso" if result.get("success") else "com avisos"
            self.logger.info(
                f"Sincronização de squads finalizada com {status}",
                result,
            )

            return result

        except Exception as exc:
            self.logger.error(
                "Erro durante sincronização de squads", {"error": str(exc)}
            )
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": str(exc)},
            }
            return {"success": False, "error": str(exc)}

    def get_status(self) -> Dict[str, Any]:
        """Retornar status da última sincronização"""
        return {
            "enabled": self.enabled,
            "is_running": self.is_running,
            "sync_interval_minutes": self.sync_interval_minutes,
            "last_sync": self.last_sync_info,
        }

    def _fetch_scum_data(self):
        """Buscar dados de squads e membros no SCUM.db"""
        from utils.scum_db_helper import scum_db_readonly_connection

        with scum_db_readonly_connection(self.scum_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            squads_rows = cursor.execute(
                """
                SELECT id, name, message, emblem, information, score, member_limit,
                       last_member_login_time, last_member_logout_time
                FROM squad
                ORDER BY score DESC, id ASC
                """
            ).fetchall()

            members_rows = cursor.execute(
                """
                SELECT sm.id AS member_id,
                       sm.squad_id,
                       sm.user_profile_id,
                       sm.rank,
                       up.fake_name,
                       up.name AS profile_name,
                       up.user_id,
                       up.fame_points,
                       up.last_login_time,
                       up.last_logout_time,
                       up.play_time
                FROM squad_member sm
                LEFT JOIN user_profile up ON up.id = sm.user_profile_id
                ORDER BY sm.squad_id ASC, sm.rank ASC, sm.id ASC
                """
            ).fetchall()

            # Buscar contagem de flags (para compatibilidade)
            flag_count_rows = cursor.execute(
                """
                SELECT sm.squad_id,
                       COUNT(DISTINCT bef.element_id) AS flag_count
                FROM base_element_flag bef
                JOIN base_element be ON be.element_id = bef.element_id
                JOIN squad_member sm ON sm.user_profile_id = be.owner_profile_id
                WHERE sm.squad_id IS NOT NULL
                GROUP BY sm.squad_id
                """
            ).fetchall()

            # Buscar IDs das flags agrupados por squad
            flag_ids_rows = cursor.execute(
                """
                SELECT sm.squad_id,
                       GROUP_CONCAT(DISTINCT bef.element_id) AS flag_ids
                FROM base_element_flag bef
                JOIN base_element be ON be.element_id = bef.element_id
                JOIN squad_member sm ON sm.user_profile_id = be.owner_profile_id
                WHERE sm.squad_id IS NOT NULL
                GROUP BY sm.squad_id
                """
            ).fetchall()

        squads = [dict(row) for row in squads_rows]
        members = [dict(row) for row in members_rows]
        flag_counts = {row["squad_id"]: row["flag_count"] or 0 for row in flag_count_rows}
        # Converter flag_ids de string para manter formato consistente
        flag_ids_dict = {
            row["squad_id"]: row["flag_ids"] if row["flag_ids"] else None
            for row in flag_ids_rows
        }

        return squads, members, flag_counts, flag_ids_dict

    def _persist_snapshot(
        self,
        squads: List[Dict[str, Any]],
        members: List[Dict[str, Any]],
        flag_counts: Dict[int, int],
        flag_ids: Dict[int, Optional[str]],
    ):
        """Persistir snapshot no SSM.db"""
        snapshot_at = datetime.utcnow().isoformat()

        # Organizar membros por squad
        members_by_squad: Dict[int, List[Dict[str, Any]]] = {}
        for member in members:
            squad_id = member.get("squad_id")
            members_by_squad.setdefault(squad_id, []).append(member)

        # Ordenar squads por score (desc) e id (asc)
        sorted_squads = sorted(
            squads,
            key=lambda item: (
                -(item.get("score") or 0),
                item.get("id") or 0,
            ),
        )

        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            conn.execute("PRAGMA foreign_keys = ON")

            # Cache de steam IDs a partir da tabela players (quando disponível)
            players_cache: Dict[str, str] = {}
            try:
                cursor.execute("SELECT player_name, steam_id FROM players")
                players_cache = {
                    row[0]: row[1] for row in cursor.fetchall() if row[0] and row[1]
                }
            except sqlite3.Error as exc:
                self.logger.warn(
                    "Não foi possível carregar steam_ids da tabela players",
                    {"error": str(exc)},
                )

            # Rastrear saídas de squad para o BountyService
            old_members = {}
            try:
                cursor.execute("SELECT player_steam_id, squad_id FROM squad_member_snapshot WHERE player_steam_id IS NOT NULL")
                old_members = {row[0]: row[1] for row in cursor.fetchall()}
            except Exception as old_err:
                self.logger.warn("Não foi possível carregar snapshots antigos de squad para rastrear saídas", {"error": str(old_err)})

            cursor.execute("DELETE FROM squad_member_snapshot")
            cursor.execute("DELETE FROM squad_snapshot")

            total_members = 0

            for position, squad in enumerate(sorted_squads, start=1):
                squad_id = squad.get("id")
                squad_members = members_by_squad.get(squad_id, [])

                flag_count = flag_counts.get(squad_id, 0)
                flag_ids_str = flag_ids.get(squad_id)

                cursor.execute(
                    """
                    INSERT INTO squad_snapshot (
                        squad_id, name, message, information, emblem, score, member_limit,
                        member_count, flag_count, flag_ids, last_member_login_time, last_member_logout_time,
                        rank_position, snapshot_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        squad_id,
                        squad.get("name"),
                        squad.get("message"),
                        squad.get("information"),
                        (
                            str(squad.get("emblem"))
                            if squad.get("emblem") is not None
                            else None
                        ),
                        squad.get("score"),
                        squad.get("member_limit"),
                        len(squad_members),
                        flag_count,
                        flag_ids_str,  # IDs das flags separados por vírgula
                        squad.get("last_member_login_time"),
                        squad.get("last_member_logout_time"),
                        position,
                        snapshot_at,
                    ),
                )

                snapshot_id = cursor.lastrowid

                for member in squad_members:
                    player_name = (
                        member.get("fake_name")
                        or member.get("profile_name")
                        or member.get("user_id")
                        or "Jogador"
                    )

                    player_steam_id = member.get("user_id") or players_cache.get(
                        player_name
                    )

                    cursor.execute(
                        """
                        INSERT INTO squad_member_snapshot (
                            squad_snapshot_id, squad_id, member_id, user_profile_id, player_steam_id, player_name,
                            rank, fame_points, last_login_time, last_logout_time, play_time
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            snapshot_id,
                            squad_id,
                            member.get("member_id"),
                            member.get("user_profile_id"),
                            player_steam_id,
                            player_name,
                            member.get("rank"),
                            member.get("fame_points"),
                            member.get("last_login_time"),
                            member.get("last_logout_time"),
                            member.get("play_time"),
                        ),
                    )

                    total_members += 1

            # Comparar e registrar saídas de squad
            if old_members:
                try:
                    cursor.execute("SELECT player_steam_id, squad_id FROM squad_member_snapshot WHERE player_steam_id IS NOT NULL")
                    new_members = {row[0]: row[1] for row in cursor.fetchall()}
                    
                    from app.extensions import get_services
                    svc = get_services()
                    bounty_svc = getattr(svc, "bounty_service", None)
                    
                    for steam_id, old_squad_id in old_members.items():
                        new_squad_id = new_members.get(steam_id)
                        if new_squad_id != old_squad_id:
                            if bounty_svc:
                                bounty_svc.log_squad_leave(steam_id, old_squad_id)
                except Exception as compare_err:
                    self.logger.error("Erro ao comparar saídas de squad", {"error": str(compare_err)})

            conn.commit()

        return {
            "success": True,
            "squads_processed": len(sorted_squads),
            "members_processed": total_members,
            "snapshot_at": snapshot_at,
        }

    def get_all_flags_with_locations(self) -> Dict[str, Any]:
        """
        Buscar todas as bandeiras do mapa com suas localizações e owners

        Retorna:
        - Lista de todas as bandeiras com coordenadas
        - Owner quando disponível, "no owner" quando não tiver
        - Informações da base associada
        """
        if not os.path.exists(self.scum_db_path):
            return {
                "success": False,
                "error": "SCUM.db não encontrado",
                "flags": [],
                "total": 0,
            }

        try:
            from utils.scum_db_helper import scum_db_readonly_connection

            with scum_db_readonly_connection(self.scum_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Buscar todas as flags com localizações e owners
                cursor.execute(
                    """
                    SELECT 
                        bef.element_id,
                        be.location_x,
                        be.location_y,
                        be.location_z,
                        be.base_id,
                        b.name AS base_name,
                        b.location_x AS base_location_x,
                        b.location_y AS base_location_y,
                        be.owner_profile_id,
                        up.fake_name AS owner_name,
                        up.name AS owner_profile_name,
                        up.user_id AS owner_steam_id,
                        sm.squad_id,
                        s.name AS squad_name,
                        bef.overtake_end_time,
                        bef.overtaker_user_profile_id
                    FROM base_element_flag bef
                    JOIN base_element be ON be.element_id = bef.element_id
                    LEFT JOIN base b ON b.id = be.base_id
                    LEFT JOIN user_profile up ON up.id = be.owner_profile_id
                    LEFT JOIN squad_member sm ON sm.user_profile_id = be.owner_profile_id
                    LEFT JOIN squad s ON s.id = sm.squad_id
                    ORDER BY be.base_id, bef.element_id
                """
                )

                rows = cursor.fetchall()
                flags = []

                for row in rows:
                    # Determinar owner
                    owner_info = "no owner"
                    owner_steam_id = None
                    owner_name = None
                    squad_id = None
                    squad_name = None

                    if row["owner_profile_id"]:
                        # Tentar pegar nome do owner
                        owner_name = (
                            row["owner_name"]
                            or row["owner_profile_name"]
                            or f"Profile {row['owner_profile_id']}"
                        )
                        owner_steam_id = row["owner_steam_id"]
                        squad_id = row["squad_id"]
                        squad_name = row["squad_name"]

                        if owner_steam_id:
                            owner_info = f"{owner_name} ({owner_steam_id})"
                        else:
                            owner_info = owner_name

                        if squad_name:
                            owner_info += f" - Squad: {squad_name}"

                    flags.append(
                        {
                            "element_id": row["element_id"],
                            "location": {
                                "x": row["location_x"],
                                "y": row["location_y"],
                                "z": row["location_z"],
                            },
                            "base": (
                                {
                                    "id": row["base_id"],
                                    "name": row["base_name"],
                                    "location": (
                                        {
                                            "x": row["base_location_x"],
                                            "y": row["base_location_y"],
                                        }
                                        if row["base_location_x"]
                                        and row["base_location_y"]
                                        else None
                                    ),
                                }
                                if row["base_id"]
                                else None
                            ),
                            "owner": owner_info,
                            "owner_profile_id": row["owner_profile_id"],
                            "owner_steam_id": owner_steam_id,
                            "owner_name": owner_name,
                            "squad_id": squad_id,
                            "squad_name": squad_name,
                            "overtake_end_time": row["overtake_end_time"],
                            "overtaker_user_profile_id": row[
                                "overtaker_user_profile_id"
                            ],
                        }
                    )

                return {
                    "success": True,
                    "flags": flags,
                    "total": len(flags),
                    "with_owner": len([f for f in flags if f["owner"] != "no owner"]),
                    "no_owner": len([f for f in flags if f["owner"] == "no owner"]),
                }

        except Exception as exc:
            self.logger.error(
                "Erro ao buscar flags com localizações", {"error": str(exc)}
            )
            return {"success": False, "error": str(exc), "flags": [], "total": 0}
