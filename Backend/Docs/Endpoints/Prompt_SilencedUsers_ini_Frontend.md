# Endpoints para SilencedUsers.ini

## Visão Geral
Este documento descreve os endpoints disponíveis para gerenciar o arquivo `SilencedUsers.ini` do servidor SCUM. Este arquivo controla quais jogadores estão silenciados (mute) no servidor.

## Endpoints Disponíveis

### 1. GET `/api/configserver/SilencedUsers.ini`
**Descrição**: Lista todos os usuários silenciados

**Resposta de Sucesso**:
```json
{
    "success": true,
    "silencedUsers": [
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
    "error": "Arquivo SilencedUsers.ini não encontrado"
}
```

### 2. PUT `/api/configserver/SilencedUsers.ini`
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
    "message": "Arquivo SilencedUsers.ini atualizado com sucesso",
    "backupCreated": "SilencedUsers_ini_2025-07-21_20-48-51.backup",
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

### 3. POST `/api/configserver/SilencedUsers.ini`
**Descrição**: Adiciona um novo usuário à lista de silenciados

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
    "message": "Usuário silenciado adicionado com sucesso",
    "backupCreated": "SilencedUsers_ini_2025-07-21_20-48-51.backup"
}
```

**Resposta de Erro**:
```json
{
    "success": false,
    "error": "SteamID já existe no SilencedUsers.ini"
}
```

### 4. DELETE `/api/configserver/SilencedUsers.ini`
**Descrição**: Remove um usuário da lista de silenciados (unmute)

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
    "message": "Usuário removido da lista de silenciados com sucesso",
    "backupCreated": "SilencedUsers_ini_2025-07-21_20-48-51.backup"
}
```

**Resposta de Erro**:
```json
{
    "success": false,
    "error": "SteamID não encontrado no SilencedUsers.ini"
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
- **Formato**: `SilencedUsers_ini_YYYY-MM-DD_HH-mm-ss.backup`

## Exemplos de Uso

### Adicionar usuário à lista de silenciados
```javascript
const response = await fetch('/api/configserver/SilencedUsers.ini', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        steamId: '76561199191241308'
    })
});
```

### Listar usuários silenciados
```javascript
const response = await fetch('/api/configserver/SilencedUsers.ini');
const data = await response.json();
console.log(data.silencedUsers);
```

### Remover usuário da lista de silenciados (unmute)
```javascript
const response = await fetch('/api/configserver/SilencedUsers.ini', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        steamId: '76561199191241308'
    })
});
```

### Substituir lista completa de silenciados
```javascript
const response = await fetch('/api/configserver/SilencedUsers.ini', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        content: [
            '76561198040636105',
            '76561198398160339',
            '76561197963358180'
        ]
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
7. **Silenciado**: Usuários nesta lista não podem enviar mensagens no chat do servidor
8. **Unmute**: DELETE remove o usuário da lista, permitindo voltar a falar

## Códigos de Status HTTP

- **200**: Operação realizada com sucesso
- **400**: Dados inválidos ou duplicata
- **404**: Arquivo não encontrado ou SteamID não encontrado
- **500**: Erro interno do servidor

## Casos de Uso Comuns

### Silenciar um jogador
```javascript
// Adicionar à lista de silenciados
await fetch('/api/configserver/SilencedUsers.ini', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ steamId: '76561199191241308' })
});
```

### Remover silêncio de um jogador
```javascript
// Remover da lista de silenciados
await fetch('/api/configserver/SilencedUsers.ini', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ steamId: '76561199191241308' })
});
```

### Verificar se jogador está silenciado
```javascript
// Listar todos os silenciados e verificar
const response = await fetch('/api/configserver/SilencedUsers.ini');
const data = await response.json();
const isSilenced = data.silencedUsers.some(user => 
    user.steamId === '76561199191241308'
);
``` 