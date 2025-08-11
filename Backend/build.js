const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('🔨 Iniciando build do Scum Server Manager...');

// Verificar se é build de teste
const isTestBuild = process.argv.includes('--test');
const isNoAxiosBuild = process.argv.includes('--no-axios');

// 1. Criar pasta dist se não existir
const distPath = path.join(__dirname, 'dist');
if (!fs.existsSync(distPath)) {
    fs.mkdirSync(distPath, { recursive: true });
}

// 2. Copiar arquivos JSON, .env e configurações
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

// 3. Copiar arquivos de configuração específicos
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
            // Copiar diretório
            copyDir(sourcePath, destPath);
        } else {
            // Copiar arquivo
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

// 4. Compilar com pkg
console.log('🔧 Compilando executável...');

let entryFile, outputName;

if (isTestBuild) {
    entryFile = 'test-server.js';
    outputName = 'test-server';
} else if (isNoAxiosBuild) {
    entryFile = 'server-no-axios.js';
    outputName = 'scum-server-manager-backend-no-axios';
} else {
    entryFile = 'server.js';
    outputName = 'scum-server-manager-backend';
}

try {
    // Usar configuração específica para resolver problemas com módulos
    execSync(`pkg ${entryFile} --config pkg.config.json --out-path dist`, { stdio: 'inherit' });
    console.log('✅ Executável compilado com sucesso!');
} catch (error) {
    console.error('❌ Erro na compilação:', error.message);
    console.log('🔄 Tentando abordagem alternativa...');
    
    try {
        // Tentar sem configuração específica
        execSync(`pkg ${entryFile} --out-path dist`, { stdio: 'inherit' });
        console.log('✅ Executável compilado com sucesso!');
    } catch (error2) {
        console.error('❌ Erro na compilação alternativa:', error2.message);
        console.log('🔄 Tentando abordagem final...');
        
        try {
            // Tentar com configuração mínima
            execSync(`pkg ${entryFile} --targets node18-win-x64 --out-path dist`, { stdio: 'inherit' });
            console.log('✅ Executável compilado com sucesso!');
        } catch (error3) {
            console.error('❌ Erro na compilação final:', error3.message);
            process.exit(1);
        }
    }
}

// 5. Criar arquivo de configuração para o executável
const configInfo = {
    version: '1.0.0',
    buildDate: new Date().toISOString(),
    buildType: isTestBuild ? 'test' : (isNoAxiosBuild ? 'no-axios' : 'production'),
    instructions: [
        '1. Coloque o executável na pasta do projeto',
        '2. Os arquivos JSON devem estar na pasta src/data/',
        '3. Configure o arquivo src/data/server/config.json',
        '4. Configure o arquivo .env com suas variáveis',
        '5. Execute o .exe'
    ],
    configFiles: {
        'src/data/server/config.json': 'Configurações do servidor',
        'src/data/webhooks.json': 'Webhooks do Discord',
        'src/data/funny_statistics.json': 'Estatísticas divertidas',
        'src/data/auth/users.json': 'Usuários do sistema',
        'src/data/players/players.json': 'Dados dos jogadores',
        '.env': 'Variáveis de ambiente',
        'env.example': 'Template de variáveis',
        'nodemon.json': 'Configuração do nodemon'
    }
};

fs.writeFileSync(
    path.join(distPath, 'BUILD_INFO.json'),
    JSON.stringify(configInfo, null, 2)
);

// 6. Criar README para distribuição
const readmeContent = `# Scum Server Manager - Distribuição

## 📁 Arquivos de Configuração

### **Arquivos que podem ser editados:**
- \`src/data/server/config.json\` - Configurações do servidor
- \`src/data/webhooks.json\` - Webhooks do Discord  
- \`src/data/funny_statistics.json\` - Estatísticas divertidas
- \`src/data/auth/users.json\` - Usuários do sistema
- \`src/data/players/players.json\` - Dados dos jogadores
- \`.env\` - Variáveis de ambiente
- \`env.example\` - Template de variáveis
- \`nodemon.json\` - Configuração do nodemon

### **Como configurar:**
1. Copie \`env.example\` para \`.env\`
2. Edite o arquivo \`.env\` com suas configurações
3. Configure \`src/data/server/config.json\` com os caminhos do servidor
4. Adicione seus webhooks em \`src/data/webhooks.json\`
5. Execute o executável

## 🚀 Como executar:
\`\`\`bash
./${outputName}.exe
\`\`\`

## 📝 Notas:
- Os arquivos JSON ficam separados do executável
- Configurações podem ser alteradas sem recompilar
- O executável é standalone (não precisa do Node.js)
`;

fs.writeFileSync(
    path.join(distPath, 'README.md'),
    readmeContent
);

console.log('🎉 Build concluído!');
console.log('📦 Arquivos gerados em: dist/');

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