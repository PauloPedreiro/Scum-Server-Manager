import sqlite3
import time
import logging
import os
import threading
from typing import Optional, ContextManager
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseConnector:
    """
    Gerenciador unificado de conexões SQLite.
    Garante que as configurações corretas de concorrência (WAL) e timeouts longos
    sejam aplicadas uniformemente em toda a aplicação.
    """
    _write_lock = threading.RLock()
    
    @staticmethod
    @contextmanager
    def get_connection(db_path: str, timeout: float = 30.0, max_retries: int = 10, write_mode: bool = False) -> ContextManager[sqlite3.Connection]:
        """
        Fornece uma conexão segura com o SQLite utilizando o modo WAL.
        
        Args:
            db_path: Caminho do arquivo .db
            timeout: Tempo de espera para obter o lock de gravação
            max_retries: Quantidade de tentativas em caso de erro 'database is locked'
            write_mode: Se True, inicia a transação com BEGIN IMMEDIATE para garantir o lock de escrita
            
        Yields:
            sqlite3.Connection
        """
        if write_mode:
            DatabaseConnector._write_lock.acquire()
            
        conn = None
        retry_delay = 0.2
        
        try:
            for attempt in range(max_retries):
                try:
                    # Criar diretório se não existir
                    db_dir = os.path.dirname(db_path)
                    if db_dir and not os.path.exists(db_dir):
                        os.makedirs(db_dir, exist_ok=True)

                    conn = sqlite3.connect(db_path, timeout=timeout)
                    conn.isolation_level = None
                    conn.row_factory = sqlite3.Row
                    
                    # Configurações de performance e concorrência
                    conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)}")
                    conn.execute("PRAGMA synchronous = NORMAL")
                    
                    # Definir WAL - Importante fazer fora da transação
                    try:
                        # Verificar modo atual primeiro para evitar lock desnecessário
                        cursor = conn.execute("PRAGMA journal_mode")
                        current_mode = cursor.fetchone()[0]
                        if current_mode.lower() != 'wal':
                            conn.execute("PRAGMA journal_mode = WAL")
                    except Exception:
                        pass
                    
                    # Iniciar transação baseada no modo
                    if write_mode:
                        # BEGIN IMMEDIATE previne deadlocks ao sinalizar intenção de escrita logo no início
                        conn.execute("BEGIN IMMEDIATE")
                    else:
                        # BEGIN DEFERRED é seguro para leituras e permite maior concorrência
                        conn.execute("BEGIN DEFERRED")
                        
                    # Sucesso ao estabelecer conexão e iniciar transação
                    break

                except sqlite3.OperationalError as e:
                    if conn:
                        try: conn.close()
                        except: pass
                    
                    error_msg = str(e).lower()
                    if "database is locked" in error_msg and attempt < max_retries - 1:
                        logger.warning(f"Banco '{db_path}' ocupado. Tentando lock {attempt + 1}/{max_retries} em {retry_delay:.1f}s...")
                        time.sleep(retry_delay)
                        # Backoff exponencial suave
                        retry_delay = min(retry_delay * 1.5, 2.0)
                        continue
                    raise e
                except Exception as e:
                    if conn:
                        try: conn.close()
                        except: pass
                    raise e
            
            yield conn
            
            # Commit automático se estiver em transação e não houver erro
            if conn and hasattr(conn, 'in_transaction') and conn.in_transaction:
                conn.commit()
        except Exception as e:
            try:
                if conn and hasattr(conn, 'in_transaction') and conn.in_transaction:
                    conn.rollback()
            except:
                pass
            raise e
        finally:
            try:
                if conn:
                    conn.close()
            except:
                pass
            if write_mode:
                DatabaseConnector._write_lock.release()


# Instância global opcional, mas os métodos estáticos já são suficientes
get_connection = DatabaseConnector.get_connection

