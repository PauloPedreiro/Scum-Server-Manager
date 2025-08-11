# Controle do Servidor SCUM

## Visão Geral

O sistema de controle do servidor SCUM permite gerenciar o status, iniciar, parar e reiniciar o servidor através de uma interface web moderna e intuitiva.

## Funcionalidades

### 1. Monitoramento em Tempo Real
- **Status do Servidor**: Exibe se o servidor está online ou offline
- **Informações do Processo**: PID, uptime, número de reinicializações
- **Configurações**: Porta, max players, BattlEye, versão
- **Auto-atualização**: Status atualizado automaticamente a cada 10 segundos

### 2. Controles do Servidor
- **Iniciar Servidor**: Inicia o servidor SCUM se não estiver rodando
- **Parar Servidor**: Para o servidor SCUM de forma segura
- **Reiniciar Servidor**: Para e inicia o servidor novamente

### 3. Interface Visual
- **Indicadores Visuais**: Cores diferentes para status online/offline
- **Botões Inteligentes**: Desabilitados quando não aplicáveis
- **Feedback em Tempo Real**: Loading states e mensagens de erro
- **Design Responsivo**: Funciona em desktop e mobile

## Estrutura de Arquivos

```
src/
├── components/
│   └── ServerControlCard.tsx    # Componente principal
├── services/
│   └── serverService.ts         # Serviço de API
├── hooks/
│   └── useServerStatus.tsx      # Hook personalizado
└── types/
    └── server.ts               # Tipos TypeScript
```

## Endpoints da API

### GET `/api/server/status`
Retorna o status atual do servidor.

**Resposta:**
```json
{
  "success": true,
  "status": {
    "isRunning": true,
    "pid": "12345",
    "startTime": "2024-01-15T10:30:00.000Z",
    "uptime": 1800000,
    "restartCount": 2,
    "lastError": null,
    "version": "0.9.0"
  },
  "config": {
    "port": 8900,
    "maxPlayers": 64,
    "useBattleye": true,
    "serverPath": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64"
  }
}
```

### POST `/api/server/start`
Inicia o servidor SCUM.

### POST `/api/server/stop`
Para o servidor SCUM.

### POST `/api/server/restart`
Reinicia o servidor SCUM.

## Componentes

### ServerControlCard
Componente principal que exibe o controle do servidor.

**Props:**
- `className?: string` - Classes CSS adicionais

**Funcionalidades:**
- Exibe status em tempo real
- Botões de controle (iniciar, parar, reiniciar)
- Informações detalhadas do servidor
- Auto-atualização do status

### useServerStatus Hook
Hook personalizado para gerenciar o estado do servidor.

**Parâmetros:**
- `autoRefresh: boolean` - Se deve atualizar automaticamente (padrão: true)
- `refreshInterval: number` - Intervalo de atualização em ms (padrão: 10000)

**Retorna:**
- `status: ServerStatus | null` - Status atual do servidor
- `config: ServerConfig | null` - Configurações do servidor
- `loading: boolean` - Estado de carregamento
- `error: string | null` - Mensagem de erro
- `lastUpdate: Date | null` - Última atualização
- `refreshStatus: () => Promise<void>` - Função para atualizar status
- `startServer: () => Promise<boolean>` - Função para iniciar servidor
- `stopServer: () => Promise<boolean>` - Função para parar servidor
- `restartServer: () => Promise<boolean>` - Função para reiniciar servidor

## Tipos TypeScript

### ServerStatus
```typescript
interface ServerStatus {
  isRunning: boolean;
  pid: string | null;
  startTime: string | null;
  lastCheck: string | null;
  uptime: number;
  restartCount: number;
  lastError: string | null;
  version: string | null;
}
```

### ServerConfig
```typescript
interface ServerConfig {
  port: number;
  maxPlayers: number;
  useBattleye: boolean;
  serverPath: string;
}
```

## Integração no Dashboard

O componente `ServerControlCard` está integrado no **dashboard principal**, sendo exibido na primeira linha quando o usuário acessa a seção "Dashboard". Isso permite que administradores tenham acesso rápido ao controle do servidor sem precisar navegar para outras seções.

## Notificações Discord

Todas as ações de controle do servidor (iniciar, parar, reiniciar) enviam notificações para o Discord quando configurado, seguindo o padrão de webhooks do sistema.

## Tratamento de Erros

- **Erro de Conexão**: Exibe mensagem amigável quando não consegue conectar
- **Erro de Permissão**: Informa quando não tem permissão para executar ações
- **Servidor Já Rodando**: Avisa quando tenta iniciar servidor já ativo
- **Servidor Não Rodando**: Avisa quando tenta parar servidor inativo

## Segurança

- Todas as requisições passam pelo sistema de autenticação
- Validação de permissões no backend
- Logs de todas as ações administrativas
- Timeout para operações longas

## Performance

- Auto-atualização otimizada (10s de intervalo)
- Debounce em ações de controle
- Cache de status para reduzir requisições
- Loading states para feedback visual

## Responsividade

O componente é totalmente responsivo e funciona bem em:
- Desktop (1920x1080+)
- Tablet (768px+)
- Mobile (320px+)

## Acessibilidade

- Botões com estados disabled apropriados
- Indicadores visuais de status
- Mensagens de erro claras
- Navegação por teclado suportada 