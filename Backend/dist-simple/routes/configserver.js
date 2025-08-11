const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { DateTime } = require('luxon');
const logger = require('../src/logger');

// Configurações
const SCUM_CONFIG_PATH = 'C:/Servers/scum/SCUM/Saved/Config/WindowsServer';
const BACKUP_PATH = 'src/data/configserver/backups';

// Criar diretórios necessários
const createDirectories = () => {
    const dirs = [
        BACKUP_PATH,
        'src/data/configserver'
    ];
    
    dirs.forEach(dir => {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    });
};

// Função para criar backup
const createBackup = (filename) => {
    try {
        const sourcePath = path.join(SCUM_CONFIG_PATH, filename);
        const timestamp = DateTime.now().toFormat('yyyy-MM-dd_HH-mm-ss');
        const backupFilename = `${filename.replace('.', '_')}_${timestamp}.backup`;
        const backupPath = path.join(BACKUP_PATH, backupFilename);
        
        if (fs.existsSync(sourcePath)) {
            fs.copyFileSync(sourcePath, backupPath);
            logger.info(`Backup criado: ${backupFilename}`);
            return backupFilename;
        }
        return null;
    } catch (error) {
        logger.error('Erro ao criar backup', { error: error.message, filename });
        return null;
    }
};

// Função para restaurar backup
const restoreBackup = (backupFilename) => {
    try {
        const backupPath = path.join(BACKUP_PATH, backupFilename);
        const originalFilename = backupFilename.split('_').slice(0, -1).join('_').replace('_', '.');
        const targetPath = path.join(SCUM_CONFIG_PATH, originalFilename);
        
        if (fs.existsSync(backupPath)) {
            fs.copyFileSync(backupPath, targetPath);
            logger.info(`Backup restaurado: ${backupFilename}`);
            return true;
        }
        return false;
    } catch (error) {
        logger.error('Erro ao restaurar backup', { error: error.message, backupFilename });
        return false;
    }
};

// Função para listar backups
const listBackups = () => {
    try {
        if (!fs.existsSync(BACKUP_PATH)) {
            return [];
        }
        
        const files = fs.readdirSync(BACKUP_PATH);
        return files
            .filter(file => file.endsWith('.backup'))
            .map(file => {
                const stats = fs.statSync(path.join(BACKUP_PATH, file));
                return {
                    filename: file,
                    size: stats.size,
                    created: stats.birthtime,
                    originalFile: file.split('_').slice(0, -1).join('_').replace('_', '.')
                };
            })
            .sort((a, b) => new Date(b.created) - new Date(a.created));
    } catch (error) {
        logger.error('Erro ao listar backups', { error: error.message });
        return [];
    }
};

// Função para validar formato INI
const validateIniFormat = (content) => {
    try {
        const lines = content.split('\n');
        const errors = [];
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            // Linha vazia - permitir
            if (line === '') {
                continue;
            }
            
            // Comentário - permitir
            if (line.startsWith(';')) {
                continue;
            }
            
            // Seção - deve ter [nome]
            if (line.startsWith('[') && line.endsWith(']')) {
                const sectionName = line.slice(1, -1).trim();
                if (sectionName === '') {
                    errors.push(`Linha ${i + 1}: Nome da seção vazio`);
                }
                continue;
            }
            
            // Chave=valor - deve ter pelo menos uma chave
            if (line.includes('=')) {
                const [key, value] = line.split('=', 2);
                if (!key.trim()) {
                    errors.push(`Linha ${i + 1}: Chave vazia`);
                }
                continue;
            }
            
            // Linha com apenas espaços - permitir
            if (line === '') {
                continue;
            }
            
            // Qualquer outra linha é considerada válida (pode ser configuração especial)
            // Não vamos rejeitar linhas que não seguem o padrão exato
        }
        
        return {
            isValid: errors.length === 0,
            errors
        };
    } catch (error) {
        return {
            isValid: false,
            errors: [`Erro ao validar formato INI: ${error.message}`]
        };
    }
};

// Função para validar formato JSON
const validateJsonFormat = (content) => {
    try {
        JSON.parse(content);
        return {
            valid: true,
            errors: []
        };
    } catch (error) {
        return {
            valid: false,
            errors: [`Erro de JSON: ${error.message}`]
        };
    }
};

// Função para ler arquivo de configuração
const readConfigFile = (filename) => {
    try {
        const filePath = path.join(SCUM_CONFIG_PATH, filename);
        
        if (!fs.existsSync(filePath)) {
            return {
                success: false,
                error: 'Arquivo não encontrado'
            };
        }
        
        const content = fs.readFileSync(filePath, 'utf8');
        const stats = fs.statSync(filePath);
        
        return {
            success: true,
            content,
            stats: {
                size: stats.size,
                modified: stats.mtime,
                created: stats.birthtime
            }
        };
    } catch (error) {
        logger.error('Erro ao ler arquivo de configuração', { error: error.message, filename });
        return {
            success: false,
            error: error.message
        };
    }
};

// Função para atualizar valor específico em arquivo INI
const updateIniValue = (filename, section, key, value) => {
    try {
        const filePath = path.join(SCUM_CONFIG_PATH, filename);
        
        if (!fs.existsSync(filePath)) {
            return {
                success: false,
                error: 'Arquivo não encontrado'
            };
        }
        
        // Criar backup antes de modificar
        const backupFilename = createBackup(filename);
        
        // Ler conteúdo atual
        const content = fs.readFileSync(filePath, 'utf8');
        const lines = content.split('\n');
        
        let currentSection = null;
        let keyFound = false;
        let sectionFound = false;
        
        // Procurar pela seção e chave
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            // Verificar se é uma seção
            if (line.startsWith('[') && line.endsWith(']')) {
                currentSection = line.slice(1, -1);
                if (currentSection === section) {
                    sectionFound = true;
                }
                continue;
            }
            
            // Se estamos na seção correta, procurar pela chave
            if (sectionFound && line.startsWith(key + '=')) {
                lines[i] = `${key}=${value}`;
                keyFound = true;
                break;
            }
        }
        
        // Se não encontrou a chave na seção, adicionar
        if (sectionFound && !keyFound) {
            // Encontrar o final da seção
            let sectionEndIndex = lines.length;
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                if (line.startsWith('[') && line.endsWith(']') && line.slice(1, -1) !== section) {
                    sectionEndIndex = i;
                    break;
                }
            }
            
            // Adicionar a nova chave no final da seção
            lines.splice(sectionEndIndex, 0, `${key}=${value}`);
            keyFound = true;
        }
        
        // Se não encontrou a seção, criar
        if (!sectionFound) {
            lines.push(`[${section}]`);
            lines.push(`${key}=${value}`);
            keyFound = true;
        }
        
        // Escrever arquivo atualizado
        const newContent = lines.join('\n');
        fs.writeFileSync(filePath, newContent, 'utf8');
        
        logger.info(`Valor atualizado: ${filename} - [${section}] ${key}=${value}`, {
            backupCreated: backupFilename
        });
        
        return {
            success: true,
            backupCreated: backupFilename,
            updated: keyFound
        };
    } catch (error) {
        logger.error('Erro ao atualizar valor INI', { error: error.message, filename, section, key });
        return {
            success: false,
            error: error.message
        };
    }
};

// Rota para ler ServerSettings.ini
router.get('/ServerSettings.ini', (req, res) => {
    try {
        const result = readConfigFile('ServerSettings.ini');
        
        if (!result.success) {
            return res.status(404).json({
                success: false,
                error: result.error
            });
        }
        
        // Sempre retornar como array de linhas (padrão)
        const lines = result.content.split('\r\n').filter(line => line.trim() !== '');
        res.json({
            success: true,
            content: lines,
            stats: result.stats
        });
    } catch (error) {
        logger.error('Erro ao ler ServerSettings.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para atualizar valor específico do ServerSettings.ini
router.put('/ServerSettings.ini/:section/:key', (req, res) => {
    try {
        const { section, key } = req.params;
        const { value } = req.body;
        
        if (value === undefined || value === null) {
            return res.status(400).json({
                success: false,
                error: 'Valor é obrigatório'
            });
        }
        
        const result = updateIniValue('ServerSettings.ini', section, key, value.toString());
        
        if (!result.success) {
            return res.status(400).json({
                success: false,
                error: result.error
            });
        }
        
        res.json({
            success: true,
            message: `Valor atualizado: [${section}] ${key}=${value}`,
            backupCreated: result.backupCreated,
            updated: result.updated
        });
    } catch (error) {
        logger.error('Erro ao atualizar valor do ServerSettings.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para atualizar arquivo completo do ServerSettings.ini
router.put('/ServerSettings.ini', (req, res) => {
    try {
        const { content } = req.body;
        
        if (!content || !Array.isArray(content)) {
            return res.status(400).json({
                success: false,
                error: 'Conteúdo deve ser um array de linhas'
            });
        }
        
        // Criar backup antes de modificar
        const backupFilename = createBackup('ServerSettings.ini');
        
        // Converter array de linhas para string
        const fileContent = content.join('\r\n');
        
        // Validar formato INI
        const validation = validateIniFormat(fileContent);
        if (!validation.isValid) {
            return res.status(400).json({
                success: false,
                error: 'Formato INI inválido',
                details: validation.errors
            });
        }
        
        // Escrever arquivo
        const filePath = path.join(SCUM_CONFIG_PATH, 'ServerSettings.ini');
        fs.writeFileSync(filePath, fileContent, 'utf8');
        
        logger.info('Arquivo ServerSettings.ini atualizado completamente', {
            backupCreated: backupFilename,
            linesCount: content.length
        });
        
        res.json({
            success: true,
            message: 'Arquivo ServerSettings.ini atualizado com sucesso',
            backupCreated: backupFilename,
            linesCount: content.length
        });
    } catch (error) {
        logger.error('Erro ao atualizar arquivo completo do ServerSettings.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para listar backups
router.get('/backups', (req, res) => {
    try {
        const backups = listBackups();
        
        res.json({
            success: true,
            backups
        });
    } catch (error) {
        logger.error('Erro ao listar backups', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para restaurar backup
router.post('/backups/restore/:filename', (req, res) => {
    try {
        const { filename } = req.params;
        
        if (!filename || !filename.endsWith('.backup')) {
            return res.status(400).json({
                success: false,
                error: 'Nome do arquivo de backup inválido'
            });
        }
        
        const success = restoreBackup(filename);
        
        if (!success) {
            return res.status(404).json({
                success: false,
                error: 'Backup não encontrado'
            });
        }
        
        res.json({
            success: true,
            message: 'Backup restaurado com sucesso',
            restoredFile: filename
        });
    } catch (error) {
        logger.error('Erro ao restaurar backup', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para obter informações do arquivo
router.get('/ServerSettings.ini/info', (req, res) => {
    try {
        const result = readConfigFile('ServerSettings.ini');
        
        if (!result.success) {
            return res.status(404).json({
                success: false,
                error: result.error
            });
        }
        
        // Extrair informações importantes do arquivo
        const content = result.content;
        const info = {
            sections: [],
            totalLines: content.split('\n').length,
            size: result.stats.size,
            modified: result.stats.modified
        };
        
        // Extrair seções
        const sectionMatches = content.match(/\[([^\]]+)\]/g);
        if (sectionMatches) {
            info.sections = sectionMatches.map(section => section.slice(1, -1));
        }
        
        // Extrair configurações importantes
        const importantSettings = [
            'scum.ServerName',
            'scum.ServerDescription',
            'scum.MaxPlayers',
            'scum.ServerPassword',
            'scum.FameGainMultiplier',
            'scum.FamePointPenaltyOnDeath',
            'scum.FamePointPenaltyOnKilled',
            'scum.FamePointRewardOnKill'
        ];
        
        info.importantSettings = {};
        importantSettings.forEach(setting => {
            const match = content.match(new RegExp(`${setting}=([^\\n]+)`));
            if (match) {
                info.importantSettings[setting] = match[1];
            }
        });
        
        res.json({
            success: true,
            info
        });
    } catch (error) {
        logger.error('Erro ao obter informações do ServerSettings.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para ler EconomyOverride.json
router.get('/EconomyOverride.json', (req, res) => {
    try {
        const result = readConfigFile('EconomyOverride.json');
        if (!result.success) {
            return res.status(404).json({
                success: false,
                error: result.error
            });
        }
        // Tentar parsear o conteúdo como JSON
        let jsonContent;
        try {
            jsonContent = JSON.parse(result.content);
        } catch (error) {
            return res.status(400).json({
                success: false,
                error: 'Conteúdo inválido: não é um JSON válido',
                details: error.message
            });
        }
        res.json({
            success: true,
            content: jsonContent,
            stats: result.stats
        });
    } catch (error) {
        logger.error('Erro ao ler EconomyOverride.json', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para atualizar EconomyOverride.json
router.put('/EconomyOverride.json', (req, res) => {
    try {
        const { content } = req.body;
        if (!content) {
            return res.status(400).json({
                success: false,
                error: 'Conteúdo é obrigatório'
            });
        }
        // Validar se o conteúdo é um objeto ou string JSON
        let jsonString;
        if (typeof content === 'object') {
            jsonString = JSON.stringify(content, null, 2);
        } else if (typeof content === 'string') {
            // Validar se é um JSON válido
            const validation = validateJsonFormat(content);
            if (!validation.valid) {
                return res.status(400).json({
                    success: false,
                    error: 'Formato JSON inválido',
                    details: validation.errors
                });
            }
            jsonString = content;
        } else {
            return res.status(400).json({
                success: false,
                error: 'Conteúdo deve ser um objeto ou string JSON'
            });
        }
        // Criar backup antes de modificar
        const backupFilename = createBackup('EconomyOverride.json');
        // Escrever arquivo
        const filePath = path.join(SCUM_CONFIG_PATH, 'EconomyOverride.json');
        fs.writeFileSync(filePath, jsonString, 'utf8');
        logger.info('Arquivo EconomyOverride.json atualizado', {
            backupCreated: backupFilename
        });
        res.json({
            success: true,
            message: 'Arquivo EconomyOverride.json atualizado com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao atualizar EconomyOverride.json', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// PATCH para atualizar campos específicos do EconomyOverride.json
router.patch('/EconomyOverride.json', (req, res) => {
    try {
        const updates = req.body;
        if (!updates || typeof updates !== 'object' || Array.isArray(updates)) {
            return res.status(400).json({
                success: false,
                error: 'O corpo da requisição deve ser um objeto JSON com os campos a serem atualizados.'
            });
        }
        const filePath = path.join(SCUM_CONFIG_PATH, 'EconomyOverride.json');
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: 'Arquivo EconomyOverride.json não encontrado.'
            });
        }
        // Ler conteúdo atual
        const content = fs.readFileSync(filePath, 'utf8');
        let json;
        try {
            json = JSON.parse(content);
        } catch (error) {
            return res.status(400).json({
                success: false,
                error: 'Conteúdo atual do arquivo não é um JSON válido.',
                details: error.message
            });
        }
        // Merge dos campos
        Object.keys(updates).forEach(key => {
            json[key] = updates[key];
        });
        // Criar backup antes de modificar
        const backupFilename = createBackup('EconomyOverride.json');
        // Salvar arquivo atualizado
        fs.writeFileSync(filePath, JSON.stringify(json, null, 2), 'utf8');
        logger.info('Campos atualizados em EconomyOverride.json', {
            backupCreated: backupFilename,
            updatedFields: Object.keys(updates)
        });
        res.json({
            success: true,
            message: 'Campos atualizados com sucesso.',
            backupCreated: backupFilename,
            updatedFields: Object.keys(updates)
        });
    } catch (error) {
        logger.error('Erro ao atualizar campos do EconomyOverride.json', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para ler AdminUsers.ini
router.get('/AdminUsers.ini', (req, res) => {
    try {
        const result = readConfigFile('AdminUsers.ini');
        if (!result.success) {
            return res.status(404).json({
                success: false,
                error: result.error
            });
        }
        // Carregar players.json
        let players = {};
        try {
            const playersPath = path.join(__dirname, '../src/data/players/players.json');
            if (fs.existsSync(playersPath)) {
                players = JSON.parse(fs.readFileSync(playersPath, 'utf8'));
            }
        } catch (err) {
            // Se der erro, segue sem nomes
            players = {};
        }
        // Montar array de objetos
        const lines = result.content.split('\r\n').filter(line => line.trim() !== '');
        const admins = lines.map(line => {
            // Extrai apenas o SteamID numérico do início da linha
            const match = line.match(/^([0-9]{17})/);
            const steamIdNum = match ? match[1] : line.trim();
            return {
                steamId: line.trim(),
                playerName: players[steamIdNum]?.playerName || null
            };
        });
        res.json({
            success: true,
            admins,
            stats: result.stats
        });
    } catch (error) {
        logger.error('Erro ao ler AdminUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para atualizar o arquivo completo do AdminUsers.ini
router.put('/AdminUsers.ini', (req, res) => {
    try {
        const { content } = req.body;
        if (!content || !Array.isArray(content)) {
            return res.status(400).json({
                success: false,
                error: 'Conteúdo deve ser um array de linhas'
            });
        }
        // Criar backup antes de modificar
        const backupFilename = createBackup('AdminUsers.ini');
        // Converter array de linhas para string
        const fileContent = content.join('\r\n');
        // Validar formato INI (opcional, pode ser simples)
        // Escrever arquivo
        const filePath = path.join(SCUM_CONFIG_PATH, 'AdminUsers.ini');
        fs.writeFileSync(filePath, fileContent + '\r\n', 'utf8');
        logger.info('Arquivo AdminUsers.ini atualizado completamente', {
            backupCreated: backupFilename,
            linesCount: content.length
        });
        res.json({
            success: true,
            message: 'Arquivo AdminUsers.ini atualizado com sucesso',
            backupCreated: backupFilename,
            linesCount: content.length
        });
    } catch (error) {
        logger.error('Erro ao atualizar arquivo completo do AdminUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para adicionar admin ao AdminUsers.ini
router.post('/AdminUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({
                success: false,
                error: 'steamId é obrigatório e deve ser uma string'
            });
        }
        const filePath = path.join(SCUM_CONFIG_PATH, 'AdminUsers.ini');
        let content = '';
        if (fs.existsSync(filePath)) {
            content = fs.readFileSync(filePath, 'utf8');
        }
        // Garante que o SteamID tenha o sufixo [setgodmode]
        let steamIdToSave = steamId;
        if (!steamId.endsWith('[setgodmode]')) {
            // Remove qualquer sufixo e adiciona o correto
            const match = steamId.match(/^([0-9]{17})/);
            const idNum = match ? match[1] : steamId.trim();
            steamIdToSave = idNum + '[setgodmode]';
        }
        // Verifica se já existe (ignora sufixos)
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        const exists = lines.some(line => {
            const match = line.match(/^([0-9]{17})/);
            const idNum = match ? match[1] : line.trim();
            const newIdNum = (steamId.match(/^([0-9]{17})/) || [])[1] || steamId.trim();
            return idNum === newIdNum;
        });
        if (exists) {
            return res.status(400).json({
                success: false,
                error: 'SteamID já existe no AdminUsers.ini'
            });
        }
        // Criar backup
        const backupFilename = createBackup('AdminUsers.ini');
        // Adicionar nova linha
        const newContent = content ? (content.endsWith('\r\n') ? content + steamIdToSave : content + '\r\n' + steamIdToSave) : steamIdToSave;
        fs.writeFileSync(filePath, newContent + '\r\n', 'utf8');
        logger.info('Admin adicionado ao AdminUsers.ini', { steamId: steamIdToSave, backupCreated: backupFilename });
        res.json({
            success: true,
            message: 'Admin adicionado com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao adicionar admin ao AdminUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para remover admin do AdminUsers.ini
router.delete('/AdminUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({
                success: false,
                error: 'steamId é obrigatório e deve ser uma string'
            });
        }
        const filePath = path.join(SCUM_CONFIG_PATH, 'AdminUsers.ini');
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: 'Arquivo AdminUsers.ini não encontrado'
            });
        }
        const content = fs.readFileSync(filePath, 'utf8');
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        // Extrai só o número do SteamID informado
        const match = steamId.match(/^([0-9]{17})/);
        const idToRemove = match ? match[1] : steamId.trim();
        // Filtra removendo todas as linhas com esse SteamID
        const newLines = lines.filter(line => {
            const m = line.match(/^([0-9]{17})/);
            const idNum = m ? m[1] : line.trim();
            return idNum !== idToRemove;
        });
        if (newLines.length === lines.length) {
            return res.status(404).json({
                success: false,
                error: 'SteamID não encontrado no AdminUsers.ini'
            });
        }
        // Criar backup
        const backupFilename = createBackup('AdminUsers.ini');
        // Salvar arquivo atualizado
        fs.writeFileSync(filePath, newLines.join('\r\n') + '\r\n', 'utf8');
        logger.info('Admin removido do AdminUsers.ini', { steamId: idToRemove, backupCreated: backupFilename });
        res.json({
            success: true,
            message: 'Admin removido com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao remover admin do AdminUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// ========================================
// ENDPOINTS PARA WhitelistedUsers.ini
// ========================================

// Rota para ler WhitelistedUsers.ini
router.get('/WhitelistedUsers.ini', (req, res) => {
    try {
        const result = readConfigFile('WhitelistedUsers.ini');
        if (!result.success) {
            return res.status(404).json({ success: false, error: result.error });
        }
        
        // Tentar ler players.json para obter nomes dos jogadores
        let players = {};
        try {
            const playersPath = path.join(__dirname, '../src/data/players/players.json');
            if (fs.existsSync(playersPath)) {
                players = JSON.parse(fs.readFileSync(playersPath, 'utf8'));
            }
        } catch (err) {
            players = {};
        }
        
        const lines = result.content.split('\r\n').filter(line => line.trim() !== '');
        const whitelistedUsers = lines.map(line => {
            const match = line.match(/^([0-9]{17})/);
            const steamIdNum = match ? match[1] : line.trim();
            return {
                steamId: line.trim(),
                playerName: players[steamIdNum]?.playerName || null
            };
        });
        
        res.json({ success: true, whitelistedUsers, stats: result.stats });
    } catch (error) {
        logger.error('Erro ao ler WhitelistedUsers.ini', { error: error.message });
        res.status(500).json({ success: false, error: 'Erro interno do servidor' });
    }
});

// Rota para substituir completamente WhitelistedUsers.ini
router.put('/WhitelistedUsers.ini', (req, res) => {
    try {
        const { content } = req.body;
        if (!content || !Array.isArray(content)) {
            return res.status(400).json({ success: false, error: 'Conteúdo deve ser um array de linhas' });
        }
        
        const backupFilename = createBackup('WhitelistedUsers.ini');
        const fileContent = content.join('\r\n');
        const filePath = path.join(SCUM_CONFIG_PATH, 'WhitelistedUsers.ini');
        fs.writeFileSync(filePath, fileContent + '\r\n', 'utf8');
        
        logger.info('Arquivo WhitelistedUsers.ini atualizado completamente', {
            backupCreated: backupFilename,
            linesCount: content.length
        });
        
        res.json({
            success: true,
            message: 'Arquivo WhitelistedUsers.ini atualizado com sucesso',
            backupCreated: backupFilename,
            linesCount: content.length
        });
    } catch (error) {
        logger.error('Erro ao atualizar arquivo completo do WhitelistedUsers.ini', { error: error.message });
        res.status(500).json({ success: false, error: 'Erro interno do servidor' });
    }
});

// Rota para adicionar usuário à whitelist
router.post('/WhitelistedUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({ success: false, error: 'steamId é obrigatório e deve ser uma string' });
        }
        
        const filePath = path.join(SCUM_CONFIG_PATH, 'WhitelistedUsers.ini');
        let content = '';
        if (fs.existsSync(filePath)) {
            content = fs.readFileSync(filePath, 'utf8');
        }
        
        // Salva o SteamID sem sufixo
        let steamIdToSave = steamId.trim();
        const match = steamId.match(/^([0-9]{17})/);
        if (match) {
            steamIdToSave = match[1]; // Apenas os 17 dígitos
        }
        
        // Verifica se já existe (ignora sufixos)
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        const exists = lines.some(line => {
            const match = line.match(/^([0-9]{17})/);
            const idNum = match ? match[1] : line.trim();
            const newIdNum = (steamId.match(/^([0-9]{17})/) || [])[1] || steamId.trim();
            return idNum === newIdNum;
        });
        
        if (exists) {
            return res.status(400).json({
                success: false,
                error: 'SteamID já existe no WhitelistedUsers.ini'
            });
        }
        
        // Criar backup
        const backupFilename = createBackup('WhitelistedUsers.ini');
        
        // Adicionar nova linha
        const newContent = content ? (content.endsWith('\r\n') ? content + steamIdToSave : content + '\r\n' + steamIdToSave) : steamIdToSave;
        fs.writeFileSync(filePath, newContent + '\r\n', 'utf8');
        
        logger.info('Usuário adicionado ao WhitelistedUsers.ini', { steamId: steamIdToSave, backupCreated: backupFilename });
        res.json({
            success: true,
            message: 'Usuário adicionado à whitelist com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao adicionar usuário ao WhitelistedUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para remover usuário da whitelist
router.delete('/WhitelistedUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({
                success: false,
                error: 'steamId é obrigatório e deve ser uma string'
            });
        }
        
        const filePath = path.join(SCUM_CONFIG_PATH, 'WhitelistedUsers.ini');
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: 'Arquivo WhitelistedUsers.ini não encontrado'
            });
        }
        
        const content = fs.readFileSync(filePath, 'utf8');
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        
        // Extrai só o número do SteamID informado
        const match = steamId.match(/^([0-9]{17})/);
        const idToRemove = match ? match[1] : steamId.trim();
        
        // Filtra removendo todas as linhas com esse SteamID
        const newLines = lines.filter(line => {
            const m = line.match(/^([0-9]{17})/);
            const idNum = m ? m[1] : line.trim();
            return idNum !== idToRemove;
        });
        
        if (newLines.length === lines.length) {
            return res.status(404).json({
                success: false,
                error: 'SteamID não encontrado no WhitelistedUsers.ini'
            });
        }
        
        // Criar backup
        const backupFilename = createBackup('WhitelistedUsers.ini');
        
        // Salvar arquivo atualizado
        fs.writeFileSync(filePath, newLines.join('\r\n') + '\r\n', 'utf8');
        
        logger.info('Usuário removido do WhitelistedUsers.ini', { steamId: idToRemove, backupCreated: backupFilename });
        res.json({
            success: true,
            message: 'Usuário removido da whitelist com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao remover usuário do WhitelistedUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// ========================================
// ENDPOINTS PARA BannedUsers.ini
// ========================================

// Rota para ler BannedUsers.ini
router.get('/BannedUsers.ini', (req, res) => {
    try {
        const result = readConfigFile('BannedUsers.ini');
        if (!result.success) {
            return res.status(404).json({ success: false, error: result.error });
        }
        
        // Tentar ler players.json para obter nomes dos jogadores
        let players = {};
        try {
            const playersPath = path.join(__dirname, '../src/data/players/players.json');
            if (fs.existsSync(playersPath)) {
                players = JSON.parse(fs.readFileSync(playersPath, 'utf8'));
            }
        } catch (err) {
            players = {};
        }
        
        const lines = result.content.split('\r\n').filter(line => line.trim() !== '');
        const bannedUsers = lines.map(line => {
            const match = line.match(/^([0-9]{17})/);
            const steamIdNum = match ? match[1] : line.trim();
            return {
                steamId: line.trim(),
                playerName: players[steamIdNum]?.playerName || null
            };
        });
        
        res.json({ success: true, bannedUsers, stats: result.stats });
    } catch (error) {
        logger.error('Erro ao ler BannedUsers.ini', { error: error.message });
        res.status(500).json({ success: false, error: 'Erro interno do servidor' });
    }
});

// Rota para substituir completamente BannedUsers.ini
router.put('/BannedUsers.ini', (req, res) => {
    try {
        const { content } = req.body;
        if (!content || !Array.isArray(content)) {
            return res.status(400).json({ success: false, error: 'Conteúdo deve ser um array de linhas' });
        }
        
        const backupFilename = createBackup('BannedUsers.ini');
        const fileContent = content.join('\r\n');
        const filePath = path.join(SCUM_CONFIG_PATH, 'BannedUsers.ini');
        fs.writeFileSync(filePath, fileContent + '\r\n', 'utf8');
        
        logger.info('Arquivo BannedUsers.ini atualizado completamente', {
            backupCreated: backupFilename,
            linesCount: content.length
        });
        
        res.json({
            success: true,
            message: 'Arquivo BannedUsers.ini atualizado com sucesso',
            backupCreated: backupFilename,
            linesCount: content.length
        });
    } catch (error) {
        logger.error('Erro ao atualizar arquivo completo do BannedUsers.ini', { error: error.message });
        res.status(500).json({ success: false, error: 'Erro interno do servidor' });
    }
});

// Rota para adicionar usuário banido
router.post('/BannedUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({ success: false, error: 'steamId é obrigatório e deve ser uma string' });
        }
        
        const filePath = path.join(SCUM_CONFIG_PATH, 'BannedUsers.ini');
        let content = '';
        if (fs.existsSync(filePath)) {
            content = fs.readFileSync(filePath, 'utf8');
        }
        
        // Salva o SteamID sem sufixo
        let steamIdToSave = steamId.trim();
        const match = steamId.match(/^([0-9]{17})/);
        if (match) {
            steamIdToSave = match[1]; // Apenas os 17 dígitos
        }
        
        // Verifica se já existe (ignora sufixos)
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        const exists = lines.some(line => {
            const match = line.match(/^([0-9]{17})/);
            const idNum = match ? match[1] : line.trim();
            const newIdNum = (steamId.match(/^([0-9]{17})/) || [])[1] || steamId.trim();
            return idNum === newIdNum;
        });
        
        if (exists) {
            return res.status(400).json({
                success: false,
                error: 'SteamID já existe no BannedUsers.ini'
            });
        }
        
        // Criar backup
        const backupFilename = createBackup('BannedUsers.ini');
        
        // Adicionar nova linha
        const newContent = content ? (content.endsWith('\r\n') ? content + steamIdToSave : content + '\r\n' + steamIdToSave) : steamIdToSave;
        fs.writeFileSync(filePath, newContent + '\r\n', 'utf8');
        
        logger.info('Usuário adicionado ao BannedUsers.ini', { steamId: steamIdToSave, backupCreated: backupFilename });
        res.json({
            success: true,
            message: 'Usuário banido adicionado com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao adicionar usuário ao BannedUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para remover usuário banido
router.delete('/BannedUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({
                success: false,
                error: 'steamId é obrigatório e deve ser uma string'
            });
        }
        
        const filePath = path.join(SCUM_CONFIG_PATH, 'BannedUsers.ini');
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: 'Arquivo BannedUsers.ini não encontrado'
            });
        }
        
        const content = fs.readFileSync(filePath, 'utf8');
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        
        // Extrai só o número do SteamID informado
        const match = steamId.match(/^([0-9]{17})/);
        const idToRemove = match ? match[1] : steamId.trim();
        
        // Filtra removendo todas as linhas com esse SteamID
        const newLines = lines.filter(line => {
            const m = line.match(/^([0-9]{17})/);
            const idNum = m ? m[1] : line.trim();
            return idNum !== idToRemove;
        });
        
        if (newLines.length === lines.length) {
            return res.status(404).json({
                success: false,
                error: 'SteamID não encontrado no BannedUsers.ini'
            });
        }
        
        // Criar backup
        const backupFilename = createBackup('BannedUsers.ini');
        
        // Salvar arquivo atualizado
        fs.writeFileSync(filePath, newLines.join('\r\n') + '\r\n', 'utf8');
        
        logger.info('Usuário removido do BannedUsers.ini', { steamId: idToRemove, backupCreated: backupFilename });
        res.json({
            success: true,
            message: 'Usuário removido da lista de banidos com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao remover usuário do BannedUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// ========================================
// ENDPOINTS PARA ExclusiveUsers.ini
// ========================================

// Rota para ler ExclusiveUsers.ini
router.get('/ExclusiveUsers.ini', (req, res) => {
    try {
        const result = readConfigFile('ExclusiveUsers.ini');
        if (!result.success) {
            return res.status(404).json({ success: false, error: result.error });
        }
        
        // Tentar ler players.json para obter nomes dos jogadores
        let players = {};
        try {
            const playersPath = path.join(__dirname, '../src/data/players/players.json');
            if (fs.existsSync(playersPath)) {
                players = JSON.parse(fs.readFileSync(playersPath, 'utf8'));
            }
        } catch (err) {
            players = {};
        }
        
        const lines = result.content.split('\r\n').filter(line => line.trim() !== '');
        const exclusiveUsers = lines.map(line => {
            const match = line.match(/^([0-9]{17})/);
            const steamIdNum = match ? match[1] : line.trim();
            return {
                steamId: line.trim(),
                playerName: players[steamIdNum]?.playerName || null
            };
        });
        
        res.json({ success: true, exclusiveUsers, stats: result.stats });
    } catch (error) {
        logger.error('Erro ao ler ExclusiveUsers.ini', { error: error.message });
        res.status(500).json({ success: false, error: 'Erro interno do servidor' });
    }
});

// Rota para substituir completamente ExclusiveUsers.ini
router.put('/ExclusiveUsers.ini', (req, res) => {
    try {
        const { content } = req.body;
        if (!content || !Array.isArray(content)) {
            return res.status(400).json({ success: false, error: 'Conteúdo deve ser um array de linhas' });
        }
        
        const backupFilename = createBackup('ExclusiveUsers.ini');
        const fileContent = content.join('\r\n');
        const filePath = path.join(SCUM_CONFIG_PATH, 'ExclusiveUsers.ini');
        fs.writeFileSync(filePath, fileContent + '\r\n', 'utf8');
        
        logger.info('Arquivo ExclusiveUsers.ini atualizado completamente', {
            backupCreated: backupFilename,
            linesCount: content.length
        });
        
        res.json({
            success: true,
            message: 'Arquivo ExclusiveUsers.ini atualizado com sucesso',
            backupCreated: backupFilename,
            linesCount: content.length
        });
    } catch (error) {
        logger.error('Erro ao atualizar arquivo completo do ExclusiveUsers.ini', { error: error.message });
        res.status(500).json({ success: false, error: 'Erro interno do servidor' });
    }
});

// Rota para adicionar usuário exclusivo
router.post('/ExclusiveUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({ success: false, error: 'steamId é obrigatório e deve ser uma string' });
        }
        
        const filePath = path.join(SCUM_CONFIG_PATH, 'ExclusiveUsers.ini');
        let content = '';
        if (fs.existsSync(filePath)) {
            content = fs.readFileSync(filePath, 'utf8');
        }
        
        // Salva o SteamID sem sufixo
        let steamIdToSave = steamId.trim();
        const match = steamId.match(/^([0-9]{17})/);
        if (match) {
            steamIdToSave = match[1]; // Apenas os 17 dígitos
        }
        
        // Verifica se já existe (ignora sufixos)
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        const exists = lines.some(line => {
            const match = line.match(/^([0-9]{17})/);
            const idNum = match ? match[1] : line.trim();
            const newIdNum = (steamId.match(/^([0-9]{17})/) || [])[1] || steamId.trim();
            return idNum === newIdNum;
        });
        
        if (exists) {
            return res.status(400).json({
                success: false,
                error: 'SteamID já existe no ExclusiveUsers.ini'
            });
        }
        
        // Criar backup
        const backupFilename = createBackup('ExclusiveUsers.ini');
        
        // Adicionar nova linha
        const newContent = content ? (content.endsWith('\r\n') ? content + steamIdToSave : content + '\r\n' + steamIdToSave) : steamIdToSave;
        fs.writeFileSync(filePath, newContent + '\r\n', 'utf8');
        
        logger.info('Usuário adicionado ao ExclusiveUsers.ini', { steamId: steamIdToSave, backupCreated: backupFilename });
        res.json({
            success: true,
            message: 'Usuário exclusivo adicionado com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao adicionar usuário ao ExclusiveUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para remover usuário exclusivo
router.delete('/ExclusiveUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({
                success: false,
                error: 'steamId é obrigatório e deve ser uma string'
            });
        }
        
        const filePath = path.join(SCUM_CONFIG_PATH, 'ExclusiveUsers.ini');
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: 'Arquivo ExclusiveUsers.ini não encontrado'
            });
        }
        
        const content = fs.readFileSync(filePath, 'utf8');
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        
        // Extrai só o número do SteamID informado
        const match = steamId.match(/^([0-9]{17})/);
        const idToRemove = match ? match[1] : steamId.trim();
        
        // Filtra removendo todas as linhas com esse SteamID
        const newLines = lines.filter(line => {
            const m = line.match(/^([0-9]{17})/);
            const idNum = m ? m[1] : line.trim();
            return idNum !== idToRemove;
        });
        
        if (newLines.length === lines.length) {
            return res.status(404).json({
                success: false,
                error: 'SteamID não encontrado no ExclusiveUsers.ini'
            });
        }
        
        // Criar backup
        const backupFilename = createBackup('ExclusiveUsers.ini');
        
        // Salvar arquivo atualizado
        fs.writeFileSync(filePath, newLines.join('\r\n') + '\r\n', 'utf8');
        
        logger.info('Usuário removido do ExclusiveUsers.ini', { steamId: idToRemove, backupCreated: backupFilename });
        res.json({
            success: true,
            message: 'Usuário removido da lista exclusiva com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao remover usuário do ExclusiveUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// ========================================
// ENDPOINTS PARA SilencedUsers.ini
// ========================================

// Rota para ler SilencedUsers.ini
router.get('/SilencedUsers.ini', (req, res) => {
    try {
        const result = readConfigFile('SilencedUsers.ini');
        if (!result.success) {
            return res.status(404).json({ success: false, error: result.error });
        }
        // Tentar ler players.json para obter nomes dos jogadores
        let players = {};
        try {
            const playersPath = path.join(__dirname, '../src/data/players/players.json');
            if (fs.existsSync(playersPath)) {
                players = JSON.parse(fs.readFileSync(playersPath, 'utf8'));
            }
        } catch (err) {
            players = {};
        }
        const lines = result.content.split('\r\n').filter(line => line.trim() !== '');
        const silencedUsers = lines.map(line => {
            const match = line.match(/^([0-9]{17})/);
            const steamIdNum = match ? match[1] : line.trim();
            return {
                steamId: line.trim(),
                playerName: players[steamIdNum]?.playerName || null
            };
        });
        res.json({ success: true, silencedUsers, stats: result.stats });
    } catch (error) {
        logger.error('Erro ao ler SilencedUsers.ini', { error: error.message });
        res.status(500).json({ success: false, error: 'Erro interno do servidor' });
    }
});

// Rota para substituir completamente SilencedUsers.ini
router.put('/SilencedUsers.ini', (req, res) => {
    try {
        const { content } = req.body;
        if (!content || !Array.isArray(content)) {
            return res.status(400).json({ success: false, error: 'Conteúdo deve ser um array de linhas' });
        }
        const backupFilename = createBackup('SilencedUsers.ini');
        const fileContent = content.join('\r\n');
        const filePath = path.join(SCUM_CONFIG_PATH, 'SilencedUsers.ini');
        fs.writeFileSync(filePath, fileContent + '\r\n', 'utf8');
        logger.info('Arquivo SilencedUsers.ini atualizado completamente', {
            backupCreated: backupFilename,
            linesCount: content.length
        });
        res.json({
            success: true,
            message: 'Arquivo SilencedUsers.ini atualizado com sucesso',
            backupCreated: backupFilename,
            linesCount: content.length
        });
    } catch (error) {
        logger.error('Erro ao atualizar arquivo completo do SilencedUsers.ini', { error: error.message });
        res.status(500).json({ success: false, error: 'Erro interno do servidor' });
    }
});

// Rota para adicionar usuário silenciado
router.post('/SilencedUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({ success: false, error: 'steamId é obrigatório e deve ser uma string' });
        }
        const filePath = path.join(SCUM_CONFIG_PATH, 'SilencedUsers.ini');
        let content = '';
        if (fs.existsSync(filePath)) {
            content = fs.readFileSync(filePath, 'utf8');
        }
        // Salva o SteamID sem sufixo
        let steamIdToSave = steamId.trim();
        const match = steamId.match(/^([0-9]{17})/);
        if (match) {
            steamIdToSave = match[1]; // Apenas os 17 dígitos
        }
        // Verifica se já existe (ignora sufixos)
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        const exists = lines.some(line => {
            const match = line.match(/^([0-9]{17})/);
            const idNum = match ? match[1] : line.trim();
            const newIdNum = (steamId.match(/^([0-9]{17})/) || [])[1] || steamId.trim();
            return idNum === newIdNum;
        });
        if (exists) {
            return res.status(400).json({
                success: false,
                error: 'SteamID já existe no SilencedUsers.ini'
            });
        }
        // Criar backup
        const backupFilename = createBackup('SilencedUsers.ini');
        // Adicionar nova linha
        const newContent = content ? (content.endsWith('\r\n') ? content + steamIdToSave : content + '\r\n' + steamIdToSave) : steamIdToSave;
        fs.writeFileSync(filePath, newContent + '\r\n', 'utf8');
        logger.info('Usuário adicionado ao SilencedUsers.ini', { steamId: steamIdToSave, backupCreated: backupFilename });
        res.json({
            success: true,
            message: 'Usuário silenciado adicionado com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao adicionar usuário ao SilencedUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para remover usuário silenciado
router.delete('/SilencedUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({
                success: false,
                error: 'steamId é obrigatório e deve ser uma string'
            });
        }
        const filePath = path.join(SCUM_CONFIG_PATH, 'SilencedUsers.ini');
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: 'Arquivo SilencedUsers.ini não encontrado'
            });
        }
        const content = fs.readFileSync(filePath, 'utf8');
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        // Extrai só o número do SteamID informado
        const match = steamId.match(/^([0-9]{17})/);
        const idToRemove = match ? match[1] : steamId.trim();
        // Filtra removendo todas as linhas com esse SteamID
        const newLines = lines.filter(line => {
            const m = line.match(/^([0-9]{17})/);
            const idNum = m ? m[1] : line.trim();
            return idNum !== idToRemove;
        });
        if (newLines.length === lines.length) {
            return res.status(404).json({
                success: false,
                error: 'SteamID não encontrado no SilencedUsers.ini'
            });
        }
        // Criar backup
        const backupFilename = createBackup('SilencedUsers.ini');
        // Salvar arquivo atualizado
        fs.writeFileSync(filePath, newLines.join('\r\n') + '\r\n', 'utf8');
        logger.info('Usuário removido do SilencedUsers.ini', { steamId: idToRemove, backupCreated: backupFilename });
        res.json({
            success: true,
            message: 'Usuário removido da lista de silenciados com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao remover usuário do SilencedUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// ========================================
// ENDPOINTS PARA ServerSettingsAdminUsers.ini
// ========================================

// Rota para ler ServerSettingsAdminUsers.ini
router.get('/ServerSettingsAdminUsers.ini', (req, res) => {
    try {
        const result = readConfigFile('ServerSettingsAdminUsers.ini');
        if (!result.success) {
            return res.status(404).json({ success: false, error: result.error });
        }
        
        // Tentar ler players.json para obter nomes dos jogadores
        let players = {};
        try {
            const playersPath = path.join(__dirname, '../src/data/players/players.json');
            if (fs.existsSync(playersPath)) {
                players = JSON.parse(fs.readFileSync(playersPath, 'utf8'));
            }
        } catch (err) {
            players = {};
        }
        
        const lines = result.content.split('\r\n').filter(line => line.trim() !== '');
        const adminUsers = lines.map(line => {
            const match = line.match(/^([0-9]{17})/);
            const steamIdNum = match ? match[1] : line.trim();
            return {
                steamId: line.trim(),
                playerName: players[steamIdNum]?.playerName || null
            };
        });
        
        res.json({ success: true, adminUsers, stats: result.stats });
    } catch (error) {
        logger.error('Erro ao ler ServerSettingsAdminUsers.ini', { error: error.message });
        res.status(500).json({ success: false, error: 'Erro interno do servidor' });
    }
});

// Rota para substituir completamente ServerSettingsAdminUsers.ini
router.put('/ServerSettingsAdminUsers.ini', (req, res) => {
    try {
        const { content } = req.body;
        if (!content || !Array.isArray(content)) {
            return res.status(400).json({ success: false, error: 'Conteúdo deve ser um array de linhas' });
        }
        
        const backupFilename = createBackup('ServerSettingsAdminUsers.ini');
        const fileContent = content.join('\r\n');
        const filePath = path.join(SCUM_CONFIG_PATH, 'ServerSettingsAdminUsers.ini');
        fs.writeFileSync(filePath, fileContent + '\r\n', 'utf8');
        
        logger.info('Arquivo ServerSettingsAdminUsers.ini atualizado completamente', {
            backupCreated: backupFilename,
            linesCount: content.length
        });
        
        res.json({
            success: true,
            message: 'Arquivo ServerSettingsAdminUsers.ini atualizado com sucesso',
            backupCreated: backupFilename,
            linesCount: content.length
        });
    } catch (error) {
        logger.error('Erro ao atualizar arquivo completo do ServerSettingsAdminUsers.ini', { error: error.message });
        res.status(500).json({ success: false, error: 'Erro interno do servidor' });
    }
});

// Rota para adicionar admin ao ServerSettingsAdminUsers.ini
router.post('/ServerSettingsAdminUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({ success: false, error: 'steamId é obrigatório e deve ser uma string' });
        }
        
        // Validar formato do SteamID (17 dígitos)
        const steamIdMatch = steamId.match(/^([0-9]{17})/);
        if (!steamIdMatch) {
            return res.status(400).json({ 
                success: false, 
                error: 'SteamID deve conter 17 dígitos numéricos' 
            });
        }
        
        const filePath = path.join(SCUM_CONFIG_PATH, 'ServerSettingsAdminUsers.ini');
        let content = '';
        if (fs.existsSync(filePath)) {
            content = fs.readFileSync(filePath, 'utf8');
        }
        
        // Extrair apenas os 17 dígitos (sem sufixo)
        const idNum = steamIdMatch[1];
        const steamIdToSave = idNum;
        
        // Verifica se já existe (ignora sufixos)
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        const exists = lines.some(line => {
            const match = line.match(/^([0-9]{17})/);
            const idNum = match ? match[1] : line.trim();
            return idNum === steamIdMatch[1];
        });
        
        if (exists) {
            return res.status(400).json({
                success: false,
                error: 'SteamID já existe no ServerSettingsAdminUsers.ini'
            });
        }
        
        // Criar backup
        const backupFilename = createBackup('ServerSettingsAdminUsers.ini');
        
        // Adicionar nova linha
        const newContent = content ? (content.endsWith('\r\n') ? content + steamIdToSave : content + '\r\n' + steamIdToSave) : steamIdToSave;
        fs.writeFileSync(filePath, newContent + '\r\n', 'utf8');
        
        logger.info('Admin adicionado ao ServerSettingsAdminUsers.ini', { 
            steamId: steamIdMatch[1], 
            steamIdSaved: steamIdToSave, 
            backupCreated: backupFilename 
        });
        res.json({
            success: true,
            message: 'Admin adicionado com sucesso',
            steamId: steamIdMatch[1],
            steamIdSaved: steamIdToSave,
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao adicionar admin ao ServerSettingsAdminUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para remover admin do ServerSettingsAdminUsers.ini
router.delete('/ServerSettingsAdminUsers.ini', (req, res) => {
    try {
        const { steamId } = req.body;
        if (!steamId || typeof steamId !== 'string') {
            return res.status(400).json({
                success: false,
                error: 'steamId é obrigatório e deve ser uma string'
            });
        }
        
        const filePath = path.join(SCUM_CONFIG_PATH, 'ServerSettingsAdminUsers.ini');
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: 'Arquivo ServerSettingsAdminUsers.ini não encontrado'
            });
        }
        
        const content = fs.readFileSync(filePath, 'utf8');
        const lines = content.split('\r\n').filter(line => line.trim() !== '');
        
        // Extrai só o número do SteamID informado
        const match = steamId.match(/^([0-9]{17})/);
        const idToRemove = match ? match[1] : steamId.trim();
        
        // Filtra removendo todas as linhas com esse SteamID
        const newLines = lines.filter(line => {
            const m = line.match(/^([0-9]{17})/);
            const idNum = m ? m[1] : line.trim();
            return idNum !== idToRemove;
        });
        
        if (newLines.length === lines.length) {
            return res.status(404).json({
                success: false,
                error: 'SteamID não encontrado no ServerSettingsAdminUsers.ini'
            });
        }
        
        // Criar backup
        const backupFilename = createBackup('ServerSettingsAdminUsers.ini');
        
        // Salvar arquivo atualizado
        fs.writeFileSync(filePath, newLines.join('\r\n') + '\r\n', 'utf8');
        
        logger.info('Admin removido do ServerSettingsAdminUsers.ini', { steamId: idToRemove, backupCreated: backupFilename });
        res.json({
            success: true,
            message: 'Admin removido com sucesso',
            backupCreated: backupFilename
        });
    } catch (error) {
        logger.error('Erro ao remover admin do ServerSettingsAdminUsers.ini', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Inicializar diretórios
createDirectories();

module.exports = router; 