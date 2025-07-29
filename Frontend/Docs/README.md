# 📚 Documentação do ScumServerManager 2.0

## 🎯 Visão Geral

Este diretório contém toda a documentação técnica do sistema ScumServerManager 2.0, incluindo guias de implementação, especificações de API e tutoriais de uso.

## 📋 Índice da Documentação

### 🏰 Sistema de Bunkers
- **[Sistema de Status dos Bunkers](./bunker-status-system.md)** - Documentação completa do novo sistema de bunkers com banco de dados persistente e interface detalhada

### 🔗 Webhooks do Discord
- **[Webhooks do Discord](./discord-webhooks.md)** - Guia completo de configuração e uso dos webhooks
- **[Webhook Admin Log](./webhook-adminlog.md)** - Configuração do webhook para logs de administração
- **[Webhook Bunkers](./webhook-bunkers.md)** - Configuração do webhook para notificações de bunkers
- **[Webhook Fama](./webhook-fama.md)** - Configuração do webhook para sistema de fama

### 🏆 Sistema de Fama
- **[Top 3 Card](./fame-top3-card.md)** - Implementação do card estático dos top 3 jogadores
- **[Breaking News Bar](./fame-breaking-news-bar.md)** - Barra de notícias para exibição dos top 3

### 🚗 Sistema de Veículos
- **[Bunkers Card](./bunkers-card.md)** - Documentação do sistema de bunkers (versão anterior)

### 🔧 Configurações e Endpoints
- **[Acesso à Rede do Backend](./backend-network-access.md)** - Configurações de rede e acesso
- **[Dúvidas Backend Chat in Game](./duvidas-backend-chat-in-game.md)** - FAQ sobre chat in-game
- **[Solicitação Endpoint GET Webhook PainelPlayers](./solicitacao-endpoint-get-webhook-painelplayers.md)** - Especificação do endpoint

## 🚀 Principais Atualizações

### ✅ Sistema de Bunkers Reformulado
O sistema de bunkers foi **completamente reformulado** com as seguintes melhorias:

1. **Banco de Dados Persistente**
   - Dados mantidos entre reinicializações
   - Arquivo: `src/data/bunkers/bunkers.json`

2. **Formatação Detalhada**
   - Status completo de bunkers ativos e bloqueados
   - Informações de coordenadas, tempo de ativação e métodos
   - Formatação otimizada para Discord

3. **Interface Completa**
   - Card dedicado no dashboard
   - Atualização automática a cada 5 minutos
   - Botão de atualização manual
   - Indicador de última atualização

### ✅ Novos Webhooks Implementados
- **Webhook Admin Log** - Para logs de administração
- **Webhook Bunkers** - Para notificações de bunkers
- **Webhook Fama** - Para sistema de reputação

### ✅ Sistema de Ocultação de Steam IDs
- Toggle global para ocultar Steam IDs em todas as seções
- Ideal para gravação de vídeos
- Persistência no localStorage

## 🔧 Estrutura da API

### Endpoints Principais

#### Bunkers
- `GET /api/bunkers/status` - Status atual dos bunkers
- `POST /api/bunkers/force-update` - Força atualização

#### Webhooks
- `GET /api/webhooks/painel-players` - Consulta webhook Painel Players
- `POST /api/webhooks/painel-players` - Salva webhook Painel Players
- `GET /api/webhooks/veiculos` - Consulta webhook Veículos
- `POST /api/webhooks/veiculos` - Salva webhook Veículos
- `GET /api/webhooks/admin-log` - Consulta webhook Admin Log
- `POST /api/webhooks/admin-log` - Salva webhook Admin Log
- `GET /api/webhooks/chat-in-game` - Consulta webhook Chat in Game
- `POST /api/webhooks/chat-in-game` - Salva webhook Chat in Game
- `GET /api/webhooks/bunkers` - Consulta webhook Bunkers
- `POST /api/webhooks/bunkers` - Salva webhook Bunkers
- `GET /api/webhooks/fama` - Consulta webhook Fama
- `POST /api/webhooks/fama` - Salva webhook Fama

#### Jogadores
- `GET /api/players/painel` - Lista de jogadores
- `GET /api/fame/points` - Pontos de fama

#### Veículos
- `GET /api/vehicles/log` - Log de eventos de veículos

## 🎨 Componentes Principais

### Dashboard
- **DashboardHeader** - Header principal com navegação
- **DashboardSidebar** - Menu lateral com seções
- **ScumBackground** - Background temático do SCUM

### Cards de Informação
- **BunkerStatusCard** - Status detalhado dos bunkers (NOVO)
- **ChatMessagesCard** - Mensagens do chat in-game
- **DiscordWebhookCard** - Configuração de webhooks
- **FameTop3Card** - Top 3 jogadores de fama

### Tabelas e Listas
- **PlayersTable** - Lista completa de jogadores
- **VehiclesTable** - Histórico de eventos de veículos
- **AdminLogTable** - Log de administração
- **FamePlayersList** - Lista de jogadores por fama

### Breaking News
- **FameTop3BreakingNewsBar** - Barra de top 3
- **VehicleEventBreakingNewsBar** - Barra de eventos de veículos

## 🔄 Atualizações Automáticas

### Frequências de Atualização
- **Jogadores**: 30 segundos
- **Top 3 Fama**: 30 segundos
- **Bunkers**: 30 minutos
- **Veículos**: 30 segundos
- **Admin Log**: Sob demanda

### Indicadores de Atualização
- Timestamp da última atualização em cada card
- Spinners de loading durante atualizações
- Botões de atualização manual

## 🎯 Funcionalidades Especiais

### Sistema de Ocultação de Steam IDs
```typescript
// Toggle global para ocultar Steam IDs
const [hideSteamIds, setHideSteamIds] = useState(false);

// Persistência no localStorage
useEffect(() => {
  localStorage.setItem('hideSteamIds', hideSteamIds.toString());
}, [hideSteamIds]);
```

### Compatibilidade com Webhooks
- Todos os webhooks seguem o mesmo padrão
- Tratamento de erros independente
- Logs detalhados para debug

## 📱 Responsividade

O sistema é totalmente responsivo com:
- Grid adaptativo (1 coluna mobile, 2+ colunas desktop)
- Cards que se ajustam ao tamanho da tela
- Navegação otimizada para mobile

## 🚀 Próximas Implementações

1. **Visualização de Mapa** para bunkers
2. **Filtros Avançados** por região/status
3. **Notificações Push** para eventos importantes
4. **Histórico Detalhado** de ativações
5. **Integração com Discord** mais rica

## 📞 Suporte

Para dúvidas técnicas ou problemas de implementação, consulte a documentação específica de cada funcionalidade ou entre em contato com a equipe de desenvolvimento.

---

**Última atualização:** Janeiro 2025  
**Versão:** 2.0  
**Status:** ✅ 100% Funcional 