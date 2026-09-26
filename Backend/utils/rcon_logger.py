"""
RconLogger - Sistema estruturado de logs e auto-limpeza para RCON (BSBR-SCUM e SCUM-RCON).

Registra:
- Comandos enviados, latência em ms, origem da chamada e resposta da engine.
- Falhas de conexão, timeouts e respostas com erro do servidor.
- Auto-limpeza configurável por dias de retenção e limite de tamanho (MB).
"""

import os
import re
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _mask_sensitive_data(command: str) -> str:
    """Mascara senhas ou dados sensíveis em comandos de log se houver."""
    if not command:
        return ""
    # Mascara senhas passadas via parâmetros comuns (ex: password <secret> ou senha=<secret>)
    masked = re.sub(r'(?i)\b(password|pass|senha)\b([\s:=]+)([^\s]+)', r'\1\2********', command)
    return masked



class RconLogger:
    """
    Logger thread-safe dedicado para operações RCON com suporte a retenção e limpeza.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, logs_dir: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Retorna uma instância Singleton do RconLogger."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(logs_dir=logs_dir, config=config)
            elif logs_dir or config:
                # Atualizar configurações se passadas
                if logs_dir:
                    cls._instance.set_logs_dir(logs_dir)
                if config:
                    cls._instance.load_config(config)
            return cls._instance

    def __init__(
        self,
        logs_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self._write_lock = threading.Lock()
        self.enabled = True
        self.retention_days = 7
        self.max_size_mb = 50
        self.auto_cleanup = True

        # Resolver diretório padrão de logs
        self.logs_dir = Path(logs_dir) if logs_dir else self._resolve_default_logs_dir()
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        if config:
            self.load_config(config)

    def _resolve_default_logs_dir(self) -> Path:
        """Resolve a pasta padrão para data/logs/rcon/."""
        # Se estiver em ambiente congelado (PyInstaller)
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).parent / "data" / "logs" / "rcon"
        else:
            # Em desenvolvimento: c:\Dev\SSM\SSM 3.0\Backend\data\logs\rcon
            backend_root = Path(__file__).resolve().parent.parent
            base = backend_root / "data" / "logs" / "rcon"
        return base

    def set_logs_dir(self, logs_dir: str) -> None:
        """Define o diretório onde os logs da RCON serão gravados."""
        p = Path(logs_dir)
        if p.name.lower() != "rcon":
            p = p / "rcon"
        p.mkdir(parents=True, exist_ok=True)
        self.logs_dir = p

    def load_config(self, config: Dict[str, Any]) -> None:
        """Carrega parâmetros de configuração da RCON."""
        if not config:
            return
        rcon_cfg = config.get("rcon", {})
        logging_cfg = rcon_cfg.get("logging", {})

        self.enabled = bool(logging_cfg.get("enabled", True))
        self.retention_days = max(1, int(logging_cfg.get("retention_days", 7) or 7))
        self.max_size_mb = max(5, int(logging_cfg.get("max_size_mb", 50) or 50))
        self.auto_cleanup = bool(logging_cfg.get("auto_cleanup", True))

        # Se houver custom logs_dir no config
        custom_logs = config.get("paths", {}).get("logs_directory") or config.get("logging", {}).get("log_dir")
        if custom_logs:
            self.set_logs_dir(custom_logs)

    def _get_log_files_for_today(self) -> Tuple[Path, Path]:
        """Retorna caminhos para (main_log, error_log) de hoje."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        main_log = self.logs_dir / f"rcon_{today_str}.log"
        error_log = self.logs_dir / f"rcon_errors_{today_str}.log"
        return main_log, error_log

    def log_command(
        self,
        command: str,
        response: str = "",
        duration_ms: float = 0.0,
        origin: str = "SYSTEM",
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """
        Registra a execução de um comando RCON de forma thread-safe.
        """
        if not self.enabled:
            return

        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        safe_command = _mask_sensitive_data(command.strip())
        origin_tag = (origin or "SYSTEM").upper()
        status_tag = "INFO" if success else "ERROR"
        result_tag = "SUCCESS" if success else "FAILED"

        # Tratar resposta ou erro
        if success:
            detail = f'Response: "{response.strip()}"' if response else "Response: (empty / ok)"
        else:
            detail = f'Error: "{error or response or "Unknown error"}"'

        log_line = f"[{timestamp}] [{status_tag}] [{origin_tag}] [{safe_command}] -> {result_tag} ({duration_ms:.1f}ms) | {detail}\n"

        with self._write_lock:
            try:
                self.logs_dir.mkdir(parents=True, exist_ok=True)
                main_file, error_file = self._get_log_files_for_today()

                # Escreve no log principal diário
                with open(main_file, "a", encoding="utf-8") as f:
                    f.write(log_line)

                # Se for erro, grava também no log de erros diário
                if not success or error:
                    with open(error_file, "a", encoding="utf-8") as f:
                        f.write(log_line)
            except Exception as e:
                # Falha silenciosa para não quebrar a execução do jogo
                print(f"[RconLogger] Erro ao gravar log: {e}", file=sys.stderr)

    def log_error(
        self,
        command: str,
        error: str,
        duration_ms: float = 0.0,
        origin: str = "SYSTEM",
    ) -> None:
        """Helper para registrar erros de conexão ou timeout."""
        self.log_command(
            command=command,
            response="",
            duration_ms=duration_ms,
            origin=origin,
            success=False,
            error=error,
        )

    def cleanup_old_logs(
        self,
        retention_days: Optional[int] = None,
        max_folder_size_mb: Optional[int] = None,
    ) -> Tuple[int, int]:
        """
        Executa a limpeza de logs antigos com base em:
        1. Dias de retenção (arquivos mais antigos que `retention_days` são deletados).
        2. Cota de tamanho da pasta (se > `max_folder_size_mb`, deleta arquivos mais antigos primeiro).

        Returns:
            Tuple[int, int]: (arquivos_deletados, bytes_liberados)
        """
        r_days = retention_days if retention_days is not None else self.retention_days
        max_mb = max_folder_size_mb if max_folder_size_mb is not None else self.max_size_mb

        if not self.logs_dir.is_dir():
            return 0, 0

        deleted_count = 0
        freed_bytes = 0
        cutoff_date = datetime.now() - timedelta(days=r_days)
        today_str = datetime.now().strftime("%Y-%m-%d")

        with self._write_lock:
            try:
                log_files = []
                for item in self.logs_dir.iterdir():
                    if not item.is_file() or not item.name.endswith(".log"):
                        continue
                    try:
                        stat = item.stat()
                        log_files.append({
                            "path": item,
                            "size": stat.st_size,
                            "mtime": stat.st_mtime,
                            "name": item.name,
                        })
                    except Exception:
                        pass

                # 1. Limpeza por dias de retenção
                remaining_files = []
                for f_info in log_files:
                    path: Path = f_info["path"]
                    # Não deletar os logs de hoje
                    if today_str in path.name:
                        remaining_files.append(f_info)
                        continue

                    # Tentar extrair a data do nome do arquivo (ex: rcon_2026-08-23.log ou rcon_errors_2026-08-23.log)
                    match = re.search(r'(\d{4}-\d{2}-\d{2})', path.name)
                    file_date = None
                    if match:
                        try:
                            file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                        except Exception:
                            pass

                    if file_date:
                        is_expired = file_date < cutoff_date
                    else:
                        file_mtime_date = datetime.fromtimestamp(f_info["mtime"])
                        is_expired = file_mtime_date < cutoff_date

                    if is_expired:
                        try:
                            f_size = f_info["size"]
                            path.unlink()
                            deleted_count += 1
                            freed_bytes += f_size
                        except Exception:
                            remaining_files.append(f_info)
                    else:
                        remaining_files.append(f_info)

                # 2. Limpeza por cota de tamanho (se ainda ultrapassar o limite em MB)
                max_bytes = max_mb * 1024 * 1024
                total_size = sum(f["size"] for f in remaining_files)

                if total_size > max_bytes:
                    # Ordenar por mais antigo primeiro (mtime crescente)
                    remaining_files.sort(key=lambda x: x["mtime"])

                    for f_info in remaining_files:
                        if total_size <= max_bytes:
                            break
                        path = f_info["path"]
                        # Proteger o log do dia atual
                        if today_str in path.name:
                            continue

                        try:
                            f_size = f_info["size"]
                            path.unlink()
                            deleted_count += 1
                            freed_bytes += f_size
                            total_size -= f_size
                        except Exception:
                            pass

            except Exception as e:
                print(f"[RconLogger] Erro durante auto-limpeza de logs: {e}", file=sys.stderr)

        return deleted_count, freed_bytes

    def open_logs_folder_in_explorer(self) -> Tuple[bool, str]:
        """Abre a pasta data/logs/rcon/ no gerenciador de arquivos do sistema operacional."""
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(str(self.logs_dir))
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(self.logs_dir)])
            return True, f"Pasta de logs aberta: {self.logs_dir}"
        except Exception as e:
            return False, f"Erro ao abrir pasta: {e}"
