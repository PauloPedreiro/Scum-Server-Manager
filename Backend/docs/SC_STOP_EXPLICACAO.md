# 📖 Explicação Detalhada: SC Stop

## 🔍 O que é SC Stop?

`sc stop` é um comando nativo do Windows que faz parte do **Service Control Manager (SCM)**. É uma ferramenta de linha de comando para controlar serviços do Windows.

## 📋 Sintaxe Básica

```cmd
sc stop <nome_do_servico>
```

**Exemplo**:
```cmd
sc stop SCUMServer
```

## 🔧 Como Funciona

### 1. **Processo Interno**

Quando você executa `sc stop SCUMServer`:

1. **Comunicação com SCM**: O comando se comunica com o Service Control Manager do Windows
2. **Envio de Sinal**: O SCM envia um sinal de parada (`SERVICE_CONTROL_STOP`) ao serviço
3. **Shutdown Gracioso**: O serviço recebe o sinal e pode executar código de limpeza antes de parar
4. **Timeout**: O Windows aguarda um tempo padrão (geralmente 30 segundos) para o serviço parar
5. **Verificação**: Verifica se o serviço realmente parou

### 2. **Fluxo de Execução**

```
sc stop SCUMServer
    │
    ├─→ Service Control Manager (SCM)
    │       │
    │       ├─→ Envia SERVICE_CONTROL_STOP ao serviço
    │       │
    │       ├─→ Serviço recebe o sinal
    │       │       │
    │       │       ├─→ Executa código de shutdown (se implementado)
    │       │       │   └─→ Permite limpezas, backups, etc.
    │       │       │
    │       │       └─→ Retorna STATUS_PENDING ou STATUS_SUCCESS
    │       │
    │       └─→ Aguarda resposta (timeout padrão: ~30 segundos)
    │
    └─→ Retorna sucesso ou erro
```

## ✅ Características

### **Vantagens**

1. **✅ Shutdown Gracioso**
   - Permite que o serviço execute código de limpeza
   - Similar ao `Stop-Service` sem `-Force`
   - Respeita o ciclo de vida do serviço

2. **✅ Nativo do Windows**
   - Não requer instalação adicional
   - Disponível em todas as versões do Windows
   - Funciona via CMD, PowerShell, ou scripts

3. **✅ Confiável**
   - Usa o mesmo mecanismo que o Gerenciador de Serviços
   - Integrado ao sistema operacional
   - Bem testado e estável

4. **✅ Funciona em Scripts**
   - Pode ser usado em batch files (.bat)
   - Pode ser usado em PowerShell
   - Pode ser usado em scripts de automação

5. **✅ Não Requer Elevação (em alguns casos)**
   - Se você tem permissão para parar o serviço, funciona
   - Não precisa sempre executar como administrador

### **Desvantagens**

1. **⚠️ Timeout Padrão Limitado**
   - Timeout padrão é de aproximadamente 30 segundos
   - Se o serviço demorar mais, pode falhar
   - Não é configurável diretamente no comando

2. **⚠️ Menos Controle**
   - Não permite especificar timeout customizado
   - Não mostra progresso em tempo real
   - Retorna apenas sucesso/erro

3. **⚠️ Mensagens de Erro Limitadas**
   - Mensagens de erro podem ser genéricas
   - Pode ser difícil diagnosticar problemas

## 🔄 Comparação com Outros Métodos

### **SC Stop vs Stop-Service (PowerShell)**

| Característica | SC Stop | Stop-Service |
|----------------|---------|--------------|
| **Shutdown Gracioso** | ✅ Sim | ✅ Sim |
| **Timeout Configurável** | ❌ Não (30s padrão) | ✅ Sim (via parâmetros) |
| **Progresso em Tempo Real** | ❌ Não | ✅ Sim |
| **Mensagens de Erro** | ⚠️ Limitadas | ✅ Detalhadas |
| **Requer PowerShell** | ❌ Não | ✅ Sim |
| **Funciona em CMD** | ✅ Sim | ❌ Não |
| **Velocidade** | ⚡ Rápido | ⚡ Rápido |

**Conclusão**: `Stop-Service` é mais flexível, mas `sc stop` é mais universal.

### **SC Stop vs NSSM Stop**

| Característica | SC Stop | NSSM Stop |
|----------------|---------|-----------|
| **Shutdown Gracioso** | ✅ Sim | ✅ Sim |
| **Envia CTRL_C_EVENT** | ❌ Não | ✅ Sim |
| **Timeout Configurável** | ❌ Não | ✅ Sim (via código) |
| **Requer Instalação** | ❌ Não | ✅ Sim (NSSM) |
| **Controle de Processo** | ⚠️ Limitado | ✅ Total |
| **Melhor para NSSM** | ❌ Não | ✅ Sim |

**Conclusão**: Para serviços gerenciados pelo NSSM, `nssm stop` é preferível.

## 💻 Exemplos de Uso

### **1. Uso Básico (CMD)**
```cmd
sc stop SCUMServer
```

### **2. Uso em PowerShell**
```powershell
# Direto
sc stop SCUMServer

# Ou via Invoke-Expression
Invoke-Expression "sc stop SCUMServer"
```

### **3. Uso em Script Batch**
```batch
@echo off
echo Parando servidor SCUM...
sc stop SCUMServer
if %errorlevel% == 0 (
    echo Servidor parado com sucesso!
) else (
    echo Erro ao parar servidor!
)
```

### **4. Verificar Status Antes de Parar**
```cmd
sc query SCUMServer
sc stop SCUMServer
```

### **5. Com Retry (PowerShell)**
```powershell
$serviceName = "SCUMServer"
$maxRetries = 3
$retryCount = 0

while ($retryCount -lt $maxRetries) {
    $result = sc stop $serviceName
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Serviço parado com sucesso!"
        break
    }
    $retryCount++
    Start-Sleep -Seconds 5
}
```

## 🔍 Códigos de Retorno

O `sc stop` retorna códigos de saída:

| Código | Significado |
|--------|-------------|
| `0` | ✅ Sucesso - Serviço parado |
| `1` | ❌ Erro - Comando inválido |
| `2` | ❌ Erro - Serviço não encontrado |
| `3` | ❌ Erro - Acesso negado |
| `1052` | ❌ Erro - Timeout (serviço não parou a tempo) |
| `1053` | ❌ Erro - Serviço não respondeu |

## ⚙️ Como Funciona com NSSM

Quando o serviço é gerenciado pelo NSSM:

1. **SC Stop** → SCM → NSSM → Processo SCUM
   - O SCM envia sinal ao NSSM
   - O NSSM pode interceptar e enviar `CTRL_C_EVENT` ao processo
   - Permite shutdown gracioso

2. **NSSM Stop** → NSSM → Processo SCUM
   - NSSM envia diretamente `CTRL_C_EVENT` ao processo
   - Mais direto e confiável para serviços NSSM

**Recomendação**: Para serviços NSSM, use `nssm stop` diretamente.

## 🎯 Quando Usar SC Stop?

### ✅ **Use SC Stop quando:**
- Você precisa de um método universal (funciona em CMD e PowerShell)
- O serviço não é gerenciado pelo NSSM
- Você quer um método simples e direto
- Você está em um ambiente onde PowerShell não está disponível
- Você precisa de um fallback adicional

### ❌ **NÃO use SC Stop quando:**
- O serviço é gerenciado pelo NSSM (use `nssm stop`)
- Você precisa de timeout customizado longo (>30 segundos)
- Você precisa de feedback em tempo real
- Você precisa de mensagens de erro detalhadas

## 🔧 Implementação no Código

Se quiséssemos adicionar `sc stop` como fallback adicional:

```python
def _stop_service_sc(self) -> Dict[str, Any]:
    """Método alternativo via SC (Service Control)"""
    try:
        self.logger.info("[3/3] Tentando parar serviço via SC (Service Control)...")
        
        # Executar sc stop
        result = subprocess.run([
            "sc", "stop", self.service_name
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Aguardar shutdown gracioso (até 2 minutos)
            max_wait_time = 120
            check_interval = 5
            waited = 0
            
            while waited < max_wait_time:
                if not self._is_service_running():
                    self.logger.info(f"Serviço parado via SC após {waited} segundos")
                    return {"success": True, "message": "Serviço parado via SC"}
                time.sleep(check_interval)
                waited += check_interval
                if waited % 30 == 0:
                    self.logger.info(f"Aguardando shutdown gracioso... ({waited}/{max_wait_time}s)")
            
            # Verificar novamente
            if not self._is_service_running():
                return {"success": True, "message": "Serviço parado via SC"}
            else:
                return {"success": False, "message": "SC não conseguiu parar o serviço"}
        else:
            error_msg = result.stderr or result.stdout or "Erro desconhecido"
            return {"success": False, "message": f"Erro SC: {error_msg}"}
            
    except Exception as e:
        self.logger.error(f"Erro ao parar via SC: {e}")
        return {"success": False, "message": f"Erro SC: {str(e)}"}
```

## 📊 Resumo

| Aspecto | Detalhes |
|---------|----------|
| **Tipo** | Comando nativo do Windows |
| **Shutdown Gracioso** | ✅ Sim |
| **Timeout Padrão** | ~30 segundos |
| **Requer Instalação** | ❌ Não |
| **Funciona em CMD** | ✅ Sim |
| **Funciona em PowerShell** | ✅ Sim |
| **Melhor para NSSM** | ❌ Não (use `nssm stop`) |
| **Recomendado como** | Fallback adicional |

## 🔗 Referências

- [Microsoft Docs: SC Command](https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/sc-stop)
- [Service Control Manager](https://docs.microsoft.com/en-us/windows/win32/services/service-control-manager)
- [Windows Service States](https://docs.microsoft.com/en-us/windows/win32/services/service-status-transitions)

