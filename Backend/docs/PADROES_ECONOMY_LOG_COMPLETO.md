# 📊 Análise Completa dos Padrões do economy_*.log

## 📄 Arquivo Analisado
- **Arquivo**: `economy_20251206000024.log`
- **Total de linhas**: 395 linhas
- **Linhas com transações**: ~390 linhas

---

## 🏷️ TIPOS DE TRANSAÇÕES IDENTIFICADOS

### 1. `[Trade]` - Transações de Comércio

#### 1.1. Venda de Itens
**Padrão**: `[Trade] Tradeable (ITEM) sold by PLAYER(STEAM_ID) for VALOR to trader LOCAL`

**Exemplos**:
```
[Trade] Tradeable (CD_Player (health: 46.48, uses: 1)) sold by Guarani(76561198157950243) for 191 (191 + 0 worth of contained items) to trader B_4_Armory
[Trade] Tradeable (Weapon_MK18 (health: 99.94, uses: 1)) sold by TutiCats(76561199617993331) for 3278 (2870 + 408 worth of contained items) to trader B_4_Armory
[Trade] Tradeable (BPC_Dirtbike (health: 152.54)) sold by Guarani(76561198157950243) for 4909 (3972 + 937 worth of contained items) to trader B_4_Mechanic
```

**Informações capturadas**:
- Item (nome, health, uses - mas health não será armazenado)
- Player (nome + Steam ID)
- Valor total (ex: 3278)
- Valor base (ex: 2870)
- Valor itens contidos (ex: 408)
- Local (quadrante + tipo)
- Saldo antes/depois (linhas separadas "Before" e "After")

#### 1.2. Compra de Itens
**Padrão**: `[Trade] Tradeable (ITEM) purchased by PLAYER(STEAM_ID) for VALOR money from trader LOCAL`

**Exemplos**:
```
[Trade] Tradeable (Cal_9mm_Ammobox (x1)) purchased by Guarani(76561198157950243) for 457 money from trader B_4_Armory
[Trade] Tradeable (Batteries (x2)) purchased by TutiCats(76561199617993331) for 200 money from trader B_4_Trader
[Trade] Tradeable (Cal_7_62x39mm_AP_Ammobox (x6)) purchased by TutiCats(76561199617993331) for 11316 money from trader B_4_Armory
```

**Informações capturadas**:
- Item (nome, quantidade)
- Player (nome + Steam ID)
- Valor (em money)
- Local (quadrante + tipo)
- Saldo antes/depois (linhas separadas "Before" e "After")

#### 1.3. Linhas de Saldo (Before/After)
**Padrões**:
- **Before selling**: `[Trade] Before selling tradeables to trader LOCAL, player PLAYER(STEAM_ID) had X cash, Y account balance and Z gold and trader had FUNDS funds.`
- **After selling**: `[Trade] After tradeable sale to trader LOCAL, player PLAYER(STEAM_ID) has X cash, Y account balance and Z gold and trader has FUNDS funds.`
- **Before purchasing**: `[Trade] Before purchasing tradeales from trader LOCAL, player PLAYER(STEAM_ID) had X cash, Y account balance and Z gold and trader had FUNDS funds.`
- **After purchasing**: `[Trade] After tradeable purchase from trader LOCAL, player PLAYER(STEAM_ID) has X cash, Y bank account balance and Z gold and trader has FUNDS funds.`

**Nota**: Há variação no texto - às vezes "account balance", às vezes "bank account balance".

### 2. `[Bank]` - Transações Bancárias

**Padrão**: `[Bank] PLAYER(ID:STEAM_ID)(Account Number:ACCOUNT) deposited AMOUNT(ACTUAL_ADDED was added) to Account Number: ACCOUNT(PLAYER)(STEAM_ID) at X=... Y=... Z=...`

**Exemplos**:
```
[Bank] TENEBROSO(ID:76561198202684968)(Account Number:718003040384) deposited 375(367 was added) to Account Number: 718003040384(TENEBROSO)(76561198202684968) at X=-150502.234 Y=290073.969 Z=69695.891
[Bank] cyborgsungjinwoo(ID:76561199768456110)(Account Number:713706045079) deposited 2976(2916 was added) to Account Number: 713706045079(cyborgsungjinwoo)(76561199768456110) at X=575072.938 Y=-227289.969 Z=360.040
```

**Informações capturadas**:
- Player (nome + Steam ID)
- Account Number
- Valor depositado (amount)
- Valor efetivamente adicionado (actual_added - pode ser diferente devido a taxas)
- Coordenadas (X, Y, Z) - **mas não serão armazenadas**

**Nota**: Apenas depósitos foram encontrados neste log. Saques podem ter padrão similar.

### 3. `[Currency Conversion]` - Conversão de Moeda

**Padrão**: `[Currency Conversion] PLAYER(ID:STEAM_ID)(Account Number:ACCOUNT) purchased GOLD_AMOUNT gold for CREDITS credits (new account balance is GOLD gold/CREDITS credits) at X=... Y=... Z=...`

**Exemplos**:
```
[Currency Conversion] TutiCats(ID:76561199617993331)(Account Number:718705046343) purchased 50 gold for 58000 credits (new account balance is 50 gold/47415 credits) at X=575022.438 Y=-227326.094 Z=356.130.
[Currency Conversion] TutiCats(ID:76561199617993331)(Account Number:718705046343) purchased 10 gold for 11800 credits (new account balance is 60 gold/35615 credits) at X=575022.438 Y=-227326.094 Z=356.130.
```

**Informações capturadas**:
- Player (nome + Steam ID)
- Account Number
- Quantidade de gold comprada
- Créditos gastos
- Novo saldo (gold e credits)
- Coordenadas (X, Y, Z) - **mas não serão armazenadas**

### 4. `[Trade-Mechanic]` - Serviços de Mecânico

**Padrão**: `[Trade-Mechanic] Service (SERVICE_DESCRIPTION) purchased by PLAYER(STEAM_ID) for VALOR money from trader LOCAL`

**Exemplos**:
```
[Trade-Mechanic] Service (Repair attachment BPC_WolfsWagen_Body_Front_C (x1)) purchased by TutiCats(76561199617993331) for 129 money from trader B_4_Mechanic
[Trade-Mechanic] Service (Repair attachment BPC_WolfsWagen_Wheel_FrontLeft_C (x1)) purchased by TutiCats(76561199617993331) for 6 money from trader B_4_Mechanic
```

**Informações capturadas**:
- Tipo de serviço (ex: "Repair attachment")
- Item/peça reparada
- Player (nome + Steam ID)
- Valor (em money)
- Local (quadrante + tipo - sempre Mechanic)

---

## 📍 QUADRANTES ENCONTRADOS

### Quadrantes Identificados:
- **B_4** - Mais comum (maioria das transações)
- **A_0** - Encontrado em transações de Sulivan
- **C_2** - Encontrado em transação de TENEBROSO
- **Z_3** - Encontrado em transações de Guarani

**Padrão**: `[LETRA]_[NÚMERO]`
- Letra: A, B, C, Z (possivelmente mais)
- Número: 0, 2, 3, 4 (possivelmente mais)

---

## 🏪 TIPOS DE LOCAIS IDENTIFICADOS

### Tipos Encontrados:
1. **Armory** - Arsenal (armas, munições, equipamentos militares)
2. **Trader** - Comerciante geral (itens diversos)
3. **Mechanic** - Mecânico (peças de veículos, reparos)
4. **Saloon** - Saloon (bebidas, itens de bar)

**Padrão**: `[QUADRANTE]_[TIPO]`

### Locais Completos Encontrados:
- `B_4_Armory` - Mais comum
- `B_4_Trader` - Muito comum
- `B_4_Mechanic` - Comum
- `B_4_Saloon` - Menos comum
- `A_0_Armory` - Encontrado
- `A_0_Mechanic` - Encontrado
- `C_2_Trader` - Encontrado
- `Z_3_Mechanic` - Encontrado
- `Z_3_Trader` - Encontrado
- `Z_3_Armory` - Encontrado

---

## 💰 ESTRUTURA DE VALORES

### Moedas Identificadas:
1. **money** - Dinheiro em mãos (cash)
2. **account balance** / **bank account balance** - Saldo bancário
3. **gold** - Ouro
4. **credits** - Créditos

### Valores de Transação:
- **Valor Total**: Valor completo da transação
- **Valor Base**: Valor do item sem itens contidos
- **Valor Itens Contidos**: Valor dos itens dentro de containers/veículos
- **Valor Efetivo**: Para depósitos, pode haver diferença (ex: depositou 375, mas 367 foi adicionado)

---

## 📦 ESTRUTURA DE ITENS

### Padrões de Nome de Item:
1. **Item simples**: `ItemName`
2. **Item com quantidade**: `ItemName (x2)`, `ItemName (x6)`, `ItemName (x12)`
3. **Item com health**: `ItemName (health: 46.48, uses: 1)`
4. **Item com health e uses**: `ItemName (health: 100.00, uses: 20)`
5. **Item com uses apenas**: `ItemName (uses: 137)`
6. **Item com valor de itens contidos**: `ItemName (health: 99.94, uses: 1)` + `(2870 + 408 worth of contained items)`

**Nota**: Health e uses não serão armazenados - apenas nome base e quantidade.

### Exemplos de Itens Encontrados:
- Armas: `Weapon_MK18`, `Weapon_M1911`, `Weapon_MAC10`, `Weapon_AK15`
- Munições: `Cal_9mm_Ammobox`, `Cal_7_62x39mm_AP_Ammobox`
- Veículos: `BPC_Dirtbike`
- Peças de veículos: `Laika_Seat_FrontLeft_Item`, `Wheel_255_55_R16_Item`
- Itens diversos: `Batteries`, `Soap`, `Puppet_Eye`, `BCULock_Item`

---

## 🔄 PADRÕES DE CORRELAÇÃO

### Transações de Trade:
1. **Venda**: Múltiplas linhas de itens vendidos → 1 linha "Before" → 1 linha "After"
2. **Compra**: 1 linha de item comprado → 1 linha "Before" → 1 linha "After"

**Estratégia**: 
- Agrupar itens vendidos/comprados entre "Before" e "After"
- Usar "After" para obter saldos finais
- Usar "Before" para obter saldos iniciais

### Transações de Bank:
- Linha única com todas as informações

### Transações de Currency Conversion:
- Linha única com todas as informações

### Transações de Trade-Mechanic:
- Linha única com todas as informações
- Sem linhas "Before/After"

---

## 📊 RESUMO ESTATÍSTICO

### Distribuição de Transações (estimativa):
- **`[Trade]`**: ~350 linhas (90%)
- **`[Bank]`**: ~4 linhas (1%)
- **`[Currency Conversion]`**: ~4 linhas (1%)
- **`[Trade-Mechanic]`**: ~8 linhas (2%)

### Locais Mais Usados:
- **B_4_Armory**: Mais comum (vendas de armas)
- **B_4_Trader**: Muito comum (comércio geral)
- **B_4_Mechanic**: Comum (peças e reparos)
- **B_4_Saloon**: Menos comum (bebidas)

### Quadrantes Mais Usados:
- **B_4**: Dominante (maioria das transações)
- **A_0**: Algumas transações
- **C_2**: Poucas transações
- **Z_3**: Poucas transações

---

## ✅ CONCLUSÕES PARA IMPLEMENTAÇÃO

### 1. Estrutura de Tabelas (Confirmada):
- ✅ `locations` - Normalização de locais (quadrante + tipo)
- ✅ `transaction_types` - Tipos de transação
- ✅ `items` - Normalização de itens (nome base, sem health)
- ✅ `bank_transactions` - Transações principais

### 2. Campos Importantes:
- ✅ **Valores monetários**: money, account balance, gold, credits
- ✅ **Saldos antes/depois**: Para cada tipo de moeda
- ✅ **Valor total, base e itens contidos**: Para transações de trade
- ✅ **Quantidade de itens**: Quando aplicável
- ❌ **Health/durabilidade**: Não armazenar
- ❌ **Coordenadas**: Não armazenar

### 3. Padrões de Parse:
- ✅ Regex flexível para tolerar variações ("tradeales" vs "tradeables")
- ✅ Extração de valores monetários (money, account balance, gold)
- ✅ Correlação de linhas "Before/After" com itens
- ✅ Tratamento de múltiplos itens em uma transação

### 4. Tipos de Transação a Implementar:
1. `trade_sale` - Venda de item
2. `trade_purchase` - Compra de item
3. `bank_deposit` - Depósito bancário
4. `bank_withdrawal` - Saque bancário (se existir no log)
5. `currency_conversion` - Conversão de moeda
6. `service_repair` - Serviço de reparo (Trade-Mechanic)

---

## 📝 PRÓXIMOS PASSOS

1. ✅ Estrutura de tabelas definida
2. ⏳ Implementar parser com regex flexível
3. ⏳ Implementar correlação Before/After
4. ⏳ Implementar inserção normalizada
5. ⏳ Testar com arquivo real
