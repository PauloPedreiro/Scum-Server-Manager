@echo off
title Testador de Notificacoes RCON - SSM 3.0
cd /d "%~dp0"
python test_notifications.py
if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro ao executar o script. Certifique-se de que o Python esta instalado e no PATH do sistema.
    pause
)
