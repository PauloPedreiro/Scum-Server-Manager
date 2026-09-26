# Endpoints de Precisão de Horário

## Visão Geral

Sistema de precisão de horário para o comando `/tm` que permite ajustar a precisão do horário exibido nas notificações in-game através de um offset configurável.

## Configuração

### Arquivo: `data/config.json`

```json
{
  "time_precision": {
    "enabled": true,
    "offset_minutes": 8,
    "description": "Minutos para adicionar ao horário do servidor para maior precisão no comando /tm"
  }
}
```

### Parâmetros

- **`enabled`**: `boolean` - Habilita/desabilita o sistema de precisão
- **`offset_minutes`**: `integer` - Número de minutos para adicionar ao horário base
- **`description`**: `string` - Descrição da configuração

## Endpoints

### 1. Obter Configuração de Precisão

**GET** `/api/time-precision/config`

Retorna a configuração atual de precisão de horário.

#### Resposta de Sucesso

```json
{
  "success": true,
  "data": {
    "enabled": true,
    "offset_minutes": 8,
    "description": "Minutos para adicionar ao horário do servidor para maior precisão no comando /tm"
  },
  "timestamp": 1703123456.789
}
```

#### Resposta de Erro

```json
{
  "success": false,
  "error": "Arquivo config.json não encontrado"
}
```

#### Códigos de Status

- `200` - Sucesso
- `404` - Arquivo config.json não encontrado
- `500` - Erro interno do servidor

### 2. Testar Precisão de Horário

**POST** `/api/time-precision/test`

Testa a precisão de horário aplicando o offset configurado.

#### Resposta de Sucesso

```json
{
  "success": true,
  "data": {
    "base_time": "15:35",
    "adjusted_time": "15:43",
    "offset_minutes": 8,
    "enabled": true,
    "time_of_day": 15.5857553482,
    "difference_minutes": 8
  },
  "timestamp": 1703123456.789
}
```

#### Resposta de Erro

```json
{
  "success": false,
  "error": "WeatherScheduler não inicializado"
}
```

#### Códigos de Status

- `200` - Sucesso
- `404` - Banco SCUM.db não encontrado ou dados climáticos não encontrados
- `500` - Erro interno do servidor

## Como Funciona

### 1. Comando `/tm` Executado

1. Sistema detecta comando `/tm` no chat
2. Consulta `time_of_day` do banco SCUM.db
3. Converte para formato HH:MM
4. Aplica offset configurado se habilitado
5. Cria notificação in-game com horário ajustado

### 2. Cálculo do Offset

```python
# Exemplo de cálculo
time_of_day = 15.5857553482  # Do banco SCUM.db
hours = int(time_of_day)      # 15
minutes = int((time_of_day - hours) * 60)  # 35
base_time = "15:35"

# Aplicar offset
offset_minutes = 8
adjusted_time = base_time + timedelta(minutes=offset_minutes)
# Resultado: "15:43"
```

### 3. Logs do Sistema

```
INFO: Aplicando offset de precisão: +8 minutos
INFO: Horário do servidor obtido diretamente do banco: 15:43 (time_of_day: 15.5857553482, offset: +8min)
INFO: Teste de precisão: 15:35 -> 15:43 (offset: 8min)
```

## Exemplos de Uso

### cURL

#### Obter Configuração

```bash
curl -X GET "http://localhost:3000/api/time-precision/config" \
  -H "Content-Type: application/json"
```

#### Testar Precisão

```bash
curl -X POST "http://localhost:3000/api/time-precision/test" \
  -H "Content-Type: application/json"
```

### Python

```python
import requests

# Obter configuração
response = requests.get("http://localhost:3000/api/time-precision/config")
config = response.json()
print(f"Offset configurado: {config['data']['offset_minutes']} minutos")

# Testar precisão
response = requests.post("http://localhost:3000/api/time-precision/test")
test_result = response.json()
print(f"Horário base: {test_result['data']['base_time']}")
print(f"Horário ajustado: {test_result['data']['adjusted_time']}")
```

### JavaScript

```javascript
// Obter configuração
fetch('http://localhost:3000/api/time-precision/config')
  .then(response => response.json())
  .then(data => {
    console.log('Configuração:', data.data);
  });

// Testar precisão
fetch('http://localhost:3000/api/time-precision/test', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => {
  console.log('Teste de precisão:', data.data);
});
```

## Troubleshooting

### Problema: Offset não está sendo aplicado

**Solução:**
1. Verificar se `enabled: true` no config.json
2. Verificar se `offset_minutes > 0`
3. Verificar logs do sistema para mensagens de erro

### Problema: Horário ainda impreciso

**Solução:**
1. Ajustar `offset_minutes` no config.json
2. Testar com endpoint `/api/time-precision/test`
3. Monitorar logs para ver aplicação do offset

### Problema: Erro ao acessar banco SCUM.db

**Solução:**
1. Verificar se o caminho do banco está correto
2. Verificar se o servidor SCUM está rodando
3. Verificar permissões de acesso ao arquivo

## Integração com Comando /tm

O sistema de precisão é automaticamente integrado ao comando `/tm`:

1. **Detecção**: ChatCommandMonitor detecta `/tm`
2. **Consulta**: Obtém horário do servidor
3. **Aplicação**: Aplica offset configurado
4. **Notificação**: Cria notificação in-game com horário ajustado
5. **Discord**: Envia confirmação para Discord

## Monitoramento

### Logs Importantes

```
INFO: Aplicando offset de precisão: +8 minutos
INFO: Horário do servidor obtido via API: 15:35 -> 15:43 (offset aplicado)
INFO: Teste de precisão: 15:35 -> 15:43 (offset: 8min)
```

### Métricas

- **Precisão**: Diferença entre horário base e ajustado
- **Performance**: Tempo de resposta dos endpoints
- **Confiabilidade**: Taxa de sucesso das consultas

## Changelog

### v1.0.0 (2024-01-XX)
- Implementação inicial do sistema de precisão
- Endpoints de configuração e teste
- Integração com comando `/tm`
- Suporte a offset configurável
