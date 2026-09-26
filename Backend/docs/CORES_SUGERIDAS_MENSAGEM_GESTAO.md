# 🎨 Cores Sugeridas para Mensagem do Gestão

## 📊 Cores Atuais no Sistema

| Tipo | Cor RGB | Visual | Uso |
|------|---------|--------|-----|
| **Restart (10-2 min)** | `255-180-50` | 🟠 Amarelo/Laranja | Alerta de restart |
| **Restart (1 min)** | `255-100-100` | 🔴 Vermelho | Urgência máxima |
| **Mensagens Custom** | `255-255-255` | ⚪ Branco | Padrão genérico |

---

## 💡 Recomendações

### 🥇 **Opção 1: Azul Claro/Informativo** ⭐ **RECOMENDADO**

**Cor:** `100-200-255`

**Por que:**
- ✅ Diferencia das cores de alerta (amarelo/laranja)
- ✅ Tom informativo e profissional (não urgente)
- ✅ Boa legibilidade no jogo
- ✅ Associação visual com "informação/comunicação"
- ✅ Não compete com mensagens de restart

**Visual:** 🔵 Azul claro/ciano suave

---

### 🥈 **Opção 2: Verde Claro**

**Cor:** `150-255-150` ou `100-255-150`

**Por que:**
- ✅ Tom positivo (propaganda/benefício)
- ✅ Diferencia das cores de alerta
- ✅ Boa legibilidade

**Visual:** 🟢 Verde claro

---

### 🥉 **Opção 3: Ciano/Turquesa**

**Cor:** `100-255-255` ou `80-240-255`

**Por que:**
- ✅ Muito chamativo e diferente
- ✅ Boa legibilidade
- ✅ Destaque sem ser urgente

**Visual:** 🔷 Ciano/Turquesa vibrante

---

### **Opção 4: Roxo Claro**

**Cor:** `200-150-255` ou `180-130-255`

**Por que:**
- ✅ Destaque diferenciado
- ✅ Não comum em sistemas de alerta
- ✅ Profissional

**Visual:** 🟣 Roxo claro

---

## 🎯 Comparação Visual

### **Cenário: Restart às 19:00**

```
18:50 → 🟠 "⚠️ SERVER RESTART IN 10 MINUTES!" (255-180-50)
18:52 → 🟢 "Enquanto o Servidor reinicia, peça um ifood..." (150-255-150) ← NOVA
18:55 → 🟠 "⚠️ SERVER RESTART IN 5 MINUTES!" (255-180-50)
18:59 → 🔴 "⚠️ SERVER RESTART IN 1 MINUTE!" (255-100-100)
```

---

## ✅ Decisão Final Escolhida

### **Cor: `150-255-150` (Verde Claro)** ✅

**Justificativa:**
1. **Diferenciação clara:** Diferente das cores de alerta (amarelo/laranja) e urgência (vermelho)
2. **Tom positivo:** Verde associa-se a benefícios/ofertas - perfeito para propaganda/anúncio
3. **Legibilidade:** Excelente contraste no jogo SCUM
4. **Visual atrativo:** Verde claro é agradável e chama atenção sem ser urgente
5. **Hierarquia visual:** Não compete com mensagens de restart (que são mais importantes)

---

## 📝 Código de Implementação

```python
# No NotificationManager.create_restart_notifications()

if gestao_message:
    notification_time_8min = restart_datetime - timedelta(minutes=8)
    
    gestao_notification = {
        "day": "Everyday",
        "time": [notification_time_8min.strftime("%H:%M")],
        "duration": 10,
        "color": "150-255-150",  # Verde claro - positivo/benefício
        "message": gestao_message
    }
```

---

## 🔄 Alternativas (se não gostar do azul)

| Preferência | Cor | Descrição |
|------------|-----|-----------|
| Mais chamativo | `100-255-255` | Ciano vibrante |
| Mais suave | `150-220-255` | Azul mais claro |
| Positivo/verde | `150-255-150` | Verde claro |
| Destaque/roxo | `200-150-255` | Roxo claro |

---

## 💭 Considerações Finais

- **Não usar vermelho** (reservado para urgência)
- **Não usar amarelo/laranja** (reservado para restart)
- **Preferir cores claras** (melhor legibilidade no jogo)
- **Manter consistência** (usar a mesma cor para todas as mensagens do Gestão)

