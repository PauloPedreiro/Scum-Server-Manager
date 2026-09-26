"""
Helper utilities for SSM.db operations
"""

from core.database.connector import DatabaseConnector
import os
import sqlite3
from typing import Optional
from utils.logger import StructuredLogger


def cleanup_ssm_db_journal(
    ssm_db_path: str, logger: Optional[StructuredLogger] = None
) -> bool:
    """
    Limpar arquivo journal órfão do SSM.db se existir.

    Um arquivo journal indica que há uma transação não finalizada.
    Se o processo foi interrompido durante uma transação, o journal
    pode permanecer e causar bloqueios.

    Args:
        ssm_db_path: Caminho para o arquivo SSM.db
        logger: Logger opcional para registrar operações

    Returns:
        True se journal foi limpo ou não existia, False se houve erro
    """

    def log(message: str, level: str = "info"):
        """Helper para logging"""
        if logger:
            if hasattr(logger, level):
                getattr(logger, level)(message)
            elif hasattr(logger, "info"):
                logger.info(message)

    journal_path = f"{ssm_db_path}-journal"

    if not os.path.exists(journal_path):
        # Sem journal, nada a fazer
        return True

    try:
        # Tentar abrir o banco com o conector central
        with DatabaseConnector.get_connection(ssm_db_path, timeout=10.0, write_mode=True) as conn:
            # Tentar fazer rollback explícito para finalizar transação pendente
            try:
                conn.rollback()
            except:
                pass

            # Agora tentar remover o journal
            if os.path.exists(journal_path):
                os.remove(journal_path)
                log(f"Arquivo journal órfão removido: {journal_path}", "info")
                return True
    except sqlite3.OperationalError as e:
        # Banco está bloqueado, não podemos limpar agora
        log(f"Banco bloqueado, não é possível limpar journal agora: {e}", "warn")
        return False
    except Exception as e:
        log(f"Erro ao tentar limpar journal: {e}", "error")
        return False

    return True


def ensure_ssm_db_clean_state(
    ssm_db_path: str, logger: Optional[StructuredLogger] = None
) -> bool:
    """
    Garantir que o SSM.db está em estado limpo antes de iniciar operações.

    Tenta limpar journals órfãos e verificar se o banco está acessível.

    Args:
        ssm_db_path: Caminho para o arquivo SSM.db
        logger: Logger opcional para registrar operações

    Returns:
        True se banco está acessível, False caso contrário
    """

    def log(message: str, level: str = "info"):
        """Helper para logging"""
        if logger:
            if hasattr(logger, level):
                getattr(logger, level)(message)
            elif hasattr(logger, "info"):
                logger.info(message)

    # Tentar limpar journal
    cleanup_ssm_db_journal(ssm_db_path, logger)

    # Verificar se banco está acessível
    try:
        with DatabaseConnector.get_connection(ssm_db_path, timeout=10.0, write_mode=False) as conn:
            pass
        return True
    except Exception as e:
        log(f"Banco SSM.db não está acessível: {e}", "error")
        return False
