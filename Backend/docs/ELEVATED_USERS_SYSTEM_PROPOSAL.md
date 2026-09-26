# 🎯 Proposta: Sistema de Gerenciamento de Elevated Users

## 📋 Visão Geral

Sistema para gerenciar a tabela `elevated_users` no `SCUM.db`, que concede privilégios de super usuário no jogo. **Operações só podem ser executadas quando o servidor está parado** para evitar corrupção do banco de dados.

---

## 🏗️ Arquitetura Proposta

### **Componentes Principais**

```
core/elevated_users/
├── __init__.py
├── elevated_users_manager.py    # Gerenciador principal
└── elevated_users_validator.py  # Validações e verificações
```

### **Fluxo de Operação**

```
1. Cliente faz requisição (POST /api/players/{steam_id}/elevated-user)
   ↓
2. Sistema valida Steam ID (formato e existência na tabela players do SSM.db)
   ↓
3. Sistema verifica status do servidor
   ↓
4a. Se servidor PARADO:
    → Atualiza coluna elevated_user na tabela players (SSM.db)
    → Faz backup do SCUM.db
    → Executa operação no SCUM.db (INSERT/DELETE na elevated_users)
    → Envia notificação Discord: "✅ Elevated user sincronizado"
    → Retorna sucesso
   ↓
4b. Se servidor RODANDO:
    → Atualiza coluna elevated_user na tabela players (SSM.db)
    → Se elevated_user = 1: Cria/verifica registro na tabela elevated_user com synced = 0
    → Se elevated_user = 0: Marca para remoção (se existir registro com synced = 1)
    → Envia notificação Discord: "⏳ Elevated user agendado (aguardando servidor parar)"
    → Retorna sucesso (com aviso de que será sincronizado depois)
   ↓
5. Quando servidor PARA (stop/restart):
    → Sistema detecta mudanças pendentes (compara SSM.db com SCUM.db)
    → Se houver diferenças:
        → Faz backup do SCUM.db
        → Sincroniza todas as mudanças pendentes com SCUM.db
        → Envia notificação Discord: "✅ Sincronização concluída"
    → Se não houver diferenças:
        → Nada a fazer (já está sincronizado)
```

---

## 🔒 **Regras de Segurança**

### **1. Verificação Obrigatória de Servidor Parado**

```python
def _ensure_server_stopped(self) -> Tuple[bool, str]:
    """
    Verifica se o servidor está parado.
    Retorna: (is_stopped: bool, error_message: str)
    """
    if server_manager._is_service_running():
        return False, "Servidor deve estar parado para modificar elevated_users"
    return True, ""
```

### **2. Validação de Steam ID**

- Formato: `7656119XXXXXXXXXX` (17 dígitos)
- Verificar se existe na tabela `players` do SSM.db (obrigatório)
- O Steam ID deve estar cadastrado na tabela `players` antes de ser marcado como elevated_user

### **3. Operações Atômicas**

- Usar transações SQLite
- Rollback em caso de erro
- Verificar integridade após operação

---

## 📡 **Endpoints da API Implementados**

### **1. Status do Sistema**

```
GET /api/elevated-users/status
```

**Descrição:** Obtém o status completo do sistema de elevated users, incluindo estado do servidor, quantidade de elevated users e informações sobre sincronização.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "server_status": "stopped",
    "is_running": false,
    "can_modify": true,
    "total_elevated_users": 2,
    "pending_changes": 0,
    "scum_db_path": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db",
    "scum_db_exists": true,
    "ssm_db_path": "data/SSM.db",
    "last_sync": "2025-01-15T10:30:00Z"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Resposta de Erro (500):**
```json
{
  "success": false,
  "error": "ElevatedUsersManager não inicializado"
}
```

---

### **2. Listar Elevated Users**

```
GET /api/elevated-users/list
```

**Descrição:** Lista todos os elevated users cadastrados no sistema, tanto no SSM.db quanto no SCUM.db.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "elevated_users": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "is_synced": true,
        "created_at": "2025-01-15T10:00:00Z",
        "synced_at": "2025-01-15T10:05:00Z"
      },
      {
        "steam_id": "76561198042887008",
        "player_name": "Mantones",
        "is_synced": true,
        "created_at": "2025-01-15T09:00:00Z",
        "synced_at": "2025-01-15T09:05:00Z"
      }
    ],
    "total": 2
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Nota:** Este endpoint funciona mesmo com servidor rodando (apenas leitura).

---

### **3. Marcar/Desmarcar Elevated User**

```
POST /api/players/<steam_id>/elevated-user
```

**Descrição:** Marca ou desmarca um jogador como elevated user. Se o servidor estiver rodando, a mudança será agendada e sincronizada automaticamente quando o servidor parar.

**Parâmetros de URL:**
- `steam_id` (string, obrigatório): Steam ID do jogador (17 dígitos)

**Body:**
```json
{
  "elevated_user": 1,
  "reason": "Promovido a administrador"
}
```

**Campos do Body:**
- `elevated_user` (integer, opcional): `1` para marcar como elevated, `0` para desmarcar. Padrão: `1`
- `reason` (string, opcional): Motivo da alteração

**Resposta de Sucesso (200) - Servidor Parado:**
```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "player_name": "Pedreiro",
    "elevated_user": 1,
    "action": "added",
    "synced": true,
    "message": "Elevated user adicionado e sincronizado com sucesso",
    "backup_created": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db.backup.20250115103000"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Resposta de Sucesso (200) - Servidor Rodando (Agendado):**
```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "player_name": "Pedreiro",
    "elevated_user": 1,
    "action": "scheduled",
    "synced": false,
    "message": "Elevated user agendado. Será sincronizado quando o servidor parar",
    "pending_sync": true
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Respostas de Erro:**
- `400`: Steam ID inválido, jogador não encontrado na tabela players, ou erro de validação
- `500`: Erro interno do servidor

---

### **4. Forçar Sincronização**

```
POST /api/elevated-users/sync
```

**Descrição:** Força a sincronização imediata de todas as mudanças pendentes. Requer que o servidor esteja parado.

**Body:** (opcional)
```json
{}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "changes_count": 2,
    "added": 1,
    "removed": 1,
    "backup_created": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db.backup.20250115103000",
    "message": "Sincronização concluída: 1 adicionado, 1 removido",
    "synced_at": "2025-01-15T10:30:00Z"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Resposta de Sucesso (200) - Sem Mudanças:**
```json
{
  "success": true,
  "data": {
    "changes_count": 0,
    "added": 0,
    "removed": 0,
    "message": "Nenhuma mudança pendente para sincronizar"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Respostas de Erro:**
- `400`: Servidor está rodando (não é possível sincronizar)
- `500`: Erro interno do servidor

---

## 🗄️ **Estrutura de Dados**

### **Tabela `elevated_users` (SCUM.db)**
```sql
CREATE TABLE elevated_users (
    user_id TEXT PRIMARY KEY
)
```

### **Tabela de Auditoria (SSM.db) - Opcional**

Se quisermos manter histórico no SSM.db:

```sql
CREATE TABLE IF NOT EXISTS elevated_users_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    player_name TEXT,
    action TEXT NOT NULL, -- 'add' ou 'remove'
    reason TEXT,
    performed_by TEXT,    -- quem executou (se houver autenticação)
    performed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (steam_id) REFERENCES players (steam_id)
);

CREATE INDEX idx_elevated_users_audit_steam_id ON elevated_users_audit(steam_id);
CREATE INDEX idx_elevated_users_audit_performed_at ON elevated_users_audit(performed_at);
```

---

## 🔧 **Implementação Técnica**

### **Classe `ElevatedUsersManager`**

```python
class ElevatedUsersManager:
    def __init__(self, config, server_manager, path_helper):
        self.config = config
        self.server_manager = server_manager
        self.path_helper = path_helper
        self.scum_db_path = path_helper.get_scum_db_path()
        self.logger = StructuredLogger()
    
    def add_elevated_user(self, steam_id: str, reason: str = None) -> Dict[str, Any]:
        """Adicionar usuário à tabela elevated_users"""
        # 1. Verificar servidor parado
        # 2. Validar Steam ID
        # 3. Verificar se já existe
        # 4. Inserir no SCUM.db
        # 5. Registrar auditoria (opcional)
        # 6. Retornar resultado
    
    def remove_elevated_user(self, steam_id: str, reason: str = None) -> Dict[str, Any]:
        """Remover usuário da tabela elevated_users"""
        # Similar ao add, mas com DELETE
    
    def list_elevated_users(self) -> List[Dict[str, Any]]:
        """Listar todos os elevated users com informações do user/user_profile"""
        # JOIN com user e user_profile para obter nomes
    
    def is_elevated(self, steam_id: str) -> bool:
        """Verificar se um Steam ID está na lista"""
    
    def get_status(self) -> Dict[str, Any]:
        """Obter status do sistema"""
```

---

## ⚠️ **Considerações Importantes**

### **1. Backup do SCUM.db**

Antes de modificar, fazer backup?

```python
def _backup_scum_db(self) -> str:
    """Criar backup do SCUM.db antes de modificar"""
    backup_path = f"{self.scum_db_path}.backup.{timestamp}"
    shutil.copy2(self.scum_db_path, backup_path)
    return backup_path
```

### **2. Timeout de Bloqueio**

O SCUM.db pode estar temporariamente bloqueado mesmo com servidor parado (processo finalizando). Implementar retry:

```python
def _wait_for_db_unlock(self, max_retries=5, delay=1):
    """Aguardar banco ficar desbloqueado"""
    for i in range(max_retries):
        try:
            conn = sqlite3.connect(self.scum_db_path, timeout=1)
            conn.close()
            return True
        except sqlite3.OperationalError:
            time.sleep(delay)
    return False
```

### **3. Integração com Sistema de Permissões**

- Sincronizar com `player_permissions` do SSM.db?
- Quando adicionar `elevated_user`, também adicionar permissão `admin` no SSM?
- Ou manter separado (elevated_users = privilégios nativos do jogo)?

---

## 📝 **Exemplo de Uso**

### **Adicionar Elevated User**

```bash
curl -X POST http://localhost:3000/api/elevated-users/add \
  -H "Content-Type: application/json" \
  -d '{
    "steam_id": "76561198040636105",
    "reason": "Promovido a administrador do servidor"
  }'
```

### **Remover Elevated User**

```bash
curl -X POST http://localhost:3000/api/elevated-users/remove \
  -H "Content-Type: application/json" \
  -d '{
    "steam_id": "76561198040636105",
    "reason": "Removido de administrador"
  }'
```

### **Listar Elevated Users**

```bash
curl http://localhost:3000/api/elevated-users/list
```

---

## ✅ **Decisões Tomadas**

1. **Backup automático?** ✅ **SIM** - Fazer backup do SCUM.db antes de modificar
2. **Auditoria no SSM.db?** ❌ **NÃO** - Não há necessidade de histórico
3. **Sincronização com `player_permissions`?** ❌ **NÃO** - São sistemas diferentes e independentes
4. **Notificações Discord?** ✅ **SIM** - Criar webhook `log-ssm` no webhooks.json
   - URL: `https://discordapp.com/api/webhooks/1440426078270128240/7TJIO_WXLkk5gv8TitbYzd_TdrwIQDC292hw3hAirC_2lm5hOfudk---9ifYG_rnGzV3`
5. **Validação de existência?** ✅ **SIM** - Verificar se Steam ID existe na tabela `players` do SSM.db
6. **Coluna na tabela `players`?** ✅ **SIM** - Criar coluna `elevated_user` (0 = não, 1 = sim)

---

## 🎯 **Sistema de Agendamento/Sincronização Automática**

### **Conceito**

Permitir que o usuário marque `elevated_user = 1` na tabela `players` do SSM.db mesmo quando o servidor está rodando. O sistema sincroniza automaticamente quando:

1. **Servidor é parado** (via `/api/server/stop`)
2. **Servidor é reiniciado** (via `/api/server/restart` ou agendamento)
3. **Servidor inicia** (após restart)

### **Fluxo de Sincronização**

```
1. Usuário marca elevated_user = 1 na tabela players (SSM.db)
   ↓
2. Sistema verifica status do servidor
   ↓
3a. Se servidor PARADO:
    → Sincroniza imediatamente com SCUM.db
    → Envia notificação Discord: "✅ Elevated user sincronizado"
   ↓
3b. Se servidor RODANDO:
    → Apenas marca na tabela players
    → Envia notificação Discord: "⏳ Elevated user agendado (aguardando servidor parar)"
   ↓
4. Servidor PARA (stop/restart)
   ↓
5. Sistema detecta mudanças pendentes
   ↓
6. Sincroniza com SCUM.db (INSERT/DELETE na elevated_users)
   ↓
7. Envia notificação Discord: "✅ Elevated user sincronizado com sucesso"
   ↓
8. Servidor INICIA (se foi restart)
```

### **Estrutura de Dados Adicional**

#### **1. Coluna na tabela `players` (SSM.db) - Flag de Controle**

```sql
ALTER TABLE players ADD COLUMN elevated_user INTEGER DEFAULT 0;
-- 0 = não é elevated user (ou foi removido)
-- 1 = é elevated user (marcado pelo usuário)
```

**Propósito:** Flag simples para indicar se o jogador deve ser elevated user.

#### **2. Tabela `elevated_user` (SSM.db) - Tabela de Controle e Sincronização**

```sql
CREATE TABLE IF NOT EXISTS elevated_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    synced INTEGER DEFAULT 0,  -- 0 = agendado, 1 = sincronizado com SCUM.db
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced_at DATETIME,
    FOREIGN KEY (steam_id) REFERENCES players (steam_id),
    UNIQUE(steam_id)
);

CREATE INDEX idx_elevated_user_steam_id ON elevated_user(steam_id);
CREATE INDEX idx_elevated_user_synced ON elevated_user(synced);
```

**Propósito:** 
- Controlar quais Steam IDs devem ser sincronizados
- Rastrear status de sincronização (agendado vs sincronizado)
- Evitar loops e duplicações
- Manter histórico de quando foi marcado e sincronizado

**Colunas:**
- `steam_id`: Steam ID do jogador (FK para `players`)
- `synced`: Status de sincronização
  - `0` = Agendado (ainda não sincronizado com SCUM.db)
  - `1` = Sincronizado (já inserido na tabela `elevated_users` do SCUM.db)
- `created_at`: Quando foi marcado como elevated user
- `synced_at`: Quando foi sincronizado com SCUM.db

#### **3. Lógica de Funcionamento**

**Quando `elevated_user = 0` na tabela `players`:**
- Não faz nada (jogador não é elevated user)
- Se existir registro na tabela `elevated_user` com `synced = 1`, marca para remoção

**Quando `elevated_user = 1` na tabela `players`:**
- Verifica se existe registro na tabela `elevated_user`
- Se **NÃO existe**: Cria registro com `synced = 0` (agendado)
- Se **existe** e `synced = 0`: Já está agendado, aguarda sincronização
- Se **existe** e `synced = 1`: Já está sincronizado, nada a fazer

**Durante sincronização (servidor parado):**
- Busca registros com `synced = 0` na tabela `elevated_user`
- Para cada registro:
  - Insere na tabela `elevated_users` do SCUM.db
  - Atualiza `synced = 1` e `synced_at = NOW()` na tabela `elevated_user` do SSM.db
- Busca registros com `synced = 1` mas `elevated_user = 0` na tabela `players`
- Para cada registro:
  - Remove da tabela `elevated_users` do SCUM.db
  - Remove registro da tabela `elevated_user` do SSM.db (ou marca como removido)

### **Endpoints Adicionais**

#### **1. Marcar/Desmarcar Elevated User (Sempre Disponível)**

```
POST /api/players/{steam_id}/elevated-user
```

**Body:**
```json
{
  "elevated_user": 1,  // 0 ou 1
  "reason": "Promovido a administrador" // opcional
}
```

**Comportamento:**
- Se servidor **PARADO**: Sincroniza imediatamente com SCUM.db
- Se servidor **RODANDO**: Apenas marca na tabela `players`, sincroniza depois

#### **2. Sincronizar Agora (Forçar)**

```
POST /api/elevated-users/sync
```

**Comportamento:**
- Verifica se servidor está parado
- Sincroniza todas as mudanças pendentes
- Retorna lista de operações realizadas

### **Notificações Discord**

#### **1. Notificação de Agendamento**

Quando o usuário marca `elevated_user = 1` mas o servidor está rodando:

```json
{
  "embeds": [{
    "title": "⏳ Elevated User Agendado",
    "description": "Um usuário foi marcado como elevated user, mas a sincronização será feita quando o servidor parar.",
    "color": 16776960, // Amarelo
    "fields": [
      {
        "name": "👤 Jogador",
        "value": "Pedreiro (76561198040636105)",
        "inline": true
      },
      {
        "name": "📊 Status",
        "value": "Aguardando servidor parar",
        "inline": true
      },
      {
        "name": "🕐 Agendado em",
        "value": "18/11/2025 às 14:30:00",
        "inline": false
      }
    ],
    "footer": {
      "text": "Sistema SSM - Elevated Users"
    }
  }]
}
```

#### **2. Notificação de Execução**

Quando a sincronização é executada (servidor parou):

```json
{
  "embeds": [{
    "title": "✅ Elevated User Sincronizado",
    "description": "A sincronização com o SCUM.db foi concluída com sucesso.",
    "color": 65280, // Verde
    "fields": [
      {
        "name": "👤 Jogador",
        "value": "Pedreiro (76561198040636105)",
        "inline": true
      },
      {
        "name": "📊 Ação",
        "value": "Adicionado",
        "inline": true
      },
      {
        "name": "🕐 Sincronizado em",
        "value": "18/11/2025 às 15:45:00",
        "inline": false
      },
      {
        "name": "💾 Backup",
        "value": "SCUM.db.backup.20251118_154500",
        "inline": false
      }
    ],
    "footer": {
      "text": "Sistema SSM - Elevated Users"
    }
  }]
}
```

#### **3. Notificação de Múltiplas Sincronizações**

Quando há várias mudanças pendentes e todas são sincronizadas:

```json
{
  "embeds": [{
    "title": "✅ Sincronização em Lote Concluída",
    "description": "Todas as mudanças pendentes foram sincronizadas com sucesso.",
    "color": 65280,
    "fields": [
      {
        "name": "📊 Total de Operações",
        "value": "3 operações",
        "inline": true
      },
      {
        "name": "➕ Adicionados",
        "value": "2 jogadores",
        "inline": true
      },
      {
        "name": "➖ Removidos",
        "value": "1 jogador",
        "inline": true
      },
      {
        "name": "👥 Jogadores",
        "value": "• Pedreiro (76561198040636105) - Adicionado\n• Reav (76561197963358180) - Adicionado\n• BlueArcher_BR (76561198398160339) - Removido",
        "inline": false
      }
    ],
    "footer": {
      "text": "Sistema SSM - Elevated Users"
    }
  }]
}
```

### **Integração com RestartScheduler**

O `RestartScheduler` pode ter um callback que executa a sincronização:

```python
def on_server_stopped():
    """Callback quando servidor para"""
    result = elevated_users_manager.sync_pending_changes()
    
    # Notificar Discord sobre sincronização
    if result['changes_count'] > 0:
        send_discord_notification(result)

def on_server_started():
    """Callback quando servidor inicia"""
    # Verificar se há mudanças pendentes e notificar
    pending = elevated_users_manager.get_pending_changes()
    if pending:
        send_discord_notification({
            "type": "pending_changes",
            "count": len(pending),
            "message": "Há mudanças pendentes aguardando servidor parar"
        })
```

### **Detecção de Mudanças Pendentes**

Com a nova estrutura, a detecção fica muito mais simples e eficiente:

#### **1. Adições Pendentes**
Jogadores marcados como `elevated_user = 1` mas ainda não sincronizados:

```sql
-- No SSM.db
SELECT eu.steam_id, p.player_name, eu.created_at
FROM elevated_user eu
JOIN players p ON eu.steam_id = p.steam_id
WHERE eu.synced = 0  -- Agendado, aguardando sincronização
```

#### **2. Remoções Pendentes**
Jogadores que foram desmarcados (`elevated_user = 0`) mas ainda estão no SCUM.db:

```sql
-- No SSM.db
SELECT eu.steam_id, p.player_name
FROM elevated_user eu
JOIN players p ON eu.steam_id = p.steam_id
WHERE eu.synced = 1  -- Já sincronizado
AND p.elevated_user = 0  -- Mas foi desmarcado
```

#### **3. Verificação de Integridade**
Verificar se há divergências entre SSM.db e SCUM.db:

```sql
-- Jogadores sincronizados no SSM mas não estão no SCUM.db
SELECT eu.steam_id
FROM elevated_user eu
WHERE eu.synced = 1
AND eu.steam_id NOT IN (
    SELECT user_id FROM elevated_users  -- Consulta no SCUM.db
)
```

#### **3. Status de Sincronização**

Para verificar o status completo de um jogador:

```python
def get_sync_status(steam_id: str) -> Dict[str, Any]:
    """
    Retorna status de sincronização de um jogador
    
    Returns:
        {
            "steam_id": "76561198040636105",
            "marked_in_ssm": True,      # elevated_user = 1 no SSM.db
            "exists_in_scum": True,     # user_id existe no SCUM.db
            "status": "synchronized"    # "synchronized", "pending_add", "pending_remove"
        }
    """
```

**Estados possíveis:**
- `synchronized`: `elevated_user = 1` no SSM.db E existe no SCUM.db → **Nada a fazer**
- `pending_add`: `elevated_user = 1` no SSM.db MAS não existe no SCUM.db → **Precisa sincronizar (INSERT)**
- `pending_remove`: `elevated_user = 0` no SSM.db MAS ainda existe no SCUM.db → **Precisa sincronizar (DELETE)**
- `not_elevated`: `elevated_user = 0` no SSM.db E não existe no SCUM.db → **Nada a fazer**

### **Prevenção de Loops e Duplicação**

O sistema evita loops através de **comparação idempotente** entre as duas tabelas:

#### **1. Detecção de Mudanças Pendentes**

Com a tabela `elevated_user`, a detecção fica muito mais simples:

```python
def get_pending_changes() -> Dict[str, List[Dict[str, Any]]]:
    """
    Detecta mudanças pendentes usando a tabela elevated_user
    
    Returns:
        {
            "to_add": [
                {"steam_id": "76561198040636105", "player_name": "Pedreiro", ...}
            ],
            "to_remove": [
                {"steam_id": "76561197963358180", "player_name": "Reav", ...}
            ]
        }
    """
    with sqlite3.connect(SSM_DB) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Adições pendentes: synced = 0 na tabela elevated_user
        cursor.execute("""
            SELECT eu.steam_id, p.player_name, eu.created_at
            FROM elevated_user eu
            JOIN players p ON eu.steam_id = p.steam_id
            WHERE eu.synced = 0
            AND p.elevated_user = 1
        """)
        to_add = [dict(row) for row in cursor.fetchall()]
        
        # Remoções pendentes: synced = 1 mas elevated_user = 0 na tabela players
        cursor.execute("""
            SELECT eu.steam_id, p.player_name, eu.synced_at
            FROM elevated_user eu
            JOIN players p ON eu.steam_id = p.steam_id
            WHERE eu.synced = 1
            AND p.elevated_user = 0
        """)
        to_remove = [dict(row) for row in cursor.fetchall()]
        
        return {"to_add": to_add, "to_remove": to_remove}
```

#### **2. Verificação Antes de Sincronizar**

Antes de executar qualquer operação, o sistema verifica novamente:

```python
def sync_pending_changes() -> Dict[str, Any]:
    """
    Sincroniza mudanças pendentes (idempotente)
    """
    # 1. Verificar se servidor está parado
    if not _ensure_server_stopped():
        return {"success": False, "error": "Servidor deve estar parado"}
    
    # 2. Detectar mudanças pendentes
    pending = get_pending_changes()
    
    # 3. Se não há mudanças, retornar imediatamente
    if not pending["to_add"] and not pending["to_remove"]:
        return {
            "success": True,
            "message": "Nenhuma mudança pendente",
            "changes_count": 0
        }
    
    # 4. Executar sincronização apenas se houver diferenças
    results = {
        "added": [],
        "removed": [],
        "errors": []
    }
    
    # Adicionar elevated users
    for item in pending["to_add"]:
        steam_id = item["steam_id"]
        try:
            # Inserir no SCUM.db
            insert_into_scum(steam_id)
            
            # Atualizar status na tabela elevated_user
            update_sync_status(steam_id, synced=1)
            
            results["added"].append(steam_id)
        except Exception as e:
            results["errors"].append(f"Erro ao adicionar {steam_id}: {e}")
    
    # Remover elevated users
    for item in pending["to_remove"]:
        steam_id = item["steam_id"]
        try:
            # Remover do SCUM.db
            remove_from_scum(steam_id)
            
            # Remover da tabela elevated_user (ou marcar como removido)
            delete_from_elevated_user(steam_id)
            
            results["removed"].append(steam_id)
        except Exception as e:
            results["errors"].append(f"Erro ao remover {steam_id}: {e}")
    
    # 5. Após sincronizar, verificar novamente para confirmar
    final_check = get_pending_changes()
    if final_check["to_add"] or final_check["to_remove"]:
        # Algo deu errado - registrar erro
        results["errors"].append("Sincronização incompleta detectada")
    
    return results
```

#### **3. Garantia de Idempotência**

A sincronização é **idempotente** - executar múltiplas vezes produz o mesmo resultado:

- **INSERT**: Usa `INSERT OR IGNORE` ou verifica antes de inserir
- **DELETE**: Verifica se existe antes de deletar
- **Comparação**: Sempre compara estado atual antes de agir

```python
def mark_elevated_user(steam_id: str, elevated: bool) -> Dict[str, Any]:
    """Marcar/desmarcar elevated user na tabela players e elevated_user"""
    with sqlite3.connect(SSM_DB) as conn:
        cursor = conn.cursor()
        
        # 1. Atualizar flag na tabela players
        cursor.execute(
            "UPDATE players SET elevated_user = ? WHERE steam_id = ?",
            (1 if elevated else 0, steam_id)
        )
        
        if elevated:
            # 2. Criar/verificar registro na tabela elevated_user
            cursor.execute("""
                INSERT OR IGNORE INTO elevated_user (steam_id, synced)
                VALUES (?, 0)
            """, (steam_id,))
            
            # Verificar se já existe e está sincronizado
            cursor.execute(
                "SELECT synced FROM elevated_user WHERE steam_id = ?",
                (steam_id,)
            )
            row = cursor.fetchone()
            if row and row[0] == 1:
                return {
                    "success": True,
                    "message": "Já está sincronizado",
                    "action": "no_change"
                }
            
            return {
                "success": True,
                "message": "Marcado como elevated user (agendado)" if not row else "Já estava agendado",
                "action": "marked"
            }
        else:
            # 3. Se desmarcou, verificar se precisa remover
            cursor.execute(
                "SELECT synced FROM elevated_user WHERE steam_id = ?",
                (steam_id,)
            )
            row = cursor.fetchone()
            if row and row[0] == 1:
                # Está sincronizado, precisa remover quando servidor parar
                return {
                    "success": True,
                    "message": "Marcado para remoção (aguardando servidor parar)",
                    "action": "marked_for_removal"
                }
            elif row:
                # Estava agendado, apenas remove o registro
                cursor.execute(
                    "DELETE FROM elevated_user WHERE steam_id = ?",
                    (steam_id,)
                )
                return {
                    "success": True,
                    "message": "Removido (não estava sincronizado)",
                    "action": "removed"
                }
        
        conn.commit()
        return {"success": True, "action": "updated"}
```

#### **4. Fluxo Completo de Prevenção de Loop**

```
1. Servidor PARA
   ↓
2. Sistema chama sync_pending_changes()
   ↓
3. get_pending_changes() compara SSM.db vs SCUM.db
   ↓
4. Se não há diferenças:
    → Retorna "Nenhuma mudança pendente"
    → NÃO executa sincronização
    → FIM (sem loop)
   ↓
5. Se há diferenças:
    → Executa sincronização
    → Após sincronizar, verifica novamente
    → Se ainda há diferenças: ERRO (algo deu errado)
    → Se não há diferenças: SUCESSO (sincronizado)
    → FIM (não executa novamente porque não há mais diferenças)
```

#### **5. Proteção Adicional**

- **Flag de sincronização em andamento**: Evita execuções simultâneas
- **Timeout**: Se sincronização demorar muito, cancela
- **Log de última sincronização**: Registrar quando foi a última vez que sincronizou

```python
class ElevatedUsersManager:
    def __init__(self):
        self._sync_in_progress = False
        self._last_sync_timestamp = None
    
    def sync_pending_changes(self):
        # Evitar execuções simultâneas
        if self._sync_in_progress:
            return {"success": False, "error": "Sincronização já em andamento"}
        
        try:
            self._sync_in_progress = True
            # ... executar sincronização ...
            self._last_sync_timestamp = datetime.now()
        finally:
            self._sync_in_progress = False
```

---

## ✅ **Checklist de Implementação**

- [ ] Criar módulo `core/elevated_users/`
- [ ] Implementar `ElevatedUsersManager`
- [ ] Implementar validações
- [ ] Criar endpoints da API
- [ ] Adicionar verificação de servidor parado
- [ ] Implementar auditoria (se decidido)
- [ ] Adicionar documentação
- [ ] Testes de integração

---

**Próximo passo:** Revisar esta proposta e decidir sobre as questões acima antes de implementar.

