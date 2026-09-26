from modules.local_handler import run_local_mode
from modules.sftp_handler import run_sftp_mode

def main():
    """
    Função principal que serve como ponto de entrada do programa.
    Exibe o menu inicial e redireciona o usuário para o módulo escolhido (Local ou Remoto).
    """
    print("=== SCUM Attribute Editor v3.0 (Modular) ===")
    print("=== Dev: Nereu Jr ===")
    print("1. Modo Local (Arquivo no PC)")
    print("2. Modo Remoto (SFTP/SSH)")
    print("0. Sair")
    
    # Captura a opção do usuário e remove espaços em branco extras
    opt = input("\nEscolha uma opção: ").strip()
    
    if opt == '1':
        # Executa o módulo de edição local
        run_local_mode()
    elif opt == '2':
        # Executa o módulo de edição remota via SFTP
        run_sftp_mode()
    elif opt == '0':
        print("Saindo.")
    else:
        print("Opção inválida.")
    
    # Pausa para que o usuário possa ler as mensagens finais antes de fechar a janela
    input("\nPressione Enter para fechar...")

if __name__ == "__main__":
    # Garante que o main() só rode se o arquivo for executado diretamente,
    # e não se for importado por outro script.
    main()
