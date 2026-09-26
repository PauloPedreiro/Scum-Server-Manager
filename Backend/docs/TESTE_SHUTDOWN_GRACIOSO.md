# 🧪 Teste de Shutdown Gracioso do Servidor SCUM

## 📋 Resumo das Mudanças

As modificações implementadas permitem que o servidor SCUM faça um **shutdown gracioso** (graceful shutdown), dando tempo suficiente para:
- ✅ Salvar dados de basebuilding
- ✅ Fazer backups completos
- ✅ Limpar recursos (gardens, farming, etc.)
- ✅ Fechar conexões de banco de dados corretamente
- ✅ Executar todos os passos de shutdown que aparecem no log normal

## 🔧 Mudanças Implementadas

### 1. `_stop_service_nssm()` - Método NSSM
- **Antes**: Aguardava apenas 10 segundos
- **Agora**: Aguarda até 2 minutos (120 segundos) com verificação a cada 5 segundos
- **Logs**: Informa progresso a cada 30 segundos

### 2. `_stop_service_powershell()` - Método PowerShell
- **Antes**: Usava `-Force` imediatamente
- **Agora**: 
  - Tenta shutdown gracioso (sem `-Force`) por até 2 minutos
  - Se não parar, aguarda mais 60 segundos adicionais (total de 3 minutos)
  - **NUNCA usa `-Force`** - sempre aguarda shutdown gracioso
  - Retorna erro apenas se não parar após 3 minutos
  - Logs informativos durante o processo

## 🧪 Como Testar

### Teste 1: Shutdown via API (Recomendado)

1. **Verificar que o servidor está rodando:**
```bash
curl -X GET http://localhost:3000/api/server/status
```

2. **Parar o servidor via API:**
```bash
curl -X POST http://localhost:3000/api/server/stop \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 0}'
```

3. **Observar os logs do servidor SCUM:**
   - Abra o arquivo de log do servidor SCUM
   - Verifique se aparecem TODOS os passos de shutdown:
     - `[Basebuilding] Saving base data`
     - `[Basebuilding] Done. Elapsed time = X s`
     - `[Basebuilding] Bases count on save: X`
     - `[Basebuilding] Base elements count on save: X`
     - `AGarden::EndPlay`
     - `Farming [DedicatedServer] AGardenManager::RemoveMeshInstance`
     - `LogRadiationManager: DbSaveGlobalData`
     - `LogDatabase: Closing connection`
     - `UWorld::CleanupWorld` (múltiplas entradas)

### Teste 2: Shutdown via Restart

1. **Reiniciar o servidor:**
```bash
curl -X POST http://localhost:3000/api/server/restart \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 0}'
```

2. **Observar os logs:**
   - Durante a fase de parada, verifique se todos os passos aparecem
   - O servidor deve ter tempo suficiente para fazer todos os backups

### Teste 3: Verificar Logs da Aplicação

Durante o shutdown, os logs da aplicação devem mostrar:

```
[1/2] Parando serviço via NSSM com shutdown gracioso...
Aguardando shutdown gracioso do servidor SCUM (pode levar até 2 minutos)...
Aguardando shutdown gracioso... (30/120s)
Aguardando shutdown gracioso... (60/120s)
Serviço parado graciosamente via NSSM após X segundos
```

## ✅ Critérios de Sucesso

### ✅ Teste PASSOU se:
1. Os logs do servidor SCUM mostram **TODOS** os passos de shutdown completo
2. Não há mensagens de erro relacionadas a dados não salvos
3. O servidor para dentro de 2 minutos (normalmente 30-60 segundos)
4. Os logs da aplicação mostram mensagens de "shutdown gracioso"
5. Após reiniciar, todos os dados estão preservados (bases, items, etc.)

### ❌ Teste FALHOU se:
1. Os logs do servidor SCUM param abruptamente sem mostrar todos os passos
2. Aparecem erros de "INTERRUPTED" ou "FORCE QUIT" muito cedo
3. Dados são perdidos após reiniciar
4. O servidor não para após 3 minutos (indica problema que precisa ser investigado)

## 📊 Comparação: Antes vs Depois

### ❌ ANTES (Shutdown Forçado)
```
[2025.12.02-02.55.21:316][653]LogCore: Engine exit requested
[2025.12.02-02.55.21:318][653]LogWorld: BeginTearingDown
[2025.12.02-02.55.22:136][653]LogSCUM: [Basebuilding] Saving base data...
(SERVIDOR PARA AQUI - não completa o processo)
```

### ✅ DEPOIS (Shutdown Gracioso)
```
[2025.12.02-02.55.21:316][653]LogCore: Engine exit requested
[2025.12.02-02.55.21:318][653]LogWorld: BeginTearingDown
[2025.12.02-02.55.22:136][653]LogSCUM: [Basebuilding] Saving base data. Time = X
[2025.12.02-02.55.24:040][653]LogSCUM: [Basebuilding] Done. Elapsed time = 2 s
[2025.12.02-02.55.24:040][653]LogSCUM: [Basebuilding] Bases count on save: 88
[2025.12.02-02.55.24:041][653]LogSCUM: [Basebuilding] Base elements count on save: 26874
[2025.12.02-02.55.04:325][653]LogSCUM: AGarden::EndPlay(4)
[... todos os passos de limpeza ...]
[2025.12.02-02.55.04:584][653]LogDatabase: Closing connection to 'SCUM.db'...
[2025.12.02-02.55.04:585][653]LogDatabase: ...success!
(SERVIDOR COMPLETA TODO O PROCESSO)
```

## 🔍 Troubleshooting

### Problema: Servidor não para após 3 minutos
**Solução**: 
- Verifique se há algum processo bloqueando o shutdown
- Verifique os logs do servidor SCUM para identificar o problema
- O código **NÃO força** a parada - sempre aguarda shutdown gracioso
- Se necessário, pare o servidor manualmente e investigue o problema

### Problema: Logs não mostram todos os passos
**Solução**: 
1. Verifique se o arquivo de log está sendo atualizado em tempo real
2. Aumente o tempo de espera se necessário (modificar `max_wait_time` no código)

### Problema: Dados ainda são perdidos
**Solução**: 
1. Verifique se o servidor tem permissões de escrita no diretório de saves
2. Verifique se há espaço em disco suficiente
3. Considere aumentar o `max_wait_time` para 3 minutos (180 segundos)

## 📝 Notas Importantes

- O shutdown gracioso pode levar de **30 segundos a 3 minutos** dependendo da quantidade de dados
- Servidores com muitas bases e elementos podem levar mais tempo
- O código **NUNCA força a parada** - sempre aguarda shutdown gracioso (até 3 minutos)
- Se o servidor não parar após 3 minutos, retorna erro e deve ser investigado manualmente
- Os logs da aplicação mostram o progresso a cada 30 segundos

## 🎯 Próximos Passos

Após testar, verifique:
1. ✅ Todos os dados foram salvos corretamente
2. ✅ Não há erros nos logs do servidor SCUM
3. ✅ O tempo de shutdown está adequado (não muito longo, não muito curto)
4. ✅ O servidor reinicia normalmente após o shutdown gracioso

