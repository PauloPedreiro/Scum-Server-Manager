"""
Sistema de Logs Estruturado para SCUM Backend
"""

import logging
import logging.handlers
import os
import json
import re
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


class DbLockedFilter(logging.Filter):
    """Filtro que aceita apenas mensagens contendo 'database is locked' ou 'database is busy'"""

    _PATTERNS = ("database is locked", "database is busy", "db_locked", "sqlite3.operationalerror")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = (getattr(record, "msg", "") or "").lower()
        return any(p in msg for p in self._PATTERNS)


class StructuredLogger:
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        name: str = "scum_backend",
        filename: Optional[str] = None,
    ):
        # Configurações padrão - suportar múltiplos formatos de config
        self.logger_name = name
        if config:
            # Suportar formato antigo (logging.level) e novo (logging.log_level)
            log_level = config.get("log_level") or config.get("level", "info")
            if isinstance(log_level, str):
                self.log_level = log_level.lower()
            else:
                self.log_level = "info"

            # Suportar formato antigo e novo
            self.log_dir = config.get("log_dir") or config.get(
                "logs_directory", "data/logs"
            )
            self.max_size = config.get("max_size", "10MB")
            self.backup_count = config.get("backup_count", 5)

            # Validar e definir formato de log
            default_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            format_str = config.get("format", default_format)
        else:
            self.log_level = "info"
            self.log_dir = "data/logs"
            self.max_size = "10MB"
            self.backup_count = 5
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            default_format = format_str

        # Definir nome do arquivo de log
        self.log_filename = filename or f"{name}.log"

        # Se o formato for uma string especial (como 'detailed'), usar formato padrão
        if format_str and isinstance(format_str, str):
            if format_str.lower() in ["detailed", "simple", "json"]:
                # Formatos especiais não suportados pelo logging.Formatter, usar padrão
                self.format_str = default_format
            else:
                # Validar se é um formato válido do logging
                try:
                    # Testar se o formato é válido
                    test_formatter = logging.Formatter(format_str)
                    self.format_str = format_str
                except (ValueError, KeyError):
                    # Se inválido, usar padrão
                    self.format_str = default_format
        else:
            self.format_str = default_format

        # Criar diretório de logs
        self._setup_log_directory()

        # Configurar logger
        self._setup_logger()

    def _setup_log_directory(self):
        """Criar diretório de logs se não existir"""
        try:
            Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Erro ao criar diretório de logs: {e}")

    def _setup_logger(self):
        """Configurar logger"""
        # Criar logger
        self.logger = logging.getLogger(self.logger_name)

        # Converter nível de log para formato correto
        log_level_upper = self.log_level.upper()
        if log_level_upper == "INFO":
            log_level_upper = "INFO"
        elif log_level_upper == "DEBUG":
            log_level_upper = "DEBUG"
        elif log_level_upper == "WARNING" or log_level_upper == "WARN":
            log_level_upper = "WARNING"
        elif log_level_upper == "ERROR":
            log_level_upper = "ERROR"
        elif log_level_upper == "CRITICAL":
            log_level_upper = "CRITICAL"
        else:
            log_level_upper = "INFO"  # Padrão

        self.logger.setLevel(getattr(logging, log_level_upper, logging.INFO))

        # Limpar handlers existentes
        self.logger.handlers.clear()

        # Handler para arquivo com rotação (todos os logs)
        log_file = os.path.join(self.log_dir, self.log_filename)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self._parse_size(self.max_size),
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # Arquivo recebe todos os logs

        # Handler para console (apenas WARNING, ERROR e CRITICAL)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Console só mostra avisos e erros

        # Formatter para arquivo (detalhado)
        file_formatter = logging.Formatter(self.format_str)
        file_handler.setFormatter(file_formatter)

        # Formatter para console (simplificado - apenas mensagem)
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_formatter)

        # Adicionar handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # --- Handler especializado: ERRORS ONLY (errors.log) ---
        try:
            errors_log_file = os.path.join(self.log_dir, "errors.log")
            errors_handler = logging.handlers.RotatingFileHandler(
                errors_log_file,
                maxBytes=self._parse_size("5MB"),
                backupCount=3,
                encoding="utf-8",
            )
            errors_handler.setLevel(logging.ERROR)  # Apenas ERROR e CRITICAL
            errors_handler.setFormatter(file_formatter)
            self.logger.addHandler(errors_handler)
        except Exception:
            pass  # Não falhar se não conseguir criar o handler de erros

        # --- Handler especializado: DATABASE LOCKED (db_locked.log) ---
        try:
            db_locked_log_file = os.path.join(self.log_dir, "db_locked.log")
            db_locked_handler = logging.handlers.RotatingFileHandler(
                db_locked_log_file,
                maxBytes=self._parse_size("5MB"),
                backupCount=3,
                encoding="utf-8",
            )
            db_locked_handler.setLevel(logging.DEBUG)  # Capturar qualquer nível
            db_locked_handler.addFilter(DbLockedFilter())  # Filtrar por conteúdo
            db_locked_handler.setFormatter(file_formatter)
            self.logger.addHandler(db_locked_handler)
        except Exception:
            pass  # Não falhar se não conseguir criar o handler de db_locked

        # Evitar propagação para logger root
        self.logger.propagate = False

    def _parse_size(self, size_str: str) -> int:
        """Converter string de tamanho para bytes"""
        size_str = size_str.upper()
        if size_str.endswith("KB"):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith("MB"):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith("GB"):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)

    def _format_message(
        self, level: str, message: str, data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Formatar mensagem de log"""
        # Sanitizar mensagem e dados antes de formatar
        sanitized_message = self._sanitize_message(message)
        sanitized_data = self._sanitize_data(data)

        timestamp = datetime.now().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "level": level.upper(),
            "message": sanitized_message,
        }

        if sanitized_data:
            log_entry["data"] = sanitized_data

        return json.dumps(log_entry, ensure_ascii=False)

    def log(self, level: str, message: str, data: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Log genérico"""
        if exc_info:
            import traceback
            tb = traceback.format_exc()
            if tb and "NoneType: None" not in tb:
                if data is None:
                    data = {}
                data["traceback"] = tb.strip()
        formatted_message = self._format_message(level, message, data)
        getattr(self.logger, level.lower())(formatted_message, **kwargs)

    def debug(self, message: str, data: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Log de debug"""
        self.log("debug", message, data, exc_info=exc_info, **kwargs)

    def info(self, message: str, data: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Log de informação"""
        self.log("info", message, data, exc_info=exc_info, **kwargs)

    def warn(self, message: str, data: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Log de aviso"""
        self.log("warn", message, data, exc_info=exc_info, **kwargs)

    def warning(self, message: str, data: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Alias para warn() - compatibilidade com logging padrão"""
        self.warn(message, data, exc_info=exc_info, **kwargs)

    def error(self, message: str, data: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Log de erro"""
        self.log("error", message, data, exc_info=exc_info, **kwargs)

    def exception(self, message: str, data: Optional[Dict[str, Any]] = None, **kwargs):
        """Log de erro com traceback completo"""
        self.log("error", message, data, exc_info=True, **kwargs)

    def critical(self, message: str, data: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Log crítico"""
        self.log("critical", message, data, exc_info=exc_info, **kwargs)


    # Logs específicos para diferentes módulos
    def server(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log específico do servidor"""
        self.info(f"[SERVER] {message}", data)

    def steam(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log específico do Steam"""
        self.info(f"[STEAM] {message}", data)

    def nssm(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log específico do NSSM"""
        self.info(f"[NSSM] {message}", data)

    def powershell(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log específico do PowerShell"""
        self.info(f"[POWERSHELL] {message}", data)

    def api(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log específico da API"""
        self.info(f"[API] {message}", data)

    def command(
        self,
        command: str,
        player: str = None,
        steam_id: str = None,
        vehicle_id: str = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Log específico de comandos"""
        # Mascarar Steam ID para segurança
        masked_steam_id = self._mask_steam_id(steam_id) if steam_id else None

        log_data = {
            "command": command,
            "player": player,
            "steam_id": masked_steam_id,
            "vehicle_id": vehicle_id,
        }

        if data:
            log_data.update(data)

        self.info(
            f"[COMMAND] /{command} | {player} ({masked_steam_id}) | Veículo: {vehicle_id}",
            log_data,
        )

    def _mask_steam_id(self, steam_id: str) -> str:
        """Mascarar Steam ID para segurança"""
        if not steam_id or len(steam_id) < 8:
            return steam_id

        first = steam_id[:4]
        last = steam_id[-4:]
        return f"{first}****{last}"

    def _sanitize_message(self, message: str) -> str:
        """
        Sanitizar mensagem de log removendo informações sensíveis:
        - Caminhos completos de arquivos
        - URLs e endpoints
        - Informações de configuração
        """
        if not message:
            return message

        # Remover caminhos completos (C:\... ou /path/to/...)
        message = re.sub(r"[A-Z]:\\[^\s\)]+", "[PATH]", message)
        # Não capturar padrões numéricos simples como "30/30", apenas caminhos reais
        # Primeiro, proteger padrões numéricos do tipo "número/número" substituindo temporariamente
        # Depois aplicar a regex de caminhos e restaurar os padrões numéricos
        numeric_pattern = re.compile(r"\b([0-9]+)/([0-9]+)\b")
        numeric_replacements = {}
        replacement_counter = 0

        def replace_numeric(match):
            nonlocal replacement_counter
            placeholder = f"__NUMERIC_{replacement_counter}__"
            numeric_replacements[placeholder] = match.group(0)
            replacement_counter += 1
            return placeholder

        # Substituir temporariamente padrões numéricos
        message = numeric_pattern.sub(replace_numeric, message)

        # Aplicar regex de caminhos
        message = re.sub(r"/[^\s\)]+", "[PATH]", message)

        # Restaurar padrões numéricos
        for placeholder, original in numeric_replacements.items():
            message = message.replace(placeholder, original)

        # Remover URLs completas (http://... ou https://...)
        message = re.sub(r"https?://[^\s\)]+", "[URL]", message)

        # Remover webhooks do Discord
        message = re.sub(r"discord\.com/api/webhooks/[^\s\)]+", "[WEBHOOK]", message)

        # Remover IPs completos (manter apenas indicação)
        message = re.sub(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "[IP]", message)

        # Remover caminhos relativos muito detalhados
        message = re.sub(r"data\\[^\s\)]+", "[DATA_PATH]", message)
        message = re.sub(r"data/[^\s\)]+", "[DATA_PATH]", message)

        return message

    def _sanitize_data(
        self, data: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Sanitizar dados de log removendo informações sensíveis
        """
        if not data:
            return data

        sanitized = {}
        sensitive_keys = [
            "path",
            "db_path",
            "config_path",
            "scum_db_path",
            "ssm_db_path",
            "server_url",
            "url",
            "endpoint",
            "webhook",
            "api_key",
            "key",
            "full_path",
            "file_path",
            "directory",
            "logs_directory",
            "scum_config_path",
            "binaries_directory",
            "root_directory",
            "savefiles_directory",
        ]

        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str):
                # Sanitizar strings que possam conter caminhos ou URLs
                if any(char in value for char in ["C:\\", "http://", "https://", "/"]):
                    sanitized[key] = self._sanitize_message(value)
                else:
                    sanitized[key] = value
            elif isinstance(value, dict):
                # Recursivamente sanitizar dicionários aninhados
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                # Sanitizar listas
                sanitized[key] = [
                    self._sanitize_message(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def get_log_file_path(self) -> str:
        """Obter caminho do arquivo de log atual"""
        return os.path.join(self.log_dir, "scum_backend.log")

    def get_log_files(self) -> list:
        """Obter lista de arquivos de log"""
        log_files = []
        log_dir = Path(self.log_dir)

        if log_dir.exists():
            for pattern in ["scum_backend.log*", "errors.log*", "db_locked.log*"]:
                for file in log_dir.glob(pattern):
                    log_files.append(str(file))

        return sorted(log_files, reverse=True)  # Mais recentes primeiro
