# Card de Bunkers - Documentação

## Visão Geral
O card de bunkers foi implementado para mostrar o status atual dos bunkers do servidor SCUM no dashboard principal.

## Funcionalidades

### 1. Exibição de Estatísticas
- **TOTAL DE UNIDADES**: Mostra o número total de bunkers (ativos + bloqueados)
- **OPERACIONAIS**: Contador de bunkers atualmente ativos (verde)
- **BLOQUEADOS**: Contador de bunkers atualmente bloqueados (vermelho)
- **Contador de Atualização**: Tempo restante até próxima verificação automática

### 2. Lista de Bunkers Ativos
- **BUNKER [NOME]**: Nome do bunker em destaque
- **Tempo de ativação**: Formato 00h 06m 41s
- **COORD**: Coordenadas formatadas (quando disponíveis)
- **Estilo**: Fundo verde sutil com bordas

### 3. Lista de Bunkers Bloqueados
- **BUNKER [NOME]**: Nome do bunker em destaque
- **Tempo até ativação**: Formato 00h 06m 41s
- **COORD**: Coordenadas formatadas (quando disponíveis)
- **Estilo**: Fundo vermelho sutil com bordas

### 4. Auto-atualização
- Atualiza automaticamente a cada 2 horas
- Contador visual para próxima atualização
- Botão de atualização manual
- Indicador de última atualização

## Estrutura de Dados

### Interface BunkersData
```typescript
interface BunkersData {
  active: ActiveBunker[];
  locked: LockedBunker[];
  lastUpdate: string;
}
```

### Interface ActiveBunker
```typescript
interface ActiveBunker {
  name: string;
  activated: string;
  coordinates: BunkerCoordinates | null;
}
```

### Interface LockedBunker
```typescript
interface LockedBunker {
  name: string;
  nextActivation: string;
  coordinates: BunkerCoordinates | null;
}
```

## Endpoint Utilizado

### GET /api/bunkers/status
- **URL**: `http://localhost:3000/api/bunkers/status`
- **Método**: GET
- **Resposta**: JSON com dados dos bunkers

### Exemplo de Resposta
```json
{
  "success": true,
  "message": "Status dos bunkers recuperado com sucesso.",
  "data": {
    "active": [
      {
        "name": "A1",
        "activated": "00h 06m 41s",
        "coordinates": null
      }
    ],
    "locked": [
      {
        "name": "D1",
        "nextActivation": "23h 53m 18s",
        "coordinates": {
          "x": -537889.562,
          "y": 540004.312,
          "z": 81279.648
        }
      }
    ],
    "lastUpdate": "2025.07.14-18.03.50"
  }
}
```

## Componente

### BunkersCard
- **Localização**: `src/components/BunkersCard.tsx`
- **Props**: `className` (opcional)
- **Estados**: loading, error, data, countdown
- **Auto-refresh**: 2 horas
- **Contador**: Visual para próxima atualização
- **Tema**: Militar/técnico

### Funcionalidades do Componente
1. **Loading State**: Skeleton loader durante carregamento
2. **Error State**: Exibe erro com botão de retry
3. **Empty State**: Quando não há dados
4. **Success State**: Exibe dados formatados
5. **Deduplicação**: Remove entradas duplicadas automaticamente

## Integração no Dashboard

### Localização
- Adicionado na seção principal do dashboard
- Posicionado ao lado do card de chat
- Layout responsivo (grid 2 colunas em desktop)

### Código de Integração
```tsx
{activeSection === 'dashboard' && (
  <>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-6xl mx-auto mb-8 items-start">
      <ChatMessagesCard messages={chatMessages} ativo={chatInGameAtivo} onToggle={() => setChatInGameAtivo(v => !v)} />
      <BunkersCard />
    </div>
  </>
)}
```

## Estilização

### Tema Militar
- **Estilo**: Interface militar/técnica
- **Fonte**: Monospace para dados técnicos
- **Cores**: Verde (operacional), Vermelho (bloqueado), Acento (destaque)
- **Layout**: Organizado e hierárquico

### Cores Utilizadas
- **Verde (Ativos)**: `text-green-400`, `bg-green-400/5`, `border-green-400/20`
- **Vermelho (Bloqueados)**: `text-red-400`, `bg-red-400/5`, `border-red-400/20`
- **Acento**: `text-scum-accent`, `border-scum-accent/30`
- **Texto**: `text-scum-light`, `text-scum-muted`
- **Background**: `bg-scum-dark/40`, `bg-scum-dark/60`

### Animações
- **Entrada**: Framer Motion com fade-in e slide-up
- **Loading**: Spinner animado
- **Hover**: Efeitos sutis nos botões

## Serviço

### BunkerService
- **Localização**: `src/services/bunkerService.ts`
- **Método**: `getBunkersStatus()`
- **Tratamento de Erros**: Try-catch com mensagens amigáveis

## Formatação

### Tempo
- **Entrada**: "00h 06m 41s"
- **Saída**: "00h 06m 41s" (formatado para melhor legibilidade)

### Coordenadas
- **Entrada**: `{x: -348529.312, y: -469201.781, z: 4247.645}`
- **Saída**: "X: -348529, Y: -469202, Z: 4248" (arredondadas)

### Contador de Atualização
- **Formato**: HH:MM:SS (ex: 01:59:45)
- **Atualização**: A cada segundo
- **Reset**: Quando dados são carregados
- **Display**: No header do card

### Deduplicação de Dados
- **Objetivo**: Remove entradas duplicadas automaticamente
- **Critério**: Prioriza bunkers com coordenadas
- **Tempo**: Mantém entrada mais recente
- **Feedback**: Mostra quantas entradas foram removidas

## Responsividade

### Mobile (< 768px)
- Grid de 1 coluna
- Cards empilhados verticalmente
- Texto menor para economizar espaço

### Desktop (≥ 768px)
- Grid de 2 colunas
- Cards lado a lado
- Mais espaço para detalhes

## Estados de Erro

### Erro de Conexão
- Mensagem: "Erro ao conectar com o servidor"
- Botão de retry disponível
- Log no console para debug

### Erro de Dados
- Mensagem: "Erro ao carregar dados dos bunkers"
- Fallback para estado vazio

### Sem Dados
- Mensagem: "Nenhum dado disponível"
- Interface limpa

## Performance

### Otimizações
- **Debounce**: Evita múltiplas chamadas simultâneas
- **Cleanup**: Limpa intervalos ao desmontar componente
- **Memoização**: Evita re-renders desnecessários
- **Countdown**: Timer visual para próxima atualização
- **Deduplicação**: Remove entradas duplicadas automaticamente

### Limitações
- Scroll limitado para listas longas (max-h-40)
- Auto-refresh a cada 2 horas (configurável)
- Countdown atualiza a cada segundo

## Próximas Melhorias

### Funcionalidades Futuras
1. **Filtros**: Por nome, status, coordenadas
2. **Mapa**: Visualização em mapa dos bunkers
3. **Notificações**: Alertas quando bunker muda de status
4. **Histórico**: Timeline de ativações
5. **Export**: Exportar dados em CSV/JSON

### Melhorias Técnicas
1. **WebSocket**: Atualizações em tempo real
2. **Cache**: Cache local para melhor performance
3. **Pagination**: Para muitos bunkers
4. **Search**: Busca por nome
5. **Sorting**: Ordenação por diferentes critérios

## Testes

### Testes Manuais
- [x] Carregamento inicial
- [x] Auto-refresh
- [x] Estados de erro
- [x] Responsividade
- [x] Formatação de dados

### Testes Automatizados (Futuro)
- Unit tests para formatação
- Integration tests para API
- E2E tests para interface

## Dependências

### Internas
- `framer-motion`: Animações
- `../services/bunkerService`: Serviço de dados
- `../config/api`: Configuração da API

### Externas
- React 18+
- TypeScript
- Tailwind CSS

## Configuração

### Variáveis de Ambiente
- `VITE_BACKEND_URL`: URL do backend (padrão: http://localhost:3000)

### Configuração da API
- Endpoint configurado em `src/config/api.ts`
- Proxy configurado em `vite.config.ts`

## Troubleshooting

### Problemas Comuns

#### 1. Card não carrega
- Verificar se backend está rodando
- Verificar console para erros de CORS
- Verificar se endpoint está correto

#### 2. Dados não atualizam
- Verificar se auto-refresh está funcionando
- Verificar se não há erros no console
- Testar botão de atualização manual

#### 3. Layout quebrado
- Verificar classes do Tailwind
- Verificar responsividade
- Verificar se não há conflitos de CSS

### Debug
- Console logs para erros de API
- Network tab para verificar chamadas
- React DevTools para inspecionar estado 