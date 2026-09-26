# Handoff (SSM): SCUM Base Upgrade/Downgrade via SCUM.db + Template DB

## 1) Objetivo
Permitir que administradores alterem o **nível de material** de todos os elementos de construção de uma base do SCUM (fundação, parede, escada, telhado etc.) de forma **segura**, usando um banco de dados auxiliar (`scum_base_template.db`) como **fonte da verdade** (whitelist + mapeamento por família/nível).

- Níveis suportados:
  - **1** = Twig
  - **2** = Wood
  - **3** = Metal
  - **4** = Brick
  - **5** = Cement

Requisito central: **não adivinhar strings de asset**. Só trocar assets se existir mapeamento explícito no template.

---

## 2) O que enviar (artefatos)
### Arquivos
- `tools/build_scum_base_template.py`
  - Gera o template DB pela primeira vez (a partir de uma base/flag).
- `tools/enrich_scum_base_template.py`
  - Enriquece o template DB incrementalmente (adiciona famílias/assets novos sem apagar dados existentes).
- `tools/set_base_level_from_template.py`
  - Calcula mudanças (dry-run) e aplica updates (apply) no `SCUM.db` com backup, transação e relatório.
- `tools/add_family_level_wide_view.py`
  - Cria VIEWs e tabelas “wide” (colunas `level_1..level_5`) para auditoria do template.
- `tools/scum_base_template.db`
  - Banco SQLite com whitelist e crosswalk (família + nível -> asset).

### (Opcional, recomendado)
- Relatórios JSON de exemplo:
  - 1 relatório de **dry-run**
  - 1 relatório de **apply**
  - 1 relatório de **postcheck** idempotente (`to_change=0`)

---

## 3) Modelo de dados (o que o SSM precisa respeitar)

### 3.1) No `SCUM.db`
Tabela relevante:
- `base_element`
  - Colunas utilizadas:
    - `element_id` (PK)
    - `base_id` (identifica a base)
    - `asset` (string do blueprint/class)

Observação: o sistema resolve `base_id` a partir do `element_id` do flag, quando o operador fornece `--flag-id`.

### 3.2) No `scum_base_template.db`
Tabelas relevantes:
- `asset_whitelist`
  - Mapeia `asset` -> `family_key`
- `family_level_asset`
  - Mapeia `(family_key, level)` -> `asset`

Conceito:
- **family_key** representa a “família” do elemento (ex.: `BPC_Base_Modular_Foundation`).
- Nem toda família tem todos os níveis. Ex.: existem famílias cujo **mínimo é Wood (2)**, ou até **Metal (3)**.

---

## 4) Fluxos de operação (visão para integrar no SSM)

### 4.1) Build template (primeira carga)
Objetivo: criar a base inicial do template (whitelist + mapeamentos) usando uma base/flag conhecida.

Resultado esperado:
- O template passa a “conhecer” famílias/níveis/asset para os elementos presentes naquela base.

### 4.2) Enrich template (incremental)
Objetivo: adicionar famílias/assets novos ao template sem perder dados anteriores.

Uso típico:
- Após identificar `not_whitelisted`/`no_mapping` em alguma base alvo.
- Após construir/encontrar outra base com outros tipos/níveis de peças.

### 4.3) Set base level (dry-run / apply)
Objetivo: ajustar o material de todos os elementos sob uma base para um nível alvo.

Entradas mínimas:
- `scum_db_path`: caminho do `SCUM.db` **real do servidor**
- `template_db_path`
- `flag_id` **ou** `base_id`
- `target_level` (1..5)
- `fallback_lowest` (recomendado como padrão ON)

Saídas:
- Estatísticas (contagens)
- Relatório (JSON recomendado)

---

## 4.4) Contrato para integração no SSM (inputs/outputs)

### Inputs (validações)
- `scum_db_path` (string)
  - Obrigatório.
  - Deve ser **caminho absoluto** para o arquivo `SCUM.db` do servidor.
  - O SSM não deve assumir um caminho default silencioso.
- `template_db_path` (string)
  - Obrigatório.
  - Caminho para `scum_base_template.db`.
- Identificador da base:
  - `flag_id` (int) **ou** `base_id` (int).
  - Exigir exatamente um (ou aceitar ambos e priorizar `base_id`, mas documentar).
- `target_level` (int)
  - Obrigatório, range **1..5**.
- `fallback_lowest` (bool)
  - Recomendado como default **true**.
- `mode` (enum)
  - `dry_run` ou `apply`.
- `report` (configuração)
  - No mínimo: persistir o payload em log/auditoria do SSM.
  - Opcional: gerar arquivo `.json` com path informado/gerado.

### Output (payload recomendado)
- `base_id` resolvido
- `target_level`
- `mode`
- `result`
  - `dry_run`, `updated`, `no_changes`, `error`
- `stats`
  - `total`, `not_whitelisted`, `no_family`, `no_mapping`, `fallback_lowest_used`, `already_target`, `to_change`
- `backup_path` (somente quando `apply` e houve mudanças)
- `updated_rows` (somente quando `apply`)
- `report_ref`
  - Referência do log/auditoria, ou path do report, ou id interno do job.

---

## 5) Modo DRY-RUN (simulação)
Objetivo: calcular mudanças sem escrever no `SCUM.db`.

Contagens importantes:
- `total`: total de elementos analisados na base
- `not_whitelisted`: assets do SCUM.db que não estão na whitelist do template
- `no_family`: asset está whitelisted mas sem `family_key`
- `no_mapping`: existe `family_key` mas falta mapeamento para o nível alvo (e não houve fallback)
- `fallback_lowest_used`: quantos casos precisaram cair para o menor nível disponível
- `already_target`: quantos já estavam no asset resolvido
- `to_change`: quantos updates seriam aplicados

Relatório:
- Deve ser gravado em arquivo (JSON recomendado) para auditoria/troubleshooting.

---

## 6) Modo APPLY (aplicação)
Regras operacionais:
- Se `to_change == 0`:
  - **não criar backup**
  - **não executar UPDATE**
  - registrar resultado como “no changes”
- Se `to_change > 0`:
  - criar backup do `SCUM.db`
  - aplicar updates dentro de transação
  - registrar relatório com `backup_path` e contagens

Observação operacional:
- Ideal aplicar durante janela de manutenção (reduz risco de concorrência com o servidor escrevendo o save).

---

## 6.1) Concorrência / locking
- O `SCUM.db` pode ser alterado pelo servidor durante saves.
- Recomendação: o SSM deve tratar a operação como **job exclusivo** por servidor/save.
- Se possível, executar durante manutenção (servidor parado) ou garantir que não exista outro processo escrevendo o mesmo `SCUM.db`.

---

## 7) Regras de segurança / invariantes
- **Nada de replace por string** (não confiar em “existe um `...Twig_C` no jogo”).
- **Template manda**: se não existe `(family_key, level)` no template, não aplicar.
- **Normalização de asset**: `strip()` para evitar caracteres invisíveis e mismatch.
- **Excluir a própria Flag**: não converter o elemento da bandeira.
- **Idempotência**: rodar de novo deve resultar em `to_change = 0`.
- **Relatórios**: guardar JSON ajuda muito suporte/admin.

Regra importante (Modular / BP vs BPC):
- Em várias famílias do SCUM, especialmente `BaseElements/Modular`, o Twig aparece como `BP_..._Twig`, enquanto Wood/Metal/Brick/Cement aparecem como `BPC_..._(Wood|Metal|Brick|Cement)`.
- Portanto, ao resolver `(family_key, target_level)`, é necessário tentar a variante de prefixo `BP_ <-> BPC_` quando não existir mapping direto.

### 7.1) Fallback `fallback_lowest`
Comportamento:
- Se não existir mapeamento para o nível alvo, cai para o **menor nível disponível** daquela família.

Motivo:
- Permite downgrade/ajustes amplos sem “inventar asset”, mantendo segurança.

---

## 7.2) Ciclo de vida do template (ponto crítico)
- O template (`scum_base_template.db`) é **stateful** e deve ser tratado como base de conhecimento.
- Quando aparecerem casos `not_whitelisted` ou `no_mapping` no dry-run:
  - O fluxo correto é enriquecer o template (enrich) a partir de uma base/flag que contenha os assets faltantes.
  - Reexecutar dry-run.
  - Só então aplicar.
- Não tentar “resolver” `no_mapping` inventando assets.

---

## 8) Checklist de validação (para o dev)
Antes de entregar:
- Rodar dry-run e confirmar que as contagens fazem sentido.
- Rodar apply e verificar:
  - backup foi criado quando `to_change > 0`
  - `updated_rows` condiz com o número de mudanças
- Rodar postcheck e confirmar:
  - `to_change = 0`

Validação objetiva (exemplo):
- Consultar `base_element` por alguns `element_id` e verificar o `asset` antes/depois.

---

## 8.1) Cenários de uso (exemplos)

### Cenário A: Forçar uma base para Metal (nível 3)
- Operador informa `flag_id` (ou `base_id`) e `target_level=3`.
- Rodar `dry_run` e verificar `to_change`.
- Rodar `apply`.
- Rodar postcheck e confirmar `to_change=0`.

### Cenário B: Downgrade “para o mínimo possível” (Twig com fallback)
- Operador informa `target_level=1` e `fallback_lowest=true`.
- Resultado esperado:
  - Famílias que possuem Twig irão para Twig.
  - Famílias sem Twig cairão para o menor nível existente (muitas vezes Wood).

### Cenário C: Base já está no alvo (idempotência)
- `dry_run` deve retornar `to_change=0`.
- `apply` deve retornar `no_changes` e **não criar backup**.

---

## 9) Parâmetros que o SSM deve expor (UI ou comando)
Mesmo se a integração for via painel ou chat-command, os parâmetros essenciais são os mesmos:
- Caminho do `SCUM.db`
- Identificador da base:
  - `flag_id` (element_id do flag) **ou** `base_id`
- Nível alvo (1..5)
- `fallback_lowest` (default ON)
- `dry-run` vs `apply`
- caminho/nome do report (ou equivalente em log/auditoria do SSM)

---

## 10) Observações práticas
- Nem todas as famílias possuem Twig (nível 1). Ex.: várias famílias têm `min_level = 2` (Wood) ou `min_level = 3` (Metal).
- Para descobrir limites reais do template, consultar `family_level_asset` (ex.: `MIN(level)` por `family_key`).

Auditoria do template (formato “wide”):
- Para visualizar a cobertura do template (por família, com colunas de nível), gerar as views/tabelas wide no `scum_base_template.db`.
- Isso ajuda a identificar rapidamente quais famílias não possuem nível 4/5, quais começam em nível 2/3 etc.

Testes executados (resultado):
- Upgrade/downgrade em base pequena isolada, com `dry_run`, `apply` e `postcheck` (idempotência).
- Destruição de flag e base, criação de uma nova base em outro local, e repetição do ciclo de mudança de nível.
- Resultado: comportamento consistente, backup automático no apply e convergência para `to_change=0` no postcheck.

---

## 11) Contato / notas de implementação
- Integração sugerida no SSM: executar como “job” backend (fila/worker), registrando auditoria e resultado.
- O mesmo motor serve tanto para disparo via painel quanto via comando de chat.
