# 🎯 Implementação Prática: Campos Dinâmicos no Frontend

## 📋 Cenário

Admin do servidor usa o frontend para:
1. Abrir seção `[General]`
2. Clicar em "Adicionar Campo Customizado"
3. Preencher: Nome do campo, Valor, Tipo
4. Salvar

O backend precisa:
- ✅ Aceitar o campo desconhecido
- ✅ Salvar no `ServerSettings.ini`
- ✅ Registrar para futuras referências
- ✅ Preservar ao recarregar

---

## 🔄 Fluxo Completo

### **1. Frontend: Adicionar Campo Customizado**

**Interface do Frontend:**
```
[General]
├── scum.ServerName: "SCUM Server" [Editar]
├── scum.MaxPlayers: 64 [Editar]
├── ... (campos conhecidos)
└── ➕ Adicionar Campo Customizado
```

**Ao clicar em "Adicionar Campo Customizado":**
```typescript
// Modal/Dialog aparece
{
  section: "General",
  key: "",        // Campo vazio para preencher
  value: "",      // Valor vazio
  type: "string"  // Tipo selecionado (string, integer, float, boolean, time)
}
```

**Exemplo de preenchimento:**
```
Nome do Campo: custom.MyCustomSetting
Valor: 100
Tipo: integer
```

---

## 📡 Requisição do Frontend

### **Opção 1: Adicionar Campo Individual**

```http
POST /api/server/settings/add-field
Content-Type: application/json

{
  "section": "General",
  "key": "custom.MyCustomSetting",
  "value": 100,
  "type": "integer",
  "description": "Minha configuração customizada" // Opcional
}
```

### **Opção 2: Atualizar Seção com Campo Novo**

```http
PATCH /api/server/settings
Content-Type: application/json

{
  "section": "General",
  "updates": {
    "scum.MaxPlayers": 100,  // Campo conhecido
    "custom.MyCustomSetting": 100  // Campo novo (não existe no schema)
  }
}
```

### **Opção 3: Salvar Seção Completa (Incluindo Novos Campos)**

```http
PUT /api/server/settings/General
Content-Type: application/json

{
  "scum.ServerName": "SCUM Server",
  "scum.MaxPlayers": 100,
  "custom.MyCustomSetting": 100,  // Campo novo
  "mod.ModSetting": "value"        // Outro campo novo
}
```

---

## 🔧 Processamento no Backend

### **Endpoint: POST /api/server/settings/add-field**

```python
@app.route('/api/server/settings/add-field', methods=['POST'])
def add_custom_field():
    """Adicionar campo customizado ao ServerSettings.ini"""
    try:
        data = request.get_json()
        
        section = data.get('section')
        key = data.get('key')
        value = data.get('value')
        field_type = data.get('type', 'string')
        description = data.get('description', '')
        
        # Validar parâmetros obrigatórios
        if not all([section, key, value is not None]):
            return jsonify({
                'success': False,
                'error': 'section, key e value são obrigatórios'
            }), 400
        
        # Validar formato da chave
        if not key or '=' in key or '\n' in key:
            return jsonify({
                'success': False,
                'error': 'Nome do campo inválido'
            }), 400
        
        # Usar ServerSettingsManager
        config_dir = path_helper.get_scum_server_path('config_directory')
        settings_manager = ServerSettingsManager(config_dir)
        
        # Adicionar campo (será tratado como desconhecido)
        result = settings_manager.set_value(
            section=section,
            key=key,
            value=value,
            validate=False  # Não validar campos customizados
        )
        
        if result['success']:
            # Registrar campo customizado
            settings_manager.register_custom_field(
                section=section,
                key=key,
                field_type=field_type,
                description=description
            )
            
            return jsonify({
                'success': True,
                'message': f'Campo {key} adicionado com sucesso',
                'data': {
                    'section': section,
                    'key': key,
                    'value': value,
                    'type': field_type,
                    'is_custom': True,
                    'requires_restart': True  # Campos customizados assumem restart
                }
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erro ao adicionar campo customizado: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### **Endpoint: PATCH /api/server/settings (Atualizado)**

```python
@app.route('/api/server/settings', methods=['PATCH'])
def update_server_settings():
    """Atualizar configurações do servidor (aceita campos novos)"""
    try:
        data = request.get_json()
        
        section = data.get('section')
        updates = data.get('updates', {})
        
        if not section:
            return jsonify({
                'success': False,
                'error': 'section é obrigatório'
            }), 400
        
        config_dir = path_helper.get_scum_server_path('config_directory')
        settings_manager = ServerSettingsManager(config_dir)
        
        results = []
        errors = []
        
        for key, value in updates.items():
            # Verificar se é campo conhecido
            is_known = settings_manager._is_known_field(section, key)
            
            # Validar apenas campos conhecidos
            validate = is_known
            
            result = settings_manager.set_value(
                section=section,
                key=key,
                value=value,
                validate=validate
            )
            
            if result['success']:
                results.append({
                    'key': key,
                    'value': value,
                    'is_known': is_known,
                    'is_custom': not is_known,
                    'requires_restart': result.get('requires_restart', True)
                })
                
                # Se for campo novo, registrar
                if not is_known:
                    settings_manager.register_custom_field(
                        section=section,
                        key=key,
                        field_type=settings_manager._infer_type(str(value))
                    )
            else:
                errors.append({
                    'key': key,
                    'error': result.get('error', 'Erro desconhecido')
                })
        
        if errors:
            return jsonify({
                'success': False,
                'message': 'Alguns campos falharam',
                'results': results,
                'errors': errors
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'{len(results)} campo(s) atualizado(s)',
            'data': {
                'section': section,
                'updated_fields': results,
                'requires_restart': any(r.get('requires_restart') for r in results)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao atualizar configurações: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

## 🗄️ Registro de Campos Customizados

### **Método: register_custom_field**

```python
def register_custom_field(self, section: str, key: str, field_type: str = None, description: str = ''):
    """Registrar campo customizado para futuras referências"""
    if section not in self.custom_fields:
        self.custom_fields[section] = {}
    
    # Se campo já existe, atualizar informações
    if key in self.custom_fields[section]:
        self.custom_fields[section][key].update({
            'type': field_type or self.custom_fields[section][key].get('type'),
            'description': description or self.custom_fields[section][key].get('description', ''),
            'last_modified': datetime.now().isoformat()
        })
    else:
        # Novo campo
        self.custom_fields[section][key] = {
            'type': field_type or self._infer_type_from_value(key),
            'description': description,
            'first_seen': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'added_by': 'frontend'  # Ou 'auto' se descoberto automaticamente
        }
    
    self._save_custom_fields()
```

### **Arquivo: data/server_settings_custom_fields.json**

```json
{
  "General": {
    "custom.MyCustomSetting": {
      "type": "integer",
      "description": "Minha configuração customizada",
      "first_seen": "2025-12-02T19:30:00",
      "last_modified": "2025-12-02T19:30:00",
      "added_by": "frontend"
    },
    "mod.ModSetting": {
      "type": "string",
      "description": "",
      "first_seen": "2025-12-02T19:35:00",
      "last_modified": "2025-12-02T19:35:00",
      "added_by": "auto"
    }
  }
}
```

---

## 📥 Resposta ao Frontend

### **Sucesso ao Adicionar Campo**

```json
{
  "success": true,
  "message": "Campo custom.MyCustomSetting adicionado com sucesso",
  "data": {
    "section": "General",
    "key": "custom.MyCustomSetting",
    "value": 100,
    "type": "integer",
    "is_custom": true,
    "requires_restart": true,
    "metadata": {
      "first_seen": "2025-12-02T19:30:00",
      "added_by": "frontend"
    }
  }
}
```

### **Erro ao Adicionar Campo**

```json
{
  "success": false,
  "error": "Nome do campo inválido",
  "details": {
    "field": "custom.My=Setting",  // Exemplo de nome inválido
    "reason": "Campo contém caracteres inválidos (= ou quebra de linha)"
  }
}
```

---

## 🔄 Carregamento de Campos Customizados

### **Endpoint: GET /api/server/settings**

Quando o frontend carrega as configurações, o backend retorna:

```json
{
  "success": true,
  "data": {
    "General": {
      "scum.ServerName": "SCUM Server",  // Campo conhecido
      "scum.MaxPlayers": 64,             // Campo conhecido
      "custom.MyCustomSetting": 100,     // Campo customizado
      "mod.ModSetting": "value"           // Campo de mod
    },
    "metadata": {
      "General": {
        "scum.ServerName": {
          "type": "string",
          "is_known": true,
          "description": "Nome do servidor"
        },
        "custom.MyCustomSetting": {
          "type": "integer",
          "is_known": false,
          "is_custom": true,
          "description": "Minha configuração customizada",
          "added_by": "frontend"
        }
      }
    }
  }
}
```

---

## 🎨 Interface do Frontend

### **Componente React: Adicionar Campo Customizado**

```typescript
interface CustomFieldForm {
  section: string;
  key: string;
  value: string | number | boolean;
  type: 'string' | 'integer' | 'float' | 'boolean' | 'time';
  description?: string;
}

function AddCustomFieldModal({ section, onClose, onSuccess }) {
  const [form, setForm] = useState<CustomFieldForm>({
    section,
    key: '',
    value: '',
    type: 'string',
    description: ''
  });
  
  const handleSubmit = async () => {
    try {
      const response = await fetch('/api/server/settings/add-field', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });
      
      const data = await response.json();
      
      if (data.success) {
        onSuccess(data.data);
        onClose();
      } else {
        alert(`Erro: ${data.error}`);
      }
    } catch (error) {
      alert(`Erro ao adicionar campo: ${error.message}`);
    }
  };
  
  return (
    <Modal>
      <h2>Adicionar Campo Customizado</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Nome do Campo:</label>
          <input
            type="text"
            value={form.key}
            onChange={(e) => setForm({ ...form, key: e.target.value })}
            placeholder="ex: custom.MySetting ou mod.ModSetting"
            required
          />
          <small>Use prefixo 'custom.' ou 'mod.' para organização</small>
        </div>
        
        <div>
          <label>Tipo:</label>
          <select
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value as any })}
          >
            <option value="string">String (Texto)</option>
            <option value="integer">Integer (Número Inteiro)</option>
            <option value="float">Float (Número Decimal)</option>
            <option value="boolean">Boolean (0 ou 1)</option>
            <option value="time">Time (HH:MM:SS)</option>
          </select>
        </div>
        
        <div>
          <label>Valor:</label>
          <input
            type={form.type === 'boolean' ? 'checkbox' : 'text'}
            value={form.value}
            onChange={(e) => {
              let value: any = e.target.value;
              if (form.type === 'integer') value = parseInt(value);
              else if (form.type === 'float') value = parseFloat(value);
              else if (form.type === 'boolean') value = e.target.checked ? 1 : 0;
              setForm({ ...form, value });
            }}
            required
          />
        </div>
        
        <div>
          <label>Descrição (Opcional):</label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Descreva o que este campo faz..."
          />
        </div>
        
        <button type="submit">Adicionar Campo</button>
        <button type="button" onClick={onClose}>Cancelar</button>
      </form>
    </Modal>
  );
}
```

### **Componente: Lista de Configurações com Suporte a Campos Customizados**

```typescript
function ServerSettingsSection({ section, settings, metadata }) {
  const [showAddField, setShowAddField] = useState(false);
  
  return (
    <div className="settings-section">
      <h3>[{section}]</h3>
      
      {/* Campos Conhecidos */}
      {Object.entries(settings).map(([key, value]) => {
        const fieldMeta = metadata?.[key];
        const isCustom = fieldMeta?.is_custom || false;
        
        return (
          <div key={key} className={`setting-item ${isCustom ? 'custom-field' : ''}`}>
            <label>
              {key}
              {isCustom && <span className="badge">Custom</span>}
            </label>
            <input
              type="text"
              value={value}
              onChange={(e) => handleUpdate(section, key, e.target.value)}
            />
            {fieldMeta?.description && (
              <small>{fieldMeta.description}</small>
            )}
          </div>
        );
      })}
      
      {/* Botão para adicionar campo customizado */}
      <button onClick={() => setShowAddField(true)}>
        ➕ Adicionar Campo Customizado
      </button>
      
      {showAddField && (
        <AddCustomFieldModal
          section={section}
          onClose={() => setShowAddField(false)}
          onSuccess={(newField) => {
            // Atualizar lista de configurações
            refreshSettings();
            setShowAddField(false);
          }}
        />
      )}
    </div>
  );
}
```

---

## ✅ Validações no Backend

### **Validação de Nome do Campo**

```python
def validate_field_name(key: str) -> Tuple[bool, str]:
    """Validar nome do campo customizado"""
    if not key:
        return False, "Nome do campo não pode ser vazio"
    
    if len(key) > 100:
        return False, "Nome do campo muito longo (máximo 100 caracteres)"
    
    # Caracteres inválidos
    invalid_chars = ['=', '\n', '\r', '[', ']']
    for char in invalid_chars:
        if char in key:
            return False, f"Caractere inválido: {char}"
    
    # Não pode começar com espaço
    if key.startswith(' ') or key.endswith(' '):
        return False, "Nome do campo não pode começar ou terminar com espaço"
    
    return True, ""
```

### **Validação de Valor por Tipo**

```python
def validate_value_by_type(value: Any, field_type: str) -> Tuple[bool, str]:
    """Validar valor baseado no tipo"""
    if field_type == 'integer':
        try:
            int(value)
            return True, ""
        except ValueError:
            return False, "Valor deve ser um número inteiro"
    
    elif field_type == 'float':
        try:
            float(value)
            return True, ""
        except ValueError:
            return False, "Valor deve ser um número decimal"
    
    elif field_type == 'boolean':
        if str(value) in ('0', '1', 'true', 'false', 'True', 'False'):
            return True, ""
        return False, "Valor deve ser 0, 1, true ou false"
    
    elif field_type == 'time':
        if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', str(value)):
            return True, ""
        return False, "Formato inválido. Use HH:MM:SS ou HH:MM"
    
    # string - sempre válido
    return True, ""
```

---

## 🔄 Fluxo Completo Visualizado

```
1. Frontend: Admin clica "Adicionar Campo Customizado"
   ↓
2. Frontend: Modal aparece, admin preenche:
   - Nome: custom.MySetting
   - Valor: 100
   - Tipo: integer
   ↓
3. Frontend: POST /api/server/settings/add-field
   {
     "section": "General",
     "key": "custom.MySetting",
     "value": 100,
     "type": "integer"
   }
   ↓
4. Backend: Valida nome do campo
   ↓
5. Backend: Valida valor pelo tipo
   ↓
6. Backend: Abre ServerSettings.ini
   ↓
7. Backend: Adiciona campo na seção [General]
   custom.MySetting=100
   ↓
8. Backend: Salva arquivo
   ↓
9. Backend: Registra em custom_fields.json
   ↓
10. Backend: Retorna sucesso
    ↓
11. Frontend: Atualiza lista de configurações
    ↓
12. Frontend: Mostra campo com badge "Custom"
```

---

## 📋 Resumo da Implementação

### **Endpoints Necessários**

1. `POST /api/server/settings/add-field` - Adicionar campo customizado
2. `PATCH /api/server/settings` - Atualizar (aceita campos novos)
3. `PUT /api/server/settings/{section}` - Salvar seção completa (aceita campos novos)
4. `GET /api/server/settings` - Carregar (inclui campos customizados)

### **Arquivos de Dados**

1. `ServerSettings.ini` - Arquivo original (com todos os campos)
2. `data/server_settings_custom_fields.json` - Registro de campos customizados

### **Funcionalidades**

1. ✅ Aceitar campos desconhecidos
2. ✅ Validar nome do campo
3. ✅ Validar valor por tipo
4. ✅ Registrar campo customizado
5. ✅ Preservar ao recarregar
6. ✅ Marcar como customizado no frontend

---

**Última atualização**: 02/12/2025

