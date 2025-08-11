# Endpoint: Cadastro_Webhook

## Método
POST

## Caminho
`/api/webhook/painelplayers`

## Descrição
Permite cadastrar ou alterar a URL do webhook do painel de jogadores (painelplayers) via API. O valor é salvo em `src/data/webhooks.json` e passa a ser utilizado imediatamente pelo backend para envio das notificações do painel de jogadores para o Discord.

Se o arquivo existir, ele tem prioridade sobre o valor do `.env` (`WEBHOOK_PAINELPLAYERS`).

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
  "message": "Webhook do painelplayers cadastrado/atualizado com sucesso.",
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

## Observações
- O valor cadastrado é salvo em `src/data/webhooks.json`.
- O backend sempre consulta primeiro esse arquivo para pegar a URL do webhook.
- Se não existir nesse arquivo, usa o valor do `.env`.
- Não altera o arquivo `.env`.
- O endpoint pode ser testado facilmente via Postman.

## Exemplo de uso com Postman
1. Selecione o método **POST**
2. URL: `http://localhost:3000/api/webhook/painelplayers`
3. Body: selecione **raw** e **JSON**
4. Cole o JSON do exemplo acima
5. Clique em **Send**

Se a URL for válida, a resposta será de sucesso e o webhook será atualizado imediatamente para os próximos envios do painelplayers. 