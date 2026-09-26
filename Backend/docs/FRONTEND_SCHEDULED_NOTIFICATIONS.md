# 📚 Scheduled Notifications (Frontend) - API de Notificações Programadas

Esta documentação é destinada ao desenvolvedor do frontend para integração com o sistema de **Scheduled Notifications** (notificações customizadas programadas) e sua compilação para o arquivo do SCUM `Notifications.json`.

---

## 🎯 Objetivo do Sistema

- Permitir que o admin crie **notificações customizadas programadas** (persistentes).
- Garantir robustez do `Notifications.json` do SCUM:
  - Notificações de **restart** (do dia) são sempre recompiladas/garantidas.
  - Customs são inseridas apenas se **não** conflitam com a janela reservada do restart.
- Bloquear (HTTP **409**) qualquer custom cujo horário caia em uma janela reservada.

---

## 🕒 Regra de Conflito (Janela Reservada do Restart)

Existe uma janela reservada ao redor de cada restart agendado:

- **Início da janela (inclusive):** `restart_time - 15 minutos`
- **Fim da janela (inclusive):** `restart_time + 5 minutos`

Se uma notificação custom (ocorrência) cair dentro dessa janela, o backend responde com:

- HTTP **409 Conflict**
- `error_code: "SCHEDULE_TIME_RESERVED_BY_RESTART"`

O frontend deve tratar esse caso mostrando ao usuário uma mensagem clara para escolher outro horário.

---

## 🔗 Base URL

Exemplos em dev:

```text
http://localhost:3000
```

---

## 📦 Modelo de Dados

### ScheduledNotification (objeto persistido)
Campos retornados pelo backend (store):

- `id` (string)
- `enabled` (boolean)
- `title` (string) (opcional, pode ser vazio)
- `message` (string) (**obrigatório**)
- `color` (string) padrão: `"255-255-255"`
- `duration` (number) em minutos, padrão: `15`
- `schedule` (object) (**obrigatório**)
- `created_at` (string ISO)
- `updated_at` (string ISO)

### Schedule (tipos suportados)

#### 1) `once`
Dispara uma única vez em um datetime específico.

```json
{
  "type": "once",
  "datetime": "2026-03-08T00:20:00"
}
```

#### 2) `daily`
Dispara diariamente no horário `HH:MM`.

```json
{
  "type": "daily",
  "time": "00:20"
}
```

#### 3) `relative_to_restart`
Dispara relativo ao horário de restart do scheduler.

- `offset_minutes` (inteiro)
  - Ex.: `-30` = 30 min antes do restart
  - Ex.: `+10` = 10 min depois do restart

```json
{
  "type": "relative_to_restart",
  "offset_minutes": -30
}
```

---

## 📡 Endpoints Disponíveis

### 1) Listar notificações programadas

**GET** `/api/notifications/scheduled`

#### Resposta (200)
```json
{
  "success": true,
  "items": [
    {
      "id": "...",
      "enabled": true,
      "title": "...",
      "message": "...",
      "color": "255-255-255",
      "duration": 15,
      "schedule": { "type": "daily", "time": "00:20" },
      "created_at": "2026-03-08T16:00:00.000000",
      "updated_at": "2026-03-08T16:00:00.000000"
    }
  ],
  "timestamp": 1772998656.6624885
}
```

---

### 2) Obter notificação programada por ID

**GET** `/api/notifications/scheduled/<item_id>`

#### Resposta (200)
```json
{
  "success": true,
  "item": { "id": "..." },
  "timestamp": 1772998656.6624885
}
```

#### Resposta (404)
```json
{
  "success": false,
  "error": "Not found"
}
```

---

### 3) Validar payload (sem salvar)

**POST** `/api/notifications/scheduled/validate`

Use este endpoint para validar antes de habilitar o botão "Salvar" no frontend.

#### Body (exemplo)
```json
{
  "enabled": true,
  "title": "Aviso",
  "message": "Mensagem exemplo",
  "color": "255-255-255",
  "duration": 15,
  "schedule": { "type": "daily", "time": "00:20" }
}
```

#### Resposta (200)
```json
{
  "success": true,
  "timestamp": 1772998656.6624885
}
```

#### Resposta (409) - Conflito com janela de restart
```json
{
  "success": false,
  "error_code": "SCHEDULE_TIME_RESERVED_BY_RESTART",
  "message": "Esse horario esta reservado para mensagens de restart. Escolha outro horario.",
  "details": {
    "requested_time": "2026-03-08T18:45:00",
    "conflicting_restart_time": "19:00",
    "reserved_window_start": "2026-03-08T18:45:00",
    "reserved_window_end": "2026-03-08T19:05:00",
    "reserved_before_minutes": 15,
    "reserved_after_minutes": 5
  }
}
```

#### Resposta (400) - Erro de validação
```json
{
  "success": false,
  "error": "message is required"
}
```

---

### 4) Criar notificação programada (persistente)

**POST** `/api/notifications/scheduled`

#### Body (exemplo)
```json
{
  "enabled": true,
  "title": "Aviso",
  "message": "Mensagem exemplo",
  "color": "255-255-255",
  "duration": 15,
  "schedule": { "type": "daily", "time": "00:20" }
}
```

#### Resposta (200)
Observação: ao criar, o backend automaticamente recompila o `Notifications.json` do SCUM.

```json
{
  "success": true,
  "item": { "id": "..." },
  "compile": {
    "success": true,
    "count": 36,
    "restart_count": 36,
    "custom_count": 0,
    "path": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\Notifications.json"
  },
  "timestamp": 1772998656.6624885
}
```

#### Respostas de erro
- HTTP **409**: mesmo payload do `validate` quando conflitar
- HTTP **400**: `{"success": false, "error": "..."}`

---

### 5) Atualizar notificação programada

**PUT** `/api/notifications/scheduled/<item_id>`

- Você pode enviar um payload parcial, mas recomenda-se enviar o objeto completo no frontend.
- O backend recompila o `Notifications.json` automaticamente após atualizar.

#### Resposta (200)
Mesmo formato do create (retorna `item` + `compile`).

#### Resposta (404)
```json
{
  "success": false,
  "error": "Not found"
}
```

#### Resposta (409)
Conflito de janela reservada (mesmo payload do `validate`).

---

### 6) Remover notificação programada

**DELETE** `/api/notifications/scheduled/<item_id>`

O backend recompila o `Notifications.json` automaticamente após remover.

#### Resposta (200)
```json
{
  "success": true,
  "deleted": true,
  "compile": {
    "success": true,
    "count": 36,
    "restart_count": 36,
    "custom_count": 0,
    "path": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\Notifications.json"
  },
  "timestamp": 1772998656.6624885
}
```

#### Resposta (404)
```json
{
  "success": false,
  "error": "Not found"
}
```

---

### 7) Forçar compilação do `Notifications.json`

**POST** `/api/notifications/compile`

Força recompilação do arquivo do SCUM juntando:
- Notificações de restart do dia
- Customs válidas (próximas 24h)

#### Resposta (200)
```json
{
  "success": true,
  "count": 36,
  "restart_count": 36,
  "custom_count": 0,
  "path": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\Notifications.json"
}
```

---

## 🧭 Fluxo Recomendado no Frontend

- **1) Listar**
  - `GET /api/notifications/scheduled`

- **2) Criar/Editar (UI)**
  - Ao alterar campos, opcionalmente chamar `POST /api/notifications/scheduled/validate`
  - Se retornar **409**, bloquear salvar e exibir `message` + sugerir outro horário

- **3) Salvar**
  - Create: `POST /api/notifications/scheduled`
  - Update: `PUT /api/notifications/scheduled/<id>`

- **4) Após salvar/remover**
  - Você já recebe `compile` na resposta.
  - Pode atualizar UI/estado com o novo resultado (ex.: exibir `custom_count`).

---

## 🧩 Tipos TypeScript (sugestão)

```ts
export type ScheduleOnce = {
  type: 'once';
  datetime: string; // ISO string
};

export type ScheduleDaily = {
  type: 'daily';
  time: string; // HH:MM
};

export type ScheduleRelativeToRestart = {
  type: 'relative_to_restart';
  offset_minutes: number; // integer
};

export type Schedule = ScheduleOnce | ScheduleDaily | ScheduleRelativeToRestart;

export type ScheduledNotification = {
  id: string;
  enabled: boolean;
  title: string;
  message: string;
  color: string; // ex: "255-255-255"
  duration: number; // minutes
  schedule: Schedule;
  created_at?: string;
  updated_at?: string;
};

export type CompileResult = {
  success: boolean;
  count?: number;
  restart_count?: number;
  custom_count?: number;
  path?: string;
  error?: string;
};

export type ReservedWindowConflict = {
  success: false;
  error_code: 'SCHEDULE_TIME_RESERVED_BY_RESTART';
  message: string;
  details: {
    requested_time: string;
    conflicting_restart_time: string; // HH:MM
    reserved_window_start: string; // ISO
    reserved_window_end: string; // ISO
    reserved_before_minutes: number;
    reserved_after_minutes: number;
  };
};
```

---

## 🧪 Observações para Debug

- Se `POST /api/notifications/scheduled` retornar sucesso, mas a custom não aparecer no SCUM:
  - Verifique o campo `compile` na resposta.
  - Verifique se a notificação não foi filtrada por cair na janela reservada.

---

## 📞 Suporte

Em caso de dúvidas sobre payloads, conflitos ou comportamento de compilação, chame o time de backend.
