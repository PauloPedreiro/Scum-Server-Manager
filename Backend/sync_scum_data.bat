@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Caminhos de origem e destino
set "SRC=Z:\Scum\SCUM\Saved\SaveFiles"
set "DST=C:\Servers\scum\SCUM\Saved\SaveFiles"

if not exist "%DST%" mkdir "%DST%"
if not exist "%DST%\Logs" mkdir "%DST%\Logs"

:loop
echo [%date% %time%] Iniciando sincronizacao...

REM Verificar origem
if not exist "%SRC%" (
  echo [%date% %time%] ERRO: Pasta de origem nao encontrada: "%SRC%"
  goto wait
)

REM Sincronizar arquivo SCUM.db
echo [%date% %time%] Copiando SCUM.db...
robocopy "%SRC%" "%DST%" "SCUM.db" /R:2 /W:5 /NFL /NDL /NP /NJH /NJS >nul

REM Sincronizar logs (.log)
echo [%date% %time%] Copiando logs...
robocopy "%SRC%\Logs" "%DST%\Logs" *.log /S /XO /R:2 /W:5 /NFL /NDL /NP /NJH /NJS >nul

echo [%date% %time%] Sincronizacao concluida.

:wait
echo [%date% %time%] Aguardando 15 minutos...
timeout /t 900 /nobreak >nul
goto loop


