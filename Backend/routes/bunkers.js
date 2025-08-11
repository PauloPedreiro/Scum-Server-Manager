const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const glob = require('glob');
const http = require('http');
const https = require('https');
const url = require('url');
const logger = require('../src/logger');

const SCUM_LOG_PATH = process.env.SCUM_LOG_PATH || 'C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\Logs';
const TEMP_PATH = 'src/data/temp';
const WEBHOOKS_PATH = path.join('src/data/webhooks.json');
const BUNKERS_DB_PATH = 'src/data/bunkers/bunkers.json';
const LAST_PROCESSED_PATH = 'src/data/bunkers/lastProcessed.json';

// Função para criar diretórios necessários
function createDirectories() {
    const dirs = [TEMP_PATH, 'src/data/bunkers'];
    dirs.forEach(dir => {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    });
}

// Função para encontrar o arquivo de log mais recente
function findLatestGameplayLog() {
    const logPattern = `${SCUM_LOG_PATH}/gameplay_*.log`;
    const files = glob.sync(logPattern);
    if (files.length === 0) {
        return null;
    }
    files.sort((a, b) => {
        const statA = fs.statSync(a);
        const statB = fs.statSync(b);
        return statB.mtime.getTime() - statA.mtime.getTime();
    });
    return path.basename(files[0]);
}

// Função para copiar log de gameplay para temp
function copyGameplayLogToTemp(logFileName) {
    const sourcePath = path.join(SCUM_LOG_PATH, logFileName);
    const tempPath = path.join(TEMP_PATH, logFileName);
    try {
        fs.copyFileSync(sourcePath, tempPath);
        return tempPath;
    } catch (error) {
        console.error(`Erro ao copiar log de gameplay: ${error.message}`);
        return null;
    }
}

// Função para ler conteúdo do log com fallback de encoding
function readLogFileWithEncoding(filePath) {
    let content = '';
    try {
        // Tentar UTF-16LE primeiro (padrão do SCUM)
        content = fs.readFileSync(filePath, 'utf16le');
        // Remover caracteres nulos intercalados
        content = content.replace(/\u0000/g, '');
    } catch (e) {
        try {
            content = fs.readFileSync(filePath, 'utf8');
        } catch (err) {
            console.error('Erro ao ler log:', err.message);
            content = '';
        }
    }
    return content;
}

// Função para carregar banco de dados de bunkers
function loadBunkersDatabase() {
    if (fs.existsSync(BUNKERS_DB_PATH)) {
        try {
            return JSON.parse(fs.readFileSync(BUNKERS_DB_PATH, 'utf8'));
        } catch (error) {
            console.error('Erro ao carregar banco de bunkers:', error.message);
        }
    }
    return {};
}

// Função para salvar banco de dados de bunkers
function saveBunkersDatabase(bunkersDb) {
    try {
        fs.writeFileSync(BUNKERS_DB_PATH, JSON.stringify(bunkersDb, null, 2), 'utf8');
        return true;
    } catch (error) {
        console.error('Erro ao salvar banco de bunkers:', error.message);
        return false;
    }
}

// Função para gerar hash dos dados de bunkers
function generateBunkersDataHash(bunkersData) {
    // Ordenar bunkers por nome para garantir consistência
    const activeSorted = bunkersData.active.sort((a, b) => a.name.localeCompare(b.name));
    const lockedSorted = bunkersData.locked.sort((a, b) => a.name.localeCompare(b.name));
    
    // Criar string com dados essenciais
    const activeString = activeSorted.map(bunker => `${bunker.name}:${bunker.status}:${bunker.activated || ''}`).join('|');
    const lockedString = lockedSorted.map(bunker => `${bunker.name}:${bunker.status}:${bunker.nextActivation || ''}`).join('|');
    
    return `${activeString}||${lockedString}`;
}

// Função para verificar se arquivo já foi processado
function isFileAlreadyProcessed(fileName, fileMTimeMs, currentDataHash) {
    if (fs.existsSync(LAST_PROCESSED_PATH)) {
        try {
            const lastProcessed = JSON.parse(fs.readFileSync(LAST_PROCESSED_PATH, 'utf8'));
            return lastProcessed.fileName === fileName && 
                   lastProcessed.fileMTimeMs === fileMTimeMs && 
                   lastProcessed.dataHash === currentDataHash;
        } catch (error) {
            console.error('Erro ao verificar arquivo processado:', error.message);
        }
    }
    return false;
}

// Função para marcar arquivo como processado
function markFileAsProcessed(fileName, fileMTimeMs, dataHash) {
    const data = {
        fileName: fileName,
        fileMTimeMs: fileMTimeMs,
        dataHash: dataHash,
        processedAt: new Date().toISOString()
    };
    
    try {
        fs.writeFileSync(LAST_PROCESSED_PATH, JSON.stringify(data, null, 2), 'utf8');
    } catch (error) {
        console.error('Erro ao marcar arquivo como processado:', error.message);
    }
}

// Função para calcular tempo decorrido
function calculateTimeElapsed(timestamp) {
    if (!timestamp) return null;
    
    const now = new Date();
    const logTime = new Date(timestamp.replace(/(\d{4})\.(\d{2})\.(\d{2})-(\d{2})\.(\d{2})\.(\d{2})/, '$1-$2-$3T$4:$5:$6.000Z'));
    const diffMs = now.getTime() - logTime.getTime();
    
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
    
    return `${hours.toString().padStart(2, '0')}h ${minutes.toString().padStart(2, '0')}m ${seconds.toString().padStart(2, '0')}s`;
}

// Função para extrair informações dos bunkers do log
function extractBunkerInfo(logContent) {
    const bunkersDb = loadBunkersDatabase();
    const lines = logContent.split(/\r?\n/);
    let lastUpdate = null;
    
    for (const lineRaw of lines) {
        const line = lineRaw.replace(/\u0000/g, '').trim();
        if (line.includes('[LogBunkerLock]')) {
            // Capturar timestamp da linha
            const timestampMatch = line.match(/^(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):/);
            if (timestampMatch) {
                lastUpdate = timestampMatch[1];
            }
            
            // Bunker ativo completo com coordenadas
            const activeMatch = line.match(/([A-Z]\d+)\s+Bunker\s+is\s+Active\.?\s+Activated\s+(\d{2}h\s+\d{2}m\s+\d{2}s)\s+ago\.?\s+X=([\-\d.]+)\s+Y=([\-\d.]+)\s+Z=([\-\d.]+)/i);
            if (activeMatch) {
                const name = activeMatch[1];
                const activated = activeMatch[2];
                const coordinates = {
                    x: parseFloat(activeMatch[3]),
                    y: parseFloat(activeMatch[4]),
                    z: parseFloat(activeMatch[5])
                };
                
                bunkersDb[name] = {
                    name,
                    status: 'active',
                    activated,
                    coordinates,
                    lastUpdate,
                    activationTime: lastUpdate
                };
            }
            
            // Bunker bloqueado
            const lockedMatch = line.match(/([A-Z]\d+)\s+Bunker\s+is\s+Locked\.?\s+Locked\s+initially,\s+next\s+Activation\s+in\s+(\d{2}h\s+\d{2}m\s+\d{2}s)\.?\s+X=([\-\d.]+)\s+Y=([\-\d.]+)\s+Z=([\-\d.]+)/i);
            if (lockedMatch) {
                const name = lockedMatch[1];
                const nextActivation = lockedMatch[2];
                const coordinates = {
                    x: parseFloat(lockedMatch[3]),
                    y: parseFloat(lockedMatch[4]),
                    z: parseFloat(lockedMatch[5])
                };
                
                bunkersDb[name] = {
                    name,
                    status: 'locked',
                    nextActivation,
                    coordinates,
                    lastUpdate
                };
            }
            
            // Bunker ativado simples (sem coordenadas)
            const activatedMatch = line.match(/([A-Z]\d+)\s+Bunker\s+Activated\s+(\d{2}h\s+\d{2}m\s+\d{2}s)\s+ago\.?/i);
            if (activatedMatch) {
                const name = activatedMatch[1];
                const activated = activatedMatch[2];
                
                // Só atualiza se não houver registro ou se o registro atual não tem coordenadas
                if (!bunkersDb[name] || !bunkersDb[name].coordinates) {
                    bunkersDb[name] = {
                        name,
                        status: 'active',
                        activated,
                        coordinates: null,
                        lastUpdate,
                        activationTime: lastUpdate
                    };
                }
            }
            
            // Bunker ativado via keycard
            const keycardMatch = line.match(/([A-Z]\d+)\s+Bunker\s+Activated\s+via\s+Keycard\s+(\d{2}h\s+\d{2}m\s+\d{2}s)\s+ago\.?/i);
            if (keycardMatch) {
                const name = keycardMatch[1];
                const activated = keycardMatch[2];
                
                bunkersDb[name] = {
                    name,
                    status: 'active',
                    activated,
                    activationMethod: 'keycard',
                    coordinates: null,
                    lastUpdate,
                    activationTime: lastUpdate
                };
            }
        }
    }
    
    // Salvar banco atualizado
    saveBunkersDatabase(bunkersDb);
    
    // Separar bunkers ativos e bloqueados
    const active = [];
    const locked = [];
    
    Object.values(bunkersDb).forEach(bunker => {
        if (bunker.status === 'active') {
            active.push(bunker);
        } else if (bunker.status === 'locked') {
            locked.push(bunker);
        }
    });
    
    return {
        active,
        locked,
        lastUpdate
    };
}

// Função para formatar informações detalhadas dos bunkers
function formatBunkerDetails(bunkerInfo) {
    let details = '';
    
    // Bunkers Ativos
    details += '**Bunkers Ativos:**\n';
    if (bunkerInfo.active.length === 0) {
        details += 'Nenhum bunker ativo no momento.\n\n';
    } else {
        bunkerInfo.active.forEach(bunker => {
            details += `${bunker.name} Bunker\n`;
            details += `Status: Ativo\n`;
            
            if (bunker.activationMethod === 'keycard') {
                details += `Ativado: Via Keycard ${bunker.activated} atrás\n`;
            } else {
                details += `Ativado: ${bunker.activated} atrás`;
                if (bunker.activationTime) {
                    const timeElapsed = calculateTimeElapsed(bunker.activationTime);
                    if (timeElapsed) {
                        details += ` (${timeElapsed} decorridos)`;
                    }
                }
                details += '\n';
            }
            
            if (bunker.coordinates) {
                details += `Coordenadas: X=${bunker.coordinates.x} Y=${bunker.coordinates.y} Z=${bunker.coordinates.z}\n`;
            } else {
                details += `Coordenadas: Não especificadas no log\n`;
            }
            details += '\n';
        });
    }
    
    // Bunkers Bloqueados
    details += '**Bunkers Bloqueados:**\n';
    if (bunkerInfo.locked.length === 0) {
        details += 'Nenhum bunker bloqueado no momento.\n';
    } else {
        bunkerInfo.locked.forEach(bunker => {
            details += `${bunker.name} Bunker\n`;
            details += `Status: Bloqueado\n`;
            details += `Próxima ativação: ${bunker.nextActivation}`;
            
            if (bunker.lastUpdate) {
                const timeElapsed = calculateTimeElapsed(bunker.lastUpdate);
                if (timeElapsed) {
                    details += ` (atualizado há ${timeElapsed})`;
                }
            }
            details += '\n';
            
            if (bunker.coordinates) {
                details += `Coordenadas: X=${bunker.coordinates.x} Y=${bunker.coordinates.y} Z=${bunker.coordinates.z}\n`;
            }
            details += '\n';
        });
    }
    
    return details;
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

// Função para enviar webhook de bunkers para Discord
async function sendBunkersWebhook(bunkerInfo) {

            logger.bunkers('Dados dos bunkers processados', { active: bunkerInfo.active.length, locked: bunkerInfo.locked.length });
    
    const webhooks = readWebhooks();
    const webhookUrl = webhooks.bunkers;
    
            if (!webhookUrl) {
            logger.bunkers('Webhook bunkers não configurado');
            return;
        }
    
    try {
        // Formatar detalhes dos bunkers
        const bunkerDetails = formatBunkerDetails(bunkerInfo);
        
        const embed = {
            title: "🏰 Status dos Bunkers - SCUM Server",
            color: 0x00ff00, // Verde
            description: bunkerDetails,
            timestamp: new Date().toISOString(),
            footer: {
                text: "SCUM Server Manager - Status dos Bunkers"
            }
        };
        
        const discordMessage = {
            embeds: [embed]
        };
        
        logger.bunkers('Enviando webhook para Discord...');
        
        try {
            const response = await makeRequest({
                url: webhookUrl,
                method: 'POST',
                data: discordMessage,
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            logger.bunkers(`Webhook enviado com sucesso! ${bunkerInfo.active.length} ativos, ${bunkerInfo.locked.length} bloqueados`, { status: response.status });
        } catch (axiosError) {
            logger.error('Erro do Axios ao enviar webhook de bunkers', { 
                error: axiosError.message,
                status: axiosError.response?.status,
                data: axiosError.response?.data
            });
            throw axiosError;
        }
    } catch (error) {
        logger.error('Erro geral ao enviar webhook de bunkers', { error: error.message });
    }
}

// Endpoint para obter status dos bunkers
router.get('/status', async (req, res) => {
    let tempPath = null;
    try {
        createDirectories();
        const latestLogFile = findLatestGameplayLog();
        if (!latestLogFile) {
            return res.status(404).json({
                success: false,
                message: 'Nenhum arquivo de log gameplay encontrado.',
                data: {
                    active: [],
                    locked: [],
                    lastUpdate: null
                }
            });
        }
        
        // Verificar se arquivo já foi processado
        const logFilePath = path.join(SCUM_LOG_PATH, latestLogFile);
        const fileMTimeMs = fs.statSync(logFilePath).mtime.getTime();
        
        tempPath = copyGameplayLogToTemp(latestLogFile);
        if (!tempPath) {
            return res.status(500).json({
                success: false,
                message: 'Erro ao copiar log para pasta temporária.',
                data: {
                    active: [],
                    locked: [],
                    lastUpdate: null
                }
            });
        }
        
        const logContent = readLogFileWithEncoding(tempPath);
        const bunkerInfo = extractBunkerInfo(logContent);
        
        // Gerar hash dos dados de bunkers
        const currentDataHash = generateBunkersDataHash(bunkerInfo);
        
        if (isFileAlreadyProcessed(latestLogFile, fileMTimeMs, currentDataHash)) {
            // Retornar dados do banco mesmo quando arquivo já foi processado
            const bunkersDb = loadBunkersDatabase();
            const active = Object.values(bunkersDb).filter(b => b.status === 'active');
            const locked = Object.values(bunkersDb).filter(b => b.status === 'locked');
            
            // Limpar arquivo temporário
            if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath);
            
            return res.json({
                success: true,
                message: 'Arquivo já processado - dados atuais',
                data: {
                    active,
                    locked,
                    lastUpdate: active.length > 0 || locked.length > 0 ? 
                        Math.max(...[...active, ...locked].map(b => b.lastUpdate).filter(Boolean)) : null
                }
            });
        }
        
        // Marcar arquivo como processado
        markFileAsProcessed(latestLogFile, fileMTimeMs, currentDataHash);
        
        await sendBunkersWebhook(bunkerInfo);
        
        // Limpar arquivo temporário APÓS todo o processamento
        if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath);
        
        res.json({
            success: true,
            message: 'Status dos bunkers recuperado com sucesso.',
            data: bunkerInfo,
            logFile: latestLogFile
        });
    } catch (error) {
        console.error('Erro ao ler status dos bunkers:', error);
        res.status(500).json({
            success: false,
            message: 'Erro interno do servidor.',
            error: error.message,
            data: {
                active: [],
                locked: [],
                lastUpdate: null
            }
        });
    } finally {
        // Garantir que o arquivo temporário seja sempre limpo
        if (tempPath && fs.existsSync(tempPath)) {
            try {
                fs.unlinkSync(tempPath);
                logger.bunkers('Arquivo temporário limpo com sucesso');
            } catch (cleanupError) {
                console.error('❌ Erro ao limpar arquivo temporário:', cleanupError.message);
            }
        }
    }
});

// Endpoint para forçar atualização dos bunkers
router.post('/force-update', async (req, res) => {
    let tempPath = null;
    try {
        createDirectories();
        const latestLogFile = findLatestGameplayLog();
        if (!latestLogFile) {
            return res.status(404).json({
                success: false,
                message: 'Nenhum arquivo de log gameplay encontrado.'
            });
        }
        tempPath = copyGameplayLogToTemp(latestLogFile);
        if (!tempPath) {
            return res.status(500).json({
                success: false,
                message: 'Erro ao copiar log para pasta temporária.'
            });
        }
        const logContent = readLogFileWithEncoding(tempPath);
        const bunkerInfo = extractBunkerInfo(logContent);
        if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath);
        
        // Gerar hash dos dados de bunkers
        const currentDataHash = generateBunkersDataHash(bunkerInfo);
        
        // Verificar se houve alterações
        const logFilePath = path.join(SCUM_LOG_PATH, latestLogFile);
        const fileMTimeMs = fs.statSync(logFilePath).mtime.getTime();
        
        if (!isFileAlreadyProcessed(latestLogFile, fileMTimeMs, currentDataHash)) {
            // Marcar arquivo como processado
            markFileAsProcessed(latestLogFile, fileMTimeMs, currentDataHash);
            
            // Enviar webhook apenas se houve alterações
            await sendBunkersWebhook(bunkerInfo);
        }
        
        res.json({
            success: true,
            message: 'Status dos bunkers atualizado.',
            data: bunkerInfo
        });
    } catch (error) {
        console.error('Erro ao forçar atualização dos bunkers:', error);
        res.status(500).json({
            success: false,
            message: 'Erro interno do servidor.',
            error: error.message
        });
    } finally {
        // Garantir que o arquivo temporário seja sempre limpo
        if (tempPath && fs.existsSync(tempPath)) {
            try {
                fs.unlinkSync(tempPath);
                logger.bunkers('Arquivo temporário limpo com sucesso (force-update)');
            } catch (cleanupError) {
                console.error('❌ Erro ao limpar arquivo temporário:', cleanupError.message);
            }
        }
    }
});

module.exports = router; 