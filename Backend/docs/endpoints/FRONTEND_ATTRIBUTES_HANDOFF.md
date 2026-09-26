# Handoff - Configuração de Preços de Upgrade de Atributos e Skills

Como o próprio jogador realiza os upgrades in-game através de comandos de chat (`/f[1-8]`, `/c[1-5]`, `/d[1-5]`, `/i[1-5]`) em tempo real via RCON, a única responsabilidade do administrador no frontend agora é configurar os **valores de cobrança** para cada nível de upgrade.

---

## 1. Funcionamento do Fluxo

1. **Definição de Preços (Admin)**: O administrador acessa a aba de configurações de atributos no Painel Web e define o custo em créditos de loja para subir cada atributo de nível.
2. **Execução In-Game (Jogador)**: O jogador digita no chat global o comando desejado (ex: `/f5` para Força nível 5).
3. **Cobrança e RCON (Backend)**: O backend valida o saldo, deduz o valor configurado e envia os comandos RCON `SetAttributes` e `SetSkillLevel` para o jogador online.

---

## 2. API Endpoints para o Frontend

As configurações de preços são armazenadas diretamente na tabela `attribute_upgrade_prices` do banco de dados SQLite `SSM.db`. O frontend interage com esta tabela através dos seguintes endpoints dedicados:

### A. Obter Preços Atuais
Retorna a matriz de preços por atributo e nível.

* **URL**: `/api/attributes/prices`
* **Método**: `GET`
* **Headers**:
  ```
  Authorization: Bearer <JWT>
  ```
* **Resposta de Sucesso (`200 OK`)**:
  ```json
  {
    "success": true,
    "data": {
      "prices": {
        "strength": {
          "1": 100,
          "2": 200,
          "3": 300,
          "4": 400,
          "5": 500,
          "6": 1000,
          "7": 2000,
          "8": 4000
        },
        "constitution": {
          "1": 100,
          "2": 200,
          "3": 300,
          "4": 400,
          "5": 800
        },
        "dexterity": {
          "1": 100,
          "2": 200,
          "3": 300,
          "4": 400,
          "5": 800
        },
        "intelligence": {
          "1": 100,
          "2": 200,
          "3": 300,
          "4": 400,
          "5": 800
        }
      }
    }
  }
  ```

### B. Salvar Novos Preços
Salva as alterações de preços inseridas pelo administrador. Requer permissão de admin.

* **URL**: `/api/attributes/prices`
* **Método**: `PUT`
* **Headers**:
  ```
  Authorization: Bearer <JWT>
  Content-Type: application/json
  ```
* **Body**: Enviar o objeto contendo todos os níveis e custos atualizados.
  ```json
  {
    "strength": {
      "1": 150,
      "2": 250,
      "3": 350,
      "4": 450,
      "5": 600,
      "6": 1200,
      "7": 2500,
      "8": 5000
    },
    "constitution": {
      "1": 120,
      "2": 220,
      "3": 320,
      "4": 450,
      "5": 900
    },
    "dexterity": {
      "1": 120,
      "2": 220,
      "3": 320,
      "4": 450,
      "5": 900
    },
    "intelligence": {
      "1": 120,
      "2": 220,
      "3": 320,
      "4": 450,
      "5": 900
    }
  }
  ```
* **Resposta de Sucesso (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Preços de upgrades de atributos salvos com sucesso no banco de dados."
  }
  ```

---

## 3. Sugestão de Layout no Frontend (Configurações)

Recomendamos criar uma nova aba no menu de Configurações chamada **"Preços de Atributos"** ou **"Progressão In-Game"**:
- **Cards de Atributos**: 4 Cards correspondentes a Força, Constituição, Destreza e Inteligência.
- **Inputs por Nível**:
  - Força: 8 inputs de nível (Nível 1 a Nível 8).
  - Outros: 5 inputs de nível (Nível 1 a Nível 5).
- **Valores default/placeholders**: Preencher com os valores retornados do GET.
- **Validação de Entrada**: Bloquear valores negativos nos campos numéricos de preço.
- **Ações**: Botões "Salvar Alterações" e "Reverter".
