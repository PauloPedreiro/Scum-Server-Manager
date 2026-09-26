# 🔄 Proposta: Sistema Dinâmico para ServerSettings.ini

## 🎯 Problema

O arquivo `ServerSettings.ini` pode receber:
1. **Novos campos da desenvolvedora** em atualizações do jogo
2. **Campos de mods** que podem variar entre servidores
3. **Campos customizados** adicionados manualmente

Precisamos de uma solução que:
- ✅ Aceite campos desconhecidos sem quebrar
- ✅ Preserve campos desconhecidos ao salvar
- ✅ Permita validação apenas para campos conhecidos
- ✅ Seja extensível para novos campos
- ✅ Mantenha compatibilidade com versões antigas

---

## 💡 Solução Proposta

### **1. Sistema de Schema Flexível**

Criar um sistema de schema que:
- Define campos conhecidos com validação
- Permite campos desconhecidos (mods/customizados)
- Preserva campos desconhecidos ao salvar
- Permite extensão via configuração

### **2. Estrutura de Schema**

```python
# core/server_settings/schema.py

# Schema base com campos conhecidos
KNOWN_FIELDS = {
    'General': {
        'scum.ServerName': {
            'type': 'string',
            'required': False,
            'default': 'SCUM Server',
            'description': 'Nome do servidor'
        },
        'scum.MaxPlayers': {
            'type': 'integer',
            'required': False,
            'default': 64,
            'min': 1,
            'max': 200,
            'description': 'Máximo de jogadores'
        },
        # ... outros campos conhecidos
    },
    'World': {
        # ... campos conhecidos
    },
    # ... outras seções
}

# Campos de mods conhecidos (opcional)
MOD_FIELDS = {
    'General': {
        'mod.CustomSetting': {
            'type': 'string',
            'description': 'Configuração de mod'
        }
    }
}

# Campos customizados do usuário (armazenados separadamente)
CUSTOM_FIELDS_FILE = 'data/server_settings_custom_fields.json'
```

### **3. Classe ServerSettingsManager com Suporte Dinâmico**

```python
class ServerSettingsManager:
    def __init__(self, config_directory: str):
        self.config_directory = Path(config_directory)
        self.settings_file = self.config_directory / 'ServerSettings.ini'
        self.parser = configparser.ConfigParser()
        self.parser.optionxform = str  # Preservar case das chaves
        
        # Carregar schema conhecido
        self.known_fields = KNOWN_FIELDS
        self.mod_fields = MOD_FIELDS
        
        # Carregar campos customizados do usuário
        self.custom_fields = self._load_custom_fields()
    
    def _load_custom_fields(self) -> Dict[str, Dict[str, Any]]:
        """Carregar campos customizados do usuário"""
        custom_file = Path('data/server_settings_custom_fields.json')
        if custom_file.exists():
            with open(custom_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_custom_fields(self):
        """Salvar campos customizados do usuário"""
        custom_file = Path('data/server_settings_custom_fields.json')
        with open(custom_file, 'w', encoding='utf-8') as f:
            json.dump(self.custom_fields, f, indent=2, ensure_ascii=False)
    
    def load_settings(self, include_unknown: bool = True) -> Dict[str, Any]:
        """
        Carregar todas as configurações
        
        Args:
            include_unknown: Incluir campos desconhecidos (mods/customizados)
        """
        self.parser.read(self.settings_file, encoding='utf-8')
        
        result = {}
        for section_name in self.parser.sections():
            section_data = {}
            
            for key, value in self.parser.items(section_name):
                # Verificar se é campo conhecido
                if self._is_known_field(section_name, key):
                    section_data[key] = self._parse_value(section_name, key, value)
                elif include_unknown:
                    # Campo desconhecido - preservar como string
                    section_data[key] = value
                    # Registrar como campo customizado se não estiver no schema
                    if not self._is_mod_field(section_name, key):
                        self._register_custom_field(section_name, key, value)
            
            result[section_name] = section_data
        
        return result
    
    def _is_known_field(self, section: str, key: str) -> bool:
        """Verificar se campo é conhecido"""
        return (
            section in self.known_fields and 
            key in self.known_fields[section]
        ) or (
            section in self.mod_fields and 
            key in self.mod_fields[section]
        )
    
    def _is_mod_field(self, section: str, key: str) -> bool:
        """Verificar se campo é de mod"""
        return (
            section in self.mod_fields and 
            key in self.mod_fields[section]
        )
    
    def _register_custom_field(self, section: str, key: str, value: str):
        """Registrar campo customizado"""
        if section not in self.custom_fields:
            self.custom_fields[section] = {}
        
        if key not in self.custom_fields[section]:
            # Tentar inferir tipo
            field_info = {
                'type': self._infer_type(value),
                'value': value,
                'first_seen': datetime.now().isoformat()
            }
            self.custom_fields[section][key] = field_info
            self._save_custom_fields()
    
    def _infer_type(self, value: str) -> str:
        """Inferir tipo do valor"""
        # Tentar converter para número
        try:
            int(value)
            return 'integer'
        except ValueError:
            try:
                float(value)
                return 'float'
            except ValueError:
                # Verificar se é boolean
                if value in ('0', '1'):
                    return 'boolean'
                # Verificar se é tempo
                if ':' in value and len(value.split(':')) in (2, 3):
                    return 'time'
                # Verificar se é moeda
                if value.endswith('g'):
                    return 'currency'
                return 'string'
    
    def set_value(self, section: str, key: str, value: Any, validate: bool = True) -> Dict[str, Any]:
        """
        Definir valor de configuração
        
        Args:
            section: Seção do INI
            key: Chave da configuração
            value: Valor a definir
            validate: Validar valor se campo é conhecido
        
        Returns:
            Resultado da operação
        """
        # Carregar arquivo atual
        self.parser.read(self.settings_file, encoding='utf-8')
        
        # Criar seção se não existir
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        
        # Validar se campo é conhecido
        if validate and self._is_known_field(section, key):
            validation_result = self._validate_value(section, key, value)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'field': key,
                    'section': section
                }
            # Converter valor para formato correto
            value = self._format_value(section, key, value)
        else:
            # Campo desconhecido - converter para string
            value = str(value)
            # Registrar como customizado se necessário
            if not self._is_mod_field(section, key):
                self._register_custom_field(section, key, value)
        
        # Definir valor
        self.parser.set(section, key, str(value))
        
        # Salvar arquivo
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                self.parser.write(f)
            
            return {
                'success': True,
                'message': f'Configuração {key} atualizada com sucesso',
                'section': section,
                'key': key,
                'value': value,
                'is_known_field': self._is_known_field(section, key),
                'requires_restart': self._requires_restart(section, key)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro ao salvar: {str(e)}'
            }
    
    def _validate_value(self, section: str, key: str, value: Any) -> Dict[str, Any]:
        """Validar valor de campo conhecido"""
        field_schema = self.known_fields.get(section, {}).get(key)
        if not field_schema:
            field_schema = self.mod_fields.get(section, {}).get(key)
        
        if not field_schema:
            return {'valid': True}  # Campo desconhecido - não validar
        
        field_type = field_schema.get('type')
        
        # Validar tipo
        if field_type == 'integer':
            try:
                int_value = int(value)
                if 'min' in field_schema and int_value < field_schema['min']:
                    return {'valid': False, 'error': f'Valor mínimo: {field_schema["min"]}'}
                if 'max' in field_schema and int_value > field_schema['max']:
                    return {'valid': False, 'error': f'Valor máximo: {field_schema["max"]}'}
            except ValueError:
                return {'valid': False, 'error': 'Valor deve ser um número inteiro'}
        
        elif field_type == 'float':
            try:
                float_value = float(value)
                if 'min' in field_schema and float_value < field_schema['min']:
                    return {'valid': False, 'error': f'Valor mínimo: {field_schema["min"]}'}
                if 'max' in field_schema and float_value > field_schema['max']:
                    return {'valid': False, 'error': f'Valor máximo: {field_schema["max"]}'}
            except ValueError:
                return {'valid': False, 'error': 'Valor deve ser um número decimal'}
        
        elif field_type == 'boolean':
            if str(value) not in ('0', '1', 'true', 'false', 'True', 'False'):
                return {'valid': False, 'error': 'Valor deve ser 0, 1, true ou false'}
        
        elif field_type == 'time':
            # Validar formato HH:MM:SS ou HH:MM
            if not re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', str(value)):
                return {'valid': False, 'error': 'Formato inválido. Use HH:MM:SS ou HH:MM'}
        
        elif field_type == 'currency':
            # Validar formato {number}g
            if not re.match(r'^\d+g$', str(value)):
                return {'valid': False, 'error': 'Formato inválido. Use {número}g (ex: 1g, 10g)'}
        
        # Validar valores permitidos se especificado
        if 'allowed_values' in field_schema:
            if str(value) not in [str(v) for v in field_schema['allowed_values']]:
                return {
                    'valid': False,
                    'error': f'Valores permitidos: {", ".join(map(str, field_schema["allowed_values"]))}'
                }
        
        return {'valid': True}
    
    def _format_value(self, section: str, key: str, value: Any) -> str:
        """Formatar valor para salvar no INI"""
        field_schema = self.known_fields.get(section, {}).get(key)
        if not field_schema:
            field_schema = self.mod_fields.get(section, {}).get(key)
        
        if not field_schema:
            return str(value)  # Campo desconhecido - manter como string
        
        field_type = field_schema.get('type')
        
        if field_type == 'boolean':
            # Converter para 0 ou 1
            if str(value).lower() in ('true', '1', 'yes', 'on'):
                return '1'
            return '0'
        
        if field_type == 'float':
            # Manter precisão decimal
            return f'{float(value):.6f}'
        
        return str(value)
    
    def _parse_value(self, section: str, key: str, value: str) -> Any:
        """Parsear valor do INI para tipo Python"""
        field_schema = self.known_fields.get(section, {}).get(key)
        if not field_schema:
            field_schema = self.mod_fields.get(section, {}).get(key)
        
        if not field_schema:
            return value  # Campo desconhecido - retornar como string
        
        field_type = field_schema.get('type')
        
        if field_type == 'integer':
            try:
                return int(value)
            except ValueError:
                return value
        
        if field_type == 'float':
            try:
                return float(value)
            except ValueError:
                return value
        
        if field_type == 'boolean':
            return value in ('1', 'true', 'True')
        
        return value
    
    def _requires_restart(self, section: str, key: str) -> bool:
        """Verificar se campo requer restart do servidor"""
        field_schema = self.known_fields.get(section, {}).get(key)
        if not field_schema:
            field_schema = self.mod_fields.get(section, {}).get(key)
        
        if not field_schema:
            return True  # Campos desconhecidos assumem que requerem restart
        
        return field_schema.get('requires_restart', True)
    
    def get_unknown_fields(self) -> Dict[str, List[str]]:
        """Obter lista de campos desconhecidos (mods/customizados)"""
        self.parser.read(self.settings_file, encoding='utf-8')
        
        unknown = {}
        for section_name in self.parser.sections():
            unknown_in_section = []
            for key in self.parser.options(section_name):
                if not self._is_known_field(section_name, key):
                    unknown_in_section.append(key)
            if unknown_in_section:
                unknown[section_name] = unknown_in_section
        
        return unknown
    
    def register_mod_field(self, section: str, key: str, field_info: Dict[str, Any]):
        """Registrar campo de mod no schema"""
        if section not in self.mod_fields:
            self.mod_fields[section] = {}
        
        self.mod_fields[section][key] = field_info
        
        # Salvar em arquivo de mods
        mod_fields_file = Path('data/server_settings_mod_fields.json')
        with open(mod_fields_file, 'w', encoding='utf-8') as f:
            json.dump(self.mod_fields, f, indent=2, ensure_ascii=False)
```

---

## 📁 Estrutura de Arquivos

```
data/
├── server_settings_custom_fields.json  # Campos customizados descobertos
├── server_settings_mod_fields.json     # Campos de mods registrados
└── server_settings_schema.json         # Schema completo (opcional, para backup)

core/server_settings/
├── __init__.py
├── manager.py          # ServerSettingsManager
├── schema.py           # Schema de campos conhecidos
└── validators.py       # Validadores customizados
```

---

## 🔄 Fluxo de Trabalho

### **1. Descoberta Automática de Novos Campos**

Quando o sistema encontra um campo desconhecido:
1. Registra no `server_settings_custom_fields.json`
2. Tenta inferir o tipo
3. Preserva o valor original
4. Permite edição sem validação rígida

### **2. Registro Manual de Campos de Mods**

Administrador pode registrar campos de mods:

```python
# Via API
POST /api/server/settings/register-mod-field
{
  "section": "General",
  "key": "mod.CustomModSetting",
  "type": "integer",
  "min": 0,
  "max": 100,
  "description": "Configuração do mod CustomMod"
}
```

### **3. Atualização de Schema**

Quando a desenvolvedora adiciona novos campos:
1. Atualizar `schema.py` com novos campos
2. Sistema automaticamente valida novos campos
3. Campos antigos continuam funcionando

---

## 📡 Endpoints Propostos

### **1. Obter Campos Desconhecidos**

```
GET /api/server/settings/unknown-fields
```

**Resposta**:
```json
{
  "success": true,
  "data": {
    "General": [
      "mod.CustomModSetting",
      "custom.UserSetting"
    ],
    "World": [
      "mod.WorldModSetting"
    ]
  }
}
```

### **2. Registrar Campo de Mod**

```
POST /api/server/settings/register-mod-field
```

**Body**:
```json
{
  "section": "General",
  "key": "mod.CustomModSetting",
  "type": "integer",
  "min": 0,
  "max": 100,
  "description": "Configuração do mod",
  "requires_restart": true
}
```

### **3. Obter Schema Completo**

```
GET /api/server/settings/schema
```

**Resposta**:
```json
{
  "success": true,
  "data": {
    "known_fields": {
      "General": {
        "scum.MaxPlayers": {
          "type": "integer",
          "min": 1,
          "max": 200,
          "description": "Máximo de jogadores"
        }
      }
    },
    "mod_fields": {
      "General": {
        "mod.CustomModSetting": {
          "type": "integer",
          "description": "Configuração do mod"
        }
      }
    },
    "custom_fields": {
      "General": {
        "custom.UserSetting": {
          "type": "string",
          "first_seen": "2025-12-02T19:00:00"
        }
      }
    }
  }
}
```

### **4. Atualizar Campo (com ou sem validação)**

```
PATCH /api/server/settings
```

**Body**:
```json
{
  "section": "General",
  "key": "mod.CustomModSetting",  // Campo de mod
  "value": 50,
  "validate": false  // Opcional: false para campos desconhecidos
}
```

---

## 🛡️ Estratégias de Compatibilidade

### **1. Preservação de Campos Desconhecidos**

- Sempre preservar campos desconhecidos ao salvar
- Nunca remover campos que não estão no schema
- Manter ordem original quando possível

### **2. Validação Opcional**

- Validar apenas campos conhecidos
- Campos desconhecidos podem ser editados livremente
- Avisar usuário sobre campos desconhecidos

### **3. Versionamento de Schema**

```python
SCHEMA_VERSION = "1.0.0"

KNOWN_FIELDS_V1 = {
    # Campos da versão 1
}

KNOWN_FIELDS_V2 = {
    # Campos da versão 2 (inclui V1 + novos)
}
```

### **4. Migração Automática**

```python
def migrate_schema(old_version: str, new_version: str):
    """Migrar schema de versão antiga para nova"""
    # Mapear campos antigos para novos
    # Converter valores se necessário
    # Preservar campos customizados
```

---

## 📋 Checklist de Implementação

- [ ] Criar estrutura de schema flexível
- [ ] Implementar descoberta automática de campos
- [ ] Implementar preservação de campos desconhecidos
- [ ] Criar sistema de registro de mods
- [ ] Implementar validação opcional
- [ ] Criar endpoints para campos desconhecidos
- [ ] Criar endpoint para registrar mods
- [ ] Implementar versionamento de schema
- [ ] Criar documentação de extensibilidade
- [ ] Testar com campos desconhecidos
- [ ] Testar com mods

---

## ✅ Benefícios

1. **Flexibilidade**: Aceita qualquer campo, conhecido ou não
2. **Extensibilidade**: Fácil adicionar novos campos ao schema
3. **Compatibilidade**: Não quebra com atualizações do jogo
4. **Preservação**: Nunca perde dados de campos desconhecidos
5. **Descoberta**: Identifica automaticamente novos campos
6. **Documentação**: Mantém registro de campos customizados

---

**Última atualização**: 02/12/2025

