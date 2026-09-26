# 📋 Planejamento - Webhook de Login/Logout no Discord

**Data:** 2025-12-05  
**Status:** 📝 Planejamento

---

## 🎯 Objetivo

Implementar notificações via webhook do Discord quando usuários fizerem login ou logout no sistema de autenticação do frontend.

---

## 📊 Análise do Sistema Atual

### **Componentes Disponíveis:**

1. **DiscordWebhook** (`core/webhooks/discord_webhook.py`)
   - Classe já implementada e funcional
   - Método `send_webhook()` disponível
   - Rate limiting implementado
   - Retry automático implementado

2. **Webhook Configurado:**
   - Nome: `"log-ssm"`
   - URL: Já configurada em `data/webhooks.json`
   - Status: ✅ Pronto para uso

3. **Endpoints de Autenticação:**
   - `POST /api/auth/login` - Endpoint de login
   - `POST /api/auth/logout` - Endpoint de logout
   - Ambos já implementados e funcionando

---

## 🔧 Implementação Proposta

### **1. Onde Implementar**

#### **Login (`POST /api/auth/login`)**
- **Local:** `main.py` - Função `login()`
- **Momento:** Após login bem-sucedido (antes de retornar resposta)
- **Condição:** Apenas se login for bem-sucedido e não for primeiro login (senha não mudada)
- **Nota:** Não incluir IP address por questões de privacidade

#### **Logout (`POST /api/auth/logout`)**
- **Local:** `main.py` - Função `logout()`
- **Momento:** Após validação do token (antes de retornar resposta)
- **Condição:** Sempre que logout for chamado com token válido

---

### **2. Dados a Incluir na Notificação**

#### **Login:**
- ✅ Username
- ✅ Role (admin/moderator)
- ✅ Timestamp
- ✅ Player vinculado (se houver steam_id)

#### **Logout:**
- ✅ Username
- ✅ Role (admin/moderator)
- ✅ Timestamp
- ✅ Duração da sessão (se possível calcular)

---

### **3. Formato das Notificações**

#### **Login:**
```json
{
  "embeds": [{
    "title": "🔐 Login Realizado",
    "description": "Um usuário fez login no sistema",
    "color": 0x00ff00,  // Verde
    "fields": [
      {
        "name": "Usuário",
        "value": "admin",
        "inline": true
      },
      {
        "name": "Role",
        "value": "admin",
        "inline": true
      },
      {
        "name": "Player Vinculado",
        "value": "PlayerName (76561198012345678)",
        "inline": false
      },
      {
        "name": "Timestamp",
        "value": "05/12/2025 às 14:30:00",
        "inline": false
      }
    ],
    "timestamp": "2025-12-05T14:30:00",
    "footer": {
      "text": "SSM Backend - Sistema de Autenticação"
    }
  }]
}
```

#### **Logout:**
```json
{
  "embeds": [{
    "title": "🚪 Logout Realizado",
    "description": "Um usuário fez logout do sistema",
    "color": 0xffaa00,  // Laranja
    "fields": [
      {
        "name": "Usuário",
        "value": "admin",
        "inline": true
      },
      {
        "name": "Role",
        "value": "admin",
        "inline": true
      },
      {
        "name": "Timestamp",
        "value": "05/12/2025 às 15:45:00",
        "inline": false
      }
    ],
    "timestamp": "2025-12-05T15:45:00",
    "footer": {
      "text": "SSM Backend - Sistema de Autenticação"
    }
  }]
}
```

---

### **4. Método de Implementação**

#### **Opção 1: Método Genérico (Recomendado)**
Criar um método específico em `DiscordWebhook` para notificações de autenticação:

```python
def send_auth_notification(self, event_type: str, user_data: Dict[str, Any]) -> bool:
    """
    Enviar notificação de autenticação (login/logout)
    
    Args:
        event_type: 'login' ou 'logout'
        user_data: Dados do usuário (username, role, steam_id, etc.)
    """
```

**Vantagens:**
- Código organizado e reutilizável
- Fácil manutenção
- Consistente com outros métodos do DiscordWebhook

#### **Opção 2: Inline nos Endpoints**
Adicionar código diretamente nos endpoints de login/logout.

**Desvantagens:**
- Código duplicado
- Mais difícil de manter
- Menos organizado

**Decisão:** ✅ **Opção 1** (Método Genérico)

---

### **5. Tratamento de Erros**

- ✅ Não bloquear o login/logout se o webhook falhar
- ✅ Logar erros mas continuar o fluxo normal
- ✅ Usar try/except para capturar exceções
- ✅ Não expor erros de webhook ao frontend

---

### **6. Informações Adicionais**

#### **Duração da Sessão (Logout):**
- Calcular baseado no `iat` (issued at) do token JWT
- Opcional: pode ser omitido se muito complexo

#### **Player Vinculado:**
- Buscar dados do player se `steam_id` estiver presente
- Mostrar nome do player e steam_id

---

## 📝 Checklist de Implementação

### **Fase 1: Método no DiscordWebhook**
- [ ] Criar método `send_auth_notification()` em `DiscordWebhook`
- [ ] Implementar formatação de embed para login
- [ ] Implementar formatação de embed para logout
- [ ] Adicionar tratamento de erros
- [ ] Testar método isoladamente

### **Fase 2: Integração no Login**
- [ ] Adicionar chamada ao webhook no endpoint de login
- [ ] Obter dados do player (se steam_id presente)
- [ ] Testar login e verificar notificação

### **Fase 3: Integração no Logout**
- [ ] Adicionar chamada ao webhook no endpoint de logout
- [ ] Obter dados do usuário do token
- [ ] Testar logout e verificar notificação

### **Fase 4: Testes e Validação**
- [ ] Testar login com usuário admin
- [ ] Testar login com usuário moderator
- [ ] Testar login com player vinculado
- [ ] Testar login sem player vinculado
- [ ] Testar logout
- [ ] Verificar que erros de webhook não bloqueiam login/logout
- [ ] Verificar formato das mensagens no Discord

---

## 🎨 Exemplo Visual das Notificações

### **Login:**
```
┌─────────────────────────────────────────┐
│ 🔐 Login Realizado                      │
├─────────────────────────────────────────┤
│ Um usuário fez login no sistema         │
│                                         │
│ Usuário: admin                          │
│ Role: admin                            │
│                                         │
│ Player Vinculado:                       │
│ PlayerName (76561198012345678)          │
│                                         │
│ Timestamp: 05/12/2025 às 14:30:00      │
└─────────────────────────────────────────┘
```

### **Logout:**
```
┌─────────────────────────────────────────┐
│ 🚪 Logout Realizado                     │
├─────────────────────────────────────────┤
│ Um usuário fez logout do sistema       │
│                                         │
│ Usuário: admin                          │
│ Role: admin                            │
│                                         │
│ Timestamp: 05/12/2025 às 15:45:00      │
└─────────────────────────────────────────┘
```

---

## ⚠️ Considerações Importantes

### **Segurança:**
- ✅ Não expor informações sensíveis (senhas, tokens)
- ✅ Não incluir IP address por questões de privacidade
- ✅ Logs devem ser mantidos apenas no Discord (não no banco)

### **Performance:**
- ✅ Webhook não deve bloquear login/logout
- ✅ Usar execução assíncrona ou não-bloqueante
- ✅ Rate limiting já implementado no DiscordWebhook

### **Privacidade:**
- ✅ IP address não será incluído (decisão tomada)
- ✅ Player vinculado será mostrado apenas se existir
- ✅ Informações mínimas necessárias para auditoria

---

## 🔄 Fluxo de Execução

### **Login:**
```
1. Usuário faz POST /api/auth/login
2. Backend valida credenciais
3. Se válido:
   a. Gera token JWT
   b. Atualiza last_login no banco
   c. Envia webhook para Discord (não-bloqueante)
   d. Retorna token para frontend
4. Se inválido:
   a. Retorna erro (sem webhook)
```

### **Logout:**
```
1. Usuário faz POST /api/auth/logout
2. Backend valida token
3. Se válido:
   a. Envia webhook para Discord (não-bloqueante)
   b. Retorna sucesso
4. Se inválido:
   a. Retorna erro (sem webhook)
```

---

## 📚 Referências

- **Webhook Config:** `data/webhooks.json`
- **DiscordWebhook Class:** `core/webhooks/discord_webhook.py`
- **Login Endpoint:** `main.py` - Função `login()`
- **Logout Endpoint:** `main.py` - Função `logout()`
- **Documentação Discord Embeds:** https://discord.com/developers/docs/resources/channel#embed-object

---

## ✅ Aprovação

- [ ] Plano revisado
- [ ] Aprovado para implementação
- [ ] Pronto para começar

---

**Versão:** 1.0  
**Última Atualização:** 2025-12-05

