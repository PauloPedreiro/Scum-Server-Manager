# 🔧 Métodos de Parada do Servidor SCUM

## 📋 Resumo

Este documento lista **todos os métodos possíveis** para parar o servidor SCUM no Windows, explicando quais são usados atualmente e quais são alternativas disponíveis.

## ✅ Métodos Implementados Atualmente

### 1. **NSSM Stop (Shutdown Gracioso)** ⭐ RECOMENDADO
**Localização**: `_stop_service_nssm()`

**Comando**:
```powershell
nssm.exe stop SCUMServer
```

**Como funciona**:
- NSSM envia `CTRL_C_EVENT` ao processo
- Permite shutdown gracioso (graceful shutdown)
- O servidor recebe o sinal e pode fazer limpezas antes de parar
- Aguarda até 2 minutos para o servidor completar o shutdown

**Vantagens**:
- ✅ Shutdown gracioso (permite backups e limpezas)
- ✅ Método oficial do NSSM
- ✅ Mais confiável para serviços Windows

**Desvantagens**:
- Requer NSSM instalado
- Pode demorar mais tempo

---

### 2. **PowerShell Stop-Service (Shutdown Gracioso)**
**Localização**: `_stop_service_powershell()`

**Comando**:
```powershell
Stop-Service -Name SCUMServer
```

**Como funciona**:
- Envia sinal de parada ao serviço Windows
- Permite shutdown gracioso (sem `-Force`)
- Aguarda até 3 minutos (2 minutos + 60 segundos adicionais)
- **NUNCA usa `-Force`**

**Vantagens**:
- ✅ Shutdown gracioso
- ✅ Não requer NSSM
- ✅ Método nativo do Windows

**Desvantagens**:
- Pode ser mais lento que NSSM
- Depende do gerenciador de serviços do Windows

---

## ❌ Métodos NÃO Implementados (Alternativas Disponíveis)

### 3. **PowerShell Stop-Service com -Force** ❌ NÃO USADO
**Comando**:
```powershell
Stop-Service -Name SCUMServer -Force
```

**Como funciona**:
- Força parada imediata do serviço
- **NÃO permite shutdown gracioso**
- Mata o processo sem dar tempo para limpezas

**Por que NÃO é usado**:
- ❌ Não permite backups
- ❌ Pode corromper dados
- ❌ Não permite limpeza de recursos
- ❌ Pode causar perda de dados

**Status**: **REMOVIDO COMPLETAMENTE** do código

---

### 3. **SC Stop (Service Control)** ✅ IMPLEMENTADO
**Localização**: `_stop_service_sc()`

**Comando**:
```cmd
sc stop SCUMServer
```

**Como funciona**:
- Comando nativo do Windows para controlar serviços
- Envia sinal de parada (`SERVICE_CONTROL_STOP`) ao serviço
- Permite shutdown gracioso (similar ao Stop-Service)
- Aguarda até 3 minutos (2 minutos + 60 segundos adicionais)

**Vantagens**:
- ✅ Shutdown gracioso
- ✅ Comando nativo do Windows
- ✅ Funciona via CMD ou PowerShell
- ✅ Não requer PowerShell (funciona em CMD puro)
- ✅ Fallback adicional quando NSSM e PowerShell falham

**Desvantagens**:
- Timeout padrão do SC é limitado (~30s), mas o código aguarda mais tempo
- Mensagens de erro podem ser menos detalhadas

**Status**: ✅ **IMPLEMENTADO** como fallback adicional (3º método)

---

### 5. **TaskKill (Forçar Parada de Processo)** ❌ NÃO USADO
**Comando**:
```cmd
taskkill /F /IM SCUM.exe
# ou
taskkill /F /PID <process_id>
```

**Como funciona**:
- Mata o processo diretamente
- `/F` força a parada
- **NÃO permite shutdown gracioso**
- Ignora completamente o serviço Windows

**Por que NÃO é usado**:
- ❌ Não permite shutdown gracioso
- ❌ Pode corromper dados
- ❌ Não respeita o gerenciador de serviços
- ❌ Pode causar perda de dados

**Status**: **NÃO IMPLEMENTADO** e não deve ser usado

---

### 6. **NSSM Kill** ❌ NÃO USADO
**Comando**:
```cmd
nssm.exe kill SCUMServer
```

**Como funciona**:
- NSSM mata o processo diretamente
- **NÃO permite shutdown gracioso**
- Similar ao TaskKill

**Por que NÃO é usado**:
- ❌ Não permite shutdown gracioso
- ❌ Pode corromper dados
- ❌ NSSM `stop` é preferível

**Status**: **NÃO IMPLEMENTADO** e não deve ser usado

---

### 7. **NSSM Restart** ⚠️ NÃO IMPLEMENTADO COMO MÉTODO DE PARADA
**Comando**:
```cmd
nssm.exe restart SCUMServer
```

**Como funciona**:
- Para e inicia o serviço em sequência
- Usa `stop` internamente (shutdown gracioso)
- Depois usa `start` para reiniciar

**Status**: **USADO APENAS PARA RESTART**, não para parada simples

---

### 8. **Get-Service + Stop-Process** ❌ NÃO USADO
**Comando**:
```powershell
$service = Get-Service -Name SCUMServer
Stop-Process -Id $service.ProcessId -Force
```

**Como funciona**:
- Obtém o ID do processo do serviço
- Mata o processo diretamente
- **NÃO permite shutdown gracioso**

**Por que NÃO é usado**:
- ❌ Não permite shutdown gracioso
- ❌ Similar ao TaskKill
- ❌ Pode corromper dados

**Status**: **NÃO IMPLEMENTADO** e não deve ser usado

---

## 📊 Comparação dos Métodos

| Método | Shutdown Gracioso | Velocidade | Segurança | Status |
|--------|-------------------|------------|-----------|--------|
| **NSSM Stop** | ✅ Sim | Média | ⭐⭐⭐⭐⭐ | ✅ Implementado |
| **Stop-Service** | ✅ Sim | Média | ⭐⭐⭐⭐⭐ | ✅ Implementado |
| **SC Stop** | ✅ Sim | Média | ⭐⭐⭐⭐⭐ | ✅ Implementado |
| **Stop-Service -Force** | ❌ Não | Rápida | ⭐ | ❌ Removido |
| **TaskKill** | ❌ Não | Muito Rápida | ⭐ | ❌ Não usado |
| **NSSM Kill** | ❌ Não | Muito Rápida | ⭐ | ❌ Não usado |
| **Stop-Process** | ❌ Não | Muito Rápida | ⭐ | ❌ Não usado |

## 🔄 Fluxo Atual de Parada

```
stop_server()
    │
    ├─→ [1] _stop_service_nssm()
    │       └─→ nssm.exe stop SCUMServer
    │       └─→ Aguarda até 2 minutos
    │       └─→ ✅ Sucesso OU ❌ Falha
    │
    ├─→ [2] _stop_service_powershell() (se NSSM falhar)
    │       └─→ Stop-Service -Name SCUMServer (SEM -Force)
    │       └─→ Aguarda até 3 minutos (2min + 60s)
    │       └─→ ✅ Sucesso OU ❌ Falha
    │
    └─→ [3] _stop_service_sc() (se NSSM e PowerShell falharem)
            └─→ sc stop SCUMServer
            └─→ Aguarda até 3 minutos (2min + 60s)
            └─→ ✅ Sucesso OU ❌ Erro
```

## 🎯 Recomendações

### ✅ Usar:
1. **NSSM Stop** - Método preferido (mais confiável) - 1º tentativa
2. **Stop-Service** - Fallback quando NSSM não está disponível - 2º tentativa
3. **SC Stop** - Fallback adicional quando NSSM e PowerShell falham - 3º tentativa

### ❌ NUNCA Usar:
1. **Stop-Service -Force** - Remove shutdown gracioso
2. **TaskKill** - Mata processo sem shutdown gracioso
3. **NSSM Kill** - Mata processo sem shutdown gracioso
4. **Stop-Process** - Mata processo sem shutdown gracioso

## 💡 Possíveis Melhorias Futuras

### 1. Adicionar SC Stop como Fallback
```python
def _stop_service_sc(self) -> Dict[str, Any]:
    """Método alternativo via SC (Service Control)"""
    # sc stop SCUMServer
    pass
```

### 2. Adicionar Verificação de Timeout Configurável
```python
# Permitir configurar timeout via config.json
max_wait_time = self.config.get('server', {}).get('shutdown_timeout', 120)
```

### 3. Adicionar Logs Mais Detalhados
- Mostrar qual método está sendo usado
- Mostrar tempo real de espera
- Mostrar progresso do shutdown do servidor SCUM

## 📝 Notas Importantes

1. **Shutdown Gracioso é ESSENCIAL**: Permite que o servidor SCUM:
   - Salve dados de basebuilding
   - Faça backups completos
   - Limpe recursos (gardens, farming, etc.)
   - Feche conexões de banco de dados corretamente

2. **NUNCA usar métodos forçados**: Eles podem causar:
   - Perda de dados
   - Corrupção de arquivos
   - Problemas ao reiniciar o servidor

3. **Timeout adequado**: 2-3 minutos é suficiente para a maioria dos servidores, mas servidores com muitos dados podem precisar de mais tempo.

## 🔍 Referências

- [NSSM Documentation](https://nssm.cc/usage)
- [Windows Service Control](https://docs.microsoft.com/en-us/windows/win32/services/service-control-manager)
- [PowerShell Stop-Service](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/stop-service)

