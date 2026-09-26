# 📋 Análise: ServerSettings.ini

## 🎯 Objetivo

Analisar a estrutura do arquivo `ServerSettings.ini` do servidor SCUM e propor funcionalidades para gerenciá-lo através da API.

---

## 📍 Localização

**Caminho**: `C:\Servers\Scum\SCUM\Saved\Config\WindowsServer\ServerSettings.ini`

**Obtido via config.json**: `paths.scum_server.config_directory`

---

## 📊 Estrutura do Arquivo

O arquivo `ServerSettings.ini` é um arquivo de configuração no formato INI com as seguintes seções:

### **1. [General] - Configurações Gerais do Servidor**

Configurações básicas do servidor:

| Chave | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `scum.ServerName` | string | Nome do servidor | `SCUM Server` |
| `scum.ServerDescription` | string | Descrição do servidor | `Server Description` |
| `scum.ServerPassword` | string | Senha do servidor | (vazio) |
| `scum.MaxPlayers` | number | Máximo de jogadores | `64` |
| `scum.ServerBannerUrl` | string | URL do banner | (vazio) |
| `scum.ServerPlaystyle` | string | Estilo de jogo | `PVE`, `PVP`, `PVPvE` |
| `scum.WelcomeMessage` | string | Mensagem de boas-vindas | `Welcome to our SCUM Server` |
| `scum.MessageOfTheDay` | string | Mensagem do dia | `This is the Message of the Day.` |
| `scum.MessageOfTheDayCooldown` | float | Cooldown da mensagem (segundos) | `10.0` |
| `scum.MinServerTickRate` | number | Taxa mínima de tick | `5` |
| `scum.MaxServerTickRate` | number | Taxa máxima de tick | `30` |
| `scum.MaxPingCheckEnabled` | number | Habilitar verificação de ping | `1` (sim) / `0` (não) |
| `scum.MaxPing` | float | Ping máximo permitido | `200.0` |
| `scum.LogoutTimer` | float | Timer de logout (segundos) | `60.0` |
| `scum.LogoutTimerWhileCaptured` | float | Timer de logout quando capturado | `120.0` |
| `scum.LogoutTimerInBunker` | float | Timer de logout no bunker | `30000.0` |
| `scum.AllowFirstPerson` | number | Permitir primeira pessoa | `1` / `0` |
| `scum.AllowThirdPerson` | number | Permitir terceira pessoa | `1` / `0` |
| `scum.AllowCrosshair` | number | Permitir mira | `1` / `0` |
| `scum.AllowVoting` | number | Permitir votação | `1` / `0` |
| `scum.AllowMapScreen` | number | Permitir tela de mapa | `1` / `0` |
| `scum.AllowKillClaiming` | number | Permitir reivindicação de kill | `1` / `0` |
| `scum.AllowComa` | number | Permitir coma | `1` / `0` |
| `scum.AllowMinesAndTraps` | number | Permitir minas e armadilhas | `1` / `0` |
| `scum.AllowSkillGainInSafeZones` | number | Permitir ganho de skill em zonas seguras | `0` / `1` |
| `scum.AllowEvents` | number | Permitir eventos | `1` / `0` |
| `scum.LimitGlobalChat` | number | Limitar chat global | `0` / `1` |
| `scum.AllowGlobalChat` | number | Permitir chat global | `1` / `0` |
| `scum.AllowLocalChat` | number | Permitir chat local | `1` / `0` |
| `scum.AllowSquadChat` | number | Permitir chat de squad | `1` / `0` |
| `scum.AllowAdminChat` | number | Permitir chat de admin | `1` / `0` |
| `scum.RustyLocksLogging` | number | Log de fechaduras enferrujadas | `0` / `1` |
| `scum.HideKillNotification` | number | Ocultar notificação de kill | `1` / `0` |
| `scum.DisableTimedGifts` | number | Desabilitar presentes temporizados | `0` / `1` |
| `scum.UseMapBaseBuildingRestriction` | number | Usar restrição de construção no mapa | `1` / `0` |
| `scum.DisableBaseBuilding` | number | Desabilitar construção de base | `0` / `1` |
| `scum.VotingDuration` | float | Duração da votação (segundos) | `60.0` |
| `scum.PlayerMinimalVotingInterest` | float | Interesse mínimo de votação | `0.5` |
| `scum.PlayerPositiveVotePercentage` | float | Porcentagem de voto positivo | `0.5` |
| `scum.MasterServerUpdateSendInterval` | number | Intervalo de atualização do master server (segundos) | `60` |
| `scum.MasterServerIsLocalTest` | number | Master server é teste local | `0` / `1` |
| `scum.PartialWipe` | number | Wipe parcial | `0` / `1` |
| `scum.GoldWipe` | number | Wipe de ouro | `0` / `1` |
| `scum.FullWipe` | number | Wipe completo | `0` / `1` |
| `scum.ItemVirtualizationRelevancyUpdatePeriod` | float | Período de atualização de relevância | `1.0` |
| `scum.ItemVirtualizationEventProcessingTimeBudget` | float | Orçamento de tempo de processamento | `5.0` |
| `scum.ItemVirtualizationVisitorDistanceTravelledForUpdate` | float | Distância percorrida para atualização | `100.0` |
| `scum.ItemVirtualizationVisitorBounds` | float | Limites do visitante | `10000.0` |
| `scum.VirtualizedItemBounds` | float | Limites do item virtualizado | `100.0` |
| `scum.FameGainMultiplier` | float | Multiplicador de ganho de fama | `1.0` |
| `scum.FamePointPenaltyOnDeath` | float | Penalidade de fama na morte | `0.1` |
| `scum.FamePointPenaltyOnKilled` | float | Penalidade de fama ao ser morto | `0.5` |
| `scum.FamePointRewardOnKill` | float | Recompensa de fama ao matar | `0.25` |
| `scum.LogSuicides` | number | Log de suicídios | `0` / `1` |
| `scum.EnableSpawnOnGround` | number | Habilitar spawn no chão | `0` / `1` |
| `scum.DeleteInactiveUsers` | number | Deletar usuários inativos | `1` / `0` |
| `scum.DaysSinceLastLoginToBecomeInactive` | number | Dias para se tornar inativo | `180` |
| `scum.DeleteBannedUsers` | number | Deletar usuários banidos | `0` / `1` |
| `scum.MaximumTimeForChestsInForbiddenZones` | time | Tempo máximo para baús em zonas proibidas | `02:00:00` |
| `scum.LogChestOwnership` | number | Log de propriedade de baús | `1` / `0` |
| `scum.SettingsVersion` | number | Versão das configurações | `3` |
| `scum.DisableExamineGhost` | number | Desabilitar fantasma de exame | `0` / `1` |

### **2. [World] - Configurações do Mundo**

Configurações do ambiente e NPCs:

| Categoria | Chaves Principais | Descrição |
|-----------|-------------------|-----------|
| **Limites de Entidades** | `scum.MaxAllowedBirds`, `MaxAllowedCharacters`, `MaxAllowedPuppets`, `MaxAllowedAnimals`, `MaxAllowedNPCs`, `MaxAllowedDrones` | Limites de entidades no mundo |
| **Sentry** | `scum.DisableSentrySpawning`, `EnableSentryRespawning` | Configurações de sentry |
| **Puppets** | `scum.PuppetHealthMultiplier`, `PuppetRunningSpeedMultiplier`, `PuppetsCanOpenDoors`, `PuppetsCanVaultWindows` | Configurações de puppets |
| **Encounters** | `scum.EncounterBaseCharacterAmountMultiplier`, `EncounterExtraCharacterPerPlayerMultiplier`, `EncounterCharacterRespawnTimeMultiplier` | Multiplicadores de encontros |
| **Hordes** | `scum.EncounterHordeBaseCharacterAmountMultiplier`, `EncounterHordeActivationChanceMultiplier` | Configurações de hordas |
| **Tempo** | `scum.StartTimeOfDay`, `TimeOfDaySpeed`, `SunriseTime`, `SunsetTime`, `NighttimeDarkness` | Configurações de tempo/dia |
| **Cargo Drops** | `scum.CargoDropCooldownMinimum`, `CargoDropCooldownMaximum`, `CargoDropFallDelay` | Configurações de drops |
| **Hunts** | `scum.MaxAllowedHunts`, `HuntTriggerChanceOverride_*`, `HuntFailureTime` | Configurações de caças |
| **Animais** | `scum.BearMaxHealthMultiplier`, `BoarMaxHealthMultiplier`, `WolfMaxHealthMultiplier`, etc. | Multiplicadores de saúde dos animais |
| **Bunkers** | `scum.AbandonedBunkerMaxSimultaneouslyActive`, `AbandonedBunkerActiveDurationHours` | Configurações de bunkers |

### **3. [Respawn] - Configurações de Respawn**

Configurações de respawn e suicídio:

| Chave | Tipo | Descrição |
|-------|------|-----------|
| `scum.AllowSectorRespawn` | number | Permitir respawn por setor |
| `scum.AllowShelterRespawn` | number | Permitir respawn em abrigo |
| `scum.AllowSquadmateRespawn` | number | Permitir respawn com squadmate |
| `scum.RandomRespawnPrice` | number | Preço do respawn aleatório |
| `scum.SectorRespawnPrice` | number | Preço do respawn por setor |
| `scum.ShelterRespawnPrice` | string | Preço do respawn em abrigo (ex: `1g` = 1 ouro) |
| `scum.SquadRespawnPrice` | string | Preço do respawn com squad |
| `scum.*RespawnInitialTime` | float | Tempo inicial de cada tipo de respawn |
| `scum.*RespawnCooldown` | float | Cooldown de cada tipo de respawn |
| `scum.CommitSuicideInitialTime` | float | Tempo inicial para suicídio |
| `scum.CommitSuicideCooldown` | float | Cooldown para suicídio |
| `scum.PermadeathThreshold` | number | Limite de fama para permadeath |

### **4. [Vehicles] - Configurações de Veículos**

Configurações de veículos e drenagem de recursos:

| Categoria | Chaves Principais |
|-----------|-------------------|
| **Drenagem** | `scum.FuelDrainFromEngineMultiplier`, `BatteryDrainFromEngineMultiplier`, `BatteryChargeWithAlternatorMultiplier` |
| **Limites por Tipo** | `scum.KingletDusterMaxAmount`, `DirtbikeMaxAmount`, `LaikaMaxAmount`, `MotorboatMaxAmount`, etc. |
| **Funcionais** | `scum.*MaxFunctionalAmount` (para cada tipo de veículo) |
| **Mínimo Comprado** | `scum.*MinPurchasedAmount` (para cada tipo de veículo) |
| **Tempos** | `scum.MaximumTimeOfVehicleInactivity`, `MaximumTimeForVehiclesInForbiddenZones` |
| **Logs** | `scum.LogVehicleDestroyed` |

### **5. [Damage] - Multiplicadores de Dano**

Multiplicadores de dano para diferentes fontes:

| Chave | Descrição |
|-------|-----------|
| `scum.HumanToHumanDamageMultiplier` | Dano entre humanos |
| `scum.HumanToHumanArmedMeleeDamageMultiplier` | Dano corpo a corpo armado |
| `scum.HumanToHumanUnarmedMeleeDamageMultiplier` | Dano corpo a corpo desarmado |
| `scum.SentryDamageMultiplier` | Dano de sentry |
| `scum.DropshipDamageMultiplier` | Dano de dropship |
| `scum.ZombieDamageMultiplier` | Dano de zumbi |
| `scum.ItemDecayDamageMultiplier` | Dano de deterioração de itens |
| `scum.FoodDecayDamageMultiplier` | Dano de deterioração de comida |
| `scum.WeaponDecayDamageOnFiring` | Dano de deterioração ao atirar |
| `scum.LockProtectionDamageMultiplier` | Dano de proteção de fechadura |

### **6. [Features] - Recursos e Funcionalidades**

Configurações de recursos avançados:

| Categoria | Chaves Principais |
|-----------|-------------------|
| **Flags** | `scum.FlagOvertakeDuration`, `MaximumAmountOfElementsPerFlag`, `AllowMultipleFlagsPerPlayer` |
| **Base Building** | `scum.AllowFlagPlacementOnBBElements`, `MaximumNumberOfExpandedElementsPerFlag` |
| **Raid Protection** | `scum.RaidProtectionType`, `RaidProtectionEnableLog`, `RaidProtectionFlagSpecificMaxProtectionTime` |
| **Recursos** | `scum.WaterPricePerUnitMultiplier`, `GasolinePricePerUnitMultiplier`, `PropanePricePerUnitMultiplier` |
| **Skills** | `scum.ArcherySkillMultiplier`, `scum.AwarenessSkillMultiplier`, `scum.CookingSkillMultiplier`, etc. (todas as skills) |
| **Quests** | `scum.QuestsEnabled`, `QuestsGlobalCycleDuration`, `MaxQuestsPerCyclePerTrader` |
| **Turrets** | `scum.TurretsAttackPrisoners`, `TurretsAttackPuppets`, `TurretsAttackVehicles` |
| **Outros** | `scum.MovementInertiaAmount`, `scum.StaminaDrainOnJumpMultiplier`, `scum.EnableNewPlayerProtection` |

---

## 💡 Proposta de Funcionalidades

### **1. Leitura do ServerSettings.ini**

**Endpoint**: `GET /api/server/settings`

**Funcionalidade**: Ler todas as configurações do arquivo

**Resposta**:
```json
{
  "success": true,
  "data": {
    "general": {
      "ServerName": "SCUM Server",
      "MaxPlayers": 64,
      "ServerPlaystyle": "PVE",
      // ... todas as configurações
    },
    "world": {
      "MaxAllowedBirds": 15,
      // ...
    },
    "respawn": {
      // ...
    },
    "vehicles": {
      // ...
    },
    "damage": {
      // ...
    },
    "features": {
      // ...
    }
  },
  "timestamp": 1701504000
}
```

### **2. Leitura de Seção Específica**

**Endpoint**: `GET /api/server/settings?section=general`

**Funcionalidade**: Ler apenas uma seção específica

### **3. Leitura de Configuração Específica**

**Endpoint**: `GET /api/server/settings?key=scum.MaxPlayers`

**Funcionalidade**: Ler apenas uma configuração específica

### **4. Atualização de Configuração**

**Endpoint**: `PATCH /api/server/settings`

**Body**:
```json
{
  "section": "general",
  "key": "scum.MaxPlayers",
  "value": 100
}
```

**Ou atualização múltipla**:
```json
{
  "updates": [
    {
      "section": "general",
      "key": "scum.MaxPlayers",
      "value": 100
    },
    {
      "section": "general",
      "key": "scum.ServerName",
      "value": "Meu Servidor"
    }
  ]
}
```

### **5. Atualização de Seção Completa**

**Endpoint**: `PUT /api/server/settings/{section}`

**Body**:
```json
{
  "scum.MaxPlayers": 100,
  "scum.ServerName": "Meu Servidor",
  // ... todas as configurações da seção
}
```

### **6. Backup e Restore**

**Endpoint**: `POST /api/server/settings/backup`

**Endpoint**: `POST /api/server/settings/restore`

**Funcionalidade**: Criar backup antes de alterações e restaurar se necessário

### **7. Validação**

**Endpoint**: `POST /api/server/settings/validate`

**Funcionalidade**: Validar configurações antes de salvar

---

## 🔧 Implementação Técnica

### **Biblioteca para Parsing INI**

Python tem suporte nativo para arquivos INI através do módulo `configparser`:

```python
import configparser

config = configparser.ConfigParser()
config.read('ServerSettings.ini')

# Ler valor
max_players = config.get('General', 'scum.MaxPlayers')

# Escrever valor
config.set('General', 'scum.MaxPlayers', '100')
with open('ServerSettings.ini', 'w') as f:
    config.write(f)
```

### **Estrutura de Classes Proposta**

```python
class ServerSettingsManager:
    def __init__(self, config_directory: str):
        self.config_directory = Path(config_directory)
        self.settings_file = self.config_directory / 'ServerSettings.ini'
        self.parser = configparser.ConfigParser()
    
    def load_settings(self) -> Dict[str, Any]:
        """Carregar todas as configurações"""
    
    def get_section(self, section: str) -> Dict[str, str]:
        """Obter seção específica"""
    
    def get_value(self, section: str, key: str) -> Optional[str]:
        """Obter valor específico"""
    
    def set_value(self, section: str, key: str, value: Any) -> bool:
        """Definir valor específico"""
    
    def update_section(self, section: str, values: Dict[str, Any]) -> bool:
        """Atualizar seção completa"""
    
    def create_backup(self) -> str:
        """Criar backup do arquivo"""
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restaurar de backup"""
```

---

## ⚠️ Considerações Importantes

### **1. Formato de Valores**

- **Números**: Podem ser inteiros ou floats
- **Booleanos**: Representados como `0` ou `1`
- **Strings**: Texto simples
- **Tempos**: Formato `HH:MM:SS` ou `HH:MM`
- **Moedas**: Formato `{number}g` (ex: `1g`, `10g`)

### **2. Validação**

- Validar tipos de dados antes de salvar
- Validar ranges (ex: MaxPlayers entre 1-200)
- Validar formatos (ex: tempo, moeda)
- Validar valores permitidos (ex: ServerPlaystyle: PVE, PVP, PVPvE)

### **3. Backup**

- Sempre criar backup antes de modificar
- Manter histórico de backups
- Permitir restore fácil

### **4. Reinício do Servidor**

- Algumas configurações requerem reinício do servidor
- Identificar quais configurações requerem restart
- Notificar usuário quando necessário

### **5. Permissões**

- Verificar se usuário tem permissão para alterar configurações
- Logar todas as alterações
- Auditoria de mudanças

---

## 📋 Checklist de Implementação

- [ ] Criar classe `ServerSettingsManager`
- [ ] Implementar leitura de configurações
- [ ] Implementar escrita de configurações
- [ ] Implementar validação de valores
- [ ] Implementar sistema de backup
- [ ] Criar endpoint `GET /api/server/settings`
- [ ] Criar endpoint `GET /api/server/settings?section=X`
- [ ] Criar endpoint `GET /api/server/settings?key=X`
- [ ] Criar endpoint `PATCH /api/server/settings`
- [ ] Criar endpoint `PUT /api/server/settings/{section}`
- [ ] Criar endpoint `POST /api/server/settings/backup`
- [ ] Criar endpoint `POST /api/server/settings/restore`
- [ ] Adicionar validações
- [ ] Adicionar logging
- [ ] Criar documentação
- [ ] Adicionar ao Postman collection

---

**Última atualização**: 02/12/2025

