# 🚀 Proposta: Framework de Plugins SSM para SCUM

## 📋 Visão Geral

Criar um **framework de plugins próprio** para SCUM, similar ao Oxygen, mas:
- ✅ **Desenvolvido por nós** (controle total)
- ✅ **Open source** (transparência)
- ✅ **Integrado com SSM** (nossa stack)
- ✅ **Focado em segurança** (sem riscos de vírus)
- ✅ **Python/C# híbrido** (flexibilidade)

---

## 🎯 Objetivos

### **Funcionalidades Principais:**
1. **Sistema de plugins** (C# ou Python)
2. **Hooks de eventos** do servidor
3. **Comandos customizados** via chat
4. **API REST** para integração com SSM
5. **Painel web** (opcional)
6. **Hot-reload** de plugins

### **Integração com SSM:**
- Plugins podem acessar SSM.db
- SSM pode executar comandos via plugins
- Sincronização bidirecional
- Logs centralizados

---

## 🏗️ Arquitetura Proposta

### **Opção 1: Arquitetura Híbrida (Recomendada)**

```
┌─────────────────────────────────────────────┐
│  SCUM Server (SCUMServer.exe)                │
│  ┌───────────────────────────────────────┐  │
│  │  SSM Plugin Framework (DLL)            │  │
│  │  - Carrega plugins                     │  │
│  │  - Gerencia hooks                      │  │
│  │  - Expõe API REST                      │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │  Plugins/                              │  │
│  │  ├── Plugin1.dll (C#)                 │  │
│  │  └── Plugin2.py (Python via IronPython)│ │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                    │
                    │ HTTP REST API
                    ▼
┌─────────────────────────────────────────────┐
│  SSM Backend (Python)                       │
│  - Faz requisições HTTP                    │
│  - Acessa SSM.db                           │
│  - Gerencia lógica de negócio              │
└─────────────────────────────────────────────┘
```

### **Opção 2: Arquitetura via Banco de Dados**

```
┌─────────────────────────────────────────────┐
│  SSM Backend (Python)                       │
│  - Monitora SCUM.db                        │
│  - Executa ações via SQL                    │
│  - Gerencia plugins Python                 │
└─────────────────────────────────────────────┘
                    │
                    │ Monitora/Modifica
                    ▼
┌─────────────────────────────────────────────┐
│  SCUM.db                                     │
│  - Dados do servidor                        │
│  - Modificações via SQL                     │
└─────────────────────────────────────────────┘
                    │
                    │ Lê/Escreve
                    ▼
┌─────────────────────────────────────────────┐
│  SCUM Server (SCUMServer.exe)               │
└─────────────────────────────────────────────┘
```

**Vantagem:** Não precisa de DLL injection, funciona via banco.

---

## 🔧 Implementação Técnica

### **Componente 1: SSM Plugin Core (C#)**

**Arquitetura:**
```csharp
namespace SSM.PluginFramework
{
    // Classe base para plugins
    public abstract class SSMPlugin
    {
        public abstract void OnLoad();
        public abstract void OnUnload();
        
        // Hooks de eventos
        public virtual void OnPlayerConnected(PlayerInfo player) { }
        public virtual void OnPlayerDisconnected(PlayerInfo player) { }
        public virtual void OnChatMessage(PlayerInfo player, string message) { }
    }
    
    // API para plugins
    public class PluginAPI
    {
        public void SendMessageToPlayer(string steamId, string message);
        public void ExecuteServerCommand(string command);
        public void SpawnItem(string steamId, string itemClass, int quantity);
        public void SetPlayerSkill(string steamId, string skill, int level, float exp);
    }
}
```

### **Componente 2: SSM Plugin Manager (Python)**

**Arquitetura:**
```python
class SSMPluginManager:
    """Gerencia plugins e integração com SSM"""
    
    def __init__(self, config, path_helper, logger):
        self.config = config
        self.scum_db_path = path_helper.get_scum_db_path()
        self.ssm_db_path = path_helper.get_ssm_db_path()
        self.plugins = {}
        
    def load_plugin(self, plugin_path):
        """Carregar plugin (C# DLL ou Python)"""
        pass
        
    def execute_command(self, command, params):
        """Executar comando no servidor via banco ou API"""
        pass
```

### **Componente 3: Integração com SCUM.db**

**Estratégia:**
1. **Monitorar SCUM.db** para eventos
2. **Modificar SCUM.db** para ações
3. **Usar comandos de console** quando possível
4. **API REST** como alternativa

---

## 📝 Estrutura de Projeto

```
SSM Plugin Framework/
├── core/
│   ├── plugin_core/              # Framework C# (DLL)
│   │   ├── SSM.PluginFramework.csproj
│   │   ├── SSMPlugin.cs          # Classe base
│   │   ├── PluginAPI.cs          # API para plugins
│   │   └── PluginLoader.cs      # Carregador de plugins
│   │
│   ├── plugin_manager/           # Manager Python
│   │   ├── __init__.py
│   │   ├── plugin_manager.py     # Gerenciador principal
│   │   ├── plugin_loader.py      # Carregador
│   │   └── plugin_api.py          # API REST
│   │
│   └── scum_integration/          # Integração SCUM
│       ├── scum_db_monitor.py    # Monitora SCUM.db
│       ├── scum_db_writer.py     # Escreve no SCUM.db
│       └── scum_command_executor.py  # Executa comandos
│
├── plugins/                       # Plugins de exemplo
│   ├── example_plugin/           # Plugin C#
│   └── example_python/           # Plugin Python
│
├── tools/                         # Ferramentas
│   ├── plugin_creator.py         # Gerador de plugins
│   └── plugin_tester.py          # Testador
│
└── docs/                         # Documentação
    └── PLUGIN_DEVELOPMENT.md
```

---

## 🎯 Funcionalidades por Fase

### **Fase 1: Base (MVP)**
- [ ] Monitorar SCUM.db para eventos
- [ ] Executar comandos via SQL (quando servidor parado)
- [ ] Sistema básico de plugins Python
- [ ] API REST simples

### **Fase 2: Integração**
- [ ] DLL injection (se necessário)
- [ ] Hooks de eventos em tempo real
- [ ] Sistema de comandos de chat
- [ ] Hot-reload de plugins

### **Fase 3: Avançado**
- [ ] Suporte a plugins C#
- [ ] Painel web integrado
- [ ] Sistema de permissões
- [ ] Marketplace de plugins

---

## 🔒 Segurança

### **Medidas de Segurança:**
1. **Validação de plugins**
   - Assinatura digital
   - Verificação de código
   - Sandbox de execução

2. **Isolamento**
   - Plugins rodam em contexto isolado
   - Sem acesso direto ao sistema
   - Permissões granulares

3. **Auditoria**
   - Logs de todas as ações
   - Rastreamento de comandos
   - Alertas de segurança

---

## 💡 Vantagens da Nossa Solução

### **vs Oxygen:**
- ✅ **Open source** - Código visível e auditável
- ✅ **Integrado com SSM** - Não precisa de integração externa
- ✅ **Desenvolvido por nós** - Controle total
- ✅ **Focado em segurança** - Sem riscos de vírus
- ✅ **Python nativo** - Nossa stack principal

### **vs Bots Externos:**
- ✅ **Não ocupa slot** de jogador
- ✅ **Mais rápido** - Acesso direto
- ✅ **Mais estável** - Sem simulação de cliente
- ✅ **Mais funcionalidades** - Acesso completo

---

## 🚀 Plano de Implementação

### **Etapa 1: Prova de Conceito**
1. Criar monitor básico do SCUM.db
2. Detectar eventos (login, logout, etc.)
3. Executar ações simples via SQL
4. Testar com servidor parado

### **Etapa 2: Sistema de Plugins**
1. Criar estrutura base de plugins
2. Sistema de carregamento
3. API básica para plugins
4. Plugin de exemplo funcionando

### **Etapa 3: Integração em Tempo Real**
1. DLL injection (se necessário)
2. Hooks de eventos
3. Comandos de chat
4. Hot-reload

### **Etapa 4: Integração com SSM**
1. API REST
2. Acesso ao SSM.db
3. Sincronização bidirecional
4. Logs centralizados

---

## 📚 Tecnologias Necessárias

### **Backend (Python):**
- `sqlite3` - Acesso ao SCUM.db
- `flask` ou `fastapi` - API REST
- `watchdog` - Monitoramento de arquivos
- `psutil` - Gerenciamento de processos

### **Plugin Core (C#):**
- `.NET 8.0` - Framework
- `System.Reflection` - Carregamento dinâmico
- `System.Net.Http` - API REST
- `Harmony` (opcional) - Para hooks avançados

### **Ferramentas:**
- Visual Studio / VS Code
- .NET SDK 8.0
- Python 3.10+

---

## ⚠️ Desafios Técnicos

### **1. DLL Injection**
- **Desafio:** Injetar código no processo SCUM
- **Solução:** Usar bibliotecas como `EasyHook` ou `DllInjection`
- **Alternativa:** Trabalhar apenas via banco (mais simples)

### **2. Hooks de Eventos**
- **Desafio:** Interceptar eventos do servidor
- **Solução:** Monitorar SCUM.db + logs do servidor
- **Alternativa:** Usar Harmony para hooks de código

### **3. Comandos de Chat**
- **Desafio:** Interceptar mensagens de chat
- **Solução:** Monitorar logs do servidor
- **Alternativa:** Hook direto no código (mais complexo)

### **4. Execução de Comandos**
- **Desafio:** Executar comandos no servidor
- **Solução:** Via banco (quando parado) ou RCON (se disponível)
- **Alternativa:** DLL injection para acesso direto

---

## 🎯 Estratégia Recomendada

### **Abordagem Incremental:**

**Fase 1: Via Banco (Mais Simples)**
- Monitorar SCUM.db
- Modificar via SQL
- Funciona com servidor parado
- Base sólida para evoluir

**Fase 2: Via Logs (Tempo Real)**
- Monitorar logs do servidor
- Detectar eventos
- Executar ações via banco
- Funciona com servidor rodando (leitura)

**Fase 3: DLL Injection (Avançado)**
- Injetar código no servidor
- Hooks diretos
- Acesso completo
- Requer mais conhecimento técnico

---

## 📋 Checklist de Desenvolvimento

### **MVP (Fase 1):**
- [ ] Criar estrutura de projeto
- [ ] Monitor básico do SCUM.db
- [ ] Sistema de plugins Python
- [ ] API REST básica
- [ ] Plugin de exemplo
- [ ] Documentação básica

### **Fase 2:**
- [ ] Monitoramento de logs
- [ ] Detecção de eventos em tempo real
- [ ] Sistema de comandos
- [ ] Hot-reload
- [ ] Integração com SSM

### **Fase 3:**
- [ ] DLL injection (se necessário)
- [ ] Hooks avançados
- [ ] Suporte C#
- [ ] Painel web
- [ ] Sistema de permissões

---

## 🔗 Integração com SSM Existente

### **Como se Integra:**

1. **SSM Backend** → Chama API do Plugin Framework
2. **Plugin Framework** → Executa ações no SCUM
3. **SSM Backend** → Recebe eventos via webhook
4. **SSM.db** → Sincronizado com eventos

### **Exemplo de Uso:**

```python
# No SSM Backend
from core.plugin_manager import SSMPluginManager

plugin_manager = SSMPluginManager(config, path_helper, logger)

# Executar comando
plugin_manager.execute_command("spawn_item", {
    "steam_id": "76561198040636105",
    "item": "Weapon_M9",
    "quantity": 1
})

# Registrar hook
@plugin_manager.on_player_connected
def handle_player_connected(player):
    # Lógica do SSM
    pass
```

---

## 🎯 Conclusão

Criar nossa própria solução é **viável e recomendado** porque:

1. ✅ **Controle total** - Desenvolvido por nós
2. ✅ **Segurança** - Código auditável
3. ✅ **Integração** - Nativo com SSM
4. ✅ **Flexibilidade** - Adaptável às nossas necessidades
5. ✅ **Open source** - Transparência total

**Próximo passo:** Começar com Fase 1 (MVP via banco) e evoluir incrementalmente.

---

**Última atualização:** 2025-01-12  
**Status:** Proposta inicial - Aguardando aprovação para desenvolvimento
