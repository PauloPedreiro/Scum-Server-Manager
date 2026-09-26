# 🚩 API de Bandeiras (Flags) - Documentação Frontend

## 📋 Visão Geral

Esta documentação descreve o endpoint da API para listar todas as **bandeiras (flags)** do mapa do servidor SCUM com suas localizações e informações de proprietário.

**Funcionalidades:**
- Listar todas as bandeiras do mapa
- Obter coordenadas (x, y, z) de cada bandeira
- Identificar o proprietário (owner) de cada bandeira
- Identificar bandeiras sem proprietário ("no owner")
- Obter informações da base associada à bandeira
- Obter informações do squad do proprietário

**⚠️ Importante:** Este endpoint consulta diretamente o `SCUM.db` em tempo real, então os dados sempre refletem o estado atual do servidor.

---

## 🌐 Base URL

```
http://localhost:3000/api
```

**⚠️ Nota:** Em produção, substitua `localhost:3000` pela URL do servidor backend.

---

## 📊 Estruturas TypeScript

### **FlagLocation**
```typescript
interface FlagLocation {
  x: number;
  y: number;
  z: number;
}
```

### **BaseLocation**
```typescript
interface BaseLocation {
  x: number;
  y: number;
}
```

### **Base**
```typescript
interface Base {
  id: number;
  name: string;
  location: BaseLocation | null;
}
```

### **Flag**
```typescript
interface Flag {
  element_id: number;
  location: FlagLocation;
  base: Base | null;
  owner: string; // String formatada ou "no owner"
  owner_profile_id: number | null;
  owner_steam_id: string | null;
  owner_name: string | null;
  squad_id: number | null;
  squad_name: string | null;
  overtake_end_time: number | null;
  overtaker_user_profile_id: number | null;
}
```

### **FlagsResponse**
```typescript
interface FlagsResponse {
  success: boolean;
  data: {
    flags: Flag[];
    total: number;
    with_owner: number;
    no_owner: number;
  };
}
```

### **ErrorResponse**
```typescript
interface ErrorResponse {
  success: false;
  error: string;
}
```

---

## 🔌 Endpoints

### **1. Listar Todas as Bandeiras**

#### **Request**

```http
GET /api/flags
```

**Headers:**
- Nenhum obrigatório

**Query Parameters:**
- Nenhum suportado

**Exemplo:**
```typescript
const response = await fetch('/api/flags');
const data: FlagsResponse = await response.json();
```

#### **Response (200 OK)**

```json
{
  "success": true,
  "data": {
    "flags": [
      {
        "element_id": 2,
        "location": {
          "x": 501103.75,
          "y": -228677.21875,
          "z": 5156.22802734375
        },
        "base": {
          "id": 3,
          "name": "Base #3",
          "location": {
            "x": 501103.75,
            "y": -228677.21875
          }
        },
        "owner": "NomeJogador (76561198040636105) - Squad: NomeSquad",
        "owner_profile_id": 304,
        "owner_steam_id": "76561198040636105",
        "owner_name": "NomeJogador",
        "squad_id": 5,
        "squad_name": "NomeSquad",
        "overtake_end_time": null,
        "overtaker_user_profile_id": null
      },
      {
        "element_id": 16569,
        "location": {
          "x": 121548.92,
          "y": -92814.97,
          "z": 12345.67
        },
        "base": {
          "id": 49,
          "name": "Base #49",
          "location": {
            "x": 121548.92,
            "y": -92814.97
          }
        },
        "owner": "no owner",
        "owner_profile_id": null,
        "owner_steam_id": null,
        "owner_name": null,
        "squad_id": null,
        "squad_name": null,
        "overtake_end_time": null,
        "overtaker_user_profile_id": null
      }
    ],
    "total": 75,
    "with_owner": 56,
    "no_owner": 19
  }
}
```

#### **Response (500 Internal Server Error)**

```json
{
  "success": false,
  "error": "SCUM.db não encontrado"
}
```

**Possíveis erros:**
- `"SCUM.db não encontrado"`: O arquivo do banco de dados do SCUM não foi encontrado
- `"SquadSyncService não inicializado"`: O serviço não foi inicializado corretamente
- Outros erros de conexão ou SQL serão retornados na mensagem de erro

---

## 📝 Descrição dos Campos

### **Estrutura Principal**

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `success` | `boolean` | Indica sucesso da requisição |
| `data` | `object` | Objeto contendo os dados das bandeiras |
| `data.flags` | `Flag[]` | Array com todas as bandeiras do mapa |
| `data.total` | `number` | Total de bandeiras no mapa |
| `data.with_owner` | `number` | Quantidade de bandeiras com proprietário |
| `data.no_owner` | `number` | Quantidade de bandeiras sem proprietário |

### **Estrutura de uma Bandeira (Flag)**

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `element_id` | `number` | ID único do elemento (bandeira) no SCUM |
| `location` | `FlagLocation` | Coordenadas da bandeira no mapa |
| `location.x` | `number` | Coordenada X (longitude) |
| `location.y` | `number` | Coordenada Y (latitude) |
| `location.z` | `number` | Coordenada Z (altura/elevação) |
| `base` | `Base \| null` | Informações da base associada (null se não houver) |
| `base.id` | `number` | ID da base |
| `base.name` | `string` | Nome da base (ex: "Base #3") |
| `base.location` | `BaseLocation \| null` | Coordenadas do centro da base |
| `owner` | `string` | String formatada com owner ou `"no owner"` |
| `owner_profile_id` | `number \| null` | ID do perfil do owner no SCUM |
| `owner_steam_id` | `string \| null` | Steam ID do owner |
| `owner_name` | `string \| null` | Nome do owner |
| `squad_id` | `number \| null` | ID do squad do owner |
| `squad_name` | `string \| null` | Nome do squad do owner |
| `overtake_end_time` | `number \| null` | Timestamp de quando a bandeira foi capturada |
| `overtaker_user_profile_id` | `number \| null` | ID do perfil que capturou a bandeira |

### **Formato do Campo `owner`**

O campo `owner` é uma string formatada que pode ter os seguintes formatos:

1. **Com owner e squad**: 
   ```
   "NomeJogador (76561198040636105) - Squad: NomeSquad"
   ```

2. **Com owner sem squad**: 
   ```
   "NomeJogador (76561198040636105)"
   ```
   ou
   ```
   "NomeJogador"
   ```

3. **Sem owner**: 
   ```
   "no owner"
   ```

---

## 💻 Exemplos de Implementação

### **1. Função Básica (TypeScript/JavaScript)**

```typescript
async function fetchFlags(): Promise<FlagsResponse> {
  const response = await fetch('/api/flags');
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  const data: FlagsResponse = await response.json();
  
  if (!data.success) {
    throw new Error(data.error || 'Erro desconhecido');
  }
  
  return data;
}

// Uso
try {
  const flagsData = await fetchFlags();
  console.log(`Total de bandeiras: ${flagsData.data.total}`);
  console.log(`Com owner: ${flagsData.data.with_owner}`);
  console.log(`Sem owner: ${flagsData.data.no_owner}`);
} catch (error) {
  console.error('Erro ao buscar bandeiras:', error);
}
```

### **2. React Hook com useState/useEffect**

```typescript
import { useState, useEffect } from 'react';

function useFlags() {
  const [flags, setFlags] = useState<Flag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    total: 0,
    with_owner: 0,
    no_owner: 0
  });

  useEffect(() => {
    async function loadFlags() {
      try {
        setLoading(true);
        setError(null);
        
        const data = await fetchFlags();
        setFlags(data.data.flags);
        setStats({
          total: data.data.total,
          with_owner: data.data.with_owner,
          no_owner: data.data.no_owner
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro desconhecido');
      } finally {
        setLoading(false);
      }
    }

    loadFlags();
    
    // Atualizar a cada 30 segundos
    const interval = setInterval(loadFlags, 30000);
    return () => clearInterval(interval);
  }, []);

  return { flags, loading, error, stats };
}

// Uso no componente
function FlagsMap() {
  const { flags, loading, error, stats } = useFlags();

  if (loading) return <div>Carregando bandeiras...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div>
      <h2>Bandeiras no Mapa ({stats.total})</h2>
      <p>Com owner: {stats.with_owner} | Sem owner: {stats.no_owner}</p>
      
      {flags.map(flag => (
        <div key={flag.element_id}>
          <h3>Bandeira #{flag.element_id}</h3>
          <p>Localização: ({flag.location.x}, {flag.location.y}, {flag.location.z})</p>
          <p>Owner: {flag.owner}</p>
          {flag.base && <p>Base: {flag.base.name}</p>}
          {flag.squad_name && <p>Squad: {flag.squad_name}</p>}
        </div>
      ))}
    </div>
  );
}
```

### **3. React Query (TanStack Query)**

```typescript
import { useQuery } from '@tanstack/react-query';

function useFlags() {
  return useQuery({
    queryKey: ['flags'],
    queryFn: async () => {
      const response = await fetch('/api/flags');
      if (!response.ok) {
        throw new Error('Erro ao buscar bandeiras');
      }
      const data: FlagsResponse = await response.json();
      if (!data.success) {
        throw new Error(data.error || 'Erro desconhecido');
      }
      return data.data;
    },
    refetchInterval: 30000, // Atualizar a cada 30 segundos
    staleTime: 15000, // Considerar dados "frescos" por 15 segundos
  });
}

// Uso no componente
function FlagsMap() {
  const { data, isLoading, error } = useFlags();

  if (isLoading) return <div>Carregando bandeiras...</div>;
  if (error) return <div>Erro: {error.message}</div>;
  if (!data) return null;

  return (
    <div>
      <h2>Bandeiras no Mapa ({data.total})</h2>
      <p>Com owner: {data.with_owner} | Sem owner: {data.no_owner}</p>
      
      {data.flags.map(flag => (
        <div key={flag.element_id}>
          {/* Renderizar bandeira */}
        </div>
      ))}
    </div>
  );
}
```

### **4. Filtrar Bandeiras**

```typescript
// Filtrar bandeiras sem owner
function getNoOwnerFlags(flags: Flag[]): Flag[] {
  return flags.filter(flag => flag.owner === "no owner");
}

// Filtrar bandeiras de um squad específico
function getSquadFlags(flags: Flag[], squadId: number): Flag[] {
  return flags.filter(flag => flag.squad_id === squadId);
}

// Filtrar bandeiras de um owner específico
function getOwnerFlags(flags: Flag[], steamId: string): Flag[] {
  return flags.filter(flag => flag.owner_steam_id === steamId);
}

// Filtrar bandeiras de uma base específica
function getBaseFlags(flags: Flag[], baseId: number): Flag[] {
  return flags.filter(flag => flag.base?.id === baseId);
}

// Uso
const { data } = useFlags();
if (data) {
  const noOwnerFlags = getNoOwnerFlags(data.flags);
  const squad5Flags = getSquadFlags(data.flags, 5);
  const ownerFlags = getOwnerFlags(data.flags, "76561198040636105");
}
```

### **5. Plotar Bandeiras no Mapa**

```typescript
interface MapMarker {
  id: number;
  x: number;
  y: number;
  z: number;
  owner: string;
  hasOwner: boolean;
  squadName: string | null;
  baseName: string | null;
}

function convertFlagsToMarkers(flags: Flag[]): MapMarker[] {
  return flags.map(flag => ({
    id: flag.element_id,
    x: flag.location.x,
    y: flag.location.y,
    z: flag.location.z,
    owner: flag.owner,
    hasOwner: flag.owner !== "no owner",
    squadName: flag.squad_name,
    baseName: flag.base?.name || null
  }));
}

// Uso com biblioteca de mapas (ex: Leaflet, Google Maps, etc.)
function FlagsMapComponent() {
  const { data } = useFlags();
  
  if (!data) return null;
  
  const markers = convertFlagsToMarkers(data.flags);
  
  return (
    <MapContainer>
      {markers.map(marker => (
        <Marker
          key={marker.id}
          position={[marker.y, marker.x]} // Ajustar conforme biblioteca
          color={marker.hasOwner ? 'green' : 'red'}
        >
          <Popup>
            <div>
              <p>Owner: {marker.owner}</p>
              {marker.squadName && <p>Squad: {marker.squadName}</p>}
              {marker.baseName && <p>Base: {marker.baseName}</p>}
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
```

---

## ⚠️ Tratamento de Erros

### **Erro de Rede**

```typescript
try {
  const data = await fetchFlags();
} catch (error) {
  if (error instanceof TypeError && error.message.includes('fetch')) {
    console.error('Erro de conexão com o servidor');
  } else {
    console.error('Erro ao buscar bandeiras:', error);
  }
}
```

### **Erro HTTP**

```typescript
async function fetchFlagsWithErrorHandling(): Promise<FlagsResponse> {
  const response = await fetch('/api/flags');
  
  if (!response.ok) {
    if (response.status === 500) {
      const errorData: ErrorResponse = await response.json();
      throw new Error(`Erro do servidor: ${errorData.error}`);
    }
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  const data: FlagsResponse = await response.json();
  
  if (!data.success) {
    throw new Error(data.error || 'Erro desconhecido');
  }
  
  return data;
}
```

---

## 📌 Observações Importantes

### **1. Dados em Tempo Real**
- Este endpoint consulta diretamente o `SCUM.db`
- Os dados sempre refletem o estado atual do servidor
- Recomenda-se cache no frontend (30 segundos) para evitar muitas requisições

### **2. Bandeiras sem Owner**
- Bandeiras com `owner = "no owner"` podem ocorrer quando:
  - O perfil do jogador foi deletado
  - O jogador saiu do squad
  - A base foi abandonada
  - Ocorreu algum problema na sincronização

### **3. Relação com Base**
- Nem todas as bandeiras têm uma base associada
- O campo `base` pode ser `null`
- Quando presente, `base.location` contém as coordenadas do centro da base

### **4. Coordenadas**
- As coordenadas estão na escala do mapa do SCUM (centenas de milhares)
- Use essas coordenadas para plotar no mapa do jogo
- Exemplo: `x: 501103.75, y: -228677.22`

### **5. Performance**
- O endpoint retorna todas as bandeiras de uma vez
- Em servidores com muitas bandeiras, considere implementar paginação no frontend se necessário
- Use `refetchInterval` com cuidado (recomendado: 30 segundos)

---

## 🔗 Relação com Sistema de Squads

Este endpoint é **complementar** ao sistema de squads:

- **`/api/squads`**: Mostra a contagem total de bandeiras por squad (`flag_count`)
- **`/api/flags`**: Mostra cada bandeira individualmente com localização e owner

**Casos de uso combinados:**

1. **Visualizar território controlado por squad:**
   ```typescript
   // Buscar squads
   const squads = await fetch('/api/squads').then(r => r.json());
   
   // Buscar flags
   const flags = await fetch('/api/flags').then(r => r.json());
   
   // Agrupar flags por squad
   const flagsBySquad = flags.data.flags.reduce((acc, flag) => {
     if (flag.squad_id) {
       if (!acc[flag.squad_id]) acc[flag.squad_id] = [];
       acc[flag.squad_id].push(flag);
     }
     return acc;
   }, {} as Record<number, Flag[]>);
   ```

2. **Identificar bandeiras órfãs:**
   ```typescript
   const flags = await fetchFlags();
   const orphanFlags = flags.data.flags.filter(f => f.owner === "no owner");
   console.log(`Bandeiras órfãs: ${orphanFlags.length}`);
   ```

3. **Mapear território no mapa:**
   ```typescript
   // Plotar todas as bandeiras no mapa
   // Colorir por squad ou mostrar "no owner" em vermelho
   ```

---

## 🧪 Testes

### **Teste Manual (Postman/Browser)**

1. Abra o Postman ou navegador
2. Faça uma requisição `GET` para `http://localhost:3000/api/flags`
3. Verifique a resposta JSON

### **Teste com cURL**

```bash
curl -X GET http://localhost:3000/api/flags
```

### **Teste Unitário (Jest/Vitest)**

```typescript
import { describe, it, expect, vi } from 'vitest';

describe('fetchFlags', () => {
  it('deve retornar flags com sucesso', async () => {
    const mockResponse: FlagsResponse = {
      success: true,
      data: {
        flags: [
          {
            element_id: 1,
            location: { x: 100, y: 200, z: 50 },
            base: null,
            owner: "no owner",
            owner_profile_id: null,
            owner_steam_id: null,
            owner_name: null,
            squad_id: null,
            squad_name: null,
            overtake_end_time: null,
            overtaker_user_profile_id: null
          }
        ],
        total: 1,
        with_owner: 0,
        no_owner: 1
      }
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse
    });

    const result = await fetchFlags();
    expect(result.success).toBe(true);
    expect(result.data.total).toBe(1);
  });
});
```

---

## 📚 Recursos Adicionais

- **Documentação de Squads**: Ver `FRONTEND_SQUADS_API.md` para endpoints relacionados
- **Postman Collection**: Importe `postman-collection.json` para testar no Postman
- **Base URL**: Configure a variável `baseUrl` no Postman ou no seu código

---

## ✅ Checklist de Implementação

- [ ] Criar interfaces TypeScript para `Flag`, `FlagsResponse`, etc.
- [ ] Implementar função `fetchFlags()` com tratamento de erros
- [ ] Criar hook React (`useFlags`) ou usar React Query
- [ ] Implementar atualização automática (polling a cada 30s)
- [ ] Criar componente para exibir lista de bandeiras
- [ ] Implementar filtros (por squad, owner, base, etc.)
- [ ] Integrar com mapa (se aplicável)
- [ ] Tratar estados de loading e error
- [ ] Testar com dados reais
- [ ] Implementar cache no frontend

---

**Última atualização:** XX/01/2025 • **Status:** ✅ Implementado e Testado
