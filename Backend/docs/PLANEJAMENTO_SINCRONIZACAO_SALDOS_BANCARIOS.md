# 💰 Planejamento: Sincronização Periódica de Saldos Bancários

## 📋 Objetivo

Criar um serviço de sincronização periódica que extrai os saldos das contas bancárias do `SCUM.db` e salva no `SSM.db`, permitindo consultas rápidas e histórico de saldos.

---

## 🎯 Requisitos

### Funcionalidades
1. ✅ Extrair saldos bancários do `SCUM.db` periodicamente
2. ✅ Salvar dados no `SSM.db` em tabela dedicada
3. ✅ Sincronização configurável (padrão: a cada 4 horas)
4. ✅ Auto-start opcional
5. ✅ Logging estruturado
6. ✅ Status e controle (start/stop)

### Dados a Sincronizar
- **Steam ID** do jogador
- **Nome do jogador**
- **Número da conta bancária**
- **Saldo Money** (currency_type = 1)
- **Saldo Gold** (currency_type = 2)
- **Saldo Total** (Money + Gold)
- **Timestamp** da sincronização

---

## 🗄️ Estrutura da Tabela no SSM.db

### Tabela: `bank_accounts_snapshot`

```sql
CREATE TABLE IF NOT EXISTS bank_accounts_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Identificação do jogador
    steam_id TEXT NOT NULL,
    player_name TEXT,
    
    -- Dados da conta bancária
    account_number TEXT,
    money_balance REAL DEFAULT 0,
    gold_balance REAL DEFAULT 0,
    total_balance REAL DEFAULT 0,
    
    -- Metadados
    snapshot_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Relacionamento com tabela players
    FOREIGN KEY (steam_id) REFERENCES players(steam_id),
    
    -- Índices para performance
    UNIQUE(steam_id, snapshot_at)
);

CREATE INDEX IF NOT EXISTS idx_bank_accounts_steam_id ON bank_accounts_snapshot(steam_id);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_snapshot_at ON bank_accounts_snapshot(snapshot_at);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_total_balance ON bank_accounts_snapshot(total_balance DESC);
```

### Estratégia de Armazenamento

**Opção 1: Snapshot (Recomendada)**
- Armazena histórico completo de cada sincronização
- Permite análise de evolução dos saldos ao longo do tempo
- Tabela: `bank_accounts_snapshot`
- **Vantagem**: Histórico completo, análise temporal

**Opção 2: Último Estado**
- Mantém apenas o estado mais recente
- Atualiza registros existentes
- Tabela: `bank_accounts`
- **Vantagem**: Menos espaço, mais rápido

**Decisão**: Usar **Opção 1 (Snapshot)** para manter histórico, mas também criar uma view ou função para obter o estado atual.

---

## 🏗️ Arquitetura do Serviço

### Classe: `BankAccountSyncService`

**Localização**: `core/banking/bank_account_sync_service.py`

### Estrutura da Classe

```python
class BankAccountSyncService:
    """Sincroniza saldos bancários do SCUM.db para o SSM.db"""
    
    def __init__(self, config, path_helper, logger):
        # Configuração
        # Caminhos dos bancos
        # Scheduler
        # Estado (is_running, last_sync_info)
    
    def ensure_table(self):
        """Garantir que a tabela existe"""
    
    def sync_once(self) -> Dict[str, Any]:
        """Executar uma sincronização"""
        # 1. Query no SCUM.db
        # 2. Processar dados
        # 3. Inserir no SSM.db
    
    def start(self) -> Dict[str, Any]:
        """Iniciar sincronização periódica"""
    
    def stop(self):
        """Parar sincronização"""
    
    def get_status(self) -> Dict[str, Any]:
        """Obter status do serviço"""
```

---

## 📝 Query SQL

### Query de Extração (SCUM.db)

**IMPORTANTE**: A sincronização só inclui jogadores que estão na tabela `players` do SSM.db.

```sql
-- 1. Primeiro, obter steam_ids válidos da tabela players (SSM.db)
SELECT steam_id FROM players

-- 2. Query no SCUM.db filtrada por steam_ids válidos
SELECT DISTINCT
    up.user_id as steam_id,
    up.name as player_name,
    bar.bank_account_number,
    barc.currency_type,
    barc.account_balance
FROM user_profile up
INNER JOIN bank_account_registry bar ON up.id = bar.account_owner_user_profile_id
INNER JOIN bank_account_registry_currencies barc ON bar.id = barc.bank_account_id
WHERE barc.account_balance > 0
  AND up.user_id IN (lista_de_steam_ids_da_tabela_players)
ORDER BY up.name, barc.currency_type
```

### Processamento
1. Agrupar por `steam_id`
2. Separar `money_balance` (currency_type = 1) e `gold_balance` (currency_type = 2)
3. Calcular `total_balance = money_balance + gold_balance`

### Inserção (SSM.db)

```sql
INSERT INTO bank_accounts_snapshot 
    (steam_id, player_name, account_number, money_balance, gold_balance, total_balance, snapshot_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
```

---

## ⚙️ Configuração

### Arquivo: `data/config.json`

```json
{
  "bank_account_sync": {
    "enabled": true,
    "auto_start": true,
    "sync_interval_hours": 4,
    "scum_db_path": null,
    "ssm_db_path": null,
    "description": "Sincronização periódica de saldos bancários do SCUM.db para SSM.db - executa a cada 4 horas"
  }
}
```

### Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `enabled` | boolean | `true` | Habilitar/desabilitar serviço |
| `auto_start` | boolean | `true` | Iniciar automaticamente ao iniciar aplicação |
| `sync_interval_hours` | integer | `4` | Intervalo entre sincronizações (em horas) |
| `scum_db_path` | string | `null` | Caminho do SCUM.db (usa padrão se null) |
| `ssm_db_path` | string | `null` | Caminho do SSM.db (usa padrão se null) |

---

## 🔄 Fluxo de Execução

### 1. Inicialização

```
main.py inicia
    ↓
BankAccountSyncService é criado
    ↓
Verifica se enabled = true
    ↓
Se auto_start = true, chama start()
```

### 2. Sincronização Periódica

```
Scheduler dispara (a cada 4 horas)
    ↓
sync_once() é executado
    ↓
1. Busca steam_ids válidos da tabela players (SSM.db)
    ↓
2. Conecta ao SCUM.db (read-only)
    ↓
3. Executa query de extração (filtrada por steam_ids válidos)
    ↓
4. Processa e agrupa dados por jogador
    ↓
5. Conecta ao SSM.db
    ↓
6. Insere snapshot na tabela
    ↓
7. Atualiza last_sync_info
    ↓
8. Log do resultado
```

**Filtro de Jogadores:**
- Apenas jogadores que existem na tabela `players` do SSM.db são sincronizados
- Isso garante consistência com o sistema de gerenciamento de jogadores
- Evita sincronizar dados de jogadores que não estão no sistema

### 3. Tratamento de Erros

- Erros de conexão: Log e retry na próxima execução
- Erros de query: Log detalhado e continuar
- Erros de inserção: Log e rollback se necessário

---

## 📊 Estrutura de Dados

### Entrada (SCUM.db)

```python
{
    'steam_id': '76561198012345678',
    'player_name': 'Jogador1',
    'bank_account_number': '12345',
    'currency_type': 1,  # 1 = Money, 2 = Gold
    'account_balance': 50000.0
}
```

### Processamento

```python
{
    'steam_id': '76561198012345678',
    'player_name': 'Jogador1',
    'account_number': '12345',
    'money_balance': 50000.0,
    'gold_balance': 0.0,
    'total_balance': 50000.0
}
```

### Saída (SSM.db)

```python
{
    'id': 1,
    'steam_id': '76561198012345678',
    'player_name': 'Jogador1',
    'account_number': '12345',
    'money_balance': 50000.0,
    'gold_balance': 0.0,
    'total_balance': 50000.0,
    'snapshot_at': '2025-01-27T10:00:00',
    'created_at': '2025-01-27T10:00:00'
}
```

---

## 🔌 Integração com main.py

### 1. Import

```python
from core.banking.bank_account_sync_service import BankAccountSyncService
```

### 2. Inicialização

```python
# Variável global
bank_account_sync_service = None

# Na função init_components()
bank_account_sync_service = BankAccountSyncService(config, path_helper, logger)
logger.info("BankAccountSyncService inicializado")
```

### 3. Auto-start

```python
# Na função start_all_services()
bank_account_sync_config = config.get('bank_account_sync', {})
if bank_account_sync_service.enabled and bank_account_sync_config.get('auto_start', True):
    bank_start_result = bank_account_sync_service.start()
    if bank_start_result.get('success'):
        logger.info("BankAccountSyncService iniciado automaticamente")
    else:
        logger.warn(f"Falha ao iniciar BankAccountSyncService: {bank_start_result.get('message')}")
```

---

## 📈 Métricas e Logging

### Logs Estruturados

```python
# Inicialização
logger.info("BankAccountSyncService inicializado", {
    "enabled": True,
    "auto_start": True,
    "sync_interval_hours": 4
})

# Sincronização bem-sucedida
logger.info("Sincronização de saldos bancários concluída", {
    "rows_processed": 150,
    "snapshot_at": "2025-01-27T10:00:00",
    "elapsed_seconds": 2.345
})

# Erro
logger.error("Erro durante sincronização de saldos bancários", {
    "error": "SCUM.db não encontrado"
})
```

### Status do Serviço

```python
{
    "enabled": True,
    "is_running": True,
    "sync_interval_hours": 4,
    "last_sync": {
        "timestamp": "2025-01-27T10:00:00",
        "status": "success",
        "details": {
            "rows_processed": 150,
            "elapsed_seconds": 2.345
        }
    }
}
```

---

## 🧪 Testes e Validação

### Cenários de Teste

1. **Sincronização bem-sucedida**
   - Verificar se dados foram inseridos corretamente
   - Verificar se timestamps estão corretos

2. **Múltiplas sincronizações**
   - Verificar se histórico é mantido
   - Verificar se não há duplicatas

3. **Jogador com Money e Gold**
   - Verificar se ambos os saldos são capturados
   - Verificar se total_balance está correto

4. **Jogador sem saldo**
   - Verificar se não aparece na sincronização (filtro > 0)

5. **Erro de conexão**
   - Verificar se erro é logado
   - Verificar se serviço continua rodando

---

## 📚 Consultas Úteis

### Obter Saldo Atual de um Jogador

```sql
SELECT * FROM bank_accounts_snapshot
WHERE steam_id = ?
ORDER BY snapshot_at DESC
LIMIT 1;
```

### Top 10 Maiores Saldos (Última Sincronização)

```sql
SELECT * FROM bank_accounts_snapshot
WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM bank_accounts_snapshot)
ORDER BY total_balance DESC
LIMIT 10;
```

### Evolução do Saldo de um Jogador

```sql
SELECT snapshot_at, total_balance, money_balance, gold_balance
FROM bank_accounts_snapshot
WHERE steam_id = ?
ORDER BY snapshot_at ASC;
```

### Saldo Total do Servidor (Última Sincronização)

```sql
SELECT 
    SUM(money_balance) as total_money,
    SUM(gold_balance) as total_gold,
    SUM(total_balance) as total_all
FROM bank_accounts_snapshot
WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM bank_accounts_snapshot);
```

---

## 🚀 Implementação

### Ordem de Implementação

1. ✅ Criar estrutura de diretório `core/banking/`
2. ✅ Criar `bank_account_sync_service.py`
3. ✅ Implementar `ensure_table()`
4. ✅ Implementar `sync_once()`
5. ✅ Implementar `start()` e `stop()`
6. ✅ Implementar `get_status()`
7. ✅ Adicionar configuração no `config.json`
8. ✅ Integrar no `main.py`
9. ✅ Testar sincronização manual
10. ✅ Testar sincronização periódica

---

## ⚠️ Considerações

### Performance
- Query usa JOINs, mas com índices adequados deve ser rápida
- Inserção em batch pode ser otimizada se necessário
- Considerar limpeza de snapshots antigos (opcional)
- **✅ Cópia Compartilhada**: O serviço já usa automaticamente o `ScumDbSharedCopyManager`
  - A cópia do SCUM.db é compartilhada entre todos os serviços
  - Reduz carga no disco e melhora performance
  - Configurado em `scum_db_shared_copy` no `config.json`
  - O `scum_db_readonly_connection` já integra isso automaticamente

### Consistência
- Usar transações para garantir atomicidade
- Tratar casos onde jogador tem múltiplas contas (se aplicável)

### Manutenção
- Considerar limpeza automática de snapshots muito antigos
- Considerar compactação de histórico (manter apenas últimas N sincronizações)

### Integração com Cópia Compartilhada

O serviço **já utiliza automaticamente** a cópia compartilhada do SCUM.db através do `scum_db_readonly_connection`:

```python
# No sync_once(), usar:
from utils.scum_db_helper import scum_db_readonly_connection

with scum_db_readonly_connection(self.scum_db_path) as conn:
    # A conexão já usa a cópia compartilhada se habilitada
    # Não precisa fazer nada especial!
```

**Vantagens:**
- ✅ Reutiliza cópia já criada por outros serviços (GPS, Survival Stats, etc.)
- ✅ Reduz I/O no disco
- ✅ Melhora performance quando múltiplos serviços rodam simultaneamente
- ✅ Configuração centralizada em `scum_db_shared_copy`

**Configuração existente:**
```json
{
  "scum_db_shared_copy": {
    "enabled": true,
    "temp_dir": "data/temp",
    "max_copy_age_seconds": 120,
    "cleanup_orphaned_copies": true,
    "max_orphan_age_hours": 1,
    "fallback_to_direct": true
  }
}
```

---

## 📝 Checklist de Implementação

- [ ] Criar diretório `core/banking/`
- [ ] Criar `__init__.py` em `core/banking/`
- [ ] Implementar `BankAccountSyncService`
- [ ] Adicionar configuração no `config.json`
- [ ] Integrar no `main.py`
- [ ] Testar sincronização manual
- [ ] Testar sincronização periódica
- [ ] Documentar uso
- [ ] Adicionar consultas úteis na documentação

---

**Última Atualização**: 2025-01-27  
**Status**: Planejamento Completo - Pronto para Implementação
