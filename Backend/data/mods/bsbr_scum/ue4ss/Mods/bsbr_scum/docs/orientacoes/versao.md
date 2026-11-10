# Versão do mod

A versão atual é **0.4.0**. Ela pode ser lida de três formas, e as três sempre
concordam, porque o número nasce num lugar só no código e é carimbado nos três
na hora de compilar.

Voltar ao [índice](../README.md).

---

## Com o servidor no ar

Pela porta Source RCON, ou pela porta de linha, ou pelo chat:

```
version
```

```
bsbr_scum 0.4.0
portas source=28015 linha=27100
opcoes elevate=1 split_replies=0 echo=0 perf_log=0
```

É a resposta mais confiável, porque vem do binário que está carregado naquele
momento. A senha nunca aparece.

Para um gerenciador externo, é uma chamada igual a qualquer outra:

```python
versao = client.send_command("version").splitlines()[0]   # "bsbr_scum 0.4.0"
```

## Com o servidor parado

**Pelo arquivo**, ao lado do `config.ini`:

```
ue4ss\Mods\bsbr_scum\version.txt
```

```
bsbr_scum 0.4.0
carregado 2026-10-15 00:31:04
```

A primeira linha é a versão. A segunda é quando o mod subiu pela última vez, e
serve de aviso: se você trocou a DLL e ainda não reiniciou o servidor, a data
estará velha e o número pode ser o da versão anterior.

**Ou pela própria DLL**, sem depender de arquivo nosso:

```powershell
(Get-Item "...\ue4ss\Mods\bsbr_scum\dlls\main.dll").VersionInfo.FileVersion
```

Esse é o caminho mais direto para um instalador ou painel: é o recurso padrão
de versão do Windows, igual ao que aparece nas propriedades do arquivo.

## Por que não fica no `config.ini`

O `config.ini` é **entrada**: você edita, e um gerenciador externo também
escreve nele. Uma versão ali envelheceria sozinha a cada troca de DLL, ou
sumiria quando o arquivo fosse regravado. Um número que mente sobre qual
binário está rodando atrapalha mais do que ajuda, então a versão fica fora dele.

---

## O que mudou na 0.4.0

- **`DestroyAllBrennersWithinRadius [Radius [m]]`**, comando do mod. O jogo
  não tem como remover o Brenner; este acha os `BP_Brenner_C` num raio do
  jogador do `as` (padrão 50 m) e os destrói. Ver
  [comandos/mod.md](../comandos/mod.md#destroyallbrennerswithinradius--remover-brenners).
- **`SpawnBrenner` passa a exigir `as <SteamID>`.** Sem alvo, o Brenner nascia
  na frente do primeiro jogador vivo. Agora responde o uso e não executa.

## O que mudou na 0.3.0

- **Comando do jogo sem nenhum admin conectado.** A entrega automática de item
  e veículo funciona de madrugada, quando não há administrador online. Ainda é
  preciso um jogador qualquer conectado. Ver
  [comandos/mod.md](../comandos/mod.md).
- **Porta Source endurecida**: limite de conexões, bloqueio após senhas
  erradas, resposta imediata enquanto o servidor ainda está subindo, e escolha
  entre uma resposta inteira ou picotada conforme o cliente.
- **Alvo por SteamID no fim do comando**, no mesmo formato que os
  gerenciadores já usam.
- **Verbo desconhecido** responde sem incomodar o jogo.
- **Chat limpo**: a porta de linha não ecoa mais nada no jogo. O registro
  completo continua em `bsbr_scum.log`, agora com quem digitou cada comando
  pelo chat.
- **`version`**, este comando.
