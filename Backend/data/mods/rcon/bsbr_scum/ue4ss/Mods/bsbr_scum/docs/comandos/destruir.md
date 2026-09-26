# Destruir

Remover veículos, itens, construções e cadáveres.

16 comandos. Voltar ao [índice](../README.md).

🔒 = exige nível Developer, já incluído como `sudo` na linha de uso.

Pelo chat do jogo, troque `scum ` por `#` — os comandos do jogo não usam
o prefixo `bsbr`, que é só dos [comandos do mod](mod.md).

Para executar no lugar de outro jogador: `scum as Fulano SpawnItem X` no terminal,
`#bsbr @Fulano SpawnItem X` no chat.

> O resumo de cada comando está em português; a explicação de cada
> argumento e a linha *Original* são o texto da própria Gamepires, lido
> do jogo — não traduzimos para não introduzir erro no que é a referência.

> Comandos com `WithinRadius` aceitam um raio e agem **em volta da sua
> posição**, ou de um local informado. Não há confirmação nem desfazer.


---
### `DestroyAllAnimalsWithinRadius`

Destrói todos os animais no raio

```
scum DestroyAllAnimalsWithinRadius <Radius [m]>
```

- `Radius [m]` — Radius in meters

*Original:* Destroys all animals within a given radius

### `DestroyAllBaseBuildingElementsForFlag`

Destrói todas as construções vinculadas a uma bandeira

```
scum DestroyAllBaseBuildingElementsForFlag <Flag ID> <Please>
```

- `Flag ID` — Flag for which to destroy all base building elements
- `Please` — Please

*Original:* Destroys all base building elements for squad with the provided id.

### `DestroyAllBaseBuildingElementsForPlayer`

Destrói todas as construções de um jogador

```
scum DestroyAllBaseBuildingElementsForPlayer <Player ID> <Please>
```

- `Player ID` — Player for which to destroy all base building elements
- `Please` — Please

*Original:* Destroys all base building elements for player with the provided id.

### `DestroyAllBaseBuildingElementsForSquad`

Destrói todas as construções de um esquadrão

```
scum DestroyAllBaseBuildingElementsForSquad <Squad ID> <Please>
```

- `Squad ID` — Squad for which to destroy all base building elements
- `Please` — Please

*Original:* Destroys all base building elements for squad with the provided id.

### `DestroyAllBaseBuildingWithinRadius`

Destrói todas as construções no raio

```
scum DestroyAllBaseBuildingWithinRadius <Radius [m]> <Location>
```

- `Radius [m]` — Radius in meters
- `Location` — Location or transform around which to destroy base building elements

*Original:* Destroys all base building elements within a given radius around given location or player if none given.

### `DestroyAllFlagsForPlayer`

Destrói todas as bandeiras de um jogador

```
scum DestroyAllFlagsForPlayer <Player>
```

- `Player` — Player whose flags to destroy

*Original:* Destroys all flags owned by the player

### `DestroyAllItemsWithinRadius`

Destrói todos os itens no raio

```
scum DestroyAllItemsWithinRadius <Item> <Radius [m]> <Location>
```

- `Item` — Type of item to destroy
- `Radius [m]` — Radius in meters
- `Location` — Location or transform around which to destroy items

*Original:* Destroys all items within a given radius around given location or player if none given.

### `DestroyAllRazorsWithinRadius`

Destrói todos os Razors no raio

```
scum DestroyAllRazorsWithinRadius <Radius [m]> <Location>
```

- `Radius [m]` — Radius in meters
- `Location` — Location or transform around which to destroy razors

*Original:* Destroys all razors within a given radius around given location or player if none given.

### `DestroyAllVehicles`

Destrói **todos** os veículos do servidor

```
scum DestroyAllVehicles <Please> <PrimaryAssetId>
```

- `Please` — Pretty please?
- `PrimaryAssetId` — PrimaryAssetId of the vehicle

*Original:* Destroys all vehicles.

### `DestroyArmedNPCsWithinRadius`

Destrói todos os NPCs armados no raio

```
scum DestroyArmedNPCsWithinRadius <Radius> <Location>
```

- `Radius` — Radius in meters
- `Location` — Location or transform around which to destroy armed NPCs.

*Original:* Destroys all armedNPCs within a given radius around given location or player if none given.

### `DestroyCorpsesWithinRadius`

Destrói todos os cadáveres no raio

```
scum DestroyCorpsesWithinRadius <Radius [m]> <Should destroy clothes on corpses?> <Location>
```

- `Radius [m]` — Radius in meters
- `Should destroy clothes on corpses?`
- `Location` — Location or transform around which to destroy corpses

*Original:* Destroys all corpses within a given radius around given location or player if none given.

### `DestroyEntity` 🔒

Destrói entidades pelo setup, ou uma pelo ID

```
scum sudo DestroyEntity <Setup or ID>
```

- `Setup or ID`

*Original:* Destroys all entities having the specified setup or a single entity if ID is provided.

### `DestroyEntityOnClient` 🔒

Igual ao anterior, no cliente

```
scum sudo DestroyEntityOnClient <Setup or ID>
```

- `Setup or ID`

*Original:* Destroys all entities having the specified setup or a single entity if ID is provided.

### `DestroyFlag`

Destrói a bandeira pelo ID

```
scum DestroyFlag <Flag>
```

- `Flag` — Flag ID to destroy

*Original:* Destroys flag having the specified ID.

### `DestroyVehicle`

Destrói o veículo pelo apelido ou ID

```
scum DestroyVehicle <Vehicle>
```

- `Vehicle` — Vehicle to destroy

*Original:* Destroys vehicle having the specified alias or ID.

### `DestroyZombiesWithinRadius`

Destrói todos os zumbis no raio

```
scum DestroyZombiesWithinRadius <Radius> <Location>
```

- `Radius` — Radius in meters
- `Location` — Location or transform around which to destroy zombies

*Original:* Destroys all zombies within a given radius around given location or player if none given.
