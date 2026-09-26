"""
Serviço de Rankings de Combate (Top 10 Live Dashboard)
Gera e atualiza rankings top 10 unificados de Kills (PvP), Longest Shots (Snipers) e Shame Rank (NPC Deaths)
para Discord em mensagem única via PATCH com detecção de alterações via hash SHA1.
"""

import os
import re
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


class KillsRankingService:
    """Serviço para gerar e sincronizar rankings de combate (Top 10 Live Dashboard)"""

    def __init__(
        self,
        ssm_db_path: str,
        webhook_url: str,
        webhooks_path: str = "data/webhooks.json",
        logger: Optional[StructuredLogger] = None,
        top_n: int = 10,
        schedule_time: str = "00:00",
        interval_minutes: int = 15,
    ):
        self.logger = logger or StructuredLogger()
        self.ssm_db_path = ssm_db_path
        self.webhook_url = webhook_url
        self.webhooks_path = webhooks_path
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
            "KillsRankingService inicializado",
            {
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
            # Agendar envio periódico e diário
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
                f"KillsRankingService iniciado - agendado a cada {self.interval_minutes}m e diariamente às {self.schedule_time}"
            )

            return {
                "success": True,
                "message": "Serviço iniciado com sucesso",
                "interval_minutes": self.interval_minutes,
                "next_send": f"{self.schedule_time} (diariamente)",
            }

        except Exception as e:
            self.logger.error(f"Erro ao iniciar KillsRankingService: {e}")
            return {"success": False, "message": f"Erro ao iniciar: {str(e)}"}

    def stop(self) -> Dict[str, Any]:
        """Parar serviço"""
        try:
            self.is_running = False
            self.stop_event.set()

            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)

            self.logger.info("KillsRankingService parado")
            return {"success": True, "message": "Serviço parado com sucesso"}

        except Exception as e:
            self.logger.error(f"Erro ao parar KillsRankingService: {e}")
            return {"success": False, "message": f"Erro ao parar: {str(e)}"}

    def _run_scheduler(self):
        """Executar scheduler em thread separada"""
        while not self.stop_event.is_set():
            self.scheduler.run_pending()
            time.sleep(30)

    def _send_rankings_job(self):
        """Job agendado para sincronizar rankings"""
        try:
            self.logger.info("Iniciando sincronização de rankings de combate...")
            result = self.send_rankings()
            if result.get("success"):
                if result.get("skipped"):
                    self.logger.debug(
                        "Sincronização de rankings de combate ignorada (dados inalterados ou webhook vazio)"
                    )
                else:
                    self.logger.info(
                        "Rankings de combate sincronizados com sucesso no Discord"
                    )
            else:
                self.logger.error(
                    f"Falha ao sincronizar rankings de combate: {result.get('message')}"
                )
        except Exception as e:
            self.logger.error(f"Erro no job de envio de rankings: {e}")

    def get_top_killers(self) -> List[Dict[str, Any]]:
        """
        Obter ranking de top killers

        Returns:
            Lista de jogadores ordenados por total de kills
        """
        try:
            conn = sqlite3.connect(self.ssm_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                SELECT 
                    steam_id,
                    player_name,
                    kills,
                    deaths,
                    kdr
                FROM rankings
                WHERE kills > 0
                ORDER BY kills DESC, kdr DESC, player_name ASC
                LIMIT ?
            """

            cursor.execute(query, (self.top_n,))
            rows = cursor.fetchall()

            rankings = []
            for rank, row in enumerate(rows, start=1):
                rankings.append(
                    {
                        "rank": rank,
                        "steam_id": row["steam_id"],
                        "player_name": row["player_name"],
                        "kills": row["kills"] or 0,
                        "deaths": row["deaths"] or 0,
                        "kdr": row["kdr"] or 0.0,
                    }
                )

            conn.close()
            return rankings

        except Exception as e:
            self.logger.error(f"Erro ao obter top killers: {e}")
            return []

    def get_top_snipers(self) -> List[Dict[str, Any]]:
        """
        Obter ranking de top snipers (maior distância de tiro)

        Returns:
            Lista de jogadores ordenados por maior distância de tiro
        """
        try:
            conn = sqlite3.connect(self.ssm_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                SELECT 
                    steam_id,
                    player_name,
                    longest_shot_distance,
                    longest_shot_weapon
                FROM rankings
                WHERE longest_shot_distance > 0
                ORDER BY longest_shot_distance DESC, player_name ASC
                LIMIT ?
            """

            cursor.execute(query, (self.top_n,))
            rows = cursor.fetchall()

            rankings = []
            for rank, row in enumerate(rows, start=1):
                rankings.append(
                    {
                        "rank": rank,
                        "steam_id": row["steam_id"],
                        "player_name": row["player_name"],
                        "distance": row["longest_shot_distance"] or 0.0,
                        "weapon": row["longest_shot_weapon"] or "Unknown",
                    }
                )

            conn.close()
            return rankings

        except Exception as e:
            self.logger.error(f"Erro ao obter top snipers: {e}")
            return []

    def get_shame_rank(self) -> List[Dict[str, Any]]:
        """
        Obter ranking de mortes por NPC (Shame Rank)

        Returns:
            Lista de jogadores ordenados por total de mortes por NPC
        """
        try:
            conn = sqlite3.connect(self.ssm_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                SELECT 
                    victim_steam_id as steam_id,
                    victim_name as player_name,
                    COUNT(*) as npc_deaths
                FROM kill_events
                WHERE event_type = 'kill' 
                  AND killer_user_id = 'NPC'
                  AND victim_steam_id IS NOT NULL
                GROUP BY victim_steam_id, victim_name
                ORDER BY npc_deaths DESC, victim_name ASC
                LIMIT ?
            """

            cursor.execute(query, (self.top_n,))
            rows = cursor.fetchall()

            rankings = []
            for rank, row in enumerate(rows, start=1):
                rankings.append(
                    {
                        "rank": rank,
                        "steam_id": row["steam_id"],
                        "player_name": row["player_name"],
                        "npc_deaths": row["npc_deaths"] or 0,
                    }
                )

            conn.close()
            return rankings

        except Exception as e:
            self.logger.error(f"Erro ao obter shame rank: {e}")
            return []

    def format_top_killers_embed(
        self, rankings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Formatar embed do Discord para top killers
        """
        if not rankings:
            description = "*No player kills recorded yet.*"
        else:
            lines = []
            lines.append("```")
            header = f"{'Rank':<4} | {'Player':<18} | {'Kills':>5} | {'Deaths':>6} | {'KDR':>6}"
            lines.append(header)
            lines.append("-" * 51)

            for r in rankings:
                player_name = str(r.get("player_name") or "Unknown")[:18].strip()
                kills = int(r.get("kills") or 0)
                deaths = int(r.get("deaths") or 0)
                kdr = f"{float(r.get('kdr') or 0.0):.2f}"
                pos_str = f"#{r.get('rank', 1)}"

                row = f"{pos_str:<4} | {player_name:<18} | {kills:>5} | {deaths:>6} | {kdr:>6}"
                lines.append(row)

            lines.append("```")
            description = "\n".join(lines)

        return {
            "title": "⚔️ TOP 10 KILLERS (PVP)",
            "description": description,
            "color": 0xE74C3C,  # Vermelho Carmesim
        }

    def format_top_snipers_embed(
        self, rankings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Formatar embed do Discord para top snipers
        """
        if not rankings:
            description = "*No long distance shots recorded yet.*"
        else:
            lines = []
            lines.append("```")
            header = f"{'Rank':<4} | {'Player':<18} | {'Weapon':<11} | {'Distance':>8}"
            lines.append(header)
            lines.append("-" * 51)

            for r in rankings:
                player_name = str(r.get("player_name") or "Unknown")[:18].strip()

                weapon_raw = str(r.get("weapon") or "Unknown")
                if weapon_raw.startswith("Weapon_"):
                    weapon = weapon_raw.replace("Weapon_", "", 1)
                else:
                    weapon = weapon_raw

                if "_C" in weapon:
                    weapon = weapon.split("_C")[0]

                weapon = weapon[:11].strip()
                distance = f"{float(r.get('distance') or 0.0):.1f}m"
                pos_str = f"#{r.get('rank', 1)}"

                row = f"{pos_str:<4} | {player_name:<18} | {weapon:<11} | {distance:>8}"
                lines.append(row)

            lines.append("```")
            description = "\n".join(lines)

        return {
            "title": "🎯 TOP 10 LONGEST SHOTS (SNIPERS)",
            "description": description,
            "color": 0x2ECC71,  # Verde
        }

    def format_shame_rank_embed(
        self, rankings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Formatar embed do Discord para shame rank
        """
        if not rankings:
            description = "*No NPC deaths recorded yet.*"
        else:
            lines = []
            lines.append("```")
            header = f"{'Rank':<4} | {'Player':<29} | {'NPC Deaths':>12}"
            lines.append(header)
            lines.append("-" * 51)

            for r in rankings:
                player_name = str(r.get("player_name") or "Unknown")[:29].strip()
                npc_deaths = int(r.get("npc_deaths") or 0)
                pos_str = f"#{r.get('rank', 1)}"

                row = f"{pos_str:<4} | {player_name:<29} | {npc_deaths:>12}"
                lines.append(row)

            lines.append("```")
            description = "\n".join(lines)

        return {
            "title": "💀 TOP 10 SHAME RANK (NPC DEATHS)",
            "description": description,
            "color": 0x7F8C8D,  # Cinza / Dark Slate
            "footer": {
                "text": f"🔄 Updated every {self.interval_minutes}m • SSM Combat Rankings"
            },
        }

    def send_rankings(self) -> Dict[str, Any]:
        """
        Gera os 3 embeds de combate (Killers, Snipers, Shame Rank) e sincroniza via PATCH
        """
        try:
            if not self.webhook_url or not str(self.webhook_url).strip():
                self.logger.debug("Webhook não configurado para kills rankings")
                return {
                    "success": True,
                    "skipped": True,
                    "message": "Webhook não configurado",
                }

            top_killers = self.get_top_killers()
            top_snipers = self.get_top_snipers()
            shame_rank = self.get_shame_rank()

            embed_killers = self.format_top_killers_embed(top_killers)
            embed_snipers = self.format_top_snipers_embed(top_snipers)
            embed_shame = self.format_shame_rank_embed(shame_rank)

            payload = {"embeds": [embed_killers, embed_snipers, embed_shame]}

            # Carregar WebhooksManager se disponível
            mgr = None
            event_state = {}
            target_event = "top10_kills"
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

            # Calcular assinatura SHA1 para evitar chamadas desnecessárias
            signature = hashlib.sha1(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()

            try:
                last_sig = str(event_state.get("last_signature") or "")
                if last_sig and last_sig == signature:
                    self.logger.debug(
                        "Nenhuma alteração nos rankings de combate (assinatura idêntica)"
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
                            f"Top 10 Combat Ranking atualizado via PATCH no Discord (msg {message_id})"
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
                            "Mensagem anterior do Combat Ranking não encontrada (404). Criando nova mensagem fixa..."
                        )
                        message_id = ""
                    else:
                        self.logger.warning(
                            f"Erro ao editar mensagem de combat ranking (HTTP {r.status_code}): {r.text}"
                        )
                except Exception as e:
                    self.logger.warning(
                        f"Exceção ao tentar PATCH de combat ranking: {e}"
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
                            f"Nova mensagem fixa de Top 10 Combat criada no Discord (msg {new_msg_id})"
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
            self.logger.error(f"Erro inesperado no envio de kills rankings: {e}")
            return {"success": False, "message": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Obter status do serviço"""
        try:
            return {
                "enabled": self.is_running,
                "webhook_configured": bool(self.webhook_url),
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

