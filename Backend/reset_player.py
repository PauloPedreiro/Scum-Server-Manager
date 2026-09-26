import os
import sys
import sqlite3

def get_db_path():
    db_path = os.path.join("data", "SSM.db")
    if not os.path.exists(db_path):
        print(f"Erro: Banco de dados nao encontrado em: {db_path}")
        sys.exit(1)
    return db_path

def main():
    steam_id = "76561198040636105"
    if len(sys.argv) > 1:
        steam_id = sys.argv[1].strip()
        
    db_path = get_db_path()
    print("==================================================")
    print("      RESETADOR DE CADASTRO E PEDIDOS - SSM       ")
    print("==================================================")
    print(f"SteamID Alvo: {steam_id}")
    print(f"Banco de dados: {db_path}")
    print("==================================================\n")
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 1. Resetar vinculo do discord na tabela players
        cur.execute(
            "UPDATE players SET discord_user_id = NULL, discord_linked_at = NULL WHERE steam_id = ?",
            (steam_id,)
        )
        players_affected = cur.rowcount
        
        # 2. Remover tokens antigos consumidos
        cur.execute(
            "DELETE FROM discord_link_tokens WHERE consumed_by_steam_id = ?",
            (steam_id,)
        )
        tokens_affected = cur.rowcount
        
        # 3. Remover pedidos da loja e itens de entrega
        cur.execute(
            "DELETE FROM shop_order_item WHERE order_id IN (SELECT order_id FROM shop_order WHERE steam_id = ?)",
            (steam_id,)
        )
        order_items_affected = cur.rowcount
        
        cur.execute(
            "DELETE FROM shop_delivery_item WHERE order_id IN (SELECT order_id FROM shop_order WHERE steam_id = ?)",
            (steam_id,)
        )
        delivery_items_affected = cur.rowcount
        
        cur.execute(
            "DELETE FROM shop_order WHERE steam_id = ?",
            (steam_id,)
        )
        orders_affected = cur.rowcount
        
        # 4. Resetar carteira para saldo inicial
        initial_balance = 0
        try:
            config_path = os.path.join("data", "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    economy = config.get("economy")
                    if isinstance(economy, dict):
                        initial_balance = int(economy.get("initial_balance", 0))
        except Exception:
            pass

        cur.execute(
            "UPDATE wallet SET balance = ? WHERE steam_id = ?",
            (initial_balance, steam_id)
        )
        wallet_affected = cur.rowcount
        if wallet_affected == 0:
            # Se não existia carteira, cria com o saldo inicial
            cur.execute(
                "INSERT OR IGNORE INTO wallet(steam_id, balance) VALUES(?, ?)",
                (steam_id, initial_balance)
            )
            wallet_affected = cur.rowcount
            
        conn.commit()
        conn.close()
        
        print(">>> Cadastro resetado com sucesso!")
        print(f"  - Registro do Discord desvinculado (tabela players)")
        print(f"  - Pedidos da Loja removidos: {orders_affected} pedido(s)")
        print(f"  - Tokens antigos limpos: {tokens_affected}")
        print(f"  - Saldo da carteira resetado para: {initial_balance}")
        print("\nAgora o jogador pode usar o comando de registro e receber o kit de boas-vindas novamente!")
        
    except Exception as e:
        print(f"\n[ERRO] Erro ao resetar jogador: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
