# 📡 **Sistema de Webhooks Discord - SCUM Backend**

Documentação completa do sistema de notificações automáticas para Discord.

## 🎯 **Visão Geral**

O SCUM Backend envia automaticamente notificações para canais do Discord através de webhooks configurados. Isso permite monitoramento em tempo real de todos os eventos importantes do servidor.

## ⚙️ **Configuração**

### **Arquivo de Configuração**
Os webhooks são configurados no arquivo `data/webhooks.json`:

```json
{
  "serverstatus": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

### **Adicionando Novos Webhooks**
Para adicionar mais webhooks, simplesmente adicione novas entradas:

```json
{
  "serverstatus": "https://discord.com/api/webhooks/...",
  "adminlog": "https://discord.com/api/webhooks/...",
  "vehicle-log": "https://discord.com/api/webhooks/..."
}
```

### **Chaves criadas automaticamente na inicialização**
Ao iniciar, o backend garante que algumas chaves essenciais existam no `data/webhooks.json`.
Se estiverem faltando, ele cria com valor vazio (`""`):

- **`bank_transaction`**
- **`cargo_drop`**

Exemplo:

```json
{
  "bank_transaction": "",
  "cargo_drop": ""
}
```

## 📋 **Eventos Suportados**

### **🚀 Inicialização do Backend**
- **Evento:** `backend_started`
- **Descrição:** Enviado quando o backend é iniciado
- **Cor:** Verde (0x00ff00)
- **Webhook:** `serverstatus`

### **🔄 Controle do Servidor**

#### **Iniciar Servidor**
- **`server_starting`** - Servidor iniciando (Laranja 0xffaa00)
- **`server_started`** - Servidor iniciado com sucesso (Verde 0x00ff00)
- **`server_start_failed`** - Falha ao iniciar (Vermelho 0xff0000)

#### **Parar Servidor**
- **`server_stopping`** - Servidor parando (Laranja 0xffaa00)
- **`server_stopped`** - Servidor parado (Azul 0x0099ff)

#### **Reiniciar Servidor**
- **`server_restarting`** - Servidor reiniciando (Laranja 0xffaa00)
- **`server_restarted`** - Servidor reiniciado com sucesso (Verde 0x00ff00)
- **`server_restart_failed`** - Falha no reinício (Vermelho 0xff0000)

### **⏰ Agendador de Reinicializações**
- **`restart_scheduled`** - Reinicialização agendada
- **`restart_started`** - Reinicialização iniciada
- **`restart_completed`** - Reinicialização concluída
- **`restart_failed`** - Falha na reinicialização

## 🎨 **Formato das Mensagens**

### **Estrutura do Embed**
As mensagens são enviadas como embeds do Discord com:

```json
{
  "title": "🔄 Servidor Reiniciando",
  "description": "O servidor SCUM está sendo reiniciado...",
  "color": 16753920,
  "timestamp": "2025-10-16T19:49:18.197442Z",
  "fields": [
    {
      "name": "Porta",
      "value": "8900",
      "inline": true
    },
    {
      "name": "Max Players",
      "value": "64",
      "inline": true
    },
    {
      "name": "Status",
      "value": "Reiniciando",
      "inline": true
    }
  ]
}
```

### **Cores por Evento**
- **Verde (0x00ff00):** Sucesso, servidor rodando
- **Vermelho (0xff0000):** Erro, falha
- **Laranja (0xffaa00):** Processando, aguardando
- **Azul (0x0099ff):** Informativo, parado

## 🔧 **Configurações Avançadas**

### **Rate Limiting**
- **Máximo:** 30 requisições por minuto
- **Retry:** 3 tentativas com delay de 5 segundos
- **Timeout:** 10 segundos por requisição

### **Tratamento de Erros**
- Falhas de rede são automaticamente retentadas
- Logs detalhados de todas as tentativas
- Fallback gracioso se webhook não estiver disponível

## 📊 **Monitoramento**

### **Logs de Webhook**
Todos os envios de webhook são registrados nos logs:

```
2025-10-16 19:49:18,197 - scum_backend - INFO - Webhook enviado com sucesso para Discord
2025-10-16 19:49:18,198 - scum_backend - INFO - Webhook 'serverstatus' enviado com sucesso
```

### **Verificação de Status**
Para verificar o status dos webhooks, consulte os logs em `data/logs/scum_backend.log`.

## 🚀 **Exemplos de Uso**

### **Testando Webhooks**
```bash
# Iniciar servidor (envia webhook)
curl -X POST http://localhost:3000/api/server/start

# Parar servidor (envia webhook)
curl -X POST http://localhost:3000/api/server/stop

# Reiniciar servidor (envia webhooks)
curl -X POST http://localhost:3000/api/server/restart
```

### **Verificando Logs**
```bash
# Ver últimos webhooks enviados
grep "Webhook" data/logs/scum_backend.log | tail -10

# Ver webhooks de restart
grep "restart" data/logs/scum_backend.log | grep "Webhook"
```

## 🔍 **Troubleshooting**

### **Webhook não está sendo enviado**
1. Verificar se o arquivo `data/webhooks.json` existe
2. Verificar se a URL do webhook está correta
3. Verificar logs para erros de rede
4. Verificar se o Discord está acessível

### **Webhook está sendo enviado mas não aparece no Discord**
1. Verificar se o webhook ainda está ativo no Discord
2. Verificar se o canal tem permissões corretas
3. Verificar se o bot tem permissão para enviar mensagens

### **Rate Limit atingido**
- O sistema automaticamente gerencia rate limits
- Aguarde alguns minutos antes de tentar novamente
- Verifique se não há muitos testes simultâneos

## 📝 **Notas Importantes**

- **Webhooks são enviados automaticamente** - não é necessário configuração adicional
- **Todos os eventos importantes** são notificados
- **Sistema robusto** com retry automático e tratamento de erros
- **Logs detalhados** para debugging e monitoramento

---

**Documentação atualizada em: 16/10/2025**  
**Versão: 1.0.0**
