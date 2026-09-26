"""
Serviço de Rankings de Lockpicking por Tipo (Top 10 Live Dashboard)
Gera e atualiza rankings top 10 de lockpicking separados por tipo para Discord em mensagem única via PATCH
"""

import os
import json
import hashlib
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests

import schedule

from utils.logger import StructuredLogger


class LockpickingRankingService:
    """Serviço para gerar e enviar rankings de lockpicking por tipo (Top 10 Live Dashboard)"""

    # Mapeamento de tipos de fechadura com suas imagens e cores
    LOCK_TYPES = {
        "veryeasy": {
            "name": "VeryEasy",
            "display_name": "🔓 VERY EASY LOCKS — TOP 10",
            "image_url": "https://i.imgur.com/xXjtBhJ.png",
            "color": 0x2ECC71,  # Verde
        },
        "basic": {
            "name": "Basic",
            "display_name": "🔓 BASIC LOCKS — TOP 10",
            "image_url": "https://i.imgur.com/QfzkYqd.png",
            "color": 0x3498DB,  # Azul
        },
        "medium": {
            "name": "Medium",
            "display_name": "🔒 MEDIUM LOCKS — TOP 10",
            "image_url": "https://i.imgur.com/LO2jnNN.png",
            "color": 0xE67E22,  # Laranja
        },
        "advanced": {
            "name": "Advanced",
            "display_name": "🔐 ADVANCED LOCKS — TOP 10",
            "image_url": "https://i.imgur.com/ng5La4h.png",
            "color": 0xE74C3C,  # Vermelho
        },
        "diallock": {
            "name": "DialLock",
            "display_name": "🔢 DIAL LOCKS — TOP 10",
            "image_url": "https://i.imgur.com/xE2xtq1.png",
            "color": 0x9B59B6,  # Roxo
        },
        "other": {
            "name": "Other",
            "display_name": "🗄️ OTHER LOCKS — TOP 10",
            "image_url": None,
            "color": 0x95A5A6,  # Cinza
        },
    }

    def __init__(
        self,
        ssm_db_path: str,
        webhook_url: str,
        webhooks_path: str = "data/webhooks.json",
        logger: Optional[StructuredLogger] = None,
        min_attempts: int = 10,
        top_n: int = 10,
        schedule_time: str = "00:00",
        interval_minutes: int = 15,
    ):
        self.logger = logger or StructuredLogger()
        self.ssm_db_path = ssm_db_path
        self.webhook_url = webhook_url
        self.webhooks_path = webhooks_path
        self.min_attempts = min_attempts
        self.top_n = top_n
        self.schedule_time = schedule_time
        self.interval_minutes = max(1, interval_minutes)

        self.scheduler = schedule.Scheduler()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False

        self.last_send_info: Dict[str, Any] = {
            "timestamp": None,
            "status": "never_sent",
            "details": {},
        }

        self.logger.info(
            "LockpickingRankingService inicializado",
            {
                "min_attempts": self.min_attempts,
                "top_n": self.top_n,
                "schedule_time": self.schedule_time,
                "interval_minutes": self.interval_minutes,
                "webhook_configured": bool(self.webhook_url),
            },
        )

    def start(self) -> Dict[str, Any]:
        """Iniciar serviço de sincronização automática"""
        if self.is_running:
            return {"success": False, "message": "Serviço já está em execução"}

        try:
            # Agendar sincronização periódica e diária
            self.scheduler.every(self.interval_minutes).minutes.do(
                self._send_rankings_job
            )
            self.scheduler.every().day.at(self.schedule_time).do(
                self._send_rankings_job
            )

            # Iniciar thread do scheduler
            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._run_scheduler, daemon=True
            )
            self.scheduler_thread.start()

            self.is_running = True

            self.logger.info(
                f"LockpickingRankingService iniciado - agendado a cada {self.interval_minutes}m e diariamente às {self.schedule_time}"
            )

            return {
                "success": True,
                "message": "Serviço iniciado com sucesso",
                "interval_minutes": self.interval_minutes,
                "next_send": f"{self.schedule_time} (diariamente)",
            }

        except Exception as e:
            self.logger.error(f"Erro ao iniciar LockpickingRankingService: {e}")
            return {"success": False, "message": f"Erro ao iniciar: {str(e)}"}

    def stop(self) -> Dict[str, Any]:
        """Parar serviço"""
        try:
            self.is_running = False
            self.stop_event.set()

            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)

            self.logger.info("LockpickingRankingService parado")
            return {"success": True, "message": "Serviço parado com sucesso"}

        except Exception as e:
            self.logger.error(f"Erro ao parar LockpickingRankingService: {e}")
            return {"success": False, "message": f"Erro ao parar: {str(e)}"}

    def _run_scheduler(self):
        """Executar scheduler em thread separada"""
        while not self.stop_event.is_set():
            self.scheduler.run_pending()
            time.sleep(30)

    def _send_rankings_job(self):
        """Job agendado para enviar rankings"""
        try:
            self.logger.info("Iniciando sincronização de rankings de lockpicking...")
            result = self.send_rankings()
            if result.get("success"):
                if result.get("skipped"):
                    self.logger.debug(
                        "Sincronização de rankings de lockpicking ignorada (dados inalterados ou webhook vazio)"
                    )
                else:
                    self.logger.info(
                        "Rankings de lockpicking sincronizados com sucesso no Discord"
                    )
            else:
                self.logger.error(
                    f"Falha ao sincronizar rankings de lockpicking: {result.get('message')}"
                )
        except Exception as e:
            self.logger.error(f"Erro no job de sincronização de rankings: {e}")

    def get_lockpicking_rankings(self, lock_type: str) -> List[Dict[str, Any]]:
        """
        Obter ranking de lockpicking por tipo

        Args:
            lock_type: Tipo de fechadura (basic, medium, advanced, veryeasy, diallock, other)

        Returns:
            Lista de jogadores ordenados por total de sucessos
        """
        try:
            conn = sqlite3.connect(self.ssm_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            lock_type_key = lock_type.lower()
            success_col = f"lockpick_{lock_type_key}_success"
            fails_col = f"lockpick_{lock_type_key}_fails"
            total_col = f"lockpick_{lock_type_key}_total"
            rate_col = f"lockpick_{lock_type_key}_rate"

            # Verificar se as colunas existem
            cursor.execute("PRAGMA table_info(rankings)")
            columns = [row[1] for row in cursor.fetchall()]

            if success_col not in columns:
                self.logger.warn(
                    f"Coluna {success_col} não encontrada na tabela rankings"
                )
                conn.close()
                return []

            # Buscar rankings ordenados por total de sucessos (descendente)
            query = f"""
                SELECT 
                    steam_id,
                    player_name,
                    {success_col} as success,
                    {fails_col} as fails,
                    {total_col} as total,
                    {rate_col} as rate
                FROM rankings
                WHERE {total_col} >= ?
                ORDER BY {success_col} DESC, player_name ASC
                LIMIT ?
            """

            cursor.execute(query, (self.min_attempts, self.top_n))
            rows = cursor.fetchall()

            rankings = []
            for rank, row in enumerate(rows, start=1):
                rankings.append(
                    {
                        "rank": rank,
                        "steam_id": row["steam_id"],
                        "player_name": row["player_name"],
                        "success": row["success"] or 0,
                        "fails": row["fails"] or 0,
                        "total": row["total"] or 0,
                        "rate": row["rate"] or 0.0,
                    }
                )

            conn.close()
            return rankings

        except Exception as e:
            self.logger.error(
                f"Erro ao obter rankings de lockpicking ({lock_type}): {e}"
            )
            return []

    def format_ranking_embed(
        self, lock_type: str, rankings: List[Dict[str, Any]], is_last: bool = False
    ) -> Dict[str, Any]:
        """
        Formatar embed do Discord para ranking de um tipo de fechadura

        Args:
            lock_type: Tipo de fechadura
            rankings: Lista de rankings
            is_last: Se é o último embed da lista (para adicionar footer)

        Returns:
            Embed formatado para Discord
        """
        lock_info = self.LOCK_TYPES.get(lock_type.lower(), self.LOCK_TYPES["other"])
        display_title = lock_info["display_name"]

        # Construir tabela de ranking
        if not rankings:
            description = (
                f"*No players with at least {self.min_attempts} attempts yet.*"
            )
        else:
            lines = []
            lines.append("```")
            header = f"{'Rank':<4} | {'Player':<18} | {'Success':>7} | {'Fails':>5} | {'Rate':>7}"
            lines.append(header)
            lines.append("-" * 50)

            for r in rankings:
                player_name = str(r.get("player_name") or "Unknown")[:18].strip()
                success = int(r.get("success") or 0)
                fails = int(r.get("fails") or 0)
                rate = f"{float(r.get('rate') or 0.0):.2f}%"
                pos_str = f"#{r.get('rank', 1)}"

                row = f"{pos_str:<4} | {player_name:<18} | {success:>7} | {fails:>5} | {rate:>7}"
                lines.append(row)

            lines.append("```")
            description = "\n".join(lines)

        embed = {
            "title": display_title,
            "description": description,
            "color": lock_info["color"],
        }

        if lock_info.get("image_url"):
            embed["author"] = {
                "name": display_title,
                "icon_url": lock_info["image_url"],
            }
            embed.pop("title", None)

        if is_last:
            embed["footer"] = {
                "text": f"🔄 Min. {self.min_attempts} attempts • Updated every {self.interval_minutes}m • SSM Backend"
            }

        return embed

    def send_rankings(self) -> Dict[str, Any]:
        """
        Gera todos os 6 embeds de lockpicking e envia ou edita via PATCH (Live Dashboard sem spam)

        Returns:
            Resultado do envio
        """
        try:
            if not self.webhook_url or not str(self.webhook_url).strip():
                self.logger.debug("Webhook não configurado para lockpicking rankings")
                return {
                    "success": True,
                    "skipped": True,
                    "message": "Webhook não configurado",
                }

            # Montar a lista de todos os 6 embeds
            embeds = []
            lock_keys = list(self.LOCK_TYPES.keys())
            for i, lock_type in enumerate(lock_keys):
                rankings = self.get_lockpicking_rankings(lock_type)
                is_last = i == len(lock_keys) - 1
                embed = self.format_ranking_embed(lock_type, rankings, is_last=is_last)
                embeds.append(embed)

            if not embeds:
                return {"success": False, "message": "Nenhum embed gerado"}

            payload = {"embeds": embeds}

            # Carregar WebhooksManager se disponível
            mgr = None
            event_state = {}
            target_event = "top10_lockpicking"
            try:
                from core.webhooks.manager import WebhooksManager

                if os.path.exists(self.webhooks_path):
                    mgr = WebhooksManager(self.webhooks_path)
                    v2 = mgr.load_v2()
                    event_state = (
                        ((v2 or {}).get("events") or {})
                        .get(target_event, {})
                        .get("state", {})
                    )
                    if not isinstance(event_state, dict):
                        event_state = {}
            except Exception as e:
                self.logger.debug(f"Não foi possível carregar WebhooksManager: {e}")

            # Calcular assinatura SHA1 para evitar chamadas de rede desnecessárias
            signature = hashlib.sha1(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()

            try:
                last_sig = str(event_state.get("last_signature") or "")
                if last_sig and last_sig == signature:
                    self.logger.debug(
                        "Nenhuma alteração nos rankings de lockpicking (assinatura idêntica)"
                    )
                    return {
                        "success": True,
                        "skipped": True,
                        "message": "Dados inalterados",
                    }
            except Exception:
                pass

            # Extrair id e token do webhook
            parsed = None
            try:
                parts = str(self.webhook_url).split("/api/webhooks/")
                if len(parts) == 2:
                    tail = parts[1].strip("/")
                    segs = tail.split("/")
                    if len(segs) >= 2:
                        parsed = {"id": segs[0], "token": segs[1]}
            except Exception:
                parsed = None

            message_id = ""
            try:
                mid = event_state.get("last_message_id")
                message_id = str(mid).strip() if mid else ""
            except Exception:
                message_id = ""

            # 1. Tentar PATCH se já houver mensagem salva
            if parsed and message_id:
                try:
                    patch_url = f"https://discord.com/api/webhooks/{parsed['id']}/{parsed['token']}/messages/{message_id}"
                    r = requests.patch(
                        patch_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=15,
                    )
                    if r.status_code in (200, 204):
                        if mgr:
                            try:
                                mgr.patch_event_state(
                                    target_event,
                                    {
                                        "last_updated_at": datetime.now().isoformat(),
                                        "last_signature": signature,
                                    },
                                    create_backup=False,
                                )
                            except Exception:
                                pass
                        self.logger.info(
                            f"Top 10 Lockpicking Ranking atualizado via PATCH no Discord (msg {message_id})"
                        )
                        self.last_send_info = {
                            "timestamp": datetime.now().isoformat(),
                            "status": "success",
                            "message_id": message_id,
                        }
                        return {
                            "success": True,
                            "message": "Ranking atualizado via PATCH",
                        }
                    elif r.status_code == 404:
                        self.logger.info(
                            "Mensagem anterior do Lockpicking Ranking não encontrada (404). Criando nova mensagem fixa..."
                        )
                        message_id = ""
                    else:
                        self.logger.warning(
                            f"Erro ao editar mensagem de lockpicking ranking (HTTP {r.status_code}): {r.text}"
                        )
                except Exception as e:
                    self.logger.warning(
                        f"Exceção ao tentar PATCH de lockpicking ranking: {e}"
                    )

            # 2. Criar nova mensagem (POST ?wait=true)
            max_retries = 3
            retry_delay = 1
            for attempt in range(max_retries):
                try:
                    if parsed:
                        post_url = f"https://discord.com/api/webhooks/{parsed['id']}/{parsed['token']}?wait=true"
                    else:
                        post_url = str(self.webhook_url)
                        if "?wait=true" not in post_url:
                            sep = "&" if "?" in post_url else "?"
                            post_url = f"{post_url}{sep}wait=true"

                    response = requests.post(post_url, json=payload, timeout=15)
                    if response.status_code in (200, 204):
                        new_msg_id = ""
                        try:
                            data = response.json()
                            new_msg_id = str(data.get("id") or "").strip()
                        except Exception:
                            pass

                        if mgr and new_msg_id:
                            try:
                                mgr.patch_event_state(
                                    target_event,
                                    {
                                        "last_message_id": new_msg_id,
                                        "last_updated_at": datetime.now().isoformat(),
                                        "last_signature": signature,
                                    },
                                    create_backup=False,
                                )
                            except Exception:
                                pass
                        self.logger.info(
                            f"Nova mensagem fixa de Top 10 Lockpicking criada no Discord (msg {new_msg_id})"
                        )
                        self.last_send_info = {
                            "timestamp": datetime.now().isoformat(),
                            "status": "success",
                            "message_id": new_msg_id,
                        }
                        return {
                            "success": True,
                            "message": "Nova mensagem fixa de ranking criada com sucesso",
                        }
                    elif response.status_code == 429:
                        try:
                            error_data = response.json()
                            retry_after = error_data.get("retry_after", retry_delay)
                            self.logger.warning(
                                f"Rate limit atingido, aguardando {retry_after:.2f}s..."
                            )
                            time.sleep(retry_after)
                            continue
                        except Exception:
                            time.sleep(retry_delay)
                            continue
                    else:
                        self.logger.error(
                            f"Erro ao enviar ranking (HTTP {response.status_code}): {response.text}"
                        )
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        return {
                            "success": False,
                            "message": f"Erro HTTP {response.status_code}",
                        }
                except requests.exceptions.Timeout:
                    self.logger.error("Timeout ao enviar ranking para Discord")
                    return {"success": False, "message": "Timeout"}
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Erro de rede ao enviar ranking: {e}")
                    return {"success": False, "message": str(e)}
                except Exception as e:
                    self.logger.error(f"Erro ao enviar ranking para Discord: {e}")
                    return {"success": False, "message": str(e)}

            return {"success": False, "message": "Falha após tentativas"}
        except Exception as e:
            self.logger.error(
                f"Erro inesperado no envio de lockpicking rankings: {e}"
            )
            return {"success": False, "message": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Obter status do serviço"""
        try:
            return {
                "enabled": self.is_running,
                "webhook_configured": bool(self.webhook_url),
                "min_attempts": self.min_attempts,
                "top_n": self.top_n,
                "schedule_time": self.schedule_time,
                "interval_minutes": self.interval_minutes,
                "last_send": self.last_send_info,
                "next_scheduled": (
                    f"{self.schedule_time} (diariamente)" if self.is_running else None
                ),
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter status: {e}")
            return {"enabled": False, "error": str(e)}

            return {"enabled": False, "error": str(e)}
