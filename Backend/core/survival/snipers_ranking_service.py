"""
Serviço de Rankings de Snipers
Gera e envia ranking top 20 de snipers (maior distância de tiro) para Discord
"""

import sqlite3
import threading
import time
import os
import mimetypes
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests

import schedule

from utils.logger import StructuredLogger


class SnipersRankingService:
    """Serviço para gerar e enviar rankings de snipers"""

    def __init__(
        self,
        ssm_db_path: str,
        webhook_url: str,
        logger: Optional[StructuredLogger] = None,
        top_n: int = 20,
        schedule_time: str = "00:00",
        gif_path: Optional[str] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.ssm_db_path = ssm_db_path
        self.webhook_url = webhook_url
        self.top_n = top_n
        self.schedule_time = schedule_time
        self.gif_path = gif_path

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
            "SnipersRankingService inicializado",
            {
                "top_n": self.top_n,
                "schedule_time": self.schedule_time,
                "webhook_configured": bool(self.webhook_url),
            },
        )

    def start(self) -> Dict[str, Any]:
        """Iniciar serviço de envio automático"""
        if self.is_running:
            return {"success": False, "message": "Serviço já está em execução"}

        try:
            # Agendar envio diário no horário configurado
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
                f"SnipersRankingService iniciado - envio agendado para {self.schedule_time} diariamente"
            )

            return {
                "success": True,
                "message": "Serviço iniciado com sucesso",
                "next_send": f"{self.schedule_time} (diariamente)",
            }

        except Exception as e:
            self.logger.error(f"Erro ao iniciar SnipersRankingService: {e}")
            return {"success": False, "message": f"Erro ao iniciar: {str(e)}"}

    def stop(self) -> Dict[str, Any]:
        """Parar serviço"""
        try:
            self.is_running = False
            self.stop_event.set()

            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)

            self.logger.info("SnipersRankingService parado")
            return {"success": True, "message": "Serviço parado com sucesso"}

        except Exception as e:
            self.logger.error(f"Erro ao parar SnipersRankingService: {e}")
            return {"success": False, "message": f"Erro ao parar: {str(e)}"}

    def _run_scheduler(self):
        """Executar scheduler em thread separada"""
        while not self.stop_event.is_set():
            self.scheduler.run_pending()
            time.sleep(60)  # Verificar a cada minuto

    def _send_rankings_job(self):
        """Job agendado para enviar rankings"""
        try:
            self.logger.info("Iniciando envio automático de rankings de snipers")
            result = self.send_rankings()
            if result.get("success"):
                if result.get("skipped"):
                    self.logger.debug(
                        "Envio de rankings de snipers ignorado (webhook não configurado)"
                    )
                else:
                    self.logger.info(
                        "Rankings de snipers enviados automaticamente com sucesso"
                    )
            else:
                self.logger.error(
                    f"Falha ao enviar rankings automaticamente: {result.get('message')}"
                )
        except Exception as e:
            self.logger.error(f"Erro no job de envio de rankings: {e}")

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

            # Buscar rankings ordenados por longest_shot_distance (descendente)
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

    def format_top_snipers_embed(
        self, rankings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Formatar embed do Discord para top snipers

        Args:
            rankings: Lista de rankings

        Returns:
            Embed formatado para Discord
        """
        # Construir tabela de ranking
        if not rankings:
            description = "*Nenhum jogador com tiros de longa distância encontrado*"
        else:
            lines = []
            lines.append("```")
            header = f"{'🏆':<2}|{'Player':<13}|{'Weapon':<11}|{'Distance':>8}"
            lines.append(header)
            lines.append("-" * 38)

            # Linhas de dados
            for r in rankings:
                player_name = r["player_name"][:13].strip()

                # Limpar nome da arma: remover "Weapon_" e sufixos como "_C"
                weapon_raw = r["weapon"] or "Unknown"
                if weapon_raw.startswith("Weapon_"):
                    weapon = weapon_raw.replace("Weapon_", "", 1)
                else:
                    weapon = weapon_raw

                # Remover sufixos comuns como "_C" ou "_C_21452063"
                if "_C" in weapon:
                    weapon = weapon.split("_C")[0]

                weapon = weapon[:11].strip()
                distance = f"{r['distance']:.2f}m"

                row = f"{r['rank']:<3}|{player_name:<13}|{weapon:<11}|{distance:>8}"
                lines.append(row)

            lines.append("```")
            description = "\n".join(lines)

        # Criar embed
        embed = {
            "title": "🎯 TOP SNIPERS 🎯",
            "description": description,
            "color": 0x2ECC71,  # Verde
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "🌐 Global Rankings",
                    "value": "[View all rankings](https://scumsm.com/rankings)",
                    "inline": False,
                }
            ],
            "footer": {"text": f"Top {self.top_n} | Atualizado"},
        }

        # Adicionar GIF como imagem no embed (aparece na parte inferior, como rodapé visual)
        if self.gif_path and os.path.exists(self.gif_path):
            embed["image"] = {"url": f"attachment://{os.path.basename(self.gif_path)}"}

        return embed

    def send_rankings(self) -> Dict[str, Any]:
        """
        Enviar ranking de snipers para Discord

        Returns:
            Resultado do envio
        """
        try:
            if not self.webhook_url or not str(self.webhook_url).strip():
                self.logger.debug("Webhook não configurado para snipers rankings")
                return {"success": True, "skipped": True, "message": "Webhook não configurado"}

            self.logger.info(
                f"Iniciando envio de ranking de snipers para webhook: {self.webhook_url[:50]}..."
            )

            rankings = self.get_top_snipers()
            self.logger.debug(f"Top Snipers: {len(rankings)} jogadores encontrados")

            embed = self.format_top_snipers_embed(rankings)

            # Preparar payload e anexos
            payload = {"embeds": [embed]}

            # Se houver GIF, enviar como anexo
            files = None
            if self.gif_path and os.path.exists(self.gif_path):
                filename = os.path.basename(self.gif_path)
                mime_type = mimetypes.guess_type(filename)[0] or "image/gif"
                files = {"file": (filename, open(self.gif_path, "rb"), mime_type)}
                # Mudar para multipart/form-data quando houver anexo
                self.logger.debug(f"Adicionando GIF como anexo: {filename}")

            self.logger.debug("Enviando Top Snipers para Discord...")

            if files:
                # Enviar com anexo (multipart/form-data)
                import json as json_lib

                response = requests.post(
                    self.webhook_url,
                    data={"payload_json": json_lib.dumps(payload)},
                    files=files,
                    timeout=15,
                )
                files["file"][1].close()  # Fechar arquivo
            else:
                # Enviar sem anexo (JSON)
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10,
                    headers={"Content-Type": "application/json"},
                )

            if response.status_code in (200, 204):
                self.last_send_info = {
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "details": {"sent": 1, "failed": 0, "total_rankings": 1},
                }
                self.logger.info("✅ Top Snipers enviado com sucesso")
                return {
                    "success": True,
                    "message": "Ranking enviado com sucesso",
                    "sent": 1,
                }
            else:
                error_msg = f"{response.status_code} - {response.text[:100]}"
                self.last_send_info = {
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "details": {
                        "sent": 0,
                        "failed": 1,
                        "total_rankings": 1,
                        "errors": [error_msg],
                    },
                }
                self.logger.error(
                    f"❌ Erro ao enviar Top Snipers: {response.status_code} - {response.text[:200]}"
                )
                return {
                    "success": False,
                    "message": f"Erro ao enviar: {error_msg}",
                    "failed": 1,
                }

        except Exception as e:
            self.logger.error(f"Erro ao enviar ranking de snipers: {e}")
            return {"success": False, "message": f"Erro ao enviar ranking: {str(e)}"}

    def get_status(self) -> Dict[str, Any]:
        """Obter status do serviço"""
        try:
            return {
                "enabled": self.is_running,
                "webhook_configured": bool(self.webhook_url),
                "top_n": self.top_n,
                "last_send": self.last_send_info,
                "next_scheduled": (
                    f"{self.schedule_time} (diariamente)" if self.is_running else None
                ),
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter status: {e}")
            return {"enabled": False, "error": str(e)}
