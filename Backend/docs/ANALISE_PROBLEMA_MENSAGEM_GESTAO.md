# 🔍 Análise do Problema: Mensagem do Gestão Não Inserida

## ❌ Problema Identificado

O `Notifications.json` não foi modificado às 20:45/20:47 com a mensagem do Gestão, mesmo com restart agendado para 21:00.

---

## 🔎 Causa Raiz

### **Problema Principal:**

O método `_create_restart_notifications()` é chamado **apenas UMA VEZ** quando o restart é agendado (na linha 263 de `restart_scheduler.py`):

```python
# Linha 263 - _schedule_restart()
self._create_restart_notifications(restart_time.strftime('%H:%M'), restart_time)
```

### **Por que não funciona:**

1. **Chamada única:** A função é executada apenas quando `_schedule_restart()` é chamado (quando o scheduler inicia ou quando calcula o próximo restart)

2. **Verificação de tempo:** Dentro de `_create_restart_notifications()`, há uma verificação:
   ```python
   if 0 < time_until_restart < 960:  # 16 minutos
   ```
   
   **MAS** se o scheduler foi iniciado ANTES de 20:44 (16 min antes das 21:00), essa verificação passa, mas a consulta só acontece se estiver entre 14-16 minutos (840-960 segundos).

3. **Falta de agendamento:** Não há um job agendado especificamente para 15 minutos antes do restart. A função é chamada apenas uma vez, e se estiver fora da janela de 14-16 minutos, a consulta nunca acontece.

---

## 📊 Fluxo Atual (QUEBRADO)

```
1. Scheduler inicia (ex: 20:00)
   ↓
2. _schedule_restart() é chamado para 21:00
   ↓
3. _create_restart_notifications() é chamado UMA VEZ
   ↓
4. time_until_restart = 60 minutos (fora da janela de 16min)
   ↓
5. NÃO cria notificações (retorna cedo)
   ↓
6. NUNCA mais é chamado → Mensagem do Gestão nunca é consultada
```

---

## ✅ Solução Necessária

### **Opção 1: Agendar Job Específico (RECOMENDADO)**

Criar um job agendado para 15 minutos antes do restart, similar ao que é feito com `_schedule_discord_notifications()`:

```python
def _schedule_gestao_message_check(self, restart_time: datetime):
    """Agendar verificação de mensagem do Gestão 15 minutos antes do restart"""
    check_time = restart_time - timedelta(minutes=15)
    
    def check_gestao_message():
        # Consultar Gestão e criar/atualizar notificações
        gestao_message = self._get_gestao_message()
        if gestao_message:
            # Atualizar notificações existentes ou criar novas
            self._update_restart_notifications_with_gestao_message(gestao_message)
    
    # Agendar job para horário específico
    self._scheduler.every().day.at(check_time.strftime('%H:%M')).do(check_gestao_message)
```

### **Opção 2: Modificar Lógica Atual**

Modificar `_create_restart_notifications()` para:
1. Sempre criar notificações padrão (mesmo que esteja fora da janela de 16min)
2. Se estiver entre 0-16 minutos, consultar Gestão
3. Se estiver fora, agendar uma segunda chamada para 15 minutos antes

---

## 🎯 Recomendação

**Usar Opção 1** - É mais limpa, similar ao padrão já usado para notificações Discord, e garante que a consulta aconteça no momento certo.

### **Mudanças Necessárias:**

1. **Criar método `_schedule_gestao_message_check()`:**
   - Agendar job para 15 minutos antes do restart
   - Consultar Gestão no momento certo
   - Atualizar notificações existentes

2. **Modificar `_schedule_restart()`:**
   - Adicionar chamada para `_schedule_gestao_message_check()`
   - Similar a como `_schedule_discord_notifications()` é chamado

3. **Modificar `_create_restart_notifications()`:**
   - Criar notificações padrão sempre (remover verificação de janela de 16min)
   - Ou manter lógica atual mas garantir que será chamado novamente

---

## 📝 Implementação Proposta

```python
def _schedule_restart(self, restart_time: datetime):
    # ... código existente ...
    
    # Agendar notificações de Discord
    self._schedule_discord_notifications(restart_time)
    
    # NOVO: Agendar verificação de mensagem do Gestão 15 minutos antes
    self._schedule_gestao_message_check(restart_time)
    
    # Criar notificações de restart in-game (criar sempre, atualizar depois se necessário)
    self._create_restart_notifications(restart_time.strftime('%H:%M'), restart_time)
```

---

## ⚠️ Pontos Importantes

1. **Horário preciso:** O job deve ser agendado exatamente 15 minutos antes
2. **Atualizar notificações:** Se as notificações já foram criadas, precisa atualizar o arquivo Notifications.json (adicionar a mensagem do Gestão)
3. **Evitar duplicação:** Garantir que não crie notificações duplicadas

---

## 🔄 Fluxo Correto (COM CORREÇÃO)

```
1. Scheduler inicia (ex: 20:00)
   ↓
2. _schedule_restart() é chamado para 21:00
   ↓
3. Cria notificações padrão (10min, 5min, 4min, etc.)
   ↓
4. Agenda job para 20:45 (15 min antes)
   ↓
5. 20:45 → Job executa
   ↓
6. Consulta Gestão
   ↓
7. Se tem mensagem → Atualiza Notifications.json (adiciona notificação de 8min)
   ↓
8. Notificações completas prontas
```

