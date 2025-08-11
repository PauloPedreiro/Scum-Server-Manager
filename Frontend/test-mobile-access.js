import http from 'http';

console.log('🔍 Testando Conectividade Móvel...\n');

// Teste 1: Frontend (Vite)
console.log('📱 Teste 1: Frontend (Porta 5173)');
const frontendTest = http.get('http://192.168.100.3:5173', (res) => {
  console.log(`✅ Frontend acessível: ${res.statusCode}`);
  console.log(`   URL: http://192.168.100.3:5173\n`);
}).on('error', (err) => {
  console.log(`❌ Frontend não acessível: ${err.message}\n`);
});

// Teste 2: Backend (API)
console.log('🔧 Teste 2: Backend (Porta 3000)');
const backendTest = http.get('http://192.168.100.3:3000/api/auth/login', (res) => {
  console.log(`✅ Backend acessível: ${res.statusCode}`);
  console.log(`   URL: http://192.168.100.3:3000/api/auth/login\n`);
}).on('error', (err) => {
  console.log(`❌ Backend não acessível: ${err.message}\n`);
});

// Teste 3: Localhost (comparação)
console.log('🏠 Teste 3: Localhost (comparação)');
const localTest = http.get('http://localhost:5173', (res) => {
  console.log(`✅ Localhost funciona: ${res.statusCode}\n`);
}).on('error', (err) => {
  console.log(`❌ Localhost não funciona: ${err.message}\n`);
});

// Informações úteis
console.log('📋 Informações para Acesso Móvel:');
console.log('   IP da Rede: 192.168.100.3');
console.log('   Frontend: http://192.168.100.3:5173');
console.log('   Backend: http://192.168.100.3:3000');
console.log('\n📱 No celular, acesse: http://192.168.100.3:5173');
console.log('\n🔧 Se o backend não funcionar, pode ser necessário:');
console.log('   1. Configurar o backend para aceitar conexões externas');
console.log('   2. Liberar porta 3000 no firewall');
console.log('   3. Verificar se o backend está rodando em 0.0.0.0:3000'); 