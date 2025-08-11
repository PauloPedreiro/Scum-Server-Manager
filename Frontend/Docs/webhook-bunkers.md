# Webhook Bunkers

## Descrição
O webhook Bunkers permite configurar notificações do Discord para eventos relacionados aos bunkers do servidor SCUM. Quando configurado, todas as atividades relacionadas aos bunkers (como aberturas, fechamentos, eventos especiais, etc.) serão enviadas automaticamente para o canal do Discord configurado.

## Funcionalidades

### Cadastro de Webhook
- **Endpoint**: `POST /api/webhook/bunkers`
- **Descrição**: Cadastra ou atualiza a URL do webhook para eventos de bunkers
- **Parâmetros**: 
  - `url` (string, obrigatório): URL do webhook do Discord
- **Exemplo de uso**:
  ```json
  {
    "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
  }
  ```

### Consulta de Webhook
- **Endpoint**: `GET /api/webhook/bunkers`
- **Descrição**: Consulta a URL do webhook atualmente configurada
- **Resposta**: Retorna a URL configurada ou null se não houver webhook

### Teste de Webhook
- **Funcionalidade**: Testa a conectividade do webhook enviando uma mensagem de teste
- **Mensagem de teste**: Envia uma mensagem formatada para verificar se o webhook está funcionando

## Interface no Dashboard

### Card de Configuração
O card "WebHook Bunkers" na seção Discord do dashboard permite:

1. **Campo de URL**: Input para inserir a URL do webhook do Discord
2. **Botão Salvar**: Salva a configuração do webhook
3. **Botão Teste**: Testa a conectividade do webhook
4. **Feedback visual**: Mostra mensagens de sucesso ou erro

### Validação
- A URL deve começar com `https://`
- Deve seguir o padrão do Discord: `https://discord.com/api/webhooks/ID/TOKEN`
- Validação automática do formato da URL

## Integração com Backend

### Armazenamento
- O webhook é salvo em `src/data/webhooks.json` no backend
- Prioridade sobre o valor do `.env` (`WEBHOOK_BUNKERS`)
- Atualização imediata após o cadastro

### Funcionamento
1. Backend consulta primeiro o arquivo `webhooks.json`
2. Se não existir, usa o valor do `.env`
3. Envia notificações para o Discord em tempo real
4. Não altera o arquivo `.env`

## Exemplo de Notificação

Quando um evento de bunker ocorre, o Discord receberá uma mensagem como:

```
🏰 **Evento de Bunker**

**Tipo**: Abertura de Bunker
**Localização**: Bunker A1
**Jogador**: PlayerName (SteamID: 123456789)
**Hora**: 2024-01-15 14:30:25
**Status**: Sucesso

📋 Detalhes completos no log do servidor
```

## Configuração no Discord

1. Crie um webhook no canal desejado do Discord
2. Copie a URL do webhook
3. Cole no campo do dashboard
4. Clique em "Salvar"
5. Teste a conectividade com o botão "Teste"

## Observações

- O webhook é usado apenas para eventos de bunkers
- Não afeta outros tipos de notificação
- Funciona independentemente dos outros webhooks
- Suporte a múltiplos canais (webhooks diferentes)
- Notificações são enviadas em tempo real 