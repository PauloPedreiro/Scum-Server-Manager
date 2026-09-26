# 🚀 Guia de Instalação: Oxygen Framework

## 📋 Situação Atual

**Repositório:** https://github.com/Jemixs/Oxygen-scum-server-plugin  
**Status:** Projeto em desenvolvimento (WIP) - **Sem releases públicos**

### **O Que Sabemos:**
- ✅ Framework existe e está sendo desenvolvido
- ✅ Usa .NET 8.0
- ✅ Funciona via DLL injection no processo do servidor
- ✅ Tem painel web integrado
- ❌ **Não há instruções de instalação no README**
- ❌ **Não há releases/binários disponíveis**

---

## 🎯 Como Implementar (Baseado na Arquitetura)

Como não há documentação oficial, vamos inferir baseado na arquitetura típica de frameworks similares:

### **Método 1: DLL Injection (Mais Provável)**

Oxygen provavelmente funciona injetando uma DLL no processo `SCUMServer.exe`:

#### **Passo 1: Obter o Oxygen Core**

**Opções:**
1. **Discord** - Pedir build de teste
2. **Compilar do código fonte** (se disponível)
3. **Aguardar release oficial**

**Arquivos necessários:**
- `Oxygen.Core.dll` - Framework principal
- `Oxygen.csharp.API.dll` - API para plugins
- `Oxygen.Launcher.exe` ou `Oxygen.Injector.exe` - Ferramenta de injeção

#### **Passo 2: Preparar Estrutura**

```
C:\Servers\Scum\SCUM\
├── Binaries\
│   └── Win64\
│       ├── SCUMServer.exe
│       └── ...
├── Oxygen\                          # Nova pasta
│   ├── Core\
│   │   ├── Oxygen.Core.dll
│   │   └── Oxygen.csharp.API.dll
│   ├── Plugins\                    # Seus plugins aqui
│   │   └── (vazio inicialmente)
│   └── config.json                # Configuração
└── ...
```

#### **Passo 3: Configurar**

Criar `Oxygen/config.json`:
```json
{
  "plugins_path": "C:\\Servers\\Scum\\SCUM\\Oxygen\\Plugins",
  "web_port": 8080,
  "web_enabled": true,
  "api_enabled": true,
  "hot_reload": true
}
```

#### **Passo 4: Injetar DLL**

**Opção A: Launcher do Oxygen (se fornecido)**
```bash
# Se houver Oxygen.Launcher.exe
Oxygen.Launcher.exe --server "C:\Servers\Scum\SCUM\Binaries\Win64\SCUMServer.exe"
```

**Opção B: DLL Injector Manual**
1. Usar ferramenta como **Xenos Injector** ou **Extreme Injector**
2. Selecionar processo `SCUMServer.exe`
3. Injetar `Oxygen.Core.dll`
4. Oxygen inicializa automaticamente

**Opção C: Script de Inicialização**
```batch
@echo off
REM Iniciar servidor e injetar Oxygen
start "" "C:\Servers\Scum\SCUM\Binaries\Win64\SCUMServer.exe"
timeout /t 5
REM Injetar DLL (usando ferramenta de injeção)
```

---

### **Método 2: Mod/Plugin Loader Nativo**

Se o SCUM tem suporte nativo ou Oxygen modifica o executável:

#### **Passo 1: Copiar Arquivos**

```
C:\Servers\Scum\SCUM\Binaries\Win64\
├── SCUMServer.exe
├── Oxygen.dll                    # Copiar aqui
├── Oxygen.csharp.API.dll         # Copiar aqui
└── ...
```

#### **Passo 2: Modificar Configuração do Servidor**

Pode haver arquivo de configuração do SCUM que precisa ser modificado:
- `ServerSettings.ini`
- `Engine.ini`
- Arquivo de configuração específico do Oxygen

#### **Passo 3: Iniciar Servidor**

Servidor carrega Oxygen automaticamente ao iniciar.

---

## 🔍 Investigação Necessária

### **O Que Precisamos Descobrir:**

1. **Como o Oxygen é carregado?**
   - [ ] DLL injection manual?
   - [ ] Launcher próprio?
   - [ ] Mod do SCUM?
   - [ ] Wrapper do executável?

2. **Onde obter os binários?**
   - [ ] Discord (build de teste)
   - [ ] Compilar do código fonte
   - [ ] Aguardar release

3. **Estrutura de arquivos:**
   - [ ] Onde colocar os arquivos?
   - [ ] Precisa de configuração?
   - [ ] Precisa de permissões especiais?

4. **Requisitos:**
   - [ ] Versão do SCUM?
   - [ ] Versão do .NET?
   - [ ] Dependências adicionais?

---

## 📝 Plano de Ação Imediato

### **1. Entrar no Discord (URGENTE)**

**Link:** discord.gg/7h2TD8mMKM

**Mensagem sugerida:**
```
Olá! Estou interessado em implementar o Oxygen no meu servidor SCUM.

Vi o repositório no GitHub (https://github.com/Jemixs/Oxygen-scum-server-plugin), 
mas não encontrei instruções de instalação.

Poderia me ajudar com:
1. Como instalar o Oxygen no servidor?
2. Onde baixar o Oxygen Core?
3. Há documentação de instalação?
4. Qual a versão do SCUM compatível?

Obrigado!
```

### **2. Explorar Repositório GitHub**

```bash
# Clonar repositório
git clone https://github.com/Jemixs/Oxygen-scum-server-plugin.git
cd Oxygen-scum-server-plugin

# Verificar estrutura
ls -la

# Verificar branches
git branch -a

# Verificar se há código fonte
find . -name "*.cs" -o -name "*.csproj" -o -name "*.sln"

# Verificar se há binários
find . -name "*.dll" -o -name "*.exe"
```

### **3. Verificar Issues e Pull Requests**

No GitHub, verificar:
- **Issues** - Pode ter perguntas sobre instalação
- **Pull Requests** - Pode ter código de instalação
- **Wiki** - Pode ter documentação
- **Releases** - Mesmo que vazios, verificar descrição

### **4. Preparar Ambiente**

Enquanto aguarda resposta:

1. **Instalar .NET 8.0 SDK:**
   ```bash
   # Download: https://dotnet.microsoft.com/download/dotnet/8.0
   ```

2. **Instalar Visual Studio 2022:**
   - Community Edition (grátis)
   - Ou VS Code + extensão C#

3. **Preparar servidor de teste:**
   - Servidor SCUM dedicado
   - Acesso administrativo
   - Backup dos arquivos

---

## 🛠️ Implementação Teórica (Aguardando Confirmação)

### **Cenário 1: DLL Injection Manual**

```batch
@echo off
REM Script de inicialização com Oxygen

REM 1. Iniciar servidor SCUM
start "" "C:\Servers\Scum\SCUM\Binaries\Win64\SCUMServer.exe"

REM 2. Aguardar servidor iniciar
timeout /t 10

REM 3. Injetar Oxygen (usando ferramenta de injeção)
REM Exemplo com Xenos Injector (CLI):
xenos-injector.exe -p SCUMServer.exe -d "C:\Servers\Scum\SCUM\Oxygen\Core\Oxygen.Core.dll"

echo Oxygen injetado com sucesso!
```

### **Cenário 2: Launcher do Oxygen**

```batch
@echo off
REM Se houver Oxygen.Launcher.exe

Oxygen.Launcher.exe ^
  --server "C:\Servers\Scum\SCUM\Binaries\Win64\SCUMServer.exe" ^
  --config "C:\Servers\Scum\SCUM\Oxygen\config.json" ^
  --plugins "C:\Servers\Scum\SCUM\Oxygen\Plugins"
```

### **Cenário 3: Mod do SCUM**

1. Copiar arquivos para pasta do servidor
2. Modificar configuração do SCUM
3. Iniciar servidor normalmente
4. Oxygen carrega automaticamente

---

## ⚠️ Importante

### **Limitações Atuais:**
- ⚠️ **Projeto em desenvolvimento** - Pode não estar estável
- ⚠️ **Sem releases** - Pode precisar compilar do código fonte
- ⚠️ **Sem documentação** - Precisa de suporte da comunidade
- ⚠️ **Pode quebrar** - Updates do SCUM podem quebrar compatibilidade

### **Recomendações:**
- ✅ **Usar servidor de teste primeiro**
- ✅ **Fazer backup completo antes de instalar**
- ✅ **Entrar no Discord para suporte**
- ✅ **Aguardar release estável** (se possível)

---

## 📚 Recursos

- **GitHub:** https://github.com/Jemixs/Oxygen-scum-server-plugin
- **Discord:** discord.gg/7h2TD8mMKM
- **Reddit:** https://www.reddit.com/r/SCUMgame/comments/1ptgavf/wip_oxygen_first_server_plugin/

---

## 🎯 Conclusão

**Oxygen está em desenvolvimento ativo**, mas **não há instruções públicas de instalação ainda**.

**Baseado no Oxide do Rust** (framework similar), a instalação provavelmente é:

1. **Copiar arquivos do Oxygen** para pasta do servidor
2. **Criar estrutura de pastas** (Plugins/, Config/)
3. **Iniciar servidor** - Oxygen carrega automaticamente
4. **OU usar DLL injection** (se necessário)

**Ação imediata:**
1. **Discord é a melhor fonte de informação** agora
2. **Explorar repositório** para encontrar código fonte
3. **Preparar ambiente** enquanto aguarda resposta
4. **Usar Oxide do Rust como referência** (arquitetura similar)

---

**Última atualização:** 2025-01-12  
**Status:** Aguardando informações do desenvolvedor via Discord
