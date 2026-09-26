# 📢 Sistema de Notificações In-Game - SCUM Backend

Sistema completo de notificações que aparecem diretamente no jogo SCUM, permitindo que administradores se comuniquem com os jogadores em tempo real.

## 🎯 **Visão Geral**

O sistema de notificações permite:

- **Notificações automáticas de restart** (integradas ao agendador)
- **Mensagens administrativas personalizadas** (via API)
- **Sistema de prioridades** para evitar conflitos
- **Templates configuráveis** para diferentes tipos de mensagem
- **Integração com Discord** para monitoramento

## 🏗️ **Arquitetura**

```
core/notifications/
├── notification_manager.py      # Gerenciador principal
├── scum_notifier.py            # Interface com SCUM
└── __init__.py

data/notifications/
├── templates/
│   ├── restart.json            # Template de restart
│   └── custom_messages.json    # Templates administrativos
└── config/
    └── cooldowns.json          # Configurações de cooldown
```

## 🚀 **Funcionalidades Principais**

### **1. Notificações de Restart Automáticas**
- **Integração perfeita** com o agendador
- **Notificações progressivas**: 10min, 5min, 4min, 3min, 2min, 1min antes
- **Limpeza automática** após restart
- **Prioridade máxima** (não pode ser sobrescrito)

### **2. Mensagens Administrativas**
- **7 tipos diferentes** de mensagem
- **Cores e durações** pré-configuradas
- **Templates prontos** para uso
- **API simplificada** para envio

### **3. Sistema de Prioridades**
```
Restart (100)     → Máxima prioridade
Eventos (20)      → Prioridade média  
Admin/Custom (10) → Prioridade baixa
```

### **4. Cooldowns Inteligentes**
- **Notificações personalizadas**: 30 segundos
- **Notificações de restart**: 10 minutos
- **Notificações de eventos**: 2 minutos

## 📡 **API Endpoints**

### **Status e Informações**
```bash
GET /api/notifications/status
```
Retorna status completo do sistema de notificações.

### **Envio de Mensagens**
```bash
POST /api/notifications/send
POST /api/notifications/admin/send
```

### **Gerenciamento**
```bash
POST /api/notifications/clear
GET /api/notifications/admin/templates
```

### **Restart**
```bash
POST /api/notifications/restart/create
```

## 🎨 **Tipos de Mensagens Administrativas**

| Tipo | Cor | Duração | Uso |
|------|-----|---------|-----|
| `admin_announcement` | 🟡 Amarelo | 25s | Anúncios gerais |
| `admin_warning` | 🟠 Laranja | 30s | Avisos importantes |
| `admin_info` | 🔵 Azul | 20s | Informações úteis |
| `admin_success` | 🟢 Verde | 15s | Confirmações |
| `admin_error` | 🔴 Vermelho | 25s | Problemas técnicos |
| `admin_maintenance` | 🟠 Laranja Claro | 30s | Manutenções |
| `admin_event` | 🟣 Roxo | 20s | Eventos especiais |

## 💡 **Exemplos de Uso**

### **Envio de Anúncio**
```bash
curl -X POST http://localhost:3000/api/notifications/admin/send \
  -H "Content-Type: application/json" \
  -d '{
    "type": "admin_announcement",
    "message": "Novo evento especial iniciado!"
  }'
```

### **Aviso de Manutenção**
```bash
curl -X POST http://localhost:3000/api/notifications/admin/send \
  -H "Content-Type: application/json" \
  -d '{
    "type": "admin_warning",
    "message": "Manutenção em 30 minutos!"
  }'
```

### **Informação Útil**
```bash
curl -X POST http://localhost:3000/api/notifications/admin/send \
  -H "Content-Type: application/json" \
  -d '{
    "type": "admin_info",
    "message": "Dicas no Discord!"
  }'
```

## ⚙️ **Configuração**

### **Arquivo Principal: `data/config.json`**
```json
{
  "notifications": {
    "enabled": true,
    "check_interval": 30000,
    "restart_protection_window": 15,
    "scum_config_path": "C:/Servers/Scum/SCUM/Saved/Config/WindowsServer",
    "notifications_file": "Notifications.json",
    "max_notifications_per_hour": 20,
    "auto_cleanup_days": 30,
    "discord_offset": {
      "enabled": true,
      "seconds": 120
    }
  }
}
```

### **Templates: `data/notifications/templates/`**
- **`restart.json`** - Template para notificações de restart
- **`custom_messages.json`** - Templates para mensagens administrativas

## 🔄 **Fluxo de Funcionamento**

### **Notificações de Restart**
1. **Agendador** detecta próximo restart
2. **NotificationManager** cria notificações progressivas
3. **SCUMNotifier** salva no arquivo do SCUM
4. **Jogadores** veem notificações no jogo
5. **Sistema** limpa notificações após restart

### **Mensagens Administrativas**
1. **Administrador** envia via API
2. **Sistema** verifica cooldown e prioridades
3. **Template** aplica cor e duração apropriadas
4. **SCUMNotifier** salva no arquivo do SCUM
5. **Jogadores** veem mensagem em 2 minutos

## 🛡️ **Proteções e Validações**

### **Sistema de Prioridades**
- Notificações de restart **nunca** são sobrescritas
- Mensagens administrativas são bloqueadas se há restart ativo
- Sistema informa quando há conflito de prioridade

### **Cooldowns**
- Previne spam de notificações
- Tempos diferentes para cada tipo
- Registro automático de última mensagem enviada

### **Validações**
- Mensagem obrigatória para envio
- Verificação de tipos válidos
- Fallback para configurações padrão

## 📊 **Monitoramento**

### **Status do Sistema**
```bash
curl http://localhost:3000/api/notifications/status
```

### **Logs**
Todas as operações são registradas em:
- `data/logs/scum_backend.log`
- Logs estruturados em JSON
- Níveis: INFO, WARNING, ERROR

### **Arquivo do SCUM**
Notificações ativas em:
```
C:\Servers\Scum\SCUM\Saved\Config\WindowsServer\Notifications.json
```

## 🚨 **Solução de Problemas**

### **"Cooldown ativo"**
- **Causa:** Tempo insuficiente desde última mensagem
- **Solução:** Aguardar cooldown (30s para admin)

### **"Prioridade insuficiente"**
- **Causa:** Há notificações de restart ativas
- **Solução:** Aguardar restart ou limpar notificações

### **"Template não encontrado"**
- **Causa:** Arquivo de template corrompido ou ausente
- **Solução:** Verificar arquivos em `data/notifications/templates/`

### **"Arquivo do SCUM não encontrado"**
- **Causa:** Caminho incorreto no config
- **Solução:** Verificar `scum_config_path` em `config.json`

## 🔗 **Integração com Outros Sistemas**

### **Discord Webhooks**
- Notificações automáticas para Discord
- Eventos: restart, admin messages, erros
- Rate limiting e retry automático

### **Agendador de Restart**
- Integração nativa com `RestartScheduler`
- Notificações automáticas antes de cada restart
- Limpeza automática após restart

### **Sistema de Logs**
- Todas as operações registradas
- Logs estruturados para análise
- Integração com `StructuredLogger`

## 📚 **Documentação Relacionada**

- [📡 Sistema de Webhooks](./webhooks/README.md)
- [📅 Agendador de Restart](../scheduler/README.md)
- [🌐 API Endpoints](../endpoints/README.md)
- [📢 Exemplos de Uso](./admin-examples.md)

---

**O sistema de notificações está 100% funcional e pronto para uso!** 🎉
