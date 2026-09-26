"""Serviço de atualização da tabela rankings para o SSM.db"""
from core.database.connector import DatabaseConnector

import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import schedule

from utils.logger import StructuredLogger


class RankingsUpdateService:
    """Atualiza rankings agregados a partir de múltiplas fontes de dados"""

    def __init__(
        self,
        config: Dict[str, Any],
        path_helper=None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        self.rankings_config = self.config.get("rankings_sync", {})

        self.enabled = self.rankings_config.get("enabled", True)
        self.auto_start = self.rankings_config.get("auto_start", True)
        self.update_interval_hours = self.rankings_config.get(
            "update_interval_hours", 24
        )
        self.update_time = self.rankings_config.get(
            "update_time", "03:00"
        )  # Horário padrão: 03:00 AM

        default_ssm_db = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"
        self.ssm_db_path = self.rankings_config.get("ssm_db_path") or default_ssm_db

        self.scheduler = schedule.Scheduler()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False

        self.last_update_info: Dict[str, Any] = {
            "timestamp": None,
            "status": "never_run",
            "details": {},
        }

        # Garantir que o schema está atualizado
        self.ensure_schema()

        self.logger.info(
            "RankingsUpdateService inicializado",
            {
                "enabled": self.enabled,
                "auto_start": self.auto_start,
                "update_interval_hours": self.update_interval_hours,
                "update_time": self.update_time,
                "ssm_db_path": self.ssm_db_path,
            },
        )

    # ------------------------------------------------------------------
    # Verificação e atualização de schema
    # ------------------------------------------------------------------

    def ensure_schema(self):
        """Garantir que a tabela rankings tenha a coluna total_fame"""
        try:
            if not os.path.exists(self.ssm_db_path):
                self.logger.warn(
                    f"SSM.db não encontrado em {self.ssm_db_path}, schema não será verificado"
                )
                return

            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cursor = conn.cursor()

                # Verificar se a tabela rankings existe
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='rankings'
                """
                )
                table_exists = cursor.fetchone()

                if not table_exists:
                    self.logger.warn(
                        "Tabela rankings não existe ainda, será criada quando necessário"
                    )
                    return

                # Verificar se a coluna total_fame existe
                cursor.execute("PRAGMA table_info(rankings)")
                columns = [column[1] for column in cursor.fetchall()]

                if "total_fame" not in columns:
                    self.logger.info(
                        "Adicionando coluna total_fame na tabela rankings..."
                    )

                    try:
                        # Adicionar coluna
                        cursor.execute(
                            "ALTER TABLE rankings ADD COLUMN total_fame REAL DEFAULT 0.0"
                        )

                        # Criar índice
                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_rankings_total_fame ON rankings(total_fame DESC)"
                        )

                        # Atualizar valores existentes com dados de player_fame_totals
                        try:
                            cursor.execute(
                                """
                                UPDATE rankings
                                SET total_fame = (
                                    SELECT COALESCE(total_fame, 0.0)
                                    FROM player_fame_totals
                                    WHERE player_fame_totals.steam_id = rankings.steam_id
                                )
                                WHERE EXISTS (
                                    SELECT 1
                                    FROM player_fame_totals
                                    WHERE player_fame_totals.steam_id = rankings.steam_id
                                )
                            """
                            )
                            updated_count = cursor.rowcount
                            self.logger.info(
                                f"Coluna total_fame adicionada e {updated_count} registros atualizados"
                            )
                        except sqlite3.OperationalError as e:
                            # Se a tabela player_fame_totals não existir, apenas adiciona a coluna
                            self.logger.warn(
                                f"Tabela player_fame_totals não encontrada, coluna total_fame adicionada sem valores: {e}"
                            )

                        conn.commit()
                        self.logger.info(
                            "Schema da tabela rankings atualizado com sucesso"
                        )
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" in str(e).lower():
                            self.logger.info(
                                "Coluna total_fame já existe (pode ter sido adicionada por outro processo)"
                            )
                        else:
                            raise
                else:
                    self.logger.debug("Coluna total_fame já existe na tabela rankings")

        except Exception as e:
            self.logger.error(
                f"Erro ao verificar/atualizar schema da tabela rankings: {e}"
            )
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            # Não falha a inicialização se houver erro no schema

    # ------------------------------------------------------------------
    # Lógica de agendamento
    # ------------------------------------------------------------------

    def start(self) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "success": False,
                "message": "Atualização de rankings desabilitada",
                "status": "disabled",
            }

        if self.is_running:
            return {
                "success": False,
                "message": "Atualização de rankings já em execução",
                "status": "already_running",
            }

        try:
            self.logger.info("Executando atualização inicial de rankings")
            update_result = self.update_once()
            self.logger.info(
                "Resultado da atualização inicial", {"result": update_result}
            )

            self.scheduler.clear()
            # Agendar atualização diária no horário especificado
            self.scheduler.every().day.at(self.update_time).do(self.update_once)

            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self.scheduler_thread.start()
            self.is_running = True

            self.logger.info(
                "RankingsUpdateService iniciado",
                {"update_time": self.update_time},
            )

            return {
                "success": True,
                "message": "Atualização de rankings iniciada",
                "status": "started",
                "update_time": self.update_time,
            }

        except Exception as exc:
            self.logger.error(
                "Erro ao iniciar RankingsUpdateService", {"error": str(exc)}
            )
            return {
                "success": False,
                "message": f"Erro ao iniciar atualização: {exc}",
                "status": "error",
            }

    def stop(self) -> Dict[str, Any]:
        if not self.is_running:
            return {
                "success": False,
                "message": "Atualização não está em execução",
                "status": "not_running",
            }

        self.stop_event.set()
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        self.scheduler.clear()
        self.is_running = False

        return {
            "success": True,
            "message": "Atualização de rankings parada",
            "status": "stopped",
        }

    def _scheduler_loop(self):
        while not self.stop_event.is_set():
            try:
                self.scheduler.run_pending()
                time.sleep(1)
            except Exception as exc:
                self.logger.error(
                    "Erro no loop de agendamento de rankings", {"error": str(exc)}
                )
                time.sleep(5)

    # ------------------------------------------------------------------
    # Atualização principal
    # ------------------------------------------------------------------

    def update_once(self) -> Dict[str, Any]:
        start_time = time.monotonic()

        if not os.path.exists(self.ssm_db_path):
            message = "SSM.db não encontrado"
            self.logger.error(message, {"path": self.ssm_db_path})
            self.last_update_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": message},
            }
            return {"success": False, "error": message}

        try:
            # Obter todos os jogadores únicos de todas as fontes
            self.logger.info("Buscando jogadores para atualizar rankings")
            all_players = self._get_all_players()
            self.logger.info(f"Jogadores encontrados: {len(all_players)}")

            if not all_players:
                self.logger.warn("Nenhum jogador encontrado para atualizar rankings")
                return {
                    "success": True,
                    "rows_processed": 0,
                    "message": "Nenhum jogador encontrado",
                }

            updated_count = 0
            calculated_rankings = []

            # 1. Calcular rankings para todos os jogadores usando uma conexão de leitura (write_mode=False)
            self.logger.info("Iniciando cálculo de rankings (modo leitura)")
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=False) as conn:
                for steam_id, player_name in all_players.items():
                    try:
                        ranking_data = self._calculate_player_rankings(
                            conn, steam_id, player_name
                        )
                        calculated_rankings.append((steam_id, player_name, ranking_data))
                        updated_count += 1
                        if updated_count % 10 == 0:
                            self.logger.info(
                                f"Calculados rankings de {updated_count} jogadores..."
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Erro ao calcular ranking do jogador {steam_id}: {e}",
                            {"steam_id": steam_id, "error": str(e)},
                        )
                        import traceback
                        self.logger.error(f"Traceback: {traceback.format_exc()}")
                        continue

            # 2. Gravar os rankings calculados usando uma única transação rápida de escrita (write_mode=True)
            self.logger.info(f"Gravando {len(calculated_rankings)} rankings no banco (modo escrita)")
            saved_count = 0
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                for steam_id, player_name, ranking_data in calculated_rankings:
                    try:
                        self._insert_or_update_ranking(
                            conn, steam_id, player_name, ranking_data
                        )
                        saved_count += 1
                    except Exception as e:
                        self.logger.error(
                            f"Erro ao gravar ranking do jogador {steam_id}: {e}",
                            {"steam_id": steam_id, "error": str(e)},
                        )
                conn.commit()
                self.logger.info(
                    f"Gravados com sucesso {saved_count} rankings no banco."
                )

            elapsed = time.monotonic() - start_time

            result = {
                "success": True,
                "rows_processed": updated_count,
                "elapsed_seconds": round(elapsed, 3),
            }

            self.last_update_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success",
                "details": result,
            }

            self.logger.info("Atualização de rankings concluída", result)
            return result

        except Exception as exc:
            self.logger.error(
                "Erro durante atualização de rankings", {"error": str(exc)}
            )
            self.last_update_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": str(exc)},
            }
            return {"success": False, "error": str(exc)}

    def _get_all_players(self) -> Dict[str, str]:
        """Obter todos os jogadores únicos de todas as fontes"""
        players = {}

        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
            cursor = conn.cursor()

            # Jogadores de kill_events (killer)
            cursor.execute(
                """
                SELECT DISTINCT killer_steam_id, killer_profile_name
                FROM kill_events
                WHERE killer_steam_id IS NOT NULL AND killer_steam_id != ''
            """
            )
            for row in cursor.fetchall():
                steam_id, name = row
                if steam_id and steam_id not in players:
                    players[steam_id] = name or steam_id

            # Jogadores de kill_events (victim)
            cursor.execute(
                """
                SELECT DISTINCT victim_steam_id, victim_name
                FROM kill_events
                WHERE victim_steam_id IS NOT NULL AND victim_steam_id != ''
            """
            )
            for row in cursor.fetchall():
                steam_id, name = row
                if steam_id and steam_id not in players:
                    players[steam_id] = name or steam_id

            # Jogadores de minigame_events
            cursor.execute(
                """
                SELECT DISTINCT steam_id, player_name
                FROM minigame_events
                WHERE steam_id IS NOT NULL AND steam_id != ''
            """
            )
            for row in cursor.fetchall():
                steam_id, name = row
                if steam_id and steam_id not in players:
                    players[steam_id] = name or steam_id

            # Jogadores de vehicle_destruction_events
            cursor.execute(
                """
                SELECT DISTINCT owner_steam_id, owner_name
                FROM vehicle_destruction_events
                WHERE owner_steam_id IS NOT NULL AND owner_steam_id != ''
            """
            )
            for row in cursor.fetchall():
                steam_id, name = row
                if steam_id and steam_id not in players:
                    players[steam_id] = name or steam_id

            # Jogadores de survival_stats_snapshot
            cursor.execute(
                """
                SELECT DISTINCT steam_id, player_name
                FROM survival_stats_snapshot
                WHERE steam_id IS NOT NULL AND steam_id != ''
            """
            )
            for row in cursor.fetchall():
                steam_id, name = row
                if steam_id and steam_id not in players:
                    players[steam_id] = name or steam_id

            # Jogadores da tabela players (como fallback)
            cursor.execute(
                """
                SELECT DISTINCT steam_id, player_name
                FROM players
                WHERE steam_id IS NOT NULL AND steam_id != ''
            """
            )
            for row in cursor.fetchall():
                steam_id, name = row
                if steam_id and steam_id not in players:
                    players[steam_id] = name or steam_id

        return players

    def _calculate_player_rankings(
        self, conn: sqlite3.Connection, steam_id: str, player_name: str
    ) -> Dict[str, Any]:
        """Calcular todas as métricas de ranking para um jogador"""
        cursor = conn.cursor()
        rankings = {}

        # ==========================================
        # kill_events
        # ==========================================

        # Kills (event_type='kill' AND killer_is_npc=0)
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM kill_events 
            WHERE killer_steam_id = ? AND event_type = 'kill' AND killer_is_npc = 0
        """,
            (steam_id,),
        )
        rankings["kills"] = cursor.fetchone()[0] or 0

        # Deaths
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM kill_events 
            WHERE victim_steam_id = ? AND event_type = 'kill'
        """,
            (steam_id,),
        )
        rankings["deaths"] = cursor.fetchone()[0] or 0

        # KDR (calculado)
        if rankings["deaths"] > 0:
            rankings["kdr"] = round(rankings["kills"] / rankings["deaths"], 2)
        else:
            rankings["kdr"] = float(rankings["kills"]) if rankings["kills"] > 0 else 0.0

        # Longest Shot
        cursor.execute(
            """
            SELECT distance, weapon, timestamp
            FROM kill_events
            WHERE killer_steam_id = ? AND event_type = 'kill' AND distance IS NOT NULL AND distance > 0
            ORDER BY distance DESC
            LIMIT 1
        """,
            (steam_id,),
        )
        longest_shot = cursor.fetchone()
        if longest_shot:
            rankings["longest_shot_distance"] = longest_shot[0] or 0.0
            rankings["longest_shot_weapon"] = longest_shot[1]
            rankings["longest_shot_timestamp"] = longest_shot[2]
        else:
            rankings["longest_shot_distance"] = 0.0
            rankings["longest_shot_weapon"] = None
            rankings["longest_shot_timestamp"] = None

        # Suicides
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM kill_events 
            WHERE victim_steam_id = ? AND event_type = 'suicide'
        """,
            (steam_id,),
        )
        rankings["suicides"] = cursor.fetchone()[0] or 0

        # ==========================================
        # minigame_events por tipo de fechadura
        # ==========================================

        # Lockpick por tipo de fechadura
        lock_types = ["Basic", "Medium", "Advanced", "VeryEasy", "DialLock"]

        for lock_type in lock_types:
            lock_type_key = lock_type.lower()

            # Success por tipo
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM minigame_events 
                WHERE steam_id = ? AND minigame_type = 'LockpickingMinigame_C' 
                  AND success = 1 AND lock_type = ?
            """,
                (steam_id, lock_type),
            )
            success_count = cursor.fetchone()[0] or 0

            # Fails por tipo
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM minigame_events 
                WHERE steam_id = ? AND minigame_type = 'LockpickingMinigame_C' 
                  AND success = 0 AND lock_type = ?
            """,
                (steam_id, lock_type),
            )
            fails_count = cursor.fetchone()[0] or 0

            total_count = success_count + fails_count

            # Taxa de sucesso por tipo
            if total_count > 0:
                rate = round((success_count / total_count) * 100, 2)
            else:
                rate = 0.0

            rankings[f"lockpick_{lock_type_key}_success"] = success_count
            rankings[f"lockpick_{lock_type_key}_fails"] = fails_count
            rankings[f"lockpick_{lock_type_key}_total"] = total_count
            rankings[f"lockpick_{lock_type_key}_rate"] = rate

        # Lockpick "Other" (tipos não conhecidos ou NULL)
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM minigame_events 
            WHERE steam_id = ? AND minigame_type = 'LockpickingMinigame_C' 
              AND success = 1 AND (lock_type IS NULL OR lock_type NOT IN ('Basic', 'Medium', 'Advanced', 'VeryEasy', 'DialLock'))
        """,
            (steam_id,),
        )
        other_success = cursor.fetchone()[0] or 0

        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM minigame_events 
            WHERE steam_id = ? AND minigame_type = 'LockpickingMinigame_C' 
              AND success = 0 AND (lock_type IS NULL OR lock_type NOT IN ('Basic', 'Medium', 'Advanced', 'VeryEasy', 'DialLock'))
        """,
            (steam_id,),
        )
        other_fails = cursor.fetchone()[0] or 0

        other_total = other_success + other_fails
        other_rate = (
            round((other_success / other_total) * 100, 2) if other_total > 0 else 0.0
        )

        rankings["lockpick_other_success"] = other_success
        rankings["lockpick_other_fails"] = other_fails
        rankings["lockpick_other_total"] = other_total
        rankings["lockpick_other_rate"] = other_rate

        # ==========================================
        # vehicle_destruction_events
        # ==========================================

        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM vehicle_destruction_events 
            WHERE owner_steam_id = ?
        """,
            (steam_id,),
        )
        rankings["vehicles_destroyed"] = cursor.fetchone()[0] or 0

        # ==========================================
        # survival_stats_snapshot (usar snapshot mais recente)
        # ==========================================

        cursor.execute(
            """
            SELECT total_defecations, animals_killed, players_knocked_out, headshots, 
                   minutes_survived, overdose, highest_weight_carried
            FROM survival_stats_snapshot
            WHERE steam_id = ?
            ORDER BY snapshot_at DESC
            LIMIT 1
        """,
            (steam_id,),
        )
        survival_row = cursor.fetchone()

        if survival_row:
            rankings["highest_defecation"] = survival_row[0] or 0
            rankings["animals_killed"] = survival_row[1] or 0
            rankings["players_knocked_out"] = survival_row[2] or 0
            rankings["headshots"] = survival_row[3] or 0
            rankings["minutes_survived"] = survival_row[4] or 0.0
            rankings["overdoses"] = survival_row[5] or 0
            rankings["highest_weight_carried"] = survival_row[6] or 0.0
        else:
            rankings["highest_defecation"] = 0
            rankings["animals_killed"] = 0
            rankings["players_knocked_out"] = 0
            rankings["headshots"] = 0
            rankings["minutes_survived"] = 0.0
            rankings["overdoses"] = 0
            rankings["highest_weight_carried"] = 0.0

        # ==========================================
        # player_fame_totals
        # ==========================================

        cursor.execute(
            """
            SELECT total_fame
            FROM player_fame_totals
            WHERE steam_id = ?
        """,
            (steam_id,),
        )
        fame_row = cursor.fetchone()

        if fame_row:
            rankings["total_fame"] = fame_row[0] or 0.0
        else:
            rankings["total_fame"] = 0.0

        return rankings

    def _insert_or_update_ranking(
        self,
        conn: sqlite3.Connection,
        steam_id: str,
        player_name: str,
        rankings: Dict[str, Any],
    ):
        """Inserir ou atualizar ranking de um jogador"""
        cursor = conn.cursor()

        # Atualizar player_name se necessário (pegar o mais recente/não-nulo)
        if not player_name or player_name == steam_id:
            # Tentar obter nome da tabela players
            cursor.execute(
                "SELECT player_name FROM players WHERE steam_id = ?", (steam_id,)
            )
            player_row = cursor.fetchone()
            if player_row and player_row[0]:
                player_name = player_row[0]
            elif not player_name:
                player_name = steam_id

        cursor.execute(
            """
            INSERT OR REPLACE INTO rankings (
                steam_id, player_name,
                kills, deaths, kdr,
                longest_shot_distance, longest_shot_weapon, longest_shot_timestamp,
                suicides,
                lockpick_basic_success, lockpick_basic_fails, lockpick_basic_total, lockpick_basic_rate,
                lockpick_medium_success, lockpick_medium_fails, lockpick_medium_total, lockpick_medium_rate,
                lockpick_advanced_success, lockpick_advanced_fails, lockpick_advanced_total, lockpick_advanced_rate,
                lockpick_veryeasy_success, lockpick_veryeasy_fails, lockpick_veryeasy_total, lockpick_veryeasy_rate,
                lockpick_diallock_success, lockpick_diallock_fails, lockpick_diallock_total, lockpick_diallock_rate,
                lockpick_other_success, lockpick_other_fails, lockpick_other_total, lockpick_other_rate,
                vehicles_destroyed,
                highest_defecation, animals_killed, players_knocked_out,
                headshots, minutes_survived, overdoses, highest_weight_carried,
                total_fame,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                steam_id,
                player_name,
                rankings.get("kills", 0),
                rankings.get("deaths", 0),
                rankings.get("kdr", 0.0),
                rankings.get("longest_shot_distance", 0.0),
                rankings.get("longest_shot_weapon"),
                rankings.get("longest_shot_timestamp"),
                rankings.get("suicides", 0),
                rankings.get("lockpick_basic_success", 0),
                rankings.get("lockpick_basic_fails", 0),
                rankings.get("lockpick_basic_total", 0),
                rankings.get("lockpick_basic_rate", 0.0),
                rankings.get("lockpick_medium_success", 0),
                rankings.get("lockpick_medium_fails", 0),
                rankings.get("lockpick_medium_total", 0),
                rankings.get("lockpick_medium_rate", 0.0),
                rankings.get("lockpick_advanced_success", 0),
                rankings.get("lockpick_advanced_fails", 0),
                rankings.get("lockpick_advanced_total", 0),
                rankings.get("lockpick_advanced_rate", 0.0),
                rankings.get("lockpick_veryeasy_success", 0),
                rankings.get("lockpick_veryeasy_fails", 0),
                rankings.get("lockpick_veryeasy_total", 0),
                rankings.get("lockpick_veryeasy_rate", 0.0),
                rankings.get("lockpick_diallock_success", 0),
                rankings.get("lockpick_diallock_fails", 0),
                rankings.get("lockpick_diallock_total", 0),
                rankings.get("lockpick_diallock_rate", 0.0),
                rankings.get("lockpick_other_success", 0),
                rankings.get("lockpick_other_fails", 0),
                rankings.get("lockpick_other_total", 0),
                rankings.get("lockpick_other_rate", 0.0),
                rankings.get("vehicles_destroyed", 0),
                rankings.get("highest_defecation", 0),
                rankings.get("animals_killed", 0),
                rankings.get("players_knocked_out", 0),
                rankings.get("headshots", 0),
                rankings.get("minutes_survived", 0.0),
                rankings.get("overdoses", 0),
                rankings.get("highest_weight_carried", 0.0),
                rankings.get("total_fame", 0.0),
                datetime.utcnow().isoformat(),
            ),
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "is_running": self.is_running,
            "update_interval_hours": self.update_interval_hours,
            "update_time": self.update_time,
            "last_update": self.last_update_info,
        }
