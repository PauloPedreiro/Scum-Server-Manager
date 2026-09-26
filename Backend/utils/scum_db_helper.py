"""
Helper para conexões read-only ao SCUM.db
Garante que não sejam criados arquivos WAL/SHM quando fazemos apenas leituras
Funciona mesmo quando o servidor SCUM está rodando

Agora suporta cópia compartilhada para melhor performance e menor carga no disco.
"""

import sqlite3
import os
import time
from typing import Optional
from contextlib import contextmanager


@contextmanager
def scum_db_readonly_connection(
    db_path: str,
    max_retries: int = 3,
    retry_delay: float = 0.5,
    use_shared_copy: bool = True,
):
    """
    Context manager para conexão read-only ao SCUM.db.

    Funciona mesmo quando o servidor SCUM está rodando, usando:
    - Modo read-uncommitted para permitir leituras durante escritas
    - Retry logic para lidar com bloqueios temporários
    - Timeout aumentado para aguardar liberação do banco
    - Cópia compartilhada (quando habilitada) para melhor performance

    Garante que:
    - A conexão seja apenas leitura (não cria WAL/SHM quando possível)
    - Funcione mesmo com servidor SCUM rodando
    - Não haja escritas acidentais

    Args:
        db_path: Caminho para o arquivo SCUM.db
        max_retries: Número máximo de tentativas em caso de bloqueio (padrão: 3)
        retry_delay: Delay entre tentativas em segundos (padrão: 0.5)
        use_shared_copy: Se True, tenta usar cópia compartilhada (padrão: True)

    Yields:
        sqlite3.Connection: Conexão read-only configurada

    Example:
        with scum_db_readonly_connection("/path/to/SCUM.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
    """
    # SEMPRE usar cópia compartilhada - sem fallback para conexão direta
    if not use_shared_copy:
        raise RuntimeError(
            "use_shared_copy deve ser True. Conexão direta ao SCUM.db não é permitida."
        )

    try:
        from utils.restart_guard import should_block_scum_db_access

        if should_block_scum_db_access(
            component="scum_db_readonly_connection",
            operation="connect",
            scum_db_path=db_path,
        ):
            try:
                from utils.logger import StructuredLogger
                StructuredLogger().warn(
                    f"[SCUM_DB] Conexão read-only bloqueada pelo Restart Guard para o banco: {db_path}"
                )
            except Exception:
                pass
            raise sqlite3.OperationalError("database is locked (Restart Guard active)")
    except sqlite3.OperationalError:
        raise
    except Exception:
        pass

    try:
        from utils.scum_db_shared_copy import get_shared_copy_manager
        manager = get_shared_copy_manager()

        # Se o manager não está habilitado, lançar erro
        if not manager.enabled:
            raise RuntimeError(
                "ScumDbSharedCopyManager não está habilitado. "
                "Configure 'scum_db_shared_copy.enabled = true' no config.json"
            )

        # Usar cópia compartilhada (única opção permitida)
        with manager.get_copy_connection(scum_db_path=db_path) as conn:
            yield conn
            return

    except RuntimeError:
        # Re-lançar RuntimeError (erros de configuração)
        raise
    except Exception as e:
        # Qualquer outro erro ao usar cópia compartilhada deve ser propagado
        raise RuntimeError(
            f"Falha ao usar cópia compartilhada do SCUM.db: {e}. "
            "Verifique se o ScumDbSharedCopyManager está configurado corretamente."
        ) from e


@contextmanager
def scum_db_readonly_connection_strict(
    db_path: str, max_retries: int = 3, retry_delay: float = 0.5
):
    """
    Context manager para conexão read-only ABSOLUTA ao SCUM.db.

    Esta função garante que NENHUM arquivo WAL/SHM seja criado ou modificado.
    Ideal para serviços que precisam de dados frescos sem overhead de cópia compartilhada.

    Funciona mesmo quando o servidor SCUM está rodando, usando:
    - URI mode read-only (file:path?mode=ro) que impede criação de arquivos auxiliares
    - Modo read-uncommitted para permitir leituras durante escritas
    - Retry logic para lidar com bloqueios temporários
    - NUNCA tenta modificar journal_mode (evita locks e criação de arquivos)

    Garante que:
    - Conexão seja read-only absoluta (não cria WAL/SHM)
    - Funcione mesmo com servidor SCUM rodando
    - Leia dados frescos diretamente do banco
    - Não haja escritas acidentais

    Args:
        db_path: Caminho para o arquivo SCUM.db
        max_retries: Número máximo de tentativas em caso de bloqueio (padrão: 3)
        retry_delay: Delay entre tentativas em segundos (padrão: 0.5)

    Yields:
        sqlite3.Connection: Conexão read-only configurada

    Example:
        with scum_db_readonly_connection_strict("/path/to/SCUM.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SCUM.db não encontrado: {db_path}")

    conn = None
    last_error = None

    try:
        from utils.restart_guard import should_block_scum_db_access

        if should_block_scum_db_access(
            component="scum_db_readonly_connection_strict",
            operation="connect",
            scum_db_path=db_path,
        ):
            try:
                from utils.logger import StructuredLogger
                StructuredLogger().warn(
                    f"[SCUM_DB] Conexão read-only strict bloqueada pelo Restart Guard para o banco: {db_path}"
                )
            except Exception:
                pass
            raise sqlite3.OperationalError("database is locked (Restart Guard active)")
    except sqlite3.OperationalError:
        raise
    except Exception:
        pass

    try:
        # Tentar múltiplas vezes em caso de bloqueio
        for attempt in range(max_retries):
            try:
                # PRIORIDADE 1: Tentar URI mode read-only (não cria arquivos WAL/SHM)
                # O modo 'ro' (read-only) do SQLite garante que nenhum arquivo auxiliar seja criado
                uri = f"file:{db_path}?mode=ro"
                try:
                    conn = sqlite3.connect(uri, uri=True, timeout=10.0)

                    # Configurar read-uncommitted para ler mesmo durante escritas do servidor
                    # Isso permite ler do WAL existente sem precisar criar novos arquivos
                    try:
                        conn.execute("PRAGMA read_uncommitted=1")
                    except:
                        # Se read_uncommitted não estiver disponível, continuar mesmo assim
                        pass

                    # NÃO tentar mudar journal_mode - conexão read-only não pode fazer isso
                    # e não é necessário, pois não criaremos arquivos WAL/SHM novos

                    yield conn
                    return  # Sucesso, sair do loop

                except sqlite3.OperationalError as uri_error:
                    # URI mode pode falhar se banco estiver muito bloqueado
                    # Tentar fallback com conexão normal read-only
                    error_msg = str(uri_error).lower()

                    if conn:
                        try:
                            conn.close()
                        except:
                            pass
                        conn = None

                    # Se não é erro de bloqueio, tentar fallback
                    if "locked" not in error_msg and "busy" not in error_msg:
                        # Pode ser que URI mode não seja suportado, tentar conexão normal
                        # mas sem tentar mudar journal_mode
                        try:
                            conn = sqlite3.connect(db_path, timeout=10.0)
                            try:
                                conn.execute("PRAGMA read_uncommitted=1")
                            except:
                                pass
                            # NÃO tentar mudar journal_mode - apenas ler
                            yield conn
                            return
                        except:
                            pass

                    # Se foi erro de bloqueio, continuar para retry
                    last_error = uri_error

            except sqlite3.OperationalError as e:
                last_error = e
                error_msg = str(e).lower()

                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                    conn = None

                # Se não é a última tentativa, aguardar e tentar novamente
                if attempt < max_retries - 1:
                    if "locked" in error_msg or "busy" in error_msg:
                        time.sleep(retry_delay * (attempt + 1))  # Backoff exponencial
                else:
                    # Última tentativa falhou
                    # Tentar uma última vez com timeout maior
                    if "locked" in error_msg or "busy" in error_msg:
                        try:
                            # Última tentativa com URI mode e timeout maior
                            uri = f"file:{db_path}?mode=ro"
                            conn = sqlite3.connect(uri, uri=True, timeout=30.0)
                            try:
                                conn.execute("PRAGMA read_uncommitted=1")
                            except:
                                pass
                            yield conn
                            return
                        except:
                            pass

                    # Se chegou aqui, realmente falhou
                    raise sqlite3.OperationalError(
                        f"Falha ao conectar ao SCUM.db (read-only strict) após {max_retries} tentativas: {last_error}"
                    )

            except Exception as e:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                    conn = None
                raise

    finally:
        # Garantir que conexão seja sempre fechada
        if conn:
            try:
                conn.close()
            except:
                pass


def get_scum_db_readonly_connection(db_path: str) -> sqlite3.Connection:
    """
    Obter conexão read-only ao SCUM.db (sem context manager).

    ATENÇÃO: Você deve fechar a conexão manualmente!
    Prefira usar scum_db_readonly_connection() com context manager.

    Args:
        db_path: Caminho para o arquivo SCUM.db

    Returns:
        sqlite3.Connection: Conexão read-only configurada
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SCUM.db não encontrado: {db_path}")

    try:
        from utils.restart_guard import should_block_scum_db_access

        if should_block_scum_db_access(
            component="get_scum_db_readonly_connection",
            operation="connect",
            scum_db_path=db_path,
        ):
            try:
                from utils.logger import StructuredLogger
                StructuredLogger().warn(
                    f"[SCUM_DB] Conexão direta read-only bloqueada pelo Restart Guard para o banco: {db_path}"
                )
            except Exception:
                pass
            raise sqlite3.OperationalError("database is locked (Restart Guard active)")
    except sqlite3.OperationalError:
        raise
    except Exception:
        pass

    # Tentar modo read-only primeiro
    uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA read_uncommitted=1")
        return conn
    except sqlite3.OperationalError:
        # Fallback para modo normal, mas sem WAL
        conn = sqlite3.connect(db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=DELETE")
        return conn
