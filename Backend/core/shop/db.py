import sqlite3
from contextlib import contextmanager
from typing import Iterator
from core.database.connector import DatabaseConnector


@contextmanager
def ssm_tx(db_path: str, timeout: float = 30.0) -> Iterator[sqlite3.Connection]:
    with DatabaseConnector.get_connection(db_path, timeout=timeout, write_mode=True) as conn:
        yield conn
