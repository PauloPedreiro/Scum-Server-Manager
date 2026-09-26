# 🚫 Planejamento: Deduplicação de Webhooks de Transações Bancárias

## 📋 Problema

Precisamos garantir que **não enviaremos transações duplicadas** para o Discord, mesmo que:
- O mesmo arquivo seja processado múltiplas vezes
- O processamento seja interrompido e retomado
- O sistema seja reiniciado
- Haja falhas no envio e retentativas

---

## 🔍 Análise de Abordagens

### **Opção 1: Coluna `discord_sent` no Banco (RECOMENDADA)** ⭐

**Como funciona:**
- Adicionar coluna `discord_sent INTEGER DEFAULT 0` na tabela `bank_transactions`
- Após inserir transação → Verificar se `discord_sent = 0`
- Se sim → Enviar webhook → Marcar `discord_sent = 1`
- Se não → Pular (já foi enviado)

**Vantagens:**
- ✅ Persistente (sobrevive a reinicializações)
- ✅ Integrado ao banco (dados já estão lá)
- ✅ Similar ao sistema de `chest_history`
- ✅ Pode consultar histórico facilmente
- ✅ Permite retry automático (transações não enviadas)

**Desvantagens:**
- ⚠️ Requer migração de banco (adicionar coluna)
- ⚠️ Para transações antigas, `discord_sent = 0` por padrão (poderia enviar todas)

**Exemplo:**
```sql
-- Migração
ALTER TABLE bank_transactions ADD COLUMN discord_sent INTEGER DEFAULT 0;

-- Verificar antes de enviar
SELECT * FROM bank_transactions 
WHERE discord_sent = 0 
ORDER BY timestamp DESC 
LIMIT 100;

-- Marcar após envio
UPDATE bank_transactions 
SET discord_sent = 1 
WHERE id = ?;
```

---

### **Opção 2: Hash da Transação em Memória/Arquivo**

**Como funciona:**
- Criar hash único: `MD5(timestamp + steam_id + transaction_value + type)`
- Armazenar hash em arquivo JSON ou set em memória
- Antes de enviar → Verificar se hash já existe
- Após envio → Adicionar hash à lista

**Vantagens:**
- ✅ Não requer mudança no banco
- ✅ Similar ao sistema de chat (`chat_processed.json`)
- ✅ Rápido (check em memória)

**Desvantagens:**
- ❌ Perdido ao reiniciar (a menos que salve em arquivo)
- ❌ Arquivo pode crescer muito ao longo do tempo
- ❌ Precisa gerenciar limpeza de hashes antigos
- ❌ Não integrado com banco (duplicação de dados)

**Exemplo:**
```python
# Gerar hash
hash_input = f"{timestamp}|{steam_id}|{transaction_value}|{type}"
transaction_hash = hashlib.md5(hash_input.encode()).hexdigest()

# Verificar
if transaction_hash in processed_transactions:
    return  # Já processado

# Processar e marcar
send_webhook(...)
processed_transactions.add(transaction_hash)
```

---

### **Opção 3: Verificar Duplicação pela Chave Única do Banco**

**Como funciona:**
- Usar combinação de campos como chave única: `(timestamp, steam_id, transaction_value, transaction_type_id)`
- Criar índice único no banco
- Tentar inserir → Se falhar (duplicata) → Pular envio
- Se inserir com sucesso → Enviar webhook

**Vantagens:**
- ✅ Evita duplicatas no banco também
- ✅ Não precisa coluna adicional
- ✅ Integrado ao INSERT

**Desvantagens:**
- ❌ **PROBLEMA:** Duas transações idênticas podem ser legítimas
  - Ex: Jogador vende mesmo item 2x no mesmo timestamp (teoricamente possível)
- ❌ Não funciona se transação já foi inserida mas webhook falhou
- ❌ Precisa gerenciar constraint UNIQUE

**Exemplo:**
```sql
-- Criar índice único (PROBLEMÁTICO)
CREATE UNIQUE INDEX idx_transaction_unique 
ON bank_transactions(timestamp, steam_id, transaction_value, transaction_type_id);
```

---

### **Opção 4: ID da Transação + Cache em Memória**

**Como funciona:**
- Após inserir → Obter `id` da transação inserida
- Manter set em memória com IDs enviados
- Verificar se `id` está no set antes de enviar
- Adicionar ao set após envio bem-sucedido

**Vantagens:**
- ✅ Simples
- ✅ Usa ID já existente
- ✅ Rápido

**Desvantagens:**
- ❌ Perdido ao reiniciar (precisa salvar em arquivo ou banco)
- ❌ Cache em memória pode crescer
- ❌ Não funciona se sistema reinicia e transação antiga não foi enviada

---

## 🎯 Decisão Recomendada: **Opção 1 - Coluna `discord_sent`**

### **Por quê?**
1. **Persistente:** Sobrevive a reinicializações
2. **Consistente:** Similar a outros sistemas (`chest_history`)
3. **Confiável:** Dados no banco são fonte única de verdade
4. **Flexível:** Permite retry automático de envios falhos
5. **Auditável:** Pode consultar quais transações foram enviadas

---

## 📐 Estrutura da Solução

### **1. Migração do Banco**

```sql
-- Adicionar coluna discord_sent
ALTER TABLE bank_transactions 
ADD COLUMN discord_sent INTEGER DEFAULT 0;

-- Criar índice para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_bank_transactions_discord_sent 
ON bank_transactions(discord_sent, timestamp DESC);
```

**Nota sobre transações antigas:**
- Transações existentes terão `discord_sent = 0`
- **Opções:**
  - **A) Marcar todas como enviadas:** `UPDATE bank_transactions SET discord_sent = 1;` (não envia histórico)
  - **B) Deixar como 0:** Envia todas ao iniciar (pode ser spam)
  - **C) Enviar apenas novas:** Marcar como 1 apenas se enviar, ou usar data de corte

---

### **2. Fluxo de Processamento**

```
1. Processar log economy_*.log
    ↓
2. Inserir transação no banco
    ↓
3. Se inserção bem-sucedida:
    ↓
   3.1. Verificar se discord_sent = 0
        ↓
   3.2. Se sim → Enviar webhook Discord
        ↓
   3.3. Se envio bem-sucedido → UPDATE discord_sent = 1
        ↓
   3.4. Se envio falhar → Deixar discord_sent = 0 (retry depois)
    ↓
4. Se inserção falhar (duplicata):
   → Pular (transação já existe)
```

---

### **3. Pontos de Integração**

**Localização:** `core/logs/bank_transaction_processor.py`

**Método:** `_insert_transaction()`

**Modificações:**
1. Após `INSERT` bem-sucedido, obter `cursor.lastrowid`
2. Retornar `transaction_id` junto com sucesso
3. Chamar método para enviar webhook (se disponível)
4. Marcar `discord_sent = 1` após envio bem-sucedido

**Novo método:** `_mark_transaction_discord_sent(transaction_id)`

---

### **4. Sistema de Retry (Opcional - Futuro)**

Para transações que falharam no envio (`discord_sent = 0`):

```python
def retry_failed_webhooks():
    """Tentar reenviar transações que falharam"""
    with sqlite3.connect(ssm_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, steam_id, transaction_type_id, transaction_value, timestamp
            FROM bank_transactions
            WHERE discord_sent = 0
            ORDER BY timestamp DESC
            LIMIT 100
        """)
        
        for row in cursor.fetchall():
            transaction_id = row[0]
            # Reconstruir dados da transação
            # Tentar enviar novamente
            # Marcar como enviado se sucesso
```

---

### **5. Tratamento de Transações Antigas**

**Estratégia Recomendada:**

Ao adicionar a coluna, executar migração inicial:

```sql
-- Opção A: Marcar todas como já enviadas (não envia histórico)
UPDATE bank_transactions SET discord_sent = 1;

-- Opção B: Marcar apenas transações muito antigas (> 1 hora)
UPDATE bank_transactions 
SET discord_sent = 1 
WHERE datetime(timestamp) < datetime('now', '-1 hour');

-- Opção C: Não marcar nada (envia todas ao iniciar - pode ser spam)
```

**Recomendação:** Opção B ou C dependendo do caso de uso.

---

## 🔄 Fluxo Detalhado de Implementação

### **Passo 1: Migração do Banco**

```python
# Em bank_transaction_tables.py ou migration separada
def add_discord_sent_column(ssm_db_path: str):
    """Adicionar coluna discord_sent se não existir"""
    with sqlite3.connect(ssm_db_path) as conn:
        cursor = conn.cursor()
        
        # Verificar se coluna existe
        cursor.execute("PRAGMA table_info(bank_transactions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'discord_sent' not in columns:
            cursor.execute("""
                ALTER TABLE bank_transactions 
                ADD COLUMN discord_sent INTEGER DEFAULT 0
            """)
            
            # Criar índice
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bank_transactions_discord_sent 
                ON bank_transactions(discord_sent, timestamp DESC)
            """)
            
            conn.commit()
            return True
    return False
```

---

### **Passo 2: Modificar `_insert_transaction()`**

```python
def _insert_transaction(...) -> Optional[int]:
    """
    Inserir transação no banco de dados
    
    Returns:
        transaction_id se inserido com sucesso, None se falhar
    """
    try:
        # ... inserção atual ...
        cursor.execute("INSERT INTO ...", (...))
        
        transaction_id = cursor.lastrowid
        
        # Retornar ID da transação inserida
        return transaction_id
        
    except sqlite3.IntegrityError:
        # Duplicata - transação já existe
        return None
    except Exception as e:
        # Outro erro
        return None
```

---

### **Passo 3: Criar Método para Marcar como Enviado**

```python
def _mark_transaction_discord_sent(self, transaction_id: int) -> bool:
    """Marcar transação como enviada para Discord"""
    try:
        with sqlite3.connect(self.ssm_db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bank_transactions 
                SET discord_sent = 1 
                WHERE id = ?
            """, (transaction_id,))
            conn.commit()
            return True
    except Exception as e:
        self.logger.error(f"Erro ao marcar transação como enviada: {e}")
        return False
```

---

### **Passo 4: Integrar Webhook no Fluxo**

```python
# Após inserir transação
transaction_id = self._insert_transaction(conn, cursor, transaction)

if transaction_id:
    # Enviar webhook (se disponível)
    if self.discord_webhook:
        try:
            success = self.discord_webhook.send_bank_transaction_notification(
                transaction_data=transaction
            )
            
            if success:
                # Marcar como enviado
                self._mark_transaction_discord_sent(transaction_id)
            else:
                # Deixar discord_sent = 0 para retry depois
                self.logger.warn(f"Falha ao enviar webhook para transação {transaction_id}")
        except Exception as e:
            self.logger.error(f"Erro ao enviar webhook: {e}")
```

---

## 📊 Vantagens da Solução Escolhida

1. ✅ **Persistente:** Sobrevive a reinicializações do sistema
2. ✅ **Consistente:** Similar ao padrão usado em `chest_history`
3. ✅ **Confiável:** Banco de dados é fonte única de verdade
4. ✅ **Flexível:** Permite consultar status de envio
5. ✅ **Retry:** Transações não enviadas podem ser reenviadas
6. ✅ **Auditável:** Histórico completo de envios
7. ✅ **Performático:** Índice garante consultas rápidas

---

## ⚠️ Considerações Importantes

### **1. Transações Antigas**
- Decidir se marca todas como enviadas ou deixa como 0
- Recomendação: Marcar apenas transações antigas (> 1 hora)

### **2. Performance**
- Índice em `(discord_sent, timestamp)` garante consultas rápidas
- Consultar apenas transações com `discord_sent = 0`

### **3. Retry Automático (Futuro)**
- Criar job periódico para reenviar transações falhadas
- Limitar tentativas (ex: máximo 3 tentativas)
- Após N falhas, marcar como erro permanente

### **4. Rate Limiting**
- Discord limita a 30 requisições/minuto
- Sistema já tem rate limiting no `DiscordWebhook`
- Se rate limit atingido, deixa `discord_sent = 0` para retry

---

## 🎯 Checklist de Implementação

### Fase 1: Migração do Banco
- [ ] Criar função para adicionar coluna `discord_sent`
- [ ] Criar função para adicionar índice
- [ ] Executar migração na inicialização
- [ ] Testar migração em banco existente

### Fase 2: Modificar Inserção
- [ ] Modificar `_insert_transaction()` para retornar `transaction_id`
- [ ] Ajustar chamadas ao método
- [ ] Tratar retorno `None` (duplicata)

### Fase 3: Sistema de Webhook
- [ ] Criar método `_mark_transaction_discord_sent()`
- [ ] Integrar webhook após inserção
- [ ] Marcar como enviado após sucesso
- [ ] Tratar erros (deixar como 0 para retry)

### Fase 4: Testes
- [ ] Testar inserção e envio de webhook
- [ ] Testar duplicação (mesma transação 2x)
- [ ] Testar reinicialização (verificar persistência)
- [ ] Testar falha no webhook (deve deixar discord_sent = 0)
- [ ] Testar rate limiting

### Fase 5: Retry (Opcional)
- [ ] Criar job de retry automático
- [ ] Limitar tentativas
- [ ] Testar retry de transações falhadas

---

## 📝 Resumo

**Solução Escolhida:** Coluna `discord_sent` no banco de dados

**Fluxo:**
1. Inserir transação → Obter `transaction_id`
2. Verificar `discord_sent = 0`
3. Enviar webhook
4. Se sucesso → Marcar `discord_sent = 1`
5. Se falha → Deixar `discord_sent = 0` (retry depois)

**Vantagens:**
- Persistente, confiável, auditável, permite retry

**Status:** Planejamento concluído - Pronto para implementação

---

**Última atualização:** 2025-01-XX
