"""
SCUM Server Log Monitor

Monitora incrementalmente o arquivo:
  ...\\Saved\\Logs\\SCUM.log

Motivação:
- Esse arquivo fica fora do diretório SaveFiles\\Logs (que o LogProcessor já monitora)
- Logs do SCUM costumam estar em UTF-16LE
- Precisamos ler apenas linhas novas, lidar com truncamento (rotação) e evitar bloqueio
"""
from __future__ import annotations



import os
import threading
import time
from typing import Callable, List, Optional

from core.logs.temp_file_manager import TempFileManager
from core.logs.database_manager import DatabaseManager


class ScumServerLogMonitor:
    """
    Monitor simples (polling) para SCUM.log, com:
    - cópia pra temp antes de ler
    - leitura incremental por offset (bytes)
    - persistência do offset em log_files_processed (DatabaseManager)
    - reset automático se o arquivo for truncado
    """

    def __init__(
        self,
        scum_log_path: str,
        on_new_lines: Callable[[List[str]], None],
        db_manager: DatabaseManager,
        stop_event: threading.Event,
        poll_interval_seconds: float = 2.0,
        file_key: str = "SCUM.log",
        logger=None,
    ) -> None:
        self.scum_log_path = scum_log_path
        self.on_new_lines = on_new_lines
        self.db_manager = db_manager
        self.stop_event = stop_event
        self.poll_interval_seconds = max(0.5, float(poll_interval_seconds))
        self.file_key = file_key
        self.logger = logger

        self._thread: Optional[threading.Thread] = None
        self._temp_manager = TempFileManager("data/temp")
        self._lock = threading.Lock()

        # Carregar offset salvo (se existir)
        self._last_position = 0
        try:
            status = self.db_manager.get_file_processing_status(self.file_key)
            if status and status.get("file_path") == self.scum_log_path:
                self._last_position = int(status.get("last_position") or 0)
        except Exception:
            self._last_position = 0

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            if self.logger:
                self.logger.info(f"[CARGO_DROP] Monitor iniciando: {self.scum_log_path}")
            else:
                print(f"[CARGO_DROP] Monitor iniciando: {self.scum_log_path}")
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        # stop_event é controlado externamente pelo LogProcessor
        t = None
        with self._lock:
            t = self._thread
        if t and t.is_alive():
            t.join(timeout=timeout)

    def _persist_position(self, position: int, lines_processed: int = 0) -> None:
        try:
            self.db_manager.update_file_processing_status(
                file_name=self.file_key,
                file_path=self.scum_log_path,
                last_position=int(position),
                lines_processed=int(lines_processed),
                status="active",
            )
        except Exception:
            # Sem spam de console aqui; falha de persistência não deve derrubar o monitor
            pass

    def _read_new_lines_from_temp(self, temp_path: str, start_position: int) -> List[str]:
        """
        Lê bytes a partir de start_position e decodifica (UTF-8/UTF-16).
        Retorna linhas não vazias.
        """
        try:
            with open(temp_path, "rb") as f:
                f.seek(max(0, int(start_position)))
                data = f.read()
        except Exception:
            return []

        if not data:
            return []

        try:
            text = self._decode_bytes(data)
        except Exception:
            return []

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return lines

    @staticmethod
    def _decode_bytes(data: bytes) -> str:
        """
        Detecta encoding mais comum dos logs do SCUM:
        - UTF-8 com BOM (utf-8-sig)
        - UTF-16 com BOM
        - UTF-16LE (sem BOM)
        Fallback: UTF-8.
        """
        if not data:
            return ""

        # UTF-8 BOM
        if data.startswith(b"\xef\xbb\xbf"):
            return data.decode("utf-8-sig", errors="ignore")

        # UTF-16 BOMs
        if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
            return data.decode("utf-16", errors="ignore")

        # Heurística: muitos NULs sugere UTF-16 (LE na prática)
        sample = data[:512]
        if sample and (sample.count(b"\x00") / max(1, len(sample))) > 0.10:
            # garantir par de bytes
            if len(data) % 2 == 1:
                data = data[:-1]
            return data.decode("utf-16le", errors="ignore")

        # Padrão moderno: UTF-8 (sem BOM)
        return data.decode("utf-8", errors="ignore")

    def _loop(self) -> None:
        # Inicializar registro na tabela, se ainda não existir
        self._persist_position(self._last_position, lines_processed=0)

        while not self.stop_event.is_set():
            try:
                if not os.path.exists(self.scum_log_path):
                    time.sleep(self.poll_interval_seconds)
                    continue

                current_size = os.path.getsize(self.scum_log_path)
                if current_size < self._last_position:
                    # Arquivo foi truncado/rotacionado -> reset
                    self._last_position = 0
                    self._persist_position(self._last_position, lines_processed=0)

                if current_size <= self._last_position:
                    time.sleep(self.poll_interval_seconds)
                    continue

                temp_path = self._temp_manager.create_temp_copy(self.scum_log_path)
                if not temp_path:
                    time.sleep(self.poll_interval_seconds)
                    continue

                try:
                    # Recalcular tamanho da cópia (pode ser menor se foi copiado no meio)
                    temp_size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                    start_pos = min(self._last_position, temp_size)
                    new_lines = self._read_new_lines_from_temp(temp_path, start_pos)
                finally:
                    self._temp_manager.cleanup_temp_file(temp_path)

                # Atualizar posição para o tamanho do arquivo original (bytes)
                self._last_position = current_size
                self._persist_position(self._last_position, lines_processed=0)

                if new_lines:
                    self.on_new_lines(new_lines)

            except Exception:
                # Evitar travar monitor por erro inesperado
                pass

            time.sleep(self.poll_interval_seconds)

