import configparser
import paramiko
import os
import sys

def debug_sftp():
    if not os.path.exists('config.ini'):
        print("config.ini não encontrado!")
        return

    config = configparser.ConfigParser()
    config.read('config.ini')

    try:
        host = config.get('SFTP', 'Host')
        port = int(config.get('SFTP', 'Port'))
        user = config.get('SFTP', 'User')
        password = config.get('SFTP', 'Password')
        remote_path = config.get('SFTP', 'RemoteDbPath')
    except Exception as e:
        print(f"Erro ao ler config: {e}")
        return

    print(f"--- TESTE DIAGNÓSTICO SFTP ---")
    print(f"Host: {host}:{port}")
    print(f"User: {user}")
    print(f"Remote Path Configurado: {remote_path}")
    print("-" * 30)

    try:
        print(f"1. Tentando conectar SSH/SFTP...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=user, password=password, timeout=10)
        print("   [OK] Conexão SSH estabelecida.")

        sftp = ssh.open_sftp()
        print("   [OK] Canal SFTP aberto.")

        # Teste 1: PWD
        try:
            cwd = sftp.getcwd() or "."
            print(f"\n2. Diretório Atual (PWD): '{cwd}'")
        except:
            print(f"\n2. Não foi possível obter PWD.")

        # Teste 2: Listar Raiz/Atual
        print("\n3. Listando arquivos no diretório atual:")
        try:
            files_root = sftp.listdir(cwd if cwd else ".")
            for f in files_root[:10]: # mostrar apenas os 10 primeiros
                print(f"   - {f}")
            if len(files_root) > 10: print("   ... (e mais)")
        except Exception as e:
            print(f"   [FALHA] Não foi possível listar raiz: {e}")

        # Teste 3: Tentar listar o caminho configurado
        print(f"\n4. Tentando acessar o caminho configurado: '{remote_path}'")
        target_dir = remote_path
        if target_dir.lower().endswith('.db'):
            target_dir = os.path.dirname(target_dir)
            print(f"   (Ajustado para pasta pai: '{target_dir}')")
        
        if not target_dir: target_dir = "."

        try:
            files_target = sftp.listdir(target_dir)
            print(f"   [OK] Sucesso! Encontrados {len(files_target)} arquivos.")
            found_db = False
            for f in files_target:
                if f.lower().endswith('.db'):
                    print(f"   -> ENCONTRADO DB: {f}")
                    found_db = True
            
            if not found_db:
                print("   [AVISO] Nenhum .db encontrado nesta pasta.")
        except FileNotFoundError:
            print("   [ERRO] Caminho não encontrado (FileNotFoundError). Verifique se a pasta existe.")
        except Exception as e:
            print(f"   [ERRO] {e}")

        sftp.close()
        ssh.close()

    except paramiko.AuthenticationException:
        print("\n[ERRO FATAL] Falha de Autenticação (Senha/User incorretos).")
    except Exception as e:
        print(f"\n[ERRO FATAL] Falha na conexão: {e}")

if __name__ == "__main__":
    debug_sftp()
