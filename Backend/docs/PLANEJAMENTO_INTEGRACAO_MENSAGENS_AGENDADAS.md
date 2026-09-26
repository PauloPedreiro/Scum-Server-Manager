# 📋 Planejamento: Integração de Mensagens Agendadas do Gestão

## 📌 Visão Geral

Implementar integração para consultar mensagens agendadas do **Gestão** antes de cada restart agendado do servidor SCUM, exibindo essas mensagens junto com as mensagens padrão de restart no jogo.

---

## 🎯 Objetivo

Consultar o endpoint `GET /api/v1/servers/messages` do Gestão **5-10 minutos antes** de cada restart agendado para obter mensagens de propaganda/anúncios que serão incluídas nas notificações de restart in-game.

---

## 🔍 Análise do Código Atual

### **Pontos de Integração Identificados:**

1. **`core/scheduler/restart_scheduler.py`**
   - Método `_create_restart_notifications()` (linha 62-107)
   - Cria notificações de restart 12 minutos antes
   - Delega para `NotificationManager.create_restart_notifications()`

2. **`core/notifications/notification_manager.py`**
   - Método `create_restart_notifications()` (linha 809-881)
   - Carrega template de `data/notifications/templates/restart.json`
   - Cria notificações com mensagens padrão
   - Salva via `SCUMNotifier.save_notifications()`

3. **`core/communication/gestao_sync_service.py`**
   - Já tem integração com Gestão
   - Usa `api_key` de `licensing.gestao_api_key`
   - URL do Gestão em `core/config/server_urls.py` (GESTAO_SERVER_URL)
   - Padrão de tratamento de erros estabelecido

4. **`data/notifications/templates/restart.json`**
   - Template atual com mensagens padrão (10min, 5min, 4min, 3min, 2min, 1min)
   - Mensagens formatadas: `"⚠️ SERVER RESTART IN X MINUTES! | #NumPlayers players online"`

---

## 📐 Arquitetura da Solução

### **Fluxo Proposto:**

```
1. RestartScheduler detecta restart agendado em ~15 minutos
   ↓
2. Consulta GestãoMessagesService para obter mensagem agendada
   ↓
3. GestãoMessagesService faz GET /api/v1/servers/messages?api_key=...
   ↓
4. Se retornar mensagem (não null), armazena temporariamente
   ↓
5. NotificationManager.create_restart_notifications() recebe mensagem do Gestão
   ↓
6. Cria notificação separada para 8 minutos antes (se mensagem existir)
   ↓
7. Salva todas as notificações (padrão + Gestão) via SCUMNotifier
   ↓
8. Estrutura final: 10min, 8min (Gestão), 5min, 4min, 3min, 2min, 1min
```

### **Estrutura de Notificações no Notifications.json:**

```json
{
  "Notifications": [
    {
      "time": ["20:50"],  // 10 minutos antes
      "message": "⚠️ SERVER RESTART IN 10 MINUTES! | #NumPlayers players online"
    },
    {
      "time": ["20:52"],  // 8 minutos antes - MENSAGEM DO GESTÃO (se existir)
      "message": "Mensagem do Gestão aqui"
    },
    {
      "time": ["20:55"],  // 5 minutos antes
      "message": "⚠️ SERVER RESTART IN 5 MINUTES! | #NumPlayers players online"
    },
    // ... resto das notificações padrão (4min, 3min, 2min, 1min)
  ]
}
```

---

## 🏗️ Componentes a Criar/Modificar

### **1. Novo Serviço: `core/communication/gestao_messages_service.py`**

**Responsabilidade:**
- Consultar endpoint `/api/v1/servers/messages` do Gestão
- Implementar cache de 5 minutos
- Tratar erros graciosamente (nunca interromper restart)
- Retornar `Optional[str]` (mensagem ou None)

**Métodos:**
```python
class GestaoMessagesService:
    def __init__(self, config, logger)
    def get_scheduled_message(self, api_key: str) -> Optional[str]
    def _fetch_message_from_gestao(self, api_key: str) -> Optional[str]
    def _is_cache_valid(self) -> bool
```

**Características:**
- ✅ Timeout de 5 segundos
- ✅ Cache de 5 minutos (evitar consultas excessivas)
- ✅ Tratamento de erros silencioso (apenas log)
- ✅ Não lança exceções (retorna None em caso de erro)
- ✅ Usa mesma URL do Gestão que `GestaoSyncService`

---

### **2. Modificar: `core/notifications/notification_manager.py`**

**Mudanças:**
- Adicionar parâmetro opcional `gestao_message: Optional[str]` em `create_restart_notifications()`
- **Criar notificação separada para 8 minutos antes** (se mensagem existir)
- Ordenar todas as notificações por horário antes de salvar

**Lógica de Inclusão:**
```python
# No método create_restart_notifications()
if gestao_message:
    # Calcular horário para 8 minutos antes do restart
    notification_time_8min = restart_datetime - timedelta(minutes=8)
    
    # Criar notificação separada para mensagem do Gestão
    gestao_notification = {
        "day": "Everyday",
        "time": [notification_time_8min.strftime("%H:%M")],
        "duration": 10,  # Mesma duração das outras
        "color": "255-180-50",  # Mesma cor das outras (ou diferente se desejado)
        "message": gestao_message  # Mensagem pura do Gestão
    }
    
    # Inserir na lista de notificações (entre 10min e 5min)
    # Ordenar por horário para manter ordem correta
```

---

### **3. Modificar: `core/scheduler/restart_scheduler.py`**

**Mudanças:**
- Importar `GestaoMessagesService`
- Instanciar serviço no `__init__` (ou receber via dependency injection)
- No método `_create_restart_notifications()`:
  1. Calcular tempo até restart
  2. Se ~15 minutos antes (entre 14-16 minutos), consultar `GestaoMessagesService`
  3. Passar mensagem obtida para `NotificationManager.create_restart_notifications()`

**Integração:**
```python
# No _create_restart_notifications()
time_until_restart = (restart_datetime - datetime.now()).total_seconds()

# EXPANDIR janela de 12 minutos para 16 minutos (para permitir consulta 15 min antes)
# Atual: if 0 < time_until_restart < 720:  # 12 minutos
# Novo: if 0 < time_until_restart < 960:   # 16 minutos

# Consultar Gestão se estiver entre 14-16 minutos antes (janela para garantir consulta)
gestao_message = None
if 840 <= time_until_restart <= 960:  # Entre 14 e 16 minutos (janela de segurança)
    if self.gestao_messages_service:
        # Obter API key do config
        licensing_config = self.config.get('licensing', {})
        api_key_raw = licensing_config.get('gestao_api_key', '')
        
        # Descriptografar se necessário (mesma lógica de GestaoSyncService)
        if api_key_raw.startswith('ENCRYPTED:'):
            from core.security.credential_encryption import decrypt_credential
            api_key = decrypt_credential(api_key_raw, logger=self.logger)
        else:
            api_key = api_key_raw
        
        if api_key:
            gestao_message = self.gestao_messages_service.get_scheduled_message(api_key)
            if gestao_message:
                self.logger.info(f"Mensagem do Gestão obtida: {gestao_message[:50]}...")
            else:
                self.logger.debug("Nenhuma mensagem ativa do Gestão encontrada")
        else:
            self.logger.warn("API key não configurada - não foi possível consultar mensagens do Gestão")

# Passar para NotificationManager (mesmo que seja None)
result = self.notification_manager.create_restart_notifications(
    restart_time, restart_datetime, gestao_message=gestao_message
)
```

**MUDANÇA NECESSÁRIA:** Expandir janela de tempo em `_create_restart_notifications()`
- **Antes:** `if 0 < time_until_restart < 720:` (12 minutos)
- **Depois:** `if 0 < time_until_restart < 960:` (16 minutos)

---

### **4. Modificar: `main.py`**

**Mudanças:**
- Instanciar `GestaoMessagesService` na função `init_components()`
- Passar para `RestartScheduler` via `__init__` ou setter
- Garantir que `api_key` esteja disponível (mesma lógica de `GestaoSyncService`)

---

## 📝 Detalhamento da Implementação

### **Fase 1: Criar GestaoMessagesService**

**Arquivo:** `core/communication/gestao_messages_service.py`

**Estrutura:**
```python
class GestaoMessagesService:
    def __init__(self, config, logger):
        - Obter URL do Gestão (usar GESTAO_SERVER_URL)
        - Inicializar cache (dict com timestamp + message)
        - Configurar timeout (5s)
    
    def get_scheduled_message(self, api_key: str) -> Optional[str]:
        - Verificar cache válido
        - Se válido, retornar cache
        - Se inválido ou não existe, consultar Gestão
        - Atualizar cache
        - Retornar mensagem ou None
    
    def _fetch_message_from_gestao(self, api_key: str) -> Optional[str]:
        - Fazer GET /api/v1/servers/messages?api_key=...
        - Tratar timeout/erros silenciosamente
        - Retornar data["message"] ou None
```

**Tratamento de Erros:**
- ✅ Timeout → None (log warning)
- ✅ 400/404 → None (log warning)
- ✅ 500 → None (log error)
- ✅ ConnectionError → None (log warning)
- ✅ JSON decode error → None (log error)
- ✅ Qualquer exceção → None (log error)

---

### **Fase 2: Modificar NotificationManager**

**Arquivo:** `core/notifications/notification_manager.py`

**Mudança no método:**
```python
def create_restart_notifications(
    self, 
    restart_time: str, 
    restart_datetime: datetime,
    gestao_message: Optional[str] = None  # NOVO PARÂMETRO
) -> Dict[str, Any]:
```

**Lógica de inclusão:**
1. Carregar template de restart (notificações padrão: 10min, 5min, 4min, 3min, 2min, 1min)
2. Criar todas as notificações padrão baseadas no template
3. **Se `gestao_message` existe:**
   - Calcular horário para 8 minutos antes: `notification_time_8min = restart_datetime - timedelta(minutes=8)`
   - Criar notificação separada:
     ```python
     gestao_notification = {
         "day": "Everyday",
         "time": [notification_time_8min.strftime("%H:%M")],
         "duration": 10,  # Mesma duração das outras
         "color": "255-180-50",  # Mesma cor das outras (pode ser personalizado depois)
         "message": gestao_message  # Mensagem pura do Gestão
     }
     ```
   - Adicionar à lista de notificações
4. Combinar lista: notificações padrão + notificação do Gestão (se existir)
5. **Ordenar todas por horário** (importante para garantir ordem correta no Notifications.json)
   ```python
   all_notifications.sort(key=lambda n: n["time"][0])  # Ordenar pelo primeiro horário
   ```
6. Salvar via SCUMNotifier.save_notifications()

**Exemplo de resultado ordenado:**
```
13:50 - "⚠️ SERVER RESTART IN 10 MINUTES! | #NumPlayers players online"
13:52 - "Enquanto o Servidor reinicia, peça um ifood cupom 545asdff"  (Gestão)
13:55 - "⚠️ SERVER RESTART IN 5 MINUTES! | #NumPlayers players online"
13:56 - "⚠️ SERVER RESTART IN 4 MINUTES! | #NumPlayers players online"
13:57 - "⚠️ SERVER RESTART IN 3 MINUTES! | #NumPlayers players online"
13:58 - "⚠️ SERVER RESTART IN 2 MINUTES! | #NumPlayers players online"
13:59 - "⚠️ SERVER RESTART IN 1 MINUTE! | #NumPlayers players online"
```

**Decisão de Design:**
- ✅ **Notificação separada para 8 minutos antes**
- ✅ Aproveita intervalo entre 10min e 5min
- ✅ Mensagem do Gestão tem destaque próprio
- ✅ Não interfere nas mensagens padrão de restart

---

### **Fase 3: Modificar RestartScheduler**

**Arquivo:** `core/scheduler/restart_scheduler.py`

**Mudanças:**
1. **No `__init__`:**
   - Adicionar `gestao_messages_service` como parâmetro opcional
   - Armazenar como `self.gestao_messages_service`

2. **No `_create_restart_notifications()`:**
   - Calcular `time_until_restart` (já existe)
   - **ATUAL:** Método só é chamado quando está dentro de 12 minutos (< 720 segundos)
   - **NECESSÁRIO:** Expandir janela OU criar lógica adicional para consultar 15 minutos antes
   - **DECISÃO:** Expandir janela para 16 minutos para permitir consulta 15 minutos antes
   - Se entre 14-16 minutos E serviço disponível:
     - Obter `api_key` do config
     - Chamar `self.gestao_messages_service.get_scheduled_message(api_key)`
     - Passar resultado para `notification_manager.create_restart_notifications()`

**Obter API Key:**
```python
# Usar mesma lógica de GestaoSyncService
licensing_config = self.config.get('licensing', {})
api_key_raw = licensing_config.get('gestao_api_key', '')
api_key = decrypt_credential(api_key_raw) if api_key_raw.startswith('ENCRYPTED:') else api_key_raw
```

---

### **Fase 4: Modificar main.py**

**Arquivo:** `main.py`

**Na função `init_components()`:**
1. Instanciar `GestaoMessagesService`:
   ```python
   from core.communication.gestao_messages_service import GestaoMessagesService
   gestao_messages_service = GestaoMessagesService(config, logger)
   ```

2. Passar para `RestartScheduler` via construtor:
   ```python
   restart_scheduler = RestartScheduler(
       config,
       server_manager,
       notification_manager,
       logger,
       gestao_messages_service=gestao_messages_service  # NOVO PARÂMETRO
   )
   ```

**Nota:** Modificar `__init__` do `RestartScheduler` para aceitar parâmetro opcional `gestao_messages_service`

---

## 🔄 Fluxo Completo Detalhado

### **Cenário: Restart agendado para 14:00, horário atual 13:45**

1. **13:45** - `RestartScheduler._create_restart_notifications()` é chamado
   - `time_until_restart = 15 minutos` (900 segundos)
   - Dentro da janela de 14-16 minutos? ✅ Sim (dentro da janela de segurança)

2. **13:45:00** - `RestartScheduler` chama `GestaoMessagesService.get_scheduled_message(api_key)`
   - Verifica cache (primeira vez, cache vazio)
   - Faz GET `https://scumsm.com/api/v1/servers/messages?api_key=ssm_...`
   - Resposta: `{"message": "Enquanto o Servidor reinicia, peça um ifood cupom 545asdff"}`
   - Armazena no cache (timestamp atual + 5min)
   - Retorna: `"Enquanto o Servidor reinicia, peça um ifood cupom 545asdff"`

3. **13:45:01** - `RestartScheduler` chama `NotificationManager.create_restart_notifications()`
   - Passa `gestao_message="Enquanto o Servidor reinicia, peça um ifood cupom 545asdff"`
   - Carrega template de restart (10min, 5min, 4min, 3min, 2min, 1min)
   - Cria notificação adicional para 8 minutos antes (13:52)
   - Combina todas as notificações: padrão + Gestão
   - Ordena por horário: 13:50 (10min), 13:52 (8min - Gestão), 13:55 (5min), 13:56 (4min), etc.

4. **13:45:02** - Notificações são salvas via `SCUMNotifier.save_notifications()`
   - Arquivo `Notifications.json` do SCUM é atualizado
   - Notificações agendadas para: 13:50, **13:52 (Gestão)**, 13:55, 13:56, 13:57, 13:58, 13:59

5. **13:50** - Jogadores veem no jogo:
   - `"⚠️ SERVER RESTART IN 10 MINUTES! | 25 players online"`

6. **13:52** - Jogadores veem no jogo (mensagem do Gestão):
   - `"Enquanto o Servidor reinicia, peça um ifood cupom 545asdff"`

7. **13:55** - Jogadores veem no jogo:
   - `"⚠️ SERVER RESTART IN 5 MINUTES! | 25 players online"`

### **Cenário Alternativo: Erro na consulta ou sem mensagem**

1. **13:45** - `GestaoMessagesService.get_scheduled_message(api_key)`
   - Timeout de 5s → `None` retornado
   - OU resposta: `{"message": null}`
   - Log warning registrado (se erro)
   - Retorna `None`
   - Restart continua normalmente

2. **13:45:01** - `NotificationManager.create_restart_notifications(gestao_message=None)`
   - `gestao_message` é None, então não cria notificação adicional
   - Notificações padrão são criadas normalmente (10min, 5min, 4min, 3min, 2min, 1min)
   - Estrutura final: apenas 6 notificações padrão (sem a de 8min)
   - Restart não é interrompido

---

## ⚙️ Configurações Necessárias

### **Nenhuma Configuração Nova Necessária**

- ✅ URL do Gestão: já existe em `core/config/server_urls.py`
- ✅ API Key: já existe em `config.json` → `licensing.gestao_api_key`
- ✅ Timeout: hardcoded 5s (conforme documentação)
- ✅ Cache: hardcoded 5min (conforme documentação)

---

## 🧪 Testes Necessários

### **Testes Unitários:**

1. **GestaoMessagesService:**
   - ✅ Retorna mensagem quando API retorna sucesso
   - ✅ Retorna None quando API retorna `{"message": null}`
   - ✅ Retorna None em caso de timeout
   - ✅ Retorna None em caso de erro HTTP (400, 404, 500)
   - ✅ Cache funciona corretamente (retorna cache válido sem consultar API)
   - ✅ Cache expira corretamente (refaz consulta após 5min)
   - ✅ Nunca lança exceção (sempre retorna None em caso de erro)

2. **NotificationManager:**
   - ✅ Adiciona mensagem do Gestão quando fornecida
   - ✅ Não adiciona quando `gestao_message` é None
   - ✅ Formato da mensagem combinada está correto

3. **RestartScheduler:**
   - ✅ Janela expandida para 16 minutos (permite consulta 15 min antes)
   - ✅ Consulta Gestão apenas entre 14-16 minutos antes
   - ✅ Passa mensagem corretamente para NotificationManager
   - ✅ Não interrompe restart se consulta falhar

### **Testes de Integração:**

1. ✅ Consulta real ao endpoint do Gestão (ambiente de dev/test)
2. ✅ Mensagem aparece corretamente no jogo SCUM
3. ✅ Cache evita consultas excessivas
4. ✅ Erros não interrompem o restart

---

## 📋 Checklist de Implementação

### **Fase 1: Criar GestaoMessagesService**
- [ ] Criar arquivo `core/communication/gestao_messages_service.py`
- [ ] Implementar classe `GestaoMessagesService`
- [ ] Implementar método `get_scheduled_message()`
- [ ] Implementar método `_fetch_message_from_gestao()`
- [ ] Implementar cache com TTL de 5 minutos
- [ ] Implementar tratamento de erros completo
- [ ] Adicionar logs apropriados
- [ ] Testes unitários básicos

### **Fase 2: Modificar NotificationManager**
- [ ] Adicionar parâmetro `gestao_message` em `create_restart_notifications()`
- [ ] Implementar lógica de inclusão da mensagem (5min antes)
- [ ] Testar formato da mensagem combinada
- [ ] Garantir compatibilidade com código existente (parâmetro opcional)

### **Fase 3: Modificar RestartScheduler**
- [ ] Adicionar parâmetro `gestao_messages_service` no `__init__`
- [ ] **EXPANDIR janela de tempo** de 12min para 16min em `_create_restart_notifications()`
- [ ] Implementar lógica de consulta no `_create_restart_notifications()`
- [ ] Validar janela de tempo (14-16 minutos antes para consulta)
- [ ] Obter `api_key` corretamente (mesma lógica de GestaoSyncService)
- [ ] Tratar caso quando serviço não está disponível
- [ ] Adicionar logs apropriados

### **Fase 4: Modificar main.py**
- [ ] Instanciar `GestaoMessagesService` em `init_components()`
- [ ] Passar para `RestartScheduler` via construtor
- [ ] Verificar inicialização correta

### **Fase 5: Testes e Validação**
- [ ] Testes unitários de GestaoMessagesService
- [ ] Testes de integração com endpoint real (dev)
- [ ] Testar cenário de sucesso (mensagem retornada)
- [ ] Testar cenário de erro (timeout, 404, 500)
- [ ] Testar cache (consultas repetidas)
- [ ] Validar mensagem no jogo SCUM

### **Fase 6: Documentação**
- [ ] Atualizar documentação de API (se aplicável)
- [ ] Adicionar comentários no código
- [ ] Documentar comportamento esperado
- [ ] Criar exemplo de uso (se necessário)

---

## 🎨 Decisões de Design

### **1. Onde incluir a mensagem do Gestão?**

**Decisão:** **Criar notificação separada para 8 minutos antes**
- ✅ Aproveita intervalo entre 10min e 5min (9,8,7,6 minutos livres)
- ✅ Mensagem do Gestão tem destaque próprio
- ✅ Não interfere nas mensagens padrão de restart
- ✅ Horário ideal: 8 minutos antes (meio termo entre 10min e 5min)

---

### **2. Formato da mensagem do Gestão**

**Decisão:** **Mensagem pura do Gestão (sem formatação adicional)**
- ✅ Mensagem vem pronta do Gestão
- ✅ Aparece em notificação separada (8 minutos antes)
- ✅ Não precisa combinar com mensagens padrão
- ✅ Exemplo: `"Enquanto o Servidor reinicia, peça um ifood cupom 545asdff"`

**Estrutura no Notifications.json:**
```json
{
  "day": "Everyday",
  "time": ["20:52"],  // 8 minutos antes (restart em 21:00)
  "duration": 10,
  "color": "255-180-50",
  "message": "Enquanto o Servidor reinicia, peça um ifood cupom 545asdff"
}
```

---

### **3. Quando consultar o Gestão?**

**Decisão do usuário:** Consultar ~15 minutos antes do restart

**Implementação proposta:**
- Consultar quando `_create_restart_notifications()` é chamado
- Este método é chamado quando está dentro de 12 minutos antes (atual)
- **MUDANÇA NECESSÁRIA:** Expandir janela ou consultar mais cedo
- Validar se está entre 14-16 minutos antes (janela de segurança)
- Se sim, consultar; se não, usar cache se disponível

**Decisão:** Consultar quando `time_until_restart` está entre 840-960 segundos (14-16 min)
- Janela de segurança garante que a consulta acontece ~15 minutos antes
- Dá tempo suficiente para inserir notificação de 8 minutos antes

---

### **4. Cache: escopo global ou por restart?**

**Opção A:** Cache global (uma mensagem para todos os restarts do dia)
- ✅ Simples
- ✅ Evita consultas excessivas
- ❌ Mensagem pode mudar durante o dia

**Opção B:** Cache por restart (validar por horário de restart)
- ✅ Mais preciso
- ✅ Permite mensagens diferentes por restart
- ❌ Mais complexo

**Decisão:** **Cache global de 5 minutos**
- ✅ Simples e eficiente
- ✅ Conforme documentação sugere cache local
- ✅ Evita consultas excessivas
- ✅ Cache pode ser reutilizado se houver múltiplos restarts próximos

**Nota:** Como a consulta acontece ~15 minutos antes, e inserimos notificação para 8 minutos antes, o cache de 5 minutos não interfere significativamente (a consulta já foi feita com bastante antecedência)

---

## ⚠️ Considerações Importantes

### **1. Não Interromper o Restart**

- ✅ Qualquer erro na consulta deve retornar `None` silenciosamente
- ✅ Logs de warning/error são aceitáveis, mas nunca exceções não tratadas
- ✅ O restart deve continuar normalmente mesmo se a consulta falhar

### **2. Performance**

- ✅ Timeout curto (5s) para não atrasar o processo
- ✅ Cache de 5min evita consultas excessivas
- ✅ Consulta assíncrona se necessário (mas provavelmente não necessário dado o timeout curto)

### **3. Segurança**

- ✅ Usar mesma `api_key` já validada pelo sistema
- ✅ Usar URL hardcoded do Gestão (já existe)
- ✅ Não expor credenciais em logs (já implementado em GestaoSyncService)

### **4. Compatibilidade**

- ✅ Parâmetro `gestao_message` deve ser opcional (retrocompatibilidade)
- ✅ Se `gestao_messages_service` não estiver disponível, comportamento deve ser como antes
- ✅ Não quebrar funcionalidade existente

---

## 📊 Resumo de Arquivos a Modificar

| Arquivo | Tipo | Mudanças |
|---------|------|----------|
| `core/communication/gestao_messages_service.py` | **NOVO** | Classe completa |
| `core/notifications/notification_manager.py` | Modificar | Adicionar parâmetro `gestao_message` |
| `core/scheduler/restart_scheduler.py` | Modificar | Integrar consulta ao Gestão |
| `main.py` | Modificar | Instanciar `GestaoMessagesService` |
| `core/communication/__init__.py` | Modificar | Exportar `GestaoMessagesService` (opcional) |

---

## 🚀 Ordem de Implementação Recomendada

1. **Criar `GestaoMessagesService`** (isolado, fácil de testar)
2. **Modificar `NotificationManager`** (adicionar parâmetro, fácil)
3. **Modificar `RestartScheduler`** (integração, requer testes)
4. **Modificar `main.py`** (inicialização, requer testes de integração)
5. **Testes finais** (validação completa)

---

## ✅ Critérios de Sucesso

A implementação será considerada bem-sucedida quando:

1. ✅ Consulta ao Gestão funciona corretamente (retorna mensagem ou None)
2. ✅ Mensagem do Gestão aparece nas notificações de restart no jogo
3. ✅ Erros não interrompem o restart
4. ✅ Cache funciona (evita consultas excessivas)
5. ✅ Código existente não é quebrado (retrocompatibilidade)
6. ✅ Logs adequados para debug
7. ✅ Testes passam (unitários + integração)

---

## 📝 Notas Finais

- **Complexidade:** Média (requer integração entre 3 componentes)
- **Risco:** Baixo (tratamento de erros robusto, não quebra funcionalidade existente)
- **Tempo estimado:** 4-6 horas (implementação + testes + ajustes)
- **Dependências:** Nenhuma nova (usa `requests` já existente, `api_key` já configurada)

---

## 🔗 Referências

- Documentação fornecida pelo dev do Gestão
- `core/communication/gestao_sync_service.py` (padrão de integração)
- `core/scheduler/restart_scheduler.py` (lógica de restart)
- `core/notifications/notification_manager.py` (sistema de notificações)

