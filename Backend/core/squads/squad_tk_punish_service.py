"""Serviço de punição e monitoramento por Team Kill (TK) no SSM"""

import os
import re
import math
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.database.connector import DatabaseConnector
from utils.logger import StructuredLogger

class SquadTKJailService:
    """Gerencia o ciclo de vida da prisão por Team Kill, incluindo monitoramento e evasão"""

    def __init__(
        self,
        config: Dict[str, Any],
        path_helper=None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        
        # Carregar as referências iniciais da config
        tk_config = self.config.get("squad_tk_jail", {})
        self.jail_coords_str = tk_config.get(
            "jail_coordinates", 
            "-271417.281 314246.875 84056.023"
        )
        self.ssm_db_path = path_helper.get_ssm_db_path() if path_helper else "data/SSM.db"
        
        # Thread de monitoramento
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False
        
        # Inicializar banco
        self.ensure_tables()
        
        self.logger.info(
            "SquadTKJailService inicializado",
            {
                "jail_coordinates": self.jail_coords_str,
                "ssm_db_path": self.ssm_db_path,
            },
        )

    def ensure_tables(self):
        """Garante que a tabela prison_records exista no banco de dados"""
        max_retries = 3
        timeout = 30.0
        
        for attempt in range(max_retries):
            try:
                with DatabaseConnector.get_connection(self.ssm_db_path, timeout=timeout, write_mode=True) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS prison_records (
                            steam_id TEXT PRIMARY KEY,
                            player_name TEXT,
                            squad_id INTEGER,
                            jailed_at TEXT NOT NULL,
                            remaining_seconds INTEGER NOT NULL,
                            last_tick_at TEXT,
                            status TEXT NOT NULL DEFAULT 'active',
                            release_coords_x REAL,
                            release_coords_y REAL,
                            release_coords_z REAL
                        )
                        """
                    )
                    cursor.execute(
                        "CREATE INDEX IF NOT EXISTS idx_prison_records_steam_id_status ON prison_records(steam_id, status)"
                    )
                    
                    # Migração dinâmica: adicionar colunas se não existirem
                    try:
                        cursor.execute("ALTER TABLE prison_records ADD COLUMN release_coords_x REAL")
                    except sqlite3.OperationalError:
                        pass
                    try:
                        cursor.execute("ALTER TABLE prison_records ADD COLUMN release_coords_y REAL")
                    except sqlite3.OperationalError:
                        pass
                    try:
                        cursor.execute("ALTER TABLE prison_records ADD COLUMN release_coords_z REAL")
                    except sqlite3.OperationalError:
                        pass
                        
                    conn.commit()
                    return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(2.0 * (2**attempt))
                    continue
                raise
            except Exception as e:
                self.logger.error(f"Erro ao criar tabela prison_records: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2.0 * (2**attempt))

    def start(self) -> Dict[str, Any]:
        """Inicia a thread de monitoramento da prisão"""
        if self.is_running:
            return {"success": False, "message": "Serviço já em execução"}
            
        self.stop_event.clear()
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="SquadTKJailMonitor")
        self.monitor_thread.start()
        self.logger.info("Thread de monitoramento do SquadTKJailService iniciada")
        return {"success": True, "message": "Serviço iniciado com sucesso"}

    def stop(self) -> Dict[str, Any]:
        """Para a thread de monitoramento"""
        if not self.is_running:
            return {"success": False, "message": "Serviço não está em execução"}
            
        self.is_running = False
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("Thread de monitoramento do SquadTKJailService parada")
        return {"success": True, "message": "Serviço parado com sucesso"}

    def parse_coordinates(self, coord_str: str) -> Optional[tuple]:
        """Faz o parsing das coordenadas do SCUM para float(x, y, z)"""
        if not coord_str:
            return None
            
        # Padrão {X=... Y=... Z=...}
        match = re.search(r'X=([-\d.]+)\s+Y=([-\d.]+)\s+Z=([-\d.]+)', coord_str, re.IGNORECASE)
        if match:
            return float(match.group(1)), float(match.group(2)), float(match.group(3))
            
        # Padrão simples separado por espaço
        parts = coord_str.replace('{', '').replace('}', '').split()
        nums = []
        for part in parts:
            clean = part
            if '=' in part:
                clean = part.split('=')[1]
            try:
                nums.append(float(clean))
            except ValueError:
                pass
        if len(nums) >= 3:
            return nums[0], nums[1], nums[2]
            
        return None

    def get_player_coords(self, steam_id: str) -> Optional[tuple]:
        """Busca as coordenadas do jogador na tabela players_online"""
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=False) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT coordinates_x, coordinates_y, coordinates_z 
                    FROM players_online 
                    WHERE steam_id = ? AND status = 'online'
                    """,
                    (steam_id,)
                )
                row = cursor.fetchone()
                if row and row[0] is not None and row[1] is not None and row[2] is not None:
                    return float(row[0]), float(row[1]), float(row[2])
        except Exception as e:
            self.logger.error(f"Erro ao buscar coordenadas online do jogador {steam_id}: {e}")
        return None

    def is_player_jailed(self, steam_id: str) -> bool:
        """Verifica se o jogador está preso no momento (status ativo)"""
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=False) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM prison_records WHERE steam_id = ? AND status = 'active'",
                    (steam_id,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            self.logger.error(f"Erro ao verificar se jogador {steam_id} está preso: {e}")
            return False

    def check_and_punish_tk(self, killer_steam_id: str, killer_name: str, victim_steam_id: str, victim_name: str):
        """Verifica se killer e victim pertencem ao mesmo squad e executa a punição se verdadeiro"""
        # Leitura em tempo real do estado habilitado
        tk_config = self.config.get("squad_tk_jail", {})
        enabled = tk_config.get("enabled", False)
        
        if not enabled:
            return
            
        if not killer_steam_id or not victim_steam_id or killer_steam_id == victim_steam_id:
            return
            
        try:
            squad_id = None
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=False) as conn:
                cursor = conn.cursor()
                # Verificar se ambos pertencem ao mesmo squad no último snapshot
                cursor.execute(
                    """
                    SELECT s1.squad_id 
                    FROM squad_member_snapshot s1
                    JOIN squad_member_snapshot s2 ON s1.squad_id = s2.squad_id
                    WHERE s1.player_steam_id = ? AND s2.player_steam_id = ?
                    LIMIT 1
                    """,
                    (killer_steam_id, victim_steam_id)
                )
                row = cursor.fetchone()
                if row:
                    squad_id = row[0]
            
            if squad_id is not None:
                self.logger.info(
                    f"Team Kill detectado! Killer: {killer_name} ({killer_steam_id}), Victim: {victim_name} ({victim_steam_id}) no squad {squad_id}. Iniciando punição."
                )
                self.jail_player(killer_steam_id, killer_name, squad_id, victim_name)
        except Exception as e:
            self.logger.error(f"Erro ao verificar Team Kill: {e}")

    def jail_player(self, steam_id: str, name: str, squad_id: int, victim_name: str):
        """Prende o jogador na cela pelo tempo configurado"""
        # Leituras em tempo real das configurações
        tk_config = self.config.get("squad_tk_jail", {})
        jail_duration_minutes = int(tk_config.get("jail_duration_minutes", 30))
        jail_coords_str = tk_config.get("jail_coordinates", "-271417.281 314246.875 84056.023")
        announcement_template = tk_config.get(
            "announcement_message",
            "{killer} matou o companheiro de squad {victim} e foi enviado para a prisão por {minutes} minutos!"
        )
        
        duration_seconds = jail_duration_minutes * 60
        now_iso = datetime.utcnow().isoformat()
        
        # Buscar coordenadas atuais antes de teleportar
        original_coords = self.get_player_coords(steam_id)
        orig_x, orig_y, orig_z = original_coords if original_coords else (None, None, None)
        
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO prison_records (steam_id, player_name, squad_id, jailed_at, remaining_seconds, last_tick_at, status, release_coords_x, release_coords_y, release_coords_z)
                    VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                    ON CONFLICT(steam_id) DO UPDATE SET
                        player_name = excluded.player_name,
                        squad_id = excluded.squad_id,
                        jailed_at = excluded.jailed_at,
                        remaining_seconds = excluded.remaining_seconds,
                        last_tick_at = excluded.last_tick_at,
                        status = 'active',
                        release_coords_x = excluded.release_coords_x,
                        release_coords_y = excluded.release_coords_y,
                        release_coords_z = excluded.release_coords_z
                    """,
                    (steam_id, name, squad_id, now_iso, duration_seconds, now_iso, orig_x, orig_y, orig_z)
                )
                conn.commit()
                
            self.logger.info(f"Jogador {name} ({steam_id}) registrado como preso por {jail_duration_minutes} minutos.")
            
            # Teleportar jogador para a sela
            coords = self.parse_coordinates(jail_coords_str)
            if coords:
                x, y, z = coords
                from core.rcon_queue_manager import RconQueueManager
                rcon_q = RconQueueManager.get_instance()
                
                # Comando de teletransporte prioritário
                rcon_q.enqueue_command(f'#teleport {x:.4f} {y:.4f} {z:.4f} {steam_id}', priority=20)
                
                # Anunciar prisão no chat
                try:
                    announcement_msg = announcement_template.format(
                        killer=name,
                        victim=victim_name,
                        minutes=jail_duration_minutes
                    )
                    self._announce_message(announcement_msg)
                except Exception as e:
                    self.logger.error(f"Erro ao anunciar prisão: {e}")
            else:
                self.logger.error(f"Coordenadas de prisão inválidas: {jail_coords_str}")
        except Exception as e:
            self.logger.error(f"Erro ao prender jogador {steam_id}: {e}")

    def release_player(self, steam_id: str):
        """Liberta o jogador e o teleporta de volta para a bandeira do squad ou local original"""
        try:
            player_name = "Jogador"
            squad_id = None
            orig_x, orig_y, orig_z = None, None, None
            
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=False) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT player_name, squad_id, release_coords_x, release_coords_y, release_coords_z FROM prison_records WHERE steam_id = ?",
                    (steam_id,)
                )
                row = cursor.fetchone()
                if row:
                    player_name = row[0]
                    squad_id = row[1]
                    orig_x = row[2]
                    orig_y = row[3]
                    orig_z = row[4]
            
            # Marcar como finalizado no banco
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE prison_records SET status = 'completed', remaining_seconds = 0 WHERE steam_id = ?",
                    (steam_id,)
                )
                conn.commit()
                
            self.logger.info(f"Jogador {player_name} ({steam_id}) libertado.")
            
            # Obter configurações de liberação em tempo real
            tk_config = self.config.get("squad_tk_jail", {})
            release_template = tk_config.get(
                "release_message",
                "{player} cumpriu sua pena e foi libertado!"
            )
            
            # Encontrar coordenadas da bandeira do squad
            flag_coords = None
            if squad_id is not None:
                try:
                    from app.extensions import get_services
                    svc = get_services()
                    if getattr(svc, "squad_sync_service", None):
                        flags_data = svc.squad_sync_service.get_all_flags_with_locations()
                        if flags_data.get("success"):
                            for flag in flags_data.get("flags", []):
                                if flag.get("squad_id") == squad_id:
                                    loc = flag.get("location", {})
                                    flag_coords = (loc.get("x"), loc.get("y"), loc.get("z"))
                                    break
                except Exception as e:
                    self.logger.error(f"Erro ao buscar bandeira do squad para soltura: {e}")
            
            # Se não encontrou bandeira, usar a coordenada original onde foi preso como fallback!
            if not flag_coords and orig_x is not None and orig_y is not None and orig_z is not None:
                self.logger.info(f"Bandeira do squad {squad_id} não encontrada. Usando coordenadas originais como fallback: {orig_x}, {orig_y}, {orig_z}")
                flag_coords = (orig_x, orig_y, orig_z)
                
            # Se ainda assim não encontrou, usar fallback 0 0 0
            if not flag_coords:
                self.logger.warn(f"Nenhuma coordenada encontrada para soltura. Usando fallback 0, 0, 0.")
                flag_coords = (0.0, 0.0, 0.0)
                
            x, y, z = flag_coords
            from core.rcon_queue_manager import RconQueueManager
            rcon_q = RconQueueManager.get_instance()
            
            # Teleportar para fora da prisão
            rcon_q.enqueue_command(f'#teleport {x:.4f} {y:.4f} {z:.4f} {steam_id}', priority=20)
            
            # Anunciar liberação
            try:
                release_msg = release_template.format(player=player_name)
                self._announce_message(release_msg)
            except Exception as e:
                self.logger.error(f"Erro ao anunciar soltura: {e}")
                
        except Exception as e:
            self.logger.error(f"Erro ao libertar jogador {steam_id}: {e}")

    def _announce_message(self, msg: str, priority: int = 15):
        """Envia mensagem no chat global/privado dependendo da configuração"""
        msg = msg.replace("\r", "").replace("\n", "").replace('"', "'").strip()
        
        from core.rcon_queue_manager import RconQueueManager
        rcon_q = RconQueueManager.get_instance()
        
        # Obter configurações de aviso em tempo real
        tk_config = self.config.get("squad_tk_jail", {})
        warning_color = tk_config.get("warning_color", "2")
        use_colors = tk_config.get("use_colors", True)
        
        # Obter jogadores online
        online_steam_ids = []
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=False) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT steam_id FROM players_online WHERE status = 'online'")
                online_steam_ids = [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as e:
            self.logger.error(f"Erro ao buscar jogadores online para anúncios de prisão: {e}")
            
        if online_steam_ids:
            chat_type = int(warning_color) if (warning_color.isdigit() and use_colors) else 2
            self.logger.info(f"Enviando aviso de prisão via SendChat ({chat_type}) para {len(online_steam_ids)} jogadores")
            for steam_id in online_steam_ids:
                rcon_q.enqueue_command(f'SendChat {chat_type} "{msg}" {steam_id}', delay_after=0.05, priority=priority)
        else:
            rcon_q.enqueue_command(f'Announce {msg}', priority=priority)

    def _monitor_loop(self):
        """Loop periódico (roda a cada 15 segundos) para descontar o tempo online e prevenir evasão"""
        self.logger.info("Loop de monitoramento GPS e tempo de prisão iniciado")
        
        while not self.stop_event.is_set():
            try:
                # Leituras em tempo real das configurações
                tk_config = self.config.get("squad_tk_jail", {})
                enabled = tk_config.get("enabled", False)
                jail_coords_str = tk_config.get("jail_coordinates", "-271417.281 314246.875 84056.023")
                jail_radius = float(tk_config.get("jail_radius_meters", 20.0))
                escape_template = tk_config.get(
                    "escape_message",
                    "{player}, você tentou escapar! Retornando para a cela."
                )
                warning_color = tk_config.get("warning_color", "2")
                use_colors = tk_config.get("use_colors", True)
                
                jail_coords = self.parse_coordinates(jail_coords_str)
                
                if not enabled:
                    self.stop_event.wait(15)
                    continue
                    
                if not jail_coords:
                    self.logger.error(f"Coordenadas de cela inválidas para monitoramento: {jail_coords_str}")
                    self.stop_event.wait(15)
                    continue
                    
                # Obter registros de presos ativos
                active_records = []
                try:
                    with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=False) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT steam_id, player_name, remaining_seconds, last_tick_at FROM prison_records WHERE status = 'active'"
                        )
                        active_records = [
                            {
                                "steam_id": row[0],
                                "player_name": row[1],
                                "remaining_seconds": row[2],
                                "last_tick_at": row[3]
                            }
                            for row in cursor.fetchall()
                        ]
                except Exception as e:
                    self.logger.error(f"Erro ao buscar presos ativos para monitoramento: {e}")
                    
                now = datetime.utcnow()
                now_iso = now.isoformat()
                
                for record in active_records:
                    steam_id = record["steam_id"]
                    player_name = record["player_name"]
                    remaining_seconds = record["remaining_seconds"]
                    last_tick_str = record["last_tick_at"]
                    
                    # 1. Verificar se está online no banco
                    is_online = False
                    try:
                        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=False) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "SELECT 1 FROM players_online WHERE steam_id = ? AND status = 'online'",
                                (steam_id,)
                            )
                            is_online = cursor.fetchone() is not None
                    except Exception as e:
                        self.logger.error(f"Erro ao verificar status online de {steam_id}: {e}")
                        
                    if not is_online:
                        # Pausar tempo: não decrementa remaining_seconds. Atualiza last_tick_at para pausar o delta.
                        try:
                            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "UPDATE prison_records SET last_tick_at = ? WHERE steam_id = ?",
                                    (now_iso, steam_id)
                                )
                                conn.commit()
                        except Exception as e:
                            self.logger.error(f"Erro ao pausar tempo de prisão para jogador offline {steam_id}: {e}")
                        continue
                        
                    # 2. Se está online, decrementar o tempo
                    last_tick = None
                    if last_tick_str:
                        try:
                            last_tick = datetime.fromisoformat(last_tick_str)
                        except:
                            last_tick = now
                    else:
                        last_tick = now
                        
                    elapsed_seconds = max(0, int((now - last_tick).total_seconds()))
                    new_remaining = max(0, remaining_seconds - elapsed_seconds)
                    
                    try:
                        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE prison_records SET remaining_seconds = ?, last_tick_at = ? WHERE steam_id = ?",
                                (new_remaining, now_iso, steam_id)
                            )
                            conn.commit()
                    except Exception as e:
                        self.logger.error(f"Erro ao atualizar tempo restante de {steam_id}: {e}")
                        continue
                        
                    # 3. Verificar liberação
                    if new_remaining <= 0:
                        self.release_player(steam_id)
                        continue
                        
                    # 4. Monitoramento GPS (fugas)
                    if jail_coords:
                        player_coords = self.get_player_coords(steam_id)
                        if player_coords:
                            px, py, pz = player_coords
                            jx, jy, jz = jail_coords
                            
                            # Distância em 3D
                            distance = math.sqrt((px - jx)**2 + (py - jy)**2 + (pz - jz)**2) / 100.0 # Converter cm para m
                            
                            if distance > jail_radius:
                                self.logger.warn(
                                    f"Jogador {player_name} ({steam_id}) fora da cela! Distância: {distance:.2f}m. Teleportando de volta."
                                )
                                
                                from core.rcon_queue_manager import RconQueueManager
                                rcon_q = RconQueueManager.get_instance()
                                
                                # Teleportar de volta
                                rcon_q.enqueue_command(f'#teleport {jx:.4f} {jy:.4f} {jz:.4f} {steam_id}', priority=20)
                                
                                # Enviar mensagem de escape privada ao jogador
                                try:
                                    escape_msg = escape_template.format(player=player_name)
                                    chat_type = int(warning_color) if (warning_color.isdigit() and use_colors) else 2
                                    rcon_q.enqueue_command(f'SendChat {chat_type} "{escape_msg}" {steam_id}', priority=18)
                                except Exception as e:
                                    self.logger.error(f"Erro ao avisar fuga do jogador {steam_id}: {e}")
                                    
            except Exception as e:
                self.logger.error(f"Erro no loop de monitoramento de prisão: {e}")
                
            # Dormir por 15 segundos
            self.stop_event.wait(15)
