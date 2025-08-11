const SquadEmbedManager = require('./src/squad_embed_manager');
const DiscordBot = require('./src/bot');

async function forceInitializeSquads() {
    try {
        console.log('🔄 Iniciando força inicialização dos squads...');
        
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
        
        // Obter dados dos squads
        const SquadsManager = require('./src/squads');
        const squadsManager = new SquadsManager();
        const currentSquads = await squadsManager.getSquadsData();
        
        console.log(`📋 Squads obtidos: ${Object.keys(currentSquads).length}`);
        
        // Forçar inicialização
        console.log('🔄 Forçando inicialização dos squads...');
        await squadEmbedManager.initializeSquads(currentSquads);
        
        console.log('✅ Inicialização forçada concluída!');
        
        // Parar o bot
        await discordBot.stop();
        console.log('🛑 Bot parado');
        
    } catch (error) {
        console.error('❌ Erro na força inicialização:', error.message);
    }
}

forceInitializeSquads(); 