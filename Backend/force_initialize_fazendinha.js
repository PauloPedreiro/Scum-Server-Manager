const SquadEmbedManager = require('./src/squad_embed_manager');
const SquadsManager = require('./src/squads');

async function forceInitializeFazendinha() {
    try {
        console.log('🔄 Forçando inicialização do squad Fazendinha GVT...');
        
        // Obter dados dos squads
        const squadsManager = new SquadsManager();
        const squadsData = await squadsManager.getSquadsData();
        
        // Encontrar o squad Fazendinha GVT
        const fazendinhaSquad = Object.values(squadsData.squads).find(squad => 
            squad.name === 'Fazendinha GVT'
        );
        
        if (!fazendinhaSquad) {
            console.log('❌ Squad Fazendinha GVT não encontrado!');
            return;
        }
        
        console.log(`✅ Squad encontrado: ${fazendinhaSquad.name} (ID: ${fazendinhaSquad.id})`);
        console.log(`👥 Membros: ${fazendinhaSquad.members.length}`);
        
        // Criar SquadEmbedManager temporário
        const { Client, GatewayIntentBits } = require('discord.js');
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
        
        // Criar SquadEmbedManager
        const squadEmbedManager = new SquadEmbedManager(client);
        
        // Aguardar um pouco para o bot estar pronto
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Inicializar apenas o squad Fazendinha GVT
        const squadToInitialize = {
            [fazendinhaSquad.id]: fazendinhaSquad
        };
        
        console.log('🔄 Inicializando embed do squad Fazendinha GVT...');
        await squadEmbedManager.initializeSquads(squadToInitialize);
        
        console.log('✅ Squad Fazendinha GVT inicializado com sucesso!');
        
        // Parar o bot
        client.destroy();
        
    } catch (error) {
        console.error('❌ Erro ao inicializar squad:', error.message);
    }
}

forceInitializeFazendinha(); 