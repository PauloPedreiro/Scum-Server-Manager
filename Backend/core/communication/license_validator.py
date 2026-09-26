"""
Sistema de Validação de Licença
Valida licença do backend com servidor de licenciamento
Integra com hardware fingerprint e cliente HTTP
"""

import os
import time
import threading
import requests
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta

# Constantes de segurança - NÃO ALTERAR
# Estes valores são hardcoded para prevenir manipulação via config.json
VALIDATION_INTERVAL_SECONDS = 14400  # 4 horas

# IMPORTANTE: URL importada do módulo centralizado
from core.config.server_urls import LICENSE_SERVER_URL

# Importar novos módulos de licenciamento
try:
    from core.licensing.hardware_fingerprint import HardwareFingerprint
    from core.licensing.license_client import LicenseClient
    from core.licensing.license_cache import LicenseCache

    LICENSING_AVAILABLE = True
except ImportError:
    LICENSING_AVAILABLE = False
    HardwareFingerprint = None
    LicenseClient = None
    LicenseCache = None


class LicenseValidator:
    def __init__(
        self, config: Dict[str, Any], logger, backend_identity=None, path_helper=None
    ):
        self.config = config
        self.logger = logger
        self.backend_identity = backend_identity
        self.path_helper = path_helper
        self.communication_config = config.get("communication", {})
        self.license_config = self.communication_config.get("license_validation", {})

        # Configuração de licenciamento
        self.licensing_config = config.get("licensing", {})
        # Segurança: sempre habilitado independente do config.json
        self.licensing_enabled = False

        # Estado da validação
        self.last_validation = None
        self.validation_failures = 0
        self.is_valid = True
        self.last_reason = None  # Último motivo de falha
        self.last_message = None  # Última mensagem de validação
        self.blocked = False  # Estado de bloqueio efetivo

        # Callbacks para eventos
        self.on_license_valid: Optional[Callable] = None
        self.on_license_invalid: Optional[Callable] = None
        self.on_hardware_changed: Optional[Callable] = None

        # Inicializar módulos de licenciamento se disponíveis
        self.hardware_fingerprint = None
        self.license_client = None
        self.license_cache = None

        if LICENSING_AVAILABLE and self.licensing_enabled:
            self._init_licensing_modules()

    def _get_license_server_url(self) -> str:
        """
        Obter URL do servidor de licenciamento do módulo centralizado

        Returns:
            str: URL do servidor de licenciamento
        """
        return LICENSE_SERVER_URL

    def _init_licensing_modules(self):
        """Inicializar módulos de licenciamento"""
        try:
            # Hardware Fingerprint
            self.hardware_fingerprint = HardwareFingerprint(logger=self.logger)

            # License Cache
            data_dir = "data"
            db_path = None
            if self.path_helper:
                db_path = self.path_helper.get_ssm_db_path()

            self.license_cache = LicenseCache(
                data_dir=data_dir, db_path=db_path, logger=self.logger
            )

            # License Client - buscar URL dinamicamente do main.py se disponível
            server_url = self._get_license_server_url()
            # SEGURANÇA: Timeouts e retries hardcodados (otimizados para servidores distantes)
            # MELHORIA: Aumentado timeout para 90s e retry para 7 tentativas para conexões intercontinentais
            self.license_client = LicenseClient(
                server_url=server_url,
                timeout=90,  # 90 segundos (aumentado de 45s para suportar conexões Europa-Brasil)
                retry_attempts=7,  # 7 tentativas (aumentado de 5 para maior robustez)
                retry_delay=30,  # Ignorado (usa backoff exponencial)
                use_exponential_backoff=True,  # Backoff exponencial: 3s, 7s, 15s, 30s, 30s, 30s, 30s
                logger=self.logger,
            )
            self.logger.info(
                f"Módulos de licenciamento inicializados (servidor: {server_url})"
            )

        except Exception as e:
            self.logger.error(f"Erro ao inicializar módulos de licenciamento: {e}")
            self.licensing_enabled = False

    def validate_license(self, license_key: str = None, owner_id: str = None) -> bool:
        """
        Validar licença com servidor de licenciamento

        Args:
            license_key: Chave de licença (opcional)
            owner_id: ID do proprietário (opcional)
        """
        try:
            # SEGURANÇA: Validação sempre ativa (não pode ser desabilitada via config.json)
            # Sem período de graça - tratar como inválida imediatamente
            self.is_valid = True
            self.blocked = False
            self.licensing_enabled = False
            return True
        except Exception as e:
            self.logger.error(f"Erro na validação de licença: {e}")
            self.is_valid = True
            return True

    def _validate_with_hardware_fingerprint(
        self, license_key: Optional[str] = None
    ) -> bool:
        """
        Validar licença usando hardware fingerprint (novo formato da API)

        Args:
            license_key: Chave de licença (opcional)
        """
        try:
            # 1. SEMPRE gerar hash do hardware atual (equipment_hash)
            # SEGURANÇA: Hash sempre gerado em memória, nunca armazenado
            current_hash, components = self.hardware_fingerprint.generate()
            self.logger.info(f"Equipment hash gerado: {current_hash[:16]}...")
            self.logger.info(
                f"🔑 VALIDAÇÃO PERIÓDICA: Hash completo (64 chars): {current_hash} (comprimento: {len(current_hash)})"
            )

            # 2. Verificar cache de validação
            # SEGURANÇA: Cache TTL hardcoded (4 horas)
            cache_ttl = 14400  # 4 horas
            if self.license_cache.is_validation_cached(cache_ttl):
                self.logger.debug("Usando cache de validação")
                return True

            # 3. Coletar hardware_list completo (formato da documentação)
            hardware_list = self.hardware_fingerprint.get_hardware_list()

            # 4. Obter backend_id e version
            backend_id = None
            if self.backend_identity:
                backend_id = self.backend_identity.get_backend_id()

            from version import VERSION

            version = VERSION

            # 5. Obter API key do config (se existir)
            api_key = self.licensing_config.get(
                "gestao_api_key"
            ) or self.licensing_config.get("api_key")

            # 5.5. Descriptografar API key se estiver criptografada
            if api_key:
                try:
                    from core.security.credential_encryption import decrypt_credential

                    api_key = decrypt_credential(api_key, logger=self.logger)
                except Exception as e:
                    self.logger.warn(
                        f"Erro ao descriptografar API key (pode estar em texto plano): {e}"
                    )

            # 6. Verificar se API key está faltando (pode ser obrigatória no servidor)
            if not api_key or api_key.strip() == "":
                error_msg = "API Key não configurada. Configure a API Key no config.json na seção 'licensing' (gestao_api_key)."
                self.logger.error(error_msg)
                self.is_valid = False
                return False

            # 7. Validar com servidor usando novo formato
            # SEGURANÇA: Sempre usar current_hash (nunca armazenado)
            response = self.license_client.validate_equipment(
                equipment_hash=current_hash,  # ✅ SEMPRE hash atual gerado em memória
                hardware_list=hardware_list,  # ✅ Lista completa de hardware
                backend_id=backend_id,
                version=version,
                api_key=api_key,  # Incluir API key se disponível
            )

            # 8. Processar resposta usando mesma lógica da validação inicial
            # Verificar resposta (MESMA LÓGICA DA VALIDAÇÃO INICIAL)
            status_code = response.get("status_code", 200)
            has_error = response.get("error") is not None
            success = response.get("success")
            error_type = response.get(
                "error_type"
            )  # Tipo de erro (Timeout, ConnectionError, etc)

            # PRIORIDADE 1: status_code = 0 = erro de conexão/rede
            if status_code == 0:
                error_msg = response.get(
                    "error", "Erro de conexão com servidor de licenciamento"
                )
                self.logger.error(
                    f"Erro de rede detectado na validação: {error_msg} (tipo: {error_type})"
                )

                # SEGURANÇA: Grace period APENAS para erros de rede (não para licença inválida)
                # Verificar se cache ainda é válido (última validação < 4 horas)
                cache_ttl = 14400  # 4 horas
                if self.license_cache.is_validation_cached(cache_ttl):
                    self.logger.warn(
                        f"Erro de rede, mas cache ainda válido. "
                        f"Permitindo continuar operação. Nova tentativa será realizada pela validação periódica."
                    )
                    # Manter is_valid como True se já estava válido (usa cache)
                    # Não retornar False aqui, permitir que continue usando cache
                    if self.is_valid:
                        return True
                    else:
                        # Se não estava válido, não pode usar cache (primeira validação falhou)
                        self.is_valid = False
                        return False
                else:
                    # Cache expirado + erro de rede = não pode continuar sem validação
                    self.logger.error(
                        f"Erro de rede E cache expirado. "
                        f"Não é possível continuar sem validação válida. Bloqueando backend."
                    )
                    self.is_valid = False
                    return False

            # PRIORIDADE 2: success = False = erro
            if success is False:
                error_msg = response.get("error", "Erro na validação")
                self.logger.error(
                    f"Erro na resposta do servidor (success=False): {error_msg}"
                )
                self.is_valid = False
                return False

            # PRIORIDADE 3: campo 'error' presente = erro
            if has_error:
                error_msg = response.get("error", "Erro na validação")
                self.logger.error(f"Campo 'error' presente na resposta: {error_msg}")
                self.is_valid = False
                return False

            # PRIORIDADE 4: status_code != 200 = erro (exceto 422 que é tratado separadamente)
            if status_code != 200:
                # Verificar se é erro de API key (422)
                if status_code == 422:
                    error_text = str(response.get("error", "")).lower()
                    message_text = str(response.get("message", "")).lower()
                    response_text = str(response).lower()

                    # Verificar se há menção a API key na resposta
                    if (
                        "api" in error_text
                        or "api" in message_text
                        or "api_key" in response_text
                        or "api key" in response_text
                    ):
                        error_msg = "API Key inválida ou não fornecida. Configure a API Key no config.json na seção 'licensing' (gestao_api_key)."
                        self.logger.error(f"Erro 422: {error_msg}")
                        self.is_valid = False
                        return False

                error_msg = (
                    f"Resposta inesperada do servidor (status_code={status_code})"
                )
                self.logger.error(f"Status code inválido: {status_code}")
                self.is_valid = False
                return False

            # PRIORIDADE 5: Verificar campo 'valid'
            is_valid = response.get("valid")
            if is_valid is None:
                error_msg = "Resposta do servidor não contém campo 'valid'"
                self.logger.error(
                    f"Resposta inválida: campo 'valid' ausente. Resposta completa: {response}"
                )
                self.is_valid = False
                return False

            # 9. Processar resposta válida
            if is_valid is True:
                # Válido - salvar apenas resultado (não o hash)
                # SEGURANÇA: Hash não é armazenado (nem arquivo, nem banco)
                # Auditoria é feita no servidor (que recebe hash a cada validação)
                self.license_cache.save_validation_result(response)
                self._handle_valid_license(response)
                return True
            else:
                # Inválido - processar reason e bloquear
                reason = response.get("reason", "unknown")
                message = response.get("message", "Licença inválida")
                self.logger.error(f"Validação falhou: {reason} - {message}")
                self._handle_invalid_license_new_format(reason, message, response)
                return False

        except Exception as e:
            self.logger.error(f"Erro na validação com hardware fingerprint: {e}")
            # Sem período de graça - tratar como inválida imediatamente
            self.is_valid = False
            return False

    def _validate_legacy(
        self, license_key: Optional[str] = None, owner_id: Optional[str] = None
    ) -> bool:
        """
        Validação legada (sistema antigo) - DESATIVADO POR SEGURANÇA

        Este método foi desativado para prevenir bypass do sistema de licenciamento.
        Módulos de licenciamento (hardware_fingerprint e license_client) são obrigatórios.
        """
        error_msg = "Sistema legado não suportado. Módulos de licenciamento devem estar disponíveis."
        self.logger.error(f"ERRO CRÍTICO DE SEGURANÇA: {error_msg}")
        self.logger.error(
            "Tentativa de usar sistema legado bloqueada. Aplicação requer validação com servidor."
        )
        self.is_valid = False
        return False

    def _handle_valid_license(self, license_data: Dict[str, Any]):
        """Processar licença válida"""
        self.is_valid = True
        self.validation_failures = 0
        self.last_validation = datetime.now()
        self.last_reason = None
        self.last_message = license_data.get("message", "Licença válida")

        self.logger.info(f"Licença válida: {license_data.get('license_type', 'N/A')}")

        if self.on_license_valid:
            self.on_license_valid(license_data)

    def _handle_invalid_license(self, reason: str):
        """Processar licença inválida (método legado)"""
        self.is_valid = False
        self.validation_failures += 1

        self.logger.warn(f"Licença inválida: {reason}")

        if self.on_license_invalid:
            self.on_license_invalid(reason)

    def _handle_invalid_license_new_format(
        self, reason: str, message: str, response: Dict[str, Any]
    ):
        """Processar licença inválida (novo formato da API)"""
        self.is_valid = False
        self.validation_failures += 1
        self.last_reason = reason
        self.last_message = message

        self.logger.error(f"Licença inválida - Reason: {reason}, Message: {message}")

        # Tratamento específico por reason
        if reason == "not_registered":
            self.logger.error("Equipamento não cadastrado. Cadastre no painel web.")
        elif reason == "hardware_changed":
            self.logger.error("Hardware mudou. Requer revalidação no painel web.")
        elif reason == "expired":
            expired_at = response.get("expired_at", "N/A")
            self.logger.error(
                f"Licença expirada em {expired_at}. Renove no painel administrativo."
            )
        elif reason == "license_inactive":
            self.logger.error("Licença não encontrada ou inativa.")
        elif reason == "invalid_timestamp":
            server_time = response.get("server_time", "N/A")
            self.logger.error(
                f"Timestamp inválido. Servidor: {server_time}. Sincronize o relógio."
            )
        else:
            self.logger.error(f"Licença inválida: {message}")

        # SEGURANÇA: Sempre bloquear quando licença inválida (hardcoded)
        self._block_backend(reason, message)

        if self.on_license_invalid:
            self.on_license_invalid(reason)

    def _block_backend(self, reason: str, message: str):
        """Bloquear backend quando licença inválida"""
        self.is_valid = False
        self.blocked = True
        self.last_reason = reason
        self.last_message = message
        self.logger.critical(
            f"BLOQUEANDO BACKEND - Reason: {reason}, Message: {message}"
        )
        self.logger.critical(
            "Backend bloqueado: APIs responderão 503 e o processo será encerrado em 2s."
        )

        # Encerrar o backend para parar serviços e schedulers
        def _shutdown():
            try:
                time.sleep(2)
            except Exception:
                pass
            os._exit(1)

        threading.Thread(
            target=_shutdown, daemon=True, name="LicenseBlockShutdown"
        ).start()

    def should_validate_now(self) -> bool:
        """Verificar se deve validar agora"""
        # SEGURANÇA: Validação sempre ativa quando licensing está habilitado
        return False

    def get_license_status(self) -> Dict[str, Any]:
        """Obter status da licença"""
        return {
            "is_valid": self.is_valid,
            "last_validation": (
                self.last_validation.isoformat() if self.last_validation else None
            ),
            "validation_failures": self.validation_failures,
            "last_reason": self.last_reason,
            "last_message": self.last_message,
            "enabled": True,  # Sempre true - validação sempre ativa por segurança
            "check_interval": VALIDATION_INTERVAL_SECONDS,  # Sempre retornar valor hardcoded por segurança
        }

    def set_license_callbacks(
        self, on_valid: Callable = None, on_invalid: Callable = None
    ):
        """Definir callbacks para eventos de licença"""
        self.on_license_valid = on_valid
        self.on_license_invalid = on_invalid

    def force_validation(self) -> bool:
        """Forçar validação imediata"""
        self.logger.info("Validação forçada de licença")
        return self.validate_license()
