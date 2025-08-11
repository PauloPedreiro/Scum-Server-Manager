const { Client, GatewayIntentBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
const fs = require('fs');
const path = require('path');
const logger = require('./logger');
const { getVehicleInfo } = require('../scripts/vehicle_database_query');

class DiscordBot {
    constructor() {
        this.client = new Client({
            intents: [
                GatewayIntentBits.Guilds,
                GatewayIntentBits.GuildMessages,
                GatewayIntentBits.MessageContent
            ]
        });
        
        this.config = this.loadConfig();
        this.dataPath = path.join(__dirname, 'data', 'bot');
        this.vehicleControl = null; // Referência ao sistema de controle de veículos
        
        this.setupEventHandlers();
    }

    loadConfig() {
        try {
            const configPath = path.join(__dirname, 'data', 'server', 'config.json');
            const configData = fs.readFileSync(configPath, 'utf8');
            return JSON.parse(configData);
        } catch (error) {
            logger.error('Erro ao carregar configuração', { error: error.message });
            return null;
        }
    }

    // Função para mascarar Steam ID nos logs
    maskSteamIdForLogs(steamId) {
        if (!steamId || steamId.length < 8) return steamId;
        const first = steamId.substring(0, 4);
        const last = steamId.substring(steamId.length - 4);
        return `${first}****${last}`;
    }

    setupEventHandlers() {
        this.client.on('ready', () => {
            logger.bot(`Conectado como ${this.client.user.tag}`);
            logger.bot(`Canal de registro: ${this.config.discord_bot.channels.vehicle_registration}`);
            
            // Iniciar monitoramento de logs
            this.startLogMonitoring();

            // Publicar painel de acesso/vínculo
            this.ensureAccessRecordPanel().catch((e) => logger.error('Erro ao publicar painel de acesso', { error: e.message }));
        });

        this.client.on('interactionCreate', async (interaction) => {
            if (interaction.isButton()) {
                await this.handleButtonInteraction(interaction);
            }
        });
        
        this.client.on('messageCreate', async (message) => {
            // manter handler existente
        });

        this.client.on('messageCreate', async (message) => {
            // Ignorar mensagens do próprio bot
            if (message.author.id === this.client.user.id) return;
            
            // Verificar se é uma mensagem do webhook Chat_in_Game
            if (message.webhookId) {
                await this.handleWebhookMessage(message);
            }
        });

        this.client.on('error', (error) => {
            logger.error('Erro no bot Discord', { error: error.message });
        });
    }

    startLogMonitoring() {
        logger.webhook('Iniciando monitoramento de webhook do chat');
        logger.webhook('Monitoramento configurado apenas para webhook Chat_in_Game');
    }

    async checkChatLogs() {
        // Função removida - o bot não precisa mais monitorar logs de gameplay
        // Os comandos são capturados via webhook Chat_in_Game
        logger.info('Monitoramento de logs desabilitado - usando apenas webhook');
    }

    async processChatMessage(messageContent) {
        try {
            console.log('🔍 Processando mensagem:', messageContent);
            
            // Padrão: 🎯 Pedreiro (76561198040636105): /rv 110050
            const rvMatch = messageContent.match(/(?:🎯|🌐|👥)\s*([^(]+)\s*\((\d+)\):\s*\/rv\s+(\d+)/);
            const rmMatch = messageContent.match(/(?:🎯|🌐|👥)\s*([^(]+)\s*\((\d+)\):\s*\/rm\s+(\d+)/);
            const mcMatch = messageContent.match(/(?:🎯|🌐|👥)\s*([^(]+)\s*\((\d+)\):\s*\/mc\s+(\d+)(?:\s+(.+))?/);
            const dvMatch = messageContent.match(/(?:🎯|🌐|👥)\s*([^(]+)\s*\((\d+)\):\s*\/dv\s+(\d+)\s+(\{[^}]+\})/);
            const rgStartMatch = messageContent.match(/(?:🎯|🌐|👥)\s*([^(]+)\s*\((\d+)\):\s*\/rg\s*$/i);
            const rgCodeMatch = messageContent.match(/(?:🎯|🌐|👥)\s*([^(]+)\s*\((\d+)\):\s*\/rg\s+(\d{4,8})/i);
            
            console.log('🔍 Matches encontrados:');
            console.log('  rvMatch:', rvMatch);
            console.log('  rmMatch:', rmMatch);
            console.log('  mcMatch:', mcMatch);
            console.log('  dvMatch:', dvMatch);
            
            let match = rvMatch || rmMatch || mcMatch || dvMatch || rgStartMatch || rgCodeMatch;
            let commandType = rvMatch ? 'rv' : (rmMatch ? 'rm' : (mcMatch ? 'mc' : (dvMatch ? 'dv' : (rgStartMatch ? 'rg_start' : (rgCodeMatch ? 'rg_code' : null)))));
            
            console.log('🎯 Tipo de comando:', commandType);
            console.log('📋 Match completo:', match);
            
            if (!match) {
                console.log('❌ Nenhum comando válido encontrado');
                return;
            }

            let playerName, steamId, vehicleId, vehicleType;
        
            let location = null;
            if (commandType === 'mc') {
                [, playerName, steamId, vehicleId, vehicleType] = match;
                vehicleType = vehicleType || null; // Tipo é opcional para /mc
            } else if (commandType === 'dv') {
                [, playerName, steamId, vehicleId, location] = match;
                vehicleType = location; // Para /dv, vehicleType contém a localização
            } else if (commandType === 'rg_start') {
                [, playerName, steamId] = match;
            } else if (commandType === 'rg_code') {
                [, playerName, steamId, vehicleId] = match; // vehicleId carrega o código
            } else {
                // Para /rv e /rm, extrair apenas ID - tipo será obtido do banco
                [, playerName, steamId, vehicleId] = match;
                vehicleType = null; // Será obtido do banco
            }
        
            logger.command(commandType, playerName, steamId, vehicleId, { vehicleType });
            
            if (!steamId) {
                logger.error('Steam ID não encontrado para jogador', { playerName });
                return;
            }
            
            // Verificar se já processamos este comando específico
            const processedKey = `${steamId}_${vehicleId}_${commandType}`;
            const processedPath = path.join(this.dataPath, 'processed_commands.json');
            let processed = {};
            
            if (fs.existsSync(processedPath)) {
                processed = JSON.parse(fs.readFileSync(processedPath, 'utf8'));
            }
            
            // Verificar se este comando específico já foi processado nos últimos 5 segundos
            const now = Date.now();
            const fiveSecondsAgo = now - 5000;
            
            if (processed[processedKey] && processed[processedKey].processed_at > fiveSecondsAgo) {
                logger.debug("Comando já processado recentemente", { steamId: this.maskSteamIdForLogs(steamId), vehicleId, commandType });
                return;
            }
            
            // Marcar como processado
            processed[processedKey] = {
                timestamp: new Date().toISOString(),
                processed_at: now,
                command_type: commandType,
                player_name: playerName
            };
            fs.writeFileSync(processedPath, JSON.stringify(processed, null, 2));
            
            // Processar comando
            console.log('🎯 Processando comando:', commandType);
            if (commandType === 'rv') {
                console.log('🚗 Processando comando /rv');
                await this.processVehicleCommand(steamId, vehicleId, vehicleType);
            } else if (commandType === 'rm') {
                console.log('🐎 Processando comando /rm');
                await this.processVehicleMountCommand(steamId, vehicleId, vehicleType);
            } else if (commandType === 'mc') {
                console.log('✅ Processando comando /mc');
                await this.processVehicleMountCompleteCommand(steamId, vehicleId);
            } else if (commandType === 'dv') {
                console.log('🚨 Processando comando /dv');
                await this.processVehicleDenounceCommand(steamId, vehicleId, vehicleType);
            } else if (commandType === 'rg_start') {
                console.log('🔗 Iniciando fluxo de vínculo /rg');
                // O painel já existe; apenas registrar intenção
                logger.info('Pedido de vínculo iniciado no jogo', { playerName, steamId: this.maskSteamIdForLogs(steamId) });
            } else if (commandType === 'rg_code') {
                console.log('🔐 Confirmando código de vínculo /rg');
                const code = vehicleId;
                await this.confirmLinkCodeFromChat(steamId, code, playerName);
            }
            
        } catch (error) {
            logger.error('Erro ao processar mensagem de chat', { error: error.message });
        }
    }

    getSteamIdFromPlayerName(playerName) {
        // Por enquanto, vamos usar um mapeamento simples
        // Em produção, isso deveria ser baseado em dados reais do servidor
        const playerMap = {
            'Pedreiro': '76561198040636105',
            'RAFA': '76561199076909393',
            'LOBO 47': '76561198422507274',
            'KamyKaazy': '76561198134357757',
            'BlueArcher_BR': '76561198398160339',
            'Reav': '76561197963358180',
            'ARKANJO': '76561198094354554',
            'TutiCats': '76561199617993331',
            'Til4toxico': '76561198129911132',
            'Rocha': '76561199086720901'
        };
        
        // Tentar encontrar o nome exato primeiro
        if (playerMap[playerName]) {
            return playerMap[playerName];
        }
        
        // Se não encontrar, tentar remover tags como [ADM], [VIP], etc.
        const cleanName = playerName.replace(/\[.*?\]/g, '').trim();
        if (cleanName && playerMap[cleanName]) {
            return playerMap[cleanName];
        }
        
        // Se ainda não encontrar, tentar buscar por nomes que contenham o nome limpo
        const matchingPlayer = Object.keys(playerMap).find(name => 
            name.toLowerCase().includes(cleanName.toLowerCase()) ||
            cleanName.toLowerCase().includes(name.toLowerCase())
        );
        
        if (matchingPlayer) {
            return playerMap[matchingPlayer];
        }
        
        return null;
    }

    // Função processLogLine removida - não é mais necessária
    // Os comandos são capturados apenas via webhook Chat_in_Game

    async ensureAccessRecordPanel() {
        try {
            const channelId = this.config.discord_bot.channels.link_request;
            if (!channelId) return;
            const channel = await this.client.channels.fetch(channelId);
            if (!channel) return;

            // Verificar se já existe um painel recente do próprio bot
            try {
                const recent = await channel.messages.fetch({ limit: 50 });
                const exists = recent.some((m) => {
                    if (m.author?.id !== this.client.user.id) return false;
                    const hasButton = (m.components || []).some(row =>
                        row.components?.some(c => c.customId === 'link_request_panel')
                    );
                    const hasTitle = (m.embeds || []).some(e => e.title?.includes('Vincular sua conta Steam ao Discord'));
                    return hasButton || hasTitle;
                });
                if (exists) return; // já existe painel, não recriar
            } catch (_) { /* ignore e continua criando */ }

            const embed = new EmbedBuilder()
                .setTitle('🔐 Vincular sua conta Steam ao Discord')
                .setDescription('Clique no botão abaixo para receber um código em DM. No jogo, digite: /rg <código>.')
                .setColor('#5865F2')
                .setFooter({ text: 'O código expira em 10 minutos' })
                .setTimestamp();

            const button = new ActionRowBuilder().addComponents(
                new ButtonBuilder()
                    .setCustomId('link_request_panel')
                    .setStyle(ButtonStyle.Primary)
                    .setLabel('Receber código por DM')
            );

            await channel.send({ embeds: [embed], components: [button] });
        } catch (e) {
            logger.error('Erro ao garantir painel de acesso', { error: e.message });
        }
    }

    async createLinkRequestEmbedFromChat(steamId, playerName) {
        try {
            const channelId = this.config.discord_bot.channels.link_request;
            const channel = await this.client.channels.fetch(channelId);

            // gerar código 6 dígitos e expiração 10 minutos
            const code = Math.floor(100000 + Math.random() * 900000).toString();
            const expiresAt = new Date(Date.now() + 10 * 60 * 1000);

            // salvar pendência
            const pendingPath = path.join(this.dataPath, 'pending_links.json');
            let pending = {};
            if (fs.existsSync(pendingPath)) pending = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            pending[steamId] = { code, playerName, createdAt: new Date().toISOString(), expiresAt: expiresAt.toISOString() };
            fs.writeFileSync(pendingPath, JSON.stringify(pending, null, 2));

            const embed = new EmbedBuilder()
                .setTitle('🔗 Vincular Steam ↔ Discord')
                .setDescription('Clique no botão para receber seu código em DM e confirme no jogo usando /rg <código>.')
                .addFields(
                    { name: 'Jogador', value: playerName, inline: true },
                    { name: 'Validade', value: '10 minutos', inline: true }
                )
                .setColor('#5865F2')
                .setTimestamp();

            const button = new ActionRowBuilder().addComponents(
                new ButtonBuilder().setCustomId(`link_code_dm:${steamId}`).setStyle(ButtonStyle.Primary).setLabel('Receber código por DM')
            );

            await channel.send({ embeds: [embed], components: [button] });
        } catch (e) {
            logger.error('Erro ao criar embed de vínculo', { error: e.message });
        }
    }

    async confirmLinkCodeFromChat(steamId, code, playerName) {
        try {
            const pendingPath = path.join(this.dataPath, 'pending_links.json');
            if (!fs.existsSync(pendingPath)) return;
            const pending = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            // pendência é por discordId; encontrar quem recebeu esse código
            const entry = Object.values(pending).find(p => p.code === code && new Date(p.expiresAt) >= new Date());
            if (!entry) return;

            await this.linkUser(entry.discordId, steamId);

            // Notificar canal de confirmação
            const notifyId = this.config.discord_bot.channels.linked_notify;
            const channel = await this.client.channels.fetch(notifyId);
            await channel.send({ content: `✅ Vinculado: ${playerName} ↔ <@${entry.discordId}>` });

            delete pending[entry.discordId];
            fs.writeFileSync(pendingPath, JSON.stringify(pending, null, 2));
        } catch (e) {
            logger.error('Erro ao confirmar código de vínculo', { error: e.message });
        }
    }

    async handleButtonInteraction(interaction) {
        if (interaction.customId === 'link_discord') {
            await this.handleLinkButton(interaction);
        } else if (interaction.customId === 'link_discord_mount') {
            await this.handleMountLinkButton(interaction);
        } else if (interaction.customId === 'link_discord_mount_complete') {
            await this.handleMountCompleteLinkButton(interaction);
        } else if (interaction.customId === 'link_request_panel') {
            await this.handleAccessPanelButton(interaction);
        } else if (interaction.customId.startsWith('link_code_dm:')) {
            await this.handleSendLinkCodeDM(interaction);
        } else if (interaction.customId === 'verify_denunciation') {
            await this.handleVerifyDenunciationButton(interaction);
        }
    }

    async handleLinkButton(interaction) {
        try {
            const steamIdOriginal = interaction.message.embeds[0]?.fields?.find(f => f.name === '**Steam ID Original:**')?.value;
            
            if (!steamIdOriginal) {
                await interaction.reply({ content: '❌ Erro: Steam ID não encontrado', ephemeral: true });
                return;
            }

            // Vincular usuário
            await this.linkUser(interaction.user.id, steamIdOriginal);
            
            // Processar solicitação pendente
            await this.processPendingRequest(steamIdOriginal, interaction.user);
            
            await interaction.reply({ content: '✅ Conta vinculada com sucesso!', ephemeral: true });
            
        } catch (error) {
            console.error('Erro ao processar vinculação:', error);
            await interaction.reply({ content: '❌ Erro ao vincular conta', ephemeral: true });
        }
    }

    async handleMountLinkButton(interaction) {
        try {
            const steamIdOriginal = interaction.message.embeds[0]?.fields?.find(f => f.name === '**Steam ID Original:**')?.value;
            
            if (!steamIdOriginal) {
                await interaction.reply({ content: '❌ Erro: Steam ID não encontrado', ephemeral: true });
                return;
            }

            // Vincular usuário
            await this.linkUser(interaction.user.id, steamIdOriginal);
            
            // Processar solicitação pendente de montagem
            await this.processPendingMountRequest(steamIdOriginal, interaction.user);
            
            await interaction.reply({ content: '✅ Conta vinculada com sucesso!', ephemeral: true });
            
        } catch (error) {
            console.error('Erro ao processar vinculação de montagem:', error);
            await interaction.reply({ content: '❌ Erro ao vincular conta', ephemeral: true });
        }
    }

    async handleMountCompleteLinkButton(interaction) {
        try {
            const steamIdOriginal = interaction.message.embeds[0]?.fields?.find(f => f.name === '**Steam ID Original:**')?.value;
            
            if (!steamIdOriginal) {
                await interaction.reply({ content: '❌ Erro: Steam ID não encontrado', ephemeral: true });
                return;
            }

            // Vincular usuário
            await this.linkUser(interaction.user.id, steamIdOriginal);
            
            // Processar solicitação pendente de conclusão de montagem
            await this.processPendingMountCompleteRequest(steamIdOriginal, interaction.user);
            
            await interaction.reply({ content: '✅ Conta vinculada com sucesso!', ephemeral: true });
            
        } catch (error) {
            console.error('Erro ao processar vinculação de conclusão de montagem:', error);
            await interaction.reply({ content: '❌ Erro ao vincular conta', ephemeral: true });
        }
    }

    async handleSendLinkCodeDM(interaction) {
        try {
            const pendingPath = path.join(this.dataPath, 'pending_links.json');
            let pending = {};
            if (fs.existsSync(pendingPath)) {
                try { pending = JSON.parse(fs.readFileSync(pendingPath, 'utf8')); } catch (_) { pending = {}; }
            }
            // gerar novo código vinculado ao Discord que clicou
            const code = Math.floor(100000 + Math.random() * 900000).toString();
            const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();
            // salvar em chave do discord (pendência aguardando código no jogo)
            pending[interaction.user.id] = { code, discordId: interaction.user.id, expiresAt };
            fs.writeFileSync(pendingPath, JSON.stringify(pending, null, 2));
            try {
                const dmEmbed = new EmbedBuilder()
                    .setTitle('🔐 Código de Vinculação')
                    .setDescription(`Use no jogo: 
                    \`/rg ${code}\`
                    `)
                    .addFields(
                        { name: 'Validade', value: '10 minutos', inline: true },
                        { name: 'Servidor', value: 'Scum Server Manager', inline: true }
                    )
                    .setColor('#00B894')
                    .setFooter({ text: 'Não compartilhe este código com outras pessoas.' })
                    .setTimestamp();
                await interaction.user.send({ embeds: [dmEmbed] });
                await interaction.reply({ content: '✅ Código enviado na sua DM.', ephemeral: true });
            } catch (e) {
                await interaction.reply({ content: `❌ Não consegui enviar DM. Ative DMs do servidor. Código: ${code}`, ephemeral: true });
            }
        } catch (error) {
            logger.error('Erro ao enviar código por DM', { error: error.message });
            try { await interaction.reply({ content: '❌ Erro ao enviar DM.', ephemeral: true }); } catch (_) {}
        }
    }

    async handleAccessPanelButton(interaction) {
        // Reutiliza o fluxo de envio de código por DM a partir do painel
        interaction.customId = 'link_code_dm:panel';
        return this.handleSendLinkCodeDM(interaction);
    }

    async handleVerifyDenunciationButton(interaction) {
        try {
            // Verificar permissões
            const member = await interaction.guild.members.fetch(interaction.user.id);
            const hasPermission = member.roles.cache.some(role => 
                role.name === 'Staff' || role.name === 'STAFF' || role.name === 'Adm' || role.name === 'ADM'
            );

            if (!hasPermission) {
                await interaction.reply({ 
                    content: '❌ Você não tem permissão para verificar denúncias. Apenas Staff e Adm podem fazer isso.', 
                    ephemeral: true 
                });
                return;
            }

            // Extrair informações da denúncia
            const embed = interaction.message.embeds[0];
            const vehicleIdField = embed.fields.find(f => f.name === '**ID do Veículo:**');
            const vehicleId = vehicleIdField?.value;

            if (!vehicleId) {
                await interaction.reply({ content: '❌ Erro: ID do veículo não encontrado', ephemeral: true });
                return;
            }

            // Atualizar status da denúncia
            await this.updateDenunciationStatus(vehicleId, interaction.user.id);

            // Atualizar embed
            const updatedEmbed = new EmbedBuilder()
                .setTitle('✅ Denúncia Verificada')
                .setDescription(`**Denúncia do veículo ${vehicleId} foi verificada!**`)
                .addFields(
                    { name: '**ID do Veículo:**', value: vehicleId, inline: true },
                    { name: '**Verificado por:**', value: `<@${interaction.user.id}>`, inline: true },
                    { name: '**Data/Hora:**', value: this.formatDateTime(new Date().toISOString()), inline: false }
                )
                .setColor('#00ff00')
                .setFooter({ text: 'Denúncia verificada e processada' })
                .setTimestamp();

            await interaction.message.edit({ embeds: [updatedEmbed], components: [] });
            await interaction.reply({ content: '✅ Denúncia verificada com sucesso!', ephemeral: true });

        } catch (error) {
            console.error('Erro ao verificar denúncia:', error);
            await interaction.reply({ content: '❌ Erro ao verificar denúncia', ephemeral: true });
        }
    }

    async linkUser(discordUserId, steamId) {
        const linkedUsersPath = path.join(this.dataPath, 'linked_users.json');
        let linkedUsers = {};
        
        try {
            if (fs.existsSync(linkedUsersPath)) {
                linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar usuários vinculados:', error);
        }

        // Verificar se este Steam ID já está vinculado a outro Discord ID
        const existingDiscordId = Object.keys(linkedUsers).find(key => linkedUsers[key].steam_id === steamId);
        
        if (existingDiscordId) {
            logger.info("Vinculação atualizada", { steamId: this.maskSteamIdForLogs(steamId), discordId: existingDiscordId, action: "update" });
            logger.info("Vinculação atualizada", { steamId: this.maskSteamIdForLogs(steamId), discordId: discordUserId, action: "update" });
            
            // Remover vinculação anterior
            delete linkedUsers[existingDiscordId];
        }

        // Verificar se este Discord ID já está vinculado a outro Steam ID
        if (linkedUsers[discordUserId]) {
            logger.info("Vinculação atualizada", { steamId: this.maskSteamIdForLogs(linkedUsers[discordUserId].steam_id), discordId: discordUserId, action: "update" });
            logger.info("Vinculação atualizada", { steamId: this.maskSteamIdForLogs(steamId), discordId: discordUserId, action: "update" });
        }

        linkedUsers[discordUserId] = {
            steam_id: steamId,
            linked_at: new Date().toISOString(),
            permissions: ["vehicle_registration", "vehicle_mount_registration"],
            last_activity: new Date().toISOString(),
            total_registrations: 0
        };

        fs.writeFileSync(linkedUsersPath, JSON.stringify(linkedUsers, null, 2));
                    logger.info("Vinculação criada", { steamId: this.maskSteamIdForLogs(steamId), discordId: discordUserId });
    }

    async processPendingRequest(steamId, discordUser) {
        const pendingPath = path.join(this.dataPath, 'pending_requests.json');
        let pendingRequests = {};
        
        try {
            if (fs.existsSync(pendingPath)) {
                pendingRequests = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar solicitações pendentes:', error);
            return;
        }

        const pendingRequest = pendingRequests[steamId];
        if (!pendingRequest) {
            logger.warn("Nenhuma solicitação pendente encontrada", { steamId: this.maskSteamIdForLogs(steamId) });
            logger.debug("Steam IDs disponíveis", { steamIds: Object.keys(pendingRequests).map(id => this.maskSteamIdForLogs(id)) });
            return;
        }

        // Remover apenas o botão do embed após vinculação
        if (pendingRequest.messageId) {
            try {
                const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_registration);
                const message = await channel.messages.fetch(pendingRequest.messageId);
                
                // Criar novo embed sem botão e sem campo Steam ID Original
                const originalEmbed = message.embeds[0];
                const embed = new EmbedBuilder()
                    .setTitle(originalEmbed.title)
                    .setDescription('✅ Vinculação Concluída')
                    .addFields(
                        originalEmbed.fields
                            .filter(field => field.name !== '**Steam ID Original:**')
                            .map(field => ({
                                name: field.name,
                                value: field.value,
                                inline: field.inline
                            }))
                    )
                    .setColor('#00ff00')
                    .setFooter({ text: 'Vinculação realizada com sucesso' })
                    .setTimestamp();
                
                // Editar mensagem removendo o botão
                await message.edit({ embeds: [embed], components: [] });
            } catch (error) {
                logger.error("Não foi possível editar embed", { error: error.message });
            }
        }

        // Registrar veículo
        await this.registerVehicle(pendingRequest.vehicleId, pendingRequest.vehicleType, steamId, discordUser);

        // Remover solicitação pendente
        delete pendingRequests[steamId];
        fs.writeFileSync(pendingPath, JSON.stringify(pendingRequests, null, 2));

        logger.info("Registro de veículo pendente", { vehicleId: pendingRequest.vehicleId, steamId: this.maskSteamIdForLogs(steamId), status: "pendente" });
    }

    async processPendingMountRequest(steamId, discordUser) {
        const pendingPath = path.join(this.dataPath, 'pending_mount_requests.json');
        let pendingRequests = {};
        
        try {
            if (fs.existsSync(pendingPath)) {
                pendingRequests = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar solicitações pendentes de montagem:', error);
            return;
        }

        const pendingRequest = pendingRequests[steamId];
        if (!pendingRequest) {
            logger.warn("Nenhuma solicitação pendente de montagem encontrada", { steamId });
            return;
        }

        // Remover apenas o botão do embed após vinculação
        if (pendingRequest.messageId) {
            try {
                const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_mount_registration);
                const message = await channel.messages.fetch(pendingRequest.messageId);
                
                // Criar novo embed sem botão e sem campo Steam ID Original
                const originalEmbed = message.embeds[0];
                const embed = new EmbedBuilder()
                    .setTitle(originalEmbed.title)
                    .setDescription('✅ Vinculação Concluída')
                    .addFields(
                        originalEmbed.fields
                            .filter(field => field.name !== '**Steam ID Original:**')
                            .map(field => ({
                                name: field.name,
                                value: field.value,
                                inline: field.inline
                            }))
                    )
                    .setColor('#ff8800')
                    .setFooter({ text: 'Vinculação realizada com sucesso' })
                    .setTimestamp();
                
                // Editar mensagem removendo o botão
                await message.edit({ embeds: [embed], components: [] });
            } catch (error) {
                logger.error("Não foi possível editar embed de montagem", { error: error.message });
            }
        }

        // Registrar montagem de veículo
        await this.registerVehicleMount(pendingRequest.vehicleId, pendingRequest.vehicleType, steamId, discordUser);

        // Remover solicitação pendente
        delete pendingRequests[steamId];
        fs.writeFileSync(pendingPath, JSON.stringify(pendingRequests, null, 2));

        logger.info("Registro de montagem pendente", { vehicleId: pendingRequest.vehicleId, steamId, status: "pendente" });
    }

    async processPendingMountCompleteRequest(steamId, discordUser) {
        const pendingPath = path.join(this.dataPath, 'pending_mount_complete_requests.json');
        let pendingRequests = {};
        
        try {
            if (fs.existsSync(pendingPath)) {
                pendingRequests = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar solicitações pendentes de conclusão de montagem:', error);
        }

        const pendingRequest = pendingRequests[steamId];
        if (!pendingRequest) {
            logger.warn("Solicitação pendente não encontrada", { steamId });
            return;
        }

        const { vehicleId } = pendingRequest;

        // Verificar se o veículo existe no registro de montagem
        const mountRegistrationsPath = path.join(this.dataPath, 'vehicle_mount_registrations.json');
        let mountRegistrations = {};
        
        if (fs.existsSync(mountRegistrationsPath)) {
            mountRegistrations = JSON.parse(fs.readFileSync(mountRegistrationsPath, 'utf8'));
        }

        if (!mountRegistrations[vehicleId]) {
            logger.error("Veículo não encontrado no registro de montagem", { vehicleId });
            return;
        }

        // Verificar se já foi concluído anteriormente
        const completedRegistrationsPath = path.join(this.dataPath, 'vehicle_mount_completed.json');
        let completedRegistrations = {};
        
        if (fs.existsSync(completedRegistrationsPath)) {
            completedRegistrations = JSON.parse(fs.readFileSync(completedRegistrationsPath, 'utf8'));
        }

        if (completedRegistrations[vehicleId]) {
            logger.warn("Montagem já foi concluída anteriormente", { vehicleId });
            return;
        }

        // Processar conclusão da montagem
        await this.completeVehicleMount(vehicleId, steamId, discordUser);

        // Remover solicitação pendente
        delete pendingRequests[steamId];
        fs.writeFileSync(pendingPath, JSON.stringify(pendingRequests, null, 2));

        logger.info("Registro de conclusão de montagem pendente", { vehicleId, steamId, status: "pendente" });
    }

    async registerVehicle(vehicleId, vehicleType, steamId, discordUser, vehicleInfo = null) {
        const registrationsPath = path.join(this.dataPath, 'vehicle_registrations.json');
        let registrations = {};
        
        try {
            if (fs.existsSync(registrationsPath)) {
                registrations = JSON.parse(fs.readFileSync(registrationsPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar registros:', error);
        }

        // Verificar se o veículo já está registrado
        if (registrations[vehicleId]) {
            const existingRegistration = registrations[vehicleId];
            logger.warn("Veículo já registrado", { vehicleId, registeredBy: existingRegistration.discordUsername, registeredAt: existingRegistration.registeredAt });
            
            // Enviar embed de aviso sobre duplicação
            await this.sendDuplicateVehicleEmbed(vehicleId, existingRegistration, 'rv');
            return;
        }

        const registration = {
            vehicleId: vehicleId,
            vehicleType: vehicleType.toUpperCase(),
            steamId: steamId,
            discordUserId: discordUser.id,
            discordUsername: discordUser.username,
            registeredAt: new Date().toISOString(),
            channelId: this.config.discord_bot.channels.vehicle_registration,
            vehicleInfo: vehicleInfo // Adicionar informações do veículo
        };

        registrations[vehicleId] = registration;
        fs.writeFileSync(registrationsPath, JSON.stringify(registrations, null, 2));

        // Atualizar contador de registros do usuário vinculado
        const linkedUsersPath = path.join(this.dataPath, 'linked_users.json');
        if (fs.existsSync(linkedUsersPath)) {
            let linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            if (linkedUsers[discordUser.id]) {
                linkedUsers[discordUser.id].total_registrations += 1;
                linkedUsers[discordUser.id].last_activity = new Date().toISOString();
                fs.writeFileSync(linkedUsersPath, JSON.stringify(linkedUsers, null, 2));
                logger.info("Registro de veículo processado", { vehicleId, username: discordUser.username, steamId, totalRegistrations: linkedUsers[discordUser.id].total_registrations });
            }
        }

        // Atualizar sistema de controle de veículos se disponível
        console.log('🔄 Verificando se vehicleControl está disponível...');
        console.log('vehicleControl:', this.vehicleControl ? 'Disponível' : 'Não disponível');
        
        if (this.vehicleControl) {
            try {
                console.log('🔄 Reinicializando sistema de controle de veículos...');
                // Reinicializar sistema para incluir novo registro (com validação no banco)
                await this.vehicleControl.vehicleControl.initializeFromRegistrations();
                console.log('🔄 Atualizando embeds do Discord...');
                await this.vehicleControl.vehicleControl.updateDiscordEmbeds();
                console.log('✅ Sistema de controle de veículos atualizado após novo registro');
                logger.info('Sistema de controle de veículos atualizado após novo registro');
            } catch (error) {
                console.error('❌ Erro ao atualizar sistema de controle de veículos:', error);
                logger.error('Erro ao atualizar sistema de controle de veículos', { error: error.message });
            }
        } else {
            console.log('⚠️ VehicleControl não está disponível - embeds não serão atualizados automaticamente');
        }

        // Enviar embed de sucesso
        await this.sendSuccessEmbed(registration);
    }

    async registerVehicleMount(vehicleId, vehicleType, steamId, discordUser, vehicleInfo = null) {
        const registrationsPath = path.join(this.dataPath, 'vehicle_mount_registrations.json');
        let registrations = {};
        
        try {
            if (fs.existsSync(registrationsPath)) {
                registrations = JSON.parse(fs.readFileSync(registrationsPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar registros de montagem:', error);
        }

        // Verificar se o veículo já está registrado para montagem
        if (registrations[vehicleId]) {
            const existingRegistration = registrations[vehicleId];
            logger.warn("Veículo já registrado para montagem", { vehicleId, registeredBy: existingRegistration.discordUsername, registeredAt: existingRegistration.registeredAt });
            
            // Enviar embed de aviso sobre duplicação
            await this.sendDuplicateVehicleEmbed(vehicleId, existingRegistration, 'rm');
            return;
        }

        const registration = {
            vehicleId: vehicleId,
            vehicleType: vehicleType.toUpperCase(),
            steamId: steamId,
            discordUserId: discordUser.id,
            discordUsername: discordUser.username,
            registeredAt: new Date().toISOString(),
            channelId: this.config.discord_bot.channels.vehicle_mount_registration,
            vehicleInfo: vehicleInfo // Adicionar informações do veículo
        };

        registrations[vehicleId] = registration;
        fs.writeFileSync(registrationsPath, JSON.stringify(registrations, null, 2));

        // Atualizar contador de registros do usuário vinculado
        const linkedUsersPath = path.join(this.dataPath, 'linked_users.json');
        if (fs.existsSync(linkedUsersPath)) {
            let linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            if (linkedUsers[discordUser.id]) {
                linkedUsers[discordUser.id].total_registrations += 1;
                linkedUsers[discordUser.id].last_activity = new Date().toISOString();
                fs.writeFileSync(linkedUsersPath, JSON.stringify(linkedUsers, null, 2));
                logger.info("Registro de montagem processado", { vehicleId, username: discordUser.username, steamId, totalRegistrations: linkedUsers[discordUser.id].total_registrations });
            }
        }

        // Enviar embed de sucesso para montagem
        await this.sendVehicleMountSuccessEmbed(registration);
    }

    async completeVehicleMount(vehicleId, steamId, discordUser) {
        // Consultar informações do veículo no banco
        let vehicleInfo = null;
        try {
            vehicleInfo = await getVehicleInfo(vehicleId);
            logger.info("Informações do veículo obtidas para montagem", { vehicleId, name: vehicleInfo.name, type: vehicleInfo.type });
        } catch (error) {
            logger.error("Erro ao consultar veículo no banco para montagem", { vehicleId, error: error.message });
            // Continuar sem as informações do banco
        }

        // Buscar informações do veículo no registro de montagem
        const mountRegistrationsPath = path.join(this.dataPath, 'vehicle_mount_registrations.json');
        let mountRegistrations = {};
        
        try {
            if (fs.existsSync(mountRegistrationsPath)) {
                mountRegistrations = JSON.parse(fs.readFileSync(mountRegistrationsPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar registros de montagem:', error);
        }

        const mountRegistration = mountRegistrations[vehicleId];
        if (!mountRegistration) {
            logger.error("Veículo não encontrado no registro de montagem", { vehicleId });
            return;
        }

        // Registrar como montagem concluída
        const completedRegistrationsPath = path.join(this.dataPath, 'vehicle_mount_completed.json');
        let completedRegistrations = {};
        
        try {
            if (fs.existsSync(completedRegistrationsPath)) {
                completedRegistrations = JSON.parse(fs.readFileSync(completedRegistrationsPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar registros de montagem concluída:', error);
        }

        const completedRegistration = {
            vehicleId: vehicleId,
            vehicleType: mountRegistration.vehicleType,
            steamId: steamId,
            discordUserId: discordUser.id,
            discordUsername: discordUser.username,
            completedAt: new Date().toISOString(),
            originalMountRegistration: mountRegistration,
            channelId: this.config.discord_bot.channels.vehicle_registration,
            vehicleInfo: vehicleInfo // Adicionar informações do veículo
        };

        completedRegistrations[vehicleId] = completedRegistration;
        fs.writeFileSync(completedRegistrationsPath, JSON.stringify(completedRegistrations, null, 2));

        // Registrar no sistema de veículos como "Veículo Montado"
        const vehicleRegistrationsPath = path.join(this.dataPath, 'vehicle_registrations.json');
        let vehicleRegistrations = {};
        
        try {
            if (fs.existsSync(vehicleRegistrationsPath)) {
                vehicleRegistrations = JSON.parse(fs.readFileSync(vehicleRegistrationsPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar registros de veículos:', error);
        }

        const vehicleRegistration = {
            vehicleId: vehicleId,
            vehicleType: `${mountRegistration.vehicleType} MONTADO`,
            steamId: steamId,
            discordUserId: discordUser.id,
            discordUsername: discordUser.username,
            registeredAt: new Date().toISOString(),
            channelId: this.config.discord_bot.channels.vehicle_registration,
            mountCompleted: true,
            originalMountRegistration: mountRegistration
        };

        vehicleRegistrations[vehicleId] = vehicleRegistration;
        fs.writeFileSync(vehicleRegistrationsPath, JSON.stringify(vehicleRegistrations, null, 2));

        // Atualizar contador de registros do usuário vinculado
        const linkedUsersPath = path.join(this.dataPath, 'linked_users.json');
        if (fs.existsSync(linkedUsersPath)) {
            let linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            if (linkedUsers[discordUser.id]) {
                linkedUsers[discordUser.id].total_registrations += 1;
                linkedUsers[discordUser.id].last_activity = new Date().toISOString();
                fs.writeFileSync(linkedUsersPath, JSON.stringify(linkedUsers, null, 2));
                logger.info("Registro de conclusão de montagem processado", { vehicleId, username: discordUser.username, steamId, totalRegistrations: linkedUsers[discordUser.id].total_registrations });
            }
        }

        // Atualizar sistema de controle de veículos se disponível
        console.log('🔄 Verificando se vehicleControl está disponível (MC)...');
        console.log('vehicleControl:', this.vehicleControl ? 'Disponível' : 'Não disponível');
        
        if (this.vehicleControl) {
            try {
                console.log('🔄 Reinicializando sistema de controle de veículos (MC)...');
                // Reinicializar sistema para incluir novo registro
                this.vehicleControl.vehicleControl.initializeFromRegistrations();
                console.log('🔄 Atualizando embeds do Discord (MC)...');
                await this.vehicleControl.vehicleControl.updateDiscordEmbeds();
                console.log('✅ Sistema de controle de veículos atualizado após montagem concluída');
                logger.info('Sistema de controle de veículos atualizado após montagem concluída');
            } catch (error) {
                console.error('❌ Erro ao atualizar sistema de controle de veículos (MC):', error);
                logger.error('Erro ao atualizar sistema de controle de veículos', { error: error.message });
            }
        } else {
            console.log('⚠️ VehicleControl não está disponível (MC) - embeds não serão atualizados automaticamente');
        }

        // Enviar embed de sucesso para montagem concluída
        await this.sendVehicleMountCompleteSuccessEmbed(completedRegistration);
    }

    async sendSuccessEmbed(registration) {
        try {
            console.log('🚀 Iniciando envio do embed de sucesso...');
            console.log('📊 Dados do registro:', {
                vehicleId: registration.vehicleId,
                vehicleType: registration.vehicleType,
                vehicleInfo: registration.vehicleInfo
            });
            
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_registration);
            console.log('📺 Canal obtido:', channel?.id);
            
            const embed = new EmbedBuilder()
                .setTitle('🎮 Registro de Veículo')
                .setDescription('✅ Novo Veículo Registrado')
                .addFields(
                    { name: '**Nome do Veículo:**', value: registration.vehicleType, inline: true },
                    { name: '**ID do Veículo:**', value: registration.vehicleId, inline: true },
                    { name: '**Registrado por:**', value: `<@${registration.discordUserId}>`, inline: true },
                    { name: '**Data/Hora:**', value: this.formatDateTime(registration.registeredAt), inline: false }
                )
                .setColor(this.config.discord_bot.features.vehicle_registration.embed_color)
                .setFooter({ text: 'Registro automático via comando /rv' })
                .setTimestamp();

            // Adicionar imagem do veículo se disponível
            if (registration.vehicleInfo && registration.vehicleInfo.imageFile) {
                const imagePath = path.join(__dirname, 'data', 'imagens', 'carros', registration.vehicleInfo.imageFile);
                console.log('🖼️ Tentando enviar imagem:', imagePath);
                console.log('📁 Arquivo existe:', fs.existsSync(imagePath));
                
                if (fs.existsSync(imagePath)) {
                    embed.setThumbnail(`attachment://${registration.vehicleInfo.imageFile}`);
                    console.log('✅ Enviando embed com imagem');
                    await channel.send({ 
                        embeds: [embed], 
                        files: [{ 
                            attachment: imagePath, 
                            name: registration.vehicleInfo.imageFile 
                        }] 
                    });
                } else {
                    console.log('⚠️ Imagem não encontrada, enviando embed sem imagem');
                    await channel.send({ embeds: [embed] });
                }
            } else {
                console.log('⚠️ Sem informações de imagem, enviando embed básico');
                await channel.send({ embeds: [embed] });
            }
            
            console.log('✅ Embed enviado com sucesso!');
            logger.info("Embed de sucesso enviado", { vehicleId: registration.vehicleId });
            
        } catch (error) {
            console.error('❌ Erro ao enviar embed de sucesso:', error);
            logger.error('Erro ao enviar embed de sucesso', { error: error.message });
        }
    }

    async sendVehicleMountSuccessEmbed(registration) {
        try {
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_mount_registration);
            
            const embed = new EmbedBuilder()
                .setTitle('🐎 Registro de Montagem de Veículo')
                .setDescription('✅ Nova Montagem Registrada')
                .addFields(
                    { name: '**Nome do Veículo:**', value: registration.vehicleType, inline: true },
                    { name: '**ID do Veículo:**', value: registration.vehicleId, inline: true },
                    { name: '**Registrado por:**', value: `<@${registration.discordUserId}>`, inline: true },
                    { name: '**Data/Hora:**', value: this.formatDateTime(registration.registeredAt), inline: false }
                )
                .setColor(this.config.discord_bot.features.vehicle_mount_registration.embed_color)
                .setFooter({ text: 'Registro automático via comando /rm' })
                .setTimestamp();

            // Adicionar imagem do veículo se disponível
            if (registration.vehicleInfo && registration.vehicleInfo.imageFile) {
                const imagePath = path.join(__dirname, 'data', 'imagens', 'carros', registration.vehicleInfo.imageFile);
                if (fs.existsSync(imagePath)) {
                    embed.setThumbnail(`attachment://${registration.vehicleInfo.imageFile}`);
                    await channel.send({ 
                        embeds: [embed], 
                        files: [{ 
                            attachment: imagePath, 
                            name: registration.vehicleInfo.imageFile 
                        }] 
                    });
                } else {
                    await channel.send({ embeds: [embed] });
                }
            } else {
                await channel.send({ embeds: [embed] });
            }
            
            logger.info("Embed de sucesso de montagem enviado", { vehicleId: registration.vehicleId });
            
        } catch (error) {
            console.error('Erro ao enviar embed de sucesso de montagem:', error);
        }
    }

    maskSteamId(steamId) {
        if (!steamId || steamId.length < 8) return steamId;
        
        // Mascarar mantendo os primeiros 4 e últimos 4 dígitos
        const first = steamId.substring(0, 4);
        const last = steamId.substring(steamId.length - 4);
        const masked = '*'.repeat(steamId.length - 8);
        
        return `${first}${masked}${last}`;
    }

    async sendLinkEmbed(steamId, vehicleId, vehicleType) {
        try {
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_registration);
            
            const maskedSteamId = this.maskSteamId(steamId);
            
            const embed = new EmbedBuilder()
                .setTitle('🎮 Registro de Veículo Detectado')
                .setDescription('⚠️ Aguardando Vinculação')
                .addFields(
                    { name: '**Steam ID:**', value: maskedSteamId, inline: true },
                    { name: '**ID do Veículo:**', value: vehicleId, inline: true },
                    { name: '**Tipo:**', value: vehicleType.toUpperCase(), inline: true },
                    { name: '**Data/Hora:**', value: this.formatDateTime(new Date().toISOString()), inline: false },
                    { name: '**Steam ID Original:**', value: steamId, inline: false }
                )
                .setColor('#ffaa00')
                .setFooter({ text: 'Clique no botão abaixo para vincular sua conta Discord' })
                .setTimestamp();

            const button = new ActionRowBuilder()
                .addComponents(
                    new ButtonBuilder()
                        .setCustomId('link_discord')
                        .setLabel('🔗 Vincular Discord')
                        .setStyle(ButtonStyle.Primary)
                );

            const message = await channel.send({ embeds: [embed], components: [button] });
            
            // Salvar ID da mensagem para deletar depois
            const pendingPath = path.join(this.dataPath, 'pending_requests.json');
            let pendingRequests = {};
            
            if (fs.existsSync(pendingPath)) {
                pendingRequests = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            }
            
            if (pendingRequests[steamId]) {
                pendingRequests[steamId].messageId = message.id;
                fs.writeFileSync(pendingPath, JSON.stringify(pendingRequests, null, 2));
            }
            
            logger.info("Embed de vinculação enviado", { steamId, status: "pendente" });
            
        } catch (error) {
            console.error('Erro ao enviar embed de vinculação:', error);
        }
    }

    async sendVehicleMountLinkEmbed(steamId, vehicleId, vehicleType) {
        try {
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_mount_registration);
            
            const maskedSteamId = this.maskSteamId(steamId);
            
            const embed = new EmbedBuilder()
                .setTitle('🐎 Registro de Montagem de Veículo Detectado')
                .setDescription('⚠️ Aguardando Vinculação')
                .addFields(
                    { name: '**Steam ID:**', value: maskedSteamId, inline: true },
                    { name: '**ID do Veículo:**', value: vehicleId, inline: true },
                    { name: '**Tipo:**', value: vehicleType.toUpperCase(), inline: true },
                    { name: '**Data/Hora:**', value: this.formatDateTime(new Date().toISOString()), inline: false },
                    { name: '**Steam ID Original:**', value: steamId, inline: false }
                )
                .setColor('#ff8800')
                .setFooter({ text: 'Clique no botão abaixo para vincular sua conta Discord' })
                .setTimestamp();

            const button = new ActionRowBuilder()
                .addComponents(
                    new ButtonBuilder()
                        .setCustomId('link_discord_mount')
                        .setLabel('🔗 Vincular Discord')
                        .setStyle(ButtonStyle.Primary)
                );

            const message = await channel.send({ embeds: [embed], components: [button] });
            
            // Salvar ID da mensagem para deletar depois
            const pendingPath = path.join(this.dataPath, 'pending_mount_requests.json');
            let pendingRequests = {};
            
            if (fs.existsSync(pendingPath)) {
                pendingRequests = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            }
            
            if (pendingRequests[steamId]) {
                pendingRequests[steamId].messageId = message.id;
                fs.writeFileSync(pendingPath, JSON.stringify(pendingRequests, null, 2));
            }
            
            logger.info("Embed de vinculação de montagem enviado", { steamId, status: "pendente" });
            
        } catch (error) {
            console.error('Erro ao enviar embed de vinculação de montagem:', error);
        }
    }

    async sendErrorEmbed(error, command) {
        try {
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_registration);
            
            const embed = new EmbedBuilder()
                .setTitle('❌ Erro no Registro')
                .setDescription(`**Problema:** ${error}`)
                .addFields(
                    { name: '**Comando usado:**', value: command, inline: true },
                    { name: '**Formato correto:**', value: '/rv <ID_NÚMERO> <TIPO_VEICULO>', inline: true },
                    { name: '**Exemplo:**', value: '/rv 1654510 ranger', inline: false }
                )
                .setColor('#ff0000')
                .setTimestamp();

            await channel.send({ embeds: [embed] });
            
        } catch (error) {
            console.error('Erro ao enviar embed de erro:', error);
        }
    }

    async sendVehicleMountErrorEmbed(error, command) {
        try {
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_mount_registration);
            
            const embed = new EmbedBuilder()
                .setTitle('❌ Erro no Registro de Montagem')
                .setDescription(`**Problema:** ${error}`)
                .addFields(
                    { name: '**Comando usado:**', value: command, inline: true },
                    { name: '**Formato correto:**', value: '/rm <ID_NÚMERO> <TIPO_VEICULO>', inline: true },
                    { name: '**Exemplo:**', value: '/rm 1654510 ranger', inline: false }
                )
                .setColor('#ff0000')
                .setTimestamp();

            await channel.send({ embeds: [embed] });
            
        } catch (error) {
            console.error('Erro ao enviar embed de erro de montagem:', error);
        }
    }

    formatDateTime(isoString) {
        const date = new Date(isoString);
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const year = date.getFullYear();
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const seconds = date.getSeconds().toString().padStart(2, '0');
        
        return `${day}/${month}/${year} às ${hours}:${minutes}:${seconds}`;
    }

    isUserLinked(discordUserId) {
        const linkedUsersPath = path.join(this.dataPath, 'linked_users.json');
        
        try {
            if (!fs.existsSync(linkedUsersPath)) return false;
            
            const linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            return linkedUsers.hasOwnProperty(discordUserId);
            
        } catch (error) {
            console.error('Erro ao verificar vinculação:', error);
            return false;
        }
    }

    getSteamIdFromDiscord(discordUserId) {
        const linkedUsersPath = path.join(this.dataPath, 'linked_users.json');
        
        try {
            if (!fs.existsSync(linkedUsersPath)) return null;
            
            const linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            return linkedUsers[discordUserId]?.steam_id || null;
            
        } catch (error) {
            console.error('Erro ao obter Steam ID:', error);
            return null;
        }
    }

    async getPlayerNameFromSteamId(steamId) {
        try {
            // Mapeamento de Steam IDs para nomes de personagens
            const playerMap = {
                '76561198040636105': 'Pedreiro',
                '76561199076909393': 'RAFA',
                '76561198422507274': 'LOBO 47',
                '76561198134357757': 'KamyKaazy',
                '76561198398160339': 'BlueArcher_BR',
                '76561197963358180': 'Reav',
                '76561198094354554': 'ARKANJO',
                '76561199617993331': 'TutiCats'
            };
            
            return playerMap[steamId] || null;
        } catch (error) {
            console.error('Erro ao obter nome do personagem:', error);
            return null;
        }
    }

    isOnCooldown(steamId) {
        const cooldownsPath = path.join(this.dataPath, 'cooldowns.json');
        
        try {
            if (!fs.existsSync(cooldownsPath)) return false;
            
            const cooldowns = JSON.parse(fs.readFileSync(cooldownsPath, 'utf8'));
            const userCooldown = cooldowns[steamId];
            
            if (!userCooldown) return false;
            
            const now = new Date();
            const cooldownUntil = new Date(userCooldown.cooldown_until);
            
            return now < cooldownUntil;
            
        } catch (error) {
            console.error('Erro ao verificar cooldown:', error);
            return false;
        }
    }

    setCooldown(steamId) {
        const cooldownsPath = path.join(this.dataPath, 'cooldowns.json');
        let cooldowns = {};
        
        try {
            if (fs.existsSync(cooldownsPath)) {
                cooldowns = JSON.parse(fs.readFileSync(cooldownsPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar cooldowns:', error);
        }

        const now = new Date();
        const cooldownSeconds = this.config.discord_bot.features.vehicle_registration.cooldown_seconds;
        const cooldownUntil = new Date(now.getTime() + cooldownSeconds * 1000);

        cooldowns[steamId] = {
            last_command: now.toISOString(),
            cooldown_until: cooldownUntil.toISOString()
        };

        fs.writeFileSync(cooldownsPath, JSON.stringify(cooldowns, null, 2));
    }

    getRemainingCooldown(steamId) {
        const cooldownsPath = path.join(this.dataPath, 'cooldowns.json');
        
        try {
            if (!fs.existsSync(cooldownsPath)) return 0;
            
            const cooldowns = JSON.parse(fs.readFileSync(cooldownsPath, 'utf8'));
            const userCooldown = cooldowns[steamId];
            
            if (!userCooldown) return 0;
            
            const now = new Date();
            const cooldownUntil = new Date(userCooldown.cooldown_until);
            
            if (now >= cooldownUntil) return 0;
            
            return Math.ceil((cooldownUntil - now) / 1000);
            
        } catch (error) {
            console.error('Erro ao calcular cooldown restante:', error);
            return 0;
        }
    }

    async handleWebhookMessage(message) {
        try {
                    // Verificar se é uma mensagem do chat do jogo
        if (!message.content || (!message.content.includes('/rv') && !message.content.includes('/rm') && !message.content.includes('/mc') && !message.content.includes('/dv') && !message.content.toLowerCase().includes('/rg'))) {
            return;
        }

            logger.webhook("Mensagem recebida do Chat_in_Game", { content: message.content.substring(0, 100) });

            // Usar a mesma lógica da processChatMessage
            await this.processChatMessage(message.content);

        } catch (error) {
            console.error('❌ Erro ao processar mensagem do webhook:', error);
        }
    }

    async processVehicleCommand(steamId, vehicleId, vehicleType) {
        try {
            // Verificar se é um comando válido
            if (!vehicleId || isNaN(vehicleId)) {
                await this.sendErrorEmbed('Comando inválido', `/rv ${vehicleId}`);
                return;
            }

            // Verificar cooldown (silencioso - não envia embed)
            if (this.isOnCooldown(steamId)) {
                logger.warn("Cooldown ativo", { steamId, command: "rv", cooldownSeconds: 30 });
                return;
            }

            // Consultar informações do veículo no banco
            let vehicleInfo;
            try {
                vehicleInfo = await getVehicleInfo(vehicleId);
                logger.info("Informações do veículo obtidas", { vehicleId, name: vehicleInfo.name, type: vehicleInfo.type });
            } catch (error) {
                logger.error("Erro ao consultar veículo no banco", { vehicleId, error: error.message });
                await this.sendErrorEmbed(`Veículo com ID ${vehicleId} não encontrado no banco de dados`, `/rv ${vehicleId}`);
                return;
            }

            // Verificar se usuário está vinculado
            const linkedUsersPath = path.join(this.dataPath, 'linked_users.json');
            let linkedUsers = {};
            
            if (fs.existsSync(linkedUsersPath)) {
                linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            }

            const discordUserId = Object.keys(linkedUsers).find(key => linkedUsers[key].steam_id === steamId);

            if (discordUserId) {
                // Steam ID já vinculado - registrar automaticamente
                logger.info("Usuário já vinculado", { steamId, discordId: discordUserId });
                try {
                    const discordUser = await this.client.users.fetch(discordUserId);
                    await this.registerVehicle(vehicleId, vehicleInfo.type, steamId, discordUser, vehicleInfo);
                    this.setCooldown(steamId);
                    logger.info("Registro de veículo automático", { vehicleId, steamId, method: "automático" });
                } catch (error) {
                    logger.warn("Discord ID inválido", { discordUserId });
                    // Se o Discord ID não for válido, criar nova solicitação pendente
                    await this.createPendingRequest(steamId, vehicleId, vehicleInfo.type, vehicleInfo);
                }
                
            } else {
                // Steam ID não vinculado - criar solicitação pendente
                logger.info("Usuário não vinculado", { steamId, status: "pendente" });
                await this.createPendingRequest(steamId, vehicleId, vehicleInfo.type, vehicleInfo);
            }

        } catch (error) {
            console.error('Erro ao processar comando de veículo:', error);
        }
    }

    async processVehicleMountCommand(steamId, vehicleId, vehicleType) {
        try {
            // Verificar se é um comando válido
            if (!vehicleId || isNaN(vehicleId)) {
                await this.sendVehicleMountErrorEmbed('Comando inválido', `/rm ${vehicleId}`);
                return;
            }

            // Verificar cooldown (silencioso - não envia embed)
            if (this.isOnCooldown(steamId)) {
                logger.warn("Cooldown ativo", { steamId, command: "rm", cooldownSeconds: 30 });
                return;
            }

            // Consultar informações do veículo no banco
            let vehicleInfo;
            try {
                vehicleInfo = await getVehicleInfo(vehicleId);
                logger.info("Informações do veículo obtidas para montagem", { vehicleId, name: vehicleInfo.name, type: vehicleInfo.type });
            } catch (error) {
                logger.error("Erro ao consultar veículo no banco para montagem", { vehicleId, error: error.message });
                await this.sendVehicleMountErrorEmbed(`Veículo com ID ${vehicleId} não encontrado no banco de dados`, `/rm ${vehicleId}`);
                return;
            }

            // Verificar se usuário está vinculado
            const linkedUsersPath = path.join(this.dataPath, 'linked_users.json');
            let linkedUsers = {};
            
            if (fs.existsSync(linkedUsersPath)) {
                linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            }

            const discordUserId = Object.keys(linkedUsers).find(key => linkedUsers[key].steam_id === steamId);

            if (discordUserId) {
                // Steam ID já vinculado - registrar automaticamente
                logger.info("Usuário já vinculado para montagem", { steamId, discordId: discordUserId });
                try {
                    const discordUser = await this.client.users.fetch(discordUserId);
                    await this.registerVehicleMount(vehicleId, vehicleInfo.type, steamId, discordUser, vehicleInfo);
                    this.setCooldown(steamId);
                    logger.info("Registro de montagem automático", { vehicleId, steamId, method: "automático" });
                } catch (error) {
                    logger.warn("Discord ID inválido", { discordUserId });
                    // Se o Discord ID não for válido, criar nova solicitação pendente
                    await this.createPendingMountRequest(steamId, vehicleId, vehicleInfo.type, vehicleInfo);
                }
                
            } else {
                // Steam ID não vinculado - criar solicitação pendente
                logger.info("Usuário não vinculado para montagem", { steamId, status: "pendente" });
                await this.createPendingMountRequest(steamId, vehicleId, vehicleInfo.type, vehicleInfo);
            }

        } catch (error) {
            console.error('Erro ao processar comando de montagem de veículo:', error);
        }
    }

    async processVehicleDenounceCommand(steamId, vehicleId, location) {
        try {
            // Verificar se é um comando válido
            if (!vehicleId || isNaN(vehicleId)) {
                await this.sendVehicleDenounceErrorEmbed('Comando inválido', `/dv ${vehicleId}`);
                return;
            }

            // Verificar cooldown (silencioso - não envia embed)
            if (this.isOnCooldown(steamId)) {
                logger.warn("Cooldown ativo", { steamId, command: "dv", cooldownSeconds: 60 });
                return;
            }

            logger.info("Processando denúncia de veículo", { vehicleId, steamId, status: "processando" });
    

            // Verificar se veículo está registrado
            const isRegistered = await this.checkVehicleRegistration(vehicleId);
    
            
            if (isRegistered) {
                logger.warn("Denúncia já registrada", { vehicleId, steamId, status: "já registrado" });
                // Veículo já registrado - enviar embed informativo
                await this.sendVehicleAlreadyRegisteredEmbed(vehicleId, isRegistered, steamId);
            } else {
                logger.info("Denúncia de veículo criada", { vehicleId, steamId, status: "criada" });
                // Veículo não registrado - criar denúncia
                await this.createVehicleDenunciation(steamId, vehicleId, location);
            }

            // Definir cooldown
            this.setCooldown(steamId);

        } catch (error) {
            console.error('Erro ao processar denúncia de veículo:', error);
        }
    }

    async processVehicleMountCompleteCommand(steamId, vehicleId) {
        try {
            // Verificar se é um comando válido
            if (!vehicleId || isNaN(vehicleId)) {
                await this.sendVehicleMountCompleteErrorEmbed('Comando inválido', `/mc ${vehicleId}`);
                return;
            }

            // Verificar cooldown (silencioso - não envia embed)
            if (this.isOnCooldown(steamId)) {
                logger.warn("Cooldown ativo", { steamId, command: "mc", cooldownSeconds: 30 });
                return;
            }

            // Verificar se o veículo existe no registro de montagem
            const mountRegistrationsPath = path.join(this.dataPath, 'vehicle_mount_registrations.json');
            let mountRegistrations = {};
            
            if (fs.existsSync(mountRegistrationsPath)) {
                mountRegistrations = JSON.parse(fs.readFileSync(mountRegistrationsPath, 'utf8'));
            }

            if (!mountRegistrations[vehicleId]) {
                logger.error("Veículo não encontrado no registro de montagem", { vehicleId });
                await this.sendVehicleMountCompleteErrorEmbed(`Veículo ${vehicleId} não está registrado para montagem`, `/mc ${vehicleId}`);
                return;
            }

            // Verificar se já foi concluído anteriormente
            const completedRegistrationsPath = path.join(this.dataPath, 'vehicle_mount_completed.json');
            let completedRegistrations = {};
            
            if (fs.existsSync(completedRegistrationsPath)) {
                completedRegistrations = JSON.parse(fs.readFileSync(completedRegistrationsPath, 'utf8'));
            }

            if (completedRegistrations[vehicleId]) {
                logger.warn("Montagem já foi concluída anteriormente", { vehicleId });
                await this.sendVehicleMountCompleteErrorEmbed(`Montagem do veículo ${vehicleId} já foi concluída`, `/mc ${vehicleId}`);
                return;
            }

            // Verificar se usuário está vinculado
            const linkedUsersPath = path.join(this.dataPath, 'linked_users.json');
            let linkedUsers = {};
            
            if (fs.existsSync(linkedUsersPath)) {
                linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            }


            
            const discordUserId = Object.keys(linkedUsers).find(key => linkedUsers[key].steam_id === steamId);

            if (discordUserId) {
                // Steam ID já vinculado - processar conclusão automaticamente
                logger.info("Usuário já vinculado para conclusão", { steamId, discordId: discordUserId });
                try {
                    const discordUser = await this.client.users.fetch(discordUserId);
                    await this.completeVehicleMount(vehicleId, steamId, discordUser);
                    this.setCooldown(steamId);
                    logger.info("Registro de conclusão de montagem automático", { vehicleId, steamId, method: "automático" });
                } catch (error) {
                    logger.warn("Discord ID inválido", { discordUserId });
                    // Se o Discord ID não for válido, criar nova solicitação pendente
                    await this.createPendingMountCompleteRequest(steamId, vehicleId);
                }
                
            } else {
                // Steam ID não vinculado - criar solicitação pendente
                logger.info("Usuário não vinculado para conclusão", { steamId, status: "pendente" });
                await this.createPendingMountCompleteRequest(steamId, vehicleId);
            }

        } catch (error) {
            console.error('Erro ao processar comando de conclusão de montagem:', error);
        }
    }

    async createPendingRequest(steamId, vehicleId, vehicleType) {
        const pendingPath = path.join(this.dataPath, 'pending_requests.json');
        let pendingRequests = {};
        
        try {
            if (fs.existsSync(pendingPath)) {
                pendingRequests = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar solicitações pendentes:', error);
        }

        const now = new Date();
        const timeoutMs = this.config.discord_bot.features.user_linking.link_button_timeout;
        const expiresAt = new Date(now.getTime() + timeoutMs);

        pendingRequests[steamId] = {
            vehicleId: vehicleId,
            vehicleType: vehicleType,
            requestedAt: now.toISOString(),
            expiresAt: expiresAt.toISOString(),
            channelId: this.config.discord_bot.channels.vehicle_registration
        };

        fs.writeFileSync(pendingPath, JSON.stringify(pendingRequests, null, 2));

        // Enviar embed de vinculação
        await this.sendLinkEmbed(steamId, vehicleId, vehicleType);
        
        logger.info("Solicitação pendente criada", { steamId });
    }

    async createPendingMountRequest(steamId, vehicleId, vehicleType) {
        const pendingPath = path.join(this.dataPath, 'pending_mount_requests.json');
        let pendingRequests = {};
        
        try {
            if (fs.existsSync(pendingPath)) {
                pendingRequests = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar solicitações pendentes de montagem:', error);
        }

        const now = new Date();
        const timeoutMs = this.config.discord_bot.features.user_linking.link_button_timeout;
        const expiresAt = new Date(now.getTime() + timeoutMs);

        pendingRequests[steamId] = {
            vehicleId: vehicleId,
            vehicleType: vehicleType,
            requestedAt: now.toISOString(),
            expiresAt: expiresAt.toISOString(),
            channelId: this.config.discord_bot.channels.vehicle_mount_registration
        };

        fs.writeFileSync(pendingPath, JSON.stringify(pendingRequests, null, 2));

        // Enviar embed de vinculação para montagem
        await this.sendVehicleMountLinkEmbed(steamId, vehicleId, vehicleType);
        
        logger.info("Solicitação pendente de montagem criada", { steamId });
    }

    async checkVehicleRegistration(vehicleId) {
        try {
            logger.debug("Verificando registro do veículo", { vehicleId });
            
            // Verificar no registro de veículos (vehicle_registrations.json)
            const vehicleRegistrationsPath = path.join(this.dataPath, 'vehicle_registrations.json');
            
            if (fs.existsSync(vehicleRegistrationsPath)) {
                const vehicleRegistrations = JSON.parse(fs.readFileSync(vehicleRegistrationsPath, 'utf8'));
                
                if (vehicleRegistrations[vehicleId]) {
                    return { type: 'vehicle', registration: vehicleRegistrations[vehicleId] };
                }
            }

            // Verificar no registro de montagem (vehicle_mount_registrations.json)
            const mountRegistrationsPath = path.join(this.dataPath, 'vehicle_mount_registrations.json');
            
            if (fs.existsSync(mountRegistrationsPath)) {
                const mountRegistrations = JSON.parse(fs.readFileSync(mountRegistrationsPath, 'utf8'));
                
                if (mountRegistrations[vehicleId]) {
                    return { type: 'mount', registration: mountRegistrations[vehicleId] };
                }
            }
            return null; // Veículo não encontrado
        } catch (error) {
            console.error('Erro ao verificar registro de veículo:', error);
            return null;
        }
    }

    async createPendingMountCompleteRequest(steamId, vehicleId) {
        const pendingPath = path.join(this.dataPath, 'pending_mount_complete_requests.json');
        let pendingRequests = {};
        
        try {
            if (fs.existsSync(pendingPath)) {
                pendingRequests = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            }
        } catch (error) {
            console.error('Erro ao carregar solicitações pendentes de conclusão de montagem:', error);
        }

        const now = new Date();
        const timeoutMs = this.config.discord_bot.features.user_linking.link_button_timeout;
        const expiresAt = new Date(now.getTime() + timeoutMs);

        pendingRequests[steamId] = {
            vehicleId: vehicleId,
            requestedAt: now.toISOString(),
            expiresAt: expiresAt.toISOString(),
            channelId: this.config.discord_bot.channels.vehicle_mount_registration
        };

        fs.writeFileSync(pendingPath, JSON.stringify(pendingRequests, null, 2));

        // Enviar embed de vinculação para conclusão de montagem
        await this.sendVehicleMountCompleteLinkEmbed(steamId, vehicleId);
        
        logger.info("Solicitação pendente de conclusão criada", { steamId });
    }

    setVehicleControl(vehicleControl) {
        this.vehicleControl = vehicleControl;
        logger.info('Sistema de controle de veículos conectado ao bot');
    }

    async start() {
        if (!this.config || !this.config.discord_bot || !this.config.discord_bot.enabled) {
            logger.error("Bot Discord desabilitado na configuração");
            return;
        }

        try {
            await this.client.login(this.config.discord_bot.token);
            logger.bot("Bot Discord iniciado com sucesso");
        } catch (error) {
            console.error('❌ Erro ao iniciar bot Discord:', error);
        }
    }

    async stop() {
        try {
            await this.client.destroy();
            logger.info("Bot Discord parado");
        } catch (error) {
            console.error('❌ Erro ao parar bot Discord:', error);
        }
    }

    async sendDuplicateVehicleEmbed(vehicleId, existingRegistration, commandType) {
        try {
            // Determinar o canal correto baseado no tipo de comando
            const channelId = commandType === 'rm' 
                ? this.config.discord_bot.channels.vehicle_mount_registration 
                : this.config.discord_bot.channels.vehicle_registration;
            
            const channel = await this.client.channels.fetch(channelId);
            
            const commandName = commandType === 'rm' ? 'Registro de Montagem' : 'Registro de Veículo';
            const embedColor = commandType === 'rm' ? '#ff8800' : '#ffaa00';
            
            const embed = new EmbedBuilder()
                .setTitle(`⚠️ ${commandName} - Veículo Já Cadastrado`)
                .setDescription(`**O veículo ${vehicleId} já está registrado no sistema!**`)
                .addFields(
                    { name: '**ID do Veículo:**', value: vehicleId, inline: true },
                    { name: '**Tipo do Veículo:**', value: existingRegistration.vehicleType, inline: true },
                    { name: '**Registrado por:**', value: `<@${existingRegistration.discordUserId}>`, inline: true },
                    { name: '**Data do Registro:**', value: this.formatDateTime(existingRegistration.registeredAt), inline: false },
                    { name: '**Comando usado:**', value: `/${commandType} ${vehicleId} ${existingRegistration.vehicleType}`, inline: false }
                )
                .setColor(embedColor)
                .setFooter({ text: `Tente usar um ID diferente ou verifique se o veículo já foi registrado` })
                .setTimestamp();

            await channel.send({ embeds: [embed] });
            logger.warn("Embed de duplicação enviado", { vehicleId, commandType });
            
        } catch (error) {
            console.error('Erro ao enviar embed de aviso sobre duplicação:', error);
        }
    }

    async sendVehicleMountCompleteErrorEmbed(error, command) {
        try {
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_mount_registration);
            
            const embed = new EmbedBuilder()
                .setTitle('❌ Erro na Conclusão de Montagem')
                .setDescription(`**Problema:** ${error}`)
                .addFields(
                    { name: '**Comando usado:**', value: command, inline: true },
                    { name: '**Formato correto:**', value: '/mc <ID_NÚMERO>', inline: true },
                    { name: '**Exemplo:**', value: '/mc 1654510', inline: false }
                )
                .setColor('#ff0000')
                .setTimestamp();

            await channel.send({ embeds: [embed] });
            
        } catch (error) {
            console.error('Erro ao enviar embed de erro de conclusão de montagem:', error);
        }
    }

    async sendVehicleMountCompleteSuccessEmbed(completedRegistration) {
        try {
            console.log('🚀 Iniciando envio do embed de montagem concluída...');
            console.log('📊 Dados do registro:', {
                vehicleId: completedRegistration.vehicleId,
                vehicleType: completedRegistration.vehicleType,
                vehicleInfo: completedRegistration.vehicleInfo
            });
            
            // Enviar embed para o canal de registro de veículos (onde o veículo será transferido)
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_registration);
            console.log('📺 Canal obtido:', channel?.id);
            
            const embed = new EmbedBuilder()
                .setTitle('✅ Montagem de Veículo Concluída')
                .setDescription(`**Montagem do veículo ${completedRegistration.vehicleId} concluída com sucesso!**`)
                .addFields(
                    { name: '**Nome do Veículo:**', value: `${completedRegistration.vehicleType} MONTADO`, inline: true },
                    { name: '**ID do Veículo:**', value: completedRegistration.vehicleId, inline: true },
                    { name: '**Registrado por:**', value: `<@${completedRegistration.discordUserId}>`, inline: true },
                    { name: '**Data/Hora:**', value: this.formatDateTime(completedRegistration.completedAt), inline: false }
                )
                .setColor('#00ff00')
                .setFooter({ text: 'Registro automático via comando /mc' })
                .setTimestamp();

            // Adicionar imagem do veículo se disponível
            if (completedRegistration.vehicleInfo && completedRegistration.vehicleInfo.imageFile) {
                const imagePath = path.join(__dirname, 'data', 'imagens', 'carros', completedRegistration.vehicleInfo.imageFile);
                console.log('🖼️ Tentando enviar imagem:', imagePath);
                console.log('📁 Arquivo existe:', fs.existsSync(imagePath));
                
                if (fs.existsSync(imagePath)) {
                    embed.setThumbnail(`attachment://${completedRegistration.vehicleInfo.imageFile}`);
                    console.log('✅ Enviando embed com imagem');
                    await channel.send({ 
                        embeds: [embed], 
                        files: [{ 
                            attachment: imagePath, 
                            name: completedRegistration.vehicleInfo.imageFile 
                        }] 
                    });
                } else {
                    console.log('⚠️ Imagem não encontrada, enviando embed sem imagem');
                    await channel.send({ embeds: [embed] });
                }
            } else {
                console.log('⚠️ Sem informações de imagem, enviando embed básico');
                await channel.send({ embeds: [embed] });
            }
            
            console.log('✅ Embed de montagem concluída enviado com sucesso!');
            logger.info("Embed de sucesso enviado para montagem concluída");
            
        } catch (error) {
            console.error('❌ Erro ao enviar embed de sucesso para montagem concluída:', error);
            logger.error('Erro ao enviar embed de montagem concluída', { error: error.message });
        }
    }

    async sendVehicleMountCompleteLinkEmbed(steamId, vehicleId) {
        try {
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_mount_registration);
            
            const maskedSteamId = this.maskSteamId(steamId);
            
            const embed = new EmbedBuilder()
                .setTitle('✅ Conclusão de Montagem Detectada')
                .setDescription('⚠️ Aguardando Vinculação')
                .addFields(
                    { name: '**Steam ID:**', value: maskedSteamId, inline: true },
                    { name: '**ID do Veículo:**', value: vehicleId, inline: true },
                    { name: '**Data/Hora:**', value: this.formatDateTime(new Date().toISOString()), inline: false },
                    { name: '**Steam ID Original:**', value: steamId, inline: false }
                )
                .setColor('#00ff00')
                .setFooter({ text: 'Clique no botão abaixo para vincular sua conta Discord' })
                .setTimestamp();

            const button = new ActionRowBuilder()
                .addComponents(
                    new ButtonBuilder()
                        .setCustomId('link_discord_mount_complete')
                        .setLabel('🔗 Vincular Discord')
                        .setStyle(ButtonStyle.Primary)
                );

            const message = await channel.send({ embeds: [embed], components: [button] });
            
            // Salvar ID da mensagem para deletar depois
            const pendingPath = path.join(this.dataPath, 'pending_mount_complete_requests.json');
            let pendingRequests = {};
            
            if (fs.existsSync(pendingPath)) {
                pendingRequests = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
            }
            
            if (pendingRequests[steamId]) {
                pendingRequests[steamId].messageId = message.id;
                fs.writeFileSync(pendingPath, JSON.stringify(pendingRequests, null, 2));
            }
            
            logger.info("Embed de vinculação de conclusão enviado", { steamId, status: "pendente" });
            
        } catch (error) {
            console.error('Erro ao enviar embed de vinculação para conclusão de montagem:', error);
        }
    }

    async sendVehicleAlreadyRegisteredEmbed(vehicleId, registrationInfo, steamId) {
        try {
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_denunciation);
            
            const registration = registrationInfo.registration;
            const type = registrationInfo.type === 'vehicle' ? 'Registro de Veículo' : 'Registro de Montagem';
            const color = registrationInfo.type === 'vehicle' ? '#00ff00' : '#ff8800';
            
            // Obter nome do personagem do Steam ID
            const playerName = await this.getPlayerNameFromSteamId(steamId);
            
            // Verificar se Steam ID está vinculado ao Discord
            const linkedUsersPath = path.join(this.dataPath, 'linked_users.json');
            let linkedUsers = {};
            
            if (fs.existsSync(linkedUsersPath)) {
                linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            }
            
            const discordUserId = Object.keys(linkedUsers).find(key => linkedUsers[key].steam_id === steamId);
            let denouncerInfo = `Steam ID: ${this.maskSteamId(steamId)}`;
            
            if (playerName) {
                denouncerInfo += `\nPersonagem: ${playerName}`;
            }
            
            if (discordUserId) {
                denouncerInfo += `\nDiscord: <@${discordUserId}>`;
            } else {
                denouncerInfo += `\nDiscord: Não vinculado`;
            }
            
            const embed = new EmbedBuilder()
                .setTitle('✅ Veículo Já Registrado')
                .setDescription(`**O veículo ${vehicleId} já está registrado no sistema!**`)
                .addFields(
                    { name: '**ID do Veículo:**', value: vehicleId, inline: true },
                    { name: '**Tipo de Registro:**', value: type, inline: true },
                    { name: '**Registrado por:**', value: `<@${registration.discordUserId}>`, inline: true },
                    { name: '**Data do Registro:**', value: this.formatDateTime(registration.registeredAt), inline: false },
                    { name: '**Denunciado por:**', value: denouncerInfo, inline: false }
                )
                .setColor(color)
                .setFooter({ text: 'Veículo já está no sistema - denúncia ignorada' })
                .setTimestamp();

            await channel.send({ embeds: [embed] });
            logger.info("Embed de veículo já registrado enviado", { vehicleId });
            
        } catch (error) {
            console.error('Erro ao enviar embed de veículo já registrado:', error);
        }
    }

    async createVehicleDenunciation(steamId, vehicleId, location) {
        try {
            console.log('🚀 Iniciando criação de denúncia de veículo...');
            console.log('📊 Dados da denúncia:', { vehicleId, steamId, location });
            
            // Consultar informações do veículo no banco
            let vehicleInfo = null;
            try {
                vehicleInfo = await getVehicleInfo(vehicleId);
                logger.info("Informações do veículo obtidas para denúncia", { vehicleId, name: vehicleInfo.name, type: vehicleInfo.type });
            } catch (error) {
                logger.error("Erro ao consultar veículo no banco para denúncia", { vehicleId, error: error.message });
                // Continuar sem as informações do banco
            }
            
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_denunciation);
            console.log('📺 Canal obtido:', channel?.id);
            
            // Extrair coordenadas da localização
            const coordMatch = location.match(/X=([-\d.]+)\s+Y=([-\d.]+)\s+Z=([-\d.]+)/);
            const coords = coordMatch ? {
                x: parseFloat(coordMatch[1]),
                y: parseFloat(coordMatch[2]),
                z: parseFloat(coordMatch[3])
            } : null;
            
            // Obter nome do personagem do Steam ID
            const playerName = await this.getPlayerNameFromSteamId(steamId);
            
            // Verificar se Steam ID está vinculado ao Discord
            const linkedUsersPath = path.join(this.dataPath, 'linked_users.json');
            let linkedUsers = {};
            
            if (fs.existsSync(linkedUsersPath)) {
                linkedUsers = JSON.parse(fs.readFileSync(linkedUsersPath, 'utf8'));
            }
            
            const discordUserId = Object.keys(linkedUsers).find(key => linkedUsers[key].steam_id === steamId);
            let denouncerInfo = `Steam ID: ${this.maskSteamId(steamId)}`;
            
            if (playerName) {
                denouncerInfo += `\nPersonagem: ${playerName}`;
            }
            
            if (discordUserId) {
                denouncerInfo += `\nDiscord: <@${discordUserId}>`;
            } else {
                denouncerInfo += `\nDiscord: Não vinculado`;
            }
            
            const embed = new EmbedBuilder()
                .setTitle('🚨 Denúncia de Veículo')
                .setDescription(`**Veículo ${vehicleId} denunciado como não registrado!**`)
                .addFields(
                    { name: '**ID do Veículo:**', value: vehicleId, inline: true },
                    { name: '**Denunciado por:**', value: denouncerInfo, inline: true },
                    { name: '**Data/Hora:**', value: this.formatDateTime(new Date().toISOString()), inline: false },
                    { name: '**Localização:**', value: location, inline: false }
                )
                .setColor('#ff0000')
                .setFooter({ text: 'Aguardando verificação por Staff/Adm' })
                .setTimestamp();

            if (coords) {
                embed.addFields({ name: '**Coordenadas:**', value: `X: ${coords.x}\nY: ${coords.y}\nZ: ${coords.z}`, inline: false });
            }

            const button = new ActionRowBuilder()
                .addComponents(
                    new ButtonBuilder()
                        .setCustomId('verify_denunciation')
                        .setLabel('🔍 Verificar Denúncia')
                        .setStyle(ButtonStyle.Danger)
                );

            // Adicionar imagem do veículo se disponível
            if (vehicleInfo && vehicleInfo.imageFile) {
                const imagePath = path.join(__dirname, 'data', 'imagens', 'carros', vehicleInfo.imageFile);
                console.log('🖼️ Tentando enviar imagem:', imagePath);
                console.log('📁 Arquivo existe:', fs.existsSync(imagePath));
                
                if (fs.existsSync(imagePath)) {
                    embed.setThumbnail(`attachment://${vehicleInfo.imageFile}`);
                    console.log('✅ Enviando embed com imagem');
                    const message = await channel.send({ 
                        embeds: [embed], 
                        components: [button],
                        files: [{ 
                            attachment: imagePath, 
                            name: vehicleInfo.imageFile 
                        }] 
                    });
                } else {
                    console.log('⚠️ Imagem não encontrada, enviando embed sem imagem');
                    const message = await channel.send({ embeds: [embed], components: [button] });
                }
            } else {
                console.log('⚠️ Sem informações de imagem, enviando embed básico');
                const message = await channel.send({ embeds: [embed], components: [button] });
            }
            
            // Salvar denúncia
            await this.saveDenunciation(steamId, vehicleId, location, message.id);
            
            console.log('✅ Denúncia de veículo criada com sucesso!');
            logger.info("Denúncia de veículo criada", { vehicleId, steamId, status: "criada" });
            
        } catch (error) {
            console.error('❌ Erro ao criar denúncia de veículo:', error);
            logger.error('Erro ao criar denúncia de veículo', { error: error.message });
        }
    }

    async saveDenunciation(steamId, vehicleId, location, messageId) {
        try {
            const denunciationsPath = path.join(this.dataPath, 'vehicle_denunciations.json');
            let denunciations = [];
            
            if (fs.existsSync(denunciationsPath)) {
                denunciations = JSON.parse(fs.readFileSync(denunciationsPath, 'utf8'));
            }

            const denunciation = {
                id: `dv_${vehicleId}_${Date.now()}`,
                vehicleId: vehicleId,
                steamId: steamId,
                location: location,
                messageId: messageId,
                status: 'pending',
                createdAt: new Date().toISOString(),
                verifiedBy: null,
                verifiedAt: null
            };

            denunciations.push(denunciation);
            fs.writeFileSync(denunciationsPath, JSON.stringify(denunciations, null, 2));
            
            logger.info("Denúncia salva", { denunciationId: denunciation.id });
            
        } catch (error) {
            console.error('Erro ao salvar denúncia:', error);
        }
    }

    async updateDenunciationStatus(vehicleId, verifiedBy) {
        try {
            const denunciationsPath = path.join(this.dataPath, 'vehicle_denunciations.json');
            
            if (!fs.existsSync(denunciationsPath)) {
                logger.error("Arquivo de denúncias não encontrado");
                return;
            }

            const denunciations = JSON.parse(fs.readFileSync(denunciationsPath, 'utf8'));
            
            // Encontrar a denúncia mais recente para este veículo
            const denunciation = denunciations
                .filter(d => d.vehicleId === vehicleId)
                .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))[0];

            if (denunciation) {
                denunciation.status = 'verified';
                denunciation.verifiedBy = verifiedBy;
                denunciation.verifiedAt = new Date().toISOString();

                fs.writeFileSync(denunciationsPath, JSON.stringify(denunciations, null, 2));
                logger.info("Denúncia de veículo verificada", { vehicleId, verifiedBy, steamId: denunciation.steamId, status: "verificada" });
            } else {
                logger.warn("Denúncia não encontrada", { vehicleId });
            }
            
        } catch (error) {
            console.error('Erro ao atualizar status da denúncia:', error);
        }
    }

    async sendVehicleDenounceErrorEmbed(error, command) {
        try {
            const channel = await this.client.channels.fetch(this.config.discord_bot.channels.vehicle_denunciation);
            
            const embed = new EmbedBuilder()
                .setTitle('❌ Erro na Denúncia de Veículo')
                .setDescription(`**Problema:** ${error}`)
                .addFields(
                    { name: '**Comando usado:**', value: command, inline: true },
                    { name: '**Formato correto:**', value: '/dv <ID_NÚMERO> <LOCALIZAÇÃO>', inline: true },
                    { name: '**Exemplo:**', value: '/dv 11005 {X=163061.547 Y=-98354.172 Z=30424.414}', inline: false }
                )
                .setColor('#ff0000')
                .setTimestamp();

            await channel.send({ embeds: [embed] });
            
        } catch (error) {
            console.error('Erro ao enviar embed de erro de denúncia:', error);
        }
    }
}

module.exports = DiscordBot; 