const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const url = require('url');
const logger = require('../src/logger');

const VEHICLE_LOG_PATH = process.env.SCUM_LOG_PATH;
const TEMP_PATH = 'src/data/temp';
const VEHICLES_DB_PATH = 'src/data/vehicles/vehicles.json';
const LAST_VEHICLE_READ_PATH = 'src/data/vehicles/lastVehicleRead.json';
const WEBHOOKS_PATH = path.join('src/data/webhooks.json');

// Função para criar diretórios necessários
const createDirectories = () => {
    const dirs = [
        TEMP_PATH,
        'src/data/vehicles'
    ];
    
    dirs.forEach(dir => {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    });
};

// Função para ler o último timestamp lido
function getLastVehicleTimestamp() {
    if (fs.existsSync(LAST_VEHICLE_READ_PATH)) {
        try {
            return JSON.parse(fs.readFileSync(LAST_VEHICLE_READ_PATH, 'utf8')).lastTimestamp || null;
        } catch (e) {
            return null;
        }
    }
    return null;
}

// Função para salvar o último timestamp lido
function setLastVehicleTimestamp(ts) {
    fs.writeFileSync(LAST_VEHICLE_READ_PATH, JSON.stringify({ lastTimestamp: ts }, null, 2), 'utf8');
}

// Função para encontrar o último log de veículos
function getLatestVehicleLog() {
    if (!fs.existsSync(VEHICLE_LOG_PATH)) return null;
    const files = fs.readdirSync(VEHICLE_LOG_PATH)
        .filter(f => f.startsWith('vehicle_destruction_') && f.endsWith('.log'));
    if (files.length === 0) return null;
    return files.map(f => ({
        name: f,
        time: fs.statSync(path.join(VEHICLE_LOG_PATH, f)).mtime.getTime()
    })).sort((a, b) => b.time - a.time)[0].name;
}

// Função para copiar log para pasta temporária
function copyVehicleLogToTemp(logFileName) {
    const sourcePath = path.join(VEHICLE_LOG_PATH, logFileName);
    const tempPath = path.join(TEMP_PATH, logFileName);
    
    try {
        fs.copyFileSync(sourcePath, tempPath);
        return tempPath;
    } catch (error) {
        console.error(`Erro ao copiar log de veículos: ${error.message}`);
        return null;
    }
}

// Função para ler conteúdo do log
function readVehicleLogContent(logPath) {
    try {
        // Tenta ler como UTF-16LE
        return fs.readFileSync(logPath, 'utf16le');
    } catch (error) {
        try {
            // Se falhar, tenta como UTF-8
            return fs.readFileSync(logPath, 'utf8');
        } catch (err) {
            console.error(`Erro ao ler log de veículos: ${err.message}`);
            return null;
        }
    }
}

// Função para extrair informações de veículos do log
function parseVehicleLog(content, lastTimestamp) {
    const vehicles = [];
    const lines = content.split(/\r?\n/);
    
    lines.forEach(line => {
        const trimmedLine = line.trim();
        if (!trimmedLine) return;
        
        // Pular linha de versão do jogo
        if (trimmedLine.includes('Game version:')) return;
        
        // Regex para capturar eventos de veículos (incluindo casos com Owner: N/A)
        // Formato: timestamp: [EventType] VehicleType. VehicleId: id. Owner: steamId (playerId, playerName) ou N/A. Location: X=x Y=y Z=z
        const vehicleMatch = trimmedLine.match(/^([0-9.:-]+): \[([^\]]+)\] ([^.]+)\. VehicleId: ([^.]+)\. Owner: ([^.]*)\. Location: X=([\-\d.]+) Y=([\-\d.]+) Z=([\-\d.]+)$/);
        
        if (vehicleMatch) {
            const timestamp = vehicleMatch[1];
            // Só incluir se for mais recente que o último processado
            if (!lastTimestamp || timestamp > lastTimestamp) {
                const ownerInfo = vehicleMatch[5];
                let ownerSteamId = null;
                let ownerPlayerId = null;
                let ownerName = null;
                
                // Processar informações do owner
                if (ownerInfo !== 'N/A') {
                    // Formato: steamId (playerId, playerName)
                    const ownerMatch = ownerInfo.match(/^([0-9]+) \(([^,]+), ([^)]+)\)$/);
                    if (ownerMatch) {
                        ownerSteamId = ownerMatch[1];
                        ownerPlayerId = ownerMatch[2];
                        ownerName = ownerMatch[3];
                    }
                } else {
                    ownerSteamId = 'N/A';
                    ownerPlayerId = 'N/A';
                    ownerName = 'Sem Proprietário';
                }
                
                vehicles.push({
                    timestamp: timestamp,
                    event: vehicleMatch[2], // Destroyed, Disappeared, VehicleInactiveTimerReached
                    vehicleType: vehicleMatch[3],
                    vehicleId: vehicleMatch[4],
                    ownerSteamId: ownerSteamId,
                    ownerPlayerId: ownerPlayerId,
                    ownerName: ownerName,
                    location: {
                        x: parseFloat(vehicleMatch[6]),
                        y: parseFloat(vehicleMatch[7]),
                        z: parseFloat(vehicleMatch[8])
                    }
                });
            }
        } else {
            // Log para debug - linhas que não bateram no regex
            logger.debug('Linha não reconhecida', { line: trimmedLine });
        }
    });
    
    return vehicles;
}

// Função para atualizar banco de dados de veículos
function updateVehiclesDatabase(newVehicles) {
    let vehiclesDb = [];
    
    // Carregar banco existente
    if (fs.existsSync(VEHICLES_DB_PATH)) {
        try {
            vehiclesDb = JSON.parse(fs.readFileSync(VEHICLES_DB_PATH, 'utf8'));
        } catch (error) {
            logger.error('Erro ao carregar banco de veículos', { error: error.message });
        }
    }
    
    // Adicionar novos eventos
    newVehicles.forEach(vehicle => {
        vehiclesDb.push({
            ...vehicle,
            processedAt: new Date().toISOString()
        });
    });
    
    // Salvar banco atualizado
    try {
        fs.writeFileSync(VEHICLES_DB_PATH, JSON.stringify(vehiclesDb, null, 2), 'utf8');
        return vehiclesDb;
    } catch (error) {
        logger.error('Erro ao salvar banco de veículos', { error: error.message });
        return null;
    }
}

// Função para ler webhooks
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

// Função para mapear tipos de evento para emojis
function getVehicleEventEmoji(event) {
    const emojiMap = {
        'Destroyed': '💥',
        'Disappeared': '👻',
        'VehicleInactiveTimerReached': '⏰'
    };
    return emojiMap[event] || `(${event})`;
}

// Função para traduzir tipos de evento
function translateVehicleEvent(event) {
    const translations = {
        'Destroyed': 'Destruído',
        'Disappeared': 'Desaparecido',
        'VehicleInactiveTimerReached': 'Timer de Inatividade'
    };
    return translations[event] || event;
}

// Função para obter cor do embed baseada no tipo de evento
function getVehicleEventColor(event) {
    switch (event) {
        case 'Destroyed':
            return 0xff0000; // Vermelho
        case 'Disappeared':
            return 0xffa500; // Laranja
        case 'VehicleInactiveTimerReached':
            return 0xffff00; // Amarelo
        default:
            return 0x808080; // Cinza
    }
}

// Função para enviar webhook de veículos
async function sendVehicleWebhook(newVehicles) {
    
    logger.vehicles(`Processando ${newVehicles.length} novos veículos`);
    
    if (newVehicles.length === 0) {
        logger.vehicles('Nenhum veículo para enviar');
        return;
    }
    
    const webhooks = readWebhooks();
    const webhookUrl = webhooks.LogVeiculos;
    
    if (!webhookUrl) {
        logger.vehicles('Webhook LogVeiculos não configurado');
        return;
    }
    
    try {
        // Enviar apenas o último veículo (mais recente)
        const lastVehicle = newVehicles[newVehicles.length - 1];
        const eventEmoji = getVehicleEventEmoji(lastVehicle.event);
        const translatedEvent = translateVehicleEvent(lastVehicle.event);
        
        // Criar embed do Discord
        const ownerDisplay = lastVehicle.ownerName || 'Sem Proprietário';
        const embed = {
            title: `${eventEmoji} ${lastVehicle.vehicleType} - ${ownerDisplay} (${translatedEvent})`,
            description: `📍 **Localização:** X:${lastVehicle.location.x} Y:${lastVehicle.location.y} Z:${lastVehicle.location.z}\n🆔 **VehicleId:** ${lastVehicle.vehicleId}`,
            color: getVehicleEventColor(lastVehicle.event),
            timestamp: new Date().toISOString(),
            footer: {
                text: "SCUM Server Manager - Eventos de Veículos"
            }
        };
        
        const discordMessage = {
            embeds: [embed]
        };
        
        logger.vehicles('Enviando webhook para Discord...');
        
        try {
            const response = await makeRequest({
                url: webhookUrl,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                data: discordMessage
            });
            logger.vehicles(`Webhook enviado com sucesso! Último evento: ${lastVehicle.vehicleType} - ${lastVehicle.event}`, { status: response.status });
        } catch (axiosError) {
            logger.error('Erro do Axios ao enviar webhook de veículos', { 
                error: axiosError.message,
                status: axiosError.response?.status,
                data: axiosError.response?.data
            });
            throw axiosError;
        }
    } catch (error) {
        logger.error('Erro geral ao enviar webhook de veículos', { error: error.message });
    }
}

// Função para enviar histórico de veículos para Discord
async function sendVehicleHistoryWebhook(vehicles, limit = 10) {
    const webhooks = readWebhooks();
    const webhookUrl = webhooks.LogVeiculos;
    
    if (!webhookUrl) {
        logger.vehicles('Webhook LogVeiculos não configurado');
        return false;
    }
    
    if (vehicles.length === 0) {
        logger.vehicles('Nenhum veículo para enviar');
        return false;
    }
    
    try {
        // Limitar quantidade para não sobrecarregar o Discord
        const vehiclesToSend = vehicles.slice(0, limit);
        
        // Criar embed do Discord
        const embed = {
            title: "🚗 Histórico de Veículos - SCUM Server",
            color: 0x00ff00, // Verde
            description: `**${vehicles.length}** eventos encontrados no histórico`,
            fields: [],
            timestamp: new Date().toISOString(),
            footer: {
                text: "SCUM Server Manager - Histórico de Veículos"
            }
        };
        
        // Agrupar por tipo de evento para estatísticas
        const eventStats = {};
        vehicles.forEach(vehicle => {
            eventStats[vehicle.event] = (eventStats[vehicle.event] || 0) + 1;
        });
        
        // Adicionar estatísticas
        const statsText = Object.entries(eventStats)
            .map(([event, count]) => `${getVehicleEventEmoji(event)} **${event}:** ${count}`)
            .join('\n');
        
        embed.fields.push({
            name: "📊 Estatísticas por Tipo",
            value: statsText,
            inline: true
        });
        
        // Adicionar top proprietários
        const ownerStats = {};
        vehicles.forEach(vehicle => {
            if (!ownerStats[vehicle.ownerSteamId]) {
                ownerStats[vehicle.ownerSteamId] = {
                    name: vehicle.ownerName,
                    count: 0
                };
            }
            ownerStats[vehicle.ownerSteamId].count++;
        });
        
        const topOwners = Object.entries(ownerStats)
            .sort((a, b) => b[1].count - a[1].count)
            .slice(0, 5)
            .map(([steamId, data]) => `👤 **${data.name}:** ${data.count}`)
            .join('\n');
        
        embed.fields.push({
            name: "🏆 Top Proprietários",
            value: topOwners || "Nenhum proprietário encontrado",
            inline: true
        });
        
        // Adicionar últimos eventos
        const recentEvents = vehiclesToSend
            .map(vehicle => {
                const eventEmoji = getVehicleEventEmoji(vehicle.event);
                return `${eventEmoji} **${vehicle.vehicleType}** - ${vehicle.ownerName} (${vehicle.event})`;
            })
            .join('\n');
        
        embed.fields.push({
            name: `🕐 Últimos ${vehiclesToSend.length} Eventos`,
            value: recentEvents || "Nenhum evento recente",
            inline: false
        });
        
        const discordMessage = {
            embeds: [embed]
        };
        
        await makeRequest({
            url: webhookUrl,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            data: discordMessage
        });
        
        logger.vehicles(`Webhook de histórico enviado com sucesso! ${vehicles.length} eventos processados.`);
        return true;
        
    } catch (error) {
        logger.error('Erro ao enviar webhook de histórico', { error: error.message });
        return false;
    }
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
router.get('/LogVeiculos', async (req, res) => {
    let tempPath = null;
    try {
        // 1. Criar diretórios necessários
        createDirectories();
        // 2. Encontrar o último log de veículos
        const latestLog = getLatestVehicleLog();
        if (!latestLog) {
            return res.json({
                success: false,
                message: 'Nenhum arquivo de log de veículos encontrado',
                data: []
            });
        }
        // 3. Copiar para pasta temporária
        tempPath = copyVehicleLogToTemp(latestLog);
        if (!tempPath) {
            return res.status(500).json({
                success: false,
                message: 'Erro ao copiar log para pasta temporária',
                data: []
            });
        }
        // 4. Ler conteúdo
        const logContent = readVehicleLogContent(tempPath);
        if (!logContent) {
            return res.status(500).json({
                success: false,
                message: 'Erro ao ler conteúdo do log',
                data: []
            });
        }
        // 5. Ler último timestamp processado
        const lastTimestamp = getLastVehicleTimestamp();
        // 6. Extrair informações de veículos (apenas novos)
        const newVehicles = parseVehicleLog(logContent, lastTimestamp);
        // 7. Atualizar banco de dados
        if (newVehicles.length > 0) {
            const vehiclesDb = updateVehiclesDatabase(newVehicles);
            if (!vehiclesDb) {
                return res.status(500).json({
                    success: false,
                    message: 'Erro ao atualizar banco de dados',
                    data: []
                });
            }
            // 8. Enviar webhook (síncrono para debug)
            logger.vehicles('Iniciando webhook automático...');
            try {
                await sendVehicleWebhook(newVehicles);
                logger.vehicles('Webhook automático concluído');
            } catch (e) {
                logger.error('Erro no webhook automático', { error: e.message });
            }
            // 9. Atualizar controle de timestamp
            setLastVehicleTimestamp(newVehicles[newVehicles.length - 1].timestamp);
        }
        // 10. Deletar arquivo temporário
        if (fs.existsSync(tempPath)) {
            fs.unlinkSync(tempPath);
        }
        // 11. Responder em UTF-8
        res.set('Content-Type', 'application/json; charset=utf-8');
        res.json({
            success: true,
            message: `Log de veículos processado com sucesso. ${newVehicles.length} novos eventos encontrados.`,
            data: newVehicles
        });
    } catch (error) {
        logger.error('Erro no endpoint LogVeiculos', { error: error.message });
        res.status(500).json({
            success: false,
            message: 'Erro interno do servidor',
            error: error.message,
            data: []
        });
    }
});

// Endpoint para obter histórico de veículos
router.get('/vehicles/history', (req, res) => {
    try {
        if (!fs.existsSync(VEHICLES_DB_PATH)) {
            return res.json({
                success: true,
                message: 'Nenhum histórico de veículos encontrado',
                data: []
            });
        }
        
        const vehiclesDb = JSON.parse(fs.readFileSync(VEHICLES_DB_PATH, 'utf8'));
        
        res.json({
            success: true,
            message: 'Histórico de veículos recuperado com sucesso',
            data: vehiclesDb
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Erro ao ler histórico de veículos',
            error: error.message
        });
    }
});

// Endpoint para obter veículos por proprietário
router.get('/vehicles/owner/:steamId', (req, res) => {
    try {
        const { steamId } = req.params;
        
        if (!fs.existsSync(VEHICLES_DB_PATH)) {
            return res.json({
                success: true,
                message: 'Nenhum histórico de veículos encontrado',
                data: []
            });
        }
        
        const vehiclesDb = JSON.parse(fs.readFileSync(VEHICLES_DB_PATH, 'utf8'));
        const ownerVehicles = vehiclesDb.filter(vehicle => vehicle.ownerSteamId === steamId);
        
        res.json({
            success: true,
            message: `Veículos do proprietário ${steamId} recuperados com sucesso`,
            data: ownerVehicles
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Erro ao buscar veículos do proprietário',
            error: error.message
        });
    }
});

// Endpoint para enviar histórico para Discord
router.post('/vehicles/send-history', async (req, res) => {
    try {
        const { limit = 10 } = req.body;
        
        // Verificar se existe histórico
        if (!fs.existsSync(VEHICLES_DB_PATH)) {
            return res.json({
                success: false,
                message: 'Nenhum histórico de veículos encontrado',
                data: null
            });
        }
        
        const vehiclesDb = JSON.parse(fs.readFileSync(VEHICLES_DB_PATH, 'utf8'));
        
        if (vehiclesDb.length === 0) {
            return res.json({
                success: false,
                message: 'Nenhum evento de veículo encontrado no histórico',
                data: null
            });
        }
        
        // Enviar para Discord
        const webhookSuccess = await sendVehicleHistoryWebhook(vehiclesDb, limit);
        
        if (webhookSuccess) {
            res.json({
                success: true,
                message: `Histórico de ${vehiclesDb.length} veículos enviado para o Discord com sucesso`,
                data: {
                    totalEvents: vehiclesDb.length,
                    sentToDiscord: true
                }
            });
        } else {
            res.json({
                success: false,
                message: 'Erro ao enviar para Discord ou webhook não configurado',
                data: {
                    totalEvents: vehiclesDb.length,
                    sentToDiscord: false
                }
            });
        }
        
    } catch (error) {
        console.error('Erro no endpoint send-history:', error);
        res.status(500).json({
            success: false,
            message: 'Erro interno do servidor',
            error: error.message
        });
    }
});

// Endpoint para obter estatísticas de veículos
router.get('/vehicles/stats', (req, res) => {
    try {
        if (!fs.existsSync(VEHICLES_DB_PATH)) {
            return res.json({
                success: true,
                message: 'Nenhum histórico de veículos encontrado',
                data: {
                    totalEvents: 0,
                    eventsByType: {},
                    topOwners: [],
                    topVehicleTypes: []
                }
            });
        }
        
        const vehiclesDb = JSON.parse(fs.readFileSync(VEHICLES_DB_PATH, 'utf8'));
        
        // Estatísticas por tipo de evento
        const eventsByType = {};
        const owners = {};
        const vehicleTypes = {};
        
        vehiclesDb.forEach(vehicle => {
            // Contar por tipo de evento
            eventsByType[vehicle.event] = (eventsByType[vehicle.event] || 0) + 1;
            
            // Contar por proprietário
            if (!owners[vehicle.ownerSteamId]) {
                owners[vehicle.ownerSteamId] = {
                    steamId: vehicle.ownerSteamId,
                    name: vehicle.ownerName,
                    count: 0
                };
            }
            owners[vehicle.ownerSteamId].count++;
            
            // Contar por tipo de veículo
            vehicleTypes[vehicle.vehicleType] = (vehicleTypes[vehicle.vehicleType] || 0) + 1;
        });
        
        // Top proprietários
        const topOwners = Object.values(owners)
            .sort((a, b) => b.count - a.count)
            .slice(0, 10);
        
        // Top tipos de veículo
        const topVehicleTypes = Object.entries(vehicleTypes)
            .map(([type, count]) => ({ type, count }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 10);
        
        res.json({
            success: true,
            message: 'Estatísticas de veículos recuperadas com sucesso',
            data: {
                totalEvents: vehiclesDb.length,
                eventsByType,
                topOwners,
                topVehicleTypes
            }
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Erro ao gerar estatísticas de veículos',
            error: error.message
        });
    }
});

// Endpoint para forçar webhook de veículos
router.get('/force-webhook', async (req, res) => {
    try {
        const webhooks = readWebhooks();
        const webhookUrl = webhooks.LogVeiculos;
        
        if (!webhookUrl) {
            return res.json({
                success: false,
                message: 'Webhook LogVeiculos não configurado'
            });
        }
        
        const testVehicle = {
            event: 'Destroyed',
            vehicleType: 'Tractor_ES',
            vehicleId: 'TEST123',
            ownerName: 'TestPlayer',
            location: {
                x: -182026.109,
                y: 77498.016,
                z: 67358.133
            }
        };
        
        const eventEmoji = getVehicleEventEmoji(testVehicle.event);
        const translatedEvent = translateVehicleEvent(testVehicle.event);
        
        const embed = {
            title: `${eventEmoji} ${testVehicle.vehicleType} - ${testVehicle.ownerName} (${translatedEvent}) - TESTE`,
            description: `📍 **Localização:** X:${testVehicle.location.x} Y:${testVehicle.location.y} Z:${testVehicle.location.z}\n🆔 **VehicleId:** ${testVehicle.vehicleId}`,
            color: getVehicleEventColor(testVehicle.event),
            timestamp: new Date().toISOString(),
            footer: {
                text: "SCUM Server Manager - Eventos de Veículos - TESTE FORÇADO"
            }
        };
        
        const discordMessage = {
            embeds: [embed]
        };
        
        await makeRequest({
            url: webhookUrl,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            data: discordMessage
        });
        
        res.json({
            success: true,
            message: 'Webhook de veículos forçado enviado com sucesso',
            status: 200 // Assuming a successful response from makeRequest
        });
        
    } catch (error) {
        console.error('Erro ao forçar webhook de veículos:', error);
        res.status(500).json({
            success: false,
            message: 'Erro ao forçar webhook de veículos',
            error: error.message
        });
    }
});

module.exports = router; 