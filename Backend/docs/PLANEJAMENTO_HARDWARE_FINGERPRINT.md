# 🔧 Planejamento: Sistema de Hardware Fingerprint

## 📋 Objetivo

Criar sistema para coletar MAC addresses e outros identificadores únicos de hardware, gerar hash único da máquina e integrar com servidor de gerenciamento para validação de licenças.

## 🔒 Princípio de Segurança Fundamental

**⚠️ IMPORTANTE:** O hash deve ser **SEMPRE gerado antes de consultar o servidor**, nunca usar hash armazenado para validação.

- ✅ **Hash armazenado**: Apenas para comparação local rápida e histórico
- ✅ **Hash gerado na hora**: Sempre enviado ao servidor (impossível falsificar)
- ✅ **Servidor decide**: Validação definitiva sempre no servidor

📖 **Ver detalhes completos em:** `docs/SEGURANCA_HASH_VALIDACAO.md`

---

## 🎯 Componentes a Coletar

### 1. MAC Addresses (Prioridade ALTA)

**Componentes com MAC:**
- ✅ **Placas de Rede** (Ethernet, Wi-Fi)
  - Método: WMI `Win32_NetworkAdapter`
  - Filtrar: `PhysicalAdapter = True`, `MACAddress IS NOT NULL`
  - Ordenar: Por nome para garantir ordem consistente

- ✅ **Placas de Vídeo** (se tiverem MAC)
  - Método: WMI `Win32_VideoController`
  - Nota: Nem todas têm MAC, usar como fallback

- ⚠️ **Adaptadores Virtuais** (filtrados)
  - Excluir: VMware, VirtualBox, Hyper-V, Loopback
  - Incluir apenas adaptadores físicos

### 2. Serial Numbers (Prioridade ALTA)

- ✅ **CPU ID/Processor ID**
  - Método: WMI `Win32_Processor.ProcessorId`
  - Fallback: `Win32_Processor.UniqueId` se ProcessorId não disponível

- ✅ **Disco Principal (HD/SSD)**
  - Método: WMI `Win32_DiskDrive.SerialNumber`
  - Múltiplos discos: Ordenar por `Index` e pegar todos
  - Fallback: Volume Serial Number via `GetVolumeInformation`

- ✅ **Placa Mãe (Motherboard)**
  - Método: WMI `Win32_BaseBoard.SerialNumber`
  - Fallback: `Win32_BaseBoard.Product`

- ✅ **BIOS Serial**
  - Método: WMI `Win32_BIOS.SerialNumber`

### 3. Identificadores do Sistema (Prioridade ALTA)

- ✅ **Windows Machine GUID**
  - Método: Registry `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography\MachineGuid`
  - Muito estável, não muda mesmo com reinstalação

- ✅ **Computer Name**
  - Método: `platform.node()` ou WMI
  - Prioridade: Baixa (pode mudar)

### 4. Componentes Adicionais (Prioridade MÉDIA)

- ⚠️ **RAM Serial** (se disponível)
  - Método: WMI `Win32_PhysicalMemory.SerialNumber`
  - Nota: Nem todos os módulos têm serial

- ⚠️ **GPU Serial** (se disponível)
  - Método: WMI `Win32_VideoController`
  - Nota: Raro ter serial

---

## 🏗️ Estrutura de Módulos

```
core/
├── licensing/                          # 🆕 Módulo de Licenciamento
│   ├── __init__.py
│   ├── hardware_fingerprint.py         # Coleta de hardware e geração de hash
│   ├── license_client.py              # Cliente HTTP para servidor de licenciamento
│   └── license_cache.py               # Cache local de validações
```

**Nota:** Não criamos `license_manager.py` porque não gerenciamos licenças localmente. Apenas validamos com o servidor.

---

## 📦 Dependências Necessárias

### Bibliotecas Python

```python
# requirements.txt (adicionar)
wmi>=1.5.1              # Windows Management Instrumentation
pywin32>=306            # Windows API (Registry, WMI)
cryptography>=41.0.0    # Hash e criptografia (já pode ter)
```

### Métodos Alternativos (se WMI falhar)

- **PowerShell**: Executar comandos PowerShell via subprocess
- **Registry**: Acesso direto via `winreg`
- **psutil**: Já existe, pode usar para algumas informações

---

## 🔍 Estratégia de Coleta

### Priorização de Componentes

```python
COMPONENT_PRIORITY = {
    "critical": [
        "windows_machine_guid",    # Sempre disponível, muito estável
        "cpu_id",                  # Sempre disponível
        "network_macs",            # Sempre disponível (pelo menos 1)
        "disk_serials"             # Sempre disponível (pelo menos 1)
    ],
    "high": [
        "motherboard_serial",      # Geralmente disponível
        "bios_serial"              # Geralmente disponível
    ],
    "medium": [
        "ram_serials",             # Pode não ter serial
        "gpu_macs"                 # Raro ter MAC
    ],
    "low": [
        "computer_name"            # Pode mudar
    ]
}
```

### Regra de Mínimo

- **Mínimo necessário**: 4 componentes críticos
- Se não conseguir 4 componentes críticos, usar fallbacks
- Se ainda assim não conseguir, gerar erro (não continuar)

---

## 🔐 Geração do Hash

### Algoritmo

```python
def generate_fingerprint(components: Dict[str, Any]) -> str:
    """
    1. Coletar todos os componentes disponíveis
    2. Ordenar cada lista (garantir ordem determinística)
    3. Normalizar valores (uppercase, remover espaços)
    4. Concatenar de forma determinística
    5. Aplicar hash SHA-256
    """
    
    # Ordenar e normalizar
    network_macs = sorted([mac.upper().replace('-', ':') 
                          for mac in components.get('network_macs', [])])
    disk_serials = sorted([serial.strip().upper() 
                          for serial in components.get('disk_serials', [])])
    
    # Concatenar de forma determinística
    fingerprint_string = "|".join([
        f"NET:{','.join(network_macs)}",
        f"CPU:{components.get('cpu_id', '').strip().upper()}",
        f"DISK:{','.join(disk_serials)}",
        f"MB:{components.get('motherboard_serial', '').strip().upper()}",
        f"BIOS:{components.get('bios_serial', '').strip().upper()}",
        f"WIN:{components.get('windows_guid', '').strip().upper()}",
        f"RAM:{','.join(sorted(components.get('ram_serials', [])))}",
        f"GPU:{','.join(sorted(components.get('gpu_macs', [])))}"
    ])
    
    # Hash SHA-256
    import hashlib
    hash_value = hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()
    
    return hash_value
```

### Características do Hash

- ✅ **Determinístico**: Mesma máquina sempre gera mesmo hash
- ✅ **Case-insensitive**: Normaliza para uppercase
- ✅ **Ordenado**: Listas sempre ordenadas
- ✅ **Consistente**: Mesma ordem de componentes sempre

---

## 💾 Armazenamento Local

### Arquivo: `data/hardware_fingerprint.json`

```json
{
  "fingerprint_hash": "a1b2c3d4e5f6...",
  "generated_at": "2025-01-15T10:00:00Z",
  "components": {
    "network_macs": ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"],
    "cpu_id": "BFEBFBFF000906EA",
    "disk_serials": ["WD-WX1234567890", "SAMSUNG-ABC123"],
    "motherboard_serial": "MB-123456",
    "bios_serial": "BIOS-789",
    "windows_guid": "{12345678-1234-1234-1234-123456789012}",
    "ram_serials": [],
    "gpu_macs": []
  },
  "collection_method": {
    "wmi_available": true,
    "registry_available": true,
    "fallback_used": false
  },
  "validation": {
    "last_verified": "2025-01-15T10:00:00Z",
    "matches_server": true,
    "server_registered_at": "2025-01-15T00:00:00Z"
  }
}
```

### Tabela no Banco: `hardware_fingerprints` (SSM.db)

```sql
CREATE TABLE IF NOT EXISTS hardware_fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint_hash TEXT UNIQUE NOT NULL,
    components_json TEXT NOT NULL,  -- JSON dos componentes
    first_detected DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_verified DATETIME DEFAULT CURRENT_TIMESTAMP,
    verification_count INTEGER DEFAULT 0,
    is_valid BOOLEAN DEFAULT 1,
    server_registered_at DATETIME,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_fingerprint_hash 
ON hardware_fingerprints(fingerprint_hash);
```

---

## 🔄 Fluxo de Funcionamento

### 1. Coleta Inicial (Primeira Execução)

```
Aplicação inicia
   ↓
HardwareFingerprint.generate()
   ↓
Coleta todos os componentes disponíveis
   ↓
Gera hash SHA-256
   ↓
Salva em data/hardware_fingerprint.json
   ↓
Salva em SSM.db (tabela hardware_fingerprints)
   ↓
Pronto para enviar ao servidor
```

### 2. Verificação Periódica (A cada 4 horas)

```
Timer dispara (4h desde última validação)
   ↓
1. SSM GERA hash do hardware ATUAL (não usa armazenado!)
   HardwareFingerprint.generate()  # Sempre gerar na hora
   ↓
2. SSM COMPARA com hash armazenado (apenas detecção local)
   Compara hash atual vs hash armazenado
   ↓
   Se diferente:
      - Hardware mudou detectado localmente
      - Bloqueia funcionalidades IMEDIATAMENTE
      - Mostra tela de revalidação
      - NÃO consulta servidor (já bloqueado)
   ↓
   Se igual:
      - Continua para validação no servidor
   ↓
3. SSM ENVIA hash GERADO (não armazenado!) ao servidor
   POST /api/v1/validate
   {
     "hardware_fingerprint": "hash_gerado_agora",  // ← SEMPRE GERADO NA HORA
     "license_key": "SSM-XXXX-XXXX-XXXX",
     "timestamp": "2025-01-15T10:00:00Z"
   }
   ↓
4. Servidor valida e retorna:
   - Se válido: { "valid": true, "expires_at": "..." }
   - Se inválido: { "valid": false, "reason": "hardware_mismatch" }
   ↓
5. SSM processa resposta:
   - Se válido: continua funcionando, atualiza cache
   - Se inválido: BLOQUEIA tudo, mostra tela de revalidação
   ↓
6. SSM ATUALIZA hash armazenado (apenas para próxima comparação)
   Salva hash gerado como "último hash conhecido"
```

**⚠️ IMPORTANTE: Segurança**
- ✅ **SEMPRE gerar hash antes de consultar servidor** (não usar armazenado)
- ✅ Hash armazenado serve apenas para **comparação local rápida**
- ✅ Servidor sempre recebe hash **gerado na hora** (impossível falsificar)

### 3. Envio ao Servidor (Registro/Validação)

```
POST /api/v1/register ou /api/v1/validate
   ↓
1. SSM GERA hash do hardware ATUAL (não usa armazenado!)
   current_hash = HardwareFingerprint.generate()  # Sempre gerar na hora
   ↓
2. SSM ENVIA hash GERADO ao servidor
   Body:
   {
     "hardware_fingerprint": "hash_gerado_agora",  // ← SEMPRE GERADO NA HORA
     "license_key": "SSM-XXXX-XXXX-XXXX",
     "timestamp": "2025-01-15T10:00:00Z",
     "components": { ... }  // opcional, apenas para debug
   }
   ↓
3. Servidor valida e responde
   - Valida hash corresponde ao cadastrado
   - Valida licença não expirou
   - Valida hardware não está em uso em outra máquina
   ↓
4. Aplicação processa resposta:
   - Se válido: salva resultado, atualiza hash armazenado
   - Se inválido: bloqueia funcionalidades, mostra erro
```

**🔒 Segurança:**
- Hash armazenado **NUNCA** é enviado ao servidor
- Servidor sempre recebe hash **gerado na hora**
- Impossível falsificar (hash sempre reflete hardware atual)

---

## 🛡️ Tratamento de Erros

### Cenários de Falha

1. **WMI não disponível**
   - Fallback: PowerShell commands
   - Fallback: Registry direto
   - Fallback: psutil (limitado)

2. **Componente não encontrado**
   - Usar fallback se disponível
   - Continuar com outros componentes
   - Erro apenas se não conseguir mínimo (4 componentes)

3. **Mudança de hardware detectada**
   - Bloquear funcionalidades
   - Mostrar tela de revalidação
   - Manter hash antigo para revalidação

4. **Servidor inacessível**
   - Usar cache local (se válido)
   - Tentar novamente em 30 minutos
   - Bloquear após 4 horas sem validação

---

## 🔍 Detecção de Mudanças

### Comparação de Fingerprints

```python
def detect_hardware_change() -> Tuple[bool, str, str]:
    """
    Detecta se hardware mudou.
    
    Returns:
        (changed: bool, current_hash: str, stored_hash: str)
    """
    # SEMPRE gerar hash atual (não usar armazenado!)
    current_hash = generate_fingerprint()  # Gerar na hora
    
    # Carregar hash armazenado (apenas para comparação)
    stored_hash = load_stored_hash()
    
    # Comparar
    changed = current_hash != stored_hash
    
    return changed, current_hash, stored_hash

def get_changed_components(current: Dict, stored: Dict) -> List[str]:
    """Retorna lista de componentes que mudaram"""
    changed = []
    
    if current.get('network_macs') != stored.get('network_macs'):
        changed.append('network_macs')
    if current.get('cpu_id') != stored.get('cpu_id'):
        changed.append('cpu_id')  # Crítico!
    if current.get('disk_serials') != stored.get('disk_serials'):
        changed.append('disk_serials')
    # ... outros componentes
    
    return changed
```

### Regras de Mudança

- **CPU ID mudou**: Bloqueio imediato (nunca deve mudar)
- **Windows GUID mudou**: Bloqueio imediato (nunca deve mudar)
- **MAC mudou**: Pode ser legítimo (nova placa), requer revalidação
- **Disco mudou**: Pode ser legítimo (novo HD), requer revalidação

### ⚠️ IMPORTANTE: Uso do Hash Armazenado

**Hash armazenado serve APENAS para:**
- ✅ Comparação local rápida (detecção imediata de mudanças)
- ✅ Histórico e logs
- ✅ Melhorar UX (resposta imediata)

**Hash armazenado NUNCA serve para:**
- ❌ Enviar ao servidor (sempre gerar novo)
- ❌ Validação final (servidor decide)
- ❌ Bypass de segurança (impossível)

**Sempre gerar hash antes de consultar servidor!**

---

## 🔌 Integração com Servidor de Licenciamento

### ⚠️ Importante: SSM é Cliente, não Servidor

O SSM Backend **NÃO cria endpoints próprios** para licenciamento. Ele é apenas um **CLIENTE** que consome os endpoints fornecidos pelo servidor de gerenciamento de licenças.

### Endpoints do Servidor (fornecidos pelo dev do servidor)

O desenvolvedor do servidor de licenciamento fornecerá os endpoints. Exemplos esperados:

1. **POST /api/v1/register** (Registro inicial)
   - SSM envia: hardware_fingerprint + dados do usuário
   - Servidor retorna: sucesso/erro

2. **POST /api/v1/validate** (Validação periódica)
   - SSM envia: license_key + hardware_fingerprint + timestamp
   - Servidor retorna: valid/invalid + dados da licença

3. **POST /api/v1/revalidate/request-code** (Solicitar código)
   - SSM envia: email + old_fingerprint
   - Servidor retorna: código enviado por email

4. **POST /api/v1/revalidate** (Revalidar com código)
   - SSM envia: email + old_fingerprint + new_fingerprint + code
   - Servidor retorna: sucesso/erro

### Responsabilidades do SSM

✅ **Fazer:**
- Coletar hardware e gerar hash
- Fazer requisições HTTP aos endpoints do servidor
- Processar respostas do servidor
- Validar periodicamente (a cada 4h)
- Detectar mudanças de hardware
- Bloquear funcionalidades se não licenciado

❌ **NÃO fazer:**
- Criar endpoints próprios de licenciamento
- Gerenciar licenças localmente (apenas validar)
- Armazenar lógica de negócio de licenças

---

## ⚙️ Configuração

### Adicionar ao `config.json`

```json
{
  "licensing": {
    "enabled": true,
    "server_url": "https://api.ssm-backend.com/v1",
    "validation_interval_seconds": 14400,  // 4 horas
    "hardware_check_interval_seconds": 3600,  // Verificar hardware a cada 1h
    "cache_ttl_seconds": 14400,  // Cache válido por 4h
    "require_internet": true,
    "block_on_invalid": true,
    "allow_hardware_changes": false,  // Requer revalidação
    "min_components_required": 4
  }
}
```

---

## 📊 Métodos de Coleta Detalhados

### 1. MAC Addresses (Rede)

**Método Principal: WMI**
```python
import wmi

c = wmi.WMI()
adapters = c.Win32_NetworkAdapter(
    PhysicalAdapter=True,
    MACAddress__ne=None
)

macs = []
for adapter in adapters:
    if adapter.MACAddress and adapter.MACAddress != "00:00:00:00:00:00":
        # Filtrar adaptadores virtuais
        if not any(virtual in adapter.Name.lower() 
                  for virtual in ['vmware', 'virtualbox', 'hyper-v', 'loopback']):
            macs.append(adapter.MACAddress)
```

**Método Fallback: PowerShell**
```python
import subprocess

result = subprocess.run(
    ['powershell', '-Command', 
     'Get-NetAdapter | Where-Object {$_.PhysicalMediaType -ne "Unspecified"} | Select-Object -ExpandProperty MacAddress'],
    capture_output=True,
    text=True
)
```

### 2. CPU ID

**Método: WMI**
```python
c = wmi.WMI()
processors = c.Win32_Processor()
cpu_id = processors[0].ProcessorId if processors else None
```

### 3. Disk Serial

**Método: WMI**
```python
c = wmi.WMI()
disks = c.Win32_DiskDrive()
serials = [disk.SerialNumber.strip() for disk in disks if disk.SerialNumber]
```

**Método Fallback: Volume Serial**
```python
import win32api

volumes = win32api.GetLogicalDriveStrings().split('\x00')
serials = []
for vol in volumes:
    if vol:
        try:
            vol_info = win32api.GetVolumeInformation(vol)
            serials.append(str(vol_info[1]))  # Serial number
        except:
            pass
```

### 4. Motherboard Serial

**Método: WMI**
```python
c = wmi.WMI()
boards = c.Win32_BaseBoard()
serial = boards[0].SerialNumber if boards and boards[0].SerialNumber else None
```

### 5. Windows Machine GUID

**Método: Registry**
```python
import winreg

key = winreg.OpenKey(
    winreg.HKEY_LOCAL_MACHINE,
    r"SOFTWARE\Microsoft\Cryptography"
)
guid = winreg.QueryValueEx(key, "MachineGuid")[0]
winreg.CloseKey(key)
```

---

## 🧪 Testes Necessários

### Testes Unitários

1. **Coleta de componentes**
   - Testar cada método de coleta
   - Testar fallbacks
   - Testar tratamento de erros

2. **Geração de hash**
   - Testar determinismo (mesma máquina = mesmo hash)
   - Testar normalização (case, espaços)
   - Testar ordenação

3. **Detecção de mudanças**
   - Testar comparação de hashes
   - Testar identificação de componentes mudados

### Testes de Integração

1. **Fluxo completo**
   - Coleta → Hash → Armazenamento → Envio ao servidor

2. **Mudança de hardware**
   - Simular mudança → Detectar → Bloquear → Revalidar

---

## 📝 Próximos Passos (Implementação no SSM)

### Fase 1: Coleta e Hash (SSM)
1. ✅ **Criar estrutura de módulos** (`core/licensing/`)
2. ✅ **Implementar HardwareFingerprint** (coleta + hash)
3. ✅ **Implementar armazenamento local** (JSON + DB)
4. ✅ **Implementar detecção de mudanças**

### Fase 2: Cliente HTTP (SSM)
5. ✅ **Criar LicenseValidatorClient** (cliente HTTP)
   - Métodos para chamar endpoints do servidor
   - Tratamento de erros e retry
   - Cache local de validações

### Fase 3: Integração (SSM)
6. ✅ **Integrar com LicenseValidator existente**
7. ✅ **Implementar validação periódica** (timer 4h)
8. ✅ **Implementar fluxo de revalidação** (quando hardware muda)

### Fase 4: Servidor (Outro projeto)
9. ⏳ **Servidor de licenciamento** (será criado separadamente)
   - Endpoints fornecidos pelo dev do servidor
   - SSM consome esses endpoints

---

## ⚠️ Considerações Importantes

### Segurança

- **SEMPRE gerar hash antes de consultar servidor** (não usar armazenado)
- **Hash armazenado apenas para comparação local** (nunca enviar ao servidor)
- **Servidor sempre recebe hash gerado na hora** (impossível falsificar)
- **Não expor componentes brutos** em logs (apenas hash)
- **Criptografar arquivo local** (opcional, mas recomendado)
- **Validar resposta do servidor** (não confiar cegamente)

### Estratégia de Segurança em Camadas

1. **Camada 1: Detecção Local (Rápida)**
   - Comparar hash atual vs armazenado
   - Bloquear localmente se diferente
   - Resposta imediata ao usuário

2. **Camada 2: Validação no Servidor (Definitiva)**
   - Sempre enviar hash gerado na hora
   - Servidor valida e decide
   - Impossível falsificar

**Resultado:** Máxima segurança + boa UX

### Performance

- **Cache do fingerprint** (não recolher toda hora)
- **Coleta assíncrona** (não bloquear inicialização)
- **Timeout nas requisições** (não travar se servidor lento)

### Compatibilidade

- **Funcionar sem WMI** (fallbacks)
- **Funcionar em diferentes versões do Windows**
- **Funcionar em VMs** (detectar mas não bloquear)

---

**Este é o plano completo. Podemos começar a implementação quando você autorizar!**

