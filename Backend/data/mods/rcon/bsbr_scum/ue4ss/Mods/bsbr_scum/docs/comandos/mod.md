# Comandos do mod

Estes **não são do SCUM**. São do `bsbr_scum`, e funcionam por reflexão da Unreal:
leem e escrevem propriedades dos objetos vivos do servidor, sem passar pelo
interpretador de comandos do jogo.

Voltar ao [índice](../README.md).

---

## As duas formas de chamar

Todo comando funciona igual pelos dois caminhos. A única diferença é o prefixo.

| | Terminal do servidor | Chat do jogo |
|---|---|---|
| Prefixo | `scum ` | `#bsbr ` |
| Exemplo | `scum vehicles` | `#bsbr vehicles` |
| Resposta | Saída do terminal | Mensagens no chat |
| Quem é o alvo padrão | Primeiro jogador vivo | **Quem digitou** |

O `scum` é a função do PowerShell descrita em [conectar.md](../orientacoes/conectar.md).
O `#` é o marcador de chat do SCUM; `bsbr` é o nosso.

**Não são sensíveis a maiúsculas.** `#BSBR VEHICLES` e `#bsbr vehicles` são a
mesma coisa. Vale para o marcador e para o nome do comando — o resto da linha
(nome de jogador, caminho de propriedade, classe) mantém a grafia.

### Abreviação

Basta digitar o suficiente para não ser ambíguo:

```
#bsbr veh          → vehicles
#bsbr pl           → players
#bsbr s            → 's' e ambiguo: say, search, set, spawn, sudo
```

A abreviação só vale para comandos do mod. Verbos do jogo passam intactos.

---

## Resumo

| Comando | O que faz |
|---|---|
| `help [comando]` | A lista, ou o detalhe de um comando |
| `players` | Jogadores conectados, com ID e SteamID |
| `vehicles` | Veículos com o ID que a interface mostra |
| `get <alvo> [caminho]` | Despeja as propriedades do alvo num arquivo |
| `set <alvo> <caminho> <valor>` | Escreve uma propriedade |
| `call <alvo> <função>` | Chama uma função sem parâmetros |
| `spawn <classe> <x> <y> <z>` | Cria um ator direto pela engine |
| `sudo <comando>` | Executa um comando de nível Developer |
| `find <texto>` | Procura classes e objetos carregados |
| `search <alvo> <valor>` | Procura uma propriedade com esse valor |
| `inspect <classe>` | Reflexão completa de uma classe |
| `say <texto>` | Anuncia no chat |
| `commands` | Gera o catálogo dos comandos do jogo |
| `capture on\|off` | Liga a captura da saída dos comandos |

E um prefixo, que não é comando:

| Prefixo | O que faz |
|---|---|
| `as <jogador> <comando>` | Executa o comando **como** aquele jogador (no chat: `@<jogador>`) |

---

## `@` e `as` — mirar em outro jogador

```powershell
scum as Fulano SpawnItem Weapon_M9
```
```
#bsbr @Fulano SpawnItem Weapon_M9
```

**São a mesma coisa, e as duas existem por necessidade.** No PowerShell, `@` no
início de um argumento é *splatting* e some antes da função receber — e `-` seria
lido como nome de parâmetro. Por isso o terminal usa `as`. No chat, onde nada
disso acontece, o `@` é o natural.

O `@` também funciona no terminal, desde que entre aspas: `scum '@Fulano' ...`.

Comandos de admin rodam **no contexto de quem os envia**. É isso que define onde
o item cai, onde o veículo nasce, de quem é a posição consultada. Trocar o
executor redireciona os 233 comandos de uma vez, sem precisar de argumento de
posição em cada um.

Aceita três identificadores, todos **exatos** — sem abreviar:

| Forma | Terminal | Chat |
|---|---|---|
| ID do perfil | `as 1` | `@1` |
| SteamID | `as 76561190000000000` | `@76561190000000000` |
| Nome completo | `as Fulano` | `@Fulano` |

Use `players` para vê-los. Só a caixa é ignorada: `as fulano` funciona.

> Casamento por trecho seria perigoso: `1` acertaria o jogador `17`, e `Ma`
> acertaria dois jogadores diferentes — em silêncio, e o erro só apareceria pela
> reclamação de quem levou.

**Sem `@`**, o alvo é quem digitou (no chat) ou o primeiro jogador vivo (no
terminal, que não tem remetente).

Combina com tudo:

```
#bsbr @Fulano sudo SpawnBrenner
#bsbr @Fulano Teleport 559735 -215880 1172
#bsbr @Fulano get player
```

---

## `help`

```powershell
scum help
scum help set
```
```
#bsbr
#bsbr help set
```

No chat, `#bsbr` sozinho já mostra a lista — não precisa escrever `help`.

O detalhe de `get`, `set`, `call` e `search` inclui os alvos aceitos; o de `set`
inclui a sintaxe do caminho; o de `sudo`, o aviso dos comandos destrutivos.

---

## `players`

```powershell
scum players
```

```
1 jogador(es):
    1 | Fulano             | 76561190000000000
alvo: '@<id|steamid|nome> <comando>' - nome completo, sem abreviar
```

As três colunas são ID do perfil, nome e SteamID — os mesmos que o SCUM registra
no log como `'76561190000000000:Fulano(1)'`. Todos servem de alvo para o `@`.

---

## `vehicles`

```powershell
scum vehicles
```

```
2 veiculo(s):
    590005 |        2 m | BPC_Rager_C_2147337983  <- voce esta neste
    140073 |      374 m | BPC_Tractor_C_2147338019
```

Ordenado por distância. A primeira coluna é o **ID que a interface do jogo
mostra** — use ele em `get` e `set`.

A marcação `<- voce esta neste` sai da cadeia de montaria, que é determinística:
o slot onde você senta mora dentro do veículo, então subir pelo `Outer` chega
nele em um salto.

> Veículos aquáticos aparecem com ID `0`. O identificador deles não fica no mesmo
> lugar; ainda não mapeado.

---

## Alvos

`get`, `set`, `call` e `search` recebem um **alvo**. Cinco formas:

| Alvo | Resolve para |
|---|---|
| `player` | Seu prisioneiro (ou o do `@`, se houver) |
| `player <nome>` | O prisioneiro daquele jogador |
| `vehicle` | O veículo em que você está; se não estiver em nenhum, o mais próximo |
| `vehicle <id>` | O veículo com esse ID da interface |
| `vehicle <nome>` | Por trecho do nome da instância — `BPC_Rager_C_2147329237` |
| `class <caminho>` | O **molde** da classe: o que escrever vale para instâncias criadas **depois** |
| `object <nome ou caminho>` | Qualquer objeto carregado — aceita nome parcial |

Para `vehicle`, o alvo real é o componente de movimento (`GetMovementComponent`),
não o ator — é lá que moram motor, câmbio e massa.

> **`vehicle` sem filtro já acertou um trator e um avião** antes da cadeia de
> montaria funcionar. Na dúvida, confirme com `vehicles` e mire pelo ID.

---

## `get` — ler o estado

```powershell
scum get vehicle 590005
scum get player Fulano
scum get class /Game/ConZ_Files/Vehicles/Rager/BPC_Rager.BPC_Rager_C
scum get object /Game/ConZ_Files/Skills/DrivingSkill.DrivingSkill
scum get object BP_Rager_MountSlot_Seat_FrontLeft_C_2147337373
```

Grava em `bsbr_scum_target.txt`, na pasta `Win64` do servidor. Uma linha por
propriedade, com tipo, caminho e valor:

```
float    EngineData.MaxRPM                    7000
struct   GearboxData
array    GearboxData.ForwardGears             [8]
float    GearboxData.ForwardGears[0].Ratio    4.7
byte     Role                                 3
enum     _repMount._mountFlags                3
name     SlotId.TagName                       MountSlot.Rager.SeatFrontLeft
string   _userId                              76561190000000000
object   _repMount.MountedSlot                BP_Rager_MountSlot_Seat_FrontLeft_C_2147337373
object   _networkPrediction                   <nulo>
```

Tipos lidos com valor: `float`, `int`, `int64`, `uint64`, `bool`, `byte`, `enum`,
`name`, `string` e `object` (mostra o **nome do objeto apontado**). Desce até 3
níveis em struct e abre array de struct. Os demais aparecem com `-` — o nome está
lá, o valor não.

**Enums saem como número.** `Role` e `RemoteRole` seguem `ENetRole`: `0` nenhum,
`1` proxy simulado, `2` proxy autônomo, `3` autoridade.

**Referências mostram o nome, não descem.** Descer viraria recursão sem fim. Para
abrir o objeto apontado, use o nome dele em `get object` — aceita nome parcial.

---

## `set` — escrever

```powershell
scum set vehicle 590005 EngineData.MaxRPM 9000
scum set vehicle 590005 GearboxData.FinalRatio 2.5
scum set vehicle 590005 GearboxData.ForwardGears[7].Ratio 0.4
scum set class /Game/ConZ_Files/Vehicles/Rager/BPC_Rager.BPC_Rager_C _driveComponent.ChassisMass 300
```

O caminho aceita **ponto** para entrar em struct e **colchete** para indexar
array. Também atravessa referência de objeto — é assim que se chega no
`_driveComponent` a partir do molde do ator.

Aceita **float, int e bool**. Tipos compostos ficam de fora de propósito:
escrever tamanho errado num ponteiro é corrupção de memória, não erro tratável.

O alvo pode ter duas palavras (`vehicle 590005`), então caminho e valor são lidos
**do fim para o começo** — analisar do começo fazia o ID virar nome de
propriedade.

### O que `set` não consegue mudar

**Física de veículo.** Massa, marchas, motor, velocidade — nada disso responde.
Três vias testadas, três fechadas:

| Via | Resultado |
|---|---|
| Escrever na instância viva | O PhysX monta o veículo no spawn e nunca mais relê |
| Escrever no `class` e spawnar | A escrita **propaga** (verificado), mas o cliente simula com os valores dele |
| Console da Unreal via `Exec` | *"Command is disabled in shipping build."* |

Confirmado no ator: `bReplicateMovement = 0` — o servidor não replica o movimento
do veículo. Quem simula é o cliente do motorista. Mudar isso exigiria mod em cada
máquina.

Vale **só para física**. O resto do estado do veículo — combustível, bateria,
vida, tranca — é autoritativo no servidor e responde normalmente.

---

## `call` — chamar função

```powershell
scum call vehicle 590005 StartEngine
```

Só funções **sem parâmetros**. O retorno sai no log interpretado como float e
como int, já que o tipo não é conhecido de antemão.

Funções nativas de `AActor` como `GetOwner` **não são encontradas** — não são
UFunction refletida. Para essas, leia a propriedade equivalente com `get`; e
quando o objeto não é `Actor`, a posse está no `Outer`, não em `Owner`.

---

## `find`, `search` e `inspect` — descobrir

```powershell
scum find Rager
scum search vehicle 2450
scum inspect /Script/SCUM.VehicleBase
```

`find` lista classes e objetos carregados cujo nome contém o texto.
`search` procura uma propriedade com determinado valor dentro de um alvo.
`inspect` despeja a reflexão completa de uma classe: propriedades, funções, herança.

> Só enxergam o que está **carregado em memória**. Classe de asset nunca usado não
> aparece. Carregar sob demanda foi tentado e derrubava o servidor
> (`Package_LoadSummary has zero prerequisites`), então foi removido.

Estes três varrem todos os objetos do servidor — é o trabalho deles. São
ferramentas de investigação, não de automação; ver a seção de desempenho.

---

## `spawn` — criar ator pela engine

```powershell
scum spawn /Game/ConZ_Files/Vehicles/Rager/BPC_Rager.BPC_Rager_C 0 0 5000
```

Vai direto no `BeginDeferredActorSpawnFromClass`, sem passar pelo comando
`SpawnVehicle` do jogo — logo, **sem verificação de permissão**. Só aceita classes
já carregadas.

Útil junto com `set class`: configure o molde, depois spawne.

Para spawnar perto de um jogador, prefira o comando do jogo com `@`, que já nasce
na posição dele:

```
#bsbr @Fulano SpawnVehicle BPC_Rager
```

---

## `sudo` — destravar nível Developer

```powershell
scum sudo SpawnBrenner
scum as Fulano sudo SpawnBrenner
```

O nível exigido é propriedade **do comando**, não do jogador. O mod rebaixa
`_requiredExecutorLevel` no molde da classe, executa e restaura no mesmo tick.

Destrava os 105 comandos de nível 3 e 4 — ver [developer.md](developer.md).

> **Cuidado.** Entre os destravados estão `CrashMajestically`, `CrashClient` e
> `DisableServer`. Um erro de digitação derruba o servidor, e o `DisableServer`
> bloqueia até a sua própria reconexão.

---

## `say` — anunciar

```powershell
scum say Servidor reiniciando em 5 minutos
```

Usa `MiscStatics::BroadcastChatLine`. É também por onde as respostas do mod
chegam ao chat.

---

## `commands` — catálogo do jogo

```powershell
scum commands
```

Gera a reflexão dos comandos de admin do SCUM em `bsbr_scum_comandos.txt`. A
versão organizada e traduzida está nos outros arquivos desta pasta.

---

## `capture` — ler a saída dos comandos

```powershell
scum capture on
```

Os comandos do jogo respondem no chat do cliente, não no log do servidor. Para
ler essa resposta é preciso observar `Chat_Client_SendMessageToChat`.

**Custa caro e não deve ficar ligado.** Exige `HookUObjectProcessEvent = 1` no
`UE4SS-settings.ini`, que desvia **toda** chamada de função do jogo — e esse hook
já derrubou o servidor na entrada de jogador. Nasce desligado.

Prefira ler o estado por reflexão com `get`, que não depende de hook nenhum.

---

## Desempenho

Buscas por jogador e veículo passam pela **lista de atores do mundo** (milhares
de objetos), não pelo array global de UObjects (centenas de milhares). O mundo, o
índice de verbos e as classes são resolvidos uma vez e guardados.

Isso vale também para os 273 comandos do jogo, que precisam localizar um
controller antes de injetar.

| Comando | Custo |
|---|---|
| Comandos do jogo, `sudo`, `players`, `vehicles`, `get`, `set`, `call` | Lista de atores — barato, pode ir para automação |
| `find`, `search`, `inspect`, `object <nome parcial>` | Varredura completa — um engasgo de frame por chamada |

A varredura roda na thread do jogo, então o frame para enquanto ela acontece.
Imperceptível de vez em quando; perceptível num laço a cada segundo com jogadores
online.

---

## Ruído no chat

Quando um comando `#bsbr` é reconhecido, o mod apaga o texto antes do jogo
processá-lo — senão o SCUM responderia *"unrecognized command"*, já que `bsbr`
não existe no catálogo dele.

O apagamento escreve o terminador no lugar, sem liberar memória: a string vive no
frame do jogo, e devolver ao allocator dele, dentro da chamada dele, quebraria
longe do ponto de origem.
