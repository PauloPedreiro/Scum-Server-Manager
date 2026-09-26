# Mundo

Clima, tempo, eventos e encontros.

28 comandos. Voltar ao [índice](../README.md).

🔒 = exige nível Developer, já incluído como `sudo` na linha de uso.

Pelo chat do jogo, troque `scum ` por `#` — os comandos do jogo não usam
o prefixo `bsbr`, que é só dos [comandos do mod](mod.md).

Para executar no lugar de outro jogador: `scum as Fulano SpawnItem X` no terminal,
`#bsbr @Fulano SpawnItem X` no chat.

> O resumo de cada comando está em português; a explicação de cada
> argumento e a linha *Original* são o texto da própria Gamepires, lido
> do jogo — não traduzimos para não introduzir erro no que é a referência.

---
### `AdvancePlaytime` 🔒

Avança o tempo de jogo. Só em banco de dados novo

```
scum sudo AdvancePlaytime <time>
```

- `time` — time how much to advance playtime.

*Original:* Advances playtime (on server, which is then propagated to clients). Do this on a fresh database as systems that depend on playtime could exhibit unpredicted behaviour

### `CancelVote`

Cancela a votação em andamento

```
scum CancelVote
```

*Original:* Cancels active voting.

### `ClearEncounterCooldowns` 🔒

Zera o tempo de espera entre encontros

```
scum sudo ClearEncounterCooldowns
```

*Original:* Clears invoking player's encounter cooldowns.

### `DestroyEncountersAtPlayerLocation`

Destrói os encontros na sua posição

```
scum DestroyEncountersAtPlayerLocation
```

*Original:* Destroys all encounters at invoking player's location.

### `DrawNearbyEncounters` 🔒

Desenha o centro dos encontros próximos

```
scum sudo DrawNearbyEncounters <Extent>
```

- `Extent` — Encounter search extent

*Original:* Draw all nearby encounter center locations.

### `DumpEncounterManagerData` 🔒

Exporta os dados do gerenciador de encontros para JSON

```
scum sudo DumpEncounterManagerData
```

*Original:* Dumps current encounter manager data to JSON files.

### `EndTournamentMode`

Encerra o modo torneio

```
scum EndTournamentMode
```

*Original:* Cancels tournament mode.

### `ForceAnimalEncounter`

Força um encontro com animais na sua posição

```
scum ForceAnimalEncounter
```

*Original:* Spawns an animal encounter at player's location.

### `ForceBBEncounterOnNearbyOwnedBase`

Força um ataque a uma base próxima, se não houver encontro ativo

```
scum ForceBBEncounterOnNearbyOwnedBase <Player>
```

- `Player` — Player

*Original:* Chooses a random BB encounter and forces it to occur on a nearby owned base as soon as possible, provided there isn't an active encounter already present.

### `ForceDropshipEncounter`

Força um encontro de nave de carga na sua posição

```
scum ForceDropshipEncounter
```

*Original:* Spawns a dropship encounter at player's location.

### `ListActiveAbandonedBunkers`

Lista os bunkers abandonados ativos

```
scum ListActiveAbandonedBunkers
```

### `ListActiveSecretBunkers`

Lista os bunkers secretos ativos

```
scum ListActiveSecretBunkers
```

### `ListWeatherControllerOverrides` 🔒

Lista as sobreposições de clima ativas

```
scum sudo ListWeatherControllerOverrides
```

*Original:* Weather controller debug

### `NightBrightness`

Ajusta o brilho da noite

```
scum NightBrightness <Amount [0-1]>
```

- `Amount [0-1]` — Amount to set between 0 and 1

*Original:* Sets night brightness level.

### `PrintGlobalRaidProtectionRaidTimes`

Mostra os horários de proteção contra raide configurados

```
scum PrintGlobalRaidProtectionRaidTimes
```

*Original:* Prints the global raid protection raid times as configured on the server.

### `ScheduleCargoDrop`

Agenda uma queda de carga perto de um prisioneiro

```
scum ScheduleCargoDrop <Player>
```

- `Player` — Player whose location to use

*Original:* Schedules a cargo drop near a prisoner.

### `ScheduleWorldEvent`

Agenda um evento de mundo em local e tipo definidos

```
scum ScheduleWorldEvent <World Event> <X> <Y> <Z>
```

- `World Event` — World event to schedule
- `X` — X coordinate
- `Y` — Y coordinate
- `Z` — Z coordinate

*Original:* Schedules a world event of the specified type at the specified location.

### `SetDecayTimeDilation` 🔒

Altera a velocidade de decomposição dos itens

```
scum sudo SetDecayTimeDilation <Value>
```

- `Value`

*Original:* Sets decay time dilation for all items.

### `SetTime`

Define a hora do dia

```
scum SetTime <Time>
```

- `Time` — Time of day [0-24]

*Original:* Sets time of day to the specified value.

### `SetTimeSpeed` 🔒

Altera a velocidade de passagem do tempo

```
scum sudo SetTimeSpeed <Value>
```

- `Value`

*Original:* Sets the time of day speed to a specified value.

### `SetWeather`

Define o clima

```
scum SetWeather <Weather>
```

- `Weather` — Weather to set to (0-1)

*Original:* Sets weather to the specified value.

### `SetWeatherControllerOverrideActive` 🔒

Depuração do controlador de clima

```
scum sudo SetWeatherControllerOverrideActive <Type> <Value>
```

- `Type` — Weather controller override type
- `Value`

*Original:* Weather controller debug

### `SetWeatherControllerOverrideValue` 🔒

Depuração do controlador de clima

```
scum sudo SetWeatherControllerOverrideValue <Type> <Value>
```

- `Type`
- `Value`

*Original:* Weather controller debug

### `ShowRespawnTimers` 🔒

Mostra os tempos de renascimento

```
scum sudo ShowRespawnTimers <RespawnOption>
```

- `RespawnOption` — Which respawn option to show the times for

> Desabilitado no build de produção — não funciona neste servidor.

*Original:* Shows respawn times for given respawn option.

### `StartTournamentMode`

Inicia o modo torneio

```
scum StartTournamentMode <Center X> <Center Y> <Delay> <Duration>
```

- `Center X` — X coordinate of the center
- `Center Y` — Y coordinate of the center
- `Delay` — Delay to start
- `Duration` — Duration of the tournament mode

*Original:* Initiates tournament mode.

### `ToggleAmbientSound`

Liga ou desliga o som ambiente

```
scum ToggleAmbientSound
```

*Original:* Enable or disable ambient sounds in drone mode

### `ToggleFog`

Liga/desliga a névoa no modo drone

```
scum ToggleFog
```

*Original:* Enable or disable fog in drone mode

### `Vote`

Inicia uma votação

```
scum Vote <Vote Topic>
```

- `Vote Topic` — Topic on which to vote

*Original:* Destroys all base building elements for squad with the provided id.
