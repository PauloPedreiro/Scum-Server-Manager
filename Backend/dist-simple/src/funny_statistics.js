const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const http = require('http');
const https = require('https');
const url = require('url');
const { DateTime } = require('luxon');

// Função para fazer requisições HTTP (substitui axios)
function makeRequest(options) {
    return new Promise((resolve, reject) => {
        const parsedUrl = url.parse(options.url);
        const requestOptions = {
            hostname: parsedUrl.hostname,
            port: parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80),
            path: parsedUrl.path,
            method: options.method || 'GET',
            headers: options.headers || {}
        };

        const client = parsedUrl.protocol === 'https:' ? https : http;
        const req = client.request(requestOptions, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                resolve({
                    status: res.statusCode,
                    data: data,
                    headers: res.headers
                });
            });
        });

        req.on('error', (err) => {
            reject(err);
        });

        if (options.data) {
            req.write(JSON.stringify(options.data));
        }

        req.end();
    });
}

class FunnyStatistics {
    constructor() {
        this.config = this.loadConfig();
        this.funnyStats = this.loadFunnyStats();
        this.webhooks = this.loadWebhooks();
        this.lastExecution = null;
    }

    loadConfig() {
        const configPath = path.join(__dirname, 'data', 'server', 'config.json');
        return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }

    loadFunnyStats() {
        const statsPath = path.join(__dirname, 'data', 'funny_statistics.json');
        return JSON.parse(fs.readFileSync(statsPath, 'utf8'));
    }

    loadWebhooks() {
        const webhooksPath = path.join(__dirname, 'data', 'webhooks.json');
        return JSON.parse(fs.readFileSync(webhooksPath, 'utf8'));
    }

    async copyDatabase() {
        const sourcePath = this.config.funny_statistics.database_path;
        const tempPath = this.config.funny_statistics.temp_path;
        
        // Criar pasta temp se não existir
        const tempDir = path.dirname(tempPath);
        if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir, { recursive: true });
        }

        // Copiar arquivo
        fs.copyFileSync(sourcePath, tempPath);
        console.log('✅ Banco de dados copiado para pasta temp');
    }

    async readSurvivalStats() {
        const tempPath = this.config.funny_statistics.temp_path;
        
        return new Promise((resolve, reject) => {
            const db = new sqlite3.Database(tempPath, (err) => {
                if (err) {
                    reject(err);
                    return;
                }

                // JOIN com user_profile para buscar o nome do jogador
                const query = `
                    SELECT s.*, u.name as player_name 
                    FROM survival_stats s 
                    LEFT JOIN user_profile u ON s.user_profile_id = u.id
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

    getRandomStatistic() {
        const availableStats = Object.keys(this.funnyStats.statistics);
        return availableStats[Math.floor(Math.random() * availableStats.length)];
    }

    getRandomPlayer(stats, columnName) {
        // Filtrar jogadores que têm dados na coluna selecionada
        const playersWithData = stats.filter(row => 
            row[columnName] !== null && 
            row[columnName] !== undefined
        );

        if (playersWithData.length === 0) {
            return null;
        }

        // Se não há jogadores com valores > 0, usar qualquer jogador
        const playersWithPositiveData = playersWithData.filter(row => row[columnName] > 0);
        const playersToUse = playersWithPositiveData.length > 0 ? playersWithPositiveData : playersWithData;

        return playersToUse[Math.floor(Math.random() * playersToUse.length)];
    }

    getRandomTemplate(statName) {
        const templates = this.funnyStats.statistics[statName].templates;
        return templates[Math.floor(Math.random() * templates.length)];
    }

    formatMessage(player, statName, value, template) {
        const funnyTitle = this.funnyStats.statistics[statName].funny_title;
        const statNamePT = this.funnyStats.statistics[statName].name;
        
        // Usar nome do jogador se disponível, senão usar ID
        const playerName = player.player_name || player.user_profile_id;
        
        // Formatar o valor baseado no tipo de estatística
        let formattedValue = this.formatValue(value, statName);
        
        // Substituir variáveis no template
        let message = template
            .replace('{player}', playerName)
            .replace('{value}', formattedValue);

        return {
            content: message,
            embed: {
                title: `🎭 ${funnyTitle}`,
                description: message,
                color: parseInt(this.config.funny_statistics.embed_color.replace('#', ''), 16),
                footer: {
                    text: `Estatística: ${statNamePT}`
                },
                timestamp: new Date().toISOString()
            }
        };
    }

    formatValue(value, statName) {
        // Se o valor for null ou undefined, retornar 0
        if (value === null || value === undefined) {
            return '0';
        }

        // Converter para número
        const numValue = parseFloat(value);
        
        // Se não for um número válido, retornar 0
        if (isNaN(numValue)) {
            return '0';
        }

        // Formatação específica por tipo de estatística
        if (statName.includes('distance') || statName.includes('longest')) {
            // Para distâncias, arredondar para 2 casas decimais
            return numValue.toFixed(2);
        } else if (statName.includes('minutes') || statName.includes('time')) {
            // Para tempos, arredondar para 0 casas decimais
            return Math.round(numValue).toString();
        } else if (statName.includes('weight') || statName.includes('mass') || statName.includes('fat')) {
            // Para pesos/massas, arredondar para 1 casa decimal
            return numValue.toFixed(1);
        } else {
            // Para a maioria das estatísticas, arredondar para 0 casas decimais
            return Math.round(numValue).toString();
        }
    }

    async sendToDiscord(messageData) {
        const webhookUrl = this.webhooks[this.config.funny_statistics.webhook_key];
        
        try {
            await makeRequest({
                url: webhookUrl,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                data: {
                    embeds: [messageData.embed]
                }
            });
            console.log('✅ Mensagem enviada para o Discord');
        } catch (error) {
            console.error('❌ Erro ao enviar para Discord:', error.message);
        }
    }

    async generateSundaySpecial(stats) {
        const embed = {
            title: '🎭 Relatório Semanal de Estatísticas Divertidas',
            description: '🌟 **Aqui estão as estatísticas mais engraçadas da semana!** 🌟\n\n*Dados coletados dos sobreviventes mais... interessantes do servidor* 😄',
            color: parseInt(this.config.funny_statistics.embed_color.replace('#', ''), 16),
            fields: [],
            timestamp: new Date().toISOString(),
            thumbnail: {
                url: 'https://cdn.discordapp.com/emojis/1234567890123456789.png' // Emoji personalizado se disponível
            },
            footer: {
                text: '🎮 SCUM Server Manager - Estatísticas Divertidas'
            }
        };

        // Selecionar algumas estatísticas interessantes
        const interestingStats = [
            'diarrheas', 'vomits', 'teeth_lost', 'shots_fired', 
            'animals_killed', 'bears_killed', 'times_mauled_by_bear',
            'heart_attacks', 'overdose', 'starvation', 'highest_fat',
            'highest_muscle_mass', 'highest_weight_carried', 'highest_damage_taken',
            'distance_travelled_by_foot', 'distance_travelled_in_vehicle',
            'distance_travelled_swimming', 'distance_travel_by_boat', 'distance_sailed',
            'times_caught_by_shark', 'times_escaped_shark_bite', 'wolves_killed',
            'last_fame_point_award_consecutive_days', 'firearm_kills', 'bare_handed_kills',
            'items_picked_up', 'liquid_drank', 'total_calories_intake',
            'shots_hit', 'headshots', 'melee_weapon_swings', 'melee_weapon_hits',
            'melee_weapons_crafted', 'drone_kills', 'sentry_kills', 'prisoner_kills',
            'puppets_knocked_out', 'crows_killed', 'seagulls_killed', 'horses_killed',
            'boars_killed', 'goats_killed', 'deers_killed', 'chickens_killed',
            'rabbits_killed', 'donkeys_killed', 'longest_animal_kill_distance',
            'alcohol_drank', 'foliage_cut', 'mushrooms_eaten', 'lowest_negative_fame_points'
        ];

        // Agrupar estatísticas por categoria
        const categories = {
            '🏥 Saúde & Sobrevivência': ['diarrheas', 'vomits', 'teeth_lost', 'heart_attacks', 'overdose', 'starvation', 'highest_fat', 'highest_muscle_mass', 'highest_weight_carried', 'highest_damage_taken'],
            '🔫 Combate & Armas': ['shots_fired', 'shots_hit', 'headshots', 'firearm_kills', 'bare_handed_kills', 'melee_weapon_swings', 'melee_weapon_hits', 'melee_weapons_crafted'],
            '🐾 Caça & Animais': ['animals_killed', 'bears_killed', 'times_mauled_by_bear', 'wolves_killed', 'crows_killed', 'seagulls_killed', 'horses_killed', 'boars_killed', 'goats_killed', 'deers_killed', 'chickens_killed', 'rabbits_killed', 'donkeys_killed', 'longest_animal_kill_distance'],
            '🚗 Movimento & Viagem': ['distance_travelled_by_foot', 'distance_travelled_in_vehicle', 'distance_travelled_swimming', 'distance_travel_by_boat', 'distance_sailed'],
            '🌊 Aventuras Marinhas': ['times_caught_by_shark', 'times_escaped_shark_bite'],
            '🤖 Tecnologia & Robôs': ['drone_kills', 'sentry_kills', 'prisoner_kills', 'puppets_knocked_out'],
            '🍽️ Consumo & Recursos': ['items_picked_up', 'liquid_drank', 'total_calories_intake', 'alcohol_drank', 'foliage_cut', 'mushrooms_eaten'],
            '⭐ Fama & Status': ['last_fame_point_award_consecutive_days', 'lowest_negative_fame_points']
        };

        let fieldCount = 0;
        const maxFields = 25; // Limitar a 25 campos para evitar erro do Discord

        // Adicionar separadores de categoria
        for (const [categoryName, categoryStats] of Object.entries(categories)) {
            if (fieldCount >= maxFields) break;
            
            // Adicionar separador de categoria
            embed.fields.push({
                name: `\n${categoryName}`,
                value: '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
                inline: false
            });
            fieldCount++;

            // Adicionar estatísticas da categoria
            for (const statName of categoryStats) {
                if (fieldCount >= maxFields) break;
                
                const statData = this.funnyStats.statistics[statName];
                if (!statData) continue;

                // Encontrar jogador com maior valor
                const maxPlayer = stats.reduce((max, player) => {
                    const value = player[statName] || 0;
                    return value > (max.value || 0) ? { player, value } : max;
                }, { player: null, value: 0 });

                if (maxPlayer.player && maxPlayer.value > 0) {
                    const playerName = maxPlayer.player.player_name || maxPlayer.player.user_profile_id;
                    const formattedValue = this.formatValue(maxPlayer.value, statName);
                    embed.fields.push({
                        name: `🎯 ${statData.funny_title}`,
                        value: `**${playerName}**: ${formattedValue} ${statData.name}`,
                        inline: true
                    });
                    fieldCount++;
                }
            }
        }

        await this.sendToDiscord({ embed });
    }

    async cleanup() {
        const tempPath = this.config.funny_statistics.temp_path;
        if (fs.existsSync(tempPath)) {
            fs.unlinkSync(tempPath);
            console.log('✅ Banco de dados temporário removido');
        }
    }

    async execute() {
        try {
            console.log('🎭 Iniciando sistema de estatísticas divertidas...');

            // Verificar cooldown
            if (this.lastExecution) {
                const timeDiff = DateTime.now().diff(DateTime.fromISO(this.lastExecution), 'minutes');
                if (timeDiff.minutes < this.config.funny_statistics.cooldown_minutes) {
                    console.log('⏰ Cooldown ativo, aguardando...');
                    return;
                }
            }

            // 1. Copiar banco
            await this.copyDatabase();

            // 2. Ler estatísticas
            const stats = await this.readSurvivalStats();

            // 3. Verificar se é domingo especial
            const now = DateTime.now().setZone(this.config.funny_statistics.schedule.timezone);
            const isSunday = now.weekday === 7;
            const isSpecialTime = now.hour === 14 && now.minute === 0;

            if (isSunday && isSpecialTime && this.config.funny_statistics.sunday_special.enabled) {
                console.log('📊 Gerando relatório especial de domingo...');
                await this.generateSundaySpecial(stats);
            } else {
                // 4. Seleção aleatória
                const statName = this.getRandomStatistic();
                const player = this.getRandomPlayer(stats, statName);

                if (!player) {
                    console.log('❌ Nenhum jogador encontrado com dados válidos');
                    return;
                }

                const template = this.getRandomTemplate(statName);
                const value = player[statName];

                // 5. Formatar mensagem
                const messageData = this.formatMessage(player, statName, value, template);

                // 6. Enviar para Discord
                await this.sendToDiscord(messageData);
            }

            // 7. Limpeza
            await this.cleanup();

            this.lastExecution = DateTime.now().toISO();

        } catch (error) {
            console.error('❌ Erro no sistema de estatísticas divertidas:', error);
            await this.cleanup();
        }
    }

    startScheduler() {
        if (!this.config.funny_statistics.schedule.enabled) {
            console.log('⏰ Agendador de estatísticas divertidas desabilitado');
            return;
        }

        console.log('⏰ Iniciando agendador de estatísticas divertidas...');
        
        // Executar imediatamente para teste
        this.execute();

        // Agendar execuções
        setInterval(() => {
            const now = DateTime.now().setZone(this.config.funny_statistics.schedule.timezone);
            const currentTime = now.toFormat('HH:mm');
            
            if (this.config.funny_statistics.schedule.times.includes(currentTime)) {
                this.execute();
            }
        }, 60000); // Verificar a cada minuto
    }
}

module.exports = FunnyStatistics; 