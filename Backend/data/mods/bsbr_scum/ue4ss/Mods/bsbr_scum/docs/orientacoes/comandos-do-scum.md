# bsbr_scum — documentação

Tudo que dá para executar neste servidor, por categoria: os **273 comandos de
administração do SCUM** e os **14 comandos do mod**.

O catálogo do SCUM foi extraído por reflexão do servidor em execução — verbo,
descrição, número de argumentos e nível de permissão vêm do próprio jogo, não de
fontes externas.

Dado bruto, no repositório do projeto: `docs/referencia/comandos.tsv` (273 registros).

> As descrições em inglês são as originais da Gamepires, lidas da propriedade
> `_description` de cada comando. As traduções em português são nossas e podem
> divergir de mudanças futuras do jogo.

---

## Como executar

**Sem o prefixo `#`.** O `#` é o marcador de chat e é consumido antes do
interpretador chegar no comando. `#Location` devolve *"unrecognized command"*;
`Location` funciona.

```powershell
scum ListPlayers
scum SpawnItem Weapon_M9
```

Pelo chat do jogo, o `#` continua sendo o marcador normal do SCUM:

```
#ListPlayers
```

Ver [conectar.md](conectar.md) para a função `scum` do PowerShell.

### Dois conjuntos de comandos

São **233 comandos do SCUM**, lidos do próprio jogo. O mod acrescenta os seus,
documentados em [comandos/mod.md](../comandos/mod.md) — esses não passam pelo
interpretador do jogo, leem e escrevem propriedades por reflexão.

Ambos entram pela mesma linha; o mod atende o que reconhece e repassa o resto ao
jogo. Pelo chat, os do mod exigem o prefixo `bsbr` (`#bsbr vehicles`) e os do
jogo não (`#ListPlayers`).

O prefixo **`@<jogador>`** funciona com os dois: `#bsbr @Fulano SpawnItem
Weapon_M9` faz o item cair no Fulano, e não em quem digitou.

---

## Níveis de permissão

Cada comando declara o nível mínimo do executor:

| Nível | Qtd | Situação |
|---|---|---|
| 0 | 10 | Sem restrição |
| 1 | 116 | Admin — funcionam normalmente |
| 2 | 2 | Um degrau acima do admin |
| 3 | 26 | Developer — recusado com *"Player must be developer"* |
| 4 | 79 | Developer |

Somam 233. O dump bruto traz 273 registros: os 40 a mais são classes de
autocompletar de argumento (`AdminCommandArgumentCompletion_*`), não comandos.
Elas guardam os **valores válidos** de cada argumento — dado ainda não aproveitado
pelo mod.

### Executando comandos de nível Developer

O nível exigido é propriedade **do comando**, não do jogador. O mod rebaixa esse
requisito, executa e restaura no mesmo tick:

```powershell
scum sudo SpawnBrenner
```

Comandos de nível 3 e 4 estão marcados com **🔒** nas tabelas.

> **Cuidado.** Entre os comandos destravados estão `CrashMajestically`,
> `CrashClient` e `DisableServer`. Um erro de digitação derruba o servidor.

---

## Onde estão as listas

Todas em [comandos/](../comandos/) — comandos por assunto, os do mod e os
identificadores de item, veículo e zumbi.

---

## Nomes de item e veículo

Os argumentos de `SpawnItem` e `SpawnVehicle` são identificadores internos, não
nomes de exibição. O jogo exporta a lista completa:

```powershell
scum ExportDefaultItemSpawningParameters
```

Grava 1134 itens em
`Saved/Config/WindowsServer/Loot/Items/Default/Parameters.json`, cada um com o
campo `Id` — o valor aceito pelo `SpawnItem`.

Exemplos: `Weapon_M9`, `Weapon_M9_Silver`, `Magazine_M9`, `Water_05l`.
Para veículos: `BPC_Rager`, `BPC_Laika`.

Também há `ListItems`, `ListVehicles`, `ListZombies` e `ListAnimals`, que
imprimem as listas filtradas no chat.
