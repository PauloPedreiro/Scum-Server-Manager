from core.database.connector import DatabaseConnector
import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from utils.logger import StructuredLogger

from core.shop.db import ssm_tx


@dataclass
class WalletApplyResult:
    steam_id: str
    balance: int
    tx_id: Optional[str]
    already_applied: bool


class WalletService:
    def __init__(self, ssm_db_path: str, logger: Optional[StructuredLogger] = None):
        self.ssm_db_path = ssm_db_path
        self.logger = logger or StructuredLogger()

    def get_balance(self, steam_id: str) -> int:
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()
            cur.execute("SELECT balance FROM wallet WHERE steam_id = ?", (steam_id,))
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def _get_initial_balance(self) -> int:
        try:
            import os
            config_file = "data/config.json"
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    economy = config.get("economy")
                    if isinstance(economy, dict):
                        return int(economy.get("initial_balance", 0))
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error loading initial_balance from config.json: {e}")
        return 0

    def ensure_wallet_row(self, conn: sqlite3.Connection, steam_id: str) -> None:
        initial_balance = self._get_initial_balance()
        conn.execute(
            "INSERT OR IGNORE INTO wallet(steam_id, balance) VALUES(?, ?)",
            (steam_id, initial_balance),
        )

    def apply_delta(
        self,
        steam_id: str,
        delta: int,
        reason: str,
        ref_type: Optional[str],
        ref_id: Optional[str],
        meta: Optional[Dict[str, Any]] = None,
        allow_negative: bool = False,
        conn: Optional[sqlite3.Connection] = None,
    ) -> WalletApplyResult:
        if conn is not None:
            return self._apply_delta_with_conn(
                conn,
                steam_id=steam_id,
                delta=delta,
                reason=reason,
                ref_type=ref_type,
                ref_id=ref_id,
                meta=meta,
                allow_negative=allow_negative,
            )

        with ssm_tx(self.ssm_db_path) as tx_conn:
            return self._apply_delta_with_conn(
                tx_conn,
                steam_id=steam_id,
                delta=delta,
                reason=reason,
                ref_type=ref_type,
                ref_id=ref_id,
                meta=meta,
                allow_negative=allow_negative,
            )

    def _apply_delta_with_conn(
        self,
        conn: sqlite3.Connection,
        *,
        steam_id: str,
        delta: int,
        reason: str,
        ref_type: Optional[str],
        ref_id: Optional[str],
        meta: Optional[Dict[str, Any]] = None,
        allow_negative: bool = False,
    ) -> WalletApplyResult:
        tx_id = str(uuid4())
        meta_json = json.dumps(meta or {}, ensure_ascii=False)

        self.ensure_wallet_row(conn, steam_id)

        # Idempotency: unique on (steam_id, reason, ref_type, ref_id)
        if ref_type is not None and ref_id is not None:
            try:
                conn.execute(
                    """
                    INSERT INTO wallet_tx(tx_id, steam_id, delta, reason, ref_type, ref_id, meta_json)
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tx_id, steam_id, int(delta), reason, ref_type, ref_id, meta_json),
                )
            except sqlite3.IntegrityError:
                # already applied
                balance = self._recalc_balance(conn, steam_id)
                return WalletApplyResult(
                    steam_id=steam_id,
                    balance=balance,
                    tx_id=None,
                    already_applied=True,
                )
        else:
            conn.execute(
                """
                INSERT INTO wallet_tx(tx_id, steam_id, delta, reason, ref_type, ref_id, meta_json)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (tx_id, steam_id, int(delta), reason, ref_type, ref_id, meta_json),
            )

        cur = conn.execute("SELECT balance FROM wallet WHERE steam_id = ?", (steam_id,))
        row = cur.fetchone()
        current_balance = int(row[0]) if row else 0
        new_balance = current_balance + int(delta)
        if not allow_negative and new_balance < 0:
            raise ValueError("INSUFFICIENT_FUNDS")

        conn.execute(
            "UPDATE wallet SET balance = ?, updated_at = datetime('now') WHERE steam_id = ?",
            (int(new_balance), steam_id),
        )

        return WalletApplyResult(
            steam_id=steam_id,
            balance=int(new_balance),
            tx_id=tx_id,
            already_applied=False,
        )

    def _recalc_balance(self, conn: sqlite3.Connection, steam_id: str) -> int:
        cur = conn.execute("SELECT balance FROM wallet WHERE steam_id = ?", (steam_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0
