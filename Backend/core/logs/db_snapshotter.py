import os
import threading
import time
import sqlite3
from typing import Optional
import tempfile


class DBSnapshotter:
    def __init__(
        self,
        source_db_path: str,
        public_db_path: str,
        interval_seconds: int = 30,
        logger=None,
    ):
        self.source_db_path = source_db_path
        self.public_db_path = public_db_path
        self.interval_seconds = interval_seconds
        self.logger = logger

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def snapshot_once(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.public_db_path) or ".", exist_ok=True)

            tmp_path = None
            try:
                fd, tmp_path = tempfile.mkstemp(
                    prefix=os.path.basename(self.public_db_path) + ".",
                    suffix=".tmp",
                    dir=os.path.dirname(self.public_db_path) or None,
                )
                os.close(fd)
            except Exception:
                tmp_path = None

            target_path = tmp_path or self.public_db_path

            from core.database.connector import DatabaseConnector
            with DatabaseConnector.get_connection(self.source_db_path, timeout=30.0, write_mode=False) as src:
                dst = sqlite3.connect(target_path, timeout=30.0)
                try:
                    dst.execute("PRAGMA busy_timeout = 30000")
                    src.backup(dst)
                    dst.commit()
                finally:
                    dst.close()

            if tmp_path:
                try:
                    try:
                        os.chmod(self.public_db_path, 0o666)
                    except Exception:
                        pass
                    os.replace(tmp_path, self.public_db_path)
                finally:
                    try:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except Exception:
                        pass

            return True
        except Exception as e:
            if self.logger:
                try:
                    self.logger.warn(f"Falha ao gerar snapshot público do DB: {e}")
                except Exception:
                    pass
            return False

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.snapshot_once()
            for _ in range(self.interval_seconds):
                if self._stop_event.is_set():
                    return
                time.sleep(1)
