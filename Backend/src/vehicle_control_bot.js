const fs = require('fs');
const path = require('path');

class VehicleControlBot {
    constructor(botClient = null) {
        this.vehiclesPath = path.join(__dirname, 'data', 'vehicles', 'vehicles.json');
        this.registrationsPath = path.join(__dirname, 'data', 'bot', 'vehicle_registrations.json');
        this.playerVehiclesPath = path.join(__dirname, 'data', 'players', 'player_vehicles.json');
    this.autoRecordPath = path.join(__dirname, 'data', 'players', 'vehicle-record-auto.json');
        this.embedMessagesPath = path.join(__dirname, 'data', 'players', 'embed_messages.json');
        this.configPath = path.join(__dirname, 'data', 'server', 'config.json');
        this.squadsPath = path.join(__dirname, 'data', 'squad', 'squads.json');
        
    this.playerVehicles = this.loadPlayerVehicles();
    this.autoRecord = this.loadAutoRecord();
        this.lastProcessedEvent = this.loadLastProcessedEvent();
        this.embedMessages = this.loadEmbedMessages();
        this.config = this.loadConfig();
        this.squads = this.loadSquads();
        
        // Usar o bot existente ou criar um novo se necessário
        this.client = botClient;
        this.ownClient = null;
        this.eventsTimer = null;
        this.eventsTimerMs = 30000; // 30s para varrer vehicles.json periodicamente
    }

    // Retorna informações de squad para um Steam ID consultando sempre o arquivo atual
    getSquadMembershipForSteamId(steamId) {
        try {
            // Recarregar squads para garantir dados atualizados
            this.squads = this.loadSquads();
            const squadsRoot = this.squads && this.squads.squads ? this.squads.squads : {};
            for (const squadId in squadsRoot) {
                const squad = squadsRoot[squadId];
                if (!squad || !Array.isArray(squad.members)) continue;
                const member = squad.members.find(m => String(m.steam_id) === String(steamId));
                if (member) {
                    return {
                        hasSquad: true,
                        squadName: squad.name || null,
                        displayName: member.name || null
                    };
                }
            }
            return { hasSquad: false, squadName: null, displayName: null };
        } catch (error) {
            console.error('Erro ao consultar squads.json para membership:', error);
            return { hasSquad: false, squadName: null, displayName: null };
        }
    }

    // Formata ISO (ex.: 2025-08-09T14:27:51.548Z) para DD/MM/YYYY HH:MM:SS em pt-BR
    formatBrazilianDateTime(isoString) {
        try {
            if (!isoString) return '';
            const d = new Date(isoString);
            if (isNaN(d.getTime())) return String(isoString);
            return d.toLocaleString('pt-BR', {
                timeZone: 'America/Sao_Paulo',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        } catch (_) {
            return String(isoString);
        }
    }

    // Normaliza o nome do veículo para exibição (remove sufixos e padroniza capitalização)
    normalizeVehicleDisplayName(rawName) {
        try {
            if (!rawName) return 'DESCONHECIDO';
            let s = String(rawName);
            // Remover prefixes/sufixos conhecidos e underscores
            s = s.replace('Vehicle:BPC_', '');
            s = s.replace(/^BPC_/i, '');
            s = s.replace(/_ES$/i, '');
            s = s.replace(/_/g, ' ');
            // Remover frases como "Item Container"
            s = s.replace(/item\s*container/ig, '');
            s = s.replace(/\s+/g, ' ').trim();
            if (!s) return 'DESCONHECIDO';

            const normalizedLower = s.toLowerCase();
            const dictionary = {
                'wolfswagen': 'WolfsWagen',
                'rager': 'Rager',
                'laika': 'Laika',
                'cruiser': 'Cruiser',
                'dirtbike': 'Dirtbike',
                'tractor': 'Tractor',
                'kinglet mariner': 'Kinglet Mariner',
                'kinglet duster': 'Kinglet Duster',
                'ris': 'RIS'
            };
            if (dictionary[normalizedLower]) return dictionary[normalizedLower];

            // Title Case, preservando siglas comuns
            const preserveUpper = new Set(['RIS']);
            return s.split(' ').map(word => {
                const upper = word.toUpperCase();
                if (preserveUpper.has(upper)) return upper;
                return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
            }).join(' ');
        } catch (_) {
            return String(rawName);
        }
    }

    // Busca o nome do veículo real no banco de dados
    async getVehicleRealName(vehicleId) {
        try {
            const sqlite3 = require('sqlite3').verbose();
            const dbPath = process.env.SCUM_DB_PATH || 'C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db';
            const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY);
            
            return new Promise((resolve) => {
                db.all(`SELECT e.id as container_id, e.class as container_class, e.parent_entity_id as vehicle_id, 
                        v.class as vehicle_class, vs.vehicle_asset_id 
                        FROM entity e 
                        LEFT JOIN entity v ON v.id = e.parent_entity_id 
                        LEFT JOIN vehicle_spawner vs ON vs.vehicle_entity_id = e.parent_entity_id 
                        WHERE e.id = ?`, [vehicleId], (err, rows) => {
                    db.close();
                    if (err || !rows || rows.length === 0) {
                        resolve(null);
                    } else {
                        const row = rows[0];
                        // Se tem vehicle_id, é um container vinculado a um veículo
                        if (row.vehicle_id) {
                            resolve({
                                name: this.normalizeVehicleDisplayName(row.vehicle_class || row.vehicle_asset_id),
                                vehicleId: row.vehicle_id
                            });
                        } else {
                            // É um container sem veículo vinculado
                            resolve({
                                name: this.normalizeVehicleDisplayName(row.container_class),
                                vehicleId: row.container_id
                            });
                        }
                    }
                });
            });
        } catch (error) {
            console.error('Erro ao buscar nome real do veículo:', error);
            return null;
        }
    }

    loadConfig() {
        try {
            const data = fs.readFileSync(this.configPath, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            console.error('Erro ao carregar configuração:', error);
            return null;
        }
    }

    loadSquads() {
        try {
            const data = fs.readFileSync(this.squadsPath, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            console.error('Erro ao carregar squads:', error);
            return { squads: {} };
        }
    }

    getPlayerNameFromSquads(steamId) {
        try {
            // Procurar o jogador nos squads
            for (const squadId in this.squads.squads) {
                const squad = this.squads.squads[squadId];
                if (squad.members) {
                    const member = squad.members.find(m => m.steam_id === steamId);
                    if (member) {
                        return member.name; // Retorna o nome correto do squads.json
                    }
                }
            }
            return null; // Jogador não encontrado nos squads
        } catch (error) {
            console.error('Erro ao buscar nome do jogador nos squads:', error);
            return null;
        }
    }

    formatPlayerName(steamId, discordUsername) {
        // Buscar nome correto do squads.json
        const squadName = this.getPlayerNameFromSquads(steamId);
        
        if (squadName) {
            // Jogador encontrado no squad
            return {
                name: squadName,
                hasSquad: true,
                squadName: squadName // Adicionado para compatibilidade
            };
        } else {
            // Jogador não encontrado no squad - usar nome em maiúsculo
            const upperName = discordUsername.toUpperCase();
            return {
                name: upperName,
                hasSquad: false,
                squadName: null // Adicionado para compatibilidade
            };
        }
    }

    checkDiscordLink(steamId, linkedUsers) {
        try {
            // Verificar se o Steam ID está vinculado a algum usuário do Discord
            for (const discordUserId in linkedUsers) {
                const linkedUser = linkedUsers[discordUserId];
                if (linkedUser.steam_id === steamId) {
                    return true;
                }
            }
            return false;
        } catch (error) {
            console.error('Erro ao verificar vinculação Discord:', error);
            return false;
        }
    }

    getDiscordUserId(steamId, linkedUsers) {
        try {
            // Encontrar o Discord User ID para o Steam ID
            for (const discordUserId in linkedUsers) {
                const linkedUser = linkedUsers[discordUserId];
                if (linkedUser.steam_id === steamId) {
                    return discordUserId;
                }
            }
            return null;
        } catch (error) {
            console.error('Erro ao obter Discord User ID:', error);
            return null;
        }
    }

    loadLinkedUsers() {
        try {
            const linkedUsersPath = path.join(__dirname, 'data', 'bot', 'linked_users.json');
            if (!fs.existsSync(linkedUsersPath)) return {};
            const data = fs.readFileSync(linkedUsersPath, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            console.error('Erro ao carregar linked_users.json:', error);
            return {};
        }
    }

    loadPlayerVehicles() {
        try {
            if (fs.existsSync(this.playerVehiclesPath)) {
                const data = fs.readFileSync(this.playerVehiclesPath, 'utf8');
                return JSON.parse(data);
            } else {
                console.log('📁 Criando arquivo player_vehicles.json...');
                return {};
            }
        } catch (error) {
            console.error('Erro ao carregar player_vehicles:', error);
            return {};
        }
    }

    loadEmbedMessages() {
        try {
            if (fs.existsSync(this.embedMessagesPath)) {
                const data = fs.readFileSync(this.embedMessagesPath, 'utf8');
                return JSON.parse(data);
            } else {
                console.log('📁 Criando arquivo embed_messages.json...');
                return {};
            }
        } catch (error) {
            console.error('Erro ao carregar embed_messages:', error);
            return {};
        }
    }

    loadAutoRecord() {
        try {
            if (fs.existsSync(this.autoRecordPath)) {
                const data = fs.readFileSync(this.autoRecordPath, 'utf8');
                return JSON.parse(data);
            } else {
                return {};
            }
        } catch (error) {
            console.error('Erro ao carregar vehicle-record-auto:', error);
            return {};
        }
    }

    saveAutoRecord() {
        try {
            const dir = path.dirname(this.autoRecordPath);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            fs.writeFileSync(this.autoRecordPath, JSON.stringify(this.autoRecord, null, 2));
        } catch (error) {
            console.error('Erro ao salvar vehicle-record-auto:', error);
        }
    }

    saveEmbedMessages() {
        try {
            fs.writeFileSync(this.embedMessagesPath, JSON.stringify(this.embedMessages, null, 2));
        } catch (error) {
            console.error('Erro ao salvar embed_messages:', error);
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

    async initializeBot() {
        if (this.client) {
            console.log('Usando bot existente');
            return;
        }

        // Criar novo bot apenas se necessário
        const { Client, GatewayIntentBits } = require('discord.js');
        this.ownClient = new Client({
            intents: [
                GatewayIntentBits.Guilds,
                GatewayIntentBits.GuildMessages,
                GatewayIntentBits.MessageContent
            ]
        });

        this.ownClient.on('ready', () => {
            console.log(`Bot de controle de veículos conectado como ${this.ownClient.user.tag}`);
        });

        this.ownClient.on('error', (error) => {
            console.error('Erro no bot de controle de veículos:', error);
        });

        try {
            await this.ownClient.login(this.config.discord_bot.token);
            this.client = this.ownClient;
        } catch (error) {
            console.error('Erro ao conectar bot de controle de veículos:', error);
            throw error;
        }
    }

    async stopBot() {
        if (this.ownClient) {
            try {
                await this.ownClient.destroy();
                this.ownClient = null;
                this.client = null;
            } catch (error) {
                console.error('Erro ao desconectar bot:', error);
            }
        }
    }

    async initializeFromRegistrations() {
        try {
            console.log('🔄 Inicializando sistema de controle de veículos...');
            
            // Carregar registros de veículos
            const registrationsPath = path.join(__dirname, 'data', 'bot', 'vehicle_registrations.json');
            if (!fs.existsSync(registrationsPath)) {
                console.log('⚠️ Arquivo de registros não encontrado');
                return;
            }
            
            const registrations = JSON.parse(fs.readFileSync(registrationsPath, 'utf8'));
            console.log(`📋 ${Object.keys(registrations).length} registros encontrados`);
            
            // Carregar eventos de veículos para verificar status
            const vehiclesPath = path.join(__dirname, 'data', 'vehicles', 'vehicles.json');
            let vehicleEvents = [];
            if (fs.existsSync(vehiclesPath)) {
                vehicleEvents = JSON.parse(fs.readFileSync(vehiclesPath, 'utf8'));
                console.log(`📊 ${vehicleEvents.length} eventos de veículos carregados`);
            }
            
            // Carregar usuários vinculados ao Discord
            const linkedUsersPath = path.join(__dirname, 'data', 'bot', 'linked_users.json');
            let linkedUsers = {};
            if (fs.existsSync(linkedUsersPath)) {
                linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
                console.log(`🔗 ${Object.keys(linkedUsers).length} usuários vinculados ao Discord`);
            }
            
            // Criar mapa de veículos destruídos/desaparecidos
            const destroyedVehicles = new Set();
            const disappearedVehicles = new Set();
            const inactiveVehicles = new Set();
            
            vehicleEvents.forEach(event => {
                if (['Destroyed', 'Disappeared', 'VehicleInactiveTimerReached'].includes(event.event)) {
                    destroyedVehicles.add(event.vehicleId);
                    if (event.event === 'Disappeared') {
                        disappearedVehicles.add(event.vehicleId);
                    } else if (event.event === 'VehicleInactiveTimerReached') {
                        inactiveVehicles.add(event.vehicleId);
                    }
                }
            });
            
            console.log(`❌ ${destroyedVehicles.size} veículos destruídos/desaparecidos detectados`);
            
            // Processar registros e verificar status
      const playerVehicles = {};
            
            // Validar veículos no banco antes de montar a lista
            const { validateVehicleIds } = require('../scripts/vehicle_database_query');
            const allIds = Object.values(registrations).map(r => r.vehicleId);
            const validationMap = await validateVehicleIds(allIds);

            Object.values(registrations).forEach(registration => {
                const vehicleId = registration.vehicleId;
                const steamId = registration.steamId;
                
                // Pular veículos que não existem mais no banco
                if (validationMap && validationMap[vehicleId] === false) {
                    console.log(`🚫 ID ${vehicleId} não encontrado no banco – ignorando registro (${registration.vehicleType})`);
                    return;
                }

                // Verificar se o veículo foi destruído/desaparecido
                if (destroyedVehicles.has(vehicleId)) {
                    console.log(`🚫 Veículo ${vehicleId} (${registration.vehicleType}) foi destruído/desaparecido - IGNORANDO`);
                    return; // Pular este veículo
                }
                
                // Verificar se já existe entrada para este jogador
                if (!playerVehicles[steamId]) {
                    const { name, hasSquad, squadName } = this.formatPlayerName(steamId, registration.discordUsername);
                    
                    // Verificar se o jogador está vinculado ao Discord
                    const isLinkedToDiscord = this.checkDiscordLink(steamId, linkedUsers);
                    
                    playerVehicles[steamId] = {
                        playerName: name,
                        steamId: steamId,
                        activeVehicles: [],
                        hasSquad: hasSquad,
                        squadName: squadName,
                        isLinkedToDiscord: isLinkedToDiscord,
                        discordUserId: isLinkedToDiscord ? this.getDiscordUserId(steamId, linkedUsers) : null,
                        lastUpdated: new Date().toISOString()
                    };
                }
                
                // Adicionar veículo à lista do jogador
                playerVehicles[steamId].activeVehicles.push({
                    vehicleId: vehicleId,
                    vehicleType: registration.vehicleType,
                    registeredAt: registration.registeredAt
                });
                
                console.log(`✅ Veículo ${vehicleId} (${registration.vehicleType}) adicionado para ${playerVehicles[steamId].playerName}`);
            });
            
      // Persistir também no banco automático e usar como fonte primária
      this.autoRecord = playerVehicles;
      this.saveAutoRecord();
      this.playerVehicles = this.autoRecord;
            
            // Salvar dados atualizados
            const playerVehiclesPath = path.join(__dirname, 'data', 'players', 'player_vehicles.json');
      fs.writeFileSync(playerVehiclesPath, JSON.stringify(playerVehicles, null, 2));
            
            console.log(`📊 Sistema inicializado com ${Object.keys(playerVehicles).length} jogadores`);
            console.log(`🚗 Total de veículos ativos: ${Object.values(playerVehicles).reduce((total, player) => total + player.activeVehicles.length, 0)}`);
            
        } catch (error) {
            console.error('❌ Erro ao inicializar sistema:', error);
            throw error;
        }
    }

    processVehicleEvents() {
        try {
            if (!fs.existsSync(this.vehiclesPath)) {
                return;
            }
            const vehiclesData = fs.readFileSync(this.vehiclesPath, 'utf8');
            const vehicles = JSON.parse(vehiclesData);

            let processedCount = 0;

            for (const event of vehicles) {
                // Verificar se já foi processado (usando processedAt)
                if (this.lastProcessedEvent.lastProcessedAt && 
                    new Date(event.processedAt) <= new Date(this.lastProcessedEvent.lastProcessedAt)) {
                    continue;
                }

                // Processar eventos de perda de veículo
                if (['Destroyed', 'Disappeared', 'VehicleInactiveTimerReached'].includes(event.event)) {
                    console.log(`Processando evento: ${event.event} para veículo ${event.vehicleId}`);
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
            
            // SALVAR MUDANÇAS NO ARQUIVO
            this.savePlayerVehicles();
      // manter autoRecord alinhado
      this.autoRecord[steamId] = this.playerVehicles[steamId];
      this.saveAutoRecord();
            console.log(`💾 Mudanças salvas no arquivo para ${player.playerName}`);
        }
    }

    async updateDiscordEmbeds() {
        try {
            if (!this.client) {
                console.error('Bot não está conectado');
                return;
            }

            const channelId = this.config.discord_bot.channels.vehicle_control;
            const channel = await this.client.channels.fetch(channelId);
            
            if (!channel) {
                console.error('Canal de controle de veículos não encontrado');
                return;
            }

            // Criar embeds para cada jogador
            for (const [steamId, player] of Object.entries(this.playerVehicles)) {
                const embed = await this.createPlayerEmbed(player);
                
                // Verificar se já existe uma mensagem para este jogador
                if (this.embedMessages[steamId] && this.embedMessages[steamId].messageId) {
                    // Tentar editar a mensagem existente
                    try {
                        const message = await channel.messages.fetch(this.embedMessages[steamId].messageId);
                        await message.edit({ embeds: [embed] });
                        console.log(`Embed editado para ${player.playerName}`);
                    } catch (error) {
                        console.log(`Erro ao editar embed para ${player.playerName}, enviando novo...`);
                        await this.sendNewMessage(channel, steamId, embed);
                    }
                } else {
                    // Enviar nova mensagem
                    await this.sendNewMessage(channel, steamId, embed);
                }

                // Pequeno delay entre mensagens
                await new Promise(resolve => setTimeout(resolve, 1000));
            }

            console.log('Embeds do Discord atualizados');
            
            // O SquadEmbedManager irá detectar automaticamente as mudanças no player_vehicles.json
            // Não precisamos forçar atualização aqui para evitar conflitos
        } catch (error) {
            console.error('Erro ao atualizar embeds do Discord:', error);
        }
    }

    async sendNewMessage(channel, steamId, embed) {
        try {
            const message = await channel.send({ embeds: [embed] });
            
            // Salvar o ID da mensagem para edições futuras
            this.embedMessages[steamId] = {
                messageId: message.id,
                lastUpdated: new Date().toISOString()
            };
            this.saveEmbedMessages();
            console.log(`Nova mensagem enviada para ${this.playerVehicles[steamId].playerName}`);
        } catch (error) {
            console.error('Erro ao enviar nova mensagem:', error);
        }
    }

    async createPlayerEmbed(player) {
        const { EmbedBuilder } = require('discord.js');
        
        // Determinar vínculo do Discord no momento da renderização (enriquece auto-record)
        const linkedUsers = this.loadLinkedUsers();
        const isLinkedDynamic = this.checkDiscordLink(player.steamId, linkedUsers);
        const discordUserIdDynamic = isLinkedDynamic ? this.getDiscordUserId(player.steamId, linkedUsers) : null;

        const vehicleCount = player.activeVehicles.length;
        const color = vehicleCount > 0 ? 3066993 : 15158332; // Verde se tem veículos, vermelho se não tem

        // Determinar squad dinamicamente a partir do squads.json
        const membership = this.getSquadMembershipForSteamId(player.steamId);
        const effectivePlayerName = membership.displayName || player.playerName;

        // Definir título baseado no status do squad (dinâmico)
        let title = '';
        if (membership.hasSquad) {
            title = `🚗 Veículos de ${effectivePlayerName}`;
        } else {
            title = `🚗 Veículos de ${effectivePlayerName} (SEM SQUAD)`;
        }

        let vehiclesList = '';
        if (vehicleCount > 0) {
            // Aguardar todas as consultas de nomes reais
            const vehiclePromises = player.activeVehicles.map(async (vehicle, index) => {
                const vehicleInfo = await this.getVehicleRealName(vehicle.vehicleId);
                if (vehicleInfo) {
                    return `${index + 1}. \`${vehicleInfo.vehicleId}\` - ${vehicleInfo.name}`;
                } else {
                    const displayName = this.normalizeVehicleDisplayName(vehicle.vehicleType);
                    return `${index + 1}. \`${vehicle.vehicleId}\` - ${displayName}`;
                }
            });
            vehiclesList = (await Promise.all(vehiclePromises)).join('\n');
        } else {
            vehiclesList = '*Todos os veículos foram perdidos*';
        }

        // Definir cor baseada no status do squad
        let embedColor = color;
        if (!membership.hasSquad) {
            embedColor = 16776960; // Amarelo para jogadores sem squad
        }

        // Criar campos do embed
        const fields = [
            {
                name: '📊 Resumo',
                value: `**Total de Veículos:** ${vehicleCount}\n**Última Atualização:** \`${this.formatBrazilianDateTime(player.lastUpdated)}\``,
                inline: false
            }
        ];

        // Adicionar informação de vinculação do Discord (usa detecção dinâmica)
        if (isLinkedDynamic) {
            fields.push({
                name: '🔗 Discord',
                value: `✅ **Vinculado ao Discord**\n<@${discordUserIdDynamic}>`,
                inline: true
            });
        } else {
            fields.push({
                name: '🔗 Discord',
                value: `❌ **Não vinculado ao Discord**`,
                inline: true
            });
        }

        // Adicionar informação do squad (dinâmico)
        if (membership.hasSquad) {
            fields.push({
                name: '👥 Squad',
                value: `✅ **${membership.squadName}**`,
                inline: true
            });
        } else {
            fields.push({
                name: '👥 Squad',
                value: `❌ **SEM SQUAD**`,
                inline: true
            });
        }

        // Adicionar lista de veículos
        fields.push({
            name: '🚙 Veículos Ativos',
            value: vehiclesList,
            inline: false
        });

        return new EmbedBuilder()
            .setTitle(title)
            .setDescription('Status atual dos seus veículos registrados')
            .setColor(embedColor)
            .addFields(fields)
            .setFooter({
                text: membership.hasSquad ? 'SCUM Server Manager • Sistema Individual' : 'SCUM Server Manager • Jogador Sem Squad'
            })
            .setTimestamp(new Date(player.lastUpdated));
    }

    // Método para executar o controle
    async run() {
        console.log('Iniciando controle de veículos com bot...');
        
        // Inicializar bot se necessário
        await this.initializeBot();
        
        // Aguardar bot estar pronto (se for próprio cliente)
        if (this.ownClient) {
            await new Promise(resolve => {
                this.ownClient.once('ready', resolve);
            });
        }
        
        // Inicializar com registros atuais (se for primeira execução)
        if (Object.keys(this.playerVehicles).length === 0) {
            await this.initializeFromRegistrations();
            // Após inicializar, enviar embeds iniciais
            await this.updateDiscordEmbeds();
        } else {
            // Se já tem dados, apenas processar eventos
            this.processVehicleEvents();
        }

        // Iniciar varredura periódica de eventos do arquivo vehicles.json
        if (!this.eventsTimer) {
            this.eventsTimer = setInterval(() => {
                try {
                    this.processVehicleEvents();
                } catch (e) {
                    console.error('Erro no timer de eventos de veículos:', e);
                }
            }, this.eventsTimerMs);
        }
    }

    // Método para parar o controle
    async stop() {
        await this.stopBot();
        if (this.eventsTimer) {
            clearInterval(this.eventsTimer);
            this.eventsTimer = null;
        }
    }
}

module.exports = VehicleControlBot; 