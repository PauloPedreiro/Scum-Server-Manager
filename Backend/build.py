#!/usr/bin/env python3
"""
Script de Build - Cria executável do SSM Backend usando PyInstaller
"""

import os
import sys
import shutil
import subprocess
import stat
import re
from pathlib import Path

ROOT_DIR = Path(__file__).parent
VERSION_FILE = ROOT_DIR / "version.py"
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"
SPEC_FILE = ROOT_DIR / "ssm_backend.spec"


def clean_build():
    """Limpar diretórios de build anteriores"""
    print("Limpando builds anteriores...")

    def remove_readonly(func, path, exc):
        """Callback para remover arquivos somente leitura no Windows"""
        try:
            # No Windows, usar os.chmod com stat
            os.chmod(path, stat.S_IWRITE)  # Remover flag somente leitura
            func(path)  # Tentar novamente
        except Exception:
            # Se ainda falhar, tentar remover a flag de somente leitura de outra forma
            try:
                if os.path.isdir(path):
                    os.chmod(path, 0o777)
                else:
                    os.chmod(path, 0o666)
                func(path)
            except Exception:
                pass  # Se ainda falhar, ignorar

    # Limpar build/
    if BUILD_DIR.exists():
        try:
            shutil.rmtree(BUILD_DIR, onerror=remove_readonly)
            print("[OK] Diretorio build/ removido")
        except Exception as e:
            print(f"[AVISO] Erro ao remover build/: {e}")

    # Limpar dist/ (mas manter se houver arquivos em uso)
    if DIST_DIR.exists():
        try:
            shutil.rmtree(DIST_DIR, onerror=remove_readonly)
            print("[OK] Diretorio dist/ removido")
        except PermissionError as e:
            print(
                f"[AVISO] Alguns arquivos em dist/ estao em uso. Tentando limpar seletivamente..."
            )
            # Tentar remover apenas os executáveis e _internal, manter data/
            try:
                for item in DIST_DIR.iterdir():
                    if item.is_file() and item.suffix == ".exe":
                        try:
                            item.unlink()
                            print(f"[OK] Removido: {item.name}")
                        except Exception:
                            pass
                    elif item.is_dir() and item.name == "_internal":
                        try:
                            shutil.rmtree(item, onerror=remove_readonly)
                            print(f"[OK] Removido diretorio: {item.name}")
                        except Exception:
                            pass
            except Exception as e2:
                print(
                    f"[AVISO] Nao foi possivel limpar completamente. Continuando mesmo assim..."
                )
        except Exception as e:
            print(f"[AVISO] Erro ao remover dist/: {e}")

    print("[OK] Limpeza concluida")


def check_pyinstaller():
    """Verificar se PyInstaller está instalado"""
    try:
        import PyInstaller

        print(f"[OK] PyInstaller encontrado (versao {PyInstaller.__version__})")
        return True
    except ImportError:
        print("[ERRO] PyInstaller nao encontrado!")
        print("Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller instalado")
        return True


def kill_processes_using_files():
    """Tentar fechar processos que possam estar usando os executáveis"""
    try:
        import psutil

        exe_names = [
            "Panel SSM.exe",
        ]  # Removido: SSM Backend.exe e launcher.exe (integrados no Panel SSM)
        killed = False

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc_name = proc.info["name"].lower()
                if any(exe_name.lower() in proc_name for exe_name in exe_names):
                    print(
                        f"[AVISO] Processo encontrado: {proc.info['name']} (PID: {proc.info['pid']})"
                    )
                    proc.terminate()
                    killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if killed:
            import time

            time.sleep(1)  # Aguardar processos terminarem
            print("[OK] Processos finalizados")
    except ImportError:
        pass  # psutil não disponível
    except Exception:
        pass  # Ignorar erros


def build_executable():
    """Criar executável usando PyInstaller"""
    print("\n" + "=" * 60)
    print("Iniciando build do executavel...")
    print("=" * 60 + "\n")

    # Tentar fechar processos que possam estar usando os executáveis
    print("Verificando processos em execucao...")
    kill_processes_using_files()

    try:
        # Comando PyInstaller
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            str(SPEC_FILE),
            "--clean",
            "--noconfirm",
        ]

        print(f"Executando: {' '.join(cmd)}\n")
        result = subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)

        # Copiar arquivos de dados adicionais
        print("\n" + "=" * 60)
        print("Copiando arquivos de dados adicionais...")
        print("=" * 60)
        copy_script = ROOT_DIR / "tools" / "copy_data_files.py"
        if copy_script.exists():
            result = subprocess.run(
                [sys.executable, str(copy_script)], cwd=str(ROOT_DIR), check=False
            )
            if result.returncode != 0:
                print(
                    "[AVISO] Alguns arquivos podem nao ter sido copiados corretamente"
                )
        else:
            print("[AVISO] Script de copia nao encontrado!")

        # Aplicar ícones aos executáveis após o build
        print("\n" + "=" * 60)
        print("Aplicando icones aos executaveis...")
        print("=" * 60)

        # Priorizar Resource Hacker (mais confiável)
        apply_icons_script = ROOT_DIR / "tools" / "apply_icon_resource_hacker.py"
        if not apply_icons_script.exists():
            # Fallback para rcedit
            apply_icons_script = ROOT_DIR / "tools" / "apply_icon_rcedit.py"
        if not apply_icons_script.exists():
            # Fallback para win32api
            apply_icons_script = ROOT_DIR / "tools" / "apply_icon_win32.py"

        if apply_icons_script.exists():
            result = subprocess.run(
                [sys.executable, str(apply_icons_script)],
                cwd=str(ROOT_DIR),
                check=False,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            if result.returncode != 0:
                print("[AVISO] Nao foi possivel aplicar os icones personalizados automaticamente.")
                print("        O executavel 'Panel SSM.exe' foi gerado com sucesso, mas usara o icone padrao.")
                print("        Para aplicar o icone personalizado, instale o Resource Hacker.")
            else:
                print("[OK] Icones aplicados com sucesso!")
        else:
            print("[AVISO] Script de aplicacao de icones nao encontrado!")

        print("\n" + "=" * 60)
        print("[OK] Build concluido com sucesso!")
        print("=" * 60)

        # Verificar onde os executáveis foram criados
        if (DIST_DIR / "Panel SSM.exe").exists():
            exe_dir = DIST_DIR
            print(f"\nExecutáveis criados em: {exe_dir}")
        elif (DIST_DIR / "Panel SSM" / "Panel SSM.exe").exists():
            exe_dir = DIST_DIR / "Panel SSM"
            print(f"\nExecutáveis criados em: {exe_dir}")
        else:
            exe_dir = DIST_DIR
            print(f"\nExecutáveis criados em: {exe_dir}")

        print("\nArquivos incluídos:")
        print("  - Panel SSM.exe (interface gráfica desktop + backend Flask integrado)")
        print("  - data/ (arquivos de configuração, imagens, templates)")
        print("  - base_coordinates.csv e base_coordinates.json")
        print("  - nssm-2.24/ (utilitários NSSM)")
        print("\nPara distribuir, copie todos os arquivos da pasta 'dist'.")
        print(f"Para executar:")
        print(f"   - Interface Principal: {exe_dir / 'Panel SSM.exe'}")
        print("     (inclui backend Flask integrado - inicia ao clicar 'Start')")
        print("\nNOTA: SSM Backend.exe e launcher.exe foram removidos.")
        print("      A funcionalidade do launcher está integrada no Panel SSM.")
        print("      O backend Flask roda em thread dentro do Panel SSM.")

        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERRO] Erro durante o build: {e}")
        return False
    except Exception as e:
        print(f"\n[ERRO] Erro inesperado: {e}")
        return False


def bump_version():
    """Incrementa automaticamente o patch da versão (ex: 3.22.0 -> 3.22.1)"""
    if not VERSION_FILE.exists():
        print("[AVISO] version.py nao encontrado, pulando bump de versao")
        return None

    content = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        print("[AVISO] Formato de versao nao reconhecido em version.py")
        return None

    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    old_version = f"{major}.{minor}.{patch}"
    new_version = f"{major}.{minor}.{patch + 1}"

    new_content = content.replace(f'__version__ = "{old_version}"', f'__version__ = "{new_version}"')
    VERSION_FILE.write_text(new_content, encoding="utf-8")

    print(f"[OK] Versao atualizada: {old_version} -> {new_version}")
    return new_version


def main():
    """Função principal"""
    print("=" * 60)
    print("SSM Backend - Build Script")
    print("=" * 60)
    print()

    # Verificar PyInstaller
    if not check_pyinstaller():
        sys.exit(1)

    # Incrementar versao automaticamente
    new_version = bump_version()

    # Limpar builds anteriores
    clean_build()

    # Verificar se spec file existe
    if not SPEC_FILE.exists():
        print(f"[ERRO] Arquivo {SPEC_FILE} nao encontrado!")
        print("Criando arquivo spec...")
        create_spec_file()

    # Build
    if build_executable():
        version_msg = f" (v{new_version})" if new_version else ""
        print(f"\n[OK] Processo concluido com sucesso!{version_msg}")
    else:
        print("\n[ERRO] Build falhou!")
        sys.exit(1)


def create_spec_file():
    """Criar arquivo spec se não existir"""
    # Isso será criado manualmente ou via PyInstaller
    print("Execute: pyinstaller --name=ssm_backend main.py")
    print("Depois ajuste o arquivo .spec gerado")


if __name__ == "__main__":
    main()
