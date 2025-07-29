# 📋 Cadastro de Webhook - Bunkers

## 🎯 Objetivo
Implementar no frontend a funcionalidade para cadastrar webhooks do Discord para notificações do sistema de Bunkers.

## 🔗 Endpoint
```
POST /api/webhook/bunkers
```

## 📝 Dados de Entrada

### Body (JSON)
```json
{
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

### Validações
- ✅ URL deve ser uma string válida
- ✅ URL deve começar com "https://"
- ✅ Campo `url` é obrigatório

## 📤 Respostas

### ✅ Sucesso (200)
```json
{
  "success": true,
  "message": "Webhook de Bunkers cadastrado com sucesso!"
}
```

### ⚠️ Sucesso com Aviso (200)
```json
{
  "success": true,
  "warning": "Webhook salvo, mas não foi possível enviar mensagem de teste. Verifique a URL."
}
```

### ❌ Erro de Validação (400)
```json
{
  "success": false,
  "error": "URL do webhook inválida"
}
```

### ❌ Erro do Servidor (500)
```json
{
  "success": false,
  "error": "Erro interno do servidor"
}
```

## 🎨 Implementação no Frontend

### 1. Componente de Formulário

```javascript
// components/WebhookBunkersForm.js
import React, { useState } from 'react';
import axios from 'axios';

const WebhookBunkersForm = () => {
  const [webhookUrl, setWebhookUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState(''); // 'success', 'warning', 'error'

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const response = await axios.post('/api/webhook/bunkers', {
        url: webhookUrl
      });

      if (response.data.success) {
        setMessageType('success');
        setMessage(response.data.message);
        
        if (response.data.warning) {
          setMessageType('warning');
          setMessage(response.data.warning);
        }
        
        setWebhookUrl(''); // Limpar campo após sucesso
      }
    } catch (error) {
      setMessageType('error');
      setMessage(error.response?.data?.error || 'Erro ao cadastrar webhook');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="webhook-form">
      <h3>🔗 Cadastrar Webhook - Bunkers</h3>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="webhookUrl">URL do Webhook Discord:</label>
          <input
            type="url"
            id="webhookUrl"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://discord.com/api/webhooks/..."
            required
            className="form-control"
          />
        </div>
        
        <button 
          type="submit" 
          disabled={loading || !webhookUrl}
          className="btn btn-primary"
        >
          {loading ? 'Cadastrando...' : 'Cadastrar Webhook'}
        </button>
      </form>

      {message && (
        <div className={`alert alert-${messageType === 'success' ? 'success' : messageType === 'warning' ? 'warning' : 'danger'}`}>
          {message}
        </div>
      )}
    </div>
  );
};

export default WebhookBunkersForm;
```

### 2. Estilos CSS

```css
/* styles/WebhookForm.css */
.webhook-form {
  max-width: 500px;
  margin: 20px auto;
  padding: 20px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  backdrop-filter: blur(10px);
}

.webhook-form h3 {
  color: #fff;
  margin-bottom: 20px;
  text-align: center;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: #fff;
  font-weight: bold;
}

.form-control {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.9);
  font-size: 14px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
  transition: all 0.3s ease;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-primary:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.alert {
  padding: 10px;
  margin-top: 15px;
  border-radius: 5px;
  font-weight: bold;
}

.alert-success {
  background: rgba(40, 167, 69, 0.2);
  color: #28a745;
  border: 1px solid #28a745;
}

.alert-warning {
  background: rgba(255, 193, 7, 0.2);
  color: #ffc107;
  border: 1px solid #ffc107;
}

.alert-danger {
  background: rgba(220, 53, 69, 0.2);
  color: #dc3545;
  border: 1px solid #dc3545;
}
```

### 3. Integração na Página

```javascript
// pages/Webhooks.js ou similar
import React from 'react';
import WebhookBunkersForm from '../components/WebhookBunkersForm';

const WebhooksPage = () => {
  return (
    <div className="webhooks-page">
      <h2>🔗 Configuração de Webhooks</h2>
      
      <div className="webhook-sections">
        <WebhookBunkersForm />
        
        {/* Outros formulários de webhook aqui */}
      </div>
    </div>
  );
};

export default WebhooksPage;
```

## 🧪 Teste com Postman

### Configuração:
- **Método:** POST
- **URL:** `http://localhost:3000/api/webhook/bunkers`
- **Headers:** `Content-Type: application/json`

### Body:
```json
{
  "url": "https://discord.com/api/webhooks/1394402625738375168/qX6bdSgfr7_Bwaaaw8gWwxcYV7BRSzVNFx9EV81Maf7rY9nHpC2p0rU6PL8be6QA3NQe"
}
```

## 📋 Checklist de Implementação

- [ ] Criar componente de formulário
- [ ] Implementar validação de URL
- [ ] Adicionar estados de loading e mensagens
- [ ] Implementar tratamento de erros
- [ ] Adicionar estilos CSS
- [ ] Integrar na página de configurações
- [ ] Testar com Postman
- [ ] Testar com URL válida do Discord
- [ ] Verificar mensagem de teste no Discord

## 🔧 Funcionalidades

### ✅ O que o endpoint faz:
1. **Valida** a URL do webhook
2. **Salva** no arquivo `src/data/webhooks.json`
3. **Envia** mensagem de teste para o Discord
4. **Retorna** confirmação do cadastro

### 📱 Notificações que serão enviadas:
- **Eventos de Bunkers** (quando implementado)
- **Mensagem de teste** após cadastro

## 🎨 Padrão Visual

Seguir o padrão transparente do projeto:
- Background: `rgba(255, 255, 255, 0.1)`
- Backdrop-filter: `blur(10px)`
- Bordas arredondadas: `10px`
- Cores consistentes com o tema

## 📞 Suporte

Em caso de dúvidas sobre a implementação, consulte:
- Documentação dos outros endpoints de webhook
- Padrões de UI/UX do projeto
- Console do navegador para debug 