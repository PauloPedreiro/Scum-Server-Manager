# 🔐 API de Recuperação de Senha - Documentação Frontend

**Versão:** 1.0  
**Data:** 2025-01-XX  
**Status:** ✅ Implementado

---

## 📋 Visão Geral

Sistema de recuperação de senha que permite ao usuário admin resetar sua senha quando esquecida. O processo utiliza tokens únicos enviados via **DM do Discord** (somente para admins ja vinculados) para garantir segurança.

---

## 🔄 Fluxo de Recuperação

```
1. Usuário solicita reset → POST /api/auth/request-password-reset
   ↓
2. Sistema gera token único (64 caracteres)
   ↓
3. Token é enviado via DM do Discord (para o `discord_user_id` vinculado)
   ↓
4. Usuário copia token da DM
   ↓
5. Usuário reseta senha → POST /api/auth/reset-password
   ↓
6. Senha é atualizada e usuário pode fazer login
```

---

## 📡 Endpoints

### **1. Solicitar Reset de Senha**

**Endpoint:** `POST /api/auth/request-password-reset`

**Descrição:** Solicita a geração de um token de recuperação de senha. O token sera enviado via **DM do Discord** para admins ja vinculados (`discord_user_id`).

**Autenticação:** ❌ Não requerida (endpoint público)

**Rate Limiting:**
- Máximo **3 tentativas por IP** a cada 15 minutos
- Máximo **1 tentativa por username** a cada 5 minutos

---

#### **Request**

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "username": "admin"
}
```

**Campos:**
- `username` (string, obrigatório): Nome de usuário para recuperação

---

#### **Response**

**Status Code:** `200 OK`

**Body (sempre retorna sucesso, mesmo se usuário não existir):**
```json
{
  "success": true,
  "message": "Se o usuário existir, um token de recuperação foi enviado via Discord"
}
```

**Nota:** A resposta é sempre genérica para não revelar se o usuário existe ou não (segurança contra enumeração de usuários).

**Observacao:** Se o usuario ainda nao estiver vinculado ao Discord, o token e gerado, mas nao ha como entregar via DM.

---

#### **Exemplo de Uso (JavaScript/TypeScript)**

```typescript
async function requestPasswordReset(username: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch('http://localhost:3000/api/auth/request-password-reset', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username }),
  });

  const data = await response.json();
  return data;
}

// Uso
try {
  const result = await requestPasswordReset('admin');
  if (result.success) {
    console.log('Token enviado via Discord. Verifique o canal log-ssm.');
  }
} catch (error) {
  console.error('Erro ao solicitar reset:', error);
}
```

---

#### **Notificação Discord**

Quando a solicitacao e bem-sucedida e o usuario esta vinculado, uma mensagem e enviada por DM com:

**Conteudo da DM:**
- Token completo (64 caracteres)
- Tempo de expiracao (15 minutos)

**Importante:** O token nao e publicado em canal/webhook.

---

### **2. Resetar Senha com Token**

**Endpoint:** `POST /api/auth/reset-password`

**Descrição:** Reseta a senha do usuário usando o token recebido via Discord.

**Autenticação:** ❌ Não requerida (endpoint público)

**Validações:**
- Token deve existir e não ter sido usado
- Token não pode estar expirado (expira em 15 minutos)
- Nova senha deve ter no mínimo 8 caracteres

---

#### **Request**

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "token": "f1f8dfce252b5c33a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f",
  "new_password": "NovaSenhaSegura123!"
}
```

**Campos:**
- `token` (string, obrigatório): Token de 64 caracteres recebido via Discord
- `new_password` (string, obrigatório): Nova senha (mínimo 8 caracteres)

---

#### **Response - Sucesso**

**Status Code:** `200 OK`

**Body:**
```json
{
  "success": true,
  "message": "Senha alterada com sucesso"
}
```

---

#### **Response - Token Inválido/Expirado**

**Status Code:** `400 Bad Request`

**Body:**
```json
{
  "success": false,
  "error": "Token inválido ou expirado"
}
```

**Causas possíveis:**
- Token não existe
- Token já foi usado
- Token expirou (15 minutos)
- Token com formato inválido

---

#### **Response - Senha Muito Curta**

**Status Code:** `400 Bad Request`

**Body:**
```json
{
  "success": false,
  "error": "Password must be at least 8 characters"
}
```

---

#### **Exemplo de Uso (JavaScript/TypeScript)**

```typescript
async function resetPassword(
  token: string,
  newPassword: string
): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await fetch('http://localhost:3000/api/auth/reset-password', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      token,
      new_password: newPassword,
    }),
  });

  const data = await response.json();
  return data;
}

// Uso
try {
  const token = 'f1f8dfce252b5c33...'; // Token copiado do Discord
  const newPassword = 'NovaSenhaSegura123!';
  
  const result = await resetPassword(token, newPassword);
  
  if (result.success) {
    console.log('Senha alterada com sucesso!');
    // Redirecionar para tela de login
  } else {
    console.error('Erro:', result.error);
    // Mostrar erro ao usuário
  }
} catch (error) {
  console.error('Erro ao resetar senha:', error);
}
```

---

#### **Notificação Discord**

Quando o reset é bem-sucedido, uma notificação é enviada para o webhook `log-ssm`:

**Embed Discord:**
- **Título:** ✅ Senha Resetada com Sucesso
- **Cor:** Verde (success)
- **Campos:**
  - 👤 Usuário: `admin`
  - ⏰ Data/Hora: `DD/MM/YYYY às HH:MM:SS`

---

## 🎨 Exemplo de Interface Frontend

### **Tela 1: Solicitar Reset**

```typescript
// Componente React/Next.js exemplo
function RequestPasswordReset() {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const result = await requestPasswordReset(username);
      setMessage('Se o usuário existir, um token foi enviado via Discord. Verifique o canal log-ssm.');
    } catch (error) {
      setMessage('Erro ao solicitar reset. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="Username"
        required
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Enviando...' : 'Solicitar Reset'}
      </button>
      {message && <p>{message}</p>}
    </form>
  );
}
```

---

### **Tela 2: Resetar Senha**

```typescript
// Componente React/Next.js exemplo
function ResetPassword() {
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    // Validações client-side
    if (newPassword.length < 8) {
      setError('A senha deve ter no mínimo 8 caracteres');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('As senhas não coincidem');
      return;
    }

    setLoading(true);

    try {
      const result = await resetPassword(token, newPassword);
      
      if (result.success) {
        setSuccess(true);
        // Redirecionar para login após 2 segundos
        setTimeout(() => {
          window.location.href = '/login';
        }, 2000);
      } else {
        setError(result.error || 'Erro ao resetar senha');
      }
    } catch (error) {
      setError('Erro ao resetar senha. Verifique o token e tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        placeholder="Token (copie do Discord)"
        required
      />
      <input
        type="password"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        placeholder="Nova senha (mín. 8 caracteres)"
        required
        minLength={8}
      />
      <input
        type="password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        placeholder="Confirmar nova senha"
        required
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Resetando...' : 'Resetar Senha'}
      </button>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {success && <p style={{ color: 'green' }}>Senha alterada com sucesso! Redirecionando...</p>}
    </form>
  );
}
```

---

## ⚠️ Tratamento de Erros

### **Erros Comuns**

1. **Token Inválido/Expirado**
   - **Causa:** Token não existe, já foi usado ou expirou
   - **Solução:** Solicitar novo token
   - **Mensagem:** "Token inválido ou expirado"

2. **Senha Muito Curta**
   - **Causa:** Nova senha tem menos de 8 caracteres
   - **Solução:** Informar senha com no mínimo 8 caracteres
   - **Mensagem:** "Password must be at least 8 characters"

3. **Rate Limit Excedido**
   - **Causa:** Muitas tentativas em pouco tempo
   - **Solução:** Aguardar 15 minutos (por IP) ou 5 minutos (por username)
   - **Mensagem:** Resposta genérica de sucesso (não revela rate limit)

4. **Erro de Rede**
   - **Causa:** Problema de conexão com o servidor
   - **Solução:** Verificar conexão e tentar novamente
   - **Tratamento:** Capturar exceção e mostrar mensagem amigável

---

## 🔒 Segurança

### **Proteções Implementadas**

1. **Rate Limiting:**
   - Previne abuso de solicitações
   - Limita tentativas por IP e por username

2. **Token Único:**
   - 64 caracteres hexadecimais (256 bits de entropia)
   - Gerado com `secrets.token_hex(32)`

3. **Expiração Curta:**
   - Tokens expiram em 15 minutos
   - Reduz janela de ataque

4. **Uso Único:**
   - Tokens são invalidados após uso
   - Previne reutilização

5. **Resposta Genérica:**
   - Não revela se usuário existe
   - Previne enumeração de usuários

6. **Validação de Senha:**
   - Mínimo 8 caracteres
   - Hash com bcrypt antes de armazenar

---

## 📝 Notas Importantes

1. **Acesso ao Discord:**
   - O usuário **deve ter acesso** ao canal Discord onde o webhook `log-ssm` está configurado
   - Sem acesso ao Discord, não será possível ver o token

2. **Tempo de Expiração:**
   - Tokens expiram em **15 minutos**
   - Após expiração, é necessário solicitar novo token

3. **Uso do Token:**
   - Cada token pode ser usado **apenas uma vez**
   - Após uso bem-sucedido, o token é invalidado

4. **Validação de Senha:**
   - Mínimo **8 caracteres**
   - Recomenda-se validar no frontend antes de enviar

5. **Rate Limiting:**
   - Resposta sempre genérica (não revela se rate limit foi atingido)
   - Usuário deve aguardar antes de tentar novamente

---

## 🧪 Testes

### **Cenário 1: Fluxo Completo**

```bash
# 1. Solicitar reset
curl -X POST http://localhost:3000/api/auth/request-password-reset \
  -H "Content-Type: application/json" \
  -d '{"username": "admin"}'

# 2. Copiar token do Discord (webhook log-ssm)

# 3. Resetar senha
curl -X POST http://localhost:3000/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "TOKEN_COPIADO_DO_DISCORD",
    "new_password": "NovaSenha123!"
  }'
```

### **Cenário 2: Token Inválido**

```bash
curl -X POST http://localhost:3000/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "token_invalido",
    "new_password": "NovaSenha123!"
  }'
```

**Resposta esperada:**
```json
{
  "success": false,
  "error": "Token inválido ou expirado"
}
```

### **Cenário 3: Senha Muito Curta**

```bash
curl -X POST http://localhost:3000/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "TOKEN_VALIDO",
    "new_password": "123"
  }'
```

**Resposta esperada:**
```json
{
  "success": false,
  "error": "Password must be at least 8 characters"
}
```

---

## 📚 Referências

- **Base URL:** `http://localhost:3000` (ou URL do servidor em produção)
- **Webhook Discord:** Configurado em `data/webhooks.json` → `log-ssm`
- **Documentação Completa:** Ver `docs/PLANEJAMENTO_RECUPERACAO_SENHA.md`

---

## ✅ Checklist de Implementação Frontend

- [ ] Criar tela de "Esqueci minha senha"
- [ ] Criar formulário para solicitar reset (campo username)
- [ ] Criar tela de reset de senha (campos: token, nova senha, confirmar senha)
- [ ] Implementar validação client-side (senha mínima 8 caracteres)
- [ ] Implementar tratamento de erros
- [ ] Mostrar mensagens de sucesso/erro ao usuário
- [ ] Redirecionar para login após reset bem-sucedido
- [ ] Adicionar instruções sobre onde encontrar o token (Discord)
- [ ] Implementar feedback visual durante requisições (loading)
- [ ] Testar fluxo completo

---

## 🆘 Suporte

Em caso de dúvidas ou problemas:
1. Verificar logs do backend para erros
2. Confirmar que webhook `log-ssm` está configurado
3. Verificar se `auth.enabled` está `true` no `config.json`
4. Testar endpoints diretamente via Postman/curl

---

**Última atualização:** 2025-01-XX

