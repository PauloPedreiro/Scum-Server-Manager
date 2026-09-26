# 🌤️ **Sistema de Monitoramento Climático - SCUM Backend**

Sistema completo de monitoramento e sincronização dos dados climáticos do SCUM, incluindo horário do servidor, temperatura e condições meteorológicas.

## 📋 **Visão Geral**

O sistema de monitoramento climático permite:
- ✅ **Sincronização automática** dos dados climáticos do SCUM
- ✅ **Notificações Discord** com horário do servidor
- ✅ **Armazenamento** do estado atual no SSM.db
- ✅ **API REST** para controle manual
- ✅ **Agendamento configurável** (padrão: 30 minutos)

---

## ⚙️ **Configuração**

### **Arquivo `data/config.json`**
```json
{
  "weather_scheduler": {
    "enabled": true,
    "auto_start": true,
    "sync_interval_minutes": 30,
    "scum_db_path": "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db",
    "ssm_db_path": "data/SSM.db"
  }
}
```

### **Parâmetros:**
- **`enabled`** (boolean): Habilita/desabilita o sistema climático
- **`auto_start`** (boolean): Inicia automaticamente com o backend
- **`sync_interval_minutes`** (integer): Intervalo de sincronização em minutos
- **`scum_db_path`** (string): Caminho para o banco SCUM.db
- **`ssm_db_path`** (string): Caminho para o banco SSM.db

---

## 🔌 **API Endpoints**

### **Base URL**
```
http://localhost:3000
```

---

## 📊 **Status do Sistema Climático**

### **Endpoint**
```
GET /api/weather/status
```

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "is_running": true,
    "sync_interval_minutes": 30,
    "auto_start": true,
    "logs_count": 15,
    "next_sync": "A cada 30 minutos"
  },
  "timestamp": 1760629995.398204
}
```

### **Resposta de Erro (500)**
```json
{
  "success": false,
  "error": "WeatherScheduler não inicializado"
}
```

---

## 🚀 **Iniciar Sistema Climático**

### **Endpoint**
```
POST /api/weather/start
```

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "message": "Agendador climático iniciado com sucesso",
  "status": "started",
  "sync_interval_minutes": 30
}
```

### **Resposta de Erro (500)**
```json
{
  "success": false,
  "error": "WeatherScheduler não inicializado"
}
```

---

## ⏹️ **Parar Sistema Climático**

### **Endpoint**
```
POST /api/weather/stop
```

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "message": "Agendador climático parado com sucesso",
  "status": "stopped"
}
```

### **Resposta de Erro (500)**
```json
{
  "success": false,
  "error": "WeatherScheduler não inicializado"
}
```

---

## 🔄 **Sincronização Forçada**

### **Endpoint**
```
POST /api/weather/sync
```

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "message": "Sincronização climática executada com sucesso",
  "status": "completed"
}
```

### **Resposta de Erro (500)**
```json
{
  "success": false,
  "message": "Falha na sincronização climática",
  "status": "failed"
}
```

---

## 🕐 **Obter Horário e Dados Climáticos**

### **Endpoint**
```
GET /api/weather/time
```

### **Descrição**
Obtém o horário atual do servidor SCUM e todos os dados climáticos disponíveis, incluindo temperatura, condições meteorológicas e informações sobre o ciclo lunar.

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "data": {
    "server_time": "23:51",
    "time_of_day": 23.853744506835938,
    "air_temperature": 25.0,
    "water_temperature": 25.0,
    "moon_rotation": 3.69,
    "fog_density": 3.8e-05,
    "cumulonimbus_causes_fog": false,
    "map_id": 1,
    "user_profile_id": null,
    "last_sync": "2025-11-01 00:30:44",
    "next_sync": "2025-11-01 01:00:00",
    "sync_interval_minutes": 30,
    "is_running": true
  },
  "timestamp": 1760629995.398204
}
```

### **Campos da Resposta:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `server_time` | string | Horário formatado (HH:MM) |
| `time_of_day` | number | Horário decimal (0-24) |
| `air_temperature` | number | Temperatura do ar em °C |
| `water_temperature` | number | Temperatura da água em °C |
| `moon_rotation` | number | Rotação da lua |
| `fog_density` | number | Densidade do nevoeiro |
| `cumulonimbus_causes_fog` | boolean | Se cumulonimbus causa névoa |
| `map_id` | number | ID do mapa |
| `user_profile_id` | number/null | ID do perfil de usuário |
| `last_sync` | string | Última sincronização |
| `next_sync` | string | Próxima sincronização |
| `sync_interval_minutes` | number | Intervalo de sincronização |
| `is_running` | boolean | Se o scheduler está rodando |

### **Resposta de Erro (404)**
```json
{
  "success": false,
  "error": "Nenhum dado climático encontrado"
}
```

### **Resposta de Erro (500)**
```json
{
  "success": false,
  "error": "WeatherScheduler não inicializado"
}
```

---

## 📝 **Logs do Sistema**

### **Endpoint**
```
GET /api/weather/logs?limit=50
```

### **Parâmetros Query:**
- **`limit`** (integer, opcional): Número de logs a retornar (padrão: 50)

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "timestamp": "2025-01-15T10:30:00",
        "event": "sync_completed",
        "data": {
          "time": "15:15",
          "temperature": 22.5
        }
      }
    ],
    "count": 1,
    "total": 15
  },
  "timestamp": 1760629995.398204
}
```

---

## 🗄️ **Estrutura do Banco de Dados**

### **Tabela `weather_parameters` (SSM.db)**
```sql
CREATE TABLE weather_parameters (
    map_id INTEGER,
    user_profile_id INTEGER,
    time_of_day REAL,
    moon_rotation REAL,
    base_air_temperature REAL,
    water_temperature REAL,
    should_cumulonimbus_cause_fog INTEGER,
    fog_density REAL,
    data BLOB,
    sync_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### **Campos:**
- **`map_id`**: ID do mapa (usado como chave única)
- **`user_profile_id`**: ID do perfil de usuário
- **`time_of_day`**: Horário do jogo (0-24, formato decimal)
- **`moon_rotation`**: Rotação da lua
- **`base_air_temperature`**: Temperatura base do ar
- **`water_temperature`**: Temperatura da água
- **`should_cumulonimbus_cause_fog`**: Se cumulonimbus causa névoa
- **`fog_density`**: Densidade do nevoeiro
- **`data`**: Dados binários adicionais
- **`sync_timestamp`**: Timestamp da última sincronização

### **⚠️ Importante - Armazenamento:**
O sistema armazena apenas o **estado atual** dos dados climáticos. Cada nova sincronização substitui o registro existente (UPDATE baseado em `map_id`). Não há histórico de mudanças climáticas ao longo do tempo.

---

## 🔔 **Notificações Discord**

### **Webhook Configuração**
```json
{
  "timer": "https://discord.com/api/webhooks/1431324042194976798/..."
}
```

### **Formato da Notificação**
```json
{
  "embeds": [{
    "title": "🕐 Horário do Servidor SCUM",
    "description": "# 15:15",
    "color": 65280,
    "footer": {
      "text": "SSM Backend - Sistema de Monitoramento"
    }
  }]
}
```

---

## 🚨 **Tratamento de Erros**

### **Erros Comuns:**

**1. Banco SCUM não encontrado:**
```json
{
  "success": false,
  "message": "Banco SCUM não encontrado: C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
}
```

**2. Webhook não configurado:**
```json
{
  "success": false,
  "message": "Webhook 'timer' não configurado"
}
```

**3. Falha na sincronização:**
```json
{
  "success": false,
  "message": "Falha na sincronização climática"
}
```

---

## 📈 **Monitoramento**

### **Health Check**
```
GET /api/health
```

### **Resposta:**
```json
{
  "status": "healthy",
  "components": {
    "weather_scheduler": true
  }
}
```

---

## 🔧 **Manutenção**

### **Limpeza de Logs Antigos**
Os logs são automaticamente limitados aos últimos 100 registros.

### **Verificação de Status**
```bash
curl -X GET http://localhost:3000/api/weather/status
```

### **Sincronização Manual**
```bash
curl -X POST http://localhost:3000/api/weather/sync
```

---

## 📚 **Exemplos de Uso**

### **1. Verificar Status**
```bash
curl -X GET http://localhost:3000/api/weather/status
```

### **2. Iniciar Sistema**
```bash
curl -X POST http://localhost:3000/api/weather/start
```

### **3. Forçar Sincronização**
```bash
curl -X POST http://localhost:3000/api/weather/sync
```

### **4. Ver Logs**
```bash
curl -X GET "http://localhost:3000/api/weather/logs?limit=10"
```

---

## 🎯 **Funcionalidades Avançadas**

### **Sincronização Automática**
- Executa a cada 30 minutos (configurável)
- Atualiza dados no SSM.db
- Envia notificação para Discord
- Registra logs detalhados

### **Controle Manual**
- API REST completa
- Sincronização sob demanda
- Logs em tempo real
- Status detalhado

### **Integração com Backend**
- Inicialização automática
- Thread separada
- Sistema de callbacks
- Logs estruturados

---

## 🔍 **Troubleshooting**

### **Problemas Comuns:**

**1. Sistema não inicia:**
- Verificar configuração no `config.json`
- Verificar caminhos dos bancos de dados
- Verificar logs do backend

**2. Notificações não chegam:**
- Verificar webhook no `webhooks.json`
- Verificar conectividade com Discord
- Verificar logs de erro

**3. Dados não sincronizam:**
- Verificar se o SCUM.db existe
- Verificar permissões de arquivo
- Verificar logs de sincronização

---

## 📞 **Suporte**

Para problemas ou dúvidas:
1. Verificar logs: `GET /api/weather/logs`
2. Verificar status: `GET /api/weather/status`
3. Testar sincronização: `POST /api/weather/sync`
4. Verificar configuração no `config.json`
