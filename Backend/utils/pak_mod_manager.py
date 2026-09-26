"""
PakModManager - Gerencia a instalação, listagem, ativação e remoção de mods de conteúdo .pak no SCUM Server.

Os mods de conteúdo do Unreal Engine ficam localizados em:
    <scum_root>/SCUM/Content/Paks/~mods/
    ou
    <scum_root>/Content/Paks/~mods/

Arquivos com extensão .pak são carregados pelo jogo.
Arquivos com extensão .pak.disabled são ignorados pelo jogo, permitindo pausar mods sem deletá-los.
"""
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import StructuredLogger


def _format_file_size(size_bytes: int) -> str:
    """Formata tamanho de arquivo em formato legível (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class PakModManager:
    """
    Gerenciador de mods de conteúdo .pak em Content/Paks/~mods/ com cópia segura em data/mods/paks/.
    """

    def __init__(self, root_dir: Optional[str] = None, logger: Optional[StructuredLogger] = None):
        self.logger = logger or StructuredLogger()
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()
        self.safe_storage_dir = self.root_dir / "data" / "mods" / "paks"
        self.safe_storage_dir.mkdir(parents=True, exist_ok=True)

    def get_safe_storage_dir(self) -> Path:
        """Retorna o diretório de armazenamento seguro em data/mods/paks/."""
        self.safe_storage_dir.mkdir(parents=True, exist_ok=True)
        return self.safe_storage_dir

    def resolve_paks_dir(self, scum_root: str) -> Optional[Path]:
        """
        Localiza o diretório Content/Paks do servidor SCUM.
        Testa estruturas comuns de pastas de servidores dedicados.
        """
        if not scum_root:
            return None

        root_path = Path(scum_root)
        candidates = [
            root_path / "SCUM" / "Content" / "Paks",
            root_path / "Content" / "Paks",
            root_path / "scum" / "SCUM" / "Content" / "Paks",
            root_path.parent / "Content" / "Paks",
        ]

        for cand in candidates:
            if cand.is_dir():
                return cand

        # Se a pasta Content existir mas Paks ainda não, usar o caminho padrão
        for parent_cand in [root_path / "SCUM" / "Content", root_path / "Content"]:
            if parent_cand.is_dir():
                paks_dir = parent_cand / "Paks"
                paks_dir.mkdir(parents=True, exist_ok=True)
                return paks_dir

        # Fallback padrão
        default_dir = root_path / "SCUM" / "Content" / "Paks"
        return default_dir

    def get_mods_dir(self, scum_root: str) -> Optional[Path]:
        """
        Retorna o caminho da pasta ~mods/ dentro de Content/Paks/.
        """
        paks_dir = self.resolve_paks_dir(scum_root)
        if not paks_dir:
            return None

        target = paks_dir / "~mods"
        legacy = paks_dir / "mods"

        # Migração transparente se a pasta sem til (mods/) existir
        if legacy.is_dir() and not target.is_dir():
            try:
                legacy.rename(target)
            except Exception:
                pass

        return target

    def ensure_mods_dir(self, scum_root: str) -> Path:
        """
        Garante que a pasta ~mods/ exista, criando-a se necessário.
        """
        mods_dir = self.get_mods_dir(scum_root)
        if not mods_dir:
            raise ValueError(f"Could not resolve Paks path for: {scum_root}")

        mods_dir.mkdir(parents=True, exist_ok=True)
        return mods_dir


    def list_mods(self, scum_root: str) -> List[Dict[str, Any]]:
        """
        Lista todos os mods .pak presentes na pasta mods/.

        Returns:
            Lista de dicionários com metadados de cada mod.
        """
        mods_dir = self.get_mods_dir(scum_root)
        if not mods_dir or not mods_dir.is_dir():
            return []

        mods = []
        try:
            for item in sorted(mods_dir.iterdir()):
                if not item.is_file():
                    continue

                name_lower = item.name.lower()
                is_pak = name_lower.endswith(".pak")
                is_disabled = name_lower.endswith(".pak.disabled") or name_lower.endswith(".disabled")

                if not (is_pak or is_disabled):
                    continue

                try:
                    stat = item.stat()
                    size_bytes = stat.st_size
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
                except Exception:
                    size_bytes = 0
                    mtime = "N/A"

                display_name = item.name
                if display_name.lower().endswith(".disabled"):
                    display_name = display_name[:-9]

                mods.append({
                    "filename": item.name,
                    "display_name": display_name,
                    "path": str(item),
                    "size_bytes": size_bytes,
                    "size_formatted": _format_file_size(size_bytes),
                    "is_active": is_pak,
                    "modified_time": mtime,
                })
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao listar mods .pak: {e}")

        return mods

    def install_pak(self, scum_root: str, source_path: str) -> Tuple[bool, str]:
        """
        Instala um novo arquivo .pak copiando-o para a pasta mods/ do servidor e
        salvando uma cópia segura em data/mods/paks/.
        """
        src = Path(source_path)
        if not src.is_file():
            return False, f"Source file not found: {source_path}"

        if not src.name.lower().endswith(".pak"):
            return False, "The selected file must have a .pak extension."

        try:
            # 1. Salvar uma cópia de segurança em data/mods/paks/
            storage_dir = self.get_safe_storage_dir()
            safe_backup_dst = storage_dir / src.name
            if src.resolve() != safe_backup_dst.resolve():
                shutil.copy2(src, safe_backup_dst)
                if self.logger:
                    self.logger.info(f"Mod .pak saved to safe storage: {src.name} → {safe_backup_dst}")

            # 2. Instalar na pasta mods do servidor SCUM
            mods_dir = self.ensure_mods_dir(scum_root)
            server_dst = mods_dir / src.name
            shutil.copy2(src, server_dst)
            if self.logger:
                self.logger.info(f"Mod .pak installed to server: {src.name} → {server_dst}")

            return True, f"Mod '{src.name}' successfully installed to server and saved in data/mods/paks/!"
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing mod .pak: {e}")
            return False, f"Error installing mod .pak: {e}"


    def toggle_pak(self, scum_root: str, filename: str) -> Tuple[bool, str]:
        """
        Alterna o status do mod entre ativo (.pak) e inativo (.pak.disabled).
        """
        mods_dir = self.get_mods_dir(scum_root)
        if not mods_dir or not mods_dir.is_dir():
            return False, "Diretório mods não encontrado."

        target = mods_dir / filename
        if not target.exists():
            return False, f"Arquivo '{filename}' não encontrado em mods."

        try:
            if filename.lower().endswith(".disabled"):
                # Ativar: remover .disabled
                new_name = filename[:-9]
                new_path = mods_dir / new_name
                target.rename(new_path)
                if self.logger:
                    self.logger.info(f"Mod .pak ativado: {filename} → {new_name}")
                return True, f"Mod '{new_name}' ativado com sucesso!"
            else:
                # Desativar: adicionar .disabled
                new_name = f"{filename}.disabled"
                new_path = mods_dir / new_name
                target.rename(new_path)
                if self.logger:
                    self.logger.info(f"Mod .pak desativado: {filename} → {new_name}")
                return True, f"Mod '{filename}' desativado (renomeado para .disabled)!"
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao alternar status do mod .pak: {e}")
            return False, f"Erro ao alterar status: {e}"

    def delete_pak(self, scum_root: str, filename: str) -> Tuple[bool, str]:
        """
        Exclui permanentemente um arquivo de mod da pasta mods/.
        """
        mods_dir = self.get_mods_dir(scum_root)
        if not mods_dir or not mods_dir.is_dir():
            return False, "Diretório mods não encontrado."

        target = mods_dir / filename
        if not target.exists():
            return False, f"Arquivo '{filename}' não encontrado."

        try:
            target.unlink()
            if self.logger:
                self.logger.info(f"Mod .pak removido: {filename}")
            return True, f"Mod '{filename}' removido com sucesso!"
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao excluir mod .pak: {e}")
            return False, f"Erro ao excluir: {e}"

    def open_mods_folder_in_explorer(self, scum_root: str) -> Tuple[bool, str]:
        """
        Abre a pasta mods do servidor no Windows Explorer.
        """
        try:
            mods_dir = self.ensure_mods_dir(scum_root)
            if sys.platform == "win32":
                os.startfile(str(mods_dir))
            else:
                subprocess.Popen(["xdg-open", str(mods_dir)])
            return True, f"Folder opened: {mods_dir}"
        except Exception as e:
            return False, f"Failed to open folder: {e}"

    def open_safe_storage_in_explorer(self) -> Tuple[bool, str]:
        """
        Abre a pasta de armazenamento seguro (data/mods/paks/) no Windows Explorer.
        """
        try:
            storage_dir = self.get_safe_storage_dir()
            if sys.platform == "win32":
                os.startfile(str(storage_dir))
            else:
                subprocess.Popen(["xdg-open", str(storage_dir)])
            return True, f"Folder opened: {storage_dir}"
        except Exception as e:
            return False, f"Failed to open safe storage folder: {e}"

