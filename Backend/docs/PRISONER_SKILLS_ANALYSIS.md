# 📊 Análise: Tabela `prisoner_skill` - Proposta de Implementação

## 📋 Visão Geral

A tabela `prisoner_skill` no banco `SCUM.db` armazena as **habilidades (skills) de cada jogador/prisioneiro** no servidor SCUM. Cada registro representa uma skill específica de um jogador, incluindo seu nível, experiência e dados XML adicionais.

### ⚠️ Características Importantes

**Significados das Siglas:**
- **FOR = Força**
- **INT = Inteligência**
- **CON = Constituição**
- **DES = Destreza**

**Regras de Níveis Máximos:**
- **FOR (Força):** Pode chegar a nível 8 permanentemente
- **INT (Inteligência):** Pode chegar a nível 8 temporariamente (com boost)
- **CON (Constituição):** Máximo nível 5
- **DES (Destreza):** Máximo nível 5, mas **pode diminuir com o tempo** se o personagem parar de treinar

**⚠️ IMPORTANTE - Degradação de Skills:**
- Skills de **DES (Destreza)** podem diminuir se o personagem parar de treinar
- Por isso é **essencial sincronizar com frequência (24h)** para capturar essas mudanças
- Manter histórico de snapshots permite detectar quando skills diminuíram ao longo do tempo

## 🗄️ Estrutura Atual no SCUM.db

### Schema
```sql
CREATE TABLE prisoner_skill (
    prisoner_id INTEGER,
    name TEXT,
    level INTEGER,
    experience REAL,
    xml TEXT
);
```

### Dados Encontrados

**Total de skills diferentes encontradas:** 23

**⚠️ IMPORTANTE:** O sistema deve monitorar **TODAS as skills** presentes no banco, não apenas as listadas abaixo. O jogo pode adicionar novas skills em atualizações futuras.

**Skills mapeadas:** 21 de 23
**Skills não mapeadas:** 2 (ResistanceSkill, TacticsSkill) - serão armazenadas com `skill_group = NULL`

**Skills identificadas atualmente:**
- ArcherySkill (Arquearia)
- AviationSkill (Aviação)
- AwarenessSkill (Percepção)
- BoxingSkill (Briga)
- CamouflageSkill (Camuflagem)
- CookingSkill (Culinária)
- DemolitionSkill (Demolição)
- DrivingSkill (Condução)
- EnduranceSkill (Resiliência)
- EngineeringSkill (Engenharia)
- FarmingSkill (Agricultura)
- HandgunSkill (Pistola)
- MedicalSkill (Medicina)
- MeleeWeaponsSkill (Armas brancas)
- MotorcycleSkill (Motociclismo)
- ResistanceSkill (Resistência)
- RiflesSkill (Fuzis)
- RunningSkill (Corrida)
- SnipingSkill (Tiro de precisão)
- StealthSkill (Furtividade)
- SurvivalSkill (Sobrevivência)
- TacticsSkill (Táticas)
- ThieverySkill (Roubo)

**Níveis observados:**
- Nível máximo encontrado nos dados: 3
- Nível máximo padrão: 5 (para CON e DES)
- Nível máximo FOR: 8 (permanente, não temporário)
- Nível máximo INT: 8 (temporário, com boost)

## 🎯 Agrupamento por Atributos (FOR, CON, DES, INT)

Com base nos prints do jogo, as skills são agrupadas em 4 categorias principais:

### **FOR (Força/Strength)**
- BoxingSkill (Briga)
- MeleeWeaponsSkill (Armas brancas)
- ArcherySkill (Arquearia)
- RiflesSkill (Fuzis)
- HandgunSkill (Pistola)

### **INT (Inteligência/Intelligence)**
- AwarenessSkill (Percepção)
- CamouflageSkill (Camuflagem)
- CookingSkill (Culinária)
- MedicalSkill (Medicina)
- SnipingSkill (Tiro de precisão)
- SurvivalSkill (Sobrevivência)
- EngineeringSkill (Engenharia)
- FarmingSkill (Agricultura)

### **CON (Constituição/Constitution)**
- RunningSkill (Corrida)
- EnduranceSkill (Resiliência)

### **DES (Destreza/Dexterity)**
- ThieverySkill (Roubo)
- DemolitionSkill (Demolição)
- StealthSkill (Furtividade)
- DrivingSkill (Condução)
- MotorcycleSkill (Motociclismo)
- AviationSkill (Avião)

**⚠️ IMPORTANTE:** Skills de DES (Destreza) podem **diminuir com o tempo** se o personagem parar de treinar. Por isso é importante sincronizar com frequência (24h) para capturar essas mudanças.

### **Skills Não Mapeadas (aguardando identificação)**
- ResistanceSkill (Resistência) - ⚠️ Presente no banco, mas não informada pelo usuário
- TacticsSkill (Táticas) - ⚠️ Presente no banco, mas não informada pelo usuário

**Nota:** Essas skills serão armazenadas com `skill_group = NULL` até serem identificadas e mapeadas.

## 💡 Proposta de Estrutura no SSM.db

### Opção 1: Tabela de Estado Atual (Recomendada)

Mantém apenas o estado atual das skills, sem histórico:

```sql
CREATE TABLE IF NOT EXISTS player_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Identificação do jogador
    steam_id TEXT NOT NULL,
    player_name TEXT,
    prisoner_id INTEGER,
    
    -- Dados da skill
    skill_name TEXT NOT NULL,
    skill_group TEXT,  -- 'FOR', 'CON', 'DES', 'INT'
    level INTEGER NOT NULL,
    experience REAL NOT NULL,
    max_level INTEGER DEFAULT 5,  -- 5 para CON/DES, 8 para FOR (permanente) e INT (temporário)
    is_temporary_boost BOOLEAN DEFAULT 0,  -- Para INT > 5 (FOR pode ser 8 permanentemente)
    
    -- Metadados
    last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Índices
    UNIQUE(steam_id, skill_name),
    FOREIGN KEY (steam_id) REFERENCES players(steam_id)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_player_skills_steam_id ON player_skills(steam_id);
CREATE INDEX IF NOT EXISTS idx_player_skills_group ON player_skills(skill_group);
```

### Estrutura Simplificada

Como não há necessidade de histórico, a estrutura é mais simples:
- Uma única tabela `player_skills` com estado atual
- `UNIQUE(steam_id, skill_name)` garante apenas um registro por skill por jogador
- Atualização: `INSERT OR REPLACE` ou `UPDATE` baseado em `steam_id` + `skill_name`

## 🔄 Proposta de Sincronização

### Serviço: `PlayerSkillsSyncService`

Similar ao `SurvivalStatsSyncService`, mas adaptado para skills:

```python
class PlayerSkillsSyncService:
    """Sincroniza prisoner_skill do SCUM.db para SSM.db"""
    
    def __init__(self, config, path_helper, logger):
        # Configuração similar ao survival_stats
        self.sync_interval_hours = 24  # Padrão: 24 horas (DES pode diminuir se não treinar)
        self.scum_db_path = ...
        self.ssm_db_path = ...
        
    def sync_once(self):
        """Executar sincronização única"""
        # 1. Buscar todos os prisoner_id únicos
        # 2. Para cada prisoner_id:
        #    - Buscar TODAS as skills do SCUM.db (não apenas as mapeadas)
        #    - Tentar mapear skill_name para skill_group
        #      * Se mapeada: usar grupo conhecido
        #      * Se não mapeada: skill_group = NULL (nova skill do jogo)
        #    - Calcular max_level:
        #      * FOR: sempre 8 (permanente)
        #      * INT: 8 se level > 5 (temporário), senão 5
        #      * CON e DES: sempre 5
        #      * NULL (não mapeada): usar 5 como padrão (pode ser ajustado depois)
        #    - Identificar boost temporário (apenas INT > 5)
        #    - Inserir ou atualizar no SSM.db (INSERT OR REPLACE)
        # 3. Atualizar last_updated para cada skill
```

### Mapeamento de Skills para Grupos

```python
SKILL_GROUPS = {
    'FOR': [
        'BoxingSkill',           # Briga
        'MeleeWeaponsSkill',      # Armas brancas
        'ArcherySkill',           # Arquearia
        'RiflesSkill',            # Fuzis
        'HandgunSkill'            # Pistola
    ],
    'INT': [
        'AwarenessSkill',         # Percepção
        'CamouflageSkill',        # Camuflagem
        'CookingSkill',           # Culinária
        'MedicalSkill',          # Medicina
        'SnipingSkill',          # Tiro de precisão
        'SurvivalSkill',         # Sobrevivência
        'EngineeringSkill',      # Engenharia
        'FarmingSkill'           # Agricultura
    ],
    'CON': [
        'RunningSkill',          # Corrida
        'EnduranceSkill'         # Resiliência
    ],
    'DES': [
        'ThieverySkill',         # Roubo
        'DemolitionSkill',       # Demolição
        'StealthSkill',          # Furtividade
        'DrivingSkill',          # Condução
        'MotorcycleSkill',       # Motociclismo
        'AviationSkill'          # Avião
    ]
}

# Função para determinar grupo de skill desconhecida
def get_skill_group(skill_name: str) -> Optional[str]:
    """Determina o grupo de uma skill. Retorna None se não mapeada."""
    for group, skills in SKILL_GROUPS.items():
        if skill_name in skills:
            return group
    # Se skill não está mapeada, retorna None (será tratada como desconhecida)
    return None
```

**⚠️ IMPORTANTE:** 
- O sistema deve processar **TODAS as skills** encontradas no banco, não apenas as mapeadas
- Skills não mapeadas devem ser armazenadas com `skill_group = NULL`
- O frontend pode exibir skills não mapeadas em uma seção "Outras" ou similar
- Quando novas skills forem identificadas, o mapeamento pode ser atualizado
- **Flexibilidade:** Sistema deve suportar qualquer quantidade de skills (novas skills do jogo)

### Processamento de Skills Desconhecidas

```python
# Exemplo de lógica de processamento
def process_skill(skill_name: str, level: int, experience: float):
    # Tentar mapear para grupo conhecido
    skill_group = get_skill_group(skill_name)
    
    # Se não mapeada, skill_group será None
    # Isso permite que novas skills sejam armazenadas mesmo sem mapeamento
    
    # Calcular max_level (usa padrão 5 se grupo desconhecido)
    max_level, is_boost = calculate_max_level_and_boost(skill_group, level)
    
    # Armazenar no banco (skill_group pode ser NULL)
    # Quando a skill for identificada, pode ser atualizada depois
```

## 📊 Estrutura de Dados para Frontend

### Resposta da API (Exemplo)

```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "player_name": "Pedreiro",
    "last_updated": "2025-01-15T10:30:00Z",
    "attribute_totals": {
      "FOR": 5.3,
      "CON": 4.6,
      "DES": 5.0,
      "INT": 5.0
    },
    "skills": {
      "FOR": [
        {
          "name": "BoxingSkill",
          "display_name": "Briga",
          "level": 5,
          "experience": 0.0,
          "max_level": 5,
          "percentage": 100,
          "is_maxed": true
        },
        {
          "name": "MeleeWeaponsSkill",
          "display_name": "Armas brancas",
          "level": 5,
          "experience": 0.0,
          "max_level": 5,
          "percentage": 100,
          "is_maxed": true
        },
        {
          "name": "ArcherySkill",
          "display_name": "Arquearia",
          "level": 1,
          "experience": 500.0,
          "max_level": 5,
          "percentage": 24,
          "is_maxed": false
        }
      ],
      "CON": [...],
      "DES": [...],
      "INT": [...],
      "UNKNOWN": [  // Skills não mapeadas
        {
          "name": "NovaSkillDoJogo",
          "display_name": "NovaSkillDoJogo",
          "level": 2,
          "experience": 500.0,
          "max_level": 5,
          "percentage": 40,
          "is_maxed": false,
          "skill_group": null
        }
      ]
    }
  }
}
```

## 🎨 Considerações para Frontend

### 1. Cálculo de Atributos Totais (FOR, CON, DES, INT)

Os valores nos círculos (5.3, 4.6, 5.0, 5.0) podem ser calculados como:
- **Média dos níveis** das skills do grupo
- **Soma ponderada** (com pesos diferentes por skill)
- **Média com experiência** (considerando progresso para próximo nível)

**Nota importante:** 
- **FOR:** Pode chegar até 8.0 permanentemente (não é temporário)
- **INT:** Pode chegar até 8.0 temporariamente (com boost)
- **CON e DES:** Máximo 5.0

### 2. Níveis Máximos

- **Nível máximo CON e DES:** 5 (permanente)
- **Nível máximo FOR:** 8 (permanente, não temporário)
- **Nível máximo INT:** 8 (temporário, apenas quando há boost)
- **Flag `is_temporary_boost`:** Indica se o nível > 5 é temporário (aplica-se apenas a INT)
- **Lógica:**
  - `FOR`: `max_level = 8` sempre, `is_temporary_boost = 0`
  - `INT`: Se `level > 5`, então `max_level = 8` e `is_temporary_boost = 1`; senão `max_level = 5`
  - `CON` e `DES`: `max_level = 5` sempre, `is_temporary_boost = 0`

### 3. Porcentagens e Barras de Progresso

```typescript
// Cálculo de porcentagem
percentage = (level / max_level) * 100

// Para experiência dentro do nível atual
// (precisa saber experiência necessária para próximo nível)
experience_percentage = (current_experience / experience_to_next_level) * 100
```

### 4. Nomes de Exibição

Mapeamento de `skill_name` para nome amigável:
```python
SKILL_DISPLAY_NAMES = {
    'BoxingSkill': 'Briga',
    'MeleeWeaponsSkill': 'Armas brancas',
    'ArcherySkill': 'Arquearia',
    'ThieverySkill': 'Roubo',
    'DemolitionSkill': 'Demolição',
    'StealthSkill': 'Furtividade',
    'EnduranceSkill': 'Resiliência',
    'ResistanceSkill': 'Resistência',
    'RunningSkill': 'Corrida',
    'SurvivalSkill': 'Sobrevivência',
    'DrivingSkill': 'Condução',
    'MotorcycleSkill': 'Motociclismo',
    'AviationSkill': 'Aviação',
    'RiflesSkill': 'Fuzis',
    'HandgunSkill': 'Pistola',
    'SnipingSkill': 'Tiro de precisão',
    'AwarenessSkill': 'Percepção',
    'CamouflageSkill': 'Camuflagem',
    'CookingSkill': 'Culinária',
    'MedicalSkill': 'Medicina',
    'EngineeringSkill': 'Engenharia',
    'FarmingSkill': 'Agricultura',
    'TacticsSkill': 'Táticas'
}

def get_display_name(skill_name: str) -> str:
    """Retorna nome amigável da skill, ou o próprio nome se não mapeada."""
    return SKILL_DISPLAY_NAMES.get(skill_name, skill_name)
```

**Nota:** Skills não mapeadas usarão o próprio `skill_name` como display_name até serem adicionadas ao mapeamento.

## 🔧 Funcionalidades Propostas

### 1. Sincronização Automática
- **Frequência recomendada:** A cada 24 horas
- **Motivo:** Skills de DES (Destreza) podem diminuir com o tempo se o personagem parar de treinar
- Sincronizar todos os jogadores (para capturar degradação de DES)
- **Estado atual apenas:** Não mantém histórico, apenas atualiza o estado atual das skills

### 2. Endpoints da API

```
GET /api/skills/player/{steam_id}
GET /api/skills/leaderboard?group=FOR&metric=level
GET /api/skills/stats?steam_id=...
GET /api/skills/sync/status
POST /api/skills/sync/run-now
```

### 3. Agregações Úteis

- **Top players por skill group**
- **Comparação entre jogadores**
- **Estatísticas gerais do servidor**
- **Skills não mapeadas:** Endpoint para listar skills com `skill_group = NULL` (novas skills do jogo)

### 4. Tratamento de Novas Skills

Quando o jogo adicionar novas skills:

1. **Detecção Automática:** O sistema detecta automaticamente skills não mapeadas (`skill_group = NULL`)
2. **Armazenamento:** Skills são armazenadas normalmente, apenas sem grupo definido
3. **Identificação:** Administrador pode identificar a skill e adicionar ao mapeamento
4. **Atualização:** Após mapear, executar atualização em lote para definir `skill_group` das skills já armazenadas

**Endpoint sugerido:**
```
GET /api/skills/unmapped
POST /api/skills/map/{skill_name}  # Mapear skill para grupo
```

## ⚠️ Pontos de Atenção

1. **Performance:** N skills × M jogadores = muitos registros
   - Solução: Índices adequados e sincronização incremental
   - **Flexibilidade:** Sistema deve suportar qualquer quantidade de skills (novas skills do jogo)

2. **Histórico:** Não necessário
   - Apenas estado atual das skills
   - Atualização: `INSERT OR REPLACE` baseado em `steam_id` + `skill_name`

3. **Níveis máximos diferentes:**
   - **FOR:** Sempre `max_level = 8` (permanente, não temporário)
   - **INT:** `max_level = 8` apenas quando `level > 5` (temporário)
   - **CON e DES:** Sempre `max_level = 5`
   - **Lógica:** 
     - Se `skill_group = 'FOR'`: `max_level = 8`, `is_temporary_boost = 0`
     - Se `skill_group = 'INT'` e `level > 5`: `max_level = 8`, `is_temporary_boost = 1`
     - Se `skill_group = 'INT'` e `level <= 5`: `max_level = 5`, `is_temporary_boost = 0`
     - Se `skill_group IN ('CON', 'DES')`: `max_level = 5`, `is_temporary_boost = 0`

4. **Degradação de DES:** Skills de Destreza podem diminuir se não treinar
   - **Importante:** Sincronizar com frequência (24h) para capturar essas mudanças
   - **Atualização:** Estado atual é atualizado, refletindo a degradação quando ocorrer

5. **Experiência para próximo nível:** Não está no banco
   - Solução: Calcular baseado em fórmulas do jogo ou estimar

6. **Jogadores offline:** Sincronizar todos ou apenas online?
   - Recomendação: Todos (para capturar degradação de DES mesmo quando offline)

## 📝 Próximos Passos

1. ✅ **Definir estrutura final:** Tabela `player_skills` (estado atual, sem histórico)
2. ✅ **Monitorar todas as skills:** Sistema flexível para novas skills do jogo
3. ⏳ **Criar mapeamento inicial** de skills conhecidas para grupos
4. ⏳ **Implementar PlayerSkillsSyncService** (sincronização a cada 24h, todas as skills)
5. ⏳ **Criar endpoints da API**
6. ⏳ **Documentar para frontend**

## 🤔 Decisões Pendentes

- [x] Estrutura da tabela: Estado atual apenas (sem histórico)
- [x] Frequência de sincronização: 24 horas (para capturar degradação de DES)
- [x] Manter histórico: Não necessário
- [ ] Como calcular atributos totais (FOR, CON, DES, INT)
- [x] Como identificar boost temporário: Apenas INT > 5 é temporário; FOR pode ser 8 permanentemente
- [x] Sincronizar todos os jogadores: Sim (para capturar degradação mesmo quando offline)

