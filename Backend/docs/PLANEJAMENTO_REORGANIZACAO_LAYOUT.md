# Planejamento: Reorganização do Layout da GUI

## 📋 Proposta do Usuário

### Mudanças Solicitadas:

1. **Unir "Backend Status" e "Server Status" em um único card**
   - Reduzir largura do card
   - Manter botões Start/Stop dentro do card

2. **Mover API Key e Hash para linha acima dos logs**
   - Criar nova seção entre status e logs
   - API Key e Hash lado a lado

3. **Transformar botões em ícones**
   - "Control Panel" → ícone
   - "Site SSM" → ícone
   - Manter checkbox de System Tray

---

## 🎨 Layout Proposto

### **Estrutura Visual:**

```
┌─────────────────────────────────────────────────────────────┐
│                    [Logo + Título]                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────┐           │
│  │  Backend & Server Status                    │           │
│  │  ┌──────────────────┐  ┌─────────────────┐ │           │
│  │  │ Backend: ● Running│  │ Server: ● Online│ │           │
│  │  └──────────────────┘  └─────────────────┘ │           │
│  │  ┌──────────────────────────────────────┐ │           │
│  │  │  [Start]  [Stop]                       │ │           │
│  │  └──────────────────────────────────────┘ │           │
│  │  Next Restart: 2h 30m                      │           │
│  └──────────────────────────────────────────────┘           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐ │
│  │ API Key: [********] [👁][✏] │ Hash: [xxx] [📋]      │ │
│  └──────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Logs                                                  │ │
│  │ ┌──────────────────────────────────────────────────┐ │ │
│  │ │ [Log messages...]                                 │ │ │
│  │ └──────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  [🌐] [🌍] [☑]  (ícones: Control Panel, Site SSM, Tray)  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📐 Dimensões e Espaçamento

### **Card Unificado de Status:**
- **Largura**: ~600-650px (reduzido de ~900px)
- **Altura**: ~180-200px
- **Layout interno**: Grid 2x2
  - Linha 1: Backend Status | Server Status
  - Linha 2: Botões Start/Stop (centralizados)
  - Linha 3: Next Restart (opcional, abaixo dos botões)

### **Seção API Key + Hash:**
- **Posição**: Entre status e logs
- **Layout**: Lado a lado com espaçamento adequado
- **API Key**: ~400px
- **Hash**: ~200px + botão copiar

### **Footer Simplificado:**
- **Apenas ícones**: 3 botões pequenos (40x40px)
- **Espaçamento**: 10px entre ícones

---

## 🔧 Implementação Técnica

### **1. Card Unificado de Status**

**Estrutura:**
```python
# Card único para ambos os status
unified_status_frame = ctk.CTkFrame(self)
unified_status_frame.pack(pady=10, padx=20, fill="x")

# Título do card
status_title = ctk.CTkLabel(unified_status_frame, text="Status", ...)

# Container interno com grid
status_grid = ctk.CTkFrame(unified_status_frame, fg_color="transparent")

# Linha 1: Backend e Server lado a lado
backend_status_mini = ...  # Versão compacta
server_status_mini = ...   # Versão compacta

# Linha 2: Botões Start/Stop centralizados
control_buttons = ctk.CTkFrame(status_grid, fg_color="transparent")
# Botões menores: width=80, height=28
```

### **2. Seção API Key + Hash**

**Estrutura:**
```python
# Nova seção entre status e logs
credentials_frame = ctk.CTkFrame(self, fg_color="transparent")
credentials_frame.pack(pady=10, padx=20, fill="x")

# API Key (esquerda)
apikey_section = ctk.CTkFrame(credentials_frame, ...)
# Hash (direita)
hash_section = ctk.CTkFrame(credentials_frame, ...)
```

### **3. Footer com Ícones**

**Estrutura:**
```python
# Footer simplificado
footer_frame = ctk.CTkFrame(self, fg_color="transparent")
footer_frame.pack(pady=10, padx=20, fill="x")

# Ícone Control Panel
control_panel_icon = IconHelper.load_icon('settings', ...)  # ou 'dashboard'
btn_control_panel = ctk.CTkButton(
    footer_frame,
    image=control_panel_icon,
    text="",
    width=40,
    height=40,
    command=self._open_frontend
)
# Tooltip: "Control Panel"

# Ícone Site SSM
site_icon = IconHelper.load_icon('globe', ...)  # ou criar novo
btn_site = ctk.CTkButton(
    footer_frame,
    image=site_icon,
    text="",
    width=40,
    height=40,
    command=self._open_site
)
# Tooltip: "Site SSM"

# Checkbox Tray (já existe)
```

---

## 🎯 Alternativas e Melhorias

### **Alternativa 1: Card de Status Mais Compacto**

**Layout Vertical:**
```
┌─────────────────────────────┐
│ Backend: ● Running           │
│ Server: ● Online            │
│ [Start] [Stop]              │
│ Next Restart: 2h 30m        │
└─────────────────────────────┘
```

**Vantagens:**
- Mais compacto
- Economiza espaço vertical
- Mais fácil de ler

### **Alternativa 2: Botões Start/Stop como Ícones**

**Mudança:**
- Start: ícone ▶ (play)
- Stop: ícone ■ (stop)

**Vantagens:**
- Mais espaço no card
- Visual mais moderno
- Consistente com footer

### **Alternativa 3: API Key e Hash em Cards Separados**

**Layout:**
```
┌──────────────────┐  ┌──────────────────┐
│ API Key          │  │ Hash              │
│ [********] [👁][✏]│  │ [xxx] [📋]        │
└──────────────────┘  └──────────────────┘
```

**Vantagens:**
- Visual mais organizado
- Melhor separação visual
- Mais fácil de identificar

### **Alternativa 4: Footer com Menu Dropdown**

**Layout:**
```
[⚙] [🌍] [☑]
  ↓
Menu com opções:
- Control Panel
- Site SSM
- Settings
- About
```

**Vantagens:**
- Mais opções sem ocupar espaço
- Escalável para futuras funcionalidades

---

## 📊 Comparação de Espaço

### **Layout Atual:**
- Status cards: ~900px (2 cards lado a lado)
- Footer: ~900px (botões + API Key + Hash)
- **Total horizontal**: ~900px

### **Layout Proposto:**
- Status card: ~600px (unificado)
- API Key + Hash: ~900px (linha separada)
- Footer: ~150px (apenas ícones)
- **Total horizontal**: ~900px (melhor distribuído)

### **Ganho de Espaço Vertical:**
- Status: -50px (card unificado é mais compacto)
- Footer: -30px (ícones são menores)
- **Total**: ~80px economizados

---

## ✅ Checklist de Implementação

### **Fase 1: Card Unificado**
- [ ] Criar `unified_status_frame`
- [ ] Mover Backend Status para dentro
- [ ] Mover Server Status para dentro
- [ ] Reorganizar layout interno (grid)
- [ ] Reduzir tamanho dos botões Start/Stop
- [ ] Testar responsividade

### **Fase 2: Seção API Key + Hash**
- [ ] Criar `credentials_frame` entre status e logs
- [ ] Mover API Key para nova seção
- [ ] Mover Hash para nova seção
- [ ] Ajustar larguras para caber lado a lado
- [ ] Testar com diferentes tamanhos de texto

### **Fase 3: Footer Simplificado**
- [ ] Verificar/criar ícones para Control Panel e Site SSM
- [ ] Converter botões em ícones
- [ ] Adicionar tooltips
- [ ] Manter checkbox de System Tray
- [ ] Testar cliques e tooltips

### **Fase 4: Ajustes Finais**
- [ ] Ajustar espaçamentos
- [ ] Verificar alinhamentos
- [ ] Testar em diferentes resoluções
- [ ] Validar acessibilidade (tooltips)

---

## 🎨 Ícones Necessários

### **Ícones a Verificar/Criar:**

1. **Control Panel**:
   - Opções: `settings`, `dashboard`, `control`
   - Fallback: ⚙ (Unicode)

2. **Site SSM**:
   - Opções: `globe`, `web`, `link`, `external`
   - Fallback: 🌍 (Unicode)

3. **Start** (opcional):
   - Opções: `play`, `start`
   - Fallback: ▶ (Unicode)

4. **Stop** (opcional):
   - Opções: `stop`, `square`
   - Fallback: ■ (Unicode)

---

## 💡 Sugestões Adicionais

### **Sugestão 1: Card de Status com Abas**
```
┌─────────────────────────────┐
│ [Backend] [Server] [Config] │
│ Backend: ● Running           │
│ [Start] [Stop]               │
└─────────────────────────────┘
```

### **Sugestão 2: Status em Formato de Lista**
```
┌─────────────────────────────┐
│ Status                      │
│ • Backend: ● Running        │
│ • Server: ● Online          │
│ • Next Restart: 2h 30m      │
│ [Start] [Stop]              │
└─────────────────────────────┘
```

### **Sugestão 3: API Key e Hash com Labels Flutuantes**
```
┌─────────────────────────────┐
│ API Key                     │
│ [****************] [👁][✏]  │
└─────────────────────────────┘
┌─────────────────────────────┐
│ Hash                        │
│ [xxx] [📋]                  │
└─────────────────────────────┘
```

---

## 🚀 Próximos Passos

1. ⏳ Revisar planejamento com usuário
2. ⏳ Escolher alternativas (se houver)
3. ⏳ Verificar disponibilidade de ícones
4. ⏳ Implementar mudanças
5. ⏳ Testar layout

---

## 📝 Notas de Implementação

- **CustomTkinter não tem grid nativo**: Usar `pack` com frames aninhados
- **Responsividade**: Considerar largura mínima da janela
- **Tooltips**: Essenciais para ícones sem texto
- **Acessibilidade**: Manter labels descritivas mesmo com ícones

