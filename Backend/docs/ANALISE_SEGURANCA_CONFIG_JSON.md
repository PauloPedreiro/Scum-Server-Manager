# 🔒 Análise de Segurança: config.json

## 📋 Resumo Executivo

**Status:** ⚠️ **MÚLTIPLAS BRECHAS DE SEGURANÇA CRÍTICAS ENCONTRADAS**

**Risco Geral:** 🔴 **ALTO** - Arquivo contém credenciais expostas e configurações inseguras

---

## 🔴 Brechas Críticas Encontradas

### 1. **API Keys Expostas em Texto Plano**

#### 1.1. Steam API Key (Linha 170)
```json
"steam": {
  "api_key": "32F6644A1EC92FD428179EE939147918"
}
```

**Risco:** 🔴 **CRÍTICO**
- API key do Steam exposta em texto plano
- Pode ser usada para fazer requisições à API do Steam
- Pode esgotar quota da API
- Pode ser usada em outras aplicações

**Impacto:**
- Uso não autorizado da API key
- Possível bloqueio da key por abuso
- Custos não autorizados (se houver)

**Recomendação:**
- ✅ Usar variáveis de ambiente: `STEAM_API_KEY`
- ✅ Criptografar no arquivo (com chave derivada do hardware)
- ✅ Armazenar em vault seguro (HashiCorp Vault, AWS Secrets Manager)

---

#### 1.2. Gestão API Key (Linha 250)
```json
"licensing": {
  "gestao_api_key": "ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10"
}
```

**Risco:** 🔴 **CRÍTICO**
- API key de gestão/licenciamento exposta
- Pode ser copiada junto com o arquivo (mesma brecha do hardware_fingerprint.json)
- Permite acesso não autorizado ao sistema de gestão
- Pode ser usada para validar licenças falsas

**Impacto:**
- Bypass do sistema de licenciamento
- Acesso não autorizado ao painel de gestão
- Validação de licenças falsas

**Recomendação:**
- ✅ Criptografar com chave derivada do hardware
- ✅ Usar variáveis de ambiente
- ✅ Armazenar em vault seguro
- ✅ Rotacionar periodicamente

---

### 2. **Credenciais de Autenticação Padrão e Fracas**

#### 2.1. JWT Secret Padrão (Linha 260)
```json
"auth": {
  "jwt_secret": "ssm-backend-secret-key-change-in-production"
}
```

**Risco:** 🔴 **CRÍTICO**
- Secret JWT padrão e conhecido
- Qualquer pessoa que tenha acesso ao código sabe o secret
- Permite forjar tokens JWT
- Permite acesso não autorizado à API

**Impacto:**
- Forjamento de tokens JWT
- Acesso não autorizado à API
- Bypass de autenticação

**Recomendação:**
- ✅ Gerar secret aleatório forte (mínimo 32 caracteres)
- ✅ Usar variáveis de ambiente
- ✅ Criptografar no arquivo
- ✅ Rotacionar periodicamente

---

#### 2.2. Credenciais Padrão do Admin (Linhas 262-263)
```json
"auth": {
  "default_username": "admin",
  "default_password": "12345678910"
}
```

**Risco:** 🔴 **CRÍTICO**
- Username padrão conhecido: `admin`
- Senha padrão muito fraca: `12345678910`
- Qualquer pessoa com acesso ao arquivo conhece as credenciais
- Permite acesso total ao sistema

**Impacto:**
- Acesso não autorizado ao painel administrativo
- Controle total do sistema
- Modificação de configurações
- Acesso a dados sensíveis

**Recomendação:**
- ✅ Remover credenciais padrão do arquivo
- ✅ Forçar alteração na primeira execução
- ✅ Usar senha forte gerada aleatoriamente
- ✅ Não armazenar senha em texto plano (apenas hash)

---

### 3. **Sistema de Licenciamento Desabilitado (Linha 239)**

```json
"licensing": {
  "enabled": false
}
```

**Risco:** 🟡 **MÉDIO**
- Sistema de licenciamento desabilitado
- Permite uso sem validação de licença
- Pode ser explorado para uso não autorizado

**Impacto:**
- Uso do sistema sem licença válida
- Bypass de validação de hardware

**Recomendação:**
- ✅ Habilitar em produção: `"enabled": true`
- ✅ Validar que não pode ser desabilitado facilmente
- ✅ Hardcoded no código (não permitir desabilitar via config)

---

### 4. **API Exposta em Todas as Interfaces (Linha 35)**

```json
"api": {
  "host": "0.0.0.0",
  "port": 3000
}
```

**Risco:** 🟡 **MÉDIO**
- API exposta em todas as interfaces de rede (`0.0.0.0`)
- Pode ser acessível de outras máquinas na rede
- Se não houver firewall adequado, pode ser acessível da internet

**Impacto:**
- Acesso não autorizado à API
- Ataques de força bruta
- Exploração de vulnerabilidades

**Recomendação:**
- ✅ Usar `127.0.0.1` ou `localhost` se não precisar acesso externo
- ✅ Implementar firewall adequado
- ✅ Usar HTTPS em produção
- ✅ Implementar rate limiting

---

### 5. **Auto-criação de Admin Habilitada (Linha 265)**

```json
"auth": {
  "auto_create_admin": true
}
```

**Risco:** 🟡 **MÉDIO**
- Criação automática de usuário admin
- Pode ser explorada para criar contas não autorizadas
- Se combinada com credenciais padrão, é muito perigoso

**Impacto:**
- Criação de contas admin não autorizadas
- Acesso não autorizado

**Recomendação:**
- ✅ Desabilitar após primeira execução
- ✅ Requer confirmação manual
- ✅ Registrar em log de auditoria

---

## 🟡 Brechas de Média Severidade

### 6. **Caminhos de Diretórios Expostos**

**Risco:** 🟡 **MÉDIO**
- Caminhos completos de diretórios expostos
- Pode facilitar ataques direcionados
- Revela estrutura do sistema

**Exemplos:**
```json
"scum_server": {
  "root_directory": "C:\\Servers\\Scum",
  "database": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
}
```

**Recomendação:**
- ✅ Usar caminhos relativos quando possível
- ✅ Validar permissões de acesso
- ✅ Não expor caminhos sensíveis

---

### 7. **Configurações de Comunicação com Valores Placeholder**

```json
"communication": {
  "api_key": "your-api-key-here",
  "webhook_url": "https://discord.com/api/webhooks/..."
}
```

**Risco:** 🟢 **BAIXO**
- Valores placeholder podem indicar configuração incompleta
- Não são credenciais reais, mas podem ser confundidos

**Recomendação:**
- ✅ Validar que não são valores padrão em produção
- ✅ Documentar claramente

---

## 📊 Resumo de Riscos

| Brecha | Severidade | Impacto | Prioridade |
|--------|-----------|---------|------------|
| Steam API Key exposta | 🔴 CRÍTICO | Alto | **P0** |
| Gestão API Key exposta | 🔴 CRÍTICO | Alto | **P0** |
| JWT Secret padrão | 🔴 CRÍTICO | Alto | **P0** |
| Credenciais admin padrão | 🔴 CRÍTICO | Alto | **P0** |
| Licenciamento desabilitado | 🟡 MÉDIO | Médio | **P1** |
| API em 0.0.0.0 | 🟡 MÉDIO | Médio | **P1** |
| Auto-criação de admin | 🟡 MÉDIO | Médio | **P2** |
| Caminhos expostos | 🟡 MÉDIO | Baixo | **P2** |

---

## ✅ Recomendações de Correção

### Prioridade P0 (Crítico - Corrigir Imediatamente)

1. **Criptografar API Keys:**
   ```python
   # Usar chave derivada do hardware
   from core.licensing.hardware_fingerprint import HardwareFingerprint
   hf = HardwareFingerprint()
   hardware_key = hf.generate()[0]  # Hash do hardware
   encrypted_api_key = encrypt(api_key, hardware_key)
   ```

2. **Remover Credenciais Padrão:**
   - Remover `default_username` e `default_password` do arquivo
   - Forçar criação na primeira execução
   - Gerar senha forte aleatória

3. **Gerar JWT Secret Forte:**
   ```python
   import secrets
   jwt_secret = secrets.token_urlsafe(32)  # 32 bytes = 43 caracteres
   ```

4. **Usar Variáveis de Ambiente:**
   ```python
   import os
   steam_api_key = os.getenv('STEAM_API_KEY')
   gestao_api_key = os.getenv('GESTAO_API_KEY')
   jwt_secret = os.getenv('JWT_SECRET')
   ```

### Prioridade P1 (Alto - Corrigir em Breve)

5. **Habilitar Licenciamento:**
   - `"enabled": true` em produção
   - Hardcoded no código (não permitir desabilitar)

6. **Restringir API:**
   - Usar `127.0.0.1` se não precisar acesso externo
   - Implementar firewall
   - Usar HTTPS

### Prioridade P2 (Médio - Melhorias)

7. **Desabilitar Auto-criação:**
   - `"auto_create_admin": false` após primeira execução
   - Requer confirmação manual

8. **Ocultar Caminhos:**
   - Usar caminhos relativos
   - Validar permissões

---

## 🔐 Solução Proposta: Criptografia de Credenciais

### Estratégia: Criptografia com Chave Derivada do Hardware

**Vantagens:**
- ✅ Credenciais não podem ser copiadas entre máquinas
- ✅ Mesma proteção do hardware fingerprint
- ✅ Transparente para o usuário
- ✅ Não requer vault externo

**Implementação:**
```python
from cryptography.fernet import Fernet
from core.licensing.hardware_fingerprint import HardwareFingerprint
import base64
import hashlib

def get_hardware_key():
    """Gera chave de criptografia baseada no hardware"""
    hf = HardwareFingerprint()
    hash_value, _ = hf.generate()
    # Usar hash como chave (32 bytes para Fernet)
    key = hashlib.sha256(hash_value.encode()).digest()
    return base64.urlsafe_b64encode(key)

def encrypt_credential(value: str) -> str:
    """Criptografa credencial usando chave do hardware"""
    key = get_hardware_key()
    f = Fernet(key)
    encrypted = f.encrypt(value.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_credential(encrypted_value: str) -> str:
    """Descriptografa credencial usando chave do hardware"""
    key = get_hardware_key()
    f = Fernet(key)
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
    decrypted = f.decrypt(encrypted_bytes)
    return decrypted.decode()
```

**Uso no config.json:**
```json
{
  "steam": {
    "api_key": "ENCRYPTED:gAAAAABh..."
  },
  "licensing": {
    "gestao_api_key": "ENCRYPTED:gAAAAABh..."
  },
  "auth": {
    "jwt_secret": "ENCRYPTED:gAAAAABh..."
  }
}
```

---

## 📝 Checklist de Segurança

- [ ] Remover todas as API keys do config.json
- [ ] Implementar criptografia de credenciais
- [ ] Remover credenciais padrão do admin
- [ ] Gerar JWT secret forte
- [ ] Habilitar licenciamento em produção
- [ ] Restringir API (127.0.0.1 ou firewall)
- [ ] Desabilitar auto-criação de admin
- [ ] Implementar validação de configuração
- [ ] Adicionar logs de auditoria
- [ ] Documentar procedimentos de segurança

---

## 🎯 Conclusão

O arquivo `config.json` contém **múltiplas brechas de segurança críticas** que precisam ser corrigidas imediatamente:

1. **4 brechas críticas** (P0) - API keys e credenciais expostas
2. **3 brechas médias** (P1-P2) - Configurações inseguras

**Ação Imediata Necessária:**
- Criptografar todas as credenciais
- Remover valores padrão
- Implementar proteções adicionais

**Status:** ⚠️ **REQUER CORREÇÃO URGENTE**

