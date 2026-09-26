# 🖥️ **Exemplos cURL - SCUM Backend API**

Coleção de exemplos práticos usando cURL para testar todos os endpoints da API.

## 🌐 **Base URL**
```bash
BASE_URL="http://localhost:3000"
```

---

## 🔍 **Health Check**

### **Verificar saúde da aplicação**
```bash
curl -X GET "$BASE_URL/api/health"
```

### **Com headers detalhados**
```bash
curl -X GET "$BASE_URL/api/health" \
  -H "Accept: application/json" \
  -H "User-Agent: SCUM-Backend-Test/1.0" \
  -v
```

---

## 📊 **Status do Servidor**

### **Obter status atual**
```bash
curl -X GET "$BASE_URL/api/server/status"
```

### **Com formatação JSON**
```bash
curl -X GET "$BASE_URL/api/server/status" | jq .
```

### **Salvar resposta em arquivo**
```bash
curl -X GET "$BASE_URL/api/server/status" \
  -o server_status.json
```

---

## 🚀 **Iniciar Servidor**

### **Iniciar com parâmetros padrão**
```bash
curl -X POST "$BASE_URL/api/server/start" \
  -H "Content-Type: application/json" \
  -d '{
    "force": false,
    "wait_timeout": 30
  }'
```

### **Forçar início (mesmo se já estiver rodando)**
```bash
curl -X POST "$BASE_URL/api/server/start" \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "wait_timeout": 60
  }'
```

### **Iniciar sem aguardar confirmação**
```bash
curl -X POST "$BASE_URL/api/server/start" \
  -H "Content-Type: application/json" \
  -d '{
    "force": false,
    "wait_timeout": 0
  }'
```

### **Com formatação JSON e verbose**
```bash
curl -X POST "$BASE_URL/api/server/start" \
  -H "Content-Type: application/json" \
  -d '{
    "force": false,
    "wait_timeout": 30
  }' \
  | jq . \
  -v
```

---

## 🛑 **Parar Servidor**

### **Parar com parâmetros padrão**
```bash
curl -X POST "$BASE_URL/api/server/stop" \
  -H "Content-Type: application/json" \
  -d '{
    "force": false,
    "wait_timeout": 30
  }'
```

### **Forçar parada**
```bash
curl -X POST "$BASE_URL/api/server/stop" \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "wait_timeout": 60
  }'
```

### **Parar sem aguardar confirmação**
```bash
curl -X POST "$BASE_URL/api/server/stop" \
  -H "Content-Type: application/json" \
  -d '{
    "force": false,
    "wait_timeout": 0
  }'
```

---

## 🔄 **Reiniciar Servidor**

### **Reiniciar com parâmetros padrão**
> **📡 Nota:** Este endpoint envia notificações automáticas para Discord durante o processo.

```bash
curl -X POST "$BASE_URL/api/server/restart" \
  -H "Content-Type: application/json" \
  -d '{
    "force": false,
    "wait_timeout": 30
  }'
```

### **Reiniciar forçado**
```bash
curl -X POST "$BASE_URL/api/server/restart" \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "wait_timeout": 60
  }'
```

---

## 📝 **Obter Logs**

### **Últimos 10 logs**
```bash
curl -X GET "$BASE_URL/api/server/logs?limit=10"
```

### **Últimos 50 logs**
```bash
curl -X GET "$BASE_URL/api/server/logs?limit=50"
```

### **Logs de erro apenas**
```bash
curl -X GET "$BASE_URL/api/server/logs?level=error&limit=20"
```

### **Logs de warning e erro**
```bash
curl -X GET "$BASE_URL/api/server/logs?level=warn&limit=15"
```

### **Logs desde timestamp específico**
```bash
curl -X GET "$BASE_URL/api/server/logs?since=1760629995&limit=100"
```

### **Salvar logs em arquivo**
```bash
curl -X GET "$BASE_URL/api/server/logs?limit=100" \
  -o server_logs.json
```

---

## 🧪 **Sequências de Teste**

### **Teste Completo - Iniciar Servidor**
```bash
#!/bin/bash

echo "🔍 Verificando saúde da API..."
curl -s "$BASE_URL/api/health" | jq .

echo -e "\n📊 Status atual do servidor..."
curl -s "$BASE_URL/api/server/status" | jq .

echo -e "\n🚀 Iniciando servidor..."
curl -s -X POST "$BASE_URL/api/server/start" \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 30}' | jq .

echo -e "\n📊 Verificando se iniciou..."
sleep 5
curl -s "$BASE_URL/api/server/status" | jq .

echo -e "\n📝 Últimos logs..."
curl -s "$BASE_URL/api/server/logs?limit=5" | jq .
```

### **Teste Completo - Parar Servidor**
```bash
#!/bin/bash

echo "📊 Status atual do servidor..."
curl -s "$BASE_URL/api/server/status" | jq .

echo -e "\n🛑 Parando servidor..."
curl -s -X POST "$BASE_URL/api/server/stop" \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 30}' | jq .

echo -e "\n📊 Verificando se parou..."
sleep 5
curl -s "$BASE_URL/api/server/status" | jq .
```

### **Teste Completo - Reiniciar Servidor**
```bash
#!/bin/bash

echo "📊 Status atual do servidor..."
curl -s "$BASE_URL/api/server/status" | jq .

echo -e "\n🔄 Reiniciando servidor..."
curl -s -X POST "$BASE_URL/api/server/restart" \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 30}' | jq .

echo -e "\n📊 Verificando se reiniciou..."
sleep 10
curl -s "$BASE_URL/api/server/status" | jq .

echo -e "\n📝 Últimos logs..."
curl -s "$BASE_URL/api/server/logs?limit=10" | jq .
```

---

## 🔧 **Scripts de Automação**

### **Script de Monitoramento**
```bash
#!/bin/bash
# monitor.sh - Monitora status do servidor a cada 30 segundos

while true; do
  echo "=== $(date) ==="
  
  # Health check
  health=$(curl -s "$BASE_URL/api/health" | jq -r '.status')
  echo "API Health: $health"
  
  # Server status
  status=$(curl -s "$BASE_URL/api/server/status" | jq -r '.data.is_running')
  echo "Server Running: $status"
  
  # Logs de erro recentes
  errors=$(curl -s "$BASE_URL/api/server/logs?level=error&limit=1" | jq -r '.data.logs[0].message // "Nenhum erro"')
  echo "Last Error: $errors"
  
  echo "---"
  sleep 30
done
```

### **Script de Backup de Logs**
```bash
#!/bin/bash
# backup_logs.sh - Faz backup dos logs diariamente

DATE=$(date +%Y%m%d)
LOG_FILE="logs_backup_$DATE.json"

echo "📝 Fazendo backup dos logs de $DATE..."

curl -s "$BASE_URL/api/server/logs?limit=1000" \
  -o "backups/$LOG_FILE"

echo "✅ Backup salvo em: backups/$LOG_FILE"
```

### **Script de Teste de Carga**
```bash
#!/bin/bash
# load_test.sh - Testa a API com múltiplas requisições

echo "🧪 Iniciando teste de carga..."

for i in {1..10}; do
  echo "Requisição $i/10"
  
  # Health check
  curl -s "$BASE_URL/api/health" > /dev/null
  
  # Status check
  curl -s "$BASE_URL/api/server/status" > /dev/null
  
  # Logs
  curl -s "$BASE_URL/api/server/logs?limit=5" > /dev/null
  
  sleep 1
done

echo "✅ Teste de carga concluído!"
```

---

## 📊 **Exemplos com jq (JSON Parser)**

### **Extrair apenas o status**
```bash
curl -s "$BASE_URL/api/server/status" | jq -r '.data.is_running'
```

### **Extrair informações específicas**
```bash
curl -s "$BASE_URL/api/server/status" | jq '{
  running: .data.is_running,
  service: .data.service_name,
  port: .data.port,
  max_players: .data.max_players
}'
```

### **Filtrar logs por nível**
```bash
curl -s "$BASE_URL/api/server/logs?limit=50" | jq '.data.logs[] | select(.level == "ERROR")'
```

### **Contar logs por nível**
```bash
curl -s "$BASE_URL/api/server/logs?limit=100" | jq '.data.logs | group_by(.level) | map({level: .[0].level, count: length})'
```

### **Últimos 5 logs formatados**
```bash
curl -s "$BASE_URL/api/server/logs?limit=5" | jq -r '.data.logs[] | "\(.timestamp) [\(.level)] \(.message)"'
```

---

## ⚠️ **Tratamento de Erros**

### **Verificar se API está respondendo**
```bash
if curl -s "$BASE_URL/api/health" > /dev/null; then
  echo "✅ API está respondendo"
else
  echo "❌ API não está respondendo"
  exit 1
fi
```

### **Verificar resposta de erro**
```bash
response=$(curl -s -w "%{http_code}" "$BASE_URL/api/server/start" \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 30}')

http_code="${response: -3}"
body="${response%???}"

if [ "$http_code" -eq 200 ]; then
  echo "✅ Sucesso: $body"
else
  echo "❌ Erro ($http_code): $body"
fi
```

### **Timeout personalizado**
```bash
curl --max-time 30 \
  --connect-timeout 10 \
  -X POST "$BASE_URL/api/server/start" \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 30}'
```

---

## 🎯 **Dicas de Uso**

### **1. Sempre verificar o health check primeiro**
```bash
curl -s "$BASE_URL/api/health" | jq -r '.status'
```

### **2. Usar timeouts apropriados**
```bash
curl --max-time 60  # 60 segundos para operações longas
```

### **3. Salvar respostas importantes**
```bash
curl -s "$BASE_URL/api/server/status" > status_$(date +%Y%m%d_%H%M%S).json
```

### **4. Usar jq para formatação**
```bash
curl -s "$BASE_URL/api/server/logs?limit=10" | jq '.data.logs[] | {timestamp, level, message}'
```

### **5. Monitorar logs em tempo real**
```bash
watch -n 5 'curl -s "$BASE_URL/api/server/logs?limit=5" | jq ".data.logs[] | \"\(.timestamp) [\(.level)] \(.message)\""'
```

---

**Documentação atualizada em: 16/10/2025**  
**Versão da API: 1.0.0**
