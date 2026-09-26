# 🔐 Sistema de Licenciamento - Arquitetura Proposta

## 📋 Visão Geral

Este documento descreve a arquitetura proposta para implementar um sistema de licenciamento robusto e escalável que:
- ✅ **Expira a cada 30 dias** (renovação automática ou manual)
- ✅ **Controle de hardware** (fingerprinting único por máquina)
- ✅ **Prevenção de uso simultâneo** (mesma licença não pode rodar em múltiplas máquinas)
- ✅ **Funcionamento offline** (cache local para períodos sem internet)
- ✅ **Escalável** (preparado para milhares de licenças)

---

## 🏗️ Arquitetura do Sistema

### **Componentes Principais**

```
┌─────────────────────────────────────────────────────────────┐
│                    SERVIDOR CENTRAL (Frontend)               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API de Licenciamento                                │   │
│  │  - Validação de licenças                            │   │
│  │  - Gerenciamento de hardware fingerprints           │   │
│  │  - Controle de expiração                            │   │
│  │  - Logs de uso                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Banco de Dados (PostgreSQL/MySQL)                    │   │
│  │  - licenses (tabela de licenças)                     │   │
│  │  - hardware_fingerprints (máquinas vinculadas)       │   │
│  │  - license_usage_logs (histórico de validações)     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTPS/API
┌─────────────────────────────────────────────────────────────┐
│              BACKEND SCUM (Cliente)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  HardwareFingerprint (novo módulo)                   │   │
│  │  - Gera fingerprint único da máquina                │   │
│  │  - Combina: MAC, CPU ID, Disk Serial, etc.          │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LicenseManager (atualizado)                          │   │
│  │  - Validação local e remota                          │   │
│  │  - Cache de validação                                │   │
│  │  - Renovação automática                              │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LicenseValidator (atualizado)                        │   │
│  │  - Integração com LicenseManager                      │   │
│  │  - Validação periódica                                │   │
│  │  - Bloqueio de funcionalidades                       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Componentes Backend (Novos/Atualizados)

### **1. HardwareFingerprint** (`core/licensing/hardware_fingerprint.py`)

**Responsabilidade:** Gerar um identificador único e estável da máquina.

```python
class HardwareFingerprint:
    """
    Gera fingerprint único da máquina combinando:
    - MAC Address (adaptadores de rede)
    - CPU ID/Serial
    - Disk Serial Number
    - Motherboard Serial (se disponível)
    - Windows Machine GUID
    """
    
    def generate_fingerprint() -> str:
        """Gera hash SHA-256 único da máquina"""
        
    def get_machine_info() -> Dict:
        """Retorna informações detalhadas da máquina"""
```

**Características:**
- ✅ **Determinístico**: Mesma máquina sempre gera mesmo fingerprint
- ✅ **Resistente a mudanças**: Não muda com atualizações de software
- ✅ **Plataforma Windows**: Usa WMI, Registry, PowerShell
- ✅ **Fallback**: Se algum componente falhar, usa alternativas

**Implementação:**

**Windows:**
```python
import wmi
import subprocess
import hashlib
import platform

def get_mac_addresses():
    """Obtém MAC addresses de todos os adaptadores"""
    # WMI query para adaptadores de rede
    
def get_cpu_id():
    """Obtém CPU ID/Serial"""
    # WMI: Win32_Processor.ProcessorId
    
def get_disk_serial():
    """Obtém serial do disco principal"""
    # WMI: Win32_DiskDrive.SerialNumber
    
def get_motherboard_serial():
    """Obtém serial da placa mãe"""
    # WMI: Win32_BaseBoard.SerialNumber
    
def get_windows_machine_guid():
    """Obtém Machine GUID do Windows"""
    # Registry: HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography\MachineGuid
```

**Hash Final:**
```python
def generate_fingerprint():
    components = [
        get_mac_addresses(),
        get_cpu_id(),
        get_disk_serial(),
        get_motherboard_serial(),
        get_windows_machine_guid()
    ]
    
    # Combina todos os componentes
    combined = "|".join(components)
    
    # Gera hash SHA-256
    return hashlib.sha256(combined.encode()).hexdigest()
```

---

### **2. LicenseManager** (`core/licensing/license_manager.py`)

**Responsabilidade:** Gerenciar ciclo de vida completo da licença.

```python
class LicenseManager:
    """
    Gerencia licença local e remota:
    - Validação inicial
    - Cache local
    - Renovação automática
    - Bloqueio de funcionalidades
    """
    
    def __init__(self, hardware_fingerprint, config, logger):
        self.fingerprint = hardware_fingerprint
        self.license_key = None
        self.cached_license = None
        self.last_validation = None
        
    def register_license(license_key: str) -> bool:
        """Registra licença na máquina"""
        
    def validate_license(force: bool = False) -> Dict:
        """Valida licença (local ou remota)"""
        
    def is_license_valid() -> bool:
        """Verifica se licença está válida"""
        
    def get_license_info() -> Dict:
        """Retorna informações da licença"""
        
    def renew_license() -> bool:
        """Tenta renovar licença automaticamente"""
```

**Fluxo de Validação:**

```
1. Verifica cache local (últimas 24h)
   ↓ (se expirado ou não existe)
2. Valida remotamente com servidor central
   ↓
3. Servidor verifica:
   - Licença existe?
   - Não expirada? (expires_at > now)
   - Hardware fingerprint corresponde?
   - Não está em uso em outra máquina?
   ↓
4. Se válido:
   - Atualiza cache local
   - Retorna sucesso
   ↓
5. Se inválido:
   - Bloqueia funcionalidades
   - Retorna erro
```

**Cache Local:**
```json
{
  "license_key": "SSM-XXXX-XXXX-XXXX",
  "hardware_fingerprint": "abc123...",
  "valid": true,
  "expires_at": "2025-02-01T00:00:00Z",
  "license_type": "monthly",
  "features": ["server_control", "scheduler", "notifications"],
  "validated_at": "2025-01-02T10:30:00Z",
  "next_validation": "2025-01-02T11:30:00Z"
}
```

---

### **3. LicenseValidator** (Atualizado)

**Modificações:**

```python
class LicenseValidator:
    def __init__(self, config, logger, backend_identity, license_manager):
        # ... código existente ...
        self.license_manager = license_manager
        
    def validate_license(self, license_key: str = None) -> bool:
        """Valida usando LicenseManager"""
        if not self.license_manager:
            return self._check_grace_period()
            
        result = self.license_manager.validate_license()
        return result.get('valid', False)
        
    def should_block_functionality(self) -> bool:
        """Verifica se deve bloquear funcionalidades"""
        return not self.license_manager.is_license_valid()
```

---

## 🗄️ Estrutura de Banco de Dados (Servidor Central)

### **Tabela: `licenses`**

```sql
CREATE TABLE licenses (
    id SERIAL PRIMARY KEY,
    license_key VARCHAR(50) UNIQUE NOT NULL,
    owner_id VARCHAR(100) NOT NULL,
    license_type VARCHAR(20) NOT NULL, -- 'monthly', 'yearly', 'lifetime'
    status VARCHAR(20) NOT NULL, -- 'active', 'expired', 'revoked', 'suspended'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_renewed_at TIMESTAMP,
    renewal_period_days INTEGER DEFAULT 30,
    max_activations INTEGER DEFAULT 1, -- Máximo de máquinas
    features JSONB, -- Array de features permitidas
    metadata JSONB -- Dados adicionais
);

CREATE INDEX idx_licenses_key ON licenses(license_key);
CREATE INDEX idx_licenses_owner ON licenses(owner_id);
CREATE INDEX idx_licenses_status ON licenses(status);
CREATE INDEX idx_licenses_expires ON licenses(expires_at);
```

### **Tabela: `hardware_fingerprints`**

```sql
CREATE TABLE hardware_fingerprints (
    id SERIAL PRIMARY KEY,
    license_key VARCHAR(50) NOT NULL,
    hardware_fingerprint VARCHAR(64) NOT NULL, -- SHA-256
    machine_name VARCHAR(255),
    ip_address VARCHAR(45),
    first_activation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_validation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    activation_count INTEGER DEFAULT 1,
    FOREIGN KEY (license_key) REFERENCES licenses(license_key) ON DELETE CASCADE,
    UNIQUE(license_key, hardware_fingerprint)
);

CREATE INDEX idx_fingerprints_license ON hardware_fingerprints(license_key);
CREATE INDEX idx_fingerprints_hash ON hardware_fingerprints(hardware_fingerprint);
```

### **Tabela: `license_usage_logs`**

```sql
CREATE TABLE license_usage_logs (
    id SERIAL PRIMARY KEY,
    license_key VARCHAR(50) NOT NULL,
    hardware_fingerprint VARCHAR(64),
    action VARCHAR(50) NOT NULL, -- 'validation', 'activation', 'renewal', 'revocation'
    result VARCHAR(20) NOT NULL, -- 'success', 'failed', 'blocked'
    reason TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (license_key) REFERENCES licenses(license_key) ON DELETE CASCADE
);

CREATE INDEX idx_logs_license ON license_usage_logs(license_key);
CREATE INDEX idx_logs_fingerprint ON license_usage_logs(hardware_fingerprint);
CREATE INDEX idx_logs_created ON license_usage_logs(created_at);
```

---

## 🌐 API do Servidor Central

### **Endpoint: `POST /api/v1/licenses/validate`**

**Request:**
```json
{
  "license_key": "SSM-XXXX-XXXX-XXXX",
  "hardware_fingerprint": "abc123...",
  "backend_id": "SCUM-BACKEND-ABC123",
  "version": "1.13.0"
}
```

**Response (Sucesso):**
```json
{
  "success": true,
  "valid": true,
  "license": {
    "license_key": "SSM-XXXX-XXXX-XXXX",
    "expires_at": "2025-02-01T00:00:00Z",
    "days_remaining": 29,
    "license_type": "monthly",
    "features": ["server_control", "scheduler", "notifications"],
    "max_activations": 1,
    "current_activations": 1
  },
  "hardware": {
    "fingerprint": "abc123...",
    "first_activation": "2025-01-01T00:00:00Z",
    "is_active": true
  },
  "cache_ttl": 86400
}
```

**Response (Erro - Licença Inválida):**
```json
{
  "success": false,
  "valid": false,
  "error": "license_expired",
  "message": "Licença expirada em 2025-01-01",
  "can_renew": true
}
```

**Response (Erro - Hardware Diferente):**
```json
{
  "success": false,
  "valid": false,
  "error": "hardware_mismatch",
  "message": "Licença já está ativa em outra máquina",
  "current_machine": {
    "fingerprint": "xyz789...",
    "last_validation": "2025-01-02T09:00:00Z"
  }
}
```

### **Endpoint: `POST /api/v1/licenses/activate`**

**Request:**
```json
{
  "license_key": "SSM-XXXX-XXXX-XXXX",
  "hardware_fingerprint": "abc123...",
  "backend_id": "SCUM-BACKEND-ABC123",
  "machine_name": "DESKTOP-ABC123"
}
```

**Response:**
```json
{
  "success": true,
  "activated": true,
  "license": {
    "license_key": "SSM-XXXX-XXXX-XXXX",
    "expires_at": "2025-02-01T00:00:00Z",
    "features": ["server_control", "scheduler", "notifications"]
  }
}
```

### **Endpoint: `POST /api/v1/licenses/renew`**

**Request:**
```json
{
  "license_key": "SSM-XXXX-XXXX-XXXX",
  "hardware_fingerprint": "abc123...",
  "renewal_period_days": 30
}
```

**Response:**
```json
{
  "success": true,
  "renewed": true,
  "new_expires_at": "2025-03-03T00:00:00Z",
  "days_added": 30
}
```

---

## 📁 Estrutura de Arquivos Locais

### **`data/license.json`** (Novo)

```json
{
  "license_key": "SSM-XXXX-XXXX-XXXX",
  "hardware_fingerprint": "abc123...",
  "registered_at": "2025-01-01T00:00:00Z",
  "last_validation": "2025-01-02T10:30:00Z",
  "cached_license": {
    "valid": true,
    "expires_at": "2025-02-01T00:00:00Z",
    "features": ["server_control", "scheduler", "notifications"],
    "validated_at": "2025-01-02T10:30:00Z"
  },
  "validation_attempts": 0,
  "last_error": null
}
```

---

## ⚙️ Configuração (`config.json`)

```json
{
  "licensing": {
    "enabled": true,
    "validation_mode": "remote", // "remote", "local", "hybrid"
    "check_interval": 3600, // 1 hora
    "cache_ttl": 86400, // 24 horas
    "grace_period": 86400, // 24 horas offline
    "auto_renew": true,
    "renewal_advance_days": 7, // Renovar 7 dias antes de expirar
    "server_url": "https://api.ssm-backend.com/v1",
    "api_key": null, // Será definido durante registro
    "block_on_invalid": true,
    "allowed_features": [
      "server_control",
      "scheduler",
      "notifications",
      "discord_webhooks"
    ]
  }
}
```

---

## 🔄 Fluxos de Funcionamento

### **1. Registro Inicial de Licença**

```
1. Usuário insere license_key no backend
   ↓
2. Backend gera hardware_fingerprint
   ↓
3. POST /api/v1/licenses/activate
   {
     license_key: "SSM-XXXX-XXXX-XXXX",
     hardware_fingerprint: "abc123...",
     backend_id: "SCUM-BACKEND-ABC123"
   }
   ↓
4. Servidor valida:
   - Licença existe e está ativa?
   - Não expirada?
   - Máximo de ativações não excedido?
   ↓
5. Servidor registra hardware_fingerprint
   ↓
6. Backend salva em data/license.json
   ↓
7. Backend inicia validações periódicas
```

### **2. Validação Periódica**

```
A cada 1 hora (check_interval):
   ↓
1. Verifica cache local (últimas 24h)
   ↓
2. Se cache válido:
   - Usa cache
   - Próxima validação em 1h
   ↓
3. Se cache expirado:
   - POST /api/v1/licenses/validate
   ↓
4. Servidor verifica:
   - Licença ainda válida?
   - Hardware fingerprint corresponde?
   - Não está em uso em outra máquina?
   ↓
5. Se válido:
   - Atualiza cache local
   - Próxima validação em 1h
   ↓
6. Se inválido:
   - Bloqueia funcionalidades
   - Mostra mensagem de erro
   - Tenta novamente em 15 minutos
```

### **3. Renovação Automática**

```
7 dias antes de expirar (renewal_advance_days):
   ↓
1. Backend detecta expiração próxima
   ↓
2. POST /api/v1/licenses/renew
   {
     license_key: "SSM-XXXX-XXXX-XXXX",
     hardware_fingerprint: "abc123...",
     renewal_period_days: 30
   }
   ↓
3. Servidor processa renovação:
   - Atualiza expires_at
   - Registra no log
   ↓
4. Backend atualiza cache local
   ↓
5. Próxima renovação em 23 dias
```

### **4. Funcionamento Offline (Grace Period)**

```
Sem internet por até 24 horas:
   ↓
1. Backend usa cache local
   ↓
2. Se cache válido:
   - Continua funcionando normalmente
   ↓
3. Se cache expirado:
   - Inicia grace period (24h)
   - Funciona normalmente
   - Tenta validar a cada 15 minutos
   ↓
4. Após 24h sem internet:
   - Bloqueia funcionalidades
   - Requer conexão para reativar
```

---

## 🛡️ Segurança e Prevenção de Fraude

### **1. Hardware Fingerprinting**

- ✅ **Múltiplos componentes**: Combina MAC, CPU, Disk, Motherboard
- ✅ **Hash SHA-256**: Não pode ser facilmente revertido
- ✅ **Determinístico**: Mesma máquina sempre gera mesmo hash
- ✅ **Resistente a mudanças**: Não muda com atualizações

### **2. Validação Remota Obrigatória**

- ✅ **Sem validação offline permanente**: Cache expira em 24h
- ✅ **Validação periódica**: A cada 1 hora
- ✅ **Bloqueio automático**: Se inválido ou expirado

### **3. Prevenção de Cópia**

- ✅ **Uma licença = Uma máquina**: Hardware fingerprint vinculado
- ✅ **Detecção de uso simultâneo**: Servidor detecta múltiplos acessos
- ✅ **Revogação automática**: Se detectado em outra máquina

### **4. Logs e Auditoria**

- ✅ **Todas as validações são logadas**
- ✅ **Histórico de ativações**
- ✅ **Rastreamento de IP e User-Agent**
- ✅ **Alertas de tentativas suspeitas**

---

## 🔧 Implementação Técnica

### **Bibliotecas Necessárias**

```python
# requirements.txt (adicional)
wmi>=1.5.1          # Windows Management Instrumentation
pywin32>=306       # Windows API (para Registry)
cryptography>=41.0 # Hash e criptografia
requests>=2.31.0   # HTTP client (já existe)
```

### **Estrutura de Módulos**

```
core/
├── licensing/                    # 🆕 Módulo de Licenciamento
│   ├── __init__.py
│   ├── hardware_fingerprint.py   # Geração de fingerprint
│   ├── license_manager.py        # Gerenciamento de licença
│   └── license_cache.py          # Cache local de validação
```

---

## 📊 Monitoramento e Métricas

### **Métricas do Backend**

- Tempo até próxima validação
- Última validação bem-sucedida
- Tentativas de validação falhadas
- Status da licença (válida/expirada/bloqueada)
- Dias restantes até expiração

### **Métricas do Servidor Central**

- Total de licenças ativas
- Licenças expirando em 7 dias
- Tentativas de uso em hardware diferente
- Taxa de renovação automática
- Licenças em grace period

---

## 🚀 Fases de Implementação

### **Fase 1: Preparação (Semana 1-2)**

1. ✅ Criar módulo `HardwareFingerprint`
2. ✅ Implementar geração de fingerprint no Windows
3. ✅ Criar estrutura de cache local
4. ✅ Testes unitários

### **Fase 2: Integração Backend (Semana 3-4)**

1. ✅ Criar módulo `LicenseManager`
2. ✅ Integrar com `LicenseValidator` existente
3. ✅ Implementar validação periódica
4. ✅ Implementar bloqueio de funcionalidades

### **Fase 3: API do Servidor Central (Semana 5-6)**

1. ✅ Criar endpoints de validação
2. ✅ Implementar banco de dados
3. ✅ Sistema de logs e auditoria
4. ✅ Testes de integração

### **Fase 4: Renovação e Grace Period (Semana 7-8)**

1. ✅ Implementar renovação automática
2. ✅ Sistema de grace period
3. ✅ Notificações de expiração
4. ✅ Dashboard de gerenciamento

### **Fase 5: Testes e Refinamento (Semana 9-10)**

1. ✅ Testes de carga
2. ✅ Testes de segurança
3. ✅ Documentação completa
4. ✅ Deploy em produção

---

## ⚠️ Considerações Importantes

### **1. Compatibilidade com Instalações Existentes**

- ✅ **Modo Legacy**: Instalações antigas sem licença continuam funcionando
- ✅ **Migração Gradual**: Usuários podem migrar quando quiserem
- ✅ **Grace Period Inicial**: Período de transição sem bloqueio

### **2. Experiência do Usuário**

- ✅ **Validação Silenciosa**: Não interrompe o uso normal
- ✅ **Mensagens Claras**: Erros explicam o problema e solução
- ✅ **Renovação Automática**: Usuário não precisa fazer nada
- ✅ **Suporte Offline**: Funciona por 24h sem internet

### **3. Escalabilidade**

- ✅ **Cache Agressivo**: Reduz requisições ao servidor
- ✅ **Validação Assíncrona**: Não bloqueia operações
- ✅ **Rate Limiting**: Protege servidor de abuso
- ✅ **CDN para Cache**: Respostas mais rápidas

---

## 📝 Checklist de Implementação

### **Backend**

- [ ] Módulo `HardwareFingerprint` implementado
- [ ] Módulo `LicenseManager` implementado
- [ ] Integração com `LicenseValidator` existente
- [ ] Sistema de cache local
- [ ] Validação periódica automática
- [ ] Renovação automática
- [ ] Bloqueio de funcionalidades
- [ ] Notificações de expiração
- [ ] Logs de validação

### **Servidor Central**

- [ ] API de validação implementada
- [ ] API de ativação implementada
- [ ] API de renovação implementada
- [ ] Banco de dados configurado
- [ ] Sistema de logs implementado
- [ ] Detecção de uso simultâneo
- [ ] Dashboard de gerenciamento
- [ ] Sistema de notificações

### **Documentação**

- [ ] Guia de instalação
- [ ] Guia de registro de licença
- [ ] Troubleshooting
- [ ] FAQ
- [ ] Documentação da API

---

## 🔮 Melhorias Futuras

### **1. Licenças Multi-Máquina**

- Permitir mesma licença em até N máquinas
- Gerenciamento de máquinas no dashboard
- Revogação individual de máquinas

### **2. Licenças por Funcionalidade**

- Planos diferentes (Basic, Pro, Enterprise)
- Ativação/desativação de features
- Upgrade/downgrade de plano

### **3. Licenças Temporárias**

- Licenças de teste (7 dias)
- Licenças de evento (24h)
- Licenças de desenvolvimento

### **4. Integração com Pagamento**

- Renovação automática com pagamento
- Notificações de pagamento pendente
- Histórico de pagamentos

---

**Última atualização**: 02/01/2025  
**Versão**: 1.0.0  
**Status**: 📋 Proposta de Arquitetura

