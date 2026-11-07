from core.database.connector import DatabaseConnector
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import threading

import requests

from utils.logger import StructuredLogger
from utils.rcon_client import is_rcon_error_response, is_rcon_tick_frozen

from core.shop.db import ssm_tx
from core.shop.scum_delivery import ScumChestSpawner

_delivery_lock = threading.Lock()
_last_rcon_delivery_ts: float = 0.0

# Intervalos de proteção da Game Thread da Unreal Engine (anti-crash)
_INTER_ORDER_COOLDOWN_SEC: float = 2.5
_DELAY_NORMAL_ITEM_SEC: float = 0.8
_DELAY_HEAVY_ITEM_SEC: float = 1.5
_MAX_TRANSIENT_ATTEMPTS: int = 8

# Correções automáticas de typos comuns em nomes de classes do SCUM
_CLASS_TYPO_FIXES: Dict[str, str] = {
    "water_051": "Water_05l",
}


@dataclass
class DeliveryJobResult:
    processed_orders: int
    delivered_orders: int
    failed_orders: int


def _load_rcon_config(config_path: str = "data/config.json") -> dict:
    """Carrega a seção 'rcon' do config.json."""
    try:
        import sys
        from pathlib import Path
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            resolved_path = exe_dir / config_path
        else:
            resolved_path = Path(config_path)
        with open(resolved_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("rcon", {})
    except Exception:
        return {}


def _is_rcon_enabled(rcon_cfg: Optional[dict] = None) -> bool:
    """Verifica se o RCON está habilitado (para bsbr_scum não exige senha)."""
    if rcon_cfg is None:
        rcon_cfg = _load_rcon_config()
    if not rcon_cfg.get("enabled", False):
        return False
    provider = str(rcon_cfg.get("provider", "bsbr_scum")).lower()
    if provider == "bsbr_scum":
        return True
    return bool(rcon_cfg.get("password", ""))


def _is_vehicle(item_class: str) -> bool:
    """Heurística: classes de veículos no SCUM começam com BP_ ou BPC_."""
    cls = str(item_class).strip()
    return cls.startswith("BPC_") or cls.startswith("BP_")


def _is_heavy_actor(item_class: str) -> bool:
    """Identifica atores complexos (veículos e armas) que exigem maior intervalo de tick na UE4."""
    cls = str(item_class).strip()
    return _is_vehicle(cls) or cls.lower().startswith("weapon_")


def _build_spawnitem_cmd(raw_setup: str, qty: int, steam_id: str) -> str:
    """
    Sanitiza o setup de um item (removendo sufixo _ES, corrigindo typos conhecidos
    e posicionando corretamente a quantidade quando há StackCount embutido) e monta o comando RCON.
    """
    clean_setup = str(raw_setup).strip()
    if clean_setup.endswith("_ES"):
        clean_setup = clean_setup[:-3].strip()

    # Verificar se há StackCount embutido (ex: "Cash 1 StackCount 5000" ou "Cash StackCount 5000")
    m_stack = re.match(
        r"^(\S+?)(?:\s+\d+)?\s+(StackCount\s+\d+.*)$",
        clean_setup,
        flags=re.IGNORECASE,
    )
    if m_stack:
        asset_name = m_stack.group(1)
        stack_part = m_stack.group(2).strip()
        asset_name = _CLASS_TYPO_FIXES.get(asset_name.lower(), asset_name)
        return f'spawnitem {asset_name} {int(qty)} {stack_part} Location "{steam_id}"'

    clean_setup = _CLASS_TYPO_FIXES.get(clean_setup.lower(), clean_setup)
    return f'spawnitem {clean_setup} {int(qty)} Location "{steam_id}"'


def _wait_inter_order_cooldown() -> None:
    """Garante um intervalo mínimo entre o término de um pedido RCON e o início do próximo."""
    global _last_rcon_delivery_ts
    if _last_rcon_delivery_ts > 0:
        elapsed = time.time() - _last_rcon_delivery_ts
        if elapsed < _INTER_ORDER_COOLDOWN_SEC:
            time.sleep(_INTER_ORDER_COOLDOWN_SEC - elapsed)


def _mark_rcon_delivery_finished() -> None:
    global _last_rcon_delivery_ts
    _last_rcon_delivery_ts = time.time()


class ShopDeliveryService:
    def __init__(
        self,
        ssm_db_path: str,
        scum_db_path: str,
        logger: Optional[StructuredLogger] = None,
    ):
        self.ssm_db_path = ssm_db_path
        self.scum_db_path = scum_db_path
        self.logger = logger or StructuredLogger()
        self.shop_log_webhook = self._load_shop_log_webhook()

    def _load_shop_log_webhook(self) -> str:
        try:
            webhooks_path = "data/webhooks.json"
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

    def _resolve_player_name(self, steam_id: str) -> str:
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT name FROM players WHERE steam_id = ? ORDER BY updated_at DESC LIMIT 1",
                    (str(steam_id),),
                )
                row = cur.fetchone()
                if row and row[0]:
                    return str(row[0])
        except Exception:
            pass
        return "Player"

    def _format_items_for_discord(self, order_id: str) -> str:
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT i.code,
                           COALESCE(NULLIF(c.display_name, ''), i.setup) AS name,
                           i.qty
                    FROM shop_order_item i
                    LEFT JOIN shop_catalog c ON c.code = i.code
                    WHERE i.order_id = ?
                    ORDER BY i.code ASC
                    """,
                    (str(order_id),),
                )
                rows = cur.fetchall()
            parts: List[str] = []
            for code, name, qty in rows:
                label = str(name) if name else str(code)
                parts.append(f"{label} x{int(qty)}")
            return " | ".join(parts)
        except Exception:
            return ""

    def run_once(self, limit: int = 50) -> DeliveryJobResult:
        with _delivery_lock:
            processed = 0
            delivered = 0
            failed = 0

            # Decidir modo de entrega
            rcon_cfg = _load_rcon_config()
            rcon_enabled = _is_rcon_enabled(rcon_cfg)
            online_steam_ids = set()

            if rcon_enabled:
                from core.rcon_queue_manager import RconQueueManager
                rcon_q = RconQueueManager.get_instance()
                cb_open, cb_rem = rcon_q.is_circuit_open()
                if cb_open:
                    if self.logger:
                        self.logger.debug(
                            f"ShopDelivery: RCON Circuit Breaker ativo ({cb_rem:.1f}s) — ciclo adiado."
                        )
                    return DeliveryJobResult(0, 0, 0)

                try:
                    from utils.rcon_client import _parse_steam_ids_from_listplayers
                    raw_response = rcon_q.execute_command_sync("ListPlayers", delay_after=0.5, priority=10, origin="SHOP")
                    if raw_response and ("sem resposta" in raw_response.lower() or "tick do jogo" in raw_response.lower()):
                        rcon_q.trip_circuit(cooldown=20.0, reason=raw_response)
                        return DeliveryJobResult(0, 0, 0)
                    online_steam_ids = set(_parse_steam_ids_from_listplayers(raw_response))
                except Exception as e:
                    if self.logger:
                        self.logger.warn(f"ShopDelivery: não foi possível listar jogadores via RCON: {e}")
                    return DeliveryJobResult(0, 0, 0)

            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn_ro:
                conn_ro.row_factory = sqlite3.Row
                cur = conn_ro.cursor()
                if rcon_enabled and online_steam_ids:
                    placeholders = ",".join("?" for _ in online_steam_ids)
                    sql = f"""
                    SELECT order_id
                    FROM shop_order
                    WHERE status = 'pending'
                       OR (status = 'failed' AND retry_requested = 1)
                    ORDER BY CASE WHEN steam_id IN ({placeholders}) THEN 0 ELSE 1 END, created_at ASC
                    LIMIT ?
                    """
                    cur.execute(sql, (*online_steam_ids, int(limit)))
                else:
                    cur.execute(
                        """
                        SELECT order_id
                        FROM shop_order
                        WHERE status = 'pending'
                           OR (status = 'failed' AND retry_requested = 1)
                        ORDER BY created_at ASC
                        LIMIT ?
                        """,
                        (int(limit),),
                    )
                order_ids = [str(r[0]) for r in cur.fetchall()]

            if not order_ids:
                return DeliveryJobResult(0, 0, 0)

            if rcon_enabled:
                for order_id in order_ids:
                    processed += 1
                    ok, err = self._deliver_order_rcon(
                        order_id=order_id,
                        online_steam_ids=online_steam_ids,
                    )
                    if ok:
                        delivered += 1
                    else:
                        failed += 1
                        if err and (
                            err.startswith("RCON_TICK_FROZEN")
                            or err.startswith("RCON_CIRCUIT_OPEN")
                        ):
                            if self.logger:
                                self.logger.warn(
                                    f"ShopDelivery: interrompendo lote de entregas para proteger o servidor ({err})."
                                )
                            break
            else:
                # Entrega legada via SCUM.db (baú/mailbox)
                spawner = ScumChestSpawner(self.scum_db_path, logger=self.logger)
                for order_id in order_ids:
                    processed += 1
                    ok, err = self._deliver_order(order_id, spawner)
                    if ok:
                        delivered += 1
                    else:
                        failed += 1

            return DeliveryJobResult(
                processed_orders=processed,
                delivered_orders=delivered,
                failed_orders=failed,
            )

    # ------------------------------------------------------------------
    # RCON delivery
    # ------------------------------------------------------------------

    def deliver_single_order_now(self, order_id: str) -> Tuple[bool, Optional[str]]:
        """
        Entrega imediata de um pedido específico sem consultar ListPlayers,
        protegida por _delivery_lock para evitar concorrência e sobrecarga do RCON.
        """
        with _delivery_lock:
            rcon_cfg = _load_rcon_config()
            rcon_enabled = _is_rcon_enabled(rcon_cfg)

            if rcon_enabled:
                return self._deliver_order_rcon(
                    order_id=order_id,
                    online_steam_ids=set(),
                    bypass_online_check=True,
                )
            else:
                # Fallback para baú/mailbox caso RCON esteja desativado
                spawner = ScumChestSpawner(self.scum_db_path, logger=self.logger)
                return self._deliver_order(order_id, spawner)

    def _execute_rcon_spawn(
        self,
        rcon_q: Any,
        cmd: str,
        delay_after: float,
    ) -> Tuple[bool, str]:
        """
        Executa um comando spawnitem/spawnvehicle via RCON e valida se o servidor
        processou com sucesso (detectando congelamento de tick ou erros).
        """
        cb_open, cb_rem = rcon_q.is_circuit_open()
        if cb_open:
            return False, f"RCON_CIRCUIT_OPEN:{cb_rem:.1f}s"

        resp = rcon_q.execute_command_sync(cmd, delay_after=delay_after, priority=5, origin="SHOP")
        if is_rcon_tick_frozen(resp):
            rcon_q.trip_circuit(cooldown=20.0, reason=resp or "RCON timeout during spawn")
            return False, f"RCON_TICK_FROZEN:{resp or 'timeout'}"

        if is_rcon_error_response(resp, allow_empty=False):
            return False, f"RCON_ERROR:{resp}"

        return True, str(resp)

    def _revert_or_fail_order(self, order_id: str, attempt_count: int, err_msg: str) -> None:
        """
        Em caso de falha transitória do RCON (ex: tick do servidor travado),
        devolve o pedido para 'pending' (até o limite de tentativas) para não perder o kit do jogador.
        """
        new_status = "pending" if int(attempt_count) < _MAX_TRANSIENT_ATTEMPTS else "failed"
        try:
            with ssm_tx(self.ssm_db_path) as conn_rev:
                conn_rev.execute(
                    """
                    UPDATE shop_order
                    SET status=?, error=?, last_attempt_at=datetime('now')
                    WHERE order_id=? AND status != 'delivered'
                    """,
                    (new_status, err_msg, order_id),
                )
        except Exception:
            pass

    def _deliver_order_rcon(
        self,
        order_id: str,
        online_steam_ids: Optional[set] = None,
        bypass_online_check: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """Tenta entregar um pedido via RCON. Se o jogador estiver offline ou o RCON falhar, preserva o progresso."""
        attempt_count = 1
        try:
            from core.rcon_queue_manager import RconQueueManager
            rcon_q = RconQueueManager.get_instance()
            cb_open, cb_rem = rcon_q.is_circuit_open()
            if cb_open:
                if self.logger:
                    self.logger.warn(
                        f"ShopDelivery RCON: Circuit Breaker aberto ({cb_rem:.1f}s) — pedido {order_id} aguarda."
                    )
                return False, f"RCON_CIRCUIT_OPEN:{cb_rem:.1f}s"

            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn_ro:
                conn_ro.row_factory = sqlite3.Row
                cur = conn_ro.cursor()
                cur.execute(
                    "SELECT steam_id, status, player_name, attempt_count FROM shop_order WHERE order_id = ?",
                    (order_id,),
                )
                row = cur.fetchone()

            if not row:
                return False, "ORDER_NOT_FOUND"

            steam_id = str(row["steam_id"])
            status = str(row["status"])
            order_player_name = row["player_name"] if "player_name" in row.keys() else None
            attempt_count = int(row["attempt_count"] or 0) + 1

            if status == "delivered":
                return True, None

            # Se o jogador não está online, manter pending (será entregue depois)
            if not bypass_online_check and (not online_steam_ids or steam_id not in online_steam_ids):
                if self.logger:
                    self.logger.debug(
                        f"ShopDelivery RCON: jogador {steam_id} offline — pedido {order_id} aguarda."
                    )
                return True, None  # True = não é um erro, apenas adiado

            # Buscar itens pendentes e progresso parcial de sub-itens de kits
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn_items:
                conn_items.row_factory = sqlite3.Row
                cur2 = conn_items.cursor()
                cur2.execute(
                    """
                    SELECT i.code, i.setup, i.qty,
                           COALESCE(d.qty_delivered, 0) AS qty_delivered
                    FROM shop_order_item i
                    LEFT JOIN shop_delivery_item d
                      ON d.order_id = i.order_id AND d.code = i.code
                    WHERE i.order_id = ?
                    """,
                    (order_id,),
                )
                items = cur2.fetchall()

                cur2.execute(
                    """
                    SELECT code, qty_delivered
                    FROM shop_delivery_item
                    WHERE order_id = ? AND code < 0
                    """,
                    (order_id,),
                )
                partial_kit_progress: Dict[int, int] = {
                    int(r["code"]): int(r["qty_delivered"] or 0) for r in cur2.fetchall()
                }

            # Marcar como entregando
            with ssm_tx(self.ssm_db_path) as conn_upd:
                res = conn_upd.execute(
                    """
                    UPDATE shop_order
                    SET status='delivering', attempt_count=attempt_count+1, last_attempt_at=datetime('now')
                    WHERE order_id=? AND (status='pending' OR (status='failed' AND retry_requested=1))
                    """,
                    (order_id,),
                )
                if res.rowcount == 0:
                    if self.logger:
                        self.logger.debug(
                            f"ShopDelivery RCON: pedido {order_id} ignorado pois já está sendo entregue ou finalizado."
                        )
                    return True, None

            # Respeitar intervalo entre pedidos consecutivos para não afogar a Game Thread
            _wait_inter_order_cooldown()

            for it in items:
                code = int(it["code"])
                setup = str(it["setup"])
                qty = int(it["qty"])
                qty_delivered = int(it["qty_delivered"] or 0)
                remaining = qty - qty_delivered

                if remaining <= 0:
                    continue

                # Verificar se é um kit cadastrado
                is_kit = setup.startswith("KIT:")
                kit_items = []
                if is_kit:
                    try:
                        kit_id = setup.split(":", 1)[1]
                        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn_kit:
                            conn_kit.row_factory = sqlite3.Row
                            cur_kit = conn_kit.cursor()
                            cur_kit.execute(
                                """
                                SELECT setup, qty
                                FROM shop_kit_item
                                WHERE kit_id = ?
                                """,
                                (kit_id,),
                            )
                            rows = cur_kit.fetchall()
                            kit_items = [(str(r["setup"]), int(r["qty"])) for r in rows]
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Erro ao buscar sub-itens do kit (setup {setup}): {e}")

                # Comandos de entrega universais via RCON (com verificação de resposta e cadência segura)
                if is_kit:
                    sub_step = 0
                    for _ in range(remaining):
                        for sub_setup, sub_qty in kit_items:
                            sub_step += 1
                            synth_code = -(abs(code) * 10000 + sub_step)
                            already_sub_del = partial_kit_progress.get(synth_code, 0)
                            if already_sub_del >= sub_qty:
                                continue

                            delay_sec = (
                                _DELAY_HEAVY_ITEM_SEC
                                if _is_heavy_actor(sub_setup)
                                else _DELAY_NORMAL_ITEM_SEC
                            )

                            if _is_vehicle(sub_setup):
                                rem_veh = sub_qty - already_sub_del
                                for _v in range(rem_veh):
                                    cmd = f'spawnvehicle {sub_setup.strip()} 1 Location "{steam_id}"'
                                    ok_cmd, resp_or_err = self._execute_rcon_spawn(rcon_q, cmd, delay_sec)
                                    if not ok_cmd:
                                        _mark_rcon_delivery_finished()
                                        self._revert_or_fail_order(order_id, attempt_count, resp_or_err)
                                        if self.logger:
                                            self.logger.warn(
                                                f"ShopDelivery RCON abortado em spawnvehicle ({sub_setup}) do pedido {order_id}: {resp_or_err}"
                                            )
                                        return False, resp_or_err
                                    if self.logger:
                                        self.logger.debug(f"Kit RCON spawnvehicle {sub_setup} → {resp_or_err}")
                            else:
                                cmd = _build_spawnitem_cmd(sub_setup, sub_qty, steam_id)
                                ok_cmd, resp_or_err = self._execute_rcon_spawn(rcon_q, cmd, delay_sec)
                                if not ok_cmd:
                                    _mark_rcon_delivery_finished()
                                    self._revert_or_fail_order(order_id, attempt_count, resp_or_err)
                                    if self.logger:
                                        self.logger.warn(
                                            f"ShopDelivery RCON abortado em spawnitem ({sub_setup}) do pedido {order_id}: {resp_or_err}"
                                        )
                                    return False, resp_or_err
                                if self.logger:
                                    self.logger.debug(f"Kit RCON {cmd} → {resp_or_err}")

                            # Persistir progresso individual do sub-item do kit
                            with ssm_tx(self.ssm_db_path) as conn_sub:
                                conn_sub.execute(
                                    """
                                    INSERT INTO shop_delivery_item(order_id, code, qty_delivered, last_delivered_at)
                                    VALUES(?, ?, ?, datetime('now'))
                                    ON CONFLICT(order_id, code) DO UPDATE SET
                                        qty_delivered = excluded.qty_delivered,
                                        last_delivered_at = datetime('now')
                                    """,
                                    (order_id, synth_code, int(sub_qty)),
                                )
                            partial_kit_progress[synth_code] = int(sub_qty)
                else:
                    delay_sec = (
                        _DELAY_HEAVY_ITEM_SEC
                        if _is_heavy_actor(setup)
                        else _DELAY_NORMAL_ITEM_SEC
                    )
                    if _is_vehicle(setup):
                        for _ in range(remaining):
                            cmd = f'spawnvehicle {setup.strip()} 1 Location "{steam_id}"'
                            ok_cmd, resp_or_err = self._execute_rcon_spawn(rcon_q, cmd, delay_sec)
                            if not ok_cmd:
                                _mark_rcon_delivery_finished()
                                self._revert_or_fail_order(order_id, attempt_count, resp_or_err)
                                if self.logger:
                                    self.logger.warn(
                                        f"ShopDelivery RCON abortado em spawnvehicle ({setup}) do pedido {order_id}: {resp_or_err}"
                                    )
                                return False, resp_or_err
                            if self.logger:
                                self.logger.debug(f"spawnvehicle {setup} → {resp_or_err}")
                            with ssm_tx(self.ssm_db_path) as conn_v:
                                conn_v.execute(
                                    """
                                    INSERT INTO shop_delivery_item(order_id, code, qty_delivered, last_delivered_at)
                                    VALUES(?, ?, 1, datetime('now'))
                                    ON CONFLICT(order_id, code) DO UPDATE SET
                                        qty_delivered = MIN(?, shop_delivery_item.qty_delivered + 1),
                                        last_delivered_at = datetime('now')
                                    """,
                                    (order_id, code, qty),
                                )
                        continue
                    else:
                        cmd = _build_spawnitem_cmd(setup, remaining, steam_id)
                        ok_cmd, resp_or_err = self._execute_rcon_spawn(rcon_q, cmd, delay_sec)
                        if not ok_cmd:
                            _mark_rcon_delivery_finished()
                            self._revert_or_fail_order(order_id, attempt_count, resp_or_err)
                            if self.logger:
                                self.logger.warn(
                                    f"ShopDelivery RCON abortado em spawnitem ({setup}) do pedido {order_id}: {resp_or_err}"
                                )
                            return False, resp_or_err
                        if self.logger:
                            self.logger.debug(f"{cmd} (original: {setup}) → {resp_or_err}")

                # Registrar entrega do item (e limpar marcadores temporários negativos se for kit)
                with ssm_tx(self.ssm_db_path) as conn_del:
                    conn_del.execute(
                        """
                        INSERT INTO shop_delivery_item(order_id, code, qty_delivered, last_delivered_at)
                        VALUES(?, ?, ?, datetime('now'))
                        ON CONFLICT(order_id, code) DO UPDATE SET
                            qty_delivered = MIN(?, shop_delivery_item.qty_delivered + excluded.qty_delivered),
                            last_delivered_at = datetime('now')
                        """,
                        (order_id, code, remaining, qty),
                    )
                    if is_kit:
                        conn_del.execute(
                            "DELETE FROM shop_delivery_item WHERE order_id = ? AND code < 0",
                            (order_id,),
                        )

            _mark_rcon_delivery_finished()

            # Enviar notificacao de sucesso via RCON
            try:
                welcome_kit_msg = "Your kit has been successfully delivered!"
                items_msg = "Your items have been successfully delivered!"
                try:
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
                        welcome_kit_msg = notif_cfg.get("welcome_kit_delivered", welcome_kit_msg)
                        items_msg = notif_cfg.get("items_delivered", items_msg)
                except Exception:
                    pass

                has_kit = any(str(it["setup"]).startswith("KIT:") for it in items)
                msg_success = welcome_kit_msg if has_kit else items_msg

                # Envia mensagem colorida e limpa no chat do jogador (SendChat tipo 6)
                rcon_q.execute_command_sync(
                    f'SendChat 6 "[SSM] {msg_success}" {steam_id}',
                    delay_after=0.3,
                    priority=5,
                    origin="SHOP",
                )

            except Exception as notify_err:
                if self.logger:
                    self.logger.error(f"Erro ao enviar notificacao de sucesso RCON para {steam_id}: {notify_err}")

            # Marcar pedido como entregue
            with ssm_tx(self.ssm_db_path) as conn_done:
                conn_done.execute(
                    """
                    UPDATE shop_order
                    SET status='delivered', delivered_at=datetime('now'), retry_requested=0, error=NULL
                    WHERE order_id=? AND status != 'delivered'
                    """,
                    (order_id,),
                )

            # Log no Discord
            try:
                player_name = str(order_player_name or "").strip() or self._resolve_player_name(steam_id)
                items_text = self._format_items_for_discord(order_id)
                item_lines: List[str] = []
                try:
                    parts = [p.strip() for p in str(items_text or "").split("|") if p.strip()]
                    item_lines = [f"- {p}" for p in parts]
                except Exception:
                    item_lines = []
                self._send_shop_log_message(
                    "```text\n"
                    + "\n".join(
                        [
                            "SYSTEM RECORD",
                            "================================================",
                            f"PLAYER: {player_name} | STATUS: ALIVE",
                            "------------------------------------------------",
                            "SENTENCE: DELIVERED (RCON)",
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
            except Exception:
                pass

            return True, None

        except Exception as e:
            err_msg = f"RCON_DELIVERY_EXCEPTION:{e}"
            self._revert_or_fail_order(order_id, attempt_count, err_msg)
            if self.logger:
                self.logger.error(f"ShopDelivery RCON: {err_msg}")
            return False, err_msg

    # ------------------------------------------------------------------
    # Legacy chest/mailbox delivery (mantido para compatibilidade)
    # ------------------------------------------------------------------

    def _deliver_order(self, order_id: str, spawner: ScumChestSpawner) -> Tuple[bool, Optional[str]]:
        now = datetime.utcnow().isoformat()

        try:
            with ssm_tx(self.ssm_db_path) as conn:
                order_player_name: Optional[str] = None
                try:
                    cur = conn.execute(
                        "SELECT steam_id, chest_id, status, player_name FROM shop_order WHERE order_id = ?",
                        (order_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        steam_id, chest_id, status, order_player_name = row
                    else:
                        steam_id, chest_id, status = None, None, None
                except Exception:
                    cur = conn.execute(
                        "SELECT steam_id, chest_id, status FROM shop_order WHERE order_id = ?",
                        (order_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        steam_id, chest_id, status = row
                    else:
                        steam_id, chest_id, status = None, None, None

                if not row:
                    return False, "ORDER_NOT_FOUND"

                if str(status) == "delivered":
                    return True, None
                chest_id = int(chest_id) if chest_id is not None else None
                if chest_id is None:
                    conn.execute(
                        "UPDATE shop_order SET status='failed', error=?, last_attempt_at=datetime('now'), attempt_count=attempt_count+1 WHERE order_id=?",
                        ("MAILBOX_NOT_REGISTERED", order_id),
                    )
                    player_name = str(order_player_name or "").strip() or self._resolve_player_name(str(steam_id))
                    items_text = self._format_items_for_discord(order_id)
                    self._send_shop_log_message(
                        "\n".join(
                            [
                                f"**{player_name}** : Delivery failed: Mailbox not registered.",
                                f"Order: {items_text}" if items_text else f"Order: {order_id}",
                            ]
                        ).strip()
                    )
                    return False, "MAILBOX_NOT_REGISTERED"

                res = conn.execute(
                    """
                    UPDATE shop_order
                    SET status='delivering', attempt_count=attempt_count+1, last_attempt_at=datetime('now')
                    WHERE order_id=? AND (status='pending' OR (status='failed' AND retry_requested=1))
                    """,
                    (order_id,),
                )
                if res.rowcount == 0:
                    return True, None

                items = conn.execute(
                    """
                    SELECT i.code, i.setup, i.qty,
                           COALESCE(d.qty_delivered, 0) as qty_delivered
                    FROM shop_order_item i
                    LEFT JOIN shop_delivery_item d
                      ON d.order_id = i.order_id AND d.code = i.code
                    WHERE i.order_id = ?
                    """,
                    (order_id,),
                ).fetchall()

            # Perform SCUM.db writes outside SSM transaction
            for it in items:
                code = int(it[0])
                setup = str(it[1])
                qty = int(it[2])
                qty_delivered = int(it[3] or 0)
                remaining = qty - qty_delivered
                if remaining <= 0:
                    continue

                # Verificar se é um kit
                is_kit = setup.startswith("KIT:")
                kit_items = []
                if is_kit:
                    try:
                        kit_id = setup.split(":", 1)[1]
                        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn_kit:
                            conn_kit.row_factory = sqlite3.Row
                            cur_kit = conn_kit.cursor()
                            cur_kit.execute(
                                """
                                SELECT setup, qty
                                FROM shop_kit_item
                                WHERE kit_id = ?
                                """,
                                (kit_id,),
                            )
                            rows = cur_kit.fetchall()
                            kit_items = [(str(r["setup"]), int(r["qty"])) for r in rows]
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Erro ao buscar sub-itens do kit (setup {setup}): {e}")

                if is_kit:
                    # Spawna cada item do kit no baú
                    for _ in range(remaining):
                        for sub_setup, sub_qty in kit_items:
                            spawn_res = spawner.spawn_into_chest(chest_id=chest_id, item_setup=sub_setup, qty=sub_qty)
                            if spawn_res.errors:
                                err = spawn_res.errors[0]
                                with ssm_tx(self.ssm_db_path) as conn2:
                                    conn2.execute(
                                        "UPDATE shop_order SET status='failed', error=? WHERE order_id=?",
                                        (err, order_id),
                                    )
                                return False, err
                else:
                    # Spawn normal
                    spawn_res = spawner.spawn_into_chest(chest_id=chest_id, item_setup=setup, qty=remaining)
                    if spawn_res.errors:
                        err = spawn_res.errors[0]
                        with ssm_tx(self.ssm_db_path) as conn2:
                            conn2.execute(
                                "UPDATE shop_order SET status='failed', error=? WHERE order_id=?",
                                (err, order_id),
                            )
                        return False, err

                # Update delivered qty
                with ssm_tx(self.ssm_db_path) as conn3:
                    conn3.execute(
                        """
                        INSERT INTO shop_delivery_item(order_id, code, qty_delivered, last_delivered_at)
                        VALUES(?, ?, ?, datetime('now'))
                        ON CONFLICT(order_id, code) DO UPDATE
                        SET qty_delivered = MIN(?, qty_delivered + excluded.qty_delivered),
                            last_delivered_at = datetime('now')
                        """,
                        (order_id, int(code), int(remaining), int(qty)),
                    )

            # Check completion
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn_check:
                curc = conn_check.cursor()
                curc.execute(
                    """
                    SELECT 1
                    FROM shop_order_item i
                    LEFT JOIN shop_delivery_item d
                      ON d.order_id=i.order_id AND d.code=i.code
                    WHERE i.order_id=? AND COALESCE(d.qty_delivered,0) < i.qty
                    """,
                    (order_id,),
                )
                remaining_row = curc.fetchone()
                if not remaining_row:
                    with ssm_tx(self.ssm_db_path) as conn4:
                        res = conn4.execute(
                            """
                            UPDATE shop_order
                            SET status='delivered', delivered_at=datetime('now'), retry_requested=0, error=NULL
                            WHERE order_id=? AND status != 'delivered'
                            """,
                            (order_id,),
                        )

                    if res.rowcount == 1:
                        try:
                            player_name = str(order_player_name or "").strip() or self._resolve_player_name(str(steam_id))
                            items_text = self._format_items_for_discord(order_id)
                            item_lines: List[str] = []
                            try:
                                parts = [p.strip() for p in str(items_text or "").split("|") if p.strip()]
                                item_lines = [f"- {p}" for p in parts]
                            except Exception:
                                item_lines = []
                            self._send_shop_log_message(
                                "```text\n"
                                + "\n".join(
                                    [
                                        "SYSTEM RECORD",
                                        "================================================",
                                        f"PLAYER: {player_name} | STATUS: ALIVE",
                                        "------------------------------------------------",
                                        "SENTENCE: DELIVERED",
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
                        except Exception:
                            pass
                    return True, None

            with ssm_tx(self.ssm_db_path) as conn5:
                conn5.execute(
                    "UPDATE shop_order SET status='failed', error=? WHERE order_id=?",
                    ("DELIVERY_INCOMPLETE", order_id),
                )
            try:
                with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn_meta:
                    curm = conn_meta.cursor()
                    curm.execute(
                        "SELECT steam_id FROM shop_order WHERE order_id = ?",
                        (str(order_id),),
                    )
                    rowm = curm.fetchone()
                if rowm:
                    player_name = self._resolve_player_name(str(rowm[0]))
                    items_text = self._format_items_for_discord(order_id)
                    self._send_shop_log_message(
                        "\n".join(
                            [
                                f"**{player_name}** : Delivery failed: pending items.",
                                f"Order: {items_text}" if items_text else f"Order: {order_id}",
                            ]
                        ).strip()
                    )
            except Exception:
                pass
            return False, "DELIVERY_INCOMPLETE"

        except Exception as e:
            with ssm_tx(self.ssm_db_path) as conn_err:
                conn_err.execute(
                    "UPDATE shop_order SET status='failed', error=? WHERE order_id=?",
                    (f"DELIVERY_EXCEPTION:{e}", order_id),
                )
            try:
                with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn_meta:
                    curm = conn_meta.cursor()
                    curm.execute(
                        "SELECT steam_id FROM shop_order WHERE order_id = ?",
                        (str(order_id),),
                    )
                    rowm = curm.fetchone()
                if rowm:
                    player_name = self._resolve_player_name(str(rowm[0]))
                    items_text = self._format_items_for_discord(order_id)
                    self._send_shop_log_message(
                        "\n".join(
                            [
                                f"**{player_name}** : Delivery failed: internal error.",
                                f"Order: {items_text}" if items_text else f"Order: {order_id}",
                            ]
                        ).strip()
                    )
            except Exception:
                pass
            return False, f"DELIVERY_EXCEPTION:{e}"


class ShopDeliveryWorker:
    def __init__(
        self,
        ssm_db_path: str,
        scum_db_path: str,
        logger: Optional[StructuredLogger] = None,
        poll_interval_seconds: float = 10.0,
    ):
        import threading
        self.ssm_db_path = ssm_db_path
        self.scum_db_path = scum_db_path
        self.logger = logger or StructuredLogger()
        self.poll_interval_seconds = float(poll_interval_seconds)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        import threading
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        if self.logger:
            self.logger.info("ShopDeliveryWorker iniciado.")

    def stop(self) -> None:
        self._stop_event.set()
        if self.logger:
            self.logger.info("ShopDeliveryWorker parado.")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                # Carregar RCON config para verificar se está ativo
                rcon_cfg = _load_rcon_config()
                rcon_enabled = _is_rcon_enabled(rcon_cfg)

                # Só processamos entregas em tempo real se o RCON estiver ativo
                if rcon_enabled:
                    svc = ShopDeliveryService(
                        self.ssm_db_path,
                        self.scum_db_path,
                        logger=self.logger
                    )

                    svc.run_once(limit=50)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Erro no loop do ShopDeliveryWorker: {e}")

            # Dormir usando o stop_event para desligamento rápido
            self._stop_event.wait(self.poll_interval_seconds)
