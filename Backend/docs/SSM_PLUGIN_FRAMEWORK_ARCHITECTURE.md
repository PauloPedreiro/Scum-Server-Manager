# 🏗️ Arquitetura: SSM Plugin Framework

## 📋 Visão Técnica Detalhada

Este documento descreve a arquitetura técnica detalhada do framework de plugins SSM para SCUM.

---

## 🎯 Decisões de Arquitetura

### **Decisão 1: Abordagem Híbrida**

**Por quê:**
- Python é nossa stack principal (SSM Backend)
- C# oferece melhor performance para hooks
- Flexibilidade para escolher a melhor ferramenta

**Implementação:**
- **Core em C#** - Performance e hooks
- **Manager em Python** - Integração com SSM
- **Plugins em ambos** - Flexibilidade

### **Decisão 2: Sem DLL Injection Inicial**

**Por quê:**
- DLL injection é complexo e arriscado
- Pode causar instabilidade
- Requer conhecimento avançado

**Alternativa:**
- Trabalhar via **SCUM.db** (mais seguro)
- Monitorar **logs do servidor** (tempo real)
- Evoluir para DLL injection depois (se necessário)

---

## 🔧 Componentes Principais

### **1. SSM Plugin Core (C#)**

**Responsabilidades:**
- Carregar plugins .dll
- Gerenciar hooks de eventos
- Executar comandos no servidor
- Expor API REST

**Estrutura:**
```csharp
namespace SSM.PluginFramework.Core
{
    public class PluginCore
    {
        private List<IPlugin> plugins;
        private PluginAPI api;
        private HttpServer httpServer;
        
        public void LoadPlugin(string path);
        public void UnloadPlugin(string name);
        public void RegisterHook(string eventName, Action<object> handler);
        public void ExecuteCommand(string command);
    }
}
```

### **2. SSM Plugin Manager (Python)**

**Responsabilidades:**
- Gerenciar ciclo de vida dos plugins
- Integração com SSM Backend
- Monitoramento do SCUM.db
- Execução de comandos

**Estrutura:**
```python
class SSMPluginManager:
    def __init__(self, config, path_helper, logger):
        self.scum_db_monitor = SCUMDatabaseMonitor()
        self.plugin_loader = PluginLoader()
        self.command_executor = CommandExecutor()
        self.api_server = APIServer()
        
    def start(self):
        """Iniciar framework"""
        pass
        
    def load_plugin(self, plugin_path):
        """Carregar plugin"""
        pass
```

### **3. SCUM Database Monitor**

**Responsabilidades:**
- Monitorar mudanças no SCUM.db
- Detectar eventos (login, logout, etc.)
- Notificar plugins sobre eventos

**Estrutura:**
```python
class SCUMDatabaseMonitor:
    def __init__(self, db_path):
        self.db_path = db_path
        self.last_check = {}
        
    def monitor_loop(self):
        """Loop de monitoramento"""
        while True:
            events = self.detect_events()
            for event in events:
                self.notify_plugins(event)
            time.sleep(1)  # Verificar a cada segundo
```

### **4. Command Executor**

**Responsabilidades:**
- Executar comandos no servidor
- Via SQL (quando parado)
- Via logs (quando rodando)
- Via API (se disponível)

**Estrutura:**
```python
class CommandExecutor:
    def execute_sql_command(self, sql):
        """Executar comando SQL no SCUM.db"""
        pass
        
    def execute_server_command(self, command):
        """Executar comando do servidor"""
        pass
        
    def spawn_item(self, steam_id, item_class, quantity):
        """Spawnar item para jogador"""
        pass
```

---

## 📊 Fluxo de Dados

### **Fluxo 1: Evento do Servidor → Plugin**

```
SCUM Server
    │
    │ (evento ocorre)
    ▼
SCUM.db (modificado)
    │
    │ (monitor detecta)
    ▼
SSM Plugin Manager
    │
    │ (notifica)
    ▼
Plugin (hook executado)
    │
    │ (ação executada)
    ▼
SSM Backend (opcional)
```

### **Fluxo 2: SSM Backend → Ação no Servidor**

```
SSM Backend
    │
    │ (requisição HTTP)
    ▼
SSM Plugin Manager API
    │
    │ (processa)
    ▼
Command Executor
    │
    │ (executa)
    ▼
SCUM.db (modificado)
    │
    │ (servidor lê)
    ▼
SCUM Server (ação aplicada)
```

---

## 🔌 Sistema de Plugins

### **Interface de Plugin (C#):**

```csharp
public interface ISSMPlugin
{
    string Name { get; }
    string Version { get; }
    string Author { get; }
    
    void OnLoad(PluginAPI api);
    void OnUnload();
    
    // Hooks opcionais
    void OnPlayerConnected(PlayerInfo player);
    void OnPlayerDisconnected(PlayerInfo player);
    void OnChatMessage(PlayerInfo player, string message);
    void OnPlayerDeath(PlayerInfo player, PlayerInfo killer);
}
```

### **Interface de Plugin (Python):**

```python
class SSMPlugin:
    name: str
    version: str
    author: str
    
    def on_load(self, api):
        """Chamado quando plugin é carregado"""
        pass
        
    def on_unload(self):
        """Chamado quando plugin é descarregado"""
        pass
        
    def on_player_connected(self, player):
        """Hook quando jogador conecta"""
        pass
```

---

## 🎯 API para Plugins

### **PluginAPI (C#):**

```csharp
public class PluginAPI
{
    // Mensagens
    public void SendMessageToPlayer(string steamId, string message);
    public void BroadcastMessage(string message);
    
    // Comandos
    public void ExecuteServerCommand(string command);
    public void SpawnItem(string steamId, string itemClass, int quantity);
    
    // Skills
    public void SetPlayerSkill(string steamId, string skill, int level, float exp);
    
    // Dados
    public PlayerInfo GetPlayerInfo(string steamId);
    public List<PlayerInfo> GetOnlinePlayers();
    
    // SSM Integration
    public void CallSSMAPI(string endpoint, object data);
    public T GetSSMData<T>(string query);
}
```

### **PluginAPI (Python):**

```python
class PluginAPI:
    def send_message_to_player(self, steam_id: str, message: str):
        """Enviar mensagem para jogador"""
        pass
        
    def execute_server_command(self, command: str):
        """Executar comando do servidor"""
        pass
        
    def spawn_item(self, steam_id: str, item_class: str, quantity: int):
        """Spawnar item"""
        pass
        
    def set_player_skill(self, steam_id: str, skill: str, level: int, exp: float):
        """Definir skill do jogador"""
        pass
```

---

## 🔄 Sistema de Eventos

### **Eventos Monitorados:**

1. **Player Events:**
   - `player.connected` - Jogador conectou
   - `player.disconnected` - Jogador desconectou
   - `player.death` - Jogador morreu
   - `player.respawn` - Jogador respawnou

2. **Chat Events:**
   - `chat.message` - Mensagem no chat
   - `chat.command` - Comando executado

3. **Server Events:**
   - `server.start` - Servidor iniciou
   - `server.stop` - Servidor parou
   - `server.save` - Servidor salvou

### **Como Detectar:**

**Via SCUM.db:**
```python
# Monitorar tabela user_profile para novos logins
SELECT * FROM user_profile WHERE last_login > ?

# Monitorar tabela kill_events para mortes
SELECT * FROM kill_events WHERE timestamp > ?
```

**Via Logs:**
```python
# Monitorar arquivos de log
# Detectar padrões como:
# "Player X connected"
# "Player Y died"
```

---

## 🚀 Implementação Incremental

### **Fase 1: MVP (Via Banco)**

**Funcionalidades:**
- Monitorar SCUM.db
- Detectar eventos básicos
- Executar ações via SQL
- Sistema de plugins Python

**Limitações:**
- Requer servidor parado para modificações
- Eventos detectados com delay
- Apenas ações via SQL

### **Fase 2: Tempo Real (Via Logs)**

**Funcionalidades:**
- Monitorar logs do servidor
- Detectar eventos em tempo real
- Executar ações via banco (leitura em tempo real)
- Hot-reload de plugins

**Limitações:**
- Ainda requer servidor parado para modificações
- Eventos em tempo real (leitura)

### **Fase 3: Completo (DLL Injection)**

**Funcionalidades:**
- DLL injection no servidor
- Hooks diretos de eventos
- Execução de comandos em tempo real
- Acesso completo à API do servidor

**Vantagens:**
- Tudo em tempo real
- Sem necessidade de parar servidor
- Performance máxima

---

## 📁 Estrutura de Arquivos

```
core/
└── plugins/
    ├── __init__.py
    ├── plugin_core/              # Framework C# (futuro)
    │   └── (será adicionado)
    │
    ├── plugin_manager/           # Manager Python
    │   ├── __init__.py
    │   ├── manager.py           # Gerenciador principal
    │   ├── loader.py            # Carregador de plugins
    │   ├── api.py                # API REST
    │   └── events.py             # Sistema de eventos
    │
    ├── scum_integration/         # Integração SCUM
    │   ├── __init__.py
    │   ├── db_monitor.py         # Monitora SCUM.db
    │   ├── db_writer.py          # Escreve no SCUM.db
    │   ├── log_monitor.py        # Monitora logs
    │   └── command_executor.py   # Executa comandos
    │
    └── examples/                 # Plugins de exemplo
        ├── welcome_plugin.py
        └── kit_plugin.py
```

---

## 🔒 Segurança

### **Validação de Plugins:**
- Verificação de assinatura
- Sandbox de execução
- Permissões granulares
- Logs de auditoria

### **Isolamento:**
- Plugins rodam em contexto isolado
- Sem acesso direto ao sistema
- API limitada e controlada

---

## 📚 Próximos Passos

1. **Criar estrutura base** do projeto
2. **Implementar monitor** do SCUM.db
3. **Criar sistema** de plugins Python
4. **Desenvolver plugin** de exemplo
5. **Testar** com servidor de teste
6. **Documentar** API e uso

---

**Última atualização:** 2025-01-12  
**Status:** Arquitetura proposta - Pronto para implementação
