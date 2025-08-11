const express = require('express');
const router = express.Router();
const VehicleControlIntegration = require('../src/vehicle_control_integration');
const logger = require('../src/logger');

let vehicleControl = null;

// Inicializar sistema se não existir
function getVehicleControl() {
    if (!vehicleControl) {
        vehicleControl = new VehicleControlIntegration();
    }
    return vehicleControl;
}

// GET - Status do sistema
router.get('/status', (req, res) => {
    try {
        const control = getVehicleControl();
        const status = control.getStatus();
        
        res.json({
            success: true,
            data: status
        });
    } catch (error) {
        logger.error('Erro ao obter status do controle de veículos', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// POST - Iniciar sistema
router.post('/start', (req, res) => {
    try {
        const control = getVehicleControl();
        control.start();
        
        res.json({
            success: true,
            message: 'Sistema de controle de veículos iniciado'
        });
    } catch (error) {
        logger.error('Erro ao iniciar controle de veículos', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// POST - Parar sistema
router.post('/stop', (req, res) => {
    try {
        const control = getVehicleControl();
        control.stop();
        
        res.json({
            success: true,
            message: 'Sistema de controle de veículos parado'
        });
    } catch (error) {
        logger.error('Erro ao parar controle de veículos', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// POST - Forçar atualização
router.post('/force-update', (req, res) => {
    try {
        const control = getVehicleControl();
        control.forceUpdate();
        
        res.json({
            success: true,
            message: 'Atualização forçada executada'
        });
    } catch (error) {
        logger.error('Erro ao forçar atualização', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// GET - Listar jogadores e veículos
router.get('/players', (req, res) => {
    try {
        const control = getVehicleControl();
        const players = control.vehicleControl.playerVehicles;
        
        res.json({
            success: true,
            data: players
        });
    } catch (error) {
        logger.error('Erro ao listar jogadores', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

// POST - Reinicializar sistema
router.post('/reinitialize', (req, res) => {
    try {
        const control = getVehicleControl();
        control.vehicleControl.initializeFromRegistrations();
        
        res.json({
            success: true,
            message: 'Sistema reinicializado com registros atuais'
        });
    } catch (error) {
        logger.error('Erro ao reinicializar sistema', { error: error.message });
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor'
        });
    }
});

module.exports = router; 