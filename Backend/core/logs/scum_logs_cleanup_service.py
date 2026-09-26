"""Serviço de limpeza periódica dos logs do SCUM (Saved\\SaveFiles\\Logs)."""

import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import schedule

from utils.logger import StructuredLogger


@dataclass
class ScumLogsCleanupStats:
    scanned_files: int = 0
    deleted_files: int = 0
    skipped_files: int = 0
    errors: int = 0
    bytes_before: int = 0
    bytes_after: int = 0


class ScumLogsCleanupService:
    def __init__(
        self,
        config: Dict[str, Any],
        path_helper=None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.logger = logger or StructuredLogger()
        self.config = config or {}
        self.cleanup_config = self.config.get("scum_logs_cleanup", {})

        self.enabled = bool(self.cleanup_config.get("enabled", True))
        self.auto_start = bool(self.cleanup_config.get("auto_start", True))
        self.run_on_startup = bool(self.cleanup_config.get("run_on_startup", False))

        self.retention_days = int(self.cleanup_config.get("retention_days", 14) or 14)
        self.min_age_hours = int(self.cleanup_config.get("min_age_hours", 24) or 24)

        self.schedule_time = self.cleanup_config.get("schedule_time", "03:30")
        self.interval_hours = int(self.cleanup_config.get("interval_hours", 24) or 24)

        max_total_size_mb = self.cleanup_config.get("max_total_size_mb", None)
        self.max_total_size_mb = (
            int(max_total_size_mb) if max_total_size_mb is not None else None
        )

        self.file_extensions = self.cleanup_config.get("file_extensions", None)
        if isinstance(self.file_extensions, str):
            self.file_extensions = [self.file_extensions]
        if not self.file_extensions or not isinstance(self.file_extensions, (list, tuple)):
            self.file_extensions = [".log", ".txt", ".dmp", ".bak"]

        default_logs_dir = (
            path_helper.get_scum_logs_directory()
            if path_helper
            else "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\Logs"
        )
        self.logs_directory = self.cleanup_config.get("logs_directory") or default_logs_dir

        self.scheduler = schedule.Scheduler()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False

        self.last_cleanup_info: Dict[str, Any] = {
            "timestamp": None,
            "status": "never_run",
            "details": {},
        }

        self.logger.info(
            "ScumLogsCleanupService inicializado",
            {
                "enabled": self.enabled,
                "auto_start": self.auto_start,
                "run_on_startup": self.run_on_startup,
                "logs_directory": self.logs_directory,
                "retention_days": self.retention_days,
                "min_age_hours": self.min_age_hours,
                "schedule_time": self.schedule_time,
                "interval_hours": self.interval_hours,
                "max_total_size_mb": self.max_total_size_mb,
            },
        )

    def _is_allowed_file(self, file_name: str) -> bool:
        if not self.file_extensions:
            return True
        lower = file_name.lower()
        return any(lower.endswith(str(ext).lower()) for ext in self.file_extensions)

    def _list_log_files(self) -> List[str]:
        try:
            if not os.path.isdir(self.logs_directory):
                return []
            files = []
            for name in os.listdir(self.logs_directory):
                full = os.path.join(self.logs_directory, name)
                if os.path.isfile(full) and self._is_allowed_file(name):
                    files.append(full)
            return files
        except Exception as e:
            self.logger.error(f"Erro ao listar logs do SCUM: {e}")
            return []

    def _get_file_mtime(self, path: str) -> Optional[datetime]:
        try:
            return datetime.fromtimestamp(os.path.getmtime(path))
        except Exception:
            return None

    def _get_file_size(self, path: str) -> int:
        try:
            return int(os.path.getsize(path))
        except Exception:
            return 0

    def _compute_total_size(self, files: List[str]) -> int:
        total = 0
        for f in files:
            total += self._get_file_size(f)
        return total

    def _delete_file(self, path: str) -> Tuple[bool, str]:
        try:
            os.remove(path)
            return True, "deleted"
        except PermissionError as e:
            return False, f"permission_error: {e}"
        except OSError as e:
            return False, f"os_error: {e}"
        except Exception as e:
            return False, f"error: {e}"

    def _cleanup_once(self, is_manual: bool = False) -> Dict[str, Any]:
        stats = ScumLogsCleanupStats()
        now = datetime.now()

        files = self._list_log_files()
        stats.scanned_files = len(files)

        if not files:
            self.last_cleanup_info = {
                "timestamp": datetime.now().isoformat(),
                "status": "no_files",
                "details": {
                    "logs_directory": self.logs_directory,
                    "scanned_files": 0,
                },
            }
            return {"success": True, "status": "no_files", "data": self.last_cleanup_info}

        stats.bytes_before = self._compute_total_size(files)

        min_age_cutoff = now - timedelta(hours=max(self.min_age_hours, 0))
        retention_cutoff = now - timedelta(days=max(self.retention_days, 0))

        deletable_by_age: List[Tuple[datetime, str]] = []
        protected_recent: List[str] = []

        for f in files:
            mtime = self._get_file_mtime(f)
            if not mtime:
                stats.skipped_files += 1
                continue

            if mtime >= min_age_cutoff:
                protected_recent.append(f)
                stats.skipped_files += 1
                continue

            if self.retention_days > 0 and mtime < retention_cutoff:
                deletable_by_age.append((mtime, f))
            else:
                stats.skipped_files += 1

        deletable_by_age.sort(key=lambda x: x[0])

        errors: List[Dict[str, Any]] = []

        for _, f in deletable_by_age:
            ok, reason = self._delete_file(f)
            if ok:
                stats.deleted_files += 1
            else:
                stats.errors += 1
                errors.append({"file": f, "reason": reason})

        remaining_files = self._list_log_files()

        if self.max_total_size_mb is not None and self.max_total_size_mb > 0:
            max_bytes = int(self.max_total_size_mb) * 1024 * 1024
            total_size = self._compute_total_size(remaining_files)

            if total_size > max_bytes:
                candidates: List[Tuple[datetime, str]] = []
                for f in remaining_files:
                    mtime = self._get_file_mtime(f)
                    if not mtime:
                        continue
                    if mtime >= min_age_cutoff:
                        continue
                    candidates.append((mtime, f))

                candidates.sort(key=lambda x: x[0])

                for _, f in candidates:
                    if total_size <= max_bytes:
                        break
                    size = self._get_file_size(f)
                    ok, reason = self._delete_file(f)
                    if ok:
                        stats.deleted_files += 1
                        total_size = max(0, total_size - size)
                    else:
                        stats.errors += 1
                        errors.append({"file": f, "reason": reason})

        final_files = self._list_log_files()
        stats.bytes_after = self._compute_total_size(final_files)

        self.last_cleanup_info = {
            "timestamp": datetime.now().isoformat(),
            "status": "completed" if stats.errors == 0 else "completed_with_errors",
            "details": {
                "logs_directory": self.logs_directory,
                "scanned_files": stats.scanned_files,
                "deleted_files": stats.deleted_files,
                "skipped_files": stats.skipped_files,
                "errors": stats.errors,
                "bytes_before": stats.bytes_before,
                "bytes_after": stats.bytes_after,
                "retention_days": self.retention_days,
                "min_age_hours": self.min_age_hours,
                "max_total_size_mb": self.max_total_size_mb,
                "errors_detail": errors[:50],
            },
        }

        if stats.deleted_files > 0 or stats.errors > 0:
            self.logger.info(
                "Limpeza de logs do SCUM executada",
                {
                    "deleted": stats.deleted_files,
                    "errors": stats.errors,
                    "bytes_before": stats.bytes_before,
                    "bytes_after": stats.bytes_after,
                    "logs_directory": self.logs_directory,
                },
            )

        # Enviar relatório para o canal log-ssm no Discord se houver arquivos limpos ou se for disparo manual
        if stats.deleted_files > 0 or is_manual:
            self._send_discord_cleanup_report(stats, is_manual=is_manual)

        return {"success": True, "status": self.last_cleanup_info["status"], "data": self.last_cleanup_info}

    def _send_discord_cleanup_report(self, stats: ScumLogsCleanupStats, is_manual: bool = False):
        """Send cleanup report embed to log-ssm webhook in English"""
        try:
            from core.webhooks.discord_webhook import DiscordWebhook
            discord = DiscordWebhook(self.config, self.logger)

            freed_bytes = max(0, stats.bytes_before - stats.bytes_after)
            if freed_bytes >= 1024 * 1024 * 1024:
                freed_str = f"{freed_bytes / (1024 * 1024 * 1024):.2f} GB"
            else:
                freed_str = f"{freed_bytes / (1024 * 1024):.2f} MB"

            trigger_str = "Manual Admin Trigger" if is_manual else f"Scheduled Maintenance ({self.schedule_time})"
            color = 0x2ECC71 if stats.errors == 0 else 0xE67E22

            folder_name = os.path.basename(self.logs_directory.rstrip("\\/")) or "Logs"

            fields = [
                {"name": "🗑️ Files Deleted", "value": f"**{stats.deleted_files}** files", "inline": True},
                {"name": "💾 Disk Space Freed", "value": f"**{freed_str}**", "inline": True},
                {"name": "🛡️ Protected Files", "value": f"**{stats.skipped_files}** files (recent / active)", "inline": True},
                {"name": "⏱️ Execution Trigger", "value": trigger_str, "inline": True},
                {"name": "📅 Retention Rule", "value": f"{self.retention_days} days (min {self.min_age_hours}h)", "inline": True},
                {"name": "📁 Target Folder", "value": f"`{folder_name}`", "inline": True},
            ]
            if stats.errors > 0:
                fields.append({"name": "⚠️ Warnings", "value": f"{stats.errors} files in use could not be removed", "inline": False})

            discord.send_webhook(
                webhook_name="log-ssm",
                title="🧹 SCUM Server Logs Cleanup Completed",
                description="Server log cleanup routine executed successfully to free up disk space.",
                color=color,
                fields=fields,
            )
        except Exception as e:
            self.logger.warn(f"Failed to send logs cleanup embed to log-ssm: {e}")

    def _scheduler_loop(self):
        while not self.stop_event.is_set():
            try:
                self.scheduler.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Erro no loop do ScumLogsCleanupService: {e}")
                time.sleep(5)

    def start(self) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "success": False,
                "message": "Limpeza de logs do SCUM desabilitada",
                "status": "disabled",
            }

        if self.is_running:
            return {
                "success": False,
                "message": "ScumLogsCleanupService já está rodando",
                "status": "already_running",
            }

        try:
            self.scheduler.clear()

            if self.schedule_time and isinstance(self.schedule_time, str):
                self.scheduler.every().day.at(self.schedule_time).do(self._cleanup_once)
            else:
                self.scheduler.every(max(self.interval_hours, 1)).hours.do(self._cleanup_once)

            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True, name="ScumLogsCleanupThread"
            )
            self.scheduler_thread.start()
            self.is_running = True

            if self.run_on_startup:
                try:
                    self._cleanup_once()
                except Exception as e:
                    self.logger.error(f"Erro ao executar limpeza no startup: {e}")

            return {
                "success": True,
                "message": "ScumLogsCleanupService iniciado",
                "status": "started",
            }

        except Exception as e:
            self.logger.error(f"Erro ao iniciar ScumLogsCleanupService: {e}")
            return {
                "success": False,
                "message": f"Erro ao iniciar ScumLogsCleanupService: {str(e)}",
                "status": "error",
            }

    def stop(self) -> Dict[str, Any]:
        if not self.is_running:
            return {
                "success": False,
                "message": "ScumLogsCleanupService não está rodando",
                "status": "not_running",
            }

        try:
            self.is_running = False
            self.stop_event.set()

            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)

            self.scheduler.clear()

            return {
                "success": True,
                "message": "ScumLogsCleanupService parado",
                "status": "stopped",
            }

        except Exception as e:
            self.logger.error(f"Erro ao parar ScumLogsCleanupService: {e}")
            return {
                "success": False,
                "message": f"Erro ao parar ScumLogsCleanupService: {str(e)}",
                "status": "error",
            }

    def get_status(self) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {
                "enabled": self.enabled,
                "is_running": self.is_running,
                "logs_directory": self.logs_directory,
                "retention_days": self.retention_days,
                "min_age_hours": self.min_age_hours,
                "schedule_time": self.schedule_time,
                "interval_hours": self.interval_hours,
                "max_total_size_mb": self.max_total_size_mb,
                "last_cleanup": self.last_cleanup_info,
                "scheduled_jobs": len(self.scheduler.jobs),
            },
        }

    def run_now(self) -> Dict[str, Any]:
        """Executar limpeza imediatamente sob demanda."""
        try:
            return self._cleanup_once(is_manual=True)
        except Exception as e:
            self.logger.error(f"Erro ao executar limpeza agora: {e}")
            return {
                "success": False,
                "message": f"Erro ao executar limpeza agora: {str(e)}",
                "status": "error",
            }

    def update_config(self, new_cleanup_config: Dict[str, Any]) -> None:
        """Atualizar configurações em tempo de execução sem reiniciar o backend."""
        try:
            self.cleanup_config.update(new_cleanup_config or {})
            self.enabled = bool(self.cleanup_config.get("enabled", self.enabled))
            self.retention_days = int(self.cleanup_config.get("retention_days", self.retention_days) or 14)
            self.min_age_hours = int(self.cleanup_config.get("min_age_hours", self.min_age_hours) or 24)
            self.schedule_time = str(self.cleanup_config.get("schedule_time", self.schedule_time) or "03:30")
            max_size = self.cleanup_config.get("max_total_size_mb")
            self.max_total_size_mb = int(max_size) if max_size is not None else None

            if self.is_running:
                self.scheduler.clear()
                if self.schedule_time:
                    self.scheduler.every().day.at(self.schedule_time).do(self._cleanup_once)
                else:
                    self.scheduler.every(max(self.interval_hours, 1)).hours.do(self._cleanup_once)
        except Exception as e:
            self.logger.warn(f"Erro ao atualizar configuração de ScumLogsCleanupService: {e}")
