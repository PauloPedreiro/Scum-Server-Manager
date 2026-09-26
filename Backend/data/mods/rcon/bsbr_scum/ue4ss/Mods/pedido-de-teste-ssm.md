# Pedido de teste — entrega de item por `Location`

**Para:** Paulo e equipe do SSM
**De:** Mazzotti — `bsbr_scum`

---

Olá, Paulo!

Obrigado pela análise que vocês mandaram — foi útil de verdade. Conferi as três
observações técnicas no nosso código e **as três procedem**: a elevação de admin
que não é revogada, a leitura de socket com um `recv` só, e o laço de aceitação
bloqueante. Já estão registradas para correção.

Estamos preparando o `bsbr_scum` para atender o SSM pelo caminho que já funciona
em produção de vocês: o `utils/rcon_client.py`, Source RCON com senha. O mod
passa a abrir uma porta falando esse protocolo, e **é por ela que o SSM
conversa** — sem uma linha de mudança no código de vocês.

## Como vai ficar a configuração

Do nosso lado, no `config.ini` do mod:

```ini
[source]
port = 28015
password = <senha forte, obrigatoria>
```

Do lado de vocês, no `data/config.json`:

```json
"rcon": {
  "enabled": true,
  "provider": "scum_rcon",
  "ip": "127.0.0.1",
  "port": 28015,
  "password": "<a mesma senha>"
}
```

Três observações:

- **`provider` fica em `scum_rcon`.** É o valor que roteia para o
  `utils/rcon_client.py`, que é justamente o cliente que queremos atender. Não é
  engano nosso — o `bsbr_client.py` não entra nessa rota.
- **A porta é livre**, desde que bata dos dois lados. Usamos 28015 por ser o
  padrão que vocês já assumem.
- **Cuidado com o instalador de provedor da interface.** Configurar
  `provider = scum_rcon` e depois mandar instalar faria o `RconModManager`
  copiar o `main.dll` do mod clássico por cima do nosso. Configurar sim,
  instalar não.

Uma última: o `_generate_bsbr_ini()` de vocês reescreve o `config.ini` do nosso
mod contendo apenas a seção `[debug]`. Se isso rodar depois da configuração, a
seção `[source]` some e a porta deixa de subir. Vale um ajuste aí quando chegar a
hora.

---

## O que precisamos saber

Antes de fechar o desenho, tem **um comportamento do jogo** que só dá para
confirmar num servidor com jogadores — e vocês têm isso, nós não.

O SSM entrega item assim:

```
spawnitem <Item> <qtd> Location "<SteamID64>"
```

A pergunta é simples: **o `Location "<SteamID64>"` realmente entrega ao jogador
nomeado, ou o item cai no pé de quem o mod usou como executor?**

Por que importa: se o jogo honra o alvo, o nosso mod só repassa o comando e
pronto. Se não honra, precisamos trocar o executor antes de executar — muda a
implementação, e preferimos descobrir agora.

Pelo que levantamos, a evidência aponta para "o jogo honra". O comando `Teleport`
documenta os argumentos como `X | Y | Z | Player`, ou seja, aceitar o alvo no fim
da linha é padrão da casa. Mas isso é leitura de documentação, não medição.

---

## Como testar

Precisa de **dois jogadores online**, em pontos distantes do mapa.

1. Jogador **A** e jogador **B** conectados, longe um do outro
2. Anote o SteamID64 de **B**
3. Pelo SSM (ou pelo RCON direto), execute:

```
spawnitem Weapon_M9 1 Location "<SteamID64 do B>"
```

4. Verifiquem **onde o item apareceu**

### O que reportar

Só isso:

- ( ) O item caiu no pé do **B** — o alvo nomeado
- ( ) O item caiu no pé de **outro** jogador
- ( ) O item não apareceu para ninguém
- ( ) O comando devolveu erro — qual?

Se caiu em outro jogador, ajuda muito saber **quem** era: provavelmente é o
jogador que o mod escolheu como executor.

### Um segundo teste, se der

Mesmo comando com **zero jogadores online**. Isso nos diz se o mod antigo usa o
controller sintético nessa rota, ou se o comando simplesmente falha.

---

## Um defeito que encontramos no parser de vocês

Aproveitando: achamos um bug em `utils/rcon_client.py` que afeta a loja,
independente de qual mod esteja rodando.

Em `parse_listplayers_response`, o saldo é lido por:

```python
m_bal = re.search(r"Account balance:\s*(\d+)", block)
```

O `(\d+)` não aceita sinal negativo. E o jogo **imprime negativo** — saída real
do nosso servidor:

```
Account balance: -1000
```

O casamento falha e o campo fica no default `0`. Ou seja, **todo jogador
endividado aparece com saldo zero** para o SSM. O mesmo vale para `Fame:` e
`Gold balance:`, caso possam ficar negativos.

Sugestão de correção:

```python
m_bal = re.search(r"Account balance:\s*(-?\d+)", block)
```

---

Qualquer coisa que precisarem do nosso lado para rodar o teste, é só falar.

Abraço,
Mazzotti
