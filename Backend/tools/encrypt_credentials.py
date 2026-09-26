"""
Script para criptografar credenciais no config.json
Uso: python tools/encrypt_credentials.py
"""

import sys
import json
from pathlib import Path

# Adicionar raiz do projeto ao path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from core.security.credential_encryption import encrypt_credential
    from utils.logger import StructuredLogger
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Certifique-se de estar executando do diretório raiz do projeto")
    sys.exit(1)


def encrypt_config_credentials():
    """Criptografa credenciais no config.json"""

    logger = StructuredLogger()
    config_path = ROOT_DIR / "data" / "config.json"

    if not config_path.exists():
        print(f"[-] Arquivo config.json nao encontrado: {config_path}")
        sys.exit(1)

    print("[*] Criptografando credenciais no config.json...")
    print(f"[*] Arquivo: {config_path}")

    try:
        # Carregar config
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        modified = False

        # Criptografar gestao_api_key
        if "licensing" in config:
            licensing = config["licensing"]
            if "gestao_api_key" in licensing:
                api_key = licensing["gestao_api_key"]
                if api_key and not api_key.startswith("ENCRYPTED:"):
                    print(f"  [*] Criptografando gestao_api_key...")
                    encrypted = encrypt_credential(api_key, logger=logger)
                    licensing["gestao_api_key"] = encrypted
                    modified = True
                    print(f"  [+] gestao_api_key criptografada")
                else:
                    print(f"  [-] gestao_api_key ja esta criptografada ou vazia")

        # steam.api_key não é mais necessário (usamos Steam Community XML API pública)
        # Removido da lista de campos a criptografar

        # Criptografar JWT secret
        if "auth" in config:
            auth = config["auth"]
            if "jwt_secret" in auth:
                jwt_secret = auth["jwt_secret"]
                if jwt_secret and not jwt_secret.startswith("ENCRYPTED:"):
                    print(f"  [*] Criptografando auth.jwt_secret...")
                    encrypted = encrypt_credential(jwt_secret, logger=logger)
                    auth["jwt_secret"] = encrypted
                    modified = True
                    print(f"  [+] auth.jwt_secret criptografado")
                else:
                    print(f"  [-] auth.jwt_secret ja esta criptografado ou vazio")

        if modified:
            # Fazer backup
            backup_path = config_path.with_suffix(".json.backup")
            if backup_path.exists():
                backup_path.unlink()
            config_path.rename(backup_path)
            print(f"  [+] Backup criado: {backup_path}")

            # Salvar config criptografado
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print("\n[+] Credenciais criptografadas com sucesso!")
            print(f"[+] Backup salvo em: {backup_path}")
            print("\n[!] IMPORTANTE:")
            print("   - As credenciais agora estao criptografadas")
            print("   - Elas so funcionam nesta maquina (chave derivada do hardware)")
            print("   - Nao copie o config.json para outra maquina")
        else:
            print("\n[-] Nenhuma credencial precisa ser criptografada")
            print("   (Todas ja estao criptografadas ou vazias)")

    except Exception as e:
        print(f"\n[-] Erro ao criptografar credenciais: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    encrypt_config_credentials()
