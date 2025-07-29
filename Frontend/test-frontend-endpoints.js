const axios = require('axios');

// Simular as chamadas do frontend
const BASE_URL = 'http://localhost:3000';

async function testFrontendEndpoints() {
  console.log('🧪 Testando endpoints como o frontend faz...\n');

  const endpoints = [
    { 
      name: 'Chat In Game', 
      url: `${BASE_URL}/api/chat_in_game`,
      method: 'GET'
    },
    { 
      name: 'Log Veículos', 
      url: `${BASE_URL}/api/LogVeiculos`,
      method: 'GET'
    },
    { 
      name: 'Admin Log', 
      url: `${BASE_URL}/api/adminlog`,
      method: 'GET'
    },
    { 
      name: 'Painel Players', 
      url: `${BASE_URL}/api/players/painelplayers`,
      method: 'GET'
    }
  ];

  for (const endpoint of endpoints) {
    try {
      console.log(`📡 Testando: ${endpoint.name}`);
      console.log(`   URL: ${endpoint.url}`);
      console.log(`   Método: ${endpoint.method}`);
      
      const response = await axios.get(endpoint.url, {
        headers: {
          'Content-Type': 'application/json'
        },
        timeout: 5000
      });
      
      console.log(`   ✅ Status: ${response.status}`);
      console.log(`   📄 Content-Type: ${response.headers['content-type']}`);
      
      const data = response.data;
      console.log(`   📊 Success: ${data.success}`);
      console.log(`   📝 Message: ${data.message}`);
      
      if (data.data) {
        if (Array.isArray(data.data)) {
          console.log(`   📊 Data length: ${data.data.length}`);
        } else {
          console.log(`   📊 Data type: ${typeof data.data}`);
        }
      }
      
      console.log('');
      
    } catch (error) {
      console.log(`   ❌ Erro: ${error.message}`);
      if (error.response) {
        console.log(`   📊 Status: ${error.response.status}`);
        console.log(`   📄 Data: ${JSON.stringify(error.response.data)}`);
      }
      console.log('');
    }
  }
}

testFrontendEndpoints().catch(console.error); 