@echo off
echo ========================================
echo RECONSTRUINDO BACKEND DO ZERO
echo ========================================
echo.

echo [1/5] Parando processos Python...
taskkill /f /im python.exe 2>nul

echo [2/5] Deletando TODOS os caches Python...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc 2>nul

echo [3/5] Deletando arquivos compilados...
del /s /q *.pyo 2>nul
del /s /q *.pyd 2>nul

echo [4/5] Verificando arquivos fonte...
dir core\notifications\scum_notifier.py | find "scum_notifier.py"
dir core\notifications\notification_manager.py | find "notification_manager.py"

echo [5/5] Backend reconstruído!
echo.
echo AGORA EXECUTE: python main.py
echo.
pause


