# 🔍 Análise do Repositório Oxygen

## 📋 Informações do Repositório

**GitHub:** https://github.com/Jemixs/Oxygen-scum-server-plugin  
**Discord:** discord.gg/7h2TD8mMKM

### **Status Atual:**
- ✅ Repositório existe e está ativo
- ⚠️ **Sem releases publicados** (0 releases)
- ⚠️ **Sem instruções de instalação no README**
- ⚠️ **Projeto em desenvolvimento (WIP)**
- ✅ Discord disponível para suporte
- ✅ Exemplos de código no README
- ✅ Painel Web integrado mencionado

---

## 🎯 O Que Sabemos

### **Características (Confirmadas):**
- **Framework C#** para plugins no servidor SCUM
- **.NET 8.0** necessário (confirmado no README)
- **Hot-reload** de scripts (sem reiniciar servidor)
- **Painel Web** integrado com múltiplas abas:
  - Servers Tab (controle do servidor)
  - Players Tab (monitoramento de jogadores)
  - Squads Tab (gerenciamento de squads)
  - Chat Tab (leitura/envio de mensagens)
  - Plugins Tab (gerenciamento de extensões)
  - Downloads Tab (atualizações)
- **API completa** para desenvolvedores
- **Funciona diretamente no processo do servidor** (DLL injection)

### **Funcionalidades:**
- ✅ Comandos customizados (`/kit`, etc.)
- ✅ Hooks de eventos (`OnPlayerLogin`, `OnDeath`, `OnChat`)
- ✅ Gerenciamento de jogadores via web
- ✅ Monitoramento em tempo real
- ✅ Spawn de itens
- ✅ Gerenciamento de squads

---

## 🔧 Como Funciona a Integração

### **Arquitetura (Baseado no README):**

```
┌─────────────────────────────────────────┐
│  Servidor SCUM (SCUMServer.exe)        │
│  ┌───────────────────────────────────┐ │
│  │  Oxygen Core (DLL injetado)      │ │
│  │  - Carrega plugins C#             │ │
│  │  - Gerencia hooks                 │ │
│  │  - Expõe API                      │ │
│  └───────────────────────────────────┘ │
│  ┌───────────────────────────────────┐ │
│  │  Plugins/                         │ │
│  │  - MyPlugin.dll                   │ │
│  │  - OutroPlugin.dll                │ │
│  └───────────────────────────────────┘ │
│  ┌───────────────────────────────────┐ │
│  │  Web Panel (HTTP Server)          │ │
│  │  - Interface web                  │ │
│  │  - API REST                       │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### **Como o Oxygen é Carregado:**

Oxygen provavelmente usa uma das seguintes técnicas:

#### **Opção 1: DLL Injection**
- DLL é injetada no processo `SCUMServer.exe`
- Hooka funções do servidor
- Intercepta eventos e comandos

#### **Opção 2: Mod/Plugin Loader**
- SCUM tem suporte nativo (improvável)
- Ou Oxygen modifica o executável (mais provável)

#### **Opção 3: Wrapper/Launcher**
- Oxygen cria um launcher que inicia o servidor
- Injeta código durante inicialização

---

## 📝 O Que Fazer Agora

### **1. Entrar no Discord (PRIORIDADE ALTA)**

**Discord:** discord.gg/7h2TD8mMKM

**Perguntas para fazer:**
- Como instalar o Oxygen no servidor?
- Onde baixar o Oxygen Core? (não há releases no GitHub)
- Há documentação de instalação?
- Qual a versão do SCUM compatível?
- Precisa de permissões especiais?
- Como funciona a DLL injection?
- Há build de teste disponível?
- Quando será o primeiro release?

### **2. Explorar o Repositório GitHub**

**Clonar e explorar:**
```bash
git clone https://github.com/Jemixs/Oxygen-scum-server-plugin.git
cd Oxygen-scum-server-plugin
```

**Verificar estrutura:**
- Pasta `src/` ou `source/` (código fonte do Oxygen Core)
- Pasta `examples/` ou `plugins/` (exemplos de plugins)
- Pasta `Oxygen.Core/` (framework principal)
- Pasta `Oxygen.API/` (API para desenvolvedores)
- Arquivo `INSTALL.md` ou `SETUP.md` (instruções)
- Arquivo `BUILD.md` (como compilar)
- Pasta `releases/` ou `bin/` (binários pré-compilados)
- Arquivo `.github/workflows/` (CI/CD que pode revelar processo de build)

### **3. Analisar Estrutura do Repositório**

Verificar se há:
- `Oxygen.Core.dll` (binário)
- `Oxygen.csharp.API.dll` (API)
- `installer.exe` ou script de instalação
- Arquivos de configuração

---

## 🛠️ Implementação Prática

### **Passo 1: Obter o Oxygen Core**

Como não há releases, você precisa:

1. **Entrar no Discord**
   - Pedir acesso ao build/teste
   - Verificar se há link de download
   - Perguntar sobre versão beta/alpha

2. **Verificar se há código fonte**
   - Clonar repositório
   - Compilar você mesmo (se possível)
   - Verificar dependências

3. **Aguardar release oficial**
   - Projeto está em desenvolvimento
   - Pode não estar pronto para produção

### **Passo 2: Instalação (Quando Tiver o Core)**

Baseado na arquitetura típica de plugins:

1. **Copiar arquivos do Oxygen:**
   ```
   C:\Servers\Scum\SCUM\Binaries\Win64\
   ├── SCUMServer.exe
   ├── Oxygen.Core.dll        # Framework principal
   ├── Oxygen.csharp.API.dll  # API para plugins
   └── ...
   ```

2. **Criar pasta de plugins:**
   ```
   C:\Servers\Scum\SCUM\Plugins\
   └── (seus plugins .dll aqui)
   ```

3. **Injetar DLL no servidor:**
   - Usar DLL injector
   - Ou usar launcher do Oxygen
   - Ou método específico do desenvolvedor

### **Passo 3: Configuração**

Provavelmente precisa de arquivo de configuração:
```json
{
  "plugins_path": "C:\\Servers\\Scum\\SCUM\\Plugins",
  "web_port": 8080,
  "api_enabled": true
}
```

---

## 🔍 Investigação Necessária

### **O Que Precisamos Descobrir:**

1. **Como o Oxygen é carregado?**
   - DLL injection?
   - Launcher?
   - Mod do SCUM?

2. **Onde baixar o Oxygen Core?**
   - Discord?
   - Build do código fonte?
   - Release futuro?

3. **Requisitos técnicos:**
   - Versão do SCUM?
   - Versão do .NET?
   - Permissões necessárias?

4. **Estrutura de arquivos:**
   - Onde colocar os arquivos?
   - Como configurar?
   - Como iniciar?

---

## 💡 Plano de Ação

### **Ação Imediata:**

1. **Entrar no Discord:** discord.gg/7h2TD8mMKM
   - Apresentar-se
   - Pedir instruções de instalação
   - Perguntar sobre status do projeto

2. **Clonar/Explorar Repositório:**
   ```bash
   git clone https://github.com/Jemixs/Oxygen-scum-server-plugin.git
   cd Oxygen-scum-server-plugin
   # Explorar estrutura
   ```

3. **Verificar Branches:**
   - Pode haver branch `dev` ou `install` com mais informações
   - Verificar issues/pull requests

4. **Preparar Ambiente:**
   - Instalar .NET 8.0 SDK
   - Instalar Visual Studio
   - Preparar servidor de teste

---

## 📚 Recursos do Projeto

### **Disponíveis:**
- ✅ Repositório GitHub
- ✅ Discord (comunidade)
- ✅ Exemplos de código no README
- ✅ API documentada (parcialmente)

### **Faltando:**
- ❌ Releases/Binários
- ❌ Instruções de instalação
- ❌ Documentação completa
- ❌ Guia de setup

---

## 🎯 Conclusão

O projeto **Oxygen está em desenvolvimento ativo**, mas ainda **não tem releases públicos** ou **instruções de instalação completas**.

**Próximos passos:**
1. **Discord é a melhor fonte de informação** agora
2. **Comunidade pode ter builds de teste**
3. **Desenvolvedor pode estar aceitando testers**

**Recomendação:**
- Entrar no Discord
- Perguntar sobre instalação
- Oferecer-se como tester (se possível)
- Aguardar release oficial ou obter build de teste

---

**Última atualização:** 2025-01-12  
**Repositório:** https://github.com/Jemixs/Oxygen-scum-server-plugin  
**Discord:** discord.gg/7h2TD8mMKM
