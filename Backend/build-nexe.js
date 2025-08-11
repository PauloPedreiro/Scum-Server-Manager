const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('🔨 Iniciando build com Nexe...');

// 1. Criar pasta dist se não existir
const distPath = path.join(__dirname, 'dist-nexe');
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

// 3. Instalar Nexe se não estiver instalado
console.log('📦 Verificando Nexe...');
try {
    execSync('nexe --version', { stdio: 'pipe' });
    console.log('✅ Nexe já está instalado');
} catch (error) {
    console.log('📦 Instalando Nexe...');
    execSync('npm install -g nexe', { stdio: 'inherit' });
}

// 4. Compilar com Nexe
console.log('🔧 Compilando executável com Nexe...');

try {
    // Usar server-no-axios.js para evitar problemas
    execSync('nexe server-no-axios.js --build --output dist-nexe/scum-server-manager.exe', { stdio: 'inherit' });
    console.log('✅ Executável compilado com sucesso!');
} catch (error) {
    console.error('❌ Erro na compilação:', error.message);
    console.log('🔄 Tentando com configuração alternativa...');
    
    try {
        execSync('nexe server-no-axios.js --build --target win32-x64-14.15.3 --output dist-nexe/scum-server-manager.exe', { stdio: 'inherit' });
        console.log('✅ Executável compilado com sucesso!');
    } catch (error2) {
        console.error('❌ Erro na compilação alternativa:', error2.message);
        process.exit(1);
    }
}

// 5. Criar README
const readmeContent = `# Scum Server Manager - Build Nexe

## 🚀 Como executar:
\`\`\`bash
./scum-server-manager.exe
\`\`\`

## 📁 Arquivos de configuração:
- \`src/data/server/config.json\` - Configurações do servidor
- \`src/data/webhooks.json\` - Webhooks do Discord
- \`src/data/funny_statistics.json\` - Estatísticas divertidas
- \`.env\` - Variáveis de ambiente

## ✅ Vantagens do Nexe:
- ✅ Mais estável que Pkg
- ✅ Melhor compatibilidade
- ✅ Menos problemas com módulos
- ✅ Executável menor
`;

fs.writeFileSync(
    path.join(distPath, 'README.md'),
    readmeContent
);

console.log('🎉 Build com Nexe concluído!');
console.log('📦 Arquivos gerados em: dist-nexe/');

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