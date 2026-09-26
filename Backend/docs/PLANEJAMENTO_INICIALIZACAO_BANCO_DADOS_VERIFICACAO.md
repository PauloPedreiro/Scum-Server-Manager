# 🔍 Como Verificar se Todas as Tabelas Existem

## 📋 Estratégia de Verificação

### 1. Lista Centralizada de Tabelas Esperadas

A aplicação terá uma **lista centralizada** com todas as tabelas que devem existir no banco `SSM.db`. Esta lista será definida no módulo `utils/database_initializer.py`.

### 2. Consulta ao Banco SQLite

O SQLite fornece uma tabela especial `sqlite_master` que contém informações sobre todas as tabelas, índices, views, etc. do banco.

### 3. Comparação e Análise

A aplicação comparará a lista esperada com a lista real de tabelas no banco para determinar:
- Quais tabelas existem
- Quais tabelas estão faltando
- Status de inicialização (completo ou parcial)

---

## 🔧 Implementação Técnica

### Consulta SQL para Listar Tabelas Existentes

```python
import sqlite3

def get_existing_tables(ssm_db_path: str) -> list:
    """
    Obtém lista de todas as tabelas existentes no banco.
    
    Args:
        ssm_db_path: Caminho para o banco SSM.db
    
    Returns:
        Lista de nomes de tabelas (sem índices, views, etc.)
    """
    try:
        with sqlite3.connect(ssm_db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            
            # Consultar sqlite_master para obter apenas tabelas
            cursor.execute("""
                SELECT name 
                FROM sqlite_master 
                WHERE type='table' 
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            
            # sqlite_% são tabelas do sistema (sqlite_sequence, etc.)
            # Não queremos incluí-las na contagem
            
            tables = [row[0] for row in cursor.fetchall()]
            return tables
            
    except sqlite3.Error as e:
        print(f"Erro ao consultar tabelas: {e}")
        return []
```

### Lista Centralizada de Tabelas Esperadas

```python
# utils/database_initializer.py

# Lista completa de todas as tabelas que devem existir
EXPECTED_TABLES = [
    # Autenticação e Usuários
    'frontend_users',
    'password_reset_tokens',
    
    # Jogadores e Rankings
    'players',
    'rankings',
    'fishing_rankings',
    
    # Squads
    'squad_snapshot',
    'squad_member_snapshot',
    
    # Estatísticas de Sobrevivência
    'survival_stats_snapshot',
    'player_skills',
    
    # Sistema Bancário
    'bank_accounts_snapshot',
    'bank_transactions',
    'transaction_types',
    'locations',
    'items',
    
    # Baús (Chests)
    'chest_snapshot',
    'chest_history',
    
    # GPS e Localização
    'player_gps_snapshot',
    
    # Elevated Users
    'elevated_user',
    
    # Eventos
    'kill_events',
    'minigame_events',
    'vehicle_destruction_events',
    
    # Veículos
    'vehicle_current_ownership',
    'vehicle_ownership_history',
    
    # Sistema de Logs
    'log_files_processed',
    'player_logins',
    
    # Licenciamento
    'hardware_fingerprints',
    
    # Clima
    'weather_parameters',
    
    # Tabelas opcionais (podem não existir em todas as instalações)
    # 'frontend_user_permissions',
    # 'frontend_user_groups',
    # 'frontend_user_group_members',
    # 'player_permissions',
    # 'license_validations',
]

# Tabelas opcionais (não contam para verificação de inicialização completa)
OPTIONAL_TABLES = [
    'frontend_user_permissions',
    'frontend_user_groups',
    'frontend_user_group_members',
    'player_permissions',
    'license_validations',
    'admin_commands_processed',
    'custom_zone_region',
    'abandoned_bunker',
]
```

### Função de Verificação Completa

```python
def check_database_status(ssm_db_path: str) -> dict:
    """
    Verifica o status completo do banco de dados.
    
    Args:
        ssm_db_path: Caminho para o banco SSM.db
    
    Returns:
        {
            'exists': bool,                    # Se o arquivo existe
            'initialized': bool,               # Se está completamente inicializado
            'table_count': int,                # Número de tabelas existentes
            'expected_tables': int,            # Número de tabelas esperadas
            'tables': List[str],              # Lista de tabelas existentes
            'missing_tables': List[str],       # Lista de tabelas faltando
            'optional_tables': List[str],      # Tabelas opcionais encontradas
            'size_bytes': int,                 # Tamanho do arquivo em bytes
            'size_mb': float,                 # Tamanho do arquivo em MB
            'last_modified': Optional[str],    # Data de última modificação
            'status_message': str              # Mensagem de status legível
        }
    """
    import os
    from datetime import datetime
    
    result = {
        'exists': False,
        'initialized': False,
        'table_count': 0,
        'expected_tables': len(EXPECTED_TABLES),
        'tables': [],
        'missing_tables': [],
        'optional_tables': [],
        'size_bytes': 0,
        'size_mb': 0.0,
        'last_modified': None,
        'status_message': ''
    }
    
    # Verificar se arquivo existe
    if not os.path.exists(ssm_db_path):
        result['status_message'] = 'Banco não encontrado'
        return result
    
    result['exists'] = True
    
    # Obter informações do arquivo
    try:
        stat = os.stat(ssm_db_path)
        result['size_bytes'] = stat.st_size
        result['size_mb'] = round(stat.st_size / (1024 * 1024), 2)
        result['last_modified'] = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        pass
    
    # Obter tabelas existentes
    existing_tables = get_existing_tables(ssm_db_path)
    result['tables'] = existing_tables
    result['table_count'] = len(existing_tables)
    
    # Separar tabelas esperadas, opcionais e faltantes
    existing_set = set(existing_tables)
    expected_set = set(EXPECTED_TABLES)
    optional_set = set(OPTIONAL_TABLES)
    
    # Tabelas faltantes (esperadas mas não existentes)
    result['missing_tables'] = sorted(list(expected_set - existing_set))
    
    # Tabelas opcionais encontradas
    result['optional_tables'] = sorted(list(optional_set & existing_set))
    
    # Verificar se está inicializado
    # Considera inicializado se todas as tabelas esperadas existem
    result['initialized'] = len(result['missing_tables']) == 0
    
    # Gerar mensagem de status
    if not result['exists']:
        result['status_message'] = '❌ Banco não encontrado'
    elif result['table_count'] == 0:
        result['status_message'] = '⚠️ Banco existe mas está vazio'
    elif result['initialized']:
        result['status_message'] = f'✅ Banco inicializado ({result["table_count"]} tabelas)'
    else:
        missing_count = len(result['missing_tables'])
        result['status_message'] = f'⚠️ Banco parcialmente inicializado ({result["table_count"]}/{result["expected_tables"]} tabelas, faltam {missing_count})'
    
    return result
```

---

## 📊 Exemplos de Resultados

### Caso 1: Banco Não Existe
```python
{
    'exists': False,
    'initialized': False,
    'table_count': 0,
    'expected_tables': 25,
    'tables': [],
    'missing_tables': [...todas as 25 tabelas...],
    'status_message': '❌ Banco não encontrado'
}
```

### Caso 2: Banco Vazio
```python
{
    'exists': True,
    'initialized': False,
    'table_count': 0,
    'expected_tables': 25,
    'tables': [],
    'missing_tables': [...todas as 25 tabelas...],
    'size_bytes': 0,
    'size_mb': 0.0,
    'status_message': '⚠️ Banco existe mas está vazio'
}
```

### Caso 3: Banco Parcialmente Inicializado
```python
{
    'exists': True,
    'initialized': False,
    'table_count': 15,
    'expected_tables': 25,
    'tables': ['players', 'rankings', 'squad_snapshot', ...],
    'missing_tables': ['bank_transactions', 'chest_snapshot', ...],
    'size_bytes': 1048576,
    'size_mb': 1.0,
    'status_message': '⚠️ Banco parcialmente inicializado (15/25 tabelas, faltam 10)'
}
```

### Caso 4: Banco Completamente Inicializado
```python
{
    'exists': True,
    'initialized': True,
    'table_count': 25,
    'expected_tables': 25,
    'tables': [...todas as 25 tabelas...],
    'missing_tables': [],
    'optional_tables': ['frontend_user_permissions'],
    'size_bytes': 2621440,
    'size_mb': 2.5,
    'status_message': '✅ Banco inicializado (25 tabelas)'
}
```

---

## 🔄 Fluxo de Verificação na GUI

### 1. Ao Abrir Tab "Banco de Dados"
```python
def _check_database_status(self):
    """Verificar e atualizar status do banco"""
    # Obter caminho do banco
    from utils.config_path_helper import ConfigPathHelper
    path_helper = ConfigPathHelper()
    ssm_db_path = path_helper.get_ssm_db_path()
    
    # Verificar status (executar em thread para não bloquear GUI)
    def check_in_thread():
        status = check_database_status(ssm_db_path)
        
        # Atualizar UI na thread principal
        self.after(0, lambda: self._update_database_status_ui(status))
    
    threading.Thread(target=check_in_thread, daemon=True).start()
```

### 2. Atualizar Interface
```python
def _update_database_status_ui(self, status: dict):
    """Atualizar interface com status do banco"""
    # Atualizar labels
    self.db_status_label.configure(text=status['status_message'])
    self.db_path_label.configure(text=f"Caminho: {ssm_db_path}")
    self.db_tables_label.configure(
        text=f"Tabelas: {status['table_count']}/{status['expected_tables']}"
    )
    
    # Atualizar botão de inicializar
    if status['initialized']:
        self.btn_init_db.configure(state="disabled", fg_color="gray")
    else:
        self.btn_init_db.configure(state="normal", fg_color="green")
    
    # Atualizar lista de tabelas
    self._update_tables_list(status['tables'], status['missing_tables'])
```

### 3. Lista de Tabelas na Interface
```python
def _update_tables_list(self, existing_tables: list, missing_tables: list):
    """Atualizar lista visual de tabelas"""
    # Limpar lista atual
    for widget in self.tables_listbox.winfo_children():
        widget.destroy()
    
    # Adicionar tabelas existentes (com ✅)
    for table in sorted(existing_tables):
        if table not in OPTIONAL_TABLES:  # Não mostrar opcionais na lista principal
            label = ctk.CTkLabel(
                self.tables_listbox,
                text=f"✅ {table}",
                font=ctk.CTkFont(size=11)
            )
            label.pack(anchor="w", padx=5, pady=2)
    
    # Adicionar tabelas faltantes (com ❌)
    for table in sorted(missing_tables):
        label = ctk.CTkLabel(
            self.tables_listbox,
            text=f"❌ {table}",
            font=ctk.CTkFont(size=11),
            text_color="red"
        )
        label.pack(anchor="w", padx=5, pady=2)
```

---

## ⚡ Performance

### Tempo de Verificação
- **Banco não existe**: ~0.001s (apenas verificação de arquivo)
- **Banco vazio**: ~0.01s (consulta rápida ao sqlite_master)
- **Banco com tabelas**: ~0.05-0.1s (consulta + processamento)

### Otimizações
- ✅ Consulta única ao `sqlite_master` (não uma por tabela)
- ✅ Processamento em thread separada (não bloqueia GUI)
- ✅ Cache do resultado (atualizar apenas quando necessário)

---

## 🧪 Testes

### Teste 1: Banco Não Existe
```python
status = check_database_status("data/SSM.db")  # Arquivo não existe
assert status['exists'] == False
assert status['initialized'] == False
assert status['status_message'] == '❌ Banco não encontrado'
```

### Teste 2: Banco Vazio
```python
# Criar banco vazio
conn = sqlite3.connect("data/SSM.db")
conn.close()

status = check_database_status("data/SSM.db")
assert status['exists'] == True
assert status['table_count'] == 0
assert status['initialized'] == False
assert status['status_message'] == '⚠️ Banco existe mas está vazio'
```

### Teste 3: Banco Parcial
```python
# Criar banco com algumas tabelas
conn = sqlite3.connect("data/SSM.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS players (id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS rankings (id INTEGER)")
conn.close()

status = check_database_status("data/SSM.db")
assert status['exists'] == True
assert status['table_count'] == 2
assert status['initialized'] == False
assert len(status['missing_tables']) > 0
```

### Teste 4: Banco Completo
```python
# Inicializar banco completamente
initialize_all_tables("data/SSM.db")

status = check_database_status("data/SSM.db")
assert status['exists'] == True
assert status['initialized'] == True
assert len(status['missing_tables']) == 0
assert status['status_message'].startswith('✅')
```

---

## 📝 Notas Importantes

### Tabelas do Sistema SQLite
- As tabelas `sqlite_sequence`, `sqlite_stat1`, etc. são **ignoradas** na contagem
- Usamos filtro `name NOT LIKE 'sqlite_%'` para excluí-las

### Tabelas Opcionais
- Tabelas opcionais **não contam** para verificação de inicialização completa
- Elas são listadas separadamente para informação

### Atualização da Lista
- Se novas tabelas forem adicionadas ao sistema, basta atualizar `EXPECTED_TABLES`
- A verificação será automaticamente atualizada

---

**Data de Criação:** 2025-01-XX  
**Status:** 📋 Documentação Técnica - Pronto para Implementação

