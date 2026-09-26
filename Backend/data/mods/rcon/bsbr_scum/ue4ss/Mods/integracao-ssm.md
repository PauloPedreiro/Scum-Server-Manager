# Integração com o SSM — especificação

**Data:** 2026-08-26
**Estado:** especificação, nada implementado
**Alvo:** fazer o `bsbr_scum` atender o SSM (Scum Server Manager) pelo caminho
que já funciona em produção deles — o cliente Source RCON — sem alterar o
comportamento atual da API de linha nem perder desempenho.

---

## 1. Por que existe

O SSM tem dois clientes:

| Cliente | Protocolo | Porta padrão | Estado |
| --- | --- | --- | --- |
| `utils/bsbr_client.py` | linha de texto, uma conexão por comando | 27100 | escrito para o nosso mod, **não funciona** |
| `utils/rcon_client.py` | Source RCON | 28015 | **em produção** contra o mod antigo |

A escolha é uma chave de configuração no `data/config.json` deles:

```json
"rcon": { "provider": "scum_rcon", "ip": "127.0.0.1", "port": 28015, "password": "..." }
```

Qualquer `provider` diferente de `bsbr_scum` cai no cliente Source RCON. Logo,
atender o SSM significa **ser indistinguível do mod antigo no fio e no texto de
saída**. Não é aproximação: o cliente deles parseia por expressão regular.

Uma aplicação web não tem SteamID e não é admin do servidor. A senha da porta
Source é o que substitui essa checagem — e vale **apenas** naquela porta.

---

## 2. Arquitetura

Dois ouvintes, um despachante:

```
27101  linha de texto, sem senha, fecha por comando   →┐
                                                        ├→ despachante → fila do tick
nova   Source RCON, senha, conexão persistente        →┘
```

A porta decide **transporte** (enquadramento e autenticação). O que o comando faz
e o texto que devolve são camada compartilhada — quem perguntar recebe o mesmo.

A porta 27101 não muda de comportamento. É contrato com o PowerShell do
administrador e com qualquer cliente existente.

### Nomenclatura

A restrição do `CLAUDE.md` §0 vale aqui: **nenhum identificador `rcon` /
`RCON` / `scum_rcon` dentro de `bsbr_scum/`** — inclui seção de config e marca de
log. A porta nova usa:

```ini
[source]
port = 28015
password = ...
```

Marca de log `[bsbr_scum][source]`. O protocolo continua sendo Source RCON; o que
não pode é o nome virar identificador nosso.

---

## 3. Contrato do transporte Source

Levantado lendo `utils/rcon_client.py` do SSM. Cada linha abaixo é exigência do
cliente, não preferência nossa.

| Item | Exigência |
| --- | --- |
| Enquadramento | `int32 size`, `int32 id`, `int32 type` (little-endian), corpo, `0x00 0x00`. O `size` não conta a si mesmo |
| Autenticação | Cliente manda type **3**, `id = 999`, corpo = senha. Resposta type **2**: eco do `999` = aceito, `-1` = recusado |
| Pacote vazio inicial | O cliente lê até 3 pacotes ignorando os que não são type 2 — mandar o type 0 vazio do Source clássico é tolerado, não obrigatório |
| Senha | Obrigatória. `if not password: return None` no lado deles — sem senha configurada, nem conectam |
| Conexão | **Persistente.** O `RconQueueManager` guarda um cliente e só reconecta se o socket morreu |
| Resposta | **Exatamente um pacote por comando** |
| Tamanho | O campo é `int32`. O teto de 4096 é convenção; resposta grande vai num pacote grande |
| Prazo | 5 s. Estourar não gera erro no lado deles: `socket.timeout` vira string vazia |
| Request id | Incrementa 2→65535 e volta a 2. O cliente **ignora** o id da resposta, mas ecoar é o correto |

### Os dois pontos que mordem

**Um pacote por resposta.** O `send_command` deles faz **um** `_read_packet()` e
retorna. Pacote extra fica no buffer do socket, e o próximo comando lê a sobra do
anterior. Como a conexão é persistente, nunca se corrige: da segunda resposta em
diante tudo sai deslocado, sem erro e sem log. **Não pode haver chunking nessa
porta.**

**Resposta em menos de 5 s.** Passar do prazo devolve `""` ao SSM sem sinal de
erro. Num `ListPlayers` isso vira "nenhum jogador online", e a entrega da loja
falha calada.

---

## 4. `ListPlayers` — a saída que o SSM lê

É a **única** saída que o SSM interpreta. Confirmado varrendo o backend: três
consumidores (`discord_bot_service`, `player_gps_sync_service`,
`delivery_service`), todos via `parse_listplayers_response`. As respostas de
`spawnitem`, `spawnvehicle`, `SendChat`, `Announce` e `Teleport` só vão para log
de depuração — ninguém decide nada com elas.

### Formato

Saída real do servidor, capturada em 2026-08-26 (identificadores trocados):

```
 1. Fulano
Steam: Fulano (76561190000000000)
Fame: 3308
Account balance: -1000
Gold balance: 0
Location: X=66157.000 Y=-421599.000 Z=10931.340
```

Detalhes que o parser deles exige:

- Blocos separados por `\n(?=\s*\d+\.\s+\S)` — a linha de índice abre o bloco
- `^\s*(\d+)\.\s+(.+)` — espaço à esquerda é tolerado
- `Steam:\s+.*\((\d{17})\)` — **exatamente 17 dígitos**; bloco sem isso é descartado
- `Fame:\s*(\d+)`, `Account balance:\s*(\d+)`, `Gold balance:\s*(\d+)`
- `Location:\s*X=([\-\d.]+)\s+Y=([\-\d.]+)\s+Z=([\-\d.]+)` — três casas decimais

### De onde sai cada campo

Tudo por leitura de propriedade. **Nenhum hook, nenhum `ProcessEvent`, nenhum
detour.** Medido no servidor em 2026-08-26.

| Campo | Origem | Tipo |
| --- | --- | --- |
| índice | contador da iteração | — |
| nome | `_userProfileName` no prisioneiro | string |
| SteamID | `identity_of()`, já implementado | string |
| `Fame` | `_repFamePoints` no **controller** | int |
| `Account balance` | `_moneyBalanceRep` no controller | int64 |
| `Gold balance` | `_goldBalanceRep` no controller | int64 |
| `Location` | `RelativeLocation` X/Y/Z do componente raiz | float ×3 |

Observações do levantamento:

- Fama, saldo e ouro moram no **controller**, não no pawn — por isso um
  `get player` nunca os mostrou.
- O componente raiz do prisioneiro é o `CollisionCylinder`, e ele tem
  `bAbsoluteLocation = 1`: a `RelativeLocation` **é** posição de mundo. Os campos
  `BasedMovement.Location` e `RepRootMotion.Location` do pawn são rascunho de
  replicação e valem zero — não usar.
- `Fame` são **pontos**, não nível. O jogo imprimiu `3308`; `_repFamePoints` lia
  `3307` sete minutos antes, e `GetFameLevel()` devolve `33`. A fama acumula, é a
  mesma grandeza. Preferir a propriedade à função — evita `ProcessEvent`.

Isso sai mais barato que o `ListPlayers` do próprio jogo, que monta o texto e o
envia pelo canal de chat.

### Defeito conhecido no lado deles

O regex de saldo é `(\d+)`, sem sinal. O jogo imprime `Account balance: -1000`
para quem está no vermelho, o casamento falha e o campo cai no default **0**.
Não é nosso para corrigir, mas afeta a loja do SSM e deve ser comunicado.

---

## 5. Comandos a implementar

### `SendChat <tipo 0-7> "<mensagem>" <steamid>`

**Não existe no jogo.** Não está entre os 233 comandos catalogados — é invenção
do mod antigo (a string `usage: SendChat <type 0-7>` está no binário dele).

É o comando mais usado do SSM: cerca de 43 chamadas no backend. Tipo 6 para
sucesso, 7 para erro.

Matéria-prima já existe no nosso mod: o `whisper()` chama

```
/Script/SCUM.MiscStatics:SendChatLineToPlayer(PlayerController, Text, ChatType, bShouldCopyToClipboard)
```

e o `<tipo 0-7>` é exatamente esse `ChatType`. Falta resolver o destinatário por
SteamID em vez de controller — o `identity_of()` já faz a tradução.

### `SendNotification <tipo> <n> "<mensagem>" <steamid>`

O jogo **tem** um `SendNotification`, mas com outra assinatura:

```
SendNotification  nível 4 (Developer)
  Notification: Notification type to send | User ID: Whom to send | Message
  "Type: {1, 2, .. 5} If User_id is -1, message is sent to all."
```

A forma de quatro tokens que o SSM manda (`SendNotification 4 0 "<msg>" <id>`) é
do mod antigo. Duas saídas: reimplementar por reflexão, ou traduzir para o
comando do jogo — que exige `sudo`, já que é nível 4.

Formas observadas no SSM: `SendNotification 4 0 ...` e `SendNotification 1 0 ...`.

---

## 6. Defeitos a corrigir — nas duas portas

Os cinco valem para todo o mod, não só para a porta nova.

### 6.1. Elevação de admin nunca revogada

`Client_SetIsAdmin` aparece **uma vez** em `dllmain.cpp` (~linha 1711): só a
concessão. Quando nenhum admin está online, o `execute()` promove um jogador
comum para servir de ponte RPC e **nunca devolve** — ele fica admin até deslogar.

Correção: guarda RAII que restaura o estado na saída do escopo, inclusive por
exceção ou retorno antecipado.

Cuidado: o `is_admin()` hoje lê o `AdminUsers.ini`, então checagem e concessão
usam fontes diferentes. O guarda precisa pendurar no resultado real de
`IsUserAdmin`, não na lista em cache.

Como o `execute()` é único, a correção cobre chat, API e porta nova de uma vez.

### 6.2. Leitura de socket confia num `recv` só

```cpp
char buffer[1024]{};
const int received = recv(client, buffer, sizeof(buffer) - 1, 0);
```

Trunca comando acima de 1023 bytes, e — pior — TCP é fluxo: um `recv` pode
devolver comando parcial mesmo curto, e executaríamos metade.

Correção, com mecânica diferente por porta (isso **não** dá para unificar):

- **API**: ler em laço até encontrar `\n`
- **Source**: ler exatamente N bytes conforme o cabeçalho

Aplicar a regra da API na porta Source travaria esperando um `\n` que nunca vem.

### 6.3. Laço de aceitação é thread única e serial

Hoje:

```
accept() → recv() → enfileira → wait_for(5s) → send() → close() → volta ao accept()
```

Enquanto um comando espera o tick, o processo **não está em `accept()`**. Duas
consequências:

- Na 27101, um comando lento bloqueia novas conexões por até 5 s
- Na porta Source seria fatal: o SSM abre uma conexão e **nunca fecha**; ela
  moraria nesse laço e mataria a 27101 junto

Correção: cada ouvinte com sua thread de aceitação, e thread por conexão.

### 6.4. O prefixo `#` não é descascado

Verificado: `#players` pela API devolveu `ok` — caiu no caminho de comando do
jogo em vez do nosso. O SSM manda `#teleport <x> <y> <z> <steamid>`.

Correção: descascar `#` inicial nas duas portas. Inofensivo na API, necessário na
Source.

### 6.5. `call` não decodifica retorno de struct

```
BP_Prisoner_C_2147330243.K2_GetActorLocation() -> StructProperty
```

Contornável para posição (lemos `RelativeLocation` como propriedade), mas é
limitação real do comando.

---

## 7. Fora de escopo

- **Controller sintético** para servidor vazio. A receita do mod antigo está
  mapeada (spawn diferido de `BP_ConZPlayerController_C`, escrever um
  `/Script/SCUM.UserProfile` em `_userProfile`, spawnar `ConZCharacter`,
  `Possess(InPawn)`, `Client_SetIsAdmin`), mas custa dois atores vivos e traz
  risco de aparecer em `ListPlayers` e no banco. Entrega de item a quem acabou de
  entrar sempre tem jogador online.
- **Saída JSON.** Boa ideia, não destrava nada: na rota Source o SSM exige o
  texto exato e o lê por regex.
- **Conexão persistente na 27101.** Já foi tentada e quebrou: tanto o
  `bsbr_client.py` do SSM quanto o cliente Go do painel dependem de a gente
  fechar para saber que a resposta terminou.
- **`HookUObjectProcessEvent`.** Fica em `0`. Toda a saída necessária sai de
  leitura de propriedade.
- **Modularização do `dllmain.cpp`** e **CI/CD**. Ambos legítimos, nenhum é
  pré-requisito. O CI/CD ainda esbarra no submódulo `UEPseudo`, privado da
  organização `@EpicGames` — runner público não compila.

---

## 8. Em aberto

- `spawnitem <item> <qtd> Location "<steamid>"` com **um segundo jogador**. A
  evidência indireta é forte: o `Teleport` documenta `X | Y | Z | Player`, ou
  seja, o jogo aceita alvo no fim do comando. Se falhar, a correção é no formato
  enviado, não na arquitetura.
- Os dois números de `SendNotification <a> <b>` no dialeto do mod antigo.

---

## 9. Evidência

Levantado em 2026-08-26 contra o servidor em execução, pela porta 27101:

- `players`, `get player`, `get object <controller>`, `get object <raiz>`
- `call object <controller> GetFameLevel` → `33`
- `call object <controller> GetFamePointsRounded` → `3307`
- `call player K2_GetActorLocation` → `StructProperty` (não decodificado)
- `find Fame`, `find SendNotification`, `find BP_ConZPlayerController_C`
- `#ListPlayers` digitado no chat do jogo, para a saída real do comando

E lendo o código do SSM (`utils/rcon_client.py`, `utils/bsbr_client.py`,
`core/rcon_queue_manager.py`, `core/shop/delivery_service.py`,
`utils/rcon_mod_manager.py`) e o decompilado do mod antigo.
