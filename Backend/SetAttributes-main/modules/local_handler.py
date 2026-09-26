import configparser
import os
from .utils import create_local_backup
from .database import process_scum_db

def run_local_mode():
    """
    Controlador para o Modo Local de edição.
    1. Lê a configuração padrão do arquivo config.ini.
    2. Pede confirmação ou novo caminho do arquivo DB.
    3. Cria um backup local antes de tocar no arquivo.
    4. Chama a função process_scum_db para realizar a edição.
    """
    
    # Inicializa o parser de configuração
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    # Tenta ler o caminho salvo, ou usa um padrão fixo se não existir
    default_path = config.get('LOCAL', 'DbPath', fallback=r'C:\Servers\scum\SCUM\Saved\SaveFiles\SCUM.db')
    
    # Input do usuário (Pressionar Enter aceita o padrão)
    path = input(f"Caminho do DB [{default_path}]: ").strip() or default_path
    
    # Verificação básica de existência do arquivo
    if not os.path.exists(path):
        print("Arquivo não encontrado. Verifique o caminho.")
        return

    # Passo crucial: BACKUP
    if not create_local_backup(path):
        print("Abortando para evitar perda de dados (Backup falhou).")
        return

    # Executa a edição
    process_scum_db(path)
