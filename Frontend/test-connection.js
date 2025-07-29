import axios from 'axios';

async function testBackendConnection() {
  const urls = [
    'http://192.168.100.3:3000',
    'http://127.0.0.1:3000',
    'http://localhost:3000'
  ];

  console.log('Testando conexão com o backend...\n');

  for (const url of urls) {
    try {
      console.log(`Testando: ${url}`);
      const response = await axios.get(`${url}/api/logs/online`, {
        timeout: 5000
      });
      console.log(`✅ SUCESSO: ${url} - Status: ${response.status}`);
      console.log(`Dados:`, response.data);
      return url; // Retorna a primeira URL que funcionar
    } catch (error) {
      console.log(`❌ ERRO: ${url} - ${error.message}`);
    }
  }

  console.log('\n❌ Nenhuma URL funcionou!');
  return null;
}

testBackendConnection(); 