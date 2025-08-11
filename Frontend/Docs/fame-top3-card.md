# Card Top 3 Fama - Documentação

## Visão Geral
O card de Top 3 Fama foi implementado para mostrar os três jogadores com maior pontuação de fama no dashboard principal. O card é estático e será atualizado junto com o contador do bunker no header.

## Funcionalidades

### 1. Exibição dos Top 3 Jogadores
- **🏆 1º Lugar**: Medalha de ouro com fundo dourado
- **🥈 2º Lugar**: Medalha de prata com fundo prateado  
- **🥉 3º Lugar**: Medalha de bronze com fundo bronze
- **Pontuação**: Mostra a pontuação exata de cada jogador
- **Porcentagem**: Barra de progresso relativa ao líder
- **SteamID**: Identificação única do jogador

### 2. Sistema de Atualização
- **Estático**: Card não atualiza automaticamente
- **Sincronizado**: Atualiza junto com o contador do bunker (2 horas)
- **Manual**: Botão para atualização manual
- **Persistente**: Dados salvos no localStorage

### 3. Design Visual
- **Cores diferenciadas**: Cada posição tem sua cor específica
- **Animações**: Entrada suave com Framer Motion
- **Barras de progresso**: Coloridas por nível de fama
- **Responsivo**: Adapta-se a diferentes tamanhos de tela

## Estrutura de Dados

### Interface FamePlayer
```typescript
interface FamePlayer {
  playerName: string;
  steamId: string;
  totalFame: number;
  timestamp: string;
}
```

## Integração com Sistema de Contador

### Hook useBunkersCountdown
O card utiliza o mesmo sistema de contador do bunker:

```typescript
const { countdown, resetCountdown } = useBunkersCountdown();
```

### Atualização Sincronizada
- **Trigger**: Quando countdown <= 1
- **Frequência**: A cada 2 horas (7200 segundos)
- **Reset**: Contador é resetado após atualização
- **Persistência**: Dados salvos no localStorage

## Endpoint Utilizado

### GET /api/famepoints
- **URL**: `http://localhost:3000/api/famepoints`
- **Método**: GET
- **Resposta**: JSON com dados de fama de todos os jogadores

### Exemplo de Resposta
```json
{
  "success": true,
  "message": "Dados de fama recuperados com sucesso.",
  "data": [
    {
      "playerName": "Reav",
      "steamId": "76561197963358180",
      "totalFame": 1018.12,
      "timestamp": "2025-07-15T00:52:00Z"
    },
    {
      "playerName": "BlueArcher_BR",
      "steamId": "76561198398160339", 
      "totalFame": 922.42,
      "timestamp": "2025-07-15T00:52:00Z"
    }
  ]
}
```

## Componente

### FameTop3Card
- **Localização**: `src/components/FameTop3Card.tsx`
- **Props**: `className` (opcional)
- **Estados**: loading, error, top3Players, lastUpdate
- **Auto-refresh**: 2 horas (sincronizado com bunker)
- **Contador**: Usa hook global useBunkersCountdown
- **Tema**: Militar/técnico

### Funcionalidades do Componente
1. **Loading State**: Skeleton loader durante carregamento
2. **Error State**: Exibe erro com botão de retry
3. **Empty State**: Quando não há dados
4. **Success State**: Exibe top 3 formatados
5. **Persistência**: Salva dados no localStorage

## Integração no Dashboard

### Localização
- Adicionado na seção principal do dashboard
- Posicionado abaixo dos cards de chat e bunker
- Layout responsivo (grid 1 coluna em mobile, 3 em desktop)

### Código de Integração
```tsx
{activeSection === 'dashboard' && (
  <>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-6xl mx-auto mb-8 items-start">
      <ChatMessagesCard messages={chatMessages} ativo={chatInGameAtivo} onToggle={() => setChatInGameAtivo(v => !v)} />
      <BunkersCard />
    </div>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto mb-8 items-start">
      <FameTop3Card />
    </div>
  </>
)}
```

## Estilização

### Tema Militar
- **Estilo**: Interface militar/técnica
- **Fonte**: Monospace para dados técnicos
- **Cores**: Dourado (1º), Prateado (2º), Bronze (3º)
- **Layout**: Organizado e hierárquico

### Cores Utilizadas
- **1º Lugar**: `text-yellow-400`, `bg-yellow-400/10`, `border-yellow-400/30`
- **2º Lugar**: `text-gray-400`, `bg-gray-400/10`, `border-gray-400/30`
- **3º Lugar**: `text-orange-400`, `bg-orange-400/10`, `border-orange-400/30`
- **Acento**: `text-scum-accent`, `border-scum-accent/30`
- **Texto**: `text-scum-light`, `text-scum-muted`
- **Background**: `bg-scum-dark/40`, `bg-scum-dark/60`

### Animações
- **Entrada**: Framer Motion com fade-in e slide-up
- **Loading**: Spinner animado
- **Hover**: Efeitos sutis nos botões
- **Progresso**: Barras animadas

## Serviço

### FameService
- **Localização**: `src/services/fameService.ts`
- **Método**: `getFamePoints()`
- **Tratamento de Erros**: Try-catch com mensagens amigáveis

## Formatação

### Pontuação
- **Entrada**: `1018.12`
- **Saída**: `1,018.12 pts` (formatado com vírgulas)

### Porcentagem
- **Cálculo**: `(pontuação / maior_pontuação) * 100`
- **Saída**: `100%` (arredondado para inteiro)

### Timestamp
- **Entrada**: `2025-07-15T00:52:00Z`
- **Saída**: `15/07/2025, 00:52` (formato brasileiro)

## Responsividade

### Mobile (< 768px)
- Grid de 1 coluna
- Cards empilhados verticalmente
- Texto menor para economizar espaço

### Desktop (≥ 768px)
- Grid de 3 colunas
- Cards lado a lado
- Mais espaço para detalhes

## Estados de Erro

### Erro de Conexão
- Mensagem: "Erro ao conectar com o servidor"
- Botão de retry disponível
- Log no console para debug

### Erro de Dados
- Mensagem: "Erro ao carregar dados de fama"
- Fallback para estado vazio

### Sem Dados
- Mensagem: "Nenhum jogador encontrado"
- Ícone de troféu
- Interface limpa

## Performance

### Otimizações
- **Debounce**: Evita múltiplas chamadas simultâneas
- **localStorage**: Persiste dados entre sessões
- **Memoização**: Evita re-renders desnecessários
- **Lazy Loading**: Carrega dados apenas quando necessário

### Cache
- **Dados**: Salvos no localStorage como `fameTop3Data`
- **Timestamp**: Salvo como `fameTop3LastUpdate`
- **Recuperação**: Carrega dados salvos na inicialização

## Sincronização com Bunker

### Sistema Compartilhado
- **Hook**: Ambos usam `useBunkersCountdown`
- **Contador**: Mesmo contador de 2 horas
- **Reset**: Ambos resetam quando atualizam
- **Persistência**: Ambos salvam no localStorage

### Vantagens
- **Consistência**: Todos os cards estáticos atualizam juntos
- **Performance**: Evita múltiplas chamadas simultâneas
- **UX**: Interface previsível para o usuário
- **Manutenção**: Código centralizado

## Configuração

### Alterando Frequência
Para alterar a frequência de atualização, modifique o hook `useBunkersCountdown`:

```typescript
// Em src/hooks/useBunkersCountdown.tsx
const INTERVAL = 7200; // 2 horas em segundos
// Altere para: const INTERVAL = 3600; // 1 hora
```

### Alterando Layout
Para alterar o layout no dashboard:

```tsx
// Em src/pages/Dashboard.tsx
<div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto mb-8 items-start">
  <FameTop3Card />
</div>
```

## Troubleshooting

### Problemas Comuns

1. **Card não atualiza**
   - Verifique se o hook `useBunkersCountdown` está funcionando
   - Confirme se a API `/api/famepoints` está respondendo
   - Verifique o console para erros

2. **Dados não persistem**
   - Verifique se o localStorage está habilitado
   - Confirme se os dados estão sendo salvos corretamente
   - Teste a recuperação dos dados salvos

3. **Erro de conexão**
   - Verifique se o backend está rodando
   - Confirme se a URL da API está correta
   - Teste a conectividade de rede

### Debug
- **Console**: Logs detalhados de erros
- **Network**: Verificar chamadas da API
- **localStorage**: Verificar dados salvos
- **React DevTools**: Inspecionar estados do componente 