# Sistema de Restart Programado - Frontend

## Visão Geral

Este documento explica como implementar a interface para gerenciar os horários de restart automático do servidor SCUM.

**Base URL:** `http://localhost:3000/api/server/schedules`

---

## Endpoint Único

### POST `/schedules`

Este endpoint único gerencia todas as operações de restart programado através de diferentes métodos HTTP.

**URL:** `http://localhost:3000/api/server/schedules`

---

## Operações Disponíveis

### 1. **Listar Horários Programados**
**GET** `/schedules`

**Resposta:**
```json
{
  success": true,
  schedules": {
    restartTimes": ["1:0,5:0,9:0,13:0, 170,21:0],  enabled: true,
lastRestart: null,
nextRestart: null,lastNotification": null
  }
}
```

### 2. **Adicionar Novo Horário**
**POST** `/schedules`

**Body:**
```json
[object Object]  time:23
}
```

**Resposta:**
```json
{
  success": true,
  restartTimes": ["1:0,5:0,9:0,13:0,17:0,21, "23:0]
}
```

### 3. **Remover Horário**
**DELETE** `/schedules`

**Body:**
```json
[object Object]  time:05
}
```

**Resposta:**
```json
{
  success": true,
  restartTimes": ["1:0,9:0,13:0,17, "21:0]
}
```

### 4. **Ativar/Desativar Sistema**
**PUT** `/schedules`

**Body:**
```json
{
  enabled": true
}
```

**Resposta:**
```json
{
  success": true,
  enabled": true
}
```

---

## Implementação Frontend

### Interface Sugerida

```tsx
import React, { useState, useEffect } from 'react';

interface ScheduledRestart {
  restartTimes: string[];
  enabled: boolean;
  lastRestart: string | null;
  nextRestart: string | null;
  lastNotification: string | null;
}

const ScheduledRestartControl: React.FC = () => {
  const [schedules, setSchedules] = useState<ScheduledRestart | null>(null);
  const [selectedTime, setSelectedTime] = useState('0;
  const [loading, setLoading] = useState(false);

  // Buscar horários configurados
  const fetchSchedules = async () =>[object Object] try {
      const response = await fetch(http://localhost:3000/api/server/schedules',[object Object]
        method: 'GET,
        headers:[object Object]Content-Type': application/json' }
      });
      const data = await response.json();
      if (data.success) {
        setSchedules(data.schedules);
      }
    } catch (error) {
      console.error('Erro ao buscar horários:, error);
    }
  };

  // Adicionar novo horário
  const addTime = async () => {
    setLoading(true);
    try {
      const response = await fetch(http://localhost:3000/api/server/schedules',[object Object]
        method: 'POST,
        headers:[object Object]Content-Type': application/json },        body: JSON.stringify({ time: selectedTime })
      });
      const data = await response.json();
      if (data.success) {
        await fetchSchedules(); // Atualizar lista
        setSelectedTime(00:00     }
    } catch (error) {
      console.error(Erro ao adicionar horário:', error);
    } finally [object Object]  setLoading(false);
    }
  };

  // Remover horário
  const removeTime = async (time: string) =>[object Object] try {
      const response = await fetch(http://localhost:3000/api/server/schedules',[object Object]
        method:DELETE,
        headers:[object Object]Content-Type': application/json },        body: JSON.stringify({ time })
      });
      const data = await response.json();
      if (data.success) {
        await fetchSchedules(); // Atualizar lista
      }
    } catch (error) {
      console.error('Erro ao remover horário:, error);
    }
  };

  // Ativar/Desativar sistema
  const toggleSystem = async (enabled: boolean) =>[object Object] try {
      const response = await fetch(http://localhost:3000/api/server/schedules',[object Object]
        method: 'PUT,
        headers:[object Object]Content-Type': application/json },        body: JSON.stringify({ enabled })
      });
      const data = await response.json();
      if (data.success) {
        await fetchSchedules(); // Atualizar status
      }
    } catch (error) {
      console.error('Erro ao alterar status:, error);
    }
  };

  // Gerar opções de horário (00:003 const timeOptions = Array.from({ length:24 }, (_, i) => 
    `${i.toString().padStart(2,0
  );

  useEffect(() => {
    fetchSchedules();
    // Atualizar a cada 30 segundos
    const interval = setInterval(fetchSchedules, 3000;
    return () => clearInterval(interval);
  },);

  return (
    <div className=scheduled-restart-control">
      <h3>Restart automático:</h3>
      
      {/* Lista de horários configurados */}
      <div className="restart-times">
      [object Object]schedules?.restartTimes.map((time, index) => (
          <span key={time} className="time-tag">
            {time.replace(':00',h')}
            {index < schedules.restartTimes.length - 1 && • '}
            <button 
              onClick={() => removeTime(time)}
              className="remove-btn"
              title=Remover horário"
            >
              🗑️
            </button>
          </span>
        ))}
      </div>

      {/* Controles */}
      <div className="controls">
        <div className="time-selector">
          <label>Hora:</label>
          <select 
            value={selectedTime} 
            onChange={(e) => setSelectedTime(e.target.value)}
          >
            {timeOptions.map(time => (
              <option key={time} value={time}>
                {time.replace(':00', 'h')}
              </option>
            ))}
          </select>
          
          <button 
            onClick={addTime}
            disabled={loading || schedules?.restartTimes.includes(selectedTime)}
            className="add-btn"
          >
            ➕
          </button>
        </div>

        {/* Toggle do sistema */}
        <div className="system-toggle">
          <label>
            <input
              type="checkbox"
              checked={schedules?.enabled || false}
              onChange={(e) => toggleSystem(e.target.checked)}
            />
            Sistema de restart automático
          </label>
        </div>
      </div>

      {/* Status */}
      {schedules && (
        <div className="status">
          <p>Status: {schedules.enabled ? '🟢 Ativo' : 🔴 Inativo}</p>
       [object Object]schedules.lastRestart && (
            <p>Último restart: {new Date(schedules.lastRestart).toLocaleString()}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default ScheduledRestartControl;
```

### CSS Sugerido

```css
.scheduled-restart-control[object Object]
  padding: 20x;
  background: #2a2a2a;
  border-radius: 8px;
  color: white;
}

.restart-times [object Object]  margin: 15px 0
  font-size: 16x;
}

.time-tag {
  position: relative;
  display: inline-block;
  margin-right: 10px;
}

.remove-btn {
  background: none;
  border: none;
  color: #ff4444;
  cursor: pointer;
  margin-left: 5x;
  font-size: 12x;
}

.controls[object Object]
  display: flex;
  gap: 20px;
  align-items: center;
  margin-top: 15px;
}

.time-selector[object Object]
  display: flex;
  align-items: center;
  gap: 10px;
}

.time-selector select[object Object]
  padding: 5x;
  border-radius: 4 border:1#555  background: #333;
  color: white;
}

.add-btn[object Object]
  background: #ff880;
  border: none;
  color: white;
  padding: 5x;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16
.add-btn:disabled[object Object]  background: #666
  cursor: not-allowed;
}

.system-toggle label[object Object]
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.status [object Object]  margin-top:15x;
  padding: 10x;
  background: #333;
  border-radius:4x;
}

.status p[object Object]
  margin: 5px 0
  font-size: 14px;
}
```

---

## Funcionalidades do Sistema

###1Notificações Automáticas**
O backend envia notificações via Discord:
- **10min antes:** "⚠️ O servidor será reiniciado automaticamente em 10nuto(s)"
- **5min antes:** "⚠️ O servidor será reiniciado automaticamente em 5nuto(s)"
- **4min antes:** "⚠️ O servidor será reiniciado automaticamente em 4nuto(s)"
- **3min antes:** "⚠️ O servidor será reiniciado automaticamente em 3nuto(s)"
- **2min antes:** "⚠️ O servidor será reiniciado automaticamente em 2nuto(s)"
- **1min antes:** "⚠️ O servidor será reiniciado automaticamente em1 minuto(s)"
- **No momento:** "🔄 Reiniciando servidor automaticamente!

### 2. **Validações**
- Horários devem estar no formato `HH:MM` (ex: "13:0
- Não permite horários duplicados
- Sistema funciona24por dia
- Usa timezone local do servidor

### 3**Comportamento**
- Horários se repetem diariamente
- Sistema verifica a cada minuto
- Restart automático chama o endpoint `/restart`
- Logs são salvos no arquivo JSON

---

## Exemplos de Uso

### Adicionar horário 15:00
```javascript
fetch(http://localhost:3000/api/server/schedules',[object Object]  method: POST',
  headers:[object Object]Content-Type': application/json' },
  body: JSON.stringify({ time: '150)
});
```

### Remover horário 05:00
```javascript
fetch(http://localhost:3000/api/server/schedules', {
  method: 'DELETE',
  headers:[object Object]Content-Type': application/json' },
  body: JSON.stringify({ time: '050)
});
```

### Desativar sistema
```javascript
fetch(http://localhost:3000/api/server/schedules', {
  method:PUT',
  headers:[object Object]Content-Type': application/json' },
  body: JSON.stringify({ enabled: false })
});
```

---

## Notas Importantes

1*Webhook:** As notificações são enviadas para o webhook `serverstatus` configurado
2. **Timezone:** Usa o horário local do servidor onde o backend está rodando3 **Persistência:** Configurações são salvas em `scheduled-restarts.json`4**Segurança:** Validação de formato de horário no backend
5. **Performance:** Verificação a cada minuto, não impacta performance

---

## Testes

Para testar no Postman:

1. **Listar horários:** `GET http://localhost:3000/api/server/schedules`
2*Adicionar horário:** `POST http://localhost:3000/api/server/schedules` com body `{time:14:0`
3. **Remover horário:** `DELETE http://localhost:3000/api/server/schedules` com body `{time:05:00"}`
4. **Ativar sistema:** `PUT http://localhost:3000/api/server/schedules` com body `{enabled 