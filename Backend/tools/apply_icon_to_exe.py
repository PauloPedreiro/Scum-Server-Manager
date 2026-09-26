#!/usr/bin/env python3
"""
Script para aplicar ícone a executáveis após compilação PyInstaller
Usa pefile para modificar recursos do executável Windows
"""
import sys
import subprocess
from pathlib import Path


def install_pefile():
    """Instalar pefile se não estiver instalado"""
    try:
        import pefile

        return True
    except ImportError:
        print("[INFO] Instalando pefile...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pefile"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            import pefile

            return True
        except Exception as e:
            print(f"[ERRO] Não foi possível instalar pefile: {e}")
            return False


def apply_icon_with_rcedit(exe_path: Path, icon_path: Path):
    """
    Aplicar ícone usando rcedit (ferramenta externa)
    Requer rcedit.exe no PATH ou na pasta tools/
    """
    # Verificar se rcedit existe
    rcedit_paths = [
        Path("tools") / "rcedit.exe",
        Path("rcedit.exe"),
        Path("tools") / "rcedit-x64.exe",
    ]

    rcedit = None
    for path in rcedit_paths:
        if path.exists():
            rcedit = path
            break

    if not rcedit:
        # Tentar usar rcedit do npm (se instalado)
        try:
            result = subprocess.run(
                ["rcedit", "--version"], capture_output=True, text=True, timeout=5
            )
            rcedit = "rcedit"
        except:
            pass

    if not rcedit:
        return False, "rcedit não encontrado"

    try:
        cmd = [str(rcedit), str(exe_path), "--set-icon", str(icon_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return True, "Ícone aplicado com sucesso usando rcedit"
        else:
            return False, f"Erro ao aplicar ícone: {result.stderr}"
    except Exception as e:
        return False, f"Erro ao executar rcedit: {e}"


def apply_icon_with_pefile(exe_path: Path, icon_path: Path):
    """
    Aplicar ícone usando pefile (biblioteca Python)
    Nota: pefile pode não suportar modificar ícones diretamente
    """
    if not install_pefile():
        return False, "pefile não disponível"

    try:
        import pefile

        # Ler o executável
        pe = pefile.PE(str(exe_path))

        # pefile não suporta modificar recursos diretamente
        # Precisamos usar outra abordagem
        return False, "pefile não suporta modificar ícones diretamente"
    except Exception as e:
        return False, f"Erro ao usar pefile: {e}"


def apply_icon_with_python(exe_path: Path, icon_path: Path):
    """
    Tentar aplicar ícone usando diferentes métodos
    """
    # Método 1: Tentar rcedit primeiro (mais confiável)
    success, message = apply_icon_with_rcedit(exe_path, icon_path)
    if success:
        return True, message

    # Método 2: Instruir usuário a usar Resource Hacker manualmente
    print(f"[AVISO] Não foi possível aplicar ícone automaticamente.")
    print(f"        Use Resource Hacker para aplicar o ícone manualmente:")
    print(f"        1. Baixe Resource Hacker: http://www.angusj.com/resourcehacker/")
    print(f"        2. Abra {exe_path}")
    print(f"        3. Vá em Action > Replace Icon")
    print(f"        4. Selecione {icon_path}")
    print(f"        5. Salve o arquivo")

    return False, message


def main():
    """Função principal"""
    if len(sys.argv) < 3:
        print("Uso: python apply_icon_to_exe.py <exe_path> <icon_path>")
        print(
            "Exemplo: python apply_icon_to_exe.py dist/ssm_gui.exe data/imagens/LogoSSM/Logo_SSM_256x256.ico"
        )
        return 1

    exe_path = Path(sys.argv[1])
    icon_path = Path(sys.argv[2])

    if not exe_path.exists():
        print(f"[ERRO] Executável não encontrado: {exe_path}")
        return 1

    if not icon_path.exists():
        print(f"[ERRO] Ícone não encontrado: {icon_path}")
        return 1

    print(f"Aplicando ícone...")
    print(f"  Executável: {exe_path}")
    print(f"  Ícone: {icon_path}")

    success, message = apply_icon_with_python(exe_path, icon_path)

    if success:
        print(f"[OK] {message}")
        return 0
    else:
        print(f"[ERRO] {message}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
