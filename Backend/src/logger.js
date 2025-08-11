const fs = require('fs');
const path = require('path');

class Logger {
    constructor() {
        this.logLevel = (process.env.LOG_LEVEL || 'info').trim(); // debug, info, warn, error
        this.logDir = path.join(__dirname, 'data', 'logs');
        this.colorsEnabled = true;
        this.ensureLogDirectory();
        
        // Níveis de log em ordem de importância
        this.levels = {
            debug: 0,
            info: 1,
            warn: 2,
            error: 3
        };
    }

    ensureLogDirectory() {
        if (!fs.existsSync(this.logDir)) {
            fs.mkdirSync(this.logDir, { recursive: true });
        }
    }

    shouldLog(level) {
        return this.levels[level] >= this.levels[this.logLevel];
    }

    formatMessage(level, message, data = null) {
        const timestamp = new Date().toISOString();
        const levelUpper = level.toUpperCase();
        
        let formattedMessage = `[${timestamp}] [${levelUpper}] ${message}`;
        
        if (data && typeof data === 'object') {
            formattedMessage += ` | ${JSON.stringify(data)}`;
        }
        
        return formattedMessage;
    }

    writeToFile(message) {
        const today = new Date().toISOString().split('T')[0];
        const logFile = path.join(this.logDir, `${today}.log`);
        
        try {
            fs.appendFileSync(logFile, message + '\n', 'utf8');
        } catch (error) {
            console.error('Erro ao escrever no arquivo de log:', error.message);
        }
    }

    log(level, message, data = null) {
        if (!this.shouldLog(level)) return;
        
        const formattedMessage = this.formatMessage(level, message, data);
        
        // Console output com cores
        const colors = {
            debug: '\x1b[36m', // Cyan
            info: '\x1b[32m',  // Green
            warn: '\x1b[33m',  // Yellow
            error: '\x1b[31m'  // Red
        };
        
        const reset = '\x1b[0m';
        const color = this.colorsEnabled ? (colors[level] || '') : '';
        
        console.log(`${color}${formattedMessage}${reset}`);
        
        // Salvar no arquivo (sem cores)
        this.writeToFile(formattedMessage);
    }

    debug(message, data = null) {
        this.log('debug', message, data);
    }

    info(message, data = null) {
        this.log('info', message, data);
    }

    warn(message, data = null) {
        this.log('warn', message, data);
    }

    error(message, data = null) {
        this.log('error', message, data);
    }

    // Logs específicos para diferentes módulos
    server(message, data = null) {
        this.info(`[SERVER] ${message}`, data);
    }

    bot(message, data = null) {
        this.info(`[BOT] ${message}`, data);
    }

    webhook(message, data = null) {
        this.info(`[WEBHOOK] ${message}`, data);
    }

    // Função para mascarar Steam ID
    maskSteamId(steamId) {
        if (!steamId || steamId.length < 8) return steamId;
        const first = steamId.substring(0, 4);
        const last = steamId.substring(steamId.length - 4);
        return `${first}****${last}`;
    }

    command(command, player, steamId, vehicleId, data = null) {
        // Mascarar Steam ID para segurança
        const maskedSteamId = this.maskSteamId(steamId);
        this.info(`[COMMAND] /${command} | ${player} (${maskedSteamId}) | Veículo: ${vehicleId}`, data);
    }

    // Logs para rotas específicas
    players(message, data = null) {
        this.info(`[PLAYERS] ${message}`, data);
    }

    vehicles(message, data = null) {
        this.info(`[VEHICLES] ${message}`, data);
    }

    bunkers(message, data = null) {
        this.info(`[BUNKERS] ${message}`, data);
    }

    famepoints(message, data = null) {
        this.info(`[FAMEPOINTS] ${message}`, data);
    }

    adminlog(message, data = null) {
        this.info(`[ADMINLOG] ${message}`, data);
    }
}

// Criar instância singleton
const logger = new Logger();

module.exports = logger; 