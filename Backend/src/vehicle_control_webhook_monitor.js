const axios = require('axios');
const VehicleControlBot = require('./vehicle_control_bot');
const fs = require('fs');
const path = require('path');

class VehicleControlWebhookMonitor {
    constructor(botClient = null) {
        this.botClient = botClient;
        this.vehicleControl = null;
        this.isRunning = false;
        this.lastProcessedEvent = null;
        this.webhookUrl = null;
        this.checkInterval = null;
    this.autoRecordPath = path.join(__dirname, 'data', 'players', 'vehicle-record-auto.json');
    this.lastAutoRecordMtime = null;
    }

    async start() {
        try {
            if (this.isRunning) {
                console.log('Monitor de webhook de veículos já está rodando');
                return;
            }

            // Carregar configuração do webhook
            const webhooksData = require('fs').readFileSync('./src/data/webhooks.json', 'utf8');
            const webhooks = JSON.parse(webhooksData);
            this.webhookUrl = webhooks.LogVeiculos;

            if (!this.webhookUrl) {
                throw new Error('Webhook LogVeiculos não configurado');
            }

      // Inicializar sistema de controle de veículos
            this.vehicleControl = new VehicleControlBot(this.botClient);
            await this.vehicleControl.run();

            // Iniciar monitoramento
      // Capturar mtime inicial do auto-record
      try {
        if (fs.existsSync(this.autoRecordPath)) {
          this.lastAutoRecordMtime = fs.statSync(this.autoRecordPath).mtimeMs;
        }
      } catch (_) {}

      // Sincronizar inicialmente os embeds a partir do auto-record
      await this.syncEmbedsFromAutoRecord();

      // Sincronização inicial a partir do auto-record, se existir
      await this.syncEmbedsFromAutoRecord();

      this.startMonitoring();

            this.isRunning = true;
            console.log('Monitor de webhook de veículos iniciado');
            
        } catch (error) {
            console.error('Erro ao iniciar monitor de webhook:', error);
            throw error;
        }
    }

    startMonitoring() {
    // Verificar a cada 5 segundos se há novos eventos/alterações
    this.checkInterval = setInterval(async () => {
      await this.checkForNewEvents();
      await this.checkAutoRecordChanges();
    }, 5000);
    }

    async checkForNewEvents() {
        try {
            // Verificar se há novos eventos no arquivo de veículos
            const vehiclesData = require('fs').readFileSync('./src/data/vehicles/vehicles.json', 'utf8');
            const vehicles = JSON.parse(vehiclesData);

            // Encontrar eventos não processados
            const unprocessedEvents = vehicles.filter(event => {
                if (!this.lastProcessedEvent) return true;
                return new Date(event.processedAt) > new Date(this.lastProcessedEvent);
            });

            if (unprocessedEvents.length > 0) {
                console.log(`📡 ${unprocessedEvents.length} novos eventos de veículos detectados`);
                
                // Processar eventos
                for (const event of unprocessedEvents) {
                    await this.processVehicleEvent(event);
                }


                // Atualizar último evento processado
                this.lastProcessedEvent = unprocessedEvents[unprocessedEvents.length - 1].processedAt;
                
                // Atualizar embeds no Discord
                await this.vehicleControl.updateDiscordEmbeds();
                console.log('✅ Embeds atualizados após processamento de eventos');
                
                // O SquadEmbedManager irá detectar automaticamente as mudanças no player_vehicles.json
                // Não precisamos forçar atualização aqui para evitar conflitos
            }
        } catch (error) {
            console.error('Erro ao verificar novos eventos:', error);
        }
    }

    async processVehicleEvent(event) {
        try {
            console.log(`🔄 Processando evento: ${event.event} - Veículo ${event.vehicleId} (${event.vehicleType}) - ${event.ownerName || 'Sem Proprietário'}`);

            // Processar eventos de perda de veículo
            if (['Destroyed', 'Disappeared', 'VehicleInactiveTimerReached'].includes(event.event)) {
                // Buscar proprietário pelo Vehicle ID nos registros; fallback: auto-record
                let ownerSteamId = this.findVehicleOwner(event.vehicleId);
                if (!ownerSteamId) {
                    ownerSteamId = this.findVehicleOwnerInAutoRecord(event.vehicleId);
                }
                
                if (ownerSteamId) {
                    this.vehicleControl.removeVehicleFromPlayer(event.vehicleId, ownerSteamId);
                    console.log(`❌ Veículo ${event.vehicleId} removido de ${ownerSteamId}`);
                } else {
                    console.log(`⚠️ Veículo ${event.vehicleId} não encontrado nos registros`);
                }
      } else if (event.event === 'Registered' || event.event === 'OwnershipClaimed') {
        // Inclusões automáticas: adicionar ao banco vehicle-record-auto
        try {
          const steamId = event.ownerSteamId || event.ownerId || null;
          if (steamId) {
            const player = this.vehicleControl.playerVehicles[steamId] || {
              playerName: event.ownerName || 'Desconhecido',
              steamId,
              activeVehicles: [],
              hasSquad: false,
              squadName: null,
              isLinkedToDiscord: false,
              discordUserId: null,
              lastUpdated: new Date().toISOString()
            };
            if (!player.activeVehicles.find(v => v.vehicleId === String(event.vehicleId))) {
              player.activeVehicles.push({ vehicleId: String(event.vehicleId), vehicleType: event.vehicleType || 'DESCONHECIDO', registeredAt: new Date().toISOString() });
            }
            player.lastUpdated = new Date().toISOString();
            this.vehicleControl.playerVehicles[steamId] = player;
            this.vehicleControl.autoRecord[steamId] = player;
            this.vehicleControl.savePlayerVehicles();
            this.vehicleControl.saveAutoRecord();
            console.log(`✅ Veículo ${event.vehicleId} adicionado para ${steamId}`);
          }
        } catch (e) {
          console.error('Erro ao adicionar veículo por evento:', e.message);
        }
            }

        } catch (error) {
            console.error('Erro ao processar evento de veículo:', error);
        }
    }

    findVehicleOwnerInAutoRecord(vehicleId) {
        try {
            if (!fs.existsSync(this.autoRecordPath)) return null;
            const data = JSON.parse(fs.readFileSync(this.autoRecordPath, 'utf8'));
            const idStr = String(vehicleId);
            for (const [steamId, player] of Object.entries(data)) {
                if (!player || !Array.isArray(player.activeVehicles)) continue;
                const found = player.activeVehicles.find(v => String(v.vehicleId) === idStr);
                if (found) {
                    return steamId;
                }
            }
            return null;
        } catch (error) {
            console.error('Erro ao procurar proprietário no auto-record:', error);
            return null;
        }
    }

    async checkAutoRecordChanges() {
        try {
            if (!fs.existsSync(this.autoRecordPath)) return;
            const mtime = fs.statSync(this.autoRecordPath).mtimeMs;
            if (this.lastAutoRecordMtime && mtime <= this.lastAutoRecordMtime) return;

            await this.syncEmbedsFromAutoRecord();
            this.lastAutoRecordMtime = mtime;
            console.log('✅ Embeds atualizados após mudança no vehicle-record-auto.json');
        } catch (error) {
            console.error('Erro ao checar vehicle-record-auto.json:', error);
        }
    }

    async syncEmbedsFromAutoRecord() {
        try {
            if (!fs.existsSync(this.autoRecordPath)) return;
            const data = JSON.parse(fs.readFileSync(this.autoRecordPath, 'utf8'));
            this.vehicleControl.autoRecord = data;
            this.vehicleControl.playerVehicles = data;
            this.vehicleControl.savePlayerVehicles();
            await this.vehicleControl.updateDiscordEmbeds();
        } catch (error) {
            console.error('Erro ao sincronizar embeds do auto-record:', error);
        }
    }

    findVehicleOwner(vehicleId) {
        try {
            // Carregar registros de veículos
            const registrationsPath = path.join(__dirname, 'data', 'bot', 'vehicle_registrations.json');
            if (!fs.existsSync(registrationsPath)) {
                console.log('⚠️ Arquivo de registros não encontrado');
                return null;
            }
            
            const registrations = JSON.parse(fs.readFileSync(registrationsPath, 'utf8'));
            
            // Procurar o veículo nos registros
            for (const [regId, registration] of Object.entries(registrations)) {
                if (registration.vehicleId === vehicleId.toString()) {
                    console.log(`✅ Veículo ${vehicleId} encontrado nos registros - Proprietário: ${registration.steamId}`);
                    return registration.steamId;
                }
            }
            
            console.log(`❌ Veículo ${vehicleId} não encontrado nos registros`);
            return null;
            
        } catch (error) {
            console.error('Erro ao buscar proprietário do veículo:', error);
            return null;
        }
    }

    async stop() {
        try {
            if (!this.isRunning) {
                console.log('Monitor de webhook não está rodando');
                return;
            }

            if (this.checkInterval) {
                clearInterval(this.checkInterval);
                this.checkInterval = null;
            }

            if (this.vehicleControl) {
                await this.vehicleControl.stop();
                this.vehicleControl = null;
            }

            this.isRunning = false;
            console.log('Monitor de webhook de veículos parado');
            
        } catch (error) {
            console.error('Erro ao parar monitor de webhook:', error);
            throw error;
        }
    }

    getStatus() {
        return {
            isRunning: this.isRunning,
            hasVehicleControl: !!this.vehicleControl,
            hasWebhookUrl: !!this.webhookUrl,
            lastProcessedEvent: this.lastProcessedEvent
        };
    }
}

module.exports = VehicleControlWebhookMonitor; 