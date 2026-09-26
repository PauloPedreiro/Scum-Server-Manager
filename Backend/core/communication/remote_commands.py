"""
Sistema de Comandos Remotos
Processa comandos enviados pelo frontend central
"""

import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime


class RemoteCommandHandler:
    def __init__(
        self, logger, notification_manager=None, server_manager=None, scheduler=None
    ):
        self.logger = logger
        self.notification_manager = notification_manager
        self.server_manager = server_manager
        self.scheduler = scheduler

        # Callbacks para comandos
        self.command_handlers = {
            "global_message": self._handle_global_message,
            "regional_message": self._handle_regional_message,
            "server_control": self._handle_server_control,
            "scheduler_control": self._handle_scheduler_control,
            "status_request": self._handle_status_request,
            "notification_control": self._handle_notification_control,
        }

    def handle_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processar comando remoto"""
        try:
            command_type = command_data.get("type")
            if not command_type:
                return {"success": False, "error": "Tipo de comando não especificado"}

            self.logger.info(f"Comando remoto recebido: {command_type}")

            # Verificar se comando é suportado
            if command_type not in self.command_handlers:
                return {
                    "success": False,
                    "error": f"Tipo de comando não suportado: {command_type}",
                }

            # Executar comando
            handler = self.command_handlers[command_type]
            result = handler(command_data)

            self.logger.info(
                f"Comando {command_type} processado: {result.get('success', False)}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Erro ao processar comando remoto: {e}")
            return {"success": False, "error": str(e)}

    def _handle_global_message(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processar mensagem global"""
        try:
            message = command_data.get("message", "")
            duration = command_data.get("duration", 30)
            color = command_data.get("color", "255-255-100")

            if not message:
                return {"success": False, "error": "Mensagem não especificada"}

            if not self.notification_manager:
                return {"success": False, "error": "NotificationManager não disponível"}

            result = self.notification_manager.send_custom_notification(
                message=message, duration=duration, color=color
            )

            return {
                "success": result.get("success", False),
                "message": f"Mensagem global enviada: {message}",
                "data": result,
            }

        except Exception as e:
            return {"success": False, "error": f"Erro ao enviar mensagem global: {e}"}

    def _handle_regional_message(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processar mensagem regional"""
        # Por enquanto, trata como mensagem global
        return self._handle_global_message(command_data)

    def _handle_server_control(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processar controle do servidor"""
        try:
            action = command_data.get("action")  # start, stop, restart
            force = command_data.get("force", False)
            wait_timeout = command_data.get("wait_timeout", 30)

            if not self.server_manager:
                return {"success": False, "error": "ServerManager não disponível"}

            if action == "start":
                result = self.server_manager.start_server()
            elif action == "stop":
                result = self.server_manager.stop_server()
            elif action == "restart":
                result = self.server_manager.restart_server()
            else:
                return {
                    "success": False,
                    "error": f"Ação de servidor não suportada: {action}",
                }

            return {
                "success": result.get("success", False),
                "message": f"Servidor {action} executado",
                "data": result,
            }

        except Exception as e:
            return {"success": False, "error": f"Erro no controle do servidor: {e}"}

    def _handle_scheduler_control(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processar controle do scheduler"""
        try:
            action = command_data.get("action")  # start, stop, restart

            if not self.scheduler:
                return {"success": False, "error": "Scheduler não disponível"}

            if action == "start":
                result = self.scheduler.start()
            elif action == "stop":
                result = self.scheduler.stop()
            elif action == "restart":
                result = self.scheduler.restart()
            else:
                return {
                    "success": False,
                    "error": f"Ação de scheduler não suportada: {action}",
                }

            return {
                "success": result.get("success", False),
                "message": f"Scheduler {action} executado",
                "data": result,
            }

        except Exception as e:
            return {"success": False, "error": f"Erro no controle do scheduler: {e}"}

    def _handle_status_request(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processar solicitação de status"""
        try:
            status = {
                "timestamp": time.time(),
                "server": {},
                "scheduler": {},
                "notifications": {},
            }

            # Status do servidor
            if self.server_manager:
                status["server"] = self.server_manager.get_status()

            # Status do scheduler
            if self.scheduler:
                status["scheduler"] = self.scheduler.get_status()

            # Status das notificações
            if self.notification_manager:
                status["notifications"] = self.notification_manager.get_status()

            return {
                "success": True,
                "message": "Status obtido com sucesso",
                "data": status,
            }

        except Exception as e:
            return {"success": False, "error": f"Erro ao obter status: {e}"}

    def _handle_notification_control(
        self, command_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Processar controle de notificações"""
        try:
            action = command_data.get("action")  # clear, create_restart, etc.

            if not self.notification_manager:
                return {"success": False, "error": "NotificationManager não disponível"}

            if action == "clear":
                result = self.notification_manager.clear_restart_notifications()
            elif action == "create_restart":
                result = self.notification_manager.create_correct_notifications()
            else:
                return {
                    "success": False,
                    "error": f"Ação de notificação não suportada: {action}",
                }

            return {
                "success": result.get("success", False),
                "message": f"Notificação {action} executada",
                "data": result,
            }

        except Exception as e:
            return {"success": False, "error": f"Erro no controle de notificações: {e}"}

    def get_supported_commands(self) -> list:
        """Obter lista de comandos suportados"""
        return list(self.command_handlers.keys())

    def add_command_handler(self, command_type: str, handler: Callable):
        """Adicionar handler personalizado para comando"""
        self.command_handlers[command_type] = handler
        self.logger.info(
            f"Handler personalizado adicionado para comando: {command_type}"
        )
