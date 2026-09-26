"""
Git Pre-Commit Hook - Atualizar versão automaticamente baseado em tags Git
Opcional: Pode ser usado como hook do Git para atualizar versão automaticamente
"""

import re
import subprocess
import sys
from pathlib import Path

VERSION_FILE = Path(__file__).parent.parent / "version.py"


def get_git_tag_version():
    """Obter versão da última tag Git"""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True,
        )
        tag = result.stdout.strip()
        # Remover 'v' se presente (ex: v3.0.1 -> 3.0.1)
        tag = tag.lstrip("v")
        # Validar formato
        if re.match(r"^\d+\.\d+\.\d+$", tag):
            return tag
    except subprocess.CalledProcessError:
        pass  # Nenhuma tag encontrada
    except FileNotFoundError:
        pass  # Git não instalado
    return None


def get_current_version():
    """Obter versão atual do arquivo"""
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


def update_version_from_git():
    """Atualizar versão baseada na tag Git mais recente"""
    git_version = get_git_tag_version()
    if not git_version:
        print("ℹ️  Nenhuma tag Git encontrada - mantendo versão atual")
        return False

    current_version = get_current_version()
    if current_version == git_version:
        print(f"✅ Versão já está atualizada: {git_version}")
        return True

    # Atualizar versão
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(
            r'__version__\s*=\s*["\'][^"\']+["\']',
            f'__version__ = "{git_version}"',
            content,
        )

        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(content)

        print(
            f"✅ Versão atualizada de {current_version} para {git_version} (baseado na tag Git)"
        )
        return True
    except Exception as e:
        print(f"❌ Erro ao atualizar versão: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Modo automático: atualizar baseado em tag Git
        update_version_from_git()
    else:
        print("Git Pre-Commit Hook - Atualizador de Versão")
        print("Uso: python tools/pre_commit_hook.py --auto")
