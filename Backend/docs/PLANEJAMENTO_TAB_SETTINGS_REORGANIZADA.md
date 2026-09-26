# Planejamento: Tab Settings Reorganizada

## 📋 Objetivo

Reorganizar as tabs da GUI para:
1. **Tab Settings única**: Configurar paths do SCUM Server (linhas 9-17) + API Key + Hash
2. **Remover Tab Credentials**: Integrar seus campos na tab Settings
3. **Manter Tab Logs**: Apenas para visualização de logs

---

## 🎯 Estrutura Proposta

### **Tab Settings (Única para Configurações)**

#### **Seção 1: SCUM Server Paths**
Campos editáveis para configurar os caminhos do servidor SCUM:

```
┌─────────────────────────────────────────────────────────┐
│ SCUM Server Paths                                       │
├─────────────────────────────────────────────────────────┤
│ Root Directory:                                         │
│ [C:\Servers\Scum                    ] [📁 Browse]      │
│                                                          │
│ Binaries Directory:                                     │
│ [C:\Servers\Scum\SCUM\Binaries\Win64] [📁 Browse]      │
│                                                          │
│ Logs Directory:                                         │
│ [C:\Servers\Scum\SCUM\Saved\SaveFiles\Logs] [📁 Browse]│
│                                                          │
│ Config Directory:                                       │
│ [C:\Servers\Scum\SCUM\Saved\Config\WindowsServer] [📁] │
│                                                          │
│ Database:                                               │
│ [C:\Servers\Scum\SCUM\Saved\SaveFiles\SCUM.db] [📁]     │
│                                                          │
│ Savefiles Directory:                                    │
│ [C:\Servers\Scum\SCUM\Saved\SaveFiles] [📁 Browse]     │
└─────────────────────────────────────────────────────────┘
```

#### **Seção 2: Credentials**
API Key e Hash (movidos da tab Credentials):

```
┌─────────────────────────────────────────────────────────┐
│ Credentials                                              │
├─────────────────────────────────────────────────────────┤
│ API Key:                                                 │
│ [****************************] [👁] [✏]                 │
│                                                          │
│ Hash:                                                    │
│ [xxx...] [📋]                                            │
└─────────────────────────────────────────────────────────┘
```

#### **Botões de Ação**
```
[Save Settings] [Reload Settings]
```

---

## 📐 Layout Visual Completo

```
┌─────────────────────────────────────────────────────────┐
│ [Logo]  SSM Backend v3.1.0          [⚙][🌍][☑] [─][×] │
├─────────────────────────────────────────────────────────┤
│ Status: Backend ● │ Server ● │ Next: 2h 30m [Start][Stop]│
├─────────────────────────────────────────────────────────┤
│ [Settings] [Logs]                                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ SCUM Server Paths                                │   │
│  │ Root Directory: [________________] [📁]         │   │
│  │ Binaries: [________________] [📁]               │   │
│  │ Logs: [________________] [📁]                   │   │
│  │ Config: [________________] [📁]                 │   │
│  │ Database: [________________] [📁]                  │   │
│  │ Savefiles: [________________] [📁]               │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Credentials                                       │   │
│  │ API Key: [________________] [👁][✏]              │   │
│  │ Hash: [________________] [📋]                    │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  [Save Settings] [Reload Settings]                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementação Técnica

### **1. Remover Tab Credentials**
- Remover `("Credentials", "credentials")` da lista de tabs
- Remover método `_create_credentials_tab()`
- Mover código de API Key e Hash para `_create_settings_tab()`

### **2. Criar Tab Settings Completa**

#### **Estrutura do Método `_create_settings_tab()`:**

```python
def _create_settings_tab(self, parent):
    """Criar tab de Settings com SCUM Server Paths + Credentials"""
    settings_frame = ctk.CTkFrame(parent, fg_color="transparent")
    self.tabs_content["settings"] = settings_frame
    
    # Scrollable frame
    scrollable_frame = ctk.CTkScrollableFrame(settings_frame)
    scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # ========== SEÇÃO 1: SCUM SERVER PATHS ==========
    paths_card = ctk.CTkFrame(scrollable_frame)
    paths_card.pack(fill="x", pady=(0, 10), padx=10)
    
    # Título
    paths_title = ctk.CTkLabel(...)
    
    # Campos de path (6 campos)
    # - root_directory
    # - binaries_directory
    # - logs_directory
    # - config_directory
    # - database
    # - savefiles_directory
    
    # Cada campo terá:
    # - Label
    # - Entry (largura expandida)
    # - Botão "Browse" (📁) para selecionar pasta/arquivo
    
    # ========== SEÇÃO 2: CREDENTIALS ==========
    credentials_card = ctk.CTkFrame(scrollable_frame)
    credentials_card.pack(fill="x", pady=(0, 10), padx=10)
    
    # Título
    credentials_title = ctk.CTkLabel(...)
    
    # API Key (mesmo código da tab Credentials antiga)
    # Hash (mesmo código da tab Credentials antiga)
    
    # ========== BOTÕES ==========
    buttons_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
    buttons_frame.pack(fill="x", pady=(10, 0), padx=10)
    
    # Save Settings
    # Reload Settings
    
    # Carregar valores iniciais
    self._load_settings()
```

### **3. Funcionalidade Browse (Seleção de Pastas/Arquivos)**

```python
def _browse_path(self, field_name: str):
    """Abrir diálogo para selecionar pasta ou arquivo"""
    import tkinter.filedialog as filedialog
    
    current_value = getattr(self, f'settings_{field_name}').get()
    
    if field_name == 'database':
        # Selecionar arquivo (.db)
        path = filedialog.askopenfilename(
            title=f"Select {field_name}",
            initialdir=os.path.dirname(current_value) if current_value else "C:\\",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")]
        )
    else:
        # Selecionar pasta
        path = filedialog.askdirectory(
            title=f"Select {field_name}",
            initialdir=current_value if current_value else "C:\\"
        )
    
    if path:
        getattr(self, f'settings_{field_name}').delete(0, "end")
        getattr(self, f'settings_{field_name}').insert(0, path)
```

### **4. Métodos de Load/Save**

#### **`_load_settings()`:**
```python
def _load_settings(self):
    """Carregar configurações do config.json"""
    config = self._load_config()
    
    # Carregar paths.scum_server
    scum_paths = config.get('paths', {}).get('scum_server', {})
    
    # Preencher campos de path
    self.settings_root_directory.delete(0, "end")
    self.settings_root_directory.insert(0, scum_paths.get('root_directory', ''))
    # ... (repetir para todos os campos)
    
    # Carregar credentials (API Key e Hash)
    # ... (código existente)
```

#### **`_save_settings()`:**
```python
def _save_settings(self):
    """Salvar configurações para o config.json"""
    config = self._load_config()
    
    # Salvar paths.scum_server
    if 'paths' not in config:
        config['paths'] = {}
    if 'scum_server' not in config['paths']:
        config['paths']['scum_server'] = {}
    
    config['paths']['scum_server']['root_directory'] = self.settings_root_directory.get()
    config['paths']['scum_server']['binaries_directory'] = self.settings_binaries_directory.get()
    # ... (repetir para todos os campos)
    
    # Salvar credentials (API Key e Hash)
    # ... (código existente)
    
    # Salvar config.json
    # ... (código existente)
```

---

## 📝 Campos a Configurar

### **SCUM Server Paths (6 campos):**

1. **root_directory**: `C:\Servers\Scum`
   - Tipo: Pasta
   - Browse: Selecionar pasta

2. **binaries_directory**: `C:\Servers\Scum\SCUM\Binaries\Win64`
   - Tipo: Pasta
   - Browse: Selecionar pasta

3. **logs_directory**: `C:\Servers\Scum\SCUM\Saved\SaveFiles\Logs`
   - Tipo: Pasta
   - Browse: Selecionar pasta

4. **config_directory**: `C:\Servers\Scum\SCUM\Saved\Config\WindowsServer`
   - Tipo: Pasta
   - Browse: Selecionar pasta

5. **database**: `C:\Servers\Scum\SCUM\Saved\SaveFiles\SCUM.db`
   - Tipo: Arquivo (.db)
   - Browse: Selecionar arquivo

6. **savefiles_directory**: `C:\Servers\Scum\SCUM\Saved\SaveFiles`
   - Tipo: Pasta
   - Browse: Selecionar pasta

### **Credentials (2 campos):**

1. **API Key**: Campo existente (com mostrar/ocultar e editar)
2. **Hash**: Campo existente (somente leitura, com copiar)

---

## 🎨 Design dos Campos

### **Layout de Cada Campo de Path:**

```
┌─────────────────────────────────────────────────────────┐
│ Root Directory:                                          │
│ ┌──────────────────────────────────────┐ ┌──────┐      │
│ │ C:\Servers\Scum                       │ │ 📁  │      │
│ └──────────────────────────────────────┘ └──────┘      │
└─────────────────────────────────────────────────────────┘
```

### **Layout de Credentials:**

```
┌─────────────────────────────────────────────────────────┐
│ API Key:                                                 │
│ ┌──────────────────────────────────────┐ ┌──┐ ┌──┐    │
│ │ ************************************  │ │👁│ │✏│    │
│ └──────────────────────────────────────┘ └──┘ └──┘    │
│                                                          │
│ Hash:                                                    │
│ ┌──────────────────────────────────────┐ ┌──┐          │
│ │ xxx...                               │ │📋│          │
│ └──────────────────────────────────────┘ └──┘          │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Vantagens

1. ✅ **Organização**: Tudo relacionado a configuração em uma única tab
2. ✅ **Simplicidade**: Menos tabs, interface mais limpa
3. ✅ **Funcionalidade**: Browse facilita seleção de pastas/arquivos
4. ✅ **Consistência**: Todos os campos editáveis em um só lugar

---

## 🔄 Mudanças Necessárias

### **Arquivos a Modificar:**

1. **`gui/main_window.py`**:
   - Remover tab "Credentials" da lista
   - Remover método `_create_credentials_tab()`
   - Criar método `_create_settings_tab()` completo
   - Adicionar método `_browse_path()` para seleção de pastas/arquivos
   - Atualizar `_load_settings()` e `_save_settings()`
   - Mover código de API Key e Hash para Settings

### **Funcionalidades a Implementar:**

1. ✅ Seleção de pastas (tkinter.filedialog.askdirectory)
2. ✅ Seleção de arquivos (tkinter.filedialog.askopenfilename)
3. ✅ Validação de caminhos antes de salvar
4. ✅ Feedback visual ao salvar/carregar

---

## 📋 Checklist de Implementação

- [ ] Remover tab "Credentials" da lista de tabs
- [ ] Remover método `_create_credentials_tab()`
- [ ] Criar método `_create_settings_tab()` com:
  - [ ] Seção SCUM Server Paths (6 campos + botões Browse)
  - [ ] Seção Credentials (API Key + Hash)
  - [ ] Botões Save/Reload
- [ ] Criar método `_browse_path()` para seleção de pastas/arquivos
- [ ] Atualizar `_load_settings()` para carregar paths + credentials
- [ ] Atualizar `_save_settings()` para salvar paths + credentials
- [ ] Testar carregamento de valores do config.json
- [ ] Testar salvamento de valores no config.json
- [ ] Testar botões Browse (seleção de pastas/arquivos)
- [ ] Testar funcionalidades de API Key (mostrar/ocultar, editar)
- [ ] Testar funcionalidade de Hash (copiar)

---

## 🚀 Próximos Passos

1. ⏳ Revisar planejamento
2. ⏳ Implementar mudanças
3. ⏳ Testar funcionalidades
4. ⏳ Ajustar se necessário

