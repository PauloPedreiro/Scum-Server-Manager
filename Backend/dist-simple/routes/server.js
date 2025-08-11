const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { spawn, exec } = require('child_process');
const http = require('http');
const https = require('https');
const url = require('url');
const { DateTime } = require('luxon');
const logger = require('../src/logger');

// Configurações
const CONFIG_PATH = 'src/data/server/config.json';
const STATUS_PATH = 'src/data/server/status.json';
const WEBHOOKS_PATH = path.join('src/data/webhooks.json');
const SCHEDULE_PATH = 'src/data/server/scheduled-restarts.json';

// Criar diretórios necessários
const createDirectories = () => {
    const dirs = [
        'src/data/server',
        'src/data/temp'
    ];
    
    dirs.forEach(dir => {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    });
};

// Função para carregar configurações
const loadConfig = () => {
    try {
        if (!fs.existsSync(CONFIG_PATH)) {
            throw new Error('Arquivo de configuração não encontrado');
        }
        return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
    } catch (error) {
        logger.error('Erro ao carregar configurações', { error: error.message });
        return null;
    }
};

// Função para salvar configurações
const saveConfig = (config) => {
    try {
        fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf8');
        return true;
    } catch (error) {
        logger.error('Erro ao salvar configurações', { error: error.message });
        return false;
    }
};

// Função para carregar status
const loadStatus = () => {
    try {
        if (!fs.existsSync(STATUS_PATH)) {
            return {
                isRunning: false,
                pid: null,
                startTime: null,
                lastCheck: null,
                uptime: 0,
                restartCount: 0,
                lastError: null,
                version: null
            };
        }
        return JSON.parse(fs.readFileSync(STATUS_PATH, 'utf8'));
    } catch (error) {
        logger.error('Erro ao carregar status', { error: error.message });
        return {
            isRunning: false,
            pid: null,
            startTime: null,
            lastCheck: null,
            uptime: 0,
            restartCount: 0,
            lastError: null,
            version: null
        };
    }
};

// Função para salvar status
const saveStatus = (status) => {
    try {
        fs.writeFileSync(STATUS_PATH, JSON.stringify(status, null, 2), 'utf8');
        return true;
    } catch (error) {
        logger.error('Erro ao salvar status', { error: error.message });
        return false;
    }
};

// Função para verificar se o processo está rodando
const checkProcessRunning = (callback) => {
    exec('tasklist /FI "IMAGENAME eq SCUMServer.exe" /FO CSV', (error, stdout) => {
        if (error) {
            logger.error('Erro ao verificar processo', { error: error.message });
            callback(false, null);
            return;
        }
        
        const lines = stdout.split('\n');
        const isRunning = lines.length > 1 && lines[1].includes('SCUMServer.exe');
        
        if (isRunning) {
            // Extrair PID se disponível
            const pidMatch = lines[1].match(/"([^"]+)","([^"]+)","([^"]+)"/);
            const pid = pidMatch ? pidMatch[2] : null;
            callback(true, pid);
        } else {
            callback(false, null);
        }
    });
};

// Função para obter nome do servidor
const getServerName = () => {
    try {
        const filePath = 'C:/Servers/scum/SCUM/Saved/Config/WindowsServer/ServerSettings.ini';
        if (!fs.existsSync(filePath)) {
            return 'Servidor Desconhecido';
        }
        
        const content = fs.readFileSync(filePath, 'utf8');
        const lines = content.split('\n');
        
        for (const line of lines) {
            if (line.trim().startsWith('scum.ServerName=')) {
                const serverName = line.split('=')[1]?.trim();
                return serverName || 'Servidor Desconhecido';
            }
        }
        
        return 'Servidor Desconhecido';
    } catch (error) {
        logger.error('Erro ao ler nome do servidor', { error: error.message });
        return 'Servidor Desconhecido';
    }
};

// Função para enviar webhook de startup do servidor SCUM
const sendStartupWebhook = async () => {
    const webhookUrl = process.env.SERVER_STARTUP_WEBHOOK;
    if (!webhookUrl) {
        logger.info('Webhook de startup não configurado');
        return;
    }
    
    try {
        const serverName = getServerName();
        const timestamp = new Date().toISOString();
        
        await makeRequest({
            url: webhookUrl,
            method: 'POST',
            data: {
                embeds: [{
                    title: '🟢 Servidor SCUM Iniciado',
                    description: `**${serverName}** está online e funcionando!`,
                    color: 0x00ff00,
                    timestamp: timestamp,
                    footer: {
                        text: 'SCUM Server Manager'
                    },
                    fields: [
                        {
                            name: '📊 Status',
                            value: '🟢 Online',
                            inline: true
                        },
                        {
                            name: '⏰ Iniciado em',
                            value: new Date().toLocaleString('pt-BR', {
                                timeZone: 'America/Sao_Paulo'
                            }),
                            inline: true
                        }
                    ]
                }]
            }
        });
        
        logger.info('Webhook de startup do servidor SCUM enviado com sucesso', { serverName });
    } catch (error) {
        logger.error('Erro ao enviar webhook de startup do servidor SCUM', { error: error.message });
    }
};

// Função para atualizar status
const updateStatus = () => {
    checkProcessRunning((isRunning, pid) => {
        const status = loadStatus();
        const now = new Date();
        const wasRunning = status.isRunning;
        
        status.isRunning = isRunning;
        status.pid = pid;
        status.lastCheck = now.toISOString();
        
        // Detectar quando o servidor SCUM inicia
        if (isRunning && !wasRunning) {
            logger.info('Servidor SCUM iniciado detectado');
            status.startTime = now.toISOString();
            status.restartCount = (status.restartCount || 0) + 1;
            
            // Enviar webhook de startup
            sendStartupWebhook();
        } else if (isRunning && status.startTime) {
            const startTime = new Date(status.startTime);
            status.uptime = now.getTime() - startTime.getTime();
        } else if (!isRunning) {
            status.uptime = 0;
            status.startTime = null;
            status.pid = null;
        }
        
        saveStatus(status);
    });
};

// Função para executar comando
const executeCommand = (command, args = [], options = {}) => {
    return new Promise((resolve, reject) => {
        logger.debug(`Executando comando: ${command} ${args.join(' ')}`);
        
        const child = spawn(command, args, {
            stdio: 'pipe',
            shell: true,
            ...options
        });
        
        let stdout = '';
        let stderr = '';
        
        child.stdout.on('data', (data) => {
            stdout += data.toString();
            logger.debug(`stdout: ${data.toString().trim()}`);
        });
        
        child.stderr.on('data', (data) => {
            stderr += data.toString();
            logger.debug(`stderr: ${data.toString().trim()}`);
        });
        
        child.on('close', (code) => {
            logger.debug(`Comando finalizado com código: ${code}`);
            
            // Considerar sucesso mesmo com código diferente de 0 se não houver erro específico
            if (code === 0 || (code !== 0 && !stderr.includes('Acesso negado') && !stderr.includes('Access denied'))) {
                resolve({ success: true, stdout, stderr, code });
            } else {
                reject({ success: false, stdout, stderr, code });
            }
        });
        
        child.on('error', (error) => {
            logger.error('Erro no comando', { error: error.message });
            reject({ success: false, error: error.message });
        });
    });
};

// Função para tentar parar processo usando PowerShell
const tryStopProcess = async (pid) => {
    logger.server('Tentando parar servidor via PowerShell');
    
    const stopPsPath = path.join('src/data/temp', 'stop-server.ps1');
    
    try {
        logger.debug(`Executando PowerShell: ${stopPsPath}`);
        
        const result = await executeCommand('powershell', [
            '-ExecutionPolicy', 'Bypass',
            '-File', stopPsPath
        ]);
        
        logger.server('PowerShell executado com sucesso');
        return result;
        
    } catch (error) {
        logger.error('Erro no PowerShell', { error: error.message });
        
        // Fallback: tentar comando direto
        try {
            logger.debug('Tentando comando direto...');
            const result = await executeCommand('powershell', [
                '-Command', 'Get-Process -Name "SCUMServer" -ErrorAction SilentlyContinue | Stop-Process -Force'
            ]);
            return result;
        } catch (fallbackError) {
            logger.error('Erro no fallback', { error: fallbackError.message });
            throw fallbackError;
        }
    }
};

// Função para enviar webhook
const sendWebhook = async (message, color = '00ff00') => {
    try {
        const webhooks = JSON.parse(fs.readFileSync(WEBHOOKS_PATH, 'utf8'));
        const serverWebhook = webhooks.serverstatus;
        
        if (!serverWebhook) {
            logger.server('Webhook serverstatus não configurado');
            return;
        }
        
        const embed = {
            title: '🖥️ Gerenciamento do Servidor SCUM',
            description: message,
            color: parseInt(color, 16),
            timestamp: new Date().toISOString(),
            footer: {
                text: 'SCUM Server Manager'
            }
        };
        
        const payload = {
            embeds: [embed]
        };
        
        try {
            await makeRequest({
                url: serverWebhook,
                method: 'POST',
                data: payload,
                headers: { 'Content-Type': 'application/json' }
            });
            logger.server('Webhook serverstatus enviado com sucesso');
        } catch (error) {
            logger.error('Erro ao enviar webhook serverstatus', { error: error.message });
        }
    } catch (error) {
        logger.error('Erro ao enviar webhook', { error: error.message });
    }
};

// Função para gerar arquivo .bat dinâmico
const generateBatFile = (config) => {
    const batContent = `@echo off
set ServerPath=${config.serverPath}
set SteamCMDPath=${config.steamCMDPath}
set InstallPath=${config.installPath}

:: Check and update SCUM server
"%SteamCMDPath%\\steamcmd.exe" +force_install_dir "%InstallPath%" +login anonymous +app_update 3792580 +quit

cd /d "%ServerPath%"
start SCUMServer.exe -log -port=${config.port}${config.maxPlayers ? ` -MaxPlayers=${config.maxPlayers}` : ''}${!config.useBattleye ? ' -nobattleye' : ''}

:: Additional startup arguments:
::
:: -port=${config.port}           : Server will run on port ${config.port}
::                        Players will connect on port ${config.port + 2} (port+2)
::
:: -MaxPlayers=${config.maxPlayers}       : Override max players set in ServerSettings.ini
::
:: -nobattleye          : Launch server without Battleye (not recommended)
`;
    
    return batContent;
};

// Funções utilitárias para horários programados
function loadSchedules() {
    if (!fs.existsSync(SCHEDULE_PATH)) {
        return {
            restartTimes: [],
            enabled: false,
            lastRestart: null,
            nextRestart: null,
            lastNotification: null
        };
    }
    
    const schedules = JSON.parse(fs.readFileSync(SCHEDULE_PATH, 'utf8'));
    
    // Calcular próximo restart se o sistema estiver habilitado
    if (schedules.enabled && Array.isArray(schedules.restartTimes) && schedules.restartTimes.length > 0) {
        const now = DateTime.local();
        let nextRestart = null;
        
        // Ordenar horários para facilitar a busca
        const sortedTimes = [...schedules.restartTimes].sort();
        
        // Procurar o próximo horário de hoje
        for (const timeStr of sortedTimes) {
            const [hours, minutes] = timeStr.split(':').map(Number);
            const restartTime = now.set({ hour: hours, minute: minutes, second: 0, millisecond: 0 });
            
            if (restartTime > now) {
                nextRestart = restartTime.toISO();
                break;
            }
        }
        
        // Se não encontrou para hoje, pegar o primeiro de amanhã
        if (!nextRestart) {
            const tomorrow = now.plus({ days: 1 });
            const [hours, minutes] = sortedTimes[0].split(':').map(Number);
            const restartTime = tomorrow.set({ hour: hours, minute: minutes, second: 0, millisecond: 0 });
            nextRestart = restartTime.toISO();
        }
        
        // Só salva se mudou
        if (schedules.nextRestart !== nextRestart) {
            schedules.nextRestart = nextRestart;
            saveSchedules(schedules);
        }
    } else {
        if (schedules.nextRestart !== null) {
            schedules.nextRestart = null;
            saveSchedules(schedules);
        }
    }
    
    return schedules;
}

function saveSchedules(data) {
    // Calcular próximo restart antes de salvar
    if (data.enabled && Array.isArray(data.restartTimes) && data.restartTimes.length > 0) {
        const now = DateTime.local();
        let nextRestart = null;
        
        // Ordenar horários para facilitar a busca
        const sortedTimes = [...data.restartTimes].sort();
        
        // Procurar o próximo horário de hoje
        for (const timeStr of sortedTimes) {
            const [hours, minutes] = timeStr.split(':').map(Number);
            const restartTime = now.set({ hour: hours, minute: minutes, second: 0, millisecond: 0 });
            
            if (restartTime > now) {
                nextRestart = restartTime.toISO();
                break;
            }
        }
        
        // Se não encontrou para hoje, pegar o primeiro de amanhã
        if (!nextRestart) {
            const tomorrow = now.plus({ days: 1 });
            const [hours, minutes] = sortedTimes[0].split(':').map(Number);
            const restartTime = tomorrow.set({ hour: hours, minute: minutes, second: 0, millisecond: 0 });
            nextRestart = restartTime.toISO();
        }
        
        data.nextRestart = nextRestart;
    } else {
        data.nextRestart = null;
    }
    
    fs.writeFileSync(SCHEDULE_PATH, JSON.stringify(data, null, 2), 'utf8');
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

// Rota para obter status do servidor
router.get('/status', async (req, res) => {
    try {
        updateStatus();
        const status = loadStatus();
        const config = loadConfig();
        
        res.json({
            success: true,
            status,
            config: {
                port: config?.port,
                maxPlayers: config?.maxPlayers,
                useBattleye: config?.useBattleye,
                serverPath: config?.serverPath
            }
        });
    } catch (error) {
        console.error('Erro ao obter status:', error.message);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para iniciar o servidor
router.post('/start', async (req, res) => {
    try {
        const config = loadConfig();
        if (!config) {
            return res.status(500).json({
                success: false,
                error: 'Configuração não encontrada'
            });
        }
        
        // Verificar se já está rodando
        checkProcessRunning((isRunning) => {
            if (isRunning) {
                return res.json({
                    success: false,
                    error: 'Servidor já está rodando'
                });
            }
            
            // Gerar arquivo .bat dinâmico
            const batContent = generateBatFile(config);
            const tempBatPath = path.join('src/data/temp', 'start-server-temp.bat');
            
            fs.writeFileSync(tempBatPath, batContent, 'utf8');
            
            // Executar o arquivo .bat
            executeCommand('cmd', ['/c', tempBatPath])
                .then(() => {
                    const status = loadStatus();
                    status.isRunning = true;
                    status.startTime = new Date().toISOString();
                    status.lastError = null;
                    saveStatus(status);
                    
                    sendWebhook('✅ Servidor SCUM iniciado com sucesso!', '00ff00');
                    
                    res.json({
                        success: true,
                        message: 'Servidor iniciado com sucesso'
                    });
                })
                .catch((error) => {
                    const status = loadStatus();
                    status.lastError = error.message;
                    saveStatus(status);
                    
                    sendWebhook('❌ Erro ao iniciar servidor SCUM', 'ff0000');
                    
                    res.status(500).json({
                        success: false,
                        error: 'Erro ao iniciar servidor',
                        details: error.message
                    });
                });
        });
    } catch (error) {
        console.error('Erro ao iniciar servidor:', error.message);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para parar o servidor
router.post('/stop', async (req, res) => {
    try {
        checkProcessRunning(async (isRunning, pid) => {
            if (!isRunning) {
                return res.json({
                    success: false,
                    error: 'Servidor não está rodando'
                });
            }
            
            console.log(`[STOP] Tentando parar servidor. PID: ${pid}, isRunning: ${isRunning}`);
            
            // Usar a nova função que tenta múltiplas abordagens
            const success = await tryStopProcess(pid);
            
            if (success) {
                const status = loadStatus();
                status.isRunning = false;
                status.pid = null;
                status.startTime = null;
                status.uptime = 0;
                status.lastError = null;
                saveStatus(status);
                
                sendWebhook('🛑 Servidor SCUM parado com sucesso!', 'ffaa00');
                
                res.json({
                    success: true,
                    message: 'Servidor parado com sucesso'
                });
            } else {
                const status = loadStatus();
                status.lastError = 'Não foi possível parar o processo - Acesso negado';
                saveStatus(status);
                
                sendWebhook('❌ Erro ao parar servidor SCUM - Acesso negado', 'ff0000');
                
                res.status(500).json({
                    success: false,
                    error: 'Erro ao parar servidor',
                    details: 'Acesso negado. Tente executar o backend como administrador ou parar o servidor manualmente.'
                });
            }
        });
    } catch (error) {
        console.error('Erro ao parar servidor:', error.message);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para reiniciar o servidor
router.post('/restart', async (req, res) => {
    try {
        checkProcessRunning(async (isRunning, pid) => {
            if (!isRunning) {
                return res.json({
                    success: false,
                    error: 'Servidor não está rodando'
                });
            }
            
            console.log(`[RESTART] Tentando reiniciar servidor. PID: ${pid}, isRunning: ${isRunning}`);
            
            // Gerar arquivo .bat de início primeiro
            const config = loadConfig();
            const batContent = generateBatFile(config);
            const tempBatPath = path.join('src/data/temp', 'start-server-temp.bat');
            fs.writeFileSync(tempBatPath, batContent, 'utf8');
            
            // Usar arquivo PowerShell para reiniciar
            const restartPsPath = path.join('src/data/temp', 'restart-server.ps1');
            
            try {
                console.log(`[RESTART] Executando PowerShell: ${restartPsPath}`);
                await executeCommand('powershell', [
                    '-ExecutionPolicy', 'Bypass',
                    '-File', restartPsPath
                ]);
                
                // Aguardar um pouco e verificar se reiniciou
                await new Promise(resolve => setTimeout(resolve, 5000));
                
                checkProcessRunning((stillRunning) => {
                    if (stillRunning) {
                        const status = loadStatus();
                        status.isRunning = true;
                        status.startTime = new Date().toISOString();
                        status.restartCount++;
                        status.lastError = null;
                        saveStatus(status);
                        
                        sendWebhook('🔄 Servidor SCUM reiniciado com sucesso!', '00aaff');
                        
                        res.json({
                            success: true,
                            message: 'Servidor reiniciado com sucesso'
                        });
                    } else {
                        const status = loadStatus();
                        status.lastError = 'Servidor não iniciou após reiniciar';
                        saveStatus(status);
                        
                        sendWebhook('❌ Erro ao reiniciar servidor SCUM', 'ff0000');
                        
                        res.status(500).json({
                            success: false,
                            error: 'Erro ao reiniciar servidor',
                            details: 'Servidor não iniciou após reiniciar'
                        });
                    }
                });
            } catch (error) {
                console.error('[RESTART] Erro ao executar arquivo .bat:', error);
                const status = loadStatus();
                status.lastError = error.message;
                saveStatus(status);
                
                sendWebhook('❌ Erro ao reiniciar servidor SCUM', 'ff0000');
                
                res.status(500).json({
                    success: false,
                    error: 'Erro ao reiniciar servidor',
                    details: error.message
                });
            }
        });
    } catch (error) {
        console.error('Erro ao reiniciar servidor:', error.message);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para obter configurações
router.get('/config', (req, res) => {
    try {
        const config = loadConfig();
        if (!config) {
            return res.status(500).json({
                success: false,
                error: 'Configuração não encontrada'
            });
        }
        
        res.json({
            success: true,
            config
        });
    } catch (error) {
        console.error('Erro ao obter configurações:', error.message);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Rota para atualizar configurações
router.put('/config', (req, res) => {
    try {
        const currentConfig = loadConfig();
        if (!currentConfig) {
            return res.status(500).json({
                success: false,
                error: 'Configuração atual não encontrada'
            });
        }
        
        const newConfig = { ...currentConfig, ...req.body };
        
        // Validações básicas
        if (newConfig.port && (newConfig.port < 1 || newConfig.port > 65535)) {
            return res.status(400).json({
                success: false,
                error: 'Porta deve estar entre 1 e 65535'
            });
        }
        
        if (newConfig.maxPlayers && (newConfig.maxPlayers < 1 || newConfig.maxPlayers > 100)) {
            return res.status(400).json({
                success: false,
                error: 'MaxPlayers deve estar entre 1 e 100'
            });
        }
        
        if (saveConfig(newConfig)) {
            sendWebhook('⚙️ Configurações do servidor atualizadas', '00aaff');
            
            res.json({
                success: true,
                message: 'Configurações atualizadas com sucesso',
                config: newConfig
            });
        } else {
            res.status(500).json({
                success: false,
                error: 'Erro ao salvar configurações'
            });
        }
    } catch (error) {
        console.error('Erro ao atualizar configurações:', error.message);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// Endpoint único para gerenciar horários de restart
router.route('/schedules')
    .get((req, res) => {
        const schedules = loadSchedules();
        res.json({ success: true, schedules });
    })
    .post((req, res) => {
        const { time } = req.body;
        if (!/^\d{2}:\d{2}$/.test(time)) {
            return res.status(400).json({ success: false, error: 'Formato de horário inválido (ex: 13:00)' });
        }
        const schedules = loadSchedules();
        if (!schedules.restartTimes.includes(time)) {
            schedules.restartTimes.push(time);
            schedules.restartTimes.sort();
            saveSchedules(schedules);
        }
        res.json({ success: true, restartTimes: schedules.restartTimes });
    })
    .delete((req, res) => {
        const { time } = req.body;
        const schedules = loadSchedules();
        schedules.restartTimes = schedules.restartTimes.filter(t => t !== time);
        saveSchedules(schedules);
        res.json({ success: true, restartTimes: schedules.restartTimes });
    })
    .put((req, res) => {
        const { enabled } = req.body;
        const schedules = loadSchedules();
        schedules.enabled = !!enabled;
        saveSchedules(schedules);
        res.json({ success: true, enabled: schedules.enabled });
    });

// Agendador automático de restart
let lastMinuteChecked = null;
setInterval(async () => {
    const schedules = loadSchedules();
    if (!schedules.enabled || !Array.isArray(schedules.restartTimes)) return;

    const now = DateTime.local().set({ second: 0, millisecond: 0 });
    const nowStr = now.toFormat('HH:mm');

    // Notificações progressivas - NOVA LÓGICA
    const notifyTimes = [10, 5, 4, 3, 2, 1];
    for (const restartTime of schedules.restartTimes) {
        const [rHour, rMinute] = restartTime.split(':').map(Number);
        const restartDateTime = now.set({ hour: rHour, minute: rMinute, second: 0, millisecond: 0 });
        for (const min of notifyTimes) {
            const notifyMoment = restartDateTime.minus({ minutes: min });
            const notifyStr = notifyMoment.toFormat('HH:mm');
            const notificationKey = restartTime + '-' + min;
            if (nowStr === notifyStr && schedules.lastNotification !== notificationKey) {
                console.log(`[SCHEDULED_RESTART] Enviando notificação de ${min} minuto(s) para restart das ${restartTime}`);
                await sendWebhook(`⚠️ O servidor será reiniciado automaticamente em ${min} minuto(s) (${restartTime})`, 'ffaa00');
                schedules.lastNotification = notificationKey;
                saveSchedules(schedules);
            }
        }
    }

    // Restart automático
    if (schedules.restartTimes.includes(nowStr) && lastMinuteChecked !== nowStr) {
        await sendWebhook('🔄 Reiniciando servidor automaticamente!', 'ffaa00');
        
        // Executar restart diretamente em vez de usar curl
        try {
            console.log('[SCHEDULED_RESTART] Executando restart automático...');
            
            // Verificar se o servidor está rodando
            checkProcessRunning(async (isRunning, pid) => {
                if (!isRunning) {
                    console.log('[SCHEDULED_RESTART] Servidor não está rodando, iniciando...');
                    await sendWebhook('⚠️ Servidor não estava rodando, iniciando automaticamente!', 'ffaa00');
                    
                    // Gerar arquivo .bat de início
                    const config = loadConfig();
                    const batContent = generateBatFile(config);
                    const tempBatPath = path.join('src/data/temp', 'start-server-temp.bat');
                    fs.writeFileSync(tempBatPath, batContent, 'utf8');
                    
                    // Executar comando de início
                    await executeCommand('cmd', ['/c', tempBatPath]);
                    
                    // Aguardar e verificar se iniciou
                    await new Promise(resolve => setTimeout(resolve, 10000));
                    checkProcessRunning((started) => {
                        if (started) {
                            const status = loadStatus();
                            status.isRunning = true;
                            status.startTime = new Date().toISOString();
                            status.lastError = null;
                            saveStatus(status);
                            
                            schedules.lastRestart = now.toISO();
                            saveSchedules(schedules);
                            lastMinuteChecked = nowStr;
                            
                            sendWebhook('✅ Servidor iniciado automaticamente com sucesso!', '00aaff');
                            
                            // Notificação adicional 1 minuto após o início
                            setTimeout(async () => {
                                await sendWebhook('🟢 Servidor SCUM está online e funcionando normalmente após o início automático!', '00ff00');
                            }, 60000); // 1 minuto
                        } else {
                            sendWebhook('❌ Falha ao iniciar servidor automaticamente!', 'ff0000');
                        }
                    });
                } else {
                    console.log('[SCHEDULED_RESTART] Servidor está rodando, reiniciando...');
                    
                    // Gerar arquivo .bat de início primeiro
                    const config = loadConfig();
                    const batContent = generateBatFile(config);
                    const tempBatPath = path.join('src/data/temp', 'start-server-temp.bat');
                    fs.writeFileSync(tempBatPath, batContent, 'utf8');
                    
                    // Usar arquivo PowerShell para reiniciar
                    const restartPsPath = path.join('src/data/temp', 'restart-server.ps1');
                    
                    await executeCommand('powershell', [
                        '-ExecutionPolicy', 'Bypass',
                        '-File', restartPsPath
                    ]);
                    
                    // Aguardar um pouco e verificar se reiniciou
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    
                    checkProcessRunning((stillRunning) => {
                        if (stillRunning) {
                            const status = loadStatus();
                            status.isRunning = true;
                            status.startTime = new Date().toISOString();
                            status.restartCount++;
                            status.lastError = null;
                            saveStatus(status);
                            
                            schedules.lastRestart = now.toISO();
                            saveSchedules(schedules);
                            lastMinuteChecked = nowStr;
                            
                            sendWebhook('✅ Servidor SCUM reiniciado automaticamente com sucesso!', '00aaff');
                            
                            // Notificação adicional 1 minuto após o restart
                            setTimeout(async () => {
                                await sendWebhook('🟢 Servidor SCUM está online e funcionando normalmente após o restart automático!', '00ff00');
                            }, 60000); // 1 minuto
                        } else {
                            const status = loadStatus();
                            status.lastError = 'Servidor não iniciou após reiniciar automaticamente';
                            saveStatus(status);
                            
                            sendWebhook('❌ Erro ao reiniciar servidor automaticamente!', 'ff0000');
                        }
                    });
                }
            });
        } catch (err) {
            console.error('[SCHEDULED_RESTART] Erro:', err);
            await sendWebhook('❌ Falha ao reiniciar servidor automaticamente!', 'ff0000');
        }
    }
}, 60 * 1000);

// Inicializar diretórios
createDirectories();

// Atualizar status periodicamente
setInterval(updateStatus, 30000); // A cada 30 segundos

module.exports = router; 