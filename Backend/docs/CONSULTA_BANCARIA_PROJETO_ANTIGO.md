# 💰 Consulta Bancária do Projeto Antigo (SSM 2.0)

## 📋 Consulta SQL Encontrada

No projeto antigo (`ScumServerManager2.0`), a consulta para extrair saldos das contas bancárias está no arquivo:
**`scripts/bank_account_updater.js`**

### Query Principal

```sql
SELECT DISTINCT
    up.user_id as steam_id,
    up.name as player_name,
    bar.bank_account_number,
    barc.currency_type,
    barc.account_balance
FROM user_profile up
INNER JOIN bank_account_registry bar ON up.id = bar.account_owner_user_profile_id
INNER JOIN bank_account_registry_currencies barc ON bar.id = barc.bank_account_id
WHERE barc.account_balance > 0
ORDER BY up.name, barc.currency_type
```

## 🔑 Pontos Importantes

### 1. **Tabelas Envolvidas**

- **`user_profile`** (`up`): Contém nome do jogador e `user_id` (Steam ID)
- **`bank_account_registry`** (`bar`): Contém o número da conta bancária
- **`bank_account_registry_currencies`** (`barc`): Contém o **saldo** (`account_balance`)

### 2. **JOINs Críticos**

- `user_profile.id = bank_account_registry.account_owner_user_profile_id`
  - **IMPORTANTE**: Usa `account_owner_user_profile_id`, não `user_profile_id`!
  
- `bank_account_registry.id = bank_account_registry_currencies.bank_account_id`
  - Liga a conta ao saldo

### 3. **Estrutura de Dados**

O saldo **NÃO está diretamente** em `bank_account_registry`, mas sim em `bank_account_registry_currencies`:

- **`account_balance`**: Saldo da conta
- **`currency_type`**: Tipo de moeda
  - `1` = Money (dinheiro)
  - `2` = Gold (ouro)

### 4. **Campos Extraídos**

- `steam_id`: ID Steam do jogador (`user_profile.user_id`)
- `player_name`: Nome do jogador (`user_profile.name`)
- `bank_account_number`: Número da conta (`bank_account_registry.bank_account_number`)
- `currency_type`: Tipo de moeda (1 ou 2)
- `account_balance`: Saldo da conta

## 📊 Processamento no Projeto Antigo

O script agrupa os dados por jogador e separa os saldos por tipo de moeda:

```javascript
// Agrupar por jogador
const players = {};
rows.forEach(row => {
    const steamId = row.steam_id;
    
    if (!players[steamId]) {
        players[steamId] = {
            steam_id: steamId,
            name: row.player_name,
            account_number: row.bank_account_number,
            money_balance: 0,
            gold_balance: 0
        };
    }
    
    // Adicionar saldo por tipo de moeda
    if (row.currency_type === 1) {
        players[steamId].money_balance = row.account_balance;
    } else if (row.currency_type === 2) {
        players[steamId].gold_balance = row.account_balance;
    }
});
```

## 🔄 Diferenças para o Projeto Novo

### Projeto Antigo (SSM 2.0)
- ✅ Usa `account_owner_user_profile_id` para JOIN
- ✅ Saldo em `bank_account_registry_currencies.account_balance`
- ✅ Separa por `currency_type` (Money/Gold)
- ✅ Número da conta em `bank_account_number`

### Projeto Novo (SSM 3.0)
O script `extract_bank_accounts.py` foi atualizado para usar a mesma estrutura:

```python
query = """
    SELECT DISTINCT
        up.user_id as steam_id,
        up.name as player_name,
        bar.bank_account_number,
        barc.currency_type,
        barc.account_balance
    FROM user_profile up
    INNER JOIN bank_account_registry bar ON up.id = bar.account_owner_user_profile_id
    INNER JOIN bank_account_registry_currencies barc ON bar.id = barc.bank_account_id
    WHERE barc.account_balance > 0
    ORDER BY up.name, barc.currency_type
"""
```

## 📁 Arquivos Relacionados no Projeto Antigo

1. **`scripts/bank_account_updater.js`**
   - Script principal de atualização
   - Extrai dados e salva em JSON

2. **`scripts/query_bank_data.js`**
   - Consulta dados bancários de um jogador específico
   - Mostra todas as tabelas relacionadas

3. **`scripts/search_all_balances.js`**
   - Busca todos os saldos do servidor
   - Inclui saldo em `user_profile.money_balance` e saldos bancários

4. **`routes/bank-account.js`**
   - Rota da API para acessar dados bancários
   - Usa o JSON gerado pelo updater

## 🎯 Uso no Projeto Novo

O script `extract_bank_accounts.py` foi criado baseado nesta consulta e:

1. ✅ Usa a mesma query SQL
2. ✅ Agrupa dados por jogador
3. ✅ Separa Money e Gold
4. ✅ Gera JSON, CSV e relatório em texto
5. ✅ Usa os helpers do projeto (read-only connection)

## ⚠️ Observações

1. **Campo correto**: `account_owner_user_profile_id` (não `user_profile_id`)
2. **Saldo em tabela separada**: `bank_account_registry_currencies.account_balance`
3. **Múltiplas moedas**: Um jogador pode ter Money (type=1) e Gold (type=2)
4. **Filtro**: Apenas contas com saldo > 0 são retornadas

---

**Última Atualização**: 2025-01-27  
**Fonte**: `ScumServerManager2.0/Backend/scripts/bank_account_updater.js`
