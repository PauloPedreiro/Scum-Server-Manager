# Planejamento: Correção da Limpeza de WAL/SHM no Restart Manual

## 📋 Problema Identificado

Os arquivos `SCUM.db-shm` e `SCUM.db-wal` não estão sendo removidos/recriados após um restart manual, enquanto o `stop` funciona normalmente.

### Análise do Problema

1. **No `/api/server/stop`** (funciona corretamente):
   - Chama `server_manager.stop_server()`
   - Aguarda confirmação de parada
   - Executa limpeza de WAL/SHM após servidor parar ✅

2. **No `/api/server/restart`** (problema):
   - Chama `server_manager.restart_server()` que faz: `stop → wait 5s → start`
   - Tenta limpar WAL/SHM **DEPOIS** do restart completo
   - Limpeza está dentro de condição que depende de `elevated_users_manager` existir
   - Verifica se servidor não está rodando, mas nesse ponto o servidor já pode ter reiniciado ❌

3. **No `server_manager.restart_server()`**:
   - Não há limpeza de WAL/SHM internamente
   - Apenas chama `stop_server()` → aguarda → `start_server()`

## 🎯 Solução Proposta

### Estratégia
Mover a limpeza de WAL/SHM para **dentro** do método `restart_server()` do ServerManager, executando-a no momento correto: **após o stop e antes do start**.

### Vantagens
- ✅ Limpeza acontece no momento certo (servidor parado, antes de reiniciar)
- ✅ Código mais organizado (lógica centralizada no ServerManager)
- ✅ Funciona independentemente de outras dependências
- ✅ Consistente com o comportamento do stop
- ✅ Garante que arquivos sejam limpos antes do servidor reiniciar

## 📝 Plano de Implementação

### 1. Modificar `server_manager.restart_server()`

**Localização**: `core/server_control/server_manager.py`

**Mudanças**:
- Após `stop_server()` bem-sucedido
- Aguardar confirmação de que servidor parou completamente
- Executar limpeza de WAL/SHM usando `cleanup_scum_db_wal_files()`
- Depois executar `start_server()`

**Código a adicionar**:
```python
# Após stop_server() bem-sucedido
# Aguardar confirmação
time.sleep(2)  # Aguardar servidor parar completamente
if not self._is_service_running():
    # Limpar arquivos WAL/SHM
    try:
        from utils.scum_db_cleanup import cleanup_scum_db_wal_files
        from utils.config_path_helper import ConfigPathHelper
        
        # Obter caminho do SCUM.db
        path_helper = ConfigPathHelper(self.config)
        scum_db_path = path_helper.get_scum_db_path()
        
        cleanup_result = cleanup_scum_db_wal_files(
            self, 
            scum_db_path, 
            self.logger
        )
        if cleanup_result.get("success"):
            self.logger.info(f"Limpeza de WAL/SHM durante restart: {cleanup_result.get('message')}")
        else:
            self.logger.warning(f"Limpeza de WAL/SHM durante restart: {cleanup_result.get('message')}")
    except Exception as e:
        self.logger.error(f"Erro ao limpar arquivos WAL/SHM durante restart: {e}")
        # Continuar mesmo se falhar
```

### 2. Ajustar endpoint `/api/server/restart`

**Localização**: `main.py` (linhas 990-1085)

**Mudanças**:
- Remover a limpeza de WAL/SHM do endpoint (linhas 1039-1049)
- Manter apenas a sincronização de elevated users
- A limpeza agora será feita automaticamente pelo ServerManager

**Código a remover**:
```python
# Remover estas linhas (1039-1049):
# Limpar arquivos WAL/SHM do SCUM.db antes de reiniciar
try:
    from utils.scum_db_cleanup import cleanup_scum_db_wal_files
    scum_db_path = path_helper.get_scum_db_path()
    cleanup_result = cleanup_scum_db_wal_files(server_manager, scum_db_path, logger)
    if cleanup_result.get("success"):
        logger.info(f"Limpeza de WAL/SHM durante restart: {cleanup_result.get('message')}")
    else:
        logger.warning(f"Limpeza de WAL/SHM durante restart: {cleanup_result.get('message')}")
except Exception as e:
    logger.error(f"Erro ao limpar arquivos WAL/SHM durante restart: {e}")
```

### 3. Garantir acesso ao caminho do SCUM.db

**Opções**:
- **Opção A**: Criar método auxiliar no ServerManager para obter caminho do SCUM.db
- **Opção B**: Passar `path_helper` como parâmetro opcional no construtor do ServerManager
- **Opção C**: Usar `ConfigPathHelper` diretamente dentro do método (escolhida)

**Escolha**: Opção C - mais simples e não requer mudanças no construtor

## 🔄 Fluxo Após Implementação

### Restart Manual:
1. Usuário chama `/api/server/restart`
2. Endpoint chama `server_manager.restart_server()`
3. `restart_server()` executa:
   - `stop_server()` → servidor para
   - Aguarda 2s → confirma que parou
   - **Limpa WAL/SHM** → remove arquivos -shm e -wal
   - Aguarda 5s → prepara reinício
   - `start_server()` → servidor inicia
4. Endpoint sincroniza elevated users (se necessário)
5. Retorna resultado

### Stop Manual:
- Continua funcionando como antes (sem mudanças)

## ✅ Validações

Após implementação, validar:
- [ ] Restart manual remove arquivos WAL/SHM corretamente
- [ ] Arquivos são recriados quando servidor inicia
- [ ] Stop manual continua funcionando
- [ ] Restart agendado continua funcionando (já tem limpeza própria)
- [ ] Logs mostram limpeza sendo executada durante restart

## 📌 Observações

- A limpeza no restart agendado (`core/scheduler/restart_scheduler.py`) já está implementada e funcionando
- Esta correção afeta apenas o restart manual via endpoint
- A função `cleanup_scum_db_wal_files()` já existe e está testada
- Não há risco de quebrar funcionalidades existentes

## 🚀 Próximos Passos

1. Revisar este planejamento
2. Aprovar implementação
3. Implementar mudanças
4. Testar restart manual
5. Validar que arquivos WAL/SHM são limpos corretamente

