"""
Sistema de prevenção de múltiplas instâncias
Garante que apenas uma instância do SSM Backend pode ser executada por vez
"""

import sys
import os
import atexit
from pathlib import Path
from typing import Optional


class SingleInstance:
    """Gerenciador de instância única da aplicação"""

    def __init__(self, lock_id: str = "ssm_backend_single_instance"):
        """
        Inicializar gerenciador de instância única

        Args:
            lock_id: ID único para o lock (mutex ou arquivo)
        """
        self.lock_id = lock_id
        self.lock_handle = None
        self.lock_file_path = None
        self.is_locked = False

    def acquire(self) -> bool:
        """
        Tentar adquirir o lock (permitir apenas uma instância)

        Returns:
            True se conseguiu adquirir o lock (pode executar)
            False se já existe outra instância rodando
        """
        if sys.platform == "win32":
            return self._acquire_windows()
        else:
            return self._acquire_file()

    def _acquire_windows(self) -> bool:
        """Acquire lock usando mutex no Windows (mais robusto)"""
        try:
            import win32event
            import win32api
            import winerror

            # Criar mutex nomeado
            # Se já existe, retorna erro
            mutex_name = f"Global\\{self.lock_id}"
            self.lock_handle = win32event.CreateMutex(None, False, mutex_name)

            last_error = win32api.GetLastError()

            if last_error == winerror.ERROR_ALREADY_EXISTS:
                # Já existe outra instância
                if self.lock_handle:
                    win32api.CloseHandle(self.lock_handle)
                    self.lock_handle = None
                return False

            # Lock adquirido com sucesso
            self.is_locked = True
            # Registrar cleanup ao sair
            atexit.register(self.release)
            return True

        except ImportError:
            # pywin32 não disponível, usar file lock como fallback
            return self._acquire_file()
        except Exception:
            # Em caso de erro, tentar file lock
            return self._acquire_file()

    def _acquire_file(self) -> bool:
        """Acquire lock usando arquivo (fallback para todos os sistemas)"""
        try:
            # Criar diretório de lock se não existir
            lock_dir = Path("data") / "temp"
            lock_dir.mkdir(parents=True, exist_ok=True)

            self.lock_file_path = lock_dir / f"{self.lock_id}.lock"

            # Tentar criar arquivo exclusivo
            # Se já existe, significa que outra instância está rodando
            if self.lock_file_path.exists():
                # Verificar se o processo ainda está ativo (via PID)
                try:
                    pid = int(self.lock_file_path.read_text().strip())
                    if self._is_process_running(pid):
                        return False  # Processo ainda está rodando
                    else:
                        # Processo morreu, remover lock órfão
                        self.lock_file_path.unlink()
                except (ValueError, OSError):
                    # Lock inválido, remover
                    try:
                        self.lock_file_path.unlink()
                    except:
                        pass

            # Criar lock file com PID do processo atual
            self.lock_file_path.write_text(str(os.getpid()))
            self.is_locked = True

            # Registrar cleanup
            atexit.register(self.release)
            return True

        except Exception as e:
            # Em caso de erro, permitir execução (melhor que bloquear)
            print(f"AVISO: Não foi possível criar lock: {e}")
            return True

    def _is_process_running(self, pid: int) -> bool:
        """Verificar se um processo com o PID especificado está rodando"""
        try:
            if sys.platform == "win32":
                # Windows: tentar usar psutil se disponível, senão assumir que está rodando
                try:
                    import psutil

                    return psutil.pid_exists(pid)
                except ImportError:
                    # Se psutil não disponível, verificar via tasklist
                    import subprocess

                    try:
                        result = subprocess.run(
                            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                            capture_output=True,
                            text=True,
                            timeout=2,
                        )
                        return str(pid) in result.stdout
                    except Exception:
                        # Se falhar, assumir que processo ainda existe (conservador)
                        return True
            else:
                # Linux/Unix: enviar sinal 0 para verificar processo
                os.kill(pid, 0)
                return True
        except (OSError, Exception):
            # Processo não existe
            return False

    def release(self):
        """Liberar o lock"""
        if not self.is_locked:
            return

        try:
            if sys.platform == "win32" and self.lock_handle:
                try:
                    import win32api

                    win32api.CloseHandle(self.lock_handle)
                except Exception:
                    pass
                self.lock_handle = None

            if self.lock_file_path and self.lock_file_path.exists():
                try:
                    self.lock_file_path.unlink()
                except Exception:
                    pass
                self.lock_file_path = None

            self.is_locked = False
        except Exception:
            pass

    def check_and_show_message(self) -> bool:
        """
        Verificar se pode executar e mostrar mensagem se já existe instância

        Returns:
            True se pode executar, False se já existe outra instância
        """
        if self.acquire():
            return True

        # Já existe outra instância - mostrar mensagem
        self._show_instance_running_message()
        return False

    def _show_instance_running_message(self):
        """Mostrar mensagem informando que já existe instância rodando"""
        # Tentar restaurar/focar na janela existente (Windows)
        try:
            if sys.platform == "win32":
                try:
                    import win32gui
                    import win32con

                    # Tentar encontrar e focar na janela existente
                    found_window = False

                    def enum_handler(hwnd, ctx):
                        nonlocal found_window
                        if win32gui.IsWindowVisible(hwnd):
                            window_title = win32gui.GetWindowText(hwnd)
                            if "SSM Backend" in window_title or "SSM" in window_title:
                                # Encontrar janela existente - restaurar e focar
                                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                                win32gui.SetForegroundWindow(hwnd)
                                win32gui.BringWindowToTop(hwnd)
                                found_window = True

                    try:
                        win32gui.EnumWindows(enum_handler, None)
                    except Exception:
                        pass
                except ImportError:
                    # pywin32 não disponível, continuar sem focar janela
                    pass
        except:
            pass

        # Tentar mostrar messagebox primeiro (mais visível)
        try:
            import tkinter.messagebox as msgbox
            import tkinter as tk

            root = tk.Tk()
            root.withdraw()  # Esconder janela principal
            root.attributes("-topmost", True)  # Trazer para frente
            msgbox.showwarning(
                "SSM Backend - Instância Duplicada",
                "O SSM Backend já está em execução!\n\n"
                "Uma instância do SSM Backend já está rodando.\n"
                "Por favor, use a janela já aberta.\n\n"
                "A nova janela será fechada.",
            )
            root.destroy()
        except Exception:
            # Se tkinter não disponível, mostrar no console
            try:
                message = (
                    "\n" + "=" * 60 + "\n"
                    "SSM Backend já está em execução!\n\n"
                    "Uma instância do SSM Backend já está rodando.\n"
                    "Por favor, use a janela já aberta.\n"
                    "=" * 60 + "\n"
                )
                print(message)
            except Exception:
                pass


def ensure_single_instance(
    lock_id: str = "ssm_backend_single_instance",
) -> Optional[SingleInstance]:
    """
    Garantir que apenas uma instância está rodando

    Args:
        lock_id: ID único para o lock

    Returns:
        SingleInstance object se pode executar, None se já existe instância
    """
    instance = SingleInstance(lock_id=lock_id)
    if instance.check_and_show_message():
        return instance
    return None
