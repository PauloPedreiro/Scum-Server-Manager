"""
Sistema de Webhooks para Discord
Gerencia notificações automáticas para Discord via webhooks
"""

import json
import time
import mimetypes
import os
import sys
import threading
import tempfile
from contextlib import ExitStack
from pathlib import Path

import requests
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from utils.logger import StructuredLogger

# Tentar importar PIL para redimensionar imagens
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class DiscordWebhook:
    def __init__(self, config: Dict[str, Any], logger: StructuredLogger = None):
        self.config = config
        self.logger = logger or StructuredLogger()

        # Configurações dos webhooks (formato simples)
        self.webhooks = config.get("webhooks", {})

        self._display_name_map = None

        # Rate limiting
        self.max_requests_per_minute = 30
        self.max_requests_per_minute_by_webhook: Dict[str, int] = {
            "bank_transaction": 300,
        }
        self.request_timestamps_by_webhook: Dict[str, List[float]] = {}

        # Rate limit do Discord (429)
        self.rate_limited_until = 0  # Timestamp até quando estamos rate limited
        self.rate_limit_lock = threading.Lock()  # Lock para thread-safety

        # Throttling de logs (evitar spam)
        self.last_rate_limit_log = 0  # Timestamp do último log de rate limit
        self.rate_limit_log_interval = 60  # Log a cada 60 segundos no máximo (mais agressivo)
        self.rate_limit_count = 0  # Contador de rate limits (resetado após log)
        self.last_wait_log = 0  # Timestamp do último log de espera

        self._last_internal_rate_limit_key: Optional[str] = None
        self._last_internal_rate_limit_time: float = 0.0

        # Timeout e retry
        self.timeout = 10
        self.retry_attempts = 3
        self.retry_delay = 5  # segundos

        # Throttling para transações bancárias (evitar spam)
        self.bank_transaction_delay = 0.1  # Delay mínimo entre transações (100ms)
        self.last_bank_transaction_time = 0  # Timestamp da última transação bancária
        self.bank_transaction_lock = threading.Lock()  # Lock para thread-safety

        # Caminho para imagens de traders
        self.traders_images_path = "data/imagens/Traders"
        self.traders_mapping_path = os.path.join(self.traders_images_path, "mapping.json")
        self.traders_mapping = self._load_traders_mapping()

        self.logger.info("DiscordWebhook inicializado")

    def _get_display_name_for_webhook(self, webhook_name: str) -> str:
        try:
            if not webhook_name:
                return ""

            if isinstance(self._display_name_map, dict) and webhook_name in self._display_name_map:
                return str(self._display_name_map.get(webhook_name) or "")

            # Lazy-load from v2 file
            try:
                from pathlib import Path
                from core.webhooks.manager import WebhooksManager

                root_dir = None
                try:
                    root_dir = self.config.get("root_dir")
                except Exception:
                    root_dir = None
                if root_dir:
                    webhooks_path = str(Path(str(root_dir)) / "data" / "webhooks.json")
                else:
                    webhooks_path = str(Path(__file__).resolve().parents[2] / "data" / "webhooks.json")

                mgr = WebhooksManager(webhooks_path)
                meta = mgr.list_events_meta()
                mapping = {}
                for k, v in (meta or {}).items():
                    if isinstance(v, dict):
                        mapping[str(k)] = str(v.get("display_name") or "")
                self._display_name_map = mapping
            except Exception:
                self._display_name_map = {}

            if isinstance(self._display_name_map, dict):
                return str(self._display_name_map.get(webhook_name) or "")
            return ""
        except Exception:
            return ""

    def send_scheduler_notification(self, event: str, data: Dict[str, Any]) -> bool:
        try:
            event_norm = (event or "").strip().lower()

            title_map = {
                "restart_warning": "[SCHEDULER] Restart Warning",
                "restart_scheduled": "[SCHEDULER] Restart Scheduled",
                "restart_started": "[SCHEDULER] Restart Started",
                "restart_completed": "[SCHEDULER] Restart Completed",
                "restart_failed": "[SCHEDULER] Restart Failed",
            }

            color_map = {
                "restart_warning": 0xFFAA00,
                "restart_scheduled": 0x0099FF,
                "restart_started": 0xFFAA00,
                "restart_completed": 0x00FF00,
                "restart_failed": 0xFF0000,
            }

            title = title_map.get(event_norm, f"[SCHEDULER] {event}")
            color = color_map.get(event_norm, 0x0099FF)

            message = ""
            if isinstance(data, dict):
                msg = data.get("message")
                if isinstance(msg, str):
                    message = msg

            if not message:
                message = f"Event: {event}"

            return self.send_webhook(
                webhook_name="log-ssm",
                title=title,
                description=message,
                color=color,
                fields=[],
            )
        except Exception as e:
            self.logger.error(f"Erro ao enviar notificação do scheduler: {e}")
            return False

    def send_server_status(self, event: str, data: Dict[str, Any]) -> bool:
        """Enviar notificacao de status do servidor para o webhook 'serverstatus'.

        Este metodo e usado por endpoints de start/stop/restart no main.py.
        """
        try:
            event_norm = (event or "").strip().lower()

            # Eventos removidos (nao enviar mais para Discord)
            if event_norm in {"server_stopping", "server_stopped", "server_restarted"}:
                return True

            title_map = {
                "server_starting": "🚀 SCUM Server Starting",
                "server_started": "✅ SCUM Server Started",
                "server_start_failed": "❌ SCUM Server Start Failed",
                "server_stop_failed": "🛑 SCUM Server Stop Failed",
                "server_restarting": "🔄 SCUM Server Restarting",
                "server_restart_failed": "❌ SCUM Server Restart Failed",
            }

            color_map = {
                "server_starting": 0xFFAA00,
                "server_started": 0x00FF00,
                "server_start_failed": 0xFF0000,
                "server_stopping": 0xFFAA00,
                "server_stopped": 0xFF0000,
                "server_stop_failed": 0xFF0000,
                "server_restarting": 0xFFAA00,
                "server_restarted": 0x00FF00,
                "server_restart_failed": 0xFF0000,
            }

            title = title_map.get(event_norm, f"SCUM Server Status: {event}")
            color = color_map.get(event_norm, 0x0099FF)

            fields: List[Dict[str, Any]] = []
            if isinstance(data, dict):
                error_msg = data.get("error")
                if isinstance(error_msg, str) and error_msg.strip():
                    fields.append(
                        {
                            "name": "Error",
                            "value": error_msg[:1000],
                            "inline": False,
                        }
                    )

                pid = data.get("pid")
                if pid is not None:
                    fields.append({"name": "PID", "value": str(pid), "inline": True})

                uptime = data.get("uptime")
                if uptime is not None:
                    fields.append(
                        {
                            "name": "Uptime",
                            "value": str(uptime),
                            "inline": True,
                        }
                    )

            # Disparar atualização imediata do Live Dashboard se disponível
            try:
                from app.extensions import get_services
                svc = get_services()
                ws = getattr(svc, "weather_scheduler", None)
                if ws and hasattr(ws, "trigger_immediate_refresh"):
                    ws.trigger_immediate_refresh()
            except Exception:
                pass

            return self.send_webhook(
                webhook_name="log-ssm",
                title=title,
                description="",
                color=color,
                fields=fields,
            )
        except Exception as e:
            self.logger.error(f"Erro ao enviar notificação de status do servidor: {e}")
            return False

    def _get_logo_path(self) -> Optional[str]:
        """Obter caminho da logo SSM para usar como thumbnail nos embeds"""
        try:
            # Detectar se está rodando como executável
            if getattr(sys, "frozen", False):
                # Rodando como executável - usar diretório do .exe
                base_dir = Path(sys.executable).parent
            else:
                # Rodando como script - usar diretório atual
                base_dir = Path.cwd()

            # Caminho da logo
            logo_path = base_dir / "data" / "imagens" / "LogoSSM" / "Logo_SSM.png"

            if logo_path.exists():
                return str(logo_path)
            else:
                self.logger.warn(f"Logo não encontrada em: {logo_path}")
                return None
        except Exception as e:
            self.logger.warn(f"Erro ao obter caminho da logo: {e}")
            return None

    def _load_traders_mapping(self) -> Dict[str, str]:
        """Carregar mapeamento de traders do JSON"""
        try:
            # Detectar se está rodando como executável
            if getattr(sys, "frozen", False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path.cwd()
            
            mapping_path = base_dir / self.traders_mapping_path
            
            if mapping_path.exists():
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                    self.logger.info(f"Mapeamento de traders carregado: {len(mapping)} traders - {list(mapping.keys())}")
                    return mapping
            else:
                self.logger.warn(f"Arquivo mapping.json de traders não encontrado em: {mapping_path}")
                return {}
        except Exception as e:
            self.logger.warn(f"Erro ao carregar mapeamento de traders: {e}")
            return {}

    def _resize_image_for_thumbnail(self, image_path: str, max_size: int = 48) -> Optional[str]:
        """
        Redimensionar imagem para thumbnail pequeno (miniatura)
        
        Args:
            image_path: Caminho da imagem original
            max_size: Tamanho máximo (largura/altura) em pixels (padrão: 48 para miniatura pequena)
        
        Returns:
            Caminho da imagem redimensionada ou None se não conseguir
        """
        if not PIL_AVAILABLE:
            # Se PIL não estiver disponível, usar imagem original
            return image_path
        
        try:
            # Abrir imagem original
            with Image.open(image_path) as img:
                # Obter dimensões
                width, height = img.size
                
                # Se já é menor que max_size, não precisa redimensionar
                if width <= max_size and height <= max_size:
                    return image_path
                
                # Calcular novo tamanho mantendo proporção
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                
                # Redimensionar com alta qualidade
                resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Salvar em arquivo temporário com extensão correta
                temp_dir = Path(tempfile.gettempdir())
                original_ext = Path(image_path).suffix or '.png'
                temp_file = temp_dir / f"ssm_thumbnail_{int(time.time() * 1000)}_{os.path.basename(image_path)}"
                
                # Manter formato original (ou PNG se não conseguir detectar)
                img_format = img.format or 'PNG'
                if img_format == 'WEBP':
                    # WebP mantém qualidade melhor
                    resized.save(temp_file, format='WEBP', quality=85, method=6)
                else:
                    resized.save(temp_file, format=img_format, optimize=True)
                
                self.logger.debug(f"Imagem redimensionada: {image_path} ({width}x{height}) -> {temp_file} ({new_width}x{new_height})")
                return str(temp_file)
        except Exception as e:
            self.logger.debug(f"Erro ao redimensionar imagem {image_path}: {e}")
            # Em caso de erro, usar imagem original
            return image_path

    def _get_trader_image_path(self, transaction_type: str, location: Optional[str] = None) -> Optional[str]:
        """Obter caminho da imagem do trader usando o mapeamento JSON
        
        Args:
            transaction_type: Tipo da transação ('trade_sale' ou 'trade_purchase')
            location: Localização no formato 'QUADRANT_LOCATION_TYPE' (ex: 'A0', 'B4', 'C2', 'Z3')
        
        Returns:
            Caminho completo da imagem ou None se não existir
        """
        # Apenas para transações de trade
        if transaction_type not in ['trade_sale', 'trade_purchase']:
            return None
        
        # Se não tem localização, não pode mapear
        if not location:
            return None
        
        # Extrair o quadrante da localização
        # Ex: 'C_2_Mechanic' -> 'C_2' -> 'C2', 'B_4_Trader' -> 'B_4' -> 'B4'
        # O formato é: QUADRANT_LOCATION_TYPE
        parts = location.split('_')
        if len(parts) >= 2:
            # Pegar as duas primeiras partes (quadrante tem formato "C_2" ou "A_0")
            quadrant_with_underscore = f"{parts[0]}_{parts[1]}"
            # Remover underscore para ficar "C2", "A0", "B4", "Z3"
            quadrant = quadrant_with_underscore.replace('_', '')
        else:
            # Se não tem formato esperado, tentar usar direto
            quadrant = location.split('_')[0] if '_' in location else location
            # Remover underscore se houver
            quadrant = quadrant.replace('_', '')
        
        # Construir chave do mapeamento: QUADRANT_TIPO
        # Ex: 'A0_Sale', 'B4_Purchase', 'C2_Sale'
        if transaction_type == 'trade_sale':
            mapping_key = f"{quadrant}_Sale"
        elif transaction_type == 'trade_purchase':
            mapping_key = f"{quadrant}_Purchase"
        else:
            return None
        
        # Log para debug
        self.logger.debug(f"Buscando imagem de trader: location={location}, quadrant={quadrant}, mapping_key={mapping_key}")
        
        # Buscar no mapeamento
        image_filename = self.traders_mapping.get(mapping_key)
        
        # Se não está no mapeamento ou está vazio, retornar None
        if not image_filename or image_filename.strip() == "":
            self.logger.debug(f"Chave '{mapping_key}' não encontrada no mapeamento ou está vazia. Chaves disponíveis: {list(self.traders_mapping.keys())}")
            return None
        
        # Construir caminho completo
        try:
            # Detectar se está rodando como executável
            if getattr(sys, "frozen", False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path.cwd()
            
            image_path = base_dir / self.traders_images_path / image_filename
            
            # Verificar se o arquivo existe
            if image_path.exists():
                self.logger.debug(f"Imagem de trader encontrada: {image_path} para {mapping_key}")
                return str(image_path)
            else:
                self.logger.warn(f"Imagem de trader não encontrada no caminho: {image_path} (arquivo: {image_filename}, chave: {mapping_key})")
                return None
        except Exception as e:
            self.logger.debug(f"Erro ao obter caminho da imagem de trader: {e}")
            return None

    def _check_rate_limit(self, webhook_key: str) -> bool:
        """Verificar rate limit interno (30 req/min) com throttling de logs"""
        now = time.time()

        max_per_minute = self.max_requests_per_minute_by_webhook.get(
            webhook_key, self.max_requests_per_minute
        )

        bucket = self.request_timestamps_by_webhook.get(webhook_key)
        if bucket is None:
            bucket = []
            self.request_timestamps_by_webhook[webhook_key] = bucket

        # Remover timestamps antigos (mais de 1 minuto)
        bucket[:] = [ts for ts in bucket if now - ts < 60]

        # Verificar se pode fazer nova requisição
        if len(bucket) >= max_per_minute:
            # Throttling: log apenas a cada X segundos (60s) e usar DEBUG em vez de WARN
            # Rate limit interno é comportamento esperado, não é um erro crítico
            if now - self.last_rate_limit_log >= self.rate_limit_log_interval:
                # Incrementar contador antes de logar
                self.rate_limit_count += 1
                # Usar DEBUG em vez de WARN - comportamento esperado, não é erro
                self.logger.debug(
                    f"Rate limit interno atingido ({webhook_key}): {len(bucket)}/{max_per_minute} "
                    f"requisições por minuto (ocorrências desde último log: {self.rate_limit_count})"
                )
                self.last_rate_limit_log = now
                self.rate_limit_count = 0
            else:
                # Apenas incrementar contador sem logar
                self.rate_limit_count += 1
            return False

        return True
    
    def _wait_for_rate_limit(self) -> None:
        """Aguardar até que o rate limit do Discord seja liberado (com throttling de logs)"""
        with self.rate_limit_lock:
            now = time.time()
            if self.rate_limited_until > now:
                wait_time = self.rate_limited_until - now
                if wait_time > 0:
                    # Throttling: log apenas a cada X segundos
                    if now - self.last_wait_log >= self.rate_limit_log_interval:
                        self.logger.warn(f"Rate limited pelo Discord. Aguardando {wait_time:.2f} segundos...")
                        self.last_wait_log = now
                    time.sleep(wait_time)
    
    def _handle_rate_limit_response(self, response: requests.Response) -> bool:
        """Tratar resposta 429 do Discord e extrair retry_after (com throttling de logs)"""
        if response.status_code == 429:
            try:
                error_data = response.json()
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
                
                # Throttling: log apenas a cada X segundos
                now = time.time()
                if now - self.last_rate_limit_log >= self.rate_limit_log_interval:
                    self.logger.warn(f"Rate limited pelo Discord. Retry after: {retry_after:.2f}s")
                    self.last_rate_limit_log = now
                    self.rate_limit_count = 0
                else:
                    self.rate_limit_count += 1
                
                return True  # Indica que foi rate limited
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                # Log de erro sempre (não throttling para erros)
                self.logger.warn(f"Erro ao processar resposta de rate limit: {e}")
                # Em caso de erro, usar delay padrão
                with self.rate_limit_lock:
                    self.rate_limited_until = time.time() + 1.0
                return True
        
        return False  # Não foi rate limited

    def _send_webhook(self, webhook_url: str, payload: Dict[str, Any], webhook_key: Optional[str] = None) -> bool:
        """Enviar webhook para Discord com tratamento de rate limit"""
        try:
            effective_key = webhook_key or webhook_url

            # 1. Verificar se estamos em rate limit do Discord antes de tentar
            with self.rate_limit_lock:
                now = time.time()
                if self.rate_limited_until > now:
                    # Estamos em rate limit, aguardar silenciosamente (sem log)
                    wait_time = self.rate_limited_until - now
                    if wait_time > 0:
                        time.sleep(wait_time)
            
            # 2. Aguardar se ainda estivermos em rate limit (após sleep)
            self._wait_for_rate_limit()
            
            # 3. Verificar rate limit interno (30 req/min)
            if not self._check_rate_limit(effective_key):
                self._last_internal_rate_limit_key = effective_key
                self._last_internal_rate_limit_time = time.time()
                return False

            # 4. Adicionar timestamp da requisição
            bucket = self.request_timestamps_by_webhook.get(effective_key)
            if bucket is None:
                bucket = []
                self.request_timestamps_by_webhook[effective_key] = bucket
            bucket.append(time.time())

            # 4. Enviar requisição
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )

            # 5. Tratar resposta
            if response.status_code in (200, 204):
                # Sucesso - limpar rate limit
                with self.rate_limit_lock:
                    self.rate_limited_until = 0
                self.logger.info(f"Webhook enviado com sucesso para Discord")
                return True
            elif response.status_code == 429:
                # Rate limited - tratar e retornar False (não tentar novamente aqui)
                self._handle_rate_limit_response(response)
                return False
            else:
                # Outro erro
                self.logger.error(
                    f"Erro ao enviar webhook: {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.Timeout:
            self.logger.error("Timeout ao enviar webhook para Discord")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro de rede ao enviar webhook: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Erro inesperado ao enviar webhook: {e}")
            return False

    def _send_webhook_with_retry(
        self, webhook_url: str, payload: Dict[str, Any], webhook_key: Optional[str] = None
    ) -> bool:
        """Enviar webhook com retry automático e tratamento de rate limit"""
        effective_key = webhook_key or webhook_url
        for attempt in range(self.retry_attempts):
            if self._send_webhook(webhook_url, payload, webhook_key=webhook_key):
                return True

            if (
                self._last_internal_rate_limit_key == effective_key
                and (time.time() - self._last_internal_rate_limit_time) < 2.0
            ):
                self.logger.warn(
                    f"Rate limit interno bloqueou envio do webhook '{effective_key}'. Sem retries adicionais nesta chamada."
                )
                return False

            # Se foi rate limited, aguardar antes de tentar novamente
            if attempt < self.retry_attempts - 1:
                # Aguardar rate limit se estivermos limitados
                self._wait_for_rate_limit()
                # Aguardar delay adicional apenas se não estivermos rate limited
                with self.rate_limit_lock:
                    if self.rate_limited_until <= time.time():
                        # Não estamos mais rate limited, usar delay padrão
                        self.logger.warn(
                            f"Tentativa {attempt + 1} falhou, aguardando {self.retry_delay}s..."
                        )
                        time.sleep(self.retry_delay)
                    # Se ainda estivermos rate limited, _wait_for_rate_limit já aguardou

        self.logger.error(
            f"Falha ao enviar webhook '{effective_key}' após {self.retry_attempts} tentativas"
        )
        return False

    def _create_embed(
        self,
        title: str,
        description: str,
        color: int,
        fields: List[Dict[str, Any]] = None,
        footer: str = None,
    ) -> Dict[str, Any]:
        """Criar embed do Discord"""
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "fields": fields or [],
        }

        if footer:
            embed["footer"] = {"text": footer}

        return embed

    def _get_status_color(self, status: str) -> int:
        """Obter cor baseada no status"""
        color_map = {
            "success": 0x00FF00,  # Verde
            "error": 0xFF0000,  # Vermelho
            "warning": 0xFFAA00,  # Laranja
            "info": 0x0099FF,  # Azul
            "starting": 0xFFAA00,  # Laranja
            "stopping": 0xFFAA00,  # Laranja
            "running": 0x00FF00,  # Verde
            "stopped": 0xFF0000,  # Vermelho
        }
        return color_map.get(status.lower(), 0x0099FF)

    def _get_status_emoji(self, status: str) -> str:
        """Obter emoji baseado no status"""
        emoji_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "starting": "🚀",
            "started": "✅",
            "stopping": "🛑",
            "stopped": "⏹️",
            "restarting": "🔄",
            "restarted": "✅",
            "running": "🟢",
            "scheduled": "📅",
        }
        return emoji_map.get(status.lower(), "ℹ️")

    def send_webhook(
        self,
        webhook_name: str,
        title: str,
        description: str,
        color: int = 0x0099FF,
        fields: List[Dict[str, Any]] = None,
        thumbnail_path: Optional[str] = None,
    ) -> bool:
        """Enviar webhook genérico para Discord

        Args:
            webhook_name: Nome do webhook configurado
            title: Título do embed
            description: Descrição do embed
            color: Cor do embed (hex)
            fields: Lista de campos do embed
            thumbnail_path: Caminho opcional para imagem de thumbnail
        """
        try:
            webhook_url = self.webhooks.get(webhook_name, "")
            if not webhook_url:
                self.logger.debug(f"Webhook '{webhook_name}' não configurado")
                return False

            try:
                display_name = self._get_display_name_for_webhook(webhook_name)
                if display_name and str(display_name).strip():
                    title = f"{str(display_name).strip()} - {title}" if title else str(display_name).strip()
            except Exception:
                pass

            # Criar embed
            embed = self._create_embed(
                title=title,
                description=description,
                color=color,
                fields=fields or [],
                footer="SCUM Backend - Management System",
            )

            # Se não foi fornecido thumbnail_path, tentar usar logo padrão
            if thumbnail_path is None:
                thumbnail_path = self._get_logo_path()

            # Se houver thumbnail, usar método com attachment
            if thumbnail_path and os.path.exists(thumbnail_path):
                return self.send_embed_with_image(
                    webhook_name=webhook_name,
                    embed=embed,
                    thumbnail_path=thumbnail_path,
                )

            # Criar payload sem thumbnail
            payload = {"embeds": [embed]}

            # Enviar webhook
            success = self._send_webhook_with_retry(webhook_url, payload, webhook_key=webhook_name)

            if success:
                self.logger.info(f"Webhook '{webhook_name}' enviado com sucesso")
            else:
                self.logger.error(f"Falha ao enviar webhook '{webhook_name}'")

            return success

        except Exception as e:
            self.logger.error(f"Erro ao enviar webhook '{webhook_name}': {e}")
            return False

    def send_text_webhook(self, webhook_name: str, content: str) -> bool:
        """Enviar mensagem de texto simples para Discord
        
        Args:
            webhook_name: Nome do webhook configurado
            content: Conteúdo em texto da mensagem
        """
        try:
            webhook_url = self.webhooks.get(webhook_name, "")
            if not webhook_url:
                self.logger.debug(f"Webhook '{webhook_name}' não configurado")
                return False

            payload = {"content": content}
            success = self._send_webhook_with_retry(webhook_url, payload, webhook_key=webhook_name)
            if success:
                self.logger.info(f"Webhook de texto '{webhook_name}' enviado com sucesso")
            else:
                self.logger.error(f"Falha ao enviar webhook de texto '{webhook_name}'")
            return success
        except Exception as e:
            self.logger.error(f"Erro ao enviar webhook de texto '{webhook_name}': {e}")
            return False

    def send_embed_with_image(
        self,
        webhook_name: str,
        embed: Dict[str, Any],
        image_path: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
        extra_attachments: Optional[List[Tuple[str, str]]] = None,
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Enviar embed customizado, anexando uma ou mais imagens locais se disponível."""
        try:
            webhook_url = self.webhooks.get(webhook_name, "")
            if not webhook_url:
                self.logger.debug(f"Webhook '{webhook_name}' não configurado")
                return False

            embed_payload = dict(embed)
            attachments: List[Tuple[str, str, str, str]] = []  # (label, path, filename, mime)

            if image_path and os.path.exists(image_path):
                filename = os.path.basename(image_path)
                mime_type = (
                    mimetypes.guess_type(filename)[0] or "application/octet-stream"
                )
                attachments.append(("image", image_path, filename, mime_type))
                embed_payload.setdefault("image", {"url": f"attachment://{filename}"})

            if thumbnail_path and os.path.exists(thumbnail_path):
                filename = os.path.basename(thumbnail_path)
                mime_type = (
                    mimetypes.guess_type(filename)[0] or "application/octet-stream"
                )
                attachments.append(("thumbnail", thumbnail_path, filename, mime_type))
                embed_payload.pop("image", None)
                embed_payload.setdefault(
                    "thumbnail", {"url": f"attachment://{filename}"}
                )

            if extra_attachments:
                for label, path in extra_attachments:
                    if not path or not os.path.exists(path):
                        continue
                    filename = os.path.basename(path)
                    mime_type = (
                        mimetypes.guess_type(filename)[0] or "application/octet-stream"
                    )
                    attachments.append((label or "attachment", path, filename, mime_type))

            payload_data: Dict[str, Any] = {"embeds": [embed_payload]}
            if components:
                payload_data["components"] = components

            if not attachments:
                return self._send_webhook_with_retry(
                    webhook_url, payload_data, webhook_key=webhook_name
                )

            payload_data["attachments"] = [
                {"id": str(idx), "filename": filename}
                for idx, (_, _, filename, _) in enumerate(attachments)
            ]

            payload_json = json.dumps(payload_data, ensure_ascii=False)

            last_status_code = None
            last_error_preview = None

            for attempt in range(self.retry_attempts):
                with self.rate_limit_lock:
                    now = time.time()
                    if self.rate_limited_until > now:
                        wait_time = self.rate_limited_until - now
                        if wait_time > 0:
                            time.sleep(wait_time)

                self._wait_for_rate_limit()

                if not self._check_rate_limit(webhook_name):
                    time.sleep(self.retry_delay)
                    continue

                bucket = self.request_timestamps_by_webhook.get(webhook_name)
                if bucket is None:
                    bucket = []
                    self.request_timestamps_by_webhook[webhook_name] = bucket
                bucket.append(time.time())

                response = None
                try:
                    with ExitStack() as stack:
                        files_payload = []
                        for idx, (_, path, filename, mime_type) in enumerate(attachments):
                            file_obj = stack.enter_context(open(path, "rb"))
                            files_payload.append(
                                (f"files[{idx}]", (filename, file_obj, mime_type))
                            )

                        response = requests.post(
                            webhook_url,
                            data={"payload_json": payload_json},
                            files=files_payload,
                            timeout=self.timeout,
                        )

                    if response.status_code in (200, 204):
                        with self.rate_limit_lock:
                            self.rate_limited_until = 0
                        self.logger.info(f"Webhook '{webhook_name}' enviado com anexos")
                        return True

                    if response.status_code == 429:
                        self._handle_rate_limit_response(response)
                        if attempt < self.retry_attempts - 1:
                            self._wait_for_rate_limit()
                            continue

                    error_text = response.text[:200] if response.text else "Sem resposta"
                    last_status_code = response.status_code
                    last_error_preview = error_text
                    self.logger.error(
                        f"Erro ao enviar webhook '{webhook_name}' com anexos: {response.status_code} - {error_text}",
                        {
                            'status_code': response.status_code,
                            'webhook_name': webhook_name,
                            'attempt': attempt + 1,
                            'error_preview': error_text,
                        },
                    )

                    if attempt < self.retry_attempts - 1:
                        self.logger.warn(
                            f"Tentativa {attempt + 1}/{self.retry_attempts} falhou, aguardando {self.retry_delay}s..."
                        )
                        time.sleep(self.retry_delay)
                except Exception as e:
                    last_status_code = None
                    last_error_preview = str(e)[:200]
                    self.logger.error(
                        f"Erro ao enviar webhook '{webhook_name}' com anexos: {e}",
                        {
                            'status_code': None,
                            'webhook_name': webhook_name,
                            'attempt': attempt + 1,
                            'error_preview': last_error_preview,
                        },
                    )
                    if attempt < self.retry_attempts - 1:
                        self.logger.warn(
                            f"Tentativa {attempt + 1}/{self.retry_attempts} falhou, aguardando {self.retry_delay}s..."
                        )
                        time.sleep(self.retry_delay)
                finally:
                    try:
                        if response is not None:
                            response.close()
                    except Exception:
                        pass

            self.logger.error(
                f"Falha ao enviar webhook '{webhook_name}' com anexos após tentativas",
                {
                    'status_code': last_status_code,
                    'webhook_name': webhook_name,
                    'error_preview': last_error_preview,
                },
            )

            fallback_payload: Dict[str, Any] = {"embeds": [embed_payload]}
            if components:
                fallback_payload["components"] = components

            fallback_ok = self._send_webhook_with_retry(
                webhook_url, fallback_payload, webhook_key=webhook_name
            )
            if fallback_ok:
                self.logger.warn(
                    f"Webhook '{webhook_name}' enviado sem anexos após falha com anexos"
                )
                return True

            return False

        except Exception as e:
            self.logger.error(
                f"Erro ao enviar webhook '{webhook_name}' com anexos: {e}"
            )
            return False

    def send_bank_transaction_notification(self, transaction_data: Dict[str, Any]) -> bool:

        """
        Enviar notificação de transação bancária para Discord
        
        Args:
            transaction_data: Dicionário com dados da transação:
                - type: Tipo da transação (trade_sale, bank_deposit, etc.)
                - player_name: Nome do jogador
                - steam_id: Steam ID do jogador
                - transaction_value: Valor da transação
                - currency_type: Tipo de moeda (money, gold, credits)
                - location: Local da transação (opcional)
                - item_name: Nome do item (opcional)
                - balance_before/after: Saldos antes/depois (opcional)
                - timestamp: Timestamp da transação
        
        Returns:
            True se enviado com sucesso
        """
        transaction_type = transaction_data.get('type', '')
        try:
            webhook_url = self.webhooks.get("bank_transaction")
            if not webhook_url:
                self.logger.warn("Webhook 'bank_transaction' não configurado")
                return False

            with self.bank_transaction_lock:
                now = time.time()
                time_since_last = now - self.last_bank_transaction_time
                if time_since_last < self.bank_transaction_delay:
                    time.sleep(self.bank_transaction_delay - time_since_last)
                self.last_bank_transaction_time = time.time()

            def format_value(val):
                val_str = f"{val:,.0f}"
                return val_str.replace(",", ".")

            type_config = {
                'trade_sale': {
                    'emoji': '💰',
                    'title_short': 'Sale',
                    'color': 0x00FF00,
                },
                'trade_purchase': {
                    'emoji': '🛒',
                    'title_short': 'Purchase',
                    'color': 0xFFA500,
                },
                'bank_deposit': {
                    'emoji': '📥',
                    'title_short': 'Deposit',
                    'color': 0x0099FF,
                },
                'bank_withdrawal': {
                    'emoji': '📤',
                    'title_short': 'Withdrawal',
                    'color': 0xFFFF00,
                },
                'currency_conversion': {
                    'emoji': '💎',
                    'title_short': 'Conversion',
                    'color': 0x9932CC,
                },
                'service_repair': {
                    'emoji': '🔧',
                    'title_short': 'Repair',
                    'color': 0x808080,
                },
                'service_modification': {
                    'emoji': '⚙️',
                    'title_short': 'Modification',
                    'color': 0x00FFFF,
                }
            }

            config = type_config.get(transaction_type, {
                'emoji': '💳',
                'title_short': 'Transaction',
                'color': 0x0099FF,
            })

            location = None
            if 'quadrant' in transaction_data and 'location_type' in transaction_data:
                location = f"{transaction_data['quadrant']}_{transaction_data['location_type']}"

            if location:
                title = f"{config['emoji']} {config['title_short']} {location}"
            else:
                title = f"{config['emoji']} {config['title_short']}"

            description_lines = []

            player_name = transaction_data.get('player_name', 'Unknown')
            description_lines.append(f"👤 {player_name}")

            if 'item_name' in transaction_data and transaction_data['item_name']:
                import re
                item_name = transaction_data['item_name']

                # Limpeza ULTRA agressiva: remover TODOS os parênteses e seu conteúdo
                # Estratégia: encontrar o nome base antes do primeiro parêntese

                # 1. Extrair apenas o nome base (tudo antes do primeiro parêntese)
                # Isso garante que pegamos apenas "ItemName" sem nada adicional
                match = re.match(r'^([^\(]+)', item_name)
                if match:
                    item_name = match.group(1).strip()
                else:
                    # Se não houver parênteses, usar o nome completo
                    item_name = item_name.strip()

                # 2. Limpar espaços extras, vírgulas e outros caracteres residuais
                item_name = re.sub(r'[,;]\s*$', '', item_name)  # Remover vírgulas e ponto-e-vírgula no final
                item_name = re.sub(r'\s+', ' ', item_name)  # Normalizar espaços múltiplos
                item_name = item_name.strip()

                # 3. Garantir que não ficou vazio
                if not item_name:
                    item_name = "Unknown Item"

                item_quantity = transaction_data.get('item_quantity', 1)
                # Mostrar quantidade apenas se for maior que 1
                if item_quantity > 1:
                    item_display = f"{item_name} (x{item_quantity})"
                else:
                    item_display = item_name
                description_lines.append(f"📦 {item_display}")

            # Tratamento especial para conversão de moeda
            if transaction_type == 'currency_conversion':
                # Obter dados específicos de conversão
                gold_amount = transaction_data.get('gold_amount', 0)
                credits_spent = transaction_data.get('transaction_value', 0)  # credits gastos

                # Formato visual com seta: 💰 credits → 🪙 gold
                credits_formatted = format_value(credits_spent)
                gold_formatted = format_value(gold_amount)
                conversion_text = f"💰 {credits_formatted} credits → 🪙 {gold_formatted} gold"
                description_lines.append(conversion_text)

                # Saldo após conversão (usar balance_after_gold e balance_after_account se disponíveis)
                balance_after_gold = transaction_data.get('balance_after_gold')
                balance_after_account = transaction_data.get('balance_after_account')

                # Se não estiver nos campos diretos, tentar balance_after dict
                if balance_after_gold is None or balance_after_account is None:
                    balance_after = transaction_data.get('balance_after', {})
                    if balance_after:
                        balance_after_account = balance_after.get('account', balance_after_account)
                        balance_after_gold = balance_after.get('gold', balance_after_gold)

                # Mostrar saldo final
                if balance_after_account is not None:
                    description_lines.append(f"💵 Credits: {format_value(balance_after_account)}")
                if balance_after_gold is not None:
                    description_lines.append(f"🪙 Gold: {format_value(balance_after_gold)}")
            else:
                # 💰 Valor (para outros tipos de transação)
                transaction_value = transaction_data.get('transaction_value', 0)
                currency_type = transaction_data.get('currency_type', 'money')

                value_formatted = format_value(transaction_value)

                # Determinar moeda para exibição
                currency_display = {
                    'money': 'money',
                    'gold': 'gold',
                    'credits': 'credits'
                }.get(currency_type, 'money')

                value_text = f"{value_formatted} {currency_display}"
                description_lines.append(f"💰 {value_text}")

                # 💵 Balance (Account e Gold em linhas separadas)
                balance_after = transaction_data.get('balance_after', {})
                if balance_after:
                    account_after = balance_after.get('account', 0)
                    gold_after = balance_after.get('gold', 0)

                    # Account em uma linha
                    description_lines.append(f"💵 Account: {format_value(account_after)}")

                    # Gold em outra linha com ícone de barra de ouro
                    description_lines.append(f"🪙 Gold: {format_value(gold_after)}")

            # Juntar todas as linhas da descrição
            description = "\n".join(description_lines)

            # Formatar footer com timestamp
            footer_text = "SCUM SSM Backend"
            timestamp = transaction_data.get('timestamp')
            if timestamp:
                try:
                    # Converter timestamp do formato SCUM (2025.12.06-00.41.27)
                    dt = datetime.strptime(timestamp, "%Y.%m.%d-%H.%M.%S")
                    # Formatar: "Today at HH:MM" ou "MM/DD at HH:MM"
                    now = datetime.now()
                    if dt.date() == now.date():
                        footer_text = f"SCUM SSM Backend•Today at {dt.strftime('%H:%M')}"
                    else:
                        footer_text = f"SCUM SSM Backend•{dt.strftime('%m/%d at %H:%M')}"
                except Exception:
                    pass  # Ignorar erro de parsing de timestamp

            # Criar embed (descrição formatada verticalmente, sem campos)
            embed = self._create_embed(
                title=title,
                description=description,
                color=config['color'],
                fields=[],  # Sem campos, tudo na descrição
                footer=footer_text
            )

            # Buscar imagem do trader se for transação de trade
            thumb_path = None
            if transaction_type in ['trade_sale', 'trade_purchase']:
                original_path = self._get_trader_image_path(transaction_type, location)
                if original_path and os.path.exists(original_path):
                    # Redimensionar imagem para thumbnail bem pequeno (48x48 max - miniatura)
                    thumb_path = self._resize_image_for_thumbnail(original_path, max_size=48)
                    # Log para debug
                    self.logger.debug(f"Imagem de trader encontrada: {original_path} (redimensionada: {thumb_path}) para {transaction_type} em {location}")
                else:
                    self.logger.debug(f"Imagem de trader não encontrada para {transaction_type} em {location}")

            # Se tem thumbnail, usar método com imagem
            if thumb_path and os.path.exists(thumb_path):
                return self.send_embed_with_image(
                    webhook_name="bank_transaction",
                    embed=embed,
                    thumbnail_path=thumb_path
                )

            # Preparar payload sem thumbnail
            payload = {"embeds": [embed]}

            # Enviar requisição com retry e tratamento de rate limit
            success = self._send_webhook_with_retry(webhook_url, payload, webhook_key="bank_transaction")

            if success:
                self.logger.debug(f"Notificação de transação bancária enviada: {transaction_type}")
                return True
            else:
                # Logar com mais detalhes para debug (mas não poluir logs em produção)
                self.logger.debug(f"Falha ao enviar notificação de transação bancária: {transaction_type}")
                return False

        except Exception as e:
            self.logger.error(f"Erro ao enviar notificação de transação bancária: {e}", {
                'transaction_type': transaction_type,
                'error_type': type(e).__name__,
                'error_message': str(e)
            })
            return False