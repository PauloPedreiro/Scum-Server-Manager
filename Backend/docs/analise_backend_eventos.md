# Relatório de Análise da Infraestrutura de Eventos & Requisitos de Negócio (SSM 3.0)

Este documento foi gerado para alinhar as regras de negócio desejadas para a interface do frontend com a implementação atual do backend (no arquivo `Backend/core/events/event_manager.py` e rotas do Flask), identificando se modificações no backend são necessárias ou se as regras podem ser resolvidas inteiramente no frontend.

---

## 1. Regra: Agendamento por Horário ("Hora Inicial" até "Hora Final")
**Exemplo:** Evento ativo das `14:30` às `16:00`.

### Como está no Backend atualmente:
* O backend agenda eventos baseando-se em:
  * `schedule_type`: `'daily'` (diário)
  * `schedule_value`: `'HH:MM'` (ex: `'14:30'`), que determina a hora de início.
  * `duration_minutes`: Inteiro que define a duração do evento ativo (ex: `90`).
* O loop de segundo plano (`_scheduler_loop`) inicia o evento quando o horário local atinge o `schedule_value` e o desativa quando o tempo decorrido desde o início atinge `duration_minutes`.

### Proposta de Implementação (Opção Recomendada):
Podemos implementar essa regra **100% no Frontend**, sem precisar alterar o banco de dados ou a lógica do agendador do backend:
1. O formulário do frontend exibirá os campos **Hora Inicial** (ex: `14:30`) e **Hora Final** (ex: `16:00`).
2. No momento de salvar/enviar os dados para a API:
   * **`schedule_type`** será enviado como `'daily'`.
   * **`schedule_value`** será enviado com o valor da *Hora Inicial* (ex: `'14:30'`).
   * **`duration_minutes`** será calculado no frontend através da diferença entre os dois horários (ex: de `14:30` a `16:00` = `90` minutos).
3. **Vantagem:** Evita a necessidade de realizar migrações de banco de dados no backend ou reescrever a thread do agendador.

---

## 2. Regra: Remoção do campo "Webhook URL" no cadastro de eventos

### Como está no Backend atualmente:
* A tabela `event_configs` possui o campo `webhook_url TEXT`.
* No código do `event_manager.py`, se esse valor for nulo ou vazio, o sistema automaticamente busca um webhook padrão configurado em `data/webhooks.json` sob a chave `"events"`.

### Proposta de Implementação:
1. No frontend, removemos o campo de entrada do Webhook.
2. A requisição de salvamento do evento enviará `webhook_url: null` ou omitirá o campo.
3. O backend já está preparado para tratar o valor nulo e usar o webhook global `"events"`.
4. **Vantagem:** Não requer alterações no backend. O desenvolvedor backend pode, opcionalmente, remover a coluna no futuro, mas o código atual já funciona perfeitamente sem ela.

---

## 3. Regra: Repetição de comandos com Toggle & Minutos
**Cenário:** Ao associar um comando ao evento, poder marcar se ele deve ser repetido e a cada quantos minutos.

### Como está no Backend atualmente (Repetição por Evento):
* A repetição é configurada na tabela **`event_configs`** através da coluna `recurrence_interval_minutes`.
* O loop do agendador verifica esse intervalo e, caso ele expire, executa **todos** os comandos cadastrados para aquele evento de forma sequencial.

### O que muda com a nova regra de "Repetição por Comando"?
Se o objetivo for fazer com que **cada comando individual** dentro de um mesmo evento tenha sua própria regra de repetição independente (ex: Comando A roda apenas 1 vez, Comando B repete a cada 20 minutos):

#### Modificações Necessárias no Backend:
1. **Banco de Dados:**
   * Adicionar a coluna `recurrence_interval_minutes` (INTEGER, NULLABLE) na tabela `event_startup_commands`.
   * Remover ou desconsiderar a coluna `recurrence_interval_minutes` da tabela `event_configs`.
   * Adicionar um campo para controle de última execução na tabela de comandos (ex: `last_execution_time TEXT`).
2. **Motor do Agendador (`event_manager.py`):**
   * O loop do agendador deve parar de rodar `_execute_event_commands(event_id)` em lote.
   * Em vez disso, o loop deve iterar sobre cada comando associado ao evento ativo e verificar individualmente a diferença de tempo baseada na última execução daquele comando.

> [!IMPORTANT]
> **Dúvida para o Dev Backend:** 
> A repetição deve ser **por comando individual** (exigindo as alterações de banco e loop listadas acima) ou podemos manter a **repetição global do evento** (onde ao definir a repetição na interface, ela se aplica a todos os comandos do evento simultaneamente)?

---

## Resumo dos Próximos Passos
* **Se a repetição for Global do Evento:** O backend atual já atende 100% dos requisitos. Podemos ajustar as regras apenas no formulário do Frontend.
* **Se a repetição for por Comando Individual:** O desenvolvedor do backend precisará ajustar a tabela `event_startup_commands` e a lógica do agendador em `event_manager.py` antes que possamos finalizar o layout do frontend.
