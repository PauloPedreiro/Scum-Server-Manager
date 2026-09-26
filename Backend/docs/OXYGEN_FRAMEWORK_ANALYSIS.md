# 🔌 Análise: Framework Oxygen para SCUM

## 📋 Visão Geral

O **Oxygen** é um framework de plugins para servidores SCUM que permite criar extensões em **C#** que se comunicam **diretamente com o servidor do jogo**, sem necessidade de bots externos (como Prisoner Bot ou Whalley Bot).

---

## 🎯 Diferença Fundamental

### **Bots Externos (Prisoner Bot, Whalley Bot)**
```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Bot       │─────▶│  Servidor    │─────▶│   Jogo      │
│  (Cliente)  │      │    SCUM      │      │             │
└─────────────┘      └──────────────┘      └─────────────┘
     │                       │
     └───────────────────────┘
   Conecta como jogador
   (requer conta Steam)
```

**Limitações:**
- Precisa de conta Steam
- Conecta como jogador (ocupa slot)
- Limitado a comandos de chat
- Pode ser detectado como bot

### **Oxygen Framework (Plugin no Servidor)**
```
┌─────────────┐
│   Plugin    │
│  (C# DLL)   │
└─────────────┘
     │
     ▼
┌──────────────┐      ┌─────────────┐
│  Servidor    │─────▶│   Jogo      │
│    SCUM      │      │             │
│  (Oxygen)    │      │             │
└──────────────┘      └─────────────┘
```

**Vantagens:**
- ✅ **Não precisa de conta Steam**
- ✅ **Não ocupa slot de jogador**
- ✅ **Acesso direto à API do servidor**
- ✅ **Hooks de eventos nativos**
- ✅ **Comandos de console diretos**
- ✅ **Mais rápido e eficiente**

---

## 📝 Análise dos Exemplos

### **Exemplo 1: Hook de Conexão**

```csharp
using System;
using System.Collections.Generic;
using Oxygen.csharp.API;

namespace Oxygen.Plugins
{
    [Info("testPlug", "jemixs", "0.1")]
    [Description("Plugin de teste mostrando a nova arquitetura")]
    public class MyFirstPlugin : OxygenPlugin 
    {
        // Este hook ativa quando o jogador termina de conectar
        public override void OnPlayerConnecting(PlayerBase player)
        {
            ReplyPlayer(player, $"Bem-vindo jogador {playerId.nickname}!");
        }
    }
}
```

**O que faz:**
- `[Info(...)]` - Metadados do plugin (nome, autor, versão)
- `[Description(...)]` - Descrição do plugin
- `OxygenPlugin` - Classe base que todos os plugins herdam
- `OnPlayerConnecting()` - **Hook** que é chamado automaticamente quando um jogador conecta
- `ReplyPlayer()` - Envia mensagem diretamente para o jogador
- `playerId.nickname` - Acessa propriedades do jogador

**Hooks disponíveis (provavelmente):**
- `OnPlayerConnecting()` - Jogador conectando
- `OnPlayerConnected()` - Jogador conectado
- `OnPlayerDisconnected()` - Jogador desconectou
- `OnPlayerDeath()` - Jogador morreu
- `OnPlayerKill()` - Jogador matou alguém
- etc.

---

### **Exemplo 2: Comandos de Chat e Spawn de Itens**

```csharp
using System;
using System.Collections.Generic;
using Oxygen.csharp.API;

namespace Oxygen.Plugins
{
    [Info("testPlug", "jemixs", "0.1")]
    [Description("Plugin de teste mostrando kits e comandos de chat")]
    public class MyFirstPlugin : OxygenPlugin 
    {
        [Command("kit")] // prefixo /kit ou !kit
        [Permission("*")] // todos os jogadores podem usar esse comando
        private void HelpCommand(PlayerBase player, string[] args){
            ReplyPlayer(player, "sem comandos");

            ProcessCommand(player, "SpawnItem Weapon_M9");
        }
    }
}
```

**O que faz:**
- `[Command("kit")]` - Registra comando `/kit` ou `!kit` no chat
- `[Permission("*")]` - Define permissão (todos podem usar)
- `HelpCommand()` - Método chamado quando jogador digita `/kit`
- `args` - Argumentos passados após o comando
- `ProcessCommand()` - **Executa comando de console do servidor**
- `"SpawnItem Weapon_M9"` - Comando nativo do SCUM para spawnar item

**Comandos de Console do SCUM (exemplos):**
- `SpawnItem <ItemClass>` - Spawna item
- `GiveItem <PlayerID> <ItemClass> <Quantity>` - Dá item para jogador
- `TeleportPlayer <PlayerID> <X> <Y> <Z>` - Teleporta jogador
- `SetPlayerSkill <PlayerID> <SkillName> <Level> <Experience>` - Define skill
- `KickPlayer <PlayerID> <Reason>` - Expulsa jogador
- etc.

---

## 🔧 Como Funciona Internamente

### **Arquitetura:**

```
┌─────────────────────────────────────────┐
│  Servidor SCUM                          │
│  ┌───────────────────────────────────┐ │
│  │  Oxygen Framework (C# Runtime)    │ │
│  │  ┌─────────────────────────────┐   │ │
│  │  │  Plugin 1 (MyFirstPlugin)   │   │ │
│  │  │  - Hooks                    │   │ │
│  │  │  - Commands                 │   │ │
│  │  └─────────────────────────────┘   │ │
│  │  ┌─────────────────────────────┐   │ │
│  │  │  Plugin 2 (Outro Plugin)    │   │ │
│  │  └─────────────────────────────┘   │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### **Fluxo de Execução:**

1. **Servidor inicia** → Carrega Oxygen Framework
2. **Oxygen carrega plugins** → DLLs na pasta de plugins
3. **Eventos do jogo ocorrem** → Oxygen chama hooks dos plugins
4. **Jogador digita comando** → Oxygen roteia para método `[Command]`
5. **Plugin executa ação** → Usa `ProcessCommand()` ou API direta

---

## 💡 Possibilidades para o SSM

### **1. Atualização de Skills em Tempo Real**

```csharp
[Command("setskill")]
[Permission("admin")]
private void SetSkillCommand(PlayerBase player, string[] args)
{
    if (args.Length < 3)
    {
        ReplyPlayer(player, "Uso: /setskill <skill> <level> <exp>");
        return;
    }
    
    string skillName = args[0];
    int level = int.Parse(args[1]);
    int experience = int.Parse(args[2]);
    
    // Executa comando de console do SCUM
    ProcessCommand(player, $"SetPlayerSkill {player.Id} {skillName} {level} {experience}");
    
    ReplyPlayer(player, $"Skill {skillName} atualizada para nível {level}!");
}
```

**Vantagem:** Funciona **com servidor rodando**, sem precisar parar!

### **2. Sincronização Automática**

```csharp
public override void OnPlayerConnected(PlayerBase player)
{
    // Quando jogador conecta, verificar se precisa atualizar skills
    // Buscar dados do SSM.db via API HTTP
    var skills = GetPlayerSkillsFromSSM(player.SteamId);
    
    foreach (var skill in skills)
    {
        ProcessCommand(player, 
            $"SetPlayerSkill {player.Id} {skill.Name} {skill.Level} {skill.Experience}");
    }
}
```

### **3. Comandos Administrativos**

```csharp
[Command("ssm-giveitem")]
[Permission("admin")]
private void GiveItemCommand(PlayerBase player, string[] args)
{
    // Integração com SSM para dar itens
    // Pode buscar do banco, verificar permissões, etc.
}
```

---

## 🚀 Como Implementar no SSM

### **Opção 1: Plugin Oxygen Simples**

Criar um plugin C# que:
- Expõe API REST local (localhost:porta)
- SSM Backend faz requisições HTTP para o plugin
- Plugin executa comandos no servidor

```
SSM Backend (Python) ──HTTP──▶ Oxygen Plugin (C#) ──API──▶ SCUM Server
```

### **Opção 2: Integração Direta**

Se Oxygen permitir acesso direto ao banco:
- Plugin lê/escreve no SCUM.db diretamente
- SSM sincroniza via banco (como já faz)

### **Opção 3: Webhook/Event System**

- SSM envia eventos via webhook
- Plugin Oxygen recebe e processa
- Executa ações no servidor

---

## 📚 Recursos Necessários

Para usar Oxygen, você precisaria:

1. **Framework Oxygen instalado no servidor SCUM**
   - DLLs do Oxygen
   - Configuração no servidor

2. **Ambiente de Desenvolvimento C#**
   - Visual Studio ou VS Code
   - .NET SDK
   - Referências do Oxygen API

3. **Conhecimento de C#**
   - Classes, métodos, atributos
   - Async/await (provavelmente)
   - LINQ (provavelmente)

---

## ⚠️ Considerações Importantes

### **Vantagens:**
- ✅ **Tempo real** - Funciona com servidor rodando
- ✅ **Sem bots** - Não precisa de conta Steam
- ✅ **Performance** - Mais rápido que bots
- ✅ **Acesso completo** - API nativa do servidor

### **Desvantagens:**
- ❌ **Requer C#** - Diferente da stack Python do SSM
- ❌ **Dependência externa** - Precisa do Oxygen instalado
- ❌ **Manutenção** - Mais uma tecnologia para manter
- ❌ **Compatibilidade** - Pode quebrar com updates do SCUM

---

## 🎯 Recomendação

Para o SSM, sugiro:

1. **Manter atualização via banco** (quando servidor parado)
   - Funciona sempre
   - Não depende de frameworks externos

2. **Adicionar suporte Oxygen como opcional**
   - Se o servidor tiver Oxygen instalado
   - Usar para atualizações em tempo real
   - Fallback para método via banco

3. **Criar plugin Oxygen simples**
   - API REST local
   - SSM faz requisições HTTP
   - Plugin executa comandos

---

## 📖 Referências

- Reddit: https://www.reddit.com/r/SCUMgame/comments/1ptgavf/wip_oxygen_first_server_plugin/
- GitHub do Oxygen (se disponível)
- Documentação da API do SCUM

---

**Última atualização:** 2025-01-12  
**Status:** Análise inicial - Framework em desenvolvimento (WIP)
