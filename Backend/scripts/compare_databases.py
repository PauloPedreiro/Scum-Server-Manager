"""Script para comparar dois bancos de dados SQLite"""

import sqlite3
from pathlib import Path
from typing import Dict, Set, List, Tuple


def get_tables(db_path: str) -> Set[str]:
    """Obter todas as tabelas de um banco"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%' 
        ORDER BY name
    """
    )
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()
    return tables


def get_table_columns(
    db_path: str, table_name: str
) -> List[Tuple[str, str, int, str, int, int]]:
    """Obter informações das colunas de uma tabela"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    conn.close()
    return columns


def get_table_schema(db_path: str, table_name: str) -> str:
    """Obter CREATE TABLE statement de uma tabela"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def compare_databases(old_db: str, new_db: str):
    """Comparar dois bancos de dados"""
    print("=" * 80)
    print("COMPARAÇÃO DE BANCOS DE DADOS")
    print("=" * 80)
    print(f"\nBanco Antigo: {old_db}")
    print(f"Banco Novo:   {new_db}\n")

    # Verificar se arquivos existem
    if not Path(old_db).exists():
        print(f"❌ ERRO: Banco antigo não encontrado: {old_db}")
        return
    if not Path(new_db).exists():
        print(f"❌ ERRO: Banco novo não encontrado: {new_db}")
        return

    # Obter tabelas de cada banco
    old_tables = get_tables(old_db)
    new_tables = get_tables(new_db)

    print(f"RESUMO:")
    print(f"   Banco Antigo: {len(old_tables)} tabelas")
    print(f"   Banco Novo:   {len(new_tables)} tabelas")
    print()

    # Tabelas que existem em ambos
    common_tables = old_tables & new_tables
    # Tabelas apenas no antigo
    only_old = old_tables - new_tables
    # Tabelas apenas no novo
    only_new = new_tables - old_tables

    print("=" * 80)
    print("1. COMPARACAO DE TABELAS")
    print("=" * 80)

    if only_old:
        print(f"\n[TABELAS APENAS NO BANCO ANTIGO] ({len(only_old)}):")
        for table in sorted(only_old):
            print(f"   - {table}")

    if only_new:
        print(f"\n[TABELAS APENAS NO BANCO NOVO] ({len(only_new)}):")
        for table in sorted(only_new):
            print(f"   - {table}")

    if not only_old and not only_new:
        print("\n[OK] Todas as tabelas existem em ambos os bancos!")

    print(f"\nTABELAS COMUNS: {len(common_tables)}")

    # Comparar colunas de cada tabela comum
    print("\n" + "=" * 80)
    print("2. COMPARACAO DE COLUNAS POR TABELA")
    print("=" * 80)

    differences_found = False

    for table in sorted(common_tables):
        old_cols = get_table_columns(old_db, table)
        new_cols = get_table_columns(new_db, table)

        old_col_names = {col[1] for col in old_cols}
        new_col_names = {col[1] for col in new_cols}

        # Colunas apenas no antigo
        only_old_cols = old_col_names - new_col_names
        # Colunas apenas no novo
        only_new_cols = new_col_names - old_col_names
        # Colunas comuns
        common_cols = old_col_names & new_col_names

        if only_old_cols or only_new_cols:
            differences_found = True
            print(f"\n[TABELA] {table}")
            print(f"   Colunas no antigo: {len(old_col_names)}")
            print(f"   Colunas no novo:   {len(new_col_names)}")

            if only_old_cols:
                print(f"   [COLUNAS APENAS NO ANTIGO] ({len(only_old_cols)}):")
                for col in sorted(only_old_cols):
                    # Encontrar detalhes da coluna
                    col_info = next((c for c in old_cols if c[1] == col), None)
                    if col_info:
                        col_type = col_info[2]
                        not_null = "NOT NULL" if col_info[3] else ""
                        default = f" DEFAULT {col_info[4]}" if col_info[4] else ""
                        print(f"      - {col} ({col_type}){not_null}{default}")

            if only_new_cols:
                print(f"   [COLUNAS APENAS NO NOVO] ({len(only_new_cols)}):")
                for col in sorted(only_new_cols):
                    # Encontrar detalhes da coluna
                    col_info = next((c for c in new_cols if c[1] == col), None)
                    if col_info:
                        col_type = col_info[2]
                        not_null = "NOT NULL" if col_info[3] else ""
                        default = f" DEFAULT {col_info[4]}" if col_info[4] else ""
                        print(f"      - {col} ({col_type}){not_null}{default}")

            # Verificar diferenças em tipos de dados
            type_differences = []
            for col_name in common_cols:
                old_col = next((c for c in old_cols if c[1] == col_name), None)
                new_col = next((c for c in new_cols if c[1] == col_name), None)
                if old_col and new_col:
                    if old_col[2] != new_col[2]:  # Tipo diferente
                        type_differences.append((col_name, old_col[2], new_col[2]))
                    elif old_col[3] != new_col[3]:  # NOT NULL diferente
                        type_differences.append(
                            (
                                col_name,
                                f"NOT NULL={old_col[3]}",
                                f"NOT NULL={new_col[3]}",
                            )
                        )
                    elif old_col[4] != new_col[4]:  # DEFAULT diferente
                        type_differences.append(
                            (col_name, f"DEFAULT={old_col[4]}", f"DEFAULT={new_col[4]}")
                        )

            if type_differences:
                print(
                    f"   [DIFERENCAS EM TIPOS/CONSTRAINTS] ({len(type_differences)}):"
                )
                for col_name, old_val, new_val in type_differences:
                    print(f"      - {col_name}: antigo={old_val}, novo={new_val}")

    if not differences_found:
        print("\n[OK] Todas as tabelas comuns tem as mesmas colunas!")

    # Resumo final
    print("\n" + "=" * 80)
    print("3. RESUMO FINAL")
    print("=" * 80)

    total_old_cols = sum(len(get_table_columns(old_db, t)) for t in old_tables)
    total_new_cols = sum(len(get_table_columns(new_db, t)) for t in new_tables)

    print(f"\nESTATISTICAS:")
    print(f"   Tabelas no antigo: {len(old_tables)}")
    print(f"   Tabelas no novo:   {len(new_tables)}")
    print(f"   Total colunas antigo: {total_old_cols}")
    print(f"   Total colunas novo:   {total_new_cols}")

    if len(old_tables) == len(new_tables) and not only_old and not only_new:
        if not differences_found:
            print("\n[OK] BANCOS IDENTICOS EM ESTRUTURA!")
        else:
            print("\n[AVISO] BANCOS TEM MESMAS TABELAS, MAS DIFERENCAS NAS COLUNAS")
    else:
        print("\n[AVISO] BANCOS TEM DIFERENCAS NAS TABELAS")


if __name__ == "__main__":
    old_db = "data/Old_SSM.db"
    new_db = "data/SSM.db"
    compare_databases(old_db, new_db)
