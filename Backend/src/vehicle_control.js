const fs = require('fs');
const path = require('path');
const axios = require('axios');

class VehicleControl {
    constructor() {
        this.webhooksPath = path.join(__dirname, 'data', 'webhooks.json');
        this.vehiclesPath = path.join(__dirname, 'data', 'vehicles', 'vehicles.json');
        this.registrationsPath = path.join(__dirname, 'data', 'bot', 'vehicle_registrations.json');
        this.playerVehiclesPath = path.join(__dirname, 'data', 'players', 'player_vehicles.json');
        this.lastCleanupPath = path.join(__dirname, 'data', 'players', 'last_cleanup.json');
        
        this.webhooks = this.loadWebhooks();
        this.playerVehicles = this.loadPlayerVehicles();
        this.lastProcessedEvent = this.loadLastProcessedEvent();
        this.lastCleanup = this.loadLastCleanup();
    }

    loadWebhooks() {
        try {
            const data = fs.readFileSync(this.webhooksPath, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            console.error('Erro ao carregar webhooks:', error);
            return {};
        }
    }

    loadPlayerVehicles() {
        try {
            const data = fs.readFileSync(this.playerVehiclesPath, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            console.error('Erro ao carregar player_vehicles:', error);
            return {};
        }
    }

    loadLastCleanup() {
        try {
            const data = fs.readFileSync(this.lastCleanupPath, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            console.error('Erro ao carregar last_cleanup:', error);
            return { lastCleanup: null };
        }
    }

    saveLastCleanup() {
        try {
            fs.writeFileSync(this.lastCleanupPath, JSON.stringify(this.lastCleanup, null, 2));
        } catch (error) {
            console.error('Erro ao salvar last_cleanup:', error);
        }
    }

    loadLastProcessedEvent() {
        try {
            const lastProcessedPath = path.join(__dirname, 'data', 'vehicles', 'lastProcessedEvent.json');
            if (fs.existsSync(lastProcessedPath)) {
                const data = fs.readFileSync(lastProcessedPath, 'utf8');
                return JSON.parse(data);
            }
            return { lastProcessedAt: null };
        } catch (error) {
            console.error('Erro ao carregar último evento processado:', error);
            return { lastProcessedAt: null };
        }
    }

    savePlayerVehicles() {
        try {
            fs.writeFileSync(this.playerVehiclesPath, JSON.stringify(this.playerVehicles, null, 2));
        } catch (error) {
            console.error('Erro ao salvar player_vehicles:', error);
        }
    }

    saveLastProcessedEvent() {
        try {
            const lastProcessedPath = path.join(__dirname, 'data', 'vehicles', 'lastProcessedEvent.json');
            fs.writeFileSync(lastProcessedPath, JSON.stringify(this.lastProcessedEvent, null, 2));
        } catch (error) {
            console.error('Erro ao salvar último evento processado:', error);
        }
    }

    initializeFromRegistrations() {
        try {
            const registrationsData = fs.readFileSync(this.registrationsPath, 'utf8');
            const registrations = JSON.parse(registrationsData);

            // Limpar dados atuais
            this.playerVehicles = {};

            // Processar registros
            for (const [vehicleId, registration] of Object.entries(registrations)) {
                const steamId = registration.steamId;
                const playerName = registration.discordUsername;
                const vehicleType = registration.vehicleType;

                if (!this.playerVehicles[steamId]) {
                    this.playerVehicles[steamId] = {
                        steamId: steamId,
                        playerName: playerName,
                        discordUserId: registration.discordUserId,
                        activeVehicles: [],
                        lastUpdated: new Date().toISOString()
                    };
                }

                this.playerVehicles[steamId].activeVehicles.push({
                    vehicleId: vehicleId,
                    vehicleType: vehicleType,
                    status: 'active'
                });
            }

            this.savePlayerVehicles();
            console.log('Sistema inicializado com registros atuais');
        } catch (error) {
            console.error('Erro ao inicializar com registros:', error);
        }
    }

    processVehicleEvents() {
        try {
            const vehiclesData = fs.readFileSync(this.vehiclesPath, 'utf8');
            const vehicles = JSON.parse(vehiclesData);

            let processedCount = 0;

            for (const event of vehicles) {
                // Verificar se já foi processado
                if (this.lastProcessedEvent.lastProcessedAt && 
                    new Date(event.processedAt) <= new Date(this.lastProcessedEvent.lastProcessedAt)) {
                    continue;
                }

                // Processar eventos de perda de veículo
                if (['Destroyed', 'Disappeared', 'VehicleInactiveTimerReached'].includes(event.event)) {
                    this.removeVehicleFromPlayer(event.vehicleId, event.ownerSteamId);
                    processedCount++;
                }

                // Atualizar último evento processado
                this.lastProcessedEvent.lastProcessedAt = event.processedAt;
            }

            if (processedCount > 0) {
                this.savePlayerVehicles();
                this.saveLastProcessedEvent();
                this.updateDiscordEmbeds();
                console.log(`Processados ${processedCount} eventos de veículos`);
            }

        } catch (error) {
            console.error('Erro ao processar eventos de veículos:', error);
        }
    }

    removeVehicleFromPlayer(vehicleId, steamId) {
        if (!this.playerVehicles[steamId]) {
            return;
        }

        const player = this.playerVehicles[steamId];
        const vehicleIndex = player.activeVehicles.findIndex(v => v.vehicleId === vehicleId);

        if (vehicleIndex !== -1) {
            player.activeVehicles.splice(vehicleIndex, 1);
            player.lastUpdated = new Date().toISOString();
            console.log(`Veículo ${vehicleId} removido de ${player.playerName}`);
        }
    }

    shouldPerformCleanup() {
        // Fazer limpeza a cada 24 horas
        const now = new Date();
        const lastCleanup = this.lastCleanup.lastCleanup ? new Date(this.lastCleanup.lastCleanup) : null;
        
        if (!lastCleanup) {
            return true;
        }
        
        const hoursSinceLastCleanup = (now - lastCleanup) / (1000 * 60 * 60);
        return hoursSinceLastCleanup >= 24;
    }

    async updateDiscordEmbeds() {
        try {
            const webhookUrl = this.webhooks['player-vehicles'];
            if (!webhookUrl) {
                console.error('Webhook player-vehicles não encontrado');
                return;
            }

            // Verificar se precisa fazer limpeza
            const needsCleanup = this.shouldPerformCleanup();
            
            if (needsCleanup) {
                console.log('Realizando limpeza periódica dos embeds...');
                this.lastCleanup.lastCleanup = new Date().toISOString();
                this.saveLastCleanup();
            }

            // Criar embeds para cada jogador
            for (const [steamId, player] of Object.entries(this.playerVehicles)) {
                const embed = this.createPlayerEmbed(player);
                
                // Sempre enviar nova mensagem (limpeza periódica controla a poluição)
                await this.sendDiscordMessage(webhookUrl, embed);
                console.log(`Embed ${needsCleanup ? 'enviado' : 'atualizado'} para ${player.playerName}`);

                // Pequeno delay entre mensagens
                await new Promise(resolve => setTimeout(resolve, 1000));
            }

            console.log('Embeds do Discord atualizados');
        } catch (error) {
            console.error('Erro ao atualizar embeds do Discord:', error);
        }
    }

    async sendDiscordMessage(webhookUrl, embed) {
        try {
            await axios.post(webhookUrl, {
                embeds: [embed]
            });
        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
        }
    }

    createPlayerEmbed(player) {
        const vehicleCount = player.activeVehicles.length;
        const color = vehicleCount > 0 ? 3066993 : 15158332; // Verde se tem veículos, vermelho se não tem

        let vehiclesList = '';
        if (vehicleCount > 0) {
            vehiclesList = player.activeVehicles.map((vehicle, index) => 
                `${index + 1}. \`${vehicle.vehicleId}\` - ${vehicle.vehicleType}`
            ).join('\n');
        } else {
            vehiclesList = '*Todos os veículos foram perdidos*';
        }

        return {
            title: `🚗 Veículos de ${player.playerName}`,
            description: 'Status atual dos seus veículos registrados',
            color: color,
            fields: [
                {
                    name: '📊 Resumo',
                    value: `**Total de Veículos:** ${vehicleCount}\n**Última Atualização:** \`${player.lastUpdated}\``,
                    inline: false
                },
                {
                    name: '🚙 Veículos Ativos',
                    value: vehiclesList,
                    inline: false
                }
            ],
            footer: {
                text: 'SCUM Server Manager • Sistema Individual'
            },
            timestamp: player.lastUpdated
        };
    }

    // Método para executar o controle
    run() {
        console.log('Iniciando controle de veículos...');
        
        // Inicializar com registros atuais (se for primeira execução)
        if (Object.keys(this.playerVehicles).length === 0) {
            this.initializeFromRegistrations();
        }

        // Processar eventos
        this.processVehicleEvents();
    }
}

module.exports = VehicleControl; 