# 📋 Endpoints do Webhook Funny Statistics

## 🎯 Visão Geral

Este documento descreve os endpoints para gerenciar o webhook das **Estatísticas Divertidas** do servidor SCUM. O sistema envia estatísticas engraçadas dos jogadores diretamente para o Discord através deste webhook.

---

## 🔗 Endpoints Disponíveis

### **Base URL:** `http://localhost:3000/api/webhook/funny-statistic`

---

## 📤 **GET** `/api/webhook/funny-statistic`

### **Descrição**
Consulta o webhook atual das estatísticas divertidas.

### **Headers**
```
Content-Type: application/json
```

### **Resposta de Sucesso (Webhook Cadastrado)**
```json
{
  "success": true,
  "message": "Webhook recuperado com sucesso.",
  "url": "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
}
```

### **Resposta de Sucesso (Sem Webhook)**
```json
{
  "success": false,
  "message": "Nenhum webhook cadastrado para funny-statistic.",
  "url": null
}
```

### **Status Codes**
- `200` - Sucesso (com ou sem webhook)

---

## 📥 **POST** `/api/webhook/funny-statistic`

### **Descrição**
Cadastra ou atualiza o webhook das estatísticas divertidas.

### **Headers**
```
Content-Type: application/json
```

### **Body (JSON)**
```json
{
  "url": "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
}
```

### **Validações**
- URL deve ser uma string válida
- URL deve começar com `https://`
- URL deve ser um webhook do Discord válido

### **Resposta de Sucesso**
```json
{
  "success": true,
  "message": "Webhook do funny-statistic cadastrado/atualizado com sucesso.",
  "url": "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
}
```

### **Resposta de Erro (URL Inválida)**
```json
{
  "success": false,
  "message": "URL do webhook inválida."
}
```

### **Resposta com Aviso (Teste Falhou)**
```json
{
  "success": true,
  "warning": "Webhook salvo, mas não foi possível enviar mensagem de teste. Verifique a URL."
}
```

### **Status Codes**
- `200` - Sucesso (com ou sem aviso)
- `400` - URL inválida

---

## 🧪 Casos de Teste

### **1. Consultar Webhook Existente**
```bash
curl -X GET http://localhost:3000/api/webhook/funny-statistic
```

### **2. Cadastrar Webhook Válido**
```bash
curl -X POST http://localhost:3000/api/webhook/funny-statistic \
  -H "Content-Type: application/json" \
  -d '{"url": "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"}'
```

### **3. Testar URL Inválida**
```bash
curl -X POST http://localhost:3000/api/webhook/funny-statistic \
  -H "Content-Type: application/json" \
  -d '{"url": "http://invalid-url.com"}'
```

---

## 🎨 Implementação Frontend

### **Exemplo de Interface Sugerida**

```javascript
// Componente React/Vue/Angular
const FunnyStatisticsWebhook = () => {
  const [webhookUrl, setWebhookUrl] = useState('');
  const [currentWebhook, setCurrentWebhook] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Buscar webhook atual
  const fetchCurrentWebhook = async () => {
    try {
      const response = await fetch('/api/webhook/funny-statistic');
      const data = await response.json();
      
      if (data.success && data.url) {
        setCurrentWebhook(data.url);
        setWebhookUrl(data.url);
      }
    } catch (error) {
      console.error('Erro ao buscar webhook:', error);
    }
  };

  // Salvar webhook
  const saveWebhook = async () => {
    setLoading(true);
    setMessage('');
    
    try {
      const response = await fetch('/api/webhook/funny-statistic', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: webhookUrl }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMessage(data.message);
        setCurrentWebhook(webhookUrl);
        
        if (data.warning) {
          setMessage(data.message + ' - ' + data.warning);
        }
      } else {
        setMessage(data.message);
      }
    } catch (error) {
      setMessage('Erro ao salvar webhook');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="webhook-config">
      <h2>🎭 Webhook das Estatísticas Divertidas</h2>
      
      <div className="form-group">
        <label>URL do Webhook Discord:</label>
        <input
          type="url"
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
          placeholder="https://discord.com/api/webhooks/..."
          className="form-control"
        />
      </div>
      
      <button 
        onClick={saveWebhook} 
        disabled={loading || !webhookUrl}
        className="btn btn-primary"
      >
        {loading ? 'Salvando...' : 'Salvar Webhook'}
      </button>
      
      {message && (
        <div className={`alert ${message.includes('sucesso') ? 'alert-success' : 'alert-danger'}`}>
          {message}
        </div>
      )}
      
      {currentWebhook && (
        <div className="current-webhook">
          <strong>Webhook Atual:</strong> {currentWebhook}
        </div>
      )}
    </div>
  );
};
```

---

## 🔧 Funcionalidades Especiais

### **Mensagem de Teste Automática**
- Ao cadastrar um webhook válido, o sistema envia automaticamente uma mensagem de teste
- A mensagem contém um embed com título "🎭 Webhook de Estatísticas Divertidas cadastrado com sucesso!"
- Se o teste falhar, retorna um aviso mas ainda salva o webhook

### **Validação Robusta**
- Verifica se a URL é uma string válida
- Confirma se começa com `https://`
- Aceita apenas URLs de webhook do Discord

### **Persistência**
- Salva no arquivo `src/data/webhooks.json`
- Chave: `"funny-statistic"`
- Mantém formato JSON existente

---

## 📊 Integração com o Sistema

### **Uso Automático**
O webhook cadastrado é usado automaticamente pelo sistema de Funny Statistics:

1. **Leitura:** `src/funny_statistics.js` lê a chave `"funny-statistic"`
2. **Envio:** Mensagens diárias e relatório de domingo são enviados para este webhook
3. **Configuração:** A chave está definida em `config.json` como `"webhook_key": "funny-statistic"`

### **Horários de Envio**
- **Diário:** 12:00 e 22:00 (horário de Brasília)
- **Domingo:** 14:00 (relatório especial semanal)

---

## 🚨 Tratamento de Erros

### **Erros Comuns**
1. **URL inválida:** Retorna 400 com mensagem específica
2. **Teste falhou:** Retorna 200 com aviso
3. **Servidor offline:** Timeout ou erro de conexão
4. **Webhook não encontrado:** Retorna null no GET

### **Boas Práticas**
- Sempre validar a URL antes de enviar
- Mostrar feedback visual para o usuário
- Implementar retry em caso de falha
- Armazenar webhook localmente para cache

---

## 📝 Notas Importantes

1. **URL do Discord:** Deve ser um webhook válido do Discord
2. **HTTPS Obrigatório:** Apenas URLs HTTPS são aceitas
3. **Teste Automático:** Sistema envia mensagem de teste ao cadastrar
4. **Persistência:** Webhook é salvo permanentemente no arquivo JSON
5. **Integração:** Usado automaticamente pelo sistema de estatísticas

---

## 🎯 Checklist de Implementação

- [ ] Interface para exibir webhook atual
- [ ] Campo de input para nova URL
- [ ] Validação de URL no frontend
- [ ] Botão para salvar webhook
- [ ] Feedback visual de sucesso/erro
- [ ] Loading state durante operações
- [ ] Tratamento de erros de rede
- [ ] Teste de conectividade
- [ ] Cache local do webhook atual

---

**Desenvolvedor Frontend:** Use este documento como referência completa para implementar a interface de gerenciamento do webhook das Estatísticas Divertidas! 🚀 