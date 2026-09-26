# 🎯 Contexto do Projeto: SSM Plugin Framework

## ⚠️ AVISO IMPORTANTE - STATUS DO PROJETO

**🚨 ESTE PROJETO ESTÁ APENAS NA FASE DE ESTUDO E PLANEJAMENTO 🚨**

- ❌ **NÃO IMPLEMENTAR CÓDIGO AINDA**
- ❌ **NÃO CRIAR ESTRUTURA DE DIRETÓRIOS**
- ❌ **NÃO DESENVOLVER FUNCIONALIDADES**
- ✅ **APENAS ESTUDAR E PLANEJAR**
- ✅ **ANALISAR VIABILIDADE**
- ✅ **DOCUMENTAR DECISÕES**

**Este documento serve apenas para CONTEXTO e PLANEJAMENTO. Qualquer implementação deve ser APROVADA ANTES.**

---

## 📋 Visão Geral do Projeto

Este documento serve como **contexto inicial** para o **planejamento** do **SSM Plugin Framework** - uma alternativa ao Oxygen para criar plugins no servidor SCUM.

**Status atual:** Apenas estudo e planejamento. Nenhuma implementação foi aprovada ainda.

---

## 🎯 Por Que Este Projeto Existe?

### **Problema:**
- **Oxygen** (framework de plugins para SCUM) não está disponível publicamente
- Há **relatos de vírus** no Oxygen
- Não há alternativa confiável para criar plugins no SCUM
- Admins precisam usar **bots externos** (lentos, instáveis, ocupam slot de jogador)

### **Solução:**
Criar nosso **próprio framework de plugins** que seja:
- ✅ **Open source** - Código auditável e transparente
- ✅ **Seguro** - Desenvolvido por nós, sem riscos
- ✅ **Integrado com SSM** - Funciona nativamente com nosso sistema
- ✅ **Flexível** - Suporta Python e C# (futuro)

---

## 🏗️ O Que Estamos Construindo?

### **SSM Plugin Framework**

Um framework que permite criar **plugins** para o servidor SCUM, similar ao Oxide (Rust) ou Oxygen (SCUM), mas:

1. **Desenvolvido por nós** - Controle total sobre o código
2. **Integrado com SSM** - Acesso direto ao SSM.db e funcionalidades do SSM
3. **Python-first** - Nossa stack principal é Python
4. **Incremental** - Começamos simples e evoluímos

---

## 📊 Arquitetura Planejada

### **Componentes Principais:**

```
SSM Plugin Framework
├── Plugin Manager (Python)
│   ├── Carrega/descarrega plugins
│   ├── Gerencia ciclo de vida
│   └── Expõe API para plugins
│
├── Plugin API (Python)
│   ├── Interface para plugins
│   ├── Acesso ao SCUM.db (read-only inicialmente)
│   ├── Acesso ao SSM.db
│   └── Execução de comandos (futuro)
│
├── SCUM Integration (Python)
│   ├── Monitor do SCUM.db
│   ├── Detecção de eventos
│   └── Execução de comandos
│
└── Plugins (Python/C# futuro)
    ├── Plugins Python (.py)
    └── Plugins C# (.dll) - futuro
```

### **Fluxo de Funcionamento:**

```
1. SSM Backend inicia Plugin Manager
2. Plugin Manager carrega plugins do diretório
3. Plugins recebem API para interagir
4. SCUM Integration monitora SCUM.db
5. Eventos são detectados e notificam plugins
6. Plugins executam ações via API
```

---

## 🎯 Funcionalidades Planejadas

### **Fase 1: MVP (Inicial)**
- ✅ Sistema básico de plugins Python
- ✅ Carregamento/descarregamento de plugins
- ✅ API para ler SCUM.db e SSM.db
- ✅ Queries customizadas
- ✅ Sistema de logs integrado
- ✅ Monitoramento básico de eventos (via SCUM.db)

### **Fase 2: Tempo Real**
- [ ] Monitoramento de logs do servidor
- [ ] Detecção de eventos em tempo real
- [ ] Sistema de comandos de chat
- [ ] Execução de comandos no servidor (quando parado)
- [ ] Hot-reload de plugins
- [ ] Sistema de eventos completo

### **Fase 3: Avançado**
- [ ] DLL injection (se necessário)
- [ ] Hooks diretos de eventos do servidor
- [ ] Execução de comandos em tempo real
- [ ] Suporte a plugins C#
- [ ] Painel web integrado
- [ ] Sistema de permissões

---

## 🔧 Decisões Técnicas Importantes

### **1. Abordagem Incremental**

**Por quê:**
- Começamos simples (via banco de dados)
- Evoluímos conforme necessidade
- Reduz risco de falhas

**Estratégia:**
- **Fase 1:** Trabalhar via SCUM.db (read-only, monitoramento)
- **Fase 2:** Adicionar monitoramento de logs (tempo real)
- **Fase 3:** DLL injection apenas se necessário

### **2. Python-First**

**Por quê:**
- SSM Backend é Python
- Facilita integração
- Mais simples de desenvolver

**Futuro:**
- Suporte a C# para performance (se necessário)
- Plugins C# via IronPython ou DLL injection

### **3. Sem DLL Injection Inicial**

**Por quê:**
- Complexo e arriscado
- Pode causar instabilidade
- Requer conhecimento avançado

**Alternativa:**
- Trabalhar via SCUM.db (mais seguro)
- Monitorar logs do servidor
- Evoluir para DLL injection depois (se necessário)

---

## 📚 Estrutura do Projeto (Planejada)

```
ssm-plugin-framework/
├── core/
│   ├── plugin_manager/          # Gerenciador principal
│   │   ├── manager.py           # SSMPluginManager
│   │   └── plugin_api.py        # API para plugins
│   │
│   └── scum_integration/        # Integração SCUM
│       ├── db_monitor.py        # Monitor do SCUM.db
│       ├── log_monitor.py       # Monitor de logs (Fase 2)
│       └── command_executor.py  # Execução de comandos
│
├── plugins/
│   ├── installed/               # Plugins instalados
│   └── examples/                # Exemplos
│
├── docs/                        # Documentação
│   ├── SSM_PLUGIN_FRAMEWORK_PROPOSAL.md
│   └── SSM_PLUGIN_FRAMEWORK_ARCHITECTURE.md
│
└── tests/                       # Testes
```

---

## 🔌 Como Plugins Funcionarão

### **Interface de Plugin (Python):**

```python
class MyPlugin:
    """Exemplo de plugin"""
    
    def __init__(self):
        self.name = "MyPlugin"
        self.version = "1.0.0"
        self.author = "Seu Nome"
        self.api = None
        
    def on_load(self, api):
        """Chamado quando plugin é carregado"""
        self.api = api
        self.api.log("Plugin carregado!")
        
    def on_unload(self):
        """Chamado quando plugin é descarregado"""
        self.api.log("Plugin descarregado!")
        
    def on_player_connected(self, event_data):
        """Hook quando jogador conecta"""
        steam_id = event_data.get("steam_id")
        nickname = event_data.get("nickname")
        self.api.log(f"{nickname} conectou!")
```

### **API Disponível para Plugins:**

```python
# Informações
api.get_scum_db_path()
api.get_ssm_db_path()

# Queries
api.query_scum_db(query, params)  # Read-only
api.query_ssm_db(query, params)

# Jogadores
api.get_player_by_steam_id(steam_id)
api.get_online_players()
api.get_player_skills(steam_id)

# Logging
api.log(message, level="info")

# Futuro (Fase 2+)
api.execute_command(command)
api.spawn_item(steam_id, item, quantity)
api.set_player_skill(steam_id, skill, level, exp)
```

---

## 🔗 Integração com SSM

### **Como se Integra:**

1. **SSM Backend** → Inicializa Plugin Manager
2. **Plugin Manager** → Carrega plugins automaticamente
3. **SCUM Integration** → Monitora SCUM.db e logs
4. **Plugins** → Recebem eventos e executam ações
5. **SSM Backend** → Pode chamar plugins via API

### **Acesso aos Bancos:**

- **SCUM.db** - Read-only inicialmente (segurança)
- **SSM.db** - Read/write (integração completa)

---

## 🎯 Objetivos do Projeto

### **Curto Prazo (MVP):**
1. Sistema básico de plugins funcionando
2. Plugins podem ler dados do SCUM.db
3. Plugins podem ler/escrever no SSM.db
4. Sistema de eventos básico
5. Documentação completa

### **Médio Prazo (Fase 2):**
1. Eventos em tempo real
2. Comandos de chat
3. Execução de comandos no servidor
4. Hot-reload de plugins

### **Longo Prazo (Fase 3):**
1. DLL injection (se necessário)
2. Hooks diretos de eventos
3. Suporte a plugins C#
4. Painel web integrado

---

## ⚠️ Desafios Técnicos Conhecidos

### **1. DLL Injection**
- **Desafio:** Injetar código no processo SCUM
- **Solução:** Usar bibliotecas como `EasyHook` ou `DllInjection`
- **Alternativa:** Trabalhar apenas via banco (mais simples)

### **2. Hooks de Eventos**
- **Desafio:** Interceptar eventos do servidor
- **Solução:** Monitorar SCUM.db + logs do servidor
- **Alternativa:** Usar Harmony para hooks de código (C#)

### **3. Comandos de Chat**
- **Desafio:** Interceptar mensagens de chat
- **Solução:** Monitorar logs do servidor
- **Alternativa:** Hook direto no código (mais complexo)

### **4. Execução de Comandos**
- **Desafio:** Executar comandos no servidor
- **Solução:** Via banco (quando parado) ou RCON (se disponível)
- **Alternativa:** DLL injection para acesso direto

---

## 📖 Documentação de Referência

### **Documentos Criados (no projeto SSM):**

1. **`SSM_PLUGIN_FRAMEWORK_PROPOSAL.md`**
   - Proposta completa do projeto
   - Objetivos e funcionalidades
   - Estratégia de implementação

2. **`SSM_PLUGIN_FRAMEWORK_ARCHITECTURE.md`**
   - Arquitetura técnica detalhada
   - Decisões de design
   - Fluxos de dados

3. **`OXIDE_SCUM_COMPATIBILITY.md`**
   - Análise sobre Oxide no SCUM
   - Por que não funciona
   - Comparação com Oxygen

4. **`OXYGEN_FRAMEWORK_ANALYSIS.md`**
   - Análise do Oxygen
   - Como funciona (teoricamente)
   - Por que precisamos de alternativa

### **Referências Externas:**

- **Oxide (Rust):** https://umod.org/ - Referência de arquitetura
- **Oxygen (SCUM):** https://github.com/Jemixs/Oxygen-scum-server-plugin - Repositório (WIP, sem releases)

---

## 🚀 Como Começar o Desenvolvimento (QUANDO APROVADO)

### ⚠️ **NÃO IMPLEMENTAR AINDA - APENAS PLANEJAMENTO**

Estes passos são apenas **planejamento** para quando o projeto for aprovado:

### **Passo 1: Estrutura Base** (Planejado)
- Criar estrutura de diretórios
- Configurar ambiente Python
- Criar arquivos base (__init__.py, etc.)

### **Passo 2: Plugin Manager** (Planejado)
- Implementar SSMPluginManager
- Sistema de carregamento de plugins
- Gerenciamento de ciclo de vida

### **Passo 3: Plugin API** (Planejado)
- Implementar PluginAPI
- Métodos de acesso aos bancos
- Sistema de logging

### **Passo 4: SCUM Integration** (Planejado)
- Monitor do SCUM.db
- Detecção de eventos básicos
- Sistema de notificações

### **Passo 5: Plugin de Exemplo** (Planejado)
- Criar plugin de exemplo funcional
- Testar integração completa
- Documentar uso

**⚠️ IMPORTANTE:** Estes passos são apenas **planejamento**. NÃO implementar até que seja explicitamente solicitado e aprovado.

---

## 🔒 Segurança

### **Princípios:**
1. **Read-only no SCUM.db** inicialmente (prevenir corrupção)
2. **Validação de plugins** antes de carregar
3. **Sandbox de execução** (isolamento)
4. **Logs de auditoria** (todas as ações)
5. **Código open source** (transparência)

---

## 📝 Notas Importantes

### **Sobre o SCUM.db:**
- SCUM.db é o banco de dados do servidor SCUM
- Localização típica: `C:\Servers\Scum\SCUM\Saved\SaveFiles\SCUM.db`
- Precisa de cuidado ao modificar (pode corromper se servidor rodando)
- Por isso começamos com read-only

### **Sobre o SSM.db:**
- SSM.db é nosso banco de dados
- Podemos ler/escrever livremente
- Integração completa com SSM Backend

### **Sobre Eventos:**
- Eventos são detectados monitorando mudanças no SCUM.db
- Exemplos: login, logout, morte, etc.
- Plugins podem registrar handlers para eventos

---

## 🎯 Status Atual

**Fase:** 📚 ESTUDO E PLANEJAMENTO (NÃO IMPLEMENTAR AINDA)

**Status:** 
- ✅ Análise de viabilidade
- ✅ Documentação de planejamento
- ✅ Estudo de arquitetura
- ❌ **NENHUMA IMPLEMENTAÇÃO APROVADA**
- ❌ **NENHUM CÓDIGO DEVE SER CRIADO**

**Próximo Passo:** Continuar estudando e planejando. Aguardar aprovação para iniciar desenvolvimento.

**Documentação:** Completa para planejamento

**Código:** ❌ **NÃO IMPLEMENTAR** - Apenas planejamento e estudo

---

## 💡 Dicas para Desenvolvimento (QUANDO APROVADO)

### ⚠️ **NÃO DESENVOLVER AINDA - APENAS ESTUDO**

Estas dicas são para **quando o projeto for aprovado**:

1. **Comece simples** - MVP primeiro, depois evolua
2. **Teste incrementalmente** - Cada componente separadamente
3. **Documente tudo** - Facilita manutenção futura
4. **Foque em segurança** - Read-only inicialmente
5. **Use o SSM como referência** - Já temos integração com SCUM.db

**⚠️ LEMBRETE:** Estamos apenas **estudando e planejando**. Não implementar código ainda.

---

---

## 🚨 RESUMO FINAL - LEIA ANTES DE QUALQUER AÇÃO

### **STATUS ATUAL:**
- 📚 **FASE DE ESTUDO E PLANEJAMENTO**
- ❌ **NÃO IMPLEMENTAR CÓDIGO**
- ❌ **NÃO CRIAR ARQUIVOS**
- ❌ **NÃO DESENVOLVER FUNCIONALIDADES**
- ✅ **APENAS ESTUDAR E PLANEJAR**
- ✅ **ANALISAR VIABILIDADE**
- ✅ **DOCUMENTAR DECISÕES**

### **O QUE FAZER:**
1. ✅ Ler e entender o contexto
2. ✅ Analisar a viabilidade
3. ✅ Estudar as opções técnicas
4. ✅ Documentar dúvidas e decisões
5. ✅ Aguardar aprovação explícita antes de implementar

### **O QUE NÃO FAZER:**
1. ❌ Criar código Python
2. ❌ Criar estrutura de diretórios
3. ❌ Implementar funcionalidades
4. ❌ Criar arquivos de exemplo
5. ❌ Iniciar desenvolvimento sem aprovação

---

**Última atualização:** 2025-01-12  
**Status:** 📚 ESTUDO E PLANEJAMENTO - NÃO IMPLEMENTAR AINDA  
**Projeto:** Separado do SSM Backend (novo repositório)  
**Ação Permitida:** Apenas estudo, análise e planejamento
