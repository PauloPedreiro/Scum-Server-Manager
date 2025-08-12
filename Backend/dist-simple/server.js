const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const DiscordBot = require('./src/bot');
const logger = require('./src/logger');
const FunnyStatistics = require('./src/funny_statistics');
const VehicleControlWebhookMonitor = require('./src/vehicle_control_webhook_monitor');
const SquadEmbedManager = require('./src/squad_embed_manager');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '127.0.0.1';

// Configurações
const SCUM_CONFIG_PATH = 'C:/Servers/scum/SCUM/Saved/Config/WindowsServer';

// Sistema de validação e recriação de arquivos críticos
function validateAndRecreateCriticalFiles() {
    console.log('🔍 Validando arquivos críticos...');
    
    // Lista de arquivos críticos que devem existir
    const criticalFiles = [
        {
            path: 'src/data/temp/restart-server.ps1',
            content: `# Script PowerShell para reiniciar servidor SCUM
# Mais robusto e com mais permissões que batch

# Configurar logging detalhado
$ErrorActionPreference = "Continue"
$VerbosePreference = "Continue"

Write-Host "=== INÍCIO DO SCRIPT DE REINÍCIO ===" -ForegroundColor Green
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan

# Função para carregar configuração do JSON
function Load-SCUMConfig {
    try {
        Write-Host "Tentando carregar configuração..." -ForegroundColor Yellow
        
        # Tentar múltiplos caminhos possíveis
        $possiblePaths = @(
            "C:\\Users\\paulo\\Desktop\\Cursor Ai\\Scum\\ScumServerManager2.0\\Backend\\src\\data\\server\\config.json",
            "src\\data\\server\\config.json",
            "..\\..\\src\\data\\server\\config.json",
            ".\\src\\data\\server\\config.json"
        )
        
        foreach ($configPath in $possiblePaths) {
            Write-Host "Tentando caminho: $configPath" -ForegroundColor Gray
            if (Test-Path $configPath) {
                Write-Host "Configuração encontrada em: $configPath" -ForegroundColor Green
                $configContent = Get-Content $configPath -Raw
                $config = $configContent | ConvertFrom-Json
                return $config
            }
        }
        
        Write-Host "ERRO: Arquivo de configuração não encontrado em nenhum caminho" -ForegroundColor Red
        return $null
    }
    catch {
        Write-Host "Erro ao carregar configuração: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
        return $null
    }
}

# Função para verificar se há processos rodando
function Get-SCUMProcesses {
    try {
        Write-Host "Verificando processos SCUMServer..." -ForegroundColor Yellow
        $processes = Get-Process -Name "SCUMServer" -ErrorAction SilentlyContinue
        Write-Host "Encontrados $($processes.Count) processo(s) SCUMServer" -ForegroundColor Cyan
        return $processes
    }
    catch {
        Write-Host "Erro ao verificar processos: $($_.Exception.Message)" -ForegroundColor Red
        return @()
    }
}

# Função para parar todos os processos SCUMServer por nome (fallback)
function Stop-AllSCUMProcesses {
    try {
        Write-Host "Tentando parar todos os processos SCUMServer por nome..." -ForegroundColor Red
        Stop-Process -Name "SCUMServer" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        
        # Verificar se ainda há processos
        $remaining = Get-Process -Name "SCUMServer" -ErrorAction SilentlyContinue
        if ($remaining) {
            Write-Host "Ainda há $($remaining.Count) processo(s) após Stop-Process por nome" -ForegroundColor Red
            return $false
        } else {
            Write-Host "Todos os processos SCUMServer parados com sucesso" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "Erro ao parar processos por nome: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Função para parar processos
function Stop-SCUMProcesses {
    param([array]$Processes)
    
    Write-Host "Iniciando parada de $($Processes.Count) processo(s)..." -ForegroundColor Yellow
    
    foreach ($process in $Processes) {
        try {
            Write-Host "Parando processo PID: $($process.Id)" -ForegroundColor Cyan
            
            # Tentar parar graciosamente primeiro
            Write-Host "  Tentativa 1: CloseMainWindow()" -ForegroundColor Gray
            $process.CloseMainWindow() | Out-Null
            Start-Sleep -Seconds 5
            
            # Se ainda estiver rodando, tentar parar com Stop-Process
            if (!$process.HasExited) {
                Write-Host "  Tentativa 2: Stop-Process -Force" -ForegroundColor Yellow
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 3
            }
            
            # Se ainda estiver rodando, forçar parada com Kill
            if (!$process.HasExited) {
                Write-Host "  Tentativa 3: Kill()" -ForegroundColor Red
                $process.Kill()
                Start-Sleep -Seconds 3
            }
            
            # Verificar se realmente parou
            try {
                $checkProcess = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
                if ($checkProcess) {
                    Write-Host "ERRO: Processo PID $($process.Id) ainda está rodando após tentativas de parada" -ForegroundColor Red
                    return $false
                }
            } catch {
                # Processo não existe mais, sucesso
            }
            
            Write-Host "Processo PID $($process.Id) parado com sucesso" -ForegroundColor Green
        }
        catch {
            Write-Host "Erro ao parar processo PID $($process.Id): $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }
    return $true
}

# Função para iniciar servidor
function Start-SCUMServer {
    param($Config)
    
    try {
        Write-Host "Iniciando servidor SCUM..." -ForegroundColor Cyan
        
        # Usar configuração do JSON
        $ServerPath = $Config.serverPath
        $SteamCMDPath = $Config.steamCMDPath
        $InstallPath = $Config.installPath
        $Port = $Config.port
        $MaxPlayers = $Config.maxPlayers
        $UseBattleye = $Config.useBattleye
        
        Write-Host "Configuração carregada:" -ForegroundColor Cyan
        Write-Host "  Porta: $Port" -ForegroundColor Yellow
        Write-Host "  Max Players: $MaxPlayers" -ForegroundColor Yellow
        Write-Host "  Battleye: $UseBattleye" -ForegroundColor Yellow
        Write-Host "  ServerPath: $ServerPath" -ForegroundColor Yellow
        Write-Host "  SteamCMDPath: $SteamCMDPath" -ForegroundColor Yellow
        Write-Host "  InstallPath: $InstallPath" -ForegroundColor Yellow
        
        # Verificar se os caminhos existem
        if (!(Test-Path $ServerPath)) {
            Write-Host "ERRO: Caminho do servidor não encontrado: $ServerPath" -ForegroundColor Red
            return $false
        }
        
        # Atualizar servidor via Steam
        Write-Host "Atualizando servidor via Steam..." -ForegroundColor Yellow
        if (Test-Path "$SteamCMDPath\\steamcmd.exe") {
            Write-Host "Executando steamcmd..." -ForegroundColor Gray
            & "$SteamCMDPath\\steamcmd.exe" +force_install_dir "$InstallPath" +login anonymous +app_update 3792580 +quit
        } else {
            Write-Host "AVISO: steamcmd.exe não encontrado em $SteamCMDPath" -ForegroundColor Yellow
        }
        
        # Navegar para o diretório do servidor
        Write-Host "Navegando para: $ServerPath" -ForegroundColor Gray
        Set-Location $ServerPath
        
        # Construir argumentos do servidor
        $serverArgs = @("-log", "-port=$Port")
        
        if ($MaxPlayers) {
            $serverArgs += "-MaxPlayers=$MaxPlayers"
        }
        
        if (!$UseBattleye) {
            $serverArgs += "-nobattleye"
        }
        
        Write-Host "Argumentos do servidor: $($serverArgs -join ' ')" -ForegroundColor Cyan
        
        # Iniciar servidor
        Write-Host "Iniciando SCUMServer.exe..." -ForegroundColor Green
        $process = Start-Process -FilePath "SCUMServer.exe" -ArgumentList $serverArgs -WindowStyle Normal -PassThru
        
        if ($process) {
            Write-Host "Processo iniciado com PID: $($process.Id)" -ForegroundColor Green
        } else {
            Write-Host "AVISO: Não foi possível obter PID do processo iniciado" -ForegroundColor Yellow
        }
        
        return $true
    }
    catch {
        Write-Host "Erro ao iniciar servidor: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
        return $false
    }
}

# MAIN EXECUTION
try {
    Write-Host "=== EXECUÇÃO PRINCIPAL ===" -ForegroundColor Green
    
    # Carregar configuração
    Write-Host "Carregando configuração do servidor..." -ForegroundColor Cyan
    $config = Load-SCUMConfig
    
    if (!$config) {
        Write-Host "ERRO: Não foi possível carregar a configuração" -ForegroundColor Red
        exit 1
    }
    
    # Verificar processos atuais
    Write-Host "Verificando processos SCUMServer.exe atuais..." -ForegroundColor Cyan
    $currentProcesses = Get-SCUMProcesses
    
    if ($currentProcesses.Count -gt 0) {
        Write-Host "Encontrados $($currentProcesses.Count) processo(s) SCUMServer.exe" -ForegroundColor Yellow
        
        # Parar processos existentes
        $stopSuccess = Stop-SCUMProcesses -Processes $currentProcesses
        
        if (!$stopSuccess) {
            Write-Host "ERRO: Não foi possível parar todos os processos" -ForegroundColor Red
            exit 1
        }
        
        # Aguardar um pouco para garantir que pararam
        Write-Host "Aguardando 5 segundos para confirmar parada..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        # Verificar se realmente pararam
        $remainingProcesses = Get-SCUMProcesses
        if ($remainingProcesses.Count -gt 0) {
            Write-Host "AVISO: Ainda há $($remainingProcesses.Count) processo(s) rodando" -ForegroundColor Yellow
            Write-Host "Tentando parada mais agressiva com Stop-Process..." -ForegroundColor Red
            
            foreach ($process in $remainingProcesses) {
                try {
                    Write-Host "Parada agressiva do processo PID: $($process.Id)" -ForegroundColor Red
                    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                }
                catch {
                    Write-Host "ERRO: Não foi possível parar processo PID: $($process.Id)" -ForegroundColor Red
                }
            }
            
            Start-Sleep -Seconds 5
            
            # Tentar novamente com Kill se ainda houver processos
            $stillRemaining = Get-SCUMProcesses
            if ($stillRemaining.Count -gt 0) {
                Write-Host "Ainda há $($stillRemaining.Count) processo(s) - tentando Kill()..." -ForegroundColor Red
                foreach ($process in $stillRemaining) {
                    try {
                        $process.Kill()
                        Write-Host "Kill() no processo PID: $($process.Id)" -ForegroundColor Red
                    }
                    catch {
                        Write-Host "ERRO: Kill() falhou para processo PID: $($process.Id)" -ForegroundColor Red
                    }
                }
                Start-Sleep -Seconds 3
            }
            
            $finalProcesses = Get-SCUMProcesses
            if ($finalProcesses.Count -gt 0) {
                Write-Host "ERRO: Não foi possível parar todos os processos após tentativas agressivas" -ForegroundColor Red
                Write-Host "Processos restantes: $($finalProcesses.Id -join ', ')" -ForegroundColor Red
                
                # Última tentativa: parar por nome
                Write-Host "Tentando parada final por nome..." -ForegroundColor Red
                $finalStop = Stop-AllSCUMProcesses
                if (!$finalStop) {
                    Write-Host "ERRO: Falha total ao parar processos SCUMServer" -ForegroundColor Red
                    exit 1
                }
            }
        }
    } else {
        Write-Host "Nenhum processo SCUMServer.exe encontrado" -ForegroundColor Green
    }
    
    # Iniciar servidor
    Write-Host "Iniciando servidor SCUM..." -ForegroundColor Cyan
    $startSuccess = Start-SCUMServer -Config $config
    
    if (!$startSuccess) {
        Write-Host "ERRO: Não foi possível iniciar o servidor" -ForegroundColor Red
        exit 1
    }
    
    # Aguardar um pouco para o servidor inicializar
    Write-Host "Aguardando 15 segundos para servidor inicializar..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
    
    # Verificar se o servidor iniciou
    Write-Host "Verificando se servidor iniciou..." -ForegroundColor Cyan
    $newProcesses = Get-SCUMProcesses
    
    if ($newProcesses.Count -eq 1) {
        Write-Host "SUCCESS: Servidor SCUM reiniciado com sucesso! (1 processo rodando)" -ForegroundColor Green
        Write-Host "PID do novo processo: $($newProcesses[0].Id)" -ForegroundColor Green
        exit 0
    } elseif ($newProcesses.Count -gt 1) {
        Write-Host "AVISO: Servidor iniciou, mas há $($newProcesses.Count) processo(s) rodando" -ForegroundColor Yellow
        Write-Host "Isso pode indicar que o servidor anterior não foi parado completamente" -ForegroundColor Yellow
        Write-Host "PIDs: $($newProcesses.Id -join ', ')" -ForegroundColor Yellow
        exit 0
    } else {
        Write-Host "ERRO: Servidor não iniciou após reiniciar" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "ERRO CRÍTICO: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
    exit 1
}
finally {
    Write-Host "=== FIM DO SCRIPT DE REINÍCIO ===" -ForegroundColor Green
    Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
}`,
            description: 'Script PowerShell para reiniciar servidor'
        },
        {
            path: 'src/data/bot/steam_ids_mapping.json',
            content: '{}',
            description: 'Mapeamento de Steam IDs'
        },
        {
            path: 'src/data/bot/linked_users.json',
            content: '{}',
            description: 'Usuários vinculados Discord-Steam'
        },
        {
            path: 'src/data/webhooks.json',
            content: '{}',
            description: 'Configuração de webhooks'
        },
        {
            path: 'src/data/players/lastChatRead.json',
            content: '{"lastRead": 0}',
            description: 'Última leitura do chat'
        },
        {
            path: 'src/data/players/lastOnline.json',
            content: '{}',
            description: 'Último status online dos jogadores'
        },
        {
            path: 'src/data/server/status.json',
            content: '{"isRunning": false, "startTime": null, "restartCount": 0, "lastError": null}',
            description: 'Status do servidor'
        },
        {
            path: 'src/data/server/scheduled-restarts.json',
            content: '{"restartTimes": ["06:00", "18:00"]}',
            description: 'Horários de reinício agendados'
        },
        {
            path: 'src/data/famepoints/lastProcessed.json',
            content: '{"lastProcessed": 0}',
            description: 'Último processamento de fame points'
        },
        {
            path: 'src/data/bunkers/lastProcessed.json',
            content: '{"lastProcessed": 0}',
            description: 'Último processamento de bunkers'
        },
        {
            path: 'src/data/bunkers/bunkers.json',
            content: '[]',
            description: 'Dados dos bunkers'
        },
        {
            path: 'src/data/bot/pending_mount_complete_requests.json',
            content: '[]',
            description: 'Requisições pendentes de montagem'
        },
        {
            path: 'src/data/temp/start-server-temp.bat',
            content: `@echo off
set ServerPath=C:\\Servers\\Scum\\SCUM\\Binaries\\Win64
set SteamCMDPath=C:\\Servers\\steamcmd
set InstallPath=C:\\Servers\\Scum

:: Check and update SCUM server
"%SteamCMDPath%\\steamcmd.exe" +force_install_dir "%InstallPath%" +login anonymous +app_update 3792580 +quit

cd /d "%ServerPath%"
start SCUMServer.exe -log -port=8904 -MaxPlayers=64

:: Additional startup arguments:
::
:: -port=8904           : Server will run on port 8904
::                        Players will connect on port 8906 (port+2)
::
:: -MaxPlayers=64       : Override max players set in ServerSettings.ini
::
:: -nobattleye          : Launch server without Battleye (not recommended)`,
            description: 'Script batch para iniciar servidor'
        },
        {
            path: 'src/data/temp/stop-server.bat',
            content: `@echo off
echo Parando servidor SCUM...

:: Verificar quantas instâncias estão rodando
echo Verificando instancias do SCUMServer.exe...
tasklist /FI "IMAGENAME eq SCUMServer.exe" /FO CSV | find /c "SCUMServer.exe" > temp_count.txt
set /p instance_count=<temp_count.txt
del temp_count.txt

echo Encontradas %instance_count% instancias do SCUMServer.exe

:: Parar TODAS as instâncias de uma vez
echo Parando TODAS as instancias do SCUMServer.exe...

:: Primeira tentativa: taskkill com /T para parar árvore completa
taskkill /IM SCUMServer.exe /T /F >nul 2>nul
if %errorlevel% equ 0 (
    echo Todas as instancias paradas com sucesso via taskkill /T /F
    goto :wait_and_check
)

:: Segunda tentativa: PowerShell para parar todos os processos
powershell -Command "Get-Process -Name 'SCUMServer' -ErrorAction SilentlyContinue | Stop-Process -Force" >nul 2>nul
if %errorlevel% equ 0 (
    echo Todas as instancias paradas com sucesso via PowerShell
    goto :wait_and_check
)

:: Terceira tentativa: wmic para parar todos
wmic process where name="SCUMServer.exe" call terminate >nul 2>nul
if %errorlevel% equ 0 (
    echo Todas as instancias paradas com sucesso via wmic
    goto :wait_and_check
)

:: Quarta tentativa: taskkill normal
taskkill /IM SCUMServer.exe /F >nul 2>nul
if %errorlevel% equ 0 (
    echo Todas as instancias paradas com sucesso via taskkill /F
    goto :wait_and_check
)

:: Quinta tentativa: taskkill mais suave
taskkill /IM SCUMServer.exe >nul 2>nul
if %errorlevel% equ 0 (
    echo Todas as instancias paradas com sucesso via taskkill suave
    goto :wait_and_check
)

:: Se chegou aqui, não conseguiu parar
echo ERRO: Nao foi possivel parar o servidor SCUM
echo Verifique se o processo esta rodando ou se voce tem permissoes de administrador
exit /b 1

:wait_and_check
echo.
echo Aguardando 5 segundos para confirmar que TODOS os processos foram finalizados...
ping -n 6 127.0.0.1 >nul

:: Verificar se ainda há alguma instância rodando
echo Verificando se ainda ha instancias rodando...
tasklist /FI "IMAGENAME eq SCUMServer.exe" /FO CSV | find /c "SCUMServer.exe" > temp_count2.txt
set /p remaining_count=<temp_count2.txt
del temp_count2.txt

if "%remaining_count%" gtr "0" (
    echo AVISO: Ainda ha %remaining_count% instancia(s) rodando
    echo Tentando parar novamente...
    
    :: Tentar parar novamente de forma mais agressiva
    taskkill /IM SCUMServer.exe /T /F >nul 2>nul
    ping -n 4 127.0.0.1 >nul
    
    :: Verificar novamente
    tasklist /FI "IMAGENAME eq SCUMServer.exe" /FO CSV | find /c "SCUMServer.exe" > temp_count3.txt
set /p final_count=<temp_count3.txt
    del temp_count3.txt
    
    if "%final_count%" gtr "0" (
        echo ERRO: Nao foi possivel parar todas as instancias
        echo Tente parar manualmente via Gerenciador de Tarefas
        exit /b 1
    ) else (
        echo Confirmado: TODAS as instancias do SCUMServer.exe foram paradas!
        exit /b 0
    )
) else (
    echo Confirmado: TODAS as instancias do SCUMServer.exe foram paradas com sucesso!
    exit /b 0
)`,
            description: 'Script batch para parar servidor'
        },
        {
            path: 'src/data/temp/restart-server.bat',
            content: `@echo off
echo Reiniciando servidor SCUM...

:: Verificar quantas instâncias estão rodando antes
echo Verificando instancias atuais do SCUMServer.exe...
tasklist /FI "IMAGENAME eq SCUMServer.exe" /FO CSV | find /c "SCUMServer.exe" > temp_count_before.txt
set /p instances_before=<temp_count_before.txt
if "%instances_before%"=="" set instances_before=0
for /f "delims=0123456789" %%a in ("%instances_before%") do set instances_before=0
del temp_count_before.txt

echo Encontradas %instances_before% instancias antes do restart

:: Primeiro, parar TODAS as instâncias
echo Parando TODAS as instancias do servidor...
call "%~dp0stop-server.bat"
if %errorlevel% neq 0 (
    echo ERRO: Nao foi possivel parar o servidor atual
    echo Tentando parar manualmente de forma mais agressiva...
    taskkill /IM SCUMServer.exe /T /F >nul 2>nul
    ping -n 6 127.0.0.1 >nul
)

:: Aguardar um pouco para garantir que TODAS pararam
echo Aguardando 8 segundos para garantir que TODAS as instancias pararam...
ping -n 9 127.0.0.1 >nul

:: Verificar se ainda ha alguma instancia rodando
echo Verificando se ainda ha instancias rodando...
tasklist /FI "IMAGENAME eq SCUMServer.exe" /FO CSV | find /c "SCUMServer.exe" > temp_count_after.txt
set /p instances_after=<temp_count_after.txt
if "%instances_after%"=="" set instances_after=0
for /f "delims=0123456789" %%a in ("%instances_after%") do set instances_after=0
del temp_count_after.txt

if "%instances_after%" gtr "0" (
    echo AVISO: Ainda ha %instances_after% instancia(s) rodando
    echo Tentando parar forçadamente novamente...
    taskkill /IM SCUMServer.exe /T /F >nul 2>nul
    ping -n 6 127.0.0.1 >nul
    
    :: Verificar novamente
    tasklist /FI "IMAGENAME eq SCUMServer.exe" /FO CSV | find /c "SCUMServer.exe" > temp_count_final.txt
    set /p instances_final=<temp_count_final.txt
    if "%instances_final%"=="" set instances_final=0
    for /f "delims=0123456789" %%a in ("%instances_final%") do set instances_final=0
    del temp_count_final.txt
    
    if "%instances_final%" gtr "0" (
        echo ERRO: Nao foi possivel parar todas as instancias
        echo Tente parar manualmente via Gerenciador de Tarefas
        exit /b 1
    )
)

:: Agora iniciar o servidor novamente
echo Iniciando servidor SCUM...
call "%~dp0start-server-temp.bat"

:: Verificar se iniciou com sucesso
echo Aguardando 15 segundos para verificar se o servidor iniciou...
ping -n 16 127.0.0.1 >nul

:: Verificar quantas instâncias estão rodando agora
echo Verificando instancias apos o restart...
tasklist /FI "IMAGENAME eq SCUMServer.exe" /FO CSV | find /c "SCUMServer.exe" > temp_count_now.txt
set /p instances_now=<temp_count_now.txt
if "%instances_now%"=="" set instances_now=0
for /f "delims=0123456789" %%a in ("%instances_now%") do set instances_now=0
del temp_count_now.txt

if "%instances_now%" equ "1" (
    echo SUCCESS: Servidor SCUM reiniciado com sucesso! (1 instancia rodando)
    exit /b 0
) else (
    if "%instances_now%" gtr "1" (
        echo AVISO: Servidor iniciou, mas ha %instances_now% instancias rodando
        echo Isso pode indicar que o servidor anterior nao foi parado completamente
        exit /b 0
    ) else (
        echo ERRO: Servidor nao iniciou apos reiniciar
        exit /b 1
    )
)`,
            description: 'Script batch para reiniciar servidor'
        },
        {
            path: 'src/data/temp/stop-server-admin.bat',
            content: `@echo off
echo Parando servidor SCUM como administrador...

:: Tentar executar como administrador
echo Tentando parar SCUMServer.exe com privilegios elevados...

:: Primeira tentativa: taskkill normal
taskkill /IM SCUMServer.exe /F
if %errorlevel% equ 0 (
    echo Servidor parado com sucesso
    goto :check
)

:: Segunda tentativa: taskkill com /T
taskkill /IM SCUMServer.exe /T /F
if %errorlevel% equ 0 (
    echo Servidor parado com sucesso via /T
    goto :check
)

:: Terceira tentativa: PowerShell com privilégios
powershell -Command "Stop-Process -Name 'SCUMServer' -Force"
if %errorlevel% equ 0 (
    echo Servidor parado com sucesso via PowerShell
    goto :check
)

:: Quarta tentativa: wmic
wmic process where name="SCUMServer.exe" call terminate
if %errorlevel% equ 0 (
    echo Servidor parado com sucesso via wmic
    goto :check
)

:: Se chegou aqui, não conseguiu parar
echo ERRO: Nao foi possivel parar o servidor
echo Execute este arquivo como administrador
exit /b 1

:check
echo Aguardando 5 segundos...
timeout /t 5 /nobreak >nul

:: Verificar se ainda está rodando
tasklist /FI "IMAGENAME eq SCUMServer.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo AVISO: O processo ainda esta rodando
    echo Tente executar manualmente: taskkill /IM SCUMServer.exe /F
    exit /b 1
) else (
    echo Confirmado: Servidor parado com sucesso!
    exit /b 0
)`,
            description: 'Script batch para parar servidor como administrador'
        },
        {
            path: 'src/data/temp/stop-server-simple.bat',
            content: `@echo off
echo Parando servidor SCUM...

:: Tentar parar o processo de forma simples
echo Tentando parar SCUMServer.exe...

:: Primeira tentativa: taskkill normal
taskkill /IM SCUMServer.exe /F
if %errorlevel% equ 0 (
    echo Servidor parado com sucesso
    goto :check
)

:: Segunda tentativa: taskkill com /T
taskkill /IM SCUMServer.exe /T /F
if %errorlevel% equ 0 (
    echo Servidor parado com sucesso via /T
    goto :check
)

:: Terceira tentativa: PowerShell
powershell -Command "Stop-Process -Name 'SCUMServer' -Force"
if %errorlevel% equ 0 (
    echo Servidor parado com sucesso via PowerShell
    goto :check
)

:: Se chegou aqui, não conseguiu parar
echo ERRO: Nao foi possivel parar o servidor
exit /b 1

:check
echo Aguardando 3 segundos...
timeout /t 3 /nobreak >nul

:: Verificar se ainda está rodando
tasklist /FI "IMAGENAME eq SCUMServer.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo AVISO: O processo ainda esta rodando
    exit /b 1
) else (
    echo Confirmado: Servidor parado com sucesso!
    exit /b 0
)`,
            description: 'Script batch simples para parar servidor'
        }
    ];

    // Criar diretórios necessários
    const requiredDirs = [
        'src/data/temp',
        'src/data/bot',
        'src/data/players',
        'src/data/server',
        'src/data/famepoints',
        'src/data/bunkers'
    ];

    // Criar diretórios
    requiredDirs.forEach(dir => {
        if (!fs.existsSync(dir)) {
            try {
                fs.mkdirSync(dir, { recursive: true });
                console.log(`✅ Diretório criado: ${dir}`);
            } catch (error) {
                console.error(`❌ Erro ao criar diretório ${dir}:`, error.message);
            }
        }
    });

    // Validar e recriar arquivos críticos
    criticalFiles.forEach(file => {
        try {
            if (!fs.existsSync(file.path)) {
                // Criar diretório pai se não existir
                const dir = path.dirname(file.path);
                if (!fs.existsSync(dir)) {
                    fs.mkdirSync(dir, { recursive: true });
                }
                
                // Criar arquivo
                fs.writeFileSync(file.path, file.content, 'utf8');
                console.log(`✅ Arquivo recriado: ${file.path} (${file.description})`);
            } else {
                console.log(`✅ Arquivo existe: ${file.path}`);
            }
        } catch (error) {
            console.error(`❌ Erro ao validar/criar arquivo ${file.path}:`, error.message);
        }
    });

    console.log('✅ Validação de arquivos críticos concluída');
}

// Executar validação antes de inicializar o servidor
validateAndRecreateCriticalFiles();

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Middleware para carregar configurações
app.use((req, res, next) => {
    try {
        req.config = loadConfig();
        req.webhooks = loadWebhooks();
        next();
    } catch (error) {
        console.error('❌ Erro ao carregar configurações:', error.message);
        res.status(500).json({ error: 'Erro de configuração' });
    }
});

// Importar e registrar todas as rotas
try {
    // Rotas principais
    app.use('/api/players', require('./routes/players'));
    app.use('/api/webhook', require('./routes/webhook'));
    app.use('/api', require('./routes/chat'));
    app.use('/api', require('./routes/vehicles'));
    app.use('/api/adminlog', require('./routes/adminlog'));
    app.use('/api/bunkers', require('./routes/bunkers'));
    app.use('/api/famepoints', require('./routes/famepoints'));
    app.use('/api/server', require('./routes/server'));
    app.use('/api/bot', require('./routes/bot'));
    app.use('/api/configserver', require('./routes/configserver'));
    app.use('/api/scheduler', require('./routes/scheduler'));
    app.use('/api/auth', require('./routes/auth'));
    console.log('✅ Todas as rotas registradas com sucesso');
} catch (error) {
    console.error('❌ Erro ao registrar rotas:', error.message);
}

// Rota principal
app.get('/', (req, res) => {
    res.json({
        message: 'Scum Server Manager - Backend',
        status: 'online',
        timestamp: new Date().toISOString(),
        version: '1.0.0'
    });
});

// Rota de health check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        uptime: process.uptime(),
        timestamp: new Date().toISOString()
    });
});

// Rota de teste de webhook
app.post('/test-webhook', async (req, res) => {
    try {
        const { webhookKey, message } = req.body;
        const webhookUrl = req.webhooks[webhookKey];
        
        if (!webhookUrl) {
            return res.status(400).json({ error: 'Webhook não encontrado' });
        }

        await sendWebhook(webhookUrl, {
            content: message || 'Teste de webhook do Scum Server Manager'
        });

        res.json({ success: true, message: 'Webhook enviado com sucesso' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Rota para estatísticas divertidas
app.get('/funny-stats', (req, res) => {
    try {
        const statsPath = path.join(__dirname, 'src', 'data', 'funny_statistics.json');
        const stats = JSON.parse(fs.readFileSync(statsPath, 'utf8'));
        res.json(stats);
    } catch (error) {
        res.status(500).json({ error: 'Erro ao carregar estatísticas' });
    }
});

// Rota para jogadores
app.get('/players', (req, res) => {
    try {
        const playersPath = path.join(__dirname, 'src', 'data', 'players', 'players.json');
        const players = JSON.parse(fs.readFileSync(playersPath, 'utf8'));
        res.json(players);
    } catch (error) {
        res.status(500).json({ error: 'Erro ao carregar jogadores' });
    }
});

// Rota para configurações
app.get('/config', (req, res) => {
    try {
        res.json(req.config);
    } catch (error) {
        res.status(500).json({ error: 'Erro ao carregar configurações' });
    }
});

// Inicializar bot Discord e outros serviços
let discordBot = null;
let funnyStatistics = null;
let scheduler = null;
let donationChannelManager = null;

app.listen(PORT, async () => {
    console.log(`🚀 Scum Server Manager rodando na porta ${PORT}`);
    console.log(`📡 Acesse: http://localhost:${PORT}`);
    console.log(`🔧 Health check: http://localhost:${PORT}/health`);
    console.log(`📊 Estatísticas: http://localhost:${PORT}/funny-stats`);
    console.log(`👥 Jogadores: http://localhost:${PORT}/players`);
    console.log(`⚙️  Configurações: http://localhost:${PORT}/config`);
    console.log(`🔐 Auth: http://localhost:${PORT}/api/auth/login`);
    
    // Iniciar bot Discord
    try {
        discordBot = new DiscordBot();
        await discordBot.start();
        console.log('✅ Bot Discord iniciado com sucesso');
    } catch (error) {
        console.error('❌ Erro ao iniciar bot Discord:', error.message);
    }

    // Iniciar gerenciador de canal de doação
    try {
        console.log('💝 Iniciando gerenciador de canal de doação...');
        const DonationChannelManager = require('./src/donation_channel_manager');
        donationChannelManager = new DonationChannelManager(config);
        const donationResult = await donationChannelManager.initialize();
        
        if (donationResult) {
            console.log('✅ Canal de doação configurado com sucesso');
        } else {
            console.log('⚠️ Canal de doação não foi configurado (verificar logs)');
        }
    } catch (error) {
        console.error('❌ Erro ao iniciar gerenciador de canal de doação:', error.message);
    }

    // Iniciar sistema de estatísticas divertidas
    try {
        funnyStatistics = new FunnyStatistics();
        funnyStatistics.startScheduler();
        console.log('✅ Sistema de estatísticas divertidas iniciado com sucesso');
    } catch (error) {
        console.error('❌ Erro ao iniciar sistema de estatísticas divertidas:', error.message);
    }

    // Executar migração automática do config.json se necessário
    try {
        const configMigrator = require('./src/config_migrator');
        const migrationStatus = configMigrator.getMigrationStatus();
        
        if (migrationStatus.needsMigration) {
            console.log('🔄 Migração automática do config.json necessária...');
            const migrationResult = configMigrator.migrate();
            
            if (migrationResult) {
                console.log('✅ Migração do config.json concluída com sucesso');
                console.log('✅ Migração automática do config.json concluída');
            } else {
                console.log('❌ Falha na migração do config.json');
                console.error('Falha na migração automática do config.json');
            }
        } else {
            console.log('✅ Config.json já está no formato atual');
        }
    } catch (error) {
        console.error('❌ Erro ao executar migração do config.json:', error.message);
        console.error('Erro ao executar migração automática do config.json:', error.message);
    }

    // Iniciar scheduler backend
    try {
        scheduler = require('./src/scheduler');
        scheduler.start();
        console.log('✅ Scheduler backend iniciado com sucesso');
    } catch (error) {
        console.error('❌ Erro ao iniciar scheduler backend:', error.message);
    }
});

// Tratamento global de erros não tratados
process.on('uncaughtException', (err) => {
    console.error('❌ Erro não tratado (uncaughtException):', err.message);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('❌ Rejeição não tratada (unhandledRejection):', reason.toString());
});

// Limpeza ao encerrar o processo
process.on('SIGINT', async () => {
    console.log('\n🔄 Encerrando aplicação...');
    
    if (donationChannelManager) {
        try {
            await donationChannelManager.cleanup();
            console.log('✅ Gerenciador de canal de doação encerrado');
        } catch (error) {
            console.error('❌ Erro ao encerrar gerenciador de canal de doação:', error.message);
        }
    }
    
    process.exit(0);
});