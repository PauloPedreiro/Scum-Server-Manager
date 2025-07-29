# Implementação Webhook Famepoints - Frontend

## 🎯 O que foi implementado

O endpoint `/api/famepoints` agora envia automaticamente uma notificação para o Discord sempre que for acessado.

## 📝 Como implementar no frontend

### **1. Acessar Famepoints (Webhook automático)**
```javascript
const obterFamepoints = async () => {
  try {
    const response = await fetch('/api/famepoints');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Erro:', error);
  }
};
```

### **2. Configurar Webhook (Opcional)**
```javascript
const configurarWebhook = async (webhookUrl) => {
  try {
    const response = await fetch('/api/webhook/famepoints', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: webhookUrl })
    });
    return await response.json();
  } catch (error) {
    console.error('Erro:', error);
  }
};
```

### **3. Consultar Webhook Atual**
```javascript
const consultarWebhook = async () => {
  try {
    const response = await fetch('/api/webhook/famepoints');
    return await response.json();
  } catch (error) {
    console.error('Erro:', error);
  }
};
```

## 🎨 Interface HTML

### **Tela de Famepoints:**
```html
<div class="famepoints">
  <h3>Fame Points</h3>
  <button onclick="obterFamepoints()">Atualizar</button>
  
  <div id="famepoints-list">
    <!-- Dados serão carregados aqui -->
  </div>
  
  <small>ℹ️ Webhook enviado automaticamente para Discord</small>
</div>
```

### **Tela de Configuração (Opcional):**
```html
<div class="webhook-config">
  <h3>Configurar Webhook</h3>
  
  <input type="text" id="webhookUrl" placeholder="URL do webhook Discord" />
  <button onclick="salvarWebhook()">Salvar</button>
  
  <button onclick="verificarWebhook()">Verificar Atual</button>
  <div id="webhook-status"></div>
</div>
```

## 🔧 Funções JavaScript

```javascript
// Carregar famepoints
async function obterFamepoints() {
  const data = await fetch('/api/famepoints').then(r => r.json());
  
  // Exibir dados
  const container = document.getElementById('famepoints-list');
  container.innerHTML = data.data.map(player => `
    <div class="player">
      <strong>${player.playerName}</strong>
      <span>Steam ID: ${player.steamId}</span>
      <span>Fame: ${player.totalFame}</span>
    </div>
  `).join('');
}

// Configurar webhook
async function salvarWebhook() {
  const url = document.getElementById('webhookUrl').value;
  const result = await configurarWebhook(url);
  alert(result.success ? 'Webhook salvo!' : 'Erro ao salvar');
}

// Verificar webhook atual
async function verificarWebhook() {
  const result = await consultarWebhook();
  const status = document.getElementById('webhook-status');
  status.innerHTML = result.success ? 
    `Webhook configurado: ${result.url}` : 
    'Nenhum webhook configurado';
}
```

## ⚠️ Importante

- **Webhook automático**: Funciona sem configuração adicional
- **Se não configurar**: Sistema funciona normalmente, só não envia para Discord
- **Configuração**: Pode ser feita via API ou diretamente no arquivo `src/data/webhooks.json`

## 🧪 Teste

```javascript
// Teste completo
async function testar() {
  // 1. Configurar webhook
  await configurarWebhook('https://discord.com/api/webhooks/SEU_WEBHOOK');
  
  // 2. Acessar famepoints (envia webhook automaticamente)
  await obterFamepoints();
  
  // 3. Verificar no Discord se chegou a notificação
}
``` 