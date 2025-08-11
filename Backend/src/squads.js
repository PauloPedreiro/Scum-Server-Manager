const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const { DateTime } = require('luxon');
const axios = require('axios');

class SquadsManager {
    constructor() {
        this.config = this.loadConfig();
        this.squadsDataPath = path.join(__dirname, 'data', 'squad', 'squads.json');
        this.lastProcessedPath = path.join(__dirname, 'data', 'squad', 'lastProcessed.json');
        this.tempDbPath = path.join(__dirname, 'data', 'squad', 'temp', 'SCUM_squads.db');
        this.squadsData = this.loadSquadsData();
        this.lastProcessed = this.loadLastProcessed();
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
        if (fs.existsSync(this.squadsDataPath)) {
            return JSON.parse(fs.readFileSync(this.squadsDataPath, 'utf8'));
        }
        return { squads: {}, last_check: null };
    }

    loadLastProcessed() {
        if (fs.existsSync(this.lastProcessedPath)) {
            return JSON.parse(fs.readFileSync(this.lastProcessedPath, 'utf8'));
        }
        return { last_execution: null, next_execution: null, interval_hours: 0 };
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
            const playerVehiclesPath = path.join(__dirname, 'data', 'players', 'player_vehicles.json');
            if (!fs.existsSync(playerVehiclesPath)) {
                return {};
            }
            
            const playerVehicles = JSON.parse(fs.readFileSync(playerVehiclesPath, 'utf8'));
            const squadVehicles = {};
            
            // Para cada membro do squad
            squad.members.forEach(member => {
                const steamId = member.steam_id;
                
                // Buscar veículos do jogador
                if (playerVehicles[steamId] && playerVehicles[steamId].activeVehicles) {
                    playerVehicles[steamId].activeVehicles.forEach(vehicle => {
                        const prettyType = this.normalizeVehicleDisplayName(vehicle.vehicleType);
                        if (!squadVehicles[prettyType]) {
                            squadVehicles[prettyType] = 0;
                        }
                        squadVehicles[prettyType]++;
                    });
                }
            });
            
            return squadVehicles;
        } catch (error) {
            console.error('Erro ao buscar veículos do squad:', error.message);
            return {};
        }
    }

    saveSquadsData() {
        fs.writeFileSync(this.squadsDataPath, JSON.stringify(this.squadsData, null, 2));
    }

    saveLastProcessed() {
        fs.writeFileSync(this.lastProcessedPath, JSON.stringify(this.lastProcessed, null, 2));
    }

    async copyDatabase() {
        const sourcePath = this.config.funny_statistics.database_path;
        
        // Criar pasta temp se não existir
        const tempDir = path.dirname(this.tempDbPath);
        if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir, { recursive: true });
        }

        // Verificar se arquivo fonte existe
        if (!fs.existsSync(sourcePath)) {
            throw new Error(`Arquivo de banco não encontrado: ${sourcePath}`);
        }

        // Copiar arquivo
        fs.copyFileSync(sourcePath, this.tempDbPath);
        console.log('✅ Banco de dados copiado para pasta temp');
    }

    async readSquadsFromDatabase() {
        return new Promise((resolve, reject) => {
            const db = new sqlite3.Database(this.tempDbPath, (err) => {
                if (err) {
                    reject(err);
                    return;
                }

                // Query para buscar squads (estrutura real do banco SCUM)
                const query = `
                    SELECT 
                        s.id as squad_id,
                        s.name as squad_name,
                        s.message as squad_message,
                        s.emblem as squad_emblem,
                        s.information as squad_information,
                        s.score as squad_score,
                        s.member_limit,
                        s.last_member_login_time,
                        s.last_member_logout_time,
                        sm.id as member_id,
                        sm.squad_id,
                        sm.user_profile_id,
                        sm.rank as member_rank,
                        u.name as member_name,
                        u.user_id as member_steam_id
                    FROM squad s
                    LEFT JOIN squad_member sm ON s.id = sm.squad_id
                    LEFT JOIN user_profile u ON sm.user_profile_id = u.id
                    ORDER BY s.id, sm.rank DESC, u.name
                `;
                
                db.all(query, (err, rows) => {
                    if (err) {
                        reject(err);
                        return;
                    }
                    db.close();
                    resolve(rows);
                });
            });
        });
    }

    processSquadsData(rawData) {
        const squads = {};
        
        rawData.forEach(row => {
            const squadId = row.squad_id;
            
            if (!squads[squadId]) {
                squads[squadId] = {
                    id: squadId,
                    name: row.squad_name,
                    message: row.squad_message,
                    emblem: row.squad_emblem,
                    information: row.squad_information,
                    score: row.squad_score,
                    member_limit: row.member_limit,
                    last_member_login_time: row.last_member_login_time,
                    last_member_logout_time: row.last_member_logout_time,
                    members: []
                };
            }
            
            if (row.member_id && row.member_name) {
                const memberExists = squads[squadId].members.find(m => m.user_profile_id === row.user_profile_id);
                if (!memberExists) {
                    squads[squadId].members.push({
                        id: row.member_id,
                        user_profile_id: row.user_profile_id,
                        name: row.member_name,
                        steam_id: row.member_steam_id,
                        rank: row.member_rank
                    });
                }
            }
        });
        
        return squads;
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
        
        return JSON.stringify(oldVehicles) !== JSON.stringify(newVehicles);
    }

    createSquadEmbed(squad) {
        const embed = {
            title: `🏆 Squad: ${squad.name}`,
            color: 0x00ff88,
            fields: [
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
            ],
            timestamp: new Date().toISOString()
        };

        // Adicionar informações do squad se houver
        if (squad.message) {
            embed.fields.push({
                name: '💬 Mensagem',
                value: squad.message.length > 1024 ? squad.message.substring(0, 1021) + '...' : squad.message,
                inline: false
            });
        }

        if (squad.information) {
            embed.fields.push({
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
            
            embed.fields.push({
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
            
            embed.fields.push({
                name: '🚗 Veículos do Squad',
                value: vehicleList,
                inline: false
            });
        } else {
            embed.fields.push({
                name: '🚗 Veículos do Squad',
                value: 'Nenhum veículo registrado',
                inline: false
            });
        }

        return embed;
    }

    async updateSquadEmbed(squad, messageId = null) {
        // Este método agora é apenas um placeholder
        // A atualização real é feita pelo SquadEmbedManager via bot Discord
        console.log(`📝 Squad ${squad.name} marcado para atualização (usando bot Discord)`);
    }

    async cleanup() {
        try {
            if (fs.existsSync(this.tempDbPath)) {
                // Aguardar um pouco antes de tentar deletar
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                // Tentar deletar com tratamento de erro
                try {
                    fs.unlinkSync(this.tempDbPath);
                    console.log('✅ Banco de dados temporário removido');
                } catch (error) {
                    if (error.code === 'EBUSY' || error.code === 'ENOENT') {
                        console.log('⚠️ Arquivo temporário já foi removido ou está em uso');
                    } else {
                        console.error('❌ Erro ao remover arquivo temporário:', error.message);
                    }
                }
            }
        } catch (error) {
            console.error('❌ Erro no cleanup:', error.message);
        }
    }

    async getSquadsData() {
        try {
            console.log('📋 Obtendo dados dos squads...');
            
            // 1. Copiar banco
            await this.copyDatabase();

            // 2. Ler squads do banco
            const rawSquadsData = await this.readSquadsFromDatabase();
            const currentSquads = this.processSquadsData(rawSquadsData);

            // 3. Limpeza
            await this.cleanup();

            console.log(`✅ Dados dos squads obtidos: ${Object.keys(currentSquads).length} squads`);
            return currentSquads;

        } catch (error) {
            console.error('❌ Erro ao obter dados dos squads:', error.message);
            await this.cleanup();
            return {};
        }
    }

    async execute() {
        try {
            console.log('🏆 Iniciando sistema de squads...');
            console.log('🔍 Verificando se é hora de executar...');

            // Verificar se é hora de executar
            const now = DateTime.now();
            const lastExecution = this.lastProcessed.last_execution 
                ? DateTime.fromISO(this.lastProcessed.last_execution) 
                : null;

            if (lastExecution) {
                const hoursSinceLastExecution = now.diff(lastExecution, 'hours');
                if (hoursSinceLastExecution.hours < this.lastProcessed.interval_hours) {
                    console.log('⏰ Ainda não é hora de verificar squads');
                    return;
                }
            }

            // 1. Copiar banco
            await this.copyDatabase();

            // 2. Ler squads do banco
            const rawSquadsData = await this.readSquadsFromDatabase();
            const currentSquads = this.processSquadsData(rawSquadsData);

            // 3. Comparar com dados salvos
            const oldSquads = this.squadsData.squads;
            let hasChanges = false;

            // Verificar squads modificados ou novos
            for (const [squadId, newSquad] of Object.entries(currentSquads)) {
                const oldSquad = oldSquads[squadId];
                
                if (this.hasSquadChanged(oldSquad, newSquad)) {
                    console.log(`🔄 Squad ${newSquad.name} modificado, atualizando...`);
                    await this.updateSquadEmbed(newSquad, oldSquad?.embed_message_id);
                    
                    // Atualizar dados salvos
                    this.squadsData.squads[squadId] = {
                        ...newSquad,
                        embed_message_id: oldSquad?.embed_message_id || null,
                        last_updated: now.toISO()
                    };
                    hasChanges = true;
                }
            }

            // Verificar squads removidos
            for (const [squadId, oldSquad] of Object.entries(oldSquads)) {
                if (!currentSquads[squadId]) {
                    console.log(`🗑️ Squad ${oldSquad.name} removido`);
                    // TODO: Implementar remoção do embed do Discord
                    delete this.squadsData.squads[squadId];
                    hasChanges = true;
                }
            }

            // 4. Salvar dados se houve mudanças
            if (hasChanges) {
                this.squadsData.last_check = now.toISO();
                this.saveSquadsData();
                console.log('💾 Dados dos squads atualizados');
            }

            // 5. Atualizar controle de execução
            this.lastProcessed.last_execution = now.toISO();
            this.lastProcessed.next_execution = now.plus({ hours: this.lastProcessed.interval_hours }).toISO();
            this.saveLastProcessed();

            // 6. Limpeza
            await this.cleanup();

            console.log('✅ Sistema de squads executado com sucesso');

        } catch (error) {
            console.error('❌ Erro no sistema de squads:', error.message);
            await this.cleanup();
        }
    }
}

module.exports = SquadsManager; 