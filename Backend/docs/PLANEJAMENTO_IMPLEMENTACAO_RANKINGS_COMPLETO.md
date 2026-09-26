# 📋 Planejamento: Implementação de Rankings Completos para Gestão

> **Data:** 2025-01-XX  
> **Status:** ✅ Pronto para Implementação  
> **Tempo Estimado:** 2-4 horas  
> **Prioridade:** Média

---

## 🎯 Objetivo

Atualizar o método `_get_rankings_data()` no `GestaoSyncService` para enviar **todos os campos de rankings** no formato completo, permitindo que o Gestão crie **15 rankings automáticos** ao invés de apenas 4.

---

## 📊 Situação Atual vs. Desejada

### **Antes (4 Rankings):**
```json
{
  "rankings": {
    "kills": [...],
    "survival": [...],
    "lockpicking": [...],
    "fishing": [...]
  }
}
```

### **Agora (15 Rankings Automáticos):**
```json
{
  "rankings": {
    "data": {
      "players": [
        {
          "steam_id": "...",
          "player_name": "...",
          "kills": 250,
          "deaths": 10,
          "kdr": 25.0,
          "headshots": 200,
          "players_knocked_out": 15,
          "animals_killed": 50,
          "minutes_survived": 200000.0,
          "total_fame": 50000.0,
          "vehicles_destroyed": 5,
          "suicides": 0,
          "overdoses": 0,
          "highest_weight_carried": 250.0,
          "highest_defecation": 300,
          "longest_shot": {
            "distance": 500.5,
            "weapon": "SVD",
            "timestamp": "2025-01-15T09:30:00Z"
          },
          "lockpicking": {
            "basic": { "success": 20, "fails": 5, "total": 25, "rate": 80.0 },
            "medium": { "success": 10, "fails": 2, "total": 12, "rate": 83.33 },
            "advanced": { "success": 5, "fails": 1, "total": 6, "rate": 83.33 },
            "veryeasy": { "success": 0, "fails": 0, "total": 0, "rate": 0.0 },
            "diallock": { "success": 0, "fails": 0, "total": 0, "rate": 0.0 },
            "other": { "success": 0, "fails": 0, "total": 0, "rate": 0.0 }
          },
          "last_updated": "2025-01-15T10:00:00Z"
        }
      ]
    }
  }
}
```

---

## 🔍 Análise do Código Atual

### **Arquivo:** `core/communication/gestao_sync_service.py`

**Método atual:** `_get_rankings_data()` (linhas 492-600)

**Problemas:**
- ❌ Retorna apenas 4 categorias separadas
- ❌ Não inclui todos os campos disponíveis
- ❌ Estrutura diferente do formato esperado

**Solução:**
- ✅ Reutilizar lógica do endpoint `/api/rankings/list` (linhas 9303-9525 em `main.py`)
- ✅ Retornar formato completo com todos os campos
- ✅ Estrutura `rankings.data.players[]`

---

## 📝 Implementação

### **Passo 1: Modificar `_get_rankings_data()`**

**Arquivo:** `core/communication/gestao_sync_service.py`

**Mudanças:**
1. Substituir queries separadas por uma query única
2. Retornar todos os campos da tabela `rankings`
3. Formatar dados no formato esperado pelo Gestão
4. Incluir estrutura completa de `lockpicking` (6 tipos)
5. Incluir estrutura completa de `longest_shot`

---

## 🔧 Estrutura do Código

### **Query SQL (Reutilizar do `/api/rankings/list`):**

```sql
SELECT steam_id, player_name,
       kills, deaths, kdr,
       longest_shot_distance, longest_shot_weapon, longest_shot_timestamp,
       suicides,
       lockpick_basic_success, lockpick_basic_fails, lockpick_basic_total, lockpick_basic_rate,
       lockpick_medium_success, lockpick_medium_fails, lockpick_medium_total, lockpick_medium_rate,
       lockpick_advanced_success, lockpick_advanced_fails, lockpick_advanced_total, lockpick_advanced_rate,
       lockpick_veryeasy_success, lockpick_veryeasy_fails, lockpick_veryeasy_total, lockpick_veryeasy_rate,
       lockpick_diallock_success, lockpick_diallock_fails, lockpick_diallock_total, lockpick_diallock_rate,
       lockpick_other_success, lockpick_other_fails, lockpick_other_total, lockpick_other_rate,
       vehicles_destroyed,
       highest_defecation, animals_killed, players_knocked_out,
       headshots, minutes_survived, overdoses, highest_weight_carried,
       total_fame,
       last_updated
FROM rankings
ORDER BY kills DESC, kdr DESC
LIMIT 1000
```

### **Formatação dos Dados:**

```python
def _get_rankings_data(self) -> Dict[str, Any]:
    """
    Obter dados de rankings no formato completo para Gestão
    
    Retorna formato: rankings.data.players[]
    """
    rankings_data = {
        "data": {
            "players": []
        }
    }
    
    # Query SQL (reutilizar do /api/rankings/list)
    # ... query completa ...
    
    for row in cursor.fetchall():
        player_data = {
            "steam_id": row['steam_id'],
            "player_name": row['player_name'],
            "kills": row['kills'] or 0,
            "deaths": row['deaths'] or 0,
            "kdr": row['kdr'] or 0.0,
            "headshots": row['headshots'] or 0,
            "players_knocked_out": row['players_knocked_out'] or 0,
            "animals_killed": row['animals_killed'] or 0,
            "minutes_survived": row['minutes_survived'] or 0.0,
            "total_fame": row['total_fame'] or 0.0,
            "vehicles_destroyed": row['vehicles_destroyed'] or 0,
            "suicides": row['suicides'] or 0,
            "overdoses": row['overdoses'] or 0,
            "highest_weight_carried": row['highest_weight_carried'] or 0.0,
            "highest_defecation": row['highest_defecation'] or 0,
            "longest_shot": {
                "distance": row['longest_shot_distance'] or 0.0,
                "weapon": row['longest_shot_weapon'] or "",
                "timestamp": row['longest_shot_timestamp'] or None
            },
            "lockpicking": {
                "basic": {
                    "success": row['lockpick_basic_success'] or 0,
                    "fails": row['lockpick_basic_fails'] or 0,
                    "total": row['lockpick_basic_total'] or 0,
                    "rate": row['lockpick_basic_rate'] or 0.0
                },
                "medium": {
                    "success": row['lockpick_medium_success'] or 0,
                    "fails": row['lockpick_medium_fails'] or 0,
                    "total": row['lockpick_medium_total'] or 0,
                    "rate": row['lockpick_medium_rate'] or 0.0
                },
                "advanced": {
                    "success": row['lockpick_advanced_success'] or 0,
                    "fails": row['lockpick_advanced_fails'] or 0,
                    "total": row['lockpick_advanced_total'] or 0,
                    "rate": row['lockpick_advanced_rate'] or 0.0
                },
                "veryeasy": {
                    "success": row['lockpick_veryeasy_success'] or 0,
                    "fails": row['lockpick_veryeasy_fails'] or 0,
                    "total": row['lockpick_veryeasy_total'] or 0,
                    "rate": row['lockpick_veryeasy_rate'] or 0.0
                },
                "diallock": {
                    "success": row['lockpick_diallock_success'] or 0,
                    "fails": row['lockpick_diallock_fails'] or 0,
                    "total": row['lockpick_diallock_total'] or 0,
                    "rate": row['lockpick_diallock_rate'] or 0.0
                },
                "other": {
                    "success": row['lockpick_other_success'] or 0,
                    "fails": row['lockpick_other_fails'] or 0,
                    "total": row['lockpick_other_total'] or 0,
                    "rate": row['lockpick_other_rate'] or 0.0
                }
            },
            "last_updated": row['last_updated'] or None
        }
        
        rankings_data["data"]["players"].append(player_data)
    
    return rankings_data
```

---

## ✅ Checklist de Implementação

### **Campos a Incluir:**
- [x] `steam_id` - já existe
- [x] `player_name` - já existe
- [ ] `rank` - opcional (pode calcular ou omitir)
- [x] `kills` - já existe
- [x] `deaths` - já existe
- [x] `kdr` - já existe
- [ ] `headshots` - **NOVO**
- [ ] `players_knocked_out` - **NOVO**
- [x] `animals_killed` - já existe
- [x] `minutes_survived` - já existe
- [ ] `total_fame` - **NOVO**
- [ ] `vehicles_destroyed` - **NOVO**
- [ ] `suicides` - **NOVO**
- [ ] `overdoses` - **NOVO**
- [ ] `highest_weight_carried` - **NOVO**
- [ ] `highest_defecation` - **NOVO**
- [ ] `longest_shot` (objeto completo) - **NOVO**
- [ ] `lockpicking` (6 tipos completos) - **MELHORAR**
- [ ] `last_updated` - **NOVO**

### **Estruturas a Garantir:**
- [ ] `longest_shot` sempre presente (mesmo que vazio)
- [ ] `lockpicking` sempre com 6 tipos (mesmo que vazios)
- [ ] Valores padrão para campos `None` (0 ou 0.0)

### **Formato:**
- [ ] Estrutura `rankings.data.players[]`
- [ ] Timestamps em formato ISO 8601 com timezone

---

## 🧪 Testes

### **1. Teste de Estrutura**
- Verificar que payload tem estrutura `rankings.data.players[]`
- Verificar que todos os campos estão presentes
- Verificar valores padrão quando campos são `None`

### **2. Teste de Dados**
- Verificar que dados vêm da tabela `rankings`
- Verificar que `lockpicking` tem todos os 6 tipos
- Verificar que `longest_shot` está sempre presente

### **3. Teste de Integração**
- Enviar payload para Gestão
- Verificar resposta: `rankings_created` deve ser ~15x número de players
- Verificar logs do Gestão

---

## 📋 Resumo das Mudanças

### **Arquivo a Modificar:**
- `core/communication/gestao_sync_service.py`
  - Método: `_get_rankings_data()` (linhas 492-600)

### **Mudanças Principais:**
1. Substituir queries separadas por query única
2. Retornar formato `rankings.data.players[]`
3. Incluir todos os 15 campos de métricas
4. Garantir estrutura completa de `lockpicking` (6 tipos)
5. Garantir estrutura completa de `longest_shot`

### **Reutilização:**
- ✅ Query SQL do endpoint `/api/rankings/list` (linhas 9379-9396 em `main.py`)
- ✅ Lógica de formatação similar

---

## 🎯 Próximos Passos

1. ✅ **Análise Completa** - Concluída
2. ⏳ **Implementação** - Modificar `_get_rankings_data()`
3. ⏳ **Testes** - Validar payload completo
4. ⏳ **Integração** - Testar com Gestão
5. ⏳ **Deploy** - Colocar em produção

---

## 📝 Notas Importantes

1. **Compatibilidade:** Formato antigo ainda funciona, mas cria apenas 4 rankings
2. **Limite:** Máximo 1000 players por requisição (conforme documentação Gestão)
3. **Performance:** Query única é mais eficiente que múltiplas queries
4. **Manutenção:** Reutilizar código existente facilita manutenção futura

---

**Status:** ✅ Pronto para Implementação  
**Prioridade:** Média  
**Tempo Estimado:** 2-4 horas
