# 📋 Planejamento: Unificação de Mapeamento de Veículos

## 🎯 Objetivo

Unificar o sistema de mapeamento de imagens de veículos, criando uma nova pasta dedicada `data/imagens/vehicle/` (seguindo o padrão do `Weapons/`) onde ficará o JSON de mapeamento e as imagens. Ambos os sistemas (`vehicle_registration` e `vehicle-log`) usarão esta pasta compartilhada, com auto-descoberta de novos veículos (adicionados ao JSON com valor vazio para preenchimento manual, igual ao kill_log).

---

## 📊 Situação Atual

### **Vehicle Registration** (`vehicle_processor.py`)
- ✅ **Pasta**: `data/imagens/carros/`
- ✅ **Mapping**: `data/imagens/carros/mapping.json`
- ✅ **Imagens**: `BPC_*.png`, `BP_*.png`, etc.
- ✅ **Normalização**: Básica (lowercase, replace espaços/hífens)
- ✅ **Auto-descoberta**: Implementada
- ✅ **Thread-safety**: Implementada
- ✅ **Ordenação**: Alfabética ao salvar

### **Vehicle Log** (`vehicle_destruction_processor.py`)
- ❌ **Pasta**: `data/imagens/carros/vehicle-log/` (separada)
- ❌ **Mapping**: `data/imagens/carros/vehicle-log/mapping.json` (separado)
- ❌ **Imagens**: `*_ES.png` (duplicadas)
- ❌ **Normalização**: Muito básica (só remove `_ES`)
- ❌ **Auto-descoberta**: Não implementada
- ❌ **Thread-safety**: Não implementada
- ❌ **Ordenação**: Não ordena

### **Referência: Kill Log** (`kill_processor.py`)
- ✅ **Pasta**: `data/imagens/Weapons/`
- ✅ **Mapping**: `data/imagens/Weapons/mapping.json`
- ✅ **Estrutura**: Pasta dedicada com imagens e JSON
- ✅ **Fluxo**: Auto-descoberta → adiciona com valor vazio → usuário preenche manualmente

---

## 🎯 Situação Desejada

### **Ambos os Sistemas (Vehicle Registration + Vehicle Log)**
- ✅ **Pasta**: `data/imagens/vehicle/` (NOVA - dedicada, como `Weapons/`)
- ✅ **Mapping**: `data/imagens/vehicle/mapping.json` (compartilhado)
- ✅ **Imagens**: Todas as imagens de veículos centralizadas
- ✅ **Normalização**: Robusta (igual ao padrão kill_log)
- ✅ **Auto-descoberta**: Implementada (adiciona com valor vazio)
- ✅ **Thread-safety**: Implementada
- ✅ **Ordenação**: Alfabética ao salvar
- ✅ **Fluxo**: Igual ao kill_log (auto-descoberta → valor vazio → preenchimento manual)

---

## 📝 Fases de Implementação

### **FASE 1: Preparação e Análise** ⏱️ ~20 min

#### 1.1 Criar Nova Estrutura de Pastas
- [ ] Criar pasta `data/imagens/vehicle/`
- [ ] Verificar estrutura similar ao `Weapons/`

#### 1.2 Verificar Compatibilidade de Dados
- [ ] Comparar `data/imagens/carros/mapping.json` com `data/imagens/carros/vehicle-log/mapping.json`
- [ ] Identificar veículos que existem apenas em um dos mappings
- [ ] Listar todas as imagens de veículos existentes:
  - `data/imagens/carros/*.png`
  - `data/imagens/carros/vehicle-log/*.png`
- [ ] Verificar se há imagens duplicadas com nomes diferentes
- [ ] Documentar diferenças encontradas

**Arquivos a verificar:**
- `data/imagens/carros/mapping.json`
- `data/imagens/carros/vehicle-log/mapping.json`
- `data/imagens/carros/*.png` (imagens de veículos)
- `data/imagens/carros/vehicle-log/*.png`

**Resultado esperado:**
- Lista de veículos únicos em cada mapping
- Lista de imagens a serem migradas
- Plano de migração de dados

---

### **FASE 2: Migrar Dados e Criar Nova Estrutura** ⏱️ ~30 min

#### 2.1 Migrar Imagens para Nova Pasta
- [ ] Copiar todas as imagens de veículos para `data/imagens/vehicle/`
- [ ] Incluir imagens de `data/imagens/carros/*.png` (veículos)
- [ ] Incluir imagens de `data/imagens/carros/vehicle-log/*.png`
- [ ] Remover duplicatas (manter apenas uma versão de cada imagem)
- [ ] Verificar se todas as imagens foram copiadas

#### 2.2 Criar e Migrar Mapping JSON
- [ ] Criar `data/imagens/vehicle/mapping.json`
- [ ] Unificar dados de ambos os mappings existentes:
  - `data/imagens/carros/mapping.json`
  - `data/imagens/carros/vehicle-log/mapping.json`
- [ ] Normalizar todas as chaves usando normalização robusta
- [ ] Verificar se imagens referenciadas existem na nova pasta
- [ ] Ordenar alfabeticamente
- [ ] Fazer backup dos mappings antigos

#### 2.3 Criar Método de Normalização Robusta
**Arquivo**: `core/logs/vehicle_processor.py`

**Mudanças:**
- [ ] Criar método `_normalize_vehicle_name()` robusto (padrão kill_log)
- [ ] Remover prefixos: `BPC_`, `BP_`, `bpc_`, `bp_`
- [ ] Remover sufixos: `_ES`, `_C`, IDs numéricos (`_12345`)
- [ ] Normalizar formato: lowercase, substituir espaços/hífens por underscore
- [ ] Manter compatibilidade com normalização atual

**Código exemplo:**
```python
def _normalize_vehicle_name(self, vehicle_name: str) -> str:
    """Normalizar nome do veículo (padrão kill_log)"""
    if not vehicle_name:
        return vehicle_name
    
    # Remover prefixos comuns
    normalized = vehicle_name
    for prefix in ['BPC_', 'BP_', 'bpc_', 'bp_']:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    
    # Remover sufixos (_ES, _C, IDs numéricos)
    normalized = re.sub(r'_ES(_\d+)?$', '', normalized)
    normalized = re.sub(r'_C(_\d+)?$', '', normalized)
    normalized = re.sub(r'_\d+$', '', normalized)  # IDs numéricos
    
    # Normalizar formato (lowercase, substituir espaços/hífens)
    normalized = normalized.lower().strip()
    normalized = normalized.replace(' ', '_').replace('-', '_')
    
    return normalized
```

#### 2.4 Atualizar Caminhos no Vehicle Processor
**Arquivo**: `core/logs/vehicle_processor.py`

**Mudanças:**
- [ ] Alterar `self.images_path` de `"data/imagens/carros"` para `"data/imagens/vehicle"`
- [ ] Alterar `self.mapping_path` para usar nova pasta
- [ ] Atualizar método `get_vehicle_image_mapping()` para usar `_normalize_vehicle_name()`
- [ ] Manter lógica de correspondência parcial
- [ ] Manter auto-descoberta

**Testes:**
- [ ] Testar normalização com vários formatos de nomes
- [ ] Verificar se mapeamentos existentes continuam funcionando
- [ ] Verificar se imagens são encontradas na nova pasta

---

### **FASE 3: Refatorar Vehicle Destruction Processor** ⏱️ ~1h

#### 3.1 Alterar Caminhos e Estrutura
**Arquivo**: `core/logs/vehicle_destruction_processor.py`

**Mudanças no `__init__`:**
- [ ] Alterar `self.images_path` de `"data/imagens/carros/vehicle-log"` para `"data/imagens/vehicle"`
- [ ] Alterar `self.mapping_file` para usar `os.path.join(self.images_path, "mapping.json")`
- [ ] Adicionar `import threading`
- [ ] Adicionar `self.mapping_lock = threading.Lock()`
- [ ] Remover `self._vehicle_mapping = None` (não será mais lazy)
- [ ] Carregar mapping no `__init__`: `self.vehicle_image_mapping = self._load_vehicle_mapping()`

**Código:**
```python
def __init__(self, webhooks_path: str = "data/webhooks.json"):
    self.webhooks_path = webhooks_path
    self.images_path = "data/imagens/vehicle"  # ✅ NOVA pasta dedicada
    self.mapping_file = os.path.join(self.images_path, "mapping.json")  # ✅ Alterado
    
    # Thread-safety
    self.mapping_lock = threading.Lock()  # ✅ Novo
    
    # Carregar mapping no init
    self.vehicle_image_mapping = self._load_vehicle_mapping()  # ✅ Novo
```

#### 3.2 Criar Método de Normalização Robusta
- [ ] Criar método `_normalize_vehicle_name()` (igual ao vehicle_registration)
- [ ] Usar mesma lógica de remoção de prefixos/sufixos

#### 3.3 Implementar Auto-descoberta
- [ ] Criar método `_add_vehicle_to_mapping()` (thread-safe)
- [ ] Adicionar veículo com valor vazio se não existir
- [ ] Log informativo quando novo veículo for descoberto

**Código:**
```python
def _add_vehicle_to_mapping(self, normalized_name: str) -> None:
    """Adicionar novo veículo ao mapeamento (thread-safe)"""
    if not normalized_name:
        return
    
    with self.mapping_lock:
        if normalized_name not in self.vehicle_image_mapping:
            self.vehicle_image_mapping[normalized_name] = ""
            self._save_vehicle_mapping(self.vehicle_image_mapping)
            logger.info(f"Novo veículo descoberto: {normalized_name}")
```

#### 3.4 Melhorar `_load_vehicle_mapping()`
- [ ] Criar arquivo vazio se não existir (igual ao vehicle_registration)
- [ ] Melhorar tratamento de erros
- [ ] Remover lazy loading (carregar no init)

**Código:**
```python
def _load_vehicle_mapping(self) -> Dict[str, str]:
    """Carregar mapeamento de veículos do arquivo JSON"""
    try:
        if os.path.exists(self.mapping_file):
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
                logger.info(f"Mapeamento carregado: {len(mapping)} veículos")
                return mapping
        else:
            # Criar arquivo vazio se não existir
            logger.info("Arquivo mapping.json não encontrado, criando novo")
            empty_mapping = {}
            self._save_vehicle_mapping(empty_mapping)
            return empty_mapping
    except Exception as e:
        logger.error(f"Erro ao carregar mapeamento: {e}")
        return {}
```

#### 3.5 Implementar Ordenação no `_save_vehicle_mapping()`
- [ ] Ordenar alfabeticamente antes de salvar
- [ ] Garantir thread-safety

**Código:**
```python
def _save_vehicle_mapping(self, mapping: Dict[str, str]) -> bool:
    """Salvar mapeamento ordenado alfabeticamente (thread-safe)"""
    try:
        # Ordenar alfabeticamente
        sorted_mapping = dict(sorted(mapping.items()))
        
        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(self.mapping_file), exist_ok=True)
        
        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            json.dump(sorted_mapping, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar mapeamento: {e}")
        return False
```

#### 3.6 Refatorar `_get_vehicle_image_mapping()`
- [ ] Usar normalização robusta
- [ ] Implementar auto-descoberta
- [ ] Verificar se arquivo existe antes de retornar
- [ ] Retornar apenas nome do arquivo (não caminho completo)

**Código:**
```python
def _get_vehicle_image_mapping(self, vehicle_name: str) -> Optional[str]:
    """Mapear nome do veículo para arquivo de imagem"""
    if not vehicle_name:
        return None
    
    # Normalizar nome
    normalized_name = self._normalize_vehicle_name(vehicle_name)
    
    # Buscar no mapping
    image_filename = self.vehicle_image_mapping.get(normalized_name)
    
    # Se não existe, adicionar (auto-descoberta)
    if image_filename is None:
        self._add_vehicle_to_mapping(normalized_name)
        return None
    
    # Se existe mas está vazio, retornar None
    if not image_filename or image_filename.strip() == "":
        return None
    
    # Verificar se arquivo existe
    image_path = os.path.join(self.images_path, image_filename)
    if os.path.exists(image_path):
        return image_filename
    
    logger.warning(f"Imagem mapeada não encontrada: {image_filename}")
    return None
```

#### 3.7 Atualizar `_format_discord_message()`
- [ ] Verificar se `_get_vehicle_image_mapping()` retorna apenas nome do arquivo
- [ ] Ajustar construção do caminho da imagem se necessário

#### 3.8 Atualizar `process_vehicle_destruction_log()`
- [ ] Verificar se caminho da imagem está correto
- [ ] Ajustar lógica de envio com imagem

---

### **FASE 4: Limpeza e Organização** ⏱️ ~15 min

#### 4.1 Fazer Backup das Pastas Antigas
- [ ] Fazer backup de `data/imagens/carros/mapping.json`
- [ ] Fazer backup de `data/imagens/carros/vehicle-log/`
- [ ] Criar pasta `data/imagens/carros.backup/` (opcional)

#### 4.2 Remover/Mover Pastas Antigas (Opcional)
- [ ] Decidir se mantém `data/imagens/carros/` para outros propósitos
- [ ] Se não for mais necessário, mover para backup
- [ ] Remover `data/imagens/carros/vehicle-log/` (dados já migrados)

#### 4.3 Verificar Referências
- [ ] Buscar por `carros` no código (pode haver outros usos)
- [ ] Buscar por `vehicle-log` no código
- [ ] Verificar se não há hardcoded paths
- [ ] Atualizar documentação se necessário

---

### **FASE 5: Testes e Validação** ⏱️ ~30 min

#### 5.1 Testes de Normalização
- [ ] Testar com veículos conhecidos:
  - `BPC_Laika_ES` → `laika`
  - `BP_WheelBarrow_Improvised` → `wheelbarrow_improvised`
  - `BPC_Dirtbike_C_12345` → `dirtbike`
  - `Kinglet_Duster` → `kinglet_duster`

#### 5.2 Testes de Auto-descoberta
- [ ] Criar veículo fictício não mapeado
- [ ] Verificar se é adicionado ao JSON com valor vazio
- [ ] Verificar se não duplica entradas

#### 5.3 Testes de Thread-safety
- [ ] Simular múltiplas threads acessando simultaneamente
- [ ] Verificar se não há race conditions
- [ ] Verificar se JSON não corrompe

#### 5.4 Testes de Integração
- [ ] Processar arquivo `vehicle_destruction_*.log` real
- [ ] Verificar se imagens são encontradas corretamente
- [ ] Verificar se notificações Discord funcionam
- [ ] Verificar se não quebra `vehicle_registration`

#### 5.5 Testes de Compatibilidade
- [ ] Verificar se mapeamentos existentes continuam funcionando
- [ ] Testar com veículos já mapeados
- [ ] Testar com veículos não mapeados

---

## 📁 Estrutura Final

### **Nova Estrutura (Igual ao Weapons/)**

```
data/imagens/
├── Weapons/                        # ✅ Referência (kill_log)
│   ├── mapping.json
│   ├── AK47.png
│   └── ...
│
└── vehicle/                         # ✅ NOVA pasta dedicada
    ├── mapping.json                 # ✅ ÚNICO mapping compartilhado
    ├── BPC_Laika.png                # ✅ Imagens centralizadas
    ├── BPC_Dirtbike.png
    ├── BPC_Tractor.png
    ├── BP_WheelBarrow_Improvised.png
    └── ... (outras imagens de veículos)

core/logs/
├── vehicle_processor.py             # ✅ Usa vehicle/mapping.json
└── vehicle_destruction_processor.py # ✅ Usa vehicle/mapping.json
```

### **Estrutura Antiga (Será Migrada/Removida)**

```
data/imagens/carros/                 # ⚠️ Será migrada/backup
├── mapping.json                     # → Migrar para vehicle/
├── BPC_*.png                        # → Migrar para vehicle/
└── vehicle-log/                      # ⚠️ Será removida
    ├── mapping.json                  # → Migrar para vehicle/
    └── *_ES.png                     # → Migrar para vehicle/
```

---

## ✅ Checklist Final

### **Código**
- [ ] `vehicle_processor.py` com normalização robusta
- [ ] `vehicle_destruction_processor.py` refatorado
- [ ] Ambos usando mesmo mapping e pasta
- [ ] Thread-safety implementada
- [ ] Auto-descoberta implementada
- [ ] Ordenação implementada

### **Dados**
- [ ] Mapping unificado
- [ ] Imagens centralizadas
- [ ] Pasta antiga removida/backup

### **Testes**
- [ ] Normalização testada
- [ ] Auto-descoberta testada
- [ ] Thread-safety testada
- [ ] Integração testada
- [ ] Compatibilidade testada

### **Documentação**
- [ ] Comentários no código atualizados
- [ ] Documentação atualizada (se houver)

---

## 🚨 Pontos de Atenção

1. **Thread-safety**: Ambos os processadores podem acessar o mesmo JSON simultaneamente
   - ✅ Solução: Usar locks separados (cada classe tem seu próprio lock)
   - ⚠️ Cuidado: Não bloquear por muito tempo

2. **Normalização**: Garantir que ambos normalizem da mesma forma
   - ✅ Solução: Usar mesma lógica de normalização
   - ⚠️ Cuidado: Manter compatibilidade com dados existentes

3. **Auto-descoberta**: Pode adicionar muitos veículos vazios
   - ✅ Solução: Log informativo para usuário preencher
   - ⚠️ Cuidado: Não poluir o JSON

4. **Migração**: Dados antigos podem ter formatos diferentes
   - ✅ Solução: Normalizar durante migração
   - ⚠️ Cuidado: Não perder dados

---

## 📊 Estimativa de Tempo Total

| Fase | Tempo Estimado |
|------|----------------|
| Fase 1: Preparação e Análise | ~20 min |
| Fase 2: Migrar Dados e Criar Nova Estrutura | ~30 min |
| Fase 3: Refatorar Vehicle Destruction Processor | ~1h |
| Fase 4: Limpeza e Organização | ~15 min |
| Fase 5: Testes e Validação | ~30 min |
| **TOTAL** | **~2h 35min** |

---

## 🎯 Benefícios Esperados

1. ✅ **Organização**: Pasta dedicada `vehicle/` igual ao `Weapons/`
2. ✅ **Consistência**: Mesma estrutura e padrão do kill_log
3. ✅ **Manutenção única**: Um único arquivo JSON para manter
4. ✅ **Auto-descoberta**: Novos veículos detectados automaticamente (valor vazio → preenchimento manual)
5. ✅ **Sem duplicação**: Imagens e mapeamentos centralizados
6. ✅ **Thread-safety**: Ambos os sistemas protegidos
7. ✅ **Simplicidade**: Estrutura clara e organizada
8. ✅ **Fluxo padronizado**: Igual ao kill_log (auto-descoberta → valor vazio → manual)

---

## 📝 Notas de Implementação

- Manter compatibilidade com dados existentes
- Fazer backup antes de qualquer mudança
- Testar em ambiente de desenvolvimento primeiro
- Documentar mudanças importantes
- Considerar rollback se necessário

---

---

## 🔄 Fluxo de Auto-descoberta (Igual ao Kill Log)

### **Quando um novo veículo é detectado:**

1. **Sistema detecta veículo não mapeado** (ex: `BPC_NovoVeiculo_ES`)
2. **Normaliza nome** → `novoveiculo`
3. **Adiciona ao JSON** com valor vazio:
   ```json
   {
     "novoveiculo": ""
   }
   ```
4. **Log informativo** para o usuário
5. **Usuário adiciona imagem manualmente**:
   - Coloca `NovoVeiculo.png` em `data/imagens/vehicle/`
   - Edita `mapping.json`:
     ```json
     {
       "novoveiculo": "NovoVeiculo.png"
     }
     ```
6. **Próxima detecção** usa a imagem automaticamente

---

**Data de Criação**: 2025-01-02  
**Última Atualização**: 2025-01-02 (Adicionada pasta `vehicle/` dedicada)  
**Status**: 📋 Planejamento Completo  
**Próximo Passo**: Aguardando aprovação para iniciar implementação

