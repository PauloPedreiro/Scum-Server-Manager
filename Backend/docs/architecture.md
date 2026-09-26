# 🏗️ Arquitetura do Sistema SCUM Backend

## 📋 Visão Geral

O sistema é composto por um **backend Python** distribuído para proprietários de servidores SCUM e um **frontend central** para controle e gerenciamento.

## 🎯 Arquitetura Completa

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND CENTRAL                        │
│  (Seu Servidor)                                           │
├─────────────────────────────────────────────────────────────┤
│  👤 PAINEL PROPRIETÁRIO    │  🎛️ PAINEL ADMINISTRATIVO    │
│  ├── Login/Cadastro        │  ├── Envio de Mensagens       │
│  ├── Configurações         │  ├── Notificações Globais     │
│  ├── Status do Servidor    │  ├── Análise de Dados         │
│  ├── Histórico             │  ├── Controle de Licenças     │
│  └── Atualizações          │  └── Monitoramento            │
└─────────────────────────────────────────────────────────────┘
                              ↕️ API REST
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND LOCAL                           │
│  (Servidor Proprietário)                                  │
├─────────────────────────────────────────────────────────────┤
│  🆔 Identificação Única    │  🎮 Controle do Servidor      │
│  ├── Backend ID            │  ├── Iniciar/Parar/Reiniciar  │
│  ├── Owner ID              │  ├── Agendamento              │
│  └── License Key           │  ├── Configurações            │
│                             │  └── Monitoramento            │
│  🔄 Sistema de Updates     │  🌐 Comunicação               │
│  ├── Verificação (24h)     │  ├── API Client               │
│  ├── Download              │  ├── Sincronização            │
│  ├── Instalação            │  └── Webhooks                 │
│  └── Rollback Manual       │                               │
└─────────────────────────────────────────────────────────────┘
                              ↕️ Controle Direto
┌─────────────────────────────────────────────────────────────┐
│                    SERVIDOR SCUM                           │
│  (Jogo)                                                   │
├─────────────────────────────────────────────────────────────┤
│  🎮 SCUMServer.exe        │  📊 Logs e Métricas           │
│  ├── Processo Principal    │  ├── Logs do Jogo             │
│  ├── Configurações         │  ├── Métricas de Performance  │
│  └── Dados do Jogo         │  └── Status do Servidor       │
└─────────────────────────────────────────────────────────────┘
```

## 🏗️ Estrutura do Backend

### **Estrutura de Diretórios**
```
scum_backend/
├── core/                    # Código principal
│   ├── __init__.py
│   ├── server_control/      # Controle do servidor SCUM
│   │   ├── __init__.py
│   │   ├── server_manager.py
│   │   ├── process_monitor.py
│   │   └── steamcmd_handler.py
│   ├── scheduler/           # Sistema de agendamento
│   │   ├── __init__.py
│   │   ├── task_scheduler.py
│   │   └── restart_manager.py
│   └── config/             # Sistema de configuração
│       ├── __init__.py
│       ├── config_manager.py
│       └── file_validator.py
├── communication/           # Comunicação com frontend
│   ├── __init__.py
│   ├── backend_id.py       # Identificação única
│   ├── license_validator.py # Validação de licença
│   ├── api_client.py       # Comunicação com frontend
│   └── webhook_manager.py  # Gerenciamento de webhooks
├── updates/                # Sistema de atualizações
│   ├── __init__.py
│   ├── update_manager.py   # Gerenciador de atualizações
│   ├── version_checker.py  # Verificação de versões
│   └── rollback_manager.py # Gerenciador de rollback
├── utils/                  # Utilitários gerais
│   ├── __init__.py
│   ├── logger.py
│   ├── file_utils.py
│   └── system_utils.py
├── data/                   # Dados e configurações
│   ├── config.json         # Configuração principal
│   ├── backend_id.json     # ID único do backend
│   ├── license.json        # Informações de licença
│   └── logs/              # Logs locais
├── scripts/                # Scripts Windows
│   ├── start_server.bat    # Script para iniciar servidor
│   ├── stop_server.bat     # Script para parar servidor
│   └── restart_server.ps1  # Script para reiniciar servidor
├── installer/              # Scripts de instalação
│   ├── install.bat
│   └── uninstall.bat
├── build/                  # Scripts de build
│   ├── build_exe.py
│   └── requirements.txt
├── main.py                 # Ponto de entrada
└── README.md              # Documentação
```

## 🔄 Fluxo de Comunicação

### **1. Proprietário → Backend**
```
Frontend → API → Backend → Servidor SCUM
```
- Configurações do servidor
- Comandos de controle
- Agendamentos
- Status e logs

### **2. Backend → Proprietário**
```
Backend → API → Frontend → Painel do Proprietário
```
- Status do servidor
- Logs e métricas
- Notificações
- Confirmações de comandos

### **3. Você → Todos**
```
Seu Painel Admin → API → Todos os Backends → Servidores SCUM
```
- Mensagens globais no jogo
- Notificações para proprietários
- Comandos administrativos
- Atualizações do sistema

## 🆔 Sistema de Identificação

### **Identificadores Únicos**
```python
# Cada backend terá identificação única
BACKEND_ID = "SCUM-BACKEND-{UUID}"
OWNER_ID = "OWNER-{UUID}"
LICENSE_KEY = "LIC-{UUID}-{TIMESTAMP}"
```

### **Arquivo de Identificação**
```json
{
  "backend_id": "SCUM-BACKEND-12345678-1234-1234-1234-123456789012",
  "owner_id": "OWNER-87654321-4321-4321-4321-210987654321",
  "license_key": "LIC-12345678-1234-1234-1234-123456789012-20250115",
  "created_at": "2025-01-15T10:30:00Z",
  "last_updated": "2025-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

## 🎮 Controle do Servidor SCUM

### **Scripts de Controle**
```python
# Scripts Windows para controle
scripts/
├── start_server.bat        # Iniciar servidor
├── stop_server.bat         # Parar servidor
└── restart_server.ps1      # Reiniciar servidor
```

### **Integração com SteamCMD**
```python
# Atualização automática do servidor
steamcmd_path = "C:\\Servers\\steamcmd"
install_path = "C:\\Servers\\Scum"
app_id = "3792580"  # SCUM App ID
```

### **Monitoramento de Processos**
```python
# Verificação de processos SCUMServer
def check_scum_process():
    # Verificar se SCUMServer.exe está rodando
    # Retornar PID e status
    pass
```

## ⏰ Sistema de Agendamento

### **Scheduler Base**
```python
# Sistema de agendamento
class TaskScheduler:
    def __init__(self):
        self.tasks = []
        self.running = False
        
    def add_task(self, task):
        # Adicionar tarefa agendada
        pass
        
    def start(self):
        # Iniciar scheduler
        pass
        
    def stop(self):
        # Parar scheduler
        pass
```

### **Restart Automático**
```python
# Configuração de restart automático
restart_config = {
    "enabled": True,
    "times": ["06:00", "18:00"],
    "timezone": "America/Sao_Paulo",
    "notifications": {
        "enabled": True,
        "intervals": [10, 5, 4, 3, 2, 1]  # minutos antes
    }
}
```

## 🔄 Sistema de Atualizações

### **Verificação de Atualizações**
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

### **Processo de Atualização**
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

## 🌐 API de Comunicação

### **Endpoints do Backend**
```python
# Endpoints para comunicação com frontend
API_ENDPOINTS = {
    "status": "/api/status",
    "config": "/api/config",
    "server_control": "/api/server",
    "scheduler": "/api/scheduler",
    "updates": "/api/updates",
    "logs": "/api/logs"
}
```

### **Autenticação**
```python
# Sistema de autenticação
def authenticate_request(request):
    # Verificar token de autenticação
    # Validar backend_id
    # Verificar permissões
    pass
```

## 📊 Sistema de Logs

### **Estrutura de Logs**
```python
# Sistema de logging estruturado
class Logger:
    def __init__(self):
        self.log_level = "info"
        self.log_dir = "data/logs"
        
    def log(self, level, message, data=None):
        # Log estruturado com timestamp
        pass
        
    def debug(self, message, data=None):
        # Log de debug
        pass
        
    def info(self, message, data=None):
        # Log de informação
        pass
        
    def warn(self, message, data=None):
        # Log de aviso
        pass
        
    def error(self, message, data=None):
        # Log de erro
        pass
```

## 🔧 Sistema de Configuração

### **Configuração Centralizada**
```json
{
  "server": {
    "path": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64",
    "steamcmd_path": "C:\\Servers\\steamcmd",
    "install_path": "C:\\Servers\\Scum",
    "port": 8900,
    "max_players": 100,
    "use_battleye": true
  },
  "scheduler": {
    "enabled": true,
    "restart_times": ["06:00", "18:00"],
    "timezone": "America/Sao_Paulo"
  },
  "updates": {
    "auto_update": true,
    "check_interval": 86400,
    "backup_versions": 3
  },
  "communication": {
    "frontend_url": "https://your-frontend.com",
    "api_key": "your-api-key",
    "webhook_url": "https://discord.com/api/webhooks/..."
  }
}
```

## 📦 Empacotamento

### **PyInstaller Configuration**
```python
# build_exe.py
import PyInstaller.__main__

PyInstaller.__main__.run([
    'main.py',
    '--onefile',                    # Arquivo único
    '--windowed',                   # Sem console
    '--name=SCUM_Backend',          # Nome do executável
    '--icon=icon.ico',              # Ícone
    '--add-data=scripts;scripts',   # Incluir scripts
    '--add-data=data;data',         # Incluir dados
    '--hidden-import=module_name',  # Imports ocultos
    '--clean',                      # Limpar cache
])
```

### **Estrutura do Executável**
```
scum_backend.exe
├── Dados internos:
│   ├── config.json
│   ├── backend_id.json
│   ├── scripts/
│   │   ├── start_server.bat
│   │   ├── stop_server.bat
│   │   └── restart_server.ps1
│   └── logs/
└── Funcionalidades:
    ├── Controle do servidor
    ├── Sistema de agendamento
    ├── Comunicação com frontend
    └── Sistema de atualizações
```

## 🚀 Vantagens da Arquitetura

### **Modularidade**
- ✅ Código organizado em módulos
- ✅ Fácil manutenção e extensão
- ✅ Testes unitários
- ✅ Reutilização de código

### **Escalabilidade**
- ✅ Suporte a múltiplos backends
- ✅ Comunicação assíncrona
- ✅ Sistema de filas
- ✅ Balanceamento de carga

### **Confiabilidade**
- ✅ Sistema de backup
- ✅ Rollback automático
- ✅ Monitoramento de saúde
- ✅ Recuperação de falhas

### **Segurança**
- ✅ Autenticação robusta
- ✅ Criptografia de dados
- ✅ Validação de entrada
- ✅ Logs de auditoria

---

**Última atualização**: 15/01/2025
**Versão**: 1.0.0
