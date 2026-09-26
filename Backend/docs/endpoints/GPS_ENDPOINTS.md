# 📍 Sistema de GPS - Documentação de Endpoints

Sistema de sincronização de GPS dos jogadores online que monitora a localização, direção e velocidade dos personagens em tempo real.

## 📋 Visão Geral

O sistema de GPS obtém em tempo real a localização dos jogadores online diretamente do servidor de jogo via comandos RCON (`ListPlayers`), armazenando as coordenadas na tabela `player_gps_snapshot` no banco `SSM.db`, eliminando a necessidade de consultas periódicas ao banco de dados `SCUM.db` do servidor.

### **Funcionalidades**
- ✅ Sincronização automática a cada 30 segundos (configurável)
- ✅ Monitoramento em tempo real de jogadores online
- ✅ Dados de localização (X, Y, Z) extraídos diretamente da memória do servidor de jogo
- ✅ Eliminação de locks e sobrecarga de I/O no banco de dados `SCUM.db`

## 🔧 Configuração

O serviço é configurado no arquivo `data/config.json`:

```json
{
  "player_gps_sync": {
    "enabled": true,
    "auto_start": true,
    "sync_interval_seconds": 30,
    "description": "Sincronização de GPS dos jogadores online via RCON"
  }
}
```

### **Parâmetros de Configuração**
- **`enabled`** (boolean): Habilita/desabilita o serviço
- **`auto_start`** (boolean): Inicia automaticamente quando o backend é iniciado
- **`sync_interval_seconds`** (integer): Intervalo de sincronização em segundos (padrão: 30)
- **`sync_interval_minutes`** (integer, opcional): Intervalo de sincronização em minutos (alternativa a seconds)

## 📡 Endpoints Disponíveis

### **1. Status do Serviço de Sincronização GPS**

Obter status atual do serviço de sincronização de GPS.

#### **Endpoint**
```
GET /api/gps/sync/status
```

#### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "is_running": true,
    "sync_interval": "30 seconds",
    "last_sync": {
      "timestamp": "2025-11-17T20:21:56.322386",
      "status": "success",
      "details": {
        "players_synced": 1,
        "source": "rcon"
      }
    }
  },
  "timestamp": 1763410930.6846802
}
```

#### **Resposta de Erro (500)**
```json
{
  "success": false,
  "error": "PlayerGpsSyncService não inicializado"
}
```

---

### **2. Iniciar Serviço de Sincronização GPS**

Iniciar o serviço de sincronização de GPS. Executa uma sincronização imediata e agenda as próximas execuções.

#### **Endpoint**
```
POST /api/gps/sync/start
```

#### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "message": "Sincronização de GPS iniciada",
  "status": "started",
  "sync_interval": "30 seconds"
}
```

#### **Resposta de Erro (400) - Já em Execução**
```json
{
  "success": false,
  "message": "Sincronização de GPS já está em execução",
  "status": "already_running"
}
```

#### **Resposta de Erro (500)**
```json
{
  "success": false,
  "error": "PlayerGpsSyncService não inicializado"
}
```

---

### **3. Parar Serviço de Sincronização GPS**

Parar o serviço de sincronização de GPS.

#### **Endpoint**
```
POST /api/gps/sync/stop
```

#### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "message": "Sincronização de GPS parada",
  "status": "stopped"
}
```

#### **Resposta de Erro (400) - Não Está em Execução**
```json
{
  "success": false,
  "message": "Sincronização de GPS não está em execução",
  "status": "not_running"
}
```

#### **Resposta de Erro (500)**
```json
{
  "success": false,
  "error": "PlayerGpsSyncService não inicializado"
}
```

---

### **4. Executar Sincronização GPS Manual**

Executar uma sincronização manual imediata, independente do agendamento.

#### **Endpoint**
```
POST /api/gps/sync/run-now
```

#### **Resposta de Sucesso (200) - Com Jogadores Online**
```json
{
  "success": true,
  "players_synced": 1,
  "source": "rcon"
}
```

#### **Resposta de Sucesso (200) - Sem Jogadores Online**
```json
{
  "success": true,
  "players_synced": 0,
  "message": "Nenhum jogador online"
}
```

#### **Resposta de Erro (500)**
```json
{
  "success": false,
  "error": "PlayerGpsSyncService não inicializado"
}
```

---

### **5. Obter GPS dos Jogadores Online**

Obter dados de GPS apenas dos jogadores que estão online no momento.

#### **Endpoint**
```
GET /api/gps/online
```

#### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "data": {
    "players": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "last_activity": "2025-11-17T20:09:21",
        "ssm_coordinates": {
          "x": -616882.0,
          "y": -554072.0,
          "z": 2477.0
        },
        "gps_data": {
          "spawns": [
            {
              "prisoner_id": null,
              "location_x": -616882.0,
              "location_y": -554072.0,
              "location_z": 2477.0,
              "rotation_yaw": null,
              "velocity_x": null,
              "velocity_y": null,
              "velocity_z": null,
              "type": 0,
              "updated_at": "2025-11-17T20:21:56"
            }
          ]
        }
      }
    ],
    "count": 1
  },
  "timestamp": 1763410930.6846802
}
```

#### **Resposta de Erro (500)**
```json
{
  "success": false,
  "error": "Erro específico"
}
```

---

## 🎯 Como Funciona

### **Processo de Sincronização**

1. **Consulta RCON**
   - O serviço envia o comando `ListPlayers` para o servidor de jogo via RCON.
   - A resposta contendo nome, steam_id e localização (`Location: X=... Y=... Z=...`) de cada jogador online é recebida e processada.

2. **Atualização no SSM.db**
   - Insere ou atualiza registros na tabela `player_gps_snapshot` do banco `SSM.db`.
   - Mantém o carimbo de data e hora `updated_at` atualizado.
   - Os dados são enriquecidos com `steam_id` e `player_name`.

### **Estrutura da Tabela `player_gps_snapshot`**

```sql
CREATE TABLE IF NOT EXISTS player_gps_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    player_name TEXT,
    fake_name TEXT,
    prisoner_id INTEGER,
    location_x REAL,
    location_y REAL,
    location_z REAL,
    rotation_yaw REAL,
    velocity_x REAL,
    velocity_y REAL,
    velocity_z REAL,
    type INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(steam_id, prisoner_id)
);
```

### **Dados Sincronizados**

- **Localização**: Coordenadas X, Y, Z do personagem obtidas via RCON.
- **Campos adicionais** (como `rotation_yaw`, `velocity_x/y/z`): Definidos como `NULL`/opcionais quando originados via RCON, pois o comando padrão não os fornece.

---

## 📊 Exemplos de Uso

### **Python**
```python
import requests

base_url = "http://localhost:3000"

# Obter status do serviço
response = requests.get(f"{base_url}/api/gps/sync/status")
print(response.json())

# Iniciar sincronização
response = requests.post(f"{base_url}/api/gps/sync/start")
print(response.json())

# Executar sincronização manual
response = requests.post(f"{base_url}/api/gps/sync/run-now")
print(response.json())

# Obter GPS dos jogadores online
response = requests.get(f"{base_url}/api/gps/online")
print(response.json())
```

### **cURL**
```bash
# Obter status
curl http://localhost:3000/api/gps/sync/status

# Iniciar sincronização
curl -X POST http://localhost:3000/api/gps/sync/start

# Executar sincronização manual
curl -X POST http://localhost:3000/api/gps/sync/run-now

# Obter GPS dos jogadores online
curl http://localhost:3000/api/gps/online
```

### **JavaScript (Node.js)**
```javascript
const axios = require('axios');

const baseUrl = 'http://localhost:3000';

// Obter status
const status = await axios.get(`${baseUrl}/api/gps/sync/status`);
console.log(status.data);

// Iniciar sincronização
const start = await axios.post(`${baseUrl}/api/gps/sync/start`);
console.log(start.data);

// Obter GPS dos jogadores online
const gps = await axios.get(`${baseUrl}/api/gps/online`);
console.log(gps.data);
```

---

## ⚠️ Notas Importantes

### **Performance**
- A busca via RCON ocorre em tempo real, sem necessidade de ler arquivos SQLite compartilhados.
- Sincronização a cada 30 segundos garante dados atualizados sem sobrecarregar o servidor do jogo.

### **Limitações**
- Requer conexão RCON ativa e configurada no backend.
- Apenas localização tridimensional (X, Y, Z) é extraída do `ListPlayers` padrão.

### **Troubleshooting**

**Serviço não inicializa:**
- Verificar se o RCON está habilitado e configurado corretamente em `config.json`.
- Verificar logs do backend para confirmar falhas de autenticação RCON.

**Sincronização não executa:**
- Confirmar se o serviço de sincronização está rodando (`GET /api/gps/sync/status`).
- Testar a conexão do RCON a partir do painel de administração.

---

## 📚 Documentação Relacionada

- [README.md](./README.md) - Documentação geral dos endpoints
- [VEHICLE_VERIFICATION_ENDPOINTS.md](./VEHICLE_VERIFICATION_ENDPOINTS.md) - Sistema de verificação de veículos

