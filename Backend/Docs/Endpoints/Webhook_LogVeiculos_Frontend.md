# 📋 Documentação para Frontend - Webhook LogVeiculos

## 🎯 **Objetivo**
Implementar interface para cadastrar e consultar webhook do Discord para eventos de veículos no SCUM Server.

---

## 🔗 **Endpoints Disponíveis**

### 1. **Cadastrar Webhook**
**POST** `http://localhost:3000/api/webhook/LogVeiculos`

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Webhook LogVeiculos cadastrado com sucesso",
  "data": {
    "url": "https://discord.com/api/webhooks/1393837217826476083/XV6TdcwcMSsU7DRk5Kx4k7nryRGq4uQxig41NF7XUbaB96ZznVRPmZsZ86BNU3uGa6sr"
  }
}
```

**Resposta de Erro (400):**
```json
{
  "success": false,
  "message": "URL do webhook é obrigatória",
  "error": "URL_REQUIRED"
}
```

---

### 2. **Consultar Webhook**
**GET** `http://localhost:3000/api/webhook/LogVeiculos`

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Webhook LogVeiculos encontrado",
  "data": {
    "url": "https://discord.com/api/webhooks/1393837217826476083/XV6TdcwcMSsU7DRk5Kx4k7nryRGq4uQxig41NF7XUbaB96ZznVRPmZsZ86BNU3uGa6sr"
  }
}
```

**Resposta de Erro (404):**
```json
{
  "success": false,
  "message": "Webhook LogVeiculos não encontrado",
  "error": "WEBHOOK_NOT_FOUND"
}
```

---

## 🎨 **Interface Sugerida**

### **Página: Configurações de Webhook**

```typescript
interface WebhookConfig {
  url: string;
  isConfigured: boolean;
  lastTest?: string;
}

interface WebhookResponse {
  success: boolean;
  message: string;
  data?: {
    url: string;
  };
  error?: string;
}
```

### **Componentes Necessários:**

1. **Formulário de Cadastro**
   - Input para URL do webhook
   - Botão "Salvar"
   - Validação de URL do Discord

2. **Status Atual**
   - Mostrar URL atual (mascarada)
   - Botão "Testar Webhook"
   - Indicador de status (✅ Configurado / ❌ Não configurado)

3. **Ações**
   - Botão "Editar"
   - Botão "Remover"
   - Botão "Testar"

---

## 🔧 **Implementação Frontend**

### **1. Função para Cadastrar Webhook**
```typescript
const cadastrarWebhook = async (url: string): Promise<WebhookResponse> => {
  try {
    const response = await fetch('/api/webhook/LogVeiculos', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url })
    });
    
    return await response.json();
  } catch (error) {
    return {
      success: false,
      message: 'Erro ao conectar com o servidor',
      error: 'NETWORK_ERROR'
    };
  }
};
```

### **2. Função para Consultar Webhook**
```typescript
const consultarWebhook = async (): Promise<WebhookResponse> => {
  try {
    const response = await fetch('/api/webhook/LogVeiculos');
    return await response.json();
  } catch (error) {
    return {
      success: false,
      message: 'Erro ao conectar com o servidor',
      error: 'NETWORK_ERROR'
    };
  }
};
```

### **3. Validação de URL**
```typescript
const validarWebhookUrl = (url: string): boolean => {
  const webhookRegex = /^https:\/\/discord\.com\/api\/webhooks\/\d+\/[a-zA-Z0-9_-]+$/;
  return webhookRegex.test(url);
};
```

---

## 🎯 **Funcionalidades Esperadas**

### **1. Cadastro de Webhook**
- ✅ Campo de input para URL
- ✅ Validação em tempo real
- ✅ Botão "Salvar" (desabilitado se URL inválida)
- ✅ Feedback visual de sucesso/erro
- ✅ Loading state durante requisição

### **2. Consulta de Status**
- ✅ Carregar status atual ao abrir página
- ✅ Mostrar URL atual (mascarada: `https://discord.com/api/webhooks/***/***`)
- ✅ Indicador visual de status

### **3. Teste de Webhook**
- ✅ Botão "Testar" que envia evento de exemplo
- ✅ Feedback de sucesso/erro do teste
- ✅ Loading state durante teste

### **4. Gerenciamento**
- ✅ Botão "Editar" (preenche formulário)
- ✅ Botão "Remover" (com confirmação)
- ✅ Confirmação antes de salvar alterações

---

## 🎨 **Exemplo de Interface**

```
┌─────────────────────────────────────┐
│ 🔗 Configuração de Webhook         │
├─────────────────────────────────────┤
│                                     │
│ Status: ✅ Configurado              │
│ URL: https://discord.com/api/***   │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ URL do Webhook:                │ │
│ │ [https://discord.com/api/...] │ │
│ │                                 │ │
│ │ [Salvar] [Testar] [Remover]    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 💡 Como obter o webhook:           │
│ 1. Abra o Discord                 │
│ 2. Vá em Configurações do Canal   │
│ 3. Integrações > Webhooks         │
│ 4. Copie a URL do webhook         │
└─────────────────────────────────────┘
```

---

## 🚀 **Fluxo de Implementação**

1. **Criar página de configurações**
2. **Implementar formulário de cadastro**
3. **Adicionar validação de URL**
4. **Implementar consulta de status**
5. **Adicionar funcionalidade de teste**
6. **Implementar gerenciamento (editar/remover)**
7. **Adicionar feedback visual e loading states**

---

## 📝 **Observações Importantes**

- **URL do Discord**: Deve seguir o padrão `https://discord.com/api/webhooks/ID/TOKEN`
- **Validação**: Implementar validação client-side antes de enviar
- **Feedback**: Sempre mostrar mensagens de sucesso/erro
- **Loading**: Implementar estados de carregamento
- **Segurança**: Mascarar URL na interface (mostrar apenas parte)
- **Responsividade**: Interface deve funcionar em mobile

---

## 🎯 **Resultado Esperado**

Após implementação, o usuário poderá:
- ✅ Cadastrar webhook do Discord
- ✅ Visualizar status atual
- ✅ Testar funcionamento
- ✅ Editar configuração
- ✅ Remover webhook
- ✅ Receber feedback visual adequado

**O webhook será usado automaticamente para enviar eventos de veículos em formato embed para o Discord!** 🚗

---

## 🔗 **Integração com Eventos de Veículos**

### **Formato da Mensagem Enviada**
Quando um evento de veículo ocorre, o sistema envia automaticamente um embed para o Discord:

```json
{
  "embeds": [
    {
      "title": "💥 Kinglet_Duster_ES - Pedreiro (Destruído)",
      "description": "📍 **Localização:** X:-311773.969 Y:5480.525 Z:36099.227\n🆔 **VehicleId:** 1600655",
      "color": 16711680,
      "timestamp": "2025-07-13T06:43:27.511Z",
      "footer": {
        "text": "SCUM Server Manager - Eventos de Veículos"
      }
    }
  ]
}
```

### **Cores por Tipo de Evento**
- 🔴 **Vermelho (16711680)** - Veículos destruídos
- 🟠 **Laranja (16753920)** - Veículos desaparecidos  
- 🟡 **Amarelo (16776960)** - Timer de inatividade atingido
- ⚪ **Cinza (8421504)** - Outros eventos

---

## 📋 **Checklist de Implementação**

- [ ] Criar página de configurações de webhook
- [ ] Implementar formulário de cadastro
- [ ] Adicionar validação de URL do Discord
- [ ] Implementar consulta de status atual
- [ ] Adicionar funcionalidade de teste
- [ ] Implementar edição de webhook
- [ ] Adicionar remoção de webhook
- [ ] Implementar feedback visual
- [ ] Adicionar loading states
- [ ] Testar responsividade
- [ ] Validar integração completa 