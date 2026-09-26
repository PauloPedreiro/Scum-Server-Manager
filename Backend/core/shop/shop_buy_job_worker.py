import hashlib
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from utils.logger import StructuredLogger

from core.shop.db import ssm_tx
from core.shop.shop_service import OrderCreateItem, ShopService


@dataclass
class BuyJob:
    job_id: str
    idempotency_key: str
    steam_id: str
    player_name: str
    items: List[OrderCreateItem]
    items_text: str
    status: str
    attempt_count: int
    created_at: Optional[str]


class ShopBuyJobWorker:
    def __init__(
        self,
        ssm_db_path: str,
        logger: Optional[StructuredLogger] = None,
        poll_interval_seconds: float = 1.0,
        lock_retry_max_seconds: int = 600,
        per_player_limit: int = 5,
    ):
        self.ssm_db_path = ssm_db_path
        self.logger = logger or StructuredLogger()
        self.poll_interval_seconds = float(poll_interval_seconds)
        self.lock_retry_max_seconds = int(lock_retry_max_seconds)
        self.per_player_limit = int(per_player_limit)

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._worker_id = f"shop-buy-worker-{int(time.time())}"

        self.shop_log_webhook = self._load_shop_log_webhook()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._ensure_schema()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _load_shop_log_webhook(self) -> str:
        try:
            import sys
            from pathlib import Path
            webhooks_file = "data/webhooks.json"
            if getattr(sys, "frozen", False):
                webhooks_path = Path(sys.executable).parent / webhooks_file
            else:
                webhooks_path = Path(webhooks_file)
            with open(webhooks_path, "r", encoding="utf-8") as f:
                webhooks = json.load(f)
            return str(webhooks.get("shop-log", "") or "")
        except Exception:
            return ""

    def _send_shop_log_message(self, message: str) -> None:
        try:
            if not self.shop_log_webhook:
                return
            payload = {"content": str(message)}
            requests.post(self.shop_log_webhook, json=payload, timeout=10)
        except Exception:
            return

    def _ensure_schema(self) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_buy_job (
                    job_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    steam_id TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    items_json TEXT NOT NULL,
                    items_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at TEXT,
                    locked_by TEXT,
                    locked_at TEXT,
                    order_id TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_shop_buy_job_pick
                ON shop_buy_job(status, next_attempt_at, created_at)
                """
            )

    def enqueue_buy_job(
        self,
        *,
        job_id: str,
        idempotency_key: str,
        steam_id: str,
        player_name: str,
        items: List[OrderCreateItem],
        items_text: str,
    ) -> Tuple[bool, str]:
        items_payload: List[Dict[str, Any]] = [
            {"code": int(i.code), "qty": int(i.qty), "is_kit": bool(getattr(i, "is_kit", False))} for i in items
        ]
        items_json = json.dumps(items_payload, ensure_ascii=False)

        with ssm_tx(self.ssm_db_path) as conn:
            cur = conn.execute(
                """
                SELECT COUNT(*)
                FROM shop_buy_job
                WHERE steam_id = ? AND status IN ('queued', 'processing')
                """,
                (steam_id,),
            )
            pending_count = int(cur.fetchone()[0] or 0)
            if pending_count >= self.per_player_limit:
                return False, "PLAYER_QUEUE_LIMIT"

            try:
                conn.execute(
                    """
                    INSERT INTO shop_buy_job(
                        job_id,
                        idempotency_key,
                        steam_id,
                        player_name,
                        items_json,
                        items_text,
                        status,
                        attempt_count,
                        created_at,
                        updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, 'queued', 0, datetime('now'), datetime('now'))
                    """,
                    (
                        job_id,
                        idempotency_key,
                        steam_id,
                        player_name,
                        items_json,
                        items_text,
                    ),
                )
            except sqlite3.IntegrityError:
                return False, "DUPLICATE"

        return True, "ENQUEUED"

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._requeue_stale_processing_jobs(max_age_seconds=120)
                job = self._claim_next_job()
                if not job:
                    time.sleep(self.poll_interval_seconds)
                    continue
                self._process_job(job)
            except Exception as e:
                self.logger.error(f"ShopBuyJobWorker loop error: {e}")
                time.sleep(2.0)

    def _requeue_stale_processing_jobs(self, max_age_seconds: int) -> None:
        try:
            threshold = (datetime.utcnow() - timedelta(seconds=int(max_age_seconds))).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            with ssm_tx(self.ssm_db_path) as conn:
                conn.execute(
                    """
                    UPDATE shop_buy_job
                    SET status='queued', locked_by=NULL, locked_at=NULL, updated_at=datetime('now')
                    WHERE status='processing' AND locked_at IS NOT NULL AND locked_at < ?
                    """,
                    (threshold,),
                )
        except Exception:
            return

    def _claim_next_job(self) -> Optional[BuyJob]:
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with ssm_tx(self.ssm_db_path) as conn:
            cur = conn.execute(
                """
                SELECT job_id, idempotency_key, steam_id, player_name, items_json, items_text, status, attempt_count, created_at
                FROM shop_buy_job
                WHERE status = 'queued'
                  AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (now_str,),
            )
            row = cur.fetchone()
            if not row:
                return None

            (
                job_id,
                idempotency_key,
                steam_id,
                player_name,
                items_json,
                items_text,
                status,
                attempt_count,
                created_at,
            ) = row

            res = conn.execute(
                """
                UPDATE shop_buy_job
                SET status='processing',
                    locked_by=?,
                    locked_at=datetime('now'),
                    attempt_count=attempt_count+1,
                    updated_at=datetime('now')
                WHERE job_id = ? AND status = 'queued'
                """,
                (self._worker_id, str(job_id)),
            )
            if res.rowcount != 1:
                return None

        items_data = json.loads(items_json or "[]")
        items: List[OrderCreateItem] = [
            OrderCreateItem(
                code=int(x.get("code")),
                qty=int(x.get("qty")),
                is_kit=bool(x.get("is_kit", False))
            )
            for x in items_data
            if int(x.get("code", 0)) > 0 and int(x.get("qty", 0)) > 0
        ]

        return BuyJob(
            job_id=str(job_id),
            idempotency_key=str(idempotency_key),
            steam_id=str(steam_id),
            player_name=str(player_name),
            items=items,
            items_text=str(items_text),
            status=str(status),
            attempt_count=int(attempt_count or 0),
            created_at=str(created_at) if created_at is not None else None,
        )

    def _job_age_seconds(self, created_at: Optional[str]) -> Optional[int]:
        if not created_at:
            return None
        try:
            dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            return int((datetime.utcnow() - dt).total_seconds())
        except Exception:
            return None

    def _backoff_seconds(self, attempt_count: int) -> int:
        schedule = [2, 5, 10, 20, 30, 60]
        idx = max(0, min(int(attempt_count) - 1, len(schedule) - 1))
        return int(schedule[idx])

    def _set_job_done(self, job_id: str, order_id: str) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            conn.execute(
                """
                UPDATE shop_buy_job
                SET status='done', order_id=?, locked_by=NULL, locked_at=NULL,
                    error_code=NULL, error_message=NULL, updated_at=datetime('now')
                WHERE job_id=?
                """,
                (str(order_id), str(job_id)),
            )

    def _set_job_failed(self, job_id: str, error_code: str, error_message: str) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            conn.execute(
                """
                UPDATE shop_buy_job
                SET status='failed', locked_by=NULL, locked_at=NULL,
                    error_code=?, error_message=?, updated_at=datetime('now')
                WHERE job_id=?
                """,
                (str(error_code), str(error_message), str(job_id)),
            )

    def _requeue_with_backoff(self, job_id: str, attempt_count: int) -> None:
        delay = self._backoff_seconds(attempt_count)
        next_at = (datetime.utcnow() + timedelta(seconds=delay)).strftime("%Y-%m-%d %H:%M:%S")
        with ssm_tx(self.ssm_db_path) as conn:
            conn.execute(
                """
                UPDATE shop_buy_job
                SET status='queued', locked_by=NULL, locked_at=NULL,
                    next_attempt_at=?, updated_at=datetime('now')
                WHERE job_id=?
                """,
                (next_at, str(job_id)),
            )

    def _send_rcon_combo_notification(self, steam_id: str, message: str) -> None:
        try:
            from core.rcon_queue_manager import RconQueueManager
            rcon_q = RconQueueManager.get_instance()
            # Enviar Tipo 4 (HUD) e Tipo 1 (Toast) direcionado ao SteamID
            rcon_q.execute_command_sync(f'SendNotification 4 0 "{message}" {steam_id}', delay_after=0.2, priority=5)
            rcon_q.execute_command_sync(f'SendNotification 1 0 "{message}" {steam_id}', delay_after=0.2, priority=5)
        except Exception as e:
            try:
                self.logger.error(f"Erro ao enviar notificacao combo RCON para {steam_id}: {e}")
            except Exception:
                pass




    def _process_job(self, job: BuyJob) -> None:
        try:
            shop = ShopService(self.ssm_db_path, logger=self.logger)
            res = shop.create_order(job.steam_id, job.items, player_name=job.player_name, source="chat")
            self._set_job_done(job.job_id, res.order_id)

            # Disparar entrega imediata via thread assíncrona
            def trigger_delivery_async():
                try:
                    import json
                    import sys
                    from pathlib import Path
                    scum_db_path = "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
                    try:
                        config_file = "data/config.json"
                        if getattr(sys, "frozen", False):
                            exe_dir = Path(sys.executable).parent
                            config_path = exe_dir / config_file
                        else:
                            config_path = Path(config_file)
                        with open(config_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                            scum_db_path = cfg.get("paths", {}).get("scum_server", {}).get("database", scum_db_path)
                    except Exception:
                        pass
                    
                    from core.shop.delivery_service import ShopDeliveryService
                    svc = ShopDeliveryService(self.ssm_db_path, scum_db_path, logger=self.logger)
                    svc.run_once(limit=10)
                except Exception as e:
                    try:
                        self.logger.error(f"Erro ao disparar entrega imediata: {e}")
                    except Exception:
                        pass
            
            threading.Thread(target=trigger_delivery_async, daemon=True).start()


            item_lines: List[str] = []
            try:
                parts = [p.strip() for p in str(job.items_text or "").split("|") if p.strip()]
                item_lines = [f"- {p}" for p in parts]
            except Exception:
                item_lines = []

            self._send_shop_log_message(
                "```text\n"
                + "\n".join(
                    [
                        "SYSTEM RECORD",
                        "================================================",
                        f"PLAYER: {job.player_name} | STATUS: ALIVE",
                        "------------------------------------------------",
                        "SENTENCE: CONFIRMED",
                        "------------------------------------------------",
                        "ITEMS ISSUED:",
                        *item_lines,
                        "------------------------------------------------",
                        "NO REFUNDS | NO MERCY | NO RESPAWN",
                        "================================================",
                    ]
                )
                + "\n```"
            )
        except ValueError as e:
            code = str(e)
            msg = "Error creating order."
            if "KIT_ALREADY_PURCHASED" in code:
                msg = "This kit is a one-time purchase and you have already acquired it."
                err_code = "KIT_ALREADY_PURCHASED"
            elif "MAILBOX_NOT_REGISTERED" in code:
                msg = "You do not have a mailbox linked. Use /mail <id>."
                err_code = "MAILBOX_NOT_REGISTERED"
            elif "PLAYER_NOT_REGISTERED" in code:
                msg = "You are not registered. Link your account in the Discord registration channel."
                err_code = "PLAYER_NOT_REGISTERED"
            elif "INSUFFICIENT_FUNDS" in code:
                try:
                    from core.shop.wallet_service import WalletService
                    wallet = WalletService(self.ssm_db_path, logger=self.logger)
                    balance = wallet.get_balance(job.steam_id)
                    
                    insufficient_funds_msg = "Insufficient funds! Your current balance: {balance}"
                    try:
                        import json
                        import sys
                        from pathlib import Path
                        config_file = "data/config.json"
                        if getattr(sys, "frozen", False):
                            exe_dir = Path(sys.executable).parent
                            config_path = exe_dir / config_file
                        else:
                            config_path = Path(config_file)
                        if config_path.exists():
                            with open(config_path, "r", encoding="utf-8") as f:
                                cfg = json.load(f)
                            notif_cfg = cfg.get("shop_notifications", {})
                            insufficient_funds_msg = notif_cfg.get("insufficient_funds", insufficient_funds_msg)
                    except Exception:
                        pass
                    
                    msg = insufficient_funds_msg.replace("{balance}", str(balance))
                except Exception:
                    msg = "Insufficient funds."
                err_code = "INSUFFICIENT_FUNDS"
            elif code.startswith("OFFER_NOT_AVAILABLE:"):
                msg = f"Invalid/unavailable item: {code.split(':', 1)[1]}"
                err_code = "OFFER_NOT_AVAILABLE"
            elif code.startswith("OFFER_DISABLED:"):
                msg = f"Item unavailable: {code.split(':', 1)[1]}"
                err_code = "OFFER_DISABLED"
            elif code.startswith("MAX_PER_ORDER:"):
                msg = f"Quantity exceeds item limit: {code.split(':', 1)[1]}"
                err_code = "MAX_PER_ORDER"
            elif code.startswith("NOT_A_KIT:"):
                msg = f"Code {code.split(':', 1)[1]} is not a kit. Use /buy."
                err_code = "NOT_A_KIT"
            elif code.startswith("IS_A_KIT_USE_KIT_COMMAND:"):
                msg = f"Code {code.split(':', 1)[1]} is a kit. Use /kit."
                err_code = "IS_A_KIT"
            else:
                err_code = "ERROR"

            self._set_job_failed(job.job_id, err_code, code)
            self._send_shop_log_message(
                "\n".join(
                    [
                        f"**{job.player_name}** : Order failed: {msg}",
                        f"Order: {job.items_text}",
                    ]
                )
            )
            # Enviar notificacao in-game do erro via RCON combo
            self._send_rcon_combo_notification(job.steam_id, msg)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                age = self._job_age_seconds(job.created_at)
                if age is not None and age >= self.lock_retry_max_seconds:
                    self._set_job_failed(job.job_id, "DB_LOCK_TIMEOUT", str(e))
                    self._send_shop_log_message(
                        "\n".join(
                            [
                                f"**{job.player_name}** : Order failed (timeout). Database busy for too long.",
                                f"Order: {job.items_text}",
                            ]
                        )
                    )
                    return

                self._requeue_with_backoff(job.job_id, max(1, job.attempt_count + 1))
                return

            self._set_job_failed(job.job_id, "SQLITE_ERROR", str(e))
            self._send_shop_log_message(
                "\n".join(
                    [
                        f"**{job.player_name}** : Order failed: internal error.",
                        f"Order: {job.items_text}",
                    ]
                )
            )
        except Exception as e:
            self._set_job_failed(job.job_id, "ERROR", str(e))
            self._send_shop_log_message(
                "\n".join(
                    [
                        f"**{job.player_name}** : Order failed: internal error.",
                        f"Order: {job.items_text}",
                    ]
                )
            )


def compute_idempotency_key(command_id: str) -> str:
    h = hashlib.sha1(str(command_id).encode("utf-8"))
    return h.hexdigest()
