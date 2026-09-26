# Servidor

Informação, manutenção e controle de acesso.

22 comandos. Voltar ao [índice](../README.md).

🔒 = exige nível Developer, já incluído como `sudo` na linha de uso.

Pelo chat do jogo, troque `scum ` por `#` — os comandos do jogo não usam
o prefixo `bsbr`, que é só dos [comandos do mod](mod.md).

Para executar no lugar de outro jogador: `scum as Fulano SpawnItem X` no terminal,
`#bsbr @Fulano SpawnItem X` no chat.

> O resumo de cada comando está em português; a explicação de cada
> argumento e a linha *Original* são o texto da própria Gamepires, lido
> do jogo — não traduzimos para não introduzir erro no que é a referência.

> **`DisableServer` é a pior armadilha desta lista.** Ele expulsa e impede
> a reconexão de todo mundo que não seja developer — inclusive você, que é
> apenas admin. Recuperar exige `EnableServer`, que também é bloqueado.
> Não execute em produção.


---
### `CheckServerTime`

Mostra a hora local do servidor

```
scum CheckServerTime
```

*Original:* Prints the server's local time.

### `DisableServer` 🔒

Bloqueia a entrada de todos que não são developer — inclusive você

```
scum sudo DisableServer
```

*Original:* Restricts non-developer users from connecting to this server.

### `EnableAdminViolations` 🔒

Registro de violações de admin

```
scum sudo EnableAdminViolations <Enable>
```

- `Enable` — Should Admin violations be logged or not

### `EnableServer` 🔒

Libera a entrada novamente

```
scum sudo EnableServer
```

*Original:* Enables non-developer users to connect to this server.

### `Exec` 🔒

Console da Unreal, no cliente

```
scum sudo Exec <Command>
```

- `Command` — Command to execute

> Desabilitado no build de produção — não funciona neste servidor.

*Original:* Executes UE4 console command locally.

### `ExecOnServer` 🔒

Console da Unreal, no servidor

```
scum sudo ExecOnServer <Command>
```

- `Command` — Command to execute

> Desabilitado no build de produção — não funciona neste servidor.

*Original:* Executes UE4 console command on a server.

### `ExportCurrentLootTree`

Exporta a árvore de loot em uso

```
scum ExportCurrentLootTree
```

*Original:* Exports the current item loot tree into 'SaveFiles\Loot\Nodes\Current'

### `ExportDefaultItemSpawnerPresets`

Exporta os presets padrão dos geradores de item

```
scum ExportDefaultItemSpawnerPresets
```

*Original:* Exports default item spawner presets into 'SaveFiles\Loot\Spawners\Presets\Default'

### `ExportDefaultItemSpawningCooldownGroups`

Exporta os grupos de espera de geração de item

```
scum ExportDefaultItemSpawningCooldownGroups
```

*Original:* Exports default item spawning cooldowns into 'SaveFiles\Loot\CooldownGroups\Default\CooldownGroups.json'

### `ExportDefaultItemSpawningParameters`

Exporta os parâmetros de geração de item — é daqui que sai a lista dos 1134 IDs

```
scum ExportDefaultItemSpawningParameters
```

*Original:* Exports default item spawning parameters into 'SaveFiles\Loot\Items\Default\Parameters.json'

### `ExportDefaultLootTree`

Exporta a árvore de loot padrão

```
scum ExportDefaultLootTree
```

*Original:* Exports the default item loot tree into 'SaveFiles\Loot\Nodes\Default'

### `ExportItemSpawnerPresetsInZone`

Exporta os presets de gerador de item da zona

```
scum ExportItemSpawnerPresetsInZone <Top Left X> <Top Left Y> <Bottom Right X> <Bottom Right Y> <Directory Name>
```

- `Top Left X`
- `Top Left Y`
- `Bottom Right X`
- `Bottom Right Y`
- `Directory Name`

*Original:* Exports item spawner presets in the specified zone into the specified directory

### `ExportQuests`

Exporta as missões

```
scum ExportQuests
```

*Original:* Exports default quest configuration

### `GrantElevatedStatus` 🔒

Concede status elevado

```
scum sudo GrantElevatedStatus <SteamID64>
```

- `SteamID64` — Steam ID of player

### `ListFeatureFlags`

Lista o estado das chaves de funcionalidade

```
scum ListFeatureFlags
```

> Desabilitado no build de produção — não funciona neste servidor.

*Original:* Lists the current state of all feature flags

### `PrintServerEntities` 🔒

Lista entidades do servidor no log

```
scum sudo PrintServerEntities <Option> <Option> <Option>
```

- `Option`
- `Option`
- `Option`

*Original:* Prints all server entities to the log file.

### `ReloadCustomMapConfig`

Recarrega as bordas de mapa do arquivo de configuração

```
scum ReloadCustomMapConfig
```

*Original:* Forces reload of custom map border settings from config.

### `ReloadLootCustomizationsAndResetSpawners`

Recarrega as customizações de loot e reinicia os geradores

```
scum ReloadLootCustomizationsAndResetSpawners
```

*Original:* Reloads the loot customizations and resets Examine Spawners.

### `RevokeElevatedStatus` 🔒

Revoga status elevado

```
scum sudo RevokeElevatedStatus <SteamID64>
```

- `SteamID64` — Steam ID of player

### `SetFeatureFlag`

Liga ou desliga uma chave de funcionalidade

```
scum SetFeatureFlag <Name> <Value>
```

- `Name` — Feature Flag Name
- `Value` — Feature Flag Value

> Desabilitado no build de produção — não funciona neste servidor.

### `SetShouldPrintExamineSpawnerPresets`

Registra os presets dos geradores ao examiná-los

```
scum SetShouldPrintExamineSpawnerPresets <Value>
```

- `Value`

*Original:* Enables or disables printing of examine spawner presets

### `ShutdownServer`

Desliga o servidor

```
scum ShutdownServer
```

*Original:* Shuts down the server
