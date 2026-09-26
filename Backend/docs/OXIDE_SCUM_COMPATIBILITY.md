# ❌ Compatibilidade: Oxide no SCUM

## 📋 Resposta Direta

**❌ NÃO, o Oxide NÃO pode ser usado no SCUM.**

---

## 🔍 Por Que Não Funciona?

### **1. Oxide é Específico por Jogo**

O Oxide é um framework que precisa ser **adaptado para cada jogo específico**. Existem versões separadas:

- ✅ **Oxide.Rust** - Para Rust
- ✅ **Oxide.7DaysToDie** - Para 7 Days to Die
- ✅ **Oxide.ARK** - Para ARK: Survival Evolved
- ✅ **Oxide.ConanExiles** - Para Conan Exiles
- ❌ **Oxide.SCUM** - **NÃO EXISTE**

### **2. SCUM Não Tem Suporte Oficial para Mods**

**Status do SCUM:**
- ❌ **Sem suporte oficial para mods**
- ❌ **Sem Steam Workshop**
- ❌ **Sem API de modding pública**
- ⚠️ **Desenvolvedores focados em conteúdo oficial primeiro**

**Fonte:** https://hosthavoc.com/en-GB/blog/does-scum-support-mods

### **3. Oxide Requer Suporte do Jogo**

Para o Oxide funcionar, o jogo precisa:
- ✅ **API de modding** (hooks, eventos)
- ✅ **Sistema de carregamento de plugins**
- ✅ **Acesso a dados internos do servidor**
- ❌ **SCUM não oferece isso oficialmente**

---

## 🎯 Por Que o Oxygen Foi Criado?

### **Problema:**
- SCUM não tem suporte oficial para mods
- SCUM não tem protocolo RCON adequado
- Admins precisam usar bots externos (lentos, instáveis)

### **Solução: Oxygen**
O desenvolvedor (`jemixs`) está criando o **Oxygen especificamente para SCUM** porque:

1. **Oxide não existe para SCUM**
2. **SCUM precisa de uma solução própria**
3. **Oxygen preenche essa lacuna**

---

## 🔄 Comparação: Oxide vs Oxygen

### **Oxide (Rust):**
```
✅ Suporte oficial do jogo
✅ Framework maduro e estável
✅ Milhares de plugins disponíveis
✅ Documentação completa
✅ Comunidade ativa
```

### **Oxygen (SCUM):**
```
⚠️ Desenvolvimento independente
⚠️ Projeto em desenvolvimento (WIP)
⚠️ Sem releases públicos ainda
⚠️ Documentação limitada
✅ Especificamente para SCUM
✅ Painel web integrado
✅ Hot-reload de plugins
```

---

## 💡 Alternativas para SCUM

### **Opção 1: Aguardar Oxygen (Recomendado)**
- Framework específico para SCUM
- Em desenvolvimento ativo
- Arquitetura similar ao Oxide
- Painel web integrado

### **Opção 2: Bots Externos (Atual)**
- Prisoner Bot
- Whalley Bot
- Outros bots disponíveis

**Limitações:**
- Precisam de conta Steam
- Ocupam slot de jogador
- Mais lentos
- Menos estáveis

### **Opção 3: Modificar SCUM (Não Recomendado)**
- Modificar executável do servidor
- Risco de banimento
- Quebra com updates
- Não suportado

---

## 🎯 Conclusão

### **Oxide no SCUM:**
- ❌ **Não é possível** usar Oxide diretamente
- ❌ **Não existe** versão do Oxide para SCUM
- ❌ **SCUM não tem** suporte oficial para mods

### **Oxygen no SCUM:**
- ✅ **Solução específica** para SCUM
- ✅ **Em desenvolvimento** ativo
- ✅ **Arquitetura similar** ao Oxide
- ⚠️ **Ainda não está** disponível publicamente

### **Recomendação:**
1. **Aguardar Oxygen** ser lançado
2. **Entrar no Discord** para acompanhar desenvolvimento
3. **Usar bots externos** como solução temporária
4. **Não tentar** adaptar Oxide (não funcionará)

---

## 📚 Referências

- **Oxide Official:** https://umod.org/
- **Oxide GitHub:** https://github.com/oxidemod
- **Oxygen SCUM:** https://github.com/Jemixs/Oxygen-scum-server-plugin
- **SCUM Modding:** https://hosthavoc.com/en-GB/blog/does-scum-support-mods

---

**Última atualização:** 2025-01-12  
**Status:** Oxide não é compatível com SCUM - Oxygen é a solução específica
