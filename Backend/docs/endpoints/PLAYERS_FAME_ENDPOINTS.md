# 🏆 Documentação - Endpoints de Fama dos Jogadores

## 📋 Visão Geral

Endpoints para consultar os totais de fama dos jogadores do servidor SCUM. A fama é atualizada automaticamente em tempo real através do processamento dos logs `famepoints_*.log`.

---

## 📡 **Endpoints Disponíveis**

### **1. Listar Todos os Jogadores com Fama**

**GET** `/api/players/fame`

Lista todos os jogadores com seus totais de fama, ordenados por total de fama.

#### **URL Base**
```
http://192.168.100.3:3000/api/players/fame
```
*(Substitua pela URL do seu ambiente de produção)*

#### **Método HTTP**
```
GET
```

#### **Headers**
```
Nenhum necessário
```

#### **Parâmetros Query (Opcionais)**

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `limit` | number | Não | `100` | Número máximo de registros (1-1000) |
| `offset` | number | Não | `0` | Deslocamento para paginação (>= 0) |
| `sort_order` | string | Não | `desc` | Direção da ordenação (`asc` ou `desc`) |

#### **Exemplo de Requisição**

```bash
GET http://192.168.100.3:3000/api/players/fame?limit=50&offset=0&sort_order=desc
```

#### **Resposta de Sucesso (200 OK)**

**Status HTTP:** `200`

**Body:**
```json
{
  "success": true,
  "data": {
    "players": [
      {
        "steam_id": "76561198777583030",
        "player_name": "ADM Guns",
        "total_fame": 234.79837,
        "last_updated": "2025-12-02 00:21:39"
      },
      {
        "steam_id": "76561199238464517",
        "player_name": "Pernalonga",
        "total_fame": 200.340378,
        "last_updated": "2025-12-02 00:21:39"
      }
    ],
    "total": 28,
    "limit": 100,
    "offset": 0,
    "count": 28,
    "sort_order": "desc"
  }
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

### **2. Obter Fama de um Jogador Específico**

**GET** `/api/players/{steam_id}/fame`

Obtém o total de fama de um jogador específico pelo Steam ID.

#### **URL Base**
```
http://192.168.100.3:3000/api/players/{steam_id}/fame
```

**Exemplo:**
```
http://192.168.100.3:3000/api/players/76561198777583030/fame
```

#### **Método HTTP**
```
GET
```

#### **Headers**
```
Nenhum necessário
```

#### **Parâmetros**

| Parâmetro | Tipo | Obrigatório | Local | Descrição | Exemplo |
|-----------|------|-------------|-------|-----------|---------|
| `steam_id` | string | ✅ Sim | Path | Steam ID do jogador | `76561198777583030` |

#### **Exemplo de Requisição**

```bash
GET http://192.168.100.3:3000/api/players/76561198777583030/fame
```

#### **Resposta de Sucesso (200 OK)**

**Status HTTP:** `200`

**Body:**
```json
{
  "success": true,
  "data": {
    "steam_id": "76561198777583030",
    "player_name": "ADM Guns",
    "total_fame": 234.79837,
    "last_updated": "2025-12-02 00:21:39"
  }
}
```

#### **Resposta de Erro (404 Not Found)**

**Status HTTP:** `404`

**Body:**
```json
{
  "success": false,
  "error": "Jogador 76561199999999999 não encontrado na tabela de fama"
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

## 🔄 Como Funciona

### **Atualização Automática**

A tabela `player_fame_totals` é atualizada automaticamente em tempo real através do processamento dos logs `famepoints_*.log`:

1. O SCUM Server gera logs `famepoints_*.log` quando há eventos de fama
2. O `FamepointsProcessor` detecta e processa esses logs automaticamente
3. A tabela `player_fame_totals` é atualizada com o total atual de fama
4. Os endpoints API permitem consultar os dados atualizados

### **Suporte a Ganho e Perda de Fama**

O sistema suporta tanto ganho quanto perda de fama:
- **Valores positivos**: Jogador ganhou fama
- **Valores negativos**: Jogador perdeu fama
- **Total**: Sempre reflete o total atual após o evento

---

## 💻 Exemplos de Uso

### **JavaScript/TypeScript (Fetch API)**

```typescript
// Listar todos os jogadores com fama
async function getPlayersFame(limit = 100, offset = 0, sortOrder = 'desc') {
  const response = await fetch(
    `http://192.168.100.3:3000/api/players/fame?limit=${limit}&offset=${offset}&sort_order=${sortOrder}`
  );
  const data = await response.json();
  return data;
}

// Obter fama de um jogador específico
async function getPlayerFame(steamId: string) {
  const response = await fetch(
    `http://192.168.100.3:3000/api/players/${steamId}/fame`
  );
  const data = await response.json();
  return data;
}

// Uso
const allPlayers = await getPlayersFame(50, 0, 'desc');
const playerFame = await getPlayerFame('76561198777583030');
```

### **Python (requests)**

```python
import requests

BASE_URL = "http://192.168.100.3:3000"

# Listar todos os jogadores com fama
def get_players_fame(limit=100, offset=0, sort_order='desc'):
    url = f"{BASE_URL}/api/players/fame"
    params = {
        'limit': limit,
        'offset': offset,
        'sort_order': sort_order
    }
    response = requests.get(url, params=params)
    return response.json()

# Obter fama de um jogador específico
def get_player_fame(steam_id):
    url = f"{BASE_URL}/api/players/{steam_id}/fame"
    response = requests.get(url)
    return response.json()

# Uso
all_players = get_players_fame(limit=50, offset=0, sort_order='desc')
player_fame = get_player_fame('76561198777583030')
```

### **cURL**

```bash
# Listar todos os jogadores com fama
curl -X GET "http://192.168.100.3:3000/api/players/fame?limit=50&offset=0&sort_order=desc"

# Obter fama de um jogador específico
curl -X GET "http://192.168.100.3:3000/api/players/76561198777583030/fame"
```

---

## 📊 Estrutura de Dados

### **Player Fame Object**

```typescript
interface PlayerFame {
  steam_id: string;        // Steam ID único do jogador
  player_name: string;      // Nome do jogador
  total_fame: number;       // Total de fama atual
  last_updated: string;    // Data/hora da última atualização (ISO 8601)
}
```

### **Response Object (List)**

```typescript
interface PlayersFameResponse {
  success: boolean;
  data: {
    players: PlayerFame[];
    total: number;          // Total de jogadores na tabela
    limit: number;          // Limite usado na consulta
    offset: number;         // Offset usado na consulta
    count: number;          // Número de registros retornados
    sort_order: string;     // Ordenação usada ('asc' ou 'desc')
  };
}
```

### **Response Object (Single)**

```typescript
interface PlayerFameResponse {
  success: boolean;
  data: PlayerFame;
}
```

---

## ⚠️ Observações Importantes

1. **Atualização em Tempo Real**: A tabela é atualizada automaticamente sempre que há eventos de fama nos logs
2. **Jogadores Não Encontrados**: Se um jogador não tiver registro na tabela de fama, o endpoint retornará 404
3. **Valores Negativos**: O sistema suporta valores negativos quando o jogador perde fama
4. **Paginação**: Use `limit` e `offset` para paginar grandes listas de jogadores
5. **Ordenação**: Por padrão, os jogadores são ordenados por total de fama em ordem decrescente (maior para menor)

---

## 🔗 Endpoints Relacionados

- **GET /api/players**: Lista todos os jogadores cadastrados
- **GET /api/rankings**: Rankings gerais dos jogadores
- **GET /api/players/{steam_id}**: Informações completas de um jogador

---

## 📞 **Suporte**

Em caso de dúvidas sobre a integração, entre em contato com o time de backend.

