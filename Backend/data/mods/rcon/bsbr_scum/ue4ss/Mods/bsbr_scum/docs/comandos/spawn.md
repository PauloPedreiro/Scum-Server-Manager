# Spawn

Criar itens, veículos, zumbis, animais e NPCs.

29 comandos. Voltar ao [índice](../README.md).

🔒 = exige nível Developer, já incluído como `sudo` na linha de uso.

Pelo chat do jogo, troque `scum ` por `#` — os comandos do jogo não usam
o prefixo `bsbr`, que é só dos [comandos do mod](mod.md).

Para executar no lugar de outro jogador: `scum as Fulano SpawnItem X` no terminal,
`#bsbr @Fulano SpawnItem X` no chat.

> O resumo de cada comando está em português; a explicação de cada
> argumento e a linha *Original* são o texto da própria Gamepires, lido
> do jogo — não traduzimos para não introduzir erro no que é a referência.

> Os identificadores válidos estão em [itens.md](itens.md) (1134),
> [veiculos.md](veiculos.md) (17) e [zumbis.md](zumbis.md) (25).


---
### `ListAnimals`

Lista os tipos de animal disponíveis

```
scum ListAnimals <Filter>
```

- `Filter`

*Original:* Prints the optionally filtered list of all animals available for spawning via the SpawnAnimal command.

### `ListDLCItems`

Lista os itens de DLC

```
scum ListDLCItems
```

### `ListItems`

Lista os itens disponíveis, com filtro opcional

```
scum ListItems <Filter>
```

- `Filter`

*Original:* Prints the optionally filtered list of all items available for spawning via the SpawnItem command.

### `ListSpawnedAnimals`

Lista os animais já existentes

```
scum ListSpawnedAnimals
```

*Original:* Prints the list of all currently spawned animals. Argument 'true' will copy the result to the clipboard.

### `ListSpawnedArmedNPCs`

Lista os NPCs armados existentes

```
scum ListSpawnedArmedNPCs
```

*Original:* Prints the list of all currently spawned armed NPCs. Argument 'true' will copy the result to the clipboard.

### `ListSpawnedVehicles`

Lista os veículos já existentes no mundo

```
scum ListSpawnedVehicles <Should Copy> <Category> <Category> <Category> <Category> <Category>
```

- `Should Copy` — Should copy to clipboard
- `Category`
- `Category`
- `Category`
- `Category`
- `Category`

*Original:* Prints the list of all currently spawned vehicles. Argument 'true' will copy the result to the clipboard.

### `ListVehicles`

Lista os veículos disponíveis

```
scum ListVehicles <Filter>
```

- `Filter`

*Original:* Prints the optionally filtered list of all vehicles available for spawning via the SpawnVehicle command.

### `ListZombies`

Lista os tipos de zumbi disponíveis

```
scum ListZombies <Filter>
```

- `Filter`

*Original:* Prints the optionally filtered list of all zombies available for spawning via the SpawnZombie command.

### `RenameVehicle`

Renomeia um veículo pelo apelido ou ID

```
scum RenameVehicle <Vehicle> <Name>
```

- `Vehicle` — Which vehicle to rename
- `Name` — New Name

*Original:* Renames vehicle having the specified alias or ID.

### `SetHealthToItemInHands`

Define a integridade do item na mão

```
scum SetHealthToItemInHands <Health [0-1]>
```

- `Health [0-1]` — Health between 0 and 1.0

*Original:* Sets health to current item in hands.

### `SetMountedVehicleProperty` 🔒

Altera propriedade do veículo em que está montado

```
scum sudo SetMountedVehicleProperty <Property Name> <Value>
```

- `Property Name`
- `Value` — Property Value. Add % suffix to specify value as a percentage of a maximum value instead of absolute value.

*Original:* Sets specified property on the currently mounted vehicle.

### `ShowVehicleInfo`

Mostra informação de todos os veículos

```
scum ShowVehicleInfo
```

*Original:* Shows info for all vehicles on the map.

### `ShowVehicleLocations`

Mostra a posição dos veículos no mapa

```
scum ShowVehicleLocations
```

*Original:* Shows all vehicle locations on map.

### `SpawnAllItems` 🔒

Cria **todos** os 1134 itens

```
scum sudo SpawnAllItems <Inventory> <Grouping cutoff point> <Distance between inventories>
```

- `Inventory` — Inventory to place the items in
- `Grouping cutoff point` — Any item classes with less or equal amounts of items will be grouped together in a "Random" chest
- `Distance between inventories` — Distance between two neighbouring inventories

*Original:* Spawns a bunch of inventories with all of the items in the game.

### `SpawnAnimal`

Cria animais do tipo indicado

```
scum SpawnAnimal <Animal> <Count> <Animal Property> <Property Value>
```

- `Animal` — Animal to spawn
- `Count` — Number of animals to spawn
- `Animal Property`
- `Property Value`

*Original:* Spawns a specified amount of the given animal type (Default count value is 1).

### `SpawnArmedNPC`

Cria NPCs armados do tipo indicado

```
scum SpawnArmedNPC <Armed NPC> <Count> <Property> <Property value>
```

- `Armed NPC` — Which armed NPC to spawn
- `Count` — Number of armed NPCs to spawn
- `Property` — Property of the Armed NPC
- `Property value`

*Original:* Spawns a specified amount of the given armed NPC type (Default count value is 1).

### `SpawnBrenner` 🔒

Cria o Brenner (chefe)

```
scum sudo SpawnBrenner
```

*Original:* Spawn debug Brenner character.

### `SpawnDebugAnimalTrack` 🔒

Cria rastro de animal para depuração

```
scum sudo SpawnDebugAnimalTrack <AnimalClass> <VisualIndex>
```

- `AnimalClass`
- `VisualIndex`

*Original:* Spawns a temporary animal track.

### `SpawnInventoryFullOf`

Enche o inventário do item indicado

```
scum SpawnInventoryFullOf <Inventory> <SetCount> <Items>
```

- `Inventory` — Inventory to place the items in
- `SetCount` — Number of sets to spawn, 0 spawns as many as can fit
- `Items` — Items to spawn into the inventory

Os últimos 1 argumento(s) podem repetir.

*Original:* Spawns an inventory full of N sets of items

### `SpawnItem`

Cria um ou mais itens à sua frente

```
scum SpawnItem <Item> <Count> <Item Property> <Property Value>
```

- `Item` — Item to spawn
- `Count` — Number of items to spawn
- `Item Property`
- `Property Value`

Os últimos 2 argumento(s) podem repetir.

*Original:* Spawns one or more items in front of invoking player.

### `SpawnItem2`

Cria um item — variante com parâmetros diferentes

```
scum SpawnItem2 <Item>
```

- `Item` — Item to spawn

*Original:* Spawns item in front of invoking player. Can use multiple words for finding item suggestions, e.g. #spawnitem2 weapon suppressor ak.

### `SpawnRandomAnimal`

Cria animais aleatórios

```
scum SpawnRandomAnimal <Count> <Animal Property> <Value>
```

- `Count` — Number of animals to spawn
- `Animal Property`
- `Value` — Property value

*Original:* Spawns a specified amount of random animals (default value is 1).

### `SpawnRandomZombie`

Cria zumbis de tipos aleatórios

```
scum SpawnRandomZombie <Count> <Zombie Property> <Property Value>
```

- `Count` — Number of zombies to spawn
- `Zombie Property`
- `Property Value`

*Original:* Spawns a specified amount of random zombie types (default value is 1).

### `SpawnRandomZombie2`

Cria um zumbi aleatório — variante com parâmetros diferentes

```
scum SpawnRandomZombie2 <Count> <Zombie Property> <Property Value>
```

- `Count` — Number of zombies to spawn
- `Zombie Property`
- `Property Value`

*Original:* Spawns a specified amount of random zombie types (default value is 1).

### `SpawnRazor`

Cria o Razor

```
scum SpawnRazor <Location>
```

- `Location` — Override spawn location.

*Original:* Spawns debug Razor character.

### `SpawnReflectionSphere` 🔒

Cria esfera de reflexão, para testes gráficos

```
scum sudo SpawnReflectionSphere
```

*Original:* Spawns a reflection sphere for testing ambient reflections.

### `SpawnVehicle`

Cria um veículo à sua frente

```
scum SpawnVehicle <Vehicle> <Count> <Vehicle Property> <Property value> <Vehicle Property> <Property value>
```

- `Vehicle` — Vehicle to spawn
- `Count` — Number of vehicles to spawn
- `Vehicle Property`
- `Property value`
- `Vehicle Property`
- `Property value`

*Original:* Spawns vehicle in front of invoking player.

### `SpawnZombie`

Cria zumbis do tipo indicado

```
scum SpawnZombie <Zombie> <Count> <Property> <Property value>
```

- `Zombie` — Which zombie to spawn
- `Count` — Number of zombies to spawn
- `Property` — Property of the zombie
- `Property value`

*Original:* Spawns a specified amount of the given zombie type (Default count value is 1).

### `VehicleCheat` 🔒

Trapaças de veículo

```
scum sudo VehicleCheat <Cheat type> <Movement speed>
```

- `Cheat type`
- `Movement speed`
