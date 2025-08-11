const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const DiscordBot = require('./src/bot');
const logger = require('./src/logger');
const FunnyStatistics = require('./src/funny_statistics');
const VehicleControlWebhookMonitor = require('./src/vehicle_control_webhook_monitor');
const SquadEmbedManager = require('./src/squad_embed_manager');
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
app.use('/api/squads', require('./routes/squads'));
app.use('/api/auth', require('./routes/auth'));
app.use('/api/vehicle-control', require('./routes/vehicle-control-bot'));

// Rota de teste
app.get('/', (req, res) => {
    res.json({ message: 'SCUM Server Manager Backend - Online' });
});

// Inicializar bot Discord
let discordBot = null;
let funnyStatistics = null;
let scheduler = null;
let vehicleControl = null;
let squadEmbedManager = null;
let chestOwnershipMonitor = null;

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

    // Iniciar monitor de Chest Ownership automático
    try {
        const ChestOwnershipMonitor = require('./src/chest_ownership_monitor');
        chestOwnershipMonitor = new ChestOwnershipMonitor();
        chestOwnershipMonitor.start();
        logger.server('ChestOwnershipMonitor iniciado com sucesso');
    } catch (error) {
        logger.error('Erro ao iniciar ChestOwnershipMonitor', { error: error.message });
    }

    // Iniciar sistema de controle de veículos com monitoramento de webhook
    try {
        console.log('🔄 Iniciando sistema de controle de veículos...');
        console.log('discordBot:', discordBot ? 'Disponível' : 'Não disponível');
        console.log('discordBot.client:', discordBot?.client ? 'Disponível' : 'Não disponível');
        
        vehicleControl = new VehicleControlWebhookMonitor(discordBot.client);
        console.log('✅ VehicleControlWebhookMonitor criado');
        
        await vehicleControl.start();
        console.log('✅ VehicleControlWebhookMonitor iniciado');
        
        // Conectar o sistema de controle de veículos ao bot
        discordBot.setVehicleControl(vehicleControl);
        console.log('✅ VehicleControl conectado ao bot');
        
        // Verificar se a conexão foi estabelecida
        console.log('vehicleControl no bot:', discordBot.vehicleControl ? 'Conectado' : 'Não conectado');
        
        logger.server('Sistema de controle de veículos com monitoramento de webhook iniciado com sucesso');
    } catch (error) {
        console.error('❌ Erro ao iniciar sistema de controle de veículos:', error);
        logger.error('Erro ao iniciar sistema de controle de veículos', { error: error.message });
    }

    // Iniciar sistema de embeds dos squads com bot Discord
    try {
        console.log('🏆 Iniciando sistema de embeds dos squads...');
        squadEmbedManager = new SquadEmbedManager(discordBot.client);
        console.log('✅ SquadEmbedManager criado');
        
        // Inicializar squads automaticamente
        setTimeout(async () => {
            try {
                console.log('🔄 Inicializando squads automaticamente...');
                const SquadsManager = require('./src/squads');
                const squadsManager = new SquadsManager();
                const currentSquads = await squadsManager.getSquadsData();
                await squadEmbedManager.initializeSquads(currentSquads);
                console.log('✅ Squads inicializados automaticamente');
            } catch (error) {
                console.error('❌ Erro ao inicializar squads automaticamente:', error.message);
            }
        }, 3000); // Aguardar 3 segundos para garantir que tudo esteja pronto
        
        console.log('✅ Sistema de embeds dos squads pronto');
        logger.server('Sistema de embeds dos squads iniciado com sucesso');
    } catch (error) {
        console.error('❌ Erro ao iniciar sistema de embeds dos squads:', error);
        logger.error('Erro ao iniciar sistema de embeds dos squads', { error: error.message });
    }
});

// Exportar variáveis para uso em outros módulos
module.exports = {
    discordBot,
    funnyStatistics,
    scheduler,
    vehicleControl,
    squadEmbedManager
};

// Também exportar globalmente para acesso direto
global.squadEmbedManager = squadEmbedManager;

// Aguardar um pouco para garantir que o SquadEmbedManager seja inicializado
setTimeout(() => {
    global.squadEmbedManager = squadEmbedManager;
    console.log('✅ SquadEmbedManager exportado globalmente');
}, 5000);

// Tratamento global de erros não tratados
process.on('uncaughtException', (err) => {
    logger.error('Erro não tratado (uncaughtException)', { error: err.message });
});

process.on('unhandledRejection', (reason, promise) => {
    logger.error('Rejeição não tratada (unhandledRejection)', { reason: reason.toString() });
}); 