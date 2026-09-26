# 📋 Planejamento: Minimizar para Área de Notificação (System Tray)

## 🎯 Objetivo

Implementar funcionalidade para minimizar a GUI para a área de notificação (system tray) do Windows, permitindo que o aplicativo continue rodando em segundo plano sem ocupar espaço na barra de tarefas.

---

## 📦 Dependências Necessárias

### **Biblioteca Principal: `pystray`**
```bash
pip install pystray
```

**Por que `pystray`?**
- ✅ Biblioteca multiplataforma (Windows, Linux, macOS)
- ✅ Suporta ícones e menus de contexto
- ✅ Thread-safe
- ✅ Bem mantida e documentada

### **Dependências Adicionais**
- `Pillow` (já usado no projeto) - Para manipular imagens do ícone
- `threading` (já usado) - Para executar o system tray em thread separada

---

## 🏗️ Arquitetura da Solução

### **Componentes Necessários**

1. **`SystemTrayManager`** (nova classe)
   - Gerencia o ícone do system tray
   - Controla menu de contexto
   - Gerencia ciclo de vida do tray

2. **Modificações em `MainWindow`**
   - Interceptar evento de minimizar
   - Interceptar evento de fechar
   - Integrar com `SystemTrayManager`

3. **Ícone do System Tray**
   - Usar ícone existente (ou criar versão 16x16/32x32)
   - Suportar diferentes estados (normal, notificação)

---

## 🔧 Implementação Detalhada

### **1. Criar `SystemTrayManager`**

**Arquivo**: `gui/system_tray_manager.py`

**Responsabilidades**:
- Criar e gerenciar ícone do system tray
- Criar menu de contexto com opções:
  - "Mostrar" / "Restaurar"
  - "Sair"
  - (Opcional) "Status do Backend"
- Thread-safe para comunicação com GUI

**Estrutura**:
```python
class SystemTrayManager:
    def __init__(self, main_window, icon_path, on_show, on_quit):
        self.main_window = main_window
        self.icon_path = icon_path
        self.on_show = on_show
        self.on_quit = on_quit
        self.tray_icon = None
        self.tray_thread = None
        self.is_running = False
    
    def start(self):
        """Iniciar system tray em thread separada"""
    
    def stop(self):
        """Parar system tray"""
    
    def show_notification(self, title, message):
        """Mostrar notificação do system tray"""
    
    def update_icon(self, icon_path):
        """Atualizar ícone do tray"""
```

### **2. Modificar `MainWindow`**

**Mudanças necessárias**:

#### **A. Adicionar variáveis de controle**
```python
self.minimize_to_tray = True  # Configurável
self.system_tray_manager = None
self.is_minimized_to_tray = False
```

#### **B. Interceptar evento de minimizar**
```python
def _on_minimize(self, event=None):
    """Handler quando janela é minimizada"""
    if self.minimize_to_tray:
        self.hide_window_to_tray()
    else:
        # Comportamento padrão: minimizar para barra de tarefas
        pass
```

#### **C. Interceptar evento de fechar**
```python
def on_closing(self):
    """Handler chamado quando a janela é fechada"""
    if self.minimize_to_tray:
        # Se configurado, minimizar para tray em vez de fechar
        self.hide_window_to_tray()
    else:
        # Fechar normalmente
        self._force_stop_backend()
        self.destroy()
```

#### **D. Métodos auxiliares**
```python
def hide_window_to_tray(self):
    """Esconder janela e mostrar no system tray"""
    self.withdraw()  # Esconder janela
    self.is_minimized_to_tray = True
    if self.system_tray_manager:
        self.system_tray_manager.show_notification(
            "SSM Backend",
            "Aplicativo minimizado para área de notificação"
        )

def show_window_from_tray(self):
    """Restaurar janela do system tray"""
    self.deiconify()  # Mostrar janela
    self.lift()  # Trazer para frente
    self.focus_force()  # Focar na janela
    self.is_minimized_to_tray = False
```

### **3. Menu de Contexto do System Tray**

**Opções do Menu**:
```
┌─────────────────────────┐
│ Mostrar                 │ ← Restaurar janela
├─────────────────────────┤
│ Status do Backend       │ ← (Opcional) Mostrar status
├─────────────────────────┤
│ Sair                    │ ← Fechar aplicativo completamente
└─────────────────────────┘
```

**Implementação**:
```python
def _create_tray_menu(self):
    """Criar menu de contexto do system tray"""
    menu = pystray.Menu(
        pystray.MenuItem(
            "Mostrar",
            self._on_tray_show,
            default=True  # Duplo clique também executa esta ação
        ),
        pystray.MenuItem(
            "Status do Backend",
            self._on_tray_status,
            enabled=self.backend_running
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Sair",
            self._on_tray_quit
        )
    )
    return menu
```

---

## 🎨 Interface do Usuário

### **Opção 1: Minimizar para Tray (Padrão)**
- **Botão Minimizar**: Minimiza para system tray
- **Botão Fechar (X)**: Minimiza para system tray (se configurado)
- **Duplo clique no ícone**: Restaura janela

### **Opção 2: Configurável**
- **Checkbox na GUI**: "Minimizar para área de notificação"
- **Se marcado**: Minimizar/fechar vai para tray
- **Se desmarcado**: Comportamento padrão do Windows

### **Notificações do System Tray**
- Quando minimiza: "SSM Backend minimizado para área de notificação"
- Quando backend inicia: "Backend iniciado com sucesso"
- Quando backend para: "Backend parado"
- (Opcional) Erros críticos

---

## 🔄 Fluxo de Funcionamento

### **Cenário 1: Minimizar para Tray**
```
1. Usuário clica em "Minimizar" ou fecha janela
   ↓
2. MainWindow.hide_window_to_tray() é chamado
   ↓
3. Janela é escondida (withdraw())
   ↓
4. SystemTrayManager mostra ícone na área de notificação
   ↓
5. Notificação é exibida: "Minimizado para área de notificação"
   ↓
6. Aplicativo continua rodando em segundo plano
```

### **Cenário 2: Restaurar do Tray**
```
1. Usuário clica em "Mostrar" no menu OU duplo clica no ícone
   ↓
2. SystemTrayManager._on_tray_show() é chamado
   ↓
3. MainWindow.show_window_from_tray() é chamado
   ↓
4. Janela é restaurada (deiconify())
   ↓
5. Janela é trazida para frente (lift(), focus_force())
```

### **Cenário 3: Sair do Tray**
```
1. Usuário clica em "Sair" no menu
   ↓
2. SystemTrayManager._on_tray_quit() é chamado
   ↓
3. MainWindow.on_closing() é chamado (com force_quit=True)
   ↓
4. Backend é parado
   ↓
5. SystemTrayManager é parado
   ↓
6. Aplicativo fecha completamente
```

---

## 📝 Estrutura de Arquivos

### **Novos Arquivos**
```
gui/
├── system_tray_manager.py  ← NOVO: Gerenciador do system tray
└── main_window.py           ← MODIFICADO: Integração com system tray
```

### **Modificações em Arquivos Existentes**
- `gui/main_window.py`: Adicionar integração com SystemTrayManager
- `requirements.txt`: Adicionar `pystray`

---

## ⚙️ Configuração

### **Opção 1: Hardcoded (Simples)**
```python
# Sempre minimizar para tray
self.minimize_to_tray = True
```

### **Opção 2: Configurável via config.json**
```json
{
  "gui": {
    "minimize_to_tray": true,
    "close_to_tray": true,
    "show_tray_notifications": true
  }
}
```

### **Opção 3: Checkbox na GUI**
- Adicionar checkbox em "Configurações"
- Salvar preferência do usuário

---

## 🐛 Tratamento de Erros

### **Cenários de Erro**

1. **`pystray` não instalado**
   - Fallback: Comportamento padrão (minimizar para barra de tarefas)
   - Log: "System tray não disponível, usando comportamento padrão"

2. **Erro ao criar ícone**
   - Fallback: Usar ícone padrão do Windows
   - Log: "Erro ao carregar ícone do tray, usando padrão"

3. **Erro ao criar menu**
   - Fallback: Menu mínimo (apenas "Sair")
   - Log: "Erro ao criar menu do tray"

---

## ✅ Checklist de Implementação

### **Fase 1: Preparação**
- [ ] Instalar `pystray` e verificar dependências
- [ ] Criar ícone 16x16 e 32x32 para system tray
- [ ] Testar `pystray` em ambiente isolado

### **Fase 2: Implementação Base**
- [ ] Criar `SystemTrayManager` básico
- [ ] Implementar criação de ícone
- [ ] Implementar menu básico (Mostrar, Sair)
- [ ] Integrar com `MainWindow`

### **Fase 3: Funcionalidades**
- [ ] Implementar minimizar para tray
- [ ] Implementar restaurar do tray
- [ ] Implementar fechar para tray
- [ ] Implementar notificações

### **Fase 4: Melhorias**
- [ ] Adicionar opção "Status do Backend" no menu
- [ ] Adicionar configuração (checkbox)
- [ ] Adicionar tratamento de erros robusto
- [ ] Testar em diferentes cenários

### **Fase 5: Testes**
- [ ] Testar minimizar/restaurar
- [ ] Testar fechar/restaurar
- [ ] Testar duplo clique no ícone
- [ ] Testar menu de contexto
- [ ] Testar notificações
- [ ] Testar com backend rodando/parado

---

## 🎯 Benefícios

1. **Melhor UX**: Aplicativo não ocupa espaço na barra de tarefas
2. **Acesso Rápido**: Duplo clique restaura janela rapidamente
3. **Notificações**: Usuário pode ser notificado de eventos importantes
4. **Profissional**: Comportamento esperado em aplicações modernas

---

## 📚 Referências

- **pystray**: https://github.com/moses-palmer/pystray
- **Documentação**: https://pystray.readthedocs.io/
- **Exemplos**: https://github.com/moses-palmer/pystray/tree/master/examples

---

## 🔄 Próximos Passos

1. **Aprovar planejamento**
2. **Instalar dependências**
3. **Criar `SystemTrayManager`**
4. **Integrar com `MainWindow`**
5. **Testar funcionalidade**
6. **Adicionar configurações (opcional)**

---

**Última Atualização**: 2025-12-16

