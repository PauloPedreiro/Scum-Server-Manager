# Documentação de Integração: Kill Feed (SSM Backend 3.0)

Esta documentação detalha os endpoints, esquemas de dados e regras de negócio necessários para implementar a interface do **Kill Feed** e gerenciamento de frases no painel front-end do SSM.

---

## 1. Configurações do Kill Feed (`kill_feed`)

O status do Kill Feed e suas propriedades são armazenados na seção `kill_feed` do arquivo de configuração global (`config.json`).

### Estrutura do Objeto `kill_feed`
```json
{
  "enabled": true,
  "mode": "chat",
  "chat_type": 2,
  "message_template": "{killer} matou {victim} ({weapon} - {distance}m) | {phrase}",
  "phrases_path": "data/kill_feed_phrases.json",
  "priority": 15
}
```

### Campos e Validações:
1. **`enabled`** *(boolean)*: Habilita/desabilita o processamento e o envio do Kill Feed para o jogo.
2. **`mode`** *(string)*: Modo de exibição. Padrão `"chat"`.
3. **`chat_type`** *(integer)*: ID do canal do chat do jogo que determina a cor da mensagem. Ver a tabela de cores abaixo.
4. **`message_template`** *(string)*: Template de mensagem. Deve permitir o uso de tags dinâmicas substituíveis pelo backend:
   - `{killer}`: Nome de quem matou.
   - `{victim}`: Nome de quem morreu.
   - `{weapon}`: Arma utilizada.
   - `{distance}`: Distância da eliminação em metros.
   - `{phrase}`: Frase aleatória do banco de frases.
5. **`priority`** *(integer)*: Prioridade do envio da mensagem na fila do RCON (padrão: `15`).

---

## 2. Tabela de Cores (RCON `chat_type`)

O front-end deve exibir uma seleção amigável (dropdown ou seletores de cores) mapeada para os seguintes inteiros que o SCUM RCON interpreta:

| Valor (`chat_type`) | Cor de Exibição | Descrição / Canal SCUM |
| :---: | :---: | :--- |
| **`0` ou `1`** | ⚪ Branco | Chat Local / Padrão |
| **`2`** | 🔵 Azul | Chat Global |
| **`3`** | 🟢 Verde | Chat de Squad |
| **`4`** | 🟡 Amarelo | Chat do Admin / Anuncio |
| **`6`** | 🟠 Laranja | Mensagem do Servidor |
| **`7`** | 🔴 Vermelho | Alerta / Erro |

---

## 3. Endpoints da API

> Todos os endpoints da API requerem autenticação por padrão. Inclua o cabeçalho HTTP:
> `Authorization: Bearer <seu_token_jwt>`

### 3.1. Obter Configurações Atuais
Retorna a seção de configuração do Kill Feed.

- **URL:** `/api/config?section=kill_feed`
- **Método:** `GET`
- **Resposta (200 OK):**
  ```json
  {
    "success": true,
    "data": {
      "kill_feed": {
        "enabled": true,
        "mode": "chat",
        "chat_type": 2,
        "message_template": "{killer} matou {victim} ({weapon} - {distance}m) | {phrase}",
        "phrases_path": "data/kill_feed_phrases.json",
        "priority": 15
      }
    },
    "timestamp": 1719943542.45
  }
  ```

---

### 3.2. Salvar Configurações
Atualiza a seção inteira do Kill Feed.

- **URL:** `/api/config/kill_feed`
- **Método:** `PUT`
- **Corpo da Requisição (JSON):**
  ```json
  {
    "enabled": true,
    "mode": "chat",
    "chat_type": 4,
    "message_template": "{killer} matou {victim} ({weapon} - {distance}m) | {phrase}",
    "priority": 15
  }
  ```
- **Resposta (200 OK):**
  ```json
  {
    "success": true,
    "message": "Seção \"kill_feed\" atualizada com sucesso",
    "data": {
      "section": "kill_feed",
      "updated_fields": ["enabled", "mode", "chat_type", "message_template", "priority"],
      "requires_restart": []
    },
    "timestamp": 1719943580.12
  }
  ```

> **Aviso Importante para o Usuário:** Qualquer alteração nos campos de configuração de RCON/Kill Feed exige a **reinicialização** do serviço do SSM Backend para que as novas configurações de chat e processamento de logs passem a valer. Recomenda-se adicionar um aviso em banner no front-end caso esta seção seja salva.

---

### 3.3. Listar Frases do Kill Feed
Retorna o array completo das frases configuradas (que preenchem a tag `{phrase}`).

- **URL:** `/api/config/kill-feed-phrases`
- **Método:** `GET`
- **Resposta (200 OK):**
  ```json
  {
    "success": true,
    "data": [
      "foi de arrasta pra cima!",
      "não tankou a pressão.",
      "virou saudades.",
      "bebeu água de poço.",
      "esqueceu de desviar da bala."
    ]
  }
  ```

---

### 3.4. Atualizar Lista de Frases
Substitui a lista completa de frases. O backend realiza a validação de que os dados enviados são obrigatoriamente um array composto exclusivamente por strings.

- **URL:** `/api/config/kill-feed-phrases`
- **Método:** `POST`
- **Corpo da Requisição (JSON):**
  ```json
  [
    "foi de arrasta pra cima!",
    "não tankou a pressão.",
    "virou saudades.",
    "bebeu água de poço.",
    "esqueceu de desviar da bala.",
    "foi pro lobby mais cedo!"
  ]
  ```
- **Resposta (200 OK):**
  ```json
  {
    "success": true,
    "message": "Lista de frases atualizada com sucesso!"
  }
  ```
- **Resposta (400 Bad Request) - Em caso de dados inválidos:**
  ```json
  {
    "success": false,
    "error": "Os dados enviados devem ser uma lista de frases (array de strings)"
  }
  ```

---

## 4. Requisitos Sugeridos para a UI
1. **Ativação Simples**: Um interruptor (Switch/Toggle) conectado à propriedade `enabled`.
2. **Seleção de Cor Prática**: Uma lista do tipo Dropdown com as opções da Tabela de Cores RCON associadas a etiquetas coloridas (ex: bolinhas coloridas ao lado do nome).
3. **Gerenciador de Tags do Template**: Um campo de entrada de texto para o `message_template` com "botões rápidos" que, ao serem clicados, inserem as tags dinâmicas como `{killer}` ou `{victim}` na posição do cursor do usuário.
4. **Gerenciador de Frases (Lista de Zoação)**: Uma seção dinâmica onde o usuário possa adicionar novas frases em uma tabela, editá-las ou excluí-las, enviando a lista completa via `POST` na hora de salvar.
