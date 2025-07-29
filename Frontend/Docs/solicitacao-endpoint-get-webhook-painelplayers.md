# Solicitação de Endpoint GET - Webhook Painel Players

## Objetivo
Permitir que o frontend recupere o endereço do webhook atualmente salvo para o Painel Players, garantindo que o valor exibido na interface seja sempre o mesmo que está em uso pelo backend.

---

## Especificação do Endpoint

- **Método:** GET
- **Rota:** `/api/webhook/painelplayers`

### Descrição
Retorna a URL do webhook atualmente cadastrada para o Painel Players.  
O valor deve ser lido do arquivo `src/data/webhooks.json` (ou fonte equivalente utilizada no POST).

---

### Exemplo de Requisição
```http
GET /api/webhook/painelplayers
```

---

### Exemplo de Resposta (Sucesso)
```json
{
  "success": true,
  "message": "Webhook recuperado com sucesso.",
  "url": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

### Exemplo de Resposta (Webhook não cadastrado)
```json
{
  "success": false,
  "message": "Nenhum webhook cadastrado para painelplayers.",
  "url": null
}
```

---

## Requisitos
- O endpoint deve retornar o valor mais recente salvo, priorizando o arquivo `webhooks.json` (mesma lógica do POST).
- Se não houver webhook cadastrado, retornar `url: null` e uma mensagem apropriada.
- O endpoint deve ser seguro para ser chamado a qualquer momento pelo frontend.

---

## Observações
- O frontend irá consumir esse endpoint ao abrir a tela de configuração do webhook, para exibir o valor salvo no campo de input.
- O método POST já está funcionando normalmente para cadastro/atualização.

---

Se precisar de mais algum detalhe técnico ou ajuste, é só avisar! 