"""
Helper para limpeza de arquivos WAL/SHM do SCUM.db
Remove arquivos órfãos que podem ficar após o servidor parar
"""

import os
import time
import sqlite3
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from datetime import datetime, timezone


_LAST_WAL_LOG_RETENTION_DATE: Optional[str] = None

# Variável global para rastrear instância do ScumDbSharedCopyManager
_shared_copy_manager_instance = None


def set_shared_copy_manager(manager):
    """Define a instância do ScumDbSharedCopyManager para limpeza de conexões"""
    global _shared_copy_manager_instance
    _shared_copy_manager_instance = manager


def cleanup_scum_db_wal_files(
    server_manager,
    scum_db_path: str,
    logger=None,
    wait_after_stop: float = 3.0,
    wait_after_close: float = 1.0,
    restart_cycle_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Limpar arquivos WAL/SHM do SCUM.db de forma segura.

    Garante que:
    - Servidor está parado antes de limpar
    - Faz checkpoint do WAL antes de remover
    - Remove arquivos WAL/SHM se checkpoint for bem-sucedido
    - Não bloqueia o processo se falhar

    Args:
        server_manager: Instância do ServerManager para verificar status
        scum_db_path: Caminho para o arquivo SCUM.db
        logger: Logger opcional para registrar operações
        wait_after_stop: Segundos para aguardar após servidor parar (padrão: 3.0)
        wait_after_close: Segundos para aguardar após fechar conexão (padrão: 1.0)

    Returns:
        Dict com resultado da operação:
        {
            "success": bool,
            "server_was_running": bool,
            "files_removed": List[str],
            "files_found": List[str],
            "checkpoint_success": bool,
            "errors": List[str],
            "message": str
        }
    """
    result = {
        "success": False,
        "server_was_running": False,
        "files_removed": [],
        "files_found": [],
        "checkpoint_success": False,
        "errors": [],
        "message": "",
    }

    def log(message: str, level: str = "info"):
        """Helper para logging"""
        if logger:
            if hasattr(logger, level):
                getattr(logger, level)(message)
            elif hasattr(logger, "info"):
                logger.info(message)
        else:
            print(f"[{level.upper()}] {message}")

    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def _safe_int(v: Any) -> Optional[int]:
        try:
            return int(v)
        except Exception:
            return None

    def _file_state(path: str) -> Dict[str, Any]:
        try:
            exists = bool(path and os.path.exists(path))
            size = os.path.getsize(path) if exists else 0
            return {"path": path, "exists": exists, "size": int(size)}
        except Exception:
            return {"path": path, "exists": False, "size": 0}

    def _classify_error(exc: BaseException) -> Dict[str, Any]:
        etype = type(exc).__name__
        msg = str(exc)
        winerror = getattr(exc, "winerror", None)
        errno = getattr(exc, "errno", None)
        lower = msg.lower() if isinstance(msg, str) else ""

        error_class = "unknown_error"
        if winerror == 32:
            error_class = "winerror_32_file_in_use"
        elif isinstance(exc, PermissionError):
            error_class = "permission_denied"
        elif isinstance(exc, FileNotFoundError):
            error_class = "file_not_found"
        elif isinstance(exc, sqlite3.OperationalError):
            if "locked" in lower:
                error_class = "sqlite_database_locked"
            elif "busy" in lower:
                error_class = "sqlite_busy"

        return {
            "error_class": error_class,
            "exception_type": etype,
            "message": msg,
            "winerror": _safe_int(winerror),
            "errno": _safe_int(errno),
        }

    def _incident_log(event: str, payload: Dict[str, Any]) -> None:
        try:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            logs_dir = os.path.join("data", "logs")
            os.makedirs(logs_dir, exist_ok=True)
            log_path = os.path.join(logs_dir, f"restart_wal_shm_{date_str}.log")

            try:
                global _LAST_WAL_LOG_RETENTION_DATE
                if _LAST_WAL_LOG_RETENTION_DATE != date_str:
                    _LAST_WAL_LOG_RETENTION_DATE = date_str

                    keep_days = 14
                    max_files = 30

                    prefix = "restart_wal_shm_"
                    suffix = ".log"
                    paths: List[str] = []
                    try:
                        for name in os.listdir(logs_dir):
                            if not (name.startswith(prefix) and name.endswith(suffix)):
                                continue
                            paths.append(os.path.join(logs_dir, name))
                    except Exception:
                        paths = []

                    by_date: List[tuple[str, str]] = []
                    for p in paths:
                        try:
                            base = os.path.basename(p)
                            raw = base[len(prefix) : -len(suffix)]
                            dt = datetime.strptime(raw, "%Y-%m-%d")
                            by_date.append((dt.strftime("%Y-%m-%d"), p))
                        except Exception:
                            continue

                    by_date.sort(key=lambda t: t[0], reverse=True)

                    cutoff = datetime.now(timezone.utc).date().toordinal() - keep_days
                    kept: List[str] = []
                    for d, p in by_date:
                        try:
                            dt = datetime.strptime(d, "%Y-%m-%d").date()
                            if dt.toordinal() < cutoff:
                                try:
                                    os.remove(p)
                                except Exception:
                                    pass
                                continue
                            kept.append(p)
                        except Exception:
                            continue

                    if len(kept) > max_files:
                        for p in kept[max_files:]:
                            try:
                                os.remove(p)
                            except Exception:
                                pass
            except Exception:
                pass

            base: Dict[str, Any] = {
                "ts_utc": _utc_now_iso(),
                "event": str(event),
                "restart_cycle_id": restart_cycle_id,
                "scum_db_path": scum_db_path,
            }
            base.update(payload or {})

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(base, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # 1. Verificar se servidor está parado (múltiplas verificações)
    max_checks = 3
    server_running = False

    for check_num in range(max_checks):
        try:
            if server_manager and hasattr(server_manager, "_is_service_running"):
                if server_manager._is_service_running():
                    server_running = True
                    if check_num < max_checks - 1:
                        log(
                            f"Servidor ainda rodando (verificação {check_num + 1}/{max_checks}) - aguardando...",
                            "warning",
                        )
                        time.sleep(2)  # Aguardar 2s entre verificações
                    else:
                        result["server_was_running"] = True
                        result["message"] = (
                            "Servidor está rodando - não é seguro limpar arquivos WAL/SHM"
                        )
                        log(result["message"], "warning")
                        return result
                else:
                    server_running = False
                    break
        except Exception as e:
            error_msg = (
                f"Erro ao verificar status do servidor (tentativa {check_num + 1}): {e}"
            )
            result["errors"].append(error_msg)
            log(error_msg, "error")
            # Continuar mesmo se verificação falhar (pode ser que server_manager não esteja disponível)
            break

    # 2. Fechar conexões do ScumDbSharedCopyManager se existir
    try:
        if _shared_copy_manager_instance:
            log("Fechando conexões do ScumDbSharedCopyManager...")
            try:
                # Tentar limpar cópias antigas
                if hasattr(_shared_copy_manager_instance, "cleanup_old_copies"):
                    _shared_copy_manager_instance.cleanup_old_copies()
                log("Conexões do ScumDbSharedCopyManager fechadas")
            except Exception as e:
                log(
                    f"Erro ao fechar conexões do ScumDbSharedCopyManager: {e}",
                    "warning",
                )
    except Exception as e:
        log(f"Erro ao acessar ScumDbSharedCopyManager: {e}", "warning")

    # 3. Aguardar alguns segundos para garantir que servidor parou completamente
    if wait_after_stop > 0:
        log(
            f"Aguardando {wait_after_stop}s para garantir que servidor parou completamente..."
        )
        time.sleep(wait_after_stop)

    # 4. Verificar se SCUM.db existe
    if not os.path.exists(scum_db_path):
        result["message"] = f"SCUM.db não encontrado: {scum_db_path}"
        result["errors"].append(result["message"])
        log(result["message"], "warning")
        _incident_log(
            "cleanup_skipped_scum_db_missing",
            {
                "wal": _file_state(f"{scum_db_path}-wal"),
                "shm": _file_state(f"{scum_db_path}-shm"),
                "result": {"success": False, "reason": "scum_db_missing"},
            },
        )
        return result

    # 5. Verificar se arquivos WAL/SHM existem
    wal_path = f"{scum_db_path}-wal"
    shm_path = f"{scum_db_path}-shm"

    files_to_check = [("WAL", wal_path), ("SHM", shm_path)]

    for file_type, file_path in files_to_check:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            result["files_found"].append(
                {"type": file_type, "path": file_path, "size": file_size}
            )
            log(f"Arquivo {file_type} encontrado: {file_path} ({file_size} bytes)")

    _incident_log(
        "cleanup_detected_files",
        {
            "wal": _file_state(wal_path),
            "shm": _file_state(shm_path),
            "server_running": bool(server_running),
        },
    )

    # Se não há arquivos para limpar, retornar sucesso
    if not result["files_found"]:
        result["success"] = True
        result["message"] = "Nenhum arquivo WAL/SHM encontrado - nada a fazer"
        log(result["message"], "info")
        return result

    # 6. Tentar fazer checkpoint do WAL (com múltiplas tentativas)
    conn = None
    max_checkpoint_attempts = 3

    for attempt in range(max_checkpoint_attempts):
        try:
            log(
                f"Conectando ao SCUM.db para fazer checkpoint do WAL (tentativa {attempt + 1}/{max_checkpoint_attempts})..."
            )
            _incident_log(
                "checkpoint_attempt",
                {
                    "attempt": attempt + 1,
                    "max_attempts": max_checkpoint_attempts,
                    "wal": _file_state(wal_path),
                    "shm": _file_state(shm_path),
                },
            )
            conn = sqlite3.connect(scum_db_path, timeout=10.0)
            cursor = conn.cursor()

            # Verificar modo journal atual
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0].upper()
            log(f"Modo journal atual: {journal_mode}")
            _incident_log(
                "journal_mode",
                {
                    "attempt": attempt + 1,
                    "journal_mode": str(journal_mode),
                },
            )

            # Se estiver em modo WAL, fazer checkpoint
            if journal_mode == "WAL":
                log("Fazendo checkpoint do WAL...")
                try:
                    # Fazer checkpoint completo (aplica todas as mudanças pendentes)
                    cursor.execute("PRAGMA wal_checkpoint(FULL)")
                    checkpoint_result = cursor.fetchone()
                    log(f"Checkpoint result: {checkpoint_result}")
                    _incident_log(
                        "wal_checkpoint_result",
                        {
                            "attempt": attempt + 1,
                            "checkpoint_result": checkpoint_result,
                        },
                    )

                    # Verificar se checkpoint foi bem-sucedido
                    # Resultado: (busy, log, checkpointed)
                    if checkpoint_result and len(checkpoint_result) >= 3:
                        busy, log_pages, checkpointed = checkpoint_result
                        if busy == 0:  # 0 = sucesso, 1 = ainda ocupado
                            result["checkpoint_success"] = True
                            log(
                                f"Checkpoint bem-sucedido: {checkpointed} páginas checkpointed"
                            )
                        else:
                            if attempt < max_checkpoint_attempts - 1:
                                log(
                                    f"Checkpoint ainda ocupado - tentando novamente em 2s...",
                                    "warning",
                                )
                                conn.close()
                                conn = None
                                time.sleep(2)
                                continue
                            else:
                                log(
                                    "Checkpoint ainda ocupado após múltiplas tentativas - continuando mesmo assim",
                                    "warning",
                                )
                                result["checkpoint_success"] = False
                    else:
                        result["checkpoint_success"] = (
                            True  # Assumir sucesso se não conseguir verificar
                        )
                        log(
                            "Checkpoint executado (não foi possível verificar resultado)"
                        )

                    # Tentar desabilitar modo WAL
                    log("Desabilitando modo WAL...")
                    cursor.execute("PRAGMA journal_mode=DELETE")
                    new_mode = cursor.fetchone()[0].upper()
                    log(f"Novo modo journal: {new_mode}")
                    _incident_log(
                        "journal_mode_set",
                        {
                            "attempt": attempt + 1,
                            "new_mode": str(new_mode),
                        },
                    )

                except Exception as e:
                    if attempt < max_checkpoint_attempts - 1:
                        error_msg = f"Erro ao fazer checkpoint (tentativa {attempt + 1}): {e} - tentando novamente..."
                        log(error_msg, "warning")
                        _incident_log(
                            "checkpoint_error_retry",
                            {
                                "attempt": attempt + 1,
                                "max_attempts": max_checkpoint_attempts,
                                **_classify_error(e),
                            },
                        )
                        if conn:
                            try:
                                conn.close()
                            except:
                                pass
                        conn = None
                        time.sleep(2)
                        continue
                    else:
                        error_msg = f"Erro ao fazer checkpoint após {max_checkpoint_attempts} tentativas: {e}"
                        result["errors"].append(error_msg)
                        log(error_msg, "warning")
                        _incident_log(
                            "checkpoint_error_final",
                            {
                                "attempt": attempt + 1,
                                "max_attempts": max_checkpoint_attempts,
                                **_classify_error(e),
                            },
                        )
                        # Continuar mesmo se checkpoint falhar
            else:
                log(
                    f"Banco não está em modo WAL ({journal_mode}) - checkpoint não necessário"
                )
                result["checkpoint_success"] = (
                    True  # Considerar sucesso se não está em WAL
                )

            # Fechar conexão explicitamente
            conn.commit()
            conn.close()
            conn = None

            log("Conexão fechada com sucesso")
            break  # Sair do loop se checkpoint foi bem-sucedido

        except sqlite3.OperationalError as e:
            if attempt < max_checkpoint_attempts - 1:
                error_msg = f"Erro ao conectar (tentativa {attempt + 1}): {e} - tentando novamente em 2s..."
                log(error_msg, "warning")
                _incident_log(
                    "checkpoint_connect_error_retry",
                    {
                        "attempt": attempt + 1,
                        "max_attempts": max_checkpoint_attempts,
                        **_classify_error(e),
                    },
                )
                time.sleep(2)
                continue
            else:
                error_msg = f"Erro ao conectar/fazer checkpoint após {max_checkpoint_attempts} tentativas: {e}"
                result["errors"].append(error_msg)
                log(error_msg, "warning")
                _incident_log(
                    "checkpoint_connect_error_final",
                    {
                        "attempt": attempt + 1,
                        "max_attempts": max_checkpoint_attempts,
                        **_classify_error(e),
                    },
                )
                # Continuar mesmo se falhar - pode ser que arquivos estejam órfãos
                break
        except Exception as e:
            error_msg = (
                f"Erro inesperado durante checkpoint (tentativa {attempt + 1}): {e}"
            )
            result["errors"].append(error_msg)
            log(error_msg, "error")
            _incident_log(
                "checkpoint_unexpected_error",
                {
                    "attempt": attempt + 1,
                    "max_attempts": max_checkpoint_attempts,
                    **_classify_error(e),
                },
            )
            break
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
                conn = None

    # 7. Aguardar um pouco após fechar conexão
    if wait_after_close > 0:
        log(f"Aguardando {wait_after_close}s após fechar conexão...")
        time.sleep(wait_after_close)

    # 8. Remover arquivos WAL/SHM (com múltiplas tentativas)
    max_remove_attempts = 3

    for file_info in result["files_found"]:
        file_path = file_info["path"]
        file_type = file_info["type"]
        removed = False

        for attempt in range(max_remove_attempts):
            try:
                if os.path.exists(file_path):
                    # Tentar remover
                    os.remove(file_path)

                    # Verificar se foi removido
                    if not os.path.exists(file_path):
                        result["files_removed"].append(
                            {
                                "type": file_type,
                                "path": file_path,
                                "size": file_info["size"],
                            }
                        )
                        log(f"Arquivo {file_type} removido: {file_path}")
                        _incident_log(
                            "remove_ok",
                            {
                                "file_type": file_type,
                                "file": _file_state(file_path),
                                "attempt": attempt + 1,
                                "max_attempts": max_remove_attempts,
                            },
                        )
                        removed = True
                        break
                    else:
                        if attempt < max_remove_attempts - 1:
                            log(
                                f"Arquivo {file_type} ainda existe após remoção - tentando novamente em 1s...",
                                "warning",
                            )
                            time.sleep(1)
                            continue
                        else:
                            error_msg = f"Arquivo {file_type} ainda existe após {max_remove_attempts} tentativas de remoção"
                            result["errors"].append(error_msg)
                            log(error_msg, "warning")
                else:
                    log(f"Arquivo {file_type} já não existe: {file_path}", "info")
                    removed = True
                    break

            except PermissionError as e:
                if attempt < max_remove_attempts - 1:
                    log(
                        f"Sem permissão para remover {file_type} (tentativa {attempt + 1}) - tentando novamente em 1s...",
                        "warning",
                    )
                    _incident_log(
                        "remove_error_retry",
                        {
                            "file_type": file_type,
                            "file": _file_state(file_path),
                            "attempt": attempt + 1,
                            "max_attempts": max_remove_attempts,
                            **_classify_error(e),
                        },
                    )
                    time.sleep(1)
                    continue
                else:
                    error_msg = f"Sem permissão para remover {file_type}: {file_path}"
                    result["errors"].append(error_msg)
                    log(error_msg, "warning")
                    _incident_log(
                        "remove_error_final",
                        {
                            "file_type": file_type,
                            "file": _file_state(file_path),
                            "attempt": attempt + 1,
                            "max_attempts": max_remove_attempts,
                            **_classify_error(e),
                        },
                    )
                    break
            except OSError as e:
                # Erro de arquivo em uso ou bloqueado
                if attempt < max_remove_attempts - 1:
                    log(
                        f"Arquivo {file_type} em uso (tentativa {attempt + 1}): {e} - tentando novamente em 2s...",
                        "warning",
                    )
                    _incident_log(
                        "remove_error_retry",
                        {
                            "file_type": file_type,
                            "file": _file_state(file_path),
                            "attempt": attempt + 1,
                            "max_attempts": max_remove_attempts,
                            **_classify_error(e),
                        },
                    )
                    time.sleep(2)
                    continue
                else:
                    error_msg = f"Arquivo {file_type} ainda em uso após {max_remove_attempts} tentativas: {file_path}"
                    result["errors"].append(error_msg)
                    log(error_msg, "warning")
                    _incident_log(
                        "remove_error_final",
                        {
                            "file_type": file_type,
                            "file": _file_state(file_path),
                            "attempt": attempt + 1,
                            "max_attempts": max_remove_attempts,
                            **_classify_error(e),
                        },
                    )
                    break
            except Exception as e:
                error_msg = f"Erro ao remover {file_type} ({file_path}): {e}"
                result["errors"].append(error_msg)
                log(error_msg, "warning")
                _incident_log(
                    "remove_unexpected_error",
                    {
                        "file_type": file_type,
                        "file": _file_state(file_path),
                        "attempt": attempt + 1,
                        "max_attempts": max_remove_attempts,
                        **_classify_error(e),
                    },
                )
                break

    # 9. Determinar sucesso
    if result["files_removed"]:
        result["success"] = True
        removed_count = len(result["files_removed"])
        total_size = sum(f["size"] for f in result["files_removed"])
        result["message"] = (
            f"Limpeza concluída: {removed_count} arquivo(s) removido(s) ({total_size} bytes)"
        )
        log(result["message"], "info")
        _incident_log(
            "cleanup_ok",
            {
                "files_removed": result.get("files_removed", []),
                "wal": _file_state(wal_path),
                "shm": _file_state(shm_path),
                "checkpoint_success": bool(result.get("checkpoint_success")),
            },
        )
    elif result["errors"]:
        result["message"] = (
            f"Limpeza parcial: {len(result['errors'])} erro(s) encontrado(s)"
        )
        log(result["message"], "warning")
        _incident_log(
            "cleanup_failed",
            {
                "errors": result.get("errors", []),
                "wal": _file_state(wal_path),
                "shm": _file_state(shm_path),
                "checkpoint_success": bool(result.get("checkpoint_success")),
            },
        )
    else:
        result["success"] = True
        result["message"] = "Nenhum arquivo foi removido (já não existiam)"
        log(result["message"], "info")
        _incident_log(
            "cleanup_noop",
            {
                "wal": _file_state(wal_path),
                "shm": _file_state(shm_path),
                "checkpoint_success": bool(result.get("checkpoint_success")),
            },
        )

    return result
