# Sistema de Verificação Periódica de Veículos

## Visão Geral

O sistema de verificação periódica de veículos verifica automaticamente se os veículos registrados no banco SSM.db ainda existem no banco SCUM.db. Veículos que não são encontrados no SCUM.db têm seu status atualizado para `4` (Removido/Não encontrado).

O serviço executa verificações periódicas a cada 24 horas (configurável) e pode ser controlado via API.

## Configuração

O serviço é configurado no arquivo `config.json`:

```json
{
  "vehicle_verification": {
    "enabled": true,
    "auto_start": true,
    "verification_interval_hours": 24,
    "description": "Verificação periódica se os veículos registrados ainda existem no SCUM.db"
  }
}
```

### Parâmetros

- `enabled`: Habilita ou desabilita o serviço
- `auto_start`: Se `true`, o serviço inicia automaticamente quando o backend é iniciado
- `verification_interval_hours`: Intervalo entre verificações em horas (padrão: 24)

## Endpoints

### 1. Obter Status do Serviço

**GET** `/api/vehicles/verification/status`

Retorna o status atual do serviço de verificação, incluindo informações sobre a última execução.

#### Resposta de Sucesso (200)

```json
{
  "success": true,
  "data": {
    "enabled": true,
    "is_running": true,
    "verification_interval_hours": 24,
    "last_verification": "2025-11-10T01:30:00.000Z",
    "last_result": {
      "success": true,
      "message": "Verificação concluída: 35 veículos existem, 4 não encontrados",
      "total_checked": 39,
      "existing": 35,
      "not_found": 4,
      "updated": 4,
      "not_found_vehicle_ids": [14370019, 14370020],
      "timestamp": "2025-11-10T01:30:00.000Z"
    }
  },
  "timestamp": 1760907347.523
}
```

#### Campos da Resposta

- `enabled`: Se o serviço está habilitado
- `is_running`: Se o serviço está em execução
- `verification_interval_hours`: Intervalo configurado entre verificações
- `last_verification`: Data/hora da última verificação executada
- `last_result`: Resultado da última verificação executada
  - `total_checked`: Total de veículos verificados
  - `existing`: Quantidade de veículos que ainda existem
  - `not_found`: Quantidade de veículos não encontrados
  - `updated`: Quantidade de veículos que tiveram status atualizado
  - `not_found_vehicle_ids`: Lista de IDs dos veículos não encontrados

---

### 2. Iniciar Serviço

**POST** `/api/vehicles/verification/start`

Inicia o serviço de verificação periódica. Executa uma verificação imediata e agenda as próximas execuções.

#### Resposta de Sucesso (200)

```json
{
  "success": true,
  "message": "Serviço de verificação de veículos iniciado",
  "status": "started",
  "verification_interval_hours": 24
}
```

#### Resposta de Erro - Já em Execução (400)

```json
{
  "success": false,
  "message": "Serviço de verificação de veículos já está em execução",
  "status": "already_running"
}
```

#### Resposta de Erro - Serviço Desabilitado (400)

```json
{
  "success": false,
  "message": "Serviço de verificação de veículos desabilitado",
  "status": "disabled"
}
```

---

### 3. Parar Serviço

**POST** `/api/vehicles/verification/stop`

Para o serviço de verificação periódica. As verificações agendadas são canceladas.

#### Resposta de Sucesso (200)

```json
{
  "success": true,
  "message": "Serviço de verificação de veículos parado",
  "status": "stopped"
}
```

#### Resposta de Erro - Não Está em Execução (400)

```json
{
  "success": false,
  "message": "Serviço de verificação de veículos não está em execução",
  "status": "not_running"
}
```

---

### 4. Executar Verificação Manual

**POST** `/api/vehicles/verification/run-now`

Executa uma verificação manual imediata, independente do agendamento. Útil para testar ou executar verificações sob demanda.

#### Resposta de Sucesso (200)

```json
{
  "success": true,
  "message": "Verificação concluída: 35 veículos existem, 4 não encontrados",
  "total_checked": 39,
  "existing": 35,
  "not_found": 4,
  "updated": 4,
  "not_found_vehicle_ids": [14370019, 14370020],
  "timestamp": "2025-11-10T01:30:00.000Z"
}
```

#### Campos da Resposta

- `total_checked`: Total de veículos verificados
- `existing`: Quantidade de veículos que ainda existem no SCUM.db
- `not_found`: Quantidade de veículos não encontrados no SCUM.db
- `updated`: Quantidade de veículos que tiveram status atualizado para `2` (Desaparecido)
- `not_found_vehicle_ids`: Lista de IDs dos veículos não encontrados
- `timestamp`: Data/hora da execução da verificação

---

## Como Funciona

1. **Coleta de IDs**: O serviço obtém todos os `vehicle_entity_id` da tabela `vehicle_current_ownership` do SSM.db
2. **Verificação em Lote**: Verifica em lote se cada veículo existe na tabela `vehicle_spawner` do SCUM.db
3. **Atualização de Status**: Veículos não encontrados têm seu status atualizado para `2` (Desaparecido)
4. **Logging**: Todas as operações são registradas nos logs do sistema

## Status dos Veículos

Os veículos podem ter os seguintes status:

- `0`: Ativo
- `1`: Inativo
- `2`: Desaparecido (atribuído quando não encontrado no SCUM.db ou por evento Disappeared)
- `3`: Destruído

## Exemplos de Uso

### Verificar Status do Serviço

```bash
curl -X GET http://localhost:3000/api/vehicles/verification/status
```

### Iniciar Serviço

```bash
curl -X POST http://localhost:3000/api/vehicles/verification/start
```

### Executar Verificação Manual

```bash
curl -X POST http://localhost:3000/api/vehicles/verification/run-now
```

### Parar Serviço

```bash
curl -X POST http://localhost:3000/api/vehicles/verification/stop
```

## Notas Importantes

1. **Performance**: A verificação é feita em lote para melhor performance
2. **Não Bloqueante**: As verificações são apenas leituras (SELECT) no SCUM.db, não bloqueiam o servidor
3. **Automático**: Se `auto_start` estiver habilitado, o serviço inicia automaticamente quando o backend é iniciado
4. **Logs**: Todas as verificações são registradas nos logs do sistema para auditoria

## Tratamento de Erros

- Se o SCUM.db não estiver acessível, a verificação falha e registra um erro
- Se o SSM.db não estiver acessível, o serviço não pode ser iniciado
- Erros durante a verificação são registrados nos logs, mas não interrompem o serviço

