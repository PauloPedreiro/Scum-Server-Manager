# Respostas para o Dev do Frontend – Integração Chat In Game

## Respostas às Dúvidas

### 1. Endpoint está disponível?
✅ **SIM** - O endpoint `GET /api/chat_in_game` está implementado e ativo no backend.

✅ **SIM** - Ele sempre retorna JSON, mesmo em caso de erro. Nunca retorna HTML.

### 2. Resposta do endpoint

#### Quando não há mensagens:
```json
{
  "success": false,
  "message": "Nenhum log de chat encontrado.",
  "data": []
}
```

#### Quando há mensagens:
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
    },
    {
      "timestamp": "2025.07.13-00.29.15",
      "steamId": "987654321",
      "playerName": "Player123",
      "chatType": "Global",
      "message": "oi galera"
    }
  ]
}
```

#### Em caso de erro interno:
```json
{
  "success": false,
  "message": "Erro ao ler log de chat.",
  "error": "Detalhes do erro específico"
}
```

### 3. Proxy/Porta
- **Porta padrão**: 3000
- **URL completa**: `http://localhost:3000/api/chat_in_game`
- **CORS**: O backend tem CORS configurado para aceitar requisições do frontend
- **Proxy**: Se usar Vite, configure no `vite.config.js`:
  ```javascript
  export default {
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:3000',
          changeOrigin: true
        }
      }
    }
  }
  ```

### 4. Caminho correto
✅ **SIM** - O endpoint é exatamente `/api/chat_in_game`
- Não há prefixo adicional como `/v1/`
- URL completa: `http://localhost:3000/api/chat_in_game`

### 5. Logs e debug

#### Logs no backend quando o frontend faz requisição:
```
GET /api/chat_in_game - 200 OK
```

#### Se o endpoint não for encontrado (404):
```json
{
  "success": false,
  "message": "Endpoint não encontrado"
}
```

#### Se houver erro interno (500):
```json
{
  "success": false,
  "message": "Erro interno do servidor",
  "error": "Detalhes do erro"
}
```

### 6. Exemplo de resposta real
```json
{
  "success": true,
  "message": "Mensagens lidas com sucesso.",
  "data": [
    {
      "timestamp": "2025.07.13-00.28.58",
      "steamId": "76561198123456789",
      "playerName": "Wolf",
      "chatType": "Local",
      "message": "flw galera"
    },
    {
      "timestamp": "2025.07.13-00.29.15",
      "steamId": "76561198987654321",
      "playerName": "Player123",
      "chatType": "Global",
      "message": "oi pessoal"
    },
    {
      "timestamp": "2025.07.13-00.30.22",
      "steamId": "76561198111222333",
      "playerName": "SquadMember",
      "chatType": "Squad",
      "message": "vamos jogar"
    }
  ]
}
```

### 7. Dependências

#### Variáveis de ambiente necessárias:
- `SCUM_LOG_PATH`: Caminho para os logs do SCUM (ex: `C:/SCUM/Logs/`)

#### Configurações:
- O backend deve estar rodando
- Os logs de chat devem existir no caminho configurado
- Webhook do Discord (opcional, só para envio das mensagens)

#### Autenticação:
❌ **NÃO** - Não há autenticação necessária para este endpoint

## Troubleshooting

### Se receber HTML ao invés de JSON:

1. **Verifique se o backend está rodando**:
   ```bash
   curl http://localhost:3000/api/chat_in_game
   ```

2. **Verifique se a porta está correta**:
   - Backend: porta 3000
   - Frontend: verifique se está acessando a porta correta

3. **Verifique o proxy do Vite**:
   ```javascript
   // vite.config.js
   export default {
     server: {
       proxy: {
         '/api': {
           target: 'http://localhost:3000',
           changeOrigin: true
         }
       }
     }
   }
   ```

4. **Teste direto no navegador**:
   - Acesse: `http://localhost:3000/api/chat_in_game`
   - Deve retornar JSON, não HTML

### Se o endpoint não for encontrado:

1. **Verifique se o servidor está rodando**:
   ```bash
   npm start
   # ou
   node server.js
   ```

2. **Verifique se a rota está registrada**:
   - O arquivo `routes/chat.js` deve estar importado no `server.js`

## Exemplo de implementação no frontend

```javascript
// Função para buscar mensagens do chat
async function fetchChatMessages() {
  try {
    const response = await fetch('/api/chat_in_game');
    const data = await response.json();
    
    if (data.success) {
      // Processar mensagens
      data.data.forEach(message => {
        console.log(`${message.playerName}: ${message.message} (${message.chatType})`);
      });
    } else {
      console.log('Nenhuma mensagem nova:', data.message);
    }
  } catch (error) {
    console.error('Erro ao buscar mensagens:', error);
  }
}

// Chamar a cada X segundos para atualização em tempo real
setInterval(fetchChatMessages, 5000); // A cada 5 segundos
```

## Contato

Se ainda houver problemas, verifique:
1. Logs do console do backend
2. Network tab do navegador
3. Se o backend está rodando na porta correta
4. Se as variáveis de ambiente estão configuradas 