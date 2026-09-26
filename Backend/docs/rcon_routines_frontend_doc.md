# 🕐 Documentação do Front-end: Agendador de Rotinas RCON (Scheduler)

Este documento especifica a estrutura de dados, os endpoints da API REST do backend e as diretrizes de interface de usuário (UI) para integrar o módulo de **Agendamento de Rotinas RCON** do SSM 3.0.

> **Versão:** 2.0 — Atualizado em 2026-07-04
> **Breaking Change:** O campo `warning_color` mudou de HEX (`#FF0000`) para um **tipo numérico** (`0`–`7`). Veja a seção [3.2](#32-formulário-de-criaçãoedição) e a tabela de cores.

---

## 📋 1. Estrutura do Objeto de Rotina (JSON Schema)

Cada rotina é armazenada no backend como um objeto JSON. Abaixo estão os campos que a interface deve exibir e gerenciar:

| Campo | Tipo | Descrição | Requisito / Padrão |
| :--- | :--- | :--- | :--- |
| `id` | `string` | ID único gerado automaticamente pelo backend (UUIDv4). | Somente leitura |
| `name` | `string` | Nome descritivo da rotina (ex: "Limpeza de itens no chão"). | Obrigatório |
| `interval_minutes` | `integer` | Intervalo em minutos de quanto em quanto tempo a rotina rodará. | Obrigatório (mínimo: `1`) |
| `enabled` | `boolean` | Status de ativação da rotina periódica. | Opcional (padrão: `true`) |
| `commands` | `array[string]`| Lista de comandos RCON a serem executados em sequência. | Obrigatório (mínimo 1 comando) |
| `last_run` | `float` \| `null`| Timestamp Unix da última execução bem-sucedida da rotina. | Somente leitura |
| `warning_enabled` | `boolean` | Define se um aviso no chat do jogo deve ser enviado antes da rotina rodar. | Opcional (padrão: `false`) |
| `warning_message` | `string` | Texto da mensagem de aviso. Suporta o placeholder `{minutes}`. | Opcional |
| `warning_color` | `string` | **⚠️ BREAKING CHANGE:** Agora é um número de `0` a `7` (string numérica), representando o tipo de cor do chat do SCUM. Anteriormente era HEX. Padrão: `"7"` (vermelho). | Opcional |
| `warning_minutes_before`| `integer` | Quantidade de minutos antes da execução que o aviso deve ser enviado. | Opcional (mínimo: `1`, máximo: `interval - 1`) |
| `last_warning_run` | `float` \| `null`| Timestamp Unix do último envio do aviso prévio no chat. | Somente leitura |

---

## 🎨 2. Tabela de Cores do Chat (`warning_color`)

> [!IMPORTANT]
> O campo `warning_color` deve ser enviado como uma **string numérica** (ex: `"7"`), não como um valor HEX. Esses tipos são definidos pelo protocolo RCON do SCUM via o comando `SendChat`.

| Valor | Cor exibida no jogo | Uso recomendado |
|:---:|:---|:---|
| `"0"` | ⬜ Branco | Mensagens neutras |
| `"2"` | 🔵 Azul | Informações globais |
| `"3"` | 🟢 Verde | Confirmações / sucesso |
| `"4"` | 🟡 Amarelo | Avisos moderados |
| `"6"` | 🟠 Laranja | Mensagens do servidor |
| `"7"` | 🔴 Vermelho | **Padrão** — avisos críticos de manutenção |

**Recomendação de UI:** Substituir o antigo campo HEX por um seletor visual com os 6 botões de cor acima. O valor enviado via API deve ser a string numérica correspondente.

---

## 🌐 3. Endpoints da API REST

Todos os endpoints requerem autenticação administrativa (`Authorization: Bearer <token>`).

### 3.1 Listar Todas as Rotinas
* **Método:** `GET`
* **Rota:** `/api/rcon-routines`
* **Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "e605d8f6-df30-4e14-9b2f-2d645fc11b43",
      "name": "Limpeza e Manutenção do Servidor (Itens/Corpos)",
      "interval_minutes": 60,
      "enabled": true,
      "last_run": 1751600323.41,
      "commands": [
        "#DestroyAllItemsWithinRadius LuisMoncada_Boots_01 25420000",
        "#DestroyCorpsesWithinRadius 25420000"
      ],
      "warning_enabled": true,
      "warning_message": "AVISO - LIMPEZA DO MAPA EM {minutes} MINUTOS!",
      "warning_color": "7",
      "warning_minutes_before": 5,
      "last_warning_run": 1751600023.15
    }
  ]
}
```

---

### 3.2 Criar Nova Rotina
* **Método:** `POST`
* **Rota:** `/api/rcon-routines`
* **Request Body:**
```json
{
  "name": "Anúncio Periódico",
  "interval_minutes": 60,
  "enabled": true,
  "commands": [
    "Announce Bem-vindos ao nosso servidor SCUM!"
  ],
  "warning_enabled": true,
  "warning_message": "Servidor passará por manutenção em {minutes} minutos!",
  "warning_color": "7",
  "warning_minutes_before": 5
}
```
* **Response (200 OK):** Retorna o objeto criado (incluindo o `id` gerado) sob a chave `"data"`.

---

### 3.3 Editar Rotina Existente
* **Método:** `PUT`
* **Rota:** `/api/rcon-routines/<routine_id>`
* **Request Body:** Enviar apenas os campos que se deseja atualizar.
```json
{
  "interval_minutes": 120,
  "warning_enabled": true,
  "warning_color": "4",
  "warning_message": "Aviso: Manutenção do servidor em {minutes} minutos."
}
```
* **Response (200 OK):** Retorna o objeto completo atualizado sob a chave `"data"`.

---

### 3.4 Excluir Rotina
* **Método:** `DELETE`
* **Rota:** `/api/rcon-routines/<routine_id>`
* **Response (200 OK):**
```json
{
  "success": true,
  "message": "Rotina deletada com sucesso"
}
```

---

### 3.5 Testar Rotina de Forma Síncrona

Este endpoint executa **imediatamente** todos os comandos da rotina com alta prioridade e retorna a resposta do console do jogo em tempo real. Se o aviso prévio estiver habilitado (`warning_enabled: true`), o comando de aviso também é disparado e seu resultado aparece no retorno.

* **Método:** `POST`
* **Rota:** `/api/rcon-routines/<routine_id>/test`
* **Response (200 OK) — com aviso prévio habilitado:**
```json
{
  "success": true,
  "routine_name": "Limpeza e Manutenção do Servidor (Itens/Corpos)",
  "results": [
    {
      "command": "SendChat 7 \"AVISO - LIMPEZA DO MAPA EM 5 MINUTOS!\" 76561198040636105",
      "success": true,
      "response": "Sem resposta do servidor (OK)"
    },
    {
      "command": "#DestroyAllItemsWithinRadius LuisMoncada_Boots_01 25420000",
      "success": true,
      "response": "Destroyed 15 items."
    },
    {
      "command": "#DestroyCorpsesWithinRadius 25420000",
      "success": true,
      "response": "Destroyed 2 corpses."
    }
  ]
}
```

> [!NOTE]
> O backend aguarda no máximo **25 segundos** pela resposta global do RCON para evitar timeouts HTTP do navegador. Se a execução demorar mais, a resposta para o comando excedente será `"Enfileirado (executando em background para evitar timeout HTTP)"`.

> [!NOTE]
> O aviso prévio via `SendChat` é enviado **para cada jogador online individualmente**. No console de resultado do teste, você verá um resultado por jogador online. Isso é comportamento esperado — o `SendChat` do SCUM exige um SteamID de destino e não suporta broadcast nativo.

---

## 🖥️ 4. Comportamento de Envio do Aviso Prévio (Como Funciona no Backend)

É importante o frontend comunicar ao usuário como o aviso funciona, para evitar confusão.

### Fluxo normal (aviso habilitado)
1. O agendador roda a cada **60 segundos** verificando os timers de cada rotina.
2. Quando falta exatamente `warning_minutes_before` minutos para a rotina executar, ele busca os **SteamIDs de todos os jogadores online** no banco de dados.
3. Para cada jogador online, envia: `SendChat <warning_color> "<warning_message>" <steamid>`
   - O `{minutes}` na mensagem é substituído pelo valor real de `warning_minutes_before`.
4. Após `warning_minutes_before` minutos, os comandos da rotina principal são executados.

### Casos especiais que o frontend deve exibir com clareza
| Situação | O que acontece |
|:---|:---|
| Rotina **nova** (nunca executou) com aviso ativado | Aviso é enviado imediatamente e a rotina principal é adiada por `warning_minutes_before` minutos |
| Backend ficou **offline/restart** e rotina está atrasada | Aviso é enviado ao voltar online, e a rotina principal executa após `warning_minutes_before` minutos |
| **Nenhum jogador online** no momento do aviso | Fallback automático para `Announce <mensagem>` (sem cor, broadcast) |

---

## 🎨 5. Diretrizes de Interface de Usuário (UI/UX)

### 5.1 Lista de Rotinas
* Apresentar em formato de cards ou tabela contendo o **Nome**, **Intervalo**, **Status (Switch)** e o timestamp formatado da **Última Execução** (`last_run`) e **Último Aviso** (`last_warning_run`).
* Botões rápidos de **Editar**, **Excluir** e **Testar**.
* Badge visual no card se o aviso prévio estiver ativado (ex: ícone 🔔 ao lado do nome).

### 5.2 Formulário de Criação/Edição

1. **Dados Básicos:**
   * Input de texto para `name`.
   * Input numérico para `interval_minutes` (mínimo `1`).
   * Toggle/switch para `enabled`.

2. **Editor de Comandos:**
   * Lista dinâmica de inputs de texto, um por comando RCON.
   * Botões de adicionar, remover e reordenar linhas.

3. **Painel de Aviso Prévio:**
   * Seção expansível com título **"⚠️ Aviso Prévio no Chat"**.
   * Toggle para `warning_enabled`.
   * Se ativo, exibir:
     * Input numérico para `warning_minutes_before` (mínimo `1`, validar: deve ser `< interval_minutes`).
     * Input de texto para `warning_message`. Exibir hint: *"Use `{minutes}` no texto — será substituído automaticamente pelo valor configurado acima."*
     * **Seletor de cor** para `warning_color`: substituir o antigo campo de hex por **6 botões coloridos** representando as cores da tabela acima. O valor enviado na API é a string numérica (ex: `"7"`).

### 5.3 Feedback do Botão de Teste (Terminal Output)
* Ao clicar em **"Testar"**, abrir modal/painel com spinner carregando.
* Quando a API responder, renderizar como console (fundo escuro, fonte monospace):
  * Header: `# ssm-routine-executor --routine="<name>" --verbose`
  * Cada resultado com ícone ✓ verde para sucesso ou ✗ vermelho para falha.
  * Mostrar o comando enviado e a resposta do servidor SCUM embaixo.
* Exibir uma nota visual: *"Se o aviso prévio estiver ativado, a mensagem de aviso será enviada antes dos comandos de manutenção."*

---

## ⚠️ 6. Breaking Change — Migração do Campo `warning_color`

| | Antes (v1) | Agora (v2) |
|:---|:---|:---|
| **Tipo** | `string` HEX | `string` numérica |
| **Exemplo** | `"#FF0000"` | `"7"` |
| **Componente UI** | Color picker / input hex | Botões de seleção de cor predefinidos |

**Ação necessária no frontend:**
1. Ao carregar rotinas existentes: se o valor de `warning_color` iniciar com `#`, tratar como legado e usar o padrão `"7"`.
2. Ao salvar: enviar apenas o número como string (ex: `"7"`).
3. Substituir o color picker por um seletor de 6 opções visuais baseado na tabela da seção 2.
