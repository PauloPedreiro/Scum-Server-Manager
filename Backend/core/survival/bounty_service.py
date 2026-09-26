"""
Bounty Hunter / Wanted Killstreak System Service
"""

import os
import json
import sqlite3
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from core.database.connector import DatabaseConnector
from core.shop.wallet_service import WalletService
from core.rcon_queue_manager import RconQueueManager
from core.config.config_manager import ConfigManager
from utils.logger import StructuredLogger

logger = logging.getLogger(__name__)


class BountyService:
    """Service to handle player killstreaks, bounties, anti-abuse checks, and Discord rankings."""

    def __init__(self, ssm_db_path: str, config: Dict[str, Any] = None, config_path: str = "data/config.json"):
        self.ssm_db_path = ssm_db_path
        self.config = config or {}
        self.config_path = config_path
        self.logger = StructuredLogger()
        self.ensure_tables()

    def ensure_tables(self):
        """Ensure all required sqlite database tables exist."""
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cursor = conn.cursor()
                
                # player_killstreaks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS player_killstreaks (
                        steam_id TEXT PRIMARY KEY,
                        player_name TEXT NOT NULL,
                        current_streak INTEGER DEFAULT 0,
                        max_streak INTEGER DEFAULT 0,
                        is_wanted INTEGER DEFAULT 0,
                        bounty_value INTEGER DEFAULT 0,
                        cooldown_until TEXT
                    )
                """)
                
                # bounty_claims table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bounty_claims (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        killer_steam_id TEXT NOT NULL,
                        killer_name TEXT NOT NULL,
                        victim_steam_id TEXT NOT NULL,
                        victim_name TEXT NOT NULL,
                        victim_streak INTEGER NOT NULL,
                        points_rewarded INTEGER NOT NULL,
                        claimed_at TEXT NOT NULL
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bounty_claims_killer ON bounty_claims(killer_steam_id)")
                
                # squad_leave_history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS squad_leave_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        steam_id TEXT NOT NULL,
                        squad_id INTEGER NOT NULL,
                        left_at TEXT NOT NULL
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_squad_leave_history_lookup ON squad_leave_history(steam_id, squad_id)")
                
                conn.commit()
                self.logger.info("BountyService database tables verified/created successfully.")
        except Exception as e:
            self.logger.error(f"Error ensuring BountyService tables: {e}")

    def log_squad_leave(self, steam_id: str, squad_id: int):
        """Record that a player left a squad (used for ex-member exploit prevention)."""
        try:
            now_iso = datetime.utcnow().isoformat()
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO squad_leave_history (steam_id, squad_id, left_at) VALUES (?, ?, ?)",
                    (steam_id, squad_id, now_iso)
                )
                conn.commit()
                self.logger.info(f"Squad leave recorded for player {steam_id} from squad {squad_id}.")
        except Exception as e:
            self.logger.error(f"Error logging squad leave: {e}")

    def verify_squad_relation(self, killer_steam_id: str, victim_steam_id: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        """
        Check if the killer is allowed to claim a bounty on the victim.
        
        Returns:
            Dict containing 'allowed' (bool) and 'reason' (str)
        """
        try:
            wanted_cfg = self.config.get("wanted_event", {})
            squad_leave_cooldown = int(wanted_cfg.get("squad_leave_cooldown_hours", 24))
            
            if conn is not None:
                return self._verify_squad_relation_with_conn(conn, killer_steam_id, victim_steam_id, squad_leave_cooldown)
                
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=False) as db_conn:
                return self._verify_squad_relation_with_conn(db_conn, killer_steam_id, victim_steam_id, squad_leave_cooldown)
        except Exception as e:
            self.logger.error(f"Error verifying squad relation: {e}")
            # Fallback to safe side (block claim if error happens to prevent exploit)
            return {"allowed": False, "reason": f"Error during verification: {e}"}

    def _verify_squad_relation_with_conn(self, conn: sqlite3.Connection, killer_steam_id: str, victim_steam_id: str, squad_leave_cooldown: int) -> Dict[str, Any]:
        cursor = conn.cursor()
        
        # 1. Check if currently in the same squad
        cursor.execute(
            """
            SELECT s1.squad_id 
            FROM squad_member_snapshot s1
            JOIN squad_member_snapshot s2 ON s1.squad_id = s2.squad_id
            WHERE s1.player_steam_id = ? AND s2.player_steam_id = ?
            LIMIT 1
            """,
            (killer_steam_id, victim_steam_id)
        )
        row = cursor.fetchone()
        if row:
            return {"allowed": False, "reason": "Killer and victim are currently in the same squad."}
        
        # 2. Check if killer recently left the victim's current squad
        # Find victim's current squad
        cursor.execute(
            "SELECT squad_id FROM squad_member_snapshot WHERE player_steam_id = ? LIMIT 1",
            (victim_steam_id,)
        )
        victim_squad_row = cursor.fetchone()
        if victim_squad_row:
            victim_squad_id = victim_squad_row[0]
            cooldown_limit = (datetime.utcnow() - timedelta(hours=squad_leave_cooldown)).isoformat()
            
            cursor.execute(
                """
                SELECT id FROM squad_leave_history 
                WHERE steam_id = ? AND squad_id = ? AND left_at >= ?
                LIMIT 1
                """,
                (killer_steam_id, victim_squad_id, cooldown_limit)
            )
            if cursor.fetchone():
                return {"allowed": False, "reason": f"Killer recently left the victim's squad within {squad_leave_cooldown} hours."}

        # 3. Check if victim recently left the killer's current squad
        # Find killer's current squad
        cursor.execute(
            "SELECT squad_id FROM squad_member_snapshot WHERE player_steam_id = ? LIMIT 1",
            (killer_steam_id,)
        )
        killer_squad_row = cursor.fetchone()
        if killer_squad_row:
            killer_squad_id = killer_squad_row[0]
            cooldown_limit = (datetime.utcnow() - timedelta(hours=squad_leave_cooldown)).isoformat()
            
            cursor.execute(
                """
                SELECT id FROM squad_leave_history 
                WHERE steam_id = ? AND squad_id = ? AND left_at >= ?
                LIMIT 1
                """,
                (victim_steam_id, killer_squad_id, cooldown_limit)
            )
            if cursor.fetchone():
                return {"allowed": False, "reason": f"Victim recently left the killer's squad within {squad_leave_cooldown} hours."}

        return {"allowed": True, "reason": ""}

    def process_pvp_kill(self, killer_steam_id: str, killer_name: str, victim_steam_id: str, victim_name: str, kill_event_id: str):
        """Process a PvP kill to update streaks, handle bounty activation/increment/claims."""
        wanted_cfg = self.config.get("wanted_event", {})
        if not wanted_cfg.get("enabled", True):
            return

        try:
            killstreak_trigger = int(wanted_cfg.get("killstreak_trigger", 5))
            base_bounty = int(wanted_cfg.get("base_bounty", 500))
            increment_bounty = int(wanted_cfg.get("increment_bounty", 100))
            cooldown_hours = int(wanted_cfg.get("cooldown_hours", 12))
            
            notifications = wanted_cfg.get("notifications", {})
            in_game_chat_color = notifications.get("in_game_chat_color", "2")
            activation_template = notifications.get("activation_template", "⚠️ PROCURADO: {player} atingiu {streak} kills seguidos e agora está PROCURADO! Recompensa por sua cabeça: {points} pontos!")
            increment_template = notifications.get("increment_template", "🔥 PERIGO: O procurado {player} fez mais uma vítima (Streak {streak})! Recompensa subiu para {points} pontos!")
            claimed_template = notifications.get("claimed_template", "🎯 RECOMPENSA: {killer} caçou o procurado {victim} (Streak {streak}) e faturou {points} pontos!")
            
            now_iso = datetime.utcnow().isoformat()
            
            # Helper to execute RCON messages
            def send_rcon_announcement(msg: str):
                try:
                    # Sanitizar mensagem para evitar injeção RCON
                    msg_clean = msg.replace("\r", "").replace("\n", "").replace('"', "'")
                    msg_clean = "".join(ch for ch in msg_clean if ord(ch) >= 32).strip()
                    
                    rcon_q = RconQueueManager.get_instance(self.config_path)
                    
                    chat_type = None
                    if in_game_chat_color.isdigit() and int(in_game_chat_color) in (0, 2, 3, 4, 6, 7):
                        chat_type = int(in_game_chat_color)
                        
                    online_players = []
                    if chat_type is not None:
                        try:
                            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=False) as conn_players:
                                cursor_players = conn_players.cursor()
                                cursor_players.execute("SELECT steam_id FROM players_online WHERE status = 'online'")
                                online_players = [row[0] for row in cursor_players.fetchall() if row[0]]
                        except Exception as db_err:
                            self.logger.error(f"Error fetching online players for bounty chat: {db_err}")
                            
                    if chat_type is not None and online_players:
                        for steam_id in online_players:
                            rcon_q.enqueue_command(f'SendChat {chat_type} "{msg_clean}" {steam_id}', delay_after=0.05, priority=10)
                    else:
                        rcon_q.enqueue_command(f'Announce {msg_clean}', priority=10)
                except Exception as ex:
                    self.logger.error(f"Error sending RCON announcement/chat: {ex}")

            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cursor = conn.cursor()
                
                # Check victim's current wanted status
                cursor.execute(
                    "SELECT is_wanted, bounty_value, current_streak FROM player_killstreaks WHERE steam_id = ?",
                    (victim_steam_id,)
                )
                victim_row = cursor.fetchone()
                
                # 1. If victim was wanted, process bounty claim
                victim_was_wanted = False
                victim_streak = 0
                bounty_reward = 0
                
                if victim_row:
                    is_wanted, bounty_value, current_streak = victim_row
                    victim_streak = current_streak
                    if is_wanted == 1:
                        victim_was_wanted = True
                        bounty_reward = bounty_value
                
                claim_result = None
                if victim_was_wanted:
                    # Run squad checks
                    relation = self.verify_squad_relation(killer_steam_id, victim_steam_id, conn=conn)
                    if relation["allowed"]:
                        # Pay reward using WalletService
                        wallet_service = WalletService(self.ssm_db_path, logger=self.logger)
                        wallet_service.apply_delta(
                            steam_id=killer_steam_id,
                            delta=bounty_reward,
                            reason="wanted_bounty",
                            ref_type="kill_event",
                            ref_id=kill_event_id,
                            meta={"victim_steam_id": victim_steam_id, "victim_name": victim_name, "streak": victim_streak},
                            conn=conn
                        )
                        
                        # Save claim history
                        cursor.execute(
                            """
                            INSERT INTO bounty_claims (
                                killer_steam_id, killer_name, victim_steam_id, victim_name, victim_streak, points_rewarded, claimed_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (killer_steam_id, killer_name, victim_steam_id, victim_name, victim_streak, bounty_reward, now_iso)
                        )
                        
                        claim_result = "reward_paid"
                        self.logger.info(f"Bounty of {bounty_reward} claimed by {killer_name} for killing {victim_name}.")
                        
                        # Announcement
                        msg = claimed_template.format(
                            killer=killer_name,
                            victim=victim_name,
                            streak=victim_streak,
                            points=bounty_reward
                        )
                        send_rcon_announcement(msg)
                    else:
                        claim_result = "blocked_by_squad"
                        self.logger.info(f"Bounty claim by {killer_name} on {victim_name} blocked: {relation['reason']}")
                        send_rcon_announcement(f"⚠️ BOUNTY BLOCKED: {killer_name} killed teammate/ex-teammate {victim_name}. No points awarded!")

                # 2. Reset victim streak and status, apply cooldown
                cooldown_until = (datetime.utcnow() + timedelta(hours=cooldown_hours)).isoformat()
                cursor.execute(
                    """
                    INSERT INTO player_killstreaks (steam_id, player_name, current_streak, max_streak, is_wanted, bounty_value, cooldown_until)
                    VALUES (?, ?, 0, 0, 0, 0, ?)
                    ON CONFLICT(steam_id) DO UPDATE SET
                        player_name = excluded.player_name,
                        current_streak = 0,
                        is_wanted = 0,
                        bounty_value = 0,
                        cooldown_until = excluded.cooldown_until
                    """,
                    (victim_steam_id, victim_name, cooldown_until)
                )

                # 3. Process killer streak progression
                cursor.execute(
                    "SELECT current_streak, max_streak, cooldown_until, is_wanted, bounty_value FROM player_killstreaks WHERE steam_id = ?",
                    (killer_steam_id,)
                )
                killer_row = cursor.fetchone()
                
                killer_current_streak = 0
                killer_max_streak = 0
                killer_cooldown_until = None
                killer_is_wanted = 0
                killer_bounty = 0
                
                if killer_row:
                    killer_current_streak, killer_max_streak, killer_cooldown_until, killer_is_wanted, killer_bounty = killer_row

                # Check if killer has cooldown active
                is_cooldown_active = False
                if killer_cooldown_until:
                    try:
                        cooldown_dt = datetime.fromisoformat(killer_cooldown_until)
                        if datetime.utcnow() < cooldown_dt:
                            is_cooldown_active = True
                    except Exception:
                        pass
                
                if not is_cooldown_active:
                    new_streak = killer_current_streak + 1
                    new_max = max(new_streak, killer_max_streak)
                    new_is_wanted = killer_is_wanted
                    new_bounty = killer_bounty
                    
                    if new_streak == killstreak_trigger:
                        new_is_wanted = 1
                        new_bounty = base_bounty
                        
                        # Announcement
                        msg = activation_template.format(
                            player=killer_name,
                            streak=new_streak,
                            points=new_bounty
                        )
                        send_rcon_announcement(msg)
                        
                    elif new_streak > killstreak_trigger:
                        if new_is_wanted == 1:
                            new_bounty += increment_bounty
                            
                            # Announcement
                            msg = increment_template.format(
                                player=killer_name,
                                streak=new_streak,
                                points=new_bounty
                            )
                            send_rcon_announcement(msg)
                    
                    cursor.execute(
                        """
                        INSERT INTO player_killstreaks (steam_id, player_name, current_streak, max_streak, is_wanted, bounty_value, cooldown_until)
                        VALUES (?, ?, ?, ?, ?, ?, NULL)
                        ON CONFLICT(steam_id) DO UPDATE SET
                            player_name = excluded.player_name,
                            current_streak = excluded.current_streak,
                            max_streak = excluded.max_streak,
                            is_wanted = excluded.is_wanted,
                            bounty_value = excluded.bounty_value,
                            cooldown_until = NULL
                        """,
                        (killer_steam_id, killer_name, new_streak, new_max, new_is_wanted, new_bounty)
                    )
                else:
                    self.logger.info(f"Killer {killer_name} is in bounty cooldown. Streak progression skipped.")

                conn.commit()

            # 4. Trigger Discord update in the background
            try:
                self.update_discord_rankings()
            except Exception as discord_err:
                self.logger.error(f"Error updating Discord rankings from PvP kill: {discord_err}")
                
        except Exception as e:
            self.logger.error(f"Error processing PvP kill: {e}")

    def update_discord_rankings(self):
        """Build and send/edit persistent embeds for Top Killers, Active Bounties, and Shame Rank."""
        wanted_cfg = self.config.get("wanted_event", {})
        webhook_url = wanted_cfg.get("discord", {}).get("webhook_url", "")
        if not webhook_url or not str(webhook_url).strip():
            # Fallback to top20_kills webhook
            webhook_url = self.config.get("webhooks", {}).get("top20_kills", "")
            if not webhook_url or not str(webhook_url).strip():
                self.logger.debug("Discord webhook not configured for rankings")
                return

        try:
            # 1. Fetch data
            top_killers = []
            shame_rank = []
            active_bounties = []
            
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=False) as conn:
                cursor = conn.cursor()
                
                # Top Killers (Top 20)
                cursor.execute("""
                    SELECT steam_id, player_name, kills, deaths, kdr
                    FROM rankings
                    WHERE kills > 0
                    ORDER BY kills DESC, player_name ASC
                    LIMIT 20
                """)
                top_killers = [
                    {
                        "steam_id": r[0],
                        "player_name": r[1],
                        "kills": r[2] or 0,
                        "deaths": r[3] or 0,
                        "kdr": r[4] or 0.0
                    }
                    for r in cursor.fetchall()
                ]
                
                # NPC Shame Rank (Top 20)
                cursor.execute("""
                    SELECT victim_steam_id, victim_name, COUNT(*) as npc_deaths
                    FROM kill_events
                    WHERE event_type = 'kill' AND killer_user_id = 'NPC' AND victim_steam_id IS NOT NULL
                    GROUP BY victim_steam_id, victim_name
                    ORDER BY npc_deaths DESC, victim_name ASC
                    LIMIT 20
                """)
                shame_rank = [
                    {
                        "steam_id": r[0],
                        "player_name": r[1],
                        "npc_deaths": r[2] or 0
                    }
                    for r in cursor.fetchall()
                ]
                
                # Active Bounties (is_wanted = 1)
                cursor.execute("""
                    SELECT steam_id, player_name, current_streak, bounty_value
                    FROM player_killstreaks
                    WHERE is_wanted = 1
                    ORDER BY bounty_value DESC, player_name ASC
                """)
                active_bounties_rows = cursor.fetchall()
                
                # Online status mapping
                cursor.execute("SELECT steam_id FROM players_online WHERE status = 'online'")
                online_steam_ids = {row[0] for row in cursor.fetchall() if row[0]}
                
                active_bounties = [
                    {
                        "steam_id": r[0],
                        "player_name": r[1],
                        "streak": r[2],
                        "bounty": r[3],
                        "status": "ONLINE" if r[0] in online_steam_ids else "OFFLINE"
                    }
                    for r in active_bounties_rows
                ]

            # 2. Format Embed 1: Top Killers & Active Bounties
            embed1_description_lines = []
            
            # Active Bounties Section
            embed1_description_lines.append("🎯 **ACTIVE BOUNTIES**")
            if active_bounties:
                embed1_description_lines.append("```")
                embed1_description_lines.append(f"{'Player':<15} | {'Streak':<6} | {'Bounty':<9} | {'Status':<7}")
                embed1_description_lines.append("-" * 47)
                for b in active_bounties:
                    p_name = b["player_name"][:15].strip()
                    status_indicator = "🟢 ON" if b["status"] == "ONLINE" else "🔴 OFF"
                    embed1_description_lines.append(
                        f"{p_name:<15} | {b['streak']:<6} | {f'{b_bounty} pts' if (b_bounty := b['bounty']) else '0 pts':<9} | {status_indicator:<7}"
                    )
                embed1_description_lines.append("```")
            else:
                embed1_description_lines.append("*No active bounties at the moment.*")
                
            embed1_description_lines.append("")
            
            # Top Killers Section
            embed1_description_lines.append("⚔️ **TOP 20 KILLERS**")
            if top_killers:
                embed1_description_lines.append("```")
                embed1_description_lines.append(f"{'Rank':<4} | {'Player':<15} | {'Kills':<6} | {'Deaths':<6} | {'KDR':<5}")
                embed1_description_lines.append("-" * 47)
                for idx, k in enumerate(top_killers, 1):
                    p_name = k["player_name"][:15].strip()
                    embed1_description_lines.append(
                        f"{idx:<4} | {p_name:<15} | {k['kills']:<6} | {k['deaths']:<6} | {k['kdr']:<5.2f}"
                    )
                embed1_description_lines.append("```")
            else:
                embed1_description_lines.append("*No ranking data available.*")

            embed1 = {
                "title": "⚔️ KILL LEADERBOARD & BOUNTIES ⚔️",
                "description": "\n".join(embed1_description_lines),
                "color": 15158332,  # Red (0xE74C3C)
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "Updated in real-time"}
            }

            # 3. Format Embed 2: Shame Rank
            embed2_description_lines = []
            embed2_description_lines.append("💀 **TOP 20 NPC DEATHS**")
            if shame_rank:
                embed2_description_lines.append("```")
                embed2_description_lines.append(f"{'Rank':<4} | {'Player':<15} | {'Deaths':<6}")
                embed2_description_lines.append("-" * 31)
                for idx, s in enumerate(shame_rank, 1):
                    p_name = s["player_name"][:15].strip()
                    embed2_description_lines.append(
                        f"{idx:<4} | {p_name:<15} | {s['npc_deaths']:<6}"
                    )
                embed2_description_lines.append("```")
            else:
                embed2_description_lines.append("*No shame data available.*")

            embed2 = {
                "title": "💀 SHAME RANK | NPC DEATHS 💀",
                "description": "\n".join(embed2_description_lines),
                "color": 9807270,  # Grey (0x95A5A6)
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "Updated in real-time"}
            }

            # 4. Helper to send or edit Webhook message
            def send_or_edit_message(msg_id_key: str, embed: Dict[str, Any]):
                msg_id = wanted_cfg.get("discord", {}).get(msg_id_key, "")
                payload = {"embeds": [embed]}
                
                success = False
                new_msg_id = msg_id

                if msg_id:
                    # Try to PATCH existing message
                    patch_url = f"{webhook_url}/messages/{msg_id}"
                    try:
                        resp = requests.patch(patch_url, json=payload, timeout=10)
                        if resp.status_code in (200, 204):
                            success = True
                        else:
                            self.logger.debug(f"PATCH for {msg_id_key} failed (status {resp.status_code}), recreating...")
                    except Exception as patch_ex:
                        self.logger.debug(f"Error PATCHing webhook message {msg_id}: {patch_ex}")

                if not success:
                    # Send new POST
                    post_url = f"{webhook_url}?wait=true"
                    try:
                        resp = requests.post(post_url, json=payload, timeout=10)
                        if resp.status_code in (200, 201, 204):
                            resp_json = resp.json()
                            new_msg_id = resp_json.get("id", "")
                            success = True
                        else:
                            self.logger.error(f"POST for {msg_id_key} failed (status {resp.status_code})")
                    except Exception as post_ex:
                        self.logger.error(f"Error POSTing webhook message: {post_ex}")

                if success and new_msg_id != msg_id:
                    # Update config on disk and memory
                    wanted_cfg.setdefault("discord", {})[msg_id_key] = new_msg_id
                    try:
                        config_mgr = ConfigManager(self.config_path)
                        config_mgr.update_section("wanted_event.discord", {msg_id_key: new_msg_id})
                        self.logger.info(f"Persistent Discord message ID for {msg_id_key} updated to {new_msg_id}.")
                    except Exception as config_err:
                        self.logger.error(f"Error updating config.json: {config_err}")

            # Send/Edit both messages
            send_or_edit_message("top_killers_message_id", embed1)
            # Sleep briefly to respect Discord rate limits
            import time
            time.sleep(1.0)
            send_or_edit_message("shame_rank_message_id", embed2)

        except Exception as e:
            self.logger.error(f"Error updating Discord rankings: {e}")
