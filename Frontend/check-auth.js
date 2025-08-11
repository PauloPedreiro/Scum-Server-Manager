// Script para verificar dados de autenticação
console.log('🔍 Verificando dados de autenticação...');

const token = localStorage.getItem('scum_auth_token');
const userData = localStorage.getItem('scum_user_data');

console.log('Token:', token ? '✅ Existe' : '❌ Não existe');
console.log('User Data:', userData ? '✅ Existe' : '❌ Não existe');

if (token) {
  console.log('Token value:', token.substring(0, 20) + '...');
}

if (userData) {
  try {
    const user = JSON.parse(userData);
    console.log('User:', user);
  } catch (e) {
    console.log('Erro ao parsear user data:', e);
  }
} 