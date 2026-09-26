import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests
import os
import json

from utils.logger import StructuredLogger
from utils.restart_guard import is_restart_active
from core.database.connector import DatabaseConnector

class AttributeExpirationScheduler(threading.Thread):
    """
    Serviço de background que monitora e reverte upgrades temporários de atributos expirados.
    """
    def __init__(self, ssm_db_path: str, scum_db_path: str, logger: Optional[Any] = None):
        super().__init__(daemon=True, name="AttributeExpirationSchedulerThread")
        self.ssm_db_path = ssm_db_path
        self.scum_db_path = scum_db_path
        self.logger = logger or StructuredLogger()
        self._running = False
        self._stop_event = threading.Event()

    def start(self):
        """Inicia a thread do agendador."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        super().start()
        self.logger.info("AttributeExpirationScheduler iniciado")

    def stop(self):
        """Para a thread do agendador de forma graciosa."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        self.logger.info("AttributeExpirationScheduler parando...")
        self.join(timeout=5.0)

    def run(self):
        """Loop principal do agendador (roda a cada 60 segundos)."""
        # Aguarda 35 segundos no startup para estabilização
        self._stop_event.wait(35.0)
        
        while self._running and not self._stop_event.is_set():
            try:
                self._check_and_expire_attributes()
            except Exception as e:
                self.logger.error(f"Erro no AttributeExpirationScheduler: {e}")
            
            # Aguarda 60 segundos
            self._stop_event.wait(60.0)

    def _load_shop_log_webhook(self) -> str:
        try:
            from utils.config_path_helper import load_config_with_paths
            config, path_helper = load_config_with_paths()
            webhooks_path = path_helper.get_application_path("webhooks", "data/webhooks.json")
            if not os.path.exists(webhooks_path):
                return ""
            
            try:
                from core.webhooks.manager import WebhooksManager
                mgr = WebhooksManager(str(webhooks_path))
                webhooks = mgr.load()
                return str((webhooks or {}).get("shop-log") or "").strip()
            except Exception:
                with open(webhooks_path, "r", encoding="utf-8") as f:
                    webhooks = json.load(f)
                return str((webhooks or {}).get("shop-log") or "").strip()
        except Exception as e:
            self.logger.error(f"Erro ao carregar webhook do shop-log no scheduler: {e}")
            return ""

    def _get_player_attributes(self, steam_id: str) -> Optional[Dict[str, float]]:
        # 1. Tentar ler do player_attributes_cache no SSM.db
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT strength, constitution, dexterity, intelligence FROM player_attributes_cache WHERE steam_id = ?",
                    (steam_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "strength": float(row[0]) if row[0] is not None else 3.0,
                        "constitution": float(row[1]) if row[1] is not None else 3.0,
                        "dexterity": float(row[2]) if row[2] is not None else 3.0,
                        "intelligence": float(row[3]) if row[3] is not None else 3.0,
                    }
        except Exception as e:
            self.logger.error(f"Erro ao obter atributos do cache para rollback: {e}")
        
        # 2. Fallback: ler do SCUM.db do jogo
        try:
            from utils.scum_db_helper import scum_db_readonly_connection
            from utils.scum_attributes_editor import resolve_prisoner_identifier, get_prisoner_attributes
            with scum_db_readonly_connection(self.scum_db_path) as scum_conn:
                scum_cursor = scum_conn.cursor()
                ident_info = resolve_prisoner_identifier(scum_cursor, steam_id)
                if ident_info:
                    prisoner_id = ident_info["prisoner_id"]
                    attrs = get_prisoner_attributes(scum_cursor, prisoner_id)
                    if attrs:
                        return attrs
        except Exception as e:
            self.logger.error(f"Erro ao obter atributos do SCUM.db para rollback: {e}")
            
        return None

    def _check_and_expire_attributes(self):
        if is_restart_active():
            return

        # 1. Verificar se a expiração global está habilitada
        expiration_enabled = False
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value FROM app_config WHERE key = ?",
                    ("attributes.expiration.enabled",)
                )
                row = cursor.fetchone()
                if row:
                    expiration_enabled = (row[0] == "1")
        except Exception as e:
            self.logger.error(f"Erro ao ler configuracao de expiracao de atributos: {e}")
            return

        if not expiration_enabled:
            return

        # 2. Marcar upgrades 'active' cuja data expirou como 'pending_rollback'
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE player_attribute_upgrades 
                    SET status = 'pending_rollback' 
                    WHERE status = 'active' AND expires_at <= ?
                    """,
                    (now_str,)
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Erro ao atualizar status para pending_rollback: {e}")

        # 3. Buscar todos os upgrades marcados como 'pending_rollback'
        pending_upgrades = []
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, steam_id, attribute_name, original_value, target_value 
                    FROM player_attribute_upgrades 
                    WHERE status = 'pending_rollback'
                    """
                )
                pending_upgrades = [
                    {
                        "id": row[0],
                        "steam_id": row[1],
                        "attribute_name": row[2],
                        "original_value": float(row[3]),
                        "target_value": float(row[4])
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            self.logger.error(f"Erro ao buscar upgrades pendentes de rollback: {e}")
            return

        if not pending_upgrades:
            return

        # 4. Processar cada upgrade pendente
        for upg in pending_upgrades:
            steam_id = upg["steam_id"]
            attribute_name = upg["attribute_name"]
            original_value = upg["original_value"]
            target_value = upg["target_value"]
            upg_id = upg["id"]

            # Verificar se o jogador está online
            is_online = False
            try:
                with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT 1 FROM players_online WHERE steam_id = ? AND status = 'online'",
                        (steam_id,)
                    )
                    is_online = (cursor.fetchone() is not None)
            except Exception as e:
                self.logger.error(f"Erro ao verificar se jogador {steam_id} esta online para rollback: {e}")
                continue

            if not is_online:
                continue

            # Obter nome do jogador e discord_user_id do SSM.db
            player_name = "Desconhecido"
            discord_user_id = None
            try:
                with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT player_name, discord_user_id FROM players WHERE steam_id = ?",
                        (steam_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        player_name = row[0] or "Desconhecido"
                        discord_user_id = row[1]
            except Exception as e:
                self.logger.error(f"Erro ao obter informacoes do jogador {steam_id} para rollback: {e}")

            # Obter o conjunto completo de atributos do jogador
            attrs = self._get_player_attributes(steam_id)
            if not attrs:
                self.logger.error(f"Nao foi possivel obter atributos atuais do jogador {steam_id} para reverter.")
                self._send_failure_log(
                    steam_id=steam_id,
                    player_name=player_name,
                    discord_user_id=discord_user_id,
                    attribute_name=attribute_name,
                    error_msg="Não foi possível obter os atributos atuais do jogador para rollback no SCUM.db."
                )
                continue

            # Alterar o atributo alvo para o valor original (base)
            attrs[attribute_name] = original_value

            # Conectar via RCON e aplicar
            from utils.rcon_client import get_rcon_client_from_config
            rcon_client = get_rcon_client_from_config()
            if not rcon_client:
                self.logger.error(f"RCON indisponivel para aplicar rollback do jogador {steam_id}")
                self._send_failure_log(
                    steam_id=steam_id,
                    player_name=player_name,
                    discord_user_id=discord_user_id,
                    attribute_name=attribute_name,
                    error_msg="RCON indisponível no momento."
                )
                continue

            try:
                with rcon_client as rcon:
                    from utils.scum_attributes_editor import apply_attribute_and_skills_via_rcon
                    ok, rcon_msg = apply_attribute_and_skills_via_rcon(
                        rcon,
                        steam_id,
                        attribute_name,
                        original_value,
                        attrs
                    )

                    if ok:
                        # 5. Persistir expiração no banco e cache
                        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                            cursor = conn.cursor()
                            # Atualizar status do upgrade para 'expired'
                            cursor.execute(
                                "UPDATE player_attribute_upgrades SET status = 'expired' WHERE id = ?",
                                (upg_id,)
                            )
                            # Atualizar cache de atributos
                            cursor.execute(
                                """
                                UPDATE player_attributes_cache 
                                SET strength = ?, constitution = ?, dexterity = ?, intelligence = ?, updated_at = CURRENT_TIMESTAMP 
                                WHERE steam_id = ?
                                """,
                                (
                                    attrs.get("strength"),
                                    attrs.get("constitution"),
                                    attrs.get("dexterity"),
                                    attrs.get("intelligence"),
                                    steam_id
                                )
                            )
                            conn.commit()

                        # Notificar jogador no jogo
                        rcon.send_command(f'SendChat 7 "Seu upgrade temporario de {attribute_name.capitalize()} expirou e foi revertido para Lvl {original_value:.1f}!" {steam_id}')
                        self.logger.info(f"Rollback executado com sucesso para {player_name} ({steam_id}) - {attribute_name} revertido para {original_value}")

                        # Enviar log de reversão bem-sucedida para o Discord
                        self._send_success_log(
                            steam_id=steam_id,
                            player_name=player_name,
                            discord_user_id=discord_user_id,
                            attribute_name=attribute_name,
                            original_value=original_value,
                            target_value=target_value
                        )
                    else:
                        self.logger.error(f"Falha ao aplicar rollback via RCON para {steam_id}: {rcon_msg}")
                        self._send_failure_log(
                            steam_id=steam_id,
                            player_name=player_name,
                            discord_user_id=discord_user_id,
                            attribute_name=attribute_name,
                            error_msg=rcon_msg
                        )
            except Exception as rcon_err:
                self.logger.error(f"Erro de RCON durante o rollback para {steam_id}: {rcon_err}")
                self._send_failure_log(
                    steam_id=steam_id,
                    player_name=player_name,
                    discord_user_id=discord_user_id,
                    attribute_name=attribute_name,
                    error_msg=str(rcon_err)
                )

    def _send_success_log(self, steam_id: str, player_name: str, discord_user_id: Optional[str], attribute_name: str, original_value: float, target_value: float):
        webhook = self._load_shop_log_webhook()
        if not webhook:
            return
        
        discord_val = f"<@{discord_user_id}>" if discord_user_id else "Não registrado / Não vinculado"
        embed = {
            "title": "⚠️ SSM | UPGRADE TEMPORÁRIO EXPIRADO (REVERTIDO)",
            "color": 0xE67E22,  # Laranja
            "fields": [
                {"name": "Jogador", "value": f"{player_name} (`{steam_id}`)", "inline": True},
                {"name": "Usuário Discord", "value": discord_val, "inline": True},
                {"name": "Atributo", "value": attribute_name.upper(), "inline": True},
                {"name": "Ajuste RCON", "value": f"Revertido de Lvl {target_value:.1f} ➔ Lvl {original_value:.1f} (Original)", "inline": False},
                {"name": "Status", "value": "Restaurado com sucesso (Jogador Online)", "inline": False}
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        try:
            requests.post(webhook, json={"embeds": [embed]}, timeout=30)
        except Exception as e:
            self.logger.error(f"Erro ao enviar success embed no discord: {e}")

    def _send_failure_log(self, steam_id: str, player_name: str, discord_user_id: Optional[str], attribute_name: str, error_msg: str):
        webhook = self._load_shop_log_webhook()
        if not webhook:
            return
        
        discord_val = f"<@{discord_user_id}>" if discord_user_id else "Não registrado / Não vinculado"
        embed = {
            "title": "🚨 SSM | FALHA AO REVERTER ATRIBUTO EXPIRADO",
            "color": 0xE74C3C,  # Vermelho
            "fields": [
                {"name": "Jogador", "value": f"{player_name} (`{steam_id}`)", "inline": True},
                {"name": "Usuário Discord", "value": discord_val, "inline": True},
                {"name": "Atributo", "value": attribute_name.upper(), "inline": True},
                {"name": "Erro", "value": f"```text\n{error_msg}\n```", "inline": False},
                {"name": "Status", "value": "O SSM agendou nova tentativa automática para daqui a 60 segundos.", "inline": False}
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        try:
            requests.post(webhook, json={"embeds": [embed]}, timeout=30)
        except Exception as e:
            self.logger.error(f"Erro ao enviar failure embed no discord: {e}")
