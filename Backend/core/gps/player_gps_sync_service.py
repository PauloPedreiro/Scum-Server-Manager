"""Serviço de sincronização de GPS dos jogadores do SCUM para o SSM"""

import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import schedule

from utils.logger import StructuredLogger
from core.database.connector import DatabaseConnector


class PlayerGpsSyncService:
    """Sincroniza prisoner_spawn_location do SCUM.db para player_gps_snapshot no SSM.db"""

    def __init__(
        self,
        config: Dict[str, Any],
        path_helper=None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        self.gps_config = self.config.get("player_gps_sync", {})

        self.enabled = self.gps_config.get("enabled", True)
        self.auto_start = self.gps_config.get("auto_start", True)
        # Suportar intervalo em segundos ou minutos
        self.sync_interval_seconds = self.gps_config.get("sync_interval_seconds")
        self.sync_interval_minutes = self.gps_config.get("sync_interval_minutes")

        if self.sync_interval_seconds is not None:
            # Usar segundos se especificado
            self.sync_interval_value = self.sync_interval_seconds
            self.sync_interval_unit = "seconds"
        elif self.sync_interval_minutes is not None:
            # Usar minutos se especificado
            self.sync_interval_value = self.sync_interval_minutes
            self.sync_interval_unit = "minutes"
        else:
            # Padrão: 2 minutos
            self.sync_interval_value = 2
            self.sync_interval_unit = "minutes"

        # Configuração para usar conexão read-only strict (não cria WAL/SHM)
        self.use_strict_readonly = self.gps_config.get("use_strict_readonly", True)

        default_scum_db = (
            path_helper.get_scum_db_path()
            if path_helper
            else "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
        )
        default_ssm_db = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"

        self.scum_db_path = self.gps_config.get("scum_db_path") or default_scum_db
        self.ssm_db_path = self.gps_config.get("ssm_db_path") or default_ssm_db

        self.scheduler = schedule.Scheduler()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False
        self.use_custom_loop = False  # Usar loop customizado para segundos

        self.last_sync_info: Dict[str, Any] = {
            "timestamp": None,
            "status": "never_run",
            "details": {},
        }

        self.logger.info(
            "PlayerGpsSyncService inicializado",
            {
                "enabled": self.enabled,
                "auto_start": self.auto_start,
                "sync_interval": f"{self.sync_interval_value} {self.sync_interval_unit}",
                "use_strict_readonly": self.use_strict_readonly,
                "scum_db_path": self.scum_db_path,
                "ssm_db_path": self.ssm_db_path,
            },
        )

    def _connect_ssm(self, timeout: float = 30.0, write_mode: bool = False) -> sqlite3.Connection:
        """Usa o DatabaseConnector centralizado."""
        return DatabaseConnector.get_connection(self.ssm_db_path, timeout=timeout, write_mode=write_mode)

    _initialized_schema = False
    _schema_lock = threading.Lock()

    def ensure_table(self):
        """Garantir que a tabela snapshot exista"""
        if PlayerGpsSyncService._initialized_schema:
            return

        with PlayerGpsSyncService._schema_lock:
            if PlayerGpsSyncService._initialized_schema:
                return

            max_retries = 3
            timeout = 30.0

            for attempt in range(max_retries):
                try:
                    with self._connect_ssm(timeout=timeout, write_mode=True) as conn:
                        cursor = conn.cursor()

                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS player_gps_snapshot (
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
                            )
                            """
                        )

                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_player_gps_steam_id ON player_gps_snapshot(steam_id)"
                        )
                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_player_gps_type ON player_gps_snapshot(type)"
                        )

                        conn.commit()
                        PlayerGpsSyncService._initialized_schema = True
                        return

                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        delay = 2.0 * (2**attempt)
                        self.logger.warn(
                            f"Banco bloqueado ao criar tabela player_gps_snapshot, tentando novamente em {delay:.1f}s"
                        )
                        time.sleep(delay)
                        continue
                    raise
                except Exception as e:
                    self.logger.error(f"Erro ao criar tabela player_gps_snapshot: {e}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2.0 * (2**attempt))

    def start(self) -> Dict[str, Any]:
        """Iniciar o agendador de sincronização"""
        if not self.enabled:
            return {
                "success": False,
                "message": "Sincronização de GPS desabilitada",
                "status": "disabled",
            }

        if self.is_running:
            return {
                "success": False,
                "message": "Sincronização de GPS já está em execução",
                "status": "already_running",
            }

        try:
            self.ensure_table()
            self.logger.info("Executando sincronização inicial de GPS")
            self.sync_once()

            self.scheduler.clear()

            # Para intervalos em segundos, usar loop customizado (mais preciso)
            # Para intervalos em minutos, usar schedule (já funciona bem)
            if self.sync_interval_unit == "seconds":
                self.use_custom_loop = True
                self.logger.info(
                    f"Agendamento configurado: a cada {self.sync_interval_value} segundos (loop customizado)"
                )
            else:
                self.use_custom_loop = False

                # Wrapper para logar quando o job é executado pelo scheduler
                def sync_job_wrapper():
                    self.logger.info(
                        f"[SCHEDULER] Executando job de sincronização GPS agendado"
                    )
                    return self.sync_once()

                job = self.scheduler.every(self.sync_interval_value).minutes.do(
                    sync_job_wrapper
                )
                self.logger.info(
                    f"Agendamento configurado: a cada {self.sync_interval_value} minutos"
                )

                # Log próximo agendamento
                if hasattr(job, "next_run"):
                    next_run = job.next_run
                    if next_run:
                        self.logger.info(
                            f"Próxima execução agendada para: {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
                        )

            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self.scheduler_thread.start()
            self.is_running = True

            self.logger.info(
                "PlayerGpsSyncService iniciado",
                {
                    "sync_interval": f"{self.sync_interval_value} {self.sync_interval_unit}",
                    "is_running": self.is_running,
                    "thread_alive": (
                        self.scheduler_thread.is_alive()
                        if self.scheduler_thread
                        else False
                    ),
                    "jobs_count": len(self.scheduler.jobs),
                },
            )

            return {
                "success": True,
                "message": "Sincronização de GPS iniciada",
                "status": "started",
                "sync_interval": f"{self.sync_interval_value} {self.sync_interval_unit}",
            }

        except Exception as exc:
            self.logger.error(
                "Erro ao iniciar PlayerGpsSyncService", {"error": str(exc)}
            )
            return {
                "success": False,
                "message": f"Erro ao iniciar sincronização: {exc}",
                "status": "error",
            }

    def stop(self) -> Dict[str, Any]:
        """Parar o agendador de sincronização"""
        if not self.is_running:
            return {
                "success": False,
                "message": "Sincronização de GPS não está em execução",
                "status": "not_running",
            }

        try:
            self.is_running = False
            self.stop_event.set()
            self.scheduler.clear()

            if self.scheduler_thread:
                self.scheduler_thread.join(timeout=5)

            self.logger.info("PlayerGpsSyncService parado")

            return {
                "success": True,
                "message": "Sincronização de GPS parada",
                "status": "stopped",
            }

        except Exception as exc:
            self.logger.error("Erro ao parar PlayerGpsSyncService", {"error": str(exc)})
            return {
                "success": False,
                "message": f"Erro ao parar sincronização: {exc}",
                "status": "error",
            }

    def _scheduler_loop(self):
        """Loop do agendador"""
        if self.use_custom_loop:
            # Loop customizado para intervalos em segundos (mais preciso)
            self.logger.info(
                f"Loop customizado iniciado - intervalo: {self.sync_interval_value} segundos"
            )
            last_sync_time = time.monotonic()
            sync_count = 0

            while not self.stop_event.is_set():
                try:
                    current_time = time.monotonic()
                    elapsed = current_time - last_sync_time

                    # Verificar se é hora de sincronizar
                    if elapsed >= self.sync_interval_value:
                        sync_count += 1
                        self.logger.info(
                            f"[CUSTOM LOOP] Executando sincronização GPS #{sync_count} - intervalo decorrido: {elapsed:.2f}s"
                        )
                        self.sync_once()
                        last_sync_time = time.monotonic()

                    # Dormir por um tempo menor que o intervalo para manter precisão
                    sleep_time = min(1.0, self.sync_interval_value / 10)
                    time.sleep(sleep_time)

                except Exception as exc:
                    self.logger.error(
                        "Erro no loop customizado de GPS", {"error": str(exc)}
                    )
                    time.sleep(5)
        else:
            # Loop usando schedule para intervalos em minutos
            self.logger.info("Loop do agendador de GPS iniciado (usando schedule)")
            last_check = time.monotonic()
            check_count = 0
            while not self.stop_event.is_set():
                try:
                    jobs_before = len(self.scheduler.jobs)
                    self.scheduler.run_pending()
                    jobs_after = len(self.scheduler.jobs)

                    # Log a cada 30 verificações (aproximadamente a cada 30 segundos)
                    check_count += 1
                    if check_count % 30 == 0:
                        elapsed = time.monotonic() - last_check
                        self.logger.debug(
                            f"Scheduler ativo - Jobs: {jobs_before}, Verificações: {check_count}, Tempo desde último log: {elapsed:.1f}s"
                        )
                        last_check = time.monotonic()

                    time.sleep(1)  # Verificar a cada segundo
                except Exception as exc:
                    self.logger.error(
                        "Erro no loop de agendamento de GPS", {"error": str(exc)}
                    )
                    time.sleep(5)

    def sync_once(self) -> Dict[str, Any]:
        """Executar sincronização completa de GPS via RCON (única fonte de GPS ativa)"""
        start_time = time.monotonic()

        if not self._is_rcon_enabled():
            msg = "Sincronização de GPS desativada: RCON não está ativo/configurado."
            self.logger.info(f"[GPS SYNC] {msg}")
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "disabled",
                "details": {"message": msg},
            }
            return {
                "success": False,
                "error": "RCON_DISABLED",
                "message": msg,
            }

        try:
            result = self._sync_via_rcon()
            result["source"] = "rcon"
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success" if result.get("success") else "error",
                "details": result,
            }
            if result.get("success"):
                elapsed = time.monotonic() - start_time
                self.logger.info(
                    f"[GPS RCON] Sincronização finalizada — "
                    f"{result.get('players_synced', 0)} jogador(es) sincronizado(s) em {elapsed:.3f}s"
                )
            else:
                self.logger.error(
                    f"[GPS RCON] Falha na sincronização de GPS: {result.get('error')}"
                )
            return result
        except Exception as exc:
            self.logger.error(
                f"[GPS RCON] Exceção durante sincronização de GPS: {exc}",
                {"error": str(exc)},
            )
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": str(exc)},
            }
            return {"success": False, "error": str(exc)}

    def _is_rcon_enabled(self) -> bool:
        """Verifica se o RCON está habilitado e configurado no config.json."""
        try:
            import json
            with open("data/config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            rcon = cfg.get("rcon", {})
            return bool(rcon.get("enabled", False)) and bool(rcon.get("password", ""))
        except Exception:
            return False

    def _get_rcon_config(self) -> dict:
        """Retorna a seção 'rcon' do config.json."""
        try:
            import json
            with open("data/config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return cfg.get("rcon", {})
        except Exception:
            return {}

    def _sync_via_rcon(self) -> Dict[str, Any]:
        """
        Sincroniza o GPS de todos os jogadores online usando o ListPlayers do RCON.
        Muito mais rápido que o SCUM.db — retorna posição em tempo real.
        """
        from core.rcon_queue_manager import RconQueueManager
        from utils.rcon_client import parse_listplayers_response

        try:
            rcon_q = RconQueueManager.get_instance()
            raw = rcon_q.execute_command_sync("ListPlayers", delay_after=0.5, priority=20)
        except Exception as e:
            return {"success": False, "error": str(e), "players_synced": 0}

        players = parse_listplayers_response(raw)

        # Sincronizar tabela players_online do banco com base no RCON
        online_steam_ids = set()
        for p in players:
            steam_id = p.get("steam_id", "")
            if steam_id:
                online_steam_ids.add(steam_id)

        timestamp_iso = datetime.utcnow().isoformat()
        try:
            with self._connect_ssm(write_mode=True) as conn:
                cursor = conn.cursor()

                # Garantir que todos os jogadores online do RCON estão marcados como online no banco
                for p in players:
                    steam_id = p.get("steam_id", "")
                    if not steam_id:
                        continue

                    name = p.get("name", "")
                    x = p.get("location_x")
                    y = p.get("location_y")
                    z = p.get("location_z")

                    # 1. Garantir que o jogador existe na tabela players (para manter integridade)
                    player_id = p.get("index") or 0
                    cursor.execute("""
                        INSERT INTO players (
                            steam_id, player_name, player_id, first_seen, last_seen,
                            total_sessions, total_playtime, is_new_player, notification_sent, permissao
                        ) VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 0)
                        ON CONFLICT(steam_id) DO UPDATE SET
                            player_name = excluded.player_name,
                            last_seen = excluded.last_seen,
                            player_id = COALESCE(excluded.player_id, players.player_id)
                    """, (steam_id, name, player_id, timestamp_iso, timestamp_iso))

                    # 2. Inserir ou atualizar na tabela players_online
                    cursor.execute("""
                        INSERT INTO players_online (
                            steam_id, player_name, player_id, last_activity, 
                            coordinates_x, coordinates_y, coordinates_z, 
                            status, last_updated
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'online', CURRENT_TIMESTAMP)
                        ON CONFLICT(steam_id) DO UPDATE SET
                            player_name = excluded.player_name,
                            player_id = excluded.player_id,
                            coordinates_x = excluded.coordinates_x,
                            coordinates_y = excluded.coordinates_y,
                            coordinates_z = excluded.coordinates_z,
                            status = 'online',
                            last_updated = CURRENT_TIMESTAMP
                    """, (steam_id, name, player_id, timestamp_iso, x, y, z))

                # 3. Qualquer jogador que esteja como 'online' no banco, mas NÃO esteja na resposta RCON, marcar como 'offline'
                cursor.execute("SELECT steam_id FROM players_online WHERE status = 'online'")
                db_online_steam_ids = [row[0] for row in cursor.fetchall()]

                offline_steam_ids = [sid for sid in db_online_steam_ids if sid not in online_steam_ids]
                if offline_steam_ids:
                    placeholders = ','.join('?' * len(offline_steam_ids))
                    cursor.execute(
                        f"UPDATE players_online SET status = 'offline', last_updated = CURRENT_TIMESTAMP WHERE steam_id IN ({placeholders})",
                        offline_steam_ids
                    )
                    self.logger.info(
                        f"[GPS RCON Sync] {len(offline_steam_ids)} jogadores marcados como offline (não presentes no RCON)"
                    )
        except Exception as e:
            self.logger.error(f"[GPS RCON Sync] Erro ao sincronizar status online/offline no banco: {e}")

        if not players:
            self.logger.info("[GPS RCON] Nenhum jogador online.")
            return {"success": True, "players_synced": 0, "message": "Nenhum jogador online"}

        self.ensure_table()
        snapshot_at = datetime.utcnow().isoformat()
        players_synced = 0
        errors = []

        for p in players:
            steam_id = p.get("steam_id", "")
            if not steam_id:
                continue

            # Montar o dict no mesmo formato que _get_gps_from_scum retorna
            gps_entry = {
                "prisoner_id": None,
                "map_id": None,
                "type": 0,        # tipo fixo: posição online
                "shelter_id": None,
                "location_x": p.get("location_x"),
                "location_y": p.get("location_y"),
                "location_z": p.get("location_z"),
                "rotation_pitch": None,
                "rotation_yaw": None,
                "rotation_roll": None,
                "velocity_x": None,
                "velocity_y": None,
                "velocity_z": None,
                "player_name": p.get("name", ""),
                "fake_name": None,
            }

            try:
                self._update_snapshot(steam_id, [gps_entry])
                players_synced += 1
                self.logger.debug(
                    f"[GPS RCON] {steam_id} ({p.get('name')}) → "
                    f"X={p.get('location_x')} Y={p.get('location_y')} Z={p.get('location_z')}"
                )
            except Exception as e:
                errors.append({"steam_id": steam_id, "error": str(e)})
                self.logger.warn(f"[GPS RCON] Erro ao salvar snapshot de {steam_id}: {e}")

        result: Dict[str, Any] = {
            "success": True,
            "players_synced": players_synced,
            "source": "rcon",
        }
        if errors:
            result["errors"] = errors
            result["error_count"] = len(errors)

        return result

    def _get_online_steam_ids(self) -> List[str]:
        """Buscar apenas steam_ids de jogadores online do SSM.db"""
        try:
            self.logger.info(f"Buscando jogadores online no banco: {self.ssm_db_path}")
            if not os.path.exists(self.ssm_db_path):
                self.logger.error(f"Banco SSM.db não encontrado em: {self.ssm_db_path}")
                return []

            with self._connect_ssm(write_mode=True) as conn:
                # Verificar total de registros primeiro
                cursor = conn.execute("SELECT COUNT(*) FROM players_online")
                total = cursor.fetchone()[0]
                self.logger.info(f"Total de registros em players_online: {total}")

                # Buscar online
                cursor = conn.execute(
                    "SELECT steam_id FROM players_online WHERE status = 'online'"
                )
                steam_ids = [row[0] for row in cursor.fetchall()]
                self.logger.info(
                    f"Jogadores online encontrados: {len(steam_ids)} - {steam_ids}"
                )

                # Debug: verificar todos os status
                cursor = conn.execute("SELECT DISTINCT status FROM players_online")
                all_statuses = [row[0] for row in cursor.fetchall()]
                self.logger.info(f"Status únicos encontrados: {all_statuses}")

                return steam_ids
        except Exception as e:
            self.logger.error(
                f"Erro ao buscar jogadores online: {e}",
                {"error": str(e), "db_path": self.ssm_db_path},
            )
            return []

    def _get_gps_from_scum(self, steam_id: str) -> List[Dict[str, Any]]:
        """Buscar dados de GPS do SCUM.db para um steam_id específico"""
        try:
            # Usar conexão read-only strict se configurado (não cria WAL/SHM, dados frescos)
            if self.use_strict_readonly:
                from utils.scum_db_helper import scum_db_readonly_connection_strict

                with scum_db_readonly_connection_strict(self.scum_db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        SELECT 
                            psl.prisoner_id,
                            psl.map_id,
                            psl.type,
                            psl.shelter_id,
                            psl.location_x,
                            psl.location_y,
                            psl.location_z,
                            psl.rotation_pitch,
                            psl.rotation_yaw,
                            psl.rotation_roll,
                            psl.velocity_x,
                            psl.velocity_y,
                            psl.velocity_z,
                            u.id as steam_id,
                            up.name as player_name,
                            up.fake_name
                        FROM prisoner_spawn_location psl
                        INNER JOIN user_profile up ON psl.prisoner_id = up.prisoner_id
                        INNER JOIN user u ON up.user_id = u.id
                        WHERE u.id = ?
                        ORDER BY psl.type
                        """,
                        (steam_id,),
                    )

                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
            else:
                # Usar conexão normal (com cópia compartilhada se disponível)
                from utils.scum_db_helper import scum_db_readonly_connection

                with scum_db_readonly_connection(
                    self.scum_db_path, use_shared_copy=True
                ) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        SELECT 
                            psl.prisoner_id,
                            psl.map_id,
                            psl.type,
                            psl.shelter_id,
                            psl.location_x,
                            psl.location_y,
                            psl.location_z,
                            psl.rotation_pitch,
                            psl.rotation_yaw,
                            psl.rotation_roll,
                            psl.velocity_x,
                            psl.velocity_y,
                            psl.velocity_z,
                            u.id as steam_id,
                            up.name as player_name,
                            up.fake_name
                        FROM prisoner_spawn_location psl
                        INNER JOIN user_profile up ON psl.prisoner_id = up.prisoner_id
                        INNER JOIN user u ON up.user_id = u.id
                        WHERE u.id = ?
                        ORDER BY psl.type
                        """,
                        (steam_id,),
                    )

                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Erro ao buscar GPS do SCUM.db para {steam_id}: {e}")
            return []

    def _get_current_snapshot(self, steam_id: str) -> Optional[List[Dict[str, Any]]]:
        """Buscar snapshot atual do SSM.db para comparar"""
        try:
            with self._connect_ssm(write_mode=True) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT 
                        location_x, location_y, location_z,
                        rotation_pitch, rotation_yaw, rotation_roll,
                        velocity_x, velocity_y, velocity_z,
                        type
                    FROM player_gps_snapshot
                    WHERE steam_id = ?
                    ORDER BY type
                    """,
                    (steam_id,),
                )

                rows = cursor.fetchall()
                return [dict(row) for row in rows] if rows else None
        except Exception as e:
            return None

    def _has_changed(
        self, old_data: List[Dict[str, Any]], new_data: List[Dict[str, Any]]
    ) -> bool:
        """Verificar se houve mudança significativa nos dados"""
        if len(old_data) != len(new_data):
            return True

        for old, new in zip(old_data, new_data):
            # Comparar coordenadas (com tolerância de 0.1)
            if abs(old.get("location_x", 0) - new.get("location_x", 0)) > 0.1:
                return True
            if abs(old.get("location_y", 0) - new.get("location_y", 0)) > 0.1:
                return True
            if abs(old.get("location_z", 0) - new.get("location_z", 0)) > 0.1:
                return True

            # Comparar rotação (com tolerância de 0.1 graus)
            if abs(old.get("rotation_yaw", 0) - new.get("rotation_yaw", 0)) > 0.1:
                return True

            # Comparar velocidade (com tolerância de 0.01)
            if abs(old.get("velocity_x", 0) - new.get("velocity_x", 0)) > 0.01:
                return True
            if abs(old.get("velocity_y", 0) - new.get("velocity_y", 0)) > 0.01:
                return True
            if abs(old.get("velocity_z", 0) - new.get("velocity_z", 0)) > 0.01:
                return True

        return False

    def _update_snapshot(
        self, steam_id: str, gps_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Atualizar snapshot com dados de GPS"""
        snapshot_at = datetime.utcnow().isoformat()
        created_count = 0
        updated_count = 0

        try:
            with self._connect_ssm(write_mode=True) as conn:
                cursor = conn.cursor()

                for gps in gps_data:
                    spawn_type = gps.get("type")
                    player_name = gps.get("player_name")
                    fake_name = gps.get("fake_name")

                    # Verificar se já existe
                    cursor.execute(
                        "SELECT id FROM player_gps_snapshot WHERE steam_id = ? AND type = ?",
                        (steam_id, spawn_type),
                    )
                    exists = cursor.fetchone()

                    if exists:
                        # UPDATE
                        cursor.execute(
                            """
                            UPDATE player_gps_snapshot SET
                                prisoner_id = ?,
                                map_id = ?,
                                shelter_id = ?,
                                location_x = ?,
                                location_y = ?,
                                location_z = ?,
                                rotation_pitch = ?,
                                rotation_yaw = ?,
                                rotation_roll = ?,
                                velocity_x = ?,
                                velocity_y = ?,
                                velocity_z = ?,
                                player_name = ?,
                                fake_name = ?,
                                last_updated = ?
                            WHERE steam_id = ? AND type = ?
                            """,
                            (
                                gps.get("prisoner_id"),
                                gps.get("map_id"),
                                gps.get("shelter_id"),
                                gps.get("location_x"),
                                gps.get("location_y"),
                                gps.get("location_z"),
                                gps.get("rotation_pitch"),
                                gps.get("rotation_yaw"),
                                gps.get("rotation_roll"),
                                gps.get("velocity_x"),
                                gps.get("velocity_y"),
                                gps.get("velocity_z"),
                                player_name,
                                fake_name,
                                snapshot_at,
                                steam_id,
                                spawn_type,
                            ),
                        )
                        updated_count += 1
                    else:
                        # INSERT
                        cursor.execute(
                            """
                            INSERT INTO player_gps_snapshot (
                                prisoner_id, map_id, type, shelter_id,
                                location_x, location_y, location_z,
                                rotation_pitch, rotation_yaw, rotation_roll,
                                velocity_x, velocity_y, velocity_z,
                                steam_id, player_name, fake_name,
                                snapshot_at, last_updated
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                gps.get("prisoner_id"),
                                gps.get("map_id"),
                                spawn_type,
                                gps.get("shelter_id"),
                                gps.get("location_x"),
                                gps.get("location_y"),
                                gps.get("location_z"),
                                gps.get("rotation_pitch"),
                                gps.get("rotation_yaw"),
                                gps.get("rotation_roll"),
                                gps.get("velocity_x"),
                                gps.get("velocity_y"),
                                gps.get("velocity_z"),
                                steam_id,
                                player_name,
                                fake_name,
                                snapshot_at,
                                snapshot_at,
                            ),
                        )
                        created_count += 1

                conn.commit()

                return {
                    "created": created_count > 0,
                    "created_count": created_count,
                    "updated_count": updated_count,
                }

        except Exception as e:
            self.logger.error(f"Erro ao atualizar snapshot de GPS: {e}")
            raise

    def get_status(self) -> Dict[str, Any]:
        """Retornar status da última sincronização"""
        return {
            "enabled": self.enabled,
            "is_running": self.is_running,
            "sync_interval": f"{self.sync_interval_value} {self.sync_interval_unit}",
            "last_sync": self.last_sync_info,
        }
