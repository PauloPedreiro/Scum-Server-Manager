# 🏰 Sistema de Status dos Bunkers - Frontend

## 📋 Visão Geral

O sistema de status dos bunkers foi completamente reformulado para fornecer informações detalhadas e em tempo real sobre o estado dos bunkers no servidor SCUM. O novo sistema inclui banco de dados persistente, formatação detalhada e controle inteligente de processamento.

## 🔄 Principais Características

### ✅ Funcionalidades Implementadas

1. **Banco de Dados Persistente**
   - Dados mantidos entre reinicializações do servidor
   - Arquivo: `src/data/bunkers/bunkers.json`

2. **Formatação Detalhada**
   - Status completo de bunkers ativos e bloqueados
   - Informações de coordenadas, tempo de ativação e métodos
   - Formatação otimizada para Discord

3. **Controle de Processamento**
   - Evita reprocessamento desnecessário
   - Sistema otimizado para performance

4. **Interface Completa**
   - Card dedicado no dashboard
   - Atualização automática a cada 30 minutos
   - Contador visual de countdown
   - Botão de atualização manual
   - Indicador de última atualização

## 📊 Estrutura de Dados

### Resposta da API - GET `/api/bunkers/status`

```json
{
  "success": true,
  "message": "Status dos bunkers recuperado com sucesso.",
  "data": {
    "active": [
      {
        "name": "A1",
        "status": "active",
        "activated": "00h 00m 00s",
        "coordinates": {
          "x": -348529.312,
          "y": -469201.781,
          "z": 4247.645
        },
        "lastUpdate": "2025.07.15-20.16.51",
        "activationTime": "2025.07.15-20.16.51",
        "activationMethod": "keycard"
      }
    ],
    "locked": [
      {
        "name": "D1",
        "status": "locked",
        "nextActivation": "21h 53m 18s",
        "coordinates": {
          "x": -537889.562,
          "y": 540004.312,
          "z": 81279.648
        },
        "lastUpdate": "2025.07.15-20.16.51"
      }
    ],
    "lastUpdate": "2025.07.15-20.16.51"
  },
  "logFile": "gameplay_2025.07.15.log"
}
```

## 🎯 Campos Disponíveis

### Para Bunkers Ativos:
- `status`: Sempre "active"
- `activated`: Tempo desde ativação (ex: "00h 00m 00s")
- `coordinates`: Objeto com x, y, z (pode ser null)
- `lastUpdate`: Timestamp da última atualização
- `activationTime`: Timestamp da ativação
- `activationMethod`: "keycard" (quando aplicável)

### Para Bunkers Bloqueados:
- `status`: Sempre "locked"
- `nextActivation`: Tempo até próxima ativação
- `coordinates`: Objeto com x, y, z
- `lastUpdate`: Timestamp da última atualização

## 🎨 Interface Implementada

### Componente: `BunkerStatusCard`

O componente exibe:

1. **Header com Indicador de Atualização**
   - Título: "🏰 Status dos Bunkers"
   - Timestamp da última atualização

2. **Seção de Bunkers Ativos**
   - Contador: "🟢 Ativos (X)"
   - Cards individuais para cada bunker ativo
   - Informações: tempo ativado, coordenadas, método de ativação

3. **Seção de Bunkers Bloqueados**
   - Contador: "🔴 Bloqueados (X)"
   - Cards individuais para cada bunker bloqueado
   - Informações: tempo até próxima ativação, coordenadas

4. **Informações Gerais**
   - Total de bunkers
   - Timestamp da atualização do sistema

5. **Botão de Atualização Manual**
   - Atualização sob demanda
   - Indicador de loading durante atualização

## 🔧 Funcionalidades Técnicas

### Atualização Automática
```typescript
// Hook global de countdown (30 minutos)
const { countdown, resetCountdown, formatCountdown } = useBunkersCountdown();

// Trigger update when countdown reaches 0
useEffect(() => {
  if (countdown <= 1 && hasLoadedRef.current) {
    fetchBunkerStatus();
  }
}, [countdown]);
```

### Tratamento de Erros
- Exibição de mensagens de erro amigáveis
- Botão "Tentar Novamente" em caso de falha
- Logs detalhados no console para debug

### Formatação de Coordenadas
```typescript
const formatCoordinates = (coordinates: BunkerCoordinates | null) => {
  if (!coordinates) return 'N/A';
  return `X: ${coordinates.x.toFixed(0)}, Y: ${coordinates.y.toFixed(0)}, Z: ${coordinates.z.toFixed(0)}`;
};
```

## 🎨 Estilos CSS

### Cards de Bunkers Ativos
```css
.bg-green-900/20 border-l-4 border-green-500 rounded-r-lg p-4
```

### Cards de Bunkers Bloqueados
```css
.bg-red-900/20 border-l-4 border-red-500 rounded-r-lg p-4
```

### Estados de Loading e Erro
- Spinner animado durante carregamento
- Mensagens de erro centralizadas
- Botões com estados disabled

## 📱 Integração no Dashboard

### Localização
- Seção: Dashboard principal
- Posição: Card ao lado do Chat Messages
- Layout: Grid responsivo (1 coluna mobile, 2 colunas desktop)

### Props Aceitas
```typescript
interface BunkerStatusCardProps {
  hideSteamIds?: boolean; // Para compatibilidade com sistema de ocultação
}
```

## 🔄 Endpoints Disponíveis

### GET `/api/bunkers/status`
- **Descrição:** Obtém status atual dos bunkers
- **Uso:** Para exibir informações em tempo real
- **Cache:** Sistema evita reprocessamento desnecessário

### POST `/api/bunkers/force-update`
- **Descrição:** Força atualização sem enviar webhook
- **Uso:** Para atualizar dados manualmente
- **Resposta:** Mesma estrutura do GET /status

## 🚀 Próximas Melhorias Sugeridas

1. **Visualização de Mapa**
   - Integração com mapa do SCUM
   - Marcadores para localização dos bunkers

2. **Filtros Avançados**
   - Filtrar por status (ativo/bloqueado)
   - Filtrar por região/coordenadas

3. **Notificações Push**
   - Alertas quando bunkers são ativados
   - Notificações de proximidade de ativação

4. **Histórico de Ativações**
   - Timeline de ativações anteriores
   - Estatísticas de uso por bunker

5. **Integração com Discord**
   - Webhook para notificações automáticas
   - Embed rico com informações detalhadas

## ⚠️ Notas Importantes

1. **Compatibilidade:** A API mantém compatibilidade com versões anteriores
2. **Performance:** Sistema otimizado para evitar reprocessamento
3. **Dados Persistidos:** Informações mantidas entre reinicializações
4. **Tempo Real:** Atualizações automáticas via webhook Discord
5. **Coordenadas:** Podem ser null para bunkers sem localização

## 🎯 Status da Implementação

✅ **100% Funcional**
- Componente criado e integrado
- Atualização automática implementada
- Tratamento de erros completo
- Interface responsiva e moderna
- Compatibilidade com sistema de ocultação de Steam IDs

O sistema está pronto para uso e fornece todas as informações necessárias para monitoramento completo dos bunkers! 🏰✨ 