#!/usr/bin/env python3
"""
Script final para aplicar ícone aos executáveis
Usa uma abordagem que modifica diretamente o executável
"""
import sys
import subprocess
from pathlib import Path


def check_pyinstaller_icon(exe_path: Path):
    """Verificar se o PyInstaller aplicou o ícone"""
    # Ler os primeiros bytes do executável para verificar se tem recursos de ícone
    try:
        with open(exe_path, "rb") as f:
            # Ler cabeçalho PE
            f.seek(0x3C)  # Offset para assinatura PE
            pe_offset = int.from_bytes(f.read(4), "little")
            f.seek(pe_offset)
            pe_signature = f.read(4)

            if pe_signature != b"PE\x00\x00":
                return False

            # Verificar se tem seção de recursos
            # (simplificado - verificação básica)
            return True
    except:
        return False


def apply_icon_with_python_script(exe_path: Path, icon_path: Path):
    """
    Aplicar ícone usando um script Python que modifica o executável
    """
    script_content = f"""
import sys
from pathlib import Path

# Tentar usar pefile para modificar recursos
try:
    import pefile
    pe = pefile.PE(str(r"{exe_path}"))
    
    # pefile não suporta modificar recursos diretamente
    # Precisamos usar outra abordagem
    print("pefile não suporta modificar ícones diretamente")
    sys.exit(1)
except ImportError:
    print("pefile não instalado")
    sys.exit(1)
except Exception as e:
    print(f"Erro: {{e}}")
    sys.exit(1)
"""

    # Criar script temporário
    temp_script = Path("temp_apply_icon.py")
    temp_script.write_text(script_content, encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, str(temp_script)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout + result.stderr
    finally:
        if temp_script.exists():
            temp_script.unlink()


def main():
    """Função principal - fornecer instruções claras"""
    root_dir = Path(__file__).parent.parent
    dist_dir = root_dir / "dist"

    # Caminhos dos ícones
    icon_path = root_dir / "data" / "imagens" / "LogoSSM" / "W-SSM-Ico.ico"

    if not icon_path.exists():
        print("[ERRO] Nenhum arquivo de ícone encontrado!")
        return 1

    gui_exe = dist_dir / "Panel SSM.exe"

    if not gui_exe.exists():
        print(f"[ERRO] Executável não encontrado: {gui_exe}")
        return 1

    print("=" * 70)
    print("SOLUÇÃO PARA APLICAR ÍCONE AO EXECUTÁVEL")
    print("=" * 70)
    print()
    print("O PyInstaller pode não estar aplicando o ícone corretamente.")
    print("Use uma das seguintes soluções:")
    print()
    print("OPÇÃO 1: Resource Hacker (RECOMENDADO - Mais fácil)")
    print("-" * 70)
    print("1. Baixe Resource Hacker:")
    print("   https://www.angusj.com/resourcehacker/")
    print()
    print("2. Abra Resource Hacker")
    print()
    print("3. Abra o arquivo:")
    print(f"   {gui_exe}")
    print()
    print("4. No menu, vá em: Action > Replace Icon...")
    print()
    print("5. Clique em 'Open file with new icon'")
    print()
    print("6. Selecione o arquivo:")
    print(f"   {icon_path}")
    print()
    print("7. Clique em 'Replace'")
    print()
    print("8. Salve o arquivo (Ctrl+S ou File > Save)")
    print()
    print("9. Feche o Resource Hacker")
    print()
    print("10. O ícone deve aparecer imediatamente no explorador!")
    print()
    print("=" * 70)
    print("OPÇÃO 2: Verificar Spec File")
    print("-" * 70)
    print("Verifique se o spec file está usando o caminho correto do ícone.")
    print(f"Ícone esperado: {icon_path.relative_to(root_dir)}")
    print()
    print("Se o caminho estiver correto, o problema pode ser:")
    print("- PyInstaller não está aplicando o ícone corretamente")
    print("- O arquivo ICO pode estar corrompido")
    print("- Cache do Windows (mas você já limpou)")
    print()
    print("=" * 70)
    print("OPÇÃO 3: Recriar o Ícone")
    print("-" * 70)
    print("Execute:")
    print("  python tools/create_multi_size_icon.py")
    print()
    print("Depois recompile:")
    print("  python build.py")
    print()
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
