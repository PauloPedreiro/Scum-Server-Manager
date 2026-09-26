# 📍 Sistema de GPS - Documentação Frontend

## 📋 Visão Geral

Esta documentação descreve os endpoints da API para controle e consulta do sistema de sincronização de GPS dos jogadores online. O sistema funciona obtendo as coordenadas tridimensionais (X, Y, Z) em tempo real dos jogadores através do comando RCON `ListPlayers` e as salva no banco local do SSM para exibição nos mapas do painel.

O sistema de polling legado ao banco `SCUM.db` foi descontinuado para otimizar a performance e eliminar locks concorrentes de banco de dados.

- Monitorar localização dos jogadores online em tempo real
- Controlar o serviço de sincronização RCON (iniciar, parar, status)
- Executar sincronizações manuais instantâneas
- Consultar dados de GPS apenas dos jogadores que estão online no momento

---

## 🌐 Base URL

```
http://localhost:3000/api
```

**⚠️ Nota:** Em produção, substitua `localhost:3000` pela URL do servidor backend.

---

## 📊 Estruturas TypeScript

### **GpsSyncStatus**
```typescript
interface GpsSyncStatus {
  enabled: boolean;
  is_running: boolean;
  sync_interval: string; // Ex: "30 seconds" ou "2 minutes"
  last_sync: {
    timestamp: string; // ISO 8601
    status: "success" | "error" | "warning";
    details: {
      players_synced?: number;
      players_updated?: number;
      players_created?: number;
      elapsed_seconds?: number;
      message?: string;
      error?: string;
    };
  };
}
```

### **GpsSyncResponse**
```typescript
interface GpsSyncResponse {
  success: boolean;
  message?: string;
  status?: "started" | "stopped" | "already_running" | "not_running" | "disabled";
  sync_interval?: string;
  error?: string;
}
```

### **GpsSyncManualResponse**
```typescript
interface GpsSyncManualResponse {
  success: boolean;
  players_synced: number;
  players_updated?: number;
  players_created?: number;
  elapsed_seconds?: number;
  message?: string; // Ex: "Nenhum jogador online"
  errors?: Array<{
    steam_id: string;
    error: string;
  }>;
  error_count?: number;
  error?: string;
}
```

### **GpsCoordinates**
```typescript
interface GpsCoordinates {
  x: number;
  y: number;
  z: number;
}
```

### **GpsSpawnData**
```typescript
interface GpsSpawnData {
  prisoner_id: number;
  location_x: number;
  location_y: number;
  location_z: number;
  rotation_yaw: number; // Direção horizontal (0-360 graus)
  velocity_x: number;
  velocity_y: number;
  velocity_z: number;
  type: number; // Tipo de spawn
  updated_at: string; // ISO 8601
}
```

### **PlayerGpsData**
```typescript
interface PlayerGpsData {
  steam_id: string;
  player_name: string;
  last_activity: string; // ISO 8601
  ssm_coordinates: GpsCoordinates;
  gps_data: {
    spawns: GpsSpawnData[];
  };
}
```

### **OnlinePlayersGpsResponse**
```typescript
interface OnlinePlayersGpsResponse {
  success: boolean;
  data: {
    players: PlayerGpsData[];
    count: number;
  };
  timestamp: number;
  error?: string;
}
```

### **ApiResponse**
```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  status?: string;
  error?: string;
  timestamp?: number;
}
```

---

## 📡 Endpoints Disponíveis

### **1. GET /api/gps/sync/status**

Obter status atual do serviço de sincronização de GPS.

#### **URL**
```
GET http://localhost:3000/api/gps/sync/status
```

#### **Headers**
```
Nenhum necessário
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
        "players_updated": 1,
        "players_created": 0,
        "elapsed_seconds": 0.123
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

#### **Exemplo de Uso (TypeScript)**
```typescript
const getGpsSyncStatus = async (): Promise<ApiResponse<GpsSyncStatus>> => {
  try {
    const response = await fetch('http://localhost:3000/api/gps/sync/status');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Erro ao obter status do GPS:', error);
    throw error;
  }
};

// Uso
const status = await getGpsSyncStatus();
if (status.success && status.data) {
  console.log('Serviço rodando:', status.data.is_running);
  console.log('Última sincronização:', status.data.last_sync.timestamp);
  console.log('Jogadores sincronizados:', status.data.last_sync.details.players_synced);
}
```

---

### **2. POST /api/gps/sync/start**

Iniciar o serviço de sincronização de GPS. Executa uma sincronização imediata e agenda as próximas execuções.

#### **URL**
```
POST http://localhost:3000/api/gps/sync/start
```

#### **Headers**
```
Content-Type: application/json
```

#### **Body**
```
Vazio (não requer parâmetros)
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

#### **Exemplo de Uso (TypeScript)**
```typescript
const startGpsSync = async (): Promise<GpsSyncResponse> => {
  try {
    const response = await fetch('http://localhost:3000/api/gps/sync/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.message || data.error || 'Erro ao iniciar sincronização');
    }

    return data;
  } catch (error) {
    console.error('Erro ao iniciar sincronização GPS:', error);
    throw error;
  }
};

// Uso
try {
  const result = await startGpsSync();
  console.log('Sincronização iniciada:', result.message);
  console.log('Intervalo:', result.sync_interval);
} catch (error) {
  console.error('Falha ao iniciar:', error.message);
}
```

---

### **3. POST /api/gps/sync/stop**

Parar o serviço de sincronização de GPS.

#### **URL**
```
POST http://localhost:3000/api/gps/sync/stop
```

#### **Headers**
```
Content-Type: application/json
```

#### **Body**
```
Vazio (não requer parâmetros)
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

#### **Exemplo de Uso (TypeScript)**
```typescript
const stopGpsSync = async (): Promise<GpsSyncResponse> => {
  try {
    const response = await fetch('http://localhost:3000/api/gps/sync/stop', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.message || data.error || 'Erro ao parar sincronização');
    }

    return data;
  } catch (error) {
    console.error('Erro ao parar sincronização GPS:', error);
    throw error;
  }
};

// Uso
try {
  const result = await stopGpsSync();
  console.log('Sincronização parada:', result.message);
} catch (error) {
  console.error('Falha ao parar:', error.message);
}
```

---

### **4. POST /api/gps/sync/run-now**

Executar uma sincronização manual imediata, independente do agendamento.

#### **URL**
```
POST http://localhost:3000/api/gps/sync/run-now
```

#### **Headers**
```
Content-Type: application/json
```

#### **Body**
```
Vazio (não requer parâmetros)
```

#### **Resposta de Sucesso (200) - Com Jogadores Online**
```json
{
  "success": true,
  "players_synced": 1,
  "players_updated": 1,
  "players_created": 0,
  "elapsed_seconds": 0.123
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

#### **Exemplo de Uso (TypeScript)**
```typescript
const runGpsSyncNow = async (): Promise<GpsSyncManualResponse> => {
  try {
    const response = await fetch('http://localhost:3000/api/gps/sync/run-now', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Erro ao executar sincronização');
    }

    return data;
  } catch (error) {
    console.error('Erro ao executar sincronização GPS:', error);
    throw error;
  }
};

// Uso
try {
  const result = await runGpsSyncNow();
  
  if (result.players_synced === 0) {
    console.warn('Nenhum jogador online para sincronizar');
  } else {
    console.log(`Sincronizados ${result.players_synced} jogador(es)`);
    console.log(`Atualizados: ${result.players_updated || 0}`);
    console.log(`Criados: ${result.players_created || 0}`);
    console.log(`Tempo: ${result.elapsed_seconds?.toFixed(3)}s`);
  }
} catch (error) {
  console.error('Falha na sincronização:', error.message);
}
```

---

### **5. GET /api/gps/online**

Obter dados de GPS apenas dos jogadores que estão online no momento.

#### **URL**
```
GET http://localhost:3000/api/gps/online
```

#### **Headers**
```
Nenhum necessário
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
              "prisoner_id": 12345,
              "location_x": -616882.0,
              "location_y": -554072.0,
              "location_z": 2477.0,
              "rotation_yaw": 45.5,
              "velocity_x": 0.0,
              "velocity_y": 0.0,
              "velocity_z": 0.0,
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

#### **Exemplo de Uso (TypeScript)**
```typescript
const getOnlinePlayersGps = async (): Promise<OnlinePlayersGpsResponse> => {
  try {
    const response = await fetch('http://localhost:3000/api/gps/online');
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Erro ao obter GPS dos jogadores');
    }

    return data;
  } catch (error) {
    console.error('Erro ao obter GPS dos jogadores:', error);
    throw error;
  }
};

// Uso
try {
  const result = await getOnlinePlayersGps();
  
  if (result.data && result.data.players.length > 0) {
    console.log(`${result.data.count} jogador(es) online`);
    
    result.data.players.forEach(player => {
      console.log(`\n${player.player_name} (${player.steam_id})`);
      console.log(`Última atividade: ${player.last_activity}`);
      console.log(`Coordenadas SSM:`, player.ssm_coordinates);
      
      player.gps_data.spawns.forEach(spawn => {
        console.log(`  Localização: (${spawn.location_x}, ${spawn.location_y}, ${spawn.location_z})`);
        console.log(`  Direção: ${spawn.rotation_yaw}°`);
        console.log(`  Velocidade: (${spawn.velocity_x}, ${spawn.velocity_y}, ${spawn.velocity_z})`);
        console.log(`  Atualizado: ${spawn.updated_at}`);
      });
    });
  } else {
    console.log('Nenhum jogador online no momento');
  }
} catch (error) {
  console.error('Falha ao obter GPS:', error.message);
}
```

---

## 🎯 Fluxo Sugerido para o Frontend

### **1. Página de Controle do Serviço GPS**

```typescript
// Componente React/Next.js exemplo
import { useState, useEffect } from 'react';

const GpsControlPage = () => {
  const [status, setStatus] = useState<GpsSyncStatus | null>(null);
  const [loading, setLoading] = useState(false);

  // Carregar status ao montar componente
  useEffect(() => {
    loadStatus();
    // Atualizar status a cada 5 segundos
    const interval = setInterval(loadStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadStatus = async () => {
    try {
      const response = await getGpsSyncStatus();
      if (response.success && response.data) {
        setStatus(response.data);
      }
    } catch (error) {
      console.error('Erro ao carregar status:', error);
    }
  };

  const handleStart = async () => {
    setLoading(true);
    try {
      const result = await startGpsSync();
      if (result.success) {
        await loadStatus(); // Recarregar status
        alert('Sincronização iniciada com sucesso!');
      }
    } catch (error) {
      alert(`Erro: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    if (!confirm('Deseja parar a sincronização de GPS?')) return;
    
    setLoading(true);
    try {
      const result = await stopGpsSync();
      if (result.success) {
        await loadStatus(); // Recarregar status
        alert('Sincronização parada com sucesso!');
      }
    } catch (error) {
      alert(`Erro: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncNow = async () => {
    setLoading(true);
    try {
      const result = await runGpsSyncNow();
      if (result.success) {
        await loadStatus(); // Recarregar status
        if (result.players_synced === 0) {
          alert('Nenhum jogador online para sincronizar');
        } else {
          alert(`Sincronizados ${result.players_synced} jogador(es) com sucesso!`);
        }
      }
    } catch (error) {
      alert(`Erro: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!status) {
    return <div>Carregando...</div>;
  }

  return (
    <div>
      <h1>Sistema de GPS</h1>
      
      <div>
        <h2>Status do Serviço</h2>
        <p>Habilitado: {status.enabled ? 'Sim' : 'Não'}</p>
        <p>Rodando: {status.is_running ? 'Sim' : 'Não'}</p>
        <p>Intervalo: {status.sync_interval}</p>
        <p>Última sincronização: {new Date(status.last_sync.timestamp).toLocaleString()}</p>
        <p>Status: {status.last_sync.status}</p>
        {status.last_sync.details.players_synced !== undefined && (
          <p>Jogadores sincronizados: {status.last_sync.details.players_synced}</p>
        )}
      </div>

      <div>
        <h2>Ações</h2>
        <button 
          onClick={handleStart} 
          disabled={loading || status.is_running}
        >
          Iniciar Sincronização
        </button>
        <button 
          onClick={handleStop} 
          disabled={loading || !status.is_running}
        >
          Parar Sincronização
        </button>
        <button 
          onClick={handleSyncNow} 
          disabled={loading}
        >
          Sincronizar Agora
        </button>
      </div>
    </div>
  );
};
```

### **2. Página de Visualização de GPS dos Jogadores**

```typescript
// Componente React/Next.js exemplo
import { useState, useEffect } from 'react';

const PlayersGpsPage = () => {
  const [players, setPlayers] = useState<PlayerGpsData[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadPlayersGps();
    // Atualizar a cada 30 segundos (mesmo intervalo da sincronização)
    const interval = setInterval(loadPlayersGps, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadPlayersGps = async () => {
    setLoading(true);
    try {
      const response = await getOnlinePlayersGps();
      if (response.success && response.data) {
        setPlayers(response.data.players);
      }
    } catch (error) {
      console.error('Erro ao carregar GPS:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCoordinates = (coords: GpsCoordinates) => {
    return `X: ${coords.x.toFixed(2)}, Y: ${coords.y.toFixed(2)}, Z: ${coords.z.toFixed(2)}`;
  };

  const formatRotation = (yaw: number) => {
    return `${yaw.toFixed(1)}°`;
  };

  const getVelocityMagnitude = (vx: number, vy: number, vz: number) => {
    return Math.sqrt(vx * vx + vy * vy + vz * vz).toFixed(2);
  };

  return (
    <div>
      <h1>GPS dos Jogadores Online</h1>
      <p>Total: {players.length} jogador(es) online</p>
      
      {loading && <p>Carregando...</p>}
      
      <div>
        {players.map(player => (
          <div key={player.steam_id} style={{ border: '1px solid #ccc', padding: '10px', margin: '10px' }}>
            <h3>{player.player_name}</h3>
            <p>Steam ID: {player.steam_id}</p>
            <p>Última atividade: {new Date(player.last_activity).toLocaleString()}</p>
            <p>Coordenadas SSM: {formatCoordinates(player.ssm_coordinates)}</p>
            
            {player.gps_data.spawns.map((spawn, index) => (
              <div key={index} style={{ marginLeft: '20px', marginTop: '10px' }}>
                <h4>Spawn #{index + 1}</h4>
                <p>Localização: {formatCoordinates({
                  x: spawn.location_x,
                  y: spawn.location_y,
                  z: spawn.location_z
                })}</p>
                <p>Direção: {formatRotation(spawn.rotation_yaw)}</p>
                <p>Velocidade: {getVelocityMagnitude(
                  spawn.velocity_x,
                  spawn.velocity_y,
                  spawn.velocity_z
                )} m/s</p>
                <p>Atualizado: {new Date(spawn.updated_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
        ))}
        
        {players.length === 0 && !loading && (
          <p>Nenhum jogador online no momento</p>
        )}
      </div>
    </div>
  );
};
```

---

## ✅ Checklist Frontend

### **Implementação Básica**
- [ ] Criar tipos TypeScript para todas as interfaces
- [ ] Implementar função `getGpsSyncStatus()`
- [ ] Implementar função `startGpsSync()`
- [ ] Implementar função `stopGpsSync()`
- [ ] Implementar função `runGpsSyncNow()`
- [ ] Implementar função `getOnlinePlayersGps()`

### **Página de Controle**
- [ ] Exibir status do serviço (habilitado, rodando, intervalo)
- [ ] Exibir última sincronização (timestamp, status, detalhes)
- [ ] Botão "Iniciar" (desabilitado se já estiver rodando)
- [ ] Botão "Parar" (desabilitado se não estiver rodando)
- [ ] Botão "Sincronizar Agora" (sempre habilitado)
- [ ] Atualizar status automaticamente (polling a cada 5 segundos)
- [ ] Exibir mensagens de erro/sucesso (toast/alert)

### **Página de Visualização GPS**
- [ ] Listar todos os jogadores online
- [ ] Exibir coordenadas (X, Y, Z)
- [ ] Exibir direção (rotation_yaw em graus)
- [ ] Exibir velocidade (magnitude ou componentes)
- [ ] Exibir última atualização
- [ ] Atualizar automaticamente (polling a cada 30 segundos)
- [ ] Tratar caso de nenhum jogador online

### **Tratamento de Erros**
- [ ] Capturar erros de rede (fetch failed)
- [ ] Exibir mensagens de erro retornadas pela API
- [ ] Tratar casos de serviço não inicializado
- [ ] Tratar casos de serviço já em execução/não em execução
- [ ] Validar dados antes de exibir

### **UX/UI**
- [ ] Indicadores de loading durante requisições
- [ ] Feedback visual para ações (sucesso/erro)
- [ ] Confirmação para ações destrutivas (parar serviço)
- [ ] Formatação adequada de coordenadas e direções
- [ ] Tooltips/explicações para campos técnicos
- [ ] Responsividade para mobile

### **Otimizações**
- [ ] Cache de status (evitar requisições desnecessárias)
- [ ] Debounce para botões de ação
- [ ] Cancelar requisições pendentes ao desmontar componente
- [ ] Lazy loading para lista de jogadores (se muitos)

---

## 🔍 Observações Importantes

### **Intervalo de Sincronização**
- O intervalo padrão é **30 segundos** (configurável no backend)
- A página de visualização deve atualizar no mesmo intervalo para manter dados atualizados
- O status do serviço pode ser atualizado com menos frequência (5-10 segundos)

### **Dados de GPS (RCON)**
- **X, Y, Z**: Coordenadas espaciais do jogador em tempo real.
- **rotation_yaw / velocity_x/y/z**: Estes campos (direção/velocidade) eram obtidos via banco de dados `SCUM.db` e agora vêm como `null`, uma vez que o comando RCON `ListPlayers` do SCUM fornece apenas coordenadas de localização (X, Y, Z).
- **type**: Tipo de spawn do personagem (valores específicos do SCUM - padrão 0).

### **Performance**
- O endpoint `/api/gps/online` retorna apenas jogadores online.
- A sincronização é extremamente otimizada, pois a consulta ocorre via RCON diretamente em memória e não consome I/O de arquivos SQLite.

### **Estados do Serviço**
- **enabled**: Serviço habilitado no config (pode estar parado)
- **is_running**: Serviço realmente em execução e sincronizando
- **last_sync.status**: Status da última sincronização
  - `success`: Sincronização bem-sucedida
  - `error`: Erro durante sincronização
  - `warning`: Sincronização concluída com avisos

---

## 📚 Exemplos de Integração

### **React Hook Customizado**

```typescript
import { useState, useEffect, useCallback } from 'react';

export const useGpsSync = () => {
  const [status, setStatus] = useState<GpsSyncStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      setError(null);
      const response = await getGpsSyncStatus();
      if (response.success && response.data) {
        setStatus(response.data);
      } else {
        setError(response.error || 'Erro ao carregar status');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    }
  }, []);

  const start = useCallback(async () => {
    setLoading(true);
    try {
      const result = await startGpsSync();
      if (result.success) {
        await loadStatus();
        return { success: true, message: result.message };
      } else {
        return { success: false, message: result.message || result.error };
      }
    } catch (err) {
      return { success: false, message: err instanceof Error ? err.message : 'Erro desconhecido' };
    } finally {
      setLoading(false);
    }
  }, [loadStatus]);

  const stop = useCallback(async () => {
    setLoading(true);
    try {
      const result = await stopGpsSync();
      if (result.success) {
        await loadStatus();
        return { success: true, message: result.message };
      } else {
        return { success: false, message: result.message || result.error };
      }
    } catch (err) {
      return { success: false, message: err instanceof Error ? err.message : 'Erro desconhecido' };
    } finally {
      setLoading(false);
    }
  }, [loadStatus]);

  const syncNow = useCallback(async () => {
    setLoading(true);
    try {
      const result = await runGpsSyncNow();
      if (result.success) {
        await loadStatus();
        return { success: true, data: result };
      } else {
        return { success: false, message: result.error || 'Erro desconhecido' };
      }
    } catch (err) {
      return { success: false, message: err instanceof Error ? err.message : 'Erro desconhecido' };
    } finally {
      setLoading(false);
    }
  }, [loadStatus]);

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 5000);
    return () => clearInterval(interval);
  }, [loadStatus]);

  return {
    status,
    loading,
    error,
    start,
    stop,
    syncNow,
    refresh: loadStatus,
  };
};
```

### **Uso do Hook**

```typescript
const GpsControlComponent = () => {
  const { status, loading, error, start, stop, syncNow } = useGpsSync();

  return (
    <div>
      {error && <div className="error">{error}</div>}
      {status && (
        <>
          <p>Status: {status.is_running ? 'Rodando' : 'Parado'}</p>
          <button onClick={start} disabled={loading || status.is_running}>
            Iniciar
          </button>
          <button onClick={stop} disabled={loading || !status.is_running}>
            Parar
          </button>
          <button onClick={syncNow} disabled={loading}>
            Sincronizar Agora
          </button>
        </>
      )}
    </div>
  );
};
```

---

## 📝 Histórico

- **17/11/2025**: Documentação criada para handoff ao frontend.

> Em caso de mudanças nos endpoints ou estruturas de dados, alinhar previamente com o backend para manter compatibilidade.

