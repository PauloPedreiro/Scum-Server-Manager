import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests


@dataclass
class ProvisionResult:
    created_categories: int = 0
    reused_categories: int = 0
    created_channels: int = 0
    reused_channels: int = 0
    created_webhooks: int = 0
    reused_webhooks: int = 0
    updated_urls: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class DiscordBotProvisioner:
    """Provisiona categorias/canais/webhooks via Discord Bot Token (REST API).

    Observacoes:
    - Nao altera 'enabled' no webhooks.json.
    - Pode provisionar eventos enabled e disabled.
    - Usa apenas requests (sem dependencias extras).
    """

    DISCORD_API_BASE = "https://discord.com/api/v10"

    def __init__(
        self,
        bot_token: str,
        guild_id: str,
        logger: Optional[Any] = None,
        sleep_between_calls: float = 0.2,
    ):
        self.bot_token = (bot_token or "").strip()
        self.guild_id = str(guild_id or "").strip()
        self.logger = logger
        self.sleep_between_calls = float(sleep_between_calls or 0)

    def _log(self, msg: str):
        try:
            if self.logger is not None:
                self.logger.info(msg)
        except Exception:
            pass

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
        }

    def _to_discord_channel_name(self, raw: str, fallback: str) -> str:
        """Converte um texto qualquer para um nome de canal válido no Discord.

        Discord aceita emoji e caracteres unicode em nomes de canal.
        Apenas fazemos lowercase de ASCII, substituímos espaços por hífens e
        removemos caracteres de controle; emojis e símbolos são preservados.
        """
        try:
            s = str(raw or "").strip()
        except Exception:
            s = ""

        if not s:
            try:
                s = str(fallback or "").strip()
            except Exception:
                s = ""

        if not s:
            return "channel"

        # Lowercase apenas ASCII (preserva emoji/unicode)
        s = "".join(ch.lower() if ch.isascii() else ch for ch in s)
        s = s.replace("_", "-")
        s = re.sub(r"\s+", "-", s)
        # Remover apenas caracteres de controle ASCII (0x00-0x1F, 0x7F), manter todo o resto
        s = re.sub(r"[\x00-\x1f\x7f]", "", s)
        s = re.sub(r"-+", "-", s)
        s = s.strip("-")

        if not s:
            s = re.sub(r"[^a-z0-9-]", "", str(fallback or "").strip().lower())
            s = re.sub(r"-+", "-", s).strip("-")

        if not s:
            return "channel"

        if len(s) > 90:
            s = s[:90].rstrip("-")
        return s

    def test_connection(self, timeout: int = 10) -> Tuple[bool, str]:
        if not self.bot_token:
            return False, "Bot token is empty"
        if not self.guild_id:
            return False, "Guild ID is empty"

        try:
            r = requests.get(
                f"{self.DISCORD_API_BASE}/users/@me",
                headers=self._headers(),
                timeout=timeout,
            )
            if r.status_code != 200:
                return False, f"Failed to authenticate bot: HTTP {r.status_code} {self._safe_text(r)}"

            r2 = requests.get(
                f"{self.DISCORD_API_BASE}/guilds/{self.guild_id}",
                headers=self._headers(),
                timeout=timeout,
            )
            if r2.status_code != 200:
                return False, f"Failed to access guild: HTTP {r2.status_code} {self._safe_text(r2)}"

            return True, "OK"
        except Exception as e:
            return False, str(e)

    def provision_all_events(
        self,
        webhooks_v2: Dict[str, Any],
        include_disabled: bool = True,
        validate_existing_urls: bool = True,
        repair_invalid_urls: bool = True,
        progress_cb: Optional[Callable[[str], None]] = None,
        timeout: int = 20,
    ) -> Tuple[Dict[str, Any], ProvisionResult]:
        """Retorna (webhooks_v2_atualizado, result)."""

        result = ProvisionResult()

        ok, msg = self.test_connection(timeout=timeout)
        if not ok:
            result.errors.append(msg)
            return webhooks_v2, result

        events = (webhooks_v2 or {}).get("events")
        if not isinstance(events, dict):
            result.errors.append("Invalid webhooks.json v2: missing 'events'")
            return webhooks_v2, result

        defaults = (webhooks_v2 or {}).get("defaults")
        if not isinstance(defaults, dict):
            defaults = {}

        default_category_name = str(defaults.get("category_name") or "SSM").strip() or "SSM"
        webhook_name_prefix = str(defaults.get("webhook_name_prefix") or "SSM").strip() or "SSM"

        channels = self._get_guild_channels(timeout=timeout)
        if channels is None:
            result.errors.append("Failed to list guild channels")
            return webhooks_v2, result

        categories_by_name = {
            (c.get("name") or "").strip().lower(): c
            for c in channels
            if int(c.get("type", -1)) == 4
        }

        channels_by_id: Dict[str, Dict[str, Any]] = {}
        for c in channels:
            try:
                cid = c.get("id")
                if cid is not None:
                    channels_by_id[str(cid)] = c
            except Exception:
                continue

        def progress(m: str):
            if progress_cb is not None:
                try:
                    progress_cb(m)
                except Exception:
                    pass

        for event_key, ev in events.items():
            if not isinstance(ev, dict):
                continue

            enabled = bool(ev.get("enabled", False))
            if (not enabled) and (not include_disabled):
                continue

            target = ev.get("target")
            if not isinstance(target, dict):
                target = {}
                ev["target"] = target

            cat = target.get("category")
            if not isinstance(cat, dict):
                cat = {}
                target["category"] = cat

            chan = target.get("channel")
            if not isinstance(chan, dict):
                chan = {}
                target["channel"] = chan

            wh = target.get("webhook")
            if not isinstance(wh, dict):
                wh = {}
                target["webhook"] = wh

            category_name = str(cat.get("name") or default_category_name).strip() or default_category_name
            display_name = ""
            try:
                display_name = str(ev.get("display_name") or "").strip()
            except Exception:
                display_name = ""
            # O usuário controla o nome do canal via display_name.
            # `chan.name` é apenas cache do último nome provisionado.
            desired_channel_name = display_name.strip() if display_name else ""
            if not desired_channel_name:
                desired_channel_name = str(chan.get("name") or "").strip() or str(event_key)
            channel_name = self._to_discord_channel_name(desired_channel_name, fallback=str(event_key))

            # Se ja tem webhook.url, opcionalmente validar/reparar e descobrir channel_id se estiver faltando
            existing_url = wh.get("url")
            skip_webhook_provision = False
            if isinstance(existing_url, str) and existing_url.strip():
                wh_data = self._get_webhook_data(existing_url, timeout=timeout)
                if wh_data:
                    progress(f"[{event_key}] webhook url ok")
                    if validate_existing_urls:
                        skip_webhook_provision = True
                    # Se não tinhamos channel_id ou se o canal existe no discord, recuperar do webhook
                    wh_chan_id = str(wh_data.get("channel_id") or "").strip()
                    if wh_chan_id and (not chan.get("id") or str(chan.get("id")) not in channels_by_id):
                        chan["id"] = wh_chan_id
                else:
                    progress(f"[{event_key}] webhook url invalid")
                    if not repair_invalid_urls:
                        skip_webhook_provision = True

            # Garantir categoria
            category_obj = None
            existing_cat_id = cat.get("id")
            if existing_cat_id is not None:
                existing_cat_id = str(existing_cat_id).strip() or None

            # Se ja temos ID salvo, reaproveitar e (se necessario) renomear
            if existing_cat_id:
                existing_obj = channels_by_id.get(existing_cat_id)
                if isinstance(existing_obj, dict) and int(existing_obj.get("type", -1)) == 4:
                    current_name = str(existing_obj.get("name") or "").strip()
                    if current_name and current_name.strip().lower() != category_name.strip().lower():
                        progress(
                            f"[{event_key}] renaming category '{current_name}' -> '{category_name}'"
                        )
                        updated = self._patch_channel(
                            channel_id=existing_cat_id,
                            payload={"name": category_name},
                            timeout=timeout,
                        )
                        if updated is not None:
                            existing_obj.update(updated)
                            channels_by_id[existing_cat_id] = existing_obj
                            # Atualizar indice por nome
                            try:
                                categories_by_name.pop(current_name.lower(), None)
                            except Exception:
                                pass
                            categories_by_name[category_name.lower()] = existing_obj
                            time.sleep(self.sleep_between_calls)
                    category_obj = existing_obj

            if category_obj is None:
                category_obj = categories_by_name.get(category_name.lower())
            if category_obj is None:
                progress(f"[{event_key}] creating category '{category_name}'")
                category_obj = self._create_channel(
                    name=category_name,
                    channel_type=4,
                    parent_id=None,
                    timeout=timeout,
                )
                if category_obj is None:
                    result.errors.append(f"Failed to create category '{category_name}' for event '{event_key}'")
                    continue
                result.created_categories += 1
                categories_by_name[category_name.lower()] = category_obj
                try:
                    if category_obj.get("id") is not None:
                        channels_by_id[str(category_obj.get("id"))] = category_obj
                except Exception:
                    pass
                time.sleep(self.sleep_between_calls)
            else:
                result.reused_categories += 1

            category_id = str(category_obj.get("id"))
            cat["id"] = category_id
            cat["name"] = category_name

            # Garantir canal
            channel_obj = None
            existing_chan_id = chan.get("id")
            if existing_chan_id is not None:
                existing_chan_id = str(existing_chan_id).strip() or None

            # Se ja temos ID salvo, reaproveitar e (se necessario) renomear
            if existing_chan_id:
                existing_obj = channels_by_id.get(existing_chan_id)
                if isinstance(existing_obj, dict) and int(existing_obj.get("type", -1)) == 0:
                    current_name = str(existing_obj.get("name") or "").strip()
                    if current_name and current_name.strip().lower() != channel_name.strip().lower():
                        progress(
                            f"[{event_key}] renaming channel '{current_name}' -> '{channel_name}'"
                        )
                        updated = self._patch_channel(
                            channel_id=existing_chan_id,
                            payload={"name": channel_name},
                            timeout=timeout,
                        )
                        if updated is not None:
                            existing_obj.update(updated)
                            channels_by_id[existing_chan_id] = existing_obj
                            time.sleep(self.sleep_between_calls)
                    channel_obj = existing_obj

            if channel_obj is None:
                channel_obj = self._find_channel_by_name(
                    channels=channels,
                    name=channel_name,
                    parent_id=category_id,
                    channel_type=0,
                    event_key=event_key,
                )
                if channel_obj is not None:
                    # Se encontrou por alias / nome anterior, renomear para o novo padrão
                    current_name = str(channel_obj.get("name") or "").strip()
                    found_id = str(channel_obj.get("id") or "")
                    if current_name and current_name.strip().lower() != channel_name.strip().lower() and found_id:
                        progress(
                            f"[{event_key}] renaming channel '{current_name}' -> '{channel_name}'"
                        )
                        updated = self._patch_channel(
                            channel_id=found_id,
                            payload={"name": channel_name},
                            timeout=timeout,
                        )
                        if updated is not None:
                            channel_obj.update(updated)
                            channels_by_id[found_id] = channel_obj
                            time.sleep(self.sleep_between_calls)
            if channel_obj is None:
                progress(f"[{event_key}] creating channel '{channel_name}'")
                channel_obj = self._create_channel(
                    name=channel_name,
                    channel_type=0,
                    parent_id=category_id,
                    timeout=timeout,
                )
                if channel_obj is None:
                    result.errors.append(f"Failed to create channel '{channel_name}' for event '{event_key}'")
                    continue
                result.created_channels += 1
                channels.append(channel_obj)
                time.sleep(self.sleep_between_calls)
            else:
                result.reused_channels += 1

            channel_id = str(channel_obj.get("id"))
            chan["id"] = channel_id
            chan["name"] = channel_name

            # Garantir webhook
            if skip_webhook_provision:
                continue
            webhook_name = "*"
            wh["name"] = webhook_name

            hook = self._find_or_create_webhook(
                channel_id=channel_id,
                webhook_name=webhook_name,
                timeout=timeout,
                progress=progress,
                result=result,
            )
            if hook is None:
                result.errors.append(f"Failed to provision webhook for event '{event_key}'")
                continue

            wh["id"] = str(hook.get("id")) if hook.get("id") is not None else None
            url = hook.get("url")
            if isinstance(url, str) and url.strip():
                wh["url"] = url
                result.updated_urls += 1

        return webhooks_v2, result

    def _safe_text(self, resp: requests.Response) -> str:
        try:
            t = (resp.text or "").strip()
            if len(t) > 300:
                t = t[:300] + "..."
            return t
        except Exception:
            return ""

    def _get_guild_channels(self, timeout: int = 20) -> Optional[List[Dict[str, Any]]]:
        try:
            r = requests.get(
                f"{self.DISCORD_API_BASE}/guilds/{self.guild_id}/channels",
                headers=self._headers(),
                timeout=timeout,
            )
            if r.status_code != 200:
                self._log(f"Failed to list channels: HTTP {r.status_code} {self._safe_text(r)}")
                return None
            data = r.json()
            if isinstance(data, list):
                return data
            return None
        except Exception as e:
            self._log(f"Failed to list channels: {e}")
            return None

    def _create_channel(
        self,
        name: str,
        channel_type: int,
        parent_id: Optional[str],
        timeout: int = 20,
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {"name": name, "type": int(channel_type)}
        if parent_id:
            payload["parent_id"] = str(parent_id)
        try:
            r = requests.post(
                f"{self.DISCORD_API_BASE}/guilds/{self.guild_id}/channels",
                headers=self._headers(),
                json=payload,
                timeout=timeout,
            )
            if r.status_code not in (200, 201):
                self._log(f"Failed to create channel '{name}': HTTP {r.status_code} {self._safe_text(r)}")
                return None
            data = r.json()
            if isinstance(data, dict):
                return data
            return None
        except Exception as e:
            self._log(f"Failed to create channel '{name}': {e}")
            return None

    def _patch_channel(
        self, channel_id: str, payload: Dict[str, Any], timeout: int = 20
    ) -> Optional[Dict[str, Any]]:
        try:
            r = requests.patch(
                f"{self.DISCORD_API_BASE}/channels/{str(channel_id)}",
                headers=self._headers(),
                json=(payload or {}),
                timeout=timeout,
            )
            if r.status_code != 200:
                self._log(
                    f"Failed to patch channel '{channel_id}': HTTP {r.status_code} {self._safe_text(r)}"
                )
                return None
            data = r.json()
            if isinstance(data, dict):
                return data
            return None
        except Exception as e:
            self._log(f"Failed to patch channel '{channel_id}': {e}")
            return None

    EVENT_LEGACY_NAMES: Dict[str, List[str]] = {
        "top10_lockpicking": [
            "top20_lockpicking",
            "top20-lockpicking",
            "top20lockpicking",
            "top10-lockpicking",
            "top10_lockpicking",
            "top10lockpicking",
            "🔓┃top20-lockpicking",
            "🔓|top20-lockpicking",
            "top20-lockpicking",
        ],
        "top10_kills": [
            "top20_kills",
            "top20-kills",
            "top20kills",
            "top10-kills",
            "top10_kills",
            "🩸┃top20-kills",
        ],
        "top10_snipers": [
            "top20_snipers",
            "top20-snipers",
            "top20snipers",
            "top10-snipers",
            "top10_snipers",
            "🎯┃top20-snipers",
        ],
    }

    def _find_channel_by_name(
        self,
        channels: List[Dict[str, Any]],
        name: str,
        parent_id: Optional[str],
        channel_type: int,
        event_key: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        name_l = (name or "").strip().lower()
        # 1. Busca exata
        for c in channels or []:
            try:
                if int(c.get("type", -1)) != int(channel_type):
                    continue
                if (c.get("name") or "").strip().lower() != name_l:
                    continue
                if parent_id is not None and str(c.get("parent_id") or "") != str(parent_id):
                    continue
                return c
            except Exception:
                continue

        # 2. Busca por aliases legados (ex: top20 -> top10)
        if event_key and event_key in self.EVENT_LEGACY_NAMES:
            aliases = [a.lower() for a in self.EVENT_LEGACY_NAMES[event_key]]
            for c in channels or []:
                try:
                    if int(c.get("type", -1)) != int(channel_type):
                        continue
                    c_name = (c.get("name") or "").strip().lower()
                    c_clean = re.sub(r"[^a-z0-9]", "", c_name)
                    for alias in aliases:
                        alias_clean = re.sub(r"[^a-z0-9]", "", alias)
                        if c_name == alias or (alias_clean and c_clean == alias_clean):
                            if parent_id is not None and str(c.get("parent_id") or "") != str(parent_id):
                                continue
                            return c
                except Exception:
                    continue

        return None

    def _find_or_create_webhook(
        self,
        channel_id: str,
        webhook_name: str,
        timeout: int,
        progress: Callable[[str], None],
        result: ProvisionResult,
    ) -> Optional[Dict[str, Any]]:
        hooks = self._list_channel_webhooks(channel_id=channel_id, timeout=timeout)
        if hooks is None:
            progress(f"Failed to list webhooks for channel {channel_id}")
            return None

        for h in hooks:
            try:
                if (h.get("name") or "").strip().lower() == webhook_name.strip().lower():
                    result.reused_webhooks += 1
                    return h
            except Exception:
                continue

        progress(f"creating webhook '{webhook_name}'")
        hook = self._create_webhook(channel_id=channel_id, name=webhook_name, timeout=timeout)
        if hook is None:
            return None
        result.created_webhooks += 1
        return hook

    def _list_channel_webhooks(
        self, channel_id: str, timeout: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        try:
            r = requests.get(
                f"{self.DISCORD_API_BASE}/channels/{channel_id}/webhooks",
                headers=self._headers(),
                timeout=timeout,
            )
            if r.status_code != 200:
                self._log(f"Failed to list webhooks: HTTP {r.status_code} {self._safe_text(r)}")
                return None
            data = r.json()
            if isinstance(data, list):
                return data
            return None
        except Exception as e:
            self._log(f"Failed to list webhooks: {e}")
            return None

    def _create_webhook(
        self, channel_id: str, name: str, timeout: int = 20
    ) -> Optional[Dict[str, Any]]:
        try:
            r = requests.post(
                f"{self.DISCORD_API_BASE}/channels/{channel_id}/webhooks",
                headers=self._headers(),
                json={"name": name},
                timeout=timeout,
            )
            if r.status_code not in (200, 201):
                self._log(f"Failed to create webhook '{name}': HTTP {r.status_code} {self._safe_text(r)}")
                return None
            data = r.json()
            if isinstance(data, dict):
                return data
            return None
        except Exception as e:
            self._log(f"Failed to create webhook '{name}': {e}")
            return None

    def _get_webhook_data(self, url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Obtém dados do webhook (GET /webhooks/{id}/{token}), incluindo channel_id e guild_id."""
        parsed = self._parse_webhook_url(url)
        if parsed is None:
            return None
        wid, wtoken = parsed
        try:
            r = requests.get(
                f"{self.DISCORD_API_BASE}/webhooks/{wid}/{wtoken}",
                timeout=timeout,
            )
            if int(r.status_code) == 200:
                data = r.json()
                if isinstance(data, dict):
                    return data
            return None
        except Exception:
            return None

    def _validate_webhook_url(self, url: str, timeout: int = 10) -> bool:
        """Valida se o webhook existe (GET /webhooks/{id}/{token})."""
        return self._get_webhook_data(url, timeout=timeout) is not None

    def _parse_webhook_url(self, url: str) -> Optional[Tuple[str, str]]:
        u = (url or "").strip()
        m = re.match(r"^https?://(canary\.|ptb\.)?discord(app)?\.com/api/webhooks/(\d+)/(\S+)$", u)
        if not m:
            m = re.match(r"^https?://discord\.com/api/webhooks/(\d+)/(\S+)$", u)
        if not m:
            return None
        return m.group(3), m.group(4)
