import time
import threading
import os
import json
import uuid
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from utils.logger import StructuredLogger
from core.database.connector import DatabaseConnector
from core.shop.wallet_service import WalletService
from core.discord_bot_service import DiscordBotService

class PersonalWebhookScheduler(threading.Thread):
    """
    Serviço de background que gerencia a renovação automática e alertas de expiração
    dos webhooks pessoais de raid (/rd).
    """
    def __init__(self, ssm_db_path: str, logger: Optional[Any] = None):
        super().__init__(daemon=True, name="PersonalWebhookSchedulerThread")
        self.ssm_db_path = ssm_db_path
        self.logger = logger or StructuredLogger()
        self._running = False
        self._stop_event = threading.Event()
        self.data_dir = os.path.dirname(ssm_db_path)

    def start(self):
        """Inicia a thread do agendador."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        super().start()
        self.logger.info("PersonalWebhookScheduler iniciado")

    def stop(self):
        """Para a thread do agendador de forma graciosa."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        self.logger.info("PersonalWebhookScheduler parando...")
        self.join(timeout=5.0)

    def run(self):
        """Loop principal do agendador (roda a cada 1 hora)."""
        # Aguarda 45 segundos no startup para estabilização
        self._stop_event.wait(45.0)
        
        while self._running and not self._stop_event.is_set():
            try:
                self._process_webhooks()
            except Exception as e:
                self.logger.error(f"Erro no PersonalWebhookScheduler: {e}")
            
            # Aguarda 1 hora (3600 segundos)
            self._stop_event.wait(3600.0)

    def _load_config(self) -> Dict[str, Any]:
        config_path = os.path.join(self.data_dir, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Erro ao ler config.json no PersonalWebhookScheduler: {e}")
        return {}

    def _process_webhooks(self):
        config = self._load_config()
        pw_cfg = config.get("personal_webhooks", {})
        enabled = pw_cfg.get("enabled", True)
        
        if not enabled:
            return

        price_points = pw_cfg.get("price_points", 500)
        duration_days = pw_cfg.get("duration_days", 30)

        # Se for vitalício / gratuito por padrão (duração <= 0), não há expiração/renovação para gerenciar
        if duration_days <= 0:
            return

        # Obter mensagens personalizadas
        default_msgs = {
            "auto_renew_success": "🔄 [SSM] Sua assinatura do webhook de raid foi renovada automaticamente por mais {days} dias! Validade: {expires_at}. Descontado {price} pontos.",
            "auto_renew_failed": "⚠️ [SSM] Sua assinatura do webhook de raid expirou e nao pôde ser renovada automaticamente por falta de saldo (Preço: {price} pontos | Seu saldo: {balance}). Adicione pontos para reativar.",
            "expiry_warning_3_days": "📅 [SSM] Lembrete: Sua assinatura do webhook de raid expira em 3 dias ({expires_at}). Caso tenha saldo suficiente, ela será renovada automaticamente.",
            "expiry_warning_1_day": "🚨 [SSM] Atenção: Sua assinatura do webhook de raid expira amanhã ({expires_at}). Verifique se possui saldo suficiente para a renovação automática."
        }
        
        msgs = pw_cfg.get("messages", {})
        for k, v in default_msgs.items():
            if k not in msgs:
                msgs[k] = v

        # Carregar registros ativos
        active_webhooks = []
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS player_webhooks (
                        steam_id TEXT PRIMARY KEY,
                        webhook_url TEXT NOT NULL,
                        expires_at DATETIME,
                        warned_3d INTEGER DEFAULT 0,
                        warned_1d INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cursor.execute("PRAGMA table_info('player_webhooks')")
                existing_cols = {str(r[1]) for r in (cursor.fetchall() or [])}
                if "expires_at" not in existing_cols:
                    cursor.execute("ALTER TABLE player_webhooks ADD COLUMN expires_at DATETIME")
                if "warned_3d" not in existing_cols:
                    cursor.execute("ALTER TABLE player_webhooks ADD COLUMN warned_3d INTEGER DEFAULT 0")
                if "warned_1d" not in existing_cols:
                    cursor.execute("ALTER TABLE player_webhooks ADD COLUMN warned_1d INTEGER DEFAULT 0")
                conn.commit()

                cursor.execute(
                    """
                    SELECT w.steam_id, w.webhook_url, w.expires_at, w.warned_3d, w.warned_1d, p.discord_user_id
                    FROM player_webhooks w
                    LEFT JOIN players p ON w.steam_id = p.steam_id
                    WHERE w.webhook_url IS NOT NULL AND w.webhook_url != '' AND w.webhook_url != 'off'
                    """
                )

                active_webhooks = [
                    {
                        "steam_id": row[0],
                        "webhook_url": row[1],
                        "expires_at": row[2],
                        "warned_3d": int(row[3] or 0),
                        "warned_1d": int(row[4] or 0),
                        "discord_user_id": row[5]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            self.logger.error(f"Erro ao buscar webhooks ativos no scheduler: {e}")
            return

        now = datetime.utcnow()

        for wh in active_webhooks:
            steam_id = wh["steam_id"]
            url = wh["webhook_url"]
            expires_str = wh["expires_at"]
            warned_3d = wh["warned_3d"]
            warned_1d = wh["warned_1d"]
            discord_user_id = wh["discord_user_id"]

            if not expires_str:
                continue

            try:
                clean_str = expires_str.split(".")[0].replace("Z", "").replace("T", " ")
                dt_expires = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                self.logger.error(f"Erro ao parsear data de expiracao para {steam_id}: {e}")
                continue

            diff = dt_expires - now

            # 1. Caso expirado -> Tenta auto-renovar
            if diff <= timedelta(seconds=0):
                wallet = WalletService(self.ssm_db_path, logger=self.logger)
                balance = wallet.get_balance(steam_id)

                if balance >= price_points:
                    # Renova
                    try:
                        wallet.apply_delta(
                            steam_id=steam_id,
                            delta=-price_points,
                            reason="personal_webhook_auto_renew",
                            ref_type="webhook",
                            ref_id=str(uuid.uuid4()),
                            allow_negative=False
                        )

                        new_expires_dt = max(dt_expires, now) + timedelta(days=duration_days)
                        new_expires_str = new_expires_dt.strftime("%Y-%m-%d %H:%M:%S")

                        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                            conn.execute(
                                """
                                UPDATE player_webhooks
                                SET expires_at = ?, warned_3d = 0, warned_1d = 0, updated_at = CURRENT_TIMESTAMP
                                WHERE steam_id = ?
                                """,
                                (new_expires_str, steam_id)
                            )
                            conn.commit()

                        # Notificar sucesso
                        dt_display = new_expires_dt.strftime("%d/%m/%Y %H:%M")
                        success_msg = msgs["auto_renew_success"].format(days=duration_days, expires_at=dt_display, price=price_points)
                        
                        # Postar no Discord Webhook
                        self._send_discord_message(url, success_msg)

                        # Postar no DM do Discord se vinculado
                        if discord_user_id:
                            self._send_discord_dm(discord_user_id, success_msg)

                        self.logger.info(f"Assinatura do webhook de {steam_id} renovada automaticamente por mais {duration_days} dias.")

                    except Exception as e:
                        self.logger.error(f"Erro ao processar cobranca de renovacao automatica para {steam_id}: {e}")
                else:
                    # Falha por falta de saldo
                    fail_msg = msgs["auto_renew_failed"].format(price=price_points, balance=balance)

                    # Postar no Discord Webhook antes de limpar a URL do banco
                    self._send_discord_message(url, fail_msg)

                    # Postar no DM do Discord se vinculado
                    if discord_user_id:
                        self._send_discord_dm(discord_user_id, fail_msg)

                    # Desativa o webhook limpando o campo webhook_url
                    try:
                        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                            conn.execute(
                                """
                                UPDATE player_webhooks
                                SET webhook_url = '', updated_at = CURRENT_TIMESTAMP
                                WHERE steam_id = ?
                                """,
                                (steam_id,)
                            )
                            conn.commit()
                        self.logger.info(f"Webhook de {steam_id} desativado por falta de saldo durante a renovacao automatica.")
                    except Exception as e:
                        self.logger.error(f"Erro ao desativar webhook de {steam_id} por falta de saldo: {e}")

            # 2. Caso perto de expirar -> Envia avisos prévios
            else:
                dt_display = dt_expires.strftime("%d/%m/%Y %H:%M")
                
                # Aviso de 1 dia
                if diff <= timedelta(days=1):
                    if not warned_1d:
                        warn_msg = msgs["expiry_warning_1_day"].format(expires_at=dt_display)
                        self._send_discord_message(url, warn_msg)
                        if discord_user_id:
                            self._send_discord_dm(discord_user_id, warn_msg)

                        try:
                            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                                conn.execute(
                                    "UPDATE player_webhooks SET warned_1d = 1 WHERE steam_id = ?",
                                    (steam_id,)
                                )
                                conn.commit()
                        except Exception as e:
                            self.logger.error(f"Erro ao atualizar warned_1d para {steam_id}: {e}")

                # Aviso de 3 dias
                elif diff <= timedelta(days=3):
                    if not warned_3d:
                        warn_msg = msgs["expiry_warning_3_days"].format(expires_at=dt_display)
                        self._send_discord_message(url, warn_msg)
                        if discord_user_id:
                            self._send_discord_dm(discord_user_id, warn_msg)

                        try:
                            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                                conn.execute(
                                    "UPDATE player_webhooks SET warned_3d = 1 WHERE steam_id = ?",
                                    (steam_id,)
                                )
                                conn.commit()
                        except Exception as e:
                            self.logger.error(f"Erro ao atualizar warned_3d para {steam_id}: {e}")

    def _send_discord_message(self, url: str, content: str):
        try:
            requests.post(url, json={"content": content}, timeout=10)
        except Exception as e:
            self.logger.warn(f"Erro ao postar mensagem de aviso no webhook: {e}")

    def _send_discord_dm(self, discord_user_id: str, content: str):
        try:
            bot_service = DiscordBotService._instance
            if bot_service:
                bot_service.send_dm(int(discord_user_id), content)
        except Exception as e:
            self.logger.warn(f"Erro ao enviar DM para {discord_user_id}: {e}")
