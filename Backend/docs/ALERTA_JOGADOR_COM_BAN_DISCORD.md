# Alerta de Jogador com Ban (Discord)

## Objetivo

Quando um jogador entra no servidor e e identificado como **novo jogador**, o backend consulta o perfil Steam (Steam Community XML) e, se detectar **ban**, envia um alerta para um canal dedicado do Discord via webhook.

## Configuracao

### Arquivo: `data/webhooks.json`

Adicionar/configurar a chave:

```json
{
  "ban-list": "https://discord.com/api/webhooks/<id>/<token>"
}
```

- O webhook `ban-list` e usado **somente** para o alerta de jogador com ban.
- Se `ban-list` nao existir no `webhooks.json`, o backend cria automaticamente a chave (com valor vazio) ao carregar webhooks via `WebhooksManager.load()`.

### Arquivo: `data/webhooks.example.json`

A chave `ban-list` existe no arquivo de exemplo para garantir que o `webhooks.json` seja completado automaticamente.

## Fonte dos dados de ban

A consulta e feita via Steam Community XML (sem API key):

- `http://steamcommunity.com/profiles/<steamid64>/?xml=1`

Campos utilizados:

- `vacBanned` (0/1)
- `tradeBanState` (ex: `None`, `Probation`, `Banned`, etc.)
- `isLimitedAccount` (0/1) (campo informativo no embed)

## Regra de deteccao de ban

Um jogador e considerado "com ban" quando:

- `vac_banned == True`
  ou
- `trade_ban_state.lower() != "none"`

## Fluxo

1. Log de login e processado.
2. Se o `steam_id` ainda nao existe no banco de dados, o jogador e marcado como **novo**.
3. O backend consulta a Steam Community XML para obter dados do perfil.
4. Se detectar ban pela regra acima, envia embed para o webhook `ban-list`.
5. Em seguida envia a notificacao normal de novo jogador (webhook `new_player`).

## Formato do embed (ban-list)

Titulo:
- `Banned Player Detected`

Campos:
- `In-Game Name`
- `Steam Name`
- `Steam ID`
- `Country`
- `VAC Banned`
- `Trade Ban State`
- `Limited Account`
- `Steam Profile`

Thumbnail:
- Avatar (quando disponivel)

## Arquivos envolvidos

- `core/logs/steam_api.py`
  - Parse de `vacBanned`, `tradeBanState`, `isLimitedAccount` no XML
  - `format_player_info()` repassa os campos para uso no Discord

- `core/logs/player_processor.py`
  - Carrega webhooks via `WebhooksManager.load()`
  - Envia alerta no `ban-list` quando novo jogador tem ban

- `core/webhooks/manager.py`
  - Estrutura padrao inclui `ban-list` para auto-completar o `webhooks.json`

- `data/webhooks.example.json`
  - Inclui `ban-list`

## Teste manual do embed

Para enviar um embed de teste (requer que `ban-list` esteja configurado em `data/webhooks.json`):

```bash
python -c "import json,requests; w=json.load(open('data/webhooks.json','r',encoding='utf-8')); url=w.get('ban-list'); assert url; steam_id='76561198040636105'; payload={'embeds':[{'title':'🚨 Banned Player Detected','color':0xE74C3C,'fields':[{'name':'In-Game Name','value':'TEST_PLAYER_INGAME','inline':True},{'name':'Steam Name','value':'TEST_STEAM_NAME','inline':True},{'name':'Steam ID','value':f'`{steam_id}`','inline':True},{'name':'Country','value':'🌍 Test','inline':True},{'name':'VAC Banned','value':'Yes','inline':True},{'name':'Trade Ban State','value':'None','inline':True},{'name':'Limited Account','value':'No','inline':True},{'name':'🔗 Steam Profile','value':f'[Click here](https://steamcommunity.com/profiles/{steam_id})','inline':False}], 'thumbnail':{'url':'https://avatars.akamai.steamstatic.com/08c9b59eb71652da144aefdab3c3dcb7281dd601_full.jpg'}, 'footer':{'text':'SCUM Server Manager'}}]}; r=requests.post(url,json=payload,headers={'Content-Type':'application/json'},timeout=10); print(r.status_code)"
```

## Observacao sobre `dist/`

Arquivos dentro de `dist/` podem estar gitignored/gerados. Se voce roda o executavel/build a partir de `dist`, garanta que o `webhooks.json` usado pelo build tambem contenha a chave `ban-list`.
