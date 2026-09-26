# 🗄️ Detalhes Técnicos: Inicialização do Banco de Dados SSM.db

## 📋 Lista Completa de Tabelas

### Tabelas Principais (Core)

#### 1. Autenticação e Usuários
- `frontend_users` - Usuários do frontend/admin
- `password_reset_tokens` - Tokens de recuperação de senha
- `frontend_user_permissions` - Permissões de usuários (se implementado)
- `frontend_user_groups` - Grupos de usuários (se implementado)
- `frontend_user_group_members` - Membros de grupos (se implementado)

#### 2. Jogadores e Rankings
- `players` - Informações básicas dos jogadores
- `rankings` - Rankings consolidados dos jogadores
- `fishing_rankings` - Rankings de pesca

#### 3. Squads
- `squad_snapshot` - Snapshots de squads
- `squad_member_snapshot` - Snapshots de membros de squads

#### 4. Estatísticas de Sobrevivência
- `survival_stats_snapshot` - Estatísticas de sobrevivência
- `player_skills` - Habilidades dos jogadores

#### 5. Sistema Bancário
- `bank_accounts_snapshot` - Snapshots de contas bancárias
- `bank_transactions` - Transações bancárias
- `transaction_types` - Tipos de transação
- `locations` - Locais de transação
- `items` - Itens normalizados

#### 6. Baús (Chests)
- `chest_snapshot` - Snapshots de baús
- `chest_history` - Histórico de baús

#### 7. GPS e Localização
- `player_gps_snapshot` - Snapshots de posições GPS

#### 8. Elevated Users
- `elevated_user` - Usuários elevados

#### 9. Eventos
- `kill_events` - Eventos de kills
- `minigame_events` - Eventos de minigames
- `vehicle_destruction_events` - Eventos de destruição de veículos

#### 10. Veículos
- `vehicle_current_ownership` - Propriedade atual de veículos
- `vehicle_ownership_history` - Histórico de propriedade

#### 11. Sistema de Logs
- `log_files_processed` - Arquivos de log processados
- `player_logins` - Logins de jogadores

#### 12. Licenciamento
- `hardware_fingerprints` - Fingerprints de hardware
- `license_validations` - Validações de licença (se implementado)

#### 13. Clima
- `weather_parameters` - Parâmetros climáticos

#### 14. Permissões
- `player_permissions` - Permissões de jogadores (se implementado)

#### 15. Outras (se existirem)
- `admin_commands_processed` - Comandos admin processados
- `custom_zone_region` - Regiões de zona customizadas
- `abandoned_bunker` - Bunkers abandonados
- `abandoned_bunker_mesh_instance_bound_to_activation` - Instâncias de mesh

---

## 🎨 Mockup Visual Detalhado

### Janela de Settings - Tab "Banco de Dados"

```
╔═══════════════════════════════════════════════════════════════╗
║  ⚙️ Configurações                                    [×]       ║
╠═══════════════════════════════════════════════════════════════╣
║  [Licenciamento & Gestão] [Banco de Dados] [Paths]           ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  📊 Status do Banco de Dados                                  ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │                                                         │  ║
║  │  Status:  ✅ Banco inicializado                        │  ║
║  │  Caminho: C:\Users\...\Backend\data\SSM.db             │  ║
║  │  Tabelas:  25 criadas / 25 esperadas                   │  ║
║  │  Tamanho:  2.5 MB                                       │  ║
║  │  Última atualização: 2025-01-XX 10:30:45               │  ║
║  │                                                         │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                               ║
║  🔧 Ações                                                      ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │                                                         │  ║
║  │  ┌──────────────────────────────────────────────┐      │  ║
║  │  │  Inicializar Banco de Dados                  │      │  ║
║  │  │  Cria todas as tabelas necessárias          │      │  ║
║  │  └──────────────────────────────────────────────┘      │  ║
║  │  [Botão Verde - Desabilitado se já inicializado]      │  ║
║  │                                                         │  ║
║  │  ┌──────────────────────────────────────────────┐      │  ║
║  │  │  Verificar Integridade                       │      │  ║
║  │  │  Verifica se todas as tabelas estão OK      │      │  ║
║  │  └──────────────────────────────────────────────┘      │  ║
║  │  [Botão Azul]                                          │  ║
║  │                                                         │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                               ║
║  📋 Tabelas do Banco                                          ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │  🔍 Filtrar: [________________]                          │  ║
║  ├─────────────────────────────────────────────────────────┤  ║
║  │  ✅ players                                              │  ║
║  │  ✅ rankings                                            │  ║
║  │  ✅ squad_snapshot                                      │  ║
║  │  ✅ squad_member_snapshot                               │  ║
║  │  ✅ survival_stats_snapshot                              │  ║
║  │  ✅ player_skills                                       │  ║
║  │  ✅ bank_accounts_snapshot                              │  ║
║  │  ✅ bank_transactions                                   │  ║
║  │  ✅ transaction_types                                   │  ║
║  │  ✅ locations                                            │  ║
║  │  ✅ items                                               │  ║
║  │  ✅ chest_snapshot                                      │  ║
║  │  ✅ chest_history                                       │  ║
║  │  ✅ player_gps_snapshot                                │  ║
║  │  ✅ elevated_user                                       │  ║
║  │  ✅ frontend_users                                      │  ║
║  │  ✅ password_reset_tokens                               │  ║
║  │  ✅ hardware_fingerprints                              │  ║
║  │  ✅ fishing_rankings                                   │  ║
║  │  ✅ kill_events                                         │  ║
║  │  ✅ minigame_events                                    │  ║
║  │  ✅ vehicle_destruction_events                        │  ║
║  │  ✅ weather_parameters                                 │  ║
║  │  ✅ log_files_processed                               │  ║
║  │  ✅ player_logins                                      │  ║
║  │  ... (scrollable)                                      │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                               ║
║  ┌──────────────┐  ┌──────────────┐                         ║
║  │ Atualizar     │  │ Fechar       │                         ║
║  └──────────────┘  └──────────────┘                         ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 🔄 Estados e Transições

### Estado Inicial (Ao Abrir Tab)
```
1. Verificar se banco existe
2. Se existe, contar tabelas
3. Calcular tamanho
4. Atualizar UI com status
```

### Estado: Inicializando
```
Status: ⏳ Inicializando banco de dados...
Progresso: [████████░░] 80% (20/25 tabelas)
Última tabela: bank_transactions

[Cancelar] ← Botão vermelho
```

### Estado: Sucesso
```
Status: ✅ Banco inicializado com sucesso!
Tabelas criadas: 25
Tempo: 2.3 segundos

[OK] ← Botão verde
```

### Estado: Erro
```
Status: ❌ Erro ao inicializar banco
Erro: database is locked

Detalhes:
- Tabelas criadas: 15/25
- Erro na tabela: bank_transactions
- Solução: Feche outras conexões ao banco

[Fechar] [Tentar Novamente]
```

---

## 🛠️ Estrutura de Código Proposta

### Arquivo: `utils/database_initializer.py`

```python
"""
Módulo centralizado para inicialização do banco de dados SSM.db
"""

import sqlite3
import os
from typing import Dict, List, Optional, Tuple
from utils.logger import StructuredLogger
from utils.config_path_helper import ConfigPathHelper

# Importar todos os módulos que criam tabelas
from core.auth.user_manager import UserManager
from core.auth.password_reset import PasswordResetManager
from core.banking.bank_account_sync_service import BankAccountSyncService
from core.banking.bank_transaction_tables import ensure_bank_transaction_tables
from core.squads.squad_sync_service import SquadSyncService
from core.survival.survival_stats_sync_service import SurvivalStatsSyncService
from core.survival.player_skills_sync_service import PlayerSkillsSyncService
from core.chests.chest_sync_service import ChestSyncService
from core.gps.player_gps_sync_service import PlayerGpsSyncService
from core.elevated_users.elevated_users_manager import ElevatedUsersManager
# ... outros imports

def check_database_status(ssm_db_path: str) -> Dict:
    """
    Verifica o status do banco de dados.
    
    Returns:
        {
            'exists': bool,
            'initialized': bool,
            'table_count': int,
            'expected_tables': int,
            'size_bytes': int,
            'size_mb': float,
            'tables': List[str],
            'missing_tables': List[str],
            'last_modified': Optional[str]
        }
    """
    pass

def initialize_all_tables(
    ssm_db_path: str,
    logger: Optional[StructuredLogger] = None,
    progress_callback: Optional[callable] = None
) -> Dict:
    """
    Inicializa todas as tabelas do banco de dados.
    
    Args:
        ssm_db_path: Caminho para o banco
        logger: Logger opcional
        progress_callback: Função callback(current, total, table_name)
    
    Returns:
        {
            'success': bool,
            'tables_created': int,
            'tables_total': int,
            'errors': List[Dict],
            'duration_seconds': float
        }
    """
    pass

def verify_database_integrity(ssm_db_path: str) -> Dict:
    """
    Verifica a integridade do banco de dados.
    
    Returns:
        {
            'valid': bool,
            'issues': List[str],
            'table_status': Dict[str, bool]
        }
    """
    pass
```

### Integração na GUI: `gui/main_window.py`

```python
def _create_database_tab(self, tabview):
    """Criar tab de Banco de Dados"""
    database_tab = tabview.add("Banco de Dados")
    
    # Status frame
    status_frame = ctk.CTkFrame(database_tab)
    status_frame.pack(fill="x", pady=10, padx=10)
    
    # Status labels
    self.db_status_label = ctk.CTkLabel(...)
    self.db_path_label = ctk.CTkLabel(...)
    self.db_tables_label = ctk.CTkLabel(...)
    
    # Botões de ação
    self.btn_init_db = ctk.CTkButton(
        text="Inicializar Banco de Dados",
        command=self._initialize_database,
        fg_color="green"
    )
    
    self.btn_verify_integrity = ctk.CTkButton(
        text="Verificar Integridade",
        command=self._verify_database_integrity,
        fg_color="blue"
    )
    
    # Lista de tabelas
    self.tables_listbox = ctk.CTkScrollableFrame(...)
    
    # Atualizar status ao abrir
    self._check_database_status()

def _check_database_status(self):
    """Verificar e atualizar status do banco"""
    # Chamar check_database_status()
    # Atualizar labels
    # Atualizar lista de tabelas
    pass

def _initialize_database(self):
    """Inicializar banco de dados"""
    # Executar em thread separada
    # Mostrar progresso
    # Atualizar status ao finalizar
    pass
```

---

## 📊 Ordem de Criação das Tabelas

### Fase 1: Tabelas Base (sem dependências)
1. `hardware_fingerprints`
2. `transaction_types`
3. `locations`
4. `items`
5. `weather_parameters`

### Fase 2: Tabelas de Usuários
6. `frontend_users`
7. `password_reset_tokens`
8. `players` (se necessário)

### Fase 3: Tabelas de Dados (podem depender de players)
9. `rankings`
10. `fishing_rankings`
11. `squad_snapshot`
12. `squad_member_snapshot`
13. `survival_stats_snapshot`
14. `player_skills`
15. `bank_accounts_snapshot`
16. `bank_transactions` (depende de transaction_types, locations, items)
17. `chest_snapshot`
18. `chest_history`
19. `player_gps_snapshot`
20. `elevated_user`
21. `kill_events`
22. `minigame_events`
23. `vehicle_destruction_events`
24. `log_files_processed`
25. `player_logins`

### Fase 4: Tabelas Opcionais
26. `frontend_user_permissions` (se implementado)
27. `frontend_user_groups` (se implementado)
28. `frontend_user_group_members` (se implementado)
29. `player_permissions` (se implementado)
30. Outras tabelas específicas...

---

## ⚡ Performance Esperada

### Tempo de Inicialização
- **Banco vazio**: ~2-5 segundos
- **Banco parcial**: ~1-3 segundos (apenas tabelas faltantes)
- **Verificação**: ~0.5-1 segundo

### Recursos
- **Memória**: < 50 MB durante inicialização
- **CPU**: Pico curto durante criação
- **Disco**: I/O mínimo (apenas criação de estrutura)

---

## 🧪 Casos de Teste

### Teste 1: Banco Não Existe
1. Deletar `SSM.db`
2. Abrir Settings → Banco de Dados
3. Verificar status: "Banco não encontrado"
4. Clicar "Inicializar"
5. Verificar: Todas as tabelas criadas

### Teste 2: Banco Vazio
1. Criar `SSM.db` vazio
2. Abrir Settings → Banco de Dados
3. Verificar status: "Banco vazio"
4. Clicar "Inicializar"
5. Verificar: Todas as tabelas criadas

### Teste 3: Banco Parcial
1. Criar banco com 10/25 tabelas
2. Abrir Settings → Banco de Dados
3. Verificar status: "10/25 tabelas"
4. Clicar "Inicializar"
5. Verificar: 25/25 tabelas criadas

### Teste 4: Banco Completo
1. Banco já inicializado
2. Abrir Settings → Banco de Dados
3. Verificar status: "Banco inicializado"
4. Botão "Inicializar" desabilitado
5. Botão "Verificar Integridade" disponível

### Teste 5: Erro Durante Inicialização
1. Simular erro (ex: banco locked)
2. Verificar mensagem de erro
3. Verificar tabelas parcialmente criadas
4. Tentar novamente após resolver

---

**Data de Criação:** 2025-01-XX  
**Status:** 📋 Detalhamento Técnico - Pronto para Implementação

