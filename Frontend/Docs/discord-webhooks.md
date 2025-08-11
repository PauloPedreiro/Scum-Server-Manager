# Discord Webhooks - SCUM Server Manager

## Visão Geral

O sistema de webhooks do Discord permite configurar notificações automáticas para diferentes eventos do servidor SCUM. Atualmente, o webhook **"Painel Players"** está integrado com a API do backend.

## Webhooks Disponíveis

### 1. WebHook Painel Players ✅ (Integrado com API)
- **Endpoint:** `/api/webhook/painelplayers`
- **Funcionalidade:** Notificações do painel de jogadores
- **Status:** Integrado com backend real
- **Salvamento:** No arquivo `src/data/webhooks.json` do backend

### 2. WebHook Veiculos 🔄 (Simulado)
- **Funcionalidade:** Notificações relacionadas a veículos
- **Status:** Simulado (preparado para integração)

### 3. WebHook Admin Log ✅ (Integrado com API)
- **Endpoint:** `/api/webhook/adminlog`
- **Funcionalidade:** Logs administrativos
- **Status:** Integrado com backend real
- **Salvamento:** No arquivo `src/data/webhooks.json` do backend

### 4. Chat in Game 🔄 (Simulado)
- **Funcionalidade:** Mensagens do chat do jogo
- **Status:** Simulado (preparado para integração)

### 5. WebHook Bunkers 🔄 (Simulado)
- **Funcionalidade:** Eventos relacionados aos bunkers
- **Status:** Simulado (preparado para integração)

### 6. WebHook Fama ✅ (Integrado com API)
- **Endpoint:** `/api/webhook/famepoints`
- **Funcionalidade:** Eventos do sistema de fama
- **Status:** Integrado com backend real
- **Salvamento:** No arquivo `src/data/webhooks.json` do backend

## Como Usar

### Configuração dos Webhooks

#### WebHook Painel Players
1. **Acesse a seção Discord:**
   - Clique em "DISCORD" na sidebar
   - Localize o card "WebHook Painel Players"

2. **Configure o webhook:**
   - Insira a URL do webhook do Discord
   - Exemplo: `https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI`

3. **Salve a configuração:**
   - Clique em "SALVAR"
   - O sistema enviará a URL para o backend
   - O backend salvará em `src/data/webhooks.json`

4. **Teste o webhook:**
   - Clique em "TESTE"
   - Uma mensagem de teste será enviada para o Discord
   - Verifique se a mensagem chegou no canal

#### WebHook Admin Log
1. **Acesse a seção Discord:**
   - Clique em "DISCORD" na sidebar
   - Localize o card "WebHook Admin Log"

2. **Configure o webhook:**
   - Insira a URL do webhook do Discord
   - Exemplo: `https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI`

3. **Salve a configuração:**
   - Clique em "SALVAR"
   - O sistema enviará a URL para o backend
   - O backend salvará em `src/data/webhooks.json`

4. **Teste o webhook:**
   - Clique em "TESTE"
   - Uma mensagem de teste será enviada para o Discord
   - Verifique se a mensagem chegou no canal

#### WebHook Bunkers
1. **Acesse a seção Discord:**
   - Clique em "DISCORD" na sidebar
   - Localize o card "WebHook Bunkers"

2. **Configure o webhook:**
   - Insira a URL do webhook do Discord
   - Exemplo: `https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI`

3. **Salve a configuração:**
   - Clique em "SALVAR"
   - O sistema enviará a URL para o backend
   - O backend salvará em `src/data/webhooks.json`

4. **Teste o webhook:**
   - Clique em "TESTE"
   - Uma mensagem de teste será enviada para o Discord
   - Verifique se a mensagem chegou no canal

#### WebHook Fama
1. **Acesse a seção Discord:**
   - Clique em "DISCORD" na sidebar
   - Localize o card "WebHook Fama"

2. **Configure o webhook:**
   - Insira a URL do webhook do Discord
   - Exemplo: `https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI`

3. **Salve a configuração:**
   - Clique em "SALVAR"
   - O sistema enviará a URL para o backend
   - O backend salvará em `src/data/webhooks.json`

4. **Teste o webhook:**
   - Clique em "TESTE"
   - Uma mensagem de teste será enviada para o Discord
   - Verifique se a mensagem chegou no canal

## Configuração do Backend

### Variável de Ambiente (Opcional)
```env
VITE_BACKEND_URL=http://localhost:3000
```

### Endpoints da API

#### Painel Players
```http
POST http://localhost:3000/api/webhook/painelplayers
Content-Type: application/json

{
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

#### Admin Log
```http
POST http://localhost:3000/api/webhook/adminlog
Content-Type: application/json

{
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

#### Bunkers
```http
POST http://localhost:3000/api/webhook/bunkers
Content-Type: application/json

{
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

#### Fama
```http
POST http://localhost:3000/api/webhook/famepoints
Content-Type: application/json

{
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

## Estrutura de Arquivos

```
src/
├── components/
│   └── DiscordWebhookCard.tsx    # Componente do card
├── services/
│   └── webhookService.ts         # Serviço de API
├── config/
│   └── api.ts                    # Configuração da API
└── pages/
    └── Dashboard.tsx             # Página principal
```

## Próximos Passos

Para integrar os outros webhooks com o backend:

1. **Criar endpoints no backend:**
   - `/api/webhook/veiculos`
   - `/api/webhook/chatgame`
   - `/api/webhook/bunkers`

2. **Atualizar o serviço:**
   - Adicionar métodos no `WebhookService`
   - Implementar chamadas reais da API

3. **Atualizar o Dashboard:**
   - Modificar `handleSaveWebhook` e `handleTestWebhook`
   - Remover simulações

## Troubleshooting

### Erro de Conexão
- Verifique se o backend está rodando em `http://localhost:3000`
- Confirme se a variável `VITE_BACKEND_URL` está configurada corretamente

### Erro de Webhook
- Verifique se a URL do Discord está correta
- Confirme se o webhook tem permissões de envio
- Teste a URL manualmente no Postman

### Mensagens de Erro
- **"Erro ao conectar com o servidor"**: Backend offline
- **"Erro ao testar webhook"**: URL inválida ou Discord inacessível
- **"HTTP error! status: 404"**: Endpoint não encontrado 