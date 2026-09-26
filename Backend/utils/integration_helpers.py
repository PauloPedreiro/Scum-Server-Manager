"""
Helpers para o sistema de integração (API Keys externas).
Extraído do main.py durante refatoração modular.

Contém:
- Gerenciamento de tabelas de integração
- Rate limiting por chave
- Decorador require_integration_key
- Funções de idempotência
- Assinatura de URLs de assets de veículos
"""

import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
import threading
from functools import wraps
from uuid import uuid4
from urllib.parse import urlencode
from typing import Optional, Dict, Any, Tuple

from flask import request, jsonify  # pyright: ignore[reportMissingImports, reportMissingModuleSource]


# ============================================================================
# RATE LIMITING
# ============================================================================

_integration_rate_limit_state = {}


def _integration_rate_limit_ok(key_id: str, limit_per_minute: int = 60) -> bool:
    """Verificar se a chave de integração está dentro do limite de requisições."""
    try:
        now = float(time.time())
        window_seconds = 60.0
        state = _integration_rate_limit_state.get(key_id)
        if not state:
            _integration_rate_limit_state[key_id] = [now]
            return True
        filtered = [t for t in state if (now - float(t)) <= window_seconds]
        if len(filtered) >= int(limit_per_minute):
            _integration_rate_limit_state[key_id] = filtered
            return False
        filtered.append(now)
        _integration_rate_limit_state[key_id] = filtered
        return True
    except Exception:
        return True


# ============================================================================
# DATABASE HELPERS
# ============================================================================

def ensure_integration_tables(conn: sqlite3.Connection) -> None:
    """Criar tabelas de integração se não existirem."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS integration_keys (
            key_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_used_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_integration_keys_hash
        ON integration_keys(key_hash)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_integration_keys_enabled
        ON integration_keys(enabled)
        """
    )
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS integration_requests (
            req_id TEXT PRIMARY KEY,
            key_id TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            external_id TEXT NOT NULL,
            steam_id TEXT,
            request_json TEXT NOT NULL,
            response_json TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (key_id) REFERENCES integration_keys(key_id) ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_integration_requests_idempotency
        ON integration_requests(key_id, endpoint, external_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_integration_requests_created
        ON integration_requests(created_at)
        """
    )


def integration_key_hash(key_plaintext: str) -> str:
    """Gerar hash SHA-256 de uma chave de integração."""
    return hashlib.sha256(str(key_plaintext).encode("utf-8")).hexdigest()


# ============================================================================
# IDEMPOTENCY
# ============================================================================

def integration_find_idempotent(
    conn: sqlite3.Connection,
    *,
    key_id: str,
    endpoint: str,
    external_id: str,
):
    """
    Buscar resultado de uma requisição de integração já processada (idempotência).

    Returns:
        Tuple[dict, int] com (payload, status_code) ou None se não encontrado
    """
    ensure_integration_tables(conn)
    cur = conn.execute(
        """
        SELECT response_json, status_code
        FROM integration_requests
        WHERE key_id = ? AND endpoint = ? AND external_id = ?
        LIMIT 1
        """,
        (str(key_id), str(endpoint), str(external_id)),
    )
    row = cur.fetchone()
    if not row:
        return None
    try:
        response_json = str(row[0] or "{}")
        status_code = int(row[1] or 200)
        payload = json.loads(response_json) if response_json else {}
    except Exception:
        payload = {"success": True, "already_applied": True}
        status_code = 200
    if isinstance(payload, dict):
        payload.setdefault("already_applied", True)
    return payload, status_code


def integration_log_request(
    conn: sqlite3.Connection,
    *,
    key_id: str,
    endpoint: str,
    external_id: str,
    steam_id: Optional[str],
    request_payload: dict,
    response_payload: dict,
    status_code: int,
) -> None:
    """Registrar uma requisição de integração para auditoria e idempotência."""
    ensure_integration_tables(conn)
    conn.execute(
        """
        INSERT INTO integration_requests(req_id, key_id, endpoint, external_id, steam_id, request_json, response_json, status_code)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            str(key_id),
            str(endpoint),
            str(external_id),
            (str(steam_id) if steam_id else None),
            json.dumps(request_payload or {}, ensure_ascii=False),
            json.dumps(response_payload or {}, ensure_ascii=False),
            int(status_code),
        ),
    )


# ============================================================================
# DECORADOR DE AUTENTICAÇÃO DE INTEGRAÇÃO
# ============================================================================

def require_integration_key(f):
    """
    Decorador que valida a chave de integração (header X-Integration-Key).
    Injeta request.integration_key_id se válida.

    Requer que a função _get_ssm_database_path esteja disponível no contexto.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            key_plain = (request.headers.get("X-Integration-Key") or "").strip()
            if not key_plain:
                return jsonify({"success": False, "error": "INTEGRATION_KEY_REQUIRED"}), 401

            # Importar aqui para evitar circular imports
            from app.extensions import get_services
            services = get_services()
            ssm_db_path = services.get_ssm_db_path()
            if not ssm_db_path:
                return jsonify({"success": False, "error": "Database path not configured"}), 500

            key_h = integration_key_hash(key_plain)

            from core.shop.db import ssm_tx

            with ssm_tx(ssm_db_path) as conn:
                ensure_integration_tables(conn)
                cur = conn.execute(
                    """
                    SELECT key_id
                    FROM integration_keys
                    WHERE enabled = 1 AND key_hash = ?
                    LIMIT 1
                    """,
                    (str(key_h),),
                )
                row = cur.fetchone()
                if not row:
                    return jsonify({"success": False, "error": "INTEGRATION_KEY_INVALID"}), 401

                key_id = str(row[0])
                if not _integration_rate_limit_ok(key_id):
                    return jsonify({"success": False, "error": "RATE_LIMIT"}), 429

                conn.execute(
                    "UPDATE integration_keys SET last_used_at = datetime('now') WHERE key_id = ?",
                    (str(key_id),),
                )

            request.integration_key_id = key_id
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return decorated_function


# ============================================================================
# ASSINATURA DE ASSETS DE VEÍCULOS
# ============================================================================

def get_vehicle_asset_signing_secret(config: Optional[Dict] = None) -> str:
    """Obter secret para assinatura de URLs de assets de veículos."""
    try:
        if config:
            auth_config = config.get("auth", {}) or {}
            jwt_secret = auth_config.get(
                "jwt_secret", "ssm-backend-secret-key-change-in-production"
            )
            return str(jwt_secret or "")
    except Exception:
        pass
    return "ssm-backend-secret-key-change-in-production"


def sign_vehicle_asset(filename: str, exp_unix: int, secret: str = None) -> str:
    """Gerar assinatura HMAC para um asset de veículo."""
    if secret is None:
        secret = get_vehicle_asset_signing_secret()
    secret_bytes = secret.encode("utf-8")
    msg = f"vehicles_asset|{filename}|{int(exp_unix)}".encode("utf-8")
    return hmac.new(secret_bytes, msg, hashlib.sha256).hexdigest()


def is_valid_vehicle_asset_signature(filename: str, exp_unix: int, sig: str, secret: str = None) -> bool:
    """Verificar se uma assinatura de asset de veículo é válida."""
    if not sig:
        return False
    expected = sign_vehicle_asset(filename, exp_unix, secret)
    try:
        return hmac.compare_digest(str(sig), str(expected))
    except Exception:
        return False


def make_signed_vehicle_asset_url(image_url: str, *, ttl_seconds: int = 3600, secret: str = None) -> str:
    """Gerar URL assinada para um asset de veículo."""
    try:
        if not image_url:
            return ""
        s = str(image_url).strip()
        if not s:
            return ""
        filename = s.rsplit("/", 1)[-1]
        if not filename or filename != os.path.basename(filename):
            return s
        now = int(time.time())
        exp = now + int(ttl_seconds)
        sig = sign_vehicle_asset(filename, exp, secret)
        qs = urlencode({"exp": str(exp), "sig": str(sig)})
        if "?" in s:
            return f"{s}&{qs}"
        return f"{s}?{qs}"
    except Exception:
        return str(image_url or "")
