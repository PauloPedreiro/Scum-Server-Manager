@echo off
title SCUM Server Manager - Gerenciador de Senhas
color 0A
mode con: cols=80 lines=25

:menu
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════════════╗
echo  ║                    SCUM SERVER MANAGER - GERENCIADOR DE SENHAS           ║
echo  ╠══════════════════════════════════════════════════════════════════════════╣
echo  ║                                                                          ║
echo  ║  [1] Alterar senha de usuário                                           ║
echo  ║  [2] Listar usuários cadastrados                                        ║
echo  ║  [3] Criar novo usuário                                                 ║
echo  ║  [4] Desativar usuário                                                  ║
echo  ║  [5] Ativar usuário                                                     ║
echo  ║  [6] Sair                                                               ║
echo  ║                                                                          ║
echo  ╚══════════════════════════════════════════════════════════════════════════╝
echo.
set /p opcao=Escolha uma opção (1-6): 

if "%opcao%"=="1" goto alterar_senha
if "%opcao%"=="2" goto listar_usuarios
if "%opcao%"=="3" goto criar_usuario
if "%opcao%"=="4" goto desativar_usuario
if "%opcao%"=="5" goto ativar_usuario
if "%opcao%"=="6" goto sair
goto menu

:alterar_senha
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════════════╗
echo  ║                           ALTERAR SENHA DE USUÁRIO                      ║
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
    goto alterar_senha
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

pause
goto menu

:listar_usuarios
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════════════╗
echo  ║                           USUÁRIOS CADASTRADOS                          ║
echo  ╚══════════════════════════════════════════════════════════════════════════╝
echo.
node -e "const fs = require('fs'); const users = JSON.parse(fs.readFileSync('src/data/auth/users.json', 'utf8')); console.log('ID\t\tUsuário\t\t\tRole\t\tStatus\t\tÚltimo Login'); console.log('─'.repeat(80)); users.users.forEach(user => { const status = user.active ? '✅ Ativo' : '❌ Inativo'; const lastLogin = user.last_login ? new Date(user.last_login).toLocaleString('pt-BR') : 'Nunca'; console.log(`${user.id}\t\t${user.username.padEnd(16)}\t${user.role.padEnd(12)}\t${status}\t${lastLogin}`); });"
echo.
pause
goto menu

:criar_usuario
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════════════╗
echo  ║                           CRIAR NOVO USUÁRIO                           ║
echo  ╚══════════════════════════════════════════════════════════════════════════╝
echo.
set /p newusername=Digite o nome do novo usuário: 
set /p newuserpassword=Digite a senha do novo usuário: 
set /p newuserrole=Digite o role (admin/user): 

echo.
echo  🔧 Criando novo usuário: %newusername%
echo.

node -e "
const fs = require('fs');
const bcrypt = require('bcrypt');
const path = require('path');

const usersPath = path.join('src', 'data', 'auth', 'users.json');
const usersData = JSON.parse(fs.readFileSync(usersPath, 'utf8'));

// Verificar se usuário já existe
const existingUser = usersData.users.find(u => u.username === process.argv[2]);
if (existingUser) {
    console.log('❌ ERRO: Usuário já existe!');
    process.exit(1);
}

// Gerar hash da senha
const saltRounds = 10;
const passwordHash = bcrypt.hashSync(process.argv[3], saltRounds);

// Criar novo usuário
const newUser = {
    id: (usersData.users.length + 1).toString(),
    username: process.argv[2],
    password: passwordHash,
    role: process.argv[4] || 'user',
    created_at: new Date().toISOString(),
    last_login: null,
    active: true
};

usersData.users.push(newUser);

// Salvar arquivo
fs.writeFileSync(usersPath, JSON.stringify(usersData, null, 2));

console.log('✅ Usuário criado com sucesso!');
console.log('📝 Detalhes:');
console.log('   - Usuário:', process.argv[2]);
console.log('   - Role:', process.argv[4] || 'user');
console.log('   - Status: Ativo');
" %newusername% %newuserpassword% %newuserrole%

if %errorlevel% equ 0 (
    echo.
    echo  ✅ Usuário criado com sucesso!
    echo.
) else (
    echo.
    echo  ❌ Erro ao criar usuário!
    echo.
)

pause
goto menu

:desativar_usuario
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════════════╗
echo  ║                           DESATIVAR USUÁRIO                             ║
echo  ╚══════════════════════════════════════════════════════════════════════════╝
echo.
echo  Usuários ativos:
echo.
node -e "const fs = require('fs'); const users = JSON.parse(fs.readFileSync('src/data/auth/users.json', 'utf8')); users.users.filter(user => user.active).forEach(user => console.log('  - ' + user.username));"
echo.
set /p username=Digite o nome do usuário para desativar: 

node -e "
const fs = require('fs');
const path = require('path');

const usersPath = path.join('src', 'data', 'auth', 'users.json');
const usersData = JSON.parse(fs.readFileSync(usersPath, 'utf8'));

const user = usersData.users.find(u => u.username === process.argv[2]);
if (!user) {
    console.log('❌ ERRO: Usuário não encontrado!');
    process.exit(1);
}

if (!user.active) {
    console.log('❌ ERRO: Usuário já está inativo!');
    process.exit(1);
}

user.active = false;

fs.writeFileSync(usersPath, JSON.stringify(usersData, null, 2));

console.log('✅ Usuário desativado com sucesso!');
" %username%

if %errorlevel% equ 0 (
    echo.
    echo  ✅ Usuário desativado com sucesso!
    echo.
) else (
    echo.
    echo  ❌ Erro ao desativar usuário!
    echo.
)

pause
goto menu

:ativar_usuario
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════════════╗
echo  ║                            ATIVAR USUÁRIO                               ║
echo  ╚══════════════════════════════════════════════════════════════════════════╝
echo.
echo  Usuários inativos:
echo.
node -e "const fs = require('fs'); const users = JSON.parse(fs.readFileSync('src/data/auth/users.json', 'utf8')); users.users.filter(user => !user.active).forEach(user => console.log('  - ' + user.username));"
echo.
set /p username=Digite o nome do usuário para ativar: 

node -e "
const fs = require('fs');
const path = require('path');

const usersPath = path.join('src', 'data', 'auth', 'users.json');
const usersData = JSON.parse(fs.readFileSync(usersPath, 'utf8'));

const user = usersData.users.find(u => u.username === process.argv[2]);
if (!user) {
    console.log('❌ ERRO: Usuário não encontrado!');
    process.exit(1);
}

if (user.active) {
    console.log('❌ ERRO: Usuário já está ativo!');
    process.exit(1);
}

user.active = true;

fs.writeFileSync(usersPath, JSON.stringify(usersData, null, 2));

console.log('✅ Usuário ativado com sucesso!');
" %username%

if %errorlevel% equ 0 (
    echo.
    echo  ✅ Usuário ativado com sucesso!
    echo.
) else (
    echo.
    echo  ❌ Erro ao ativar usuário!
    echo.
)

pause
goto menu

:sair
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════════════╗
echo  ║                           OBRIGADO POR USAR!                            ║
echo  ║                    SCUM SERVER MANAGER - GERENCIADOR DE SENHAS          ║
echo  ╚══════════════════════════════════════════════════════════════════════════╝
echo.
echo  👋 Saindo do sistema...
echo.
timeout /t 3 /nobreak >nul
exit 