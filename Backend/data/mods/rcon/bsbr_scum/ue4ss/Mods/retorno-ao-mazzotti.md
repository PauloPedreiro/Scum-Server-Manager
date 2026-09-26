# Retorno dos Testes de Comunicação e Integração — SSM ↔ BSBR-SCUM

**Para:** Mazzotti — `bsbr_scum`  
**De:** Paulo e Equipe SSM  
**Data:** 26 de agosto de 2026  
**Status:** Testes de conectividade, comandos e entrega executados com sucesso  

---

Olá, Mazzotti!

Recebemos os novos arquivos e a especificação da integração. Subimos a nova versão da DLL e executamos a primeira bateria de testes práticos direto com o servidor do SCUM online. 

Aqui estão os resultados detalhados e as respostas aos seus pontos:

---

## 1. Testes de Conectividade e Comandos (Porta 27100)

A comunicação via socket TCP em `127.0.0.1:27100` funcionou de forma **imediata, estável e com latência praticamente zero**:

1. **Catálogo de Comandos (`help`)**:
   * Respondeu listando os 15 comandos do mod perfeitamente.

2. **Listagem de Jogadores (`players`)**:
   * Detectou e formatou com precisão o jogador conectado em tempo real:
     ```text
     1 jogador(es):
       591 | Pedreiro | 76561198040636105
     alvo: '@<id|steamid|nome> <comando>' ou 'as <id|steamid|nome> <comando>'
     ```

3. **Broadcast Global (`say`)**:
   * O comando `say SSM conectado ao mod BSBR com sucesso!` retornou `ok` e a mensagem foi exibida instantaneamente no chat global dentro do jogo.

4. **Entrega de Itens pelo Contexto do Jogador (`as <SteamID>`)**:
   * Quando o jogador era admin, a entrega funcionou com perfeição:
     ```text
     as 76561198040636105 SpawnItem Hiking_Backpack_01_03
     ```
   * **Resultado**: O mod respondeu `como Pedreiro:` e a mochila **`Hiking_Backpack_01_03` apareceu imediatamente aos pés do personagem no jogo**.

---

## 2. Resposta sobre o Pedido de Teste: `Location "<SteamID64>"`

Testamos a chamada do comando com o parâmetro `Location`:
```text
spawnitem Apple 1 Location "76561198040636105"
```
* **Resultado**: O servidor retornou `ok` e o item foi gerado (quando havia admin ativo).
* **Nossa Observação Técnica sobre o `as`**:  
  A funcionalidade **`as <SteamID64> <comando>`** que você implementou no mod é **muito superior e mais elegante**, porque ela troca o contexto de execução diretamente na memória da Unreal Engine. Isso resolve de forma universal não apenas o `SpawnItem`, mas também `SpawnVehicle`, `Teleport`, etc., sem depender de idiossincrasias de sintaxe de cada um dos 233 comandos do SCUM.

---

## 3. Teste Crítico: Execução com Jogador Comum (ZERO Admins Online)

Realizamos o teste retirando o ID do jogador do `AdminUsers.ini`, deixando **zero administradores conectados no servidor** (apenas 1 jogador comum conectado).

Ao enviar o comando de spawn:
```text
spawnitem Apple 1 Location "76561198040636105"
```
ou
```text
as 76561198040636105 SpawnItem Apple
```

### O que aconteceu no jogo:
O item **não foi entregue** e o SCUM exibiu a seguinte mensagem de erro no chat:
```text
Not authorized to execute command.
[api] spawnitem Apple 1 Location "76561198040636105"
Not authorized to execute command.
```

### O que o UE4SS.log registrou:
```text
[2026-08-26 21:56:27] [bsbr_scum] 'spawnitem Apple 1 Location "76561198040636105"' processado no servidor via PlayerRpcChannel (admin previo: false)
[2026-08-26 21:56:40] [bsbr_scum] sudo 'SpawnItem Apple' (nivel 1 -> 1 -> 1)
```

### Diagnóstico Técnico:
Como o jogador ponte é um jogador comum (`admin previo: false`), quando o mod despacha a chamada via `PlayerRpcChannel`, a engine do SCUM verifica as permissões do remetente e **bloqueia o comando** com *"Not authorized to execute command"*.

**Como resolver na porta Source / API**:
Para que entregas da loja funcionem quando nenhum administrador está jogando:
* O mod precisa conceder `Client_SetIsAdmin(true)` ao jogador ponte **imediatamente antes** de disparar o RPC e **restaurar para `false` via RAII imediatamente após o tick**; **OU**
* Utilizar a estratégia do controller sintético como o mod antigo fazia.

---

## 4. Bug do Regex de Saldo Negativo (`utils/rcon_client.py`)

Agradecemos imensamente por apontar esse detalhe!
* Você tem toda a razão: o regex `Account balance:\s*(\d+)` realmente descartava valores negativos quando o jogador ficava com a conta no vermelho (`-1000`).
* Já acolhemos a correção no backend do SSM utilizando `r"Account balance:\s*(-?\d+)"` tanto para saldo bancário quanto para outros campos numéricos que possam admitir sinal.

---

## 5. Arquitetura da Porta Source RCON (28015)

Achamos a sua proposta de **dois ouvintes (27101 para linha / 28015 para Source RCON persistente)** simplesmente **brilhante**:
* Permite que o SSM converse com o `bsbr_scum` através do nosso cliente oficial `utils/rcon_client.py` (que já possui fila assíncrona, reconexão automática e tratamento de timeout).
* Preserva a porta de linha de comando para administradores usarem scripts PowerShell locais (`scum players`, etc.).
* Cuidaremos do nosso lado para que o `_generate_bsbr_ini()` preserve intacta a seção `[source]` do `config.ini`.

Estamos prontos para testar a porta Source RCON assim que você liberar a build com esse ouvinte!

Um grande abraço,  
**Paulo e Equipe SSM**
