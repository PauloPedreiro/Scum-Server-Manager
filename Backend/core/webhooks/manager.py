"""
Gerenciador de webhooks.json
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import shutil
from utils.logger import StructuredLogger


# Mapeamento de display_name padrão com ícone para eventos conhecidos
_DEFAULT_DISPLAY_NAMES: Dict[str, str] = {
    "serverstatus": "🟢┃serverstatus",
    "new_player": "👋┃new-player",
    "ban-list": "🚫┃ban-list",
    "players_online": "👥┃players-online",
    "vehicle_registration": "📋┃vehicle-registration",
    "chat_in_game": "💬┃chat-in-game",
    "adminlog": "🛡️┃adminlog",
    "vehicle-log": "🚗┃vehicle-log",
    "bunkers_status": "🏢┃bunkers-status",
    "register": "🔑┃register",
    "cargo_drop": "📦┃cargo-drop",

    "commands": "⌨️┃commands",
    "fishing_ranking": "🎣┃fishing-ranking",
    "kill_log": "💀┃kill-log",
    "chest_events": "📦┃chest-events",
    "chest_vehicle_alerts": "⚠️┃chest-vehicle-alerts",
    "shop-log": "🛒┃shop-log",
    "log-ssm": "🛰️┃log-ssm",
    "lockpicking_events": "🔒┃lockpicking-events",
    "top10_lockpicking": "🔓┃top10-lockpicking",
    "top20_lockpicking": "🔓┃top10-lockpicking",
    "top10_kills": "🩸┃top10-kills",
    "top20_kills": "🩸┃top10-kills",
    "bank_transaction": "💳┃bank-transaction",
    "mines_alerts": "⚠️┃mines-alerts",
    "events": "📅┃events",
    "playtime_rewards": "⏱️┃playtime-rewards",
}


class WebhooksManager:
    """Gerenciador de webhooks.json com backup automático"""

    def __init__(self, webhooks_path: str):
        """
        Inicializar gerenciador

        Args:
            webhooks_path: Caminho completo para o webhooks.json
        """
        self.webhooks_path = Path(webhooks_path)
        self.webhooks_dir = self.webhooks_path.parent
        self.logger = StructuredLogger()
        self.max_backups = 10

    def load(self) -> Dict[str, str]:
        """
        Carregar webhooks completos

        Mescla webhooks do arquivo atual com webhooks do exemplo para garantir
        que todos os webhooks estejam presentes, mesmo que com valores vazios.

        Returns:
            Dicionário com todos os webhooks {nome: url}
        """
        v2_data = self.load_v2()
        return self._extract_enabled_webhooks(v2_data)

    def load_v2(self) -> Dict[str, Any]:
        example_keys = self._load_example_keys()
        data = {}
        if self.webhooks_path.exists():
            try:
                with open(self.webhooks_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                self.logger.error(f"Erro ao carregar webhooks.json: {e}")
                raise

        if not isinstance(data, dict):
            data = {}

        schema_version = data.get("schema_version")
        if schema_version != 2:
            migrated = self._migrate_v1_to_v2(data, example_keys)
            try:
                if self.webhooks_path.exists():
                    self._create_backup()
                self._save_v2(migrated)
            except Exception as e:
                self.logger.warn(f"Falha ao salvar migração do webhooks.json: {e}")
            data = migrated

        modified = self._ensure_events_present(data, example_keys)
        modified = self._ensure_mines_alerts_channel_name(data) or modified
        modified = self._migrate_top20_to_top10_lockpicking(data) or modified
        modified = self._migrate_top20_to_top10_kills(data) or modified
        modified = self._cleanup_deprecated_events(data) or modified
        cleaned = self._cleanup_root_litter(data)
        if modified or cleaned:
            try:
                if self.webhooks_path.exists():
                    self._create_backup()
                self._save_v2(data)
            except Exception as e:
                self.logger.warn(f"Falha ao garantir estrutura do webhooks.json: {e}")

        return data

    def _migrate_top20_to_top10_lockpicking(self, v2_data: Dict[str, Any]) -> bool:
        """Migra automaticamente o evento antigo 'top20_lockpicking' para 'top10_lockpicking'"""
        try:
            if not isinstance(v2_data, dict) or v2_data.get("schema_version") != 2:
                return False
            events = v2_data.get("events")
            if not isinstance(events, dict):
                return False

            if "top20_lockpicking" in events and "top10_lockpicking" not in events:
                old_ev = events.pop("top20_lockpicking")
                if isinstance(old_ev, dict):
                    old_ev["display_name"] = "top10_lockpicking"
                    if isinstance(old_ev.get("target"), dict):
                        old_ev["target"]["channel"] = "top10-lockpicking"
                    events["top10_lockpicking"] = old_ev
                    return True
            elif "top20_lockpicking" in events and "top10_lockpicking" in events:
                old_ev = events.pop("top20_lockpicking")
                new_ev = events.get("top10_lockpicking", {})
                if isinstance(old_ev, dict) and isinstance(new_ev, dict):
                    old_url = str(
                        (old_ev.get("target") or {})
                        .get("webhook", {})
                        .get("url")
                        or ""
                    ).strip()
                    new_url = str(
                        (new_ev.get("target") or {})
                        .get("webhook", {})
                        .get("url")
                        or ""
                    ).strip()
                    if old_url and not new_url:
                        if "target" not in new_ev or not isinstance(new_ev["target"], dict):
                            new_ev["target"] = {}
                        if "webhook" not in new_ev["target"] or not isinstance(new_ev["target"]["webhook"], dict):
                            new_ev["target"]["webhook"] = {}
                        new_ev["target"]["webhook"]["url"] = old_url
                        new_ev["enabled"] = old_ev.get("enabled", True)
                return True
        except Exception:
            pass
        return False

    def _migrate_top20_to_top10_kills(self, v2_data: Dict[str, Any]) -> bool:
        """Migra automaticamente o evento antigo 'top20_kills' para 'top10_kills'"""
        try:
            if not isinstance(v2_data, dict) or v2_data.get("schema_version") != 2:
                return False
            events = v2_data.get("events")
            if not isinstance(events, dict):
                return False

            if "top20_kills" in events and "top10_kills" not in events:
                old_ev = events.pop("top20_kills")
                if isinstance(old_ev, dict):
                    old_ev["display_name"] = "top10_kills"
                    if isinstance(old_ev.get("target"), dict):
                        old_ev["target"]["channel"] = "top10-kills"
                    events["top10_kills"] = old_ev
                    return True
            elif "top20_kills" in events and "top10_kills" in events:
                old_ev = events.pop("top20_kills")
                new_ev = events.get("top10_kills", {})
                if isinstance(old_ev, dict) and isinstance(new_ev, dict):
                    old_url = str(
                        (old_ev.get("target") or {})
                        .get("webhook", {})
                        .get("url")
                        or ""
                    ).strip()
                    new_url = str(
                        (new_ev.get("target") or {})
                        .get("webhook", {})
                        .get("url")
                        or ""
                    ).strip()
                    if old_url and not new_url:
                        if "target" not in new_ev or not isinstance(new_ev["target"], dict):
                            new_ev["target"] = {}
                        if "webhook" not in new_ev["target"] or not isinstance(new_ev["target"]["webhook"], dict):
                            new_ev["target"]["webhook"] = {}
                        new_ev["target"]["webhook"]["url"] = old_url
                        new_ev["enabled"] = old_ev.get("enabled", True)
                return True
        except Exception:
            pass
        return False

    def _cleanup_deprecated_events(self, v2_data: Dict[str, Any]) -> bool:
        """Remove eventos obsoletos como 'timer' e 'top20_snipers' fundidos em outros canais."""
        try:
            if not isinstance(v2_data, dict) or v2_data.get("schema_version") != 2:
                return False
            events = v2_data.get("events")
            if not isinstance(events, dict):
                return False
            modified = False
            for deprecated_key in ["timer", "top20_snipers", "top10_snipers", "snipers_ranking"]:
                if deprecated_key in events:
                    del events[deprecated_key]
                    modified = True
            return modified
        except Exception:
            pass
        return False


    def _ensure_mines_alerts_channel_name(self, v2_data: Dict[str, Any]) -> bool:
        """Garante compatibilidade do mines_alerts com GUI/SSM legado.

        Alguns servidores antigos podem ter o evento sem 'target.channel' (ou com nome
        diferente). Para o mines alert, o canal deve ser sempre 'mines-alerts'.

        Nao sobrescreve URL/enabled, apenas garante a estrutura e o nome do canal.
        """
        try:
            if not isinstance(v2_data, dict) or v2_data.get("schema_version") != 2:
                return False

            events = v2_data.get("events")
            if not isinstance(events, dict):
                events = {}
                v2_data["events"] = events

            ev = events.get("mines_alerts")
            if not isinstance(ev, dict):
                defaults = v2_data.get("defaults")
                if not isinstance(defaults, dict):
                    defaults = {}
                    v2_data["defaults"] = defaults

                if "delivery_mode" not in defaults:
                    defaults["delivery_mode"] = "append"
                if "category_name" not in defaults:
                    defaults["category_name"] = "SSM"
                if "webhook_name_prefix" not in defaults:
                    defaults["webhook_name_prefix"] = "SSM"

                ev = {
                    "enabled": False,
                    "display_name": "mines_alerts",
                    "delivery": {"mode": str(defaults.get("delivery_mode") or "append")},
                    "target": {
                        "category": {
                            "name": str(defaults.get("category_name") or "SSM"),
                            "id": None,
                        },
                        "channel": {"name": "mines-alerts", "id": None},
                        "webhook": {
                            "name": f"{str(defaults.get('webhook_name_prefix') or 'SSM')} mines_alerts",
                            "id": None,
                            "url": None,
                        },
                    },
                    "state": {"last_message_id": None, "last_updated_at": None},
                }
                events["mines_alerts"] = ev
                return True

            target = ev.get("target")
            if not isinstance(target, dict):
                target = {}
                ev["target"] = target

            channel = target.get("channel")
            if not isinstance(channel, dict):
                channel = {"name": None, "id": None}
                target["channel"] = channel

            desired_name = "mines-alerts"
            current_name = channel.get("name")
            if not isinstance(current_name, str) or current_name.strip() != desired_name:
                channel["name"] = desired_name
                if "id" not in channel:
                    channel["id"] = None
                return True

            if "id" not in channel:
                channel["id"] = None
                return True

            return False
        except Exception:
            return False

    def _cleanup_root_litter(self, v2_data: Dict[str, Any]) -> bool:
        """Remove chaves antigas no root (fora de 'events') que ficaram do formato v1.

        Para evitar apagar metadados futuros, só remove chaves extras quando o valor
        estiver vazio (ex.: "", None, {}, []).
        """
        try:
            if not isinstance(v2_data, dict):
                return False
            if v2_data.get("schema_version") != 2:
                return False

            allowed = {"schema_version", "defaults", "events"}
            to_delete: List[str] = []
            for k, v in list(v2_data.items()):
                if k in allowed:
                    continue

                is_empty = False
                if v is None:
                    is_empty = True
                elif isinstance(v, str) and not v.strip():
                    is_empty = True
                elif isinstance(v, dict) and not v:
                    is_empty = True
                elif isinstance(v, list) and not v:
                    is_empty = True

                if is_empty:
                    to_delete.append(str(k))

            if not to_delete:
                return False

            for k in to_delete:
                try:
                    del v2_data[k]
                except Exception:
                    pass
            return True
        except Exception:
            return False

    def replace_all_v2(self, new_data: Dict[str, Any], create_backup: bool = True) -> bool:
        if create_backup:
            self._create_backup()
        self._save_v2(new_data)
        return True

    def update_event_webhook_url(
        self, event_key: str, url: str, create_backup: bool = True
    ) -> bool:
        data = self.load_v2()
        events = data.get("events")
        if not isinstance(events, dict):
            raise KeyError("Invalid webhooks.json v2: missing 'events'")
        if event_key not in events or not isinstance(events.get(event_key), dict):
            raise KeyError(f"Event '{event_key}' não existe")
        ev = events.get(event_key)
        target = ev.get("target")
        if not isinstance(target, dict):
            target = {}
            ev["target"] = target
        webhook = target.get("webhook")
        if not isinstance(webhook, dict):
            webhook = {}
            target["webhook"] = webhook
        webhook["url"] = url
        if create_backup:
            self._create_backup()
        self._save_v2(data)
        return True

    def list_events_simple(self) -> Dict[str, str]:
        """Retorna {event_key: webhook_url_or_empty} para uso na GUI.

        Inclui eventos enabled e disabled.
        """
        data = self.load_v2()
        events = (data or {}).get("events")
        if not isinstance(events, dict):
            return {}

        out: Dict[str, str] = {}
        for key, ev in events.items():
            if str(key) == "timer" or not isinstance(ev, dict):
                continue
            target = ev.get("target")
            if not isinstance(target, dict):
                out[str(key)] = ""
                continue
            webhook = target.get("webhook")
            if not isinstance(webhook, dict):
                out[str(key)] = ""
                continue
            url = webhook.get("url")
            out[str(key)] = (url.strip() if isinstance(url, str) else "")
        return out

    def list_events_meta(self) -> Dict[str, Dict[str, Any]]:
        data = self.load_v2()
        events = (data or {}).get("events")
        if not isinstance(events, dict):
            return {}

        out: Dict[str, Dict[str, Any]] = {}
        for key, ev in events.items():
            if str(key) == "timer" or not isinstance(ev, dict):
                continue


            target = ev.get("target")
            webhook_url = ""
            if isinstance(target, dict):
                webhook = target.get("webhook")
                if isinstance(webhook, dict):
                    url = webhook.get("url")
                    webhook_url = (url.strip() if isinstance(url, str) else "")

            out[str(key)] = {
                "url": webhook_url,
                "enabled": bool(ev.get("enabled", False)),
                "display_name": str(ev.get("display_name") or ""),
            }
        return out

    def apply_events_meta_updates(
        self,
        updates: Dict[str, Dict[str, Any]],
        create_backup: bool = True,
    ) -> bool:
        data = self.load_v2()
        events = data.get("events")
        if not isinstance(events, dict):
            raise KeyError("Invalid webhooks.json v2: missing 'events'")

        modified = False
        for key, patch in (updates or {}).items():
            if key not in events or not isinstance(events.get(key), dict):
                continue
            ev = events.get(key)
            if not isinstance(ev, dict):
                continue

            target = ev.get("target")
            if not isinstance(target, dict):
                target = {}
                ev["target"] = target

            webhook = target.get("webhook")
            if not isinstance(webhook, dict):
                webhook = {}
                target["webhook"] = webhook

            if isinstance(patch, dict):
                if "url" in patch:
                    cleaned = str(patch.get("url") or "").strip()
                    webhook["url"] = cleaned if cleaned else None
                    modified = True

                if "enabled" in patch:
                    ev["enabled"] = bool(patch.get("enabled"))
                    modified = True

                if "display_name" in patch:
                    ev["display_name"] = str(patch.get("display_name") or "")
                    modified = True

        if modified:
            if create_backup:
                self._create_backup()
            self._save_v2(data)
        return True

    def patch_event_state(
        self, event_key: str, patch: Dict[str, Any], create_backup: bool = True
    ) -> bool:
        data = self.load_v2()
        events = data.get("events")
        if not isinstance(events, dict):
            raise KeyError("Invalid webhooks.json v2: missing 'events'")

        ev = events.get(event_key)
        if not isinstance(ev, dict):
            raise KeyError(f"Event '{event_key}' não existe")

        state = ev.get("state")
        if not isinstance(state, dict):
            state = {}
            ev["state"] = state

        if isinstance(patch, dict):
            for k, v in patch.items():
                state[str(k)] = v

        if create_backup:
            self._create_backup()
        self._save_v2(data)
        return True

    def apply_simple_updates(
        self,
        updates: Dict[str, str],
        create_backup: bool = True,
    ) -> bool:
        """Aplica atualizações vindas da GUI no v2.

        Regras:
        - Se URL nao vazia -> enabled=True
        - Se URL vazia -> enabled=False
        - Apenas chaves presentes em 'updates' sao alteradas.
        """
        data = self.load_v2()
        events = data.get("events")
        if not isinstance(events, dict):
            raise KeyError("Invalid webhooks.json v2: missing 'events'")

        modified = False
        for key, url in (updates or {}).items():
            if key not in events or not isinstance(events.get(key), dict):
                continue
            ev = events.get(key)

            target = ev.get("target")
            if not isinstance(target, dict):
                target = {}
                ev["target"] = target

            webhook = target.get("webhook")
            if not isinstance(webhook, dict):
                webhook = {}
                target["webhook"] = webhook

            cleaned = (url or "").strip()
            webhook["url"] = cleaned if cleaned else None
            ev["enabled"] = bool(cleaned)
            modified = True

        if modified:
            if create_backup:
                self._create_backup()
            self._save_v2(data)
        return True

    def _save_v2(self, data: Dict[str, Any]) -> None:
        self.webhooks_dir.mkdir(parents=True, exist_ok=True)
        with open(self.webhooks_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=False)
            f.write("\n")

    def _extract_enabled_webhooks(self, v2_data: Dict[str, Any]) -> Dict[str, str]:
        events = (v2_data or {}).get("events")
        if not isinstance(events, dict):
            return {}
        out: Dict[str, str] = {}
        for key, ev in events.items():
            if not isinstance(ev, dict):
                continue
            if not bool(ev.get("enabled", False)):
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

    def _load_example_keys(self) -> List[str]:
        example_webhooks = {}
        example_path = self.webhooks_path.parent / "webhooks.example.json"
        if example_path.exists():
            try:
                with open(example_path, "r", encoding="utf-8") as f:
                    example_webhooks = json.load(f)
            except Exception as e:
                self.logger.warn(f"Erro ao carregar webhooks.example.json: {e}")
        if isinstance(example_webhooks, dict) and example_webhooks:
            # Compat: exemplo antigo v1 (top-level {event_key: ""})
            if "events" not in example_webhooks:
                return [str(k) for k in example_webhooks.keys()]

            # Exemplo v2 (top-level {schema_version, defaults, events:{...}})
            events = example_webhooks.get("events")
            if isinstance(events, dict) and events:
                return [str(k) for k in events.keys()]

        return [
            "serverstatus",
            "new_player",
            "ban-list",
            "players_online",
            "vehicle_registration",
            "chat_in_game",
            "adminlog",
            "vehicle-log",
            "bunkers_status",
            "register",
            "cargo_drop",

            "mines_alerts",
            "commands",
            "fishing_ranking",
            "kill_log",
            "chest_events",
            "chest_vehicle_alerts",
            "shop-log",
            "log-ssm",
            "lockpicking_events",
            "top10_lockpicking",
            "top10_kills",
            "bank_transaction",
            "events",
            "playtime_rewards",
        ]

    def _migrate_v1_to_v2(self, v1_data: Dict[str, Any], example_keys: List[str]) -> Dict[str, Any]:
        defaults = {
            "category_name": "SSM",
            "webhook_name_prefix": "SSM",
            "delivery_mode": "append",
        }
        events: Dict[str, Any] = {}

        if isinstance(v1_data, dict):
            for key, url in v1_data.items():
                if key == "schema_version":
                    continue
                if key in {"defaults", "events", "discord"}:
                    continue
                enabled = isinstance(url, str) and bool(url.strip())
                events[str(key)] = {
                    "enabled": enabled,
                    "display_name": _DEFAULT_DISPLAY_NAMES.get(str(key), str(key)),
                    "delivery": {"mode": "append"},
                    "target": {
                        "category": {"name": defaults["category_name"], "id": None},
                        "channel": {"name": str(key), "id": None},
                        "webhook": {
                            "name": f"{defaults['webhook_name_prefix']} {key}",
                            "id": None,
                            "url": (url.strip() if isinstance(url, str) and url.strip() else None),
                        },
                    },
                    "state": {"last_message_id": None, "last_updated_at": None},
                }

        v2 = {
            "schema_version": 2,
            "defaults": defaults,
            "events": events,
        }

        self._ensure_events_present(v2, example_keys)
        return v2

    def _ensure_events_present(self, v2_data: Dict[str, Any], example_keys: List[str]) -> bool:
        if not isinstance(v2_data, dict):
            return False

        modified = False
        if v2_data.get("schema_version") != 2:
            v2_data["schema_version"] = 2
            modified = True

        defaults = v2_data.get("defaults")
        if not isinstance(defaults, dict):
            defaults = {}
            v2_data["defaults"] = defaults
            modified = True

        if "category_name" not in defaults:
            defaults["category_name"] = "SSM"
            modified = True
        if "webhook_name_prefix" not in defaults:
            defaults["webhook_name_prefix"] = "SSM"
            modified = True
        if "delivery_mode" not in defaults:
            defaults["delivery_mode"] = "append"
            modified = True

        events = v2_data.get("events")
        if not isinstance(events, dict):
            events = {}
            v2_data["events"] = events
            modified = True

        for key in example_keys:
            if key in events and isinstance(events.get(key), dict):
                continue
            events[str(key)] = {
                "enabled": False,
                "display_name": _DEFAULT_DISPLAY_NAMES.get(str(key), str(key)),
                "delivery": {"mode": str(defaults.get("delivery_mode") or "append")},
                "target": {
                    "category": {"name": str(defaults.get("category_name") or "SSM"), "id": None},
                    "channel": {"name": str(key), "id": None},
                    "webhook": {
                        "name": f"{str(defaults.get('webhook_name_prefix') or 'SSM')} {key}",
                        "id": None,
                        "url": None,
                    },
                },
                "state": {"last_message_id": None, "last_updated_at": None},
            }
            modified = True

        # Atualizar display_name de eventos existentes que ainda usam o nome plain
        for key, preferred in _DEFAULT_DISPLAY_NAMES.items():
            ev = events.get(key)
            if isinstance(ev, dict):
                cur = str(ev.get("display_name") or "").strip()
                if cur == key:
                    ev["display_name"] = preferred
                    modified = True

        return modified

    def get_webhook(self, webhook_name: str) -> Optional[str]:
        """
        Obter URL de um webhook específico

        Args:
            webhook_name: Nome do webhook

        Returns:
            URL do webhook ou None se não existir
        """
        webhooks = self.load()
        return webhooks.get(webhook_name)

    def get_webhook_names(self) -> List[str]:
        """
        Listar todos os nomes de webhooks disponíveis

        Returns:
            Lista com nomes dos webhooks
        """
        webhooks = self.load()
        return list(webhooks.keys())

    def update_webhook(
        self, webhook_name: str, url: str, create_backup: bool = True
    ) -> bool:
        """
        Atualizar um webhook específico (apenas webhooks existentes)

        Args:
            webhook_name: Nome do webhook
            url: URL do webhook
            create_backup: Se deve criar backup antes de atualizar

        Returns:
            True se atualizado com sucesso

        Raises:
            KeyError: Se o webhook não existir
        """
        try:
            # Carregar webhooks atuais
            webhooks = self.load()

            # Verificar se o webhook existe
            if webhook_name not in webhooks:
                raise KeyError(
                    f"Webhook '{webhook_name}' não existe. Apenas atualização de webhooks existentes é permitida."
                )

            # Criar backup se solicitado
            if create_backup:
                self._create_backup()

            # Atualizar webhook
            webhooks[webhook_name] = url

            # Salvar
            self._save(webhooks)

            self.logger.info(f"Webhook '{webhook_name}' atualizado com sucesso")
            return True

        except KeyError:
            raise
        except Exception as e:
            self.logger.error(f"Erro ao atualizar webhook '{webhook_name}': {e}")
            raise

    def update_webhooks(
        self, webhooks_updates: Dict[str, str], create_backup: bool = True
    ) -> List[str]:
        """
        Atualizar múltiplos webhooks (apenas webhooks existentes)

        Args:
            webhooks_updates: Dicionário com webhooks a atualizar {nome: url}
            create_backup: Se deve criar backup antes de atualizar

        Returns:
            Lista com nomes dos webhooks atualizados

        Raises:
            KeyError: Se algum webhook não existir
        """
        try:
            # Carregar webhooks atuais
            webhooks = self.load()

            # Verificar se todos os webhooks existem
            missing_webhooks = []
            for webhook_name in webhooks_updates.keys():
                if webhook_name not in webhooks:
                    missing_webhooks.append(webhook_name)

            if missing_webhooks:
                raise KeyError(
                    f"Webhooks não existem: {', '.join(missing_webhooks)}. Apenas atualização de webhooks existentes é permitida."
                )

            # Criar backup se solicitado
            if create_backup:
                self._create_backup()

            updated_webhooks = []

            # Atualizar cada webhook
            for webhook_name, url in webhooks_updates.items():
                webhooks[webhook_name] = url
                updated_webhooks.append(webhook_name)

            # Salvar
            self._save(webhooks)

            self.logger.info(f"Webhooks atualizados: {', '.join(updated_webhooks)}")
            return updated_webhooks

        except KeyError:
            raise
        except Exception as e:
            self.logger.error(f"Erro ao atualizar webhooks: {e}")
            raise

    def replace_all(
        self, new_webhooks: Dict[str, str], create_backup: bool = True
    ) -> bool:
        """
        Substituir todos os webhooks

        Args:
            new_webhooks: Novo dicionário completo de webhooks
            create_backup: Se deve criar backup antes de substituir

        Returns:
            True se substituído com sucesso
        """
        try:
            # Criar backup se solicitado
            if create_backup:
                self._create_backup()

            # Salvar novos webhooks
            self._save(new_webhooks)

            self.logger.info("Webhooks completos substituídos com sucesso")
            return True

        except Exception as e:
            self.logger.error(f"Erro ao substituir webhooks: {e}")
            raise

    def test_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """
        Testar um webhook enviando uma mensagem de teste

        Args:
            webhook_url: URL do webhook a testar

        Returns:
            Dicionário com resultado do teste
        """
        import requests

        try:
            # Criar mensagem de teste
            test_embed = {
                "title": "🧪 Teste de Webhook",
                "description": "Esta é uma mensagem de teste enviada pelo SCUM Backend.",
                "color": 0x0099FF,  # Azul
                "fields": [
                    {
                        "name": "Status",
                        "value": "✅ Webhook funcionando corretamente!",
                        "inline": False,
                    },
                    {
                        "name": "Data/Hora",
                        "value": datetime.now().strftime("%d/%m/%Y às %H:%M:%S"),
                        "inline": False,
                    },
                ],
                "footer": {"text": "SCUM Backend - Management System"},
            }

            payload = {"embeds": [test_embed]}

            # Enviar requisição
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in (200, 204):
                self.logger.info(
                    f"Teste de webhook bem-sucedido: {webhook_url[:50]}..."
                )
                return {
                    "success": True,
                    "message": "Webhook testado com sucesso",
                    "status_code": response.status_code,
                }
            else:
                error_msg = response.text[:200] if response.text else "Sem detalhes"
                self.logger.error(
                    f"Erro ao testar webhook: {response.status_code} - {error_msg}"
                )
                return {
                    "success": False,
                    "message": f"Erro ao testar webhook: {response.status_code}",
                    "status_code": response.status_code,
                    "error": error_msg,
                }

        except requests.exceptions.Timeout:
            self.logger.error("Timeout ao testar webhook")
            return {
                "success": False,
                "message": "Timeout ao testar webhook",
                "error": "A requisição demorou mais de 10 segundos",
            }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro de rede ao testar webhook: {e}")
            return {
                "success": False,
                "message": "Erro de rede ao testar webhook",
                "error": str(e),
            }
        except Exception as e:
            self.logger.error(f"Erro inesperado ao testar webhook: {e}")
            return {
                "success": False,
                "message": "Erro inesperado ao testar webhook",
                "error": str(e),
            }

    def _save(self, webhooks: Dict[str, str]) -> None:
        """
        Salvar webhooks no arquivo

        Args:
            webhooks: Dicionário com webhooks
        """
        # Garantir que o diretório existe
        self.webhooks_dir.mkdir(parents=True, exist_ok=True)

        # Salvar com formatação (preservar ordem das chaves)
        with open(self.webhooks_path, "w", encoding="utf-8") as f:
            json.dump(webhooks, f, indent=2, ensure_ascii=False, sort_keys=False)
            f.write("\n")

    def _create_backup(self) -> str:
        """
        Criar backup do webhooks.json

        Returns:
            Caminho do arquivo de backup criado
        """
        return None
        if not self.webhooks_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"webhooks.backup.{timestamp}.json"
        backup_path = self.webhooks_dir / backup_filename

        try:
            shutil.copy2(self.webhooks_path, backup_path)
            self.logger.info(f"Backup criado: {backup_filename}")

            # Limpar backups antigos
            self._cleanup_old_backups()

            return str(backup_path)

        except Exception as e:
            self.logger.error(f"Erro ao criar backup: {e}")
            raise

    def _cleanup_old_backups(self) -> None:
        """Limpar backups antigos, mantendo apenas os últimos N"""
        try:
            # Listar todos os backups
            backups = sorted(
                self.webhooks_dir.glob("webhooks.backup.*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            # Remover backups excedentes
            if len(backups) > self.max_backups:
                for backup in backups[self.max_backups :]:
                    backup.unlink()
                    self.logger.debug(f"Backup antigo removido: {backup.name}")

        except Exception as e:
            self.logger.warn(f"Erro ao limpar backups antigos: {e}")

    def list_backups(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Listar backups disponíveis

        Args:
            limit: Número máximo de backups a retornar

        Returns:
            Lista de dicionários com informações dos backups
        """
        backups = []

        try:
            backup_files = sorted(
                self.webhooks_dir.glob("webhooks.backup.*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:limit]

            for backup_file in backup_files:
                stat = backup_file.stat()
                backups.append(
                    {
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "size": stat.st_size,
                    }
                )

        except Exception as e:
            self.logger.error(f"Erro ao listar backups: {e}")

        return backups

    def restore_backup(self, backup_filename: str, create_backup: bool = True) -> bool:
        """
        Restaurar webhooks de um backup

        Args:
            backup_filename: Nome do arquivo de backup (ex: "webhooks.backup.20251202_153045.json")
            create_backup: Se deve criar backup dos webhooks atuais antes de restaurar

        Returns:
            True se restaurado com sucesso
        """
        backup_path = self.webhooks_dir / backup_filename

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup não encontrado: {backup_filename}")

        try:
            # Criar backup dos webhooks atuais se solicitado
            if create_backup and self.webhooks_path.exists():
                self._create_backup()

            # Restaurar backup
            shutil.copy2(backup_path, self.webhooks_path)

            self.logger.info(f"Webhooks restaurados do backup: {backup_filename}")
            return True

        except Exception as e:
            self.logger.error(f"Erro ao restaurar backup: {e}")
            raise
