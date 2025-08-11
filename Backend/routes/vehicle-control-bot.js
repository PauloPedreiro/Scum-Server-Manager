const express = require('express');
const router = express.Router();
const VehicleControlIntegrationBot = require('../src/vehicle_control_integration_bot');

let vehicleControlBot = null;

// Função para inicializar o sistema com bot existente
function initializeVehicleControl(botClient) {
    if (!vehicleControlBot) {
        vehicleControlBot = new VehicleControlIntegrationBot(botClient);
    }
    return vehicleControlBot;
}

// Middleware para garantir que o sistema está inicializado
function ensureInitialized(req, res, next) {
    if (!vehicleControlBot) {
        return res.status(500).json({
            success: false,
            error: 'Sistema de controle de veículos não foi inicializado'
        });
    }
    next();
}

// GET /api/vehicle-control-bot/status
router.get('/status', ensureInitialized, (req, res) => {
    try {
        const status = vehicleControlBot.getStatus();
        res.json({
            success: true,
            status: status,
            message: status.isRunning ? 'Sistema rodando' : 'Sistema parado'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// POST /api/vehicle-control-bot/start
router.post('/start', ensureInitialized, async (req, res) => {
    try {
        await vehicleControlBot.start();
        res.json({
            success: true,
            message: 'Sistema de controle de veículos com bot iniciado'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// POST /api/vehicle-control-bot/stop
router.post('/stop', ensureInitialized, async (req, res) => {
    try {
        await vehicleControlBot.stop();
        res.json({
            success: true,
            message: 'Sistema de controle de veículos com bot parado'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// POST /api/vehicle-control-bot/force-update
router.post('/force-update', ensureInitialized, async (req, res) => {
    try {
        await vehicleControlBot.forceUpdate();
        res.json({
            success: true,
            message: 'Atualização forçada dos embeds concluída'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// GET /api/vehicle-control-bot/players
router.get('/players', ensureInitialized, (req, res) => {
    try {
        if (!vehicleControlBot.vehicleControl) {
            return res.status(400).json({
                success: false,
                error: 'Sistema não está rodando'
            });
        }

        const players = vehicleControlBot.vehicleControl.playerVehicles;
        res.json({
            success: true,
            players: players,
            count: Object.keys(players).length
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// POST /api/vehicle-control-bot/reinitialize
router.post('/reinitialize', ensureInitialized, async (req, res) => {
    try {
        await vehicleControlBot.reinitialize();
        res.json({
            success: true,
            message: 'Sistema reinicializado com sucesso'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Exportar router e função de inicialização
module.exports = router; 