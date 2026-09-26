#!/usr/bin/env python3
"""
Script para aplicar ícones aos executáveis após compilação PyInstaller
Usa win32api para modificar recursos do executável Windows
"""
import sys
import subprocess
from pathlib import Path


def install_win32api():
    """Instalar pywin32 se não estiver instalado"""
    try:
        import win32api
        import win32con

        return True
    except ImportError:
        print("[INFO] Instalando pywin32...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pywin32"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            import win32api
            import win32con

            return True
        except Exception as e:
            print(f"[AVISO] Não foi possível instalar pywin32: {e}")
            return False


def apply_icon_win32api(exe_path: Path, icon_path: Path):
    """
    Aplicar ícone usando win32api (método mais direto no Windows)
    """
    if not install_win32api():
        return False, "pywin32 não disponível"

    try:
        import win32api
        import win32con
        import win32gui

        # Carregar o ícone
        icon_handle = win32gui.LoadImage(
            0,
            str(icon_path),
            win32con.IMAGE_ICON,
            0,
            0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
        )

        if not icon_handle:
            return False, "Não foi possível carregar o ícone"

        # Nota: win32api não suporta modificar recursos de executáveis diretamente
        # Precisamos usar outra abordagem
        return False, "win32api não suporta modificar ícones de executáveis diretamente"

    except Exception as e:
        return False, f"Erro ao usar win32api: {e}"


def apply_icon_with_resource_hacker(exe_path: Path, icon_path: Path):
    """
    Aplicar ícone usando Resource Hacker (ferramenta externa)
    """
    # Verificar se Resource Hacker existe
    res_hacker_paths = [
        Path("tools") / "ResourceHacker.exe",
        Path("ResourceHacker.exe"),
        Path("C:/Program Files/Resource Hacker/ResourceHacker.exe"),
    ]

    res_hacker = None
    for path in res_hacker_paths:
        if path.exists():
            res_hacker = path
            break

    if not res_hacker:
        return False, "Resource Hacker não encontrado"

    try:
        # Criar script temporário para Resource Hacker
        script_content = f"""
-open "{exe_path}"
-save "{exe_path}"
-action addoverwrite
-resource "{icon_path}"
-mask ICONGROUP,1,
"""
        script_path = exe_path.parent / "temp_icon_script.txt"
        script_path.write_text(script_content, encoding="utf-8")

        cmd = [str(res_hacker), "-script", str(script_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        # Limpar script temporário
        if script_path.exists():
            script_path.unlink()

        if result.returncode == 0:
            return True, "Ícone aplicado com sucesso usando Resource Hacker"
        else:
            return False, f"Erro ao aplicar ícone: {result.stderr}"
    except Exception as e:
        return False, f"Erro ao executar Resource Hacker: {e}"


def apply_icon_simple_copy(exe_path: Path, icon_path: Path):
    """
    Método simples: verificar se o PyInstaller aplicou o ícone
    e fornecer instruções se não aplicou
    """
    print(f"[INFO] Verificando se o ícone foi aplicado ao executável...")
    print(f"       Executável: {exe_path}")
    print(f"       Ícone: {icon_path}")

    # Verificar se o executável existe
    if not exe_path.exists():
        return False, f"Executável não encontrado: {exe_path}"

    if not icon_path.exists():
        return False, f"Ícone não encontrado: {icon_path}"

    # Tentar Resource Hacker primeiro
    success, message = apply_icon_with_resource_hacker(exe_path, icon_path)
    if success:
        return True, message

    # Se não funcionar, fornecer instruções
    print(f"\n[AVISO] Não foi possível aplicar o ícone automaticamente.")
    print(f"        O PyInstaller deve aplicar o ícone durante a compilação.")
    print(f"        Se o ícone não aparecer, use uma das seguintes opções:\n")
    print(f"        OPÇÃO 1: Resource Hacker (Recomendado)")
    print(f"        1. Baixe: http://www.angusj.com/resourcehacker/")
    print(f"        2. Abra Resource Hacker")
    print(f"        3. Abra o arquivo: {exe_path}")
    print(f"        4. Vá em Action > Replace Icon")
    print(f"        5. Selecione: {icon_path}")
    print(f"        6. Clique em Replace Icon")
    print(f"        7. Salve o arquivo (Ctrl+S)\n")
    print(f"        OPÇÃO 2: Verificar spec file")
    print(f"        Certifique-se de que o spec file está usando o ícone correto:")
    print(f"        icon='{icon_path.relative_to(Path.cwd())}'\n")

    return False, message


def main():
    """Função principal"""
    root_dir = Path(__file__).parent.parent
    dist_dir = root_dir / "dist"

    # Caminhos dos ícones
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
        print("       Execute: python tools/create_multi_size_icon.py")
        return 1

    # Executáveis para aplicar ícone
    executables = [
        dist_dir / "Panel SSM.exe",
        # Removido: SSM Backend.exe e launcher.exe (integrados no Panel SSM)
    ]

    print("=" * 60)
    print("Aplicando ícones aos executáveis...")
    print("=" * 60)

    success_count = 0
    for exe_path in executables:
        if not exe_path.exists():
            print(f"[AVISO] {exe_path.name} não encontrado, pulando...")
            continue

        print(f"\nProcessando: {exe_path.name}")
        success, message = apply_icon_simple_copy(exe_path, icon_path)

        if success:
            print(f"[OK] {message}")
            success_count += 1
        else:
            print(f"[AVISO] {message}")

    print("\n" + "=" * 60)
    print(
        f"Processo concluído: {success_count}/{len([e for e in executables if e.exists()])} executáveis processados"
    )
    print("=" * 60)

    if success_count == 0:
        print("\n[INFO] Se os ícones não aparecerem, use Resource Hacker manualmente")
        print("       ou verifique se o spec file está configurado corretamente.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
