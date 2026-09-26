import time
import threading
from typing import Dict, Any, List, Optional
from utils.logger import StructuredLogger
from utils.restart_guard import is_restart_active
from utils.sanitize import sanitize_rcon_command_coords
from core.rcon_queue_manager import RconQueueManager
from core.scheduler.rcon_routine_manager import RconRoutineManager

class RconRoutineScheduler(threading.Thread):
    """
    Serviço de background que monitora e agenda a execução de rotinas RCON
    periódicas registradas no sistema.
    """
    def __init__(self, routine_manager: RconRoutineManager, rcon_queue_manager: RconQueueManager, logger: Optional[Any] = None, db_manager=None):
        super().__init__(daemon=True, name="RconRoutineSchedulerThread")
        self.routine_manager = routine_manager
        self.rcon_queue_manager = rcon_queue_manager
        self.logger = logger or StructuredLogger()
        self.db_manager = db_manager  # Usado para buscar jogadores online (mesmo padrão do Kill Feed)
        self._running = False
        self._stop_event = threading.Event()

    def start(self):
        """Inicia a thread do agendador."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        super().start()
        self.logger.info("RconRoutineScheduler iniciado")

    def stop(self):
        """Para a thread do agendador de forma graciosa."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        self.logger.info("RconRoutineScheduler parando...")
        self.join(timeout=5.0)

    def run(self):
        """Loop principal do agendador (roda a cada 60 segundos)."""
        # Aguarda 30 segundos no startup para evitar colidir com inicialização crítica do RCON
        self._stop_event.wait(30.0)
        
        while self._running and not self._stop_event.is_set():
            try:
                self._check_and_run_routines()
            except Exception as e:
                self.logger.error(f"Erro no processamento de rotinas RCON: {e}")
            
            # Aguarda 60 segundos antes do próximo ciclo de checagem
            self._stop_event.wait(60.0)

    def _get_online_steam_ids(self) -> List[str]:
        """Busca SteamIDs dos jogadores online da tabela players_online (mesmo padrão do Kill Feed)."""
        if not self.db_manager:
            return []
        try:
            from core.database.connector import DatabaseConnector
            with DatabaseConnector.get_connection(self.db_manager.db_path, write_mode=False) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT steam_id FROM players_online WHERE status = 'online'")
                return [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as e:
            self.logger.error(f"Erro ao buscar jogadores online para aviso prévio RCON: {e}")
            return []

    def _send_warning(self, routine: Dict[str, Any], warning_message: str, warning_minutes_before: int, now: float):
        """Envia a mensagem de aviso prévio para todos os jogadores via RCON do SCUM.
        
        Usa o mesmo padrão do Kill Feed:
        - Se há db_manager e jogadores online: SendChat <tipo> "<mensagem>" <steamid> (suporta cor via tipo)
        - Fallback: Announce <mensagem> (broadcast sem cor)
        """
        formatted_msg = warning_message.replace("{minutes}", str(warning_minutes_before))
        
        # Sanitização igual ao Kill Feed (evita injeção de comandos RCON)
        formatted_msg = formatted_msg.replace("\r", "").replace("\n", "").replace('"', "'")
        formatted_msg = "".join(ch for ch in formatted_msg if ord(ch) >= 32).strip()

        # Tipo de chat: 7 = vermelho (erro/aviso), conforme USAGE.md
        # Pode ser sobrescrito via warning_color se armazenar um número válido
        warning_color = routine.get("warning_color", "").strip()
        try:
            chat_type = int(warning_color) if warning_color.isdigit() else 7
        except (ValueError, AttributeError):
            chat_type = 7  # Padrão: vermelho
        
        routine_name = routine.get('name')
        online_steam_ids = self._get_online_steam_ids()
        
        if online_steam_ids:
            self.logger.info(f"Disparando aviso prévio RCON para '{routine_name}' via SendChat tipo {chat_type} para {len(online_steam_ids)} jogadores")
            for steam_id in online_steam_ids:
                self.rcon_queue_manager.enqueue_command(
                    command=f'SendChat {chat_type} "{formatted_msg}" {steam_id}',
                    delay_after=0.05,
                    priority=10
                )
        else:
            # Fallback: Announce broadcast (sem cor, mas chega a todos)
            self.logger.info(f"Disparando aviso prévio RCON para '{routine_name}' via Announce (nenhum jogador online encontrado no banco)")
            self.rcon_queue_manager.enqueue_command(
                command=f"Announce {formatted_msg}",
                delay_after=0.5,
                priority=10
            )

        self.routine_manager.update_last_warning_run(routine["id"], now)


    def _check_and_run_routines(self):
        """Varre as rotinas cadastradas e dispara aquelas que estão no horário."""
        # Travas de segurança: se o servidor estiver reiniciando, não dispara nada
        if is_restart_active():
            self.logger.info("SCUM Server está reiniciando (Restart Guard ativo). Pulando execução de rotinas RCON.")
            return

        routines = self.routine_manager.get_routines()
        now = time.time()
        
        for routine in routines:
            if not routine.get("enabled", False):
                continue
            
            commands = routine.get("commands", [])
            if not commands:
                continue

            interval_minutes = int(routine.get("interval_minutes", 60))
            last_run = routine.get("last_run")
            warning_enabled = routine.get("warning_enabled", False)
            warning_message = routine.get("warning_message", "")
            
            warning_minutes_before = int(routine.get("warning_minutes_before", 5))
            # Garante que o aviso é disparado pelo menos 1 minuto antes do intervalo completo
            warning_minutes_before = min(warning_minutes_before, max(1, interval_minutes - 1))
            warning_trigger_seconds = (interval_minutes - warning_minutes_before) * 60

            # Caso A: A rotina nunca rodou antes (last_run é None)
            if last_run is None:
                if warning_enabled and warning_message:
                    # Envia o aviso prévio primeiro e agenda a execução da rotina principal
                    # para daqui a `warning_minutes_before` minutos.
                    self._send_warning(routine, warning_message, warning_minutes_before, now)
                    adjusted_last_run = now - warning_trigger_seconds
                    self.routine_manager.update_last_run(routine["id"], adjusted_last_run)
                else:
                    # Sem aviso prévio, roda a rotina principal imediatamente
                    self.logger.info(f"Disparando rotina periódica RCON '{routine.get('name')}' ({len(commands)} comandos) pela primeira vez...")
                    self.execute_routine(routine)
                    self.routine_manager.update_last_run(routine["id"], now)
                continue

            # Caso B: last_run já está registrado
            elapsed_seconds = now - float(last_run)

            # 1. A rotina principal atingiu (ou passou) o tempo programado para execução
            if elapsed_seconds >= (interval_minutes * 60):
                if warning_enabled and warning_message:
                    last_warning_run = routine.get("last_warning_run")
                    has_sent_warning_this_cycle = False
                    if last_warning_run is not None:
                        has_sent_warning_this_cycle = float(last_warning_run) > float(last_run)

                    if not has_sent_warning_this_cycle:
                        # O tempo estourou (ex: app ficou offline ou atraso do agendador), mas
                        # o aviso prévio deste ciclo ainda não foi enviado. 
                        # Enviamos o aviso prévio agora e adiamos a rotina principal para dar tempo dos jogadores lerem.
                        self._send_warning(routine, warning_message, warning_minutes_before, now)
                        adjusted_last_run = now - warning_trigger_seconds
                        self.routine_manager.update_last_run(routine["id"], adjusted_last_run)
                        continue

                # Se o aviso prévio já foi enviado ou não está habilitado, executa a rotina principal
                self.logger.info(f"Disparando rotina periódica RCON '{routine.get('name')}' ({len(commands)} comandos)...")
                self.execute_routine(routine)
                self.routine_manager.update_last_run(routine["id"], now)

            # 2. Ainda não atingiu o tempo da rotina principal. Verificamos se está no momento do aviso prévio.
            elif warning_enabled and warning_message:
                last_warning_run = routine.get("last_warning_run")
                has_sent_warning_this_cycle = False
                if last_warning_run is not None:
                    has_sent_warning_this_cycle = float(last_warning_run) > float(last_run)

                if elapsed_seconds >= warning_trigger_seconds and not has_sent_warning_this_cycle:
                    self._send_warning(routine, warning_message, warning_minutes_before, now)

    def execute_routine(self, routine: Dict[str, Any]):
        """Enfileira todos os comandos da rotina na fila RconQueueManager."""
        commands = routine.get("commands", [])
        if not commands:
            return
            
        routine_name = routine.get("name", "Sem Nome")
        self.logger.info(f"Enfileirando {len(commands)} comandos da rotina '{routine_name}' no RconQueueManager")
        
        for cmd in commands:
            if not cmd.strip():
                continue
            
            # Sanitiza coordenadas antes de enfileirar
            sanitized_cmd = sanitize_rcon_command_coords(cmd.strip())
            
            # Enfileira com prioridade de background (20) e delay de 2 segundos
            # pós-execução de cada comando para proteger o buffer RCON do jogo
            self.rcon_queue_manager.enqueue_command(
                command=sanitized_cmd,
                delay_after=2.0,
                priority=20
            )
