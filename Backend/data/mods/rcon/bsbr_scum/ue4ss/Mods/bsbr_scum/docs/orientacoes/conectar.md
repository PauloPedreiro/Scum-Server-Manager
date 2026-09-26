# Conectar no mod

O mod escuta em **`127.0.0.1:27100`**, só na máquina do servidor. Manda-se uma
linha de texto, ele responde com o resultado e fecha a conexão.

A porta é ajustável no `config.ini`; o endereço não:

```ini
[api]
port = 27100
```

Trocar exige reiniciar o servidor, e ajustar a função `scum` abaixo, que tem a
porta escrita nela.

Voltar ao [índice](../README.md).

---

## PowerShell — a função `scum`

Cole no terminal do servidor, ou no seu `$PROFILE` para ficar permanente:

```powershell
function scum {
    param([Parameter(ValueFromRemainingArguments)][string[]]$cmd)

    try {
        $client = [Net.Sockets.TcpClient]::new('127.0.0.1', 27100)
    } catch {
        Write-Error 'servidor fora do ar ou mod nao carregado'
        return
    }

    $stream = $client.GetStream()
    $stream.ReadTimeout = 10000

    $bytes = [Text.Encoding]::UTF8.GetBytes(($cmd -join ' ') + "`n")
    $stream.Write($bytes, 0, $bytes.Length)
    $stream.Flush()

    # O mod fecha a conexao depois de responder, entao ReadToEnd devolve a
    # resposta inteira - inclusive as de varias linhas, como 'vehicles' e 'help'.
    $reader = [IO.StreamReader]::new($stream, [Text.Encoding]::UTF8)
    try { $reader.ReadToEnd().TrimEnd() } catch { Write-Error 'sem resposta em 10s' }

    $reader.Dispose()
    $client.Close()
}
```

Para tornar permanente:

```powershell
notepad $PROFILE
```

Se o arquivo não existir, crie antes:

```powershell
New-Item -ItemType File -Path $PROFILE -Force
```

### Uso

```powershell
scum help
scum players
scum vehicles
scum SpawnItem Weapon_M9
scum as Fulano SpawnVehicle BPC_Rager
scum sudo SpawnBrenner
```

**O prefixo `scum` é obrigatório** — `get`, `set` e `sudo` sozinhos colidem com
comandos internos do PowerShell.

---

## Sem instalar nada

Uma linha só, quando não vale a pena definir a função:

```powershell
$c=[Net.Sockets.TcpClient]::new('127.0.0.1',27100);$s=$c.GetStream();$b=[Text.Encoding]::UTF8.GetBytes("players`n");$s.Write($b,0,$b.Length);$s.Flush();[IO.StreamReader]::new($s).ReadToEnd();$c.Close()
```

## Bash — Git Bash ou WSL

```bash
echo "players" | nc 127.0.0.1 27100
```

---

## Pelo chat do jogo

Não precisa de terminal nenhum. Dentro do jogo, sendo admin:

```
#bsbr players
#bsbr vehicles
#bsbr @Fulano SpawnItem Weapon_M9
#bsbr
```

A resposta volta no chat, uma linha por mensagem. Diferença que importa: **pelo
chat, o alvo padrão é quem digitou**; pelo terminal, que não tem remetente, é o
primeiro jogador vivo.

Comandos do jogo entram pelo chat sem o `bsbr`, do jeito normal: `#ListPlayers`.

---

## Respostas

| Resposta | Significado |
|---|---|
| O resultado do comando | Executou |
| `ok` | Executou, sem nada a relatar |
| `erro: sem resposta em 5s - o tick do jogo pode estar parado` | O mod recebeu, mas a thread do jogo não drenou a fila |
| `servidor fora do ar ou mod nao carregado` | Nem conectou |

O comando não executa na hora em que chega: `ProcessEvent` só pode ser chamado na
thread do jogo, então o socket enfileira e o tick executa. O timeout de 5 segundos
existe porque responder `ok` sem ter executado seria mentira — foi um defeito real
deste mod, com o tick parado por horas e todo comando respondendo `ok`.

---

## Segurança

O socket aceita conexão **apenas de `127.0.0.1`**, e isso não é configurável de
propósito. Não há autenticação: quem alcança a porta executa qualquer um dos 233
comandos, inclusive `sudo DisableServer`, que bloqueia a entrada de todos —
inclusive a sua.

Em loopback isso equivale a já ter a máquina. Aberto na rede, equivaleria a
entregar o servidor a quem varresse a porta.

### Para alcançar de fora

Duas formas, ambas mantendo o socket fechado para o mundo:

**Túnel** — VPN ou SSH. Você conecta como se fosse local.

**Backend na própria máquina** — o serviço roda ao lado do servidor, fala com o
socket em loopback, e a autenticação de verdade fica nele. É o desenho natural
para um painel web.

Pelo chat, o filtro é ser **admin do servidor** — o mesmo nível exigido para
qualquer comando com `#`.
