"""
Gerenciador de System Tray para minimizar aplicativo para área de notificação
"""

import threading
import os
from pathlib import Path
from typing import Optional, Callable
from PIL import Image

try:
    import pystray

    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False
    pystray = None


class SystemTrayManager:
    """Gerenciador do System Tray (área de notificação)"""

    def __init__(
        self,
        main_window,
        icon_path: Optional[str] = None,
        on_show: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
    ):
        """
        Inicializar gerenciador de system tray

        Args:
            main_window: Instância da MainWindow
            icon_path: Caminho para o ícone (opcional)
            on_show: Callback quando "Mostrar" é clicado
            on_quit: Callback quando "Sair" é clicado
            on_start: Callback quando "Start" é clicado
            on_stop: Callback quando "Stop" é clicado
        """
        self.main_window = main_window
        self.icon_path = icon_path or self._find_default_icon()
        self.on_show = on_show
        self.on_quit = on_quit
        self.on_start = on_start
        self.on_stop = on_stop

        self.tray_icon: Optional[pystray.Icon] = None
        self.tray_thread: Optional[threading.Thread] = None
        self.is_running = False

        # winotify não precisa de instância persistente, mas vamos manter compatibilidade
        self._has_winotify = False
        try:
            from winotify import Notification

            self._has_winotify = True
        except ImportError:
            self._has_winotify = False

        # Detectar se está rodando como executável
        if getattr(main_window, "IS_EXE", False):
            self.ROOT_DIR = Path(main_window.EXE_DIR)
        else:
            self.ROOT_DIR = Path(main_window.ROOT_DIR)

    def _find_default_icon(self) -> Optional[str]:
        """Encontrar ícone padrão para system tray"""
        ssm_windows_ico_icon_path = (
            self.ROOT_DIR / "data" / "imagens" / "LogoSSM" / "W-SSM-Ico.ico"
        )
        return str(ssm_windows_ico_icon_path)

    def _load_tray_icon(self) -> Optional[Image.Image]:
        """Carregar ícone para system tray"""
        if not HAS_PYSTRAY:
            return None

        try:
            if self.icon_path and os.path.exists(self.icon_path):
                # Carregar ícone ICO
                icon = Image.open(self.icon_path)
                # Redimensionar para tamanho adequado do tray (16x16 ou 32x32)
                if icon.size[0] > 32 or icon.size[1] > 32:
                    icon = icon.resize((32, 32), Image.Resampling.LANCZOS)
                return icon
            else:
                # Criar ícone simples se não encontrar arquivo
                return self._create_simple_icon()
        except Exception:
            return self._create_simple_icon()

    def _create_simple_icon(self) -> Image.Image:
        """Criar ícone simples caso não encontre arquivo"""
        # Criar ícone simples com "SSM"
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(img)

        # Desenhar círculo de fundo
        draw.ellipse([2, 2, 30, 30], fill=(70, 130, 180, 255))  # Azul aço

        # Tentar desenhar texto "SSM"
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None

        if font:
            text = "SSM"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (32 - text_width) // 2
            y = (32 - text_height) // 2
            draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

        return img

    def _create_tray_menu(self) -> Optional[pystray.Menu]:
        """Criar menu de contexto do system tray"""
        if not HAS_PYSTRAY:
            return None

        menu_items = []

        # Item "Show" (restore window)
        menu_items.append(
            pystray.MenuItem(
                "Show",
                self._on_tray_show,
                default=True,  # Duplo clique executa esta ação
            )
        )

        menu_items.append(pystray.Menu.SEPARATOR)

        # Item dinâmico Start/Stop baseado no estado do backend
        backend_running = getattr(self.main_window, "backend_running", False)
        if backend_running:
            # Se está rodando, mostrar "Stop"
            menu_items.append(pystray.MenuItem("Stop", self._on_tray_stop))
        else:
            # Se está parado, mostrar "Start"
            menu_items.append(pystray.MenuItem("Start", self._on_tray_start))

        menu_items.append(pystray.Menu.SEPARATOR)

        # Item "Exit"
        menu_items.append(pystray.MenuItem("Exit", self._on_tray_quit))

        return pystray.Menu(*menu_items)

    def _on_tray_show(self, icon: pystray.Icon, item: pystray.MenuItem):
        """Handler quando 'Mostrar' é clicado no menu"""
        if self.on_show:
            self.on_show()

    def _on_tray_start(self, icon: pystray.Icon, item: pystray.MenuItem):
        """Handler quando 'Start' é clicado no menu"""
        if self.on_start:
            self.on_start()
        # Menu será atualizado automaticamente quando o estado mudar

    def _on_tray_stop(self, icon: pystray.Icon, item: pystray.MenuItem):
        """Handler quando 'Stop' é clicado no menu"""
        if self.on_stop:
            self.on_stop()
        # Menu será atualizado automaticamente quando o estado mudar

    def _on_tray_quit(self, icon: pystray.Icon, item: pystray.MenuItem):
        """Handler quando 'Sair' é clicado no menu"""
        if self.on_quit:
            self.on_quit()

    def _update_menu(self):
        """Atualizar menu do system tray de forma thread-safe"""
        if not HAS_PYSTRAY or not self.tray_icon:
            return

        # Executar no thread principal da GUI para garantir thread-safety
        if hasattr(self.main_window, "after"):

            def update():
                try:
                    # Recriar menu com estado atualizado
                    new_menu = self._create_tray_menu()
                    if new_menu and self.tray_icon:
                        self.tray_icon.menu = new_menu
                except Exception:
                    pass

            self.main_window.after(0, update)
        else:
            # Se não tiver método after, tentar diretamente
            try:
                new_menu = self._create_tray_menu()
                if new_menu and self.tray_icon:
                    self.tray_icon.menu = new_menu
            except Exception:
                pass

    def start(self):
        """Iniciar system tray em thread separada"""
        if not HAS_PYSTRAY:
            return False

        if self.is_running:
            return False

        try:
            # Carregar ícone
            icon_image = self._load_tray_icon()
            if not icon_image:
                return False

            # Criar menu
            menu = self._create_tray_menu()
            if not menu:
                return False

            # Criar ícone do tray
            self.tray_icon = pystray.Icon(
                "SSM Backend", icon_image, "SSM Backend - Status and Licensing", menu
            )

            # Iniciar em thread separada
            self.is_running = True
            self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
            self.tray_thread.start()

            return True

        except Exception:
            self.is_running = False
            return False

    def _run_tray(self):
        """Executar system tray (deve rodar em thread separada)"""
        try:
            if self.tray_icon:
                self.tray_icon.run()
        except Exception:
            pass
        finally:
            self.is_running = False

    def stop(self):
        """Parar system tray"""
        if not self.is_running or not self.tray_icon:
            return

        try:
            self.is_running = False
            if self.tray_icon:
                self.tray_icon.stop()
            if self.tray_thread and self.tray_thread.is_alive():
                self.tray_thread.join(timeout=2)
        except Exception:
            pass

    def show_notification(self, title: str, message: str, duration: int = 3):
        """Mostrar notificação do system tray usando Windows Toast (winotify)"""
        if not HAS_PYSTRAY or not self.tray_icon:
            return

        # Usar winotify para notificações robustas (funciona perfeitamente em executáveis)
        if self._has_winotify:
            try:
                from winotify import Notification

                # Converter duration para formato do winotify
                # winotify aceita "short" (5s) ou "long" (25s)
                duration_str = "long" if duration > 10 else "short"

                # Criar notificação
                toast = Notification(
                    app_id="SSM Backend",
                    title=title,
                    msg=message,
                    duration=duration_str,
                )

                # Executar no thread principal da GUI para garantir thread-safety
                if hasattr(self.main_window, "after"):

                    def _show_toast_in_gui_thread():
                        try:
                            toast.show()
                        except Exception:
                            # Se falhar, usar tooltip como fallback
                            if self.tray_icon:
                                self.tray_icon.title = f"{title}\n{message}"

                    self.main_window.after(0, _show_toast_in_gui_thread)
                else:
                    # Se não tiver método after, tentar diretamente
                    try:
                        toast.show()
                    except Exception:
                        if self.tray_icon:
                            self.tray_icon.title = f"{title}\n{message}"
                return

            except Exception:
                # Se falhar, usar tooltip como fallback
                pass

        # Fallback: usar tooltip do system tray
        if self.tray_icon:
            try:
                self.tray_icon.title = f"{title}\n{message}"
            except Exception:
                pass

    def update_icon(self, icon_path: Optional[str] = None):
        """Atualizar ícone do system tray"""
        if not HAS_PYSTRAY or not self.tray_icon:
            return

        try:
            if icon_path:
                self.icon_path = icon_path

            icon_image = self._load_tray_icon()
            if icon_image:
                self.tray_icon.icon = icon_image
        except Exception:
            pass

    @staticmethod
    def is_available() -> bool:
        """Verificar se system tray está disponível"""
        return HAS_PYSTRAY
