from core.database.connector import DatabaseConnector
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from utils.logger import StructuredLogger

from core.shop.db import ssm_tx
from core.shop.rewards_service import RewardsService
from core.shop.wallet_service import WalletService


@dataclass
class OrderCreateItem:
    code: int
    qty: int
    is_kit: bool = False


@dataclass
class OrderCreateResult:
    order_id: str
    total_price: int
    balance: int


class ShopService:
    def __init__(self, ssm_db_path: str, logger: Optional[StructuredLogger] = None):
        self.ssm_db_path = ssm_db_path
        self.logger = logger or StructuredLogger()

    def _is_rcon_enabled(self) -> bool:
        """Verifica se a entrega via RCON está habilitada no config.json."""
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
                
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            rcon = cfg.get("rcon", {})
            if not rcon.get("enabled", False):
                return False
            provider = str(rcon.get("provider", "bsbr_scum")).lower()
            if provider == "bsbr_scum":
                return True
            return bool(rcon.get("password", ""))
        except Exception:
            return False


    def get_mailbox(self, steam_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
        if conn is not None:
            cur = conn.execute(
                "SELECT chest_id FROM player_mailbox WHERE steam_id = ?",
                (steam_id,),
            )
            row = cur.fetchone()
            return int(row[0]) if row else None

        with DatabaseConnector.get_connection(self.ssm_db_path) as conn:
            cur = conn.execute(
                "SELECT chest_id FROM player_mailbox WHERE steam_id = ?",
                (steam_id,),
            )
            row = cur.fetchone()
            return int(row[0]) if row else None

    def upsert_mailbox(self, steam_id: str, chest_id: int) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            conn.execute(
                """
                INSERT INTO player_mailbox(steam_id, chest_id, updated_at)
                VALUES(?, ?, datetime('now'))
                ON CONFLICT(steam_id) DO UPDATE SET
                    chest_id = excluded.chest_id,
                    updated_at = datetime('now')
                """,
                (steam_id, int(chest_id)),
            )

            try:
                rewards = RewardsService(self.ssm_db_path, logger=self.logger)
                default_rule_id = rewards.get_playtime_rule_id_by_name("Padrão", conn=conn)
                if default_rule_id:
                    rewards.add_playtime_rule_target_conn(str(default_rule_id), str(steam_id), conn)
            except Exception as e:
                try:
                    self.logger.error(f"Falha ao inserir steam_id={steam_id} na regra de playtime 'Padrão' após /mail: {e}")
                except Exception:
                    pass

    def create_order(
        self,
        steam_id: str,
        items: List[OrderCreateItem],
        player_name: Optional[str] = None,
        source: str = "web",
    ) -> OrderCreateResult:
        if not items:
            raise ValueError("NO_ITEMS")

        # Normalize / merge by code
        merged: Dict[int, int] = {}
        is_kit_by_code: Dict[int, bool] = {}
        for it in items:
            if it.qty <= 0:
                continue
            code_i = int(it.code)
            merged[code_i] = merged.get(code_i, 0) + int(it.qty)
            is_kit_by_code[code_i] = is_kit_by_code.get(code_i, False) or bool(getattr(it, "is_kit", False))

        if not merged:
            raise ValueError("NO_ITEMS")

        order_id = str(uuid4())

        with ssm_tx(self.ssm_db_path) as conn:
            # Verificar se entrega é via RCON (não exige mailbox nesse caso)
            rcon_enabled = self._is_rcon_enabled()

            # Verificar se o jogador está registrado (vinculado ao Discord)
            cur_player = conn.execute(
                "SELECT discord_user_id FROM players WHERE steam_id = ?",
                (steam_id,),
            ).fetchone()

            if rcon_enabled:
                # Se RCON está ativo, não exige mailbox, mas exige vínculo Steam-Discord
                if not cur_player or not cur_player[0]:
                    raise ValueError("PLAYER_NOT_REGISTERED")
                mailbox_chest_id = self.get_mailbox(steam_id, conn=conn)  # opcional, pode ser None
            else:
                # Modo legado: exige mailbox cadastrada
                mailbox_chest_id = self.get_mailbox(steam_id, conn=conn)
                if mailbox_chest_id is None:
                    raise ValueError("MAILBOX_NOT_REGISTERED")

            try:
                conn.execute("ALTER TABLE shop_order ADD COLUMN player_name TEXT")
            except Exception:
                pass

            # Validate offers and compute total
            total_price = 0
            resolved: List[Tuple[int, str, int, int, Optional[int]]] = []
            # (code, setup, qty, price, max_per_order)
            for code, qty in merged.items():
                is_kit_requested = is_kit_by_code.get(int(code), False)
                cur_kit = None
                if is_kit_requested:
                    # Verificar se é um kit cadastrado
                    cur_kit = conn.execute(
                        "SELECT kit_id, name, price, enabled, only_once, auto_deliver_on_register FROM shop_kit WHERE code = ?",
                        (int(code),),
                    ).fetchone()

                if is_kit_requested:
                    if not cur_kit:
                        raise ValueError(f"KIT_NOT_FOUND:{code}")
                    kit_id, kit_name, price, enabled, only_once, auto_deliver_on_register = cur_kit
                    setup = f"KIT:{kit_id}"
                    offer_qty = 1
                    max_per_order = 1
                else:
                    cur = conn.execute(
                        """
                        SELECT c.setup, o.qty, o.price, o.enabled, o.max_per_order
                        FROM shop_catalog c
                        INNER JOIN shop_offer o ON o.code = c.code
                        WHERE c.code = ? AND c.enabled = 1
                        """,
                        (int(code),),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise ValueError(f"OFFER_NOT_AVAILABLE:{code}")
                    setup, offer_qty, price, enabled, max_per_order = row
                    only_once = 0

                # Permitir kits de auto-entrega no registro mesmo se desabilitados no catalogo geral
                if is_kit_requested and int(auto_deliver_on_register or 0) == 1:
                    pass
                elif int(enabled) != 1:
                    raise ValueError(f"OFFER_DISABLED:{code}")

                if max_per_order is not None and int(qty) > int(max_per_order):
                    raise ValueError(f"MAX_PER_ORDER:{code}")

                # Se veio do chat, validar se o comando condiz com o tipo do item
                if source == "chat":
                    setup_str = str(setup or "")
                    is_actual_kit = setup_str.startswith("KIT:")

                    if is_kit_requested and not is_actual_kit:
                        raise ValueError(f"NOT_A_KIT:{code}")
                    if not is_kit_requested and is_actual_kit:
                        raise ValueError(f"IS_A_KIT_USE_KIT_COMMAND:{code}")

                # Verificar se é um kit com compra única (only_once)
                if int(only_once) == 1:
                    cur_ordered = conn.execute(
                        """
                        SELECT 1 FROM shop_order o
                        INNER JOIN shop_order_item oi ON oi.order_id = o.order_id
                        WHERE o.steam_id = ? AND oi.setup = ? AND o.status IN ('pending', 'delivering', 'delivered')
                        LIMIT 1
                        """,
                        (steam_id, setup),
                    )
                    if cur_ordered.fetchone():
                        raise ValueError(f"KIT_ALREADY_PURCHASED:{code}")

                unit_price = int(price or 0)
                total_price += unit_price * int(qty)
                resolved.append((int(code), str(setup), int(qty), unit_price, max_per_order))

            # Insert order
            try:
                conn.execute(
                    """
                    INSERT INTO shop_order(order_id, steam_id, player_name, chest_id, total_price, status)
                    VALUES(?, ?, ?, ?, ?, 'pending')
                    """,
                    (
                        order_id,
                        steam_id,
                        str(player_name or "") or None,
                        int(mailbox_chest_id) if mailbox_chest_id is not None else None,
                        int(total_price),
                    ),
                )
            except sqlite3.OperationalError:
                conn.execute(
                    """
                    INSERT INTO shop_order(order_id, steam_id, chest_id, total_price, status)
                    VALUES(?, ?, ?, ?, 'pending')
                    """,
                    (
                        order_id,
                        steam_id,
                        int(mailbox_chest_id) if mailbox_chest_id is not None else None,
                        int(total_price),
                    ),
                )

            for code, setup, qty, _price, _m in resolved:
                conn.execute(
                    """
                    INSERT INTO shop_order_item(order_id, code, setup, qty)
                    VALUES(?, ?, ?, ?)
                    """,
                    (order_id, int(code), setup, int(qty)),
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO shop_delivery_item(order_id, code, qty_delivered)
                    VALUES(?, ?, 0)
                    """,
                    (order_id, int(code)),
                )

            # Debit wallet (no negative)
            wallet = WalletService(self.ssm_db_path, logger=self.logger)
            apply_res = wallet.apply_delta(
                steam_id=steam_id,
                delta=-int(total_price),
                reason="shop_purchase",
                ref_type="order",
                ref_id=order_id,
                meta={"order_id": order_id},
                allow_negative=False,
                conn=conn,
            )

            return OrderCreateResult(
                order_id=order_id,
                total_price=int(total_price),
                balance=int(apply_res.balance),
            )

    def request_retry(self, order_id: str) -> bool:
        with ssm_tx(self.ssm_db_path) as conn:
            cur = conn.execute(
                "SELECT status FROM shop_order WHERE order_id = ?",
                (order_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("ORDER_NOT_FOUND")
            status = str(row[0])
            if status != "failed":
                return False
            conn.execute(
                "UPDATE shop_order SET retry_requested = 1 WHERE order_id = ?",
                (order_id,),
            )
            return True
