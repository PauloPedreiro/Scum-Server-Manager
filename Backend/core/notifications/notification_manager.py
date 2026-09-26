#!/usr/bin/env python3
"""
Notification Manager - Gerenciador principal do sistema de notificações
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from utils.logger import StructuredLogger
from .scum_notifier import SCUMNotifier
from .notifications_compiler import NotificationsCompiler
from .scheduled_notifications_store import ScheduledNotificationsStore
from .scheduled_notifications_manager import ScheduledNotificationsManager


class NotificationManager:
    """Gerenciador principal do sistema de notificações"""

    def __init__(
        self,
        config: Dict[str, Any],
        logger: StructuredLogger = None,
        scum_config_path: str = None,
        scheduler_times: Optional[List[str]] = None,
    ):
        self.config = config
        self.logger = logger or StructuredLogger()

        self.scheduler_times = list(scheduler_times) if scheduler_times else []

        # Sistema de prioridades
        self.PRIORITIES = {
            "RESTART": 100,  # Máxima prioridade - não pode ser sobrescrito
            "CUSTOM": 10,  # Baixa prioridade - não pode interferir com restart
            "EVENTS": 20,  # Média prioridade
        }

        # Configurações
        self.enabled = config.get("enabled", True)
        self.check_interval = config.get("check_interval", 30000)  # 30 segundos
        self.restart_protection_window = config.get(
            "restart_protection_window", 15
        )  # 15 minutos

        # Caminhos
        self.scum_config_path = (
            scum_config_path or "C:/Servers/Scum/SCUM/Saved/Config/WindowsServer"
        )
        self.base_path = Path("data/notifications")
        self.templates_path = self.base_path / "templates"
        self.config_path = self.base_path / "config"

        # Criar diretórios se não existirem
        self._create_directories()

        # Inicializar SCUM Notifier
        self.scum_notifier = SCUMNotifier(config, self.logger)

        self._compiler = NotificationsCompiler(
            logger=self.logger,
            scum_notifications_path=self.scum_notifier.scum_notifications_path,
            scheduler_times=self.scheduler_times,
            templates_path=self.templates_path,
            reserved_before_minutes=15,
            reserved_after_minutes=5,
        )

        self._scheduled_store = ScheduledNotificationsStore(
            base_path=self.base_path,
            logger=self.logger,
        )
        self.scheduled_manager = ScheduledNotificationsManager(
            store=self._scheduled_store,
            compiler=self._compiler,
            logger=self.logger,
        )

        # Estado interno
        self.is_running = False
        self.last_restart_notifications = None
        self.notification_callbacks = []

        self._stop_event = threading.Event()

        # Verificação periódica
        self.last_verification = None
        self.verification_interval = 60  # 1 minuto
        self.last_restart_check = None
        self.last_time_check = None

        # Carregar configurações
        self.cooldowns = self._load_cooldowns()

        self.logger.info(
            "NotificationManager inicializado",
            {
                "enabled": self.enabled,
                "check_interval": self.check_interval,
                "restart_protection_window": self.restart_protection_window,
                "verification_interval": self.verification_interval,
            },
        )

        # Iniciar verificação automática em thread separada
        if self.enabled:
            self.verification_thread = threading.Thread(
                target=self._verification_loop, daemon=True
            )
            self.verification_thread.start()
            self.logger.info("Thread de verificação automática iniciada")

    def update_scheduler_times(self, restart_times: Optional[List[str]]):
        """Atualizar horários de restart conhecidos"""
        self.scheduler_times = list(restart_times) if restart_times else []
        self._compiler.scheduler_times = list(self.scheduler_times)
        self.logger.info(
            "Horários de restart atualizados no NotificationManager",
            {"count": len(self.scheduler_times), "restart_times": self.scheduler_times},
        )

    def compile_notifications(self) -> Dict[str, Any]:
        try:
            now = datetime.now()

            restart_notifications = self._compiler.build_expected_restart_schedule_for_today(
                now
            )
            custom_notifications = self.scheduled_manager.build_custom_notifications_next_24h(
                now
            )

            notifications = list(restart_notifications) + list(custom_notifications)
            notifications.sort(key=lambda n: (n.get("time") or ["99:99"])[0])

            self._compiler.write_notifications_atomic(notifications)

            return {
                "success": True,
                "count": len(notifications),
                "restart_count": len(restart_notifications),
                "custom_count": len(custom_notifications),
                "path": str(self.scum_notifier.scum_notifications_path),
            }
        except Exception as e:
            self.logger.error("Erro ao compilar notificações", {"error": str(e)})
            return {"success": False, "error": str(e)}

    def _has_reserved_window_violations(
        self, notifications: List[Dict[str, Any]], now: datetime
    ) -> bool:
        try:
            windows = self._compiler.build_reserved_windows(now)
            for n in notifications:
                msg = str(n.get("message", ""))
                if "RESTART" in msg.upper():
                    continue

                time_slots = n.get("time") or []
                if not time_slots:
                    continue

                try:
                    hhmm = str(time_slots[0])
                    h, m = self._compiler._parse_hhmm(hhmm)
                    when = datetime(now.year, now.month, now.day, h, m)
                except Exception:
                    continue

                if self._compiler.is_reserved_time(when, windows):
                    return True
            return False
        except Exception:
            return False

    def _create_directories(self):
        """Criar diretórios necessários"""
        directories = [self.base_path, self.templates_path, self.config_path]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_cooldowns(self) -> Dict[str, Any]:
        """Carregar configurações de cooldown"""
        try:
            cooldown_path = self.config_path / "cooldowns.json"
            if cooldown_path.exists():
                with open(cooldown_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                # Criar arquivo padrão
                default_cooldowns = {
                    "cooldowns": {
                        "restart": 600,  # 10 minutos
                        "custom": 30,  # 30 segundos
                        "events": 120,  # 2 minutos
                    },
                    "last_sent": {"restart": None, "custom": None, "events": None},
                }
                self._save_cooldowns(default_cooldowns)
                return default_cooldowns

        except Exception as e:
            self.logger.error("Erro ao carregar cooldowns", {"error": str(e)})
            return {
                "cooldowns": {"restart": 600, "custom": 30, "events": 120},
                "last_sent": {"restart": None, "custom": None, "events": None},
            }

    def _save_cooldowns(self, cooldowns: Dict[str, Any]):
        """Salvar configurações de cooldown"""
        try:
            cooldown_path = self.config_path / "cooldowns.json"
            with open(cooldown_path, "w", encoding="utf-8") as f:
                json.dump(cooldowns, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error("Erro ao salvar cooldowns", {"error": str(e)})

    def start(self) -> Dict[str, Any]:
        """Iniciar sistema de notificações"""
        if self.is_running:
            self.logger.warn("NotificationManager já está rodando")
            return {"success": False, "message": "Já está rodando"}

        if not self.enabled:
            self.logger.info("Sistema de notificações desabilitado")
            return {"success": False, "message": "Sistema desabilitado"}

        self.is_running = True
        self.logger.info(
            "Sistema de notificações iniciado",
            {
                "check_interval": self.check_interval,
                "restart_protection_window": self.restart_protection_window,
            },
        )

        return {"success": True, "message": "Sistema iniciado com sucesso"}

    def stop(self) -> Dict[str, Any]:
        """Parar sistema de notificações"""
        if not self.is_running and not self.enabled:
            return {"success": False, "message": "Sistema não está rodando"}

        # IMPORTANTE: Desabilitar enabled para parar a thread de verificação
        # A thread _verification_loop verifica self.enabled, não self.is_running
        self.enabled = False
        self.is_running = False

        self._stop_event.set()

        # Aguardar um pouco para a thread de verificação parar
        if hasattr(self, "verification_thread") and self.verification_thread.is_alive():
            try:
                self.verification_thread.join(timeout=10.0)
                if self.verification_thread.is_alive():
                    self.logger.warn("Thread de verificação ainda está rodando após 10 segundos")
            except Exception as e:
                self.logger.warn(f"Erro ao aguardar thread de verificação parar: {e}")
        
        self.logger.info("Sistema de notificações parado")

        return {"success": True, "message": "Sistema parado com sucesso"}

    def add_notification_callback(
        self, callback: Callable[[str, Dict[str, Any]], None]
    ):
        """Adicionar callback para notificações"""
        self.notification_callbacks.append(callback)
        self.logger.info("Callback de notificação adicionado")

    def _notify_callbacks(self, event: str, data: Dict[str, Any]):
        """Notificar callbacks registrados"""
        for callback in self.notification_callbacks:
            try:
                callback(event, data)
            except Exception as e:
                self.logger.error("Erro em callback de notificação", {"error": str(e)})

    def create_correct_notifications(
        self,
        custom_message: str = None,
        custom_duration: int = 15,
        custom_color: str = "255-255-255",
    ) -> Dict[str, Any]:
        """Criar notificações corretas: mensagem personalizada + restart para próximo horário"""
        try:
            import json

            # LIMPAR o arquivo antes de criar novas notificações
            self.logger.info("Limpando arquivo de notificações antes de criar novas")
            clear_result = self.scum_notifier.clear_notifications()
            if not clear_result.get("success"):
                self.logger.warn(
                    "Falha ao limpar notificações, continuando mesmo assim"
                )

            # Carregar template de restart
            template = self._load_template("restart")
            if not template:
                self.logger.error("Template de restart não encontrado")
                return {"success": False, "message": "Template não encontrado"}

            all_notifications = []

            # 1. Adicionar mensagem personalizada se fornecida (hora_atual + 1 minuto)
            if custom_message:
                now = datetime.now()
                notification_time = now + timedelta(minutes=1)

                custom_notification = {
                    "day": "Everyday",
                    "time": [notification_time.strftime("%H:%M")],
                    "duration": custom_duration,
                    "color": custom_color,
                    "message": custom_message,
                }
                all_notifications.append(custom_notification)

                self.logger.info(
                    f"Mensagem personalizada criada para: {notification_time.strftime('%H:%M')}"
                )

            # 2. Identificar próximo restart
            next_restart = self._get_next_restart_time()
            if not next_restart:
                return {
                    "success": False,
                    "message": "Nenhum restart agendado encontrado",
                }

            # 3. Criar notificações de restart para o próximo horário
            for notification_template in template.get("notifications", []):
                minutes_before = int(notification_template["time"].split("_")[0])
                notification_time = next_restart - timedelta(minutes=minutes_before)

                restart_notification = {
                    "day": "Everyday",
                    "time": [notification_time.strftime("%H:%M")],
                    "duration": notification_template["duration"],
                    "color": notification_template["color"],
                    "message": notification_template["message"],
                }
                all_notifications.append(restart_notification)

            # 4. Salvar no arquivo SCUM usando o método que tem verificação de horário
            self.logger.info(
                f"Salvando {len(all_notifications)} notificações com prioridade {self.PRIORITIES['CUSTOM']}"
            )
            result = self.scum_notifier.save_notifications(
                all_notifications, self.PRIORITIES["CUSTOM"]
            )
            self.logger.info(f"Resultado de save_notifications: {result}")

            if result["success"]:
                self.logger.info(
                    f"Notificações criadas: {len(all_notifications)} total",
                    {
                        "custom_message": custom_message is not None,
                        "restart_notifications": len(template.get("notifications", [])),
                        "next_restart": next_restart.strftime("%H:%M"),
                    },
                )

                return {
                    "success": True,
                    "count": len(all_notifications),
                    "next_restart": next_restart.strftime("%H:%M"),
                    "path": result.get("path", "unknown"),
                }
            else:
                return result

        except Exception as e:
            self.logger.error(f"Erro ao criar notificações corretas: {e}")
            return {"success": False, "error": str(e)}

    def _get_next_restart_time(self) -> datetime:
        """Identificar o próximo horário de restart"""
        try:

            # Horários do scheduler (do config.json)
            scheduler_times = self.scheduler_times or [
                "01:00",
                "05:00",
                "09:00",
                "13:00",
                "17:00",
                "21:00",
            ]
            if not self.scheduler_times:
                self.logger.warn(
                    "Scheduler times não informados ao NotificationManager; usando valores padrão"
                )

            now = datetime.now()
            today = now.strftime("%Y-%m-%d")

            # Converter horários para datetime de hoje
            restart_times_today = []
            for time_str in scheduler_times:
                restart_datetime = datetime.strptime(
                    f"{today} {time_str}", "%Y-%m-%d %H:%M"
                )
                restart_times_today.append(restart_datetime)

            # Se já passou o último restart de hoje, pegar o primeiro de amanhã
            next_restart = None
            for restart_time in restart_times_today:
                if restart_time > now:
                    next_restart = restart_time
                    break

            # Se não encontrou para hoje, pegar o primeiro de amanhã
            if not next_restart:
                tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
                first_restart_tomorrow = datetime.strptime(
                    f"{tomorrow} {scheduler_times[0]}", "%Y-%m-%d %H:%M"
                )
                next_restart = first_restart_tomorrow

            return next_restart

        except Exception as e:
            self.logger.error(f"Erro ao identificar próximo restart: {e}")
            return None

    def periodic_verification(self):
        """Verificação periódica do sistema de notificações"""
        try:
            current_time = time.time()

            # Verificar se é hora de fazer verificação
            if (
                self.last_verification is None
                or current_time - self.last_verification >= self.verification_interval
            ):

                self.logger.info(
                    "Iniciando verificação periódica do sistema de notificações"
                )

                now_dt = datetime.now()

                current = self._compiler.load_current_notifications()
                expected_restart = (
                    self._compiler.build_expected_restart_schedule_for_today(now_dt)
                )
                has_all_restart = self._compiler.validate_restart_presence(
                    current=current, expected=expected_restart
                )
                has_reserved_violations = self._has_reserved_window_violations(
                    current, now_dt
                )

                if not current or (not has_all_restart) or has_reserved_violations:
                    reason = "Arquivo vazio" if not current else "Divergência"
                    if has_reserved_violations:
                        reason = "Violação de janela reservada"

                    self.logger.warn(
                        "Recriando Notifications.json",
                        {
                            "reason": reason,
                            "has_all_restart": has_all_restart,
                            "has_reserved_violations": has_reserved_violations,
                        },
                    )
                    self.compile_notifications()

                self._check_time_change()

                self.last_verification = current_time
                self.logger.info("Verificação periódica concluída")

        except Exception as e:
            self.logger.error(f"Erro na verificação periódica: {e}")

    def _verify_notifications_file(self):
        """Verificar se o arquivo Notifications.json existe e está correto"""
        try:
            scum_path = self.scum_config_path
            notifications_file = self.config.get(
                "notifications_file", "Notifications.json"
            )
            full_path = f"{scum_path}/{notifications_file}".replace("/", "\\")

            # Verificar se arquivo existe
            if not os.path.exists(full_path):
                self.logger.warn(
                    f"Arquivo Notifications.json não encontrado: {full_path}"
                )
                self._recreate_restart_notifications("Arquivo não encontrado")
                return False

            # Verificar se arquivo está válido
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if not data.get("Notifications"):
                    self.logger.warn(
                        "Arquivo Notifications.json está vazio ou inválido"
                    )
                    self._recreate_restart_notifications("Arquivo vazio/inválido")
                    return False

                # Verificar se tem notificações de restart
                notifications = data.get("Notifications", [])
                restart_notifications = [
                    n for n in notifications if "RESTART" in n.get("message", "")
                ]

                if not restart_notifications:
                    # Verificar se está dentro da janela de 12 minutos antes de recriar
                    next_restart = self._get_next_restart_time()
                    if next_restart:
                        now = datetime.now()
                        time_until_restart = (next_restart - now).total_seconds()

                        if (
                            0 < time_until_restart < 720
                        ):  # Dentro da janela de 12 minutos
                            self.logger.warn(
                                "Nenhuma notificação de restart encontrada no arquivo - recriando (dentro da janela de 12 minutos)"
                            )
                            result = self.create_restart_notifications(
                                next_restart.strftime("%H:%M"), next_restart
                            )
                            if result["success"]:
                                return True
                            else:
                                self.logger.error(
                                    f"Falha ao recriar notificações: {result.get('reason', 'Erro desconhecido')}"
                                )
                                return False
                        else:
                            self.logger.info(
                                f"Nenhuma notificação de restart encontrada, mas fora da janela de 12 minutos ({time_until_restart/60:.1f} min) - aguardando"
                            )
                            return True  # Não recriar, apenas aguardar
                    else:
                        self.logger.warn(
                            "Nenhuma notificação de restart encontrada e não foi possível determinar próximo restart"
                        )
                        return False

                self.logger.info(
                    f"Arquivo Notifications.json verificado: {len(notifications)} notificações, {len(restart_notifications)} de restart"
                )
                return True

            except json.JSONDecodeError as e:
                self.logger.error(f"Arquivo Notifications.json corrompido: {e}")
                self._recreate_restart_notifications("Arquivo corrompido")
                return False

        except Exception as e:
            self.logger.error(f"Erro ao verificar arquivo Notifications.json: {e}")
            return False

    def _check_time_change(self):
        """Verificar se o horário do sistema mudou significativamente"""
        try:
            current_time = datetime.now()

            if self.last_time_check is None:
                self.last_time_check = current_time
                return

            # Calcular diferença de tempo
            time_diff = abs((current_time - self.last_time_check).total_seconds())

            # Se mudou mais de 1 hora, pode ter sido mudança manual do horário
            if time_diff > 3600:  # 1 hora
                self.logger.warn(
                    f"Mudança significativa de horário detectada: {time_diff/3600:.1f} horas"
                )
                self._recreate_restart_notifications("Mudança de horário detectada")

            self.last_time_check = current_time

        except Exception as e:
            self.logger.error(f"Erro ao verificar mudança de horário: {e}")

    def _check_restart_notifications(self):
        """Verificar se as notificações de restart estão corretas para o próximo restart"""
        try:
            next_restart = self._get_next_restart_time()
            if not next_restart:
                return

            # Verificar se já passou do horário de criar notificações
            now = datetime.now()
            time_until_restart = (next_restart - now).total_seconds()

            # NOVA LÓGICA: Recriar notificações APENAS 12 minutos antes do restart
            if 0 < time_until_restart < 720:  # Entre 0 e 12 minutos (720 segundos)
                scum_path = self.scum_config_path
                notifications_file = self.config.get(
                    "notifications_file", "Notifications.json"
                )
                full_path = f"{scum_path}/{notifications_file}".replace("/", "\\")

                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    notifications = data.get("Notifications", [])
                    restart_notifications = [
                        n for n in notifications if "RESTART" in n.get("message", "")
                    ]

                    # Verificar se há mensagem personalizada recente (criada nos últimos 5 minutos)
                    has_recent_custom = self._has_recent_custom_notification(
                        notifications, now
                    )

                    if not restart_notifications:
                        if has_recent_custom:
                            self.logger.info(
                                f"Faltam {time_until_restart/60:.1f} minutos para restart, mas há mensagem personalizada recente - aguardando"
                            )
                        else:
                            self.logger.warn(
                                f"Faltam {time_until_restart/60:.1f} minutos para restart mas não há notificações - recriando"
                            )
                            result = self.create_restart_notifications(
                                next_restart.strftime("%H:%M"), next_restart
                            )
                            if not result["success"]:
                                self.logger.error(
                                    f"Falha ao recriar notificações: {result.get('reason', 'Erro desconhecido')}"
                                )
                    else:
                        self.logger.info(
                            f"Notificações de restart já existem para restart em {time_until_restart/60:.1f} minutos"
                        )
                else:
                    # Arquivo não existe, recriar notificações
                    self.logger.warn(
                        f"Arquivo de notificações não existe, recriando para restart em {time_until_restart/60:.1f} minutos"
                    )
                    result = self.create_restart_notifications(
                        next_restart.strftime("%H:%M"), next_restart
                    )
                    if not result["success"]:
                        self.logger.error(
                            f"Falha ao recriar notificações: {result.get('reason', 'Erro desconhecido')}"
                        )
            elif time_until_restart >= 720:
                # Fora da janela de 12 minutos - não fazer nada
                self.logger.debug(
                    f"Fora da janela de 12 minutos para restart: {time_until_restart/60:.1f} minutos"
                )
            else:
                # Já passou do restart - limpar notificações
                self.logger.info(f"Restart já passou, limpando notificações")
                result = self.clear_restart_notifications()
                if not result["success"]:
                    self.logger.error(
                        f"Falha ao limpar notificações: {result.get('reason', 'Erro desconhecido')}"
                    )

        except Exception as e:
            self.logger.error(f"Erro ao verificar notificações de restart: {e}")

    def _has_recent_custom_notification(
        self, notifications: List[Dict[str, Any]], current_time: datetime
    ) -> bool:
        """Verificar se há mensagem personalizada recente"""
        try:
            # Obter configuração de proteção
            protection_config = self.config.get("custom_message_protection", {})
            if not protection_config.get("enabled", True):
                return False

            protection_minutes = protection_config.get("protection_minutes", 5)
            protection_seconds = protection_minutes * 60

            for notification in notifications:
                message = notification.get("message", "")
                time_slots = notification.get("time", [])

                # Verificar se é uma mensagem personalizada (não contém 'RESTART')
                if "RESTART" not in message.upper():
                    for time_slot in time_slots:
                        try:
                            # Converter horário da notificação
                            hour, minute = map(int, time_slot.split(":"))
                            notification_time = current_time.replace(
                                hour=hour, minute=minute, second=0, microsecond=0
                            )

                            # Se a notificação é para hoje e foi criada recentemente
                            time_diff = abs(
                                (current_time - notification_time).total_seconds()
                            )

                            if time_diff < protection_seconds:
                                self.logger.info(
                                    f"Mensagem personalizada recente encontrada: '{message[:30]}...' criada há {time_diff/60:.1f} minutos (proteção: {protection_minutes}min)"
                                )
                                return True

                        except (ValueError, IndexError) as e:
                            self.logger.warn(
                                f"Erro ao processar horário {time_slot}: {e}"
                            )
                            continue

            return False

        except Exception as e:
            self.logger.error(
                f"Erro ao verificar mensagens personalizadas recentes: {e}"
            )
            return False

    def _recreate_restart_notifications(self, reason: str):
        """Recriar notificações de restart"""
        try:
            self.logger.info(f"Recriando notificações de restart: {reason}")

            # Usar o método que cria notificações corretas
            result = self.create_correct_notifications()

            if result.get("success"):
                self.logger.info("Notificações de restart recriadas com sucesso")

                # Notificar via callback se disponível
                if self.notification_callbacks:
                    for callback in self.notification_callbacks:
                        try:
                            callback(
                                "restart_notifications_recreated",
                                {
                                    "reason": reason,
                                    "next_restart": result.get("next_restart"),
                                    "count": result.get("count"),
                                },
                            )
                        except Exception as e:
                            self.logger.error(f"Erro em callback de recriação: {e}")
            else:
                self.logger.error(
                    f"Falha ao recriar notificações: {result.get('error')}"
                )

        except Exception as e:
            self.logger.error(f"Erro ao recriar notificações de restart: {e}")

    def _verification_loop(self):
        """Loop de verificação automática a cada 1 minuto"""
        while self.enabled:
            try:
                self.periodic_verification()
            except Exception as e:
                self.logger.error(f"Erro no loop de verificação: {e}")

            self._stop_event.wait(timeout=60)
            self._stop_event.clear()

    def create_restart_notifications(
        self, restart_time: str, restart_datetime: datetime
    ) -> Dict[str, Any]:
        """Criar notificações de restart"""
        try:
            if not self.can_send_notification("restart"):
                return {
                    "success": False,
                    "message": "Cooldown ativo para notificações de restart",
                }

            # Carregar template de restart
            template = self._load_template("restart")
            if not template:
                self.logger.error("Template de restart não encontrado")
                return {"success": False, "message": "Template não encontrado"}

            notifications = []

            # Processar template para horários específicos
            for notification_template in template.get("notifications", []):
                notification_time = self._calculate_notification_time(
                    notification_template["time"], restart_datetime
                )

                if notification_time:
                    notification = self.scum_notifier.create_notification(
                        message=notification_template["message"],
                        time_slots=[notification_time],
                        duration=notification_template["duration"],
                        color=notification_template["color"],
                    )
                    notifications.append(notification)

            # Salvar notificações no SCUM com prioridade máxima
            result = self.scum_notifier.save_notifications(
                notifications, self.PRIORITIES["RESTART"]
            )

            if result["success"]:
                self.register_notification_sent("restart")
                self.last_restart_notifications = restart_time

                self.logger.info(
                    "Notificações de restart criadas",
                    {
                        "restart_time": restart_time,
                        "notifications_count": len(notifications),
                    },
                )

                # Notificar callbacks
                self._notify_callbacks(
                    "restart_notifications_created",
                    {
                        "restart_time": restart_time,
                        "notifications_count": len(notifications),
                    },
                )
            else:
                self.logger.error(
                    "Falha ao salvar notificações de restart",
                    {
                        "error": result.get("reason", "Erro desconhecido"),
                        "blocked": result.get("blocked", False),
                    },
                )

            return result

        except Exception as e:
            self.logger.error(
                "Erro ao criar notificações de restart", {"error": str(e)}
            )
            return {"success": False, "error": str(e)}

    def clear_restart_notifications(self) -> Dict[str, Any]:
        """Limpar notificações de restart"""
        try:
            result = self.scum_notifier.clear_notifications()

            if result["success"]:
                self.last_restart_notifications = None
                self.logger.info("Notificações de restart limpas")

                # Notificar callbacks
                self._notify_callbacks("restart_notifications_cleared", {})

            return result

        except Exception as e:
            self.logger.error(
                "Erro ao limpar notificações de restart", {"error": str(e)}
            )
            return {"success": False, "error": str(e)}

    def send_custom_notification(
        self, message: str, duration: int = 15, color: str = "255-255-255"
    ) -> Dict[str, Any]:
        """Enviar notificação personalizada (comportamento igual ao projeto original)"""
        try:
            if not self.can_send_notification("custom"):
                return {
                    "success": False,
                    "message": "Cooldown ativo para notificações personalizadas",
                }

            # Usar o método que replica exatamente o comportamento do projeto original
            result = self.send_custom_notification_original_behavior(
                message=message, duration=duration, color=color
            )

            if result["success"]:
                self.register_notification_sent("custom")
                self.logger.info(
                    "Notificação personalizada enviada",
                    {"message": message, "color": color, "duration": duration},
                )

                # Notificar callbacks
                self._notify_callbacks(
                    "custom_notification_sent",
                    {"message": message, "color": color, "duration": duration},
                )

            return result

        except Exception as e:
            self.logger.error(
                "Erro ao enviar notificação personalizada", {"error": str(e)}
            )
            return {"success": False, "error": str(e)}

    def send_custom_notification_original_behavior(
        self, message: str, duration: int = 15, color: str = "255-255-255"
    ) -> Dict[str, Any]:
        """Enviar notificação personalizada com comportamento idêntico ao projeto original"""
        try:

            # Comportamento exato do projeto original:
            # 1. Pegar horário atual
            # 2. Adicionar 2 minutos de offset
            # 3. Criar notificação simples
            # 4. Salvar diretamente no arquivo (sem verificações de bloqueio)

            current_time = datetime.now()
            offset_time = current_time + timedelta(minutes=2)
            time_str = offset_time.strftime("%H:%M")

            self.logger.info(
                f"Enviando notificação personalizada - Horário atual: {current_time.strftime('%H:%M')}, Offset: {time_str}"
            )

            # Criar notificação no formato exato do projeto original
            notification = {
                "day": "Everyday",
                "time": [time_str],
                "duration": duration,
                "color": color,
                "message": message,
            }

            # Salvar diretamente no arquivo (sem verificações de bloqueio)
            scum_notifications = {"Notifications": [notification]}

            # Usar o mesmo caminho do SCUM Notifier
            scum_path = self.scum_config_path
            notifications_file = self.config.get(
                "notifications_file", "Notifications.json"
            )
            full_path = f"{scum_path}/{notifications_file}".replace("/", "\\")

            # Criar diretório se não existir
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Salvar arquivo (comportamento idêntico ao projeto original)
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(scum_notifications, f, indent=2, ensure_ascii=False)

            self.logger.info(
                "Notificação personalizada salva com comportamento original",
                {
                    "message": message,
                    "color": color,
                    "duration": duration,
                    "time": time_str,
                    "path": full_path,
                    "original_time": current_time.strftime("%H:%M"),
                    "offset_time": time_str,
                },
            )

            return {
                "success": True,
                "message": "Notificação enviada com sucesso",
                "data": {
                    "message": message,
                    "color": color,
                    "duration": duration,
                    "time": time_str,
                    "path": full_path,
                },
            }

        except Exception as e:
            self.logger.error(
                f"Erro ao enviar notificação personalizada (comportamento original): {e}"
            )
            return {"success": False, "error": str(e)}

    def _calculate_notification_time(
        self, time_type: str, restart_datetime: datetime
    ) -> Optional[str]:
        """Calcular horário da notificação"""
        try:
            if time_type == "10_min_before":
                return (restart_datetime - timedelta(minutes=10)).strftime("%H:%M")
            elif time_type == "5_min_before":
                return (restart_datetime - timedelta(minutes=5)).strftime("%H:%M")
            elif time_type == "4_min_before":
                return (restart_datetime - timedelta(minutes=4)).strftime("%H:%M")
            elif time_type == "3_min_before":
                return (restart_datetime - timedelta(minutes=3)).strftime("%H:%M")
            elif time_type == "2_min_before":
                return (restart_datetime - timedelta(minutes=2)).strftime("%H:%M")
            elif time_type == "1_min_before":
                return (restart_datetime - timedelta(minutes=1)).strftime("%H:%M")
            else:
                return None
        except Exception as e:
            self.logger.error(
                "Erro ao calcular horário da notificação", {"error": str(e)}
            )
            return None

    def _load_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Carregar template de notificação"""
        try:
            template_path = self.templates_path / f"{template_name}.json"
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                self.logger.error(f"Template {template_name} não encontrado")
                return None
        except Exception as e:
            self.logger.error(
                f"Erro ao carregar template {template_name}", {"error": str(e)}
            )
            return None

    def can_send_notification(self, notification_type: str) -> bool:
        """Verificar se pode enviar notificação (cooldown)"""
        cooldown = self.cooldowns["cooldowns"].get(notification_type, 0)
        last_sent = self.cooldowns["last_sent"].get(notification_type)

        if cooldown == 0:
            return True  # Sem cooldown

        if not last_sent:
            return True  # Primeira vez

        try:
            last_sent_time = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
            time_since_last = datetime.now().timestamp() - last_sent_time.timestamp()
            return time_since_last >= cooldown
        except Exception as e:
            self.logger.error("Erro ao verificar cooldown", {"error": str(e)})
            return True  # Em caso de erro, permitir envio

    def register_notification_sent(self, notification_type: str):
        """Registrar envio de notificação"""
        self.cooldowns["last_sent"][notification_type] = datetime.now().isoformat()
        self._save_cooldowns(self.cooldowns)

    def clear_restart_notifications(self) -> Dict[str, Any]:
        """Limpar notificações de restart"""
        try:
            result = self.scum_notifier.clear_notifications()

            if result["success"]:
                self.last_restart_notifications = None

                # Notificar callbacks
                for callback in self.notification_callbacks:
                    try:
                        callback("restart_notifications_cleared", {})
                    except Exception as e:
                        self.logger.error(f"Erro no callback: {e}")

                return {"success": True, "message": "Notificações de restart limpas"}
            else:
                return {
                    "success": False,
                    "reason": f"Falha ao limpar notificações: {result.get('error', 'Erro desconhecido')}",
                }

        except Exception as e:
            self.logger.error(
                "Erro ao limpar notificações de restart", {"error": str(e)}
            )
            return {"success": False, "reason": str(e)}

    def create_restart_notifications(
        self,
        restart_time: str,
        restart_datetime: datetime,
        gestao_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Criar notificações de restart in-game

        Args:
            restart_time: Horário do restart no formato "HH:MM"
            restart_datetime: Objeto datetime do restart
            gestao_message: Mensagem opcional do Gestão para incluir 8 minutos antes do restart
        """
        try:
            # Carregar template de restart
            template = self._load_template("restart")
            if not template:
                return {
                    "success": False,
                    "reason": "Template de restart não encontrado",
                }

            # Limpar notificações existentes
            self.scum_notifier.clear_notifications()

            # Criar notificações baseadas no template
            notifications = []
            for notification_config in template.get("notifications", []):
                time_type = notification_config.get("time")
                duration = notification_config.get("duration", 10)
                color = notification_config.get("color", "255-180-50")
                message = notification_config.get("message", "")

                # Calcular horário da notificação
                notification_time = self._calculate_notification_time(
                    time_type, restart_datetime
                )
                if notification_time:
                    notifications.append(
                        {
                            "day": "Everyday",
                            "time": [notification_time],
                            "duration": duration,
                            "color": color,
                            "message": message,
                        }
                    )

            # Adicionar notificação do Gestão se existir (8 minutos antes do restart)
            if gestao_message:

                notification_time_8min = restart_datetime - timedelta(minutes=8)
                notification_time_str = notification_time_8min.strftime("%H:%M")

                gestao_notification = {
                    "day": "Everyday",
                    "time": [notification_time_str],
                    "duration": 10,  # Mesma duração das outras
                    "color": "150-255-150",  # Verde claro - positivo/benefício
                    "message": gestao_message,  # Mensagem pura do Gestão
                }

                notifications.append(gestao_notification)

                if self.logger:
                    self.logger.info(
                        f"Notificação do Gestão adicionada para {notification_time_str} (8 minutos antes do restart)"
                    )

            # Ordenar todas as notificações por horário (importante para ordem correta no Notifications.json)
            notifications.sort(key=lambda n: n["time"][0])

            # Salvar notificações no SCUM
            if notifications:
                result = self.scum_notifier.save_notifications(
                    notifications, priority=self.PRIORITIES["RESTART"]
                )

                if result["success"]:
                    self.last_restart_notifications = restart_time

                    # Notificar callbacks
                    for callback in self.notification_callbacks:
                        try:
                            callback(
                                "restart_notifications_created",
                                {
                                    "restart_time": restart_time,
                                    "count": len(notifications),
                                    "notifications": notifications,
                                },
                            )
                        except Exception as e:
                            self.logger.error(f"Erro no callback: {e}")

                    return {
                        "success": True,
                        "count": len(notifications),
                        "notifications": notifications,
                    }
                else:
                    return {
                        "success": False,
                        "reason": f"Falha ao salvar notificações: {result.get('error', 'Erro desconhecido')}",
                    }
            else:
                return {"success": False, "reason": "Nenhuma notificação criada"}

        except Exception as e:
            self.logger.error(
                "Erro ao criar notificações de restart", {"error": str(e)}
            )
            return {"success": False, "reason": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Obter status do sistema de notificações"""
        try:
            scum_status = self.scum_notifier.get_status()

            return {
                "enabled": self.enabled,
                "is_running": self.is_running,
                "check_interval": self.check_interval,
                "restart_protection_window": self.restart_protection_window,
                "last_restart_notifications": self.last_restart_notifications,
                "cooldowns": self.cooldowns,
                "scum_notifier": scum_status,
                "templates_path": str(self.templates_path),
                "config_path": str(self.config_path),
            }

        except Exception as e:
            self.logger.error("Erro ao obter status", {"error": str(e)})
            return {"enabled": False, "error": str(e)}
