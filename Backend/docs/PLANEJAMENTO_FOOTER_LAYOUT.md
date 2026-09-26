# Planejamento: Correção do Layout do Footer

## Problema Identificado

O botão de copiar hash está ficando escondido/fora da tela no footer da GUI.

## Análise do Layout Atual

### Estrutura do Footer

```
┌─────────────────────────────────────────────────────────────────┐
│ [Control Panel] [Site SSM] [☑] │ [API Key: ********] [👁][✏] │ [Hash: xxx] [📋] │
│ footer_buttons_frame            │ apikey_main_frame            │ footer_hash_frame│
│ (left, fixed)                    │ (left, expand=True)          │ (right, fixed)   │
└─────────────────────────────────────────────────────────────────┘
```

### Problema

1. **`apikey_main_frame`** está usando `fill="x", expand=True`
   - Isso faz ele ocupar TODO o espaço disponível
   - Empurra o `footer_hash_frame` para fora da tela quando a janela é pequena ou o campo API Key é longo

2. **Largura fixa da janela**: 900px
   - Com 3 seções lado a lado, pode não caber tudo

3. **Campo API Key** pode ser muito largo
   - Placeholder longo pode fazer o campo expandir demais

## Soluções Possíveis

### Opção 1: Limitar largura do `apikey_main_frame` (Recomendado)

**Vantagens:**
- Simples de implementar
- Mantém layout atual
- Garante que hash sempre fica visível

**Implementação:**
- Remover `expand=True` do `apikey_main_frame`
- Definir largura máxima para o campo API Key
- Usar `fill="x"` sem `expand=True`

### Opção 2: Reduzir tamanho do campo Hash

**Vantagens:**
- Mais espaço para API Key
- Mantém layout atual

**Desvantagens:**
- Hash pode ficar cortado se for muito longo
- Menos legível

### Opção 3: Reorganizar em duas linhas

**Vantagens:**
- Mais espaço para todos os elementos
- Melhor organização visual

**Desvantagens:**
- Muda layout significativamente
- Pode não ficar tão compacto

### Opção 4: Usar grid em vez de pack

**Vantagens:**
- Controle mais preciso sobre tamanhos
- Melhor distribuição de espaço

**Desvantagens:**
- Requer refatoração maior
- Mais complexo

## Solução Recomendada: Opção 1

### Mudanças Necessárias

1. **Modificar `apikey_main_frame`**:
   - Remover `expand=True`
   - Adicionar largura máxima ao campo API Key
   - Usar `fill="x"` sem expandir

2. **Ajustar largura do campo API Key**:
   - Definir `width` fixo ou máximo
   - Usar `max_width` se CustomTkinter suportar

3. **Garantir espaço mínimo para Hash**:
   - Verificar que `footer_hash_frame` sempre fica visível
   - Ajustar padding se necessário

### Código Proposto

```python
# Frame para API Key (centro) - SEM expand=True
apikey_main_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
apikey_main_frame.pack(side="left", padx=10, fill="x")  # Remover expand=True

# Campo API Key com largura limitada
self.main_apikey_entry = ctk.CTkEntry(
    apikey_main_frame,
    placeholder_text="ssm_2d9ba653192f1a872fbef6583485c50fd6265384ace80ecf222727cc41c4ac4c",
    height=40,
    width=300,  # Largura fixa ou máxima
    font=ctk.CTkFont(size=11),
    show="*"
)
self.main_apikey_entry.pack(side="left", padx=2)  # Remover fill="x", expand=True
```

### Alternativa: Usar largura relativa

```python
# Calcular largura baseada na janela
window_width = 900
buttons_width = 120 + 100 + 20 + 20  # Control Panel + Site SSM + padding + checkbox
hash_width = 180 + 40 + 20  # Hash field + button + padding
available_width = window_width - buttons_width - hash_width - 60  # 60 = padding total

self.main_apikey_entry = ctk.CTkEntry(
    apikey_main_frame,
    width=min(available_width, 400),  # Máximo 400px, mínimo disponível
    ...
)
```

## Testes Necessários

1. ✅ Verificar que botão copiar hash fica visível
2. ✅ Verificar que API Key ainda é legível
3. ✅ Testar com diferentes tamanhos de janela
4. ✅ Testar com API Key curta e longa
5. ✅ Verificar responsividade

## Próximos Passos

1. ⏳ Implementar solução escolhida
2. ⏳ Testar layout
3. ⏳ Ajustar se necessário

