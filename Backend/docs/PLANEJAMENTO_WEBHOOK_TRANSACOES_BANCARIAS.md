# 💰 Planejamento: Webhook de Transações Bancárias em Tempo Real

## 📋 Objetivo

Criar sistema de notificações Discord em tempo real para todas as transações financeiras processadas: vendas, compras, depósitos, saques, conversões de moeda e serviços.

---

## 🎯 Requisitos

### Funcionalidades
1. ✅ Notificação em tempo real para cada transação inserida
2. ✅ Embed Discord formatado e informativo
3. ✅ Diferentes cores por tipo de transação
4. ✅ Integração com sistema existente de webhooks
5. ✅ Rate limiting (evitar spam)
6. ✅ Tratamento de erros (não interromper processamento)

### Tipos de Transações a Notificar
- **trade_sale** - Venda para trader
- **trade_purchase** - Compra de trader
- **bank_deposit** - Depósito bancário
- **bank_withdrawal** - Saque bancário
- **currency_conversion** - Conversão de moeda
- **service_repair** - Reparo de veículo
- **service_modification** - Modificação de veículo

---

## 📝 Configuração

### Arquivo: `data/webhooks.json`

Adicionar nova entrada:
```json
{
  "bank_transaction": "https://discord.com/api/webhooks/1459032535051927706/8AX87Kl1jAvh-wZvoatec6g5ITzq60WiAB4dKBdvD6HqJCEAy8fC-qw0eRrkFwIzXczX"
}
```

---

## 🏗️ Arquitetura da Solução

### 1. Ponto de Integração

**Localização:** `core/logs/bank_transaction_processor.py`

**Método:** `_insert_transaction()` (linha 651)

**Ação:** Após inserção bem-sucedida no banco, chamar método para enviar webhook.

### 2. Fluxo de Execução

```
BankTransactionProcessor.process_file()
    ↓
Processa linha do log
    ↓
Parse da transação (parse_trade_sale, parse_trade_purchase, etc.)
    ↓
_insert_transaction() → Insere no banco
    ↓
✅ Se sucesso → send_bank_transaction_webhook()
    ↓
Cria embed Discord formatado
    ↓
Envia via DiscordWebhook
```

---

## 🔧 Modificações Necessárias

### 1. Adicionar Webhook ao `webhooks.json`

**Arquivo:** `data/webhooks.json`

Adicionar entrada:
```json
"bank_transaction": "https://discord.com/api/webhooks/1459032535051927706/8AX87Kl1jAvh-wZvoatec6g5ITzq60WiAB4dKBdvD6HqJCEAy8fC-qw0eRrkFwIzXczX"
```

### 2. Adicionar Método no `DiscordWebhook`

**Arquivo:** `core/webhooks/discord_webhook.py`

**Novo Método:**
```python
def send_bank_transaction_notification(self, transaction_data: Dict[str, Any]) -> bool:
    """
    Enviar notificação de transação bancária para Discord
    
    Args:
        transaction_data: Dicionário com dados da transação:
            - type: Tipo da transação (trade_sale, bank_deposit, etc.)
            - player_name: Nome do jogador
            - steam_id: Steam ID do jogador
            - transaction_value: Valor da transação
            - currency_type: Tipo de moeda (money, gold, credits)
            - location: Local da transação (opcional)
            - item_name: Nome do item (opcional)
            - balance_before/after: Saldos antes/depois (opcional)
            - timestamp: Timestamp da transação
    
    Returns:
        True se enviado com sucesso
    """
```

**Características:**
- Verificar se webhook 'bank_transaction' está configurado
- Criar embed formatado baseado no tipo de transação
- Aplicar cores diferentes por tipo
- Incluir informações relevantes (player, valor, local, item)
- Rate limiting automático (já implementado na classe)
- Tratamento de erros (log apenas, não interromper processamento)

### 3. Integrar no `BankTransactionProcessor`

**Arquivo:** `core/logs/bank_transaction_processor.py`

**Modificações:**

1. **No `__init__`:**
   - Adicionar parâmetro opcional `discord_webhook: Optional[DiscordWebhook] = None`
   - Armazenar referência para uso posterior

2. **No `_insert_transaction()`:**
   - Após inserção bem-sucedida (`return True` antes da linha 731)
   - Chamar: `self._notify_transaction(transaction)` (método novo)

3. **Novo Método `_notify_transaction()`:**
   ```python
   def _notify_transaction(self, transaction: Dict[str, Any]) -> None:
       """
       Notificar transação via Discord webhook
       
       Args:
           transaction: Dicionário com dados da transação
       """
       if not self.discord_webhook:
           return
       
       try:
           self.discord_webhook.send_bank_transaction_notification(transaction)
       except Exception as e:
           # Log mas não interromper processamento
           self.logger.warn(f"Erro ao enviar notificação Discord: {e}")
   ```

### 4. Passar Referência no `LogProcessor`

**Arquivo:** `core/logs/log_processor.py`

**Modificações:**
- Ao inicializar `BankTransactionProcessor`, passar referência do `DiscordWebhook`
- Se `DiscordWebhook` não estiver disponível, passar `None` (compatibilidade)

---

## 🎨 Formato dos Embeds Discord

### Cores por Tipo de Transação

| Tipo | Cor | Emoji | Descrição |
|------|-----|-------|-----------|
| `trade_sale` | Verde `0x00FF00` | 💰 | Venda (ganho) |
| `trade_purchase` | Laranja `0xFFA500` | 🛒 | Compra (gasto) |
| `bank_deposit` | Azul `0x0099FF` | 📥 | Depósito |
| `bank_withdrawal` | Amarelo `0xFFFF00` | 📤 | Saque |
| `currency_conversion` | Roxo `0x9932CC` | 💎 | Conversão |
| `service_repair` | Cinza `0x808080` | 🔧 | Reparo |
| `service_modification` | Cyan `0x00FFFF` | ⚙️ | Modificação |

### Estrutura do Embed

#### Exemplo: Venda (trade_sale)
```json
{
  "title": "💰 Venda para Trader",
  "description": "**TutiCats** vendeu item para trader",
  "color": 3447003,
  "fields": [
    {
      "name": "📦 Item",
      "value": "Weapon_MK18",
      "inline": true
    },
    {
      "name": "💰 Valor",
      "value": "3,278 money\n(2,870 + 408 itens contidos)",
      "inline": true
    },
    {
      "name": "📍 Local",
      "value": "B_4_Armory",
      "inline": true
    },
    {
      "name": "💵 Saldo Antes",
      "value": "Cash: 0 | Conta: 26,019 | Gold: 68",
      "inline": false
    },
    {
      "name": "💵 Saldo Depois",
      "value": "Cash: 3,278 | Conta: 26,019 | Gold: 68",
      "inline": false
    }
  ],
  "footer": {
    "text": "SCUM SSM Backend"
  },
  "timestamp": "2025-12-06T00:41:27Z"
}
```

#### Exemplo: Depósito Bancário
```json
{
  "title": "📥 Depósito Bancário",
  "description": "**TutiCats** depositou na conta bancária",
  "color": 3447003,
  "fields": [
    {
      "name": "💰 Valor Depositado",
      "value": "10,000 money",
      "inline": true
    },
    {
      "name": "🏦 Conta",
      "value": "718705046343",
      "inline": true
    }
  ],
  "footer": {
    "text": "SCUM SSM Backend"
  },
  "timestamp": "2025-12-06T00:41:27Z"
}
```

#### Exemplo: Conversão de Moeda
```json
{
  "title": "💎 Conversão de Moeda",
  "description": "**TutiCats** converteu credits para gold",
  "color": 10181046,
  "fields": [
    {
      "name": "💎 Gold Recebido",
      "value": "100 gold",
      "inline": true
    },
    {
      "name": "💳 Credits Gastos",
      "value": "10,000 credits",
      "inline": true
    },
    {
      "name": "💰 Novo Saldo",
      "value": "Gold: 168 | Credits: 5,000",
      "inline": false
    }
  ],
  "footer": {
    "text": "SCUM SSM Backend"
  },
  "timestamp": "2025-12-06T00:41:27Z"
}
```

---

## ⚙️ Considerações de Implementação

### 1. Performance
- ✅ Webhook assíncrono não é necessário (requests já é não-bloqueante)
- ✅ Rate limiting já implementado no `DiscordWebhook`
- ✅ Erros não devem interromper processamento de logs
- ⚠️ Muitas transações podem gerar muitos webhooks (considerar throttle)

### 2. Rate Limiting Discord
- Discord permite **30 requisições por minuto** por webhook
- Já implementado no `DiscordWebhook._check_rate_limit()`
- Se rate limit atingido, webhook é silenciosamente ignorado (log de warning)

### 3. Tratamento de Erros
- Erros ao enviar webhook **não devem** interromper inserção no banco
- Usar `try/except` e apenas logar erros
- Não lançar exceções que quebrem o fluxo principal

### 4. Compatibilidade
- Se `DiscordWebhook` não estiver disponível, não deve quebrar
- Verificar se webhook está configurado antes de tentar enviar
- Passar `None` como valor padrão se não disponível

### 5. Dados do Embed
- Formatar valores monetários com separadores (ex: "10,000 money")
- Truncar nomes muito longos
- Mostrar apenas campos relevantes por tipo de transação
- Incluir timestamp formatado corretamente (ISO 8601)

---

## 📊 Checklist de Implementação

### Fase 1: Configuração
- [ ] Adicionar `bank_transaction` ao `webhooks.json`
- [ ] Testar webhook manualmente (usar Discord webhook tester)

### Fase 2: DiscordWebhook
- [ ] Criar método `send_bank_transaction_notification()` no `DiscordWebhook`
- [ ] Implementar criação de embeds por tipo de transação
- [ ] Implementar formatação de valores monetários
- [ ] Testar método isoladamente

### Fase 3: Integração
- [ ] Adicionar parâmetro `discord_webhook` no `BankTransactionProcessor.__init__`
- [ ] Criar método `_notify_transaction()` no `BankTransactionProcessor`
- [ ] Chamar `_notify_transaction()` após inserção bem-sucedida
- [ ] Modificar `LogProcessor` para passar referência do `DiscordWebhook`

### Fase 4: Testes
- [ ] Testar com transação de venda
- [ ] Testar com depósito bancário
- [ ] Testar com compra
- [ ] Testar com conversão de moeda
- [ ] Verificar rate limiting funcionando
- [ ] Verificar tratamento de erros (webhook inválido)
- [ ] Verificar que processamento continua mesmo com erro no webhook

### Fase 5: Documentação
- [ ] Atualizar documentação de webhooks
- [ ] Documentar novos campos e formatos
- [ ] Adicionar exemplos de embeds

---

## 🎯 Vantagens da Solução

1. **Tempo Real:** Notificações imediatas quando transações são processadas
2. **Integrado:** Usa sistema de webhooks existente (não duplica código)
3. **Robusto:** Tratamento de erros não interrompe processamento
4. **Rate Limited:** Evita spam automaticamente
5. **Flexível:** Fácil adicionar novos tipos de transação
6. **Formatado:** Embeds visuais e informativos no Discord

---

## 📝 Notas Adicionais

### Throttling (Opcional - Futuro)
Se houver muitas transações, considerar:
- Buffer de transações (agrupar por X segundos)
- Filtrar transações de baixo valor
- Permitir configurar valor mínimo para notificar

### Configuração Avançada (Opcional - Futuro)
Adicionar ao `config.json`:
```json
{
  "bank_transaction_webhook": {
    "enabled": true,
    "min_value": 1000,  // Notificar apenas transações acima de X
    "types": ["trade_sale", "bank_deposit"],  // Tipos a notificar
    "include_balances": true  // Incluir saldos antes/depois
  }
}
```

---

**Última atualização:** 2025-01-XX  
**Status:** Planejamento concluído - Aguardando aprovação para implementação
