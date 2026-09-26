#!/usr/bin/env python3
"""
Script para aplicar ícone aos executáveis usando rcedit
rcedit é uma ferramenta de linha de comando para modificar recursos de executáveis Windows
"""
import sys
import subprocess
import shutil
from pathlib import Path
import urllib.request
import zipfile
import tempfile


def download_rcedit():
    """Baixar rcedit se não estiver disponível"""
    tools_dir = Path(__file__).parent
    rcedit_dir = tools_dir / "rcedit"
    rcedit_exe = rcedit_dir / "rcedit-x64.exe"

    if rcedit_exe.exists():
        return rcedit_exe

    print("[INFO] rcedit não encontrado. Baixando...")

    # URL do rcedit (versão pré-compilada)
    # Nota: rcedit é uma ferramenta Node.js, mas há versões pré-compiladas
    # Vamos tentar usar npx se Node.js estiver instalado
    try:
        result = subprocess.run(
            ["npx", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if result.returncode == 0:
            print("[OK] Node.js encontrado, usando npx rcedit")
            return "npx"  # Usar npx
    except:
        pass

    # Se não tiver Node.js, fornecer instruções
    print("[AVISO] rcedit não está disponível e Node.js não foi encontrado.")
    print("        Opções:")
    print("        1. Instale Node.js: https://nodejs.org/")
    print("        2. Depois execute: npx rcedit --help")
    print("        3. Ou use Resource Hacker manualmente")
    return None


def apply_icon_with_rcedit(exe_path: Path, icon_path: Path, rcedit_cmd):
    """Aplicar ícone usando rcedit"""
    try:
        if rcedit_cmd == "npx":
            cmd = ["npx", "-y", "rcedit", str(exe_path), "--set-icon", str(icon_path)]
        else:
            cmd = [str(rcedit_cmd), str(exe_path), "--set-icon", str(icon_path)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        if result.returncode == 0:
            return True, "Ícone aplicado com sucesso"
        else:
            return False, f"Erro: {result.stderr or result.stdout}"
    except FileNotFoundError:
        return False, "rcedit não encontrado"
    except Exception as e:
        return False, f"Erro ao executar rcedit: {e}"


def main():
    """Função principal"""
    root_dir = Path(__file__).parent.parent
    dist_dir = root_dir / "dist"

    # Caminho do ícone
    icon_paths = [
        root_dir / "data" / "imagens" / "LogoSSM" / "W-SSM-Ico.ico",
    ]

    icon_path = None
    for path in icon_paths:
        if path.exists():
            icon_path = path
            break

    if not icon_path:
        print("[ERRO] Nenhum arquivo de ícone encontrado!")
        return 1

    # Verificar se rcedit está disponível
    rcedit_cmd = download_rcedit()
    if not rcedit_cmd:
        print()
        print("=" * 70)
        print("SOLUÇÃO ALTERNATIVA: Resource Hacker")
        print("=" * 70)
        print("Como rcedit não está disponível, use Resource Hacker:")
        print()
        print("1. Baixe Resource Hacker:")
        print("   http://www.angusj.com/resourcehacker/")
        print()
        print("2. Para cada executável em dist/:")
        executables = [
            dist_dir / "Panel SSM.exe",
            # Removido: SSM Backend.exe e launcher.exe (integrados no Panel SSM)
        ]
        for exe in executables:
            if exe.exists():
                print(f"   - Abra: {exe.name}")
                print(f"     Action > Replace Icon...")
                print(f"     Selecione: {icon_path.name}")
                print(f"     Clique em Replace")
                print(f"     Salve (Ctrl+S)")
        return 1

    # Executáveis para aplicar ícone
    executables = [
        dist_dir / "Panel SSM.exe",
        # Removido: SSM Backend.exe e launcher.exe (integrados no Panel SSM)
    ]

    print("=" * 70)
    print("Aplicando ícones aos executáveis usando rcedit")
    print("=" * 70)
    print(f"Ícone: {icon_path.name}")
    print()

    success_count = 0
    for exe_path in executables:
        if not exe_path.exists():
            print(f"[AVISO] {exe_path.name} não encontrado, pulando...")
            continue

        print(f"Processando: {exe_path.name}...", end=" ")
        success, message = apply_icon_with_rcedit(exe_path, icon_path, rcedit_cmd)

        if success:
            print(f"[OK]")
            success_count += 1
        else:
            print(f"[ERRO] {message}")

    print()
    print("=" * 70)
    print(
        f"Resultado: {success_count}/{len([e for e in executables if e.exists()])} executáveis processados"
    )
    print("=" * 70)

    if success_count > 0:
        print()
        print("[OK] Ícones aplicados! Se não aparecerem imediatamente:")
        print("     1. Limpe o cache de ícones do Windows")
        print(
            "     2. Reinicie o Explorer (taskkill /f /im explorer.exe && start explorer.exe)"
        )
        print("     3. Ou reinicie o computador")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
