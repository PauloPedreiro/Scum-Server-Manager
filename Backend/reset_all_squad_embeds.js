const { Client, GatewayIntentBits } = require('discord.js');
const SquadEmbedManager = require('./src/squad_embed_manager');
const SquadsManager = require('./src/squads');
const fs = require('fs');
const path = require('path');

async function resetAllSquadEmbeds() {
    try {
        console.log('🗑️ Iniciando reset completo dos embeds de squads...');
        
        // Criar cliente Discord
        const client = new Client({ 
            intents: [
                GatewayIntentBits.Guilds,
                GatewayIntentBits.GuildMessages,
                GatewayIntentBits.MessageContent
            ] 
        });
        
        // Aguardar bot conectar
        await new Promise((resolve, reject) => {
            client.once('ready', () => {
                console.log('✅ Bot conectado ao Discord');
                resolve();
            });
            
            client.login(require('./src/data/server/config.json').discord_bot.token);
        });
        
        // Aguardar um pouco para o bot estar pronto
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Obter configuração
        const config = require('./src/data/server/config.json');
        const channelId = config.discord_bot.channels.squads;
        const guild = client.guilds.cache.get(config.discord_bot.guild_id);
        const channel = guild.channels.cache.get(channelId);
        
        if (!channel) {
            throw new Error(`Canal de squads não encontrado: ${channelId}`);
        }
        
        console.log(`✅ Canal encontrado: ${channel.name}`);
        
        // 1. DELETAR TODOS OS EMBEDS EXISTENTES
        console.log('🗑️ Deletando todos os embeds existentes...');
        
        const messages = await channel.messages.fetch({ limit: 100 });
        const squadMessages = messages.filter(msg => 
            msg.author.id === client.user.id && 
            msg.embeds.length > 0 &&
            msg.embeds[0].title && 
            msg.embeds[0].title.includes('Squad:')
        );
        
        console.log(`📋 Encontradas ${squadMessages.size} mensagens de squads para deletar`);
        
        for (const [messageId, message] of squadMessages) {
            try {
                await message.delete();
                console.log(`✅ Mensagem deletada: ${messageId}`);
            } catch (error) {
                console.log(`⚠️ Erro ao deletar mensagem ${messageId}: ${error.message}`);
            }
        }
        
        console.log('✅ Todos os embeds antigos deletados!');
        
        // 2. LIMPAR embed_message_id DOS DADOS
        console.log('🧹 Limpando embed_message_id dos dados...');
        
        const squadsPath = path.join(__dirname, 'src', 'data', 'squad', 'squads.json');
        const squadsData = JSON.parse(fs.readFileSync(squadsPath, 'utf8'));
        
        for (const [squadId, squad] of Object.entries(squadsData.squads)) {
            if (squad.embed_message_id) {
                delete squad.embed_message_id;
                console.log(`🧹 Limpo embed_message_id do squad: ${squad.name}`);
            }
        }
        
        fs.writeFileSync(squadsPath, JSON.stringify(squadsData, null, 2));
        console.log('✅ Dados limpos!');
        
        // 3. RECRIAR TODOS OS EMBEDS
        console.log('🔄 Recriando todos os embeds...');
        
        const squadEmbedManager = new SquadEmbedManager(client);
        
        // Aguardar um pouco para garantir que o canal está limpo
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Obter dados atualizados dos squads
        const squadsManager = new SquadsManager();
        const currentSquads = await squadsManager.getSquadsData();
        
        console.log(`📋 Total de squads para recriar: ${Object.keys(currentSquads.squads).length}`);
        
        // Inicializar todos os squads
        await squadEmbedManager.initializeSquads(currentSquads.squads);
        
        console.log('✅ Todos os embeds recriados com sucesso!');
        
        // 4. VERIFICAR RESULTADO
        console.log('🔍 Verificando resultado...');
        
        const newMessages = await channel.messages.fetch({ limit: 50 });
        const newSquadMessages = newMessages.filter(msg => 
            msg.author.id === client.user.id && 
            msg.embeds.length > 0 &&
            msg.embeds[0].title && 
            msg.embeds[0].title.includes('Squad:')
        );
        
        console.log(`📊 Total de embeds criados: ${newSquadMessages.size}`);
        
        for (const [messageId, message] of newSquadMessages) {
            const embed = message.embeds[0];
            console.log(`📝 ${embed.title} - ID: ${messageId}`);
        }
        
        // Parar o bot
        client.destroy();
        
        console.log('🎉 Reset completo dos embeds concluído com sucesso!');
        
    } catch (error) {
        console.error('❌ Erro no reset dos embeds:', error.message);
    }
}

resetAllSquadEmbeds(); 