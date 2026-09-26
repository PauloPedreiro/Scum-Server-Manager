# 📋 Resumo Executivo: Integração Mensagens Agendadas do Gestão

## 🎯 Objetivo

Consultar mensagens do Gestão **15 minutos antes** de cada restart e inserir como **notificação separada para 8 minutos antes** do restart.

---

## 🔄 Fluxo Simplificado

```
Restart agendado para 14:00
    ↓
13:45 (15 min antes) → Consulta Gestão
    ↓
Se tem mensagem → Cria notificação para 13:52 (8 min antes)
    ↓
Estrutura final no Notifications.json:
  - 13:50 → "⚠️ SERVER RESTART IN 10 MINUTES! | #Players"
  - 13:52 → "Mensagem do Gestão" ← NOVA
  - 13:55 → "⚠️ SERVER RESTART IN 5 MINUTES! | #Players"
  - 13:56 → "⚠️ SERVER RESTART IN 4 MINUTES! | #Players"
  - ... (resto das notificações padrão)
```

---

## 📝 Mudanças Principais

### **1. Criar: `core/communication/gestao_messages_service.py`**
- Consulta `GET /api/v1/servers/messages?api_key=...`
- Cache de 5 minutos
- Timeout de 5 segundos
- Retorna `Optional[str]` (nunca lança exceção)

### **2. Modificar: `core/scheduler/restart_scheduler.py`**
- ✅ Adicionar parâmetro `gestao_messages_service` no `__init__`
- ✅ **EXPANDIR janela de 12min para 16min** (linha 74)
- ✅ Consultar Gestão quando `840 <= time_until_restart <= 960` (14-16 min)
- ✅ Passar mensagem para `NotificationManager`

### **3. Modificar: `core/notifications/notification_manager.py`**
- ✅ Adicionar parâmetro `gestao_message: Optional[str]`
- ✅ Se mensagem existir, criar notificação para **8 minutos antes**
- ✅ Ordenar todas as notificações por horário

### **4. Modificar: `main.py`**
- ✅ Instanciar `GestaoMessagesService`
- ✅ Passar para `RestartScheduler` via construtor

---

## ⚠️ Ponto Crítico

**EXPANDIR JANELA DE TEMPO:**

```python
# core/scheduler/restart_scheduler.py - LINHA 74

# ANTES:
if 0 < time_until_restart < 720:  # 12 minutos

# DEPOIS:
if 0 < time_until_restart < 960:  # 16 minutos
```

Sem isso, a consulta não acontecerá a tempo!

---

## ✅ Exemplo de Resultado Final

```json
{
  "Notifications": [
    {
      "day": "Everyday",
      "time": ["20:50"],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 10 MINUTES! | #NumPlayers players online"
    },
    {
      "day": "Everyday",
      "time": ["20:52"],
      "duration": 10,
      "color": "255-180-50",
      "message": "Enquanto o Servidor reinicia, peça um ifood cupom 545asdff"
    },
    {
      "day": "Everyday",
      "time": ["20:55"],
      "duration": 10,
      "color": "255-180-50",
      "message": "⚠️ SERVER RESTART IN 5 MINUTES! | #NumPlayers players online"
    }
    // ... resto das notificações padrão
  ]
}
```

---

## 🚀 Ordem de Implementação

1. Criar `GestaoMessagesService` (testável isoladamente)
2. Modificar `RestartScheduler` (expandir janela + consulta)
3. Modificar `NotificationManager` (criar notificação de 8min)
4. Modificar `main.py` (instanciar e passar serviços)
5. Testes

---

## ⏱️ Timeline

- **Tempo estimado:** 4-6 horas
- **Complexidade:** Média
- **Risco:** Baixo (erros não interrompem restart)

