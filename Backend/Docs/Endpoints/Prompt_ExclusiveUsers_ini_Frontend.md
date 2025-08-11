# Endpoints para ExclusiveUsers.ini

## Visão Geral
Este documento descreve os endpoints disponíveis para gerenciar o arquivo `ExclusiveUsers.ini` do servidor SCUM. Este arquivo controla quais jogadores têm acesso exclusivo ao servidor (VIP).

## Endpoints Disponíveis

### 1. GET `/api/configserver/ExclusiveUsers.ini`
**Descrição**: Lista todos os usuários exclusivos

**Resposta de Sucesso**:
```json
{
    "success": true,
    "exclusiveUsers": [
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
    "error": "Arquivo ExclusiveUsers.ini não encontrado"
}
```

### 2. PUT `/api/configserver/ExclusiveUsers.ini`
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
    "message": "Arquivo ExclusiveUsers.ini atualizado com sucesso",
    "backupCreated": "ExclusiveUsers_ini_2025-07-21_20-48-51.backup",
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

### 3. POST `/api/configserver/ExclusiveUsers.ini`
**Descrição**: Adiciona um novo usuário à lista exclusiva

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
    "message": "Usuário exclusivo adicionado com sucesso",
    "backupCreated": "ExclusiveUsers_ini_2025-07-21_20-48-51.backup"
}
```

**Resposta de Erro**:
```json
{
    "success": false,
    "error": "SteamID já existe no ExclusiveUsers.ini"
}
```

### 4. DELETE `/api/configserver/ExclusiveUsers.ini`
**Descrição**: Remove um usuário da lista exclusiva

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
    "message": "Usuário removido da lista exclusiva com sucesso",
    "backupCreated": "ExclusiveUsers_ini_2025-07-21_20-48-51.backup"
}
```

**Resposta de Erro**:
```json
{
    "success": false,
    "error": "SteamID não encontrado no ExclusiveUsers.ini"
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
- **Formato**: `ExclusiveUsers_ini_YYYY-MM-DD_HH-mm-ss.backup`

## Exemplos de Uso

### Adicionar usuário à lista exclusiva
```javascript
const response = await fetch('/api/configserver/ExclusiveUsers.ini', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        steamId: '76561199191241308'
    })
});
```

### Listar usuários exclusivos
```javascript
const response = await fetch('/api/configserver/ExclusiveUsers.ini');
const data = await response.json();
console.log(data.exclusiveUsers);
```

### Remover usuário da lista exclusiva
```javascript
const response = await fetch('/api/configserver/ExclusiveUsers.ini', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        steamId: '76561199191241308'
    })
});
```

### Substituir lista completa de usuários exclusivos
```javascript
const response = await fetch('/api/configserver/ExclusiveUsers.ini', {
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
7. **Acesso Exclusivo**: Usuários nesta lista têm prioridade de acesso ao servidor
8. **VIP**: Geralmente usado para jogadores que pagaram por acesso exclusivo

## Códigos de Status HTTP

- **200**: Operação realizada com sucesso
- **400**: Dados inválidos ou duplicata
- **404**: Arquivo não encontrado ou SteamID não encontrado
- **500**: Erro interno do servidor

## Casos de Uso Comuns

### Adicionar VIP
```javascript
// Adicionar à lista exclusiva
await fetch('/api/configserver/ExclusiveUsers.ini', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ steamId: '76561199191241308' })
});
```

### Remover VIP
```javascript
// Remover da lista exclusiva
await fetch('/api/configserver/ExclusiveUsers.ini', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ steamId: '76561199191241308' })
});
```

### Verificar se jogador é VIP
```javascript
// Listar todos os exclusivos e verificar
const response = await fetch('/api/configserver/ExclusiveUsers.ini');
const data = await response.json();
const isExclusive = data.exclusiveUsers.some(user => 
    user.steamId === '76561199191241308'
);
```

### Gerenciar lista VIP
```javascript
// Substituir toda a lista VIP
await fetch('/api/configserver/ExclusiveUsers.ini', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        content: [
            '76561198040636105', // VIP 1
            '76561198398160339', // VIP 2
            '76561197963358180'  // VIP 3
        ]
    })
});
```

## Diferenças dos Outros Endpoints

- **AdminUsers.ini**: Administradores com poderes especiais
- **WhitelistedUsers.ini**: Usuários autorizados a conectar
- **BannedUsers.ini**: Usuários banidos do servidor
- **ExclusiveUsers.ini**: Usuários VIP com acesso prioritário

Cada arquivo tem uma função específica no sistema de controle de acesso do servidor SCUM. 