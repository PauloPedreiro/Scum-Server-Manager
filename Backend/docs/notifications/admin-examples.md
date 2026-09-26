# 📋 Exemplos de Uso - Sistema de Admin Logs

## 🎯 Visão Geral

Este documento contém exemplos práticos de como usar o sistema de monitoramento de comandos admin do SCUM Server Manager.

## 🔧 Configuração Inicial

### 1. Configurar Webhook Discord

```json
{
  "adminlog": "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
}
```

### 2. Verificar Status do Sistema

```bash
curl -X GET "http://localhost:3000/api/admin-logs/status"
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "admin_log_processor": true,
    "webhook_configured": true,
    "last_processed_command": "2025.10.21-00.13.01:76561198040636105",
    "total_commands_processed": 156,
    "commands_by_category": {
      "spawn": 89,
      "teleport": 34,
      "godmode": 12,
      "info": 15,
      "command": 6
    },
    "most_active_admin": "Pedreiro (76561198040636105)",
    "last_activity": "2025-10-21T00:13:01Z"
  }
}
```

## 📊 Exemplos de Comandos Monitorados

### 🎁 Comandos de Spawn (Categoria: spawn)

**Comando no jogo:**
```
SpawnItem Phoenix_Tears
```

**Log gerado:**
```
2025.10.21-00.13.01: '76561198040636105:Pedreiro(1)' Command: 'SpawnItem Phoenix_Tears'
```

**Notificação Discord:**
```json
{
  "embeds": [{
    "title": "🎁 Spawn Item",
    "description": "**Admin:** Pedreiro\n**Steam ID:** `76561198040636105`\n**Comando:** SpawnItem Phoenix_Tears\n**Horário:** 21/10/2025 00:13:01",
    "color": 16119260,
    "timestamp": "2025-10-21T00:13:01Z",
    "footer": {
      "text": "SCUM Server Manager - Admin Log"
    }
  }]
}
```

### 🚀 Comandos de Teleporte (Categoria: teleport)

**Comando no jogo:**
```
Teleport 100 200
```

**Log gerado:**
```
2025.10.21-00.12.45: '76561198040636105:Pedreiro(1)' Command: 'Teleport 100 200'
```

**Notificação Discord:**
```json
{
  "embeds": [{
    "title": "🚀 Teleport",
    "description": "**Admin:** Pedreiro\n**Steam ID:** `76561198040636105`\n**Comando:** Teleport 100 200\n**Horário:** 21/10/2025 00:12:45",
    "color": 10181046,
    "timestamp": "2025-10-21T00:12:45Z",
    "footer": {
      "text": "SCUM Server Manager - Admin Log"
    }
  }]
}
```

### 🛡️ Comandos de God Mode (Categoria: godmode)

**Comando no jogo:**
```
GodMode true
```

**Log gerado:**
```
2025.10.21-00.11.30: '76561198040636105:Pedreiro(1)' Command: 'GodMode true'
```

**Notificação Discord:**
```json
{
  "embeds": [{
    "title": "🛡️ God Mode",
    "description": "**Admin:** Pedreiro\n**Steam ID:** `76561198040636105`\n**Comando:** GodMode true\n**Horário:** 21/10/2025 00:11:30",
    "color": 15158332,
    "timestamp": "2025-10-21T00:11:30Z",
    "footer": {
      "text": "SCUM Server Manager - Admin Log"
    }
  }]
}
```

## 📈 Consultas de Estatísticas

### 1. Estatísticas Gerais

```bash
curl -X GET "http://localhost:3000/api/admin-logs/stats"
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "total_commands": 156,
    "commands_today": 23,
    "commands_this_week": 89,
    "commands_this_month": 156,
    "categories": {
      "spawn": {
        "count": 89,
        "percentage": 57.1,
        "emoji": "🎁",
        "color": "#f1c40f"
      },
      "teleport": {
        "count": 34,
        "percentage": 21.8,
        "emoji": "🚀",
        "color": "#9b59b6"
      }
    },
    "top_admins": [
      {
        "steam_id": "76561198040636105",
        "name": "Pedreiro",
        "commands_count": 89,
        "percentage": 57.1
      }
    ]
  }
}
```

### 2. Últimos Comandos

```bash
curl -X GET "http://localhost:3000/api/admin-logs/recent?limit=5"
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "commands": [
      {
        "command_id": "2025.10.21-00.13.01:76561198040636105",
        "timestamp": "2025-10-21T00:13:01Z",
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "action": "SpawnItem Phoenix_Tears",
        "category": {
          "name": "spawn",
          "emoji": "🎁",
          "color": "#f1c40f"
        }
      }
    ],
    "total": 156,
    "limit": 5
  }
}
```

### 3. Status de Processamento

```bash
curl -X GET "http://localhost:3000/api/admin-logs/processing-status"
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "processing_status": "active",
    "last_processed_command": "2025.10.21-00.13.01:76561198040636105",
    "method_available": true,
    "database_connection": true,
    "webhook_configured": true,
    "error_count": 0,
    "last_error": null,
    "uptime": "2h 15m 30s",
    "version": "1.2.0",
    "temp_files_cleanup": "working",
    "log_files_table": "active",
    "fixes_applied": [
      "Método _get_last_processed_command() implementado",
      "Sistema migrado para banco SQLite",
      "Controle de estado melhorado",
      "Limpeza de arquivos temporários corrigida",
      "Registro na tabela log_files_processed implementado"
    ]
  }
}
```

### 4. Status da Tabela de Arquivos

```bash
curl -X GET "http://localhost:3000/api/admin-logs/files-status"
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "total_files": 5,
    "admin_files": 3,
    "files_by_status": {
      "completed": 5,
      "active": 0,
      "error": 0
    },
    "recent_admin_files": [
      {
        "file_name": "admin_20251021121820.log",
        "lines_processed": 0,
        "status": "completed",
        "updated_at": "2025-10-21T12:18:20.000Z"
      }
    ],
    "table_status": "active",
    "last_update": "2025-10-21T12:18:20.000Z"
  }
}
```

## 🔧 Personalização de Categorias

### Adicionar Nova Categoria

Edite o arquivo `core/logs/admin_log_processor.py`:

```python
self.command_categories = {
    # Categorias existentes...
    
    'custom': {
        'keywords': ['custom', 'meucomando', 'especial'],
        'emoji': '⭐',
        'color': 0xff6b35,  # Laranja
        'name': 'Comando Customizado'
    }
}
```

### Exemplo de Comando Customizado

**Comando no jogo:**
```
CustomCommand parametro1 parametro2
```

**Log gerado:**
```
2025.10.21-00.15.30: '76561198040636105:Pedreiro(1)' Command: 'CustomCommand parametro1 parametro2'
```

**Notificação Discord:**
```json
{
  "embeds": [{
    "title": "⭐ Comando Customizado",
    "description": "**Admin:** Pedreiro\n**Steam ID:** `76561198040636105`\n**Comando:** CustomCommand parametro1 parametro2\n**Horário:** 21/10/2025 00:15:30",
    "color": 16744448,
    "timestamp": "2025-10-21T00:15:30Z",
    "footer": {
      "text": "SCUM Server Manager - Admin Log"
    }
  }]
}
```

## 🚨 Troubleshooting

### Problema: Comandos não aparecem no Discord

**Verificação:**
```bash
# 1. Verificar webhook
curl -X GET "http://localhost:3000/api/admin-logs/status"

# 2. Verificar arquivo de log
ls -la C:\Servers\Scum\SCUM\Saved\SaveFiles\Logs\admin_*.log

# 3. Verificar logs do backend
tail -f data/logs/scum_backend.log
```

### Problema: Erro "_get_last_processed_command"

**Status:** ✅ **CORRIGIDO na v1.2.0**

**Solução:**
```bash
# Reiniciar o backend após a correção
python main.py
```

### Problema: Arquivos temporários não removidos

**Status:** ✅ **CORRIGIDO na v1.2.0**

**Solução:**
```bash
# Limpar arquivos órfãos
python auto_cleanup_temp.py

# Verificar pasta temp
ls -la data/temp/
```

### Problema: Tabela log_files_processed não usada

**Status:** ✅ **CORRIGIDO na v1.2.0**

**Verificação:**
```bash
# Verificar status da tabela
python check_log_files_status.py

# Verificar via API
curl -X GET "http://localhost:3000/api/admin-logs/files-status"
```

### Problema: Comandos duplicados

**Verificação:**
```bash
# Verificar banco de dados
sqlite3 data/SSM.db "SELECT COUNT(*) FROM admin_commands_processed;"
```

## 📝 Scripts Úteis

### Script para Monitorar Admin Logs

```python
#!/usr/bin/env python3
"""
Script para monitorar admin logs em tempo real
"""

import requests
import time
import json

def monitor_admin_logs():
    base_url = "http://localhost:3000"
    
    while True:
        try:
            # Verificar status
            response = requests.get(f"{base_url}/api/admin-logs/status")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Sistema ativo - {data['data']['total_commands_processed']} comandos processados")
            
            # Verificar últimos comandos
            response = requests.get(f"{base_url}/api/admin-logs/recent?limit=1")
            if response.status_code == 200:
                data = response.json()
                if data['data']['commands']:
                    cmd = data['data']['commands'][0]
                    print(f"🔄 Último comando: {cmd['player_name']} - {cmd['action']}")
            
            time.sleep(30)  # Verificar a cada 30 segundos
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            time.sleep(60)

if __name__ == "__main__":
    monitor_admin_logs()
```

### Script para Estatísticas Diárias

```python
#!/usr/bin/env python3
"""
Script para gerar relatório diário de admin logs
"""

import requests
import json
from datetime import datetime

def daily_report():
    base_url = "http://localhost:3000"
    
    # Obter estatísticas
    response = requests.get(f"{base_url}/api/admin-logs/stats")
    if response.status_code == 200:
        data = response.json()
        stats = data['data']
        
        print("📊 RELATÓRIO DIÁRIO - ADMIN LOGS")
        print("=" * 50)
        print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y')}")
        print(f"📈 Total de comandos: {stats['total_commands']}")
        print(f"📈 Comandos hoje: {stats['commands_today']}")
        print()
        
        print("🏆 TOP ADMINS:")
        for admin in stats['top_admins'][:3]:
            print(f"  • {admin['name']}: {admin['commands_count']} comandos ({admin['percentage']:.1f}%)")
        print()
        
        print("📊 CATEGORIAS:")
        for category, info in stats['categories'].items():
            print(f"  • {info['emoji']} {category.title()}: {info['count']} ({info['percentage']:.1f}%)")

if __name__ == "__main__":
    daily_report()
```

## 🎯 Casos de Uso Práticos

### 1. Monitoramento de Administradores

- **Objetivo**: Acompanhar atividade dos admins
- **Endpoint**: `/api/admin-logs/recent?limit=50`
- **Frequência**: A cada hora
- **Ação**: Alertar se admin inativo há mais de 4 horas

### 2. Detecção de Abuso

- **Objetivo**: Identificar uso excessivo de comandos
- **Endpoint**: `/api/admin-logs/stats`
- **Critério**: Mais de 100 comandos spawn em 1 hora
- **Ação**: Notificar administradores superiores

### 3. Relatórios de Atividade

- **Objetivo**: Gerar relatórios semanais
- **Endpoint**: `/api/admin-logs/stats`
- **Dados**: Comandos por categoria, admins mais ativos
- **Frequência**: Semanal

---

**Última atualização**: 21/10/2025  
**Versão**: 1.2.0  
**Status**: ✅ Documentação Completa e Atualizada  
**Correções**: Limpeza de arquivos temporários e tabela log_files_processed