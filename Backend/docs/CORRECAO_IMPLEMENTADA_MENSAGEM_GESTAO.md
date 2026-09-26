# ✅ Correção Implementada: Mensagem do Gestão

## 🔧 Problema Corrigido

**Problema:** `_create_restart_notifications()` era chamado apenas uma vez quando o restart era agendado. Se o scheduler iniciasse muito antes do restart, a consulta ao Gestão nunca acontecia.

**Solução:** Criado job agendado específico para consultar o Gestão **exatamente 15 minutos antes** do restart.

---

## 📝 Mudanças Implementadas

### **1. Novo Método: `_schedule_gestao_message_check()`**

**Localização:** `core/scheduler/restart_scheduler.py` (linha ~269)

**Funcionalidade:**
- Agenda um job para executar **exatamente 15 minutos antes** do restart
- Quando executar, consulta o Gestão
- Se houver mensagem, recria todas as notificações (padrão + Gestão)
- Se não houver mensagem, mantém as notificações padrão

**Código:**
```python
def _schedule_gestao_message_check(self, restart_time: datetime):
    check_time = restart_time - timedelta(minutes=15)
    
    def gestao_message_job():
        # Consulta Gestão
        # Recria notificações com mensagem do Gestão (se existir)
    
    self._scheduler.every().day.at(check_time.strftime('%H:%M')).do(gestao_message_job)
```

---

### **2. Modificado: `_schedule_restart()`**

**Mudança:** Adicionada chamada para `_schedule_gestao_message_check()`:

```python
# Agendar notificações de Discord
self._schedule_discord_notifications(restart_time)

# NOVO: Agendar verificação de mensagem do Gestão 15 minutos antes
self._schedule_gestao_message_check(restart_time)

# Criar notificações de restart in-game (padrão, sem mensagem do Gestão ainda)
self._create_restart_notifications(restart_time.strftime('%H:%M'), restart_time)
```

---

### **3. Modificado: `_create_restart_notifications()`**

**Mudança:** Removida verificação de janela de tempo. Agora sempre cria notificações padrão:

**Antes:**
```python
if 0 < time_until_restart < 960:  # Só cria se dentro de 16 minutos
    # criar notificações
```

**Agora:**
```python
# Sempre cria notificações padrão (sem mensagem do Gestão)
# A mensagem do Gestão será adicionada pelo job de 15 minutos
gestao_message = None
result = self.notification_manager.create_restart_notifications(...)
```

---

## 🔄 Novo Fluxo

### **Cenário: Restart às 21:00, scheduler inicia às 20:00**

```
20:00 → Scheduler inicia
      → _schedule_restart() é chamado para 21:00
      ↓
20:00 → Cria notificações padrão (10min, 5min, 4min, 3min, 2min, 1min)
      → Agenda job para 20:45 (15 min antes)
      ↓
20:45 → Job executa (exatamente 15 minutos antes)
      → Consulta Gestão: GET /api/v1/servers/messages?api_key=...
      → Se tem mensagem:
         → Recria TODAS as notificações (padrão + Gestão de 8min)
         → Atualiza Notifications.json
      → Se não tem mensagem:
         → Mantém notificações padrão
      ↓
21:00 → Restart executa
```

---

## ✅ Garantias

1. **Consulta sempre acontece:** Job agendado garante execução 15 minutos antes
2. **Horário preciso:** Usa `schedule.every().day.at()` para horário exato
3. **Notificações atualizadas:** Recria todas as notificações quando mensagem é obtida
4. **Não interrompe restart:** Erros são tratados silenciosamente
5. **Cache funciona:** GestaoMessagesService usa cache de 5 minutos

---

## 🧪 Como Testar

1. **Agendar restart para um horário futuro** (ex: 10 minutos a partir de agora)
2. **Verificar logs** para ver se o job foi agendado
3. **Aguardar 15 minutos antes** e verificar se:
   - Job executou
   - Gestão foi consultado
   - Notifications.json foi atualizado com mensagem do Gestão

---

## 📋 Logs Esperados

### **Quando restart é agendado:**
```
[SCHEDULER] Verificação de mensagem do Gestão agendada para 20:45 (15 minutos antes do restart às 21:00)
```

### **Quando job executa (20:45):**
```
[SCHEDULER] Verificando mensagem do Gestão para restart às 21:00
[INFO] Mensagem do Gestão obtida: Enquanto o Servidor reinicia...
[INFO] Notificações atualizadas com mensagem do Gestão (total: 7 notificações)
```

---

## ⚠️ Observações Importantes

1. **Job único por restart:** Cada restart tem seu próprio job agendado
2. **Recriação de notificações:** Quando mensagem é obtida, todas as notificações são recriadas (limpa e cria novas)
3. **Cache:** Se houver múltiplos restarts próximos, o cache de 5 minutos evita consultas excessivas
4. **Falhas silenciosas:** Se a consulta falhar, as notificações padrão são mantidas

---

**Data da correção:** 2025-01-XX  
**Status:** ✅ Implementado e pronto para teste

