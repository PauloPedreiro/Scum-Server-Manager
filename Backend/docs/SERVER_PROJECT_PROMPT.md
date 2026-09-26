# 🚀 Prompt para Iniciar Projeto - Servidor de Gerenciamento SSM

## 📋 Contexto do Projeto

Preciso criar um **servidor de gerenciamento central** para validar licenças e hardware de múltiplas instâncias do SSM Backend (Sistema de Gerenciamento de Servidores SCUM).

### Situação Atual:
- Existem múltiplos servidores SCUM rodando o SSM Backend
- Cada servidor precisa de validação de licença mensal
- Cada servidor tem um hardware fingerprint único (hash de MAC addresses, CPU, HDs, etc)
- Licenças são válidas por **1 mês**
- Validação deve ocorrer **a cada 4 horas** (sem tolerância)
- Quando hardware muda, usuário precisa **revalidar** (sem tolerância automática)

### Objetivo:
Criar um servidor web que:
1. Gerencia cadastro de usuários (nome completo, email, etc)
2. Vincula hardware fingerprints a usuários
3. Valida licenças periodicamente
4. Permite revalidação quando hardware muda
5. Envia códigos de verificação por email

---

## 🎯 Requisitos Funcionais

### 1. Sistema de Cadastro/Registro

**Registro Inicial:**
- Usuário se cadastra com:
  - Nome completo
  - Email (obrigatório, deve ser verificado)
  - Telefone (opcional)
  - CPF/CNPJ (opcional, mas recomendado)
  - Hardware fingerprint da máquina
  - License key (opcional no cadastro, pode ser adicionado depois)

**Validação de Email:**
- Enviar email de verificação após cadastro
- Usuário deve clicar no link para ativar conta
- Conta só fica ativa após verificação de email

### 2. Sistema de Validação de Licença

**Validação Periódica (a cada 4 horas):**
- Endpoint que recebe:
  - License key
  - Hardware fingerprint
  - Timestamp
  - Backend ID (opcional)

- Servidor valida:
  - ✅ Licença existe e está ativa?
  - ✅ Licença não expirou? (expires_at > now)
  - ✅ Hardware fingerprint corresponde ao cadastrado?
  - ✅ Licença não está em uso em outra máquina simultaneamente?
  - ✅ Timestamp é válido? (não muito antigo, não muito futuro)

- Resposta:
  - Se válido: retorna `valid: true` + data de expiração + próximo check
  - Se inválido: retorna `valid: false` + motivo do erro

**Regras:**
- Licença válida por **30 dias** (1 mês)
- Validação obrigatória **a cada 4 horas**
- **Sem tolerância** - se qualquer validação falhar, bloqueia
- **Sem grace period offline** - requer internet sempre

### 3. Sistema de Revalidação (Hardware Mudou)

**Quando hardware fingerprint muda:**

1. **Solicitar Código de Revalidação:**
   - Usuário informa email
   - Servidor verifica:
     - Email existe no sistema?
     - Email está vinculado ao hardware fingerprint antigo?
   - Se válido:
     - Gera código de 6 dígitos
     - Envia por email
     - Salva código em `revalidation_requests` (expira em 15 minutos)

2. **Revalidar com Código:**
   - Usuário informa:
     - Email
     - Hardware fingerprint antigo
     - Hardware fingerprint novo
     - Código recebido por email
   - Servidor valida:
     - Código está correto?
     - Código não expirou?
     - Email corresponde ao hardware antigo?
   - Se válido:
     - Atualiza hardware fingerprint no banco
     - Registra mudança no histórico
     - Retorna sucesso

### 4. Sistema de Licenças

**Estrutura de Licença:**
- License key (formato: `SSM-XXXX-XXXX-XXXX`)
- Vinculada a um usuário
- Vinculada a um hardware fingerprint
- Data de criação
- Data de expiração (30 dias após criação/renovação)
- Status (active, expired, suspended)
- Tipo (monthly, yearly - por enquanto só monthly)

**Renovação:**
- Licença expira após 30 dias
- Usuário precisa renovar manualmente (por enquanto)
- Ao renovar, adiciona mais 30 dias

---

## 🏗️ Estrutura Técnica

### Stack Tecnológica (Sugestão)

**Backend:**
- Python + Flask/FastAPI (ou Node.js + Express)
- PostgreSQL ou MySQL (banco relacional)
- SQLAlchemy/Sequelize (ORM)

**Autenticação:**
- JWT para API keys de super user (futuro)
- Hash de senhas com bcrypt (se tiver login de usuários)

**Email:**
- SMTP (Gmail, SendGrid, etc)
- Templates de email (HTML)

**Deploy:**
- Docker (recomendado)
- Servidor Linux (Ubuntu/Debian)

### Estrutura de Pastas (Python/Flask)

```
ssm-license-server/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── user.py
│   │   ├── machine.py
│   │   ├── license.py
│   │   └── revalidation_request.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── licenses.py
│   │   └── validation.py
│   ├── services/
│   │   ├── email_service.py
│   │   ├── validation_service.py
│   │   └── license_service.py
│   └── utils/
│       ├── validators.py
│       └── helpers.py
├── migrations/
├── tests/
├── config.py
├── requirements.txt
├── .env
└── README.md
```

---

## 📡 Endpoints da API

### Base URL
```
https://api.ssm-backend.com/v1
```

### 1. Registro de Usuário

**POST /api/v1/register**

Request:
```json
{
  "full_name": "João Silva",
  "email": "joao@email.com",
  "phone": "+5511999999999",  // opcional
  "document": "12345678900",  // CPF/CNPJ, opcional
  "hardware_fingerprint": "a1b2c3d4e5f6...",
  "license_key": "SSM-XXXX-XXXX-XXXX"  // opcional
}
```

Response (200):
```json
{
  "success": true,
  "message": "Usuário registrado. Verifique seu email para ativar a conta.",
  "data": {
    "user_id": 1,
    "email": "joao@email.com",
    "verification_sent": true
  }
}
```

Response (400):
```json
{
  "success": false,
  "error": "Email já cadastrado"
}
```

### 2. Verificação de Email

**GET /api/v1/verify-email?token={verification_token}**

Response (200):
```json
{
  "success": true,
  "message": "Email verificado com sucesso"
}
```

### 3. Validação de Licença (Principal)

**POST /api/v1/validate**

Request:
```json
{
  "license_key": "SSM-XXXX-XXXX-XXXX",
  "hardware_fingerprint": "a1b2c3d4e5f6...",
  "timestamp": "2025-01-15T10:00:00Z",
  "backend_id": "SCUM-BACKEND-ABC123"  // opcional
}
```

Response (200) - Válido:
```json
{
  "valid": true,
  "license": {
    "key": "SSM-XXXX-XXXX-XXXX",
    "expires_at": "2025-02-15T00:00:00Z",
    "days_remaining": 15,
    "type": "monthly"
  },
  "hardware": {
    "fingerprint": "a1b2c3d4e5f6...",
    "matches": true,
    "registered_at": "2025-01-15T00:00:00Z"
  },
  "validation": {
    "timestamp": "2025-01-15T10:00:00Z",
    "next_check_at": "2025-01-15T14:00:00Z",
    "server_time": "2025-01-15T10:00:01Z"
  },
  "features": {
    "server_control": true,
    "scheduler": true,
    "notifications": true
  }
}
```

Response (200) - Inválido:
```json
{
  "valid": false,
  "reason": "hardware_mismatch",  // ou "expired", "not_found", "in_use_elsewhere"
  "message": "Hardware fingerprint não corresponde ao cadastrado",
  "requires_revalidation": true
}
```

### 4. Solicitar Código de Revalidação

**POST /api/v1/revalidate/request-code**

Request:
```json
{
  "email": "joao@email.com",
  "old_fingerprint": "a1b2c3d4e5f6..."
}
```

Response (200):
```json
{
  "success": true,
  "message": "Código de revalidação enviado para seu email",
  "expires_in_minutes": 15
}
```

Response (400):
```json
{
  "success": false,
  "error": "Email não encontrado ou não vinculado a este hardware"
}
```

### 5. Revalidar com Código

**POST /api/v1/revalidate**

Request:
```json
{
  "email": "joao@email.com",
  "old_fingerprint": "a1b2c3d4e5f6...",
  "new_fingerprint": "f6e5d4c3b2a1...",
  "verification_code": "123456"
}
```

Response (200):
```json
{
  "success": true,
  "message": "Hardware revalidado com sucesso",
  "data": {
    "old_fingerprint": "a1b2c3d4e5f6...",
    "new_fingerprint": "f6e5d4c3b2a1...",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

Response (400):
```json
{
  "success": false,
  "error": "Código inválido ou expirado"
}
```

### 6. Criar/Renovar Licença (Admin)

**POST /api/v1/licenses/create**

Request:
```json
{
  "user_id": 1,
  "license_key": "SSM-XXXX-XXXX-XXXX",  // opcional, gerar se não fornecido
  "duration_days": 30,
  "type": "monthly"
}
```

Response (200):
```json
{
  "success": true,
  "data": {
    "license_key": "SSM-XXXX-XXXX-XXXX",
    "expires_at": "2025-02-15T00:00:00Z",
    "created_at": "2025-01-15T00:00:00Z"
  }
}
```

---

## 🗄️ Estrutura do Banco de Dados

### Tabela: `users`

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    phone VARCHAR(20),
    document VARCHAR(20),  -- CPF/CNPJ
    password_hash VARCHAR(255),  -- se tiver login
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_verification_token ON users(email_verification_token);
```

### Tabela: `machines`

```sql
CREATE TABLE machines (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    hardware_fingerprint VARCHAR(255) UNIQUE NOT NULL,
    license_key VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_validated TIMESTAMP,
    validation_count INTEGER DEFAULT 0,
    FOREIGN KEY (license_key) REFERENCES licenses(key)
);

CREATE INDEX idx_machines_fingerprint ON machines(hardware_fingerprint);
CREATE INDEX idx_machines_user_id ON machines(user_id);
CREATE INDEX idx_machines_license_key ON machines(license_key);
```

### Tabela: `licenses`

```sql
CREATE TABLE licenses (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    hardware_fingerprint VARCHAR(255) NOT NULL,
    type VARCHAR(20) DEFAULT 'monthly',  -- monthly, yearly
    status VARCHAR(20) DEFAULT 'active',  -- active, expired, suspended
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_renewed_at TIMESTAMP,
    renewal_count INTEGER DEFAULT 0,
    FOREIGN KEY (hardware_fingerprint) REFERENCES machines(hardware_fingerprint)
);

CREATE INDEX idx_licenses_key ON licenses(key);
CREATE INDEX idx_licenses_user_id ON licenses(user_id);
CREATE INDEX idx_licenses_status ON licenses(status);
CREATE INDEX idx_licenses_expires_at ON licenses(expires_at);
```

### Tabela: `validation_history`

```sql
CREATE TABLE validation_history (
    id SERIAL PRIMARY KEY,
    machine_id INTEGER NOT NULL REFERENCES machines(id),
    license_key VARCHAR(50) NOT NULL,
    hardware_fingerprint VARCHAR(255) NOT NULL,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,  -- valid, invalid, expired, mismatch
    reason TEXT,
    backend_id VARCHAR(100),
    ip_address VARCHAR(45),
    details JSONB
);

CREATE INDEX idx_validation_history_machine_id ON validation_history(machine_id);
CREATE INDEX idx_validation_history_validated_at ON validation_history(validated_at);
CREATE INDEX idx_validation_history_status ON validation_history(status);
```

### Tabela: `revalidation_requests`

```sql
CREATE TABLE revalidation_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    email VARCHAR(255) NOT NULL,
    old_fingerprint VARCHAR(255) NOT NULL,
    new_fingerprint VARCHAR(255),  -- preenchido após revalidação
    verification_code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_revalidation_code ON revalidation_requests(verification_code);
CREATE INDEX idx_revalidation_email ON revalidation_requests(email);
CREATE INDEX idx_revalidation_expires_at ON revalidation_requests(expires_at);
```

---

## 🔒 Regras de Validação

### Validação Periódica (a cada 4 horas)

**Checklist de Validação:**

1. **Licença existe?**
   ```sql
   SELECT * FROM licenses WHERE key = ? AND status = 'active'
   ```

2. **Licença não expirou?**
   ```sql
   WHERE expires_at > NOW()
   ```

3. **Hardware fingerprint corresponde?**
   ```sql
   SELECT * FROM machines 
   WHERE hardware_fingerprint = ? 
   AND license_key = ?
   AND is_active = TRUE
   ```

4. **Licença não está em uso simultâneo em outra máquina?**
   - Verificar último `validation_history` com status 'valid'
   - Se hardware_fingerprint diferente E timestamp < 5 minutos, bloquear

5. **Timestamp válido?**
   - Timestamp não pode ser > 5 minutos no futuro
   - Timestamp não pode ser > 1 hora no passado

**Ação em caso de falha:**
- Retornar `valid: false` + motivo
- Registrar em `validation_history` com status 'invalid'
- Não bloquear licença (deixa para o cliente decidir)

### Revalidação de Hardware

**Fluxo:**
1. Usuário solicita código → gera código de 6 dígitos
2. Envia por email
3. Código expira em 15 minutos
4. Usuário envia código → valida e atualiza hardware_fingerprint
5. Registra mudança no histórico

**Validações:**
- Email existe e está verificado
- Email está vinculado ao hardware_fingerprint antigo
- Código está correto e não expirou
- Código não foi usado antes

---

## 📧 Sistema de Emails

### Templates Necessários

1. **Verificação de Email (Cadastro)**
   - Assunto: "Verifique seu email - SSM Backend"
   - Link com token de verificação
   - Expira em 24 horas

2. **Código de Revalidação**
   - Assunto: "Código de Revalidação - SSM Backend"
   - Código de 6 dígitos
   - Expira em 15 minutos
   - Instruções de uso

3. **Licença Expirando (Aviso)**
   - Assunto: "Sua licença expira em X dias"
   - Enviar 7 dias antes de expirar
   - Link para renovação

4. **Licença Expirada**
   - Assunto: "Sua licença expirou - SSM Backend"
   - Instruções para renovação

---

## 🛡️ Segurança

### Medidas de Segurança

1. **Rate Limiting**
   - Máximo 10 requisições/minuto por IP
   - Máximo 5 tentativas de revalidação/hora por email

2. **Validação de Input**
   - Sanitizar todos os inputs
   - Validar formato de email, hardware_fingerprint, etc
   - Prevenir SQL injection (usar ORM/prepared statements)

3. **Códigos de Verificação**
   - Códigos aleatórios de 6 dígitos
   - Hash no banco (não armazenar em texto plano)
   - Expiração curta (15 minutos)

4. **Logs de Auditoria**
   - Registrar todas as validações
   - Registrar tentativas de revalidação
   - Registrar mudanças de hardware

5. **HTTPS Obrigatório**
   - Todas as comunicações via HTTPS
   - Não aceitar requisições HTTP em produção

---

## 🧪 Testes Necessários

### Testes Unitários
- Validação de licença (vários cenários)
- Geração de códigos de revalidação
- Validação de hardware fingerprint

### Testes de Integração
- Fluxo completo de registro
- Fluxo completo de validação
- Fluxo completo de revalidação

### Testes de Carga
- Múltiplas validações simultâneas
- Rate limiting funcionando

---

## 📝 Variáveis de Ambiente

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/ssm_licenses

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password
EMAIL_FROM=noreply@ssm-backend.com

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret

# Server
HOST=0.0.0.0
PORT=5000
DEBUG=False

# License
DEFAULT_LICENSE_DURATION_DAYS=30
REVALIDATION_CODE_EXPIRY_MINUTES=15
EMAIL_VERIFICATION_EXPIRY_HOURS=24
```

---

## 🚀 Próximos Passos

1. **Setup inicial**
   - Criar estrutura do projeto
   - Configurar banco de dados
   - Configurar ambiente de desenvolvimento

2. **Implementar modelos**
   - Criar models (User, Machine, License, etc)
   - Criar migrations

3. **Implementar endpoints básicos**
   - Registro
   - Verificação de email
   - Validação

4. **Implementar serviços**
   - Email service
   - Validation service
   - License service

5. **Implementar revalidação**
   - Solicitar código
   - Revalidar com código

6. **Testes e deploy**
   - Testes completos
   - Deploy em servidor
   - Documentação da API

---

## 📚 Documentação Adicional

- API deve ter documentação Swagger/OpenAPI
- README com instruções de instalação
- Guia de deploy
- Exemplos de uso da API

---

**Inicie o projeto com este prompt e me avise quando tiver a estrutura básica pronta!**

