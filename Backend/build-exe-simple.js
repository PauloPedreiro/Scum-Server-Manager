const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('🔨 Criando executável simples...');

// 1. Criar pasta dist-exe
const distPath = path.join(__dirname, 'dist-exe');
if (!fs.existsSync(distPath)) {
    fs.mkdirSync(distPath, { recursive: true });
}

// 2. Copiar arquivos necessários
const copyFiles = [
    'src/data',
    'src/config',
    'routes',
    'src/middleware',
    'src/bot.js',
    'src/funny_statistics.js',
    'src/logger.js',
    'src/scheduler.js',
    'scripts'
];

const configFiles = [
    '.env',
    'env.example',
    'nodemon.json'
];

console.log('📁 Copiando arquivos...');

// Copiar diretórios
copyFiles.forEach(file => {
    const sourcePath = path.join(__dirname, file);
    const destPath = path.join(distPath, file);
    
    if (fs.existsSync(sourcePath)) {
        if (fs.lstatSync(sourcePath).isDirectory()) {
            copyDir(sourcePath, destPath);
        } else {
            copyFile(sourcePath, destPath);
        }
        console.log(`✅ Copiado: ${file}`);
    } else {
        console.log(`⚠️  Arquivo não encontrado: ${file}`);
    }
});

// Copiar arquivos de configuração
configFiles.forEach(file => {
    const sourcePath = path.join(__dirname, file);
    const destPath = path.join(distPath, file);
    
    if (fs.existsSync(sourcePath)) {
        copyFile(sourcePath, destPath);
        console.log(`✅ Copiado: ${file}`);
    } else {
        console.log(`⚠️  Arquivo não encontrado: ${file}`);
    }
});

// 3. Copiar server-no-axios.js como server.js
copyFile(
    path.join(__dirname, 'server-no-axios.js'),
    path.join(distPath, 'server.js')
);
console.log('✅ Copiado: server.js (versão sem Axios)');

// 4. Criar package.json simplificado para pkg
const packageJson = {
    "name": "scum-server-manager-exe",
    "version": "1.0.0",
    "description": "Scum Server Manager - Executável",
    "main": "server.js",
    "bin": "server.js",
    "scripts": {
        "start": "node server.js"
    },
    "pkg": {
        "scripts": ["server.js"],
        "assets": [
            "src/**/*",
            "routes/**/*",
            "scripts/**/*",
            ".env",
            "env.example",
            "nodemon.json"
        ],
        "targets": ["node18-win-x64"],
        "outputPath": "dist-exe"
    },
    "dependencies": {
        "bcrypt": "^5.1.1",
        "cors": "^2.8.5",
        "discord.js": "^14.21.0",
        "dotenv": "^16.3.1",
        "express": "^4.18.2",
        "glob": "^10.4.5",
        "jsonwebtoken": "^9.0.2",
        "luxon": "^3.7.1",
        "sqlite3": "^5.1.7"
    }
};

fs.writeFileSync(
    path.join(distPath, 'package.json'),
    JSON.stringify(packageJson, null, 2)
);
console.log('✅ Criado: package.json para pkg');

// 5. Instalar dependências
console.log('📦 Instalando dependências...');
try {
    execSync('npm install', { cwd: distPath, stdio: 'inherit' });
    console.log('✅ Dependências instaladas');
} catch (error) {
    console.error('❌ Erro ao instalar dependências:', error.message);
}

// 6. Compilar com pkg
console.log('🔧 Compilando executável...');
try {
    execSync('npx pkg . --targets node18-win-x64 --output ScumServerManager.exe', { 
        cwd: distPath, 
        stdio: 'inherit' 
    });
    console.log('✅ Executável compilado com sucesso!');
} catch (error) {
    console.error('❌ Erro na compilação:', error.message);
    console.log('🔄 Tentando abordagem alternativa...');
    
    try {
        execSync('npx pkg server.js --targets node18-win-x64 --output ScumServerManager.exe', { 
            cwd: distPath, 
            stdio: 'inherit' 
        });
        console.log('✅ Executável compilado com sucesso!');
    } catch (error2) {
        console.error('❌ Erro na compilação alternativa:', error2.message);
        process.exit(1);
    }
}

// 7. Criar start.bat para o executável
const startBat = `@echo off
echo 🚀 Iniciando Scum Server Manager...
echo.
echo 📡 Servidor rodando em: http://localhost:3000
echo 🔧 Health check: http://localhost:3000/health
echo 📊 Estatísticas: http://localhost:3000/funny-stats
echo 👥 Jogadores: http://localhost:3000/players
echo ⚙️  Configurações: http://localhost:3000/config
echo.
echo Pressione Ctrl+C para parar o servidor
echo.
ScumServerManager.exe
pause
`;

fs.writeFileSync(path.join(distPath, 'start.bat'), startBat);
console.log('✅ Criado: start.bat');

// 8. Criar README
const readmeContent = `# Scum Server Manager - Executável

## 🚀 Como executar:

### Opção 1 - Executável direto:
\`\`\`bash
ScumServerManager.exe
\`\`\`

### Opção 2 - Com script:
\`\`\`bash
start.bat
\`\`\`

## 📁 Arquivos de configuração:
- \`src/data/server/config.json\` - Configurações do servidor
- \`src/data/webhooks.json\` - Webhooks do Discord
- \`src/data/funny_statistics.json\` - Estatísticas divertidas
- \`.env\` - Variáveis de ambiente

## ✅ Vantagens:
- ✅ Executável standalone
- ✅ Não precisa do Node.js instalado
- ✅ Arquivos JSON separados e editáveis
- ✅ Funciona em qualquer Windows 10/11

## 📡 Endpoints:
- API: http://localhost:3000
- Health: http://localhost:3000/health
- Estatísticas: http://localhost:3000/funny-stats
- Jogadores: http://localhost:3000/players
- Configurações: http://localhost:3000/config

## 🔧 Configuração:
1. Edite \`.env\` com suas configurações
2. Configure \`src/data/server/config.json\`
3. Adicione webhooks em \`src/data/webhooks.json\`
4. Execute \`ScumServerManager.exe\`
`;

fs.writeFileSync(path.join(distPath, 'README.md'), readmeContent);
console.log('✅ Criado: README.md');

console.log('🎉 Executável criado!');
console.log('📦 Arquivos gerados em: dist-exe/');
console.log('');
console.log('📋 Para distribuir:');
console.log('1. Copie a pasta dist-exe/');
console.log('2. Execute ScumServerManager.exe');
console.log('3. Configure os arquivos JSON conforme necessário');

// Funções auxiliares
function copyDir(src, dest) {
    if (!fs.existsSync(dest)) {
        fs.mkdirSync(dest, { recursive: true });
    }
    
    const files = fs.readdirSync(src);
    files.forEach(file => {
        const srcPath = path.join(src, file);
        const destPath = path.join(dest, file);
        
        if (fs.lstatSync(srcPath).isDirectory()) {
            copyDir(srcPath, destPath);
        } else {
            copyFile(srcPath, destPath);
        }
    });
}

function copyFile(src, dest) {
    const destDir = path.dirname(dest);
    if (!fs.existsSync(destDir)) {
        fs.mkdirSync(destDir, { recursive: true });
    }
    fs.copyFileSync(src, dest);
}