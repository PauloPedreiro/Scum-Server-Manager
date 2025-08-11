const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const url = require('url');

const CHAT_LOG_PATH = process.env.SCUM_LOG_PATH;
const TEMP_PATH = 'src/data/temp';
const LAST_CHAT_READ_PATH = 'src/data/players/lastChatRead.json';
const WEBHOOKS_PATH = path.join('src/data/webhooks.json');

// Função para ler o último timestamp lido
function getLastChatTimestamp() {
    if (fs.existsSync(LAST_CHAT_READ_PATH)) {
        try {
            return JSON.parse(fs.readFileSync(LAST_CHAT_READ_PATH, 'utf8')).lastTimestamp || null;
        } catch (e) {
            return null;
        }
    }
    return null;
}

// Função para salvar o último timestamp lido
function setLastChatTimestamp(ts) {
    fs.writeFileSync(LAST_CHAT_READ_PATH, JSON.stringify({ lastTimestamp: ts }, null, 2), 'utf8');
}

// Função para encontrar o último log de chat
function getLatestChatLog() {
    if (!fs.existsSync(CHAT_LOG_PATH)) return null;
    const files = fs.readdirSync(CHAT_LOG_PATH)
        .filter(f => f.startsWith('chat_') && f.endsWith('.log'));
    if (files.length === 0) return null;
    return files.map(f => ({
        name: f,
        time: fs.statSync(path.join(CHAT_LOG_PATH, f)).mtime.getTime()
    })).sort((a, b) => b.time - a.time)[0].name;
}

// Função para copiar para temp
function copyChatToTemp(logFileName) {
    const sourcePath = path.join(CHAT_LOG_PATH, logFileName);
    const tempPath = path.join(TEMP_PATH, logFileName);
    fs.copyFileSync(sourcePath, tempPath);
    return tempPath;
}

// Função para ler e filtrar mensagens novas
function parseChatLog(content, lastTimestamp) {
    const lines = content.split(/\r?\n/);
    // Regex mais permissivo para mensagens do chat
    const regex = /^([0-9.:-]+): '([0-9]+):?([^']*)\((\d+)\)' '([^:]+): (.*)'$/;
    const messages = [];
    for (const line of lines) {
        if (!line.trim()) continue;
        const match = line.match(regex);
        // Log para debug
        console.log('Linha:', line);
        if (match) {
            console.log('Match:', match);
            const [_, timestamp, steamId, playerName, playerId, chatType, message] = match;
            if (!lastTimestamp || timestamp > lastTimestamp) {
                messages.push({
                    timestamp,
                    steamId,
                    playerName: playerName.trim(),
                    chatType: chatType.trim(),
                    message: message.trim()
                });
            }
        } else {
            // Ignorar linhas de versão do jogo e outros logs não relacionados ao chat
            if (!line.includes('Game version:') && !line.includes('[Vehicle') && !line.includes('[Disappeared]') && !line.includes('[Destroyed]')) {
            console.log('Não bateu regex:', line);
            }
        }
    }
    return messages;
}

function readWebhooks() {
    if (fs.existsSync(WEBHOOKS_PATH)) {
        try {
            return JSON.parse(fs.readFileSync(WEBHOOKS_PATH, 'utf8'));
        } catch (e) {
            return {};
        }
    }
    return {};
}

// Função para mapear tipos de chat para emojis
function getChatTypeEmoji(chatType) {
    const emojiMap = {
        'Local': '🎯',
        'Global': '🌐',
        'Squad': '👥'
    };
    return emojiMap[chatType] || `(${chatType})`;
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

router.get('/chat_in_game', async (req, res) => {
    try {
        // 1. Encontrar o último log de chat
        const latestLog = getLatestChatLog();
        if (!latestLog) {
            return res.json({ success: false, message: 'Nenhum log de chat encontrado.', data: [] });
        }
        // 2. Copiar para temp
        const tempPath = copyChatToTemp(latestLog);
        // 3. Ler conteúdo em UTF-16LE
        const content = fs.readFileSync(tempPath, 'utf16le');
        // 4. Ler último timestamp lido
        const lastTimestamp = getLastChatTimestamp();
        // 5. Filtrar mensagens novas
        const messages = parseChatLog(content, lastTimestamp);
        // 5.1. Enviar cada mensagem para o Discord (exceto Squad)
        const webhooks = readWebhooks();
        const webhookUrl = webhooks.Chat_in_Game;
        if (webhookUrl && messages.length > 0) {
            console.log(`Enviando ${messages.length} mensagens para o Discord...`);
            for (const msg of messages) {
                // Pular mensagens Squad apenas se NÃO forem comandos relevantes (/rg, /rv, /rm, /mc, /dv)
                if (msg.chatType === 'Squad') {
                    const isRelevantCommand = /^\/(rg|rv|rm|mc|dv)\b/i.test(msg.message);
                    if (!isRelevantCommand) {
                        console.log(`⏭️ Mensagem Squad ignorada: ${msg.playerName}: ${msg.message}`);
                        continue;
                    }
                }
                
                const chatTypeEmoji = getChatTypeEmoji(msg.chatType);
                const text = `${chatTypeEmoji} ${msg.playerName} (${msg.steamId}): ${msg.message}`;
                try {
                    const response = await makeRequest({
                        url: webhookUrl,
                        method: 'POST',
                        data: { content: text },
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    console.log(`✅ Mensagem enviada: ${msg.playerName}: ${msg.message}`);
                } catch (error) {
                    console.error(`❌ Erro ao enviar mensagem para Discord:`, error.message);
                    if (error.response) {
                        console.error('Status:', error.response.status);
                        console.error('Dados:', error.response.data);
                    }
                }
                // Delay reduzido entre mensagens para processar comandos simultâneos
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        }
        // 6. Atualizar controle se houver mensagens novas
        if (messages.length > 0) {
            setLastChatTimestamp(messages[messages.length - 1].timestamp);
        }
        // 7. Deletar arquivo temporário
        if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath);
        // 8. Responder em UTF-8
        res.set('Content-Type', 'application/json; charset=utf-8');
        res.json({ success: true, message: 'Mensagens lidas com sucesso.', data: messages });
    } catch (error) {
        res.status(500).json({ success: false, message: 'Erro ao ler log de chat.', error: error.message });
    }
});

// Endpoint para forçar webhook de chat
router.get('/force-webhook', async (req, res) => {
    try {
        const webhooks = readWebhooks();
        const webhookUrl = webhooks.Chat_in_Game;
        
        if (!webhookUrl) {
            return res.json({
                success: false,
                message: 'Webhook Chat_in_Game não configurado'
            });
        }
        
        const testMessages = [
            "🌐 [SISTEMA] Teste de webhook forçado!",
            "🌐 [ADM] Admin: Sistema funcionando corretamente",
            "🌐 [INFO] Webhook de chat ativo"
        ];
        
        for (const message of testMessages) {
            await makeRequest({
                url: webhookUrl,
                method: 'POST',
                data: { content: message },
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            await new Promise(resolve => setTimeout(resolve, 1000)); // Delay entre mensagens
        }
        
        res.json({
            success: true,
            message: 'Webhook de chat forçado enviado com sucesso'
        });
        
    } catch (error) {
        console.error('Erro ao forçar webhook de chat:', error);
        res.status(500).json({
            success: false,
            message: 'Erro ao forçar webhook de chat',
            error: error.message
        });
    }
});

module.exports = router; 