# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File para SSM Backend
"""

import sys
from pathlib import Path

block_cipher = None

# Diretório raiz do projeto
import os
# PyInstaller define SPECPATH quando processa o spec file
# build.py executa PyInstaller com cwd=ROOT_DIR, então Path.cwd() deve funcionar
# Mas SPECPATH pode apontar para um caminho diferente, então vamos usar ambos
try:
    # Primeiro, tentar usar SPECPATH (definido pelo PyInstaller)
    if 'SPECPATH' in globals():
        spec_path = Path(SPECPATH).resolve()
        # O spec file está em Backend/ssm_backend.spec
        # O diretório do spec é o ROOT_DIR
        spec_dir = spec_path.parent.resolve()
        # Verificar se o spec file realmente existe neste diretório
        if (spec_dir / 'ssm_backend.spec').exists():
            ROOT_DIR = spec_dir
        else:
            # Se não, usar o diretório de trabalho atual (definido por build.py)
            ROOT_DIR = Path.cwd().resolve()
    else:
        # Se SPECPATH não estiver disponível, usar diretório de trabalho atual
        ROOT_DIR = Path.cwd().resolve()
except Exception as e:
    # Último fallback: diretório de trabalho atual
    ROOT_DIR = Path.cwd().resolve()
    print(f"[PyInstaller] Erro ao calcular ROOT_DIR: {e}, usando: {ROOT_DIR}")

# Arquivos de dados a serem incluídos
datas = [
    # Arquivos de configuração reais
    # Distribuicao: usar template limpo (config.example.json) como config.json
    ('data/config.example.json', 'data/config.json'),
    # Distribuicao: usar template limpo (webhooks.example.json) como webhooks.json
    ('data/webhooks.example.json', 'data/webhooks.json'),
    
    # Arquivos de configuração exemplo (backup)
    ('data/config.example.json', 'data'),
    ('data/webhooks.example.json', 'data'),
    
    # Diretório de imagens completo
    ('data/imagens', 'data/imagens'),
    
    # Arquivos de coordenadas
    ('base_coordinates.csv', '.'),
    ('base_coordinates.json', '.'),
    
    # Diretório nssm
    ('nssm-2.24', 'nssm-2.24'),
    
    # Templates de notificações
    ('data/notifications', 'data/notifications'),

    # Templates / banco de templates (SCUM_TEMPLATES.db)
    ('data/templates', 'data/templates'),

    # Mods directory (RCON engines, UE4SS core, Pak mods library)
    ('data/mods', 'data/mods'),
]

# Certificados SSL do certifi (necessário para discord.py no Windows empacotado)
try:
    import certifi
    datas.append((str(certifi.where()), 'certifi'))
except Exception:
    pass

# Binários ocultos (se necessário)
binaries = []


# Análise do script principal (mantida para mapeamento de dependências)
# NOTA: O executável SSM Backend.exe foi removido, mas a análise é mantida
# para que o PyInstaller possa mapear todas as dependências do projeto
a = Analysis(
    ['main.py'],
    pathex=[str(ROOT_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'flask',
        'flask_cors',
        'psutil',
        'requests',
        'schedule',
        'sqlite3',
        'json',
        'threading',
        'datetime',
        'pathlib',
        # Windows API (pywin32) - necessário para single instance
        'win32event',
        'win32api',
        'win32gui',
        'win32con',
        'winerror',
        'win32process',
        # Core modules
        'core.server_control.server_manager',
        'core.scheduler.restart_scheduler',
        'core.scheduler.weather_scheduler',
        'core.webhooks.discord_webhook',
        'core.notifications.notification_manager',
        'core.identity.backend_id',
        'core.identity.owner_manager',
        'core.communication.heartbeat_manager',
        'core.communication.remote_commands',
        'core.communication.license_validator',
        'core.communication.license_validator_integrity',
        'core.logs.log_processor',
        'core.logs.online_monitor',
        'core.logs.chat_processor',
        'core.logs.bunker_processor',
        'core.logs.chat_command_monitor',
        'core.logs.fishing_ranking_manager',
        'core.permissions.permission_manager',
        'core.permissions.ini_manager',
        'core.squads.squad_sync_service',
        'core.survival.survival_stats_sync_service',
        'core.survival.player_skills_sync_service',
        'core.survival.rankings_update_service',
        'core.survival.lockpicking_ranking_service',
        'core.survival.kills_ranking_service',
        'core.survival.snipers_ranking_service',
        'core.chests.chest_sync_service',
        'core.vehicles.vehicle_verification_service',
        'core.vehicles.vehicle_order_spawn_service',
        'core.base_material.base_material_job_service',
        'core.gps.player_gps_sync_service',
        'core.elevated_users.elevated_users_manager',
        'utils.config_path_helper',
        'utils.logger',
        'utils.single_instance',  # Single instance management
        'utils.database_initializer',  # Database initialization module
        'utils.rcon_mod_manager',
        'utils.pak_mod_manager',
        'utils.rcon_logger',
        'utils.bsbr_client',
        'utils.rcon_client',
        # Discord Bot
        'discord',
        'discord.ext',
        'discord.ext.commands',
        'discord.app_commands',
        'aiohttp',
        'certifi',
        'core.discord_bot_service',
    ],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Caminho do ícone (usar multi-tamanho para melhor compatibilidade no Windows)
# Usar Kit_SSM_Multi.ico como ícone principal
# Tentar múltiplos caminhos possíveis
possible_roots = [
    ROOT_DIR,
    ROOT_DIR / 'Backend',
    Path.cwd().resolve(),
    Path.cwd().resolve() / 'Backend',
]

# Encontrar o diretório correto que contém o ícone
icon_root = None
for root in possible_roots:
    test_path = root / 'data' / 'imagens' / 'LogoSSM' / 'W-SSM-Ico.ico'
    if test_path.exists():
        icon_root = root
        break

# Se não encontrou, usar ROOT_DIR mesmo
if icon_root is None:
    icon_root = ROOT_DIR

ssm_ico_windows_path = icon_root / 'data' / 'imagens' / 'LogoSSM' / 'W-SSM-Ico.ico'
icon_path = ssm_ico_windows_path

# Converter para caminho absoluto e string para garantir compatibilidade com PyInstaller
if icon_path.exists():
    icon_absolute = str(icon_path.resolve())
    print(f"[PyInstaller] Usando ícone: {icon_absolute}")
    backend_icon = icon_absolute
    config_editor_icon = icon_absolute
    launcher_icon = icon_absolute
    gui_icon = icon_absolute
else:
    print(f"[PyInstaller] ERRO: Ícone obrigatório não encontrado!")
    print(f"[PyInstaller]   ROOT_DIR: {ROOT_DIR}")
    print(f"[PyInstaller]   icon_root: {icon_root}")
    print(f"[PyInstaller]   Esperado: {icon_path}")
    raise SystemExit(1)

# REMOVIDO: Build do SSM Backend.exe (agora integrado no Panel SSM.exe)
# O backend Flask agora roda em thread dentro do Panel SSM
# if False:  # Desabilitado - backend integrado no Panel SSM
#     exe = EXE(
#         pyz,
#         a.scripts,
#         a.binaries,
#         a.zipfiles,
#         a.datas,
#         [],
#         name='SSM Backend',
#         debug=False,
#         bootloader_ignore_signals=False,
#         strip=False,
#         upx=True,
#         upx_exclude=[],
#         runtime_tmpdir=None,
#         console=True,
#         disable_windowed_traceback=False,
#         argv_emulation=False,
#         target_arch=None,
#         codesign_identity=None,
#         entitlements_file=None,
#         icon=backend_icon,  # Usar ícone do SSM
#     )

# Build do config_editor
# DESABILITADO POR SEGURANCA: este binario sobe um servidor web local e expõe
# configuracoes sensiveis. O produto final nao deve empacotar isso.
if False:
    config_editor = Analysis(
        ['tools/config_editor.py'],
        pathex=[str(ROOT_DIR)],
        binaries=[],
        datas=[],
        hiddenimports=['flask', 'flask_cors'],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=block_cipher,
        noarchive=False,
    )

    config_editor_pyz = PYZ(config_editor.pure, config_editor.zipped_data, cipher=block_cipher)

    config_editor_exe = EXE(
        config_editor_pyz,
        config_editor.scripts,
        config_editor.binaries,
        config_editor.zipfiles,
        config_editor.datas,
        [],
        name='config_editor',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=config_editor_icon,
    )

# REMOVIDO: Build do launcher.exe (agora integrado no Panel SSM.exe)
# A lógica do launcher (verificação de config) agora está no Panel SSM
# if False:  # Desabilitado - launcher integrado no Panel SSM
#     launcher = Analysis(
#         ['tools/launcher.py'],
#         pathex=[str(ROOT_DIR)],
#         binaries=[],
#         datas=[],
#         hiddenimports=[],
#         hookspath=[],
#         hooksconfig={},
#         runtime_hooks=[],
#         excludes=[],
#         win_no_prefer_redirects=False,
#         win_private_assemblies=False,
#         cipher=block_cipher,
#         noarchive=False,
#     )
# 
#     launcher_pyz = PYZ(launcher.pure, launcher.zipped_data, cipher=block_cipher)
# 
#     launcher_exe = EXE(
#         launcher_pyz,
#         launcher.scripts,
#         launcher.binaries,
#         launcher.zipfiles,
#         launcher.datas,
#         [],
#         name='launcher',
#         debug=False,
#         bootloader_ignore_signals=False,
#         strip=False,
#         upx=True,
#         upx_exclude=[],
#         runtime_tmpdir=None,
#         console=True,
#         disable_windowed_traceback=False,
#         argv_emulation=False,
#         target_arch=None,
#         codesign_identity=None,
#         entitlements_file=None,
#         icon=launcher_icon,  # Usar ícone do SSM
#     )

# Build do GUI Desktop (Panel SSM.exe - agora inclui backend Flask integrado)
gui_datas = [
    # Arquivos de configuração reais
    ('data/config.json', 'data'),
    ('data/webhooks.json', 'data'),
    
    # Arquivos de configuração exemplo (backup)
    ('data/config.example.json', 'data'),
    ('data/webhooks.example.json', 'data'),
    
    # Diretório de imagens completo (inclui ícones)
    ('data/imagens', 'data/imagens'),
    
    # Arquivos de coordenadas
    ('base_coordinates.csv', '.'),
    ('base_coordinates.json', '.'),
    
    # Templates de notificações
    ('data/notifications', 'data/notifications'),

    # Certificados SSL do certifi (necessário para discord.py no Windows empacotado)
    (str(__import__('certifi').where()), 'certifi'),
]

gui = Analysis(
    ['gui/gui_runner.py'],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=gui_datas,
    hiddenimports=[
        # GUI dependencies
        'gui.main_window',
        'customtkinter',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'pyperclip',
        'tkinter',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.ttk',
        # System tray and notifications
        'pystray',
        'winotify',
        'winotify.notification',
        # Core modules (GUI usa vários módulos do core)
        'core.server_control.server_manager',
        'core.licensing.hardware_fingerprint',
        'core.licensing.license_client',
        'core.licensing.license_cache',
        'core.scheduler.restart_scheduler',
        'core.security.credential_encryption',
        'core.communication.gestao_sync_service',
        'core.webhooks.discord_webhook',
        'core.notifications.notification_manager',
        'core.identity.backend_id',
        'core.identity.owner_manager',
        'core.communication.heartbeat_manager',
        'core.communication.remote_commands',
        'core.communication.license_validator',
        'core.communication.license_validator_integrity',
        'core.logs.log_processor',
        'core.logs.online_monitor',
        'core.logs.chat_processor',
        'core.logs.bunker_processor',
        'core.logs.chat_command_monitor',
        'core.logs.fishing_ranking_manager',
        'core.permissions.permission_manager',
        'core.permissions.ini_manager',
        'core.squads.squad_sync_service',
        'core.survival.survival_stats_sync_service',
        'core.survival.player_skills_sync_service',
        'core.survival.rankings_update_service',
        'core.survival.lockpicking_ranking_service',
        'core.survival.kills_ranking_service',
        'core.survival.snipers_ranking_service',
        'core.chests.chest_sync_service',
        'core.vehicles.vehicle_verification_service',
        'core.vehicles.vehicle_order_spawn_service',
        'core.gps.player_gps_sync_service',
        'core.elevated_users.elevated_users_manager',
        'utils.config_path_helper',
        'utils.logger',
        'utils.single_instance',  # Single instance management
        'utils.database_initializer',  # Database initialization module
        'utils.rcon_mod_manager',
        'utils.pak_mod_manager',
        'utils.rcon_logger',
        'utils.bsbr_client',
        'utils.rcon_client',
        'version',

        # Windows API (pywin32) - necessário para single instance
        'win32event',
        'win32api',
        'win32gui',
        'win32con',
        'winerror',
        'win32process',
        # Standard library
        'psutil',
        'requests',
        'json',
        'threading',
        'datetime',
        'pathlib',
        'webbrowser',
        'subprocess',
        'socket',
        'signal',
        'time',
        'logging',
        'io',
        'codecs',
        # Discord Bot
        'discord',
        'discord.ext',
        'discord.ext.commands',
        'discord.app_commands',
        'aiohttp',
        'certifi',
        'core.discord_bot_service',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

gui_pyz = PYZ(gui.pure, gui.zipped_data, cipher=block_cipher)

gui_exe = EXE(
    gui_pyz,
    gui.scripts,
    [],
    name='Panel SSM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Sem console - aplicação GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=gui_icon,  # Usar ícone do SSM
    exclude_binaries=True,  # onedir: binários ficam na pasta _internal/
)

# COLLECT: gera a pasta dist/Panel SSM/ com o .exe pequeno + _internal/
# Isso elimina a extração de ~180 MB para %TEMP% a cada startup
coll = COLLECT(
    gui_exe,
    gui.binaries,
    gui.zipfiles,
    gui.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Panel SSM',
)

