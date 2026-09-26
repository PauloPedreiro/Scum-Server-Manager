"""
Server Manager para controle do servidor SCUM
Substitui os scripts .bat por controle Python completo
"""

import subprocess
import time
import sqlite3
import os
import sys
import threading
import ctypes
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from utils.logger import StructuredLogger
from utils.config_path_helper import ConfigPathHelper
import json
import uuid
from datetime import datetime, timezone

from core.webhooks.discord_webhook import DiscordWebhook


class ServerManager:
    def __init__(
        self, config: Dict[str, Any], path_helper: Optional[ConfigPathHelper] = None
    ):
        """
        Inicializar ServerManager

        Args:
            config: Configuração da seção 'server' do config.json
            path_helper: Helper para obter caminhos (opcional, cria novo se não fornecido)
        """
        self.config = config
        self.path_helper = path_helper
        self.logger = StructuredLogger()
        self.service_name = str(config.get("service_name", "SCUMServer") or "SCUMServer")
        
        # Lock de concorrência para prevenir múltiplos restarts simultâneos
        self._restart_lock = threading.Lock()
        self._restart_in_progress = False
        self._restart_lock_file = None  # Será inicializado quando necessário

        # Usar ConfigPathHelper para obter caminhos (elimina redundância)
        if path_helper is None:
            # Se não foi fornecido, criar um novo (compatibilidade retroativa)
            from utils.config_path_helper import ConfigPathHelper

            # Precisamos do config completo, não apenas da seção server
            # Em caso de uso sem path_helper, usar fallbacks
            self.server_path = config.get(
                "server_path", "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64"
            )
            self.install_path = config.get("install_path", "C:\\Servers\\Scum")
        else:
            # Usar ConfigPathHelper (forma preferida)
            self.server_path = path_helper.get_scum_server_path(
                "binaries_directory", "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64"
            )
            self.install_path = path_helper.get_scum_server_path(
                "root_directory", "C:\\Servers\\Scum"
            )

        # Campos específicos do servidor (não são caminhos do SCUM)
        self.steamcmd_path = config.get("steamcmd_path", "C:\\Servers\\steamcmd")
        nssm_path_config = config.get("nssm_path", "nssm-2.24\\win64\\nssm.exe")
        nssm_path = Path(nssm_path_config)
        if not nssm_path.is_absolute():
            # Detectar diretório base: executável compilado ou script Python
            if getattr(sys, "frozen", False):
                # Rodando como executável - usar diretório do .exe como base
                backend_root = Path(sys.executable).parent
            else:
                # Rodando como script - usar diretório Backend
                backend_root = Path(__file__).resolve().parents[2]
            nssm_path = backend_root / nssm_path
        self.nssm_path = str(nssm_path)

        # VALIDAÇÃO RIGOROSA: Se NSSM não existir, lançar exceção
        self.nssm_available = os.path.exists(self.nssm_path)
        if not self.nssm_available:
            error_msg = (
                f"NSSM não encontrado em: {self.nssm_path}. "
                f"Operações de serviço (start/stop/restart) não estarão disponíveis até configurar/instalar o NSSM."
            )
            self.logger.warn(error_msg)
        else:
            self.logger.info(f"NSSM validado e encontrado em: {self.nssm_path}")

        # Configurações do servidor
        self.port = config.get("port", 7777)
        self.max_players = config.get("max_players", 64)
        self.use_battleye = config.get("use_battleye", True)

        # Carregar webhooks (usar path_helper se disponível)
        if path_helper:
            webhooks_path = path_helper.get_application_path(
                "webhooks_file", "data/webhooks.json"
            )
        else:
            app_paths = config.get("paths", {}).get("application", {})
            default_webhooks = app_paths.get("webhooks_file", "data/webhooks.json")
            webhooks_path = Path(default_webhooks)
            if not webhooks_path.is_absolute():
                # Detectar diretório base: executável compilado ou script Python
                if getattr(sys, "frozen", False):
                    # Rodando como executável - usar diretório do .exe como base
                    backend_root = Path(sys.executable).parent
                else:
                    # Rodando como script - usar diretório Backend
                    backend_root = Path(__file__).resolve().parents[2]
                webhooks_path = backend_root / webhooks_path
            webhooks_path = str(webhooks_path)

        # Carregar webhooks
        webhooks_config = {}
        webhooks_modified = False
        
        if os.path.exists(webhooks_path):
            try:
                with open(webhooks_path, "r", encoding="utf-8") as f:
                    webhooks_config = json.load(f)
            except Exception as e:
                # Log error se logger disponível
                webhooks_config = {}
        
        # Garantir que "bank_transaction" existe
        if "bank_transaction" not in webhooks_config:
            webhooks_config["bank_transaction"] = ""
            webhooks_modified = True
        
        # Salvar se foi modificado
        if webhooks_modified:
            try:
                webhooks_dir = os.path.dirname(webhooks_path)
                if webhooks_dir:
                    os.makedirs(webhooks_dir, exist_ok=True)
                
                with open(webhooks_path, "w", encoding="utf-8") as f:
                    json.dump(webhooks_config, f, indent=2, ensure_ascii=False, sort_keys=False)
            except Exception:
                pass  # Silenciosamente ignora erro de salvamento
        
        config["webhooks"] = webhooks_config

        # Webhook Discord (lazy)
        self._discord_webhook: Optional[DiscordWebhook] = None

    def create_or_update_nssm_service(
        self,
        *,
        app_exe: str,
        app_directory: str,
        app_parameters: str,
        console_timeout_ms: int = 120000,
        enable_terminate: bool = True,
        terminate_timeout_ms: int = 300000,
    ) -> Dict[str, Any]:
        try:
            if sys.platform != "win32":
                return {
                    "success": False,
                    "message": "Operação suportada apenas no Windows",
                    "status": "not_supported",
                }

            service = str(self.service_name)
            nssm = str(self.nssm_path)

            if not os.path.exists(nssm):
                return {
                    "success": False,
                    "message": f"NSSM não encontrado em: {nssm}",
                    "status": "nssm_not_found",
                }

            if not app_exe or not os.path.exists(app_exe):
                return {
                    "success": False,
                    "message": f"SCUMServer.exe não encontrado: {app_exe}",
                    "status": "app_not_found",
                }

            if not app_directory or not os.path.isdir(app_directory):
                return {
                    "success": False,
                    "message": f"Diretório inválido: {app_directory}",
                    "status": "invalid_directory",
                }

            def _is_admin() -> bool:
                try:
                    return bool(ctypes.windll.shell32.IsUserAnAdmin())
                except Exception:
                    return False

            def _service_exists() -> bool:
                try:
                    r = subprocess.run(
                        ["sc", "query", service],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                        ),
                    )
                    return int(r.returncode or 0) == 0
                except Exception:
                    return False

            exists_before = _service_exists()

            direct_outputs = []
            if _is_admin():
                try:
                    if not exists_before:
                        r = subprocess.run(
                            [nssm, "install", service, app_exe],
                            capture_output=True,
                            text=True,
                            timeout=30,
                            creationflags=(
                                subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                            ),
                        )
                        direct_outputs.append(((r.stdout or "") + "\n" + (r.stderr or "")).strip())
                        if int(r.returncode or 0) != 0:
                            return {
                                "success": False,
                                "message": "Falha ao criar serviço via NSSM.",
                                "status": "nssm_install_failed",
                                "returncode": int(r.returncode or 0),
                                "output": "\n\n".join(o for o in direct_outputs if o)[:2000],
                            }

                    for cmd in [
                        [nssm, "set", service, "Application", app_exe],
                        [nssm, "set", service, "AppDirectory", app_directory],
                        [nssm, "set", service, "AppParameters", app_parameters or ""],
                    ]:
                        r = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=30,
                            creationflags=(
                                subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                            ),
                        )
                        direct_outputs.append(((r.stdout or "") + "\n" + (r.stderr or "")).strip())
                        if int(r.returncode or 0) != 0:
                            return {
                                "success": False,
                                "message": "Falha ao configurar serviço via NSSM.",
                                "status": "nssm_set_failed",
                                "returncode": int(r.returncode or 0),
                                "output": "\n\n".join(o for o in direct_outputs if o)[:2000],
                            }

                    preset_res = self.apply_nssm_shutdown_preset(
                        console_timeout_ms=int(console_timeout_ms),
                        enable_terminate=bool(enable_terminate),
                        terminate_timeout_ms=int(terminate_timeout_ms),
                    )
                    if not preset_res.get("success"):
                        return {
                            "success": True,
                            "message": "Serviço NSSM criado/atualizado, mas o preset de shutdown não pôde ser verificado.",
                            "status": "ok_with_warning",
                            "service_exists_before": bool(exists_before),
                            "preset": preset_res,
                            "output": "\n\n".join(o for o in direct_outputs if o)[:2000],
                        }

                    return {
                        "success": True,
                        "message": "Serviço NSSM criado/atualizado com sucesso",
                        "status": "ok",
                        "service_exists_before": bool(exists_before),
                        "output": "\n\n".join(o for o in direct_outputs if o)[:2000],
                    }
                except Exception as e:
                    direct_outputs.append(str(e))

            import base64

            escaped_args = (app_parameters or "").replace("'", "''")

            ps_lines = [
                "$ErrorActionPreference = 'Stop'",
                f"$nssm = '{nssm}'",
                f"$service = '{service}'",
                f"$app = '{app_exe}'",
                f"$dir = '{app_directory}'",
                f"$args = '{escaped_args}'",
                "try { $null = Get-Service -Name $service -ErrorAction Stop } catch { & $nssm install $service $app | Out-Null }",
                "& $nssm set $service Application $app | Out-Null",
                "& $nssm set $service AppDirectory $dir | Out-Null",
                "& $nssm set $service AppParameters $args | Out-Null",
                "exit 0",
            ]
            ps_inner = "\n".join(ps_lines)
            encoded = base64.b64encode(ps_inner.encode("utf-16le")).decode("ascii")
            ps_cmd = (
                "Start-Process -FilePath 'powershell' "
                "-ArgumentList '-NoProfile -ExecutionPolicy Bypass -EncodedCommand "
                + encoded
                + "' -Verb RunAs -WindowStyle Hidden -Wait -PassThru | ForEach-Object { exit $_.ExitCode }"
            )

            res = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=180,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )

            out = ((res.stdout or "") + "\n" + (res.stderr or "")).strip()
            if int(res.returncode or 0) != 0:
                return {
                    "success": False,
                    "message": "Falha ao criar/atualizar serviço via NSSM (UAC).",
                    "status": "elevation_failed",
                    "returncode": int(res.returncode or 0),
                    "output": out[:2000],
                }

            preset_res = self.apply_nssm_shutdown_preset(
                console_timeout_ms=int(console_timeout_ms),
                enable_terminate=bool(enable_terminate),
                terminate_timeout_ms=int(terminate_timeout_ms),
            )
            if not preset_res.get("success"):
                return {
                    "success": True,
                    "message": "Serviço NSSM criado/atualizado, mas o preset de shutdown não pôde ser verificado.",
                    "status": "ok_with_warning",
                    "service_exists_before": bool(exists_before),
                    "preset": preset_res,
                    "output": out[:2000],
                }

            return {
                "success": True,
                "message": "Serviço NSSM criado/atualizado com sucesso",
                "status": "ok",
                "service_exists_before": bool(exists_before),
                "output": out[:2000],
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Timeout ao criar/atualizar serviço via NSSM (provável UAC pendente).",
                "status": "timeout",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Erro ao criar/atualizar serviço via NSSM: {e}",
                "status": "error",
            }

    def _get_discord_webhook(self) -> Optional[DiscordWebhook]:
        try:
            if self._discord_webhook is not None:
                return self._discord_webhook
            self._discord_webhook = DiscordWebhook(self.config, logger=self.logger)
            return self._discord_webhook
        except Exception:
            return None

    def _sanitize_process_output(self, value: Any) -> str:
        try:
            s = "" if value is None else str(value)
        except Exception:
            return ""

        if "\x00" in s:
            s = s.replace("\x00", "")
        return s.strip()

    def _is_scumserver_process_running(self) -> bool:
        if sys.platform != "win32":
            return False

        powershell_cmd = r"""
        $p = Get-Process -Name 'SCUMServer' -ErrorAction SilentlyContinue
        if ($null -ne $p) { Write-Host 'RUNNING' } else { Write-Host 'STOPPED' }
        """
        try:
            res = subprocess.run(
                ["powershell", "-Command", powershell_cmd],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            out = self._sanitize_process_output((res.stdout or "") + "\n" + (res.stderr or ""))
            return "RUNNING" in out
        except Exception:
            return False

    def _get_scumserver_working_set_bytes(self) -> Optional[int]:
        if sys.platform != "win32":
            return None

        powershell_cmd = r"""
        $p = Get-Process -Name 'SCUMServer' -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $p) { Write-Host $p.WorkingSet64 } else { Write-Host '' }
        """
        try:
            res = subprocess.run(
                ["powershell", "-Command", powershell_cmd],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            out = self._sanitize_process_output((res.stdout or "") + "\n" + (res.stderr or ""))
            if not out:
                return None
            # Expected output is an integer (bytes)
            return int(out.strip())
        except Exception:
            return None

    def _wait_for_scumserver_ready(
        self,
        *,
        min_working_set_gb: float = 6.0,
        max_wait_seconds: int = 600,
        check_interval_seconds: float = 5.0,
    ) -> Tuple[bool, str]:
        """Wait until SCUMServer.exe is running and has reached a RAM threshold.

        This is used as a readiness barrier before resuming SSM jobs that may touch SCUM.db.
        """
        if sys.platform != "win32":
            return False, "not_supported"

        min_bytes = int(float(min_working_set_gb) * 1024 * 1024 * 1024)
        start = time.time()
        last_log_t = 0.0
        last_ws = None

        while (time.time() - start) < float(max_wait_seconds):
            if not self._is_scumserver_process_running():
                last_ws = None
            else:
                ws = self._get_scumserver_working_set_bytes()
                last_ws = ws
                if isinstance(ws, int) and ws >= min_bytes:
                    return True, f"ready (working_set_gb={ws / (1024**3):.2f})"

            now = time.time()
            if (now - last_log_t) >= 15.0:
                last_log_t = now
                if last_ws is None:
                    self.logger.info(
                        "[SCUM_READY] Aguardando SCUMServer.exe iniciar e atingir uso de RAM..."
                    )
                else:
                    self.logger.info(
                        f"[SCUM_READY] SCUMServer.exe ainda carregando (working_set_gb={last_ws / (1024**3):.2f}, min_gb={min_working_set_gb:.2f})"
                    )
            time.sleep(float(check_interval_seconds))

        if last_ws is None:
            return False, "timeout_waiting_process"
        return False, f"timeout_waiting_memory (working_set_gb={last_ws / (1024**3):.2f}, min_gb={min_working_set_gb:.2f})"

    def apply_nssm_shutdown_preset(
        self,
        *,
        console_timeout_ms: int = 120000,
        enable_window_close: bool = False,
        window_close_timeout_ms: int = 1500,
        enable_thread_quit: bool = False,
        thread_quit_timeout_ms: int = 1500,
        enable_terminate: bool = False,
        terminate_timeout_ms: int = 300000,
    ) -> Dict[str, Any]:
        """Apply a recommended graceful shutdown configuration to the NSSM service.

        This requires admin privileges (UAC) on Windows.
        """
        try:
            if sys.platform != "win32":
                return {
                    "success": False,
                    "message": "Configuração NSSM suportada apenas no Windows",
                    "status": "not_supported",
                }

            if not os.path.exists(self.nssm_path):
                return {
                    "success": False,
                    "message": f"NSSM não encontrado em: {self.nssm_path}",
                    "status": "nssm_not_found",
                }

            def _b(v: bool) -> int:
                return 1 if bool(v) else 0

            console_timeout_ms = int(max(0, int(console_timeout_ms)))
            window_close_timeout_ms = int(max(0, int(window_close_timeout_ms)))
            thread_quit_timeout_ms = int(max(0, int(thread_quit_timeout_ms)))
            terminate_timeout_ms = int(max(0, int(terminate_timeout_ms)))

            service = str(self.service_name)
            nssm = str(self.nssm_path)

            def _is_admin() -> bool:
                try:
                    return bool(ctypes.windll.shell32.IsUserAnAdmin())
                except Exception:
                    return False

            def _nssm_get(param: str) -> str:
                rc, out = _nssm_get_raw(param)
                return out

            def _nssm_get_raw(param: str) -> Tuple[int, str]:
                try:
                    r = subprocess.run(
                        [nssm, "get", service, param],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                        ),
                    )
                    rc = int(r.returncode or 0)
                    out = (r.stdout or "").strip()
                    err = (r.stderr or "").strip()
                    # On success, NSSM writes the value to stdout.
                    # On failure, it usually writes an error to stderr.
                    if rc == 0:
                        return rc, out or err
                    return rc, err or out
                except Exception:
                    return 1, ""

            def _normalize_get_value(raw: str) -> str:
                # nssm get usually returns a single value line.
                # Be defensive and only compare the first non-empty line/token.
                if not raw:
                    return ""
                lines = [ln.strip() for ln in str(raw).splitlines() if ln.strip()]
                if not lines:
                    return ""
                first = lines[0]
                # Some outputs may include extra tokens; keep the first token.
                return first.split()[0].strip()

            def _param_supported(param: str) -> bool:
                rc, _out = _nssm_get_raw(param)
                return rc == 0

            # NSSM versions differ:
            # - Newer: AppStopMethodConsoleTimeout/AppStopMethodWindowTimeout/... exist
            # - Older (incl. 2.24): timeout is stored in AppStopMethodConsole/Window/Threads directly (ms); 0 disables.
            supports_console_timeout = _param_supported("AppStopMethodConsoleTimeout")
            supports_window_timeout = _param_supported("AppStopMethodWindowTimeout")
            supports_threads_timeout = _param_supported("AppStopMethodThreadsTimeout")
            supports_terminate = _param_supported("AppStopMethodTerminate")
            supports_stop_skip = _param_supported("AppStopMethodSkip")
            legacy_mode = not supports_console_timeout

            def _readback() -> Dict[str, str]:
                rb = {
                    "AppStopMethodConsole": _normalize_get_value(
                        _nssm_get("AppStopMethodConsole")
                    ),
                    "AppStopMethodWindow": _normalize_get_value(
                        _nssm_get("AppStopMethodWindow")
                    ),
                    "AppStopMethodThreads": _normalize_get_value(
                        _nssm_get("AppStopMethodThreads")
                    ),
                }
                if supports_stop_skip:
                    rb["AppStopMethodSkip"] = _normalize_get_value(
                        _nssm_get("AppStopMethodSkip")
                    )
                if supports_console_timeout:
                    rb["AppStopMethodConsoleTimeout"] = _nssm_get(
                        "AppStopMethodConsoleTimeout"
                    )
                if supports_window_timeout:
                    rb["AppStopMethodWindowTimeout"] = _nssm_get("AppStopMethodWindowTimeout")
                if supports_threads_timeout:
                    rb["AppStopMethodThreadsTimeout"] = _nssm_get(
                        "AppStopMethodThreadsTimeout"
                    )
                if supports_terminate:
                    rb["AppStopMethodTerminate"] = _nssm_get("AppStopMethodTerminate")
                    if _param_supported("AppStopMethodTerminateTimeout"):
                        rb["AppStopMethodTerminateTimeout"] = _nssm_get(
                            "AppStopMethodTerminateTimeout"
                        )
                return rb

            if supports_console_timeout:
                expected = {
                    "AppStopMethodConsole": "1",
                    "AppStopMethodConsoleTimeout": str(console_timeout_ms),
                    "AppStopMethodWindow": str(_b(enable_window_close)),
                    "AppStopMethodWindowTimeout": str(
                        window_close_timeout_ms if enable_window_close else 0
                    ),
                    "AppStopMethodThreads": str(_b(enable_thread_quit)),
                    "AppStopMethodThreadsTimeout": str(
                        thread_quit_timeout_ms if enable_thread_quit else 0
                    ),
                }
                if supports_terminate and _param_supported("AppStopMethodTerminateTimeout"):
                    expected["AppStopMethodTerminate"] = str(_b(enable_terminate))
                    expected["AppStopMethodTerminateTimeout"] = str(terminate_timeout_ms)
                elif supports_terminate:
                    expected["AppStopMethodTerminate"] = str(_b(enable_terminate))
            else:
                # Legacy mode: values are timeouts (ms). 0 disables.
                expected = {
                    "AppStopMethodConsole": str(console_timeout_ms),
                    "AppStopMethodWindow": str(
                        window_close_timeout_ms if enable_window_close else 0
                    ),
                    "AppStopMethodThreads": str(
                        thread_quit_timeout_ms if enable_thread_quit else 0
                    ),
                }
                # Prefer actually disabling methods via AppStopMethodSkip when available.
                # Bitmask (NSSM): 1=Console, 2=Window, 4=Threads, 8=Terminate.
                # We want Console enabled, and disable Window/Threads/Terminate.
                if supports_stop_skip:
                    expected["AppStopMethodSkip"] = "14"

            def _mismatches(readback: Dict[str, str]) -> Dict[str, Dict[str, str]]:
                mism: Dict[str, Dict[str, str]] = {}
                for k, v in expected.items():
                    rb = str(readback.get(k, "")).strip()
                    # NSSM 2.24 quirk: some installations report AppStopMethodConsole as "1" (enabled)
                    # even when the GUI shows the configured timeout. In legacy mode, accept "1".
                    if (
                        legacy_mode
                        and k == "AppStopMethodConsole"
                        and rb == "1"
                        and str(v).strip().isdigit()
                    ):
                        continue
                    if rb != str(v).strip():
                        mism[k] = {"expected": str(v), "readback": rb}
                return mism

            def _verify_with_retries() -> Tuple[Dict[str, str], Dict[str, Dict[str, str]]]:
                # In some NSSM setups, values may not be immediately visible after `set`.
                last_rb: Dict[str, str] = {}
                last_mism: Dict[str, Dict[str, str]] = {}
                for _ in range(20):
                    last_rb = _readback()
                    last_mism = _mismatches(last_rb)
                    if not last_mism:
                        break
                    time.sleep(0.5)
                return last_rb, last_mism

            def _raw_debug_for(keys) -> Dict[str, Any]:
                dbg: Dict[str, Any] = {}
                for k in keys:
                    try:
                        r = subprocess.run(
                            [nssm, "get", service, k],
                            capture_output=True,
                            text=True,
                            timeout=10,
                            creationflags=(
                                subprocess.CREATE_NO_WINDOW
                                if sys.platform == "win32"
                                else 0
                            ),
                        )
                        dbg[k] = {
                            "rc": int(r.returncode or 0),
                            "stdout": (r.stdout or "")[:500],
                            "stderr": (r.stderr or "")[:500],
                        }
                    except Exception as e:
                        dbg[k] = {"error": str(e)}
                return dbg

            # Prefer direct NSSM execution if we are already admin.
            if _is_admin():
                try:
                    self.logger.info(
                        "[NSSM] Aplicando preset (modo admin direto, sem PowerShell)..."
                    )
                except Exception:
                    pass

                if supports_console_timeout:
                    direct_cmds = [
                        [nssm, "set", service, "AppStopMethodConsole", "1"],
                        [
                            nssm,
                            "set",
                            service,
                            "AppStopMethodConsoleTimeout",
                            str(console_timeout_ms),
                        ],
                        [
                            nssm,
                            "set",
                            service,
                            "AppStopMethodWindow",
                            str(_b(enable_window_close)),
                        ],
                        [
                            nssm,
                            "set",
                            service,
                            "AppStopMethodWindowTimeout",
                            str(window_close_timeout_ms if enable_window_close else 0),
                        ],
                        [
                            nssm,
                            "set",
                            service,
                            "AppStopMethodThreads",
                            str(_b(enable_thread_quit)),
                        ],
                        [
                            nssm,
                            "set",
                            service,
                            "AppStopMethodThreadsTimeout",
                            str(thread_quit_timeout_ms if enable_thread_quit else 0),
                        ],
                    ]
                    if supports_terminate:
                        direct_cmds.append(
                            [
                                nssm,
                                "set",
                                service,
                                "AppStopMethodTerminate",
                                str(_b(enable_terminate)),
                            ]
                        )
                        if _param_supported("AppStopMethodTerminateTimeout"):
                            direct_cmds.append(
                                [
                                    nssm,
                                    "set",
                                    service,
                                    "AppStopMethodTerminateTimeout",
                                    str(terminate_timeout_ms),
                                ]
                            )
                else:
                    direct_cmds = [
                        [
                            nssm,
                            "set",
                            service,
                            "AppStopMethodConsole",
                            str(console_timeout_ms),
                        ],
                        [
                            nssm,
                            "set",
                            service,
                            "AppStopMethodWindow",
                            str(window_close_timeout_ms if enable_window_close else 0),
                        ],
                        [
                            nssm,
                            "set",
                            service,
                            "AppStopMethodThreads",
                            str(thread_quit_timeout_ms if enable_thread_quit else 0),
                        ],
                    ]
                    if supports_stop_skip:
                        direct_cmds.append(
                            [nssm, "set", service, "AppStopMethodSkip", "14"]
                        )

                outputs = []
                for cmd in direct_cmds:
                    r = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW
                            if sys.platform == "win32"
                            else 0
                        ),
                    )
                    outputs.append(((r.stdout or "") + "\n" + (r.stderr or "")).strip())
                    if int(r.returncode or 0) != 0:
                        rb = _readback()
                        return {
                            "success": False,
                            "message": "Falha ao aplicar preset do NSSM (modo admin direto).",
                            "status": "failed_direct",
                            "returncode": int(r.returncode or 0),
                            "output": "\n\n".join(o for o in outputs if o)[:2000],
                            "readback": rb,
                            "mismatches": _mismatches(rb),
                        }

                rb = _readback()
                rb, mism = _verify_with_retries()
                if mism:
                    return {
                        "success": False,
                        "message": "Preset executou, mas as configurações não foram aplicadas no NSSM.",
                        "status": "not_applied",
                        "output": "\n\n".join(o for o in outputs if o)[:2000],
                        "readback": rb,
                        "mismatches": mism,
                        "debug_raw": _raw_debug_for(expected.keys()),
                    }

                return {
                    "success": True,
                    "message": "Preset do NSSM aplicado com sucesso",
                    "status": "ok",
                    "output": "\n\n".join(o for o in outputs if o)[:2000],
                    "readback": rb,
                }

            # Run an elevated PowerShell with -EncodedCommand to avoid quoting issues.
            # Note: legacy NSSM doesn't support *Timeout parameters.
            ps_window_timeout = window_close_timeout_ms if enable_window_close else 0
            ps_threads_timeout = thread_quit_timeout_ms if enable_thread_quit else 0
            ps_inner = "\n".join(
                [
                    "$ErrorActionPreference = 'Stop'",
                    (
                        f"& '{nssm}' set {service} AppStopMethodConsole 1; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodConsole failed' }}"
                        if supports_console_timeout
                        else f"& '{nssm}' set {service} AppStopMethodConsole {console_timeout_ms}; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodConsole failed' }}"
                    ),
                    (
                        f"& '{nssm}' set {service} AppStopMethodConsoleTimeout {console_timeout_ms}; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodConsoleTimeout failed' }}"
                        if supports_console_timeout
                        else "$null = $null"
                    ),
                    (
                        f"& '{nssm}' set {service} AppStopMethodWindow {_b(enable_window_close)}; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodWindow failed' }}"
                        if supports_console_timeout
                        else f"& '{nssm}' set {service} AppStopMethodWindow {(window_close_timeout_ms if enable_window_close else 0)}; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodWindow failed' }}"
                    ),
                    (
                        f"& '{nssm}' set {service} AppStopMethodWindowTimeout {ps_window_timeout}; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodWindowTimeout failed' }}"
                        if supports_window_timeout
                        else "$null = $null"
                    ),
                    (
                        f"& '{nssm}' set {service} AppStopMethodThreads {_b(enable_thread_quit)}; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodThreads failed' }}"
                        if supports_console_timeout
                        else f"& '{nssm}' set {service} AppStopMethodThreads {(thread_quit_timeout_ms if enable_thread_quit else 0)}; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodThreads failed' }}"
                    ),
                    (
                        f"& '{nssm}' set {service} AppStopMethodThreadsTimeout {ps_threads_timeout}; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodThreadsTimeout failed' }}"
                        if supports_threads_timeout
                        else "$null = $null"
                    ),
                    (
                        f"& '{nssm}' set {service} AppStopMethodSkip 14; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodSkip failed' }}"
                        if (not supports_console_timeout and supports_stop_skip)
                        else "$null = $null"
                    ),
                    (
                        f"& '{nssm}' set {service} AppStopMethodTerminate {_b(enable_terminate)}; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodTerminate failed' }}"
                        if supports_terminate
                        else "$null = $null"
                    ),
                    (
                        f"& '{nssm}' set {service} AppStopMethodTerminateTimeout {terminate_timeout_ms}; if ($LASTEXITCODE -ne 0) {{ throw 'set AppStopMethodTerminateTimeout failed' }}"
                        if supports_terminate and _param_supported("AppStopMethodTerminateTimeout")
                        else "$null = $null"
                    ),
                    "exit 0",
                ]
            )

            import base64

            encoded = base64.b64encode(ps_inner.encode("utf-16le")).decode("ascii")
            ps_cmd = (
                "Start-Process -FilePath 'powershell' "
                "-ArgumentList '-NoProfile -ExecutionPolicy Bypass -EncodedCommand "
                + encoded
                + "' -Verb RunAs -WindowStyle Hidden -Wait -PassThru | ForEach-Object { exit $_.ExitCode }"
            )

            self.logger.info(
                "[NSSM] Aplicando preset de shutdown gracioso (pode solicitar UAC)...",
                {
                    "console_timeout_ms": console_timeout_ms,
                    "enable_terminate": bool(enable_terminate),
                    "terminate_timeout_ms": terminate_timeout_ms,
                },
            )

            res = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=180,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )

            out = ((res.stdout or "") + "\n" + (res.stderr or "")).strip()

            readback, mismatches = _verify_with_retries()

            if int(res.returncode or 0) != 0:
                return {
                    "success": False,
                    "message": "Falha ao aplicar preset do NSSM (processo elevado retornou erro).",
                    "status": "failed",
                    "returncode": int(res.returncode or 0),
                    "output": out[:2000],
                    "readback": readback,
                    "mismatches": mismatches,
                }

            if mismatches:
                return {
                    "success": False,
                    "message": "Preset executou, mas as configurações não foram aplicadas no NSSM (verifique permissões/UAC).",
                    "status": "not_applied",
                    "output": out[:2000],
                    "readback": readback,
                    "mismatches": mismatches,
                    "debug_raw": _raw_debug_for(expected.keys()),
                }

            return {
                "success": True,
                "message": "Preset do NSSM aplicado com sucesso",
                "status": "ok",
                "output": out[:2000],
                "readback": readback,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Timeout ao aplicar preset do NSSM (provável UAC pendente ou travado)",
                "status": "timeout",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Erro ao aplicar preset do NSSM: {e}",
                "status": "error",
            }

    def start_server(self, scum_db_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Iniciar servidor SCUM (substitui start.bat)

        Args:
            scum_db_path: Caminho opcional para SCUM.db (se não fornecido, tenta obter automaticamente)
        """
        try:
            self.logger.info("=" * 40)
            self.logger.info("INICIANDO SERVIDOR SCUM (SERVICO NSSM)")
            self.logger.info("=" * 40)

            # Verificar se o serviço já está rodando
            if self._is_service_running():
                self.logger.error("ERRO: O serviço SCUMServer já está rodando!")
                self.logger.info("Para reiniciar, use o comando restart.")
                return {
                    "success": False,
                    "message": "Serviço já está rodando",
                    "status": "already_running",
                }

            self.logger.info("Serviço não está rodando. Prosseguindo...")

            # Verificar e limpar arquivos WAL/SHM antes de iniciar (se servidor está parado)
            # IMPORTANTE: Esta verificação não deve bloquear o start do servidor
            if not self._is_service_running():
                try:
                    from utils.scum_db_cleanup import cleanup_scum_db_wal_files

                    # Obter caminho do SCUM.db se não foi fornecido
                    if not scum_db_path:
                        # Tentar usar fallbacks diretos
                        scum_db_path = (
                            self.config.get("weather_scheduler", {}).get("scum_db_path")
                            or self.config.get("fishing_ranking", {}).get(
                                "scum_db_path"
                            )
                            or "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
                        )

                    # Verificar se arquivos WAL/SHM existem
                    wal_path = f"{scum_db_path}-wal"
                    shm_path = f"{scum_db_path}-shm"

                    wal_exists = os.path.exists(wal_path) if scum_db_path else False
                    shm_exists = os.path.exists(shm_path) if scum_db_path else False

                    if wal_exists or shm_exists:
                        self.logger.warn(
                            "Arquivos WAL/SHM encontrados antes de iniciar. Removendo para evitar duplicação de itens..."
                        )

                        try:
                            # Registrar ScumDbSharedCopyManager para fechar conexões antes de limpar
                            try:
                                from utils.scum_db_cleanup import (
                                    set_shared_copy_manager,
                                )
                                from utils.scum_db_shared_copy import (
                                    get_shared_copy_manager,
                                )

                                shared_copy_mgr = get_shared_copy_manager()
                                if shared_copy_mgr:
                                    set_shared_copy_manager(shared_copy_mgr)
                            except Exception as e:
                                self.logger.warn(
                                    f"Erro ao registrar ScumDbSharedCopyManager: {e}"
                                )

                            # Tentar limpeza via função de cleanup primeiro
                            from utils.scum_db_cleanup import cleanup_scum_db_wal_files

                            # Limpar WAL/SHM com tempo fixo (backend deve funcionar perfeitamente 24/7)
                            cleanup_result = cleanup_scum_db_wal_files(
                                self,
                                scum_db_path,
                                self.logger,
                                wait_after_stop=0,  # Servidor já está parado
                                wait_after_close=1.0,  # Tempo fixo apropriado
                            )

                            # Verificar novamente e remover forçadamente se ainda existirem
                            wal_exists = os.path.exists(wal_path)
                            shm_exists = os.path.exists(shm_path)

                            if wal_exists or shm_exists:
                                self.logger.warn(
                                    "Arquivos WAL/SHM ainda existem após cleanup. Removendo forçadamente..."
                                )
                                try:
                                    if wal_exists:
                                        os.remove(wal_path)
                                        self.logger.info(
                                            f"Arquivo WAL removido forçadamente: {wal_path}"
                                        )
                                    if shm_exists:
                                        os.remove(shm_path)
                                        self.logger.info(
                                            f"Arquivo SHM removido forçadamente: {shm_path}"
                                        )

                                    # Aguardar 5 segundos após remover (conforme solicitado)
                                    self.logger.info(
                                        "Aguardando 5 segundos após remover arquivos WAL/SHM antes de iniciar..."
                                    )
                                    time.sleep(5)
                                except Exception as e:
                                    self.logger.error(
                                        f"Erro ao remover arquivos WAL/SHM forçadamente: {e}"
                                    )
                                    # Continuar mesmo se falhar, mas avisar
                            else:
                                if cleanup_result.get("success"):
                                    self.logger.info(
                                        f"Limpeza de WAL/SHM antes de iniciar: {cleanup_result.get('message')}"
                                    )
                                else:
                                    self.logger.warn(
                                        f"Limpeza de WAL/SHM antes de iniciar: {cleanup_result.get('message')}"
                                    )
                                # Aguardar um pouco após limpeza
                                time.sleep(2)
                        except Exception as cleanup_error:
                            self.logger.error(
                                f"Erro durante limpeza de WAL/SHM: {cleanup_error}"
                            )
                            # Tentar remoção direta como fallback
                            try:
                                if os.path.exists(wal_path):
                                    os.remove(wal_path)
                                    self.logger.info(
                                        f"Arquivo WAL removido via fallback: {wal_path}"
                                    )
                                if os.path.exists(shm_path):
                                    os.remove(shm_path)
                                    self.logger.info(
                                        f"Arquivo SHM removido via fallback: {shm_path}"
                                    )
                            except Exception as fallback_error:
                                self.logger.error(
                                    f"Erro no fallback de remoção: {fallback_error}"
                                )
                    else:
                        self.logger.info(
                            "Nenhum arquivo WAL/SHM encontrado - seguro para iniciar"
                        )
                except Exception as e:
                    import traceback

                    self.logger.error(
                        f"Erro ao verificar/limpar arquivos WAL/SHM antes de iniciar: {e}"
                    )
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    # Continuar mesmo se falhar - não deve bloquear o start
                    self.logger.warn(
                        "Continuando com o start do servidor apesar do erro na limpeza de WAL/SHM"
                    )

            # 1. Atualização Steam
            steam_result = self._update_steam()
            if not steam_result["success"]:
                return steam_result

            # Iniciar serviço via NSSM (ÚNICO MÉTODO)
            start_result = self._start_service_nssm()
            if start_result["success"]:
                return self._verify_startup()

            # Se NSSM falhou, retornar erro imediatamente (SEM FALLBACKS)
            error_status = start_result.get("status", "unknown")
            error_message = start_result.get("message", "Erro desconhecido")
            self.logger.error(f"Falha ao iniciar serviço via NSSM: {error_message}")
            return {
                "success": False,
                "message": f"Falha ao iniciar serviço via NSSM: {error_message}",
                "status": error_status,
                "nssm_path": self.nssm_path,
            }

        except Exception as e:
            self.logger.error(f"Erro inesperado ao iniciar servidor: {e}")
            return {
                "success": False,
                "message": f"Erro inesperado: {str(e)}",
                "status": "error",
            }

    def stop_server(
        self,
        scum_db_path: Optional[str] = None,
        elevated_users_manager=None,
        restart_cycle_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parar servidor SCUM (substitui stop.bat)

        Args:
            scum_db_path: Caminho opcional para SCUM.db (se não fornecido, tenta obter automaticamente)
            elevated_users_manager: Instância opcional do ElevatedUsersManager para sincronização
        """
        try:
            self.logger.info("=" * 40)
            self.logger.info("PARANDO SERVIDOR SCUM (SERVICO NSSM)")
            self.logger.info("=" * 40)

            # Verificar se o serviço está rodando
            if not self._is_service_running():
                self.logger.info("O serviço SCUMServer não está rodando.")
                self.logger.info("Nada a fazer.")
                return {
                    "success": True,
                    "message": "Serviço não estava rodando",
                    "status": "not_running",
                }

            self.logger.info("Serviço está rodando. Iniciando parada...")

            # Parar via NSSM (ÚNICO MÉTODO)
            stop_result = self._stop_service_nssm()
            if stop_result["success"]:
                return self._verify_stop(
                    scum_db_path=scum_db_path,
                    elevated_users_manager=elevated_users_manager,
                    restart_cycle_id=restart_cycle_id,
                )

            # Se NSSM falhou, retornar erro imediatamente (SEM FALLBACKS)
            error_status = stop_result.get("status", "unknown")
            error_message = stop_result.get("message", "Erro desconhecido")
            self.logger.error(f"Falha ao parar serviço via NSSM: {error_message}")
            return {
                "success": False,
                "message": f"Falha ao parar serviço via NSSM: {error_message}",
                "status": error_status,
                "nssm_path": self.nssm_path,
            }

        except Exception as e:
            self.logger.error(f"Erro inesperado ao parar servidor: {e}")
            return {
                "success": False,
                "message": f"Erro inesperado: {str(e)}",
                "status": "error",
            }

    def _acquire_restart_lock(self) -> Tuple[bool, str]:
        """
        Adquirir lock de restart (prevenir múltiplos restarts simultâneos)
        
        Returns:
            Tuple[sucesso, mensagem] onde sucesso indica se conseguiu adquirir o lock
        """
        # Tentar adquirir lock em memória (rápido)
        if not self._restart_lock.acquire(blocking=False):
            return False, "Restart já está em andamento (lock em memória)"
        
        # Verificar lock em arquivo (backup, sobrevive a crashes)
        try:
            # Criar diretório de lock se não existir
            lock_dir = Path("data") / "temp"
            lock_dir.mkdir(parents=True, exist_ok=True)
            
            self._restart_lock_file = lock_dir / "restart_in_progress.lock"
            
            # Verificar se lock file existe e se processo ainda está ativo
            if self._restart_lock_file.exists():
                try:
                    pid = int(self._restart_lock_file.read_text().strip())
                    # Verificar se processo ainda está rodando
                    if sys.platform == "win32":
                        import psutil
                        if psutil.pid_exists(pid):
                            # Processo ainda está rodando - lock válido
                            self._restart_lock.release()  # Liberar lock em memória
                            return False, f"Restart já está em andamento (processo {pid} ainda ativo)"
                        else:
                            # Processo morreu - remover lock órfão
                            self._restart_lock_file.unlink()
                    else:
                        # Linux/Unix - verificar se processo existe
                        try:
                            os.kill(pid, 0)  # Signal 0 apenas verifica existência
                            self._restart_lock.release()
                            return False, f"Restart já está em andamento (processo {pid} ainda ativo)"
                        except OSError:
                            # Processo não existe - remover lock órfão
                            try:
                                self._restart_lock_file.unlink()
                            except Exception:
                                pass
                except Exception:
                    # Lock file corrompido/ilegível - remover e seguir
                    try:
                        self._restart_lock_file.unlink()
                    except Exception:
                        pass
            
            # Criar lock file com PID do processo atual
            self._restart_lock_file.write_text(str(os.getpid()))
            self._restart_in_progress = True
            
            return True, "Lock adquirido com sucesso"
            
        except Exception as e:
            # Se falhar ao criar lock file, ainda usar lock em memória
            self.logger.warn(f"Erro ao criar lock file: {e} - usando apenas lock em memória")
            return True, "Lock adquirido (apenas em memória)"
    
    def _release_restart_lock(self):
        """Liberar lock de restart"""
        try:
            self._restart_in_progress = False
            
            # Remover lock file se existir
            if self._restart_lock_file and self._restart_lock_file.exists():
                try:
                    self._restart_lock_file.unlink()
                except Exception as e:
                    self.logger.warn(f"Erro ao remover lock file: {e}")
            
            # Liberar lock em memória
            if self._restart_lock.locked():
                self._restart_lock.release()
                
        except Exception as e:
            self.logger.error(f"Erro ao liberar lock de restart: {e}")

    def restart_server(
        self, scum_db_path: Optional[str] = None, elevated_users_manager=None
    ) -> Dict[str, Any]:
        """
        Reiniciar servidor SCUM com retry automático, verificações de segurança e timeout máximo

        Args:
            scum_db_path: Caminho opcional para SCUM.db (se não fornecido, tenta obter automaticamente)
            elevated_users_manager: Instância opcional do ElevatedUsersManager para sincronização

        Returns:
            Dict com resultado do restart incluindo status, mensagem e metadados
        """
        # SEGURANÇA: Verificar e adquirir lock de concorrência
        lock_acquired, lock_msg = self._acquire_restart_lock()
        if not lock_acquired:
            self.logger.warn(f"Restart rejeitado: {lock_msg}")
            return {
                "success": False,
                "message": lock_msg,
                "status": "restart_in_progress",
                "note": "Aguarde o restart atual terminar antes de tentar novamente"
            }
        
        restart_start_time = time.time()
        max_restart_timeout = 300  # 5 minutos timeout máximo para todo o processo (inclui wait de readiness)

        restart_cycle_id = (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            + "_"
            + str(os.getpid())
            + "_"
            + uuid.uuid4().hex[:8]
        )

        restart_ready = False

        try:
            try:
                from utils.restart_guard import set_restart_active

                set_restart_active(True, restart_cycle_id=restart_cycle_id)
            except Exception:
                pass

            nssm_shutdown_result = None
            # Durante o restart, pausar leituras do SCUM.db via ScumDbSharedCopyManager
            # para evitar que o próprio backend segure handles no SCUM.db enquanto o serviço para/inicia.
            shared_copy_mgr = None
            try:
                from utils.scum_db_shared_copy import get_shared_copy_manager

                shared_copy_mgr = get_shared_copy_manager()
                if shared_copy_mgr:
                    pause_s = getattr(shared_copy_mgr, "restart_pause_seconds", 120) or 120
                    shared_copy_mgr.pause_for(
                        pause_s,
                        reason="SCUMServer restart window (stop/start)",
                    )
            except Exception as e:
                self.logger.warn(f"[SCUM_DB] Falha ao pausar shared copy manager: {e}")

            self.logger.info("=" * 40)
            self.logger.info("REINICIANDO SERVIDOR SCUM (SERVICO NSSM)")
            self.logger.info("=" * 40)
            self.logger.info(
                f"Timeout máximo configurado: {max_restart_timeout} segundos"
            )
            self.logger.info(f"Lock de restart adquirido: {lock_msg}")
            self.logger.info(f"Restart cycle id: {restart_cycle_id}")

            # Verificar timeout antes de começar
            if (time.time() - restart_start_time) >= max_restart_timeout:
                return {
                    "success": False,
                    "message": "Timeout máximo atingido antes de iniciar processo",
                    "status": "timeout_before_start",
                }

            # Parar servidor (já faz limpeza de WAL/SHM e sync de elevated users internamente)
            stop_result = self.stop_server(
                scum_db_path=scum_db_path,
                elevated_users_manager=elevated_users_manager,
                restart_cycle_id=restart_cycle_id,
            )

            try:
                if isinstance(stop_result, dict) and stop_result.get("nssm_shutdown_result") is not None:
                    nssm_shutdown_result = stop_result.get("nssm_shutdown_result")
            except Exception:
                pass

            # Verificar timeout após parada
            elapsed = time.time() - restart_start_time
            if elapsed >= max_restart_timeout:
                return {
                    "success": False,
                    "message": f"Timeout máximo atingido após parar servidor ({elapsed:.1f}s)",
                    "status": "timeout_after_stop",
                    "stop_result": stop_result,
                }

            if not stop_result["success"] and stop_result["status"] != "not_running":
                return {
                    "success": False,
                    "message": f"Erro ao parar servidor: {stop_result['message']}",
                    "status": "stop_failed",
                    "elapsed_seconds": elapsed,
                }

            # Obter caminho do SCUM.db se não foi fornecido
            if not scum_db_path:
                scum_db_path = (
                    self.config.get("weather_scheduler", {}).get("scum_db_path")
                    or self.config.get("fishing_ranking", {}).get("scum_db_path")
                    or "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
                )

            # Se há elevated_users_manager, aguardar tempo maior (já feito no stop_server)
            # Mas vamos aguardar um pouco adicional para garantir que tudo esteja pronto
            if elevated_users_manager:
                self.logger.info(
                    "Aguardando tempo adicional para garantir que tudo esteja pronto..."
                )
                time.sleep(5)  # Pequeno delay adicional

            # Aguardar até que serviço esteja completamente parado usando método melhorado
            self.logger.info(
                "Aguardando confirmação de que serviço está completamente parado..."
            )
            stopped_success, stopped_msg = self._wait_for_service_stopped(
                max_wait_seconds=30, initial_wait=2.0
            )

            if not stopped_success:
                self.logger.warn(
                    f"Serviço pode não estar completamente parado: {stopped_msg}"
                )
                # Continuar mesmo assim - pode ser que o estado esteja transitório

            # Aguardar tempo fixo para Windows liberar recursos do serviço
            # Backend deve funcionar perfeitamente 24/7, então usamos tempo fixo apropriado
            wait_time = 5
            self.logger.info(
                f"Aguardando {wait_time} segundos para Windows liberar recursos do serviço..."
            )
            time.sleep(wait_time)

            # Aguardar o processo SCUMServer.exe encerrar (quando o serviço já está STOPPED)
            try:
                proc_wait_start = time.time()
                proc_max_wait = 20
                last_log_t = 0.0
                while (time.time() - proc_wait_start) < proc_max_wait:
                    if not self._is_scumserver_process_running():
                        elapsed = time.time() - proc_wait_start
                        self.logger.info(
                            f"[SCUM_PROCESS] SCUMServer.exe encerrou após {elapsed:.1f}s"
                        )
                        break
                    now = time.time()
                    if (now - last_log_t) >= 5.0:
                        last_log_t = now
                        self.logger.warn(
                            "[SCUM_PROCESS] SCUMServer.exe ainda está rodando após STOPPED. Aguardando encerrar..."
                        )
                    time.sleep(1.0)

                if self._is_scumserver_process_running():
                    self.logger.warn(
                        f"[SCUM_PROCESS] SCUMServer.exe ainda está rodando após {proc_max_wait}s de espera. Prosseguindo para checagem do SCUM.db/kill fallback."
                    )
            except Exception as e:
                self.logger.warn(f"[SCUM_PROCESS] Falha ao verificar processo SCUMServer.exe: {e}")

            # Garantir que o SCUM.db esteja realmente livre antes de QUALQUER escrita offline.
            scum_db_unlocked = True
            try:
                # O SCUM pode continuar finalizando por um tempo mesmo após o serviço entrar em STOPPED.
                # Se matarmos o processo cedo demais, o SCUM não completa o shutdown (logs ficam "curtos").
                # Portanto, aguardar mais tempo antes de considerar kill forçado.
                self.logger.info(
                    f"[SCUM_DB] Aguardando SCUM.db destravar antes de processar entregas offline (timeout=180s)"
                )
                self._wait_for_scum_db_unlocked(scum_db_path, max_wait_seconds=180)
            except Exception as e:
                scum_db_unlocked = False
                self.logger.warn(
                    f"[SCUM_DB] SCUM.db ainda parece bloqueado após stop - tentando finalizar processos remanescentes do SCUMServer.exe: {e}"
                )
                try:
                    self.logger.warn(
                        "[SCUM_DB] Kill forçado do SCUMServer.exe será tentado para destravar SCUM.db (isso pode interromper o shutdown gracioso)."
                    )
                    killed = self._force_kill_scumserver_processes()
                    if killed:
                        # Após kill forçado, aguardar um pouco e re-checar lock
                        time.sleep(2)
                        self._wait_for_scum_db_unlocked(scum_db_path, max_wait_seconds=15)
                        scum_db_unlocked = True
                        self.logger.info(
                            "[SCUM_DB] SCUM.db destravado após kill forçado de processo remanescente."
                        )
                except Exception as kill_e:
                    self.logger.warn(
                        f"[SCUM_DB] Ainda bloqueado após tentativa de kill forçado: {kill_e}"
                    )

            # Executar entregas OFFLINE (shop + veículos) na janela offline (servidor parado)
            try:
                if self._is_service_running():
                    self.logger.warn(
                        "[OFFLINE_JOBS] Serviço ainda aparenta estar rodando - pulando processamento offline"
                    )
                elif not scum_db_unlocked:
                    self.logger.warn(
                        "[OFFLINE_JOBS] SCUM.db está bloqueado - pulping processamento offline (shop + veículos)"
                    )
                else:
                    try:
                        from utils.restart_guard import allow_scum_db_access
                    except Exception:
                        allow_scum_db_access = None

                    try:
                        if self.path_helper:
                            ssm_db_path = self.path_helper.get_ssm_db_path()
                        else:
                            ssm_db_path = "data/SSM.db"
                    except Exception:
                        ssm_db_path = "data/SSM.db"

                    if allow_scum_db_access:
                        with allow_scum_db_access("ServerManager offline jobs (shop+vehicles)"):
                            # 1) SHOP (itens) - escreve no SCUM.db, então somente offline
                            try:
                                if hasattr(self, "shop_service") and self.shop_service:
                                    self.logger.info(
                                        "[OFFLINE_JOBS] Processando entregas de shop pendentes..."
                                    )
                                    try:
                                        # Inicializar serviço com caminhos corretos
                                        from core.shop.delivery_service import ShopDeliveryService

                                        delivery_service = ShopDeliveryService(
                                            ssm_db_path=ssm_db_path,
                                            scum_db_path=scum_db_path,
                                            logger=self.logger,
                                        )
                                        delivery_result = (
                                            delivery_service.run_once()
                                        )
                                        self.logger.info(
                                            f"[OFFLINE_JOBS] Shop deliveries processadas: {delivery_result}"
                                        )
                                    except Exception as e:
                                        self.logger.error(
                                            f"[OFFLINE_JOBS] Erro ao processar entregas de shop: {e}"
                                        )
                                else:
                                    self.logger.info(
                                        "[OFFLINE_JOBS] shop_service não disponível - pulando entregas"
                                    )
                            except Exception as e:
                                self.logger.error(
                                    f"[OFFLINE_JOBS] Erro no bloco de shop: {e}"
                                )

                            # 2) VEÍCULOS - escreve no SCUM.db, então somente offline
                            try:
                                self._process_vehicle_orders_offline(
                                    scum_db_path, ssm_db_path
                                )
                            except Exception as e:
                                self.logger.error(
                                    f"[OFFLINE_JOBS] Erro ao processar pedidos de veículos offline: {e}"
                                )

                            # 3) BASE UPGRADES - escreve no SCUM.db, então somente offline
                            try:
                                self._process_base_upgrades_offline(
                                    scum_db_path, ssm_db_path
                                )
                            except Exception as e:
                                self.logger.error(
                                    f"[OFFLINE_JOBS] Erro ao processar upgrades de base offline: {e}"
                                )
                    else:
                        # Fallback: manter comportamento atual se guard estiver indisponível
                        # 1) SHOP (itens) - escreve no SCUM.db, então somente offline
                        try:
                            if hasattr(self, "shop_service") and self.shop_service:
                                self.logger.info(
                                    "[OFFLINE_JOBS] Processando entregas de shop pendentes..."
                                )
                                try:
                                    # Inicializar serviço com caminhos corretos
                                    from core.shop.delivery_service import ShopDeliveryService

                                    delivery_service = ShopDeliveryService(
                                        ssm_db_path=ssm_db_path,
                                        scum_db_path=scum_db_path,
                                        logger=self.logger,
                                    )
                                    delivery_result = (
                                        delivery_service.run_once()
                                    )
                                    self.logger.info(
                                        f"[OFFLINE_JOBS] Shop deliveries processadas: {delivery_result}"
                                    )
                                except Exception as e:
                                    self.logger.error(
                                        f"[OFFLINE_JOBS] Erro ao processar entregas de shop: {e}"
                                    )
                            else:
                                self.logger.info(
                                    "[OFFLINE_JOBS] shop_service não disponível - pulando entregas"
                                )
                        except Exception as e:
                            self.logger.error(
                                f"[OFFLINE_JOBS] Erro no bloco de shop: {e}"
                            )

                        # 2) VEÍCULOS - escreve no SCUM.db, então somente offline
                        try:
                            self._process_vehicle_orders_offline(scum_db_path, ssm_db_path)
                        except Exception as e:
                            self.logger.error(
                                f"[OFFLINE_JOBS] Erro ao processar pedidos de veículos offline: {e}"
                            )

                        # 3) BASE UPGRADES - escreve no SCUM.db, então somente offline
                        try:
                            self._process_base_upgrades_offline(scum_db_path, ssm_db_path)
                        except Exception as e:
                            self.logger.error(
                                f"[OFFLINE_JOBS] Erro ao processar upgrades de base offline: {e}"
                            )

            except Exception as e:
                self.logger.error(f"[OFFLINE_JOBS] Erro geral no processamento offline: {e}")

            # Verificar timeout antes de tentar iniciar
            elapsed = time.time() - restart_start_time
            remaining_time = max_restart_timeout - elapsed
            if remaining_time <= 0:
                # FAIL-OPEN: timeout atingido mas servidor está PARADO.
                # É MELHOR tentar iniciar mesmo assim do que deixar o servidor offline.
                self.logger.warn(
                    f"[FAIL-OPEN] Timeout máximo atingido ({elapsed:.1f}s) mas servidor está parado. "
                    "Prosseguindo com start_server para não deixar servidor offline."
                )
                remaining_time = 120  # Dar mais 2 minutos para tentar

            # Aguardar até que o SCUM.db esteja desbloqueado ANTES de iniciar o serviço.
            # Se iniciarmos com o DB lockado, o próprio SCUMServer pode crashar no startup.
            try:
                # Esperar no máximo 30s aqui - não bloquear o restart indefinidamente
                db_wait = min(30, int(remaining_time))
                self._wait_for_scum_db_unlocked(scum_db_path, max_wait_seconds=db_wait)
            except Exception as e:
                # FAIL-OPEN: SCUM.db bloqueado NÃO deve impedir o start.
                # O SCUMServer geralmente consegue iniciar mesmo com DB temporariamente locked.
                # É MELHOR iniciar com risco de crash do que deixar o servidor permanentemente offline.
                self.logger.warn(
                    f"[FAIL-OPEN] SCUM.db ainda bloqueado mas prosseguindo com start para não deixar servidor offline: {e}"
                )

            # Sistema de retry: tentar iniciar até conseguir (máximo 5 tentativas)
            max_retries = 5
            retry_count = 0

            while retry_count < max_retries:
                # Verificar timeout antes de cada tentativa
                elapsed = time.time() - restart_start_time
                if elapsed >= max_restart_timeout:
                    # FAIL-OPEN: Não abortar - servidor está PARADO. Tentar iniciar de qualquer forma.
                    self.logger.warn(
                        f"[FAIL-OPEN] Timeout ({elapsed:.1f}s) durante tentativas mas servidor está parado. "
                        f"Continuando tentativa {retry_count + 1} para não deixar servidor offline."
                    )

                retry_count += 1
                self.logger.info(
                    f"Tentativa {retry_count}/{max_retries} de iniciar servidor..."
                )
                self.logger.info(
                    f"Tempo decorrido: {elapsed:.1f}s / {max_restart_timeout}s"
                )

                # Validações de segurança antes de iniciar
                validation_success, validation_msg = self._validate_before_start(
                    scum_db_path
                )
                if not validation_success:
                    error_msg = f"Validação de segurança falhou (tentativa {retry_count}): {validation_msg}"
                    self.logger.warn(error_msg)

                    # Se é erro crítico (arquivos WAL/SHM ou serviço rodando), tentar corrigir
                    if "WAL" in validation_msg or "SHM" in validation_msg:
                        # Tentar limpar novamente
                        wal_path = f"{scum_db_path}-wal"
                        shm_path = f"{scum_db_path}-shm"
                        try:
                            if os.path.exists(wal_path):
                                os.remove(wal_path)
                                self.logger.info(f"Arquivo WAL removido: {wal_path}")
                            if os.path.exists(shm_path):
                                os.remove(shm_path)
                                self.logger.info(f"Arquivo SHM removido: {shm_path}")
                            time.sleep(2)
                            continue  # Tentar novamente
                        except Exception as e:
                            self.logger.error(f"Erro ao remover arquivos WAL/SHM: {e}")
                            if retry_count < max_retries:
                                time.sleep(5)
                                continue

                            # FAIL-OPEN (última tentativa): se o restart estiver travado somente por WAL/SHM
                            # em uso (WinError 32), prosseguir para o start mesmo assim.
                            try:
                                is_winerror_32 = getattr(e, "winerror", None) == 32
                            except Exception:
                                is_winerror_32 = False

                            if is_winerror_32:
                                self.logger.warn(
                                    "[FAIL-OPEN] WAL/SHM ainda em uso (WinError 32) na última tentativa. "
                                    "Prosseguindo com start_server mesmo assim para não impedir o restart."
                                )
                                validation_success = True
                                validation_msg = "fail-open: wal_shm_in_use_winerror_32"
                            else:
                                # manter fluxo normal de validação
                                pass

                    # Se serviço ainda está rodando, aguardar mais
                    if (
                        "rodando" in validation_msg.lower()
                        or "RUNNING" in validation_msg
                    ):
                        self.logger.warn(
                            "Serviço ainda está rodando. Aguardando mais tempo..."
                        )
                        stopped_success, stopped_msg = self._wait_for_service_stopped(
                            max_wait_seconds=20, initial_wait=3.0
                        )
                        if retry_count < max_retries:
                            continue  # Tentar novamente

                    # Se não é a última tentativa, continuar
                    if retry_count < max_retries:
                        self.logger.info(
                            f"Aguardando 5 segundos antes da próxima tentativa..."
                        )
                        time.sleep(5)
                        continue
                    else:
                        # Última tentativa falhou na validação
                        return {
                            "success": False,
                            "message": error_msg,
                            "status": "validation_failed",
                            "retry_count": retry_count,
                            "elapsed_seconds": elapsed,
                        }

                # Tentar iniciar servidor
                self.logger.info("=" * 40)
                self.logger.info(
                    f"INICIANDO PROCESSO DE START DO SERVIDOR (Tentativa {retry_count}/{max_retries})..."
                )
                self.logger.info("=" * 40)

                try:
                    start_result = self.start_server(scum_db_path=scum_db_path)
                    self.logger.info(
                        f"Resultado do start_server: success={start_result.get('success')}, message={start_result.get('message')}, status={start_result.get('status')}"
                    )

                    if start_result["success"]:
                        # Verificar saúde do serviço após iniciar
                        self.logger.info("Verificando saúde do serviço após iniciar...")
                        health_success, health_msg = self._verify_service_health(
                            max_wait_seconds=30, check_interval=2.0
                        )

                        if health_success:
                            # Barreira de prontidão: só liberar rotinas do SSM quando o processo estiver de pé.
                            # Usar Working Set como heurística de "servidor quase pronto".
                            # Usar apenas o tempo restante do budget, limitado a 120s para não atrasar demais.
                            try:
                                ready_remaining = max(30, int(max_restart_timeout - (time.time() - restart_start_time)))
                                ready_wait = min(120, ready_remaining)
                                ready_ok, ready_msg = self._wait_for_scumserver_ready(
                                    min_working_set_gb=6.0,
                                    max_wait_seconds=ready_wait,
                                    check_interval_seconds=5.0,
                                )
                            except Exception as ready_e:
                                ready_ok, ready_msg = False, f"exception: {ready_e}"

                            if not ready_ok:
                                elapsed_total = time.time() - restart_start_time
                                self.logger.warn(
                                    f"[SCUM_READY] Servidor iniciou mas não atingiu prontidão total: {ready_msg}. "
                                    "Considerando restart como SUCESSO pois o serviço está RUNNING."
                                )
                                # FAIL-OPEN: Servidor ESTÁ rodando (health check passou).
                                # Não atingir prontidão total (RAM threshold) NÃO é motivo para reportar falha.
                                # O servidor vai continuar carregando normalmente.

                            # Servidor está rodando (ready ou não, chegou aqui = health check OK)
                            restart_ready = True
                            elapsed_total = time.time() - restart_start_time
                            self.logger.info("=" * 40)
                            self.logger.info("SERVIDOR SCUM REINICIADO COM SUCESSO!")
                            self.logger.info("=" * 40)
                            self.logger.info(
                                f"Tempo total de restart: {elapsed_total:.1f} segundos"
                            )
                            self.logger.info(
                                f"Tentativas necessárias: {retry_count}/{max_retries}"
                            )

                            return {
                                "success": True,
                                "message": "Servidor reiniciado com sucesso",
                                "status": "restarted",
                                "retry_count": retry_count,
                                "elapsed_seconds": elapsed_total,
                                "health_check": health_msg,
                                "server_ready": ready_ok,
                                "ready_check": ready_msg,
                                "nssm_shutdown_result": nssm_shutdown_result,
                            }
                        else:
                            # Health check falhou - aguardar e tentar novamente
                            error_msg = (
                                f"Health check falhou (tentativa {retry_count}): {health_msg}"
                            )
                            self.logger.warn(error_msg)
                            if retry_count < max_retries:
                                time.sleep(10)
                                continue
                            return {
                                "success": False,
                                "message": error_msg,
                                "status": "health_check_failed",
                                "retry_count": retry_count,
                                "start_result": start_result,
                                "elapsed_seconds": time.time() - restart_start_time,
                            }
                except Exception as start_error:
                    import traceback

                    error_msg = f"Exceção ao chamar start_server (tentativa {retry_count}): {str(start_error)}"
                    self.logger.error(error_msg)
                    self.logger.error(f"Traceback: {traceback.format_exc()}")

                    # Detectar se é erro de logger (AttributeError: 'StructuredLogger' object has no attribute 'warning')
                    # Este erro não deve bloquear o restart, apenas logar e continuar
                    if "AttributeError" in str(type(start_error).__name__) and "warning" in str(start_error).lower():
                        self.logger.error(
                            "Erro de logger detectado - isso não deve acontecer após correção. "
                            "Continuando com próxima tentativa..."
                        )
                        # Aguardar um pouco e continuar
                        if retry_count < max_retries:
                            wait_time = 5  # Menor tempo de espera para erro de logger
                            self.logger.info(
                                f"Aguardando {wait_time} segundos antes da próxima tentativa..."
                            )
                            time.sleep(wait_time)
                            continue

                    # Se não é a última tentativa, aguardar e tentar novamente
                    if retry_count < max_retries:
                        # Usar tempo fixo de espera (backend deve funcionar 24/7)
                        wait_time = 10
                        self.logger.info(
                            f"Aguardando {wait_time} segundos antes da próxima tentativa..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        elapsed_total = time.time() - restart_start_time
                        return {
                            "success": False,
                            "message": error_msg,
                            "status": "start_exception",
                            "retry_count": retry_count,
                            "elapsed_seconds": elapsed_total,
                        }

            # Se chegou aqui, todas as tentativas falharam sem erro específico
            elapsed_total = time.time() - restart_start_time
            return {
                "success": False,
                "message": f"Falha ao iniciar servidor após {max_retries} tentativas",
                "status": "max_retries_exceeded",
                "retry_count": retry_count,
                "elapsed_seconds": elapsed_total,
            }

        except Exception as e:
            import traceback

            elapsed_total = time.time() - restart_start_time
            error_msg = f"Erro inesperado ao reiniciar servidor: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.logger.error(
                f"Tempo decorrido antes do erro: {elapsed_total:.1f} segundos"
            )

            return {
                "success": False,
                "message": error_msg,
                "status": "error",
                "elapsed_seconds": elapsed_total,
                "exception_type": type(e).__name__,
            }
        finally:
            # Garantir que o modo de pausa seja removido, mesmo em caso de erro.
            try:
                if 'shared_copy_mgr' in locals() and shared_copy_mgr:
                    shared_copy_mgr.resume()
            except Exception:
                pass
            try:
                from utils.restart_guard import set_restart_active

                set_restart_active(False)
            except Exception:
                pass

            # Sempre liberar lock de restart
            self._release_restart_lock()
            self.logger.info("Lock de restart liberado")

    def _get_service_state(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Obter estado detalhado do serviço

        Returns:
            Tuple[estado, stdout_completo] onde estado pode ser:
            - "RUNNING" - Serviço está rodando
            - "STOPPED" - Serviço está parado
            - "STOP_PENDING" - Serviço está parando
            - "START_PENDING" - Serviço está iniciando
            - "PAUSED" - Serviço está pausado
            - "CONTINUE_PENDING" - Serviço está continuando
            - "PAUSE_PENDING" - Serviço está pausando
            - None - Erro ao obter estado
        """
        try:
            # Usar PowerShell como método principal (mais confiável que sc.exe)
            # sc.exe pode falhar com erro 0xc0000142 em alguns sistemas
            try:
                ps_cmd = f"Get-Service -Name '{self.service_name}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status"
                result = subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ),
                )

                if result.returncode == 0 and result.stdout:
                    status = result.stdout.strip().upper()
                    if status == "RUNNING":
                        return "RUNNING", f"PowerShell: {status}"
                    elif status == "STOPPED":
                        return "STOPPED", f"PowerShell: {status}"
                    elif "START_PENDING" in status or "STARTING" in status:
                        return "START_PENDING", f"PowerShell: {status}"
                    elif "STOP_PENDING" in status or "STOPPING" in status:
                        return "STOP_PENDING", f"PowerShell: {status}"
                    else:
                        return status, f"PowerShell: {status}"
            except Exception as ps_error:
                self.logger.warn(
                    f"PowerShell falhou, tentando sc.exe como fallback: {ps_error}"
                )

            # Fallback: usar sc.exe apenas se PowerShell falhar
            # Aumentar timeout para 30 segundos - quando serviço está em estado transitório
            # (iniciando/parando) ou após erro 0xc0000142, o sc query pode demorar mais
            result = subprocess.run(
                ["sc", "query", self.service_name],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )

            if result.returncode == 0:
                output_upper = result.stdout.upper()
                # Extrair estado exato
                if "STATE" in output_upper:
                    for line in result.stdout.split("\n"):
                        if "STATE" in line.upper():
                            # Formato esperado: STATE              : 4  RUNNING
                            parts = line.split(":")
                            if len(parts) >= 2:
                                state_part = parts[-1].strip()
                                # Extrair o nome do estado (última palavra)
                                state_words = state_part.split()
                                if state_words:
                                    state = state_words[-1].upper()
                                    return state, result.stdout
                # Fallback: tentar detectar estado manualmente
                if (
                    "RUNNING" in output_upper
                    and "STOP_PENDING" not in output_upper
                    and "START_PENDING" not in output_upper
                ):
                    return "RUNNING", result.stdout
                elif "STOPPED" in output_upper:
                    return "STOPPED", result.stdout
                elif "STOP_PENDING" in output_upper:
                    return "STOP_PENDING", result.stdout
                elif "START_PENDING" in output_upper:
                    return "START_PENDING", result.stdout
                elif "PAUSED" in output_upper:
                    return "PAUSED", result.stdout
                elif "CONTINUE_PENDING" in output_upper:
                    return "CONTINUE_PENDING", result.stdout
                elif "PAUSE_PENDING" in output_upper:
                    return "PAUSE_PENDING", result.stdout
            return None, result.stdout if result.returncode == 0 else None

        except subprocess.TimeoutExpired:
            # Timeout pode ocorrer quando serviço está em estado transitório ou após erro 0xc0000142
            self.logger.warn(
                "Timeout ao verificar status do serviço. Tentando PowerShell..."
            )
            try:
                # Fallback: usar PowerShell Get-Service (mais rápido e confiável)
                ps_cmd = f"Get-Service -Name '{self.service_name}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status"
                result = subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ),
                )

                if result.returncode == 0 and result.stdout:
                    status = result.stdout.strip().upper()
                    if status == "RUNNING":
                        return "RUNNING", f"PowerShell: {status}"
                    elif status == "STOPPED":
                        return "STOPPED", f"PowerShell: {status}"
                    elif "START_PENDING" in status or "STARTING" in status:
                        return "START_PENDING", f"PowerShell: {status}"
                    elif "STOP_PENDING" in status or "STOPPING" in status:
                        return "STOP_PENDING", f"PowerShell: {status}"
                    else:
                        return status, f"PowerShell: {status}"
            except Exception as ps_error:
                self.logger.warn(f"Fallback PowerShell também falhou: {ps_error}")

            # Se ambos falharam, retornar None mas logar aviso
            self.logger.error(
                "Não foi possível obter status do serviço (timeout + PowerShell fallback falhou)"
            )
            return None, None
        except Exception as e:
            error_msg = str(e)
            # Verificar se é erro relacionado a 0xc0000142 ou inicialização
            if (
                "0xc0000142" in error_msg
                or "inicialização" in error_msg.lower()
                or "não pôde ser inicializado" in error_msg.lower()
            ):
                self.logger.warn(
                    f"Erro de inicialização detectado (0xc0000142) ao verificar status: {e}"
                )
                self.logger.info("Usando PowerShell como método alternativo...")
                # Tentar fallback PowerShell
                try:
                    ps_cmd = f"Get-Service -Name '{self.service_name}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status"
                    result = subprocess.run(
                        ["powershell", "-Command", ps_cmd],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW
                            if sys.platform == "win32"
                            else 0
                        ),
                    )
                    if result.returncode == 0 and result.stdout:
                        status = result.stdout.strip().upper()
                        return status, f"PowerShell fallback: {status}"
                except Exception as ps_err:
                    self.logger.error(f"PowerShell fallback também falhou: {ps_err}")

            self.logger.error(f"Erro ao verificar status do serviço: {e}")
            return None, None

    def _is_service_running(self) -> bool:
        """
        Verificar se serviço está rodando (considera estados intermediários)

        Returns:
            True se serviço está rodando (RUNNING), False caso contrário
        """
        state, stdout = self._get_service_state()
        if state == "RUNNING":
            return True
        # Estados intermediários ou parados são considerados como "não rodando"
        # para permitir tentativas de iniciar
        return False

    def _wait_for_service_stopped(
        self, max_wait_seconds: int = 30, initial_wait: float = 2.0
    ) -> Tuple[bool, str]:
        """
        Aguardar até que o serviço esteja completamente parado

        Args:
            max_wait_seconds: Tempo máximo de espera em segundos
            initial_wait: Tempo inicial de espera antes da primeira verificação

        Returns:
            Tuple[sucesso, mensagem] onde sucesso indica se serviço está parado
        """
        start_time = time.time()
        wait_time = initial_wait
        attempt = 0

        self.logger.info(
            f"Aguardando serviço parar completamente (timeout: {max_wait_seconds}s)..."
        )

        # Aguardar tempo inicial antes da primeira verificação
        time.sleep(initial_wait)

        while (time.time() - start_time) < max_wait_seconds:
            attempt += 1
            state, stdout = self._get_service_state()

            if state is None:
                self.logger.warn(
                    f"Tentativa {attempt}: Não foi possível obter estado do serviço"
                )
            else:
                self.logger.info(f"Tentativa {attempt}: Estado do serviço = {state}")

                if state == "STOPPED":
                    elapsed = time.time() - start_time
                    self.logger.info(
                        f"Serviço confirmado como parado após {elapsed:.1f} segundos"
                    )
                    return True, f"Serviço parado confirmado (estado: {state})"

                # Se está em STOP_PENDING, aguardar mais tempo
                if state == "STOP_PENDING":
                    self.logger.info(
                        f"Serviço em STOP_PENDING - aguardando mais {wait_time:.1f} segundos..."
                    )
                elif state == "RUNNING":
                    self.logger.warn(
                        f"Serviço ainda está RUNNING - aguardando mais {wait_time:.1f} segundos..."
                    )
                else:
                    self.logger.info(
                        f"Serviço em estado intermediário ({state}) - aguardando mais {wait_time:.1f} segundos..."
                    )

            # Backoff exponencial com limite máximo
            time.sleep(min(wait_time, 10.0))  # Máximo de 10 segundos por iteração
            wait_time = min(wait_time * 1.5, 10.0)  # Aumentar progressivamente até 10s

        # Timeout atingido
        elapsed = time.time() - start_time
        final_state, final_stdout = self._get_service_state()
        error_msg = f"Timeout após {elapsed:.1f} segundos. Estado final: {final_state or 'desconhecido'}"
        self.logger.error(error_msg)
        if final_stdout:
            self.logger.debug(f"Output do serviço: {final_stdout}")

        # Se o estado final for STOPPED, considerar sucesso mesmo com timeout
        if final_state == "STOPPED":
            return (
                True,
                f"Serviço parado confirmado (após timeout, estado: {final_state})",
            )

        return False, error_msg

    def _wait_for_scum_db_unlocked(self, scum_db_path: str, max_wait_seconds: int = 60) -> None:
        """
        Aguarda até que o SCUM.db esteja desbloqueado para operações.

        Implementação: tenta abrir uma transação de escrita (BEGIN IMMEDIATE). Se falhar com
        'database is locked/busy', aguarda e tenta novamente até o timeout.
        """
        if not scum_db_path:
            raise ValueError("Caminho do SCUM.db não fornecido")

        start_time = time.time()
        deadline = start_time + max_wait_seconds
        attempts = 0
        last_err: Optional[BaseException] = None
        last_log_t = 0.0

        try:
            self.logger.info(
                f"[SCUM_DB] Aguardando SCUM.db destravar (max {int(max_wait_seconds)}s): {scum_db_path}"
            )
        except Exception:
            pass

        while time.time() < deadline:
            conn = None
            try:
                attempts += 1
                conn = sqlite3.connect(scum_db_path, timeout=1.0)
                conn.execute("PRAGMA busy_timeout = 1000")
                conn.execute("BEGIN IMMEDIATE")
                conn.rollback()

                elapsed = time.time() - start_time
                if elapsed >= 1.0:
                    try:
                        self.logger.info(
                            f"[SCUM_DB] SCUM.db destravado após {elapsed:.1f}s (tentativas={attempts})"
                        )
                    except Exception:
                        pass
                return
            except sqlite3.OperationalError as oe:
                last_err = oe
                msg = str(oe or "").lower()
                if "locked" in msg or "busy" in msg:
                    now = time.time()
                    if (now - last_log_t) >= 5.0:
                        last_log_t = now
                        elapsed = now - start_time
                        try:
                            self.logger.warn(
                                f"[SCUM_DB] SCUM.db ainda bloqueado ({elapsed:.1f}s/{int(max_wait_seconds)}s). Aguardando..."
                            )
                        except Exception:
                            pass
                    time.sleep(1.0)
                    continue
                raise
            except Exception as e:
                last_err = e
                time.sleep(1.0)
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass

        raise RuntimeError(
            f"SCUM.db ainda está bloqueado após {int(max_wait_seconds)}s: {last_err}"
        )

    def _force_kill_scumserver_processes(self) -> bool:
        """Finaliza processos SCUMServer.exe remanescentes após stop do serviço."""
        if sys.platform != "win32":
            return False

        powershell_cmd = r"""
        $p = Get-Process -Name 'SCUMServer' -ErrorAction SilentlyContinue
        if ($null -ne $p) {
            $p | Stop-Process -Force -ErrorAction SilentlyContinue
            Write-Host 'KILLED'
        } else {
            Write-Host 'NOT_FOUND'
        }
        """

        try:
            res = subprocess.run(
                ["powershell", "-Command", powershell_cmd],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            out = (res.stdout or "") + (res.stderr or "")
            killed = "KILLED" in out
            if killed:
                self.logger.warn(
                    "[SCUM_DB] Processo SCUMServer.exe remanescente foi finalizado com -Force."
                )
            return killed
        except Exception as e:
            self.logger.warn(
                f"[SCUM_DB] Falha ao tentar kill forçado do SCUMServer.exe: {e}"
            )
            return False

    def _validate_before_start(self, scum_db_path: str) -> Tuple[bool, str]:
        """
        Validar condições de segurança antes de iniciar servidor

        Args:
            scum_db_path: Caminho do banco SCUM.db

        Returns:
            Tuple[sucesso, mensagem] onde sucesso indica se todas validações passaram
        """
        validations = []

        # 1. Verificar se serviço está realmente parado
        state, stdout = self._get_service_state()
        if state == "RUNNING":
            return False, f"Serviço ainda está rodando (estado: {state})"
        elif state == "START_PENDING":
            return False, f"Serviço já está iniciando (estado: {state})"
        elif state not in ("STOPPED", "STOP_PENDING", None):
            validations.append(f"Estado do serviço: {state} (pode ser seguro iniciar)")

        # 2. Verificar se arquivos WAL/SHM foram removidos
        wal_path = f"{scum_db_path}-wal"
        shm_path = f"{scum_db_path}-shm"
        wal_exists = os.path.exists(wal_path)
        shm_exists = os.path.exists(shm_path)

        if wal_exists or shm_exists:
            files = []
            if wal_exists:
                files.append("WAL")
            if shm_exists:
                files.append("SHM")
            return (
                False,
                f"Arquivos {', '.join(files)} ainda existem (devem ser removidos antes de iniciar)",
            )

        # 3. Verificar se caminho do servidor existe
        if not os.path.exists(self.server_path):
            return False, f"Caminho do servidor não existe: {self.server_path}"

        # 4. Verificar se diretório de instalação existe
        if not os.path.exists(self.install_path):
            return False, f"Diretório de instalação não existe: {self.install_path}"

        # 5. Verificar se NSSM existe (se usando)
        if self.nssm_path and not os.path.exists(self.nssm_path):
            validations.append(
                f"NSSM não encontrado em: {self.nssm_path} (pode usar métodos alternativos)"
            )

        # Todas validações passaram
        if validations:
            self.logger.info(
                f"Validações de segurança passaram com avisos: {', '.join(validations)}"
            )
        else:
            self.logger.info("Todas validações de segurança passaram")

        return True, "Validações de segurança passadas"

    def _verify_service_health(
        self, max_wait_seconds: int = 30, check_interval: float = 2.0
    ) -> Tuple[bool, str]:
        """
        Verificar saúde do serviço após iniciar

        Args:
            max_wait_seconds: Tempo máximo de espera em segundos
            check_interval: Intervalo entre verificações em segundos

        Returns:
            Tuple[sucesso, mensagem] onde sucesso indica se serviço está saudável
        """
        start_time = time.time()
        attempt = 0

        self.logger.info(
            f"Verificando saúde do serviço após iniciar (timeout: {max_wait_seconds}s)..."
        )

        while (time.time() - start_time) < max_wait_seconds:
            attempt += 1
            state, stdout = self._get_service_state()

            if state == "RUNNING":
                # Serviço está rodando - aguardar um pouco mais para garantir que não morra imediatamente
                if attempt >= 2:  # Pelo menos 2 verificações positivas
                    elapsed = time.time() - start_time
                    self.logger.info(
                        f"Serviço confirmado como saudável após {elapsed:.1f} segundos (estado: {state})"
                    )
                    return True, f"Serviço saudável (estado: {state})"
            elif state == "STOPPED":
                elapsed = time.time() - start_time
                error_msg = f"Serviço parou imediatamente após iniciar (após {elapsed:.1f}s, estado: {state})"
                self.logger.error(error_msg)
                return False, error_msg
            elif state == "START_PENDING":
                self.logger.info(
                    f"Tentativa {attempt}: Serviço em START_PENDING - aguardando mais {check_interval}s..."
                )
            elif state is None:
                self.logger.warn(
                    f"Tentativa {attempt}: Não foi possível obter estado do serviço"
                )
            else:
                self.logger.info(
                    f"Tentativa {attempt}: Estado do serviço = {state} - aguardando mais {check_interval}s..."
                )

            time.sleep(check_interval)

        # Timeout atingido
        elapsed = time.time() - start_time
        final_state, final_stdout = self._get_service_state()

        if final_state == "RUNNING":
            # Mesmo com timeout, se está RUNNING, considerar sucesso
            return True, f"Serviço está rodando (após timeout, estado: {final_state})"
        else:
            error_msg = f"Timeout na verificação de saúde após {elapsed:.1f} segundos. Estado final: {final_state or 'desconhecido'}"
            self.logger.warn(error_msg)
            return False, error_msg

    def _update_steam(self) -> Dict[str, Any]:
        """Atualizar servidor via SteamCMD"""
        try:
            self.logger.info("[1/3] Iniciando atualização Steam...")

            # Resolver steamcmd.exe: steamcmd_path pode ser diretório OU caminho completo do .exe
            steamcmd_exe = None
            steamcmd_dir = None
            configured_path = (self.steamcmd_path or "").strip()
            if configured_path:
                if configured_path.lower().endswith("steamcmd.exe"):
                    if os.path.exists(configured_path):
                        steamcmd_exe = configured_path
                        steamcmd_dir = os.path.dirname(configured_path)
                else:
                    candidate = os.path.join(configured_path, "steamcmd.exe")
                    if os.path.exists(candidate):
                        steamcmd_exe = candidate
                        steamcmd_dir = configured_path

            # Fallback: procurar no PATH
            if not steamcmd_exe:
                found = shutil.which("steamcmd.exe")
                if found:
                    steamcmd_exe = found
                    steamcmd_dir = os.path.dirname(found)

            if not steamcmd_exe or not os.path.exists(steamcmd_exe):
                return {
                    "success": False,
                    "message": (
                        "SteamCMD não encontrado. "
                        f"Config steamcmd_path='{self.steamcmd_path}'. "
                        "Esperado diretório contendo steamcmd.exe ou caminho completo do steamcmd.exe."
                    ),
                    "status": "steamcmd_not_found",
                }

            self.logger.info(
                f'Executando: {steamcmd_exe} +force_install_dir "{self.install_path}" +login anonymous +app_update 3792580 +quit'
            )

            result = subprocess.run(
                [
                    steamcmd_exe,
                    "+force_install_dir",
                    self.install_path,
                    "+login",
                    "anonymous",
                    "+app_update",
                    "3792580",
                    "+quit",
                ],
                cwd=steamcmd_dir or None,
                capture_output=True,
                text=True,
                timeout=600,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )  # 10 minutos timeout

            if result.returncode != 0:
                self.logger.error(f"ERRO: Falha na atualização Steam!")
                self.logger.error(
                    f"Verifique se o SteamCMD está instalado e funcionando."
                )
                self.logger.error(f"SteamCMD returncode: {result.returncode}")
                self.logger.error(f"SteamCMD cwd: {steamcmd_dir}")
                self.logger.error(f"Stdout: {(result.stdout or '').strip()}")
                captured_stderr = (result.stderr or "").strip()
                self.logger.error(f"Stderr: {captured_stderr}")

                # SteamCMD frequentemente redireciona stderr para arquivo.
                stderr_file_tail = ""
                try:
                    if steamcmd_dir:
                        stderr_file = os.path.join(steamcmd_dir, "logs", "stderr.txt")
                        if os.path.exists(stderr_file):
                            with open(stderr_file, "r", encoding="utf-8", errors="replace") as f:
                                stderr_file_tail = (f.read() or "")[-4000:].strip()
                except Exception as e:
                    self.logger.warn(f"Não foi possível ler logs/stderr.txt do SteamCMD: {e}")

                if stderr_file_tail:
                    self.logger.error(f"SteamCMD stderr.txt (tail): {stderr_file_tail}")
                return {
                    "success": False,
                    "message": "Falha na atualização Steam (SteamCMD)",
                    "status": "steam_update_failed",
                    "returncode": result.returncode,
                    "steamcmd_exe": steamcmd_exe,
                    "steamcmd_cwd": steamcmd_dir,
                    "stdout": (result.stdout or "")[-4000:],
                    "stderr": (result.stderr or "")[-4000:],
                    "stderr_txt": stderr_file_tail,
                }

            self.logger.info("Steam Update concluído com sucesso!")
            return {"success": True, "message": "Steam atualizado com sucesso"}

        except subprocess.TimeoutExpired:
            self.logger.error("Timeout na atualização Steam (10 minutos)")
            return {
                "success": False,
                "message": "Timeout na atualização Steam",
                "status": "steam_timeout",
            }
        except Exception as e:
            self.logger.error(f"Erro na atualização Steam: {e}")
            return {
                "success": False,
                "message": f"Erro na atualização Steam: {str(e)}",
                "status": "steam_error",
            }

    def install_or_update_via_steamcmd(self) -> Dict[str, Any]:
        """Instalar/atualizar o servidor SCUM via SteamCMD (sem iniciar o servidor)."""
        return self._update_steam()

    def _start_service_nssm(self) -> Dict[str, Any]:
        """Iniciar serviço via NSSM"""
        try:
            self.logger.info("Iniciando serviço SCUMServer via NSSM...")

            if not os.path.exists(self.nssm_path):
                self.logger.error(f"ERRO: NSSM não encontrado em: {self.nssm_path}")
                return {
                    "success": False,
                    "message": f"NSSM não encontrado em: {self.nssm_path}",
                    "status": "nssm_not_found",
                }

            self.logger.info(f"NSSM encontrado em: {self.nssm_path}")

            # Verificar se serviço já está rodando antes de tentar iniciar
            if self._is_service_running():
                self.logger.warn(
                    "Serviço já está rodando antes de tentar iniciar via NSSM"
                )
                return {"success": True, "message": "Serviço já estava rodando"}

            # Em ambiente onde este backend roda como Serviço do Windows, usar PowerShell RunAs
            # pode ser intermitente por causa do UAC/sessão 0. Portanto, tentar primeiro
            # executar o NSSM diretamente. Se falhar (ex.: sem permissão), cair no método atual.
            direct_err = None
            def _is_admin() -> bool:
                try:
                    return bool(ctypes.windll.shell32.IsUserAnAdmin())
                except Exception:
                    return False

            # Importante: quando o SSM não está elevado (etapa de instalação), o Windows pode
            # negar acesso ao Service Control Manager e o NSSM retorna "OpenService(): Acesso negado".
            # Isso é esperado e não deve gerar warning/confusão. Nesse caso, pular a tentativa direta
            # e ir direto para o RunAs (UAC).
            if _is_admin():
                try:
                    self.logger.info(
                        "Tentando iniciar via NSSM diretamente (sem PowerShell/RunAs)..."
                    )
                    r = subprocess.run(
                        [self.nssm_path, "start", self.service_name],
                        capture_output=True,
                        text=True,
                        timeout=20,
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                        ),
                    )
                    if int(r.returncode or 0) != 0:
                        direct_err = self._sanitize_process_output(
                            (r.stdout or "") + "\n" + (r.stderr or "")
                        )
                        self.logger.warn(
                            f"Start NSSM direto retornou código {r.returncode}: {direct_err}"
                        )
                    else:
                        self.logger.info("Comando NSSM direto executado.")
                except Exception as e:
                    direct_err = str(e)
                    self.logger.warn(f"Start NSSM direto falhou: {e}")
            else:
                direct_err = "Not elevated; skipping direct NSSM start and using UAC RunAs."
                try:
                    self.logger.info(
                        "Não está em modo administrador; iniciando via UAC (RunAs) diretamente..."
                    )
                except Exception:
                    pass

            # Aguardar um pouco extra para garantir que serviço está completamente parado
            self.logger.info(
                "Aguardando 3 segundos adicionais para garantir que serviço está completamente parado..."
            )
            time.sleep(3)

            self.logger.info(
                "Executando comando NSSM com privilégios de administrador..."
            )

            # Executar NSSM com elevação via PowerShell
            # Usar -Wait para aguardar conclusão e melhor tratamento de erros
            powershell_cmd = f"""
            $process = Start-Process -FilePath '{self.nssm_path}' -ArgumentList 'start {self.service_name}' -Verb RunAs -PassThru -WindowStyle Hidden
            $process.WaitForExit(30000)
            if ($process.ExitCode -ne 0) {{
                Write-Host "NSSM_EXIT_CODE:$($process.ExitCode)"
            }}
            """

            try:
                result = subprocess.run(
                    ["powershell", "-Command", powershell_cmd],
                    capture_output=True,
                    text=True,
                    timeout=35,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ),
                )

                # Verificar se houve erro no output
                if (
                    result.returncode != 0
                    or "NSSM_EXIT_CODE" in result.stdout
                    or "NSSM_EXIT_CODE" in result.stderr
                ):
                    self.logger.warn(
                        f"NSSM pode ter retornado erro. Return code: {result.returncode}"
                    )
                    self.logger.warn(
                        f"Stdout: {self._sanitize_process_output(result.stdout)}"
                    )
                    self.logger.warn(
                        f"Stderr: {self._sanitize_process_output(result.stderr)}"
                    )
            except subprocess.TimeoutExpired:
                self.logger.warn(
                    "Timeout ao executar NSSM (pode ser normal se serviço iniciou)"
                )
            except Exception as e:
                self.logger.warn(
                    f"Erro ao executar NSSM: {e} - continuando para verificar se serviço iniciou"
                )

            # Aguardar mais tempo para o serviço iniciar
            self.logger.info("Aguardando 15 segundos para o serviço iniciar...")
            time.sleep(15)

            # Verificar se iniciou
            if self._is_service_running():
                self.logger.info("Serviço iniciado com sucesso via NSSM!")
                return {"success": True, "message": "Serviço iniciado via NSSM"}
            else:
                self.logger.error("NSSM não conseguiu iniciar o serviço.")
                return {
                    "success": False,
                    "message": "NSSM falhou ao iniciar serviço. Verifique os logs do serviço Windows.",
                    "status": "nssm_start_failed",
                    "direct_attempt_error": direct_err,
                }

        except Exception as e:
            import traceback

            self.logger.error(f"Erro ao iniciar via NSSM: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "message": f"Erro NSSM: {str(e)}"}

    def _start_service_powershell(self) -> Dict[str, Any]:
        """Método alternativo via PowerShell"""
        try:
            # Verificar se serviço já está rodando antes de tentar iniciar
            if self._is_service_running():
                self.logger.warn(
                    "Serviço já está rodando antes de tentar iniciar via PowerShell"
                )
                return {"success": True, "message": "Serviço já estava rodando"}

            # Aguardar um pouco extra para garantir que serviço está completamente parado
            self.logger.info(
                "Aguardando 3 segundos adicionais antes de iniciar via PowerShell..."
            )
            time.sleep(3)

            self.logger.info(
                "Tentando iniciar serviço via PowerShell com tratamento de erros..."
            )

            # Usar try-catch no PowerShell para capturar erros específicos como 0xc0000142
            powershell_cmd = f"""
            try {{
                $service = Get-Service -Name '{self.service_name}' -ErrorAction Stop
                if ($service.Status -eq 'Running') {{
                    Write-Host "SERVICE_ALREADY_RUNNING"
                    exit 0
                }}
                
                Start-Service -Name '{self.service_name}' -ErrorAction Stop
                Start-Sleep -Seconds 10
                $status = Get-Service -Name '{self.service_name}'
                if ($status.Status -eq "Running") {{
                    Write-Host "SUCCESS"
                    exit 0
                }} else {{
                    Write-Host "FAILED_STATUS:$($status.Status)"
                    exit 1
                }}
            }} catch {{
                $errorMsg = $_.Exception.Message
                if ($errorMsg -match '0xc0000142') {{
                    Write-Host "ERROR_0xc0000142:Inicialização falhou - serviço pode estar em estado transitório"
                    exit 2
                }} else {{
                    Write-Host "ERROR:$errorMsg"
                    exit 1
                }}
            }}
            """

            try:
                result = subprocess.run(
                    ["powershell", "-Command", powershell_cmd],
                    capture_output=True,
                    text=True,
                    timeout=35,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ),
                )

                # Verificar output para erros específicos
                output = result.stdout + result.stderr
                if "ERROR_0xc0000142" in output:
                    self.logger.error(
                        "Erro 0xc0000142 detectado: Inicialização do serviço falhou"
                    )
                    self.logger.info("Aguardando mais tempo e tentando novamente...")
                    time.sleep(10)
                    # Tentar verificar se serviço iniciou mesmo assim
                    if self._is_service_running():
                        self.logger.info("Serviço iniciou apesar do erro 0xc0000142")
                        return {
                            "success": True,
                            "message": "Serviço iniciado (recuperado de erro 0xc0000142)",
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Erro 0xc0000142: Inicialização falhou",
                            "status": "init_error",
                        }
                elif "SERVICE_ALREADY_RUNNING" in output:
                    self.logger.info("Serviço já estava rodando")
                    return {"success": True, "message": "Serviço já estava rodando"}
                elif "SUCCESS" in output:
                    self.logger.info("Comando PowerShell retornou SUCCESS")
                else:
                    self.logger.warn(f"Output do PowerShell: {output}")
            except subprocess.TimeoutExpired:
                self.logger.warn(
                    "Timeout ao executar PowerShell (pode ser normal se serviço iniciou)"
                )
            except Exception as e:
                self.logger.warn(
                    f"Erro ao executar PowerShell: {e} - continuando para verificar se serviço iniciou"
                )

            # Aguardar um pouco mais
            self.logger.info("Aguardando 15 segundos para o serviço iniciar...")
            time.sleep(15)

            if self._is_service_running():
                return {"success": True, "message": "Serviço iniciado via PowerShell"}
            else:
                return {"success": False, "message": "Falha no método PowerShell"}

        except Exception as e:
            import traceback

            self.logger.error(f"Erro no método PowerShell: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "message": f"Erro PowerShell: {str(e)}"}

    def _stop_service_nssm(self) -> Dict[str, Any]:
        """Parar serviço via NSSM com shutdown gracioso"""
        try:
            self.logger.info("Parando serviço via NSSM com shutdown gracioso...")

            if not os.path.exists(self.nssm_path):
                self.logger.error(f"ERRO: NSSM não encontrado em: {self.nssm_path}")
                return {
                    "success": False,
                    "message": f"NSSM não encontrado em: {self.nssm_path}",
                    "status": "nssm_not_found",
                }

            self.logger.info(f"NSSM encontrado em: {self.nssm_path}")
            self.logger.info(
                "Executando comando NSSM com privilégios de administrador..."
            )
            self.logger.info(
                "Aguardando shutdown gracioso do servidor SCUM (pode levar até 2 minutos e 30 segundos)..."
            )

            direct_err = None
            try:
                self.logger.info(
                    "Tentando parar via NSSM diretamente (sem PowerShell/RunAs)..."
                )
                r = subprocess.run(
                    [self.nssm_path, "stop", self.service_name],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ),
                )
                if int(r.returncode or 0) != 0:
                    direct_err = self._sanitize_process_output(
                        (r.stdout or "") + "\n" + (r.stderr or "")
                    )
                    self.logger.warn(
                        f"Stop NSSM direto retornou código {r.returncode}: {direct_err}"
                    )
                else:
                    self.logger.info("Comando NSSM stop direto executado.")
            except Exception as e:
                direct_err = str(e)
                self.logger.warn(f"Stop NSSM direto falhou: {e}")

            # Executar NSSM com elevação via PowerShell
            # NSSM stop envia CTRL_C_EVENT que permite shutdown gracioso
            powershell_cmd = f"Start-Process -FilePath '{self.nssm_path}' -ArgumentList 'stop {self.service_name}' -Verb RunAs -WindowStyle Hidden"

            result = subprocess.run(
                ["powershell", "-Command", powershell_cmd],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )

            # Aguardar tempo suficiente para o servidor fazer backups e limpezas (até 2 minutos e 30 segundos)
            max_wait_time = 150  # 2 minutos e 30 segundos para shutdown completo
            check_interval = 5  # Verificar a cada 5 segundos
            waited = 0

            while waited < max_wait_time:
                if not self._is_service_running():
                    self.logger.info(
                        f"Serviço parado graciosamente via NSSM após {waited} segundos"
                    )
                    return {
                        "success": True,
                        "message": "Serviço parado graciosamente via NSSM",
                        "direct_attempt_error": direct_err,
                    }
                time.sleep(check_interval)
                waited += check_interval
                if waited % 30 == 0:  # Log a cada 30 segundos
                    self.logger.info(
                        f"Aguardando shutdown gracioso... ({waited}/{max_wait_time}s)"
                    )

            # Se ainda estiver rodando após 2 minutos, verificar novamente
            if not self._is_service_running():
                self.logger.info("Serviço parado com sucesso via NSSM!")
                return {
                    "success": True,
                    "message": "Serviço parado via NSSM",
                    "direct_attempt_error": direct_err,
                }
            else:
                self.logger.error(
                    "NSSM não conseguiu parar o serviço após shutdown gracioso (2 minutos e 30 segundos)."
                )
                return {
                    "success": False,
                    "message": "NSSM falhou ao parar serviço após 2 minutos e 30 segundos de shutdown gracioso. O servidor pode estar travado.",
                    "status": "nssm_stop_timeout",
                    "direct_attempt_error": direct_err,
                }

        except Exception as e:
            self.logger.error(f"Erro ao parar via NSSM: {e}")
            return {"success": False, "message": f"Erro NSSM: {str(e)}"}

    def _stop_service_powershell(self) -> Dict[str, Any]:
        """Método alternativo via PowerShell com shutdown gracioso"""
        try:
            # Primeiro, tentar shutdown gracioso (sem -Force)
            self.logger.info(
                "[2/2] Tentando shutdown gracioso via PowerShell (sem -Force)..."
            )
            self.logger.info(
                "Aguardando shutdown gracioso do servidor SCUM (pode levar até 2 minutos e 30 segundos)..."
            )

            # Executar Stop-Service sem -Force para permitir shutdown gracioso
            powershell_cmd_graceful = f"""
            Start-Process powershell -ArgumentList '-Command', 
            'Stop-Service -Name {self.service_name}; 
            Start-Sleep -Seconds 5; 
            $status = Get-Service -Name {self.service_name}; 
            if ($status.Status -eq "Stopped") {{ Write-Host "SUCCESS" }} else {{ Write-Host "STILL_RUNNING" }}' 
            -Verb RunAs -WindowStyle Hidden
            """

            result = subprocess.run(
                ["powershell", "-Command", powershell_cmd_graceful],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )

            # Aguardar tempo suficiente para o servidor fazer backups e limpezas (até 2 minutos e 30 segundos)
            max_wait_time = 150  # 2 minutos e 30 segundos
            check_interval = 5  # Verificar a cada 5 segundos
            waited = 0

            while waited < max_wait_time:
                if not self._is_service_running():
                    self.logger.info(
                        f"Serviço parado graciosamente via PowerShell após {waited} segundos"
                    )
                    return {
                        "success": True,
                        "message": "Serviço parado graciosamente via PowerShell",
                    }
                time.sleep(check_interval)
                waited += check_interval
                if waited % 30 == 0:  # Log a cada 30 segundos
                    self.logger.info(
                        f"Aguardando shutdown gracioso... ({waited}/{max_wait_time}s)"
                    )

            # Se ainda estiver rodando após 2 minutos e 30 segundos, informar que está demorando
            # NÃO usar -Force - aguardar mais tempo ou retornar erro
            self.logger.warn(
                "Serviço ainda rodando após 2 minutos e 30 segundos de shutdown gracioso."
            )
            self.logger.warn(
                "O servidor pode estar processando muitos dados. Aguardando mais 60 segundos..."
            )

            # Aguardar mais 60 segundos adicionais
            additional_wait = 60
            additional_waited = 0

            while additional_waited < additional_wait:
                if not self._is_service_running():
                    total_time = max_wait_time + additional_waited
                    self.logger.info(
                        f"Serviço parado graciosamente via PowerShell após {total_time} segundos"
                    )
                    return {
                        "success": True,
                        "message": f"Serviço parado graciosamente via PowerShell após {total_time} segundos",
                    }
                time.sleep(check_interval)
                additional_waited += check_interval
                if additional_waited % 30 == 0:
                    self.logger.info(
                        f"Aguardando shutdown gracioso (tempo adicional: {additional_waited}/{additional_wait}s)..."
                    )

            # Verificar uma última vez
            if not self._is_service_running():
                total_time = max_wait_time + additional_wait
                self.logger.info(
                    f"Serviço parado graciosamente via PowerShell após {total_time} segundos"
                )
                return {
                    "success": True,
                    "message": f"Serviço parado graciosamente via PowerShell após {total_time} segundos",
                }
            else:
                self.logger.error(
                    "Serviço não parou após 3 minutos de shutdown gracioso."
                )
                self.logger.error(
                    "Verifique os logs do servidor SCUM para identificar o problema."
                )
                return {
                    "success": False,
                    "message": "Serviço não parou após shutdown gracioso (3 minutos). Verifique os logs do servidor.",
                }

        except Exception as e:
            self.logger.error(f"Erro no método PowerShell: {e}")
            return {"success": False, "message": f"Erro PowerShell: {str(e)}"}

    def _stop_service_sc(self) -> Dict[str, Any]:
        """Método alternativo via SC (Service Control) com shutdown gracioso"""
        try:
            self.logger.info(
                "Tentando shutdown gracioso via PowerShell Stop-Service..."
            )
            self.logger.info(
                "Aguardando shutdown gracioso do servidor SCUM (pode levar até 2 minutos e 30 segundos)..."
            )

            # Usar PowerShell como método principal (mais confiável que sc.exe)
            # sc.exe pode falhar com erro 0xc0000142 em alguns sistemas
            try:
                ps_cmd = f"Stop-Service -Name '{self.service_name}' -ErrorAction Stop"
                result = subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ),
                )

                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Erro desconhecido"
                    self.logger.warn(
                        f"PowerShell Stop-Service retornou código {result.returncode}: {error_msg}"
                    )
                    # Continuar mesmo assim - pode ser que o serviço já esteja parando
            except Exception as ps_error:
                self.logger.warn(
                    f"PowerShell Stop-Service falhou: {ps_error}. Tentando sc.exe como fallback..."
                )

                # Fallback: usar sc.exe apenas se PowerShell falhar
                # Executar sc stop (comando nativo do Windows)
                # SC stop envia SERVICE_CONTROL_STOP que permite shutdown gracioso
                result = subprocess.run(
                    ["sc", "stop", self.service_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ),
                )

                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Erro desconhecido"
                    # Verificar se é erro 0xc0000142
                    if (
                        "0xc0000142" in error_msg
                        or "não pôde ser inicializado" in error_msg.lower()
                    ):
                        self.logger.error(
                            f"Erro 0xc0000142 ao executar sc.exe: {error_msg}"
                        )
                        self.logger.info(
                            "Continuando com verificação de status via PowerShell..."
                        )
                    else:
                        self.logger.warn(
                            f"SC stop retornou código {result.returncode}: {error_msg}"
                        )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Erro desconhecido"
                self.logger.warn(
                    f"SC stop retornou código {result.returncode}: {error_msg}"
                )
                # Continuar mesmo assim - pode ser que o serviço já esteja parando

            # Aguardar tempo suficiente para o servidor fazer backups e limpezas (até 2 minutos e 30 segundos)
            max_wait_time = 150  # 2 minutos e 30 segundos
            check_interval = 5  # Verificar a cada 5 segundos
            waited = 0

            while waited < max_wait_time:
                if not self._is_service_running():
                    self.logger.info(
                        f"Serviço parado graciosamente via SC após {waited} segundos"
                    )
                    return {
                        "success": True,
                        "message": "Serviço parado graciosamente via SC",
                    }
                time.sleep(check_interval)
                waited += check_interval
                if waited % 30 == 0:  # Log a cada 30 segundos
                    self.logger.info(
                        f"Aguardando shutdown gracioso... ({waited}/{max_wait_time}s)"
                    )

            # Se ainda estiver rodando após 2 minutos e 30 segundos, informar que está demorando
            self.logger.warn(
                "Serviço ainda rodando após 2 minutos e 30 segundos de shutdown gracioso via SC."
            )
            self.logger.warn(
                "O servidor pode estar processando muitos dados. Aguardando mais 60 segundos..."
            )

            # Aguardar mais 60 segundos adicionais
            additional_wait = 60
            additional_waited = 0

            while additional_waited < additional_wait:
                if not self._is_service_running():
                    total_time = max_wait_time + additional_waited
                    self.logger.info(
                        f"Serviço parado graciosamente via SC após {total_time} segundos"
                    )
                    return {
                        "success": True,
                        "message": f"Serviço parado graciosamente via SC após {total_time} segundos",
                    }
                time.sleep(check_interval)
                additional_waited += check_interval
                if additional_waited % 30 == 0:
                    self.logger.info(
                        f"Aguardando shutdown gracioso (tempo adicional: {additional_waited}/{additional_wait}s)..."
                    )

            # Verificar uma última vez
            if not self._is_service_running():
                total_time = max_wait_time + additional_wait
                self.logger.info(
                    f"Serviço parado graciosamente via SC após {total_time} segundos"
                )
                return {
                    "success": True,
                    "message": f"Serviço parado graciosamente via SC após {total_time} segundos",
                }
            else:
                self.logger.error(
                    "Serviço não parou após 3 minutos de shutdown gracioso via SC."
                )
                self.logger.error(
                    "Verifique os logs do servidor SCUM para identificar o problema."
                )
                return {
                    "success": False,
                    "message": "Serviço não parou após shutdown gracioso via SC (3 minutos). Verifique os logs do servidor.",
                }

        except subprocess.TimeoutExpired:
            self.logger.error("Timeout ao executar comando SC stop")
            return {"success": False, "message": "Timeout ao executar SC stop"}
        except Exception as e:
            self.logger.error(f"Erro no método SC: {e}")
            return {"success": False, "message": f"Erro SC: {str(e)}"}

    def _verify_startup(self) -> Dict[str, Any]:
        """Verificação final do startup"""
        try:
            self.logger.info("[FINAL] Verificando status do serviço...")
            time.sleep(5)

            if self._is_service_running():
                self.logger.info("=" * 40)
                self.logger.info("SERVIDOR SCUM INICIADO COM SUCESSO!")
                self.logger.info("=" * 40)
                self.logger.info("Status: RUNNING")
                self.logger.info("Serviço: SCUMServer (NSSM)")
                self.logger.info(f"Porta: {self.port} (conexão: {self.port + 2})")
                self.logger.info(f"Max Players: {self.max_players}")
                self.logger.info("O servidor está pronto para receber jogadores!")

                return {
                    "success": True,
                    "message": "Servidor iniciado com sucesso",
                    "status": "running",
                    "port": self.port,
                    "max_players": self.max_players,
                }
            else:
                self.logger.error(
                    "ERRO: O serviço não está rodando após a inicialização!"
                )
                self.logger.error("Verifique os logs do serviço para mais detalhes.")
                self.logger.info("SOLUÇÃO: Execute manualmente:")
                self.logger.info("1. Abra o Gerenciador de Serviços (services.msc)")
                self.logger.info("2. Encontre o serviço SCUMServer")
                self.logger.info("3. Clique com botão direito e selecione 'Iniciar'")
                self.logger.info(
                    f'4. Ou execute como administrador: "{self.nssm_path}" start {self.service_name}'
                )

                return {
                    "success": False,
                    "message": "Serviço não iniciou após comando",
                    "status": "verification_failed",
                }

        except Exception as e:
            self.logger.error(f"Erro na verificação: {e}")
            return {
                "success": False,
                "message": f"Erro na verificação: {str(e)}",
                "status": "verification_error",
            }

    def _verify_stop(
        self,
        scum_db_path: Optional[str] = None,
        elevated_users_manager=None,
        restart_cycle_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verificação final do stop

        Args:
            scum_db_path: Caminho opcional para SCUM.db
            elevated_users_manager: Instância opcional do ElevatedUsersManager para sincronização
            restart_cycle_id: ID do ciclo de reinicialização (opcional)
        """
        try:
            self.logger.info("[FINAL] Verificando status final...")
            time.sleep(3)

            if not self._is_service_running():
                self.logger.info("=" * 40)
                self.logger.info("SERVIDOR SCUM PARADO COM SUCESSO!")
                self.logger.info("=" * 40)
                self.logger.info("Status: STOPPED")
                self.logger.info("Serviço: SCUMServer (NSSM)")
                self.logger.info("O servidor foi parado com sucesso.")

                # Sincronizar elevated users (se fornecido)
                if elevated_users_manager:
                    try:
                        self.logger.info(
                            "Sincronizando elevated users após servidor parar..."
                        )
                        self.logger.info(
                            "Esta operação pode levar até 90 segundos para completar..."
                        )
                        sync_result = elevated_users_manager.sync_pending_changes()
                        if (
                            sync_result.get("success")
                            and sync_result.get("changes_count", 0) > 0
                        ):
                            self.logger.info(
                                f"Elevated users sincronizados: {sync_result.get('changes_count')} mudanças"
                            )
                            # Aguardar tempo adicional após sincronização para garantir que WAL/SHM sejam limpos
                            self.logger.info(
                                "Aguardando 30 segundos adicionais após sincronização para garantir limpeza de WAL/SHM..."
                            )
                            time.sleep(30)
                        else:
                            self.logger.info(
                                "Nenhuma mudança de elevated users para sincronizar"
                            )
                    except Exception as e:
                        self.logger.error(f"Erro ao sincronizar elevated users: {e}")
                        # Continuar mesmo se falhar

                # Limpar arquivos WAL/SHM após servidor parar
                try:
                    from utils.scum_db_cleanup import cleanup_scum_db_wal_files

                    # Obter caminho do SCUM.db se não foi fornecido
                    if not scum_db_path:
                        # Tentar usar fallbacks diretos
                        scum_db_path = (
                            self.config.get("weather_scheduler", {}).get("scum_db_path")
                            or self.config.get("fishing_ranking", {}).get(
                                "scum_db_path"
                            )
                            or "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
                        )

                    self.logger.info(
                        "Limpando arquivos WAL/SHM do SCUM.db após servidor parar..."
                    )

                    # Registrar ScumDbSharedCopyManager para fechar conexões antes de limpar
                    try:
                        from utils.scum_db_cleanup import set_shared_copy_manager
                        from utils.scum_db_shared_copy import get_shared_copy_manager

                        shared_copy_mgr = get_shared_copy_manager()
                        if shared_copy_mgr:
                            set_shared_copy_manager(shared_copy_mgr)
                    except Exception as e:
                        self.logger.warn(
                            f"Erro ao registrar ScumDbSharedCopyManager: {e}"
                        )

                    from utils.scum_db_cleanup import cleanup_scum_db_wal_files

                    cleanup_result = cleanup_scum_db_wal_files(
                        self,
                        scum_db_path,
                        self.logger,
                        wait_after_stop=0,  # Já aguardamos acima
                        wait_after_close=2.0,  # Aumentar tempo de espera após fechar conexão
                        restart_cycle_id=restart_cycle_id,
                    )
                    if cleanup_result.get("success"):
                        self.logger.info(
                            f"Limpeza de WAL/SHM: {cleanup_result.get('message')}"
                        )
                    else:
                        self.logger.warn(
                            f"Limpeza de WAL/SHM: {cleanup_result.get('message')}"
                        )
                except Exception as e:
                    self.logger.error(f"Erro ao limpar arquivos WAL/SHM: {e}")
                    # Continuar mesmo se falhar - não deve bloquear o stop

                return {
                    "success": True,
                    "message": "Servidor parado com sucesso",
                    "status": "stopped",
                }
            else:
                self.logger.warn("=" * 40)
                self.logger.warn("AVISO: SERVIÇO PODE ESTAR PROTEGIDO")
                self.logger.warn("=" * 40)
                self.logger.warn(
                    "O serviço SCUMServer (NSSM) pode estar configurado para:"
                )
                self.logger.warn("- Reinicialização automática pelo NSSM")
                self.logger.warn("- Proteção contra parada")
                self.logger.warn("- Configurações específicas do NSSM")
                self.logger.info("SOLUÇÃO MANUAL:")
                self.logger.info("1. Abra o Gerenciador de Serviços (services.msc)")
                self.logger.info("2. Encontre o serviço SCUMServer")
                self.logger.info("3. Clique com botão direito e selecione 'Parar'")
                self.logger.info(
                    f'4. Ou execute como administrador: "{self.nssm_path}" stop {self.service_name}'
                )
                self.logger.info("Comando para verificar: sc query SCUMServer")

                return {
                    "success": False,
                    "message": "Serviço pode estar protegido",
                    "status": "protected",
                }

        except Exception as e:
            self.logger.error(f"Erro na verificação: {e}")
            return {
                "success": False,
                "message": f"Erro na verificação: {str(e)}",
                "status": "verification_error",
            }

    def _process_vehicle_orders_offline(self, scum_db_path: str, ssm_db_path: str) -> None:
        """Processar entregas de veículos pendentes enquanto o servidor está offline."""
        try:
            from core.vehicles.vehicle_order_spawn_service import VehicleOrderSpawnService

            self.logger.info("[OFFLINE_JOBS] Iniciando processamento de pedidos de veículos...")

            # Templates DB path
            templates_db = "data/templates/SCUM_TEMPLATES.db"

            vehicle_service = VehicleOrderSpawnService(
                ssm_db_path=ssm_db_path,
                scum_db_path=scum_db_path,
                templates_db_path=templates_db,
                logger=self.logger,
            )

            # Criar um ID de ciclo temporário para o processamento offline
            cycle_id = f"offline_job_{int(time.time())}"

            result = vehicle_service.run_once(restart_cycle_id=cycle_id)
            self.logger.info(
                f"[OFFLINE_JOBS] Veículos processados: "
                f"total={result.claimed}, spawnados={result.spawned}, falhas={result.failed}"
            )
        except Exception as e:
            self.logger.error(f"[OFFLINE_JOBS] Erro no processamento de veículos offline: {e}")
            try:
                import traceback
                self.logger.error(f"[OFFLINE_JOBS] Traceback: {traceback.format_exc()}")
            except Exception:
                pass

    def _process_base_upgrades_offline(self, scum_db_path: str, ssm_db_path: str):
        """Processar upgrades de base pendentes enquanto o servidor está offline."""
        try:
            from core.base_material.base_material_job_service import BaseMaterialJobService

            self.logger.info("[OFFLINE_JOBS] Iniciando processamento de upgrades de base...")

            # Templates DB path
            templates_db = "data/templates/scum_base_template.db"

            base_service = BaseMaterialJobService(
                ssm_db_path=ssm_db_path,
                scum_db_path=scum_db_path,
                template_db_path=templates_db,
                logger=self.logger,
            )

            # Criar um ID de ciclo temporário para o processamento offline
            cycle_id = f"offline_job_base_{int(time.time())}"

            result = base_service.run_once(restart_cycle_id=cycle_id)
            self.logger.info(
                f"[OFFLINE_JOBS] Upgrades de base processados: "
                f"total={result.claimed}, atualizados={result.updated}, sem_mudancas={result.no_changes}, falhas={result.failed}"
            )
        except Exception as e:
            self.logger.error(f"[OFFLINE_JOBS] Erro no processamento de upgrades de base offline: {e}")
            try:
                import traceback
                self.logger.error(f"[OFFLINE_JOBS] Traceback: {traceback.format_exc()}")
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        """Obter status detalhado do servidor"""
        try:
            # Usar _is_service_running() que já tem tratamento melhorado
            is_running = self._is_service_running()

            # Obter informações detalhadas do serviço usando _get_service_state()
            # que já tem timeout aumentado e fallback para PowerShell
            state, stdout = self._get_service_state()

            service_info = {}
            if stdout:
                # Parsear informações do stdout
                lines = stdout.split("\n")
                for line in lines:
                    if ":" in line:
                        try:
                            key, value = line.split(":", 1)
                            service_info[key.strip()] = value.strip()
                        except:
                            pass

            # Adicionar estado se disponível
            if state:
                service_info["STATE"] = state

            return {
                "is_running": is_running,
                "service_name": self.service_name,
                "service_info": service_info,
                "server_path": self.server_path,
                "steamcmd_path": self.steamcmd_path,
                "install_path": self.install_path,
                "nssm_path": self.nssm_path,
                "port": self.port,
                "max_players": self.max_players,
                "use_battleye": self.use_battleye,
                "last_check": time.time(),
            }

        except subprocess.TimeoutExpired:
            # Timeout - retornar status básico sem informações detalhadas
            self.logger.warn(
                "Timeout ao obter status detalhado do serviço - retornando status básico"
            )
            return {
                "is_running": False,  # Assumir não rodando em caso de timeout
                "service_name": self.service_name,
                "service_info": {"STATE": "TIMEOUT"},
                "error": "Timeout ao verificar status do serviço",
                "last_check": time.time(),
            }
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Erro ao obter status: {error_msg}")

            # Se for erro de timeout, logar como warning
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                self.logger.warn(
                    f"Timeout ao verificar status do serviço: {error_msg}"
                )

            return {
                "is_running": False,
                "service_name": self.service_name,
                "error": error_msg,
                "last_check": time.time(),
            }
