const express = require('express');
const router = express.Router();
const SquadsManager = require('../src/squads');
const SquadEmbedManager = require('../src/squad_embed_manager');
const logger = require('../src/logger');

// Instâncias dos gerenciadores
const squadsManager = new SquadsManager();
let squadEmbedManager = null;

// Função para obter o SquadEmbedManager
function getSquadEmbedManager() {
    if (!squadEmbedManager) {
        try {
            // Tentar obter do server.js
            const server = require('../server');
            squadEmbedManager = server.squadEmbedManager;
            console.log('SquadEmbedManager obtido do server:', !!squadEmbedManager);
        } catch (error) {
            console.log('SquadEmbedManager não disponível ainda:', error.message);
        }
        
        // Tentar obter globalmente
        if (!squadEmbedManager && global.squadEmbedManager) {
            squadEmbedManager = global.squadEmbedManager;
            console.log('SquadEmbedManager obtido globalmente:', !!squadEmbedManager);
        }
    }
    return squadEmbedManager;
}

/**
 * @route GET /api/squads
 * @desc Executa a verificação de squads
 * @access Public
 */
router.get('/', async (req, res) => {
    try {
        logger.info('Iniciando verificação de squads via API');
        
        // Obter dados dos squads do banco
        await squadsManager.copyDatabase();
        const rawSquadsData = await squadsManager.readSquadsFromDatabase();
        const currentSquads = squadsManager.processSquadsData(rawSquadsData);
        
        // Usar o novo sistema de embeds com bot
        const embedManager = getSquadEmbedManager();
        if (embedManager) {
            await embedManager.updateSquads(currentSquads);
        } else {
            // Fallback para o sistema antigo
            await squadsManager.execute();
        }
        
        // Carregar dados atualizados
        const squadsData = squadsManager.loadSquadsData();
        const lastProcessed = squadsManager.loadLastProcessed();
        
        res.json({
            success: true,
            message: 'Verificação de squads executada com sucesso',
            data: {
                squads_count: Object.keys(squadsData.squads).length,
                last_check: squadsData.last_check,
                last_execution: lastProcessed.last_execution,
                next_execution: lastProcessed.next_execution,
                interval_hours: lastProcessed.interval_hours,
                using_bot: !!embedManager
            }
        });
        
    } catch (error) {
        logger.error('Erro na verificação de squads:', error);
        res.status(500).json({
            success: false,
            error: 'Erro interno na verificação de squads',
            message: error.message
        });
    }
});

/**
 * @route GET /api/squads/status
 * @desc Obtém o status atual do sistema de squads
 * @access Public
 */
router.get('/status', async (req, res) => {
    try {
        const squadsData = squadsManager.loadSquadsData();
        const lastProcessed = squadsManager.loadLastProcessed();
        
        res.json({
            success: true,
            message: 'Status do sistema de squads recuperado com sucesso',
            data: {
                squads_count: Object.keys(squadsData.squads).length,
                last_check: squadsData.last_check,
                last_execution: lastProcessed.last_execution,
                next_execution: lastProcessed.next_execution,
                interval_hours: lastProcessed.interval_hours,
                is_enabled: true
            }
        });
        
    } catch (error) {
        logger.error('Erro ao obter status de squads:', error);
        res.status(500).json({
            success: false,
            error: 'Erro interno ao obter status de squads',
            message: error.message
        });
    }
});

/**
 * @route GET /api/squads/list
 * @desc Lista todos os squads salvos
 * @access Public
 */
router.get('/list', async (req, res) => {
    try {
        const squadsData = squadsManager.loadSquadsData();
        
        res.json({
            success: true,
            message: 'Lista de squads recuperada com sucesso',
            data: {
                squads: squadsData.squads,
                total_count: Object.keys(squadsData.squads).length,
                last_check: squadsData.last_check
            }
        });
        
    } catch (error) {
        logger.error('Erro ao listar squads:', error);
        res.status(500).json({
            success: false,
            error: 'Erro interno ao listar squads',
            message: error.message
        });
    }
});

/**
 * @route POST /api/squads/force-update
 * @desc Força uma atualização completa dos squads
 * @access Public
 */
router.post('/force-update', async (req, res) => {
    try {
        logger.info('Forçando atualização de squads via API');
        
        // Obter dados dos squads do banco
        await squadsManager.copyDatabase();
        const rawSquadsData = await squadsManager.readSquadsFromDatabase();
        const currentSquads = squadsManager.processSquadsData(rawSquadsData);
        
        // Usar o novo sistema de embeds com bot
        const embedManager = getSquadEmbedManager();
        if (embedManager) {
            await embedManager.updateSquads(currentSquads);
        } else {
            // Fallback para o sistema antigo
            await squadsManager.execute();
        }
        
        res.json({
            success: true,
            message: 'Atualização forçada de squads executada com sucesso',
            data: {
                timestamp: new Date().toISOString(),
                using_bot: !!embedManager
            }
        });
        
    } catch (error) {
        logger.error('Erro na atualização forçada de squads:', error);
        res.status(500).json({
            success: false,
            error: 'Erro interno na atualização forçada de squads',
            message: error.message
        });
    }
});

/**
 * @route POST /api/squads/initialize
 * @desc Inicializa os embeds dos squads no canal do bot
 * @access Public
 */
router.post('/initialize', async (req, res) => {
    try {
        logger.info('Inicializando embeds dos squads via API');
        
        // Obter dados dos squads do banco
        await squadsManager.copyDatabase();
        const rawSquadsData = await squadsManager.readSquadsFromDatabase();
        const currentSquads = squadsManager.processSquadsData(rawSquadsData);
        
        // Tentar obter o SquadEmbedManager
        let embedManager = getSquadEmbedManager();
        
        // Se não conseguir obter, aguardar um pouco e tentar novamente
        if (!embedManager) {
            console.log('⏳ Aguardando SquadEmbedManager ficar disponível...');
            await new Promise(resolve => setTimeout(resolve, 5000));
            embedManager = getSquadEmbedManager();
            
            // Se ainda não conseguir, tentar acessar diretamente
            if (!embedManager && global.squadEmbedManager) {
                embedManager = global.squadEmbedManager;
                console.log('✅ SquadEmbedManager obtido globalmente');
            }
        }
        
        if (embedManager) {
            try {
                console.log('🏆 Inicializando embeds com bot Discord...');
                await embedManager.initializeSquads(currentSquads);
                console.log('✅ Embeds inicializados com sucesso!');
                res.json({
                    success: true,
                    message: 'Embeds dos squads inicializados com sucesso',
                    data: {
                        squads_count: Object.keys(currentSquads).length,
                        timestamp: new Date().toISOString(),
                        using_bot: true
                    }
                });
            } catch (error) {
                console.log('❌ Erro ao usar bot, usando fallback:', error.message);
                // Fallback: usar sistema antigo
                await squadsManager.execute();
                res.json({
                    success: true,
                    message: 'Embeds dos squads inicializados (sistema antigo)',
                    data: {
                        squads_count: Object.keys(currentSquads).length,
                        timestamp: new Date().toISOString(),
                        using_bot: false
                    }
                });
            }
        } else {
            console.log('⚠️ SquadEmbedManager não disponível, usando sistema antigo');
            // Fallback: usar sistema antigo
            await squadsManager.execute();
            res.json({
                success: true,
                message: 'Embeds dos squads inicializados (sistema antigo)',
                data: {
                    squads_count: Object.keys(currentSquads).length,
                    timestamp: new Date().toISOString(),
                    using_bot: false
                }
            });
        }
        
    } catch (error) {
        logger.error('Erro na inicialização dos squads:', error);
        res.status(500).json({
            success: false,
            error: 'Erro interno na inicialização dos squads',
            message: error.message
        });
    }
});

module.exports = router; 