# 🔄 Sistema de Atualizações SCUM Backend

## 📋 Visão Geral

Sistema robusto de atualizações automáticas para o backend SCUM, com controle do proprietário e rollback manual.

## 🎯 Configurações Definidas

- **Frequência de verificação**: 24 horas
- **Tipo de atualização**: Obrigatória (proprietário escolhe quando)
- **Sistema de rollback**: Manual
- **Notificações**: Painel + Discord

## 🏗️ Arquitetura do Sistema

### **Servidor Central (Seu Servidor)**
```
┌─────────────────────────────────────────────────────────────┐
│                    SERVIDOR CENTRAL                        │
├─────────────────────────────────────────────────────────────┤
│  📦 REPOSITÓRIO DE VERSÕES    │  🔄 API DE ATUALIZAÇÕES    │
│  ├── Versão 1.0.0             │  ├── Check de versão        │
│  ├── Versão 1.1.0             │  ├── Download de arquivos   │
│  ├── Versão 1.2.0             │  ├── Validação de integridade│
│  └── Versão 2.0.0             │  └── Logs de atualização    │
└─────────────────────────────────────────────────────────────┘
```

### **Backend Local (Proprietário)**
```
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND LOCAL                           │
├─────────────────────────────────────────────────────────────┤
│  🔍 VERIFICADOR              │  📥 ATUALIZADOR             │
│  ├── Check automático (24h)  │  ├── Download de nova versão│
│  ├── Comparação de versões   │  ├── Backup da versão atual │
│  └── Notificação             │  ├── Instalação             │
│                               │  └── Restart do serviço    │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Fluxo de Atualização

### **1. Verificação Automática**
```python
# Backend verifica a cada 24 horas
def check_for_updates():
    current_version = get_current_version()
    latest_version = get_latest_version_from_server()
    
    if latest_version > current_version:
        notify_update_available(latest_version)
        return True
    return False
```

### **2. Processo de Atualização**
```python
# Processo completo de atualização
def update_backend():
    # 1. Verificar nova versão
    new_version = get_latest_version()
    
    # 2. Fazer backup da versão atual
    backup_current_version()
    
    # 3. Download da nova versão
    download_new_version(new_version)
    
    # 4. Validar integridade
    validate_download()
    
    # 5. Parar serviços
    stop_backend_services()
    
    # 6. Substituir arquivos
    replace_files()
    
    # 7. Reiniciar serviços
    restart_backend_services()
    
    # 8. Confirmar atualização
    confirm_update_success()
```

## 🎛️ Controle do Proprietário

### **Opções de Atualização**
```python
# Configurações do proprietário
update_preferences = {
    "auto_update": True,           # Atualização automática
    "check_interval": 86400,       # 24 horas (86400 segundos)
    "force_update": True,          # Atualização obrigatória
    "notify_discord": True,        # Notificar no Discord
    "notify_panel": True,          # Notificar no painel
    "backup_versions": 3           # Manter 3 backups
}
```

### **Interface do Painel**
```python
# Seção de Atualizações no Painel
┌─────────────────────────────────────────────────────────────┐
│                    ATUALIZAÇÕES                            │
├─────────────────────────────────────────────────────────────┤
│  📦 Versão Atual: 1.2.0                                    │
│  🔄 Nova Versão: 1.3.0 (Disponível)                       │
│  ⚠️  Atualização Obrigatória                               │
│                                                             │
│  🎛️ Opções:                                                │
│  ☑️ Atualizar Automaticamente                              │
│  ☑️ Notificar no Discord                                   │
│  ☑️ Notificar no Painel                                    │
│                                                             │
│  📋 Changelog:                                             │
│  • Correção de bugs críticos                               │
│  • Nova funcionalidade X                                   │
│  • Melhorias de performance                                │
│                                                             │
│  [🔄 Atualizar Agora] [⏰ Agendar] [❌ Cancelar]          │
└─────────────────────────────────────────────────────────────┘
```

## 🤖 Notificações Discord

### **Embed de Atualização**
```python
# Notificação Discord
embed = {
    "title": "🔄 Nova Atualização Disponível",
    "description": "**Versão 1.3.0** está disponível para seu servidor",
    "color": 0xffaa00,
    "fields": [
        {
            "name": "📦 Versão Atual",
            "value": "1.2.0",
            "inline": True
        },
        {
            "name": "🆕 Nova Versão",
            "value": "1.3.0",
            "inline": True
        },
        {
            "name": "⚠️ Tipo",
            "value": "Atualização Obrigatória",
            "inline": True
        },
        {
            "name": "📋 Principais Mudanças",
            "value": "• Correção de bugs críticos\n• Nova funcionalidade X\n• Melhorias de performance"
        }
    ],
    "footer": {
        "text": "Acesse o painel para atualizar"
    }
}
```

## 🔄 Cenários de Atualização

### **Cenário 1: Atualização Automática Habilitada**
```
1. Backend verifica (24h) → Nova versão encontrada
2. Notifica Discord + Painel
3. Aguarda 1 hora para proprietário cancelar
4. Se não cancelar → Atualização automática
5. Backup → Download → Instalação → Restart
6. Confirmação para servidor central
7. Notificação de sucesso
```

### **Cenário 2: Atualização Manual**
```
1. Backend verifica (24h) → Nova versão encontrada
2. Notifica Discord + Painel
3. Proprietário acessa painel
4. Clica "Atualizar Agora"
5. Backup → Download → Instalação → Restart
6. Confirmação para servidor central
7. Notificação de sucesso
```

### **Cenário 3: Agendamento**
```
1. Backend verifica (24h) → Nova versão encontrada
2. Notifica Discord + Painel
3. Proprietário agenda para horário específico
4. Sistema aguarda horário agendado
5. Executa atualização no horário
6. Confirmação para servidor central
7. Notificação de sucesso
```

## 🛠️ Sistema de Rollback Manual

### **Controle no Painel**
```python
# Seção de Rollback
┌─────────────────────────────────────────────────────────────┐
│                    ROLLBACK                                │
├─────────────────────────────────────────────────────────────┤
│  ⚠️  Apenas use em caso de problemas                       │
│                                                             │
│  📦 Versões Disponíveis:                                   │
│  ☑️ 1.3.0 (Atual) - 15/01/2025 14:30                     │
│  ☐ 1.2.0 (Backup) - 10/01/2025 09:15                     │
│  ☐ 1.1.0 (Backup) - 05/01/2025 16:45                     │
│                                                             │
│  ⚠️  Aviso: Rollback irá parar o servidor temporariamente  │
│                                                             │
│  [🔄 Fazer Rollback] [❌ Cancelar]                        │
└─────────────────────────────────────────────────────────────┘
```

### **Processo de Rollback**
```python
def manual_rollback(target_version):
    # 1. Parar serviços
    stop_backend_services()
    
    # 2. Restaurar backup
    restore_backup(target_version)
    
    # 3. Validar restauração
    validate_restoration()
    
    # 4. Reiniciar serviços
    restart_backend_services()
    
    # 5. Confirmar rollback
    confirm_rollback_success()
    
    # 6. Notificar proprietário
    notify_rollback_complete()
```

## 📊 Monitoramento de Atualizações

### **Painel Administrativo**
```python
# Dashboard de atualizações
┌─────────────────────────────────────────────────────────────┐
│                DASHBOARD DE ATUALIZAÇÕES                   │
├─────────────────────────────────────────────────────────────┤
│  📊 Estatísticas:                                          │
│  • Total de Backends: 150                                  │
│  • Atualizados: 120 (80%)                                  │
│  • Pendentes: 25 (17%)                                     │
│  • Falhas: 5 (3%)                                          │
│                                                             │
│  📋 Versões em Uso:                                        │
│  • 1.3.0: 120 backends                                     │
│  • 1.2.0: 25 backends                                      │
│  • 1.1.0: 5 backends                                       │
│                                                             │
│  🔄 Ações:                                                 │
│  [📤 Upload Nova Versão] [📊 Relatório] [🔔 Notificar]    │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Implementação Técnica

### **API de Atualizações**
```python
# Endpoints para atualizações
GET /api/updates/check/{backend_id}
POST /api/updates/download/{version}
GET /api/updates/version/{version}/info
POST /api/updates/confirm/{backend_id}
```

### **Sistema de Versões**
```python
# Controle de versão semântico
version = "1.2.3"
# 1 = Major (mudanças grandes)
# 2 = Minor (novas funcionalidades)
# 3 = Patch (correções)

# Comparação de versões
def compare_versions(v1, v2):
    return v1 < v2  # True se v1 é menor que v2
```

### **Sistema de Backup**
```python
# Backup antes da atualização
def backup_before_update():
    # Backup da versão atual
    backup_dir = f"backup_{current_version}_{timestamp}"
    copy_files(current_files, backup_dir)
    
    # Backup de configurações
    backup_config()
    
    # Backup de dados
    backup_data()
```

## 📁 Estrutura de Arquivos

### **Repositório de Versões**
```
updates/
├── versions/
│   ├── 1.0.0/
│   │   ├── scum_backend.exe
│   │   ├── changelog.md
│   │   └── checksum.txt
│   ├── 1.1.0/
│   │   ├── scum_backend.exe
│   │   ├── changelog.md
│   │   └── checksum.txt
│   └── 1.2.0/
│       ├── scum_backend.exe
│       ├── changelog.md
│       └── checksum.txt
├── api/
│   ├── check_version.php
│   ├── download_version.php
│   └── confirm_update.php
└── logs/
    └── update_logs.json
```

## 🚀 Módulo de Atualizações

### **UpdateManager**
```python
# update_manager.py
class UpdateManager:
    def __init__(self):
        self.check_interval = 86400  # 24 horas
        self.auto_update = True
        self.backup_versions = 3
        
    def check_for_updates(self):
        # Verificar nova versão no servidor
        pass
        
    def download_update(self, version):
        # Download da nova versão
        pass
        
    def install_update(self, version):
        # Instalação da nova versão
        pass
        
    def rollback(self, target_version):
        # Rollback manual
        pass
```

### **VersionChecker**
```python
# version_checker.py
class VersionChecker:
    def __init__(self):
        self.server_url = "https://your-server.com/api"
        
    def get_current_version(self):
        # Obter versão atual
        pass
        
    def get_latest_version(self):
        # Obter versão mais recente
        pass
        
    def compare_versions(self, v1, v2):
        # Comparar versões
        pass
```

## 🎯 Vantagens do Sistema

### **Para o Proprietário:**
- ✅ **Controle total** sobre quando atualizar
- ✅ **Notificações claras** no Discord e painel
- ✅ **Rollback manual** em caso de problemas
- ✅ **Backup automático** antes de atualizar
- ✅ **Agendamento** de atualizações

### **Para Você (Dono da Plataforma):**
- ✅ **Controle centralizado** das versões
- ✅ **Atualizações obrigatórias** para correções críticas
- ✅ **Monitoramento** de adoção de versões
- ✅ **Rollback** em caso de problemas
- ✅ **Estatísticas** de atualizações

## 🔄 Fluxo de Implementação

### **1. Verificação de Atualizações**
```python
# Verificação automática a cada 24 horas
def check_for_updates():
    current_version = get_current_version()
    latest_version = get_latest_version_from_server()
    
    if latest_version > current_version:
        notify_update_available(latest_version)
        return True
    return False
```

### **2. Notificação do Proprietário**
```python
# Notificar proprietário
def notify_update_available(version):
    # Notificar no Discord
    send_discord_notification(version)
    
    # Notificar no painel
    send_panel_notification(version)
    
    # Aguardar resposta do proprietário
    wait_for_owner_response()
```

### **3. Execução da Atualização**
```python
# Executar atualização
def execute_update(version):
    # Backup
    backup_current_version()
    
    # Download
    download_new_version(version)
    
    # Instalação
    install_new_version(version)
    
    # Confirmação
    confirm_update_success()
```

---

**Última atualização**: 15/01/2025
**Versão**: 1.0.0
