"""
Cargo Drop Notifier - Envia notificações de spawn de Cargo Drop para Discord

Detecta eventos do tipo:
  LogTemp: Cargo drop spawned at: X, Y, Z

E envia um embed com coordenadas + link do SCUM Map.
"""
from __future__ import annotations



import os
import re
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests


_CARGO_DROP_RE = re.compile(
    # Exemplos que já apareceram em logs do SCUM (varia por versão):
    # - "Cargo drop spawned at: X, Y, Z"
    # - "Cargo Drop spawned at X Y Z"
    r"Cargo\s+drop\s+spawned\s+at:?\s*([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)",
    re.IGNORECASE,
)

# Ex: [2026.01.18-23.46.38:005][756]LogTemp: ...
_LOG_TS_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):(\d{3})\]"
)


@dataclass(frozen=True)
class CargoDropEvent:
    timestamp: Optional[datetime]
    x: float
    y: float
    z: float
    raw_line: str


class CargoDropNotifier:
    """
    Notificador simples via webhook Discord (data/webhooks.json).
    Mantém consistência com outros notifiers em core/logs (VehicleNotifier/MinigameNotifier).
    """

    def __init__(
        self,
        webhook_config: Dict[str, str] | None = None,
        state_path: str = "data/cargo_drop_state.json",
        cargo_drop_selfdestruct_seconds: Optional[float] = None,
    ) -> None:
        self.webhook_url = (webhook_config or {}).get("cargo_drop") if webhook_config else None
        self.state_path = state_path
        self._last_sent_signature: Optional[str] = self._load_last_sent_signature()
        self.last_http_status: Optional[int] = None
        self.last_http_error: Optional[str] = None
        # Defaults do SCUM (segundos): 1200s = 20min
        self.cargo_drop_selfdestruct_seconds: float = float(
            cargo_drop_selfdestruct_seconds
            if cargo_drop_selfdestruct_seconds is not None
            else 1200.0
        )

        if not self.webhook_url or not str(self.webhook_url).strip():
            # Não é erro: permite rodar sem webhook configurado
            self.webhook_url = None

    @staticmethod
    def _world_xy_to_quadrant(
        x: float,
        y: float,
        *,
        min_x: float = -900000.0,
        max_x: float = 625000.0,
        min_y: float = -900000.0,
        max_y: float = 610000.0,
        grid_size: int = 5,
    ) -> Optional[str]:
        """Converter coordenadas do mundo (SCUM Map) em quadrante (ex: A1, C3, Z4).

        Observacao:
        - Esses bounds padrao foram calibrados para bater com o grid do scum-map.com
          (5x5: Z/A/B/C/D e 0..4). Se o seu servidor/mapa usar outro range, ajuste.
        - Se o seu servidor/mapa usar outro range, ajuste os limites.
        """
        try:
            xf = float(x)
            yf = float(y)
        except Exception:
            return None

        if grid_size <= 0:
            return None

        # Fora do range -> nao rotular
        if xf < min_x or xf > max_x or yf < min_y or yf > max_y:
            return None

        width = max_x - min_x
        height = max_y - min_y
        if width <= 0 or height <= 0:
            return None

        cell_w = width / float(grid_size)
        cell_h = height / float(grid_size)

        # No grid do SCUM, os numeros (0..4) aparecem da direita para esquerda.
        # Para isso, invertimos o X ao calcular a coluna "da esquerda".
        col_from_left = int(math.floor((max_x - xf) / cell_w))
        row_from_bottom = int(math.floor((yf - min_y) / cell_h))

        col_from_left = max(0, min(grid_size - 1, col_from_left))
        row_from_bottom = max(0, min(grid_size - 1, row_from_bottom))

        # Mapeamento vertical (de baixo para cima): Z, A, B, C, D
        letters = ["Z", "A", "B", "C", "D"]
        if grid_size != 5:
            # fallback para qualquer tamanho: usa A..Z
            letters = [chr(ord("A") + i) for i in range(grid_size)]

        letter = letters[row_from_bottom] if row_from_bottom < len(letters) else None
        if not letter:
            return None

        number = (grid_size - 1) - col_from_left
        return f"{letter}{number}"
    
    def _load_last_sent_signature(self) -> Optional[str]:
        try:
            if not self.state_path or not os.path.exists(self.state_path):
                return None
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            sig = data.get("last_sent_signature")
            return str(sig) if sig else None
        except Exception:
            return None

    def _save_last_sent_signature(self, signature: str) -> None:
        try:
            os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump({"last_sent_signature": signature}, f, ensure_ascii=False, indent=2)
        except Exception:
            # Não travar por falha de IO
            pass

    @staticmethod
    def _event_signature(event: CargoDropEvent) -> str:
        """
        Assinatura estável para deduplicar (timestamp+coords se possível; senão linha crua).
        """
        if event.timestamp:
            ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")
            return f"{ts}|{event.x:.4f}|{event.y:.4f}|{event.z:.4f}"
        return event.raw_line.strip()

    def should_send(self, event: CargoDropEvent) -> bool:
        sig = self._event_signature(event)
        return sig and sig != self._last_sent_signature

    @staticmethod
    def parse_cargo_drop_event(line: str) -> Optional[CargoDropEvent]:
        if not line:
            return None

        m = _CARGO_DROP_RE.search(line)
        if not m:
            return None

        try:
            x = float(m.group(1))
            y = float(m.group(2))
            z = float(m.group(3))
        except Exception:
            return None

        ts = None
        ts_m = _LOG_TS_RE.search(line)
        if ts_m:
            try:
                date_part = ts_m.group(1)  # 2026.01.18
                time_part = ts_m.group(2).replace(".", ":")  # 23:46:38
                ms_part = ts_m.group(3)  # 005
                ts = datetime.strptime(
                    f"{date_part} {time_part}.{ms_part}", "%Y.%m.%d %H:%M:%S.%f"
                )
            except Exception:
                ts = None

        return CargoDropEvent(timestamp=ts, x=x, y=y, z=z, raw_line=line)

    @staticmethod
    def _get_scum_map_link(x: float, y: float, zoom: int = 4) -> str:
        return f"https://scum-map.com/en/shared/scum/island/{x:.4f},{y:.4f},{zoom}"

    @staticmethod
    def _format_time_ptbr(ts: Optional[datetime]) -> str:
        if not ts:
            return "desconhecido"
        # Exibir só dia/mês + hora:min:seg
        return ts.strftime("%d/%m %H:%M:%S")

    @staticmethod
    def _format_duration_ptbr(seconds: float) -> str:
        try:
            total = max(0, int(round(float(seconds))))
        except Exception:
            total = 0
        mm = total // 60
        ss = total % 60
        return f"{mm:02d}m {ss:02d}s"

    def send(self, event: CargoDropEvent) -> bool:
        # Reset do estado da última tentativa
        self.last_http_status = None
        self.last_http_error = None

        if not self.webhook_url:
            return False
        if not self.should_send(event):
            return False

        try:
            map_link = self._get_scum_map_link(event.x, event.y, zoom=4)
            quadrant = self._world_xy_to_quadrant(event.x, event.y)

            embed = {
                "title": "📦 Cargo Drop Spawned",
                "color": 0xF1C40F,  # yellow
                "fields": [
                    {
                        "name": "Quadrant",
                        "value": quadrant or "N/A",
                        "inline": True,
                    },
                    {"name": "Map", "value": f"[Open in SCUM Map]({map_link})", "inline": False},
                ],
                "footer": {"text": "SCUM Server Manager • Cargo Drop"},
            }

            # Thumbnail (miniatura) via attachment
            # Discord: usar "attachment://<filename>" + multipart com payload_json + files
            # __file__ = .../Backend/core/logs/cargo_drop_notifier.py
            backend_dir = Path(__file__).resolve().parents[2]  # .../Backend
            thumb_path = backend_dir / "data" / "imagens" / "Drop" / "Cargo_Drop.webp"

            if thumb_path.exists():
                # Thumbnail aparece do lado direito no embed
                embed["thumbnail"] = {"url": "attachment://Cargo_Drop.webp"}
                payload: Dict[str, Any] = {"embeds": [embed]}
                data = {"payload_json": json.dumps(payload, ensure_ascii=False)}
                with thumb_path.open("rb") as f:
                    # Discord espera "files[0]" para attachments
                    files = {"files[0]": ("Cargo_Drop.webp", f, "image/webp")}
                    resp = requests.post(
                        self.webhook_url, data=data, files=files, timeout=10
                    )
            else:
                payload = {"embeds": [embed]}
                resp = requests.post(self.webhook_url, json=payload, timeout=10)

            self.last_http_status = int(getattr(resp, "status_code", 0) or 0)
            ok = self.last_http_status in (200, 204)
            if ok:
                sig = self._event_signature(event)
                self._last_sent_signature = sig
                self._save_last_sent_signature(sig)
            else:
                try:
                    # Evitar logs gigantes / dados sensíveis
                    txt = (resp.text or "").strip()
                    self.last_http_error = txt[:300] if txt else None
                except Exception:
                    self.last_http_error = None
            return ok
        except Exception:
            self.last_http_error = "exception"
            return False

