# bsbr_scum — documentação

Tudo que dá para executar neste servidor: os **233 comandos de administração do
SCUM** e os **14 comandos do mod**.

Se é a primeira vez: [orientacoes/conectar.md](orientacoes/conectar.md) ensina a
mandar o primeiro comando.

---

## Comandos do mod

| Arquivo | Conteúdo |
|---|---|
| [comandos/mod.md](comandos/mod.md) | `get`, `set`, `call`, `sudo`, `@jogador`, `vehicles`, `players` |

Leem e escrevem propriedades dos objetos vivos por reflexão da Unreal, sem passar
pelo interpretador do jogo. Pelo chat exigem o prefixo `bsbr`.

## Comandos do SCUM

233 comandos, por assunto. Cada entrada traz a linha de chamada pronta e o
significado de cada argumento, lidos do próprio jogo:

| Arquivo | Qtd | Conteúdo |
|---|---|---|
| [comandos/jogadores.md](comandos/jogadores.md) | 47 | Listar, expulsar, banir, silenciar, teleportar |
| [comandos/spawn.md](comandos/spawn.md) | 29 | Itens, veículos, zumbis, animais, NPCs |
| [comandos/mundo.md](comandos/mundo.md) | 28 | Clima, tempo, eventos, encontros |
| [comandos/economia.md](comandos/economia.md) | 14 | Moeda, fama, comerciantes |
| [comandos/destruir.md](comandos/destruir.md) | 16 | Veículos, itens, construções, cadáveres |
| [comandos/servidor.md](comandos/servidor.md) | 22 | Informação e manutenção |
| [comandos/developer.md](comandos/developer.md) | 77 | Ferramentas internas — todos 🔒 |

## Identificadores

O que passar como argumento de `SpawnItem`, `SpawnVehicle` e afins:

| Arquivo | Qtd |
|---|---|
| [comandos/itens.md](comandos/itens.md) | 1134 itens |
| [comandos/veiculos.md](comandos/veiculos.md) | 17 veículos |
| [comandos/zumbis.md](comandos/zumbis.md) | 25 tipos de zumbi |

## Orientações

| Arquivo | Conteúdo |
|---|---|
| [orientacoes/conectar.md](orientacoes/conectar.md) | A função `scum` do PowerShell, o chat, e o que cada resposta significa |
| [orientacoes/comandos-do-scum.md](orientacoes/comandos-do-scum.md) | Níveis de permissão e como destravar os de nível Developer |

---

## Referência rápida

```powershell
scum ListPlayers                       # comando do jogo, pelo terminal
scum sudo SpawnBrenner                 # comando de nível Developer
scum as Fulano SpawnItem Weapon_M9   # executando no lugar de outro jogador
```

```
#ListPlayers                           # comando do jogo, pelo chat
#bsbr vehicles                         # comando do mod, pelo chat
#bsbr @Fulano SpawnItem Weapon_M9    # no lugar de outro jogador
#bsbr                                  # a lista dos comandos do mod
```

O `#` é o marcador do SCUM; o `bsbr` é o do mod. Comandos do jogo **não** levam
`bsbr`.

No terminal use `as`, não `@`: o PowerShell consome o `@` como splatting antes da
função receber o argumento. No chat, o `@` é o natural.

---

## Como ler cada entrada dos comandos

```
### `BaseBuildingDebug` 🔒          ← 🔒 exige nível Developer

Depuração de construção             ← resumo, em português

​```
scum sudo BaseBuildingDebug <Mode>  ← linha pronta, com o sudo já incluso
​```

- `Mode` — 0 = Disabled ; 1 = Basic ; 2 = RadialDamage ; ...   ← cada argumento

*Original:* Sets debug mode for base building.    ← texto da Gamepires
```

O resumo é nosso. A explicação dos argumentos e a linha *Original* são o texto da
própria Gamepires, lido do jogo — não traduzimos para não introduzir erro no que
é a referência.
