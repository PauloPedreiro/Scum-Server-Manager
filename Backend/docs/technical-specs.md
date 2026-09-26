# 🔧 Especificações Técnicas SCUM Backend

## 📋 Visão Geral

Especificações técnicas detalhadas para implementação do backend SCUM, incluindo tecnologias, dependências, configurações e padrões de desenvolvimento.

## 🛠️ Stack Tecnológico

### **Linguagem Principal**
- **Python 3.9+** - Linguagem principal do backend

### **Dependências Principais**
```python
# requirements.txt
requests>=2.28.0          # Comunicação HTTP
psutil>=5.9.0            # Monitoramento de processos
schedule>=1.2.0          # Agendamento
python-dotenv>=0.19.0    # Variáveis de ambiente
PyInstaller>=5.0.0       # Empacotamento
```

### **Ferramentas de Desenvolvimento**
- **Git** - Controle de versão
- **PyInstaller** - Empacotamento para .exe
- **pytest** - Testes unitários
- **black** - Formatação de código
- **flake8** - Linting

## 🏗️ Arquitetura Técnica

### **Padrão de Arquitetura**
- **Modular** - Código organizado em módulos
- **Singleton** - Instâncias únicas de gerenciadores
- **Observer** - Sistema de notificações
- **Factory** - Criação de objetos

### **Estrutura de Módulos**
```python
# Estrutura modular
core/
├── server_control/      # Controle do servidor
├── scheduler/           # Sistema de agendamento
└── config/             # Configuração

communication/
├── api_client.py       # Cliente HTTP
├── webhook_manager.py  # Gerenciamento de webhooks
└── auth_manager.py     # Autenticação

updates/
├── update_manager.py   # Gerenciador de atualizações
├── version_checker.py  # Verificação de versões
└── rollback_manager.py # Gerenciador de rollback
```

## 🔧 Configurações Técnicas

### **Configuração Principal**
```json
{
  "server": {
    "path": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64",
    "steamcmd_path": "C:\\Servers\\steamcmd",
    "install_path": "C:\\Servers\\Scum",
    "port": 8900,
    "max_players": 100,
    "use_battleye": true,
    "auto_restart": false,
    "restart_interval": 3600000
  },
  "scheduler": {
    "enabled": true,
    "interval": 30000,
    "restart_times": ["06:00", "18:00"],
    "timezone": "America/Sao_Paulo",
    "notifications": {
      "enabled": true,
      "intervals": [10, 5, 4, 3, 2, 1]
    }
  },
  "updates": {
    "enabled": true,
    "auto_update": true,
    "check_interval": 86400,
    "backup_versions": 3,
    "force_update": true,
    "notify_discord": true,
    "notify_panel": true
  },
  "communication": {
    "frontend_url": "https://your-frontend.com",
    "api_key": "your-api-key",
    "webhook_url": "https://discord.com/api/webhooks/...",
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 5000
  },
  "logging": {
    "level": "info",
    "max_size": "10MB",
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

### **Configuração de Identificação**
```json
{
  "backend_id": "SCUM-BACKEND-12345678-1234-1234-1234-123456789012",
  "owner_id": "OWNER-87654321-4321-4321-4321-210987654321",
  "license_key": "LIC-12345678-1234-1234-1234-123456789012-20250115",
  "created_at": "2025-01-15T10:30:00Z",
  "last_updated": "2025-01-15T10:30:00Z",
  "version": "1.0.0",
  "status": "active"
}
```

## 🎮 Controle do Servidor SCUM

### **Scripts de Controle**

#### **Script PowerShell para Reiniciar**
```powershell
# restart_server.ps1
param(
    [string]$ConfigPath = "config.json"
)

# Carregar configuração
$config = Get-Content $ConfigPath | ConvertFrom-Json

# Parar processos existentes
Get-Process -Name "SCUMServer" -ErrorAction SilentlyContinue | Stop-Process -Force

# Aguardar parada
Start-Sleep -Seconds 5

# Iniciar servidor
$serverPath = $config.server.path
$port = $config.server.port
$maxPlayers = $config.server.max_players
$useBattleye = $config.server.use_battleye

Set-Location $serverPath

$args = @("-log", "-port=$port")
if ($maxPlayers) { $args += "-MaxPlayers=$maxPlayers" }
if (-not $useBattleye) { $args += "-nobattleye" }

Start-Process -FilePath "SCUMServer.exe" -ArgumentList $args -WindowStyle Normal
```

#### **Script Batch para Parar**
```batch
@echo off
echo Parando servidor SCUM...

:: Parar todas as instâncias
taskkill /IM SCUMServer.exe /T /F >nul 2>&1

:: Verificar se parou
timeout /t 5 /nobreak >nul
tasklist /FI "IMAGENAME eq SCUMServer.exe" 2>nul | find /I /N "SCUMServer.exe" >nul
if "%ERRORLEVEL%"=="0" (
    echo ERRO: Nao foi possivel parar o servidor
    exit /b 1
) else (
    echo Servidor parado com sucesso
    exit /b 0
)
```

#### **Script Batch para Iniciar**
```batch
@echo off
echo Iniciando servidor SCUM...

:: Verificar se já está rodando
tasklist /FI "IMAGENAME eq SCUMServer.exe" 2>nul | find /I /N "SCUMServer.exe" >nul
if "%ERRORLEVEL%"=="0" (
    echo ERRO: Servidor ja esta rodando
    exit /b 1
)

:: Iniciar servidor
cd /d "C:\Servers\Scum\SCUM\Binaries\Win64"
start SCUMServer.exe -log -port=8900 -MaxPlayers=100

echo Servidor iniciado com sucesso
```

### **Integração com SteamCMD**
```python
# steamcmd_handler.py
import subprocess
import os
import json

class SteamCMDHandler:
    def __init__(self, config):
        self.config = config
        self.steamcmd_path = config['server']['steamcmd_path']
        self.install_path = config['server']['install_path']
        self.app_id = "3792580"  # SCUM App ID
        
    def update_server(self):
        """Atualizar servidor via SteamCMD"""
        try:
            cmd = [
                os.path.join(self.steamcmd_path, 'steamcmd.exe'),
                '+force_install_dir', self.install_path,
                '+login', 'anonymous',
                '+app_update', self.app_id,
                '+quit'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, "Atualização concluída com sucesso"
            else:
                return False, f"Erro na atualização: {result.stderr}"
                
        except Exception as e:
            return False, f"Erro ao executar SteamCMD: {str(e)}"
```

## ⏰ Sistema de Agendamento

### **Scheduler Base**
```python
# task_scheduler.py
import schedule
import time
import threading
from datetime import datetime, timedelta
import pytz

class TaskScheduler:
    def __init__(self, config):
        self.config = config
        self.running = False
        self.thread = None
        self.timezone = pytz.timezone(config['scheduler']['timezone'])
        
    def start(self):
        """Iniciar scheduler"""
        if self.running:
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler)
        self.thread.daemon = True
        self.thread.start()
        return True
        
    def stop(self):
        """Parar scheduler"""
        self.running = False
        if self.thread:
            self.thread.join()
            
    def _run_scheduler(self):
        """Executar scheduler"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
            
    def add_restart_task(self, time_str):
        """Adicionar tarefa de restart"""
        schedule.every().day.at(time_str).do(self._restart_server)
        
    def _restart_server(self):
        """Executar restart do servidor"""
        # Implementar restart
        pass
```

### **Restart Manager**
```python
# restart_manager.py
import subprocess
import time
from datetime import datetime

class RestartManager:
    def __init__(self, config):
        self.config = config
        self.notification_intervals = config['scheduler']['notifications']['intervals']
        
    def schedule_restart(self, restart_time):
        """Agendar restart com notificações"""
        now = datetime.now()
        restart_datetime = datetime.combine(now.date(), restart_time)
        
        # Agendar notificações
        for interval in self.notification_intervals:
            notification_time = restart_datetime - timedelta(minutes=interval)
            if notification_time > now:
                self._schedule_notification(notification_time, interval)
                
        # Agendar restart
        self._schedule_restart(restart_datetime)
        
    def _schedule_notification(self, notification_time, minutes_before):
        """Agendar notificação"""
        # Implementar notificação
        pass
        
    def _schedule_restart(self, restart_time):
        """Agendar restart"""
        # Implementar restart
        pass
```

## 🔄 Sistema de Atualizações

### **Update Manager**
```python
# update_manager.py
import requests
import json
import os
import shutil
import hashlib
from pathlib import Path

class UpdateManager:
    def __init__(self, config):
        self.config = config
        self.frontend_url = config['communication']['frontend_url']
        self.api_key = config['communication']['api_key']
        self.backup_versions = config['updates']['backup_versions']
        
    def check_for_updates(self):
        """Verificar atualizações"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.frontend_url}/api/updates/check",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('update_available', False), data.get('latest_version')
            else:
                return False, None
                
        except Exception as e:
            print(f"Erro ao verificar atualizações: {e}")
            return False, None
            
    def download_update(self, version):
        """Download da atualização"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.frontend_url}/api/updates/download/{version}",
                headers=headers,
                timeout=300
            )
            
            if response.status_code == 200:
                # Salvar arquivo
                with open(f"update_{version}.exe", "wb") as f:
                    f.write(response.content)
                return True, f"update_{version}.exe"
            else:
                return False, None
                
        except Exception as e:
            print(f"Erro ao baixar atualização: {e}")
            return False, None
            
    def install_update(self, update_file):
        """Instalar atualização"""
        try:
            # Fazer backup
            self._backup_current_version()
            
            # Parar serviços
            self._stop_services()
            
            # Substituir arquivo
            shutil.copy2(update_file, "scum_backend.exe")
            
            # Reiniciar serviços
            self._start_services()
            
            return True, "Atualização instalada com sucesso"
            
        except Exception as e:
            return False, f"Erro na instalação: {e}"
            
    def _backup_current_version(self):
        """Fazer backup da versão atual"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backup_{timestamp}"
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        # Copiar arquivos
        shutil.copy2("scum_backend.exe", backup_dir)
        shutil.copy2("config.json", backup_dir)
        
        # Limpar backups antigos
        self._cleanup_old_backups()
        
    def _cleanup_old_backups(self):
        """Limpar backups antigos"""
        backup_dirs = [d for d in os.listdir('.') if d.startswith('backup_')]
        backup_dirs.sort(reverse=True)
        
        # Manter apenas os backups mais recentes
        for backup_dir in backup_dirs[self.backup_versions:]:
            shutil.rmtree(backup_dir)
```

## 🌐 Sistema de Comunicação

### **API Client**
```python
# api_client.py
import requests
import json
import time
from typing import Dict, Any, Optional

class APIClient:
    def __init__(self, config):
        self.config = config
        self.base_url = config['communication']['frontend_url']
        self.api_key = config['communication']['api_key']
        self.timeout = config['communication']['timeout']
        self.retry_attempts = config['communication']['retry_attempts']
        self.retry_delay = config['communication']['retry_delay']
        
    def _get_headers(self) -> Dict[str, str]:
        """Obter headers para requisições"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'SCUM-Backend/1.0.0'
        }
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Fazer requisição com retry"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        for attempt in range(self.retry_attempts):
            try:
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers, timeout=self.timeout)
                elif method.upper() == 'POST':
                    response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
                elif method.upper() == 'PUT':
                    response = requests.put(url, headers=headers, json=data, timeout=self.timeout)
                else:
                    raise ValueError(f"Método HTTP não suportado: {method}")
                    
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    # Token inválido
                    return None
                else:
                    # Tentar novamente
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return None
                        
            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    return None
                    
        return None
        
    def send_status(self, status_data: Dict[str, Any]) -> bool:
        """Enviar status do servidor"""
        response = self._make_request('POST', '/api/status', status_data)
        return response is not None
        
    def get_commands(self) -> Optional[Dict]:
        """Obter comandos pendentes"""
        return self._make_request('GET', '/api/commands')
        
    def confirm_command(self, command_id: str, success: bool, message: str = "") -> bool:
        """Confirmar execução de comando"""
        data = {
            'command_id': command_id,
            'success': success,
            'message': message
        }
        response = self._make_request('POST', '/api/commands/confirm', data)
        return response is not None
```

### **Webhook Manager**
```python
# webhook_manager.py
import requests
import json
from typing import Dict, Any

class WebhookManager:
    def __init__(self, config):
        self.config = config
        self.webhook_url = config['communication']['webhook_url']
        
    def send_notification(self, title: str, description: str, color: int = 0x00ff00, fields: list = None):
        """Enviar notificação via webhook"""
        try:
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "SCUM Backend"
                }
            }
            
            if fields:
                embed["fields"] = fields
                
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 204
            
        except Exception as e:
            print(f"Erro ao enviar webhook: {e}")
            return False
            
    def send_server_status(self, status: str, details: Dict[str, Any]):
        """Enviar status do servidor"""
        color = 0x00ff00 if status == "online" else 0xff0000
        
        fields = []
        for key, value in details.items():
            fields.append({
                "name": key,
                "value": str(value),
                "inline": True
            })
            
        return self.send_notification(
            f"🖥️ Servidor SCUM - {status.upper()}",
            f"Status do servidor: {status}",
            color,
            fields
        )
```

## 📊 Sistema de Logs

### **Logger Estruturado**
```python
# logger.py
import logging
import logging.handlers
import os
from datetime import datetime
from typing import Any, Dict

class StructuredLogger:
    def __init__(self, config):
        self.config = config
        self.log_level = config['logging']['level']
        self.max_size = config['logging']['max_size']
        self.backup_count = config['logging']['backup_count']
        self.format = config['logging']['format']
        
        self._setup_logger()
        
    def _setup_logger(self):
        """Configurar logger"""
        # Criar diretório de logs
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Configurar logger
        self.logger = logging.getLogger('scum_backend')
        self.logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # Handler para arquivo
        log_file = os.path.join(log_dir, 'scum_backend.log')
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self._parse_size(self.max_size),
            backupCount=self.backup_count
        )
        
        # Handler para console
        console_handler = logging.StreamHandler()
        
        # Formatter
        formatter = logging.Formatter(self.format)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Adicionar handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def _parse_size(self, size_str: str) -> int:
        """Converter string de tamanho para bytes"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
            
    def log(self, level: str, message: str, data: Dict[str, Any] = None):
        """Log estruturado"""
        log_data = {
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'level': level.upper()
        }
        
        if data:
            log_data.update(data)
            
        getattr(self.logger, level.lower())(json.dumps(log_data))
        
    def debug(self, message: str, data: Dict[str, Any] = None):
        """Log de debug"""
        self.log('debug', message, data)
        
    def info(self, message: str, data: Dict[str, Any] = None):
        """Log de informação"""
        self.log('info', message, data)
        
    def warn(self, message: str, data: Dict[str, Any] = None):
        """Log de aviso"""
        self.log('warn', message, data)
        
    def error(self, message: str, data: Dict[str, Any] = None):
        """Log de erro"""
        self.log('error', message, data)
```

## 📦 Empacotamento

### **Configuração PyInstaller**
```python
# build_exe.py
import PyInstaller.__main__
import os
import shutil

def build_executable():
    """Empacotar aplicação como executável"""
    
    # Configurações do PyInstaller
    args = [
        'main.py',
        '--onefile',                    # Arquivo único
        '--windowed',                   # Sem console
        '--name=SCUM_Backend',          # Nome do executável
        '--icon=icon.ico',              # Ícone
        '--add-data=scripts;scripts',   # Incluir scripts
        '--add-data=data;data',         # Incluir dados
        '--hidden-import=requests',     # Imports ocultos
        '--hidden-import=psutil',
        '--hidden-import=schedule',
        '--hidden-import=pytz',
        '--clean',                      # Limpar cache
        '--noconfirm'                   # Não confirmar
    ]
    
    # Executar PyInstaller
    PyInstaller.__main__.run(args)
    
    # Copiar arquivos adicionais
    dist_dir = 'dist'
    if os.path.exists(dist_dir):
        # Copiar scripts
        scripts_src = 'scripts'
        scripts_dst = os.path.join(dist_dir, 'scripts')
        if os.path.exists(scripts_src):
            shutil.copytree(scripts_src, scripts_dst)
            
        # Copiar dados
        data_src = 'data'
        data_dst = os.path.join(dist_dir, 'data')
        if os.path.exists(data_src):
            shutil.copytree(data_src, data_dst)
            
    print("Empacotamento concluído!")

if __name__ == "__main__":
    build_executable()
```

### **Script de Instalação**
```batch
@echo off
title SCUM Backend - Instalador
color 0A

echo ========================================
echo  SCUM Backend - Instalador
echo ========================================
echo.

:: Verificar se está rodando como administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Execute como administrador!
    pause
    exit /b 1
)

:: Criar diretório de instalação
set INSTALL_DIR=C:\SCUM_Backend
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
)

:: Copiar arquivos
echo [INFO] Copiando arquivos...
copy "SCUM_Backend.exe" "%INSTALL_DIR%\"
copy "scripts\*" "%INSTALL_DIR%\scripts\"
copy "data\*" "%INSTALL_DIR%\data\"

:: Criar atalho
echo [INFO] Criando atalho...
powershell -Command "& {$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\SCUM Backend.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\SCUM_Backend.exe'; $Shortcut.Save()}"

:: Configurar serviço (opcional)
echo [INFO] Configurando serviço...
sc create "SCUM Backend" binPath= "%INSTALL_DIR%\SCUM_Backend.exe" start= auto

echo.
echo [SUCCESS] Instalação concluída!
echo [INFO] O SCUM Backend foi instalado em: %INSTALL_DIR%
echo [INFO] Atalho criado na área de trabalho
echo.
pause
```

## 🧪 Testes

### **Testes Unitários**
```python
# test_server_control.py
import unittest
from unittest.mock import Mock, patch
from core.server_control.server_manager import ServerManager

class TestServerManager(unittest.TestCase):
    def setUp(self):
        self.config = {
            'server': {
                'path': 'C:\\Test\\SCUM',
                'port': 8900,
                'max_players': 100
            }
        }
        self.server_manager = ServerManager(self.config)
        
    def test_start_server(self):
        """Testar início do servidor"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = self.server_manager.start_server()
            self.assertTrue(result)
            
    def test_stop_server(self):
        """Testar parada do servidor"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = self.server_manager.stop_server()
            self.assertTrue(result)
            
    def test_get_status(self):
        """Testar obtenção de status"""
        with patch('psutil.process_iter') as mock_process:
            mock_process.return_value = [Mock(name='SCUMServer.exe')]
            status = self.server_manager.get_status()
            self.assertEqual(status, 'running')

if __name__ == '__main__':
    unittest.main()
```

### **Testes de Integração**
```python
# test_integration.py
import unittest
import requests
from main import app

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        
    def test_api_status(self):
        """Testar endpoint de status"""
        response = self.app.get('/api/status')
        self.assertEqual(response.status_code, 200)
        
    def test_api_config(self):
        """Testar endpoint de configuração"""
        response = self.app.get('/api/config')
        self.assertEqual(response.status_code, 200)
        
    def test_api_server_control(self):
        """Testar endpoint de controle do servidor"""
        response = self.app.post('/api/server/start')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
```

## 🔒 Segurança

### **Autenticação**
```python
# auth_manager.py
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta

class AuthManager:
    def __init__(self, config):
        self.config = config
        self.secret_key = config['communication']['api_key']
        
    def generate_token(self, backend_id: str) -> str:
        """Gerar token JWT"""
        payload = {
            'backend_id': backend_id,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
        
    def validate_token(self, token: str) -> bool:
        """Validar token JWT"""
        try:
            jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return True
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False
            
    def hash_password(self, password: str) -> str:
        """Hash de senha"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{hash_obj.hex()}"
        
    def verify_password(self, password: str, hash_str: str) -> bool:
        """Verificar senha"""
        salt, hash_hex = hash_str.split(':')
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_obj.hex() == hash_hex
```

### **Validação de Entrada**
```python
# input_validator.py
import re
from typing import Any, Dict

class InputValidator:
    @staticmethod
    def validate_port(port: Any) -> bool:
        """Validar porta"""
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except (ValueError, TypeError):
            return False
            
    @staticmethod
    def validate_max_players(max_players: Any) -> bool:
        """Validar número máximo de jogadores"""
        try:
            players_int = int(max_players)
            return 1 <= players_int <= 100
        except (ValueError, TypeError):
            return False
            
    @staticmethod
    def validate_time_format(time_str: str) -> bool:
        """Validar formato de horário"""
        pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
        return bool(re.match(pattern, time_str))
        
    @staticmethod
    def validate_backend_id(backend_id: str) -> bool:
        """Validar ID do backend"""
        pattern = r'^SCUM-BACKEND-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(pattern, backend_id))
```

## 📋 Padrões de Desenvolvimento

### **Convenções de Código**
- **PEP 8** - Estilo de código Python
- **Type Hints** - Anotações de tipo
- **Docstrings** - Documentação de funções
- **Logging** - Sistema de logs estruturado
- **Error Handling** - Tratamento de erros robusto

### **Estrutura de Commits**
```
feat: adicionar nova funcionalidade
fix: corrigir bug
docs: atualizar documentação
style: formatação de código
refactor: refatoração de código
test: adicionar testes
chore: tarefas de manutenção
```

### **Versionamento**
- **Semantic Versioning** (SemVer)
- **Major.Minor.Patch** (1.0.0)
- **Major**: Mudanças incompatíveis
- **Minor**: Novas funcionalidades compatíveis
- **Patch**: Correções de bugs

---

**Última atualização**: 15/01/2025
**Versão**: 1.0.0
