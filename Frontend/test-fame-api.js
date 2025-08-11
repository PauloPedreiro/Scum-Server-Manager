import fetch from 'node-fetch';

async function testFameAPI() {
  try {
    console.log('🧪 Testando API de Fama...');
    
    const response = await fetch('http://localhost:3000/api/famepoints', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    
    console.log('✅ API funcionando!');
    console.log('📊 Dados recebidos:');
    console.log(`   • Success: ${data.success}`);
    console.log(`   • Message: ${data.message}`);
    console.log(`   • Total de jogadores: ${data.data.length}`);
    
    if (data.data && data.data.length > 0) {
      console.log('\n🏆 Top 3 jogadores:');
      data.data.slice(0, 3).forEach((player, index) => {
        console.log(`   ${index + 1}. ${player.playerName} - ${player.totalFame} pontos`);
      });
    }
    
  } catch (error) {
    console.error('❌ Erro ao testar API:', error.message);
  }
}

testFameAPI(); 