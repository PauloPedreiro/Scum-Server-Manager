# Planejamento: Barra de Título Customizada com Botão de Minimizar para Tray

## Objetivo
Substituir o checkbox "Minimizar para área de notificação" do footer por um botão na barra de título da janela, junto com os botões padrão (minimizar, maximizar, fechar).

## Análise da Situação Atual

### Estrutura Atual
- **Checkbox no footer**: Localizado em `footer_buttons_frame`, junto com botões "Control Panel" e "Site SSM"
- **Posição**: Linha 718-725 em `gui/main_window.py`
- **Comportamento**: Checkbox que habilita/desabilita minimizar para tray

### Limitações do CustomTkinter
- CustomTkinter não fornece acesso direto aos botões da barra de título do sistema
- No Windows, precisamos usar `overrideredirect(True)` para criar uma barra de título completamente customizada
- Isso remove TODOS os botões padrão (minimizar, maximizar, fechar), então precisamos recriar todos

## Solução Proposta

### Opção Escolhida: Barra de Título Customizada Completa

**Vantagens:**
- Controle total sobre o design
- Botão de minimizar para tray integrado naturalmente
- Consistência visual com o tema dark
- Experiência de usuário mais profissional

**Desvantagens:**
- Mais código para manter
- Precisa implementar arrastar janela manualmente
- Precisa recriar todos os botões (minimizar, maximizar, fechar)

### Estrutura da Barra de Título

```
┌─────────────────────────────────────────────────────────────┐
│ [Logo]  SSM Backend v3.1.0 - Status and Licensing  [─][□][×]│
│                                                              │
│  └─ Botão Minimizar para Tray (quando habilitado)          │
└─────────────────────────────────────────────────────────────┘
```

**Botões da Barra de Título (da esquerda para direita):**
1. **Minimizar para Tray** (`_`) - Apenas quando `minimize_to_tray = True`
2. **Minimizar** (`─`) - Minimiza para barra de tarefas
3. **Maximizar** (`□`) - Maximiza/restaura janela (pode ser desabilitado se `resizable=False`)
4. **Fechar** (`×`) - Fecha a janela

## Implementação Técnica

### 1. Modificar Configuração da Janela

**Arquivo**: `gui/main_window.py`

**Mudanças**:
- Adicionar `self.overrideredirect(True)` após criar a janela
- Criar frame para barra de título customizada
- Implementar arrastar janela manualmente

```python
# No __init__, após self.geometry():
self.overrideredirect(True)  # Remove barra de título padrão
```

### 2. Criar Frame da Barra de Título

**Estrutura**:
```python
def _create_title_bar(self):
    """Criar barra de título customizada"""
    title_bar = ctk.CTkFrame(
        self,
        height=35,  # Altura padrão de barra de título
        fg_color=("#2b2b2b", "#1a1a1a"),  # Cor escura
        corner_radius=0
    )
    title_bar.pack(fill="x", side="top")
    
    # Logo pequeno (opcional)
    # Título
    # Botões de controle (lado direito)
```

### 3. Implementar Botões da Barra de Título

**Botão Minimizar para Tray** (`_`):
- Só aparece se `minimize_to_tray = True`
- Ícone: `_` (underscore) ou ícone customizado
- Comando: `self.minimize_to_tray_action()`

**Botão Minimizar** (`─`):
- Ícone: `─` (dash) ou ícone customizado
- Comando: `self.iconify()` (minimiza para barra de tarefas)

**Botão Maximizar** (`□`):
- Pode ser desabilitado se `resizable=False`
- Ícone: `□` (square) ou ícone customizado
- Comando: Alternar entre maximizado/restaurado

**Botão Fechar** (`×`):
- Ícone: `×` (times) ou ícone customizado
- Comando: `self.on_closing()`

### 4. Implementar Arrastar Janela

**Código necessário**:
```python
def _start_move(self, event):
    """Iniciar movimento da janela"""
    self._x = event.x
    self._y = event.y

def _on_move(self, event):
    """Mover janela durante arrasto"""
    x = self.winfo_x() + event.x - self._x
    y = self.winfo_y() + event.y - self._y
    self.geometry(f"+{x}+{y}")
```

**Aplicar na barra de título**:
```python
title_bar.bind("<Button-1>", self._start_move)
title_bar.bind("<B1-Motion>", self._on_move)
```

### 5. Remover Checkbox do Footer

**Mudanças**:
- Remover código do checkbox (linhas 716-727)
- Manter lógica de `minimize_to_tray` e `_on_tray_checkbox_changed`
- Adaptar `_on_tray_checkbox_changed` para ser chamado quando botão é clicado

### 6. Atualizar Métodos Existentes

**`_on_tray_checkbox_changed`** → Renomear para `_on_tray_button_clicked`:
- Alternar estado de `minimize_to_tray`
- Atualizar visibilidade do botão na barra de título
- Salvar preferência no config

**`on_closing`**: Manter como está (já funciona corretamente)

## Estrutura de Arquivos Modificados

### `gui/main_window.py`
- Adicionar método `_create_title_bar()`
- Adicionar métodos `_start_move()` e `_on_move()` para arrastar
- Modificar `__init__()` para criar barra de título
- Remover checkbox do `_create_widgets()`
- Adicionar método `_update_title_bar_buttons()` para atualizar visibilidade

## Design Visual

### Cores
- **Barra de título**: `#2b2b2b` (dark mode) / `#1a1a1a` (mais escuro)
- **Botões**: Fundo transparente, hover cinza escuro
- **Botão fechar**: Hover vermelho (`#d32f2f`)

### Tamanhos
- **Altura da barra**: 35px
- **Botões**: 30x30px
- **Espaçamento**: 5px entre botões

### Ícones
- Usar caracteres Unicode ou ícones da pasta `data/imagens/`
- Alternativa: Usar `CTkLabel` com texto Unicode (`─`, `□`, `×`, `_`)

## Fluxo de Funcionamento

### Inicialização
1. Criar janela com `overrideredirect(True)`
2. Criar barra de título customizada
3. Adicionar botões conforme configuração
4. Carregar preferência `minimize_to_tray` do config
5. Mostrar/ocultar botão "Minimizar para Tray" conforme preferência

### Interação do Usuário
1. **Clicar em "Minimizar para Tray"**:
   - Se `minimize_to_tray = True`: Minimiza para tray
   - Se `minimize_to_tray = False`: Alterna para `True` e salva

2. **Clicar em "Minimizar"**:
   - Minimiza para barra de tarefas (comportamento padrão)

3. **Clicar em "Fechar"**:
   - Chama `on_closing()`
   - Se `minimize_to_tray = True`: Vai para tray
   - Se `minimize_to_tray = False`: Fecha aplicação

## Considerações Especiais

### Windows
- `overrideredirect(True)` funciona bem no Windows
- Arrastar janela precisa ser implementado manualmente
- Botões precisam ter feedback visual (hover)

### Compatibilidade
- Verificar se funciona em outros sistemas operacionais
- Se não funcionar bem, manter fallback para checkbox no footer

### Acessibilidade
- Botões devem ter tooltips
- Feedback visual claro no hover
- Área clicável adequada (mínimo 30x30px)

## Testes Necessários

1. **Teste de Arrastar**: Arrastar janela pela barra de título
2. **Teste de Botões**: Clicar em cada botão e verificar comportamento
3. **Teste de Minimizar para Tray**: Verificar se minimiza corretamente
4. **Teste de Restaurar**: Verificar se restaura corretamente do tray
5. **Teste de Preferência**: Verificar se preferência é salva/carregada
6. **Teste Visual**: Verificar aparência em diferentes temas

## Próximos Passos

1. ✅ Planejamento (este documento)
2. ⏳ Implementar barra de título customizada
3. ⏳ Implementar botões de controle
4. ⏳ Implementar arrastar janela
5. ⏳ Remover checkbox do footer
6. ⏳ Testar funcionalidade
7. ⏳ Ajustar design visual

