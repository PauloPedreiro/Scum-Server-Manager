# Portable Data Directory (EXE)

Este documento descreve o comportamento de arquivos de dados quando o SSM Backend roda como executavel (`Panel SSM.exe`).

## Objetivo

Quando rodando como EXE, a fonte da verdade passa a ser a pasta `data\` ao lado do executavel. Isso evita confusao com arquivos em `%APPDATA%` e garante portabilidade (pode estar em qualquer drive/pasta).

## Pasta de dados usada

### Executavel (EXE)

- Pasta de dados: `<PASTA_DO_EXE>\data\`
- Arquivos principais:
  - `config.json`
  - `webhooks.json`
  - `SSM.db`
  - `license.json`
  - `identity.json`
  - `logs\`, `temp\`, etc.

### Script Python (DEV)

- Pasta de dados: `<PROJETO>\data\`

## Permissao de escrita (obrigatorio)

No modo EXE, o SSM exige que a pasta `<PASTA_DO_EXE>\data\` seja gravavel.

- Se nao for possivel escrever em `data\`, o painel exibe um erro e nao continua.
- Solucao:
  - Executar como Administrador, ou
  - Mover a pasta do SSM para um local gravavel (ex.: `C:\ScumServer\Panel\`).

## Migracao (legado AppData)

Versoes antigas podiam usar `%APPDATA%\SSM Backend\`.

O comportamento atual:

- Se existirem arquivos legados em `%APPDATA%\SSM Backend\` e **nao** existirem os mesmos arquivos na pasta local `data\`, o SSM copia (migra) os arquivos para `data\`.
- O AppData nao e apagado automaticamente (backup).

## Atualizacao automatica do config.json (merge com config.example.json)

No startup, o SSM compara `data\config.json` com `data\config.example.json` e:

- Adiciona somente chaves ausentes do exemplo no `config.json` do usuario.
- Nao sobrescreve valores ja configurados pelo usuario.

Isso garante que novas chaves (ex.: `discord_bot.register_role_id`) aparecam automaticamente mesmo em instalacoes antigas.

## Como confirmar onde foi salvo

Na aba Discord > Bot, ao clicar `Save`, o painel exibe uma mensagem no status:

- `Saved: <caminho>`

Esse caminho indica o `config.json` efetivamente escrito.
