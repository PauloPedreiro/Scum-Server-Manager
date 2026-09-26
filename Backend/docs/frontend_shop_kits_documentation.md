# Documentação de Integração Frontend — Gestão de Kits e Validação de Compra Única (SSM 3.0)

Esta documentação detalha a integração com o novo sistema de **Kits de Loja** e controle de **Kits de Boas-Vindas (Compra Única)** do SSM 3.0.

---

## 📋 Visão Geral

O backend agora suporta a criação de kits de itens (compostos por vários itens agrupados por classe e suas respectivas quantidades). O fluxo do administrador permite:
1. **Cadastrar Kits Manualmente** vinculando itens a um código de catálogo.
2. **Cadastrar Kits via Escaneamento de Baú**: O admin fornece o `chest_id` de um baú do jogo, o backend escaneia todos os itens de dentro dele, agrupa por tipo de item calculando as quantidades correspondentes e gera o Kit de forma atômica no banco de dados.
3. **Bloqueio de Recompra (`only_once`)**: Kits de compra única (como kits de boas-vindas) são validados no momento da compra do jogador. Se ele já possuir qualquer pedido anterior (pendente ou entregue) daquele kit, a transação é bloqueada.

---

## 🛠️ Modificações Recomendadas no Frontend

### 1. Extensão de Tipos e Métodos em `src/services/shopAdmin.ts`
Adicione os seguintes tipos e funções ao arquivo de serviços administrativos da loja:

```typescript
// --- Novos tipos e estruturas para Kits ---

export type ShopAdminKitItemDetail = {
  setup: string;
  qty: number;
};

export type ShopAdminKit = {
  kit_id: string;
  code: number;
  name: string;
  only_once: boolean; // Mapeado a partir do integer do backend (0 ou 1)
  created_at: string;
  updated_at: string;
  items: ShopAdminKitItemDetail[];
};

// Respostas genéricas de API
export type ShopAdminKitListResponse = ApiSuccess<ShopAdminKit[]> | ApiError;
export type ShopAdminKitDetailResponse = ApiSuccess<ShopAdminKit> | ApiError;
export type ShopAdminKitActionResponse = ApiSuccess<{ message: string }> | ApiError;

export type SaveKitPayload = {
  kit_id: string;
  code: number;
  name: string;
  only_once: boolean;
  items: ShopAdminKitItemDetail[];
};

export type ScanKitPayload = {
  chest_id: number;
  kit_id: string;
  name: string;
  price: number;
  enabled: boolean;
  only_once: boolean;
  code?: number; // Opcional (se omitido, o backend gera um código sequencial)
};

// --- Funções de API de Kits ---

/**
 * Retorna a lista de todos os kits cadastrados
 */
export async function getShopAdminKits(): Promise<ShopAdminKitListResponse> {
  const { data } = await api.get<ShopAdminKitListResponse>('/shop/admin/kits');
  return data;
}

/**
 * Cria ou edita um kit manualmente
 */
export async function saveShopAdminKit(payload: SaveKitPayload): Promise<ShopAdminKitActionResponse> {
  const { data } = await api.post<ShopAdminKitActionResponse>('/shop/admin/kits', payload);
  return data;
}

/**
 * Obtém os detalhes de um kit específico
 */
export async function getShopAdminKitDetail(kitId: string): Promise<ShopAdminKitDetailResponse> {
  const { data } = await api.get<ShopAdminKitDetailResponse>(`/shop/admin/kits/${encodeURIComponent(kitId)}`);
  return data;
}

/**
 * Deleta um kit específico
 */
export async function deleteShopAdminKit(kitId: string): Promise<ShopAdminKitActionResponse> {
  const { data } = await api.delete<ShopAdminKitActionResponse>(`/shop/admin/kits/${encodeURIComponent(kitId)}`);
  return data;
}

/**
 * Escaneia um baú in-game e cria um kit automaticamente
 */
export async function scanChestToKit(payload: ScanKitPayload): Promise<ApiSuccess<ShopAdminKit> | ApiError> {
  const { data } = await api.post<any>('/shop/admin/kits/scan', payload);
  return data;
}
```

---

## 📡 Detalhes dos Endpoints (Referência Técnica)

### 1. Listar todos os Kits
*   **Rota**: `GET /api/shop/admin/kits`
*   **Auth**: Token JWT Admin no Header `Authorization: Bearer <token>`
*   **Resposta (HTTP 200)**:
    ```json
    {
      "success": true,
      "data": [
        {
          "kit_id": "kit_boas_vindas",
          "code": 1002,
          "name": "Kit Boas-Vindas Premium",
          "only_once": true,
          "created_at": "2026-05-24 03:00:00",
          "updated_at": "2026-05-24 03:00:00",
          "items": [
            { "setup": "Hiking_Backpack_01_03", "qty": 1 },
            { "setup": "Weapon_MP5", "qty": 1 }
          ]
        }
      ]
    }
    ```

### 2. Cadastrar / Atualizar Kit Manualmente
*   **Rota**: `POST /api/shop/admin/kits`
*   **Auth**: Token JWT Admin no Header
*   **Payload (JSON)**:
    *   `kit_id` (string, obrigatório): ID do kit (ex: `"kit_boas_vindas"`).
    *   `code` (number, obrigatório): Código cadastrado na tabela de catálogo correspondente.
    *   `name` (string, obrigatório): Nome amigável do kit.
    *   `only_once` (boolean, obrigatório): Define se é um kit de compra única.
    *   `items` (array de objetos, obrigatório):
        *   `setup` (string): Classe de spawn do item.
        *   `qty` (number): Quantidade do item.
*   **Resposta (HTTP 200)**:
    ```json
    {
      "success": true,
      "message": "Kit 'Kit Boas-Vindas Premium' saved successfully."
    }
    ```

### 3. Escanear Baú in-game e Criar Kit
*   **Rota**: `POST /api/shop/admin/kits/scan`
*   **Auth**: Token JWT Admin no Header
*   **Payload (JSON)**:
    *   `chest_id` (number, obrigatório): ID numérico do baú encontrado no mapa ou na lista de baús do jogador.
    *   `kit_id` (string, obrigatório): ID único do kit a ser cadastrado.
    *   `name` (string, obrigatório): Nome amigável do kit.
    *   `price` (number, obrigatório): Preço da oferta de venda na loja.
    *   `enabled` (boolean, obrigatório): Define se o kit fica ativo na loja imediatamente.
    *   `only_once` (boolean, obrigatório): Define se é kit de compra única.
    *   `code` (number, opcional): Se omitido, o backend gerará o próximo número sequencial de oferta livre automaticamente.
*   **Resposta (HTTP 201)**:
    ```json
    {
      "success": true,
      "message": "Kit 'Super Kit' scanned from chest 999999 and created successfully.",
      "data": {
        "kit_id": "super_kit",
        "code": 1003,
        "name": "Super Kit",
        "price": 250,
        "enabled": true,
        "only_once": true,
        "items": [
          { "setup": "Hiking_Backpack_01_03", "qty": 1 },
          { "setup": "Weapon_MP5", "qty": 2 }
        ]
      }
    }
    ```
*   **Possíveis Erros**:
    *   `CHEST_NOT_FOUND_SCUMDB` (HTTP 400): Baú não encontrado no banco de dados do jogo.
    *   `The scanned chest is empty` (HTTP 400): O baú foi localizado, mas não possui nenhum item dentro.

---

## 🛒 Fluxo do Jogador (Checkout de Kits)

Quando um jogador compra um kit na loja através do endpoint público `POST /api/shop/orders`, o backend fará a validação de compra única se o kit estiver com `only_once: true`.

*   **Bloqueio de Compra**: Caso o jogador já tenha comprado o kit anteriormente, o backend responderá com **HTTP 400** e uma mensagem formatada contendo a string de erro `KIT_ALREADY_PURCHASED:<code_do_kit>`.
*   **Ação Recomendada para o Frontend**:
    *   Na página da loja pública ou no fluxo de checkout, capturar o erro da requisição de compra.
    *   Se o erro contiver `KIT_ALREADY_PURCHASED`, exibir um modal ou aviso destacando:
        > ⚠️ **Este kit é de uso único!**
        > Você já adquiriu este kit de boas-vindas anteriormente no servidor.
    *   Você também pode esconder o botão de compra ou mostrar um badge "Adquirido" se a listagem retornar o histórico de pedidos do jogador e bater com o código do kit.

---

## 🎨 Protótipo e Sugestão de UI (Admin Panel)

1.  **Formulário / Modal de Scan de Baú**:
    *   Adicionar um botão **"Escanear Baú para Novo Kit"** na tela de gerenciamento de kits / entregas (`ShopDeliveries.tsx`).
    *   Este botão abre um formulário com os seguintes campos:
        *   `ID do Baú` (Input numérico)
        *   `ID do Kit` (Input string sem espaços)
        *   `Nome do Kit` (Input de texto)
        *   `Preço` (Input numérico)
        *   `Ativo na Loja?` (Toggle/Checkbox)
        *   `Compra Única? (Ex: Boas-Vindas)` (Toggle/Checkbox)
    *   Ao submeter, chama `scanChestToKit()`. Ao receber a resposta positiva, atualiza a lista de catálogo e kits na tela.

2.  **Toggle `only_once` na Edição Manual**:
    *   No formulário de edição/criação manual de kits existente na interface de admin, adicionar um checkbox: **"Permitir compra apenas uma vez (Welcome Kit)"**.
    *   Passar o valor booleano no campo `only_once` do payload do `saveShopAdminKit()`.
