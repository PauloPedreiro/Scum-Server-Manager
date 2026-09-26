@echo off
chcp 65001 >nul
title SSM 3.0 - Verificar Build

echo.
echo ========================================
echo   Verificando Build de Produção
echo ========================================
echo.

if not exist "dist" (
    echo [ERRO] Pasta dist não encontrada!
    echo Execute 'npm run build' primeiro.
    echo.
    pause
    exit /b 1
)

echo Verificando arquivos essenciais...
echo.

set ERRO=0

REM Verificar index.html
if not exist "dist\index.html" (
    echo [ERRO] dist\index.html não encontrado!
    set ERRO=1
) else (
    echo [OK] index.html encontrado
)

REM Verificar pasta assets
if not exist "dist\assets" (
    echo [ERRO] dist\assets não encontrada!
    set ERRO=1
) else (
    echo [OK] Pasta assets encontrada
)

REM Verificar arquivos JS principais
set JS_COUNT=0
for %%f in (dist\assets\*.js) do set /a JS_COUNT+=1

if %JS_COUNT% LSS 1 (
    echo [ERRO] Nenhum arquivo JS encontrado em dist\assets\
    set ERRO=1
) else (
    echo [OK] %JS_COUNT% arquivo(s) JS encontrado(s)
)

REM Verificar arquivo CSS
set CSS_COUNT=0
for %%f in (dist\assets\*.css) do set /a CSS_COUNT+=1

if %CSS_COUNT% LSS 1 (
    echo [AVISO] Nenhum arquivo CSS encontrado em dist\assets\
) else (
    echo [OK] %CSS_COUNT% arquivo(s) CSS encontrado(s)
)

REM Verificar config.json
if not exist "dist\config.json" (
    echo [AVISO] dist\config.json não encontrado!
) else (
    echo [OK] config.json encontrado
)

REM Contar total de arquivos
set TOTAL=0
for /r dist %%f in (*) do set /a TOTAL+=1

echo.
echo Total de arquivos na dist: %TOTAL%
echo.

if %ERRO% EQU 1 (
    echo.
    echo [ERRO] Build incompleto! Execute 'npm run build' novamente.
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo   Build verificado com sucesso!
    echo ========================================
    echo.
    echo Todos os arquivos essenciais estão presentes.
    echo.
)

pause

