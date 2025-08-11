const VehicleControlBot = require('./vehicle_control_bot');

class VehicleControlIntegrationBot {
    constructor(botClient = null) {
        this.vehicleControl = null;
        this.isRunning = false;
        this.interval = null;
        this.botClient = botClient;
    }

    async start() {
        try {
            if (this.isRunning) {
                console.log('Sistema de controle de veículos já está rodando');
                return;
            }

            this.vehicleControl = new VehicleControlBot(this.botClient);
            await this.vehicleControl.run();
            
            // Iniciar processamento periódico
            this.interval = setInterval(async () => {
                // Processar eventos de veículos
                this.vehicleControl.processVehicleEvents();
                
                // Verificar se há novos registros e sincronizar se necessário
                await this.checkForNewRegistrations();
            }, 30000); // Verificar a cada 30 segundos

            this.isRunning = true;
            console.log('Sistema de controle de veículos com bot iniciado');
            
        } catch (error) {
            console.error('Erro ao iniciar sistema de controle de veículos:', error);
            throw error;
        }
    }

    async checkForNewRegistrations() {
        try {
            // Verificar se há novos registros comparando com os dados atuais
            const registrationsData = require('fs').readFileSync(this.vehicleControl.registrationsPath, 'utf8');
            const registrations = JSON.parse(registrationsData);
            
            let hasNewRegistrations = false;
            
            // Verificar se há registros que não estão nos dados atuais
            for (const [vehicleId, registration] of Object.entries(registrations)) {
                const steamId = registration.steamId;
                const player = this.vehicleControl.playerVehicles[steamId];
                
                if (!player || !player.activeVehicles.find(v => v.vehicleId === vehicleId)) {
                    hasNewRegistrations = true;
                    break;
                }
            }
            
            if (hasNewRegistrations) {
                console.log('Novos registros detectados, sincronizando...');
                this.vehicleControl.initializeFromRegistrations();
                this.vehicleControl.processVehicleEvents();
                await this.vehicleControl.updateDiscordEmbeds();
                console.log('Sincronização concluída');
            }
        } catch (error) {
            console.error('Erro ao verificar novos registros:', error);
        }
    }

    async stop() {
        try {
            if (!this.isRunning) {
                console.log('Sistema de controle de veículos não está rodando');
                return;
            }

            if (this.interval) {
                clearInterval(this.interval);
                this.interval = null;
            }

            if (this.vehicleControl) {
                await this.vehicleControl.stop();
                this.vehicleControl = null;
            }

            this.isRunning = false;
            console.log('Sistema de controle de veículos com bot parado');
            
        } catch (error) {
            console.error('Erro ao parar sistema de controle de veículos:', error);
            throw error;
        }
    }

    async forceUpdate() {
        try {
            if (!this.vehicleControl) {
                throw new Error('Sistema não está rodando');
            }

            console.log('Forçando atualização dos embeds...');
            await this.vehicleControl.updateDiscordEmbeds();
            console.log('Atualização forçada concluída');
            
        } catch (error) {
            console.error('Erro ao forçar atualização:', error);
            throw error;
        }
    }

    getStatus() {
        return {
            isRunning: this.isRunning,
            hasVehicleControl: !!this.vehicleControl,
            hasInterval: !!this.interval,
            hasBotClient: !!this.botClient
        };
    }

    async reinitialize() {
        try {
            console.log('Reinicializando sistema de controle de veículos...');
            
            if (this.isRunning) {
                await this.stop();
            }
            
            await this.start();
            console.log('Sistema reinicializado com sucesso');
            
        } catch (error) {
            console.error('Erro ao reinicializar sistema:', error);
            throw error;
        }
    }
}

module.exports = VehicleControlIntegrationBot; 