"""
Fila serializada de escritas SQLite para gerenciar concorrência de I/O.
Extraído do main.py durante refatoração modular.

Uso:
    from utils.sqlite_queue import submit_sqlite_write, ensure_sqlite_wal

    # Habilitar WAL mode para um banco
    ensure_sqlite_wal("/path/to/SSM.db")

    # Submeter uma operação de escrita serializada
    def my_write():
        with DatabaseConnector.get_connection(db_path, timeout=30.0, write_mode=True) as conn:
            conn.execute("INSERT INTO ...")
            conn.commit()
    result = submit_sqlite_write(my_write)
"""
from core.database.connector import DatabaseConnector

import sqlite3
import threading
import time
import queue
from typing import Optional


_SQLITE_WAL_ENABLED_FOR: set[str] = set()
_SQLITE_WAL_LOCK = threading.Lock()


def ensure_sqlite_wal(ssm_db_path: str) -> None:
    """
    Habilitar WAL mode para um banco SQLite (idempotente).
    Garante que cada banco só seja configurado uma vez.
    """
    if not ssm_db_path:
        return
    with _SQLITE_WAL_LOCK:
        if ssm_db_path in _SQLITE_WAL_ENABLED_FOR:
            return
        with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.commit()
        _SQLITE_WAL_ENABLED_FOR.add(ssm_db_path)


import logging
logger = logging.getLogger("scum_backend.sqlite_queue")


class SQLiteWriteQueue:
    """
    Fila serializada para escritas SQLite.
    Garante que apenas uma escrita ocorra por vez, evitando
    'database is locked' em cenários de alta concorrência.
    """

    def __init__(self) -> None:
        self._q: "queue.Queue[tuple[callable, queue.Queue]]" = queue.Queue(maxsize=500)
        self._worker = threading.Thread(target=self._run, name="sqlite-write-queue", daemon=True)
        logger.info("[SQLiteWriteQueue] Inicializando worker thread 'sqlite-write-queue'...")
        self._worker.start()

    def _run(self) -> None:
        logger.info("[SQLiteWriteQueue] Worker thread 'sqlite-write-queue' iniciada com sucesso.")
        while True:
            try:
                fn, result_q = self._q.get()
                logger.info(f"[SQLiteWriteQueue] Nova tarefa de escrita recebida. Itens pendentes na fila: {self._q.qsize()}")
                try:
                    start_time = time.perf_counter()
                    res = self._run_with_retry(fn)
                    duration = time.perf_counter() - start_time
                    logger.info(f"[SQLiteWriteQueue] Tarefa de escrita executada com sucesso em {duration:.4f}s.")
                    result_q.put((True, res))
                except BaseException as e:
                    logger.error(f"[SQLiteWriteQueue] Erro ao executar tarefa: {e}", exc_info=True)
                    result_q.put((False, e))
                finally:
                    try:
                        self._q.task_done()
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"[SQLiteWriteQueue] Erro crítico no loop do worker: {e}", exc_info=True)
                time.sleep(0.5)

    def _run_with_retry(self, fn):
        max_attempts = 6
        base_sleep = 0.075
        for attempt in range(max_attempts):
            try:
                return fn()
            except sqlite3.OperationalError as oe:
                msg = str(oe or "").lower()
                if "database is locked" not in msg and "database locked" not in msg:
                    raise
                logger.warning(
                    f"[SQLiteWriteQueue] Banco de dados travado. Tentativa {attempt + 1}/{max_attempts} de escrita em {base_sleep * (2**attempt):.3f}s..."
                )
                if attempt >= max_attempts - 1:
                    raise
                time.sleep(base_sleep * (2**attempt))

    def submit(self, fn, timeout_seconds: float = 20.0):
        """
        Submeter uma função de escrita para execução serializada.

        Args:
            fn: Callable sem argumentos que executa a escrita
            timeout_seconds: Timeout para aguardar o resultado

        Returns:
            Resultado da função fn

        Raises:
            Exception propagada da função fn se houve erro
        """
        result_q: "queue.Queue[tuple[bool, object]]" = queue.Queue(maxsize=1)
        logger.info(f"[SQLiteWriteQueue.submit] Submetendo tarefa de escrita à fila (timeout={timeout_seconds}s)")
        try:
            self._q.put((fn, result_q), timeout=5.0)
        except queue.Full:
            logger.error("[SQLiteWriteQueue.submit] A fila de escritas SQLite está CHEIA (limite 500)!")
            raise RuntimeError("Fila de escritas SQLite cheia")

        try:
            ok, payload = result_q.get(timeout=timeout_seconds)
            logger.info(f"[SQLiteWriteQueue.submit] Resposta recebida da fila. Sucesso={ok}")
            if ok:
                return payload
            raise payload
        except queue.Empty:
            logger.error(f"[SQLiteWriteQueue.submit] TIMEOUT de {timeout_seconds}s aguardando execução da escrita SQLite pela fila!")
            raise



# Singleton global da fila de escrita
_SQLITE_WRITE_QUEUE: Optional[SQLiteWriteQueue] = None
_SQLITE_WRITE_QUEUE_LOCK = threading.Lock()


def submit_sqlite_write(fn, timeout_seconds: float = 20.0):
    """
    Submeter uma operação de escrita SQLite para a fila serializada global.
    Inicializa a fila lazy se necessário.

    Args:
        fn: Callable sem argumentos que executa a escrita
        timeout_seconds: Timeout para aguardar o resultado

    Returns:
        Resultado da função fn
    """
    global _SQLITE_WRITE_QUEUE
    if _SQLITE_WRITE_QUEUE is None:
        with _SQLITE_WRITE_QUEUE_LOCK:
            if _SQLITE_WRITE_QUEUE is None:
                _SQLITE_WRITE_QUEUE = SQLiteWriteQueue()
    return _SQLITE_WRITE_QUEUE.submit(fn, timeout_seconds=timeout_seconds)
