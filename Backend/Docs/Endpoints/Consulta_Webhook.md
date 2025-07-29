# Endpoint: Consulta_Webhook

## Método
GET

## Caminho
`/api/webhook/painelplayers`

## Descrição
Permite consultar a URL do webhook atualmente cadastrada para o Painel Players. O valor é lido do arquivo `src/data/webhooks.json` (mesma fonte utilizada no cadastro via POST). Caso não exista um webhook cadastrado, retorna `url: null` e uma mensagem apropriada.

## Exemplo de Requisição
```http
GET /api/webhook/painelplayers
```

## Exemplo de Resposta (Sucesso)
```json
{
  "success": true,
  "message": "Webhook recuperado com sucesso.",
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

## Exemplo de Resposta (Webhook não cadastrado)
```json
{
  "success": false,
  "message": "Nenhum webhook cadastrado para painelplayers.",
  "url": null
}
```

## Observações
- O endpoint retorna sempre o valor mais recente salvo, priorizando o arquivo `webhooks.json`.
- Se não houver webhook cadastrado, retorna `url: null` e uma mensagem apropriada.
- O endpoint é seguro para ser chamado a qualquer momento pelo frontend, por exemplo, ao abrir a tela de configuração do webhook.
- O método POST já está disponível para cadastro/atualização do webhook. 