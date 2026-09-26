"""
Blueprint: survival
"""
from typing import Dict, Any, List, Optional, Tuple
from core.database.connector import DatabaseConnector
from core.config.config_manager import ConfigManager
from core.rcon_queue_manager import RconQueueManager

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac
from functools import wraps
from core.auth.decorators import require_auth, require_admin
import sqlite3
import re
from .helpers import _get_ssm_database_path, _get_survival_numeric_columns


survival_bp = Blueprint('survival', __name__)

@survival_bp.route("/api/survival/sync/status", methods=["GET"])
def get_survival_sync_status():
    """Obter status do serviço de sincronização de survival stats"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    shop_delivery_service = getattr(services, 'shop_delivery_service', None)
    rewards_service = getattr(services, 'rewards_service', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    try:
        if not survival_stats_sync_service:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "SurvivalStatsSyncService não inicializado",
                    }
                ),
                500,
            )

        status = survival_stats_sync_service.get_status()

        return jsonify({"success": True, "data": status, "timestamp": time.time()})

    except Exception as e:
        logger.error(f"Erro ao obter status do serviço de survival stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@survival_bp.route("/api/survival/sync/start", methods=["POST"])
def start_survival_sync():
    """Iniciar serviço de sincronização de survival stats"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    shop_delivery_service = getattr(services, 'shop_delivery_service', None)
    rewards_service = getattr(services, 'rewards_service', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    try:
        if not survival_stats_sync_service:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "SurvivalStatsSyncService não inicializado",
                    }
                ),
                500,
            )

        result = survival_stats_sync_service.start()

        return jsonify({"success": True, "data": result, "timestamp": time.time()})

    except Exception as e:
        logger.error(f"Erro ao iniciar serviço de survival stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@survival_bp.route("/api/survival/sync/stop", methods=["POST"])
def stop_survival_sync():
    """Parar serviço de sincronização de survival stats"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    shop_delivery_service = getattr(services, 'shop_delivery_service', None)
    rewards_service = getattr(services, 'rewards_service', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    try:
        if not survival_stats_sync_service:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "SurvivalStatsSyncService não inicializado",
                    }
                ),
                500,
            )

        result = survival_stats_sync_service.stop()

        return jsonify({"success": True, "data": result, "timestamp": time.time()})

    except Exception as e:
        logger.error(f"Erro ao parar serviço de survival stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@survival_bp.route("/api/survival/sync/run-now", methods=["POST"])
def run_survival_sync_now():
    """Executar sincronização de survival stats manualmente"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    shop_delivery_service = getattr(services, 'shop_delivery_service', None)
    rewards_service = getattr(services, 'rewards_service', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    try:
        if not survival_stats_sync_service:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "SurvivalStatsSyncService não inicializado",
                    }
                ),
                500,
            )

        result = survival_stats_sync_service.sync_once()

        return jsonify({"success": True, "data": result, "timestamp": time.time()})

    except Exception as e:
        logger.error(f"Erro ao executar sincronização de survival stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@survival_bp.route("/api/survival/leaderboard", methods=["GET"])
def get_survival_leaderboard():
    """Listar ranking de survival stats por métrica"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    shop_delivery_service = getattr(services, 'shop_delivery_service', None)
    rewards_service = getattr(services, 'rewards_service', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    try:
        db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        metric = (
            request.args.get("metric", "minutes_survived") or "minutes_survived"
        ).strip()
        if not metric:
            metric = "minutes_survived"

        if not re.fullmatch(r"[A-Za-z0-9_]+", metric):
            return (
                jsonify({"success": False, "error": 'Parâmetro "metric" inválido'}),
                400,
            )

        limit = request.args.get("limit", default=20, type=int)
        offset = request.args.get("offset", default=0, type=int)

        limit = max(1, min(limit or 20, 100))
        offset = max(0, offset or 0)

        numeric_columns = _get_survival_numeric_columns(db_path)
        if not numeric_columns:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Tabela survival_stats_snapshot não está disponível",
                    }
                ),
                500,
            )

        if metric not in numeric_columns:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Métrica "{metric}" não suportada',
                        "available_metrics": sorted(numeric_columns),
                    }
                ),
                400,
            )

        with DatabaseConnector.get_connection(db_path, timeout=30.0, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                f"SELECT COUNT(*) AS total FROM survival_stats_snapshot WHERE {metric} IS NOT NULL"
            )
            total_row = cursor.fetchone()
            total = total_row["total"] if total_row else 0

            query = f"""
                SELECT steam_id, player_name, user_profile_id, {metric} AS metric_value,
                       kills, deaths, animals_killed, puppets_killed, longest_kill_distance,
                       shots_fired, shots_hit, headshots, snapshot_at
                FROM survival_stats_snapshot
                ORDER BY {metric} DESC, steam_id ASC
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, (limit, offset))
            rows = cursor.fetchall()

        leaderboard = []
        position = offset + 1
        for row in rows:
            metric_value = row["metric_value"] if row["metric_value"] is not None else 0
            kills = row["kills"] if row["kills"] is not None else 0
            deaths = row["deaths"] if row["deaths"] is not None else 0
            raw_kdr = float(kills) / deaths if deaths else float(kills)
            kdr = round(raw_kdr, 2) if deaths else raw_kdr

            shots_fired = row["shots_fired"] if row["shots_fired"] is not None else 0
            shots_hit = row["shots_hit"] if row["shots_hit"] is not None else 0
            accuracy = (
                round((shots_hit / shots_fired) * 100, 2) if shots_fired else None
            )

            leaderboard.append(
                {
                    "position": position,
                    "steam_id": row["steam_id"],
                    "player_name": row["player_name"],
                    "user_profile_id": row["user_profile_id"],
                    "value": metric_value,
                    "kills": kills,
                    "deaths": deaths,
                    "kdr": kdr,
                    "animals_killed": (
                        row["animals_killed"]
                        if row["animals_killed"] is not None
                        else 0
                    ),
                    "puppets_killed": (
                        row["puppets_killed"]
                        if row["puppets_killed"] is not None
                        else 0
                    ),
                    "longest_kill_distance": row["longest_kill_distance"],
                    "shots_fired": shots_fired,
                    "shots_hit": shots_hit,
                    "accuracy_percent": accuracy,
                    "headshots": (
                        row["headshots"] if row["headshots"] is not None else 0
                    ),
                    "snapshot_at": row["snapshot_at"],
                }
            )
            position += 1

        return jsonify(
            {
                "success": True,
                "data": {
                    "metric": metric,
                    "available_metrics": sorted(numeric_columns),
                    "players": leaderboard,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "count": len(leaderboard),
                },
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao listar survival leaderboard: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@survival_bp.route("/api/survival/player/<identifier>", methods=["GET"])
def get_survival_player_detail(identifier: str):
    """Obter métricas de survival para um jogador (por steam_id ou user_profile_id)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    shop_delivery_service = getattr(services, 'shop_delivery_service', None)
    rewards_service = getattr(services, 'rewards_service', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    try:
        db_path, error = _get_ssm_database_path()
        if error:
            return jsonify({"success": False, "error": error}), 500

        identifier = (identifier or "").strip()
        if not identifier:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Identificador do jogador é obrigatório",
                    }
                ),
                400,
            )

        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM survival_stats_snapshot WHERE steam_id = ?",
                (identifier,),
            )
            row = cursor.fetchone()

            if not row:
                try:
                    user_profile_id = int(identifier)
                except ValueError:
                    user_profile_id = None

                if user_profile_id is not None:
                    cursor.execute(
                        "SELECT * FROM survival_stats_snapshot WHERE user_profile_id = ?",
                        (user_profile_id,),
                    )
                    row = cursor.fetchone()

            if not row:
                return (
                    jsonify({"success": False, "error": "Jogador não encontrado"}),
                    404,
                )

            row_dict = dict(row)

        meta_keys = {"user_profile_id", "steam_id", "player_name", "snapshot_at"}
        metrics = {k: row_dict[k] for k in row_dict.keys() if k not in meta_keys}

        kills = metrics.get("kills") or 0
        deaths = metrics.get("deaths") or 0
        shots_fired = metrics.get("shots_fired") or 0
        shots_hit = metrics.get("shots_hit") or 0

        raw_kdr = float(kills) / deaths if deaths else float(kills)
        kdr = round(raw_kdr, 2) if deaths else raw_kdr
        accuracy = round((shots_hit / shots_fired) * 100, 2) if shots_fired else None

        return jsonify(
            {
                "success": True,
                "data": {
                    "steam_id": row_dict.get("steam_id"),
                    "player_name": row_dict.get("player_name"),
                    "user_profile_id": row_dict.get("user_profile_id"),
                    "snapshot_at": row_dict.get("snapshot_at"),
                    "metrics": metrics,
                    "derived": {"kdr": kdr, "accuracy_percent": accuracy},
                },
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.error(f"Erro ao obter survival stats do jogador {identifier}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# BOUNTY EVENT / WANTED KILLSTREAK SYSTEM ROUTES
# ============================================================================

@survival_bp.route("/api/bounty/config", methods=["GET"])
@require_auth
@require_admin
def get_bounty_config():
    """Obter configuração do evento de procurado"""
    services = get_services()
    config = getattr(services, 'config', {})
    
    default_cfg = {
        "enabled": False,
        "killstreak_trigger": 5,
        "base_bounty": 500,
        "increment_bounty": 100,
        "cooldown_hours": 12,
        "squad_leave_cooldown_hours": 24,
        "discord": {
            "webhook_url": "",
            "top_killers_message_id": "",
            "shame_rank_message_id": ""
        },
        "notifications": {
            "in_game_chat_color": "2",
            "activation_template": "⚠️ WANTED: {player} reached a {streak} killstreak and is now WANTED! Bounty: {points} points!",
            "increment_template": "🔥 DANGER: Wanted player {player} got another kill (Streak {streak})! Bounty increased to {points} points!",
            "claimed_template": "🎯 BOUNTY CLAIMED: {killer} killed wanted player {victim} (Streak {streak}) and won {points} points!"
        }
    }
    
    wanted_cfg = config.get("wanted_event") or {}
    merged_cfg = default_cfg.copy()
    
    for key, value in wanted_cfg.items():
        if isinstance(value, dict) and key in merged_cfg and isinstance(merged_cfg[key], dict):
            merged_cfg[key] = {**merged_cfg[key], **value}
        else:
            merged_cfg[key] = value
            
    return jsonify({"success": True, "config": merged_cfg})


@survival_bp.route("/api/bounty/config", methods=["PUT"])
@require_auth
@require_admin
def update_bounty_config():
    """Atualizar configuração do evento de procurado"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    
    try:
        data = request.json or {}
        
        updates = {
            "enabled": bool(data.get("enabled", False)),
            "killstreak_trigger": int(data.get("killstreak_trigger", 5)),
            "base_bounty": int(data.get("base_bounty", 500)),
            "increment_bounty": int(data.get("increment_bounty", 100)),
            "cooldown_hours": int(data.get("cooldown_hours", 12)),
            "squad_leave_cooldown_hours": int(data.get("squad_leave_cooldown_hours", 24)),
        }
        
        if "discord" in data and isinstance(data["discord"], dict):
            updates["discord"] = {
                "webhook_url": str(data["discord"].get("webhook_url", "")).strip(),
                "top_killers_message_id": str(data["discord"].get("top_killers_message_id", "")).strip(),
                "shame_rank_message_id": str(data["discord"].get("shame_rank_message_id", "")).strip()
            }
            
        if "notifications" in data and isinstance(data["notifications"], dict):
            updates["notifications"] = {
                "in_game_chat_color": str(data["notifications"].get("in_game_chat_color", "2")),
                "activation_template": str(data["notifications"].get("activation_template", "")),
                "increment_template": str(data["notifications"].get("increment_template", "")),
                "claimed_template": str(data["notifications"].get("claimed_template", ""))
            }

        # Update disk using ConfigManager
        config_path = path_helper.get_config_path() if (path_helper and hasattr(path_helper, "get_config_path")) else "data/config.json"
        config_mgr = ConfigManager(config_path)
        config_mgr.update_section("wanted_event", updates)
        
        # Update memory configuration
        config["wanted_event"] = config_mgr.get_section("wanted_event") or updates
        
        # Propagate config to bounty_service
        bounty_service = getattr(services, 'bounty_service', None)
        if bounty_service:
            bounty_service.config = config
            try:
                bounty_service.update_discord_rankings()
            except Exception as discord_err:
                if logger:
                    logger.error(f"Erro ao atualizar Discord após mudança de config de bounty: {discord_err}")
        
        return jsonify({"success": True, "message": "Bounty configuration updated successfully."})
    except Exception as e:
        if logger:
            logger.error(f"Erro ao atualizar configuração de bounty: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@survival_bp.route("/api/bounty/active", methods=["GET"])
@require_auth
def get_active_bounties():
    """Listar recompensas/procurados ativos"""
    services = get_services()
    db_path = services.get_ssm_db_path()
    
    try:
        with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT p.steam_id, p.player_name, p.current_streak, p.bounty_value, 
                       CASE WHEN po.status = 'online' THEN 1 ELSE 0 END as is_online
                FROM player_killstreaks p
                LEFT JOIN players_online po ON p.steam_id = po.steam_id
                WHERE p.is_wanted = 1
                ORDER BY p.bounty_value DESC, p.player_name ASC
            """)
            rows = cursor.fetchall()
            
        active_list = [dict(row) for row in rows]
        return jsonify({"success": True, "data": active_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@survival_bp.route("/api/bounty/trigger", methods=["POST"])
@require_auth
@require_admin
def manual_trigger_bounty():
    """Ativar manualmente o status de procurado para um jogador"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    db_path = services.get_ssm_db_path()
    
    try:
        data = request.json or {}
        steam_id = str(data.get("steam_id", "")).strip()
        player_name = str(data.get("player_name", "")).strip()
        bounty_value = int(data.get("bounty_value", 500))
        
        if not steam_id or not player_name:
            return jsonify({"success": False, "error": "steam_id e player_name são obrigatórios"}), 400
            
        with DatabaseConnector.get_connection(db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO player_killstreaks (steam_id, player_name, current_streak, max_streak, is_wanted, bounty_value, cooldown_until)
                VALUES (?, ?, 1, 1, 1, ?, NULL)
                ON CONFLICT(steam_id) DO UPDATE SET
                    player_name = excluded.player_name,
                    is_wanted = 1,
                    bounty_value = excluded.bounty_value,
                    cooldown_until = NULL
                """,
                (steam_id, player_name, bounty_value)
            )
            conn.commit()
            
        # Send in-game RCON message
        try:
            rcon_q = RconQueueManager.get_instance("data/config.json")
            msg = f"⚠️ MANUAL WANTED: {player_name} has been marked WANTED by Administrator! Bounty: {bounty_value} points!"
            
            # Obter a cor configurada
            config = getattr(services, 'config', {})
            wanted_cfg = config.get("wanted_event", {})
            notifications = wanted_cfg.get("notifications", {})
            in_game_chat_color = notifications.get("in_game_chat_color", "2")
            
            chat_type = None
            if in_game_chat_color.isdigit() and int(in_game_chat_color) in (0, 2, 3, 4, 6, 7):
                chat_type = int(in_game_chat_color)
                
            online_players = []
            if chat_type is not None:
                try:
                    with DatabaseConnector.get_connection(db_path, timeout=30.0) as conn_players:
                        cursor_players = conn_players.cursor()
                        cursor_players.execute("SELECT steam_id FROM players_online WHERE status = 'online'")
                        online_players = [row[0] for row in cursor_players.fetchall() if row[0]]
                except Exception as db_err:
                    if logger:
                        logger.error(f"Error fetching online players for manual bounty chat: {db_err}")
                        
            if chat_type is not None and online_players:
                for steam_id in online_players:
                    rcon_q.enqueue_command(f'SendChat {chat_type} "{msg}" {steam_id}', delay_after=0.05, priority=10)
            else:
                rcon_q.enqueue_command(f'Announce {msg}', priority=10)
        except Exception as rcon_err:
            if logger:
                logger.error(f"Erro ao enviar RCON de bounty manual: {rcon_err}")
                
        # Update Discord rankings
        bounty_service = getattr(services, 'bounty_service', None)
        if bounty_service:
            try:
                bounty_service.update_discord_rankings()
            except Exception as discord_err:
                if logger:
                    logger.error(f"Erro ao atualizar Discord rankings pós-bounty manual: {discord_err}")
                    
        return jsonify({"success": True, "message": f"Player {player_name} marked as wanted manually."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@survival_bp.route("/api/bounty/reset", methods=["POST"])
@require_auth
@require_admin
def manual_reset_bounty():
    """Remover manualmente o status de procurado de um jogador ou todos"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    db_path = services.get_ssm_db_path()
    
    try:
        data = request.json or {}
        steam_id = str(data.get("steam_id", "")).strip()
        
        with DatabaseConnector.get_connection(db_path, timeout=30.0, write_mode=True) as conn:
            cursor = conn.cursor()
            if steam_id:
                cursor.execute(
                    "UPDATE player_killstreaks SET is_wanted = 0, bounty_value = 0, current_streak = 0 WHERE steam_id = ?",
                    (steam_id,)
                )
                message = f"Bounty for player {steam_id} reset."
            else:
                cursor.execute("UPDATE player_killstreaks SET is_wanted = 0, bounty_value = 0, current_streak = 0")
                message = "All active bounties reset."
            conn.commit()
            
        # Update Discord rankings
        bounty_service = getattr(services, 'bounty_service', None)
        if bounty_service:
            try:
                bounty_service.update_discord_rankings()
            except Exception as discord_err:
                if logger:
                    logger.error(f"Erro ao atualizar Discord rankings pós-reset: {discord_err}")
                    
        return jsonify({"success": True, "message": message})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



