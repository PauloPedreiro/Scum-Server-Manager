# 🎯 Solução Simples: Gerenciamento de ServerSettings.ini

## 📋 Abordagem Simplificada

Manter o padrão atual do `ServerSettings.ini`:
- ✅ Ler arquivo completo
- ✅ Editar qualquer campo (conhecido ou não)
- ✅ Salvar preservando tudo
- ✅ Sem schema complexo
- ✅ Sem registro separado de campos customizados

---

## 🔧 Implementação Simples

### **Classe ServerSettingsManager (Simplificada)**

```python
import configparser
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import shutil

class ServerSettingsManager:
    """Gerenciador simples do ServerSettings.ini"""
    
    def __init__(self, config_directory: str):
        self.config_directory = Path(config_directory)
        self.settings_file = self.config_directory / 'ServerSettings.ini'
        self.parser = configparser.ConfigParser()
        self.parser.optionxform = str  # Preservar case das chaves
    
    def load_all(self) -> Dict[str, Dict[str, str]]:
        """Carregar todas as configurações"""
        if not self.settings_file.exists():
            return {}
        
        self.parser.read(self.settings_file, encoding='utf-8')
        
        result = {}
        for section_name in self.parser.sections():
            result[section_name] = dict(self.parser.items(section_name))
        
        return result
    
    def get_section(self, section: str) -> Dict[str, str]:
        """Obter seção específica"""
        if not self.settings_file.exists():
            return {}
        
        self.parser.read(self.settings_file, encoding='utf-8')
        
        if not self.parser.has_section(section):
            return {}
        
        return dict(self.parser.items(section))
    
    def get_value(self, section: str, key: str) -> Optional[str]:
        """Obter valor específico"""
        if not self.settings_file.exists():
            return None
        
        self.parser.read(self.settings_file, encoding='utf-8')
        
        if not self.parser.has_section(section):
            return None
        
        return self.parser.get(section, key, fallback=None)
    
    def set_value(self, section: str, key: str, value: Any) -> Dict[str, Any]:
        """Definir valor (aceita qualquer campo)"""
        # Criar backup antes de modificar
        backup_path = self._create_backup()
        
        # Carregar arquivo atual
        self.parser.read(self.settings_file, encoding='utf-8')
        
        # Criar seção se não existir
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        
        # Definir valor (sempre como string)
        self.parser.set(section, key, str(value))
        
        # Salvar arquivo
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                self.parser.write(f)
            
            return {
                'success': True,
                'message': f'Configuração {key} atualizada',
                'section': section,
                'key': key,
                'value': str(value),
                'backup': str(backup_path)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro ao salvar: {str(e)}'
            }
    
    def update_section(self, section: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Atualizar múltiplos campos de uma seção"""
        backup_path = self._create_backup()
        
        self.parser.read(self.settings_file, encoding='utf-8')
        
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        
        updated = []
        for key, value in updates.items():
            self.parser.set(section, key, str(value))
            updated.append(key)
        
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                self.parser.write(f)
            
            return {
                'success': True,
                'message': f'{len(updated)} campo(s) atualizado(s)',
                'section': section,
                'updated_fields': updated,
                'backup': str(backup_path)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro ao salvar: {str(e)}'
            }
    
    def _create_backup(self) -> Path:
        """Criar backup do arquivo antes de modificar"""
        if not self.settings_file.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.config_directory / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        backup_path = backup_dir / f'ServerSettings.backup.{timestamp}.ini'
        shutil.copy2(self.settings_file, backup_path)
        
        # Manter apenas últimos 10 backups
        self._cleanup_old_backups(backup_dir)
        
        return backup_path
    
    def _cleanup_old_backups(self, backup_dir: Path, keep: int = 10):
        """Limpar backups antigos, mantendo apenas os últimos N"""
        backups = sorted(backup_dir.glob('ServerSettings.backup.*.ini'), reverse=True)
        for backup in backups[keep:]:
            backup.unlink()
```

---

## 📡 Endpoints Simples

### **1. GET /api/server/settings**

```python
@app.route('/api/server/settings', methods=['GET'])
def get_server_settings():
    """Obter todas as configurações ou seção específica"""
    try:
        section = request.args.get('section')
        
        config_dir = path_helper.get_scum_server_path('config_directory')
        manager = ServerSettingsManager(config_dir)
        
        if section:
            # Retornar apenas uma seção
            settings = manager.get_section(section)
            return jsonify({
                'success': True,
                'data': {
                    section: settings
                }
            })
        else:
            # Retornar todas as seções
            settings = manager.load_all()
            return jsonify({
                'success': True,
                'data': settings
            })
            
    except Exception as e:
        logger.error(f"Erro ao carregar configurações: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### **2. PATCH /api/server/settings**

```python
@app.route('/api/server/settings', methods=['PATCH'])
def update_server_settings():
    """Atualizar configuração (aceita qualquer campo)"""
    try:
        data = request.get_json()
        
        section = data.get('section')
        key = data.get('key')
        value = data.get('value')
        
        if not all([section, key, value is not None]):
            return jsonify({
                'success': False,
                'error': 'section, key e value são obrigatórios'
            }), 400
        
        config_dir = path_helper.get_scum_server_path('config_directory')
        manager = ServerSettingsManager(config_dir)
        
        result = manager.set_value(section, key, value)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erro ao atualizar configuração: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### **3. PUT /api/server/settings/{section}**

```python
@app.route('/api/server/settings/<section>', methods=['PUT'])
def update_section(section: str):
    """Atualizar seção completa (aceita qualquer campo)"""
    try:
        data = request.get_json()
        
        if not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'Body deve ser um objeto com chaves e valores'
            }), 400
        
        config_dir = path_helper.get_scum_server_path('config_directory')
        manager = ServerSettingsManager(config_dir)
        
        result = manager.update_section(section, data)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Erro ao atualizar seção: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

## 🎨 Interface do Frontend (Simplificada)

### **Componente: Editar Seção**

```typescript
function ServerSettingsSection({ section }) {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // Carregar seção
    fetch(`/api/server/settings?section=${section}`)
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setSettings(data.data[section] || {});
        }
        setLoading(false);
      });
  }, [section]);
  
  const handleFieldChange = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };
  
  const handleSave = async () => {
    const response = await fetch(`/api/server/settings/${section}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    });
    
    const data = await response.json();
    if (data.success) {
      alert('Configurações salvas com sucesso!');
    } else {
      alert(`Erro: ${data.error}`);
    }
  };
  
  const handleAddField = () => {
    const key = prompt('Nome do campo:');
    const value = prompt('Valor:');
    
    if (key && value !== null) {
      setSettings(prev => ({ ...prev, [key]: value }));
    }
  };
  
  if (loading) return <div>Carregando...</div>;
  
  return (
    <div className="settings-section">
      <h3>[{section}]</h3>
      
      {Object.entries(settings).map(([key, value]) => (
        <div key={key} className="setting-item">
          <label>{key}</label>
          <input
            type="text"
            value={value}
            onChange={(e) => handleFieldChange(key, e.target.value)}
          />
        </div>
      ))}
      
      <button onClick={handleAddField}>➕ Adicionar Campo</button>
      <button onClick={handleSave}>💾 Salvar</button>
    </div>
  );
}
```

---

## ✅ Vantagens da Abordagem Simples

1. **Simplicidade**: Sem schema, sem registro separado
2. **Flexibilidade**: Aceita qualquer campo
3. **Preservação**: Mantém tudo ao salvar
4. **Fácil de usar**: Interface direta no frontend
5. **Compatibilidade**: Funciona com qualquer versão do jogo
6. **Mods**: Suporta mods automaticamente

---

## 📋 Funcionalidades Básicas

### **O que faz:**
- ✅ Lê arquivo INI completo
- ✅ Permite editar qualquer campo
- ✅ Permite adicionar novos campos
- ✅ Salva preservando tudo
- ✅ Cria backup antes de modificar
- ✅ Limpa backups antigos

### **O que NÃO faz:**
- ❌ Validação de tipos (aceita tudo como string)
- ❌ Schema de campos conhecidos
- ❌ Registro separado de campos customizados
- ❌ Validação de valores permitidos

---

## 🔄 Fluxo Simplificado

```
1. Frontend: Carrega seção [General]
   GET /api/server/settings?section=General
   
2. Backend: Lê ServerSettings.ini
   Retorna todos os campos da seção
   
3. Frontend: Mostra campos em inputs
   Admin pode editar qualquer campo
   Admin pode adicionar novo campo
   
4. Frontend: Salva seção completa
   PUT /api/server/settings/General
   { "scum.MaxPlayers": "100", "custom.NewField": "value" }
   
5. Backend: Cria backup
   Salva ServerSettings.ini
   Preserva todos os campos
   
6. Pronto! ✅
```

---

## 📁 Estrutura de Arquivos

```
core/server_settings/
└── manager.py  # ServerSettingsManager (simples)

main.py
└── Endpoints /api/server/settings/*
```

**Sem arquivos extras de configuração!**

---

## 🎯 Resumo

**Abordagem**: Leitura/escrita direta do INI, sem validação complexa.

**Endpoints**:
- `GET /api/server/settings` - Ler tudo ou seção
- `PATCH /api/server/settings` - Atualizar um campo
- `PUT /api/server/settings/{section}` - Atualizar seção completa

**Frontend**: Interface simples de edição, sem modal complexo.

**Resultado**: Solução simples, flexível e fácil de usar! 🎉

---

**Última atualização**: 02/12/2025

