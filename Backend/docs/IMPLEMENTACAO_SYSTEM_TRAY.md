# ✅ Implementação: Minimizar para Área de Notificação

## 📋 Resumo

Implementação completa da funcionalidade de minimizar para área de notificação (system tray) com checkbox configurável na GUI.

---

## ✅ Arquivos Criados/Modificados

### **1. `gui/system_tray_manager.py` (NOVO)**
Gerenciador completo do system tray com:
- ✅ Criação e gerenciamento de ícone
- ✅ Menu de contexto (Mostrar, Status, Sair)
- ✅ Notificações
- ✅ Thread-safe
- ✅ Fallback se `pystray` não estiver instalado

### **2. `gui/main_window.py` (MODIFICADO)**
Integração completa com system tray:
- ✅ Checkbox na GUI para configurar
- ✅ Salvar/carregar preferência do `config.json`
- ✅ Métodos para mostrar/esconder do tray
- ✅ Handler de fechamento modificado
- ✅ Callbacks do menu do tray

### **3. `requirements.txt` (MODIFICADO)**
- ✅ Adicionado `pystray>=0.19.5`

---

## 🎯 Funcionalidades Implementadas

### **1. Checkbox na GUI**
- Localização: Footer, ao lado dos botões "Control Panel" e "Site SSM"
- Texto: "Minimizar para área de notificação"
- Comportamento:
  - ✅ Marcado: Minimizar/fechar vai para tray
  - ✅ Desmarcado: Comportamento padrão do Windows
  - ✅ Preferência salva automaticamente no `config.json`

### **2. System Tray**
- ✅ Ícone na área de notificação
- ✅ Menu de contexto com opções:
  - **Mostrar**: Restaura janela
  - **Status do Backend**: Mostra status e restaura janela
  - **Sair**: Fecha aplicativo completamente
- ✅ Duplo clique no ícone: Restaura janela

### **3. Comportamento**
- ✅ **Fechar janela (X)**: Se checkbox marcado → vai para tray
- ✅ **Minimizar**: Comportamento padrão (pode ser melhorado futuramente)
- ✅ **Restaurar**: Duplo clique no ícone ou "Mostrar" no menu

### **4. Configuração**
- ✅ Preferência salva em `config.json`:
```json
{
  "gui": {
    "minimize_to_tray": true
  }
}
```
- ✅ Carregada automaticamente na inicialização
- ✅ Padrão: `true` (habilitado)

---

## 🔧 Como Funciona

### **Fluxo de Minimizar para Tray**
```
1. Usuário fecha janela (X) OU minimiza
   ↓
2. on_closing() verifica: minimize_to_tray == True?
   ↓
3. Se SIM: hide_window_to_tray()
   - Esconde janela (withdraw())
   - Mostra ícone no tray
   - Exibe notificação
   ↓
4. Aplicativo continua rodando em segundo plano
```

### **Fluxo de Restaurar do Tray**
```
1. Usuário clica "Mostrar" OU duplo clica no ícone
   ↓
2. _on_tray_show() é chamado
   ↓
3. show_window_from_tray()
   - Mostra janela (deiconify())
   - Traz para frente (lift(), focus_force())
   ↓
4. Janela restaurada e focada
```

### **Fluxo de Sair do Tray**
```
1. Usuário clica "Sair" no menu
   ↓
2. _on_tray_quit() é chamado
   ↓
3. Desmarca checkbox
   ↓
4. on_closing() é chamado (sem minimizar para tray)
   ↓
5. Backend é parado
   ↓
6. System tray é parado
   ↓
7. Aplicativo fecha completamente
```

---

## 📝 Estrutura do Código

### **Variáveis Adicionadas em MainWindow**
```python
self.minimize_to_tray = True  # Preferência do usuário
self.system_tray_manager = None  # Instância do gerenciador
self.is_minimized_to_tray = False  # Estado atual
self.tray_checkbox = None  # Widget do checkbox
```

### **Métodos Adicionados**
- `_load_tray_preference()`: Carrega preferência do config.json
- `_save_tray_preference()`: Salva preferência no config.json
- `_init_system_tray()`: Inicializa system tray
- `_on_tray_checkbox_changed()`: Handler do checkbox
- `hide_window_to_tray()`: Esconde janela e mostra no tray
- `show_window_from_tray()`: Restaura janela do tray
- `_on_tray_show()`: Callback "Mostrar"
- `_on_tray_status()`: Callback "Status"
- `_on_tray_quit()`: Callback "Sair"

---

## 🎨 Interface do Usuário

### **Checkbox**
- **Localização**: Footer, após botões "Control Panel" e "Site SSM"
- **Texto**: "Minimizar para área de notificação"
- **Estado inicial**: Carregado do `config.json` (padrão: marcado)
- **Comportamento**: Salva preferência automaticamente ao alterar

### **Menu do System Tray**
```
┌─────────────────────────┐
│ Mostrar                 │ ← Restaurar janela (duplo clique também)
├─────────────────────────┤
│ Status do Backend       │ ← Ver status e restaurar
├─────────────────────────┤
│ Sair                    │ ← Fechar completamente
└─────────────────────────┘
```

---

## ⚙️ Configuração

### **config.json**
```json
{
  "gui": {
    "minimize_to_tray": true
  }
}
```

### **Comportamento**
- `true`: Minimizar/fechar vai para tray
- `false`: Comportamento padrão (fechar fecha completamente)

---

## 🐛 Tratamento de Erros

### **Cenários de Fallback**

1. **`pystray` não instalado**
   - ✅ Checkbox não aparece na GUI
   - ✅ Sistema funciona normalmente (sem tray)
   - ✅ Log: "System tray não disponível"

2. **Erro ao criar ícone**
   - ✅ Usa ícone simples gerado automaticamente
   - ✅ Sistema continua funcionando

3. **Erro ao iniciar tray**
   - ✅ Fallback para comportamento padrão
   - ✅ Log de erro

---

## ✅ Checklist de Implementação

- [x] Criar `SystemTrayManager`
- [x] Integrar com `MainWindow`
- [x] Adicionar checkbox na GUI
- [x] Implementar salvar/carregar preferência
- [x] Implementar métodos mostrar/esconder
- [x] Modificar `on_closing()` para respeitar configuração
- [x] Adicionar `pystray` ao `requirements.txt`
- [x] Tratamento de erros robusto
- [ ] Testar funcionalidade completa

---

## 🚀 Como Usar

### **1. Instalar Dependência**
```bash
pip install pystray
```

### **2. Executar GUI**
```bash
python main.py --gui
```

### **3. Configurar**
1. Marcar/desmarcar checkbox "Minimizar para área de notificação"
2. Preferência é salva automaticamente

### **4. Usar**
- **Fechar janela (X)**: Se checkbox marcado → vai para tray
- **Duplo clique no ícone**: Restaura janela
- **Menu do tray**: Acessar opções

---

## 📚 Referências

- **pystray**: https://github.com/moses-palmer/pystray
- **Documentação**: https://pystray.readthedocs.io/

---

**Última Atualização**: 2025-12-16

