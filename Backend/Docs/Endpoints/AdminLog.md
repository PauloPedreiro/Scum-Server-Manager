# Endpoint AdminLog

## Descrição
Endpoint para leitura e processamento do log de administração do servidor SCUM. O endpoint lê o arquivo de log admin mais recente, salva os dados em JSON e envia novos eventos para o Discord via webhook.

## Endpoint
```
GET /api/adminlog
```

## Funcionamento
1. **Lê o log de admin** mais recente do diretório configurado
2. **Processa o conteúdo** separando cada evento em linhas individuais
3. **Salva no banco** (`src/data/admin/adminlog.json`) com estrutura organizada
4. **Envia para Discord** apenas os novos eventos via webhook configurado
5. **Controle de duplicação** - não envia eventos já processados

## Parâmetros
Nenhum parâmetro necessário.

## Resposta de Sucesso
```json
{
  "success": true,
  "message": "Log admin lido com sucesso",
  "file": "admin_20250714050808.log",
  "data": "\n2025.07.14-05.08.08: Game version: 1.0.1.2.96201\n2025.07.14-05.08.14: Deleting players that haven't logged in for 180 day(s)...\n2025.07.14-05.08.14: Completed in 0.022s for 0 player profiles and 0 players.\n2025.07.14-05.11.46: '76561198040636105:Pedreiro(1)' Command: 'SpawnVehicle BPC_Kinglet_Duster'\n2025.07.14-05.12.12: '76561198040636105:Pedreiro(1)' Command: 'ListPlayers true'"
}
```

## Resposta de Erro
```json
{
  "success": false,
  "message": "Nenhum arquivo de log admin encontrado",
  "data": []
}
```

## Estrutura do Banco de Dados
O endpoint salva os dados em `src/data/admin/adminlog.json`:

```json
{
  "file": "admin_20250714050808.log",
  "content": [
    "2025.07.14-05.08.08: Game version: 1.0.1.2.96201",
    "2025.07.14-05.08.14: Deleting players that haven't logged in for 180 day(s)...",
    "2025.07.14-05.08.14: Completed in 0.022s for 0 player profiles and 0 players.",
    "2025.07.14-05.11.46: '76561198040636105:Pedreiro(1)' Command: 'SpawnVehicle BPC_Kinglet_Duster'",
    "2025.07.14-05.12.12: '76561198040636105:Pedreiro(1)' Command: 'ListPlayers true'"
  ],
  "savedAt": "2025-07-14T05:47:53.630Z"
}
```

## Integração com Discord
- **Webhook configurado** em `src/data/webhooks.json` (chave: `"adminlog"`)
- **Envio automático** de novos eventos para o Discord
- **Controle de duplicação** via `src/data/admin/lastAdminLogLine.json`
- **Status de envio** retornado no console do servidor

## Exemplos de Eventos
- Comandos de administrador: `'76561198040636105:Pedreiro(1)' Command: 'SpawnVehicle BPC_Kinglet_Duster'`
- Informações do servidor: `Game version: 1.0.1.2.96201`
- Operações do sistema: `Deleting players that haven't logged in for 180 day(s)...`

## Configuração
- **Caminho dos logs**: Configurado em `.env` (`SCUM_LOG_PATH`)
- **Webhook Discord**: Configurado em `src/data/webhooks.json`
- **Arquivos de controle**: 
  - `src/data/admin/adminlog.json` (dados salvos)
  - `src/data/admin/lastAdminLogLine.json` (controle de envio)

## Uso no Frontend
```javascript
// Exemplo de chamada
fetch('/api/adminlog')
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      console.log('Log processado:', data.file);
      console.log('Conteúdo:', data.data);
    } else {
      console.error('Erro:', data.message);
    }
  });
```

## Observações
- O endpoint processa automaticamente novos eventos
- Cada evento é enviado individualmente para o Discord
- O sistema mantém controle para evitar duplicação
- Logs detalhados são exibidos no console do servidor 