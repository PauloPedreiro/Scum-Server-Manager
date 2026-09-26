import struct
import os
import shutil
from datetime import datetime

def double_to_hex(value):
    """
    Converte um número decimal (float) para a representação binária de 8 bytes
    usada pela Unreal Engine 4 (Double Precision IEEE 754 Little Endian).
    
    Args:
        value (float): O valor numérico (ex: 5.0).
        
    Returns:
        bytes: Sequência de bytes pronta para ser escrita no arquivo binário.
    """
    return struct.pack('<d', float(value))

def get_valid_float(prompt, min_val=0.0, max_val=10.0):
    """
    Solicita input do usuário, valida se é um número, e se está dentro do intervalo seguro.
    
    Args:
        prompt (str): A mensagem para exibir ao usuário.
        min_val (float): Valor mínimo aceitável.
        max_val (float): Valor máximo aceitável.
        
    Returns:
        float: O valor validado.
    """
    while True:
        # Troca vírgula por ponto para aceitar padrão brasileiro (ex: 3,5 -> 3.5)
        val_str = input(prompt).replace(',', '.')
        try:
            val = float(val_str)
            
            # Verifica se está no range recomendado
            if min_val <= val <= max_val:
                return val
            else:
                # Se estiver fora (ex: Força 100), avisa mas permite continuar se o usuário quiser arriscar
                input_conf = input(f"[AVISO] Valor fora do recomendado ({min_val}-{max_val}). Continuar mesmo assim? (S/N): ")
                if input_conf.lower().startswith('s'):
                    return val
        except ValueError:
            print("Entrada inválida. Digite um número (ex: 3.5).")

def create_local_backup(file_path, custom_name=None):
    """
    Cria uma cópia de segurança do arquivo especificado.
    O backup é salvo em uma pasta 'Backups' NA RAIZ DO SCRIPT.
    
    Args:
        file_path (str): Caminho absoluto do arquivo a ser backupeado.
        custom_name (str): Nome opcional para o arquivo de backup (sem extensão .bak).
        
    Returns:
        bool: True se sucesso, False se falha.
    """
    try:
        # Pega o diretório atual de execução do script (Raiz do projeto)
        script_root = os.getcwd()
        
        # Define pasta de backups centralizada
        backup_dir = os.path.join(script_root, "Backups")
        
        # Cria a pasta se não existir
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            print(f"[INFO] Pasta de Backups criada em: {backup_dir}")
            
        if custom_name:
            filename = custom_name
        else:
            filename = os.path.basename(file_path)

        # Organização: Cria uma subpasta para cada arquivo (ex: Backups/SCUMTeste.db/)
        backup_subdir = os.path.join(backup_dir, filename)
        
        # Cria a subpasta se não existir
        if not os.path.exists(backup_subdir):
            os.makedirs(backup_subdir)
            
        # Gera nome com data/hora
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_subdir, f"{filename}.{timestamp}.bak")
        
        # Faz a cópia
        shutil.copy2(file_path, backup_path)
        print(f"[BACKUP] Salvo em: {backup_path}")
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao criar backup: {e}")
        return False

def check_db_lock(file_path):
    """
    Verifica se o arquivo de banco de dados está bloqueado por outro processo.
    Tenta abrir o arquivo para escrita exclusiva.
    Retorna True se estiver bloqueado, False caso contrário.
    """
    if not os.path.exists(file_path):
         return False

    try:
        # Tenta renomear o arquivo para ele mesmo.
        # No Windows, isso falha se o arquivo estiver aberto por outro processo.
        # Alternativamente, tentar abrir com 'r+' também pode funcionar, mas rename é um teste de lock robusto.
        # Porém, renomear pode ser perigoso se falhar no meio (embora rename para mesmo nome seja seguro atomicamente ou falhe).
        # Vamos usar open com 'r+' (read/write). Se falhar permissão, está lockado.
        
        with open(file_path, 'r+') as f:
            pass
        return False
    except IOError:
        return True
