"""
RconModManager - Gerenciador nativo do mod RCON (BSBR-SCUM) e motor UE4SS no SCUM Server.

Responsabilidades:
1. Detecção automática de versão (PE FileVersion em main.dll e fallback em version.txt).
2. Verificação de pacotes novos descompactados em data/mods/bsbr_scum/.
3. Instalação e Atualização segura (com backup automático, rollback e preservação de config.ini).
4. Bloqueio de atualização enquanto SCUMServer.exe estiver em execução.
5. Ativação/Desativação rápida via mods.txt (bsbr_scum : 1 ou 0).
6. Sincronização cirúrgica de porta e senha na seção [source] do config.ini.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import StructuredLogger

MOD_NAME = "bsbr_scum"
MOD_DISPLAY_NAME = "BSBR-SCUM (Nativo)"
DEFAULT_SOURCE_PORT = 28015
DEFAULT_API_PORT = 27100

_SENTINEL_DLL = "dwmapi.dll"
_SENTINEL_UE4SS = "ue4ss"
_MAX_BACKUPS = 5


# ----------------------------------------------------------------------
# Verificação de Processo
# ----------------------------------------------------------------------

def is_scum_server_running() -> bool:
    """Verifica se o executável do SCUM Server está rodando no sistema."""
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info.get("name") or ""
                if name.lower() in ("scumserver.exe", "scumserver-win64-shipping.exe"):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        # Fallback via tasklist no Windows
        if sys.platform == "win32":
            try:
                import subprocess
                output = subprocess.check_output(
                    ["tasklist", "/FI", "IMAGENAME eq SCUMServer.exe", "/NH"],
                    text=True,
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                if "SCUMServer.exe" in output:
                    return True
            except Exception:
                pass
    return False


# ----------------------------------------------------------------------
# Funções de Extração e Comparação de Versão
# ----------------------------------------------------------------------

def get_pe_file_version(path: Path | str) -> Optional[str]:
    """
    Extrai a versão numérica do recurso PE de um arquivo DLL/EXE no Windows.
    Retorna strings como '0.3.0.0' ou None se não houver recurso.
    """
    path_obj = Path(path)
    if not path_obj.exists() or sys.platform != "win32":
        return None

    try:
        size = ctypes.windll.version.GetFileVersionInfoSizeW(str(path_obj), None)
        if not size:
            return None

        buf = ctypes.create_string_buffer(size)
        if not ctypes.windll.version.GetFileVersionInfoW(str(path_obj), 0, size, buf):
            return None

        lp = ctypes.c_void_p()
        ln = wintypes.UINT()
        if not ctypes.windll.version.VerQueryValueW(buf, "\\", ctypes.byref(lp), ctypes.byref(ln)):
            return None

        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                (name, wintypes.DWORD)
                for name in (
                    "dwSignature",
                    "dwStrucVersion",
                    "dwFileVersionMS",
                    "dwFileVersionLS",
                    "dwProductVersionMS",
                    "dwProductVersionLS",
                    "dwFileFlagsMask",
                    "dwFileFlags",
                    "dwFileOS",
                    "dwFileType",
                    "dwFileSubtype",
                    "dwFileDateMS",
                    "dwFileDateLS",
                )
            ]

        ffi = ctypes.cast(lp, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
        major = ffi.dwFileVersionMS >> 16
        minor = ffi.dwFileVersionMS & 0xFFFF
        build = ffi.dwFileVersionLS >> 16
        revision = ffi.dwFileVersionLS & 0xFFFF
        return f"{major}.{minor}.{build}.{revision}"
    except Exception:
        return None


def read_version_txt(path: Path | str) -> Optional[str]:
    """
    Lê a versão contida na primeira linha de version.txt.
    Ignora linhas subsequentes (ex: carimbos de boot 'carregado 2026-10-15...').
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return None
    try:
        content = path_obj.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            # Ignora linhas de log do mod como 'carregado ...'
            if line.lower().startswith("carregado"):
                continue
            return line
    except Exception:
        pass
    return None


def normalize_version(raw: Optional[str]) -> Optional[str]:
    """
    Normaliza representações de versão como:
    - 'bsbr_scum 0.3.0' -> '0.3.0'
    - '0.3.0.0'         -> '0.3.0'
    - 'v0.3.0'          -> '0.3.0'
    """
    if not raw:
        return None

    cleaned = raw.strip()
    # Remove prefixos como 'bsbr_scum', 'v', etc.
    cleaned = re.sub(r"^(?:bsbr_scum|version|v)?\s*", "", cleaned, flags=re.IGNORECASE).strip()

    # Extrai o padrão numérico X.Y.Z[.W]
    match = re.search(r"\b(\d+)\.(\d+)(?:\.(\d+))?(?:\.(\d+))?\b", cleaned)
    if not match:
        return cleaned if cleaned else None

    parts = [p for p in match.groups() if p is not None]
    # Se terminar com 0 após 3 partes (ex 0.3.0.0 -> 0.3.0)
    if len(parts) == 4 and parts[3] == "0":
        parts = parts[:3]
    return ".".join(parts)


def compare_versions(v1: Optional[str], v2: Optional[str]) -> int:
    """
    Compara duas versões semver-like:
    Retorna:
       1 se v1 > v2
       0 se v1 == v2
      -1 se v1 < v2
    Valores None são tratados como menores que qualquer versão válida.
    """
    n1 = normalize_version(v1)
    n2 = normalize_version(v2)

    if n1 is None and n2 is None:
        return 0
    if n1 is None:
        return -1
    if n2 is None:
        return 1

    def to_tuple(v: str) -> tuple:
        parts = []
        for p in re.findall(r"\d+", v):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return tuple(parts)

    t1 = to_tuple(n1)
    t2 = to_tuple(n2)

    # Igualar comprimento com zeros para comparação justa
    max_len = max(len(t1), len(t2))
    t1_padded = t1 + (0,) * (max_len - len(t1))
    t2_padded = t2 + (0,) * (max_len - len(t2))

    if t1_padded > t2_padded:
        return 1
    elif t1_padded < t2_padded:
        return -1
    return 0


# ----------------------------------------------------------------------
# Localizador de Componentes do Mod
# ----------------------------------------------------------------------

def resolve_mod_components(base_dir: Path) -> Dict[str, Optional[Path]]:
    """
    Localiza os componentes do mod (main.dll, version.txt, config.ini, UE4SS)
    independentemente de terem sido descompactados na raiz ou dentro de subpastas ue4ss/.
    """
    result: Dict[str, Optional[Path]] = {
        "dwmapi_dll": None,
        "ue4ss_dll": None,
        "ue4ss_settings": None,
        "mod_dir": None,
        "main_dll": None,
        "version_txt": None,
        "config_ini": None,
    }

    if not base_dir.is_dir():
        return result

    # 1. Procurar main.dll
    candidates_main = [
        base_dir / "ue4ss" / "Mods" / MOD_NAME / "dlls" / "main.dll",
        base_dir / "Mods" / MOD_NAME / "dlls" / "main.dll",
        base_dir / MOD_NAME / "dlls" / "main.dll",
        base_dir / "dlls" / "main.dll",
    ]
    for cand in candidates_main:
        if cand.is_file():
            result["main_dll"] = cand
            result["mod_dir"] = cand.parent.parent
            break

    # Se ainda não encontrou mod_dir, busca recursiva tolerante
    if not result["main_dll"]:
        for match in base_dir.glob("**/dlls/main.dll"):
            result["main_dll"] = match
            result["mod_dir"] = match.parent.parent
            break

    # 2. Localizar version.txt e config.ini relativos ao mod_dir
    if result["mod_dir"]:
        vt = result["mod_dir"] / "version.txt"
        if vt.is_file():
            result["version_txt"] = vt
        ci = result["mod_dir"] / "config.ini"
        if ci.is_file():
            result["config_ini"] = ci

    # 3. Localizar binários UE4SS Core
    candidates_dwmapi = [
        base_dir / _SENTINEL_DLL,
        base_dir / "ue4ss" / _SENTINEL_DLL,
    ]
    for cand in candidates_dwmapi:
        if cand.is_file():
            result["dwmapi_dll"] = cand
            break

    candidates_ue4ss = [
        base_dir / "ue4ss" / "UE4SS.dll",
        base_dir / "UE4SS.dll",
    ]
    for cand in candidates_ue4ss:
        if cand.is_file():
            result["ue4ss_dll"] = cand
            break

    candidates_settings = [
        base_dir / "ue4ss" / "UE4SS-settings.ini",
        base_dir / "UE4SS-settings.ini",
    ]
    for cand in candidates_settings:
        if cand.is_file():
            result["ue4ss_settings"] = cand
            break

    return result


# ----------------------------------------------------------------------
# Classe Principal: RconModManager
# ----------------------------------------------------------------------

class RconModManager:
    """
    Gerenciador unificado para o mod RCON nativo (BSBR-SCUM) do SCUM Server.
    """

    def __init__(self, root_dir: Optional[str] = None, logger: Optional[StructuredLogger] = None):
        self.logger = logger or StructuredLogger()
        if root_dir:
            self.root_dir = Path(root_dir)
        else:
            self.root_dir = Path(__file__).resolve().parent.parent

        self.mods_data_dir = self.root_dir / "data" / "mods"
        self.package_dir = self.mods_data_dir / MOD_NAME
        self.backup_root_dir = self.mods_data_dir / "_backup"

    # ------------------------------------------------------------------
    # Inspeção de Pacote e Instalação
    # ------------------------------------------------------------------

    def get_package_info(self) -> Dict[str, Any]:
        """
        Inspeciona o pacote presente em data/mods/bsbr_scum/ pronto para instalação.
        """
        components = resolve_mod_components(self.package_dir)
        main_dll = components["main_dll"]

        if not main_dll or not main_dll.is_file():
            return {
                "available": False,
                "version": None,
                "raw_version": None,
                "path": str(self.package_dir),
                "components": components,
            }

        # Extração de versão: Prioridade 1 = PE FileVersion; Prioridade 2 = version.txt
        raw_version = None
        pe_version = get_pe_file_version(main_dll)
        if pe_version:
            raw_version = pe_version
        elif components["version_txt"]:
            raw_version = read_version_txt(components["version_txt"])

        norm_version = normalize_version(raw_version)

        return {
            "available": True,
            "version": norm_version,
            "raw_version": raw_version,
            "path": str(self.package_dir),
            "components": components,
        }

    def get_installed_info(self, binaries_dir: str) -> Dict[str, Any]:
        """
        Inspeciona os arquivos do mod instalados no diretório do servidor SCUM.
        """
        bin_path = Path(binaries_dir)
        if not bin_path.is_dir():
            return {
                "installed": False,
                "enabled": False,
                "version": None,
                "raw_version": None,
                "binaries_dir": str(bin_path),
            }

        mod_folder = bin_path / _SENTINEL_UE4SS / "Mods" / MOD_NAME
        main_dll = mod_folder / "dlls" / "main.dll"
        version_txt = mod_folder / "version.txt"
        config_ini = mod_folder / "config.ini"
        dwmapi = bin_path / _SENTINEL_DLL
        ue4ss_dll = bin_path / _SENTINEL_UE4SS / "UE4SS.dll"
        mods_txt = bin_path / _SENTINEL_UE4SS / "Mods" / "mods.txt"

        installed = main_dll.is_file() and dwmapi.is_file()
        enabled = False
        if installed and mods_txt.is_file():
            mods_state = self._read_mods_txt(mods_txt)
            enabled = mods_state.get(MOD_NAME, False)

        raw_version = None
        pe_ver = get_pe_file_version(main_dll) if main_dll.is_file() else None
        if pe_ver:
            raw_version = pe_ver
        elif version_txt.is_file():
            raw_version = read_version_txt(version_txt)

        norm_version = normalize_version(raw_version)

        # Se instalado mas não tem versão identificável (build de teste anterior)
        version_display = norm_version or ("< 0.3.0" if installed else None)

        return {
            "installed": installed,
            "enabled": enabled,
            "version": norm_version,
            "version_display": version_display,
            "raw_version": raw_version,
            "main_dll": str(main_dll) if main_dll.exists() else None,
            "version_txt": str(version_txt) if version_txt.exists() else None,
            "config_ini": str(config_ini) if config_ini.exists() else None,
            "has_dwmapi": dwmapi.is_file(),
            "has_ue4ss": ue4ss_dll.is_file(),
        }

    def check_update_status(self, binaries_dir: str) -> Dict[str, Any]:
        """
        Compara o pacote disponível em data/mods/bsbr_scum/ com o instalado no servidor.
        """
        pkg = self.get_package_info()
        inst = self.get_installed_info(binaries_dir)

        server_running = is_scum_server_running()

        if not pkg["available"]:
            return {
                "can_update": False,
                "update_available": False,
                "is_up_to_date": True if inst["installed"] else False,
                "status_code": "NO_PACKAGE",
                "message": "Nenhum pacote novo encontrado em data/mods/bsbr_scum/.",
                "server_running": server_running,
                "installed_info": inst,
                "package_info": pkg,
            }

        if not inst["installed"]:
            return {
                "can_update": not server_running,
                "update_available": True,
                "is_up_to_date": False,
                "status_code": "NOT_INSTALLED",
                "message": f"Pronto para instalar versão {pkg['version'] or 'recente'}.",
                "server_running": server_running,
                "installed_info": inst,
                "package_info": pkg,
            }

        cmp = compare_versions(pkg["version"], inst["version"])
        # Se inst["version"] for None mas inst["installed"] for True, o pacote mais novo deve ser oferecido
        update_available = (cmp > 0) or (inst["version"] is None)
        is_up_to_date = (cmp == 0) and (inst["version"] is not None)

        return {
            "can_update": update_available and not server_running,
            "update_available": update_available,
            "is_up_to_date": is_up_to_date,
            "status_code": "UPDATE_AVAILABLE" if update_available else "UP_TO_DATE",
            "message": (
                f"Nova versão disponível: v{pkg['version']}"
                if update_available
                else "O mod RCON já está na versão mais recente."
            ),
            "server_running": server_running,
            "installed_info": inst,
            "package_info": pkg,
        }

    # ------------------------------------------------------------------
    # Backup & Rollback
    # ------------------------------------------------------------------

    def create_backup(self, binaries_dir: str, current_version: Optional[str] = None) -> Optional[Path]:
        """
        Cria cópia de segurança dos binários atuais do mod antes de atualizar.
        Mantém até _MAX_BACKUPS pastas.
        """
        bin_path = Path(binaries_dir)
        mod_folder = bin_path / _SENTINEL_UE4SS / "Mods" / MOD_NAME
        if not mod_folder.is_dir():
            return None

        ver_tag = current_version or "antiga"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = self.backup_root_dir / f"bsbr_scum_{ver_tag}_{ts}"

        try:
            backup_folder.mkdir(parents=True, exist_ok=True)
            _copy_tree_merge(mod_folder, backup_folder / "mod")

            # Salvar dwmapi e UE4SS.dll se existirem
            dwmapi = bin_path / _SENTINEL_DLL
            if dwmapi.exists():
                shutil.copy2(dwmapi, backup_folder / _SENTINEL_DLL)

            ue4ss_dll = bin_path / _SENTINEL_UE4SS / "UE4SS.dll"
            if ue4ss_dll.exists():
                shutil.copy2(ue4ss_dll, backup_folder / "UE4SS.dll")

            self.logger.info(f"Backup do mod RCON criado em: {backup_folder}")
            self._prune_old_backups()
            return backup_folder
        except Exception as e:
            self.logger.error(f"Falha ao criar backup do mod RCON: {e}")
            return None

    def _prune_old_backups(self) -> None:
        """Mantém apenas os últimos backups em disco."""
        if not self.backup_root_dir.is_dir():
            return
        try:
            dirs = [d for d in self.backup_root_dir.iterdir() if d.is_dir()]
            dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
            for old in dirs[_MAX_BACKUPS:]:
                try:
                    shutil.rmtree(old)
                    self.logger.info(f"Backup antigo removido: {old.name}")
                except Exception:
                    pass
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Instalação e Atualização Unificada
    # ------------------------------------------------------------------

    def install_or_update(
        self,
        binaries_dir: str,
        preserve_config: bool = True,
        force: bool = False,
    ) -> Tuple[bool, str]:
        """
        Instala ou atualiza o mod BSBR-SCUM com total segurança:
        - Verifica se o SCUMServer.exe está rodando (bloqueia se estiver).
        - Cria backup do estado anterior.
        - Copia componentes novos (dwmapi.dll, UE4SS Core, Mods/bsbr_scum).
        - Preserva integralmente o config.ini pré-existente (senhas, portas, etc).
        - Ativa o mod no mods.txt.
        - Em caso de falha de I/O, restaura automaticamente o backup.
        """
        bin_path = Path(binaries_dir)
        if not bin_path.is_dir():
            return False, f"Diretório de binários do SCUM não encontrado: {binaries_dir}"

        if not force and is_scum_server_running():
            return False, (
                "O SCUM Server está em execução!\n\n"
                "Pare o servidor SCUM antes de instalar ou atualizar o mod de RCON "
                "para liberar as DLLs bloqueadas pelo jogo."
            )

        pkg = self.get_package_info()
        if not pkg["available"]:
            return False, "Nenhum pacote de instalação/atualização encontrado em 'data/mods/bsbr_scum/'."

        components = pkg["components"]
        target_mod_folder = bin_path / _SENTINEL_UE4SS / "Mods" / MOD_NAME
        config_ini_target = target_mod_folder / "config.ini"

        # 1. Guardar config.ini existente em memória se necessário
        saved_config_content: Optional[str] = None
        if preserve_config and config_ini_target.is_file():
            try:
                saved_config_content = config_ini_target.read_text(encoding="utf-8")
                self.logger.info("config.ini existente preservado para restauração pós-cópia.")
            except Exception as e:
                self.logger.warning(f"Não foi possível ler config.ini existente: {e}")

        # 2. Criar backup do mod instalado atualmente
        installed_info = self.get_installed_info(binaries_dir)
        backup_dir = None
        if installed_info["installed"]:
            backup_dir = self.create_backup(binaries_dir, current_version=installed_info["version"])

        try:
            # 3. Copiar dwmapi.dll (Core Loader)
            if components["dwmapi_dll"] and components["dwmapi_dll"].is_file():
                shutil.copy2(components["dwmapi_dll"], bin_path / _SENTINEL_DLL)
                self.logger.info("dwmapi.dll atualizado com sucesso.")

            # 4. Copiar UE4SS Core
            ue4ss_dir = bin_path / _SENTINEL_UE4SS
            ue4ss_dir.mkdir(parents=True, exist_ok=True)

            if components["ue4ss_dll"] and components["ue4ss_dll"].is_file():
                shutil.copy2(components["ue4ss_dll"], ue4ss_dir / "UE4SS.dll")
                self.logger.info("UE4SS.dll atualizado.")

            if components["ue4ss_settings"] and components["ue4ss_settings"].is_file():
                # Só sobrescreve settings se não existir para não perder modificações
                target_settings = ue4ss_dir / "UE4SS-settings.ini"
                if not target_settings.exists():
                    shutil.copy2(components["ue4ss_settings"], target_settings)

            # 5. Copiar pasta do Mod (Mods/bsbr_scum)
            target_mod_folder.mkdir(parents=True, exist_ok=True)
            src_mod_dir = components["mod_dir"]
            if src_mod_dir and src_mod_dir.is_dir():
                _copy_tree_merge(src_mod_dir, target_mod_folder)
                self.logger.info(f"Arquivos do mod copiados para: {target_mod_folder}")

            # 6. Restauração ou Inicialização do config.ini
            if saved_config_content:
                config_ini_target.write_text(saved_config_content, encoding="utf-8")
                self.logger.info("config.ini preservado restaurado com sucesso.")
            elif not config_ini_target.exists() and components["config_ini"]:
                shutil.copy2(components["config_ini"], config_ini_target)
                self.logger.info("config.ini padrão criado a partir do pacote.")

            # 7. Garantir enabled.txt
            enabled_txt = target_mod_folder / "enabled.txt"
            if not enabled_txt.exists():
                try:
                    enabled_txt.touch()
                except Exception:
                    pass

            # 8. Atualizar mods.txt
            mods_txt_path = ue4ss_dir / "Mods" / "mods.txt"
            self._update_mods_txt(mods_txt_path, enable_mod=MOD_NAME)

            # 9. Validação pós-cópia
            installed_main = target_mod_folder / "dlls" / "main.dll"
            if not installed_main.is_file():
                raise RuntimeError("Falha na validação: 'dlls/main.dll' não encontrado após a cópia.")

            new_ver = pkg["version"] or "recente"
            self.logger.info(f"BSBR-SCUM v{new_ver} instalado/atualizado com sucesso.")
            return True, f"BSBR-SCUM v{new_ver} instalado com sucesso! Inicie o servidor SCUM para carregar."

        except Exception as e:
            self.logger.error(f"Erro durante instalação/atualização: {e}")
            # Rollback automático se houver backup
            if backup_dir and (backup_dir / "mod").is_dir():
                try:
                    self.logger.info("Iniciando rollback automático...")
                    _copy_tree_merge(backup_dir / "mod", target_mod_folder)
                    if (backup_dir / _SENTINEL_DLL).exists():
                        shutil.copy2(backup_dir / _SENTINEL_DLL, bin_path / _SENTINEL_DLL)
                    if (backup_dir / "UE4SS.dll").exists():
                        shutil.copy2(backup_dir / "UE4SS.dll", bin_path / _SENTINEL_UE4SS / "UE4SS.dll")
                    self.logger.info("Rollback concluído.")
                except Exception as rb_err:
                    self.logger.error(f"Falha no rollback automático: {rb_err}")

            return False, f"Falha na atualização do mod: {e}"

    # ------------------------------------------------------------------
    # Ativação / Desativação via mods.txt
    # ------------------------------------------------------------------

    def toggle_active(self, binaries_dir: str, enable: bool) -> Tuple[bool, str]:
        """
        Ativa ou desativa o mod BSBR-SCUM no mods.txt do UE4SS.
        Gera efeito na próxima inicialização do servidor.
        """
        bin_path = Path(binaries_dir)
        mods_txt_path = bin_path / _SENTINEL_UE4SS / "Mods" / "mods.txt"

        try:
            self._update_mods_txt(mods_txt_path, enable_mod=MOD_NAME if enable else None, disable_mod=None if enable else MOD_NAME)
            status_str = "ativado" if enable else "desativado"
            self.logger.info(f"Mod RCON {status_str} no mods.txt.")
            return True, f"Mod RCON {status_str} com sucesso! Reinicie o servidor para aplicar."
        except Exception as e:
            self.logger.error(f"Erro ao alternar ativação do mod no mods.txt: {e}")
            return False, f"Erro ao alternar ativação: {e}"

    # ------------------------------------------------------------------
    # Sincronização Cirúrgica de Credenciais ([source] no config.ini)
    # ------------------------------------------------------------------

    def update_source_credentials(
        self,
        binaries_dir: str,
        port: int,
        password: str,
    ) -> Tuple[bool, str]:
        """
        Atualiza cirurgicamente a porta e senha da seção [source] no config.ini do mod,
        preservando todos os comentários e as demais seções.
        """
        bin_path = Path(binaries_dir)
        config_path = bin_path / _SENTINEL_UE4SS / "Mods" / MOD_NAME / "config.ini"

        if not config_path.is_file():
            return False, f"Arquivo config.ini não encontrado em {config_path}."

        try:
            content = config_path.read_text(encoding="utf-8")
            new_content = _patch_ini_source_section(content, port=port, password=password)
            config_path.write_text(new_content, encoding="utf-8")
            self.logger.info(f"Credenciais [source] atualizadas no config.ini: porta {port}")
            return True, "Credenciais de RCON atualizadas com sucesso no config.ini!"
        except Exception as e:
            self.logger.error(f"Erro ao atualizar config.ini: {e}")
            return False, f"Erro ao atualizar config.ini: {e}"

    # ------------------------------------------------------------------
    # Desinstalação
    # ------------------------------------------------------------------

    def uninstall(
        self,
        binaries_dir: str,
        remove_ue4ss_core: bool = False,
    ) -> Tuple[bool, str]:
        """
        Remove o mod BSBR-SCUM do servidor.
        """
        bin_path = Path(binaries_dir)
        if not bin_path.is_dir():
            return False, f"Diretório não encontrado: {binaries_dir}"

        if is_scum_server_running():
            return False, "Pare o servidor SCUM antes de desinstalar o mod de RCON."

        target_mod_folder = bin_path / _SENTINEL_UE4SS / "Mods" / MOD_NAME
        errors = []

        if target_mod_folder.is_dir():
            try:
                shutil.rmtree(target_mod_folder)
                self.logger.info(f"Pasta do mod removida: {target_mod_folder}")
            except Exception as e:
                errors.append(f"Erro ao remover pasta do mod: {e}")

        # Atualizar mods.txt
        mods_txt_path = bin_path / _SENTINEL_UE4SS / "Mods" / "mods.txt"
        if mods_txt_path.exists():
            try:
                self._update_mods_txt(mods_txt_path, disable_mod=MOD_NAME)
            except Exception:
                pass

        if remove_ue4ss_core:
            dll_path = bin_path / _SENTINEL_DLL
            if dll_path.exists():
                try:
                    dll_path.unlink()
                except Exception as e:
                    errors.append(f"Erro ao remover {dll_path}: {e}")

            ue4ss_dir = bin_path / _SENTINEL_UE4SS
            if ue4ss_dir.is_dir():
                try:
                    shutil.rmtree(ue4ss_dir)
                except Exception as e:
                    errors.append(f"Erro ao remover {ue4ss_dir}: {e}")

        if errors:
            return False, "\n".join(errors)
        return True, "Mod RCON desinstalado com sucesso!"

    # ------------------------------------------------------------------
    # Compatibilidade Legada
    # ------------------------------------------------------------------

    def get_installed_provider(self, binaries_dir: str) -> Optional[str]:
        info = self.get_installed_info(binaries_dir)
        return MOD_NAME if info["installed"] and info["enabled"] else None

    def is_installed(self, binaries_dir: str, provider: Optional[str] = None) -> bool:
        return self.get_installed_info(binaries_dir)["installed"]

    def get_installed_config(self, binaries_dir: str, provider: Optional[str] = None) -> Optional[dict]:
        bin_path = Path(binaries_dir)
        config_path = bin_path / _SENTINEL_UE4SS / "Mods" / MOD_NAME / "config.ini"
        if not config_path.exists():
            return None
        try:
            return _parse_ini_source_section(config_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def get_available_providers(self) -> List[Dict[str, Any]]:
        return [{
            "id": MOD_NAME,
            "name": MOD_DISPLAY_NAME,
            "default_port": DEFAULT_SOURCE_PORT,
            "path": str(self.package_dir),
        }]

    def install(
        self,
        binaries_dir: str,
        provider: str = MOD_NAME,
        rcon_ip: str = "127.0.0.1",
        rcon_port: Optional[int] = None,
        rcon_password: str = "",
    ) -> Tuple[bool, str]:
        ok, msg = self.install_or_update(binaries_dir, preserve_config=True)
        if ok and rcon_port:
            self.update_source_credentials(binaries_dir, port=rcon_port, password=rcon_password)
        return ok, msg

    def update_config(
        self,
        binaries_dir: str,
        provider: str = MOD_NAME,
        rcon_ip: str = "127.0.0.1",
        rcon_port: Optional[int] = None,
        rcon_password: str = "",
    ) -> Tuple[bool, str]:
        port = rcon_port or DEFAULT_SOURCE_PORT
        return self.update_source_credentials(binaries_dir, port=port, password=rcon_password)

    # ------------------------------------------------------------------
    # Helpers Internos de mods.txt
    # ------------------------------------------------------------------

    def _read_mods_txt(self, mods_txt_path: Path) -> Dict[str, bool]:
        if not mods_txt_path.exists():
            return {}
        result = {}
        try:
            for line in mods_txt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith(";"):
                    continue
                if ":" in line:
                    k, _, v = line.partition(":")
                    result[k.strip()] = (v.strip() == "1")
                elif "=" in line:
                    k, _, v = line.partition("=")
                    result[k.strip()] = (v.strip() == "1")
        except Exception:
            pass
        return result

    def _update_mods_txt(
        self,
        mods_txt_path: Path,
        enable_mod: Optional[str] = None,
        disable_mod: Optional[str] = None,
    ) -> None:
        mods = self._read_mods_txt(mods_txt_path)
        if disable_mod:
            mods[disable_mod] = False
        if enable_mod:
            mods[enable_mod] = True

        mods_txt_path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["; UE4SS mods list", "; 1 = enabled, 0 = disabled", ""]
        for mod_name, is_enabled in sorted(mods.items()):
            lines.append(f"{mod_name} : {1 if is_enabled else 0}")
        lines.append("")
        mods_txt_path.write_text("\n".join(lines), encoding="utf-8")


# ----------------------------------------------------------------------
# Helpers de Cópia e Manipulação Cirúrgica de INI
# ----------------------------------------------------------------------

def _copy_tree_merge(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        dst_item = dst / item.name
        if item.is_dir():
            _copy_tree_merge(item, dst_item)
        else:
            shutil.copy2(item, dst_item)


def _patch_ini_source_section(content: str, port: int, password: str) -> str:
    """
    Atualiza 'port = ...' e 'password = ...' dentro da seção [source] do config.ini,
    sem alterar linhas de comentários ou outras seções.
    Se a seção [source] não existir, anexa-a ao final.
    """
    lines = content.splitlines()
    in_source = False
    port_found = False
    password_found = False
    source_section_found = False

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            sec_name = stripped[1:-1].strip().lower()
            if in_source:
                # Saindo da seção [source]: se faltou alguma chave, adiciona antes da nova seção
                if not port_found:
                    new_lines.append(f"port = {port}")
                    port_found = True
                if not password_found:
                    new_lines.append(f"password = {password}")
                    password_found = True
            in_source = (sec_name == "source")
            if in_source:
                source_section_found = True
            new_lines.append(line)
            continue

        if in_source and not stripped.startswith(";"):
            if stripped.startswith("port") and "=" in stripped:
                new_lines.append(f"port = {port}")
                port_found = True
                continue
            if stripped.startswith("password") and "=" in stripped:
                new_lines.append(f"password = {password}")
                password_found = True
                continue

        new_lines.append(line)

    # Se terminou o arquivo e ainda estava na seção [source]
    if in_source:
        if not port_found:
            new_lines.append(f"port = {port}")
        if not password_found:
            new_lines.append(f"password = {password}")

    # Se a seção [source] nunca existiu
    if not source_section_found:
        new_lines.extend([
            "",
            "[source]",
            f"port = {port}",
            f"password = {password}",
        ])

    return "\n".join(new_lines) + "\n"


def _parse_ini_source_section(content: str) -> dict:
    result = {}
    in_source = False
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            sec = line[1:-1].strip().lower()
            in_source = (sec == "source")
            continue
        if in_source and "=" in line and not line.startswith(";"):
            k, _, v = line.partition("=")
            k, v = k.strip().lower(), v.strip()
            if k == "port":
                try:
                    result["port"] = int(v)
                except ValueError:
                    pass
            elif k == "password":
                result["password"] = v
    return result
