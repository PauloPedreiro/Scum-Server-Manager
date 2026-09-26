# 📋 Linhas Não Parseadas nos Logs

## 🔍 O que são?

As mensagens `[INFO] Linha não parseada: ...` aparecem quando o sistema processa arquivos de log do SCUM e encontra linhas que **não correspondem aos padrões esperados** de login/logout.

## 📝 Exemplos de Linhas Não Parseadas

### **1. Linhas de Versão do Jogo**
```
2025.12.15-05.05.01: Game version: 1.1.0.5.101995
```
**Por que não é parseada?**
- Não contém informações de login/logout
- É apenas informação de versão do jogo
- **Comportamento esperado**: Essas linhas são **ignoradas** pelo parser

### **2. Linhas de Limpeza de Jogadores**
```
2025.12.15-14.05.25: Deleting players that haven't logged in for 180 day(s)...
2025.12.15-14.05.25: Completed in 0.003s for 0 player profiles and 0 players.
```
**Por que não é parseada?**
- São mensagens de sistema do SCUM
- Não contêm dados de sessão de jogadores
- **Comportamento esperado**: Essas linhas são **ignoradas** pelo parser

## ✅ Isso é Normal?

**SIM!** É completamente normal e esperado. O sistema está funcionando corretamente.

### **Por que aparecem?**

1. **Arquivos de log do SCUM contêm múltiplos tipos de informação:**
   - Logins/logouts de jogadores (parseadas)
   - Informações de versão (ignoradas)
   - Mensagens de sistema (ignoradas)
   - Outras informações (ignoradas)

2. **O parser só processa linhas relevantes:**
   - Linhas com padrão `logged in at:` → Parseadas ✅
   - Linhas com padrão `logged out at:` → Parseadas ✅
   - Outras linhas → Ignoradas (não parseadas) ⚠️

## 🔧 Como Funciona

### **Parser de Logs (`log_parser.py`)**

```python
def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
    # Ignorar linhas vazias
    if self.empty_pattern.match(line):
        return None
    
    # Ignorar linhas de versão do jogo
    if self.version_pattern.search(line):
        return None  # ← Linha ignorada silenciosamente
    
    # Tentar fazer match com padrão de login/logout
    match = self.login_pattern.match(line)
    if match:
        return self._extract_session_data(match)
    
    # Linha não reconhecida (mas não é erro!)
    print(f"⚠️ Linha não reconhecida: {line[:100]}...")
    return None
```

### **OnlinePlayersMonitor (`online_monitor.py`)**

```python
def _rebuild_online_from_login_file(self):
    for line in lines:
        if 'logged in at:' in line:
            # Processar login
            login_data = self._parse_login_event(line)
        elif 'logged out at:' in line:
            # Processar logout
            logout_data = self._parse_logout_event(line)
        # Outras linhas são simplesmente ignoradas
```

## 📊 Tipos de Linhas nos Logs do SCUM

| Tipo de Linha | Parseada? | Motivo |
|---------------|-----------|--------|
| `logged in at:` | ✅ SIM | Contém dados de login |
| `logged out at:` | ✅ SIM | Contém dados de logout |
| `Game version:` | ❌ NÃO | Apenas informação de versão |
| `Deleting players...` | ❌ NÃO | Mensagem de sistema |
| `Completed in...` | ❌ NÃO | Mensagem de sistema |
| Linhas vazias | ❌ NÃO | Sem informação útil |

## 🎯 Conclusão

### **Status: ✅ FUNCIONANDO CORRETAMENTE**

As linhas "não parseadas" são:
- ✅ **Normais** - Fazem parte dos logs do SCUM
- ✅ **Esperadas** - O sistema está ignorando corretamente linhas irrelevantes
- ✅ **Não são erros** - Apenas informações que não precisam ser processadas

### **O que fazer?**

**NADA!** O sistema está funcionando como esperado. Essas mensagens são apenas informativas e indicam que o parser está filtrando corretamente as linhas relevantes.

### **Quer reduzir essas mensagens?**

Se você quiser reduzir o "ruído" nos logs, pode:
1. **Ignorar** - Essas mensagens são normais e não afetam o funcionamento
2. **Filtrar na GUI** - Adicionar filtro para ocultar mensagens `[INFO] Linha não parseada`
3. **Ajustar nível de log** - Configurar para mostrar apenas erros e avisos

---

**Última Atualização**: 2025-12-16

