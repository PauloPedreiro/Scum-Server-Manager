# Endpoints para WhitelistedUsers.ini

## Visão Geral
Este documento descreve os endpoints disponíveis para gerenciar o arquivo `WhitelistedUsers.ini` do servidor SCUM. Este arquivo controla quais jogadores têm acesso ao servidor (whitelist).

## Endpoints Disponíveis

### 1. GET `/api/configserver/WhitelistedUsers.ini`
**Descrição**: Lista todos os usuários na whitelist

**Resposta de Sucesso**:
```json
{
    "success": true,
    "whitelistedUsers": [
        {
            "steamId": "76561198040636105",
            "playerName": "Pedreiro"
        },
        {
            "steamId": "76561198398160339",
            "playerName": "BlueArcher_BR"
        }
    ],
    "stats": {
        "size": 124,
        "modified": "2025-07-04T22:30:52.351Z",
        "created": "2025-07-16T01:01:02.548Z"
    }
}
```

**Resposta de Erro**:
```json
{
    "success": false,
    "error": "Arquivo WhitelistedUsers.ini não encontrado"
}
```

### 2. PUT `/api/configserver/WhitelistedUsers.ini`
**Descrição**: Substitui completamente o conteúdo do arquivo

**Body**:
```json
{
    "content": [
        "76561198040636105",
        "76561198398160339",
        "76561197963358180"
    ]
}
```

**Resposta de Sucesso**:
```json
{
    "success": true,
    "message": "Arquivo WhitelistedUsers.ini atualizado com sucesso",
    "backupCreated": "WhitelistedUsers_ini_2025-07-21_20-48-51.backup",
    "linesCount": 3
}
```

**Resposta de Erro**:
```json
{
    "success": false,
    "error": "Conteúdo deve ser um array de linhas"
}
```

### 3. POST `/api/configserver/WhitelistedUsers.ini`
**Descrição**: Adiciona um novo usuário à whitelist

**Body**:
```json
{
    "steamId": "76561199191241308"
}
```

**Resposta de Sucesso**:
```json
{
    "success": true,
    "message": "Usuário adicionado à whitelist com sucesso",
    "backupCreated": "WhitelistedUsers_ini_2025-07-21_20-48-51.backup"
}
```

**Resposta de Erro**:
```json
{
    "success": false,
    "error": "SteamID já existe no WhitelistedUsers.ini"
}
```

### 4. DELETE `/api/configserver/WhitelistedUsers.ini`
**Descrição**: Remove um usuário da whitelist

**Body**:
```json
{
    "steamId": "76561199191241308"
}
```

**Resposta de Sucesso**:
```json
{
    "success": true,
    "message": "Usuário removido da whitelist com sucesso",
    "backupCreated": "WhitelistedUsers_ini_2025-07-21_20-48-51.backup"
}
```

**Resposta de Erro**:
```json
{
    "success": false,
    "error": "SteamID não encontrado no WhitelistedUsers.ini"
}
```

## Regras de Negócio

### 1. Formato SteamID
- **POST**: SteamID é salvo apenas com os 17 dígitos numéricos
- **Exemplo**: `76561199191241308` → `76561199191241308`

### 2. Verificação de Duplicatas
- **POST**: Não permite adicionar SteamIDs que já existem
- **Verificação**: Ignora sufixos, compara apenas os 17 dígitos

### 3. Busca de Nomes
- **GET**: Automaticamente busca nomes dos jogadores no `players.json`
- **Fallback**: Retorna `null` se o nome não for encontrado

### 4. Backups Automáticos
- **Todas as operações**: Criam backup automático antes de modificar
- **Formato**: `WhitelistedUsers_ini_YYYY-MM-DD_HH-mm-ss.backup`

## Exemplos de Uso

### Adicionar usuário à whitelist
```javascript
const response = await fetch('/api/configserver/WhitelistedUsers.ini', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        steamId: '76561199191241308'
    })
});
```

### Listar usuários na whitelist
```javascript
const response = await fetch('/api/configserver/WhitelistedUsers.ini');
const data = await response.json();
console.log(data.whitelistedUsers);
```

### Remover usuário da whitelist
```javascript
const response = await fetch('/api/configserver/WhitelistedUsers.ini', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        steamId: '76561199191241308'
    })
});
```

## Observações Importantes

1. **Arquivo Vazio**: Se o arquivo estiver vazio, o GET retornará array vazio
2. **Formato SteamID**: Aceita SteamIDs com ou sem sufixo
3. **Backups**: Sempre criados antes de qualquer modificação
4. **Logs**: Todas as operações são registradas no log do servidor
5. **Validação**: SteamIDs devem ter 17 dígitos numéricos
6. **Encoding**: Arquivo salvo em UTF-8 com quebras de linha `\r\n`

## Códigos de Status HTTP

- **200**: Operação realizada com sucesso
- **400**: Dados inválidos ou duplicata
- **404**: Arquivo não encontrado ou SteamID não encontrado
- **500**: Erro interno do servidor 