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
    db_path = get_db_path()
    print("==================================================")
    print("   RESETADOR GERAL DE CADASTRO E PEDIDOS - SSM    ")
    print("==================================================")
    print(f"Banco de dados: {db_path}")
    print("Este script ira desvincular TODOS os jogadores do Discord,")
    print("limpar todos os tokens e apagar todos os pedidos da loja.")
    print("==================================================\n")
    
    confirm = input("Tem certeza que deseja resetar TODOS os registros? (S/N): ").strip().upper()
    if confirm not in ("S", "SIM"):
        print("Operacao cancelada pelo usuario.")
        sys.exit(0)
        
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 1. Resetar vinculo do discord na tabela players para todos
        cur.execute("UPDATE players SET discord_user_id = NULL, discord_linked_at = NULL")
        players_affected = cur.rowcount
        
        # 2. Remover todos os tokens de link do discord
        cur.execute("DELETE FROM discord_link_tokens")
        tokens_affected = cur.rowcount
        
        # 3. Remover todos os itens de pedidos e entregas
        cur.execute("DELETE FROM shop_order_item")
        order_items_affected = cur.rowcount
        
        cur.execute("DELETE FROM shop_delivery_item")
        delivery_items_affected = cur.rowcount
        
        cur.execute("DELETE FROM shop_order")
        orders_affected = cur.rowcount
        
        # 4. Resetar todas as carteiras para saldo inicial
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

        cur.execute("UPDATE wallet SET balance = ?", (initial_balance,))
        wallet_affected = cur.rowcount
        
        conn.commit()
        conn.close()
        
        print("\n>>> TODOS os registros foram resetados com sucesso!")
        print(f"  - Jogadores desvinculados no Discord: {players_affected}")
        print(f"  - Tokens do Discord deletados: {tokens_affected}")
        print(f"  - Pedidos da loja removidos: {orders_affected}")
        print(f"  - Itens de pedido deletados: {order_items_affected}")
        print(f"  - Itens de entrega pendentes deletados: {delivery_items_affected}")
        print(f"  - Carteiras resetadas para: {initial_balance} ({wallet_affected} carteiras)")
        print("\nPronto! Todos os jogadores podem se registrar novamente e o Welcome Pack sera entregue do zero.")
        
    except Exception as e:
        print(f"\n[ERRO] Falha ao resetar banco de dados: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
