import os
import sqlite3
import urllib.request
import urllib.error
import json
import jwt
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List, Dict, Any, Set
from flask import request, jsonify
from app.extensions import get_services
from core.database.connector import DatabaseConnector
from utils.sqlite_queue import ensure_sqlite_wal as _ensure_sqlite_wal
from utils.integration_helpers import make_signed_vehicle_asset_url as _make_signed_vehicle_asset_url

# ============================================================================
# DATABASE PATH HELPERS
# ============================================================================

def _get_ssm_database_path() -> Tuple[Optional[str], Optional[str]]:
    """Retorna (caminho_db, erro)"""
    services = get_services()
    path_helper = getattr(services, 'path_helper', None)
    if not path_helper:
        return None, "Configuração não inicializada"
    db_path = path_helper.get_ssm_db_path()
    if not db_path or not os.path.exists(db_path):
        return None, "Banco SSM.db não encontrado"
    return str(db_path), None

def _get_scum_database_path() -> Tuple[Optional[str], Optional[str]]:
    """Retorna (caminho_db, erro)"""
    services = get_services()
    path_helper = getattr(services, 'path_helper', None)
    if not path_helper:
        return None, "Configuração não inicializada"
    db_path = path_helper.get_scum_db_path()
    if not db_path or not os.path.exists(db_path):
        return None, "Banco SCUM.db não encontrado"
    return str(db_path), None

# ============================================================================
# SERVER & PLAYER STATE HELPERS
# ============================================================================

def _is_player_online(steam_id: str) -> Tuple[Optional[bool], Optional[str]]:
    """Verifica se o jogador está online via OnlineMonitor."""
    services = get_services()
    online_monitor = getattr(services, "online_monitor", None)
    if not online_monitor:
        return None, "Serviço de monitoramento offline"
    try:
        # Tentar is_player_online, fallback para get_online_players
        if hasattr(online_monitor, "is_player_online"):
            is_online = online_monitor.is_player_online(steam_id)
        elif hasattr(online_monitor, "get_online_players"):
            res = online_monitor.get_online_players()
            players = res.get("players", {}) if isinstance(res, dict) else {}
            is_online = steam_id in (players or {})
        else:
            return None, "Método de verificação online não encontrado"
        return is_online, None
    except Exception as e:
        return None, str(e)


def _server_must_be_offline_for_scum_db_write() -> Tuple[bool, Optional[str]]:
    """Verifica se o servidor está offline, permitindo escrita no SCUM.db."""
    services = get_services()
    server_manager = getattr(services, "server_manager", None)
    if not server_manager:
        return False, "Gerenciador de servidor não disponível"
    try:
        if hasattr(server_manager, "is_running"):
            is_running = server_manager.is_running()
        elif hasattr(server_manager, "get_status"):
            status = server_manager.get_status()
            is_running = status.get("is_running", False)
        else:
            # Fallback final: verificar processo se for ServerManager
            if hasattr(server_manager, "_is_scumserver_process_running"):
                is_running = server_manager._is_scumserver_process_running()
            else:
                return False, "Método de verificação de status não encontrado"
        return not is_running, None
    except Exception as e:
        return False, str(e)


def _ensure_sqlite_wal(db_path: str) -> None:
    """Garante que o banco de dados esteja em modo WAL para permitir leituras concorrentes."""
    try:
        if not db_path or not os.path.exists(db_path):
            return
        with sqlite3.connect(db_path, timeout=10.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass

# ============================================================================
# AUTH & JWT HELPERS
# ============================================================================

def _decrypt_if_needed(value: Any) -> str:
    """Helper para descriptografar valores se necessário."""
    try:
        services = get_services()
        logger = getattr(services, 'logger', None)
        if not value:
            return ""
        if not str(value).startswith("ENCRYPTED:"):
            return str(value)
        from core.security.credential_encryption import decrypt_credential
        return str(decrypt_credential(str(value), logger=logger))
    except Exception:
        return str(value or "")

def _get_player_jwt_secret() -> str:
    services = get_services()
    config = getattr(services, 'config', {})
    auth_cfg = (config or {}).get("auth", {}) if isinstance(config, dict) else {}
    raw = str(auth_cfg.get("jwt_secret") or "").strip()
    if not raw:
        return "ssm-player-secret-change-in-production"
    return _decrypt_if_needed(raw)

def _get_player_jwt_expiration_hours() -> int:
    services = get_services()
    config = getattr(services, 'config', {})
    public_cfg = (config or {}).get("public", {}) if isinstance(config, dict) else {}
    try:
        v = int(public_cfg.get("player_jwt_expiration_hours", 24))
        return v if v > 0 else 24
    except Exception:
        return 24

def _get_gestao_player_me_path() -> str:
    services = get_services()
    config = getattr(services, 'config', {})
    public_cfg = (config or {}).get("public", {}) if isinstance(config, dict) else {}
    path = str(public_cfg.get("gestao_player_me_path") or "").strip() or "/api/v1/player/me"
    if not path.startswith("/"):
        path = "/" + path
    return path

def _issue_player_jwt(steam_id: str, server_hash: str) -> str:
    exp = datetime.utcnow() + timedelta(hours=_get_player_jwt_expiration_hours())
    payload = {
        "sub": str(steam_id),
        "aud": "player",
        "server_hash": str(server_hash),
        "iat": datetime.utcnow(),
        "exp": exp,
    }
    return jwt.encode(payload, _get_player_jwt_secret(), algorithm="HS256")

def _decode_player_jwt(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            _get_player_jwt_secret(),
            algorithms=["HS256"],
            options={"require": ["exp", "iat"], "verify_aud": False},
        )
        if not isinstance(payload, dict):
            return None
        if str(payload.get("aud") or "") != "player":
            return None
        if not str(payload.get("sub") or "").strip():
            return None
        if not str(payload.get("server_hash") or "").strip():
            return None
        return payload
    except Exception:
        return None

def _gestao_get_player_identity(gestao_access_token: str) -> Tuple[Optional[str], Optional[str]]:
    """Retorna (steam_id, error_code)"""
    services = get_services()
    config = getattr(services, 'config', {})
    gestao_url = config.get("gestao", {}).get("server_url", "https://gestao.scumservermanager.com")
    
    token = str(gestao_access_token or "").strip()
    if not token:
        return None, "GESTAO_TOKEN_REQUIRED"

    base = str(gestao_url or "").rstrip("/")
    url = f"{base}{_get_gestao_player_me_path()}"

    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace") if raw else "{}"
            data = json.loads(text) if text else {}
            if isinstance(data, dict) and "steam_id" in data:
                steam_id = str(data.get("steam_id") or "").strip()
            else:
                inner = (data or {}).get("data") if isinstance(data, dict) else None
                steam_id = str((inner or {}).get("steam_id") or "").strip() if isinstance(inner, dict) else ""
            if not steam_id:
                return None, "STEAM_ID_NOT_FOUND"
            return steam_id, None
    except urllib.error.HTTPError as he:
        status = getattr(he, "code", None)
        if status in (401, 403):
            return None, "GESTAO_TOKEN_INVALID"
        return None, "GESTAO_HTTP_ERROR"
    except Exception:
        return None, "GESTAO_UNREACHABLE"

# ============================================================================
# CHEST & INVENTORY HELPERS
# ============================================================================

_CHEST_CLASS_DISPLAY = {
    "BP_Chest_C": "Small Wooden",
    "BP_Chest_Medium_C": "Medium Wooden",
    "BP_Chest_Large_C": "Large Wooden",
    "BP_Chest_Steel_C": "Steel",
    "BP_Chest_Metal_C": "Metal",
    "BP_Chest_Gold_C": "Gold",
}

def _get_chest_display_name_api(chest_class: Optional[str]) -> str:
    """Retornar nome amigável para o tipo de baú."""
    if not chest_class:
        return "Desconhecido"
    if chest_class in _CHEST_CLASS_DISPLAY:
        return _CHEST_CLASS_DISPLAY[chest_class]
    lowered = chest_class.lower()
    if "wood" in lowered: return "Wooden"
    if "metal" in lowered: return "Metal"
    if "steel" in lowered: return "Steel"
    return chest_class

def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None: return None
        return float(value)
    except (TypeError, ValueError):
        return None

def _fetch_chest_rows(
    filters: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> Tuple[List[sqlite3.Row], Optional[int]]:
    """Consultar registros da tabela chest_snapshot com filtros opcionais."""
    services = get_services()
    db_path = services.get_ssm_db_path()
    if not db_path:
        raise RuntimeError("Caminho do banco SSM.db não disponível.")

    with DatabaseConnector.get_connection(db_path, write_mode=False) as conn:
        conn.row_factory = sqlite3.Row
        filters = filters or {}
        where_clauses: List[str] = []
        params: List[Any] = []
        steam_id_filter = filters.get("steam_id")
        if steam_id_filter is not None:
            where_clauses.append("steam_id = ?")
            params.append(steam_id_filter)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        base_query = f"""
            SELECT * FROM chest_snapshot
            {where_clause}
            ORDER BY last_seen_at DESC
        """
        query_params = list(params)
        if limit is not None:
            base_query += " LIMIT ?"
            query_params.append(limit)
            if offset:
                base_query += " OFFSET ?"
                query_params.append(offset)
        elif offset:
            base_query += " LIMIT -1 OFFSET ?"
            query_params.append(offset)

        cursor = conn.execute(base_query, query_params)
        rows = cursor.fetchall()
        total = None
        if limit is not None or offset:
            count_query = f"SELECT COUNT(*) AS total FROM chest_snapshot {where_clause}"
            count_cursor = conn.execute(count_query, params)
            total_row = count_cursor.fetchone()
            total = total_row["total"] if total_row else 0
        return rows, total

def _serialize_chest_row(row: sqlite3.Row) -> Dict[str, Any]:
    """Transformar linha do banco em estrutura pronta para API."""
    vehicle_info = None
    if (row["vehicle_entity_id"] or row["vehicle_class"] or row["vehicle_container_class"]):
        vehicle_info = {
            "entity_id": row["vehicle_entity_id"],
            "class": row["vehicle_class"],
            "container_class": row["vehicle_container_class"],
            "owner_name": row["vehicle_owner_name"],
            "owner_steam_id": row["vehicle_owner_steam_id"],
            "owner_player_id": row["vehicle_owner_player_id"],
            "registered_at": row["vehicle_registered_at"],
        }
    return {
        "entity_id": row["entity_id"],
        "container_entity_id": row["container_entity_id"],
        "owner_profile_id": row["owner_profile_id"],
        "steam_id": row["steam_id"],
        "player_name": row["player_name"],
        "fake_name": row["fake_name"],
        "custom_name": row["custom_name"],
        "chest_class": row["chest_class"],
        "chest_type": _get_chest_display_name_api(row["chest_class"]),
        "location": {
            "x": _safe_float(row["location_x"]),
            "y": _safe_float(row["location_y"]),
            "z": _safe_float(row["location_z"]),
        },
        "rotation": {
            "x": _safe_float(row["rotation_x"]),
            "y": _safe_float(row["rotation_y"]),
            "z": _safe_float(row["rotation_z"]),
        },
        "vehicle_owner_mismatch": bool(row["vehicle_owner_mismatch"]) if row["vehicle_owner_mismatch"] is not None else False,
        "vehicle": vehicle_info,
        "last_seen_at": row["last_seen_at"],
        "created_at": row["created_at"],
        "has_vehicle": vehicle_info is not None,
    }

# ============================================================================
# MISC HELPERS
# ============================================================================

def _str_to_bool(value: Optional[str]) -> bool:
    if value is None: return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}

def _format_vehicle_class_display(v_class: Optional[str]) -> str:
    if not v_class: return "Desconhecido"
    if "wolfs" in v_class.lower(): return "Wolfswagen"
    if "laika" in v_class.lower(): return "Laika"
    if "riser" in v_class.lower(): return "Riser"
    if "tractor" in v_class.lower(): return "Trator"
    return v_class

# ============================================================================
# PLAYER & VEHICLE SORTING HELPERS
# ============================================================================

PLAYER_DEFAULT_SORT_FIELD = "last_seen"
PLAYER_DEFAULT_SORT_ORDER = "desc"
PLAYER_SORT_COLUMN_MAP: Dict[str, str] = {
    "player_name": "COALESCE(p.player_name, '') COLLATE NOCASE",
    "last_seen": "p.last_seen",
    "first_seen": "p.first_seen",
    "total_playtime": "COALESCE(p.total_playtime, 0)",
    "total_sessions": "COALESCE(p.total_sessions, 0)",
    "created_at": "p.created_at",
    "balance": "COALESCE(w.balance, 0)",
}
PLAYER_SORTABLE_FIELDS: Set[str] = set(PLAYER_SORT_COLUMN_MAP.keys()).union(
    {"vehicles_total"}
)

def _normalize_player_sort_params(
    sort_by: Optional[str], sort_order: Optional[str]
) -> Tuple[str, str]:
    normalized_sort_by = (sort_by or PLAYER_DEFAULT_SORT_FIELD).lower()
    if normalized_sort_by not in PLAYER_SORTABLE_FIELDS:
        return PLAYER_DEFAULT_SORT_FIELD, PLAYER_DEFAULT_SORT_ORDER

    normalized_sort_order = (sort_order or PLAYER_DEFAULT_SORT_ORDER).lower()
    if normalized_sort_order not in {"asc", "desc"}:
        normalized_sort_order = PLAYER_DEFAULT_SORT_ORDER

    return normalized_sort_by, normalized_sort_order

def _fetch_vehicle_statistics(
    steam_ids: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    services = get_services()
    log_processor = getattr(services, 'log_processor', None)
    if not log_processor:
        return {}

    ids = [sid for sid in (steam_ids or []) if sid]
    vehicle_db_path = log_processor.db_manager.db_path

    query = """
        SELECT steam_id,
               COUNT(*) AS total,
               SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) AS status_0,
               SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS status_1,
               SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) AS status_2,
               SUM(CASE WHEN status = 3 THEN 1 ELSE 0 END) AS status_3,
               MAX(last_ownership_change) AS updated_at
        FROM vehicle_current_ownership
    """

    params: List[Any] = []
    if ids:
        placeholders = ",".join("?" for _ in ids)
        query += f" WHERE steam_id IN ({placeholders})"
        params.extend(ids)

    query += " GROUP BY steam_id"

    try:
        with DatabaseConnector.get_connection(vehicle_db_path, write_mode=False) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(query, params).fetchall()
    except Exception:
        return {}

    stats: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        stats[row["steam_id"]] = {
            "total": row["total"] or 0,
            "by_status": {
                "0": row["status_0"] or 0,
                "1": row["status_1"] or 0,
                "2": row["status_2"] or 0,
                "3": row["status_3"] or 0,
            },
            "updated_at": row["updated_at"],
        }

    return stats

def _get_sorted_player_rows(
    limit: int, offset: int, sort_by: str, sort_order: str, search_query: Optional[str] = None
) -> Tuple[List[sqlite3.Row], int, Optional[Dict[str, Dict[str, Any]]]]:
    db_path, error = _get_ssm_database_path()
    if error:
        raise RuntimeError(error)

    services = get_services()
    log_processor = getattr(services, 'log_processor', None)

    where_clause = ""
    params: List[Any] = []
    if search_query:
        where_clause = " WHERE p.player_name LIKE ? OR p.steam_id LIKE ?"
        params = [f"%{search_query}%", f"%{search_query}%"]

    with DatabaseConnector.get_connection(db_path, write_mode=False) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f"SELECT COUNT(*) as total FROM players p{where_clause}", params)
        total_count = cursor.fetchone()["total"]

        base_query = (
            "SELECT p.steam_id, p.player_name, p.player_id, p.first_seen, p.last_seen, "
            "       p.total_sessions, p.total_playtime, p.is_new_player, "
            "       p.notification_sent, p.permissao, p.created_at, "
            "       COALESCE(w.balance, 0) AS balance "
            "FROM players p "
            "LEFT JOIN wallet w ON p.steam_id = w.steam_id"
            f"{where_clause}"
        )

        if sort_by == "vehicles_total":
            if not log_processor:
                # Fallback se log_processor não disponível
                query = base_query + " ORDER BY p.last_seen DESC LIMIT ? OFFSET ?"
                rows = cursor.execute(query, params + [limit, offset]).fetchall()
                return rows, total_count, None

            rows = cursor.execute(base_query, params).fetchall()
            vehicle_stats = _fetch_vehicle_statistics()

            def sort_key(row: sqlite3.Row):
                vehicles_total = vehicle_stats.get(row["steam_id"], {}).get("total", 0)
                name = (row["player_name"] or "").lower()
                return (vehicles_total, name, row["steam_id"])

            reverse = sort_order == "desc"
            sorted_rows = sorted(rows, key=sort_key, reverse=reverse)
            page_rows = sorted_rows[offset : offset + limit]
            return page_rows, total_count, vehicle_stats

        order_column = PLAYER_SORT_COLUMN_MAP.get(sort_by, "p.last_seen")
        order_direction = "DESC" if sort_order == "desc" else "ASC"

        query = (
            base_query + f" ORDER BY {order_column} {order_direction}, p.steam_id ASC "
            "LIMIT ? OFFSET ?"
        )

        rows = cursor.execute(query, params + [limit, offset]).fetchall()
        return rows, total_count, None

# ============================================================================
# SURVIVAL HELPERS
# ============================================================================

def _get_survival_numeric_columns(db_path: str) -> Set[str]:
    """Obter colunas numéricas disponíveis na tabela survival_stats_snapshot"""
    if not db_path or not os.path.exists(db_path):
        return set()

    try:
        with DatabaseConnector.get_connection(db_path, write_mode=False) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(survival_stats_snapshot)")
            columns = cursor.fetchall()
    except Exception:
        return set()

    if not columns:
        return set()

    numeric_types = {"INTEGER", "REAL", "FLOAT", "DOUBLE", "NUMERIC"}
    return {
        col["name"]
        for col in columns
        if any(nt in str(col["type"]).upper() for nt in numeric_types)
    }


_CHEST_CLASS_DISPLAY: Dict[str, str] = {
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


def _get_chest_display_name_api(chest_class: Optional[str]) -> str:
    """Retornar nome amigável para o tipo de baú."""
    if not chest_class:
        return "Desconhecido"

    if chest_class in _CHEST_CLASS_DISPLAY:
        return _CHEST_CLASS_DISPLAY[chest_class]

    lowered = chest_class.lower()
    if "wood" in lowered:
        return "Wooden"
    if "metal" in lowered:
        return "Metal"
    if "steel" in lowered:
        return "Steel"

    return chest_class


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fetch_chest_rows(
    filters: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> Tuple[List[sqlite3.Row], Optional[int]]:
    """Consultar registros da tabela chest_snapshot com filtros opcionais."""
    services = get_services()
    path_helper = getattr(services, "path_helper", None)

    if not path_helper:
        raise RuntimeError("Configuração não carregada - path_helper indisponível.")

    db_path = path_helper.get_ssm_db_path()
    with DatabaseConnector.get_connection(db_path, write_mode=False) as conn:
        conn.row_factory = sqlite3.Row

        filters = filters or {}
        where_clauses: List[str] = []
        params: List[Any] = []

        steam_id_filter = filters.get("steam_id")
        if steam_id_filter is not None:
            where_clauses.append("steam_id = ?")
            params.append(steam_id_filter)

        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        base_query = f"""
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
                vehicle_owner_name,
                vehicle_owner_steam_id,
                vehicle_owner_player_id,
                vehicle_registered_at,
                vehicle_owner_mismatch,
                last_seen_at,
                created_at
            FROM chest_snapshot
            {where_clause}
            ORDER BY last_seen_at DESC
        """

        query_params = list(params)
        if limit is not None:
            base_query += " LIMIT ?"
            query_params.append(limit)
            if offset:
                base_query += " OFFSET ?"
                query_params.append(offset)
        elif offset:
            base_query += " LIMIT -1 OFFSET ?"
            query_params.append(offset)

        try:
            cursor = conn.execute(base_query, query_params)
            rows = cursor.fetchall()

            total = None
            if limit is not None or offset:
                count_query = (
                    f"SELECT COUNT(*) AS total FROM chest_snapshot {where_clause}"
                )
                count_cursor = conn.execute(count_query, params)
                total_row = count_cursor.fetchone()
                total = total_row["total"] if total_row else 0

            return rows, total
        except Exception as e:
            raise e


def _serialize_chest_row(row: sqlite3.Row) -> Dict[str, Any]:
    """Transformar linha do banco em estrutura pronta para API."""
    vehicle_info = None
    if (
        row["vehicle_entity_id"]
        or row["vehicle_class"]
        or row["vehicle_container_class"]
    ):
        vehicle_info = {
            "entity_id": row["vehicle_entity_id"],
            "class": row["vehicle_class"],
            "container_class": row["vehicle_container_class"],
            "owner_name": row["vehicle_owner_name"],
            "owner_steam_id": row["vehicle_owner_steam_id"],
            "owner_player_id": row["vehicle_owner_player_id"],
            "registered_at": row["vehicle_registered_at"],
        }

    return {
        "entity_id": row["entity_id"],
        "container_entity_id": row["container_entity_id"],
        "owner_profile_id": row["owner_profile_id"],
        "steam_id": row["steam_id"],
        "player_name": row["player_name"],
        "fake_name": row["fake_name"],
        "custom_name": row["custom_name"],
        "chest_class": row["chest_class"],
        "chest_type": _get_chest_display_name_api(row["chest_class"]),
        "location": {
            "x": _safe_float(row["location_x"]),
            "y": _safe_float(row["location_y"]),
            "z": _safe_float(row["location_z"]),
        },
        "rotation": {
            "x": _safe_float(row["rotation_x"]),
            "y": _safe_float(row["rotation_y"]),
            "z": _safe_float(row["rotation_z"]),
        },
        "vehicle_owner_mismatch": (
            bool(row["vehicle_owner_mismatch"])
            if row["vehicle_owner_mismatch"] is not None
            else False
        ),
        "vehicle": vehicle_info,
        "last_seen_at": row["last_seen_at"],
        "created_at": row["created_at"],
        "has_vehicle": vehicle_info is not None,
    }


def _build_chest_player_summary(chests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Gerar resumo por jogador para facilitar filtros."""
    summary: Dict[str, Dict[str, Any]] = {}
    for chest in chests:
        key = chest.get("steam_id") or "__UNKNOWN__"
        entry = summary.setdefault(
            key,
            {
                "steam_id": None if key == "__UNKNOWN__" else key,
                "count": 0,
                "player_name": chest.get("player_name"),
                "fake_name": chest.get("fake_name"),
            },
        )
        entry["count"] += 1
        if not entry.get("player_name") and chest.get("player_name"):
            entry["player_name"] = chest["player_name"]
        if not entry.get("fake_name") and chest.get("fake_name"):
            entry["fake_name"] = chest["fake_name"]
    return sorted(summary.values(), key=lambda item: item["count"], reverse=True)
def _fetch_functional_vehicle_counts_by_steam_id(
    db_path: str,
    steam_ids: List[str],
) -> Dict[str, int]:
    """Obter contagem de veículos funcionais por steam_id."""
    ids = [sid for sid in (steam_ids or []) if sid]
    if not ids:
        return {}

    counts: Dict[str, int] = {}
    chunk_size = 900

    try:
        with DatabaseConnector.get_connection(db_path, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            for i in range(0, len(ids), chunk_size):
                chunk = ids[i : i + chunk_size]
                placeholders = ",".join("?" for _ in chunk)
                query = f"""
                    SELECT steam_id, COUNT(*) AS total
                    FROM vehicle_current_ownership
                    WHERE is_vehicle_functional = 1
                      AND status = 0
                      AND steam_id IN ({placeholders})
                    GROUP BY steam_id
                """
                rows = cursor.execute(query, chunk).fetchall()
                for row in rows:
                    counts[row["steam_id"]] = row["total"] or 0

    except Exception:
        return {}

    return counts
