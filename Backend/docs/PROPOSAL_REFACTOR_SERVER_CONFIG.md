# 🔧 Proposta: Refatoração da Seção "server" no config.json

## 🎯 Objetivo

Eliminar redundância entre a seção `server` e `paths.scum_server`, simplificando a estrutura do `config.json` e fazendo o `ServerManager` usar o `ConfigPathHelper` de forma consistente.

---

## 📊 Situação Atual

### **Redundância Identificada**

A seção `server` contém campos que já existem em `paths.scum_server`:

| Campo em `server` | Equivalente em `paths.scum_server` | Status |
|-------------------|-------------------------------------|--------|
| `server_path` | `binaries_directory` | ✅ Redundante |
| `install_path` | `root_directory` | ✅ Redundante |
| `logs_directory` | `logs_directory` | ✅ Redundante |
| `steamcmd_path` | - | ❌ Único |
| `nssm_path` | - | ❌ Único |
| `port` | - | ❌ Único |
| `max_players` | - | ❌ Único |
| `use_battleye` | - | ❌ Único |
| `service_name` | - | ❌ Único (mas não usado) |

### **Uso Atual**

1. **ServerManager** (linha 167 do `main.py`):
   ```python
   server_manager = ServerManager(config.get('server', {}))
   ```
   - Lê diretamente de `config['server']`
   - Não usa `ConfigPathHelper`

2. **ConfigPathHelper**:
   - Usa `paths.scum_server` como principal
   - Usa `server` apenas como fallback (linhas 62-64)

---

## 💡 Proposta de Refatoração

### **Fase 1: Refatorar ServerManager**

Modificar `ServerManager` para:
1. Receber `ConfigPathHelper` como parâmetro
2. Usar métodos do `ConfigPathHelper` para obter caminhos
3. Manter apenas campos específicos do servidor na seção `server`

**Antes:**
```python
class ServerManager:
    def __init__(self, config: Dict[str, Any]):
        self.server_path = config.get('server_path', '...')
        self.install_path = config.get('install_path', '...')
        self.steamcmd_path = config.get('steamcmd_path', '...')
        # ...
```

**Depois:**
```python
class ServerManager:
    def __init__(self, config: Dict[str, Any], path_helper: ConfigPathHelper):
        # Usar ConfigPathHelper para caminhos
        self.server_path = path_helper.get_scum_server_path('binaries_directory')
        self.install_path = path_helper.get_scum_server_path('root_directory')
        
        # Campos específicos do servidor (não são caminhos)
        server_config = config.get('server', {})
        self.steamcmd_path = server_config.get('steamcmd_path', 'C:\\Servers\\steamcmd')
        self.port = server_config.get('port', 8900)
        self.max_players = server_config.get('max_players', 64)
        self.use_battleye = server_config.get('use_battleye', True)
        # ...
```

### **Fase 2: Simplificar config.json**

**Estrutura Atual:**
```json
{
  "paths": {
    "scum_server": {
      "root_directory": "C:\\Servers\\Scum",
      "binaries_directory": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64",
      "logs_directory": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs"
    }
  },
  "server": {
    "server_path": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64",  // ❌ Redundante
    "install_path": "C:\\Servers\\Scum",                        // ❌ Redundante
    "logs_directory": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs", // ❌ Redundante
    "steamcmd_path": "C:\\Servers\\steamcmd",                   // ✅ Manter
    "nssm_path": "nssm-2.24\\win64\\nssm.exe",                 // ✅ Manter
    "port": 8900,                                               // ✅ Manter
    "max_players": 64,                                          // ✅ Manter
    "use_battleye": true,                                       // ✅ Manter
    "service_name": "SCUMServer"                               // ✅ Manter (mas não usado)
  }
}
```

**Estrutura Proposta:**
```json
{
  "paths": {
    "scum_server": {
      "root_directory": "C:\\Servers\\Scum",
      "binaries_directory": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64",
      "logs_directory": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs"
    }
  },
  "server": {
    "steamcmd_path": "C:\\Servers\\steamcmd",                   // ✅ Específico do servidor
    "nssm_path": "nssm-2.24\\win64\\nssm.exe",                 // ✅ Específico do servidor
    "port": 8900,                                               // ✅ Configuração do servidor
    "max_players": 64,                                          // ✅ Configuração do servidor
    "use_battleye": true                                        // ✅ Configuração do servidor
  }
}
```

### **Fase 3: Atualizar ConfigPathHelper**

Remover fallbacks para campos que não existem mais em `server`:

**Antes:**
```python
fallbacks = {
    'root_directory': self.config.get('server', {}).get('install_path', '...'),
    'binaries_directory': self.config.get('server', {}).get('server_path', '...'),
    'logs_directory': self.config.get('server', {}).get('logs_directory', '...'),
}
```

**Depois:**
```python
fallbacks = {
    'root_directory': 'C:\\Servers\\Scum',
    'binaries_directory': 'C:\\Servers\\Scum\\SCUM\\Binaries\\Win64',
    'logs_directory': 'C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs',
}
```

---

## 🔄 Plano de Migração

### **Passo 1: Refatorar ServerManager**
1. Modificar `__init__` para receber `ConfigPathHelper`
2. Substituir leitura direta de `config['server']` por métodos do `path_helper`
3. Manter apenas campos específicos do servidor

### **Passo 2: Atualizar main.py**
```python
# Antes
server_manager = ServerManager(config.get('server', {}))

# Depois
server_manager = ServerManager(config.get('server', {}), path_helper)
```

### **Passo 3: Atualizar config.json**
1. Remover campos redundantes de `server`:
   - `server_path` → usar `paths.scum_server.binaries_directory`
   - `install_path` → usar `paths.scum_server.root_directory`
   - `logs_directory` → usar `paths.scum_server.logs_directory`
2. Manter apenas campos específicos

### **Passo 4: Atualizar ConfigPathHelper**
1. Remover fallbacks para campos removidos de `server`
2. Usar valores padrão hardcoded como fallback final

### **Passo 5: Script de Migração**
Criar script para migrar `config.json` existente:
```python
# scripts/migrate_server_config.py
def migrate_config(config_path):
    # Ler config atual
    # Remover campos redundantes de server
    # Salvar config atualizado
```

---

## ✅ Benefícios

1. **Eliminação de Redundância**: Um único local para cada caminho
2. **Consistência**: Todos os componentes usam `ConfigPathHelper`
3. **Manutenibilidade**: Mais fácil de manter e atualizar
4. **Clareza**: Separação clara entre caminhos (`paths`) e configurações (`server`)
5. **Compatibilidade**: `ConfigPathHelper` já tem fallbacks, então é seguro

---

## ⚠️ Considerações

### **Compatibilidade Retroativa**

O `ConfigPathHelper` já tem fallbacks para a estrutura antiga, então:
- Configs antigos continuarão funcionando
- Migração pode ser gradual
- Não quebra código existente

### **Campos a Manter em `server`**

- `steamcmd_path` - Específico do gerenciamento do servidor
- `nssm_path` - Específico do gerenciamento do servidor
- `port` - Configuração do servidor SCUM
- `max_players` - Configuração do servidor SCUM
- `use_battleye` - Configuração do servidor SCUM
- `service_name` - Pode ser removido se não for usado (está hardcoded)

### **Testes Necessários**

1. Testar inicialização do `ServerManager` com novo formato
2. Testar todos os métodos que usam caminhos
3. Testar com config antigo (compatibilidade)
4. Testar com config novo (sem redundância)

---

## 📋 Checklist de Implementação

- [ ] Refatorar `ServerManager.__init__` para usar `ConfigPathHelper`
- [ ] Atualizar `main.py` para passar `path_helper` ao `ServerManager`
- [ ] Criar script de migração `migrate_server_config.py`
- [ ] Atualizar `ConfigPathHelper` para remover fallbacks redundantes
- [ ] Atualizar `config.example.json` com nova estrutura
- [ ] Testar com config antigo (compatibilidade)
- [ ] Testar com config novo (sem redundância)
- [ ] Atualizar documentação
- [ ] Executar migração no `config.json` de produção

---

## 🔍 Verificação de Impacto

### **Arquivos Afetados**

1. `core/server_control/server_manager.py` - Refatoração principal
2. `main.py` - Atualizar inicialização
3. `utils/config_path_helper.py` - Remover fallbacks redundantes
4. `data/config.json` - Remover campos redundantes
5. `data/config.example.json` - Atualizar exemplo

### **Sem Impacto**

- Outros serviços que usam `ConfigPathHelper` (já estão corretos)
- Endpoints da API (não acessam diretamente `config['server']`)

---

**Última atualização**: 02/12/2025

