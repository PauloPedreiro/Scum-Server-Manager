#!/usr/bin/env python3
"""
Launcher do SSM Backend
Abre a GUI do backend sem validações ou inicializações
"""

import os
import sys
import time
import subprocess
import traceback
import json
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False
    tk = None
    filedialog = None
    messagebox = None

from utils.app_data_dir import (
    get_legacy_appdata_dir,
    get_runtime_data_dir,
    migrate_legacy_data_dir,
)

# Detectar se está rodando como executável
if getattr(sys, "frozen", False):
    # Rodando como executável (PyInstaller)
    ROOT_DIR = Path(
        sys._MEIPASS
    )  # Diretório temporário do PyInstaller (arquivos empacotados)
    EXE_DIR = Path(
        sys.executable
    ).parent  # Diretório onde o .exe está (onde os dados devem estar)
    IS_EXE = True
else:
    # Rodando como script Python
    ROOT_DIR = Path(__file__).parent.parent
    EXE_DIR = ROOT_DIR
    IS_EXE = False

sys.path.insert(0, str(ROOT_DIR))

# Quando executável, usar diretório do .exe para dados (não o temporário!)
# Quando script, usar diretório do projeto
if IS_EXE:
    CONFIG_DIR = get_runtime_data_dir(is_exe=True, exe_dir=EXE_DIR)  # Portable: EXE_DIR/data
    legacy_appdata = get_legacy_appdata_dir()
    migrate_legacy_data_dir(legacy_appdata, CONFIG_DIR)
    # Arquivos de exemplo podem estar no diretório temporário (empacotados) ou no EXE_DIR
    CONFIG_EXAMPLE = ROOT_DIR / "data" / "config.example.json"  # Do empacotamento
    WEBHOOKS_EXAMPLE = ROOT_DIR / "data" / "webhooks.example.json"  # Do empacotamento
    # Mas também verificar se estão no EXE_DIR
    if not CONFIG_EXAMPLE.exists():
        CONFIG_EXAMPLE = EXE_DIR / "data" / "config.example.json"
    if not WEBHOOKS_EXAMPLE.exists():
        WEBHOOKS_EXAMPLE = EXE_DIR / "data" / "webhooks.example.json"
else:
    CONFIG_DIR = ROOT_DIR / "data"
    CONFIG_EXAMPLE = CONFIG_DIR / "config.example.json"
    WEBHOOKS_EXAMPLE = CONFIG_DIR / "webhooks.example.json"

CONFIG_FILE = CONFIG_DIR / "config.json"
WEBHOOKS_FILE = CONFIG_DIR / "webhooks.json"

# Criar diretório data se não existir
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def check_config_files():
    """Verificar se os arquivos de configuração existem"""
    config_exists = CONFIG_FILE.exists()
    webhooks_exists = WEBHOOKS_FILE.exists()

    # Auto-criar arquivos ausentes para evitar prompts/telas de "Configuration Required"
    try:
        if not config_exists:
            create_config_from_example()
            config_exists = CONFIG_FILE.exists()
    except Exception:
        pass

    try:
        if not webhooks_exists:
            create_webhooks_from_example()
            webhooks_exists = WEBHOOKS_FILE.exists()
    except Exception:
        pass

    return config_exists, webhooks_exists


def validate_json_file(file_path):
    """Validar se um arquivo JSON é válido"""
    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                json.load(f)
            return True, None
        return False, "Arquivo não existe"
    except json.JSONDecodeError as e:
        return False, f"JSON inválido: {str(e)}"
    except Exception as e:
        return False, f"Erro ao ler arquivo: {str(e)}"


def create_config_from_example():
    """Criar config.json a partir do exemplo ou criar um básico"""
    # Tentar encontrar o arquivo de exemplo (pode estar no ROOT_DIR ou EXE_DIR)
    example_paths = [CONFIG_EXAMPLE]
    if IS_EXE:
        # Também verificar no diretório do executável
        example_paths.append(EXE_DIR / "data" / "config.example.json")
        # E no diretório temporário do PyInstaller
        example_paths.append(ROOT_DIR / "data" / "config.example.json")

    # Tentar copiar do exemplo
    for example_path in example_paths:
        if example_path.exists() and not CONFIG_FILE.exists():
            try:
                import shutil

                # Garantir que o diretório de destino existe
                CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(example_path, CONFIG_FILE)
                print(f"[OK] Arquivo config.json criado a partir do exemplo")
                print(f"     Origem: {example_path}")
                print(f"     Destino: {CONFIG_FILE}")
                return True
            except Exception as e:
                print(f"[AVISO] Erro ao copiar exemplo: {e}")
                continue

    # Se não encontrou exemplo, criar um arquivo básico
    if not CONFIG_FILE.exists():
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            default_config = {
                "paths": {
                    "application": {
                        "data_directory": "data",
                        "logs_directory": "data/logs",
                        "database": "data/SSM.db",
                        "config_file": "data/config.json",
                        "webhooks_file": "data/webhooks.json",
                    },
                    "scum_server": {
                        "root_directory": "C:\\Servers\\Scum",
                        "binaries_directory": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64",
                        "logs_directory": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs",
                        "config_directory": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer",
                        "database": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db",
                        "savefiles_directory": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles",
                    },
                },
                "server": {
                    "server_path": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64",
                    "steamcmd_path": "C:\\Servers\\steamcmd",
                    "install_path": "C:\\Servers\\Scum",
                    "port": 8900,
                    "max_players": 64,
                    "use_battleye": True,
                    "service_name": "SCUMServer",
                },
                "api": {"host": "127.0.0.1", "port": 3000, "debug": False},
                "logging": {"level": "INFO", "format": "detailed"},
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"[OK] Arquivo config.json criado com configuracoes padrao")
            print(f"     Destino: {CONFIG_FILE}")
            print(f"     [IMPORTANTE] Ajuste os caminhos do servidor SCUM no arquivo!")
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao criar config.json: {e}")
            traceback.print_exc()
            return False

    return False


def create_webhooks_from_example():
    """Criar webhooks.json a partir do exemplo ou criar um básico"""
    # Tentar encontrar o arquivo de exemplo (pode estar no ROOT_DIR ou EXE_DIR)
    example_paths = [WEBHOOKS_EXAMPLE]
    if IS_EXE:
        # Também verificar no diretório do executável
        example_paths.append(EXE_DIR / "data" / "webhooks.example.json")
        # E no diretório temporário do PyInstaller
        example_paths.append(ROOT_DIR / "data" / "webhooks.example.json")

    # Tentar copiar do exemplo
    for example_path in example_paths:
        if example_path.exists() and not WEBHOOKS_FILE.exists():
            try:
                import shutil

                # Garantir que o diretório de destino existe
                WEBHOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(example_path, WEBHOOKS_FILE)
                print(f"[OK] Arquivo webhooks.json criado a partir do exemplo")
                print(f"     Origem: {example_path}")
                print(f"     Destino: {WEBHOOKS_FILE}")
                return True
            except Exception as e:
                print(f"[AVISO] Erro ao copiar exemplo: {e}")
                continue

    # Se não encontrou exemplo, criar um arquivo básico
    if not WEBHOOKS_FILE.exists():
        try:
            WEBHOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            default_webhooks = {
                "serverstatus": "",
                "new_player": "",
                "players_online": "",
                "vehicle_registration": "",
                "chat_in_game": "",
                "adminlog": "",
                "vehicle-log": "",
                "bunkers_status": "",
                "commands": "",

                "fishing_ranking": "",
                "kill_log": "",
                "chest_events": "",
                "chest_vehicle_alerts": "",
                "shop-log": "",
                "log-ssm": "",
                "lockpicking_events": "",
                "top10_lockpicking": "",
                "top10_kills": "",
            }
            with open(WEBHOOKS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_webhooks, f, indent=2, ensure_ascii=False)
            print(f"[OK] Arquivo webhooks.json criado com estrutura padrao")
            print(f"     Destino: {WEBHOOKS_FILE}")
            print(
                f"     [IMPORTANTE] Preencha as URLs dos webhooks do Discord no arquivo!"
            )
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao criar webhooks.json: {e}")
            traceback.print_exc()
            return False

    return False


def open_config_editor():
    """Abrir editor de configuração"""
    print(
        "[INFO] Config editor is disabled for security reasons. "
        "Configuration files are created automatically when missing."
    )
    return False


def start_backend():
    """Iniciar o backend principal"""
    try:
        if IS_EXE:
            # Quando executável, usar ssm_backend.exe
            backend_exe = EXE_DIR / "ssm_backend.exe"
            if backend_exe.exists():
                print("\n" + "=" * 60)
                print("Iniciando SSM Backend...")
                print("=" * 60 + "\n")

                # Iniciar o backend
                subprocess.run([str(backend_exe)], cwd=str(EXE_DIR))
            else:
                print(f"[ERRO] Executavel do backend nao encontrado em: {backend_exe}")
                return False
        else:
            # Quando script, usar main.py
            main_py = ROOT_DIR / "main.py"
            if main_py.exists():
                print("\n" + "=" * 60)
                print("Iniciando SSM Backend...")
                print("=" * 60 + "\n")

                # Iniciar o backend
                subprocess.run([sys.executable, str(main_py)], cwd=str(ROOT_DIR))
            else:
                print(f"[ERRO] Arquivo main.py nao encontrado em: {main_py}")
                return False
    except KeyboardInterrupt:
        print("\n\nBackend encerrado pelo usuario")
    except Exception as e:
        print(f"[ERRO] Erro ao iniciar backend: {e}")
        traceback.print_exc()
        return False


def wait_before_exit(message="Pressione Enter para fechar..."):
    """Aguardar antes de fechar para o usuário ver mensagens"""
    try:
        input(f"\n{message}")
    except (KeyboardInterrupt, EOFError):
        pass
    except:
        # Se input() falhar (ex: em ambiente sem console), aguardar 5 segundos
        time.sleep(5)


def show_directory_selector():
    """Mostrar interface gráfica para selecionar diretório de configuração"""
    if not HAS_TKINTER:
        print("[AVISO] tkinter nao disponivel, usando diretorio padrao")
        return None

    root = tk.Tk()
    root.title("SSM Backend - Selecionar Diretorio de Configuracao")
    root.geometry("600x400")
    root.resizable(False, False)

    # Centralizar janela
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (600 // 2)
    y = (root.winfo_screenheight() // 2) - (400 // 2)
    root.geometry(f"600x400+{x}+{y}")

    selected_dir = [None]  # Usar lista para poder modificar dentro da função

    def select_directory():
        """Abrir diálogo para selecionar diretório"""
        initial_dir = str(EXE_DIR) if IS_EXE else str(ROOT_DIR)
        dir_path = filedialog.askdirectory(
            title="Selecione o diretorio para salvar os arquivos de configuracao",
            initialdir=initial_dir,
        )
        if dir_path:
            selected_dir[0] = Path(dir_path)
            dir_label.config(text=f"Diretorio selecionado:\n{dir_path}")
            create_btn.config(state=tk.NORMAL)

    def create_files():
        """Criar arquivos de configuração no diretório selecionado"""
        if not selected_dir[0]:
            messagebox.showwarning(
                "Aviso", "Por favor, selecione um diretorio primeiro!"
            )
            return

        try:
            config_dir = selected_dir[0] / "data"
            config_dir.mkdir(parents=True, exist_ok=True)

            config_file = config_dir / "config.json"
            webhooks_file = config_dir / "webhooks.json"

            # Criar config.json
            if not config_file.exists():
                default_config = {
                    "paths": {
                        "application": {
                            "data_directory": "data",
                            "logs_directory": "data/logs",
                            "database": "data/SSM.db",
                            "config_file": "data/config.json",
                            "webhooks_file": "data/webhooks.json",
                        },
                        "scum_server": {
                            "root_directory": "C:\\Servers\\Scum",
                            "binaries_directory": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64",
                            "logs_directory": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs",
                            "config_directory": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer",
                            "database": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db",
                            "savefiles_directory": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles",
                        },
                    },
                    "server": {
                        "server_path": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64",
                        "steamcmd_path": "C:\\Servers\\steamcmd",
                        "install_path": "C:\\Servers\\Scum",
                        "port": 8900,
                        "max_players": 64,
                        "use_battleye": True,
                        "service_name": "SCUMServer",
                    },
                    "api": {"host": "127.0.0.1", "port": 3000, "debug": False},
                    "logging": {"level": "INFO", "format": "detailed"},
                }
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)

            # Criar webhooks.json
            if not webhooks_file.exists():
                default_webhooks = {
                    "serverstatus": "",
                    "new_player": "",
                    "players_online": "",
                    "vehicle_registration": "",
                    "chat_in_game": "",
                    "adminlog": "",
                    "vehicle-log": "",
                    "bunkers_status": "",
                    "commands": "",

                    "fishing_ranking": "",
                    "kill_log": "",
                    "chest_events": "",
                    "chest_vehicle_alerts": "",
                    "log-ssm": "",
                    "lockpicking_events": "",
                    "top10_lockpicking": "",
                    "top10_kills": "",
                }
                with open(webhooks_file, "w", encoding="utf-8") as f:
                    json.dump(default_webhooks, f, indent=2, ensure_ascii=False)

            messagebox.showinfo(
                "Sucesso",
                f"Arquivos criados com sucesso!\n\n"
                f"config.json: {config_file}\n"
                f"webhooks.json: {webhooks_file}\n\n"
                f"Por favor, edite os arquivos antes de continuar.",
            )

            # Atualizar CONFIG_DIR global para usar o diretório selecionado
            global CONFIG_DIR, CONFIG_FILE, WEBHOOKS_FILE
            CONFIG_DIR = config_dir
            CONFIG_FILE = config_file
            WEBHOOKS_FILE = webhooks_file

            root.destroy()
            return True

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao criar arquivos:\n{str(e)}")
            traceback.print_exc()
            return False

    def use_default():
        """Usar diretório padrão (ao lado do executável)"""
        selected_dir[0] = EXE_DIR if IS_EXE else ROOT_DIR
        dir_label.config(text=f"Diretorio padrao:\n{selected_dir[0] / 'data'}")
        create_btn.config(state=tk.NORMAL)

    def cancel():
        """Cancelar"""
        root.destroy()

    # Interface
    title_label = tk.Label(
        root,
        text="SSM Backend - Configuracao Inicial",
        font=("Arial", 16, "bold"),
        pady=20,
    )
    title_label.pack()

    info_label = tk.Label(
        root,
        text="Selecione o diretorio onde os arquivos de configuracao serao salvos:",
        font=("Arial", 10),
        pady=10,
    )
    info_label.pack()

    dir_label = tk.Label(
        root,
        text="Nenhum diretorio selecionado",
        font=("Arial", 9),
        fg="gray",
        pady=10,
        wraplength=550,
    )
    dir_label.pack()

    button_frame = tk.Frame(root, pady=20)
    button_frame.pack()

    select_btn = tk.Button(
        button_frame,
        text="Selecionar Diretorio",
        command=select_directory,
        width=20,
        height=2,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 10, "bold"),
    )
    select_btn.pack(side=tk.LEFT, padx=10)

    default_btn = tk.Button(
        button_frame,
        text="Usar Padrao",
        command=use_default,
        width=20,
        height=2,
        bg="#2196F3",
        fg="white",
        font=("Arial", 10, "bold"),
    )
    default_btn.pack(side=tk.LEFT, padx=10)

    create_btn = tk.Button(
        root,
        text="Criar Arquivos de Configuracao",
        command=create_files,
        width=30,
        height=2,
        bg="#FF9800",
        fg="white",
        font=("Arial", 11, "bold"),
        state=tk.DISABLED,
    )
    create_btn.pack(pady=20)

    cancel_btn = tk.Button(
        root,
        text="Cancelar",
        command=cancel,
        width=20,
        height=1,
        bg="#f44336",
        fg="white",
        font=("Arial", 9),
    )
    cancel_btn.pack(pady=10)

    # Mostrar diretório padrão inicialmente
    use_default()

    root.mainloop()

    return selected_dir[0]


def safe_print(text):
    """Imprimir texto de forma segura, removendo caracteres não suportados"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Remover emojis e caracteres especiais se não suportados
        safe_text = text.encode("ascii", "ignore").decode("ascii")
        print(safe_text)


def start_gui():
    """Abrir GUI do backend"""
    try:
        if IS_EXE:
            # Quando executável, usar ssm_backend.exe com flag --gui
            backend_exe = EXE_DIR / "ssm_backend.exe"
            if backend_exe.exists():
                # Iniciar o backend em modo GUI
                subprocess.Popen([str(backend_exe), "--gui"], cwd=str(EXE_DIR))
                return True
            else:
                print(f"[ERRO] Executavel do backend nao encontrado em: {backend_exe}")
                return False
        else:
            # Quando script, usar main.py com flag --gui
            main_py = ROOT_DIR / "main.py"
            if main_py.exists():
                # Iniciar o backend em modo GUI
                subprocess.Popen(
                    [sys.executable, str(main_py), "--gui"], cwd=str(ROOT_DIR)
                )
                return True
            else:
                print(f"[ERRO] Arquivo main.py nao encontrado em: {main_py}")
                return False
    except Exception as e:
        print(f"[ERRO] Erro ao abrir GUI: {e}")
        traceback.print_exc()
        return False


def main():
    """Função principal do launcher - apenas abre a GUI"""
    try:
        # Configurar encoding do console para UTF-8 se possível
        if sys.platform == "win32":
            try:
                import codecs

                sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
                sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")
            except:
                pass  # Se falhar, continua sem UTF-8

        # Abrir GUI diretamente (sem validações)
        start_gui()

    except Exception as e:
        print("\n" + "=" * 60)
        print("ERRO FATAL")
        print("=" * 60)
        print(f"\nErro: {e}")
        print("\nDetalhes do erro:")
        traceback.print_exc()
        try:
            input("\nPressione Enter para fechar...")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
