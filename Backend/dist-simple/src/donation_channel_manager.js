const { Client, GatewayIntentBits, EmbedBuilder, AttachmentBuilder } = require('discord.js');
const fs = require('fs');
const path = require('path');
const logger = require('./logger');

class DonationChannelManager {
    constructor(config) {
        this.config = config;
        this.client = null;
        this.channelName = 'Donate/Doação';
        this.logoPath = path.join(__dirname, 'data', 'imagens', 'LogoSSM', 'Logo_SSM.png');
    }

    async initialize() {
        try {
            if (!this.config.discord_bot || !this.config.discord_bot.token) {
                logger.warn('Token do Discord não configurado, pulando criação do canal de doação');
                return false;
            }

            this.client = new Client({
                intents: [
                    GatewayIntentBits.Guilds,
                    GatewayIntentBits.GuildMessages,
                    GatewayIntentBits.MessageContent
                ]
            });

            await this.client.login(this.config.discord_bot.token);
            logger.info('Cliente Discord conectado para criação do canal de doação');

            return await this.setupDonationChannel();
        } catch (error) {
            logger.error('Erro ao inicializar gerenciador de canal de doação', { error: error.message });
            return false;
        }
    }

    async setupDonationChannel() {
        try {
            const guild = await this.client.guilds.fetch(this.config.discord_bot.guild_id);
            if (!guild) {
                logger.error('Guild não encontrada para criação do canal de doação');
                return false;
            }

            // Verificar se o canal já existe
            const existingChannel = guild.channels.cache.find(
                channel => channel.name.toLowerCase() === this.channelName.toLowerCase()
            );

            if (existingChannel) {
                logger.info('Canal de doação já existe, pulando criação', { 
                    channelId: existingChannel.id,
                    channelName: existingChannel.name 
                });
                return true;
            }

            // Criar o canal no topo do servidor
            const newChannel = await guild.channels.create({
                name: this.channelName,
                type: 0, // Text channel
                position: 0, // Posição no topo
                topic: 'Canal oficial para doações e suporte ao servidor',
                reason: 'Criação automática do canal de doação'
            });

            logger.info('Canal de doação criado com sucesso', { 
                channelId: newChannel.id,
                channelName: newChannel.name 
            });

            // Enviar embed de doação
            await this.sendDonationEmbed(newChannel);

            return true;
        } catch (error) {
            logger.error('Erro ao configurar canal de doação', { error: error.message });
            return false;
        }
    }

    async sendDonationEmbed(channel) {
        try {
            // Verificar se o arquivo de logo existe
            let attachment = null;
            if (fs.existsSync(this.logoPath)) {
                attachment = new AttachmentBuilder(this.logoPath, { name: 'logo_ssm.png' });
            }

            const embed = new EmbedBuilder()
                .setTitle('💝 Faça uma Doação')
                .setDescription('Ajude a manter nosso servidor online e melhorar a experiência de todos os jogadores!')
                .setColor('#FF6B6B')
                .setThumbnail(attachment ? 'attachment://logo_ssm.png' : null)
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
                        value: '• Manutenção do servidor\n• Melhorias na infraestrutura\n• Novos recursos e funcionalidades\n• Suporte técnico 24/7',
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

            await channel.send(messageOptions);
            logger.info('Embed de doação enviado com sucesso', { channelId: channel.id });

        } catch (error) {
            logger.error('Erro ao enviar embed de doação', { error: error.message });
        }
    }

    async cleanup() {
        try {
            if (this.client) {
                await this.client.destroy();
                logger.info('Cliente Discord desconectado do gerenciador de doação');
            }
        } catch (error) {
            logger.error('Erro ao limpar gerenciador de doação', { error: error.message });
        }
    }
}

module.exports = DonationChannelManager;
