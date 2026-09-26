"""
Janela principal da GUI Desktop para SSM Backend
"""

import customtkinter as ctk  # type: ignore[reportMissingImports]
import pyperclip  # type: ignore[reportMissingImports]
import webbrowser
import os
import sys
import subprocess
import socket
import signal
import time
import json
import threading
import logging
import shutil
import re
import ctypes
from ctypes import wintypes
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from datetime import datetime
from PIL import Image  # type: ignore[reportMissingImports]

from utils.app_data_dir import (
    get_legacy_appdata_dir,
    get_runtime_data_dir,
    migrate_legacy_data_dir,
)

try:
    import requests  # type: ignore[reportMissingImports]

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import psutil  # type: ignore[reportMissingImports]

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from core.server_control.server_manager import ServerManager
from core.licensing.hardware_fingerprint import HardwareFingerprint
from core.scheduler.restart_scheduler import RestartScheduler
from utils.logger import StructuredLogger
from gui.icon_helper import IconHelper
from gui.system_tray_manager import SystemTrayManager

# URLs padrão (serão sobrescritas se main.py estiver disponível)
# As URLs serão buscadas dinamicamente no método _get_license_server_url()


class TextRedirector:
    """Classe para redirecionar stdout/stderr para o GUI"""

    def __init__(self, gui_window, stream_type="stdout"):
        """
        Args:
            gui_window: Instância da MainWindow
            stream_type: "stdout" ou "stderr"
        """
        self.gui_window = gui_window
        self.stream_type = stream_type
        self.buffer = ""
        self.last_flush = time.time()
        self._schedule_flush()

    def _schedule_flush(self):
        """Agendar flush periódico"""
        try:
            if hasattr(self.gui_window, "after"):
                self.gui_window.after(1000, self._check_flush)
        except:
            pass

    def _check_flush(self):
        """Verificar se precisa fazer flush"""
        try:
            if time.time() - self.last_flush > 1.0 and self.buffer:
                self.flush()
            self._schedule_flush()
        except:
            pass

    def write(self, text):
        """Escrever texto no buffer e adicionar ao GUI quando houver quebra de linha"""
        if not text:
            return

        self.buffer += text
        self.last_flush = time.time()

        # Processar linhas completas
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            if line:  # Ignorar linhas vazias
                # Determinar nível baseado no stream e conteúdo
                level = "ERROR" if self.stream_type == "stderr" else "INFO"

                # Detectar níveis de log comuns
                line_lower = line.lower()
                if (
                    "error" in line_lower
                    or "✗" in line
                    or "❌" in line
                    or "erro" in line_lower
                ):
                    level = "ERROR"
                elif "warning" in line_lower or "⚠" in line or "aviso" in line_lower:
                    level = "WARNING"
                elif (
                    "success" in line_lower
                    or "✓" in line
                    or "✅" in line
                    or ("ok" in line_lower and "arquivo" not in line_lower)
                ):
                    level = "SUCCESS"

                # Adicionar ao GUI de forma thread-safe
                if hasattr(self.gui_window, "_add_log_message"):
                    # Usar função com valores capturados para evitar problemas de closure
                    def add_log(msg=line, lvl=level):
                        try:
                            self.gui_window._add_log_message(msg, lvl)
                        except:
                            pass

                    self.gui_window.after(0, add_log)

    def flush(self):
        """Flush do buffer (requerido para compatibilidade)"""
        if self.buffer.strip():
            level = "ERROR" if self.stream_type == "stderr" else "INFO"
            line = self.buffer.strip()
            if hasattr(self.gui_window, "_add_log_message"):

                def add_log(msg=line, lvl=level):
                    try:
                        self.gui_window._add_log_message(msg, lvl)
                    except:
                        pass

                self.gui_window.after(0, add_log)
            self.buffer = ""

    def isatty(self):
        """Retornar False para indicar que não é um TTY (requerido por algumas bibliotecas)"""
        return False


class MainWindow(ctk.CTk):
    """Janela principal da aplicação"""

    def __init__(
        self,
        server_manager: Optional[ServerManager] = None,
        hardware_fingerprint: Optional[HardwareFingerprint] = None,
        logger: Optional[StructuredLogger] = None,
        config: Optional[Dict] = None,
        restart_scheduler: Optional[RestartScheduler] = None,
    ):
        super().__init__()

        self.server_manager = server_manager
        self.hardware_fingerprint = hardware_fingerprint
        self.logger = logger
        self.config = config
        self.restart_scheduler = restart_scheduler

        # Gerenciamento do backend (agora em thread, não subprocess)
        self.backend_thread = None
        self.backend_running = False
        self.flask_server = None  # Referência ao servidor Flask para shutdown
        self._backend_lock = None  # Lock de single instance do backend

        # Flag para prevenir múltiplos cliques no Stop enquanto o shutdown está em andamento
        self.backend_stopping = False

        # Flag para controlar validação em andamento
        self.validation_in_progress = False

        # Lock para garantir que apenas uma thread inicie o backend
        self._backend_start_lock = threading.Lock()

        # Cache para countdown de restart (evitar requisições excessivas)
        self.cached_next_restart = None
        self.last_api_check_time = None
        self.cache_ttl_seconds = 180  # 3 minutos (restarts são 10+ minutos)

        # Detectar se está rodando como executável
        if getattr(sys, "frozen", False):
            self.ROOT_DIR = Path(sys._MEIPASS)
            self.EXE_DIR = Path(sys.executable).parent
            self.IS_EXE = True
        else:
            self.ROOT_DIR = Path(__file__).parent.parent
            self.EXE_DIR = self.ROOT_DIR
            self.IS_EXE = False

        self.DATA_DIR = get_runtime_data_dir(
            is_exe=self.IS_EXE, exe_dir=self.EXE_DIR, project_root=self.ROOT_DIR
        )
        if self.IS_EXE:
            legacy_appdata = get_legacy_appdata_dir()
            migrate_legacy_data_dir(legacy_appdata, self.DATA_DIR)

        try:
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        if self.IS_EXE:
            try:
                test_path = self.DATA_DIR / ".write_test"
                test_path.write_text("ok", encoding="utf-8")
                try:
                    test_path.unlink()
                except Exception:
                    pass
            except Exception:
                try:
                    import tkinter.messagebox as messagebox

                    messagebox.showerror(
                        "SSM Backend",
                        "The data folder is not writable.\n\n"
                        f"Path: {str(self.DATA_DIR)}\n\n"
                        "Run Panel SSM as Administrator or move it to a writable folder.",
                    )
                except Exception:
                    pass
                raise

        try:
            legacy = self.EXE_DIR / "config_editor.exe"
            if legacy.exists() and legacy.is_file():
                try:
                    legacy.unlink()
                    if self.logger:
                        self.logger.info("Legacy file removed", {"file": str(legacy)})
                except Exception:
                    try:
                        disabled = self.EXE_DIR / "config_editor.exe.disabled"
                        try:
                            if disabled.exists():
                                disabled.unlink()
                        except Exception:
                            pass
                        legacy.rename(disabled)
                        if self.logger:
                            self.logger.warn(
                                "Legacy file disabled",
                                {"from": str(legacy), "to": str(disabled)},
                            )
                    except Exception:
                        pass
        except Exception:
            pass

        # Importar versão
        from version import VERSION

        # Configurar janela (fazer primeiro para aparecer rapidamente)
        self.title(f"SSM Backend v{VERSION} - Status and Licensing")

        try:
            self._set_window_icon()
        except Exception:
            pass

        # Definir tamanho da janela
        window_width = 900
        window_height = 800

        # Centralizar janela no monitor principal
        # Atualizar para obter dimensões corretas da tela
        self.update_idletasks()

        # Obter dimensões do monitor principal
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calcular posição central
        center_x = int((screen_width - window_width) / 2)
        center_y = int((screen_height - window_height) / 2)

        # Aplicar geometria com posição centralizada
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.resizable(True, True)
        try:
            self.minsize(900, 700)
        except Exception:
            pass

        # Janela de configurações (será criada quando necessário)
        self.settings_window = None

        # Tema (configurar antes de criar widgets)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Variáveis
        self.status_running = False
        self._closing = False
        self._cleanup_ui_notified = False
        self.hash_value = ""
        self.license_validated = False  # Flag para indicar se licença foi validada
        self.logs_max_lines = 100  # Máximo de linhas nos logs
        self.apikey_visible = False  # Flag para visibilidade da API key
        self.apikey_edit_mode = True  # Flag para modo de edição da API key (inicia editável se não houver key salva)
        self.apikey_dirty = False
        self.is_loading = False  # Flag para indicar se está carregando dados
        self.license_alert_label = (
            None  # Label de alerta de licença bloqueada/ inválida
        )
        self.license_alert_visible = False  # Flag persistente de alerta visível
        self.license_alert_text = None  # Último texto de alerta

        self.license_expires_at = None
        self.license_days_remaining = None
        self.license_status_text = None

        self._is_resizing = False
        self._resize_debounce_job = None
        self._log_buffer = []
        self._scum_log_buffer = []
        self._log_flush_job = None
        self._scum_log_flush_job = None

        self._discord_scrollable_frame = None
        self._discord_resize_placeholder = None
        self._discord_resize_placeholder_parent = None
        self._discord_frozen = False

        self._winapi_resize_hook_active = False
        self._winapi_hwnd = None
        self._winapi_old_wndproc = None
        self._winapi_wndproc = None

        try:
            self.bind("<Configure>", self._on_window_configure)
        except Exception:
            pass

        self.scum_log_file_pos = 0
        self.scum_log_file_path = None
        self.scum_log_tail_job = None
        self.logs_current_page = "application"

        # System Tray
        self.minimize_to_tray = (
            self._load_tray_preference()
        )  # Carregar preferência do config
        self.system_tray_manager: Optional[SystemTrayManager] = None
        self.is_minimized_to_tray = False

        # Registrar handler para fechamento da janela
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 1. Exibir Tela de Preparação imediatamente dentro da janela principal (< 50ms)
        self._show_startup_overlay()

        # Mostrar janela imediatamente
        self.update()
        self.deiconify()

        # 2. Construir o painel principal de forma assíncrona enquanto o usuário vê a preparação
        self.after(30, self._async_init_main_dashboard)

    def _show_startup_overlay(self):
        """Exibe a tela de preparação integrada na janela principal com alta performance"""
        self.startup_frame = ctk.CTkFrame(self, fg_color="#121212", corner_radius=0)
        self.startup_frame.pack(fill="both", expand=True)

        center_box = ctk.CTkFrame(self.startup_frame, fg_color="transparent")
        center_box.place(relx=0.5, rely=0.5, anchor="center")

        # Logo Oficial do SSM
        logo_path = self._get_logo_path()
        if logo_path:
            try:
                logo_img = Image.open(logo_path)
                logo_size = 64
                logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(logo_size, logo_size))
                lbl_logo = ctk.CTkLabel(center_box, image=logo_ctk, text="", fg_color="transparent")
                lbl_logo.pack(pady=(0, 14))
            except Exception:
                pass

        from version import VERSION

        lbl_title = ctk.CTkLabel(
            center_box,
            text="SCUM SERVER MANAGER",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff",
        )
        lbl_title.pack(pady=(0, 3))

        lbl_sub = ctk.CTkLabel(
            center_box,
            text=f"SSM Backend Control Panel • v{VERSION}",
            font=ctk.CTkFont(size=12),
            text_color="#888888",
        )
        lbl_sub.pack(pady=(0, 22))

        self.startup_progress = ctk.CTkProgressBar(
            center_box,
            width=360,
            height=6,
            corner_radius=3,
            fg_color="#222222",
            progress_color="#1f538d",
        )
        self.startup_progress.pack(pady=(0, 10))
        self.startup_progress.set(0.2)

        self.startup_status = ctk.CTkLabel(
            center_box,
            text="Inicializando SSM Backend...",
            font=ctk.CTkFont(size=11),
            text_color="#aaaaaa",
        )
        self.startup_status.pack()

    def _async_init_main_dashboard(self):
        """Constrói os componentes da interface e faz a transição da tela de preparação"""
        try:
            if hasattr(self, "startup_status") and self.startup_status:
                self.startup_status.configure(
                    text="Construindo interface e carregando módulos..."
                )
                self.startup_progress.set(0.65)
                self.update()

            # Container principal para os widgets do dashboard
            self.main_container = ctk.CTkFrame(
                self, fg_color="transparent", corner_radius=0
            )

            # Criar os widgets no container
            self._create_widgets()

            if hasattr(self, "startup_status") and self.startup_status:
                self.startup_status.configure(text="Pronto!")
                self.startup_progress.set(1.0)
                self.update()
                # Transição suave
                self.after(350, self._reveal_main_dashboard)
            else:
                self._reveal_main_dashboard()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao inicializar dashboard: {e}")
            self._reveal_main_dashboard()

    def _reveal_main_dashboard(self):
        """Remove o overlay de inicialização e exibe o dashboard principal"""
        if hasattr(self, "startup_frame") and self.startup_frame:
            try:
                self.startup_frame.pack_forget()
                self.startup_frame.destroy()
            except Exception:
                pass
            self.startup_frame = None

        if hasattr(self, "main_container") and self.main_container:
            self.main_container.pack(fill="both", expand=True)

        # Inicializar System Tray (se disponível e habilitado)
        if self.minimize_to_tray and SystemTrayManager.is_available():
            self.after(500, self._init_system_tray)

        # Hook WinAPI para detectar início/fim de resize/move (máxima suavidade no Windows)
        self.after(20, self._install_winapi_resize_hook)

        # Configurar ícone da janela (adiar para não bloquear)
        self.after(50, self._set_window_icon)

        # Redirecionar stdout e stderr para o GUI (adiar)
        self.after(50, self._setup_console_redirect)

        # INTEGRAÇÃO DO LAUNCHER: Verificar config na inicialização
        self.after(100, self._check_config_on_startup)

        # Atualizar status inicial de forma assíncrona (com delay maior para não bloquear)
        self.after(200, self._initial_update_async)

        # Atualizar status periodicamente
        self.after(30000, self._periodic_update)
        # Atualizar countdown a cada segundo
        self.after(1000, self._update_restart_countdown_periodic)

    def _check_config_on_startup(self):
        """Verificar se config.json existe na inicialização (lógica do launcher integrada)"""
        try:
            # Determinar caminhos de config
            if self.IS_EXE:
                config_dir = self.DATA_DIR
            else:
                config_dir = self.ROOT_DIR / "data"

            config_file = config_dir / "config.json"
            webhooks_file = config_dir / "webhooks.json"

            def _merge_missing_keys(dst, src):
                try:
                    if not isinstance(dst, dict) or not isinstance(src, dict):
                        return 0
                    added = 0
                    for k, v in src.items():
                        if k not in dst:
                            dst[k] = v
                            added += 1
                            continue
                        if isinstance(dst.get(k), dict) and isinstance(v, dict):
                            added += _merge_missing_keys(dst[k], v)
                    return added
                except Exception:
                    return 0

            def _find_config_example_path() -> Optional[Path]:
                try:
                    if self.IS_EXE:
                        p1 = self.EXE_DIR / "data" / "config.example.json"
                        if p1.exists():
                            return p1
                        p2 = self.ROOT_DIR / "data" / "config.example.json"
                        if p2.exists():
                            return p2
                        return None
                    p = self.ROOT_DIR / "data" / "config.example.json"
                    return p if p.exists() else None
                except Exception:
                    return None

            # Auto-criar arquivos ausentes para evitar abrir/depender de config editors
            try:
                if not config_file.exists() or not webhooks_file.exists():
                    from tools.launcher import create_config_from_example, create_webhooks_from_example

                    if not config_file.exists():
                        create_config_from_example()
                    if not webhooks_file.exists():
                        create_webhooks_from_example()
            except Exception:
                pass

            # Verificar se config existe
            config_exists = config_file.exists()
            webhooks_exists = webhooks_file.exists()

            if not config_exists or not webhooks_exists:
                # Config não existe - mostrar tela de configuração inicial
                self._show_config_required_screen(
                    config_exists, webhooks_exists, config_dir
                )
            else:
                # Validar JSON
                try:
                    import json

                    with open(config_file, "r", encoding="utf-8") as f:
                        json.load(f)
                    if webhooks_exists:
                        with open(webhooks_file, "r", encoding="utf-8") as f:
                            json.load(f)

                    try:
                        example_path = _find_config_example_path()
                        if example_path and example_path.exists():
                            with open(config_file, "r", encoding="utf-8") as f:
                                cfg = json.load(f) or {}
                            with open(example_path, "r", encoding="utf-8") as f:
                                tpl = json.load(f) or {}

                            added = _merge_missing_keys(cfg, tpl)
                            if int(added or 0) > 0:
                                with open(config_file, "w", encoding="utf-8") as f:
                                    json.dump(cfg, f, indent=2, ensure_ascii=False)
                                try:
                                    self._add_log_message(
                                        f"Config updated with missing keys: {int(added)}",
                                        "SUCCESS",
                                    )
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    # Config válido - continuar normalmente
                except json.JSONDecodeError as e:
                    # JSON inválido - mostrar erro (não abrir/servir editor)
                    self._show_config_error_screen(str(e))
                except Exception as e:
                    # Outro erro - mostrar erro
                    self._show_config_error_screen(str(e))
        except Exception as e:
            # Erro ao verificar config - logar mas continuar
            if self.logger:
                self.logger.warning(f"Failed to check config on startup: {e}")

    def _show_config_required_screen(
        self, config_exists: bool, webhooks_exists: bool, config_dir: Path
    ):
        """Mostrar tela quando config não existe"""
        # Criar frame de configuração inicial
        config_frame = ctk.CTkFrame(self)
        config_frame.place(relx=0.5, rely=0.5, anchor="center")

        title = ctk.CTkLabel(
            config_frame,
            text="⚙️ Configuration Required",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(pady=20)

        message = ctk.CTkLabel(
            config_frame,
            text="Configuration files were not found.\n\n"
            "You must configure the system before using it.",
            font=ctk.CTkFont(size=14),
        )
        message.pack(pady=10)

        missing_files = []
        if not config_exists:
            missing_files.append("config.json")
        if not webhooks_exists:
            missing_files.append("webhooks.json")

        files_label = ctk.CTkLabel(
            config_frame,
            text=f"Missing files: {', '.join(missing_files)}",
            font=ctk.CTkFont(size=12),
            text_color="orange",
        )
        files_label.pack(pady=5)

        info_label = ctk.CTkLabel(
            config_frame,
            text="Configuration files were auto-created. Restart the SSM Panel.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        info_label.pack(pady=5)

    def _show_config_error_screen(self, error_msg: str):
        """Mostrar tela quando config tem erro"""
        self._add_log_message(f"Configuration file error: {error_msg}", "ERROR")
        self._add_log_message(
            "Fix the JSON files manually and restart the SSM Panel.", "INFO"
        )

    def _initial_update_async(self):
        """Atualização inicial assíncrona após criação dos widgets"""
        self.is_loading = True
        self._show_loading_indicator("Loading...")
        # self._add_log_message("Carregando informações...", "INFO")

        # Atualizar interface imediatamente
        self.update()

        # Executar operações pesadas em thread separada
        def load_data():
            try:
                # Carregar fingerprint (pode ser pesado) - executar na thread
                self.after(
                    0, lambda: self._show_loading_indicator("Generating fingerprint...")
                )
                # self.after(0, lambda: self._add_log_message("Carregando hardware fingerprint...", "INFO"))
                # Executar na thread (não bloqueia GUI)
                fingerprint_result = self._load_fingerprint_thread_safe()
                # Atualizar GUI na thread principal
                self.after(0, lambda: self._update_fingerprint_ui(fingerprint_result))

                # Carregar API key - executar na thread
                self.after(
                    0,
                    lambda: self._show_loading_indicator("Loading settings..."),
                )
                # self.after(0, lambda: self._add_log_message("Carregando configurações...", "INFO"))
                apikey_result = self._load_apikey_main_thread_safe()
                self.after(0, lambda: self._update_apikey_ui(apikey_result))

                # Atualizar status do backend - executar na thread
                self.after(
                    0, lambda: self._show_loading_indicator("Checking backend...")
                )
                # self.after(0, lambda: self._add_log_message("Verificando status do backend...", "INFO"))
                backend_status = self._is_backend_running()
                self.after(0, lambda: self._update_backend_status_ui(backend_status))

                # Atualizar countdown
                self.after(0, self._update_restart_countdown)

                # Finalizar carregamento
                self.after(0, self._finish_loading)

            except Exception as e:
                self.after(
                    0,
                    lambda: self._add_log_message(
                        f"Failed to load data: {e}", "ERROR"
                    ),
                )
                self.after(0, self._finish_loading)

        # Iniciar thread de carregamento
        loading_thread = threading.Thread(target=load_data, daemon=True)
        loading_thread.start()

    def _show_loading_indicator(self, message: str):
        """Mostrar indicador de carregamento"""
        if hasattr(self, "loading_indicator"):
            self.loading_indicator.configure(text=f"⏳ {message}")
            self.update_idletasks()

    def _finish_loading(self):
        """Finalizar processo de carregamento"""
        self.is_loading = False
        if hasattr(self, "loading_indicator"):
            self.loading_indicator.configure(text="")
        self._add_log_message(
            "✅ Loading complete. Waiting for command to start backend...",
            "SUCCESS",
        )

    def _on_window_configure(self, event):
        # Se hook WinAPI estiver ativo, ele controla o início/fim do resize/move.
        # Manter <Configure> apenas como fallback.
        if getattr(self, "_winapi_resize_hook_active", False):
            return

        try:
            if event.widget is not self:
                return
        except Exception:
            return

        self._is_resizing = True

        try:
            self._freeze_discord_ui()
        except Exception:
            pass

        try:
            if self._resize_debounce_job is not None:
                self.after_cancel(self._resize_debounce_job)
        except Exception:
            pass

        try:
            self._resize_debounce_job = self.after(200, self._on_resize_end)
        except Exception:
            self._resize_debounce_job = None

    def _on_resize_end(self):
        self._resize_debounce_job = None
        self._is_resizing = False

        try:
            self._unfreeze_discord_ui()
        except Exception:
            pass

        try:
            self._flush_log_buffer()
        except Exception:
            pass
        try:
            self._flush_scum_log_buffer()
        except Exception:
            pass

    def _install_winapi_resize_hook(self):
        try:
            if sys.platform != "win32":
                return

            # Evitar reinstalar
            if getattr(self, "_winapi_resize_hook_active", False):
                return

            try:
                hwnd = wintypes.HWND(int(self.winfo_id()))
            except Exception:
                return

            WM_ENTERSIZEMOVE = 0x0231
            WM_EXITSIZEMOVE = 0x0232
            GWL_WNDPROC = -4

            WNDPROC = ctypes.WINFUNCTYPE(
                wintypes.LRESULT,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            )

            user32 = ctypes.windll.user32

            # SetWindowLongPtrW para 64-bit; fallback para SetWindowLongW em 32-bit
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                _SetWindowLongPtr = user32.SetWindowLongPtrW
                _GetWindowLongPtr = user32.GetWindowLongPtrW
            else:
                _SetWindowLongPtr = user32.SetWindowLongW
                _GetWindowLongPtr = user32.GetWindowLongW

            _SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LPARAM]
            _SetWindowLongPtr.restype = wintypes.LPARAM
            _GetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int]
            _GetWindowLongPtr.restype = wintypes.LPARAM

            old_wndproc = _GetWindowLongPtr(hwnd, GWL_WNDPROC)
            if not old_wndproc:
                return

            def _py_wndproc(hWnd, msg, wParam, lParam):
                try:
                    if msg == WM_ENTERSIZEMOVE:
                        self._is_resizing = True
                        try:
                            self._freeze_discord_ui()
                        except Exception:
                            pass
                        return 0

                    if msg == WM_EXITSIZEMOVE:
                        self._is_resizing = False
                        try:
                            self._unfreeze_discord_ui()
                        except Exception:
                            pass
                        try:
                            self._flush_log_buffer()
                        except Exception:
                            pass
                        try:
                            self._flush_scum_log_buffer()
                        except Exception:
                            pass
                        return 0
                except Exception:
                    pass

                try:
                    return user32.CallWindowProcW(old_wndproc, hWnd, msg, wParam, lParam)
                except Exception:
                    try:
                        return 0
                    except Exception:
                        return 0

            new_wndproc = WNDPROC(_py_wndproc)

            res = _SetWindowLongPtr(hwnd, GWL_WNDPROC, ctypes.cast(new_wndproc, wintypes.LPARAM))
            if not res:
                return

            self._winapi_resize_hook_active = True
            self._winapi_hwnd = hwnd
            self._winapi_old_wndproc = old_wndproc
            self._winapi_wndproc = new_wndproc  # manter referencia viva
        except Exception:
            pass

    def _remove_winapi_resize_hook(self):
        try:
            if not getattr(self, "_winapi_resize_hook_active", False):
                return
            if sys.platform != "win32":
                return
            hwnd = getattr(self, "_winapi_hwnd", None)
            old = getattr(self, "_winapi_old_wndproc", None)
            if not hwnd or not old:
                return

            user32 = ctypes.windll.user32
            GWL_WNDPROC = -4
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                _SetWindowLongPtr = user32.SetWindowLongPtrW
            else:
                _SetWindowLongPtr = user32.SetWindowLongW
            _SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LPARAM]
            _SetWindowLongPtr.restype = wintypes.LPARAM

            _SetWindowLongPtr(hwnd, GWL_WNDPROC, old)
        except Exception:
            pass
        finally:
            try:
                self._winapi_resize_hook_active = False
                self._winapi_hwnd = None
                self._winapi_old_wndproc = None
                self._winapi_wndproc = None
            except Exception:
                pass

    def _freeze_discord_ui(self):
        try:
            if self._discord_frozen:
                return

            sf = getattr(self, "_discord_scrollable_frame", None)
            if sf is None:
                return

            # Apenas congelar se o Discord estiver visivel (evitar mexer em tabs ocultas)
            if getattr(self, "settings_current_page", None) != "discord":
                return
            if getattr(self, "discord_current_page", None) != "webhooks":
                return

            parent = getattr(self, "_discord_resize_placeholder_parent", None)
            if parent is None:
                return

            if self._discord_resize_placeholder is None:
                ph = ctk.CTkFrame(parent, fg_color=("gray90", "gray20"), corner_radius=12)
                lbl = ctk.CTkLabel(ph, text="Resizing...", font=ctk.CTkFont(size=13, weight="bold"))
                lbl.pack(padx=20, pady=20)
                self._discord_resize_placeholder = ph

            try:
                sf.pack_forget()
            except Exception:
                pass

            try:
                self._discord_resize_placeholder.pack(fill="both", expand=True, padx=0, pady=0)
            except Exception:
                pass

            self._discord_frozen = True
        except Exception:
            pass

    def _unfreeze_discord_ui(self):
        try:
            if not self._discord_frozen:
                return

            sf = getattr(self, "_discord_scrollable_frame", None)
            if sf is None:
                self._discord_frozen = False
                return

            try:
                if self._discord_resize_placeholder is not None:
                    self._discord_resize_placeholder.pack_forget()
            except Exception:
                pass

            # Restaurar apenas se o Discord estiver visivel
            if getattr(self, "settings_current_page", None) == "discord" and getattr(self, "discord_current_page", None) == "webhooks":
                try:
                    sf.pack(fill="both", expand=True, padx=0, pady=0)
                except Exception:
                    pass

            self._discord_frozen = False
        except Exception:
            self._discord_frozen = False

    def _flush_log_buffer(self):
        try:
            if getattr(self, "_is_resizing", False):
                try:
                    if self._log_flush_job is None:
                        self._log_flush_job = self.after(250, self._flush_log_buffer)
                except Exception:
                    pass
                return

            if not self._log_buffer:
                try:
                    self._log_flush_job = None
                except Exception:
                    pass
                return
            if not hasattr(self, "logs_textbox") or not self.logs_textbox:
                self._log_buffer.clear()
                try:
                    self._log_flush_job = None
                except Exception:
                    pass
                return

            self.logs_textbox.configure(state="normal")
            self.logs_textbox.insert("end", "".join(self._log_buffer))
            self._log_buffer.clear()

            lines = self.logs_textbox.get("1.0", "end-1c").split("\n")
            if len(lines) > self.logs_max_lines:
                excess = len(lines) - self.logs_max_lines
                self.logs_textbox.delete("1.0", f"{excess + 1}.0")

            self.logs_textbox.see("end")
            self.logs_textbox.configure(state="disabled")
            try:
                self._log_flush_job = None
            except Exception:
                pass
        except Exception:
            try:
                self._log_buffer.clear()
            except Exception:
                pass
            try:
                self._log_flush_job = None
            except Exception:
                pass

    def _flush_scum_log_buffer(self):
        try:
            if getattr(self, "_is_resizing", False):
                try:
                    if self._scum_log_flush_job is None:
                        self._scum_log_flush_job = self.after(
                            250, self._flush_scum_log_buffer
                        )
                except Exception:
                    pass
                return

            if not self._scum_log_buffer:
                try:
                    self._scum_log_flush_job = None
                except Exception:
                    pass
                return
            tb = getattr(self, "scum_logs_textbox", None)
            if not tb:
                self._scum_log_buffer.clear()
                try:
                    self._scum_log_flush_job = None
                except Exception:
                    pass
                return
            tb.configure(state="normal")
            tb.insert("end", "".join(self._scum_log_buffer))
            self._scum_log_buffer.clear()
            tb.see("end")
            tb.configure(state="disabled")
            try:
                self._scum_log_flush_job = None
            except Exception:
                pass
        except Exception:
            try:
                self._scum_log_buffer.clear()
            except Exception:
                pass
            try:
                self._scum_log_flush_job = None
            except Exception:
                pass

    def _load_fingerprint_thread_safe(self):
        """Carregar fingerprint de forma thread-safe (executar na thread de background)"""
        try:
            if not self.hardware_fingerprint:
                self.hardware_fingerprint = HardwareFingerprint(logger=self.logger)
            hash_value, components = self.hardware_fingerprint.generate()
            return hash_value
        except Exception as e:
            return f"Error: {str(e)[:50]}"

    def _update_fingerprint_ui(self, hash_value: str):
        """Atualizar UI do fingerprint na thread principal"""
        self.hash_value = hash_value
        if hasattr(self, "hash_entry"):
            self.hash_entry.configure(state="normal")
            self.hash_entry.delete(0, "end")
            self.hash_entry.insert(0, hash_value)
            self.hash_entry.configure(state="readonly")

    def _load_apikey_main_thread_safe(self):
        """Carregar API key de forma thread-safe"""
        try:
            config = self._load_config()
            if not config:
                return None
            licensing_config = config.get("licensing", {})
            apikey = licensing_config.get("gestao_api_key", "")
            if apikey and apikey.startswith("ENCRYPTED:"):
                from core.security.credential_encryption import decrypt_credential

                apikey = decrypt_credential(apikey, logger=self.logger)
            return apikey
        except Exception as e:
            return None

    def _update_apikey_ui(self, apikey: str):
        """Atualizar UI da API key na thread principal"""
        if apikey and hasattr(self, "main_apikey_entry"):
            self.main_apikey_entry.delete(0, "end")
            self.main_apikey_entry.insert(0, apikey)
            self.main_apikey_entry.configure(show="*")
            self.apikey_visible = False
            if hasattr(self, "btn_toggle_apikey_main"):
                eye_icon = IconHelper.load_icon(
                    "ver", self.ROOT_DIR, self.EXE_DIR, self.IS_EXE, size=18
                )
                self.btn_toggle_apikey_main.configure(image=eye_icon, text="")
            self.apikey_dirty = False
            self._set_apikey_status_main("", status="idle")
            try:
                self.main_apikey_entry.configure(state="normal")
            except Exception:
                pass
        elif not apikey:
            self.apikey_dirty = False
            self._set_apikey_status_main("", status="idle")
            try:
                self.main_apikey_entry.configure(state="normal")
            except Exception:
                pass

    def _show_start_only(self):
        try:
            self.btn_stop_backend.pack_forget()
        except Exception:
            pass

        # Se SCUM Server não estiver instalado ou se a instalação estiver em andamento, não mostrar Start
        if getattr(self, "_steam_install_in_progress", False) or not self._is_scum_installed():
            try:
                self.btn_start_backend.pack_forget()
            except Exception:
                pass
            return

        try:
            self.btn_start_backend.pack_forget()
        except Exception:
            pass

        try:
            self.btn_start_backend.pack(side="left", padx=5)
        except Exception:
            pass

    def _show_stop_only(self):
        try:
            self.btn_start_backend.pack_forget()
        except Exception:
            pass

        try:
            self.btn_stop_backend.pack_forget()
        except Exception:
            pass

        try:
            self.btn_stop_backend.pack(side="left", padx=5)
        except Exception:
            pass

    def _update_backend_status_ui(self, is_running: bool):
        """Atualizar UI do status do backend na thread principal"""
        self.backend_running = is_running

        if getattr(self, "backend_stopping", False):
            try:
                self.backend_status_indicator.configure(text_color="orange")
                self.backend_status_text.configure(text="Stopping")
                self.btn_start_backend.configure(state="disabled", fg_color="gray")
                self.btn_stop_backend.configure(state="normal", text="Stopping...", fg_color="#dc3545")
                self._show_stop_only()
            except Exception:
                pass
            return

        if is_running:
            self.backend_status_indicator.configure(text_color="green")
            self.backend_status_text.configure(text="Running")
            self.btn_start_backend.configure(state="disabled", fg_color="gray")
            self.btn_stop_backend.configure(state="normal", fg_color="red")
            self._show_stop_only()
        else:
            self.backend_status_indicator.configure(text_color="red")
            self.backend_status_text.configure(text="Stopped")
            if not self.license_validated:
                current_text = self.btn_start_backend.cget("text")
                if current_text != "Blocked":
                    self.btn_start_backend.configure(state="normal", fg_color="green")
            else:
                self.btn_start_backend.configure(state="normal", fg_color="green")
                self.license_validated = False
            self.btn_stop_backend.configure(state="disabled", fg_color="gray", text="Stop")
            self._show_start_only()

        try:
            self._update_tray_icon()
        except Exception:
            pass

    def _initial_update(self):
        """Atualização inicial após criação dos widgets (método antigo - mantido para compatibilidade)"""
        self._initial_update_async()

    def _set_window_icon(self):
        """Configurar ícone da janela"""
        try:
            # Tentar encontrar o ícone ICO (prioridade para arquivos .ico)
            base_dir = self.EXE_DIR if self.IS_EXE else self.ROOT_DIR

            # Primeiro, tentar arquivos .ico (preferência por 32x32, depois 256x256, depois outros)
            ico_paths = [
                base_dir / "data" / "imagens" / "LogoSSM" / "W-SSM-Ico.ico",
            ]

            # Tentar arquivos .ico primeiro
            for ico_path in ico_paths:
                if ico_path.exists():
                    try:
                        # Método 1: iconbitmap (para ícone da janela)
                        try:
                            self.iconbitmap(str(ico_path))
                        except Exception:
                            pass

                        # Método 2: iconphoto (para barra de tarefas - mais confiável no Windows)
                        # Carregar ICO como imagem PIL e converter para PhotoImage
                        icon_ico = Image.open(ico_path)
                        best_frame = None
                        best_area = -1
                        frame_count = getattr(icon_ico, "n_frames", 1)
                        for i in range(frame_count):
                            try:
                                icon_ico.seek(i)
                                w, h = icon_ico.size
                                area = w * h
                                if area > best_area:
                                    best_area = area
                                    best_frame = icon_ico.copy()
                            except Exception:
                                continue

                        if best_frame is None:
                            raise RuntimeError("Falha ao ler frames do ícone")

                        icon_image = best_frame.convert("RGBA")
                        if icon_image.size != (256, 256):
                            icon_image = icon_image.resize((256, 256), Image.Resampling.LANCZOS)

                        # Converter para PhotoImage do Tkinter
                        from tkinter import PhotoImage
                        import io

                        # Salvar em buffer como PNG
                        img_buffer = io.BytesIO()
                        icon_image.save(img_buffer, format="PNG")
                        img_buffer.seek(0)

                        # Criar PhotoImage e aplicar
                        photo = PhotoImage(data=img_buffer.read())
                        self.iconphoto(False, photo)

                        # Manter referência para evitar garbage collection
                        self._icon_photo = photo
                        break
                    except Exception:
                        continue
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to load window icon: {e}")

    def _get_logo_path(self) -> Optional[Path]:
        """Obter caminho da logo"""
        try:
            # Usar ROOT_DIR ou EXE_DIR conforme o caso
            base_dir = self.ROOT_DIR if not self.IS_EXE else self.EXE_DIR

            # Priorizar logo Grande.png com fundo
            logo_paths = [
                base_dir / "data" / "imagens" / "LogoSSM" / "Grande.png",
                base_dir / "data" / "imagens" / "logossm" / "Logo_SSM.png",
                base_dir / "data" / "imagens" / "logossm" / "Logo.png",
                base_dir / "data" / "imagens" / "LogoSSM" / "Logo_SSM.png",
                base_dir / "data" / "imagens" / "LogoSSM" / "Logo.png",
            ]

            for logo_path in logo_paths:
                if logo_path.exists():
                    return logo_path
            return None
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to find logo: {e}")
            return None

    def _create_tooltip(self, widget, text: str):
        """Criar tooltip para um widget"""

        def show_tooltip(event):
            # Se já existe tooltip, não criar outro
            if hasattr(widget, "_tooltip_label") and widget._tooltip_label:
                return

            # Criar label do tooltip
            tooltip_label = ctk.CTkLabel(
                self,
                text=text,
                font=ctk.CTkFont(size=11),
                fg_color=("#2b2b2b", "#1a1a1a"),
                corner_radius=5,
                padx=8,
                pady=4,
            )
            widget._tooltip_label = tooltip_label

            # Atualizar layout para obter posições corretas
            self.update_idletasks()
            widget.update_idletasks()

            # Obter posição absoluta do widget na tela
            widget_x_root = widget.winfo_rootx()
            widget_y_root = widget.winfo_rooty()
            widget_width = widget.winfo_width()
            widget_height = widget.winfo_height()

            # Obter posição da janela principal na tela
            window_x_root = self.winfo_rootx()
            window_y_root = self.winfo_rooty()

            # Calcular posição relativa do widget em relação à janela
            widget_x = widget_x_root - window_x_root
            widget_y = widget_y_root - window_y_root

            # Posicionar tooltip ao lado direito do checkbox (com pequeno espaçamento)
            tooltip_x = widget_x + widget_width + 10
            tooltip_y = (
                widget_y + (widget_height // 2) - 10
            )  # Centralizado verticalmente

            # Verificar se o tooltip cabe na tela (se não, colocar à esquerda)
            tooltip_label.update_idletasks()
            tooltip_width = tooltip_label.winfo_reqwidth()
            window_width = self.winfo_width()

            if tooltip_x + tooltip_width > window_width:
                # Colocar à esquerda do checkbox
                tooltip_x = widget_x - tooltip_width - 10

            tooltip_label.place(x=tooltip_x, y=tooltip_y)
            tooltip_label.lift()  # Trazer para frente

        def hide_tooltip(event):
            if hasattr(widget, "_tooltip_label") and widget._tooltip_label:
                widget._tooltip_label.destroy()
                widget._tooltip_label = None

        # Vincular eventos de mouse
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def _set_license_alert(self, visible: bool, text: Optional[str] = None):
        """Exibir ou ocultar alerta visual de licença inválida/bloqueada na barra superior."""
        if not self.license_alert_label:
            return
        if visible:
            self.license_alert_visible = True
            self.license_alert_text = text or "⚠️ License invalid/blocked"
            self.license_alert_label.configure(text=self.license_alert_text)
            # Reposicionar caso estivesse oculto
            self.license_alert_label.pack(side="left", padx=(12, 0))
        else:
            self.license_alert_visible = False
            self.license_alert_text = None
            self.license_alert_label.pack_forget()

    def _set_license_status_value(self, value: str, text_color: Optional[str] = None):
        try:
            if hasattr(self, "license_status_value") and self.license_status_value:
                if text_color is not None:
                    self.license_status_value.configure(text=value, text_color=text_color)
                else:
                    self.license_status_value.configure(text=value)
        except Exception:
            pass

    def _update_license_status_label(self):
        try:
            self._set_license_status_value("Free", text_color="#00c853")
        except Exception:
            pass

    def _create_widgets(self):
        """Criar widgets da interface - Layout Híbrido (Top Bar + Tabs)"""
        parent = getattr(self, "main_container", self)

        # ========== TOP BAR ==========
        top_bar = ctk.CTkFrame(
            parent, height=60, fg_color=("#1a1a1a", "#0f0f0f"), corner_radius=0
        )
        top_bar.pack(side="top", fill="x")

        # Logo e título (esquerda)
        top_left = ctk.CTkFrame(top_bar, fg_color="transparent")
        top_left.pack(side="left", padx=10, pady=10)

        logo_path = self._get_logo_path()
        if logo_path:
            try:
                logo_image = Image.open(logo_path)
                max_height = 40
                if logo_image.height > max_height:
                    ratio = max_height / logo_image.height
                    new_width = int(logo_image.width * ratio)
                    logo_image = logo_image.resize(
                        (new_width, max_height), Image.Resampling.LANCZOS
                    )
                logo_ctk = ctk.CTkImage(
                    light_image=logo_image,
                    dark_image=logo_image,
                    size=(logo_image.width, logo_image.height),
                )
                logo_label = ctk.CTkLabel(
                    top_left, image=logo_ctk, text="", fg_color="transparent"
                )
                logo_label.pack(side="left", padx=(0, 10))
            except Exception as e:
                if self.logger:
                    self.logger.warn(f"Failed to load logo: {e}")

        from version import VERSION

        title_label = ctk.CTkLabel(
            top_left,
            text=f"SSM Backend v{VERSION}",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        title_label.pack(side="left")

        # Alerta de licença (exibido apenas quando inválida/bloqueada)
        self.license_alert_label = ctk.CTkLabel(
            top_left,
            text="⚠️ License invalid/blocked",
            text_color="#000000",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#fcbf49",  # âmbar
            corner_radius=8,
            padx=10,
            pady=4,
        )
        self.license_alert_label.pack(side="left", padx=(12, 0))
        self.license_alert_label.pack_forget()  # escondido por padrão

        # Se havia alerta persistente (caso a GUI seja recarregada), reexibir
        if self.license_alert_visible:
            self._set_license_alert(True, self.license_alert_text)

        # Controles rápidos (direita)
        top_right = ctk.CTkFrame(top_bar, fg_color="transparent")
        top_right.pack(side="right", padx=10, pady=10)

        # Botão Control Panel (ícone)
        icons_path = IconHelper.get_icons_path(self.ROOT_DIR, self.EXE_DIR, self.IS_EXE)
        panel_icon_path = icons_path / "painel-de-controle.png"
        frontend_icon = None
        if panel_icon_path.exists():
            try:
                frontend_icon = IconHelper.load_icon_from_file(panel_icon_path, size=20)
            except Exception as e:
                if self.logger:
                    self.logger.warn(f"Failed to load control panel icon: {e}")

        frontend_button = ctk.CTkButton(
            top_right,
            image=frontend_icon,
            text="",
            command=self._open_frontend,
            width=40,
            height=35,
            fg_color="transparent",
            hover_color=("#2b2b2b", "#2b2b2b"),
        )
        frontend_button.pack(side="left", padx=5)
        if frontend_icon:
            self._create_tooltip(frontend_button, "Control Panel")

        # Botão Discord Oficial do SSM (ícone)
        discord_icon_candidates = [
            self.DATA_DIR / "imagens" / "Discord-Logo" / "Symbol_RGB" / "Discord-Symbol-Blurple.png",
            self.ROOT_DIR / "data" / "imagens" / "Discord-Logo" / "Symbol_RGB" / "Discord-Symbol-Blurple.png",
            self.EXE_DIR / "data" / "imagens" / "Discord-Logo" / "Symbol_RGB" / "Discord-Symbol-Blurple.png",
            icons_path / "www.png",
        ]
        discord_icon = None
        for cand in discord_icon_candidates:
            if cand.exists():
                try:
                    discord_icon = IconHelper.load_icon_from_file(cand, size=20)
                    if discord_icon:
                        break
                except Exception as e:
                    if self.logger:
                        self.logger.warn(f"Failed to load discord icon from {cand}: {e}")

        discord_button = ctk.CTkButton(
            top_right,
            image=discord_icon,
            text="",
            command=self._open_discord_community,
            width=40,
            height=35,
            fg_color="transparent",
            hover_color=("#2b2b2b", "#2b2b2b"),
        )
        discord_button.pack(side="left", padx=5)
        if discord_icon:
            self._create_tooltip(discord_button, "SSM Discord Community")

        # Checkbox System Tray (se disponível)
        if SystemTrayManager.is_available():
            self.tray_checkbox = ctk.CTkCheckBox(
                top_right,
                text="",
                command=self._on_tray_checkbox_changed,
                width=20,
                height=20,
            )
            self.tray_checkbox.pack(side="left", padx=(10, 0))
            (
                self.tray_checkbox.select()
                if self.minimize_to_tray
                else self.tray_checkbox.deselect()
            )
            self._create_tooltip(self.tray_checkbox, "Minimize to notification area")
        else:
            self.tray_checkbox = None

        # ========== STATUS OVERVIEW (Sempre Visível) ==========
        status_overview = ctk.CTkFrame(parent, fg_color=("#2b2b2b", "#1a1a1a"))
        status_overview.pack(side="top", fill="x", padx=10, pady=(10, 5))

        # Status do Backend
        backend_status_frame = ctk.CTkFrame(status_overview, fg_color="transparent")
        backend_status_frame.pack(side="left", padx=15, pady=10)

        backend_status_label = ctk.CTkLabel(
            backend_status_frame, text="Backend:", font=ctk.CTkFont(size=13)
        )
        backend_status_label.pack(side="left", padx=(0, 5))

        self.backend_status_indicator = ctk.CTkLabel(
            backend_status_frame, text="●", font=ctk.CTkFont(size=18), text_color="gray"
        )
        self.backend_status_indicator.pack(side="left", padx=2)

        self.backend_status_text = ctk.CTkLabel(
            backend_status_frame, text="Checking...", font=ctk.CTkFont(size=13)
        )
        self.backend_status_text.pack(side="left", padx=5)

        # Status do Servidor
        server_status_frame = ctk.CTkFrame(status_overview, fg_color="transparent")
        server_status_frame.pack(side="left", padx=15, pady=10)

        server_status_label = ctk.CTkLabel(
            server_status_frame, text="Server:", font=ctk.CTkFont(size=13)
        )
        server_status_label.pack(side="left", padx=(0, 5))

        self.status_indicator = ctk.CTkLabel(
            server_status_frame, text="●", font=ctk.CTkFont(size=18), text_color="gray"
        )
        self.status_indicator.pack(side="left", padx=2)

        self.status_text = ctk.CTkLabel(
            server_status_frame, text="N/A", font=ctk.CTkFont(size=13)
        )
        self.status_text.pack(side="left", padx=5)

        # Next Restart
        restart_frame = ctk.CTkFrame(status_overview, fg_color="transparent")
        restart_frame.pack(side="left", padx=15, pady=10)

        restart_label = ctk.CTkLabel(
            restart_frame, text="Next Restart:", font=ctk.CTkFont(size=12)
        )
        restart_label.pack(side="left", padx=(0, 5))

        self.restart_countdown = ctk.CTkLabel(
            restart_frame, text="--", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.restart_countdown.pack(side="left")

        license_frame = ctk.CTkFrame(status_overview, fg_color="transparent")
        license_frame.pack(side="left", padx=15, pady=10)

        license_label = ctk.CTkLabel(
            license_frame, text="License:", font=ctk.CTkFont(size=12)
        )
        license_label.pack(side="left", padx=(0, 5))

        self.license_status_value = ctk.CTkLabel(
            license_frame, text="Free", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00c853"
        )
        self.license_status_value.pack(side="left")

        # Botões Start/Stop
        control_buttons_frame = ctk.CTkFrame(status_overview, fg_color="transparent")
        control_buttons_frame.pack(side="right", padx=15, pady=10)
        self.control_buttons_frame = control_buttons_frame

        self.btn_start_backend = ctk.CTkButton(
            control_buttons_frame,
            text="Start",
            command=self._start_backend,
            width=110,
            height=34,
            fg_color="green",
            hover_color="darkgreen",
        )
        self.btn_start_backend.pack(side="left", padx=5)

        self.btn_stop_backend = ctk.CTkButton(
            control_buttons_frame,
            text="Stop",
            command=self._stop_backend,
            width=110,
            height=34,
            fg_color="#dc3545",
            hover_color="#c82333",
            state="disabled",
        )
        self.btn_stop_backend.pack(side="left", padx=5)

        self.btn_install_default = ctk.CTkButton(
            control_buttons_frame,
            text="Install",
            command=lambda: self._install_or_update_scum_server(prompt_for_base_dir=True),
            width=120,
            height=40,
            fg_color="#FFA500",
            hover_color="#FF8C00",
        )
        self.btn_install_default.pack(side="left", padx=5)

        # ========== MAIN CONTENT ==========
        main_content = ctk.CTkFrame(parent, fg_color="transparent")
        main_content.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))

        # ========== TABS SYSTEM ==========
        # Barra de tabs
        tabs_bar = ctk.CTkFrame(main_content, fg_color="transparent")
        tabs_bar.pack(fill="x", pady=(0, 5))

        self.tab_buttons = {}
        self.tabs_content = {}
        self.current_tab = "logs"  # Tab padrão

        tabs_config = [
            ("Settings", "settings"),
            ("Logs", "logs"),
        ]

        for tab_name, tab_id in tabs_config:
            btn = ctk.CTkButton(
                tabs_bar,
                text=tab_name,
                command=lambda t=tab_id: self._switch_tab(t),
                width=120,
                height=35,
                state="normal",  # Garantir que sempre esteja habilitado
                fg_color=(
                    ("gray", "gray") if tab_id != "logs" else ("#1f538d", "#14375e")
                ),
                hover_color=(
                    ("#3b3b3b", "#2a2a2a")
                    if tab_id != "logs"
                    else ("#2a5a9a", "#1a4a7a")
                ),
                font=ctk.CTkFont(
                    size=12, weight="bold" if tab_id == "logs" else "normal"
                ),
            )
            btn.pack(side="left", padx=2)
            self.tab_buttons[tab_id] = btn

        # Container para conteúdo das tabs
        tabs_content_container = ctk.CTkFrame(main_content, fg_color="transparent")
        tabs_content_container.pack(fill="both", expand=True)

        # Criar conteúdo de cada tab
        self._create_settings_tab(tabs_content_container)
        self._create_logs_tab(tabs_content_container)

        # Mostrar tab padrão (Logs)
        self._switch_tab("logs")

        try:
            self.after(200, self._update_installation_ui)
        except Exception:
            pass

    def _is_scum_installed(self) -> bool:
        try:
            config = self._load_config() or {}
            scum_paths = config.get("paths", {}).get("scum_server", {})

            steamcmd_dir = scum_paths.get("steamcmd_path")
            root_dir = scum_paths.get("root_directory")

            scumserver_exe = ""
            if root_dir:
                scumserver_exe = os.path.join(
                    root_dir, "SCUM", "Binaries", "Win64", "SCUMServer.exe"
                )

            # Fallback comum: instalação padrão em C:\Servers
            default_scumserver_exe = os.path.join(
                "C:\\Servers", "SCUM", "Binaries", "Win64", "SCUMServer.exe"
            )

            # Para UI, considerar instalado se o binário do servidor existe.
            # SteamCMD pode não estar configurado (ou estar em outro local) mesmo com o servidor instalado.
            if scumserver_exe and os.path.exists(scumserver_exe):
                return True
            if os.path.exists(default_scumserver_exe):
                return True

            # Heurística extra (quando configurado): se SteamCMD está presente, também é um sinal.
            if steamcmd_dir:
                steamcmd_exe = os.path.join(steamcmd_dir, "steamcmd.exe")
                if os.path.exists(steamcmd_exe):
                    return True

            return False
        except Exception:
            return False

    def _update_installation_ui(self):
        """Ajustar UI para primeira execução: se não estiver instalado ou instalando, mostrar botão Install e ocultar Start/Stop."""
        try:
            in_progress = getattr(self, "_steam_install_in_progress", False)
            installed = self._is_scum_installed()

            if installed and not in_progress:
                try:
                    if hasattr(self, "btn_install_default"):
                        self.btn_install_default.pack_forget()
                except Exception:
                    pass
                try:
                    # Reaplicar regra de 1 botao (Start/Stop) baseada no status atual.
                    self._update_backend_status()
                except Exception:
                    pass
            else:
                try:
                    self.btn_start_backend.pack_forget()
                    self.btn_stop_backend.pack_forget()
                except Exception:
                    pass
                try:
                    if hasattr(self, "btn_install_default"):
                        self.btn_install_default.pack(side="left", padx=5)
                        if in_progress:
                            self.btn_install_default.configure(
                                state="disabled",
                                fg_color="#CC8400",
                            )
                        else:
                            self.btn_install_default.configure(
                                state="normal",
                                text="Install",
                                fg_color="#FFA500",
                            )
                except Exception:
                    pass
        except Exception:
            pass

    def _install_scum_server_default(self):
        """Instalação padrão (C:\\Servers). Usado na primeira execução."""
        try:
            self._install_or_update_scum_server(
                base_dir="C:\\Servers", prompt_for_base_dir=False
            )
        except Exception:
            pass

    def _create_settings_tab(self, parent):
        """Criar tab de Settings com SCUM Server Paths + Credentials"""
        settings_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.tabs_content["settings"] = settings_frame

        topbar = ctk.CTkFrame(
            settings_frame,
            fg_color=("gray90", "gray20"),
            corner_radius=12,
            border_width=1,
            border_color=("gray82", "gray28"),
        )
        topbar.pack(side="top", fill="x", padx=12, pady=(12, 10))

        content = ctk.CTkFrame(settings_frame, fg_color="transparent")
        content.pack(side="top", fill="both", expand=True)

        self.settings_pages = {}
        self.settings_page_buttons = {}
        self.settings_current_page = "general"

        def switch_settings_page(page_id: str):
            try:
                for f in self.settings_pages.values():
                    try:
                        f.pack_forget()
                    except Exception:
                        pass

                frame = self.settings_pages.get(page_id)
                if frame is not None:
                    frame.pack(fill="both", expand=True)

                self.settings_current_page = page_id

                for pid, btn in self.settings_page_buttons.items():
                    if pid == page_id:
                        btn.configure(
                            fg_color=("#1f538d", "#14375e"),
                            hover_color=("#2a5a9a", "#1a4a7a"),
                            font=ctk.CTkFont(size=12, weight="bold"),
                        )
                    else:
                        btn.configure(
                            fg_color=("gray", "gray"),
                            hover_color=("#3b3b3b", "#2a2a2a"),
                            font=ctk.CTkFont(size=12, weight="normal"),
                        )

                if page_id == "database":
                    try:
                        self._check_database_status_main()
                    except Exception:
                        pass
                elif page_id == "rcon":
                    try:
                        self._load_rcon_settings()
                        self._refresh_rcon_mod_status()
                    except Exception:
                        pass
                elif page_id == "mods":
                    try:
                        self._refresh_pak_mods_list()
                    except Exception:
                        pass

            except Exception:
                pass

        btn_general = ctk.CTkButton(
            topbar,
            text="General",
            command=lambda: switch_settings_page("general"),
            width=120,
            height=38,
        )
        btn_general.pack(side="left", padx=8, pady=8)
        self.settings_page_buttons["general"] = btn_general

        btn_database = ctk.CTkButton(
            topbar,
            text="Database",
            command=lambda: switch_settings_page("database"),
            width=120,
            height=38,
        )
        btn_database.pack(side="left", padx=(0, 8), pady=8)
        self.settings_page_buttons["database"] = btn_database

        btn_discord = ctk.CTkButton(
            topbar,
            text="Discord",
            command=lambda: switch_settings_page("discord"),
            width=120,
            height=38,
        )
        btn_discord.pack(side="left", padx=(0, 8), pady=8)
        self.settings_page_buttons["discord"] = btn_discord

        btn_rcon = ctk.CTkButton(
            topbar,
            text="RCON",
            command=lambda: switch_settings_page("rcon"),
            width=110,
            height=38,
        )
        btn_rcon.pack(side="left", padx=(0, 8), pady=8)
        self.settings_page_buttons["rcon"] = btn_rcon

        btn_mods = ctk.CTkButton(
            topbar,
            text="Mods",
            command=lambda: switch_settings_page("mods"),
            width=110,
            height=38,
        )
        btn_mods.pack(side="left", padx=(0, 8), pady=8)
        self.settings_page_buttons["mods"] = btn_mods

        btn_maintenance = ctk.CTkButton(
            topbar,
            text="Maintenance",
            command=lambda: switch_settings_page("maintenance"),
            width=120,
            height=38,
        )
        btn_maintenance.pack(side="left", padx=(0, 8), pady=8)
        self.settings_page_buttons["maintenance"] = btn_maintenance


        general_page = ctk.CTkFrame(content, fg_color="transparent")
        self.settings_pages["general"] = general_page

        # Scrollable frame para permitir rolagem
        scrollable_frame = ctk.CTkScrollableFrame(
            general_page, fg_color="transparent"
        )
        scrollable_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Card style
        card_color = ("gray95", "gray17")
        card_border_color = ("gray82", "gray28")

        # ========== SEÇÃO 1: CREDENTIALS ==========
        credentials_card = ctk.CTkFrame(
            scrollable_frame,
            fg_color=card_color,
            corner_radius=12,
            border_width=1,
            border_color=card_border_color,
        )
        # credentials_card.pack(fill="x", pady=(0, 12), padx=6)

        creds_header_frame = ctk.CTkFrame(credentials_card, fg_color="transparent")
        creds_header_frame.pack(fill="x", padx=15, pady=(15, 10))

        creds_icon_label = ctk.CTkLabel(
            creds_header_frame, text="🔑", font=ctk.CTkFont(size=20)
        )
        creds_icon_label.pack(side="left", padx=(0, 10))

        credentials_title = ctk.CTkLabel(
            creds_header_frame,
            text="Credentials",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        credentials_title.pack(side="left")

        # API Key
        apikey_field_frame = ctk.CTkFrame(credentials_card, fg_color="transparent")
        apikey_field_frame.pack(fill="x", padx=15, pady=5)

        apikey_label = ctk.CTkLabel(
            apikey_field_frame,
            text="API Key",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        apikey_label.pack(side="top", fill="x", padx=0, pady=(0, 2))

        apikey_entry_frame = ctk.CTkFrame(apikey_field_frame, fg_color="transparent")
        apikey_entry_frame.pack(side="top", fill="x", expand=True)

        self.main_apikey_entry = ctk.CTkEntry(
            apikey_entry_frame,
            placeholder_text="ssm_...",
            height=35,
            font=ctk.CTkFont(size=12),
            show="*",
        )
        self.main_apikey_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        eye_icon = IconHelper.load_icon(
            "ver", self.ROOT_DIR, self.EXE_DIR, self.IS_EXE, size=18
        )
        self.btn_toggle_apikey_main = ctk.CTkButton(
            apikey_entry_frame,
            image=eye_icon,
            text="",
            command=self._toggle_apikey_visibility_main,
            width=35,
            height=35,
            fg_color=("gray85", "gray25"),
            hover_color=("gray75", "gray35"),
        )
        self.btn_toggle_apikey_main.pack(side="left", padx=2)

        self.apikey_status_label = ctk.CTkLabel(
            apikey_field_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray70"),
            anchor="w",
        )
        self.apikey_status_label.pack(side="top", fill="x", padx=0, pady=(4, 0))

        try:
            self.main_apikey_entry.bind("<KeyRelease>", self._on_apikey_entry_changed_main)
        except Exception:
            pass

        # Hash
        hash_field_frame = ctk.CTkFrame(credentials_card, fg_color="transparent")
        hash_field_frame.pack(fill="x", padx=15, pady=5)

        hash_label = ctk.CTkLabel(
            hash_field_frame,
            text="Installation Hash (ID)",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        hash_label.pack(side="top", fill="x", padx=0, pady=(0, 2))

        hash_entry_frame = ctk.CTkFrame(hash_field_frame, fg_color="transparent")
        hash_entry_frame.pack(side="top", fill="x", expand=True)

        self.hash_entry = ctk.CTkEntry(
            hash_entry_frame,
            height=35,
            font=ctk.CTkFont(size=12),
            state="readonly",
            fg_color=("gray90", "gray20"),
        )
        self.hash_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        copy_icon = IconHelper.load_icon(
            "copiar", self.ROOT_DIR, self.EXE_DIR, self.IS_EXE, size=18
        )
        self.btn_copy = ctk.CTkButton(
            hash_entry_frame,
            image=copy_icon,
            text="",
            command=self._copy_hash,
            width=35,
            height=35,
            fg_color=("gray85", "gray25"),
            hover_color=("gray75", "gray35"),
        )
        self.btn_copy.pack(side="left", padx=2)

        self.copy_icon_original = copy_icon

        # Padding inferior no card
        ctk.CTkFrame(credentials_card, height=10, fg_color="transparent").pack()

        # ========== SEÇÃO: SERVER CONNECTION (DISCORD DISPLAY) ==========
        connection_card = ctk.CTkFrame(
            scrollable_frame,
            fg_color=card_color,
            corner_radius=12,
            border_width=1,
            border_color=card_border_color,
        )
        connection_card.pack(fill="x", pady=(0, 12), padx=6)

        conn_header_frame = ctk.CTkFrame(connection_card, fg_color="transparent")
        conn_header_frame.pack(fill="x", padx=15, pady=(15, 10))

        conn_icon_label = ctk.CTkLabel(
            conn_header_frame, text="🌐", font=ctk.CTkFont(size=20)
        )
        conn_icon_label.pack(side="left", padx=(0, 10))

        conn_title = ctk.CTkLabel(
            conn_header_frame,
            text="Server Connection (Discord Display)",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        conn_title.pack(side="left")

        # Row com IP e Porta na mesma linha
        conn_row_frame = ctk.CTkFrame(connection_card, fg_color="transparent")
        conn_row_frame.pack(fill="x", padx=15, pady=(0, 12))


        # External IP / Domain (expande na esquerda)
        ip_frame = ctk.CTkFrame(conn_row_frame, fg_color="transparent")
        ip_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkLabel(
            ip_frame,
            text="External IP / Domain",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(side="top", fill="x", padx=0, pady=(0, 2))

        self.settings_external_ip = ctk.CTkEntry(
            ip_frame,
            placeholder_text="Ex: 189.45.120.33 or play.myserver.com",
            height=35,
            font=ctk.CTkFont(size=12),
        )
        self.settings_external_ip.pack(side="top", fill="x", expand=True)

        # Game Port (compacto na direita)
        port_frame = ctk.CTkFrame(conn_row_frame, fg_color="transparent")
        port_frame.pack(side="right", padx=0)

        ctk.CTkLabel(
            port_frame,
            text="Game Port",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(side="top", fill="x", padx=0, pady=(0, 2))

        self.settings_server_port = ctk.CTkEntry(
            port_frame,
            placeholder_text="7777",
            width=130,
            height=35,
            font=ctk.CTkFont(size=12),
        )
        self.settings_server_port.pack(side="top", fill="x")


        # ========== SEÇÃO 2: SCUM SERVER PATHS ==========
        paths_card = ctk.CTkFrame(
            scrollable_frame,
            fg_color=card_color,
            corner_radius=12,
            border_width=1,
            border_color=card_border_color,
        )
        paths_card.pack(fill="x", pady=(0, 12), padx=6)


        paths_header_frame = ctk.CTkFrame(paths_card, fg_color="transparent")
        paths_header_frame.pack(fill="x", padx=15, pady=(15, 10))

        paths_icon_label = ctk.CTkLabel(
            paths_header_frame, text="📂", font=ctk.CTkFont(size=20)
        )
        paths_icon_label.pack(side="left", padx=(0, 10))

        paths_title = ctk.CTkLabel(
            paths_header_frame,
            text="SCUM Server Paths",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        paths_title.pack(side="left")

        self._create_path_field(
            paths_card,
            "Root Directory",
            "settings_root_directory",
            lambda: self._browse_path("root_directory", is_file=False),
            tooltip="Root directory of the SCUM Server installation",
        )

        self._create_path_field(
            paths_card,
            "Binaries Directory",
            "settings_binaries_directory",
            lambda: self._browse_path("binaries_directory", is_file=False),
            tooltip="Folder containing the server executable (Win64)",
        )

        self._create_path_field(
            paths_card,
            "Logs Directory",
            "settings_logs_directory",
            lambda: self._browse_path("logs_directory", is_file=False),
            tooltip="Folder where game logs are saved",
        )

        self._create_path_field(
            paths_card,
            "Server Logs Directory (SCUM.log)",
            "settings_server_logs_directory",
            lambda: self._browse_path("server_logs_directory", is_file=False),
            tooltip="Folder containing SCUM.log (e.g., ...\\SCUM\\Saved\\Logs)",
        )

        self._create_path_field(
            paths_card,
            "Config Directory",
            "settings_config_directory",
            lambda: self._browse_path("config_directory", is_file=False),
            tooltip="Folder containing configuration files (.ini)",
        )

        self._create_path_field(
            paths_card,
            "Database File (SCUM.db)",
            "settings_database",
            lambda: self._browse_path("database", is_file=True),
            tooltip="Full path to the SCUM.db file",
        )

        self._create_path_field(
            paths_card,
            "Savefiles Directory",
            "settings_savefiles_directory",
            lambda: self._browse_path("savefiles_directory", is_file=False),
            tooltip="Root folder for savefiles",
        )

        self._create_path_field(
            paths_card,
            "SteamCMD Directory",
            "settings_steamcmd_path",
            lambda: self._browse_path("steamcmd_path", is_file=False),
            tooltip="Folder containing steamcmd.exe (e.g., C:\\Servers\\steamcmd)",
        )

        ctk.CTkFrame(paths_card, height=10, fg_color="transparent").pack()

        # ========== SEÇÃO 3: CHAT MONITORING ==========
        chat_card = ctk.CTkFrame(
            scrollable_frame,
            fg_color=card_color,
            corner_radius=12,
            border_width=1,
            border_color=card_border_color,
        )
        chat_card.pack(fill="x", pady=(0, 12), padx=6)

        chat_header_frame = ctk.CTkFrame(chat_card, fg_color="transparent")
        chat_header_frame.pack(fill="x", padx=15, pady=(15, 10))

        chat_icon_label = ctk.CTkLabel(
            chat_header_frame, text="💬", font=ctk.CTkFont(size=20)
        )
        chat_icon_label.pack(side="left", padx=(0, 10))

        chat_title = ctk.CTkLabel(
            chat_header_frame,
            text="Chat Monitoring",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        chat_title.pack(side="left")

        channels_frame = ctk.CTkFrame(chat_card, fg_color="transparent")
        channels_frame.pack(fill="x", padx=15, pady=(0, 10))

        channels_label = ctk.CTkLabel(
            channels_frame,
            text="Channels",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        channels_label.pack(side="top", fill="x", pady=(0, 6))

        self.chat_channel_global_var = ctk.BooleanVar(value=True)
        self.chat_channel_local_var = ctk.BooleanVar(value=False)
        self.chat_channel_squad_var = ctk.BooleanVar(value=False)
        self.chat_channel_admin_var = ctk.BooleanVar(value=False)

        channels_row = ctk.CTkFrame(channels_frame, fg_color="transparent")
        channels_row.pack(fill="x")

        ctk.CTkCheckBox(
            channels_row, text="Global", variable=self.chat_channel_global_var
        ).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(
            channels_row, text="Local", variable=self.chat_channel_local_var
        ).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(
            channels_row, text="Squad", variable=self.chat_channel_squad_var
        ).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(
            channels_row, text="Admin", variable=self.chat_channel_admin_var
        ).pack(side="left", padx=(0, 10))

        ctk.CTkFrame(chat_card, height=10, fg_color="transparent").pack()

        # ========== BOTÕES ==========
        buttons_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 0), padx=10)

        save_settings_btn = ctk.CTkButton(
            buttons_frame,
            text="Save Settings",
            command=self._save_settings,
            width=150,
            height=40,
            fg_color="green",
            hover_color="darkgreen",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        save_settings_btn.pack(side="left", padx=5)

        install_server_btn = ctk.CTkButton(
            buttons_frame,
            text="Install/Update SCUM Server",
            command=self._install_or_update_scum_server,
            width=220,
            height=40,
            fg_color=("#FF9800", "#FF9800"),
            hover_color=("#F57C00", "#F57C00"),
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        install_server_btn.pack(side="left", padx=5)
        self.btn_install_scum_server = install_server_btn

        self.btn_apply_nssm_preset = None

        reload_settings_btn = ctk.CTkButton(
            buttons_frame,
            text="Reload Settings",
            command=self._load_settings,
            width=150,
            height=40,
            fg_color="blue",
            hover_color="darkblue",
            font=ctk.CTkFont(size=13),
        )
        reload_settings_btn.pack(side="left", padx=5)

        # Carregar valores iniciais
        self._load_settings()

        try:
            database_page = ctk.CTkFrame(content, fg_color="transparent")
            self.settings_pages["database"] = database_page
            self._create_database_tab(database_page, register_tab=False)
        except Exception:
            pass

        try:
            discord_page = ctk.CTkFrame(content, fg_color="transparent")
            self.settings_pages["discord"] = discord_page
            self._create_webhooks_tab(discord_page, register_tab=False)
        except Exception:
            pass

        card_color = ("gray95", "gray17")
        card_border_color = ("gray82", "gray28")

        # ================================================================
        # ========== RCON PAGE (UE4SS Engine & Network Settings) =========
        # ================================================================
        try:
            rcon_page = ctk.CTkFrame(content, fg_color="transparent")
            self.settings_pages["rcon"] = rcon_page

            rcon_scroll = ctk.CTkScrollableFrame(rcon_page, fg_color="transparent")
            rcon_scroll.pack(fill="both", expand=True, padx=12, pady=12)

            # ========== CARD 1: RCON ENGINE & CONNECTION (COMPACT) ==========
            rcon_card = ctk.CTkFrame(
                rcon_scroll,
                fg_color=card_color,
                corner_radius=12,
                border_width=1,
                border_color=card_border_color,
            )
            rcon_card.pack(fill="x", pady=(0, 12), padx=6)

            # Header com Badge de Status do Motor à Direita
            rcon_header = ctk.CTkFrame(rcon_card, fg_color="transparent")
            rcon_header.pack(fill="x", padx=15, pady=(15, 12))

            ctk.CTkLabel(
                rcon_header, text="📡", font=ctk.CTkFont(size=20)
            ).pack(side="left", padx=(0, 10))

            ctk.CTkLabel(
                rcon_header,
                text="RCON Engine & Connection",
                font=ctk.CTkFont(size=16, weight="bold"),
            ).pack(side="left")

            self.rcon_mod_badge_label = ctk.CTkLabel(
                rcon_header,
                text="Checking...",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="gray",
            )
            self.rcon_mod_badge_label.pack(side="right")

            # Credentials Row: IP, Port, Password
            rcon_fields_row = ctk.CTkFrame(rcon_card, fg_color="transparent")
            rcon_fields_row.pack(fill="x", padx=15, pady=(0, 12))

            # IP
            rcon_ip_col = ctk.CTkFrame(rcon_fields_row, fg_color="transparent")
            rcon_ip_col.pack(side="left", fill="x", expand=True, padx=(0, 8))
            ctk.CTkLabel(
                rcon_ip_col,
                text="Server IP / Host",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).pack(fill="x", pady=(0, 2))
            self.rcon_ip_entry = ctk.CTkEntry(
                rcon_ip_col,
                placeholder_text="127.0.0.1",
                height=35,
                font=ctk.CTkFont(size=12),
            )
            self.rcon_ip_entry.pack(fill="x")

            # Port
            rcon_port_col = ctk.CTkFrame(rcon_fields_row, fg_color="transparent")
            rcon_port_col.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                rcon_port_col,
                text="Port",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).pack(fill="x", pady=(0, 2))
            self.rcon_port_entry = ctk.CTkEntry(
                rcon_port_col,
                placeholder_text="27100",
                height=35,
                width=90,
                font=ctk.CTkFont(size=12),
            )
            self.rcon_port_entry.pack()

            # Password
            rcon_pass_col = ctk.CTkFrame(rcon_fields_row, fg_color="transparent")
            rcon_pass_col.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                rcon_pass_col,
                text="Password",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).pack(fill="x", pady=(0, 2))
            rcon_pass_row = ctk.CTkFrame(rcon_pass_col, fg_color="transparent")
            rcon_pass_row.pack(fill="x")
            self.rcon_password_entry = ctk.CTkEntry(
                rcon_pass_row,
                placeholder_text="••••••••",
                height=35,
                font=ctk.CTkFont(size=12),
                show="*",
            )
            self.rcon_password_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            self._rcon_pass_visible = False

            def _toggle_rcon_pass():
                self._rcon_pass_visible = not self._rcon_pass_visible
                self.rcon_password_entry.configure(
                    show="" if self._rcon_pass_visible else "*"
                )

            ctk.CTkButton(
                rcon_pass_row,
                text="👁",
                command=_toggle_rcon_pass,
                width=38,
                height=35,
                fg_color=("gray85", "gray25"),
                hover_color=("gray75", "gray35"),
                text_color=("gray10", "gray90"),
                font=ctk.CTkFont(size=14),
            ).pack(side="left")

            self.rcon_provider_var = ctk.StringVar(value="bsbr_scum")
            self.rcon_enabled_var = ctk.BooleanVar(value=True)

            # Action Buttons Row
            rcon_actions_row = ctk.CTkFrame(rcon_card, fg_color="transparent")
            rcon_actions_row.pack(fill="x", padx=15, pady=(0, 15))

            ctk.CTkButton(
                rcon_actions_row,
                text="💾 Save Settings",
                command=self._save_rcon_settings,
                width=135,
                height=35,
                fg_color="#2E7D32",
                hover_color="#1B5E20",
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                rcon_actions_row,
                text="⚡ Test Connection",
                command=self._test_rcon_connection,
                width=135,
                height=35,
                fg_color=("gray70", "gray30"),
                hover_color=("gray60", "gray40"),
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 6))

            self.btn_select_rcon_mod = ctk.CTkButton(
                rcon_actions_row,
                text="📦 Select Engine",
                command=self._select_and_install_rcon_dialog,
                width=145,
                height=35,
                fg_color=("#1565C0", "#1565C0"),
                hover_color=("#0D47A1", "#0D47A1"),
                font=ctk.CTkFont(size=12),
            )
            self.btn_select_rcon_mod.pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                rcon_actions_row,
                text="📁 RCON Folder",
                command=self._open_rcon_mods_folder,
                width=120,
                height=35,
                fg_color=("gray70", "gray30"),
                hover_color=("gray60", "gray40"),
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 6))

            self.btn_uninstall_rcon_mod = ctk.CTkButton(
                rcon_actions_row,
                text="🗑️ Uninstall",
                command=self._uninstall_rcon_mod,
                width=100,
                height=35,
                fg_color=("#B71C1C", "#B71C1C"),
                hover_color=("#7F0000", "#7F0000"),
                font=ctk.CTkFont(size=12),
            )
            self.btn_uninstall_rcon_mod.pack(side="left")

            # ========== CARD 2: INTERACTIVE RCON CONSOLE & TESTER ==========
            console_card = ctk.CTkFrame(
                rcon_scroll,
                fg_color=card_color,
                corner_radius=12,
                border_width=1,
                border_color=card_border_color,
            )
            console_card.pack(fill="x", pady=(0, 12), padx=6)

            console_header = ctk.CTkFrame(console_card, fg_color="transparent")
            console_header.pack(fill="x", padx=15, pady=(15, 8))

            ctk.CTkLabel(
                console_header, text="💻", font=ctk.CTkFont(size=20)
            ).pack(side="left", padx=(0, 10))

            ctk.CTkLabel(
                console_header,
                text="RCON Console & Command Tester",
                font=ctk.CTkFont(size=16, weight="bold"),
            ).pack(side="left")

            ctk.CTkLabel(
                console_header,
                text="Send real-time remote commands (e.g. players, Announce, as <player> SpawnItem)",
                font=ctk.CTkFont(size=11),
                text_color=("gray40", "gray70"),
            ).pack(side="right")

            # Console Input Row
            cmd_input_row = ctk.CTkFrame(console_card, fg_color="transparent")
            cmd_input_row.pack(fill="x", padx=15, pady=(0, 8))

            self.rcon_cmd_entry = ctk.CTkEntry(
                cmd_input_row,
                placeholder_text="Enter RCON command (e.g. players, Announce Hello, sudo SpawnBrenner)...",
                height=36,
                font=ctk.CTkFont(family="Consolas", size=12),
            )
            self.rcon_cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
            self.rcon_cmd_entry.bind("<Return>", lambda event: self._execute_rcon_console_command())

            ctk.CTkButton(
                cmd_input_row,
                text="🚀 Send",
                command=self._execute_rcon_console_command,
                width=90,
                height=36,
                fg_color=("#1976D2", "#1976D2"),
                hover_color=("#1565C0", "#1565C0"),
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                cmd_input_row,
                text="🧹 Clear",
                command=self._clear_rcon_console,
                width=75,
                height=36,
                fg_color=("gray70", "gray30"),
                hover_color=("gray60", "gray40"),
                font=ctk.CTkFont(size=12),
            ).pack(side="left")

            # Quick Preset Command Buttons
            quick_btn_row = ctk.CTkFrame(console_card, fg_color="transparent")
            quick_btn_row.pack(fill="x", padx=15, pady=(0, 8))

            ctk.CTkLabel(
                quick_btn_row,
                text="Quick Commands:",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("gray40", "gray70"),
            ).pack(side="left", padx=(0, 8))

            for label, cmd in [
                ("👥 players", "players"),
                ("📜 ListPlayers", "ListPlayers"),
                ("🚗 vehicles", "vehicles"),
                ("📢 Announce...", "Announce Hello from SSM!"),
                ("❓ help", "help"),
            ]:
                ctk.CTkButton(
                    quick_btn_row,
                    text=label,
                    command=lambda c=cmd: self._set_and_send_rcon_quick_command(c),
                    height=24,
                    fg_color=("gray75", "gray25"),
                    hover_color=("gray65", "gray35"),
                    font=ctk.CTkFont(family="Consolas", size=11),
                ).pack(side="left", padx=(0, 5))

            # Console Output Textbox
            self.rcon_console_textbox = ctk.CTkTextbox(
                console_card,
                height=160,
                corner_radius=8,
                fg_color=("#1E1E1E", "#121212"),
                text_color=("#E0E0E0", "#E0E0E0"),
                font=ctk.CTkFont(family="Consolas", size=11),
                wrap="word",
            )
            self.rcon_console_textbox.pack(fill="x", padx=15, pady=(0, 15))
            self.rcon_console_textbox.insert("1.0", "--- RCON Terminal Ready. Enter a command above, use Quick Commands, or press Enter. ---\n\n")


            # ========== CARD 3: RCON LOGGING & AUTO-CLEANUP (COMPACT BAR) ==========
            log_card = ctk.CTkFrame(
                rcon_scroll,
                fg_color=card_color,
                corner_radius=12,
                border_width=1,
                border_color=card_border_color,
            )
            log_card.pack(fill="x", pady=(0, 12), padx=6)

            log_bar = ctk.CTkFrame(log_card, fg_color="transparent")
            log_bar.pack(fill="x", padx=15, pady=12)

            ctk.CTkLabel(
                log_bar, text="📜", font=ctk.CTkFont(size=18)
            ).pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                log_bar,
                text="Logs & Retention:",
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(side="left", padx=(0, 12))

            self.rcon_log_enabled_var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(
                log_bar,
                text="Enable Logs",
                variable=self.rcon_log_enabled_var,
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 15))

            self.rcon_log_auto_clean_var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(
                log_bar,
                text="Auto-clean (50MB)",
                variable=self.rcon_log_auto_clean_var,
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 12))

            ctk.CTkLabel(
                log_bar,
                text="Days:",
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 4))

            self.rcon_log_retention_entry = ctk.CTkEntry(
                log_bar,
                placeholder_text="7",
                width=50,
                height=28,
                font=ctk.CTkFont(size=12),
            )
            self.rcon_log_retention_entry.pack(side="left", padx=(0, 20))
            self.rcon_log_retention_entry.insert(0, "7")


            ctk.CTkButton(
                log_bar,
                text="📁 Open Logs",
                command=self._open_rcon_logs_folder,
                width=120,
                height=30,
                fg_color=("gray70", "gray30"),
                hover_color=("gray60", "gray40"),
                font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                log_bar,
                text="🗑️ Clean Now",
                command=self._clean_rcon_logs_now,
                width=110,
                height=30,
                fg_color=("#B71C1C", "#B71C1C"),
                hover_color=("#7F0000", "#7F0000"),
                font=ctk.CTkFont(size=11),
            ).pack(side="left")

            # Load initial settings and lists for RCON
            self._load_rcon_settings()
            self.after(200, self._refresh_rcon_mod_status)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao criar aba RCON: {e}")



        # ================================================================
        # ========== MODS PAGE (Exclusively .PAK Content Mods) ===========
        # ================================================================
        try:
            mods_page = ctk.CTkFrame(content, fg_color="transparent")
            self.settings_pages["mods"] = mods_page

            mods_scroll = ctk.CTkScrollableFrame(mods_page, fg_color="transparent")
            mods_scroll.pack(fill="both", expand=True, padx=12, pady=12)

            # ========== CARD: CONTENT MODS (.PAK MANAGER) ==========
            pak_card = ctk.CTkFrame(
                mods_scroll,
                fg_color=card_color,
                corner_radius=12,
                border_width=1,
                border_color=card_border_color,
            )
            pak_card.pack(fill="x", pady=(0, 12), padx=6)

            pak_header = ctk.CTkFrame(pak_card, fg_color="transparent")
            pak_header.pack(fill="x", padx=15, pady=(15, 6))

            ctk.CTkLabel(
                pak_header, text="📦", font=ctk.CTkFont(size=20)
            ).pack(side="left", padx=(0, 10))

            ctk.CTkLabel(
                pak_header,
                text="Content Mods (.PAK Manager)",
                font=ctk.CTkFont(size=16, weight="bold"),
            ).pack(side="left")

            # Folder location info
            ctk.CTkLabel(
                pak_card,
                text="Asset, skin, balancing, and cosmetic mods installed in SCUM/Content/Paks/~mods/ and safely backed up in data/mods/paks/.",
                font=ctk.CTkFont(size=11),
                text_color=("gray40", "gray70"),
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=15, pady=(0, 8))

            # Inner frame for .pak mods table/list
            self.pak_mods_list_frame = ctk.CTkFrame(pak_card, fg_color=("gray90", "gray20"), corner_radius=8)
            self.pak_mods_list_frame.pack(fill="x", padx=15, pady=(0, 12))

            # Bottom action buttons for .pak
            pak_btn_row = ctk.CTkFrame(pak_card, fg_color="transparent")
            pak_btn_row.pack(fill="x", padx=15, pady=(0, 15))

            ctk.CTkButton(
                pak_btn_row,
                text="+ Install .pak Mod",
                command=self._install_pak_mod,
                width=150,
                height=36,
                fg_color=("#2E7D32", "#2E7D32"),
                hover_color=("#1B5E20", "#1B5E20"),
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                pak_btn_row,
                text="📁 Open Server ~mods",
                command=self._open_pak_mods_folder,
                width=160,
                height=36,
                fg_color=("gray70", "gray30"),
                hover_color=("gray60", "gray40"),
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                pak_btn_row,
                text="💾 Safe Storage",
                command=self._open_pak_safe_storage,
                width=135,
                height=36,
                fg_color=("gray70", "gray30"),
                hover_color=("gray60", "gray40"),
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                pak_btn_row,
                text="🔄 Refresh List",
                command=self._refresh_pak_mods_list,
                width=120,
                height=36,
                fg_color=("gray70", "gray30"),
                hover_color=("gray60", "gray40"),
                font=ctk.CTkFont(size=12),
            ).pack(side="left")

            # Load initial pak list
            self.after(300, self._refresh_pak_mods_list)


        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao criar aba Mods: {e}")





        # ========== MAINTENANCE PAGE ==========
        try:
            maintenance_page = ctk.CTkFrame(content, fg_color="transparent")
            self.settings_pages["maintenance"] = maintenance_page
            self._create_maintenance_page(maintenance_page)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao criar aba Maintenance: {e}")

        switch_settings_page("general")

    def _check_database_status_main(self):
        """Check database status in main Settings tab"""
        import threading
        from utils.database_initializer import check_database_status, EXPECTED_TABLES
        from utils.config_path_helper import ConfigPathHelper

        def check_in_thread():
            try:
                config = self._load_config()
                if not config:
                    config = {}
                path_helper = ConfigPathHelper(config)
                ssm_db_path = path_helper.get_ssm_db_path()

                status = check_database_status(ssm_db_path)
                # Ensure expected_tables is set
                if "expected_tables" not in status or status["expected_tables"] == 0:
                    status["expected_tables"] = len(EXPECTED_TABLES)

                # Update UI in main thread
                def update_ui(s=status):
                    try:
                        if hasattr(self, "_update_database_status_main_ui"):
                            self._update_database_status_main_ui(s)
                    except Exception:
                        pass

                try:
                    self.after(0, update_ui)
                except (RuntimeError, AttributeError):
                    pass
            except Exception as e:
                error_status = {
                    "exists": False,
                    "initialized": False,
                    "table_count": 0,
                    "expected_tables": len(EXPECTED_TABLES),
                    "size_mb": 0.0,
                }

                def update_error(s=error_status):
                    try:
                        if hasattr(self, "_update_database_status_main_ui"):
                            self._update_database_status_main_ui(s)
                    except Exception:
                        pass

                try:
                    self.after(0, update_error)
                except (RuntimeError, AttributeError):
                    pass

        threading.Thread(target=check_in_thread, daemon=True).start()

    def _update_database_status_main_ui(self, status: dict):
        """Update database status UI in main Settings tab"""
        required_count = status.get("required_table_count", status.get("table_count", 0))
        expected = status.get("expected_tables")
        if not expected:
            try:
                from utils.database_initializer import EXPECTED_TABLES

                expected = len(EXPECTED_TABLES)
            except Exception:
                expected = 0

        # Update table count label
        if hasattr(self, "db_count_label_main"):
            self.db_count_label_main.configure(text=f"{required_count}/{expected} tables")

        # Update button state
        if hasattr(self, "btn_init_db_main"):
            if status.get("initialized", False) or required_count >= expected:
                self.btn_init_db_main.configure(state="disabled", fg_color="gray")
            else:
                self.btn_init_db_main.configure(state="normal", fg_color="green")

        # Update tables list
        if hasattr(self, "tables_listbox"):
            columns = status.get("columns_per_table", {})
            self._update_tables_list(
                status.get("tables", []), status.get("missing_tables", []), columns
            )

    def _initialize_database_main(self):
        """Initialize database in main Settings tab"""
        import threading
        from utils.database_initializer import initialize_all_tables
        from utils.config_path_helper import ConfigPathHelper

        # Check if backend is running
        if self.backend_running:
            self._add_log_message(
                "⚠️ Backend is running. Stop the backend before initializing the database.",
                "WARNING",
            )
            return

        # Disable button
        if hasattr(self, "btn_init_db_main"):
            self.btn_init_db_main.configure(state="disabled")

        # Update count label
        if hasattr(self, "db_count_label_main"):
            self.db_count_label_main.configure(text="Initializing...")

        def init_in_thread():
            try:
                config = self._load_config()
                if not config:
                    config = {}
                path_helper = ConfigPathHelper(config)
                ssm_db_path = path_helper.get_ssm_db_path()

                result = initialize_all_tables(
                    ssm_db_path,
                    config=config,
                    path_helper=path_helper,
                    logger=self.logger,
                )

                # Atualizar UI na thread principal
                self.after(0, lambda: self._on_initialization_complete_main(result))

            except Exception as e:
                error_result = {
                    "success": False,
                    "tables_created": 0,
                    "tables_total": 0,
                    "errors": [{"table": "unknown", "error": str(e)}],
                    "duration_seconds": 0,
                }
                self.after(
                    0, lambda: self._on_initialization_complete_main(error_result)
                )

        threading.Thread(target=init_in_thread, daemon=True).start()

    def _on_initialization_complete_main(self, result: dict):
        """Callback when initialization completes in main tab"""
        if result.get("success", False):
            tables_created = result.get("tables_created", 0)
            duration = result.get("duration_seconds", 0)
            self._add_log_message(
                f"✅ Database initialized successfully! {tables_created} tables created in {duration}s",
                "SUCCESS",
            )
        else:
            errors = result.get("errors", [])
            error_count = len(errors)
            self._add_log_message(
                f"❌ Error initializing database: {error_count} error(s) found", "ERROR"
            )

        # Update status
        self._check_database_status_main()

    def _create_path_field(
        self,
        parent,
        label_text: str,
        entry_attr: str,
        browse_command,
        tooltip: str = None,
    ):
        """Criar campo de path com layout moderno (Label em cima, Entry em baixo)"""
        field_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_frame.pack(fill="x", padx=15, pady=5)

        # Label em cima
        label = ctk.CTkLabel(
            field_frame,
            text=label_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        label.pack(side="top", fill="x", padx=0, pady=(0, 2))

        # Container do input + botão
        entry_frame = ctk.CTkFrame(field_frame, fg_color="transparent")
        entry_frame.pack(side="top", fill="x", expand=True)

        entry = ctk.CTkEntry(
            entry_frame,
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color=("gray95", "gray20"),
            border_color=("gray70", "gray40"),
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Bind validation
        entry.bind("<FocusOut>", lambda e: self._validate_path_field(entry))
        entry.bind("<KeyRelease>", lambda e: self._validate_path_field(entry))

        # Armazenar referência do entry
        setattr(self, entry_attr, entry)

        # Botão Browse
        browse_btn = ctk.CTkButton(
            entry_frame,
            text="Browse...",
            command=browse_command,
            width=80,
            height=35,
            fg_color=("gray85", "gray25"),
            hover_color=("gray75", "gray35"),
            text_color=("gray10", "gray90"),
            font=ctk.CTkFont(size=12),
        )
        browse_btn.pack(side="right")

    def _normalize_windows_path(self, path: str) -> str:
        """Normalizar caminho do Windows para usar \\ (barra invertida dupla no JSON)"""
        if not path:
            return path
        # Converter / para \\ para manter consistência no Windows
        normalized = path.replace("/", "\\")
        return normalized

    def _browse_path(self, field_name: str, is_file: bool = False):
        """Abrir diálogo para selecionar pasta ou arquivo"""
        try:
            import tkinter.filedialog as filedialog

            # Obter valor atual do campo
            entry = getattr(self, f"settings_{field_name}")
            current_value = entry.get()

            if is_file:
                # Selecionar arquivo (.db)
                initial_dir = "C:\\"
                if current_value:
                    try:
                        dir_path = os.path.dirname(current_value)
                        if dir_path and os.path.exists(dir_path):
                            initial_dir = dir_path
                    except:
                        pass

                path = filedialog.askopenfilename(
                    title=f"Select {field_name.replace('_', ' ').title()}",
                    initialdir=initial_dir,
                    filetypes=[("Database files", "*.db"), ("All files", "*.*")],
                )
            else:
                # Selecionar pasta
                initial_dir = "C:\\"
                if current_value and os.path.exists(current_value):
                    initial_dir = current_value

                path = filedialog.askdirectory(
                    title=f"Select {field_name.replace('_', ' ').title()}",
                    initialdir=initial_dir,
                )

            if path:
                # Normalizar caminho antes de inserir no campo
                normalized_path = self._normalize_windows_path(path)
                entry.delete(0, "end")
                entry.insert(0, normalized_path)

                # Validar manualmente após inserção
                self._validate_path_field(entry)

        except Exception as e:
            self._add_log_message(f"Failed to select path: {e}", "ERROR")
            if self.logger:
                self.logger.error(f"Failed to select path: {e}")

    def _load_settings(self):
        """Carregar configurações do config.json para os campos"""
        try:
            config = self._load_config()
            if not config:
                return

            # Carregar SCUM Server Paths
            scum_paths = config.get("paths", {}).get("scum_server", {})

            if hasattr(self, "settings_root_directory"):
                self.settings_root_directory.delete(0, "end")
                self.settings_root_directory.insert(
                    0, scum_paths.get("root_directory", "")
                )

            if hasattr(self, "settings_binaries_directory"):
                self.settings_binaries_directory.delete(0, "end")
                self.settings_binaries_directory.insert(
                    0, scum_paths.get("binaries_directory", "")
                )

            if hasattr(self, "settings_logs_directory"):
                self.settings_logs_directory.delete(0, "end")
                self.settings_logs_directory.insert(
                    0, scum_paths.get("logs_directory", "")
                )

            if hasattr(self, "settings_server_logs_directory"):
                self.settings_server_logs_directory.delete(0, "end")
                self.settings_server_logs_directory.insert(
                    0, scum_paths.get("server_logs_directory", "")
                )

            if hasattr(self, "settings_config_directory"):
                self.settings_config_directory.delete(0, "end")
                self.settings_config_directory.insert(
                    0, scum_paths.get("config_directory", "")
                )

            if hasattr(self, "settings_database"):
                self.settings_database.delete(0, "end")
                self.settings_database.insert(0, scum_paths.get("database", ""))

            if hasattr(self, "settings_savefiles_directory"):
                self.settings_savefiles_directory.delete(0, "end")
                self.settings_savefiles_directory.insert(
                    0, scum_paths.get("savefiles_directory", "")
                )

            # Carregar Server Connection (IP Externo e Porta) e SteamCMD
            server_cfg = config.get("server", {})
            if hasattr(self, "settings_external_ip"):
                self.settings_external_ip.delete(0, "end")
                self.settings_external_ip.insert(0, str(server_cfg.get("external_ip") or ""))

            if hasattr(self, "settings_server_port"):
                self.settings_server_port.delete(0, "end")
                port_val = server_cfg.get("port", 7777)
                self.settings_server_port.insert(0, str(port_val if port_val is not None else 7777))

            if hasattr(self, "settings_steamcmd_path"):
                self.settings_steamcmd_path.delete(0, "end")
                self.settings_steamcmd_path.insert(0, server_cfg.get("steamcmd_path", ""))


            # Carregar Credentials (API Key e Hash)
            # API Key
            licensing_config = config.get("licensing", {})
            apikey = licensing_config.get("gestao_api_key", "")
            if apikey and apikey.startswith("ENCRYPTED:"):
                from core.security.credential_encryption import decrypt_credential

                try:
                    apikey = decrypt_credential(apikey, logger=self.logger)
                except Exception as e:
                    if self.logger:
                        self.logger.warn(f"Failed to decrypt API key: {e}")
                    apikey = ""

            if hasattr(self, "main_apikey_entry"):
                self.main_apikey_entry.delete(0, "end")
                if apikey:
                    self.main_apikey_entry.insert(0, apikey)
                    self.main_apikey_entry.configure(show="*")
                    self.apikey_visible = False
                    if hasattr(self, "btn_toggle_apikey_main"):
                        eye_icon = IconHelper.load_icon(
                            "ver", self.ROOT_DIR, self.EXE_DIR, self.IS_EXE, size=18
                        )
                        self.btn_toggle_apikey_main.configure(image=eye_icon, text="")
                else:
                    pass

                try:
                    self.main_apikey_entry.configure(state="normal")
                except Exception:
                    pass
                self.apikey_dirty = False
                self._set_apikey_status_main("", status="idle")

            # Hash (já é carregado em _update_fingerprint_ui)
            # Não precisa recarregar aqui, pois é gerado dinamicamente

            chat_cfg = config.get("chat_monitoring", {})

            if hasattr(self, "chat_monitoring_enabled_var"):
                try:
                    self.chat_monitoring_enabled_var.set(bool(chat_cfg.get("enabled", True)))
                except Exception:
                    pass

            if hasattr(self, "chat_monitoring_webhook_entry"):
                self.chat_monitoring_webhook_entry.delete(0, "end")
                self.chat_monitoring_webhook_entry.insert(
                    0, str(chat_cfg.get("webhook_name", "chat_in_game") or "chat_in_game")
                )

            if hasattr(self, "chat_monitoring_rate_limit_entry"):
                self.chat_monitoring_rate_limit_entry.delete(0, "end")
                self.chat_monitoring_rate_limit_entry.insert(
                    0, str(chat_cfg.get("rate_limit", 10))
                )

            if hasattr(self, "chat_monitoring_cleanup_days_entry"):
                self.chat_monitoring_cleanup_days_entry.delete(0, "end")
                self.chat_monitoring_cleanup_days_entry.insert(
                    0, str(chat_cfg.get("cleanup_days", 7))
                )

            channels = chat_cfg.get("channels")
            if not isinstance(channels, list) or not channels:
                channels = ["Global"]
            channels_norm = set(str(c).strip().lower() for c in channels)

            if hasattr(self, "chat_channel_global_var"):
                self.chat_channel_global_var.set("global" in channels_norm)
            if hasattr(self, "chat_channel_local_var"):
                self.chat_channel_local_var.set("local" in channels_norm)
            if hasattr(self, "chat_channel_squad_var"):
                self.chat_channel_squad_var.set("squad" in channels_norm)
            if hasattr(self, "chat_channel_admin_var"):
                self.chat_channel_admin_var.set("admin" in channels_norm)

        except Exception as e:
            self._add_log_message(f"Failed to load settings: {e}", "ERROR")
            if self.logger:
                self.logger.error(f"Failed to load settings: {e}")

    def _save_settings(self):
        """Salvar configurações para o config.json"""
        try:
            config = self._load_config()
            if not config:
                self._add_log_message(
                    "Error: Unable to load config.json", "ERROR"
                )
                return

            # Salvar SCUM Server Paths
            if "paths" not in config:
                config["paths"] = {}
            if "scum_server" not in config["paths"]:
                config["paths"]["scum_server"] = {}

            if hasattr(self, "settings_root_directory"):
                config["paths"]["scum_server"]["root_directory"] = (
                    self._normalize_windows_path(self.settings_root_directory.get())
                )
            if hasattr(self, "settings_binaries_directory"):
                config["paths"]["scum_server"]["binaries_directory"] = (
                    self._normalize_windows_path(self.settings_binaries_directory.get())
                )
            if hasattr(self, "settings_logs_directory"):
                config["paths"]["scum_server"]["logs_directory"] = (
                    self._normalize_windows_path(self.settings_logs_directory.get())
                )

            if hasattr(self, "settings_server_logs_directory"):
                config["paths"]["scum_server"]["server_logs_directory"] = (
                    self._normalize_windows_path(
                        self.settings_server_logs_directory.get()
                    )
                )
            if hasattr(self, "settings_config_directory"):
                config["paths"]["scum_server"]["config_directory"] = (
                    self._normalize_windows_path(self.settings_config_directory.get())
                )
            if hasattr(self, "settings_database"):
                config["paths"]["scum_server"]["database"] = (
                    self._normalize_windows_path(self.settings_database.get())
                )
            if hasattr(self, "settings_savefiles_directory"):
                config["paths"]["scum_server"]["savefiles_directory"] = (
                    self._normalize_windows_path(
                        self.settings_savefiles_directory.get()
                    )
                )

            # Salvar Server Connection & SteamCMD
            if "server" not in config:
                config["server"] = {}
            if hasattr(self, "settings_external_ip"):
                config["server"]["external_ip"] = self.settings_external_ip.get().strip()
            if hasattr(self, "settings_server_port"):
                try:
                    port_str = self.settings_server_port.get().strip()
                    config["server"]["port"] = int(port_str) if port_str else 7777
                except Exception:
                    config["server"]["port"] = 7777
            if hasattr(self, "settings_steamcmd_path"):
                config["server"]["steamcmd_path"] = self._normalize_windows_path(
                    self.settings_steamcmd_path.get()
                )


            # Salvar API Key (se foi editada)
            if hasattr(self, "main_apikey_entry") and getattr(self, "apikey_dirty", False):
                apikey_value = (self.main_apikey_entry.get() or "").strip()
                if not apikey_value:
                    self._add_log_message("API Key is empty", "WARNING")
                    import tkinter.messagebox as messagebox

                    messagebox.showwarning(
                        "Warning", "Please enter an API Key before saving."
                    )
                    return

                if not apikey_value.startswith("ssm_"):
                    self._add_log_message("Invalid API Key format", "WARNING")
                    import tkinter.messagebox as messagebox

                    messagebox.showerror(
                        "Error",
                        "Invalid API Key format.\n\nThe API Key must start with 'ssm_'",
                    )
                    return

                if "licensing" not in config:
                    config["licensing"] = {}

                if not apikey_value.startswith("ENCRYPTED:"):
                    from core.security.credential_encryption import (
                        encrypt_credential,
                    )

                    try:
                        encrypted_apikey = encrypt_credential(
                            apikey_value, logger=self.logger
                        )
                        config["licensing"]["gestao_api_key"] = encrypted_apikey
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Failed to encrypt API key: {e}")
                        config["licensing"]["gestao_api_key"] = apikey_value
                else:
                    config["licensing"]["gestao_api_key"] = apikey_value

            if "chat_monitoring" not in config or not isinstance(config.get("chat_monitoring"), dict):
                config["chat_monitoring"] = {}

            if hasattr(self, "chat_monitoring_enabled_var"):
                try:
                    config["chat_monitoring"]["enabled"] = bool(self.chat_monitoring_enabled_var.get())
                except Exception:
                    config["chat_monitoring"]["enabled"] = True

            if hasattr(self, "chat_monitoring_webhook_entry"):
                webhook_name = self.chat_monitoring_webhook_entry.get().strip() or "chat_in_game"
                config["chat_monitoring"]["webhook_name"] = webhook_name

            if hasattr(self, "chat_monitoring_rate_limit_entry"):
                try:
                    rate_limit = int(str(self.chat_monitoring_rate_limit_entry.get()).strip())
                except Exception:
                    rate_limit = int(config["chat_monitoring"].get("rate_limit", 10) or 10)
                config["chat_monitoring"]["rate_limit"] = max(1, rate_limit)

            if hasattr(self, "chat_monitoring_cleanup_days_entry"):
                try:
                    cleanup_days = int(str(self.chat_monitoring_cleanup_days_entry.get()).strip())
                except Exception:
                    cleanup_days = int(config["chat_monitoring"].get("cleanup_days", 7) or 7)
                config["chat_monitoring"]["cleanup_days"] = max(1, cleanup_days)

            channels = []
            if hasattr(self, "chat_channel_global_var") and bool(self.chat_channel_global_var.get()):
                channels.append("Global")
            if hasattr(self, "chat_channel_local_var") and bool(self.chat_channel_local_var.get()):
                channels.append("Local")
            if hasattr(self, "chat_channel_squad_var") and bool(self.chat_channel_squad_var.get()):
                channels.append("Squad")
            if hasattr(self, "chat_channel_admin_var") and bool(self.chat_channel_admin_var.get()):
                channels.append("Admin")
            if not channels:
                channels = ["Global"]
            config["chat_monitoring"]["channels"] = channels

            # Salvar config.json (usar caminho correto)
            config_path = (
                self.DATA_DIR / "config.json"
                if self.IS_EXE
                else self.ROOT_DIR / "data" / "config.json"
            )
            import json

            try:
                from datetime import datetime
                import shutil

                backups_dir = config_path.parent / "backups"
                backups_dir.mkdir(parents=True, exist_ok=True)
                if config_path.exists():
                    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                    backup_path = backups_dir / f"config.json.{ts}.bak"
                    shutil.copy2(config_path, backup_path)
            except Exception:
                pass

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self._add_log_message("✅ Settings saved successfully", "SUCCESS")
            if hasattr(self, "main_apikey_entry") and getattr(self, "apikey_dirty", False):
                self.apikey_dirty = False
                self._set_apikey_status_main("Saved", status="saved")

            import tkinter.messagebox as messagebox

            messagebox.showinfo(
                "Success",
                "Settings saved successfully!\n\nRestart the backend to apply the changes.",
            )

        except Exception as e:
            self._add_log_message(f"Failed to save settings: {e}", "ERROR")
            if self.logger:
                self.logger.error(f"Failed to save settings: {e}")
            import tkinter.messagebox as messagebox

            messagebox.showerror("Error", f"Failed to save settings:\n{str(e)}")

    # ================================================================
    # RCON / Mods support methods
    # ================================================================

    # ================================================================
    # RCON / Mods support methods
    # ================================================================

    def _get_rcon_config_path(self):
        """Retorna o caminho correto para o config.json."""
        if self.IS_EXE:
            return self.DATA_DIR / "config.json"
        return self.ROOT_DIR / "data" / "config.json"

    def _update_provider_info(self):
        """Atualiza o texto descritivo do provedor RCON selecionado."""
        if not hasattr(self, "rcon_provider_info_label") or not hasattr(self, "rcon_provider_var"):
            return
        prov = self.rcon_provider_var.get()
        if prov == "bsbr_scum":
            self.rcon_provider_info_label.configure(
                text=(
                    "BSBR-SCUM (Mazzotti): Mod avançado com suporte a 105 comandos restritos de desenvolvedor\n"
                    "(sudo), entrega direta no inventário/pés ('as <player>'), reflexão em tempo real e porta 27100."
                )
            )
        else:
            self.rcon_provider_info_label.configure(
                text=(
                    "SCUM-RCON (Clássico): Mod legado baseado no protocolo Source RCON (porta 28015).\n"
                    "Executa comandos via console padrão e requer autenticação por senha."
                )
            )

    def _load_rcon_settings(self):
        """Carrega as configurações de RCON do config.json para os campos da aba."""
        try:
            config = self._load_config() or {}
            rcon_cfg = config.get("rcon", {})
            provider = rcon_cfg.get("provider", "bsbr_scum")

            if hasattr(self, "rcon_provider_var"):
                self.rcon_provider_var.set(provider)
                if hasattr(self, "provider_segmented"):
                    if provider == "scum_rcon":
                        self.provider_segmented.set("SCUM-RCON (Clássico)")
                    else:
                        self.provider_segmented.set("BSBR-SCUM (Mazzotti - Avançado)")

            if hasattr(self, "rcon_ip_entry"):
                self.rcon_ip_entry.delete(0, "end")
                self.rcon_ip_entry.insert(0, str(rcon_cfg.get("ip", "127.0.0.1") or "127.0.0.1"))

            if hasattr(self, "rcon_port_entry"):
                default_p = 27100 if provider == "bsbr_scum" else 28015
                self.rcon_port_entry.delete(0, "end")
                self.rcon_port_entry.insert(0, str(rcon_cfg.get("port", default_p) or default_p))

            if hasattr(self, "rcon_password_entry"):
                self.rcon_password_entry.delete(0, "end")
                pwd = str(rcon_cfg.get("password", "") or "")
                if pwd:
                    self.rcon_password_entry.insert(0, pwd)

            if hasattr(self, "rcon_enabled_var"):
                self.rcon_enabled_var.set(bool(rcon_cfg.get("enabled", False)))

            # Carregar configurações de logging
            logging_cfg = rcon_cfg.get("logging", {})
            if hasattr(self, "rcon_log_enabled_var"):
                self.rcon_log_enabled_var.set(bool(logging_cfg.get("enabled", True)))
            if hasattr(self, "rcon_log_auto_clean_var"):
                self.rcon_log_auto_clean_var.set(bool(logging_cfg.get("auto_cleanup", True)))
            if hasattr(self, "rcon_log_retention_entry"):
                self.rcon_log_retention_entry.delete(0, "end")
                self.rcon_log_retention_entry.insert(0, str(logging_cfg.get("retention_days", 7) or 7))

        except Exception as e:
            if self.logger:
                self.logger.error(f"Erro ao carregar configurações RCON: {e}")

    def _save_rcon_settings(self):
        """Salva as configurações de RCON no config.json."""
        import json
        import tkinter.messagebox as messagebox

        try:
            provider = (getattr(self, "rcon_provider_var", None) and self.rcon_provider_var.get()) or "bsbr_scum"
            default_p = 27100 if provider == "bsbr_scum" else 28015
            ip = (getattr(self, "rcon_ip_entry", None) and self.rcon_ip_entry.get().strip()) or "127.0.0.1"
            port_str = (getattr(self, "rcon_port_entry", None) and self.rcon_port_entry.get().strip()) or str(default_p)
            password = (getattr(self, "rcon_password_entry", None) and self.rcon_password_entry.get().strip()) or ""
            enabled = bool(getattr(self, "rcon_enabled_var", None) and self.rcon_enabled_var.get())

            try:
                port = int(port_str)
                if not (1 <= port <= 65535):
                    raise ValueError("Port out of range")
            except ValueError:
                messagebox.showerror("Error", "Invalid RCON port. Must be a number between 1 and 65535.")
                return

            # Configurações de logging
            log_enabled = bool(getattr(self, "rcon_log_enabled_var", None) and self.rcon_log_enabled_var.get())
            log_auto_clean = bool(getattr(self, "rcon_log_auto_clean_var", None) and self.rcon_log_auto_clean_var.get())
            retention_str = (getattr(self, "rcon_log_retention_entry", None) and self.rcon_log_retention_entry.get().strip()) or "7"
            try:
                retention_days = max(1, int(retention_str))
            except ValueError:
                retention_days = 7

            config = self._load_config() or {}
            if "rcon" not in config:
                config["rcon"] = {}
            config["rcon"]["provider"] = provider
            config["rcon"]["enabled"] = enabled
            config["rcon"]["ip"] = ip
            config["rcon"]["port"] = port
            config["rcon"]["password"] = password
            config["rcon"]["logging"] = {
                "enabled": log_enabled,
                "auto_cleanup": log_auto_clean,
                "retention_days": retention_days,
                "max_size_mb": 50,
            }

            config_path = self._get_rcon_config_path()
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            from utils.rcon_logger import RconLogger
            RconLogger.get_instance().load_config(config)

            self._add_log_message("✅ RCON settings saved successfully.", "SUCCESS")

            # Se o mod já estiver instalado, atualizar o config.ini
            binaries_dir = ""
            try:
                binaries_dir = config.get("paths", {}).get("scum_server", {}).get("binaries_directory", "")
            except Exception:
                pass

            if binaries_dir:
                from utils.rcon_mod_manager import RconModManager
                mgr = RconModManager(root_dir=str(self.EXE_DIR), logger=self.logger)
                if mgr.is_installed(binaries_dir, provider=provider):
                    ok, msg = mgr.update_config(
                        binaries_dir=binaries_dir,
                        provider=provider,
                        rcon_ip=ip,
                        rcon_port=port,
                        rcon_password=password,
                    )
                    if ok:
                        self._add_log_message("📝 Mod config.ini updated with new credentials.", "INFO")

            messagebox.showinfo("Saved", "RCON settings saved!\n\nRestart the SCUM server for changes to take effect.")

        except Exception as e:
            self._add_log_message(f"Failed to save RCON settings: {e}", "ERROR")
            if self.logger:
                self.logger.error(f"Failed to save RCON settings: {e}")
            import tkinter.messagebox as messagebox
            messagebox.showerror("Error", f"Failed to save RCON settings:\n{e}")

    def _open_rcon_logs_folder(self):
        """Abre a pasta data/logs/rcon/ no Windows Explorer."""
        from utils.rcon_logger import RconLogger
        rcon_log = RconLogger.get_instance()
        success, message = rcon_log.open_logs_folder_in_explorer()
        if not success:
            self._show_custom_message("Error", message, type_="error")

    def _clean_rcon_logs_now(self):
        """Perform immediate cleanup of old RCON logs."""
        from utils.rcon_logger import RconLogger
        rcon_log = RconLogger.get_instance()
        retention_str = (getattr(self, "rcon_log_retention_entry", None) and self.rcon_log_retention_entry.get().strip()) or "7"
        try:
            r_days = max(1, int(retention_str))
        except ValueError:
            r_days = 7

        deleted_f, freed_b = rcon_log.cleanup_old_logs(retention_days=r_days)
        if deleted_f > 0:
            freed_kb = freed_b / 1024
            msg = f"Cleanup completed successfully!\n\n🗑️ {deleted_f} expired log file(s) removed.\n💾 {freed_kb:.1f} KB freed."
            self._add_log_message(f"🧹 {msg}", "SUCCESS")
            self._show_custom_message("Logs Cleaned", msg, type_="ok")
        else:
            msg = f"No expired log files older than {r_days} day(s) found."
            self._show_custom_message("Logs Up to Date", msg, type_="ok")


    def _test_rcon_connection(self):
        """Test RCON connection in a separate thread and show the result to the user."""
        import threading

        provider = (getattr(self, "rcon_provider_var", None) and self.rcon_provider_var.get()) or "bsbr_scum"
        default_p = 27100 if provider == "bsbr_scum" else 28015
        ip = (getattr(self, "rcon_ip_entry", None) and self.rcon_ip_entry.get().strip()) or "127.0.0.1"
        port_str = (getattr(self, "rcon_port_entry", None) and self.rcon_port_entry.get().strip()) or str(default_p)
        password = (getattr(self, "rcon_password_entry", None) and self.rcon_password_entry.get().strip()) or ""

        try:
            port = int(port_str)
        except ValueError:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Error", "Invalid RCON port.")
            return

        if provider == "scum_rcon" and not password:
            import tkinter.messagebox as messagebox
            messagebox.showwarning("Warning", "Please enter the RCON password before testing SCUM-RCON.")
            return

        self._add_log_message(f"🔌 Testing connection to {provider} at {ip}:{port}...", "INFO")

        def _do_test():
            try:
                if provider == "bsbr_scum":
                    from utils.bsbr_client import BsbrClient
                    client = BsbrClient(host=ip, port=port, password=password, timeout=5.0)
                    resp = client.send_command("players", origin="TEST")
                else:
                    from utils.rcon_client import RconClient
                    client = RconClient(host=ip, port=port, password=password, timeout=5.0)
                    resp = client.send_command("players", origin="TEST")

                def _show_result():
                    from utils.rcon_mod_manager import PROVIDER_NAMES
                    prov_title = PROVIDER_NAMES.get(provider, provider)
                    if resp is not None:
                        self._add_log_message(f"✅ RCON Connection successful! Response: {resp}", "SUCCESS")
                        self._show_custom_message("RCON Connected", f"Connection successful!\n\nEngine: {prov_title}\nHost: {ip}:{port}\n\nResponse:\n{resp}")
                    else:
                        self._add_log_message("❌ Failed to connect to RCON.", "ERROR")
                        self._show_custom_message("RCON Error", f"Failed to connect to {prov_title} at {ip}:{port}.\nCheck if the server is running and port is correct.", type_="error")

                self.after(0, _show_result)
            except Exception:
                pass

        threading.Thread(target=_do_test, daemon=True).start()

    def _show_custom_message(self, title: str, message: str, type_: str = "ok") -> bool:
        """
        Shows a modern, English-only CustomTkinter message dialog centered on MainWindow.
        type_: "ok", "yesno", "warning", "error"
        Returns: True if OK/Yes clicked, False otherwise.
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        # Ensure window is in front and focused
        dialog.lift()
        dialog.focus_force()
        dialog.attributes("-topmost", True)
        dialog.after(100, lambda: dialog.attributes("-topmost", False))

        # Dynamic calculation of dialog size based on content
        lines = message.splitlines()
        line_count = len(lines) if lines else 1
        max_line_len = max(len(l) for l in lines) if lines else 20

        # Calculate dynamic dimensions
        width = min(540, max(440, max_line_len * 7 + 80))
        calculated_height = max(80, min(300, line_count * 20 + 30))
        height = calculated_height + 100

        self.update_idletasks()
        px = self.winfo_x()
        py = self.winfo_y()
        pw = self.winfo_width()
        ph = self.winfo_height()
        x = px + (pw // 2) - (width // 2)
        y = py + (ph // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

        result = [False]

        def on_yes():
            result[0] = True
            dialog.destroy()

        def on_no():
            result[0] = False
            dialog.destroy()

        # Main frame
        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=(15, 12))

        # Content Area - If tall or long, use a clean scrollable box
        if line_count > 7 or len(message) > 280:
            content_box = ctk.CTkScrollableFrame(
                container,
                height=min(220, calculated_height),
                fg_color=("gray90", "gray18"),
                corner_radius=8,
            )
            content_box.pack(fill="both", expand=True, pady=(0, 12))
            label = ctk.CTkLabel(
                content_box,
                text=message,
                wraplength=width - 90,
                justify="left",
                font=ctk.CTkFont(family="Consolas" if ("|" in message or "{" in message) else "Segoe UI", size=12),
                anchor="w",
            )
            label.pack(fill="both", expand=True, padx=10, pady=8)
        else:
            label = ctk.CTkLabel(
                container,
                text=message,
                wraplength=width - 50,
                justify="left",
                font=ctk.CTkFont(family="Segoe UI", size=13),
            )
            label.pack(fill="both", expand=True, pady=(0, 12))

        # Buttons
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom")

        if type_ == "yesno":
            btn_no = ctk.CTkButton(
                btn_frame,
                text="No",
                width=80,
                height=30,
                fg_color="#4a4a4a",
                hover_color="#5a5a5a",
                command=on_no,
            )
            btn_no.pack(side="right", padx=(6, 0))

            btn_yes = ctk.CTkButton(
                btn_frame,
                text="Yes",
                width=80,
                height=30,
                fg_color="#1f538d",
                hover_color="#2b74c7",
                command=on_yes,
            )
            btn_yes.pack(side="right")
        else:
            # "ok", "warning", "error"
            btn_ok = ctk.CTkButton(
                btn_frame,
                text="OK",
                width=85,
                height=30,
                fg_color="#1f538d",
                hover_color="#2b74c7",
                command=on_yes,
            )
            btn_ok.pack(side="right")

        dialog.bind("<Return>", lambda e: on_yes())
        dialog.bind("<Escape>", lambda e: on_no())

        # Wait until dialog is closed
        self.wait_window(dialog)
        return result[0]


    def _refresh_rcon_mod_status(self):
        """Atualiza o label de status e detalhes do mod RCON ativo na GUI."""
        try:
            config = self._load_config() or {}
            binaries_dir = config.get("paths", {}).get("scum_server", {}).get("binaries_directory", "")

            if not binaries_dir:
                if hasattr(self, "rcon_mod_badge_label"):
                    self.rcon_mod_badge_label.configure(
                        text="⚠️ Binaries not set",
                        text_color="orange",
                    )
                return

            from utils.rcon_mod_manager import RconModManager, PROVIDER_NAMES
            mgr = RconModManager(root_dir=str(self.EXE_DIR), logger=self.logger)
            installed_prov = mgr.get_installed_provider(binaries_dir)

            if installed_prov:
                prov_title = PROVIDER_NAMES.get(installed_prov, installed_prov.replace("_", " ").title())
                if hasattr(self, "rcon_mod_badge_label"):
                    self.rcon_mod_badge_label.configure(
                        text=f"🟢 {prov_title} • Active",
                        text_color="#4CAF50",
                    )
                if hasattr(self, "rcon_provider_var"):
                    self.rcon_provider_var.set(installed_prov)
            else:
                if hasattr(self, "rcon_mod_badge_label"):
                    self.rcon_mod_badge_label.configure(
                        text="⚪ Not Installed",
                        text_color="#F44336",
                    )
        except Exception as e:
            if hasattr(self, "rcon_mod_badge_label"):
                self.rcon_mod_badge_label.configure(
                    text=f"⚠️ Error: {e}",
                    text_color="orange",
                )

    def _select_and_install_rcon_dialog(self):
        """Abre o diálogo de seleção e instalação modular de provedores RCON."""
        import customtkinter as ctk
        import tkinter.messagebox as messagebox
        from utils.rcon_mod_manager import (
            RconModManager,
            PROVIDER_BSBR,
            PROVIDER_SCUM_RCON,
            PROVIDER_NAMES,
            DEFAULT_PORTS,
        )

        config = self._load_config() or {}
        binaries_dir = config.get("paths", {}).get("scum_server", {}).get("binaries_directory", "")
        if not binaries_dir or not Path(binaries_dir).is_dir():
            messagebox.showerror(
                "Binaries Not Found",
                "SCUM server binaries directory is not configured.\n"
                "Please configure 'Binaries Directory' in General Settings first.",
            )
            return

        mgr = RconModManager(root_dir=str(self.EXE_DIR), logger=self.logger)
        current_prov = mgr.get_installed_provider(binaries_dir) or config.get("rcon", {}).get("provider", PROVIDER_BSBR)

        dialog = ctk.CTkToplevel(self)
        dialog.title("Select & Install RCON Engine")
        dialog.geometry("540x480")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        try:
            dialog.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() // 2) - (540 // 2)
            y = self.winfo_y() + (self.winfo_height() // 2) - (480 // 2)
            dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            content,
            text="📦 Select RCON Engine",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", pady=(0, 6))

        ctk.CTkLabel(
            content,
            text="Choose which RCON provider to install and activate in your SCUM Server.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(anchor="w", pady=(0, 15))

        selected_prov_var = ctk.StringVar(value=current_prov)

        # Card 1: BSBR-SCUM
        card_bsbr = ctk.CTkFrame(content, fg_color=("gray90", "gray20"), corner_radius=8)
        card_bsbr.pack(fill="x", pady=(0, 10))

        r_bsbr = ctk.CTkRadioButton(
            card_bsbr,
            text="BSBR-SCUM (Mazzotti - Advanced)",
            variable=selected_prov_var,
            value=PROVIDER_BSBR,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        r_bsbr.pack(anchor="w", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            card_bsbr,
            text="• Port: 27100 (Local TCP socket, no password)\n"
                 "• Direct deliveries with 'sudo' support for all players\n"
                 "• Fast reflection command queries ('players', 'vehicles')\n"
                 "• No chat spam for admins during automated syncs",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=32, pady=(0, 10))

        # Card 2: SCUM-RCON
        card_rcon = ctk.CTkFrame(content, fg_color=("gray90", "gray20"), corner_radius=8)
        card_rcon.pack(fill="x", pady=(0, 15))

        r_rcon = ctk.CTkRadioButton(
            card_rcon,
            text="SCUM-RCON (Classic)",
            variable=selected_prov_var,
            value=PROVIDER_SCUM_RCON,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        r_rcon.pack(anchor="w", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            card_rcon,
            text="• Port: 28015 (Source RCON Protocol with Password)\n"
                 "• Full admin console execution\n"
                 "• Compatible with external RCON tools (mcrcon, bot dashboards)",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=32, pady=(0, 10))

        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        def _do_install():
            chosen = selected_prov_var.get()
            port = DEFAULT_PORTS.get(chosen, 27100)
            pwd = (getattr(self, "rcon_password_entry", None) and self.rcon_password_entry.get().strip()) or config.get("rcon", {}).get("password", "181917")
            ip = (getattr(self, "rcon_ip_entry", None) and self.rcon_ip_entry.get().strip()) or "127.0.0.1"

            ok, msg = mgr.install(
                binaries_dir=binaries_dir,
                provider=chosen,
                rcon_ip=ip,
                rcon_port=port,
                rcon_password=pwd,
            )

            if ok:
                cfg = self._load_config() or {}
                if "rcon" not in cfg:
                    cfg["rcon"] = {}
                cfg["rcon"]["provider"] = chosen
                cfg["rcon"]["port"] = port
                cfg["rcon"]["enabled"] = True
                cfg_path = self._get_rcon_config_path()
                try:
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

                self._load_rcon_settings()
                self._refresh_rcon_mod_status()
                dialog.destroy()
                messagebox.showinfo("Success", f"{PROVIDER_NAMES.get(chosen, chosen)} installed successfully!\n\nPlease restart the SCUM Server to load the engine.")
            else:
                messagebox.showerror("Installation Error", msg)

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            command=dialog.destroy,
            width=100,
            height=35,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
        ).pack(side="left")

        ctk.CTkButton(
            btn_row,
            text="🚀 Install / Activate",
            command=_do_install,
            width=160,
            height=35,
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="right")

    def _open_rcon_mods_folder(self):
        """Abre a pasta ue4ss/Mods no Windows Explorer."""
        import os
        import tkinter.messagebox as messagebox
        config = self._load_config() or {}
        binaries_dir = config.get("paths", {}).get("scum_server", {}).get("binaries_directory", "")
        if not binaries_dir:
            messagebox.showerror("Error", "Binaries directory not set in config.")
            return

        mods_dir = Path(binaries_dir) / "ue4ss" / "Mods"
        if not mods_dir.is_dir():
            mods_dir = Path(binaries_dir)

        try:
            os.startfile(str(mods_dir))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {e}")

    def _uninstall_rcon_mod(self):
        """Desinstala o mod RCON atualmente instalado."""
        import tkinter.messagebox as messagebox
        from utils.rcon_mod_manager import RconModManager

        config = self._load_config() or {}
        binaries_dir = config.get("paths", {}).get("scum_server", {}).get("binaries_directory", "")
        if not binaries_dir:
            messagebox.showerror("Error", "Binaries directory not set in config.")
            return

        confirm = messagebox.askyesno(
            "Uninstall RCON Mod",
            "Are you sure you want to uninstall the active RCON mod from your SCUM server?\n\n"
            "The server should be stopped before uninstalling.",
        )
        if not confirm:
            return

        mgr = RconModManager(root_dir=str(self.EXE_DIR), logger=self.logger)
        ok, msg = mgr.uninstall(binaries_dir=binaries_dir)
        if ok:
            self._refresh_rcon_mod_status()
            messagebox.showinfo("Uninstalled", "RCON mod removed successfully.")
        else:
            messagebox.showerror("Uninstall Error", msg)

    def _execute_rcon_console_command(self, event=None):
        """Executa um comando RCON digitado no console de testes e exibe a resposta em tempo real."""
        if not hasattr(self, "rcon_cmd_entry") or not hasattr(self, "rcon_console_textbox"):
            return


        cmd = self.rcon_cmd_entry.get().strip()
        if not cmd:
            return

        # ─── Proteção contra '#' no painel RCON ───
        if cmd.startswith("#"):
            ts = datetime.now().strftime("%H:%M:%S")
            clean_cmd = cmd.lstrip("#").strip()
            self._append_rcon_console_text(
                f"[{ts}] > {cmd}\n"
                f"[{ts}] ⚠️ Warning: Do NOT use '#' in the RCON panel. The '#' prefix is only used in-game chat.\n"
                f"[{ts}] 💡 Suggested command: {clean_cmd}\n\n"
            )
            self.rcon_cmd_entry.delete(0, "end")
            self.rcon_cmd_entry.insert(0, clean_cmd)
            return

        self.rcon_cmd_entry.delete(0, "end")

        ip = (getattr(self, "rcon_ip_entry", None) and self.rcon_ip_entry.get().strip()) or "127.0.0.1"
        port_str = (getattr(self, "rcon_port_entry", None) and self.rcon_port_entry.get().strip()) or "27100"
        password = (getattr(self, "rcon_password_entry", None) and self.rcon_password_entry.get().strip()) or ""
        provider = (getattr(self, "rcon_provider_var", None) and self.rcon_provider_var.get()) or "bsbr_scum"

        try:
            port = int(port_str)
        except ValueError:
            port = 27100 if provider == "bsbr_scum" else 28015

        ts = datetime.now().strftime("%H:%M:%S")
        self.rcon_console_textbox.insert("end", f"[{ts}] > {cmd}\n")
        self.rcon_console_textbox.see("end")

        def _do_send():
            import time
            start = time.perf_counter()
            try:
                if provider == "bsbr_scum":
                    from utils.bsbr_client import BsbrClient
                    client = BsbrClient(host=ip, port=port, timeout=5.0)
                    resp = client.send_command(cmd, origin="CONSOLE")
                else:
                    from utils.rcon_client import RconClient
                    client = RconClient(host=ip, port=port, password=password, timeout=5.0)
                    resp = client.send_command(cmd, origin="CONSOLE")

                duration_ms = (time.perf_counter() - start) * 1000.0
                out_ts = datetime.now().strftime("%H:%M:%S")
                if resp:
                    out_text = f"[{out_ts}] ({duration_ms:.1f}ms) {resp}\n\n"
                else:
                    out_text = f"[{out_ts}] ({duration_ms:.1f}ms) (Executed / No response)\n\n"

                self.after(0, lambda: self._append_rcon_console_text(out_text))
            except Exception as e:
                out_ts = datetime.now().strftime("%H:%M:%S")
                err_text = f"[{out_ts}] [ERROR] {e}\n\n"
                self.after(0, lambda: self._append_rcon_console_text(err_text))

        threading.Thread(target=_do_send, daemon=True).start()

    def _append_rcon_console_text(self, text: str):
        """Adiciona texto à caixa de terminal do console RCON."""
        if hasattr(self, "rcon_console_textbox"):
            self.rcon_console_textbox.insert("end", text)
            self.rcon_console_textbox.see("end")

    def _clear_rcon_console(self):
        """Clears the RCON console terminal."""
        if hasattr(self, "rcon_console_textbox"):
            self.rcon_console_textbox.delete("1.0", "end")
            self.rcon_console_textbox.insert("1.0", "--- RCON Terminal Cleared ---\n\n")

    def _set_and_send_rcon_quick_command(self, cmd: str):
        """Preenche e opcionalmente dispara um comando rápido de preset no console RCON."""
        if not hasattr(self, "rcon_cmd_entry"):
            return
        self.rcon_cmd_entry.delete(0, "end")
        self.rcon_cmd_entry.insert(0, cmd)
        if "..." not in cmd and not cmd.endswith(" "):
            self._execute_rcon_console_command()
        else:
            self.rcon_cmd_entry.focus()



    def _open_rcon_mods_folder(self):
        """Abre a pasta data/mods/rcon/ no Windows Explorer."""
        import os, sys, subprocess
        rcon_dir = self.DATA_DIR / "mods" / "rcon" if self.IS_EXE else self.ROOT_DIR / "data" / "mods" / "rcon"
        rcon_dir.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(rcon_dir))
            else:
                subprocess.Popen(["xdg-open", str(rcon_dir)])
        except Exception as e:
            self._show_custom_message("Error", f"Failed to open folder: {e}", type_="error")

    def _select_and_install_rcon_dialog(self):
        """Abre uma janela para selecionar qual mod RCON instalar a partir de data/mods/rcon/ ou pasta customizada."""
        from tkinter import filedialog
        from utils.rcon_mod_manager import RconModManager, PROVIDER_NAMES, DEFAULT_PORTS

        if getattr(self, "server_running", False) or getattr(self, "backend_running", False):
            self._show_custom_message(
                "Server is Running",
                "⚠️ The SCUM Server is currently running.\n\n"
                "Please STOP the server before installing or switching RCON mods.\n"
                "This is required because the server locks the application files while running.",
                type_="warning"
            )
            return

        config = self._load_config() or {}
        binaries_dir = config.get("paths", {}).get("scum_server", {}).get("binaries_directory", "")
        if not binaries_dir:
            self._show_custom_message(
                "Error",
                "Binaries directory is not configured.\n\n"
                "Go to the General tab and set the 'Binaries Directory' path first.",
                type_="error"
            )
            return

        mgr = RconModManager(root_dir=str(self.EXE_DIR), logger=self.logger)
        available_mods = mgr.get_available_providers()

        dialog = ctk.CTkToplevel(self)
        dialog.title("Select RCON Engine to Install")
        dialog.geometry("520x420")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - 260
            y = self.winfo_y() + (self.winfo_height() // 2) - 210
            dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        ctk.CTkLabel(
            dialog,
            text="📦 Select RCON Engine",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(padx=20, pady=(20, 5), anchor="w")

        ctk.CTkLabel(
            dialog,
            text="Choose one of the available engines from data/mods/rcon/ or select an external folder:",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
            wraplength=480,
            justify="left",
        ).pack(padx=20, pady=(0, 15), anchor="w")

        selected_provider_var = ctk.StringVar(value=available_mods[0]["id"] if available_mods else "bsbr_scum")
        custom_path_var = ctk.StringVar(value="")

        mods_list_frame = ctk.CTkScrollableFrame(dialog, height=160, fg_color=("gray90", "gray20"), corner_radius=8)
        mods_list_frame.pack(fill="x", padx=20, pady=(0, 12))

        for mod in available_mods:
            mod_id = mod["id"]
            mod_name = mod["name"]
            port = mod.get("default_port", 27100)

            row = ctk.CTkFrame(mods_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=4, padx=5)

            rb = ctk.CTkRadioButton(
                row,
                text=f"{mod_name}  (Default port: {port})",
                variable=selected_provider_var,
                value=mod_id,
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            rb.pack(side="left", padx=5)

        # Opção de selecionar pasta externa
        browse_row = ctk.CTkFrame(dialog, fg_color="transparent")
        browse_row.pack(fill="x", padx=20, pady=(0, 15))

        def _on_browse():
            rcon_base = self.DATA_DIR / "mods" / "rcon" if self.IS_EXE else self.ROOT_DIR / "data" / "mods" / "rcon"
            chosen = filedialog.askdirectory(
                title="Select Custom RCON Mod Folder",
                initialdir=str(rcon_base) if rcon_base.is_dir() else str(self.ROOT_DIR),
            )
            if chosen:
                custom_path_var.set(chosen)
                folder_name = Path(chosen).name
                selected_provider_var.set(folder_name)
                lbl_custom.configure(text=f"📁 {folder_name}")

        btn_browse = ctk.CTkButton(
            browse_row,
            text="📁 Browse Another Folder...",
            command=_on_browse,
            width=180,
            height=32,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            font=ctk.CTkFont(size=12),
        )
        btn_browse.pack(side="left")

        lbl_custom = ctk.CTkLabel(
            browse_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray70"),
        )
        lbl_custom.pack(side="left", padx=(10, 0))

        # Bottom buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 20), side="bottom")

        def _confirm_install():
            choice = selected_provider_var.get()
            dialog.destroy()
            self._do_install_chosen_rcon(choice, custom_dir=custom_path_var.get() or None)

        ctk.CTkButton(
            btn_frame,
            text="Install & Activate",
            command=_confirm_install,
            width=150,
            height=36,
            fg_color=("#1565C0", "#1565C0"),
            hover_color=("#0D47A1", "#0D47A1"),
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            width=100,
            height=36,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            font=ctk.CTkFont(size=12),
        ).pack(side="right")

    def _do_install_chosen_rcon(self, provider: str, custom_dir: Optional[str] = None):
        """Instala o mod RCON selecionado pelo usuário."""
        import threading
        from utils.rcon_mod_manager import PROVIDER_NAMES, DEFAULT_PORTS

        config = self._load_config() or {}
        binaries_dir = config.get("paths", {}).get("scum_server", {}).get("binaries_directory", "")
        if not binaries_dir:
            return

        ip = (getattr(self, "rcon_ip_entry", None) and self.rcon_ip_entry.get().strip()) or "127.0.0.1"
        default_p = DEFAULT_PORTS.get(provider, 27100)
        password = (getattr(self, "rcon_password_entry", None) and self.rcon_password_entry.get().strip()) or ""

        # Auto-update port field to match selected mod's default port
        if hasattr(self, "rcon_port_entry"):
            self.rcon_port_entry.delete(0, "end")
            self.rcon_port_entry.insert(0, str(default_p))
            port = default_p
        else:
            port = default_p

        prov_title = PROVIDER_NAMES.get(provider, provider.replace("_", " ").title())
        self._add_log_message(f"📦 Installing {prov_title}...", "INFO")

        if hasattr(self, "btn_select_rcon_mod"):
            self.btn_select_rcon_mod.configure(state="disabled", text="Installing...")

        def _bg():
            from utils.rcon_mod_manager import RconModManager
            mgr = RconModManager(root_dir=str(self.EXE_DIR), logger=self.logger)
            success, message = mgr.install(
                binaries_dir=binaries_dir,
                provider=provider,
                rcon_ip=ip,
                rcon_port=port,
                rcon_password=password,
            )

            if success:
                try:
                    cfg = self._load_config() or {}
                    if "rcon" not in cfg:
                        cfg["rcon"] = {}
                    cfg["rcon"]["provider"] = provider
                    cfg["rcon"]["port"] = port
                    import json
                    cfg_path = self._get_rcon_config_path()
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

            def _on_done():
                if hasattr(self, "btn_select_rcon_mod"):
                    self.btn_select_rcon_mod.configure(state="normal", text="📦 Select Engine")


                if success:
                    self._add_log_message(f"✅ {message}", "SUCCESS")
                    self._show_custom_message("RCON Installed", f"✅ {message}", type_="ok")
                else:
                    self._add_log_message(f"❌ Installation failed: {message}", "ERROR")
                    self._show_custom_message("Installation Failed", f"❌ {message}", type_="error")

                self._refresh_rcon_mod_status()

            try:
                self.after(0, _on_done)
            except Exception:
                pass

        threading.Thread(target=_bg, daemon=True).start()

    def _uninstall_rcon_mod(self):
        """Remove o provedor RCON ativo do servidor SCUM."""
        import threading

        if getattr(self, "server_running", False) or getattr(self, "backend_running", False):
            self._show_custom_message(
                "Server is Running",
                "⚠️ The SCUM Server is currently running.\n\n"
                "Please STOP the server before uninstalling mods.\n"
                "This is required because the server locks the application files while running.",
                type_="warning"
            )
            return

        config = self._load_config() or {}
        binaries_dir = config.get("paths", {}).get("scum_server", {}).get("binaries_directory", "")

        if not binaries_dir:
            self._show_custom_message("Error", "Binaries directory is not configured.", type_="error")
            return

        from utils.rcon_mod_manager import RconModManager, PROVIDER_NAMES
        mgr = RconModManager(root_dir=str(self.EXE_DIR), logger=self.logger)
        installed_prov = mgr.get_installed_provider(binaries_dir)

        if not installed_prov:
            self._show_custom_message("Info", "No RCON engine is currently installed.", type_="info")
            return

        prov_title = PROVIDER_NAMES.get(installed_prov, installed_prov)

        confirm = self._show_custom_message(
            f"Uninstall {prov_title}",
            f"This will uninstall {prov_title} from the SCUM server.\n\n"
            "Are you sure?",
            type_="yesno"
        )
        if not confirm:
            return

        self._add_log_message(f"🗑️ Uninstalling {prov_title}...", "INFO")

        if hasattr(self, "btn_uninstall_rcon_mod"):
            self.btn_uninstall_rcon_mod.configure(state="disabled", text="Uninstalling...")

        def _do_uninstall():
            success, message = mgr.uninstall(binaries_dir=binaries_dir, provider=installed_prov)

            def _on_done():
                if hasattr(self, "btn_uninstall_rcon_mod"):
                    self.btn_uninstall_rcon_mod.configure(state="normal", text="🗑️ Uninstall Engine")

                if success:
                    self._add_log_message(f"✅ {message}", "SUCCESS")
                    self._show_custom_message("Engine Uninstalled", f"✅ {message}", type_="ok")
                else:
                    self._add_log_message(f"❌ Uninstall failed: {message}", "ERROR")
                    self._show_custom_message("Uninstall Failed", f"❌ {message}", type_="error")

                self._refresh_rcon_mod_status()

            try:
                self.after(0, _on_done)
            except Exception:
                pass

        threading.Thread(target=_do_uninstall, daemon=True).start()


    # ================================================================
    # Content Mods (.PAK Manager) methods
    # ================================================================

    def _get_scum_root_dir(self) -> str:
        """Resolve a pasta raiz do servidor SCUM a partir da configuração."""
        config = self._load_config() or {}
        paths = config.get("paths", {}).get("scum_server", {})
        root_dir = paths.get("root_directory", "")
        if root_dir and Path(root_dir).is_dir():
            return root_dir
        bin_dir = paths.get("binaries_directory", "")
        if bin_dir and Path(bin_dir).is_dir():
            p = Path(bin_dir)
            if p.name.lower() == "win64":
                return str(p.parent.parent.parent)
            return str(p.parent)
        return ""

    def _get_pak_mod_manager(self):
        """Retorna uma instância configurada do PakModManager com diretório base seguro."""
        from utils.pak_mod_manager import PakModManager
        return PakModManager(root_dir=str(self.EXE_DIR), logger=self.logger)

    def _refresh_pak_mods_list(self):
        """Recarrega a lista visual de mods .pak na tabela."""
        if not hasattr(self, "pak_mods_list_frame"):
            return

        for child in self.pak_mods_list_frame.winfo_children():
            child.destroy()

        scum_root = self._get_scum_root_dir()
        if not scum_root:
            ctk.CTkLabel(
                self.pak_mods_list_frame,
                text="⚠️ SCUM server directory is not configured in General tab.",
                font=ctk.CTkFont(size=12),
                text_color="orange",
            ).pack(pady=12, padx=10)
            return

        mgr = self._get_pak_mod_manager()
        mods = mgr.list_mods(scum_root)

        if not mods:
            empty_frame = ctk.CTkFrame(self.pak_mods_list_frame, fg_color="transparent")
            empty_frame.pack(fill="x", pady=12, padx=10)
            ctk.CTkLabel(
                empty_frame,
                text="📁 No .pak mods found in Content/Paks/~mods/ folder.",
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray70"),
            ).pack(side="left")
            return


        # Table Header
        header_row = ctk.CTkFrame(self.pak_mods_list_frame, fg_color=("gray85", "gray25"), height=30)
        header_row.pack(fill="x", padx=5, pady=(5, 2))

        ctk.CTkLabel(
            header_row, text="Mod File", font=ctk.CTkFont(size=11, weight="bold"), anchor="w"
        ).pack(side="left", fill="x", expand=True, padx=(10, 5))

        ctk.CTkLabel(
            header_row, text="Size", font=ctk.CTkFont(size=11, weight="bold"), width=80, anchor="e"
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            header_row, text="Status", font=ctk.CTkFont(size=11, weight="bold"), width=90, anchor="center"
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            header_row, text="Actions", font=ctk.CTkFont(size=11, weight="bold"), width=140, anchor="center"
        ).pack(side="left", padx=(5, 10))

        # Mod Rows
        for mod in mods:
            row = ctk.CTkFrame(self.pak_mods_list_frame, fg_color="transparent", height=34)
            row.pack(fill="x", padx=5, pady=2)

            fname = mod["filename"]
            is_active = mod["is_active"]

            ctk.CTkLabel(
                row,
                text=f"📦 {mod['display_name']}",
                font=ctk.CTkFont(size=11),
                anchor="w",
            ).pack(side="left", fill="x", expand=True, padx=(10, 5))

            ctk.CTkLabel(
                row,
                text=mod["size_formatted"],
                font=ctk.CTkFont(size=11),
                width=80,
                anchor="e",
            ).pack(side="left", padx=5)

            status_text = "🟢 Active" if is_active else "⚪ Inactive"
            status_color = "#4CAF50" if is_active else "gray"
            ctk.CTkLabel(
                row,
                text=status_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=status_color,
                width=90,
                anchor="center",
            ).pack(side="left", padx=5)

            actions_box = ctk.CTkFrame(row, fg_color="transparent", width=140)
            actions_box.pack(side="left", padx=(5, 10))

            btn_toggle_txt = "Disable" if is_active else "Enable"
            btn_toggle_color = ("#D32F2F", "#D32F2F") if is_active else ("#2E7D32", "#2E7D32")

            ctk.CTkButton(
                actions_box,
                text=btn_toggle_txt,
                command=lambda f=fname: self._toggle_pak_mod(f),
                width=75,
                height=26,
                fg_color=btn_toggle_color,
                font=ctk.CTkFont(size=10, weight="bold"),
            ).pack(side="left", padx=(0, 4))

            ctk.CTkButton(
                actions_box,
                text="🗑️",
                command=lambda f=fname: self._delete_pak_mod(f),
                width=30,
                height=26,
                fg_color=("gray75", "gray35"),
                hover_color=("#B71C1C", "#B71C1C"),
                font=ctk.CTkFont(size=11),
            ).pack(side="left")

    def _install_pak_mod(self):
        """Abre seletor de arquivo e instala um novo mod .pak."""
        from tkinter import filedialog

        scum_root = self._get_scum_root_dir()
        if not scum_root:
            self._show_custom_message("Error", "SCUM Server path is not configured.", type_="error")
            return

        file_path = filedialog.askopenfilename(
            title="Select SCUM .pak Mod",
            filetypes=[("Unreal Pak Files (*.pak)", "*.pak"), ("All Files (*.*)", "*.*")],
        )
        if not file_path:
            return

        mgr = self._get_pak_mod_manager()
        success, message = mgr.install_pak(scum_root, file_path)

        if success:
            self._add_log_message(f"✅ {message}", "SUCCESS")
            self._show_custom_message("Mod Installed", f"✅ {message}", type_="ok")
        else:
            self._add_log_message(f"❌ {message}", "ERROR")
            self._show_custom_message("Installation Error", f"❌ {message}", type_="error")

        self._refresh_pak_mods_list()

    def _toggle_pak_mod(self, filename: str):
        """Alterna ativação do mod .pak."""
        scum_root = self._get_scum_root_dir()
        if not scum_root:
            return

        mgr = self._get_pak_mod_manager()
        success, message = mgr.toggle_pak(scum_root, filename)

        if success:
            self._add_log_message(f"🔄 {message}", "INFO")
        else:
            self._add_log_message(f"❌ {message}", "ERROR")

        self._refresh_pak_mods_list()

    def _delete_pak_mod(self, filename: str):
        """Exclui um mod .pak após confirmação."""
        scum_root = self._get_scum_root_dir()
        if not scum_root:
            return

        confirm = self._show_custom_message(
            "Delete Mod",
            f"Are you sure you want to permanently delete:\n{filename}?",
            type_="yesno"
        )
        if not confirm:
            return

        mgr = self._get_pak_mod_manager()
        success, message = mgr.delete_pak(scum_root, filename)

        if success:
            self._add_log_message(f"🗑️ {message}", "INFO")
            self._show_custom_message("Mod Deleted", f"✅ {message}", type_="ok")
        else:
            self._add_log_message(f"❌ {message}", "ERROR")
            self._show_custom_message("Delete Error", f"❌ {message}", type_="error")

        self._refresh_pak_mods_list()

    def _open_pak_mods_folder(self):
        """Abre a pasta mods do servidor no Windows Explorer."""
        scum_root = self._get_scum_root_dir()
        if not scum_root:
            self._show_custom_message("Error", "SCUM Server path is not configured.", type_="error")
            return

        mgr = self._get_pak_mod_manager()
        success, message = mgr.open_mods_folder_in_explorer(scum_root)
        if not success:
            self._show_custom_message("Error", message, type_="error")

    def _open_pak_safe_storage(self):
        """Abre a pasta de armazenamento seguro data/mods/paks/ no Windows Explorer."""
        mgr = self._get_pak_mod_manager()
        success, message = mgr.open_safe_storage_in_explorer()
        if not success:
            self._show_custom_message("Error", message, type_="error")



    def _apply_nssm_shutdown_preset(self):
        try:
            self._add_log_message(
                "Applying NSSM shutdown preset (may prompt UAC)...", "INFO"
            )

            import tkinter.messagebox as messagebox

            if not HAS_REQUESTS:
                messagebox.showerror(
                    "Error",
                    "The 'requests' package is not available. Install dependencies and try again.",
                )
                return

            resp = None
            data = None
            try:
                resp = requests.post(
                    "http://127.0.0.1:3000/api/server/nssm/apply_shutdown_preset",
                    json={},
                    timeout=30,
                )
                try:
                    data = resp.json()
                except Exception:
                    data = {"success": False, "message": (resp.text or "").strip()}
            except Exception as http_err:
                # Fallback: a GUI pode estar rodando com o backend parado.
                # Aplicar preset diretamente via ServerManager.
                self._add_log_message(
                    f"Backend API not reachable (using local fallback): {http_err}",
                    "WARNING",
                )
                from utils.config_path_helper import ConfigPathHelper

                cfg = self._load_config() or {}
                path_helper = ConfigPathHelper(cfg)
                local_sm = ServerManager(cfg.get("server", {}), path_helper)
                data = local_sm.apply_nssm_shutdown_preset()
                resp = None

            http_ok = (
                resp is not None
                and 200 <= int(getattr(resp, "status_code", 0) or 0) < 300
            )
            if (http_ok or resp is None) and (data or {}).get("success"):
                self._add_log_message("✅ NSSM preset applied successfully", "SUCCESS")
                messagebox.showinfo(
                    "Success",
                    "NSSM shutdown preset applied successfully.\n\n"
                    "Stop the server once to confirm the SCUM log closes cleanly.",
                )
                return

            msg = (
                data.get("message")
                or data.get("error")
                or "Failed to apply NSSM preset"
            )
            out = data.get("output")
            if out:
                msg = f"{msg}\n\n{out}"
            status = data.get("status")
            if status:
                msg = f"{msg}\n\nstatus: {status}"
            mismatches = data.get("mismatches")
            if isinstance(mismatches, dict) and mismatches:
                lines = []
                for k, v in mismatches.items():
                    if isinstance(v, dict):
                        lines.append(
                            f"- {k}: expected={v.get('expected')} readback={v.get('readback')}"
                        )
                    else:
                        lines.append(f"- {k}: {v}")
                msg = f"{msg}\n\nMismatches:\n" + "\n".join(lines)
            self._add_log_message(f"❌ Failed to apply NSSM preset: {msg}", "ERROR")
            messagebox.showerror(
                "Error",
                "Failed to apply NSSM shutdown preset.\n\n"
                f"{msg}\n\n"
                "Try running SSM as Administrator or allow the UAC prompt.",
            )
        except Exception as e:
            try:
                self._add_log_message(f"❌ Failed to apply NSSM preset: {e}", "ERROR")
            except Exception:
                pass
            import tkinter.messagebox as messagebox

            messagebox.showerror("Error", f"Failed to apply NSSM preset:\n{str(e)}")

    def _ask_yes_no_english(self, *, title: str, message: str) -> bool:
        import tkinter as tk

        result = {"value": False}
        win = tk.Toplevel(self)
        win.title(title)
        try:
            win.resizable(False, False)
        except Exception:
            pass

        try:
            win.transient(self)
            win.grab_set()
        except Exception:
            pass

        frm = tk.Frame(win, padx=16, pady=14)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text=message, justify="left", anchor="w").pack(
            fill="both", expand=True
        )

        btns = tk.Frame(frm)
        btns.pack(fill="x", pady=(12, 0))

        def _no():
            try:
                win.destroy()
            except Exception:
                pass

        def _yes():
            result["value"] = True
            try:
                win.destroy()
            except Exception:
                pass

        tk.Button(btns, text="No", width=10, command=_no).pack(side="right", padx=(8, 0))
        tk.Button(btns, text="Yes", width=10, command=_yes).pack(side="right")

        try:
            win.update_idletasks()
            w = int(win.winfo_reqwidth())
            h = int(win.winfo_reqheight())
            px = int(self.winfo_rootx())
            py = int(self.winfo_rooty())
            pw = int(self.winfo_width())
            ph = int(self.winfo_height())
            x = int(px + (pw / 2) - (w / 2))
            y = int(py + (ph / 2) - (h / 2))
            if x < 0:
                x = 0
            if y < 0:
                y = 0
            win.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        try:
            win.wait_window()
        except Exception:
            pass
        return bool(result.get("value"))

    def _ask_yes_no_cancel_english(
        self, *, title: str, message: str
    ) -> Optional[bool]:
        import tkinter as tk

        result: Dict[str, Optional[bool]] = {"value": None}
        win = tk.Toplevel(self)
        win.title(title)
        try:
            win.resizable(False, False)
        except Exception:
            pass

        try:
            win.transient(self)
            win.grab_set()
        except Exception:
            pass

        frm = tk.Frame(win, padx=16, pady=14)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text=message, justify="left", anchor="w").pack(
            fill="both", expand=True
        )

        btns = tk.Frame(frm)
        btns.pack(fill="x", pady=(12, 0))

        def _cancel():
            try:
                win.destroy()
            except Exception:
                pass

        def _no():
            result["value"] = False
            try:
                win.destroy()
            except Exception:
                pass

        def _yes():
            result["value"] = True
            try:
                win.destroy()
            except Exception:
                pass

        tk.Button(btns, text="Cancel", width=10, command=_cancel).pack(
            side="right", padx=(8, 0)
        )
        tk.Button(btns, text="No", width=10, command=_no).pack(side="right", padx=(8, 0))
        tk.Button(btns, text="Yes", width=10, command=_yes).pack(side="right")

        try:
            win.update_idletasks()
            w = int(win.winfo_reqwidth())
            h = int(win.winfo_reqheight())
            px = int(self.winfo_rootx())
            py = int(self.winfo_rooty())
            pw = int(self.winfo_width())
            ph = int(self.winfo_height())
            x = int(px + (pw / 2) - (w / 2))
            y = int(py + (ph / 2) - (h / 2))
            if x < 0:
                x = 0
            if y < 0:
                y = 0
            win.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        try:
            win.wait_window()
        except Exception:
            pass
        return result.get("value")

    def _show_service_settings_dialog(
        self, *, default_port: int = 7777, default_max_players: int = 64
    ) -> Optional[dict]:
        import tkinter as tk

        result = {"ok": False}

        try:
            port_value = tk.StringVar(value=str(int(default_port)))
        except Exception:
            port_value = tk.StringVar(value="7777")
        try:
            max_players_value = tk.StringVar(value=str(int(default_max_players)))
        except Exception:
            max_players_value = tk.StringVar(value="64")

        steam_update_var = tk.BooleanVar(value=True)
        log_var = tk.BooleanVar(value=True)
        fileopenlog_var = tk.BooleanVar(value=True)

        win = tk.Toplevel(self)
        win.title("Service settings")
        try:
            win.resizable(False, False)
        except Exception:
            pass

        try:
            win.transient(self)
            win.grab_set()
        except Exception:
            pass

        frm = tk.Frame(win, padx=12, pady=12)
        frm.pack(fill="both", expand=True)

        tk.Label(
            frm,
            text="Configure the Windows Service (NSSM) settings:",
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        tk.Label(frm, text="Port:").grid(row=1, column=0, sticky="w")
        port_entry = tk.Entry(frm, textvariable=port_value, width=18)
        port_entry.grid(row=1, column=1, sticky="w", pady=2)

        tk.Label(frm, text="Max players:").grid(row=2, column=0, sticky="w")
        mp_entry = tk.Entry(frm, textvariable=max_players_value, width=18)
        mp_entry.grid(row=2, column=1, sticky="w", pady=2)

        tk.Label(frm, text="Flags:").grid(row=3, column=0, sticky="nw", pady=(8, 0))
        flags_frame = tk.Frame(frm)
        flags_frame.grid(row=3, column=1, sticky="w", pady=(8, 0))

        tk.Checkbutton(
            flags_frame,
            text="-steam_update",
            variable=steam_update_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            flags_frame,
            text="-log",
            variable=log_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            flags_frame,
            text="-fileopenlog",
            variable=fileopenlog_var,
        ).pack(anchor="w")

        btns = tk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))

        def _cancel():
            try:
                win.destroy()
            except Exception:
                pass

        def _ok():
            try:
                port = int(str(port_value.get() or "").strip())
                maxp = int(str(max_players_value.get() or "").strip())
                if port <= 0 or port > 65535:
                    raise ValueError("Invalid port")
                if maxp <= 0 or maxp > 255:
                    raise ValueError("Invalid max players")

                result["ok"] = True
                result["port"] = port
                result["max_players"] = maxp
                result["flags"] = {
                    "steam_update": bool(steam_update_var.get()),
                    "log": bool(log_var.get()),
                    "fileopenlog": bool(fileopenlog_var.get()),
                }
                win.destroy()
            except Exception:
                import tkinter.messagebox as messagebox

                messagebox.showerror(
                    "Error",
                    "Please enter a valid Port (1-65535) and Max players (1-255).",
                    parent=win,
                )

        tk.Button(btns, text="Cancel", width=10, command=_cancel).pack(
            side="right", padx=(6, 0)
        )
        tk.Button(btns, text="OK", width=10, command=_ok).pack(side="right")

        try:
            win.update_idletasks()
            w = int(win.winfo_reqwidth())
            h = int(win.winfo_reqheight())
            # Center relative to parent window
            px = int(self.winfo_rootx())
            py = int(self.winfo_rooty())
            pw = int(self.winfo_width())
            ph = int(self.winfo_height())
            x = int(px + (pw / 2) - (w / 2))
            y = int(py + (ph / 2) - (h / 2))
            if x < 0:
                x = 0
            if y < 0:
                y = 0
            win.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        try:
            port_entry.focus_set()
            port_entry.selection_range(0, tk.END)
        except Exception:
            pass

        try:
            win.wait_window()
        except Exception:
            pass

        if result.get("ok"):
            return {
                "port": result.get("port"),
                "max_players": result.get("max_players"),
                "flags": result.get("flags") or {},
            }
        return None
        

    def _install_or_update_scum_server(
        self, base_dir: Optional[str] = None, prompt_for_base_dir: bool = True
    ):
        """1-click: baixar SteamCMD automaticamente e instalar/atualizar SCUM Server (requer admin)."""
        import threading
        import tkinter.messagebox as messagebox
        import tkinter.filedialog as filedialog
        import shlex
        import ctypes
        import signal

        if getattr(self, "_steam_install_in_progress", False):
            self._add_log_message("⚠️ Instalação já está em andamento...", "WARNING")
            return

        default_base_dir = "C:\\Servers"
        if prompt_for_base_dir:
            choice = self._ask_yes_no_cancel_english(
                title="SCUM Server Installation",
                message=(
                    "The default installation folder is:\n\n"
                    "C:\\Servers\n\n"
                    "Do you want to use the default location?\n\n"
                    "Yes = Use default\n"
                    "No = Choose a custom folder\n"
                    "Cancel = Abort"
                ),
            )
            if choice is None:
                # Cancel
                self._add_log_message("Installation aborted by user.", "WARNING")
                return
            if choice:
                base_dir = default_base_dir
            else:
                selected = filedialog.askdirectory(
                    title="Select base directory", initialdir=default_base_dir
                )
                if not selected:
                    return
                base_dir = selected

            base_dir = self._normalize_windows_path(base_dir)
        else:
            base_dir = self._normalize_windows_path(base_dir or default_base_dir)

        app_dir = self.EXE_DIR if self.IS_EXE else self.ROOT_DIR

        def choose_installer_state_dir() -> Path:
            # Precisa ser gravável pelo usuário atual (GUI pode estar sem admin).
            candidates = []
            try:
                program_data = os.environ.get("PROGRAMDATA") or "C:\\ProgramData"
                candidates.append(Path(program_data) / "SSM" / "installer")
            except Exception:
                pass
            try:
                local_appdata = os.environ.get("LOCALAPPDATA")
                if local_appdata:
                    candidates.append(Path(local_appdata) / "SSM" / "installer")
            except Exception:
                pass

            # Fallback final: pasta temporária no diretório do app (pode falhar em Program Files).
            candidates.append(app_dir / "data" / "temp" / "installer")

            for cand in candidates:
                try:
                    (cand / "logs").mkdir(parents=True, exist_ok=True)
                    test_file = cand / "_write_test.tmp"
                    with open(test_file, "w", encoding="utf-8") as f:
                        f.write("ok")
                    try:
                        test_file.unlink()
                    except Exception:
                        pass
                    return cand
                except Exception:
                    continue

            return candidates[-1]

        installer_state_dir = choose_installer_state_dir()
        log_path = installer_state_dir / "logs" / "scum_installer.log"
        status_path = installer_state_dir / "scum_installer_status.json"

        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                status_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        except Exception:
            try:
                self._add_log_message(
                    f"⚠️ Unable to prepare installer state directory: {installer_state_dir}",
                    "WARNING",
                )
            except Exception:
                pass

        def is_admin() -> bool:
            try:
                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception:
                return False

        def build_install_command_args() -> Tuple[str, list]:
            """Return (executable, args_list) suitable for subprocess without shell."""
            if self.IS_EXE:
                exe = str(Path(sys.executable))
                return exe, [
                    "--install-scum-server",
                    "--base-dir",
                    base_dir,
                    "--installer-state-dir",
                    str(installer_state_dir),
                ]

            main_py = str(self.ROOT_DIR / "main.py")
            return sys.executable, [
                main_py,
                "--install-scum-server",
                "--base-dir",
                base_dir,
                "--installer-state-dir",
                str(installer_state_dir),
            ]

        def launch_installer_admin():
            exe, args_list = build_install_command_args()
            # Usar ShellExecuteW com 'runas' para obter retorno imediato (e detectar cancelamento do UAC).
            # Isso é bem mais confiável do que PowerShell Start-Process.
            try:
                try:
                    self._add_log_message(
                        f"[Installer] Launching elevated installer: {exe} {subprocess.list2cmdline(args_list)}",
                        "INFO",
                    )
                except Exception:
                    pass
                params = subprocess.list2cmdline(args_list)
                rc = ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    exe,
                    params,
                    str(app_dir),
                    1,
                )
                try:
                    self._add_log_message(
                        f"[Installer] ShellExecuteW returned: {int(rc)}",
                        "INFO",
                    )
                except Exception:
                    pass
                # rc <= 32 indica erro; 1223 é cancelamento pelo usuário
                if int(rc) == 1223:
                    raise PermissionError("UAC canceled")
                if int(rc) <= 32:
                    raise PermissionError(f"ShellExecute failed: {rc}")
                return True
            except PermissionError:
                raise
            except Exception as e:
                raise RuntimeError(f"Failed to launch elevated installer: {e}")

        def launch_installer_current_user():
            exe, args_list = build_install_command_args()
            try:
                try:
                    self._add_log_message(
                        f"[Installer] Launching installer (current user): {exe} {subprocess.list2cmdline(args_list)}",
                        "INFO",
                    )
                except Exception:
                    pass
                subprocess.Popen(
                    [exe] + args_list,
                    cwd=str(app_dir),
                    creationflags=(subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0),
                )
            except Exception as e:
                self._add_log_message(
                    f"❌ Failed to launch installer (current user): {e}", "ERROR"
                )
                raise

        def monitor_installer():
            last_size = 0
            last_state = None
            start_time = time.time()
            while True:
                try:
                    if log_path.exists():
                        size = log_path.stat().st_size
                        if size > last_size:
                            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                                f.seek(last_size)
                                new = f.read()
                            last_size = size
                            for line in new.splitlines():
                                line = line.strip()
                                if line:
                                    self._add_log_message(line, "INFO")
                                    # Atualizar texto do botão com porcentagem se disponível
                                    match = re.search(r"\((\d+%)\)", line)
                                    if match and hasattr(self, "btn_install_default"):
                                        pct = match.group(1)
                                        self.after(
                                            0,
                                            lambda p=pct: self.btn_install_default.configure(
                                                text=f"Installing ({p})..."
                                            )
                                            if hasattr(self, "btn_install_default")
                                            else None,
                                        )
                except Exception:
                    pass

                try:
                    if status_path.exists():
                        with open(status_path, "r", encoding="utf-8") as f:
                            status = json.load(f) or {}
                        state = status.get("state")
                        msg = status.get("message")
                        if state and state != last_state:
                            last_state = state
                            if state == "success":
                                self._add_log_message(f"✅ {msg or 'Installation completed'}", "SUCCESS")
                                try:
                                    def _post_install_sequence():
                                        import threading

                                        def _prompt_start_for_db():
                                            try:
                                                start_now = self._ask_yes_no_english(
                                                    title="Start SCUMServer",
                                                    message=(
                                                        "Installation completed successfully.\n\n"
                                                        "Do you want to start SCUMServer now to generate SCUM.db?\n\n"
                                                        "If you created a Windows Service, you can also start it later from the Service controls."
                                                    ),
                                                )
                                                if not start_now:
                                                    self._add_log_message(
                                                        "ℹ️ Skipped automatic SCUMServer start.",
                                                        "INFO",
                                                    )
                                                    return

                                                try:
                                                    cfg = self._load_config() or {}
                                                    service_name = str(
                                                        (cfg.get("server", {}) or {}).get("service_name")
                                                        or "SCUMServer"
                                                    )
                                                except Exception:
                                                    service_name = "SCUMServer"

                                                if not _service_exists_windows(service_name):
                                                    _auto_start_scum_db_creation()
                                                    return

                                                self._add_log_message(
                                                    f"[Installer] Starting Windows Service '{service_name}' to generate SCUM.db...",
                                                    "INFO",
                                                )

                                                def _start_worker():
                                                    started = False
                                                    try:
                                                        from utils.config_path_helper import ConfigPathHelper
                                                        from core.server_control.server_manager import ServerManager

                                                        cfg = self._load_config() or {}
                                                        ph = ConfigPathHelper(cfg)
                                                        sm = ServerManager(
                                                            (cfg.get("server", {}) or {}), ph
                                                        )
                                                        sm.service_name = service_name
                                                        res = sm.start_server(
                                                            scum_db_path=ph.get_scum_db_path()
                                                        )
                                                        started = bool(res.get("success"))
                                                        if not started:
                                                            err_msg = res.get("message") or res.get("error")
                                                            if err_msg:
                                                                try:
                                                                    self.after(
                                                                        0,
                                                                        lambda: self._add_log_message(
                                                                            f"[Installer] Failed to start service: {err_msg}",
                                                                            "WARNING",
                                                                        ),
                                                                    )
                                                                except Exception:
                                                                    pass
                                                    except Exception as e:
                                                        started = False
                                                        try:
                                                            self.after(
                                                                0,
                                                                lambda: self._add_log_message(
                                                                    f"[Installer] Failed to start service: {e}",
                                                                    "WARNING",
                                                                ),
                                                            )
                                                        except Exception:
                                                            pass

                                                    def _finish_start_ui():
                                                        try:
                                                            if started:
                                                                self._add_log_message(
                                                                    f"✅ Service '{service_name}' start requested.",
                                                                    "SUCCESS",
                                                                )
                                                                threading.Thread(
                                                                    target=lambda: _run_scum_server_until_db(
                                                                        timeout_minutes=5
                                                                    ),
                                                                    daemon=True,
                                                                ).start()
                                                            else:
                                                                self._add_log_message(
                                                                    "⚠️ Could not start service. Falling back to starting SCUMServer console.",
                                                                    "WARNING",
                                                                )
                                                                _auto_start_scum_db_creation()
                                                        except Exception:
                                                            pass

                                                    self.after(0, _finish_start_ui)

                                                threading.Thread(
                                                    target=_start_worker, daemon=True
                                                ).start()
                                            except Exception:
                                                _auto_start_scum_db_creation()

                                        # Step 1: offer service creation/update.
                                        # Step 2: only after it's finished (or skipped), ask to start for SCUM.db.
                                        try:
                                            self._offer_create_windows_service_after_install(
                                                on_done=lambda *_a, **_k: self.after(
                                                    0, _prompt_start_for_db
                                                )
                                            )
                                        except Exception:
                                            self.after(0, _prompt_start_for_db)

                                    self.after(0, _post_install_sequence)
                                except Exception:
                                    pass
                                try:
                                    self.after(0, self._update_installation_ui)
                                except Exception:
                                    pass
                            elif state == "error":
                                self._add_log_message(f"❌ {msg or 'Installation failed'}", "ERROR")
                            elif state == "running" and msg:
                                self._add_log_message(f"{msg}", "INFO")
                        if state in ("success", "error"):
                            break
                except Exception:
                    pass

                if time.time() - start_time > 7200:
                    self._add_log_message("❌ Installer timeout (2h)", "ERROR")
                    break

                time.sleep(1)

            self._steam_install_in_progress = False
            try:
                if hasattr(self, "btn_install_default"):
                    self.after(
                        0,
                        lambda: self.btn_install_default.configure(
                            state="normal", text="Install", fg_color="#FFA500"
                        ),
                    )
                if hasattr(self, "btn_install_scum_server"):
                    self.after(0, lambda: self.btn_install_scum_server.configure(state="normal"))
                self.after(0, self._update_installation_ui)
            except Exception:
                pass

            try:
                self.after(0, self._load_settings)
            except Exception:
                pass

        def _auto_start_scum_db_creation():
            try:
                self._add_log_message(
                    "[Installer] Starting SCUMServer automatically to generate SCUM.db...",
                    "INFO",
                )
                threading.Thread(
                    target=lambda: _run_scum_server_until_db(timeout_minutes=5),
                    daemon=True,
                ).start()
            except Exception:
                pass

        def _run_scum_server_until_db(timeout_minutes: int = 5):
            try:
                config = self._load_config() or {}
                scum_paths = config.get("paths", {}).get("scum_server", {})
                root_dir = scum_paths.get("root_directory")
                db_path = scum_paths.get("database")

                if not root_dir:
                    self._add_log_message(
                        "⚠️ root_directory is not configured; unable to start SCUMServer.",
                        "WARNING",
                    )
                    return

                if not db_path:
                    db_path = os.path.join(root_dir, "SCUM", "Saved", "SaveFiles", "SCUM.db")

                scumserver_exe = os.path.join(root_dir, "SCUM", "Binaries", "Win64", "SCUMServer.exe")
                if not os.path.exists(scumserver_exe):
                    self._add_log_message(
                        f"⚠️ SCUMServer.exe not found: {scumserver_exe}", "WARNING"
                    )
                    return

                # Se já existe, não precisa iniciar
                if os.path.exists(db_path):
                    self._add_log_message(
                        "✅ SCUM.db already exists. No action needed.", "SUCCESS"
                    )
                    return

                self._add_log_message(
                    "[Installer] Starting SCUMServer (-log) to generate SCUM.db...",
                    "INFO",
                )

                p = None
                try:
                    creationflags = 0
                    if sys.platform == "win32":
                        creationflags = subprocess.CREATE_NEW_CONSOLE

                    p = subprocess.Popen(
                        [scumserver_exe, "-log"],
                        cwd=os.path.dirname(scumserver_exe),
                        creationflags=creationflags,
                    )
                except OSError as oe:
                    # WinError 740: requer elevação
                    if getattr(oe, "winerror", None) == 740 and sys.platform == "win32":
                        try:
                            params = subprocess.list2cmdline(["-log"])
                            rc = ctypes.windll.shell32.ShellExecuteW(
                                None,
                                "runas",
                                scumserver_exe,
                                params,
                                os.path.dirname(scumserver_exe),
                                1,
                            )
                            if int(rc) == 1223:
                                self._add_log_message(
                                    "⚠️ UAC canceled. SCUMServer was not started.",
                                    "WARNING",
                                )
                                return
                            if int(rc) <= 32:
                                raise PermissionError(f"ShellExecute failed: {rc}")
                            self._add_log_message(
                                "[Installer] SCUMServer started with elevation (UAC).",
                                "INFO",
                            )
                            p = None  # sem handle confiável
                        except Exception as e:
                            self._add_log_message(
                                f"❌ Failed to start SCUMServer with elevation: {e}",
                                "ERROR",
                            )
                            return
                    else:
                        raise

                start = time.time()
                timeout_seconds = max(60, min(int(timeout_minutes) * 60, 600))
                last_wait_log = 0.0
                while time.time() - start < timeout_seconds:
                    if os.path.exists(db_path):
                        self._add_log_message(
                            "✅ SCUM.db detectado. Você já pode fechar a janela do SCUMServer.",
                            "SUCCESS",
                        )
                        break
                    if p is not None and p.poll() is not None:
                        break

                    now = time.time()
                    if (now - last_wait_log) > 10:
                        last_wait_log = now
                        elapsed = int(now - start)
                        total = int(timeout_seconds)
                        try:
                            self._add_log_message(
                                f"[Installer] Waiting for SCUM.db creation... ({elapsed}s / {total}s)",
                                "INFO",
                            )
                        except Exception:
                            pass
                    time.sleep(2)

                if os.path.exists(db_path):
                    self._add_log_message(
                        "✅ Initialization complete: SCUM.db created.", "SUCCESS"
                    )
                else:
                    self._add_log_message(
                        "⚠️ SCUM.db was not created yet. The server may need more time or it may be blocked (firewall/permissions).",
                        "WARNING",
                    )
            except Exception as e:
                self._add_log_message(f"❌ Failed to start SCUMServer: {e}", "ERROR")

        def _resolve_app_dir_for_service() -> Path:
            try:
                return self.EXE_DIR if self.IS_EXE else self.ROOT_DIR
            except Exception:
                return Path(os.getcwd())

        def _find_nssm_exe() -> Optional[str]:
            try:
                cfg = self._load_config() or {}
                rel = (
                    cfg.get("server", {}).get("nssm_path")
                    or "nssm-2.24\\win64\\nssm.exe"
                )
                p = Path(rel)
                if p.is_absolute() and p.exists():
                    return str(p)
                base = _resolve_app_dir_for_service()
                cand = (base / p).resolve()
                if cand.exists():
                    return str(cand)
                # Fallback hardcoded relative to app
                cand2 = (base / "nssm-2.24" / "win64" / "nssm.exe").resolve()
                if cand2.exists():
                    return str(cand2)
            except Exception:
                pass
            return None

        def _service_exists_windows(service_name: str) -> bool:
            try:
                if sys.platform != "win32":
                    return False
                r = subprocess.run(
                    ["sc", "query", str(service_name)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ),
                )
                return int(r.returncode or 0) == 0
            except Exception:
                return False

        def _offer_create_windows_service_after_install(on_done=None):
            try:
                import tkinter.messagebox as messagebox
                import threading

                cfg = self._load_config() or {}
                server_cfg = cfg.get("server", {}) if isinstance(cfg, dict) else {}
                paths_cfg = cfg.get("paths", {}) if isinstance(cfg, dict) else {}
                scum_paths = (
                    paths_cfg.get("scum_server", {}) if isinstance(paths_cfg, dict) else {}
                )

                service_name = str(server_cfg.get("service_name") or "SCUMServer")
                binaries_dir = str(scum_paths.get("binaries_directory") or "")
                scumserver_exe = str(Path(binaries_dir) / "SCUMServer.exe")

                if not binaries_dir or not os.path.isdir(binaries_dir):
                    return
                if not os.path.exists(scumserver_exe):
                    return

                nssm_exe = _find_nssm_exe()
                if not nssm_exe or not os.path.exists(nssm_exe):
                    self._add_log_message(
                        "⚠️ NSSM not found in the application folder. Windows Service creation is not available.",
                        "WARNING",
                    )
                    return

                create_now = self._ask_yes_no_english(
                    title="Windows Service",
                    message=(
                        "SCUM Server installation completed successfully.\n\n"
                        "Do you want to create a Windows Service now (recommended)?\n\n"
                        "This enables automatic startup and graceful stop/restart."
                    ),
                )
                if not create_now:
                    if callable(on_done):
                        try:
                            on_done(False)
                        except Exception:
                            pass
                    return

                settings = self._show_service_settings_dialog(default_port=int(server_cfg.get("port") or 7777), default_max_players=int(server_cfg.get("max_players") or 64))
                if not settings:
                    return

                port = int(settings.get("port") or 7777)
                max_players = int(settings.get("max_players") or 64)
                flags = settings.get("flags") or {}

                args = [f"-port={port}", f"-MaxPlayers={max_players}"]
                if flags.get("steam_update"):
                    args.append("-steam_update")
                if flags.get("log"):
                    args.append("-log")
                if flags.get("fileopenlog"):
                    args.append("-fileopenlog")
                app_parameters = " ".join(args).strip()

                exists = _service_exists_windows(service_name)
                if exists:
                    ok = self._ask_yes_no_english(
                        title="Windows Service",
                        message=(
                            f"Service '{service_name}' already exists.\n\n"
                            "Do you want to update it with the current settings?"
                        ),
                    )
                    if not ok:
                        if callable(on_done):
                            try:
                                on_done(False)
                            except Exception:
                                pass
                        return

                from utils.config_path_helper import ConfigPathHelper
                from core.server_control.server_manager import ServerManager

                path_helper = ConfigPathHelper(cfg)
                sm = ServerManager(server_cfg, path_helper)
                sm.service_name = service_name
                sm.nssm_path = nssm_exe

                self._add_log_message(
                    f"[NSSM] Creating/updating Windows Service '{service_name}' (may prompt UAC)...",
                    "INFO",
                )

                def _worker():
                    try:
                        res = sm.create_or_update_nssm_service(
                            app_exe=scumserver_exe,
                            app_directory=binaries_dir,
                            app_parameters=app_parameters,
                            console_timeout_ms=120000,
                            enable_terminate=True,
                            terminate_timeout_ms=300000,
                        )

                        def _finish_ui():
                            try:
                                if res.get("success"):
                                    status = str(res.get("status") or "ok")
                                    self._add_log_message(
                                        f"✅ Windows Service '{service_name}' created/updated successfully.",
                                        "SUCCESS",
                                    )
                                    if status == "ok_with_warning":
                                        preset = res.get("preset") or {}
                                        warn_msg = (
                                            preset.get("message")
                                            or "The NSSM shutdown preset could not be verified."
                                        )
                                        self._add_log_message(f"⚠️ {warn_msg}", "WARNING")
                                        messagebox.showinfo(
                                            "Success",
                                            f"Service '{service_name}' was created/updated successfully.",
                                        )
                                    else:
                                        messagebox.showinfo(
                                            "Success",
                                            f"Service '{service_name}' was created/updated successfully.",
                                        )
                                    if callable(on_done):
                                        try:
                                            on_done(True)
                                        except Exception:
                                            pass
                                    return

                                msg = (
                                    res.get("message")
                                    or res.get("error")
                                    or "Failed to create/update Windows Service"
                                )
                                out = res.get("output")
                                if out:
                                    msg = f"{msg}\n\n{out}"
                                self._add_log_message(f"❌ {msg}", "ERROR")
                                messagebox.showerror(
                                    "Error",
                                    "Failed to create/update Windows Service.\n\n" + str(msg),
                                )
                                if callable(on_done):
                                    try:
                                        on_done(False)
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                        self.after(0, _finish_ui)
                    except Exception as e:
                        def _err_ui():
                            try:
                                self._add_log_message(
                                    f"❌ Failed to create/update Windows Service: {e}",
                                    "ERROR",
                                )
                                messagebox.showerror(
                                    "Error",
                                    "Failed to create/update Windows Service.\n\n" + str(e),
                                )
                                if callable(on_done):
                                    try:
                                        on_done(False)
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                        self.after(0, _err_ui)

                threading.Thread(target=_worker, daemon=True).start()
                return
            except Exception as e:
                try:
                    self._add_log_message(
                        f"❌ Failed to create/update Windows Service: {e}", "ERROR"
                    )
                except Exception:
                    pass
                if callable(on_done):
                    try:
                        on_done(False)
                    except Exception:
                        pass

        self._offer_create_windows_service_after_install = _offer_create_windows_service_after_install

        def start_flow():
            try:
                self._steam_install_in_progress = True
                try:
                    if hasattr(self, "btn_install_default"):
                        self.after(
                            0,
                            lambda: self.btn_install_default.configure(
                                state="disabled", text="Installing...", fg_color="#CC8400"
                            ),
                        )
                    if hasattr(self, "btn_install_scum_server"):
                        self.after(0, lambda: self.btn_install_scum_server.configure(state="disabled"))
                    self.after(0, self._update_installation_ui)
                except Exception:
                    pass

                self._add_log_message(f"[Installer] Base directory: {base_dir}", "INFO")
                self._add_log_message(
                    f"[Installer] State directory: {installer_state_dir}", "INFO"
                )
                try:
                    self._add_log_message(
                        f"[Installer] GUI is_admin() = {is_admin()}",
                        "INFO",
                    )
                except Exception:
                    pass
                self._add_log_message("[Installer] Starting...", "INFO")

                try:
                    if log_path.exists():
                        log_path.unlink()
                except Exception:
                    pass
                try:
                    if status_path.exists():
                        status_path.unlink()
                except Exception:
                    pass

                if is_admin():
                    launch_installer_admin()
                    try:
                        self._add_log_message(
                            "[Installer] Elevated installer launch requested successfully (UAC should appear).",
                            "INFO",
                        )
                    except Exception:
                        pass
                else:
                    try:
                        launch_installer_current_user()
                        try:
                            self._add_log_message(
                                "[Installer] Installer launch requested (current user).",
                                "INFO",
                            )
                        except Exception:
                            pass
                    except PermissionError:
                        self._add_log_message(
                            "⚠️ UAC canceled. The installer was not started.",
                            "WARNING",
                        )
                        self._steam_install_in_progress = False
                        try:
                            if hasattr(self, "btn_install_default"):
                                self.btn_install_default.configure(
                                    state="normal", text="Install", fg_color="#FFA500"
                                )
                            if hasattr(self, "btn_install_scum_server"):
                                self.btn_install_scum_server.configure(state="normal")
                            self._update_installation_ui()
                        except Exception:
                            pass
                        return

                def verify_started():
                    try:
                        if not log_path.exists() and not status_path.exists():
                            self._add_log_message(
                                "⚠️ Still waiting for the installer to start (UAC may be pending). If nothing shows up, try running the GUI as Administrator.",
                                "WARNING",
                            )
                    except Exception:
                        pass

                try:
                    # Dar mais tempo: em alguns PCs o UAC/antivírus pode atrasar a criação de log/status.
                    self.after(25000, verify_started)
                except Exception:
                    pass

                threading.Thread(target=monitor_installer, daemon=True).start()
            except Exception as e:
                self._steam_install_in_progress = False
                try:
                    if hasattr(self, "btn_install_scum_server"):
                        self.after(0, lambda: self.btn_install_scum_server.configure(state="normal"))
                except Exception:
                    pass
                self._add_log_message(f"❌ Failed to start installer: {e}", "ERROR")

        threading.Thread(target=start_flow, daemon=True).start()

    def _create_logs_tab(self, parent):
        """Criar tab de Logs"""
        logs_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.tabs_content["logs"] = logs_frame

        header = ctk.CTkFrame(logs_frame, fg_color="transparent")
        header.pack(pady=(12, 6), padx=12, fill="x")

        logs_label = ctk.CTkLabel(header, text="Logs", font=ctk.CTkFont(size=14, weight="bold"))
        logs_label.pack(side="left", anchor="w")

        self.loading_indicator = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=12))
        self.loading_indicator.pack(side="right", padx=10)

        topbar = ctk.CTkFrame(
            logs_frame,
            fg_color=("gray90", "gray20"),
            corner_radius=12,
            border_width=1,
            border_color=("gray82", "gray28"),
        )
        topbar.pack(side="top", fill="x", padx=12, pady=(0, 10))

        content = ctk.CTkFrame(logs_frame, fg_color="transparent")
        content.pack(side="top", fill="both", expand=True, padx=12, pady=(0, 12))

        self.logs_pages = {}
        self.logs_page_buttons = {}

        def switch_page(page_id: str):
            try:
                for f in self.logs_pages.values():
                    try:
                        f.pack_forget()
                    except Exception:
                        pass

                if page_id != "scum":
                    self._stop_scum_log_tail()

                frame = self.logs_pages.get(page_id)
                if frame is not None:
                    frame.pack(fill="both", expand=True)

                self.logs_current_page = page_id

                for pid, btn in self.logs_page_buttons.items():
                    if pid == page_id:
                        btn.configure(
                            fg_color=("#1f538d", "#14375e"),
                            hover_color=("#2a5a9a", "#1a4a7a"),
                            font=ctk.CTkFont(size=12, weight="bold"),
                        )
                    else:
                        btn.configure(
                            fg_color=("gray", "gray"),
                            hover_color=("#3b3b3b", "#2a2a2a"),
                            font=ctk.CTkFont(size=12, weight="normal"),
                        )

                if page_id == "scum":
                    self._start_scum_log_tail()
            except Exception:
                pass

        btn_app = ctk.CTkButton(
            topbar,
            text="Application",
            command=lambda: switch_page("application"),
            width=140,
            height=38,
        )
        btn_app.pack(side="left", padx=10, pady=8)
        self.logs_page_buttons["application"] = btn_app

        btn_scum = ctk.CTkButton(
            topbar,
            text="SCUM",
            command=lambda: switch_page("scum"),
            width=140,
            height=38,
        )
        btn_scum.pack(side="left", padx=(0, 10), pady=8)
        self.logs_page_buttons["scum"] = btn_scum

        app_tab = ctk.CTkFrame(content, fg_color="transparent")
        self.logs_pages["application"] = app_tab

        self.logs_textbox = ctk.CTkTextbox(
            app_tab,
            state="disabled",
            font=ctk.CTkFont(size=10),
            fg_color=("#000000", "#000000"),
            text_color=("#EDEDED", "#EDEDED"),
            border_color=("#2B2B2B", "#2B2B2B"),
            scrollbar_button_color=("#3A3A3A", "#3A3A3A"),
            scrollbar_button_hover_color=("#4A4A4A", "#4A4A4A"),
        )
        self.logs_textbox.pack(pady=5, padx=0, fill="both", expand=True)

        scum_tab = ctk.CTkFrame(content, fg_color="transparent")
        self.logs_pages["scum"] = scum_tab

        self.scum_logs_textbox = ctk.CTkTextbox(
            scum_tab,
            state="disabled",
            font=ctk.CTkFont(size=10),
            fg_color=("#000000", "#000000"),
            text_color=("#EDEDED", "#EDEDED"),
            border_color=("#2B2B2B", "#2B2B2B"),
            scrollbar_button_color=("#3A3A3A", "#3A3A3A"),
            scrollbar_button_hover_color=("#4A4A4A", "#4A4A4A"),
        )
        self.scum_logs_textbox.pack(pady=5, padx=0, fill="both", expand=True)

        switch_page("application")

    def _get_scum_server_logs_directory(self) -> str:
        try:
            config = self._load_config() or {}
            scum_paths = config.get("paths", {}).get("scum_server", {})
            configured = str(scum_paths.get("server_logs_directory") or "").strip()
            if configured:
                return configured

            root_dir = str(scum_paths.get("root_directory") or "").strip()
            if root_dir:
                return os.path.join(root_dir, "SCUM", "Saved", "Logs")
        except Exception:
            pass
        return ""

    def _start_scum_log_tail(self):
        try:
            if not hasattr(self, "scum_logs_textbox"):
                return

            if getattr(self, "_is_resizing", False):
                self.scum_log_tail_job = self.after(500, self._start_scum_log_tail)
                return

            if self.scum_log_tail_job is not None:
                return

            logs_dir = self._get_scum_server_logs_directory()
            if not logs_dir:
                self._set_scum_logs_text("Server logs directory is not configured.\n\nConfigure it in Settings under 'Server Logs Directory (SCUM.log)'.\n")
                self.scum_log_tail_job = self.after(1000, self._start_scum_log_tail)
                return

            log_file = os.path.join(logs_dir, "SCUM.log")
            self.scum_log_file_path = log_file
            self.scum_log_file_pos = 0

            if not os.path.exists(log_file):
                self._set_scum_logs_text(f"SCUM.log was not found at:\n{log_file}\n")
                self.scum_log_tail_job = self.after(1000, self._poll_scum_log)
                return

            self._set_scum_logs_text(f"Tailing:\n{log_file}\n\n")
            try:
                self.scum_log_file_pos = os.path.getsize(log_file)
            except Exception:
                self.scum_log_file_pos = 0

            self.scum_log_tail_job = self.after(300, self._poll_scum_log)
        except Exception:
            try:
                self.scum_log_tail_job = self.after(1000, self._start_scum_log_tail)
            except Exception:
                pass

    def _stop_scum_log_tail(self):
        try:
            if self.scum_log_tail_job is not None:
                try:
                    self.after_cancel(self.scum_log_tail_job)
                except Exception:
                    pass
                self.scum_log_tail_job = None
        except Exception:
            pass

    def _set_scum_logs_text(self, text: str):
        try:
            tb = getattr(self, "scum_logs_textbox", None)
            if not tb:
                return
            tb.configure(state="normal")
            tb.delete("1.0", "end")
            tb.insert("end", text)
            tb.configure(state="disabled")
        except Exception:
            pass

    def _append_scum_logs_text(self, text: str):
        try:
            tb = getattr(self, "scum_logs_textbox", None)
            if not tb:
                return

            if getattr(self, "_is_resizing", False):
                try:
                    self._scum_log_buffer.append(text)
                    if self._scum_log_flush_job is None:
                        self._scum_log_flush_job = self.after(
                            250, self._flush_scum_log_buffer
                        )
                except Exception:
                    pass
                return

            tb.configure(state="normal")
            tb.insert("end", text)

            try:
                current_lines = int(tb.index("end-1c").split(".")[0])
                max_lines = 2000
                if current_lines > max_lines:
                    delete_to = current_lines - max_lines
                    tb.delete("1.0", f"{delete_to}.0")
            except Exception:
                pass

            tb.see("end")
            tb.configure(state="disabled")
        except Exception:
            pass

    def _poll_scum_log(self):
        try:
            if self.logs_current_page != "scum":
                self._stop_scum_log_tail()
                return

            if getattr(self, "_is_resizing", False):
                self.scum_log_tail_job = self.after(500, self._poll_scum_log)
                return

            log_file = self.scum_log_file_path
            if not log_file:
                self._stop_scum_log_tail()
                return

            if not os.path.exists(log_file):
                self._set_scum_logs_text(f"SCUM.log was not found at:\n{log_file}\n")
                self.scum_log_tail_job = self.after(1000, self._poll_scum_log)
                return

            try:
                size = os.path.getsize(log_file)
                if size < int(self.scum_log_file_pos or 0):
                    self.scum_log_file_pos = 0
            except Exception:
                pass

            new_text = ""
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    try:
                        f.seek(int(self.scum_log_file_pos or 0))
                    except Exception:
                        f.seek(0)
                        self.scum_log_file_pos = 0
                    new_text = f.read()
                    try:
                        self.scum_log_file_pos = f.tell()
                    except Exception:
                        pass
            except Exception as e:
                self._append_scum_logs_text(f"\n[read error] {e}\n")
                self.scum_log_tail_job = self.after(1000, self._poll_scum_log)
                return

            if new_text:
                self._append_scum_logs_text(new_text)

            self.scum_log_tail_job = self.after(300, self._poll_scum_log)
        except Exception:
            try:
                self.scum_log_tail_job = self.after(1000, self._poll_scum_log)
            except Exception:
                pass

    def _create_webhooks_tab(self, parent, register_tab: bool = True):
        """Create Discord tab (Webhooks + future Bot)"""
        webhooks_frame = ctk.CTkFrame(parent, fg_color="transparent")
        if register_tab:
            self.tabs_content["webhooks"] = webhooks_frame
        else:
            webhooks_frame.pack(fill="both", expand=True)

        # Discord agora e uma pagina unica (Bot + Webhooks). Mantemos este flag para
        # a logica de freeze/unfreeze durante resize.
        try:
            self.discord_current_page = "webhooks"
        except Exception:
            pass

        self._webhooks_parent_for_reload = parent
        self._webhooks_register_tab_for_reload = register_tab

        # Single page (Option A): Bot card at top + Webhooks below
        scrollable_frame = ctk.CTkScrollableFrame(webhooks_frame, fg_color="transparent")
        scrollable_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Referencia para otimizar resize (Discord/Webhooks e muito pesado para reflow em cada pixel)
        self._discord_scrollable_frame = scrollable_frame
        self._discord_resize_placeholder_parent = webhooks_frame

        card_color = ("gray95", "gray17")
        card_border_color = ("gray80", "gray25")

        # Card: Bot (at top)
        bot_card = ctk.CTkFrame(
            scrollable_frame,
            fg_color=card_color,
            corner_radius=10,
            border_width=1,
            border_color=card_border_color,
        )
        bot_card.pack(fill="x", padx=5, pady=(0, 12))

        bot_header = ctk.CTkFrame(bot_card, fg_color="transparent")
        bot_header.pack(fill="x", padx=15, pady=(15, 8))

        bot_icon = ctk.CTkLabel(bot_header, text="🤖", font=ctk.CTkFont(size=20))
        bot_icon.pack(side="left", padx=(0, 10))

        bot_title = ctk.CTkLabel(
            bot_header,
            text="Bot",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        bot_title.pack(side="left")

        bot_body = ctk.CTkFrame(bot_card, fg_color="transparent")
        bot_body.pack(fill="x", padx=15, pady=(0, 15))

        # Load config defaults
        cfg = self._load_config() or {}
        bot_cfg = cfg.get("discord_bot", {}) if isinstance(cfg, dict) else {}
        if not isinstance(bot_cfg, dict):
            bot_cfg = {}

        token_val = str(bot_cfg.get("bot_token") or "")
        guild_val = str(bot_cfg.get("guild_id") or "")
        cat_val = str(bot_cfg.get("default_category_name") or "SSM")
        register_role_val = str(bot_cfg.get("register_role_id") or "")
        include_disabled_val = bool(bot_cfg.get("include_disabled_events", True))
        validate_urls_val = bool(bot_cfg.get("validate_existing_urls", True))
        repair_urls_val = bool(bot_cfg.get("repair_invalid_urls", True))

        row1 = ctk.CTkFrame(bot_body, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(row1, text="Bot Token", width=120, anchor="w").pack(
            side="left", padx=(0, 10)
        )
        self.discord_bot_token_entry = ctk.CTkEntry(
            row1,
            height=35,
            show="*",
            placeholder_text="Paste Discord Bot Token...",
        )
        self.discord_bot_token_entry.pack(side="left", fill="x", expand=True)
        try:
            self.discord_bot_token_entry.insert(0, token_val)
        except Exception:
            pass

        row2 = ctk.CTkFrame(bot_body, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 8))

        row2_left = ctk.CTkFrame(row2, fg_color="transparent")
        row2_left.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkLabel(row2_left, text="Guild ID", width=120, anchor="w").pack(
            side="left", padx=(0, 10)
        )
        self.discord_bot_guild_entry = ctk.CTkEntry(
            row2_left,
            height=35,
            placeholder_text="123456789012345678",
        )
        self.discord_bot_guild_entry.pack(side="left", fill="x", expand=True)
        try:
            self.discord_bot_guild_entry.insert(0, guild_val)
        except Exception:
            pass

        row2_right = ctk.CTkFrame(row2, fg_color="transparent")
        row2_right.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            row2_right,
            text="Register Role ID",
            width=120,
            anchor="w",
        ).pack(side="left", padx=(0, 10))
        self.discord_bot_register_role_entry = ctk.CTkEntry(
            row2_right,
            height=35,
            placeholder_text="Optional (leave blank)",
        )
        self.discord_bot_register_role_entry.pack(side="left", fill="x", expand=True)
        try:
            self.discord_bot_register_role_entry.insert(0, register_role_val)
        except Exception:
            pass

        row3 = ctk.CTkFrame(bot_body, fg_color="transparent")
        row3.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(row3, text="Default Category", width=120, anchor="w").pack(
            side="left", padx=(0, 10)
        )
        self.discord_bot_category_entry = ctk.CTkEntry(
            row3,
            height=35,
            placeholder_text="SSM",
        )
        self.discord_bot_category_entry.pack(side="left", fill="x", expand=True)
        try:
            self.discord_bot_category_entry.insert(0, cat_val)
        except Exception:
            pass

        opts_row = ctk.CTkFrame(bot_body, fg_color="transparent")
        opts_row.pack(fill="x", pady=(6, 10))

        self.discord_bot_include_disabled_var = ctk.BooleanVar(value=include_disabled_val)
        self.discord_bot_validate_urls_var = ctk.BooleanVar(value=validate_urls_val)
        self.discord_bot_repair_urls_var = ctk.BooleanVar(value=repair_urls_val)

        ctk.CTkCheckBox(
            opts_row,
            text="Include disabled events",
            variable=self.discord_bot_include_disabled_var,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkCheckBox(
            opts_row,
            text="Validate existing webhook URLs",
            variable=self.discord_bot_validate_urls_var,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkCheckBox(
            opts_row,
            text="Repair invalid webhook URLs",
            variable=self.discord_bot_repair_urls_var,
        ).pack(side="left")

        actions = ctk.CTkFrame(bot_body, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 10))

        self.discord_bot_save_btn = ctk.CTkButton(
            actions,
            text="Save",
            width=110,
            height=38,
            command=self._discord_bot_save,
            fg_color=("#1f538d", "#14375e"),
            hover_color=("#2a5a9a", "#1a4a7a"),
        )
        self.discord_bot_save_btn.pack(side="left", padx=(0, 10))

        self.discord_bot_test_btn = ctk.CTkButton(
            actions,
            text="Test Bot",
            width=140,
            height=38,
            command=self._discord_bot_test,
            fg_color=("#1f538d", "#14375e"),
            hover_color=("#2a5a9a", "#1a4a7a"),
        )
        self.discord_bot_test_btn.pack(side="left", padx=(0, 10))

        self.discord_bot_sync_btn = ctk.CTkButton(
            actions,
            text="Create/Sync channels",
            width=200,
            height=38,
            command=self._discord_bot_sync,
            fg_color="green",
            hover_color="darkgreen",
        )
        self.discord_bot_sync_btn.pack(side="left")

        self.discord_bot_status_label = ctk.CTkLabel(
            bot_body,
            text="",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        self.discord_bot_status_label.pack(fill="x", pady=(2, 0))

        help_text = ctk.CTkLabel(
            bot_body,
            text=(
                "Creates missing categories/channels/webhooks and updates webhooks.json. "
                "Does not enable sending automatically."
            ),
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        help_text.pack(fill="x", pady=(6, 0))

        self.webhook_entries = {}
        self.webhook_enabled_vars = {}
        self.webhook_display_name_entries = {}

        webhooks = self._load_webhooks_meta()
        if not isinstance(webhooks, dict):
            webhooks = {}

        table_outer = ctk.CTkFrame(scrollable_frame, fg_color=card_color, corner_radius=10)
        table_outer.pack(fill="both", expand=False, padx=5, pady=(0, 10))

        header = ctk.CTkFrame(table_outer, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(12, 6))
        header.grid_columnconfigure(0, weight=0)
        header.grid_columnconfigure(1, weight=0)
        header.grid_columnconfigure(2, weight=0)
        header.grid_columnconfigure(3, weight=1)
        header.grid_columnconfigure(4, weight=0)

        ctk.CTkLabel(
            header,
            text="Log",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=180,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Active",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=70,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            header,
            text="Display",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=220,
            anchor="w",
        ).grid(row=0, column=2, sticky="w")
        ctk.CTkLabel(
            header,
            text="Address",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).grid(row=0, column=3, sticky="w", padx=(10, 0))
        ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=80,
            anchor="center",
        ).grid(row=0, column=4, sticky="e")

        rows_wrap = ctk.CTkFrame(table_outer, fg_color="transparent")
        rows_wrap.pack(fill="x", padx=15, pady=(0, 12))

        for name in sorted(webhooks.keys(), key=lambda x: str(x).lower()):
            meta = webhooks.get(name, {}) if isinstance(webhooks.get(name), dict) else {}
            value = meta.get("url", "") if isinstance(meta, dict) else ""
            enabled_val = bool(meta.get("enabled", False)) if isinstance(meta, dict) else False
            display_name_val = str(meta.get("display_name") or "") if isinstance(meta, dict) else ""

            row = ctk.CTkFrame(rows_wrap, fg_color="transparent")
            row.pack(fill="x", pady=(0, 8))
            row.grid_columnconfigure(0, weight=0)
            row.grid_columnconfigure(1, weight=0)
            row.grid_columnconfigure(2, weight=0)
            row.grid_columnconfigure(3, weight=1)
            row.grid_columnconfigure(4, weight=0)

            name_label = ctk.CTkLabel(
                row,
                text=str(name),
                font=ctk.CTkFont(size=12, weight="bold"),
                width=180,
                anchor="w",
            )
            name_label.grid(row=0, column=0, sticky="w")

            enabled_var = ctk.BooleanVar(value=enabled_val)
            enabled_cb = ctk.CTkCheckBox(
                row,
                text="",
                variable=enabled_var,
                width=22,
            )
            enabled_cb.grid(row=0, column=1, sticky="w")

            display_entry = ctk.CTkEntry(
                row,
                height=35,
                font=ctk.CTkFont(size=12),
                placeholder_text="Display name (Discord)",
                width=220,
            )
            display_entry.grid(row=0, column=2, sticky="w", padx=(10, 0))
            try:
                display_entry.insert(0, display_name_val)
            except Exception:
                pass

            entry = ctk.CTkEntry(
                row,
                height=35,
                font=ctk.CTkFont(size=12),
                placeholder_text="https://discord.com/api/webhooks/...",
            )
            entry.grid(row=0, column=3, sticky="ew", padx=(10, 10))
            try:
                entry.insert(0, str(value) if value is not None else "")
            except Exception:
                pass

            test_btn = ctk.CTkButton(
                row,
                text="Test",
                width=80,
                height=35,
                command=lambda n=name: self._test_webhook(str(n)),
                fg_color=("#1f538d", "#14375e"),
                hover_color=("#2a5a9a", "#1a4a7a"),
            )
            test_btn.grid(row=0, column=4, sticky="e")

            self.webhook_entries[str(name)] = entry
            self.webhook_enabled_vars[str(name)] = enabled_var
            self.webhook_display_name_entries[str(name)] = display_entry

        buttons_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 0), padx=10)

        save_btn = ctk.CTkButton(
            buttons_frame,
            text="Save Webhooks",
            command=self._save_webhooks,
            width=160,
            height=40,
            fg_color="green",
            hover_color="darkgreen",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        save_btn.pack(side="left", padx=5)

        reload_btn = ctk.CTkButton(
            buttons_frame,
            text="Reload",
            command=self._reload_webhooks_tab,
            width=120,
            height=40,
            fg_color="blue",
            hover_color="darkblue",
            font=ctk.CTkFont(size=13),
        )
        reload_btn.pack(side="left", padx=5)

    def _reload_webhooks_tab(self):
        """Recarregar tab de webhooks (recria o conteúdo)"""
        try:
            old = None
            if "webhooks" in self.tabs_content:
                old = self.tabs_content.get("webhooks")
            elif hasattr(self, "_webhooks_parent_for_reload"):
                try:
                    for child in self._webhooks_parent_for_reload.winfo_children():
                        if isinstance(child, ctk.CTkFrame):
                            old = child
                            break
                except Exception:
                    old = None

            if old is not None:
                try:
                    old.destroy()
                except Exception:
                    pass

            parent = getattr(self, "_webhooks_parent_for_reload", None)
            if parent is None:
                return

            register_tab = bool(getattr(self, "_webhooks_register_tab_for_reload", True))
            self._create_webhooks_tab(parent, register_tab=register_tab)
        except Exception:
            pass

    def _load_webhooks(self) -> Optional[Dict]:
        """Carregar webhooks.json"""
        try:
            webhooks_path = (
                self.EXE_DIR / "data" / "webhooks.json"
                if self.IS_EXE
                else self.ROOT_DIR / "data" / "webhooks.json"
            )

            if not webhooks_path.exists():
                self._add_log_message(
                    f"webhooks.json not found at: {webhooks_path}", "WARNING"
                )
                return None

            from core.webhooks.manager import WebhooksManager

            mgr = WebhooksManager(str(webhooks_path))
            return mgr.list_events_simple()
        except Exception as e:
            self._add_log_message(f"Failed to load webhooks.json: {e}", "ERROR")
            if self.logger:
                self.logger.error(f"Failed to load webhooks.json: {e}")
            return None

    def _load_webhooks_meta(self) -> Optional[Dict]:
        try:
            webhooks_path = (
                self.EXE_DIR / "data" / "webhooks.json"
                if self.IS_EXE
                else self.ROOT_DIR / "data" / "webhooks.json"
            )

            if not webhooks_path.exists():
                self._add_log_message(
                    f"webhooks.json not found at: {webhooks_path}", "WARNING"
                )
                return None

            from core.webhooks.manager import WebhooksManager

            mgr = WebhooksManager(str(webhooks_path))
            return mgr.list_events_meta()
        except Exception as e:
            self._add_log_message(f"Failed to load webhooks.json: {e}", "ERROR")
            if self.logger:
                self.logger.error(f"Failed to load webhooks.json: {e}")
            return None

    def _save_webhooks(self):
        """Salvar webhooks.json a partir dos campos da GUI"""
        try:
            if not hasattr(self, "webhook_entries"):
                return

            webhooks_path = (
                self.EXE_DIR / "data" / "webhooks.json"
                if self.IS_EXE
                else self.ROOT_DIR / "data" / "webhooks.json"
            )

            updated: Dict[str, Dict[str, Any]] = {}

            def is_probably_discord_webhook(url: str) -> bool:
                u = (url or "").strip().lower()
                if not u:
                    return True
                return (
                    u.startswith("https://discord.com/api/webhooks/")
                    or u.startswith("https://discordapp.com/api/webhooks/")
                )

            for name, entry in self.webhook_entries.items():
                try:
                    url = entry.get().strip()
                except Exception:
                    url = ""

                if not is_probably_discord_webhook(url):
                    import tkinter.messagebox as messagebox

                    messagebox.showerror(
                        "Error",
                        f"Invalid webhook URL for '{name}'.\n\nURL must start with:\nhttps://discord.com/api/webhooks/",
                    )
                    return

                try:
                    enabled_var = None
                    if hasattr(self, "webhook_enabled_vars"):
                        enabled_var = self.webhook_enabled_vars.get(name)
                    enabled_val = bool(enabled_var.get()) if enabled_var is not None else bool(url.strip())
                except Exception:
                    enabled_val = bool(url.strip())

                try:
                    disp_entry = None
                    if hasattr(self, "webhook_display_name_entries"):
                        disp_entry = self.webhook_display_name_entries.get(name)
                    display_name_val = (disp_entry.get() or "") if disp_entry is not None else ""
                except Exception:
                    display_name_val = ""

                updated[name] = {
                    "url": url,
                    "enabled": enabled_val,
                    "display_name": display_name_val,
                }

            from core.webhooks.manager import WebhooksManager

            mgr = WebhooksManager(str(webhooks_path))
            mgr.apply_events_meta_updates(updated, create_backup=True)

            self._add_log_message("✅ Webhooks saved successfully", "SUCCESS")
            import tkinter.messagebox as messagebox

            messagebox.showinfo("Success", "Webhooks saved successfully!")

        except Exception as e:
            self._add_log_message(f"Failed to save webhooks.json: {e}", "ERROR")
            if self.logger:
                self.logger.error(f"Failed to save webhooks.json: {e}")
            import tkinter.messagebox as messagebox

            messagebox.showerror("Error", f"Failed to save webhooks.json:\n{str(e)}")

    def _test_webhook(self, webhook_name: str):
        """Enviar mensagem de teste para um webhook"""
        try:
            if not HAS_REQUESTS:
                self._add_log_message(
                    "The 'requests' library is not installed. Install it with: pip install requests",
                    "ERROR",
                )
                return

            if not hasattr(self, "webhook_entries") or webhook_name not in self.webhook_entries:
                return

            url = ""
            try:
                url = self.webhook_entries[webhook_name].get().strip()
            except Exception:
                url = ""

            if not url:
                import tkinter.messagebox as messagebox

                messagebox.showwarning(
                    "Warning",
                    f"Webhook '{webhook_name}' is empty. Paste the URL before testing.",
                )
                return

            payload = {"content": f"Webhook test: {webhook_name} (SSM Backend GUI)"}

            try:
                resp = requests.post(url, json=payload, timeout=10)
            except Exception as e:
                self._add_log_message(f"❌ Failed to test webhook '{webhook_name}': {e}", "ERROR")
                import tkinter.messagebox as messagebox

                messagebox.showerror("Error", f"Failed to test webhook '{webhook_name}':\n{e}")
                return

            if 200 <= int(getattr(resp, "status_code", 0)) < 300:
                self._add_log_message(f"✅ Webhook '{webhook_name}' OK", "SUCCESS")
                import tkinter.messagebox as messagebox

                messagebox.showinfo("Success", f"Webhook '{webhook_name}' tested successfully!")
                return

            status_code = getattr(resp, "status_code", "N/A")
            try:
                body = resp.text
            except Exception:
                body = ""
            body = (body or "").strip()
            if len(body) > 400:
                body = body[:400] + "..."

            self._add_log_message(
                f"❌ Webhook '{webhook_name}' failed: HTTP {status_code} {body}", "ERROR"
            )
            import tkinter.messagebox as messagebox

            messagebox.showerror(
                "Error",
                f"Webhook '{webhook_name}' failed.\nHTTP {status_code}\n\n{body}",
            )
        except Exception:
            pass

    def _save_discord_bot_settings(self) -> bool:
        try:
            config = self._load_config()
            if not isinstance(config, dict):
                return False

            bot_cfg = config.get("discord_bot")
            if not isinstance(bot_cfg, dict):
                bot_cfg = {}
                config["discord_bot"] = bot_cfg

            token = ""
            guild_id = ""
            cat = "SSM"
            register_role_id = ""
            try:
                token = (self.discord_bot_token_entry.get() or "").strip()
            except Exception:
                token = ""
            try:
                guild_id = (self.discord_bot_guild_entry.get() or "").strip()
            except Exception:
                guild_id = ""
            try:
                cat = (self.discord_bot_category_entry.get() or "SSM").strip() or "SSM"
            except Exception:
                cat = "SSM"
            try:
                register_role_id = (self.discord_bot_register_role_entry.get() or "").strip()
            except Exception:
                register_role_id = ""

            if register_role_id:
                register_role_id = "".join([c for c in register_role_id if c.isdigit()])

            bot_cfg["bot_token"] = token
            bot_cfg["guild_id"] = guild_id
            bot_cfg["default_category_name"] = cat
            bot_cfg["register_role_id"] = register_role_id
            bot_cfg["include_disabled_events"] = bool(
                self.discord_bot_include_disabled_var.get()
            )
            bot_cfg["validate_existing_urls"] = bool(
                self.discord_bot_validate_urls_var.get()
            )
            bot_cfg["repair_invalid_urls"] = bool(self.discord_bot_repair_urls_var.get())

            config_path = (
                self.DATA_DIR / "config.json"
                if self.IS_EXE
                else self.ROOT_DIR / "data" / "config.json"
            )
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            try:
                self._last_bot_config_save_path = str(config_path)
            except Exception:
                pass
            return True
        except Exception as e:
            self._add_log_message(f"Failed to save bot settings: {e}", "ERROR")
            return False

    def _discord_bot_save(self):
        try:
            ok = bool(self._save_discord_bot_settings())
            if ok:
                try:
                    path = str(getattr(self, "_last_bot_config_save_path", "") or "").strip()
                    if path:
                        self.discord_bot_status_label.configure(text=f"Saved: {path}")
                    else:
                        self.discord_bot_status_label.configure(text="Saved.")
                except Exception:
                    pass
                try:
                    self._add_log_message("Discord bot settings saved", "SUCCESS")
                except Exception:
                    pass
            else:
                try:
                    self.discord_bot_status_label.configure(text="Failed to save.")
                except Exception:
                    pass
        except Exception:
            try:
                self.discord_bot_status_label.configure(text="Failed to save.")
            except Exception:
                pass

    def _discord_bot_test(self):
        try:
            import tkinter.messagebox as messagebox

            self._set_discord_bot_busy(True, "Testing bot connection... Please wait")

            self._save_discord_bot_settings()
            cfg = self._load_config() or {}
            bot_cfg = cfg.get("discord_bot", {}) if isinstance(cfg, dict) else {}
            token = str(bot_cfg.get("bot_token") or "")
            guild_id = str(bot_cfg.get("guild_id") or "")

            if not token or not guild_id:
                self._add_log_message(
                    "Discord bot settings missing: bot_token or guild_id", "ERROR"
                )
                messagebox.showerror(
                    "Discord Bot",
                    "Bot Token and Guild ID are required before testing.",
                )
                return

            from core.webhooks.discord_bot_provisioner import DiscordBotProvisioner

            prov = DiscordBotProvisioner(token, guild_id, logger=self.logger)
            ok, msg = prov.test_connection()
            if ok:
                self._add_log_message("✅ Discord bot OK", "SUCCESS")
                messagebox.showinfo("Discord Bot", "Bot connection OK.")
            else:
                self._add_log_message(f"❌ Discord bot failed: {msg}", "ERROR")
                messagebox.showerror("Discord Bot", f"Bot connection failed:\n\n{msg}")
        except Exception as e:
            self._add_log_message(f"❌ Discord bot test failed: {e}", "ERROR")
            try:
                import tkinter.messagebox as messagebox

                messagebox.showerror(
                    "Discord Bot",
                    f"Bot test failed:\n\n{str(e)}",
                )
            except Exception:
                pass
        finally:
            try:
                self._set_discord_bot_busy(False, "")
            except Exception:
                pass

    def _discord_bot_sync(self):
        try:
            import tkinter.messagebox as messagebox

            if not HAS_REQUESTS:
                self._add_log_message("requests not installed", "ERROR")
                messagebox.showerror(
                    "Discord Bot",
                    "The 'requests' library is not available in this build.\n\n"
                    "Install it (pip install requests) or rebuild the exe including requests.",
                )
                return

            self._set_discord_bot_busy(True, "Provisioning... Creating/Syncing channels. Please wait")

            self._save_discord_bot_settings()

            try:
                if hasattr(self, "webhook_entries") and isinstance(getattr(self, "webhook_entries", None), dict):
                    updated: Dict[str, Dict[str, Any]] = {}

                    def is_probably_discord_webhook(url: str) -> bool:
                        u = (url or "").strip().lower()
                        if not u:
                            return True
                        return (
                            u.startswith("https://discord.com/api/webhooks/")
                            or u.startswith("https://discordapp.com/api/webhooks/")
                        )

                    for name, entry in self.webhook_entries.items():
                        try:
                            url = entry.get().strip()
                        except Exception:
                            url = ""

                        if not is_probably_discord_webhook(url):
                            messagebox.showerror(
                                "Error",
                                f"Invalid webhook URL for '{name}'.\n\nURL must start with:\nhttps://discord.com/api/webhooks/",
                            )
                            self._set_discord_bot_busy(False, "")
                            return

                        try:
                            enabled_var = None
                            if hasattr(self, "webhook_enabled_vars"):
                                enabled_var = self.webhook_enabled_vars.get(name)
                            enabled_val = bool(enabled_var.get()) if enabled_var is not None else bool(url.strip())
                        except Exception:
                            enabled_val = bool(url.strip())

                        try:
                            disp_entry = None
                            if hasattr(self, "webhook_display_name_entries"):
                                disp_entry = self.webhook_display_name_entries.get(name)
                            display_name_val = (disp_entry.get() or "") if disp_entry is not None else ""
                        except Exception:
                            display_name_val = ""

                        updated[str(name)] = {
                            "url": url,
                            "enabled": enabled_val,
                            "display_name": display_name_val,
                        }

                    webhooks_path = (
                        self.EXE_DIR / "data" / "webhooks.json"
                        if self.IS_EXE
                        else self.ROOT_DIR / "data" / "webhooks.json"
                    )
                    from core.webhooks.manager import WebhooksManager

                    mgr_ui = WebhooksManager(str(webhooks_path))
                    mgr_ui.apply_events_meta_updates(updated, create_backup=True)
            except Exception:
                pass

            cfg_preview = self._load_config() or {}
            bot_cfg_preview = (
                cfg_preview.get("discord_bot", {}) if isinstance(cfg_preview, dict) else {}
            )
            token_preview = str(bot_cfg_preview.get("bot_token") or "")
            guild_preview = str(bot_cfg_preview.get("guild_id") or "")
            if not token_preview or not guild_preview:
                self._add_log_message(
                    "Discord bot settings missing: bot_token or guild_id", "ERROR"
                )
                messagebox.showerror(
                    "Discord Bot",
                    "Bot Token and Guild ID are required before provisioning.",
                )
                return

            def worker():
                try:
                    cfg = self._load_config() or {}
                    if not isinstance(cfg, dict):
                        self.after(
                            0,
                            lambda: self._add_log_message(
                                "Failed to load config.json", "ERROR"
                            ),
                        )
                        return

                    bot_cfg = cfg.get("discord_bot", {})
                    if not isinstance(bot_cfg, dict):
                        bot_cfg = {}

                    token = str(bot_cfg.get("bot_token") or "")
                    guild_id = str(bot_cfg.get("guild_id") or "")
                    default_cat = str(bot_cfg.get("default_category_name") or "SSM")
                    include_disabled = bool(bot_cfg.get("include_disabled_events", True))
                    validate_urls = bool(bot_cfg.get("validate_existing_urls", True))
                    repair_urls = bool(bot_cfg.get("repair_invalid_urls", True))

                    webhooks_path = (
                        self.EXE_DIR / "data" / "webhooks.json"
                        if self.IS_EXE
                        else self.ROOT_DIR / "data" / "webhooks.json"
                    )

                    from core.webhooks.manager import WebhooksManager
                    from core.webhooks.discord_bot_provisioner import DiscordBotProvisioner

                    mgr = WebhooksManager(str(webhooks_path))
                    v2 = mgr.load_v2()
                    defaults = v2.get("defaults")
                    if not isinstance(defaults, dict):
                        defaults = {}
                        v2["defaults"] = defaults
                    defaults["category_name"] = default_cat

                    # Aplicar categoria default em todos os eventos (GUI nao expõe categoria por evento)
                    try:
                        events = v2.get("events")
                        if isinstance(events, dict):
                            for _ek, _ev in events.items():
                                if not isinstance(_ev, dict):
                                    continue
                                _target = _ev.get("target")
                                if not isinstance(_target, dict):
                                    _target = {}
                                    _ev["target"] = _target
                                _cat = _target.get("category")
                                if not isinstance(_cat, dict):
                                    _cat = {}
                                    _target["category"] = _cat
                                _cat["name"] = default_cat
                    except Exception:
                        pass

                    prov = DiscordBotProvisioner(token, guild_id, logger=self.logger)

                    def progress_cb(m: str):
                        self.after(0, lambda: self._add_log_message(str(m), "INFO"))

                    self.after(
                        0,
                        lambda: self._add_log_message(
                            "Starting Discord provisioning...", "INFO"
                        ),
                    )
                    updated_v2, _res = prov.provision_all_events(
                        v2,
                        include_disabled=include_disabled,
                        validate_existing_urls=validate_urls,
                        repair_invalid_urls=repair_urls,
                        progress_cb=progress_cb,
                    )

                    mgr.replace_all_v2(updated_v2, create_backup=True)
                    self.after(
                        0,
                        lambda: self._add_log_message(
                            "✅ Provisioning completed", "SUCCESS"
                        ),
                    )
                    def _post_provision_prompt():
                        try:
                            self._set_discord_bot_busy(False, "")
                        except Exception:
                            pass

                        try:
                            do_activate = self._ask_yes_no_english(
                                title="Discord Bot",
                                message=
                                "Provisioning completed.\n\nTest and activate now?\n\n"
                                "Yes: enable all events with a webhook URL and send a test message to each.\n"
                                "No: keep events disabled (no sending).",
                            )
                        except Exception:
                            do_activate = False

                        if not do_activate:
                            try:
                                messagebox.showinfo(
                                    "Discord Bot",
                                    "OK. Events remain disabled.\n\n"
                                    "To activate later: fill URLs and click 'Save Webhooks'.",
                                )
                            except Exception:
                                pass
                            return

                        def activate_worker():
                            try:
                                self.after(
                                    0,
                                    lambda: self._set_discord_bot_busy(
                                        True, "Activating and testing... Please wait"
                                    ),
                                )
                                from core.webhooks.manager import WebhooksManager

                                mgr2 = WebhooksManager(str(webhooks_path))
                                v2_now = mgr2.load_v2()
                                events2 = (v2_now or {}).get("events")
                                enabled_keys = []
                                if isinstance(events2, dict):
                                    for k, ev2 in events2.items():
                                        if not isinstance(ev2, dict):
                                            continue
                                        target2 = ev2.get("target")
                                        if not isinstance(target2, dict):
                                            continue
                                        wh2 = target2.get("webhook")
                                        if not isinstance(wh2, dict):
                                            continue
                                        url2 = wh2.get("url")
                                        if isinstance(url2, str) and url2.strip():
                                            ev2["enabled"] = True
                                            enabled_keys.append(str(k))

                                mgr2.replace_all_v2(v2_now, create_backup=True)

                                # Test: send one minimal message per enabled webhook
                                import requests

                                errors = []
                                for k in enabled_keys:
                                    try:
                                        ev2 = events2.get(k)
                                        wh_url = (
                                            ((ev2.get("target") or {}).get("webhook") or {}).get("url")
                                            if isinstance(ev2, dict)
                                            else None
                                        )
                                        if not (isinstance(wh_url, str) and wh_url.strip()):
                                            continue
                                        payload = {
                                            "content": f"SSM test: {k} (activated)"
                                        }
                                        r = requests.post(wh_url.strip(), json=payload, timeout=15)
                                        if int(r.status_code) not in (200, 204):
                                            errors.append(
                                                f"{k}: HTTP {r.status_code}"
                                            )
                                    except Exception as te:
                                        errors.append(f"{k}: {te}")

                                def done_ui():
                                    try:
                                        self._set_discord_bot_busy(False, "")
                                    except Exception:
                                        pass
                                    try:
                                        if errors:
                                            self._add_log_message(
                                                f"⚠️ Activate/Test finished with errors: {len(errors)}",
                                                "WARNING",
                                            )
                                            messagebox.showwarning(
                                                "Discord Bot",
                                                "Activated, but some tests failed:\n\n"
                                                + "\n".join(errors[:12])
                                                + ("\n..." if len(errors) > 12 else ""),
                                            )
                                        else:
                                            self._add_log_message(
                                                "✅ Activated and tested successfully",
                                                "SUCCESS",
                                            )
                                            messagebox.showinfo(
                                                "Discord Bot",
                                                "Activated and tested successfully.",
                                            )
                                    except Exception:
                                        pass

                                    try:
                                        self._reload_webhooks_tab()
                                    except Exception:
                                        pass

                                self.after(0, done_ui)
                            except Exception as ae:
                                self.after(
                                    0,
                                    lambda: messagebox.showerror(
                                        "Discord Bot",
                                        f"Activate/Test failed:\n\n{str(ae)}",
                                    ),
                                )
                                self.after(0, lambda: self._set_discord_bot_busy(False, ""))

                        threading.Thread(target=activate_worker, daemon=True).start()

                    self.after(0, _post_provision_prompt)
                    self.after(0, self._reload_webhooks_tab)
                except Exception as e:
                    self.after(
                        0,
                        lambda: self._add_log_message(
                            f"❌ Provisioning failed: {e}", "ERROR"
                        ),
                    )
                    self.after(
                        0,
                        lambda: messagebox.showerror(
                            "Discord Bot",
                            f"Provisioning failed:\n\n{str(e)}",
                        ),
                    )
                    self.after(0, lambda: self._set_discord_bot_busy(False, ""))

            t = threading.Thread(target=worker, daemon=True)
            t.start()
        except Exception as e:
            self._add_log_message(f"❌ Provisioning failed: {e}", "ERROR")
            try:
                import tkinter.messagebox as messagebox

                messagebox.showerror(
                    "Discord Bot",
                    f"Provisioning failed:\n\n{str(e)}",
                )
            except Exception:
                pass

    def _set_discord_bot_busy(self, busy: bool, status_text: str = ""):
        try:
            lbl = getattr(self, "discord_bot_status_label", None)
            if lbl is not None:
                try:
                    lbl.configure(text=str(status_text or ""))
                except Exception:
                    pass

            test_btn = getattr(self, "discord_bot_test_btn", None)
            sync_btn = getattr(self, "discord_bot_sync_btn", None)

            if test_btn is not None:
                try:
                    test_btn.configure(state="disabled" if busy else "normal")
                    test_btn.configure(text="Working..." if busy else "Test Bot")
                except Exception:
                    pass

            if sync_btn is not None:
                try:
                    sync_btn.configure(state="disabled" if busy else "normal")
                    sync_btn.configure(
                        text="Working..." if busy else "Create/Sync channels"
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def _clear_logs(self):
        """Limpar logs da interface"""
        self.logs_textbox.configure(state="normal")
        self.logs_textbox.delete("0.0", "end")
        self.logs_textbox.configure(state="disabled")

    def _validate_path_field(self, entry):
        """Validar visualmente se o caminho existe"""
        path = entry.get()
        if path and not os.path.exists(path):
            entry.configure(border_color="red")
        else:
            # Restaurar cor padrão (depende do tema, mas hardcoded é seguro aqui)
            entry.configure(border_color=("#979da2", "#565b5e"))

    def _ensure_tabs_enabled(self):
        """Garantir que todas as tabs estejam sempre habilitadas"""
        if hasattr(self, "tab_buttons"):
            for btn in self.tab_buttons.values():
                try:
                    btn.configure(state="normal")
                except:
                    pass

    def _switch_tab(self, tab_id: str):
        """Trocar tab ativa"""
        # Garantir que as tabs estejam habilitadas
        self._ensure_tabs_enabled()

        # Esconder todas as tabs
        for content in self.tabs_content.values():
            content.pack_forget()

        # Mostrar tab selecionada
        self.tabs_content[tab_id].pack(fill="both", expand=True)
        self.current_tab = tab_id

        # Atualizar estilo dos botões (garantir que sempre estejam habilitados)
        for tid, btn in self.tab_buttons.items():
            if tid == tab_id:
                btn.configure(
                    state="normal",  # Garantir que está habilitado
                    fg_color=("#1f538d", "#14375e"),
                    hover_color=("#2a5a9a", "#1a4a7a"),
                    font=ctk.CTkFont(size=12, weight="bold"),
                )
            else:
                btn.configure(
                    state="normal",  # Garantir que está habilitado
                    fg_color=("gray", "gray"),
                    hover_color=("#3b3b3b", "#2a2a2a"),
                    font=ctk.CTkFont(size=12, weight="normal"),
                )

    def _create_maintenance_page(self, parent):
        """Create the content for the Maintenance page"""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=12)

        card_color = ("gray95", "gray17")
        card_border_color = ("gray82", "gray28")

        # ========== CARD 1: RESET PLAYERS & SHOP ORDERS ==========
        reset_card = ctk.CTkFrame(
            scroll,
            fg_color=card_color,
            corner_radius=12,
            border_width=1,
            border_color=card_border_color,
        )
        reset_card.pack(fill="x", pady=(0, 10), padx=6)

        header_frame = ctk.CTkFrame(reset_card, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(12, 6))

        icon_label = ctk.CTkLabel(
            header_frame, text="🔧", font=ctk.CTkFont(size=18)
        )
        icon_label.pack(side="left", padx=(0, 8))

        title_label = ctk.CTkLabel(
            header_frame,
            text="Player Registration & Shop Reset",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        title_label.pack(side="left")

        desc_label = ctk.CTkLabel(
            reset_card,
            text="Clean player links to Discord, delete old link tokens, remove shop orders/delivery items, and reset wallet balance to initial balance.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            wraplength=700,
            justify="left",
        )
        desc_label.pack(fill="x", padx=15, pady=(0, 10))

        # Inputs section
        input_frame = ctk.CTkFrame(reset_card, fg_color="transparent")
        input_frame.pack(fill="x", padx=15, pady=(0, 10))

        steam_id_label = ctk.CTkLabel(
            input_frame,
            text="Target SteamID (Optional for single player reset):",
            font=ctk.CTkFont(size=12),
        )
        steam_id_label.pack(side="left", padx=(0, 10))

        self.maintenance_steam_id_entry = ctk.CTkEntry(
            input_frame,
            width=230,
            placeholder_text="e.g. 76561198040636105",
        )
        self.maintenance_steam_id_entry.pack(side="left", padx=(0, 20))

        # Buttons section
        btn_frame = ctk.CTkFrame(reset_card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 12))

        reset_single_btn = ctk.CTkButton(
            btn_frame,
            text="Reset Specific Player",
            command=self._maintenance_reset_player,
            width=160,
            height=32,
            fg_color=("#1f538d", "#14375e"),
            hover_color=("#2a5a9a", "#1a4a7a"),
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        reset_single_btn.pack(side="left", padx=(0, 12))

        reset_all_btn = ctk.CTkButton(
            btn_frame,
            text="Reset All Players",
            command=self._maintenance_reset_all_players,
            width=160,
            height=32,
            fg_color=("#B71C1C", "#B71C1C"),
            hover_color=("#7F0000", "#7F0000"),
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        reset_all_btn.pack(side="left")

        # ========== CARD 2: SCUM SERVER LOGS CLEANUP (ULTRA-COMPACT) ==========
        logs_card = ctk.CTkFrame(
            scroll,
            fg_color=card_color,
            corner_radius=12,
            border_width=1,
            border_color=card_border_color,
        )
        logs_card.pack(fill="x", pady=(0, 10), padx=6)

        # Header with Title and inline Auto Cleanup Switch
        logs_header = ctk.CTkFrame(logs_card, fg_color="transparent")
        logs_header.pack(fill="x", padx=15, pady=(12, 4))

        logs_icon = ctk.CTkLabel(
            logs_header, text="🧹", font=ctk.CTkFont(size=18)
        )
        logs_icon.pack(side="left", padx=(0, 8))

        logs_title = ctk.CTkLabel(
            logs_header,
            text="SCUM Server Logs Cleanup",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        logs_title.pack(side="left")

        self.logs_cleanup_enabled_switch = ctk.CTkSwitch(
            logs_header,
            text="Auto Cleanup",
            font=ctk.CTkFont(size=12, weight="bold"),
            progress_color=("#2ecc71", "#27ae60"),
        )
        self.logs_cleanup_enabled_switch.pack(side="right", padx=(0, 5))

        logs_desc = ctk.CTkLabel(
            logs_card,
            text="Automatically cleans old logs (.log, .dmp, .txt, .bak) from Saved\\SaveFiles\\Logs to free disk space.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            wraplength=700,
            justify="left",
        )
        logs_desc.pack(fill="x", padx=15, pady=(0, 8))

        # Compact Parameters Row (Retention, Max Size, Schedule Time)
        params_row = ctk.CTkFrame(logs_card, fg_color="transparent")
        params_row.pack(fill="x", padx=15, pady=(0, 10))

        # Retention
        ret_label = ctk.CTkLabel(params_row, text="Retention:", font=ctk.CTkFont(size=12, weight="bold"))
        ret_label.pack(side="left", padx=(0, 6))
        self.logs_cleanup_retention_entry = ctk.CTkEntry(params_row, width=55, justify="center")
        self.logs_cleanup_retention_entry.pack(side="left", padx=(0, 4))
        ret_unit = ctk.CTkLabel(params_row, text="days", font=ctk.CTkFont(size=12), text_color="gray")
        ret_unit.pack(side="left", padx=(0, 18))

        # Max Size
        size_label = ctk.CTkLabel(params_row, text="Max Size:", font=ctk.CTkFont(size=12, weight="bold"))
        size_label.pack(side="left", padx=(0, 6))
        self.logs_cleanup_size_entry = ctk.CTkEntry(params_row, width=65, justify="center")
        self.logs_cleanup_size_entry.pack(side="left", padx=(0, 4))
        size_unit = ctk.CTkLabel(params_row, text="MB", font=ctk.CTkFont(size=12), text_color="gray")
        size_unit.pack(side="left", padx=(0, 18))

        # Schedule Time
        time_label = ctk.CTkLabel(params_row, text="Time:", font=ctk.CTkFont(size=12, weight="bold"))
        time_label.pack(side="left", padx=(0, 6))
        self.logs_cleanup_time_entry = ctk.CTkEntry(params_row, width=65, justify="center")
        self.logs_cleanup_time_entry.pack(side="left", padx=(0, 4))
        time_unit = ctk.CTkLabel(params_row, text="(Daily)", font=ctk.CTkFont(size=12), text_color="gray")
        time_unit.pack(side="left", padx=(0, 15))

        # Actions & Status Row
        action_row = ctk.CTkFrame(logs_card, fg_color="transparent")
        action_row.pack(fill="x", padx=15, pady=(0, 12))

        save_btn = ctk.CTkButton(
            action_row,
            text="Save Settings",
            command=self._save_logs_cleanup_settings,
            width=120,
            height=32,
            fg_color=("#1f538d", "#14375e"),
            hover_color=("#2a5a9a", "#1a4a7a"),
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        save_btn.pack(side="left", padx=(0, 10))

        clean_now_btn = ctk.CTkButton(
            action_row,
            text="Clean Now",
            command=self._run_logs_cleanup_now,
            width=110,
            height=32,
            fg_color=("#2E7D32", "#1B5E20"),
            hover_color=("#388E3C", "#2E7D32"),
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        clean_now_btn.pack(side="left", padx=(0, 15))

        self.logs_cleanup_status_label = ctk.CTkLabel(
            action_row,
            text="Status: Ready",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.logs_cleanup_status_label.pack(side="left")

        # Load initial values
        self._load_logs_cleanup_settings()

    def _maintenance_reset_player(self):
        """Reset a single player's registration and shop history"""
        steam_id = self.maintenance_steam_id_entry.get().strip()
        if not steam_id:
            self._show_custom_message(
                title="Error",
                message="Please enter a valid SteamID.",
                type_="ok",
            )
            return

        # Basic sanitization
        import re
        steam_id_clean = re.sub(r"[^0-9]", "", steam_id)
        if not steam_id_clean:
            self._show_custom_message(
                title="Error",
                message="SteamID must contain only numbers.",
                type_="ok",
            )
            return

        confirm = self._ask_yes_no_english(
            title="Reset Player Registration",
            message=f"Are you sure you want to reset registration, tokens, orders, and wallet balance for player {steam_id_clean}?",
        )
        if not confirm:
            return

        try:
            from utils.config_path_helper import ConfigPathHelper
            from core.database.connector import DatabaseConnector

            config = self._load_config() or {}
            path_helper = ConfigPathHelper(config)
            ssm_db_path = path_helper.get_ssm_db_path()

            with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cur = conn.cursor()
                
                # 1. Reset Discord link
                cur.execute(
                    "UPDATE players SET discord_user_id = NULL, discord_linked_at = NULL WHERE steam_id = ?",
                    (steam_id_clean,),
                )
                
                # 2. Delete consumed tokens
                cur.execute(
                    "DELETE FROM discord_link_tokens WHERE consumed_by_steam_id = ?",
                    (steam_id_clean,),
                )
                
                # 3. Delete orders and delivery items
                cur.execute(
                    "DELETE FROM shop_order_item WHERE order_id IN (SELECT order_id FROM shop_order WHERE steam_id = ?)",
                    (steam_id_clean,),
                )
                
                cur.execute(
                    "DELETE FROM shop_delivery_item WHERE order_id IN (SELECT order_id FROM shop_order WHERE steam_id = ?)",
                    (steam_id_clean,),
                )
                
                cur.execute(
                    "DELETE FROM shop_order WHERE steam_id = ?",
                    (steam_id_clean,),
                )
                
                # 4. Reset wallet
                economy = config.get("economy")
                initial_balance = 0
                if isinstance(economy, dict):
                    try:
                        initial_balance = int(economy.get("initial_balance", 0))
                    except Exception:
                        pass

                cur.execute(
                    "UPDATE wallet SET balance = ? WHERE steam_id = ?",
                    (initial_balance, steam_id_clean),
                )
                if cur.rowcount == 0:
                    cur.execute(
                        "INSERT OR IGNORE INTO wallet(steam_id, balance) VALUES(?, ?)",
                        (steam_id_clean, initial_balance),
                    )
                
                conn.commit()

            self._add_log_message(f"Maintenance: Reset player {steam_id_clean} successfully.", "SUCCESS")
            self._show_custom_message(
                title="Success",
                message=f"Player {steam_id_clean} has been successfully reset.",
                type_="ok",
            )
            self.maintenance_steam_id_entry.delete(0, "end")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error resetting player: {e}")
            self._add_log_message(f"Maintenance Error: Failed to reset player: {e}", "ERROR")
            self._show_custom_message(
                title="Error",
                message=f"Failed to reset player: {e}",
                type_="ok",
            )

    def _maintenance_reset_all_players(self):
        """Reset all players' registrations and shop history"""
        confirm = self._ask_yes_no_english(
            title="Reset ALL Players",
            message="WARNING: Are you sure you want to reset registration, tokens, orders, and wallet balance for ALL players? This action is IRREVERSIBLE.",
        )
        if not confirm:
            return

        # Double check for safety
        confirm_double = self._ask_yes_no_english(
            title="Confirm Critical Action",
            message="CRITICAL WARNING: This will disconnect all players from the Discord link and delete all shop history. Click YES to confirm.",
        )
        if not confirm_double:
            return

        try:
            from utils.config_path_helper import ConfigPathHelper
            from core.database.connector import DatabaseConnector

            config = self._load_config() or {}
            path_helper = ConfigPathHelper(config)
            ssm_db_path = path_helper.get_ssm_db_path()

            with DatabaseConnector.get_connection(ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cur = conn.cursor()
                
                # 1. Reset Discord links
                cur.execute("UPDATE players SET discord_user_id = NULL, discord_linked_at = NULL")
                players_affected = cur.rowcount
                
                # 2. Delete all tokens
                cur.execute("DELETE FROM discord_link_tokens")
                tokens_affected = cur.rowcount
                
                # 3. Delete all orders and delivery items
                cur.execute("DELETE FROM shop_order_item")
                order_items_affected = cur.rowcount
                
                cur.execute("DELETE FROM shop_delivery_item")
                delivery_items_affected = cur.rowcount
                
                cur.execute("DELETE FROM shop_order")
                orders_affected = cur.rowcount
                
                # 4. Reset all wallets
                economy = config.get("economy")
                initial_balance = 0
                if isinstance(economy, dict):
                    try:
                        initial_balance = int(economy.get("initial_balance", 0))
                    except Exception:
                        pass

                cur.execute("UPDATE wallet SET balance = ?", (initial_balance,))
                wallets_affected = cur.rowcount
                
                conn.commit()

            msg = f"Reset all players complete. Affected: {players_affected} players, {tokens_affected} tokens, {orders_affected} orders, {wallets_affected} wallets."
            self._add_log_message(f"Maintenance: {msg}", "SUCCESS")
            self._show_custom_message(
                title="Success",
                message="All registrations and shop history have been successfully reset.",
                type_="ok",
            )

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error resetting all players: {e}")
            self._add_log_message(f"Maintenance Error: Failed to reset all players: {e}", "ERROR")
            self._show_custom_message(
                title="Error",
                message=f"Failed to reset database: {e}",
                type_="ok",
            )

    def _load_logs_cleanup_settings(self):
        """Carregar configurações de limpeza de logs para os campos da aba Maintenance"""
        try:
            config = self._load_config() or {}
            cleanup = config.get("scum_logs_cleanup", {})

            enabled = bool(cleanup.get("enabled", True))
            if hasattr(self, "logs_cleanup_enabled_switch"):
                if enabled:
                    self.logs_cleanup_enabled_switch.select()
                else:
                    self.logs_cleanup_enabled_switch.deselect()

            retention = str(cleanup.get("retention_days", 14) or 14)
            if hasattr(self, "logs_cleanup_retention_entry"):
                self.logs_cleanup_retention_entry.delete(0, "end")
                self.logs_cleanup_retention_entry.insert(0, retention)

            max_size = cleanup.get("max_total_size_mb")
            max_size_str = str(max_size) if max_size is not None else "2048"
            if hasattr(self, "logs_cleanup_size_entry"):
                self.logs_cleanup_size_entry.delete(0, "end")
                self.logs_cleanup_size_entry.insert(0, max_size_str)

            sched_time = str(cleanup.get("schedule_time", "03:30") or "03:30")
            if hasattr(self, "logs_cleanup_time_entry"):
                self.logs_cleanup_time_entry.delete(0, "end")
                self.logs_cleanup_time_entry.insert(0, sched_time)

        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to load logs cleanup settings: {e}")

    def _save_logs_cleanup_settings(self):
        """Salvar configurações de limpeza de logs para o config.json e atualizar serviço em execução"""
        try:
            config = self._load_config() or {}
            if "scum_logs_cleanup" not in config:
                config["scum_logs_cleanup"] = {}

            enabled = bool(self.logs_cleanup_enabled_switch.get())
            retention_raw = self.logs_cleanup_retention_entry.get().strip()
            size_raw = self.logs_cleanup_size_entry.get().strip()
            time_raw = self.logs_cleanup_time_entry.get().strip()

            try:
                retention_val = max(1, int(retention_raw))
            except ValueError:
                self._show_custom_message(
                    title="Invalid Input",
                    message="Retention days must be a positive integer.",
                    type_="ok",
                )
                return

            try:
                size_val = int(size_raw) if size_raw else 2048
            except ValueError:
                self._show_custom_message(
                    title="Invalid Input",
                    message="Max size must be an integer in MB.",
                    type_="ok",
                )
                return

            if not time_raw:
                time_raw = "03:30"

            cleanup_patch = {
                "enabled": enabled,
                "retention_days": retention_val,
                "max_total_size_mb": size_val,
                "schedule_time": time_raw,
                "min_age_hours": 24,
                "auto_start": True,
                "file_extensions": [".log", ".txt", ".dmp", ".bak"],
            }
            config["scum_logs_cleanup"].update(cleanup_patch)

            config_path = (
                self.DATA_DIR / "config.json"
                if self.IS_EXE
                else self.ROOT_DIR / "data" / "config.json"
            )
            import json
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # Atualizar serviço se o backend estiver rodando
            try:
                from app.extensions import get_services
                svc = get_services()
                cleanup_svc = getattr(svc, "scum_logs_cleanup_service", None)
                if cleanup_svc and hasattr(cleanup_svc, "update_config"):
                    cleanup_svc.update_config(config["scum_logs_cleanup"])
            except Exception:
                pass

            self._add_log_message("Maintenance: SCUM logs cleanup settings saved successfully", "SUCCESS")
            self.logs_cleanup_status_label.configure(text="Status: Settings saved", text_color="#2ecc71")
            self._show_custom_message(
                title="Success",
                message="SCUM logs cleanup settings saved successfully!",
                type_="ok",
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save logs cleanup settings: {e}")
            self._add_log_message(f"Maintenance Error: Failed to save logs cleanup settings: {e}", "ERROR")
            self._show_custom_message(
                title="Error",
                message=f"Failed to save settings: {e}",
                type_="ok",
            )

    def _run_logs_cleanup_now(self):
        """Executar limpeza de logs sob demanda em thread de background"""
        confirm = self._ask_yes_no_english(
            title="Clean SCUM Logs",
            message="Are you sure you want to clean old SCUM server logs now?\n\nFiles older than configured retention or safety limits will be deleted.",
        )
        if not confirm:
            return

        self.logs_cleanup_status_label.configure(text="Status: Cleaning in progress...", text_color="#3498db")

        import threading

        def _worker():
            try:
                from utils.config_path_helper import ConfigPathHelper
                from core.logs.scum_logs_cleanup_service import ScumLogsCleanupService
                from app.extensions import get_services

                config = self._load_config() or {}
                path_helper = ConfigPathHelper(config)

                svc = get_services()
                cleanup_svc = getattr(svc, "scum_logs_cleanup_service", None)
                if not cleanup_svc:
                    cleanup_svc = ScumLogsCleanupService(config, path_helper, logger=self.logger)

                res = cleanup_svc.run_now()
                data = (res or {}).get("data", {})
                details = data.get("details", {})

                deleted = details.get("deleted_files", 0)
                skipped = details.get("skipped_files", 0)
                bytes_freed = max(0, details.get("bytes_before", 0) - details.get("bytes_after", 0))

                if bytes_freed >= 1024 * 1024 * 1024:
                    freed_str = f"{bytes_freed / (1024 * 1024 * 1024):.2f} GB"
                else:
                    freed_str = f"{bytes_freed / (1024 * 1024):.2f} MB"

                from datetime import datetime
                ts = datetime.now().strftime("%H:%M")
                status_text = f"Status: Last run {ts} | {deleted} deleted ({freed_str} freed)"

                def _on_success():
                    self.logs_cleanup_status_label.configure(text=status_text, text_color="#2ecc71")
                    self._add_log_message(
                        f"Maintenance: SCUM logs cleanup completed: {deleted} files deleted ({freed_str} freed).",
                        "SUCCESS",
                    )
                    self._show_custom_message(
                        title="Logs Cleanup",
                        message=f"Cleanup completed successfully!\n\nDeleted files: {deleted}\nDisk space freed: {freed_str}\nProtected files: {skipped}",
                        type_="ok",
                    )

                self.after(0, _on_success)

            except Exception as e:
                err_msg = str(e)
                if self.logger:
                    self.logger.error(f"Error during logs cleanup: {err_msg}")

                def _on_error():
                    self.logs_cleanup_status_label.configure(text="Status: Cleanup failed", text_color="#e74c3c")
                    self._add_log_message(f"Maintenance Error: Logs cleanup failed: {err_msg}", "ERROR")
                    self._show_custom_message(
                        title="Error",
                        message=f"Logs cleanup failed:\n{err_msg}",
                        type_="ok",
                    )

                self.after(0, _on_error)

        threading.Thread(target=_worker, daemon=True, name="ManualLogsCleanupThread").start()

    def _create_database_tab(self, parent, register_tab: bool = True):
        database_frame = ctk.CTkFrame(parent, fg_color="transparent")
        if register_tab:
            self.tabs_content["database"] = database_frame
        else:
            database_frame.pack(fill="both", expand=True)

        scrollable_frame = ctk.CTkScrollableFrame(
            database_frame, fg_color="transparent"
        )
        scrollable_frame.pack(fill="both", expand=True, padx=12, pady=12)

        card_color = ("gray95", "gray17")
        card_border_color = ("gray82", "gray28")

        database_card = ctk.CTkFrame(
            scrollable_frame,
            fg_color=card_color,
            corner_radius=12,
            border_width=1,
            border_color=card_border_color,
        )
        database_card.pack(fill="x", pady=(0, 12), padx=6)

        db_header_frame = ctk.CTkFrame(database_card, fg_color="transparent")
        db_header_frame.pack(fill="x", padx=15, pady=(15, 10))

        db_icon_label = ctk.CTkLabel(
            db_header_frame, text="🗄️", font=ctk.CTkFont(size=20)
        )
        db_icon_label.pack(side="left", padx=(0, 10))

        database_title = ctk.CTkLabel(
            db_header_frame, text="Database", font=ctk.CTkFont(size=16, weight="bold")
        )
        database_title.pack(side="left")

        db_action_frame = ctk.CTkFrame(database_card, fg_color="transparent")
        db_action_frame.pack(fill="x", padx=15, pady=10)

        self.btn_init_db_main = ctk.CTkButton(
            db_action_frame,
            text="Create / Repair Database",
            command=self._initialize_database_main,
            width=200,
            height=40,
            fg_color="green",
            hover_color="darkgreen",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_init_db_main.pack(side="left", padx=(0, 15))

        self.db_count_label_main = ctk.CTkLabel(
            db_action_frame,
            text="0/33 tables",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        self.db_count_label_main.pack(side="left", padx=5)

        ctk.CTkFrame(database_card, height=10, fg_color="transparent").pack()

        tables_frame = ctk.CTkFrame(
            scrollable_frame,
            fg_color=card_color,
            corner_radius=12,
            border_width=1,
            border_color=card_border_color,
        )
        tables_frame.pack(fill="both", expand=True, pady=(0, 12), padx=6)

        tables_header = ctk.CTkFrame(tables_frame, fg_color="transparent")
        tables_header.pack(fill="x", padx=15, pady=(15, 5))

        tables_title = ctk.CTkLabel(
            tables_header, text="Tables", font=ctk.CTkFont(size=16, weight="bold")
        )
        tables_title.pack(side="left")

        self.tables_listbox = ctk.CTkScrollableFrame(tables_frame, height=260)
        self.tables_listbox.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        try:
            self._check_database_status_main()
        except Exception:
            pass

    def _start_backend_output_reader(self):
        """Iniciar thread para ler saída do processo do backend (REMOVIDO - nova arquitetura)"""
        # NOVA ARQUITETURA: Backend roda em thread, não há stdout para ler
        # O output do Flask será redirecionado automaticamente pelo TextRedirector
        return

        # Código antigo (remover depois):
        if False:  # Desabilitar código antigo
            if not self.backend_process:
                return

            def read_output():
                try:
                    if self.backend_process and self.backend_process.stdout:
                        for line in iter(self.backend_process.stdout.readline, ""):
                            if not line:
                                break
                            line = line.strip()
                            if line:
                                # Determinar nível baseado no conteúdo
                                level = "INFO"
                                line_lower = line.lower()
                                if (
                                    "error" in line_lower
                                    or "✗" in line
                                    or "❌" in line
                                    or "erro" in line_lower
                                ):
                                    level = "ERROR"
                                elif (
                                    "warning" in line_lower
                                    or "⚠" in line
                                    or "aviso" in line_lower
                                ):
                                    level = "WARNING"
                                elif (
                                    "success" in line_lower
                                    or "✓" in line
                                    or "✅" in line
                                    or (
                                        "ok" in line_lower
                                        and "arquivo" not in line_lower
                                    )
                                ):
                                    level = "SUCCESS"

                                # Adicionar ao GUI de forma thread-safe
                                self.after(
                                    0,
                                    lambda msg=line, lvl=level: self._add_log_message(
                                        msg, lvl
                                    ),
                                )
                except Exception as e:
                    # Se houver erro, apenas ignorar
                    pass

            # Iniciar thread para ler saída
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()

    def _setup_console_redirect(self):
        """Configurar redirecionamento de stdout, stderr e logging para o GUI"""
        try:
            # Criar rediretores
            self.stdout_redirector = TextRedirector(self, "stdout")
            self.stderr_redirector = TextRedirector(self, "stderr")

            # Salvar stdout e stderr originais (para possível restauração)
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr

            # Redirecionar stdout e stderr
            sys.stdout = self.stdout_redirector
            sys.stderr = self.stderr_redirector

            # Configurar logging para também redirecionar para o GUI
            # Criar handler customizado para logging
            class GUILogHandler(logging.Handler):
                def __init__(self, gui_window):
                    super().__init__()
                    self.gui_window = gui_window

                def emit(self, record):
                    try:
                        msg = self.format(record)
                        # Determinar nível
                        level_map = {
                            logging.DEBUG: "INFO",
                            logging.INFO: "INFO",
                            logging.WARNING: "WARNING",
                            logging.ERROR: "ERROR",
                            logging.CRITICAL: "ERROR",
                        }
                        level = level_map.get(record.levelno, "INFO")
                        # Adicionar ao GUI de forma thread-safe
                        if hasattr(self.gui_window, "_add_log_message"):

                            def add_log(msg=msg, lvl=level):
                                try:
                                    self.gui_window._add_log_message(msg, lvl)
                                except:
                                    pass

                            self.gui_window.after(0, add_log)
                    except:
                        pass

            # Adicionar handler customizado a todos os loggers
            gui_handler = GUILogHandler(self)
            gui_handler.setFormatter(logging.Formatter("%(message)s"))

            # Obter root logger e adicionar handler
            root_logger = logging.getLogger()
            root_logger.addHandler(gui_handler)
            root_logger.setLevel(logging.INFO)  # Capturar INFO e acima

            # Também configurar loggers específicos comuns
            for logger_name in ["scum_backend", "__main__", "core", "utils"]:
                logger = logging.getLogger(logger_name)
                logger.addHandler(gui_handler)
                logger.setLevel(logging.INFO)

            # Log inicial
            self._add_log_message("Console and logging redirected to GUI", "INFO")
        except Exception as e:
            # Se houver erro, apenas logar e continuar
            if hasattr(self, "logs_textbox"):
                try:
                    self._add_log_message(
                        f"Failed to set up redirect: {e}", "ERROR"
                    )
                except:
                    pass

    def _add_log_message(self, message: str, level: str = "INFO"):
        """
        Add message to the logs area

        Args:
            message: Message to add
            level: Nível da mensagem (INFO, SUCCESS, ERROR, WARNING)
        """
        try:
            if not hasattr(self, "logs_textbox") or not self.logs_textbox:
                return

            timestamp = datetime.now().strftime("%H:%M:%S")

            level_prefix = {
                "INFO": "[INFO]",
                "SUCCESS": "[✓]",
                "ERROR": "[✗]",
                "WARNING": "[⚠]",
            }.get(level, "[INFO]")

            log_line = f"[{timestamp}] {level_prefix} {message}\n"

            if getattr(self, "_is_resizing", False):
                try:
                    self._log_buffer.append(log_line)
                    if self._log_flush_job is None:
                        self._log_flush_job = self.after(250, self._flush_log_buffer)
                except Exception:
                    pass
                return

            self.logs_textbox.configure(state="normal")
            self.logs_textbox.insert("end", log_line)

            lines = self.logs_textbox.get("1.0", "end-1c").split("\n")
            if len(lines) > self.logs_max_lines:
                excess = len(lines) - self.logs_max_lines
                self.logs_textbox.delete("1.0", f"{excess + 1}.0")

            self.logs_textbox.see("end")
            self.logs_textbox.configure(state="disabled")

        except Exception:
            pass

    def _setup_console_redirect(self):
        """Configurar redirecionamento de stdout/stderr para o GUI"""
        try:
            # Salvar referências originais
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr

            # Criar rediretores
            self.stdout_redirector = TextRedirector(self, "stdout")
            self.stderr_redirector = TextRedirector(self, "stderr")

            # Redirecionar
            sys.stdout = self.stdout_redirector
            sys.stderr = self.stderr_redirector

        except Exception as e:
            # Se falhar, continuar sem redirecionamento
            if hasattr(self, "_add_log_message"):
                self._add_log_message(
                    f"Failed to set up console redirect: {e}", "WARNING"
                )

    def _restore_console_redirect(self):
        """Restaurar stdout/stderr originais"""
        try:
            if hasattr(self, "original_stdout"):
                sys.stdout = self.original_stdout
            if hasattr(self, "original_stderr"):
                sys.stderr = self.original_stderr
        except Exception:
            pass

    def _validate_and_repair_json(
        self, file_path: Path
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Validar e tentar reparar JSON corrompido
        Retorna: (sucesso, config_dict, mensagem_erro)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Tentar carregar normalmente
            try:
                config = json.loads(content)
                return True, config, None
            except json.JSONDecodeError as e:
                # JSON corrompido - tentar reparar
                error_msg = (
                    f"JSON corrompido na linha {e.lineno}, coluna {e.colno}: {e.msg}"
                )

                # Tentar reparar problemas comuns
                repaired_content = content

                # 1. Remover vírgulas duplicadas antes de fechamento de array/objeto
                repaired_content = re.sub(r",\s*([}\]])", r"\1", repaired_content)

                # 2. Adicionar vírgulas faltantes entre objetos/arrays (caso mais comum)
                # Padrão: } seguido de { (sem vírgula)
                repaired_content = re.sub(r"}\s*\n\s*{", r"},\n    {", repaired_content)
                repaired_content = re.sub(r"}\s*{", r"},\n    {", repaired_content)

                # Padrão: ] seguido de [ (sem vírgula)
                repaired_content = re.sub(
                    r"]\s*\n\s*\[", r"],\n    [", repaired_content
                )
                repaired_content = re.sub(r"]\s*\[", r"],\n    [", repaired_content)

                # Padrão: "value" seguido de "key" (sem vírgula entre propriedades)
                repaired_content = re.sub(r'"\s*\n\s*"', r'",\n    "', repaired_content)

                # Padrão: número/string/boolean seguido de "key" (sem vírgula)
                repaired_content = re.sub(
                    r'(["\d\]}\w])\s*\n\s*"', r'\1,\n    "', repaired_content
                )

                # 3. Remover vírgulas no final de arrays/objetos antes de fechar
                repaired_content = re.sub(r",(\s*[}\]])", r"\1", repaired_content)

                # 4. Corrigir vírgulas faltantes antes de fechamento de objetos/arrays
                # Se na linha do erro há um "}" ou "]" sem vírgula antes, adicionar
                lines = repaired_content.split("\n")
                if e.lineno <= len(lines):
                    error_line = lines[e.lineno - 1]
                    # Se a linha começa com } ou ] e a anterior não termina com vírgula
                    if e.lineno > 1:
                        prev_line = lines[e.lineno - 2].rstrip()
                        if (
                            error_line.strip().startswith(("}", "]"))
                            and prev_line
                            and not prev_line.rstrip().endswith((",", "{", "[", ":"))
                        ):
                            # Adicionar vírgula no final da linha anterior
                            lines[e.lineno - 2] = prev_line.rstrip() + ","
                            repaired_content = "\n".join(lines)

                # Tentar carregar novamente
                try:
                    config = json.loads(repaired_content)
                    # Se funcionou, salvar o arquivo reparado
                    backup_path = (
                        file_path.parent
                        / f"config.json.backup.before_repair.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    )
                    shutil.copy2(file_path, backup_path)

                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)

                    return (
                        True,
                        config,
                        f"JSON repaired automatically. Backup: {backup_path.name}",
                    )
                except json.JSONDecodeError:
                    # Não foi possível reparar automaticamente
                    return (
                        False,
                        None,
                        f"{error_msg}\n\nUnable to repair automatically. Check the file manually.",
                    )

        except Exception as e:
            return False, None, f"Failed to validate JSON: {e}"

    def _load_config(self) -> Optional[Dict]:
        """Carregar configuração do config.json com validação e reparo"""
        try:
            # Usar caminho correto (EXE_DIR se executável, ROOT_DIR se script)
            config_path = (
                self.DATA_DIR / "config.json"
                if self.IS_EXE
                else self.ROOT_DIR / "data" / "config.json"
            )
            if config_path.exists():
                # Validar e reparar JSON se necessário
                success, config, message = self._validate_and_repair_json(config_path)

                if success:
                    if message:
                        self._add_log_message(f"⚠️ {message}", "WARNING")
                    
                    try:
                        import main
                        if main.ensure_default_config_sections(str(config_path), config):
                            success, config, _ = self._validate_and_repair_json(config_path)
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Erro ao garantir seções padrão do config no GUI: {e}")
                            
                    return config
                else:
                    self._add_log_message(
                        f"Failed to load config.json: {message}", "ERROR"
                    )
                    if self.logger:
                        self.logger.error(f"Failed to load config.json: {message}")
            else:
                self._add_log_message(
                    f"config.json not found at: {config_path}", "WARNING"
                )
        except Exception as e:
            self._add_log_message(f"Failed to load config.json: {e}", "ERROR")
            if self.logger:
                self.logger.error(f"Failed to load config.json: {e}")
        return None

    def _get_license_server_url(self) -> str:
        """
        Obter URL do servidor de licenciamento do módulo centralizado
        """
        try:
            from core.config.server_urls import get_license_server_url

            return get_license_server_url()
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Failed to import LICENSE_SERVER_URL: {e}")
            # Fallback para produção se não conseguir importar
            return "https://scumsm.com"

    def _get_gestao_server_url(self) -> str:
        """
        Obter URL do servidor de Gestão do módulo centralizado
        """
        try:
            from core.config.server_urls import get_gestao_server_url

            return get_gestao_server_url()
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Failed to import GESTAO_SERVER_URL: {e}")
            # Fallback para produção se não conseguir importar
            return "https://scumsm.com"

    def _validate_equipment_license(self) -> Tuple[bool, str, Optional[str]]:
        """
        Validar licença do equipamento com servidor

        Returns:
            Tupla (is_valid: bool, message: str, reason: Optional[str])
        """
        return True, "Device authorized (Open Source / Standalone)", None

    def _is_backend_running(self) -> bool:
        """Verificar se o backend está rodando na porta configurada e responde ao health check"""
        port = 3000
        try:
            config = self._load_config()
            if config:
                port = config.get("api", {}).get("port", 3000)
        except Exception:
            pass

        try:
            # 1. Teste rápido de socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result != 0:
                return False

            # 2. Se a porta está aberta, verificar se é realmente o SSM Backend
            import urllib.request
            import json
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/health",
                    headers={"User-Agent": "SSM-Backend-GUI-Check"}
                )
                with urllib.request.urlopen(req, timeout=0.3) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        if isinstance(data, dict) and "status" in data:
                            return True
            except Exception as e:
                if getattr(self, "logger", None):
                    self.logger.debug(f"Port {port} is open but health check failed (likely another app): {e}")
            return False
        except Exception:
            return False

    def _wait_for_backend_port_and_verify(self, timeout_seconds=30):
        """
        Aguardar porta 3000 abrir e verificar se não há múltiplos processos
        Executado em thread separada para não bloquear GUI

        Args:
            timeout_seconds: Tempo máximo para aguardar porta abrir
        """
        import time

        start_time = time.time()
        check_interval = 0.5  # Verificar a cada 0.5 segundos

        # Aguardar porta abrir
        while time.time() - start_time < timeout_seconds:
            if self._is_backend_running():
                # Porta abriu - aguardar 2 segundos para garantir que processo está estável
                time.sleep(2)

                # Verificar se há múltiplos processos
                backend_processes = self._find_backend_processes()

                # Obter porta configurada
                port = 3000
                try:
                    config = self._load_config()
                    if config:
                        port = config.get("api", {}).get("port", 3000)
                except Exception:
                    pass

                # Filtrar apenas processos que realmente são backend (usando porta configurada ou nome)
                real_backend_processes = []
                for proc in backend_processes:
                    try:
                        is_backend = False
                        if HAS_PSUTIL and isinstance(proc, psutil.Process):
                            # Verificar se está usando porta configurada em estado LISTEN
                            try:
                                for conn in proc.connections():
                                    if (
                                        hasattr(conn, "laddr")
                                        and conn.laddr.port == port
                                        and getattr(conn, "status", "").upper() == "LISTEN"
                                    ):
                                        is_backend = True
                                        break
                            except:
                                pass

                            # Verificar por nome também
                            if not is_backend:
                                proc_name = proc.name().lower()
                                if (
                                    "ssm backend.exe" in proc_name
                                    or "ssm_backend.exe" in proc_name
                                ):
                                    is_backend = True
                                elif "python" in proc_name:
                                    try:
                                        cmdline = proc.cmdline()
                                        cmdline_str = (
                                            " ".join(cmdline) if cmdline else ""
                                        )
                                        if (
                                            "main.py" in cmdline_str
                                            or "ssm_backend" in cmdline_str
                                        ):
                                            is_backend = True
                                    except:
                                        pass

                        if is_backend:
                            real_backend_processes.append(proc)
                    except Exception:
                        pass

                if len(real_backend_processes) > 1:
                    # Múltiplos processos detectados - encerrar o processo que acabou de iniciar
                    error_msg = f"⚠️ Múltiplos processos backend detectados ({len(real_backend_processes)} processos). Encerrando processo duplicado."
                    self.after(0, lambda: self._add_log_message(error_msg, "WARNING"))

                    # Encerrar o processo que acabou de iniciar
                    # NOVA ARQUITETURA: Backend roda em thread, não há processo para terminar
                    # O backend Flask será parado via _stop_backend_flask()
                    # Código antigo (remover depois):
                    if False:  # Desabilitar código antigo
                        if self.backend_process:
                            try:
                                self.backend_process.terminate()
                                time.sleep(1)
                                if self.backend_process.poll() is None:
                                    self.backend_process.kill()
                            except:
                                pass
                            self.after(
                                0, lambda: setattr(self, "backend_process", None)
                            )

                    self.after(
                        0,
                        lambda: self.btn_start_backend.configure(
                            state="normal", text="Start"
                        ),
                    )
                    self.after(
                        0, lambda: setattr(self, "validation_in_progress", False)
                    )
                    return
                else:
                    # Apenas um processo - tudo certo
                    return

            time.sleep(check_interval)

        # Timeout - porta não abriu
        # NOVA ARQUITETURA: Verificar thread ao invés de processo
        if self.backend_thread and self.backend_thread.is_alive():
            # Thread ainda está rodando mas porta não abriu - pode estar inicializando ainda
            # Aguardar mais um pouco
            time.sleep(2)
            if not self._is_backend_running():
                # Porta ainda não abriu - pode ser erro
                error_msg = "❌ Timeout: Backend não iniciou na porta 3000 dentro do tempo esperado."
                self.after(0, lambda: self._add_log_message(error_msg, "ERROR"))
                self.after(0, lambda: self._stop_backend_flask())
                self.after(
                    0,
                    lambda: self.btn_start_backend.configure(
                        state="normal", text="Start"
                    ),
                )
                self.after(0, lambda: setattr(self, "validation_in_progress", False))

        # Código antigo (remover depois):
        if False:  # Desabilitar código antigo
            if self.backend_process and self.backend_process.poll() is None:
                # Processo ainda está rodando mas porta não abriu - pode estar inicializando ainda
                # Aguardar mais um pouco
                time.sleep(2)
                if not self._is_backend_running():
                    # Porta ainda não abriu - pode ser erro
                    error_msg = "❌ Timeout: Backend did not start on port 3000 within the expected time."
                    self.after(0, lambda: self._add_log_message(error_msg, "ERROR"))
                    if self.backend_process:
                        try:
                            self.backend_process.terminate()
                            self.backend_process.wait(timeout=5)
                            self.backend_process = None
                        except Exception as e:
                            self.after(
                                0,
                                lambda: self._add_log_message(
                                    f"Erro ao encerrar processo com timeout: {e}",
                                    "ERROR",
                                ),
                            )
                    self.after(
                        0,
                        lambda: self.btn_start_backend.configure(
                            state="normal", text="Start"
                        ),
                    )
                    self.after(
                        0, lambda: setattr(self, "validation_in_progress", False)
                    )
                error_msg = "⚠️ Backend started but port 3000 did not open after 30 seconds. Check the logs."
                self.after(0, lambda: self._add_log_message(error_msg, "WARNING"))
        else:
            # Processo terminou antes da porta abrir - erro
            error_msg = "⚠️ Backend started but exited before port 3000 opened. Check the logs."
            self.after(0, lambda: self._add_log_message(error_msg, "WARNING"))

    def _update_backend_status(self):
        """Atualizar status do backend"""
        is_running = self._is_backend_running()
        self.backend_running = is_running

        if getattr(self, "backend_stopping", False):
            try:
                self.backend_status_indicator.configure(text_color="orange")
                self.backend_status_text.configure(text="Stopping")
                self.btn_start_backend.configure(state="disabled", fg_color="gray")
                # Manter o botao Stop vermelho e clicavel durante o shutdown.
                # Cliques repetidos sao ignorados por _stop_backend (guard backend_stopping).
                self.btn_stop_backend.configure(state="normal", text="Stopping...", fg_color="#dc3545")
                self._show_stop_only()
            except Exception:
                pass
            return

        if is_running:
            self.backend_status_indicator.configure(text_color="green")
            self.backend_status_text.configure(text="Running")
            self.btn_start_backend.configure(state="disabled", fg_color="gray")
            self.btn_stop_backend.configure(state="normal", fg_color="red")
            self._show_stop_only()
        else:
            self.backend_status_indicator.configure(text_color="red")
            self.backend_status_text.configure(text="Stopped")

            # Verificar se licença foi validada para habilitar botão Start
            # Se não foi validada ou foi bloqueada, manter desabilitado
            if not self.license_validated:
                # Verificar se botão está bloqueado (text="Blocked")
                current_text = self.btn_start_backend.cget("text")
                if current_text != "Blocked":
                    self.btn_start_backend.configure(state="normal", fg_color="green")
            else:
                self.btn_start_backend.configure(state="normal", fg_color="green")
                self.license_validated = False  # Resetar para próxima validação

            self.btn_stop_backend.configure(state="disabled", fg_color="gray", text="Stop")
            self._show_start_only()

        # Atualizar menu do system tray quando estado mudar
        if self.system_tray_manager:
            self._update_tray_menu()

    def _start_backend(self):
        """Iniciar processo do backend (com validação de licença)"""
        # Se SCUM/SteamCMD não estiver instalado, executar instalação padrão e não iniciar o backend automaticamente.
        try:
            if not self._is_scum_installed():
                self._add_log_message(
                    "⚠️ SCUM Server is not installed. Starting default install (C:\\Servers)...",
                    "WARNING",
                )
                try:
                    self.btn_start_backend.configure(
                        state="disabled",
                        text="Installing...",
                        fg_color="#FFA500",
                    )
                except Exception:
                    pass

                def _run_default_install_then_reset():
                    try:
                        self._install_or_update_scum_server(
                            base_dir="C:\\Servers", prompt_for_base_dir=False
                        )
                    finally:
                        try:
                            self.after(0, self._update_installation_ui)
                        except Exception:
                            pass
                        try:
                            self.after(
                                0,
                                lambda: self.btn_start_backend.configure(
                                    state="normal",
                                    text="Start",
                                    fg_color="green",
                                ),
                            )
                        except Exception:
                            pass
                        try:
                            self.after(0, lambda: setattr(self, "validation_in_progress", False))
                        except Exception:
                            pass

                threading.Thread(target=_run_default_install_then_reset, daemon=True).start()
                return
        except Exception:
            pass

        # SEGURANÇA CRÍTICA: Definir flag ANTES de qualquer verificação para prevenir condição de corrida
        # Se já está em progresso, retornar imediatamente
        if self.validation_in_progress:
            self._add_log_message(
                "⚠️ Validation already in progress. Please wait...", "WARNING"
            )
            return

        # FEEDBACK VISUAL IMEDIATO: Atualizar botão ANTES de qualquer outra ação
        self.btn_start_backend.configure(
            state="disabled",
            text="Validating...",
            fg_color="#FFA500",  # Laranja para indicar processo em andamento
        )
        self.update()  # Forçar atualização imediata da GUI

        # Marcar validação em andamento IMEDIATAMENTE para prevenir múltiplos cliques
        self.validation_in_progress = True

        # SEGURANÇA: Verificação IMEDIATA antes de qualquer ação
        # 1. Verificar porta 3000 (MAIS CONFIÁVEL - se porta está aberta, backend está rodando)
        if self._is_backend_running():
            error_msg = "⚠️ Backend já está rodando (porta 3000 ativa). Não é possível iniciar outro processo."
            self._add_log_message(error_msg, "WARNING")
            self.validation_in_progress = False  # Resetar flag
            return

        if self.backend_running:
            self.validation_in_progress = False  # Resetar flag
            return

        # NOVA ARQUITETURA: Verificar thread ao invés de processo
        if self.backend_thread and self.backend_thread.is_alive():
            # Thread ainda está rodando
            self._add_log_message(
                "⚠️ Backend já está rodando (thread interna detectada).", "WARNING"
            )
            self.validation_in_progress = False  # Resetar flag
            return

        # Código antigo (remover depois):
        if False:  # Desabilitar código antigo
            if hasattr(self, "backend_process") and self.backend_process is not None:
                try:
                    if self.backend_process.poll() is None:
                        # Processo ainda está rodando
                        self._add_log_message(
                            "⚠️ Backend já está rodando (processo interno detectado).",
                            "WARNING",
                        )
                        self.validation_in_progress = False  # Resetar flag
                        return
                except Exception:
                    pass

        # SEGURANÇA: Verificar se já existe processo EXTERNO do backend rodando
        # NOVA ARQUITETURA: Backend roda em thread dentro do Panel SSM
        # Apenas processos EXTERNOS usando a porta configurada em estado LISTEN são considerados
        backend_processes = self._find_backend_processes()
        if backend_processes:
            port = 3000
            try:
                config = self._load_config()
                if config:
                    port = config.get("api", {}).get("port", 3000)
            except Exception:
                pass

            processes_detected = []
            for proc in backend_processes:
                try:
                    if HAS_PSUTIL and isinstance(proc, psutil.Process):
                        # Verificar novamente por porta configurada em estado LISTEN (confirmação)
                        try:
                            for conn in proc.connections():
                                if (
                                    hasattr(conn, "laddr")
                                    and conn.laddr.port == port
                                    and getattr(conn, "status", "").upper() == "LISTEN"
                                ):
                                    processes_detected.append(proc)
                                    break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except Exception:
                    pass

            if processes_detected:
                # Processo EXTERNO do backend encontrado - não iniciar novo
                error_msg = f"⚠️ Backend is already running (external process detected on port {port}). You cannot start another process."
                self._add_log_message(error_msg, "WARNING")
                self._add_log_message(
                    "Use the 'Stop' button to stop it before starting again.",
                    "INFO",
                )
                self.btn_start_backend.configure(state="normal", text="Start")
                self.validation_in_progress = False
                return

        try:
            # Botão já foi atualizado no início da função para feedback visual imediato
            # Validar licença em thread separada para não travar a GUI
            validation_thread = threading.Thread(
                target=self._validate_and_start_backend, daemon=True
            )
            validation_thread.start()

        except Exception as e:
            self.validation_in_progress = False
            self._add_log_message(f"Failed to start validation: {e}", "ERROR")
            self.btn_start_backend.configure(state="normal", text="Start")

    def _validate_and_start_backend(self):
        """Validar licença e iniciar backend em thread separada"""
        try:
            # SEGURANÇA: Verificar se já existe processo EXTERNO do backend antes de validar
            # NOVA ARQUITETURA: Backend roda em thread dentro do Panel SSM
            # Apenas processos EXTERNOS usando porta 3000 são considerados
            backend_processes_before = self._find_backend_processes()
            if backend_processes_before:
                # _find_backend_processes já filtra apenas processos externos usando porta 3000
                # Se retornou processos, são processos externos que não deveriam existir
                error_msg = "ERROR: External backend process is already running before validation (port 3000 in use)"
                self.after(0, lambda: self._add_log_message(error_msg, "ERROR"))
                self.after(
                    0,
                    lambda: self._handle_validation_error(
                        "External backend is already running"
                    ),
                )
                return

            # Adicionar log de progresso (na thread principal)
            # self.after(0, lambda: self._add_log_message("Conectando ao servidor de licenciamento...", "INFO"))

            # Validar licença (pode demorar)
            is_valid, message, reason = self._validate_equipment_license()

            # SEGURANÇA: Verificar se processo do backend foi iniciado durante validação
            backend_processes_after = self._find_backend_processes()
            if len(backend_processes_after) > len(backend_processes_before):
                # Novo processo detectado - isso não deveria acontecer
                error_msg = "WARNING: Backend process started during validation - this should not happen"
                if self.logger:
                    self.logger.warning(error_msg)
                self.after(0, lambda: self._add_log_message(error_msg, "WARNING"))
                # Continuar com validação, mas logar o problema

            # Atualizar GUI na thread principal
            self.after(
                0, lambda: self._handle_validation_result(is_valid, message, reason)
            )

        except Exception as e:
            # Em caso de erro, atualizar GUI na thread principal
            self.after(0, lambda: self._handle_validation_error(str(e)))

    def _handle_validation_error(self, error_msg: str):
        """Tratar erro na validação"""
        self.validation_in_progress = False
        self._add_log_message(f"Validation error: {error_msg}", "ERROR")
        self.btn_start_backend.configure(
            state="normal", text="Start", fg_color="green"  # Restaurar cor verde
        )

    def _handle_validation_result(
        self, is_valid: bool, message: str, reason: Optional[str]
    ):
        """Tratar resultado da validação"""
        self.validation_in_progress = False

        try:
            if is_valid:
                self._update_license_status_label()
            else:
                self._set_license_status_value("Blocked")
        except Exception:
            pass

        if not is_valid:
            # Licença inválida ou erro - SEMPRE BLOQUEAR
            self._add_log_message(f"✗ {message}", "ERROR")
            if reason:
                self._add_log_message(f"Reason: {reason}", "ERROR")

            # Mostrar alerta visual na barra superior
            alert_text = "⚠️ License invalid/blocked"
            if reason:
                alert_text = f"⚠️ License invalid ({reason})"
            self._set_license_alert(True, alert_text)

            # Bloquear botão Start permanentemente
            self.btn_start_backend.configure(
                state="disabled", text="Blocked", fg_color="gray"
            )

            # Mensagem de erro apropriada baseada no motivo
            import tkinter.messagebox as messagebox

            if reason == "api_key_missing" or reason == "api_key_invalid":
                # API Key faltando ou inválida - não permitir iniciar
                messagebox.showerror(
                    "API Key Not Configured",
                    f"License validation failed:\n\n{message}\n\n"
                    "You cannot start the backend without a valid API Key.\n\n"
                    "To configure the API Key:\n"
                    "1. Fill the 'API Key' field in the main window\n"
                    "2. Click the save button (💾) next to the field\n\n"
                    "Or configure it manually in config.json under 'licensing':\n"
                    '- gestao_api_key: "ssm_<your_key_here>"',
                )
            elif reason == "network_error":
                # Erro de rede - não permitir iniciar
                messagebox.showerror(
                    "Network Error",
                    f"License validation failed:\n\n{message}\n\n"
                    "You cannot start the backend without validating the license.\n\n"
                    "Check:\n"
                    "- If the licensing server is running\n"
                    "- If your internet connection is active\n"
                    "- If the API Key is configured correctly",
                )
            else:
                # Licença inválida - não permitir iniciar
                messagebox.showerror(
                    "Invalid License",
                    f"Device is not authorized:\n\n{message}\n\n"
                    f"Reason: {reason}\n\n"
                    "Register the device in the web panel before starting.\n\n"
                    "The backend cannot be started without a valid license.",
                )
            return

        # Licença válida - continuar com inicialização
        # Só limpar alerta quando validar com sucesso
        self._set_license_alert(False)

        # SEGURANÇA: Verificação completa antes de iniciar backend
        # 1. Verificar se porta 3000 está aberta (mais confiável)
        if self._is_backend_running():
            error_msg = (
                "⚠️ Backend já está rodando (porta 3000 ativa). Processo não iniciado."
            )
            self._add_log_message(error_msg, "WARNING")
            self.btn_start_backend.configure(state="normal", text="Start")
            self.validation_in_progress = False
            return

        # 2. Verificar processos em execução (incluindo processos filhos)
        backend_processes_check = self._find_backend_processes()
        if backend_processes_check:
            # Verificar se algum processo está usando a porta 3000 ou é um processo backend
            processes_detected = []
            for proc in backend_processes_check:
                try:
                    is_backend = False
                    if HAS_PSUTIL and isinstance(proc, psutil.Process):
                        # Verificar se processo está usando porta 3000 (mais confiável)
                        try:
                            for conn in proc.connections():
                                if hasattr(conn, "laddr") and conn.laddr.port == 3000:
                                    is_backend = True
                                    break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                        # Verificar por nome também
                        if not is_backend:
                            proc_name = proc.name()
                            if proc_name:
                                proc_name_lower = proc_name.lower()
                                if (
                                    "ssm backend.exe" in proc_name_lower
                                    or "ssm_backend.exe" in proc_name_lower
                                ):
                                    is_backend = True
                                elif "python" in proc_name_lower:
                                    # Verificar linha de comando
                                    try:
                                        cmdline = proc.cmdline()
                                        cmdline_str = (
                                            " ".join(cmdline) if cmdline else ""
                                        )
                                        if (
                                            "main.py" in cmdline_str
                                            or "ssm_backend" in cmdline_str
                                        ):
                                            is_backend = True
                                    except:
                                        pass

                    if is_backend:
                        processes_detected.append(proc)
                except Exception:
                    pass

            if processes_detected:
                error_msg = f"⚠️ Backend já está rodando ({len(processes_detected)} processo(s) detectado(s)). Processo não iniciado."
                self._add_log_message(error_msg, "WARNING")
                self.btn_start_backend.configure(state="normal", text="Start")
                self.validation_in_progress = False
                return

        # NOVA ARQUITETURA: Verificar thread ao invés de processo
        if self.backend_thread and self.backend_thread.is_alive():
            # Thread ainda está rodando
            error_msg = "⚠️ Backend já está rodando (thread interna detectada)."
            self._add_log_message(error_msg, "WARNING")
            self.btn_start_backend.configure(state="normal", text="Start")
            self.validation_in_progress = False
            return

        # Código antigo (remover depois):
        if False:  # Desabilitar código antigo
            if hasattr(self, "backend_process") and self.backend_process is not None:
                try:
                    # Verificar se processo ainda está rodando
                    if self.backend_process.poll() is None:
                        # Processo ainda está rodando
                        error_msg = (
                            "⚠️ Backend já está rodando (processo interno detectado)."
                        )
                        self._add_log_message(error_msg, "WARNING")
                        self.btn_start_backend.configure(state="normal", text="Start")
                        self.validation_in_progress = False
                        return
                except Exception:
                    pass

        self._add_log_message("✓ Device authorized. Starting backend...", "SUCCESS")
        # Atualizar botão para "Starting..." com cor laranja para feedback visual
        self.btn_start_backend.configure(
            state="disabled",
            text="Starting...",
            fg_color="#FFA500",  # laranja
        )
        self.update()  # Forçar atualização imediata da GUI

        # Mostrar notificação "Starting"
        if self.system_tray_manager:
            self.system_tray_manager.show_notification(
                "SSM Backend", "Starting...", duration=2
            )

        # NOVA ARQUITETURA: Iniciar backend Flask em thread (não subprocess)
        self._start_backend_flask_thread()

    def _start_backend_flask_thread(self):
        """Iniciar backend Flask em thread separada (nova arquitetura integrada)"""
        # SEGURANÇA CRÍTICA: Lock para garantir que apenas UMA thread inicie o backend
        with self._backend_start_lock:
            # Verificação FINAL antes de iniciar (dentro do lock)
            if self._is_backend_running():
                error_msg = "⚠️ Backend já está rodando (porta 3000 ativa). Processo não iniciado."
                self._add_log_message(error_msg, "WARNING")
                self.btn_start_backend.configure(state="normal", text="Start")
                self.validation_in_progress = False
                return

            # Verificar se thread já está rodando
            if self.backend_thread and self.backend_thread.is_alive():
                error_msg = "⚠️ Backend já está rodando (thread detectada). Processo não iniciado."
                self._add_log_message(error_msg, "WARNING")
                self.btn_start_backend.configure(state="normal", text="Start")
                self.validation_in_progress = False
                return

            # Função para iniciar Flask em thread
            def start_flask_backend():
                """Iniciar backend Flask em thread separada"""
                try:
                    # Log de início da thread
                    self.after(
                        0,
                        lambda: self._add_log_message(
                            "Starting Flask backend thread...", "INFO"
                        ),
                    )
                    
                    # Importar módulos necessários
                    import sys
                    import os
                    import logging
                    from io import StringIO

                    # Adicionar ROOT_DIR ao path se necessário
                    if self.ROOT_DIR not in [Path(p) for p in sys.path]:
                        sys.path.insert(0, str(self.ROOT_DIR))

                    # Importar main.py (mas não executar main())
                    try:
                        import main
                    except ImportError as import_error:
                        error_msg = f"Failed to import main module: {import_error}"
                        if self.logger:
                            self.logger.error(error_msg)
                        self.after(0, lambda: self._add_log_message(f"✗ {error_msg}", "ERROR"))
                        self.after(
                            0,
                            lambda: self.btn_start_backend.configure(
                                state="normal", text="Start"
                            ),
                        )
                        self.after(0, lambda: setattr(self, "validation_in_progress", False))
                        self.after(0, lambda: setattr(self, "backend_thread", None))
                        return

                    # Inicializar componentes (permitir chamada do GUI)
                    self.after(0, lambda: self._add_log_message("Initializing backend components...", "INFO"))
                    try:
                        # Chamar init_components e aguardar conclusão
                        main.init_components(allow_gui_call=True)
                        
                        # Log imediatamente após init_components retornar
                        # IMPORTANTE: Usar variável de captura explícita para evitar problema de closure em lambda
                        success_msg = "✓ Components initialized successfully"
                        self.after(0, lambda msg=success_msg: self._add_log_message(msg, "SUCCESS"))
                        
                    except Exception as e:
                        error_msg = f"✗ Failed to initialize components: {e}"
                        import traceback
                        error_details = traceback.format_exc()
                        if self.logger:
                            self.logger.error(f"{error_msg}\n{error_details}")
                        self.after(0, lambda: self._add_log_message(error_msg, "ERROR"))
                        self.after(
                            0,
                            lambda: self.btn_start_backend.configure(
                                state="normal", text="Start"
                            ),
                        )
                        self.after(
                            0, lambda: setattr(self, "validation_in_progress", False)
                        )
                        return

                    # Log após try/except para debug
                    self.after(0, lambda: self._add_log_message("Checking Flask app availability...", "INFO"))
                    
                    # Verificar se main.app existe antes de continuar
                    if not hasattr(main, 'app') or main.app is None:
                        error_msg = "✗ Error: main.app is not available. Backend was not initialized correctly."
                        if self.logger:
                            self.logger.error(error_msg)
                        self.after(0, lambda: self._add_log_message(error_msg, "ERROR"))
                        self.after(
                            0,
                            lambda: self.btn_start_backend.configure(
                                state="normal", text="Start"
                            ),
                        )
                        self.after(0, lambda: setattr(self, "validation_in_progress", False))
                        self.after(0, lambda: setattr(self, "backend_thread", None))
                        return
                    
                    # Obter configurações da API
                    if not hasattr(main, 'config') or main.config is None:
                        error_msg = "✗ Erro: main.config não está disponível."
                        if self.logger:
                            self.logger.error(error_msg)
                        self.after(0, lambda: self._add_log_message(error_msg, "ERROR"))
                        self.after(
                            0,
                            lambda: self.btn_start_backend.configure(
                                state="normal", text="Start"
                            ),
                        )
                        self.after(0, lambda: setattr(self, "validation_in_progress", False))
                        self.after(0, lambda: setattr(self, "backend_thread", None))
                        return
                    
                    api_config = main.config.get("api", {})
                    host = api_config.get("host", "127.0.0.1")
                    port = api_config.get("port", 3000)
                    debug = api_config.get("debug", False)

                    # Log de início
                    self.after(
                        0,
                        lambda: self._add_log_message(
                            f"Configuring server on port {port}...", "INFO"
                        ),
                    )
                    if main.logger:
                        main.logger.info(
                            f"API server starting on port {port} (integrated mode)"
                        )

                    # Agendar sincronizações iniciais
                    self.after(0, lambda: self._add_log_message("Scheduling initial syncs...", "INFO"))
                    try:
                        main.schedule_initial_syncs()
                        self.after(0, lambda: self._add_log_message("✓ Initial syncs scheduled", "SUCCESS"))
                    except Exception as e:
                        error_msg = f"⚠ Failed to schedule syncs: {e}"
                        if main.logger:
                            main.logger.warning(
                                f"Failed to schedule initial syncs: {e}"
                            )
                        self.after(0, lambda: self._add_log_message(error_msg, "WARNING"))

                    # Silenciar werkzeug
                    log = logging.getLogger("werkzeug")
                    log.setLevel(logging.ERROR)
                    log.disabled = True

                    # Redirecionar stdout para GUI (usar TextRedirector existente)
                    # FlaskOutputFilter será aplicado automaticamente pelo TextRedirector

                    # Iniciar servidor Flask
                    # Usar werkzeug.serving.make_server para ter controle de shutdown
                    from werkzeug.serving import make_server  # type: ignore[reportMissingImports]

                    # Criar servidor Flask
                    self.after(0, lambda: self._add_log_message(f"Creating Flask server on port {port}...", "INFO"))
                    try:
                        server = make_server(host, port, main.app, threaded=True)
                    except Exception as server_error:
                        error_msg = f"✗ Failed to create Flask server: {server_error}"
                        import traceback
                        error_details = traceback.format_exc()
                        if self.logger:
                            self.logger.error(f"{error_msg}\n{error_details}")
                        self.after(0, lambda: self._add_log_message(error_msg, "ERROR"))
                        self.after(
                            0,
                            lambda: self.btn_start_backend.configure(
                                state="normal", text="Start"
                            ),
                        )
                        self.after(0, lambda: setattr(self, "validation_in_progress", False))
                        self.after(0, lambda: setattr(self, "backend_thread", None))
                        return

                    # IMPORTANTE: Armazenar referência ANTES de iniciar serve_forever
                    # Isso garante que está disponível para shutdown mesmo se serve_forever bloquear
                    self.flask_server = server

                    # Também notificar GUI (thread-safe via after)
                    self.after(
                        0,
                        lambda: self._add_log_message(
                            f"Backend Flask iniciado na porta {port}", "SUCCESS"
                        ),
                    )
                    self.after(0, lambda: self._update_backend_status())

                    # Log de sucesso na thread
                    if main.logger:
                        main.logger.info(
                            f"Servidor Flask iniciado na porta {port} (thread: {threading.current_thread().name})"
                        )

                    # Armazenar referência ao socket para fechamento forçado se necessário
                    server_socket = None
                    try:
                        if hasattr(server, "socket"):
                            server_socket = server.socket
                        elif hasattr(server, "_sockets") and server._sockets:
                            server_socket = (
                                server._sockets[0] if server._sockets else None
                            )
                    except:
                        pass

                    # Armazenar socket na instância para acesso externo
                    if server_socket:
                        self._flask_server_socket = server_socket
                    else:
                        self._flask_server_socket = None

                    # Iniciar servidor (bloqueia até ser parado)
                    # serve_forever() retorna quando shutdown() é chamado ou socket é fechado
                    try:
                        server.serve_forever()
                    except (OSError, ConnectionError) as socket_error:
                        # Socket foi fechado - isso é esperado quando paramos o servidor
                        if main.logger:
                            main.logger.info(
                                f"Socket fechado (esperado ao parar servidor): {socket_error}"
                            )
                    except Exception as serve_error:
                        # Capturar qualquer outro erro durante serve_forever
                        if main.logger:
                            main.logger.error(
                                f"Erro durante serve_forever: {serve_error}"
                            )
                        raise
                    finally:
                        # Limpar referências quando servidor parar
                        if main.logger:
                            main.logger.info(
                                "Servidor Flask parou (serve_forever retornou)"
                            )
                        self.after(0, lambda: setattr(self, "flask_server", None))
                        self.after(
                            0, lambda: setattr(self, "_flask_server_socket", None)
                        )

                except Exception as e:
                    error_msg = f"Erro ao iniciar backend Flask: {e}"
                    import traceback

                    error_details = traceback.format_exc()
                    if self.logger:
                        self.logger.error(f"{error_msg}\n{error_details}")
                    self.after(0, lambda: self._add_log_message(error_msg, "ERROR"))
                    self.after(
                        0,
                        lambda: self.btn_start_backend.configure(
                            state="normal", text="Start"
                        ),
                    )
                    self.after(
                        0, lambda: setattr(self, "validation_in_progress", False)
                    )
                    self.after(0, lambda: setattr(self, "backend_thread", None))

            # Iniciar thread (NÃO daemon para poder controlar shutdown)
            self.backend_thread = threading.Thread(
                target=start_flask_backend, daemon=False, name="FlaskBackendThread"
            )
            self.backend_thread.start()

            # Aguardar um pouco e verificar se iniciou
            self.after(3000, self._check_backend_started)

    def _stop_backend_flask(self):
        """Parar backend Flask (nova arquitetura integrada)"""
        try:
            # PRIORIDADE CRÍTICA: Fechar socket do Flask IMEDIATAMENTE primeiro
            # Isso força serve_forever() a retornar imediatamente, parando o servidor instantaneamente
            if self.flask_server:
                try:
                    socket_to_close = None
                    if hasattr(self.flask_server, "socket"):
                        socket_to_close = self.flask_server.socket
                    elif hasattr(self.flask_server, "_sockets") and self.flask_server._sockets:
                        socket_to_close = self.flask_server._sockets[0] if self.flask_server._sockets else None
                    elif hasattr(self, "_flask_server_socket") and self._flask_server_socket:
                        socket_to_close = self._flask_server_socket

                    if socket_to_close:
                        socket_to_close.close()
                        if self.logger:
                            self.logger.info("Socket Flask fechado IMEDIATAMENTE - servidor deve parar agora")
                        # Limpar referência imediatamente após fechar socket
                        self.flask_server = None
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Erro ao fechar socket imediatamente: {e}")
            
            # IMPORTANTE: Parar todos os componentes de background ANTES de parar o Flask
            # Isso garante que threads de processamento de logs, sincronizações, etc. sejam paradas
            # Essas threads continuam rodando mesmo após o Flask parar, causando os logs que vemos
            # Executar cleanup em thread separada para NÃO TRAVAR a GUI
            cleanup_complete = threading.Event()
            cleanup_error_occurred = [False]
            cleanup_error_msg = [None]
            self._cleanup_ui_notified = False

            def run_cleanup():
                """Executar cleanup em thread separada para não travar GUI"""
                try:
                    import sys
                    from pathlib import Path

                    # Adicionar ROOT_DIR ao path se necessário
                    if self.ROOT_DIR not in [Path(p) for p in sys.path]:
                        sys.path.insert(0, str(self.ROOT_DIR))

                    import main

                    if hasattr(main, "cleanup_components"):
                        if self.logger:
                            self.logger.info(
                                "Parando componentes de background antes de parar Flask..."
                            )
                        self.after(
                            0,
                            lambda: self._add_log_message(
                                "Parando componentes de background...", "INFO"
                            ),
                        )

                        main.cleanup_components()
                        # NÃO aguardar aqui - componentes param com timeout próprio
                        def _mark_cleanup_ui_and_log():
                            try:
                                self._cleanup_ui_notified = True
                            except Exception:
                                pass
                            self._add_log_message("Componentes de background parados", "SUCCESS")

                        self.after(0, _mark_cleanup_ui_and_log)
                    else:
                        if self.logger:
                            self.logger.warning(
                                "Função cleanup_components não encontrada em main.py"
                            )
                except Exception as cleanup_error:
                    cleanup_error_occurred[0] = True
                    cleanup_error_msg[0] = str(cleanup_error)
                    if self.logger:
                        self.logger.error(f"Erro durante cleanup: {cleanup_error}")
                        import traceback

                        self.logger.error(f"Traceback: {traceback.format_exc()}")
                    self.after(
                        0,
                        lambda: self._add_log_message(
                            f"Erro ao parar componentes: {cleanup_error_msg[0]}",
                            "ERROR",
                        ),
                    )
                finally:
                    cleanup_complete.set()

            # Iniciar cleanup em thread separada (NÃO daemon para garantir execução)
            cleanup_thread = threading.Thread(
                target=run_cleanup, daemon=False, name="CleanupThread"
            )
            cleanup_thread.start()

            # NÃO aguardar cleanup aqui - isso travaria a GUI com "Não está respondendo"
            # O cleanup continuará em background enquanto paramos o Flask
            # Verificar status do cleanup de forma assíncrona usando after()

            cleanup_start_ts = time.time()

            def check_cleanup_status():
                """Verificar status do cleanup sem bloquear GUI"""
                if cleanup_complete.is_set():
                    # Cleanup completou
                    if cleanup_error_occurred[0]:
                        if self.logger:
                            self.logger.warning(
                                f"Cleanup completou mas com erro: {cleanup_error_msg[0]}"
                            )
                    else:
                        if self.logger:
                            self.logger.info("Cleanup completado com sucesso")

                    # Finalizar UI somente quando:
                    # - cleanup terminou
                    # - a porta 3000 já fechou
                    # - e a GUI já exibiu "Componentes de background parados" (evitar liberar Start antes do log)
                    if (
                        not self._is_backend_running()
                        and getattr(self, "_cleanup_ui_notified", False)
                    ):
                        def finalize_stop_ui():
                            try:
                                self.backend_stopping = False
                                self._update_backend_status()
                            except Exception:
                                pass

                        self.after(0, finalize_stop_ui)
                        return

                    # Safety: se por algum motivo a porta não fecha ou a UI não marca cleanup,
                    # não ficar preso indefinidamente em "Stopping..."
                    try:
                        if time.time() - cleanup_start_ts > 25:
                            def _force_finalize_stop_ui():
                                try:
                                    self.backend_stopping = False
                                    self._update_backend_status()
                                except Exception:
                                    pass

                            self.after(0, _force_finalize_stop_ui)
                            try:
                                self.after(
                                    0,
                                    lambda: self._add_log_message(
                                        "AVISO: Stop demorou mais que o esperado; UI liberada, mas algum componente pode ainda estar parando.",
                                        "WARNING",
                                    ),
                                )
                            except Exception:
                                pass
                            return
                    except Exception:
                        pass

                    # Ainda aguardando porta fechar ou UI sinalizar cleanup; continuar verificando
                    self.after(500, check_cleanup_status)
                    return
                else:
                    # Cleanup ainda em execução - agendar verificação novamente
                    self.after(500, check_cleanup_status)  # Verificar a cada 500ms

            # Iniciar verificação assíncrona (não bloqueia)
            self.after(500, check_cleanup_status)

            # NÃO aguardar cleanup aqui - isso travaria a GUI
            # O cleanup continuará em background enquanto paramos o Flask

            # Parar servidor Flask se estiver rodando
            # O shutdown() precisa ser chamado de uma thread diferente da que está rodando o servidor
            flask_server_ref = None
            if self.flask_server:
                flask_server_ref = self.flask_server
                try:
                    # Chamar shutdown em thread separada (NÃO daemon para garantir execução)
                    shutdown_complete = threading.Event()
                    shutdown_error = [None]

                    def shutdown_server():
                        try:
                            if flask_server_ref:
                                # PRIORIDADE: Fechar socket PRIMEIRO (mais rápido e direto)
                                # Isso força serve_forever() a retornar imediatamente
                                socket_closed = False
                                try:
                                    # Tentar fechar socket do servidor
                                    socket_to_close = None
                                    if hasattr(flask_server_ref, "socket"):
                                        socket_to_close = flask_server_ref.socket
                                    elif (
                                        hasattr(flask_server_ref, "_sockets")
                                        and flask_server_ref._sockets
                                    ):
                                        socket_to_close = (
                                            flask_server_ref._sockets[0]
                                            if flask_server_ref._sockets
                                            else None
                                        )
                                    elif (
                                        hasattr(self, "_flask_server_socket")
                                        and self._flask_server_socket
                                    ):
                                        socket_to_close = self._flask_server_socket

                                    if socket_to_close:
                                        socket_to_close.close()
                                        socket_closed = True
                                        if self.logger:
                                            self.logger.info(
                                                "Socket do servidor Flask fechado diretamente - serve_forever deve retornar imediatamente"
                                            )
                                except Exception as socket_err:
                                    if self.logger:
                                        self.logger.warning(
                                            f"Erro ao fechar socket: {socket_err}"
                                        )

                                # Método 1: Tentar shutdown normal (backup caso socket não funcione)
                                if not socket_closed:
                                    try:
                                        flask_server_ref.shutdown()
                                        if self.logger:
                                            self.logger.info(
                                                "Comando shutdown() enviado ao servidor Flask"
                                            )
                                    except Exception as shutdown_err:
                                        if self.logger:
                                            self.logger.warning(
                                                f"Erro no shutdown normal: {shutdown_err}"
                                            )

                                # Método 2: Tentar fechar servidor HTTP diretamente (backup adicional)
                                try:
                                    if hasattr(
                                        flask_server_ref,
                                        "_BaseServer__shutdown_request",
                                    ):
                                        flask_server_ref._BaseServer__shutdown_request = (
                                            True
                                        )
                                    if hasattr(flask_server_ref, "server_close"):
                                        flask_server_ref.server_close()
                                        if self.logger:
                                            self.logger.info(
                                                "Servidor Flask fechado via server_close()"
                                            )
                                except Exception as close_err:
                                    if self.logger:
                                        self.logger.warning(
                                            f"Erro ao fechar servidor: {close_err}"
                                        )
                        except Exception as e:
                            shutdown_error[0] = e
                            if self.logger:
                                self.logger.warning(
                                    f"Erro ao chamar shutdown do servidor Flask: {e}"
                                )
                        finally:
                            shutdown_complete.set()

                    shutdown_thread = threading.Thread(
                        target=shutdown_server, daemon=False, name="FlaskShutdownThread"
                    )
                    shutdown_thread.start()

                    # NÃO aguardar shutdown aqui - isso travaria a GUI
                    # Verificar status do shutdown de forma assíncrona
                    def check_shutdown_status():
                        """Verificar status do shutdown sem bloquear GUI"""
                        if shutdown_complete.is_set():
                            if shutdown_error[0]:
                                if self.logger:
                                    self.logger.warning(
                                        f"Shutdown executado mas com erro: {shutdown_error[0]}"
                                    )
                            else:
                                if self.logger:
                                    self.logger.info(
                                        "Servidor Flask recebeu comando shutdown com sucesso"
                                    )
                        else:
                            # Shutdown ainda em execução - agendar verificação novamente
                            self.after(
                                500, check_shutdown_status
                            )  # Verificar a cada 500ms

                    # Iniciar verificação assíncrona (não bloqueia)
                    self.after(500, check_shutdown_status)

                    # Limpar referência imediatamente (não aguardar)
                    self.flask_server = None
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Erro ao iniciar thread de shutdown: {e}")
                    # Tentar limpar referência mesmo em caso de erro
                    self.flask_server = None

            # NÃO aguardar thread do backend aqui - isso travaria a GUI
            # Verificar status da thread de forma assíncrona
            if self.backend_thread and self.backend_thread.is_alive():
                if self.logger:
                    self.logger.info(
                        "Thread do backend ainda ativa - será verificada assincronamente..."
                    )

                def check_backend_thread_status():
                    """Verificar se thread do backend terminou sem bloquear GUI"""
                    if self.backend_thread and self.backend_thread.is_alive():
                        # Thread ainda ativa - agendar verificação novamente
                        self.after(
                            1000, check_backend_thread_status
                        )  # Verificar a cada 1s
                    else:
                        # Thread terminou
                        if self.logger:
                            self.logger.info("Thread do backend terminou")
                        # Limpar referências
                        self.backend_thread = None
                        self.flask_server = None

                # Iniciar verificação assíncrona (não bloqueia)
                self.after(1000, check_backend_thread_status)

                # Verificar uma vez rapidamente (timeout muito curto)
                if self.backend_thread.is_alive():
                    # Thread não terminou - tentar métodos mais agressivos
                    if self.logger:
                        self.logger.warning(
                            "Thread do backend não terminou em 10s após shutdown - tentando métodos mais agressivos"
                        )

                    # Verificar se porta ainda está aberta
                    port_still_active = self._is_backend_running()
                    if port_still_active:
                        if self.logger:
                            self.logger.warning(
                                "Porta 3000 ainda está ativa - tentando forçar parada..."
                            )

                        # Tentar shutdown novamente se ainda temos referência ao servidor
                        if flask_server_ref:
                            try:
                                if self.logger:
                                    self.logger.info(
                                        "Tentando shutdown forçado novamente..."
                                    )
                                flask_server_ref.shutdown()
                                time.sleep(2)
                            except Exception as e:
                                if self.logger:
                                    self.logger.warning(
                                        f"Erro ao tentar shutdown forçado: {e}"
                                    )

                        # Aguardar mais 5 segundos
                        self.backend_thread.join(timeout=5)

                        # Se ainda não terminou, tentar método final: marcar thread como daemon
                        if self.backend_thread.is_alive():
                            if self.logger:
                                self.logger.error(
                                    "ERRO CRÍTICO: Thread do backend não terminou após múltiplas tentativas de shutdown"
                                )
                                self.logger.error(
                                    "Tentando método final: marcar thread como daemon para permitir encerramento do processo"
                                )

                            # Último recurso: marcar thread como daemon
                            # Isso permite que o processo principal termine mesmo se a thread não parar
                            try:
                                self.backend_thread.daemon = True
                                if self.logger:
                                    self.logger.warning(
                                        "Thread marcada como daemon - processo pode terminar mesmo com thread ativa"
                                    )
                            except Exception as daemon_err:
                                if self.logger:
                                    self.logger.warning(
                                        f"Erro ao marcar thread como daemon: {daemon_err}"
                                    )

                            # Limpar referências mesmo assim para evitar estado inconsistente
                            self.backend_thread = None
                            self.flask_server = None
                            self.backend_running = False

                            # Adicionar log na GUI
                            self.after(
                                0,
                                lambda: self._add_log_message(
                                    "AVISO: Backend não parou completamente. Thread marcada como daemon. Considere reiniciar o aplicativo.",
                                    "WARNING",
                                ),
                            )

                            # Atualizar status na GUI
                            self.after(0, self._update_backend_status)
                            return  # Retornar cedo pois não conseguimos parar completamente
                else:
                    if self.logger:
                        self.logger.info("Thread do backend terminou com sucesso")

            # Limpar referências
            self.backend_thread = None
            self.backend_running = False

            # Verificar se porta está fechada
            if self._is_backend_running():
                if self.logger:
                    self.logger.warning(
                        "Aviso: Porta 3000 ainda está ativa após parar backend"
                    )
            else:
                if self.logger:
                    self.logger.info(
                        "Backend Flask parado completamente (porta 3000 fechada)"
                    )

        except Exception as e:
            import traceback

            if self.logger:
                self.logger.error(f"Erro ao parar backend Flask: {e}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
            # Limpar referências mesmo em caso de erro
            self.backend_thread = None
            self.flask_server = None
            self.backend_running = False

        # Código antigo (remover depois):
        if False:  # Desabilitar código antigo
            # Quando executável, usar SSM Backend.exe (modo API, sem --gui)
            # Tentar primeiro com o novo nome, depois com o antigo para compatibilidade
            backend_exe = self.EXE_DIR / "SSM Backend.exe"
            if not backend_exe.exists():
                backend_exe = self.EXE_DIR / "ssm_backend.exe"
            if backend_exe.exists():
                # Capturar stdout e stderr do processo do backend
                # Combinar CREATE_NEW_PROCESS_GROUP com CREATE_NO_WINDOW
                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = (
                        subprocess.CREATE_NEW_PROCESS_GROUP
                        | subprocess.CREATE_NO_WINDOW
                    )

                # SEGURANÇA: Verificação final antes de iniciar (última chance)
                # 1. Verificar porta 3000 (mais confiável - se porta está aberta, backend está rodando)
                if self._is_backend_running():
                    error_msg = "⚠️ Backend já está rodando (porta 3000 ativa). Processo não iniciado."
                    self._add_log_message(error_msg, "WARNING")
                    self.btn_start_backend.configure(state="normal", text="Start")
                    self.validation_in_progress = False
                    return

                # 2. Verificar processos (incluindo processos filhos)
                final_check = self._find_backend_processes()
                if final_check:
                    # Verificar se algum processo está usando a porta 3000 ou é um processo backend
                    processes_detected = []
                    for proc in final_check:
                        try:
                            is_backend = False
                            if HAS_PSUTIL and isinstance(proc, psutil.Process):
                                # Verificar se processo está usando porta 3000 (mais confiável)
                                try:
                                    for conn in proc.connections():
                                        if (
                                            hasattr(conn, "laddr")
                                            and conn.laddr.port == 3000
                                        ):
                                            is_backend = True
                                            break
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass

                                # Verificar por nome também
                                if not is_backend:
                                    proc_name = proc.name()
                                    if proc_name:
                                        proc_name_lower = proc_name.lower()
                                        if (
                                            "ssm backend.exe" in proc_name_lower
                                            or "ssm_backend.exe" in proc_name_lower
                                        ):
                                            is_backend = True
                                        elif "python" in proc_name_lower:
                                            # Verificar linha de comando
                                            try:
                                                cmdline = proc.cmdline()
                                                cmdline_str = (
                                                    " ".join(cmdline) if cmdline else ""
                                                )
                                                if (
                                                    "main.py" in cmdline_str
                                                    or "ssm_backend" in cmdline_str
                                                ):
                                                    is_backend = True
                                            except:
                                                pass

                            if is_backend:
                                processes_detected.append(proc)
                        except Exception:
                            pass

                    if processes_detected:
                        error_msg = f"⚠️ Backend já está rodando ({len(processes_detected)} processo(s) detectado(s)). Processo não iniciado."
                        self._add_log_message(error_msg, "WARNING")
                        self.btn_start_backend.configure(state="normal", text="Start")
                        self.validation_in_progress = False
                        return

                # 3. SEGURANÇA: Verificar se mutex do single instance já existe (sem adquirir)
                # Se existir, significa que backend já está rodando
                try:
                    if sys.platform == "win32":
                        try:
                            import win32event
                            import win32api

                            # Tentar abrir mutex existente (não criar)
                            mutex_handle = win32event.OpenMutex(
                                win32event.SYNCHRONIZE,
                                False,
                                f"Global\\ssm_backend_api",
                            )
                            if mutex_handle:
                                # Mutex existe - backend já está rodando
                                win32api.CloseHandle(mutex_handle)
                                error_msg = (
                                    "⚠️ Backend já está rodando. Processo não iniciado."
                                )
                                self._add_log_message(error_msg, "WARNING")
                                self.btn_start_backend.configure(
                                    state="normal", text="Start"
                                )
                                self.validation_in_progress = False
                                return
                        except Exception:
                            # Se falhar ao abrir mutex, verificar arquivo de lock como fallback
                            lock_file = Path("data") / "temp" / "ssm_backend_api.lock"
                            if lock_file.exists():
                                try:
                                    pid = int(lock_file.read_text().strip())
                                    # Verificar se processo ainda está rodando
                                    try:
                                        import psutil

                                        if psutil.pid_exists(pid):
                                            error_msg = "⚠️ Backend já está rodando (detectado via lock file). Processo não iniciado."
                                            self._add_log_message(error_msg, "WARNING")
                                            self.btn_start_backend.configure(
                                                state="normal", text="Start"
                                            )
                                            self.validation_in_progress = False
                                            return
                                    except ImportError:
                                        # psutil não disponível, assumir que está rodando se lock existe
                                        error_msg = "⚠️ Backend pode estar rodando (lock file encontrado). Processo não iniciado."
                                        self._add_log_message(error_msg, "WARNING")
                                        self.btn_start_backend.configure(
                                            state="normal", text="Start"
                                        )
                                        self.validation_in_progress = False
                                        return
                                except (ValueError, OSError):
                                    # Lock inválido, continuar
                                    pass
                    else:
                        # Linux/Unix: verificar arquivo de lock
                        lock_file = Path("data") / "temp" / "ssm_backend_api.lock"
                        if lock_file.exists():
                            try:
                                pid = int(lock_file.read_text().strip())
                                import os

                                try:
                                    os.kill(pid, 0)  # Verificar se processo existe
                                    error_msg = "⚠️ Backend já está rodando (detectado via lock file). Processo não iniciado."
                                    self._add_log_message(error_msg, "WARNING")
                                    self.btn_start_backend.configure(
                                        state="normal", text="Start"
                                    )
                                    self.validation_in_progress = False
                                    return
                                except OSError:
                                    # Processo não existe, lock órfão - continuar
                                    pass
                            except (ValueError, OSError):
                                # Lock inválido, continuar
                                pass
                except Exception as e:
                    # Se falhar verificação de mutex, logar mas continuar (melhor que bloquear)
                    if self.logger:
                        self.logger.warning(
                            f"Erro ao verificar mutex de single instance: {e}"
                        )

                # SEGURANÇA CRÍTICA: Lock para garantir que apenas UMA thread crie o processo
                # Verificar novamente dentro do lock (última verificação antes de criar)
                with self._process_creation_lock:
                    # Verificação FINAL antes de criar processo (dentro do lock)
                    if self._is_backend_running():
                        error_msg = "⚠️ Backend já está rodando (porta 3000 ativa). Processo não iniciado."
                        self._add_log_message(error_msg, "WARNING")
                        self.btn_start_backend.configure(state="normal", text="Start")
                        self.validation_in_progress = False
                        return

                    # Verificar se já existe processo interno
                    if (
                        hasattr(self, "backend_process")
                        and self.backend_process is not None
                    ):
                        try:
                            if self.backend_process.poll() is None:
                                error_msg = "⚠️ Backend já está rodando (processo interno detectado). Processo não iniciado."
                                self._add_log_message(error_msg, "WARNING")
                                self.btn_start_backend.configure(
                                    state="normal", text="Start"
                                )
                                self.validation_in_progress = False
                                return
                        except Exception:
                            pass

                    # Verificar processos externos uma última vez
                    final_backend_check = self._find_backend_processes()
                    if final_backend_check:
                        processes_detected = []
                        for proc in final_backend_check:
                            try:
                                is_backend = False
                                if HAS_PSUTIL and isinstance(proc, psutil.Process):
                                    try:
                                        for conn in proc.connections():
                                            if (
                                                hasattr(conn, "laddr")
                                                and conn.laddr.port == 3000
                                            ):
                                                is_backend = True
                                                break
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        pass

                                    if not is_backend:
                                        proc_name = proc.name()
                                        if proc_name:
                                            proc_name_lower = proc_name.lower()
                                            if (
                                                "ssm backend.exe" in proc_name_lower
                                                or "ssm_backend.exe" in proc_name_lower
                                            ):
                                                is_backend = True

                                if is_backend:
                                    processes_detected.append(proc)
                            except Exception:
                                pass

                        if processes_detected:
                            error_msg = f"⚠️ Backend já está rodando ({len(processes_detected)} processo(s) detectado(s)). Processo não iniciado."
                            self._add_log_message(error_msg, "WARNING")
                            self.btn_start_backend.configure(
                                state="normal", text="Start"
                            )
                            self.validation_in_progress = False
                            return

                    # TODAS as verificações passaram - criar processo
                    self.backend_process = subprocess.Popen(
                        [str(backend_exe)],
                        cwd=str(self.EXE_DIR),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1,
                        creationflags=creation_flags,
                    )

                # Iniciar thread para ler saída do processo
                self._start_backend_output_reader()

                # SEGURANÇA: Aguardar porta 3000 abrir e verificar se não há múltiplos processos (em thread separada)
                threading.Thread(
                    target=self._wait_for_backend_port_and_verify, daemon=True
                ).start()
            else:
                self.backend_status_text.configure(text="Backend exe not found")
                self._add_log_message("Error: backend executable not found", "ERROR")
                self.btn_start_backend.configure(state="normal", text="Start")
                return
        else:
            # Quando script, usar main.py (modo API, sem --gui)
            main_py = self.ROOT_DIR / "main.py"
            if main_py.exists():
                # Capturar stdout e stderr do processo do backend
                # Combinar CREATE_NEW_PROCESS_GROUP com CREATE_NO_WINDOW
                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = (
                        subprocess.CREATE_NEW_PROCESS_GROUP
                        | subprocess.CREATE_NO_WINDOW
                    )

                # SEGURANÇA: Verificação final antes de iniciar (última chance)
                # 1. Verificar porta 3000 (mais confiável - se porta está aberta, backend está rodando)
                if self._is_backend_running():
                    error_msg = "⚠️ Backend já está rodando (porta 3000 ativa). Processo não iniciado."
                    self._add_log_message(error_msg, "WARNING")
                    self.btn_start_backend.configure(state="normal", text="Start")
                    self.validation_in_progress = False
                    return

                # 2. Verificar processos (incluindo processos filhos)
                final_check = self._find_backend_processes()
                if final_check:
                    # Verificar se algum processo está usando a porta 3000 ou é um processo backend
                    processes_detected = []
                    for proc in final_check:
                        try:
                            is_backend = False
                            if HAS_PSUTIL and isinstance(proc, psutil.Process):
                                # Verificar se processo está usando porta 3000 (mais confiável)
                                try:
                                    for conn in proc.connections():
                                        if (
                                            hasattr(conn, "laddr")
                                            and conn.laddr.port == 3000
                                        ):
                                            is_backend = True
                                            break
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass

                                # Verificar por nome também
                                if not is_backend:
                                    proc_name = proc.name()
                                    if proc_name:
                                        proc_name_lower = proc_name.lower()
                                        if (
                                            "ssm backend.exe" in proc_name_lower
                                            or "ssm_backend.exe" in proc_name_lower
                                        ):
                                            is_backend = True
                                        elif "python" in proc_name_lower:
                                            # Verificar linha de comando
                                            try:
                                                cmdline = proc.cmdline()
                                                cmdline_str = (
                                                    " ".join(cmdline) if cmdline else ""
                                                )
                                                if (
                                                    "main.py" in cmdline_str
                                                    or "ssm_backend" in cmdline_str
                                                ):
                                                    is_backend = True
                                            except:
                                                pass

                            if is_backend:
                                processes_detected.append(proc)
                        except Exception:
                            pass

                    if processes_detected:
                        error_msg = f"⚠️ Backend já está rodando ({len(processes_detected)} processo(s) detectado(s)). Processo não iniciado."
                        self._add_log_message(error_msg, "WARNING")
                        self.btn_start_backend.configure(state="normal", text="Start")
                        self.validation_in_progress = False
                        return

                # 3. SEGURANÇA: Verificar se mutex do single instance já existe (sem adquirir)
                # Se existir, significa que backend já está rodando
                try:
                    if sys.platform == "win32":
                        try:
                            import win32event
                            import win32api

                            # Tentar abrir mutex existente (não criar)
                            mutex_handle = win32event.OpenMutex(
                                win32event.SYNCHRONIZE,
                                False,
                                f"Global\\ssm_backend_api",
                            )
                            if mutex_handle:
                                # Mutex existe - backend já está rodando
                                win32api.CloseHandle(mutex_handle)
                                error_msg = (
                                    "⚠️ Backend já está rodando. Processo não iniciado."
                                )
                                self._add_log_message(error_msg, "WARNING")
                                self.btn_start_backend.configure(
                                    state="normal", text="Start"
                                )
                                self.validation_in_progress = False
                                return
                        except Exception:
                            # Se falhar ao abrir mutex, verificar arquivo de lock como fallback
                            lock_file = Path("data") / "temp" / "ssm_backend_api.lock"
                            if lock_file.exists():
                                try:
                                    pid = int(lock_file.read_text().strip())
                                    # Verificar se processo ainda está rodando
                                    try:
                                        import psutil

                                        if psutil.pid_exists(pid):
                                            error_msg = "⚠️ Backend já está rodando (detectado via lock file). Processo não iniciado."
                                            self._add_log_message(error_msg, "WARNING")
                                            self.btn_start_backend.configure(
                                                state="normal", text="Start"
                                            )
                                            self.validation_in_progress = False
                                            return
                                    except ImportError:
                                        # psutil não disponível, assumir que está rodando se lock existe
                                        error_msg = "⚠️ Backend pode estar rodando (lock file encontrado). Processo não iniciado."
                                        self._add_log_message(error_msg, "WARNING")
                                        self.btn_start_backend.configure(
                                            state="normal", text="Start"
                                        )
                                        self.validation_in_progress = False
                                        return
                                except (ValueError, OSError):
                                    # Lock inválido, continuar
                                    pass
                    else:
                        # Linux/Unix: verificar arquivo de lock
                        lock_file = Path("data") / "temp" / "ssm_backend_api.lock"
                        if lock_file.exists():
                            try:
                                pid = int(lock_file.read_text().strip())
                                import os

                                try:
                                    os.kill(pid, 0)  # Verificar se processo existe
                                    error_msg = "⚠️ Backend já está rodando (detectado via lock file). Processo não iniciado."
                                    self._add_log_message(error_msg, "WARNING")
                                    self.btn_start_backend.configure(
                                        state="normal", text="Start"
                                    )
                                    self.validation_in_progress = False
                                    return
                                except OSError:
                                    # Processo não existe, lock órfão - continuar
                                    pass
                            except (ValueError, OSError):
                                # Lock inválido, continuar
                                pass
                except Exception as e:
                    # Se falhar verificação de mutex, logar mas continuar (melhor que bloquear)
                    if self.logger:
                        self.logger.warning(
                            f"Erro ao verificar mutex de single instance: {e}"
                        )

                # SEGURANÇA CRÍTICA: Lock para garantir que apenas UMA thread crie o processo
                # Verificar novamente dentro do lock (última verificação antes de criar)
                with self._process_creation_lock:
                    # Verificação FINAL antes de criar processo (dentro do lock)
                    if self._is_backend_running():
                        error_msg = "⚠️ Backend já está rodando (porta 3000 ativa). Processo não iniciado."
                        self._add_log_message(error_msg, "WARNING")
                        self.btn_start_backend.configure(state="normal", text="Start")
                        self.validation_in_progress = False
                        return

                    # Verificar se já existe processo interno
                    if (
                        hasattr(self, "backend_process")
                        and self.backend_process is not None
                    ):
                        try:
                            if self.backend_process.poll() is None:
                                error_msg = "⚠️ Backend já está rodando (processo interno detectado). Processo não iniciado."
                                self._add_log_message(error_msg, "WARNING")
                                self.btn_start_backend.configure(
                                    state="normal", text="Start"
                                )
                                self.validation_in_progress = False
                                return
                        except Exception:
                            pass

                    # Verificar processos externos uma última vez
                    final_backend_check = self._find_backend_processes()
                    if final_backend_check:
                        processes_detected = []
                        for proc in final_backend_check:
                            try:
                                is_backend = False
                                if HAS_PSUTIL and isinstance(proc, psutil.Process):
                                    try:
                                        for conn in proc.connections():
                                            if (
                                                hasattr(conn, "laddr")
                                                and conn.laddr.port == 3000
                                            ):
                                                is_backend = True
                                                break
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        pass

                                    if not is_backend:
                                        proc_name = proc.name()
                                        if proc_name:
                                            proc_name_lower = proc_name.lower()
                                            if (
                                                "ssm backend.exe" in proc_name_lower
                                                or "ssm_backend.exe" in proc_name_lower
                                            ):
                                                is_backend = True
                                        elif "python" in proc_name_lower:
                                            try:
                                                cmdline = proc.cmdline()
                                                cmdline_str = (
                                                    " ".join(cmdline) if cmdline else ""
                                                )
                                                if (
                                                    "main.py" in cmdline_str
                                                    or "ssm_backend" in cmdline_str
                                                ):
                                                    is_backend = True
                                            except:
                                                pass

                                if is_backend:
                                    processes_detected.append(proc)
                            except Exception:
                                pass

                        if processes_detected:
                            error_msg = f"⚠️ Backend já está rodando ({len(processes_detected)} processo(s) detectado(s)). Processo não iniciado."
                            self._add_log_message(error_msg, "WARNING")
                            self.btn_start_backend.configure(
                                state="normal", text="Start"
                            )
                            self.validation_in_progress = False
                            return

                    # TODAS as verificações passaram - criar processo
                    self.backend_process = subprocess.Popen(
                        [sys.executable, str(main_py)],
                        cwd=str(self.ROOT_DIR),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1,
                        creationflags=creation_flags,
                    )

                # Iniciar thread para ler saída do processo
                self._start_backend_output_reader()

                # SEGURANÇA: Aguardar porta 3000 abrir e verificar se não há múltiplos processos (em thread separada)
                threading.Thread(
                    target=self._wait_for_backend_port_and_verify, daemon=True
                ).start()
            else:
                self.backend_status_text.configure(text="main.py not found")
                self._add_log_message("Error: main.py not found", "ERROR")
                self.btn_start_backend.configure(state="normal", text="Start")
                return

        # Aguardar um pouco e verificar se iniciou
        self.after(3000, self._check_backend_started)

    def _check_backend_started(self):
        """Verificar se o backend iniciou com sucesso"""
        if self._is_backend_running():
            self._update_backend_status()
            self.btn_start_backend.configure(text="Start")
            self._add_log_message(
                "Backend iniciado com sucesso na porta 3000", "SUCCESS"
            )
            self.license_validated = True  # Marcar como validado
            # Invalidar cache quando backend inicia (pode ter novos dados)
            self.cached_next_restart = None
            self.last_api_check_time = None

            # Garantir que as tabs estejam sempre habilitadas
            self._ensure_tabs_enabled()

            # Mostrar notificação "Started"
            if self.system_tray_manager:
                self.system_tray_manager.show_notification(
                    "SSM Backend", "Started", duration=3
                )
                # Atualizar menu do tray imediatamente
                self.after(100, self._update_tray_menu)
        else:
            # Ainda não iniciou, verificar novamente
            # NOVA ARQUITETURA: Verificar thread ao invés de processo
            if self.backend_thread and self.backend_thread.is_alive():
                # Thread ainda rodando, aguardar mais
                self.after(2000, self._check_backend_started)
            else:
                # Thread terminou (erro ou exceção não tratada)
                self.backend_status_text.configure(text="Failed to start")
                
                # Verificar se houve erro não capturado
                if self.backend_thread and not self.backend_thread.is_alive():
                    # Thread morreu - provavelmente erro não capturado
                    error_msg = "✗ Backend falhou ao iniciar (thread terminou inesperadamente). Verifique os logs para mais detalhes."
                    self._add_log_message(error_msg, "ERROR")
                    
                    # Tentar obter mais informações do log se disponível
                    if self.logger:
                        self.logger.error("Thread do backend terminou sem criar servidor Flask. Verificar erros anteriores nos logs.")
                
                self.btn_start_backend.configure(state="normal", text="Start", fg_color="green")
                self.backend_thread = None
                self.flask_server = None
                self.validation_in_progress = False

            # Código antigo (remover depois):
            if False:  # Desabilitar código antigo
                if self.backend_process and self.backend_process.poll() is None:
                    # Processo ainda rodando, aguardar mais
                    self.after(2000, self._check_backend_started)
                else:
                    # Processo terminou (erro)
                    self.backend_status_text.configure(text="Failed to start")
                    self._add_log_message("Failed to start backend", "ERROR")
                    self.btn_start_backend.configure(state="normal", text="Start")
                    self.backend_process = None

    def _stop_backend(self):
        """Parar processo do backend (nova arquitetura integrada)"""
        try:
            if threading.current_thread() is not threading.main_thread():
                self.after(0, self._stop_backend)
                return
        except Exception:
            pass

        if getattr(self, "backend_stopping", False):
            # Stop já foi acionado; evitar necessidade de múltiplos cliques
            return

        # NOVA ARQUITETURA: Usar _stop_backend_flask
        # Verificar se realmente precisa parar (thread viva OU porta ativa)
        thread_alive = self.backend_thread and self.backend_thread.is_alive()
        port_active = self._is_backend_running()

        if not self.backend_running and not thread_alive and not port_active:
            # Backend já está parado
            self._update_backend_status()
            return

        # Se thread está viva OU porta está ativa, precisa parar (mesmo que backend_running seja False)
        if self.logger:
            self.logger.info(
                f"Parando backend (backend_running={self.backend_running}, thread_alive={thread_alive}, port_active={port_active})"
            )

        try:
            self.backend_stopping = True

            # FEEDBACK VISUAL IMEDIATO
            self.btn_stop_backend.configure(state="normal", text="Stopping...", fg_color="#dc3545")
            try:
                self._show_stop_only()
            except Exception:
                pass
            self.update()

            # Mostrar notificação "Stopping"
            if self.system_tray_manager:
                self.system_tray_manager.show_notification(
                    "SSM Backend", "Stopping...", duration=2
                )

            # Parar backend Flask (nova arquitetura) - executa em threads separadas (não bloqueia)
            self._stop_backend_flask()

            # Verificar status do stop de forma assíncrona (não bloqueia GUI)
            # Usar after() para verificar periodicamente sem travar a interface
            def check_stop_status(attempt=0, max_attempts=60):
                """Verificar se backend parou completamente sem bloquear GUI"""
                port_still_active = self._is_backend_running()
                thread_still_alive = self.backend_thread and self.backend_thread.is_alive()

                if port_still_active or thread_still_alive:
                    if attempt < max_attempts:
                        # Ainda está parando - verificar novamente em 500ms
                        self.after(500, lambda a=attempt+1: check_stop_status(a, max_attempts))
                    else:
                        # Timeout - backend pode não ter parado completamente
                        if self.logger:
                            self.logger.warn(
                                f"Backend ainda ativo após parar (port_active={port_still_active}, thread_alive={thread_still_alive})"
                            )
                        self._add_log_message(
                            "⚠️ Warning: Backend may not have stopped completely",
                            "WARNING",
                        )
                        # Atualizar status mesmo assim
                        self._update_backend_status()
                else:
                    # Backend parou completamente
                    self._add_log_message("✓ Backend stopped successfully", "SUCCESS")
                    # Atualizar status após parar
                    self._update_backend_status()

            # Iniciar verificação assíncrona após 1 segundo (permite que cleanup inicie)
            self.after(1000, lambda: check_stop_status())

            # Código antigo (remover depois):
            if False:  # Desabilitar código antigo
                if self.backend_process:
                    # Tentar terminar o processo de forma mais robusta
                    if sys.platform == "win32":
                        # Windows: CREATE_NEW_PROCESS_GROUP requer abordagem diferente
                        try:
                            pid = self.backend_process.pid

                            # Usar taskkill com /T (tree) para matar processo e todos os filhos
                            # Isso é necessário porque CREATE_NEW_PROCESS_GROUP cria um grupo separado
                            try:
                                result = subprocess.run(
                                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                                    timeout=5,
                                    capture_output=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                )
                                # Aguardar um pouco para o processo terminar
                                time.sleep(0.5)

                                # Verificar se o processo realmente parou
                                if self.backend_process.poll() is None:
                                    # Ainda rodando, tentar novamente
                                    time.sleep(0.5)
                                    subprocess.run(
                                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                                        timeout=3,
                                        capture_output=True,
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                    )
                                    time.sleep(0.5)
                            except subprocess.TimeoutExpired:
                                # Se taskkill demorar muito, tentar kill direto
                                try:
                                    self.backend_process.kill()
                                    self.backend_process.wait(timeout=2)
                                except:
                                    pass
                            except Exception:
                                # Se taskkill falhar, tentar kill direto
                                try:
                                    self.backend_process.kill()
                                    self.backend_process.wait(timeout=2)
                                except:
                                    pass

                            # Verificação final - se ainda estiver rodando, forçar kill
                            try:
                                if self.backend_process.poll() is None:
                                    # Ainda rodando, última tentativa com taskkill
                                    subprocess.run(
                                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                                        timeout=2,
                                        capture_output=True,
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                    )
                                    time.sleep(0.3)
                                    # Se ainda não parou, tentar kill direto
                                    if self.backend_process.poll() is None:
                                        self.backend_process.kill()
                                        self.backend_process.wait(timeout=1)
                            except:
                                pass

                        except Exception as e:
                            # Em caso de erro, tentar kill direto
                            try:
                                if self.backend_process:
                                    self.backend_process.kill()
                                    self.backend_process.wait(timeout=2)
                            except:
                                pass
                    else:
                        # Linux/Mac: enviar SIGTERM
                        self.backend_process.terminate()
                        try:
                            self.backend_process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.backend_process.kill()
                            self.backend_process.wait()

                    self.backend_process = None

        except Exception as e:
            try:
                import traceback

                if self.logger:
                    self.logger.error(f"Erro ao parar backend: {e}")
                    self.logger.error(traceback.format_exc())
            except Exception:
                pass
            try:
                self.backend_status_text.configure(text=f"Error: {str(e)[:30]}")
            except Exception:
                pass
            try:
                self._update_backend_status()
            except Exception:
                pass

    def _check_backend_stopped(self):
        """Verificar se o backend parou (nova arquitetura integrada)"""
        # NOVA ARQUITETURA: Verificar thread ao invés de processo
        thread_still_running = False
        if self.backend_thread:
            try:
                # Verificar se a thread ainda está rodando
                if self.backend_thread.is_alive():
                    thread_still_running = True
                else:
                    # Thread terminou, limpar referência
                    self.backend_thread = None
            except:
                # Erro ao verificar, assumir que parou
                self.backend_thread = None

        # Verificar se a porta ainda está aberta
        port_still_open = self._is_backend_running()

        # Código antigo (remover depois):
        process_still_running = False
        if False:  # Desabilitar código antigo
            if self.backend_process:
                try:
                    # Verificar se o processo ainda está rodando
                    if self.backend_process.poll() is None:
                        process_still_running = True
                    else:
                        # Processo terminou, limpar referência
                        self.backend_process = None
                except:
                    # Erro ao verificar, assumir que parou
                    self.backend_process = None

        if not thread_still_running and not port_still_open:
            # Backend parou completamente
            # Liberar lock de single instance se existir
            if hasattr(self, "_backend_lock") and self._backend_lock:
                try:
                    self._backend_lock.release()
                    self._backend_lock = None
                except Exception:
                    pass

            self._update_backend_status()
            # Limpar referências
            self.backend_thread = None
            self.flask_server = None
            # Invalidar cache quando backend para
            self.cached_next_restart = None
            self.last_api_check_time = None
            # Garantir que as tabs estejam sempre habilitadas
            self._ensure_tabs_enabled()

            # Mostrar notificação "Stopped"
            if self.system_tray_manager:
                self.system_tray_manager.show_notification(
                    "SSM Backend", "Stopped", duration=3
                )
                # Atualizar menu do tray imediatamente
                self.after(100, self._update_tray_menu)
        else:
            # Ainda rodando, tentar parar novamente se necessário
            if thread_still_running:
                # Thread ainda está rodando - tentar parar novamente
                self.after(1000, self._stop_backend_flask)
            # Código antigo (remover depois):
            if False:  # Desabilitar código antigo
                if process_still_running and self.backend_process:
                    # Processo ainda existe, tentar kill mais agressivo
                    try:
                        if sys.platform == "win32":
                            pid = self.backend_process.pid
                            # Usar /T para matar processo e todos os filhos
                            subprocess.run(
                                ["taskkill", "/F", "/T", "/PID", str(pid)],
                                timeout=2,
                                capture_output=True,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                            )
                            time.sleep(0.3)
                            # Se ainda não parou, tentar kill direto
                            if (
                                self.backend_process
                                and self.backend_process.poll() is None
                            ):
                                try:
                                    self.backend_process.kill()
                                    self.backend_process.wait(timeout=1)
                                except:
                                    pass
                        else:
                            self.backend_process.kill()
                    except:
                        pass

            # Verificar novamente após um tempo
            self.after(1000, self._check_backend_stopped)

    def _find_backend_processes(self):
        """Encontrar processos do backend rodando (incluindo processos filhos)"""
        processes = []
        found_pids = set()

        port = 3000
        try:
            config = self._load_config()
            if config:
                port = config.get("api", {}).get("port", 3000)
        except Exception:
            pass

        # NOVA ARQUITETURA: Verificar thread ao invés de processo
        # Nota: Threads não têm PID, então verificamos apenas processos externos
        # O backend agora roda em thread dentro do mesmo processo do Panel SSM
        
        # Tentar encontrar processos Python/EXE relacionados ao backend via psutil
        if HAS_PSUTIL:
            try:
                current_pid = os.getpid()

                for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                    try:
                        proc_info = proc.info
                        pid = proc_info.get("pid")

                        # Ignorar o processo atual (GUI)
                        if pid == current_pid or pid in found_pids:
                            continue

                        proc_obj = None
                        is_backend = False

                        # NOVA ARQUITETURA: Apenas verificar por porta configurada em estado LISTEN
                        # Se um processo EXTERNO está usando a porta configurada em estado LISTEN, é um backend separado
                        try:
                            proc_obj = psutil.Process(pid)
                            for conn in proc_obj.connections():
                                if (
                                    hasattr(conn, "laddr")
                                    and conn.laddr.port == port
                                    and getattr(conn, "status", "").upper() == "LISTEN"
                                ):
                                    # Processo externo escutando na porta do backend - é um backend separado
                                    is_backend = True
                                    break
                        except (
                            psutil.NoSuchProcess,
                            psutil.AccessDenied,
                            psutil.ZombieProcess,
                        ):
                            continue
                        except Exception:
                            pass

                        # REMOVIDO: Verificação por nome/comando (Método 2)
                        # Na nova arquitetura, não há mais processos "SSM Backend.exe" ou "main.py" separados
                        # O backend roda em thread dentro do Panel SSM
                        # Verificar por nome causava falsos positivos (detectava processos Python genéricos)

                        # Se é backend, adicionar processo e seus filhos
                        if is_backend and proc_obj:
                            processes.append(proc_obj)
                            found_pids.add(pid)

                            # Adicionar processos filhos também
                            try:
                                for child in proc_obj.children(recursive=True):
                                    try:
                                        child_pid = child.pid
                                        if child_pid not in found_pids:
                                            processes.append(child)
                                            found_pids.add(child_pid)
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        continue
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass

                    except (
                        psutil.NoSuchProcess,
                        psutil.AccessDenied,
                        psutil.ZombieProcess,
                    ):
                        continue
            except Exception:
                pass

        return processes

    def _stop_backend_flask_sync(self):
        """
        Parar backend Flask de forma síncrona (aguarda conclusão)
        Usado quando a aplicação está fechando para garantir parada completa
        OTIMIZADO: Fechamento rápido para não demorar ao fechar GUI
        """
        import time
        
        if self.logger:
            self.logger.info("Parando backend Flask de forma síncrona (fechamento da aplicação)...")
        
        try:
            # PRIORIDADE: Fechar socket IMEDIATAMENTE primeiro (força serve_forever a retornar)
            if self.flask_server:
                try:
                    socket_to_close = None
                    if hasattr(self.flask_server, "socket"):
                        socket_to_close = self.flask_server.socket
                    elif hasattr(self.flask_server, "_sockets") and self.flask_server._sockets:
                        socket_to_close = self.flask_server._sockets[0] if self.flask_server._sockets else None
                    elif hasattr(self, "_flask_server_socket") and self._flask_server_socket:
                        socket_to_close = self._flask_server_socket

                    if socket_to_close:
                        socket_to_close.close()
                        if self.logger:
                            self.logger.info("Socket Flask fechado IMEDIATAMENTE (fechamento rápido)")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Erro ao fechar socket imediatamente: {e}")
                
                # Tentar shutdown normal (backup)
                try:
                    self.flask_server.shutdown()
                    if self.logger:
                        self.logger.info("Comando shutdown() enviado ao servidor Flask")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Erro no shutdown normal: {e}")
                
                # Limpar referência imediatamente
                self.flask_server = None
            
            # 1. Parar componentes de background (em paralelo, não bloquear)
            try:
                import sys
                from pathlib import Path
                
                if self.ROOT_DIR not in [Path(p) for p in sys.path]:
                    sys.path.insert(0, str(self.ROOT_DIR))
                
                import main
                if hasattr(main, "cleanup_components"):
                    if self.logger:
                        self.logger.info("Parando componentes de background...")
                    main.cleanup_components()
                    # NÃO aguardar - componentes param com timeout próprio (0.2s por serviço)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Erro ao parar componentes: {e}")
            
            # 2. Aguardar thread do backend terminar (timeout REDUZIDO para fechamento rápido)
            if self.backend_thread and self.backend_thread.is_alive():
                if self.logger:
                    self.logger.info("Aguardando thread do backend terminar (timeout: 1.5 segundos)...")
                
                # Aguardar até 1.5 segundos (reduzido de 5s para fechamento mais rápido)
                self.backend_thread.join(timeout=1.5)
                
                if self.backend_thread.is_alive():
                    # Thread ainda está viva - marcar como daemon IMEDIATAMENTE para permitir encerramento
                    if self.logger:
                        self.logger.warning(
                            "Thread do backend não terminou após 1.5 segundos - marcando como daemon para permitir encerramento imediato"
                        )
                    try:
                        self.backend_thread.daemon = True
                    except Exception as e:
                        if self.logger:
                            self.logger.warning(f"Erro ao marcar thread como daemon: {e}")
                else:
                    if self.logger:
                        self.logger.info("Thread do backend terminou com sucesso")
            
            # 4. Limpar referências
            self.backend_thread = None
            self.backend_running = False
            
            if self.logger:
                self.logger.info("Backend Flask parado completamente (modo síncrono)")
                
        except Exception as e:
            import traceback
            if self.logger:
                self.logger.error(f"Erro ao parar backend Flask (modo síncrono): {e}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Em caso de erro, garantir que as threads sejam marcadas como daemon
            if self.backend_thread and self.backend_thread.is_alive():
                try:
                    self.backend_thread.daemon = True
                except:
                    pass
            self.backend_thread = None
            self.backend_running = False

    def _force_stop_backend(self):
        """Forçar parada do backend (usado ao fechar janela) - forma síncrona"""
        # Encontrar todos os processos do backend
        processes = self._find_backend_processes()

        for proc in processes:
            try:
                if isinstance(proc, subprocess.Popen):
                    # Processo subprocess.Popen
                    if sys.platform == "win32":
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=2)
                    else:
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=2)
                elif HAS_PSUTIL and isinstance(proc, psutil.Process):
                    # Processo psutil.Process
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=2)
                else:
                    # Processo identificado por PID (fallback)
                    try:
                        pid = proc if isinstance(proc, int) else proc.pid
                        if sys.platform == "win32":
                            # CREATE_NO_WINDOW para evitar abrir console
                            # Usar /T para matar processo e todos os filhos
                            subprocess.run(
                                ["taskkill", "/F", "/T", "/PID", str(pid)],
                                timeout=2,
                                capture_output=True,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                            )
                        else:
                            os.kill(pid, signal.SIGTERM)
                            import time

                            time.sleep(0.5)
                            try:
                                os.kill(pid, signal.SIGKILL)
                            except:
                                pass
                    except:
                        pass
            except Exception:
                # Tentar kill direto se terminate falhar
                try:
                    if isinstance(proc, subprocess.Popen):
                        proc.kill()
                        proc.wait(timeout=1)
                    elif HAS_PSUTIL and isinstance(proc, psutil.Process):
                        proc.kill()
                        proc.wait(timeout=1)
                except:
                    pass  # Ignorar erros finais

        self.backend_process = None

    def on_closing(self):
        """Handler chamado quando a janela é fechada"""
        self._closing = True

        try:
            self._remove_winapi_resize_hook()
        except Exception:
            pass
        # Se minimizar para tray está habilitado, esconder em vez de fechar
        if (
            self.minimize_to_tray
            and self.system_tray_manager
            and self.system_tray_manager.is_running
        ):
            self.hide_window_to_tray()
            return

        # Caso contrário, fechar normalmente
        # Parar backend se estiver rodando (nova arquitetura integrada)
        if (
            self.backend_thread and self.backend_thread.is_alive()
        ) or self.backend_running:
            # Desabilitar botões para evitar novas ações
            if hasattr(self, "btn_start_backend"):
                self.btn_start_backend.configure(state="disabled")
            if hasattr(self, "btn_stop_backend"):
                self.btn_stop_backend.configure(state="disabled")

            # Atualizar status
            if hasattr(self, "backend_status_text"):
                self.backend_status_text.configure(text="Stopping...")

            # Parar backend Flask (nova arquitetura) - modo síncrono para fechamento
            self._stop_backend_flask_sync()

        # Parar system tray antes de fechar (não bloquear se demorar)
        if self.system_tray_manager:
            try:
                # Tentar parar, mas não aguardar muito tempo
                self.system_tray_manager.stop()
            except Exception as e:
                # Se der erro ao parar tray, apenas logar e continuar fechamento
                if self.logger:
                    self.logger.warning(f"Erro ao parar system tray: {e}")

        # IMPORTANTE: Se a thread do backend ainda estiver viva após tentar parar,
        # marcá-la como daemon ANTES de destruir a janela para permitir que o processo termine
        if self.backend_thread and self.backend_thread.is_alive():
            try:
                self.backend_thread.daemon = True
                if self.logger:
                    self.logger.warning(
                        "Thread do backend ainda ativa ao fechar - marcada como daemon para permitir encerramento"
                    )
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Erro ao marcar thread como daemon: {e}")

        # Fechar janela
        self.destroy()

    def _check_scum_server_via_api(self) -> Optional[bool]:
        """Verificar status do servidor SCUM via API"""
        if not self.backend_running or not HAS_REQUESTS:
            return None

        try:
            response = requests.get(
                "http://127.0.0.1:3000/api/server/status", timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("is_running", False)
        except:
            pass
        return None

    def _check_scum_server_direct(self) -> bool:
        """Verificar serviço SCUM diretamente via Windows"""
        try:
            # CREATE_NO_WINDOW para evitar abrir console
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(
                ["sc", "query", "SCUMServer"],
                capture_output=True,
                text=True,
                timeout=2,
                creationflags=creation_flags,
            )
            return "RUNNING" in result.stdout
        except:
            return False

    def _update_status(self):
        """Atualizar status do servidor SCUM"""
        is_running = False

        # Tentar via ServerManager se disponível
        if self.server_manager:
            try:
                status = self.server_manager.get_status()
                is_running = status.get("is_running", False)
                self.status_running = is_running
            except:
                pass

        # Se não conseguiu via ServerManager, tentar via API
        if not is_running and self.backend_running:
            api_result = self._check_scum_server_via_api()
            if api_result is not None:
                is_running = api_result
                self.status_running = is_running

        # Se ainda não conseguiu, tentar verificação direta (fallback)
        if not is_running:
            try:
                is_running = self._check_scum_server_direct()
                self.status_running = is_running
            except:
                pass

        # Atualizar interface
        if is_running:
            self.status_indicator.configure(text_color="green")
            self.status_text.configure(text="Running")
        else:
            self.status_indicator.configure(text_color="red")
            self.status_text.configure(text="Stopped")

    def _load_fingerprint(self):
        """Carregar hardware fingerprint - sempre funciona mesmo sem logger"""
        try:
            # Sempre criar instância se não existe
            if not self.hardware_fingerprint:
                self.hardware_fingerprint = HardwareFingerprint(logger=self.logger)

            # Gerar hash
            hash_value, components = self.hardware_fingerprint.generate()
            self.hash_value = hash_value

            display_value = hash_value
            try:
                fingerprint_status = (components or {}).get("fingerprint_status")
                fingerprint_message = (components or {}).get("fingerprint_message")
                if fingerprint_status in ("unavailable", "weak") and fingerprint_message:
                    display_value = fingerprint_message
            except Exception:
                pass

            # Atualizar campo apenas se existir
            if hasattr(self, "hash_entry"):
                self.hash_entry.configure(state="normal")
                self.hash_entry.delete(0, "end")
                self.hash_entry.insert(0, display_value)
                self.hash_entry.configure(state="readonly")

        except Exception as e:
            # Tratar erro sem quebrar a interface
            error_msg = f"Failed to generate fingerprint: {str(e)[:50]}"
            if self.logger:
                self.logger.warn(error_msg)

            # Atualizar campo apenas se existir
            if hasattr(self, "hash_entry"):
                self.hash_entry.configure(state="normal")
                self.hash_entry.delete(0, "end")
                self.hash_entry.insert(0, "Failed to generate fingerprint")
                self.hash_entry.configure(state="readonly")

    def _open_frontend(self):
        """Abrir frontend no navegador"""
        try:
            import tkinter.messagebox as messagebox

            possible_roots = []
            if self.IS_EXE:
                possible_roots.extend([self.EXE_DIR, self.EXE_DIR.parent])
            else:
                possible_roots.extend(
                    [
                        self.ROOT_DIR,
                        self.ROOT_DIR.parent,
                        self.ROOT_DIR.parent.parent,
                        Path.cwd(),
                        Path.cwd().parent,
                    ]
                )

            scumserver_dir = None
            for root in possible_roots:
                try:
                    if root.name.lower() == "scumserver":
                        scumserver_dir = root
                        break
                    candidate = root / "ScumServer"
                    if candidate.exists() and candidate.is_dir():
                        scumserver_dir = candidate
                        break
                except Exception:
                    continue

            if scumserver_dir is None:
                messagebox.showerror(
                    "Error",
                    "ScumServer folder not found.\n\n"
                    "Make sure there is a 'ScumServer' folder in the same directory as the application.",
                )
                return

            config_path = scumserver_dir / "Panel" / "config.json"

            if not config_path.exists():
                messagebox.showerror(
                    "Error",
                    "Control Panel config not found.\n\n"
                    f"Expected file at: {config_path}",
                )
                return

            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            frontend_config = config_data.get("frontend", {})
            frontend_host = frontend_config.get("host")
            frontend_port = frontend_config.get("port")

            if not isinstance(frontend_host, str) or not frontend_host.strip():
                messagebox.showerror(
                    "Error",
                    "Control Panel host/IP is missing or invalid in config.json.\n\n"
                    "Configure 'frontend.host' in ScumServer\\Panel\\config.json.",
                )
                return

            if not isinstance(frontend_port, int) or not (1 <= frontend_port <= 65535):
                messagebox.showerror(
                    "Error",
                    "Control Panel port is missing or invalid in config.json.\n\n"
                    "Configure 'frontend.port' in ScumServer\\Panel\\config.json.",
                )
                return

            frontend_url = f"http://{frontend_host.strip()}:{frontend_port}/"
            webbrowser.open(frontend_url)
            if self.logger:
                self.logger.info(f"Frontend aberto: {frontend_url}")
        except Exception as e:
            import tkinter.messagebox as messagebox

            messagebox.showerror("Error", f"Failed to open Control Panel: {str(e)}")
            if self.logger:
                self.logger.warn(f"Failed to open Control Panel: {e}")

    def _open_discord_community(self):
        """Abrir canal oficial do Discord do SSM no navegador"""
        try:
            discord_url = "https://discord.gg/EHwQTKWAtv"
            webbrowser.open(discord_url)
            if self.logger:
                self.logger.info(f"Discord SSM aberto: {discord_url}")
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Erro ao abrir Discord SSM: {e}")

    def _open_site(self):
        """Alias para compatibilidade"""
        self._open_discord_community()

    def _open_gestao(self):
        """Abrir Gestão no navegador"""
        try:
            config = self._load_config()
            if not config:
                import tkinter.messagebox as messagebox

                messagebox.showerror("Error", "Failed to load configuration")
                return

            # Buscar URL dinamicamente do main.py (para desenvolvimento)
            gestao_url = self._get_gestao_server_url()

            licensing_config = config.get("licensing", {})
            gestao_enabled = licensing_config.get("gestao_enabled", False)

            if not gestao_enabled:
                import tkinter.messagebox as messagebox

                messagebox.showwarning(
                    "Warning",
                    "Gestao sync is not enabled.\n\n"
                    "Enable 'gestao_enabled' in config.json under 'licensing'.",
                )
                return

            webbrowser.open(gestao_url)
            if self.logger:
                self.logger.info(f"Gestao opened: {gestao_url}")
        except Exception as e:
            import tkinter.messagebox as messagebox

            messagebox.showerror("Error", f"Failed to open Gestao: {str(e)}")
            if self.logger:
                self.logger.warn(f"Failed to open Gestao: {e}")

    def _toggle_apikey_visibility(self):
        """Alternar visibilidade da API Key"""
        try:
            self.apikey_visible = not self.apikey_visible
            if self.apikey_visible:
                self.gestao_apikey_entry.configure(show="")
                self.btn_toggle_apikey.configure(text="🙈")
            else:
                self.gestao_apikey_entry.configure(show="*")
                self.btn_toggle_apikey.configure(text="👁️")
        except Exception as e:
            self._add_log_message(f"Failed to toggle visibility: {e}", "ERROR")

    def _toggle_apikey_visibility_main(self):
        """Alternar visibilidade da API Key na janela principal"""
        try:
            # Temporariamente habilitar para alterar show se estiver readonly
            was_readonly = self.main_apikey_entry.cget("state") == "readonly"
            if was_readonly:
                self.main_apikey_entry.configure(state="normal")

            self.apikey_visible = not self.apikey_visible
            if self.apikey_visible:
                self.main_apikey_entry.configure(show="")
                # Quando visível, mostrar ícone de ocultar
                hide_icon = IconHelper.load_icon(
                    "ocultar", self.ROOT_DIR, self.EXE_DIR, self.IS_EXE, size=18
                )
                self.btn_toggle_apikey_main.configure(image=hide_icon, text="")
            else:
                self.main_apikey_entry.configure(show="*")
                # Quando oculta, mostrar ícone de ver
                eye_icon = IconHelper.load_icon(
                    "ver", self.ROOT_DIR, self.EXE_DIR, self.IS_EXE, size=18
                )
                self.btn_toggle_apikey_main.configure(image=eye_icon, text="")

            # Restaurar estado readonly se estava bloqueado
            if was_readonly:
                self.main_apikey_entry.configure(state="readonly")
        except Exception as e:
            self._add_log_message(f"Failed to toggle visibility: {e}", "ERROR")

    def _set_apikey_status_main(self, text: str, status: str = "idle"):
        try:
            if not hasattr(self, "apikey_status_label"):
                return
            if status == "dirty":
                self.apikey_status_label.configure(text=text, text_color=("#b58900", "#f0c674"))
            elif status == "saved":
                self.apikey_status_label.configure(text=text, text_color=("#2e7d32", "#4caf50"))
            else:
                self.apikey_status_label.configure(text=text, text_color=("gray40", "gray70"))
        except Exception:
            pass

    def _on_apikey_entry_changed_main(self, _event=None):
        try:
            if not hasattr(self, "main_apikey_entry"):
                return
            self.apikey_dirty = True
            self._set_apikey_status_main("Unsaved changes", status="dirty")
        except Exception:
            pass

    def _load_apikey_main(self):
        """Carregar API Key do config.json para o campo principal"""
        try:
            if not hasattr(self, "main_apikey_entry"):
                return

            config = self._load_config()
            if not config:
                try:
                    self.main_apikey_entry.configure(state="normal")
                except Exception:
                    pass
                return

            licensing_config = config.get("licensing", {})
            apikey = licensing_config.get("gestao_api_key", "")

            if apikey:
                # Descriptografar se necessário
                if apikey.startswith("ENCRYPTED:"):
                    try:
                        from core.security.credential_encryption import (
                            decrypt_credential,
                        )

                        apikey = decrypt_credential(apikey, logger=self.logger)
                    except Exception as e:
                        if self.logger:
                            self.logger.warning(f"Erro ao descriptografar API key: {e}")
                        return

                self.main_apikey_entry.delete(0, "end")
                self.main_apikey_entry.insert(0, apikey)
                self.main_apikey_entry.configure(show="*")
                self.apikey_visible = False
                if hasattr(self, "btn_toggle_apikey_main"):
                    # Quando oculta, mostrar ícone de ver
                    eye_icon = IconHelper.load_icon(
                        "ver", self.ROOT_DIR, self.EXE_DIR, self.IS_EXE, size=18
                    )
                    self.btn_toggle_apikey_main.configure(image=eye_icon, text="")
                try:
                    self.main_apikey_entry.configure(state="normal")
                except Exception:
                    pass
                self.apikey_dirty = False
                self._set_apikey_status_main("", status="idle")
            else:
                try:
                    self.main_apikey_entry.configure(state="normal")
                except Exception:
                    pass
                self.apikey_dirty = False
                self._set_apikey_status_main("", status="idle")
        except Exception as e:
            self._add_log_message(f"Error loading API key: {e}", "ERROR")
            if self.logger:
                self.logger.error(f"Error loading API key: {e}")

    def _set_apikey_edit_mode(self, edit_mode: bool):
        """Set API Key field edit mode"""
        try:
            if not hasattr(self, "main_apikey_entry"):
                return

            if edit_mode:
                # Edit mode: field enabled, save button
                self.main_apikey_entry.configure(state="normal")
                self.apikey_edit_mode = True
                if hasattr(self, "btn_save_edit_apikey"):
                    save_icon = IconHelper.load_icon(
                        "salvar", self.ROOT_DIR, self.EXE_DIR, self.IS_EXE, size=18
                    )
                    self.btn_save_edit_apikey.configure(
                        image=save_icon,
                        text="",
                        command=self._save_apikey_main,
                        fg_color="transparent",
                        hover_color=("#2b2b2b", "#2b2b2b"),  # Dark gray on hover
                    )
            else:
                # Blocked mode: field readonly, edit button
                self.main_apikey_entry.configure(state="readonly")
                self.apikey_edit_mode = False
                if hasattr(self, "btn_save_edit_apikey"):
                    edit_icon = IconHelper.load_icon(
                        "editar", self.ROOT_DIR, self.EXE_DIR, self.IS_EXE, size=18
                    )
                    self.btn_save_edit_apikey.configure(
                        image=edit_icon,
                        text="",
                        command=self._toggle_edit_mode_apikey,
                        fg_color="transparent",
                        hover_color=("#2b2b2b", "#2b2b2b"),  # Dark gray on hover
                    )
        except Exception as e:
            self._add_log_message(f"Error setting edit mode: {e}", "ERROR")

    def _toggle_edit_mode_apikey(self):
        """Toggle API Key edit mode"""
        try:
            if self.apikey_edit_mode:
                # If in edit mode, block
                self._set_apikey_edit_mode(False)
            else:
                # If blocked, enable edit
                self._set_apikey_edit_mode(True)
                # Focus on field for easy editing
                self.main_apikey_entry.focus()
        except Exception as e:
            self._add_log_message(f"Error toggling edit mode: {e}", "ERROR")

    def _save_apikey_main(self):
        """Save API Key directly from main window"""
        try:
            apikey = self.main_apikey_entry.get().strip()

            if not apikey:
                self._add_log_message("API Key is empty", "WARNING")
                import tkinter.messagebox as messagebox

                messagebox.showwarning(
                    "Warning", "Please enter an API Key before saving."
                )
                return

            # Validate basic format (must start with "ssm_")
            if not apikey.startswith("ssm_"):
                self._add_log_message("Invalid API Key format", "WARNING")
                import tkinter.messagebox as messagebox

                messagebox.showerror(
                    "Error",
                    "Invalid API Key format.\n\nThe API Key must start with 'ssm_'",
                )
                return

            # Load current config
            config_path = (
                self.DATA_DIR / "config.json"
                if self.IS_EXE
                else self.ROOT_DIR / "data" / "config.json"
            )

            if not config_path.exists():
                self._add_log_message("config.json not found", "ERROR")
                import tkinter.messagebox as messagebox

                messagebox.showerror(
                    "Error", f"config.json not found at:\n{config_path}"
                )
                return

            # Create backup
            backup_path = (
                config_path.parent
                / f"config.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            shutil.copy2(config_path, backup_path)

            # Validate and repair JSON before loading
            success, config, repair_message = self._validate_and_repair_json(
                config_path
            )

            if not success:
                # If unable to repair, show detailed error
                error_msg = (
                    f"Unable to load config.json:\n{repair_message}\n\n"
                )
                error_msg += f"The file may be corrupted.\n"
                error_msg += f"Backup created: {backup_path.name}\n\n"
                error_msg += "Suggestions:\n"
                error_msg += "1. Check the file manually\n"
                error_msg += "2. Use an online JSON validator\n"
                error_msg += "3. Restore from a previous backup"

                self._add_log_message(
                    f"Error validating config.json: {repair_message}", "ERROR"
                )
                import tkinter.messagebox as messagebox

                messagebox.showerror("Error - Corrupted JSON", error_msg)
                if self.logger:
                    self.logger.error(f"Error validating config.json: {repair_message}")
                return

            if repair_message:
                self._add_log_message(f"⚠️ {repair_message}", "WARNING")

            # Update licensing section
            # Atualizar seção licensing
            if "licensing" not in config:
                config["licensing"] = {}

            # SEGURANÇA: Criptografar API key antes de salvar
            try:
                from core.security.credential_encryption import encrypt_credential

                # Criptografar gestao_api_key se não estiver já criptografada
                if apikey and not apikey.startswith("ENCRYPTED:"):
                    config["licensing"]["gestao_api_key"] = encrypt_credential(
                        apikey, logger=self.logger
                    )
                else:
                    config["licensing"]["gestao_api_key"] = apikey
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        f"Erro ao criptografar API key (salvando em texto plano): {e}"
                    )
                config["licensing"]["gestao_api_key"] = apikey

            # Salvar config
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self._add_log_message("✅ API Key saved successfully", "SUCCESS")

            # Bloquear campo após salvar
            self._set_apikey_edit_mode(False)

            import tkinter.messagebox as messagebox

            messagebox.showinfo(
                "Success",
                "API Key saved successfully!\n\n" f"Backup created: {backup_path.name}",
            )

        except Exception as e:
            self._add_log_message(f"Failed to save API Key: {e}", "ERROR")
            import tkinter.messagebox as messagebox

            messagebox.showerror("Error", f"Failed to save API Key:\n{str(e)}")
            if self.logger:
                self.logger.error(f"Failed to save API Key: {e}")

    def _get_decrypted_apikey(self):
        """Obter API Key descriptografada do campo de entrada"""
        try:
            if not hasattr(self, "gestao_apikey_entry"):
                return None

            apikey = self.gestao_apikey_entry.get().strip()

            if not apikey:
                return None

            # Descriptografar se estiver criptografada
            if apikey.startswith("ENCRYPTED:"):
                try:
                    from core.security.credential_encryption import decrypt_credential

                    apikey = decrypt_credential(apikey, logger=self.logger)
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Erro ao descriptografar API Key: {e}")
                    return None

            return apikey
        except Exception:
            return None

    def _get_decrypted_hash(self):
        """Obter hash descriptografado (se estiver criptografado)"""
        try:
            # Garantir que o hash está carregado
            if not self.hash_value:
                self._load_fingerprint()

            if not self.hash_value:
                return None

            # Descriptografar se estiver criptografado
            hash_value = self.hash_value
            if hash_value.startswith("ENCRYPTED:"):
                try:
                    from core.security.credential_encryption import decrypt_credential

                    hash_value = decrypt_credential(hash_value, logger=self.logger)
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Erro ao descriptografar hash: {e}")
                    return None

            return hash_value
        except Exception:
            return None

    def _validate_apikey_format(self):
        """Validar formato da API Key"""
        try:
            apikey = self.gestao_apikey_entry.get().strip()

            if not apikey:
                self._add_log_message("API Key is empty", "WARNING")
                self.gestao_status_label.configure(
                    text="Status: ⚠️ API Key is empty"
                )
                return False

            # Descriptografar API Key se estiver criptografada
            if apikey.startswith("ENCRYPTED:"):
                try:
                    from core.security.credential_encryption import decrypt_credential

                    apikey = decrypt_credential(apikey, logger=self.logger)
                    if not apikey:
                        self._add_log_message(
                            "API Key criptografada inválida ou chave de descriptografia incorreta",
                            "ERROR",
                        )
                        self.gestao_status_label.configure(
                            text="Status: ❌ Erro ao descriptografar API Key"
                        )
                        return False
                except Exception as e:
                    self._add_log_message(
                        f"Failed to decrypt API Key: {e}", "ERROR"
                    )
                    self.gestao_status_label.configure(
                        text="Status: ❌ Decryption error"
                    )
                    return False

            # Validar formato: ssm_ + 64 caracteres hexadecimais
            if not apikey.startswith("ssm_"):
                self._add_log_message(
                    "Invalid API Key: must start with 'ssm_'", "ERROR"
                )
                self.gestao_status_label.configure(
                    text="Status: ❌ Invalid format (must start with 'ssm_')"
                )
                return False

            hex_part = apikey[4:]  # Remove "ssm_"

            if len(hex_part) != 64:
                self._add_log_message(
                    f"Invalid API Key: must have 64 hex characters (has {len(hex_part)})",
                    "ERROR",
                )
                self.gestao_status_label.configure(
                    text=f"Status: ❌ Invalid format (must have 64 chars, has {len(hex_part)})"
                )
                return False

            # Validar se são apenas caracteres hexadecimais
            try:
                int(hex_part, 16)
            except ValueError:
                self._add_log_message(
                    "Invalid API Key: non-hex characters", "ERROR"
                )
                self.gestao_status_label.configure(
                    text="Status: ❌ Invalid format (non-hex characters)"
                )
                return False

            self._add_log_message("✅ API Key format is valid", "SUCCESS")
            self.gestao_status_label.configure(text="Status: ✅ Valid format")
            return True

        except Exception as e:
            self._add_log_message(f"Failed to validate API Key: {e}", "ERROR")
            return False

    def _test_gestao_connection(self):
        """Testar conexão com o Gestão"""
        try:
            if not HAS_REQUESTS:
                self._add_log_message(
                    "The 'requests' library is not installed. Install it with: pip install requests",
                    "ERROR",
                )
                return

            # Buscar URL dinamicamente do main.py (para desenvolvimento)
            url = self._get_gestao_server_url()
            apikey = self.gestao_apikey_entry.get().strip()

            if not apikey:
                self._add_log_message("API Key is empty", "WARNING")
                return

            # Validar formato primeiro
            if not self._validate_apikey_format():
                return

            self._add_log_message(f"Testing Gestao connection: {url}", "INFO")
            self.gestao_status_label.configure(text="Status: 🔄 Testing connection...")

            def test_connection():
                try:
                    # Obter hash do hardware (descriptografado se necessário)
                    server_hash = self._get_decrypted_hash()
                    if not server_hash:
                        self._add_log_message(
                            "❌ Error: Unable to get server hash", "ERROR"
                        )
                        self.gestao_status_label.configure(
                            text="Status: ❌ Hash not available"
                        )
                        return

                    # Fazer handshake
                    handshake_url = f"{url}/api/v1/servers/ready"
                    self._add_log_message(
                        f"🔄 Handshake URL: {handshake_url}", "INFO"
                    )
                    self._add_log_message(
                        f"🔄 Server hash: {server_hash[:20]}...", "INFO"
                    )

                    response = requests.get(
                        handshake_url, params={"server_hash": server_hash}, timeout=5
                    )

                    self._add_log_message(
                        f"🔄 Response status: {response.status_code}", "INFO"
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data.get("ready"):
                            self._add_log_message(
                                "✅ Gestao connection OK - Server ready", "SUCCESS"
                            )
                            self.gestao_status_label.configure(
                                text="Status: ✅ Connection OK"
                            )
                        else:
                            retry_after = data.get("retry_after", 0)
                            self._add_log_message(
                                f"⚠️ Gestao is not ready (wait {retry_after}s)",
                                "WARNING",
                            )
                            self.gestao_status_label.configure(
                                text=f"Status: ⚠️ Not ready (wait {retry_after}s)"
                            )
                    elif response.status_code == 429:  # Rate Limit
                        try:
                            data = response.json()
                            retry_after = data.get("retry_after", 60)
                            message = data.get("message", "Rate limit reached")
                            self._add_log_message(
                                f"⚠️ Rate limit: {message} (wait {retry_after}s before trying again)",
                                "WARNING",
                            )
                            self.gestao_status_label.configure(
                                text=f"Status: ⚠️ Rate limit (wait {retry_after}s)"
                            )
                        except:
                            self._add_log_message(
                                "⚠️ Rate limit reached - wait a few seconds before trying again",
                                "WARNING",
                            )
                            self.gestao_status_label.configure(
                                text="Status: ⚠️ Rate limit"
                            )
                    elif response.status_code == 403:
                        self._add_log_message(
                            "❌ Server not registered in Gestao", "ERROR"
                        )
                        self.gestao_status_label.configure(
                            text="Status: ❌ Not registered"
                        )
                    else:
                        self._add_log_message(
                            f"❌ Connection error: {response.status_code}", "ERROR"
                        )
                        self.gestao_status_label.configure(
                            text=f"Status: ❌ Error {response.status_code}"
                        )

                except requests.exceptions.ConnectionError:
                    self._add_log_message(
                        "❌ Error: Gestao offline or invalid URL", "ERROR"
                    )
                    self.gestao_status_label.configure(text="Status: ❌ Gestao offline")
                except requests.exceptions.Timeout:
                    self._add_log_message(
                        "❌ Error: Timeout while connecting to Gestao", "ERROR"
                    )
                    self.gestao_status_label.configure(text="Status: ❌ Timeout")
                except Exception as e:
                    self._add_log_message(f"❌ Connection test failed: {e}", "ERROR")
                    self.gestao_status_label.configure(
                        text="Status: ❌ Connection error"
                    )

            # Executar em thread para não travar a interface
            thread = threading.Thread(target=test_connection, daemon=True)
            thread.start()

        except Exception as e:
            self._add_log_message(f"❌ Failed to start connection test: {e}", "ERROR")
            self.gestao_status_label.configure(text="Status: ❌ Error")
            if self.logger:
                self.logger.error(
                    f"Failed to start connection test: {e}", exc_info=True
                )

    def _test_gestao_sync(self):
        """Testar sincronização completa com o Gestão (handshake + sync)"""
        try:
            if not HAS_REQUESTS:
                self._add_log_message(
                    "The 'requests' library is not installed. Install it with: pip install requests",
                    "ERROR",
                )
                return

            # Buscar URL dinamicamente do main.py (para desenvolvimento)
            url = self._get_gestao_server_url()
            apikey = self.gestao_apikey_entry.get().strip()

            if not apikey:
                self._add_log_message("API Key is empty", "WARNING")
                return

            # Validar formato primeiro
            if not self._validate_apikey_format():
                return

            self._add_log_message(
                f"Testing full Gestao sync: {url}", "INFO"
            )
            self.gestao_status_label.configure(
                text="Status: 🔄 Testing sync..."
            )

            def test_sync():
                try:
                    # Obter hash do hardware (descriptografado se necessário)
                    server_hash = self._get_decrypted_hash()
                    if not server_hash:
                        self._add_log_message(
                            "❌ Error: Unable to get server hash", "ERROR"
                        )
                        self.gestao_status_label.configure(
                            text="Status: ❌ Hash not available"
                        )
                        return

                    # Passo 1: Handshake
                    self._add_log_message("🔄 Step 1: Testing handshake...", "INFO")
                    handshake_url = f"{url}/api/v1/servers/ready"
                    self._add_log_message(
                        f"🔄 Handshake URL: {handshake_url}", "INFO"
                    )
                    self._add_log_message(
                        f"🔄 Server hash: {server_hash[:20]}...", "INFO"
                    )

                    response = requests.get(
                        handshake_url, params={"server_hash": server_hash}, timeout=5
                    )

                    self._add_log_message(
                        f"🔄 Response status: {response.status_code}", "INFO"
                    )

                    if response.status_code == 429:  # Rate Limit
                        try:
                            data = response.json()
                            retry_after = data.get("retry_after", 60)
                            message = data.get("message", "Rate limit reached")
                            self._add_log_message(
                                f"⚠️ Rate limit: {message} (wait {retry_after}s before trying again)",
                                "WARNING",
                            )
                            self.gestao_status_label.configure(
                                text=f"Status: ⚠️ Rate limit (wait {retry_after}s)"
                            )
                        except:
                            self._add_log_message(
                                "⚠️ Rate limit reached - wait a few seconds before trying again",
                                "WARNING",
                            )
                            self.gestao_status_label.configure(
                                text="Status: ⚠️ Rate limit"
                            )
                        return

                    if response.status_code != 200:
                        error_msg = (
                            f"❌ Handshake failed: Status {response.status_code}"
                        )
                        if response.status_code == 404:
                            error_msg = "❌ Handshake failed: Endpoint not found (check the URL)"
                        elif response.status_code == 403:
                            error_msg = (
                                "❌ Handshake failed: Server not registered in Gestao"
                            )
                        self._add_log_message(error_msg, "ERROR")
                        self.gestao_status_label.configure(
                            text=f"Status: ❌ Handshake failed ({response.status_code})"
                        )
                        return

                    data = response.json()
                    if not data.get("ready"):
                        retry_after = data.get("retry_after", 0)
                        self._add_log_message(
                            f"⚠️ Gestao is not ready (wait {retry_after}s)",
                            "WARNING",
                        )
                        self.gestao_status_label.configure(
                            text=f"Status: ⚠️ Not ready (wait {retry_after}s)"
                        )
                        return

                    self._add_log_message(
                        "✅ Handshake OK - Server ready", "SUCCESS"
                    )

                    # Passo 2: Sincronização
                    self._add_log_message(
                        "🔄 Step 2: Testing data sync...", "INFO"
                    )

                    # Carregar configuração para obter dados reais
                    config = self._load_config()
                    if not config:
                        self._add_log_message(
                            "❌ Error: Unable to load configuration", "ERROR"
                        )
                        return

                    # Preparar payload de teste (usar dados reais se disponíveis)
                    from core.communication.gestao_sync_service import GestaoSyncService
                    from utils.config_path_helper import ConfigPathHelper
                    from core.webhooks.discord_webhook import DiscordWebhook

                    path_helper = ConfigPathHelper(config)
                    # Criar DiscordWebhook para auditoria (obrigatório)
                    discord_webhook = DiscordWebhook(config, self.logger)
                    sync_service = GestaoSyncService(
                        config,
                        path_helper,
                        self.logger,
                        discord_webhook=discord_webhook,
                    )

                    # Executar sincronização
                    try:
                        self._add_log_message(
                            "🔄 Chamando sync_service.sync_data()...", "INFO"
                        )
                        result = sync_service.sync_data()
                        self._add_log_message(
                            f"🔄 sync_data() retornou: tipo={type(result).__name__}, valor={result is not None}",
                            "INFO",
                        )
                        if self.logger:
                            try:
                                self.logger.debug(
                                    f"Resultado da sincronização: {result}"
                                )
                            except:
                                pass
                    except Exception as sync_error:
                        import traceback

                        error_trace = traceback.format_exc()
                        error_detail = f"{str(sync_error)[:200]}"
                        self._add_log_message(
                            f"❌ Exceção durante sincronização: {error_detail}", "ERROR"
                        )
                        if self.logger:
                            try:
                                self.logger.error(
                                    f"Exceção durante sync_data(): {sync_error}\n{error_trace}",
                                    exc_info=True,
                                )
                            except:
                                pass
                        result = {
                            "success": False,
                            "error": f"Exceção: {error_detail}",
                            "should_retry": False,
                        }

                    # Verificar se result é válido
                    if result is None:
                        self._add_log_message(
                            "❌ Erro: Sincronização retornou resultado inválido (None)",
                            "ERROR",
                        )
                        self.gestao_status_label.configure(
                            text="Status: ❌ Erro na sincronização"
                        )
                        return

                    if not isinstance(result, dict):
                        self._add_log_message(
                            f"❌ Erro: Resultado inválido (tipo: {type(result).__name__})",
                            "ERROR",
                        )
                        self.gestao_status_label.configure(
                            text="Status: ❌ Erro na sincronização"
                        )
                        return

                    if result.get("success"):
                        sync_data = result.get("data", {})
                        players_synced = sync_data.get("players_synced", 0)
                        rankings_synced = sync_data.get(
                            "rankings_synced", 0
                        ) or sync_data.get("rankings_created", 0)
                        server_id = sync_data.get("server_id", "N/A")

                        success_msg = (
                            f"✅ Sincronização completa bem-sucedida!\n"
                            f"   Servidor ID: {server_id}\n"
                            f"   Jogadores sincronizados: {players_synced}\n"
                            f"   Rankings sincronizados: {rankings_synced}"
                        )
                        self._add_log_message(success_msg, "SUCCESS")
                        self.gestao_status_label.configure(
                            text="Status: ✅ Sincronização OK"
                        )

                        # Atualizar última sincronização
                        if hasattr(self, "gestao_info_label"):
                            from datetime import datetime

                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            self.gestao_info_label.configure(
                                text=f"Última sincronização: {now}"
                            )
                    else:
                        error = result.get("error", "Erro desconhecido")
                        retry_after = result.get("retry_after")

                        error_msg = f"❌ Sincronização falhou: {error}"
                        if retry_after:
                            error_msg += f" (tentar novamente em {retry_after}s)"

                        self._add_log_message(error_msg, "ERROR")
                        self.gestao_status_label.configure(
                            text="Status: ❌ Sincronização falhou"
                        )

                except requests.exceptions.ConnectionError:
                    self._add_log_message(
                        "❌ Erro: Gestão offline ou URL inválida", "ERROR"
                    )
                    self.gestao_status_label.configure(text="Status: ❌ Gestão offline")
                except requests.exceptions.Timeout:
                    self._add_log_message(
                        "❌ Erro: Timeout ao sincronizar com Gestão", "ERROR"
                    )
                    self.gestao_status_label.configure(text="Status: ❌ Timeout")
                except Exception as e:
                    error_detail = str(e)[:200]
                    self._add_log_message(
                        f"❌ Erro ao testar sincronização: {error_detail}", "ERROR"
                    )
                    self.gestao_status_label.configure(
                        text="Status: ❌ Erro na sincronização"
                    )
                    if self.logger:
                        self.logger.error(
                            f"Erro ao testar sincronização: {e}", exc_info=True
                        )

            # Executar em thread para não travar a interface
            thread = threading.Thread(target=test_sync, daemon=True)
            thread.start()

        except Exception as e:
            self._add_log_message(
                f"❌ Erro ao iniciar teste de sincronização: {e}", "ERROR"
            )
            self.gestao_status_label.configure(text="Status: ❌ Erro")
            if self.logger:
                self.logger.error(
                    f"Erro ao iniciar teste de sincronização: {e}", exc_info=True
                )

    def _get_apikey_from_portal(self):
        """Obter API Key do portal de licenças"""
        try:
            if not HAS_REQUESTS:
                self._add_log_message(
                    "The 'requests' library is not installed. Install it with: pip install requests",
                    "ERROR",
                )
                return

            config = self._load_config()
            if not config:
                self._add_log_message("Failed to load configuration", "ERROR")
                return

            # Buscar URL dinamicamente do main.py (para desenvolvimento)
            server_url = self._get_license_server_url()

            licensing_config = config.get("licensing", {})
            licensing_enabled = licensing_config.get("enabled", False)

            if not licensing_enabled:
                self._add_log_message(
                    "⚠️ Licensing is not enabled in the config (licensing.enabled=false)",
                    "WARNING",
                )
                import tkinter.messagebox as messagebox

                messagebox.showinfo(
                    "Information",
                    "To get the API Key automatically, configure 'server_url' under 'licensing' in config.json first.",
                )
                return

            # Obter hash do hardware
            if not self.hash_value:
                self._load_fingerprint()

            self._add_log_message("Getting API Key from portal...", "INFO")

            # Tentar obter da lista de licenças
            # Nota: Isso requer autenticação, então por enquanto apenas mostra mensagem
            import tkinter.messagebox as messagebox

            messagebox.showinfo(
                "Get API Key",
                "To get the API Key:\n\n"
                "1. Open the licensing portal\n"
                "2. Create or view your license\n"
                "3. Copy the displayed API Key\n"
                "4. Paste it in the field above\n\n"
                "API Key format: ssm_<64 hex characters>",
            )

        except Exception as e:
            self._add_log_message(f"Failed to get API Key: {e}", "ERROR")

    def _save_gestao_config(self):
        """Salvar configuração do Gestão na seção licensing do config.json"""
        try:
            import json
            import shutil
            from datetime import datetime

            # SEGURANÇA: URL é hardcoded - não precisa validar
            # url e server_url são sempre https://scumsm.com (hardcoded no código)
            apikey = self.gestao_apikey_entry.get().strip()

            if not apikey:
                self._add_log_message("API Key is empty", "WARNING")
                return

            # Validar formato
            if not self._validate_apikey_format():
                return

            # Carregar config atual
            config_path = (
                self.DATA_DIR / "config.json"
                if self.IS_EXE
                else self.ROOT_DIR / "data" / "config.json"
            )

            if not config_path.exists():
                self._add_log_message("config.json not found", "ERROR")
                return

            # Fazer backup
            backup_path = (
                config_path.parent
                / f"config.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            shutil.copy2(config_path, backup_path)

            # Carregar config
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Atualizar seção licensing (usar seção existente)
            if "licensing" not in config:
                config["licensing"] = {}

            # SEGURANÇA: Não salvar server_url e gestao_url - são hardcoded no código
            # URLs são hardcoded para https://scumsm.com por segurança
            # Não atualizar esses campos no config.json
            # SEGURANÇA: API key será criptografada automaticamente ao salvar
            config["licensing"]["gestao_api_key"] = apikey
            config["licensing"]["gestao_enabled"] = True
            config["licensing"]["gestao_sync_interval_seconds"] = config[
                "licensing"
            ].get("gestao_sync_interval_seconds", 300)
            config["licensing"]["gestao_handshake_timeout_seconds"] = config[
                "licensing"
            ].get("gestao_handshake_timeout_seconds", 5)
            config["licensing"]["gestao_sync_timeout_seconds"] = config[
                "licensing"
            ].get("gestao_sync_timeout_seconds", 30)
            config["licensing"]["gestao_max_retry_delay_seconds"] = config[
                "licensing"
            ].get("gestao_max_retry_delay_seconds", 3600)
            config["licensing"]["gestao_max_retries"] = config["licensing"].get(
                "gestao_max_retries", 3
            )

            # SEGURANÇA: Criptografar campos sensíveis antes de salvar
            try:
                from core.security.credential_encryption import encrypt_credential

                # Criptografar gestao_api_key se não estiver já criptografada
                if config["licensing"]["gestao_api_key"] and not config["licensing"][
                    "gestao_api_key"
                ].startswith("ENCRYPTED:"):
                    config["licensing"]["gestao_api_key"] = encrypt_credential(
                        config["licensing"]["gestao_api_key"], logger=self.logger
                    )
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        f"Failed to encrypt API key (may be stored as plain text): {e}"
                    )

            # Salvar config
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self._add_log_message(
                "✅ Configuration saved successfully under 'licensing'", "SUCCESS"
            )
            self.gestao_status_label.configure(text="Status: ✅ Configuration saved")

            import tkinter.messagebox as messagebox

            messagebox.showinfo(
                "Success",
                "Configuration saved successfully!\n\n"
                "Data saved under 'licensing' in config.json.\n\n"
                f"Backup created: {backup_path.name}",
            )

        except Exception as e:
            self._add_log_message(f"Failed to save configuration: {e}", "ERROR")
            import tkinter.messagebox as messagebox

            messagebox.showerror("Error", f"Failed to save configuration:\n{str(e)}")

    def _load_gestao_config(self):
        """Carregar configuração do Gestão da seção licensing do config.json"""
        try:
            # Verificar se os campos existem (janela pode não estar criada ainda)
            if not hasattr(self, "gestao_url_entry") or not hasattr(
                self, "gestao_apikey_entry"
            ):
                return

            config = self._load_config()
            if not config:
                return

            licensing_config = config.get("licensing", {})

            # SEGURANÇA: URLs são hardcoded - não carregar do config.json
            # server_url e gestao_url são definidas no início do arquivo
            if hasattr(self, "licensing_server_url_entry"):
                self.licensing_server_url_entry.delete(0, "end")
                self.licensing_server_url_entry.insert(
                    0, self._get_license_server_url()
                )

            if hasattr(self, "gestao_url_entry"):
                self.gestao_url_entry.delete(0, "end")
                self.gestao_url_entry.insert(0, self._get_gestao_server_url())

            # Carregar API Key (da seção licensing)
            apikey = licensing_config.get("gestao_api_key", "")
            if apikey:
                self.gestao_apikey_entry.delete(0, "end")
                self.gestao_apikey_entry.insert(0, apikey)
                # Ocultar por padrão
                self.gestao_apikey_entry.configure(show="*")
                self.apikey_visible = False
                if hasattr(self, "btn_toggle_apikey"):
                    self.btn_toggle_apikey.configure(text="👁️")

            # Atualizar status
            if hasattr(self, "gestao_status_label"):
                url = (
                    self._get_gestao_server_url()
                    if hasattr(self, "gestao_url_entry")
                    else None
                )
                if url and apikey:
                    # Validar formato (sem mostrar mensagem)
                    if self._validate_apikey_format_silent():
                        self.gestao_status_label.configure(
                            text="Status: ✅ Configured"
                        )
                    else:
                        self.gestao_status_label.configure(
                            text="Status: ⚠️ Configured (invalid format)"
                        )
                elif url or apikey:
                    self.gestao_status_label.configure(
                        text="Status: ⚠️ Incomplete configuration"
                    )
                else:
                    self.gestao_status_label.configure(text="Status: ⚠️ Not configured")

            # Atualizar informação de última sincronização
            if hasattr(self, "gestao_info_label"):
                last_sync = licensing_config.get("gestao_last_sync")
                if last_sync:
                    self.gestao_info_label.configure(
                        text=f"Last sync: {last_sync}"
                    )
                else:
                    self.gestao_info_label.configure(
                        text="Last sync: Never"
                    )

            self._add_log_message(
                "Gestao configuration loaded from config.json", "INFO"
            )

        except Exception as e:
            self._add_log_message(f"Failed to load configuration: {e}", "ERROR")
            if self.logger:
                self.logger.error(f"Failed to load Gestao configuration: {e}")

    def _validate_apikey_format_silent(self):
        """Validar formato da API Key sem mostrar mensagens (para uso interno)"""
        try:
            if not hasattr(self, "gestao_apikey_entry"):
                return False

            apikey = self.gestao_apikey_entry.get().strip()

            if not apikey:
                return False

            # Descriptografar API Key se estiver criptografada
            if apikey.startswith("ENCRYPTED:"):
                try:
                    from core.security.credential_encryption import decrypt_credential

                    apikey = decrypt_credential(apikey, logger=self.logger)
                    if not apikey:
                        return False
                except Exception:
                    return False

            if not apikey.startswith("ssm_"):
                return False

            hex_part = apikey[4:]

            if len(hex_part) != 64:
                return False

            try:
                int(hex_part, 16)
                return True
            except ValueError:
                return False

        except Exception:
            return False

    def _open_settings(self):
        """Abrir janela de configurações"""
        try:
            # Se já existe, apenas trazer para frente
            if self.settings_window is not None:
                try:
                    self.settings_window.lift()
                    self.settings_window.focus_force()
                    self.settings_window.attributes("-topmost", True)
                    self.settings_window.attributes("-topmost", False)
                    return
                except:
                    # Janela foi fechada, criar nova
                    self.settings_window = None

            # Criar nova janela de configurações
            self.settings_window = ctk.CTkToplevel(self)
            self.settings_window.title("Settings - SSM Backend")
            self.settings_window.geometry("700x600")
            self.settings_window.resizable(False, False)

            # Tornar janela filha da principal (transient)
            self.settings_window.transient(self)

            # Garantir que a janela apareça na frente
            self.settings_window.lift()
            self.settings_window.focus_force()
            self.settings_window.attributes("-topmost", True)
            # Remover topmost após trazer para frente (para não ficar sempre no topo)
            self.settings_window.after(
                100, lambda: self.settings_window.attributes("-topmost", False)
            )

            # Criar interface de configurações
            self._create_settings_window()

        except Exception as e:
            self._add_log_message(f"Failed to open settings: {e}", "ERROR")

    def _create_settings_window(self):
        """Criar conteúdo da janela de configurações"""
        if not self.settings_window:
            return

        # Título
        title_label = ctk.CTkLabel(
            self.settings_window,
            text="⚙️ Settings",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title_label.pack(pady=20)

        # Tabs para diferentes seções
        tabview = ctk.CTkTabview(self.settings_window)
        tabview.pack(pady=10, padx=20, fill="both", expand=True)

        # Tab: Licenciamento e Gestão
        licensing_tab = tabview.add("Licensing & Gestao")

        # Seção: Licenciamento
        licensing_frame = ctk.CTkFrame(licensing_tab)
        licensing_frame.pack(pady=10, padx=10, fill="x")

        licensing_title = ctk.CTkLabel(
            licensing_frame,
            text="Licensing",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        licensing_title.pack(pady=(10, 5), padx=10, anchor="w")

        # Server URL
        server_url_frame = ctk.CTkFrame(licensing_frame, fg_color="transparent")
        server_url_frame.pack(pady=5, padx=10, fill="x")

        server_url_label = ctk.CTkLabel(
            server_url_frame, text="Server URL:", font=ctk.CTkFont(size=12)
        )
        server_url_label.pack(side="left", padx=(0, 10))

        self.licensing_server_url_entry = ctk.CTkEntry(
            server_url_frame,
            placeholder_text="URL is hardcoded for security",
            width=400,
            height=30,
            state="disabled",  # Desabilitado - URL é hardcoded por segurança
        )
        self.licensing_server_url_entry.insert(0, self._get_license_server_url())
        self.licensing_server_url_entry.pack(side="left", fill="x", expand=True)

        # Label informativo
        security_note = ctk.CTkLabel(
            server_url_frame,
            text="🔒 Hardcoded for security",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        )
        security_note.pack(side="left", padx=5)

        # Seção: Sincronização com Gestão
        gestao_frame = ctk.CTkFrame(licensing_tab)
        gestao_frame.pack(pady=10, padx=10, fill="x")

        gestao_title = ctk.CTkLabel(
            gestao_frame,
            text="Gestao Sync",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        gestao_title.pack(pady=(10, 5), padx=10, anchor="w")

        # Status da configuração
        gestao_status_frame = ctk.CTkFrame(gestao_frame, fg_color="transparent")
        gestao_status_frame.pack(pady=5, padx=10, fill="x")

        self.gestao_status_label = ctk.CTkLabel(
            gestao_status_frame,
            text="Status: ⚠️ Not configured",
            font=ctk.CTkFont(size=12),
        )
        self.gestao_status_label.pack(side="left", padx=10)

        # URL do Gestão
        url_frame = ctk.CTkFrame(gestao_frame, fg_color="transparent")
        url_frame.pack(pady=5, padx=10, fill="x")

        url_label = ctk.CTkLabel(
            url_frame, text="Gestao URL:", font=ctk.CTkFont(size=12)
        )
        url_label.pack(side="left", padx=(0, 10))

        self.gestao_url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="URL is hardcoded for security",
            width=300,
            height=30,
            state="disabled",  # Desabilitado - URL é hardcoded por segurança
        )
        self.gestao_url_entry.insert(0, self._get_gestao_server_url())
        self.gestao_url_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Label informativo
        security_note_gestao = ctk.CTkLabel(
            url_frame,
            text="🔒 Hardcoded for security",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        )
        security_note_gestao.pack(side="left", padx=5)

        # API Key
        apikey_frame = ctk.CTkFrame(gestao_frame, fg_color="transparent")
        apikey_frame.pack(pady=5, padx=10, fill="x")

        apikey_label = ctk.CTkLabel(
            apikey_frame, text="API Key:", font=ctk.CTkFont(size=12)
        )
        apikey_label.pack(side="left", padx=(0, 10))

        self.gestao_apikey_entry = ctk.CTkEntry(
            apikey_frame,
            placeholder_text="ssm_2d9ba653192f1a872fbef6583485c50fd6265384ace80ecf222727cc41c4ac4c",
            width=300,
            height=30,
            show="*",  # Ocultar API key por segurança
        )
        self.gestao_apikey_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Botão para mostrar/ocultar API key
        self.btn_toggle_apikey = ctk.CTkButton(
            apikey_frame,
            text="👁️",
            command=self._toggle_apikey_visibility,
            width=40,
            height=30,
            fg_color="gray",
            hover_color="darkgray",
        )
        self.btn_toggle_apikey.pack(side="left", padx=5)
        self.apikey_visible = False

        # Botões de ação
        gestao_buttons_frame = ctk.CTkFrame(gestao_frame, fg_color="transparent")
        gestao_buttons_frame.pack(pady=10, padx=10, fill="x")

        # Botão Validar API Key
        self.btn_validate_apikey = ctk.CTkButton(
            gestao_buttons_frame,
            text="Validate API Key",
            command=self._validate_apikey_format,
            width=120,
            height=30,
            fg_color="blue",
            hover_color="darkblue",
        )
        self.btn_validate_apikey.pack(side="left", padx=5)

        # Botão Testar Conexão
        self.btn_test_connection = ctk.CTkButton(
            gestao_buttons_frame,
            text="Test Connection",
            command=self._test_gestao_connection,
            width=120,
            height=30,
            fg_color="green",
            hover_color="darkgreen",
        )
        self.btn_test_connection.pack(side="left", padx=5)

        # Botão Testar Sincronização
        self.btn_test_sync = ctk.CTkButton(
            gestao_buttons_frame,
            text="Test Sync",
            command=self._test_gestao_sync,
            width=140,
            height=30,
            fg_color="purple",
            hover_color="darkviolet",
        )
        self.btn_test_sync.pack(side="left", padx=5)

        # Botão Obter do Portal
        self.btn_get_from_portal = ctk.CTkButton(
            gestao_buttons_frame,
            text="Get From Portal",
            command=self._get_apikey_from_portal,
            width=120,
            height=30,
            fg_color="orange",
            hover_color="darkorange",
        )
        self.btn_get_from_portal.pack(side="left", padx=5)

        # Informações de última sincronização
        self.gestao_info_label = ctk.CTkLabel(
            gestao_frame,
            text="Last sync: Never",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        )
        self.gestao_info_label.pack(pady=(0, 10), padx=10, anchor="w")

        # Tab 'Banco de Dados' desativada nesta janela para evitar duplicação com a tab principal

        # Botão Salvar (na parte inferior da janela)
        save_frame = ctk.CTkFrame(self.settings_window, fg_color="transparent")
        save_frame.pack(pady=10, padx=20, fill="x")

        self.btn_save_gestao = ctk.CTkButton(
            save_frame,
            text="💾 Save Settings",
            command=self._save_gestao_config,
            width=200,
            height=40,
            fg_color="purple",
            hover_color="darkviolet",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.btn_save_gestao.pack()

        # Carregar configuração existente
        self._load_gestao_config()

        # Handler para fechar janela
        def on_settings_close():
            if self.settings_window:
                self.settings_window.destroy()
                self.settings_window = None

        self.settings_window.protocol("WM_DELETE_WINDOW", on_settings_close)

    def _create_database_settings_tab(self, parent):
        """Criar tab de Banco de Dados"""
        try:
            import threading
            from utils.config_path_helper import ConfigPathHelper

            # Frame scrollable para todo o conteúdo
            scrollable_frame = ctk.CTkScrollableFrame(parent)
            scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # ========== SEÇÃO 1: STATUS DO BANCO ==========
            status_frame = ctk.CTkFrame(scrollable_frame)
            status_frame.pack(fill="x", pady=(0, 10), padx=10)

            status_title = ctk.CTkLabel(
                status_frame,
                text="📊 Status do Banco de Dados",
                font=ctk.CTkFont(size=16, weight="bold"),
            )
            status_title.pack(pady=(15, 15), padx=15, anchor="w")

            # Status label
            self.db_status_label = ctk.CTkLabel(
                status_frame, text="Verificando...", font=ctk.CTkFont(size=13)
            )
            self.db_status_label.pack(pady=5, padx=15, anchor="w")

            # Caminho label
            self.db_path_label = ctk.CTkLabel(
                status_frame,
                text="Caminho: Verificando...",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            )
            self.db_path_label.pack(pady=2, padx=15, anchor="w")

            # Tabelas label
            self.db_tables_label = ctk.CTkLabel(
                status_frame,
                text="Tabelas: Verificando...",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            )
            self.db_tables_label.pack(pady=2, padx=15, anchor="w")

            # Tamanho label
            self.db_size_label = ctk.CTkLabel(
                status_frame,
                text="Tamanho: Verificando...",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            )
            self.db_size_label.pack(pady=2, padx=15, anchor="w")

            # ========== SEÇÃO 2: AÇÕES ==========
            actions_frame = ctk.CTkFrame(scrollable_frame)
            actions_frame.pack(fill="x", pady=(0, 10), padx=10)

            actions_title = ctk.CTkLabel(
                actions_frame, text="🔧 Ações", font=ctk.CTkFont(size=16, weight="bold")
            )
            actions_title.pack(pady=(15, 15), padx=15, anchor="w")

            # Botão Inicializar Banco
            self.btn_init_db = ctk.CTkButton(
                actions_frame,
                text="Inicializar Banco de Dados",
                command=self._initialize_database,
                width=250,
                height=40,
                fg_color="green",
                hover_color="darkgreen",
                font=ctk.CTkFont(size=13, weight="bold"),
            )
            self.btn_init_db.pack(pady=5, padx=15, anchor="w")

            init_info_label = ctk.CTkLabel(
                actions_frame,
                text="Cria todas as tabelas necessárias",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            )
            init_info_label.pack(pady=(0, 10), padx=15, anchor="w")

            # Botão Verificar Integridade
            self.btn_verify_integrity = ctk.CTkButton(
                actions_frame,
                text="Verificar Integridade",
                command=self._verify_database_integrity,
                width=250,
                height=40,
                fg_color="blue",
                hover_color="darkblue",
                font=ctk.CTkFont(size=13),
            )
            self.btn_verify_integrity.pack(pady=5, padx=15, anchor="w")

            verify_info_label = ctk.CTkLabel(
                actions_frame,
                text="Verifica se todas as tabelas estão corretas",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            )
            verify_info_label.pack(pady=(0, 10), padx=15, anchor="w")

            # Botão Atualizar Status
            self.btn_refresh_status = ctk.CTkButton(
                actions_frame,
                text="Atualizar Status",
                command=self._check_database_status,
                width=250,
                height=35,
                fg_color="gray",
                hover_color="darkgray",
                font=ctk.CTkFont(size=12),
            )
            self.btn_refresh_status.pack(pady=5, padx=15, anchor="w")

            # ========== SEÇÃO 3: LISTA DE TABELAS ==========
            tables_frame = ctk.CTkFrame(scrollable_frame)
            tables_frame.pack(fill="both", expand=True, pady=(0, 10), padx=10)

            tables_title = ctk.CTkLabel(
                tables_frame,
                text="📋 Tabelas do Banco",
                font=ctk.CTkFont(size=16, weight="bold"),
            )
            tables_title.pack(pady=(15, 10), padx=15, anchor="w")

            # Frame scrollable para lista de tabelas
            self.tables_listbox = ctk.CTkScrollableFrame(tables_frame, height=200)
            self.tables_listbox.pack(fill="both", expand=True, padx=15, pady=(0, 15))

            # Verificar status inicial
            self._check_database_status()
        except Exception as e:
            # Se houver erro ao criar a tab, mostrar mensagem de erro
            error_label = ctk.CTkLabel(
                parent,
                text=f"❌ Erro ao carregar tab Banco de Dados: {str(e)}",
                font=ctk.CTkFont(size=12),
                text_color="red",
            )
            error_label.pack(pady=20, padx=20)
            if self.logger:
                self.logger.error(f"Erro ao criar tab Banco de Dados: {e}")
            import traceback

            traceback.print_exc()

    def _check_database_status(self):
        """Verificar e atualizar status do banco"""
        import threading
        from utils.database_initializer import check_database_status
        from utils.config_path_helper import ConfigPathHelper

        # Desabilitar botão de atualizar durante verificação
        if hasattr(self, "btn_refresh_status"):
            self.btn_refresh_status.configure(state="disabled")

        def check_in_thread():
            try:
                config = self._load_config()
                if not config:
                    config = {}
                path_helper = ConfigPathHelper(config)
                ssm_db_path = path_helper.get_ssm_db_path()

                status = check_database_status(ssm_db_path)

                # Atualizar UI na thread principal
                self.after(0, lambda: self._update_database_status_ui(status))
            except Exception as e:
                error_status = {
                    "exists": False,
                    "initialized": False,
                    "status_message": f"❌ Erro ao verificar: {str(e)}",
                    "path": "N/A",
                    "table_count": 0,
                    "expected_tables": 0,
                    "tables": [],
                    "missing_tables": [],
                    "size_mb": 0.0,
                }
                self.after(0, lambda: self._update_database_status_ui(error_status))
            finally:
                if hasattr(self, "btn_refresh_status"):
                    self.after(
                        0, lambda: self.btn_refresh_status.configure(state="normal")
                    )

        threading.Thread(target=check_in_thread, daemon=True).start()

    def _update_database_status_ui(self, status: dict):
        """Atualizar interface com status do banco"""
        # Atualizar labels
        if hasattr(self, "db_status_label"):
            self.db_status_label.configure(
                text=status.get("status_message", "Status desconhecido")
            )

        if hasattr(self, "db_path_label"):
            path = status.get("path", "N/A")
            # Truncar caminho se muito longo
            if len(path) > 60:
                path = "..." + path[-57:]
            self.db_path_label.configure(text=f"Caminho: {path}")

        if hasattr(self, "db_tables_label"):
            table_count = status.get("table_count", 0)
            expected = status.get("expected_tables")
            if not expected:
                try:
                    from utils.database_initializer import EXPECTED_TABLES

                    expected = len(EXPECTED_TABLES)
                except Exception:
                    expected = 0
            self.db_tables_label.configure(text=f"Tabelas: {table_count}/{expected}")

        columns_per_table = status.get("columns_per_table", {})

        if hasattr(self, "db_size_label"):
            size_mb = status.get("size_mb", 0.0)
            if size_mb > 0:
                self.db_size_label.configure(text=f"Tamanho: {size_mb} MB")
            else:
                self.db_size_label.configure(text="Tamanho: N/A")

        # Atualizar botão de inicializar
        if hasattr(self, "btn_init_db"):
            if status.get("initialized", False):
                self.btn_init_db.configure(state="disabled", fg_color="gray")
            else:
                self.btn_init_db.configure(state="normal", fg_color="green")

        # Atualizar lista de tabelas
        if hasattr(self, "tables_listbox"):
            self._update_tables_list(
                status.get("tables", []),
                status.get("missing_tables", []),
                columns_per_table,
            )

    def _update_tables_list(
        self,
        existing_tables: list,
        missing_tables: list,
        columns_per_table: dict = None,
    ):
        """Atualizar lista visual de tabelas"""
        if not hasattr(self, "tables_listbox"):
            return

        # Limpar lista atual
        for widget in self.tables_listbox.winfo_children():
            widget.destroy()

        from utils.database_initializer import EXPECTED_TABLES, OPTIONAL_TABLES

        categories = {
            "Auth": [
                "frontend_users",
                "password_reset_tokens",
                "frontend_user_permissions",
                "frontend_user_groups",
                "frontend_user_group_members",
            ],
            "Players/Rankings": [
                "players",
                "players_online",
                "player_fame_totals",
                "player_permissions",
                "rankings",
                "fishing_rankings",
            ],
            "Squads": ["squad_snapshot", "squad_member_snapshot"],
            "Survival": ["survival_stats_snapshot", "player_skills"],
            "Banking": [
                "bank_accounts_snapshot",
                "bank_transactions",
                "transaction_types",
                "locations",
                "items",
            ],
            "Chests": ["chest_snapshot", "chest_history"],
            "GPS": ["player_gps_snapshot"],
            "Elevated Users": ["elevated_user"],
            "Events": [
                "kill_events",
                "minigame_events",
                "vehicle_destruction_events",
                "admin_commands_processed",
            ],
            "Vehicles": ["vehicle_current_ownership", "vehicle_ownership_history"],
            "Logs": ["log_files_processed", "log_cursors", "player_logins"],
            "Licensing": ["hardware_fingerprints", "license_validations"],
            "Weather": ["weather_parameters"],
            "Bunkers": [
                "bunker_status",
                "abandoned_bunker",
                "abandoned_bunker_mesh_instance_bound_to_activation",
            ],
            "Outros": [],
        }
        table_to_category = {}
        for cat, tables in categories.items():
            for t in tables:
                table_to_category[t] = cat
        existing_set = set(existing_tables)
        missing_set = set(missing_tables)
        all_expected = [t for t in EXPECTED_TABLES]
        for t in OPTIONAL_TABLES:
            if t not in table_to_category:
                table_to_category[t] = "Outros"
                categories["Outros"].append(t)
        grouped = {}
        for t in all_expected:
            cat = table_to_category.get(t, "Outros")
            if cat not in grouped:
                grouped[cat] = []
            count = 0
            if columns_per_table and isinstance(columns_per_table, dict):
                count = columns_per_table.get(t, 0)
            status_ok = t in existing_set
            grouped[cat].append((t, count, status_ok))
        order = [
            "Auth",
            "Players/Rankings",
            "Squads",
            "Survival",
            "Banking",
            "Chests",
            "GPS",
            "Elevated Users",
            "Events",
            "Vehicles",
            "Logs",
            "Licensing",
            "Weather",
            "Bunkers",
            "Outros",
        ]
        for cat in order:
            if cat not in grouped or len(grouped[cat]) == 0:
                continue
            section_frame = ctk.CTkFrame(self.tables_listbox)
            section_frame.pack(fill="x", padx=5, pady=(8, 4))
            title = ctk.CTkLabel(
                section_frame, text=cat, font=ctk.CTkFont(size=12, weight="bold")
            )
            title.pack(anchor="w", padx=5, pady=(2, 6))
            items = sorted(grouped[cat], key=lambda x: x[1], reverse=True)
            for name, count, ok in items:
                color = None
                prefix = "✅" if ok else "❌"
                text = (
                    f"{prefix} {name} {count}/{count}" if ok else f"{prefix} {name} 0/0"
                )
                lbl = ctk.CTkLabel(
                    section_frame,
                    text=text,
                    font=ctk.CTkFont(size=11),
                    text_color=color,
                )
                lbl.pack(anchor="w", padx=10, pady=2)

    def _initialize_database(self):
        """Inicializar banco de dados"""
        import threading
        from utils.database_initializer import initialize_all_tables
        from utils.config_path_helper import ConfigPathHelper

        # Confirmar ação
        if not hasattr(self, "db_status_label"):
            return

        # Verificar se backend está rodando
        if self.backend_running:
            self._add_log_message(
                "⚠️ Backend está rodando. Pare o backend antes de inicializar o banco.",
                "WARNING",
            )
            return

        # Desabilitar botão durante inicialização
        if hasattr(self, "btn_init_db"):
            self.btn_init_db.configure(state="disabled")

        # Atualizar status
        if hasattr(self, "db_status_label"):
            self.db_status_label.configure(text="⏳ Inicializando banco de dados...")

        def init_in_thread():
            try:
                path_helper = ConfigPathHelper()
                ssm_db_path = path_helper.get_ssm_db_path()
                config = self._load_config()

                # Callback de progresso
                def progress_callback(current, total, table_name):
                    self.after(
                        0, lambda: self._update_progress(current, total, table_name)
                    )

                result = initialize_all_tables(
                    ssm_db_path,
                    config=config,
                    path_helper=path_helper,
                    logger=self.logger,
                    progress_callback=progress_callback,
                )

                # Atualizar UI na thread principal
                self.after(0, lambda: self._on_initialization_complete(result))

            except Exception as e:
                error_result = {
                    "success": False,
                    "tables_created": 0,
                    "tables_total": 0,
                    "errors": [{"table": "unknown", "error": str(e)}],
                    "duration_seconds": 0,
                }
                self.after(0, lambda: self._on_initialization_complete(error_result))

        threading.Thread(target=init_in_thread, daemon=True).start()

    def _update_progress(self, current: int, total: int, table_name: str):
        """Atualizar progresso da inicialização"""
        if hasattr(self, "db_status_label"):
            percent = int((current / total) * 100) if total > 0 else 0
            self.db_status_label.configure(
                text=f"⏳ Inicializando... {percent}% ({current}/{total}) - {table_name}"
            )

    def _on_initialization_complete(self, result: dict):
        """Callback quando inicialização completa"""
        if result.get("success", False):
            tables_created = result.get("tables_created", 0)
            duration = result.get("duration_seconds", 0)
            self._add_log_message(
                f"✅ Banco inicializado com sucesso! {tables_created} tabelas criadas em {duration}s",
                "SUCCESS",
            )
        else:
            errors = result.get("errors", [])
            error_count = len(errors)
            self._add_log_message(
                f"❌ Erro ao inicializar banco: {error_count} erro(s) encontrado(s)",
                "ERROR",
            )
            for error in errors[:5]:  # Mostrar apenas os primeiros 5 erros
                self._add_log_message(
                    f"  - {error.get('table', 'unknown')}: {error.get('error', 'Erro desconhecido')}",
                    "ERROR",
                )

        # Reabilitar botão
        if hasattr(self, "btn_init_db"):
            self.btn_init_db.configure(state="normal")

        # Atualizar status
        self._check_database_status()

    def _verify_database_integrity(self):
        """Verificar integridade do banco de dados"""
        import threading
        from utils.database_initializer import verify_database_integrity
        from utils.config_path_helper import ConfigPathHelper

        # Desabilitar botão durante verificação
        if hasattr(self, "btn_verify_integrity"):
            self.btn_verify_integrity.configure(state="disabled")

        if hasattr(self, "db_status_label"):
            self.db_status_label.configure(text="⏳ Verificando integridade...")

        def verify_in_thread():
            try:
                config = self._load_config()
                if not config:
                    config = {}
                path_helper = ConfigPathHelper(config)
                ssm_db_path = path_helper.get_ssm_db_path()

                result = verify_database_integrity(ssm_db_path)

                # Atualizar UI na thread principal
                self.after(0, lambda: self._on_integrity_check_complete(result))
            except Exception as e:
                error_result = {
                    "valid": False,
                    "issues": [f"Erro ao verificar: {str(e)}"],
                    "table_status": {},
                }
                self.after(0, lambda: self._on_integrity_check_complete(error_result))
            finally:
                if hasattr(self, "btn_verify_integrity"):
                    self.after(
                        0, lambda: self.btn_verify_integrity.configure(state="normal")
                    )

        threading.Thread(target=verify_in_thread, daemon=True).start()

    def _on_integrity_check_complete(self, result: dict):
        """Callback quando verificação de integridade completa"""
        if result.get("valid", False):
            self._add_log_message(
                "✅ Integridade verificada: Todas as tabelas estão corretas", "SUCCESS"
            )
        else:
            issues = result.get("issues", [])
            self._add_log_message(f"⚠️ Problemas encontrados: {len(issues)}", "WARNING")
            for issue in issues[:5]:  # Mostrar apenas os primeiros 5 problemas
                self._add_log_message(f"  - {issue}", "WARNING")

        # Atualizar status
        self._check_database_status()

    def _copy_hash(self):
        """Copiar hash para área de transferência"""
        hash_to_copy = self._get_decrypted_hash()
        if hash_to_copy:
            try:
                pyperclip.copy(hash_to_copy)
                # Feedback visual: trocar ícone para copiado.png
                try:
                    # Tentar carregar ícone copiado
                    copied_icon = IconHelper.load_icon(
                        "copiado", self.ROOT_DIR, self.EXE_DIR, self.IS_EXE, size=18
                    )
                    self.btn_copy.configure(image=copied_icon)
                    # Restaurar ícone original após 2 segundos
                    self.after(
                        2000,
                        lambda: self.btn_copy.configure(image=self.copy_icon_original),
                    )
                except Exception:
                    # Se não encontrar copiado.png, usar texto como fallback
                    original_text = self.btn_copy.cget("text")
                    self.btn_copy.configure(text="Copied!")
                    self.after(
                        2000, lambda: self.btn_copy.configure(text=original_text)
                    )
            except Exception as e:
                if self.logger:
                    self.logger.warn(f"Erro ao copiar hash: {e}")

    def _get_restart_countdown_via_api(self) -> Optional[str]:
        """Obter próximo restart via API com cache (evita requisições excessivas)"""
        if not self.backend_running or not HAS_REQUESTS:
            # Invalidar cache se backend não está rodando
            self.cached_next_restart = None
            self.last_api_check_time = None
            return None

        # Verificar se cache é válido (última requisição há menos de cache_ttl_seconds)
        if self.cached_next_restart and self.last_api_check_time:
            elapsed = time.time() - self.last_api_check_time
            if elapsed < self.cache_ttl_seconds:
                # Cache ainda válido, retornar sem fazer requisição
                return self.cached_next_restart

        # Cache expirado ou não existe, fazer nova requisição
        try:
            response = requests.get(
                "http://127.0.0.1:3000/api/scheduler/status", timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                next_restart_str = data.get("data", {}).get("next_restart")
                # Atualizar cache
                self.cached_next_restart = next_restart_str
                self.last_api_check_time = time.time()
                return next_restart_str
        except:
            pass
        return None

    def _update_restart_countdown(self):
        """Atualizar contador de próximo restart"""
        try:
            next_restart_str = None

            # Tentar obter via restart_scheduler se disponível
            if self.restart_scheduler:
                try:
                    status = self.restart_scheduler.get_status()
                    data = status.get("data", {})
                    next_restart_str = data.get("next_restart")
                except:
                    pass

            # Se não conseguiu, tentar via API
            if not next_restart_str and self.backend_running:
                next_restart_str = self._get_restart_countdown_via_api()

            if not next_restart_str:
                self.restart_countdown.configure(text="Not scheduled")
                return

            # Calcular tempo restante
            from datetime import datetime

            # Parse da data ISO (formato: "2025-11-01T05:00:00" ou "2025-11-01T05:00:00Z")
            next_restart_str_clean = next_restart_str.replace("Z", "")
            try:
                next_restart = datetime.fromisoformat(next_restart_str_clean)
            except:
                # Tentar formato alternativo
                try:
                    next_restart = datetime.strptime(
                        next_restart_str_clean, "%Y-%m-%dT%H:%M:%S"
                    )
                except:
                    self.restart_countdown.configure(text="Invalid format")
                    return

            now = datetime.now()

            diff = next_restart - now

            if diff.total_seconds() < 0:
                self.restart_countdown.configure(text="Passed")
                # Invalidar cache para buscar próximo restart na próxima atualização
                self.cached_next_restart = None
                self.last_api_check_time = None
                return

            # Formatar como "Xh Ym" ou "Ym Zs"
            total_seconds = int(diff.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            if hours > 0:
                countdown_text = f"{hours}h {minutes}m"
            elif minutes > 0:
                countdown_text = f"{minutes}min {seconds}s"
            else:
                countdown_text = f"{seconds}s"

            self.restart_countdown.configure(text=countdown_text)

        except Exception as e:
            if self.logger:
                self.logger.warn(f"Erro ao atualizar countdown: {e}")
            self.restart_countdown.configure(text="Error")

    def _update_restart_countdown_periodic(self):
        """Atualização periódica do countdown (a cada segundo)"""
        if getattr(self, "_closing", False):
            return
        self._update_restart_countdown()
        self.after(1000, self._update_restart_countdown_periodic)

    def _periodic_update(self):
        """Atualização periódica do status"""
        if getattr(self, "_closing", False):
            return
        self._update_backend_status()
        self._update_status()
        self.after(30000, self._periodic_update)

    # ============================================================================
    # SYSTEM TRAY METHODS
    # ============================================================================

    def _load_tray_preference(self) -> bool:
        """Carregar preferência de minimizar para tray do config.json"""
        try:
            config = self._load_config()
            if config:
                gui_config = config.get("gui", {})
                return gui_config.get("minimize_to_tray", True)  # Padrão: True
            return True  # Padrão se não houver config
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Erro ao carregar preferência do tray: {e}")
            return True  # Padrão em caso de erro

    def _save_tray_preference(self):
        """Salvar preferência de minimizar para tray no config.json"""
        try:
            import json

            config_path = (
                self.DATA_DIR / "config.json"
                if self.IS_EXE
                else self.ROOT_DIR / "data" / "config.json"
            )

            # Carregar config existente
            config = {}
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                except:
                    pass

            # Adicionar/atualizar seção gui
            if "gui" not in config:
                config["gui"] = {}

            config["gui"]["minimize_to_tray"] = self.minimize_to_tray

            # Salvar
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            if self.logger:
                self.logger.info(f"Preferência do tray salva: {self.minimize_to_tray}")
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Erro ao salvar preferência do tray: {e}")

    def _init_system_tray(self):
        """Inicializar system tray"""
        try:
            if not SystemTrayManager.is_available():
                return

            icon_path = None
            w_ssm_ico_icon_path = (
                self.ROOT_DIR / "data" / "imagens" / "LogoSSM" / "W-SSM-Ico.ico"
            )
            icon_path = str(w_ssm_ico_icon_path)

            # Criar SystemTrayManager
            self.system_tray_manager = SystemTrayManager(
                main_window=self,
                icon_path=icon_path,
                on_show=self._on_tray_show,
                on_quit=self._on_tray_quit,
                on_start=self._on_tray_start,
                on_stop=self._on_tray_stop,
            )

            # Iniciar tray
            if not self.system_tray_manager.start():
                self.system_tray_manager = None
            else:
                try:
                    self._update_tray_icon()
                except Exception:
                    pass

        except Exception:
            self.system_tray_manager = None

    def _on_tray_checkbox_changed(self):
        """Handler quando checkbox do tray é alterado"""
        try:
            if self.tray_checkbox:
                self.minimize_to_tray = self.tray_checkbox.get() == 1

                # Salvar preferência
                self._save_tray_preference()

                # Inicializar ou parar system tray conforme necessário
                if self.minimize_to_tray:
                    if (
                        not self.system_tray_manager
                        or not self.system_tray_manager.is_running
                    ):
                        self._init_system_tray()
                else:
                    if self.system_tray_manager:
                        self.system_tray_manager.stop()
                        self.system_tray_manager = None

                # Preferência salva silenciosamente
        except Exception:
            pass

    def hide_window_to_tray(self):
        """Esconder janela e mostrar no system tray"""
        try:
            self.withdraw()  # Esconder janela
            self.is_minimized_to_tray = True

            if self.system_tray_manager:
                self.system_tray_manager.show_notification(
                    "SSM Backend", "Application minimized to notification area"
                )

            # Aplicativo minimizado silenciosamente
        except Exception:
            pass

    def show_window_from_tray(self):
        """Restaurar janela do system tray"""
        try:
            self.deiconify()  # Mostrar janela
            self.lift()  # Trazer para frente
            self.focus_force()  # Focar na janela
            self.is_minimized_to_tray = False

            # Aplicativo restaurado silenciosamente
        except Exception:
            pass

    def _on_tray_show(self):
        """Callback quando 'Mostrar' é clicado no menu do tray"""
        self.show_window_from_tray()

    def _on_tray_start(self):
        """Callback quando 'Start' é clicado no menu do tray"""
        # SEGURANÇA: Verificar se backend já está rodando ou se validação está em andamento
        if self.backend_running:
            return  # Backend já está rodando

        if self.validation_in_progress:
            # Validação já em andamento - não iniciar outra
            return

        # Notificação "Starting" será mostrada em _start_backend
        self._start_backend()
        # Atualizar menu do tray após iniciar
        self.after(2000, self._update_tray_menu)  # Aguardar 2s para o estado atualizar

    def _on_tray_stop(self):
        """Callback quando 'Stop' é clicado no menu do tray"""
        if self.backend_running:
            # Notificação "Stopping" será mostrada em _stop_backend
            self._stop_backend()
            # Atualizar menu do tray após parar
            self.after(
                2000, self._update_tray_menu
            )  # Aguardar 2s para o estado atualizar

    def _update_tray_menu(self):
        """Atualizar menu do system tray quando estado do backend mudar"""
        if self.system_tray_manager:
            self.system_tray_manager._update_menu()

    def _get_backend_state_icon_path(self) -> Optional[str]:
        try:
            base = self.EXE_DIR if getattr(self, "IS_EXE", False) else self.ROOT_DIR
            base = Path(base)
            icons_dir = base / "data" / "imagens" / "Icons"
            filename = "Start.ico" if bool(getattr(self, "backend_running", False)) else "Stop.ico"
            p = icons_dir / filename
            if p.exists():
                return str(p)
            return None
        except Exception:
            return None

    def _update_tray_icon(self) -> None:
        try:
            if not self.system_tray_manager:
                return
            icon_path = self._get_backend_state_icon_path()
            if icon_path:
                self.system_tray_manager.update_icon(icon_path)
        except Exception:
            return

    def _on_tray_quit(self):
        """Callback quando 'Sair' é clicado no menu do tray"""
        # Fechar normalmente (sem minimizar para tray)
        self.minimize_to_tray = False
        if self.tray_checkbox:
            self.tray_checkbox.deselect()

        # Chamar on_closing que vai fechar tudo
        self.on_closing()
        self.on_closing()
