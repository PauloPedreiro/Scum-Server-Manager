# Prompt para Desenvolvedor Frontend: AdminUsers.ini

## Endpoints Disponíveis

### 1. Listar Admins
**GET** `/api/configserver/AdminUsers.ini`
- Retorna todos os admins cadastrados no arquivo AdminUsers.ini.
- Resposta:
```json
{
  "success": true,
  "admins": [
    { "steamId": "76561198040636105[setgodmode]", "playerName": "Pedreiro" },
    { "steamId": "76561199191241308[setgodmode]", "playerName": "RoyHB" }
  ],
  "stats": { "size": 123, "modified": "2025-07-21T20:48:51.139Z", "created": "2025-07-16T01:01:02.548Z" }
}
```

### 2. Adicionar Admin
**POST** `/api/configserver/AdminUsers.ini`
- Adiciona um novo SteamID ao AdminUsers.ini.
- O SteamID será salvo automaticamente com o sufixo `[setgodmode]`.
- Não permite duplicidade (mesmo SteamID não pode ser cadastrado duas vezes).
- Exemplo de body:
```json
{
  "steamId": "76561199191241308"
}
```
- Resposta de sucesso:
```json
{
  "success": true,
  "message": "Admin adicionado com sucesso",
  "backupCreated": "AdminUsers_ini_2025-07-21_20-48-51.backup"
}
```

### 3. Remover Admin
**DELETE** `/api/configserver/AdminUsers.ini`
- Remove um SteamID do AdminUsers.ini.
- Remove todas as linhas cujo SteamID (ignorando sufixos) seja igual ao informado.
- Exemplo de body:
```json
{
  "steamId": "76561199191241308"
}
```
- Resposta de sucesso:
```json
{
  "success": true,
  "message": "Admin removido com sucesso",
  "backupCreated": "AdminUsers_ini_2025-07-21_20-48-51.backup"
}
```
- Se o SteamID não existir, retorna erro 404.

### 4. Substituir Todos os Admins
**PUT** `/api/configserver/AdminUsers.ini`
- Substitui todo o conteúdo do arquivo AdminUsers.ini.
- Body deve ser um array de linhas:
```json
{
  "content": [
    "76561198040636105[setgodmode]",
    "76561199191241308[setgodmode]"
  ]
}
```
- Resposta de sucesso:
```json
{
  "success": true,
  "message": "Arquivo AdminUsers.ini atualizado com sucesso",
  "backupCreated": "AdminUsers_ini_2025-07-21_20-48-51.backup",
  "linesCount": 2
}
```

## Regras de Negócio
- Todo SteamID inserido deve ser salvo com o sufixo `[setgodmode]`.
- Não é permitido duplicidade de SteamID (mesmo número, mesmo com sufixos diferentes).
- O campo `playerName` é preenchido automaticamente a partir do arquivo players.json, se existir.
- Sempre que um admin é adicionado, removido ou o arquivo é alterado, um backup é criado automaticamente.
- Para remoção, o sistema ignora sufixos e remove baseado apenas no número do SteamID.

## Observações
- Em caso de erro, a resposta sempre terá `success: false` e um campo `error` explicando o motivo.
- Todos os endpoints retornam informações sobre o backup criado para auditoria.

---
Dúvidas ou necessidades de novos endpoints, entre em contato com o backend. 