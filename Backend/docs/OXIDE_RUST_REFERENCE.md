# 🎮 Referência: Como o Oxide Funciona no Rust

## 📋 Visão Geral

O **Oxide** é o framework de modding oficial do Rust. Entender como ele funciona ajuda a entender como o **Oxygen** provavelmente funciona no SCUM.

---

## 🔧 Instalação do Oxide no Rust

### **Passo 1: Download**

1. Acessar: https://umod.org/
2. Selecionar versão do Rust
3. Baixar `Oxide.Rust.zip`

### **Passo 2: Instalação**

```
Rust Server/
├── RustDedicated.exe
├── oxide/                    # Pasta criada pelo Oxide
│   ├── Oxide.Rust.dll        # Framework principal
│   ├── plugins/              # Plugins aqui
│   ├── config/               # Configurações
│   ├── data/                 # Dados persistentes
│   └── lang/                 # Traduções
└── ...
```

**Processo:**
1. Extrair `Oxide.Rust.dll` na pasta do servidor
2. Iniciar servidor normalmente
3. Oxide detecta e carrega automaticamente
4. Cria estrutura de pastas automaticamente

### **Passo 3: Adicionar Plugins**

1. Baixar plugin (arquivo `.cs`)
2. Colocar em `oxide/plugins/`
3. Reiniciar servidor OU usar `oxide.reload PluginName`
4. Plugin é compilado e carregado automaticamente

---

## 📝 Estrutura de um Plugin Oxide

### **Exemplo Completo:**

```csharp
using Oxide.Core;
using System.Collections.Generic;

namespace Oxide.Plugins
{
    [Info("MyPlugin", "Author", "1.0.0")]
    [Description("My first Oxide plugin")]
    public class MyPlugin : RustPlugin
    {
        // Hook quando servidor inicia
        void OnServerInitialized()
        {
            PrintWarning("MyPlugin loaded!");
        }
        
        // Hook quando jogador conecta
        void OnPlayerConnected(BasePlayer player)
        {
            SendReply(player, "Welcome to the server!");
        }
        
        // Hook quando jogador desconecta
        void OnPlayerDisconnected(BasePlayer player, string reason)
        {
            PrintWarning($"{player.displayName} disconnected: {reason}");
        }
        
        // Comando de chat
        [ChatCommand("kit")]
        void KitCommand(BasePlayer player, string command, string[] args)
        {
            if (args.Length == 0)
            {
                SendReply(player, "Usage: /kit <name>");
                return;
            }
            
            string kitName = args[0];
            
            // Spawn items
            player.inventory.GiveItem(ItemManager.CreateByName("rifle.ak"));
            player.inventory.GiveItem(ItemManager.CreateByName("ammo.rifle"));
            
            SendReply(player, $"Kit '{kitName}' given!");
        }
        
        // Comando de console (admin)
        [ConsoleCommand("myplugin.test")]
        void TestCommand(ConsoleSystem.Arg arg)
        {
            if (arg.Connection != null)
            {
                // Chamado por jogador
                BasePlayer player = arg.Connection.player as BasePlayer;
                SendReply(player, "Test command executed!");
            }
            else
            {
                // Chamado do console do servidor
                PrintWarning("Test command executed from server console!");
            }
        }
    }
}
```

---

## 🎯 Hooks Disponíveis no Oxide

### **Hooks de Servidor:**
- `OnServerInitialized()` - Servidor totalmente iniciado
- `OnServerSave()` - Servidor salvando dados
- `OnServerShutdown()` - Servidor desligando

### **Hooks de Jogador:**
- `OnPlayerConnected()` - Jogador conectou
- `OnPlayerDisconnected()` - Jogador desconectou
- `OnPlayerRespawned()` - Jogador respawnou
- `OnPlayerDeath()` - Jogador morreu
- `OnPlayerChat()` - Jogador enviou mensagem

### **Hooks de Construção:**
- `OnEntityBuilt()` - Entidade construída
- `OnEntityDeath()` - Entidade destruída

### **Hooks de Inventário:**
- `OnItemAddedToContainer()` - Item adicionado
- `OnItemRemovedFromContainer()` - Item removido

---

## 🔄 Sistema de Permissões

```csharp
// Verificar permissão
if (!permission.UserHasPermission(player.UserIDString, "myplugin.admin"))
{
    SendReply(player, "You don't have permission!");
    return;
}

// Dar permissão via código
permission.GrantUserPermission(player.UserIDString, "myplugin.admin", null);
```

**Comandos Oxide:**
- `oxide.grant <user> <permission>` - Dar permissão
- `oxide.revoke <user> <permission>` - Remover permissão
- `oxide.group add <group> <permission>` - Adicionar ao grupo

---

## 📊 Gerenciamento de Dados

### **Salvar Dados Persistentes:**

```csharp
// Interface para dados
class PlayerData
{
    public int Kills { get; set; }
    public int Deaths { get; set; }
}

// Salvar
void SaveData()
{
    Interface.Oxide.DataFileSystem.WriteObject("MyPlugin", playerData);
}

// Carregar
void LoadData()
{
    playerData = Interface.Oxide.DataFileSystem.ReadObject<Dictionary<ulong, PlayerData>>("MyPlugin");
}
```

**Arquivo salvo em:** `oxide/data/MyPlugin.json`

---

## 🎨 Interface com Jogadores

### **Enviar Mensagens:**

```csharp
// Mensagem no chat
SendReply(player, "Hello!");

// Mensagem no console
PrintWarning("Server message");

// Mensagem para todos
rust.BroadcastChat("Server", "Announcement!");
```

### **Notificações:**

```csharp
// Notificação na tela
player.SendConsoleCommand("chat.add", 0, "Server", "Hello!");
```

---

## 🔧 Comandos do Oxide

### **Gerenciamento de Plugins:**
- `oxide.load <plugin>` - Carregar plugin
- `oxide.unload <plugin>` - Descarregar plugin
- `oxide.reload <plugin>` - Recarregar plugin (hot-reload)
- `oxide.plugins` - Listar plugins

### **Permissões:**
- `oxide.grant <user> <permission>` - Dar permissão
- `oxide.revoke <user> <permission>` - Remover permissão
- `oxide.group add <group> <permission>` - Adicionar ao grupo

### **Informações:**
- `oxide.version` - Versão do Oxide
- `oxide.plugins` - Lista de plugins

---

## 💡 Como Isso Ajuda no SCUM (Oxygen)

### **Similaridades Esperadas:**

1. **Estrutura de Pastas:**
   ```
   Oxygen/
   ├── Plugins/      # Similar a oxide/plugins/
   ├── Config/       # Similar a oxide/config/
   └── Data/         # Similar a oxide/data/
   ```

2. **Sistema de Hooks:**
   - Oxygen provavelmente tem hooks similares
   - `OnPlayerConnecting()` (já visto no README)
   - `OnPlayerConnected()` (provavelmente existe)
   - `OnPlayerDeath()` (provavelmente existe)

3. **Sistema de Comandos:**
   - `[Command]` no Oxygen = `[ChatCommand]` no Oxide
   - `ProcessCommand()` no Oxygen = execução direta de comandos

4. **Sistema de Permissões:**
   - `[Permission]` no Oxygen = sistema de permissões do Oxide

---

## 🎯 Diferenças Principais

| Aspecto | Oxide (Rust) | Oxygen (SCUM) |
|---------|-------------|---------------|
| **Plugins** | Arquivos `.cs` (source) | Arquivos `.dll` (compilados) |
| **Compilação** | Automática (runtime) | Manual (pré-compilado) |
| **Instalação** | Copiar DLL | DLL injection? |
| **Suporte** | Oficial | Independente |
| **Painel Web** | Não (plugins separados) | Sim (integrado) |

---

## 🚀 Aplicação Prática

### **Para o SCUM (Oxygen), esperamos:**

1. **Estrutura similar:**
   ```
   SCUM Server/
   ├── SCUMServer.exe
   ├── Oxygen/
   │   ├── Plugins/
   │   ├── Config/
   │   └── Data/
   └── ...
   ```

2. **API similar:**
   - Hooks de eventos
   - Sistema de comandos
   - Sistema de permissões
   - Acesso a dados do servidor

3. **Instalação:**
   - Pode ser mais simples (copiar arquivos)
   - OU pode precisar DLL injection
   - Discord vai esclarecer

---

## 📚 Recursos

- **Oxide Rust:** https://umod.org/
- **Documentação Oxide:** https://docs.oxidemod.org/
- **Carbon Rust:** https://wiki.facepunch.com/rust/Carbon
- **Oxygen SCUM:** https://github.com/Jemixs/Oxygen-scum-server-plugin

---

**Última atualização:** 2025-01-12  
**Nota:** Este documento serve como referência baseada no Oxide do Rust, que é o framework mais similar ao Oxygen proposto para SCUM.
