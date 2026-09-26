# 📊 Análise do Processo de Cópia do SCUM.db

## 🔍 Problema Identificado

A cópia do SCUM.db em `data/temp/SCUM.db.temp` estava sendo criada mas **não estava sendo removida** quando deveria.

### Status Encontrado:
- **Arquivo**: `data/temp/SCUM.db.temp`
- **Tamanho**: 6.18 MB
- **Idade**: 12.79 horas
- **Status**: EXPIRADO (idade máxima: 2 minutos)

---

## 🔧 Como Funciona o Sistema

### **ScumDbSharedCopyManager**

O sistema cria uma **cópia compartilhada** do SCUM.db para:
- ✅ Evitar bloqueios quando o servidor SCUM está rodando
- ✅ Melhorar performance (múltiplos serviços podem usar a mesma cópia)
- ✅ Reduzir I/O no disco

### **Ciclo de Vida da Cópia**

1. **Criação**: Quando um serviço precisa ler o SCUM.db
2. **Reutilização**: Outros serviços podem usar a mesma cópia (reference counting)
3. **Expiração**: Após 2 minutos (`max_copy_age_seconds = 120`)
4. **Remoção**: Quando:
   - Não há mais referências ativas (`reference_count = 0`) **E** está expirada
   - Ou durante limpeza de cópias órfãs (> 1 hora)

---

## 🐛 Problema Encontrado

### **Causa Raiz**

A função `_cleanup_orphaned_copies()` tinha uma lógica incompleta:

```python
# ANTES (PROBLEMA):
if filepath != self._copy_path and file_age > max_age_seconds:
    os.remove(filepath)  # Só remove se NÃO é a cópia atual
```

**Problema**: Se a cópia atual estava muito antiga (> 1 hora) mas ainda estava registrada como `_copy_path`, ela **não era removida** mesmo sem referências ativas.

### **Cenários que Causavam o Problema**

1. Backend foi fechado abruptamente sem liberar referências
2. Cópia ficou órfã mas ainda estava registrada como "cópia atual"
3. Limpeza automática não removia porque verificava `filepath != self._copy_path`

---

## ✅ Solução Implementada

### **Correção na Lógica de Limpeza**

Agora a função `_cleanup_orphaned_copies()` remove cópias em dois casos:

1. **Cópias órfãs** (não são a cópia atual):
   - Arquivos antigos (> 1 hora) que não são a cópia atual

2. **Cópia atual expirada sem referências**:
   - Se é a cópia atual (`filepath == self._copy_path`)
   - **E** está muito antiga (> 1 hora)
   - **E** não há referências ativas (`reference_count == 0`)
   - Então remove e limpa o estado interno

### **Código Corrigido**

```python
# DEPOIS (CORRIGIDO):
if filepath != self._copy_path:
    # Cópia órfã (não é a atual)
    if file_age > max_age_seconds:
        should_remove = True
        reason = "cópia órfã"
elif filepath == self._copy_path:
    # É a cópia atual, mas está muito antiga e sem referências
    if file_age > max_age_seconds and self._reference_count == 0:
        should_remove = True
        reason = "cópia atual expirada sem referências"
        # Limpar estado interno também
        self._copy_path = None
        self._copy_created_at = None
```

---

## 📋 Comportamento Esperado Agora

### **Cenário 1: Cópia em Uso**
- ✅ Cópia criada e sendo usada
- ✅ Expira após 2 minutos
- ✅ Continua disponível enquanto há referências
- ✅ Removida quando `reference_count = 0` **E** expirada

### **Cenário 2: Cópia Órfã**
- ✅ Cópia criada mas backend foi fechado
- ✅ Cópia fica antiga (> 1 hora)
- ✅ Limpeza automática remove na próxima inicialização
- ✅ Estado interno é limpo

### **Cenário 3: Múltiplas Cópias**
- ✅ Sistema mantém apenas 1 cópia ativa
- ✅ Cópias antigas são removidas automaticamente
- ✅ Limpeza executa na inicialização e quando necessário

---

## 🔄 Quando a Limpeza é Executada

1. **Na inicialização**: `configure()` chama `_cleanup_orphaned_copies()`
2. **Quando referências são liberadas**: `_release_copy()` verifica e remove se expirada
3. **Manual**: Pode ser chamada via API ou endpoint de limpeza

---

## ✅ Verificação

Execute o script de verificação:

```bash
python verificar_copia_scum_db.py
```

Isso mostrará:
- Status da cópia atual
- Idade e tamanho
- Se está expirada
- Se há outras cópias órfãs

---

## 📝 Configuração

No `config.json`:

```json
{
  "scum_db_shared_copy": {
    "enabled": true,
    "temp_dir": "data/temp",
    "max_copy_age_seconds": 120,        // 2 minutos
    "cleanup_orphaned_copies": true,     // Limpeza automática
    "max_orphan_age_hours": 1,           // Remove cópias > 1 hora
    "fallback_to_direct": true           // Usa banco original se falhar
  }
}
```

---

## 🎯 Conclusão

✅ **Problema corrigido**: A lógica de limpeza agora remove cópias órfãs corretamente, incluindo a cópia atual se estiver muito antiga e sem referências.

✅ **Comportamento esperado**: Cópias temporárias são criadas quando necessário e removidas automaticamente quando não são mais usadas.

✅ **Sistema funcionando**: O processo está correto e funcionando como esperado após a correção.

---

**Última Atualização**: 2025-12-16

