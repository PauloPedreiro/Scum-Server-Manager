@echo off
REM Script para limpar cache de ícones do Windows
REM Execute como Administrador para melhor resultado

echo Limpando cache de icones do Windows...
echo.

REM Parar o processo explorer.exe temporariamente
taskkill /f /im explorer.exe >nul 2>&1

REM Limpar cache de ícones
del /a /q /f /s "%LOCALAPPDATA%\IconCache.db" >nul 2>&1
del /a /q /f /s "%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache*.db" >nul 2>&1
del /a /q /f /s "%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache*.db" >nul 2>&1

REM Limpar cache de thumbnails
del /a /q /f /s "%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db" >nul 2>&1

REM Reiniciar explorer.exe
start explorer.exe

echo.
echo Cache de icones limpo!
echo.
echo NOTA: Se os icones ainda nao aparecerem corretamente:
echo 1. Feche e reabra o explorador de arquivos
echo 2. Reinicie o computador
echo 3. Verifique se o arquivo .ico tem multiplos tamanhos (16x16, 32x32, 48x48, 256x256)
echo.
pause

