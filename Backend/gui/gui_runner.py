"""
Runner da GUI - Interface gráfica sem inicializar backend automaticamente
"""

import sys
import argparse


def run_gui_mode():
    """Executar em modo GUI - interface desktop com SplashScreen integrada"""
    # SEGURANÇA: Verificar se já existe instância rodando
    from utils.single_instance import ensure_single_instance

    instance_lock = ensure_single_instance("ssm_backend_gui")
    if instance_lock is None:
        # Já existe outra instância - sair silenciosamente
        sys.exit(0)

    try:
        from gui.main_window import MainWindow

        window = MainWindow()
        window.mainloop()

        # Liberar lock ao fechar
        if instance_lock:
            instance_lock.release()

    except KeyboardInterrupt:
        # Aplicação encerrada pelo usuário - não precisa de mensagem
        pass
    except Exception as e:
        # Em caso de erro crítico, mostrar mensagem via GUI se possível
        # Se não for possível, usar traceback apenas em modo debug
        if not getattr(sys, "frozen", False):
            # Apenas em modo desenvolvimento mostrar erro no console
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Quando executado diretamente, sempre executar em modo GUI.
    # Porém, em build EXE o entrypoint pode ser este arquivo; então precisamos
    # suportar também o modo CLI do instalador para que o GUI consiga lançar
    # o instalador como um segundo processo.
    parser = argparse.ArgumentParser(description="SSM Backend - Interface Gráfica")
    parser.add_argument(
        "--gui", action="store_true", help="Executar em modo GUI (opcional)"
    )
    parser.add_argument(
        "--install-scum-server",
        action="store_true",
        help="Instalar/atualizar SCUM Server (SteamCMD) e sair",
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default="C:\\Servers",
        help="Diretorio base para instalar (cria steamcmd/ e scum/ dentro)",
    )
    parser.add_argument(
        "--installer-state-dir",
        type=str,
        default="",
        help="Diretorio para estado/logs do instalador (default: ProgramData\\SSM\\installer)",
    )
    args = parser.parse_args()

    if args.install_scum_server:
        from installer.scum_server_installer import run_scum_server_installer

        exit_code = run_scum_server_installer(args.base_dir, args.installer_state_dir)
        sys.exit(exit_code)

    run_gui_mode()
