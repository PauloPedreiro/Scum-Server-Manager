@echo off
echo Parando processos Python...
taskkill /f /im python.exe 2>nul

echo Deletando cache Python...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc 2>nul

echo Cache limpo com sucesso!
echo.
echo Agora execute: python main.py
pause


