# 🔓 Explicação: Como Funciona a Liberação no Start (Inicialização)

## 📋 Visão Geral

Quando o SSM Backend inicia, ele **DEVE** validar a licença antes de continuar. Se a validação falhar, o backend é **imediatamente encerrado** (não inicia).

---

## 🔄 Fluxo Completo da Validação Inicial

### **Passo 1: Inicialização dos Componentes**

```787:828:main.py
def validate_license_simple(validation_type: str = "initial"):
    """
    Validar licença usando o mesmo processo que a GUI usa
    Retorna: (is_valid: bool, message: str, reason: Optional[str])
    
    Args:
        validation_type: "initial" ou "periodic" - usado apenas para logs
    """
    global _validation_hash
    try:
        # SEGURANÇA: URL é hardcoded (definida no início do arquivo)
        server_url = LICENSE_SERVER_URL
        
        # Importar módulos necessários
        from core.licensing.hardware_fingerprint import HardwareFingerprint
        from core.licensing.license_client import LicenseClient
        from core.licensing.license_cache import LicenseCache
        
        # Inicializar HardwareFingerprint
        hardware_fp = HardwareFingerprint(logger=logger)
        
        # Gerar equipment_hash
        # SEGURANÇA: Hash sempre gerado em memória, nunca armazenado
        equipment_hash, components = hardware_fp.generate()
        _validation_hash = equipment_hash  # Armazenar para usar no webhook
        validation_label = "VALIDAÇÃO INICIAL" if validation_type == "initial" else "VALIDAÇÃO PERIÓDICA"
        logger.info(f"🔑 {validation_label}: Hash gerado: {equipment_hash}")
        logger.info(f"🔑 {validation_label}: Hash completo (64 chars): {equipment_hash} (comprimento: {len(equipment_hash)})")
        
        # Coletar hardware_list completo
        hardware_list = hardware_fp.get_hardware_list()
        
        # Inicializar LicenseClient
        # SEGURANÇA: Timeouts e retries hardcodados (otimizados para servidores distantes)
        license_client = LicenseClient(
            server_url=server_url,
            timeout=45,  # 45 segundos (aumentado para suportar servidores distantes)
            retry_attempts=5,  # 5 tentativas (aumentado para maior robustez)
            retry_delay=30,  # Ignorado (usa backoff exponencial)
            use_exponential_backoff=True,  # Backoff exponencial: 2s, 5s, 10s
            logger=logger
        )
```

**O que acontece:**
1. ✅ Importa módulos necessários (`HardwareFingerprint`, `LicenseClient`, `LicenseCache`)
2. ✅ Cria instância de `HardwareFingerprint` para gerar hash do hardware
3. ✅ Gera `equipment_hash` (hash único do hardware) - **sempre em memória, nunca salvo**
4. ✅ Coleta `hardware_list` completo (lista de componentes de hardware)
5. ✅ Cria `LicenseClient` com configurações de timeout e retry

---

### **Passo 2: Obter e Validar API Key**

```830:843:main.py
# Obter API key
api_key = licensing_config.get('gestao_api_key') or licensing_config.get('api_key')

# Descriptografar API key se estiver criptografada
if api_key:
    try:
        from core.security.credential_encryption import decrypt_credential
        api_key = decrypt_credential(api_key, logger=logger)
    except Exception as e:
        logger.warn(f"Erro ao descriptografar API key (pode estar em texto plano): {e}")

# Verificar se API key está faltando
if not api_key or api_key.strip() == "":
    return False, "API Key não configurada", "api_key_missing"
```

**O que acontece:**
1. ✅ Busca API key no `config.json` (seção `licensing.gestao_api_key` ou `licensing.api_key`)
2. ✅ Tenta descriptografar a API key (se estiver criptografada)
3. ❌ **Se API key não existir ou estiver vazia → FALHA IMEDIATA** (backend não inicia)

---

### **Passo 3: Enviar Requisição ao Servidor**

```845:851:main.py
# Validar com servidor
response = license_client.validate_equipment(
    equipment_hash=equipment_hash,  # ✅ SEMPRE hash atual gerado em memória
    hardware_list=hardware_list,
    version=VERSION,
    api_key=api_key
)
```

**O que acontece:**
1. ✅ Envia requisição POST para `/api/v1/validate` no servidor do Gestão
2. ✅ Payload enviado:
   ```json
   {
     "equipment_hash": "abc123...",  // Hash do hardware (64 caracteres)
     "hardware_list": { ... },        // Lista completa de hardware
     "timestamp": "2025-01-XX...",    // Timestamp UTC
     "version": "3.0",                // Versão do SSM Backend
     "api_key": "ssm_xxxxx"           // API Key para autenticação
   }
   ```
3. ✅ **Retry automático**: Se falhar, tenta novamente até 5 vezes com backoff exponencial (2s, 5s, 10s, 10s, 10s)
4. ✅ **Timeout**: Cada tentativa tem timeout de 45 segundos

---

### **Passo 4: Processar Resposta do Servidor**

```637:705:main.py
def process_license_response(response: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Processar resposta do servidor de licenciamento
    Retorna: (is_valid: bool, message: str, reason: Optional[str])
    
    SEGURANÇA: Distingue entre erros de rede (permitem grace period) 
    e licença inválida (bloqueiam imediatamente)
    """
    # Verificar resposta (MESMA LÓGICA DA GUI)
    status_code = response.get('status_code', 200)
    has_error = response.get('error') is not None
    success = response.get('success')
    error_type = response.get('error_type')  # Tipo de erro (Timeout, ConnectionError, etc)
    
    # PRIORIDADE 1: status_code = 0 = erro de conexão/rede
    # Este é um erro de rede (timeout, connection error, etc)
    # Diferente de licença inválida - pode permitir grace period se cache válido
    if status_code == 0:
        error_msg = response.get('error', 'Erro de conexão com servidor de licenciamento')
        logger.warn(f"Erro de rede detectado na validação: {error_msg} (tipo: {error_type})")
        # Retornar network_error para permitir tratamento diferenciado (grace period)
        return False, error_msg, "network_error"
    
    # PRIORIDADE 2: success = False = erro (pode ser rede ou servidor)
    # Se não tem status_code ou status_code não é 0, tratar como erro de servidor
    if success is False:
        error_msg = response.get('error', 'Erro na validação')
        logger.warn(f"Erro na resposta do servidor (success=False): {error_msg}")
        # Se status_code existe e não é 0, não é erro de rede
        if status_code and status_code != 0:
            return False, error_msg, "server_error"
        else:
            return False, error_msg, "network_error"
    
    # PRIORIDADE 3: campo 'error' presente = erro
    # Verificar se é erro de rede (status_code = 0) ou erro de servidor
    if has_error:
        error_msg = response.get('error', 'Erro na validação')
        logger.warn(f"Campo 'error' presente na resposta: {error_msg}")
        if status_code == 0:
            return False, error_msg, "network_error"
        else:
            return False, error_msg, "server_error"
    
    # PRIORIDADE 4: status_code != 200 = erro de servidor (não rede)
    if status_code != 200:
        error_msg = f"Resposta inesperada do servidor (status_code={status_code})"
        logger.warn(f"Status code inválido: {status_code}")
        # Status code diferente de 200 mas existe = erro de servidor (não rede)
        return False, error_msg, "server_error"
    
    # PRIORIDADE 5: Verificar campo 'valid'
    is_valid = response.get('valid')
    if is_valid is None:
        error_msg = "Resposta do servidor não contém campo 'valid'"
        logger.warn(f"Resposta inválida: campo 'valid' ausente. Resposta completa: {response}")
        return False, error_msg, "server_error"
    
    # PRIORIDADE 6: Verificar se licença é válida
    if is_valid is True:
        return True, "Equipamento liberado", None
    else:
        # Licença inválida - SEMPRE bloquear (não é erro de rede)
        reason = response.get('reason', 'unknown')
        message = response.get('message', 'Licença inválida')
        logger.error(f"Licença inválida - Reason: {reason}, Message: {message}")
        # Retornar reason específica para permitir tratamento diferenciado
        return False, message, reason
```

**Ordem de verificação (prioridades):**

1. **PRIORIDADE 1**: `status_code == 0` → Erro de rede (timeout, conexão)
   - Retorna: `(False, erro, "network_error")`
   - ⚠️ **Na validação inicial, erro de rede = FALHA** (não há cache ainda)

2. **PRIORIDADE 2**: `success == False` → Erro do servidor ou rede
   - Verifica `status_code` para distinguir

3. **PRIORIDADE 3**: Campo `error` presente → Erro explícito
   - Verifica `status_code` para distinguir

4. **PRIORIDADE 4**: `status_code != 200` → Erro do servidor
   - Exceção: `status_code == 422` pode ser erro de API key

5. **PRIORIDADE 5**: Campo `valid` ausente → Resposta inválida

6. **PRIORIDADE 6**: Verificar `valid == True`
   - ✅ **Se `valid == True` → SUCESSO**
   - ❌ **Se `valid == False` → FALHA** (reason: `not_registered`, `expired`, etc.)

---

### **Passo 5: Decisão Final (Sucesso ou Falha)**

```863:896:main.py
# VALIDAÇÃO INICIAL - Ao iniciar o backend
# SEGURANÇA: URL é hardcoded para https://scumsm.com
licensing_config = config.get('licensing', {})
# Segurança: validação inicial sempre habilitada (ignorar config)
server_url = LICENSE_SERVER_URL
logger.debug(f"Validando licença inicial com servidor: {server_url}")

is_valid, message, reason = validate_license_simple(validation_type="initial")

if not is_valid:
    logger.critical(f"Validação inicial falhou: {message}")
    if reason:
        logger.critical(f"Motivo: {reason}")
    
    # Enviar notificação de falha para Discord
    send_license_validation_notification(
        validation_type="initial",
        is_valid=False,
        message=message,
        reason=reason
    )
    
    logger.critical("Encerrando SSM Backend...")
    time.sleep(2)
    os._exit(1)
else:
    logger.info(f"Validação inicial concluída com sucesso: {message}")
    
    # Enviar notificação de sucesso para Discord
    send_license_validation_notification(
        validation_type="initial",
        is_valid=True,
        message=message
    )
```

**Se FALHAR (`is_valid == False`):**
1. ❌ Log crítico da falha
2. ❌ Envia notificação de falha para Discord
3. ❌ Aguarda 2 segundos
4. ❌ **Encerra o backend imediatamente** (`os._exit(1)`)
5. ❌ **Backend NÃO inicia**

**Se SUCESSO (`is_valid == True`):**
1. ✅ Log de sucesso
2. ✅ Envia notificação de sucesso para Discord
3. ✅ **Backend continua inicializando normalmente**
4. ✅ Salva resultado no cache (para uso futuro)

---

## 🔑 Diferenças Importantes: Inicial vs Periódica

### **Validação Inicial (Start)**
- ❌ **NÃO usa cache** (não há cache ainda)
- ❌ **Erro de rede = FALHA** (backend não inicia)
- ❌ **Qualquer erro = FALHA** (backend não inicia)
- ✅ **Bloqueio imediato** se inválido

### **Validação Periódica (4 horas)**
- ✅ **Pode usar cache** se ainda válido (< 4 horas)
- ✅ **Erro de rede + cache válido = CONTINUA** (grace period)
- ✅ **Erro de rede + cache expirado = FALHA** (bloqueia)
- ✅ **Múltiplas tentativas** antes de bloquear

---

## 📊 Resumo do Fluxo

```
START BACKEND
    ↓
1. Gerar hash do hardware (em memória)
    ↓
2. Verificar API key (obrigatória)
    ↓
3. Enviar requisição ao servidor (5 tentativas, 45s timeout cada)
    ↓
4. Processar resposta (verificar status_code, valid, etc.)
    ↓
5. DECISÃO:
    ├─ ✅ SUCESSO → Backend continua
    └─ ❌ FALHA → Backend encerra (os._exit(1))
```

---

## ⚠️ Pontos Críticos

1. **API Key é OBRIGATÓRIA**: Sem API key, backend não inicia
2. **Hash sempre gerado em memória**: Nunca é salvo (segurança)
3. **Sem cache na inicialização**: Sempre valida com servidor
4. **Erro de rede = FALHA na inicialização**: Não há grace period
5. **Bloqueio imediato**: Se inválido, encerra em 2 segundos
6. **URL hardcoded**: Não pode ser alterada via config.json (segurança)

---

## 🔍 Logs Importantes

Durante a validação inicial, você verá logs como:

```
🔑 VALIDAÇÃO INICIAL: Hash gerado: abc123...
🔑 VALIDAÇÃO INICIAL: Hash completo (64 chars): abc123... (comprimento: 64)
Requisição POST https://scumsm.com/api/v1/validate (tentativa 1/5, timeout: 45s)
Validação bem-sucedida: True (latência: 2.34s)
Validação inicial concluída com sucesso: Equipamento liberado
```

Ou em caso de falha:

```
Erro de rede detectado na validação: Timeout na requisição após 45s (tipo: Timeout)
Validação inicial falhou: Timeout na requisição após 45s
Motivo: network_error
Encerrando SSM Backend...
```

---

**Data da Explicação:** 2025-01-XX  
**Versão do SSM Backend:** 3.0

