# 🔌 Planejamento: Cliente de Licenciamento (SSM Backend)

## 📋 Objetivo

Criar cliente HTTP no SSM Backend para consumir endpoints do servidor de gerenciamento de licenças. O SSM **NÃO cria endpoints próprios**, apenas consome os endpoints fornecidos pelo servidor.

---

## 🎯 Responsabilidades do Cliente

### ✅ O que o SSM faz:

1. **Coleta Hardware**
   - Coleta MACs e outros componentes
   - Gera hash único
   - Armazena localmente

2. **Validação Periódica**
   - A cada 4 horas, chama endpoint do servidor
   - Envia: `license_key` + `hardware_fingerprint` + `timestamp`
   - Recebe: `valid/invalid` + dados da licença

3. **Registro Inicial**
   - Primeira vez: chama endpoint de registro
   - Envia: dados do usuário + `hardware_fingerprint`
   - Recebe: confirmação de registro

4. **Revalidação (Hardware Mudou)**
   - Solicita código: chama endpoint com email + old_fingerprint
   - Revalida: chama endpoint com código + new_fingerprint

5. **Bloqueio de Funcionalidades**
   - Se servidor retornar `invalid`, bloqueia funcionalidades
   - Mostra mensagem ao usuário

### ❌ O que o SSM NÃO faz:

- ❌ Criar endpoints próprios de licenciamento
- ❌ Gerenciar licenças localmente
- ❌ Validar licenças sem consultar servidor
- ❌ Decidir regras de negócio de licenças

---

## 🏗️ Estrutura do Cliente

### Módulo: `core/licensing/license_client.py`

```python
class LicenseClient:
    """
    Cliente HTTP para servidor de licenciamento.
    Consome endpoints fornecidos pelo servidor.
    """
    
    def __init__(self, server_url: str, config: Dict):
        self.server_url = server_url
        self.config = config
        self.session = requests.Session()
    
    def register(self, user_data: Dict, hardware_fingerprint: str) -> Dict:
        """
        Registra usuário e hardware no servidor.
        
        Endpoint: POST {server_url}/api/v1/register
        """
        pass
    
    def validate(self, license_key: str, hardware_fingerprint: str) -> Dict:
        """
        Valida licença com servidor.
        
        Endpoint: POST {server_url}/api/v1/validate
        """
        pass
    
    def request_revalidation_code(self, email: str, old_fingerprint: str) -> Dict:
        """
        Solicita código de revalidação.
        
        Endpoint: POST {server_url}/api/v1/revalidate/request-code
        """
        pass
    
    def revalidate(self, email: str, old_fingerprint: str, 
                   new_fingerprint: str, code: str) -> Dict:
        """
        Revalida hardware com código.
        
        Endpoint: POST {server_url}/api/v1/revalidate
        """
        pass
```

---

## 🔄 Fluxo de Uso

### 1. Registro Inicial

```
Usuário abre aplicação pela primeira vez
   ↓
SSM coleta hardware → gera hash
   ↓
SSM mostra tela de registro
   ↓
Usuário preenche: nome, email, etc
   ↓
SSM → POST /api/v1/register
   {
     "full_name": "...",
     "email": "...",
     "hardware_fingerprint": "abc123...",
     "license_key": "SSM-XXXX-XXXX-XXXX"  // opcional
   }
   ↓
Servidor retorna: { "success": true, "user_id": 1 }
   ↓
SSM salva: user_id, hardware_fingerprint, license_key
   ↓
Pronto para usar
```

### 2. Validação Periódica (A cada 4h)

```
Timer dispara (4h desde última validação)
   ↓
SSM coleta hardware atual → gera hash
   ↓
Compara com hash armazenado
   ↓
Se igual:
   SSM → POST /api/v1/validate
   {
     "license_key": "SSM-XXXX-XXXX-XXXX",
     "hardware_fingerprint": "abc123...",
     "timestamp": "2025-01-15T10:00:00Z",
     "backend_id": "SCUM-BACKEND-ABC123"
   }
   ↓
Servidor retorna:
   {
     "valid": true,
     "expires_at": "2025-02-15T00:00:00Z",
     "next_check_at": "2025-01-15T14:00:00Z"
   }
   ↓
SSM salva resultado em cache
   ↓
Continua funcionando normalmente
```

### 3. Hardware Mudou

```
SSM detecta hash diferente
   ↓
SSM bloqueia funcionalidades
   ↓
SSM mostra tela de revalidação
   ↓
Usuário informa email
   ↓
SSM → POST /api/v1/revalidate/request-code
   {
     "email": "joao@email.com",
     "old_fingerprint": "abc123..."
   }
   ↓
Servidor envia código por email
   ↓
Usuário recebe código e informa na aplicação
   ↓
SSM → POST /api/v1/revalidate
   {
     "email": "joao@email.com",
     "old_fingerprint": "abc123...",
     "new_fingerprint": "def456...",
     "verification_code": "123456"
   }
   ↓
Servidor retorna: { "success": true }
   ↓
SSM atualiza hardware_fingerprint local
   ↓
SSM desbloqueia funcionalidades
```

---

## 💾 Armazenamento Local (SSM)

### Arquivo: `data/license.json`

```json
{
  "license_key": "SSM-XXXX-XXXX-XXXX",
  "hardware_fingerprint": "a1b2c3d4e5f6...",
  "user_email": "joao@email.com",
  "registered_at": "2025-01-15T00:00:00Z",
  "last_validation": {
    "timestamp": "2025-01-15T10:00:00Z",
    "valid": true,
    "expires_at": "2025-02-15T00:00:00Z",
    "next_check_at": "2025-01-15T14:00:00Z"
  },
  "server_url": "https://api.ssm-backend.com/v1"
}
```

### Tabela no Banco: `license_validations` (SSM.db)

```sql
CREATE TABLE IF NOT EXISTS license_validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_key TEXT NOT NULL,
    hardware_fingerprint TEXT NOT NULL,
    validated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    valid BOOLEAN NOT NULL,
    expires_at DATETIME,
    next_check_at DATETIME,
    server_response TEXT,  -- JSON da resposta do servidor
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_license_validated_at 
ON license_validations(validated_at);
```

---

## 🔧 Configuração

### Adicionar ao `config.json`

```json
{
  "licensing": {
    "enabled": true,
    "server_url": "https://api.ssm-backend.com/v1",
    "validation_interval_seconds": 14400,  // 4 horas
    "hardware_check_interval_seconds": 3600,  // Verificar hardware a cada 1h
    "cache_ttl_seconds": 14400,  // Cache válido por 4h
    "require_internet": true,
    "block_on_invalid": true,
    "timeout_seconds": 10,
    "retry_attempts": 3,
    "retry_delay_seconds": 30
  }
}
```

---

## 🛡️ Tratamento de Erros

### Cenários

1. **Servidor inacessível**
   - Tentar novamente em 30 minutos
   - Usar cache local se válido (< 4h)
   - Bloquear após 4h sem validação

2. **Licença inválida**
   - Bloquear funcionalidades imediatamente
   - Mostrar mensagem ao usuário
   - Tentar validar novamente em 30 minutos

3. **Hardware mudou**
   - Bloquear funcionalidades
   - Mostrar tela de revalidação
   - Manter hash antigo para revalidação

4. **Timeout na requisição**
   - Retry automático (3 tentativas)
   - Se falhar todas, usar cache se válido
   - Bloquear se cache expirado

---

## 📊 Integração com Código Existente

### Atualizar `LicenseValidator` existente

O `core/communication/license_validator.py` já existe. Vamos atualizá-lo para:

1. Usar `HardwareFingerprint` para obter hash
2. Usar `LicenseClient` para chamar servidor
3. Manter lógica de validação periódica
4. Integrar com bloqueio de funcionalidades

### Fluxo de Validação

```python
# No LicenseValidator
def validate_license(self):
    # 1. Obter hardware fingerprint
    fingerprint = hardware_fingerprint.get_fingerprint()
    
    # 2. Verificar se mudou
    if fingerprint != stored_fingerprint:
        # Hardware mudou - requer revalidação
        return self._handle_hardware_change()
    
    # 3. Chamar servidor
    result = license_client.validate(
        license_key=self.license_key,
        hardware_fingerprint=fingerprint
    )
    
    # 4. Processar resposta
    if result['valid']:
        self._handle_valid(result)
    else:
        self._handle_invalid(result)
```

---

## 🧪 Testes

### Testes do Cliente

1. **Testes de requisições HTTP**
   - Mock do servidor
   - Testar todos os endpoints
   - Testar tratamento de erros

2. **Testes de integração**
   - Fluxo completo de registro
   - Fluxo completo de validação
   - Fluxo completo de revalidação

3. **Testes de cache**
   - Cache válido vs expirado
   - Uso de cache quando servidor offline

---

## 📝 Resumo

### O que implementar no SSM:

1. ✅ **HardwareFingerprint** - Coleta e hash
2. ✅ **LicenseClient** - Cliente HTTP
3. ✅ **LicenseCache** - Cache local
4. ✅ **Atualizar LicenseValidator** - Integrar tudo

### O que NÃO implementar no SSM:

- ❌ Endpoints de licenciamento
- ❌ Lógica de negócio de licenças
- ❌ Gerenciamento de usuários
- ❌ Envio de emails

**Tudo isso fica no servidor de licenciamento!**

