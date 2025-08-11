const express = require('express');
const router = express.Router();
const scheduler = require('../src/scheduler');
const logger = require('../src/logger');

// GET /api/scheduler/status - Obter status do scheduler
router.get('/status', (req, res) => {
    try {
        const status = scheduler.getStatus();
        res.json({
            success: true,
            message: 'Status do scheduler recuperado com sucesso',
            data: status
        });
    } catch (error) {
        logger.error('Erro ao obter status do scheduler', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// POST /api/scheduler/start - Iniciar scheduler
router.post('/start', (req, res) => {
    try {
        const result = scheduler.start();
        
        if (result) {
            logger.info('Scheduler iniciado via API');
            res.json({
                success: true,
                message: 'Scheduler iniciado com sucesso',
                data: scheduler.getStatus()
            });
        } else {
            res.status(400).json({
                success: false,
                error: 'Não foi possível iniciar o scheduler'
            });
        }
    } catch (error) {
        logger.error('Erro ao iniciar scheduler', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// POST /api/scheduler/stop - Parar scheduler
router.post('/stop', (req, res) => {
    try {
        const result = scheduler.stop();
        
        if (result) {
            logger.info('Scheduler parado via API');
            res.json({
                success: true,
                message: 'Scheduler parado com sucesso',
                data: scheduler.getStatus()
            });
        } else {
            res.status(400).json({
                success: false,
                error: 'Não foi possível parar o scheduler'
            });
        }
    } catch (error) {
        logger.error('Erro ao parar scheduler', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// POST /api/scheduler/execute - Execução manual
router.post('/execute', async (req, res) => {
    try {
        const result = await scheduler.executeManual();
        
        logger.info('Execução manual do scheduler realizada', { result });
        
        res.json({
            success: true,
            message: 'Execução manual realizada com sucesso',
            data: result
        });
    } catch (error) {
        logger.error('Erro na execução manual do scheduler', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// GET /api/scheduler/can-frontend-execute - Verificar se frontend pode executar
router.get('/can-frontend-execute', (req, res) => {
    try {
        const canExecute = scheduler.canFrontendExecute();
        const status = scheduler.getStatus();
        
        res.json({
            success: true,
            message: 'Verificação de execução do frontend realizada',
            data: {
                canExecute,
                schedulerStatus: status
            }
        });
    } catch (error) {
        logger.error('Erro ao verificar execução do frontend', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// POST /api/scheduler/frontend-execute - Execução pelo frontend
router.post('/frontend-execute', async (req, res) => {
    try {
        if (!scheduler.canFrontendExecute()) {
            return res.status(400).json({
                success: false,
                error: 'Frontend não pode executar neste momento'
            });
        }
        
        const result = await scheduler.executeSequence('frontend');
        
        logger.info('Execução do frontend realizada', { result });
        
        res.json({
            success: true,
            message: 'Execução do frontend realizada com sucesso',
            data: result
        });
    } catch (error) {
        logger.error('Erro na execução do frontend', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

module.exports = router; 