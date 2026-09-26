# 🔧 Proposta: Remover Fallbacks e Usar Apenas NSSM

## 📋 Objetivo

Remover todos os métodos alternativos (PowerShell, SC) e fazer a aplicação usar **SOMENTE NSSM** para controle do serviço.

---

## 🔄 Mudanças Propostas

### **1. Validação Rigorosa no `__init__`**

**Localização:** `core/server_control/server_manager.py` (linha ~42-49)

**Mudança:**
```python
# ANTES:
nssm_path_config = config.get('nssm_path', 'nssm-2.24\\win64\\nssm.exe')
nssm_path = Path(nssm_path_config)
if not nssm_path.is_absolute():
    backend_root = Path(__file__).resolve().parents[2]
    nssm_path = backend_root / nssm_path
self.nssm_path = str(nssm_path)

# DEPOIS (MANTÉM CONVERSÃO RELATIVO → ABSOLUTO):
nssm_path_config = config.get('nssm_path', 'nssm-2.24\\win64\\nssm.exe')
nssm_path = Path(nssm_path_config)
if not nssm_path.is_absolute():
    backend_root = Path(__file__).resolve().parents[2]
    nssm_path = backend_root / nssm_path
self.nssm_path = str(nssm_path)

# VALIDAÇÃO RIGOROSA: Se NSSM não existir, lançar exceção
if not os.path.exists(self.nssm_path):
    error_msg = (
        f"ERRO CRÍTICO: NSSM não encontrado em: {self.nssm_path}\n"
        f"A aplicação requer NSSM e não possui fallbacks.\n"
        f"Configure o caminho correto no config.json:\n"
        f'  "nssm_path": "nssm-2.24\\\\win64\\\\nssm.exe"  (relativo ao Backend)\n'
        f'  OU\n'
        f'  "nssm_path": "C:\\\\caminho\\\\completo\\\\para\\\\nssm.exe"  (absoluto)'
    )
    self.logger.error(error_msg)
    raise FileNotFoundError(error_msg)
    
self.logger.info(f"NSSM validado e encontrado em: {self.nssm_path}")
```

**Nota:** O caminho no `config.json` pode continuar sendo **relativo** (ex: `"nssm-2.24\\win64\\nssm.exe"`). O código automaticamente converte para absoluto baseado no diretório do Backend.

---

### **2. Remover Fallbacks do `start_server()`**

**Localização:** `core/server_control/server_manager.py` (linha ~196-212)

**Mudança:**
```python
# ANTES:
# 2. Iniciar serviço via NSSM
start_result = self._start_service_nssm()
if start_result["success"]:
    return self._verify_startup()

# 3. Método alternativo via PowerShell
self.logger.info("[3/3] Tentando iniciar serviço via PowerShell elevado...")
alt_result = self._start_service_powershell()
if alt_result["success"]:
    return self._verify_startup()

# Se chegou aqui, falhou
return {
    "success": False,
    "message": "Falha ao iniciar serviço após todas as tentativas",
    "status": "start_failed"
}

# DEPOIS:
# Iniciar serviço via NSSM (ÚNICO MÉTODO)
start_result = self._start_service_nssm()
if start_result["success"]:
    return self._verify_startup()

# Se NSSM falhou, retornar erro imediatamente (SEM FALLBACKS)
error_status = start_result.get("status", "unknown")
error_message = start_result.get("message", "Erro desconhecido")
self.logger.error(f"Falha ao iniciar serviço via NSSM: {error_message}")
return {
    "success": False,
    "message": f"Falha ao iniciar serviço via NSSM: {error_message}",
    "status": error_status,
    "nssm_path": self.nssm_path
}
```

---

### **3. Remover Fallbacks do `stop_server()`**

**Localização:** `core/server_control/server_manager.py` (linha ~247-269)

**Mudança:**
```python
# ANTES:
# 1. Parar via NSSM
stop_result = self._stop_service_nssm()
if stop_result["success"]:
    return self._verify_stop(scum_db_path=scum_db_path, elevated_users_manager=elevated_users_manager)

# 2. Método alternativo via PowerShell
self.logger.info("[2/3] Tentando parar serviço via PowerShell elevado...")
alt_result = self._stop_service_powershell()
if alt_result["success"]:
    return self._verify_stop(scum_db_path=scum_db_path, elevated_users_manager=elevated_users_manager)

# 3. Método alternativo via SC (Service Control)
self.logger.info("[3/3] Tentando parar serviço via SC (Service Control)...")
sc_result = self._stop_service_sc()
if sc_result["success"]:
    return self._verify_stop(scum_db_path=scum_db_path, elevated_users_manager=elevated_users_manager)

# Se chegou aqui, falhou
return {
    "success": False,
    "message": "Falha ao parar serviço após todas as tentativas (NSSM, PowerShell, SC)",
    "status": "stop_failed"
}

# DEPOIS:
# Parar via NSSM (ÚNICO MÉTODO)
stop_result = self._stop_service_nssm()
if stop_result["success"]:
    return self._verify_stop(scum_db_path=scum_db_path, elevated_users_manager=elevated_users_manager)

# Se NSSM falhou, retornar erro imediatamente (SEM FALLBACKS)
error_status = stop_result.get("status", "unknown")
error_message = stop_result.get("message", "Erro desconhecido")
self.logger.error(f"Falha ao parar serviço via NSSM: {error_message}")
return {
    "success": False,
    "message": f"Falha ao parar serviço via NSSM: {error_message}",
    "status": error_status,
    "nssm_path": self.nssm_path
}
```

---

### **4. Atualizar Mensagens nos Métodos NSSM**

**Localização:** `core/server_control/server_manager.py`

#### **4.1. `_start_service_nssm()` (linha ~975)**

**Mudança:**
```python
# ANTES:
self.logger.info("[2/3] Iniciando serviço SCUMServer...")

# DEPOIS:
self.logger.info("Iniciando serviço SCUMServer via NSSM...")
```

**E remover:**
```python
# REMOVER estas linhas:
self.logger.warn("NSSM não conseguiu iniciar o serviço.")
self.logger.info("Tentando método alternativo...")
return {"success": False, "message": "NSSM falhou, tentando método alternativo"}

# SUBSTITUIR por:
self.logger.error("NSSM não conseguiu iniciar o serviço.")
return {
    "success": False,
    "message": f"NSSM falhou ao iniciar serviço. Verifique os logs do serviço Windows.",
    "status": "nssm_start_failed"
}
```

#### **4.2. `_stop_service_nssm()` (linha ~1134)**

**Mudança:**
```python
# ANTES:
self.logger.info("[1/2] Parando serviço via NSSM com shutdown gracioso...")

# DEPOIS:
self.logger.info("Parando serviço via NSSM com shutdown gracioso...")
```

**E remover:**
```python
# REMOVER estas linhas:
self.logger.warn("NSSM não conseguiu parar o serviço após shutdown gracioso.")
self.logger.info("Tentando método alternativo...")
return {"success": False, "message": "NSSM falhou, tentando método alternativo"}

# SUBSTITUIR por:
self.logger.error("NSSM não conseguiu parar o serviço após shutdown gracioso (2 minutos).")
return {
    "success": False,
    "message": "NSSM falhou ao parar serviço após 2 minutos de shutdown gracioso. O servidor pode estar travado.",
    "status": "nssm_stop_timeout"
}
```

---

## ⚠️ Impactos e Considerações

### **Vantagens:**
- ✅ Código mais simples e direto
- ✅ Sem ambiguidade sobre qual método será usado
- ✅ Erros mais claros quando NSSM falhar
- ✅ Força configuração correta do NSSM

### **Desvantagens:**
- ❌ Se NSSM não estiver configurado corretamente, aplicação não funcionará
- ❌ Se NSSM falhar, não há alternativa automática
- ❌ Requer que o usuário configure o caminho do NSSM corretamente

### **Recomendações:**
1. **Documentação clara** sobre como configurar `nssm_path` no `config.json`
   - Pode ser **relativo** (ex: `"nssm-2.24\\win64\\nssm.exe"`) - convertido automaticamente para absoluto
   - Ou **absoluto** (ex: `"C:\\Servers\\SSM3.0\\nssm-2.24\\win64\\nssm.exe"`)
2. **Mensagens de erro descritivas** quando NSSM não for encontrado
3. **Validação na inicialização** para detectar problemas cedo
4. **Possível melhoria futura:** Detecção automática do caminho do NSSM consultando o serviço Windows

---

## 📝 Resumo das Mudanças

| Arquivo | Linhas | Mudança |
|---------|--------|---------|
| `server_manager.py` | ~42-49 | Adicionar validação rigorosa do NSSM no `__init__` |
| `server_manager.py` | ~196-212 | Remover fallback PowerShell do `start_server()` |
| `server_manager.py` | ~247-269 | Remover fallbacks PowerShell e SC do `stop_server()` |
| `server_manager.py` | ~975 | Atualizar mensagens em `_start_service_nssm()` |
| `server_manager.py` | ~1134 | Atualizar mensagens em `_stop_service_nssm()` |

---

## 🧪 Como Testar

1. **Teste com NSSM configurado corretamente:**
   - Deve funcionar normalmente

2. **Teste com NSSM não encontrado:**
   - Deve lançar exceção na inicialização
   - Mensagem de erro clara

3. **Teste com NSSM falhando:**
   - Deve retornar erro imediatamente
   - Sem tentar métodos alternativos

---

**Status:** 📝 Proposta - Aguardando aprovação para implementação

