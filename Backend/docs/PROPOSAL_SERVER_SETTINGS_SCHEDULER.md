# 🔄 Proposta: Agendador Programado de Configurações do Servidor (ServerSettings.ini)

Este documento descreve a análise técnica, desafios arquiteturais e a estratégia de implementação para um sistema de troca automatizada e temporizada do arquivo de configuração do servidor SCUM (`ServerSettings.ini`).

---

## 🎯 1. Objetivo do Recurso
Permitir que administradores agendem alterações automáticas no comportamento do servidor de forma cíclica (ex: todas as terças e quintas-feiras das 18:00 às 23:30).
* **Casos de uso comuns:**
  * Modo PvP com multiplicadores de dano elevados em horários de pico.
  * Finais de semana com taxas de loot modificadas (PvE relaxado ou PvP hardcore).
  * Desativação temporária de builds/mecanismos pesados durante manutenções.

---

## ⚙️ 2. Desafios Técnicos e Soluções Propostas

Abaixo estão os 4 pilares fundamentais que determinam a viabilidade técnica do agendador:

### ⚡ Desafio A: O Ciclo de Vida do SCUM e Recarregamento de Configurações
* **Problema:** O SCUM Server (executado via `SCUMServer.exe` gerenciado pelo NSSM) **apenas lê o arquivo `ServerSettings.ini` no momento da inicialização**. Se substituirmos o arquivo com o servidor em execução, as alterações não terão efeito prático até que ocorra um restart completo.
* **Solução (Substituição sem Travamento / Hot-Swap de Configuração):** Testes práticos confirmaram que o sistema operacional **não bloqueia a gravação/escrita no arquivo `ServerSettings.ini` enquanto o servidor está rodando**. Portanto, o SSM pode alterar o arquivo a qualquer momento em segundo plano.
* **Como funciona a Transição:**
  1. No horário exato agendado para o evento (ex: 18:00), o agendador do SSM sobrescreve/edita o `ServerSettings.ini` em disco.
  2. O servidor continua rodando com a configuração anterior.
  3. No próximo restart agendado do servidor (que já é gerenciado de forma independente pelo sistema), o SCUMServer inicia carregando o novo arquivo configurado.
  4. Ao término do evento (ex: 23:30), o agendador reverte as alterações no arquivo físico em disco, e no restart correspondente das 23:30, o servidor volta para as configurações padrões.


---

### 🗂️ Desafio B: Estratégia de Modificação (Substituição Total vs. Edição de Chaves)
Temos duas alternativas para aplicar a configuração do evento:

| Estratégia | Funcionamento | Vantagens | Desvantagens |
| :--- | :--- | :--- | :--- |
| **Opção 1: Substituição Física** | Substituir o arquivo `ServerSettings.ini` inteiro por outro pré-salvo (ex: `ServerSettings_PvP.ini`). | Simples de codificar; garante 100% de previsibilidade do arquivo final. | Qualquer mudança geral que o administrador fizer na config padrão (ex: senha de admin, porta) não se propagará para as configs dos eventos, obrigando-o a atualizar manualmente todos os arquivos. |
| **Opção 2: Sobrescrita de Chaves (Recomendada)** | Manter um único arquivo mestre e aplicar apenas as diferenças (diffs) necessárias para o evento (ex: `{"World": {"scum.DamageMultiplier": "2.0"}}`). | Extremamente flexível; preserva configurações globais e atualizações do jogo automaticamente. | Exige lógica de parsing INI mais refinada e controle estrito das chaves modificadas. |

* **Decisão Arquitetural:** A **Opção 2 (Sobrescrita de Chaves)** é ideal para evitar reclamações de administradores sobre perda de configurações de rede ou senhas. No entanto, para simplicidade visual na UI do admin, ele pode criar "Templates" de configuração no painel que representam arquivos INI parciais, e o backend faz o merge inteligente no arquivo padrão.

---

### 🔄 Desafio C: Recuperação de Estado e Reconciliação (Crash Recovery)
* **Problema:** Se o backend do SSM ou o sistema operacional reiniciar inesperadamente (ex: às 20:00), o sistema precisa garantir que o arquivo esteja no estado correto.
* **Solução:** **Motor de Reconciliação Ativa**. No startup do backend, o agendador verifica a hora e dia atuais em relação à grade de eventos. Caso perceba que as chaves do arquivo físico não condizem com a rotina esperada, ele faz a atualização do arquivo imediatamente em disco. Assim, caso o servidor do jogo sofra um crash ou restart manual subsequente, ele subirá no estado correto.

### ⏰ Desafio D: Autonomia e Consciência do Administrador
* **Previsibilidade:** O administrador tem total controle sobre a grade de agendamentos. Se ele configurar a troca de arquivo para as 18:00 e o restart periódico do servidor para as 19:00, o SSM realizará a gravação em disco exatamente às 18:00, ciente de que as novas configurações só surtirão efeito a partir do próximo ciclo de reinicialização às 19:00. O backend não tentará ajustar os minutos automaticamente, mantendo a operação simples e totalmente controlada pelo usuário.

---



## 🗄️ 3. Modelo de Dados Proposto (JSON / Banco de Dados)

Podemos representar as rotinas em uma nova tabela SQLite no banco `SSM.db` (`settings_routines`) ou em um arquivo de dados dedicado `data/settings_routines.json`.

### Exemplo de Estrutura de Rotina:
```json
{
  "id": "event_pvp_ter_qui",
  "name": "Evento PvP Semanal",
  "enabled": true,
  "days_of_week": [2, 4], 
  "start_time": "18:00",
  "end_time": "23:30",
  "warning_minutes_before": 10,
  "config_overrides": {
    "General": {
      "scum.MaxPlayers": 80
    },
    "World": {
      "scum.PvpDamageMultiplier": 2.0,
      "scum.HumanToHumanDamageMultiplier": 2.0
    }
  }
}
```
* *Nota:* `days_of_week` segue padrão numérico (`0` = Segunda-feira, `6` = Domingo, ou similar).

---

## 🚀 4. Como Seria o Fluxo de Implementação (Faseado)

1. **Fase 1: Módulo de Merge de Arquivos INI (`utils/ini_helper.py`)**
   * Criar métodos para ler o `ServerSettings.ini` oficial, injetar ou alterar seções/chaves com base em um dicionário de overrides, e salvar preservando comentários/estrutura.

2. **Fase 2: Motor do Agendador de Arquivos (`core/scheduler/settings_routine_scheduler.py`)**
   * Uma thread leve em segundo plano que roda a cada 1 minuto verificando a hora atual. Ao atingir o minuto inicial/final de uma rotina, aplica a alteração no arquivo `ServerSettings.ini` diretamente em disco.


3. **Fase 3: API do Flask (`app/routes/settings_routine_routes.py`)**
   * Endpoints de CRUD (`GET`, `POST`, `PUT`, `DELETE`) para gerenciar as rotinas e os overrides de chaves.

4. **Fase 4: Tela no Frontend (UI)**
   * Uma aba intuitiva com calendário/grade de horários semanais para visualizar as rotinas ativas e um formulário para configurar as chaves que devem mudar em cada horário.
