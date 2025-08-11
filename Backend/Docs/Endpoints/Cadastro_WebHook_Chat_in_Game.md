# Cadastro WebHook Chat in Game

## Descrição
Endpoint para cadastrar e consultar o webhook do Discord para o sistema de chat in game do SCUM Server Manager.

## Endpoints

### 1. Cadastrar/Atualizar Webhook
**POST** `/api/webhook/chat_in_game`

Cadastra ou atualiza a URL do webhook do Discord para receber mensagens do chat in game.

#### Parâmetros
- **url** (string, obrigatório): URL do webhook do Discord
  - Deve começar com `https://`
  - Formato: `https://discord.com/api/webhooks/SEU_WEBHOOK_ID/SEU_WEBHOOK_TOKEN`

#### Exemplo de Request
```json
{
    "url": "https://discord.com/api/webhooks/123456789/abcdefghijklmnop"
}
```

#### Exemplo de Response (Sucesso)
```json
{
    "success": true,
    "message": "Webhook do chat_in_game cadastrado/atualizado com sucesso.",
    "url": "https://discord.com/api/webhooks/123456789/abcdefghijklmnop"
}
```

#### Exemplo de Response (Erro)
```json
{
    "success": false,
    "message": "URL do webhook inválida."
}
```

### 2. Consultar Webhook
**GET** `/api/webhook/chat_in_game`

Consulta a URL do webhook atualmente cadastrada.

#### Exemplo de Response (Com webhook cadastrado)
```json
{
    "success": true,
    "message": "Webhook recuperado com sucesso.",
    "url": "https://discord.com/api/webhooks/123456789/abcdefghijklmnop"
}
```

#### Exemplo de Response (Sem webhook cadastrado)
```json
{
    "success": false,
    "message": "Nenhum webhook cadastrado para chat_in_game.",
    "url": null
}
```

## Como Obter o Webhook do Discord

1. Acesse seu servidor Discord
2. Vá em **Configurações do Canal** → **Integrações** → **Webhooks**
3. Clique em **Novo Webhook**
4. Configure o nome e avatar (opcional)
5. Copie a URL do webhook
6. Use a URL no endpoint POST para cadastrar

## Formato das Mensagens Enviadas

As mensagens do chat são enviadas para o Discord no formato:
```
🎯 NomeDoJogador: mensagem
🌐 NomeDoJogador: mensagem
👥 NomeDoJogador: mensagem
```

### Emojis por Tipo de Chat:
- **Local** → 🎯
- **Global** → 🌐
- **Squad** → 👥

## Armazenamento

O webhook é salvo no arquivo `src/data/webhooks.json` com a chave `Chat_in_Game`.

## Códigos de Status HTTP

- **200**: Sucesso
- **400**: URL inválida (não começa com https://)
- **500**: Erro interno do servidor

## Exemplo de Uso com cURL

### Cadastrar webhook:
```bash
curl -X POST http://localhost:3000/api/webhook/chat_in_game \
-H "Content-Type: application/json" \
-d '{"url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"}'
```

### Consultar webhook:
```bash
curl http://localhost:3000/api/webhook/chat_in_game
``` 