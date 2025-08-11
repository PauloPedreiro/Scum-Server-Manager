const fs = require('fs');
const path = require('path');
const { EmbedBuilder } = require('discord.js');

class SquadEmbedManager {
    constructor(discordClient) {
        this.client = discordClient;
        this.config = this.loadConfig();
        this.squadsData = this.loadSquadsData();
        this.playerVehiclesPath = path.join(__dirname, 'data', 'players', 'vehicle-record-auto.json');
        this.lastPlayerVehiclesHash = null;
        this.monitoringInterval = null;
        
        // Iniciar monitoramento contínuo
        this.startContinuousMonitoring();
    }

    // Normaliza o nome do veículo para exibição/agrupamento (remove sufixos e padroniza)
    normalizeVehicleDisplayName(rawName) {
        try {
            if (!rawName) return 'DESCONHECIDO';
            let s = String(rawName);
            s = s.replace('Vehicle:BPC_', '');
            s = s.replace(/^BPC_/i, '');
            s = s.replace(/_ES$/i, '');
            s = s.replace(/_/g, ' ');
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

    loadConfig() {
        const configPath = path.join(__dirname, 'data', 'server', 'config.json');
        return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }

    loadSquadsData() {
        const squadsPath = path.join(__dirname, 'data', 'squad', 'squads.json');
        try {
            if (fs.existsSync(squadsPath)) {
                return JSON.parse(fs.readFileSync(squadsPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar dados dos squads:', error.message);
        }
        return { squads: {} };
    }

    saveSquadsData() {
        const squadsPath = path.join(__dirname, 'data', 'squad', 'squads.json');
        fs.writeFileSync(squadsPath, JSON.stringify(this.squadsData, null, 2));
    }

    // SISTEMA DE MONITORAMENTO CONTÍNUO
    startContinuousMonitoring() {
        console.log('🔄 Iniciando monitoramento contínuo dos veículos...');
        
        // Verificar a cada 30 segundos se houve mudanças no vehicle-record-auto.json
        this.monitoringInterval = setInterval(async () => {
            await this.checkForVehicleChanges();
        }, 30000); // 30 segundos
        
        console.log('✅ Monitoramento contínuo iniciado (verificação a cada 30s)');
    }

    async checkForVehicleChanges() {
        try {
            console.log('🔍 Verificando mudanças nos veículos...');
            
            // Verificar se o arquivo vehicle-record-auto.json existe
            if (!fs.existsSync(this.playerVehiclesPath)) {
                console.log('❌ Arquivo vehicle-record-auto.json não encontrado');
                return;
            }

            // Ler o arquivo atual
            const currentData = fs.readFileSync(this.playerVehiclesPath, 'utf8');
            const currentHash = this.generateHash(currentData);
            const currentTimestamp = fs.statSync(this.playerVehiclesPath).mtime.getTime();
            
            console.log(`📊 Hash atual: ${currentHash}`);
            console.log(`📊 Hash anterior: ${this.lastPlayerVehiclesHash}`);
            console.log(`📊 Timestamp atual: ${new Date(currentTimestamp).toISOString()}`);
            console.log(`📊 Timestamp anterior: ${this.lastFileTimestamp ? new Date(this.lastFileTimestamp).toISOString() : 'NENHUM'}`);

            // Se é a primeira verificação, apenas salvar o hash
            if (this.lastPlayerVehiclesHash === null) {
                this.lastPlayerVehiclesHash = currentHash;
                this.lastFileTimestamp = currentTimestamp;
                console.log('📋 Hash inicial dos veículos salvo');
                
                // Forçar atualização inicial dos squads
                console.log('🔄 Forçando atualização inicial dos squads...');
                await this.forceUpdateSquads();
                return;
            }

            // Verificar se houve mudanças (hash ou timestamp)
            const hashChanged = currentHash !== this.lastPlayerVehiclesHash;
            const timestampChanged = currentTimestamp !== this.lastFileTimestamp;
            
            if (hashChanged || timestampChanged) {
                console.log('🔄 Mudanças detectadas no player_vehicles.json!');
                console.log(`📊 Hash mudou: ${hashChanged}`);
                console.log(`📊 Timestamp mudou: ${timestampChanged}`);
                console.log('📊 Atualizando embeds dos squads automaticamente...');
                
                // Atualizar hash e timestamp
                this.lastPlayerVehiclesHash = currentHash;
                this.lastFileTimestamp = currentTimestamp;
                
                // Forçar atualização dos squads
                await this.forceUpdateSquads();
                
            } else {
                console.log('✅ Nenhuma mudança detectada nos veículos');
                
                // FORÇAR ATUALIZAÇÃO MESMO SEM MUDANÇAS (a cada 5 verificações)
                this.forceUpdateCounter = (this.forceUpdateCounter || 0) + 1;
                if (this.forceUpdateCounter >= 5) {
                    console.log('🔄 Forçando atualização periódica dos squads...');
                    await this.forceUpdateSquads();
                    this.forceUpdateCounter = 0;
                }
            }

        } catch (error) {
            console.error('❌ Erro no monitoramento contínuo:', error.message);
        }
    }

    generateHash(data) {
        // Hash simples baseado no conteúdo
        let hash = 0;
        for (let i = 0; i < data.length; i++) {
            const char = data.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return hash.toString();
    }

    async forceUpdateSquads() {
        try {
            console.log('🔄 Forçando atualização dos squads...');
            
            // SEMPRE verificar mudanças no player_vehicles.json antes de atualizar
            console.log('🔍 Verificando mudanças no vehicle-record-auto.json...');
            
            if (fs.existsSync(this.playerVehiclesPath)) {
                const currentData = fs.readFileSync(this.playerVehiclesPath, 'utf8');
                const currentHash = this.generateHash(currentData);
                const currentTimestamp = fs.statSync(this.playerVehiclesPath).mtime.getTime();
                
                console.log(`📊 Hash atual: ${currentHash}`);
                console.log(`📊 Hash anterior: ${this.lastPlayerVehiclesHash}`);
                
                // Atualizar hash e timestamp
                this.lastPlayerVehiclesHash = currentHash;
                this.lastFileTimestamp = currentTimestamp;
            }
            
            // Obter dados atualizados dos squads
            const SquadsManager = require('./squads');
            const squadsManager = new SquadsManager();
            const currentSquads = await squadsManager.getSquadsData();
            
            // Atualizar embeds
            await this.updateSquads(currentSquads);
            
            console.log('✅ Squads atualizados automaticamente');
            
        } catch (error) {
            console.error('❌ Erro ao forçar atualização dos squads:', error.message);
        }
    }

    stopContinuousMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
            console.log('🛑 Monitoramento contínuo parado');
        }
    }

    // Método para parar completamente o SquadEmbedManager
    async stop() {
        this.stopContinuousMonitoring();
        console.log('🛑 SquadEmbedManager parado');
    }

    // Função para verificar se usuário está vinculado ao Discord
    checkDiscordLink(steamId) {
        try {
            const linkedUsersPath = path.join(__dirname, 'data', 'bot', 'linked_users.json');
            if (!fs.existsSync(linkedUsersPath)) {
                return null;
            }
            
            const linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            
            // Procurar pelo Steam ID nos usuários vinculados
            for (const [discordId, userData] of Object.entries(linkedUsers)) {
                if (userData.steam_id === steamId) {
                    return {
                        discordId: discordId,
                        linkedAt: userData.linked_at,
                        permissions: userData.permissions || []
                    };
                }
            }
            
            return null;
        } catch (error) {
            console.error('Erro ao verificar usuário vinculado:', error.message);
            return null;
        }
    }

    // Função para buscar veículos dos jogadores do squad
    getSquadVehicles(squad) {
        try {
            const playerVehiclesPath = path.join(__dirname, 'data', 'players', 'vehicle-record-auto.json');
            if (!fs.existsSync(playerVehiclesPath)) {
                console.log('❌ Arquivo vehicle-record-auto.json não encontrado');
                return {};
            }
            
            const playerVehicles = JSON.parse(fs.readFileSync(playerVehiclesPath, 'utf8'));
            const squadVehicles = {};
            
            console.log(`🔍 Verificando veículos para squad: ${squad.name}`);
            console.log(`👥 Membros do squad: ${squad.members.length}`);
            
            // Para cada membro do squad
            squad.members.forEach(member => {
                const steamId = member.steam_id;
                console.log(`🔍 Verificando membro: ${member.name} (${steamId})`);
                
                // Buscar veículos do jogador
                if (playerVehicles[steamId] && playerVehicles[steamId].activeVehicles) {
                    console.log(`✅ Jogador ${member.name} tem ${playerVehicles[steamId].activeVehicles.length} veículos`);
                    
                    playerVehicles[steamId].activeVehicles.forEach(vehicle => {
                        const prettyType = this.normalizeVehicleDisplayName(vehicle.vehicleType);
                        console.log(`🚗 Veículo encontrado: ${prettyType} (ID: ${vehicle.vehicleId})`);
                        if (!squadVehicles[prettyType]) {
                            squadVehicles[prettyType] = 0;
                        }
                        squadVehicles[prettyType]++;
                    });
                } else {
                    console.log(`❌ Jogador ${member.name} não tem veículos registrados`);
                }
            });
            
            console.log(`📊 Veículos do squad ${squad.name}:`, squadVehicles);
            return squadVehicles;
        } catch (error) {
            console.error('❌ Erro ao buscar veículos do squad:', error.message);
            return {};
        }
    }

    createSquadEmbed(squad) {
        const embed = new EmbedBuilder()
            .setTitle(`🏆 Squad: ${squad.name}`)
            .setColor(0x00ff88)
            .addFields(
                {
                    name: '👥 Membros',
                    value: `${squad.members.length}/${squad.member_limit || '∞'}`,
                    inline: true
                },
                {
                    name: '🏆 Score',
                    value: squad.score ? squad.score.toFixed(0) : '0',
                    inline: true
                }
            )
            .setTimestamp();

        // Adicionar informações do squad se houver
        if (squad.message) {
            embed.addFields({
                name: '💬 Mensagem',
                value: squad.message.length > 1024 ? squad.message.substring(0, 1021) + '...' : squad.message,
                inline: false
            });
        }

        if (squad.information) {
            embed.addFields({
                name: 'ℹ️ Informações',
                value: squad.information.length > 1024 ? squad.information.substring(0, 1021) + '...' : squad.information,
                inline: false
            });
        }

        // Adicionar lista de membros se houver
        if (squad.members.length > 0) {
            const memberList = squad.members
                .sort((a, b) => b.rank - a.rank) // Ordenar por rank (maior primeiro)
                .map(member => {
                    const rankEmoji = member.rank === 1 ? '👑' : member.rank === 2 ? '⚔️' : '🛡️';
                    
                    // Verificar se usuário está vinculado ao Discord
                    const discordLink = this.checkDiscordLink(member.steam_id);
                    const discordInfo = discordLink ? `✅ (<@${discordLink.discordId}>)` : `❌`;
                    
                    return `${rankEmoji} ${member.name} (Rank: ${member.rank}) - Discord: ${discordInfo}`;
                })
                .join('\n');
            
            embed.addFields({
                name: '📋 Lista de Membros',
                value: memberList.length > 1024 ? memberList.substring(0, 1021) + '...' : memberList,
                inline: false
            });
        }

        // Adicionar veículos do squad
        const squadVehicles = this.getSquadVehicles(squad);
        if (Object.keys(squadVehicles).length > 0) {
            const vehicleList = Object.entries(squadVehicles)
                .map(([type, count], index) => `${index + 1} - ${type} (${count})`)
                .join('\n');
            
            embed.addFields({
                name: '🚗 Veículos do Squad',
                value: vehicleList,
                inline: false
            });
        } else {
            embed.addFields({
                name: '🚗 Veículos do Squad',
                value: 'Nenhum veículo registrado',
                inline: false
            });
        }

        return embed;
    }

    async getSquadsChannel() {
        // Aguardar até que o bot esteja pronto
        let attempts = 0;
        const maxAttempts = 10;
        
        while (attempts < maxAttempts) {
            try {
                const guild = this.client.guilds.cache.get(this.config.discord_bot.guild_id);
                if (!guild) {
                    console.log(`Tentativa ${attempts + 1}: Aguardando bot conectar...`);
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    attempts++;
                    continue;
                }

                const channelId = this.config.discord_bot.channels.squads;
                const channel = guild.channels.cache.get(channelId);
                
                if (!channel) {
                    throw new Error(`Canal de squads não encontrado: ${channelId}`);
                }

                console.log(`✅ Bot conectado ao servidor: ${guild.name}`);
                console.log(`✅ Canal encontrado: ${channel.name}`);
                return channel;
            } catch (error) {
                console.log(`Tentativa ${attempts + 1}: ${error.message}`);
                await new Promise(resolve => setTimeout(resolve, 1000));
                attempts++;
            }
        }
        
        throw new Error('Bot não conseguiu conectar ao servidor Discord após várias tentativas');
    }

    async updateSquadEmbed(squad, messageId = null) {
        try {
            console.log(`🔄 Atualizando embed do squad: ${squad.name}`);
            const channel = await this.getSquadsChannel();
            const embed = this.createSquadEmbed(squad);
            
            console.log(`📊 Embed criado para ${squad.name}:`, {
                title: embed.data.title,
                fields: embed.data.fields?.length || 0,
                hasVehicles: embed.data.fields?.some(f => f.name === '🚗 Veículos do Squad' && f.value !== 'Nenhum veículo registrado')
            });
            
            if (messageId) {
                // Editar embed existente
                console.log(`📝 Editando mensagem existente: ${messageId}`);
                const message = await channel.messages.fetch(messageId);
                await message.edit({ embeds: [embed] });
                console.log(`✅ Embed do squad ${squad.name} atualizado com sucesso`);
            } else {
                // Criar novo embed
                console.log(`📝 Criando nova mensagem`);
                const message = await channel.send({ embeds: [embed] });
                console.log(`✅ Novo embed criado para squad ${squad.name} com ID: ${message.id}`);
                return message.id; // Retornar ID para salvar
            }
        } catch (error) {
            console.error(`❌ Erro ao atualizar embed do squad ${squad.name}:`, error.message);
            
            // Tentar enviar mesmo com erro (forçar envio)
            try {
                console.log(`🔄 Tentando envio forçado para ${squad.name}...`);
                const channel = await this.getSquadsChannel();
                const embed = this.createSquadEmbed(squad);
                const message = await channel.send({ embeds: [embed] });
                console.log(`✅ Embed do squad ${squad.name} enviado com sucesso (forçado)`);
                return message.id;
            } catch (forceError) {
                console.error(`❌ Erro forçado ao enviar embed do squad ${squad.name}:`, forceError.message);
                // Retornar ID mock em caso de erro
                if (!messageId) {
                    return `mock_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
                }
            }
        }
    }

    async deleteSquadEmbed(messageId) {
        try {
            const channel = await this.getSquadsChannel();
            const message = await channel.messages.fetch(messageId);
            await message.delete();
            console.log(`🗑️ Embed do squad removido`);
        } catch (error) {
            console.error('❌ Erro ao deletar embed do squad:', error.message);
        }
    }

    async initializeSquads(squads) {
        console.log('🏆 Inicializando embeds dos squads...');
        
        // Primeiro, tentar buscar mensagens existentes no canal
        const existingMessages = await this.getExistingSquadMessages();
        
        console.log(`📋 Total de squads para inicializar: ${Object.keys(squads).length}`);
        
        for (const [squadId, squad] of Object.entries(squads)) {
            try {
                console.log(`🔄 Inicializando squad: ${squad.name} (ID: ${squadId})`);
                
                // Tentar encontrar mensagem existente para este squad
                const existingMessageId = this.findExistingMessageForSquad(squad, existingMessages);
                console.log(`📝 MessageId existente para ${squad.name}: ${existingMessageId || 'NENHUM'}`);
                
                const messageId = await this.updateSquadEmbed(squad, existingMessageId);
                
                // Salvar ID da mensagem
                this.squadsData.squads[squadId] = {
                    ...squad,
                    embed_message_id: messageId,
                    last_updated: new Date().toISOString()
                };
                
                console.log(`✅ Squad ${squad.name} ${existingMessageId ? 'atualizado' : 'inicializado'} com ID: ${messageId}`);
            } catch (error) {
                console.error(`❌ Erro ao inicializar squad ${squad.name}:`, error.message);
            }
        }
        
        this.saveSquadsData();
        console.log('✅ Todos os squads inicializados!');
    }

    async updateSquads(squads) {
        console.log('🔄 Atualizando embeds dos squads...');
        
        const oldSquads = this.squadsData.squads;
        let hasChanges = false;

        // SEMPRE verificar mudanças no vehicle-record-auto.json antes de atualizar
        console.log('🔍 Verificando mudanças no vehicle-record-auto.json...');
        let playerVehiclesChanged = false;
        
        if (fs.existsSync(this.playerVehiclesPath)) {
            const currentData = fs.readFileSync(this.playerVehiclesPath, 'utf8');
            const currentHash = this.generateHash(currentData);
            const currentTimestamp = fs.statSync(this.playerVehiclesPath).mtime.getTime();
            
            console.log(`📊 Hash atual: ${currentHash}`);
            console.log(`📊 Hash anterior: ${this.lastPlayerVehiclesHash}`);
            
            // Verificar se houve mudanças
            if (this.lastPlayerVehiclesHash && currentHash !== this.lastPlayerVehiclesHash) {
                console.log('🔄 Mudanças detectadas no vehicle-record-auto.json!');
                console.log(`🔍 Hash anterior: ${this.lastPlayerVehiclesHash}`);
                console.log(`🔍 Hash atual: ${currentHash}`);
                playerVehiclesChanged = true;
            } else {
                console.log(`🔍 Nenhuma mudança detectada no vehicle-record-auto.json`);
                console.log(`🔍 Hash anterior: ${this.lastPlayerVehiclesHash}`);
                console.log(`🔍 Hash atual: ${currentHash}`);
            }
            
            // Atualizar hash e timestamp
            this.lastPlayerVehiclesHash = currentHash;
            this.lastFileTimestamp = currentTimestamp;
        }

        // Primeiro, buscar mensagens existentes no canal
        const existingMessages = await this.getExistingSquadMessages();

        // Verificar squads modificados ou novos
        for (const [squadId, newSquad] of Object.entries(squads)) {
            const oldSquad = oldSquads[squadId];
            
            console.log(`🔍 Verificando squad: ${newSquad.name} (ID: ${squadId})`);
            console.log(`📊 Squad antigo existe: ${!!oldSquad}`);
            
            // SEMPRE atualizar se houve mudanças no vehicle-record-auto.json
            let shouldUpdate = this.hasSquadChanged(oldSquad, newSquad) || playerVehiclesChanged;
            
            // FORÇAR atualização se houve mudanças nos veículos
            if (playerVehiclesChanged) {
                console.log(`🚗 FORÇANDO atualização do embed devido a mudanças nos veículos`);
                shouldUpdate = true;
            }
            
            // SEMPRE atualizar se é um squad novo ou se houve mudanças nos veículos
            if (!oldSquad || playerVehiclesChanged) {
                shouldUpdate = true;
            }
            
            if (shouldUpdate) {
                console.log(`🔄 Squad ${newSquad.name} ${playerVehiclesChanged ? 'atualizando devido a mudanças nos veículos' : 'modificado'}, atualizando...`);

                // Preferir EDITAR o embed existente mesmo quando veículos mudaram; recriar só se falhar
                let messageId = oldSquad?.embed_message_id;
                if (!messageId) {
                    messageId = this.findExistingMessageForSquad(newSquad, existingMessages);
                }

                try {
                    console.log(`📝 ${messageId ? 'Editando' : 'Criando'} embed para ${newSquad.name}`);
                    const maybeNewId = await this.updateSquadEmbed(newSquad, messageId);
                    const effectiveId = messageId || maybeNewId || null;

                    this.squadsData.squads[squadId] = {
                        ...newSquad,
                        embed_message_id: effectiveId,
                        last_updated: new Date().toISOString()
                    };
                    hasChanges = true;
                } catch (editError) {
                    console.log(`⚠️ Falha ao editar embed (${editError.message}). Tentando recriar...`);
                    try {
                        // Tentar deletar antigo se existir
                        if (messageId) {
                            try { await this.deleteSquadEmbed(messageId); } catch (_) {}
                        }
                        const newMessageId = await this.updateSquadEmbed(newSquad, null);
                        this.squadsData.squads[squadId] = {
                            ...newSquad,
                            embed_message_id: newMessageId,
                            last_updated: new Date().toISOString()
                        };
                        hasChanges = true;
                    } catch (createError) {
                        console.log(`❌ Falha ao recriar embed: ${createError.message}`);
                    }
                }
            } else {
                console.log(`✅ Squad ${newSquad.name} não modificado, pulando...`);
            }
        }

        // Verificar squads removidos
        for (const [squadId, oldSquad] of Object.entries(oldSquads)) {
            if (!squads[squadId]) {
                console.log(`🗑️ Squad ${oldSquad.name} removido`);
                if (oldSquad.embed_message_id) {
                    await this.deleteSquadEmbed(oldSquad.embed_message_id);
                }
                delete this.squadsData.squads[squadId];
                hasChanges = true;
            }
        }

        // Salvar dados se houve mudanças
        if (hasChanges) {
            this.saveSquadsData();
            console.log('💾 Dados dos squads atualizados');
        }

        console.log('✅ Atualização dos squads concluída!');
    }

    async getExistingSquadMessages() {
        try {
            const channel = await this.getSquadsChannel();
            const messages = await channel.messages.fetch({ limit: 50 });
            
            // Filtrar apenas mensagens com embeds do nosso bot
            const squadMessages = messages.filter(msg => 
                msg.author.id === this.client.user.id && 
                msg.embeds.length > 0 &&
                msg.embeds[0].title && 
                msg.embeds[0].title.includes('Squad:')
            );
            
            console.log(`📋 Encontradas ${squadMessages.size} mensagens de squads existentes`);
            return squadMessages;
        } catch (error) {
            console.error('❌ Erro ao buscar mensagens existentes:', error.message);
            return new Map();
        }
    }
    
    findExistingMessageForSquad(squad, existingMessages) {
        for (const [messageId, message] of existingMessages) {
            const embed = message.embeds[0];
            if (embed && embed.title && embed.title.includes(`Squad: ${squad.name}`)) {
                console.log(`🔍 Encontrada mensagem existente para ${squad.name}: ${messageId}`);
                return messageId;
            }
        }
        console.log(`🆕 Nenhuma mensagem existente encontrada para ${squad.name}`);
        return null;
    }
    
    hasSquadChanged(oldSquad, newSquad) {
        if (!oldSquad) return true;
        
        // Comparar nome
        if (oldSquad.name !== newSquad.name) return true;
        
        // Comparar informações básicas
        if (oldSquad.message !== newSquad.message) return true;
        if (oldSquad.emblem !== newSquad.emblem) return true;
        if (oldSquad.information !== newSquad.information) return true;
        if (oldSquad.score !== newSquad.score) return true;
        if (oldSquad.member_limit !== newSquad.member_limit) return true;
        
        // Comparar membros
        if (oldSquad.members.length !== newSquad.members.length) return true;
        
        const oldMemberIds = oldSquad.members.map(m => m.user_profile_id).sort();
        const newMemberIds = newSquad.members.map(m => m.user_profile_id).sort();
        
        if (JSON.stringify(oldMemberIds) !== JSON.stringify(newMemberIds)) return true;
        
        // Comparar veículos do squad
        const oldVehicles = this.getSquadVehicles(oldSquad);
        const newVehicles = this.getSquadVehicles(newSquad);
        
        console.log(`🔍 Comparando veículos para ${newSquad.name}:`);
        console.log(`   Antigo:`, oldVehicles);
        console.log(`   Novo:`, newVehicles);
        console.log(`   Mudou:`, JSON.stringify(oldVehicles) !== JSON.stringify(newVehicles));
        
        const vehiclesChanged = JSON.stringify(oldVehicles) !== JSON.stringify(newVehicles);
        console.log(`   Resultado final: ${vehiclesChanged}`);
        
        return vehiclesChanged;
    }
}

module.exports = SquadEmbedManager; 