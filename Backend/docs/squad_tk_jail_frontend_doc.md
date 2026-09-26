# 🏛️ Documentação do Front-end: Sistema de Punição por Team Kill (Squad TK Jail)

Este documento especifica a estrutura de dados, os endpoints da API REST do backend, o tratamento de erros e as diretrizes de interface de usuário (UI) para integrar o módulo de **Punição de Team Kill (Squad TK Jail)** no painel administrativo e de shop do SSM 3.0.

---

## 📋 1. Estrutura de Configuração (`squad_tk_jail`)

A configuração do sistema de prisão é integrada ao objeto de configuração global do SSM sob a chave `squad_tk_jail`. A interface administrativa do frontend deve disponibilizar uma seção/tab (ou formulário) para gerenciar as seguintes propriedades:

| Campo | Tipo | Descrição | Valor Padrão | Requisito UI |
| :--- | :--- | :--- | :--- | :--- |
| `enabled` | `boolean` | Ativa/desativa a punição automática de TK. | `false` | Toggle Switch |
| `jail_coordinates` | `string` | Coordenadas da cela no jogo (formato `X Y Z` ou `{X=... Y=... Z=...}`). | `"-271417.281 314246.875 84056.023"` | Input Text |
| `jail_radius_meters` | `number` | Raio máximo em metros que o jogador pode se afastar da cela antes de ser teleportado de volta. | `20.0` | Input Number (mínimo `1`) |
| `jail_duration_minutes` | `integer` | Tempo padrão de permanência em prisão (minutos). | `30` | Input Number (mínimo `1`) |
| `warning_color` | `string` | Cor dos avisos exibidos no chat do jogo (string numérica `0`–`7`). | `"2"` (Azul) | Dropdown/Seletor de cor |
| `use_colors` | `boolean` | Define se as mensagens SendChat devem utilizar a cor configurada (ou o branco básico/Announce). | `true` | Toggle Switch |
| `announcement_message` | `string` | Frase anunciada a todos quando alguém é preso. Suporta placeholders `{killer}`, `{victim}` e `{minutes}`. | `"{killer} matou o companheiro de squad {victim} e foi enviado para a prisão por {minutes} minutos!"` | Textarea |
| `escape_message` | `string` | Frase privada exibida ao preso se ele tentar sair do raio da cela. Suporta o placeholder `{player}`. | `"{player}, você tentou escapar! Retornando para a cela."` | Textarea |
| `release_message` | `string` | Frase anunciada a todos quando o preso cumpre a pena e é solto. Suporta o placeholder `{player}`. | `"{player} cumpriu sua pena e foi libertado!"` | Textarea |

---

## 🎨 2. Tabela de Cores do Chat (`warning_color`)

Esta tabela segue o padrão nativo do SCUM RCON para o comando `SendChat`:

| Valor | Cor exibida no jogo | Uso recomendado |
|:---:|:---|:---|
| `"0"` | ⬜ Branco | Mensagens neutras |
| `"2"` | 🔵 Azul | Informações globais |
| `"3"` | 🟢 Verde | Confirmações / sucesso |
| `"4"` | 🟡 Amarelo | Avisos moderados |
| `"6"` | 🟠 Laranja | Mensagens do servidor |
| `"7"` | 🔴 Vermelho | Avisos críticos / erro |

---

## 🌐 3. Endpoints da API REST para Configuração

Todos os endpoints requerem autenticação administrativa (`Authorization: Bearer <token>`).

### 3.1 Obter Configuração Atual
* **Método**: `GET`
* **Rota**: `/api/config`
* **Response (200 OK)**:
```json
{
  "success": true,
  "data": {
    "squad_tk_jail": {
      "enabled": true,
      "jail_coordinates": "-271417.281 314246.875 84056.023",
      "jail_radius_meters": 20.0,
      "jail_duration_minutes": 30,
      "warning_color": "2",
      "use_colors": true,
      "announcement_message": "{killer} matou o companheiro de squad {victim} e foi enviado para a prisão por {minutes} minutos!",
      "escape_message": "{player}, você tentou escapar! Retornando para a cela.",
      "release_message": "{player} cumpriu sua pena e foi libertado!"
    }
  }
}
```

### 3.2 Atualizar Configurações da Prisão
* **Método**: `PUT`
* **Rota**: `/api/config/squad_tk_jail`
* **Request Body**: Enviar o objeto `squad_tk_jail` com as propriedades atualizadas:
```json
{
  "enabled": true,
  "jail_coordinates": "-271417.281 314246.875 84056.023",
  "jail_radius_meters": 20.0,
  "jail_duration_minutes": 30,
  "warning_color": "2",
  "use_colors": true,
  "announcement_message": "{killer} matou o companheiro de squad {victim} e foi enviado para a prisão por {minutes} minutos!",
  "escape_message": "{player}, você tentou escapar! Retornando para a cela.",
  "release_message": "{player} cumpriu sua pena e foi libertado!"
}
```
* **Response (200 OK)**:
```json
{
  "success": true,
  "message": "Section squad_tk_jail updated successfully"
}
```

---

## 🛒 4. Restrição de Compra no Shop (Tratamento de Erro)

O backend agora valida se um jogador que tenta finalizar um pedido de compra de itens ou kits está preso.

* **Endpoint**: `POST /api/shop/orders`
* **Retorno quando o jogador está preso (403 Forbidden)**:
```json
{
  "success": false,
  "error": "PLAYER_JAILED"
}
```

### 💡 Diretriz de Implementação no Frontend:
1. Ao realizar uma requisição para a rota de pedidos `/api/shop/orders`, a aplicação frontend deve capturar a resposta caso retorne status `403` ou a propriedade `error` seja `"PLAYER_JAILED"`.
2. Em vez do alerta genérico de falha, exibir um modal explicativo ou notificação em destaque (Toast / Alert vermelho):
   > **Compra Negada**
   > *"Você não pode realizar compras na loja ou resgatar kits enquanto estiver cumprindo pena na prisão por Team Kill."*

---

## ℹ️ 5. Outros Bloqueios Automáticos no Backend (Apenas Contexto)

O backend realiza automaticamente o bloqueio de outras ações de forma transparente. **Não é necessária nenhuma ação ou desenvolvimento no frontend** para as seguintes features:
* **Entrada em Eventos**: O comando `/evento <CÓDIGO>` in-game e o botão do Discord de teletransporte para eventos ativos do servidor estão bloqueados para jogadores presos. O servidor responde automaticamente ao jogador informando a restrição.
* **Comando `/buy` e `/kit` In-Game**: O bot responde diretamente ao chat do jogador recusando a transação.
* **Upgrades de Atributos/Skills**: Bloqueados in-game para evitar teletransportes ou manipulação de status durante a detenção.
