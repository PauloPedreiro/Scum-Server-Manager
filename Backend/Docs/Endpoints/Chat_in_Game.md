# Chat in Game

## Descrição
Endpoint para processar logs de chat do SCUM e enviar mensagens novas para o Discord via webhook. O sistema lê apenas mensagens novas desde o último processamento, evitando duplicatas.

## Endpoint

### Processar Chat in Game
**GET** `/api/chat_in_game`

Lê o log de chat mais recente, filtra mensagens novas e envia para o Discord.

#### Funcionamento
1. Encontra o arquivo de log de chat mais recente (`chat_*.log`)
2. Copia o arquivo para pasta temporária
3. Lê o conteúdo em UTF-16LE
4. Filtra apenas mensagens novas (baseado no timestamp)
5. Envia cada mensagem para o Discord via webhook
6. Atualiza o controle de último timestamp lido
7. Remove arquivo temporário

#### Exemplo de Response (Sucesso)
```json
{
    "success": true,
    "message": "Mensagens lidas com sucesso.",
    "data": [
        {
            "timestamp": "2025.07.13-00.28.58",
            "steamId": "123456789",
            "playerName": "Wolf",
            "chatType": "Local",
            "message": "flw"
        }
    ]
}
```

#### Exemplo de Response (Sem log encontrado)
```json
{
    "success": false,
    "message": "Nenhum log de chat encontrado.",
    "data": []
}
```

#### Exemplo de Response (Erro)
```json
{
    "success": false,
    "message": "Erro ao ler log de chat.",
    "error": "Detalhes do erro"
}
```

## Formato das Mensagens no Discord

As mensagens são enviadas para o Discord no formato:
```
🎯 Wolf: flw
🌐 Player123: oi galera
👥 SquadMember: vamos jogar
```

### Emojis por Tipo de Chat:
- **Local** → 🎯 (alvo - área específica)
- **Global** → 🌐 (mundo - chat global)
- **Squad** → 👥 (grupo de pessoas)

## Controle de Duplicatas

O sistema mantém controle do último timestamp processado no arquivo `src/data/players/lastChatRead.json` para evitar enviar a mesma mensagem múltiplas vezes.

## Configuração do Webhook

Para que as mensagens sejam enviadas ao Discord, é necessário cadastrar um webhook usando o endpoint:
- **POST** `/api/webhook/chat_in_game`

## Estrutura do Log de Chat

O sistema espera logs no formato:
```
2025.07.13-00.28.58: '123456789:Wolf(123)' 'Local: flw'
2025.07.13-00.29.15: '987654321:Player123(456)' 'Global: oi galera'
```

## Arquivos Utilizados

- **Log de chat**: `{SCUM_LOG_PATH}/chat_*.log`
- **Controle de timestamp**: `src/data/players/lastChatRead.json`
- **Webhooks**: `src/data/webhooks.json`
- **Pasta temporária**: `src/data/temp/`

## Códigos de Status HTTP

- **200**: Sucesso
- **500**: Erro interno do servidor

## Exemplo de Uso

### Processar chat:
```bash
curl http://localhost:3000/api/chat_in_game
```

## Logs de Debug

O sistema exibe logs no console para debug:
- Linhas lidas do log
- Matches encontrados pelo regex
- Linhas que não bateram no regex
- Erros ao enviar para Discord

## Dependências

- **SCUM_LOG_PATH**: Variável de ambiente com o caminho dos logs do SCUM
- **Webhook cadastrado**: Para envio das mensagens ao Discord 