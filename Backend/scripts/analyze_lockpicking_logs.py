#!/usr/bin/env python3
"""
Script para analisar logs de gameplay e identificar eventos de lockpicking
Verifica por que falhas não estão sendo registradas
"""

import os
import sys
import re
import sqlite3
from core.database.connector import DatabaseConnector
from pathlib import Path
from datetime import datetime
from collections import Counter

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.path_helper import ConfigPathHelper

def parse_log_line(line):
    """Parsear uma linha de log de minigame"""
    result = {
        'has_logminigame': False,
        'has_lockpicking': False,
        'has_success': None,
        'success_value': None,
        'has_owner': False,
        'owner_info': None,
        'has_location': False,
        'has_target_object': False,
        'line': line
    }
    
    # Verificar se é LogMinigame
    if '[LogMinigame]' not in line:
        return result
    
    result['has_logminigame'] = True
    
    # Verificar se é LockpickingMinigame_C
    if 'LockpickingMinigame_C' in line:
        result['has_lockpicking'] = True
    
    # Verificar Success
    success_match = re.search(r'Success:\s*(Yes|No)', line)
    if success_match:
        result['has_success'] = True
        result['success_value'] = success_match.group(1) == 'Yes'
    else:
        # Tentar variações
        if 'Success:' in line:
            result['has_success'] = True
            result['success_value'] = None  # Formato desconhecido
    
    # Verificar Owner
    owner_match = re.search(r'User owner:\s*(\d+)\s*\(\[(\d+)\]\s*([^)]+)\)', line)
    if owner_match:
        result['has_owner'] = True
        result['owner_info'] = {
            'id': owner_match.group(1),
            'steam_id': owner_match.group(2),
            'name': owner_match.group(3).strip()
        }
    else:
        # Tentar padrão alternativo
        owner_match_alt = re.search(r'User owner:\s*(\d+)\s*\[(\d+)\]\s*([^.\s]+)', line)
        if owner_match_alt:
            result['has_owner'] = True
            result['owner_info'] = {
                'id': owner_match_alt.group(1),
                'steam_id': owner_match_alt.group(2),
                'name': owner_match_alt.group(3).strip()
            }
        elif 'User owner: N/A' in line:
            result['has_owner'] = False
            result['owner_info'] = 'N/A'
    
    # Verificar Location
    location_match = re.search(r'Location:\s*X=([-\d.]+)\s+Y=([-\d.]+)\s+Z=([-\d.]+)', line)
    if location_match:
        result['has_location'] = True
    
    # Verificar Target object
    if 'Target object:' in line:
        result['has_target_object'] = True
    
    return result

def analyze_log_file(log_path):
    """Analisar um arquivo de log"""
    print(f"\n{'='*80}")
    print(f"ANALISANDO: {os.path.basename(log_path)}")
    print(f"{'='*80}")
    
    try:
        # Tentar UTF-16LE primeiro (formato padrão do SCUM)
        try:
            with open(log_path, 'r', encoding='utf-16le', errors='ignore') as f:
                content = f.read()
        except:
            # Tentar UTF-8
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        
        lines = content.split('\n')
        print(f"Total de linhas no arquivo: {len(lines)}")
        
        # Filtrar linhas de LogMinigame
        minigame_lines = [line for line in lines if '[LogMinigame]' in line]
        print(f"Linhas com [LogMinigame]: {len(minigame_lines)}")
        
        # Filtrar linhas de LockpickingMinigame_C
        lockpicking_lines = [line for line in minigame_lines if 'LockpickingMinigame_C' in line]
        print(f"Linhas com LockpickingMinigame_C: {len(lockpicking_lines)}")
        
        if not lockpicking_lines:
            print("\n⚠️  Nenhuma linha de LockpickingMinigame_C encontrada neste arquivo")
            return None
        
        # Analisar cada linha
        parsed_events = []
        stats = {
            'total': 0,
            'with_success_yes': 0,
            'with_success_no': 0,
            'without_success': 0,
            'with_owner': 0,
            'without_owner': 0,
            'with_location': 0,
            'without_location': 0,
            'with_target': 0,
            'without_target': 0,
            'parseable': 0,
            'unparseable': 0
        }
        
        print(f"\n{'='*80}")
        print("ANÁLISE DETALHADA")
        print(f"{'='*80}\n")
        
        for idx, line in enumerate(lockpicking_lines[:50], 1):  # Limitar a 50 para não sobrecarregar
            parsed = parse_log_line(line)
            parsed_events.append(parsed)
            
            stats['total'] += 1
            
            if parsed['has_success']:
                if parsed['success_value'] is True:
                    stats['with_success_yes'] += 1
                elif parsed['success_value'] is False:
                    stats['with_success_no'] += 1
                else:
                    stats['without_success'] += 1
            else:
                stats['without_success'] += 1
            
            if parsed['has_owner']:
                stats['with_owner'] += 1
            else:
                stats['without_owner'] += 1
            
            if parsed['has_location']:
                stats['with_location'] += 1
            else:
                stats['without_location'] += 1
            
            if parsed['has_target_object']:
                stats['with_target'] += 1
            else:
                stats['without_target'] += 1
            
            # Verificar se é "parseable" (tem todos os campos necessários)
            if (parsed['has_lockpicking'] and 
                parsed['has_location'] and 
                'User:' in line and
                parsed['has_success'] is not None):
                stats['parseable'] += 1
            else:
                stats['unparseable'] += 1
        
        # Mostrar estatísticas
        print(f"📊 ESTATÍSTICAS (primeiros {min(50, len(lockpicking_lines))} eventos):")
        print(f"   Total de eventos LockpickingMinigame_C: {stats['total']}")
        print(f"   ✅ Com Success: Yes: {stats['with_success_yes']}")
        print(f"   ❌ Com Success: No: {stats['with_success_no']}")
        print(f"   ⚠️  Sem campo Success: {stats['without_success']}")
        print(f"   👤 Com proprietário: {stats['with_owner']}")
        print(f"   ❓ Sem proprietário: {stats['without_owner']}")
        print(f"   📍 Com coordenadas: {stats['with_location']}")
        print(f"   ❌ Sem coordenadas: {stats['without_location']}")
        print(f"   🎯 Com target object: {stats['with_target']}")
        print(f"   ❌ Sem target object: {stats['without_target']}")
        print(f"   ✅ Parseable (pode ser inserido): {stats['parseable']}")
        print(f"   ❌ Não parseable: {stats['unparseable']}")
        
        # Mostrar exemplos de falhas não parseáveis
        print(f"\n{'='*80}")
        print("EXEMPLOS DE EVENTOS DE FALHA (Success: No)")
        print(f"{'='*80}\n")
        
        failure_examples = [p for p in parsed_events if p.get('success_value') is False]
        if failure_examples:
            for idx, example in enumerate(failure_examples[:5], 1):
                print(f"Exemplo {idx} - Success: No")
                print(f"   Tem proprietário: {example['has_owner']}")
                print(f"   Tem coordenadas: {example['has_location']}")
                print(f"   Parseable: {example['has_location'] and example['has_lockpicking'] and 'User:' in example['line']}")
                print(f"   Linha: {example['line'][:150]}...")
                print()
        else:
            print("⚠️  Nenhum evento de falha encontrado nos primeiros 50 eventos")
        
        # Mostrar eventos sem proprietário
        print(f"\n{'='*80}")
        print("EVENTOS SEM PROPRIETÁRIO (não serão enviados para Discord)")
        print(f"{'='*80}\n")
        
        no_owner = [p for p in parsed_events if not p['has_owner']]
        if no_owner:
            print(f"Total encontrado: {len(no_owner)}")
            for idx, example in enumerate(no_owner[:5], 1):
                success_status = "Yes" if example.get('success_value') else "No" if example.get('success_value') is False else "Unknown"
                print(f"\n   Exemplo {idx} - Success: {success_status}")
                print(f"   Linha: {example['line'][:200]}...")
        else:
            print("✅ Todos os eventos têm proprietário")
        
        return {
            'stats': stats,
            'parsed_events': parsed_events,
            'total_in_file': len(lockpicking_lines)
        }
        
    except Exception as e:
        print(f"❌ ERRO ao analisar arquivo: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_database(db_path):
    """Verificar eventos no banco de dados"""
    print(f"\n{'='*80}")
    print("VERIFICANDO BANCO DE DADOS")
    print(f"{'='*80}\n")
    
    try:
        with DatabaseConnector.get_connection(db_path, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Total de eventos
            cursor.execute("SELECT COUNT(*) FROM minigame_events WHERE minigame_type = 'LockpickingMinigame_C'")
            total = cursor.fetchone()[0]
            print(f"Total de eventos LockpickingMinigame_C no banco: {total}")
            
            # Eventos com sucesso
            cursor.execute("""
                SELECT COUNT(*) FROM minigame_events 
                WHERE minigame_type = 'LockpickingMinigame_C' 
                  AND success = 1
            """)
            success_count = cursor.fetchone()[0]
            print(f"   ✅ Com success = 1 (sucesso): {success_count}")
            
            # Eventos com falha
            cursor.execute("""
                SELECT COUNT(*) FROM minigame_events 
                WHERE minigame_type = 'LockpickingMinigame_C' 
                  AND success = 0
            """)
            fail_count = cursor.fetchone()[0]
            print(f"   ❌ Com success = 0 (falha): {fail_count}")
            
            # Eventos com success NULL
            cursor.execute("""
                SELECT COUNT(*) FROM minigame_events 
                WHERE minigame_type = 'LockpickingMinigame_C' 
                  AND success IS NULL
            """)
            null_count = cursor.fetchone()[0]
            print(f"   ❓ Com success = NULL: {null_count}")
            
            # Eventos com proprietário
            cursor.execute("""
                SELECT COUNT(*) FROM minigame_events 
                WHERE minigame_type = 'LockpickingMinigame_C' 
                  AND owner_id IS NOT NULL
            """)
            with_owner = cursor.fetchone()[0]
            print(f"   👤 Com proprietário: {with_owner}")
            
            # Eventos sem proprietário
            cursor.execute("""
                SELECT COUNT(*) FROM minigame_events 
                WHERE minigame_type = 'LockpickingMinigame_C' 
                  AND owner_id IS NULL
            """)
            without_owner = cursor.fetchone()[0]
            print(f"   ❓ Sem proprietário: {without_owner}")
            
            # Últimos eventos
            print(f"\n📋 ÚLTIMOS 10 EVENTOS NO BANCO:")
            cursor.execute("""
                SELECT 
                    timestamp, player_name, success, owner_name,
                    lock_type, failed_attempts
                FROM minigame_events
                WHERE minigame_type = 'LockpickingMinigame_C'
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                success_str = "✅ Yes" if row['success'] else "❌ No" if row['success'] is False else "❓ NULL"
                owner_str = row['owner_name'] or "Sem proprietário"
                print(f"   [{row['timestamp']}] {row['player_name']} - Success: {success_str} - Owner: {owner_str}")
            
    except Exception as e:
        print(f"❌ ERRO ao verificar banco: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Função principal"""
    print("\n" + "="*80)
    print("🔍 ANÁLISE DE LOGS DE LOCKPICKING")
    print("="*80)
    
    path_helper = ConfigPathHelper()
    logs_directory = path_helper.get_scum_logs_directory()
    db_path = path_helper.get_ssm_db_path()
    
    print(f"\n📁 Caminhos:")
    print(f"   Logs: {logs_directory}")
    print(f"   Banco: {db_path}")
    
    # Encontrar arquivo mais recente
    log_files = list(Path(logs_directory).glob("gameplay_*.log"))
    if not log_files:
        print(f"\n❌ ERRO: Nenhum arquivo gameplay_*.log encontrado em {logs_directory}")
        return
    
    # Ordenar por data de modificação
    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    print(f"\n📄 Arquivo mais recente: {latest_log.name}")
    print(f"   Modificado: {datetime.fromtimestamp(latest_log.stat().st_mtime)}")
    
    # Analisar log
    analysis_result = analyze_log_file(str(latest_log))
    
    # Verificar banco
    if os.path.exists(db_path):
        check_database(db_path)
    else:
        print(f"\n⚠️  Banco de dados não encontrado: {db_path}")
    
    print(f"\n{'='*80}")
    print("ANÁLISE CONCLUÍDA")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
