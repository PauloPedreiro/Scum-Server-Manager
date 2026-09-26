## API de ServerSettings.ini (Frontend)

### Visão Geral

- **Objetivo**: Gerenciar o arquivo `ServerSettings.ini` do servidor SCUM através do frontend.
- **Fonte dos dados**: Arquivo `ServerSettings.ini` no diretório de configuração do servidor.
- **Formato das respostas**: JSON com estrutura simples de chave-valor.
- **Flexibilidade**: Aceita qualquer campo (conhecido ou customizado), incluindo mods.
- **Backup automático**: Sistema cria backup antes de cada modificação.

---

### Endpoints Disponíveis

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/server/settings` | Obter todas as configurações ou seção específica |
| `PATCH` | `/api/server/settings` | Atualizar um campo específico |
| `PUT` | `/api/server/settings/{section}` | Atualizar seção completa |

---

### 1. `GET /api/server/settings`

Obter todas as configurações ou uma seção específica do `ServerSettings.ini`.

**⚠️ Importante**: O endpoint retorna **TODOS os campos** de cada seção. Não há filtragem - todos os campos do arquivo INI são retornados.

**Query Params**

| Parâmetro | Tipo | Default | Descrição |
| --- | --- | --- | --- |
| `section` | `string` | - | Nome da seção (ex: `General`, `World`, `Respawn`) |

**Exemplos**

```bash
# Obter todas as seções
GET /api/server/settings

# Obter apenas seção General
GET /api/server/settings?section=General
```

**Resposta de Exemplo (Todas as Seções)**

```json
{
  "success": true,
  "data": {
    "General": {
      "scum.ServerName": "SCUM Server",
      "scum.ServerDescription": "Server Description",
      "scum.ServerPassword": "",
      "scum.MaxPlayers": "64",
      "scum.ServerBannerUrl": "",
      "scum.ServerPlaystyle": "PVE",
      "scum.WelcomeMessage": "Welcome to our SCUM Server",
      "scum.MessageOfTheDay": "This is the Message of the Day.",
      "scum.MessageOfTheDayCooldown": "10.000000",
      "scum.MinServerTickRate": "5",
      "scum.MaxServerTickRate": "30",
      "scum.MaxPingCheckEnabled": "1",
      "scum.MaxPing": "200.000000",
      "scum.LogoutTimer": "60.000000",
      "scum.AllowFirstPerson": "1",
      "scum.AllowThirdPerson": "1",
      "scum.AllowCrosshair": "1",
      "scum.AllowVoting": "1",
      "scum.AllowMapScreen": "1",
      "scum.AllowKillClaiming": "1",
      "scum.AllowComa": "1",
      "scum.AllowMinesAndTraps": "1",
      "scum.AllowSkillGainInSafeZones": "0",
      "scum.AllowEvents": "1",
      "scum.LimitGlobalChat": "0",
      "scum.AllowGlobalChat": "1",
      "scum.AllowLocalChat": "1",
      "scum.AllowSquadChat": "1",
      "scum.AllowAdminChat": "1",
      "scum.RustyLocksLogging": "0",
      "scum.HideKillNotification": "1",
      "scum.DisableTimedGifts": "0",
      "scum.UseMapBaseBuildingRestriction": "1",
      "scum.DisableBaseBuilding": "0",
      "scum.VotingDuration": "60.000000",
      "scum.PlayerMinimalVotingInterest": "0.500000",
      "scum.PlayerPositiveVotePercentage": "0.500000",
      "scum.MasterServerUpdateSendInterval": "60",
      "scum.MasterServerIsLocalTest": "0",
      "scum.PartialWipe": "0",
      "scum.GoldWipe": "0",
      "scum.FullWipe": "0",
      "scum.ItemVirtualizationRelevancyUpdatePeriod": "1.000000",
      "scum.ItemVirtualizationEventProcessingTimeBudget": "5.000000",
      "scum.ItemVirtualizationVisitorDistanceTravelledForUpdate": "100.000000",
      "scum.ItemVirtualizationVisitorBounds": "10000.000000",
      "scum.VirtualizedItemBounds": "100.000000",
      "scum.FameGainMultiplier": "1.000000",
      "scum.FamePointPenaltyOnDeath": "0.100000",
      "scum.FamePointPenaltyOnKilled": "0.500000",
      "scum.FamePointRewardOnKill": "0.250000",
      "scum.LogSuicides": "0",
      "scum.EnableSpawnOnGround": "0",
      "scum.DeleteInactiveUsers": "1",
      "scum.DaysSinceLastLoginToBecomeInactive": "180",
      "scum.DeleteBannedUsers": "0",
      "scum.MaximumTimeForChestsInForbiddenZones": "02:00:00",
      "scum.LogChestOwnership": "1",
      "scum.SettingsVersion": "3",
      "scum.DisableExamineGhost": "0"
    },
    "World": {
      "scum.MaxAllowedBirds": "15",
      "scum.MaxAllowedCharacters": "-1",
      "scum.MaxAllowedPuppets": "-1",
      "scum.MaxAllowedAnimals": "-1",
      "scum.MaxAllowedNPCs": "-1"
    },
    "Respawn": {
      "scum.AllowSectorRespawn": "1",
      "scum.AllowShelterRespawn": "1",
      "scum.RandomRespawnPrice": "250"
    },
    "Vehicles": {
      "scum.FuelDrainFromEngineMultiplier": "1.000000"
    },
    "Damage": {
      "scum.HumanToHumanDamageMultiplier": "1.000000"
    },
    "Features": {
      "scum.FlagOvertakeDuration": "24:00:00"
    }
  },
  "timestamp": 1701504000
}
```

**⚠️ Importante**: A resposta inclui **TODOS os campos** de cada seção. O exemplo acima mostra apenas alguns campos para brevidade. Na prática:
- **General**: ~62 campos
- **World**: ~100+ campos
- **Respawn**: ~20 campos
- **Vehicles**: ~50+ campos
- **Damage**: ~15 campos
- **Features**: ~100+ campos

**Resposta de Exemplo (Seção Específica)**

```json
{
  "success": true,
  "data": {
    "General": {
      "scum.ServerName": "SCUM Server",
      "scum.ServerDescription": "Server Description",
      "scum.ServerPassword": "",
      "scum.MaxPlayers": "64",
      "scum.ServerBannerUrl": "",
      "scum.ServerPlaystyle": "PVE",
      "scum.WelcomeMessage": "Welcome to our SCUM Server",
      "scum.MessageOfTheDay": "This is the Message of the Day.",
      "scum.MessageOfTheDayCooldown": "10.000000",
      "scum.MinServerTickRate": "5",
      "scum.MaxServerTickRate": "30",
      "scum.MaxPingCheckEnabled": "1",
      "scum.MaxPing": "200.000000",
      "scum.LogoutTimer": "60.000000",
      "scum.AllowFirstPerson": "1",
      "scum.AllowThirdPerson": "1",
      "scum.AllowCrosshair": "1",
      "scum.AllowVoting": "1",
      "scum.AllowMapScreen": "1",
      "scum.AllowKillClaiming": "1",
      "scum.AllowComa": "1",
      "scum.AllowMinesAndTraps": "1",
      "scum.AllowSkillGainInSafeZones": "0",
      "scum.AllowEvents": "1",
      "scum.LimitGlobalChat": "0",
      "scum.AllowGlobalChat": "1",
      "scum.AllowLocalChat": "1",
      "scum.AllowSquadChat": "1",
      "scum.AllowAdminChat": "1",
      "scum.RustyLocksLogging": "0",
      "scum.HideKillNotification": "1",
      "scum.DisableTimedGifts": "0",
      "scum.UseMapBaseBuildingRestriction": "1",
      "scum.DisableBaseBuilding": "0",
      "scum.VotingDuration": "60.000000",
      "scum.PlayerMinimalVotingInterest": "0.500000",
      "scum.PlayerPositiveVotePercentage": "0.500000",
      "scum.MasterServerUpdateSendInterval": "60",
      "scum.MasterServerIsLocalTest": "0",
      "scum.PartialWipe": "0",
      "scum.GoldWipe": "0",
      "scum.FullWipe": "0",
      "scum.ItemVirtualizationRelevancyUpdatePeriod": "1.000000",
      "scum.ItemVirtualizationEventProcessingTimeBudget": "5.000000",
      "scum.ItemVirtualizationVisitorDistanceTravelledForUpdate": "100.000000",
      "scum.ItemVirtualizationVisitorBounds": "10000.000000",
      "scum.VirtualizedItemBounds": "100.000000",
      "scum.FameGainMultiplier": "1.000000",
      "scum.FamePointPenaltyOnDeath": "0.100000",
      "scum.FamePointPenaltyOnKilled": "0.500000",
      "scum.FamePointRewardOnKill": "0.250000",
      "scum.LogSuicides": "0",
      "scum.EnableSpawnOnGround": "0",
      "scum.DeleteInactiveUsers": "1",
      "scum.DaysSinceLastLoginToBecomeInactive": "180",
      "scum.DeleteBannedUsers": "0",
      "scum.MaximumTimeForChestsInForbiddenZones": "02:00:00",
      "scum.LogChestOwnership": "1",
      "scum.SettingsVersion": "3",
      "scum.DisableExamineGhost": "0"
    }
  },
  "timestamp": 1701504000
}
```

**⚠️ Nota**: A resposta inclui **TODOS os campos** da seção solicitada. A seção `General` contém aproximadamente 62 campos no total.

---

### 2. `PATCH /api/server/settings`

Atualizar uma configuração específica. Aceita qualquer campo (conhecido ou customizado).

**Body**

```json
{
  "section": "General",
  "key": "scum.MaxPlayers",
  "value": 100
}
```

**Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Configuração scum.MaxPlayers atualizada",
  "data": {
    "section": "General",
    "key": "scum.MaxPlayers",
    "value": "100",
    "backup": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\backups\\ServerSettings.backup.20251202_190000.ini"
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (400)**

```json
{
  "success": false,
  "error": "section, key e value são obrigatórios"
}
```

---

### 3. `PUT /api/server/settings/{section}`

Atualizar seção completa. Útil para salvar múltiplas alterações de uma vez. Aceita qualquer campo (conhecido ou customizado).

**Body**

```json
{
  "scum.ServerName": "Meu Servidor SCUM",
  "scum.MaxPlayers": "100",
  "scum.ServerPlaystyle": "PVP",
  "custom.MyCustomSetting": "value",
  "mod.ModSetting": "mod_value"
}
```

**Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "5 campo(s) atualizado(s)",
  "data": {
    "section": "General",
    "updated_fields": [
      "scum.ServerName",
      "scum.MaxPlayers",
      "scum.ServerPlaystyle",
      "custom.MyCustomSetting",
      "mod.ModSetting"
    ],
    "backup": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\backups\\ServerSettings.backup.20251202_190000.ini"
  },
  "timestamp": 1701504000
}
```

---

### Interfaces TypeScript Sugeridas

```typescript
export interface ServerSettingsResponse {
  success: boolean;
  data: {
    [section: string]: {
      [key: string]: string;
    };
  };
  timestamp: number;
}

export interface UpdateSettingRequest {
  section: string;
  key: string;
  value: string | number | boolean;
}

export interface UpdateSettingResponse {
  success: boolean;
  message: string;
  data: {
    section: string;
    key: string;
    value: string;
    backup: string | null;
  };
  timestamp: number;
}

export interface UpdateSectionResponse {
  success: boolean;
  message: string;
  data: {
    section: string;
    updated_fields: string[];
    backup: string | null;
  };
  timestamp: number;
}
```

---

### Hooks React (exemplo com React Query)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Hook para carregar configurações
export function useServerSettings(section?: string) {
  return useQuery({
    queryKey: ['server', 'settings', section],
    queryFn: async () => {
      const url = section 
        ? `/api/server/settings?section=${section}`
        : '/api/server/settings';
      
      const res = await fetch(url);
      if (!res.ok) throw new Error('Falha ao carregar configurações');
      return (await res.json()) as ServerSettingsResponse;
    },
    staleTime: 30_000, // 30 segundos
  });
}

// Hook para atualizar um campo
export function useUpdateSetting() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data: UpdateSettingRequest) => {
      const res = await fetch('/api/server/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || 'Falha ao atualizar configuração');
      }
      
      return (await res.json()) as UpdateSettingResponse;
    },
    onSuccess: (_, variables) => {
      // Invalidar cache para recarregar
      queryClient.invalidateQueries({ queryKey: ['server', 'settings'] });
    },
  });
}

// Hook para atualizar seção completa
export function useUpdateSection() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ section, settings }: { section: string; settings: Record<string, any> }) => {
      const res = await fetch(`/api/server/settings/${section}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || 'Falha ao atualizar seção');
      }
      
      return (await res.json()) as UpdateSectionResponse;
    },
    onSuccess: (_, variables) => {
      // Invalidar cache para recarregar
      queryClient.invalidateQueries({ queryKey: ['server', 'settings', variables.section] });
    },
  });
}
```

---

### Componente React: Editor de Configurações

```typescript
import { useState } from 'react';
import { useServerSettings, useUpdateSection } from './hooks/useServerSettings';

type Section = 'General' | 'World' | 'Respawn' | 'Vehicles' | 'Damage' | 'Features';

export function ServerSettingsEditor() {
  const [activeSection, setActiveSection] = useState<Section>('General');
  const { data, isLoading } = useServerSettings(activeSection);
  const updateSection = useUpdateSection();
  
  const [editingSettings, setEditingSettings] = useState<Record<string, string>>({});
  
  // Inicializar editingSettings quando dados carregarem
  useEffect(() => {
    if (data?.data?.[activeSection]) {
      setEditingSettings(data.data[activeSection]);
    }
  }, [data, activeSection]);
  
  const handleFieldChange = (key: string, value: string) => {
    setEditingSettings(prev => ({ ...prev, [key]: value }));
  };
  
  const handleAddField = () => {
    const key = prompt('Nome do campo:');
    const value = prompt('Valor:');
    
    if (key && value !== null) {
      setEditingSettings(prev => ({ ...prev, [key]: value }));
    }
  };
  
  const handleSave = async () => {
    try {
      await updateSection.mutateAsync({
        section: activeSection,
        settings: editingSettings
      });
      alert('Configurações salvas com sucesso!');
    } catch (error) {
      alert(`Erro ao salvar: ${error.message}`);
    }
  };
  
  if (isLoading) return <div>Carregando...</div>;
  
  const settings = data?.data?.[activeSection] || {};
  
  return (
    <div className="server-settings-editor">
      <h1>Configurações do Servidor</h1>
      
      {/* Tabs de seções */}
      <div className="section-tabs">
        {['General', 'World', 'Respawn', 'Vehicles', 'Damage', 'Features'].map(section => (
          <button
            key={section}
            className={activeSection === section ? 'active' : ''}
            onClick={() => setActiveSection(section as Section)}
          >
            [{section}]
          </button>
        ))}
      </div>
      
      {/* Campos editáveis */}
      <div className="settings-fields">
        {Object.entries(editingSettings).map(([key, value]) => (
          <div key={key} className="setting-field">
            <label>{key}</label>
            <input
              type="text"
              value={value}
              onChange={(e) => handleFieldChange(key, e.target.value)}
            />
          </div>
        ))}
      </div>
      
      {/* Ações */}
      <div className="actions">
        <button onClick={handleAddField}>➕ Adicionar Campo</button>
        <button 
          onClick={handleSave}
          disabled={updateSection.isPending}
        >
          {updateSection.isPending ? 'Salvando...' : '💾 Salvar'}
        </button>
      </div>
      
      {updateSection.data?.data?.backup && (
        <div className="backup-info">
          Backup criado: {updateSection.data.data.backup}
        </div>
      )}
    </div>
  );
}
```

---

### Exemplos de Uso

**1. Carregar Todas as Configurações**

```typescript
const { data } = useServerSettings();

// Acessar seção específica
const generalSettings = data?.data?.General;
```

**2. Carregar Seção Específica**

```typescript
const { data } = useServerSettings('General');

// Acessar campos
const maxPlayers = data?.data?.General?.['scum.MaxPlayers'];
```

**3. Atualizar Campo Específico**

```typescript
const updateSetting = useUpdateSetting();

await updateSetting.mutateAsync({
  section: 'General',
  key: 'scum.MaxPlayers',
  value: 100
});
```

**4. Atualizar Seção Completa (com campo customizado)**

```typescript
const updateSection = useUpdateSection();

await updateSection.mutateAsync({
  section: 'General',
  settings: {
    'scum.MaxPlayers': '100',
    'scum.ServerName': 'Meu Servidor',
    'custom.MyCustomSetting': 'value'  // Campo customizado
  }
});
```

**5. Adicionar Campo Customizado**

```typescript
// Simplesmente inclua o campo ao atualizar a seção
const updateSection = useUpdateSection();

await updateSection.mutateAsync({
  section: 'General',
  settings: {
    ...existingSettings,
    'custom.MyNewField': 'new_value'  // Novo campo
  }
});
```

---

### Seções Disponíveis

O `ServerSettings.ini` possui as seguintes seções:

1. **General** - Configurações gerais do servidor
   - Nome, descrição, senha
   - Máximo de jogadores
   - Estilo de jogo (PVE, PVP, PVPvE)
   - Configurações de chat, votação, eventos
   - Multiplicadores de fama

2. **World** - Configurações do mundo
   - Limites de entidades (puppets, animais, NPCs)
   - Configurações de encounters e hordas
   - Tempo/dia (nascer/pôr do sol)
   - Cargo drops, hunts, bunkers

3. **Respawn** - Configurações de respawn
   - Tipos de respawn (setor, abrigo, squad)
   - Preços e cooldowns
   - Configurações de suicídio

4. **Vehicles** - Configurações de veículos
   - Drenagem de combustível/bateria
   - Limites por tipo de veículo

5. **Damage** - Multiplicadores de dano
   - Dano entre humanos
   - Dano de sentry, dropship, zumbis

6. **Features** - Recursos avançados
   - Flags e base building
   - Raid protection
   - Multiplicadores de skills
   - Quests, turrets

---

### Campos Customizados e Mods

O sistema aceita **qualquer campo**, incluindo:

- **Campos conhecidos**: `scum.MaxPlayers`, `scum.ServerName`, etc.
- **Campos customizados**: `custom.MySetting`, `custom.UserConfig`, etc.
- **Campos de mods**: `mod.ModName.Setting`, `mod.CustomMod.Config`, etc.

**Como adicionar:**

1. Ao atualizar uma seção, simplesmente inclua o novo campo no body
2. O sistema preserva automaticamente todos os campos
3. Não é necessário registro prévio

**Exemplo:**

```typescript
// Adicionar campo customizado
await updateSection.mutateAsync({
  section: 'General',
  settings: {
    'scum.MaxPlayers': '100',  // Campo conhecido
    'custom.MyCustomSetting': 'value',  // Campo customizado
    'mod.MyMod.Setting': 'mod_value'  // Campo de mod
  }
});
```

---

### Backup Automático

O sistema cria backup automaticamente antes de cada modificação:

- **Localização**: `{config_directory}/backups/ServerSettings.backup.{timestamp}.ini`
- **Retenção**: Mantém últimos 10 backups
- **Limpeza**: Backups antigos são removidos automaticamente

O caminho do backup é retornado na resposta:

```json
{
  "data": {
    "backup": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\backups\\ServerSettings.backup.20251202_190000.ini"
  }
}
```

---

### Tratamento de Erros

```typescript
const { data, error, isLoading } = useServerSettings();

if (error) {
  // Erro de rede ou servidor
  console.error('Erro ao carregar configurações:', error);
}

const updateSection = useUpdateSection();

try {
  await updateSection.mutateAsync({ section: 'General', settings: {...} });
} catch (error) {
  // Erro ao salvar
  if (error.message.includes('obrigatórios')) {
    // Campos obrigatórios faltando
  } else {
    // Outro erro
  }
}
```

---

### Considerações Importantes

1. **Valores como String**: Todos os valores são tratados como string no arquivo INI, mesmo números e booleanos.

2. **Preservação**: O sistema preserva todos os campos ao salvar, incluindo campos desconhecidos.

3. **Backup**: Sempre há backup antes de modificar. Use o caminho retornado para restaurar se necessário.

4. **Reinício do Servidor**: Algumas configurações podem requerer reinício do servidor para ter efeito.

5. **Formato de Valores**:
   - Números: `"64"`, `"100"`
   - Booleanos: `"0"` (false) ou `"1"` (true)
   - Tempos: `"24:00:00"`, `"02:00:00"`
   - Moedas: `"1g"`, `"10g"`

6. **Case Sensitive**: Os nomes das seções e chaves são case-sensitive. Use exatamente como aparecem no arquivo.

---

### UX & Visualizações Sugeridas

- **Editor de Seções**: 
  - Tabs para cada seção (General, World, Respawn, etc.)
  - Lista de campos editáveis
  - Botão para adicionar novo campo
  - Botão para salvar seção

- **Indicadores**:
  - Mostrar quando há alterações não salvas
  - Mostrar caminho do backup após salvar
  - Loading state durante salvamento

- **Validação**:
  - Validação básica de formato (opcional no frontend)
  - Alertas antes de salvar alterações importantes

- **Organização**:
  - Agrupar campos relacionados
  - Busca/filtro de campos (para seções grandes)
  - Ordenação alfabética opcional

---

### Exemplo Completo: Página de Configurações

```typescript
import { useState, useEffect } from 'react';
import { useServerSettings, useUpdateSection } from './hooks/useServerSettings';

export function ServerSettingsPage() {
  const sections: Section[] = ['General', 'World', 'Respawn', 'Vehicles', 'Damage', 'Features'];
  const [activeSection, setActiveSection] = useState<Section>('General');
  const { data, isLoading, error } = useServerSettings(activeSection);
  const updateSection = useUpdateSection();
  
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);
  
  useEffect(() => {
    if (data?.data?.[activeSection]) {
      setSettings(data.data[activeSection]);
      setHasChanges(false);
    }
  }, [data, activeSection]);
  
  const handleChange = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };
  
  const handleAddField = () => {
    const key = prompt('Nome do campo:');
    const value = prompt('Valor:');
    if (key && value !== null) {
      handleChange(key, value);
    }
  };
  
  const handleSave = async () => {
    try {
      const result = await updateSection.mutateAsync({
        section: activeSection,
        settings
      });
      setHasChanges(false);
      alert(`✅ ${result.message}\nBackup: ${result.data.backup}`);
    } catch (error: any) {
      alert(`❌ Erro: ${error.message}`);
    }
  };
  
  if (isLoading) return <div>Carregando configurações...</div>;
  if (error) return <div>Erro ao carregar: {error.message}</div>;
  
  return (
    <div className="server-settings-page">
      <h1>⚙️ Configurações do Servidor</h1>
      
      {/* Tabs */}
      <div className="tabs">
        {sections.map(section => (
          <button
            key={section}
            className={activeSection === section ? 'active' : ''}
            onClick={() => setActiveSection(section)}
          >
            [{section}]
          </button>
        ))}
      </div>
      
      {/* Campos */}
      <div className="settings-container">
        {Object.entries(settings).map(([key, value]) => (
          <div key={key} className="field-row">
            <label>{key}</label>
            <input
              type="text"
              value={value}
              onChange={(e) => handleChange(key, e.target.value)}
            />
          </div>
        ))}
      </div>
      
      {/* Ações */}
      <div className="actions">
        <button onClick={handleAddField}>➕ Adicionar Campo</button>
        <button 
          onClick={handleSave}
          disabled={!hasChanges || updateSection.isPending}
          className="primary"
        >
          {updateSection.isPending ? 'Salvando...' : '💾 Salvar Alterações'}
        </button>
      </div>
      
      {hasChanges && (
        <div className="warning">
          ⚠️ Você tem alterações não salvas
        </div>
      )}
    </div>
  );
}
```

---

### Integração com Outros Endpoints

Este endpoint pode ser combinado com outros para funcionalidades mais avançadas:

- **`GET /api/server/status`**: Verificar se servidor está rodando antes de modificar configurações
- **`POST /api/server/restart`**: Reiniciar servidor após alterar configurações que requerem restart

---

Última atualização: **02/12/2025** • Status: ✅ Implementado e Testado

