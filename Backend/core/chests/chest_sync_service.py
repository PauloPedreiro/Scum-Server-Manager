"""Serviço de sincronização de baús do SCUM para o SSM.

Responsável por:
- Capturar o estado atual dos baús no `SCUM.db`;
- Persistir um snapshot consolidado no `SSM.db`;
- Registrar histórico de eventos (criação, destruição, mudança de dono, etc.);
- Enviar notificações para o Discord utilizando o sistema de webhooks existente.
"""
from __future__ import annotations

from core.database.connector import DatabaseConnector


import json
import math
import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import schedule

from core.webhooks.discord_webhook import DiscordWebhook
from utils.config_path_helper import ConfigPathHelper
from utils.logger import StructuredLogger


class ChestSyncService:
    """Sincroniza baús do SCUM.db para tabelas de snapshot e histórico no SSM.db."""

    DEFAULT_NOTIFY_EVENTS = [
        "created",
        "destroyed",
        "owner_changed",
        "moved",
        "renamed",
        "vehicle_attached",
        "vehicle_detached",
        "vehicle_changed",
        "vehicle_owner_mismatch",
    ]
    POSITION_TOLERANCE = 0.5  # metros

    def __init__(
        self,
        config: Dict[str, Any],
        path_helper: Optional[ConfigPathHelper] = None,
        logger: Optional[StructuredLogger] = None,
        discord_webhook: Optional[DiscordWebhook] = None,
    ) -> None:
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        self.path_helper = path_helper

        self.chest_config = self.config.get("chest_sync", {})
        self.enabled = self.chest_config.get("enabled", True)
        self.auto_start = self.chest_config.get("auto_start", True)
        self.sync_interval_minutes = self.chest_config.get("sync_interval_minutes", 30)
        self.webhook_name = self.chest_config.get("webhook_name", "chest_events")
        notify_events = self.chest_config.get(
            "notify_events", self.DEFAULT_NOTIFY_EVENTS
        )
        self.notify_events = {event.lower() for event in notify_events}
        self.vehicle_alert_webhook_name = self.chest_config.get(
            "vehicle_alert_webhook_name",
            "chest_vehicle_alerts",
        )

        default_scum_db = (
            path_helper.get_scum_db_path()
            if path_helper
            else "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
        )
        default_ssm_db = (
            path_helper.get_ssm_db_path()
            if path_helper
            else os.path.join("data", "SSM.db")
        )
        default_vehicle_images_dir = (
            os.path.join(
                path_helper.get_application_path("data_directory", "data"),
                "imagens",
                "carros",
            )
            if path_helper
            else os.path.join("data", "imagens", "carros")
        )
        default_images_dir = (
            os.path.join(
                path_helper.get_application_path("data_directory", "data"),
                "imagens",
                "Baus",
            )
            if path_helper
            else os.path.join("data", "imagens", "Baus")
        )

        self.scum_db_path = self.chest_config.get("scum_db_path") or default_scum_db
        self.ssm_db_path = self.chest_config.get("ssm_db_path") or default_ssm_db
        self.images_directory = (
            self.chest_config.get("images_directory") or default_images_dir
        )
        self.vehicle_images_directory = (
            self.chest_config.get("vehicle_images_directory")
            or default_vehicle_images_dir
        )

        self.discord_webhook = discord_webhook

        self.scheduler = schedule.Scheduler()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False

        self.last_sync_info: Dict[str, Any] = {
            "timestamp": None,
            "status": "never_run",
            "details": {},
        }
        self._last_vehicle_mismatch_alerts: Dict[
            int, Tuple[Optional[int], Optional[str]]
        ] = {}

        self.logger.info(
            "ChestSyncService inicializado",
            {
                "enabled": self.enabled,
                "auto_start": self.auto_start,
                "sync_interval_minutes": self.sync_interval_minutes,
                "scum_db_path": self.scum_db_path,
                "ssm_db_path": self.ssm_db_path,
                "images_directory": self.images_directory,
                "notify_events": sorted(self.notify_events),
            },
        )

    # --------------------------------------------------------------------- #
    # Inicialização e agendamento
    # --------------------------------------------------------------------- #
    def set_discord_webhook(self, discord_webhook: DiscordWebhook) -> None:
        """Permitir injetar uma instância compartilhada do DiscordWebhook."""
        self.discord_webhook = discord_webhook

    _initialized_schema = False
    _schema_lock = threading.Lock()

    def ensure_tables(self) -> None:
        """Criar tabelas de snapshot e histórico, caso não existam."""
        if ChestSyncService._initialized_schema:
            return

        with ChestSyncService._schema_lock:
            if ChestSyncService._initialized_schema:
                return

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                        cursor = conn.cursor()

                        cursor.execute(
                            """
                        CREATE TABLE IF NOT EXISTS chest_snapshot (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            entity_id INTEGER NOT NULL UNIQUE,
                            container_entity_id INTEGER,
                            chest_class TEXT,
                            owner_profile_id INTEGER,
                            steam_id TEXT,
                            player_name TEXT,
                            fake_name TEXT,
                            custom_name TEXT,
                            location_x REAL,
                            location_y REAL,
                            location_z REAL,
                            rotation_x REAL,
                            rotation_y REAL,
                            rotation_z REAL,
                            vehicle_container_class TEXT,
                            vehicle_entity_id INTEGER,
                            vehicle_class TEXT,
                            vehicle_owner_steam_id TEXT,
                            vehicle_owner_name TEXT,
                            vehicle_owner_player_id INTEGER,
                            vehicle_registered_at TEXT,
                            vehicle_owner_mismatch INTEGER DEFAULT 0,
                            last_seen_at TEXT NOT NULL,
                            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                        )

                        cursor.execute(
                            """
                        CREATE TABLE IF NOT EXISTS chest_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            entity_id INTEGER,
                            event_type TEXT NOT NULL,
                            container_entity_id INTEGER,
                            owner_profile_id INTEGER,
                            steam_id TEXT,
                            player_name TEXT,
                            fake_name TEXT,
                            custom_name TEXT,
                            chest_class TEXT,
                            location_x REAL,
                            location_y REAL,
                            location_z REAL,
                            rotation_x REAL,
                            rotation_y REAL,
                            rotation_z REAL,
                            vehicle_container_class TEXT,
                            vehicle_entity_id INTEGER,
                            vehicle_class TEXT,
                            vehicle_owner_steam_id TEXT,
                            vehicle_owner_name TEXT,
                            vehicle_owner_player_id INTEGER,
                            vehicle_registered_at TEXT,
                            vehicle_owner_mismatch INTEGER DEFAULT 0,
                            details_json TEXT,
                            event_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                        )

                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_chest_snapshot_entity ON chest_snapshot (entity_id)"
                        )
                        # Garantir colunas adicionais em cenários de upgrade
                        self._ensure_column(
                            cursor, "chest_snapshot", "container_entity_id INTEGER"
                        )
                        self._ensure_column(
                            cursor, "chest_snapshot", "vehicle_container_class TEXT"
                        )
                        self._ensure_column(
                            cursor, "chest_snapshot", "vehicle_entity_id INTEGER"
                        )
                        self._ensure_column(cursor, "chest_snapshot", "vehicle_class TEXT")
                        self._ensure_column(
                            cursor, "chest_snapshot", "vehicle_owner_steam_id TEXT"
                        )
                        self._ensure_column(
                            cursor, "chest_snapshot", "vehicle_owner_name TEXT"
                        )
                        self._ensure_column(
                            cursor, "chest_snapshot", "vehicle_owner_player_id INTEGER"
                        )
                        self._ensure_column(
                            cursor, "chest_snapshot", "vehicle_registered_at TEXT"
                        )
                        self._ensure_column(
                            cursor,
                            "chest_snapshot",
                            "vehicle_owner_mismatch INTEGER DEFAULT 0",
                        )

                        self._ensure_column(
                            cursor, "chest_history", "container_entity_id INTEGER"
                        )
                        self._ensure_column(
                            cursor, "chest_history", "vehicle_container_class TEXT"
                        )
                        self._ensure_column(
                            cursor, "chest_history", "vehicle_entity_id INTEGER"
                        )
                        self._ensure_column(cursor, "chest_history", "vehicle_class TEXT")
                        self._ensure_column(
                            cursor, "chest_history", "vehicle_owner_steam_id TEXT"
                        )
                        self._ensure_column(
                            cursor, "chest_history", "vehicle_owner_name TEXT"
                        )
                        self._ensure_column(
                            cursor, "chest_history", "vehicle_owner_player_id INTEGER"
                        )
                        self._ensure_column(
                            cursor, "chest_history", "vehicle_registered_at TEXT"
                        )
                        self._ensure_column(
                            cursor,
                            "chest_history",
                            "vehicle_owner_mismatch INTEGER DEFAULT 0",
                        )

                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_chest_history_entity ON chest_history (entity_id)"
                        )
                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_chest_history_event ON chest_history (event_type)"
                        )
                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_chest_snapshot_vehicle ON chest_snapshot (vehicle_entity_id)"
                        )
                        cursor.execute(
                            "CREATE INDEX IF NOT EXISTS idx_chest_snapshot_vehicle_owner ON chest_snapshot (vehicle_owner_steam_id)"
                        )
                        self._ensure_column(
                            cursor, "chest_history", "discord_sent INTEGER DEFAULT 0"
                        )

                        conn.commit()
                        ChestSyncService._initialized_schema = True
                        return  # Sucesso - sair do loop de retry

                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        delay = 2.0 * (2**attempt)  # Backoff exponencial: 2s, 4s, 8s
                        self.logger.warn(
                            f"Banco bloqueado ao garantir tabelas de baús, tentando novamente em {delay:.1f}s (tentativa {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    raise
                except Exception as exc:
                    self.logger.error(
                        "Erro ao garantir tabelas de baús",
                        {"error": str(exc), "attempt": attempt + 1},
                    )
                    if attempt == max_retries - 1:
                        raise
                    delay = 2.0 * (2**attempt)
                    time.sleep(delay)

    def _ensure_column(
        self, cursor: sqlite3.Cursor, table: str, column_definition: str
    ) -> None:
        """Adicionar coluna caso não exista."""
        column_name = column_definition.split()[0]
        cursor.execute(f"PRAGMA table_info({table})")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_definition}")

    def start(self) -> Dict[str, Any]:
        """Iniciar o agendador de sincronização."""
        if not self.enabled:
            return {
                "success": False,
                "message": "Sincronização de baús desabilitada",
                "status": "disabled",
            }

        if self.is_running:
            return {
                "success": False,
                "message": "Sincronização de baús já está em execução",
                "status": "already_running",
            }

        try:
            self.ensure_tables()

            self.logger.info("Executando sincronização inicial de baús")
            self.sync_once()

            self.scheduler.clear()
            self.scheduler.every(self.sync_interval_minutes).minutes.do(self.sync_once)

            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self.scheduler_thread.start()
            self.is_running = True

            return {
                "success": True,
                "message": "Sincronização de baús iniciada",
                "status": "started",
                "sync_interval_minutes": self.sync_interval_minutes,
            }

        except Exception as exc:
            self.logger.error("Erro ao iniciar ChestSyncService", {"error": str(exc)})
            return {
                "success": False,
                "message": f"Erro ao iniciar sincronização: {exc}",
                "status": "error",
            }

    def stop(self) -> Dict[str, Any]:
        """Parar o agendador de sincronização."""
        if not self.is_running:
            return {
                "success": False,
                "message": "Sincronização de baús não está em execução",
                "status": "not_running",
            }

        self.stop_event.set()
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        self.scheduler.clear()
        self.is_running = False

        return {
            "success": True,
            "message": "Sincronização de baús parada",
            "status": "stopped",
        }

    def _scheduler_loop(self) -> None:
        """Loop do agendador."""
        while not self.stop_event.is_set():
            try:
                self.scheduler.run_pending()
                time.sleep(1)
            except Exception as exc:
                self.logger.error(
                    "Erro no loop de agendamento de baús", {"error": str(exc)}
                )
                time.sleep(5)

    # --------------------------------------------------------------------- #
    # Fluxo principal de sincronização
    # --------------------------------------------------------------------- #
    def sync_once(self) -> Dict[str, Any]:
        """Executar uma sincronização completa."""
        start_time = time.monotonic()

        if not os.path.exists(self.scum_db_path):
            message = "SCUM.db não encontrado"
            self.logger.error(message, {"path": self.scum_db_path})
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": message},
            }
            return {"success": False, "error": message}

        try:
            self.ensure_tables()

            previous_snapshot = self._load_snapshot()
            current_snapshot = self._fetch_scum_chests()
            events = self._detect_events(previous_snapshot, current_snapshot)

            self._persist_snapshot(current_snapshot.values())
            if events:
                self._persist_history(events)
                self._notify_events(events)

            elapsed = round(time.monotonic() - start_time, 3)
            result = {
                "success": True,
                "chests": len(current_snapshot),
                "events": len(events),
                "elapsed_seconds": elapsed,
            }

            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success",
                "details": result,
            }

            self.logger.info("Sincronização de baús executada", result)
            return result

        except Exception as exc:
            self.logger.error("Erro durante sincronização de baús", {"error": str(exc)})
            self.last_sync_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "details": {"error": str(exc)},
            }
            return {"success": False, "error": str(exc)}

    def get_status(self) -> Dict[str, Any]:
        """Retornar status atual do serviço."""
        return {
            "enabled": self.enabled,
            "is_running": self.is_running,
            "sync_interval_minutes": self.sync_interval_minutes,
            "last_sync": self.last_sync_info,
        }

    # --------------------------------------------------------------------- #
    # Operações auxiliares
    # --------------------------------------------------------------------- #
    def _load_snapshot(self) -> Dict[int, Dict[str, Any]]:
        """Carregar snapshot atual do SSM."""
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(
                """
                SELECT
                    entity_id,
                    container_entity_id,
                    chest_class,
                    owner_profile_id,
                    steam_id,
                    player_name,
                    fake_name,
                    custom_name,
                    location_x,
                    location_y,
                    location_z,
                    rotation_x,
                    rotation_y,
                    rotation_z,
                    vehicle_container_class,
                    vehicle_entity_id,
                    vehicle_class,
                    vehicle_owner_steam_id,
                    vehicle_owner_name,
                    vehicle_owner_player_id,
                    vehicle_registered_at,
                    vehicle_owner_mismatch
                FROM chest_snapshot
                """
            ).fetchall()

        snapshot = {}
        for row in rows:
            data = dict(row)
            data["vehicle_owner_mismatch"] = bool(data.get("vehicle_owner_mismatch"))
            snapshot[row["entity_id"]] = data
        return snapshot

    def _fetch_scum_chests(self) -> Dict[int, Dict[str, Any]]:
        """Buscar dados atuais de baús no SCUM.db."""
        from utils.scum_db_helper import scum_db_readonly_connection

        with scum_db_readonly_connection(self.scum_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            profiles_rows = cursor.execute(
                """
                SELECT id, name, fake_name, user_id
                FROM user_profile
                """
            ).fetchall()
            profiles = {row["id"]: dict(row) for row in profiles_rows}

            chest_rows = cursor.execute(
                """
                SELECT e.id,
                       e.class,
                       e.location_x,
                       e.location_y,
                       e.location_z,
                       e.rotation_x,
                       e.rotation_y,
                       e.rotation_z,
                       e.owning_entity_id,
                       e.parent_entity_id,
                       ie.xml
                FROM entity e
                LEFT JOIN item_entity ie ON ie.entity_id = e.id
                WHERE e.class LIKE '%Chest%'
                   OR e.class IN ('ImprovisedWardrobe_C', 'StorageShelf_C', 'WoodenWeaponRack_C')
                """
            ).fetchall()

        snapshot_at = datetime.utcnow().isoformat()

        # Montar mapa de containers
        container_ids = {
            row["owning_entity_id"] or row["parent_entity_id"]
            for row in chest_rows
            if row["owning_entity_id"] or row["parent_entity_id"]
        }

        container_map: Dict[int, Dict[str, Any]] = {}
        vehicle_relations: Dict[int, Optional[int]] = {}
        vehicle_ids: set[int] = set()

        if container_ids:
            container_map = self._fetch_entities(container_ids)
            for container_id, container_data in container_map.items():
                vehicle_id = container_data.get(
                    "parent_entity_id"
                ) or container_data.get("owning_entity_id")
                if vehicle_id:
                    vehicle_relations[container_id] = vehicle_id
                    vehicle_ids.add(vehicle_id)
                else:
                    vehicle_relations[container_id] = None

        vehicle_map: Dict[int, Dict[str, Any]] = {}
        if vehicle_ids:
            vehicle_map = self._fetch_entities(vehicle_ids)

        owners_by_container, owners_by_vehicle = self._fetch_vehicle_owners(
            container_ids, vehicle_ids
        )

        result: Dict[int, Dict[str, Any]] = {}

        for row in chest_rows:
            entity_id = row["id"]
            owner_profile_id, custom_name = self._parse_item_xml(row["xml"])

            profile = profiles.get(owner_profile_id or 0)
            steam_id = (
                profile["user_id"] if profile and profile.get("user_id") else None
            )
            player_name = profile["name"] if profile and profile.get("name") else None
            fake_name = (
                profile["fake_name"] if profile and profile.get("fake_name") else None
            )

            container_entity_id = row["owning_entity_id"] or row["parent_entity_id"]
            container_data = container_map.get(container_entity_id or -1, {})
            vehicle_entity_id = None
            vehicle_class = None

            if container_entity_id:
                vehicle_entity_id = vehicle_relations.get(container_entity_id)
                if vehicle_entity_id:
                    vehicle_info = vehicle_map.get(vehicle_entity_id, {})
                    vehicle_class = vehicle_info.get("class")

            owner_info = owners_by_container.get(
                container_entity_id or -1
            ) or owners_by_vehicle.get(vehicle_entity_id or -1, {})
            vehicle_owner_steam_id = owner_info.get("steam_id")
            vehicle_owner_name = owner_info.get("player_name")
            vehicle_owner_player_id = owner_info.get("player_id")
            vehicle_registered_at = owner_info.get("last_ownership_change")

            # Caso vehicle_class não tenha vindo do SCUM, tentar usar o valor persistido
            if not vehicle_class:
                vehicle_class = owner_info.get("vehicle_class")
            vehicle_container_class = container_data.get("class")

            vehicle_owner_mismatch = bool(
                steam_id
                and vehicle_owner_steam_id
                and steam_id != vehicle_owner_steam_id
            )

            result[entity_id] = {
                "entity_id": entity_id,
                "container_entity_id": container_entity_id,
                "chest_class": row["class"],
                "owner_profile_id": owner_profile_id,
                "steam_id": steam_id,
                "player_name": player_name,
                "fake_name": fake_name,
                "custom_name": custom_name,
                "location_x": row["location_x"],
                "location_y": row["location_y"],
                "location_z": row["location_z"],
                "rotation_x": row["rotation_x"],
                "rotation_y": row["rotation_y"],
                "rotation_z": row["rotation_z"],
                "vehicle_container_class": vehicle_container_class,
                "vehicle_entity_id": vehicle_entity_id,
                "vehicle_class": vehicle_class,
                "vehicle_owner_steam_id": vehicle_owner_steam_id,
                "vehicle_owner_name": vehicle_owner_name,
                "vehicle_owner_player_id": vehicle_owner_player_id,
                "vehicle_registered_at": vehicle_registered_at,
                "vehicle_owner_mismatch": vehicle_owner_mismatch,
                "last_seen_at": snapshot_at,
            }

        return result

    def _fetch_entities(self, entity_ids: Iterable[int]) -> Dict[int, Dict[str, Any]]:
        """Carregar entidades específicas do SCUM.db."""
        ids = [eid for eid in entity_ids if eid is not None]
        if not ids:
            return {}

        query = f"""
            SELECT id, class, owning_entity_id, parent_entity_id
            FROM entity
            WHERE id IN ({",".join(["?"] * len(ids))})
        """

        from utils.scum_db_helper import scum_db_readonly_connection

        with scum_db_readonly_connection(self.scum_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(query, ids).fetchall()

        return {row["id"]: dict(row) for row in rows}

    def _fetch_vehicle_owners(
        self,
        container_ids: Iterable[int],
        vehicle_ids: Iterable[int],
    ) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, Dict[str, Any]]]:
        """Carregar proprietários atuais dos veículos a partir do SSM.db."""
        container_ids_list = [cid for cid in container_ids if cid is not None]
        vehicle_ids_list = [vid for vid in vehicle_ids if vid is not None]

        owners_by_container: Dict[int, Dict[str, Any]] = {}
        owners_by_vehicle: Dict[int, Dict[str, Any]] = {}

        if container_ids_list:
            placeholders = ",".join(["?"] * len(container_ids_list))
            query = f"""
            SELECT
                entity_id,
                vehicle_entity_id,
                steam_id,
                player_name,
                player_id,
                last_ownership_change,
                vehicle_class
            FROM vehicle_current_ownership
            WHERE entity_id IN ({placeholders})
        """

            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                rows = cursor.execute(query, container_ids_list).fetchall()
                owners_by_container = {row["entity_id"]: dict(row) for row in rows}

        if vehicle_ids_list:
            placeholders = ",".join(["?"] * len(vehicle_ids_list))
            query = f"""
                SELECT
                    entity_id,
                    vehicle_entity_id,
                    steam_id,
                    player_name,
                    player_id,
                    last_ownership_change,
                    vehicle_class
                FROM vehicle_current_ownership
                WHERE vehicle_entity_id IN ({placeholders})
            """

            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                rows = cursor.execute(query, vehicle_ids_list).fetchall()
                owners_by_vehicle = {
                    row["vehicle_entity_id"]: dict(row) for row in rows
                }

        return owners_by_container, owners_by_vehicle

    def _parse_item_xml(
        self, xml_text: Optional[str]
    ) -> Tuple[Optional[int], Optional[str]]:
        """Extrair owner_profile_id e custom_name do XML do item."""
        if not xml_text:
            return None, None

        try:
            import xml.etree.ElementTree as ET

            # Parse XML do item
            root = ET.fromstring(xml_text)

            owner_attr = root.attrib.get("_owningUserProfileId")
            owner_profile_id = (
                int(owner_attr) if owner_attr and owner_attr != "0" else None
            )

            custom_name = None
            for component in root.findall(".//Component"):
                if component.attrib.get("Name") == "NameableComponent":
                    custom_name = component.attrib.get("_name")
                    break

            return owner_profile_id, custom_name

        except ET.ParseError as exc:
            # XML malformado - comum em itens corrompidos do SCUM, não é crítico
            # Log apenas em debug para não poluir os logs
            self.logger.debug("XML de item malformado ignorado", {"error": str(exc)})
            return None, None
        except Exception as exc:
            # Outros erros também são tratados silenciosamente
            self.logger.debug("Falha ao interpretar XML de item", {"error": str(exc)})
            return None, None

    def _detect_events(
        self,
        previous: Dict[int, Dict[str, Any]],
        current: Dict[int, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Identificar diferenças entre snapshots."""
        events: List[Dict[str, Any]] = []

        for entity_id, record in current.items():
            old = previous.get(entity_id)
            if not old:
                if record.get("vehicle_entity_id") and not record.get(
                    "vehicle_owner_mismatch"
                ):
                    continue
                if self._is_same_owner_vehicle(record, None):
                    continue
                events.append(
                    {
                        "entity_id": entity_id,
                        "event_type": "created",
                        "record": record,
                        "previous": None,
                        "details": {},
                    }
                )
                if record.get("vehicle_owner_mismatch"):
                    events.append(
                        {
                            "entity_id": entity_id,
                            "event_type": "vehicle_owner_mismatch",
                            "record": record,
                            "previous": None,
                            "details": {
                                "chest_owner": {
                                    "steam_id": record.get("steam_id"),
                                    "name": record.get("fake_name")
                                    or record.get("player_name"),
                                },
                                "vehicle_owner": {
                                    "steam_id": record.get("vehicle_owner_steam_id"),
                                    "name": record.get("vehicle_owner_name"),
                                },
                                "vehicle_entity_id": record.get("vehicle_entity_id"),
                                "container_entity_id": record.get(
                                    "container_entity_id"
                                ),
                                "vehicle_class": record.get("vehicle_class"),
                            },
                        }
                    )
                continue

            # Mudança de container/veículo
            old_container = old.get("container_entity_id")
            new_container = record.get("container_entity_id")
            old_vehicle = old.get("vehicle_entity_id")
            new_vehicle = record.get("vehicle_entity_id")

            if new_container and not old_container:
                events.append(
                    {
                        "entity_id": entity_id,
                        "event_type": "vehicle_attached",
                        "record": record,
                        "previous": old,
                        "details": {
                            "container_entity_id": new_container,
                            "vehicle_entity_id": new_vehicle,
                            "vehicle_class": record.get("vehicle_class"),
                        },
                    }
                )
            elif old_container and not new_container:
                events.append(
                    {
                        "entity_id": entity_id,
                        "event_type": "vehicle_detached",
                        "record": record,
                        "previous": old,
                        "details": {
                            "previous_container_entity_id": old_container,
                            "previous_vehicle_entity_id": old_vehicle,
                            "previous_vehicle_class": old.get("vehicle_class"),
                        },
                    }
                )
            elif old_container != new_container or old_vehicle != new_vehicle:
                events.append(
                    {
                        "entity_id": entity_id,
                        "event_type": "vehicle_changed",
                        "record": record,
                        "previous": old,
                        "details": {
                            "container_entity_id": new_container,
                            "vehicle_entity_id": new_vehicle,
                            "vehicle_class": record.get("vehicle_class"),
                            "previous_container_entity_id": old_container,
                            "previous_vehicle_entity_id": old_vehicle,
                            "previous_vehicle_class": old.get("vehicle_class"),
                        },
                    }
                )

            # Mudança de dono
            if (old.get("steam_id") or old.get("owner_profile_id")) != (
                record.get("steam_id") or record.get("owner_profile_id")
            ):
                events.append(
                    {
                        "entity_id": entity_id,
                        "event_type": "owner_changed",
                        "record": record,
                        "previous": old,
                        "details": {
                            "previous_steam_id": old.get("steam_id"),
                            "previous_player_name": old.get("player_name"),
                            "previous_fake_name": old.get("fake_name"),
                        },
                    }
                )

            # Mudança de nome personalizado
            if (old.get("custom_name") or "").strip() != (
                record.get("custom_name") or ""
            ).strip():
                events.append(
                    {
                        "entity_id": entity_id,
                        "event_type": "renamed",
                        "record": record,
                        "previous": old,
                        "details": {
                            "previous_custom_name": old.get("custom_name"),
                        },
                    }
                )

            # Mudança de posição
            if self._has_position_changed(old, record):
                events.append(
                    {
                        "entity_id": entity_id,
                        "event_type": "moved",
                        "record": record,
                        "previous": old,
                        "details": {
                            "previous_location": [
                                old.get("location_x"),
                                old.get("location_y"),
                                old.get("location_z"),
                            ]
                        },
                    }
                )

            # Início de mismatch entre dono do baú e dono do veículo
            prev_mismatch = bool(old.get("vehicle_owner_mismatch"))
            curr_mismatch = bool(record.get("vehicle_owner_mismatch"))
            if curr_mismatch and not prev_mismatch:
                events.append(
                    {
                        "entity_id": entity_id,
                        "event_type": "vehicle_owner_mismatch",
                        "record": record,
                        "previous": old,
                        "details": {
                            "chest_owner": {
                                "steam_id": record.get("steam_id"),
                                "name": record.get("fake_name")
                                or record.get("player_name"),
                            },
                            "vehicle_owner": {
                                "steam_id": record.get("vehicle_owner_steam_id"),
                                "name": record.get("vehicle_owner_name"),
                            },
                            "vehicle_entity_id": record.get("vehicle_entity_id"),
                            "container_entity_id": record.get("container_entity_id"),
                            "vehicle_class": record.get("vehicle_class"),
                        },
                    }
                )
            elif not curr_mismatch and prev_mismatch:
                self._clear_history_alert_flags(entity_id)

        # Baús removidos
        for entity_id, old in previous.items():
            if entity_id not in current:
                events.append(
                    {
                        "entity_id": entity_id,
                        "event_type": "destroyed",
                        "record": None,
                        "previous": old,
                        "details": {},
                    }
                )

        return events

    def _has_position_changed(
        self, previous: Dict[str, Any], current: Dict[str, Any]
    ) -> bool:
        """Verificar se houve alteração relevante na posição."""
        try:
            prev_coords = (
                float(previous.get("location_x") or 0.0),
                float(previous.get("location_y") or 0.0),
                float(previous.get("location_z") or 0.0),
            )
            current_coords = (
                float(current.get("location_x") or 0.0),
                float(current.get("location_y") or 0.0),
                float(current.get("location_z") or 0.0),
            )

            distance = math.dist(prev_coords, current_coords)
            return distance > self.POSITION_TOLERANCE
        except Exception:
            return False

    def _persist_snapshot(self, chests: Iterable[Dict[str, Any]]) -> None:
        """Persistir snapshot atual no SSM."""
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chest_snapshot")

            fields = (
                "entity_id",
                "container_entity_id",
                "chest_class",
                "owner_profile_id",
                "steam_id",
                "player_name",
                "fake_name",
                "custom_name",
                "location_x",
                "location_y",
                "location_z",
                "rotation_x",
                "rotation_y",
                "rotation_z",
                "vehicle_container_class",
                "vehicle_entity_id",
                "vehicle_class",
                "vehicle_owner_steam_id",
                "vehicle_owner_name",
                "vehicle_owner_player_id",
                "vehicle_registered_at",
                "vehicle_owner_mismatch",
                "last_seen_at",
            )

            cursor.executemany(
                f"""
                INSERT INTO chest_snapshot (
                    {', '.join(fields)}
                ) VALUES ({', '.join(['?'] * len(fields))})
                """,
                [
                    tuple(
                        (
                            chest.get(field)
                            if field != "vehicle_owner_mismatch"
                            else int(bool(chest.get(field)))
                        )
                        for field in fields
                    )
                    for chest in chests
                ],
            )

            conn.commit()

    def _persist_history(self, events: Iterable[Dict[str, Any]]) -> None:
        """Salvar eventos no histórico."""
        snapshot_fields = [
            "entity_id",
            "event_type",
            "container_entity_id",
            "owner_profile_id",
            "steam_id",
            "player_name",
            "fake_name",
            "custom_name",
            "chest_class",
            "location_x",
            "location_y",
            "location_z",
            "rotation_x",
            "rotation_y",
            "rotation_z",
            "vehicle_container_class",
            "vehicle_entity_id",
            "vehicle_class",
            "vehicle_owner_steam_id",
            "vehicle_owner_name",
            "vehicle_owner_player_id",
            "vehicle_registered_at",
            "vehicle_owner_mismatch",
            "details_json",
            "discord_sent",
        ]

        insert_sql = f"""
            INSERT INTO chest_history (
                {', '.join(snapshot_fields)}
            ) VALUES ({', '.join(['?'] * len(snapshot_fields))})
        """

        if not events:
            return

        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            for event in events:
                if (event.get("event_type") or "").lower() == "moved":
                    continue
                data_source = event.get("record") or event.get("previous") or {}
                values = (
                    event.get("entity_id"),
                    event.get("event_type"),
                    data_source.get("container_entity_id"),
                    data_source.get("owner_profile_id"),
                    data_source.get("steam_id"),
                    data_source.get("player_name"),
                    data_source.get("fake_name"),
                    data_source.get("custom_name"),
                    data_source.get("chest_class"),
                    data_source.get("location_x"),
                    data_source.get("location_y"),
                    data_source.get("location_z"),
                    data_source.get("rotation_x"),
                    data_source.get("rotation_y"),
                    data_source.get("rotation_z"),
                    data_source.get("vehicle_container_class"),
                    data_source.get("vehicle_entity_id"),
                    data_source.get("vehicle_class"),
                    data_source.get("vehicle_owner_steam_id"),
                    data_source.get("vehicle_owner_name"),
                    data_source.get("vehicle_owner_player_id"),
                    data_source.get("vehicle_registered_at"),
                    int(bool(data_source.get("vehicle_owner_mismatch"))),
                    json.dumps(event.get("details") or {}, ensure_ascii=False),
                    0,
                )
                cursor.execute(insert_sql, values)
                event["_history_row_id"] = cursor.lastrowid
            conn.commit()

    # --------------------------------------------------------------------- #
    # Notificações
    # --------------------------------------------------------------------- #
    def _notify_events(self, events: Iterable[Dict[str, Any]]) -> None:
        """Enviar notificações para eventos relevantes."""
        if not self.discord_webhook and self.config:
            # fallback: criar uma instância local usando a config carregada
            self.discord_webhook = DiscordWebhook(self.config, self.logger)

        if not self.discord_webhook:
            self.logger.warn("DiscordWebhook não disponível para notificações de baú")
            return

        for event in events:
            event_type = (event.get("event_type") or "").lower()
            if event_type not in self.notify_events:
                continue

            record = event.get("record") or event.get("previous") or {}
            previous = event.get("previous") or {}
            entity_id = record.get("entity_id") or previous.get("entity_id")
            history_row_id = event.get("_history_row_id")

            if self._is_same_owner_vehicle(record, previous) and event_type in {
                "created",
                "vehicle_attached",
                "vehicle_changed",
                "vehicle_owner_mismatch",
            }:
                if history_row_id is not None:
                    self._mark_history_discord_sent(history_row_id)
                continue

            if event_type == "vehicle_attached":
                if history_row_id is not None:
                    self._mark_history_discord_sent(history_row_id)
                continue

            if event_type == "vehicle_owner_mismatch":
                vehicle_id = record.get("vehicle_entity_id") or previous.get(
                    "vehicle_entity_id"
                )
                vehicle_owner = record.get("vehicle_owner_steam_id") or previous.get(
                    "vehicle_owner_steam_id"
                )
                cache_key = (vehicle_id, vehicle_owner)
                if (
                    entity_id is not None
                    and cache_key == self._last_vehicle_mismatch_alerts.get(entity_id)
                ):
                    if history_row_id is not None:
                        self._mark_history_discord_sent(history_row_id)
                    continue
                if entity_id is not None and self._history_was_mismatch_alert_sent(
                    entity_id, vehicle_id, vehicle_owner
                ):
                    self._last_vehicle_mismatch_alerts[entity_id] = cache_key
                    if history_row_id is not None:
                        self._mark_history_discord_sent(history_row_id)
                    continue
            else:
                if entity_id is not None:
                    combined = record if record else previous
                    if not combined or not combined.get("vehicle_owner_mismatch"):
                        self._last_vehicle_mismatch_alerts.pop(entity_id, None)
                        self._clear_history_alert_flags(entity_id)

            embed = self._build_embed(
                event_type, record, previous, event.get("details") or {}
            )

            target_webhook = self.webhook_name
            image_path = None
            thumbnail_path = None
            extra_attachments: List[Tuple[str, Optional[str]]] = []
            map_components = self._build_map_components(record, previous)

            if event_type in {
                "vehicle_attached",
                "vehicle_detached",
                "vehicle_changed",
                "vehicle_owner_mismatch",
            }:
                vehicle_image_path = self._resolve_vehicle_image_path(
                    record.get("vehicle_class") or previous.get("vehicle_class")
                )
                image_path = vehicle_image_path
                if event_type == "vehicle_owner_mismatch":
                    target_webhook = self.vehicle_alert_webhook_name
                    # Manter apenas o thumbnail dentro do embed (baú); nenhuma imagem grande fora do embed
                    image_path = None
                    extra_attachments = []
                    thumbnail_path = self._resolve_chest_image_path(
                        record.get("chest_class") or previous.get("chest_class")
                    )
            else:
                thumbnail_path = self._resolve_chest_image_path(
                    record.get("chest_class") or previous.get("chest_class")
                )

            if not target_webhook:
                self.logger.warn(
                    f"Nenhum webhook configurado para evento '{event_type}'"
                )
                continue

            try:
                self.discord_webhook.send_embed_with_image(
                    webhook_name=target_webhook,
                    embed=embed,
                    image_path=image_path,
                    thumbnail_path=thumbnail_path,
                    extra_attachments=extra_attachments or None,
                    components=map_components or None,
                )
                if event_type == "vehicle_owner_mismatch" and entity_id is not None:
                    vehicle_id = record.get("vehicle_entity_id") or previous.get(
                        "vehicle_entity_id"
                    )
                    vehicle_owner = record.get(
                        "vehicle_owner_steam_id"
                    ) or previous.get("vehicle_owner_steam_id")
                    self._last_vehicle_mismatch_alerts[entity_id] = (
                        vehicle_id,
                        vehicle_owner,
                    )
                if history_row_id is not None:
                    self._mark_history_discord_sent(history_row_id)
            except Exception as exc:
                self.logger.error(
                    "Falha ao enviar notificação de baú", {"error": str(exc)}
                )

    def _build_embed(
        self,
        event_type: str,
        record: Dict[str, Any],
        previous: Dict[str, Any],
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Construir embed para o Discord."""
        titles = {
            "created": "📦 Chest Created",
            "destroyed": "💥 Chest Removed",
            "owner_changed": "🔄 Chest Transferred",
            "moved": "🚚 Chest Moved",
            "renamed": "✏️ Chest Renamed",
            "vehicle_attached": "🚗 Chest Placed in Vehicle",
            "vehicle_detached": "🛑 Chest Removed from Vehicle",
            "vehicle_changed": "🔁 Chest Moved Between Vehicles",
            "vehicle_owner_mismatch": "⚠️ CHEST ALERT ⚠️",
        }
        colors = {
            "created": 0x00FF7F,
            "destroyed": 0xFF5555,
            "owner_changed": 0xFFAA00,
            "moved": 0x3399FF,
            "renamed": 0x9966FF,
            "vehicle_attached": 0x2ECC71,
            "vehicle_detached": 0xE74C3C,
            "vehicle_changed": 0xF1C40F,
            "vehicle_owner_mismatch": 0xE67E22,
        }

        title = titles.get(event_type, "📦 Chest Update")
        color = colors.get(event_type, 0x0099FF)

        current_data = record or {}
        previous_data = previous or {}

        steam_id = (
            current_data.get("steam_id") or previous_data.get("steam_id") or "Unknown"
        )
        owner_name = (
            current_data.get("fake_name")
            or current_data.get("player_name")
            or previous_data.get("fake_name")
            or previous_data.get("player_name")
            or "Unknown"
        )
        chest_class = (
            current_data.get("chest_class")
            or previous_data.get("chest_class")
            or "Unknown"
        )
        container_entity_id = current_data.get(
            "container_entity_id"
        ) or previous_data.get("container_entity_id")
        vehicle_entity_id = current_data.get("vehicle_entity_id") or previous_data.get(
            "vehicle_entity_id"
        )
        vehicle_class = current_data.get("vehicle_class") or previous_data.get(
            "vehicle_class"
        )
        vehicle_owner_name = current_data.get(
            "vehicle_owner_name"
        ) or previous_data.get("vehicle_owner_name")
        vehicle_owner_steam = current_data.get(
            "vehicle_owner_steam_id"
        ) or previous_data.get("vehicle_owner_steam_id")

        location_x = current_data.get("location_x")
        if location_x is None:
            location_x = previous_data.get("location_x")
        location_y = current_data.get("location_y")
        if location_y is None:
            location_y = previous_data.get("location_y")
        location_z = current_data.get("location_z")
        if location_z is None:
            location_z = previous_data.get("location_z")

        coords_raw = self._format_coords(
            location_x,
            location_y,
            location_z,
        )
        # Colocar em bloco de código para exibir botão de copiar no Discord
        coords = f"```{coords_raw}```" if coords_raw != "Unknown" else "Unknown"

        map_field: Optional[Dict[str, Any]] = None
        try:
            if location_x is not None and location_y is not None:
                x_float = float(location_x)
                y_float = float(location_y)
                map_url = (
                    f"https://scum-map.com/en/shared/scum/island/"
                    f"{x_float:.4f},{y_float:.4f},4"
                )
                map_field = {
                    "name": "Map",
                    "value": f"[Open on SCUM Map]({map_url})",
                    "inline": False,
                }
        except (TypeError, ValueError):
            map_field = None

        description = ""
        owner_display = owner_name if owner_name != "Unknown" else "Unknown"

        fields = []
        if event_type == "vehicle_changed":
            vehicle_name = vehicle_class or "Unknown"
            vehicle_id_display = vehicle_entity_id or "?"
            vehicle_owner_name_display = vehicle_owner_name or "Unknown"
            vehicle_owner_steam_display = vehicle_owner_steam or "Unknown"

            fields.extend(
                [
                    {
                        "name": "ID",
                        "value": str(
                            current_data.get("entity_id")
                            or previous_data.get("entity_id")
                        ),
                        "inline": True,
                    },
                    {
                        "name": "Type",
                        "value": self._get_chest_display_name(chest_class),
                        "inline": True,
                    },
                    {"name": "Location", "value": coords, "inline": False},
                    {"name": "Owner", "value": owner_display, "inline": False},
                    {
                        "name": "Vehicle",
                        "value": f"{vehicle_name} (ID: {vehicle_id_display})\n{vehicle_owner_name_display} ({vehicle_owner_steam_display})",
                        "inline": False,
                    },
                ]
            )
        else:
            fields.extend(
                [
                    {
                        "name": "ID",
                        "value": str(
                            current_data.get("entity_id")
                            or previous_data.get("entity_id")
                        ),
                        "inline": True,
                    },
                    {
                        "name": "Chest Type",
                        "value": self._get_chest_display_name(chest_class),
                        "inline": True,
                    },
                    {"name": "Location", "value": coords, "inline": False},
                    {"name": "Chest Owner", "value": owner_display, "inline": False},
                ]
            )

        if map_field is not None:
            fields.append(map_field)

        if event_type == "vehicle_attached":
            container_display = "Vehicle"
            if container_entity_id:
                container_display += f" (ID: {container_entity_id})"

        if event_type == "renamed":
            prev_name = details.get("previous_custom_name") or "No name"
            fields.append(
                {"name": "Previous Name", "value": prev_name, "inline": False}
            )

        if event_type == "vehicle_owner_mismatch":
            chest_owner = details.get("chest_owner", {})
            vehicle_owner = details.get("vehicle_owner", {})
            chest_owner_name = chest_owner.get("name") or owner_name
            chest_owner_steam = chest_owner.get("steam_id") or steam_id
            vehicle_owner_name = (
                vehicle_owner.get("name") or vehicle_owner_name or "Unknown"
            )
            vehicle_owner_steam = (
                vehicle_owner.get("steam_id") or vehicle_owner_steam or "N/A"
            )
            vehicle_id = record.get("vehicle_entity_id") or previous.get(
                "vehicle_entity_id"
            )
            description = (
                f"Chest owned by ({chest_owner_name}) is inside vehicle owned by ({vehicle_owner_name}).\n\n"
                f"CHEST ID: {current_data.get('entity_id') or previous_data.get('entity_id')}\n"
                f"VEHICLE ID: {vehicle_id or 'N/A'}"
            )
            fields = []

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "fields": fields,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "SCUM Backend • Chest Monitoring"},
        }

        return embed

    def _build_map_components(
        self,
        record: Dict[str, Any],
        previous: Dict[str, Any],
    ) -> Optional[List[Dict[str, Any]]]:
        """Construir botão de acesso ao SCUM Maps."""
        return None

    def _get_chest_display_name(self, chest_class: str) -> str:
        """Converter o nome da classe do baú para um formato amigável."""
        if not chest_class:
            return "Unknown"

        mapping = {
            "Improvised_Metal_Chest_ES": "Metal",
            "ImprovisedMetalChest": "Metal",
            "Improved_Wooden_Chest_ES": "Wooden",
            "ImprovedWoodenChest": "Wooden",
            "Improvised_Wooden_Chest_ES": "Wooden",
            "ImprovisedWoodenChest": "Wooden",
            "MedicalLocker_C": "Medical Locker",
            "ImprovisedWardrobe_C": "Wardrobe",
            "StorageShelf_C": "Storage Shelf",
            "WoodenWeaponRack_C": "Weapon Rack",
        }

        if chest_class in mapping:
            return mapping[chest_class]

        # fallback: tentar extrair palavra chave
        if "Wood" in chest_class or "Wooden" in chest_class:
            return "Wooden"
        if "Metal" in chest_class:
            return "Metal"
        if "Steel" in chest_class:
            return "Steel"

        return chest_class

    def _format_coords(
        self, x: Optional[Any], y: Optional[Any], z: Optional[Any]
    ) -> str:
        """Formatar coordenadas para exibição no formato Teleport (igual ao lockpicking_events)."""
        try:
            # Formato igual ao usado em minigame_notifier.py (lockpicking_events)
            # Usar 4 casas decimais para X e Y, e 0 casas para Z (sempre inteiro)
            z_value = float(z) if z is not None else 0
            return f"#Teleport {float(x):.4f} {float(y):.4f} {z_value:.0f}"
        except (TypeError, ValueError):
            return "Unknown"

    def _is_same_owner_vehicle(
        self,
        record: Optional[Dict[str, Any]],
        previous: Optional[Dict[str, Any]],
    ) -> bool:
        """Verificar se o proprietário do baú é o mesmo do veículo."""
        record = record or {}
        previous = previous or {}
        chest_owner_values = {
            self._normalize_owner_identifier(record.get("steam_id")),
            self._normalize_owner_identifier(previous.get("steam_id")),
            self._normalize_owner_identifier(record.get("owner_profile_id")),
            self._normalize_owner_identifier(previous.get("owner_profile_id")),
        }
        vehicle_owner_values = {
            self._normalize_owner_identifier(record.get("vehicle_owner_steam_id")),
            self._normalize_owner_identifier(previous.get("vehicle_owner_steam_id")),
            self._normalize_owner_identifier(record.get("vehicle_owner_player_id")),
            self._normalize_owner_identifier(previous.get("vehicle_owner_player_id")),
        }
        chest_owner_values.discard(None)
        vehicle_owner_values.discard(None)
        return bool(
            chest_owner_values
            and vehicle_owner_values
            and chest_owner_values & vehicle_owner_values
        )

    def _normalize_owner_identifier(self, value: Any) -> Optional[str]:
        """Converter identificadores de proprietários para string comparável."""
        if value is None:
            return None
        try:
            return str(value).strip()
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Persistência de alertas no histórico
    # ------------------------------------------------------------------ #
    def _history_was_mismatch_alert_sent(
        self,
        entity_id: int,
        vehicle_entity_id: Optional[int],
        vehicle_owner_steam_id: Optional[str],
    ) -> bool:
        """Verificar no histórico se o alerta já foi enviado para este mismatch."""
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                """
                SELECT 1
                FROM chest_history
                WHERE entity_id = ?
                  AND event_type = 'vehicle_owner_mismatch'
                  AND COALESCE(vehicle_entity_id, -1) = COALESCE(?, -1)
                  AND COALESCE(vehicle_owner_steam_id, '') = COALESCE(?, '')
                  AND discord_sent = 1
                ORDER BY event_at DESC
                LIMIT 1
                """,
                (entity_id, vehicle_entity_id, vehicle_owner_steam_id),
            ).fetchone()
        return bool(row)

    def _mark_history_discord_sent(self, history_row_id: int) -> None:
        """Marcar no histórico que o alerta já foi enviado (ou dispensado)."""
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chest_history SET discord_sent = 1 WHERE id = ?",
                (history_row_id,),
            )
            conn.commit()

    def _clear_history_alert_flags(self, entity_id: int) -> None:
        """Limpar controle em memória e sinalizar alertas resolvidos."""
        self._last_vehicle_mismatch_alerts.pop(entity_id, None)
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE chest_history
                SET discord_sent = 2
                WHERE entity_id = ?
                  AND event_type = 'vehicle_owner_mismatch'
                  AND discord_sent = 1
                """,
                (entity_id,),
            )
            conn.commit()

    def _resolve_chest_image_path(self, chest_class: Optional[str]) -> Optional[str]:
        """Descobrir o caminho da imagem correspondente ao tipo de baú."""
        if not chest_class:
            return None

        filename = f"{chest_class}.png"
        candidate = os.path.join(self.images_directory, filename)
        if os.path.exists(candidate):
            return candidate

        # Tentativa com nomes alternativos (sem sufixos específicos)
        if chest_class.endswith("_ES"):
            alt_filename = f"{chest_class[:-3]}.png"
            alt_candidate = os.path.join(self.images_directory, alt_filename)
            if os.path.exists(alt_candidate):
                return alt_candidate

        default_candidate = os.path.join(self.images_directory, "default.png")
        if os.path.exists(default_candidate):
            return default_candidate

        return None

    def _resolve_vehicle_image_path(
        self, vehicle_class: Optional[str]
    ) -> Optional[str]:
        """Descobrir o caminho da imagem correspondente ao tipo de veículo."""
        if not vehicle_class:
            return None

        normalized = vehicle_class.replace(" ", "_")
        candidates = [
            f"{normalized}.png",
            f"{normalized}_C.png",
            f"{normalized}_ES.png",
        ]

        # Também tentar versões lower-case
        candidates.extend([name.lower() for name in list(candidates)])

        for filename in candidates:
            candidate = os.path.join(self.vehicle_images_directory, filename)
            if os.path.exists(candidate):
                return candidate

        return None
