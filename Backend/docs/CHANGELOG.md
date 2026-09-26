# 📝 Changelog - SCUM Backend

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### ✨ Adicionado
- **Sistema de Scheduled Notifications (notificações customizadas programadas)**
  - Persistência das notificações programadas em `data/notifications/config/scheduled_notifications.json`.
  - Suporte a múltiplos tipos de agenda:
    - `once` (data/hora ISO)
    - `daily` (HH:MM)
    - `relative_to_restart` (offset em minutos relativo ao horário de restart)
  - Compilação do arquivo do SCUM `Notifications.json` combinando:
    - Notificações de restart de todos os restarts do dia
    - Notificações customizadas válidas nas próximas 24h

- **Discord Bot: optional role assignment after register (`!register`)**
  - New `Register Role ID` field in the Discord (Bot) tab to configure which role to grant.
  - New config key: `discord_bot.register_role_id`.
  - Behavior:
    - If `register_role_id` is empty, registration works as before (only links `steam_id` <-> `discord_user_id`).
    - If `register_role_id` is set, the bot attempts to grant the role in the configured `guild_id`.
    - Role assignment failure does not break registration: the system logs and sends a DM informing the failure.

### 🔒 Segurança
- **Bloqueio de horários reservados por restart (HTTP 409)**
  - Implementada regra de janela reservada ao redor de cada restart:
    - Início: `restart - 15 min` (inclusive)
    - Fim: `restart + 5 min` (inclusive)
  - Customs que conflitam retornam HTTP `409` com `error_code: SCHEDULE_TIME_RESERVED_BY_RESTART` e detalhes do conflito.

### 🎯 Melhorias
- **Robustez do `Notifications.json` (SCUM)**
  - Escrita atômica do arquivo (tmp + `os.replace`) para evitar corrupção.
  - Compilação automática no startup.
  - Verificação periódica reforçada para detectar adulteração e auto-reparar recompilando o arquivo.

### 🌐 API
- **Novos endpoints para gerenciar notificações programadas**
  - `GET /api/notifications/scheduled` - listar
  - `GET /api/notifications/scheduled/<item_id>` - obter por id
  - `POST /api/notifications/scheduled/validate` - validar payload (sem salvar), com retorno `409` em conflito
  - `POST /api/notifications/scheduled` - criar e recompilar
  - `PUT /api/notifications/scheduled/<item_id>` - atualizar e recompilar
  - `DELETE /api/notifications/scheduled/<item_id>` - remover e recompilar
  - `POST /api/notifications/compile` - forçar compilação do `Notifications.json`

### 📚 Documentação
- **Postman collection atualizada**
  - Inclusão dos requests dos endpoints de scheduled notifications.
  - Correção de problemas de JSON na collection.
- **Documentação para o frontend**
  - Criado `docs/FRONTEND_SCHEDULED_NOTIFICATIONS.md` com:
    - Endpoints
    - Schemas/payloads
    - Fluxo recomendado de validação
    - Tratamento de erro `409` (janela reservada)

### 🔧 Corrigido
- **Monitoramento de logs em tempo real (robustez / admin_*.log)**
  - Corrigida condição de corrida no `LogFileMonitor.start_monitoring()` onde `polling_thread` podia iniciar com `self.running=False` e encerrar imediatamente, impedindo o polling de `admin_*.log` (e outros logs do polling).
  - Corrigida leitura incremental de logs via `data/temp` para evitar `seek()` em modo texto com UTF-16 (offset em bytes), migrando para leitura **binária por bytes** + decode seguro e atualização de posição baseada no que foi efetivamente lido.
  - Resultado: processamento não depende mais de “abrir o arquivo” na pasta original para disparar leitura.
  - Arquivo afetado: `core/logs/file_monitor.py`.

- **Mitigação de locks do `SCUM.db` no restart (Elevated Users)**
  - `ElevatedUsersManager._release_db_lock()` não força mais `wal_checkpoint`, não altera `journal_mode` e não tenta remover arquivos `SCUM.db-wal/-shm` (limpeza passa a ser centralizada no `ServerManager`, evitando disputa de locks durante a janela offline do restart).
  - Corrigido uso de `StructuredLogger`: substituído `logger.warning(...)` por `logger.warn(...)`.
  - Adicionados logs de observabilidade no `sync_pending_changes()`:
    - Início: quantidade de pendências (`to_add` / `to_remove`).
    - Fim (sempre): duração (`elapsed_s`), `changes_count` e `errors_count`.
  - Arquivo afetado: `core/elevated_users/elevated_users_manager.py`.

- **Mitigação de `database is locked` no startup (SQLite)**
  - Conexões SQLite padronizadas com `PRAGMA busy_timeout`, `PRAGMA journal_mode=WAL` e `PRAGMA synchronous=NORMAL` para reduzir contenção.
  - Retry com backoff para operações críticas em momentos de pico (inicialização / múltiplos workers).
  - Arquivos afetados:
    - `core/logs/bank_transaction_processor.py`
    - `core/gps/player_gps_sync_service.py`
    - `core/logs/file_monitor.py`

- **Players online (Discord): retorno do modo log/spam de entrada/saída**
  - Reativado envio de mensagens individuais quando um player entra/sai (uso como log administrativo).
  - Mantida a atualização do painel de players online via edição (sem flood do painel).
  - Arquivo afetado: `core/logs/online_monitor.py`.

- **Players online (Discord): nome do canal com contador preservando prefixo editável**
  - Admin pode renomear manualmente o canal (prefixo), e o backend mantém automaticamente o sufixo `-{count}`.
  - Arquivo afetado: `core/logs/online_monitor.py`.

- **Notificações de veículos: deduplicação persistente para evitar spam**
  - Previne reenvio de notificações quando há reprocessamento da última linha ou reinícios.
  - Arquivos afetados:
    - `core/logs/database_manager.py`
    - `core/logs/log_processor.py`

## [1.12.1] - 2025-11-08

### 🧭 Monitoramento de Baús
- **Campos de coordenadas com botão copiar**: Localização atual e anterior dos baús agora são mostradas em blocos de código, permitindo copiar as coordenadas rapidamente no Discord.
- **Novos endpoints frontend**: `/api/chests` e `/api/chests/player/{steam_id}` expõem os snapshots de baús para filtros por jogador e mapas interativos.

## [1.12.0] - 2025-11-01

### 🌤️ Sistema de Monitoramento Climático Aprimorado
- **Endpoint `/api/weather/time` expandido** com dados climáticos completos
- **Retorno de todas as variáveis climáticas** do SSM.db
- **Inclusão de temperaturas** (ar e água) nas respostas
- **Informações de lua e névoa** adicionadas ao endpoint
- **Melhor aproveitamento** dos dados sincronizados

### 📊 Novos Dados Climáticos Disponíveis
- **Temperatura do Ar**: Temperatura ambiente atual
- **Temperatura da Água**: Temperatura dos corpos d'água
- **Rotação da Lua**: Estado atual do ciclo lunar
- **Densidade de Névoa**: Nível de nevoeiro no servidor
- **Estado Cumulonimbus**: Se nuvens cumulonimbus causam névoa
- **Timestamp de Sincronização**: Última atualização dos dados

### 🗄️ Otimização de Banco de Dados
- **Endpoint agora consulta SSM.db** ao invés de SCUM.db
- **Aproveitamento completo** dos dados já sincronizados
- **Redução de sobrecarga** no banco SCUM.db
- **Performance melhorada** nas consultas climáticas

### 📚 Documentação Atualizada
- **WEATHER_SYSTEM.md**: Nova seção completa para endpoint `/api/weather/time`
- **Postman Collection**: Exemplo de resposta atualizado com dados completos
- **Tabela de campos**: Documentação detalhada de todos os retornos

### 🚗 Correção no Sistema de Veículos
- **Filtro de containers secundários** implementado
- **Prevenção de duplicatas** em StorageRacks de veículos
- **Ignorar registros automáticos** de inventários de expansão
- **Melhoria na precisão** do sistema de auto-registro
- **Prevenção de duplicação por Vehicle Entity ID**: Verificação no banco de dados antes de inserir registros
- **Suporte para múltiplos containers do mesmo veículo**: Sistema ignora containers secundários (ex: carreta do trator)
- **Deduplicação robusta**: Garante que cada `vehicle_entity_id` apareça apenas uma vez, mesmo quando eventos chegam simultaneamente
- **Query recursiva otimizada**: Identificação correta do veículo real através de hierarquia de entidades

## [1.10.0] - 2025-01-15

### 🔐 Sistema de Permissões de Jogadores
- **Sistema completo** de gerenciamento de permissões implementado
- **6 tipos de permissão** suportados (Admin, Banned, Exclusive, Server Admin, Silenced, Whitelisted)
- **Sincronização automática** com arquivos INI do servidor SCUM
- **Ativação/desativação** de permissões por jogador
- **Múltiplas permissões** simultâneas para um mesmo jogador
- **Auditoria completa** com histórico de alterações

### 📊 Funcionalidades do Sistema de Permissões
- **API REST completa** com 7 endpoints principais
- **Validação de dados** e verificação de integridade
- **Formatação específica** para cada tipo de arquivo INI
- **Estatísticas detalhadas** de permissões por tipo e status
- **Sincronização manual** e automática de arquivos
- **Listagem de jogadores** por tipo de permissão
- **Sistema de notas** para rastreamento de alterações

### 🗄️ Estrutura de Banco de Dados
- **Tabela player_permissions** criada com campos completos
- **Índices otimizados** para performance de consultas
- **Relacionamento** com tabela players existente
- **Campos de auditoria** (granted_by, granted_at, revoked_by, revoked_at)
- **Sistema de notas** para documentação de alterações

### 🔧 Integração e Configuração
- **Caminhos configuráveis** para arquivos INI do servidor
- **Logs detalhados** para monitoramento e debugging
- **Validação de Steam IDs** e tipos de permissão
- **Tratamento de erros** robusto com mensagens descritivas

### 📚 Documentação e Testes
- **Documentação completa** do sistema de permissões
- **Coleção Postman** atualizada com novos endpoints
- **Exemplos de uso** e casos de teste
- **Guia de troubleshooting** para problemas comuns
- **Integração preparada** para frontend futuro

## [1.9.0] - 2025-10-27

### 🎣 Sistema de Ranking de Pescadores
- **Sistema completo** de ranking diário de pescadores implementado
- **Extração automática** de dados do banco SCUM.db
- **Geração de rankings** em 7 partes formatadas
- **Envio automático** para Discord via webhook
- **Armazenamento** no banco SSM.db para histórico
- **Execução agendada** diariamente no horário configurado
- **API endpoints** para teste manual e verificação de status

### 📊 Funcionalidades do Ranking
- **TOP 20 pescadores** mais ativos com estatísticas detalhadas
- **Ranking por espécie** de peixe (Bass, Catfish, Pike, Carp, Tuna)
- **Recordes especiais** (peixe mais pesado, mais longo, pescador mais eficiente)
- **Análise de dados** com padrões de comportamento
- **Estatísticas gerais** do servidor (total de jogadores, pescadores ativos)
- **Dicas de pesca** baseadas nos dados coletados

### 🔧 Integração e Migração
- **Migração automática** de banco de dados
- **Tabela fishing_rankings** criada automaticamente no SSM.db
- **Índices otimizados** para performance
- **Sistema robusto** que funciona mesmo se o banco for deletado
- **Integração completa** com o sistema existente

### 📚 Documentação e API
- **Documentação completa** em `docs/FISHING_RANKING_SYSTEM.md`
- **Coleção Postman atualizada** com novos endpoints
- **Endpoints de API**:
  - `POST /api/fishing-ranking/test` - Execução manual
  - `GET /api/fishing-ranking/status` - Status do sistema
- **README atualizado** com nova funcionalidade

### 🎯 Formatação e Visual
- **Formato limpo** sem separadores desnecessários
- **Alinhamento perfeito** de todas as tabelas
- **Visual profissional** e organizado
- **7 partes distintas** enviadas sequencialmente para Discord
- **Compatibilidade** com encoding de caracteres

## [1.7.0] - 2025-11-08

### 🧭 Monitoramento de Baús
- **Embed simplificado**: Removido o link/botão para SCUM Maps por inconsistências nas coordenadas fornecidas pelo jogo.
- **Entrega confiável**: Ajustados os metadados de anexos ao enviar imagens locais para o Discord, eliminando erros HTTP 400 (`{"attachments": ["0"]}`) e evitando tentativas repetidas.

### 📚 Documentação
- **CHANGELOG** atualizado com as correções do monitoramento de baús.
- **Coleção Postman 1.15.0**: descrição atualizada refletindo as alterações recentes (sem novos endpoints).

## [1.6.0] - 2025-10-22

### 🚫 Sistema de Deduplicação de Notificações Discord
- **Correção crítica** de duplicação de notificações Discord
- **Sistema de deduplicação global** implementado em todos os processadores
- **Eliminação completa** de notificações duplicadas
- **Melhoria de performance** com redução de 66% no processamento desnecessário
- **Sistema de locks** para evitar processamento simultâneo do mesmo arquivo
- **Logs de monitoramento** para acompanhar status de processamento

### 🔧 Correções Específicas
- **Admin Logs**: Corrigida duplicação de comandos admin
- **Vehicle Destruction**: Corrigida duplicação de embeds de destruição
- **Chat**: Corrigida duplicação de mensagens de chat
- **Bunkers**: Corrigida duplicação de status de bunkers
- **Chest Ownership**: Corrigida duplicação de notificações de veículos

### 📊 Melhorias de Performance
- **Processamento otimizado** com sistema de deduplicação
- **Redução de uso de recursos** (CPU e memória)
- **Interface Discord mais limpa** sem notificações duplicadas
- **Sistema mais estável** e previsível

### 📚 Documentação
- **Nova documentação** sobre sistema de deduplicação
- **Guia de troubleshooting** para problemas de duplicação
- **Exemplos práticos** de implementação
- **Diagramas de fluxo** para melhor compreensão

## [1.5.0] - 2025-10-21

### 🆕 Sistema de Monitoramento de Destruição de Veículos
- **Novo sistema completo** para monitoramento de eventos de destruição de veículos
- **Monitoramento em tempo real** de arquivos `vehicle_destruction_*.log`
- **Sistema de imagens específicas** para cada tipo de veículo
- **Mapeamento JSON** para fácil manutenção de imagens
- **Notificações Discord** com embeds coloridos e imagens dos veículos
- **Categorização por tipo de evento** (Destroyed, Disappeared, VehicleInactiveTimerReached)
- **Processamento incremental** - não reprocessa eventos antigos
- **Integração com banco SCUM.db** para dados adicionais

### 🖼️ Sistema de Imagens
- **Pasta dedicada** para imagens de destruição: `data/imagens/carros/vehicle-log/`
- **Mapeamento JSON** para associação veículo-imagem
- **Imagens específicas** para cada tipo de veículo
- **Fallback automático** para veículos sem imagem
- **Suporte a 15+ tipos de veículos** (WolfsWagen, Laika, Dirtbike, etc.)

### 🎨 Categorização de Eventos
- **⚫ Destroyed** (preto) - Veículo destruído
- **🔴 Disappeared** (vermelho) - Veículo desaparecido
- **🟡 VehicleInactiveTimerReached** (amarelo) - Veículo inativo

### 📊 Controle de Estado
- **ID único por evento** - timestamp + vehicle_id
- **Prevenção de duplicatas** - Sistema robusto contra reprocessamento
- **Atualização de status** na tabela de propriedade atual
- **Logs detalhados** para monitoramento e debug

### 🌐 Novos Endpoints da API
- **GET** `/api/vehicles/destruction/events` - Listar eventos de destruição
- **GET** `/api/vehicles/destruction/stats` - Estatísticas de destruição
- **POST** `/api/vehicles/destruction/process` - Processar log manualmente

### 📚 Documentação Atualizada
- **Nova documentação** específica para vehicle destruction
- **Postman collection** atualizada com novos endpoints
- **Exemplos práticos** de uso e configuração
- **Guia de troubleshooting** para problemas comuns

## [1.4.0] - 2025-10-20

### 🆕 Sistema de Monitoramento de Comandos Admin
- **Novo sistema completo** para monitoramento de comandos de administradores
- **Monitoramento em tempo real** de arquivos `admin_*.log`
- **Categorização inteligente** com 6 categorias (Teleport, Spawn, God Mode, Info, Command, Default)
- **Notificações Discord** com embeds coloridos e emojis específicos
- **Sistema de controle de duplicatas** baseado em timestamp + steam_id
- **Processamento incremental** - não reprocessa comandos antigos
- **Configuração via webhook** em `data/webhooks.json`

### 🎨 Categorização de Comandos
- **🚀 Teleport** (roxo) - Comandos de teleporte
- **🎁 Spawn** (amarelo) - Spawn de itens
- **🛡️ God Mode** (vermelho) - Comandos de god mode
- **👁️ Info** (azul) - Informações de jogadores
- **⚡ Command** (laranja) - Outros comandos
- **📋 Default** (verde) - Comandos não categorizados

### 📊 Controle de Estado
- **ID único por comando** - timestamp + steam_id
- **Arquivo de controle** - `data/admin/lastAdminLogLine.json`
- **Prevenção de duplicatas** - Sistema robusto contra reprocessamento
- **Detecção de mudanças** - Polling a cada 5 segundos

### 📚 Documentação
- **Nova documentação** - `docs/ADMIN_LOGS_SYSTEM.md`
- **Postman collection** atualizada com endpoints de admin logs
- **README principal** atualizado com nova funcionalidade
- **Exemplos de uso** e troubleshooting

### 🔧 Arquivos Criados/Modificados
- `core/logs/admin_log_processor.py` - Processador principal
- `core/logs/log_processor.py` - Integração com sistema de logs
- `core/logs/file_monitor.py` - Monitoramento de admin_*.log
- `data/admin/lastAdminLogLine.json` - Controle de estado
- `data/webhooks.json` - Configuração de webhook adminlog

## [1.3.1] - 2025-10-19

### 🧹 Limpeza e Organização
- **Limpeza de scripts de teste** - Removidos 32 scripts desnecessários
- **Mantidos apenas 7 scripts essenciais** para testes funcionais
- **Projeto mais limpo** e organizado para desenvolvimento
- **Foco nas funcionalidades principais** do sistema

### 📊 Scripts de Teste Mantidos
- `test_scalability.py` - Teste de compatibilidade e escalabilidade
- `test_players.py` - Sistema de jogadores completo
- `test_log_processing.py` - Processamento de logs
- `test_server_control.py` - Controle de servidor
- `test_notifications.py` - Sistema de notificações
- `test_vehicle_system.py` - Sistema de veículos
- `test_steam_api_simple.py` - Steam API

### 🎯 Benefícios da Limpeza
- **Redução de 82%** nos scripts de teste
- **Manutenção facilitada** - Menos código para manter
- **Estrutura profissional** - Projeto mais focado
- **Desenvolvimento mais eficiente** - Apenas testes essenciais

## [1.3.0] - 2025-10-19

### 🆕 Adicionado - Sistema de Auto-Registro de Veículos
- **Monitoramento automático** de logs `chest_ownership_*.log`
- **Detecção de eventos** de veículos trancados e transferências
- **Duplo identificador**: Container ID + Vehicle Entity ID
- **Notificações Discord** com embeds ricos e imagens de veículos
- **Banco de dados expandido** com tabelas de histórico e propriedade atual
- **API completa** para consulta de veículos registrados
- **Sistema híbrido de monitoramento** (watchdog + polling)
- **Processamento incremental** para evitar duplicatas

### 🗄️ Banco de Dados - Novas Tabelas
- **`vehicle_ownership_history`** - Histórico completo de mudanças de propriedade
- **`vehicle_current_ownership`** - Propriedade atual de cada veículo
- **Índices otimizados** para performance de consultas

### 🚗 Mapeamento de Veículos
- **17 tipos de veículos** suportados com imagens correspondentes
- **Mapeamento automático** entre logs e dados do SCUM.db
- **Nomes amigáveis** para exibição em português
- **Sistema de fallback** para veículos não mapeados

### 💬 Notificações Discord Aprimoradas
- **Embeds específicos** para veículos trancados vs transferidos
- **Imagens dos veículos** integradas nas notificações
- **Informações completas**: jogador, localização, IDs duplos
- **Prevenção de spam** com sistema de cooldown

### 🌐 API Endpoints - Sistema de Veículos
- **`GET /api/vehicles/ownership/history`** - Histórico de propriedade
- **`GET /api/vehicles/ownership/current`** - Propriedade atual
- **`GET /api/vehicles/stats`** - Estatísticas de veículos
- **Filtros avançados** por jogador, tipo de veículo, tipo de evento

### 📚 Documentação
- **Documentação completa** do sistema de veículos
- **Postman Collection** atualizada com novos endpoints
- **Exemplos de uso** e troubleshooting
- **Estrutura do banco** documentada

### 🔧 Melhorias Técnicas
- **Sistema de polling** para arquivos em uso pelo SCUM
- **Processamento incremental** de logs
- **Prevenção de duplicatas** no banco de dados
- **Logs detalhados** para debugging
- **Tratamento de erros** robusto

## [1.2.0] - 2025-01-15

### 🆕 Adicionado - Escalabilidade
- **Sistema de Identidade Única** para cada backend
- **Módulo de Comunicação** para controle centralizado
- **Sistema de Heartbeat** para monitoramento
- **Comandos Remotos** do frontend central
- **Validação de Licença** automática
- **Novos Endpoints de API**:
  - `GET /api/identity` - Identidade do backend
  - `GET /api/health/detailed` - Health check detalhado
  - `POST /api/remote/command` - Comandos remotos
  - `GET /api/owner/info` - Informações do proprietário
  - `POST /api/owner/info` - Atualizar proprietário

### 🔧 Estrutura Expandida
- **Módulo de Identidade** (`core/identity/`)
  - `BackendIdentity` - Geração de ID único
  - `OwnerManager` - Gerenciamento do proprietário
- **Módulo de Comunicação** (`core/communication/`)
  - `HeartbeatManager` - Sistema de heartbeat
  - `RemoteCommandHandler` - Comandos remotos
  - `LicenseValidator` - Validação de licença

### 📄 Configuração Atualizada
- **Novos campos** no `config.json` para escalabilidade
- **Modo individual** mantido por padrão (`auto_register: false`)
- **Compatibilidade total** com configurações existentes

### 🛠️ Scripts de Apoio
- **`migrate_to_scalable.py`** - Migração automática
- **`test_scalability.py`** - Testes de compatibilidade
- **Backup automático** de configurações

### 📚 Documentação
- **Documentação completa** de escalabilidade
- **Collection Postman** atualizada com novos endpoints
- **Exemplos de uso** para todos os novos endpoints
- **Guia de migração** passo a passo

### ✅ Compatibilidade
- **Zero impacto** nas funcionalidades existentes
- **Modo individual** mantido por padrão
- **Testes de compatibilidade** incluídos
- **Migração opcional** e reversível

## [1.1.0] - 2025-10-16

### ✨ Adicionado
- **Sistema de Webhooks Discord** completo
- Notificações automáticas para todos os eventos do servidor
- Suporte a múltiplos webhooks configuráveis
- Rate limiting e retry automático para webhooks
- Eventos de webhook para:
  - Inicialização do backend
  - Controle do servidor (iniciar, parar, reiniciar)
  - Agendador de reinicializações
- Documentação completa do sistema de webhooks
- Exemplos de uso e troubleshooting

### 🔧 Corrigido
- **Endpoint de restart** agora envia webhooks corretamente
- Verificação de status do servidor antes do restart
- Tratamento de erros melhorado nos webhooks
- Logs mais detalhados para debugging

### 📚 Documentação
- Atualizada documentação da API com informações sobre webhooks
- Criada documentação específica para sistema de webhooks
- Atualizados exemplos cURL, Postman e Python
- Adicionada seção de troubleshooting para webhooks

### 🎯 Melhorias
- Sistema de webhooks mais robusto com retry automático
- Mensagens Discord mais informativas com embeds
- Cores e emojis apropriados para cada tipo de evento
- Rate limiting para evitar spam no Discord

## [1.0.0] - 2025-10-15

### ✨ Adicionado
- **Backend Python** completo para controle de servidor SCUM
- Sistema de controle do servidor (iniciar, parar, reiniciar)
- Integração com NSSM para gerenciamento de serviços Windows
- Sistema de agendamento com restart automático
- API REST completa com endpoints documentados
- Sistema de logging estruturado
- Configuração centralizada via JSON
- Integração com SteamCMD para atualizações
- Sistema de identificação única para backends
- Documentação completa da API
- Exemplos de uso (cURL, Postman, Python)
- Sistema de health check
- Monitoramento de processos e status do servidor

### 🏗️ Arquitetura
- Estrutura modular com separação de responsabilidades
- Sistema de configuração flexível
- Logging estruturado em JSON
- Tratamento robusto de erros
- Sistema de callbacks para notificações

### 📦 Empacotamento
- Preparado para distribuição como executável .exe
- Dependências Python documentadas
- Scripts de inicialização
- Configuração de ambiente

---

## 🔄 Tipos de Mudanças

- **✨ Adicionado** - para novas funcionalidades
- **🔧 Corrigido** - para correções de bugs
- **📚 Documentação** - para mudanças na documentação
- **🎯 Melhorias** - para melhorias em funcionalidades existentes
- **⚠️ Deprecado** - para funcionalidades que serão removidas
- **🗑️ Removido** - para funcionalidades removidas
- **🔒 Segurança** - para correções de segurança
