const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const url = require('url');

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

// Configurações
const SCUM_LOG_PATH = process.env.SCUM_LOG_PATH || './logs';
const SCUM_LOG_CACHE_PATH = process.env.SCUM_LOG_CACHE_PATH || './src/data/logs/cache';
const SCUM_LOG_MAX_RETRIES = parseInt(process.env.SCUM_LOG_MAX_RETRIES) || 2;
const LAST_ONLINE_PATH = 'src/data/players/lastOnline.json';
const WEBHOOKS_PATH = path.join('src/data/webhooks.json');

// Criar diretórios necessários
const createDirectories = () => {
    const dirs = [
        SCUM_LOG_CACHE_PATH,
        'src/data/players',
        'src/data/temp'
    ];
    
    dirs.forEach(dir => {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    });
};

// Função para copiar arquivo de log para pasta temporária
const copyLogToTemp = (logFileName) => {
    const sourcePath = path.join(SCUM_LOG_PATH, logFileName);
    const tempPath = path.join('src/data/temp', logFileName);
    
    try {
        fs.copyFileSync(sourcePath, tempPath);
        return tempPath;
    } catch (error) {
        console.error(`Erro ao copiar log: ${error.message}`);
        return null;
    }
};

// Função para ler conteúdo do log
const readLogContent = (logPath) => {
    try {
        // Tenta ler como UTF-16LE
        return fs.readFileSync(logPath, 'utf16le');
    } catch (error) {
        try {
            // Se falhar, tenta como UTF-8
            return fs.readFileSync(logPath, 'utf8');
        } catch (err) {
            console.error(`Erro ao ler log: ${err.message}`);
            return null;
        }
    }
};

// Função para extrair informações de login/logout
const extractPlayerInfo = (logContent) => {
    const players = [];
    const lines = logContent.split(/\r?\n/);
    
    lines.forEach(line => {
        const trimmedLine = line.trim();
        if (!trimmedLine) return;
        
        // Novo padrão para login
        const loginMatch = trimmedLine.match(/^([0-9.:-]+): '([0-9.]+) ([0-9]+):([^()]+)\(\d+\)' logged in at: X=([\-\d.]+) Y=([\-\d.]+) Z=([\-\d.]+)/);
        if (loginMatch) {
            players.push({
                action: 'login',
                timestamp: loginMatch[1],
                ip: loginMatch[2],
                steamId: loginMatch[3],
                playerName: loginMatch[4],
                position: {
                    x: loginMatch[5],
                    y: loginMatch[6],
                    z: loginMatch[7]
                },
                loginTime: new Date().toISOString()
            });
            return;
        }
        
        // Novo padrão para logout
        const logoutMatch = trimmedLine.match(/^([0-9.:-]+): '([0-9.]+) ([0-9]+):([^()]+)\(\d+\)' logged out at: (.+)$/);
        if (logoutMatch) {
            players.push({
                action: 'logout',
                timestamp: logoutMatch[1],
                ip: logoutMatch[2],
                steamId: logoutMatch[3],
                playerName: logoutMatch[4],
                logoutInfo: logoutMatch[5],
                logoutTime: new Date().toISOString()
            });
        }
    });
    return players;
};

// Função para atualizar banco de dados de jogadores
const updatePlayersDatabase = (players) => {
    const dbPath = 'src/data/players/players.json';
    let playersDb = {};
    // Carregar banco existente
    if (fs.existsSync(dbPath)) {
        try {
            playersDb = JSON.parse(fs.readFileSync(dbPath, 'utf8'));
        } catch (error) {
            console.error('Erro ao carregar banco de jogadores:', error.message);
        }
    }
    
    // Ordenar eventos por timestamp (garante ordem cronológica)
    players.sort((a, b) => parseLogTimestamp(a.timestamp) - parseLogTimestamp(b.timestamp));
    
    // Processar eventos em ordem cronológica
    players.forEach(player => {
        const steamId = player.steamId;
        const eventDate = parseLogTimestamp(player.timestamp);
        
        // Inicializar jogador se não existir
        if (!playersDb[steamId]) {
            playersDb[steamId] = {
                playerName: player.playerName,
                steamId: steamId,
                totalPlayTime: 0,
                lastLogin: null,
                lastLogout: null,
                isOnline: false,
                tags: [],
                processedSessions: []
            };
        } else {
            // Se já existe, garantir que processedSessions é carregado do JSON
            if (!Array.isArray(playersDb[steamId].processedSessions)) {
                playersDb[steamId].processedSessions = [];
            }
        }
        
        // Criar chave única para a sessão (login + logout)
        const sessionKey = `${player.timestamp}_${player.action}`;
        
        // Verificar se esta sessão já foi processada
        if (playersDb[steamId].processedSessions.includes(sessionKey)) {
            return; // Pular se já foi processada
        }
        
        if (player.action === 'login') {
            playersDb[steamId].playerName = player.playerName;
            playersDb[steamId].lastLogin = eventDate.toISOString();
            playersDb[steamId].isOnline = true;
            
            // Marcar início da sessão
            playersDb[steamId]._currentSessionStart = eventDate;
            
        } else if (player.action === 'logout') {
            playersDb[steamId].lastLogout = eventDate.toISOString();
            playersDb[steamId].isOnline = false;
            
            // Calcular tempo da sessão se houver login pendente
            if (playersDb[steamId]._currentSessionStart) {
                const sessionStart = playersDb[steamId]._currentSessionStart;
                const sessionEnd = eventDate;
                const sessionTime = sessionEnd.getTime() - sessionStart.getTime();
                
                // Só adiciona se o tempo for válido (positivo e razoável)
                if (sessionTime > 0 && sessionTime < 24 * 60 * 60 * 1000) { // Máximo 24 horas por sessão
                    playersDb[steamId].totalPlayTime += sessionTime;
                    console.log(`[PLAYERS] ${player.playerName}: Sessão de ${Math.round(sessionTime / 1000 / 60)} minutos adicionada`);
                }
                
                delete playersDb[steamId]._currentSessionStart;
            }
        }
        
        // Marcar sessão como processada
        playersDb[steamId].processedSessions.push(sessionKey);
    });
    
    // Finalizar sessões pendentes automaticamente (APENAS para jogadores que não estão mais online)
    const currentTime = new Date();
    Object.values(playersDb).forEach(player => {
        // Log de depuração

        
        // Só finalizar sessões pendentes se o jogador NÃO está online
        // Jogadores online devem permanecer online até terem logout registrado
        if (
            player.isOnline === false && // Só processar jogadores que já estão marcados como offline
            player.lastLogin &&
            (player.lastLogout === null || player.lastLogout === undefined || player.lastLogout === '')
        ) {
            const lastLoginDate = new Date(player.lastLogin);
            const sessionTime = currentTime.getTime() - lastLoginDate.getTime();
            // Só finaliza se a sessão tem mais de 5 minutos (evita sessões muito curtas)
            if (sessionTime > 5 * 60 * 1000 && sessionTime < 24 * 60 * 60 * 1000) {
                player.totalPlayTime += sessionTime;
                player.lastLogout = currentTime.toISOString();
                console.log(`[PLAYERS] ${player.playerName}: Sessão pendente de ${Math.round(sessionTime / 1000 / 60)} minutos finalizada`);
            }
        }
        // Garantir que lastLogout nunca seja undefined
        if (typeof player.lastLogout === 'undefined') {
            player.lastLogout = null;
        }
    });
    
    // Limpar apenas campos temporários antes de salvar
    Object.values(playersDb).forEach(player => {
        if (player._currentSessionStart) delete player._currentSessionStart;
        // NÃO remover processedSessions!
    });
    
    // Garantir que processedSessions está presente em todos os jogadores antes de salvar
    Object.values(playersDb).forEach(player => {
        if (!Array.isArray(player.processedSessions)) {
            player.processedSessions = [];
        }
    });
    
    // Forçar persistência de processedSessions no JSON
    const playersDbToSave = {};
    Object.keys(playersDb).forEach(steamId => {
        playersDbToSave[steamId] = { ...playersDb[steamId] };
        playersDbToSave[steamId].processedSessions = [...(playersDb[steamId].processedSessions || [])];
    });
    

    
    // Salvar banco atualizado
    try {
        fs.writeFileSync(dbPath, JSON.stringify(playersDbToSave, null, 2), 'utf8');
        return playersDbToSave; // Retornar o objeto com processedSessions
    } catch (error) {
        console.error('Erro ao salvar banco de jogadores:', error.message);
        return null;
    }
};

// Função para gerar tags baseadas no tempo de jogo
const generateTags = (playersDb) => {
    Object.keys(playersDb).forEach(steamId => {
        const player = playersDb[steamId];
        const totalHours = player.totalPlayTime / (1000 * 60 * 60);
        
        // Limpar tags antigas
        player.tags = [];
        
        // Gerar tags baseadas no tempo de jogo
        if (totalHours >= 100) {
            player.tags.push('Veterano');
        }
        if (totalHours >= 50) {
            player.tags.push('Experiente');
        }
        if (totalHours >= 20) {
            player.tags.push('Regular');
        }
        if (totalHours >= 5) {
            player.tags.push('Novato');
        }
        if (totalHours < 5) {
            player.tags.push('Iniciante');
        }
        
        // Tag especial para jogadores online
        if (player.isOnline) {
            player.tags.push('Online');
        }
    });
    
    return playersDb;
};

// Função para obter emoji de ranking
function getRankingEmoji(hours) {
    if (hours >= 200) return '👑'; // Lendário
    if (hours >= 100) return '🏆'; // Veterano
    if (hours >= 50)  return '🥇'; // Experiente
    if (hours >= 20)  return '🥈'; // Regular
    if (hours >= 5)   return '🥉'; // Novato
    return '🆕'; // Iniciante
}

function getCurrentOnlineList(playersDb) {
    return Object.values(playersDb)
        .filter(player => player.isOnline)
        .map(player => player.steamId)
        .sort();
}

function readLastOnlineList() {
    if (fs.existsSync(LAST_ONLINE_PATH)) {
        try {
            return JSON.parse(fs.readFileSync(LAST_ONLINE_PATH, 'utf8'));
        } catch (e) {
            return [];
        }
    }
    return [];
}

function saveLastOnlineList(onlineList) {
    fs.writeFileSync(LAST_ONLINE_PATH, JSON.stringify(onlineList, null, 2), 'utf8');
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

// Função para enviar webhook com jogadores online
const sendWebhook = async (playersDb) => {
    const onlinePlayers = Object.values(playersDb).filter(player => player.isOnline);
    const currentOnlineList = getCurrentOnlineList(playersDb);
    const lastOnlineList = readLastOnlineList();
    // Só envia se houve mudança
    const changed = currentOnlineList.length !== lastOnlineList.length ||
        currentOnlineList.some((id, i) => id !== lastOnlineList[i]);
    
    
    
    if (!changed) {
        console.log('Nenhuma mudança na lista de jogadores online. Webhook não enviado.');
        return { skipped: true };
    }
    const webhooks = readWebhooks();
    const webhookUrl = webhooks.painelplayers || process.env.WEBHOOK_PAINELPLAYERS;
    const webhookData = {
        timestamp: new Date().toISOString(),
        totalOnline: onlinePlayers.length,
        players: onlinePlayers.map(player => ({
            name: player.playerName,
            steamId: player.steamId,
            totalPlayTime: Math.round(player.totalPlayTime / (1000 * 60 * 60)), // em horas inteiras
            tags: player.tags,
            lastLogin: player.lastLogin
        }))
    };
    try {
        if (webhookUrl) {
            // Estatísticas
            const statsField =
                `- **Jogadores Online:** ${onlinePlayers.length}\n` +
                `- **Total de Jogadores:** ${Object.keys(playersDb).length}`;

            // Lista de jogadores online formatada
            let playersList = '━━━━━━━━━━━━━━━━━━━━\n';
            if (onlinePlayers.length > 0) {
                playersList += onlinePlayers.map(player => {
                    const playTimeHours = Math.floor(player.totalPlayTime / (1000 * 60 * 60));
                    const emoji = getRankingEmoji(playTimeHours);
                    return `${emoji}   ${player.playerName} - ${playTimeHours}h`;
                }).join('\n');
                playersList += '\n━━━━━━━━━━━━━━━━━━━━';
            } else {
                playersList += 'Nenhum jogador online no momento\n━━━━━━━━━━━━━━━━━━━━';
            }

            // Embed Discord
            const embed = {
                title: "🎮 SCUM Server - Status dos Jogadores",
                color: onlinePlayers.length > 0 ? 0x00ff00 : 0xff0000,
                fields: [
                    {
                        name: "📊 Estatísticas",
                        value: statsField,
                        inline: false
                    },
                    {
                        name: `👥 Jogadores Online (${onlinePlayers.length}):`,
                        value: playersList,
                        inline: false
                    },
                    {
                        name: "🕐 Última Atualização",
                        value: new Date().toLocaleString('pt-BR'),
                        inline: false
                    }
                ],
                timestamp: new Date().toISOString(),
                footer: {
                    text: "SCUM Server Manager"
                }
            };

            const discordMessage = {
                embeds: [embed]
            };

            const response = await makeRequest({
                url: webhookUrl,
                method: 'POST',
                data: discordMessage,
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            console.log(`Webhook enviado com sucesso! Status: ${response.status}`);
        } else {
            console.log('WEBHOOK_PAINELPLAYERS não configurado');
        }
    } catch (error) {
        console.error('Erro ao enviar webhook Discord:', error.message);
        if (error.response) {
            console.error('Status do erro:', error.response.status);
            console.error('Dados do erro:', error.response.data);
        }
    }
    saveLastOnlineList(currentOnlineList);
    return webhookData;
};

// Função para forçar webhook (ignora mudanças)
const forceWebhook = async (playersDb) => {
    console.log('=== FORÇANDO WEBHOOK DE PLAYERS ===');
    const onlinePlayers = Object.values(playersDb).filter(player => player.isOnline);
    const webhooks = readWebhooks();
    const webhookUrl = webhooks.painelplayers || process.env.WEBHOOK_PAINELPLAYERS;
    
    if (!webhookUrl) {
        console.log('Webhook painelplayers não configurado');
        return;
    }
    
    try {
        // Estatísticas
        const statsField =
            `- **Jogadores Online:** ${onlinePlayers.length}\n` +
            `- **Total de Jogadores:** ${Object.keys(playersDb).length}`;

        // Lista de jogadores online formatada
        let playersList = '━━━━━━━━━━━━━━━━━━━━\n';
        if (onlinePlayers.length > 0) {
            playersList += onlinePlayers.map(player => {
                const playTimeHours = Math.floor(player.totalPlayTime / (1000 * 60 * 60));
                const emoji = getRankingEmoji(playTimeHours);
                return `${emoji}   ${player.playerName} - ${playTimeHours}h`;
            }).join('\n');
            playersList += '\n━━━━━━━━━━━━━━━━━━━━';
        } else {
            playersList += 'Nenhum jogador online no momento\n━━━━━━━━━━━━━━━━━━━━';
        }

        // Embed Discord
        const embed = {
            title: "🎮 SCUM Server - Status dos Jogadores (FORÇADO)",
            color: onlinePlayers.length > 0 ? 0x00ff00 : 0xff0000,
            fields: [
                {
                    name: "📊 Estatísticas",
                    value: statsField,
                    inline: false
                },
                {
                    name: `👥 Jogadores Online (${onlinePlayers.length}):`,
                    value: playersList,
                    inline: false
                },
                {
                    name: "🕐 Última Atualização",
                    value: new Date().toLocaleString('pt-BR'),
                    inline: false
                }
            ],
            timestamp: new Date().toISOString(),
            footer: {
                text: "SCUM Server Manager - FORÇADO"
            }
        };

        const discordMessage = {
            embeds: [embed]
        };

        const response = await makeRequest({
            url: webhookUrl,
            method: 'POST',
            data: discordMessage,
            headers: {
                'Content-Type': 'application/json'
            }
        });
        console.log(`Webhook forçado enviado com sucesso! Status: ${response.status}`);
        
    } catch (error) {
        console.error('Erro ao enviar webhook forçado:', error.message);
        if (error.response) {
            console.error('Status do erro:', error.response.status);
            console.error('Dados do erro:', error.response.data);
        }
    }
};

// Função para limpar arquivos temporários
const cleanupTempFiles = () => {
    const tempDir = 'src/data/temp';
    if (fs.existsSync(tempDir)) {
        const files = fs.readdirSync(tempDir);
        files.forEach(file => {
            if (file.endsWith('.log')) {
                fs.unlinkSync(path.join(tempDir, file));
            }
        });
    }
};

// Endpoint principal
router.get('/painelplayers', async (req, res) => {
    try {
        // 1. Criar diretórios necessários
        createDirectories();
        // 2. Listar arquivos de log de login
        const logFiles = fs.readdirSync(SCUM_LOG_PATH)
            .filter(file => file.startsWith('login_') && file.endsWith('.log'));
        if (logFiles.length === 0) {
            return res.json({
                success: false,
                message: 'Nenhum arquivo de log de login encontrado',
                data: []
            });
        }
        // 3. Buscar o arquivo mais recente
        const latestLogFile = logFiles
            .map(file => ({
                name: file,
                time: fs.statSync(path.join(SCUM_LOG_PATH, file)).mtime.getTime()
            }))
            .sort((a, b) => b.time - a.time)[0].name;
        // 4. Copiar para pasta temporária
        const tempLogPath = copyLogToTemp(latestLogFile);
        if (!tempLogPath) {
            return res.status(500).json({
                success: false,
                message: 'Erro ao copiar log para pasta temporária',
                data: []
            });
        }
        // 5. Ler conteúdo
        const logContent = readLogContent(tempLogPath);
        if (!logContent) {
            return res.status(500).json({
                success: false,
                message: 'Erro ao ler conteúdo do log',
                data: []
            });
        }
        // 6. Extrair informações
        const allPlayers = extractPlayerInfo(logContent);
        // 6.1. Obter lista de SteamIDs presentes no novo log de login
        const steamIdsNoLog = allPlayers.filter(p => p.action === 'login').map(p => p.steamId);
        // 7. Atualizar banco de dados
        const playersDb = updatePlayersDatabase(allPlayers);
        if (!playersDb) {
            return res.status(500).json({
                success: false,
                message: 'Erro ao atualizar banco de dados',
                data: []
            });
        }
        // 7.1. Marcar como offline quem não está no novo log
        Object.values(playersDb).forEach(player => {
            if (player.isOnline && !steamIdsNoLog.includes(player.steamId)) {
                player.isOnline = false;
            }
        });
        // 7.2. Se não houver nenhum login no novo log, deslogar todos
        if (allPlayers.filter(p => p.action === 'login').length === 0) {
            Object.values(playersDb).forEach(player => {
                player.isOnline = false;
            });
        }
        // 8. Gerar tags
        const updatedPlayersDb = generateTags(playersDb);
        // 9. Enviar webhook (agora assíncrono, não trava o endpoint)
        setTimeout(() => {
            sendWebhook(updatedPlayersDb).catch(e => console.error("Erro no webhook:", e));
        }, 100);
        
        // 9.1. Forçar webhook se solicitado via query parameter
        if (req.query.force_webhook === 'true') {
            console.log('Forçando envio de webhook...');
            setTimeout(() => {
                forceWebhook(updatedPlayersDb).catch(e => console.error("Erro no webhook forçado:", e));
            }, 200);
        }
        // 10. Deletar arquivo temporário
        if (fs.existsSync(tempLogPath)) {
            fs.unlinkSync(tempLogPath);
        }
        // 11. Salvar banco atualizado (usar playersDb que contém processedSessions)
        fs.writeFileSync('src/data/players/players.json', JSON.stringify(playersDb, null, 2), 'utf8');
        // 12. Preparar resposta
        let responseDb = {};
        try {
            responseDb = JSON.parse(fs.readFileSync('src/data/players/players.json', 'utf8'));
        } catch (e) {
            responseDb = {};
        }
        res.json({
            success: true,
            message: 'Dados processados com sucesso',
            data: Object.values(responseDb)
        });
    } catch (error) {
        console.error('Erro no endpoint painelplayers:', error);
        res.status(500).json({
            success: false,
            message: 'Erro interno do servidor',
            error: error.message,
            data: []
        });
    }
});

// Endpoint para obter dados de um jogador específico
router.get('/player/:steamId', (req, res) => {
    try {
        const { steamId } = req.params;
        const dbPath = 'src/data/players/players.json';
        
        if (!fs.existsSync(dbPath)) {
            return res.status(404).json({
                success: false,
                message: 'Banco de dados não encontrado'
            });
        }
        
        const playersDb = JSON.parse(fs.readFileSync(dbPath, 'utf8'));
        const player = playersDb[steamId];
        
        if (!player) {
            return res.status(404).json({
                success: false,
                message: 'Jogador não encontrado'
            });
        }
        
        res.json({
            success: true,
            data: player
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Erro interno do servidor',
            error: error.message
        });
    }
});

// Endpoint para obter todos os jogadores
router.get('/all', (req, res) => {
    try {
        const dbPath = 'src/data/players/players.json';
        
        if (!fs.existsSync(dbPath)) {
            return res.json({
                success: true,
                data: []
            });
        }
        
        const playersDb = JSON.parse(fs.readFileSync(dbPath, 'utf8'));
        
        res.json({
            success: true,
            data: Object.values(playersDb)
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Erro interno do servidor',
            error: error.message
        });
    }
});

// Endpoint para forçar webhook
router.get('/force-webhook', async (req, res) => {
    try {
        // Carregar dados atuais
        let playersDb = {};
        if (fs.existsSync('src/data/players/players.json')) {
            try {
                playersDb = JSON.parse(fs.readFileSync('src/data/players/players.json', 'utf8'));
            } catch (e) {
                console.error('Erro ao carregar dados de jogadores:', e.message);
            }
        }
        
        // Forçar webhook
        await forceWebhook(playersDb);
        
        res.json({
            success: true,
            message: 'Webhook forçado enviado com sucesso'
        });
        
    } catch (error) {
        console.error('Erro ao forçar webhook:', error);
        res.status(500).json({
            success: false,
            message: 'Erro ao forçar webhook',
            error: error.message
        });
    }
});

// Endpoint de teste do webhook
router.get('/test-webhook', async (req, res) => {
    try {
        const webhookUrl = process.env.WEBHOOK_PAINELPLAYERS;
        console.log('Testando webhook URL:', webhookUrl);
        
        if (!webhookUrl) {
            return res.json({
                success: false,
                message: 'WEBHOOK_PAINELPLAYERS não configurado'
            });
        }
        
        const testMessage = {
            content: "🧪 Teste de webhook do SCUM Server Manager!"
        };
        
        console.log('Enviando mensagem de teste:', testMessage);
        
        const response = await makeRequest({
            url: webhookUrl,
            method: 'POST',
            data: testMessage,
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('Teste de webhook bem-sucedido. Status:', response.status);
        
        res.json({
            success: true,
            message: 'Webhook testado com sucesso',
            status: response.status
        });
        
    } catch (error) {
        console.error('Erro no teste do webhook:', error.message);
        if (error.response) {
            console.error('Status do erro:', error.response.status);
            console.error('Dados do erro:', error.response.data);
        }
        
        res.json({
            success: false,
            message: 'Erro no teste do webhook',
            error: error.message
        });
    }
});

// Endpoint para debug do sistema de tempo
router.get('/debug-time', (req, res) => {
    try {
        const dbPath = 'src/data/players/players.json';
        
        if (!fs.existsSync(dbPath)) {
            return res.json({
                success: false,
                message: 'Banco de dados não encontrado'
            });
        }
        
        const playersDb = JSON.parse(fs.readFileSync(dbPath, 'utf8'));
        
        // Converter tempos para horas para facilitar visualização
        const debugData = Object.values(playersDb).map(player => ({
            name: player.playerName,
            steamId: player.steamId,
            totalPlayTimeHours: Math.round(player.totalPlayTime / 1000 / 60 / 60),
            totalPlayTimeMinutes: Math.round(player.totalPlayTime / 1000 / 60),
            lastLogin: player.lastLogin,
            lastLogout: player.lastLogout,
            isOnline: player.isOnline,
            tags: player.tags
        }));
        
        res.json({
            success: true,
            message: 'Dados de debug do sistema de tempo',
            data: debugData
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Erro interno do servidor',
            error: error.message
        });
    }
});

// Função para converter timestamp do log para Date
function parseLogTimestamp(ts) {
    // Exemplo de ts: 2025.07.12-14.49.00
    // Formato: yyyy.MM.dd-HH.mm.ss
    const match = ts.match(/(\d{4})\.(\d{2})\.(\d{2})-(\d{2})\.(\d{2})\.(\d{2})/);
    if (match) {
        const [_, year, month, day, hour, min, sec] = match;
        // Criar data usando UTC para evitar problemas de timezone
        const date = new Date(Date.UTC(parseInt(year), parseInt(month) - 1, parseInt(day), parseInt(hour), parseInt(min), parseInt(sec)));
        return date;
    }
    // Se não bater o padrão, retorna data atual
    console.warn(`[PLAYERS] Timestamp inválido: ${ts}, usando data atual`);
    return new Date();
}

module.exports = router; 