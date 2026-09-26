# 🔍 Comparação: Oxygen (SCUM) vs Oxide/Carbon (Rust)

## 📋 Descoberta Importante

A pesquisa revelou que o **Rust usa Oxide/Carbon**, não "Oxygen". Porém, a arquitetura é muito similar ao que o desenvolvedor do Oxygen para SCUM está criando.

---

## 🎮 Rust: Oxide e Carbon

### **Oxide (Framework Tradicional do Rust)**

**Como funciona:**
- Framework de modding **oficialmente suportado** pelo Rust
- Plugins escritos em **C#**
- Carregamento automático de plugins
- Sistema de permissões integrado
- API completa para desenvolvedores

**Estrutura de Instalação:**
```
Rust Server/
├── RustDedicated.exe
├── oxide/
│   ├── plugins/          # Plugins .cs aqui
│   ├── config/           # Configurações
│   └── data/             # Dados dos plugins
└── ...
```

**Como é instalado:**
1. **Download do Oxide** (site oficial)
2. **Extrair arquivos** na pasta do servidor
3. **Iniciar servidor** - Oxide carrega automaticamente
4. **Colocar plugins** na pasta `oxide/plugins/`
5. **Plugins são compilados automaticamente** (arquivos .cs)

**Características:**
- ✅ **Suporte oficial** do jogo
- ✅ **Hot-reload** de plugins
- ✅ **Sistema de permissões**
- ✅ **API completa**
- ✅ **Plugins em C#** (arquivos .cs, não .dll)

---

### **Carbon (Framework Moderno do Rust)**

**Diferenças do Oxide:**
- Escrito em **C#** (Oxide é C++)
- **Otimizações** de performance
- **Compatível com plugins Oxide**
- Sistema de permissões modular
- **Melhor performance** (menos CPU/memória)

**Estrutura similar ao Oxide:**
```
Rust Server/
├── RustDedicated.exe
├── carbon/
│   ├── plugins/
│   ├── config/
│   └── data/
└── ...
```

---

## 🔄 Comparação: Rust vs SCUM

### **Rust (Oxide/Carbon):**
```
┌─────────────────────────────────┐
│  RustDedicated.exe              │
│  ┌───────────────────────────┐ │
│  │  Oxide/Carbon Framework    │ │
│  │  (Suportado oficialmente)  │ │
│  │  ┌─────────────────────┐  │ │
│  │  │  Plugins/           │  │ │
│  │  │  - Plugin.cs        │  │ │
│  │  │  - Outro.cs         │  │ │
│  │  └─────────────────────┘  │ │
│  └───────────────────────────┘ │
└─────────────────────────────────┘
```

**Características:**
- ✅ Suporte oficial do jogo
- ✅ Plugins são arquivos `.cs` (compilados em runtime)
- ✅ Estrutura de pastas criada automaticamente
- ✅ Sistema de permissões integrado

### **SCUM (Oxygen - Proposto):**
```
┌─────────────────────────────────┐
│  SCUMServer.exe                 │
│  ┌───────────────────────────┐ │
│  │  Oxygen Framework          │ │
│  │  (DLL Injection)           │ │
│  │  ┌─────────────────────┐  │ │
│  │  │  Plugins/           │  │ │
│  │  │  - Plugin.dll        │  │ │
│  │  │  - Outro.dll         │  │ │
│  │  └─────────────────────┘  │ │
│  └───────────────────────────┘ │
└─────────────────────────────────┘
```

**Características:**
- ⚠️ Não suportado oficialmente (ainda)
- ⚠️ Plugins são `.dll` (precisam ser compilados)
- ⚠️ Requer DLL injection manual
- ✅ Hot-reload mencionado

---

## 💡 Lições do Rust para SCUM

### **1. Estrutura de Pastas**

O Oxide cria automaticamente:
```
oxide/
├── plugins/      # Plugins aqui
├── config/       # Configurações
├── data/         # Dados persistentes
└── lang/         # Traduções
```

**Oxygen provavelmente precisa:**
```
Oxygen/
├── Plugins/      # Plugins .dll
├── Config/       # Configurações
└── Data/         # Dados (se necessário)
```

### **2. Sistema de Carregamento**

**Oxide:**
- Carrega plugins `.cs` automaticamente
- Compila em runtime
- Hot-reload nativo

**Oxygen (inferido):**
- Carrega plugins `.dll` automaticamente
- Plugins pré-compilados
- Hot-reload mencionado no README

### **3. API e Hooks**

**Oxide tem hooks como:**
- `OnServerInitialized()`
- `OnPlayerConnected()`
- `OnPlayerDisconnected()`
- `OnChatCommand()`

**Oxygen (do README) tem:**
- `OnPlayerConnecting()`
- `OnPlayerConnected()` (provavelmente)
- `[Command]` para comandos de chat
- `ProcessCommand()` para executar comandos do servidor

---

## 🎯 Como o Oxide Funciona no Rust (Detalhes Técnicos)

### **Instalação do Oxide:**

1. **Download:**
   - Site oficial: https://umod.org/
   - Versão específica para cada versão do Rust
   - Arquivo: `Oxide.Rust.zip`

2. **Extração:**
   ```
   Rust Server/
   ├── RustDedicated.exe
   ├── oxide/
   │   ├── Oxide.Rust.dll      # Framework principal
   │   ├── plugins/            # Pasta de plugins
   │   └── ...
   └── ...
   ```

3. **Inicialização:**
   - Servidor inicia normalmente
   - Oxide detecta e carrega automaticamente
   - Cria estrutura de pastas se não existir
   - Carrega plugins da pasta `oxide/plugins/`

4. **Plugins:**
   - Arquivos `.cs` (C# source code)
   - Oxide compila automaticamente
   - Não precisa compilar manualmente
   - Hot-reload: `oxide.reload PluginName`

### **Exemplo de Plugin Oxide (Rust):**

```csharp
using Oxide.Core;

namespace Oxide.Plugins
{
    [Info("MyPlugin", "Author", "1.0.0")]
    [Description("My first Oxide plugin")]
    public class MyPlugin : RustPlugin
    {
        void OnServerInitialized()
        {
            PrintWarning("MyPlugin loaded!");
        }
        
        void OnPlayerConnected(BasePlayer player)
        {
            SendReply(player, "Welcome!");
        }
        
        [ChatCommand("kit")]
        void KitCommand(BasePlayer player, string command, string[] args)
        {
            // Spawn item
            player.inventory.GiveItem(ItemManager.CreateByName("rifle.ak"));
        }
    }
}
```

**Similaridades com Oxygen:**
- ✅ Mesma estrutura de atributos `[Info]`
- ✅ Herda de classe base (`RustPlugin` vs `OxygenPlugin`)
- ✅ Hooks similares
- ✅ Comandos de chat com `[ChatCommand]`

---

## 🔧 Como Isso Ajuda no SCUM

### **Inferências para Oxygen:**

1. **Estrutura de Pastas:**
   - Oxygen provavelmente cria estrutura similar
   - Pasta `Plugins/` para plugins
   - Pasta `Config/` para configurações

2. **Carregamento:**
   - Oxygen provavelmente escaneia pasta de plugins
   - Carrega `.dll` automaticamente
   - Registra hooks e comandos

3. **API:**
   - Similar ao Oxide
   - Hooks de eventos
   - Sistema de comandos
   - Acesso a dados do servidor

4. **Instalação:**
   - Pode ser similar ao Oxide
   - Copiar arquivos para pasta do servidor
   - Iniciar servidor normalmente
   - Ou requer DLL injection (diferente do Oxide)

---

## 📝 Diferenças Principais

| Aspecto | Oxide (Rust) | Oxygen (SCUM) |
|---------|-------------|---------------|
| **Suporte** | Oficial | Não oficial (WIP) |
| **Instalação** | Copiar arquivos | DLL injection? |
| **Plugins** | Arquivos `.cs` | Arquivos `.dll` |
| **Compilação** | Runtime (automática) | Pré-compilado |
| **Hot-reload** | Nativo | Mencionado |
| **Painel Web** | Não (plugins separados) | Sim (integrado) |

---

## 🎯 Conclusão

O **Oxide do Rust** é um excelente modelo para entender como o **Oxygen do SCUM** provavelmente funciona:

1. **Estrutura similar** - Pastas de plugins, config, etc.
2. **API similar** - Hooks, comandos, permissões
3. **Filosofia similar** - Plugins C#, hot-reload, etc.

**Diferença principal:**
- Oxide é **suportado oficialmente** pelo Rust
- Oxygen é **desenvolvimento independente** para SCUM
- Oxygen pode precisar de **DLL injection** (Oxide não precisa)

**Próximos passos:**
- Entrar no Discord do Oxygen
- Perguntar sobre instalação (pode ser similar ao Oxide)
- Verificar se há estrutura de pastas automática
- Confirmar se precisa de DLL injection ou é mais simples

---

**Última atualização:** 2025-01-12  
**Referências:**
- Oxide Rust: https://umod.org/
- Carbon Rust: https://wiki.facepunch.com/rust/Carbon
- Oxygen SCUM: https://github.com/Jemixs/Oxygen-scum-server-plugin
