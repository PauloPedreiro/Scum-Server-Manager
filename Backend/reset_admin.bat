@echo off
setlocal EnableDelayedExpansion

echo ===================================================
echo   SSM Backend - Reset de Senha do Admin para admin123
echo ===================================================
echo.

if not exist "%~dp0reset_admin.ps1" (
    echo [ERRO] reset_admin.ps1 nao encontrado!
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0reset_admin.ps1"

echo.
echo Processo concluido.
pause
