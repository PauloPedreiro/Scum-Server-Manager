# 🛡️ Planejamento: Segurança no Intervalo de Validação de Licença

## 🔴 Problema Identificado

**Vulnerabilidade de Segurança:**
- Usuário pode modificar `config.json` e alterar `check_interval` para um valor muito alto (ex: 999999999 segundos)
- Isso permite evitar validações periódicas da licença
- Compromete a segurança do sistema de licenciamento

**Localização do problema:**
- `data/config.json` → `communication.license_validation.check_interval`
- `data/config.json` → `licensing.validation_interval_seconds`

---

## ✅ Soluções Propostas

### **Opção A: Hardcoded no Código (Recomendada)**
**Vantagens:**
- ✅ Máxima segurança - usuário não pode alterar
- ✅ Simples de implementar
- ✅ Sem dependência de configuração externa
- ✅ Fácil manutenção

**Desvantagens:**
- ❌ Não é configurável (mas isso é uma vantagem de segurança)
- ❌ Requer recompilação para mudar (mas isso é desejável)

**Implementação:**
```python
# Constante no código
VALIDATION_INTERVAL_SECONDS = 14400  # 4 horas - NÃO ALTERAR

def should_validate_now(self) -> bool:
    check_interval = VALIDATION_INTERVAL_SECONDS  # Ignora config.json
    # ... resto do código
```

---

### **Opção B: Hardcoded + Validação de Máximo**
**Vantagens:**
- ✅ Permite configuração, mas com limite máximo
- ✅ Mais flexível para testes
- ✅ Ainda mantém segurança

**Desvantagens:**
- ❌ Ainda permite alguma manipulação (dentro do limite)
- ❌ Mais complexo

**Implementação:**
```python
# Constante no código
MAX_VALIDATION_INTERVAL_SECONDS = 14400  # 4 horas - máximo permitido

def should_validate_now(self) -> bool:
    config_interval = self.licensing_config.get('validation_interval_seconds', 14400)
    # Forçar máximo de 4 horas
    check_interval = min(config_interval, MAX_VALIDATION_INTERVAL_SECONDS)
    # ... resto do código
```

---

### **Opção C: Hardcoded + Log de Tentativa de Alteração**
**Vantagens:**
- ✅ Máxima segurança
- ✅ Detecta tentativas de alteração
- ✅ Pode alertar servidor de licenciamento

**Desvantagens:**
- ❌ Mais complexo
- ❌ Requer logging adicional

**Implementação:**
```python
VALIDATION_INTERVAL_SECONDS = 14400  # 4 horas

def should_validate_now(self) -> bool:
    config_interval = self.licensing_config.get('validation_interval_seconds', 14400)
    
    # Detectar tentativa de alteração
    if config_interval != VALIDATION_INTERVAL_SECONDS:
        self.logger.warning(
            f"Tentativa de alterar intervalo de validação detectada: "
            f"{config_interval}s (ignorado, usando {VALIDATION_INTERVAL_SECONDS}s)"
        )
        # Opcional: reportar ao servidor de licenciamento
    
    check_interval = VALIDATION_INTERVAL_SECONDS  # Sempre usar valor hardcoded
    # ... resto do código
```

---

## 🎯 Recomendação: **Opção A + C (Híbrida)**

**Implementação recomendada:**
1. **Hardcoded no código** - Valor fixo de 4 horas (14400 segundos)
2. **Ignorar config.json** - Não usar valores do arquivo de configuração
3. **Log de tentativas** - Registrar se usuário tentou alterar (para auditoria)
4. **Comentário de segurança** - Documentar que não deve ser alterado

**Benefícios:**
- ✅ Máxima segurança
- ✅ Detecção de tentativas de bypass
- ✅ Simples de manter
- ✅ Não compromete funcionalidade

---

## 📋 Plano de Implementação

### **1. Criar constante de segurança**
```python
# core/communication/license_validator.py

# Constante de segurança - NÃO ALTERAR
# Este valor é hardcoded para prevenir manipulação via config.json
VALIDATION_INTERVAL_SECONDS = 14400  # 4 horas
```

### **2. Atualizar método `should_validate_now()`**
```python
def should_validate_now(self) -> bool:
    # Usar valor hardcoded (ignorar config.json para segurança)
    check_interval = VALIDATION_INTERVAL_SECONDS
    
    # Detectar tentativa de alteração (para auditoria)
    config_interval = self.licensing_config.get('validation_interval_seconds', None)
    if config_interval and config_interval != VALIDATION_INTERVAL_SECONDS:
        self.logger.warning(
            f"Security: Attempt to modify validation interval detected "
            f"(config: {config_interval}s, using: {VALIDATION_INTERVAL_SECONDS}s)"
        )
    
    # ... resto do código
```

### **3. Atualizar método `get_license_status()`**
```python
def get_license_status(self) -> Dict[str, Any]:
    return {
        # ... outros campos
        "check_interval": VALIDATION_INTERVAL_SECONDS,  # Sempre retornar valor hardcoded
        # ... outros campos
    }
```

### **4. Remover do config.json (opcional)**
- Manter no config.json para referência/documentação
- Adicionar comentário: "Este valor é ignorado - definido no código por segurança"

---

## 🔒 Considerações de Segurança Adicionais

### **Outros parâmetros que podem precisar de proteção:**
1. `grace_period` - Período de graça após falha de validação
2. `block_on_invalid` - Se deve bloquear quando inválido
3. `enabled` - Se validação está habilitada

### **Recomendações:**
- ✅ `check_interval` → **Hardcoded** (crítico)
- ⚠️ `grace_period` → Pode manter configurável (menos crítico)
- ⚠️ `block_on_invalid` → Pode manter configurável (mas validar)
- ⚠️ `enabled` → Pode manter configurável (mas sempre validar se server_url existe)

---

## 📝 Checklist de Implementação

- [ ] Criar constante `VALIDATION_INTERVAL_SECONDS` no código
- [ ] Atualizar `should_validate_now()` para usar constante
- [ ] Adicionar log de detecção de tentativas de alteração
- [ ] Atualizar `get_license_status()` para retornar valor hardcoded
- [ ] Adicionar comentários de segurança no código
- [ ] Testar que alterações no config.json são ignoradas
- [ ] Documentar no código que não deve ser alterado
- [ ] Verificar se há outros lugares que usam esse valor

---

## 🧪 Testes Necessários

1. **Teste de Segurança:**
   - Alterar `check_interval` no config.json para 999999999
   - Verificar que validação ainda ocorre a cada 4 horas
   - Verificar log de tentativa de alteração

2. **Teste de Funcionalidade:**
   - Verificar que validação ocorre corretamente a cada 4 horas
   - Verificar que status retorna valor correto

3. **Teste de Edge Cases:**
   - Config.json com valor muito baixo (deve usar 4h)
   - Config.json sem o campo (deve usar 4h)
   - Config.json com valor negativo (deve usar 4h)

