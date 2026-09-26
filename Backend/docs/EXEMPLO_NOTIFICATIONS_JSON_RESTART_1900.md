# 📋 Exemplo: Notifications.json com Restart às 19:00

## 🎯 Cenário

- **Restart agendado:** 19:00
- **Mensagem do Gestão:** "Enquanto o Servidor reinicia, peça um ifood cupom 545asdff"
- **Mensagem obtida:** 18:45 (15 minutos antes)
- **Notificação do Gestão:** 18:52 (8 minutos antes)

---

## 📄 Notifications.json Completo

```json
{
  "Notifications": [
    {
      "day": "Everyday",
      "time": [
        "18:50"
      ],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 10 MINUTES! | #NumPlayers players online"
    },
    {
      "day": "Everyday",
      "time": [
        "18:52"
      ],
      "duration": 10,
      "color": "150-255-150",
      "message": "Enquanto o Servidor reinicia, peça um ifood cupom 545asdff"
    },
    {
      "day": "Everyday",
      "time": [
        "18:55"
      ],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 5 MINUTES! | #NumPlayers players online"
    },
    {
      "day": "Everyday",
      "time": [
        "18:56"
      ],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 4 MINUTES! | #NumPlayers players online"
    },
    {
      "day": "Everyday",
      "time": [
        "18:57"
      ],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 3 MINUTES! | #NumPlayers players online"
    },
    {
      "day": "Everyday",
      "time": [
        "18:58"
      ],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 2 MINUTES! | #NumPlayers players online"
    },
    {
      "day": "Everyday",
      "time": [
        "18:59"
      ],
      "duration": 10,
      "color": "255-100-100",
      "message": "⚠️ SERVER RESTART IN 1 MINUTE! | #NumPlayers players online"
    }
  ]
}
```

---

## 📊 Linha do Tempo

```
18:45 → Consulta ao Gestão (obtém mensagem)
   ↓
18:50 → ⚠️ SERVER RESTART IN 10 MINUTES! | #NumPlayers players online
   ↓
18:52 → Enquanto o Servidor reinicia, peça um ifood cupom 545asdff  ← MENSAGEM DO GESTÃO
   ↓
18:55 → ⚠️ SERVER RESTART IN 5 MINUTES! | #NumPlayers players online
   ↓
18:56 → ⚠️ SERVER RESTART IN 4 MINUTES! | #NumPlayers players online
   ↓
18:57 → ⚠️ SERVER RESTART IN 3 MINUTES! | #NumPlayers players online
   ↓
18:58 → ⚠️ SERVER RESTART IN 2 MINUTES! | #NumPlayers players online
   ↓
18:59 → ⚠️ SERVER RESTART IN 1 MINUTE! | #NumPlayers players online
   ↓
19:00 → RESTART DO SERVIDOR
```

---

## 🎨 Observações

### **Notificação do Gestão (18:52):**
- ✅ **Horário:** 8 minutos antes do restart
- ✅ **Duração:** 10 segundos (mesma das outras)
- ✅ **Cor:** `255-180-50` (mesma cor das outras, pode ser personalizado)
- ✅ **Mensagem:** Texto puro do Gestão (sem formatação adicional)
- ✅ **Posição:** Entre a notificação de 10min e 5min

### **Comparação:**

| Horário | Tipo | Mensagem |
|---------|------|----------|
| 18:50 | Padrão | ⚠️ SERVER RESTART IN 10 MINUTES! \| #Players |
| **18:52** | **Gestão** | **Enquanto o Servidor reinicia, peça um ifood cupom 545asdff** |
| 18:55 | Padrão | ⚠️ SERVER RESTART IN 5 MINUTES! \| #Players |
| 18:56 | Padrão | ⚠️ SERVER RESTART IN 4 MINUTES! \| #Players |
| 18:57 | Padrão | ⚠️ SERVER RESTART IN 3 MINUTES! \| #Players |
| 18:58 | Padrão | ⚠️ SERVER RESTART IN 2 MINUTES! \| #Players |
| 18:59 | Padrão | ⚠️ SERVER RESTART IN 1 MINUTE! \| #Players |

---

## 🔄 Cenário Sem Mensagem do Gestão

Se não houver mensagem ativa no Gestão (retorna `null`), o arquivo ficaria:

```json
{
  "Notifications": [
    {
      "day": "Everyday",
      "time": ["18:50"],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 10 MINUTES! | #NumPlayers players online"
    },
    {
      "day": "Everyday",
      "time": ["18:55"],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 5 MINUTES! | #NumPlayers players online"
    },
    {
      "day": "Everyday",
      "time": ["18:56"],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 4 MINUTES! | #NumPlayers players online"
    },
    {
      "day": "Everyday",
      "time": ["18:57"],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 3 MINUTES! | #NumPlayers players online"
    },
    {
      "day": "Everyday",
      "time": ["18:58"],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 2 MINUTES! | #NumPlayers players online"
    },
    {
      "day": "Everyday",
      "time": ["18:59"],
      "duration": 10,
      "color": "255-100-100",
      "message": "⚠️ SERVER RESTART IN 1 MINUTE! | #NumPlayers players online"
    }
  ]
}
```

**Diferença:** Não há notificação de 18:52 (sem mensagem do Gestão).

---

## 📝 Notas Técnicas

1. **Ordenação:** As notificações devem estar ordenadas por horário (crescente)
2. **Formato de horário:** `"HH:MM"` (24 horas)
3. **Duração:** Todas têm 10 segundos de duração
4. **Cores:**
   - Notificações padrão: `"255-180-50"` (amarelo/laranja)
   - Notificação de 1 minuto: `"255-100-100"` (vermelho - mais urgente)
   - Notificação do Gestão: `"255-180-50"` (mesma das outras, pode ser personalizado)
5. **Placeholder:** `#NumPlayers` será substituído pelo número real de jogadores online

