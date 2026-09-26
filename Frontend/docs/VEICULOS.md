# 🚗 Sistema de Gerenciamento de Veículos - SSM 3.0 Frontend

Esta documentação descreve o sistema completo de gerenciamento de veículos implementado no frontend do SSM 3.0.

---

## 📋 Visão Geral

O sistema de veículos permite visualizar e gerenciar todos os veículos vinculados aos players do servidor SCUM. A funcionalidade está integrada na página de Players com uma interface intuitiva e organizada.

### Características Principais

- ✅ **Lista Visual**: Contagem de veículos ativos na tabela principal de players
- ✅ **Detalhes Completos**: Aba dedicada com informações detalhadas de cada veículo
- ✅ **Miniaturas**: Imagens dos veículos para identificação visual rápida
- ✅ **Filtros por Status**: Filtrar veículos por status (Ativo, Inativo, Desaparecido, Destruído)
- ✅ **Ordenação**: Ordenar players por quantidade de veículos ativos
- ✅ **Agrupamento**: Veículos agrupados automaticamente por status

---

## 🎯 Funcionalidades

### 1. Coluna de Veículos na Tabela Principal

Na tabela de players, há uma coluna "Veículos" que mostra:
- **Número em verde**: Quantidade de veículos ativos > 0
- **Número em vermelho**: Quantidade de veículos ativos = 0

**Exemplo:**
```
Player Name    | Veículos
---------------|----------
Pedreiro       | 5        (verde)
Eu Mesmo       | 0        (vermelho)
ARKANJO        | 3        (verde)
```

### 2. Ordenação por Veículos

Ao clicar no cabeçalho da coluna "Veículos":
- Ativa ordenação descendente (maior → menor)
- Seta verde (▼) indica que a ordenação está ativa
- Ordenação secundária: mesmo número de veículos → online primeiro → alfabético
- Clicar novamente desativa e volta à ordem padrão

### 3. Aba de Veículos

Ao clicar no nome de um player, abre-se um painel colapsável com duas abas:

#### Aba "Permissões"
- Toggles para gerenciar permissões do player
- Timer, Admin, Banned, Config, Silenced, Whitelist

#### Aba "Veículos"
- **Resumo**: Total de veículos e contagem por status com indicadores coloridos
- **Filtros**: Botões para filtrar por status (Todos, Ativo, Inativo, Desaparecido, Destruído)
- **Lista Detalhada**:
  - **Layout em Grid Responsivo**: Veículos agrupados 2 por card
    - Mobile: 1 coluna (cards empilhados verticalmente)
    - Desktop: 2 colunas (2 cards lado a lado)
    - Cada card contém 2 veículos lado a lado no desktop, empilhados no mobile
    - Cards mais largos para melhor visualização
    - Cores por status aplicadas ao card externo (verde/amarelo/laranja/vermelho)
    - Se quantidade ímpar, último card com 1 veículo ocupa toda a largura
  - Informações de cada veículo:
    - Miniatura do veículo (imagem PNG)
    - Nome do veículo (`vehicle_class_display`)
    - ID Veículo (`vehicle_entity_id`)
    - ID Container (`entity_id`)
    - Localização (coordenadas X, Y, Z) - sem quebra de linha
    - Última mudança de propriedade
    - Status e funcionalidade
  - Todas as informações empilhadas verticalmente sem quebra de linha

---

## 📊 Status dos Veículos

| Status | Valor | Cor | Descrição |
|--------|-------|-----|-----------|
| **Ativo** | `0` | 🟢 Verde | Veículo está ativo e em uso |
| **Inativo** | `1` | 🟡 Amarelo | Veículo inativo (VehicleInactiveTimerReached) |
| **Desaparecido** | `2` | 🟠 Laranja | Veículo desapareceu do servidor |
| **Destruído** | `3` | 🔴 Vermelho | Veículo foi destruído |

---

## 🖼️ Miniaturas de Veículos

### Localização das Imagens

As imagens dos veículos estão localizadas em:
```
src/assets/vehicle-log/
```

### Arquivos Disponíveis

- `Laika_ES.png`
- `Kinglet_Duster_ES.png`
- `WolfsWagen_ES.png`
- `Dirtbike_ES.png`
- `Rager_ES.png`
- `Tractor_ES.png`
- `Cruiser_ES.png`
- `CityBike_ES.png`
- `MountainBike_ES.png`
- `Barba_ES.png`
- `BigRaft_ES.png`
- `SmallRaft_ES.png`
- `SUP_ES.png`
- `RIS_ES.png`
- `Kinglet_Mariner_ES.png`
- E outros...

### Mapeamento

O arquivo `mapping.json` mapeia o `vehicle_class_display` para o nome do arquivo:

```json
{
  "Laika": "Laika_ES.png",
  "Kinglet_Duster": "Kinglet_Duster_ES.png",
  "WolfsWagen": "WolfsWagen_ES.png"
}
```

### Fallback

Se a imagem não for encontrada:
- Exibe um ícone padrão de carro (`Car` do Lucide React)
- Mantém a interface consistente

---

## 🔌 Endpoints Utilizados

### `GET /api/vehicles/player/{steam_id}/by-status`

Busca veículos de um player específico.

**Parâmetros:**
- `steam_id` (path): Steam ID do player
- `status` (query, opcional): Filtro por status (0, 1, 2, 3 ou múltiplos separados por vírgula)

**Exemplo:**
```typescript
// Todos os veículos agrupados por status
const response = await getPlayerVehiclesByStatus('76561198040636105');

// Apenas veículos ativos
const active = await getPlayerVehiclesByStatus('76561198040636105', '0');
```

### `GET /api/vehicles/players`

Busca todos os players com seus veículos.

**Parâmetros Query (opcionais):**
- `status`: Filtro por status
- `group_by_status`: Agrupar veículos por status
- `limit`: Número máximo de players (padrão: 1000)
- `offset`: Deslocamento para paginação

**Exemplo:**
```typescript
// Players com veículos ativos
const response = await getAllPlayersVehicles('0', false, 10000, 0);
```

---

## 💻 Implementação Técnica

### Carregamento de Dados

1. **Contagem Inicial**: Ao carregar a página, busca contagem de veículos ativos para todos os players
2. **Detalhes Sob Demanda**: Detalhes dos veículos são carregados apenas quando o usuário abre a aba "Veículos"

### Estado do Componente

```typescript
// Contagem de veículos ativos (para a tabela)
const [activeVehiclesCount, setActiveVehiclesCount] = useState<Map<string, number>>(new Map());

// Ordenação
const [sortByVehicles, setSortByVehicles] = useState<boolean>(false);

// Dados detalhados de veículos (por player)
const [vehiclesData, setVehiclesData] = useState<Map<string, PlayerVehiclesData>>(new Map());
```

### Carregamento de Imagens

```typescript
// Carregar todas as imagens de veículos
const vehicleImages = import.meta.glob('/src/assets/vehicle-log/*.png', {
  eager: true,
  as: 'url',
});

// Função helper para obter imagem
const getVehicleImagePath = (vehicleClassDisplay: string): string | null => {
  // Usa mapping.json para encontrar o arquivo correto
  // Retorna URL da imagem ou null
};
```

### Ordenação

```typescript
// Ordenação por veículos (descendente)
if (sortByVehicles) {
  playersList.sort((a, b) => {
    const vehiclesA = activeVehiclesCount.get(a.steam_id) ?? 0;
    const vehiclesB = activeVehiclesCount.get(b.steam_id) ?? 0;
    
    // Maior para menor
    if (vehiclesA !== vehiclesB) {
      return vehiclesB - vehiclesA;
    }
    
    // Ordenação secundária...
  });
}
```

---

## 🎨 Interface do Usuário

### Tabela Principal

```
┌─────────────────────────────────────────────────────┐
│ Player Name  │ Steam ID    │ Status  │ Veículos ▼  │
├─────────────────────────────────────────────────────┤
│ Pedreiro     │ 76561198... │ Online  │ 5 (verde)   │
│ Eu Mesmo     │ 76561198... │ Offline │ 0 (vermelho)│
└─────────────────────────────────────────────────────┘
```

### Aba de Veículos

```
┌────────────────────────────────────────────────────────────────────────┐
│ [Permissões] [Veículos] ← Abas                                        │
├────────────────────────────────────────────────────────────────────────┤
│ Total: 5 veículos                                                       │
│ 🟢 Ativo: 3  🟡 Inativo: 1  🔴 Destruído: 1                           │
│                                                                         │
│ [Todos] [Ativo] [Inativo] [Desaparecido] [Destruído]                   │
├────────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────┐  ┌──────────────────────────────┐   │
│ │ [🖼️] Laika    │ [🖼️] WolfsWagen │  │ [🖼️] Dirtbike              │   │
│ │ ID Veículo:  │ ID Veículo:     │  │ ID Veículo: 15987332        │   │
│ │ ID Container:│ ID Container:    │  │ ID Container: 15987337      │   │
│ │ Localização: │ Localização:    │  │ Localização: (-364729, -...) │   │
│ │ Status: Ativo│ Status: Ativo   │  │ Status: Ativo • Funcional   │   │
│ └──────────────────────────────┘  └──────────────────────────────┘   │
│          ↑ 2 veículos por card (desktop)                               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Tratamento de Erros

### Player Sem Veículos

Quando um player não possui veículos:
- **Antes**: Mostrava erro 404 no console e interface
- **Agora**: Trata silenciosamente como situação normal
- Interface mostra: "Nenhum veículo encontrado"
- Sem erros no console

### Implementação

```typescript
// Interceptor do Axios trata 404 para endpoint de veículos
api.interceptors.response.use(
  (r) => r,
  (e) => {
    // Transformar 404 em resposta válida para veículos
    if (e.response?.status === 404 && e.config?.url?.includes('/vehicles/player/')) {
      return Promise.resolve({
        status: 404,
        data: { success: false, error: 'Player not found or has no vehicles' }
      });
    }
    return Promise.reject(e);
  }
);
```

---

## 🔄 Fluxo de Uso

1. **Usuário entra na página Players**
   - Carrega lista de players
   - Carrega contagem de veículos ativos para cada player

2. **Usuário visualiza contagem**
   - Vê números verdes/vermelhos na coluna "Veículos"

3. **Usuário clica no cabeçalho "Veículos"**
   - Ordena players da maior para menor quantidade de veículos

4. **Usuário clica no nome de um player**
   - Abre painel colapsável
   - Por padrão mostra aba "Permissões"

5. **Usuário clica na aba "Veículos"**
   - Carrega dados detalhados dos veículos do player
   - Mostra resumo, filtros e lista com miniaturas

6. **Usuário filtra por status**
   - Seleciona filtro (ex: "Ativo")
   - Lista atualiza mostrando apenas veículos do status selecionado

---

## 📝 Notas Importantes

1. **Performance**: Dados de veículos são carregados sob demanda (lazy loading)
2. **Atualização**: Dados são atualizados manualmente via botão "Atualizar"
3. **Cache**: Imagens de veículos são carregadas uma vez no início (eager loading)
4. **Fallback**: Sempre há um fallback visual se a imagem não existir
5. **Ordenação**: Ordenação por veículos não interfere com outros filtros/busca

---

## 🚀 Melhorias Futuras

- [ ] Filtro combinado: players com mais de X veículos
- [ ] Visualização no mapa: mostrar localização dos veículos
- [ ] Ações: teleportar player para veículo, deletar veículo
- [ ] Estatísticas: gráficos de veículos por status ao longo do tempo
- [ ] Exportação: exportar lista de veículos para CSV/PDF

---

**Última atualização**: 2025-12-03  
**Versão**: 1.4.1

