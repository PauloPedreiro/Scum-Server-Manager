#!/usr/bin/env python3
"""
Script para adicionar a coluna total_fame na tabela rankings
Execute este script para aplicar a migração manualmente
"""

import sqlite3
from core.database.connector import DatabaseConnector
import os
import sys


def get_ssm_db_path():
    """Obter caminho do SSM.db"""
    # Tentar encontrar o banco em locais comuns
    possible_paths = [
        "data/SSM.db",
        "../data/SSM.db",
        "../../data/SSM.db",
        os.path.join(os.path.dirname(__file__), "..", "data", "SSM.db"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return os.path.abspath(path)

    # Se não encontrar, pedir ao usuário
    print("Banco SSM.db não encontrado nos locais padrão.")
    db_path = input("Digite o caminho completo para o arquivo SSM.db: ").strip()

    if not os.path.exists(db_path):
        print(f"Erro: Arquivo não encontrado: {db_path}")
        sys.exit(1)

    return db_path


def check_column_exists(cursor, table_name, column_name):
    """Verificar se uma coluna existe na tabela"""
    cursor.execute("PRAGMA table_info({})".format(table_name))
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns


def apply_migration(db_path):
    """Aplicar migração para adicionar coluna total_fame"""
    print(f"Conectando ao banco: {db_path}")

    try:
        with DatabaseConnector.get_connection(db_path, write_mode=True) as conn:
            cursor = conn.cursor()

            # Verificar se a tabela rankings existe
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='rankings'"
            )
            if not cursor.fetchone():
                print("Erro: Tabela 'rankings' não encontrada no banco!")
                sys.exit(1)

            # Verificar se a coluna já existe
            if check_column_exists(cursor, "rankings", "total_fame"):
                print("✓ Coluna 'total_fame' já existe na tabela rankings")

                # Verificar se há valores
                cursor.execute("SELECT COUNT(*) FROM rankings WHERE total_fame > 0")
                count = cursor.fetchone()[0]
                print(f"  {count} registros com total_fame > 0")

                response = (
                    input("Deseja atualizar os valores existentes? (s/n): ")
                    .strip()
                    .lower()
                )
                if response == "s":
                    update_existing_values(cursor, conn)

                return

            print("Adicionando coluna 'total_fame' na tabela rankings...")

            # Adicionar coluna
            cursor.execute(
                "ALTER TABLE rankings ADD COLUMN total_fame REAL DEFAULT 0.0"
            )
            print("✓ Coluna adicionada com sucesso")

            # Criar índice
            print("Criando índice para ordenação rápida...")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_rankings_total_fame ON rankings(total_fame DESC)"
            )
            print("✓ Índice criado com sucesso")

            # Verificar se a tabela player_fame_totals existe
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='player_fame_totals'"
            )
            if cursor.fetchone():
                print(
                    "Atualizando valores existentes com dados de player_fame_totals..."
                )
                update_existing_values(cursor, conn)
            else:
                print(
                    "⚠ Tabela 'player_fame_totals' não encontrada. Valores serão 0.0 até a próxima atualização."
                )

            conn.commit()
            print("\n✓ Migração aplicada com sucesso!")
            print(
                "  A coluna 'total_fame' foi adicionada e os valores foram atualizados."
            )

    except sqlite3.Error as e:
        print(f"Erro SQLite: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {e}")
        sys.exit(1)


def update_existing_values(cursor, conn):
    """Atualizar valores existentes com dados de player_fame_totals"""
    try:
        cursor.execute(
            """
            UPDATE rankings
            SET total_fame = (
                SELECT COALESCE(total_fame, 0.0)
                FROM player_fame_totals
                WHERE player_fame_totals.steam_id = rankings.steam_id
            )
            WHERE EXISTS (
                SELECT 1
                FROM player_fame_totals
                WHERE player_fame_totals.steam_id = rankings.steam_id
            )
        """
        )
        updated_count = cursor.rowcount
        conn.commit()
        print(
            f"✓ {updated_count} registros atualizados com valores de player_fame_totals"
        )
    except sqlite3.OperationalError as e:
        print(f"⚠ Erro ao atualizar valores: {e}")
        print("  A coluna foi adicionada, mas os valores não puderam ser atualizados.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migração: Adicionar coluna total_fame na tabela rankings")
    print("=" * 60)
    print()

    db_path = get_ssm_db_path()
    print()

    apply_migration(db_path)

    print()
    print("=" * 60)
    print("Migração concluída!")
    print("=" * 60)
