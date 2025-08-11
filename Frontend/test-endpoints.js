import axios from 'axios';

const BASE_URL = 'http://localhost:3000';

async function testEndpoints() {
  console.log('🧪 Testando endpoints do backend...\n');

  const endpoints = [
    { name: 'Chat In Game', url: `${BASE_URL}/api/chat_in_game` },
    { name: 'Log Veículos', url: `${BASE_URL}/api/LogVeiculos` },
    { name: 'Admin Log', url: `${BASE_URL}/api/adminlog` },
    { name: 'Painel Players', url: `${BASE_URL}/api/players/painelplayers` }
  ];

  for (const endpoint of endpoints) {
    try {
      console.log(`📡 Testando: ${endpoint.name}`);
      console.log(`   URL: ${endpoint.url}`);
      
      const response = await axios.get(endpoint.url, {
        timeout: 5000,
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      console.log(`   ✅ Status: ${response.status}`);
      console.log(`   📄 Tipo de resposta: ${typeof response.data}`);
      console.log(`   📊 Dados:`, response.data);
      console.log('');
      
    } catch (error) {
      console.log(`   ❌ Erro: ${error.message}`);
      if (error.response) {
        console.log(`   📊 Status: ${error.response.status}`);
        console.log(`   📄 Resposta:`, error.response.data);
      }
      console.log('');
    }
  }
}

testEndpoints().catch(console.error); 