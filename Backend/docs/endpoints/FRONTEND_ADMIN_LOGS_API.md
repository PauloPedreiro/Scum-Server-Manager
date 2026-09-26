# 👨‍💼 API de Admin Logs - Documentação Frontend

## 📋 Visão Geral

Esta documentação descreve o endpoint da API para consulta dos últimos comandos de administradores processados pelo sistema. O endpoint permite:

- Listar os comandos admin mais recentes
- Controlar a quantidade de comandos retornados
- Acessar informações completas de cada comando (jogador, ação, categoria, timestamp)
- Obter metadados sobre o total de comandos no sistema

---

## 🌐 Base URL

```
http://localhost:3000/api
```

**⚠️ Nota:** Em produção, substitua `localhost:3000` pela URL do servidor backend.

---

## 🔌 Endpoint: Últimos Comandos Admin

### **Descrição**

Retorna os últimos comandos de administradores processados pelo sistema, ordenados do mais recente para o mais antigo.

### **Endpoint**
```
GET /api/admin-logs/recent
```

### **Query Parameters (Opcionais)**

| Parâmetro | Tipo | Obrigatório | Descrição | Padrão | Exemplo |
|-----------|------|-------------|-----------|--------|---------|
| `limit` | `number` | ❌ Não | Número máximo de comandos a retornar (**1-200**) | `10` | `?limit=20` |
| `include_total` | `boolean` | ❌ Não | Se `true`, inclui `total` (count) na resposta | `false` | `?include_total=true` |
| `category` | `string` | ❌ Não | Filtra por categoria (pode repetir o parâmetro) | - | `?category=teleport&category=spawn` |
| `steam_id` | `string` | ❌ Não | Filtra por SteamID do admin | - | `?steam_id=7656...` |
| `player_name` | `string` | ❌ Não | Filtra por nome do admin (contains) | - | `?player_name=dracula` |
| `q` | `string` | ❌ Não | Busca textual em `action` (contains) | - | `?q=spawnvehicle` |

### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "data": {
    "commands": [
      {
        "command_id": "2025.11.01-14:30:15:76561198040636105",
        "timestamp": "2025-11-01T14:30:15",
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "action": "SpawnItem Phoenix_Tears",
        "event_type": "command",
        "category": {
          "key": "spawn",
          "name": "Spawn",
          "emoji": "🎁",
          "color": "#f1c40f"
        }
      },
      {
        "command_id": "2025.11.01-14:25:42:76561198040636105",
        "timestamp": "2025-11-01T14:25:42",
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "action": "Teleport 100 200",
        "event_type": "command",
        "category": {
          "key": "teleport",
          "name": "Teleport",
          "emoji": "🚀",
          "color": "#9b59b6"
        }
      }
    ],
    "total": 156,
    "limit": 10
  },
  "timestamp": 1730455200.123456
}
```

### **Campos da Resposta**

#### **Comando (`command`)**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `command_id` | `string` | ID único do comando (timestamp:steam_id) |
| `timestamp` | `string` | Data e hora do comando (ISO 8601) |
| `steam_id` | `string` | Steam ID do administrador |
| `player_name` | `string` | Nome do jogador que executou o comando |
| `action` | `string` | Comando executado (ex: "SpawnItem Phoenix_Tears") |
| `event_type` | `string \| null` | Tipo do evento (ex: `command`, `map_teleport_player`, `map_teleport_vehicle`) |
| `category` | `object` | Informações da categoria do comando |

#### **Categoria (`category`)**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `key` | `string` | Chave da categoria (ex: `spawn`, `teleport`) |
| `name` | `string` | Nome da categoria (ex: "Spawn Item", "Teleport") |
| `emoji` | `string` | Emoji representativo da categoria |
| `color` | `string` | Cor hexadecimal para exibição (com #) |

#### **Metadados**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `total` | `number \| null` | Total de comandos processados (só vem se `include_total=true`) |
| `limit` | `number` | Quantidade de comandos retornados nesta requisição |

### **Categorias de Comandos**

| Categoria | Emoji | Cor | Descrição |
|-----------|-------|-----|-----------|
| **Teleport** (`teleport`) | 🚀 | `#9b59b6` | Comandos de teleporte |
| **Spawn** (`spawn`) | 🎁 | `#f1c40f` | Spawn/Destroy de itens/veículos/zombies |
| **God Mode** (`godmode`) | 🛡️ | `#e74c3c` | Comandos de god mode |
| **Game Info** (`info`) | 👁️ | `#3498db` | Comandos `Show*` / `List*` |
| **Server Punishments** (`punishments`) | 🔨 | `#e67e22` | Ban/Kick/Mute/Unban/Unmute |
| **Other** (`other`) | 📋 | `#2ecc71` | Outros comandos |

### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "Sistema de logs não inicializado"
}
```

```json
{
  "success": false,
  "error": "Sistema de admin logs não inicializado"
}
```

---

## 📊 Estruturas TypeScript

### **AdminCommand**
```typescript
interface AdminCommand {
  command_id: string;
  timestamp: string; // ISO 8601
  steam_id: string;
  player_name: string;
  action: string;
  event_type: string | null;
  category: CommandCategory;
}

interface CommandCategory {
  key: string;
  name: string;
  emoji: string;
  color: string; // Hex color com #
}

interface AdminLogsRecentResponse {
  success: boolean;
  data: {
    commands: AdminCommand[];
    total: number | null;
    limit: number;
  };
  timestamp: number;
  error?: string;
}
```

---

## 💻 Exemplos de Implementação

### **React com TypeScript**

```typescript
import { useState, useEffect } from 'react';

const API_BASE_URL = 'http://localhost:3000/api';

// Hook para buscar comandos admin recentes
function useAdminLogsRecent(limit: number = 10) {
  const [commands, setCommands] = useState<AdminCommand[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const fetchCommands = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `${API_BASE_URL}/admin-logs/recent?limit=${limit}`
        );
        const data: AdminLogsRecentResponse = await response.json();

        if (data.success && data.data) {
          setCommands(data.data.commands);
          setTotal(data.data.total);
        } else {
          setError(data.error || 'Erro ao carregar comandos');
        }
      } catch (err) {
        setError('Erro de conexão');
      } finally {
        setLoading(false);
      }
    };

    fetchCommands();
    // Atualizar a cada 30 segundos
    const interval = setInterval(fetchCommands, 30000);

    return () => clearInterval(interval);
  }, [limit]);

  return { commands, loading, error, total };
}

// Componente de exibição
function AdminLogsList({ limit = 10 }: { limit?: number }) {
  const { commands, loading, error, total } = useAdminLogsRecent(limit);

  if (loading) return <div>Carregando comandos...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div className="admin-logs">
      <h2>Comandos Admin Recentes</h2>
      <p>Total de comandos: {total}</p>

      <div className="commands-list">
        {commands.map((cmd) => (
          <div
            key={cmd.command_id}
            className="command-card"
            style={{ borderLeft: `4px solid ${cmd.category.color}` }}
          >
            <div className="command-header">
              <span className="category-emoji">{cmd.category.emoji}</span>
              <span className="category-name">{cmd.category.name}</span>
              <span className="timestamp">
                {new Date(cmd.timestamp).toLocaleString('pt-BR')}
              </span>
            </div>

            <div className="command-body">
              <p><strong>Admin:</strong> {cmd.player_name}</p>
              <p><strong>Steam ID:</strong> {cmd.steam_id}</p>
              <p><strong>Comando:</strong> {cmd.action}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### **Vue.js com TypeScript**

```vue
<template>
  <div class="admin-logs">
    <h2>Comandos Admin Recentes</h2>
    <p v-if="total">Total de comandos: {{ total }}</p>

    <div v-if="loading">Carregando...</div>
    <div v-else-if="error">Erro: {{ error }}</div>
    <div v-else class="commands-list">
      <div
        v-for="cmd in commands"
        :key="cmd.command_id"
        class="command-card"
        :style="{ borderLeft: `4px solid ${cmd.category.color}` }"
      >
        <div class="command-header">
          <span>{{ cmd.category.emoji }}</span>
          <span>{{ cmd.category.name }}</span>
          <span>{{ formatDate(cmd.timestamp) }}</span>
        </div>
        <div class="command-body">
          <p><strong>Admin:</strong> {{ cmd.player_name }}</p>
          <p><strong>Steam ID:</strong> {{ cmd.steam_id }}</p>
          <p><strong>Comando:</strong> {{ cmd.action }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

const API_BASE_URL = 'http://localhost:3000/api';
const props = defineProps<{ limit?: number }>();

const commands = ref<AdminCommand[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const total = ref(0);

const fetchCommands = async () => {
  loading.value = true;
  error.value = null;

  try {
    const response = await fetch(
      `${API_BASE_URL}/admin-logs/recent?limit=${props.limit || 10}`
    );
    const data: AdminLogsRecentResponse = await response.json();

    if (data.success && data.data) {
      commands.value = data.data.commands;
      total.value = data.data.total;
    } else {
      error.value = data.error || 'Erro ao carregar comandos';
    }
  } catch (err) {
    error.value = 'Erro de conexão';
  } finally {
    loading.value = false;
  }
};

const formatDate = (dateStr: string): string => {
  return new Date(dateStr).toLocaleString('pt-BR');
};

onMounted(() => {
  fetchCommands();
  setInterval(fetchCommands, 30000); // Atualizar a cada 30s
});
</script>
```

---

### **JavaScript (Vanilla)**

```javascript
const API_BASE_URL = 'http://localhost:3000/api';

// Função para buscar comandos admin recentes
async function getAdminLogsRecent(limit = 10) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/admin-logs/recent?limit=${limit}`
    );
    const data = await response.json();

    if (data.success) {
      console.log(`Total de comandos: ${data.data.total}`);
      console.log(`Comandos retornados: ${data.data.commands.length}`);
      
      // Processar comandos
      data.data.commands.forEach((cmd) => {
        console.log(`${cmd.category.emoji} ${cmd.category.name}`);
        console.log(`  Admin: ${cmd.player_name} (${cmd.steam_id})`);
        console.log(`  Comando: ${cmd.action}`);
        console.log(`  Data: ${new Date(cmd.timestamp).toLocaleString('pt-BR')}`);
        console.log('---');
      });

      return data.data.commands;
    } else {
      console.error('Erro:', data.error);
      return [];
    }
  } catch (error) {
    console.error('Erro de conexão:', error);
    return [];
  }
}

// Exemplo de uso
getAdminLogsRecent(20).then((commands) => {
  console.log(`Recebidos ${commands.length} comandos`);
});
```

---

## ✅ Boas Práticas

### **1. Polling Inteligente**
- Atualize a lista a cada 30-60 segundos
- Pare o polling quando o componente não estiver visível
- Aumente o intervalo se não houver novos comandos

```typescript
// Exemplo de polling condicional
useEffect(() => {
  const interval = commands.length > 0 
    ? 30000  // 30s se há comandos
    : 60000; // 60s se não há comandos
    
  const timer = setInterval(fetchCommands, interval);
  return () => clearInterval(timer);
}, [commands.length]);
```

### **2. Paginação**
- Use o campo `total` para implementar paginação
- Permita ao usuário escolher quantos comandos visualizar
- Considere implementar "carregar mais"

```typescript
const [page, setPage] = useState(1);
const LIMIT_PER_PAGE = 20;

const fetchCommands = async () => {
  const response = await fetch(
    `${API_BASE_URL}/admin-logs/recent?limit=${LIMIT_PER_PAGE * page}`
  );
  // ...
};
```

### **3. Formatação de Data**
- Converta o timestamp ISO 8601 para formato amigável
- Use timezone do usuário
- Mostre tempo relativo quando relevante (ex: "há 5 minutos")

```typescript
function formatCommandTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Agora';
  if (diffMins < 60) return `Há ${diffMins} minuto(s)`;
  if (diffMins < 1440) return `Há ${Math.floor(diffMins / 60)} hora(s)`;
  
  return date.toLocaleString('pt-BR');
}
```

### **4. Estilização por Categoria**
- Use a cor retornada para destacar visualmente
- Mostre o emoji da categoria
- Crie badges/etiquetas coloridas

```css
.command-card {
  border-left: 4px solid var(--category-color);
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: 4px;
  background: #f9f9f9;
}

.category-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  background-color: var(--category-color);
  color: white;
  font-size: 0.875rem;
}
```

### **5. Tratamento de Erros**
- Sempre verifique o campo `success` antes de usar os dados
- Exiba mensagens amigáveis para o usuário
- Implemente retry automático para erros temporários

```typescript
const fetchWithRetry = async (retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url);
      const data = await response.json();
      if (data.success) return data;
    } catch (err) {
      if (i === retries - 1) throw err;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
};
```

### **6. Performance**
- Limite a quantidade inicial (ex: 10-20 comandos)
- Implemente lazy loading para listas longas
- Use `React.memo` ou `useMemo` para evitar re-renders desnecessários

---

## 📝 Exemplo de Componente Completo (React)

```typescript
import React, { useState, useEffect } from 'react';
import './AdminLogs.css';

interface AdminCommand {
  command_id: string;
  timestamp: string;
  steam_id: string;
  player_name: string;
  action: string;
  category: {
    name: string;
    emoji: string;
    color: string;
  };
}

const API_BASE_URL = 'http://localhost:3000/api';

export function AdminLogsRecent() {
  const [commands, setCommands] = useState<AdminCommand[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(10);

  const fetchCommands = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/admin-logs/recent?limit=${limit}`
      );
      const data = await response.json();

      if (data.success && data.data) {
        setCommands(data.data.commands);
        setTotal(data.data.total);
      } else {
        setError(data.error || 'Erro ao carregar comandos');
      }
    } catch (err) {
      setError('Erro de conexão com o servidor');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCommands();
    const interval = setInterval(fetchCommands, 30000);
    return () => clearInterval(interval);
  }, [limit]);

  const formatTime = (timestamp: string): string => {
    return new Date(timestamp).toLocaleString('pt-BR');
  };

  if (loading && commands.length === 0) {
    return <div className="loading">Carregando comandos...</div>;
  }

  if (error) {
    return <div className="error">Erro: {error}</div>;
  }

  return (
    <div className="admin-logs-recent">
      <div className="header">
        <h2>Comandos Admin Recentes</h2>
        <div className="controls">
          <label>
            Mostrar:
            <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </label>
          <span className="total">Total: {total}</span>
        </div>
      </div>

      <div className="commands-list">
        {commands.length === 0 ? (
          <p className="empty">Nenhum comando encontrado</p>
        ) : (
          commands.map((cmd) => (
            <div
              key={cmd.command_id}
              className="command-card"
              style={{ borderLeftColor: cmd.category.color }}
            >
              <div className="command-header">
                <span className="category">
                  {cmd.category.emoji} {cmd.category.name}
                </span>
                <span className="timestamp">{formatTime(cmd.timestamp)}</span>
              </div>
              <div className="command-body">
                <div className="admin-info">
                  <strong>{cmd.player_name}</strong>
                  <span className="steam-id">({cmd.steam_id})</span>
                </div>
                <div className="action">{cmd.action}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

---

## 🎨 Exemplo de CSS

```css
.admin-logs-recent {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.controls {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.commands-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.command-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  border-left: 4px solid;
  transition: transform 0.2s;
}

.command-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.command-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #eee;
}

.category {
  font-weight: 600;
  font-size: 1.1rem;
}

.timestamp {
  color: #666;
  font-size: 0.875rem;
}

.command-body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.admin-info {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.steam-id {
  color: #666;
  font-size: 0.875rem;
}

.action {
  font-family: 'Courier New', monospace;
  background: #f5f5f5;
  padding: 0.5rem;
  border-radius: 4px;
  color: #333;
}

.loading,
.error,
.empty {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.error {
  color: #e74c3c;
}
```

---

## ⚠️ Observações Importantes

1. **Timestamp**: O campo `timestamp` está em formato ISO 8601, converta para exibição
2. **Command ID**: Use como chave única em listas React/Vue
3. **Cores**: As cores já vêm em formato hexadecimal com `#`, use diretamente em CSS
4. **Emojis**: Os emojis são strings, podem ser exibidos diretamente
5. **Vazio**: Se não houver comandos, o array `commands` estará vazio (não será `null`)
6. **Limite**: O limite máximo recomendado é 100 comandos por requisição
7. **Atualização**: Comandos são adicionados em tempo real, considere polling regular

---

**Última atualização**: 2025-11-01  
**Versão da API**: 1.12.0

