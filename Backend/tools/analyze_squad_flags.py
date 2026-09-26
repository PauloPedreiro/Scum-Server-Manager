"""Script para analisar flags por squad no SCUM.db"""

import sqlite3
import os
import sys
import json
from collections import defaultdict

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_path_helper import ConfigPathHelper
from utils.scum_db_helper import scum_db_readonly_connection

def analyze_squad_flags():
    """Analisar flags por squad no SCUM.db"""
    
    # Carregar config.json
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "config.json")
    if not os.path.exists(config_path):
        print(f"[ERRO] config.json nao encontrado em: {config_path}")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Obter caminho do SCUM.db
    path_helper = ConfigPathHelper(config)
    scum_db_path = path_helper.get_scum_db_path()
    
    if not os.path.exists(scum_db_path):
        print(f"[ERRO] SCUM.db nao encontrado em: {scum_db_path}")
        return
    
    print("="*70)
    print("ANALISE DE FLAGS POR SQUAD")
    print("="*70)
    print(f"\nBanco de dados: {scum_db_path}\n")
    
    if not os.path.exists(scum_db_path):
        print(f"[ERRO] SCUM.db nao encontrado em: {scum_db_path}")
        print(f"\nVerifique se o caminho esta correto no config.json")
        return
    
    # Tentar usar cópia compartilhada, mas se falhar, usar conexão direta para análise
    conn = None
    try:
        with scum_db_readonly_connection(scum_db_path) as conn:
            analyze_connection(conn, scum_db_path)
    except RuntimeError as e:
        # Se falhar com cópia compartilhada, tentar conexão direta para análise
        print(f"[AVISO] Nao foi possivel usar copia compartilhada: {e}")
        print(f"[AVISO] Tentando conexao direta para analise...\n")
        conn = sqlite3.connect(scum_db_path, timeout=10.0)
        conn.execute("PRAGMA read_uncommitted=1")
        analyze_connection(conn, scum_db_path)
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def analyze_connection(conn, scum_db_path):
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. Buscar todas as flags com seus squads
            print("[1] Buscando flags e seus squads...")
            cursor.execute("""
                SELECT 
                    bef.element_id AS flag_id,
                    be.owner_profile_id,
                    sm.squad_id,
                    s.name AS squad_name,
                    s.id AS squad_id_scum
                FROM base_element_flag bef
                JOIN base_element be ON be.element_id = bef.element_id
                LEFT JOIN squad_member sm ON sm.user_profile_id = be.owner_profile_id
                LEFT JOIN squad s ON s.id = sm.squad_id
                WHERE sm.squad_id IS NOT NULL
                ORDER BY sm.squad_id, bef.element_id
            """)
            
            rows = cursor.fetchall()
            
            # Agrupar flags por squad
            squad_flags = defaultdict(list)
            squad_names = {}
            
            for row in rows:
                squad_id = row['squad_id']
                flag_id = row['flag_id']
                squad_name = row['squad_name'] or f"Squad {squad_id}"
                
                if squad_id:
                    squad_flags[squad_id].append(flag_id)
                    squad_names[squad_id] = squad_name
            
            # 2. Estatísticas gerais
            print(f"\n[2] ESTATISTICAS GERAIS:")
            print(f"   - Total de squads com flags: {len(squad_flags)}")
            print(f"   - Total de flags: {sum(len(flags) for flags in squad_flags.values())}")
            
            # 3. Distribuição de flags por squad
            print(f"\n[3] DISTRIBUICAO DE FLAGS POR SQUAD:")
            flag_counts = [(squad_id, len(flags)) for squad_id, flags in squad_flags.items()]
            flag_counts.sort(key=lambda x: x[1], reverse=True)
            
            print(f"\n   Top 10 squads com mais flags:")
            for i, (squad_id, count) in enumerate(flag_counts[:10], 1):
                squad_name = squad_names.get(squad_id, f"Squad {squad_id}")
                print(f"   {i:2d}. Squad {squad_id:3d} ({squad_name[:30]:30s}): {count:3d} flags")
            
            # 4. Exemplos de dados
            print(f"\n[4] EXEMPLOS DE DADOS:")
            print(f"\n   Exemplo 1 - Squad com mais flags:")
            if flag_counts:
                squad_id, count = flag_counts[0]
                flags = squad_flags[squad_id]
                squad_name = squad_names.get(squad_id, f"Squad {squad_id}")
                flags_str = ",".join(str(f) for f in flags[:10])  # Primeiros 10
                if len(flags) > 10:
                    flags_str += f",... (+{len(flags)-10} mais)"
                
                print(f"   Squad ID: {squad_id}")
                print(f"   Nome: {squad_name}")
                print(f"   Total de flags: {count}")
                print(f"   IDs das flags: {flags_str}")
                print(f"   Tamanho da string (todos IDs): {len(','.join(str(f) for f in flags))} caracteres")
            
            # 5. Análise de tamanho
            print(f"\n[5] ANALISE DE TAMANHO:")
            all_flag_strings = []
            for squad_id, flags in squad_flags.items():
                flags_str = ",".join(str(f) for f in flags)
                all_flag_strings.append((squad_id, len(flags_str), len(flags)))
            
            all_flag_strings.sort(key=lambda x: x[1], reverse=True)
            
            print(f"\n   Maior string de IDs:")
            if all_flag_strings:
                squad_id, str_len, flag_count = all_flag_strings[0]
                squad_name = squad_names.get(squad_id, f"Squad {squad_id}")
                print(f"   Squad {squad_id} ({squad_name[:30]}): {str_len} caracteres ({flag_count} flags)")
            
            print(f"\n   Media de caracteres por squad: {sum(x[1] for x in all_flag_strings) / len(all_flag_strings) if all_flag_strings else 0:.1f}")
            print(f"   Maximo de caracteres: {max(x[1] for x in all_flag_strings) if all_flag_strings else 0}")
            
            # 6. Verificar se há squads sem flags
            cursor.execute("SELECT COUNT(*) as total FROM squad")
            total_squads = cursor.fetchone()['total']
            squads_with_flags = len(squad_flags)
            squads_without_flags = total_squads - squads_with_flags
            
            print(f"\n[6] SQUADS SEM FLAGS:")
            print(f"   Total de squads: {total_squads}")
            print(f"   Squads com flags: {squads_with_flags}")
            print(f"   Squads sem flags: {squads_without_flags}")
            
            # 7. Exemplo completo de um squad
            print(f"\n[7] EXEMPLO COMPLETO - Squad com flags:")
            if flag_counts:
                squad_id, count = flag_counts[0]
                flags = squad_flags[squad_id]
                squad_name = squad_names.get(squad_id, f"Squad {squad_id}")
                flags_str = ",".join(str(f) for f in flags)
                
                print(f"\n   Squad ID: {squad_id}")
                print(f"   Nome: {squad_name}")
                print(f"   Quantidade de flags: {count}")
                print(f"   String completa de IDs: {flags_str}")
                print(f"   Tamanho: {len(flags_str)} caracteres")
                print(f"   Primeiros 5 IDs: {flags[:5]}")
                print(f"   Ultimos 5 IDs: {flags[-5:]}")
            
            print("\n" + "="*70)
            print("RESUMO PARA IMPLEMENTACAO:")
            print("="*70)
            print(f"\n[RECOMENDACAO]")
            print(f"   - Tipo de coluna: TEXT (SQLite suporta strings longas)")
            print(f"   - Formato: IDs separados por virgula (ex: '123,456,789')")
            print(f"   - Tamanho maximo estimado: {max(x[1] for x in all_flag_strings) if all_flag_strings else 0} caracteres")
            print(f"   - Squads afetados: {squads_with_flags} de {total_squads} total")
            print(f"\n   VANTAGENS:")
            print(f"   + Simples de implementar")
            print(f"   + Nao cria novas linhas ou colunas adicionais")
            print(f"   + Facil de consultar (LIKE ou split)")
            print(f"\n   DESVANTAGENS:")
            print(f"   - Nao e normalizado (viola 1NF)")
            print(f"   - Busca por flag especifica requer LIKE ou split")
            print(f"   - Dificulta JOINs com tabela de flags")
            print(f"   - Tamanho pode crescer muito se squad tiver muitas flags")

if __name__ == "__main__":
    try:
        analyze_squad_flags()
    except Exception as e:
        print(f"[ERRO] Erro ao analisar flags: {e}")
        import traceback
        traceback.print_exc()
