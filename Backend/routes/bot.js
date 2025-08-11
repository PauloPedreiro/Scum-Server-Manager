const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');

// Carregar configuração
function loadConfig() {
    try {
        const configPath = path.join(__dirname, '..', 'src', 'data', 'server', 'config.json');
        const configData = fs.readFileSync(configPath, 'utf8');
        return JSON.parse(configData);
    } catch (error) {
        console.error('Erro ao carregar configuração:', error);
        return null;
    }
}

// Obter caminho dos dados do bot
function getBotDataPath() {
    return path.join(__dirname, '..', 'src', 'data', 'bot');
}

// GET /api/bot/config - Obter configurações
router.get('/config', (req, res) => {
    try {
        const config = loadConfig();
        if (!config) {
            return res.status(500).json({ error: 'Erro ao carregar configuração' });
        }
        
        res.json({
            enabled: config.discord_bot?.enabled || false,
            features: config.discord_bot?.features || {},
            channels: config.discord_bot?.channels || {}
        });
    } catch (error) {
        console.error('Erro ao obter configuração:', error);
        res.status(500).json({ error: 'Erro interno do servidor' });
    }
});

// POST /api/bot/config - Atualizar configurações
router.post('/config', (req, res) => {
    try {
        const configPath = path.join(__dirname, '..', 'src', 'data', 'server', 'config.json');
        const config = loadConfig();
        
        if (!config) {
            return res.status(500).json({ error: 'Erro ao carregar configuração' });
        }

        // Atualizar configurações do bot
        if (req.body.discord_bot) {
            config.discord_bot = { ...config.discord_bot, ...req.body.discord_bot };
        }

        fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
        
        res.json({ message: 'Configuração atualizada com sucesso', config: config.discord_bot });
    } catch (error) {
        console.error('Erro ao atualizar configuração:', error);
        res.status(500).json({ error: 'Erro interno do servidor' });
    }
});

// GET /api/bot/status - Status do bot
router.get('/status', (req, res) => {
    try {
        const config = loadConfig();
        const botDataPath = getBotDataPath();
        
        // Verificar arquivos de dados
        const linkedUsersPath = path.join(botDataPath, 'linked_users.json');
        const registrationsPath = path.join(botDataPath, 'vehicle_registrations.json');
        const pendingPath = path.join(botDataPath, 'pending_requests.json');
        const cooldownsPath = path.join(botDataPath, 'cooldowns.json');
        
        let stats = {
            enabled: config.discord_bot?.enabled || false,
            linked_users: 0,
            total_registrations: 0,
            pending_requests: 0,
            active_cooldowns: 0
        };
        
        // Contar usuários vinculados
        if (fs.existsSync(linkedUsersPath)) {
            const linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            stats.linked_users = Object.keys(linkedUsers).length;
        }
        
        // Contar registros
        if (fs.existsSync(registrationsPath)) {
            const registrations = JSON.parse(fs.readFileSync(registrationsPath, 'utf8'));
            stats.total_registrations = Object.keys(registrations).length;
        }
        
        // Contar solicitações pendentes
        if (fs.existsSync(pendingPath)) {
            const pending = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            stats.pending_requests = Object.keys(pending).length;
        }
        
        // Contar cooldowns ativos
        if (fs.existsSync(cooldownsPath)) {
            const cooldowns = JSON.parse(fs.readFileSync(cooldownsPath, 'utf8'));
            const now = new Date();
            stats.active_cooldowns = Object.values(cooldowns).filter(cooldown => {
                return new Date(cooldown.cooldown_until) > now;
            }).length;
        }
        
        res.json(stats);
    } catch (error) {
        console.error('Erro ao obter status:', error);
        res.status(500).json({ error: 'Erro interno do servidor' });
    }
});

// GET /api/bot/linked-users - Listar usuários vinculados
router.get('/linked-users', (req, res) => {
    try {
        const linkedUsersPath = path.join(getBotDataPath(), 'linked_users.json');
        
        if (!fs.existsSync(linkedUsersPath)) {
            return res.json([]);
        }
        
        const linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
        const users = Object.entries(linkedUsers).map(([discordId, data]) => ({
            discord_id: discordId,
            steam_id: data.steam_id,
            linked_at: data.linked_at,
            last_activity: data.last_activity,
            total_registrations: data.total_registrations
        }));
        
        res.json(users);
    } catch (error) {
        console.error('Erro ao listar usuários vinculados:', error);
        res.status(500).json({ error: 'Erro interno do servidor' });
    }
});

// POST /api/bot/link-user - Vincular Discord ↔ Steam
router.post('/link-user', (req, res) => {
    try {
        const { discord_id, steam_id } = req.body;
        
        if (!discord_id || !steam_id) {
            return res.status(400).json({ error: 'Discord ID e Steam ID são obrigatórios' });
        }
        
        const linkedUsersPath = path.join(getBotDataPath(), 'linked_users.json');
        let linkedUsers = {};
        
        if (fs.existsSync(linkedUsersPath)) {
            linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
        }
        
        linkedUsers[discord_id] = {
            steam_id: steam_id,
            linked_at: new Date().toISOString(),
            permissions: ["vehicle_registration"],
            last_activity: new Date().toISOString(),
            total_registrations: 0
        };
        
        fs.writeFileSync(linkedUsersPath, JSON.stringify(linkedUsers, null, 2));
        
        res.json({ message: 'Usuário vinculado com sucesso', discord_id, steam_id });
    } catch (error) {
        console.error('Erro ao vincular usuário:', error);
        res.status(500).json({ error: 'Erro interno do servidor' });
    }
});

// DELETE /api/bot/unlink-user/:discordId - Desvincular usuário
router.delete('/unlink-user/:discordId', (req, res) => {
    try {
        const { discordId } = req.params;
        
        const linkedUsersPath = path.join(getBotDataPath(), 'linked_users.json');
        
        if (!fs.existsSync(linkedUsersPath)) {
            return res.status(404).json({ error: 'Nenhum usuário vinculado encontrado' });
        }
        
        const linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
        
        if (!linkedUsers[discordId]) {
            return res.status(404).json({ error: 'Usuário não encontrado' });
        }
        
        delete linkedUsers[discordId];
        fs.writeFileSync(linkedUsersPath, JSON.stringify(linkedUsers, null, 2));
        
        res.json({ message: 'Usuário desvinculado com sucesso', discord_id: discordId });
    } catch (error) {
        console.error('Erro ao desvincular usuário:', error);
        res.status(500).json({ error: 'Erro interno do servidor' });
    }
});

// GET /api/bot/vehicle-registrations - Listar registros
router.get('/vehicle-registrations', (req, res) => {
    try {
        const registrationsPath = path.join(getBotDataPath(), 'vehicle_registrations.json');
        
        if (!fs.existsSync(registrationsPath)) {
            return res.json([]);
        }
        
        const registrations = JSON.parse(fs.readFileSync(registrationsPath, 'utf8'));
        const registrationsList = Object.values(registrations);
        
        res.json(registrationsList);
    } catch (error) {
        console.error('Erro ao listar registros:', error);
        res.status(500).json({ error: 'Erro interno do servidor' });
    }
});

// GET /api/bot/vehicle-registrations/:steamId - Registros por usuário
router.get('/vehicle-registrations/:steamId', (req, res) => {
    try {
        const { steamId } = req.params;
        const registrationsPath = path.join(getBotDataPath(), 'vehicle_registrations.json');
        
        if (!fs.existsSync(registrationsPath)) {
            return res.json([]);
        }
        
        const registrations = JSON.parse(fs.readFileSync(registrationsPath, 'utf8'));
        const userRegistrations = Object.values(registrations).filter(
            reg => reg.steamId === steamId
        );
        
        res.json(userRegistrations);
    } catch (error) {
        console.error('Erro ao listar registros do usuário:', error);
        res.status(500).json({ error: 'Erro interno do servidor' });
    }
});

// POST /api/bot/vehicle-registration - Registrar veículo manualmente
router.post('/vehicle-registration', (req, res) => {
    try {
        const { vehicleId, vehicleType, steamId, discordUserId } = req.body;
        
        if (!vehicleId || !vehicleType || !steamId) {
            return res.status(400).json({ error: 'Vehicle ID, Vehicle Type e Steam ID são obrigatórios' });
        }
        
        const registrationsPath = path.join(getBotDataPath(), 'vehicle_registrations.json');
        let registrations = {};
        
        if (fs.existsSync(registrationsPath)) {
            registrations = JSON.parse(fs.readFileSync(registrationsPath, 'utf8'));
        }
        
        const registration = {
            vehicleId: vehicleId,
            vehicleType: vehicleType.toUpperCase(),
            steamId: steamId,
            discordUserId: discordUserId || null,
            discordUsername: null,
            registeredAt: new Date().toISOString(),
            channelId: null
        };
        
        registrations[vehicleId] = registration;
        fs.writeFileSync(registrationsPath, JSON.stringify(registrations, null, 2));
        
        res.json({ message: 'Veículo registrado com sucesso', registration });
    } catch (error) {
        console.error('Erro ao registrar veículo:', error);
        res.status(500).json({ error: 'Erro interno do servidor' });
    }
});

// POST /api/bot/clear-cooldown/:steamId - Limpar cooldown
router.post('/clear-cooldown/:steamId', (req, res) => {
    try {
        const { steamId } = req.params;
        const cooldownsPath = path.join(getBotDataPath(), 'cooldowns.json');
        
        if (!fs.existsSync(cooldownsPath)) {
            return res.json({ message: 'Nenhum cooldown encontrado' });
        }
        
        const cooldowns = JSON.parse(fs.readFileSync(cooldownsPath, 'utf8'));
        
        if (!cooldowns[steamId]) {
            return res.json({ message: 'Nenhum cooldown encontrado para este usuário' });
        }
        
        delete cooldowns[steamId];
        fs.writeFileSync(cooldownsPath, JSON.stringify(cooldowns, null, 2));
        
        res.json({ message: 'Cooldown limpo com sucesso', steam_id: steamId });
    } catch (error) {
        console.error('Erro ao limpar cooldown:', error);
        res.status(500).json({ error: 'Erro interno do servidor' });
    }
});

// GET /api/bot/pending-requests - Solicitações pendentes
router.get('/pending-requests', (req, res) => {
    try {
        const pendingPath = path.join(getBotDataPath(), 'pending_requests.json');
        
        if (!fs.existsSync(pendingPath)) {
            return res.json([]);
        }
        
        const pending = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
        const pendingList = Object.entries(pending).map(([steamId, data]) => ({
            steam_id: steamId,
            vehicle_id: data.vehicleId,
            vehicle_type: data.vehicleType,
            requested_at: data.requestedAt,
            expires_at: data.expiresAt
        }));
        
        res.json(pendingList);
    } catch (error) {
        console.error('Erro ao listar solicitações pendentes:', error);
        res.status(500).json({ error: 'Erro interno do servidor' });
    }
});

module.exports = router; 