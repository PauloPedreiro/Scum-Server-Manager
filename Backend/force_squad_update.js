const SquadEmbedManager = require('./src/squad_embed_manager');
const DiscordBot = require('./src/bot');

async function forceSquadUpdate() {
    try {
        console.log('🔄 Iniciando força atualização dos squads...');
        
        // Inicializar bot Discord
        const discordBot = new DiscordBot();
        await discordBot.start();
        console.log('✅ Bot Discord iniciado');
        
        // Aguardar um pouco para garantir que o bot esteja pronto
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Criar SquadEmbedManager
        const squadEmbedManager = new SquadEmbedManager(discordBot.client);
        console.log('✅ SquadEmbedManager criado');
        
        // Aguardar mais um pouco
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Forçar atualização
        console.log('🔄 Forçando atualização dos squads...');
        await squadEmbedManager.forceUpdateSquads();
        
        console.log('✅ Atualização forçada concluída!');
        
        // Parar o bot
        await discordBot.stop();
        console.log('🛑 Bot parado');
        
    } catch (error) {
        console.error('❌ Erro na força atualização:', error.message);
    }
}

forceSquadUpdate(); 