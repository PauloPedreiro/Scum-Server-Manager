# 📋 Planejamento: Implementação do Sistema de Fila para Rankings

**Data:** 18/12/2025  
**Sistema:** SSM Backend v3.0  
**API:** Gestão v3.0 (Sistema de Fila Assíncrona)  
**Status:** ✅ Análise Completa - Pronto para Implementação

---

## 🎯 Resumo Executivo

### **O Que Mudou no Gestão**

- ✅ Endpoint `POST /api/v1/servers/sync` agora processa rankings de forma **assíncrona**
- ✅ Resposta rápida (< 2 segundos) ao invés de 10-30 segundos
- ✅ Resposta inclui `job_id` e `status="queued"` quando rankings são processados
- ✅ `rankings_created` será `null` quando processado em background
- ✅ Novo endpoint: `GET /api/v1/servers/sync/status/{job_id}` (opcional)

### **Impacto no SSM Backend**

- ✅ **Mudanças Mínimas Necessárias:** Aceitar `job_id` na resposta e não esperar `rankings_created`
- ✅ **Mudanças Opcionais:** Implementar consulta de status e polling
- ✅ **Retrocompatibilidade:** 100% compatível (sem rankings = processamento síncrono)

---

## 📊 Análise Comparativa dos Documentos

### **Documento 1: Sistema de Fila para Rankings (Completo)**
- ✅ Documentação técnica detalhada
- ✅ Exemplos de código Python
- ✅ Formato completo de resposta
- ✅ Todos os campos documentados
- ✅ Tratamento de erros detalhado
- ✅ Status possíveis: `pending`, `processing`, `completed`, `failed`, `expired`

### **Documento 2: Resumo Executivo**
- ✅ Resumo conciso
- ✅ Implementação mínima clara
- ✅ Confirma informações do Documento 1
- ✅ Checklist de implementação

### **Conclusão da Análise**

Ambos os documentos são **consistentes** e **complementares**:
- Documento 1 = Referência técnica completa
- Documento 2 = Guia rápido de implementação

**Não há contradições entre os documentos.** ✅

---

## 🔍 Análise do Código Atual

### **Arquivo: `core/communication/gestao_sync_service.py`**

#### **1. Método `_send_payload()` (Linhas 246-404)**

**Situação Atual:**
```python
if response.status_code == 200:
    response_data = response.json()
    return {"success": True, "data": response_data, "status_code": 200}
```

**Análise:**
- ✅ Já retorna `response_data` completo (inclui `job_id` e `status`)
- ⚠️ Não extrai explicitamente `job_id` e `status`
- ⚠️ Não loga `job_id` para rastreabilidade
- ✅ Compatível (não quebra, mas não aproveita novos campos)

#### **2. Método `sync_data()` (Linhas 406-577)**

**Situação Atual:**
```python
result = self._send_payload(payload)

if result.get("success"):
    if self.logger:
        size_mb = payload_size / (1024 * 1024)
        self.logger.info(f"✅ Dados sincronizados com sucesso...")
    
    return result
```

**Análise:**
- ✅ Já retorna resultado completo
- ⚠️ Não verifica se `job_id` está presente
- ⚠️ Logs não mencionam processamento assíncrono
- ⚠️ Não trata caso de `rankings_created` ser `null` (pode ser confuso)

#### **3. Método `sync_with_retry()` (Linhas 579-610)**

**Análise:**
- ✅ Não precisa de mudanças (já funciona com novo formato)
- ✅ Trata `success` corretamente

#### **4. Método `start_periodic_sync()` (Linhas 612-677)**

**Análise:**
- ✅ Não precisa de mudanças
- ✅ Já trata `success` corretamente

### **Conclusão da Análise de Código**

**Código Atual:**
- ✅ **Funciona** com novo formato (retrocompatível)
- ⚠️ **Não aproveita** novos recursos (`job_id`, `status`)
- ⚠️ **Logs não são claros** sobre processamento assíncrono
- ⚠️ **Rastreabilidade limitada** (sem `job_id` nos logs)

---

## ✅ Plano de Implementação

### **Fase 1: Implementação Mínima (Obrigatório)**

**Objetivo:** Fazer o SSM Backend funcionar corretamente com o novo sistema de fila.

#### **Tarefa 1.1: Atualizar `_send_payload()`**

**Localização:** `core/communication/gestao_sync_service.py`, linha ~264

**Mudanças:**
```python
if response.status_code == 200:
    try:
        response_data = response.json()
        
        # NOVO: Extrair job_id e status
        job_id = response_data.get("job_id")
        status = response_data.get("status")
        rankings_created = response_data.get("rankings_created")
        
        # NOVO: Logar job_id se presente
        if job_id:
            if self.logger:
                self.logger.info(
                    f"📋 Job criado: {job_id} (status: {status}). "
                    f"Rankings sendo processados em background."
                )
        
    except (ValueError, AttributeError) as e:
        # ... código existente ...
    
    return {
        "success": True,
        "data": response_data,
        "status_code": 200,
        "job_id": job_id,  # NOVO
        "status": status   # NOVO
    }
```

**Critérios de Aceitação:**
- [ ] `job_id` extraído e retornado no resultado
- [ ] `status` extraído e retornado no resultado
- [ ] Log criado quando `job_id` presente
- [ ] Código existente continua funcionando

#### **Tarefa 1.2: Atualizar `sync_data()`**

**Localização:** `core/communication/gestao_sync_service.py`, linha ~557

**Mudanças:**
```python
# Após result = self._send_payload(payload)

if result.get("success"):
    job_id = result.get("job_id")
    response_data = result.get("data", {})
    rankings_created = response_data.get("rankings_created")
    
    if job_id:
        # Processado em background
        if self.logger:
            size_mb = payload_size / (1024 * 1024)
            self.logger.info(
                f"✅ Dados recebidos pelo Gestão. "
                f"Rankings sendo processados em background "
                f"(job_id: {job_id}, {size_mb:.2f} MB, {len(rankings_players)} players)"
            )
    else:
        # Processado síncrono (sem rankings)
        if self.logger:
            size_mb = payload_size / (1024 * 1024)
            self.logger.info(
                f"✅ Dados sincronizados com sucesso com Gestão "
                f"({size_mb:.2f} MB, {len(rankings_players)} players"
            )
            if rankings_created is not None:
                self.logger.info(f", {rankings_created} rankings criados)")
            else:
                self.logger.info(")")
    
    return result
```

**Critérios de Aceitação:**
- [ ] Detecta quando `job_id` está presente
- [ ] Logs diferentes para processamento assíncrono vs síncrono
- [ ] Não considera erro quando `rankings_created` é `null` e `job_id` presente
- [ ] Funciona tanto com rankings (assíncrono) quanto sem (síncrono)

#### **Tarefa 1.3: Atualizar Processamento de Lotes**

**Localização:** `core/communication/gestao_sync_service.py`, linha ~520

**Mudanças:**
```python
# Após enviar cada lote
result = self._send_payload(batch_payload)

# Se algum lote falhou, retornar erro
if not result.get("success"):
    # ... código existente ...
    return result

# NOVO: Logar job_id se presente
job_id = result.get("job_id")
if job_id:
    if self.logger:
        self.logger.info(f"📋 Lote {batch_idx}/{len(batches)} - Job criado: {job_id}")
```

**Critérios de Aceitação:**
- [ ] Logs incluem `job_id` para cada lote
- [ ] Comportamento de lotes não muda (continua funcionando)

---

### **Fase 2: Funcionalidades Opcionais (Recomendado)**

**Objetivo:** Melhorar rastreabilidade e capacidade de diagnóstico.

#### **Tarefa 2.1: Implementar `check_job_status()`**

**Localização:** `core/communication/gestao_sync_service.py`, novo método

**Implementação:**
```python
def check_job_status(self, job_id: int) -> Dict[str, Any]:
    """
    Consultar status de um job
    
    Args:
        job_id: ID do job retornado pelo Gestão
        
    Returns:
        Dados do status do job ou erro
    """
    if not HAS_REQUESTS:
        return {
            "success": False,
            "error": "Biblioteca 'requests' não disponível"
        }
    
    try:
        response = requests.get(
            f"{self.gestao_url}/api/v1/servers/sync/status/{job_id}",
            timeout=self.handshake_timeout,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json()
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": f"Job {job_id} não encontrado",
                "status_code": 404
            }
        else:
            return {
                "success": False,
                "error": f"Erro ao consultar status: {response.status_code}",
                "status_code": response.status_code
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

**Critérios de Aceitação:**
- [ ] Método implementado corretamente
- [ ] Trata erro 404 (job não encontrado)
- [ ] Trata erros de conexão/timeout
- [ ] Retorna dados do job quando encontrado

#### **Tarefa 2.2: Armazenar `job_id` Localmente (Opcional)**

**Localização:** Novo arquivo ou adicionar ao `sync_data()`

**Implementação:**
```python
# Salvar job_id em arquivo JSON para rastreabilidade
def _save_job_id(self, job_id: int, server_hash: str, timestamp: str):
    """
    Salvar job_id para rastreabilidade
    
    Args:
        job_id: ID do job
        server_hash: Hash do servidor
        timestamp: Timestamp da sincronização
    """
    try:
        jobs_file = self.path_helper.get_data_dir() / "gestao_jobs.json"
        
        # Carregar jobs existentes
        if jobs_file.exists():
            with open(jobs_file, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
        else:
            jobs = []
        
        # Adicionar novo job
        jobs.append({
            "job_id": job_id,
            "server_hash": server_hash,
            "timestamp": timestamp,
            "status": "queued"
        })
        
        # Manter apenas últimos 100 jobs
        if len(jobs) > 100:
            jobs = jobs[-100:]
        
        # Salvar
        with open(jobs_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        if self.logger:
            self.logger.warn(f"Erro ao salvar job_id: {e}")
```

**Critérios de Aceitação:**
- [ ] `job_id` salvo em arquivo JSON
- [ ] Arquivo mantém histórico (últimos 100 jobs)
- [ ] Não quebra se não conseguir salvar (apenas loga aviso)

#### **Tarefa 2.3: Implementar `wait_for_job_completion()` (Opcional)**

**Localização:** `core/communication/gestao_sync_service.py`, novo método

**Implementação:**
```python
def wait_for_job_completion(
    self,
    job_id: int,
    max_wait: int = 300,
    check_interval: int = 5
) -> Dict[str, Any]:
    """
    Aguardar job ser processado
    
    Args:
        job_id: ID do job
        max_wait: Tempo máximo de espera (segundos)
        check_interval: Intervalo entre verificações (segundos)
        
    Returns:
        Resultado final do job
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if not self.running:  # Se parou de rodar, sair
            return {
                "success": False,
                "error": "Sincronização interrompida"
            }
        
        # Consultar status
        result = self.check_job_status(job_id)
        
        if not result.get("success"):
            return result
        
        status_data = result.get("data", {})
        status = status_data.get("status")
        
        if status == "completed":
            if self.logger:
                self.logger.info(f"✅ Job {job_id} processado com sucesso")
            return {
                "success": True,
                "data": status_data
            }
        elif status == "failed":
            error_msg = status_data.get("error_message", "Erro desconhecido")
            if self.logger:
                self.logger.error(f"❌ Job {job_id} falhou: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "data": status_data
            }
        elif status == "expired":
            if self.logger:
                self.logger.warn(f"⚠️ Job {job_id} expirado")
            return {
                "success": False,
                "error": "Job expirado",
                "data": status_data
            }
        
        # Ainda processando (pending ou processing)
        if self.logger:
            attempts = status_data.get("attempts", 0)
            max_attempts = status_data.get("max_attempts", 3)
            self.logger.debug(
                f"⏳ Job {job_id} status: {status} "
                f"(tentativa {attempts}/{max_attempts})"
            )
        
        time.sleep(check_interval)
    
    # Timeout
    if self.logger:
        self.logger.warn(f"⏱️ Timeout aguardando job {job_id}")
    return {
        "success": False,
        "error": f"Timeout aguardando processamento (max: {max_wait}s)"
    }
```

**Critérios de Aceitação:**
- [ ] Aguarda até job completar ou falhar
- [ ] Respeita `max_wait` (timeout)
- [ ] Respeita `check_interval` entre verificações
- [ ] Retorna resultado apropriado para cada status

---

### **Fase 3: Melhorias e Refinamentos (Opcional)**

#### **Tarefa 3.1: Integrar Polling em `sync_data()` (Opcional)**

**Objetivo:** Adicionar opção de aguardar processamento após enviar dados.

**Implementação:**
```python
# Adicionar parâmetro opcional
def sync_data(self, wait_for_completion: bool = False) -> Dict[str, Any]:
    # ... código existente ...
    
    if result.get("success"):
        job_id = result.get("job_id")
        
        if job_id and wait_for_completion:
            # Aguardar processamento
            wait_result = self.wait_for_job_completion(job_id)
            
            if wait_result.get("success"):
                # Job completado com sucesso
                result["job_completed"] = True
                result["job_result"] = wait_result
            else:
                # Job falhou ou expirou
                result["job_completed"] = False
                result["job_error"] = wait_result.get("error")
        
        return result
```

#### **Tarefa 3.2: Dashboard de Jobs (Opcional)**

**Objetivo:** Permitir visualizar status de jobs na GUI.

**Implementação:**
- Adicionar método `get_recent_jobs()` para listar últimos jobs
- Adicionar endpoint na API interna (se houver)
- Mostrar na GUI (se necessário)

---

## 🧪 Plano de Testes

### **Teste 1: Envio com Rankings (Assíncrono)**

**Objetivo:** Verificar que sistema funciona com novo formato assíncrono.

**Passos:**
1. Executar sincronização com rankings
2. Verificar resposta contém `job_id`
3. Verificar `rankings_created` é `null`
4. Verificar `status` é `"queued"`
5. Verificar logs contêm `job_id`

**Resultado Esperado:**
```python
{
    "success": True,
    "job_id": 456,
    "status": "queued",
    "data": {
        "rankings_created": None,
        "players_synced": 532,
        ...
    }
}
```

**Log Esperado:**
```
📋 Job criado: 456 (status: queued). Rankings sendo processados em background.
✅ Dados recebidos pelo Gestão. Rankings sendo processados em background (job_id: 456, 0.66 MB, 532 players)
```

### **Teste 2: Envio sem Rankings (Síncrono - Retrocompatibilidade)**

**Objetivo:** Verificar que sistema mantém comportamento anterior.

**Passos:**
1. Executar sincronização sem rankings
2. Verificar resposta não contém `job_id` (ou é `null`)
3. Verificar `rankings_created` tem valor (ou é `None` se não aplicável)
4. Verificar logs não mencionam "background"

**Resultado Esperado:**
```python
{
    "success": True,
    "job_id": None,
    "data": {
        "rankings_created": 0,  # ou None
        "players_synced": 532,
        ...
    }
}
```

### **Teste 3: Consulta de Status (Opcional)**

**Objetivo:** Verificar que consulta de status funciona.

**Passos:**
1. Obter `job_id` de uma sincronização
2. Consultar status via `check_job_status(job_id)`
3. Verificar resposta contém `status`, `attempts`, etc.
4. Aguardar processamento e verificar `status="completed"`

**Resultado Esperado:**
```python
{
    "success": True,
    "data": {
        "job_id": 456,
        "status": "completed",
        "attempts": 1,
        "max_attempts": 3,
        ...
    }
}
```

### **Teste 4: Processamento de Lotes**

**Objetivo:** Verificar que sistema de lotes funciona com `job_id`.

**Passos:**
1. Enviar dados que excedem 5MB (será dividido em lotes)
2. Verificar cada lote recebe `job_id`
3. Verificar logs incluem `job_id` para cada lote

**Resultado Esperado:**
```
📋 Lote 1/3 - Job criado: 456
📋 Lote 2/3 - Job criado: 457
📋 Lote 3/3 - Job criado: 458
✅ Todos os 3 lotes sincronizados com sucesso
```

### **Teste 5: Tratamento de Erros**

**Objetivo:** Verificar que erros são tratados corretamente.

**Cenários:**
- Job não encontrado (404)
- Job falhado (`status="failed"`)
- Job expirado (`status="expired"`)
- Timeout na consulta de status

---

## 📝 Checklist de Implementação

### **Fase 1: Obrigatório**

- [ ] **1.1** Atualizar `_send_payload()` para extrair e retornar `job_id` e `status`
- [ ] **1.2** Adicionar logs quando `job_id` presente em `_send_payload()`
- [ ] **1.3** Atualizar `sync_data()` para detectar processamento assíncrono
- [ ] **1.4** Atualizar logs em `sync_data()` para mencionar "background" quando aplicável
- [ ] **1.5** Atualizar processamento de lotes para logar `job_id`

### **Fase 2: Recomendado**

- [ ] **2.1** Implementar `check_job_status()`
- [ ] **2.2** Testar consulta de status com job válido
- [ ] **2.3** Testar consulta de status com job inválido (404)
- [ ] **2.4** (Opcional) Implementar `_save_job_id()` para rastreabilidade
- [ ] **2.5** (Opcional) Implementar `wait_for_job_completion()`

### **Fase 3: Opcional**

- [ ] **3.1** (Opcional) Integrar polling em `sync_data()`
- [ ] **3.2** (Opcional) Implementar dashboard de jobs

### **Testes**

- [ ] **T1** Teste de envio com rankings (assíncrono)
- [ ] **T2** Teste de envio sem rankings (síncrono)
- [ ] **T3** Teste de consulta de status
- [ ] **T4** Teste de processamento de lotes
- [ ] **T5** Teste de tratamento de erros

---

## ⚠️ Pontos de Atenção

### **1. Retrocompatibilidade**

- ✅ **Importante:** Sistema deve funcionar tanto com rankings (assíncrono) quanto sem (síncrono)
- ✅ Verificar que código funciona em ambos os cenários
- ✅ Não assumir que `job_id` sempre existe

### **2. Timeout**

- ✅ Resposta do Gestão agora é rápida (< 2s), mas manter timeout atual (30s) para segurança
- ✅ Timeout de consulta de status pode ser menor (5s)

### **3. Logs**

- ✅ Logs devem ser claros sobre processamento assíncrono
- ✅ Incluir `job_id` nos logs para rastreabilidade
- ✅ Não mencionar "background" quando processado síncrono

### **4. Tratamento de `rankings_created`**

- ✅ **Não considerar erro** quando `rankings_created` é `null` e `job_id` presente
- ✅ Isso é comportamento esperado no novo sistema
- ✅ Processamento síncrono (sem rankings) ainda retorna `rankings_created` (ou `None`)

---

## 🎯 Ordem de Implementação Recomendada

1. ✅ **Fase 1** (Obrigatório) - Implementação mínima
   - Tarefas 1.1, 1.2, 1.3
   - Testes T1, T2, T4

2. ✅ **Fase 2** (Recomendado) - Funcionalidades opcionais
   - Tarefa 2.1 (consulta de status)
   - Teste T3

3. ✅ **Fase 3** (Opcional) - Melhorias
   - Apenas se necessário

---

## 📚 Referências

- **Documento 1:** Sistema de Fila para Rankings (Completo)
- **Documento 2:** Resumo Executivo
- **Código Atual:** `core/communication/gestao_sync_service.py`
- **Análise:** `docs/ANALISE_SISTEMA_FILA_RANKINGS.md`

---

## ✅ Conclusão

O planejamento está **completo** e **pronto para implementação**. 

**Implementação mínima (Fase 1)** é **simples** e **não invasiva**, garantindo que o sistema funcione corretamente com o novo formato de fila assíncrona.

**Funcionalidades opcionais (Fase 2)** melhoram rastreabilidade e diagnóstico, mas não são obrigatórias para funcionamento básico.

**Status:** ✅ Pronto para iniciar implementação

---

**Última Atualização:** 18/12/2025  
**Versão do Planejamento:** 1.0  
**Próximo Passo:** Implementar Fase 1 (Obrigatório)

