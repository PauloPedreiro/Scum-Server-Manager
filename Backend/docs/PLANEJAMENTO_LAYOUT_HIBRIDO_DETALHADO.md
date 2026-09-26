# Planejamento Detalhado: Layout Híbrido (Top Bar + Sidebar)

## 🎨 Proposta 6: Layout Híbrido - Variações

### **Estrutura Base:**
- **Top Bar**: Logo + controles rápidos + botões de janela
- **Sidebar Esquerda**: Controles principais (Start/Stop, ícones)
- **Área Principal**: Conteúdo dinâmico

---

## 📐 Variação 1: API Key e Hash Empilhados

### **Visual:**
```
┌─────────────────────────────────────────────────────────────┐
│ [Logo]  SSM Backend v3.1.0          [⚙][🌍][☑] [─][□][×]   │
├────┬────────────────────────────────────────────────────────┤
│[▶]│                                                         │
│[■]│  ┌──────────────────────────────────────────────────┐   │
│────│  │ Status: Backend ● │ Server ● │ Next: 2h 30m    │   │
│[⚙]│  └──────────────────────────────────────────────────┘   │
│[🌍]│                                                         │
│[☑]│  ┌──────────────────────────────────────────────────┐   │
│────│  │ API Key                                          │   │
│    │  │ [****************] [👁][✏]                      │   │
│    │  └──────────────────────────────────────────────────┘   │
│    │                                                          │
│    │  ┌──────────────────────────────────────────────────┐   │
│    │  │ Hash                                              │   │
│    │  │ [xxx] [📋]                                        │   │
│    │  └──────────────────────────────────────────────────┘   │
│    │                                                          │
│    │  ┌──────────────────────────────────────────────────┐   │
│    │  │ Logs                                              │   │
│    │  │ [Log messages...]                                 │   │
│    │  └──────────────────────────────────────────────────┘   │
└────┴─────────────────────────────────────────────────────────┘
```

### **Características:**
- ✅ API Key em card próprio acima
- ✅ Hash em card próprio abaixo
- ✅ Cada um ocupa largura total
- ✅ Melhor legibilidade
- ✅ Mais espaço para cada campo

### **Vantagens:**
- ✅ Campos não competem por espaço
- ✅ API Key pode ser mais largo
- ✅ Hash tem espaço próprio
- ✅ Visual mais organizado

---

## 📐 Variação 2: Tab para Credentials

### **Visual:**
```
┌─────────────────────────────────────────────────────────────┐
│ [Logo]  SSM Backend v3.1.0          [⚙][🌍][☑] [─][□][×]   │
├────┬────────────────────────────────────────────────────────┤
│[▶]│                                                         │
│[■]│  ┌──────────────────────────────────────────────────┐   │
│────│  │ Status: Backend ● │ Server ● │ Next: 2h 30m    │   │
│[⚙]│  └──────────────────────────────────────────────────┘   │
│[🌍]│                                                         │
│[☑]│  [Status] [Credentials] [Logs]                         │
│────│  ┌──────────────────────────────────────────────────┐   │
│    │  │ Credentials Tab                                   │   │
│    │  │ ┌──────────────────────────────────────────────┐ │   │
│    │  │ │ API Key                                       │ │   │
│    │  │ │ [****************] [👁][✏]                  │ │   │
│    │  │ └──────────────────────────────────────────────┘ │   │
│    │  │ ┌──────────────────────────────────────────────┐ │   │
│    │  │ │ Hash                                         │ │   │
│    │  │ │ [xxx] [📋]                                   │ │   │
│    │  │ └──────────────────────────────────────────────┘ │   │
│    │  └──────────────────────────────────────────────────┘   │
└────┴─────────────────────────────────────────────────────────┘
```

### **Características:**
- ✅ Tab "Credentials" na área principal
- ✅ Quando ativa: mostra API Key e Hash
- ✅ Quando inativa: área fica disponível para logs
- ✅ Navegação por tabs

### **Vantagens:**
- ✅ Credentials ficam ocultos quando não necessários
- ✅ Mais espaço para logs quando Credentials não está ativa
- ✅ Organização por categorias
- ✅ Visual limpo

---

## 📐 Variação 3: Tab + Empilhados (Híbrido)

### **Visual:**
```
┌─────────────────────────────────────────────────────────────┐
│ [Logo]  SSM Backend v3.1.0          [⚙][🌍][☑] [─][□][×]   │
├────┬────────────────────────────────────────────────────────┤
│[▶]│                                                         │
│[■]│  ┌──────────────────────────────────────────────────┐   │
│────│  │ Status: Backend ● │ Server ● │ Next: 2h 30m    │   │
│[⚙]│  └──────────────────────────────────────────────────┘   │
│[🌍]│                                                         │
│[☑]│  [Status] [Credentials] [Logs]                         │
│────│  ┌──────────────────────────────────────────────────┐   │
│    │  │ Credentials Tab (quando ativa)                   │   │
│    │  │ ┌──────────────────────────────────────────────┐ │   │
│    │  │ │ API Key                                       │ │   │
│    │  │ │ [****************] [👁][✏]                  │ │   │
│    │  │ └──────────────────────────────────────────────┘ │   │
│    │  │ ┌──────────────────────────────────────────────┐ │   │
│    │  │ │ Hash                                         │ │   │
│    │  │ │ [xxx] [📋]                                   │ │   │
│    │  │ └──────────────────────────────────────────────┘ │   │
│    │  └──────────────────────────────────────────────────┘   │
│    │                                                          │
│    │  ┌──────────────────────────────────────────────────┐   │
│    │  │ Logs Tab (quando ativa)                          │   │
│    │  │ [Log messages...]                                 │   │
│    │  └──────────────────────────────────────────────────┘   │
└────┴─────────────────────────────────────────────────────────┘
```

### **Características:**
- ✅ Tabs na área principal
- ✅ Tab Credentials: API Key e Hash empilhados
- ✅ Tab Logs: Área de logs expandida
- ✅ Tab Status: Status detalhado (opcional)

---

## 📐 Variação 4: Credentials em Sidebar (Expandida)

### **Visual:**
```
┌─────────────────────────────────────────────────────────────┐
│ [Logo]  SSM Backend v3.1.0          [⚙][🌍][☑] [─][□][×]   │
├──────┬───────────────────────────────────────────────────────┤
│ [▶]  │                                                       │
│ [■]  │  ┌────────────────────────────────────────────────┐   │
│──────│  │ Status: Backend ● │ Server ● │ Next: 2h 30m  │   │
│ [⚙]  │  └────────────────────────────────────────────────┘   │
│ [🌍] │                                                         │
│ [☑] │  ┌────────────────────────────────────────────────┐   │
│──────│  │ Logs                                            │   │
│ API  │  │ [Log messages...]                              │   │
│ Key: │  └────────────────────────────────────────────────┘   │
│ [***]│                                                       │
│ [👁] │                                                       │
│ [✏] │                                                       │
│──────│                                                       │
│ Hash:│                                                       │
│ [xxx]│                                                       │
│ [📋] │                                                       │
└──────┴───────────────────────────────────────────────────────┘
```

### **Características:**
- ✅ Sidebar expandida (150-180px)
- ✅ Controles no topo da sidebar
- ✅ Credentials no meio da sidebar
- ✅ Área principal só para logs

---

## 🎯 Comparação das Variações

| Variação | Espaço Logs | Acesso Credentials | Visual | Complexidade |
|----------|-------------|-------------------|--------|--------------|
| **1. Empilhados** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **2. Tab** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **3. Tab+Empilhados** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **4. Sidebar Expandida** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

---

## 💡 Recomendação: Variação 3 (Tab + Empilhados)

### **Por quê?**
1. ✅ **Melhor dos dois mundos**: Tab organiza, empilhados dão espaço
2. ✅ **Flexibilidade**: Usuário escolhe quando ver credentials
3. ✅ **Mais espaço para logs**: Quando Credentials não está ativa
4. ✅ **Visual limpo**: Organização por categorias
5. ✅ **Escalável**: Fácil adicionar novas tabs

---

## 🔧 Implementação Detalhada

### **Estrutura de Tabs:**

```python
# Container de tabs na área principal
tabs_container = ctk.CTkFrame(main_content, fg_color="transparent")
tabs_container.pack(fill="both", expand=True, padx=10, pady=10)

# Barra de tabs
tabs_bar = ctk.CTkFrame(tabs_container, fg_color="transparent")
tabs_bar.pack(fill="x", pady=(0, 10))

# Botões de tab
self.tab_buttons = {}
tabs = [
    ("Status", "status"),
    ("Credentials", "credentials"),
    ("Logs", "logs")
]

for tab_name, tab_id in tabs:
    btn = ctk.CTkButton(
        tabs_bar,
        text=tab_name,
        command=lambda t=tab_id: self._switch_tab(t),
        width=120,
        height=35,
        fg_color=("gray", "gray") if tab_id != "logs" else ("blue", "blue")
    )
    btn.pack(side="left", padx=5)
    self.tab_buttons[tab_id] = btn

# Conteúdo das tabs
self.tabs_content = {}
for tab_id in ["status", "credentials", "logs"]:
    content_frame = ctk.CTkFrame(tabs_container, fg_color="transparent")
    content_frame.pack(fill="both", expand=True)
    self.tabs_content[tab_id] = content_frame

# Inicialmente mostrar tab de Logs
self._switch_tab("logs")
```

### **Tab Credentials com API Key e Hash Empilhados:**

```python
def _create_credentials_tab(self):
    """Criar tab de Credentials"""
    credentials_frame = self.tabs_content["credentials"]
    
    # Card API Key
    apikey_card = ctk.CTkFrame(credentials_frame)
    apikey_card.pack(fill="x", pady=(0, 10), padx=10)
    
    apikey_label = ctk.CTkLabel(apikey_card, text="API Key:", ...)
    apikey_label.pack(side="left", padx=10)
    
    self.main_apikey_entry = ctk.CTkEntry(
        apikey_card,
        width=500,  # Largura maior já que está sozinho
        ...
    )
    self.main_apikey_entry.pack(side="left", padx=5, fill="x", expand=True)
    
    # Botões API Key
    self.btn_toggle_apikey_main.pack(side="left", padx=2)
    self.btn_save_edit_apikey.pack(side="left", padx=2)
    
    # Card Hash
    hash_card = ctk.CTkFrame(credentials_frame)
    hash_card.pack(fill="x", pady=(0, 10), padx=10)
    
    hash_label = ctk.CTkLabel(hash_card, text="Hash:", ...)
    hash_label.pack(side="left", padx=10)
    
    self.hash_entry = ctk.CTkEntry(
        hash_card,
        width=500,
        ...
    )
    self.hash_entry.pack(side="left", padx=5, fill="x", expand=True)
    
    # Botão copiar Hash
    self.btn_copy.pack(side="left", padx=2)
```

### **Tab Logs:**

```python
def _create_logs_tab(self):
    """Criar tab de Logs"""
    logs_frame = self.tabs_content["logs"]
    
    # Área de logs expandida
    self.logs_textbox = ctk.CTkTextbox(
        logs_frame,
        height=400,  # Altura maior já que tem mais espaço
        ...
    )
    self.logs_textbox.pack(fill="both", expand=True, padx=10, pady=10)
```

### **Tab Status (Opcional):**

```python
def _create_status_tab(self):
    """Criar tab de Status (detalhado)"""
    status_frame = self.tabs_content["status"]
    
    # Status detalhado com mais informações
    # Pode incluir gráficos, estatísticas, etc.
```

---

## 🎨 Design das Tabs

### **Estilo:**
- **Tab ativa**: Cor azul/primária, texto em negrito
- **Tab inativa**: Cor cinza, texto normal
- **Transição**: Suave ao trocar de tab
- **Hover**: Efeito hover nos botões de tab

### **Implementação de Switch:**

```python
def _switch_tab(self, tab_id: str):
    """Trocar tab ativa"""
    # Esconder todas as tabs
    for content in self.tabs_content.values():
        content.pack_forget()
    
    # Mostrar tab selecionada
    self.tabs_content[tab_id].pack(fill="both", expand=True)
    
    # Atualizar estilo dos botões
    for tid, btn in self.tab_buttons.items():
        if tid == tab_id:
            btn.configure(fg_color=("blue", "blue"), font=ctk.CTkFont(weight="bold"))
        else:
            btn.configure(fg_color=("gray", "gray"), font=ctk.CTkFont(weight="normal"))
```

---

## 📊 Layout Final Recomendado

### **Estrutura Completa:**

```
┌─────────────────────────────────────────────────────────────┐
│ [Logo]  SSM Backend v3.1.0          [⚙][🌍][☑] [─][□][×]   │
├────┬────────────────────────────────────────────────────────┤
│[▶]│                                                         │
│[■]│  ┌──────────────────────────────────────────────────┐   │
│────│  │ Status Overview (sempre visível)                │   │
│[⚙]│  │ Backend: ● Running │ Server: ● Online           │   │
│[🌍]│  │ Next Restart: 2h 30m                            │   │
│[☑]│  └──────────────────────────────────────────────────┘   │
│────│                                                         │
│    │  [Status] [Credentials] [Logs]                         │
│    │  ┌──────────────────────────────────────────────────┐   │
│    │  │ Conteúdo da Tab Ativa                            │   │
│    │  │                                                  │   │
│    │  │ Tab Credentials:                                 │   │
│    │  │ ┌──────────────────────────────────────────────┐ │   │
│    │  │ │ API Key                                       │ │   │
│    │  │ │ [****************] [👁][✏]                  │ │   │
│    │  │ └──────────────────────────────────────────────┘ │   │
│    │  │ ┌──────────────────────────────────────────────┐ │   │
│    │  │ │ Hash                                         │ │   │
│    │  │ │ [xxx] [📋]                                   │ │   │
│    │  │ └──────────────────────────────────────────────┘ │   │
│    │  │                                                  │   │
│    │  │ Tab Logs:                                       │   │
│    │  │ [Log messages...]                               │   │
│    │  └──────────────────────────────────────────────────┘   │
└────┴─────────────────────────────────────────────────────────┘
```

---

## ✅ Vantagens da Variação 3 (Tab + Empilhados)

1. ✅ **Organização clara**: Cada categoria em sua tab
2. ✅ **Mais espaço**: Logs têm área expandida quando Credentials não está ativa
3. ✅ **API Key e Hash empilhados**: Cada um com espaço próprio
4. ✅ **Flexível**: Usuário escolhe o que ver
5. ✅ **Escalável**: Fácil adicionar novas tabs (Settings, About, etc.)

---

## 🚀 Próximos Passos

1. ⏳ Confirmar variação escolhida
2. ⏳ Implementar estrutura base (Top Bar + Sidebar)
3. ⏳ Implementar sistema de tabs
4. ⏳ Criar tab Credentials (API Key + Hash empilhados)
5. ⏳ Criar tab Logs
6. ⏳ Testar navegação entre tabs

---

## 💭 Outras Ideias para Credentials

### **Opção A: Accordion (Expansível)**
- Card que expande/colapsa ao clicar
- Mostra API Key e Hash quando expandido

### **Opção B: Modal/Dialog**
- Botão "Credentials" abre janela modal
- API Key e Hash dentro do modal

### **Opção C: Dropdown no Top Bar**
- Menu dropdown no topo
- Credentials aparecem no dropdown

---

## 📋 Resumo das Opções

| Opção | Espaço | Acesso | Visual | Recomendado |
|-------|--------|--------|--------|-------------|
| **Empilhados** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Sim |
| **Tab** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Sim |
| **Tab+Empilhados** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅✅ **Melhor** |
| **Sidebar Expandida** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⚠️ Ocupa espaço |

---

## 🎯 Recomendação Final

**Variação 3: Tab + Empilhados** é a melhor opção porque:
- Combina organização (tabs) com espaço (empilhados)
- Credentials ficam ocultos quando não necessários
- Logs têm mais espaço quando Credentials não está ativa
- Visual moderno e profissional
- Escalável para futuras funcionalidades

