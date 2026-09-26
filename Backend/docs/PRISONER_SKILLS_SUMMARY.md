# 📊 Resumo: Sistema de Skills - Decisões e Especificações

## 🎯 Informações Confirmadas

### Significados das Siglas
- **FOR = Força**
- **INT = Inteligência**  
- **CON = Constituição**
- **DES = Destreza**

### Níveis Máximos por Grupo

| Grupo | Nível Máximo | Tipo | Observação |
|-------|--------------|------|------------|
| **FOR (Força)** | **8** | Permanente | Pode chegar a 8 permanentemente (não temporário) |
| **INT (Inteligência)** | **8** | Temporário | Pode chegar a 8 apenas com boost temporário |
| **CON (Constituição)** | **5** | Permanente | Máximo fixo em 5 |
| **DES (Destreza)** | **5** | Degradável | Máximo 5, mas **pode diminuir** se parar de treinar |

### ⚠️ Característica Especial: Degradação de DES

**Skills de Destreza (DES) podem diminuir com o tempo se o personagem parar de treinar.**

**Implicações:**
- ✅ Necessário sincronizar com frequência (24h) para capturar mudanças
- ✅ Sincronizar todos os jogadores (mesmo offline) para capturar degradação
- ✅ Estado atual é atualizado, refletindo a degradação quando ocorrer

## 🔄 Frequência de Sincronização

**Recomendação: A cada 24 horas**

**Motivos:**
1. Capturar degradação de skills DES quando jogador não treina
2. Balance entre atualização e performance
3. Atualizar estado atual das skills regularmente

## 📊 Estrutura Proposta

### Tabela: `player_skills`

```sql
CREATE TABLE IF NOT EXISTS player_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Identificação do jogador
    steam_id TEXT NOT NULL,
    player_name TEXT,
    prisoner_id INTEGER,
    
    -- Dados da skill
    skill_name TEXT NOT NULL,
    skill_group TEXT,  -- 'FOR', 'CON', 'DES', 'INT', ou NULL (skill não mapeada)
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
```

**Notas Importantes:** 
- ✅ Não mantém histórico, apenas estado atual. Atualização via `INSERT OR REPLACE`.
- ✅ **Monitora TODAS as skills** do banco, não apenas as mapeadas (flexível para novas skills do jogo).
- ✅ Skills não mapeadas terão `skill_group = NULL` até serem adicionadas ao mapeamento.
- ✅ Sistema preparado para receber novas skills em atualizações futuras do jogo.

### Lógica de max_level e boost

```python
def calculate_max_level_and_boost(skill_group: Optional[str], level: int) -> tuple:
    """
    Calcula max_level e is_temporary_boost baseado no grupo e nível
    
    Args:
        skill_group: 'FOR', 'CON', 'DES', 'INT', ou None (skill não mapeada)
        level: Nível atual da skill
    
    Returns:
        (max_level, is_temporary_boost)
    """
    if skill_group == 'FOR':
        # FOR pode ser 8 permanentemente
        return (8, False)
    
    elif skill_group == 'INT':
        # INT pode ser 8 temporariamente
        if level > 5:
            return (8, True)  # Boost temporário
        else:
            return (5, False)
    
    elif skill_group in ('CON', 'DES'):
        # CON e DES sempre máximo 5
        return (5, False)
    
    else:  # skill_group é None (skill não mapeada)
        # Para skills não mapeadas, usar 5 como padrão
        # Pode ser ajustado depois quando a skill for identificada
        return (5, False)
```

## 🎨 Mapeamento de Skills

### FOR (Força) - 5 skills
- BoxingSkill (Briga)
- MeleeWeaponsSkill (Armas brancas)
- ArcherySkill (Arquearia)
- RiflesSkill (Fuzis)
- HandgunSkill (Pistola)

### INT (Inteligência) - 8 skills
- AwarenessSkill (Percepção)
- CamouflageSkill (Camuflagem)
- CookingSkill (Culinária)
- MedicalSkill (Medicina)
- SnipingSkill (Tiro de precisão)
- SurvivalSkill (Sobrevivência)
- EngineeringSkill (Engenharia)
- FarmingSkill (Agricultura)

### CON (Constituição) - 2 skills
- RunningSkill (Corrida)
- EnduranceSkill (Resiliência)

### DES (Destreza) - 6 skills ⚠️ Degradável
- ThieverySkill (Roubo)
- DemolitionSkill (Demolição)
- StealthSkill (Furtividade)
- DrivingSkill (Condução)
- MotorcycleSkill (Motociclismo)
- AviationSkill (Avião)

### Skills Não Mapeadas (aguardando identificação)
- ResistanceSkill (Resistência) - ⚠️ Presente no banco, mas não informada
- TacticsSkill (Táticas) - ⚠️ Presente no banco, mas não informada

**Total:** 21 skills mapeadas de 23 encontradas no banco

## 📝 Decisões Confirmadas

- [x] **Estrutura:** Tabela de estado atual (sem histórico)
- [x] **Frequência:** 24 horas
- [x] **Histórico:** Não necessário (apenas acompanhar estado atual)
- [x] **Jogadores:** Todos (online e offline)
- [x] **Skills:** Monitorar TODAS as skills (flexível para novas skills do jogo)
- [x] **Níveis máximos:** FOR=8 (permanente), INT=8 (temporário), CON/DES=5
- [x] **Degradação DES:** Capturar com atualizações frequentes (24h)
- [x] **Atualização:** `INSERT OR REPLACE` baseado em `steam_id` + `skill_name`
- [x] **Skills não mapeadas:** Armazenar com `skill_group = NULL` (pode ser mapeada depois)

## 🚀 Próximos Passos (se implementar)

1. Criar `PlayerSkillsSyncService`
2. Implementar mapeamento de skills → grupos
3. Implementar lógica de max_level e boost
4. Criar tabela `player_skills` (estado atual)
5. Criar endpoints da API
6. Documentar para frontend

