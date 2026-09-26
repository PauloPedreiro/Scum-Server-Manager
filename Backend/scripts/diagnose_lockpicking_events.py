#!/usr/bin/env python3
"""
Script de Diagnóstico para Eventos de Lockpicking
Analisa possíveis problemas no fluxo de registro de eventos
"""

import os
import sys
import sqlite3
from core.database.connector import DatabaseConnector
import json
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logs.gameplay_parser import GameplayLogParser
from core.logs.temp_file_manager import TempFileManager
from core.logs.minigame_notifier import MinigameNotifier
from utils.path_helper import ConfigPathHelper

def check_database_structure(db_path: str):
    """Verificar estrutura da tabela minigame_events"""
    print("\n" + "="*60)
    print("1. VERIFICANDO ESTRUTURA DO BANCO DE DADOS")
    print("="*60)
    
    try:
        with DatabaseConnector.get_connection(db_path, write_mode=True) as conn:
            cursor = conn.cursor()
            
            # Verificar se a tabela existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='minigame_events'
            """)
            if not cursor.fetchone():
                print("❌ ERRO: Tabela minigame_events não existe!")
                return False
            
            print("✅ Tabela minigame_events existe")
            
            # Verificar colunas
            cursor.execute("PRAGMA table_info(minigame_events)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            required_columns = [
                'id', 'log_line', 'timestamp', 'minigame_type',
                'steam_id', 'player_id', 'player_name',
                'success', 'elapsed_time', 'failed_attempts',
                'target_object', 'target_object_id', 'lock_type',
                'owner_id', 'owner_steam_id', 'owner_name',
                'is_property_invasion', 'location_x', 'location_y',
                'location_z', 'log_file', 'discord_sent'
            ]
            
            missing = []
            for col in required_columns:
                if col not in columns:
                    missing.append(col)
            
            if missing:
                print(f"❌ ERRO: Colunas faltando: {', '.join(missing)}")
                return False
            
            print(f"✅ Todas as {len(required_columns)} colunas necessárias existem")
            
            # Verificar índices
            cursor.execute("PRAGMA index_list('minigame_events')")
            indexes = [row[1] for row in cursor.fetchall()]
            print(f"ℹ️  Índices encontrados: {len(indexes)}")
            
            # Verificar foreign key constraints
            cursor.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]
            print(f"ℹ️  Foreign Keys: {'Habilitado' if fk_enabled else 'Desabilitado'}")
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM minigame_events")
            total = cursor.fetchone()[0]
            print(f"ℹ️  Total de registros: {total}")
            
            # Contar registros com proprietário
            cursor.execute("""
                SELECT COUNT(*) FROM minigame_events 
                WHERE owner_id IS NOT NULL 
                  AND owner_steam_id IS NOT NULL 
                  AND owner_name IS NOT NULL
            """)
            with_owner = cursor.fetchone()[0]
            print(f"ℹ️  Registros com proprietário: {with_owner}")
            
            # Contar enviados para Discord
            cursor.execute("SELECT COUNT(*) FROM minigame_events WHERE discord_sent = 1")
            sent = cursor.fetchone()[0]
            print(f"ℹ️  Registros enviados para Discord: {sent}")
            
            # Contar não enviados mas com proprietário
            cursor.execute("""
                SELECT COUNT(*) FROM minigame_events 
                WHERE discord_sent = 0
                  AND owner_id IS NOT NULL 
                  AND owner_steam_id IS NOT NULL 
                  AND owner_name IS NOT NULL
                  AND minigame_type = 'LockpickingMinigame_C'
            """)
            pending = cursor.fetchone()[0]
            print(f"ℹ️  Pendentes de envio: {pending}")
            
            return True
            
    except Exception as e:
        print(f"❌ ERRO ao verificar banco: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_webhook_config(webhooks_path: str):
    """Verificar configuração do webhook"""
    print("\n" + "="*60)
    print("2. VERIFICANDO CONFIGURAÇÃO DO WEBHOOK")
    print("="*60)
    
    try:
        if not os.path.exists(webhooks_path):
            print(f"❌ ERRO: Arquivo {webhooks_path} não existe!")
            return False
        
        with open(webhooks_path, 'r', encoding='utf-8') as f:
            webhooks = json.load(f)
        
        lockpicking_webhook = webhooks.get('lockpicking_events')
        
        if not lockpicking_webhook:
            print("❌ ERRO: Webhook 'lockpicking_events' não configurado!")
            return False
        
        if lockpicking_webhook.strip() == "":
            print("❌ ERRO: Webhook 'lockpicking_events' está vazio!")
            return False
        
        print(f"✅ Webhook configurado: {lockpicking_webhook[:50]}...")
        
        # Tentar inicializar MinigameNotifier
        try:
            notifier = MinigameNotifier(webhooks_path)
            if notifier.webhook_url:
                print("✅ MinigameNotifier inicializado corretamente")
                return True
            else:
                print("❌ ERRO: MinigameNotifier não conseguiu carregar webhook")
                return False
        except Exception as e:
            print(f"❌ ERRO ao inicializar MinigameNotifier: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ ERRO ao verificar webhook: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_foreign_key_issues(db_path: str):
    """Verificar problemas de foreign key constraint"""
    print("\n" + "="*60)
    print("3. VERIFICANDO PROBLEMAS DE FOREIGN KEY")
    print("="*60)
    
    try:
        with DatabaseConnector.get_connection(db_path, write_mode=True) as conn:
            cursor = conn.cursor()
            
            # Verificar steam_ids que não existem na tabela players
            cursor.execute("""
                SELECT DISTINCT m.steam_id, m.player_name, COUNT(*) as count
                FROM minigame_events m
                LEFT JOIN players p ON m.steam_id = p.steam_id
                WHERE m.steam_id IS NOT NULL
                  AND p.steam_id IS NULL
                GROUP BY m.steam_id, m.player_name
                LIMIT 10
            """)
            
            orphans = cursor.fetchall()
            if orphans:
                print(f"⚠️  AVISO: {len(orphans)} steam_ids não encontrados na tabela players")
                print("   Isso pode causar falhas na inserção se foreign keys estiverem habilitadas")
                for steam_id, name, count in orphans[:5]:
                    print(f"   - {name} ({steam_id}): {count} eventos")
                if len(orphans) > 5:
                    print(f"   ... e mais {len(orphans) - 5}")
            else:
                print("✅ Todos os steam_ids existem na tabela players (ou tabela players está vazia)")
            
            # Verificar se foreign keys podem causar problemas
            cursor.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]
            
            if fk_enabled:
                print("⚠️  AVISO: Foreign keys estão habilitadas")
                print("   Inserções podem falhar se steam_id não existir na tabela players")
            
            return True
            
    except Exception as e:
        print(f"❌ ERRO ao verificar foreign keys: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parsing(logs_directory: str):
    """Testar parsing de eventos de minigame"""
    print("\n" + "="*60)
    print("4. TESTANDO PARSING DE EVENTOS")
    print("="*60)
    
    try:
        # Encontrar arquivo de log mais recente
        log_files = list(Path(logs_directory).glob("gameplay_*.log"))
        if not log_files:
            print(f"⚠️  AVISO: Nenhum arquivo gameplay_*.log encontrado em {logs_directory}")
            return False
        
        # Pegar o mais recente
        latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
        print(f"📄 Testando com arquivo: {latest_log.name}")
        
        # Inicializar parser
        temp_manager = TempFileManager()
        parser = GameplayLogParser(temp_manager)
        
        # Tentar parsear
        events = parser.parse_minigame_events(str(latest_log))
        
        if not events:
            print("⚠️  AVISO: Nenhum evento de minigame encontrado no arquivo")
            return False
        
        print(f"✅ {len(events)} eventos de minigame encontrados")
        
        # Analisar eventos
        lockpicking = [e for e in events if e.get('minigame_type') == 'LockpickingMinigame_C']
        print(f"ℹ️  Eventos de LockpickingMinigame_C: {len(lockpicking)}")
        
        with_owner = [e for e in lockpicking if e.get('owner_id') is not None]
        print(f"ℹ️  Com proprietário identificado: {len(with_owner)}")
        
        without_owner = [e for e in lockpicking if e.get('owner_id') is None]
        print(f"ℹ️  Sem proprietário: {len(without_owner)}")
        
        if without_owner:
            print("\n⚠️  Exemplo de evento SEM proprietário:")
            example = without_owner[0]
            print(f"   Jogador: {example.get('player_name')}")
            print(f"   Objeto: {example.get('target_object')}")
            log_line = example.get('log_line', '')[:200]
            print(f"   Log: {log_line}...")
            
            # Verificar se tem "User owner" na linha
            if 'User owner' in log_line:
                print("   ❌ PROBLEMA: 'User owner' está na linha mas não foi extraído!")
                print("   Possível problema na regex do owner_pattern")
        
        if with_owner:
            print("\n✅ Exemplo de evento COM proprietário:")
            example = with_owner[0]
            print(f"   Jogador: {example.get('player_name')}")
            print(f"   Proprietário: {example.get('owner_name')} (ID: {example.get('owner_id')})")
            print(f"   Invasão: {example.get('is_property_invasion')}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO ao testar parsing: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_recent_events(db_path: str):
    """Verificar eventos recentes no banco"""
    print("\n" + "="*60)
    print("5. VERIFICANDO EVENTOS RECENTES NO BANCO")
    print("="*60)
    
    try:
        with DatabaseConnector.get_connection(db_path, write_mode=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Últimos 10 eventos
            cursor.execute("""
                SELECT 
                    timestamp, player_name, minigame_type,
                    success, owner_name, discord_sent,
                    lock_type, target_object
                FROM minigame_events
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            
            events = cursor.fetchall()
            if not events:
                print("⚠️  AVISO: Nenhum evento no banco de dados")
                return False
            
            print(f"📊 Últimos {len(events)} eventos:")
            for event in events:
                status = "✅ Enviado" if event['discord_sent'] else "❌ Não enviado"
                owner = event['owner_name'] or "Sem proprietário"
                print(f"\n   [{event['timestamp']}] {event['player_name']}")
                print(f"   Tipo: {event['minigame_type']} | Lock: {event['lock_type']}")
                print(f"   Proprietário: {owner} | Status: {status}")
                print(f"   Objeto: {event['target_object']}")
            
            return True
            
    except Exception as e:
        print(f"❌ ERRO ao verificar eventos: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executar diagnóstico completo"""
    print("\n" + "="*60)
    print("🔍 DIAGNÓSTICO DE EVENTOS DE LOCKPICKING")
    print("="*60)
    
    # Inicializar path helper
    path_helper = ConfigPathHelper()
    db_path = path_helper.get_ssm_db_path()
    webhooks_path = path_helper.get_webhooks_path()
    logs_directory = path_helper.get_scum_logs_directory()
    
    print(f"\n📁 Caminhos:")
    print(f"   Banco: {db_path}")
    print(f"   Webhooks: {webhooks_path}")
    print(f"   Logs: {logs_directory}")
    
    results = []
    
    # Executar verificações
    results.append(("Estrutura do Banco", check_database_structure(db_path)))
    results.append(("Configuração do Webhook", check_webhook_config(webhooks_path)))
    results.append(("Foreign Keys", check_foreign_key_issues(db_path)))
    results.append(("Parsing de Eventos", test_parsing(logs_directory)))
    results.append(("Eventos Recentes", check_recent_events(db_path)))
    
    # Resumo
    print("\n" + "="*60)
    print("📋 RESUMO DO DIAGNÓSTICO")
    print("="*60)
    
    for name, result in results:
        status = "✅ OK" if result else "❌ FALHOU"
        print(f"   {status}: {name}")
    
    all_ok = all(result for _, result in results)
    
    if all_ok:
        print("\n✅ Todos os testes passaram!")
    else:
        print("\n⚠️  Alguns problemas foram detectados. Revise os detalhes acima.")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
