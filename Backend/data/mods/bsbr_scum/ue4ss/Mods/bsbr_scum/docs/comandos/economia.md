# Economia

Moeda, fama e comerciantes.

14 comandos. Voltar ao [índice](../README.md).

🔒 = exige nível Developer, já incluído como `sudo` na linha de uso.

Pelo chat do jogo, troque `scum ` por `#` — os comandos do jogo não usam
o prefixo `bsbr`, que é só dos [comandos do mod](mod.md).

Para executar no lugar de outro jogador: `scum as Fulano SpawnItem X` no terminal,
`#bsbr @Fulano SpawnItem X` no chat.

> O resumo de cada comando está em português; a explicação de cada
> argumento e a linha *Original* são o texto da própria Gamepires, lido
> do jogo — não traduzimos para não introduzir erro no que é a referência.

---
### `ChangeCurrencyBalance`

Soma moeda a você ou ao jogador indicado

```
scum ChangeCurrencyBalance <Currency Type> <Amount> <Player>
```

- `Currency Type`
- `Amount`
- `Player` — Player whose balance to change

*Original:* Adds specified currency amount to self or the specified player.

### `ChangeCurrencyBalanceToAll`

Soma moeda a todos do banco, inclusive offline

```
scum ChangeCurrencyBalanceToAll <Currency Type> <Amount>
```

- `Currency Type` — Currency to change
- `Amount`

*Original:* Adds the specified currency amount to all players in the database.

### `ChangeCurrencyBalanceToAllOnline`

Soma moeda a todos os conectados

```
scum ChangeCurrencyBalanceToAllOnline <Currency Type> <Amount>
```

- `Currency Type` — Currency to change
- `Amount`

*Original:* Adds the specified currency amount to all online players.

### `ChangeFamePoints`

Soma pontos de fama ao jogador

```
scum ChangeFamePoints <Amount> <Player>
```

- `Amount`
- `Player`

*Original:* Changes fame points of the specified player for the specified value.

### `RandomizePriceDeltas`

Sorteia novas variações de preço

```
scum RandomizePriceDeltas
```

*Original:* Randomizes price deltas.

### `ResetEconomy`

Zera fundos e estoque dos comerciantes

```
scum ResetEconomy
```

*Original:* Resets trader funds and amount of stocked items. Recommended to use RandomizePriceDeltas before using this command.

### `ResetPlayerBalances`

Zera dinheiro, ouro e fama de um jogador

```
scum ResetPlayerBalances <Player ID> <Please>
```

- `Player ID` — Player for which to reset all balances (cash, gold and fame)
- `Please` — Please

*Original:* Resets all balances (cash, gold and fame) for a player.

### `SetCurrencyBalance`

Define a moeda de um jogador

```
scum SetCurrencyBalance <Currency Type> <Amount> <Player>
```

- `Currency Type` — Which currency balance to set
- `Amount`
- `Player` — Which player to set for

*Original:* Sets specified currency amount to self or the specified player.

### `SetCurrencyBalanceToAll`

Define a moeda de todos do banco

```
scum SetCurrencyBalanceToAll <Currency Type> <Amount>
```

- `Currency Type` — Which currency balance to set
- `Amount`

*Original:* Sets the specified currency amount to all players in the database.

### `SetCurrencyBalanceToAllOnline`

Define a moeda de todos os conectados

```
scum SetCurrencyBalanceToAllOnline <Currency Type> <Amount>
```

- `Currency Type` — Which currency balance to set
- `Amount`

*Original:* Sets the specified currency amount to all online players.

### `SetFamePoints`

Define os pontos de fama do jogador

```
scum SetFamePoints <Amount> <Player>
```

- `Amount`
- `Player`

*Original:* Sets fame points of the specified player to the specified value.

### `SetFamePointsToAll`

Define a fama de todos, online e offline

```
scum SetFamePointsToAll <Amount>
```

- `Amount`

*Original:* Sets fame points of all online and offline players to the specified value.

### `SetFamePointsToAllOnline`

Define a fama de todos os conectados

```
scum SetFamePointsToAllOnline <Amount>
```

- `Amount`

*Original:* Sets fame points of all online players to the specified value.

### `ToggleFamePointDebugVisualization` 🔒

Liga/desliga a visualização de depuração da fama

```
scum sudo ToggleFamePointDebugVisualization
```

*Original:* Toggles accurate debug visualization of Fame Points.
