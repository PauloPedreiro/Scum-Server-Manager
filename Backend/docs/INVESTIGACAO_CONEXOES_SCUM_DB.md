# Investigação: Conexões Diretas ao SCUM.db

## Resumo
Este documento identifica todos os processos que estão conectando diretamente ao banco de dados `SCUM.db` sem usar o sistema de cópia compartilhada (`ScumDbSharedCopyManager`), o que pode resultar na criação de arquivos WAL/SHM.

## Processos Identificados

### 1. **VehicleProcessor** (`core/logs/vehicle_processor.py`)
**Status:** ⚠️ **CRÍTICO - Múltiplas conexões diretas**

**Conexões diretas encontradas:**
- **Linha 49**: `map_containers_to_vehicles()` - `sqlite3.connect(self.scum_db_path)`
- **Linha 364**: `check_vehicle_exists()` - `sqlite3.connect(self.scum_db_path)`
- **Linha 399**: `check_vehicles_batch()` - `sqlite3.connect(self.scum_db_path)`

**Problema:**
- Este processador é usado pelo `LogProcessor` para processar logs de `chest_ownership_*.log`
- Faz consultas frequentes ao SCUM.db para mapear containers para veículos
- **NÃO usa** `scum_db_readonly_connection()` ou `ScumDbSharedCopyManager`
- Pode criar arquivos WAL/SHM quando o servidor SCUM está rodando

**Impacto:**
- Alto - Processa logs em tempo real, fazendo múltiplas consultas ao banco

---

### 2. **ElevatedUsersManager** (`core/elevated_users/elevated_users_manager.py`)
**Status:** ⚠️ **CRÍTICO - Conexões diretas para escrita**

**Conexões diretas encontradas:**
- **Linha 105**: `_wait_for_db_unlock()` - `sqlite3.connect(self.scum_db_path, timeout=1)`
- **Linha 117**: `_release_db_lock()` - `sqlite3.connect(self.scum_db_path, timeout=5.0)`
- **Linha 452**: `sync_pending_changes()` - `sqlite3.connect(self.scum_db_path)` (inserção)
- **Linha 514**: `sync_pending_changes()` - `sqlite3.connect(self.scum_db_path)` (remoção)

**Problema:**
- Este manager faz **ESCRITAS** no SCUM.db (inserção/remoção de elevated users)
- O método `_release_db_lock()` tenta desabilitar WAL, mas pode criar WAL/SHM antes disso
- **NÃO usa** helpers de conexão read-only (mas faz escritas, então é esperado)

**Impacto:**
- Médio - Sincroniza apenas quando servidor está parado, mas pode criar WAL durante o processo

---

### 3. **main.py - Endpoint `/api/weather/time`** (linha 7007)
**Status:** ⚠️ **MODERADO - Conexão direta para leitura**

**Conexão direta encontrada:**
- **Linha 7007**: `sqlite3.connect(scum_db_path)` para consultar `weather_parameters`

**Problema:**
- Endpoint da API que consulta horário do jogo
- **NÃO usa** `scum_db_readonly_connection()` ou `ScumDbSharedCopyManager`
- Pode ser chamado frequentemente pelo frontend

**Impacto:**
- Baixo-Médio - Depende da frequência de chamadas do frontend

---

### 4. **scum_db_cleanup.py** (`utils/scum_db_cleanup.py`)
**Status:** ✅ **ESPERADO - Limpeza de WAL/SHM**

**Conexão direta encontrada:**
- **Linha 124**: `sqlite3.connect(scum_db_path, timeout=5.0)` para fazer checkpoint

**Problema:**
- Este arquivo é **específico para limpeza** de arquivos WAL/SHM
- A conexão direta é **intencional** para fazer checkpoint e desabilitar WAL
- Não é um problema - é a solução para limpar WAL/SHM

**Impacto:**
- Nenhum - Este é o processo que limpa os arquivos WAL/SHM

---

## Processos que USAM o Sistema Correto

### ✅ **BankAccountSyncService**
- Usa `scum_db_readonly_connection()` ✅

### ✅ **SurvivalStatsSyncService**
- Usa `scum_db_readonly_connection()` ✅

### ✅ **PlayerSkillsSyncService**
- Usa `scum_db_readonly_connection()` ✅

### ✅ **SquadSyncService**
- Usa `scum_db_readonly_connection()` ✅

### ✅ **ChestSyncService**
- Usa `scum_db_readonly_connection()` ✅

### ✅ **PlayerGpsSyncService**
- Usa `scum_db_readonly_connection()` ✅

---

## Recomendações

### Prioridade ALTA

1. **Corrigir VehicleProcessor**
   - Substituir todas as conexões diretas por `scum_db_readonly_connection()`
   - Este é o processo mais crítico, pois processa logs em tempo real

2. **Corrigir endpoint `/api/weather/time`**
   - Substituir conexão direta por `scum_db_readonly_connection()`

### Prioridade MÉDIA

3. **Melhorar ElevatedUsersManager**
   - O método `_release_db_lock()` já tenta desabilitar WAL, mas pode ser otimizado
   - Considerar usar `scum_db_readonly_connection()` para verificações de unlock

---

## Solução Proposta

### Para VehicleProcessor:

```python
# ANTES (linha 49):
with sqlite3.connect(self.scum_db_path) as conn:

# DEPOIS:
from utils.scum_db_helper import scum_db_readonly_connection
with scum_db_readonly_connection(self.scum_db_path) as conn:
```

Aplicar a mesma correção nas linhas 364 e 399.

### Para endpoint `/api/weather/time`:

```python
# ANTES (linha 7007):
with sqlite3.connect(scum_db_path) as conn:

# DEPOIS:
from utils.scum_db_helper import scum_db_readonly_connection
with scum_db_readonly_connection(scum_db_path) as conn:
```

---

## Conclusão

O principal culpado pela criação de arquivos WAL/SHM é o **VehicleProcessor**, que faz múltiplas conexões diretas ao SCUM.db durante o processamento de logs em tempo real. A correção deste processo deve resolver a maior parte do problema.
