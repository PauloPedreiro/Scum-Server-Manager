"""
RconModManager - Gerencia a instalação, configuração e remoção modular de mods RCON (UE4SS) no SCUM Server.

Provedores suportados:
    1. bsbr_scum (Mazzotti - Avançado / Porta padrão 27100 / Comandos sudo, reflection, entrega as <player>)
    2. scum_rcon (Clássico / Porta padrão 28015 / Source RCON Protocol)

Estrutura nos binários (Win64):
    - dwmapi.dll                   (Loader UE4SS)
    - ue4ss/
        - UE4SS.dll                (Engine UE4SS)
        - UE4SS-settings.ini       (Configurações do UE4SS)
        - Mods/
            - mods.txt             (Lista de ativação: 1 = Ativo, 0 = Inativo)
            - bsbr_scum/           (Arquivos do mod BSBR)
            - scum_rcon/           (Arquivos do mod SCUM-RCON)
"""
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import StructuredLogger

# Provedores
PROVIDER_BSBR = "bsbr_scum"
PROVIDER_SCUM_RCON = "scum_rcon"

PROVIDER_NAMES = {
    PROVIDER_BSBR: "BSBR-SCUM (Mazzotti - Advanced)",
    PROVIDER_SCUM_RCON: "SCUM-RCON (Classic)",
}


DEFAULT_PORTS = {
    PROVIDER_BSBR: 27100,
    PROVIDER_SCUM_RCON: 28015,
}

_SENTINEL_DLL = "dwmapi.dll"
_SENTINEL_UE4SS = "ue4ss"


class RconModManager:
    """
    Gerencia a instalação modular e desinstalação de provedores RCON (UE4SS) no servidor SCUM.
    Garante que apenas 1 provedor de RCON esteja ativo por vez no mods.txt.
    """

    def __init__(self, root_dir: Optional[str] = None, logger: Optional[StructuredLogger] = None):
        self.logger = logger or StructuredLogger()
        if root_dir:
            self.root_dir = Path(root_dir)
        else:
            self.root_dir = Path(__file__).parent.parent

        self.mods_data_dir = self.root_dir / "data" / "mods"

    # ------------------------------------------------------------------
    # Consultas de estado
    # ------------------------------------------------------------------

    def get_installed_provider(self, binaries_dir: str) -> Optional[str]:
        """
        Retorna o ID do provedor RCON atualmente instalado e ativo ('bsbr_scum', 'scum_rcon' ou None).
        """
        bin_path = Path(binaries_dir)
        if not (bin_path / _SENTINEL_DLL).exists() or not (bin_path / _SENTINEL_UE4SS).is_dir():
            return None

        mods_txt_path = bin_path / _SENTINEL_UE4SS / "Mods" / "mods.txt"
        active_mods = self._read_mods_txt(mods_txt_path)

        # Verificar qual provedor está explicitamente ativo (= 1)
        if active_mods.get(PROVIDER_BSBR, False):
            return PROVIDER_BSBR
        if active_mods.get(PROVIDER_SCUM_RCON, False):
            return PROVIDER_SCUM_RCON

        # Fallback: verificar se as pastas existem no disco se mods.txt não especificar
        if (bin_path / _SENTINEL_UE4SS / "Mods" / PROVIDER_BSBR / "dlls" / "main.dll").exists():
            return PROVIDER_BSBR
        if (bin_path / _SENTINEL_UE4SS / "Mods" / PROVIDER_SCUM_RCON / "dlls" / "main.dll").exists():
            return PROVIDER_SCUM_RCON

        return None

    def is_installed(self, binaries_dir: str, provider: Optional[str] = None) -> bool:
        """
        Verifica se o UE4SS e o provedor especificado (ou qualquer um) estão instalados.
        """
        installed = self.get_installed_provider(binaries_dir)
        if not installed:
            return False
        if provider:
            return installed == provider
        return True

    def get_installed_config(self, binaries_dir: str, provider: Optional[str] = None) -> Optional[dict]:
        """
        Lê a configuração atual do mod instalado.
        """
        active_provider = provider or self.get_installed_provider(binaries_dir) or PROVIDER_BSBR
        bin_path = Path(binaries_dir)
        config_path = bin_path / _SENTINEL_UE4SS / "Mods" / active_provider / "config.ini"

        if not config_path.exists():
            return None
        try:
            return _parse_rcon_ini(config_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """
        Descobre dinamicamente os mods RCON disponíveis em data/mods/rcon/.
        """
        rcon_dir = self.mods_data_dir / "rcon"
        providers = []

        if rcon_dir.is_dir():
            for folder in sorted(rcon_dir.iterdir()):
                if folder.is_dir():
                    pid = folder.name
                    providers.append({
                        "id": pid,
                        "name": PROVIDER_NAMES.get(pid, pid.replace("_", " ").title()),
                        "default_port": DEFAULT_PORTS.get(pid, 27100),
                        "path": str(folder),
                    })

        if not providers:
            for pid in [PROVIDER_BSBR, PROVIDER_SCUM_RCON]:
                providers.append({
                    "id": pid,
                    "name": PROVIDER_NAMES.get(pid, pid),
                    "default_port": DEFAULT_PORTS.get(pid, 27100),
                    "path": str(self.mods_data_dir / pid),
                })

        return providers

    # ------------------------------------------------------------------
    # Instalação Modular
    # ------------------------------------------------------------------

    def install(
        self,
        binaries_dir: str,
        provider: str = PROVIDER_BSBR,
        rcon_ip: str = "127.0.0.1",
        rcon_port: Optional[int] = None,
        rcon_password: str = "",
    ) -> Tuple[bool, str]:
        """
        Instala (ou repara) o UE4SS Core e o provedor de RCON selecionado.
        Garante que apenas o provedor escolhido seja ativado no mods.txt.
        """
        bin_path = Path(binaries_dir)
        if not bin_path.is_dir():
            return False, f"Diretório de binários não encontrado: {binaries_dir}"

        if provider not in (PROVIDER_BSBR, PROVIDER_SCUM_RCON):
            provider = PROVIDER_BSBR

        if rcon_port is None:
            rcon_port = DEFAULT_PORTS.get(provider, 27100)

        # Para SCUM-RCON clássico, senha é obrigatória
        if provider == PROVIDER_SCUM_RCON and (not rcon_password or rcon_password.strip() == ""):
            return False, "A senha de RCON é obrigatória para o SCUM-RCON clássico."

        # Identificar pasta fonte do mod (onde ficam dlls/main.dll e config.ini do mod)
        src_mod_dir = None
        candidates = [
            self.mods_data_dir / "rcon" / provider / "ue4ss" / "Mods" / provider,
            self.mods_data_dir / provider / "ue4ss" / "Mods" / provider,
            self.mods_data_dir / "rcon" / provider,
            self.mods_data_dir / provider,
        ]
        for cand in candidates:
            if cand.is_dir() and (cand / "dlls" / "main.dll").exists():
                src_mod_dir = cand
                break
            elif cand.is_dir() and src_mod_dir is None:
                src_mod_dir = cand

        # Identificar pasta fonte do UE4SS Core
        core_dir = self.mods_data_dir / "ue4ss_core"
        if not core_dir.is_dir():
            core_dir = self.mods_data_dir / PROVIDER_SCUM_RCON / "ue4ss"

        try:
            # 1. Copiar dwmapi.dll (Core Loader)
            src_dll = core_dir / _SENTINEL_DLL
            if not src_dll.exists():
                src_dll = self.mods_data_dir / PROVIDER_SCUM_RCON / _SENTINEL_DLL
            if not src_dll.exists():
                src_dll = self.mods_data_dir / "rcon" / PROVIDER_SCUM_RCON / _SENTINEL_DLL
            dst_dll = bin_path / _SENTINEL_DLL
            if src_dll.exists():
                self.logger.info(f"Copiando {src_dll} → {dst_dll}")
                shutil.copy2(src_dll, dst_dll)

            # 2. Copiar UE4SS Core files (UE4SS.dll, UE4SS-settings.ini)
            dst_ue4ss = bin_path / _SENTINEL_UE4SS
            dst_ue4ss.mkdir(parents=True, exist_ok=True)

            for core_file in ["UE4SS.dll", "UE4SS-settings.ini"]:
                src_core = core_dir / core_file
                if not src_core.exists():
                    src_core = self.mods_data_dir / PROVIDER_SCUM_RCON / "ue4ss" / core_file
                if not src_core.exists():
                    src_core = self.mods_data_dir / "rcon" / PROVIDER_SCUM_RCON / "ue4ss" / core_file
                if src_core.exists():
                    shutil.copy2(src_core, dst_ue4ss / core_file)

            # 3. Copiar pasta do Mod específico para ue4ss/Mods/<provider>/
            dst_mod_folder = dst_ue4ss / "Mods" / provider
            if dst_mod_folder.is_dir():
                try:
                    shutil.rmtree(dst_mod_folder)
                except Exception:
                    pass
            dst_mod_folder.mkdir(parents=True, exist_ok=True)

            if src_mod_dir and src_mod_dir.is_dir():
                self.logger.info(f"Copiando mod '{provider}' de {src_mod_dir} → {dst_mod_folder}")
                _copy_tree_merge(src_mod_dir, dst_mod_folder)


            # Limpar resíduos de arquivos txt do bsbr se estiver instalando scum_rcon
            if provider == PROVIDER_SCUM_RCON:
                for txt_file in bin_path.glob("bsbr_scum_*.txt"):
                    try:
                        txt_file.unlink()
                    except Exception:
                        pass

            # 4. Gerar/Atualizar config.ini do provedor
            config_path = dst_mod_folder / "config.ini"
            if provider == PROVIDER_SCUM_RCON:
                config_content = _generate_rcon_ini(
                    bind_address=rcon_ip,
                    port=rcon_port,
                    password=rcon_password,
                )
            else:
                config_content = _generate_bsbr_ini()

            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(config_content, encoding="utf-8")

            # Garantir enabled.txt na pasta do mod
            enabled_txt = dst_mod_folder / "enabled.txt"
            if not enabled_txt.exists():
                enabled_txt.touch()

            # 5. Atualizar mods.txt para ativar este provedor e desativar o outro
            mods_txt_path = dst_ue4ss / "Mods" / "mods.txt"
            other_provider = PROVIDER_SCUM_RCON if provider == PROVIDER_BSBR else PROVIDER_BSBR
            self._update_mods_txt(mods_txt_path, enable_mod=provider, disable_mod=other_provider)

            # 6. Validação final pós-cópia
            installed_dll = dst_mod_folder / "dlls" / "main.dll"
            if not installed_dll.exists():
                return False, f"Falha na instalação: o arquivo 'dlls/main.dll' não foi encontrado em {dst_mod_folder}."

            provider_name = PROVIDER_NAMES.get(provider, provider)
            return True, f"{provider_name} instalado e ativado com sucesso! Reinicie o servidor para carregar."

        except PermissionError as e:
            return False, (
                f"Erro de permissão ao copiar arquivos de RCON: {e}\n\n"
                "O SCUM Server está em execução e bloqueando as DLLs.\n"
                "Por favor, pare o servidor SCUM antes de instalar ou trocar o mod de RCON."
            )
        except Exception as e:
            return False, f"Erro durante a instalação do mod: {e}"


    # ------------------------------------------------------------------
    # Desinstalação Modular
    # ------------------------------------------------------------------

    def uninstall(
        self,
        binaries_dir: str,
        provider: Optional[str] = None,
        remove_ue4ss_core: bool = False,
    ) -> Tuple[bool, str]:
        """
        Remove um provedor específico de RCON.
        Preserva a pasta ue4ss se outros mods existirem, a menos que remove_ue4ss_core=True.
        """
        bin_path = Path(binaries_dir)
        if not bin_path.is_dir():
            return False, f"Diretório de binários não encontrado: {binaries_dir}"

        target_provider = provider or self.get_installed_provider(binaries_dir)
        errors = []

        dst_ue4ss = bin_path / _SENTINEL_UE4SS
        mods_dir = dst_ue4ss / "Mods"

        # 1. Remover pasta do mod específico
        if target_provider and (mods_dir / target_provider).is_dir():
            try:
                shutil.rmtree(mods_dir / target_provider)
                self.logger.info(f"Mod '{target_provider}' removido de: {mods_dir / target_provider}")
            except Exception as e:
                errors.append(f"Erro ao remover pasta do mod {target_provider}: {e}")

        # Limpar resíduos específicos de arquivos txt se for bsbr_scum
        if target_provider == PROVIDER_BSBR:
            for txt_file in bin_path.glob("bsbr_scum_*.txt"):
                try:
                    txt_file.unlink()
                except Exception:
                    pass

        # 2. Atualizar mods.txt
        mods_txt_path = mods_dir / "mods.txt"
        if target_provider and mods_txt_path.exists():
            try:
                self._update_mods_txt(mods_txt_path, disable_mod=target_provider)
            except Exception:
                pass


        # 3. Verificar se ainda restam outros mods em ue4ss/Mods
        remaining_mods = []
        if mods_dir.is_dir():
            for item in mods_dir.iterdir():
                if item.is_dir() and item.name not in (PROVIDER_BSBR, PROVIDER_SCUM_RCON):
                    remaining_mods.append(item.name)

        # Se solicitado ou se não restou nenhum outro mod, limpar UE4SS core
        if remove_ue4ss_core or (not remaining_mods and not (mods_dir / PROVIDER_BSBR).exists() and not (mods_dir / PROVIDER_SCUM_RCON).exists()):
            dll_path = bin_path / _SENTINEL_DLL
            try:
                if dll_path.exists():
                    dll_path.unlink()
                    self.logger.info(f"dwmapi.dll removido de: {dll_path}")
            except Exception as e:
                errors.append(f"Erro ao remover dwmapi.dll: {e}")

            if remove_ue4ss_core:
                try:
                    if dst_ue4ss.is_dir():
                        shutil.rmtree(dst_ue4ss)
                        self.logger.info(f"Pasta ue4ss removida completamente: {dst_ue4ss}")
                except Exception as e:
                    errors.append(f"Erro ao remover pasta ue4ss: {e}")

        if errors:
            return False, "\n".join(errors)

        return True, "Mod RCON desinstalado com sucesso! Reinicie o servidor para aplicar."

    # ------------------------------------------------------------------
    # Atualização de Configuração
    # ------------------------------------------------------------------

    def update_config(
        self,
        binaries_dir: str,
        provider: str = PROVIDER_BSBR,
        rcon_ip: str = "127.0.0.1",
        rcon_port: Optional[int] = None,
        rcon_password: str = "",
    ) -> Tuple[bool, str]:
        """
        Atualiza o config.ini do mod instalado.
        """
        bin_path = Path(binaries_dir)
        config_path = bin_path / _SENTINEL_UE4SS / "Mods" / provider / "config.ini"
        if not config_path.exists():
            return False, f"Mod '{provider}' não está instalado. Instale antes de atualizar a configuração."

        if rcon_port is None:
            rcon_port = DEFAULT_PORTS.get(provider, 27100)

        try:
            if provider == PROVIDER_SCUM_RCON:
                content = _generate_rcon_ini(rcon_ip, rcon_port, rcon_password)
            else:
                content = _generate_bsbr_ini()

            config_path.write_text(content, encoding="utf-8")
            self.logger.info(f"config.ini de {provider} atualizado em: {config_path}")
            return True, f"Configuração do {provider} atualizada com sucesso!"
        except Exception as e:
            return False, f"Erro ao atualizar config.ini: {e}"

    # ------------------------------------------------------------------
    # Manipulação de mods.txt
    # ------------------------------------------------------------------

    def _read_mods_txt(self, mods_txt_path: Path) -> Dict[str, bool]:
        """Lê mods.txt e retorna dict {mod_name: is_enabled}."""
        if not mods_txt_path.exists():
            return {}
        result = {}
        try:
            for line in mods_txt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith(";"):
                    continue
                if ":" in line:
                    mod_name, _, val = line.partition(":")
                    mod_name = mod_name.strip()
                    val = val.strip()
                    result[mod_name] = (val == "1")
                elif "=" in line:
                    mod_name, _, val = line.partition("=")
                    mod_name = mod_name.strip()
                    val = val.strip()
                    result[mod_name] = (val == "1")
        except Exception:
            pass
        return result

    def _update_mods_txt(
        self,
        mods_txt_path: Path,
        enable_mod: Optional[str] = None,
        disable_mod: Optional[str] = None,
    ) -> None:
        """
        Atualiza o mods.txt definindo enable_mod como 1 e disable_mod como 0,
        preservando todos os outros mods já configurados.
        """
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


# ------------------------------------------------------------------
# Helpers internos
# ------------------------------------------------------------------

def _copy_tree_merge(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        dst_item = dst / item.name
        if item.is_dir():
            _copy_tree_merge(item, dst_item)
        else:
            shutil.copy2(item, dst_item)


def _generate_rcon_ini(bind_address: str, port: int, password: str) -> str:
    return (
        "; SCUM-RCON configuration\n"
        "; Gerado automaticamente pelo SSM Backend.\n"
        "\n"
        "[rcon]\n"
        f"bind_address = {bind_address}\n"
        f"port = {port}\n"
        f"password = {password}\n"
        "auth_log = true\n"
        "max_connections = 4\n"
        "\n"
        "[logging]\n"
        "log_level = info\n"
    )


def _generate_bsbr_ini() -> str:
    return (
        "; bsbr_scum configuration\n"
        "; Gerado automaticamente pelo SSM Backend.\n"
        "\n"
        "[debug]\n"
        "output_capture = 0\n"
    )


def _parse_rcon_ini(content: str) -> dict:
    result = {}
    for line in content.splitlines():
        line = line.strip()
        if line.startswith(";") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key == "bind_address":
            result["ip"] = value
        elif key == "port":
            try:
                result["port"] = int(value)
            except ValueError:
                pass
        elif key == "password":
            result["password"] = value
    return result
