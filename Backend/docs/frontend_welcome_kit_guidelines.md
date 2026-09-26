# Guia de Integração do Frontend: Kit de Boas-Vindas Automático

Este documento descreve as alterações necessárias no painel administrativo do Frontend para suportar o recurso de **Entrega Automática do Kit de Boas-Vindas (Welcome Pack)** ao registrar uma conta de Discord-para-Jogo.

---

## 1. Alterações no Estado e Formulários de Kits
Nas interfaces de:
*   **Modal de Criação / Edição de Kit Manual**
*   **Modal de Escaneamento de Baú para Kit (Scan Chest)**

### Novas Propriedades a Adicionar:
*   **Campo Visual**: Checkbox / Switch `"Entregar Automaticamente no Registro"`
*   **Nome do Campo no State/Payload**: `auto_deliver_on_register` (booleano)

---

## 2. Regra de Negócio e Comportamento da UI (Importante)
Para evitar abusos ou duplicidade indevida de resgates, todo Kit de Boas-Vindas deve obrigatoriamente ser configurado como **"Apenas uma vez"** (`only_once = true`).

### Comportamento Esperado na UI:
1.  Quando o usuário ativar o switch `"Entregar Automaticamente no Registro"` (`auto_deliver_on_register = true`), a UI deve:
    *   Marcar automaticamente o switch `"Apenas uma vez"` (`only_once`) como **ativo (true)**.
    *   **Desabilitar / Bloquear** a interação com o switch `"Apenas uma vez"`, impedindo que o administrador desmarque-o enquanto a entrega automática estiver ativa.
2.  Exibir um pequeno texto de ajuda abaixo do switch:
    > ℹ️ *Kits de Boas-Vindas são configurados obrigatoriamente para resgate único (Apenas uma vez).*

---

## 3. Especificação das APIs Backend

### A. Listagem de Kits (`GET /api/shop/admin/kits`)
A resposta da API agora inclui a propriedade `auto_deliver_on_register` (como `1`/`0` ou booleano):
```json
{
  "success": true,
  "data": [
    {
      "kit_id": "welcome_pack_new",
      "code": 1002,
      "name": "Welcome Pack",
      "only_once": 1,
      "auto_deliver_on_register": 1,
      "price": 0,
      "enabled": 1,
      "items": [
        { "setup": "BP_Weapon_AK47", "qty": 1 }
      ]
    }
  ]
}
```

### B. Detalhes de um Kit (`GET /api/shop/admin/kits/<kit_id>`)
Retorno atualizado incluindo a flag:
```json
{
  "success": true,
  "data": {
    "kit_id": "welcome_pack_new",
    "code": 1002,
    "name": "Welcome Pack",
    "only_once": 1,
    "auto_deliver_on_register": 1,
    "price": 0,
    "enabled": 1,
    "items": [
      { "setup": "BP_Weapon_AK47", "qty": 1 }
    ]
  }
}
```

### C. Salvar/Atualizar Kit (`POST /api/shop/admin/kits`)
Enviar a nova propriedade no payload:
```json
{
  "kit_id": "welcome_pack_new",
  "code": 1002,
  "name": "Welcome Pack",
  "only_once": true,
  "auto_deliver_on_register": true,
  "price": 0,
  "enabled": true,
  "items": [
    { "setup": "BP_Weapon_AK47", "qty": 1 }
  ]
}
```

### D. Escanear e Criar Kit (`POST /api/shop/admin/kits/scan`)
Enviar a nova propriedade no payload de escaneamento de baú:
```json
{
  "chest_id": 987654,
  "kit_id": "welcome_pack_new",
  "code": 1002,
  "name": "Welcome Pack",
  "only_once": true,
  "auto_deliver_on_register": true,
  "price": 0,
  "enabled": true
}
```

*Nota: O backend gerencia a unicidade automaticamente. Se o administrador marcar um novo kit como `auto_deliver_on_register = true`, o backend removerá essa flag de qualquer outro kit cadastrado anteriormente.*
