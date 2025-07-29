const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const axios = require('axios');

const WEBHOOKS_PATH = path.join('src/data/webhooks.json');

// Função para ler webhooks
function readWebhooks() {
    if (fs.existsSync(WEBHOOKS_PATH)) {
        try {
            return JSON.parse(fs.readFileSync(WEBHOOKS_PATH, 'utf8'));
        } catch (e) {
            return {};
        }
    }
    return {};
}

// Função para salvar webhooks
function saveWebhooks(obj) {
    fs.writeFileSync(WEBHOOKS_PATH, JSON.stringify(obj, null, 2), 'utf8');
}

// Endpoint para cadastrar/alterar webhook do painelplayers
router.post('/painelplayers', (req, res) => {
    const { url } = req.body;
    if (!url || typeof url !== 'string' || !url.startsWith('https://')) {
        return res.status(400).json({ success: false, message: 'URL do webhook inválida.' });
    }
    const webhooks = readWebhooks();
    webhooks.painelplayers = url;
    saveWebhooks(webhooks);
    res.json({ success: true, message: 'Webhook do painelplayers cadastrado/atualizado com sucesso.', url });
});

// Endpoint para obter o webhook do painelplayers
router.get('/painelplayers', (req, res) => {
    const webhooks = readWebhooks();
    const url = webhooks.painelplayers || null;
    if (url) {
        res.json({ success: true, message: 'Webhook recuperado com sucesso.', url });
    } else {
        res.json({ success: false, message: 'Nenhum webhook cadastrado para painelplayers.', url: null });
    }
});

// Endpoint para cadastrar/alterar webhook do chat_in_game
router.post('/chat_in_game', (req, res) => {
    const { url } = req.body;
    if (!url || typeof url !== 'string' || !url.startsWith('https://')) {
        return res.status(400).json({ success: false, message: 'URL do webhook inválida.' });
    }
    const webhooks = readWebhooks();
    webhooks.Chat_in_Game = url;
    saveWebhooks(webhooks);
    res.json({ success: true, message: 'Webhook do chat_in_game cadastrado/atualizado com sucesso.', url });
});

// Endpoint para obter o webhook do chat_in_game
router.get('/chat_in_game', (req, res) => {
    const webhooks = readWebhooks();
    const url = webhooks.Chat_in_Game || null;
    if (url) {
        res.json({ success: true, message: 'Webhook recuperado com sucesso.', url });
    } else {
        res.json({ success: false, message: 'Nenhum webhook cadastrado para chat_in_game.', url: null });
    }
});

// Endpoint para cadastrar/alterar webhook do LogVeiculos
router.post('/LogVeiculos', (req, res) => {
    const { url } = req.body;
    if (!url || typeof url !== 'string' || !url.startsWith('https://')) {
        return res.status(400).json({ success: false, message: 'URL do webhook inválida.' });
    }
    const webhooks = readWebhooks();
    webhooks.LogVeiculos = url;
    saveWebhooks(webhooks);
    res.json({ success: true, message: 'Webhook do LogVeiculos cadastrado/atualizado com sucesso.', url });
});

// Endpoint para obter o webhook do LogVeiculos
router.get('/LogVeiculos', (req, res) => {
    const webhooks = readWebhooks();
    const url = webhooks.LogVeiculos || null;
    if (url) {
        res.json({ success: true, message: 'Webhook recuperado com sucesso.', url });
    } else {
        res.json({ success: false, message: 'Nenhum webhook cadastrado para LogVeiculos.', url: null });
    }
});

// Endpoint para cadastrar/alterar webhook do AdminLog
router.post('/adminlog', (req, res) => {
    const { url } = req.body;
    if (!url || typeof url !== 'string' || !url.startsWith('https://')) {
        return res.status(400).json({ success: false, message: 'URL do webhook inválida.' });
    }
    const webhooks = readWebhooks();
    webhooks.adminlog = url;
    saveWebhooks(webhooks);
    res.json({ success: true, message: 'Webhook do adminlog cadastrado/atualizado com sucesso.', url });
});

// Endpoint para obter o webhook do AdminLog
router.get('/adminlog', (req, res) => {
    const webhooks = readWebhooks();
    const url = webhooks.adminlog || null;
    if (url) {
        res.json({ success: true, message: 'Webhook recuperado com sucesso.', url });
    } else {
        res.json({ success: false, message: 'Nenhum webhook cadastrado para adminlog.', url: null });
    }
});

// Endpoint para cadastrar/alterar webhook do Bunkers
router.post('/bunkers', async (req, res) => {
    const { url } = req.body;
    if (!url || typeof url !== 'string' || !url.startsWith('https://')) {
        return res.status(400).json({ success: false, message: 'URL do webhook inválida.' });
    }
    const webhooks = readWebhooks();
    webhooks.bunkers = url;
    saveWebhooks(webhooks);
    
    // Mensagem de teste
    try {
        await axios.post(url, {
            content: null,
            embeds: [{
                title: '🛡️ Webhook de Bunkers cadastrado com sucesso!',
                description: 'Este webhook foi cadastrado para receber notificações dos eventos de bunkers.',
                color: 0x00ff00,
                timestamp: new Date().toISOString(),
                footer: { text: 'SCUM Server Manager' }
            }]
        }, { headers: { 'Content-Type': 'application/json' } });
    } catch (err) {
        return res.status(200).json({ success: true, warning: 'Webhook salvo, mas não foi possível enviar mensagem de teste. Verifique a URL.' });
    }
    
    res.json({ success: true, message: 'Webhook do bunkers cadastrado/atualizado com sucesso.', url });
});

// Endpoint para obter o webhook do Bunkers
router.get('/bunkers', (req, res) => {
    const webhooks = readWebhooks();
    const url = webhooks.bunkers || null;
    if (url) {
        res.json({ success: true, message: 'Webhook recuperado com sucesso.', url });
    } else {
        res.json({ success: false, message: 'Nenhum webhook cadastrado para bunkers.', url: null });
    }
});

// Endpoint para cadastrar/alterar webhook do Famepoints
router.post('/famepoints', (req, res) => {
    const { url } = req.body;
    if (!url || typeof url !== 'string' || !url.startsWith('https://')) {
        return res.status(400).json({ success: false, message: 'URL do webhook inválida.' });
    }
    const webhooks = readWebhooks();
    webhooks.famepoints = url;
    saveWebhooks(webhooks);
    res.json({ success: true, message: 'Webhook do famepoints cadastrado/atualizado com sucesso.', url });
});

// Endpoint para obter o webhook do Famepoints
router.get('/famepoints', (req, res) => {
    const webhooks = readWebhooks();
    const url = webhooks.famepoints || null;
    if (url) {
        res.json({ success: true, message: 'Webhook recuperado com sucesso.', url });
    } else {
        res.json({ success: false, message: 'Nenhum webhook cadastrado para famepoints.', url: null });
    }
});

// Endpoint para cadastrar/alterar webhook do ServerStatus
router.post('/serverstatus', async (req, res) => {
    const { url } = req.body;
    if (!url || typeof url !== 'string' || !url.startsWith('https://')) {
        return res.status(400).json({ success: false, message: 'URL do webhook inválida.' });
    }
    const webhooks = readWebhooks();
    webhooks.serverstatus = url;
    saveWebhooks(webhooks);
    
    // Mensagem de teste
    try {
        await axios.post(url, {
            content: null,
            embeds: [{
                title: '🖥️ Webhook de Status do Servidor cadastrado com sucesso!',
                description: 'Este webhook foi cadastrado para receber notificações sobre o status do servidor SCUM.',
                color: 0x00ff00,
                timestamp: new Date().toISOString(),
                footer: { text: 'SCUM Server Manager' }
            }]
        }, { headers: { 'Content-Type': 'application/json' } });
    } catch (err) {
        return res.status(200).json({ success: true, warning: 'Webhook salvo, mas não foi possível enviar mensagem de teste. Verifique a URL.' });
    }
    
    res.json({ success: true, message: 'Webhook do serverstatus cadastrado/atualizado com sucesso.', url });
});

// Endpoint para obter o webhook do ServerStatus
router.get('/serverstatus', (req, res) => {
    const webhooks = readWebhooks();
    const url = webhooks.serverstatus || null;
    if (url) {
        res.json({ success: true, message: 'Webhook recuperado com sucesso.', url });
    } else {
        res.json({ success: false, message: 'Nenhum webhook cadastrado para serverstatus.', url: null });
    }
});

// Endpoint para cadastrar/alterar webhook do Funny Statistics
router.post('/funny-statistic', async (req, res) => {
    const { url } = req.body;
    if (!url || typeof url !== 'string' || !url.startsWith('https://')) {
        return res.status(400).json({ success: false, message: 'URL do webhook inválida.' });
    }
    const webhooks = readWebhooks();
    webhooks['funny-statistic'] = url;
    saveWebhooks(webhooks);
    
    // Mensagem de teste
    try {
        await axios.post(url, {
            content: null,
            embeds: [{
                title: '🎭 Webhook de Estatísticas Divertidas cadastrado com sucesso!',
                description: 'Este webhook foi cadastrado para receber as estatísticas divertidas do servidor SCUM.',
                color: 0xff6b6b,
                timestamp: new Date().toISOString(),
                footer: { text: 'SCUM Server Manager - Estatísticas Divertidas' }
            }]
        }, { headers: { 'Content-Type': 'application/json' } });
    } catch (err) {
        return res.status(200).json({ success: true, warning: 'Webhook salvo, mas não foi possível enviar mensagem de teste. Verifique a URL.' });
    }
    
    res.json({ success: true, message: 'Webhook do funny-statistic cadastrado/atualizado com sucesso.', url });
});

// Endpoint para obter o webhook do Funny Statistics
router.get('/funny-statistic', (req, res) => {
    const webhooks = readWebhooks();
    const url = webhooks['funny-statistic'] || null;
    if (url) {
        res.json({ success: true, message: 'Webhook recuperado com sucesso.', url });
    } else {
        res.json({ success: false, message: 'Nenhum webhook cadastrado para funny-statistic.', url: null });
    }
});

module.exports = router; 