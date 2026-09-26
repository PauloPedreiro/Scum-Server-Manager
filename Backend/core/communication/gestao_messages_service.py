"""
Serviço para consultar mensagens agendadas do Gestão
Consulta mensagens de propaganda/anúncios que serão exibidas antes dos restarts
"""

import time
from datetime import datetime, timedelta
from typing import Optional

# IMPORTANTE: URL importada do módulo centralizado
from core.config.server_urls import GESTAO_SERVER_URL

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class GestaoMessagesService:
    """
    Serviço para consultar mensagens agendadas do Gestão

    Consulta o endpoint GET /api/v1/servers/messages do Gestão para obter
    mensagens de propaganda/anúncios que serão exibidas antes dos restarts.
    """

    def __init__(self, config: dict = None, logger=None):
        """
        Inicializar serviço de mensagens do Gestão

        Args:
            config: Configuração do sistema (opcional, não usado atualmente)
            logger: Logger estruturado (opcional)
        """
        self.logger = logger

        # URL do Gestão (hardcoded para segurança)
        self.gestao_url = GESTAO_SERVER_URL.rstrip("/")

        # Timeout para requisições (5 segundos conforme documentação)
        self.request_timeout = 5

        # Cache de mensagens (TTL de 5 minutos)
        self.cache = {
            "message": None,
            "timestamp": None,
            "ttl_seconds": 300,  # 5 minutos
        }

        if self.logger:
            self.logger.info(
                f"GestaoMessagesService inicializado (URL: {self.gestao_url})"
            )

    def get_scheduled_message(self, api_key: str) -> Optional[str]:
        """
        Obter mensagem agendada do Gestão

        Args:
            api_key: API key do servidor (formato: ssm_ + 64 caracteres hex)

        Returns:
            Texto da mensagem ou None
        """
        return None

    def _is_cache_valid(self) -> bool:
        """
        Verificar se o cache é válido (não expirou)

        Returns:
            True se cache existe e não expirou, False caso contrário
        """
        if self.cache["timestamp"] is None:
            return False

        elapsed = (datetime.now() - self.cache["timestamp"]).total_seconds()
        return elapsed < self.cache["ttl_seconds"]

    def _fetch_message_from_gestao(self, api_key: str) -> Optional[str]:
        """
        Consultar endpoint do Gestão para obter mensagem agendada

        Faz GET /api/v1/servers/messages?api_key=...

        Tratamento de erros:
        - Timeout: retorna None (log warning)
        - Erros HTTP (400, 404, 500): retorna None (log warning/error)
        - ConnectionError: retorna None (log warning)
        - Qualquer exceção: retorna None (log error)

        NUNCA lança exceção - sempre retorna None em caso de erro.

        Args:
            api_key: API key do servidor

        Returns:
            Texto da mensagem ou None
        """
        try:
            url = f"{self.gestao_url}/api/v1/servers/messages"
            params = {"api_key": api_key}

            if self.logger:
                api_key_preview = (
                    f"{api_key[:10]}...{api_key[-5:]}" if len(api_key) > 15 else "***"
                )
                self.logger.debug(
                    f"Consultando mensagem do Gestão (api_key: {api_key_preview})"
                )

            response = requests.get(
                url,
                params=params,
                timeout=self.request_timeout,
                headers={"Content-Type": "application/json"},
            )

            # Verificar status code
            if response.status_code == 200:
                try:
                    data = response.json()
                    message = data.get("message")

                    # Retornar None se message for None (sem mensagem ativa)
                    if message is None:
                        if self.logger:
                            self.logger.debug(
                                "Gestão retornou null - nenhuma mensagem ativa"
                            )
                        return None

                    # Validar que message é string
                    if isinstance(message, str):
                        return message
                    else:
                        if self.logger:
                            self.logger.warn(
                                f"Formato de mensagem inválido (esperado string, recebido {type(message)})"
                            )
                        return None

                except (ValueError, AttributeError) as e:
                    if self.logger:
                        self.logger.error(
                            f"Erro ao parsear resposta JSON do Gestão: {e}"
                        )
                    return None

            elif response.status_code == 400:
                # API key inválida ou ausente
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "Erro de validação")
                except (ValueError, AttributeError):
                    error_detail = "Erro de validação (400)"

                if self.logger:
                    self.logger.warn(
                        f"Erro 400 ao consultar mensagem do Gestão: {error_detail}"
                    )
                return None

            elif response.status_code == 404:
                # Servidor não encontrado ou inativo
                if self.logger:
                    self.logger.warn(
                        "Servidor não encontrado ou inativo no Gestão (404)"
                    )
                return None

            elif response.status_code == 500:
                # Erro interno do servidor
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "Erro interno do servidor")
                except (ValueError, AttributeError):
                    error_detail = "Erro interno do servidor (500)"

                if self.logger:
                    self.logger.error(
                        f"Erro 500 ao consultar mensagem do Gestão: {error_detail}"
                    )
                return None

            else:
                # Outro status code não esperado
                if self.logger:
                    self.logger.warn(
                        f"Status code inesperado ao consultar mensagem do Gestão: {response.status_code}"
                    )
                return None

        except requests.exceptions.Timeout:
            if self.logger:
                self.logger.warn(
                    f"Timeout ao consultar mensagem do Gestão (timeout: {self.request_timeout}s)"
                )
            return None

        except requests.exceptions.ConnectionError:
            if self.logger:
                self.logger.warn(
                    "Erro de conexão ao consultar mensagem do Gestão (servidor offline?)"
                )
            return None

        except Exception as e:
            # Qualquer outra exceção - nunca interromper o restart
            if self.logger:
                try:
                    self.logger.error(
                        f"Erro inesperado ao consultar mensagem do Gestão: {e}"
                    )
                except:
                    # Se até o logger falhar, não fazer nada (nunca interromper)
                    pass
            return None
