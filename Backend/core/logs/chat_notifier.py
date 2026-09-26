#!/usr/bin/env python3
"""
Notificador de chat do SCUM para Discord
Envia mensagens de chat global para Discord via webhook
"""

import time
import requests
import threading
import queue
from typing import Dict, Optional
from utils.logger import StructuredLogger


class ChatNotifier:
    """Notificador de mensagens de chat para Discord"""
    
    def __init__(self, webhook_config: Dict, logger: StructuredLogger = None):
        """
        Inicializar notificador de chat
        
        Args:
            webhook_config: Configuração dos webhooks Discord
            logger: Logger estruturado
        """
        self.logger = logger or StructuredLogger()
        self.webhook_config = webhook_config
        
        # Configurações
        self.webhook_name = "chat_in_game"
        # Discord permite 30 requisições por minuto = 1 requisição a cada 2 segundos
        # Usar 2.1s para garantir margem de segurança
        self.rate_limit_delay = 2.1  # 2.1s entre mensagens (respeita limite do Discord)
        
        # Rate limit do Discord (429) - controlado globalmente para a fila
        self.rate_limited_until = 0  # Timestamp até quando estamos rate limited
        self.rate_limit_lock = threading.Lock()  # Lock para thread-safety
        
        # Fila de mensagens com limite máximo para evitar consumo excessivo de memória
        # Limite de 1000 mensagens (se atingir, novas mensagens são rejeitadas)
        self.max_queue_size = 1000
        self.message_queue = queue.Queue(maxsize=self.max_queue_size)
        
        # Controle de worker
        self.worker_thread = None
        self.stop_worker = False
        self.worker_heartbeat = 0  # Timestamp do último heartbeat do worker
        self.worker_lock = threading.Lock()  # Lock para controlar worker
        
        # Configurações de retry e TTL
        self.max_retries_per_message = 3  # Máximo de tentativas por mensagem
        self.message_ttl = 300  # Time To Live: 5 minutos (mensagens antigas são descartadas)
        
        # Estatísticas
        self.stats = {
            'messages_sent': 0,
            'messages_queued': 0,
            'messages_dropped': 0,  # Mensagens descartadas (fila cheia, TTL expirado)
            'messages_failed': 0,  # Mensagens que falharam após max_retries
            'errors': 0,
            'last_send': None,
            'queue_full_count': 0,  # Quantas vezes a fila ficou cheia
            'worker_restarts': 0  # Quantas vezes o worker foi reiniciado
        }
        self.stats_lock = threading.Lock()
        
        # Iniciar worker thread
        self._start_worker()
        
        self.logger.info("ChatNotifier inicializado com sistema de fila")
    
    def get_webhook_url(self) -> Optional[str]:
        """
        Obter URL do webhook do chat
        
        Returns:
            URL do webhook ou None se não configurado
        """
        return self.webhook_config.get(self.webhook_name)
    
    def format_chat_message(self, player_name: str, message: str, channel: Optional[str] = None) -> str:
        """
        Formatar mensagem de chat para Discord
        
        Args:
            player_name: Nome do jogador
            message: Mensagem do chat
            
        Returns:
            Mensagem formatada
        """
        channel_norm = (channel or "").strip().lower()
        emoji = "💬"
        if channel_norm == "global":
            emoji = ":mega:"
        elif channel_norm == "local":
            emoji = "📍"
        elif channel_norm == "squad":
            emoji = ":military_helmet:"
        elif channel_norm == "admin":
            emoji = ":man_detective::skin-tone-1:"

        return f"{emoji} {player_name}: {message}"
    
    def _start_worker(self):
        """Iniciar thread worker para processar fila de mensagens"""
        with self.worker_lock:
            if self.worker_thread is None or not self.worker_thread.is_alive():
                self.stop_worker = False
                self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="ChatNotifierWorker")
                self.worker_thread.start()
                self.worker_heartbeat = time.time()
                with self.stats_lock:
                    self.stats['worker_restarts'] += 1
                self.logger.debug("Worker thread iniciado para processar fila de mensagens")
    
    def _worker_loop(self):
        """Loop do worker que processa mensagens da fila"""
        last_send_time = 0
        
        while not self.stop_worker:
            try:
                # Atualizar heartbeat
                self.worker_heartbeat = time.time()
                
                # Obter mensagem da fila (com timeout para verificar stop_worker periodicamente)
                try:
                    message_data = self.message_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                player_name = message_data.get('player_name')
                message = message_data.get('message')
                channel = message_data.get('channel')
                callback = message_data.get('callback')
                retry_count = message_data.get('retry_count', 0)
                timestamp = message_data.get('timestamp', time.time())
                
                # Verificar TTL (Time To Live) - descartar mensagens muito antigas
                current_time = time.time()
                message_age = current_time - timestamp
                if message_age > self.message_ttl:
                    with self.stats_lock:
                        self.stats['messages_dropped'] += 1
                    self.logger.debug(
                        f"Mensagem descartada por TTL expirado ({message_age:.1f}s > {self.message_ttl}s): "
                        f"{player_name}: {message[:50]}..."
                    )
                    self.message_queue.task_done()
                    continue
                
                # Verificar retry limit - descartar mensagens que excederam tentativas
                if retry_count >= self.max_retries_per_message:
                    with self.stats_lock:
                        self.stats['messages_failed'] += 1
                        self.stats['errors'] += 1
                    self.logger.warn(
                        f"Mensagem descartada após {retry_count} tentativas: "
                        f"{player_name}: {message[:50]}..."
                    )
                    self.message_queue.task_done()
                    continue
                
                # Verificar se estamos em rate limit antes de tentar enviar
                with self.rate_limit_lock:
                    if self.rate_limited_until > current_time:
                        # Estamos em rate limit, aguardar até liberar
                        wait_time = self.rate_limited_until - current_time
                        if wait_time > 0:
                            self.logger.debug(f"Aguardando {wait_time:.2f}s até rate limit ser liberado...")
                            # Atualizar heartbeat durante espera
                            start_wait = time.time()
                            while time.time() - start_wait < wait_time and not self.stop_worker:
                                self.worker_heartbeat = time.time()
                                time.sleep(min(1.0, wait_time - (time.time() - start_wait)))
                            if self.stop_worker:
                                # Recolocar mensagem na fila se estivermos parando
                                self.message_queue.put_nowait(message_data)
                                break
                            current_time = time.time()
                
                # Verificar rate limiting interno (delay entre mensagens)
                time_since_last = current_time - last_send_time
                if time_since_last < self.rate_limit_delay:
                    sleep_time = self.rate_limit_delay - time_since_last
                    time.sleep(sleep_time)
                    current_time = time.time()
                
                # Enviar mensagem
                success = self._send_message(player_name, message, channel, retry_count)
                
                # Atualizar timestamp da última mensagem enviada
                if success:
                    last_send_time = time.time()
                    self.worker_heartbeat = time.time()
                
                # Chamar callback se fornecido
                if callback:
                    try:
                        callback(success)
                    except Exception as e:
                        self.logger.error(f"Erro ao chamar callback: {e}")
                
                # Marcar tarefa como concluída
                self.message_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Erro no worker loop: {e}", exc_info=True)
                # Worker não deve parar por um erro - continuar processando
                time.sleep(1.0)  # Aguardar um pouco antes de continuar
                self.worker_heartbeat = time.time()
    
    def _send_message(self, player_name: str, message: str, channel: Optional[str] = None, retry_count: int = 0) -> bool:
        """
        Enviar mensagem única para Discord (método interno usado pelo worker)
        
        Args:
            player_name: Nome do jogador
            message: Mensagem do chat
            retry_count: Número de tentativas já realizadas
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        import json
        
        try:
            # Obter URL do webhook
            webhook_url = self.get_webhook_url()
            if not webhook_url:
                self.logger.error("Webhook de chat não configurado")
                with self.stats_lock:
                    self.stats['errors'] += 1
                return False
            
            # Formatar mensagem
            formatted_message = self.format_chat_message(player_name, message, channel=channel)
            
            # Preparar payload
            payload = {
                "content": formatted_message
            }
            
            # Enviar para Discord
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10
            )
            
            # Tratar resposta
            if response.status_code in (200, 204):
                # Sucesso - limpar rate limit
                with self.rate_limit_lock:
                    self.rate_limited_until = 0
                
                with self.stats_lock:
                    self.stats['messages_sent'] += 1
                    self.stats['last_send'] = time.time()
                
                self.logger.debug(f"Mensagem enviada para Discord: {player_name}: {message[:50]}...")
                return True
            
            elif response.status_code == 429:
                # Rate limited - extrair retry_after e agendar liberação
                try:
                    error_data = response.json() if response.text else {}
                    retry_after = error_data.get('retry_after', 1.0)
                    
                    # Garantir que retry_after é um número e tem valor mínimo
                    try:
                        retry_after = float(retry_after)
                        if retry_after < 0:
                            retry_after = 1.0
                    except (ValueError, TypeError):
                        retry_after = 1.0
                    
                    # Atualizar timestamp de rate limit (com margem de segurança de 0.5s)
                    with self.rate_limit_lock:
                        self.rate_limited_until = time.time() + retry_after + 0.5
                    
                    # Log apenas ocasionalmente para evitar spam
                    self.logger.debug(
                        f"Rate limit detectado. Aguardando {retry_after:.2f}s antes de continuar fila. "
                        f"Mensagem (tentativa {retry_count + 1}): {player_name}: {message[:50]}..."
                    )
                    
                    # Recolocar mensagem na fila para tentar novamente após o rate limit
                    # Incrementar contador de retry e preservar timestamp original
                    try:
                        self.message_queue.put_nowait({
                            'player_name': player_name,
                            'message': message,
                            'channel': channel,
                            'retry_count': retry_count + 1,
                            'timestamp': time.time()  # Resetar timestamp para evitar TTL durante rate limit
                        })
                    except queue.Full:
                        # Se a fila estiver cheia após rate limit, mensagem será descartada
                        with self.stats_lock:
                            self.stats['messages_dropped'] += 1
                            self.stats['errors'] += 1
                        self.logger.error(
                            f"Fila cheia ao recolocar mensagem após rate limit. Mensagem descartada: "
                            f"{player_name}: {message[:50]}..."
                        )
                    
                    return False
                    
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    # Em caso de erro ao processar resposta de rate limit, usar delay padrão
                    with self.rate_limit_lock:
                        self.rate_limited_until = time.time() + 1.0
                    
                    with self.stats_lock:
                        self.stats['errors'] += 1
                    
                    self.logger.error(f"Erro ao processar resposta de rate limit: {e}")
                    return False
            
            else:
                # Outro erro
                with self.stats_lock:
                    self.stats['errors'] += 1
                
                error_text = response.text[:200] if response.text else "Sem resposta"
                self.logger.error(
                    f"Erro ao enviar mensagem para Discord: {response.status_code} - {error_text}. "
                    f"Mensagem: {player_name}: {message[:50]}..."
                )
                return False
        
        except requests.exceptions.Timeout:
            with self.stats_lock:
                self.stats['errors'] += 1
            self.logger.error(f"Timeout ao enviar mensagem para Discord: {player_name}: {message[:50]}...")
            return False
        
        except requests.exceptions.RequestException as e:
            with self.stats_lock:
                self.stats['errors'] += 1
            self.logger.error(f"Erro de rede ao enviar mensagem para Discord: {e}. Mensagem: {player_name}: {message[:50]}...")
            return False
        
        except Exception as e:
            with self.stats_lock:
                self.stats['errors'] += 1
            self.logger.error(f"Erro inesperado ao enviar mensagem para Discord: {e}. Mensagem: {player_name}: {message[:50]}...")
            return False
    
    def send_chat_message(self, player_name: str, message: str, channel: Optional[str] = None) -> bool:
        """
        Adicionar mensagem à fila para envio ao Discord
        
        Args:
            player_name: Nome do jogador
            message: Mensagem do chat
            
        Returns:
            True se adicionado à fila com sucesso, False caso contrário
        """
        try:
            # Verificar se fila está cheia
            if self.message_queue.full():
                with self.stats_lock:
                    self.stats['messages_dropped'] += 1
                    self.stats['queue_full_count'] += 1
                self.logger.warn(
                    f"Fila de mensagens cheia ({self.max_queue_size}). Mensagem descartada: "
                    f"{player_name}: {message[:50]}..."
                )
                return False
            
            # Adicionar à fila com metadados
            try:
                self.message_queue.put_nowait({
                    'player_name': player_name,
                    'message': message,
                    'channel': channel,
                    'retry_count': 0,
                    'timestamp': time.time()
                })
            except queue.Full:
                # Race condition: fila ficou cheia entre verificação e inserção
                with self.stats_lock:
                    self.stats['messages_dropped'] += 1
                    self.stats['queue_full_count'] += 1
                self.logger.warn(
                    f"Fila de mensagens cheia durante inserção. Mensagem descartada: "
                    f"{player_name}: {message[:50]}..."
                )
                return False
            
            with self.stats_lock:
                self.stats['messages_queued'] += 1
            
            # Garantir que worker está rodando
            # Verificar também se worker não travou (heartbeat > 60s sem atualização)
            current_time = time.time()
            worker_stuck = (current_time - self.worker_heartbeat) > 60
            
            if (self.worker_thread is None or 
                not self.worker_thread.is_alive() or 
                worker_stuck):
                if worker_stuck:
                    self.logger.warn("Worker thread travado detectado, reiniciando...")
                self._start_worker()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao adicionar mensagem à fila: {e}")
            with self.stats_lock:
                self.stats['errors'] += 1
            return False
    
    def send_test_message(self) -> bool:
        """
        Enviar mensagem de teste para Discord
        
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        return self.send_chat_message("Sistema", "Teste de conexão do chat - sistema funcionando!", channel="Global")
    
    def get_stats(self) -> Dict:
        """
        Obter estatísticas do notificador
        
        Returns:
            Estatísticas atuais
        """
        with self.stats_lock:
            stats_copy = self.stats.copy()
        
        with self.rate_limit_lock:
            is_rate_limited = self.rate_limited_until > time.time()
            rate_limit_until = self.rate_limited_until if is_rate_limited else None
        
        current_time = time.time()
        worker_age = current_time - self.worker_heartbeat if self.worker_heartbeat > 0 else 0
        
        return {
            **stats_copy,
            'webhook_configured': self.get_webhook_url() is not None,
            'webhook_name': self.webhook_name,
            'rate_limit_delay': self.rate_limit_delay,
            'queue_size': self.message_queue.qsize(),
            'queue_max_size': self.max_queue_size,
            'queue_usage_percent': (self.message_queue.qsize() / self.max_queue_size * 100) if self.max_queue_size > 0 else 0,
            'worker_running': self.worker_thread is not None and self.worker_thread.is_alive(),
            'worker_heartbeat_age': worker_age,
            'worker_stuck': worker_age > 60,
            'is_rate_limited': is_rate_limited,
            'rate_limit_until': rate_limit_until,
            'max_retries_per_message': self.max_retries_per_message,
            'message_ttl': self.message_ttl
        }
    
    def shutdown(self):
        """Parar worker thread e aguardar conclusão da fila"""
        self.logger.info("Parando worker thread do ChatNotifier...")
        self.stop_worker = True
        
        # Aguardar até 5 segundos para a fila ser processada
        try:
            self.message_queue.join(timeout=5.0)
        except:
            pass
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        
        self.logger.info("Worker thread do ChatNotifier parado")
    
    def reset_stats(self):
        """Resetar estatísticas"""
        self.stats = {
            'messages_sent': 0,
            'errors': 0,
            'last_send': None
        }
        self.logger.info("Estatísticas do ChatNotifier resetadas")
