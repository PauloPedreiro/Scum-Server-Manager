"""
Sistema de Heartbeat para Comunicação com Frontend Central
Gerencia comunicação periódica e status do backend
"""

import time
import threading
import requests
from typing import Dict, Any, Optional, Callable
from datetime import datetime


class HeartbeatManager:
    def __init__(self, config: Dict[str, Any], logger, backend_identity=None):
        self.config = config
        self.logger = logger
        self.backend_identity = backend_identity
        self.communication_config = config.get("communication", {})
        self.running = False
        self.thread = None
        self.last_heartbeat = None
        self.heartbeat_failures = 0
        self.max_failures = 3

        # Callbacks para eventos
        self.on_heartbeat_success: Optional[Callable] = None
        self.on_heartbeat_failure: Optional[Callable] = None

    def start_heartbeat(self):
        """Iniciar sistema de heartbeat"""
        # 🎯 SÓ INICIA SE AUTO_REGISTER = TRUE
        if not self.communication_config.get("auto_register", False):
            self.logger.info("Auto-registro desabilitado - heartbeat não iniciado")
            return

        if self.running:
            self.logger.warn("Heartbeat já está rodando")
            return

        self.running = True
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()
        self.logger.info("Sistema de heartbeat iniciado")

    def stop_heartbeat(self):
        """Parar sistema de heartbeat"""
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Sistema de heartbeat parado")

    def _heartbeat_loop(self):
        """Loop principal do heartbeat"""
        interval = self.communication_config.get("heartbeat_interval", 60)

        while self.running:
            try:
                self._send_heartbeat()
                self.heartbeat_failures = 0  # Reset contador de falhas
            except Exception as e:
                self.heartbeat_failures += 1
                self.logger.error(
                    f"Erro no heartbeat (tentativa {self.heartbeat_failures}): {e}"
                )

                if self.on_heartbeat_failure:
                    self.on_heartbeat_failure(self.heartbeat_failures, str(e))

                # Se muitas falhas, parar heartbeat
                if self.heartbeat_failures >= self.max_failures:
                    self.logger.error("Muitas falhas no heartbeat - parando sistema")
                    self.stop_heartbeat()
                    break

            time.sleep(interval)

    def _send_heartbeat(self):
        """Enviar heartbeat para o frontend central"""
        try:
            # Por enquanto, apenas log - será implementado quando houver frontend
            self.logger.info("Heartbeat enviado (simulado)")

            # Preparar dados do heartbeat
            heartbeat_data = {
                "backend_id": (
                    self.backend_identity.get_backend_id()
                    if self.backend_identity
                    else "N/A"
                ),
                "owner_id": (
                    self.backend_identity.get_owner_id()
                    if self.backend_identity
                    else None
                ),
                "status": "online",
                "timestamp": time.time(),
                "server_status": self._get_server_status(),
                "version": "1.0.0",
                "capabilities": self._get_capabilities(),
            }

            # TODO: Implementar comunicação real quando frontend estiver pronto
            # response = requests.post(
            #     f"{self.communication_config['frontend_url']}/api/backends/heartbeat",
            #     json=heartbeat_data,
            #     headers={"Authorization": f"Bearer {self.communication_config['api_key']}"},
            #     timeout=self.communication_config.get('timeout', 30)
            # )

            self.last_heartbeat = datetime.now()

            if self.on_heartbeat_success:
                self.on_heartbeat_success(heartbeat_data)

        except Exception as e:
            raise Exception(f"Falha no heartbeat: {e}")

    def _get_server_status(self) -> Dict[str, Any]:
        """Obter status do servidor para heartbeat"""
        # TODO: Integrar com ServerManager quando disponível
        return {
            "is_running": False,  # Será obtido do ServerManager
            "uptime": 0,
            "player_count": 0,
            "last_check": time.time(),
        }

    def _get_capabilities(self) -> list:
        """Obter capacidades do backend"""
        if self.backend_identity:
            return self.backend_identity.get_identity().get("capabilities", [])
        return ["server_control", "scheduler", "notifications"]

    def get_heartbeat_status(self) -> Dict[str, Any]:
        """Obter status do heartbeat"""
        return {
            "running": self.running,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
            "failures": self.heartbeat_failures,
            "interval": self.communication_config.get("heartbeat_interval", 60),
            "auto_register": self.communication_config.get("auto_register", False),
        }

    def set_heartbeat_callbacks(
        self, on_success: Callable = None, on_failure: Callable = None
    ):
        """Definir callbacks para eventos do heartbeat"""
        self.on_heartbeat_success = on_success
        self.on_heartbeat_failure = on_failure
