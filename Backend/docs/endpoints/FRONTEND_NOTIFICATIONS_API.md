## Documentação Sistema de Notificações (Frontend)

### Visão Geral
- **Objetivo**: permitir que o frontend monitore e dispare notificações in-game do SSM 3.0 com segurança.
- **Componente principal**: painel de notificações (dashboard/admin) consumindo os endpoints descritos abaixo.
- **Formato**: todas as requisições são JSON (`Content-Type: application/json`).
- **Cooldowns**: o backend controla automaticamente proteção contra spam e janela de reinício; utilize os endpoints de status/cooldown para feedback ao usuário.

---

### 1. `GET /api/notifications/status`
| Método | URL | Autenticação | Cache |
| --- | --- | --- | --- |
| `GET` | `/api/notifications/status` | não | 5 s |

**Uso**
- Carregar na abertura da tela e atualizar via polling (ex.: 5–10 s).
- Exibir flags como “Sistema ativo”, “Cooldown em curso”, “Última notificação enviada”.

**Resposta (`200 OK`)**
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "is_running": false,
    "check_interval": 30000,
    "restart_protection_window": 15,
    "last_restart_notifications": "21:00",
    "cooldowns": {
      "cooldowns": {
        "restart": 600,
        "custom": 30,
        "events": 120
      },
      "last_sent": {
        "restart": "2025-10-16T20:16:57.996991",
        "custom": null,
        "events": null
      }
    },
    "scum_notifier": {
      "enabled": true,
      "notifications_file_exists": true,
      "current_notifications_count": 0,
      "highest_priority": 0
    }
  },
  "timestamp": 1760656651
}
```

**Frontend**
- Mostrar status geral (ligado/desligado).
- Exibir contadores de cooldown e tempo desde a última notificação.
- Permitir botão “Resetar cooldowns” apenas se `cooldowns.cooldowns.* > 0`.

---

### 2. `POST /api/notifications/send`
| Método | URL | Autenticação | Cache |
| --- | --- | --- | --- |
| `POST` | `/api/notifications/send` | não | n/a |

**Objetivo**: enviar notificação personalizada (texto livre). Ideal para avisos rápidos.

**Body exemplo**
```json
{
  "message": "Servidor será reiniciado em 15 minutos",
  "duration": 15,
  "color": "255-255-255"
}
```

**Resposta (`200 OK`)**
```json
{
  "success": true,
  "message": "Notificação enviada com sucesso",
  "data": {
    "message": "Servidor será reiniciado em 15 minutos",
    "color": "255-255-255",
    "duration": 15,
    "time": "00:44",
    "path": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\Notifications.json"
  }
}
```

**Frontend**
- Validar campos obrigatórios: `message` (string), `duration` (int > 0), `color` formato `R-G-B`.
- Mostrar aviso se `success` for `false` (possível cooldown ativo).
- Após envio, atualizar status (`GET /status`).

---

### 3. `POST /api/notifications/admin/send`
| Método | URL |
| --- | --- |
| `POST` | `/api/notifications/admin/send` |

**Objetivo**: enviar alertas com base em templates pré-configurados.

**Body exemplo**
```json
{
  "type": "admin_announcement",
  "message": "Evento especial iniciado!"
}
```

**Parâmetros opcionais**
- `granted_by` / `notes`: texto livre registrado no histórico.

**Resposta (`200 OK`)**
Retorna dados da notificação aplicada e sinaliza se o arquivo `.ini` foi atualizado (quando aplicável).

**Frontend**
- Montar um dropdown usando `/api/notifications/admin/templates` para listar tipos e descrições.
- Exibir mensagem de erro quando `success=false` (ex.: cooldown ativo).
- Atualizar status após cada envio.

---

### 4. `GET /api/notifications/admin/templates`
| Método | URL |
| --- | --- |
| `GET` | `/api/notifications/admin/templates` |

**Uso**
- Carregar na abertura da tela de notificações administrativas.
- Exibir lista com: `type`, `description`, `color`, `duration`, exemplos.

**Resposta (`200 OK`)**
```json
{
  "success": true,
  "data": {
    "name": "admin_messages",
    "description": "Template para mensagens administrativas",
    "version": "1.0",
    "admin_message_types": [
      {
        "type": "admin_announcement",
        "description": "Anúncios gerais",
        "color": "255-255-100",
        "duration": 25,
        "examples": ["Novo evento especial iniciado!", "Regras atualizadas"]
      }
    ]
  }
}
```

**Frontend**
- Popular UI com esses valores; bloquear envio se `type` não for selecionado.

---

### 5. `POST /api/notifications/clear`
| Método | URL |
| --- | --- |
| `POST` | `/api/notifications/clear` |

**Objetivo**: limpar todas as notificações pendentes.

**Resposta (`200 OK`)**
```json
{ "success": true }
```

**Frontend**
- Ação deve exibir confirmação (“Tem certeza?”). 
- Após confirmar, chamar endpoint e recarregar status.

---

### 6. `POST /api/notifications/cooldowns/reset`
| Método | URL |
| --- | --- |
| `POST` | `/api/notifications/cooldowns/reset` |

**Objetivo**: zera os cooldowns (`restart`, `custom`, `events`).

**Resposta (`200 OK`)**
```json
{
  "success": true,
  "message": "Cooldowns resetados com sucesso",
  "cooldowns": {
    "cooldowns": {
      "restart": 600,
      "custom": 30,
      "events": 120
    },
    "last_sent": {
      "restart": null,
      "custom": null,
      "events": null
    }
  }
}
```

**Frontend**
- Mostrar feedback (“Cooldowns zerados”).
- Atualizar painel de status em seguida.

---

### 7. `POST /api/notifications/restart/create`
| Método | URL |
| --- | --- |
| `POST` | `/api/notifications/restart/create` |

**Objetivo**: gerar automaticamente notificações de restart para um horário/data.

**Body exemplo**
```json
{
  "restart_time": "21:00",
  "restart_date": "2025-10-16"
}
```

**Resposta (`200 OK`)**
```json
{
  "success": true,
  "count": 6,
  "priority": 100,
  "path": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\Notifications.json"
}
```

**Frontend**
- Formular inputs para data/hora (validar formato 24h).
- Após chamada, avisar usuário da quantidade de notificações criadas e sugerir visualizar status.

---

### Fluxo Sugerido para o Frontend
1. **Carregar status** (`GET /status`) ao abrir a página.
2. **Listar templates** (`GET /admin/templates`) para preencher dropdowns.
3. Expor ações:
   - Envio rápido (`POST /send`).
   - Envio administrativo (`POST /admin/send`).
   - Limpeza (`POST /clear`).
   - Reset cooldown (`POST /cooldowns/reset`).
   - Criar notificações de restart (`POST /restart/create`).
4. A cada ação bem-sucedida, disparar novo `GET /status`.
5. Exibir mensagens de erro retornadas (`success=false`) em diálogos ou toasts.

---

### Checklist Frontend
- [ ] Respeita cooldowns: bloqueia botão se `status` indicar cooldown ativo.
- [ ] Valida dados antes das chamadas (`message`, `duration`, `color`, `restart_time`, etc.).
- [ ] Atualiza painel de status após cada operação.
- [ ] Loga erros (`error` retornado pela API) e mostra feedback ao usuário.
- [ ] Protege ações sensíveis com confirmação (limpar notificações / reset cooldown / criar restart).

---

### Histórico
- **11/11/2025**: documentação consolidada para handoff ao frontend.

> Em caso de novas categorias de template ou mudanças no arquivo `Notifications.json`, alinhar previamente com o backend para manter compatibilidade.
