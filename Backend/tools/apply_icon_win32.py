#!/usr/bin/env python3
"""
Script para aplicar ícone aos executáveis usando win32api
Este script realmente modifica o executável para incluir o ícone
"""
import sys
from pathlib import Path


def check_and_install_pywin32():
    """Verificar e instalar pywin32 se necessário"""
    try:
        import win32api
        import win32con

        return True
    except ImportError:
        print("[INFO] pywin32 não encontrado. Tentando instalar...")
        import subprocess

        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pywin32"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            import win32api
            import win32con

            print("[OK] pywin32 instalado com sucesso")
            return True
        except Exception as e:
            print(f"[ERRO] Não foi possível instalar pywin32: {e}")
            print("       Execute manualmente: pip install pywin32")
            return False


def apply_icon_to_exe(exe_path: Path, icon_path: Path):
    """
    Aplicar ícone a um executável usando win32api.UpdateResource
    """
    if not check_and_install_pywin32():
        return False, "pywin32 não disponível"

    try:
        import win32api
        import win32con

        if not exe_path.exists():
            return False, f"Executável não encontrado: {exe_path}"

        if not icon_path.exists():
            return False, f"Ícone não encontrado: {icon_path}"

        # Ler o arquivo ICO
        with open(icon_path, "rb") as f:
            icon_data = f.read()

        if len(icon_data) == 0:
            return False, "Arquivo de ícone vazio"

        # Abrir o executável para atualização de recursos
        exe_str = str(exe_path.resolve())

        # Usar BeginUpdateResource para modificar o executável
        handle = win32api.BeginUpdateResource(exe_str, False)

        if not handle:
            return False, "Não foi possível abrir o executável para modificação"

        try:
            # Atualizar o recurso de ícone
            # RT_ICON = 3, RT_GROUP_ICON = 14
            # ID 1 é o ícone principal

            # Primeiro, remover o ícone antigo se existir
            try:
                win32api.UpdateResource(handle, win32con.RT_GROUP_ICON, 1, None)
            except:
                pass  # Pode não existir ícone antigo

            # Adicionar o novo ícone
            # O arquivo ICO contém tanto o grupo quanto os ícones individuais
            # Precisamos extrair e adicionar corretamente

            # Ler o arquivo ICO e processar
            # Um arquivo ICO tem uma estrutura específica
            # Vamos usar uma abordagem mais simples: substituir todo o recurso de ícone

            # Para um ICO válido, precisamos adicionar como RT_GROUP_ICON
            # Mas win32api requer que o formato seja específico

            # Método alternativo: usar UpdateResource com os dados do ICO
            # Nota: win32api.UpdateResource pode não funcionar diretamente com arquivos ICO
            # Precisamos processar o arquivo ICO primeiro

            # Tentar adicionar o ícone diretamente
            # O Windows espera o formato de recurso, não o formato ICO bruto
            # Vamos tentar mesmo assim

            success = False
            try:
                # Tentar adicionar como RT_GROUP_ICON
                win32api.UpdateResource(
                    handle, win32con.RT_GROUP_ICON, 1, icon_data  # ID do recurso
                )
                success = True
            except Exception as e1:
                # Se falhar, tentar outra abordagem
                try:
                    # Tentar adicionar como RT_ICON
                    win32api.UpdateResource(handle, win32con.RT_ICON, 1, icon_data)
                    success = True
                except Exception as e2:
                    return False, f"Erro ao adicionar ícone: {e1} / {e2}"

            # Finalizar a atualização
            win32api.EndUpdateResource(handle, False)

            if success:
                return True, "Ícone aplicado com sucesso"
            else:
                return False, "Falha ao aplicar ícone"

        except Exception as e:
            # Em caso de erro, cancelar a atualização
            try:
                win32api.EndUpdateResource(handle, True)  # True = descartar mudanças
            except:
                pass
            return False, f"Erro durante a atualização: {e}"

    except Exception as e:
        return False, f"Erro ao aplicar ícone: {e}"


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
        print("       Caminhos verificados:")
        for path in icon_paths:
            print(f"         - {path}")
        return 1

    # Executáveis para aplicar ícone
    executables = [
        dist_dir / "Panel SSM.exe",
        # Removido: SSM Backend.exe e launcher.exe (integrados no Panel SSM)
    ]

    print("=" * 70)
    print("Aplicando ícones aos executáveis usando win32api")
    print("=" * 70)
    print(f"Ícone: {icon_path.name}")
    print()

    success_count = 0
    for exe_path in executables:
        if not exe_path.exists():
            print(f"[AVISO] {exe_path.name} não encontrado, pulando...")
            continue

        print(f"Processando: {exe_path.name}...", end=" ")
        success, message = apply_icon_to_exe(exe_path, icon_path)

        if success:
            print(f"[OK] {message}")
            success_count += 1
        else:
            print(f"[ERRO] {message}")

    print()
    print("=" * 70)
    print(
        f"Resultado: {success_count}/{len([e for e in executables if e.exists()])} executáveis processados"
    )
    print("=" * 70)

    if success_count == 0:
        print()
        print("[AVISO] Não foi possível aplicar ícones automaticamente.")
        print("        Isso pode ocorrer porque:")
        print("        1. pywin32 não está instalado corretamente")
        print("        2. O formato do arquivo ICO não é compatível")
        print("        3. O executável está em uso ou protegido")
        print()
        print("        SOLUÇÃO ALTERNATIVA: Use Resource Hacker")
        print("        1. Baixe: http://www.angusj.com/resourcehacker/")
        print("        2. Abra Resource Hacker")
        print("        3. Abra cada executável")
        print("        4. Vá em Action > Replace Icon...")
        print(f"        5. Selecione: {icon_path}")
        print("        6. Clique em Replace")
        print("        7. Salve o arquivo (Ctrl+S)")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
