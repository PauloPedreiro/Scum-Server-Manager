# Jogadores

Listar, expulsar, banir, silenciar, teleportar.

47 comandos. Voltar ao [índice](../README.md).

🔒 = exige nível Developer, já incluído como `sudo` na linha de uso.

Pelo chat do jogo, troque `scum ` por `#` — os comandos do jogo não usam
o prefixo `bsbr`, que é só dos [comandos do mod](mod.md).

Para executar no lugar de outro jogador: `scum as Fulano SpawnItem X` no terminal,
`#bsbr @Fulano SpawnItem X` no chat.

> O resumo de cada comando está em português; a explicação de cada
> argumento e a linha *Original* são o texto da própria Gamepires, lido
> do jogo — não traduzimos para não introduzir erro no que é a referência.

---
### `Announce`

Envia um anúncio a todos os jogadores conectados

```
scum Announce <Message>
```

- `Message` — Announcement message

*Original:* Sends the announcement message to all currently connected players.

### `Ban`

Expulsa e impede o jogador de reconectar até ser desbanido

```
scum Ban <SteamID64>
```

- `SteamID64` — Steam ID of player to ban

*Original:* Kicks the specified player from the game and prevents him or her from connecting to this server until unbanned.

### `ClearFakeName`

Remove o nome falso

```
scum ClearFakeName
```

*Original:* Clears a fake name on the server.

### `DumpAllSquadsInfoList`

Copia a lista de todos os esquadrões e membros

```
scum DumpAllSquadsInfoList
```

*Original:* Makes a list of all squads and its members on your clipboard.

### `FindSquadMember`

Localiza um membro pelo ID e mostra o esquadrão

```
scum FindSquadMember <Player or SteamID64>
```

- `Player or SteamID64` — Steam ID of wanted player

*Original:* Find squad member by id and display its squad info. If second argument is 'true', this will copy the result to the clipboard.

### `GetSteamID`

Obtém o SteamID a partir do nome do jogador

```
scum GetSteamID <Player>
```

- `Player`

*Original:* Gets the Steam ID of player with selected player name.

### `GetSteamIDByRank`

Obtém o SteamID pelo posto no ranking de eventos

```
scum GetSteamIDByRank <Rank>
```

- `Rank` — Player rank

*Original:* Gets Steam ID of player with selected rank on the Events rankings.

### `Kick`

Expulsa o jogador do servidor

```
scum Kick <Player>
```

- `Player`

*Original:* Kicks the specified player from the game.

### `Knockout` 🔒

Desmaia o prisioneiro

```
scum sudo Knockout <Duration> <Player>
```

- `Duration` — Duration [seconds]
- `Player`

*Original:* Adds knockout body effect to own prisoner, or another players prisoner if player is provided.

### `LeaveCorpse` 🔒

Larga seu cadáver no chão

```
scum sudo LeaveCorpse
```

*Original:* Drops your corpse on the ground.

### `ListFlags`

Lista as bandeiras de base

```
scum ListFlags <Page Number>
```

- `Page Number`

*Original:* Prints the list of all placed flags with their owners and locations. First argument is the page number to list. If second argument is 'true', this will copy the results to the clipboard.

### `ListMutedPlayers`

Lista os jogadores silenciados por `Mute`

```
scum ListMutedPlayers
```

*Original:* Lists all currently muted players.

### `ListPlayers`

Lista todos os jogadores conectados. Argumento `true` copia o resultado para a área de transferência

```
scum ListPlayers
```

*Original:* Prints the list of all players currently connected to this server. Argument 'true' will copy the result to the clipboard.

### `ListSilencedPlayers`

Lista os jogadores silenciados por `Silence`

```
scum ListSilencedPlayers <Should Copy>
```

- `Should Copy` — Should copy to clipboard

*Original:* Lists all currently silenced players. Argument 'true' will copy the result to the clipboard.

### `ListSquadMembers`

Lista os membros de um esquadrão

```
scum ListSquadMembers <Squad>
```

- `Squad` — From which squad to list players

*Original:* Prints the list of all squad members. Argument is squad name or squad id. If second argument is 'true', this will copy the result to the clipboard.

### `ListSquads`

Lista os esquadrões, por página

```
scum ListSquads <Page Number>
```

- `Page Number`

*Original:* Prints the list of squads. First argument is the page to list. If second argument is 'true', this will copy the result to the clipboard.

### `Location`

Mostra a posição do jogador indicado, ou a sua se omitido

```
scum Location <Player>
```

- `Player` — Whose location to show

*Original:* Prints the location of the specified player or your location if the player is omitted. Copies the result to the clipboard if desired.

### `MapTeleport`

Teleporte pelo mapa

```
scum MapTeleport
```

*Original:* Next click on the map will teleport the user to the clicked location

### `Mute`

Oculta as mensagens do jogador (só para quem silenciou)

```
scum Mute <Player>
```

- `Player` — Player to mute

*Original:* Hides messages from the muted player.

### `PlayerInfo`

Informações do jogador

```
scum PlayerInfo <Player Steam ID> <Show skills>
```

- `Player Steam ID` — Player Steam ID
- `Show skills` — Show skill info

*Original:* Lists information about the player

### `ResetSquadInfo`

Zera nome e informações do esquadrão

```
scum ResetSquadInfo <Squad>
```

- `Squad`

*Original:* Resets squad name and information. Argument is squad name or ID.

### `SetAttributes` 🔒

Lê ou define os atributos base

```
scum sudo SetAttributes <Strength> <Constitution> <Dexterity> <Intelligence>
```

- `Strength`
- `Constitution`
- `Dexterity`
- `Intelligence`

*Original:* Sets or gets prisoner's (base) attributes

### `SetFakeName`

Define um nome falso no servidor

```
scum SetFakeName <Fake Name>
```

- `Fake Name` — Fake name to set

*Original:* Sets a fake name on the server.

### `SetGodMode`

Liga/desliga invulnerabilidade

```
scum SetGodMode
```

*Original:* Enables or disables god mode.

### `SetImmortality` 🔒

Imortalidade

```
scum sudo SetImmortality
```

*Original:* Sets or gets prisoner's immortality mode.

### `SetInfiniteOxygen` 🔒

Oxigênio infinito

```
scum sudo SetInfiniteOxygen
```

*Original:* Sets or gets prisoner's infinite oxygen mode.

### `SetInfiniteStamina` 🔒

Estamina infinita

```
scum sudo SetInfiniteStamina
```

*Original:* Sets or gets prisoner's infinite stamina mode.

### `SetSkillLevel` 🔒

Define o nível de uma perícia

```
scum sudo SetSkillLevel <Skill Name> <Skill Level Value> <Skill Experience Value>
```

- `Skill Name`
- `Skill Level Value`
- `Skill Experience Value`

*Original:* Sets level of chosen skill.

### `SetSuperJump` 🔒

Super salto

```
scum sudo SetSuperJump
```

*Original:* Enables or disables super jump.

### `ShowAnimalsLocation`

Mostra a posição dos animais

```
scum ShowAnimalsLocation <Show currently active animal's location>
```

- `Show currently active animal's location`

*Original:* Enables or disables animal location visualization

### `ShowArmedNPCsLocation`

Mostra a posição dos NPCs armados

```
scum ShowArmedNPCsLocation <Show currently active armed NPC's location>
```

- `Show currently active armed NPC's location`

*Original:* Enables or disables armed NPCs location visualization

### `ShowFlagInfo`

Informações da bandeira de base

```
scum ShowFlagInfo
```

*Original:* Shows flag owners on map.

### `ShowFlagLocations`

Mostra a posição das bandeiras de base

```
scum ShowFlagLocations
```

*Original:* Shows all flag locations on map.

### `ShowNameplates`

Mostra as plaquetas de nome dos outros jogadores

```
scum ShowNameplates <Show all other players' nameplates>
```

- `Show all other players' nameplates`

*Original:* Shows all other player nameplates.

### `ShowOtherPlayerInfo`

Mostra informações dos outros jogadores (nome, posição)

```
scum ShowOtherPlayerInfo
```

*Original:* Enables display of other players’ information (Name, Location etc.).

### `ShowOtherPlayerLocations`

Liga/desliga a posição dos outros jogadores no mapa

```
scum ShowOtherPlayerLocations
```

*Original:* Enables or disables displaying of other player locations on the map.

### `ShowZombiesLocation`

Mostra a posição dos zumbis

```
scum ShowZombiesLocation <Show currently active zombie's location>
```

- `Show currently active zombie's location`

*Original:* Enables or disables puppet location visualization

### `Silence`

Impede o jogador de escrever no chat para os demais

```
scum Silence <Player> <Duration [hours]> <Channel>
```

- `Player` — Player to silence
- `Duration [hours]` — Duration (hours), 0 or no argument = Indefinitely
- `Channel` — Channel in which to silence

*Original:* Prevents the silenced player from sending messages to other players.

### `SquadInfo`

Informações do esquadrão

```
scum SquadInfo <Player ID>
```

- `Player ID` — Player for whos squad info to show

*Original:* Destroys all base building elements for squad with the provided id.

### `Teleport`

Teleporta para as coordenadas X Y Z

```
scum Teleport <X> <Y> <Z> <Player>
```

- `X` — X coordinate
- `Y` — Y coordinate
- `Z` — Z coordinate
- `Player` — Player to teleport

*Original:* Teleports the specified player to the specified location. If player is unspecified, teleports you.

### `TeleportTo`

Teleporta até outro jogador

```
scum TeleportTo <Player Target> <Teleportee>
```

- `Player Target` — Player to teleport to
- `Teleportee` — Which player to teleport

*Original:* Teleports the specified player to another player. If player to teleport is unspecified, teleports you.

### `TeleportTo3pm`

Teleporta para o marcador do mapa

```
scum TeleportTo3pm <Player>
```

- `Player` — Player to teleport

*Original:* Teleports the specified player to a random location. If player is unspecified, teleports you.

### `TeleportToMe`

Traz o jogador para a sua frente

```
scum TeleportToMe <Player>
```

- `Player` — Player to teleport

*Original:* Teleports the specified player in front of you.

### `TeleportToVehicle`

Teleporta até um veículo, pelo apelido ou ID

```
scum TeleportToVehicle <Vehicle> <Teleportee>
```

- `Vehicle` — Vehicle to teleport to
- `Teleportee` — Which player to teleport

*Original:* Teleports the specified player to vehicle having the specified alias or ID. If player is unspecified, teleports you.

### `Unban`

Remove o banimento

```
scum Unban <Player SteamID64>
```

- `Player SteamID64` — Player Steam ID to unban

*Original:* Lifts the ban on the specified player so he or she can connect to this server again.

### `Unmute`

Desfaz o `Mute`

```
scum Unmute <Player>
```

- `Player` — Player to unmute

*Original:* Re-enables chat messaging for the specified player.

### `Unsilence`

Desfaz o `Silence`

```
scum Unsilence <Player> <Channel>
```

- `Player` — Player to unsilence
- `Channel` — Channel in which to unsilence

*Original:* Re-enables chat messaging for the specified player.
