# 🏆 Documentação Frontend - Sistema de Fama dos Jogadores

## 📋 Visão Geral

Esta documentação descreve como implementar a integração com o sistema de **Fama dos Jogadores** do servidor SCUM no frontend. O sistema permite consultar os totais de fama dos jogadores, que são atualizados automaticamente em tempo real através do processamento dos logs do servidor.

### **Características Principais**

- ✅ **Atualização em Tempo Real**: Dados atualizados automaticamente quando há eventos de fama
- ✅ **Paginação**: Suporte completo para listagens paginadas
- ✅ **Ordenação**: Ordenação ascendente ou descendente por total de fama
- ✅ **Valores Negativos**: Suporta perda de fama (valores negativos)
- ✅ **RESTful API**: Endpoints padrão REST com respostas JSON

---

## 🔗 Base URL da API

```
http://192.168.100.3:3000/api
```

**⚠️ Importante**: Substitua pela URL do seu ambiente de produção/desenvolvimento.

---

## 📡 Endpoints Disponíveis

### **1. Listar Todos os Jogadores com Fama**

**GET** `/api/players/fame`

Lista todos os jogadores com seus totais de fama, ordenados por total de fama.

#### **Parâmetros Query (Opcionais)**

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição | Valores Aceitos |
|-----------|------|-------------|--------|-----------|------------------|
| `limit` | number | Não | `100` | Número máximo de registros | 1-1000 |
| `offset` | number | Não | `0` | Deslocamento para paginação | >= 0 |
| `sort_order` | string | Não | `desc` | Direção da ordenação | `asc` ou `desc` |

#### **Exemplo de Requisição**

```typescript
GET /api/players/fame?limit=50&offset=0&sort_order=desc
```

#### **Resposta de Sucesso (200 OK)**

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

#### **Resposta de Erro (500 Internal Server Error)**

```json
{
  "success": false,
  "error": "Mensagem de erro específica"
}
```

---

### **2. Obter Fama de um Jogador Específico**

**GET** `/api/players/{steam_id}/fame`

Obtém o total de fama de um jogador específico pelo Steam ID.

#### **Parâmetros Path**

| Parâmetro | Tipo | Obrigatório | Descrição | Exemplo |
|-----------|------|-------------|-----------|---------|
| `steam_id` | string | ✅ Sim | Steam ID do jogador | `76561198777583030` |

#### **Exemplo de Requisição**

```typescript
GET /api/players/76561198777583030/fame
```

#### **Resposta de Sucesso (200 OK)**

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

```json
{
  "success": false,
  "error": "Jogador 76561199999999999 não encontrado na tabela de fama"
}
```

#### **Resposta de Erro (500 Internal Server Error)**

```json
{
  "success": false,
  "error": "Mensagem de erro específica"
}
```

---

## 💻 Implementação Frontend

### **TypeScript Interfaces**

```typescript
/**
 * Interface para dados de fama de um jogador
 */
interface PlayerFame {
  steam_id: string;        // Steam ID único do jogador
  player_name: string;     // Nome do jogador
  total_fame: number;      // Total de fama atual (pode ser negativo)
  last_updated: string;    // Data/hora da última atualização (ISO 8601)
}

/**
 * Interface para resposta da listagem de jogadores com fama
 */
interface PlayersFameResponse {
  success: boolean;
  data: {
    players: PlayerFame[];
    total: number;          // Total de jogadores na tabela
    limit: number;          // Limite usado na consulta
    offset: number;         // Offset usado na consulta
    count: number;          // Número de registros retornados
    sort_order: 'asc' | 'desc';  // Ordenação usada
  };
}

/**
 * Interface para resposta de um jogador específico
 */
interface PlayerFameResponse {
  success: boolean;
  data: PlayerFame;
}

/**
 * Interface para resposta de erro
 */
interface ErrorResponse {
  success: false;
  error: string;
}
```

---

### **Service/API Client (TypeScript)**

#### **Opção 1: Usando Fetch API**

```typescript
class FameService {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://192.168.100.3:3000/api') {
    this.baseUrl = baseUrl;
  }

  /**
   * Lista todos os jogadores com fama
   */
  async getPlayersFame(
    limit: number = 100,
    offset: number = 0,
    sortOrder: 'asc' | 'desc' = 'desc'
  ): Promise<PlayersFameResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
      sort_order: sortOrder,
    });

    const response = await fetch(`${this.baseUrl}/players/fame?${params}`);
    
    if (!response.ok) {
      const error: ErrorResponse = await response.json();
      throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Obtém fama de um jogador específico
   */
  async getPlayerFame(steamId: string): Promise<PlayerFameResponse> {
    const response = await fetch(`${this.baseUrl}/players/${steamId}/fame`);
    
    if (!response.ok) {
      if (response.status === 404) {
        const error: ErrorResponse = await response.json();
        throw new Error(error.error || 'Jogador não encontrado');
      }
      const error: ErrorResponse = await response.json();
      throw new Error(error.error || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }
}

// Exportar instância singleton
export const fameService = new FameService();
```

#### **Opção 2: Usando Axios**

```typescript
import axios, { AxiosInstance } from 'axios';

class FameService {
  private api: AxiosInstance;

  constructor(baseURL: string = 'http://192.168.100.3:3000/api') {
    this.api = axios.create({
      baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Lista todos os jogadores com fama
   */
  async getPlayersFame(
    limit: number = 100,
    offset: number = 0,
    sortOrder: 'asc' | 'desc' = 'desc'
  ): Promise<PlayersFameResponse> {
    try {
      const response = await this.api.get<PlayersFameResponse>('/players/fame', {
        params: {
          limit,
          offset,
          sort_order: sortOrder,
        },
      });
      return response.data;
    } catch (error: any) {
      if (error.response) {
        throw new Error(error.response.data.error || 'Erro ao buscar jogadores');
      }
      throw new Error('Erro de conexão com o servidor');
    }
  }

  /**
   * Obtém fama de um jogador específico
   */
  async getPlayerFame(steamId: string): Promise<PlayerFameResponse> {
    try {
      const response = await this.api.get<PlayerFameResponse>(
        `/players/${steamId}/fame`
      );
      return response.data;
    } catch (error: any) {
      if (error.response) {
        if (error.response.status === 404) {
          throw new Error('Jogador não encontrado');
        }
        throw new Error(error.response.data.error || 'Erro ao buscar fama do jogador');
      }
      throw new Error('Erro de conexão com o servidor');
    }
  }
}

// Exportar instância singleton
export const fameService = new FameService();
```

---

### **React Hook (Custom Hook)**

```typescript
import { useState, useEffect } from 'react';
import { fameService } from './services/fameService';
import { PlayerFame, PlayersFameResponse, PlayerFameResponse } from './types/fame';

/**
 * Hook para listar jogadores com fama
 */
export function usePlayersFame(
  limit: number = 100,
  offset: number = 0,
  sortOrder: 'asc' | 'desc' = 'desc'
) {
  const [data, setData] = useState<PlayersFameResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fameService.getPlayersFame(limit, offset, sortOrder);
        if (isMounted) {
          setData(response);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Erro ao carregar dados');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [limit, offset, sortOrder]);

  return { data, loading, error };
}

/**
 * Hook para obter fama de um jogador específico
 */
export function usePlayerFame(steamId: string | null) {
  const [data, setData] = useState<PlayerFame | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!steamId) {
      setData(null);
      setLoading(false);
      return;
    }

    let isMounted = true;

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fameService.getPlayerFame(steamId);
        if (isMounted) {
          setData(response.data);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Erro ao carregar fama do jogador');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [steamId]);

  return { data, loading, error };
}
```

---

### **Componente React - Lista de Jogadores com Fama**

```typescript
import React, { useState } from 'react';
import { usePlayersFame } from './hooks/usePlayersFame';

interface FameRankingProps {
  itemsPerPage?: number;
}

export const FameRanking: React.FC<FameRankingProps> = ({ itemsPerPage = 50 }) => {
  const [page, setPage] = useState(0);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  
  const offset = page * itemsPerPage;
  const { data, loading, error } = usePlayersFame(itemsPerPage, offset, sortOrder);

  const handleSortToggle = () => {
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    setPage(0); // Resetar para primeira página ao mudar ordenação
  };

  const handleNextPage = () => {
    if (data && offset + itemsPerPage < data.data.total) {
      setPage(prev => prev + 1);
    }
  };

  const handlePrevPage = () => {
    if (page > 0) {
      setPage(prev => prev - 1);
    }
  };

  const formatFame = (fame: number): string => {
    return fame.toFixed(2);
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('pt-BR');
  };

  if (loading) {
    return <div className="loading">Carregando ranking de fama...</div>;
  }

  if (error) {
    return <div className="error">Erro: {error}</div>;
  }

  if (!data || data.data.players.length === 0) {
    return <div className="empty">Nenhum jogador encontrado</div>;
  }

  return (
    <div className="fame-ranking">
      <div className="fame-ranking-header">
        <h2>🏆 Ranking de Fama</h2>
        <button onClick={handleSortToggle}>
          Ordenar: {sortOrder === 'desc' ? 'Maior → Menor' : 'Menor → Maior'}
        </button>
      </div>

      <table className="fame-table">
        <thead>
          <tr>
            <th>Posição</th>
            <th>Jogador</th>
            <th>Total de Fama</th>
            <th>Última Atualização</th>
          </tr>
        </thead>
        <tbody>
          {data.data.players.map((player, index) => (
            <tr key={player.steam_id}>
              <td>{offset + index + 1}</td>
              <td>{player.player_name}</td>
              <td className={player.total_fame < 0 ? 'negative' : 'positive'}>
                {formatFame(player.total_fame)}
              </td>
              <td>{formatDate(player.last_updated)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pagination">
        <button 
          onClick={handlePrevPage} 
          disabled={page === 0}
        >
          Anterior
        </button>
        <span>
          Página {page + 1} de {Math.ceil(data.data.total / itemsPerPage)}
          {' '}({data.data.count} de {data.data.total} jogadores)
        </span>
        <button 
          onClick={handleNextPage}
          disabled={offset + itemsPerPage >= data.data.total}
        >
          Próxima
        </button>
      </div>
    </div>
  );
};
```

---

### **Componente React - Card de Fama do Jogador**

```typescript
import React from 'react';
import { usePlayerFame } from './hooks/usePlayerFame';

interface PlayerFameCardProps {
  steamId: string;
}

export const PlayerFameCard: React.FC<PlayerFameCardProps> = ({ steamId }) => {
  const { data, loading, error } = usePlayerFame(steamId);

  if (loading) {
    return <div className="loading">Carregando fama...</div>;
  }

  if (error) {
    return <div className="error">Erro: {error}</div>;
  }

  if (!data) {
    return <div className="empty">Jogador não encontrado</div>;
  }

  const formatFame = (fame: number): string => {
    return fame.toFixed(2);
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('pt-BR');
  };

  return (
    <div className="player-fame-card">
      <h3>🏆 Fama de {data.player_name}</h3>
      <div className="fame-value">
        <span className={data.total_fame < 0 ? 'negative' : 'positive'}>
          {formatFame(data.total_fame)}
        </span>
      </div>
      <div className="last-updated">
        Última atualização: {formatDate(data.last_updated)}
      </div>
      <div className="steam-id">
        Steam ID: {data.steam_id}
      </div>
    </div>
  );
};
```

---

## 🎨 Exemplos de Estilos CSS

```css
/* Ranking de Fama */
.fame-ranking {
  padding: 20px;
}

.fame-ranking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.fame-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
}

.fame-table th,
.fame-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.fame-table th {
  background-color: #f5f5f5;
  font-weight: bold;
}

.fame-table tr:hover {
  background-color: #f9f9f9;
}

.fame-table .positive {
  color: #28a745;
  font-weight: bold;
}

.fame-table .negative {
  color: #dc3545;
  font-weight: bold;
}

/* Paginação */
.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background-color: #fff;
  cursor: pointer;
  border-radius: 4px;
}

.pagination button:hover:not(:disabled) {
  background-color: #f5f5f5;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Card de Fama */
.player-fame-card {
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.player-fame-card h3 {
  margin-top: 0;
}

.fame-value {
  font-size: 2em;
  font-weight: bold;
  margin: 20px 0;
}

.fame-value .positive {
  color: #28a745;
}

.fame-value .negative {
  color: #dc3545;
}

.last-updated,
.steam-id {
  color: #666;
  font-size: 0.9em;
  margin-top: 10px;
}

/* Estados de Loading e Erro */
.loading {
  padding: 20px;
  text-align: center;
  color: #666;
}

.error {
  padding: 20px;
  background-color: #fee;
  color: #c33;
  border-radius: 4px;
}

.empty {
  padding: 20px;
  text-align: center;
  color: #999;
}
```

---

## 🔄 Atualização em Tempo Real (Polling)

Se você quiser atualizar os dados automaticamente, pode usar polling:

```typescript
import { useEffect, useRef } from 'react';
import { usePlayersFame } from './hooks/usePlayersFame';

export const FameRankingAutoRefresh: React.FC = () => {
  const [refreshInterval, setRefreshInterval] = useState<number>(30000); // 30 segundos
  const { data, loading, error, refetch } = usePlayersFame(50, 0, 'desc');
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Configurar polling
    intervalRef.current = setInterval(() => {
      refetch();
    }, refreshInterval);

    // Limpar intervalo ao desmontar
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [refreshInterval, refetch]);

  return (
    <div>
      <label>
        Intervalo de atualização (ms):
        <input
          type="number"
          value={refreshInterval}
          onChange={(e) => setRefreshInterval(Number(e.target.value))}
          min="5000"
          step="1000"
        />
      </label>
      {/* Renderizar dados */}
    </div>
  );
};
```

---

## ⚠️ Tratamento de Erros

### **Erros Comuns e Como Tratá-los**

```typescript
try {
  const response = await fameService.getPlayersFame();
  // Processar dados
} catch (error: any) {
  if (error.message.includes('não encontrado')) {
    // Jogador não encontrado (404)
    console.error('Jogador não encontrado na tabela de fama');
  } else if (error.message.includes('conexão')) {
    // Erro de conexão
    console.error('Erro de conexão com o servidor');
  } else {
    // Outro erro
    console.error('Erro desconhecido:', error.message);
  }
}
```

---

## 📊 Casos de Uso

### **1. Ranking de Fama (Top 10)**

```typescript
const { data } = usePlayersFame(10, 0, 'desc');
// Retorna os top 10 jogadores com mais fama
```

### **2. Buscar Fama de um Jogador Específico**

```typescript
const { data } = usePlayerFame('76561198777583030');
// Retorna a fama do jogador específico
```

### **3. Paginação Completa**

```typescript
const [page, setPage] = useState(0);
const itemsPerPage = 25;
const { data } = usePlayersFame(itemsPerPage, page * itemsPerPage, 'desc');
// Implementa paginação com 25 itens por página
```

### **4. Ordenação Alternada**

```typescript
const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
const { data } = usePlayersFame(100, 0, sortOrder);
// Permite alternar entre maior→menor e menor→maior
```

---

## 🎯 Boas Práticas

1. **Cache de Dados**: Considere implementar cache para reduzir requisições desnecessárias
2. **Loading States**: Sempre mostre estados de carregamento para melhor UX
3. **Error Handling**: Trate todos os possíveis erros (404, 500, timeout, etc.)
4. **Paginação**: Use paginação para grandes listas (recomendado: 25-50 itens por página)
5. **Formatação**: Formate números de fama com 2 casas decimais para melhor legibilidade
6. **Valores Negativos**: Destaque visualmente valores negativos (perda de fama)
7. **Atualização**: Considere polling apenas se necessário (evite sobrecarregar o servidor)

---

## 🔗 Endpoints Relacionados

- **GET /api/players**: Lista todos os jogadores cadastrados
- **GET /api/rankings**: Rankings gerais dos jogadores
- **GET /api/players/{steam_id}**: Informações completas de um jogador

---

## 📞 Suporte

Em caso de dúvidas sobre a integração, entre em contato com o time de backend.

---

## 📝 Notas Importantes

1. **Atualização Automática**: Os dados são atualizados automaticamente pelo backend quando há eventos de fama nos logs do servidor SCUM
2. **Valores Negativos**: O sistema suporta valores negativos quando o jogador perde fama
3. **Steam ID**: O `steam_id` é o identificador único do jogador (formato: 17 dígitos)
4. **Timezone**: As datas são retornadas no formato ISO 8601 (UTC)
5. **Rate Limiting**: Considere implementar rate limiting no frontend para evitar requisições excessivas

---

## ✅ Checklist de Implementação

- [ ] Configurar base URL da API
- [ ] Criar interfaces TypeScript
- [ ] Implementar service/API client
- [ ] Criar hooks customizados (se usar React)
- [ ] Implementar componentes de UI
- [ ] Adicionar tratamento de erros
- [ ] Implementar estados de loading
- [ ] Adicionar estilos CSS
- [ ] Testar paginação
- [ ] Testar ordenação
- [ ] Testar tratamento de erros (404, 500)
- [ ] Implementar formatação de números
- [ ] Adicionar indicadores visuais para valores negativos
- [ ] Testar em diferentes dispositivos/resoluções

---

**Versão da Documentação**: 1.0  
**Última Atualização**: 2025-12-02

