# Notificações RCON Dinâmicas da Loja - SSM 3.0

Esta documentação detalha a funcionalidade de customização de notificações RCON para a loja de prêmios/kits do SSM 3.0.

---

## 1. Estrutura de Dados (`data/config.json`)
O arquivo `config.json` armazena os templates na seção `"shop_notifications"`:

```json
{
  "shop_notifications": {
    "welcome_kit_delivered": "Seu kit foi entregue com sucesso!",
    "items_delivered": "Seus itens foram entregues com sucesso!",
    "insufficient_funds": "Saldo insuficiente! Seu saldo atual: R$ {balance}"
  }
}
```

### Campos e Substituições:
- **`welcome_kit_delivered`**: Mensagem enviada via RCON na entrega bem-sucedida de qualquer Kit.
- **`items_delivered`**: Mensagem enviada via RCON na entrega de itens normais/avulsos do catálogo.
- **`insufficient_funds`**: Mensagem de saldo insuficiente ao tentar realizar compras pelo chat. Suporta a variável dinâmica `{balance}`, que o backend substitui pelo saldo atual do jogador.

---

## 2. API Endpoints
As operações de configuração utilizam os endpoints genéricos `/api/config`:

### Obter Notificações
- **Método**: `GET`
- **URL**: `/api/config?section=shop_notifications`
- **Headers**: `Authorization: Bearer <token>`
- **Resposta**:
  ```json
  {
    "success": true,
    "data": {
      "welcome_kit_delivered": "Seu kit...",
      "items_delivered": "Seus itens...",
      "insufficient_funds": "Saldo insuficiente..."
    }
  }
  ```

### Atualizar Notificações
- **Método**: `POST`
- **URL**: `/api/config`
- **Headers**: `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Payload**:
  ```json
  {
    "section": "shop_notifications",
    "data": {
      "welcome_kit_delivered": "Novo texto...",
      "items_delivered": "Novo texto...",
      "insufficient_funds": "Novo texto: {balance}"
    },
    "backup": true
  }
  ```

---

## 3. Comandos RCON e Sequenciamento (Combo)
O SSM 3.0 utiliza um padrão **"Combo"** para garantir que as notificações sejam exibidas de forma clara e visível para o jogador:
1. **Comando HUD (Tipo 4)**: Envia a notificação como um monólogo interno do personagem (texto sutil que aparece flutuando próximo ao meio da tela).
2. **Delay**: Aguarda **0.2 segundos** para processamento sequencial no servidor do SCUM.
3. **Comando Toast (Tipo 1)**: Envia a notificação como um alerta de estilo de drop de carga no canto superior direito.

Comandos enviados internamente pelo RconClient:
```
SendNotification 4 0 "Mensagem Customizada" <SteamID>
SendNotification 1 0 "Mensagem Customizada" <SteamID>
```
