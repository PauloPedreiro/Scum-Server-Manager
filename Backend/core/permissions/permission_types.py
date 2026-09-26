"""
Definições de tipos de permissão e mapeamento para arquivos .ini
"""

# Mapeamento de tipos de permissão para arquivos .ini
PERMISSION_FILE_MAPPING = {
    "admin": "AdminUsers.ini",
    "banned": "BannedUsers.ini",
    "exclusive": "ExclusiveUsers.ini",
    "server_admin": "ServerSettingsAdminUsers.ini",
    "silenced": "SilencedUsers.ini",
    "whitelisted": "WhitelistedUsers.ini",
}

# Tipos de permissão que existem apenas no banco (não possuem arquivo INI)
DB_ONLY_PERMISSION_TYPES = {
    "raid_webhook_manage",
}

# Tipos de permissão disponíveis
PERMISSION_TYPES = list(PERMISSION_FILE_MAPPING.keys()) + list(DB_ONLY_PERMISSION_TYPES)

# Formato específico para cada arquivo .ini
FILE_FORMATS = {
    "AdminUsers.ini": "{steam_id}[setgodmode]",
    "BannedUsers.ini": "{steam_id}",
    "ExclusiveUsers.ini": "{steam_id}",
    "ServerSettingsAdminUsers.ini": "{steam_id}",
    "SilencedUsers.ini": "{steam_id}",
    "WhitelistedUsers.ini": "{steam_id}",
}


def format_steam_id_for_file(steam_id: str, permission_type: str) -> str:
    """
    Formatar Steam ID para o arquivo .ini específico

    Args:
        steam_id: Steam ID do jogador
        permission_type: Tipo de permissão

    Returns:
        Steam ID formatado conforme o formato do arquivo
    """
    file_name = PERMISSION_FILE_MAPPING.get(permission_type)
    if not file_name:
        raise ValueError(f"Tipo de permissão inválido: {permission_type}")

    format_pattern = FILE_FORMATS.get(file_name, "{steam_id}")
    return format_pattern.format(steam_id=steam_id)


def validate_permission_type(permission_type: str) -> bool:
    """
    Validar se o tipo de permissão é válido

    Args:
        permission_type: Tipo de permissão a validar

    Returns:
        True se válido, False caso contrário
    """
    return permission_type in PERMISSION_TYPES


def validate_steam_id(steam_id: str) -> bool:
    """
    Validar formato do Steam ID

    Args:
        steam_id: Steam ID a validar

    Returns:
        True se válido, False caso contrário
    """
    return steam_id.isdigit() and len(steam_id) == 17
