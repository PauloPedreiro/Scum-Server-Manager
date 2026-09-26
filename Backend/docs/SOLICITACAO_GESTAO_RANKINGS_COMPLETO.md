# 📋 Solicitação: Receber Rankings Completos no POST /api/v1/servers/sync

> **Data:** 2025-01-XX  
> **Para:** Desenvolvedor do Gestão  
> **Assunto:** Alteração no formato de recebimento de rankings

---

## 🎯 Objetivo

Solicitar que o endpoint `POST /api/v1/servers/sync` aceite os dados de rankings no **mesmo formato** que o endpoint `GET /api/rankings/list` do SSM Backend retorna.

---

## 📊 Situação Atual

### **Formato Atual Enviado (Categorias Separadas):**

```json
{
  "rankings": {
    "kills": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 150,
        "kdr": 2.5,
        "deaths": 60
      }
    ],
    "survival": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 125000,
        "fame": 50000
      }
    ],
    "lockpicking": [...],
    "fishing": [...]
  }
}
```

**Problemas:**
- ❌ Dados duplicados (mesmo jogador aparece em múltiplas categorias)
- ❌ Informações limitadas (apenas campos relevantes para cada categoria)
- ❌ Não inclui todos os dados disponíveis (faltam headshots, knockouts, etc.)
- ❌ Estrutura complexa para processar no Gestão

---

## 💡 Proposta: Formato Completo (Igual ao `/api/rankings/list`)

### **Formato Proposto:**

```json
{
  "rankings": {
    "players": [
      {
        "steam_id": "76561197963358180",
        "player_name": "Reav",
        "rank": 1,
        "kills": 140,
        "deaths": 0,
        "kdr": 140.0,
        "headshots": 1071,
        "players_knocked_out": 5,
        "animals_killed": 38,
        "minutes_survived": 170053.140625,
        "total_fame": 25369.654297,
        "vehicles_destroyed": 0,
        "suicides": 0,
        "overdoses": 0,
        "highest_weight_carried": 212.64688110351562,
        "highest_defecation": 222,
        "last_updated": "2025-12-12T02:41:28.229053",
        "longest_shot": {
          "distance": 30.69,
          "weapon": "Default__Weapon_RPG7_C",
          "timestamp": "2025-12-06T23:22:27"
        },
        "lockpicking": {
          "basic": {
            "success": 11,
            "fails": 3,
            "total": 14,
            "rate": 78.57
          },
          "medium": {
            "success": 2,
            "fails": 1,
            "total": 3,
            "rate": 66.67
          },
          "advanced": {
            "success": 3,
            "fails": 3,
            "total": 6,
            "rate": 50.0
          },
          "veryeasy": {
            "success": 0,
            "fails": 0,
            "total": 0,
            "rate": 0.0
          },
          "diallock": {
            "success": 0,
            "fails": 0,
            "total": 0,
            "rate": 0.0
          },
          "other": {
            "success": 0,
            "fails": 0,
            "total": 0,
            "rate": 0.0
          }
        }
      }
    ],
    "pagination": {
      "total": 473,
      "limit": 100,
      "offset": 0
    }
  }
}
```

---

## ✅ Vantagens da Proposta

### **1. Dados Completos**
- ✅ **TODOS** os campos da tabela `rankings` são enviados
- ✅ Não há perda de informação
- ✅ Gestão pode criar qualquer ranking que quiser

### **2. Sem Duplicação**
- ✅ Cada jogador aparece **apenas uma vez**
- ✅ Reduz tamanho do payload
- ✅ Mais eficiente para processar

### **3. Estrutura Consistente**
- ✅ Mesmo formato que o endpoint `/api/rankings/list`
- ✅ Reutiliza código existente no SSM Backend
- ✅ Mais fácil de manter

### **4. Flexibilidade no Gestão**
- ✅ Gestão pode ordenar por qualquer campo
- ✅ Pode criar rankings dinâmicos
- ✅ Não precisa esperar novas categorias serem adicionadas

### **5. Facilita Expansão Futura**
- ✅ Novos campos na tabela `rankings` são automaticamente incluídos
- ✅ Não precisa alterar contrato da API
- ✅ Backward compatible (campos novos podem ser opcionais)

---

## 📝 Estrutura Completa do Payload

### **Payload Completo do POST /api/v1/servers/sync:**

```json
{
  "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
  "api_key": "ssm_2d9ba653192f1a872fbef6583485c50fd6265384ace80ecf222727cc41c4ac4c",
  "server_info": {
    "name": "Meu Servidor SCUM",
    "version": "3.0.0",
    "max_players": 64,
    "current_players": 32
  },
  "players": [
    {
      "steam_id": "76561198012345678",
      "name": "PlayerName",
      "fame": 50000,
      "is_online": true,
      "last_seen": "2025-01-15T10:30:00Z"
    }
  ],
  "rankings": {
    "players": [
      {
        "steam_id": "76561197963358180",
        "player_name": "Reav",
        "rank": 1,
        "kills": 140,
        "deaths": 0,
        "kdr": 140.0,
        "headshots": 1071,
        "players_knocked_out": 5,
        "animals_killed": 38,
        "minutes_survived": 170053.140625,
        "total_fame": 25369.654297,
        "vehicles_destroyed": 0,
        "suicides": 0,
        "overdoses": 0,
        "highest_weight_carried": 212.64688110351562,
        "highest_defecation": 222,
        "last_updated": "2025-12-12T02:41:28.229053",
        "longest_shot": {
          "distance": 30.69,
          "weapon": "Default__Weapon_RPG7_C",
          "timestamp": "2025-12-06T23:22:27"
        },
        "lockpicking": {
          "basic": {
            "success": 11,
            "fails": 3,
            "total": 14,
            "rate": 78.57
          },
          "medium": {
            "success": 2,
            "fails": 1,
            "total": 3,
            "rate": 66.67
          },
          "advanced": {
            "success": 3,
            "fails": 3,
            "total": 6,
            "rate": 50.0
          },
          "veryeasy": {
            "success": 0,
            "fails": 0,
            "total": 0,
            "rate": 0.0
          },
          "diallock": {
            "success": 0,
            "fails": 0,
            "total": 0,
            "rate": 0.0
          },
          "other": {
            "success": 0,
            "fails": 0,
            "total": 0,
            "rate": 0.0
          }
        }
      }
    ],
    "pagination": {
      "total": 473,
      "limit": 100,
      "offset": 0
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## 🔄 Mudanças Necessárias no Gestão

### **1. Estrutura da Tabela `server_ranking`**

**Opção A: Manter estrutura atual e adaptar**
- Manter tabela `server_ranking` com categorias
- Criar rankings dinamicamente a partir dos dados completos
- Mais flexível, permite criar rankings sob demanda

**Opção B: Nova estrutura (Recomendado)**
- Criar tabela `server_player_rankings` que armazena todos os dados de cada jogador
- Estrutura similar à tabela `rankings` do SSM Backend
- Rankings são calculados dinamicamente via queries

### **2. Processamento no Endpoint**

```python
# Pseudocódigo
def sync_rankings(rankings_data):
    players = rankings_data.get('players', [])
    
    for player_data in players:
        # Salvar/atualizar dados completos do jogador
        save_player_rankings(player_data)
    
    # Rankings podem ser calculados dinamicamente:
    # - Top Kills: ORDER BY kills DESC
    # - Top Headshots: ORDER BY headshots DESC
    # - Top Survival: ORDER BY minutes_survived DESC
    # etc.
```

---

## 📋 Checklist de Implementação

### **SSM Backend:**
- [x] Endpoint `/api/rankings/list` já retorna formato completo
- [ ] Modificar `_get_rankings_data()` para retornar formato completo
- [ ] Manter compatibilidade com formato antigo (se necessário)

### **Gestão:**
- [ ] Aceitar novo formato no `POST /api/v1/servers/sync`
- [ ] Decidir estrutura de armazenamento (Opção A ou B)
- [ ] Implementar lógica de processamento
- [ ] Criar queries para rankings dinâmicos
- [ ] Atualizar documentação da API

---

## 🎯 Benefícios para o Gestão

1. **Rankings Dinâmicos:** Pode criar qualquer ranking sem precisar esperar nova categoria
2. **Dados Completos:** Acesso a todos os campos para análises futuras
3. **Menos Manutenção:** Não precisa atualizar código quando novos campos são adicionados
4. **Performance:** Processa dados uma vez, cria rankings sob demanda
5. **Flexibilidade:** Pode criar rankings customizados (ex: "Top Headshots com KDR > 2.0")

---

## ❓ Questões para Discussão

1. **Limite de Jogadores:** Enviar todos os jogadores ou apenas top 100/500?
2. **Frequência:** Manter mesma frequência de sincronização?
3. **Compatibilidade:** Manter suporte ao formato antigo durante transição?
4. **Armazenamento:** Qual estrutura de tabela prefere no Gestão?

---

## 📞 Próximos Passos

1. ✅ **Aprovação da Proposta** - Confirmar se formato é aceitável
2. ⏳ **Definição de Estrutura** - Decidir como armazenar no Gestão
3. ⏳ **Implementação SSM Backend** - Modificar `_get_rankings_data()`
4. ⏳ **Implementação Gestão** - Atualizar endpoint de sync
5. ⏳ **Testes** - Validar sincronização completa
6. ⏳ **Deploy** - Colocar em produção

---

## 📝 Notas Finais

Esta mudança simplifica significativamente o processo de sincronização e oferece muito mais flexibilidade para o Gestão criar e exibir rankings. O formato proposto é o mesmo que já está sendo usado com sucesso no endpoint `/api/rankings/list`, garantindo consistência e reutilização de código.

**Aguardando feedback e aprovação para prosseguir com a implementação.**
