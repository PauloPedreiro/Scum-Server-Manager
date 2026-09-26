# 📊 Análise: Tabela `abandoned_bunker_mesh_instance_bound_to_activation`

## 📋 Visão Geral

A tabela `abandoned_bunker_mesh_instance_bound_to_activation` no banco `SCUM.db` registra **instâncias de objetos/meshes que foram ativados (examinados) dentro de bunkers abandonados** no jogo SCUM.

---

## 🗄️ Estrutura da Tabela

### **Schema**

```sql
CREATE TABLE abandoned_bunker_mesh_instance_bound_to_activation (
    abandoned_bunker_id INTEGER NOT NULL,
    mesh_instance_name TEXT NOT NULL,
    examine_time REAL NOT NULL,
    PRIMARY KEY (abandoned_bunker_id, mesh_instance_name),
    FOREIGN KEY (abandoned_bunker_id) REFERENCES abandoned_bunker(id)
);
```

### **Colunas**

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `abandoned_bunker_id` | INTEGER | ID do bunker abandonado (FK para `abandoned_bunker.id`) |
| `mesh_instance_name` | TEXT | Nome único da instância do mesh/objeto ativado |
| `examine_time` | REAL | Timestamp do momento em que o objeto foi examinado/ativado |

---

## 🎯 Função da Tabela

### **Propósito Principal**

Esta tabela funciona como um **registro de ativação/examinação de objetos** dentro dos bunkers abandonados. Ela rastreia:

1. **Quais objetos foram ativados**: Cada `mesh_instance_name` representa um objeto específico dentro de um bunker (ex.: portas, armários, painéis, etc.)

2. **Quando foram ativados**: O campo `examine_time` registra o momento exato da ativação/examinação

3. **Em qual bunker**: A relação com `abandoned_bunker` identifica em qual bunker o objeto está localizado

### **Contexto no Jogo**

No SCUM, os bunkers abandonados contêm vários objetos interativos que podem ser:
- **Portas** que precisam ser abertas
- **Armários** que podem ser examinados
- **Painéis elétricos** que podem ser ativados
- **Outros objetos interativos** que requerem ação do jogador

Quando um jogador interage com esses objetos (examinar, abrir, ativar), o jogo registra essa ação nesta tabela.

---

## 📊 Análise dos Dados

### **Estatísticas Encontradas**

- **Total de registros**: 143 ativações
- **Bunkers únicos**: 11 bunkers diferentes
- **Instâncias de mesh únicas**: 143 (cada registro é único)
- **Distribuição**: Cada bunker tem aproximadamente 13 ativações registradas

### **Padrões Observados**

1. **Chave Primária Composta**: A combinação `(abandoned_bunker_id, mesh_instance_name)` garante que cada instância de objeto em um bunker seja única

2. **Relacionamento com `abandoned_bunker`**: 
   - Foreign Key para `abandoned_bunker.id`
   - Permite rastrear qual bunker contém cada objeto ativado

3. **Nomes de Mesh**: 
   - Seguem padrão: `TV_Base_X_Secret:$BP_ArmorySmall_...`
   - Parecem representar diferentes tipos de armários/objetos dentro dos bunkers
   - Cada nome é único e identifica uma instância específica de objeto

4. **Timestamps (`examine_time`)**:
   - Valores em formato REAL (provavelmente tempo do jogo em segundos)
   - Intervalo observado: ~9.1 milhões a ~11.4 milhões
   - Cada ativação tem um timestamp único

---

## 🔗 Relacionamentos

### **Tabela Pai: `abandoned_bunker`**

A tabela `abandoned_bunker` contém informações sobre os bunkers:
- `id`: Identificador único do bunker
- `location_x`, `location_y`: Coordenadas do bunker no mapa
- `user_profile_id`: Perfil do usuário (se aplicável)
- `map_id`: ID do mapa
- `is_day`: Se é dia ou noite
- Campos de tempo relacionados à ativação do bunker

### **Outras Tabelas Relacionadas**

O banco também contém outras tabelas relacionadas a bunkers:
- `abandoned_bunker_alarmed_room`: Salas com alarme
- `abandoned_bunker_bcu_terminal`: Terminais BCU
- `abandoned_bunker_powered_room`: Salas energizadas
- `abandoned_bunker_switchboard_fuse`: Fusíveis de painel elétrico

---

## 💡 Casos de Uso

### **1. Rastreamento de Ativações**

A tabela permite saber:
- Quais objetos foram ativados em cada bunker
- Quantas vezes cada objeto foi ativado
- Histórico de ativações ao longo do tempo

### **2. Análise de Uso de Bunkers**

Combinando com `abandoned_bunker`, é possível:
- Identificar bunkers mais visitados
- Mapear quais objetos são mais frequentemente ativados
- Analisar padrões de exploração

### **3. Sistema de Respawn/Reset**

O campo `examine_time` pode ser usado para:
- Controlar quando objetos devem respawnar
- Implementar cooldowns entre ativações
- Gerenciar ciclos de ativação dos bunkers

---

## 🔍 Exemplos de Consultas Úteis

### **Listar todas as ativações de um bunker específico**

```sql
SELECT 
    abmita.mesh_instance_name,
    abmita.examine_time,
    ab.location_x,
    ab.location_y
FROM abandoned_bunker_mesh_instance_bound_to_activation abmita
JOIN abandoned_bunker ab ON abmita.abandoned_bunker_id = ab.id
WHERE abmita.abandoned_bunker_id = 25
ORDER BY abmita.examine_time DESC;
```

### **Contar ativações por bunker**

```sql
SELECT 
    ab.id as bunker_id,
    ab.location_x,
    ab.location_y,
    COUNT(abmita.mesh_instance_name) as total_activations
FROM abandoned_bunker ab
LEFT JOIN abandoned_bunker_mesh_instance_bound_to_activation abmita 
    ON ab.id = abmita.abandoned_bunker_id
GROUP BY ab.id
ORDER BY total_activations DESC;
```

### **Encontrar objetos mais ativados**

```sql
SELECT 
    mesh_instance_name,
    COUNT(*) as activation_count,
    MIN(examine_time) as first_activation,
    MAX(examine_time) as last_activation
FROM abandoned_bunker_mesh_instance_bound_to_activation
GROUP BY mesh_instance_name
ORDER BY activation_count DESC;
```

---

## ⚠️ Observações Importantes

1. **Chave Primária Composta**: A combinação `(abandoned_bunker_id, mesh_instance_name)` garante unicidade, mas permite múltiplas ativações do mesmo objeto se o nome da instância mudar

2. **Timestamps**: O campo `examine_time` usa valores REAL muito grandes (milhões), provavelmente representando tempo do jogo em segundos desde algum ponto de referência

3. **Relacionamento 1:N**: Um bunker pode ter múltiplas ativações de diferentes objetos, mas cada combinação bunker+objeto é única

4. **Integridade Referencial**: A foreign key garante que só existam registros para bunkers que realmente existem na tabela `abandoned_bunker`

---

## 📝 Conclusão

A tabela `abandoned_bunker_mesh_instance_bound_to_activation` serve como um **sistema de rastreamento de interações** com objetos dentro dos bunkers abandonados. Ela permite ao jogo:

- Registrar quando jogadores interagem com objetos específicos
- Manter histórico de ativações
- Gerenciar respawns e cooldowns de objetos
- Analisar padrões de exploração dos bunkers

É uma tabela de **auditoria/rastreamento** que complementa a tabela principal `abandoned_bunker` com informações detalhadas sobre as interações dos jogadores com os objetos dentro dos bunkers.

