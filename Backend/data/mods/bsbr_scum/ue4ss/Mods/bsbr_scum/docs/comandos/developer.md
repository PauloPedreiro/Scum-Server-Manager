# Developer

Depuração e ferramentas internas da Gamepires.

77 comandos. Voltar ao [índice](../README.md).

🔒 = exige nível Developer, já incluído como `sudo` na linha de uso.

Pelo chat do jogo, troque `scum ` por `#` — os comandos do jogo não usam
o prefixo `bsbr`, que é só dos [comandos do mod](mod.md).

Para executar no lugar de outro jogador: `scum as Fulano SpawnItem X` no terminal,
`#bsbr @Fulano SpawnItem X` no chat.

> O resumo de cada comando está em português; a explicação de cada
> argumento e a linha *Original* são o texto da própria Gamepires, lido
> do jogo — não traduzimos para não introduzir erro no que é a referência.

> São ferramentas internas da Gamepires, feitas para desenvolvimento e não
> para uso em servidor com jogadores. Vários alteram estado que não tem como
> desfazer, e três derrubam o servidor ou o cliente de propósito:
> `CrashMajestically`, `CrashClient` e `DisableServer`.


---
### `AddBleedingInjury` 🔒

Aplica sangramento

```
scum sudo AddBleedingInjury <Body Part> <Damage> <Blood Loss Rate>
```

- `Body Part`
- `Damage`
- `Blood Loss Rate`

*Original:* Adds bleeding injury body effect to prisoner.

### `AddBodyEffect` 🔒

Aplica um efeito corporal

```
scum sudo AddBodyEffect <Body Effect>
```

- `Body Effect`

*Original:* Adds the specified prisoner body effect.

### `AddBurnInjury` 🔒

Aplica queimadura

```
scum sudo AddBurnInjury <Body Part> <Damage>
```

- `Body Part`
- `Damage`

*Original:* Adds burn injury body effect to prisoner.

### `AddGardenPlantPest` 🔒

Adiciona praga à planta

```
scum sudo AddGardenPlantPest <WholeGarden> <species> <Aphids> <value> <value> <remove>
```

- `WholeGarden` — Affect whole garden or one slot
- `species` — species
- `Aphids` — pest or disease species name, or just enter random
- `value` — (0.0 - 1.0]
- `value` — (0.0 - 1.0]
- `remove` — removes pest species

### `AddOrRemoveWidget` 🔒

Adiciona ou remove um widget da interface

```
scum sudo AddOrRemoveWidget <Action> <Widget> <Z Order>
```

- `Action` — Add or remove
- `Widget` — Widget to add / remove
- `Z Order`

*Original:* Adds or removes the specified widget.

### `AddRadiationPresence` 🔒

Aplica presença de radiação

```
scum sudo AddRadiationPresence <Radiation Amount> <Additional Change Rate>
```

- `Radiation Amount`
- `Additional Change Rate`

*Original:* Adds radiation presence body effect to prisoner.

### `ArmorAbsorptionOutput` 🔒

Registro de absorção de armadura

```
scum sudo ArmorAbsorptionOutput <Value>
```

- `Value` — Enables or disables armor absorption data logging.

*Original:* Enables or disables armor absorption data logging.

### `BaseBuildingDebug` 🔒

Depuração de construção

```
scum sudo BaseBuildingDebug <Mode>
```

- `Mode` — 0 = Disabled ; 1 = Basic ; 2 = RadialDamage ; 3 = InteractionZones ; 4 = BaseBounds

> Desabilitado no build de produção — não funciona neste servidor.

*Original:* Sets debug mode for base building.

### `BoatDebug` 🔒

Depuração de embarcação

```
scum sudo BoatDebug
```

*Original:* Enables or disables boat debug info

### `CookRecipe` 🔒

Executa uma receita de cozinha

```
scum sudo CookRecipe
```

### `CrashClient` 🔒

Derruba o **cliente**

```
scum sudo CrashClient
```

*Original:* Crashes the client.

### `CrashMajestically`

Derruba o **servidor**

```
scum CrashMajestically
```

> Desabilitado no build de produção — não funciona neste servidor.

*Original:* Crashes the server.

### `CreateEntity` 🔒

Cria entidade pelo setup

```
scum sudo CreateEntity <Setup>
```

- `Setup`

*Original:* Creates entity using the specified entity setup

### `CreateEntityOnClient` 🔒

Igual, no cliente

```
scum sudo CreateEntityOnClient <Setup>
```

- `Setup`

*Original:* Creates entity using the specified entity setup

### `DebugProjectileCollisions` 🔒

Depuração de colisão de projétil

```
scum sudo DebugProjectileCollisions <Value>
```

- `Value` — Enables or disables projectile collisions debug.

*Original:* Enables or disables projectile collisions debug.

### `DebugWeapon` 🔒

Depuração de arma

```
scum sudo DebugWeapon
```

*Original:* Weapon debugging.

### `DemolitionSkillDebug` 🔒

Depuração da perícia de demolição

```
scum sudo DemolitionSkillDebug
```

> Desabilitado no build de produção — não funciona neste servidor.

*Original:* Shows or hides demolition skill debugging.

### `DisableBodyEffects` 🔒

Remove todos e impede novos

```
scum sudo DisableBodyEffects <Disabled>
```

- `Disabled`

*Original:* Removes all existing body effects and disables effect adding.

### `DistanceDebug` 🔒

Depuração de distância

```
scum sudo DistanceDebug <Distance>
```

- `Distance`

*Original:* Enables the distance debug and sets the max possible distance.

### `DoorDebug` 🔒

Depuração de portas

```
scum sudo DoorDebug
```

*Original:* Shows or hides door debugging.

### `DrawDebugZombieCapsulesOnLegacySpawnPoints` 🔒

Cápsulas de depuração nos pontos de spawn antigos

```
scum sudo DrawDebugZombieCapsulesOnLegacySpawnPoints
```

> Desabilitado no build de produção — não funciona neste servidor.

*Original:* Draw zombie debug capsules on legacy spawn points.

### `DrawEnemyHealthBars` 🔒

Barras de vida sobre os inimigos

```
scum sudo DrawEnemyHealthBars
```

*Original:* Draws health bars above AI enemies.

### `DumpWetnessDebug` 🔒

Depuração de umidade

```
scum sudo DumpWetnessDebug
```

### `EnableGameplayMetadataLogging`

Liga o registro de metadados de jogabilidade

```
scum EnableGameplayMetadataLogging <Enable Or Not>
```

- `Enable Or Not` — 1 or 0

### `EnhancedPhotoMode` 🔒

Modo foto avançado

```
scum sudo EnhancedPhotoMode
```

### `EquipParachute` 🔒

Equipa um paraquedas

```
scum sudo EquipParachute
```

*Original:* Equips a parachute.

### `ExecuteConditionInteraction` 🔒

Executa uma interação de condição

```
scum sudo ExecuteConditionInteraction <Condition> <Condition Interaction ID>
```

- `Condition`
- `Condition Interaction ID`

*Original:* Executes the specified condition interaction.

### `Flash` 🔒

Efeito de flash

```
scum sudo Flash <Distance>
```

- `Distance`

### `GardenPlantRandomPlants` 🔒

Planta espécies aleatórias

```
scum sudo GardenPlantRandomPlants
```

### `GetMeshInfo`

Informações da malha do objeto observado

```
scum GetMeshInfo
```

*Original:* Copies mesh info used for custom quests into clipboard of a mesh being looked at

### `Inventory` 🔒

Acesso ao inventário

```
scum sudo Inventory <Entity Id> <Command>
```

- `Entity Id`
- `Command`

### `ListBodyEffects` 🔒

Lista os efeitos corporais

```
scum sudo ListBodyEffects <Body Effect>
```

- `Body Effect`

*Original:* Lists prisoner body effects.

### `ListConditionInteractions` 🔒

Lista as interações de uma condição

```
scum sudo ListConditionInteractions <Condition>
```

- `Condition`

*Original:* Lists all interactions for the specified condition.

### `ListConditions` 🔒

Lista as condições

```
scum sudo ListConditions
```

*Original:* Lists prisoner conditions.

### `ListForeignSubstances` 🔒

Substâncias absorvidas no estômago

```
scum sudo ListForeignSubstances
```

*Original:* Displays information about foreign substances currently absorbed in the stomach and intestine of the invoking prisoner.

### `ListItemsSpawnLocations` 🔒

Lista locais de spawn de item

```
scum sudo ListItemsSpawnLocations <SearchType>
```

- `SearchType`

*Original:* Lists all possible item spawn locations matching the provided search type.

### `Loot` 🔒

Simula loot dos níveis carregados e salva em arquivo

```
scum sudo Loot <Include Foliage>
```

- `Include Foliage`

*Original:* Emulates looting over the loaded levels and saves looting data into a file.

### `PlacementDebug` 🔒

Depuração de posicionamento

```
scum sudo PlacementDebug <Debug Mode>
```

- `Debug Mode` — 0 = Disabled; 1 = Basic (most useful); 2 = Grounding (not floating) 3 = Walls

*Original:* Shows or hides placement debugging.

### `PrintClientEntities` 🔒

Lista entidades do cliente no log

```
scum sudo PrintClientEntities <Option> <Option> <Option>
```

- `Option`
- `Option`
- `Option`

*Original:* Prints all client entities to the log file.

### `Quests` 🔒

Controla o sistema de missões

```
scum sudo Quests <Subcommand> <Quest Asset>
```

- `Subcommand`
- `Quest Asset`

*Original:* Control quests system.

### `RemoveBodyEffect` 🔒

Remove efeitos corporais

```
scum sudo RemoveBodyEffect <Body Effect>
```

- `Body Effect`

*Original:* Removes all prisoner body effects of the specified class or single body effect with the specified ID.

### `ReportDesync` 🔒

Inicia/para o relatório de dessincronização

```
scum sudo ReportDesync <Toggle> <Period> <Delay>
```

- `Toggle` — Toggle
- `Period` — Report period
- `Delay` — Delay time

*Original:* Starts or stops a report desync function

### `ResetAchievements` 🔒

Apaga todas as conquistas

```
scum sudo ResetAchievements
```

*Original:* Resets all achievements.

### `SendNotification` 🔒

Envia notificação a um jogador; `-1` envia a todos

```
scum sudo SendNotification <Notification> <User ID> <Message>
```

- `Notification` — Notification type to send
- `User ID` — Whom to send the message to
- `Message`

*Original:* Sends notification to target player. Type: {1, 2, .. 5} If User_id is -1, message is sent to all.

### `SetAchievementUnlocked` 🔒

Desbloqueia uma conquista Steam

```
scum sudo SetAchievementUnlocked <Achievement Name>
```

- `Achievement Name`

> Desabilitado no build de produção — não funciona neste servidor.

*Original:* Unlocks a Steam achievement.

### `SetAIInvisibility` 🔒

Invisibilidade perante a IA

```
scum sudo SetAIInvisibility <Value>
```

- `Value` — Set invisibility to true or false.

*Original:* Sets AI invisibility to true or false.

### `SetAirplaneMaxVelocity` 🔒

Velocidade máxima das aeronaves

```
scum sudo SetAirplaneMaxVelocity <Value>
```

- `Value`

*Original:* Sets airplanes' max velocity.

### `SetAllInventoryAccess` 🔒

Libera acesso a todos os inventários

```
scum sudo SetAllInventoryAccess
```

*Original:* Enables or disables all inventory access.

### `SetBladderVolume` 🔒

Define o volume da bexiga

```
scum sudo SetBladderVolume <Amount>
```

- `Amount` — Amount as either milliliters or percentage

*Original:* Sets your prisoner's bladder volume to the specified value.

### `SetBodyType` 🔒

Define o tipo físico

```
scum sudo SetBodyType
```

### `SetCraftingSearch` 🔒

Caixa de busca na interface de criação. Em desenvolvimento

```
scum sudo SetCraftingSearch
```

*Original:* Enables/disables crafting UI search box. Feature is still in development and not available to public players.

### `SetDeluxeVersion` 🔒

Força os pacotes de apoiador

```
scum sudo SetDeluxeVersion <Supporter pack version value>
```

- `Supporter pack version value`

*Original:* Force supporter packs.

### `SetExhaustion` 🔒

Define o cansaço

```
scum sudo SetExhaustion <Accumulated Fatigue>
```

- `Accumulated Fatigue` — [SU or %]

*Original:* Sets or gets prisoner’s exhaustion.

### `SetFarmingSimulationSpeed` 🔒

Velocidade da simulação agrícola

```
scum sudo SetFarmingSimulationSpeed <Value>
```

- `Value` — Speed

*Original:* Sets simulation speed for farming (gardening).

### `SetGardenNutrientsHigh` 🔒

Nutrientes do solo no máximo

```
scum sudo SetGardenNutrientsHigh
```

### `SetGardenPlantGrowthStage` 🔒

Define o estágio de crescimento da planta

```
scum sudo SetGardenPlantGrowthStage <WholeGarden> <Stage> <Growth>
```

- `WholeGarden` — Affect whole garden or one slot
- `Stage` — Plant growth stage
- `Growth` — Plant stage progress [0.0 - 1.0)

### `SetGardenPlantingTime` 🔒

Define o tempo de plantio

```
scum sudo SetGardenPlantingTime <Enabled> <Duration>
```

- `Enabled` — Enabled
- `Duration` — Duration

### `SetGender` 🔒

Define o gênero

```
scum sudo SetGender <gender> <female>
```

- `gender` — male
- `female`

*Original:* Set the gender of prisoner

### `SetInfiniteAmmo` 🔒

Munição infinita

```
scum sudo SetInfiniteAmmo
```

*Original:* Enables or disables infinite ammo.

### `SetItemDebugMode` 🔒

Modo de depuração de item

```
scum sudo SetItemDebugMode <Mode>
```

- `Mode`

*Original:* 0 = None; 1 = Basic

### `SetMalfunctionProbability` 🔒

Probabilidade de falha de arma

```
scum sudo SetMalfunctionProbability <Malfunction Name> <Malfunction Probability>
```

- `Malfunction Name`
- `Malfunction Probability`

*Original:* Sets probability of chosen malfunction.

### `SetMetabolismSimulationSpeed` 🔒

Velocidade da simulação do metabolismo

```
scum sudo SetMetabolismSimulationSpeed <Value>
```

- `Value`

*Original:* Sets or gets prisoner's metabolism simulation speed.

### `SetReplenishableResourceAmount` 🔒

Quantidade de recurso renovável

```
scum sudo SetReplenishableResourceAmount <Amount> <Area>
```

- `Amount`
- `Area` — Area of effect (centimeters)

*Original:* Sets the amount of replenishable resources in close proximity around the player.

### `SetStamina` 🔒

Define a estamina

```
scum sudo SetStamina <Stamina>
```

- `Stamina` — [SU or %]

*Original:* Sets or gets prisoner's stamina.

### `SetStomachVolume` 🔒

Define o volume do estômago

```
scum sudo SetStomachVolume <Amount>
```

- `Amount` — Amount as either milliliters or percentage

*Original:* Sets your prisoner's stomach volume to the specified value.

### `ShowVehicleDebug` 🔒

Depuração de veículo

```
scum sudo ShowVehicleDebug
```

*Original:* Shows or hides vehicle debug info.

### `ShowWeaponInfo` 🔒

Informações da arma

```
scum sudo ShowWeaponInfo
```

*Original:* Shows currently held weapon's info.

### `SkipDiseaseIncubationStage` 🔒

Pula a incubação de uma doença

```
scum sudo SkipDiseaseIncubationStage <Value>
```

- `Value` — If enabled, skips current and future disease's incubation stages.

*Original:* While enabled, skips current and future disease's incubation stages.

### `Sleep` 🔒

Faz o prisioneiro dormir

```
scum sudo Sleep <Value>
```

- `Value` — Seconds

*Original:* Suspends the game thread for the specified amount of seconds.

### `ToggleZombieNavigationLogging` 🔒

Registro de navegação dos zumbis

```
scum sudo ToggleZombieNavigationLogging
```

*Original:* Toggles Zombie Navigation Error/Warning Logging

### `TrackShots` 🔒

Rastreia disparos

```
scum sudo TrackShots
```

*Original:* Shows shots fired by current player since execution of the command.

### `TrapsDebug` 🔒

Depuração de armadilhas

```
scum sudo TrapsDebug
```

*Original:* Shows or hides traps debugging.

### `UpgradeBaseBuildingElementsWithinRadius` 🔒

Melhora construções no raio

```
scum sudo UpgradeBaseBuildingElementsWithinRadius <Radius>
```

- `Radius` — Radius within the upgrade will happen

*Original:* Upgrade all Base Bulding Elements within radius

### `VisualizeBulletTrajectories`

Desenha a trajetória dos projéteis

```
scum VisualizeBulletTrajectories
```

*Original:* Enables or disables bullet trajectory visualization.

### `VisualizePath`

Desenha o caminho de navegação

```
scum VisualizePath <start> <startLocation> <end> <endLocation>
```

- `start` — start
- `startLocation` — Transform or vector of the start location
- `end` — end
- `endLocation` — Transform or vector of the end location

*Original:* Draws a path from start to end location. Note that keywords "start" and "end" need to be put in before the locations.

### `VisualizePlayerAiming`

Desenha a mira do jogador

```
scum VisualizePlayerAiming
```

*Original:* Enables or disables player aim visualization.

### `VisualizeVehicleTrajectory`

Desenha a trajetória do veículo

```
scum VisualizeVehicleTrajectory <Vehicle> <Sampling Interval>
```

- `Vehicle` — Vehicle to spawn
- `Sampling Interval`
