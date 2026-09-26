@echo off
chcp 65001 >nul
title SSM 3.0 - Iniciando Produção

echo.
echo ========================================
echo   SSM 3.0 Frontend - Modo Produção
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

REM Verificar se a pasta dist existe
if not exist "dist" (
    echo [AVISO] Pasta 'dist' não encontrada!
    echo.
    echo Deseja fazer o build agora? (S/N)
    set /p BUILD_NOW=
    if /i "%BUILD_NOW%"=="S" (
        echo.
        echo Executando build...
        call npm run build
        if errorlevel 1 (
            echo [ERRO] Build falhou!
            pause
            exit /b 1
        )
        echo.
        echo Build concluído com sucesso!
        echo.
    ) else (
        echo.
        echo Execute 'npm run build' primeiro e tente novamente.
        pause
        exit /b 1
    )
)

REM Verificar se serve está instalado
where serve >nul 2>&1
if errorlevel 1 (
    echo [AVISO] 'serve' não encontrado globalmente.
    echo.
    echo Deseja instalar agora? (S/N)
    set /p INSTALL_SERVE=
    if /i "%INSTALL_SERVE%"=="S" (
        echo.
        echo Instalando serve globalmente...
        call npm install -g serve
        if errorlevel 1 (
            echo [ERRO] Falha ao instalar serve!
            pause
            exit /b 1
        )
        echo.
        echo Serve instalado com sucesso!
        echo.
    ) else (
        echo.
        echo Execute 'npm install -g serve' primeiro.
        pause
        exit /b 1
    )
)

echo.
echo Iniciando servidor de produção...
echo.
echo Servidor será iniciado em: http://localhost:5173
echo Para parar o servidor, pressione Ctrl+C
echo.
echo ========================================
echo.

REM Executar o comando de produção
call npm run start:prod

REM Se o comando falhar, manter a janela aberta
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao iniciar o servidor!
    pause
    exit /b 1
)

