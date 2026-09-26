# 🔌 Guia de Implementação: Oxygen Framework no SCUM

## 📋 Visão Geral

O **Oxygen** é um framework de plugins C# que permite criar extensões que rodam **dentro do servidor SCUM**, dando acesso direto à API do servidor sem precisar de bots externos.

---

## 🎯 O Que É Necessário

### **1. Framework Oxygen**
- Biblioteca C# que se integra com o servidor SCUM
- Provavelmente um **DLL** ou conjunto de DLLs
- API que expõe hooks e comandos

### **2. Servidor SCUM**
- Servidor dedicado SCUM rodando
- Acesso administrativo ao servidor
- Permissões para modificar arquivos do servidor

### **3. Ambiente de Desenvolvimento**
- **Visual Studio** ou **VS Code** com extensão C#
- **.NET SDK** (provavelmente .NET 6.0 ou superior)
- Conhecimento básico de C#

---

## 🏗️ Como Funciona a Integração

### **Arquitetura:**

```
┌─────────────────────────────────────────────┐
│  Servidor SCUM                              │
│  ┌───────────────────────────────────────┐  │
│  │  SCUMServer.exe (Processo Principal) │  │
│  │                                       │  │
│  │  ┌─────────────────────────────────┐ │  │
│  │  │  Oxygen Framework               │ │  │
│  │  │  - Carrega plugins .dll         │ │  │
│  │  │  - Gerencia hooks e eventos      │ │  │
│  │  │  - Expõe API para plugins       │ │  │
│  │  └─────────────────────────────────┘ │  │
│  │                                       │  │
│  │  ┌─────────────────────────────────┐ │  │
│  │  │  Plugins/                       │ │  │
│  │  │  ├── MyPlugin.dll               │ │  │
│  │  │  ├── AnotherPlugin.dll          │ │  │
│  │  │  └── ...                        │ │  │
│  │  └─────────────────────────────────┘ │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### **Fluxo de Carregamento:**

1. **Servidor SCUM inicia**
2. **Oxygen Framework é carregado** (provavelmente via DLL injection ou mod)
3. **Oxygen escaneia pasta de plugins**
4. **Carrega todos os .dll encontrados**
5. **Registra hooks e comandos de cada plugin**
6. **Plugins ficam ativos e respondem a eventos**

---

## 📁 Estrutura de Arquivos Esperada

### **Estrutura Típica:**

```
C:\Servers\Scum\SCUM\
├── Binaries\
│   └── Win64\
│       ├── SCUMServer.exe          # Servidor principal
│       ├── Oxygen.dll              # Framework Oxygen (se injetado)
│       └── ...
├── Saved\
│   └── SaveFiles\
│       ├── SCUM.db
│       └── ...
└── Plugins\                        # Pasta de plugins (provavelmente)
    ├── MyFirstPlugin.dll
    ├── MyFirstPlugin.deps.json
    ├── MyFirstPlugin.runtimeconfig.json
    └── ...
```

**OU**

```
C:\Servers\Scum\SCUM\
├── Binaries\
│   └── Win64\
│       ├── SCUMServer.exe
│       └── ...
├── Oxygen\                         # Framework em pasta separada
│   ├── Oxygen.dll
│   ├── Oxygen.csharp.API.dll
│   └── Plugins\
│       ├── MyFirstPlugin.dll
│       └── ...
└── ...
```

---

## 🔧 Passos de Implementação

### **Passo 1: Obter o Framework Oxygen**

O Oxygen provavelmente está disponível em:
- **GitHub** (repositório do desenvolvedor)
- **Discord** (comunidade do desenvolvedor)
- **Fórum oficial** do SCUM
- **Reddit** (r/SCUMgame)

**O que você precisa:**
- `Oxygen.dll` - Framework principal
- `Oxygen.csharp.API.dll` - API para desenvolvedores
- Documentação/README
- Exemplos de plugins

### **Passo 2: Instalar no Servidor**

#### **Opção A: Injeção de DLL (se necessário)**

Se o Oxygen precisa ser injetado no processo do servidor:

1. **Usar DLL injector** (como Extreme Injector, Xenos Injector)
2. **Injetar `Oxygen.dll` no processo `SCUMServer.exe`**
3. **Oxygen inicializa e carrega plugins**

#### **Opção B: Mod/Plugin Loader (mais provável)**

Se o SCUM tem suporte nativo ou o Oxygen é um mod:

1. **Copiar arquivos do Oxygen para pasta do servidor**
2. **Configurar arquivo de configuração** (se houver)
3. **Servidor carrega automaticamente ao iniciar**

### **Passo 3: Configurar Pasta de Plugins**

1. **Criar pasta `Plugins`** (se não existir)
2. **Configurar caminho no Oxygen** (via config ou código)
3. **Colocar plugins .dll na pasta**

### **Passo 4: Criar Primeiro Plugin**

#### **Estrutura do Projeto C#:**

```
MyFirstPlugin/
├── MyFirstPlugin.csproj
├── Program.cs (ou MyFirstPlugin.cs)
└── bin/
    └── Release/
        └── net6.0/
            ├── MyFirstPlugin.dll
            ├── MyFirstPlugin.deps.json
            └── MyFirstPlugin.runtimeconfig.json
```

#### **Arquivo .csproj:**

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
    <OutputType>Library</OutputType>
    <AssemblyName>MyFirstPlugin</AssemblyName>
  </PropertyGroup>
  
  <ItemGroup>
    <Reference Include="Oxygen.csharp.API">
      <HintPath>path/to/Oxygen.csharp.API.dll</HintPath>
    </Reference>
  </ItemGroup>
</Project>
```

#### **Código do Plugin:**

```csharp
using System;
using Oxygen.csharp.API;

namespace Oxygen.Plugins
{
    [Info("MyFirstPlugin", "SeuNome", "1.0.0")]
    [Description("Meu primeiro plugin Oxygen")]
    public class MyFirstPlugin : OxygenPlugin
    {
        // Hook quando servidor inicia
        public override void OnServerStart()
        {
            Console.WriteLine("[MyFirstPlugin] Servidor iniciado!");
        }
        
        // Hook quando jogador conecta
        public override void OnPlayerConnecting(PlayerBase player)
        {
            ReplyPlayer(player, $"Bem-vindo {player.nickname}!");
        }
        
        // Comando de chat
        [Command("hello")]
        [Permission("*")]
        private void HelloCommand(PlayerBase player, string[] args)
        {
            ReplyPlayer(player, "Olá do Oxygen!");
        }
    }
}
```

### **Passo 5: Compilar e Instalar**

1. **Compilar projeto** → Gera `MyFirstPlugin.dll`
2. **Copiar DLL para pasta de plugins do servidor**
3. **Copiar dependências** (se necessário)
4. **Reiniciar servidor SCUM**

---

## 🔍 Como Descobrir Mais Informações

### **1. Verificar o Reddit Original**

O desenvolvedor provavelmente deixou:
- Link para GitHub
- Link para Discord
- Instruções de instalação
- Documentação

### **2. Procurar no GitHub**

Buscar por:
- `Oxygen SCUM`
- `SCUM plugin framework`
- `SCUM C# API`

### **3. Verificar Comunidade SCUM**

- **Discord oficial do SCUM**
- **Fóruns de servidores**
- **Comunidades de desenvolvedores**

### **4. Analisar o Código do Exemplo**

Do Reddit, podemos ver:
- Namespace: `Oxygen.csharp.API`
- Classe base: `OxygenPlugin`
- Atributos: `[Info]`, `[Description]`, `[Command]`, `[Permission]`
- Métodos: `ReplyPlayer()`, `ProcessCommand()`
- Hooks: `OnPlayerConnecting()`

---

## 🛠️ Implementação Prática

### **Checklist de Implementação:**

- [ ] **1. Encontrar/download do Oxygen Framework**
  - [ ] GitHub do desenvolvedor
  - [ ] Discord/Comunidade
  - [ ] Documentação

- [ ] **2. Verificar requisitos**
  - [ ] Versão do .NET necessária
  - [ ] Versão do SCUM compatível
  - [ ] Dependências adicionais

- [ ] **3. Instalar no servidor**
  - [ ] Copiar DLLs do Oxygen
  - [ ] Configurar pasta de plugins
  - [ ] Testar carregamento

- [ ] **4. Criar ambiente de desenvolvimento**
  - [ ] Instalar Visual Studio/VS Code
  - [ ] Instalar .NET SDK
  - [ ] Referenciar Oxygen.csharp.API.dll

- [ ] **5. Criar plugin de teste**
  - [ ] Plugin simples (hello world)
  - [ ] Compilar e testar
  - [ ] Verificar logs do servidor

- [ ] **6. Integrar com SSM**
  - [ ] Plugin que expõe API REST
  - [ ] SSM faz requisições HTTP
  - [ ] Plugin executa comandos no servidor

---

## 📚 Recursos Necessários

### **Ferramentas:**
- **Visual Studio 2022** (Community é grátis)
  - Ou **VS Code** + extensão C#
- **.NET SDK 6.0 ou 7.0**
- **Git** (para clonar repositórios)

### **Conhecimento:**
- **C# básico** (classes, métodos, atributos)
- **Conceitos de plugins/modding**
- **Estrutura de DLLs**

### **Acesso:**
- **Servidor SCUM** com permissões administrativas
- **Acesso aos arquivos do servidor**

---

## 🎯 Próximos Passos Recomendados

1. **Contatar o desenvolvedor do Oxygen**
   - Comentar no Reddit
   - Pedir link do GitHub/Discord
   - Pedir instruções de instalação

2. **Procurar repositório no GitHub**
   - Buscar "Oxygen SCUM"
   - Verificar se é open source
   - Ler README e documentação

3. **Criar plugin de teste**
   - Plugin mínimo que funciona
   - Verificar se consegue executar comandos
   - Testar hooks básicos

4. **Integrar com SSM**
   - Plugin que expõe API REST
   - SSM faz requisições
   - Executa comandos no servidor

---

## ⚠️ Considerações Importantes

### **Limitações:**
- ⚠️ **Framework em desenvolvimento** (WIP - Work In Progress)
- ⚠️ **Pode não estar público ainda**
- ⚠️ **Pode quebrar com updates do SCUM**
- ⚠️ **Requer conhecimento de C#**

### **Riscos:**
- ⚠️ **Pode causar instabilidade no servidor**
- ⚠️ **Pode ser detectado como cheat (improvável, mas possível)**
- ⚠️ **Pode não ser oficialmente suportado**

### **Vantagens:**
- ✅ **Acesso direto ao servidor**
- ✅ **Sem necessidade de bots**
- ✅ **Performance superior**
- ✅ **Funciona em tempo real**

---

## 🔗 Links e Referências

- **Reddit Original:** https://www.reddit.com/r/SCUMgame/comments/1ptgavf/wip_oxygen_first_server_plugin/
- **GitHub do Oxygen:** (procurar no Reddit/comentários)
- **Discord do desenvolvedor:** (procurar no Reddit/comentários)
- **Documentação SCUM:** (se houver)

---

## 💡 Sugestão de Ação Imediata

1. **Comentar no Reddit** pedindo:
   - Link do GitHub
   - Link do Discord
   - Instruções de instalação
   - Documentação

2. **Procurar no GitHub** por:
   - `Oxygen SCUM`
   - `SCUM plugin framework C#`
   - Nome do desenvolvedor (`jemixs`)

3. **Preparar ambiente:**
   - Instalar Visual Studio
   - Instalar .NET SDK
   - Preparar servidor de teste

---

**Última atualização:** 2025-01-12  
**Status:** Guia inicial - Aguardando informações do desenvolvedor
