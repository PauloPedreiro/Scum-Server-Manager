const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { DateTime } = require('luxon');
const DiscordBot = require('./src/bot');
const logger = require('./src/logger');
const FunnyStatistics = require('./src/funny_statistics');
require('dotenv').config();

// Substituir axios por http nativo
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

// Carregar configurações
function loadConfig() {
    const configPath = path.join(__dirname, 'src', 'data', 'server', 'config.json');
    return JSON.parse(fs.readFileSync(configPath, 'utf8'));
}

// Carregar webhooks
function loadWebhooks() {
    const webhooksPath = path.join(__dirname, 'src', 'data', 'webhooks.json');
    return JSON.parse(fs.readFileSync(webhooksPath, 'utf8'));
}

// Função para enviar webhook (substitui axios)
async function sendWebhook(webhookUrl, data) {
    try {
        await makeRequest({
            url: webhookUrl,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            data: data
        });
        console.log('✅ Webhook enviado com sucesso');
    } catch (error) {
        console.error('❌ Erro ao enviar webhook:', error.message);
    }
}

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Middleware para carregar configurações
app.use((req, res, next) => {
    try {
        req.config = loadConfig();
        req.webhooks = loadWebhooks();
        next();
    } catch (error) {
        console.error('❌ Erro ao carregar configurações:', error.message);
        res.status(500).json({ error: 'Erro de configuração' });
    }
});

// Importar e registrar todas as rotas
try {
    // Rotas principais
    app.use('/api/players', require('./routes/players'));
    app.use('/api/webhook', require('./routes/webhook'));
    app.use('/api', require('./routes/chat'));
    app.use('/api', require('./routes/vehicles'));
    app.use('/api/adminlog', require('./routes/adminlog'));
    app.use('/api/bunkers', require('./routes/bunkers'));
    app.use('/api/famepoints', require('./routes/famepoints'));
    app.use('/api/server', require('./routes/server'));
    app.use('/api/bot', require('./routes/bot'));
    app.use('/api/configserver', require('./routes/configserver'));
    app.use('/api/scheduler', require('./routes/scheduler'));
    app.use('/api/auth', require('./routes/auth'));
    console.log('✅ Todas as rotas registradas com sucesso');
} catch (error) {
    console.error('❌ Erro ao registrar rotas:', error.message);
}

// Rota principal
app.get('/', (req, res) => {
    res.json({
        message: 'Scum Server Manager - Backend',
        status: 'online',
        timestamp: new Date().toISOString(),
        version: '1.0.0'
    });
});

// Rota de health check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        uptime: process.uptime(),
        timestamp: new Date().toISOString()
    });
});

// Rota de teste de webhook
app.post('/test-webhook', async (req, res) => {
    try {
        const { webhookKey, message } = req.body;
        const webhookUrl = req.webhooks[webhookKey];
        
        if (!webhookUrl) {
            return res.status(400).json({ error: 'Webhook não encontrado' });
        }

        await sendWebhook(webhookUrl, {
            content: message || 'Teste de webhook do Scum Server Manager'
        });

        res.json({ success: true, message: 'Webhook enviado com sucesso' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Rota para estatísticas divertidas
app.get('/funny-stats', (req, res) => {
    try {
        const statsPath = path.join(__dirname, 'src', 'data', 'funny_statistics.json');
        const stats = JSON.parse(fs.readFileSync(statsPath, 'utf8'));
        res.json(stats);
    } catch (error) {
        res.status(500).json({ error: 'Erro ao carregar estatísticas' });
    }
});

// Rota para jogadores
app.get('/players', (req, res) => {
    try {
        const playersPath = path.join(__dirname, 'src', 'data', 'players', 'players.json');
        const players = JSON.parse(fs.readFileSync(playersPath, 'utf8'));
        res.json(players);
    } catch (error) {
        res.status(500).json({ error: 'Erro ao carregar jogadores' });
    }
});

// Rota para configurações
app.get('/config', (req, res) => {
    try {
        res.json(req.config);
    } catch (error) {
        res.status(500).json({ error: 'Erro ao carregar configurações' });
    }
});

// Inicializar bot Discord e outros serviços
let discordBot = null;
let funnyStatistics = null;
let scheduler = null;

app.listen(PORT, async () => {
    console.log(`🚀 Scum Server Manager rodando na porta ${PORT}`);
    console.log(`📡 Acesse: http://localhost:${PORT}`);
    console.log(`🔧 Health check: http://localhost:${PORT}/health`);
    console.log(`📊 Estatísticas: http://localhost:${PORT}/funny-stats`);
    console.log(`👥 Jogadores: http://localhost:${PORT}/players`);
    console.log(`⚙️  Configurações: http://localhost:${PORT}/config`);
    console.log(`🔐 Auth: http://localhost:${PORT}/api/auth/login`);
    
    // Iniciar bot Discord
    try {
        discordBot = new DiscordBot();
        await discordBot.start();
        console.log('✅ Bot Discord iniciado com sucesso');
    } catch (error) {
        console.error('❌ Erro ao iniciar bot Discord:', error.message);
    }

    // Iniciar sistema de estatísticas divertidas
    try {
        funnyStatistics = new FunnyStatistics();
        funnyStatistics.startScheduler();
        console.log('✅ Sistema de estatísticas divertidas iniciado com sucesso');
    } catch (error) {
        console.error('❌ Erro ao iniciar sistema de estatísticas divertidas:', error.message);
    }

    // Iniciar scheduler backend
    try {
        scheduler = require('./src/scheduler');
        scheduler.start();
        console.log('✅ Scheduler backend iniciado com sucesso');
    } catch (error) {
        console.error('❌ Erro ao iniciar scheduler backend:', error.message);
    }
});

// Tratamento global de erros não tratados
process.on('uncaughtException', (err) => {
    console.error('❌ Erro não tratado (uncaughtException):', err.message);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('❌ Rejeição não tratada (unhandledRejection):', reason.toString());
});