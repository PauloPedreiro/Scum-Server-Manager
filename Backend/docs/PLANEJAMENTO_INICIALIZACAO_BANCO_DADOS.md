# 🗄️ Planejamento: Inicialização do Banco de Dados SSM.db

## 📋 Resumo da Solução

### Problema Identificado
Quando o SSM Backend GUI é iniciado pela primeira vez e o banco de dados `SSM.db` não existe, as tabelas são criadas aos poucos durante a inicialização dos serviços. Isso pode:
- Causar lentidão na primeira inicialização
- Gerar confusão com múltiplas mensagens de criação de tabelas
- Não dar controle ao usuário sobre quando inicializar o banco

### Solução Proposta
Criar uma **seção dedicada na janela de Settings** para gerenciar a inicialização do banco de dados, permitindo:
1. **Verificar status do banco**: Detectar se o banco existe e se está inicializado
2. **Inicializar banco manualmente**: Botão para criar todas as tabelas de uma vez
3. **Feedback visual**: Mostrar progresso e status da inicialização

---

## 🎯 Funcionalidades

### 1. Verificação Automática
- Ao abrir Settings, verificar automaticamente:
  - Se o arquivo `SSM.db` existe
  - Se o banco tem tabelas criadas
  - Quantidade de tabelas existentes

### 2. Inicialização Manual
- Botão "Inicializar Banco de Dados" que:
  - Cria todas as tabelas necessárias de uma vez
  - Mostra progresso durante a criação
  - Exibe mensagem de sucesso/erro
  - Atualiza status após conclusão

### 3. Informações do Banco
- Exibir informações úteis:
  - Caminho do banco de dados
  - Data de criação (se disponível)
  - Número de tabelas
  - Tamanho do arquivo
  - Status (Inicializado / Não inicializado)

---

## 🎨 Layout Proposto

### Localização
**Janela de Settings → Nova Tab: "Banco de Dados"**

### Estrutura Visual

```
┌─────────────────────────────────────────────────────────┐
│  ⚙️ Configurações                                        │
├─────────────────────────────────────────────────────────┤
│  [Licenciamento & Gestão] [Banco de Dados] [Paths]      │ ← Tabs
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📊 Status do Banco de Dados                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Status: ✅ Banco inicializado                     │  │
│  │ Caminho: C:\...\Backend\data\SSM.db              │  │
│  │ Tabelas: 25 criadas                               │  │
│  │ Tamanho: 2.5 MB                                   │  │
│  │ Última atualização: 2025-01-XX 10:30              │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  🔧 Ações                                                │
│  ┌───────────────────────────────────────────────────┐  │
│  │                                                   │  │
│  │  [Inicializar Banco de Dados]  (Verde)            │  │
│  │  Cria todas as tabelas necessárias                │  │
│  │                                                   │  │
│  │  [Verificar Integridade]  (Azul)                   │  │
│  │  Verifica se todas as tabelas estão corretas      │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  📋 Tabelas Criadas                                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │ [Scrollable List]                                 │  │
│  │ ✅ players                                        │  │
│  │ ✅ rankings                                       │  │
│  │ ✅ squad_snapshot                                 │  │
│  │ ✅ bank_accounts_snapshot                          │  │
│  │ ✅ bank_transactions                               │  │
│  │ ✅ frontend_users                                  │  │
│  │ ... (lista todas as tabelas)                      │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  [Atualizar Status]  [Fechar]                            │
└─────────────────────────────────────────────────────────┘
```

### Estados Visuais

#### Estado 1: Banco Não Existe
```
Status: ❌ Banco não encontrado
Caminho: C:\...\Backend\data\SSM.db (não existe)
Tabelas: 0
Tamanho: N/A

[Inicializar Banco de Dados] ← Botão destacado em verde
```

#### Estado 2: Banco Existe mas Não Inicializado
```
Status: ⚠️ Banco existe mas não inicializado
Caminho: C:\...\Backend\data\SSM.db
Tabelas: 0 (banco vazio)
Tamanho: 0 KB

[Inicializar Banco de Dados] ← Botão destacado em verde
```

#### Estado 3: Banco Inicializado
```
Status: ✅ Banco inicializado
Caminho: C:\...\Backend\data\SSM.db
Tabelas: 25 criadas
Tamanho: 2.5 MB

[Inicializar Banco de Dados] ← Botão desabilitado (cinza)
[Verificar Integridade] ← Botão disponível (azul)
```

#### Estado 4: Durante Inicialização
```
Status: ⏳ Inicializando banco de dados...
Progresso: [████████░░] 80% (20/25 tabelas)

[Cancelar] ← Botão vermelho (se possível cancelar)
```

---

## 🔧 Implementação Técnica

### 1. Função Centralizada de Inicialização

**Arquivo:** `utils/database_initializer.py` (novo)

```python
def initialize_all_tables(ssm_db_path: str, logger=None) -> dict:
    """
    Inicializa todas as tabelas do banco SSM.db de uma vez.
    
    Returns:
        dict com status, tabelas_criadas, erros
    """
    # Chamar todos os ensure_table() de uma vez
    # Retornar progresso e status
```

### 2. Verificação de Status

**Função:** `check_database_status(ssm_db_path: str) -> dict`
- Verifica se arquivo existe
- Consulta `sqlite_master` para listar tabelas existentes
- Compara com lista centralizada de tabelas esperadas
- Identifica tabelas faltantes
- Calcula tamanho do arquivo
- Retorna status completo

**📖 Detalhes técnicos:** Ver `docs/PLANEJAMENTO_INICIALIZACAO_BANCO_DADOS_VERIFICACAO.md`

### 3. Lista de Tabelas a Criar

Todas as tabelas que precisam ser criadas:
1. `players` (se necessário)
2. `rankings`
3. `squad_snapshot`
4. `squad_member_snapshot`
5. `survival_stats_snapshot`
6. `player_skills`
7. `bank_accounts_snapshot`
8. `bank_transactions`
9. `transaction_types`
10. `locations`
11. `items`
12. `chest_snapshot`
13. `chest_history`
14. `player_gps_snapshot`
15. `elevated_user`
16. `frontend_users`
17. `password_reset_tokens`
18. `hardware_fingerprints`
19. `fishing_rankings`
20. `kill_events`
21. `minigame_events`
22. `vehicle_destruction_events`
23. `weather_parameters`
24. `log_files_processed`
25. `player_logins`
... (outras conforme necessário)

### 4. Integração com GUI

**Arquivo:** `gui/main_window.py`

- Adicionar nova tab "Banco de Dados" na janela de Settings
- Criar método `_create_database_tab()`
- Criar método `_check_database_status()`
- Criar método `_initialize_database()`

---

## 📝 Fluxo de Uso

### Cenário 1: Primeira Inicialização
1. Usuário abre Settings
2. Vai para tab "Banco de Dados"
3. Vê status: "Banco não encontrado"
4. Clica em "Inicializar Banco de Dados"
5. Vê progresso: "Criando tabelas... 5/25"
6. Recebe mensagem: "✅ Banco inicializado com sucesso!"
7. Status atualiza: "✅ Banco inicializado - 25 tabelas"

### Cenário 2: Banco Parcialmente Inicializado
1. Usuário abre Settings
2. Vê status: "⚠️ Banco existe mas não inicializado (5/25 tabelas)"
3. Clica em "Inicializar Banco de Dados"
4. Sistema cria apenas as tabelas faltantes
5. Status atualiza: "✅ Banco inicializado - 25 tabelas"

### Cenário 3: Verificação de Integridade
1. Usuário clica em "Verificar Integridade"
2. Sistema verifica todas as tabelas
3. Mostra relatório: "✅ Todas as tabelas estão corretas" ou lista problemas

---

## ⚠️ Considerações Importantes

### Segurança
- ✅ **Verificar se backend está rodando** antes de inicializar (evitar conflitos)

### Performance
- ✅ Executar inicialização em thread separada (não bloquear GUI)
- ✅ Mostrar progresso em tempo real
- ✅ Permitir cancelamento (se possível)

### Compatibilidade
- ✅ Funcionar mesmo se banco já existir parcialmente
- ✅ Não duplicar tabelas (usar CREATE TABLE IF NOT EXISTS)
- ✅ Manter compatibilidade com código existente

---

## 🎯 Próximos Passos

1. ✅ **Criar função centralizada** `initialize_all_tables()`
2. ✅ **Criar função de verificação** `check_database_status()`
3. ✅ **Adicionar tab na GUI** "Banco de Dados"
4. ✅ **Implementar botões e feedback visual**
5. ✅ **Testar em cenários reais**:
   - Banco não existe
   - Banco vazio
   - Banco parcialmente inicializado
   - Banco já inicializado

---

## 📊 Métricas de Sucesso

- ✅ Usuário consegue inicializar banco em < 5 segundos
- ✅ Feedback visual claro durante processo
- ✅ Zero erros durante inicialização
- ✅ Todas as tabelas criadas corretamente
- ✅ Interface intuitiva e fácil de usar

---

**Data de Criação:** 2025-01-XX  
**Status:** 📋 Planejamento - Aguardando Aprovação

