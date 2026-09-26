# 📊 Análise: Tabela `base`

## 📋 Visão Geral

A tabela `base` no banco `SCUM.db` armazena informações sobre **bases de jogadores** no servidor SCUM. Cada registro representa uma base construída no mapa, incluindo sua localização, tamanho, propriedade e limites.

---

## 🗄️ Estrutura da Tabela

### **Schema**

```sql
CREATE TABLE base (
    id INTEGER PRIMARY KEY,
    location_x REAL,
    location_y REAL,
    size_x NUMERIC,
    size_y REAL,
    name TEXT,
    map_id INTEGER,
    user_profile_id INTEGER,
    owner_user_profile_id INTEGER,
    is_owned_by_player INTEGER,
    bounds_min_x REAL,
    bounds_min_y REAL,
    bounds_max_x REAL,
    bounds_max_y REAL,
    FOREIGN KEY (user_profile_id) REFERENCES user_profile(id),
    FOREIGN KEY (map_id) REFERENCES map(id)
);
```

### **Colunas**

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER | Identificador único da base (chave primária) |
| `location_x` | REAL | Coordenada X do centro da base no mapa |
| `location_y` | REAL | Coordenada Y do centro da base no mapa |
| `size_x` | NUMERIC | Largura da base (geralmente 0, não utilizado) |
| `size_y` | REAL | Altura da base (geralmente 0, não utilizado) |
| `name` | TEXT | Nome da base (ex: "Base #3", "Base #4") |
| `map_id` | INTEGER | ID do mapa onde a base está localizada (FK para `map.id`) |
| `user_profile_id` | INTEGER | ID do perfil do usuário (FK para `user_profile.id`, geralmente NULL) |
| `owner_user_profile_id` | INTEGER | ID do perfil do proprietário da base |
| `is_owned_by_player` | INTEGER | Flag indicando se a base é propriedade de um jogador (0 = não, 1 = sim) |
| `bounds_min_x` | REAL | Coordenada X mínima dos limites da base |
| `bounds_min_y` | REAL | Coordenada Y mínima dos limites da base |
| `bounds_max_x` | REAL | Coordenada X máxima dos limites da base |
| `bounds_max_y` | REAL | Coordenada Y máxima dos limites da base |

---

## 📊 Estatísticas

### **Dados Gerais**

- **Total de registros**: 150 bases
- **IDs**: De 3 a 177 (não sequenciais)
- **Mapa**: Todas as bases estão no mapa ID 1 (The_Island)
- **Bases com elementos**: 80 bases possuem elementos na tabela `base_element`

### **Distribuição de Propriedade**

| Owner ID | Quantidade | % do Total |
|---|---|---|
| `-1` (Sem dono) | 118 | 78.7% |
| `324` | 7 | 4.7% |
| `106` | 2 | 1.3% |
| `16` | 2 | 1.3% |
| Outros (25 únicos) | 21 | 14.0% |

### **Propriedade de Jogadores**

- **Bases de jogadores** (`is_owned_by_player = 1`): 9 bases (6.0%)
- **Bases não de jogadores** (`is_owned_by_player = 0`): 141 bases (94.0%)

### **Tamanho das Bases**

- **Tamanho padrão**: A maioria das bases tem bounds de -10000 a +10000 (92-94%)
- **Maior base**: Base #42 com área de ~972.726.125 unidades²
- **Bases grandes**: 10 bases têm área superior a 600.000 unidades²

---

## 🔗 Relacionamentos

### **Tabelas Filhas (Referenciam `base.id`)**

1. **`base_element`**
   - Contém os elementos/objetos dentro de cada base
   - **Total**: 26.139 elementos distribuídos em 80 bases
   - Campos: `element_id`, `base_id`, `location_x/y/z`, `rotation`, `scale`, `asset`, `health`, etc.
   - **Top 5 bases com mais elementos**:
     - Base ID 6: 2.208 elementos
     - Base ID 125: 1.747 elementos
     - Base ID 58: 1.534 elementos
     - Base ID 131: 1.305 elementos
     - Base ID 4: 1.261 elementos

2. **`base_element_shelter_map`**
   - Mapeia elementos para shelters/abrigos

3. **`base_raid_protection`**
   - Proteção contra raids (atualmente 0 registros)

4. **`placeable_basebuilding`**
   - Construções colocáveis relacionadas a bases (76 registros)

### **Tabelas Pais (Referenciadas por `base`)**

1. **`user_profile`**
   - Perfil do usuário (via `user_profile_id` e `owner_user_profile_id`)
   - **Observação**: `user_profile_id` está sempre NULL, mas `owner_user_profile_id` é usado

2. **`map`**
   - Mapa onde a base está localizada (via `map_id`)
   - Todas as bases estão no mapa ID 1

---

## 📐 Sistema de Coordenadas e Bounds

### **Coordenadas**

- **`location_x`, `location_y`**: Coordenadas do **centro** da base no mapa
- **Escala**: Coordenadas em escala de mapa (centenas de milhares)
- **Exemplo**: Base #3 está em (501103.75, -228677.22)

### **Bounds (Limites)**

Os campos `bounds_min_x/y` e `bounds_max_x/y` definem uma **caixa delimitadora (bounding box)** da base:

- **Largura**: `bounds_max_x - bounds_min_x`
- **Altura**: `bounds_max_y - bounds_min_y`
- **Área**: `(bounds_max_x - bounds_min_x) * (bounds_max_y - bounds_min_y)`

**Padrão**: A maioria das bases usa bounds de **-10000 a +10000** (área padrão de 400.000.000 unidades²)

**Bases grandes**: Algumas bases têm bounds customizados, resultando em áreas muito maiores.

---

## 🔍 Consultas Úteis

### **1. Listar Todas as Bases com Informações Completas**

```sql
SELECT 
    id,
    name,
    location_x,
    location_y,
    owner_user_profile_id,
    is_owned_by_player,
    (bounds_max_x - bounds_min_x) as width,
    (bounds_max_y - bounds_min_y) as height,
    ((bounds_max_x - bounds_min_x) * (bounds_max_y - bounds_min_y)) as area
FROM base
ORDER BY id;
```

### **2. Buscar Bases por Proprietário**

```sql
SELECT 
    id,
    name,
    location_x,
    location_y,
    is_owned_by_player
FROM base
WHERE owner_user_profile_id = 324  -- Substituir pelo ID do proprietário
ORDER BY id;
```

### **3. Listar Bases de Jogadores**

```sql
SELECT 
    id,
    name,
    owner_user_profile_id,
    location_x,
    location_y
FROM base
WHERE is_owned_by_player = 1
ORDER BY id;
```

### **4. Encontrar as Maiores Bases**

```sql
SELECT 
    id,
    name,
    (bounds_max_x - bounds_min_x) as width,
    (bounds_max_y - bounds_min_y) as height,
    ((bounds_max_x - bounds_min_x) * (bounds_max_y - bounds_min_y)) as area
FROM base
ORDER BY area DESC
LIMIT 10;
```

### **5. Contar Elementos por Base**

```sql
SELECT 
    b.id,
    b.name,
    COUNT(be.element_id) as element_count
FROM base b
LEFT JOIN base_element be ON b.id = be.base_id
GROUP BY b.id, b.name
ORDER BY element_count DESC
LIMIT 10;
```

### **6. Buscar Base por Coordenadas (proximidade)**

```sql
SELECT 
    id,
    name,
    location_x,
    location_y,
    SQRT(POWER(location_x - ?, 2) + POWER(location_y - ?, 2)) as distance
FROM base
ORDER BY distance
LIMIT 1;
-- Substituir ? pelas coordenadas X e Y desejadas
```

### **7. Verificar se Coordenadas Estão Dentro de uma Base**

```sql
SELECT 
    id,
    name,
    owner_user_profile_id
FROM base
WHERE ? BETWEEN bounds_min_x AND bounds_max_x
  AND ? BETWEEN bounds_min_y AND bounds_max_y;
-- Substituir ? pelas coordenadas X e Y a verificar
```

### **8. Estatísticas de Propriedade**

```sql
SELECT 
    owner_user_profile_id,
    COUNT(*) as base_count,
    SUM(CASE WHEN is_owned_by_player = 1 THEN 1 ELSE 0 END) as player_owned,
    SUM(CASE WHEN is_owned_by_player = 0 THEN 1 ELSE 0 END) as not_player_owned
FROM base
GROUP BY owner_user_profile_id
ORDER BY base_count DESC;
```

---

## 💡 Observações Importantes

### **1. Propriedade**

- **`owner_user_profile_id = -1`**: Indica que a base não tem proprietário definido (78.7% das bases)
- **`is_owned_by_player`**: Flag que indica se a base pertence a um jogador
- **`user_profile_id`**: Sempre NULL, não é utilizado para propriedade

### **2. Tamanho**

- **`size_x` e `size_y`**: Sempre 0, não são utilizados
- **Bounds**: O tamanho real da base é determinado pelos campos `bounds_min/max_x/y`

### **3. Nomes**

- Os nomes seguem o padrão "Base #N" onde N é o ID da base
- Não há nomes customizados pelos jogadores armazenados aqui

### **4. Elementos**

- Nem todas as bases têm elementos na tabela `base_element`
- Apenas 80 das 150 bases possuem elementos registrados
- Bases podem ter de 0 a mais de 2.000 elementos

---

## 🔧 Índices

A tabela possui um índice composto para otimizar consultas:

```sql
CREATE INDEX index_on_base_for_user_profile_id_and_map_id 
ON base(user_profile_id, map_id);
```

**Nota**: Este índice pode não ser muito útil já que `user_profile_id` está sempre NULL. Um índice em `owner_user_profile_id` seria mais eficiente para consultas por proprietário.

---

## 📝 Casos de Uso

### **1. Monitoramento de Bases**

- Listar todas as bases do servidor
- Identificar bases abandonadas (sem proprietário ou sem elementos)
- Rastrear bases de jogadores específicos

### **2. Análise de Tamanho**

- Identificar bases muito grandes (possíveis exploits)
- Calcular área total ocupada por bases
- Estatísticas de construção

### **3. Localização**

- Encontrar bases próximas a coordenadas específicas
- Verificar se um ponto está dentro de uma base
- Mapear distribuição de bases no servidor

### **4. Relacionamento com Elementos**

- Contar elementos por base
- Identificar bases com muitos elementos (possíveis lag)
- Rastrear construção/remoção de elementos

---

## 🔗 Relação com Outras Tabelas

```
base (1) ──< (N) base_element
base (1) ──< (N) base_element_shelter_map
base (1) ──< (N) base_raid_protection
base (N) >── (1) user_profile (via owner_user_profile_id)
base (N) >── (1) map
```

---

## 📊 Exemplos de Dados

### **Base Pequena (Padrão)**

```json
{
  "id": 3,
  "name": "Base #3",
  "location_x": 501103.75,
  "location_y": -228677.22,
  "owner_user_profile_id": 304,
  "is_owned_by_player": 0,
  "bounds_min_x": -10000.0,
  "bounds_min_y": -10000.0,
  "bounds_max_x": 10000.0,
  "bounds_max_y": 10000.0,
  "area": 400000000
}
```

### **Base Grande (Customizada)**

```json
{
  "id": 42,
  "name": "Base #42",
  "location_x": [coordenada],
  "location_y": [coordenada],
  "bounds_min_x": -18855.53,
  "bounds_min_y": -10000.0,
  "bounds_max_x": 10000.0,
  "bounds_max_y": 10714.09,
  "area": 972726125
}
```

---

## 🚀 Melhorias Sugeridas

1. **Índice em `owner_user_profile_id`**: Criar índice para otimizar consultas por proprietário
2. **Índice em coordenadas**: Para buscas por proximidade
3. **Índice em bounds**: Para verificações de ponto dentro de base
4. **View combinada**: Criar view que combine `base` com contagem de elementos
5. **Trigger de atualização**: Atualizar área automaticamente quando bounds mudarem

