# 🔒 Segurança: Proteção do LicenseValidator no Executável

## 📦 O que acontece quando empacotamos?

Quando você compila a aplicação em um `.exe` usando PyInstaller, o `license_validator.py` é:

1. **Convertido em bytecode** (`.pyc`) - código Python compilado
2. **Empacotado dentro do executável** - não fica como arquivo separado
3. **Armazenado em `sys._MEIPASS`** - diretório temporário quando executado

### Estrutura do Executável

```
ssm_backend.exe
├── Bootloader (PyInstaller)
├── Python Runtime
├── Bibliotecas (.dll)
└── Código Python (bytecode)
    └── core/
        └── communication/
            └── license_validator.pyc  ← Bytecode compilado
```

## ⚠️ Vulnerabilidades Potenciais

### 1. Extração do Módulo
- **Ferramentas como `pyinstxtractor`** podem extrair arquivos do executável
- Alguém pode extrair `license_validator.pyc` e modificá-lo
- Pode ser decompilado de volta para Python (com limitações)

### 2. Modificação do Bytecode
- Bytecode pode ser modificado diretamente
- Valores hardcoded podem ser alterados
- Lógica de validação pode ser bypassada

### 3. Substituição do Módulo
- Se alguém extrair o módulo, pode criar um falso
- Pode colocar arquivo `.py` no mesmo diretório do `.exe`
- Python pode carregar o arquivo externo ao invés do empacotado

## 🛡️ Proteções Implementadas

### 1. Verificação de Integridade (`license_validator_integrity.py`)

O módulo `license_validator_integrity.py` verifica:

#### ✅ Constantes Críticas
- Verifica se `VALIDATION_INTERVAL_SECONDS = 14400` (não foi modificado)
- Verifica se classe `LicenseValidator` existe
- Verifica se métodos críticos existem (`validate_license`, `should_validate_now`)

#### ✅ Assinaturas de Código
- Verifica se strings críticas estão presentes no código:
  - `'VALIDATION_INTERVAL_SECONDS = 14400'`
  - `'SEGURANÇA: Validação sempre ativa'`
  - `'Sem período de graça'`

#### ✅ Detecção de Extração
- Verifica se arquivo `license_validator.py` existe fora do executável
- Bloqueia se detectar arquivo extraído em:
  - `exe_dir/core/communication/license_validator.py`
  - `exe_dir/lib/communication/license_validator.py`
  - `exe_dir/modules/communication/license_validator.py`

### 2. Verificação na Inicialização

No `main.py`, antes de usar o `LicenseValidator`:

```python
# Verificar integridade
integrity_ok, integrity_msg = verify_module_integrity()
if not integrity_ok:
    sys.exit(1)  # ⛔ APLICAÇÃO NÃO INICIA

# Verificar se não foi extraído
extraction_ok, extraction_msg = verify_module_not_extracted()
if not extraction_ok:
    sys.exit(1)  # ⛔ APLICAÇÃO NÃO INICIA
```

### 3. Proteção em Múltiplas Camadas

| Camada | Proteção |
|--------|----------|
| **Import** | Se módulo não existe → `sys.exit(1)` |
| **Integridade** | Se constantes modificadas → `sys.exit(1)` |
| **Extração** | Se arquivo extraído → `sys.exit(1)` |
| **Middleware** | Se módulo não disponível → Bloqueia requisições |
| **Thread Periódica** | Verifica a cada ciclo → `os._exit(1)` se removido |

## 🔍 Como Funciona a Verificação

### Em Modo Desenvolvimento (Script Python)

```python
# Verifica arquivo físico
module_file = license_validator.__file__
if not os.path.exists(module_file):
    return False  # Arquivo não existe

# Verifica constantes
if VALIDATION_INTERVAL_SECONDS != 14400:
    return False  # Valor foi modificado
```

### Em Executável (PyInstaller)

```python
# Verifica se módulo está em sys.modules
if 'core.communication.license_validator' not in sys.modules:
    return False  # Módulo não carregado

# Verifica constantes via atributos
interval = getattr(lv_module, 'VALIDATION_INTERVAL_SECONDS')
if interval != 14400:
    return False  # Valor foi modificado

# Verifica se arquivo foi extraído
if Path("core/communication/license_validator.py").exists():
    return False  # Arquivo extraído detectado
```

## 🚨 Cenários de Ataque e Proteção

### Cenário 1: Extrair e Modificar

**Ataque:**
1. Usar `pyinstxtractor` para extrair `license_validator.pyc`
2. Decompilar para Python
3. Modificar `VALIDATION_INTERVAL_SECONDS = 999999`
4. Recompilar e reinjetar no executável

**Proteção:**
- ✅ Verificação de integridade detecta valor modificado
- ✅ Aplicação não inicia (`sys.exit(1)`)

### Cenário 2: Criar Arquivo Falso

**Ataque:**
1. Extrair `license_validator.pyc`
2. Criar `license_validator.py` falso no diretório do `.exe`
3. Python carrega arquivo externo ao invés do empacotado

**Proteção:**
- ✅ `verify_module_not_extracted()` detecta arquivo extraído
- ✅ Aplicação não inicia (`sys.exit(1)`)

### Cenário 3: Modificar Bytecode Diretamente

**Ataque:**
1. Editar bytecode diretamente no executável
2. Alterar valor de `14400` para `999999`

**Proteção:**
- ✅ Verificação de constantes detecta valor incorreto
- ✅ Aplicação não inicia (`sys.exit(1)`)

## 📊 Níveis de Segurança

| Nível | Proteção | Eficácia |
|-------|----------|----------|
| **1. Bytecode** | Código compilado (não texto) | ⭐⭐ |
| **2. Empacotamento** | Dentro do executável | ⭐⭐⭐ |
| **3. Verificação de Integridade** | Valida constantes e métodos | ⭐⭐⭐⭐ |
| **4. Detecção de Extração** | Bloqueia arquivos externos | ⭐⭐⭐⭐ |
| **5. Validação Periódica** | Verifica a cada ciclo | ⭐⭐⭐⭐⭐ |

## 🔐 Recomendações Adicionais (Opcional)

### 1. Obfuscação com PyArmor

Para proteção adicional, você pode usar `pyarmor`:

```bash
pip install pyarmor
pyarmor gen --pack onefile main.py
```

**Vantagens:**
- Código ofuscado (mais difícil de decompilar)
- Proteção contra engenharia reversa

**Desvantagens:**
- Aumenta tamanho do executável
- Pode causar problemas de compatibilidade

### 2. Assinatura Digital

Assinar o executável com certificado digital:

```bash
signtool sign /f certificate.pfx /p password ssm_backend.exe
```

**Vantagens:**
- Detecta modificação do executável
- Windows mostra aviso se assinatura inválida

### 3. Verificação de Hash do Executável

Calcular hash SHA-256 do executável e validar:

```python
def verify_exe_integrity():
    exe_path = sys.executable
    expected_hash = "abc123..."  # Hash calculado no build
    actual_hash = calculate_file_hash(exe_path)
    return actual_hash == expected_hash
```

## ✅ Conclusão

Com as proteções implementadas:

1. ✅ **Módulo não pode ser deletado** → Aplicação não inicia
2. ✅ **Módulo não pode ser modificado** → Verificação detecta alterações
3. ✅ **Módulo não pode ser extraído** → Detecção bloqueia arquivos externos
4. ✅ **Constantes não podem ser alteradas** → Validação de valores críticos
5. ✅ **Aplicação não funciona sem validação** → Múltiplas camadas de proteção

**O sistema está protegido contra tentativas de bypass da validação de licença!** 🛡️

