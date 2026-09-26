# Plano de Implementação: Agendador de Rotinas RCON (Option B)

Este plano descreve a estrutura de arquivos, serviços e endpoints para implementar o agendamento de comandos RCON agrupados por rotinas periódicas.

---

## 1. Estrutura de Armazenamento (`data/rcon_routines.json`)

As rotinas e seus respectivos comandos serão salvos em um arquivo JSON dinâmico.

### Estrutura do JSON:
```json
[
  {
    "id": "limpeza_lag",
    "name": "Limpeza de Lag",
    "interval_minutes": 60,
    "enabled": true,
    "last_run": null,
    "commands": [
      "#DestroyAllItemsWithinRadius LuisMoncada_Boots_01 25420000",
      "#DestroyAllItemsWithinRadius LuisMoncada_Glove_01 25420000",
      "#DestroyCorpsesWithinRadius 25420000"
    ]
  },
  {
    "id": "anuncios_servidor",
    "name": "Anúncios do Servidor",
    "interval_minutes": 15,
    "enabled": false,
    "last_run": null,
    "commands": [
      "Say Bem-vindos ao servidor! Digite /help para comandos.",
      "Say Visite nosso Discord para eventos semanais!"
    ]
  }
]
```

---

## 2. Manager de Rotinas (`core/scheduler/rcon_routine_manager.py`)

Esta classe será responsável pela leitura, escrita e manipulação (CRUD) do arquivo `rcon_routines.json`. Ela usará uma trava de thread (`threading.Lock`) para garantir segurança de concorrência.

### Principais Operações:
* `load_routines()`: Lê e retorna a lista de rotinas. Cria um array vazio ou default se o arquivo não existir.
* `save_routines(routines)`: Salva a lista de rotinas no disco.
* `get_routine(routine_id)`: Retorna uma rotina específica.
* `add_routine(name, interval_minutes, commands, enabled)`: Adiciona uma nova rotina gerando um UUID único como `id`.
* `update_routine(routine_id, data)`: Atualiza campos de uma rotina.
* `delete_routine(routine_id)`: Remove uma rotina da lista.
* `update_last_run(routine_id, timestamp)`: Atualiza o timestamp de execução de forma atômica.

---

## 3. Executor em Background (`core/scheduler/rcon_routine_scheduler.py`)

Um serviço de segundo plano herdando de uma thread dedicada.

### Fluxo de Execução:
1. O loop roda a cada **60 segundos**.
2. Verifica se a proteção de restart está ativa usando `is_restart_active()`. Se estiver, aborta a execução do ciclo atual.
3. Carrega as rotinas ativas (`enabled == true`).
4. Para cada rotina:
   - Se `last_run` for `None` ou `current_time - last_run >= (interval_minutes * 60)`:
     - Itera sobre a lista de `commands`.
     - Envia cada comando para o `RconQueueManager.enqueue_command` com:
       * `priority = 20` (Prioridade baixa de background).
       * `delay_after = 2.0` (Espaçamento de 2 segundos entre execuções).
     - Atualiza o `last_run` para o timestamp atual e salva no arquivo.

---

## 4. Endpoints da API (`app/routes/rcon_routine_routes.py`)

Criaremos rotas HTTP expostas sob o Blueprint `/api/rcon-routines`.

### Endpoints:
* **`GET /api/rcon-routines`**: Retorna a lista de todas as rotinas.
* **`POST /api/rcon-routines`**: Adiciona uma nova rotina (valida formato dos comandos e intervalo).
* **`PUT /api/rcon-routines/<routine_id>`**: Edita uma rotina existente ou atualiza o estado `enabled`.
* **`DELETE /api/rcon-routines/<routine_id>`**: Remove a rotina.
* **`POST /api/rcon-routines/<routine_id>/test`**: **Botão de Teste**. Enfileira imediatamente todos os comandos daquela rotina específica no RCON (mesmo se estiver desativada ou fora do horário), ignorando o intervalo de tempo.

---

## 5. Integração com a Inicialização (`main.py` & `app/extensions.py`)

1. Adicionar o `rcon_routine_scheduler` e `rcon_routine_manager` ao registro de serviços em `app/extensions.py`.
2. Instanciar o `RconRoutineManager` e o `RconRoutineScheduler` dentro de `init_components()` no `main.py`.
3. Iniciar o scheduler (`scheduler.start()`) na inicialização do backend e pará-lo graciosamente (`scheduler.stop()`) no encerramento.
4. Registrar o blueprint de rotas no App Factory em `app/__init__.py`.
