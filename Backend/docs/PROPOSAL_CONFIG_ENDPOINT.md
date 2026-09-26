# 📋 Proposta: Endpoint de Configuração (`/api/config`)

## 🎯 Objetivo

Criar endpoints REST para gerenciar o arquivo `data/config.json` de forma segura e controlada, permitindo leitura, atualização parcial e completa da configuração.

---

## 📊 Análise do Estado Atual

### **Estrutura do `config.json`**

O arquivo possui múltiplas seções:
- `paths` - Caminhos de diretórios e arquivos
- `server` - Configurações do servidor SCUM
- `logging` - Configurações de log
- `api` - Configurações da API
- `updates` - Configurações de atualização
- `communication` - Configurações de comunicação
- `scheduler` - Agendamento de restarts
- `weather_scheduler` - Sincronização de clima
- `squad_sync` - Sincronização de squads
- `survival_sync` - Sincronização de survival stats
- `rankings_sync` - Sincronização de rankings
- `player_skills_sync` - Sincronização de skills
- `chest_sync` - Sincronização de baús
- `notifications` - Sistema de notificações
- `logs` - Monitoramento de logs
- `steam` - Configurações Steam
- `chat_monitoring` - Monitoramento de chat
- `time_precision` - Precisão de horário
- `fishing_ranking` - Ranking de pescadores
- `lockpicking_ranking` - Ranking de lockpicking
- `kills_ranking` - Ranking de kills
- `snipers_ranking` - Ranking de snipers
- `vehicle_verification` - Verificação de veículos
- `player_gps_sync` - Sincronização de GPS
- `scum_db_shared_copy` - Gerenciador de cópia do DB

### **Carregamento Atual**

- Config é carregado no início da aplicação via `load_config()`
- Armazenado em variável global `config`
- Usado por múltiplos serviços e componentes
- Não há recarregamento dinâmico (requer reinício)

---

## 💡 Proposta de Endpoints

### **1. GET `/api/config`**
**Objetivo**: Obter a configuração completa ou uma seção específica

**Query Params**:
- `section` (opcional): Nome da seção (ex: `server`, `api`, `scheduler`)
- `format` (opcional): `pretty` para JSON formatado (padrão: `compact`)

**Resposta**:
```json
{
  "success": true,
  "data": {
    // Configuração completa ou seção específica
  },
  "timestamp": 1701504000
}
```

**Exemplos**:
- `GET /api/config` - Retorna configuração completa
- `GET /api/config?section=api` - Retorna apenas seção `api`
- `GET /api/config?section=scheduler&format=pretty` - Retorna seção formatada

---

### **2. GET `/api/config/sections`**
**Objetivo**: Listar todas as seções disponíveis

**Resposta**:
```json
{
  "success": true,
  "data": {
    "sections": [
      "paths",
      "server",
      "logging",
      "api",
      "updates",
      "communication",
      "scheduler",
      // ... todas as seções
    ],
    "total": 25
  }
}
```

---

### **3. PATCH `/api/config`**
**Objetivo**: Atualizar seção(s) específica(s) da configuração

**Body**:
```json
{
  "sections": {
    "api": {
      "port": 3001,
      "debug": true
    },
    "scheduler": {
      "enabled": false
    }
  },
  "create_backup": true
}
```

**Resposta**:
```json
{
  "success": true,
  "message": "Configuração atualizada com sucesso",
  "data": {
    "updated_sections": ["api", "scheduler"],
    "backup_file": "data/config.backup.2025-12-02_15-30-45.json",
    "requires_restart": ["api", "scheduler"]
  },
  "timestamp": 1701504000
}
```

**Validações**:
- Verificar se as seções existem
- Validar tipos de dados (números, strings, booleans, arrays)
- Validar valores específicos (ex: portas válidas, timezones válidos)
- Criar backup antes de salvar (se `create_backup: true`)

---

### **4. PUT `/api/config`**
**Objetivo**: Substituir a configuração completa

**Body**:
```json
{
  "config": {
    // Configuração completa
  },
  "create_backup": true,
  "validate": true
}
```

**Resposta**:
```json
{
  "success": true,
  "message": "Configuração completa atualizada",
  "data": {
    "backup_file": "data/config.backup.2025-12-02_15-30-45.json",
    "requires_restart": true
  },
  "timestamp": 1701504000
}
```

**Validações**:
- Validar estrutura completa do JSON
- Verificar se todas as seções obrigatórias estão presentes
- Validar tipos e valores
- Criar backup obrigatório antes de substituir

---

### **5. POST `/api/config/reload`**
**Objetivo**: Recarregar a configuração do arquivo sem reiniciar o servidor

**Body** (opcional):
```json
{
  "sections": ["api", "scheduler"]  // Seções específicas para recarregar
}
```

**Resposta**:
```json
{
  "success": true,
  "message": "Configuração recarregada",
  "data": {
    "reloaded_sections": ["api", "scheduler"],
    "requires_service_restart": ["scheduler"]
  },
  "timestamp": 1701504000
}
```

**Nota**: Algumas seções podem requerer reinício de serviços específicos.

---

### **6. GET `/api/config/backup`**
**Objetivo**: Listar backups disponíveis

**Query Params**:
- `limit` (opcional): Número máximo de backups (padrão: 10)

**Resposta**:
```json
{
  "success": true,
  "data": {
    "backups": [
      {
        "filename": "config.backup.2025-12-02_15-30-45.json",
        "path": "data/config.backup.2025-12-02_15-30-45.json",
        "created_at": "2025-12-02T15:30:45",
        "size": 15234
      }
    ],
    "total": 5
  }
}
```

---

### **7. POST `/api/config/restore`**
**Objetivo**: Restaurar configuração de um backup

**Body**:
```json
{
  "backup_file": "config.backup.2025-12-02_15-30-45.json",
  "create_backup": true
}
```

**Resposta**:
```json
{
  "success": true,
  "message": "Configuração restaurada com sucesso",
  "data": {
    "restored_from": "config.backup.2025-12-02_15-30-45.json",
    "current_backup": "data/config.backup.2025-12-02_15-45-30.json",
    "requires_restart": true
  }
}
```

---

## 🔒 Segurança e Validação

### **Validações Necessárias**

1. **Validação de Tipos**:
   - Números: portas, intervalos, limites
   - Strings: caminhos, URLs, timezones
   - Booleans: flags de habilitação
   - Arrays: listas de horários, canais

2. **Validação de Valores**:
   - Portas: 1-65535
   - Timezones: lista válida de timezones
   - Caminhos: verificar se existem (opcional)
   - URLs: formato válido
   - Horários: formato HH:MM

3. **Validação de Estrutura**:
   - Seções obrigatórias presentes
   - Campos obrigatórios dentro de seções
   - Estrutura de objetos aninhados

### **Backup Automático**

- Criar backup antes de qualquer alteração
- Nome do backup: `config.backup.YYYY-MM-DD_HH-MM-SS.json`
- Manter últimos N backups (configurável, padrão: 10)
- Limpar backups antigos automaticamente

### **Segurança**

- **Autenticação**: Considerar autenticação para endpoints de escrita (PATCH, PUT, POST)
- **Validação de Permissões**: Verificar se usuário tem permissão para alterar config
- **Rate Limiting**: Limitar número de alterações por minuto
- **Logging**: Registrar todas as alterações de configuração

---

## 🔄 Recarregamento Dinâmico

### **Seções que Podem ser Recarregadas sem Restart**

- `api` (parcial - apenas algumas configurações)
- `logging` (pode requerer reinício do logger)
- `notifications`
- `logs`
- `chat_monitoring`

### **Seções que Requerem Restart**

- `server` - Requer reinício completo
- `scheduler` - Requer reinício do scheduler
- `squad_sync` - Requer reinício do serviço
- `survival_sync` - Requer reinício do serviço
- `rankings_sync` - Requer reinício do serviço
- `chest_sync` - Requer reinício do serviço
- `player_gps_sync` - Requer reinício do serviço
- `player_skills_sync` - Requer reinício do serviço
- `vehicle_verification` - Requer reinício do serviço

### **Implementação de Recarregamento**

```python
def reload_config_section(section_name: str):
    """Recarregar seção específica da configuração"""
    # 1. Carregar nova configuração do arquivo
    # 2. Atualizar variável global `config`
    # 3. Notificar serviços que usam essa seção
    # 4. Reiniciar serviços se necessário
```

---

## 📝 Estrutura de Resposta Padrão

### **Sucesso**
```json
{
  "success": true,
  "message": "Mensagem descritiva",
  "data": {
    // Dados específicos da operação
  },
  "timestamp": 1701504000
}
```

### **Erro**
```json
{
  "success": false,
  "error": "Mensagem de erro descritiva",
  "details": {
    // Detalhes adicionais do erro (opcional)
    "field": "api.port",
    "expected": "number between 1 and 65535",
    "received": "30000"
  },
  "timestamp": 1701504000
}
```

---

## 🎨 Casos de Uso

### **1. Alterar Porta da API**
```http
PATCH /api/config
Content-Type: application/json

{
  "sections": {
    "api": {
      "port": 3001
    }
  }
}
```

### **2. Desabilitar Scheduler**
```http
PATCH /api/config
Content-Type: application/json

{
  "sections": {
    "scheduler": {
      "enabled": false
    }
  }
}
```

### **3. Adicionar Horário de Restart**
```http
PATCH /api/config
Content-Type: application/json

{
  "sections": {
    "scheduler": {
      "restart_times": ["02:00", "03:00", "04:00", "24:00"]
    }
  }
}
```

### **4. Atualizar Múltiplas Seções**
```http
PATCH /api/config
Content-Type: application/json

{
  "sections": {
    "api": {
      "port": 3001,
      "debug": true
    },
    "logging": {
      "log_level": "debug"
    },
    "scheduler": {
      "enabled": false
    }
  },
  "create_backup": true
}
```

### **5. Obter Apenas Seção Específica**
```http
GET /api/config?section=scheduler
```

### **6. Restaurar de Backup**
```http
POST /api/config/restore
Content-Type: application/json

{
  "backup_file": "config.backup.2025-12-02_15-30-45.json"
}
```

---

## ⚠️ Considerações Importantes

### **1. Thread Safety**
- Garantir que alterações não causem race conditions
- Usar locks ao atualizar configuração global

### **2. Validação de Caminhos**
- Validar se caminhos de diretórios existem (opcional)
- Alertar se caminhos não existem, mas não bloquear

### **3. Impacto em Serviços**
- Identificar quais serviços são afetados por cada alteração
- Notificar serviços para recarregar configuração
- Reiniciar serviços quando necessário

### **4. Backup e Rollback**
- Sempre criar backup antes de alterar
- Permitir rollback fácil
- Manter histórico de alterações

### **5. Performance**
- Cache da configuração em memória
- Recarregar apenas quando necessário
- Validar antes de salvar no disco

---

## 🚀 Implementação Sugerida

### **Fase 1: Endpoints Básicos**
1. `GET /api/config` - Leitura completa
2. `GET /api/config?section=X` - Leitura de seção
3. `PATCH /api/config` - Atualização parcial

### **Fase 2: Backup e Restore**
4. Sistema de backup automático
5. `GET /api/config/backup` - Listar backups
6. `POST /api/config/restore` - Restaurar backup

### **Fase 3: Validação Avançada**
7. Validação completa de tipos e valores
8. Validação de estrutura
9. Mensagens de erro detalhadas

### **Fase 4: Recarregamento Dinâmico**
10. `POST /api/config/reload` - Recarregar sem restart
11. Notificação de serviços
12. Reinício automático de serviços quando necessário

### **Fase 5: Segurança**
13. Autenticação (se necessário)
14. Rate limiting
15. Logging de alterações

---

## 📚 Documentação

### **Endpoints a Documentar**

1. **GET `/api/config`** - Obter configuração
2. **GET `/api/config/sections`** - Listar seções
3. **PATCH `/api/config`** - Atualizar parcialmente
4. **PUT `/api/config`** - Substituir completamente
5. **POST `/api/config/reload`** - Recarregar configuração
6. **GET `/api/config/backup`** - Listar backups
7. **POST `/api/config/restore`** - Restaurar backup

### **Exemplos para Postman**

- Criar collection com todos os endpoints
- Incluir exemplos de requisições
- Incluir exemplos de respostas

---

## ❓ Decisões Pendentes

1. **Autenticação**: Implementar autenticação para endpoints de escrita?
2. **Validação de Caminhos**: Validar se caminhos existem ou apenas alertar?
3. **Recarregamento Automático**: Recarregar automaticamente após salvar ou apenas notificar?
4. **Limite de Backups**: Quantos backups manter? (sugestão: 10)
5. **Formato de Backup**: Apenas JSON ou incluir metadados?

---

## ✅ Checklist de Implementação

- [ ] Criar função de validação de configuração
- [ ] Criar função de backup automático
- [ ] Implementar `GET /api/config`
- [ ] Implementar `GET /api/config/sections`
- [ ] Implementar `PATCH /api/config`
- [ ] Implementar `PUT /api/config`
- [ ] Implementar `POST /api/config/reload`
- [ ] Implementar `GET /api/config/backup`
- [ ] Implementar `POST /api/config/restore`
- [ ] Adicionar validações
- [ ] Adicionar logging
- [ ] Criar documentação
- [ ] Adicionar ao Postman collection
- [ ] Testes

---

**Última atualização**: 02/12/2025

