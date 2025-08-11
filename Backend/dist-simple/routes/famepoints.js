const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const url = require('url');

// Configurações
const SCUM_LOG_PATH = process.env.SCUM_LOG_PATH || './logs';
const SCUM_LOG_CACHE_PATH = process.env.SCUM_LOG_CACHE_PATH || './src/data/logs/cache';
const WEBHOOKS_PATH = path.join('src/data/webhooks.json');

// Criar diretórios necessários
const createDirectories = () => {
    const dirs = [
        SCUM_LOG_CACHE_PATH,
        'src/data/famepoints',
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

// Função para ler conteúdo do log com encoding UTF-16LE
const readLogContent = (logPath) => {
    try {
        // Tenta ler como UTF-16LE primeiro
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

// Função para extrair informações de famepoints
const extractFamepointsInfo = (logContent) => {
    const players = [];
    const lines = logContent.split(/\r?\n/);
    
    console.log(`[FAMEPOINTS] Processando ${lines.length} linhas`);
    
    lines.forEach((line, index) => {
        const trimmedLine = line.trim();
        if (!trimmedLine) return;
        
        // Padrão para linha de famepoints
        const fameMatch = trimmedLine.match(/Player\s+([^(]+)\((\d+)\)\s+was awarded\s+([\d.]+)\s+fame points in 10 minutes for a total of\s+([\d.]+)/);
        if (fameMatch) {
            const playerName = fameMatch[1].trim();
            const steamId = fameMatch[2];
            const totalFame = parseFloat(fameMatch[4]);
            
            players.push({
                playerName: playerName,
                steamId: steamId,
                totalFame: totalFame,
                timestamp: new Date().toISOString()
            });
            
            console.log(`[FAMEPOINTS] Jogador encontrado: ${playerName} (${steamId}) - Total Fame: ${totalFame}`);
        }
    });
    
    console.log(`[FAMEPOINTS] Total de jogadores processados: ${players.length}`);
    return players;
};

// Função para salvar dados de famepoints (apenas o mais recente por jogador)
const saveFamepointsData = (players) => {
    const dbPath = 'src/data/famepoints/famepoints.json';
    let famepointsDb = {};
    
    // Carregar dados existentes
    if (fs.existsSync(dbPath)) {
        try {
            famepointsDb = JSON.parse(fs.readFileSync(dbPath, 'utf8'));
        } catch (error) {
            console.error('Erro ao carregar dados de famepoints:', error.message);
        }
    }
    // famepointsDb agora será um objeto { steamId: {playerName, steamId, totalFame, timestamp} }
    // Atualizar ou adicionar o registro mais recente para cada jogador
    players.forEach(player => {
        // Sempre atualiza com o valor mais recente, independente se aumentou ou diminuiu
        famepointsDb[player.steamId] = player;
    });
    // Salvar dados atualizados
    try {
        fs.writeFileSync(dbPath, JSON.stringify(famepointsDb, null, 2), 'utf8');
        // Retornar como array para a resposta, removendo fameAwarded se existir
        return Object.values(famepointsDb).map(({playerName, steamId, totalFame, timestamp}) => ({playerName, steamId, totalFame, timestamp}));
    } catch (error) {
        console.error('Erro ao salvar dados de famepoints:', error.message);
        return null;
    }
};

// Função para gerar hash dos dados de fama
const generateFameDataHash = (famepointsData) => {
    // Ordenar por steamId para garantir consistência
    const sortedData = famepointsData.sort((a, b) => a.steamId.localeCompare(b.steamId));
    // Criar string com apenas os dados essenciais (steamId e totalFame)
    const dataString = sortedData.map(player => `${player.steamId}:${player.totalFame}`).join('|');
    return dataString;
};

// Função para verificar se arquivo já foi processado
const isFileAlreadyProcessed = (fileName, fileMTimeMs, currentDataHash) => {
    const lastProcessedPath = 'src/data/famepoints/lastProcessed.json';
    
    if (fs.existsSync(lastProcessedPath)) {
        try {
            const lastProcessed = JSON.parse(fs.readFileSync(lastProcessedPath, 'utf8'));
            return lastProcessed.fileName === fileName && 
                   lastProcessed.fileMTimeMs === fileMTimeMs && 
                   lastProcessed.dataHash === currentDataHash;
        } catch (error) {
            console.error('Erro ao verificar arquivo processado:', error.message);
        }
    }
    return false;
};

// Função para marcar arquivo como processado
const markFileAsProcessed = (fileName, fileMTimeMs, dataHash) => {
    const lastProcessedPath = 'src/data/famepoints/lastProcessed.json';
    const data = {
        fileName: fileName,
        fileMTimeMs: fileMTimeMs,
        dataHash: dataHash,
        processedAt: new Date().toISOString()
    };
    
    try {
        fs.writeFileSync(lastProcessedPath, JSON.stringify(data, null, 2), 'utf8');
    } catch (error) {
        console.error('Erro ao marcar arquivo como processado:', error.message);
    }
};

// Função para converter número para ordinal em português
const toOrdinal = (num) => {
    if (num === 1) return '1º';
    if (num === 2) return '2º';
    if (num === 3) return '3º';
    if (num === 4) return '4º';
    if (num === 5) return '5º';
    if (num === 6) return '6º';
    if (num === 7) return '7º';
    if (num === 8) return '8º';
    if (num === 9) return '9º';
    if (num === 10) return '10º';
    if (num === 11) return '11º';
    if (num === 12) return '12º';
    if (num === 13) return '13º';
    if (num === 14) return '14º';
    if (num === 15) return '15º';
    if (num === 16) return '16º';
    if (num === 17) return '17º';
    if (num === 18) return '18º';
    if (num === 19) return '19º';
    if (num === 20) return '20º';
    
    // Para números maiores que 20, usar formato padrão
    return `${num}º`;
};

// Função para ler webhooks
const readWebhooks = () => {
    if (fs.existsSync(WEBHOOKS_PATH)) {
        try {
            return JSON.parse(fs.readFileSync(WEBHOOKS_PATH, 'utf8'));
        } catch (e) {
            return {};
        }
    }
    return {};
};

// Função para enviar webhook de famepoints para Discord
const sendFamepointsWebhook = async (famepointsData) => {

    console.log('Dados de famepoints:', famepointsData);
    
    const webhooks = readWebhooks();
    const webhookUrl = webhooks.famepoints;
    
    console.log('Webhook URL:', webhookUrl);
    
    if (!webhookUrl) {
        console.log('Webhook famepoints não configurado');
        return;
    }
    
    try {
        // Ordenar jogadores por fame (maior para menor)
        const sortedPlayers = famepointsData.sort((a, b) => b.totalFame - a.totalFame);
        
        // Criar painel de fama
        const embed = {
            title: "🏆 Ranking de Fama",
            color: 0xFFD700, // Dourado
            description: `**${sortedPlayers.length}** jogadores ativos`,
            fields: [],
            timestamp: new Date().toISOString(),
            footer: {
                text: "SCUM Server Manager"
            }
        };
        
        // Adicionar top 10 jogadores como campos principais
        const topPlayers = sortedPlayers.slice(0, 10);
        
        // Criar ranking em formato compacto com números ordinais
        const rankingList = topPlayers.map((player, index) => {
            const rank = index + 1;
            const ordinalRank = toOrdinal(rank);
            const fameFormatted = player.totalFame.toLocaleString();
            return `${ordinalRank} ${player.playerName} **${fameFormatted}**`;
        }).join('\n');
        
        embed.fields.push({
            name: '🏅 Ranking',
            value: rankingList,
            inline: false
        });
        
        // Se houver mais de 10 jogadores, adicionar resumo
        if (sortedPlayers.length > 10) {
            const remainingPlayers = sortedPlayers.slice(10);
            const totalFameRemaining = remainingPlayers.reduce((sum, player) => sum + player.totalFame, 0);
            
            embed.fields.push({
                name: "📊 Mais Jogadores",
                value: `**${remainingPlayers.length}** jogadores adicionais • **${totalFameRemaining.toLocaleString()}** pontos totais`,
                inline: false
            });
        }
        
        const discordMessage = {
            embeds: [embed]
        };
        
        console.log('Embed a ser enviado:', JSON.stringify(discordMessage, null, 2));
        console.log('Enviando para Discord...');
        
        try {
            const response = await makeRequest({
                url: webhookUrl,
                method: 'POST',
                data: discordMessage,
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            console.log('Resposta do Discord - Status:', response.status);
            console.log('Resposta do Discord - Data:', response.data);
            console.log(`Webhook enviado com sucesso! ${sortedPlayers.length} jogadores processados`);
        } catch (axiosError) {
            console.error('Erro do Axios:', axiosError.message);
            if (axiosError.response) {
                console.error('Status do erro:', axiosError.response.status);
                console.error('Dados do erro:', axiosError.response.data);
            } else if (axiosError.request) {
                console.error('Erro de rede - sem resposta do servidor');
            }
            throw axiosError;
        }
    } catch (error) {
        console.error('Erro geral ao enviar webhook de famepoints:', error.message);
    }
};

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
        // 1. Criar diretórios necessários
        createDirectories();
        
        // 2. Listar arquivos de log de famepoints
        const logFiles = fs.readdirSync(SCUM_LOG_PATH)
            .filter(file => file.startsWith('famepoints_') && file.endsWith('.log'));
        
        if (logFiles.length === 0) {
            return res.json({
                success: false,
                message: 'Nenhum arquivo de log de famepoints encontrado',
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
        
        console.log(`[FAMEPOINTS] Arquivo mais recente: ${latestLogFile}`);
        
        // 4. Processar dados do arquivo
        const logContent = readLogContent(path.join(SCUM_LOG_PATH, latestLogFile));
        if (!logContent) {
            return res.status(500).json({
                success: false,
                message: 'Erro ao ler conteúdo do log',
                data: []
            });
        }
        
        const players = extractFamepointsInfo(logContent);
        const famepointsDb = saveFamepointsData(players);
        if (!famepointsDb) {
            return res.status(500).json({
                success: false,
                message: 'Erro ao salvar dados de famepoints',
                data: []
            });
        }
        
        // 5. Gerar hash dos dados de fama
        const currentDataHash = generateFameDataHash(famepointsDb);
        
        // 6. Verificar se arquivo já foi processado
        if (isFileAlreadyProcessed(latestLogFile, fs.statSync(path.join(SCUM_LOG_PATH, latestLogFile)).mtime.getTime(), currentDataHash)) {
            // Retornar dados salvos mesmo quando arquivo já foi processado
            return res.json({
                success: true,
                message: 'Arquivo já processado - dados atuais',
                data: famepointsDb
            });
        }
        
        // 7. Marcar arquivo como processado
        markFileAsProcessed(latestLogFile, fs.statSync(path.join(SCUM_LOG_PATH, latestLogFile)).mtime.getTime(), currentDataHash);
        
        // 8. Enviar webhook para Discord
        await sendFamepointsWebhook(famepointsDb);
        
        // 9. Preparar resposta
        res.json({
            success: true,
            message: 'Dados de famepoints processados com sucesso',
            data: famepointsDb
        });
        
    } catch (error) {
        console.error('Erro no endpoint famepoints:', error);
        res.status(500).json({
            success: false,
            message: 'Erro interno do servidor',
            error: error.message,
            data: []
        });
    }
});

module.exports = router; 