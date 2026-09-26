"""
Serviço de Sincronização com Gestão
Sincroniza dados de servidor, jogadores e rankings com o sistema de Gestão
"""
from core.database.connector import DatabaseConnector

import os
import sqlite3
import threading
import time
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Optional

# IMPORTANTE: URL importada do módulo centralizado
from core.config.server_urls import GESTAO_SERVER_URL

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class GestaoSyncService:
    """
    Serviço para sincronizar dados com o servidor de Gestão
    """

    def __init__(self, config: Dict[str, Any], path_helper, logger, discord_webhook):
        """
        Inicializar serviço de sincronização

        Args:
            config: Configuração completa do sistema
            path_helper: Helper para caminhos de arquivos
            logger: Logger estruturado
            discord_webhook: Instância do DiscordWebhook para envio de notificações (obrigatório para auditoria)
                            Deve ser a mesma instância criada em main.py
        """
        self.config = config
        self.path_helper = path_helper
        self.logger = logger

        # AUDITORIA: Webhook é obrigatório para registrar todas as sincronizações
        if discord_webhook is None:
            raise ValueError(
                "discord_webhook é obrigatório para auditoria de sincronizações. Use a instância criada em main.py"
            )

        self.discord_webhook = discord_webhook

        # Obter configuração do Gestão
        licensing_config = config.get("licensing", {})

        # SEGURANÇA: Intervalo de sincronização fixo (4 horas)
        self.sync_interval = 14400  # 4 horas em segundos

        # Obter e descriptografar API key se necessário
        api_key_raw = licensing_config.get("gestao_api_key", "")
        api_key = None

        if api_key_raw:
            # Verificar se está criptografada (começa com "ENCRYPTED:")
            if api_key_raw.startswith("ENCRYPTED:"):
                try:
                    from core.security.credential_encryption import decrypt_credential

                    api_key = decrypt_credential(api_key_raw, logger=logger)
                    if logger:
                        logger.info(
                            f"✅ API key descriptografada com sucesso (formato: {api_key[:10]}...{api_key[-5:] if len(api_key) > 15 else ''})"
                        )
                except Exception as e:
                    if logger:
                        logger.error(
                            f"❌ ERRO CRÍTICO: Falha ao descriptografar API key: {e}"
                        )
                        logger.error(
                            "A API key está criptografada mas não pôde ser descriptografada. A sincronização com Gestão falhará!"
                        )
                    api_key = None  # Garantir que não use a versão criptografada
            else:
                # API key em texto plano
                api_key = api_key_raw
                if logger:
                    logger.info("API key está em texto plano (não criptografada)")
        else:
            if logger:
                logger.warn("⚠️ gestao_api_key não configurada no config.json")

        self.api_key = api_key

        # IMPORTANTE: O Gestão identifica o servidor pela API key, não pelo hash
        # O hash ainda pode ser enviado como informação adicional, mas a identificação
        # é feita pela API key que está cadastrada no Gestão
        if self.api_key and logger:
            api_key_preview = (
                f"{self.api_key[:10]}...{self.api_key[-5:]}"
                if len(self.api_key) > 15
                else "***"
            )
            logger.info(
                f"✅ API key configurada - servidor será identificado por esta API key: {api_key_preview}"
            )

        # SEGURANÇA: Timeouts e retries hardcodados
        self.handshake_timeout = 5  # 5 segundos para handshake
        self.sync_timeout = 30  # 30 segundos para sincronização
        self.max_retry_delay = 3600  # 1 hora máximo entre tentativas
        self.max_retries = 3  # 3 tentativas máximo
        # SEGURANÇA: Sincronização com Gestão sempre habilitada
        self.enabled = False

        # SEGURANÇA: URL hardcoded para prevenir manipulação via config.json
        # Buscar dinamicamente do main.py se disponível (para desenvolvimento)
        gestao_server_url = self._get_gestao_server_url()
        self.gestao_url = gestao_server_url.rstrip("/")

        # Log da URL sendo usada (para debug em desenvolvimento)
        if self.logger:
            self.logger.info(f"🔗 URL do Gestão configurada: {self.gestao_url}")

        # Obter hardware fingerprint
        try:
            from core.licensing.hardware_fingerprint import HardwareFingerprint

            # IMPORTANTE: Usar o mesmo logger para garantir consistência na coleta
            self.hardware_fingerprint = HardwareFingerprint(logger=logger)
            # Gerar hash imediatamente para verificar se está funcionando
            if self.hardware_fingerprint:
                test_hash, _ = self.hardware_fingerprint.generate()
                if self.logger:
                    self.logger.info(
                        f"🔑 GESTAO SYNC: Hash inicial gerado no __init__: {test_hash}"
                    )
        except Exception as e:
            self.logger.error(f"Erro ao inicializar HardwareFingerprint: {e}")
            self.hardware_fingerprint = None

        # Thread de sincronização
        self.sync_thread = None
        self.running = False

        self._backend_base_url_cache: Optional[str] = None
        self._backend_base_url_source_cache: Optional[str] = None
        self._backend_base_url_cached_at: float = 0.0
        self._backend_base_url_checked_cache: Optional[bool] = None
        self._backend_base_url_checked_at: float = 0.0

        if not HAS_REQUESTS:
            self.logger.error(
                "Biblioteca 'requests' não encontrada. Sincronização com Gestão desabilitada."
            )
            self.enabled = False

    def _normalize_base_url(self, raw: str) -> str:
        value = (raw or "").strip()
        if not value:
            return ""
        if not value.startswith("http://") and not value.startswith("https://"):
            value = f"http://{value}"
        value = value.rstrip("/")
        return value

    def _ensure_port_3000(self, base_url: str) -> str:
        value = self._normalize_base_url(base_url)
        if not value:
            return ""

        without_scheme = value.split("://", 1)[1] if "://" in value else value
        hostport = without_scheme.split("/", 1)[0]

        has_port = False
        if hostport.startswith("["):
            end = hostport.find("]")
            if end != -1:
                has_port = ":" in hostport[end + 1 :]
        else:
            has_port = hostport.count(":") == 1

        if has_port:
            return value

        return f"{value}:3000"

    def _detect_external_ip(self) -> Optional[str]:
        if not HAS_REQUESTS:
            return None

        urls = [
            ("https://api.ipify.org?format=json", "json", "ip"),
            ("https://ifconfig.me/ip", "text", None),
            ("https://checkip.amazonaws.com", "text", None),
        ]
        for url, mode, json_key in urls:
            try:
                resp = requests.get(url, timeout=4)
                if resp.status_code != 200:
                    continue
                if mode == "json":
                    data = resp.json() if resp.content else {}
                    ip = str((data or {}).get(json_key) or "").strip()
                else:
                    ip = str(resp.text or "").strip()

                if ip and re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", ip):
                    return ip
            except Exception:
                continue

        return None

    def _compute_backend_base_url(self) -> Tuple[Optional[str], Optional[str]]:
        public_cfg = (self.config or {}).get("public", {})
        enabled = bool(public_cfg.get("backend_base_url_enabled", False))
        configured = str(public_cfg.get("backend_base_url") or "").strip()
        if enabled and configured:
            normalized = self._ensure_port_3000(configured)
            return (normalized if normalized else None), "configured"

        ip = self._detect_external_ip()
        if not ip:
            return None, None
        return f"http://{ip}:3000", "detected"

    def _get_backend_base_url_cached(self) -> Tuple[Optional[str], Optional[str]]:
        now = time.time()
        cache_ttl_seconds = 6 * 3600
        if (
            self._backend_base_url_cache
            and self._backend_base_url_source_cache
            and (now - self._backend_base_url_cached_at) < cache_ttl_seconds
        ):
            return self._backend_base_url_cache, self._backend_base_url_source_cache

        base_url, source = self._compute_backend_base_url()
        if base_url and source:
            self._backend_base_url_cache = base_url
            self._backend_base_url_source_cache = source
            self._backend_base_url_cached_at = now
            return base_url, source

        if self._backend_base_url_cache and self._backend_base_url_source_cache:
            return self._backend_base_url_cache, self._backend_base_url_source_cache

        return None, None

    def _check_backend_base_url(self, base_url: str) -> bool:
        if not HAS_REQUESTS:
            return False
        try:
            url = f"{self._normalize_base_url(base_url)}/api/health"
            resp = requests.get(url, timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def _get_backend_base_url_checked_cached(self, base_url: Optional[str]) -> Optional[bool]:
        if not base_url:
            return None
        now = time.time()
        cache_ttl_seconds = 30 * 60
        if (
            self._backend_base_url_checked_cache is not None
            and (now - self._backend_base_url_checked_at) < cache_ttl_seconds
        ):
            return self._backend_base_url_checked_cache

        checked = self._check_backend_base_url(base_url)
        self._backend_base_url_checked_cache = bool(checked)
        self._backend_base_url_checked_at = now
        return self._backend_base_url_checked_cache

    def _get_gestao_server_url(self) -> str:
        """
        Obter URL do servidor de Gestão do módulo centralizado

        Returns:
            str: URL do servidor de Gestão
        """
        return GESTAO_SERVER_URL

    def _send_webhook_notification(
        self, success: bool, result: Dict[str, Any] = None, error: str = None
    ):
        """
        Enviar notificação via webhook Discord sobre sucesso ou falha da sincronização
        OBRIGATÓRIO para auditoria - todas as sincronizações devem ser registradas

        Args:
            success: Se a sincronização foi bem-sucedida
            result: Dicionário com resultado da sincronização (se sucesso)
            error: Mensagem de erro (se falha)
        """
        # Log de debug para rastrear chamadas do webhook
        if self.logger:
            self.logger.debug(
                f"📤 Tentando enviar notificação Discord (success={success}, error={'Sim' if error else 'Não'})"
            )

        # AUDITORIA: Webhook é obrigatório, mas não deve interromper sincronização se falhar
        if not self.discord_webhook:
            if self.logger:
                self.logger.warn(
                    "⚠️ AVISO DE AUDITORIA: DiscordWebhook não disponível - sincronização não será registrada"
                )
            return

        try:
            webhook_configured = bool(
                getattr(self.discord_webhook, "webhooks", {})
                and str(getattr(self.discord_webhook, "webhooks", {}).get("log-ssm") or "").strip()
            )
        except Exception:
            webhook_configured = True

        try:

            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            if success:
                # Webhook de sucesso - Embed simplificado conforme solicitado
                total_players = result.get("total_players", 0) if result else 0

                # Embed simplificado: título, descrição com "✅ sucesso" e campo de jogadores
                fields = [
                    {
                        "name": "👤 Players",
                        "value": (
                            str(total_players) if total_players is not None else "0"
                        ),
                        "inline": False,
                    }
                ]

                webhook_sent = self.discord_webhook.send_webhook(
                    webhook_name="log-ssm",
                    title="🔄 Management Synchronization",
                    description="✅ success",  # Status na descrição
                    color=0x00FF00,  # Verde
                    fields=fields,
                )
                if self.logger:
                    if webhook_sent:
                        self.logger.info(
                            "✅ Notificação de sucesso enviada para Discord (webhook: log-ssm)"
                        )
                    else:
                        if webhook_configured:
                            self.logger.warn(
                                "⚠️ Falha ao enviar notificação de sucesso para Discord"
                            )
                        else:
                            self.logger.debug(
                                "Notificação de sucesso ignorada (webhook: log-ssm não configurado)"
                            )
            else:
                # Webhook de falha - Embed simplificado conforme solicitado
                # Apenas título, sem descrição e sem campos
                webhook_sent = self.discord_webhook.send_webhook(
                    webhook_name="log-ssm",
                    title="❌ Management Synchronization Failure",
                    description="",  # Sem descrição - modelo simplificado
                    color=0xFF0000,  # Vermelho
                    fields=[],  # Sem campos
                )
                if self.logger:
                    if webhook_sent:
                        self.logger.info(
                            "✅ Notificação de falha enviada para Discord (webhook: log-ssm)"
                        )
                    else:
                        if webhook_configured:
                            self.logger.warn(
                                "⚠️ Falha ao enviar notificação de falha para Discord"
                            )
                        else:
                            self.logger.debug(
                                "Notificação de falha ignorada (webhook: log-ssm não configurado)"
                            )
        except Exception as e:
            # Não interromper a sincronização se o webhook falhar
            if self.logger:
                self.logger.warn(f"Erro ao enviar webhook de notificação: {e}")

    def get_server_hash(self) -> Optional[str]:
        """
        Obter hash do servidor (equipment_hash)

        IMPORTANTE: O Gestão identifica o servidor pela API key, não pelo hash.
        O hash é enviado apenas como informação adicional.
        Este método gera o hash atual do hardware para envio ao Gestão.
        """
        if not self.hardware_fingerprint:
            if self.logger:
                self.logger.error(
                    "⚠️ HardwareFingerprint não disponível - não é possível obter hash"
                )
            return None

        try:
            hash_value, components = self.hardware_fingerprint.generate()
            if self.logger:
                self.logger.info(
                    f"🔑 Hash do hardware gerado (64 chars): {hash_value} (comprimento: {len(hash_value)})"
                )
                self.logger.debug(
                    f"🔍 Componentes coletados: CPU={components.get('cpu_id')}, MACs={len(components.get('network_macs', []))}, Discos={len(components.get('disk_serials', []))}, WindowsGUID={components.get('windows_guid')}"
                )
            return hash_value
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao obter hash do servidor: {e}")
            return None

    def _validate_server_hash(self, server_hash: str) -> bool:
        """Validar formato de server_hash (64 caracteres hexadecimais)"""
        if not server_hash:
            return False
        return bool(re.match(r"^[0-9a-fA-F]{64}$", server_hash))

    def _validate_api_key(self, api_key: str) -> bool:
        """Validar formato de api_key (ssm_ + 64 caracteres hexadecimais)"""
        if not api_key:
            return False
        return bool(re.match(r"^ssm_[0-9a-fA-F]{64}$", api_key))

    def _calculate_payload_size(self, payload: Dict[str, Any]) -> int:
        """Calcular tamanho aproximado do payload em bytes"""
        try:
            json_str = json.dumps(payload)
            return len(json_str.encode("utf-8"))
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Erro ao calcular tamanho do payload: {e}")
            return 0

    def _split_players_in_batches(
        self, players: List[Dict[str, Any]], max_size_mb: float = 5.0
    ) -> List[List[Dict[str, Any]]]:
        """
        Dividir players em lotes respeitando limite de tamanho (5 MB)

        Args:
            players: Lista de players do ranking
            max_size_mb: Tamanho máximo em MB (padrão: 5.0)

        Returns:
            Lista de lotes (cada lote é uma lista de players)
        """
        max_size_bytes = max_size_mb * 1024 * 1024  # Converter MB para bytes
        batches = []
        current_batch = []

        # Estimar tamanho base do payload (sem players de ranking)
        # Isso é uma estimativa, mas ajuda a evitar recalcular o payload completo
        avg_player_size = 700  # ~700 bytes por player (JSON compacto)

        for player in players:
            # Calcular tamanho aproximado do player
            try:
                player_size = len(json.dumps(player).encode("utf-8"))
            except Exception:
                player_size = avg_player_size

            # Estimar tamanho do batch atual
            estimated_batch_size = (
                len(json.dumps(current_batch).encode("utf-8")) if current_batch else 0
            )

            # Se adicionar este player exceder o limite, criar novo batch
            if current_batch and (estimated_batch_size + player_size) > max_size_bytes:
                batches.append(current_batch)
                current_batch = [player]
            else:
                current_batch.append(player)

        # Adicionar último batch se houver
        if current_batch:
            batches.append(current_batch)

        if self.logger and len(batches) > 1:
            self.logger.info(
                f"Rankings divididos em {len(batches)} lotes para respeitar limite de 5 MB"
            )

        return batches

    def check_ready(self) -> Tuple[bool, int]:
        """
        Verificar se o Gestão está pronto para receber dados (Handshake)

        IMPORTANTE: O Gestão identifica o servidor pela API key, não pelo hash.
        O hash é enviado apenas como informação adicional.

        Returns:
            (ready: bool, retry_after: int) - Se pronto e tempo para retry
        """
        if not HAS_REQUESTS:
            return (False, 60)

        # IMPORTANTE: Validar API key primeiro (identificador principal)
        if not self.api_key:
            if self.logger:
                self.logger.error(
                    "❌ API key não configurada - não é possível identificar o servidor no Gestão"
                )
            return (False, 60)

        try:
            # Log da URL completa sendo usada (para debug em desenvolvimento)
            handshake_url = f"{self.gestao_url}/api/v1/servers/ready"
            if self.logger:
                # IMPORTANTE: O Gestão identifica o servidor apenas pela API key
                api_key_preview = (
                    f"{self.api_key[:10]}...{self.api_key[-5:]}"
                    if self.api_key and len(self.api_key) > 15
                    else "N/A"
                )
                self.logger.debug(
                    f"🔑 Handshake: servidor será identificado pela API key: {api_key_preview}"
                )
                self.logger.debug(f"🔗 Handshake: URL sendo usada: {handshake_url}")
                self.logger.debug(
                    f"🔗 Handshake: URL completa com parâmetros: {handshake_url}?api_key={api_key_preview}"
                )

            response = requests.get(
                handshake_url,
                params={"api_key": self.api_key},
                timeout=self.handshake_timeout,
            )

            # Log detalhado da resposta para debug
            if self.logger:
                try:
                    response_text = (
                        response.text[:500] if hasattr(response, "text") else "N/A"
                    )
                    self.logger.debug(
                        f"🔍 Handshake resposta HTTP {response.status_code}: {response_text}"
                    )
                except:
                    pass

            if response.status_code == 200:
                try:
                    data = response.json() or {}
                except (ValueError, AttributeError):
                    data = {}

                ready = data.get("ready", False)
                # Se não está pronto, usar retry_after da resposta ou padrão de 30s
                if not ready:
                    retry_after = data.get("retry_after", 30)
                    # Garantir que retry_after seja pelo menos 5 segundos
                    retry_after = max(retry_after, 5)
                    if self.logger:
                        message = data.get(
                            "message", "Gestão não está pronto para receber dados"
                        )
                        self.logger.info(
                            f"Gestão não está pronto: {message} (aguardando {retry_after}s)"
                        )
                    return (False, retry_after)
                else:
                    if self.logger:
                        self.logger.debug("Gestão está pronto para receber dados")
                    return (True, 0)
            elif response.status_code == 503:  # Servidor ocupado
                try:
                    data = response.json() or {}
                    retry_after = data.get("retry_after", 30)
                except (ValueError, AttributeError):
                    retry_after = 30
                if self.logger:
                    self.logger.info(f"Gestão ocupado, aguardar {retry_after} segundos")
                return (False, retry_after)
            elif response.status_code == 429:  # Rate limit
                try:
                    data = response.json() or {}
                    retry_after = data.get("retry_after", 60)
                except (ValueError, AttributeError):
                    retry_after = 60
                if self.logger:
                    self.logger.info(
                        f"Rate limit atingido, aguardar {retry_after} segundos"
                    )
                return (False, retry_after)
            elif (
                response.status_code == 422
            ):  # Unprocessable Entity - erro de validação
                try:
                    data = response.json()
                    error_detail = data.get(
                        "detail",
                        (
                            response.text[:200]
                            if hasattr(response, "text")
                            else "Erro de validação"
                        ),
                    )
                except (ValueError, AttributeError):
                    error_detail = (
                        response.text[:200]
                        if hasattr(response, "text")
                        else "Erro de validação desconhecido"
                    )

                if self.logger:
                    api_key_preview = (
                        f"{self.api_key[:10]}...{self.api_key[-5:]}"
                        if self.api_key and len(self.api_key) > 15
                        else "N/A"
                    )
                    self.logger.error(f"❌ Erro 422 (Validação): {error_detail}")
                    self.logger.error(f"⚠️ API key usada: {api_key_preview}")
                    self.logger.error("⚠️ Possíveis causas:")
                    self.logger.error(
                        "   1. API key inválida ou não cadastrada no Gestão"
                    )
                    self.logger.error("   2. Formato da API key incorreto")
                    self.logger.error(
                        "   3. Gestão espera outro formato de parâmetro no handshake"
                    )

                return (False, 60)  # Aguardar 1 minuto antes de tentar novamente
            else:
                try:
                    error_detail = (
                        response.text[:200]
                        if hasattr(response, "text")
                        else "Erro desconhecido"
                    )
                except:
                    error_detail = "Erro desconhecido"

                if self.logger:
                    self.logger.warn(
                        f"Resposta inesperada do handshake: {response.status_code} - {error_detail}"
                    )
                return (False, 60)  # Aguardar 1 minuto

        except requests.exceptions.Timeout:
            if self.logger:
                self.logger.warn("Timeout ao verificar se Gestão está pronto")
            return (False, 30)
        except requests.exceptions.ConnectionError:
            if self.logger:
                self.logger.warn("Gestão offline, aguardar antes de tentar novamente")
            return (False, 300)  # Aguardar 5 minutos se offline
        except Exception as e:
            if self.logger:
                try:
                    self.logger.error(f"Erro ao verificar se Gestão está pronto: {e}")
                except:
                    pass
            return (False, 60)

    def _mask_api_key(self, api_key: str) -> str:
        """
        Mascarar API key parcialmente para segurança (mostra apenas início e fim)

        Args:
            api_key: API key completa

        Returns:
            API key mascarada (ex: "ssm_1234567890...abcdef")
        """
        if not api_key or len(api_key) <= 15:
            return "***"
        return f"{api_key[:10]}...{api_key[-5:]}"

    def _cleanup_old_audit_files(self, keep_count: int = 10):
        """
        Remover arquivos de auditoria antigos, mantendo apenas os últimos N arquivos

        Args:
            keep_count: Número de arquivos mais recentes para manter (padrão: 10)
        """
        try:
            # Obter diretório de logs
            logs_dir = (
                self.path_helper.get_logs_directory()
                if self.path_helper
                else "data/logs"
            )
            audit_dir = os.path.join(logs_dir, "gestao_sync")

            # Verificar se diretório existe
            if not os.path.exists(audit_dir):
                return

            # Listar todos os arquivos .json com suas datas de modificação
            files_with_mtime = []

            for filename in os.listdir(audit_dir):
                if not filename.endswith(".json"):
                    continue

                filepath = os.path.join(audit_dir, filename)

                try:
                    # Obter data de modificação do arquivo
                    file_mtime = os.path.getmtime(filepath)
                    file_size = os.path.getsize(filepath)
                    files_with_mtime.append((filepath, file_mtime, file_size))
                except OSError as e:
                    # Ignorar erros ao acessar arquivo
                    if self.logger:
                        self.logger.debug(
                            f"Erro ao processar arquivo {filename} durante limpeza: {e}"
                        )
                    continue

            # Se temos menos ou igual ao número de arquivos para manter, não precisa deletar nada
            if len(files_with_mtime) <= keep_count:
                return

            # Ordenar por data de modificação (mais recente primeiro)
            files_with_mtime.sort(key=lambda x: x[1], reverse=True)

            # Manter apenas os N mais recentes, deletar os demais
            files_to_delete = files_with_mtime[keep_count:]

            deleted_count = 0
            total_size_freed = 0

            for filepath, _, file_size in files_to_delete:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    total_size_freed += file_size
                except OSError as e:
                    # Ignorar erros ao deletar (arquivo pode ter sido deletado, etc)
                    if self.logger:
                        self.logger.debug(
                            f"Erro ao deletar arquivo {filepath} durante limpeza: {e}"
                        )
                    continue

            # Log de resultado (apenas se deletou algo)
            if deleted_count > 0 and self.logger:
                size_mb = round(total_size_freed / (1024 * 1024), 2)
                self.logger.info(
                    f"🧹 Limpeza de auditoria: {deleted_count} arquivo(s) removido(s), mantidos os últimos {keep_count} arquivos, {size_mb} MB liberados"
                )

        except Exception as e:
            # Não interromper sincronização se falhar na limpeza
            if self.logger:
                self.logger.warn(f"⚠️ Erro ao limpar arquivos de auditoria antigos: {e}")

    def _save_payload_for_audit(
        self,
        payload: Dict[str, Any],
        response_data: Dict[str, Any],
        job_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Salvar payload JSON enviado ao Gestão para auditoria

        Args:
            payload: Payload completo enviado
            response_data: Resposta do Gestão
            job_id: ID do job (se presente)

        Returns:
            Caminho do arquivo salvo ou None se falhou
        """
        try:
            # Obter diretório de logs
            logs_dir = (
                self.path_helper.get_logs_directory()
                if self.path_helper
                else "data/logs"
            )
            audit_dir = os.path.join(logs_dir, "gestao_sync")

            # Criar diretório se não existir
            os.makedirs(audit_dir, exist_ok=True)

            # Gerar nome do arquivo: gestao_sync_YYYYMMDD_HHMMSS_jobID.json
            timestamp = datetime.utcnow()
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

            if job_id:
                filename = f"gestao_sync_{timestamp_str}_{job_id}.json"
            else:
                filename = f"gestao_sync_{timestamp_str}.json"

            filepath = os.path.join(audit_dir, filename)

            # Preparar payload para salvar (com API key mascarada)
            payload_to_save = payload.copy()
            if "api_key" in payload_to_save:
                payload_to_save["api_key"] = self._mask_api_key(
                    payload_to_save["api_key"]
                )

            # Calcular tamanho do payload original
            payload_size = self._calculate_payload_size(payload)

            # Contar players
            rankings_players = payload.get("rankings", {}).get("players", [])
            total_players = len(rankings_players)
            players_count = len(payload.get("players", []))

            # Obter nome do servidor
            server_name = payload.get("server_info", {}).get("name", "Unknown")

            # Criar documento de auditoria completo
            audit_document = {
                "metadata": {
                    "timestamp": timestamp.isoformat() + "Z",
                    "job_id": job_id,
                    "status": response_data.get("status"),
                    "success": True,
                    "payload_size_bytes": payload_size,
                    "payload_size_mb": round(payload_size / (1024 * 1024), 2),
                    "server_name": server_name,
                    "total_players_rankings": total_players,
                    "total_players": players_count,
                    "gestao_url": self.gestao_url,
                    "gestao_response": response_data,
                },
                "payload": payload_to_save,
            }

            # Salvar arquivo JSON formatado
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(audit_document, f, indent=2, ensure_ascii=False)

            if self.logger:
                self.logger.info(
                    f"📋 Payload salvo para auditoria: {filename} ({audit_document['metadata']['payload_size_mb']} MB, {total_players} players)"
                )

            # Limpar arquivos antigos, mantendo apenas os últimos 10 arquivos
            self._cleanup_old_audit_files(keep_count=10)

            return filepath

        except Exception as e:
            # Não interromper sincronização se falhar ao salvar
            if self.logger:
                self.logger.warn(f"⚠️ Erro ao salvar payload para auditoria: {e}")
            return None

    def _send_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enviar payload para o Gestão

        Args:
            payload: Payload completo para enviar

        Returns:
            Resultado da requisição
        """
        try:
            sync_url = f"{self.gestao_url}/api/v1/servers/sync"
            # Log da URL completa sendo usada (para debug em desenvolvimento)
            if self.logger:
                self.logger.debug(f"🔗 Sync: URL sendo usada: {sync_url}")

            response = requests.post(
                sync_url,
                json=payload,
                timeout=self.sync_timeout,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                try:
                    response_data = response.json()
                except (ValueError, AttributeError) as e:
                    response_data = {
                        "message": (
                            response.text[:200]
                            if hasattr(response, "text")
                            else "Resposta inválida"
                        )
                    }
                    if self.logger:
                        self.logger.warn(f"Não foi possível parsear resposta JSON: {e}")

                # Extrair job_id e status (novo sistema de fila assíncrona v3.0)
                job_id = response_data.get("job_id")
                status = response_data.get("status")

                # Salvar payload para auditoria (após resposta bem-sucedida)
                self._save_payload_for_audit(payload, response_data, job_id)

                # Logar job_id se presente (processamento assíncrono)
                if job_id:
                    if self.logger:
                        self.logger.info(
                            f"📋 Job criado: {job_id} (status: {status}). "
                            f"Rankings sendo processados em background."
                        )

                return {
                    "success": True,
                    "data": response_data,
                    "status_code": 200,
                    "job_id": job_id,
                    "status": status,
                }
            elif response.status_code == 413:  # Payload muito grande
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", "Payload muito grande")
                except (ValueError, AttributeError):
                    error_msg = "Payload muito grande (413 Payload Too Large)"

                if self.logger:
                    self.logger.warning(f"Payload muito grande: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": 413,
                    "should_retry": True,
                    "should_split": True,  # Flag para indicar que deve dividir
                }
            elif response.status_code == 400:  # Erro de validação
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", "Erro de validação")
                except (ValueError, AttributeError):
                    error_msg = f"Erro de validação (400): {response.text[:200] if hasattr(response, 'text') else 'Erro desconhecido'}"

                if self.logger:
                    self.logger.error(f"Erro de validação: {error_msg}")

                    # Verificar se é erro de servidor não cadastrado
                    if (
                        "não encontrado" in error_msg.lower()
                        or "não cadastrado" in error_msg.lower()
                        or "not found" in error_msg.lower()
                    ):
                        # Log detalhado para debug - verificar se a API key está correta
                        api_key_preview = (
                            f"{self.api_key[:10]}...{self.api_key[-5:]}"
                            if self.api_key and len(self.api_key) > 15
                            else "N/A"
                        )
                        self.logger.error(
                            f"⚠️ ERRO: Servidor não encontrado no Gestão. "
                            f"API key usada: {api_key_preview}. "
                            f"Verifique se a API key está cadastrada corretamente no Gestão."
                        )

                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": 400,
                    "should_retry": False,
                }
            elif response.status_code == 401:  # Erro de autenticação
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", "Erro de autenticação")
                except (ValueError, AttributeError):
                    error_msg = (
                        "Erro de autenticação: verifique se a API key está correta"
                    )

                if self.logger:
                    self.logger.error(f"Erro de autenticação: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": 401,
                    "should_retry": False,
                }
            elif response.status_code == 503:  # Servidor ocupado
                try:
                    data = response.json()
                    retry_after = data.get("retry_after", 30)
                except (ValueError, AttributeError):
                    retry_after = 30

                if self.logger:
                    self.logger.warn(
                        f"Gestão ocupado durante sync, aguardar {retry_after} segundos"
                    )
                return {
                    "success": False,
                    "error": "Servidor ocupado",
                    "status_code": 503,
                    "retry_after": retry_after,
                    "should_retry": True,
                }
            elif response.status_code == 500:  # Erro do servidor
                try:
                    error_data = response.json()
                    error_msg = error_data.get(
                        "detail", error_data.get("message", "Erro interno do servidor")
                    )
                    error_detail = error_data
                except (ValueError, AttributeError):
                    error_msg = "Erro interno do servidor (500)"
                    error_detail = None
                    error_text = (
                        response.text[:500] if hasattr(response, "text") else ""
                    )
                    if error_text:
                        error_detail = {"response_text": error_text}

                if self.logger:
                    self.logger.error(f"Erro do servidor: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": 500,
                    "should_retry": True,
                    "data": error_detail,
                    "response_text": (
                        response.text[:1000] if hasattr(response, "text") else ""
                    ),
                }
            elif response.status_code == 404:  # Servidor não encontrado
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", "Servidor não encontrado")
                except (ValueError, AttributeError):
                    error_msg = f"Servidor não encontrado (404): {response.text[:200] if hasattr(response, 'text') else 'Erro desconhecido'}"

                if self.logger:
                    api_key_preview = (
                        f"{self.api_key[:10]}...{self.api_key[-5:]}"
                        if self.api_key and len(self.api_key) > 15
                        else "N/A"
                    )
                    self.logger.error(f"❌ Erro 404: {error_msg}")
                    self.logger.error(f"⚠️ API key usada: {api_key_preview}")
                    self.logger.error("⚠️ DIAGNÓSTICO:")
                    self.logger.error(
                        "   • Sincronização com Gestão: FALHOU ❌ (servidor não encontrado)"
                    )
                    self.logger.error("⚠️ POSSÍVEIS CAUSAS:")
                    self.logger.error(
                        "   1. A API key não está cadastrada no sistema de Gestão"
                    )
                    self.logger.error(
                        "   2. A API key está incorreta ou não corresponde ao servidor"
                    )
                    self.logger.error(
                        "⚠️ SOLUÇÃO: Verifique se a API key está correta e se o servidor foi cadastrado no Gestão."
                    )

                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": 404,
                    "should_retry": False,
                }
            else:
                try:
                    error_text = (
                        response.text[:500]
                        if hasattr(response, "text")
                        else f"Erro HTTP {response.status_code}"
                    )
                except:
                    error_text = f"Erro HTTP {response.status_code}"

                if self.logger:
                    self.logger.error(
                        f"Erro ao sincronizar: {response.status_code} - {error_text}"
                    )
                return {
                    "success": False,
                    "error": error_text,
                    "status_code": response.status_code,
                    "should_retry": False,
                }

        except requests.exceptions.Timeout:
            if self.logger:
                self.logger.error("Timeout ao sincronizar com Gestão")
            return {
                "success": False,
                "error": "Timeout",
                "status_code": 0,
                "retry_after": 60,
                "should_retry": True,
            }
        except requests.exceptions.ConnectionError:
            if self.logger:
                self.logger.error("Gestão offline")
            return {
                "success": False,
                "error": "Gestão offline",
                "status_code": 0,
                "retry_after": 300,
                "should_retry": True,
            }
        except Exception as e:
            error_msg = str(e) if e else "Erro desconhecido"
            if self.logger:
                try:
                    import traceback

                    tb_str = traceback.format_exc()
                    self.logger.error(
                        f"Erro ao enviar payload para Gestão: {error_msg}",
                        {"traceback": tb_str},
                    )
                except:
                    self.logger.error(
                        f"Erro ao enviar payload para Gestão: {error_msg}"
                    )
            return {
                "success": False,
                "error": error_msg,
                "status_code": 0,
                "should_retry": False,
            }

    def sync_data(self) -> Dict[str, Any]:
        """
        Sincronizar dados com o Gestão (com handshake e controle de tamanho)

        Conforme documentação v2.0:
        - Valida server_hash e api_key
        - Verifica tamanho do payload (< 5 MB)
        - Divide em lotes se necessário
        - Trata erro 413 Payload Too Large
        """
        if not self.enabled:
            players_count = 0
            rankings_count = 0
            try:
                players_count = len(self._get_players_data())
            except Exception:
                pass
            try:
                rankings_count = len(self._get_rankings_data().get("players", []))
            except Exception:
                pass
            return {
                "success": True,
                "data": {
                    "players_synced": players_count,
                    "rankings_created": rankings_count,
                    "server_id": "standalone"
                },
                "status_code": 200,
                "message": "Sincronização desabilitada (Modo Open Source/Standalone)"
            }

        if not HAS_REQUESTS:
            return {
                "success": False,
                "error": "Biblioteca 'requests' não disponível",
                "should_retry": False,
            }

        try:
            # 1. Handshake - verificar se Gestão está pronto
            if self.logger:
                self.logger.debug("Verificando se Gestão está pronto (handshake)...")
            ready, retry_after = self.check_ready()

            if not ready:
                if self.logger:
                    self.logger.warn(
                        f"❌ Gestão não está pronto para sincronização. Aguardando {retry_after}s antes de tentar novamente."
                    )
                error_result = {
                    "success": False,
                    "error": f"Gestão não está pronto para sincronização (aguardando {retry_after}s)",
                    "retry_after": retry_after,
                    "should_retry": True,
                }
                # Enviar webhook mesmo quando Gestão não está pronto (para auditoria completa)
                self._send_webhook_notification(
                    success=False, error=error_result["error"]
                )
                return error_result

            if self.logger:
                self.logger.debug(
                    "✅ Gestão está pronto. Iniciando sincronização de dados..."
                )

            # 2. Coletar dados
            # IMPORTANTE: O Gestão identifica o servidor apenas pela API key
            if self.logger:
                api_key_preview = (
                    f"{self.api_key[:10]}...{self.api_key[-5:]}"
                    if len(self.api_key) > 15
                    else "***"
                )
                self.logger.info(
                    f"🔑 Servidor será identificado pela API key: {api_key_preview}"
                )

            if not self.api_key:
                error_result = {
                    "success": False,
                    "error": "API key não configurada ou não pôde ser descriptografada",
                    "should_retry": False,
                }
                if self.logger:
                    self.logger.error(
                        "❌ API key não disponível. Verifique se está configurada no config.json e se a descriptografia funcionou."
                    )
                self._send_webhook_notification(
                    success=False, error=error_result["error"]
                )
                return error_result

            # Log da API key que será usada (apenas início e fim para segurança)
            if self.logger:
                api_key_preview = (
                    f"{self.api_key[:10]}...{self.api_key[-5:]}"
                    if len(self.api_key) > 15
                    else "***"
                )
                self.logger.info(f"🔑 API key que será usada: {api_key_preview}")

            # Validar formato de api_key
            if not self._validate_api_key(self.api_key):
                error_msg = f"Formato de api_key inválido (esperado: 'ssm_' + 64 caracteres hexadecimais, recebido: '{self.api_key[:20]}...' ({len(self.api_key)} caracteres))"
                if self.logger:
                    self.logger.error(f"❌ {error_msg}")
                    self.logger.error(
                        "⚠️ Verifique se a API key foi descriptografada corretamente!"
                    )
                    self.logger.error(
                        f"⚠️ Valor atual da API key (primeiros 30 chars): {self.api_key[:30]}"
                    )
                error_result = {
                    "success": False,
                    "error": error_msg,
                    "should_retry": False,
                }
                self._send_webhook_notification(success=False, error=error_msg)
                return error_result

            server_info = self._get_server_info()
            players = self._get_players_data()
            rankings = self._get_rankings_data()

            rankings_players = rankings.get("players", [])

            # Log de debug para auditoria
            if self.logger:
                self.logger.info(
                    f"📊 Dados coletados: {len(rankings_players)} players de ranking, {len(players)} players totais"
                )

            # 3. Preparar payload base (sem rankings para testar tamanho)
            # IMPORTANTE: O Gestão identifica o servidor apenas pela API key, não precisa enviar hash
            payload_base = {
                "api_key": self.api_key,
                "server_info": server_info,
                "players": players,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            # 4. Verificar tamanho do payload completo
            test_payload = {**payload_base, "rankings": rankings}
            payload_size = self._calculate_payload_size(test_payload)
            max_size_bytes = 5 * 1024 * 1024  # 5 MB

            if payload_size > max_size_bytes:
                # Payload muito grande - dividir em lotes
                if self.logger:
                    size_mb = payload_size / (1024 * 1024)
                    self.logger.warning(
                        f"Payload muito grande ({size_mb:.2f} MB). Dividindo em lotes..."
                    )

                batches = self._split_players_in_batches(
                    rankings_players, max_size_mb=5.0
                )

                if not batches:
                    error_result = {
                        "success": False,
                        "error": "Não foi possível dividir rankings em lotes",
                        "should_retry": False,
                    }
                    self._send_webhook_notification(
                        success=False, error=error_result["error"]
                    )
                    return error_result

                # Enviar cada lote separadamente
                results = []
                for batch_idx, batch in enumerate(batches, 1):
                    if self.logger:
                        self.logger.info(
                            f"Enviando lote {batch_idx}/{len(batches)} ({len(batch)} players)..."
                        )

                    # Preparar payload do lote
                    batch_rankings = {"players": batch}
                    batch_payload = {**payload_base, "rankings": batch_rankings}

                    # Enviar lote
                    result = self._send_payload(batch_payload)
                    results.append(result)

                    # Se algum lote falhou, retornar erro
                    if not result.get("success"):
                        if self.logger:
                            self.logger.error(
                                f"Falha ao enviar lote {batch_idx}/{len(batches)}: {result.get('error')}"
                            )
                        error_msg = result.get(
                            "error", "Erro desconhecido ao enviar lote"
                        )
                        self._send_webhook_notification(
                            success=False,
                            error=f"Falha ao enviar lote {batch_idx}/{len(batches)}: {error_msg}",
                        )
                        return result

                    # Logar job_id se presente (novo sistema de fila assíncrona v3.0)
                    job_id = result.get("job_id")
                    if job_id and self.logger:
                        self.logger.info(
                            f"📋 Lote {batch_idx}/{len(batches)} - Job criado: {job_id}"
                        )

                    # Aguardar entre lotes para respeitar rate limiting (1 req/5min)
                    # Mas apenas se não for o último lote
                    if batch_idx < len(batches):
                        if self.logger:
                            self.logger.info(
                                f"Aguardando 5 minutos antes do próximo lote (rate limiting)..."
                            )
                        # Aguardar 5 minutos entre lotes
                        for _ in range(300):  # 5 minutos = 300 segundos
                            if not self.running:  # Se parou de rodar, sair
                                break
                            time.sleep(1)

                # Todos os lotes foram enviados com sucesso
                if self.logger:
                    self.logger.info(
                        f"✅ Todos os {len(batches)} lotes sincronizados com sucesso"
                    )

                # Retornar resultado do último lote (já tem todos os dados)
                last_result = results[-1]
                final_result = {
                    "success": True,
                    "data": last_result.get("data", {}),
                    "batches_sent": len(batches),
                    "total_players": len(rankings_players),
                    "job_id": last_result.get("job_id"),  # Incluir job_id se presente
                    "status": last_result.get("status"),  # Incluir status se presente
                }

                # Enviar webhook de sucesso
                self._send_webhook_notification(success=True, result=final_result)

                return final_result
            else:
                # Payload dentro do limite - enviar normalmente
                payload = {**payload_base, "rankings": rankings}

                # Log de debug: verificar se rankings estão no payload
                if self.logger:
                    rankings_in_payload = payload.get("rankings", {})
                    players_in_rankings = rankings_in_payload.get("players", [])
                    self.logger.info(
                        f"🔍 DEBUG: Payload preparado com {len(players_in_rankings)} players de ranking no payload"
                    )

                result = self._send_payload(payload)

                if result.get("success"):
                    # Adicionar total_players ao resultado para o webhook de auditoria
                    total_players_count = len(rankings_players)
                    result["total_players"] = total_players_count

                    job_id = result.get("job_id")
                    response_data = result.get("data", {})
                    rankings_created = response_data.get("rankings_created")

                    if self.logger:
                        size_mb = payload_size / (1024 * 1024)

                        # Log detalhado dos dados enviados
                        self.logger.info(
                            f"📊 Resumo do envio: "
                            f"{total_players_count} players de ranking, "
                            f"{size_mb:.2f} MB, "
                            f"job_id={job_id if job_id else 'N/A'}"
                        )

                        if job_id:
                            # Processado em background (novo sistema de fila assíncrona v3.0)
                            self.logger.info(
                                f"✅ Dados recebidos pelo Gestão. "
                                f"Rankings sendo processados em background "
                                f"(job_id: {job_id}, {size_mb:.2f} MB, {total_players_count} players)"
                            )
                        else:
                            # Processado síncrono (sem rankings ou compatibilidade)
                            log_msg = (
                                f"✅ Dados sincronizados com sucesso com Gestão "
                                f"({size_mb:.2f} MB, {total_players_count} players"
                            )
                            if rankings_created is not None:
                                log_msg += f", {rankings_created} rankings criados)"
                            else:
                                log_msg += ")"
                            self.logger.info(log_msg)
                else:
                    # Se falhou, também adicionar total_players para informação no webhook de erro
                    if self.logger:
                        self.logger.warn(
                            f"⚠️ Falha ao enviar dados (payload tinha {len(rankings_players)} players de ranking)"
                        )

                # Enviar webhook de sucesso ou falha
                self._send_webhook_notification(
                    success=result.get("success"),
                    result=result if result.get("success") else None,
                    error=result.get("error") if not result.get("success") else None,
                )

                return result

        except Exception as e:
            error_msg = str(e) if e else "Erro desconhecido"
            if self.logger:
                try:
                    import traceback

                    tb_str = traceback.format_exc()
                    self.logger.error(
                        f"Erro ao sincronizar com Gestão: {error_msg}",
                        {"traceback": tb_str},
                    )
                except:
                    self.logger.error(f"Erro ao sincronizar com Gestão: {error_msg}")

            # Enviar webhook de falha
            self._send_webhook_notification(success=False, error=error_msg)

            return {"success": False, "error": error_msg, "should_retry": False}

    def sync_with_retry(self, max_retries: Optional[int] = None) -> Dict[str, Any]:
        """
        Sincronizar com retry automático

        Args:
            max_retries: Número máximo de tentativas (usa self.max_retries se None)

        Returns:
            Resultado da sincronização
        """
        if max_retries is None:
            max_retries = self.max_retries

        for attempt in range(max_retries):
            result = self.sync_data()

            if result.get("success"):
                return result

            # Verificar se deve tentar novamente
            if not result.get("should_retry", False):
                return result

            # Aguardar antes de tentar novamente
            retry_after = result.get("retry_after", 60)
            retry_after = min(retry_after, self.max_retry_delay)

            if attempt < max_retries - 1:
                self.logger.info(
                    f"Aguardando {retry_after} segundos antes de tentar novamente... (tentativa {attempt + 1}/{max_retries})"
                )
                time.sleep(retry_after)

        return result

    def start_periodic_sync(self):
        """
        Iniciar sincronização periódica com handshake

        Executa em thread separada, fazendo:
        1. Verifica se Gestão está pronto (handshake)
        2. Se pronto, envia dados
        3. Se não pronto, aguarda e tenta novamente
        4. Repete a cada sync_interval segundos
        """
        if not self.enabled:
            self.logger.info("Sincronização com Gestão desabilitada")
            return None

        if not self.gestao_url:
            self.logger.warn("URL do Gestão não configurada")
            return None

        if not self.api_key:
            self.logger.warn("API key do Gestão não configurada")
            return None

        if self.running:
            self.logger.warn("Sincronização periódica já está em execução")
            return self.sync_thread

        def sync_loop():
            self.running = True
            self.logger.info(
                f"Sincronização periódica iniciada (intervalo: {self.sync_interval}s)"
            )

            while self.running:
                try:
                    self.logger.info(
                        "Iniciando tentativa de sincronização com Gestão..."
                    )

                    # Tentar sincronizar (com retry automático)
                    result = self.sync_with_retry()

                    if result.get("success"):
                        self.logger.info("✅ Sincronização concluída com sucesso")
                    else:
                        error = result.get("error", "Erro desconhecido")
                        retry_after = result.get("retry_after", self.sync_interval)
                        self.logger.warn(
                            f"❌ Sincronização falhou: {error}. Próxima tentativa em {retry_after}s"
                        )

                    # Aguardar antes da próxima tentativa
                    wait_time = result.get("retry_after", self.sync_interval)
                    wait_time = min(
                        wait_time, self.sync_interval
                    )  # Não esperar mais que o intervalo normal

                    # Aguardar o intervalo completo antes da próxima sincronização
                    for _ in range(int(wait_time)):
                        if not self.running:
                            break
                        time.sleep(1)

                except Exception as e:
                    self.logger.error(f"Erro no loop de sincronização: {e}")
                    # Aguardar intervalo completo em caso de erro
                    for _ in range(int(self.sync_interval)):
                        if not self.running:
                            break
                        time.sleep(1)

        # Iniciar thread
        self.sync_thread = threading.Thread(
            target=sync_loop, daemon=True, name="GestaoSyncThread"
        )
        self.sync_thread.start()
        return self.sync_thread

    def stop_periodic_sync(self):
        """Parar sincronização periódica"""
        self.running = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
        self.logger.info("Sincronização periódica parada")

    def _get_server_info(self) -> Dict[str, Any]:
        """Obter informações do servidor"""
        # Verificar se servidor está online
        is_online = False
        try:
            # Tentar obter server_manager do main.py para verificar se está rodando
            import sys

            if "main" in sys.modules:
                from main import server_manager

                if server_manager:
                    is_online = (
                        server_manager.is_running()
                        if hasattr(server_manager, "is_running")
                        else False
                    )
        except Exception:
            pass

        server_info = {
            "name": self.config.get("communication", {}).get(
                "server_name", "Servidor SCUM"
            ),
            "region": self.config.get("communication", {}).get("region", "americas"),
            "version": "3.0.0",  # Versão do SSM
            "max_players": self.config.get("server", {}).get("max_players", 64),
            "current_players": self._get_current_players_count(),
            "is_online": is_online,
        }

        try:
            base_url, source = self._get_backend_base_url_cached()
            if base_url and source:
                server_info["backend_base_url"] = base_url
                server_info["backend_base_url_source"] = source
                checked = self._get_backend_base_url_checked_cached(base_url)
                if checked is not None:
                    server_info["backend_base_url_checked"] = bool(checked)
        except Exception:
            pass

        return server_info

    def _get_current_players_count(self) -> int:
        """Obter número de jogadores online"""
        db_path = self.path_helper.get_ssm_db_path() if self.path_helper else None
        if not db_path or not os.path.exists(db_path):
            return 0

        try:
            with DatabaseConnector.get_connection(db_path, timeout=30.0, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM players_online WHERE status = 'online'"
                )
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Erro ao contar jogadores online: {e}")
            return 0

    def _get_players_data(self) -> List[Dict[str, Any]]:
        """
        Obter dados dos jogadores - REUTILIZA lógica dos endpoints existentes

        Reutiliza a mesma lógica que:
        - GET /api/players/online
        - GET /api/players/online/list
        """
        players_data = []
        db_path = self.path_helper.get_ssm_db_path() if self.path_helper else None

        if not db_path or not os.path.exists(db_path):
            self.logger.error(f"Banco SSM.db não encontrado: {db_path}")
            return players_data

        try:
            with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Buscar todos os jogadores (online e offline)
                # Usar tabela players_online para status e última atividade
                # REMOVIDO LIMIT 1000 - enviar todos os players conforme documentação v2.0
                # IMPORTANTE: Garantir que player_name nunca seja NULL - buscar de múltiplas fontes
                cursor.execute(
                    """
                    SELECT 
                        po.steam_id,
                        COALESCE(po.player_name, r.player_name, p.player_name, po.steam_id, 'Unknown') as player_name,
                        CASE WHEN po.status = 'online' THEN 1 ELSE 0 END as is_online,
                        po.last_activity as last_seen
                    FROM players_online po
                    LEFT JOIN rankings r ON po.steam_id = r.steam_id
                    LEFT JOIN players p ON po.steam_id = p.steam_id
                    UNION
                    SELECT 
                        r.steam_id,
                        COALESCE(r.player_name, po.player_name, p.player_name, r.steam_id, 'Unknown') as player_name,
                        0 as is_online,
                        NULL as last_seen
                    FROM rankings r
                    LEFT JOIN players_online po ON r.steam_id = po.steam_id
                    LEFT JOIN players p ON r.steam_id = p.steam_id
                    WHERE r.steam_id NOT IN (SELECT steam_id FROM players_online)
                """
                )

                for row in cursor.fetchall():
                    last_seen = row["last_seen"]
                    if last_seen:
                        # Converter para ISO format se for string
                        if isinstance(last_seen, str):
                            try:
                                # Tentar parsear diferentes formatos
                                dt = datetime.fromisoformat(
                                    last_seen.replace("Z", "+00:00")
                                )
                                last_seen_iso = dt.isoformat() + "Z"
                            except:
                                last_seen_iso = last_seen
                        else:
                            last_seen_iso = (
                                last_seen.isoformat() + "Z"
                                if hasattr(last_seen, "isoformat")
                                else str(last_seen)
                            )
                    else:
                        last_seen_iso = None

                    # Garantir que player_name nunca seja None ou vazio
                    player_name = row["player_name"]
                    if not player_name or player_name == "Unknown":
                        # Tentar buscar de outra fonte se disponível
                        player_name = row.get("steam_id") or "Unknown"

                    players_data.append(
                        {
                            "steam_id": row["steam_id"],
                            "player_name": player_name,  # Sempre um valor válido (não None)
                            "is_online": bool(row["is_online"]),
                            "last_seen": last_seen_iso,
                        }
                    )
        except Exception as e:
            self.logger.error(f"Erro ao buscar dados de jogadores: {e}")

        return players_data

    def _get_rankings_data(self) -> Dict[str, Any]:
        """
        Obter dados de rankings no formato completo para Gestão (v3.0)

        Retorna formato: {"players": [...]} com todas as 44 colunas por player
        - 1 registro por player (não mais 1 por categoria)
        - Sem campo 'rank' (calculado pelo Gestão)
        - Todos os valores numéricos são 0 (não null) quando não houver dados
        - Envia todos os players do banco (sem limite)
        """
        rankings_data = {"players": []}
        db_path = self.path_helper.get_ssm_db_path() if self.path_helper else None

        if not db_path or not os.path.exists(db_path):
            self.logger.error(f"Banco SSM.db não encontrado: {db_path}")
            return rankings_data

        try:
            with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Query completa - SEM LIMIT (enviar todos os players)
                # Buscar rankings com player_name de múltiplas fontes para garantir que sempre tenhamos um nome
                query = """
                    SELECT 
                        r.*,
                        COALESCE(
                            r.player_name,
                            po.player_name,
                            p.player_name,
                            r.steam_id
                        ) as player_name_final
                    FROM rankings r
                    LEFT JOIN players_online po ON r.steam_id = po.steam_id
                    LEFT JOIN players p ON r.steam_id = p.steam_id
                    ORDER BY r.kills DESC, r.kdr DESC
                """

                cursor.execute(query)
                rows = cursor.fetchall()

                # Formatar dados no formato esperado pelo Gestão (campos separados)
                for idx, row in enumerate(rows, start=1):
                    # Garantir que player_name nunca seja None
                    # sqlite3.Row não tem .get(), usar indexação direta com try/except
                    player_name = None
                    try:
                        # Tentar pegar player_name_final (do COALESCE na query)
                        player_name = row["player_name_final"]
                    except (KeyError, AttributeError):
                        try:
                            # Se não existir, tentar player_name original
                            player_name = row["player_name"]
                        except (KeyError, AttributeError):
                            pass

                    # Se ainda não tiver nome, usar steam_id como fallback
                    if not player_name or (
                        isinstance(player_name, str) and player_name.strip() == ""
                    ):
                        try:
                            player_name = row["steam_id"]
                        except (KeyError, AttributeError):
                            player_name = "Unknown"

                    player_data = {
                        "steam_id": row["steam_id"],
                        "player_name": player_name,
                        # 'rank' removido - o Gestão calcula automaticamente
                        "kills": row["kills"] or 0,
                        "deaths": row["deaths"] or 0,
                        "kdr": row["kdr"] or 0.0,
                        "headshots": row["headshots"] or 0,
                        "players_knocked_out": row["players_knocked_out"] or 0,
                        "animals_killed": row["animals_killed"] or 0,
                        "minutes_survived": row["minutes_survived"] or 0.0,
                        "total_fame": (
                            row["total_fame"] if row["total_fame"] is not None else 0.0
                        ),
                        "vehicles_destroyed": row["vehicles_destroyed"] or 0,
                        "suicides": row["suicides"] or 0,
                        "overdoses": row["overdoses"] or 0,
                        "highest_weight_carried": row["highest_weight_carried"] or 0.0,
                        "highest_defecation": row["highest_defecation"] or 0,
                        "last_updated": row["last_updated"] or None,
                        # ✅ Campos separados (não objetos aninhados) - conforme documentação v3.0
                        "longest_shot_distance": row["longest_shot_distance"] or 0.0,
                        "longest_shot_weapon": row["longest_shot_weapon"] or None,
                        "longest_shot_timestamp": row["longest_shot_timestamp"] or None,
                        # Lockpicking - campos separados
                        "lockpick_basic_success": row["lockpick_basic_success"] or 0,
                        "lockpick_basic_fails": row["lockpick_basic_fails"] or 0,
                        "lockpick_basic_total": row["lockpick_basic_total"] or 0,
                        "lockpick_basic_rate": row["lockpick_basic_rate"] or 0.0,
                        "lockpick_medium_success": row["lockpick_medium_success"] or 0,
                        "lockpick_medium_fails": row["lockpick_medium_fails"] or 0,
                        "lockpick_medium_total": row["lockpick_medium_total"] or 0,
                        "lockpick_medium_rate": row["lockpick_medium_rate"] or 0.0,
                        "lockpick_advanced_success": row["lockpick_advanced_success"]
                        or 0,
                        "lockpick_advanced_fails": row["lockpick_advanced_fails"] or 0,
                        "lockpick_advanced_total": row["lockpick_advanced_total"] or 0,
                        "lockpick_advanced_rate": row["lockpick_advanced_rate"] or 0.0,
                        "lockpick_veryeasy_success": row["lockpick_veryeasy_success"]
                        or 0,
                        "lockpick_veryeasy_fails": row["lockpick_veryeasy_fails"] or 0,
                        "lockpick_veryeasy_total": row["lockpick_veryeasy_total"] or 0,
                        "lockpick_veryeasy_rate": row["lockpick_veryeasy_rate"] or 0.0,
                        "lockpick_diallock_success": row["lockpick_diallock_success"]
                        or 0,
                        "lockpick_diallock_fails": row["lockpick_diallock_fails"] or 0,
                        "lockpick_diallock_total": row["lockpick_diallock_total"] or 0,
                        "lockpick_diallock_rate": row["lockpick_diallock_rate"] or 0.0,
                        "lockpick_other_success": row["lockpick_other_success"] or 0,
                        "lockpick_other_fails": row["lockpick_other_fails"] or 0,
                        "lockpick_other_total": row["lockpick_other_total"] or 0,
                        "lockpick_other_rate": row["lockpick_other_rate"] or 0.0,
                    }

                    rankings_data["players"].append(player_data)

                if self.logger:
                    players_count = len(rankings_data["players"])
                    self.logger.info(
                        f"📊 Rankings coletados do banco: {players_count} players"
                    )
                    if players_count == 0:
                        self.logger.warn(
                            "⚠️ ATENÇÃO: Nenhum player de ranking encontrado no banco de dados!"
                        )
                    else:
                        # Verificar quantos têm player_name válido (não None, não vazio, não 'Unknown')
                        players_with_name = sum(
                            1
                            for p in rankings_data["players"]
                            if p.get("player_name")
                            and p.get("player_name") not in ["Unknown", "", None]
                        )
                        players_without_name = players_count - players_with_name
                        if players_without_name > 0:
                            self.logger.warn(
                                f"⚠️ ATENÇÃO: {players_without_name} players sem nome válido (será usado steam_id como fallback)"
                            )
                        else:
                            self.logger.info(
                                f"✅ Todos os {players_count} players têm nome válido"
                            )
                            # Log de exemplo do primeiro player (para documentar que player_name está no payload)
                            if rankings_data["players"]:
                                first_player = rankings_data["players"][0]
                                sample_name = first_player.get("player_name", "N/A")
                                sample_steam_id = first_player.get("steam_id", "N/A")
                                self.logger.info(
                                    f"📝 Exemplo de payload: player_name='{sample_name[:30] if sample_name and len(sample_name) > 30 else sample_name}' | steam_id='{sample_steam_id}'"
                                )

        except Exception as e:
            try:
                import traceback

                tb_str = traceback.format_exc()
                self.logger.error(
                    f"Erro ao buscar dados de rankings: {e}", {"traceback": tb_str}
                )
            except:
                self.logger.error(f"Erro ao buscar dados de rankings: {e}")

        return rankings_data
