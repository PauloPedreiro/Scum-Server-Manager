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
                    const response = await makeRequest({
                        url: adminWebhookUrl,
                        method: 'POST',
                        data: {
                            content: line
                        }
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