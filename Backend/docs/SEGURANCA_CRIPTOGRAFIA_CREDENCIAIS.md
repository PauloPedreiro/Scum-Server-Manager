# 🔐 Segurança: Criptografia de Credenciais

## 📋 Visão Geral

Sistema de criptografia de credenciais usando chave derivada do hardware. Impede que credenciais sejam copiadas entre máquinas, mesmo que o `config.json` seja copiado.

---

## 🎯 Objetivo

**Proteger API Keys e credenciais sensíveis** mesmo que o arquivo `config.json` seja copiado para outra máquina.

**Como funciona:**
- Chave de criptografia é derivada do hardware da máquina
- Credenciais são criptografadas com essa chave
- Se o arquivo for copiado para outra máquina, não pode ser descriptografado
- Mesma proteção do hardware fingerprint

---

## 🔧 Como Funciona

### 1. Geração da Chave

```python
# Chave derivada do hardware usando PBKDF2
hash_value = hardware_fingerprint.generate()  # Hash do hardware
salt = SHA256(hash_value)[:16]  # Salt de 16 bytes
key = PBKDF2HMAC(SHA256, salt, hash_value, 100000 iterations)
```

**Características:**
- ✅ Usa PBKDF2 (mais seguro que hash direto)
- ✅ 100.000 iterações (resistente a brute force)
- ✅ Salt único por máquina
- ✅ Chave de 32 bytes (Fernet)

### 2. Criptografia

```python
from core.security.credential_encryption import encrypt_credential

# Criptografar
encrypted = encrypt_credential("minha-api-key")
# Retorna: "ENCRYPTED:gAAAAABh..."
```

### 3. Descriptografia

```python
from core.security.credential_encryption import decrypt_credential

# Descriptografar (automático no código)
decrypted = decrypt_credential("ENCRYPTED:gAAAAABh...")
# Retorna: "minha-api-key"
```

---

## 📝 Uso no Código

### Leitura Automática (Já Implementado)

O código já descriptografa automaticamente quando lê do `config.json`:

```python
# Em license_validator.py, main.py, gui/main_window.py, etc.
api_key = licensing_config.get('gestao_api_key')

# Descriptografa automaticamente se estiver criptografada
if api_key:
    from core.security.credential_encryption import decrypt_credential
    api_key = decrypt_credential(api_key, logger=logger)
```

**Compatibilidade:**
- ✅ Funciona com valores em texto plano (backward compatible)
- ✅ Funciona com valores criptografados
- ✅ Detecta automaticamente se está criptografado

---

## 🛠️ Como Criptografar Credenciais

### Opção 1: Script Automático (Recomendado)

```bash
python tools/encrypt_credentials.py
```

**O que faz:**
- ✅ Criptografa `gestao_api_key`
- ✅ Criptografa `steam.api_key`
- ✅ Criptografa `auth.jwt_secret`
- ✅ Cria backup do config.json
- ✅ Detecta se já está criptografado

**Exemplo de saída:**
```
🔐 Criptografando credenciais no config.json...
📁 Arquivo: data/config.json
  🔒 Criptografando gestao_api_key...
  ✅ gestao_api_key criptografada
  🔒 Criptografando steam.api_key...
  ✅ steam.api_key criptografada
  🔒 Criptografando auth.jwt_secret...
  ✅ auth.jwt_secret criptografado
  💾 Backup criado: data/config.json.backup

✅ Credenciais criptografadas com sucesso!
```

### Opção 2: Manual (Python)

```python
from core.security.credential_encryption import encrypt_credential
import json

# Carregar config
with open('data/config.json', 'r') as f:
    config = json.load(f)

# Criptografar API key
api_key = config['licensing']['gestao_api_key']
encrypted = encrypt_credential(api_key)
config['licensing']['gestao_api_key'] = encrypted

# Salvar
with open('data/config.json', 'w') as f:
    json.dump(config, f, indent=2)
```

---

## 📋 Formato no config.json

### Antes (Texto Plano)
```json
{
  "licensing": {
    "gestao_api_key": "ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10"
  }
}
```

### Depois (Criptografado)
```json
{
  "licensing": {
    "gestao_api_key": "ENCRYPTED:gAAAAABhZ3V0ZXJfY3J5cHRlZF9rZXlfZXhhbXBsZQ=="
  }
}
```

**Prefixo:** `ENCRYPTED:` identifica credenciais criptografadas

---

## ✅ Vantagens

1. **Segurança Máxima:**
   - ✅ Credenciais não podem ser copiadas entre máquinas
   - ✅ Mesma proteção do hardware fingerprint
   - ✅ Chave derivada do hardware (única por máquina)

2. **Transparente:**
   - ✅ Código descriptografa automaticamente
   - ✅ Compatível com valores em texto plano
   - ✅ Não requer mudanças no código de uso

3. **Fácil de Usar:**
   - ✅ Script automático para criptografar
   - ✅ Detecta se já está criptografado
   - ✅ Cria backup automaticamente

---

## ⚠️ Limitações e Considerações

### 1. Hardware Deve Ser Estável
- Se o hardware mudar significativamente, a chave muda
- Credenciais precisarão ser re-criptografadas
- Solução: Re-executar script de criptografia

### 2. Não Funciona Entre Máquinas
- Credenciais criptografadas só funcionam na máquina original
- Não pode copiar config.json para outra máquina
- **Isso é uma feature de segurança, não um bug!**

### 3. Backup Importante
- Sempre fazer backup antes de criptografar
- Script cria backup automaticamente
- Se perder a máquina, precisará re-configurar

---

## 🔄 Fluxo de Migração

### Para Usuários Existentes

1. **Fazer backup do config.json:**
   ```bash
   cp data/config.json data/config.json.backup
   ```

2. **Executar script de criptografia:**
   ```bash
   python tools/encrypt_credentials.py
   ```

3. **Verificar que funcionou:**
   - Verificar que API key ainda funciona
   - Verificar logs para erros
   - Testar validação de licença

### Para Novos Usuários

1. **Configurar API key normalmente** (texto plano)
2. **Executar script de criptografia:**
   ```bash
   python tools/encrypt_credentials.py
   ```
3. **Pronto!** Credenciais protegidas

---

## 🧪 Testes

### Testar Criptografia/Descriptografia

```python
from core.security.credential_encryption import encrypt_credential, decrypt_credential

# Testar
original = "minha-api-key-teste"
encrypted = encrypt_credential(original)
decrypted = decrypt_credential(encrypted)

assert original == decrypted
print("✅ Criptografia funcionando!")
```

### Testar no Sistema

1. Criptografar credenciais
2. Reiniciar backend
3. Verificar que validação funciona
4. Verificar logs (não deve ter erros)

---

## 📚 Dependências

### Biblioteca Necessária

```bash
pip install cryptography
```

**Versão mínima:** `cryptography >= 3.0.0`

**Verificar instalação:**
```python
try:
    from cryptography.fernet import Fernet
    print("✅ cryptography instalado")
except ImportError:
    print("❌ cryptography não instalado")
    print("Execute: pip install cryptography")
```

---

## 🔐 Segurança Adicional

### Recomendações

1. **Permissões do Arquivo:**
   ```bash
   chmod 600 data/config.json  # Apenas owner pode ler/escrever
   ```

2. **Backup Seguro:**
   - Fazer backup do config.json em local seguro
   - Não compartilhar backups
   - Criptografar backups também

3. **Rotação de Credenciais:**
   - Rotacionar API keys periodicamente
   - Re-criptografar após rotação
   - Invalidar keys antigas

---

## 🎯 Resumo

**Problema:** API keys expostas em texto plano no config.json podem ser copiadas entre máquinas.

**Solução:** Criptografia com chave derivada do hardware.

**Resultado:**
- ✅ API keys protegidas
- ✅ Não podem ser copiadas entre máquinas
- ✅ Transparente para o código
- ✅ Fácil de usar (script automático)

**Status:** ✅ **IMPLEMENTADO E PRONTO PARA USO**

