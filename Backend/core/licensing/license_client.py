"""
Cliente HTTP para Servidor de Licenciamento
Consome endpoints fornecidos pelo servidor de gerenciamento de licenças
"""

import requests
import time
from typing import Dict, Any, Optional
from datetime import datetime


class LicenseClient:
    """Cliente HTTP para servidor de licenciamento"""

    def __init__(
        self,
        server_url: str,
        timeout: int = 45,
        retry_attempts: int = 5,
        retry_delay: int = None,
        logger=None,
        use_exponential_backoff: bool = True,
    ):
        """
        Inicializa o cliente de licenciamento

        Args:
            server_url: URL base do servidor de licenciamento
            timeout: Timeout das requisições em segundos (padrão: 45s para servidores distantes)
            retry_attempts: Número de tentativas em caso de falha (padrão: 5)
            retry_delay: Delay fixo entre tentativas em segundos (ignorado se use_exponential_backoff=True)
            logger: Logger opcional
            use_exponential_backoff: Usar backoff exponencial (2s, 5s, 10s) em vez de delay fixo
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.use_exponential_backoff = use_exponential_backoff
        self.logger = logger

        # Criar sessão HTTP
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "User-Agent": "SSM-Backend/1.0"}
        )

    def register(
        self,
        full_name: str,
        email: str,
        hardware_fingerprint: str,
        license_key: Optional[str] = None,
        phone: Optional[str] = None,
        document: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registra usuário e hardware no servidor

        Args:
            full_name: Nome completo
            email: Email do usuário
            hardware_fingerprint: Hash do hardware (gerado na hora)
            license_key: Chave de licença (opcional)
            phone: Telefone (opcional)
            document: CPF/CNPJ (opcional)

        Returns:
            Resposta do servidor
        """
        url = f"{self.server_url}/api/v1/register"

        payload = {
            "full_name": full_name,
            "email": email,
            "hardware_fingerprint": hardware_fingerprint,
        }

        if license_key:
            payload["license_key"] = license_key
        if phone:
            payload["phone"] = phone
        if document:
            payload["document"] = document

        return self._make_request("POST", url, payload)

    def validate(
        self,
        license_key: str,
        hardware_fingerprint: str,
        backend_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Valida licença com servidor (método legado - mantido para compatibilidade)

        Args:
            license_key: Chave de licença
            hardware_fingerprint: Hash do hardware (gerado na hora)
            backend_id: ID do backend (opcional)

        Returns:
            Resposta do servidor com valid/invalid
        """
        url = f"{self.server_url}/api/v1/validate"

        payload = {
            "license_key": license_key,
            "hardware_fingerprint": hardware_fingerprint,
            "timestamp": datetime.now().isoformat(),
        }

        if backend_id:
            payload["backend_id"] = backend_id

        return self._make_request("POST", url, payload)

    def validate_equipment(
        self,
        equipment_hash: str,
        hardware_list: Dict[str, Any],
        backend_id: Optional[str] = None,
        version: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Valida equipamento com servidor usando novo formato da API

        Args:
            equipment_hash: Hash único do equipamento
            hardware_list: Dicionário completo com hardware_list (formato da documentação)
            backend_id: ID do backend (opcional)
            version: Versão do SSM Backend (opcional)
            api_key: API Key para autenticação (obrigatória se máquina tiver API key cadastrada)

        Returns:
            Resposta do servidor com valid/invalid e reason
        """
        url = f"{self.server_url}/api/v1/validate"

        # Timestamp em formato ISO 8601 UTC
        timestamp = datetime.utcnow().isoformat() + "Z"

        payload = {
            "equipment_hash": equipment_hash,
            "hardware_list": hardware_list,
            "timestamp": timestamp,
        }

        if backend_id:
            payload["backend_id"] = backend_id

        if version:
            payload["version"] = version

        # Incluir API key se fornecida (obrigatória para máquinas novas)
        if api_key:
            payload["api_key"] = api_key

        return self._make_request("POST", url, payload)

    def request_revalidation_code(
        self, email: str, old_fingerprint: str
    ) -> Dict[str, Any]:
        """
        Solicita código de revalidação

        Args:
            email: Email do usuário
            old_fingerprint: Hash do hardware antigo

        Returns:
            Resposta do servidor
        """
        url = f"{self.server_url}/api/v1/revalidate/request-code"

        payload = {"email": email, "old_fingerprint": old_fingerprint}

        return self._make_request("POST", url, payload)

    def revalidate(
        self,
        email: str,
        old_fingerprint: str,
        new_fingerprint: str,
        verification_code: str,
    ) -> Dict[str, Any]:
        """
        Revalida hardware com código

        Args:
            email: Email do usuário
            old_fingerprint: Hash do hardware antigo
            new_fingerprint: Hash do hardware novo
            verification_code: Código de verificação recebido por email

        Returns:
            Resposta do servidor
        """
        url = f"{self.server_url}/api/v1/revalidate"

        payload = {
            "email": email,
            "old_fingerprint": old_fingerprint,
            "new_fingerprint": new_fingerprint,
            "verification_code": verification_code,
        }

        return self._make_request("POST", url, payload)

    def _make_request(
        self, method: str, url: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Faz requisição HTTP com retry e backoff exponencial

        Args:
            method: Método HTTP (GET, POST, etc)
            url: URL da requisição
            payload: Dados a enviar

        Returns:
            Resposta do servidor como dicionário
        """
        last_error = None
        last_exception_type = None

        for attempt in range(1, self.retry_attempts + 1):
            request_start_time = time.time()
            try:
                if self.logger:
                    self.logger.debug(
                        f"Requisição {method} {url} (tentativa {attempt}/{self.retry_attempts}, timeout: {self.timeout}s)"
                    )

                response = self.session.request(
                    method=method, url=url, json=payload, timeout=self.timeout
                )

                # Calcular latência
                latency = time.time() - request_start_time

                # Tentar parsear JSON
                try:
                    result = response.json()
                except ValueError:
                    result = {
                        "success": False,
                        "error": f"Resposta inválida do servidor: {response.status_code}",
                        "status_code": response.status_code,
                    }

                # Adicionar status code
                result["status_code"] = response.status_code

                # Log de sucesso com latência
                if self.logger and response.status_code == 200:
                    self.logger.info(
                        f"Validação bem-sucedida: {result.get('valid', 'N/A')} (latência: {latency:.2f}s)"
                    )

                return result

            except requests.exceptions.Timeout as e:
                latency = time.time() - request_start_time
                last_error = f"Timeout na requisição após {self.timeout}s"
                last_exception_type = "Timeout"
                if self.logger:
                    self.logger.warn(
                        f"Timeout na requisição (tentativa {attempt}/{self.retry_attempts}, latência: {latency:.2f}s): {e}"
                    )

            except requests.exceptions.ConnectionError as e:
                latency = time.time() - request_start_time
                last_error = f"Erro de conexão com servidor: {str(e)}"
                last_exception_type = "ConnectionError"
                if self.logger:
                    self.logger.warn(
                        f"Erro de conexão (tentativa {attempt}/{self.retry_attempts}, latência: {latency:.2f}s): {e}"
                    )

            except requests.exceptions.RequestException as e:
                latency = time.time() - request_start_time
                last_error = f"Erro na requisição HTTP: {str(e)}"
                last_exception_type = "RequestException"
                if self.logger:
                    self.logger.error(
                        f"Erro HTTP na requisição (tentativa {attempt}/{self.retry_attempts}, latência: {latency:.2f}s): {e}"
                    )

            except Exception as e:
                latency = time.time() - request_start_time
                last_error = f"Erro inesperado: {str(e)}"
                last_exception_type = "Exception"
                if self.logger:
                    self.logger.error(
                        f"Erro na requisição (tentativa {attempt}/{self.retry_attempts}, latência: {latency:.2f}s): {e}"
                    )

            # Aguardar antes de tentar novamente (exceto na última tentativa)
            if attempt < self.retry_attempts:
                if self.use_exponential_backoff:
                    # MELHORIA: Backoff exponencial melhorado: 3s, 7s, 15s, 30s, 30s, 30s, 30s
                    # Otimizado para conexões intercontinentais (Europa-Brasil)
                    if attempt == 1:
                        delay = 3.0
                    elif attempt == 2:
                        delay = 7.0
                    elif attempt == 3:
                        delay = 15.0
                    else:
                        delay = 30.0  # A partir da tentativa 4, mantém 30s
                else:
                    # Delay fixo (backward compatibility)
                    delay = self.retry_delay if self.retry_delay else 30.0

                if self.logger:
                    self.logger.debug(
                        f"Aguardando {delay:.1f}s antes da próxima tentativa..."
                    )
                time.sleep(delay)

        # Todas as tentativas falharam
        error_type_label = last_exception_type or "Unknown"
        return {
            "success": False,
            "valid": False,
            "error": f"Falha após {self.retry_attempts} tentativas ({error_type_label}): {last_error}",
            "error_type": last_exception_type,
            "status_code": 0,
        }
