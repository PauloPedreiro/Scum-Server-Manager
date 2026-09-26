@echo off
chcp 65001 > nul
set CURRENT_DIR=%~dp0
cd /d "%CURRENT_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%CURRENT_DIR%reset_player.ps1"

pause
