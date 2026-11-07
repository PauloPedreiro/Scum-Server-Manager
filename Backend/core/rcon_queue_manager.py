import queue
import threading
import time
from typing import Any, Dict, Optional, Tuple
from concurrent.futures import Future

from utils.rcon_client import (
    get_rcon_client_from_config,
    is_rcon_tick_frozen,
    RconClient,
)

class RconQueueItem:
    def __init__(self, command: str, delay_after: float, priority: int, future: Future, origin: str = "SYSTEM"):
        self.command = command
        self.delay_after = delay_after
        self.priority = priority
        self.future = future
        self.origin = origin
        self.timestamp = time.time()

    def __lt__(self, other: 'RconQueueItem') -> bool:
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp

class RconQueueManager:
    _instance: Optional['RconQueueManager'] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, config_path: str = "data/config.json", logger: Optional[Any] = None) -> 'RconQueueManager':
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config_path=config_path, logger=logger)
            return cls._instance

    def __init__(self, config_path: str = "data/config.json", logger: Optional[Any] = None):
        self.config_path = config_path
        self.logger = logger
        self._queue = queue.PriorityQueue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._rcon_client: Optional[RconClient] = None
        self._client_lock = threading.Lock()
        self._circuit_open_until: float = 0.0
        self._consecutive_tick_failures: int = 0

    def is_circuit_open(self) -> Tuple[bool, float]:
        """Verifica se o disjuntor (circuit breaker) anti-crash do RCON está aberto."""
        now = time.time()
        if now < self._circuit_open_until:
            return True, self._circuit_open_until - now
        return False, 0.0

    def trip_circuit(self, cooldown: float = 15.0, reason: str = "") -> None:
        """Abre o disjuntor do RCON por `cooldown` segundos para aliviar a Game Thread."""
        now = time.time()
        new_until = now + max(1.0, float(cooldown))
        if new_until > self._circuit_open_until:
            self._circuit_open_until = new_until
        if self.logger:
            self.logger.warn(
                f"RconQueueManager: Circuit Breaker ativado por {cooldown:.1f}s — motivo: {reason}"
            )

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._process_queue, daemon=True, name="RconQueueThread")
            self._thread.start()
            if self.logger:
                self.logger.info("RconQueueManager started")
            else:
                print("RconQueueManager started")

    def stop(self):
        with self._lock:
            if not self._running:
                return
            self._running = False
        
        # Add a dummy command to wake up the queue thread if it is waiting
        self.enqueue_command("ListPlayers", delay_after=0.0, priority=100)
        
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
            
        with self._client_lock:
            if self._rcon_client:
                try:
                    self._rcon_client.close()
                except Exception:
                    pass
                self._rcon_client = None
        if self.logger:
            self.logger.info("RconQueueManager stopped")
        else:
            print("RconQueueManager stopped")

    def enqueue_command(self, command: str, delay_after: float = 0.1, priority: int = 10, origin: str = "SYSTEM") -> Future:
        """
        Envia um comando RCON para a fila.
        Retorna um Future que será resolvido com a resposta do servidor (str).
        
        Prioridades sugeridas:
        - 1: Comandos administrativos em tempo real (teleporte imediato, comandos manuais)
        - 5: Entregas de itens da loja
        - 10: Eventos (teleportes em lote, comandos iniciais)
        - 20: Sincronizações periódicas automáticas
        """
        future = Future()
        item = RconQueueItem(command, delay_after, priority, future, origin=origin)
        self._queue.put(item)
        
        # Garante que a thread está rodando
        if not self._running:
            self.start()
            
        return future

    def execute_command_sync(self, command: str, delay_after: float = 0.1, priority: int = 10, timeout: float = 30.0, origin: str = "SYSTEM") -> str:
        """
        Envia um comando RCON e aguarda de forma síncrona pelo seu resultado.
        """
        future = self.enqueue_command(command, delay_after=delay_after, priority=priority, origin=origin)
        try:
            return future.result(timeout=timeout)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error executing command sync '{command}': {e}")
            raise

    def _process_queue(self):
        while self._running:
            try:
                item: RconQueueItem = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if not self._running:
                item.future.cancel()
                self._queue.task_done()
                break

            response = ""
            skip_delay = False
            try:
                cmd_lower = item.command.strip().lower()
                is_lp = cmd_lower == "listplayers"
                cb_open, cb_rem = self.is_circuit_open()
                if cb_open and cmd_lower.startswith(("spawnitem", "spawnvehicle", "sendchat")):
                    skip_delay = True
                    item.future.set_result(
                        f"erro: circuit_breaker_open ({cb_rem:.1f}s restantes - protegendo tick do servidor)"
                    )
                    continue

                with self._client_lock:
                    if not self._rcon_client:
                        self._rcon_client = get_rcon_client_from_config(self.config_path)
                    
                    if not self._rcon_client:
                        raise Exception("RCON configuration disabled or invalid")
                    
                    # Reconnect if socket was closed or doesn't exist
                    if self._rcon_client._sock is None:
                        self._rcon_client.connect()
                    
                    response = self._rcon_client.send_command(item.command, delay_after=0.0, origin=item.origin)

                # Verificar se o tick do servidor congelou
                tick_frozen = (
                    ("sem resposta" in response.lower() or "tick do jogo" in response.lower())
                    if is_lp
                    else is_rcon_tick_frozen(response)
                )
                if tick_frozen:
                    self._consecutive_tick_failures += 1
                    cooldown = min(45.0, 15.0 * self._consecutive_tick_failures)
                    self.trip_circuit(cooldown=cooldown, reason=response or "RCON socket timeout")
                else:
                    self._consecutive_tick_failures = 0
                    self._circuit_open_until = 0.0

                # Resolve future outside the lock
                item.future.set_result(response)
            except Exception as e:
                # Se falhar, fecha a conexão para tentar reconectar na próxima vez
                with self._client_lock:
                    if self._rcon_client:
                        try:
                            self._rcon_client.close()
                        except Exception:
                            pass
                
                if self.logger:
                    self.logger.error(f"Error executing RCON command '{item.command}': {e}")
                
                item.future.set_exception(e)
            finally:
                self._queue.task_done()
                # Aplica o delay após a execução, liberando o lock e evitando stress no RCON
                if not skip_delay and item.delay_after > 0:
                    time.sleep(item.delay_after)
