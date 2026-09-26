#!/usr/bin/env python3
"""
Chat Command Monitor - Sistema de monitoramento de comandos de chat
Detecta comandos específicos no chat do SCUM e envia notificações para Discord
"""

import os
import re
import json
import time
import threading
import mimetypes
import requests
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from core.database.connector import DatabaseConnector
import hashlib

from utils.logger import StructuredLogger
from .temp_file_manager import TempFileManager
from core.shop.shop_service import ShopService, OrderCreateItem
from core.shop.shop_buy_job_worker import ShopBuyJobWorker, compute_idempotency_key
from core.shop.wallet_service import WalletService

class ChatCommandMonitor:
    """Monitor de comandos de chat do SCUM"""
    
    def __init__(
        self,
        logger: StructuredLogger = None,
        scum_db_path: str = None,
        discord_bot_service: Optional[Any] = None,
        ssm_db_path: Optional[str] = None,
    ):
        """Inicializar monitor de comandos de chat"""
        self.logger = logger or StructuredLogger()
        self.discord_bot_service = discord_bot_service
        
        import sys
        if getattr(sys, "frozen", False):
            self.data_dir = Path(sys.executable).parent / "data"
        else:
            self.data_dir = Path("data")

        # Configurações
        self.log_directory = "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs"
        self.temp_manager = TempFileManager(str(self.data_dir / "temp"))
        
        # Caminho do banco SCUM.db
        self.scum_db_path = scum_db_path or "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"

        # Se scum_db_path for válido, derivar o diretório de Logs a partir dele
        # (evita monitorar o servidor errado quando existem múltiplas instalações).
        try:
            base_dir = os.path.dirname(str(self.scum_db_path))
            candidate = os.path.join(base_dir, "Logs")
            if base_dir and os.path.exists(candidate):
                self.log_directory = candidate
        except Exception:
            pass
        
        # Webhook de comandos
        self.commands_webhook = self._load_commands_webhook()

        # Webhook para respostas do shop (/buy, /mail, /tmail)
        self.shop_log_webhook = self._load_shop_log_webhook()

        self.ssm_db_path = ssm_db_path or str(self.data_dir / "SSM.db")

        self.vehicle_images_path = str(self.data_dir / "imagens/vehicle")

        # Enfileirador de jobs de compra (/buy). O processamento acontece no worker global.
        self.buy_job_enqueuer = ShopBuyJobWorker(
            self.ssm_db_path, logger=self.logger, per_player_limit=5
        )
        
        # Estado do monitor
        self.is_running = False
        self.processed_files = set()
        self.last_check_time = None
        self.processed_commands_file = str(self.data_dir / "processed_commands.json")
        self.processed_commands = self._load_processed_commands()
        self.chat_state_file = str(self.data_dir / "chat_state.json")
        self.last_processed_chat_ts = self._load_last_processed_chat_ts()
        self.time_precision_config = self._load_time_precision_config()

        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._current_chat_file: Optional[str] = None
        self._current_chat_pos: int = 0
        self._pending_chat_bytes: bytes = b""
        self._pending_chat_text: str = ""
        
        # Padrões de comandos
        self.command_patterns = {
            'tm': r'/tm\b',  # Comando /tm
            'sd': r'/(?:sd|saldo|money|balance)\b',  # Comando /sd e aliases
            'rd': r'/rd\b',  # Comando /rd <url> ou /rd off
            'buy': r'/buy\b',  # Comando /buy
            'kit': r'/kit\b',  # Comando /kit
            # 'mail': r'/mail\b',  # Comando /mail (Desativado)
            # 'tmail': r'/tmail\b',  # Comando /tmail (Desativado)
            'atr': r'/atr\b',  # Comando /atr
            'attr_upgrade': r'/(?:f[1-8]|[cdi][1-5])\b', # Comando de Atributos/Skills
            # 'vbuy': r'/vbuy\b',  # Comando /vbuy (Desativado - entrega de veículos agora via RCON pela loja)
            'register': r'!register\b',  # Comando !register <CODE>
            'evento': r'/evento\b',  # Comando /evento <CÓDIGO>
        }

        # Inicializar default upgrade prices no config.json se não existirem (iniciam com 0 = desativado por padrão)
        try:
            config_path = str(self.data_dir / "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if "attribute_upgrade_prices" not in cfg:
                    cfg["attribute_upgrade_prices"] = {
                        "strength": {
                            "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0
                        },
                        "constitution": {
                            "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
                        },
                        "dexterity": {
                            "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
                        },
                        "intelligence": {
                            "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
                        }
                    }
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erro ao inicializar default upgrade prices no config.json: {e}")
        
        self.logger.info("ChatCommandMonitor inicializado")
        try:
            self.logger.info(
                "ChatCommandMonitor discord_bot_service injected",
                {"available": bool(self.discord_bot_service is not None)},
            )
        except Exception:
            pass

    def start_monitoring(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        try:
            self.logger.info(
                "ChatCommandMonitor start_monitoring",
                {"log_directory": self.log_directory},
            )
        except Exception:
            pass

    def stop_monitoring(self) -> None:
        try:
            self.is_running = False
            self._stop_event.set()
        except Exception:
            pass

    def _monitor_loop(self) -> None:
        try:
            poll_interval = 0.5
            while not self._stop_event.is_set():
                try:
                    chat_file = self._pick_latest_chat_log()
                    if chat_file:
                        if self._current_chat_file != chat_file:
                            self._current_chat_file = chat_file
                            try:
                                self.logger.info(
                                    "ChatCommandMonitor seguindo chat log",
                                    {"file": str(chat_file)},
                                )
                            except Exception:
                                pass
                            try:
                                self._current_chat_pos = int(os.path.getsize(chat_file) or 0)
                            except Exception:
                                self._current_chat_pos = 0
                            self._pending_chat_bytes = b""
                            self._pending_chat_text = ""

                        self._read_new_chat_bytes_and_process(chat_file)

                    time.sleep(poll_interval)
                except Exception as e:
                    try:
                        self.logger.error(f"Erro no loop do ChatCommandMonitor: {e}")
                    except Exception:
                        pass
                    time.sleep(1.0)
        except Exception:
            return

    def _pick_latest_chat_log(self) -> Optional[str]:
        try:
            if not self.log_directory or not os.path.exists(self.log_directory):
                try:
                    self.logger.warn(
                        "ChatCommandMonitor log_directory inexistente",
                        {"log_directory": str(self.log_directory)},
                    )
                except Exception:
                    pass
                return None

            best_path: Optional[str] = None
            best_mtime = -1.0
            for name in os.listdir(self.log_directory):
                if not str(name).lower().startswith("chat_"):
                    continue
                if not str(name).lower().endswith(".log"):
                    continue
                p = os.path.join(self.log_directory, name)
                try:
                    st = os.stat(p)
                    if st.st_mtime > best_mtime:
                        best_mtime = st.st_mtime
                        best_path = p
                except Exception:
                    continue
            if not best_path:
                try:
                    self.logger.warn(
                        "ChatCommandMonitor nenhum chat_*.log encontrado",
                        {"log_directory": str(self.log_directory)},
                    )
                except Exception:
                    pass
            return best_path
        except Exception:
            return None

    def _read_new_chat_bytes_and_process(self, file_path: str) -> None:
        temp_path: Optional[str] = None
        source_path = file_path

        try:
            if not os.path.exists(file_path):
                return

            # Verificar se há bytes novos ANTES de criar cópia temporária.
            # Isso evita gerar milhares de arquivos em data/temp quando o chat não mudou.
            original_size = 0
            try:
                original_size = int(os.path.getsize(file_path) or 0)
            except Exception:
                original_size = 0

            if self._current_chat_pos > original_size:
                self._current_chat_pos = 0

            if self._current_chat_pos == original_size:
                return

            # Criar cópia temporária para evitar lock do SCUM.
            try:
                temp_path = self.temp_manager.create_temp_copy(file_path)
                if temp_path:
                    source_path = temp_path
            except Exception:
                temp_path = None
                source_path = file_path

            try:
                with open(source_path, "rb") as f:
                    f.seek(int(self._current_chat_pos))
                    chunk = f.read()
                    self._current_chat_pos = f.tell()
            except Exception as e:
                try:
                    self.logger.error(
                        f"ChatCommandMonitor falha ao ler chat log: {e}",
                        {"file": str(file_path)},
                    )
                except Exception:
                    pass
                return

            if not chunk:
                return

            if self._pending_chat_bytes:
                chunk = self._pending_chat_bytes + chunk
                self._pending_chat_bytes = b""

            if len(chunk) % 2 == 1:
                # UTF-16LE: manter byte pendente para o próximo read.
                self._pending_chat_bytes = chunk[-1:]
                chunk = chunk[:-1]

            try:
                text = chunk.decode("utf-16le", errors="ignore")
            except Exception:
                text = ""

            if not text:
                return

            if self._pending_chat_text:
                text = self._pending_chat_text + text
                self._pending_chat_text = ""

            # Se o último pedaço não termina em newline, guardar para próxima iteração.
            if not text.endswith("\n"):
                last_nl = text.rfind("\n")
                if last_nl == -1:
                    self._pending_chat_text = text
                    return
                self._pending_chat_text = text[last_nl + 1 :]
                text = text[: last_nl + 1]

            lines = [ln.strip("\r") for ln in text.split("\n") if ln.strip()]
            if not lines:
                return

            filename = os.path.basename(file_path)
            for idx, line in enumerate(lines, 1):
                self._process_chat_line(line=line, filename=filename, virtual_line_no=idx)
        except Exception:
            return
        finally:
            try:
                if temp_path and temp_path != file_path:
                    self.temp_manager.cleanup_temp_file(temp_path)
            except Exception:
                pass

    def _process_chat_line(self, *, line: str, filename: str, virtual_line_no: int) -> None:
        try:
            parsed = self._parse_chat_line(line)
            if not parsed:
                return

            ts = str(parsed.get("timestamp") or "").strip()
            # Evitar reprocessar logs antigos ao iniciar/reconectar:
            # se a linha tiver timestamp <= último timestamp processado, ignorar.
            try:
                if ts:
                    ts_dt = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                    if self.last_processed_chat_ts and ts_dt <= self.last_processed_chat_ts:
                        return
            except Exception:
                ts_dt = None
            steam_id = str(parsed.get("steam_id") or "").strip()
            player = str(parsed.get("player_name") or "").strip() or "Player"
            player_id = parsed.get("player_id")
            msg = str(parsed.get("message") or "").strip()
            if not msg:
                return

            cmd = None
            for k in self.command_patterns.keys():
                if re.search(self.command_patterns[k], msg, flags=re.IGNORECASE):
                    cmd = k
                    break
            if not cmd:
                return

            try:
                self.logger.info(
                    "ChatCommandMonitor comando detectado",
                    {"cmd": str(cmd), "player": str(player), "file": str(filename)},
                )
            except Exception:
                pass

            # Deduplicação estável: o LogProcessor pode entregar batches com índices reiniciando.
            # Usar hash de campos imutáveis da mensagem.
            try:
                if cmd == "vbuy":
                    stable_key = "|".join(
                        [
                            str(steam_id or ""),
                            str(player or ""),
                            str(msg or ""),
                            str(cmd or ""),
                        ]
                    )
                else:
                    stable_key = "|".join(
                        [
                            str(ts or ""),
                            str(steam_id or ""),
                            str(player or ""),
                            str(msg or ""),
                            str(cmd or ""),
                        ]
                    )
                command_id = hashlib.sha256(stable_key.encode("utf-8", errors="ignore")).hexdigest()
            except Exception:
                if cmd == "vbuy":
                    command_id = f"{steam_id}:{player}:{cmd}"
                else:
                    command_id = f"{ts}:{player}:{cmd}:{int(virtual_line_no)}"
            if command_id in self.processed_commands:
                return

            self.processed_commands.add(command_id)
            self._save_processed_commands()

            if cmd == "vbuy":
                # self._handle_vbuy_command(steam_id, player, msg, command_id)
                try:
                    if ts:
                        ts_dt2 = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                        if not self.last_processed_chat_ts or ts_dt2 > self.last_processed_chat_ts:
                            self.last_processed_chat_ts = ts_dt2
                            self._save_last_processed_chat_ts()
                except Exception:
                    pass
                return
            if cmd in ("buy", "kit"):
                self._handle_buy_command(steam_id, player, msg, command_id)
                try:
                    if ts:
                        ts_dt2 = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                        if not self.last_processed_chat_ts or ts_dt2 > self.last_processed_chat_ts:
                            self.last_processed_chat_ts = ts_dt2
                            self._save_last_processed_chat_ts()
                except Exception:
                    pass
                return
            if cmd == "mail":
                # self._handle_mail_command(steam_id, player, msg)
                try:
                    if ts:
                        ts_dt2 = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                        if not self.last_processed_chat_ts or ts_dt2 > self.last_processed_chat_ts:
                            self.last_processed_chat_ts = ts_dt2
                            self._save_last_processed_chat_ts()
                except Exception:
                    pass
                return
            if cmd == "tmail":
                # self._handle_tmail_command(steam_id, player, msg)
                try:
                    if ts:
                        ts_dt2 = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                        if not self.last_processed_chat_ts or ts_dt2 > self.last_processed_chat_ts:
                            self.last_processed_chat_ts = ts_dt2
                            self._save_last_processed_chat_ts()
                except Exception:
                    pass
                return
            if cmd == "tm":
                self._handle_tm_command(player)
                try:
                    if ts:
                        ts_dt2 = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                        if not self.last_processed_chat_ts or ts_dt2 > self.last_processed_chat_ts:
                            self.last_processed_chat_ts = ts_dt2
                            self._save_last_processed_chat_ts()
                except Exception:
                    pass
                return
            if cmd == "sd":
                self._handle_sd_command(steam_id, player)
                if self.commands_webhook:
                    try:
                        requests.post(
                            self.commands_webhook,
                            json={"content": f"{player}: {msg}"},
                            timeout=10,
                        )
                    except Exception:
                        pass
                try:
                    if ts:
                        ts_dt2 = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                        if not self.last_processed_chat_ts or ts_dt2 > self.last_processed_chat_ts:
                            self.last_processed_chat_ts = ts_dt2
                            self._save_last_processed_chat_ts()
                except Exception:
                    pass
                return

            if cmd == "rd":
                self._handle_rd_command(steam_id, player, msg)
                if self.commands_webhook:
                    try:
                        requests.post(
                            self.commands_webhook,
                            json={"content": f"{player}: {msg}"},
                            timeout=10,
                        )
                    except Exception:
                        pass
                try:
                    if ts:
                        ts_dt2 = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                        if not self.last_processed_chat_ts or ts_dt2 > self.last_processed_chat_ts:
                            self.last_processed_chat_ts = ts_dt2
                            self._save_last_processed_chat_ts()
                except Exception:
                    pass
                return

            if cmd == "atr":
                self._handle_atr_command(steam_id, player, msg)
                try:
                    if ts:
                        ts_dt2 = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                        if not self.last_processed_chat_ts or ts_dt2 > self.last_processed_chat_ts:
                            self.last_processed_chat_ts = ts_dt2
                            self._save_last_processed_chat_ts()
                except Exception:
                    pass
                return

            if cmd == "attr_upgrade":
                self._handle_attr_upgrade_command(steam_id, player, msg, command_id)
                try:
                    if ts:
                        ts_dt2 = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                        if not self.last_processed_chat_ts or ts_dt2 > self.last_processed_chat_ts:
                            self.last_processed_chat_ts = ts_dt2
                            self._save_last_processed_chat_ts()
                except Exception:
                    pass
                return

            if cmd == "register":
                self._handle_register_command(
                    steam_id=steam_id,
                    player_name=player,
                    player_id=player_id,
                    message_text=msg,
                )
                try:
                    if ts:
                        ts_dt2 = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                        if not self.last_processed_chat_ts or ts_dt2 > self.last_processed_chat_ts:
                            self.last_processed_chat_ts = ts_dt2
                            self._save_last_processed_chat_ts()
                except Exception:
                    pass
                return

            if cmd == "evento":
                self._handle_evento_command(
                    steam_id=steam_id,
                    player_name=player,
                    message_text=msg,
                )
                try:
                    if ts:
                        ts_dt2 = datetime.strptime(ts, "%Y.%m.%d-%H.%M.%S")
                        if not self.last_processed_chat_ts or ts_dt2 > self.last_processed_chat_ts:
                            self.last_processed_chat_ts = ts_dt2
                            self._save_last_processed_chat_ts()
                except Exception:
                    pass
                return
        except Exception:
            return

    def _handle_register_command(
        self,
        *,
        steam_id: str,
        player_name: str,
        player_id: Any,
        message_text: str,
    ) -> None:
        try:
            txt = str(message_text or "").strip()
            m = re.search(r"!register\s+([A-Za-z0-9\-]{4,64})", txt, flags=re.IGNORECASE)
            if not m:
                return
            code = str(m.group(1) or "").strip()
            if not code:
                return

            if not steam_id:
                return

            import sqlite3

            now = datetime.utcnow().isoformat()
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                cur = conn.cursor()

                cur.execute(
                    """
                    SELECT id, discord_user_id, expires_at
                    FROM discord_link_tokens
                    WHERE code = ?
                      AND consumed_at IS NULL
                      AND expires_at > ?
                    LIMIT 1
                    """,
                    (str(code), str(now)),
                )
                tok = cur.fetchone()
                if not tok:
                    return

                token_id, discord_user_id, _expires_at = tok
                discord_user_id = str(discord_user_id or "").strip()
                if not discord_user_id:
                    return

                # Bloqueios de relink
                cur.execute(
                    "SELECT discord_user_id FROM players WHERE steam_id = ? LIMIT 1",
                    (str(steam_id),),
                )
                row = cur.fetchone()
                if row and row[0]:
                    self._notify_discord_register_result(
                        discord_user_id,
                        "This Steam account is already linked. Contact an admin to unregister.",
                    )
                    return

                cur.execute(
                    "SELECT steam_id FROM players WHERE discord_user_id = ? LIMIT 1",
                    (str(discord_user_id),),
                )
                row2 = cur.fetchone()
                if row2 and row2[0] and str(row2[0]) != str(steam_id):
                    self._notify_discord_register_result(
                        discord_user_id,
                        "This Discord account is already linked. Contact an admin to unregister.",
                    )
                    return

                # Garantir player row (players tem campos NOT NULL)
                cur.execute(
                    "SELECT steam_id FROM players WHERE steam_id = ? LIMIT 1",
                    (str(steam_id),),
                )
                exists = cur.fetchone() is not None
                if not exists:
                    try:
                        pid_int = int(player_id) if player_id is not None else 0
                    except Exception:
                        pid_int = 0
                    cur.execute(
                        """
                        INSERT INTO players(
                            steam_id,
                            player_name,
                            player_id,
                            first_seen,
                            last_seen,
                            total_sessions,
                            total_playtime,
                            is_new_player,
                            notification_sent,
                            permissao
                        )
                        VALUES(?, ?, ?, ?, ?, 0, 0, 0, 0, 0)
                        """,
                        (str(steam_id), str(player_name or "Player"), int(pid_int), str(now), str(now)),
                    )

                cur.execute(
                    """
                    UPDATE players
                    SET discord_user_id = ?, discord_linked_at = ?
                    WHERE steam_id = ?
                    """,
                    (str(discord_user_id), str(now), str(steam_id)),
                )

                cur.execute(
                    """
                    UPDATE discord_link_tokens
                    SET consumed_at = ?, consumed_by_steam_id = ?
                    WHERE id = ?
                    """,
                    (str(now), str(steam_id), int(token_id)),
                )

                # Auto-inserir na regra "Padrão" para ganhar pontos por hora
                try:
                    from core.shop.rewards_service import RewardsService
                    rewards = RewardsService(self.ssm_db_path, logger=self.logger)
                    rewards._ensure_playtime_rules_schema(conn)
                    default_rule_id = rewards.get_playtime_rule_id_by_name("Padrão", conn=conn)
                    if default_rule_id:
                        rewards.add_playtime_rule_target_conn(str(default_rule_id), str(steam_id), conn)
                except Exception as e:
                    try:
                        self.logger.error(f"Falha ao inserir steam_id={steam_id} na regra 'Padrão' após !register: {e}")
                    except Exception:
                        pass

                conn.commit()

            safe_player = str(player_name or "Player").strip() or "Player"
            try:
                self.logger.info(
                    "Register link completed; sending confirmations",
                    {
                        "player": str(safe_player),
                        "steam_id": str(steam_id),
                        "discord_user_id": str(discord_user_id),
                        "dm_available": bool(self.discord_bot_service is not None),
                    },
                )
            except Exception:
                pass

            # Entrega Automática do Kit de Boas-Vindas (Welcome Pack)
            welcome_kit_code = None
            welcome_kit_name = None
            try:
                with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT code, name FROM shop_kit WHERE auto_deliver_on_register = 1 LIMIT 1"
                    )
                    row = cur.fetchone()
                    if row:
                        welcome_kit_code, welcome_kit_name = row
            except Exception as db_err:
                try:
                    self.logger.error(f"Erro ao buscar kit de boas-vindas: {db_err}")
                except Exception:
                    pass

            if welcome_kit_code is not None:
                already_received = False
                try:
                    with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                        cur = conn.cursor()
                        cur.execute(
                            """
                            SELECT 1 FROM shop_order o
                            JOIN shop_order_item oi ON oi.order_id = o.order_id
                            WHERE o.steam_id = ? AND oi.code = ? AND o.status IN ('pending', 'delivering', 'delivered')
                            LIMIT 1
                            """,
                            (str(steam_id), int(welcome_kit_code))
                        )
                        if cur.fetchone():
                            already_received = True
                except Exception as db_err:
                    try:
                        self.logger.error(f"Erro ao verificar recebimento do kit de boas-vindas: {db_err}")
                    except Exception:
                        pass

                if not already_received:
                    try:
                        shop = ShopService(self.ssm_db_path, logger=self.logger)
                        order_res = shop.create_order(
                            steam_id=steam_id,
                            items=[OrderCreateItem(code=int(welcome_kit_code), qty=1, is_kit=True)],
                            player_name=safe_player
                        )
                        
                        try:
                            self.logger.info(
                                f"Pedido de boas-vindas gerado para {safe_player}",
                                {"order_id": order_res.order_id, "kit_code": welcome_kit_code}
                            )
                        except Exception:
                            pass

                        self._send_shop_log_message(
                            f"**[WELCOME PACK]** : Automatic order created for **{safe_player}** (SteamID: {steam_id}). Kit: {welcome_kit_name}."
                        )

                        # Disparar entrega assíncrona
                        def trigger_delivery_async():
                            try:
                                import json
                                import sys
                                from pathlib import Path
                                scum_db_path = "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
                                try:
                                    config_file = "data/config.json"
                                    if getattr(sys, "frozen", False):
                                        exe_dir = Path(sys.executable).parent
                                        config_path = exe_dir / config_file
                                    else:
                                        config_path = Path(config_file)
                                    with open(config_path, "r", encoding="utf-8") as f:
                                        cfg = json.load(f)
                                        scum_db_path = cfg.get("paths", {}).get("scum_server", {}).get("database", scum_db_path)
                                except Exception:
                                    pass
                                
                                from core.shop.delivery_service import ShopDeliveryService
                                svc = ShopDeliveryService(self.ssm_db_path, scum_db_path, logger=self.logger)
                                svc.run_once(limit=10)
                            except Exception as e:
                                try:
                                    self.logger.error(f"Erro ao disparar entrega imediata do Welcome Pack: {e}")
                                except Exception:
                                    pass

                        threading.Thread(target=trigger_delivery_async, daemon=True).start()

                    except Exception as order_err:
                        try:
                            self.logger.error(f"Falha ao gerar pedido automático de boas-vindas: {order_err}")
                        except Exception:
                            pass
                        self._send_shop_log_message(
                            f"**[WELCOME PACK]** : Failed to create automatic order for **{safe_player}**. Error: {order_err}"
                        )

            role_ok = None
            role_reason = ""
            try:
                if self.discord_bot_service is not None:
                    try:
                        uid_int = int(str(discord_user_id).strip())
                    except Exception:
                        uid_int = 0
                    if uid_int > 0:
                        ok_role, reason = self.discord_bot_service.assign_register_role(uid_int)
                        if str(reason or "").strip() != "disabled":
                            role_ok = bool(ok_role)
                            role_reason = str(reason or "")
            except Exception:
                pass

            self._notify_discord_register_result(
                discord_user_id,
                "[TEC1 // LINK CONFIRMATION]\n\n"
                "Registration successful.\n\n"
                "Your digital identity has been integrated into the system.\n"
                "You are now traceable. You are now under control.\n\n"
                f"Subject: {safe_player}\n"
                f"Identifier (SteamID): {steam_id}\n\n"
                "Remain compliant.\n\n"
                "SSM // CENTRAL CONTROL",
            )

            if role_ok is False:
                try:
                    self._notify_discord_register_result(
                        discord_user_id,
                        "Registration completed, but role assignment failed. Please contact an admin.\n\n"
                        f"Reason: {role_reason}",
                    )
                except Exception:
                    pass

            self._notify_commands_webhook(
                f"✅ Registration complete: **{safe_player}** linked their Discord account successfully."
            )

            if role_ok is True:
                try:
                    self._notify_commands_webhook(
                        f"✅ Role assigned after register: **{safe_player}** (discord_user_id={discord_user_id})"
                    )
                except Exception:
                    pass
            elif role_ok is False:
                try:
                    self._notify_commands_webhook(
                        f"⚠️ Role assignment failed after register: **{safe_player}** (discord_user_id={discord_user_id}) reason={role_reason}"
                    )
                except Exception:
                    pass
        except Exception as e:
            try:
                self.logger.warn(f"Falha ao processar !register: {e}")
            except Exception:
                pass

    def _handle_evento_command(self, steam_id: str, player_name: str, message_text: str) -> None:
        try:
            txt = str(message_text or "").strip()
            # Extrair o código (ex: /evento 7F3A)
            m = re.search(r'/evento\s+([A-Za-z0-9]+)', txt, flags=re.IGNORECASE)
            if not m:
                return
            
            code = str(m.group(1) or "").strip().upper()
            if not code or not steam_id:
                return

            # Verificar se o jogador está preso
            try:
                from app.extensions import get_services
                svc = get_services()
                if getattr(svc, 'squad_tk_jail_service', None) and svc.squad_tk_jail_service.is_player_jailed(steam_id):
                    # Informar in-game e retornar
                    from core.rcon_queue_manager import RconQueueManager
                    rcon_q = RconQueueManager.get_instance()
                    chat_color = int(svc.squad_tk_jail_service.warning_color) if (svc.squad_tk_jail_service.warning_color.isdigit() and svc.squad_tk_jail_service.use_colors) else 7
                    rcon_q.enqueue_command(f'SendChat {chat_color} "Você não pode entrar em eventos enquanto estiver preso!" {steam_id}', priority=20)
                    return
            except Exception as jail_check_err:
                self.logger.error(f"Erro ao verificar se jogador está preso no /evento: {jail_check_err}")

            import json
            from pathlib import Path
            codes_file = str(Path(self.ssm_db_path).parent / "event_teleport_codes.json")
            if not os.path.exists(codes_file):
                return

            # Ler o registro de códigos
            try:
                with open(codes_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                return

            codes = data.get("codes", {})
            if code not in codes:
                return

            entry = codes[code]
            # Validar se o SteamID coincide
            if entry.get("steam_id") != steam_id:
                try:
                    self.logger.warn(f"[EVENTO] Jogador {player_name} ({steam_id}) tentou usar código {code} do jogador {entry.get('player_name')} ({entry.get('steam_id')})")
                except Exception:
                    pass
                return

            event_id = entry.get("event_id")
            if not event_id:
                return

            # Consultar se o evento está ativo e obter coordenadas
            import sqlite3
            x, y, z = None, None, None
            event_name = "Evento"
            
            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute(
                    "SELECT status, name FROM event_configs WHERE event_id = ? LIMIT 1",
                    (event_id,)
                )
                event_row = cur.fetchone()
                
                if not event_row or event_row["status"] != "active":
                    return
                
                event_name = event_row["name"]

                # Puxar coordenadas
                cur = conn.execute(
                    "SELECT name, x, y, z FROM event_coordinates WHERE event_id = ?",
                    (event_id,)
                )
                coord_rows = cur.fetchall()

            if coord_rows:
                import random
                chosen_coord = random.choice(coord_rows)
                x, y, z = chosen_coord["x"], chosen_coord["y"], chosen_coord["z"]
            else:
                # Fallback: escanear comandos de inicialização
                with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cur = conn.execute(
                        "SELECT command_string FROM event_startup_commands WHERE event_id = ? ORDER BY order_index ASC, startup_id ASC",
                        (event_id,)
                    )
                    commands = cur.fetchall()

                import re as _re
                for cmd in commands:
                    cmd_str = cmd["command_string"]
                    match = _re.search(r'\{X=([\d\.\-]+)[,\s]+Y=([\d\.\-]+)[,\s]+Z=([\d\.\-]+)', cmd_str, _re.IGNORECASE)
                    if match:
                        try:
                            x, y, z = float(match.group(1)), float(match.group(2)), float(match.group(3))
                            break
                        except ValueError:
                            pass

                    match = _re.search(r'#ScheduleWorldEvent\s+\S+\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)', cmd_str, _re.IGNORECASE)
                    if match:
                        try:
                            x, y, z = float(match.group(1)), float(match.group(2)), float(match.group(3))
                            break
                        except ValueError:
                            pass

            if x is None or y is None or z is None:
                try:
                    self.logger.warn(f"[EVENTO] Evento '{event_name}' não possui coordenadas configuradas.")
                except Exception:
                    pass
                return

            # Enfileirar comando RCON
            from core.rcon_queue_manager import RconQueueManager
            teleport_cmd = f"#teleport {x} {y} {z} {steam_id}"
            rcon_mgr = RconQueueManager.get_instance()
            rcon_mgr.enqueue_command(teleport_cmd, delay_after=1.0, priority=1)

            try:
                self.logger.info(f"[EVENTO] Teleporte de {player_name} ({steam_id}) para coordenadas {x}, {y}, {z} via código {code}")
            except Exception:
                pass

            # Notificar no Discord (canal de comandos)
            if self.discord_bot_service:
                try:
                    chan_id = self.discord_bot_service._get_admin_link_channel_id()
                    if chan_id:
                        async def send_log():
                            try:
                                channel = self.discord_bot_service._bot.get_channel(chan_id)
                                if not channel:
                                    channel = await self.discord_bot_service._bot.fetch_channel(chan_id)
                                if channel:
                                    await channel.send(
                                        f"**[EVENT TELEPORT]** O jogador **{player_name}** (SteamID: `{steam_id}`) teleportou-se para o evento **{event_name}** usando o código `{code}`."
                                    )
                            except Exception as ex:
                                try:
                                    self.discord_bot_service._log_error(f"Erro ao enviar log de teleporte para o Discord: {ex}")
                                except Exception:
                                    pass
                        
                        import asyncio
                        asyncio.run_coroutine_threadsafe(send_log(), self.discord_bot_service._loop)
                except Exception as ex:
                    try:
                        self.logger.error(f"Erro ao disparar envio do log de teleporte para Discord: {ex}")
                    except Exception:
                        pass

        except Exception as e:
            try:
                self.logger.error(f"Erro no manipulador _handle_evento_command: {e}")
            except Exception:
                pass

    def _notify_commands_webhook(self, content: str) -> None:
        try:
            if not self.commands_webhook:
                return
            msg = str(content or "").strip()
            if not msg:
                return
            try:
                requests.post(
                    self.commands_webhook,
                    json={"content": msg},
                    timeout=10,
                )
            except Exception:
                return
        except Exception:
            return

    def _notify_discord_register_result(self, discord_user_id: str, content: str) -> None:
        try:
            if self.discord_bot_service is None:
                try:
                    self.logger.warn(
                        "discord_bot_service unavailable; cannot send DM",
                        {"discord_user_id": str(discord_user_id)},
                    )
                except Exception:
                    pass
                return
            try:
                uid = int(str(discord_user_id).strip())
            except Exception:
                return
            ok = bool(self.discord_bot_service.send_dm(uid, str(content or "")))
            if not ok:
                try:
                    self.logger.warn(
                        "Falha ao enviar DM de confirmação do registro",
                        {"discord_user_id": str(discord_user_id)},
                    )
                except Exception:
                    pass
        except Exception:
            return

    def _parse_chat_line(self, line: str) -> Optional[Dict[str, Any]]:
        try:
            # Mesmo padrão usado no ChatProcessor.
            pattern_channel = r"(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}): '(\d+):([^']+)\((\d+)\)' '(Global|Globaal|Gloobal|Local|Squad|Admin)[:]*\s*(.+)'"
            m = re.match(pattern_channel, str(line or "").strip())
            if not m:
                pattern_generic = r"(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}): '(\d+):([^']+)\((\d+)\)'.*?:\s*(.+)"
                m = re.match(pattern_generic, str(line or "").strip())
                if not m:
                    return None
                ts, steam_id, player_name, player_id, msg = m.groups()
                return {
                    "timestamp": ts,
                    "steam_id": steam_id,
                    "player_name": str(player_name).strip(),
                    "player_id": int(player_id),
                    "channel": None,
                    "message": str(msg).strip(),
                }

            ts, steam_id, player_name, player_id, channel, msg = m.groups()
            channel_norm = str(channel).strip()
            if channel_norm.lower() in ("globaal", "gloobal"):
                channel_norm = "Global"
            return {
                "timestamp": ts,
                "steam_id": steam_id,
                "player_name": str(player_name).strip(),
                "player_id": int(player_id),
                "channel": channel_norm,
                "message": str(msg).strip(),
            }
        except Exception:
            return None

    def _load_commands_webhook(self) -> str:
        try:
            webhooks_path = str(self.data_dir / "webhooks.json")
            if not os.path.exists(webhooks_path):
                return ""
            try:
                from core.webhooks.manager import WebhooksManager

                mgr = WebhooksManager(webhooks_path)
                webhooks = mgr.load()
                return str((webhooks or {}).get("commands") or "").strip()
            except Exception:
                with open(webhooks_path, "r", encoding="utf-8") as f:
                    webhooks = json.load(f)
                return str((webhooks or {}).get("commands") or "").strip()
        except Exception:
            return ""

    def _load_shop_log_webhook(self) -> str:
        try:
            webhooks_path = str(self.data_dir / "webhooks.json")
            if not os.path.exists(webhooks_path):
                return ""
            try:
                from core.webhooks.manager import WebhooksManager

                mgr = WebhooksManager(webhooks_path)
                webhooks = mgr.load()
                return str((webhooks or {}).get("shop-log") or "").strip()
            except Exception:
                with open(webhooks_path, "r", encoding="utf-8") as f:
                    webhooks = json.load(f)
                return str((webhooks or {}).get("shop-log") or "").strip()
        except Exception:
            return ""

    def _load_processed_commands(self) -> set:
        try:
            if not os.path.exists(self.processed_commands_file):
                return set()
            with open(self.processed_commands_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return {str(x) for x in data if x}
            if isinstance(data, dict):
                cmds = data.get("processed_commands")
                if isinstance(cmds, list):
                    return {str(x) for x in cmds if x}
            return set()
        except Exception:
            return set()

    def _save_processed_commands(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.processed_commands_file), exist_ok=True)
            with open(self.processed_commands_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"processed_commands": sorted(list(self.processed_commands))},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception:
            return

    def _load_last_processed_chat_ts(self) -> Optional[datetime]:
        try:
            if not os.path.exists(self.chat_state_file):
                return None
            with open(self.chat_state_file, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            last_ts = str((data or {}).get("last_processed_chat_ts") or "").strip()
            if not last_ts:
                return None
            return datetime.strptime(last_ts, "%Y.%m.%d-%H.%M.%S")
        except Exception:
            return None

    def _save_last_processed_chat_ts(self) -> None:
        try:
            if not self.last_processed_chat_ts:
                return
            os.makedirs(os.path.dirname(self.chat_state_file), exist_ok=True)
            payload = {
                "last_processed_chat_ts": self.last_processed_chat_ts.strftime(
                    "%Y.%m.%d-%H.%M.%S"
                )
            }
            with open(self.chat_state_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception:
            return

    def _load_time_precision_config(self) -> Dict[str, Any]:
        try:
            import sys
            from pathlib import Path
            config_file = "data/config.json"
            if getattr(sys, "frozen", False):
                exe_dir = Path(sys.executable).parent
                config_path = exe_dir / config_file
            else:
                config_path = Path(config_file)

            if not os.path.exists(config_path):
                return {"enabled": False, "offset_minutes": 0}

            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            tp = (cfg or {}).get("time_precision")
            if isinstance(tp, dict):
                return {
                    "enabled": bool(tp.get("enabled", False)),
                    "offset_minutes": int(tp.get("offset_minutes", 0) or 0),
                }
            return {"enabled": False, "offset_minutes": 0}
        except Exception:
            return {"enabled": False, "offset_minutes": 0}

    def _get_time_precision_offset(self) -> int:
        try:
            cfg = self.time_precision_config or {}
            if not isinstance(cfg, dict):
                return 0
            if not bool(cfg.get("enabled", False)):
                return 0
            return int(cfg.get("offset_minutes", 0) or 0)
        except Exception:
            return 0

    def _apply_time_precision_offset(self, server_time: str) -> str:
        try:
            offset = int(self._get_time_precision_offset() or 0)
            if offset == 0:
                return str(server_time)

            s = str(server_time or "").strip()
            if not s or ":" not in s:
                return str(server_time)

            parts = s.split(":", 1)
            h = int(parts[0])
            m = int(parts[1])
            base_time = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
            adjusted = base_time + timedelta(minutes=offset)
            return f"{int(adjusted.hour):02d}:{int(adjusted.minute):02d}"
        except Exception:
            return str(server_time)

    def _send_shop_log_message(self, content: str) -> None:
        try:
            webhook = str(self.shop_log_webhook or "").strip()
            if not webhook:
                return

            payload = {"content": str(content or "").strip()}
            requests.post(webhook, json=payload, timeout=15)
        except Exception as e:
            try:
                self.logger.error(f"Falha ao enviar shop-log message: {e}")
            except Exception:
                pass

    def _send_shop_log_embed(
        self, *, embed: Dict[str, Any], thumbnail_path: Optional[str] = None
    ) -> None:
        try:
            webhook = str(self.shop_log_webhook or "").strip()
            if not webhook:
                return

            safe_embed = embed or {}

            if thumbnail_path:
                try:
                    p = str(thumbnail_path)
                    if os.path.exists(p) and os.path.isfile(p):
                        filename = os.path.basename(p)
                        mime, _ = mimetypes.guess_type(filename)
                        if not mime:
                            mime = "application/octet-stream"

                        safe_embed = dict(safe_embed)
                        safe_embed["thumbnail"] = {"url": f"attachment://{filename}"}
                        payload_json = json.dumps({"embeds": [safe_embed]}, ensure_ascii=False)
                        with open(p, "rb") as f:
                            files = {"files[0]": (filename, f.read(), mime)}
                            resp = requests.post(
                                webhook,
                                data={"payload_json": payload_json},
                                files=files,
                                timeout=30,
                            )
                        try:
                            if int(getattr(resp, "status_code", 0) or 0) >= 300:
                                self.logger.error(
                                    "Falha ao enviar embed shop-log",
                                    {
                                        "status": int(getattr(resp, "status_code", 0) or 0),
                                        "text": str(getattr(resp, "text", "") or "")[:1000],
                                    },
                                )
                        except Exception:
                            pass
                        return
                except Exception as e:
                    try:
                        self.logger.error(f"Falha ao enviar embed shop-log com thumbnail: {e}")
                    except Exception:
                        pass

            resp = requests.post(webhook, json={"embeds": [safe_embed]}, timeout=30)
            try:
                if int(getattr(resp, "status_code", 0) or 0) >= 300:
                    self.logger.error(
                        "Falha ao enviar embed shop-log",
                        {
                            "status": int(getattr(resp, "status_code", 0) or 0),
                            "text": str(getattr(resp, "text", "") or "")[:1000],
                        },
                    )
            except Exception:
                pass
        except Exception as e:
            try:
                self.logger.error(f"Falha ao enviar embed shop-log: {e}")
            except Exception:
                pass

    def _resolve_vehicle_thumbnail_path_from_catalog(self, *, code: int) -> Optional[str]:
        try:
            if not os.path.exists(self.ssm_db_path):
                return None

            import sqlite3

            image_url = None
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        "SELECT image_url FROM vehicle_catalog WHERE code = ?",
                        (int(code),),
                    )
                    row = cur.fetchone()
                    if row:
                        image_url = row[0]
                except Exception:
                    image_url = None

            if not image_url:
                return None

            url = str(image_url).strip()
            if not url:
                return None

            filename = url
            try:
                q = filename.find("?")
                if q != -1:
                    filename = filename[:q]
                h = filename.find("#")
                if h != -1:
                    filename = filename[:h]
            except Exception:
                pass

            if "/api/vehicles/assets/" in filename:
                filename = filename.split("/api/vehicles/assets/", 1)[1]
            filename = filename.replace("\\", "/")
            filename = filename.split("/")[-1]
            filename = str(filename).strip()
            if not filename:
                return None

            candidate = os.path.join(self.vehicle_images_path, filename)
            if os.path.exists(candidate) and os.path.isfile(candidate):
                return candidate

            if os.path.exists(url) and os.path.isfile(url):
                return url
            return None
        except Exception:
            return None

    def _handle_vbuy_command(
        self, steam_id: str, player: str, message_text: str, command_id: str
    ) -> None:
        try:
            code, payload = self._parse_vbuy(message_text)
            if code is None or not payload:
                self._send_shop_log_message(
                    f"**{player}** : Usage: /vbuy <code> {{X=.. Y=.. Z=..|P=.. Y=.. R=..}}"
                )
                return

            pos, rot = self._parse_delivery_payload(payload)
            if pos is None:
                self._send_shop_log_message(
                    f"**{player}** : Invalid coordinates. Ex: /vbuy 1 {{X=.. Y=.. Z=..|P=.. Y=.. R=..}}"
                )
                return

            if not os.path.exists(self.ssm_db_path):
                self._send_shop_log_message(
                    f"**{player}** : Internal error: SSM.db not found."
                )
                return

            import sqlite3
            from core.shop.db import ssm_tx

            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT display_name, template_vehicle_entity_id, price, enabled
                    FROM vehicle_catalog
                    WHERE code = ?
                    """,
                    (int(code),),
                )
                row = cur.fetchone()

            if not row:
                self._send_shop_log_message(
                    f"**{player}** : Invalid vehicle. Code: {int(code)}"
                )
                return

            display_name, template_id, price, enabled = row
            if int(enabled or 0) != 1:
                self._send_shop_log_message(
                    f"**{player}** : Vehicle currently unavailable. ({str(display_name)})"
                )
                return

            x, y, z = pos
            keep_template_rotation = 1
            new_rot_x = None
            new_rot_y = None
            new_rot_z = None
            if rot is not None:
                keep_template_rotation = 0
                rx, ry, rz = rot
                new_rot_x = float(rx)
                new_rot_y = float(ry)
                new_rot_z = float(rz)

            # Idempotência do /vbuy:
            # - O SCUM pode reescrever/rotacionar logs; o mesmo comando pode reaparecer sem ser um novo pedido.
            # - Gerar idempotency_key por fingerprint normalizado + bucket por dia (UTC), evitando duplicar.
            try:
                bucket = datetime.utcnow().date().isoformat()
            except Exception:
                bucket = ""

            if keep_template_rotation:
                rot_key = "template"
            else:
                rot_key = f"{float(new_rot_x or 0.0):.3f},{float(new_rot_y or 0.0):.3f},{float(new_rot_z or 0.0):.3f}"

            vbuy_fingerprint = (
                f"vbuy|{str(steam_id)}|{int(code)}|"
                f"{float(x):.3f},{float(y):.3f},{float(z):.3f}|{rot_key}|{bucket}"
            )
            idempotency_key = compute_idempotency_key(vbuy_fingerprint)

            price_i = int(price or 0)

            wallet = WalletService(self.ssm_db_path, logger=self.logger)
            try:
                with ssm_tx(self.ssm_db_path) as tx:
                    # Se já existe pedido com este fingerprint (mesmo dia), não recriar nem cobrar.
                    try:
                        cur = tx.execute(
                            "SELECT 1 FROM vehicle_order WHERE idempotency_key = ? LIMIT 1",
                            (str(idempotency_key),),
                        )
                        if cur.fetchone():
                            return
                    except Exception:
                        pass

                    wallet.apply_delta(
                        steam_id=steam_id,
                        delta=-int(price_i),
                        reason="vehicle_purchase",
                        ref_type="vbuy",
                        ref_id=idempotency_key,
                        meta={
                            "code": int(code),
                            "template_vehicle_entity_id": int(template_id),
                        },
                        allow_negative=False,
                        conn=tx,
                    )

                    order_id = uuid.uuid4().hex

                    try:
                        tx.execute(
                            """
                            INSERT INTO vehicle_order(
                                order_id,
                                idempotency_key,
                                template_vehicle_entity_id,
                                new_x,
                                new_y,
                                new_z,
                                keep_template_rotation,
                                new_rot_x,
                                new_rot_y,
                                new_rot_z,
                                requested_steam_id,
                                requested_player_name,
                                requested_vehicle_code,
                                requested_vehicle_name,
                                status,
                                attempt_count,
                                created_at,
                                updated_at
                            )
                            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, datetime('now'), datetime('now'))
                            """,
                            (
                                str(order_id),
                                str(idempotency_key),
                                int(template_id),
                                float(x),
                                float(y),
                                float(z),
                                int(keep_template_rotation),
                                new_rot_x,
                                new_rot_y,
                                new_rot_z,
                                str(steam_id),
                                str(player),
                                int(code),
                                str(display_name),
                            ),
                        )
                    except sqlite3.IntegrityError:
                        # idempotency_key é UNIQUE; se bater corrida, não duplicar.
                        return
                    except sqlite3.OperationalError as oe:
                        msg = str(oe or "")
                        if "no column named requested_steam_id" not in msg:
                            raise
                        tx.execute(
                            """
                            INSERT INTO vehicle_order(
                                order_id,
                                idempotency_key,
                                template_vehicle_entity_id,
                                new_x,
                                new_y,
                                new_z,
                                keep_template_rotation,
                                new_rot_x,
                                new_rot_y,
                                new_rot_z,
                                status,
                                attempt_count,
                                created_at,
                                updated_at
                            )
                            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, datetime('now'), datetime('now'))
                            """,
                            (
                                str(order_id),
                                str(idempotency_key),
                                int(template_id),
                                float(x),
                                float(y),
                                float(z),
                                int(keep_template_rotation),
                                new_rot_x,
                                new_rot_y,
                                new_rot_z,
                            ),
                        )

                thumb = self._resolve_vehicle_thumbnail_path_from_catalog(code=int(code))
                if not thumb:
                    try:
                        self.logger.warn(
                            f"Thumbnail nao encontrado para vehicle code={int(code)} (ssm_db_path={self.ssm_db_path})"
                        )
                    except Exception:
                        pass
                embed = {
                    "title": "Pedido de veículo recebido",
                    "color": 0x2ECC71,
                    "fields": [
                        {"name": "\u200b", "value": str(player), "inline": True},
                        {
                            "name": "\u200b",
                            "value": f"{int(code)} {str(display_name)}",
                            "inline": True,
                        },
                        {
                            "name": "Location",
                            "value": "```text\n"
                            + f"#Teleport {float(x):.4f} {float(y):.4f} {float(z):.3f}"
                            + "\n```",
                            "inline": False,
                        },
                    ],
                    "footer": {"text": f"Order: {order_id} • Steam ID: {steam_id}"},
                }
                self._send_shop_log_embed(embed=embed, thumbnail_path=thumb)

            except ValueError as ve:
                if str(ve) == "INSUFFICIENT_FUNDS":
                    bal = 0
                    try:
                        bal = wallet.get_balance(steam_id)
                    except Exception:
                        bal = 0
                    self._send_shop_log_message(
                        f"**{player}** : Insufficient funds. Price: {price_i} | Balance: {int(bal)}"
                    )
                    return
                raise

        except Exception as e:
            self.logger.error(f"Erro ao executar comando /vbuy: {e}")
            self._send_shop_log_message(
                f"**{player}** : Error processing vehicle purchase."
            )

    def _parse_vbuy(self, message_text: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            text = str(message_text or "").strip()
            if not text.lower().startswith("/vbuy"):
                return None, None

            # Aceitar formatos:
            # - /vbuy 1 {X=.. Y=.. Z=..|P=.. Y=.. R=..}
            # - /vbuy 1{X=.. Y=.. Z=..|P=.. Y=.. R=..}
            m = re.match(r"^/vbuy\s+(\d+)\s*\{(.+)\}\s*$", text, flags=re.IGNORECASE)
            if m:
                code = str(m.group(1)).strip()
                payload = str(m.group(2)).strip()
                return code, payload

            # Fallback mais permissivo
            parts = text.split(None, 1)
            if len(parts) < 2:
                return None, None

            rest = parts[1].strip()
            m2 = re.match(r"^(\d+)\s*(.*)$", rest)
            if not m2:
                return None, None

            code = str(m2.group(1)).strip()
            tail = str(m2.group(2) or "").strip()
            i1 = tail.find("{")
            i2 = tail.rfind("}")
            if i1 == -1 or i2 == -1 or i2 <= i1:
                self.logger.warn(f"Comando /vbuy inválido: {text}")
                return code, None
            payload = tail[i1 + 1 : i2].strip()
            return code, payload
        except Exception:
            return None, None

    def _parse_delivery_payload(
        self, payload: str
    ) -> Tuple[Optional[Tuple[float, float, float]], Optional[Tuple[float, float, float]]]:
        try:
            raw = str(payload or "").strip()
            if not raw:
                return None, None

            parts = [p.strip() for p in raw.split("|") if p.strip()]
            pos_part = parts[0] if parts else ""
            rot_part = parts[1] if len(parts) > 1 else ""

            pos_vals: Dict[str, float] = {}
            for tok in re.split(r"\s+", pos_part):
                if "=" not in tok:
                    continue
                k, v = tok.split("=", 1)
                k = k.strip().upper()
                try:
                    pos_vals[k] = float(v)
                except Exception:
                    pass

            if not all(k in pos_vals for k in ("X", "Y", "Z")):
                return None, None
            pos = (float(pos_vals["X"]), float(pos_vals["Y"]), float(pos_vals["Z"]))

            if not rot_part:
                return pos, None

            rot_vals: Dict[str, float] = {}
            for tok in re.split(r"\s+", rot_part):
                if "=" not in tok:
                    continue
                k, v = tok.split("=", 1)
                k = k.strip().upper()
                try:
                    rot_vals[k] = float(v)
                except Exception:
                    pass

            # Esperado: P, Y, R
            if all(k in rot_vals for k in ("P", "Y", "R")):
                rot = (float(rot_vals["P"]), float(rot_vals["Y"]), float(rot_vals["R"]))
                return pos, rot

            return pos, None
        except Exception:
            return None, None

    def _parse_single_int_arg(self, message_text: str) -> Optional[int]:
        try:
            tokens = str(message_text or "").strip().split()
            if len(tokens) < 2:
                return None
            if not str(tokens[1]).strip().lstrip("-").isdigit():
                return None
            return int(tokens[1])
        except Exception:
            return None

    def _handle_mail_command(self, steam_id: str, player: str, message_text: str) -> None:
        try:
            chest_id = self._parse_single_int_arg(message_text)
            if chest_id is None:
                self._send_shop_log_message(f"**{player}** : Usage: /mail <id>")
                return

            shop = ShopService(self.ssm_db_path, logger=self.logger)
            shop.upsert_mailbox(steam_id, int(chest_id))
            self._send_shop_log_message(
                f"**{player}** : Mailbox registered: {int(chest_id)}\nDeliveries after restart."
            )
        except Exception as e:
            self.logger.error(f"Erro ao executar comando /mail: {e}")
            self._send_shop_log_message(f"**{player}** : Error registering mailbox.")

    def _handle_tmail_command(self, steam_id: str, player: str, message_text: str) -> None:
        try:
            chest_id = self._parse_single_int_arg(message_text)
            if chest_id is None:
                self._send_shop_log_message(
                    f"**{player}** : Usage: /tmail <id>"
                )
                return

            shop = ShopService(self.ssm_db_path, logger=self.logger)
            current = shop.get_mailbox(steam_id)
            if current is None:
                self._send_shop_log_message(
                    f"**{player}** : You do not have a mailbox linked. Use /mail <id>."
                )
                return

            shop.upsert_mailbox(steam_id, int(chest_id))
            self._send_shop_log_message(
                f"**{player}** : Mailbox changed: {int(current)} -> {int(chest_id)}\nDeliveries after restart."
            )
        except Exception as e:
            self.logger.error(f"Erro ao executar comando /tmail: {e}")
            self._send_shop_log_message(
                f"**{player}** : Error changing mailbox."
            )

    def _parse_buy_items(self, message_text: str) -> List[OrderCreateItem]:
        items: List[OrderCreateItem] = []
        tokens = str(message_text or "").strip().split()
        if not tokens:
            return items
        first_token = tokens[0].lower()
        if first_token not in ("/buy", "/kit"):
            return items
        for token in tokens[1:]:
            tok = token.strip()
            if not tok:
                continue
            if first_token == "/kit":
                if tok.isdigit():
                    code = int(tok)
                    if code > 0:
                        items.append(OrderCreateItem(code=code, qty=1, is_kit=True))
                continue
            m = re.match(r"^(\d+)\s*[xX]\s*(\d+)$", tok)
            if m:
                code = int(m.group(1))
                qty = int(m.group(2))
                if code > 0 and qty > 0:
                    items.append(OrderCreateItem(code=code, qty=qty, is_kit=False))
                continue
            if tok.isdigit():
                code = int(tok)
                if code > 0:
                    items.append(OrderCreateItem(code=code, qty=1, is_kit=False))
                continue
        return items

    def _format_items_for_discord(self, items: List[OrderCreateItem]) -> str:
        try:
            if not items:
                return ""
            codes = sorted({int(i.code) for i in items})
            name_by_code: Dict[int, str] = {}

            import sqlite3

            if os.path.exists(self.ssm_db_path):
                with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                    placeholders = ",".join(["?"] * len(codes))
                    cur = conn.execute(
                        f"""
                        SELECT code, COALESCE(NULLIF(display_name, ''), setup) AS name
                        FROM shop_catalog
                        WHERE code IN ({placeholders})
                        """,
                        tuple(codes),
                    )
                    for code, name in cur.fetchall():
                        name_by_code[int(code)] = str(name)

            parts: List[str] = []
            for it in items:
                code = int(it.code)
                qty = int(it.qty)
                label = name_by_code.get(code, str(code))
                parts.append(f"{label} x{qty}")

            return " | ".join(parts)
        except Exception:
            return " | ".join([f"{int(i.code)}x{int(i.qty)}" for i in items])

    def _handle_buy_command(self, steam_id: str, player: str, message_text: str, command_id: str) -> None:
        try:
            # Verificar se o jogador está preso
            try:
                from app.extensions import get_services
                svc = get_services()
                if getattr(svc, 'squad_tk_jail_service', None) and svc.squad_tk_jail_service.is_player_jailed(steam_id):
                    from core.rcon_queue_manager import RconQueueManager
                    rcon_q = RconQueueManager.get_instance()
                    chat_color = int(svc.squad_tk_jail_service.warning_color) if (svc.squad_tk_jail_service.warning_color.isdigit() and svc.squad_tk_jail_service.use_colors) else 7
                    rcon_q.enqueue_command(f'SendChat {chat_color} "Você não pode comprar itens na loja enquanto estiver preso!" {steam_id}', priority=20)
                    return
            except Exception as jail_check_err:
                self.logger.error(f"Erro ao verificar se jogador está preso no /buy: {jail_check_err}")

            items = self._parse_buy_items(message_text)
            if not items:
                if str(message_text).strip().lower().startswith("/kit"):
                    self._send_shop_log_message(
                        f"**{player}** : Usage: /kit <code> [<code> ...]"
                    )
                else:
                    self._send_shop_log_message(
                        f"**{player}** : Usage: /buy <code>x<qty> [<code>x<qty> ...]"
                    )
                return

            items_text = self._format_items_for_discord(items)

            # Enfileirar job persistido (processamento feito pelo ShopBuyJobWorker)
            job_id = uuid.uuid4().hex
            idempotency_key = compute_idempotency_key(command_id or f"buy:{steam_id}:{message_text}")

            ok, reason = self.buy_job_enqueuer.enqueue_buy_job(
                job_id=job_id,
                idempotency_key=idempotency_key,
                steam_id=steam_id,
                player_name=player,
                items=items,
                items_text=items_text,
            )

            if not ok and reason == "PLAYER_QUEUE_LIMIT":
                self._send_shop_log_message(
                    "\n".join(
                        [
                            f"**{player}** : You already have 5 orders in the queue. Please wait.",
                            f"Order: {items_text}" if items_text else "",
                        ]
                    ).strip()
                )
                return

            if not ok and reason == "DUPLICATE":
                self._send_shop_log_message(
                    "\n".join(
                        [
                            f"**{player}** : Order already received and is in the queue.",
                            f"Order: {items_text}" if items_text else "",
                        ]
                    ).strip()
                )
                return

            if not ok:
                self._send_shop_log_message(
                    "\n".join(
                        [
                            f"**{player}** : Error receiving order.",
                        ]
                    ).strip()
                )
                return

            item_lines: List[str] = []
            try:
                parts = [p.strip() for p in str(items_text or "").split("|") if p.strip()]
                item_lines = [f"- {p}" for p in parts]
            except Exception:
                item_lines = []

            self._send_shop_log_message(
                "```text\n"
                + "\n".join(
                    [
                        f"APP | {player}",
                        "================================================",
                        f"ORDER ID: {job_id}",
                        "------------------------------------------------",
                        "ITEMS:",
                        *item_lines,
                        "------------------------------------------------",
                        "STATUS: Waiting for processing",
                        "================================================",
                    ]
                )
                + "\n```"
            )
        except Exception as e:
            self.logger.error(f"Erro ao enfileirar comando /buy: {e}")
            self._send_shop_log_message(f"**{player}** : Error receiving order.")

    def _handle_tm_command(self, player: str):
        """Executar ação específica do comando /tm"""
        try:
            self.logger.info(f"Executando ação do comando /tm para jogador: {player}")

            # 1. Consultar API para obter horário do servidor
            server_time = self._get_server_time()
            if not server_time:
                self.logger.error("Falha ao obter horário do servidor")
                return

            # 2. Criar notificação usando template
            self._create_time_notification(server_time, player)

        except Exception as e:
            self.logger.error(f"Erro ao executar comando /tm: {e}")

    def _get_server_time(self) -> str:
        """Obter horário do servidor via API com precisão configurável"""
        try:
            api_url = "http://localhost:3000/api/weather/time"
            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    server_time = data['data'].get('server_time')
                    if server_time:
                        # Aplicar offset de precisão se configurado
                        adjusted_time = self._apply_time_precision_offset(server_time)
                        if adjusted_time != server_time:
                            self.logger.info(f"Horário do servidor obtido via API: {server_time} -> {adjusted_time} (offset aplicado)")
                        else:
                            self.logger.info(f"Horário do servidor obtido via API: {server_time}")
                        return adjusted_time
                    else:
                        self.logger.error("Campo server_time não encontrado na resposta da API")
                else:
                    self.logger.error(f"API retornou erro: {data.get('error', 'Erro desconhecido')}")
            else:
                self.logger.error(f"Erro HTTP ao consultar API: {response.status_code}")

            # Fallback: consultar diretamente o banco SCUM.db
            try:
                from utils.restart_guard import should_block_scum_db_access

                if should_block_scum_db_access(
                    component="ChatCommandMonitor",
                    operation="get_server_time_direct_fallback",
                    scum_db_path=self.scum_db_path,
                ):
                    return None
            except Exception:
                pass
            return self._get_server_time_direct()

        except Exception as e:
            self.logger.error(f"Erro ao consultar API de horário: {e}")
            # Fallback: consultar diretamente o banco SCUM.db
            try:
                from utils.restart_guard import should_block_scum_db_access

                if should_block_scum_db_access(
                    component="ChatCommandMonitor",
                    operation="get_server_time_direct_fallback_exception",
                    scum_db_path=self.scum_db_path,
                ):
                    return None
            except Exception:
                pass
            return self._get_server_time_direct()

    def _get_server_time_direct(self) -> str:
        """Obter horário do servidor diretamente do banco SCUM.db com precisão configurável"""
        try:
            try:
                from utils.restart_guard import should_block_scum_db_access

                if should_block_scum_db_access(
                    component="ChatCommandMonitor",
                    operation="get_server_time_direct",
                    scum_db_path=self.scum_db_path,
                ):
                    return None
            except Exception:
                pass


            if not self.scum_db_path or not os.path.exists(self.scum_db_path):
                self.logger.error(f"Banco SCUM.db não encontrado: {self.scum_db_path}")
                return None

            from utils.scum_db_helper import scum_db_readonly_connection_strict

            with scum_db_readonly_connection_strict(self.scum_db_path) as conn:
                cursor = conn.cursor()

                # Buscar dados da tabela weather_parameters
                cursor.execute(
                    "SELECT value FROM weather_parameters WHERE name = 'TimeOfDay'"
                )

                weather_data = cursor.fetchone()

                if not weather_data:
                    self.logger.error("Nenhum dado climático encontrado no SCUM.db")
                    return None

                # Converter time_of_day para formato legível
                time_of_day = weather_data[0]
                hours = int(time_of_day)
                minutes = int((time_of_day - hours) * 60)

                # Aplicar offset de precisão se configurado
                offset_minutes = self._get_time_precision_offset()
                if offset_minutes > 0:
                    # Converter para datetime para facilitar cálculos
                    base_time = datetime.now().replace(hour=hours, minute=minutes, second=0, microsecond=0)
                    adjusted_time = base_time + timedelta(minutes=offset_minutes)
                    hours = adjusted_time.hour
                    minutes = adjusted_time.minute
                    self.logger.info(f"Aplicando offset de precisão: +{offset_minutes} minutos")

                server_time = f"{hours:02d}:{minutes:02d}"

                self.logger.info(f"Horário do servidor obtido diretamente do banco: {server_time} (time_of_day: {time_of_day}, offset: +{offset_minutes}min)")
                return server_time

        except Exception as e:
            self.logger.error(f"Erro ao acessar banco SCUM diretamente: {e}")
            return None

    def _create_time_notification(self, server_time: str, player: str):
        """Criar notificação de horário usando template"""
        try:
            # Carregar template
            template_path = "data/notifications/templates/time_notification.json"
            if not os.path.exists(template_path):
                self.logger.error(f"Template não encontrado: {template_path}")
                return

            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)

            # Obter configuração da notificação
            notification_config = template.get('notifications', [{}])[0]

            # Substituir {server_time} pelo horário real
            message = notification_config.get('message', '{server_time}').replace('{server_time}', server_time)
            duration = notification_config.get('duration', 15)
            color = notification_config.get('color', '255-255-255')

            # Calcular horário da notificação (atual + 2 minutos)
            now = datetime.now()
            notification_time = now + timedelta(minutes=2)
            time_str = notification_time.strftime("%H:%M")

            # Criar notificação
            notification = {
                "day": "Everyday",
                "time": [time_str],
                "duration": duration,
                "color": color,
                "message": message
            }

            # Salvar no arquivo Notifications.json do SCUM
            self._save_notification_to_scum(notification)

            self.logger.info(f"Notificação de horário criada: {message} para {time_str}")

        except Exception as e:
            self.logger.error(f"Erro ao criar notificação de horário: {e}")

    def _save_notification_to_scum(self, notification: dict):
        """Salvar notificação no arquivo Notifications.json do SCUM"""
        try:
            scum_path = "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\Notifications.json"

            # Criar diretório se não existir
            os.makedirs(os.path.dirname(scum_path), exist_ok=True)

            # Carregar notificações existentes ou criar novo
            if os.path.exists(scum_path):
                with open(scum_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"Notifications": []}

            # Adicionar nova notificação
            data["Notifications"].append(notification)

            # Salvar arquivo
            with open(scum_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Notificação salva em: {scum_path}")

        except Exception as e:
            self.logger.error(f"Erro ao salvar notificação no SCUM: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Obter status do monitor"""
        return {
            "is_running": self.is_running,
            "processed_files": len(self.processed_files),
            "processed_commands": len(self.processed_commands),
            "commands_webhook_configured": bool(self.commands_webhook),
            "monitored_commands": list(self.command_patterns.keys()),
            "last_check_time": self.last_check_time
        }

    def clear_old_commands(self, max_age_hours: int = 24):
        """Limpar comandos antigos do arquivo JSON"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            # Carregar dados atuais
            if os.path.exists(self.processed_commands_file):
                with open(self.processed_commands_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Filtrar comandos antigos (baseado no timestamp)
                old_commands = []
                for command_id in list(self.processed_commands):
                    try:
                        # Extrair timestamp do command_id (formato: timestamp:player:command:file:line)
                        timestamp_str = command_id.split(':')[0]
                        # Converter timestamp para verificar idade (se estiver no formato esperado)
                        # Assumindo formato: 2025.10.26-03.19.53
                        if not timestamp_str or "-" not in timestamp_str:
                            continue
                        dt = datetime.strptime(timestamp_str, "%Y.%m.%d-%H.%M.%S")
                        command_time = dt.timestamp()

                        if current_time - command_time > max_age_seconds:
                            old_commands.append(command_id)
                    except Exception:
                        continue

                # Remover comandos antigos
                for old_command in old_commands:
                    self.processed_commands.discard(old_command)

                if old_commands:
                    self._save_processed_commands()
                    self.logger.info(f"Removidos {len(old_commands)} comandos antigos")
                    
        except Exception as e:
            self.logger.error(f"Erro ao limpar comandos antigos: {e}")

    def _get_attribute_upgrade_price(self, attribute_name: str, level: int) -> int:
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT price 
                    FROM attribute_upgrade_prices 
                    WHERE attribute_name = ? AND level = ?
                    """,
                    (str(attribute_name), int(level))
                )
                row = cursor.fetchone()
                if row is not None:
                    price = int(row[0])
                    self.logger.info(f"[Upgrade Price] Preço encontrado no banco para {attribute_name} Lvl {level}: {price} (Banco: {self.ssm_db_path})")
                    return price
                else:
                    self.logger.warning(f"[Upgrade Price] Nenhum preço cadastrado no banco para {attribute_name} Lvl {level}. Retornando 0 (Desativado).")
        except Exception as e:
            self.logger.error(f"[Upgrade Price] Erro ao buscar preço de atributo {attribute_name} Lvl {level} no banco de dados (Banco: {self.ssm_db_path}): {e}")

        # Retornar 0 se o banco falhar ou se o preço não for encontrado
        return 0

    def _handle_attr_upgrade_command(
        self, steam_id: str, player: str, message_text: str, command_id: str
    ) -> None:
        try:
            if not steam_id:
                return

            # Verificar se o jogador está preso
            try:
                from app.extensions import get_services
                svc = get_services()
                if getattr(svc, 'squad_tk_jail_service', None) and svc.squad_tk_jail_service.is_player_jailed(steam_id):
                    from utils.rcon_client import get_rcon_client_from_config
                    rcon_client = get_rcon_client_from_config()
                    if rcon_client:
                        with rcon_client as rcon:
                            msg_error = "Você não pode comprar upgrades de atributos enquanto estiver preso!"
                            rcon.send_command(f'SendChat 7 "{msg_error}" {steam_id}')
                    return
            except Exception as jail_check_err:
                self.logger.error(f"Erro ao verificar se jogador está preso no upgrade de atributos: {jail_check_err}")

            m = re.search(r'/([fcdi])([1-8])\b', message_text, flags=re.IGNORECASE)
            if not m:
                return
            attr_char = m.group(1).lower()
            target_level = int(m.group(2))

            attr_map = {
                'f': 'strength',
                'c': 'constitution',
                'd': 'dexterity',
                'i': 'intelligence'
            }
            attribute_name = attr_map[attr_char]

            max_level = 8 if attribute_name == 'strength' else 5
            if target_level < 1 or target_level > max_level:
                return

            price = self._get_attribute_upgrade_price(attribute_name, target_level)

            # Verificar se o upgrade está desativado (preço <= 0)
            if price <= 0:
                from utils.rcon_client import get_rcon_client_from_config
                rcon_client = get_rcon_client_from_config()
                if rcon_client:
                    with rcon_client as rcon:
                        msg_error = f"Upgrade de {attribute_name.capitalize()} Lvl {target_level} esta temporariamente desativado."
                        rcon.send_command(f'SendChat 7 "{msg_error}" {steam_id}')
                
                # Logar recusa no Discord
                self._send_shop_log_message(
                    "```text\n"
                    + "\n".join(
                        [
                            f"APP | {player} ({steam_id})",
                            "================================================",
                            "ATTRIBUTE UPGRADE (DENIED - DISABLED)",
                            "------------------------------------------------",
                            f"ATTRIBUTE: {attribute_name.capitalize()}",
                            f"TARGET LEVEL: {target_level}",
                            "------------------------------------------------",
                            "STATUS: Upgrade is currently disabled by Admin (Price = 0)",
                            "================================================",
                        ]
                    )
                    + "\n```"
                )
                return

            from core.shop.wallet_service import WalletService
            wallet = WalletService(self.ssm_db_path, logger=self.logger)
            current_balance = wallet.get_balance(steam_id)

            from utils.rcon_client import get_rcon_client_from_config
            rcon_client = get_rcon_client_from_config()
            if not rcon_client:
                self.logger.error("RCON não está disponível para upgrade de atributo.")
                return

            with rcon_client as rcon:
                if current_balance < price:
                    def get_unit(val):
                        if val < 100: return "Teeth"
                        if val < 1000: return "Ears"
                        return "Heads"
                    cost_unit = get_unit(price)
                    bal_unit = get_unit(current_balance)
                    msg_error = f"Saldo insuficiente! Custo: {price} {cost_unit} | Seu Saldo: {current_balance} {bal_unit}"
                    rcon.send_command(f'SendChat 7 "{msg_error}" {steam_id}')
                    
                    # Logar no Discord (Saldo Insuficiente)
                    self._send_shop_log_message(
                        "```text\n"
                        + "\n".join(
                            [
                                f"APP | {player} ({steam_id})",
                                "================================================",
                                "ATTRIBUTE UPGRADE (DENIED)",
                                "------------------------------------------------",
                                f"ATTRIBUTE: {attribute_name.capitalize()}",
                                f"TARGET LEVEL: {target_level}",
                                f"COST: {price}",
                                f"CURRENT BALANCE: {current_balance}",
                                "------------------------------------------------",
                                "STATUS: Insufficient Funds",
                                "================================================",
                            ]
                        )
                        + "\n```"
                    )
                    return

                from utils.scum_db_helper import scum_db_readonly_connection
                from utils.scum_attributes_editor import (
                    resolve_prisoner_identifier,
                    get_prisoner_attributes,
                    apply_attribute_and_skills_via_rcon
                )

                with scum_db_readonly_connection(self.scum_db_path) as scum_conn:
                    scum_cursor = scum_conn.cursor()
                    ident_info = resolve_prisoner_identifier(scum_cursor, steam_id)
                    if not ident_info:
                        msg_error = "Erro ao identificar prisioneiro no banco de dados do jogo."
                        rcon.send_command(f'SendChat 7 "{msg_error}" {steam_id}')
                        return
                    prisoner_id = ident_info["prisoner_id"]
                    current_attrs = get_prisoner_attributes(scum_cursor, prisoner_id)
                    if current_attrs is None:
                        current_attrs = {
                            "strength": 3.0,
                            "constitution": 3.0,
                            "dexterity": 3.0,
                            "intelligence": 3.0
                        }

                    # Buscar do SSM.db (player_attributes_cache) para mesclar com SCUM.db (evitar dados obsoletos)
                    cached_attrs = {}
                    cached_prisoner_id = None
                    try:
                        from core.database.connector import DatabaseConnector
                        with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                SELECT strength, constitution, dexterity, intelligence, prisoner_id 
                                FROM player_attributes_cache 
                                WHERE steam_id = ?
                                """,
                                (steam_id,)
                            )
                            row = cursor.fetchone()
                            if row:
                                cached_attrs = {
                                    "strength": float(row[0]) if row[0] is not None else 0.0,
                                    "constitution": float(row[1]) if row[1] is not None else 0.0,
                                    "dexterity": float(row[2]) if row[2] is not None else 0.0,
                                    "intelligence": float(row[3]) if row[3] is not None else 0.0,
                                }
                                cached_prisoner_id = row[4]
                    except Exception as e:
                        self.logger.error(f"Erro ao ler cache de atributos: {e}")

                    # Mesclar as duas leituras usando o maior valor para cada atributo,
                    # apenas se for o mesmo prisioneiro (evita herdar lixo de personagem deletado)
                    if cached_prisoner_id is not None and cached_prisoner_id == prisoner_id:
                        for attr in ["strength", "constitution", "dexterity", "intelligence"]:
                            db_val = current_attrs.get(attr, 3.0)
                            cache_val = cached_attrs.get(attr, 0.0)
                            current_attrs[attr] = max(db_val, cache_val)

                # Debitar saldo
                try:
                    wallet.apply_delta(
                        steam_id=steam_id,
                        delta=-price,
                        reason=f"upgrade_{attribute_name}_{target_level}",
                        ref_type="chat_command",
                        ref_id=command_id,
                        meta={
                            "player": player,
                            "attribute": attribute_name,
                            "level": target_level,
                            "price": price
                        }
                    )
                except ValueError:
                    msg_error = "Erro no saldo. Saldo insuficiente!"
                    rcon.send_command(f'SendChat 7 "{msg_error}" {steam_id}')
                    return

                # Aplicar via RCON
                ok, rcon_msg = apply_attribute_and_skills_via_rcon(
                    rcon,
                    steam_id,
                    attribute_name,
                    float(target_level),
                    current_attrs
                )

                if ok:
                    # Atualizar o cache de atributos no SSM.db e salvar validade temporária
                    try:
                        from datetime import datetime, timedelta
                        original_val = float(current_attrs.get(attribute_name, 3.0))
                        target_val = float(target_level)
                        
                        # Atualizar current_attrs para refletir o novo valor no cache
                        current_attrs[attribute_name] = target_val
                        
                        # Buscar configurações de expiração
                        expiration_enabled = False
                        duration_days = 30
                        try:
                            from core.database.connector import DatabaseConnector
                            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT key, value FROM app_config WHERE key IN (?, ?)",
                                    ("attributes.expiration.enabled", "attributes.expiration.duration_days")
                                )
                                for k, v in cursor.fetchall():
                                    if k == "attributes.expiration.enabled":
                                        expiration_enabled = (v == "1")
                                    elif k == "attributes.expiration.duration_days" and v.isdigit():
                                        duration_days = int(v)
                        except Exception as config_err:
                            self.logger.error(f"Erro ao ler configuracao de expiracao no monitor: {config_err}")

                        inherited_original_val = original_val
                        
                        from core.database.connector import DatabaseConnector
                        if expiration_enabled:
                            # Tentar obter o valor original mais antigo de um upgrade ativo (proteção do valor base real)
                            try:
                                with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        """
                                        SELECT original_value 
                                        FROM player_attribute_upgrades 
                                        WHERE steam_id = ? AND attribute_name = ? AND status = 'active'
                                        ORDER BY created_at ASC LIMIT 1
                                        """,
                                        (steam_id, attribute_name)
                                    )
                                    row = cursor.fetchone()
                                    if row:
                                        inherited_original_val = float(row[0])
                            except Exception as db_err:
                                self.logger.error(f"Erro ao buscar upgrade ativo anterior: {db_err}")

                            expires_at = (datetime.utcnow() + timedelta(days=duration_days)).strftime("%Y-%m-%d %H:%M:%S")

                            # Transação atômica para registrar o upgrade e atualizar o cache
                            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                                cursor = conn.cursor()
                                
                                # Marcar upgrades ativos antigos como superseded
                                cursor.execute(
                                    """
                                    UPDATE player_attribute_upgrades 
                                    SET status = 'superseded' 
                                    WHERE steam_id = ? AND attribute_name = ? AND status = 'active'
                                    """,
                                    (steam_id, attribute_name)
                                )
                                
                                # Inserir novo upgrade
                                cursor.execute(
                                    """
                                    INSERT INTO player_attribute_upgrades (steam_id, attribute_name, original_value, target_value, expires_at, status)
                                    VALUES (?, ?, ?, ?, ?, 'active')
                                    """,
                                    (steam_id, attribute_name, inherited_original_val, target_val, expires_at)
                                )
                                
                                # Atualizar o cache de atributos
                                cursor.execute(
                                    """
                                    INSERT INTO player_attributes_cache (steam_id, strength, constitution, dexterity, intelligence, prisoner_id, updated_at)
                                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                                    ON CONFLICT(steam_id) DO UPDATE SET
                                        strength = excluded.strength,
                                        constitution = excluded.constitution,
                                        dexterity = excluded.dexterity,
                                        intelligence = excluded.intelligence,
                                        prisoner_id = excluded.prisoner_id,
                                        updated_at = CURRENT_TIMESTAMP
                                    """,
                                    (
                                        steam_id,
                                        current_attrs.get("strength"),
                                        current_attrs.get("constitution"),
                                        current_attrs.get("dexterity"),
                                        current_attrs.get("intelligence"),
                                        prisoner_id
                                    )
                                )
                                conn.commit()
                        else:
                            # Expiração desabilitada: apenas atualiza o cache
                            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    """
                                    INSERT INTO player_attributes_cache (steam_id, strength, constitution, dexterity, intelligence, prisoner_id, updated_at)
                                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                                    ON CONFLICT(steam_id) DO UPDATE SET
                                        strength = excluded.strength,
                                        constitution = excluded.constitution,
                                        dexterity = excluded.dexterity,
                                        intelligence = excluded.intelligence,
                                        prisoner_id = excluded.prisoner_id,
                                        updated_at = CURRENT_TIMESTAMP
                                    """,
                                    (
                                        steam_id,
                                        current_attrs.get("strength"),
                                        current_attrs.get("constitution"),
                                        current_attrs.get("dexterity"),
                                        current_attrs.get("intelligence"),
                                        prisoner_id
                                    )
                                )
                                conn.commit()

                        # Discord Logging (Embed)
                        discord_user_id = None
                        try:
                            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                                cursor = conn.cursor()
                                cursor.execute("SELECT discord_user_id FROM players WHERE steam_id = ?", (steam_id,))
                                row = cursor.fetchone()
                                if row:
                                    discord_user_id = row[0]
                        except Exception as discord_err:
                            self.logger.error(f"Erro ao buscar discord_user_id para log: {discord_err}")

                        discord_val = f"<@{discord_user_id}>" if discord_user_id else "Não registrado / Não vinculado"
                        
                        if expiration_enabled:
                            try:
                                dt_expires = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                                validade_str = f"{duration_days} dias (Expira em: {dt_expires.strftime('%d/%m/%Y às %H:%M:%S')} UTC)"
                            except Exception:
                                validade_str = f"{duration_days} dias"

                            embed = {
                                "title": "⚙️ SSM | UPGRADE TEMPORÁRIO COMPRADO",
                                "color": 0x2ECC71,  # Verde
                                "fields": [
                                    {"name": "Jogador", "value": f"{player} (`{steam_id}`)", "inline": True},
                                    {"name": "Usuário Discord", "value": discord_val, "inline": True},
                                    {"name": "Atributo", "value": attribute_name.upper(), "inline": True},
                                    {"name": "Custo", "value": f"{price} Pontos", "inline": True},
                                    {"name": "Nível Anterior (Base)", "value": f"{inherited_original_val:.1f}", "inline": True},
                                    {"name": "Novo Nível", "value": f"{target_val:.1f}", "inline": True},
                                    {"name": "Duração / Validade", "value": validade_str, "inline": False}
                                ],
                                "timestamp": datetime.utcnow().isoformat() + "Z"
                            }
                        else:
                            embed = {
                                "title": "⚙️ SSM | UPGRADE DE ATRIBUTO COMPRADO (PERMANENTE)",
                                "color": 0x3498DB,  # Azul
                                "fields": [
                                    {"name": "Jogador", "value": f"{player} (`{steam_id}`)", "inline": True},
                                    {"name": "Usuário Discord", "value": discord_val, "inline": True},
                                    {"name": "Atributo", "value": attribute_name.upper(), "inline": True},
                                    {"name": "Custo", "value": f"{price} Pontos", "inline": True},
                                    {"name": "Nível Anterior", "value": f"{original_val:.1f}", "inline": True},
                                    {"name": "Novo Nível", "value": f"{target_val:.1f}", "inline": True}
                                ],
                                "timestamp": datetime.utcnow().isoformat() + "Z"
                            }
                        self._send_shop_log_embed(embed=embed)

                    except Exception as e:
                        self.logger.error(f"Erro ao processar logs e persistência pós-upgrade: {e}")
                else:
                    # Estornar
                    wallet.apply_delta(
                        steam_id=steam_id,
                        delta=price,
                        reason=f"refund_{attribute_name}_{target_level}",
                        ref_type="chat_command",
                        ref_id=f"refund_{command_id}"
                    )
                    rcon.send_command(f'SendChat 7 "{rcon_msg}" {steam_id}')
                    
                    # Logar no Discord (Falha RCON com estorno)
                    self._send_shop_log_message(
                        "```text\n"
                        + "\n".join(
                            [
                                f"APP | {player} ({steam_id})",
                                "================================================",
                                "ATTRIBUTE UPGRADE (FAILED)",
                                "------------------------------------------------",
                                f"ATTRIBUTE: {attribute_name.capitalize()}",
                                f"TARGET LEVEL: {target_level}",
                                f"COST: {price} (Refunded)",
                                "------------------------------------------------",
                                f"RCON ERROR: {rcon_msg}",
                                "================================================",
                            ]
                        )
                        + "\n```"
                    )
                    return

                msg_success = f"Upar {attribute_name.capitalize()} para {target_level} efetuado com sucesso!"
                rcon.send_command(f'SendChat 6 "{msg_success}" {steam_id}')

                # Logar no Discord (Sucesso)
                self._send_shop_log_message(
                    "```text\n"
                    + "\n".join(
                        [
                            f"APP | {player} ({steam_id})",
                            "================================================",
                            "ATTRIBUTE UPGRADE",
                            "------------------------------------------------",
                            f"ATTRIBUTE: {attribute_name.capitalize()}",
                            f"TARGET LEVEL: {target_level}",
                            f"COST: {price}",
                            f"REMAINING BALANCE: {current_balance - price}",
                            "------------------------------------------------",
                            "STATUS: Upgrade successfully applied via RCON",
                            "================================================",
                        ]
                    )
                    + "\n```"
                )

        except Exception as e:
            self.logger.error(f"Erro ao processar upgrade de atributo chat command: {e}")

    def _handle_sd_command(self, steam_id: str, player: str) -> None:
        try:
            if not steam_id:
                return

            from core.shop.wallet_service import WalletService
            wallet = WalletService(self.ssm_db_path, logger=self.logger)
            current_balance = wallet.get_balance(steam_id)

            if current_balance < 100:
                unit = "Teeth"
            elif current_balance < 1000:
                unit = "Ears"
            else:
                unit = "Heads"

            from utils.rcon_client import get_rcon_client_from_config
            rcon_client = get_rcon_client_from_config()
            if not rcon_client:
                self.logger.error("RCON não está disponível para consultar saldo.")
                return

            message = f"[SSM] Your current balance: {current_balance} {unit}"

            with rcon_client as rcon:
                rcon.send_command(f'SendChat 6 "{message}" {steam_id}')

        except Exception as e:
            self.logger.error(f"Erro ao processar comando /sd: {e}")

    def _handle_rd_command(self, steam_id: str, player: str, message_text: str) -> None:
        try:
            if not steam_id:
                return

            from utils.rcon_client import get_rcon_client_from_config
            rcon_client = get_rcon_client_from_config()
            if not rcon_client:
                self.logger.error("RCON não está disponível para gerenciar webhook pessoal.")
                return

            # 1. Carregar Configurações
            config_path = str(self.data_dir / "config.json")
            config = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                except Exception as e:
                    self.logger.error(f"Erro ao ler config.json: {e}")

            pw_cfg = config.get("personal_webhooks", {})
            enabled = pw_cfg.get("enabled", True)
            price_points = pw_cfg.get("price_points", 500)
            duration_days = pw_cfg.get("duration_days", 30)

            # Mensagens padrão
            default_msgs = {
                "system_disabled": "[SSM] O sistema de webhook pessoal de raid esta desativado neste servidor.",
                "usage_help": "[SSM] Uso correto: /rd <url> ou /rd off. Para ver detalhes digite: /rd info",
                "no_permission": "[SSM] Voce nao tem permissao para gerenciar webhook pessoal.",
                "insufficient_funds": "[SSM] Saldo insuficiente. Para cadastrar o webhook sao necessarios {price} pontos. Seu saldo: {balance}.",
                "disabled_success": "[SSM] Webhook desativado. Sua assinatura continua valida ate {expires_at}.",
                "disabled_success_lifetime": "[SSM] Webhook pessoal desativado com sucesso.",
                "registered_success": "[SSM] Webhook cadastrado por {days} dias! Validade: {expires_at}. Descontado {price} pontos.",
                "registered_success_lifetime": "[SSM] Webhook pessoal cadastrado com sucesso (Plano Vitalicio)!",
                "updated_success": "[SSM] Webhook atualizado com sucesso! Validade: {expires_at}.",
                "updated_success_lifetime": "[SSM] Webhook pessoal atualizado com sucesso!",
                "renewed_success": "[SSM] Assinatura estendida por mais {days} dias! Nova validade: {expires_at}. Descontado {price} pontos.",
                "status_info": "[SSM] Webhook: {url} | Validade da assinatura: {expires_at} {remaining}.",
                "status_expired": "[SSM] Webhook: {url} | Assinatura EXPIRADA em: {expires_at}.",
                "status_no_subscription": "[SSM] Voce nao possui uma assinatura de webhook pessoal ativa.",
                "invalid_webhook": "[SSM] URL de webhook invalida. Use uma URL do Discord valida.",
                "database_error": "[SSM] Erro interno ao salvar as configuracoes do webhook."
            }

            msgs = pw_cfg.get("messages", {})
            for k, v in default_msgs.items():
                if k not in msgs:
                    msgs[k] = v

            # Verificar se está ativado
            if not enabled:
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 7 "{msgs["system_disabled"]}" {steam_id}')
                return

            # Verificar permissão 'raid_webhook_manage' (bloqueado se is_active = 0)
            is_blocked = False
            try:
                with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT is_active FROM player_permissions WHERE steam_id = ? AND permission_type = 'raid_webhook_manage' LIMIT 1",
                        (steam_id,)
                    )
                    row = cursor.fetchone()
                    if row is not None and row[0] == 0:
                        is_blocked = True
            except Exception as e:
                self.logger.error(f"Erro ao verificar permissão do jogador para webhook pessoal: {e}")

            if is_blocked:
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 7 "{msgs["no_permission"]}" {steam_id}')
                return

            # Parsear argumento
            tokens = str(message_text or "").strip().split()
            if len(tokens) < 2:
                self._show_rd_status(steam_id, rcon_client, msgs)
                return

            arg = tokens[1].strip()

            # Comando: /rd info ou /rd status
            if arg.lower() in ("info", "status"):
                self._show_rd_status(steam_id, rcon_client, msgs)
                return

            # Comando: /rd renew
            if arg.lower() == "renew":
                self._handle_rd_renew(steam_id, rcon_client, msgs, price_points, duration_days)
                return

            # Comando: /rd off
            if arg.lower() == "off":
                self._handle_rd_off(steam_id, rcon_client, msgs, duration_days)
                return

            # Cadastrar / Atualizar Webhook
            self._handle_rd_register(steam_id, rcon_client, msgs, arg, price_points, duration_days)

        except Exception as e:
            self.logger.error(f"Erro no handler do comando /rd: {e}")

    def _show_rd_status(self, steam_id: str, rcon_client: Any, msgs: Dict[str, str]) -> None:
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT webhook_url, expires_at FROM player_webhooks WHERE steam_id = ?",
                    (steam_id,)
                )
                row = cursor.fetchone()

            if not row:
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 7 "{msgs["status_no_subscription"]}" {steam_id}')
                return

            url, expires_at = row
            url_display = url if url else "OFF"

            # Se expires_at for nulo, é vitalício
            if not expires_at:
                msg = msgs["status_info"].format(url=url_display, expires_at="Vitalicia", remaining="")
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 6 "{msg}" {steam_id}')
                return

            # Verificar se expirou
            from datetime import datetime
            clean_str = expires_at.split(".")[0].replace("Z", "").replace("T", " ")
            dt_expires = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.utcnow()

            # Formatar data de exibição
            dt_display = dt_expires.strftime("%d/%m/%Y %H:%M")

            if dt_expires <= now:
                msg = msgs["status_expired"].format(url=url_display, expires_at=dt_display)
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 7 "{msg}" {steam_id}')
            else:
                remaining = self._get_remaining_time_desc(expires_at)
                msg = msgs["status_info"].format(url=url_display, expires_at=dt_display, remaining=remaining)
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 6 "{msg}" {steam_id}')

        except Exception as e:
            self.logger.error(f"Erro ao exibir status do webhook: {e}")
            with rcon_client as rcon:
                rcon.send_command(f'SendChat 7 "{msgs["database_error"]}" {steam_id}')

    def _get_remaining_time_desc(self, expires_str: Optional[str]) -> str:
        if not expires_str:
            return ""
        try:
            from datetime import datetime
            clean_str = expires_str.split(".")[0].replace("Z", "").replace("T", " ")
            dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.utcnow()
            diff = dt - now
            if diff.total_seconds() <= 0:
                return "Expirado"
            days = diff.days
            hours = diff.seconds // 3600
            if days > 0:
                return f"(Restam {days}d e {hours}h)"
            else:
                minutes = (diff.seconds % 3600) // 60
                return f"(Restam {hours}h e {minutes}m)"
        except Exception:
            return ""

    def _handle_rd_off(self, steam_id: str, rcon_client: Any, msgs: Dict[str, str], duration_days: int) -> None:
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT expires_at FROM player_webhooks WHERE steam_id = ?",
                    (steam_id,)
                )
                row = cursor.fetchone()

                if not row:
                    with rcon_client as rcon:
                        rcon.send_command(f'SendChat 7 "{msgs["status_no_subscription"]}" {steam_id}')
                    return

                expires_at = row[0]
                cursor.execute(
                    "UPDATE player_webhooks SET webhook_url = '', updated_at = CURRENT_TIMESTAMP WHERE steam_id = ?",
                    (steam_id,)
                )
                conn.commit()

            # Responder de acordo com a validade
            if duration_days <= 0 or not expires_at:
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 6 "{msgs["disabled_success_lifetime"]}" {steam_id}')
            else:
                from datetime import datetime
                clean_str = expires_at.split(".")[0].replace("Z", "").replace("T", " ")
                dt_expires = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
                dt_display = dt_expires.strftime("%d/%m/%Y %H:%M")
                msg = msgs["disabled_success"].format(expires_at=dt_display)
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 6 "{msg}" {steam_id}')

        except Exception as e:
            self.logger.error(f"Erro ao desativar webhook: {e}")
            with rcon_client as rcon:
                rcon.send_command(f'SendChat 7 "{msgs["database_error"]}" {steam_id}')

    def _handle_rd_renew(self, steam_id: str, rcon_client: Any, msgs: Dict[str, str], price_points: int, duration_days: int) -> None:
        try:
            # Se for vitalício, não há necessidade de renovar
            if duration_days <= 0:
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 6 "[SSM] Seu plano ja eh vitalicio. Nao eh necessario renovar." {steam_id}')
                return

            wallet = WalletService(self.ssm_db_path, logger=self.logger)
            balance = wallet.get_balance(steam_id)

            if balance < price_points:
                msg = msgs["insufficient_funds"].format(price=price_points, balance=balance)
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 7 "{msg}" {steam_id}')
                return

            # Obter expiração atual
            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT expires_at FROM player_webhooks WHERE steam_id = ?",
                    (steam_id,)
                )
                row = cursor.fetchone()

            from datetime import datetime, timedelta
            now = datetime.utcnow()
            current_expires_at = None

            if row and row[0]:
                try:
                    clean_str = row[0].split(".")[0].replace("Z", "").replace("T", " ")
                    dt_expires = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
                    if dt_expires > now:
                        current_expires_at = dt_expires
                except Exception:
                    pass

            if current_expires_at:
                new_expires_dt = current_expires_at + timedelta(days=duration_days)
            else:
                new_expires_dt = now + timedelta(days=duration_days)

            new_expires_str = new_expires_dt.strftime("%Y-%m-%d %H:%M:%S")

            # Cobrar pontos
            try:
                wallet.apply_delta(
                    steam_id=steam_id,
                    delta=-price_points,
                    reason="personal_webhook_registration",
                    ref_type="webhook",
                    ref_id=str(uuid.uuid4()),
                    allow_negative=False
                )
            except Exception as e:
                self.logger.error(f"Erro ao cobrar pontos para renovacao: {e}")
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 7 "{msgs["insufficient_funds"].format(price=price_points, balance=balance)}" {steam_id}')
                return

            # Atualizar banco
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                conn.execute(
                    """
                    INSERT INTO player_webhooks (steam_id, webhook_url, expires_at, warned_3d, warned_1d, created_at, updated_at)
                    VALUES (?, '', ?, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(steam_id) DO UPDATE SET
                        expires_at = excluded.expires_at,
                        warned_3d = 0,
                        warned_1d = 0,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (steam_id, new_expires_str)
                )
                conn.commit()

            dt_display = new_expires_dt.strftime("%d/%m/%Y %H:%M")
            msg = msgs["renewed_success"].format(days=duration_days, expires_at=dt_display, price=price_points)
            with rcon_client as rcon:
                rcon.send_command(f'SendChat 6 "{msg}" {steam_id}')

        except Exception as e:
            self.logger.error(f"Erro ao renovar webhook: {e}")
            with rcon_client as rcon:
                rcon.send_command(f'SendChat 7 "{msgs["database_error"]}" {steam_id}')

    def _handle_rd_register(self, steam_id: str, rcon_client: Any, msgs: Dict[str, str], url: str, price_points: int, duration_days: int) -> None:
        try:
            # Validar URL de webhook
            discord_webhook_pattern = r"^https:\/\/(?:ptb\.|canary\.)?discord(?:app)?\.com\/api\/webhooks\/\d+\/[A-Za-z0-9\-_]+$"
            if not re.match(discord_webhook_pattern, url):
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 7 "{msgs["invalid_webhook"]}" {steam_id}')
                return

            # Verificar se já possui assinatura ativa
            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT expires_at FROM player_webhooks WHERE steam_id = ?",
                    (steam_id,)
                )
                row = cursor.fetchone()

            from datetime import datetime, timedelta
            now = datetime.utcnow()
            has_active_subscription = False
            current_expires_at = None

            if duration_days <= 0:
                has_active_subscription = True
            elif row and row[0]:
                try:
                    clean_str = row[0].split(".")[0].replace("Z", "").replace("T", " ")
                    dt_expires = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
                    if dt_expires > now:
                        has_active_subscription = True
                        current_expires_at = dt_expires
                except Exception:
                    pass

            # Caso 1: Já possui assinatura ativa -> Apenas atualiza a URL de graça
            if has_active_subscription:
                with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                    conn.execute(
                        """
                        INSERT INTO player_webhooks (steam_id, webhook_url, expires_at, warned_3d, warned_1d, created_at, updated_at)
                        VALUES (?, ?, ?, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT(steam_id) DO UPDATE SET
                            webhook_url = excluded.webhook_url,
                            warned_3d = 0,
                            warned_1d = 0,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (steam_id, url, current_expires_at.strftime("%Y-%m-%d %H:%M:%S") if current_expires_at else None)
                    )
                    conn.commit()

                if duration_days <= 0 or not current_expires_at:
                    msg = msgs["updated_success_lifetime"]
                else:
                    msg = msgs["updated_success"].format(expires_at=current_expires_at.strftime("%d/%m/%Y %H:%M"))
                
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 6 "{msg}" {steam_id}')
                return

            # Caso 2: Não possui assinatura ou expirou -> Precisa pagar
            wallet = WalletService(self.ssm_db_path, logger=self.logger)
            balance = wallet.get_balance(steam_id)

            if price_points > 0 and balance < price_points:
                msg = msgs["insufficient_funds"].format(price=price_points, balance=balance)
                with rcon_client as rcon:
                    rcon.send_command(f'SendChat 7 "{msg}" {steam_id}')
                return

            # Cobrar pontos se preço for maior que 0
            if price_points > 0:
                try:
                    wallet.apply_delta(
                        steam_id=steam_id,
                        delta=-price_points,
                        reason="personal_webhook_registration",
                        ref_type="webhook",
                        ref_id=str(uuid.uuid4()),
                        allow_negative=False
                    )
                except Exception as e:
                    self.logger.error(f"Erro ao cobrar pontos para cadastro: {e}")
                    with rcon_client as rcon:
                        rcon.send_command(f'SendChat 7 "{msgs["insufficient_funds"].format(price=price_points, balance=balance)}" {steam_id}')
                    return

            # Calcular nova expiração
            new_expires_dt = now + timedelta(days=duration_days)
            new_expires_str = new_expires_dt.strftime("%Y-%m-%d %H:%M:%S")

            # Salvar no banco
            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                conn.execute(
                    """
                    INSERT INTO player_webhooks (steam_id, webhook_url, expires_at, warned_3d, warned_1d, created_at, updated_at)
                    VALUES (?, ?, ?, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(steam_id) DO UPDATE SET
                        webhook_url = excluded.webhook_url,
                        expires_at = excluded.expires_at,
                        warned_3d = 0,
                        warned_1d = 0,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (steam_id, url, new_expires_str)
                )
                conn.commit()

            dt_display = new_expires_dt.strftime("%d/%m/%Y %H:%M")
            msg = msgs["registered_success"].format(days=duration_days, expires_at=dt_display, price=price_points)
            with rcon_client as rcon:
                rcon.send_command(f'SendChat 6 "{msg}" {steam_id}')

        except Exception as e:
            self.logger.error(f"Erro ao registrar webhook: {e}")
            with rcon_client as rcon:
                rcon.send_command(f'SendChat 7 "{msgs["database_error"]}" {steam_id}')

    def _handle_atr_command(self, steam_id: str, player: str, message_text: str) -> None:
        try:
            if not steam_id:
                return

            from utils.rcon_client import get_rcon_client_from_config
            rcon_client = get_rcon_client_from_config()
            if not rcon_client:
                self.logger.error("RCON não está disponível para sincronização de atributos.")
                return

            with rcon_client as rcon:
                from utils.scum_db_helper import scum_db_readonly_connection
                from utils.scum_attributes_editor import (
                    resolve_prisoner_identifier,
                    get_prisoner_attributes
                )

                if not os.path.exists(self.scum_db_path):
                    msg_error = "Banco de dados do jogo SCUM.db não encontrado."
                    rcon.send_command(f'SendChat 7 "{msg_error}" {steam_id}')
                    return

                with scum_db_readonly_connection(self.scum_db_path) as scum_conn:
                    scum_cursor = scum_conn.cursor()
                    ident_info = resolve_prisoner_identifier(scum_cursor, steam_id)
                    if not ident_info:
                        msg_error = "Prisioneiro não encontrado no banco de dados. Logue no servidor primeiro!"
                        rcon.send_command(f'SendChat 7 "{msg_error}" {steam_id}')
                        return
                    prisoner_id = ident_info["prisoner_id"]
                    current_attrs = get_prisoner_attributes(scum_cursor, prisoner_id)
                    
                    if not current_attrs:
                        msg_error = "Não foi possível ler seus atributos do banco de dados."
                        rcon.send_command(f'SendChat 7 "{msg_error}" {steam_id}')
                        return

                    # Salvar no cache do SSM.db (inclui prisoner_id para validação posterior)
                    try:
                        from core.database.connector import DatabaseConnector
                        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                INSERT INTO player_attributes_cache (steam_id, strength, constitution, dexterity, intelligence, prisoner_id, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                                ON CONFLICT(steam_id) DO UPDATE SET
                                    strength = excluded.strength,
                                    constitution = excluded.constitution,
                                    dexterity = excluded.dexterity,
                                    intelligence = excluded.intelligence,
                                    prisoner_id = excluded.prisoner_id,
                                    updated_at = CURRENT_TIMESTAMP
                                """,
                                (
                                    steam_id,
                                    current_attrs.get("strength"),
                                    current_attrs.get("constitution"),
                                    current_attrs.get("dexterity"),
                                    current_attrs.get("intelligence"),
                                    prisoner_id
                                )
                            )
                            conn.commit()
                        self.logger.debug(
                            f"[ATR] Cache sincronizado para {steam_id} (prisoner_id={prisoner_id}): "
                            f"STR={current_attrs.get('strength')} CON={current_attrs.get('constitution')} "
                            f"DEX={current_attrs.get('dexterity')} INT={current_attrs.get('intelligence')}"
                        )
                    except Exception as e:
                        self.logger.error(f"Erro ao salvar cache de atributos no SSM.db: {e}")
                        msg_error = "Erro interno ao atualizar cache de atributos."
                        rcon.send_command(f'SendChat 7 "{msg_error}" {steam_id}')
                        return

                    s = current_attrs.get("strength", 3.0)
                    c = current_attrs.get("constitution", 3.0)
                    d = current_attrs.get("dexterity", 3.0)
                    i = current_attrs.get("intelligence", 3.0)
                    
                    msg_success = f"[SSM] Atributos sincronizados! FOR: {s:.0f} | CON: {c:.0f} | DES: {d:.0f} | INT: {i:.0f}"
                    rcon.send_command(f'SendChat 6 "{msg_success}" {steam_id}')

        except Exception as e:
            self.logger.error(f"Erro ao processar comando /atr: {e}")
