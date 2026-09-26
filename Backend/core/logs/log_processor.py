"""
Processador Principal de Logs do SCUM
Integra monitoramento, parsing e armazenamento em banco de dados
"""

import os
import json
import time
import threading
import queue
import hashlib
import math
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from core.database.connector import DatabaseConnector

from .database_manager import DatabaseManager
from .log_parser import LogParser
from .file_monitor import LogFileMonitor, LogFileScanner
from .player_processor import PlayerProcessor
from .temp_file_manager import TempFileManager
from .vehicle_processor import VehicleProcessor
from .vehicle_notifier import VehicleNotifier
from .chat_processor import ChatProcessor
from .chat_command_monitor import ChatCommandMonitor
from .admin_log_processor import AdminLogProcessor
from .vehicle_destruction_processor import VehicleDestructionProcessor
from .bunker_processor import BunkerProcessor
from .kill_processor import KillProcessor
from .gameplay_parser import GameplayLogParser
from .minigame_notifier import MinigameNotifier
from .famepoints_processor import FamepointsProcessor
from .bank_transaction_processor import BankTransactionProcessor
from .cargo_drop_notifier import CargoDropNotifier
from .scum_server_log_monitor import ScumServerLogMonitor
import requests
from pathlib import Path
import re
import configparser
from .db_write_queue import DBWriteQueue, QueuedDatabaseManager
from .db_snapshotter import DBSnapshotter

class RconPunishmentWorker:
    def __init__(self, log_processor):
        self.log_processor = log_processor
        self.queue = queue.Queue(maxsize=100)
        self.cooldowns = {}  # steam_id -> float (timestamp)
        self.thread = None
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, name="rcon-punishment-worker", daemon=True)
        self.thread.start()

    def stop(self, timeout: float = 5.0):
        if not self.running:
            return
        self.running = False
        self.queue.put(None)
        if self.thread:
            self.thread.join(timeout=timeout)

    def enqueue_punishment(self, steam_id: str, mine_id: int, x: float, y: float, z: float, delay_seconds: float):
        if self.queue.full():
            print(f"PUNISHMENT_WORKER AVISO: Fila de punições cheia. Ignorando teleporte para {steam_id}")
            return False
        self.queue.put((steam_id, mine_id, x, y, z, delay_seconds))
        return True

    def _run(self):
        while self.running:
            try:
                item = self.queue.get()
                if item is None:
                    break

                steam_id, mine_id, x, y, z, delay = item
                
                # Cooldown check
                now = time.time()
                last_punished = self.cooldowns.get(steam_id, 0)
                if now - last_punished < 30.0:  # 30 segundos de cooldown global por player
                    print(f"PUNISHMENT_WORKER INFO: Cooldown de punição ativo para {steam_id}. Ignorando teleporte para mina {mine_id}.")
                    # Marcar como executado no banco para não tentar mais e evitar loop
                    self.log_processor.db_manager.mark_mine_teleported(mine_id)
                    continue

                # Delay
                if delay > 0:
                    time.sleep(delay)

                if not self.running:
                    break

                # Obter config RCON
                rcon_cfg = self.log_processor.config.get("rcon", {})
                if not rcon_cfg.get("enabled", False):
                    continue

                ip = str(rcon_cfg.get("ip", "127.0.0.1") or "127.0.0.1")
                port = int(rcon_cfg.get("port", 28015) or 28015)
                password = str(rcon_cfg.get("password", "") or "")
                if not password:
                    continue

                from utils.rcon_client import RconClient
                try:
                    with RconClient(ip, port, password, timeout=5.0) as rcon:
                        # Verificar se jogador está online
                        if not rcon.is_player_online(steam_id):
                            print(f"PUNISHMENT_WORKER INFO: Jogador {steam_id} offline. Teleporte para mina {mine_id} cancelado/pendente de login.")
                            continue

                        # Executa o teleporte
                        cmd = f"#teleport {x:.4f} {y:.4f} {z:.4f} {steam_id}"
                        print(f"PUNISHMENT_WORKER EXECUTE: {cmd}")
                        rcon.send_command(cmd)

                        # Enviar notificação ingame
                        mines_cfg = self.log_processor.config.get("mines_alerts", {})
                        msg = mines_cfg.get("teleport_message", "ATENCAO: Voce foi teleportado por implantar mina fora da flag!")
                        rcon.send_command(f'SendNotification 4 0 "{msg}" {steam_id}')

                        # Registrar cooldown
                        self.cooldowns[steam_id] = time.time()

                        # Marcar mina no banco como teleportada executada
                        self.log_processor.db_manager.mark_mine_teleported(mine_id)
                except Exception as e:
                    print(f"PUNISHMENT_WORKER ERRO: Falha ao executar punição RCON para {steam_id}: {e}")

            except Exception as e:
                print(f"PUNISHMENT_WORKER ERRO: Exceção no worker thread: {e}")
                time.sleep(1)


class LogProcessor:
    """Processador principal que integra todos os componentes"""
    
    def __init__(
        self,
        log_directory: str = None,
        db_path: str = "data/SSM.db",
        config_path: str = "data/config.json",
        discord_webhook=None,
        discord_bot_service=None,
        logger=None,
    ):
        # Carregar configuração se log_directory não for fornecido
        if log_directory is None:
            log_directory = self._load_log_directory_from_config(config_path)
        
        self.log_directory = log_directory
        self.db_path = db_path
        self.config_path = config_path
        self.discord_webhook = discord_webhook  # Referência opcional ao DiscordWebhook
        self.discord_bot_service = discord_bot_service
        self.logger = logger  # StructuredLogger (opcional)
        
        # Carregar configuração completa
        self.config = self._load_config()
        
        # Inicializar componentes
        self._db_write_queue = DBWriteQueue()
        self._db_write_queue.start()

        self._db_manager_inner = DatabaseManager(db_path)
        self.db_manager = QueuedDatabaseManager(self._db_manager_inner, self._db_write_queue)

        self._db_snapshotter = DBSnapshotter(
            source_db_path=db_path,
            public_db_path=os.path.join(os.path.dirname(db_path), "SSM_public.db"),
            interval_seconds=300,
            logger=self.logger,
        )
        self._db_snapshotter.start()
        self.parser = LogParser()
        self.file_monitor = None
        self.file_scanner = LogFileScanner(log_directory)
        self.player_processor = PlayerProcessor(self.db_manager)
        self.temp_manager = TempFileManager("data/temp")
        self.famepoints_processor = None
        self.cargo_drop_notifier = None
        self.scum_server_log_monitor = None
        
        # Sistema de deduplicação - evitar processamento múltiplo do mesmo arquivo
        self.processed_files = set()  # Arquivos já processados nesta sessão
        self.processing_locks = set()  # Arquivos sendo processados no momento

        try:
            cfg_dir = Path(self.config_path).resolve().parent
        except Exception:
            cfg_dir = Path("data").resolve()
        self._mines_alerts_state_path = str(cfg_dir / "mines_alerts_state.json")
        try:
            self._mines_alerts_sent_sigs = set(self._load_mines_alerts_sent_signatures())
        except Exception:
            self._mines_alerts_sent_sigs = set()
        
        # Timer para limpeza periódica do cache (1 hora)
        self.cache_cleanup_timer = None
        self.cache_cleanup_interval = 3600  # 1 hora em segundos

        self._weapons_mapping_lock = threading.Lock()
        
        # Inicializar sistema de veículos
        try:
            scum_db_path = None
            try:
                from utils.config_path_helper import ConfigPathHelper

                path_helper = ConfigPathHelper(self.config)
                scum_db_path = path_helper.get_scum_db_path()
            except Exception:
                scum_db_path = None

            self.vehicle_processor = VehicleProcessor(scum_db_path=scum_db_path)
            self.vehicle_notifier = VehicleNotifier(
                self._load_webhook_config(),
                self.vehicle_processor,
                self.config,
                logger=self.logger,
            )
            print("OK Sistema de veículos inicializado")
        except Exception as e:
            print(f"AVISO Sistema de veículos não disponível: {e}")
            self.vehicle_processor = None
            self.vehicle_notifier = None
        
        # Inicializar sistema de chat
        try:
            webhook_config = self._load_webhook_config()
            chat_config = self.config.get("chat_monitoring", {}) if isinstance(self.config, dict) else {}
            self.chat_processor = ChatProcessor(self._load_webhook_config(), logger=self.logger, chat_config=chat_config)
            print("OK Sistema de chat inicializado")
        except Exception as e:
            print(f"AVISO Sistema de chat não disponível: {e}")
            self.chat_processor = None

        # Monitor/Executor de comandos de chat (/vbuy, /buy, etc)
        self.chat_command_monitor = None
        try:
            scum_db_path = None
            try:
                from utils.config_path_helper import ConfigPathHelper

                path_helper = ConfigPathHelper(self.config)
                scum_db_path = path_helper.get_scum_db_path()
            except Exception:
                scum_db_path = None

            self.chat_command_monitor = ChatCommandMonitor(
                logger=self.logger,
                scum_db_path=scum_db_path,
                discord_bot_service=self.discord_bot_service,
                ssm_db_path=self.db_path,
            )
        except Exception as e:
            self.chat_command_monitor = None
            try:
                if self.logger:
                    self.logger.warn(
                        "ChatCommandMonitor não disponível no LogProcessor",
                        {"error": str(e)},
                    )
            except Exception:
                pass
        
        # Inicializar sistema de admin logs
        try:
            # logger.debug("Tentando inicializar AdminLogProcessor...")
            self.admin_log_processor = AdminLogProcessor(db_path=self.db_path)
            # logger.debug("Sistema de admin logs inicializado")
        except Exception as e:
            print(f"AVISO Sistema de admin logs não disponível: {e}")
            import traceback
            traceback.print_exc()
            self.admin_log_processor = None
        
        # Inicializar sistema de destruição de veículos
        try:
            # logger.debug("Tentando inicializar VehicleDestructionProcessor...")
            self.vehicle_destruction_processor = VehicleDestructionProcessor(db_manager=self.db_manager)
            # logger.debug("Sistema de destruição de veículos inicializado")
        except Exception as e:
            print(f"AVISO Sistema de destruição de veículos não disponível: {e}")
            import traceback
            traceback.print_exc()
            self.vehicle_destruction_processor = None
        
        # Inicializar sistema de bunkers
        try:
            self.bunker_processor = BunkerProcessor(self.db_manager)
            print("OK Sistema de bunkers inicializado")
        except Exception as e:
            print(f"AVISO Sistema de bunkers não disponível: {e}")
            import traceback
            traceback.print_exc()
            self.bunker_processor = None
        
        # Inicializar sistema de kill logs
        try:
            # logger.debug("Tentando inicializar KillProcessor...")
            self.kill_processor = KillProcessor(
                db_manager=self.db_manager,
                webhooks_path=str(Path(self.config_path).parent / "webhooks.json"),
                config=self.config,
                config_path=self.config_path
            )
            # logger.debug("Sistema de kill logs inicializado")
        except Exception as e:
            print(f"AVISO Sistema de kill logs não disponível: {e}")
            import traceback
            traceback.print_exc()
            self.kill_processor = None
        
        # Inicializar parser de minigame events
        try:
            # logger.debug("Tentando inicializar GameplayLogParser...")
            self.gameplay_parser = GameplayLogParser(self.temp_manager)
            # logger.debug("Sistema de minigame events inicializado")
        except Exception as e:
            print(f"AVISO Sistema de minigame events não disponível: {e}")
            import traceback
            traceback.print_exc()
            self.gameplay_parser = None
        
        # Inicializar notifier de minigame events
        try:
            # logger.debug("Tentando inicializar MinigameNotifier...")
            self.minigame_notifier = MinigameNotifier()
            # logger.debug("Sistema de notificações de minigame inicializado")
        except Exception as e:
            print(f"AVISO Sistema de notificações de minigame não disponível: {e}")
            import traceback
            traceback.print_exc()
            self.minigame_notifier = None

        # Inicializar notifier de cargo drop (SCUM.log)
        try:
            webhook_config = self._load_webhook_config()
            selfdestruct = self._load_cargo_drop_selfdestruct_seconds()
            self.cargo_drop_notifier = CargoDropNotifier(
                webhook_config,
                cargo_drop_selfdestruct_seconds=selfdestruct,
            )
            if self.cargo_drop_notifier and getattr(self.cargo_drop_notifier, "webhook_url", None):
                if self.logger:
                    self.logger.info("[CARGO_DROP] Webhook cargo_drop configurado")
                else:
                    print("[CARGO_DROP] Webhook cargo_drop configurado")
            else:
                if self.logger:
                    self.logger.warn("[CARGO_DROP] Webhook cargo_drop NÃO configurado (data/webhooks.json)")
                else:
                    print("[CARGO_DROP] Webhook cargo_drop NÃO configurado (data/webhooks.json)")
        except Exception as e:
            print(f"AVISO Sistema de cargo drop não disponível: {e}")
            self.cargo_drop_notifier = None

        # Inicializar processador de famepoints
        try:
            # logger.debug("Tentando inicializar FamepointsProcessor...")
            from .famepoints_processor import FamepointsProcessor
            self.famepoints_processor = FamepointsProcessor(self.db_manager, self.temp_manager)
            # logger.debug("Sistema de fama inicializado")
        except Exception as e:
            print(f"AVISO Sistema de fama não disponível: {e}")
            import traceback
            traceback.print_exc()
            self.famepoints_processor = None
        
        # Inicializar processador de transações bancárias
        try:
            # logger.debug("Tentando inicializar BankTransactionProcessor...")
            self.bank_transaction_processor = BankTransactionProcessor(
                ssm_db_path=self.db_path,
                logs_directory=self.log_directory,
                discord_webhook=self.discord_webhook
            )
            # logger.debug("Sistema de transações bancárias inicializado")
        except Exception as e:
            print(f"AVISO Sistema de transações bancárias não disponível: {e}")
            import traceback
            traceback.print_exc()
            self.bank_transaction_processor = None
        
        # Controle de processamento - OPÇÃO 5: Event-based shutdown robusto
        self.running = False
        self.stop_event = threading.Event()  # Event para shutdown rápido e thread-safe
        self.processed_files = set()
        self.last_admin_log_file = None  # Controle do último arquivo admin processado
        self.last_vehicle_destruction_log_file = None  # Controle do último arquivo vehicle destruction processado
        self.stats = {
            'total_sessions': 0,
            'files_processed': 0,
            'errors': 0,
            'start_time': None
        }
        
        # RCON Punishment Worker
        self._punishment_worker = RconPunishmentWorker(self)
        self._punishment_worker.start()
        
        # OPÇÃO 5: Propagar stop_event para processadores filhos após inicialização
        # Isso será feito em start_processing() após inicializar todos os componentes
    
    def _load_config(self) -> Dict[str, Any]:
        """Carregar configuração completa do config.json"""
        try:
            if not os.path.exists(self.config_path):
                print(f"AVISO Arquivo de configuração não encontrado: {self.config_path}")
                return {}
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            modified = False
            if not isinstance(config, dict):
                config = {}
                modified = True

            mines_cfg = config.get("mines_alerts")
            if not isinstance(mines_cfg, dict):
                mines_cfg = {}
                config["mines_alerts"] = mines_cfg
                modified = True

            if "flag_radius_units" not in mines_cfg:
                mines_cfg["flag_radius_units"] = 10000
                modified = True

            if "flag_radius_tolerance_units" not in mines_cfg:
                mines_cfg["flag_radius_tolerance_units"] = 600
                modified = True

            if "teleport_punishment_enabled" not in mines_cfg:
                mines_cfg["teleport_punishment_enabled"] = False
                modified = True

            if "teleport_punishment_delay_seconds" not in mines_cfg:
                mines_cfg["teleport_punishment_delay_seconds"] = 5.0
                modified = True

            if "wallet_fine_enabled" not in mines_cfg:
                mines_cfg["wallet_fine_enabled"] = False
                modified = True

            if "wallet_fine_amount" not in mines_cfg:
                mines_cfg["wallet_fine_amount"] = 1000
                modified = True

            if "teleport_message" not in mines_cfg:
                mines_cfg["teleport_message"] = "ATENCAO: Voce foi teleportado por implantar mina fora da flag!"
                modified = True

            fm_cfg = config.get("file_monitor")
            if not isinstance(fm_cfg, dict):
                fm_cfg = {}
                config["file_monitor"] = fm_cfg
                modified = True

            if "polling_interval_seconds" not in fm_cfg:
                fm_cfg["polling_interval_seconds"] = 5
                modified = True

            if "gameplay_copy_interval_seconds" not in fm_cfg:
                fm_cfg["gameplay_copy_interval_seconds"] = 5
                modified = True

            if "chest_ownership_copy_interval_seconds" not in fm_cfg:
                fm_cfg["chest_ownership_copy_interval_seconds"] = 30
                modified = True

            if "economy_copy_interval_seconds" not in fm_cfg:
                fm_cfg["economy_copy_interval_seconds"] = 30
                modified = True

            kill_feed_cfg = config.get("kill_feed")
            if not isinstance(kill_feed_cfg, dict):
                kill_feed_cfg = {}
                config["kill_feed"] = kill_feed_cfg
                modified = True

            if "enabled" not in kill_feed_cfg:
                kill_feed_cfg["enabled"] = True
                modified = True

            if "mode" not in kill_feed_cfg:
                kill_feed_cfg["mode"] = "chat"
                modified = True

            if "chat_type" not in kill_feed_cfg:
                kill_feed_cfg["chat_type"] = 2
                modified = True

            if "message_template" not in kill_feed_cfg:
                kill_feed_cfg["message_template"] = "{killer} matou {victim} ({weapon} - {distance}m) | {phrase}"
                modified = True

            if "phrases_path" not in kill_feed_cfg:
                kill_feed_cfg["phrases_path"] = "data/kill_feed_phrases.json"
                modified = True

            if "priority" not in kill_feed_cfg:
                kill_feed_cfg["priority"] = 15
                modified = True

            if modified:
                try:
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"AVISO Não foi possível salvar defaults no config.json: {e}")
            
            return config
            
        except Exception as e:
            print(f"ERRO Erro ao carregar configuração: {e}")
            return {}

    def _get_server_settings_ini_path(self) -> Optional[str]:
        """
        Obter caminho completo do ServerSettings.ini a partir do config.json.
        """
        try:
            cfg_dir = (
                (self.config or {})
                .get("paths", {})
                .get("scum_server", {})
                .get("config_directory")
            )
            if not cfg_dir:
                return None
            return str(Path(cfg_dir) / "ServerSettings.ini")
        except Exception:
            return None

    def _trap_name_to_weapon_key(self, trap_name: str) -> Optional[str]:
        try:
            t = str(trap_name or "").strip().lower()
            if not t:
                return None

            if "pressure cooker" in t:
                return "PressureCookerBomb"
            if "improvised claymore" in t:
                return "ImprovisedClaymore"
            if "claymore" in t:
                return "Claymore"
            if "prom-1" in t:
                return "PromTrap"
            if "pipe bomb" in t:
                return "PipeBomb"
            if "tnt" in t:
                return "TNT"
            if "improvised" in t and "mine" in t:
                return "ImprovisedMine"
            if "mine" in t:
                return "Mine_01"

            # Fallback: gerar chave a partir do nome da trap
            # Ex.: "Fireworks Trap" -> "FireworksTrap", "Silent Alarm" -> "SilentAlarm"
            raw = str(trap_name or "").strip()
            if not raw:
                return None

            parts = re.split(r"[^A-Za-z0-9]+", raw)
            parts = [p for p in parts if p]
            if not parts:
                return None
            return "".join([p[:1].upper() + p[1:] for p in parts])
        except Exception:
            return None

    def _get_trap_thumbnail_path(self, trap_name: str) -> Optional[str]:
        try:
            key = self._trap_name_to_weapon_key(trap_name)
            if not key:
                return None

            try:
                data_dir = Path(self.config_path).resolve().parent
            except Exception:
                data_dir = Path("data").resolve()

            weapons_dir = data_dir / "imagens" / "Weapons"
            mapping_path = weapons_dir / "mapping.json"

            try:
                os.makedirs(str(weapons_dir), exist_ok=True)
            except Exception:
                pass

            mapping: Dict[str, Any] = {}
            if mapping_path.exists():
                with open(mapping_path, "r", encoding="utf-8") as f:
                    mapping = json.load(f)
            else:
                mapping = {}

            if not isinstance(mapping, dict):
                return None

            if key not in mapping:
                try:
                    with self._weapons_mapping_lock:
                        mapping[key] = ""
                        sorted_mapping = dict(sorted(mapping.items()))
                        with open(mapping_path, "w", encoding="utf-8") as f:
                            json.dump(sorted_mapping, f, indent=2, ensure_ascii=False)
                except Exception:
                    return None
                return None

            filename = mapping.get(key)
            if not isinstance(filename, str) or not filename.strip():
                return None

            img_path = weapons_dir / filename
            return str(img_path) if img_path.exists() else None
        except Exception:
            return None

    def _load_cargo_drop_selfdestruct_seconds(self) -> Optional[float]:
        """
        Ler scum.CargoDropSelfdestructTime (segundos) do ServerSettings.ini.
        """
        ini_path = self._get_server_settings_ini_path()
        if not ini_path or not os.path.exists(ini_path):
            return None
        try:
            parser = configparser.ConfigParser()
            parser.optionxform = str  # preservar case/dots
            parser.read(ini_path, encoding="utf-8")

            # normalmente fica em [World]
            value = None
            if parser.has_section("World") and parser.has_option(
                "World", "scum.CargoDropSelfdestructTime"
            ):
                value = parser.get(
                    "World", "scum.CargoDropSelfdestructTime", fallback=None
                )

            # fallback: procurar em qualquer seção
            if value is None:
                for sec in parser.sections():
                    if parser.has_option(sec, "scum.CargoDropSelfdestructTime"):
                        value = parser.get(
                            sec, "scum.CargoDropSelfdestructTime", fallback=None
                        )
                        break

            if value is None:
                return None
            return float(str(value).strip())
        except Exception:
            return None
    
    def _load_log_directory_from_config(self, config_path: str) -> str:
        """Carregar diretório de logs do config.json"""
        try:
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Obter diretório de logs da configuração
            logs_directory = config.get('paths', {}).get('scum_server', {}).get('logs_directory')
            
            if not logs_directory:
                # Fallback para estrutura antiga
                logs_directory = config.get('server', {}).get('logs_directory')
            
            if not logs_directory:
                raise ValueError("Diretório de logs não configurado no config.json")
            
            # Verificar se diretório existe
            if not os.path.exists(logs_directory):
                print(f"AVISO Diretório de logs não encontrado: {logs_directory}")
                print("   Verifique a configuração no config.json")
            
            return logs_directory
            
        except Exception as e:
            print(f"ERRO Erro ao carregar configuração: {e}")
            # Fallback para diretório padrão
            default_directory = r"C:\Servers\scum\SCUM\Saved\SaveFiles\Logs"
            print(f"   Usando diretório padrão: {default_directory}")
            return default_directory
    
    def _load_webhook_config(self) -> Dict[str, str]:
        """Carregar configuração de webhooks"""
        try:
            # 1) caminho relativo (comportamento atual)
            webhook_path = "data/webhooks.json"
            if os.path.exists(webhook_path):
                try:
                    from core.webhooks.manager import WebhooksManager

                    mgr = WebhooksManager(webhook_path)
                    webhooks = mgr.load()
                    return webhooks if isinstance(webhooks, dict) else {}
                except Exception:
                    with open(webhook_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        if isinstance(raw, dict) and raw.get("schema_version") == 2 and isinstance(raw.get("events"), dict):
                            out: Dict[str, str] = {}
                            for key, ev in raw.get("events", {}).items():
                                if not isinstance(ev, dict) or not ev.get("enabled"):
                                    continue
                                target = ev.get("target")
                                if not isinstance(target, dict):
                                    continue
                                webhook = target.get("webhook")
                                if not isinstance(webhook, dict):
                                    continue
                                url = webhook.get("url")
                                if isinstance(url, str) and url.strip():
                                    out[str(key)] = url.strip()
                            return out
                        return raw if isinstance(raw, dict) else {}

            # 2) fallback: relativo ao diretório do projeto (evita problemas de cwd em GUI/pyinstaller)
            try:
                from pathlib import Path as _Path
                base_dir = _Path(__file__).resolve().parents[2]  # .../Backend
                webhook_path2 = str(base_dir / "data" / "webhooks.json")
                if os.path.exists(webhook_path2):
                    try:
                        from core.webhooks.manager import WebhooksManager

                        mgr = WebhooksManager(webhook_path2)
                        webhooks = mgr.load()
                        return webhooks if isinstance(webhooks, dict) else {}
                    except Exception:
                        with open(webhook_path2, "r", encoding="utf-8") as f:
                            raw = json.load(f)
                            if isinstance(raw, dict) and raw.get("schema_version") == 2 and isinstance(raw.get("events"), dict):
                                out: Dict[str, str] = {}
                                for key, ev in raw.get("events", {}).items():
                                    if not isinstance(ev, dict) or not ev.get("enabled"):
                                        continue
                                    target = ev.get("target")
                                    if not isinstance(target, dict):
                                        continue
                                    webhook = target.get("webhook")
                                    if not isinstance(webhook, dict):
                                        continue
                                    url = webhook.get("url")
                                    if isinstance(url, str) and url.strip():
                                        out[str(key)] = url.strip()
                                return out
                            return raw if isinstance(raw, dict) else {}
            except Exception:
                pass

            return {}
        except Exception as e:
            print(f"AVISO Erro ao carregar webhooks: {e}")
            return {}
    
    def _is_file_being_processed(self, file_path: str) -> bool:
        """Verificar se arquivo está sendo processado no momento"""
        return file_path in self.processing_locks
    
    def _mark_file_processing(self, file_path: str) -> None:
        """Marcar arquivo como sendo processado"""
        self.processing_locks.add(file_path)
    
    def _mark_file_processed(self, file_path: str) -> None:
        """Marcar arquivo como processado e remover do lock"""
        self.processed_files.add(file_path)
        self.processing_locks.discard(file_path)
    
    def _should_process_file(self, file_path: str) -> bool:
        """Verificar se arquivo deve ser processado (não duplicado)"""
        if file_path in self.processed_files:
            # logger.debug(f"Arquivo já processado nesta sessão: {os.path.basename(file_path)}")
            return False
        
        if file_path in self.processing_locks:
            # logger.debug(f"Arquivo sendo processado no momento: {os.path.basename(file_path)}")
            return False
        
        return True
    
    def _cleanup_cache(self):
        """
        Limpar cache de arquivos processados para evitar acúmulo de memória.
        Seguro porque o banco de dados (log_files_processed) é a fonte de verdade.
        """
        try:
            # Contar quantos arquivos serão removidos
            processed_count = len(self.processed_files)
            locks_count = len(self.processing_locks)
            
            # Limpar caches
            self.processed_files.clear()
            self.processing_locks.clear()
            
            # Log apenas se havia arquivos para limpar
            if processed_count > 0 or locks_count > 0:
                print(f"[CACHE CLEANUP] Cache limpo: {processed_count} arquivos processados, {locks_count} locks removidos")
            
            # Agendar próxima limpeza (1 hora)
            if self.running:
                self._schedule_cache_cleanup()
        except Exception as e:
            print(f"[CACHE CLEANUP] Erro ao limpar cache: {e}")
            # Agendar próxima limpeza mesmo em caso de erro
            if self.running:
                self._schedule_cache_cleanup()
    
    def _schedule_cache_cleanup(self):
        """Agendar próxima limpeza do cache"""
        try:
            # Cancelar timer anterior se existir
            if self.cache_cleanup_timer is not None:
                self.cache_cleanup_timer.cancel()
            
            # Criar novo timer (1 hora)
            self.cache_cleanup_timer = threading.Timer(
                self.cache_cleanup_interval,
                self._cleanup_cache
            )
            self.cache_cleanup_timer.daemon = True  # Não bloquear shutdown
            self.cache_cleanup_timer.start()
        except Exception as e:
            print(f"[CACHE CLEANUP] Erro ao agendar limpeza do cache: {e}")
    
    def start_processing(self, real_time: bool = True):
        """Iniciar processamento de logs - OPÇÃO 5: Inicializa stop_event"""
        try:
            self.stats['start_time'] = datetime.now()
            self.running = True
            self.stop_event.clear()  # OPÇÃO 5: Limpar event ao iniciar

            try:
                if self.logger:
                    self.logger.info(
                        "[LOG_PROCESSOR] start_processing",
                        {"real_time": bool(real_time)},
                    )
            except Exception:
                pass
            
            # Iniciar limpeza periódica do cache (1 hora)
            self._schedule_cache_cleanup()
            
            # OPÇÃO 5: Propagar stop_event para processadores filhos
            if self.bank_transaction_processor and hasattr(self.bank_transaction_processor, 'set_stop_event'):
                self.bank_transaction_processor.set_stop_event(self.stop_event)
            
            # logger.debug("Iniciando processamento de logs do SCUM...")
            
            # Processar arquivos existentes primeiro
            self._process_existing_files()
            
            # Iniciar monitoramento em tempo real se solicitado
            if real_time and self.running and not self.stop_event.is_set():
                try:
                    if self.logger:
                        self.logger.info("[LOG_PROCESSOR] Starting real-time monitoring", {})
                except Exception:
                    pass
                self._start_real_time_monitoring()
            else:
                try:
                    if self.logger:
                        self.logger.warn(
                            "[LOG_PROCESSOR] Real-time monitoring skipped",
                            {
                                "real_time": bool(real_time),
                                "running": bool(self.running),
                                "stop_event": bool(self.stop_event.is_set()),
                            },
                        )
                except Exception:
                    pass
            
            # logger.debug("Processamento iniciado com sucesso!")
            
        except Exception as e:
            print(f"ERRO Erro ao iniciar processamento: {e}")
            try:
                if self.logger:
                    self.logger.error(f"[LOG_PROCESSOR] start_processing failed: {e}", {})
            except Exception:
                pass
            raise
    
    def stop_processing(self, timeout: float = 5.0):
        """
        Parar processamento de logs de forma robusta (OPÇÃO 5: Event + Timeout + Fallback)
        
        Args:
            timeout: Tempo máximo em segundos para aguardar parada completa (padrão: 5s)
        """
        try:
            # 1. Sinalizar parada via Event (thread-safe e rápido)
            self.stop_event.set()
            self.running = False
            
            # 1.5. Cancelar timer de limpeza do cache
            if self.cache_cleanup_timer is not None:
                try:
                    self.cache_cleanup_timer.cancel()
                    self.cache_cleanup_timer = None
                except Exception as e:
                    print(f"AVISO Erro ao cancelar timer de limpeza do cache: {e}")
            
            # 2. Parar FileMonitor primeiro (evita novos arquivos sendo processados)
            if self.file_monitor:
                try:
                    self.file_monitor.stop_monitoring()
                except Exception as e:
                    print(f"AVISO Erro ao parar FileMonitor: {e}")
                finally:
                    self.file_monitor = None

            # 2.5. Parar monitor do SCUM.log (cargo drop)
            if self.scum_server_log_monitor:
                try:
                    self.scum_server_log_monitor.stop(timeout=2.0)
                except Exception:
                    pass
            
            # 3. Sinalizar parada para processadores filhos
            if self.bank_transaction_processor and hasattr(self.bank_transaction_processor, 'set_running'):
                try:
                    self.bank_transaction_processor.set_running(False)
                except Exception as e:
                    print(f"AVISO Erro ao parar BankTransactionProcessor: {e}")

            # 3.5. Parar snapshotter e fila de escrita do banco
            try:
                if hasattr(self, '_db_snapshotter') and self._db_snapshotter:
                    self._db_snapshotter.stop(timeout=2.0)
            except Exception:
                pass
            try:
                if hasattr(self, '_db_write_queue') and self._db_write_queue:
                    self._db_write_queue.stop(timeout=2.0)
            except Exception:
                pass

            # Parar RconPunishmentWorker
            try:
                if hasattr(self, '_punishment_worker') and self._punishment_worker:
                    self._punishment_worker.stop(timeout=2.0)
            except Exception:
                pass
            
            # 4. Aguardar processamento em andamento terminar (com timeout)
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Verificar se há arquivos sendo processados
                if not self.processing_locks:
                    break
                time.sleep(0.1)  # Verificar a cada 100ms
            
            # 5. Se ainda há processamento após timeout, forçar parada
            if self.processing_locks:
                print(f"AVISO Limpando {len(self.processing_locks)} arquivo(s) em processamento após timeout")
                self.processing_locks.clear()
            
            print("OK Processamento parado")
            
        except Exception as e:
            print(f"ERRO Erro ao parar processamento: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_existing_files(self):
        """Processar arquivos de log existentes"""
        try:
            # OPÇÃO 5: Verificar stop_event ANTES de processar (thread-safe)
            if not self.running or self.stop_event.is_set():
                return
            
            # logger.debug("Processando arquivos existentes...")
            
            # Escanear arquivos existentes
            existing_files = self.file_scanner.scan_existing_files()
            
            # MELHORIA: Separar economy logs para processar por último
            # Isso permite que serviços de sincronização iniciem antes, evitando bloqueios
            economy_files = [f for f in existing_files if os.path.basename(f).startswith('economy_')]
            non_economy_files = [f for f in existing_files if not os.path.basename(f).startswith('economy_')]
            
            # Processar arquivos não-economy primeiro
            for file_path in non_economy_files:
                if self.running:
                    filename = os.path.basename(file_path)
                    
                    # Processar arquivos de chat
                    if self.chat_processor and filename.startswith('chat_'):
                        self._process_chat_file(file_path)
                    # NOTA: chest_ownership_*.log NÃO é processado aqui na inicialização
                    # Deixa para a thread de cópia periódica processar incrementalmente
                    # Processar arquivos de admin log
                    elif self.admin_log_processor and filename.startswith('admin_'):
                        self._process_admin_log_file(file_path)
                    # Processar arquivos de destruição de veículos
                    elif self.vehicle_destruction_processor and filename.startswith('vehicle_destruction_'):
                        self._process_vehicle_destruction_file(file_path)
                    # Processar arquivos de gameplay (bunkers e minigame events)
                    elif filename.startswith('gameplay_'):
                        if self.bunker_processor or self.gameplay_parser:
                            self._process_gameplay_file(file_path)
                        else:
                            print(f"   [AVISO] Nem bunker_processor nem gameplay_parser disponível para processar {filename}")
                    # Processar arquivos de kill logs
                    elif self.kill_processor and filename.startswith('kill_'):
                        self._process_kill_log_file(file_path)
                    # Processar arquivos de famepoints
                    elif filename.startswith('famepoints_'):
                        if self.famepoints_processor:
                            self._process_famepoints_file(file_path)
                        else:
                            print(f"   AVISO FamepointsProcessor não disponível para processar {filename}")
                    # Processar arquivos de login/logout
                    elif not filename.startswith('chest_ownership_') and not filename.startswith('chat_') and not filename.startswith('admin_') and not filename.startswith('vehicle_destruction_') and not filename.startswith('gameplay_') and not filename.startswith('kill_') and not filename.startswith('famepoints_') and not filename.startswith('economy_'):
                        self._process_file(file_path)
            
            # OPÇÃO 5: Verificar admin log mais recente (verifica stop_event)
            if self.running and not self.stop_event.is_set() and self.admin_log_processor:
                self._check_latest_admin_log()
            
            # MELHORIA: Aguardar 15 segundos antes de processar economy logs
            # Isso permite que serviços de sincronização iniciem primeiro, evitando bloqueios
            # IMPORTANTE: Verificar self.running durante a espera para permitir parada imediata
            if self.running and economy_files and self.bank_transaction_processor:
                import time
                print(f"   INFO Aguardando 15 segundos antes de processar {len(economy_files)} arquivo(s) economy_*.log (permitindo que serviços iniciem primeiro)")
                
                # OPÇÃO 5: Aguardar 15 segundos, mas verificar stop_event a cada segundo para parada imediata
                for _ in range(15):
                    if not self.running or self.stop_event.is_set():
                        print("   INFO Processamento interrompido durante espera de economy logs")
                        break
                    time.sleep(1)
                
                # OPÇÃO 5: Processar economy logs por último (verifica stop_event em cada iteração)
                if self.running and not self.stop_event.is_set():
                    for file_path in economy_files:
                        if self.running and not self.stop_event.is_set():
                            self._process_economy_file(file_path)
                            # Pequena pausa para permitir que outras threads (GPS/Sincronização) acessem o banco
                            time.sleep(0.5)
                        else:
                            break
            
            # OPÇÃO 5: Verificar vehicle destruction log mais recente (verifica stop_event)
            if self.running and not self.stop_event.is_set() and self.vehicle_destruction_processor:
                self._check_latest_vehicle_destruction_log()
            
            # logger.debug(f"Arquivos existentes processados: {len(existing_files)}")
            
        except Exception as e:
            print(f"ERRO Erro ao processar arquivos existentes: {e}")
            self.stats['errors'] += 1

    def _get_discord_user_id_for_steam_id(self, steam_id: str) -> Optional[str]:
        try:
            sid = str(steam_id or "").strip()
            if not sid:
                return None

            with DatabaseConnector.get_connection(self.db_path, write_mode=True) as conn:
                cur = conn.execute(
                    "SELECT discord_user_id FROM players WHERE steam_id = ? LIMIT 1",
                    (sid,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                val = row[0]
                if val is None:
                    return None
                out = str(val).strip()
                return out if out else None
        except Exception:
            return None
    
    def _start_real_time_monitoring(self):
        """Iniciar monitoramento em tempo real"""
        try:
            if not self.running or self.stop_event.is_set():
                return
            # logger.debug("Iniciando monitoramento em tempo real...")

            try:
                if self.logger:
                    self.logger.info(
                        "[LOG_PROCESSOR] Creating LogFileMonitor",
                        {"log_directory": str(self.log_directory)},
                    )
            except Exception:
                pass
            
            # Configurar callback para mudanças de arquivo (inclui chat e veículos)
            self.file_monitor = LogFileMonitor(
                self.log_directory,
                self._on_file_changed,
                self.db_path,  # Passar db_path para acessar log_files_processed
                config=self.config,
                logger=self.logger,
            )
            
            # Iniciar monitoramento
            self.file_monitor.start_monitoring()

            try:
                if self.logger:
                    self.logger.info("[LOG_PROCESSOR] LogFileMonitor started", {})
            except Exception:
                pass

            # Iniciar monitoramento do SCUM.log (cargo drop) em paralelo
            self._start_scum_server_log_monitor()
            
        except Exception as e:
            print(f"ERRO Erro ao iniciar monitoramento em tempo real: {e}")
            try:
                if self.logger:
                    self.logger.error(f"[LOG_PROCESSOR] Real-time monitoring start failed: {e}", {})
            except Exception:
                pass
            raise

    def _get_scum_server_main_log_path(self) -> str:
        """
        Derivar caminho do SCUM.log a partir do diretório SaveFiles\\Logs (self.log_directory).
        Ex:
          C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs  ->  C:\\Servers\\Scum\\SCUM\\Saved\\Logs\\SCUM.log
        """
        base = None
        try:
            base = Path(self.log_directory).resolve()
        except Exception:
            base = None

        # Fallback padrão (mantém compatibilidade)
        fallback = r"C:\Servers\scum\SCUM\Saved\Logs\SCUM.log"

        try:
            if not base:
                return fallback

            # Caso padrão: ...\Saved\SaveFiles\Logs
            if base.name.lower() == "logs" and base.parent.name.lower() == "savefiles" and base.parent.parent.name.lower() == "saved":
                saved_dir = base.parent.parent
                return str(saved_dir / "Logs" / "SCUM.log")

            # Caso alternativo: ...\Saved\Logs
            if base.name.lower() == "logs" and base.parent.name.lower() == "saved":
                saved_dir = base.parent
                return str(saved_dir / "Logs" / "SCUM.log")

            # Heurística: procurar um parent chamado "Saved"
            for p in base.parents:
                if p.name.lower() == "saved":
                    return str(p / "Logs" / "SCUM.log")

            return fallback
        except Exception:
            return fallback

    def _start_scum_server_log_monitor(self) -> None:
        """Iniciar monitoramento incremental do SCUM.log para detectar Cargo Drops."""
        try:
            # Só iniciar se estiver rodando e se existir notifier
            if not self.running or self.stop_event.is_set():
                return
            if not self.cargo_drop_notifier:
                return

            scum_log_path = self._get_scum_server_main_log_path()
            if self.logger:
                self.logger.info(f"[CARGO_DROP] Usando SCUM.log: {scum_log_path}")
            else:
                print(f"[CARGO_DROP] Usando SCUM.log: {scum_log_path}")
            if not os.path.exists(scum_log_path):
                if self.logger:
                    self.logger.warn("[CARGO_DROP] SCUM.log não encontrado (servidor pode estar desligado)")
                else:
                    print("[CARGO_DROP] SCUM.log não encontrado (servidor pode estar desligado)")

            if self.scum_server_log_monitor is None:
                self.scum_server_log_monitor = ScumServerLogMonitor(
                    scum_log_path=scum_log_path,
                    on_new_lines=self._on_scum_server_log_lines,
                    db_manager=self.db_manager,
                    stop_event=self.stop_event,
                    poll_interval_seconds=2.0,
                    file_key="SCUM.log",
                    logger=self.logger,
                )

            self.scum_server_log_monitor.start()
            # Enviar o último drop já existente no SCUM.log (1x), sem reenviar duplicados
            self._send_last_cargo_drop_from_scum_log(scum_log_path)
        except Exception as e:
            # Não derrubar backend por falha nesse monitor, mas logar o motivo (antes era silencioso)
            try:
                import traceback
                tb = traceback.format_exc()
                if self.logger:
                    self.logger.warn(f"[CARGO_DROP] Falha ao iniciar monitor do SCUM.log: {e}")
                    self.logger.warn(f"[CARGO_DROP] Traceback: {tb}")
                else:
                    print(f"[CARGO_DROP] Falha ao iniciar monitor do SCUM.log: {e}")
                    print(f"[CARGO_DROP] Traceback: {tb}")
            except Exception:
                pass

    def _on_scum_server_log_lines(self, new_lines: List[str]) -> None:
        """Processar linhas novas do SCUM.log e enviar webhook quando cargo drop spawnar."""
        if not self.cargo_drop_notifier:
            return

        for line in new_lines:
            try:
                event = self.cargo_drop_notifier.parse_cargo_drop_event(line)
                if not event:
                    continue
                # Enviar notificação
                if not getattr(self.cargo_drop_notifier, "webhook_url", None):
                    msg = "[CARGO_DROP] Drop detectado, mas webhook cargo_drop não está configurado."
                    if self.logger:
                        self.logger.warn(msg)
                    else:
                        print(msg)
                    continue

                if not self.cargo_drop_notifier.should_send(event):
                    # Deduplicação (normal em restart)
                    msg = "[CARGO_DROP] Drop detectado, mas ignorado por deduplicação (já enviado)."
                    if self.logger:
                        self.logger.info(msg)
                    else:
                        print(msg)
                    continue

                sent = self.cargo_drop_notifier.send(event)
                if sent:
                    msg = (
                        f"[CARGO_DROP] Drop detectado (tempo real). "
                        f"X={event.x:.4f}, Y={event.y:.4f}, Z={event.z:.4f}. Enviado=True"
                    )
                    if self.logger:
                        self.logger.info(msg)
                    else:
                        print(msg)
                else:
                    status = getattr(self.cargo_drop_notifier, "last_http_status", None)
                    err = getattr(self.cargo_drop_notifier, "last_http_error", None)
                    msg = (
                        f"[CARGO_DROP] Falha ao enviar webhook (tempo real). "
                        f"status={status} error={err}"
                    )
                    if self.logger:
                        self.logger.warn(msg)
                    else:
                        print(msg)
            except Exception:
                continue

    def _send_last_cargo_drop_from_scum_log(self, scum_log_path: str) -> None:
        """
        Ao iniciar o backend, enviar o último cargo drop já registrado no SCUM.log.
        Útil para validação (servidor pode estar parado) e para não depender de um drop novo.
        Deduplicação é feita pelo CargoDropNotifier via state file.
        """
        if not self.cargo_drop_notifier:
            return
        try:
            if not os.path.exists(scum_log_path):
                return
            # Ler como UTF-8 (mais comum hoje; com BOM), fallback UTF-16LE
            try:
                with open(scum_log_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    lines = f.read().splitlines()
            except Exception:
                with open(scum_log_path, "r", encoding="utf-16le", errors="ignore") as f:
                    lines = f.read().splitlines()

            # Encontrar a última linha que casa com cargo drop
            for raw in reversed(lines):
                line = (raw or "").strip()
                if not line:
                    continue
                event = self.cargo_drop_notifier.parse_cargo_drop_event(line)
                if event:
                    if not getattr(self.cargo_drop_notifier, "webhook_url", None):
                        msg = "[CARGO_DROP] Último drop encontrado, mas webhook cargo_drop não está configurado."
                        if self.logger:
                            self.logger.warn(msg)
                        else:
                            print(msg)
                        break

                    if not self.cargo_drop_notifier.should_send(event):
                        msg = "[CARGO_DROP] Último drop encontrado, mas ignorado por deduplicação (já enviado)."
                        if self.logger:
                            self.logger.info(msg)
                        else:
                            print(msg)
                        break

                    sent = self.cargo_drop_notifier.send(event)
                    if sent:
                        msg = "[CARGO_DROP] Último drop encontrado. Enviado=True"
                        if self.logger:
                            self.logger.info(msg)
                        else:
                            print(msg)
                    else:
                        status = getattr(self.cargo_drop_notifier, "last_http_status", None)
                        err = getattr(self.cargo_drop_notifier, "last_http_error", None)
                        msg = f"[CARGO_DROP] Falha ao enviar webhook (startup). status={status} error={err}"
                        if self.logger:
                            self.logger.warn(msg)
                        else:
                            print(msg)
                    break
        except Exception as e:
            try:
                import traceback
                tb = traceback.format_exc()
                if self.logger:
                    self.logger.warn(f"[CARGO_DROP] Falha ao buscar último drop no startup: {e}")
                    self.logger.warn(f"[CARGO_DROP] Traceback: {tb}")
                else:
                    print(f"[CARGO_DROP] Falha ao buscar último drop no startup: {e}")
                    print(f"[CARGO_DROP] Traceback: {tb}")
            except Exception:
                pass
            return
    
    def _on_file_changed(self, file_path: str, new_lines: List[str]):
        """Callback para mudanças em arquivo - OPÇÃO 5: Verifica stop_event"""
        try:
            # Verificar stop_event ANTES de processar (thread-safe e rápido)
            if not self.running or self.stop_event.is_set():
                return
            
            filename = os.path.basename(file_path)
            print(f"MODIFICADO Arquivo modificado: {filename}")
            print(f"   Novas linhas: {len(new_lines)}")
            
            # Verificar se é arquivo de chat primeiro
            if self.chat_processor and filename.startswith('chat_'):
                self._process_chat_lines(filename, new_lines)
            # Processar chest_ownership quando vem do callback (cópia periódica)
            elif filename.startswith('chest_ownership_'):
                print(f"DEBUG Chest ownership detectado: {filename}, vehicle_processor={self.vehicle_processor is not None}")
                if self.vehicle_processor:
                    print(f"DEBUG Processando chest_ownership: {filename} com {len(new_lines)} linhas")
                    self._process_chest_ownership_lines(filename, new_lines)
                else:
                    print(f"ERRO VehicleProcessor não disponível para processar {filename}")
            # Verificar se é arquivo de admin log
            elif self.admin_log_processor and filename.startswith('admin_'):
                self._process_admin_log_file(file_path)
            # Verificar se é arquivo de destruição de veículos
            elif self.vehicle_destruction_processor and filename.startswith('vehicle_destruction_'):
                self._process_vehicle_destruction_file(file_path)
            # Verificar se é arquivo de gameplay (bunkers e minigame events)
            elif filename.startswith('gameplay_'):
                # Processar apenas novas linhas (incremental) quando vem do callback de cópia periódica
                if new_lines and self.gameplay_parser:
                    print(f"GAMEPLAY Processando {len(new_lines)} novas linhas de {filename} (incremental)")
                    self._process_gameplay_lines(filename, file_path, new_lines)
                elif self.bunker_processor or self.gameplay_parser:
                    # Processar arquivo completo (para processamento inicial ou watchdog)
                    self._process_gameplay_file(file_path)
                else:
                    print(f"   [AVISO] Nem bunker_processor nem gameplay_parser disponível para processar {filename}")
            # Verificar se é arquivo de kill log
            elif self.kill_processor and filename.startswith('kill_'):
                self._process_kill_log_file(file_path)
            # Verificar se é arquivo de famepoints
            elif self.famepoints_processor and filename.startswith('famepoints_'):
                self._process_famepoints_lines(filename, new_lines)
            # Verificar se é arquivo de transações bancárias
            elif self.bank_transaction_processor and filename.startswith('economy_'):
                # Processar arquivo completo (economy logs precisam de contexto completo)
                self._process_economy_file(file_path)
            else:
                # Processar logs de login/logout
                sessions = self.parser.parse_lines(new_lines)
                
                if sessions:
                    # Processar cada sessão com PlayerProcessor
                    for session in sessions:
                        if session['action'] == 'login':
                            result = self.player_processor.process_login(session)
                            try:
                                steam_id = session.get('steam_id')
                                if steam_id:
                                    self._check_and_trigger_pending_teleport(steam_id)
                            except Exception as e:
                                print(f"Erro ao verificar teleportes pendentes no login: {e}")
                        elif session['action'] == 'logout':
                            result = self.player_processor.process_logout(session)
                        else:
                            result = {'error': f'Unknown action: {session["action"]}'}
                    
                    # Inserir no banco
                    success_count = self.db_manager.insert_batch_sessions(sessions)
                    
                    if success_count > 0:
                        self.stats['total_sessions'] += success_count
                        # logger.debug(f"{success_count} sessões inseridas no banco")
                        # Disparar atualização imediata do monitor de jogadores online
                        try:
                            requests.get('http://127.0.0.1:3000/api/players/online?force_check=true', timeout=2)
                        except Exception:
                            pass
                    else:
                        print("   AVISO Nenhuma sessão inserida")
                        self.stats['errors'] += 1
            
            # Verificar admin log mais recente após qualquer mudança
            if self.admin_log_processor:
                self._check_latest_admin_log()
            
            # Verificar vehicle destruction log mais recente após qualquer mudança
            if self.vehicle_destruction_processor:
                self._check_latest_vehicle_destruction_log()
            
        except Exception as e:
            print(f"ERRO Erro ao processar mudanças no arquivo: {e}")
            self.stats['errors'] += 1

    def _process_famepoints_file(self, file_path: str):
        """Processar arquivo completo de famepoints."""
        if not self.famepoints_processor:
            return
        if not self._should_process_file(file_path):
            return

        self._mark_file_processing(file_path)
        filename = os.path.basename(file_path)
        # logger.debug(f"Processando arquivo de fama: {filename}")

        try:
            updated = self.famepoints_processor.process_file(file_path)
            print(f"   OK Totais de fama atualizados: {updated}")
        except Exception as e:
            print(f"ERRO Erro ao processar famepoints {filename}: {e}")
            self.stats['errors'] += 1
        finally:
            self._mark_file_processed(file_path)
    
    def _process_economy_file(self, file_path: str):
        """Processar arquivo completo de transações bancárias (economy_*.log)."""
        # OPÇÃO 5: Verificar stop_event ANTES de processar
        if not self.running or self.stop_event.is_set():
            return
        
        temp_path = None
        is_temp_file = False  # Indica se file_path já é um arquivo temporário
        if not self.bank_transaction_processor:
            print(f"   AVISO BankTransactionProcessor não disponível")
            return
        
        # Verificar se file_path já é um arquivo temporário (vindo da cópia periódica)
        if "temp" in file_path and os.path.basename(os.path.dirname(file_path)) == "temp":
            is_temp_file = True
            # Se já é temp, usar diretamente (não precisa copiar novamente)
            temp_path = file_path
            # Obter file_path original para marcação
            # Como não temos referência direta, vamos tentar encontrar pelo nome
            filename = os.path.basename(file_path)
            # Remover sufixo de timestamp do nome temporário: economy_2025.01.01-00.00.00_1234567890.log
            original_filename = "_".join(filename.split("_")[:-1]) + ".log"
            if not original_filename.startswith("economy_"):
                original_filename = filename  # Fallback
            file_path = os.path.join(self.log_directory, original_filename)
        else:
            # Verificar se deve processar (apenas para arquivos originais)
            if not self._should_process_file(file_path):
                return
            filename = os.path.basename(file_path)

        self._mark_file_processing(file_path)
        if not is_temp_file:
            filename = os.path.basename(file_path)
        # logger.debug(f"Processando arquivo de economia: {filename}")

        try:
            # Verificar se arquivo existe
            if not os.path.exists(temp_path if is_temp_file else file_path):
                print(f"   AVISO Arquivo não encontrado")
                return
            
            # Copiar para temp apenas se não for um arquivo temporário já
            if not is_temp_file:
                # SEMPRE copiar arquivo para temp (mesmo se estiver em uso pelo SCUM)
                temp_path = self.temp_manager.create_temp_copy(file_path)
                if not temp_path:
                    print(f"   ERRO Falha ao copiar arquivo para temp")
                    return
            else:
                print(f"   INFO Processando arquivo temporário já copiado: {filename}")
            
            # Processar arquivo temporário diretamente (ele já gerencia suas próprias transações)
            # Retirado da fila de escrita para evitar bloquear outros processos menores (login/logout)
            stats = self.bank_transaction_processor.process_file(temp_path)
            # logger.debug(f"Transações encontradas: {stats['transactions_found']}, Inseridas: {stats['transactions_inserted']}, Linhas processadas: {stats['lines_processed']}")
            if stats['errors'] > 0:
                print(f"   AVISO Erros durante processamento: {stats['errors']}")
            self.stats['files_processed'] += 1
        except Exception as e:
            print(f"ERRO Erro ao processar economy {filename}: {e}")
            import traceback
            traceback.print_exc()
            self.stats['errors'] += 1
        finally:
            # Limpar arquivo temporário apenas se nós criamos (não limpar se veio da cópia periódica)
            # A cópia periódica cuida da limpeza
            if not is_temp_file and temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
            self._mark_file_processed(file_path)

    def _process_famepoints_lines(self, filename: str, new_lines: List[str]):
        """Processar novas linhas de um arquivo famepoints monitorado em tempo real."""
        if not self.famepoints_processor:
            return

        try:
            updated = self.famepoints_processor.process_lines(filename, new_lines)
            if updated:
                print(f"   OK Totais de fama atualizados (tempo real): {updated}")
        except Exception as e:
            print(f"ERRO Erro ao processar famepoints em tempo real ({filename}): {e}")
            self.stats['errors'] += 1
    
    def _process_chat_file(self, file_path: str):
        """Processar arquivo de chat completo"""
        try:
            if not self.chat_processor:
                return
            
            # Verificar deduplicação
            if not self._should_process_file(file_path):
                return
            
            # Marcar como sendo processado
            self._mark_file_processing(file_path)
            
            filename = os.path.basename(file_path)
            # logger.debug(f"Processando arquivo de chat: {filename}")
            
            # Usar o ChatProcessor para processar o arquivo
            stats = self.chat_processor.process_file(file_path)
            
            if stats['messages_sent'] > 0:
                print(f"   OK {stats['messages_sent']} mensagens de chat enviadas")
            else:
                print(f"   INFO {stats['messages_found']} mensagens encontradas, {stats['messages_sent']} enviadas")
            
            # Marcar arquivo como processado
            self._mark_file_processed(file_path)
                
        except Exception as e:
            print(f"ERRO Erro ao processar arquivo de chat: {e}")
    
    def _process_chat_lines(self, filename: str, lines: List[str]):
        """Processar linhas de chat em tempo real"""
        try:
            if not self.chat_processor:
                return
            
            # Para arquivos modificados, não verificar se já foi processado
            # pois estamos processando apenas as novas linhas
            file_path = os.path.join(self.log_directory, filename)
            
            # Marcar como sendo processado
            self._mark_file_processing(file_path)
            
            print(f"CHAT Processando linhas de chat: {filename}")
            print(f"   Novas linhas: {len(lines)}")
            
            # Processar cada linha com ChatProcessor
            for idx, line in enumerate(lines, 1):
                raw = (line or "").strip()
                if raw:
                    # Executar comandos (/vbuy) usando o MESMO fluxo que já leu as linhas
                    if self.chat_command_monitor:
                        try:
                            self.chat_command_monitor._process_chat_line(
                                line=raw,
                                filename=str(filename),
                                virtual_line_no=int(idx),
                            )
                        except Exception:
                            pass

                    chat_data = self.chat_processor.parse_chat_line(raw)
                    if chat_data:
                        if not self.chat_processor.should_send_channel(chat_data.get('channel')):
                            continue
                        # Gerar hash da mensagem
                        channel_value = chat_data.get('channel') or ""
                        if channel_value:
                            message_hash = self.chat_processor.generate_message_hash_with_channel(
                                chat_data['timestamp'],
                                chat_data['steam_id'],
                                channel_value,
                                chat_data['message']
                            )
                        else:
                            message_hash = self.chat_processor.generate_message_hash(
                                chat_data['timestamp'],
                                chat_data['steam_id'],
                                chat_data['message']
                            )
                        
                        # Verificar se já foi processada
                        if message_hash not in self.chat_processor.processed_messages:
                            # Enviar para Discord
                            success = self.chat_processor.notifier.send_chat_message(
                                chat_data['player_name'],
                                chat_data['message'],
                                channel=chat_data.get('channel')
                            )
                            
                            if success:
                                # Marcar como processada
                                self.chat_processor.processed_messages.add(message_hash)
                                self.chat_processor.save_processed_messages()
                                print(f"   OK Mensagem enviada: {chat_data['player_name']}: {chat_data['message'][:50]}...")
                            else:
                                print(f"   ERRO Falha ao enviar mensagem: {chat_data['player_name']}: {chat_data['message'][:50]}...")
                        else:
                            print(f"   INFO Mensagem já processada: {chat_data['player_name']}: {chat_data['message'][:50]}...")
            
            # Marcar arquivo como processado
            self._mark_file_processed(file_path)
                            
        except Exception as e:
            print(f"ERRO Erro ao processar linhas de chat {filename}: {e}")
    
    def _process_chest_ownership_lines(self, filename: str, lines: List[str]):
        """Processar linhas de logs de chest ownership"""
        try:
            if not self.vehicle_processor:
                print(f"ERRO VehicleProcessor não disponível para processar {filename}")
                raise Exception(f"VehicleProcessor não disponível para processar {filename}")
            
            # Processar apenas as novas linhas (incremental)
            print(f"VEÍCULOS Processando logs de chest ownership: {filename}")
            print(f"   Novas linhas recebidas: {len(lines)}")
            try:
                if self.logger:
                    self.logger.info(
                        "[VEHICLE_REGISTRATION] Processing chest_ownership lines",
                        {"file": str(filename), "lines": int(len(lines))},
                    )
            except Exception:
                pass
            
            if not lines:
                print(f"AVISO Nenhuma linha para processar em {filename}")
                return
            
            # Processar apenas as novas linhas diretamente
            vehicle_claims = self.vehicle_processor.parse_lines(lines)
            
            # Contar transferências
            transfers = [v for v in vehicle_claims if v.get('ownership_type') == 'changed']
            claims = [v for v in vehicle_claims if v.get('ownership_type') == 'claimed']
            
            print(f"VEÍCULOS {filename}: {len(vehicle_claims)} veículos encontrados após parsing")
            try:
                if self.logger:
                    self.logger.info(
                        "[VEHICLE_REGISTRATION] Parsed vehicle claims",
                        {
                            "file": str(filename),
                            "vehicle_claims": int(len(vehicle_claims)),
                            "transfers": int(len(transfers)),
                            "claims": int(len(claims)),
                        },
                    )
            except Exception:
                pass

            if not vehicle_claims:
                try:
                    if self.logger:
                        sample_lines = []
                        for line in (lines[:3] if isinstance(lines, list) else []):
                            try:
                                sample_lines.append(str(line)[:300])
                            except Exception:
                                continue
                        self.logger.info(
                            "[VEHICLE_REGISTRATION] Raw chest_ownership sample (no vehicles parsed)",
                            {"file": str(filename), "sample": sample_lines, "lines": int(len(lines))},
                        )
                except Exception:
                    pass
            if transfers:
                print(f"   → {len(transfers)} transferência(s) detectada(s)")
            if claims:
                print(f"   → {len(claims)} registro(s) novo(s) detectado(s)")
            
            if vehicle_claims:
                # logger.debug(f"Veículos encontrados: {len(vehicle_claims)}")
                
                # Inserir no banco
                print(f"VEÍCULOS {filename}: Inserindo {len(vehicle_claims)} veículos no banco...")
                success_count = self.db_manager.insert_batch_vehicle_ownership(vehicle_claims)
                
                print(f"VEÍCULOS {filename}: {success_count} veículos inseridos com sucesso")
                try:
                    if self.logger:
                        self.logger.info(
                            "[VEHICLE_REGISTRATION] DB insert result",
                            {
                                "file": str(filename),
                                "attempted": int(len(vehicle_claims)),
                                "inserted": int(success_count),
                            },
                        )
                except Exception:
                    pass
                
                if success_count > 0:
                    print(f"   OK {success_count} veículos inseridos no banco")
                    
                    # Enviar notificações Discord
                    if self.vehicle_notifier:
                        for vehicle_data in vehicle_claims:
                            try:
                                raw_line = vehicle_data.get("raw_line")
                                if isinstance(raw_line, str) and raw_line.strip():
                                    event_key = hashlib.sha1(raw_line.strip().encode("utf-8", errors="ignore")).hexdigest()
                                else:
                                    event_key = hashlib.sha1(
                                        f"{vehicle_data.get('entity_id')}|{vehicle_data.get('ownership_type')}|{vehicle_data.get('timestamp')}".encode(
                                            "utf-8", errors="ignore"
                                        )
                                    ).hexdigest()

                                is_new_event = False
                                try:
                                    is_new_event = bool(
                                        self.db_manager.register_vehicle_notification_event(
                                            event_key,
                                            entity_id=vehicle_data.get("entity_id"),
                                            ownership_type=vehicle_data.get("ownership_type"),
                                            event_timestamp=vehicle_data.get("timestamp"),
                                        )
                                    )
                                except Exception:
                                    is_new_event = False

                                if not is_new_event:
                                    continue

                                # Verificar se já foi notificado
                                if not self._should_send_vehicle_notification(vehicle_data):
                                    continue
                                
                                # Enviar notificação
                                notification_sent = self.vehicle_notifier.send_vehicle_notification(vehicle_data)
                                try:
                                    if self.logger:
                                        self.logger.info(
                                            "[VEHICLE_REGISTRATION] Discord notification attempted",
                                            {
                                                "sent": bool(notification_sent),
                                                "entity_id": int(vehicle_data.get("entity_id") or 0),
                                                "ownership_type": str(vehicle_data.get("ownership_type") or ""),
                                                "steam_id": str(vehicle_data.get("steam_id") or ""),
                                                "player_name": str(vehicle_data.get("player_name") or ""),
                                            },
                                        )
                                except Exception:
                                    pass
                                
                                if notification_sent:
                                    # Marcar como notificado
                                    self.db_manager.mark_vehicle_notification_sent(
                                        vehicle_data['entity_id'], 
                                        vehicle_data['ownership_type']
                                    )
                                    
                            except Exception as e:
                                print(f"ERRO Erro ao enviar notificação de veículo: {e}")
                                try:
                                    if self.logger:
                                        self.logger.error(
                                            f"[VEHICLE_REGISTRATION] Discord notification error: {e}",
                                            {
                                                "entity_id": int(vehicle_data.get("entity_id") or 0),
                                                "ownership_type": str(vehicle_data.get("ownership_type") or ""),
                                            },
                                        )
                                except Exception:
                                    pass
                else:
                    # Verificar se foi duplicata (esperado) ou erro real
                    # Se todos os veículos foram duplicatas, isso é normal e não deve causar erro
                    # Duplicatas são esperadas quando reprocessamos linhas já processadas
                    print("   INFO Nenhum veículo inserido - provavelmente duplicata (comportamento esperado ao reprocessar)")
                    # Não lançar exceção para duplicatas - isso é comportamento esperado
                    # Não incrementar contador de erros também, pois duplicatas não são erros
            else:
                print("   INFO Nenhum veículo encontrado nas linhas (pode ser linha de versão do jogo)")
                try:
                    if self.logger:
                        self.logger.info(
                            "[VEHICLE_REGISTRATION] No vehicles found in lines",
                            {"file": str(filename), "lines": int(len(lines))},
                        )
                except Exception:
                    pass
                # Não lançar exceção aqui, pois pode ser uma linha de versão do jogo
                
        except Exception as e:
            print(f"ERRO Erro ao processar logs de chest ownership: {e}")
            import traceback
            traceback.print_exc()
            try:
                if self.logger:
                    self.logger.error(
                        f"[VEHICLE_REGISTRATION] Processing error: {e}",
                        {"file": str(filename)},
                    )
            except Exception:
                pass
            self.stats['errors'] += 1
            # Re-lançar exceção para que o contador não seja atualizado
            raise
    
    def _process_admin_log_file(self, file_path: str):
        """Processar arquivo de admin log"""
        temp_path = None
        try:
            if not self.admin_log_processor:
                return
            
            # Para arquivos modificados, não verificar se já foi processado
            # pois estamos processando apenas as novas linhas
            # if not self._should_process_file(file_path):
            #     return
            
            # Marcar como sendo processado
            self._mark_file_processing(file_path)
            
            filename = os.path.basename(file_path)
            # logger.debug(f"Processando arquivo admin: {filename}")
            
            # SEMPRE copiar arquivo para temp (mesmo se estiver em uso pelo SCUM)
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                print(f"   ERRO Falha ao copiar arquivo para temp")
                return
            
            # logger.debug(f"Arquivo copiado para temp: {os.path.basename(temp_path)}")
            
            # Verificar se há novas linhas antes de processar
            has_new_content = self._check_admin_log_for_new_content(temp_path, filename)
            
            if has_new_content:
                print(f"   OK Novas linhas detectadas, processando...")
                # Processar admin log
                success = self.admin_log_processor.process_admin_log(temp_path)
                
                if success:
                    # logger.debug("Admin log processado com sucesso")
                    
                    # Registrar arquivo processado na tabela
                    file_info = os.stat(file_path)
                    self.db_manager.update_file_processing_status(
                        file_name=filename,
                        file_path=file_path,
                        last_position=file_info.st_size,
                        lines_processed=len(content.split('\n')) if 'content' in locals() else 0,  # pyright: ignore[reportUndefinedVariable]
                        status='completed'
                    )
                else:
                    print(f"   ERRO Falha ao processar admin log")
            else:
                # logger.debug("Nenhuma nova linha detectada, ignorando")
                pass
            
            # Marcar arquivo como processado
            self._mark_file_processed(file_path)
            
        except Exception as e:
            print(f"ERRO Erro ao processar admin log: {e}")
        finally:
            # SEMPRE limpar arquivo temporário, mesmo em caso de erro
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def _process_kill_log_file(self, file_path: str):
        """Processar arquivo de kill log"""
        temp_path = None
        try:
            if not self.kill_processor:
                return
            
            # Marcar como sendo processado
            self._mark_file_processing(file_path)
            
            filename = os.path.basename(file_path)
            # logger.debug(f"Processando arquivo de kill: {filename}")
            
            # Copiar arquivo para temp (mesmo se estiver em uso pelo SCUM)
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                print(f"   ERRO Falha ao copiar arquivo para temp")
                return
            
            # logger.debug(f"Arquivo copiado para temp: {os.path.basename(temp_path)}")
            
            # Processar kill log
            result = self.kill_processor.process_kill_log(temp_path)
            
            if result.get('success'):
                processed = result.get('processed', 0)
                skipped = result.get('skipped', 0)
                # logger.debug(f"Kill log processado: {processed} eventos inseridos, {skipped} ignorados (duplicados)")
                
                # Registrar arquivo processado na tabela
                file_info = os.stat(file_path)
                self.db_manager.update_file_processing_status(
                    file_name=filename,
                    file_path=file_path,
                    last_position=file_info.st_size,
                    lines_processed=processed,
                    status='completed'
                )
            else:
                error = result.get('error', 'Erro desconhecido')
                print(f"   ERRO Falha ao processar kill log: {error}")
            
            # Marcar arquivo como processado
            self._mark_file_processed(file_path)
            
        except Exception as e:
            print(f"ERRO Erro ao processar kill log: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # SEMPRE limpar arquivo temporário, mesmo em caso de erro
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def _check_admin_log_for_new_content(self, temp_path: str, filename: str) -> bool:
        """Verificar se há novas linhas no arquivo admin log"""
        try:
            # Ler arquivo temporário
            with open(temp_path, 'r', encoding='utf-16le') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(temp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"   ERRO Erro ao ler arquivo temporário: {e}")
                return False
        
        # Dividir em linhas
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        if not lines:
            return False
        
        # Obter último comando processado
        last_processed_command = self.admin_log_processor._get_last_processed_command()
        
        if not last_processed_command:
            # DEBUG removido para reduzir verbosidade do console
            # print(f"   DEBUG Nenhum comando processado anteriormente - processando todas as linhas")
            return True
        
        # Verificar se há comandos novos
        has_new_commands = False
        for line in lines:
            if not line:
                continue
                
            # Parse da linha para obter command_id
            parsed_data = self.admin_log_processor._parse_admin_line(line)
            if parsed_data and parsed_data.get('command_id'):
                command_id = parsed_data['command_id']
                if command_id != last_processed_command:
                    has_new_commands = True
                    break
        
        if has_new_commands:
            # DEBUG removido para reduzir verbosidade do console
            # print(f"   DEBUG Novos comandos encontrados (último processado: {last_processed_command})")
            return True
        else:
            # DEBUG removido para reduzir verbosidade do console
            # print(f"   DEBUG Nenhum comando novo (último processado: {last_processed_command})")
            return False
            
    def _check_latest_admin_log(self):
        """Verificar e processar o arquivo admin_*.log mais recente"""
        temp_path = None
        try:
            # OPÇÃO 5: Verificar stop_event ANTES de processar (thread-safe)
            if not self.running or self.stop_event.is_set():
                return
            
            if not self.admin_log_processor:
                return
            
            # Encontrar o arquivo admin mais recente
            latest_file = self.admin_log_processor._find_latest_admin_log(self.log_directory)
            if not latest_file:
                return
            
            latest_filename = os.path.basename(latest_file)
            
            # Verificar se é um arquivo novo ou diferente
            if latest_filename != self.last_admin_log_file:
                # logger.debug(f"Novo arquivo admin detectado: {latest_filename}")
                
                # Copiar para temp e processar
                temp_path = self.temp_manager.create_temp_copy(latest_file)
                if temp_path:
                    success = self.admin_log_processor.process_admin_log(temp_path)
                    if success:
                        # logger.debug(f"Admin log processado: {latest_filename}")
                        self.last_admin_log_file = latest_filename
                        
                        # Registrar arquivo processado na tabela
                        file_info = os.stat(latest_file)
                        self.db_manager.update_file_processing_status(
                            file_name=latest_filename,
                            file_path=latest_file,
                            last_position=file_info.st_size,
                            lines_processed=0,  # Admin logs não contam linhas da mesma forma
                            status='completed'
                        )
                    else:
                        print(f"ERRO Falha ao processar admin log: {latest_filename}")
                else:
                    print(f"ERRO Falha ao copiar admin log para temp: {latest_filename}")
            
        except Exception as e:
            print(f"ERRO Erro ao verificar admin log mais recente: {e}")
        finally:
            # SEMPRE limpar arquivo temporário, mesmo em caso de erro
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def _check_latest_vehicle_destruction_log(self):
        """Verificar e processar o arquivo vehicle_destruction_*.log mais recente"""
        try:
            # OPÇÃO 5: Verificar stop_event ANTES de processar (thread-safe)
            if not self.running or self.stop_event.is_set():
                return
            
            if not self.vehicle_destruction_processor:
                return
            
            # Encontrar o arquivo vehicle_destruction mais recente
            latest_file = self._find_latest_vehicle_destruction_log()
            if not latest_file:
                return
            
            latest_filename = os.path.basename(latest_file)
            
            # OPÇÃO 5: Verificar stop_event novamente antes de processar
            if not self.running or self.stop_event.is_set():
                return
            
            # Verificar se é um arquivo novo ou diferente
            if latest_filename != self.last_vehicle_destruction_log_file:
                # logger.debug(f"Novo arquivo de destruição de veículos detectado: {latest_filename}")
                
                # Copiar para temp e processar
                temp_path = self.temp_manager.create_temp_copy(latest_file)
                if temp_path:
                    # OPÇÃO 5: Verificar stop_event uma última vez antes de processar
                    if not self.running or self.stop_event.is_set():
                        self.temp_manager.cleanup_temp_file(temp_path)
                        return
                    success = self.vehicle_destruction_processor.process_vehicle_destruction_log(temp_path)
                    if success:
                        print(f"OK Vehicle destruction log processado: {latest_filename}")
                        self.last_vehicle_destruction_log_file = latest_filename
                    else:
                        print(f"ERRO Falha ao processar vehicle destruction log: {latest_filename}")
                    
                    # Limpar arquivo temporário
                    self.temp_manager.cleanup_temp_file(temp_path)
                else:
                    print(f"ERRO Falha ao copiar vehicle destruction log para temp: {latest_filename}")
            
        except Exception as e:
            print(f"ERRO Erro ao verificar vehicle destruction log mais recente: {e}")
    
    def _find_latest_vehicle_destruction_log(self):
        """Encontrar o arquivo vehicle_destruction_*.log mais recente"""
        try:
            if not os.path.exists(self.log_directory):
                return None
            
            vehicle_destruction_files = []
            for filename in os.listdir(self.log_directory):
                if filename.startswith('vehicle_destruction_') and filename.endswith('.log'):
                    file_path = os.path.join(self.log_directory, filename)
                    if os.path.isfile(file_path):
                        mtime = os.path.getmtime(file_path)
                        vehicle_destruction_files.append((file_path, mtime))
            
            if not vehicle_destruction_files:
                return None
            
            # Retornar o arquivo mais recente
            latest_file = max(vehicle_destruction_files, key=lambda x: x[1])
            return latest_file[0]
            
        except Exception as e:
            print(f"ERRO Erro ao encontrar vehicle destruction log mais recente: {e}")
            return None
    
    def _process_vehicle_destruction_file(self, file_path: str):
        """Processar arquivo de destruição de veículos"""
        try:
            if not self.vehicle_destruction_processor:
                return
            
            # Para arquivos modificados, não verificar se já foi processado
            # pois estamos processando apenas as novas linhas
            # if not self._should_process_file(file_path):
            #     return
            
            # Marcar como sendo processado
            self._mark_file_processing(file_path)
            
            filename = os.path.basename(file_path)
            # logger.debug(f"Processando arquivo de destruição de veículos: {filename}")
            
            # Copiar arquivo para temp
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                print(f"   ERRO Falha ao copiar arquivo para temp")
                return
            
            # logger.debug(f"Arquivo copiado para temp: {os.path.basename(temp_path)}")
            
            # Processar arquivo de destruição de veículos
            success = self.vehicle_destruction_processor.process_vehicle_destruction_log(temp_path)
            
            if success:
                print(f"   OK Vehicle destruction log processado com sucesso")
            else:
                print(f"   ERRO Falha ao processar vehicle destruction log")
            
            # Marcar arquivo como processado
            self._mark_file_processed(file_path)
            
            # Limpar arquivo temporário
            self.temp_manager.cleanup_temp_file(temp_path)
            
        except Exception as e:
            print(f"ERRO Erro ao processar vehicle destruction log: {e}")
    
    def _should_send_vehicle_notification(self, vehicle_data: Dict[str, Any]) -> bool:
        """Verificar se deve enviar notificação para o veículo"""
        try:
            entity_id = vehicle_data['entity_id']
            ownership_type = vehicle_data['ownership_type']
            
            # Verificar se já foi notificado recentemente para este entity_id
            recent_notifications = self.db_manager.get_vehicle_ownership_history(
                entity_id=entity_id, 
                limit=1
            )
            
            if recent_notifications:
                last_notification = recent_notifications[0]
                if last_notification.get('notification_sent'):
                    # Verificar tempo desde última notificação
                    last_time = datetime.fromisoformat(last_notification['timestamp'])
                    time_diff = datetime.now() - last_time
                    
                    # Só notificar se passou mais de 1 hora
                    return time_diff.total_seconds() > 3600
            
            # Se não há notificações anteriores, enviar
            return True
            
        except Exception as e:
            print(f"ERRO Erro ao verificar notificação de veículo: {e}")
            return True  # Em caso de erro, enviar notificação
    
    def _process_chest_ownership_file(self, file_path: str):
        """Processar arquivo completo de chest ownership usando arquivo temporário"""
        temp_path = None
        try:
            filename = os.path.basename(file_path)
            
            # Verificar deduplicação
            if not self._should_process_file(file_path):
                return
            
            # Marcar como sendo processado
            self._mark_file_processing(file_path)
            
            # logger.debug(f"Processando arquivo de veículos: {filename}")
            
            # Criar cópia temporária para evitar bloqueio
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                print(f"ERRO Falha ao criar cópia temporária: {filename}")
                return
            
            # Obter informações do arquivo
            file_info = self.file_scanner.get_file_info(file_path)
            
            # Processar arquivo temporário
            vehicle_claims = self.vehicle_processor.parse_file(temp_path)
            # logger.debug(f"{len(vehicle_claims)} veículos encontrados no arquivo {filename}")
            
            if vehicle_claims:
                # Inserir no banco
                success_count = self.db_manager.insert_batch_vehicle_ownership(vehicle_claims)
                
                if success_count > 0:
                    self.stats['files_processed'] += 1
                    self.processed_files.add(filename)
                    
                    # Atualizar status de processamento do arquivo
                    self.db_manager.update_file_processing_status(
                        file_name=filename,
                        file_path=file_path,
                        last_position=file_info['file_size'],
                        lines_processed=len(vehicle_claims),
                        status='completed'
                    )
                    
                    print(f"   OK {success_count} veículos inseridos")
                    
                    # Enviar notificações Discord
                    if self.vehicle_notifier:
                        for vehicle_data in vehicle_claims:
                            try:
                                # Verificar se já foi notificado
                                if not self._should_send_vehicle_notification(vehicle_data):
                                    continue
                                
                                # Enviar notificação
                                notification_sent = self.vehicle_notifier.send_vehicle_notification(vehicle_data)
                                
                                if notification_sent:
                                    # Marcar como notificado
                                    self.db_manager.mark_vehicle_notification_sent(
                                        vehicle_data['entity_id'], 
                                        vehicle_data['ownership_type']
                                    )
                                    
                            except Exception as e:
                                print(f"ERRO Erro ao enviar notificação de veículo: {e}")
                else:
                    print("   AVISO Nenhum veículo inserido")
                    self.stats['errors'] += 1
            else:
                print("   INFO Nenhum veículo encontrado no arquivo")
                
                # Marcar arquivo como processado mesmo sem veículos
                self.db_manager.update_file_processing_status(
                    file_name=filename,
                    file_path=file_path,
                    last_position=file_info['file_size'],
                    lines_processed=0,
                    status='completed'
                )
            
            # Marcar arquivo como processado no sistema de deduplicação
            self._mark_file_processed(file_path)
            
        except Exception as e:
            print(f"ERRO Erro ao processar arquivo de veículos: {e}")
            self.stats['errors'] += 1
        finally:
            # Limpar arquivo temporário
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def _process_file(self, file_path: str):
        """Processar arquivo completo usando arquivo temporário"""
        temp_path = None
        try:
            filename = os.path.basename(file_path)
            
            # Verificar se arquivo deve ser processado (não duplicado)
            if not self._should_process_file(file_path):
                return
            
            # Marcar como sendo processado
            self._mark_file_processing(file_path)
            
            # logger.debug(f"Processando arquivo de login: {filename}")
            
            # Criar cópia temporária para evitar bloqueio
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                print(f"ERRO Falha ao criar cópia temporária: {filename}")
                self._mark_file_processed(file_path)
                return
            
            # logger.debug(f"Arquivo copiado para temp: {os.path.basename(temp_path)}")
            
            # Obter informações do arquivo
            file_info = self.file_scanner.get_file_info(file_path)
            
            # Processar arquivo temporário
            sessions = self.parser.parse_file(temp_path)
            # DEBUG removido para reduzir verbosidade do console
            # print(f"DEBUG: {len(sessions)} sessões encontradas no arquivo {filename}")
            
            if sessions:
                # Processar cada sessão com PlayerProcessor
                processed_sessions = []
                # DEBUG removido para reduzir verbosidade do console
                # print(f"DEBUG: Processando {len(sessions)} sessões com PlayerProcessor...")
                for i, session in enumerate(sessions):
                    try:
                        # DEBUG removido para reduzir verbosidade do console
                        # print(f"DEBUG: Processando sessão {i+1}: {session['player_name']} - {session['action']}")
                        # print(f"DEBUG: Dados da sessão: {session}")
                        
                        if session['action'] == 'login':
                            # DEBUG removido para reduzir verbosidade do console
                            # print(f"DEBUG: Chamando process_login...")
                            result = self.player_processor.process_login(session)
                            try:
                                steam_id = session.get('steam_id')
                                if steam_id:
                                    self._check_and_trigger_pending_teleport(steam_id)
                            except Exception as e:
                                print(f"Erro ao verificar teleportes pendentes no login: {e}")
                            # DEBUG removido para reduzir verbosidade do console
                            # print(f"PlayerProcessor login result: {result}")
                        elif session['action'] == 'logout':
                            # DEBUG removido para reduzir verbosidade do console
                            # print(f"DEBUG: Chamando process_logout...")
                            result = self.player_processor.process_logout(session)
                            # DEBUG removido para reduzir verbosidade do console
                            # print(f"PlayerProcessor logout result: {result}")
                        else:
                            # DEBUG removido para reduzir verbosidade do console
                            # print(f"DEBUG: Ação desconhecida: {session['action']}")
                            result = {'error': f'Unknown action: {session["action"]}'}
                        
                        processed_sessions.append(result)
                        # DEBUG removido para reduzir verbosidade do console
                        # print(f"DEBUG: Sessão processada com sucesso")
                        
                    except Exception as e:
                        print(f"ERRO no PlayerProcessor: {e}")
                        import traceback
                        traceback.print_exc()
                        result = {'error': str(e)}
                        processed_sessions.append(result)
                
                # Inserir no banco
                success_count = self.db_manager.insert_batch_sessions(sessions)
                
                if success_count > 0:
                    self.stats['total_sessions'] += success_count
                    self.stats['files_processed'] += 1
                    
                    # Atualizar status de processamento do arquivo
                    self.db_manager.update_file_processing_status(
                        file_name=filename,
                        file_path=file_path,
                        last_position=file_info['file_size'],
                        lines_processed=len(sessions),
                        status='completed'
                    )
                    
                    # logger.debug(f"{success_count} sessões inseridas")
                else:
                    print("   AVISO Nenhuma sessão inserida")
                    self.stats['errors'] += 1
            else:
                # logger.debug("Nenhuma sessão encontrada no arquivo")
                
                # Marcar arquivo como processado mesmo sem sessões
                self.db_manager.update_file_processing_status(
                    file_name=filename,
                    file_path=file_path,
                    last_position=file_info['file_size'],
                    lines_processed=0,
                    status='completed'
                )
            
        except Exception as e:
            print(f"ERRO Erro ao processar arquivo: {e}")
            import traceback
            traceback.print_exc()
            self.stats['errors'] += 1
        finally:
            # Marcar arquivo como processado (mesmo em caso de erro)
            self._mark_file_processed(file_path)
            
            # Limpar arquivo temporário
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
                # logger.debug(f"Arquivo temporário removido: {os.path.basename(temp_path)}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do processamento"""
        stats = self.stats.copy()
        
        # Adicionar estatísticas do banco
        db_stats = self.db_manager.get_database_stats()
        stats.update(db_stats)
        
        # Adicionar status do monitoramento
        if self.file_monitor:
            monitor_status = self.file_monitor.get_monitoring_status()
            stats['monitoring'] = monitor_status
        
        # Calcular tempo de execução
        if stats['start_time']:
            stats['runtime_seconds'] = (datetime.now() - stats['start_time']).total_seconds()
        
        return stats
    
    def get_recent_logins(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obter logins recentes"""
        return self.db_manager.get_recent_logins(limit)
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Limpar dados antigos"""
        return self.db_manager.cleanup_old_data(days_to_keep)
    
    def test_processing(self, file_path: str) -> Dict[str, Any]:
        """Testar processamento de arquivo específico"""
        try:
            print(f"🧪 Testando processamento: {os.path.basename(file_path)}")
            
            # Verificar se arquivo existe
            if not os.path.exists(file_path):
                return {'success': False, 'error': 'Arquivo não encontrado'}
            
            # Processar arquivo
            sessions = self.parser.parse_file(file_path)
            
            if not sessions:
                return {'success': False, 'error': 'Nenhuma sessão encontrada'}
            
            # Validar sessões
            valid_sessions = []
            for session in sessions:
                if self.parser.validate_session_data(session):
                    valid_sessions.append(session)
            
            return {
                'success': True,
                'file_path': file_path,
                'total_sessions': len(sessions),
                'valid_sessions': len(valid_sessions),
                'sessions': valid_sessions[:10]  # Primeiras 10 para preview
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_parser_info(self) -> Dict[str, Any]:
        """Obter informações do parser"""
        return self.parser.get_parser_stats()
    
    def get_players_summary(self) -> Dict[str, Any]:
        """Obter resumo dos jogadores"""
        return self.player_processor.get_players_summary()
    
    def get_active_sessions(self) -> Dict[str, Any]:
        """Obter sessões ativas"""
        return self.player_processor.get_active_sessions()
    
    def cleanup_inactive_sessions(self, timeout_hours: int = 24) -> int:
        """Limpar sessões inativas"""
        return self.player_processor.cleanup_inactive_sessions(timeout_hours)
    
    def get_processed_files_stats(self) -> Dict[str, Any]:
        """Obter estatísticas dos arquivos processados"""
        try:
            with DatabaseConnector.get_connection(self.db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                
                # Total de arquivos processados
                cursor.execute("SELECT COUNT(*) FROM log_files_processed")
                total_files = cursor.fetchone()[0]
                
                # Arquivos por status
                cursor.execute("SELECT status, COUNT(*) FROM log_files_processed GROUP BY status")
                files_by_status = dict(cursor.fetchall())
                
                # Últimos arquivos processados
                cursor.execute("""
                    SELECT file_name, lines_processed, status, updated_at 
                    FROM log_files_processed 
                    ORDER BY updated_at DESC 
                    LIMIT 10
                """)
                recent_files = cursor.fetchall()
                
                return {
                    'total_files': total_files,
                    'files_by_status': files_by_status,
                    'recent_files': [
                        {
                            'file_name': row[0],
                            'lines_processed': row[1],
                            'status': row[2],
                            'updated_at': row[3]
                        }
                        for row in recent_files
                    ]
                }
                
        except Exception as e:
            print(f"ERRO Erro ao obter estatísticas de arquivos processados: {e}")
            return {}
    
    def _process_gameplay_lines(self, filename: str, file_path: str, lines: List[str]):
        """Processar apenas novas linhas de gameplay (processamento incremental)"""
        try:
            if not self.gameplay_parser:
                print(f"ERRO GameplayParser não disponível para processar {filename}")
                raise Exception(f"GameplayParser não disponível para processar {filename}")
            
            # Processar apenas as novas linhas diretamente
            print(f"GAMEPLAY Processando logs de gameplay: {filename}")
            print(f"   Novas linhas recebidas: {len(lines)}")
            
            if not lines:
                print(f"AVISO Nenhuma linha para processar em {filename}")
                return
            
            # Processar apenas as novas linhas diretamente
            minigame_events = self.gameplay_parser.parse_minigame_events_from_lines(lines, file_path)
            trap_events = []
            try:
                trap_events = self.gameplay_parser.parse_trap_events_from_lines(lines, file_path)
            except Exception as e:
                print(f"AVISO Erro ao fazer parsing de LogTrap: {e}")
                trap_events = []

            try:
                if trap_events:
                    first_line = str(trap_events[0].get("log_line") or "").strip() if isinstance(trap_events[0], dict) else ""
                    print(f"MINES_ALERTS DEBUG: {len(trap_events)} trap event(s) parseados. Primeiro: {first_line}")
            except Exception:
                pass
            
            print(f"GAMEPLAY {filename}: {len(minigame_events)} eventos encontrados após parsing")

            if trap_events:
                try:
                    self._process_trap_events(trap_events)
                except Exception as e:
                    print(f"AVISO Erro ao processar trap events: {e}")
                    import traceback
                    traceback.print_exc()
            
            if minigame_events:
                # Estatísticas antes de inserir
                lockpicking_total = sum(1 for e in minigame_events if e.get('minigame_type') == 'LockpickingMinigame_C')
                lockpicking_fails = sum(1 for e in minigame_events if e.get('minigame_type') == 'LockpickingMinigame_C' and e.get('success') is False)
                lockpicking_with_owner = sum(1 for e in minigame_events if e.get('minigame_type') == 'LockpickingMinigame_C' and e.get('owner_id') is not None)
                
                if lockpicking_total > 0:
                    print(f"   └─ LockpickingMinigame_C: {lockpicking_total} eventos ({lockpicking_fails} falhas, {lockpicking_with_owner} com proprietário)")
                
                # Inserir eventos no banco (já tem verificação de duplicatas)
                inserted_count = self.db_manager.insert_batch_minigame_events(minigame_events)
                print(f"GAMEPLAY {filename}: {inserted_count} eventos inseridos no banco")
                
                if inserted_count > 0:
                    # Enviar notificações para eventos de LockpickingMinigame_C COM PROPRIETÁRIO
                    if self.minigame_notifier:
                        try:
                            # Filtrar apenas LockpickingMinigame_C E que tenham proprietário identificado
                            # Não filtrar por success - enviar ambos sucessos e falhas
                            lockpicking_events = [
                                event for event in minigame_events 
                                if event.get('minigame_type', '').startswith('LockpickingMinigame_C')
                                and event.get('owner_id') is not None
                                and event.get('owner_steam_id') is not None
                                and event.get('owner_name') is not None
                            ]
                            
                            if lockpicking_events:
                                # Enviar notificações (global + pessoal) com deduplicação robusta
                                for event in lockpicking_events:
                                    self._send_lockpicking_notifications(event)
                                
                                print(f"GAMEPLAY {filename}: {len(lockpicking_events)} notificações enviadas para Discord")
                        except Exception as e:
                            print(f"AVISO Erro ao enviar notificações de minigame: {e}")
                            import traceback
                            traceback.print_exc()
                else:
                    print(f"   INFO Nenhum evento inserido - provavelmente duplicata (comportamento esperado)")
            else:
                print(f"   INFO Nenhum evento encontrado nas linhas")
                
        except Exception as e:
            print(f"ERRO Erro ao processar linhas de gameplay: {e}")
            import traceback
            traceback.print_exc()
            self.stats['errors'] += 1
            raise
    def _process_trap_events(self, trap_events: List[Dict[str, Any]]) -> None:
        try:
            if not trap_events:
                return

            # Recarregar configuração do config.json dinamicamente para aplicar alterações da UI/API
            try:
                self.config = self._load_config()
            except Exception:
                pass

            webhook_name = "mines_alerts"

            # Se não tiver DiscordWebhook disponível, não enviar
            if not self.discord_webhook:
                return

            # Configuração do raio (em units do SCUM)
            mines_cfg = self.config.get("mines_alerts") if isinstance(self.config, dict) else None
            if not isinstance(mines_cfg, dict):
                mines_cfg = {}
            radius_units = mines_cfg.get("flag_radius_units")
            try:
                radius_units_f = float(radius_units) if radius_units is not None else 10000.0
            except Exception:
                radius_units_f = 10000.0

            tol_units = mines_cfg.get("flag_radius_tolerance_units")
            try:
                tol_units_f = float(tol_units) if tol_units is not None else 600.0
            except Exception:
                tol_units_f = 600.0
            effective_radius = radius_units_f + max(0.0, tol_units_f)

            # Carregar flags do SCUM.db
            flags: List[Dict[str, Any]] = []
            scum_db_path_used = None
            db_query_success = False
            try:
                from utils.config_path_helper import ConfigPathHelper
                from core.squads.squad_sync_service import SquadSyncService

                path_helper = ConfigPathHelper(self.config)
                svc = SquadSyncService(self.config, path_helper, logger=self.logger)
                scum_db_path_used = getattr(svc, "scum_db_path", None)
                flags_resp = svc.get_all_flags_with_locations()
                if isinstance(flags_resp, dict) and flags_resp.get("success") is True:
                    db_query_success = True
                    raw_flags = flags_resp.get("flags")
                    if isinstance(raw_flags, list):
                        flags = raw_flags
                else:
                    try:
                        print(
                            f"MINES_ALERTS AVISO: Falha ao carregar flags (success != True). scum_db_path={scum_db_path_used}. resp_error={flags_resp.get('error') if isinstance(flags_resp, dict) else flags_resp}"
                        )
                    except Exception:
                        pass
            except Exception as e:
                try:
                    print(f"MINES_ALERTS AVISO: Exceção ao carregar flags do SCUM.db. scum_db_path={scum_db_path_used}. error={e}")
                except Exception:
                    pass
                flags = []

            # Segurança: se falhar na consulta ao banco de dados, não dispare alerta (evita falso-positivo)
            if not db_query_success:
                try:
                    print(
                        f"MINES_ALERTS AVISO: Falha ao carregar banco de dados de flags - ignorando trap events para evitar falso-positivo (scum_db_path={scum_db_path_used})"
                    )
                except Exception:
                    pass
                return

            for ev in trap_events:
                try:
                    sig = self._mines_alert_signature(ev)
                except Exception:
                    sig = None

                if sig:
                    if sig in self._mines_alerts_sent_sigs:
                        continue
                    try:
                        self._mines_alerts_sent_sigs.add(sig)
                        self._save_mines_alerts_sent_signatures(self._mines_alerts_sent_sigs)
                    except Exception:
                        pass

                try:
                    x = float(ev.get("location_x"))
                    y = float(ev.get("location_y"))
                    z = float(ev.get("location_z"))
                except Exception:
                    continue

                player_name = str(ev.get("player_name") or "Unknown").strip()
                steam_id = str(ev.get("steam_id") or "").strip()
                trap_name = str(ev.get("trap_name") or "").strip()

                # Dentro de alguma bandeira? (se não houver flags, consideramos fora)
                inside_any = False
                min_dist = None
                if flags:
                    for f in flags:
                        try:
                            loc = f.get("location") if isinstance(f, dict) else None
                            if not isinstance(loc, dict):
                                continue
                            fx = float(loc.get("x"))
                            fy = float(loc.get("y"))
                        except Exception:
                            continue
                        d = math.hypot(x - fx, y - fy)
                        if min_dist is None or d < min_dist:
                            min_dist = d
                        if d <= effective_radius:
                            inside_any = True
                            break

                is_illegal = not inside_any

                # Inserir mina implantada no banco
                mine_id = None
                try:
                    mine_data = {
                        'steam_id': steam_id,
                        'player_name': player_name,
                        'trap_name': trap_name,
                        'location_x': x,
                        'location_y': y,
                        'location_z': z,
                        'is_illegal': is_illegal,
                        'status': 'active',
                        'teleport_executed': False,
                        'fine_executed': False
                    }
                    self.db_manager.insert_deployed_mine(mine_data)
                except Exception as e:
                    print(f"MINES_ALERTS ERRO: Falha ao registrar mina no banco: {e}")

                if not is_illegal:
                    try:
                        if min_dist is not None:
                            print(f"MINES_ALERTS INFO: Mina dentro do raio de uma flag (min_dist={min_dist:.2f} <= {effective_radius:.2f}) - registrada no banco como legal")
                    except Exception:
                        pass
                    continue

                # A partir daqui, a mina é ilegal
                try:
                    if min_dist is not None:
                        print(f"MINES_ALERTS INFO: Mina fora de todas as flags (min_dist={min_dist:.2f} > {effective_radius:.2f}) - iniciando punições e alerta")
                except Exception:
                    pass

                # 1. Aplicar multa se habilitado
                wallet_fine_enabled = mines_cfg.get("wallet_fine_enabled", False)
                if wallet_fine_enabled and steam_id:
                    try:
                        fine_amount = int(mines_cfg.get("wallet_fine_amount", 1000))
                        from core.shop.wallet_service import WalletService
                        wallet_svc = WalletService(self.db_path)
                        # Aplicar débito
                        wallet_svc.apply_delta(
                            steam_id=steam_id,
                            delta=-abs(fine_amount),
                            reason=f"Multa por implantar mina ilegal em {x:.1f}, {y:.1f}, {z:.1f}",
                            ref_type="illegal_mine",
                            ref_id=f"{x:.1f}_{y:.1f}",
                            allow_negative=True
                        )
                        print(f"MINES_ALERTS: Aplicado multa de {fine_amount} ao jogador {steam_id}")
                    except Exception as e:
                        print(f"MINES_ALERTS ERRO: Falha ao aplicar multa de carteira: {e}")

                # 2. Agendar teleporte se habilitado
                teleport_punishment_enabled = mines_cfg.get("teleport_punishment_enabled", False)
                if teleport_punishment_enabled and steam_id:
                    try:
                        delay_seconds = float(mines_cfg.get("teleport_punishment_delay_seconds", 5.0))
                        cursor = self.db_manager.execute_query(
                            "SELECT id FROM deployed_mines WHERE steam_id = ? AND location_x = ? AND location_y = ? ORDER BY id DESC LIMIT 1",
                            (steam_id, x, y)
                        )
                        mine_id = cursor[0][0] if cursor else None
                        if mine_id:
                            self._schedule_teleport_punishment(steam_id, mine_id, x, y, z, delay_seconds)
                    except Exception as e:
                        print(f"MINES_ALERTS ERRO: Falha ao agendar teleporte: {e}")

                # 3. Enviar Alerta do Discord
                try:
                    from core.logs.cargo_drop_notifier import CargoDropNotifier
                    quadrant = CargoDropNotifier._world_xy_to_quadrant(x, y) or "N/A"
                except Exception:
                    quadrant = "N/A"

                armed_label = trap_name or "trap"
                discord_user_id = self._get_discord_user_id_for_steam_id(steam_id) if steam_id else None
                mention = f"<@{discord_user_id}>" if discord_user_id else "❌"

                player_line = f"Player: {player_name} {mention}"
                teleport_line = f"#Teleport {x:.4f} {y:.4f} {z:.0f}"

                description = "\n".join(
                    [
                        player_line,
                        f"Armed: {armed_label}",
                        teleport_line,
                        f"Quadrant: {quadrant}",
                    ]
                )

                thumbnail_path = None
                try:
                    thumbnail_path = self._get_trap_thumbnail_path(trap_name)
                except Exception:
                    thumbnail_path = None

                try:
                    self.discord_webhook.send_webhook(
                        webhook_name=webhook_name,
                        title="🚨 Trap Alert",
                        description=description,
                        color=0xFF0000,
                        fields=[],
                        thumbnail_path=thumbnail_path,
                    )
                except Exception:
                    # Se falhar o envio, permitir tentar novamente em um próximo processamento
                    if sig:
                        try:
                            if sig in self._mines_alerts_sent_sigs:
                                self._mines_alerts_sent_sigs.remove(sig)
                                self._save_mines_alerts_sent_signatures(self._mines_alerts_sent_sigs)
                        except Exception:
                            pass
                    raise
        except Exception:
            import traceback

            traceback.print_exc()
            return

    def _load_mines_alerts_sent_signatures(self) -> List[str]:
        try:
            if not self._mines_alerts_state_path or not os.path.exists(self._mines_alerts_state_path):
                return []
            with open(self._mines_alerts_state_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            sigs = data.get("sent_signatures")
            if not isinstance(sigs, list):
                return []
            out: List[str] = []
            for s in sigs:
                try:
                    st = str(s).strip()
                    if st:
                        out.append(st)
                except Exception:
                    continue
            return out
        except Exception:
            return []

    def _save_mines_alerts_sent_signatures(self, sigs) -> None:
        try:
            lst: List[str] = []
            try:
                for s in (sigs or []):
                    st = str(s).strip()
                    if st:
                        lst.append(st)
            except Exception:
                lst = []

            max_keep = 500
            if len(lst) > max_keep:
                lst = lst[-max_keep:]

            os.makedirs(os.path.dirname(self._mines_alerts_state_path) or ".", exist_ok=True)
            with open(self._mines_alerts_state_path, "w", encoding="utf-8") as f:
                json.dump({"sent_signatures": lst}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _schedule_teleport_punishment(self, steam_id: str, mine_id: int, x: float, y: float, z: float, delay_seconds: float):
        """Agenda uma punição de teleporte para a fila do PunishmentWorker"""
        if hasattr(self, '_punishment_worker') and self._punishment_worker:
            self._punishment_worker.enqueue_punishment(steam_id, mine_id, x, y, z, delay_seconds)

    def _check_and_trigger_pending_teleport(self, steam_id: str):
        """Verifica se o jogador tem teleporte pendente por mina ilegal e agenda"""
        try:
            # Buscar minas ilegais ativas de um jogador com teleport_executed = 0
            pending = self.db_manager.get_active_illegal_mines_by_player(steam_id)
            if pending:
                # Pegar a primeira pendente
                mine = pending[0]
                mine_id = mine['id']
                x = mine['location_x']
                y = mine['location_y']
                z = mine['location_z']
                
                # Config
                mines_cfg = self.config.get("mines_alerts") if isinstance(self.config, dict) else {}
                delay_seconds = float(mines_cfg.get("teleport_punishment_delay_seconds", 5.0))
                
                print(f"LOGIN_PUNISHMENT: Jogador {steam_id} possui mina ilegal pendente (id={mine_id}). Agendando teleporte em {delay_seconds}s.")
                self._schedule_teleport_punishment(steam_id, mine_id, x, y, z, delay_seconds)
        except Exception as e:
            print(f"LOGIN_PUNISHMENT ERRO: Erro ao verificar punição pendente para {steam_id}: {e}")

    def _mines_alert_signature(self, ev: Dict[str, Any]) -> Optional[str]:
        try:
            # Preferir a linha de log crua: é a assinatura mais estável e evita duplicação
            # quando o mesmo evento é processado 2x com os mesmos dados.
            line = str(ev.get("log_line") or "").strip()
            if line:
                return hashlib.sha1(line.encode("utf-8", errors="ignore")).hexdigest()

            ts = ev.get("timestamp")
            ts_s = None
            if ts is not None:
                try:
                    # bucket por minuto para dedup mais estável
                    ts_s = ts.replace(second=0, microsecond=0).isoformat()
                except Exception:
                    ts_s = str(ts)

            steam_id = str(ev.get("steam_id") or "").strip()
            trap_name = str(ev.get("trap_name") or "").strip()
            x = float(ev.get("location_x"))
            y = float(ev.get("location_y"))
            z = float(ev.get("location_z"))

            # Normalizar coords (reduz pequenas variações de log/replicação)
            # SCUM units: 100 = 1m. 500 units = 5m.
            q = 500.0
            xq = round(x / q) * q
            yq = round(y / q) * q
            zq = round(z / q) * q

            base = "|".join(
                [
                    ts_s or "",
                    steam_id,
                    trap_name,
                    f"{xq:.0f}",
                    f"{yq:.0f}",
                    f"{zq:.0f}",
                ]
            )
            if not base.strip():
                return None
            return hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()
        except Exception:
            return None
    
    def _process_gameplay_file(self, file_path: str):
        """Processar arquivo de gameplay - bunkers e minigame events"""
        temp_path = None
        try:
            filename = os.path.basename(file_path)
            print(f"   [DEBUG] Processando arquivo de gameplay: {filename}")
            print(f"   [DEBUG] Caminho completo: {file_path}")
            
            # Verificar se arquivo existe
            if not os.path.exists(file_path):
                print(f"   [ERRO] Arquivo não existe: {file_path}")
                return
            
            # Copiar arquivo para temp ANTES de processar (evita bloqueio e lentidão)
            print(f"   [DEBUG] Copiando arquivo para pasta temp...")
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                print(f"   [ERRO] Falha ao copiar arquivo para temp")
                return
            
            print(f"   [DEBUG] Arquivo copiado para temp: {os.path.basename(temp_path)}")
            print(f"   [DEBUG] Caminho temp: {temp_path}")
            
            # Verificar se arquivo temp existe e tem conteúdo
            if os.path.exists(temp_path):
                file_size = os.path.getsize(temp_path)
                print(f"   [DEBUG] Arquivo temp existe, tamanho: {file_size} bytes")
            else:
                print(f"   [ERRO] Arquivo temp não foi criado: {temp_path}")
                return
            
            # Processar bunkers usando arquivo temporário
            if self.bunker_processor:
                try:
                    result = self.bunker_processor.process_bunker_logs_from_temp(temp_path, file_path)
                    
                    if result.get('success'):
                        events_found = result.get('events_found', 0)
                        lines_processed = result.get('lines_processed', 0)
                        print(f"   OK Bunkers: {events_found} eventos encontrados, {lines_processed} linhas processadas")
                        
                        # Enviar notificação se houver eventos
                        if events_found > 0:
                            self._send_bunker_notification()
                    else:
                        error = result.get('error', 'Erro desconhecido')
                        print(f"   AVISO Falha ao processar bunkers: {error}")
                except Exception as e:
                    print(f"   AVISO Erro ao processar bunkers: {e}")
            
            # Processar minigame events usando arquivo temporário
            if self.gameplay_parser:
                try:
                    print(f"   [DEBUG] Iniciando parsing de eventos de minigame...")
                    minigame_events = self.gameplay_parser.parse_minigame_events_from_temp(temp_path, file_path)
                    print(f"   [DEBUG] Parsing concluído: {len(minigame_events)} eventos encontrados")
                    
                    if minigame_events:
                        # Estatísticas antes de inserir
                        lockpicking_total = sum(1 for e in minigame_events if e.get('minigame_type') == 'LockpickingMinigame_C')
                        lockpicking_fails = sum(1 for e in minigame_events if e.get('minigame_type') == 'LockpickingMinigame_C' and e.get('success') is False)
                        lockpicking_with_owner = sum(1 for e in minigame_events if e.get('minigame_type') == 'LockpickingMinigame_C' and e.get('owner_id') is not None)
                        
                        # Inserir eventos no banco (sem marcar como enviado)
                        inserted_count = self.db_manager.insert_batch_minigame_events(minigame_events)
                        print(f"   OK Minigame events: {len(minigame_events)} eventos encontrados, {inserted_count} inseridos no banco")
                        if lockpicking_total > 0:
                            print(f"      └─ LockpickingMinigame_C: {lockpicking_total} eventos ({lockpicking_fails} falhas, {lockpicking_with_owner} com proprietário)")
                        
                        # Enviar notificações para eventos de LockpickingMinigame_C COM PROPRIETÁRIO
                        # IMPORTANTE: Enviar tanto sucessos quanto falhas, desde que tenham proprietário
                        if self.minigame_notifier and inserted_count > 0:
                            try:
                                # Filtrar apenas LockpickingMinigame_C E que tenham proprietário identificado
                                # Não filtrar por success - enviar ambos sucessos e falhas
                                lockpicking_events = [
                                    event for event in minigame_events 
                                    if event.get('minigame_type', '').startswith('LockpickingMinigame_C')
                                    and event.get('owner_id') is not None
                                    and event.get('owner_steam_id') is not None
                                    and event.get('owner_name') is not None
                                ]
                                
                                if lockpicking_events:
                                    for event in lockpicking_events:
                                        self._send_lockpicking_notifications(event)
                                    
                                    print(f"   OK Notificações enviadas: {len(lockpicking_events)} eventos de lockpicking")
                            except Exception as e:
                                print(f"   AVISO Erro ao enviar notificações de minigame: {e}")
                                import traceback
                                traceback.print_exc()
                    else:
                        print(f"   [AVISO] Minigame events: nenhum evento encontrado no arquivo {filename}")
                        print(f"   [DEBUG] Verifique se o arquivo contém linhas com [LogMinigame]")
                except Exception as e:
                    print(f"   AVISO Erro ao processar minigame events: {e}")
                    import traceback
                    traceback.print_exc()
            
        except Exception as e:
            print(f"   [ERRO] Erro ao processar arquivo de gameplay: {e}")
            print(f"   [ERRO] Arquivo: {file_path}")
            import traceback
            traceback.print_exc()
            self.stats['errors'] += 1
        finally:
            # SEMPRE limpar arquivo temporário, mesmo em caso de erro
            if temp_path:
                print(f"   [DEBUG] Limpando arquivo temp: {os.path.basename(temp_path)}")
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def _send_bunker_notification(self):
        """Enviar notificação de bunkers para Discord"""
        try:
            if not self.bunker_processor:
                return

            # Delegar para o BunkerProcessor (mensagem fixa editada, sem spam)
            try:
                self.bunker_processor.send_or_edit_bunker_status_message(force=True)
            except Exception:
                pass
            
        except Exception as e:
            print(f"ERRO ao enviar notificação de bunkers: {e}")
    
    def _get_time_ago(self, timestamp: str) -> str:
        """Calcular tempo decorrido desde timestamp"""
        try:
            if not timestamp:
                return "desconhecido"
            
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            
            now = datetime.now()
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days} dias"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} horas"
            else:
                minutes = diff.seconds // 60
                return f"{minutes} minutos"
                
        except Exception:
            return "desconhecido"

    def _build_minigame_event_key(self, event: Dict[str, Any]) -> str:
        try:
            timestamp_str = event.get('timestamp')
            if isinstance(timestamp_str, datetime):
                timestamp_str = timestamp_str.isoformat()
            else:
                timestamp_str = str(timestamp_str)

            steam_id = str(event.get('steam_id', '') or '')
            minigame_type = str(event.get('minigame_type', '') or '')
            log_line = str(event.get('log_line', '') or '')

            raw = f"{timestamp_str}|{steam_id}|{minigame_type}|{log_line}"
            return hashlib.md5(raw.encode('utf-8', errors='ignore')).hexdigest()
        except Exception:
            return ""

    def _get_player_webhook_url(self, owner_steam_id: str) -> str:
        try:
            if not owner_steam_id:
                return ""

            with DatabaseConnector.get_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT webhook_url FROM player_webhooks 
                    WHERE steam_id = ? 
                      AND (expires_at IS NULL OR expires_at > datetime('now'))
                    """,
                    (owner_steam_id,),
                )
                row = cursor.fetchone()
                return str(row[0]).strip() if row and row[0] else ""
        except Exception:
            return ""

    def _ensure_delivery_record(self, conn: sqlite3.Connection, event_key: str, target_type: str, target_steam_id: Optional[str]) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO minigame_event_deliveries (event_key, target_type, target_steam_id)
            VALUES (?, ?, ?)
        """,
            (event_key, target_type, target_steam_id),
        )

    def _get_delivery_status(self, conn: sqlite3.Connection, event_key: str, target_type: str, target_steam_id: Optional[str]) -> Optional[str]:
        cursor = conn.execute(
            """
            SELECT status
            FROM minigame_event_deliveries
            WHERE event_key = ? AND target_type = ? AND target_steam_id IS ?
            LIMIT 1
        """,
            (event_key, target_type, target_steam_id),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def _mark_delivery_attempt(self, conn: sqlite3.Connection, event_key: str, target_type: str, target_steam_id: Optional[str]) -> None:
        conn.execute(
            """
            UPDATE minigame_event_deliveries
            SET attempt_count = attempt_count + 1,
                last_attempt_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE event_key = ? AND target_type = ? AND target_steam_id IS ?
        """,
            (event_key, target_type, target_steam_id),
        )

    def _mark_delivery_sent(self, conn: sqlite3.Connection, event_key: str, target_type: str, target_steam_id: Optional[str]) -> None:
        conn.execute(
            """
            UPDATE minigame_event_deliveries
            SET status = 'sent',
                sent_at = CURRENT_TIMESTAMP,
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE event_key = ? AND target_type = ? AND target_steam_id IS ?
        """,
            (event_key, target_type, target_steam_id),
        )

    def _mark_delivery_failed(self, conn: sqlite3.Connection, event_key: str, target_type: str, target_steam_id: Optional[str], error: str) -> None:
        conn.execute(
            """
            UPDATE minigame_event_deliveries
            SET status = 'failed',
                last_error = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE event_key = ? AND target_type = ? AND target_steam_id IS ?
        """,
            (error, event_key, target_type, target_steam_id),
        )

    def _send_lockpicking_notifications(self, event: Dict[str, Any]) -> None:
        """Enviar alertas de lockpicking para webhook global (admin) e para webhook pessoal do owner (se existir) com deduplicação por destino."""
        try:
            if not self.minigame_notifier:
                return

            event_key = self._build_minigame_event_key(event)
            if not event_key:
                return

            owner_steam_id = event.get('owner_steam_id')

            # Determinar possíveis destinos
            global_target_type = 'global'
            owner_target_type = 'owner'

            # --- ETAPA 1: Verificar status do envio global ---
            should_send_global = False
            with DatabaseConnector.get_connection(self.db_path, write_mode=True) as conn:
                self._ensure_delivery_record(conn, event_key, global_target_type, None)
                status = self._get_delivery_status(conn, event_key, global_target_type, None)
                if status != 'sent':
                    self._mark_delivery_attempt(conn, event_key, global_target_type, None)
                    should_send_global = True

            # --- ETAPA 2: Enviar notificação global (Sem conexão ativa!) ---
            if should_send_global:
                ok = False
                err = ''
                try:
                    ok = self.minigame_notifier.send_notification(event)
                except Exception as e:
                    err = str(e)

                # --- ETAPA 3: Atualizar resultado do envio global ---
                with DatabaseConnector.get_connection(self.db_path, write_mode=True) as conn:
                    if ok:
                        self._mark_delivery_sent(conn, event_key, global_target_type, None)
                        
                        # Manter a flag legacy
                        timestamp_str = event['timestamp'].isoformat() if isinstance(event['timestamp'], datetime) else str(event['timestamp'])
                        conn.execute(
                            '''
                            UPDATE minigame_events
                            SET discord_sent = 1
                            WHERE timestamp = ?
                              AND steam_id = ?
                              AND minigame_type = ?
                              AND log_line = ?
                              AND discord_sent = 0
                            ''',
                            (
                                timestamp_str,
                                event.get('steam_id'),
                                event.get('minigame_type'),
                                event.get('log_line'),
                            ),
                        )
                    else:
                        self._mark_delivery_failed(conn, event_key, global_target_type, None, err or 'send_failed')

            # --- ETAPA 4: Verificar status do envio pessoal ---
            owner_webhook_url = self._get_player_webhook_url(str(owner_steam_id) if owner_steam_id else '')
            if owner_webhook_url:
                should_send_owner = False
                with DatabaseConnector.get_connection(self.db_path, write_mode=True) as conn:
                    self._ensure_delivery_record(conn, event_key, owner_target_type, str(owner_steam_id))
                    status = self._get_delivery_status(conn, event_key, owner_target_type, str(owner_steam_id))
                    if status != 'sent':
                        self._mark_delivery_attempt(conn, event_key, owner_target_type, str(owner_steam_id))
                        should_send_owner = True

                # --- ETAPA 5: Enviar notificação pessoal (Sem conexão ativa!) ---
                if should_send_owner:
                    ok_owner = False
                    err_owner = ''
                    try:
                        ok_owner = self.minigame_notifier.send_notification_to_webhook(event, owner_webhook_url)
                    except Exception as e:
                        err_owner = str(e)

                    # --- ETAPA 6: Atualizar resultado do envio pessoal ---
                    with DatabaseConnector.get_connection(self.db_path, write_mode=True) as conn:
                        if ok_owner:
                            self._mark_delivery_sent(conn, event_key, owner_target_type, str(owner_steam_id))
                        else:
                            self._mark_delivery_failed(conn, event_key, owner_target_type, str(owner_steam_id), err_owner or 'send_failed')

        except Exception as e:
            print(f"AVISO Erro em _send_lockpicking_notifications: {e}")
    
    def _get_time_until(self, timestamp: str) -> str:
        """Calcular tempo até timestamp"""
        try:
            if not timestamp:
                return "desconhecido"
            
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            
            now = datetime.now()
            diff = dt - now
            
            if diff.days > 0:
                return f"em {diff.days} dias"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"em {hours} horas"
            else:
                minutes = diff.seconds // 60
                return f"em {minutes} minutos"
                
        except Exception:
            return "desconhecido"
