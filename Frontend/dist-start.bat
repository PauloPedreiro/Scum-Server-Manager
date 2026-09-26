@echo off
chcp 65001 >nul
title SSM 3.0 - Iniciando Produção

echo.
echo ========================================
echo   SSM 3.0 Frontend - Modo Produção
echo ========================================
echo.

REM Verificar se estamos na pasta dist
if not exist "index.html" (
    echo [ERRO] index.html não encontrado!
    echo Certifique-se de executar este arquivo na pasta dist/.
    echo.
    pause
    exit /b 1
)

REM Verificar se serve está instalado
set SERVE_CMD=
where serve >nul 2>&1
if not errorlevel 1 (
    set SERVE_CMD=serve
    echo [OK] serve encontrado no PATH!
    echo.
) else (
    REM Tentar usar npx serve (não precisa estar instalado globalmente)
    where npx >nul 2>&1
    if not errorlevel 1 (
        echo [INFO] serve não encontrado no PATH, usando npx...
        set SERVE_CMD=npx serve
        echo.
    ) else (
        echo [AVISO] 'serve' não encontrado e 'npx' não disponível.
        echo.
        echo Deseja instalar serve globalmente? (S/N)
        set /p INSTALL_SERVE=
        if /i "%INSTALL_SERVE%"=="S" (
            echo.
            echo Instalando serve globalmente...
            call npm install -g serve
            if errorlevel 1 (
                echo [ERRO] Falha ao instalar serve!
                echo.
                echo Alternativa: Use http-server ou Python
                echo   http-server: npm install -g http-server
                echo   Python: python -m http.server 5173
                pause
                exit /b 1
            )
            echo.
            echo Serve instalado com sucesso!
            echo.
            REM Tentar usar serve diretamente após instalação
            set SERVE_CMD=serve
            REM Verificar se funciona
            %SERVE_CMD% --version >nul 2>&1
            if errorlevel 1 (
                echo [AVISO] serve instalado mas pode não estar no PATH atual.
                echo Tentando usar npx como alternativa...
                where npx >nul 2>&1
                if not errorlevel 1 (
                    set SERVE_CMD=npx serve
                ) else (
                    echo.
                    echo Por favor, feche e abra o terminal novamente.
                    echo Depois execute este script novamente.
                    pause
                    exit /b 1
                )
            )
            echo [OK] serve pronto para uso!
            echo.
        ) else (
            echo.
            echo Opções alternativas:
            echo   1. Instale serve: npm install -g serve
            echo   2. Use http-server: npm install -g http-server
            echo   3. Use Python: python -m http.server 5173
            echo.
            pause
            exit /b 1
        )
    )
)

echo.
echo ========================================
echo   Iniciando servidor de produção...
echo ========================================
echo.
echo Servidor será iniciado em:
echo   - Local: http://localhost:5173
echo   - Rede: http://[SEU_IP]:5173
echo Para parar o servidor, pressione Ctrl+C
echo.
echo Aguarde alguns segundos...
echo.
echo ========================================
echo.

REM Executar o comando de produção
REM -s: modo SPA (Single Page Application)
REM -l: listen endpoint (0.0.0.0:5173 = todas as interfaces, aceita localhost e IP)
REM -c: usar serve.json se existir (garante que config.json seja servido corretamente)
if exist "serve.json" (
    %SERVE_CMD% -s . -l tcp://0.0.0.0:5173 -c serve.json
) else (
    %SERVE_CMD% -s . -l tcp://0.0.0.0:5173
)

REM Se o comando falhar, manter a janela aberta
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao iniciar o servidor!
    echo.
    echo Verifique se:
    echo   - serve está instalado: npm install -g serve
    echo   - A porta 5173 está disponível
    echo   - Você tem permissões adequadas
    echo.
    pause
    exit /b 1
)

