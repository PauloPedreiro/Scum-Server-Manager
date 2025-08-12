const { Client, GatewayIntentBits, EmbedBuilder, AttachmentBuilder } = require('discord.js');
const fs = require('fs');
const path = require('path');
const logger = require('./logger');

class DonationChannelManager {
    constructor(config) {
        this.config = config;
        this.client = null;
        this.channelName = 'ℹ️┃𝐃𝐨𝐧𝐚𝐭𝐞-𝐃𝐨𝐚𝐜̧𝐚̃𝐨'; // Nome com emoji, separador e hífen
        this.logoPath = path.join(__dirname, 'data', 'imagens', 'LogoSSM', 'Logo_SSM.png');
        
        console.log('🔧 DonationChannelManager inicializado');
        console.log('📁 Caminho do logo:', this.logoPath);
        console.log('📁 Logo existe:', fs.existsSync(this.logoPath));
    }

    async initialize() {
        try {
            console.log('🚀 Iniciando DonationChannelManager...');
            
            if (!this.config.discord_bot || !this.config.discord_bot.token) {
                console.log('❌ Token do Discord não configurado');
                logger.warn('Token do Discord não configurado, pulando criação do canal de doação');
                return false;
            }

            console.log('✅ Token do Discord encontrado');
            console.log('🏠 Guild ID:', this.config.discord_bot.guild_id);

            this.client = new Client({
                intents: [
                    GatewayIntentBits.Guilds,
                    GatewayIntentBits.GuildMessages,
                    GatewayIntentBits.MessageContent
                ]
            });

            console.log('🔗 Conectando ao Discord...');
            await this.client.login(this.config.discord_bot.token);
            console.log('✅ Cliente Discord conectado');
            logger.info('Cliente Discord conectado para criação do canal de doação');

            return await this.setupDonationChannel();
        } catch (error) {
            console.error('❌ Erro na inicialização:', error.message);
            logger.error('Erro ao inicializar gerenciador de canal de doação', { error: error.message });
            return false;
        }
    }

    async setupDonationChannel() {
        try {
            console.log('🔍 Buscando guild...');
            const guild = await this.client.guilds.fetch(this.config.discord_bot.guild_id);
            if (!guild) {
                console.log('❌ Guild não encontrada');
                logger.error('Guild não encontrada para criação do canal de doação');
                return false;
            }

            console.log('✅ Guild encontrada:', guild.name);

            // Forçar carregamento dos canais
            await guild.channels.fetch();

            // Verificar se o canal já existe
            console.log('🔍 Verificando se o canal já existe...');
            
            // Buscar por canais que contenham "Donate" ou "Doação" no nome
            const existingChannel = guild.channels.cache.find(channel => {
                const channelName = channel.name.toLowerCase();
                const hasDonate = channelName.includes('donate');
                const hasDoacao = channelName.includes('doação') || channelName.includes('doacao');
                const exactMatch = channelName === this.channelName.toLowerCase();
                
                return hasDonate || hasDoacao || exactMatch;
            });

            if (existingChannel) {
                console.log('✅ Canal de doação já existe:', existingChannel.name);
                
                // Verificar se já tem mensagens de doação
                try {
                    const messages = await existingChannel.messages.fetch({ limit: 10 });
                    const hasDonationMessage = messages.some(msg => 
                        msg.author.id === this.client.user.id && 
                        msg.embeds.length > 0 && 
                        msg.embeds[0].title === '💝 Faça uma Doação'
                    );
                    
                    if (hasDonationMessage) {
                        console.log('✅ Canal já possui mensagem de doação, pulando...');
                        logger.info('Canal de doação já existe com mensagem, pulando criação', { 
                            channelId: existingChannel.id,
                            channelName: existingChannel.name 
                        });
                        return true;
                    } else {
                        console.log('📝 Canal existe mas não tem mensagem de doação, enviando...');
                        await this.sendDonationEmbed(existingChannel);
                        return true;
                    }
                } catch (error) {
                    console.log('⚠️ Erro ao verificar mensagens, enviando nova mensagem...');
                    await this.sendDonationEmbed(existingChannel);
                    return true;
                }
            } else {
                console.log('📝 Criando novo canal de doação...');
            }

            console.log('📝 Criando novo canal de doação...');
            // Criar o canal no topo do servidor
            const newChannel = await guild.channels.create({
                name: this.channelName,
                type: 0, // Text channel
                position: 0, // Posição no topo
                topic: 'Canal oficial para doações e suporte ao servidor',
                reason: 'Criação automática do canal de doação'
            });

            console.log('✅ Canal de doação criado com sucesso:', newChannel.name);
            logger.info('Canal de doação criado com sucesso', { 
                channelId: newChannel.id,
                channelName: newChannel.name 
            });

            // Enviar embed de doação
            console.log('📤 Enviando embed de doação...');
            await this.sendDonationEmbed(newChannel);

            return true;
        } catch (error) {
            console.error('❌ Erro ao configurar canal:', error.message);
            logger.error('Erro ao configurar canal de doação', { error: error.message });
            return false;
        }
    }

    async sendDonationEmbed(channel) {
        try {
            console.log('🎨 Preparando embed de doação...');
            
            // Verificar se o arquivo de logo existe
            let attachment = null;
            if (fs.existsSync(this.logoPath)) {
                console.log('✅ Logo encontrado, anexando...');
                attachment = new AttachmentBuilder(this.logoPath, { name: 'logo_ssm.png' });
            } else {
                console.log('⚠️ Logo não encontrado, continuando sem imagem');
            }

            const embed = new EmbedBuilder()
                .setTitle('💝 Faça uma Doação')
                .setDescription('Ajude para manter o projeto do SCUM Server Manager!')
                .setColor('#FF6B6B')
                .setImage(attachment ? 'attachment://logo_ssm.png' : null) // Logo maior como imagem principal
                .addFields(
                    {
                        name: '💳 Cartão de Crédito/Débito',
                        value: '[Clique aqui para doar via Mercado Pago](https://link.mercadopago.com.br/scum)',
                        inline: false
                    },
                    {
                        name: '💸 PayPal',
                        value: '[Clique aqui para doar via PayPal](https://www.paypal.com/donate/?hosted_button_id=M5252YJR7KJUN)',
                        inline: false
                    },
                    {
                        name: '⚡ PIX',
                        value: '[Clique aqui para doar via PIX](https://nubank.com.br/cobrar/11dh0n/686a7d58-9cbf-4c90-a6bb-39c21dda7527)',
                        inline: false
                    }
                )
                .addFields(
                    {
                        name: '🎯 Como sua doação nos ajuda:',
                        value: '• Custos de criação e desenvolvimento\n• Novas implementações e funcionalidades\n• Melhorias na infraestrutura\n• Manutenção e atualizações do projeto',
                        inline: false
                    }
                )
                .setFooter({ 
                    text: 'SCUM Server Manager - Agradecemos seu apoio!',
                    iconURL: attachment ? 'attachment://logo_ssm.png' : null
                })
                .setTimestamp();

            const messageOptions = {
                embeds: [embed]
            };

            if (attachment) {
                messageOptions.files = [attachment];
            }

            console.log('📤 Enviando mensagem para o canal...');
            await channel.send(messageOptions);
            console.log('✅ Embed de doação enviado com sucesso');
            logger.info('Embed de doação enviado com sucesso', { channelId: channel.id });

        } catch (error) {
            console.error('❌ Erro ao enviar embed:', error.message);
            logger.error('Erro ao enviar embed de doação', { error: error.message });
        }
    }

    async cleanup() {
        try {
            if (this.client) {
                await this.client.destroy();
                console.log('🔌 Cliente Discord desconectado');
                logger.info('Cliente Discord desconectado do gerenciador de doação');
            }
        } catch (error) {
            console.error('❌ Erro ao limpar:', error.message);
            logger.error('Erro ao limpar gerenciador de doação', { error: error.message });
        }
    }
}

module.exports = DonationChannelManager;
