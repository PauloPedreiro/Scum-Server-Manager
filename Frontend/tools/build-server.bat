@echo off
setlocal EnableExtensions
chcp 65001 >nul
echo.
echo ========================================
echo   Build do Servidor Go - SSM 3.0
echo ========================================
echo.

REM Verificar se Go esta instalado
where go >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Go nao esta instalado!
    echo.
    echo Instale Go: https://golang.org/dl/
    echo.
    echo Apos instalar, adicione Go ao PATH e execute este script novamente.
    pause
    exit /b 1
)

echo [OK] Go encontrado!
go version
echo.

echo Gerando icones (System Tray / PWA iPhone)...
REM Gerar Ativado.ico e Parado.ico para o systray (Windows usa .ico)
python convert_to_ico.py "..\src\assets\logo\Ativado.webp" "server\Ativado.ico"
if errorlevel 1 (
    echo [ERRO] Falha ao gerar server\Ativado.ico
    pause
    exit /b 1
)
python convert_to_ico.py "..\src\assets\logo\Parado.webp" "server\Parado.ico"
if errorlevel 1 (
    echo [ERRO] Falha ao gerar server\Parado.ico
    pause
    exit /b 1
)

REM Gerar apple-touch-icon.png (iPhone) dentro do public/ para ir junto no build
python convert_to_ico.py "..\src\assets\logo\Ativado.webp" "..\public\apple-touch-icon.png" 180
if errorlevel 1 (
    echo [ERRO] Falha ao gerar public\apple-touch-icon.png
    pause
    exit /b 1
)

echo [OK] Icones gerados!
echo.

echo Executando build do Frontend (npm run build)...
pushd ..
if errorlevel 1 (
    echo [ERRO] Nao foi possivel acessar a raiz do projeto Frontend!
    pause
    exit /b 1
)
call npm run build
set "npm_errorlevel=%errorlevel%"
popd
if not "%npm_errorlevel%"=="0" (
    echo.
    echo [ERRO] Build do Frontend falhou!
    pause
    exit /b 1
)

echo [OK] Build do Frontend concluido!
echo.

REM Verificar se dist/ existe
if not exist "..\dist\index.html" (
    echo [ERRO] Pasta dist/ nao encontrada!
    echo.
    echo Execute 'npm run build' primeiro.
    pause
    exit /b 1
)

echo [OK] Pasta dist/ encontrada!
echo.

REM Copiar arquivos de dist/ para server/dist/ (necessario para embed)
echo Copiando arquivos de dist/ para server/dist/...
if exist "server\dist" (
    rmdir /s /q "server\dist"
)
xcopy /E /I /Y "..\dist" "server\dist" >nul
if errorlevel 1 (
    echo [ERRO] Falha ao copiar arquivos de dist/!
    pause
    exit /b 1
)
echo [OK] Arquivos copiados para server/dist/

REM Copiar Ativado.ico para server/ (necessario para embed)
if exist "server\Ativado.ico" (
    echo [OK] Ativado.ico encontrado em tools/server/
) else (
    echo [AVISO] Ativado.ico nao encontrado em tools/server/
)
echo.
REM Garantir que os icones de tray existem dentro de tools/server (go:embed)
if exist "server\Ativado.ico" (
    echo [OK] Ativado.ico pronto para embed
) else (
    echo [ERRO] server\Ativado.ico nao encontrado!
    pause
    exit /b 1
)
if exist "server\Parado.ico" (
    echo [OK] Parado.ico pronto para embed
) else (
    echo [ERRO] server\Parado.ico nao encontrado!
    pause
    exit /b 1
)
echo.

REM Entrar na pasta do servidor
cd server
if errorlevel 1 (
    echo [ERRO] Pasta tools/server/ nao encontrada!
    pause
    exit /b 1
)

echo Compilando servidor...
echo.

REM Verificar se rsrc esta instalado (para adicionar icone)
where rsrc >nul 2>&1
set "has_rsrc=%errorlevel%"
if "%has_rsrc%"=="0" goto :RSRC_OK

echo [AVISO] rsrc nao esta instalado. Instale com: go install github.com/akavel/rsrc@latest
echo [AVISO] Continuando sem icone...
goto :RSRC_END

:RSRC_OK
echo Adicionando icone (Ativado.ico)...
if exist "Ativado.ico" (
    rsrc -ico Ativado.ico -o rsrc.syso
    if errorlevel 1 (
        echo [AVISO] Erro ao adicionar icone, continuando sem icone...
    ) else (
        echo [OK] Icone adicionado!
    )
) else (
    echo [AVISO] Ativado.ico nao encontrado, continuando sem icone...
)

:RSRC_END

echo.
echo Copiando Mine_01.ico para dist/ (toast notifications)...
if exist "..\Mine_01.ico" (
    copy /Y "..\Mine_01.ico" "..\dist\Mine_01.ico" >nul
    echo [OK] Mine_01.ico copiado para dist/
) else (
    echo [AVISO] Mine_01.ico nao encontrado em tools/
)
echo.
echo Compilando servidor Go...
echo.

echo Limpando cache do Go...
go clean -cache -modcache
echo.

REM Garantir pasta de saida e compilar com otimizacoes
set "DIST_DIR=%CD%\..\..\dist"
if not exist "%DIST_DIR%" (
    mkdir "%DIST_DIR%" >nul 2>&1
)
go build -ldflags="-s -w -H windowsgui" -o "%DIST_DIR%\SSM-Server.exe"
if errorlevel 1 (
    echo [ERRO] Falha na compilacao!
    pause
    exit /b 1
)

REM Limpar arquivos temporarios (opcional)
if exist "dist" (
    echo.
    echo Limpando arquivos temporarios...
    rmdir /s /q "dist"
)

echo.
echo ========================================
echo [OK] Servidor compilado com sucesso!
echo ========================================
echo.
echo Executavel: ..\..\dist\SSM-Server.exe
echo.
echo Para executar:
echo   1. Va para a pasta dist/
echo   2. Execute SSM-Server.exe
echo   3. O navegador abrira automaticamente
echo.
pause

