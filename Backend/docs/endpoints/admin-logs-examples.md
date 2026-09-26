# 👨‍💼 Exemplos de Uso - Sistema de Admin Logs

## 📋 Visão Geral

Este documento contém exemplos práticos de como usar os endpoints do sistema de monitoramento de comandos admin.

## 🔗 Endpoints Disponíveis

### 1. Status do Sistema
**GET** `/api/admin-logs/status`

Verifica o status do sistema de monitoramento de comandos admin.

#### Exemplo de Resposta
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
  },
  "timestamp": 1760907347.523
}
```

### 2. Estatísticas Detalhadas
**GET** `/api/admin-logs/stats`

Obtém estatísticas detalhadas dos comandos admin processados.

#### Exemplo de Resposta
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
      },
      "godmode": {
        "count": 12,
        "percentage": 7.7,
        "emoji": "🛡️",
        "color": "#e74c3c"
      },
      "info": {
        "count": 15,
        "percentage": 9.6,
        "emoji": "👁️",
        "color": "#3498db"
      },
      "command": {
        "count": 6,
        "percentage": 3.8,
        "emoji": "⚡",
        "color": "#ff6b35"
      }
    },
    "top_admins": [
      {
        "steam_id": "76561198040636105",
        "name": "Pedreiro",
        "commands_count": 89,
        "percentage": 57.1
      },
      {
        "steam_id": "76561198042887008",
        "name": "Mantones",
        "commands_count": 45,
        "percentage": 28.8
      }
    ],
    "hourly_distribution": {
      "00:00": 12,
      "01:00": 8,
      "02:00": 3,
      "22:00": 15,
      "23:00": 18
    }
  },
  "timestamp": 1760907347.523
}
```

### 3. Últimos Comandos
**GET** `/api/admin-logs/recent?limit=10`

Obtém os últimos comandos admin executados.

#### Parâmetros
- `limit` (opcional): Número de comandos a retornar (padrão: 10)

#### Exemplo de Resposta
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
      },
      {
        "command_id": "2025.10.21-00.12.45:76561198040636105",
        "timestamp": "2025-10-21T00:12:45Z",
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "action": "Teleport 100 200",
        "category": {
          "name": "teleport",
          "emoji": "🚀",
          "color": "#9b59b6"
        }
      }
    ],
    "total": 156,
    "limit": 10
  },
  "timestamp": 1760907347.523
}
```

## 🐍 Exemplos em Python

### Verificar Status do Sistema
```python
import requests

def check_admin_logs_status():
    response = requests.get('http://localhost:3000/api/admin-logs/status')
    data = response.json()
    
    if data['success']:
        print(f"✅ Sistema ativo: {data['data']['admin_log_processor']}")
        print(f"📊 Total de comandos: {data['data']['total_commands_processed']}")
        print(f"👤 Admin mais ativo: {data['data']['most_active_admin']}")
    else:
        print("❌ Erro ao verificar status")

check_admin_logs_status()
```

### Obter Estatísticas
```python
import requests

def get_admin_stats():
    response = requests.get('http://localhost:3000/api/admin-logs/stats')
    data = response.json()
    
    if data['success']:
        stats = data['data']
        print(f"📈 Comandos hoje: {stats['commands_today']}")
        print(f"📈 Comandos esta semana: {stats['commands_this_week']}")
        
        print("\n📊 Por categoria:")
        for category, info in stats['categories'].items():
            print(f"  {info['emoji']} {category}: {info['count']} ({info['percentage']}%)")
        
        print("\n👑 Top admins:")
        for admin in stats['top_admins']:
            print(f"  {admin['name']}: {admin['commands_count']} comandos")
    else:
        print("❌ Erro ao obter estatísticas")

get_admin_stats()
```

### Monitorar Comandos em Tempo Real
```python
import requests
import time

def monitor_admin_commands():
    last_command_id = None
    
    while True:
        response = requests.get('http://localhost:3000/api/admin-logs/recent?limit=1')
        data = response.json()
        
        if data['success'] and data['data']['commands']:
            command = data['data']['commands'][0]
            current_id = command['command_id']
            
            if last_command_id != current_id:
                print(f"🆕 Novo comando: {command['player_name']} - {command['action']}")
                print(f"   Categoria: {command['category']['emoji']} {command['category']['name']}")
                print(f"   Timestamp: {command['timestamp']}")
                print("-" * 50)
                last_command_id = current_id
        
        time.sleep(5)  # Verificar a cada 5 segundos

# monitor_admin_commands()  # Descomente para usar
```

## 🔧 Exemplos de cURL

### Verificar Status
```bash
curl -X GET "http://localhost:3000/api/admin-logs/status" \
  -H "Content-Type: application/json"
```

### Obter Estatísticas
```bash
curl -X GET "http://localhost:3000/api/admin-logs/stats" \
  -H "Content-Type: application/json"
```

### Últimos Comandos
```bash
curl -X GET "http://localhost:3000/api/admin-logs/recent?limit=5" \
  -H "Content-Type: application/json"
```

## 📊 Casos de Uso

### 1. Dashboard de Administração
Use os endpoints para criar um dashboard que mostre:
- Status do sistema em tempo real
- Estatísticas de uso por categoria
- Ranking de administradores mais ativos
- Gráficos de atividade por hora

### 2. Monitoramento de Segurança
- Verificar comandos suspeitos
- Monitorar atividade de administradores
- Detectar padrões anômalos de uso

### 3. Relatórios de Atividade
- Gerar relatórios de uso de comandos
- Analisar eficiência de administradores
- Identificar horários de maior atividade

## 🚨 Tratamento de Erros

### Respostas de Erro Comuns
```json
{
  "success": false,
  "error": "Sistema de admin logs não inicializado",
  "timestamp": 1760907347.523
}
```

### Códigos de Status HTTP
- **200**: Sucesso
- **404**: Endpoint não encontrado
- **500**: Erro interno do servidor

## 🔍 Troubleshooting

### Problema: Sistema não inicializado
```python
# Verificar se o sistema está ativo
response = requests.get('http://localhost:3000/api/admin-logs/status')
if not response.json()['data']['admin_log_processor']:
    print("❌ Sistema não inicializado")
```

### Problema: Webhook não configurado
```python
# Verificar configuração do webhook
response = requests.get('http://localhost:3000/api/admin-logs/status')
if not response.json()['data']['webhook_configured']:
    print("❌ Webhook não configurado")
```

---

**Última atualização**: 20/10/2025  
**Versão**: 1.0.0
