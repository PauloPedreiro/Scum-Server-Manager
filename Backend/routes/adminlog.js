const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const url = require('url');
const logger = require('../src/logger');

const ADMIN_LOG_PATH = process.env.SCUM_LOG_PATH;
const ADMIN_DB_PATH = 'src/data/admin/adminlog.json';
const TEMP_PATH = 'src/data/temp';
const WEBHOOKS_PATH = 'src/data/webhooks.json';
const LAST_LINE_PATH = 'src/data/admin/lastAdminLogLine.json';

// Função para criar diretórios necessários
const createDirectories = () => {
    const dirs = [
        TEMP_PATH,
        'src/data/admin'
    ];
    dirs.forEach(dir => {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    });
};

// Função para encontrar o último log de admin
function getLatestAdminLog() {
    if (!fs.existsSync(ADMIN_LOG_PATH)) return null;
    const files = fs.readdirSync(ADMIN_LOG_PATH)
        .filter(f => f.startsWith('admin_') && f.endsWith('.log'));
    if (files.length === 0) return null;
    return files.map(f => ({
        name: f,
        time: fs.statSync(path.join(ADMIN_LOG_PATH, f)).mtime.getTime()
    })).sort((a, b) => b.time - a.time)[0].name;
}

// Função para copiar log para temp
function copyAdminLogToTemp(logFileName) {
    const sourcePath = path.join(ADMIN_LOG_PATH, logFileName);
    const tempPath = path.join(TEMP_PATH, logFileName);
    try {
        fs.copyFileSync(sourcePath, tempPath);
        return tempPath;
    } catch (error) {
        console.error(`Erro ao copiar log admin: ${error.message}`);
        return null;
    }
}

// Função para verificar se usuário está vinculado ao Discord
function checkDiscordLink(steamId) {
    try {
        const linkedUsersPath = 'src/data/bot/linked_users.json';
        if (!fs.existsSync(linkedUsersPath)) {
            logger.debug('Arquivo linked_users.json não encontrado');
            return null;
        }
        
        const linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
        logger.debug(`Verificando Steam ID: ${steamId}`);
        logger.debug(`Usuários vinculados: ${JSON.stringify(linkedUsers)}`);
        
        // Procurar pelo Steam ID nos usuários vinculados
        for (const [discordId, userData] of Object.entries(linkedUsers)) {
            logger.debug(`Comparando: ${userData.steam_id} === ${steamId} = ${userData.steam_id === steamId}`);
            if (userData.steam_id === steamId) {
                logger.debug(`Usuário encontrado: ${discordId}`);
                return {
                    discordId: discordId,
                    linkedAt: userData.linked_at,
                    permissions: userData.permissions || []
                };
            }
        }
        
        logger.debug('Usuário não encontrado na lista de vinculados');
        return null;
    } catch (error) {
        logger.error('Erro ao verificar usuário vinculado', { error: error.message });
        return null;
    }
}

// Função para formatar mensagem do log de admin
function formatAdminLogMessage(line) {
    // Extrair informações da linha usando regex
    const regex = /^(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}): '(\d+):([^']+)' (.+)$/;
    const match = line.match(regex);
    
    if (!match) {
        // Se não conseguir parsear, retorna como texto simples
        return {
            content: `📋 **Log de Admin**\n\`\`\`${line}\`\`\``
        };
    }
    
    const [, timestamp, steamId, playerName, action] = match;
    
    // Determinar cor baseada no tipo de ação
    let color = 0x00ff00; // Verde padrão
    let emoji = "📋";
    
    if (action.includes('Command:')) {
        color = 0xff6b35; // Laranja para comandos
        emoji = "⚡";
    } else if (action.includes('teleport')) {
        color = 0x9b59b6; // Roxo para teleportes
        emoji = "🚀";
    } else if (action.includes('SpawnItem')) {
        color = 0xf1c40f; // Amarelo para spawn de itens
        emoji = "🎁";
    } else if (action.includes('SetGodMode')) {
        color = 0xe74c3c; // Vermelho para god mode
        emoji = "🛡️";
    } else if (action.includes('ShowOtherPlayerInfo')) {
        color = 0x3498db; // Azul para informações de jogador
        emoji = "👁️";
    }
    
    // Formatar timestamp
    let date;
    try {
        // Converter o formato do SCUM para ISO
        const timestampParts = timestamp.split('-');
        const datePart = timestampParts[0].replace(/\./g, '-');
        const timePart = timestampParts[1].replace(/\./g, ':');
        const isoString = `${datePart}T${timePart}`;
        date = new Date(isoString);
        
        // Verificar se a data é válida
        if (isNaN(date.getTime())) {
            date = new Date(); // Usar data atual se inválida
        }
    } catch (error) {
        date = new Date(); // Usar data atual em caso de erro
    }
    
    const formattedTime = date.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    // Verificar se usuário está vinculado ao Discord
    const discordLink = checkDiscordLink(steamId);
    const discordInfo = discordLink ? `✅ Vinculado (<@${discordLink.discordId}>)` : `❌ Não vinculado`;
    
    // Criar embed
    return {
        embeds: [{
            title: `${emoji} Atividade de Admin`,
            description: `**Jogador:** ${playerName}\n**Steam ID:** \`${steamId}\`\n**Discord:** ${discordInfo}\n**Ação:** ${action}\n**Horário:** ${formattedTime}`,
            color: color,
            timestamp: date.toISOString(),
            footer: {
                text: "SCUM Server Manager - Log de Admin"
            }
        }]
    };
}

// Função para fazer requisições HTTP (substitui axios)
function makeRequest(options) {
    return new Promise((resolve, reject) => {
        const parsedUrl = url.parse(options.url);
        const requestOptions = {
            hostname: parsedUrl.hostname,
            port: parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80),
            path: parsedUrl.path,
            method: options.method || 'GET',
            headers: options.headers || {}
        };

        const client = parsedUrl.protocol === 'https:' ? https : http;
        const req = client.request(requestOptions, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                resolve({
                    status: res.statusCode,
                    data: data,
                    headers: res.headers
                });
            });
        });

        req.on('error', (err) => {
            reject(err);
        });

        if (options.data) {
            req.write(JSON.stringify(options.data));
        }

        req.end();
    });
}

// Endpoint principal
router.get('/', async (req, res) => {
    try {
        createDirectories();
        const latestLog = getLatestAdminLog();
        if (!latestLog) {
            return res.json({
                success: false,
                message: 'Nenhum arquivo de log admin encontrado',
                data: []
            });
        }
        const tempPath = copyAdminLogToTemp(latestLog);
        if (!tempPath) {
            return res.status(500).json({
                success: false,
                message: 'Erro ao copiar log para pasta temporária',
                data: []
            });
        }
        // Tenta ler como UTF-16LE, se falhar tenta UTF-8
        let logContent = '';
        try {
            logContent = fs.readFileSync(tempPath, 'utf16le');
        } catch (e) {
            try {
                logContent = fs.readFileSync(tempPath, 'utf8');
            } catch (err) {
                return res.status(500).json({
                    success: false,
                    message: 'Erro ao ler conteúdo do log',
                    data: []
                });
            }
        }
        // Processar o conteúdo do log - separar cada evento em linha
        const logLines = logContent.split(/\r?\n/)
            .filter(line => line.trim() !== '') // Remove linhas vazias
            .map(line => line.trim()); // Remove espaços extras
        
        // Salvar no banco
        const jsonData = {
            file: latestLog,
            content: logLines,
            savedAt: new Date().toISOString()
        };
        
        logger.adminlog(`Salvando arquivo: ${ADMIN_DB_PATH}`);
        logger.adminlog(`Conteúdo do log: ${logContent.length} caracteres`);
        
        fs.writeFileSync(ADMIN_DB_PATH, JSON.stringify(jsonData, null, 2), 'utf8');
        
        // --- Envio para o webhook ---
        let adminWebhookUrl = null;
        if (fs.existsSync(WEBHOOKS_PATH)) {
            try {
                const webhooks = JSON.parse(fs.readFileSync(WEBHOOKS_PATH, 'utf8'));
                adminWebhookUrl = webhooks.adminlog;
                logger.adminlog(`Webhook URL encontrada: ${adminWebhookUrl ? 'Sim' : 'Não'}`);
            } catch (error) {
                logger.error('Erro ao ler webhooks.json', { error: error.message });
            }
        }
        if (!adminWebhookUrl) {
            return res.status(500).json({
                success: false,
                message: 'Webhook do adminlog não configurado em webhooks.json',
                data: []
            });
        }
        let lastIndex = -1;
        if (fs.existsSync(LAST_LINE_PATH)) {
            try {
                const lastData = JSON.parse(fs.readFileSync(LAST_LINE_PATH, 'utf8'));
                if (lastData.file === latestLog) {
                    lastIndex = lastData.lastIndex;
                }
            } catch (error) {
                logger.error('Erro ao ler lastAdminLogLine.json', { error: error.message });
            }
        }
        const newLines = logLines.slice(lastIndex + 1);
        logger.adminlog(`Total de linhas: ${logLines.length}, Último índice: ${lastIndex}, Novas linhas: ${newLines.length}`);
        
        for (let i = 0; i < newLines.length; i++) {
            const line = newLines[i];
            if (line) {
                logger.debug(`Enviando linha: ${line}`);
                try {
                    // Formatar a mensagem para melhor legibilidade
                    const formattedMessage = formatAdminLogMessage(line);
                    
                    const response = await makeRequest({
                        url: adminWebhookUrl,
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        data: formattedMessage
                    });
                    logger.debug(`Linha enviada com sucesso: ${response.status}`);
                } catch (err) {
                    logger.error('Erro ao enviar para webhook', { 
                        error: err.message,
                        response: err.response?.data 
                    });
                }
            }
        }
        // Atualizar o índice da última linha enviada
        fs.writeFileSync(LAST_LINE_PATH, JSON.stringify({ file: latestLog, lastIndex: logLines.length - 1 }, null, 2), 'utf8');
        // --- Fim do envio para webhook ---
        
        logger.adminlog('Arquivo salvo com sucesso');
        // Deletar arquivo temporário
        if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath);
        res.set('Content-Type', 'application/json; charset=utf-8');
        res.json({
            success: true,
            message: 'Log admin lido com sucesso',
            file: latestLog,
            data: logContent
        });
    } catch (error) {
        logger.error('Erro no endpoint adminlog', { error: error.message });
        res.status(500).json({
            success: false,
            message: 'Erro interno do servidor',
            error: error.message,
            data: []
        });
    }
});

module.exports = router; 