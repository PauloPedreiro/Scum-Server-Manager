@echo off
title SCUM Server Manager - Alterar Senha Rápido
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════════════════════╗
echo  ║                    SCUM SERVER MANAGER - ALTERAR SENHA                   ║
echo  ╚══════════════════════════════════════════════════════════════════════════╝
echo.
echo  Usuários disponíveis:
echo.
node -e "const fs = require('fs'); const users = JSON.parse(fs.readFileSync('src/data/auth/users.json', 'utf8')); users.users.forEach(user => console.log('  - ' + user.username + (user.active ? ' (Ativo)' : ' (Inativo)')));"
echo.
set /p username=Digite o nome do usuário: 
set /p newpassword=Digite a nova senha: 
set /p confirmpassword=Confirme a nova senha: 

if not "%newpassword%"=="%confirmpassword%" (
    echo.
    echo  ❌ ERRO: As senhas não coincidem!
    echo.
    pause
    exit
)

echo.
echo  🔧 Gerando nova senha para: %username%
echo.

node scripts/generate-password.js %username% %newpassword%

if %errorlevel% equ 0 (
    echo.
    echo  ✅ Senha alterada com sucesso!
    echo  📝 Nova senha: %newpassword%
    echo.
) else (
    echo.
    echo  ❌ Erro ao alterar senha!
    echo.
)

echo.
echo  Pressione qualquer tecla para sair...
pause >nul 