@echo off
chcp 65001 >nul
title SSM 3.0 - Build para Produção

echo.
echo ========================================
echo   SSM 3.0 Frontend - Build Produção
echo ========================================
echo.

REM Verificar se estamos no diretório correto
if not exist "package.json" (
    echo [ERRO] package.json não encontrado!
    echo Certifique-se de executar este arquivo na raiz do projeto.
    echo.
    pause
    exit /b 1
)

echo Limpando build anterior...
if exist "dist" (
    rmdir /s /q dist
    echo Pasta dist removida.
)

echo.
echo Gerando apple-touch-icon.png (iPhone PWA)...
python tools\convert_to_ico.py "src\assets\logo\Ativado.webp" "public\apple-touch-icon.png" 180
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao gerar public\apple-touch-icon.png
    echo Verifique se Python esta instalado e tente novamente.
    pause
    exit /b 1
)

echo.
echo Executando build...
echo.

REM Executar o build
call npm run build

if errorlevel 1 (
    echo.
    echo [ERRO] Build falhou!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Build concluído com sucesso!
echo ========================================
echo.
echo Arquivos gerados na pasta: dist/
echo.
echo Para iniciar o servidor de produção:
echo   npm run start:prod
echo.
echo Ou execute: start-prod.bat
echo.

pause

