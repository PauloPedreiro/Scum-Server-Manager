// Script para limpar localStorage
console.log('🧹 Limpando localStorage...');

// Limpar dados de autenticação
localStorage.removeItem('scum_auth_token');
localStorage.removeItem('scum_user_data');

console.log('✅ localStorage limpo!');
console.log('Token removido:', !localStorage.getItem('scum_auth_token'));
console.log('User removido:', !localStorage.getItem('scum_user_data')); 