"""
Sistema de Agendamento de Reinicializações
Gerencia reinicializações automáticas do servidor SCUM em horários específicos
"""

import threading
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from utils.logger import StructuredLogger


class RestartScheduler:
    def __init__(
        self,
        config: Dict[str, Any],
        server_manager,
        notification_manager=None,
        logger: StructuredLogger = None,
        gestao_messages_service=None,
        discord_webhook=None,
    ):
        self.config = config
        self.server_manager = server_manager
        self.notification_manager = notification_manager
        self.logger = logger or StructuredLogger()
        self.gestao_messages_service = gestao_messages_service
        self.discord_webhook = discord_webhook

        # Configurações do agendador
        self.scheduler_config = config.get("scheduler", {})
        self.enabled = self.scheduler_config.get("enabled", True)
        self.restart_times = self.scheduler_config.get("restart_times", [])
        self.notification_minutes = self.scheduler_config.get(
            "notification_minutes", [5, 1]
        )  # Notificar 5min e 1min antes
        self.auto_start = self.scheduler_config.get("auto_start", True)
        self._scheduler = schedule.Scheduler()

        if self.notification_manager and hasattr(
            self.notification_manager, "update_scheduler_times"
        ):
            self.notification_manager.update_scheduler_times(self.restart_times)

        # Estado do agendador
        self.is_running = False
        self.scheduler_thread = None
        self.stop_event = threading.Event()
        
        # Lock para prevenir race conditions ao agendar jobs
        # IMPORTANTE: Usar RLock (reentrante) para permitir chamadas aninhadas
        # (start() -> _schedule_restart() ambos usam o mesmo lock)
        self._scheduling_lock = threading.RLock()
        
        # Health check: última verificação de integridade
        self._last_health_check = None
        self._health_check_interval = 3600  # Verificar a cada 1 hora

        # Callbacks para notificações
        self.notification_callbacks: List[Callable] = []

        # Logs de agendamento
        self.schedule_logs = []

        # Controle de notificações de restart
        self.last_restart_notifications = None
        
        # Configurações de alertas de restart
        self.alert_config = self.scheduler_config.get("alerts", {})
        self.alert_enabled = self.alert_config.get("enabled", True)
        self.alert_max_time_seconds = self.alert_config.get("max_time_seconds", 240)  # 4 minutos padrão
        self.alert_on_failure = self.alert_config.get("alert_on_failure", True)  # Alertar sempre que falhar
        self.alert_on_timeout = self.alert_config.get("alert_on_timeout", True)  # Alertar se demorar muito
        
        # Contador de falhas consecutivas (para futuro uso)
        self.consecutive_failures = 0

        self.logger.info(
            "RestartScheduler inicializado",
            {
                "notification_manager_available": notification_manager is not None,
                "gestao_messages_service_available": gestao_messages_service
                is not None,
            },
        )

    def add_notification_callback(self, callback: Callable):
        """Adicionar callback para notificações"""
        self.notification_callbacks.append(callback)
        self.logger.info(f"Callback de notificação adicionado: {callback.__name__}")

    def _notify(self, message: str, data: Dict[str, Any] = None):
        """Enviar notificação para todos os callbacks"""
        for callback in self.notification_callbacks:
            try:
                callback(message, data)
            except Exception as e:
                self.logger.error(f"Erro no callback de notificação: {e}")

    def _create_restart_notifications(
        self, restart_time: str, restart_datetime: datetime
    ):
        """Criar notificações de restart in-game"""
        if not self.notification_manager:
            self.logger.warn(
                "NotificationManager não disponível para notificações de restart"
            )
            return

        try:
            # Verificar se já foram criadas notificações para este restart
            if self.last_restart_notifications == restart_time:
                self.logger.debug(
                    "Notificações de restart já criadas para horário",
                    {"restart_time": restart_time},
                )
                return

            # Calcular tempo até restart
            now = datetime.now()
            time_until_restart = (restart_datetime - now).total_seconds()

            # Criar notificações padrão sempre (sem mensagem do Gestão ainda)
            # A mensagem do Gestão será adicionada pelo job agendado para 15 minutos antes
            # Não consultar Gestão aqui - será feito pelo job agendado
            gestao_message = None

            # DELEGAR para NotificationManager (cria notificações padrão)
            result = self.notification_manager.create_restart_notifications(
                restart_time, restart_datetime, gestao_message=gestao_message
            )

            if result["success"]:
                self.last_restart_notifications = restart_time
                self.logger.info(
                    "Notificações de restart padrão criadas",
                    {
                        "restart_time": restart_time,
                        "notifications_count": result.get("count", 0),
                        "time_until_restart": f"{time_until_restart/60:.1f} minutos",
                        "note": "Mensagem do Gestão será adicionada 15 minutos antes do restart",
                    },
                )
            else:
                self.logger.error(
                    "Falha ao criar notificações de restart",
                    {
                        "restart_time": restart_time,
                        "error": result.get("reason", "Erro desconhecido"),
                    },
                )

        except Exception as e:
            self.logger.error(
                "Erro ao criar notificações de restart",
                {"restart_time": restart_time, "error": str(e)},
            )

    def _clear_restart_notifications(self):
        """Limpar notificações de restart"""
        if not self.notification_manager:
            return

        try:
            result = self.notification_manager.clear_restart_notifications()

            if result["success"]:
                self.last_restart_notifications = None
                self.logger.info("Notificações de restart limpas")
            else:
                self.logger.error(
                    "Falha ao limpar notificações de restart",
                    {"error": result.get("error", "Erro desconhecido")},
                )

        except Exception as e:
            self.logger.error(
                "Erro ao limpar notificações de restart", {"error": str(e)}
            )
    
    def _send_restart_alert(self, alert_type: str, result: Dict[str, Any]):
        """
        Send restart alert to Discord (webhook log-ssm)
        
        Args:
            alert_type: Alert type ('failure' or 'timeout')
            result: Restart result with details
        """
        if not self.discord_webhook:
            return
        
        try:
            elapsed = result.get("elapsed_seconds", 0)
            status = result.get("status", "unknown")
            message = result.get("message", "No details")
            retry_count = result.get("retry_count", 0)
            
            if alert_type == "failure":
                # Alerta de falha
                title = "🚨 Scheduled Restart Failed"
                color = 0xFF0000  # Vermelho
                description = f"The scheduled restart failed after {retry_count} attempt(s)"
                
                fields = [
                    {"name": "❌ Status", "value": status, "inline": True},
                    {"name": "⏱️ Time", "value": f"{elapsed:.1f}s", "inline": True},
                    {"name": "🔄 Attempts", "value": str(retry_count), "inline": True},
                    {"name": "📝 Details", "value": message[:500], "inline": False},  # Limitar tamanho
                ]
                
            elif alert_type == "timeout":
                # Alerta de timeout (demorou muito)
                title = "⚠️ Restart Took Too Long"
                color = 0xFFAA00  # Laranja
                description = f"The restart was completed, but took longer than expected ({self.alert_max_time_seconds}s)"
                
                fields = [
                    {"name": "⏱️ Actual Time", "value": f"{elapsed:.1f}s", "inline": True},
                    {"name": "⏱️ Limit", "value": f"{self.alert_max_time_seconds}s", "inline": True},
                    {"name": "🔄 Attempts", "value": str(retry_count), "inline": True},
                    {"name": "✅ Status", "value": "Completed successfully, but took too long", "inline": False},
                ]
            else:
                return  # Tipo desconhecido
            
            # Enviar webhook
            success = self.discord_webhook.send_webhook(
                webhook_name="log-ssm",
                title=title,
                description=description,
                color=color,
                fields=fields,
            )
            
            if success:
                self.logger.info(f"Alerta de restart ({alert_type}) enviado para Discord")
            else:
                self.logger.warn(f"Falha ao enviar alerta de restart ({alert_type}) para Discord")
                
        except Exception as e:
            self.logger.error(f"Erro ao enviar alerta de restart: {e}")
    
    def test_restart_alert(self, alert_type: str = "failure") -> Dict[str, Any]:
        """
        Método de teste para enviar alerta de restart para Discord
        
        Args:
            alert_type: Tipo de alerta ('failure' ou 'timeout')
        
        Returns:
            Dict com resultado do teste
        """
        try:
            if alert_type not in ["failure", "timeout"]:
                return {
                    "success": False,
                    "error": f"Tipo de alerta inválido: {alert_type}. Use 'failure' ou 'timeout'"
                }
            
            # Criar resultado simulado
            if alert_type == "failure":
                test_result = {
                    "success": False,
                    "status": "test_failure",
                    "message": "This is a test alert for scheduled restart failure",
                    "elapsed_seconds": 150.5,
                    "retry_count": 3,
                }
            else:  # timeout
                test_result = {
                    "success": True,
                    "status": "restarted",
                    "message": "Restart completed successfully, but took longer than expected",
                    "elapsed_seconds": 280.0,  # Mais que o limite padrão de 240s
                    "retry_count": 2,
                }
            
            # Enviar alerta
            self._send_restart_alert(alert_type, test_result)
            
            return {
                "success": True,
                "message": f"Test alert ({alert_type}) sent to Discord",
                "alert_type": alert_type,
                "test_result": test_result,
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao enviar alerta de teste: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _log_schedule_event(
        self, event_type: str, message: str, data: Dict[str, Any] = None
    ):
        """Registrar evento do agendador"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "message": message,
            "data": data or {},
        }

        self.schedule_logs.append(log_entry)

        # Manter apenas os últimos 100 logs
        if len(self.schedule_logs) > 100:
            self.schedule_logs = self.schedule_logs[-100:]

        self.logger.info(f"[SCHEDULER] {message}", data)

    def _calculate_next_restart(self) -> Optional[datetime]:
        """Calcular próxima reinicialização"""
        if not self.restart_times:
            return None

        now = datetime.now()
        today = now.date()

        # Converter horários para datetime de hoje
        restart_datetimes = []
        for time_str in self.restart_times:
            try:
                hour, minute = map(int, time_str.split(":"))
                restart_dt = datetime.combine(
                    today, datetime.min.time().replace(hour=hour, minute=minute)
                )
                restart_datetimes.append(restart_dt)
            except ValueError:
                self.logger.error(f"Formato de horário inválido: {time_str}")
                continue

        # Ordenar horários
        restart_datetimes.sort()

        # Encontrar próximo horário
        for restart_dt in restart_datetimes:
            if restart_dt > now:
                return restart_dt

        # Se não há horário hoje, usar o primeiro de amanhã
        if restart_datetimes:
            return restart_datetimes[0] + timedelta(days=1)

        return None

    def _clear_restart_jobs(self):
        """
        Limpar todos os jobs relacionados a restart do scheduler
        
        Isso previne acúmulo de jobs duplicados que podem causar múltiplos
        restarts simultâneos e mensagens duplicadas no Discord.
        """
        try:
            jobs_before = len(self._scheduler.jobs)
            
            # Limpar todos os jobs do scheduler
            # Nota: Como RestartScheduler tem seu próprio scheduler isolado,
            # é seguro limpar todos os jobs, pois todos são relacionados ao restart
            self._scheduler.clear()
            
            jobs_after = len(self._scheduler.jobs)
            
            if jobs_before > 0:
                self.logger.info(
                    f"[SCHEDULER] Jobs de restart limpos: {jobs_before} job(s) removido(s)",
                    {"jobs_before": jobs_before, "jobs_after": jobs_after}
                )
                self._log_schedule_event(
                    "jobs_cleared",
                    f"Jobs de restart limpos ({jobs_before} removido(s))"
                )
        except Exception as e:
            self.logger.error(f"Erro ao limpar jobs de restart: {e}")
            # Não falhar se houver erro na limpeza, apenas logar
    
    def _health_check(self):
        """
        Verificação de saúde do scheduler
        
        Verifica se todos os horários configurados têm jobs agendados corretamente.
        Se detectar problemas, tenta corrigir automaticamente.
        """
        try:
            if not self.is_running or not self.restart_times:
                return
            
            # Verificar se a thread do scheduler está viva (com lock para evitar race conditions)
            # Usar lock apenas na verificação e modificação de estado, não na leitura inicial
            if self.scheduler_thread and not self.scheduler_thread.is_alive():
                self.logger.error(
                    "[SCHEDULER HEALTH] Thread do scheduler morreu! Tentando reiniciar..."
                )
                # Tentar reiniciar o scheduler automaticamente (com lock para thread safety)
                # IMPORTANTE: Usar lock aqui para evitar race conditions com stop()/start()
                thread_restarted = False
                new_thread = None
                with self._scheduling_lock:
                    try:
                        # Verificar novamente após adquirir lock (pode ter mudado)
                        if self.is_running and (not self.scheduler_thread or not self.scheduler_thread.is_alive()):
                            # Parar evento anterior e criar nova thread
                            self.stop_event.clear()
                            
                            # Criar nova thread
                            new_thread = threading.Thread(
                                target=self._scheduler_loop, daemon=True
                            )
                            new_thread.start()
                            
                            # Atualizar referência da thread
                            self.scheduler_thread = new_thread
                            thread_restarted = True
                            
                    except Exception as e:
                        self.logger.error(f"[SCHEDULER HEALTH] Erro ao reiniciar thread: {e}")
                        self.is_running = False
                        return
                
                # Aguardar um pouco para verificar se iniciou corretamente (FORA do lock para não bloquear)
                if thread_restarted and new_thread:
                    time.sleep(0.5)
                    if new_thread.is_alive():
                        self.logger.info("[SCHEDULER HEALTH] Thread do scheduler reiniciada com sucesso")
                    else:
                        self.logger.error("[SCHEDULER HEALTH] Falha ao reiniciar thread - thread morreu imediatamente")
                        # Marcar como não rodando se thread morreu
                        with self._scheduling_lock:
                            self.is_running = False
                return
            
            # Contar jobs agendados
            jobs_count = len(self._scheduler.jobs)
            
            # Calcular quantos jobs deveriam existir
            # 1 job principal por horário + notificações Discord + verificação Gestão
            expected_jobs_per_restart = 1 + len(self.notification_minutes) + 1  # restart + notificações + gestão
            expected_total_jobs = len(self.restart_times) * expected_jobs_per_restart
            
            # Verificar se há jobs suficientes
            if jobs_count < expected_total_jobs * 0.5:  # Menos de 50% dos jobs esperados
                self.logger.warning(
                    f"[SCHEDULER HEALTH] Jobs insuficientes detectados: {jobs_count} encontrado(s), esperado ~{expected_total_jobs}",
                    {
                        "jobs_found": jobs_count,
                        "jobs_expected": expected_total_jobs,
                        "restart_times": len(self.restart_times)
                    }
                )
                
                # Tentar recuperação: reagendar todos os horários
                self.logger.info("[SCHEDULER HEALTH] Tentando recuperação automática...")
                self._recover_scheduled_jobs()
            
            # Verificar se há jobs demais (possível duplicação)
            elif jobs_count > expected_total_jobs * 1.5:  # Mais de 150% dos jobs esperados
                self.logger.warning(
                    f"[SCHEDULER HEALTH] Possível duplicação de jobs: {jobs_count} encontrado(s), esperado ~{expected_total_jobs}",
                    {
                        "jobs_found": jobs_count,
                        "jobs_expected": expected_total_jobs
                    }
                )
                
                # Limpar e reagendar TODOS os horários usando método de recuperação
                self.logger.info("[SCHEDULER HEALTH] Limpando e reagendando todos os jobs...")
                self._recover_scheduled_jobs()
            
            # Log periódico de saúde (apenas se tudo estiver OK)
            else:
                self._last_health_check = datetime.now()
                self.logger.debug(
                    f"[SCHEDULER HEALTH] Status OK: {jobs_count} job(s) agendado(s)",
                    {"jobs_count": jobs_count, "restart_times": len(self.restart_times)}
                )
                
        except Exception as e:
            self.logger.error(f"Erro no health check do scheduler: {e}")
    
    def _recover_scheduled_jobs(self):
        """
        Recuperação automática: reagendar TODOS os horários de restart
        
        Usado quando o health check detecta que faltam jobs agendados.
        Reagenda todos os horários configurados para garantir cobertura completa.
        
        NOTA: Este método chama _schedule_restart() que já tem lock próprio.
        Mas limpar jobs antes precisa de lock para evitar race conditions com start().
        """
        # Usar lock para evitar race conditions com start()/stop()
        # _schedule_restart() já tem lock, mas clear() precisa ser protegido
        with self._scheduling_lock:
            try:
                self.logger.info("[SCHEDULER RECOVERY] Iniciando recuperação de jobs...")
                
                # Limpar todos os jobs (protegido por lock)
                self._scheduler.clear()
                
                # Reagendar TODOS os horários de restart
                # Nota: _schedule_restart() tem seu próprio lock, mas vamos chamar
                # com clear_existing=False para não limpar entre chamadas
                now = datetime.now()
                today = now.date()
                recovered_count = 0
                
                restart_times_copy = list(self.restart_times)  # Copiar para evitar modificação durante iteração
                
            except Exception as e:
                self.logger.error(f"Erro durante recuperação de jobs (fase de limpeza): {e}")
                return
        
        # Agendar jobs fora do lock (cada _schedule_restart() tem seu próprio lock)
        # Isso evita deadlock e permite agendamento em paralelo se necessário
        for time_str in restart_times_copy:
            try:
                hour, minute = map(int, time_str.split(":"))
                restart_dt = datetime.combine(
                    today, datetime.min.time().replace(hour=hour, minute=minute)
                )
                if restart_dt <= now:
                    restart_dt += timedelta(days=1)
                
                # Agendar restart (clear_existing=False para não limpar entre chamadas)
                # Cada chamada tem seu próprio lock interno
                self._schedule_restart(restart_dt, clear_existing=False)
                recovered_count += 1
            except ValueError:
                self.logger.error(f"Formato de horário inválido durante recuperação: {time_str}")
                continue
            except Exception as e:
                self.logger.error(f"Erro ao agendar restart durante recuperação: {e}")
                continue
        
        jobs_after = len(self._scheduler.jobs)
        self.logger.info(
            f"[SCHEDULER RECOVERY] Recuperação concluída: {recovered_count} horário(s) reagendado(s), {jobs_after} job(s) total(is)"
        )

    def _schedule_restart(self, restart_time: datetime, clear_existing: bool = True):
        """
        Agendar reinicialização para horário específico
        
        Args:
            restart_time: Horário do restart
            clear_existing: Se True, limpa todos os jobs antes de criar novos.
                          Se False, apenas adiciona o novo job (útil para agendar múltiplos horários)
        
        IMPORTANTE: Por padrão, limpa todos os jobs existentes antes de criar novos
        para prevenir acúmulo de jobs duplicados que causam múltiplos restarts.
        """
        # Validar que restart_time não está muito no passado (mais de 24 horas)
        now = datetime.now()
        if restart_time < now - timedelta(days=1):
            self.logger.warning(
                f"[SCHEDULER] Horário de restart muito no passado ignorado: {restart_time.strftime('%Y-%m-%d %H:%M')} "
                f"(mais de 24h no passado). Horário atual: {now.strftime('%Y-%m-%d %H:%M')}"
            )
            return  # Não agendar se estiver muito no passado
        
        # Lock para prevenir race conditions (múltiplas chamadas simultâneas)
        # O lock protege toda a operação de agendamento
        with self._scheduling_lock:
            # Limpar jobs apenas se solicitado (padrão: sim, para prevenir duplicação)
            if clear_existing:
                # LIMPAR TODOS OS JOBS ANTES DE CRIAR NOVOS
                # Isso previne acúmulo de jobs duplicados ao longo do tempo
                self._clear_restart_jobs()
            
            # Verificar se já existe job para este horário (prevenção adicional)
            # Verificar pelo nome da função (restart_job) e horário para evitar falsos positivos
            restart_time_str = restart_time.strftime("%H:%M")
            existing_restart_jobs = []
            for job in self._scheduler.jobs:
                # Verificar se é um job de restart (pela função restart_job e horário)
                if hasattr(job, 'next_run') and job.next_run:
                    job_time_str = job.next_run.strftime("%H:%M")
                    # Verificar se é um job principal de restart (não notificação)
                    # Jobs de restart têm função restart_job
                    if job_time_str == restart_time_str:
                        # Tentar identificar pelo nome da função (melhor método)
                        if hasattr(job.job_func, '__name__'):
                            func_name = job.job_func.__name__
                            # Se for 'restart_job', é um job principal de restart
                            if func_name == 'restart_job':
                                existing_restart_jobs.append(job)
            
            if existing_restart_jobs and not clear_existing:
                self.logger.debug(
                    f"[SCHEDULER] Job de restart já existe para {restart_time_str}, pulando criação",
                    {"existing_restart_jobs": len(existing_restart_jobs)}
                )
                return  # Job já existe, não criar duplicado

            def restart_job():
                try:
                    self._log_schedule_event(
                        "restart_started",
                        f"Iniciando reinicialização agendada para {restart_time.strftime('%H:%M')}",
                    )
                    # REMOVIDO: self._notify para evitar duplicação de mensagens Discord

                    # IMPORTANTE: Não executar entregas (shop/veículos) aqui.
                    # Entregas escrevem no SCUM.db e devem acontecer SOMENTE na janela offline,
                    # depois do serviço SCUM parar, dentro do ServerManager.restart_server().

                    # Limpar notificações de restart antes de reiniciar
                    self._clear_restart_notifications()

                    # Obter caminho do SCUM.db e elevated_users_manager para passar ao restart_server()
                    scum_db_path = None
                    elevated_users_manager = None

                    # Tentar obter scum_db_path do config
                    try:
                        from utils.config_path_helper import ConfigPathHelper

                        path_helper = ConfigPathHelper(self.config)
                        scum_db_path = path_helper.get_scum_db_path()
                    except Exception as e:
                        self.logger.warning(
                            f"Erro ao obter scum_db_path: {e} - usando fallbacks"
                        )

                    # Obter elevated_users_manager se disponível
                    if (
                        hasattr(self, "elevated_users_manager")
                        and self.elevated_users_manager
                    ):
                        elevated_users_manager = self.elevated_users_manager

                    # Obter player_gps_sync_service se disponível para pará-lo temporariamente
                    gps_was_running = False
                    player_gps_sync_service = None
                    try:
                        from app.extensions import get_services
                        svc = get_services()
                        if svc and svc.player_gps_sync_service:
                            player_gps_sync_service = svc.player_gps_sync_service
                            if getattr(player_gps_sync_service, "is_running", False):
                                gps_was_running = True
                                self.logger.info(
                                    "[SCHEDULER] Pausando PlayerGpsSyncService temporariamente para janela de restart agendado."
                                )
                                player_gps_sync_service.stop()
                    except Exception as e:
                        self.logger.warn(
                            f"[SCHEDULER] Erro ao tentar parar PlayerGpsSyncService antes do restart: {e}"
                        )

                    # Executar reinicialização com parâmetros
                    # Nota: A limpeza de WAL/SHM e sincronização de elevated users agora são feitas automaticamente pelo restart_server()
                    result = {"success": False, "status": "failed_exception"}
                    try:
                        result = self.server_manager.restart_server(
                            scum_db_path=scum_db_path,
                            elevated_users_manager=elevated_users_manager,
                        )
                    finally:
                        # Reiniciar PlayerGpsSyncService se estava rodando
                        try:
                            if gps_was_running and player_gps_sync_service is not None:
                                self.logger.info(
                                    "[SCHEDULER] Retomando PlayerGpsSyncService após conclusão do restart agendado."
                                )
                                player_gps_sync_service.start()
                        except Exception as e:
                            self.logger.warn(
                                f"[SCHEDULER] Falha ao iniciar PlayerGpsSyncService após restart: {e}"
                            )

                    if result.get("success"):
                        self._log_schedule_event(
                            "restart_success",
                            "Reinicialização agendada concluída com sucesso",
                            result,
                        )
                        self._notify(
                            "Reinicialização agendada concluída com sucesso", result
                        )
                        
                        # Resetar contador de falhas consecutivas
                        self.consecutive_failures = 0
                        
                        # Verificar se tempo excedeu limite (alerta de demora)
                        elapsed = result.get("elapsed_seconds", 0)
                        if self.alert_enabled and self.alert_on_timeout and elapsed > self.alert_max_time_seconds:
                            self._send_restart_alert("timeout", result)
                    else:
                        self._log_schedule_event(
                            "restart_failed", "Falha na reinicialização agendada", result
                        )
                        self._notify("Falha na reinicialização agendada", result)
                        
                        # Enviar alerta de falha
                        if self.alert_enabled and self.alert_on_failure:
                            self._send_restart_alert("failure", result)
                        
                        # Incrementar contador de falhas consecutivas
                        self.consecutive_failures += 1

                    # NOTA: Não é necessário chamar _schedule_next_restart() aqui
                    # porque os jobs criados com every().day.at() são RECORRENTES
                    # e executam automaticamente todos os dias no horário agendado.
                    # Chamar _schedule_next_restart() aqui causaria duplicação de jobs.

                except Exception as e:
                    self._log_schedule_event(
                        "restart_error", f"Erro na reinicialização agendada: {e}"
                    )
                    self._notify("Erro na reinicialização agendada", {"error": str(e)})
                    
                    # Enviar alerta de erro excepcional
                    if self.alert_enabled and self.alert_on_failure:
                        error_result = {
                            "success": False,
                            "status": "exception",
                            "message": str(e),
                            "elapsed_seconds": 0,
                            "retry_count": 0,
                        }
                        self._send_restart_alert("failure", error_result)
                    
                    # Incrementar contador de falhas consecutivas
                    self.consecutive_failures += 1

            # Agendar job principal (dentro do lock para garantir atomicidade)
            self._scheduler.every().day.at(restart_time.strftime("%H:%M")).do(restart_job)
            self._log_schedule_event(
                "restart_scheduled",
                f"Reinicialização agendada para {restart_time.strftime('%H:%M')}",
            )

            # Agendar notificações de Discord (10, 5, 4, 3, 2, 1 minutos antes)
            self._schedule_discord_notifications(restart_time)

            # Agendar verificação de mensagem do Gestão 15 minutos antes do restart
            self._schedule_gestao_message_check(restart_time)

            # Criar notificações de restart in-game (sempre criar, mesmo que esteja fora da janela)
            # A mensagem do Gestão será adicionada depois quando o job de 15min executar
            self._create_restart_notifications(restart_time.strftime("%H:%M"), restart_time)

    def _schedule_discord_notifications(self, restart_time: datetime):
        """Agendar notificações de Discord antes da reinicialização"""
        # Usar os minutos do config.json (scheduler.notification_minutes)
        discord_notification_minutes = self.notification_minutes

        now = datetime.now()
        for minutes in discord_notification_minutes:
            # Validar valor de minutos (deve ser positivo e razoável)
            if not isinstance(minutes, (int, float)) or minutes <= 0:
                self.logger.warning(
                    f"[SCHEDULER] Valor inválido de notification_minutes ignorado: {minutes}. Deve ser positivo."
                )
                continue
            
            # Validar que não é muito grande (máximo 23h59 = 1439 minutos)
            if minutes >= 1440:
                self.logger.warning(
                    f"[SCHEDULER] Valor muito grande de notification_minutes ignorado: {minutes}. Máximo: 1439 minutos (23h59)."
                )
                continue
            
            notification_time = restart_time - timedelta(minutes=minutes)
            
            # Validar que notification_time não está muito no passado
            # Se estiver mais de 24 horas no passado, não agendar
            if notification_time < now - timedelta(days=1):
                self.logger.warning(
                    f"[SCHEDULER] Horário de notificação muito no passado ignorado: {notification_time.strftime('%H:%M')} "
                    f"(mais de 24h no passado para restart às {restart_time.strftime('%H:%M')})"
                )
                continue

            def discord_notification_job(
                minutes=minutes,
            ):  # Capturar o valor atual de minutes
                try:
                    self._log_schedule_event(
                        "discord_notification",
                        f"Notificação Discord: {minutes} minuto(s) antes do restart",
                    )
                    self._notify(
                        "",
                        {
                            "restart_time": restart_time.isoformat(),
                            "minutes_remaining": minutes,
                            "notification_type": "discord_warning",
                        },
                    )
                except Exception as e:
                    self._log_schedule_event(
                        "discord_notification_error",
                        f"Erro na notificação Discord: {e}",
                    )

            # Agendar notificação
            self._scheduler.every().day.at(notification_time.strftime("%H:%M")).do(
                discord_notification_job
            )
            self._log_schedule_event(
                "discord_notification_scheduled",
                f"Notificação Discord agendada para {minutes} minuto(s) antes do restart ({notification_time.strftime('%H:%M')})",
            )

    def _schedule_gestao_message_check(self, restart_time: datetime):
        """
        Agendar verificação de mensagem do Gestão (Desativado no Open Source)
        """
        return

    def _schedule_notifications(self, restart_time: datetime):
        """Agendar notificações antes da reinicialização"""
        for minutes in self.notification_minutes:
            notification_time = restart_time - timedelta(minutes=minutes)

            def notification_job():
                try:
                    message = f"Reinicialização agendada em {minutes} minuto(s) - {restart_time.strftime('%H:%M')}"
                    self._log_schedule_event("notification", message)
                    self._notify(
                        message,
                        {
                            "restart_time": restart_time.isoformat(),
                            "minutes_remaining": minutes,
                        },
                    )
                except Exception as e:
                    self.logger.error(f"Erro na notificação: {e}")

            # Agendar notificação
            self._scheduler.every().day.at(notification_time.strftime("%H:%M")).do(
                notification_job
            )
            self._log_schedule_event(
                "notification_scheduled",
                f"Notificação agendada para {notification_time.strftime('%H:%M')} ({minutes}min antes)",
            )

    def _scheduler_loop(self):
        """Loop principal do agendador"""
        self.logger.info("Loop do agendador iniciado")
        
        last_health_check = time.time()
        consecutive_errors = 0
        max_consecutive_errors = 10  # Após 10 erros consecutivos, parar o loop

        while not self.stop_event.is_set():
            try:
                self._scheduler.run_pending()
                
                # Resetar contador de erros se execução foi bem-sucedida
                consecutive_errors = 0
                
                # Health check periódico: verificar integridade dos jobs
                current_time = time.time()
                if current_time - last_health_check >= self._health_check_interval:
                    self._health_check()
                    last_health_check = current_time
                
                time.sleep(1)  # Verificar a cada segundo
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(
                    f"Erro no loop do agendador (erro {consecutive_errors}/{max_consecutive_errors}): {e}"
                )
                
                # Se muitos erros consecutivos, parar o loop para evitar spam de logs
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.error(
                        f"[SCHEDULER CRITICAL] Muitos erros consecutivos ({consecutive_errors}). "
                        "Parando loop do agendador. Use /api/scheduler/restart para reiniciar."
                    )
                    # Usar lock para evitar race condition ao modificar is_running
                    with self._scheduling_lock:
                        self.is_running = False
                    break
                
                time.sleep(5)  # Aguardar mais tempo em caso de erro

        self.logger.info("Loop do agendador encerrado")

    def start(self) -> Dict[str, Any]:
        """Iniciar agendador"""
        # Usar lock para evitar race conditions com stop() ou restart()
        with self._scheduling_lock:
            try:
                if not self.enabled:
                    return {
                        "success": False,
                        "message": "Agendador está desabilitado",
                        "status": "disabled",
                    }

                if self.is_running:
                    return {
                        "success": False,
                        "message": "Agendador já está rodando",
                        "status": "already_running",
                    }

                if not self.restart_times:
                    return {
                        "success": False,
                        "message": "Nenhum horário de reinicialização configurado",
                        "status": "no_times_configured",
                    }

                # Limpar agendamentos anteriores (uma única vez)
                self._scheduler.clear()

                # Validar notification_minutes
                if not isinstance(self.notification_minutes, (list, tuple)):
                    self.logger.warning(
                        f"[SCHEDULER] notification_minutes deve ser uma lista, recebido: {type(self.notification_minutes)}. "
                        "Usando padrão [5, 1]."
                    )
                    self.notification_minutes = [5, 1]
                else:
                    # Filtrar valores inválidos
                    valid_minutes = []
                    for minutes in self.notification_minutes:
                        if isinstance(minutes, (int, float)) and 0 < minutes < 1440:
                            valid_minutes.append(int(minutes))
                        else:
                            self.logger.warning(
                                f"[SCHEDULER] Valor inválido de notification_minutes ignorado: {minutes}. "
                                "Deve ser um número positivo menor que 1440 (24h)."
                            )
                    if valid_minutes:
                        self.notification_minutes = sorted(set(valid_minutes), reverse=True)  # Ordenar do maior para o menor
                    else:
                        self.logger.warning(
                            "[SCHEDULER] Nenhum valor válido de notification_minutes encontrado. Usando padrão [5, 1]."
                        )
                        self.notification_minutes = [5, 1]
                
                # Validar horários duplicados na configuração
                unique_times = set(self.restart_times)
                if len(unique_times) < len(self.restart_times):
                    duplicates = [t for t in self.restart_times if self.restart_times.count(t) > 1]
                    self.logger.warning(
                        f"[SCHEDULER] Horários duplicados encontrados na configuração: {set(duplicates)}. "
                        "Usando apenas horários únicos."
                    )
                    self.restart_times = list(unique_times)
                
                # Agendar TODOS os horários de restart configurados
                # Isso garante que todos os horários tenham jobs recorrentes agendados
                scheduled_count = 0
                now = datetime.now()
                today = now.date()
                
                for time_str in self.restart_times:
                    try:
                        hour, minute = map(int, time_str.split(":"))
                        
                        # Validar horário (0-23 horas, 0-59 minutos)
                        if not (0 <= hour <= 23 and 0 <= minute <= 59):
                            self.logger.error(
                                f"Horário inválido: {time_str} (hora deve ser 0-23, minuto deve ser 0-59)"
                            )
                            continue
                        
                        restart_dt = datetime.combine(
                            today, datetime.min.time().replace(hour=hour, minute=minute)
                        )
                        
                        # Se o horário já passou hoje, agendar para amanhã
                        if restart_dt <= now:
                            restart_dt += timedelta(days=1)
                        
                        # Agendar restart para este horário (clear_existing=False para não limpar entre chamadas)
                        self._schedule_restart(restart_dt, clear_existing=False)
                        scheduled_count += 1
                        
                    except ValueError:
                        self.logger.error(f"Formato de horário inválido: {time_str}")
                        continue
                
                if scheduled_count == 0:
                    return {
                        "success": False,
                        "message": "Não foi possível agendar nenhuma reinicialização",
                        "status": "schedule_failed",
                    }
                
                # Calcular próximo restart para retornar no status
                next_restart = self._calculate_next_restart()

                # Iniciar thread do agendador
                self.stop_event.clear()
                self.scheduler_thread = threading.Thread(
                    target=self._scheduler_loop, daemon=True
                )
                self.scheduler_thread.start()

                self.is_running = True

                jobs_count = len(self._scheduler.jobs)
                
                self._log_schedule_event(
                    "scheduler_started",
                    "Agendador iniciado com sucesso",
                    {
                        "restart_times": self.restart_times,
                        "scheduled_restarts": scheduled_count,
                        "total_jobs": jobs_count,
                        "next_restart": next_restart.isoformat() if next_restart else None,
                        "notification_minutes": self.notification_minutes,
                    },
                )

                return {
                    "success": True,
                    "message": "Agendador iniciado com sucesso",
                    "status": "started",
                    "data": {
                        "restart_times": self.restart_times,
                        "scheduled_restarts": scheduled_count,
                        "total_jobs": jobs_count,
                        "next_restart": next_restart.isoformat() if next_restart else None,
                        "notification_minutes": self.notification_minutes,
                    },
                }

            except Exception as e:
                self.logger.error(f"Erro ao iniciar agendador: {e}")
                return {
                    "success": False,
                    "message": f"Erro ao iniciar agendador: {str(e)}",
                    "status": "error",
                }

    def stop(self) -> Dict[str, Any]:
        """Parar agendador"""
        # Usar lock para evitar race conditions com start() ou restart()
        with self._scheduling_lock:
            try:
                if not self.is_running:
                    return {
                        "success": False,
                        "message": "Agendador não está rodando",
                        "status": "not_running",
                    }

                # Marcar como parado ANTES de parar thread (evita race conditions)
                self.is_running = False

                # Parar thread
                self.stop_event.set()
                if self.scheduler_thread and self.scheduler_thread.is_alive():
                    self.scheduler_thread.join(timeout=5)
                    # Se a thread ainda estiver viva após timeout, logar aviso
                    if self.scheduler_thread.is_alive():
                        self.logger.warning(
                            "[SCHEDULER] Thread do scheduler não parou dentro do timeout (5s)"
                        )

                # Limpar agendamentos
                self._scheduler.clear()

                self._log_schedule_event(
                    "scheduler_stopped", "Agendador parado com sucesso"
                )

                return {
                    "success": True,
                    "message": "Agendador parado com sucesso",
                    "status": "stopped",
                }

            except Exception as e:
                self.logger.error(f"Erro ao parar agendador: {e}")
                return {
                    "success": False,
                    "message": f"Erro ao parar agendador: {str(e)}",
                    "status": "error",
                }

    def restart(self) -> Dict[str, Any]:
        """Reiniciar agendador"""
        try:
            stop_result = self.stop()
            if not stop_result.get("success"):
                return stop_result

            time.sleep(1)  # Aguardar um pouco

            start_result = self.start()
            return start_result

        except Exception as e:
            self.logger.error(f"Erro ao reiniciar agendador: {e}")
            return {
                "success": False,
                "message": f"Erro ao reiniciar agendador: {str(e)}",
                "status": "error",
            }

    def get_status(self) -> Dict[str, Any]:
        """Obter status do agendador"""
        try:
            next_restart = self._calculate_next_restart()
            
            # Detalhar jobs agendados
            jobs_detail = []
            try:
                for job in self._scheduler.jobs:
                    job_info = {
                        "next_run": job.next_run.isoformat() if job.next_run else None,
                        "interval": str(job.interval) if hasattr(job, 'interval') else None,
                    }
                    # Tentar identificar tipo de job pela função
                    if hasattr(job.job_func, '__name__'):
                        job_info["type"] = job.job_func.__name__
                    jobs_detail.append(job_info)
            except Exception as e:
                self.logger.debug(f"Erro ao detalhar jobs: {e}")

            return {
                "success": True,
                "data": {
                    "enabled": self.enabled,
                    "is_running": self.is_running,
                    "restart_times": self.restart_times,
                    "next_restart": next_restart.isoformat() if next_restart else None,
                    "notification_minutes": self.notification_minutes,
                    "scheduled_jobs": len(self._scheduler.jobs),
                    "jobs_detail": jobs_detail,
                    "logs_count": len(self.schedule_logs),
                    "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
                    "consecutive_failures": self.consecutive_failures,
                },
            }

        except Exception as e:
            self.logger.error(f"Erro ao obter status do agendador: {e}")
            return {"success": False, "error": str(e)}

    def get_logs(self, limit: int = 50) -> Dict[str, Any]:
        """Obter logs do agendador"""
        try:
            logs = self.schedule_logs[-limit:] if limit > 0 else self.schedule_logs

            return {
                "success": True,
                "data": {"logs": logs, "count": len(logs), "limit": limit},
            }

        except Exception as e:
            self.logger.error(f"Erro ao obter logs do agendador: {e}")
            return {"success": False, "error": str(e)}

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Atualizar configuração do agendador"""
        # Usar lock para evitar race conditions com start()/stop()/restart()
        with self._scheduling_lock:
            try:
                # Atualizar configurações
                self.scheduler_config.update(new_config)
                self.enabled = self.scheduler_config.get("enabled", True)
                self.restart_times = self.scheduler_config.get("restart_times", [])
                self.notification_minutes = self.scheduler_config.get(
                    "notification_minutes", [5, 1]
                )

                if self.notification_manager and hasattr(
                    self.notification_manager, "update_scheduler_times"
                ):
                    self.notification_manager.update_scheduler_times(self.restart_times)

                self._log_schedule_event(
                    "config_updated", "Configuração do agendador atualizada", new_config
                )

                # Verificar se estava rodando dentro do lock (para evitar race conditions)
                was_running = self.is_running
                
            except Exception as e:
                self.logger.error(f"Erro ao atualizar configuração: {e}")
                return {
                    "success": False,
                    "message": f"Erro ao atualizar configuração: {str(e)}",
                    "status": "error",
                }
        
        # Reiniciar agendador se estiver rodando (fora do lock para evitar deadlock)
        # Nota: restart() já tem lock próprio, mas verificamos was_running dentro do lock
        if was_running:
            restart_result = self.restart()
            return {
                "success": True,
                "message": "Configuração atualizada e agendador reiniciado",
                "status": "updated_and_restarted",
                "restart_result": restart_result,
            }

        return {
            "success": True,
            "message": "Configuração atualizada",
            "status": "updated",
        }

    def force_restart_now(self) -> Dict[str, Any]:
        """Forçar reinicialização imediatamente"""
        try:
            self._log_schedule_event(
                "force_restart", "Reinicialização forçada iniciada"
            )
            self._notify(
                "Reinicialização forçada iniciada",
                {"forced": True, "timestamp": datetime.now().isoformat()},
            )

            # Obter caminho do SCUM.db e elevated_users_manager para passar ao restart_server()
            scum_db_path = None
            elevated_users_manager = None

            # Tentar obter scum_db_path do config
            try:
                from utils.config_path_helper import ConfigPathHelper

                path_helper = ConfigPathHelper(self.config)
                scum_db_path = path_helper.get_scum_db_path()
            except Exception as e:
                self.logger.warning(
                    f"Erro ao obter scum_db_path: {e} - usando fallbacks"
                )

            # Obter elevated_users_manager se disponível
            if hasattr(self, "elevated_users_manager") and self.elevated_users_manager:
                elevated_users_manager = self.elevated_users_manager

            result = self.server_manager.restart_server(
                scum_db_path=scum_db_path, elevated_users_manager=elevated_users_manager
            )

            if result.get("success"):
                self._log_schedule_event(
                    "force_restart_success",
                    "Reinicialização forçada concluída com sucesso",
                    result,
                )
                self._notify("Reinicialização forçada concluída com sucesso", result)
            else:
                self._log_schedule_event(
                    "force_restart_failed", "Falha na reinicialização forçada", result
                )
                self._notify("Falha na reinicialização forçada", result)

            return result

        except Exception as e:
            self._log_schedule_event(
                "force_restart_error", f"Erro na reinicialização forçada: {e}"
            )
            self._notify("Erro na reinicialização forçada", {"error": str(e)})
            return {
                "success": False,
                "message": f"Erro na reinicialização forçada: {str(e)}",
                "status": "error",
            }
