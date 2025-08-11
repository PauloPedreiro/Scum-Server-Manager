# Sistema de Atualização de Cards - Dashboard

## Visão Geral

O dashboard agora possui um sistema híbrido onde você pode controlar quais cards são atualizados automaticamente e quais permanecem estáticos. A página principal é estática e apenas os cards específicos que você definir serão atualizados automaticamente.

## Como Funciona

### 1. Configuração de Cards

No arquivo `src/pages/Dashboard.tsx`, você encontra a configuração `cardConfig`:

```javascript
const cardConfig = {
  onlinePlayers: true,    // Card de jogadores online - atualiza automaticamente
  stats: false,           // Card de estatísticas - estático
  events: true,           // Card de eventos - atualiza automaticamente
  weapons: false,         // Card de armas - estático
  players: false,         // Card de jogadores - estático
  serverStatus: false     // Card de status do servidor - estático
};
```

### 2. Cards Disponíveis

#### Cards com Atualização Automática:
- **OnlinePlayersCardAutoRefresh**: Atualiza jogadores online
- **StatsCardAutoRefresh**: Atualiza estatísticas do servidor
- **EventsCardAutoRefresh**: Atualiza eventos recentes

#### Cards Estáticos:
- **ServerStatusCard**: Status do servidor
- **WeaponsCard**: Armas mais usadas
- **PlayersCard**: Lista de jogadores
- **StatsCard**: Estatísticas (versão estática)
- **EventsCard**: Eventos (versão estática)

### 3. Como Alterar a Configuração

Para alterar quais cards atualizam automaticamente, modifique o objeto `cardConfig`:

```javascript
// Exemplo: Fazer todos os cards estáticos
const cardConfig = {
  onlinePlayers: false,
  stats: false,
  events: false,
  weapons: false,
  players: false,
  serverStatus: false
};

// Exemplo: Fazer todos os cards atualizarem automaticamente
const cardConfig = {
  onlinePlayers: true,
  stats: true,
  events: true,
  weapons: true,
  players: true,
  serverStatus: true
};
```

### 4. Intervalos de Atualização

Cada card com atualização automática possui seu próprio seletor de intervalo:

- **30 segundos**
- **45 segundos** (apenas para eventos)
- **1 minuto**
- **2 minutos**

### 5. Indicadores Visuais

O dashboard mostra um painel de configuração no topo que indica:
- 🟢 **Verde**: Card com atualização automática
- ⚫ **Cinza**: Card estático

## Vantagens do Sistema

1. **Performance**: A página não recarrega completamente
2. **Flexibilidade**: Você escolhe quais dados são críticos para atualização
3. **Controle**: Cada card pode ter seu próprio intervalo de atualização
4. **Estabilidade**: Cards menos críticos permanecem estáticos

## Como Adicionar Novos Cards

### 1. Criar o Card com Atualização Automática

```javascript
export const MeuCardAutoRefresh: React.FC = () => {
  const [intervalo, setIntervalo] = useState(30000);
  const [dados, setDados] = useState(null);
  
  const fetchDados = async () => {
    // Lógica para buscar dados
  };
  
  useEffect(() => {
    fetchDados();
    const timer = setInterval(fetchDados, intervalo);
    return () => clearInterval(timer);
  }, [intervalo]);
  
  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs text-gray-400">Atualizar a cada:</span>
        <select
          value={intervalo}
          onChange={e => setIntervalo(Number(e.target.value))}
        >
          <option value={30000}>30 segundos</option>
          <option value={60000}>1 minuto</option>
        </select>
      </div>
      <MeuCard dados={dados} />
    </div>
  );
};
```

### 2. Adicionar à Configuração

```javascript
const cardConfig = {
  // ... outros cards
  meuCard: true  // ou false para versão estática
};
```

### 3. Usar no Dashboard

```javascript
{cardConfig.meuCard ? (
  <MeuCardAutoRefresh />
) : (
  <MeuCard dados={dadosEstaticos} />
)}
```

## Exemplos de Uso

### Cenário 1: Monitoramento Crítico
```javascript
const cardConfig = {
  onlinePlayers: true,    // Atualiza a cada 30s
  stats: true,           // Atualiza a cada 1min
  events: true,          // Atualiza a cada 45s
  weapons: false,        // Estático
  players: false,        // Estático
  serverStatus: false    // Estático
};
```

### Cenário 2: Dashboard Estático
```javascript
const cardConfig = {
  onlinePlayers: false,
  stats: false,
  events: false,
  weapons: false,
  players: false,
  serverStatus: false
};
```

### Cenário 3: Apenas Dados Críticos
```javascript
const cardConfig = {
  onlinePlayers: true,    // Único card que atualiza
  stats: false,
  events: false,
  weapons: false,
  players: false,
  serverStatus: false
};
```

## Notas Importantes

1. **Tokens**: Todos os cards com atualização automática usam o token do localStorage
2. **Tratamento de Erros**: Cada card possui seu próprio tratamento de erro
3. **Loading States**: Cards mostram estados de carregamento individuais
4. **Cleanup**: Os intervalos são limpos automaticamente quando os componentes são desmontados

## Troubleshooting

### Card não atualiza
- Verifique se o token está presente no localStorage
- Confirme se a API está respondendo
- Verifique o console para erros

### Performance lenta
- Reduza os intervalos de atualização
- Desative cards menos críticos
- Use cards estáticos para dados que não mudam frequentemente

### Erro de rede
- Os cards mostram mensagens de erro individuais
- Tente novamente ou verifique a conectividade 