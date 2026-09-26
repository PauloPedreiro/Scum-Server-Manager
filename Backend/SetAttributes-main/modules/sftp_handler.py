import configparser
import os
import shutil
from datetime import datetime
from .utils import create_local_backup
from .database import process_scum_db

# Verifica se a biblioteca paramiko está instalada.
# Ela é necessária para SFTP, mas não vem com o Python padrão.
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

def run_sftp_mode():
    """
    Controlador para o Modo Remoto SFTP.
    Conecta, baixa, edita e reenvia o banco de dados.
    """
    
    # Se paramiko não estiver instalado, aborta com instruções
    if not PARAMIKO_AVAILABLE:
        print("\n[ERRO] A biblioteca 'paramiko' é necessária para SFTP.")
        print("Instale usando: pip install paramiko")
        return

    # --- FASE 1: CONFIGURAÇÃO ---
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    # Lê defaults do .ini
    cfg_host = config.get('SFTP', 'Host', fallback='')
    cfg_port = config.get('SFTP', 'Port', fallback='22')
    cfg_user = config.get('SFTP', 'User', fallback='')
    cfg_pass = config.get('SFTP', 'Password', fallback='')
    cfg_rem_path = config.get('SFTP', 'RemoteDbPath', fallback='/home/steam/SCUM/Saved/SaveFiles/SCUM.db')

    print("\n--- Conexão SFTP ---")
    host = input(f"IP/Host [{cfg_host}]: ").strip() or cfg_host
    port = input(f"Porta [{cfg_port}]: ").strip() or cfg_port
    user = input(f"Usuário [{cfg_user}]: ").strip() or cfg_user
    # Oculta senha na exibição se já estiver salva
    pass_display = '******' if cfg_pass else ''
    password = input(f"Senha [{pass_display}]: ").strip() or cfg_pass
    
    remote_path = input(f"Caminho remoto do DB [{cfg_rem_path}]: ").strip() or cfg_rem_path



    # Configuração do cliente SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Aceita chaves desconhecidas automaticamente
    
    temp_local_db = "SCUM_temp.db"

    try:
        # --- FASE 2: CONEXÃO ---
        print(f"Conectando a {host}...")
        ssh.connect(hostname=host, port=int(port), username=user, password=password)
        sftp = ssh.open_sftp()
        
        # Verifica se o arquivo existe lá
        try:
            sftp.stat(remote_path)
        except FileNotFoundError:
            print(f"Arquivo não encontrado no servidor: {remote_path}")
            return

        # --- FASE 3: DOWNLOAD ---
        print("Baixando SCUM.db para edição temporária...")
        sftp.get(remote_path, temp_local_db)
        
        # Cria backup LOCAL do arquivo que acabamos de baixar (segurança extra)
        create_local_backup(temp_local_db)
        
        # --- FASE 4: PROCESSAMENTO (Edição) ---
        # Usa a mesma função do modo local no arquivo temporário
        changed = process_scum_db(temp_local_db)
        
        if changed:
            print("\n[UPLOAD] Preparando para enviar alterações...")
            
            # --- FASE 5: BACKUP REMOTO ---
            # Antes de sobrescrever lá no servidor, vamos renomear o original para .bak
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            remote_backup = f"{remote_path}.{timestamp}.bak"
            print(f"Criando backup remoto: {remote_backup}")
            try:
                sftp.rename(remote_path, remote_backup)
            except Exception as e:
                print(f"Erro ao renomear remoto (Backup): {e}")
                # Se falhar o renomear (permissão, etc), pergunta se continua
                confirm = input("Não foi possível criar backup remoto. Sobrescrever mesmo assim? (S/N): ")
                if confirm.lower() != 's':
                    return

            # --- FASE 6: UPLOAD ---
            print("Enviando novo SCUM.db...")
            sftp.put(temp_local_db, remote_path)
            print("[SUCESSO] Upload concluído! Reinicie o servidor.")
        else:
            print("Nenhuma alteração para enviar. O arquivo remoto não foi tocado.")

        sftp.close()
        ssh.close()

    except paramiko.AuthenticationException:
        print("Erro de autenticação (Usuário/Senha incorretos).")
    except Exception as e:
        print(f"Erro na conexão SFTP: {e}")
    finally:
        # Limpeza: remove o arquivo temporário 'SCUM_temp.db' do PC
        if os.path.exists(temp_local_db):
            try:
                os.remove(temp_local_db)
            except:
                pass
