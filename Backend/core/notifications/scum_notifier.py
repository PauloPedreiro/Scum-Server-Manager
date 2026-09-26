#!/usr/bin/env python3
"""
SCUM Notifier - Interface com o sistema de notificações do SCUM
"""

import os
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils.logger import StructuredLogger


class SCUMNotifier:
    """Interface para enviar notificações in-game para o SCUM"""

    def __init__(self, config: Dict[str, Any], logger: StructuredLogger = None):
        self.config = config
        self.logger = logger or StructuredLogger()

        # Caminhos do SCUM
        self.scum_config_path = config.get(
            "scum_config_path", "C:/Servers/Scum/SCUM/Saved/Config/WindowsServer"
        )
        self.notifications_file = config.get("notifications_file", "Notifications.json")
        self.scum_notifications_path = (
            Path(self.scum_config_path) / self.notifications_file
        )

        # Criar diretório se não existir
        self.scum_notifications_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            "SCUMNotifier inicializado",
            {
                "scum_config_path": self.scum_config_path,
                "notifications_file": self.notifications_file,
                "full_path": str(self.scum_notifications_path),
            },
        )

    def save_notifications(
        self, notifications: List[Dict[str, Any]], priority: int = 10
    ) -> Dict[str, Any]:
        """Salvar notificações no arquivo do SCUM (sem verificações de bloqueio)"""
        try:
            self.logger.info(f"Salvando {len(notifications)} notificações no SCUM")

            # Criar estrutura de notificações do SCUM
            scum_notifications = {"Notifications": notifications}

            # Salvar no arquivo
            with open(self.scum_notifications_path, "w", encoding="utf-8") as f:
                json.dump(scum_notifications, f, indent=2, ensure_ascii=False)

            self.logger.info(
                "Notificações salvas no SCUM",
                {
                    "count": len(notifications),
                    "path": str(self.scum_notifications_path),
                    "priority": priority,
                },
            )

            return {
                "success": True,
                "count": len(notifications),
                "priority": priority,
                "path": str(self.scum_notifications_path),
            }

        except Exception as e:
            self.logger.error("Erro ao salvar notificações no SCUM", {"error": str(e)})
            return {"success": False, "error": str(e)}

    def clear_notifications(self) -> Dict[str, Any]:
        """Limpar todas as notificações"""
        try:
            empty_notifications = {"Notifications": []}

            with open(self.scum_notifications_path, "w", encoding="utf-8") as f:
                json.dump(empty_notifications, f, indent=2, ensure_ascii=False)

            self.logger.info("Notificações limpas")
            return {"success": True}

        except Exception as e:
            self.logger.error("Erro ao limpar notificações", {"error": str(e)})
            return {"success": False, "error": str(e)}

    def get_current_notifications(self) -> List[Dict[str, Any]]:
        """Obter notificações atuais"""
        try:
            existing_notifications = self._load_existing_notifications()
            return existing_notifications if existing_notifications else []

        except Exception as e:
            self.logger.error("Erro ao obter notificações atuais", {"error": str(e)})
            return []

    def _load_existing_notifications(self) -> Optional[List[Dict[str, Any]]]:
        """Carregar notificações existentes"""
        try:
            if not self.scum_notifications_path.exists():
                return None

            with open(self.scum_notifications_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("Notifications", [])

        except Exception as e:
            self.logger.error(
                "Erro ao carregar notificações existentes", {"error": str(e)}
            )
            return None

    def _get_highest_priority(self, notifications: List[Dict[str, Any]]) -> int:
        """Determinar a prioridade mais alta das notificações existentes"""
        highest_priority = 0

        for notification in notifications:
            message = notification.get("message", "")

            # Determinar prioridade baseada no conteúdo da mensagem
            if "RESTART" in message.upper():
                highest_priority = max(highest_priority, 100)  # Prioridade máxima
            elif "ADMIN" in message.upper():
                highest_priority = max(highest_priority, 50)  # Prioridade média
            else:
                highest_priority = max(highest_priority, 10)  # Prioridade baixa

        return highest_priority

    def _should_block_custom_notification(
        self,
        existing_notifications: List[Dict[str, Any]],
        new_notifications: List[Dict[str, Any]],
    ) -> bool:
        """Verificar se deve bloquear notificação personalizada baseado no horário"""
        try:

            self.logger.info(
                "Iniciando verificação de bloqueio de notificação personalizada"
            )

            # Verificar se há notificações de restart existentes
            restart_notifications = [
                n
                for n in existing_notifications
                if "RESTART" in n.get("message", "").upper()
            ]

            self.logger.info(
                f"Notificações de restart encontradas: {len(restart_notifications)}"
            )

            if not restart_notifications:
                self.logger.info("Não há notificações de restart, não bloquear")
                return False  # Não há notificações de restart, não bloquear

            # Verificar se a nova notificação é personalizada (não restart)
            new_is_custom = not any(
                "RESTART" in n.get("message", "").upper() for n in new_notifications
            )

            if not new_is_custom:
                return False  # Nova notificação também é de restart, não bloquear

            # Verificar se alguma notificação de restart está próxima (menos de 10 minutos)
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")

            self.logger.info(f"Horário atual: {current_time_str}")

            for notification in restart_notifications:
                message = notification.get("message", "")
                time_slots = notification.get("time", [])

                self.logger.info(
                    f"Verificando notificação de restart: {message[:50]}... com horários: {time_slots}"
                )

                for time_slot in time_slots:
                    try:
                        # Verificar se o horário é válido antes de converter
                        hour, minute = map(int, time_slot.split(":"))
                        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                            self.logger.warn(
                                f"Horário inválido: {time_slot}, pulando..."
                            )
                            continue

                        # Converter horário da notificação para datetime
                        notification_time = datetime.strptime(
                            f"{now.strftime('%Y-%m-%d')} {time_slot}", "%Y-%m-%d %H:%M"
                        )

                        self.logger.info(
                            f"Horário da notificação: {time_slot}, Horário atual: {current_time_str}"
                        )

                        # Se a notificação é para hoje e está próxima (menos de 12 minutos)
                        if notification_time > now:
                            time_diff = (notification_time - now).total_seconds()
                            self.logger.info(
                                f"Diferença de tempo: {time_diff/60:.1f} minutos"
                            )

                            if time_diff < 720:  # 12 minutos
                                self.logger.info(
                                    f"Notificação de restart próxima detectada: {time_slot} (em {time_diff/60:.1f} minutos)"
                                )
                                return True  # Bloquear notificação personalizada
                            else:
                                self.logger.info(
                                    f"Notificação de restart distante: {time_slot} (em {time_diff/60:.1f} minutos) - NÃO bloquear"
                                )
                        else:
                            self.logger.info(
                                f"Notificação de restart já passou: {time_slot}"
                            )
                    except ValueError as e:
                        self.logger.error(f"Erro ao converter horário {time_slot}: {e}")
                        continue

                self.logger.info(
                    "Nenhuma notificação de restart próxima encontrada (12+ minutos) - NÃO bloquear"
                )
                return False  # Não há notificações de restart próximas, não bloquear

        except Exception as e:
            self.logger.error(f"Erro ao verificar se deve bloquear notificação: {e}")
            return False  # Em caso de erro, não bloquear

    def create_notification(
        self,
        message: str,
        time_slots: List[str],
        duration: int = 15,
        color: str = "255-255-255",
    ) -> Dict[str, Any]:
        """Criar uma notificação no formato do SCUM"""
        return {
            "day": "Everyday",
            "time": time_slots,
            "duration": duration,
            "color": color,
            "message": message,
        }

    def send_custom_notification(
        self,
        message: str,
        duration: int = 15,
        color: str = "255-255-255",
        priority: int = 10,
    ) -> Dict[str, Any]:
        """Enviar notificação personalizada imediatamente"""
        try:
            # Criar horário atual com offset de 2 minutos para garantir visibilidade
            current_time = datetime.now()
            future_time = current_time.replace(
                minute=current_time.minute + 2, second=0, microsecond=0
            )
            time_str = future_time.strftime("%H:%M")

            notification = self.create_notification(
                message=message, time_slots=[time_str], duration=duration, color=color
            )

            result = self.save_notifications([notification], priority)

            if result["success"]:
                self.logger.info(
                    "Notificação personalizada enviada",
                    {
                        "message": message,
                        "color": color,
                        "duration": duration,
                        "time": time_str,
                        "priority": priority,
                    },
                )

            return result

        except Exception as e:
            self.logger.error(
                "Erro ao enviar notificação personalizada", {"error": str(e)}
            )
            return {"success": False, "error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Obter status do sistema de notificações"""
        try:
            current_notifications = self.get_current_notifications()
            highest_priority = (
                self._get_highest_priority(current_notifications)
                if current_notifications
                else 0
            )

            return {
                "enabled": True,
                "notifications_file_exists": self.scum_notifications_path.exists(),
                "current_notifications_count": len(current_notifications),
                "highest_priority": highest_priority,
                "scum_config_path": self.scum_config_path,
                "notifications_file": self.notifications_file,
                "full_path": str(self.scum_notifications_path),
            }

        except Exception as e:
            self.logger.error("Erro ao obter status", {"error": str(e)})
            return {"enabled": False, "error": str(e)}
