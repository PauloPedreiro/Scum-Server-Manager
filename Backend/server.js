const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const DiscordBot = require('./src/bot');
const logger = require('./src/logger');
const FunnyStatistics = require('./src/funny_statistics');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '127.0.0.1';

// Configurações
const SCUM_CONFIG_PATH = 'C:/Servers/scum/SCUM/Saved/Config/WindowsServer';



// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Importar rotas
const playersRouter = require('./routes/players');

// Rotas
app.use('/api/players', playersRouter);
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

// Rota de teste
app.get('/', (req, res) => {
    res.json({ message: 'SCUM Server Manager Backend - Online' });
});

// Inicializar bot Discord
let discordBot = null;
let funnyStatistics = null;
let scheduler = null;

app.listen(PORT, HOST, async () => {
    logger.server(`Servidor iniciado em http://${HOST}:${PORT}`);
    logger.server(`Ambiente: ${process.env.NODE_ENV}`);
    
    // Iniciar bot Discord
    try {
        discordBot = new DiscordBot();
        await discordBot.start();
        logger.bot('Bot Discord iniciado com sucesso');
    } catch (error) {
        logger.error('Erro ao iniciar bot Discord', { error: error.message });
    }

    // Iniciar sistema de estatísticas divertidas
    try {
        funnyStatistics = new FunnyStatistics();
        funnyStatistics.startScheduler();
        logger.server('Sistema de estatísticas divertidas iniciado com sucesso');
    } catch (error) {
        logger.error('Erro ao iniciar sistema de estatísticas divertidas', { error: error.message });
    }

    // Iniciar scheduler backend
    try {
        scheduler = require('./src/scheduler');
        scheduler.start();
        logger.server('Scheduler backend iniciado com sucesso');
    } catch (error) {
        logger.error('Erro ao iniciar scheduler backend', { error: error.message });
    }
});

// Tratamento global de erros não tratados
process.on('uncaughtException', (err) => {
    logger.error('Erro não tratado (uncaughtException)', { error: err.message });
});

process.on('unhandledRejection', (reason, promise) => {
    logger.error('Rejeição não tratada (unhandledRejection)', { reason: reason.toString() });
}); 