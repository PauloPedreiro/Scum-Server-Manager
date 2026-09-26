import sys
import types
if "audioop" not in sys.modules:
    try:
        import audioop  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        _audioop = types.ModuleType("audioop")
        _audioop.error = Exception
        sys.modules["audioop"] = _audioop

import asyncio

import discord

import os

import secrets

import sqlite3

import threading

import time

from datetime import datetime, timedelta

from typing import Any, Dict, Optional






class TeleportEventButton(discord.ui.Button):
    """Persistent event teleport button."""
    def __init__(self, event_id: int, service):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Pegar Código",
            emoji="🌀",
            custom_id=f"teleport_event:{event_id}"
        )
        self.service = service

    async def callback(self, interaction: discord.Interaction):
        try:
            if self.service is None:
                # Tentar recuperar do Singleton
                from core.discord_bot_service import DiscordBotService
                self.service = DiscordBotService._instance

            if self.service:
                self.service._log_info("--- TeleportEventButton.callback iniciou ---")
            else:
                print("--- TeleportEventButton.callback iniciou (service is None) ---")

            if self.service is None:
                await interaction.response.send_message("❌ Erro interno: Bot service não disponível.", ephemeral=True)
                return

            def log_debug(msg: str):
                if self.service:
                    self.service._log_info(f"[TELEPORT_DEBUG] {msg}")
                else:
                    print(f"[TELEPORT_DEBUG] {msg}")

            await self.service._handle_teleport_interaction(interaction, log_debug)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            msg_err = f"ERRO CRÍTICO no callback da View:\n{tb}"
            if self.service:
                self.service._log_error(msg_err)
            else:
                print(msg_err)
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=True)
                await interaction.followup.send("❌ Erro interno ao processar seu teleporte.", ephemeral=True)
            except Exception:
                pass




class TeleportEventView(discord.ui.View):
    """Persistent view for the event teleport button."""
    def __init__(self, event_id: int, service):
        super().__init__(timeout=None)
        self.add_item(TeleportEventButton(event_id, service))


class SSMDiscordClient(discord.Client):

    def __init__(self, service, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.service = service

        self.tree = discord.app_commands.CommandTree(self)



    async def on_ready(self):

        try:

            self.service._log_info(f"DiscordBotService online as {self.user}")

            # Register persistent views for active events
            await self._refresh_event_views()

            # Register persistent view for register select menu
            try:
                self.add_view(self.service._build_register_view())
            except Exception as e_view:
                self.service._log_warn(f"DiscordBotService: Failed to add register view: {e_view}")

            channel_id = self.service._load_register_channel_id()
            if channel_id:
                await self.service._ensure_register_message(channel_id)
            else:
                self.service._log_warn("DiscordBotService: register channel id missing (events.register.target.channel.id)")




            try:

                await self.tree.sync()

            except Exception:

                pass

            try:
                from app.extensions import get_services
                services = get_services()
                online_monitor = getattr(services, 'online_monitor', None)
                if online_monitor:
                    count = len(online_monitor.online_players)
                    max_players = online_monitor.config.get("server", {}).get("max_players", 64)
                    await self.service._update_bot_status_async(count, max_players)
            except Exception as e_status:
                self.service._log_warn(f"Failed to update status on ready: {e_status}")

        except Exception as e:

            self.service._log_warn(f"DiscordBotService on_ready failed: {e}")



    async def on_interaction(self, interaction: discord.Interaction):
        try:
            data = interaction.data
            custom_id = data.get("custom_id") if isinstance(data, dict) else getattr(data, "custom_id", None)
            self.service._log_info(f"[DEBUG_INTERACTION] Recebida interação type={interaction.type} custom_id={custom_id} user={interaction.user}")
        except Exception:
            pass

        # Forward slash commands and autocomplete to CommandTree
        if interaction.type in (discord.InteractionType.application_command, discord.InteractionType.autocomplete):
            try:
                self.tree._from_interaction(interaction)
            except Exception as e:
                self.service._log_error(f"DiscordBotService process_application_commands error: {e}")

    async def _refresh_event_views(self):
        """Registra views persistentes para todos os eventos ativos no banco."""
        try:
            import sqlite3 as _sqlite3
            with _sqlite3.connect(self.service.ssm_db_path) as conn:
                conn.row_factory = _sqlite3.Row
                cur = conn.execute("SELECT event_id, name FROM event_configs WHERE status = 'active'")
                rows = cur.fetchall()
            for row in rows:
                event_id = row["event_id"]
                view = TeleportEventView(event_id, self.service)
                self.add_view(view)
                self.service._log_info(f"[BOT] View de teleporte registrada para evento {event_id}: {row['name']}")
            
            # Limpar automaticamente mensagens de eventos órfãos ou excluídos
            await self._cleanup_orphaned_event_messages()
        except Exception as e:
            self.service._log_error(f"[BOT] Erro ao registrar views de eventos: {e}")

    async def _cleanup_orphaned_event_messages(self):
        """Busca mensagens no canal de eventos e deleta as que pertencem a eventos inativos ou deletados."""
        try:
            channel_id_str = None
            try:
                import json, os
                wh_path = "data/webhooks.json"
                if os.path.exists(wh_path):
                    with open(wh_path, "r", encoding="utf-8") as f:
                        wh_data = json.load(f)
                    events_cfg = wh_data.get("events", {})
                    target = events_cfg.get("target", {})
                    if isinstance(target, dict):
                        channel_id_str = target.get("channel", {}).get("id")
            except Exception:
                pass

            if not channel_id_str:
                return

            channel_id = int(channel_id_str)
            channel = self.get_channel(channel_id)
            if not channel:
                channel = await self.fetch_channel(channel_id)
            if not channel:
                return

            import sqlite3 as _sqlite3
            active_ids = set()
            try:
                with _sqlite3.connect(self.service.ssm_db_path) as conn:
                    cur = conn.execute("SELECT event_id FROM event_configs WHERE status = 'active'")
                    active_ids = {row[0] for row in cur.fetchall()}
            except Exception as e:
                self.service._log_error(f"[BOT] Erro ao buscar eventos ativos no banco durante cleanup: {e}")
                return

            async for message in channel.history(limit=50):
                has_event_button = False
                event_id_found = None
                if message.components:
                    for comp in message.components:
                        for child in comp.children:
                            custom_id = getattr(child, "custom_id", None)
                            if custom_id and custom_id.startswith("teleport_event:"):
                                has_event_button = True
                                try:
                                    event_id_found = int(custom_id.split(":")[1])
                                except Exception:
                                    pass
                                break
                        if has_event_button:
                            break

                if has_event_button:
                    if event_id_found is None or event_id_found not in active_ids:
                        self.service._log_info(f"[BOT] Deletando mensagem orfã/inativa do evento {event_id_found}: ID {message.id}")
                        try:
                            await message.delete()
                        except Exception as de:
                            self.service._log_error(f"[BOT] Erro ao deletar mensagem orfã {message.id}: {de}")
        except Exception as e:
            self.service._log_error(f"[BOT] Erro geral no _cleanup_orphaned_event_messages: {e}")

    def register_event_view(self, event_id: int):
        def _register():
            try:
                view = TeleportEventView(event_id, self.service)
                self.add_view(view)
                self.service._log_info(f"[BOT] View de teleporte registrada para novo evento {event_id}")
            except Exception as e:
                self.service._log_error(f"[BOT] Erro ao registrar view para evento {event_id}: {e}")

        loop = getattr(self, "_connection", None) and getattr(self._connection, "loop", None)
        if loop and hasattr(loop, "call_soon_threadsafe") and loop.is_running():
            loop.call_soon_threadsafe(_register)
        else:
            _register()

    async def on_message(self, message):

        try:

            if message.author.bot:

                return

            chan = getattr(message, "channel", None)

            if chan is None:

                return

            channel_id = self.service._get_admin_link_channel_id()

            if not channel_id:

                return

            if int(getattr(chan, "id", 0) or 0) != int(channel_id):

                return



            content = str(getattr(message, "content", "") or "").strip()

            if not content:

                return

            if not content.lower().startswith("!link "):

                return



            parts = content.split()

            if len(parts) < 2:

                return

            code = str(parts[1]).strip()

            uid = int(getattr(message.author, "id", 0) or 0)

            ok, payload = self.service._consume_admin_link_code(code, uid)



            try:

                await message.delete()

            except Exception:

                pass



            if ok:

                try:

                    await self.service._send_dm_async(uid, "Discord account linked successfully.")

                except Exception:

                    pass

                return



            try:

                await self.service._send_dm_async(uid, "Failed to link Discord account.")

            except Exception:

                pass

        except Exception as e:

            try:

                self.service._log_warn(f"DiscordBotService on_message failed: {e}")

            except Exception:

                pass





class DiscordBotService:
    _instance = None  # Singleton reference for access from EventManager

    def __init__(

        self,

        config: Dict[str, Any],

        ssm_db_path: str = "data/SSM.db",

        logger: Optional[Any] = None,

        webhooks_path: str = "data/webhooks.json",

        auth_manager: Optional[Any] = None,

    ):

        self.config = config or {}

        self.ssm_db_path = str(ssm_db_path or "data/SSM.db")

        self.logger = logger

        self.webhooks_path = str(webhooks_path or "data/webhooks.json")

        self.auth_manager = auth_manager



        self._thread: Optional[threading.Thread] = None

        self._stop_event = threading.Event()

        self._loop: Optional[asyncio.AbstractEventLoop] = None



        self._bot = None
        DiscordBotService._instance = self  # Register singleton



    def _get_guild_id(self) -> str:

        try:

            bot_cfg = self.config.get("discord_bot")

            if not isinstance(bot_cfg, dict):

                return ""

            return str(bot_cfg.get("guild_id") or "").strip()

        except Exception:

            return ""



    def _get_register_role_id(self) -> str:

        try:

            bot_cfg = self.config.get("discord_bot")

            if not isinstance(bot_cfg, dict):

                return ""

            return str(bot_cfg.get("register_role_id") or "").strip()

        except Exception:

            return ""



    async def _assign_register_role_async(self, discord_user_id: int) -> tuple[bool, str]:

        try:

            if self._bot is None:

                return False, "bot_not_ready"



            gid_raw = self._get_guild_id()

            rid_raw = self._get_register_role_id()

            if not gid_raw:

                return False, "guild_id_missing"

            if not rid_raw:

                return False, "disabled"



            try:

                guild_id = int(gid_raw)

            except Exception:

                return False, "guild_id_invalid"

            try:

                role_id = int(rid_raw)

            except Exception:

                return False, "role_id_invalid"



            guild = self._bot.get_guild(int(guild_id))

            if guild is None:

                return False, "guild_not_found"



            role = guild.get_role(int(role_id))

            if role is None:

                return False, "role_not_found"



            try:

                member = await guild.fetch_member(int(discord_user_id))

            except Exception:

                member = None

            if member is None:

                return False, "member_not_found"



            try:

                await member.add_roles(role, reason="SSM register")

            except Exception:

                return False, "add_roles_failed"



            return True, "ok"

        except Exception:

            return False, "internal_error"



    def assign_register_role(self, discord_user_id: int) -> tuple[bool, str]:

        try:

            if self._loop is None or self._bot is None:

                return False, "bot_not_ready"



            rid_raw = self._get_register_role_id()

            if not str(rid_raw or "").strip():

                return False, "disabled"



            fut = asyncio.run_coroutine_threadsafe(

                self._assign_register_role_async(int(discord_user_id)),

                self._loop,

            )

            try:

                res = fut.result(timeout=20)

            except Exception:

                return False, "timeout"

            try:

                ok, reason = res

                return bool(ok), str(reason or "")

            except Exception:

                return False, "invalid_result"

        except Exception:

            return False, "internal_error"



    def _log_info(self, msg: str):

        try:

            if self.logger is not None:

                self.logger.info(msg)

            else:

                print(msg)

        except Exception:

            pass



    def _log_warn(self, msg: str):

        try:

            if self.logger is not None:

                self.logger.warn(msg)

            else:

                print(msg)

        except Exception:

            pass



    def _log_error(self, msg: str):

        try:

            if self.logger is not None:

                self.logger.error(msg)

            else:

                print(msg)

        except Exception:

            pass



    def _get_bot_token(self) -> str:

        try:

            bot_cfg = self.config.get("discord_bot")

            if not isinstance(bot_cfg, dict):

                return ""

            return str(bot_cfg.get("bot_token") or "").strip()

        except Exception:

            return ""



    def _get_admin_user_ids(self) -> set[int]:

        ids: set[int] = set()

        try:

            bot_cfg = self.config.get("discord_bot")

            if isinstance(bot_cfg, dict):

                raw = bot_cfg.get("admin_user_ids")

                if isinstance(raw, list):

                    for v in raw:

                        try:

                            ids.add(int(str(v).strip()))

                        except Exception:

                            continue

                elif isinstance(raw, str) and raw.strip():

                    for part in raw.split(","):

                        try:

                            ids.add(int(part.strip()))

                        except Exception:

                            continue

        except Exception:

            pass



        try:

            env_raw = (os.environ.get("SSM_DISCORD_ADMIN_USER_IDS", "") or "").strip()

            if env_raw:

                for part in env_raw.split(","):

                    try:

                        ids.add(int(part.strip()))

                    except Exception:

                        continue

        except Exception:

            pass



        return ids



    def _load_register_channel_id(self) -> Optional[int]:

        try:

            from core.webhooks.manager import WebhooksManager



            mgr = WebhooksManager(self.webhooks_path)

            v2 = mgr.load_v2()

            events = (v2 or {}).get("events")

            if not isinstance(events, dict):

                return None

            ev = events.get("register")

            if not isinstance(ev, dict):

                return None

            target = ev.get("target")

            if not isinstance(target, dict):

                return None

            chan = target.get("channel")

            if not isinstance(chan, dict):

                return None

            cid = chan.get("id")

            if cid is None:

                return None

            return int(str(cid).strip())

        except Exception:

            return None



    def _load_log_ssm_channel_id(self) -> Optional[int]:

        try:

            from core.webhooks.manager import WebhooksManager



            mgr = WebhooksManager(self.webhooks_path)

            v2 = mgr.load_v2()

            ev = ((v2 or {}).get("events") or {}).get("log-ssm")

            if not isinstance(ev, dict):

                return None

            target = ev.get("target")

            if not isinstance(target, dict):

                return None

            chan = target.get("channel")

            if not isinstance(chan, dict):

                return None

            cid = chan.get("id")

            if cid is None:

                return None

            return int(str(cid).strip())

        except Exception:

            return None



    def _get_admin_link_channel_id(self) -> Optional[int]:

        cid = self._load_log_ssm_channel_id()

        if cid:

            return cid



        try:

            self._log_warn(

                "DiscordBotService: log-ssm channel not found in webhooks.json; admin must create/configure it"

            )

        except Exception:

            pass

        return None



    def _consume_admin_link_code(self, code: str, discord_user_id: int) -> tuple[bool, str]:

        try:

            if not code:

                return False, "invalid_code"

            raw_code = str(code).strip()

            if not raw_code:

                return False, "invalid_code"

            if discord_user_id <= 0:

                return False, "invalid_discord_user_id"



            now = datetime.utcnow()

            with self._db_connect() as conn:

                conn.row_factory = sqlite3.Row

                cur = conn.execute(

                    """

                    SELECT *

                    FROM discord_admin_link_codes

                    WHERE code = ?

                    LIMIT 1

                    """,

                    (raw_code,),

                )

                row = cur.fetchone()

                if not row:

                    return False, "code_not_found"

                data = dict(row)

                if data.get("consumed_at"):

                    return False, "code_already_used"



                try:

                    expires_at = datetime.fromisoformat(str(data.get("expires_at") or ""))

                except Exception:

                    return False, "invalid_expires_at"



                if now > expires_at:

                    return False, "code_expired"



                user_id = int(data.get("user_id") or 0)

                if user_id <= 0:

                    return False, "invalid_user"



                cur = conn.execute(

                    "SELECT id, username, role, discord_user_id FROM frontend_users WHERE id = ? LIMIT 1",

                    (user_id,),

                )

                urow = cur.fetchone()

                if not urow:

                    return False, "user_not_found"

                u = dict(urow)



                existing_discord = str(u.get("discord_user_id") or "").strip()

                if existing_discord and existing_discord != str(discord_user_id):

                    return False, "already_linked"



                conn.execute(

                    """

                    UPDATE discord_admin_link_codes

                    SET consumed_at = ?, consumed_by_discord_user_id = ?

                    WHERE id = ?

                    """,

                    (now.isoformat(), str(discord_user_id), int(data.get("id") or 0)),

                )

                new_role = "admin" if str(u.get("role") or "").strip() == "admin_pending" else str(u.get("role") or "").strip()

                if not new_role:

                    new_role = "admin"

                conn.execute(

                    """

                    UPDATE frontend_users

                    SET discord_user_id = ?, role = ?, updated_at = ?

                    WHERE id = ?

                    """,

                    (str(discord_user_id), new_role, now.isoformat(), user_id),

                )

                conn.commit()

                return True, u.get("username") or ""

        except Exception as e:

            try:

                self._log_warn(f"DiscordBotService consume admin link code failed: {e}")

            except Exception:

                pass

            return False, "internal_error"



    def _get_register_state(self) -> Dict[str, Any]:

        try:

            from core.webhooks.manager import WebhooksManager



            mgr = WebhooksManager(self.webhooks_path)

            v2 = mgr.load_v2()

            ev = ((v2 or {}).get("events") or {}).get("register")

            if not isinstance(ev, dict):

                return {}

            st = ev.get("state")

            return dict(st) if isinstance(st, dict) else {}

        except Exception:

            return {}



    def _patch_register_state(self, patch: Dict[str, Any]) -> None:

        try:

            from core.webhooks.manager import WebhooksManager



            mgr = WebhooksManager(self.webhooks_path)

            v2 = mgr.load_v2()

            events = v2.get("events")

            if not isinstance(events, dict):

                return

            ev = events.get("register")

            if not isinstance(ev, dict):

                return

            st = ev.get("state")

            if not isinstance(st, dict):

                st = {}

                ev["state"] = st

            for k, v in (patch or {}).items():

                st[k] = v

            mgr.replace_all_v2(v2, create_backup=True)

        except Exception:

            pass



    def _db_connect(self) -> sqlite3.Connection:

        conn = sqlite3.connect(self.ssm_db_path, timeout=30.0)

        try:

            conn.execute("PRAGMA busy_timeout = 30000")

            conn.execute("PRAGMA foreign_keys = ON")

            conn.execute("PRAGMA journal_mode = WAL")

            conn.execute("PRAGMA synchronous = NORMAL")

        except Exception:

            pass

        return conn



    def _discord_already_linked(self, discord_user_id: int) -> bool:

        try:

            with self._db_connect() as conn:

                cur = conn.execute(

                    "SELECT steam_id FROM players WHERE discord_user_id = ? LIMIT 1",

                    (str(discord_user_id),),

                )

                row = cur.fetchone()

                return row is not None

        except Exception:

            return False



    def _create_or_replace_token(self, discord_user_id: int, ttl_minutes: int = 10) -> str:

        # One active token per discord_user_id

        code = f"SSM-{secrets.token_hex(3).upper()}"  # 6 hex chars

        now = datetime.utcnow()

        expires_at = now + timedelta(minutes=int(ttl_minutes))



        with self._db_connect() as conn:

            conn.execute(

                """

                UPDATE discord_link_tokens

                SET consumed_at = ?, consumed_by_steam_id = consumed_by_steam_id

                WHERE discord_user_id = ?

                  AND consumed_at IS NULL

                  AND expires_at > ?

                """,

                (now.isoformat(), str(discord_user_id), now.isoformat()),

            )

            conn.execute(

                """

                INSERT INTO discord_link_tokens

                    (code, discord_user_id, created_at, expires_at, consumed_at, consumed_by_steam_id)

                VALUES

                    (?, ?, ?, ?, NULL, NULL)

                """,

                (

                    code,

                    str(discord_user_id),

                    now.isoformat(),

                    expires_at.isoformat(),

                ),

            )

            conn.commit()



        return code



    def _build_register_view(self):

        import discord



        class SSMSelectMenu(discord.ui.Select):

            def __init__(self, service):

                options = [

                    discord.SelectOption(

                        label="Register Account",

                        description="Generate a temporary token to link your Steam account",

                        emoji="🔑",

                        value="register_account"

                    ),

                    discord.SelectOption(

                        label="Check Balance",

                        description="View your current SSM balance",

                        emoji="💰",

                        value="check_balance"

                    )

                ]

                super().__init__(

                    placeholder="Select an action...",

                    min_values=1,

                    max_values=1,

                    options=options,

                    custom_id="ssm_select_menu"

                )

                self.service = service



            async def callback(self, interaction: discord.Interaction):

                try:

                    user = getattr(interaction, "user", None)

                    if user is None:

                        return

                    discord_user_id = int(getattr(user, "id", 0) or 0)

                    if not discord_user_id:

                        return



                    if not self.values:

                        return



                    selected_value = self.values[0]



                    if selected_value == "register_account":

                        if self.service._discord_already_linked(discord_user_id):

                            await interaction.response.send_message(

                                "You already have a linked account. Contact an admin to unregister.",

                                ephemeral=True,

                            )

                            return



                        code = self.service._create_or_replace_token(discord_user_id)



                        await interaction.response.send_message(

                            "🔑 **Registration Protocol Initiated!**\n\n"

                            "Copy and paste the command below into the in-game chat (tap to copy on mobile):\n"

                            f"```\n!register {code}\n```\n"

                            "*This code expires in 10 minutes.*",

                            ephemeral=True,

                        )



                    elif selected_value == "check_balance":

                        with self.service._db_connect() as conn:

                            conn.row_factory = sqlite3.Row

                            cur = conn.execute(

                                "SELECT steam_id, player_name FROM players WHERE discord_user_id = ? LIMIT 1",

                                (str(discord_user_id),),

                            )

                            row = cur.fetchone()



                        if not row:

                            await interaction.response.send_message(

                                "❌ **Your Discord account is not registered.**\n"

                                "Please select **Register Account** from the dropdown menu above first.",

                                ephemeral=True

                            )

                            return



                        steam_id = row["steam_id"]

                        player_name = row["player_name"] or "Player"



                        from core.shop.wallet_service import WalletService

                        wallet = WalletService(self.service.ssm_db_path, logger=self.service.logger)

                        balance = wallet.get_balance(steam_id)



                        if balance < 100:

                            currency_display = f"🦷 {balance} Teeth"

                        elif balance < 1000:

                            currency_display = f"👂 {balance} Ears"

                        else:

                            currency_display = f"💀 {balance} Heads"



                        dark_joke = ""

                        if balance >= 50000:

                            import random

                            jokes = [

                                "💀 **WARNING:** That is a lot of heads... We recommend checking your chest's ventilation. The smell of 50,000 decaying brains must be... lovely.",

                                "💀 **WARNING:** 50,000? Are you trying to survive or are you starting a cannibalistic soup kitchen? TEC-1 sponsors do not recommend the latter.",

                                "💀 **WARNING:** With this many body parts, you could buy your freedom. Just kidding! TEC-1 owns your soul. Have a great broadcast!",

                                "💀 **WARNING:** That's enough teeth to build a new set of dentures for every zombie on the island. Are you a serial killer or just a very aggressive dentist?"

                            ]

                            dark_joke = f"\n\n{random.choice(jokes)}"



                        await interaction.response.send_message(

                            f"💰 Hello, **{player_name}**!\n\n"

                            f"Your current balance is:\n"

                            f"```\n{currency_display}\n```"

                            f"*(Linked Steam ID: `{steam_id}`)*"

                            f"{dark_joke}",

                            ephemeral=True

                        )

                except Exception as e:

                    try:

                        self.service._log_warn(f"Select menu callback failed: {e}")

                        await interaction.response.send_message(

                            "An error occurred while processing your request. Please try again.",

                            ephemeral=True

                        )

                    except Exception:

                        pass



        view = discord.ui.View(timeout=None)

        view.add_item(SSMSelectMenu(self))

        return view



    async def _ensure_register_message(self, channel_id: int):

        try:

            import discord



            channel = self._bot.get_channel(int(channel_id))

            if channel is None:

                try:

                    channel = await self._bot.fetch_channel(int(channel_id))

                except Exception:

                    channel = None



            if channel is None:

                self._log_warn("DiscordBotService: register channel not found")

                return



            state = self._get_register_state()
            last_message_id = state.get("last_message_id")
            msg = None

            if last_message_id:
                try:
                    fetched_msg = await channel.fetch_message(int(str(last_message_id).strip()))
                    # Verificar se a mensagem pertence ao bot atual (SSMBOT)
                    bot_user_id = getattr(self._bot.user, "id", None)
                    msg_author_id = getattr(getattr(fetched_msg, "author", None), "id", None)
                    if bot_user_id and msg_author_id == bot_user_id:
                        msg = fetched_msg
                    else:
                        # Mensagem pertence a um bot antigo ou outro autor; ignorar/remover
                        self._log_info("DiscordBotService: Mensagem de registro anterior pertence a outro bot/autor. Criando nova mensagem.")
                        try:
                            await fetched_msg.delete()
                        except Exception:
                            pass
                        msg = None
                except Exception:
                    msg = None

            view = self._build_register_view()

            embed = discord.Embed(
                title="[TEC-1 // CENTRAL DATABASE TERMINAL]",
                description=(
                    "**SYSTEM STATUS: CONNECTION DETACHED**\n\n"
                    "Your telemetry node is currently unlinked. To synchronize your in-game BCU (Brain Control Unit) and profile telemetry with the central server directory, please initialize the network registration protocol.\n\n"
                    "**OPERATIONAL INSTRUCTIONS:**\n"
                    "1. Open the dropdown menu below and select **Register Account**.\n"
                    "2. A secure, ephemeral linkage token will be generated for you.\n"
                    "3. Copy the token and paste it directly into the in-game global chat.\n\n"
                    "**ADDITIONAL UTILITIES:**\n"
                    "Use **Check Balance** from the dropdown menu to query your current biometric asset status at any time.\n\n"
                    "Already synchronized? Please contact system administration to purge your active connection record."
                ),
                color=0xE67E22,  # SCUM Orange
            )
            embed.set_footer(text="SSM // NETWORK CONTROL TERMINAL")

            if msg is None:
                sent = await channel.send(embed=embed, view=view)
                try:
                    self._patch_register_state({"last_message_id": str(sent.id)})
                except Exception:
                    pass
                return

            try:
                await msg.edit(embed=embed, view=view)
            except Exception:
                sent = await channel.send(embed=embed, view=view)
                try:
                    self._patch_register_state({"last_message_id": str(sent.id)})
                except Exception:
                    pass




        except Exception as e:

            self._log_warn(f"DiscordBotService: failed to ensure register message: {e}")



    async def _run_bot_async(self):

        import discord
        import ssl
        import certifi
        import aiohttp



        intents = discord.Intents.default()

        intents.guilds = True

        try:

            intents.message_content = True

        except Exception:

            pass



        # Cria um conector SSL usando o bundle de certificados do certifi.
        # Isso resolve SSLCertVerificationError no Windows quando o app é
        # empacotado com PyInstaller, pois o Python embutido perde acesso
        # ao store de certificados do sistema operacional.
        # Quando empacotado, o cacert.pem fica em sys._MEIPASS/certifi/.
        try:
            import sys as _sys
            import os as _os
            _meipass = getattr(_sys, '_MEIPASS', None)
            if _meipass:
                _cafile = _os.path.join(_meipass, 'certifi', 'cacert.pem')
                if not _os.path.exists(_cafile):
                    _cafile = certifi.where()
            else:
                _cafile = certifi.where()
            _ssl_ctx = ssl.create_default_context(cafile=_cafile)
            _connector = aiohttp.TCPConnector(ssl=_ssl_ctx)
            self._log_info(f"DiscordBotService: SSL connector criado com certifi ({_cafile})")
        except Exception as _ssl_err:
            self._log_warn(f"DiscordBotService: failed to create SSL connector with certifi, using default: {_ssl_err}")
            _connector = None

        self._bot = SSMDiscordClient(service=self, intents=intents, connector=_connector)



        service = self



        @self._bot.tree.command(name="ssm_reset_admin_password", description="Reset admin password")

        async def ssm_reset_admin_password(

            interaction: discord.Interaction,

            new_password: str,

            confirm: str,

        ):

            try:

                uid = int(getattr(getattr(interaction, "user", None), "id", 0) or 0)

                allowed = service._get_admin_user_ids()

                if not uid or not allowed or uid not in allowed:

                    try:

                        await interaction.response.send_message("Unauthorized", ephemeral=True)

                    except Exception:

                        pass

                    return



                if str(confirm or "").strip().upper() != "RESET":

                    try:

                        await interaction.response.send_message(

                            "Confirmation required. Set confirm to RESET.",

                            ephemeral=True,

                        )

                    except Exception:

                        pass

                    return



                if service.auth_manager is None:

                    try:

                        await interaction.response.send_message(

                            "Auth system not initialized",

                            ephemeral=True,

                        )

                    except Exception:

                        pass

                    return



                pwd = str(new_password or "").strip()

                if not pwd:

                    try:

                        await interaction.response.send_message(

                            "New password is required",

                            ephemeral=True,

                        )

                    except Exception:

                        pass

                    return



                is_valid, error_msg = service.auth_manager.password_handler.validate_password_strength(

                    pwd, min_length=8

                )

                if not is_valid:

                    try:

                        await interaction.response.send_message(

                            str(error_msg or "Invalid password"),

                            ephemeral=True,

                        )

                    except Exception:

                        pass

                    return



                admin_user = service.auth_manager.user_manager.get_user_by_username("admin")

                if not admin_user:

                    try:

                        await interaction.response.send_message(

                            "Admin user not found",

                            ephemeral=True,

                        )

                    except Exception:

                        pass

                    return



                now = datetime.utcnow().isoformat()

                new_password_hash = service.auth_manager.password_handler.hash_password(pwd)

                updated = service.auth_manager.user_manager.update_user(

                    admin_user["id"],

                    password_hash=new_password_hash,

                    password_changed=1,

                    last_password_change=now,

                )

                if not updated:

                    try:

                        await interaction.response.send_message(

                            "Failed to update password",

                            ephemeral=True,

                        )

                    except Exception:

                        pass

                    return



                try:

                    service._log_warn("Senha do admin foi resetada via DiscordBotService")

                except Exception:

                    pass



                try:

                    await interaction.response.send_message(

                        "Admin password reset successfully.",

                        ephemeral=True,

                    )

                except Exception:

                    pass

            except Exception as e:

                try:

                    service._log_warn(f"DiscordBotService reset admin password failed: {e}")

                except Exception:

                    pass

                try:

                    if not interaction.response.is_done():

                        await interaction.response.send_message(

                            "Internal error",

                            ephemeral=True,

                        )

                    else:

                        await interaction.followup.send(

                            "Internal error",

                            ephemeral=True,

                        )

                except Exception:

                    pass



        token = self._get_bot_token()

        if not token:

            self._log_warn("DiscordBotService: bot_token is empty; not starting")

            return



        await self._bot.start(token)



    def _get_teleport_details(self, discord_user_id: int, event_id: int) -> dict:
        try:
            # Query to see if the user is linked
            with self._db_connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute(
                    "SELECT steam_id, player_name FROM players WHERE discord_user_id = ? LIMIT 1",
                    (str(discord_user_id),)
                )
                player_row = cur.fetchone()

            if not player_row:
                return {
                    "success": False,
                    "error_msg": "❌ **Your Discord account is not linked to SSM.**\n"
                                 "Please use the registration channel to link your Discord account to your character/SteamID."
                }

            steam_id = player_row["steam_id"]
            player_name = player_row["player_name"] or "Player"

            # Verificar se o jogador está online no jogo
            with self._db_connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute(
                    "SELECT status FROM players_online WHERE steam_id = ? LIMIT 1",
                    (steam_id,)
                )
                online_row = cur.fetchone()

            is_online = online_row and online_row["status"] == "online"

            if not is_online:
                # Fallback: check RCON directly in real time
                try:
                    from core.rcon_queue_manager import RconQueueManager
                    from utils.rcon_client import parse_listplayers_response
                    rcon_q = RconQueueManager.get_instance()
                    raw = rcon_q.execute_command_sync("ListPlayers", delay_after=0.1, priority=1, timeout=5.0)
                    players = parse_listplayers_response(raw)
                    for p in players:
                        if p.get("steam_id") == steam_id:
                            is_online = True
                            # Also update the players_online table to online since we know they are online
                            with self._db_connect() as conn:
                                conn.execute(
                                    "UPDATE players_online SET status = 'online', last_updated = CURRENT_TIMESTAMP WHERE steam_id = ?",
                                    (steam_id,)
                                )
                            break
                except Exception as e:
                    self._log_warn(f"Failed to check real-time online status via RCON: {e}")

            if not is_online:
                self._log_info(f"[TELEPORT] Jogador {player_name} ({steam_id}) tentou teleporte mas está offline no jogo.")
                return {
                    "success": False,
                    "error_msg": "❌ **You must be online on the game server to teleport to the event.**\n"
                                 "Please connect to the server first and try again."
                }

            # Query if the event is active
            with self._db_connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute(
                    "SELECT status, name FROM event_configs WHERE event_id = ? LIMIT 1",
                    (event_id,)
                )
                event_row = cur.fetchone()

            if not event_row:
                return {
                    "success": False,
                    "error_msg": "❌ **Event not found.**"
                }

            if event_row["status"] != "active":
                return {
                    "success": False,
                    "error_msg": f"❌ **The event '{event_row['name']}' is no longer active.**"
                }

            # Get coordinates
            x, y, z = None, None, None
            coord_name = "Event Location"

            with self._db_connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute(
                    "SELECT name, x, y, z FROM event_coordinates WHERE event_id = ?",
                    (event_id,)
                )
                coord_rows = cur.fetchall()

            if coord_rows:
                import random
                chosen_coord = random.choice(coord_rows)
                coord_name = chosen_coord["name"]
                x, y, z = chosen_coord["x"], chosen_coord["y"], chosen_coord["z"]
            else:
                # Fallback: scan startup commands
                with self._db_connect() as conn:
                    conn.row_factory = sqlite3.Row
                    cur = conn.execute(
                        "SELECT command_string FROM event_startup_commands WHERE event_id = ? ORDER BY order_index ASC, startup_id ASC",
                        (event_id,)
                    )
                    commands = cur.fetchall()

                import re
                for cmd in commands:
                    cmd_str = cmd["command_string"]
                    # Try SCUM telemetry format
                    match = re.search(r'\{X=([\d\.\-]+)[,\s]+Y=([\d\.\-]+)[,\s]+Z=([\d\.\-]+)', cmd_str, re.IGNORECASE)
                    if match:
                        try:
                            x, y, z = float(match.group(1)), float(match.group(2)), float(match.group(3))
                            break
                        except ValueError:
                            pass

                    # Try ScheduleWorldEvent
                    match = re.search(r'#ScheduleWorldEvent\s+\S+\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)', cmd_str, re.IGNORECASE)
                    if match:
                        try:
                            x, y, z = float(match.group(1)), float(match.group(2)), float(match.group(3))
                            break
                        except ValueError:
                            pass

                    # Try general 3 numbers at the end
                    parts = cmd_str.split()
                    floats = []
                    for part in parts:
                        cleaned = re.sub(r'[^\d\.\-]', '', part)
                        if not cleaned:
                            continue
                        if len(cleaned) == 17 and cleaned.startswith("7656"):
                            continue
                        try:
                            floats.append(float(cleaned))
                        except ValueError:
                            pass

                    if len(floats) >= 3:
                        x, y, z = floats[-3], floats[-2], floats[-1]
                        break

            if x is None or y is None or z is None:
                return {
                    "success": False,
                    "error_msg": f"❌ **The event '{event_row['name']}' does not have any coordinates configured for teleport.**"
                }

            return {
                "success": True,
                "player_name": player_name,
                "steam_id": steam_id,
                "event_name": event_row["name"],
                "x": x,
                "y": y,
                "z": z,
                "coord_name": coord_name
            }

        except Exception as e:
            self._log_error(f"Error in _get_teleport_details: {e}")
            return {
                "success": False,
                "error_msg": "❌ **Internal error processing your teleport.**"
            }

    async def _handle_teleport_interaction(self, interaction: discord.Interaction, log_debug=None):
        if log_debug is None:
            def log_debug(msg): pass

        log_debug("Iniciando _handle_teleport_interaction")
        try:
            data = interaction.data
            custom_id = ""
            if isinstance(data, dict):
                custom_id = data.get("custom_id", "")
            elif data is not None:
                custom_id = getattr(data, "custom_id", "") or ""

            log_debug(f"custom_id extraído: {custom_id}")
            parts = custom_id.split(":")
            if len(parts) < 2:
                log_debug("parts < 2, retornando")
                return

            event_id_str = parts[1]
            try:
                event_id = int(event_id_str)
            except ValueError:
                log_debug(f"Falha ao converter event_id_str '{event_id_str}' para int")
                return

            log_debug(f"event_id parsed: {event_id}. Deferindo resposta...")
            
            # Defer response first to avoid timeout
            await interaction.response.defer(ephemeral=True)
            log_debug("Resposta deferida com sucesso!")

            discord_user_id = interaction.user.id
            log_debug(f"discord_user_id: {discord_user_id}. Conectando ao banco para verificar vínculo...")

            # 1. Query to see if the user is registered/linked
            with self._db_connect() as conn:
                conn.row_factory = sqlite3.Row
                log_debug("Conexão com banco obtida. Executando query de jogador...")
                cur = conn.execute(
                    "SELECT steam_id, player_name FROM players WHERE discord_user_id = ? LIMIT 1",
                    (str(discord_user_id),)
                )
                player_row = cur.fetchone()

            if player_row:
                log_debug(f"Jogador encontrado: steam_id={player_row['steam_id']}, player_name={player_row['player_name']}")
            else:
                log_debug("Jogador não encontrado no banco de dados!")

            if not player_row:
                log_debug("Enviando aviso de não registrado...")
                await interaction.followup.send("❌ **Você precisa registrar sua conta primeiro.**", ephemeral=True)
                log_debug("Aviso de não registrado enviado!")
                return

            steam_id = player_row["steam_id"]
            player_name = player_row["player_name"] or "Player"

            # Verificar se o jogador está preso
            try:
                from app.extensions import get_services
                svc = get_services()
                if getattr(svc, 'squad_tk_jail_service', None) and svc.squad_tk_jail_service.is_player_jailed(steam_id):
                    log_debug(f"Jogador {player_name} ({steam_id}) está preso. Impedindo teleporte pelo Discord.")
                    await interaction.followup.send("❌ **Você não pode se teleportar para eventos enquanto estiver preso!**", ephemeral=True)
                    return
            except Exception as jail_check_err:
                log_debug(f"Erro ao verificar se jogador está preso no teleporte do Discord: {jail_check_err}")

            log_debug("Consultando status do evento...")
            # 2. Check if the event is active
            with self._db_connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute(
                    "SELECT status, name FROM event_configs WHERE event_id = ? LIMIT 1",
                    (event_id,)
                )
                event_row = cur.fetchone()

            if event_row:
                log_debug(f"Evento encontrado: status={event_row['status']}, name={event_row['name']}")
            else:
                log_debug("Evento não encontrado no banco de dados!")

            if not event_row or event_row["status"] != "active":
                log_debug("Evento inativo ou inexistente. Enviando aviso...")
                await interaction.followup.send("❌ **O evento não está ativo.**", ephemeral=True)
                log_debug("Aviso de evento inativo enviado!")
                return

            event_name = event_row["name"]

            # 3. Read/write to JSON file with threading lock
            log_debug("Lendo arquivo JSON de códigos...")
            import json
            import secrets
            import threading
            from pathlib import Path
            codes_file = str(Path(self.ssm_db_path).parent / "event_teleport_codes.json")
            
            # Ensure the directory exists
            os.makedirs(str(Path(self.ssm_db_path).parent), exist_ok=True)
            
            # Simple file-lock / mutex mechanism
            lock = threading.Lock()
            
            code = None
            with lock:
                data = {"codes": {}}
                if os.path.exists(codes_file):
                    try:
                        with open(codes_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        log_debug(f"JSON lido com sucesso. Total de códigos: {len(data.get('codes', {}))}")
                    except Exception as e_json:
                        log_debug(f"Erro ao ler JSON existente: {e_json}")
                
                if "codes" not in data:
                    data["codes"] = {}
                
                # Check if this player already has a code for this event
                found_code = None
                for c, entry in data["codes"].items():
                    if entry.get("steam_id") == steam_id and entry.get("event_id") == event_id:
                        found_code = c
                        break
                
                if found_code:
                    code = found_code
                    log_debug(f"Código existente encontrado para o jogador: {code}")
                else:
                    log_debug("Gerando novo código de teleporte...")
                    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # exclude O, 0, I, 1
                    while True:
                        new_code = "".join(secrets.choice(alphabet) for _ in range(4))
                        if new_code not in data["codes"]:
                            code = new_code
                            break
                    
                    data["codes"][code] = {
                        "steam_id": steam_id,
                        "player_name": player_name,
                        "event_id": event_id,
                        "generated_at": datetime.utcnow().isoformat()
                    }
                    log_debug(f"Novo código gerado: {code}. Gravando no JSON...")
                    
                    try:
                        with open(codes_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        log_debug("Gravação no JSON realizada com sucesso!")
                    except Exception as ex:
                        log_debug(f"Falha ao gravar JSON: {ex}")
                        self._log_error(f"Failed to write event codes to json: {ex}")
            
            if not code:
                log_debug("Falha na geração do código. Enviando resposta de erro...")
                await interaction.followup.send("❌ **Falha ao gerar o código do evento.**", ephemeral=True)
                return

            log_debug("Enviando mensagem final com o código gerado...")
            # Send ephemeral response with click-to-copy code
            await interaction.followup.send(
                f"Digite o comando abaixo no chat global do jogo para se teleportar para o evento '{event_name}':\n"
                f"```\n"
                f"/evento {code}\n"
                f"```",
                ephemeral=True
            )
            log_debug("Mensagem final enviada com sucesso!")

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log_debug(f"ERRO em _handle_teleport_interaction:\n{tb}")
            self._log_error(f"DiscordBotService _handle_teleport_interaction error: {e}")
            try:
                await interaction.followup.send(
                    "❌ **Erro interno ao processar seu teleporte.**",
                    ephemeral=True
                )
            except Exception as e_send:
                log_debug(f"Falha ao enviar mensagem de erro do followup: {e_send}")


    async def _send_dm_async(self, discord_user_id: int, content: str) -> bool:

        try:

            if self._bot is None:

                return False

            uid = int(discord_user_id)

            if uid <= 0:

                return False



            user = self._bot.get_user(uid)

            if user is None:

                try:

                    user = await self._bot.fetch_user(uid)

                except Exception as e:

                    try:

                        self._log_warn(f"DiscordBotService DM fetch_user failed for {uid}: {e}")

                    except Exception:

                        pass

                    user = None

            if user is None:

                return False



            await user.send(str(content or ""))

            return True

        except Exception as e:

            try:

                self._log_warn(f"DiscordBotService DM send failed for {discord_user_id}: {e}")

            except Exception:

                pass

            return False



    def send_dm(self, discord_user_id: int, content: str) -> bool:

        try:

            if self._loop is None:

                return False

            if self._bot is None:

                return False

            fut = asyncio.run_coroutine_threadsafe(

                self._send_dm_async(int(discord_user_id), str(content or "")),

                self._loop,

            )

            try:

                return bool(fut.result(timeout=15))

            except Exception as e:

                try:

                    self._log_warn(

                        f"DiscordBotService DM future failed for {discord_user_id}: {e}"

                    )

                except Exception:

                    pass

                return False

        except Exception as e:

            try:

                self._log_warn(f"DiscordBotService send_dm failed for {discord_user_id}: {e}")

            except Exception:

                pass

            return False



    def start(self) -> Dict[str, Any]:

        if self._thread and self._thread.is_alive():

            return {"success": True, "message": "already_running"}



        token = self._get_bot_token()

        if not token:

            return {"success": False, "message": "bot_token_empty"}



        channel_id = self._load_register_channel_id()

        if not channel_id:

            return {"success": False, "message": "register_channel_missing"}



        self._stop_event.clear()



        def runner():

            try:

                self._loop = asyncio.new_event_loop()

                asyncio.set_event_loop(self._loop)

                self._loop.run_until_complete(self._run_bot_async())

            except Exception as e:

                self._log_error(f"DiscordBotService crashed: {e}")

            finally:

                try:

                    if self._loop and not self._loop.is_closed():

                        self._loop.stop()

                        self._loop.close()

                except Exception:

                    pass



        self._thread = threading.Thread(target=runner, daemon=True)

        self._thread.start()

        return {"success": True, "message": "started"}



    def stop(self):

        try:

            if self._bot is not None:

                try:

                    fut = asyncio.run_coroutine_threadsafe(self._bot.close(), self._loop)

                    try:

                        fut.result(timeout=5)

                    except Exception:

                        pass

                except Exception:

                    pass

        finally:

            self._stop_event.set()

    def update_bot_status(self, count: int, max_players: int):
        """Update bot status (presence and guild nickname) in a thread-safe way."""
        try:
            if self._loop is None or self._bot is None:
                return

            if not self._loop.is_running():
                return

            asyncio.run_coroutine_threadsafe(
                self._update_bot_status_async(count, max_players),
                self._loop
            )
        except Exception as e:
            try:
                self._log_warn(f"DiscordBotService update_bot_status failed: {e}")
            except Exception:
                pass

    async def _update_bot_status_async(self, count: int, max_players: int) -> None:
        """Coroutine to update bot presence (activity) and nickname in the configured guild."""
        try:
            if self._bot is None or not self._bot.is_ready():
                return

            import discord
            import re

            # 1. Update presence (activity: Watching X/Y Jogadores)
            activity_text = f"{count}/{max_players} Jogadores"
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=activity_text
            )
            await self._bot.change_presence(activity=activity)
            self._log_info(f"[BOT] Presence updated to: Watching {activity_text}")

            # 2. Update Guild Nickname if possible
            gid_raw = self._get_guild_id()
            if gid_raw:
                try:
                    guild_id = int(gid_raw)
                    guild = self._bot.get_guild(guild_id)
                    if not guild:
                        guild = await self._bot.fetch_guild(guild_id)
                    
                    if guild:
                        me = guild.me
                        if not me or not hasattr(me, "edit"):
                            me = await guild.fetch_member(self._bot.user.id)
                        
                        if me:
                            current_nick = me.nick or me.name
                            base_name = re.sub(r"^\[\d+/\d+\]\s*", "", current_nick).strip()
                            new_nick = f"[{count}/{max_players}] {base_name}"
                            new_nick = new_nick[:32]
                            
                            if me.nick != new_nick:
                                await me.edit(nick=new_nick)
                                self._log_info(f"[BOT] Guild nickname updated to: {new_nick}")
                except Exception as guild_err:
                    self._log_warn(f"[BOT] Failed to update nickname in guild {gid_raw}: {guild_err}")
        except Exception as e:
            try:
                self._log_error(f"[BOT] Failed to update status/nickname: {e}")
            except Exception:
                pass

