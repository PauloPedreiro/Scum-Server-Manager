# 📋 Planejamento de Implementação: Inicialização do Banco de Dados SSM.db

## 📌 Visão Geral

**Objetivo:** Criar uma interface na janela de Settings para gerenciar a inicialização do banco de dados `SSM.db`, permitindo que o usuário inicialize todas as tabelas de uma vez antes de iniciar o backend.

**Problema:** Atualmente, as tabelas são criadas aos poucos durante a inicialização dos serviços, causando lentidão e confusão na primeira execução.

**Solução:** Tab dedicada em Settings com verificação de status, inicialização manual e feedback visual.

---

## 🎯 Escopo do Projeto

### Funcionalidades Principais
- ✅ Verificação automática do status do banco
- ✅ Inicialização manual de todas as tabelas
- ✅ Verificação de integridade
- ✅ Lista visual de tabelas criadas/faltantes
- ✅ Feedback de progresso em tempo real

### Funcionalidades Excluídas
- ❌ Recriação do banco (não solicitado)
- ❌ Backup automático
- ❌ Migração de dados

---

## 📐 Arquitetura da Solução

### Componentes

```
┌─────────────────────────────────────────┐
│         GUI (main_window.py)            │
│  ┌───────────────────────────────────┐  │
│  │  Tab "Banco de Dados"            │  │
│  │  - Status display                 │  │
│  │  - Botões de ação                 │  │
│  │  - Lista de tabelas                │  │
│  └───────────────────────────────────┘  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  utils/database_initializer.py (NOVO)   │
│  ┌───────────────────────────────────┐  │
│  │  check_database_status()          │  │
│  │  initialize_all_tables()          │  │
│  │  verify_database_integrity()      │  │
│  │  get_existing_tables()            │  │
│  └───────────────────────────────────┘  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Módulos Existentes                 │
│  - UserManager.ensure_table()           │
│  - BankAccountSyncService.ensure_table()│
│  - SquadSyncService.ensure_tables()     │
│  - ... (outros módulos)                 │
└─────────────────────────────────────────┘
```

---

## 📝 Fase 1: Módulo de Inicialização (Backend)

### Arquivo: `utils/database_initializer.py` (NOVO)

#### 1.1 Lista de Tabelas Esperadas

```python
# Lista completa de tabelas obrigatórias
EXPECTED_TABLES = [
    # Autenticação
    'frontend_users',
    'password_reset_tokens',
    
    # Jogadores e Rankings
    'players',
    'rankings',
    'fishing_rankings',
    
    # Squads
    'squad_snapshot',
    'squad_member_snapshot',
    
    # Estatísticas
    'survival_stats_snapshot',
    'player_skills',
    
    # Sistema Bancário
    'bank_accounts_snapshot',
    'bank_transactions',
    'transaction_types',
    'locations',
    'items',
    
    # Baús
    'chest_snapshot',
    'chest_history',
    
    # GPS
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
    
    # Logs
    'log_files_processed',
    'player_logins',
    
    # Licenciamento
    'hardware_fingerprints',
    
    # Clima
    'weather_parameters',
]

# Tabelas opcionais (não contam para verificação)
OPTIONAL_TABLES = [
    'frontend_user_permissions',
    'frontend_user_groups',
    'frontend_user_group_members',
    'player_permissions',
    'license_validations',
]
```

#### 1.2 Função: `get_existing_tables()`

```python
def get_existing_tables(ssm_db_path: str) -> List[str]:
    """
    Obtém lista de todas as tabelas existentes no banco.
    
    Returns:
        Lista de nomes de tabelas (sem tabelas do sistema)
    """
    # Consultar sqlite_master
    # Filtrar sqlite_%
    # Retornar lista ordenada
```

#### 1.3 Função: `check_database_status()`

```python
def check_database_status(ssm_db_path: str) -> Dict:
    """
    Verifica status completo do banco de dados.
    
    Returns:
        {
            'exists': bool,
            'initialized': bool,
            'table_count': int,
            'expected_tables': int,
            'tables': List[str],
            'missing_tables': List[str],
            'size_bytes': int,
            'size_mb': float,
            'last_modified': Optional[str],
            'status_message': str
        }
    """
    # 1. Verificar se arquivo existe
    # 2. Obter informações do arquivo (tamanho, data)
    # 3. Consultar tabelas existentes
    # 4. Comparar com EXPECTED_TABLES
    # 5. Gerar status_message
    # 6. Retornar dict completo
```

#### 1.4 Função: `initialize_all_tables()`

```python
def initialize_all_tables(
    ssm_db_path: str,
    logger: Optional[StructuredLogger] = None,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Inicializa todas as tabelas do banco de dados.
    
    Args:
        ssm_db_path: Caminho para o banco
        logger: Logger opcional
        progress_callback: Função(current, total, table_name)
    
    Returns:
        {
            'success': bool,
            'tables_created': int,
            'tables_total': int,
            'errors': List[Dict],
            'duration_seconds': float
        }
    """
    # Ordem de criação:
    # 1. Tabelas base (sem dependências)
    # 2. Tabelas de usuários
    # 3. Tabelas de dados
    # 4. Tabelas opcionais
    
    # Para cada tabela:
    # - Chamar ensure_table() do módulo correspondente
    # - Chamar progress_callback se fornecido
    # - Registrar erros se houver
    # - Retornar resultado completo
```

#### 1.5 Função: `verify_database_integrity()`

```python
def verify_database_integrity(ssm_db_path: str) -> Dict:
    """
    Verifica integridade do banco de dados.
    
    Returns:
        {
            'valid': bool,
            'issues': List[str],
            'table_status': Dict[str, bool]
        }
    """
    # 1. Verificar se todas as tabelas esperadas existem
    # 2. Verificar estrutura básica de cada tabela
    # 3. Verificar índices importantes
    # 4. Retornar relatório de problemas
```

---

## 🎨 Fase 2: Interface Gráfica (GUI)

### Arquivo: `gui/main_window.py`

#### 2.1 Adicionar Tab na Janela de Settings

**Localização:** Método `_create_settings_window()`

```python
# Adicionar nova tab
database_tab = tabview.add("Banco de Dados")
self._create_database_tab(database_tab)
```

#### 2.2 Método: `_create_database_tab()`

```python
def _create_database_tab(self, parent):
    """Criar tab de Banco de Dados"""
    
    # 1. Frame de Status
    status_frame = ctk.CTkFrame(parent)
    # - Label de status
    # - Label de caminho
    # - Label de tabelas
    # - Label de tamanho
    # - Label de última atualização
    
    # 2. Frame de Ações
    actions_frame = ctk.CTkFrame(parent)
    # - Botão "Inicializar Banco de Dados"
    # - Botão "Verificar Integridade"
    # - Botão "Atualizar Status"
    
    # 3. Frame de Lista de Tabelas
    tables_frame = ctk.CTkScrollableFrame(parent)
    # - Lista scrollable com todas as tabelas
    # - ✅ para tabelas existentes
    # - ❌ para tabelas faltantes
    
    # 4. Carregar status inicial
    self._check_database_status()
```

#### 2.3 Método: `_check_database_status()`

```python
def _check_database_status(self):
    """Verificar e atualizar status do banco"""
    
    # Executar em thread separada
    def check_in_thread():
        from utils.database_initializer import check_database_status
        from utils.config_path_helper import ConfigPathHelper
        
        path_helper = ConfigPathHelper()
        ssm_db_path = path_helper.get_ssm_db_path()
        
        status = check_database_status(ssm_db_path)
        
        # Atualizar UI na thread principal
        self.after(0, lambda: self._update_database_status_ui(status))
    
    threading.Thread(target=check_in_thread, daemon=True).start()
```

#### 2.4 Método: `_update_database_status_ui()`

```python
def _update_database_status_ui(self, status: dict):
    """Atualizar interface com status do banco"""
    
    # Atualizar labels
    self.db_status_label.configure(text=status['status_message'])
    self.db_path_label.configure(text=f"Caminho: {status.get('path', 'N/A')}")
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

#### 2.5 Método: `_initialize_database()`

```python
def _initialize_database(self):
    """Inicializar banco de dados"""
    
    # Confirmar ação
    # Mostrar diálogo de progresso
    # Executar em thread separada
    
    def init_in_thread():
        from utils.database_initializer import initialize_all_tables
        from utils.config_path_helper import ConfigPathHelper
        
        path_helper = ConfigPathHelper()
        ssm_db_path = path_helper.get_ssm_db_path()
        
        # Callback de progresso
        def progress_callback(current, total, table_name):
            self.after(0, lambda: self._update_progress(current, total, table_name))
        
        result = initialize_all_tables(
            ssm_db_path,
            logger=self.logger,
            progress_callback=progress_callback
        )
        
        # Atualizar UI na thread principal
        self.after(0, lambda: self._on_initialization_complete(result))
    
    threading.Thread(target=init_in_thread, daemon=True).start()
```

---

## 📊 Ordem de Implementação

### Etapa 1: Backend (Módulo de Inicialização)
1. ✅ Criar arquivo `utils/database_initializer.py`
2. ✅ Definir `EXPECTED_TABLES` e `OPTIONAL_TABLES`
3. ✅ Implementar `get_existing_tables()`
4. ✅ Implementar `check_database_status()`
5. ✅ Implementar `initialize_all_tables()`
6. ✅ Implementar `verify_database_integrity()`
7. ✅ Testar funções isoladamente

### Etapa 2: Frontend (Interface Gráfica)
8. ✅ Adicionar tab "Banco de Dados" em Settings
9. ✅ Criar método `_create_database_tab()`
10. ✅ Criar método `_check_database_status()`
11. ✅ Criar método `_update_database_status_ui()`
12. ✅ Criar método `_initialize_database()`
13. ✅ Criar método `_update_tables_list()`
14. ✅ Criar método `_update_progress()`
15. ✅ Criar método `_on_initialization_complete()`

### Etapa 3: Integração e Testes
16. ✅ Integrar módulo de inicialização com GUI
17. ✅ Testar verificação de status
18. ✅ Testar inicialização completa
19. ✅ Testar inicialização parcial
20. ✅ Testar verificação de integridade
21. ✅ Testar casos de erro
22. ✅ Ajustar UI/UX conforme necessário

---

## 🧪 Casos de Teste

### Teste 1: Banco Não Existe
- **Setup:** Deletar `SSM.db`
- **Ação:** Abrir Settings → Tab "Banco de Dados"
- **Esperado:** Status "❌ Banco não encontrado", botão "Inicializar" habilitado

### Teste 2: Banco Vazio
- **Setup:** Criar `SSM.db` vazio
- **Ação:** Abrir Settings → Tab "Banco de Dados"
- **Esperado:** Status "⚠️ Banco existe mas está vazio", botão "Inicializar" habilitado

### Teste 3: Banco Parcialmente Inicializado
- **Setup:** Criar banco com 10/25 tabelas
- **Ação:** Abrir Settings → Tab "Banco de Dados" → Clicar "Inicializar"
- **Esperado:** Criar apenas tabelas faltantes, status atualizado

### Teste 4: Banco Completamente Inicializado
- **Setup:** Banco com todas as tabelas
- **Ação:** Abrir Settings → Tab "Banco de Dados"
- **Esperado:** Status "✅ Banco inicializado", botão "Inicializar" desabilitado

### Teste 5: Inicialização com Erro
- **Setup:** Banco bloqueado por outro processo
- **Ação:** Tentar inicializar
- **Esperado:** Mensagem de erro clara, tabelas parcialmente criadas preservadas

### Teste 6: Verificação de Integridade
- **Setup:** Banco inicializado
- **Ação:** Clicar "Verificar Integridade"
- **Esperado:** Relatório mostrando status de todas as tabelas

---

## ⚠️ Considerações Importantes

### Segurança
- ✅ Verificar se backend está rodando antes de inicializar
- ✅ Usar transações para garantir consistência
- ✅ Não permitir inicialização simultânea

### Performance
- ✅ Executar operações em threads separadas
- ✅ Mostrar progresso em tempo real
- ✅ Não bloquear GUI durante operações

### Compatibilidade
- ✅ Funcionar com banco existente parcialmente inicializado
- ✅ Usar `CREATE TABLE IF NOT EXISTS` para evitar duplicação
- ✅ Manter compatibilidade com código existente
- ✅ Não quebrar funcionalidades existentes

### Tratamento de Erros
- ✅ Capturar e exibir erros de forma clara
- ✅ Preservar tabelas já criadas em caso de erro
- ✅ Permitir retry após erro
- ✅ Log detalhado de erros

---

## 📈 Métricas de Sucesso

### Performance
- ⏱️ Inicialização completa: < 5 segundos
- ⏱️ Verificação de status: < 1 segundo
- ⏱️ Verificação de integridade: < 2 segundos

### Qualidade
- ✅ Zero erros durante inicialização normal
- ✅ Todas as tabelas criadas corretamente
- ✅ Interface responsiva (não trava)
- ✅ Feedback visual claro

### Usabilidade
- ✅ Interface intuitiva
- ✅ Mensagens claras e objetivas
- ✅ Progresso visível durante operações
- ✅ Fácil de entender e usar

---

## 📚 Documentação de Referência

### Documentos Relacionados
- `docs/PLANEJAMENTO_INICIALIZACAO_BANCO_DADOS.md` - Visão geral
- `docs/PLANEJAMENTO_INICIALIZACAO_BANCO_DADOS_DETALHES.md` - Detalhes técnicos
- `docs/PLANEJAMENTO_INICIALIZACAO_BANCO_DADOS_VERIFICACAO.md` - Verificação de tabelas

### Módulos a Importar
- `core.auth.user_manager.UserManager`
- `core.auth.password_reset.PasswordResetManager`
- `core.banking.bank_account_sync_service.BankAccountSyncService`
- `core.banking.bank_transaction_tables.ensure_bank_transaction_tables`
- `core.squads.squad_sync_service.SquadSyncService`
- `core.survival.survival_stats_sync_service.SurvivalStatsSyncService`
- `core.survival.player_skills_sync_service.PlayerSkillsSyncService`
- `core.chests.chest_sync_service.ChestSyncService`
- `core.gps.player_gps_sync_service.PlayerGpsSyncService`
- `core.elevated_users.elevated_users_manager.ElevatedUsersManager`
- `core.licensing.license_cache.LicenseCache`
- ... (outros conforme necessário)

---

## ✅ Checklist de Implementação

### Backend
- [ ] Criar `utils/database_initializer.py`
- [ ] Definir `EXPECTED_TABLES`
- [ ] Implementar `get_existing_tables()`
- [ ] Implementar `check_database_status()`
- [ ] Implementar `initialize_all_tables()`
- [ ] Implementar `verify_database_integrity()`
- [ ] Testar todas as funções

### Frontend
- [ ] Adicionar tab "Banco de Dados" em Settings
- [ ] Criar `_create_database_tab()`
- [ ] Criar `_check_database_status()`
- [ ] Criar `_update_database_status_ui()`
- [ ] Criar `_initialize_database()`
- [ ] Criar `_update_tables_list()`
- [ ] Criar `_update_progress()`
- [ ] Criar `_on_initialization_complete()`

### Testes
- [ ] Teste: Banco não existe
- [ ] Teste: Banco vazio
- [ ] Teste: Banco parcial
- [ ] Teste: Banco completo
- [ ] Teste: Erro durante inicialização
- [ ] Teste: Verificação de integridade

### Finalização
- [ ] Revisar código
- [ ] Testar em ambiente real
- [ ] Ajustar UI/UX
- [ ] Documentar mudanças
- [ ] Commit e push

---

## 🚀 Próximos Passos

1. **Aprovar planejamento** ✅
2. **Implementar Fase 1** (Backend)
3. **Implementar Fase 2** (Frontend)
4. **Testar integração**
5. **Ajustes finais**
6. **Deploy**

---

**Data de Criação:** 2025-01-XX  
**Status:** 📋 Planejamento Completo - Pronto para Implementação  
**Versão:** 1.0

