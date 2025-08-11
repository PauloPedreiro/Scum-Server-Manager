const fs = require('fs');
const path = require('path');

console.log('🔨 Criando distribuição simples...');

// 1. Criar pasta dist-simple
const distPath = path.join(__dirname, 'dist-simple');
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
    'nodemon.json',
    'package.json'
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

// 4. Criar start.bat para Windows
const startBat = `@echo off
echo 🚀 Iniciando Scum Server Manager...
echo.
echo 📦 Instalando dependências...
npm install
echo.
echo 🎯 Iniciando servidor...
node server.js
pause
`;

fs.writeFileSync(path.join(distPath, 'start.bat'), startBat);
console.log('✅ Criado: start.bat');

// 5. Criar start.sh para Linux/Mac
const startSh = `#!/bin/bash
echo "🚀 Iniciando Scum Server Manager..."
echo ""
echo "📦 Instalando dependências..."
npm install
echo ""
echo "🎯 Iniciando servidor..."
node server.js
`;

fs.writeFileSync(path.join(distPath, 'start.sh'), startSh);
console.log('✅ Criado: start.sh');

// 6. Criar package.json simplificado
const packageJson = {
    "name": "scum-server-manager-dist",
    "version": "1.0.0",
    "description": "Scum Server Manager - Distribuição",
    "main": "server.js",
    "scripts": {
        "start": "node server.js",
        "install-deps": "npm install",
        "dev": "nodemon server.js"
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
    },
    "devDependencies": {
        "nodemon": "^3.0.1"
    }
};

fs.writeFileSync(
    path.join(distPath, 'package.json'),
    JSON.stringify(packageJson, null, 2)
);
console.log('✅ Criado: package.json simplificado');

// 7. Criar README
const readmeContent = `# Scum Server Manager - Distribuição Simples

## 🚀 Como executar:

### Windows:
1. Clique duas vezes em \`start.bat\`
2. Aguarde a instalação das dependências
3. O servidor iniciará automaticamente

### Linux/Mac:
\`\`\`bash
chmod +x start.sh
./start.sh
\`\`\`

### Manual:
\`\`\`bash
npm install
node server.js
\`\`\`

## 📁 Arquivos de configuração:
- \`src/data/server/config.json\` - Configurações do servidor
- \`src/data/webhooks.json\` - Webhooks do Discord
- \`src/data/funny_statistics.json\` - Estatísticas divertidas
- \`.env\` - Variáveis de ambiente

## ✅ Vantagens desta distribuição:
- ✅ Não precisa compilar
- ✅ Funciona em qualquer sistema
- ✅ Fácil de instalar e executar
- ✅ Arquivos JSON separados e editáveis
- ✅ Sem problemas de dependências

## 🔧 Configuração:
1. Edite \`.env\` com suas configurações
2. Configure \`src/data/server/config.json\`
3. Adicione webhooks em \`src/data/webhooks.json\`
4. Execute \`start.bat\` (Windows) ou \`start.sh\` (Linux/Mac)

## 📡 Acesso:
- API: http://localhost:3000
- Health: http://localhost:3000/health
- Estatísticas: http://localhost:3000/funny-stats
- Jogadores: http://localhost:3000/players
`;

fs.writeFileSync(path.join(distPath, 'README.md'), readmeContent);
console.log('✅ Criado: README.md');

console.log('🎉 Distribuição simples criada!');
console.log('📦 Arquivos gerados em: dist-simple/');
console.log('');
console.log('📋 Para distribuir:');
console.log('1. Copie a pasta dist-simple/');
console.log('2. Execute start.bat (Windows) ou start.sh (Linux/Mac)');
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