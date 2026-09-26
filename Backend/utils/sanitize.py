"""
Funções de sanitização de logs e dados sensíveis.
Extraído do main.py durante refatoração modular.
"""

import re
from typing import Dict, Any, Optional


def sanitize_log_message(message: str) -> str:
    """
    Sanitizar mensagem de log removendo informações sensíveis:
    - Caminhos completos de arquivos
    - URLs e endpoints
    - Informações de configuração
    """
    if not message:
        return message

    # Remover caminhos completos (C:\... ou /path/to/...)
    message = re.sub(r"[A-Z]:\\[^\s]+", "[PATH]", message)
    message = re.sub(r"/[^\s]+", "[PATH]", message)

    # Remover URLs completas (http://... ou https://...)
    message = re.sub(r"https?://[^\s]+", "[URL]", message)

    # Remover webhooks do Discord
    message = re.sub(r"discord\.com/api/webhooks/[^\s]+", "[WEBHOOK]", message)

    # Remover IPs completos (manter apenas indicação)
    message = re.sub(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "[IP]", message)

    # Remover caminhos relativos muito detalhados
    message = re.sub(r"data\\[^\s]+", "[DATA_PATH]", message)
    message = re.sub(r"data/[^\s]+", "[DATA_PATH]", message)

    return message


def sanitize_log_data(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
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
    ]

    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str):
            # Sanitizar strings que possam conter caminhos ou URLs
            if any(char in value for char in ["C:\\", "http://", "https://", "/"]):
                sanitized[key] = sanitize_log_message(value)
            else:
                sanitized[key] = value
        else:
            sanitized[key] = value

    return sanitized


def sanitize_rcon_command_coords(command: str) -> str:
    """
    Sanitiza e formata coordenadas SCUM em comandos RCON específicos.
    Converte o formato de telemetria Unreal: {X=... Y=... Z=...|P=...} ou {X=... Y=... Z=...}
    em valores numéricos limpos separados por espaço.

    Para o comando #ScheduleWorldEvent:
      - Se houver formato {X=... Y=... Z=...|...}, extrai X e Y e força Z como 0 (ex: "X Y 0").
      - Se as coordenadas já estiverem limpas por espaço (ex: "X Y Z"), mas for #ScheduleWorldEvent,
        força a coordenada Z para "0".

    Para o comando #teleport:
      - Extrai X, Y, Z e mantém o Z original para evitar problemas de queda/colisão.
    """
    if not command:
        return command

    command_stripped = command.strip()
    cmd_lower = command_stripped.lower()

    # Se não for um dos comandos que usam coordenadas espaciais, retorna como está
    is_world_event = cmd_lower.startswith("#scheduleworldevent") or cmd_lower.startswith("scheduleworldevent")
    is_teleport = cmd_lower.startswith("#teleport") or cmd_lower.startswith("teleport")

    if not (is_world_event or is_teleport):
        return command_stripped

    import re
    coord_pattern = r'\{X=([\d\.\-]+)[,\s]+Y=([\d\.\-]+)[,\s]+Z=([\d\.\-]+)[^}]*\}'

    # Caso 1: Contém o formato em chaves {X=...}
    match = re.search(coord_pattern, command_stripped, re.IGNORECASE)
    if match:
        x, y, z = match.group(1), match.group(2), match.group(3)
        if is_world_event:
            replacement = f"{x} {y} 0"
        else:
            replacement = f"{x} {y} {z}"

        # Substitui o bloco com chaves pelos valores limpos
        sanitized = re.sub(coord_pattern, replacement, command_stripped)

        # Remove aspas redundantes em torno de coordenadas numéricas limpas
        sanitized = re.sub(r'"([\d\.\-\s]+)"', r'\1', sanitized)
        return sanitized

    # Caso 2: Se for #ScheduleWorldEvent e já estiver em formato de espaço, mas com Z não-zero
    if is_world_event:
        # Padrão: #ScheduleWorldEvent <NomeDoEvento> <X> <Y> <Z>
        match_spaces = re.search(
            r'^((?:#)?scheduleworldevent\s+\S+\s+[\d\.\-]+[,\s]+[\d\.\-]+[,\s]+)([\d\.\-]+)$',
            command_stripped,
            re.IGNORECASE
        )
        if match_spaces:
            prefix = match_spaces.group(1).replace(',', ' ')
            # Força o Z a ser 0
            return f"{prefix.strip()} 0"

    return command_stripped

