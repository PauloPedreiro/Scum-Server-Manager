const fs = require('fs');
const path = require('path');

function cleanSquadData() {
    try {
        console.log('🧹 Limpando dados dos squads...');
        
        const squadsPath = path.join(__dirname, 'src', 'data', 'squad', 'squads.json');
        const squadsData = JSON.parse(fs.readFileSync(squadsPath, 'utf8'));
        
        let cleanedCount = 0;
        
        for (const [squadId, squad] of Object.entries(squadsData.squads)) {
            if (squad.embed_message_id) {
                delete squad.embed_message_id;
                console.log(`🧹 Limpo embed_message_id do squad: ${squad.name}`);
                cleanedCount++;
            }
        }
        
        fs.writeFileSync(squadsPath, JSON.stringify(squadsData, null, 2));
        
        console.log(`✅ Limpeza concluída! ${cleanedCount} squads limpos.`);
        console.log('🔄 Agora reinicie o servidor para recriar os embeds automaticamente.');
        
    } catch (error) {
        console.error('❌ Erro ao limpar dados:', error.message);
    }
}

cleanSquadData(); 