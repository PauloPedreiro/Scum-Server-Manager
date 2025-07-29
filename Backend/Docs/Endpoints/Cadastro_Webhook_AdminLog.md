# Endpoint: Cadastro_Webhook_AdminLog

## Método
POST

## Caminho
`/api/webhook/adminlog`

## Descrição
Permite cadastrar ou alterar a URL do webhook do adminlog via API. O valor é salvo em `src/data/webhooks.json` e passa a ser utilizado imediatamente pelo backend para envio das notificações de logs administrativos para o Discord.

Se o arquivo existir, ele tem prioridade sobre o valor do `.env` (`WEBHOOK_ADMINLOG`).

## Parâmetros (Body)
- **url**: string (obrigatório)
  - Exemplo: `https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI`

### Exemplo de Body (JSON)
```json
{
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

## Resposta
- **success**: booleano indicando sucesso
- **message**: mensagem de status
- **url**: a URL cadastrada

### Exemplo de resposta
```json
{
  "success": true,
  "message": "Webhook do adminlog cadastrado/atualizado com sucesso.",
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

## Endpoint de Consulta
### Método
GET

### Caminho
`/api/webhook/adminlog`

### Descrição
Permite consultar a URL do webhook do adminlog atualmente cadastrada.

### Exemplo de resposta (com webhook cadastrado)
```json
{
  "success": true,
  "message": "Webhook recuperado com sucesso.",
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

### Exemplo de resposta (sem webhook cadastrado)
```json
{
  "success": false,
  "message": "Nenhum webhook cadastrado para adminlog.",
  "url": null
}
```

## Observações
- O valor cadastrado é salvo em `src/data/webhooks.json`.
- O backend sempre consulta primeiro esse arquivo para pegar a URL do webhook.
- Se não existir nesse arquivo, usa o valor do `.env`.
- Não altera o arquivo `.env`.
- O endpoint pode ser testado facilmente via Postman.
- A URL deve começar com 'https://' para ser considerada válida.

## Exemplo de uso com Postman

### Para cadastrar/alterar webhook:
1. Selecione o método **POST**
2. URL: `http://localhost:3000/api/webhook/adminlog`
3. Body: selecione **raw** e **JSON**
4. Cole o JSON do exemplo acima
5. Clique em **Send**

### Para consultar webhook atual:
1. Selecione o método **GET**
2. URL: `http://localhost:3000/api/webhook/adminlog`
3. Clique em **Send**

Se a URL for válida, a resposta será de sucesso e o webhook será atualizado imediatamente para os próximos envios de logs administrativos. 